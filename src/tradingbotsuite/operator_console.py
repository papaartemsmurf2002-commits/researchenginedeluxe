from __future__ import annotations

import asyncio
import hashlib
import json
from collections import deque
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd

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
from tradingbotsuite.promotion.stage13_readiness import build_stage13_readiness_report
from tradingbotsuite.research.data_pipeline import DATA_PIPELINE_DEFAULT_STAGE, prepare_hmm_knn_research_data
from tradingbotsuite.research.experiment_runner import run_research_experiment
from tradingbotsuite.research.workflow import build_dataset, calibrate_model_artifact, replay_eval_artifact, train_model
from tradingbotsuite.research_cycle import HistoricalResearchCycleSpec, run_historical_research_cycle
from tradingbotsuite.research_discovery.candidate_pack_bridge import (
    evaluate_discovery_candidate_pack_eligibility,
    write_discovery_candidate_pack_eligibility,
)
from tradingbotsuite.research_discovery.runner import run_discovery
from tradingbotsuite.research_discovery.spec import DiscoveryRunSpec

REPO_ROOT = Path(__file__).resolve().parents[2]

AMBIGUOUS_SAFETY_REASONS = {
    SafeModeReason.POSITION_AMBIGUITY,
    SafeModeReason.RECONCILIATION_MISMATCH,
    SafeModeReason.RECONCILIATION_STALE,
}


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _safe_operator_path_part(value: str) -> str:
    safe = "".join(char.lower() if char.isalnum() else "-" for char in str(value)).strip("-")
    return safe[:96] or "operator-job"


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

    async def shadow_diagnostics(self, symbol: str, *, limit: int = 20) -> dict[str, Any]:
        rows = await self.store.list_research_signals(symbol.upper())
        items: list[dict[str, Any]] = []
        skip_reasons: dict[str, int] = {}
        confidence_buckets: dict[str, int] = {}
        scored_count = 0
        skipped_count = 0
        accepted_count = 0
        for row in reversed(rows):
            packet = row.get("decision_packet")
            if not isinstance(packet, dict) or str(packet.get("mode")) != str(RuntimeMode.SHADOW):
                continue
            feature_snapshot = packet.get("feature_snapshot") if isinstance(packet.get("feature_snapshot"), dict) else {}
            score = feature_snapshot.get("v2_acceptance") if isinstance(feature_snapshot.get("v2_acceptance"), dict) else {}
            status = str(score.get("status") or "skipped")
            if status == "scored":
                scored_count += 1
            else:
                skipped_count += 1
            if packet.get("accepted") is True:
                accepted_count += 1
            reason = str(score.get("scoring_fallback_reason") or ("none" if status == "scored" else "missing_shadow_score"))
            if reason != "none":
                skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
            bucket = str(score.get("confidence_bucket") or packet.get("confidence_bucket") or "unscored")
            confidence_buckets[bucket] = confidence_buckets.get(bucket, 0) + 1
            items.append(
                {
                    "signal_id": row.get("signal_id"),
                    "time_ms": row.get("received_time_ms") or row.get("signal_bar_time_ms"),
                    "direction": row.get("direction"),
                    "action": packet.get("action"),
                    "accepted": bool(packet.get("accepted")),
                    "status": status,
                    "accept_probability": score.get("accept_probability"),
                    "base_probability": score.get("base_probability"),
                    "confidence_bucket": bucket,
                    "model_version": score.get("model_version") or packet.get("model_version"),
                    "calibration_version": score.get("calibration_version") or packet.get("calibration_version"),
                    "scoring_fallback_reason": score.get("scoring_fallback_reason"),
                    "observe_only": True,
                }
            )
            if len(items) >= limit:
                break
        items.sort(key=lambda item: int(item.get("time_ms") or 0), reverse=True)
        return {
            "symbol": symbol.upper(),
            "runtime_mode": str(self.config.runtime_mode),
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "operator_control_input": False,
            "live_execution_input": False,
            "summary": {
                "shadow_decision_count": len(items),
                "scored_count": scored_count,
                "skipped_count": skipped_count,
                "accepted_count": accepted_count,
                "skip_reasons": skip_reasons,
                "confidence_buckets": confidence_buckets,
            },
            "items": items,
        }

    def stage13_readiness_diagnostics(self) -> dict[str, Any]:
        readiness_dir = self.config.research.output_dir / "stage13" / "readiness"
        report_path = readiness_dir / "stage13_readiness_report.json"
        if report_path.exists():
            payload = json.loads(report_path.read_text(encoding="utf-8-sig"))
            if isinstance(payload, dict):
                payload.setdefault("report_path", str(report_path))
                payload.setdefault("research_only", True)
                payload.setdefault("observe_only", True)
                payload.setdefault("promotion_ready", False)
                payload.setdefault("operator_control_input", False)
                payload.setdefault("live_execution_input", False)
                payload.setdefault("runtime_control_input", False)
                payload.setdefault("live_canary_authorized", False)
                return payload
        report = build_stage13_readiness_report(
            manifest_paths={
                "expected_readiness_report": str(report_path),
                "expected_output_dir": str(readiness_dir),
            }
        ).to_payload()
        report["report_path"] = str(report_path)
        report["notes"] = [
            "Read-only diagnostic. Run plan-stage13-readiness to write local templates.",
            "Stage 13 execution remains blocked until paper, shadow, testnet, rollback, and approval artifacts exist.",
        ]
        return report

    def r104_readiness_diagnostics(self) -> dict[str, Any]:
        configs_root = REPO_ROOT / "configs"
        symbols = {
            "BTCUSDT": {
                "readiness_config": configs_root / "research" / "durable_public_archive_fixture_readiness_btcusdt_v1.json",
                "cycle_spec": configs_root / "research" / "full_cycle_btcusdt_durable_public_archive_r104_v1.json",
                "discovery_spec": configs_root / "discovery" / "standard_entry_discovery_btcusdt_v4.json",
            },
            "ETHUSDT": {
                "readiness_config": configs_root / "research" / "durable_public_archive_fixture_readiness_ethusdt_v1.json",
                "cycle_spec": configs_root / "research" / "full_cycle_ethusdt_durable_public_archive_r104_v1.json",
                "discovery_spec": configs_root / "discovery" / "standard_entry_discovery_ethusdt_durable_r104_v1.json",
            },
        }
        items: list[dict[str, Any]] = []
        for symbol, paths in symbols.items():
            readiness_payload = self._read_json_path(paths["readiness_config"])
            cycle_payload = self._read_json_path(paths["cycle_spec"])
            discovery_payload = self._read_json_path(paths["discovery_spec"])
            fixture_path = self._resolve_repo_path((readiness_payload or {}).get("fixture_manifest_path"))
            fixture_exists = bool(fixture_path and fixture_path.exists())
            expected_sha = str((readiness_payload or {}).get("fixture_manifest_sha256") or "")
            actual_sha = f"sha256:{self._file_sha256(fixture_path)}" if fixture_exists and fixture_path is not None else ""
            sha_ok = bool(expected_sha and actual_sha and expected_sha == actual_sha)
            ready = bool(
                readiness_payload
                and readiness_payload.get("readiness_status") == "durable_public_archive_ready"
                and readiness_payload.get("research_only") is True
                and readiness_payload.get("observe_only") is True
                and readiness_payload.get("promotion_ready") is False
                and fixture_exists
                and sha_ok
                and cycle_payload
                and discovery_payload
            )
            blockers: list[str] = []
            if not readiness_payload:
                blockers.append("durable_readiness_config_missing_or_invalid")
            if not fixture_exists:
                blockers.append("fixture_manifest_missing")
            if expected_sha and actual_sha and expected_sha != actual_sha:
                blockers.append("fixture_manifest_sha256_mismatch")
            if not cycle_payload:
                blockers.append("r104_cycle_spec_missing_or_invalid")
            if not discovery_payload:
                blockers.append("r104_discovery_spec_missing_or_invalid")
            items.append(
                {
                    "symbol": symbol,
                    "ready": ready,
                    "status": "durable_ready" if ready else "blocked",
                    "blockers": blockers,
                    "readiness_config_path": str(paths["readiness_config"]),
                    "cycle_spec_path": str(paths["cycle_spec"]),
                    "discovery_spec_path": str(paths["discovery_spec"]),
                    "fixture_manifest_path": str(fixture_path) if fixture_path is not None else None,
                    "fixture_manifest_sha256": actual_sha or None,
                    "expected_fixture_manifest_sha256": expected_sha or None,
                    "fixture_row_counts": (readiness_payload or {}).get("fixture_row_counts") or {},
                    "window_selection_recorded": (readiness_payload or {}).get("window_selection_recorded") or {},
                    "promotion_ready": False,
                    "research_only": True,
                    "observe_only": True,
                }
            )
        ready_count = sum(1 for item in items if item["ready"])
        return {
            "stage": "R104",
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "ready": ready_count == len(items),
            "ready_count": ready_count,
            "symbol_count": len(items),
            "items": items,
            "recommended_next_action": (
                "Run durable BTC or ETH historical cycle, then discovery, then candidate eligibility review."
                if ready_count == len(items)
                else "Fix durable fixture readiness before running candidate validation."
            ),
            "primary_blockers": sorted({reason for item in items for reason in item["blockers"]}),
        }

    def list_artifacts(self) -> list[dict[str, Any]]:
        base_dir = self.config.research.output_dir
        if not base_dir.exists():
            return []
        artifacts: list[dict[str, Any]] = []
        for train_manifest in sorted(base_dir.rglob("train_manifest.json")):
            payload = self._read_json_artifact(artifacts, train_manifest, "train_artifact")
            if payload is None:
                continue
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
            payload = self._read_json_artifact(artifacts, manifest_path, "artifact_manifest")
            if payload is None:
                continue
            if payload.get("artifact_manifest_version") == "v2-hmm-knn-artifact-manifest-1":
                raw_metrics_path = payload.get("metrics_path")
                metrics_path = Path(str(raw_metrics_path)) if raw_metrics_path else manifest_path.parent / "walk_forward_metrics.json"
                if not metrics_path.is_absolute():
                    parent_candidate = manifest_path.parent / metrics_path
                    metrics_path = parent_candidate if parent_candidate.exists() else metrics_path
                metrics = self._read_optional_json(metrics_path) if metrics_path.exists() else None
                monitoring_path = manifest_path.parent / "monitoring_report.json"
                monitoring = self._read_optional_json(monitoring_path) if monitoring_path.exists() else None
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
            metrics = self._read_optional_json(metrics_path) if metrics_path.exists() else None
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
            payload = self._read_json_artifact(artifacts, dataset_manifest, "dataset")
            if payload is None:
                continue
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
            payload = self._read_json_artifact(artifacts, pipeline_summary, "research_pipeline")
            if payload is None:
                continue
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
            payload = self._read_json_artifact(artifacts, intake_manifest, "data_pipeline_intake")
            if payload is None:
                continue
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
            payload = self._read_json_artifact(artifacts, data_quality_report, "data_quality_report")
            if payload is None:
                continue
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
            payload = self._read_json_artifact(artifacts, market_journal_manifest, "market_journal_manifest")
            if payload is None:
                continue
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
            payload = self._read_json_artifact(artifacts, provider_manifest, "provider_archive_manifest")
            if payload is None:
                continue
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
            payload = self._read_json_artifact(artifacts, experiment_manifest, "hmm_knn_experiment_matrix")
            if payload is None:
                continue
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
            payload = self._read_json_artifact(artifacts, experiment_run_manifest, "research_experiment_run")
            if payload is None:
                continue
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
        for cycle_manifest in sorted(base_dir.rglob("research_cycle_manifest.json")):
            payload = self._read_json_artifact(artifacts, cycle_manifest, "historical_research_cycle")
            if payload is None:
                continue
            required_outputs = payload.get("required_outputs") if isinstance(payload.get("required_outputs"), dict) else {}
            compute_policy = payload.get("compute_policy") if isinstance(payload.get("compute_policy"), dict) else {}
            backend_summary = payload.get("backtest_backend_summary") if isinstance(payload.get("backtest_backend_summary"), dict) else {}
            rankings_summary = self._summarize_research_cycle_rankings(required_outputs.get("candidate_rankings"))
            gate_summary = self._summarize_research_cycle_gate_report(required_outputs.get("candidate_gate_report"))
            holding_summary = self._summarize_research_cycle_holding_windows(required_outputs.get("metrics_by_holding_window"))
            artifacts.append(
                {
                    "type": "historical_research_cycle",
                    "path": str(cycle_manifest),
                    "sort_time": cycle_manifest.stat().st_mtime,
                    "manifest": payload,
                    "summary": {
                        "cycle_id": payload.get("cycle_id"),
                        "symbol": payload.get("symbol"),
                        "candidate_count": payload.get("candidate_count"),
                        "candidate_search_mode": payload.get("candidate_search_mode"),
                        "candidate_search_method": payload.get("candidate_search_method"),
                        "aggregate_backtest_count": payload.get("aggregate_backtest_count"),
                        "split_backtest_count": payload.get("split_backtest_count"),
                        "cost_stress_backtest_count": payload.get("cost_stress_backtest_count"),
                        "candidate_pack_written": payload.get("candidate_pack_written"),
                        "candidate_acceptance_scope": payload.get("candidate_acceptance_scope"),
                        "backtest_backend_requested": payload.get("backtest_backend_requested"),
                        "backtest_backend_used_counts": backend_summary.get("used_counts") or {},
                        "compute_profile": compute_policy.get("gpu_execution_profile"),
                        "compute_cpu_threads": compute_policy.get("cpu_threads"),
                        "aggregate_backtest_workers_used": compute_policy.get("aggregate_backtest_workers_used"),
                        "gpu_execution_status": compute_policy.get("gpu_execution_status"),
                        "selected_cuda_backend": compute_policy.get("selected_cuda_backend"),
                        "cuda_runtime_checked": compute_policy.get("cuda_runtime_checked"),
                        "r97_batched_cuda_requested": compute_policy.get("r97_batched_cuda_requested"),
                        "tensorcore_screening_requested": compute_policy.get("tensorcore_screening_requested"),
                        "runtime_seconds": ((payload.get("runtime") or {}).get("elapsed_seconds")),
                        "data_source_type": ((payload.get("data_source") or {}).get("source_type")),
                        "research_only": payload.get("research_only"),
                        "observe_only": payload.get("observe_only"),
                        "promotion_ready": payload.get("promotion_ready"),
                        "rankings": rankings_summary,
                        "gate_report": gate_summary,
                        "holding_windows": holding_summary,
                    },
                }
            )
        for discovery_manifest in sorted(base_dir.rglob("discovery_run_manifest.json")):
            payload = self._read_json_artifact(artifacts, discovery_manifest, "discovery_run")
            if payload is None:
                continue
            required_outputs = payload.get("required_outputs") if isinstance(payload.get("required_outputs"), dict) else {}
            artifacts.append(
                {
                    "type": "discovery_run",
                    "path": str(discovery_manifest),
                    "sort_time": discovery_manifest.stat().st_mtime,
                    "manifest": payload,
                    "summary": {
                        "run_id": payload.get("run_id"),
                        "symbol": payload.get("symbol"),
                        "timeframe": payload.get("timeframe"),
                        "discovery_mode": payload.get("discovery_mode"),
                        "status": ((payload.get("state") or {}).get("status")),
                        "message": ((payload.get("state") or {}).get("message")),
                        "completed_trial_count": len(((payload.get("state") or {}).get("completed_trial_ids") or [])),
                        "failed_trial_count": len(((payload.get("state") or {}).get("failed_trial_ids") or [])),
                        "snapshot_count": ((payload.get("state") or {}).get("snapshot_count")),
                        "last_snapshot_path": ((payload.get("state") or {}).get("last_snapshot_path")),
                        "budget_max_trials": ((payload.get("budget") or {}).get("max_trials")),
                        "candidate_pack_written": payload.get("candidate_pack_written"),
                        "candidate_acceptance_scope": payload.get("candidate_acceptance_scope"),
                        "runtime_seconds": ((payload.get("runtime") or {}).get("elapsed_seconds")),
                        "research_only": payload.get("research_only"),
                        "observe_only": payload.get("observe_only"),
                        "promotion_ready": payload.get("promotion_ready"),
                        "counts": payload.get("counts") or {},
                        "interesting_candidates": self._summarize_discovery_ledger(required_outputs.get("interesting_candidates")),
                        "blocked_candidates": self._summarize_discovery_ledger(required_outputs.get("blocked_candidates")),
                        "filter_blockers": self._summarize_discovery_ledger(required_outputs.get("filter_blockers")),
                        "latest_snapshot": self._summarize_discovery_snapshot(required_outputs.get("snapshots")),
                    },
                }
            )
        for exit_lab_manifest in sorted(base_dir.rglob("discovery_exit_lab_manifest.json")):
            payload = self._read_json_artifact(artifacts, exit_lab_manifest, "discovery_exit_lab")
            if payload is None:
                continue
            outputs = payload.get("required_outputs") if isinstance(payload.get("required_outputs"), dict) else {}
            artifacts.append(
                {
                    "type": "discovery_exit_lab",
                    "path": str(exit_lab_manifest),
                    "sort_time": exit_lab_manifest.stat().st_mtime,
                    "manifest": payload,
                    "summary": {
                        "input_ranking_row_count": payload.get("input_ranking_row_count"),
                        "comparison_count": payload.get("comparison_count"),
                        "candidate_gate_row_count": payload.get("candidate_gate_row_count"),
                        "decision_counts": payload.get("decision_counts") or {},
                        "promotion_ready": payload.get("promotion_ready"),
                        "candidate_gates": self._summarize_gate_artifact(outputs.get("discovery_exit_lab_candidate_gates")),
                    },
                }
            )
        for multiple_testing_manifest in sorted(base_dir.rglob("discovery_multiple_testing_manifest.json")):
            payload = self._read_json_artifact(artifacts, multiple_testing_manifest, "discovery_multiple_testing")
            if payload is None:
                continue
            outputs = payload.get("required_outputs") if isinstance(payload.get("required_outputs"), dict) else {}
            artifacts.append(
                {
                    "type": "discovery_multiple_testing",
                    "path": str(multiple_testing_manifest),
                    "sort_time": multiple_testing_manifest.stat().st_mtime,
                    "manifest": payload,
                    "summary": {
                        "input_candidate_row_count": payload.get("input_candidate_row_count"),
                        "candidate_gate_row_count": payload.get("candidate_gate_row_count"),
                        "summary": payload.get("summary") or {},
                        "promotion_ready": payload.get("promotion_ready"),
                        "candidate_gates": self._summarize_gate_artifact(outputs.get("discovery_multiple_testing_candidate_gates")),
                    },
                }
            )
        for validation_floors_manifest in sorted(base_dir.rglob("discovery_validation_floors_manifest.json")):
            payload = self._read_json_artifact(artifacts, validation_floors_manifest, "discovery_validation_floors")
            if payload is None:
                continue
            outputs = payload.get("required_outputs") if isinstance(payload.get("required_outputs"), dict) else {}
            artifacts.append(
                {
                    "type": "discovery_validation_floors",
                    "path": str(validation_floors_manifest),
                    "sort_time": validation_floors_manifest.stat().st_mtime,
                    "manifest": payload,
                    "summary": {
                        "input_candidate_row_count": payload.get("input_candidate_row_count"),
                        "candidate_gate_row_count": payload.get("candidate_gate_row_count"),
                        "summary": payload.get("summary") or {},
                        "experiment_budget_ledger": payload.get("experiment_budget_ledger") or {},
                        "promotion_ready": payload.get("promotion_ready"),
                        "candidate_gates": self._summarize_gate_artifact(outputs.get("discovery_validation_floor_candidate_gates")),
                    },
                }
            )
        for bridge_manifest in sorted(base_dir.rglob("candidate_pack_eligibility_manifest.json")):
            payload = self._read_json_artifact(artifacts, bridge_manifest, "candidate_pack_eligibility")
            if payload is None:
                continue
            outputs = payload.get("required_outputs") if isinstance(payload.get("required_outputs"), dict) else {}
            artifacts.append(
                {
                    "type": "candidate_pack_eligibility",
                    "path": str(bridge_manifest),
                    "sort_time": bridge_manifest.stat().st_mtime,
                    "manifest": payload,
                    "summary": {
                        "bridge_scope": payload.get("bridge_scope"),
                        "claim_scope": payload.get("claim_scope"),
                        "summary": payload.get("summary") or {},
                        "global_reasons": payload.get("global_reasons") or [],
                        "candidate_pack_written": payload.get("candidate_pack_written"),
                        "promotion_ready": payload.get("promotion_ready"),
                        "eligibility": self._summarize_gate_artifact(outputs.get("candidate_pack_eligibility")),
                    },
                }
            )
        artifacts.sort(key=lambda item: float(item.get("sort_time") or 0.0), reverse=True)
        for artifact in artifacts:
            artifact.pop("sort_time", None)
        return artifacts

    def _read_json_artifact(self, artifacts: list[dict[str, Any]], path: Path, artifact_type: str) -> dict[str, Any] | None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            artifacts.append(self._artifact_read_error(path, artifact_type, exc))
            return None
        if not isinstance(payload, dict):
            artifacts.append(self._artifact_read_error(path, artifact_type, ValueError("JSON artifact must be an object")))
            return None
        return payload

    def _artifact_read_error(self, path: Path, artifact_type: str, exc: Exception) -> dict[str, Any]:
        sort_time = path.stat().st_mtime if path.exists() else 0.0
        return {
            "type": "artifact_read_error",
            "path": str(path),
            "sort_time": sort_time,
            "manifest": {},
            "summary": {
                "intended_type": artifact_type,
                "error": str(exc),
                "promotion_ready": False,
                "research_only": True,
                "observe_only": True,
            },
        }

    def _read_optional_json(self, path: Path) -> dict[str, Any] | None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return None
        return payload if isinstance(payload, dict) else None

    def _read_json_path(self, path: Path) -> dict[str, Any] | None:
        return self._read_optional_json(path) if path.exists() else None

    def _resolve_repo_path(self, raw_path: object) -> Path | None:
        if raw_path is None or str(raw_path).strip() == "":
            return None
        path = Path(str(raw_path)).expanduser()
        return path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()

    def _file_sha256(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _summarize_gate_artifact(self, raw_path: object) -> dict[str, Any]:
        path = self._existing_path(raw_path)
        if path is None:
            return {"available": False, "reason": "gate_artifact_missing"}
        try:
            frame = pd.read_parquet(path)
        except Exception as exc:
            return {"available": False, "path": str(path), "reason": str(exc)}
        reason_columns = [
            column
            for column in (
                "bridge_reasons",
                "validation_floor_reasons",
                "multiple_testing_reasons",
                "exit_lab_reasons",
                "gate_reasons",
                "blocker_code",
                "filter_blocker_code",
            )
            if column in frame
        ]
        reasons: dict[str, int] = {}
        for column in reason_columns:
            for value in frame[column].fillna("").astype(str):
                for reason in [item for item in value.replace(",", "|").split("|") if item]:
                    reasons[reason] = reasons.get(reason, 0) + 1
        return {
            "available": True,
            "path": str(path),
            "row_count": int(len(frame)),
            "status_counts": self._value_counts(frame, "bridge_status") or self._value_counts(frame, "gate_status") or self._value_counts(frame, "status"),
            "eligible_count": int(frame.get("eligible_for_existing_candidate_pack_validator", pd.Series(dtype=bool)).fillna(False).astype(bool).sum()) if "eligible_for_existing_candidate_pack_validator" in frame else None,
            "top_reasons": dict(sorted(reasons.items(), key=lambda item: (-item[1], item[0]))[:8]),
        }

    def _summarize_discovery_ledger(self, raw_path: object) -> dict[str, Any]:
        path = self._existing_path(raw_path)
        if path is None:
            return {"available": False, "reason": "ledger_missing"}
        try:
            frame = pd.read_parquet(path)
        except Exception as exc:
            return {"available": False, "path": str(path), "reason": str(exc)}
        rows: list[dict[str, Any]] = []
        sort_frame = frame.sort_values("score", ascending=False, kind="mergesort") if "score" in frame else frame
        for row in sort_frame.head(8).to_dict("records"):
            rows.append(
                {
                    "trial_id": str(row.get("trial_id", "")),
                    "candidate_id": str(row.get("candidate_id", "")),
                    "candidate_family": str(row.get("candidate_family", "")),
                    "ledger_kind": str(row.get("ledger_kind", "")),
                    "score": self._float_or_none(row.get("score")),
                    "blocker_code": str(row.get("blocker_code", "")),
                    "filter_blocker_code": str(row.get("filter_blocker_code", "")),
                    "promotion_ready": bool(row.get("promotion_ready")) if "promotion_ready" in row else False,
                }
            )
        return {
            "available": True,
            "path": str(path),
            "row_count": int(len(frame)),
            "candidate_family_counts": self._value_counts(frame, "candidate_family"),
            "blocker_counts": self._value_counts(frame, "blocker_code"),
            "filter_blocker_counts": self._value_counts(frame, "filter_blocker_code"),
            "rows": rows,
        }

    def _summarize_discovery_snapshot(self, raw_path: object) -> dict[str, Any]:
        path = self._existing_path(raw_path)
        if path is None:
            return {"available": False, "reason": "snapshot_dir_missing"}
        snapshot_dir = path if path.is_dir() else path.parent
        snapshots = sorted(snapshot_dir.glob("*_snapshot.json"))
        if not snapshots:
            return {"available": False, "path": str(snapshot_dir), "reason": "no_snapshots"}
        latest = snapshots[-1]
        try:
            payload = json.loads(latest.read_text(encoding="utf-8"))
        except Exception as exc:
            return {"available": False, "path": str(latest), "reason": str(exc)}
        return {
            "available": True,
            "path": str(latest),
            "created_at_utc": payload.get("created_at_utc"),
            "summary": payload.get("summary") or {},
        }

    def _summarize_research_cycle_rankings(self, raw_path: object) -> dict[str, Any]:
        path = self._existing_path(raw_path)
        if path is None:
            return {"available": False, "reason": "candidate_rankings_missing"}
        try:
            frame = pd.read_parquet(path)
        except Exception as exc:
            return {"available": False, "path": str(path), "reason": str(exc)}
        if frame.empty:
            return {"available": True, "path": str(path), "candidate_count": 0, "top_candidates": []}
        sorted_frame = frame.sort_values(["final_score", "trade_count"], ascending=[False, False], kind="mergesort") if "final_score" in frame else frame
        top_candidates: list[dict[str, Any]] = []
        for row in sorted_frame.head(12).to_dict("records"):
            top_candidates.append(
                {
                    "candidate_id": str(row.get("candidate_id", "")),
                    "strategy_id": str(row.get("strategy_id", "")),
                    "feature_set_id": str(row.get("feature_set_id", "")),
                    "holding_window": str(row.get("holding_window", "")),
                    "exit_policy_id": str(row.get("exit_policy_id", "")),
                    "decision": str(row.get("decision", "")),
                    "final_score": self._float_or_none(row.get("final_score")),
                    "costed_expectancy": self._float_or_none(row.get("costed_expectancy")),
                    "net_return_after_fees_slippage_funding": self._float_or_none(row.get("net_return_after_fees_slippage_funding")),
                    "max_drawdown": self._float_or_none(row.get("max_drawdown")),
                    "profit_factor": self._float_or_none(row.get("profit_factor")),
                    "trade_count": self._int_or_none(row.get("trade_count")),
                    "failure_reasons": str(row.get("failure_reasons", "")),
                }
            )
        return {
            "available": True,
            "path": str(path),
            "candidate_count": int(len(frame)),
            "decision_counts": self._value_counts(frame, "decision"),
            "strategy_counts": self._value_counts(frame, "strategy_id"),
            "feature_set_counts": self._value_counts(frame, "feature_set_id"),
            "exit_policy_counts": self._value_counts(frame, "exit_policy_id"),
            "best_final_score": self._float_or_none(frame["final_score"].max()) if "final_score" in frame else None,
            "best_costed_expectancy": self._float_or_none(frame["costed_expectancy"].max()) if "costed_expectancy" in frame else None,
            "best_net_return": self._float_or_none(frame["net_return_after_fees_slippage_funding"].max()) if "net_return_after_fees_slippage_funding" in frame else None,
            "worst_drawdown": self._float_or_none(frame["max_drawdown"].min()) if "max_drawdown" in frame else None,
            "top_candidates": top_candidates,
        }

    def _summarize_research_cycle_gate_report(self, raw_path: object) -> dict[str, Any]:
        path = self._existing_path(raw_path)
        if path is None:
            return {"available": False, "reason": "candidate_gate_report_missing"}
        try:
            frame = pd.read_parquet(path)
        except Exception as exc:
            return {"available": False, "path": str(path), "reason": str(exc)}
        return {
            "available": True,
            "path": str(path),
            "row_count": int(len(frame)),
            "acceptance_scope_counts": self._value_counts(frame, "candidate_acceptance_scope"),
            "decision_counts": self._value_counts(frame, "decision"),
            "passed_count": int(pd.to_numeric(frame.get("gate_passed", pd.Series(dtype=bool)), errors="coerce").fillna(False).astype(bool).sum()) if "gate_passed" in frame else None,
        }

    def _summarize_research_cycle_holding_windows(self, raw_path: object) -> dict[str, Any]:
        path = self._existing_path(raw_path)
        if path is None:
            return {"available": False, "reason": "metrics_by_holding_window_missing"}
        try:
            frame = pd.read_parquet(path)
        except Exception as exc:
            return {"available": False, "path": str(path), "reason": str(exc)}
        rows: list[dict[str, Any]] = []
        for row in frame.to_dict("records"):
            rows.append(
                {
                    "holding_window": str(row.get("holding_window", "")),
                    "candidate_count": self._int_or_none(row.get("candidate_count")),
                    "holding_window_trade_count": self._int_or_none(row.get("holding_window_trade_count")),
                    "median_costed_expectancy": self._float_or_none(row.get("median_costed_expectancy")),
                    "best_final_score": self._float_or_none(row.get("best_final_score")),
                }
            )
        return {"available": True, "path": str(path), "rows": rows}

    def _existing_path(self, raw_path: object) -> Path | None:
        if not raw_path:
            return None
        path = Path(str(raw_path))
        if not path.is_absolute():
            path = (self.config.research.output_dir / path).resolve()
        return path if path.exists() else None

    def _value_counts(self, frame: pd.DataFrame, column: str) -> dict[str, int]:
        if column not in frame:
            return {}
        return {str(key): int(value) for key, value in frame[column].fillna("missing").astype(str).value_counts().sort_index().items()}

    def _float_or_none(self, value: object) -> float | None:
        try:
            numeric = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None
        if pd.isna(numeric):
            return None
        return numeric

    def _int_or_none(self, value: object) -> int | None:
        try:
            if pd.isna(value):
                return None
            return int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None

    def list_guide_documents(self) -> list[dict[str, Any]]:
        root = Path(__file__).resolve().parents[2]
        runtime_docs_root = root / "docs" / "tradingbotsuite_runtime"

        def doc_path(name: str) -> Path:
            current_path = root / "docs" / name
            if current_path.exists():
                return current_path
            runtime_path = runtime_docs_root / name
            if runtime_path.exists():
                return runtime_path
            return current_path

        docs = [
            ("operator-quickstart", "Operator Quickstart", doc_path("OPERATOR_QUICKSTART.md")),
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
        if job_type == "run-historical-research-cycle":
            result = await asyncio.to_thread(
                self._run_isolated_historical_research_cycle,
                Path(str(request["spec_path"])),
                job_id,
            )
            return result
        if job_type == "run-discovery":
            result = await asyncio.to_thread(
                self._run_isolated_discovery,
                Path(str(request["spec_path"])),
                job_id,
                bool(request.get("resume", False)),
                self._positive_int_or_none(request.get("stop_after_trials")),
            )
            return result
        if job_type == "evaluate-discovery-candidate-pack-eligibility":
            return await asyncio.to_thread(
                self._run_isolated_discovery_candidate_pack_eligibility,
                request,
                job_id,
            )
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

    def _run_isolated_historical_research_cycle(self, spec_path: Path, job_id: str) -> dict[str, Any]:
        resolved_spec_path = Path(spec_path).expanduser().resolve()
        spec = HistoricalResearchCycleSpec.from_path(resolved_spec_path)
        research_root = self._research_root()
        safe_job_id = _safe_operator_path_part(job_id)
        safe_cycle_id = _safe_operator_path_part(spec.cycle_id)
        output_dir = (research_root / "operator_runs" / "historical_cycles" / safe_cycle_id / safe_job_id).resolve()
        if not _is_relative_to(output_dir, research_root):
            raise ValueError("historical cycle output_dir must stay inside the configured research output directory")
        if output_dir.exists() and any(output_dir.iterdir()):
            raise ValueError(f"historical cycle output_dir already contains files: {output_dir}")

        isolated_spec_dir = (research_root / "operator_runs" / "cycle_specs" / safe_job_id).resolve()
        if not _is_relative_to(isolated_spec_dir, research_root):
            raise ValueError("historical cycle resolved spec path must stay inside the configured research output directory")
        isolated_spec_dir.mkdir(parents=True, exist_ok=False)
        isolated_spec_path = isolated_spec_dir / "cycle_spec.json"
        isolated_payload = spec.to_payload()
        isolated_payload["output_dir"] = str(output_dir)
        isolated_payload["operator_job_id"] = job_id
        isolated_payload["operator_original_spec_path"] = str(resolved_spec_path)
        isolated_payload["operator_overwrite_protection"] = "isolated_output_dir"
        isolated_spec_path.write_text(json.dumps(isolated_payload, indent=2, sort_keys=True), encoding="utf-8")

        result = run_historical_research_cycle(
            spec_path=isolated_spec_path,
            app_config=self.config,
        )
        return {
            "output_dir": str(result.output_dir),
            "isolated_spec_path": str(isolated_spec_path),
            "source_spec_path": str(resolved_spec_path),
            "overwrite_protection": "isolated_output_dir",
            "research_cycle_manifest_path": str(result.manifest_path),
            "candidate_rankings_path": str(result.candidate_rankings_path),
            "backtest_index_path": str(result.backtest_index_path),
            "rejection_report_path": str(result.rejection_report_path),
        }

    def _run_isolated_discovery(
        self,
        spec_path: Path,
        job_id: str,
        resume: bool,
        stop_after_trials: int | None,
    ) -> dict[str, Any]:
        resolved_spec_path = Path(spec_path).expanduser().resolve()
        spec = DiscoveryRunSpec.from_path(resolved_spec_path)
        research_root = self._research_root()
        safe_job_id = _safe_operator_path_part(job_id)
        safe_run_id = _safe_operator_path_part(spec.run_id)
        if resume or stop_after_trials is not None:
            output_dir = (research_root / "operator_runs" / "discovery_runs" / safe_run_id).resolve()
            overwrite_protection = "resume_stable_run_id_output_dir" if resume else "pauseable_stable_run_id_output_dir"
        else:
            output_dir = (research_root / "operator_runs" / "discovery_runs" / safe_run_id / safe_job_id).resolve()
            overwrite_protection = "isolated_job_output_dir"
        if not _is_relative_to(output_dir, research_root):
            raise ValueError("discovery output_dir must stay inside the configured research output directory")

        isolated_spec_dir = (research_root / "operator_runs" / "discovery_specs" / safe_run_id / safe_job_id).resolve()
        if not _is_relative_to(isolated_spec_dir, research_root):
            raise ValueError("discovery resolved spec path must stay inside the configured research output directory")
        isolated_spec_dir.mkdir(parents=True, exist_ok=False)
        isolated_spec_path = isolated_spec_dir / "discovery_spec.json"
        isolated_payload = spec.to_payload()
        isolated_payload["research_output_dir"] = str(research_root)
        isolated_payload["output_dir"] = str(output_dir)
        isolated_payload["operator_job_id"] = job_id
        isolated_payload["operator_original_spec_path"] = str(resolved_spec_path)
        isolated_payload["operator_overwrite_protection"] = overwrite_protection
        isolated_spec_path.write_text(json.dumps(isolated_payload, indent=2, sort_keys=True), encoding="utf-8")

        result = run_discovery(
            spec_path=isolated_spec_path,
            app_config=self.config,
            resume=resume,
            stop_after_trials=stop_after_trials,
        )
        return {
            "output_dir": str(result.output_dir),
            "isolated_spec_path": str(isolated_spec_path),
            "source_spec_path": str(resolved_spec_path),
            "overwrite_protection": overwrite_protection,
            "resume": resume,
            "stop_after_trials": stop_after_trials,
            "discovery_run_manifest_path": str(result.manifest_path),
            "run_state_path": str(result.run_state_path),
            "interesting_candidates_path": str(result.interesting_candidates_path),
            "blocked_candidates_path": str(result.blocked_candidates_path),
            "filter_blockers_path": str(result.filter_blockers_path),
            "snapshot_count": len(result.snapshot_paths),
        }

    def _run_isolated_discovery_candidate_pack_eligibility(
        self,
        request: dict[str, Any],
        job_id: str,
    ) -> dict[str, Any]:
        research_root = self._research_root()
        safe_job_id = _safe_operator_path_part(job_id)
        output_dir = (research_root / "operator_runs" / "candidate_pack_eligibility" / safe_job_id).resolve()
        if not _is_relative_to(output_dir, research_root):
            raise ValueError("candidate-pack eligibility output_dir must stay inside the configured research output directory")
        if output_dir.exists() and any(output_dir.iterdir()):
            raise ValueError(f"candidate-pack eligibility output_dir already contains files: {output_dir}")

        def optional_path(field: str) -> Path | None:
            raw = request.get(field)
            return Path(str(raw)).expanduser().resolve() if raw else None

        result = evaluate_discovery_candidate_pack_eligibility(
            discovery_manifest_path=Path(str(request["discovery_manifest_path"])).expanduser().resolve(),
            cycle_manifest_path=optional_path("cycle_manifest_path"),
            exit_lab_manifest_path=optional_path("exit_lab_manifest_path"),
            multiple_testing_manifest_path=optional_path("multiple_testing_manifest_path"),
            validation_floors_manifest_path=optional_path("validation_floors_manifest_path"),
            candidate_id_map=request.get("candidate_id_map") if isinstance(request.get("candidate_id_map"), dict) else None,
        )
        artifact = write_discovery_candidate_pack_eligibility(output_dir=output_dir, result=result)
        eligible_count = int(result.eligibility["eligible_for_existing_candidate_pack_validator"].sum()) if not result.eligibility.empty else 0
        return {
            "output_dir": str(artifact.output_dir),
            "candidate_pack_eligibility_manifest_path": str(artifact.manifest_path),
            "candidate_pack_eligibility_path": str(artifact.eligibility_path),
            "candidate_pack_bridge_rejections_path": str(artifact.rejections_path),
            "eligible_count": eligible_count,
            "row_count": int(len(result.eligibility)),
            "candidate_pack_written": False,
            "promotion_ready": False,
            "research_only": True,
            "observe_only": True,
        }

    def _positive_int_or_none(self, value: object) -> int | None:
        if value is None or str(value).strip() == "":
            return None
        parsed = int(value)  # type: ignore[arg-type]
        if parsed <= 0:
            raise ValueError("stop_after_trials must be positive when supplied")
        return parsed

    def _research_root(self) -> Path:
        path = Path(self.config.research.output_dir).expanduser()
        if path.is_absolute():
            return path.resolve()
        return (REPO_ROOT / path).resolve()

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
