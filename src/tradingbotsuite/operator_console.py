from __future__ import annotations

import asyncio
import json
import re
from collections import deque
from dataclasses import asdict, dataclass
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
from tradingbotsuite.research.entry_gate import (
    DEFAULT_GATE_CANDIDATE_CAP,
    GOLDILOCKS_GATE_FAMILY,
    LEGACY_GATE_FAMILY,
    GateParameters,
    analyze_entry_gate_configuration,
    default_visual_gate_parameters,
    optimizer_exit_settings,
    preferred_research_exit_settings,
    run_entry_gate_optimizer,
    run_entry_gate_preflight,
    run_entry_gate_research,
)
from tradingbotsuite.research.data_pipeline import DATA_PIPELINE_DEFAULT_STAGE, prepare_hmm_knn_research_data
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
        for entry_gate_metrics in sorted(base_dir.rglob("v2-btc-entry-gates-*/metrics.json")):
            payload = json.loads(entry_gate_metrics.read_text(encoding="utf-8"))
            artifacts.append(
                {
                    "type": "entry_gate_research",
                    "path": str(entry_gate_metrics),
                    "sort_time": entry_gate_metrics.stat().st_mtime,
                    "manifest": payload,
                    "summary": {
                        "strategy_version": payload.get("strategy_version"),
                        "selection_status": payload.get("selection_status"),
                        "candidate_count": payload.get("candidate_count"),
                        "candidate_full_pass_count": payload.get("candidate_full_pass_count"),
                        "baseline_return": ((payload.get("baseline") or {}).get("return_on_capital_pct")),
                        "best_return": ((payload.get("best") or {}).get("return_on_capital_pct")),
                        "best_rejection_rate": ((payload.get("best") or {}).get("rejection_rate")),
                    },
                }
            )
        for optimizer_metrics in sorted(base_dir.rglob("v2-btc-entry-gate-optimizer-*/metrics.json")):
            payload = json.loads(optimizer_metrics.read_text(encoding="utf-8"))
            artifacts.append(
                {
                    "type": "entry_gate_optimizer",
                    "path": str(optimizer_metrics),
                    "sort_time": optimizer_metrics.stat().st_mtime,
                    "manifest": payload,
                    "summary": {
                        "strategy_version": payload.get("strategy_version"),
                        "exit_profile": payload.get("exit_profile"),
                        "allowed_components": payload.get("allowed_components"),
                        "evaluated_count": payload.get("evaluated_count"),
                        "selection_status": payload.get("selection_status"),
                        "candidate_full_pass_count": payload.get("candidate_full_pass_count"),
                        "best_return": ((payload.get("best") or {}).get("return_on_capital_pct")),
                        "best_rejection_rate": ((payload.get("best") or {}).get("rejection_rate")),
                    },
                }
            )
        for preflight_metrics in sorted(base_dir.rglob("v2-btc-entry-gate-preflight-*/metrics.json")):
            payload = json.loads(preflight_metrics.read_text(encoding="utf-8"))
            artifacts.append(
                {
                    "type": "entry_gate_preflight",
                    "path": str(preflight_metrics),
                    "sort_time": preflight_metrics.stat().st_mtime,
                    "manifest": payload,
                    "summary": {
                        "strategy_version": payload.get("strategy_version"),
                        "candidate_count": payload.get("candidate_count"),
                        "component_count": payload.get("component_count"),
                        "viable_components": payload.get("viable_components"),
                    },
                }
            )
        artifacts.sort(key=lambda item: float(item.get("sort_time") or 0.0), reverse=True)
        for artifact in artifacts:
            artifact.pop("sort_time", None)
        return artifacts

    def list_analysis_uploads(self) -> list[dict[str, Any]]:
        upload_dir = self._analysis_upload_dir()
        if not upload_dir.exists():
            return []
        items: list[dict[str, Any]] = []
        for path in sorted(upload_dir.glob("*.csv"), key=lambda candidate: candidate.stat().st_mtime, reverse=True):
            stat = path.stat()
            items.append(
                {
                    "name": path.name,
                    "path": str(path),
                    "size_bytes": stat.st_size,
                    "updated_at_ms": int(stat.st_mtime * 1000),
                }
            )
        return items

    async def upload_chart_export(self, filename: str, content: bytes) -> dict[str, Any]:
        safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(filename).name).strip("_") or "chart_export.csv"
        if not safe_name.lower().endswith(".csv"):
            safe_name = f"{safe_name}.csv"
        upload_dir = self._analysis_upload_dir()
        upload_dir.mkdir(parents=True, exist_ok=True)
        target = upload_dir / safe_name
        await asyncio.to_thread(target.write_bytes, content)
        return {
            "name": target.name,
            "path": str(target),
            "size_bytes": len(content),
            "updated_at_ms": self.engine.clock(),
        }

    async def analyze_entry_gates(self, payload: dict[str, Any]) -> dict[str, Any]:
        path = Path(str(payload.get("path", "BINANCE_BTCUSDT.P, 15 (2).csv")))
        symbol = str(payload.get("symbol", "BTCUSDT")).upper()
        strategy_version = str(payload.get("strategy_version", "visual_analysis"))
        gate_family = str(payload.get("gate_family", LEGACY_GATE_FAMILY)).strip().lower().replace("-", "_")
        if gate_family not in {LEGACY_GATE_FAMILY, GOLDILOCKS_GATE_FAMILY}:
            raise ValueError(f"unsupported gate_family: {gate_family}")
        max_chart_points = max(200, min(int(payload.get("max_chart_points", 20_000)), 20_000))
        max_visible_decisions = payload.get("max_visible_decisions", 2000)
        if max_visible_decisions is not None:
            max_visible_decisions = max(100, min(int(max_visible_decisions), 10000))

        params = GateParameters(
            gate_family=gate_family,
            acf_window=int(payload.get("acf_window", 14)),
            acf_block_below=float(payload.get("acf_block_below", -0.20)),
            acf_trend_above=float(payload.get("acf_trend_above", 0.10)),
            hvr_short_window=int(payload.get("hvr_short_window", 6)),
            hvr_long_window=int(payload.get("hvr_long_window", 60)),
            hvr_block_below=float(payload.get("hvr_block_below", 0.50)),
            hvr_release_above=float(payload.get("hvr_release_above", 0.75)),
            dsp_min_cycle_bars=int(payload.get("dsp_min_cycle_bars", 4)),
            dsp_max_cycle_bars=int(payload.get("dsp_max_cycle_bars", 16)),
            dsp_cycle_ratio_threshold=float(payload.get("dsp_cycle_ratio_threshold", 0.55)),
            dsp_trend_slope_threshold=float(payload.get("dsp_trend_slope_threshold", 0.25)),
            use_acf=bool(payload.get("use_acf", True)),
            use_hvr=bool(payload.get("use_hvr", True)),
            use_dsp=bool(payload.get("use_dsp", True)),
            er_window=int(payload.get("er_window", 14)),
            er_min=float(payload.get("er_min", 0.20)),
            vwap_margin_bps=float(payload.get("vwap_margin_bps", 0.0)),
            hv_window_bars=int(payload.get("hv_window_bars", 672)),
            hvp_lookback_bars=int(payload.get("hvp_lookback_bars", 2880)),
            hvp_min=float(payload.get("hvp_min", 20.0)),
            hvp_max=float(payload.get("hvp_max", 80.0)),
            use_er=bool(payload.get("use_er", True)),
            use_vwap=bool(payload.get("use_vwap", True)),
            use_hvp=bool(payload.get("use_hvp", True)),
        )
        settings = optimizer_exit_settings(str(payload.get("exit_profile", preferred_research_exit_settings().exit_mode)))
        result = await asyncio.to_thread(
            analyze_entry_gate_configuration,
            path=path,
            symbol=symbol,
            strategy_version=strategy_version,
            params=params,
            settings=settings,
            gate_family=gate_family,
            ohlcv_cache_policy=payload.get("ohlcv_cache_policy"),
            max_chart_points=max_chart_points,
            max_visible_decisions=max_visible_decisions,
        )
        return result.payload

    def analysis_defaults(self) -> dict[str, Any]:
        gate = default_visual_gate_parameters()
        settings = preferred_research_exit_settings()
        return {
            "gate_family": LEGACY_GATE_FAMILY,
            "gate_parameters": asdict(gate),
            "simulation_settings": asdict(settings),
            "uploads": self.list_analysis_uploads(),
        }

    def list_guide_documents(self) -> list[dict[str, Any]]:
        root = Path(__file__).resolve().parents[2]
        runtime_docs_root = root / "docs" / "tradingbotsuite_runtime"

        def doc_path(name: str) -> Path:
            runtime_path = runtime_docs_root / name
            if runtime_path.exists():
                return runtime_path
            return root / "docs" / name

        docs = [
            ("operator-console", "Operator Console", doc_path("OPERATOR_CONSOLE.md")),
            ("operator-guide", "Operator Guide", doc_path("OPERATOR_GUIDE.md")),
            ("v2-stability-audit", "V2 Stability Audit", doc_path("V2_STABILITY_AUDIT.md")),
            ("btc-runtime-reliability", "BTC Runtime Reliability Guide", doc_path("BTC_RUNTIME_RELIABILITY_GUIDE.md")),
            ("testnet-full-stack-checklist", "Testnet Full-Stack Checklist", doc_path("TESTNET_FULL_STACK_CHECKLIST.md")),
            ("v2-research-guide", "V2 Research Guide", doc_path("V2_RESEARCH_GUIDE.md")),
            ("entry-gate-research", "Entry Gate Research", doc_path("ENTRY_GATE_RESEARCH.md")),
            ("goldilocks-filter-research", "Goldilocks Filter Research", doc_path("GOLDILOCKS_FILTER_RESEARCH.md")),
            ("tradingview-v2-data-framework", "TradingView to V2 Data Framework", doc_path("TRADINGVIEW_V2_DATA_FRAMEWORK.md")),
            ("dataset-building-guide", "Dataset Building Guide", doc_path("DATASET_BUILDING_GUIDE.md")),
            ("microstructure-reliability", "Microstructure Reliability", doc_path("MICROSTRUCTURE_RELIABILITY.md")),
            ("development-roadmap", "Development Roadmap", doc_path("DEVELOPMENT_ROADMAP.md")),
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
        if job_type == "research-entry-gates":
            result = await asyncio.to_thread(
                run_entry_gate_research,
                path=Path(request.get("path", "BINANCE_BTCUSDT.P, 15 (2).csv")),
                symbol=str(request.get("symbol", "BTCUSDT")).upper(),
                strategy_version=str(request.get("strategy_version", "kernel_v1")),
                output_dir=self.config.research.output_dir,
                settings=optimizer_exit_settings(str(request.get("exit_profile", "runner"))),
                max_candidates=int(request.get("max_candidates", DEFAULT_GATE_CANDIDATE_CAP)),
                gate_family=str(request.get("gate_family", LEGACY_GATE_FAMILY)),
                allowed_components=tuple(request["allowed_components"]) if request.get("allowed_components") is not None else None,
                ohlcv_cache_policy=request.get("ohlcv_cache_policy"),
            )
            return {
                "output_dir": str(result.output_dir),
                "metrics_path": str(result.metrics_path),
                "grid_results_path": str(result.grid_results_path),
                "best_gate_manifest_path": str(result.best_gate_manifest_path),
                "equity_curve_path": str(result.equity_curve_path),
                "rejected_vs_accepted_path": str(result.rejected_vs_accepted_path),
            }
        if job_type == "preflight-entry-gates":
            result = await asyncio.to_thread(
                run_entry_gate_preflight,
                path=Path(request.get("path", "BINANCE_BTCUSDT.P, 15 (2).csv")),
                symbol=str(request.get("symbol", "BTCUSDT")).upper(),
                strategy_version=str(request.get("strategy_version", "kernel_v1")),
                output_dir=self.config.research.output_dir,
                gate_family=str(request.get("gate_family", LEGACY_GATE_FAMILY)),
                ohlcv_cache_policy=request.get("ohlcv_cache_policy"),
            )
            return {
                "output_dir": str(result.output_dir),
                "metrics_path": str(result.metrics_path),
                "preflight_results_path": str(result.preflight_results_path),
            }
        if job_type == "optimize-entry-gates":
            result = await asyncio.to_thread(
                run_entry_gate_optimizer,
                path=Path(request.get("path", "BINANCE_BTCUSDT.P, 15 (2).csv")),
                symbol=str(request.get("symbol", "BTCUSDT")).upper(),
                strategy_version=str(request.get("strategy_version", "kernel_v1")),
                output_dir=self.config.research.output_dir,
                max_gate_candidates=int(request.get("max_gate_candidates", DEFAULT_GATE_CANDIDATE_CAP)),
                exit_profile=str(request.get("exit_profile", "runner")),
                top_n=int(request.get("top_n", 5)),
                workers=int(request.get("workers", 1)),
                allowed_components=tuple(request["allowed_components"]) if request.get("allowed_components") is not None else None,
                gate_family=str(request.get("gate_family", LEGACY_GATE_FAMILY)),
                ohlcv_cache_policy=request.get("ohlcv_cache_policy"),
            )
            return {
                "output_dir": str(result.output_dir),
                "metrics_path": str(result.metrics_path),
                "top_results_path": str(result.top_results_path),
                "best_gate_manifest_path": str(result.best_gate_manifest_path),
                "equity_curve_path": str(result.equity_curve_path),
                "rejected_vs_accepted_path": str(result.rejected_vs_accepted_path),
            }
        raise ValueError(f"unsupported job type: {job_type}")

    def _analysis_upload_dir(self) -> Path:
        return self.config.research.output_dir / "analysis_uploads"

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
