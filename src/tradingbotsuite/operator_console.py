from __future__ import annotations

import asyncio
import json
from collections import deque
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from tradingbotsuite.config import AppConfig
from tradingbotsuite.core.microstructure_prediction import build_microstructure_prediction
from tradingbotsuite.core.models import RuntimeMode, SafeModeReason, SignalDirection, TradeStatus
from tradingbotsuite.operator_commands import (
    command_id,
    execute_manual_signal,
    execute_reconcile,
    execute_refresh_health,
    execute_smoke_live,
    execute_supervise,
)
from tradingbotsuite.research.data_pipeline import DATA_PIPELINE_DEFAULT_STAGE, prepare_hmm_knn_research_data
from tradingbotsuite.research.experiment_runner import run_research_experiment
from tradingbotsuite.research.workflow import build_dataset, calibrate_model_artifact, replay_eval_artifact, train_model

AMBIGUOUS_SAFETY_REASONS = {
    SafeModeReason.POSITION_AMBIGUITY,
    SafeModeReason.RECONCILIATION_MISMATCH,
    SafeModeReason.RECONCILIATION_STALE,
}


class TraceRecorder:
    def __init__(self, limit: int = 256) -> None:
        self._events: deque[dict[str, Any]] = deque(maxlen=limit)

    def _sanitize(self, value: Any, *, depth: int = 0) -> Any:
        if depth >= 3:
            return str(value)
        if isinstance(value, dict):
            sanitized: dict[str, Any] = {}
            for key, nested in value.items():
                if key == "recent_traces":
                    sanitized[key] = "<omitted>"
                else:
                    sanitized[key] = self._sanitize(nested, depth=depth + 1)
            return sanitized
        if isinstance(value, list):
            return [self._sanitize(item, depth=depth + 1) for item in value[:10]]
        return value

    def __call__(self, stage: str, details: dict[str, Any]) -> None:
        time_ms = None
        if isinstance(details, dict):
            time_ms = details.get("now_ms") or details.get("updated_time_ms")
        if time_ms is None:
            time_ms = 0
        event_id = f"{int(time_ms):013d}:trace:{len(self._events):05d}"
        self._events.append(
            {
                "id": event_id,
                "time_ms": int(time_ms),
                "kind": "trace",
                "summary": stage,
                "payload": self._sanitize(details),
            }
        )

    def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        return list(self._events)[-limit:]


@dataclass(slots=True)
class OperatorContext:
    config: AppConfig
    engine: Any
    trace_recorder: TraceRecorder


class OperatorConsoleService:
    def __init__(self, context: OperatorContext):
        self.context = context
        self._stop_event = asyncio.Event()
        self._job_task: asyncio.Task[None] | None = None

    @property
    def config(self) -> AppConfig:
        self.context.config = self.context.engine.config
        return self.context.config

    @property
    def engine(self):
        return self.context.engine

    @property
    def store(self):
        return self.context.engine.store

    async def start(self) -> None:
        if self.config.operator_ui.enabled and self._job_task is None:
            self._job_task = asyncio.create_task(self._job_loop())

    async def shutdown(self) -> None:
        self._stop_event.set()
        if self._job_task is not None:
            self._job_task.cancel()
            try:
                await self._job_task
            except asyncio.CancelledError:
                pass

    async def snapshot(self, symbol: str) -> dict[str, Any]:
        snapshot = await self.engine.collect_system_snapshot(symbol)
        snapshot["microstructure_prediction"] = build_microstructure_prediction(snapshot.get("microstructure"))
        snapshot["recommendations"] = self.build_recommendations(snapshot)
        snapshot["recent_traces"] = self.context.trace_recorder.list_recent(limit=20)
        return snapshot

    async def feed(
        self,
        *,
        after_id: str | None = None,
        limit: int = 50,
        include_health_events: bool = True,
        include_execution_metrics: bool = True,
    ) -> dict[str, Any]:
        persisted = await self.store.list_operator_feed(
            after_id=after_id,
            limit=limit,
            include_health_events=include_health_events,
            include_execution_metrics=include_execution_metrics,
        )
        trace_items = self.context.trace_recorder.list_recent(limit=limit)
        items = persisted["items"] + [item for item in trace_items if after_id is None or item["id"] > after_id]
        items.sort(key=lambda item: item["id"], reverse=True)
        items = items[:limit]
        return {"items": items, "next_cursor": items[0]["id"] if items else after_id}

    async def execute_command(self, command_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        now_ms = self.engine.clock()
        cid = command_id(command_type)
        try:
            if command_type == "manual-signal":
                direction = SignalDirection(str(payload["direction"]))
                result = await execute_manual_signal(
                    self.engine,
                    symbol=str(payload.get("symbol", "BTCUSDT")).upper(),
                    direction=direction,
                    testnet_short_lived_protections=bool(payload.get("testnet_short_lived_protections", False)),
                )
            elif command_type == "supervise":
                result = await execute_supervise(self.engine, symbol=str(payload.get("symbol", "BTCUSDT")).upper())
            elif command_type == "reconcile":
                result = await execute_reconcile(self.engine, symbol=str(payload.get("symbol", "BTCUSDT")).upper())
            elif command_type == "refresh-health":
                result = await execute_refresh_health(self.engine, symbol=str(payload.get("symbol", "BTCUSDT")).upper())
            elif command_type == "smoke-live":
                size = payload.get("size")
                result = await execute_smoke_live(self.engine, size=(Decimal(str(size)) if size is not None else None))
            elif command_type == "set-mode":
                result = await self.engine.set_runtime_mode(RuntimeMode(str(payload["mode"])))
                self.context.config = self.engine.config
            else:
                raise ValueError(f"unsupported operator command: {command_type}")
            await self.store.save_operator_command(
                command_id=cid,
                command_type=command_type,
                requested_at_ms=now_ms,
                request=payload,
                result=result,
                success=True,
            )
            return {"command_id": cid, "success": True, "result": result}
        except Exception as exc:
            error_result = {"error": str(exc)}
            await self.store.save_operator_command(
                command_id=cid,
                command_type=command_type,
                requested_at_ms=now_ms,
                request=payload,
                result=error_result,
                success=False,
            )
            return {"command_id": cid, "success": False, "result": error_result}

    async def queue_job(self, job_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        await self._assert_research_job_allowed()
        job_id = command_id(job_type)
        await self.store.queue_operator_job(
            job_id=job_id,
            job_type=job_type,
            requested_at_ms=self.engine.clock(),
            request=payload,
        )
        await self.store.append_operator_job_log(
            job_id=job_id,
            time_ms=self.engine.clock(),
            level="info",
            message="job queued",
            payload=payload,
        )
        return {"job_id": job_id, "status": "queued"}

    async def list_jobs(self) -> list[dict[str, Any]]:
        return await self.store.list_operator_jobs()

    async def get_job(self, job_id: str) -> dict[str, Any] | None:
        return await self.store.get_operator_job(job_id)

    def list_artifacts(self) -> list[dict[str, Any]]:
        base_dir = self.config.research.output_dir
        if not base_dir.exists():
            return []
        artifacts: list[dict[str, Any]] = []
        for train_manifest in sorted(base_dir.rglob("train_manifest.json")):
            payload = json.loads(train_manifest.read_text(encoding="utf-8"))
            artifacts.append(
                {
                    "type": "train_artifact",
                    "path": str(train_manifest),
                    "sort_time": train_manifest.stat().st_mtime,
                    "manifest": payload,
                    "summary": {
                        "model_version": payload.get("model_version"),
                        "train_rows": payload.get("train_rows"),
                        "total_rows": payload.get("total_rows"),
                        "dataset_path": payload.get("dataset_path"),
                    },
                }
            )
        for manifest_path in sorted(base_dir.rglob("artifact_manifest.json")):
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            if payload.get("artifact_manifest_version") == "v2-hmm-knn-artifact-manifest-1":
                raw_metrics_path = payload.get("metrics_path")
                metrics_path = Path(str(raw_metrics_path)) if raw_metrics_path else manifest_path.parent / "walk_forward_metrics.json"
                if not metrics_path.is_absolute():
                    parent_candidate = manifest_path.parent / metrics_path
                    metrics_path = parent_candidate if parent_candidate.exists() else metrics_path
                metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else None
                monitoring_path = manifest_path.parent / "monitoring_report.json"
                monitoring = json.loads(monitoring_path.read_text(encoding="utf-8")) if monitoring_path.exists() else None
                alert_counts: dict[str, int] = {}
                for alert in (monitoring or {}).get("alerts", []):
                    severity = str(alert.get("severity", "unknown"))
                    alert_counts[severity] = alert_counts.get(severity, 0) + 1
                artifacts.append(
                    {
                        "type": "hmm_knn_artifact",
                        "path": str(manifest_path),
                        "sort_time": manifest_path.stat().st_mtime,
                        "manifest": payload,
                        "metrics_path": str(metrics_path) if metrics_path.exists() else None,
                        "metrics": metrics,
                        "monitoring_path": str(monitoring_path) if monitoring_path.exists() else None,
                        "monitoring": monitoring,
                        "summary": {
                            "plan_version": payload.get("plan_version"),
                            "symbol": payload.get("symbol"),
                            "row_count": payload.get("row_count"),
                            "promotion_ready": False,
                            "research_only": payload.get("research_only"),
                            "meta_trade_count": ((((metrics or {}).get("comparison") or {}).get("hmm_knn_meta_model") or {}).get("trade_count")),
                            "meta_expectancy": ((((metrics or {}).get("comparison") or {}).get("hmm_knn_meta_model") or {}).get("expectancy_after_cost")),
                            "monitoring_alert_count": len((monitoring or {}).get("alerts", [])),
                            "monitoring_alert_counts": alert_counts,
                            "regime_no_trade_rate": (((monitoring or {}).get("entropy_no_trade") or {}).get("regime_no_trade_rate")),
                            "posterior_entropy_p95": (((monitoring or {}).get("entropy_no_trade") or {}).get("posterior_entropy_p95")),
                            "max_regime_drift": (((monitoring or {}).get("regime_distribution_drift") or {}).get("max_drift")),
                            "neighbor_quality_p05": (((monitoring or {}).get("neighbor_quality") or {}).get("neighbor_distance_quality_p05")),
                        },
                    }
                )
                continue
            metrics_path = manifest_path.parent / "metrics.json"
            metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else None
            artifacts.append(
                {
                    "type": "model_artifact",
                    "path": str(manifest_path),
                    "sort_time": manifest_path.stat().st_mtime,
                    "manifest": payload,
                    "metrics_path": str(metrics_path) if metrics_path.exists() else None,
                    "metrics": metrics,
                    "summary": {
                        "model_version": payload.get("model_version"),
                        "calibration_version": payload.get("calibration_version"),
                        "dataset_path": payload.get("dataset_path"),
                        "promotion_ready": (metrics or {}).get("promotion_ready"),
                        "v2_expectancy": (((metrics or {}).get("comparison") or {}).get("v2_meta_label_acceptance") or {}).get("expectancy_after_cost"),
                        "baseline_expectancy": (((metrics or {}).get("comparison") or {}).get("v1_microstructure_baseline") or {}).get("expectancy_after_cost"),
                    },
                }
            )
        for dataset_manifest in sorted(base_dir.rglob("dataset_manifest.json")):
            payload = json.loads(dataset_manifest.read_text(encoding="utf-8"))
            artifacts.append(
                {
                    "type": "dataset",
                    "path": str(dataset_manifest),
                    "sort_time": dataset_manifest.stat().st_mtime,
                    "manifest": payload,
                    "summary": {
                        "row_count": payload.get("row_count"),
                        "dataset_path": payload.get("dataset_path"),
                        "dataset_sha256": payload.get("dataset_sha256"),
                        "missing_feature_rates": payload.get("missing_feature_rates"),
                    },
                }
            )
        for pipeline_summary in sorted(base_dir.rglob("pipeline_summary.json")):
            payload = json.loads(pipeline_summary.read_text(encoding="utf-8"))
            artifacts.append(
                {
                    "type": "research_pipeline",
                    "path": str(pipeline_summary),
                    "sort_time": pipeline_summary.stat().st_mtime,
                    "manifest": payload,
                    "summary": {
                        "version": payload.get("version"),
                        "stage_requested": payload.get("stage_requested"),
                        "conclusion_status": ((payload.get("conclusion") or {}).get("status")),
                        "conclusion_reason": ((payload.get("conclusion") or {}).get("reason")),
                        "data_quality_alert_count": ((payload.get("data_quality") or {}).get("alert_count")),
                        "evidence_mode": ((payload.get("evidence") or {}).get("mode")),
                        "evidence_status": ((payload.get("evidence") or {}).get("status")),
                        "top_failure_count": len(payload.get("top_failure_reasons") or []),
                    },
                }
            )
        for intake_manifest in sorted(base_dir.rglob("data_intake_manifest.json")):
            payload = json.loads(intake_manifest.read_text(encoding="utf-8"))
            artifacts.append(
                {
                    "type": "data_pipeline_intake",
                    "path": str(intake_manifest),
                    "sort_time": intake_manifest.stat().st_mtime,
                    "manifest": payload,
                    "summary": {
                        "version": payload.get("version"),
                        "stage_requested": payload.get("stage_requested"),
                        "provider_count": len(payload.get("providers") or []),
                        "dataset_status": (((payload.get("stage_status") or {}).get("dataset") or {}).get("status")),
                        "evidence_status": (((payload.get("stage_status") or {}).get("evidence") or {}).get("status")),
                    },
                }
            )
        for data_quality_report in sorted(base_dir.rglob("data_quality_report.json")):
            payload = json.loads(data_quality_report.read_text(encoding="utf-8"))
            artifacts.append(
                {
                    "type": "data_quality_report",
                    "path": str(data_quality_report),
                    "sort_time": data_quality_report.stat().st_mtime,
                    "manifest": payload,
                    "summary": {
                        "manifest_count": payload.get("manifest_count"),
                        "alert_count": len(payload.get("alerts") or []),
                        "gap_count_total": payload.get("gap_count_total"),
                        "duplicate_count_total": payload.get("duplicate_count_total"),
                        "non_promotable_count": payload.get("non_promotable_count"),
                    },
                }
            )
        for market_journal_manifest in sorted(base_dir.rglob("market_journal_manifest.json")):
            payload = json.loads(market_journal_manifest.read_text(encoding="utf-8"))
            artifacts.append(
                {
                    "type": "market_journal_manifest",
                    "path": str(market_journal_manifest),
                    "sort_time": market_journal_manifest.stat().st_mtime,
                    "manifest": payload,
                    "summary": {
                        "event_count": payload.get("event_count"),
                        "event_counts_by_source": payload.get("event_counts_by_source") or {},
                        "event_counts_by_symbol": payload.get("event_counts_by_symbol") or {},
                        "event_counts_by_family": payload.get("event_counts_by_family") or {},
                        "duplicate_hash_count": payload.get("duplicate_hash_count"),
                        "sequence_gap_count": payload.get("sequence_gap_count"),
                    },
                }
            )
        for provider_manifest in sorted(base_dir.rglob("*.manifest.json")):
            if provider_manifest.name == "market_journal_manifest.json":
                continue
            payload = json.loads(provider_manifest.read_text(encoding="utf-8"))
            if not payload.get("source_name") or not payload.get("data_family"):
                continue
            if "content_hash" not in payload and "ingestion_status" not in payload:
                continue
            artifacts.append(
                {
                    "type": "provider_archive_manifest",
                    "path": str(provider_manifest),
                    "sort_time": provider_manifest.stat().st_mtime,
                    "manifest": payload,
                    "summary": {
                        "source_name": payload.get("source_name"),
                        "symbol": payload.get("symbol"),
                        "data_family": payload.get("data_family"),
                        "interval": payload.get("interval"),
                        "row_count": payload.get("row_count"),
                        "gap_count": payload.get("gap_count"),
                        "duplicate_count": payload.get("duplicate_count"),
                        "ingestion_status": payload.get("ingestion_status"),
                        "diagnostic_only": payload.get("diagnostic_only"),
                    },
                }
            )
        for experiment_manifest in sorted(base_dir.rglob("experiment_manifest.json")):
            payload = json.loads(experiment_manifest.read_text(encoding="utf-8"))
            artifacts.append(
                {
                    "type": "hmm_knn_experiment_matrix",
                    "path": str(experiment_manifest),
                    "sort_time": experiment_manifest.stat().st_mtime,
                    "manifest": payload,
                    "summary": {
                        "name": payload.get("name"),
                        "overall_status": payload.get("overall_status"),
                        "experiment_count": len(payload.get("experiments") or []),
                        "effective_workers": payload.get("effective_workers"),
                        "promotion_failure_counts": payload.get("promotion_failure_counts") or {},
                        "research_boundary_passed": ((payload.get("research_boundary") or {}).get("passed")),
                    },
                }
            )
        for experiment_run_manifest in sorted(base_dir.rglob("experiment_run_manifest.json")):
            payload = json.loads(experiment_run_manifest.read_text(encoding="utf-8"))
            conclusion_path = Path(str((payload.get("artifact_links") or {}).get("conclusion_path") or experiment_run_manifest.parent / "conclusion.md"))
            conclusion_text = conclusion_path.read_text(encoding="utf-8") if conclusion_path.exists() else None
            artifacts.append(
                {
                    "type": "research_experiment_run",
                    "path": str(experiment_run_manifest),
                    "sort_time": experiment_run_manifest.stat().st_mtime,
                    "manifest": payload,
                    "conclusion_path": str(conclusion_path) if conclusion_path.exists() else None,
                    "conclusion_text": conclusion_text,
                    "summary": {
                        "name": payload.get("name"),
                        "run_id": payload.get("run_id"),
                        "conclusion_status": ((payload.get("conclusion") or {}).get("status")),
                        "conclusion_reason": ((payload.get("conclusion") or {}).get("reason")),
                        "pipeline_status": ((payload.get("pipeline_conclusion") or {}).get("status")),
                        "data_quality_alert_count": ((payload.get("data_quality") or {}).get("alert_count")),
                        "evidence_status": ((payload.get("evidence") or {}).get("status")),
                        "provider_statuses": payload.get("provider_statuses") or [],
                        "research_boundary_passed": ((payload.get("research_boundary") or {}).get("passed")),
                    },
                }
            )
        artifacts.sort(key=lambda item: float(item.get("sort_time") or 0.0), reverse=True)
        for artifact in artifacts:
            artifact.pop("sort_time", None)
        return artifacts

    def list_guide_documents(self) -> list[dict[str, Any]]:
        root = Path(__file__).resolve().parents[2]
        runtime_docs_root = root / "docs" / "tradingbotsuite_runtime"

        def doc_path(name: str) -> Path:
            runtime_path = runtime_docs_root / name
            if runtime_path.exists():
                return runtime_path
            return root / "docs" / name

        docs = [
            ("operator-guide", "Operator Guide", doc_path("OPERATOR_GUIDE.md")),
            ("microstructure-reliability", "Microstructure Reliability", doc_path("MICROSTRUCTURE_RELIABILITY.md")),
        ]
        result: list[dict[str, Any]] = []
        for slug, title, path in docs:
            if not path.exists():
                continue
            result.append(
                {
                    "slug": slug,
                    "title": title,
                    "sections": self._parse_markdown_sections(path.read_text(encoding="utf-8")),
                }
            )
        return result

    def build_recommendations(self, snapshot: dict[str, Any]) -> list[dict[str, str]]:
        recommendations: list[dict[str, str]] = []
        safety = snapshot.get("safety") or {}
        safety_state = snapshot.get("safety_state") or {}
        reason = safety.get("reason")
        state = safety_state.get("state")
        if reason == str(SafeModeReason.STALE_MARKET_DATA):
            recommendations.append({"title": "Market Data Stale", "message": "Check Binance stream health, then run Refresh Health or restart the app."})
        microstructure = snapshot.get("microstructure") or {}
        if microstructure and (not microstructure.get("healthy", True) or microstructure.get("degraded")):
            sync_state = microstructure.get("depth_sync_state") or microstructure.get("order_book_health_state") or "unknown"
            retry_text = " A retry is already scheduled." if microstructure.get("backoff_until_ms") else ""
            recommendations.append(
                {
                    "title": "Depth Stream Degraded",
                    "message": (
                        f"Queue depth is currently {sync_state}. Signed trade flow and top-of-book can still be used when entry readiness stays healthy, "
                        f"but queue imbalance and depletion fields should be treated as unavailable until depth returns to synced.{retry_text}"
                    ),
                }
            )
        market_health = snapshot.get("market_data_health") or {}
        if market_health.get("reason_code") == "spread_abnormality":
            recommendations.append(
                {
                    "title": "Spread Too Wide",
                    "message": "Wait for Binance spread to normalize before trusting a new entry.",
                }
            )
        if market_health.get("reason_code") == "daily_loss_limit":
            recommendations.append(
                {
                    "title": "Daily Loss Limit Hit",
                    "message": "Keep entries paused for the rest of the UTC session and review closed-trade attribution.",
                }
            )
        if reason == str(SafeModeReason.BASIS_DISLOCATION):
            recommendations.append({"title": "Basis Dislocation", "message": "Do not force entries. Inspect Binance and Hyperliquid mids before continuing."})
        if reason == str(SafeModeReason.RECONCILIATION_STALE):
            recommendations.append({"title": "Reconciliation Stale", "message": "Run Reconcile. If unresolved, keep trading disabled."})
        if state == "blocked":
            recommendations.append(
                {
                    "title": "Entry Blocked",
                    "message": safety_state.get("recommended_action") or "Review the current safety state before sending another signal.",
                }
            )
        if self.config.research.artifact_manifest_path is None:
            recommendations.append({"title": "No V2 Model Artifact", "message": "Build dataset, train, and calibrate before expecting shadow-mode scores."})
        position = snapshot.get("position") or {}
        if self.config.runtime_mode == RuntimeMode.LIVE and position.get("status") == str(TradeStatus.OPEN):
            recommendations.append({"title": "Live Position Open", "message": "Research jobs stay blocked while a live position is open."})
        if not recommendations:
            recommendations.append({"title": "System Healthy", "message": "No operator action is currently recommended."})
        return recommendations

    async def _assert_research_job_allowed(self) -> None:
        safety = await self.store.get_safety_status()
        if safety and safety.in_safe_mode and safety.reason in AMBIGUOUS_SAFETY_REASONS:
            raise ValueError(f"research jobs are blocked while safety is ambiguous: {safety.reason}")
        if self.config.runtime_mode == RuntimeMode.LIVE:
            positions = await self.store.list_position_states()
            if any(position.status == TradeStatus.OPEN for position in positions):
                raise ValueError("research jobs are blocked while a live position is open")
            raise ValueError("research jobs are blocked in live mode")

    async def _job_loop(self) -> None:
        while not self._stop_event.is_set():
            claimed = await self.store.claim_next_operator_job()
            if claimed is None:
                await asyncio.sleep(0.5)
                continue
            job_id = claimed["job_id"]
            await self.store.mark_operator_job_started(job_id, self.engine.clock())
            await self.store.append_operator_job_log(
                job_id=job_id,
                time_ms=self.engine.clock(),
                level="info",
                message="job started",
            )
            try:
                request = claimed["request"]
                result = await self._run_job(claimed["job_type"], request, job_id)
                await self.store.complete_operator_job(
                    job_id=job_id,
                    status="succeeded",
                    finished_at_ms=self.engine.clock(),
                    result=result,
                )
                await self.store.append_operator_job_log(
                    job_id=job_id,
                    time_ms=self.engine.clock(),
                    level="info",
                    message="job completed",
                    payload=result,
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                await self.store.complete_operator_job(
                    job_id=job_id,
                    status="failed",
                    finished_at_ms=self.engine.clock(),
                    error_text=str(exc),
                )
                await self.store.append_operator_job_log(
                    job_id=job_id,
                    time_ms=self.engine.clock(),
                    level="error",
                    message="job failed",
                    payload={"error": str(exc)},
                )

    async def _run_job(self, job_type: str, request: dict[str, Any], job_id: str) -> dict[str, Any]:
        if job_type == "build-dataset":
            result = await build_dataset(self.config)
            return {"dataset_path": str(result.dataset_path), "manifest_path": str(result.manifest_path), "row_count": result.row_count}
        if job_type == "prepare-hmm-knn-research-data":
            result = await asyncio.to_thread(
                prepare_hmm_knn_research_data,
                spec_path=Path(str(request["spec_path"])),
                stage=str(request.get("stage") or DATA_PIPELINE_DEFAULT_STAGE),
                app_config=self.config,
            )
            return {
                "output_dir": str(result.output_dir),
                "data_intake_manifest_path": str(result.intake_manifest_path),
                "data_quality_report_path": str(result.data_quality_report_path),
                "market_journal_manifest_path": str(result.market_journal_manifest_path),
                "pipeline_summary_path": str(result.pipeline_summary_path),
                "dataset_manifest_path": str(result.dataset_manifest_path) if result.dataset_manifest_path is not None else None,
                "evidence_manifest_path": str(result.evidence_manifest_path) if result.evidence_manifest_path is not None else None,
            }
        if job_type == "run-research-experiment":
            result = await asyncio.to_thread(
                run_research_experiment,
                spec_path=Path(str(request["spec_path"])),
                app_config=self.config,
            )
            return {
                "output_dir": str(result.output_dir),
                "experiment_run_manifest_path": str(result.manifest_path),
                "conclusion_path": str(result.conclusion_path),
                "pipeline_summary_path": str(result.pipeline_summary_path),
            }
        if job_type == "train-model":
            dataset_path = Path(request["dataset_path"])
            manifest_path = await asyncio.to_thread(train_model, self.config, dataset_path=dataset_path)
            return {"train_manifest_path": str(manifest_path)}
        if job_type == "calibrate-model":
            artifact_manifest_path = await asyncio.to_thread(
                calibrate_model_artifact,
                self.config,
                train_manifest_path=Path(request["train_manifest_path"]),
            )
            return {"artifact_manifest_path": str(artifact_manifest_path)}
        if job_type == "replay-eval":
            metrics_path = await asyncio.to_thread(
                replay_eval_artifact,
                self.config,
                artifact_manifest_path=Path(request["artifact_manifest_path"]),
            )
            return {"metrics_path": str(metrics_path)}
        raise ValueError(f"unsupported job type: {job_type}")

    def _parse_markdown_sections(self, text: str) -> list[dict[str, Any]]:
        sections: list[dict[str, Any]] = []
        current_section: dict[str, Any] | None = None
        for raw_line in text.splitlines():
            line = raw_line.rstrip()
            if line.startswith("# "):
                continue
            if line.startswith("## "):
                current_section = {"title": line[3:].strip(), "items": []}
                sections.append(current_section)
                continue
            if current_section is None:
                continue
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("- "):
                current_section["items"].append({"type": "bullet", "text": stripped[2:].strip()})
            elif stripped.startswith("```"):
                continue
            else:
                current_section["items"].append({"type": "text", "text": stripped})
        return sections
