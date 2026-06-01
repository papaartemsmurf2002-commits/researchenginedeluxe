from __future__ import annotations

import asyncio
import hashlib
import json
import os
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

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
from tradingbotsuite.data.durable_public_archive import (
    DEFAULT_DURABLE_COLLECTION_END_MONTH,
    DEFAULT_DURABLE_COLLECTION_START_MONTH,
    DEFAULT_DURABLE_COLLECTION_SYMBOLS,
    collect_candidate_depth_public_archive_fixtures,
)
from tradingbotsuite.data.historical_data_catalog import (
    DEFAULT_HISTORICAL_CATALOG_START_MONTH,
    default_historical_catalog_end_month,
    historical_data_provider_states,
    normalize_operator_run_artifact_paths,
    read_historical_data_catalog,
    refresh_historical_data_catalog,
)
from tradingbotsuite.promotion.stage13_readiness import build_stage13_readiness_report
from tradingbotsuite.research.data_pipeline import DATA_PIPELINE_DEFAULT_STAGE, prepare_hmm_knn_research_data
from tradingbotsuite.research.experiment_runner import run_research_experiment
from tradingbotsuite.research.workflow import build_dataset, calibrate_model_artifact, replay_eval_artifact, train_model
from tradingbotsuite.research_cycle import (
    HistoricalResearchCycleSpec,
    run_historical_research_cycle,
    write_hardware_utilization_report,
)
from tradingbotsuite.research_discovery.candidate_pack_bridge import (
    DISCOVERY_CANDIDATE_PACK_BRIDGE_VERSION,
    DISCOVERY_CANDIDATE_PACK_ELIGIBILITY_VERSION,
    evaluate_discovery_candidate_pack_eligibility,
    validate_discovery_candidate_pack_bridge_manifest,
    write_discovery_candidate_pack_eligibility,
)
from tradingbotsuite.research_discovery.analysis_report import write_research_analysis_artifacts
from tradingbotsuite.research_discovery.frozen_entry_exit_lab import write_frozen_entry_exit_lab_artifacts
from tradingbotsuite.research_discovery.runner import run_discovery
from tradingbotsuite.research_discovery.run_deltas import write_research_analysis_delta_artifacts
from tradingbotsuite.research_discovery.spec import DiscoveryRunSpec

REPO_ROOT = Path(__file__).resolve().parents[2]
CANDIDATE_READY_PRIMARY_15M_MIN_BARS = 365 * 24 * 4
CANDIDATE_READY_CONTEXT_1M_MIN_ROWS = 365 * 24 * 60
CANDIDATE_READY_MIN_EFFECTIVE_HOURS = 365 * 24
CYCLE_COST_STRESS_SCENARIO_COUNT = 11
DEEP_CYCLE_MIN_MATERIALIZED_CANDIDATES = 63
RESEARCH_AUTOPILOT_VERSION = "r106-research-autopilot-v1"
RESEARCH_AUTOPILOT_DEFAULT_STEP_ATTEMPTS = 2
RESEARCH_AUTOPILOT_MAX_STEP_ATTEMPTS = 5
RESEARCH_AUTOPILOT_MAX_STALE_RECOVERY_ATTEMPTS = 1
RESEARCH_AUTOPILOT_STEP_ESTIMATES_SECONDS = {
    "historical_data_catalog": 3600,
    "historical_cycle": 7200,
    "exact_discovery": 86400,
    "research_analysis": 90,
    "research_analysis_delta": 45,
    "frozen_entry_exit_lab": 180,
    "candidate_eligibility": 30,
}
RESEARCH_AUTOPILOT_STALE_MANIFEST_SECONDS = 900

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
    _ARTIFACT_SCAN_SKIP_DIRS = {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        "__pycache__",
        "aggregate_backtests",
        "backtests",
        "cache",
        "chart_ohlcv_cache",
        "cost_stress_backtests",
        "data",
        "feature_cache",
        "feature_frames",
        "features",
        "fixtures",
        "market_data",
        "snapshots",
        "split_backtests",
        "trial_artifacts",
        "trials",
    }
    _ARTIFACT_SCAN_MAX_MATCHES_PER_PATTERN = 500

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
            await self._recover_interrupted_running_jobs()
            self._job_task = asyncio.create_task(self._job_loop())

    async def shutdown(self) -> None:
        self._stop_event.set()
        if self._job_task is not None:
            self._job_task.cancel()
            try:
                await self._job_task
            except asyncio.CancelledError:
                pass

    async def _recover_interrupted_running_jobs(self) -> None:
        now_ms = self.engine.clock()
        for job in await self.store.list_operator_jobs():
            if job.get("status") != "running":
                continue
            job_id = str(job.get("job_id") or "")
            if not job_id:
                continue
            await self.store.complete_operator_job(
                job_id=job_id,
                status="failed",
                finished_at_ms=now_ms,
                error_text="stale_running_job_recovered_after_operator_restart",
            )
            await self.store.append_operator_job_log(
                job_id=job_id,
                time_ms=now_ms,
                level="error",
                message="stale running job recovered after operator restart",
                payload={"previous_status": "running"},
            )
            if str(job.get("job_type") or "") != "run-research-autopilot":
                continue
            request = dict(job.get("request") or {})
            if request.get("auto_requeue_on_restart") is False:
                continue
            stale_attempt = self._nonnegative_int(request.get("_stale_recovery_attempt"))
            if stale_attempt >= RESEARCH_AUTOPILOT_MAX_STALE_RECOVERY_ATTEMPTS:
                continue
            retry_attempt = stale_attempt + 1
            retry_job_id = f"{job_id}-restart-retry-{retry_attempt}"
            retry_request = dict(request)
            retry_request["_stale_recovery_attempt"] = retry_attempt
            retry_request["recovered_from_job_id"] = job_id
            retry_request["recovered_from_started_at_ms"] = job.get("started_at_ms")
            await self.store.queue_operator_job(
                job_id=retry_job_id,
                job_type="run-research-autopilot",
                requested_at_ms=now_ms + retry_attempt,
                request=retry_request,
            )
            await self.store.append_operator_job_log(
                job_id=job_id,
                time_ms=now_ms,
                level="info",
                message="stale autopilot job requeued for automatic restart retry",
                payload={"retry_job_id": retry_job_id, "retry_attempt": retry_attempt},
            )

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
        try:
            rows = await self.store.list_research_signals(symbol.upper())
        except Exception as exc:
            return {
                "summary": {
                    "shadow_decision_count": 0,
                    "scored_count": 0,
                    "skipped_count": 0,
                    "accepted_count": 0,
                    "skip_reasons": {},
                    "confidence_buckets": {},
                    "available": False,
                    "error": str(exc),
                },
                "items": [],
            }
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
                "cycle_spec": configs_root / "research" / "full_cycle_btcusdt_durable_public_archive_r104_deep_v1.json",
                "standard_cycle_spec": configs_root / "research" / "full_cycle_btcusdt_durable_public_archive_r104_v1.json",
                "discovery_spec": configs_root / "discovery" / "exact_entry_sweep_btcusdt_durable_r104_v1.json",
                "standard_discovery_spec": configs_root / "discovery" / "standard_entry_discovery_btcusdt_durable_r104_v1.json",
            },
            "ETHUSDT": {
                "readiness_config": configs_root / "research" / "durable_public_archive_fixture_readiness_ethusdt_v1.json",
                "cycle_spec": configs_root / "research" / "full_cycle_ethusdt_durable_public_archive_r104_deep_v1.json",
                "standard_cycle_spec": configs_root / "research" / "full_cycle_ethusdt_durable_public_archive_r104_v1.json",
                "discovery_spec": configs_root / "discovery" / "exact_entry_sweep_ethusdt_durable_r104_v1.json",
                "standard_discovery_spec": configs_root / "discovery" / "standard_entry_discovery_ethusdt_durable_r104_v1.json",
            },
        }
        active_readiness = self._latest_historical_data_catalog_readiness_by_symbol()
        if not active_readiness:
            active_readiness = self._latest_durable_collection_readiness_by_symbol()
        items: list[dict[str, Any]] = []
        for symbol, paths in symbols.items():
            active_paths = active_readiness.get(symbol) or {}
            if active_paths:
                merged_paths = dict(paths)
                for key in ("readiness_config", "cycle_spec", "discovery_spec"):
                    raw_path = active_paths.get(f"{key}_path")
                    if raw_path:
                        merged_paths[key] = Path(str(raw_path)).expanduser().resolve()
                paths = merged_paths
            readiness_payload = self._read_json_path(paths["readiness_config"])
            cycle_payload = self._read_json_path(paths["cycle_spec"])
            standard_cycle_payload = self._read_json_path(paths["standard_cycle_spec"])
            discovery_payload = self._read_json_path(paths["discovery_spec"])
            standard_discovery_payload = self._read_json_path(paths["standard_discovery_spec"])
            fixture_path = self._resolve_repo_path((readiness_payload or {}).get("fixture_manifest_path"))
            fixture_exists = bool(fixture_path and fixture_path.exists())
            expected_sha = str((readiness_payload or {}).get("fixture_manifest_sha256") or "")
            actual_sha = f"sha256:{self._file_sha256(fixture_path)}" if fixture_exists and fixture_path is not None else ""
            sha_ok = bool(expected_sha and actual_sha and expected_sha == actual_sha)
            fixture_integrity_ready = bool(
                readiness_payload
                and readiness_payload.get("readiness_status") == "durable_public_archive_ready"
                and readiness_payload.get("research_only") is True
                and readiness_payload.get("observe_only") is True
                and readiness_payload.get("promotion_ready") is False
                and fixture_exists
                and sha_ok
                and cycle_payload
                and standard_cycle_payload
                and discovery_payload
                and standard_discovery_payload
            )
            blockers: list[str] = []
            if not readiness_payload:
                blockers.append("durable_readiness_config_missing_or_invalid")
            if not fixture_exists:
                blockers.append("fixture_manifest_missing")
            if expected_sha and actual_sha and expected_sha != actual_sha:
                blockers.append("fixture_manifest_sha256_mismatch")
            if not cycle_payload:
                blockers.append("r104_deep_cycle_spec_missing_or_invalid")
            if not standard_cycle_payload:
                blockers.append("r104_standard_cycle_spec_missing_or_invalid")
            if not discovery_payload:
                blockers.append("r104_exact_discovery_spec_missing_or_invalid")
            if not standard_discovery_payload:
                blockers.append("r104_standard_discovery_spec_missing_or_invalid")
            row_counts = (readiness_payload or {}).get("fixture_row_counts") or {}
            primary_bars = self._nonnegative_int(row_counts.get("bars"))
            lower_rows = self._nonnegative_int(row_counts.get("lower_timeframe_bars"))
            agg_rows = self._nonnegative_int(row_counts.get("agg_trade"))
            window_selection = (readiness_payload or {}).get("window_selection_recorded") or {}
            effective_hours = round(primary_bars * 15 / 60, 2)
            evidence_depth_blockers: list[str] = []
            if primary_bars < CANDIDATE_READY_PRIMARY_15M_MIN_BARS:
                evidence_depth_blockers.append(
                    f"primary_15m_bars_below_candidate_floor:{primary_bars}<{CANDIDATE_READY_PRIMARY_15M_MIN_BARS}"
                )
            if lower_rows < CANDIDATE_READY_CONTEXT_1M_MIN_ROWS:
                evidence_depth_blockers.append(
                    f"lower_timeframe_1m_rows_below_candidate_floor:{lower_rows}<{CANDIDATE_READY_CONTEXT_1M_MIN_ROWS}"
                )
            if agg_rows < CANDIDATE_READY_CONTEXT_1M_MIN_ROWS:
                evidence_depth_blockers.append(
                    f"agg_trade_1m_rows_below_candidate_floor:{agg_rows}<{CANDIDATE_READY_CONTEXT_1M_MIN_ROWS}"
                )
            if effective_hours < CANDIDATE_READY_MIN_EFFECTIVE_HOURS:
                evidence_depth_blockers.append(
                    f"effective_coverage_hours_below_candidate_floor:{effective_hours}<{CANDIDATE_READY_MIN_EFFECTIVE_HOURS}"
                )
            evidence_depth_ready = fixture_integrity_ready and not evidence_depth_blockers
            ready = fixture_integrity_ready and evidence_depth_ready
            items.append(
                {
                    "symbol": symbol,
                    "ready": ready,
                    "fixture_integrity_ready": fixture_integrity_ready,
                    "evidence_depth_ready": evidence_depth_ready,
                    "candidate_evidence_ready": ready,
                    "status": (
                        "candidate_depth_ready"
                        if ready
                        else ("screening_only" if fixture_integrity_ready else "blocked")
                    ),
                    "blockers": blockers,
                    "evidence_depth_blockers": evidence_depth_blockers,
                    "readiness_config_path": str(paths["readiness_config"]),
                    "cycle_spec_path": str(paths["cycle_spec"]),
                    "standard_cycle_spec_path": str(paths["standard_cycle_spec"]),
                    "discovery_spec_path": str(paths["discovery_spec"]),
                    "standard_discovery_spec_path": str(paths["standard_discovery_spec"]),
                    "active_generated_fixture": bool(active_paths),
                    "active_catalog_fixture": bool(active_paths.get("catalog_path")),
                    "catalog_path": active_paths.get("catalog_path"),
                    "collection_summary_path": active_paths.get("collection_summary_path"),
                    "cycle_id": cycle_payload.get("cycle_id") if isinstance(cycle_payload, Mapping) else None,
                    "discovery_run_id": discovery_payload.get("run_id") if isinstance(discovery_payload, Mapping) else None,
                    "modern_window_profile_count": int(active_paths.get("modern_window_profile_count") or 0),
                    "modern_window_profiles": {
                        str(profile_id): dict(profile)
                        for profile_id, profile in (active_paths.get("modern_window_profiles") or {}).items()
                        if isinstance(profile, Mapping)
                    },
                    "fixture_manifest_path": str(fixture_path) if fixture_path is not None else None,
                    "fixture_manifest_sha256": actual_sha or None,
                    "expected_fixture_manifest_sha256": expected_sha or None,
                    "fixture_row_counts": row_counts,
                    "window_selection_recorded": window_selection,
                    "evidence_depth": {
                        "claim_scope": "candidate_ready_1y_floor",
                        "primary_interval": "15m",
                        "primary_bars": primary_bars,
                        "lower_timeframe_1m_rows": lower_rows,
                        "agg_trade_1m_rows": agg_rows,
                        "effective_coverage_hours": effective_hours,
                        "sparse_window_count": len(window_selection) if isinstance(window_selection, Mapping) else 0,
                        "required_primary_15m_bars": CANDIDATE_READY_PRIMARY_15M_MIN_BARS,
                        "required_context_1m_rows": CANDIDATE_READY_CONTEXT_1M_MIN_ROWS,
                        "required_effective_hours": CANDIDATE_READY_MIN_EFFECTIVE_HOURS,
                    },
                    "promotion_ready": False,
                    "research_only": True,
                    "observe_only": True,
                }
            )
        ready_count = sum(1 for item in items if item["ready"])
        fixture_integrity_ready_count = sum(1 for item in items if item["fixture_integrity_ready"])
        evidence_depth_ready_count = sum(1 for item in items if item["evidence_depth_ready"])
        depth_blockers = sorted({reason for item in items for reason in item["evidence_depth_blockers"]})
        return {
            "stage": "R106",
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "source_of_truth": "historical_data_catalog",
            "provider_states": historical_data_provider_states(),
            "ready": ready_count == len(items),
            "fixture_integrity_ready": fixture_integrity_ready_count == len(items),
            "candidate_evidence_ready": ready_count == len(items),
            "ready_count": ready_count,
            "fixture_integrity_ready_count": fixture_integrity_ready_count,
            "evidence_depth_ready_count": evidence_depth_ready_count,
            "symbol_count": len(items),
            "items": items,
            "recommended_next_action": (
                "Run durable BTC or ETH brute-force cycle, then exact discovery, then candidate eligibility review."
                if ready_count == len(items)
                else (
                    "Refresh the R106 Historical Data Catalog before treating exact discovery as required candidate evidence; "
                    "current checked fixtures are integrity-ready screening windows only."
                    if fixture_integrity_ready_count == len(items) and depth_blockers
                    else "Fix catalog fixture integrity before running candidate validation."
                )
            ),
            "primary_blockers": sorted({reason for item in items for reason in [*item["blockers"], *item["evidence_depth_blockers"]]}),
        }

    def historical_data_catalog_diagnostics(self) -> dict[str, Any]:
        catalog = self._latest_historical_data_catalog_manifest()
        if isinstance(catalog, Mapping):
            payload = dict(catalog)
            payload.setdefault("stage", "R106")
            payload.setdefault("research_only", True)
            payload.setdefault("observe_only", True)
            payload.setdefault("promotion_ready", False)
            payload.setdefault("recommended_next_action", self.r104_readiness_diagnostics().get("recommended_next_action"))
            return payload
        provider_states = historical_data_provider_states()
        return {
            "historical_data_catalog_version": "historical-data-catalog-v1",
            "stage": "R106",
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "catalog_ready": False,
            "candidate_depth_ready": False,
            "source_of_truth": "historical_data_catalog",
            "provider_states": provider_states,
            "symbols": {},
            "intervention_required": [
                {
                    "source_name": source_name,
                    "catalog_state": state.get("catalog_state"),
                    "required_next_steps": list(state.get("required_next_steps") or []),
                }
                for source_name, state in sorted(provider_states.items())
                if state.get("required_next_steps")
            ],
            "recommended_next_action": "Refresh Historical Data Catalog to create active BTC/ETH generated fixture packs.",
        }

    def _latest_historical_data_catalog_manifest(self) -> dict[str, Any] | None:
        research_root = self._research_root()
        if not research_root.exists():
            return None
        try:
            artifact_paths = self._artifact_path_index(research_root)
        except OSError:
            return None
        catalogs = sorted(
            self._artifact_paths_from_index(artifact_paths, "historical_data_catalog.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for catalog_path in catalogs:
            payload = self._read_historical_data_catalog_path(catalog_path)
            if isinstance(payload, dict):
                payload.setdefault("catalog_path", str(catalog_path))
                return payload
        return None

    def _latest_historical_data_catalog_readiness_by_symbol(self) -> dict[str, dict[str, Any]]:
        catalog = self._latest_historical_data_catalog_manifest()
        if not isinstance(catalog, Mapping):
            return {}
        catalog_path = str(catalog.get("catalog_path") or "")
        symbols = catalog.get("symbols")
        if not isinstance(symbols, Mapping):
            return {}
        result: dict[str, dict[str, Any]] = {}
        for raw_symbol, item in symbols.items():
            symbol = str(raw_symbol).strip().upper()
            if not symbol or not isinstance(item, Mapping):
                continue
            if item.get("candidate_depth_ready") is not True and item.get("candidate_depth_thresholds_met") is not True:
                continue
            result[symbol] = {
                "catalog_path": catalog_path,
                "collection_summary_path": item.get("source_summary_path"),
                "readiness_config_path": item.get("readiness_config_path"),
                "cycle_spec_path": item.get("cycle_spec_path"),
                "discovery_spec_path": item.get("discovery_spec_path"),
                "fixture_manifest_path": item.get("fixture_manifest_path"),
                "modern_window_profile_count": int(item.get("modern_window_profile_count") or 0),
                "modern_window_profiles": {
                    str(profile_id): dict(profile)
                    for profile_id, profile in (item.get("modern_window_profiles") or {}).items()
                    if isinstance(profile, Mapping)
                },
            }
        return result

    def _latest_durable_collection_readiness_by_symbol(self) -> dict[str, dict[str, Any]]:
        research_root = self._research_root()
        if not research_root.exists():
            return {}
        try:
            artifact_paths = self._artifact_path_index(research_root)
        except OSError:
            return {}
        result: dict[str, dict[str, Any]] = {}
        summaries = sorted(
            self._artifact_paths_from_index(artifact_paths, "durable_fixture_collection_summary.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for summary_path in summaries:
            payload = self._read_json_path(summary_path)
            if not isinstance(payload, Mapping):
                continue
            symbols = payload.get("symbols")
            if not isinstance(symbols, Mapping):
                continue
            for raw_symbol, item in symbols.items():
                symbol = str(raw_symbol).strip().upper()
                if symbol in result or not isinstance(item, Mapping):
                    continue
                if item.get("status") != "candidate_depth_fixture_ready":
                    continue
                result[symbol] = {
                    "collection_summary_path": str(summary_path),
                    "readiness_config_path": item.get("readiness_config_path"),
                    "cycle_spec_path": item.get("cycle_spec_path"),
                    "discovery_spec_path": item.get("discovery_spec_path"),
                    "fixture_manifest_path": item.get("fixture_manifest_path"),
                }
        return result

    @staticmethod
    def _nonnegative_int(value: object) -> int:
        try:
            return max(0, int(value))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0

    async def research_progress_diagnostics(self) -> dict[str, Any]:
        jobs = await self.list_jobs()
        artifacts = self._dedupe_research_progress_artifacts(
            [
                *self._research_progress_artifacts_from_jobs(jobs),
                *self._research_progress_known_artifacts(),
            ]
        )
        readiness = self.r104_readiness_diagnostics()
        r104_job_types = {
            "refresh-historical-data-catalog",
            "collect-durable-data",
            "run-historical-research-cycle",
            "run-discovery",
            "analyze-research-results",
            "analyze-research-delta",
            "run-frozen-entry-exit-lab",
            "run-research-autopilot",
            "evaluate-discovery-candidate-pack-eligibility",
        }
        active_job = next(
            (
                job for job in jobs
                if job.get("status") in {"queued", "running"} and job.get("job_type") in r104_job_types
            ),
            None,
        )
        required_evidence_ready = bool(readiness.get("ready"))
        active_discovery_progress = (
            self._active_discovery_progress(active_job)
            if active_job is not None and active_job.get("job_type") == "run-discovery"
            else self._latest_incomplete_discovery_progress(artifacts)
        )
        active_historical_data_progress = (
            self._active_historical_data_progress(active_job)
            if active_job is not None and active_job.get("job_type") == "refresh-historical-data-catalog"
            else None
        )
        active_historical_cycle_progress = (
            self._active_historical_cycle_progress(active_job)
            if active_job is not None and active_job.get("job_type") == "run-historical-research-cycle"
            else None
        )
        active_autopilot_progress = (
            self._active_research_autopilot_progress(active_job, artifacts)
            if active_job is not None and active_job.get("job_type") == "run-research-autopilot"
            else None
        )
        expected_btc_cycle_id = self._expected_cycle_id(readiness, "BTCUSDT")
        expected_eth_cycle_id = self._expected_cycle_id(readiness, "ETHUSDT")
        expected_btc_discovery_id = self._expected_discovery_run_id(readiness, "BTCUSDT")
        expected_eth_discovery_id = self._expected_discovery_run_id(readiness, "ETHUSDT")
        btc_cycle_complete = required_evidence_ready and self._required_artifact_complete(
            artifacts,
            "historical_research_cycle",
            "BTCUSDT",
            "btc_cycle",
            {expected_btc_cycle_id},
        )
        eth_cycle_complete = required_evidence_ready and self._required_artifact_complete(
            artifacts,
            "historical_research_cycle",
            "ETHUSDT",
            "eth_cycle",
            {expected_eth_cycle_id},
        )
        exact_discovery_complete = required_evidence_ready and any(
            self._required_artifact_status(item, "candidate_eligibility", None)["complete"]
            for item in artifacts
            if item.get("type") == "discovery_run"
        )
        analysis_complete = required_evidence_ready and self._required_artifact_complete(
            artifacts,
            "research_analysis",
            None,
            "research_analysis",
            None,
        )
        analysis_delta_complete = required_evidence_ready and self._required_artifact_complete(
            artifacts,
            "research_analysis_delta",
            None,
            "research_analysis_delta",
            None,
        )
        exit_lab_complete = required_evidence_ready and self._required_artifact_complete(
            artifacts,
            "discovery_exit_lab",
            None,
            "frozen_entry_exit_lab",
            None,
        )
        milestones: list[dict[str, Any]] = [
            self._historical_data_catalog_milestone(jobs, artifacts, readiness),
            self._readiness_milestone(readiness),
            self._artifact_job_milestone(
                "btc_cycle",
                "BTC brute-force cycle",
                "BTCUSDT",
                "run-historical-research-cycle",
                "historical_research_cycle",
                jobs,
                artifacts,
                prerequisite_complete=bool(readiness.get("ready")),
                require_current_evidence=required_evidence_ready,
                ready_detail="Run the deep BTC historical cycle on durable public-archive fixtures.",
                waiting_detail="Candidate-depth durable data must be available before the BTC cycle can count.",
                expected_artifact_ids={expected_btc_cycle_id},
            ),
            self._artifact_job_milestone(
                "btc_discovery",
                "BTC exact discovery",
                "BTCUSDT",
                "run-discovery",
                "discovery_run",
                jobs,
                artifacts,
                prerequisite_complete=btc_cycle_complete,
                require_current_evidence=required_evidence_ready,
                ready_detail="Run the BTC exact bounded sweep after the deep cycle so search coverage is exhaustive.",
                waiting_detail="Run the BTC brute-force cycle before BTC exact discovery.",
                expected_artifact_ids={expected_btc_discovery_id},
            ),
            self._artifact_job_milestone(
                "eth_cycle",
                "ETH brute-force cycle",
                "ETHUSDT",
                "run-historical-research-cycle",
                "historical_research_cycle",
                jobs,
                artifacts,
                prerequisite_complete=bool(readiness.get("ready")),
                require_current_evidence=required_evidence_ready,
                ready_detail="Run the deep ETH mirror cycle to check whether BTC findings generalize.",
                waiting_detail="Candidate-depth durable data must be available before the ETH cycle can count.",
                expected_artifact_ids={expected_eth_cycle_id},
            ),
            self._artifact_job_milestone(
                "eth_discovery",
                "ETH exact discovery",
                "ETHUSDT",
                "run-discovery",
                "discovery_run",
                jobs,
                artifacts,
                prerequisite_complete=eth_cycle_complete,
                require_current_evidence=required_evidence_ready,
                ready_detail="Run ETH exact bounded discovery after ETH cycle evidence is available.",
                waiting_detail="Run the ETH brute-force cycle before ETH exact discovery.",
                expected_artifact_ids={expected_eth_discovery_id},
            ),
            self._artifact_job_milestone(
                "research_analysis",
                "Research analysis",
                None,
                "analyze-research-results",
                "research_analysis",
                jobs,
                artifacts,
                prerequisite_complete=exact_discovery_complete,
                require_current_evidence=required_evidence_ready,
                ready_detail="Analyze completed cycle/discovery outputs before eligibility review or another search mutation.",
                waiting_detail="Run at least one exact durable discovery before writing research analysis.",
            ),
            self._artifact_job_milestone(
                "research_analysis_delta",
                "Run-to-run delta",
                None,
                "analyze-research-delta",
                "research_analysis_delta",
                jobs,
                artifacts,
                prerequisite_complete=analysis_complete,
                require_current_evidence=required_evidence_ready,
                ready_detail="Write the run-to-run delta artifact; if no compatible prior exists, it records a baseline instead of promoting anything.",
                waiting_detail="Run research analysis before writing run-to-run deltas.",
            ),
            self._artifact_job_milestone(
                "frozen_entry_exit_lab",
                "Frozen-entry exit lab",
                None,
                "run-frozen-entry-exit-lab",
                "discovery_exit_lab",
                jobs,
                artifacts,
                prerequisite_complete=analysis_delta_complete,
                require_current_evidence=required_evidence_ready,
                ready_detail="Replay frozen entry evidence across fixed holding and simple-runner exits, or write a blocked manifest when entry timestamps are unavailable.",
                waiting_detail="Run the run-to-run delta before the frozen-entry exit lab.",
            ),
            self._artifact_job_milestone(
                "candidate_eligibility",
                "Candidate eligibility review",
                None,
                "evaluate-discovery-candidate-pack-eligibility",
                "candidate_pack_eligibility",
                jobs,
                artifacts,
                prerequisite_complete=exit_lab_complete,
                require_current_evidence=required_evidence_ready,
                ready_detail="Evaluate latest discovery output against candidate-pack gate evidence.",
                waiting_detail="Run research analysis, deltas, and the frozen-entry exit lab before eligibility review.",
            ),
        ]
        complete_count = sum(1 for item in milestones if item["status"] == "complete")
        next_action = self._research_next_action(milestones, active_job)
        return {
            "stage": "R106",
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "progress": {
                "completed": complete_count,
                "total": len(milestones),
                "percent": round((complete_count / max(len(milestones), 1)) * 100),
                "active_job_id": active_job.get("job_id") if active_job else None,
                "active_job_type": active_job.get("job_type") if active_job else None,
                "active_job_status": active_job.get("status") if active_job else None,
            },
            "active_autopilot_progress": active_autopilot_progress,
            "active_discovery_progress": active_discovery_progress,
            "active_historical_data_progress": active_historical_data_progress,
            "active_historical_cycle_progress": active_historical_cycle_progress,
            "next_action": next_action,
            "milestones": milestones,
            "settings": {
                "default_scope": "R106 Historical Data Catalog active fixtures",
                "primary_cycle_profile": "deep durable cycle, 64 candidates per strategy, 16 regions refined",
                "primary_discovery_profile": "exact bounded sweep, 570240 planned combinations per symbol",
                "analysis_profile": "mandatory analysis, run-to-run delta, and frozen-entry exit-lab artifacts before eligibility review",
                "standard_discovery_profile": "720-trial sparse screen for quick blocker feedback",
                "output_policy": "stable resumable output directory for exact sweeps; isolated output for quick diagnostics",
                "path_policy": "configs plus research output allowlists",
                "promotion_policy": "candidate pack blocked until gates pass",
            },
        }

    def _research_progress_artifacts_from_jobs(self, jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        artifacts: list[dict[str, Any]] = []
        for job in jobs:
            if job.get("status") != "succeeded" or not isinstance(job.get("result"), Mapping):
                continue
            result = job["result"]
            job_type = str(job.get("job_type") or "")
            if job_type == "run-historical-research-cycle":
                path = self._existing_path(result.get("research_cycle_manifest_path"))
                payload = self._read_json_path(path) if path is not None else None
                if isinstance(payload, dict):
                    artifacts.append(
                        {
                            "type": "historical_research_cycle",
                            "path": str(path),
                            "sort_time": path.stat().st_mtime,
                            "manifest": payload,
                            "summary": {
                                "cycle_id": payload.get("cycle_id"),
                                "symbol": payload.get("symbol"),
                                "candidate_count": payload.get("candidate_count"),
                            },
                        }
                    )
            elif job_type == "refresh-historical-data-catalog":
                path = self._existing_path(result.get("catalog_path") or result.get("historical_data_catalog_path"))
                payload = self._read_json_path(path) if path is not None else None
                if isinstance(payload, dict):
                    artifacts.append(
                        {
                            "type": "historical_data_catalog",
                            "path": str(path),
                            "sort_time": path.stat().st_mtime,
                            "manifest": payload,
                            "summary": {
                                "symbol_count": len(payload.get("symbols") or {}),
                                "start_month": payload.get("start_month"),
                                "end_month": payload.get("end_month"),
                                "candidate_depth_ready": payload.get("candidate_depth_ready"),
                                "promotion_ready": payload.get("promotion_ready"),
                            },
                        }
                    )
            elif job_type == "collect-durable-data":
                path = self._existing_path(result.get("summary_path"))
                payload = self._read_json_path(path) if path is not None else None
                if isinstance(payload, dict):
                    artifacts.append(
                        {
                            "type": "durable_data_collection",
                            "path": str(path),
                            "sort_time": path.stat().st_mtime,
                            "manifest": payload,
                            "summary": {
                                "symbol_count": len(payload.get("symbols") or {}),
                                "start_month": payload.get("start_month"),
                                "end_month": payload.get("end_month"),
                                "promotion_ready": payload.get("promotion_ready"),
                            },
                        }
                    )
            elif job_type == "run-discovery":
                path = self._existing_path(result.get("discovery_run_manifest_path"))
                payload = self._read_json_path(path) if path is not None else None
                if isinstance(payload, dict):
                    artifacts.append(
                        {
                            "type": "discovery_run",
                            "path": str(path),
                            "sort_time": path.stat().st_mtime,
                            "manifest": payload,
                            "summary": {
                                "run_id": payload.get("run_id"),
                                "symbol": payload.get("symbol"),
                                "status": ((payload.get("state") or {}).get("status")),
                            },
                        }
                    )
            elif job_type == "analyze-research-results":
                path = self._existing_path(result.get("research_analysis_path"))
                payload = self._read_json_path(path) if path is not None else None
                if isinstance(payload, dict):
                    artifacts.append(
                        {
                            "type": "research_analysis",
                            "path": str(path),
                            "sort_time": path.stat().st_mtime,
                            "manifest": payload,
                            "summary": self._research_analysis_summary(payload),
                        }
                    )
            elif job_type == "analyze-research-delta":
                path = self._existing_path(result.get("research_analysis_delta_path"))
                payload = self._read_json_path(path) if path is not None else None
                if isinstance(payload, dict):
                    artifacts.append(
                        {
                            "type": "research_analysis_delta",
                            "path": str(path),
                            "sort_time": path.stat().st_mtime,
                            "manifest": payload,
                            "summary": self._research_analysis_delta_summary(payload),
                        }
                    )
            elif job_type == "run-frozen-entry-exit-lab":
                path = self._existing_path(result.get("exit_lab_manifest_path"))
                payload = self._read_json_path(path) if path is not None else None
                if isinstance(payload, dict):
                    artifacts.append(
                        {
                            "type": "discovery_exit_lab",
                            "path": str(path),
                            "sort_time": path.stat().st_mtime,
                            "manifest": payload,
                            "summary": self._discovery_exit_lab_summary(payload),
                        }
                    )
            elif job_type == "run-research-autopilot":
                path = self._existing_path(result.get("research_autopilot_manifest_path"))
                payload = self._read_json_path(path) if path is not None else None
                if isinstance(payload, dict):
                    artifacts.append(
                        {
                            "type": "research_autopilot",
                            "path": str(path),
                            "sort_time": path.stat().st_mtime,
                            "manifest": payload,
                            "summary": self._research_autopilot_summary(payload),
                        }
                    )
            elif job_type == "evaluate-discovery-candidate-pack-eligibility":
                path = self._existing_path(result.get("candidate_pack_eligibility_manifest_path"))
                payload = self._read_json_path(path) if path is not None else None
                if isinstance(payload, dict):
                    artifacts.append(
                        {
                            "type": "candidate_pack_eligibility",
                            "path": str(path),
                            "sort_time": path.stat().st_mtime,
                            "manifest": payload,
                            "summary": {
                                "bridge_scope": payload.get("bridge_scope"),
                                "candidate_pack_written": payload.get("candidate_pack_written"),
                            },
                        }
                    )
        return artifacts

    def _research_progress_known_artifacts(self) -> list[dict[str, Any]]:
        root = self.config.research.output_dir.resolve()
        if not root.exists():
            return []
        active_readiness = self._latest_historical_data_catalog_readiness_by_symbol()
        if not active_readiness:
            active_readiness = self._latest_durable_collection_readiness_by_symbol()
        active_cycle_ids = tuple(
            str((self._read_json_path(Path(str(item.get("cycle_spec_path")))) or {}).get("cycle_id"))
            for item in active_readiness.values()
            if item.get("cycle_spec_path")
        )
        active_discovery_ids = tuple(
            str((self._read_json_path(Path(str(item.get("discovery_spec_path")))) or {}).get("run_id"))
            for item in active_readiness.values()
            if item.get("discovery_spec_path")
        )
        cycle_ids = (
            "r104-btcusdt-durable-public-archive-deep-v1",
            "r104-ethusdt-durable-public-archive-deep-v1",
            "r104-btcusdt-durable-public-archive-v1",
            "r104-ethusdt-durable-public-archive-v1",
            *[value for value in active_cycle_ids if value and value != "None"],
        )
        discovery_ids = (
            "exact_entry_sweep_btcusdt_durable_r104_v1",
            "exact_entry_sweep_ethusdt_durable_r104_v1",
            "standard_entry_discovery_btcusdt_durable_r104_v1",
            "standard_entry_discovery_ethusdt_durable_r104_v1",
            "deep_candidate_harvest_btcusdt_v4",
            "standard_entry_discovery_btcusdt_v4",
            *[value for value in active_discovery_ids if value and value != "None"],
        )
        artifacts: list[dict[str, Any]] = []
        for path in root.glob("operator_runs/historical_data/*/historical_data_catalog.json"):
            artifact = self._research_progress_artifact_from_manifest(path, artifact_type="historical_data_catalog")
            if artifact is not None:
                artifacts.append(artifact)
        for path in root.glob("operator_runs/durable_data/*/durable_fixture_collection_summary.json"):
            artifact = self._research_progress_artifact_from_manifest(path, artifact_type="durable_data_collection")
            if artifact is not None:
                artifacts.append(artifact)
        for cycle_id in cycle_ids:
            safe_id = _safe_operator_path_part(cycle_id)
            direct_id = cycle_id.replace("-", "_")
            paths = [
                *root.glob(f"operator_runs/historical_cycles/{safe_id}/*/research_cycle_manifest.json"),
                root / "historical_cycles" / direct_id / "research_cycle_manifest.json",
            ]
            for path in paths:
                artifact = self._research_progress_artifact_from_manifest(
                    path,
                    artifact_type="historical_research_cycle",
                )
                if artifact is not None:
                    artifacts.append(artifact)
        for run_id in discovery_ids:
            safe_id = _safe_operator_path_part(run_id)
            paths = [
                root / "operator_runs" / "discovery_runs" / safe_id / "discovery_run_manifest.json",
                *root.glob(f"operator_runs/discovery_runs/{safe_id}/*/discovery_run_manifest.json"),
                root / "discovery_runs" / run_id / "discovery_run_manifest.json",
            ]
            for path in paths:
                artifact = self._research_progress_artifact_from_manifest(path, artifact_type="discovery_run")
                if artifact is not None:
                    artifacts.append(artifact)
        for path in root.glob("operator_runs/candidate_pack_eligibility/*/candidate_pack_eligibility_manifest.json"):
            artifact = self._research_progress_artifact_from_manifest(path, artifact_type="candidate_pack_eligibility")
            if artifact is not None:
                artifacts.append(artifact)
        for path in root.glob("operator_runs/analysis/*/research_analysis.json"):
            artifact = self._research_progress_artifact_from_manifest(path, artifact_type="research_analysis")
            if artifact is not None:
                artifacts.append(artifact)
        for path in root.glob("operator_runs/analysis_deltas/*/research_analysis_delta.json"):
            artifact = self._research_progress_artifact_from_manifest(path, artifact_type="research_analysis_delta")
            if artifact is not None:
                artifacts.append(artifact)
        for path in root.glob("operator_runs/frozen_entry_exit_lab/*/discovery_exit_lab_manifest.json"):
            artifact = self._research_progress_artifact_from_manifest(path, artifact_type="discovery_exit_lab")
            if artifact is not None:
                artifacts.append(artifact)
        for path in root.glob("operator_runs/research_autopilot/*/research_autopilot_manifest.json"):
            artifact = self._research_progress_artifact_from_manifest(path, artifact_type="research_autopilot")
            if artifact is not None:
                artifacts.append(artifact)
        return artifacts

    def _research_progress_artifact_from_manifest(
        self,
        path: Path,
        *,
        artifact_type: str,
    ) -> dict[str, Any] | None:
        path = Path(path)
        if not path.is_file():
            return None
        payload = self._read_json_path(path)
        if not isinstance(payload, dict):
            return None
        if artifact_type == "historical_research_cycle":
            summary = {
                "cycle_id": payload.get("cycle_id"),
                "symbol": payload.get("symbol"),
                "candidate_count": payload.get("candidate_count"),
            }
        elif artifact_type == "discovery_run":
            summary = {
                "run_id": payload.get("run_id"),
                "symbol": payload.get("symbol"),
                "status": ((payload.get("state") or {}).get("status")),
            }
        elif artifact_type == "historical_data_catalog":
            summary = {
                "symbol_count": len(payload.get("symbols") or {}),
                "start_month": payload.get("start_month"),
                "end_month": payload.get("end_month"),
                "candidate_depth_ready": payload.get("candidate_depth_ready"),
                "promotion_ready": payload.get("promotion_ready"),
            }
        elif artifact_type == "modern_window_profile":
            summary = self._modern_window_profile_summary(payload)
        elif artifact_type == "durable_data_collection":
            summary = {
                "symbol_count": len(payload.get("symbols") or {}),
                "start_month": payload.get("start_month"),
                "end_month": payload.get("end_month"),
                "promotion_ready": payload.get("promotion_ready"),
            }
        elif artifact_type == "research_analysis":
            summary = self._research_analysis_summary(payload)
        elif artifact_type == "research_analysis_delta":
            summary = self._research_analysis_delta_summary(payload)
        elif artifact_type == "discovery_exit_lab":
            summary = self._discovery_exit_lab_summary(payload)
        elif artifact_type == "research_autopilot":
            summary = self._research_autopilot_summary(payload)
        else:
            summary = {
                "bridge_scope": payload.get("bridge_scope"),
                "candidate_pack_written": payload.get("candidate_pack_written"),
            }
        return {
            "type": artifact_type,
            "path": str(path),
            "sort_time": path.stat().st_mtime,
            "manifest": payload,
            "summary": summary,
        }

    def _modern_window_profile_summary(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "profile_id": payload.get("profile_id"),
            "profile_scope": payload.get("profile_scope"),
            "status": payload.get("status"),
            "symbol": payload.get("symbol"),
            "cycle_id": payload.get("cycle_id"),
            "discovery_run_id": payload.get("discovery_run_id"),
            "window_start_utc": payload.get("window_start_utc"),
            "window_end_utc": payload.get("window_end_utc"),
            "row_counts": payload.get("row_counts") if isinstance(payload.get("row_counts"), Mapping) else {},
            "research_only": payload.get("research_only"),
            "observe_only": payload.get("observe_only"),
            "promotion_ready": payload.get("promotion_ready"),
        }

    def _research_analysis_summary(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        cycle = payload.get("cycle") if isinstance(payload.get("cycle"), Mapping) else {}
        discovery = payload.get("discovery") if isinstance(payload.get("discovery"), Mapping) else {}
        interpretation = payload.get("interpretation") if isinstance(payload.get("interpretation"), Mapping) else {}
        cycle_manifest = cycle.get("manifest") if isinstance(cycle.get("manifest"), Mapping) else {}
        takeaways = interpretation.get("takeaways") if isinstance(interpretation.get("takeaways"), list) else []
        next_steps = interpretation.get("next_steps") if isinstance(interpretation.get("next_steps"), list) else []
        return {
            "analysis_version": payload.get("analysis_version"),
            "symbol": discovery.get("symbol") or cycle_manifest.get("symbol"),
            "cycle_id": cycle_manifest.get("cycle_id"),
            "run_id": discovery.get("run_id"),
            "cycle_available": bool(cycle.get("available")),
            "discovery_available": bool(discovery.get("available")),
            "takeaway_count": len(takeaways),
            "next_step_count": len(next_steps),
            "research_only": payload.get("research_only"),
            "observe_only": payload.get("observe_only"),
            "promotion_ready": payload.get("promotion_ready"),
        }

    def _discovery_performance_summary(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        compute = payload.get("compute_telemetry") if isinstance(payload.get("compute_telemetry"), Mapping) else {}
        observed = payload.get("execution_observed") if isinstance(payload.get("execution_observed"), Mapping) else {}
        worker_plan = compute.get("worker_plan") if isinstance(compute.get("worker_plan"), Mapping) else {}
        stage_seconds = (
            compute.get("wall_time_seconds_by_stage")
            if isinstance(compute.get("wall_time_seconds_by_stage"), Mapping)
            else {}
        )
        cache_hit_rates = compute.get("cache_hit_rates") if isinstance(compute.get("cache_hit_rates"), Mapping) else {}
        cache_counts = compute.get("cache_counts") if isinstance(compute.get("cache_counts"), Mapping) else {}
        process_chunk_timing = (
            compute.get("process_chunk_timing")
            if isinstance(compute.get("process_chunk_timing"), Mapping)
            else {}
        )
        top_stage_seconds = dict(
            sorted(
                ((str(key), self._float_or_none(value) or 0.0) for key, value in stage_seconds.items()),
                key=lambda item: (-item[1], item[0]),
            )[:8]
        )
        return {
            "executor": compute.get("executor") or observed.get("executor"),
            "configured_executor": compute.get("configured_executor") or observed.get("configured_executor"),
            "configured_max_workers": compute.get("configured_max_workers") or observed.get("configured_max_workers"),
            "requested_workers": compute.get("requested_workers") or observed.get("requested_workers"),
            "active_workers": compute.get("active_workers") or observed.get("active_workers"),
            "worker_plan_reason": worker_plan.get("reason") or observed.get("worker_plan_reason"),
            "worker_plan": worker_plan,
            "trial_chunk_size": compute.get("trial_chunk_size") or observed.get("trial_chunk_size"),
            "process_worker_cap": compute.get("process_worker_cap") or observed.get("process_worker_cap"),
            "process_worker_cap_source": compute.get("process_worker_cap_source") or observed.get("process_worker_cap_source"),
            "process_worker_cap_applied": compute.get("process_worker_cap_applied") or observed.get("process_worker_cap_applied"),
            "real_discovery_requested": compute.get("real_discovery_requested") or observed.get("real_discovery_requested"),
            "process_pool_child_cpu_not_in_parent_process_cpu_seconds": bool(
                compute.get("process_pool_child_cpu_not_in_parent_process_cpu_seconds")
                or observed.get("process_pool_child_cpu_not_in_parent_process_cpu_seconds")
            ),
            "wall_time_seconds": compute.get("wall_time_seconds"),
            "trials_per_minute": compute.get("trials_per_minute"),
            "completed_trials": compute.get("completed_trials"),
            "total_planned_trials": compute.get("total_planned_trials"),
            "remaining_trials": compute.get("remaining_trials"),
            "estimated_seconds_remaining": compute.get("estimated_seconds_remaining"),
            "process_cpu_percent_of_worker_capacity": compute.get("process_cpu_percent_of_worker_capacity"),
            "process_cpu_percent_of_logical_capacity": compute.get("process_cpu_percent_of_logical_capacity"),
            "artifact_write_time_seconds_observed": compute.get("artifact_write_time_seconds_observed"),
            "artifact_write_wall_time_share": compute.get("artifact_write_wall_time_share"),
            "artifact_write_time_scope": compute.get("artifact_write_time_scope"),
            "artifact_file_count": compute.get("artifact_file_count"),
            "artifact_bytes_written": compute.get("artifact_bytes_written"),
            "artifact_count_scope": compute.get("artifact_count_scope"),
            "artifact_count_strategy": compute.get("artifact_count_strategy"),
            "cache_hit_rates": dict(cache_hit_rates),
            "cache_counts": dict(cache_counts),
            "stage_seconds": dict(stage_seconds),
            "top_stage_seconds": top_stage_seconds,
            "process_chunk_timing": dict(process_chunk_timing),
            "telemetry_version": compute.get("telemetry_version"),
            "timing_note": (
                "parent_process_cpu_excludes_process_pool_children"
                if compute.get("process_pool_child_cpu_not_in_parent_process_cpu_seconds")
                or observed.get("process_pool_child_cpu_not_in_parent_process_cpu_seconds")
                else "parent_process_cpu_scope"
            ),
        }

    def _performance_utilization_study_summary(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        machine = payload.get("machine") if isinstance(payload.get("machine"), Mapping) else {}
        hardware_runs = payload.get("hardware") if isinstance(payload.get("hardware"), list) else []
        best_hardware = max(
            (item for item in hardware_runs if isinstance(item, Mapping)),
            key=lambda item: self._float_or_none(item.get("cpu_logical_capacity_percent")) or 0.0,
            default={},
        )
        historical = (
            payload.get("historical_cycle_provider_latest_month")
            if isinstance(payload.get("historical_cycle_provider_latest_month"), Mapping)
            else {}
        )
        historical_summary = (
            historical.get("summary")
            if isinstance(historical.get("summary"), Mapping)
            else {}
        )
        exact_probe = (
            payload.get("exact_btc_candidate_depth_probe_16")
            if isinstance(payload.get("exact_btc_candidate_depth_probe_16"), Mapping)
            else {}
        )
        exact_compute = (
            exact_probe.get("compute_telemetry")
            if isinstance(exact_probe.get("compute_telemetry"), Mapping)
            else {}
        )
        final_rebuild = (
            payload.get("active_btc_exact_final_manifest_artifact_rebuild_evidence")
            if isinstance(payload.get("active_btc_exact_final_manifest_artifact_rebuild_evidence"), Mapping)
            else {}
        )
        final_compute = (
            final_rebuild.get("compute_telemetry")
            if isinstance(final_rebuild.get("compute_telemetry"), Mapping)
            else {}
        )
        boundary = payload.get("research_boundary") if isinstance(payload.get("research_boundary"), Mapping) else {}
        return {
            "summary_version": payload.get("summary_version"),
            "cpu": machine.get("cpu"),
            "physical_cores": machine.get("physical_cores"),
            "logical_cpus": machine.get("logical_cpus"),
            "best_hardware_profile": best_hardware.get("name"),
            "best_hardware_workers": best_hardware.get("active_workers"),
            "best_hardware_worker_capacity_percent": best_hardware.get("cpu_worker_capacity_percent"),
            "best_hardware_logical_capacity_percent": best_hardware.get("cpu_logical_capacity_percent"),
            "best_hardware_worker_saturation": best_hardware.get("worker_saturation"),
            "best_hardware_logical_saturation": best_hardware.get("logical_saturation"),
            "gpu_status": best_hardware.get("gpu_status"),
            "gpu_approx_gflops_per_second": best_hardware.get("gpu_approx_gflops_per_second"),
            "historical_candidate_backtests_per_minute": historical_summary.get("candidate_backtests_per_minute_mean"),
            "historical_elapsed_seconds_mean": historical_summary.get("elapsed_seconds_mean"),
            "exact_probe_trials_per_minute": exact_compute.get("trials_per_minute"),
            "exact_probe_wall_time_seconds": exact_compute.get("wall_time_seconds"),
            "exact_probe_active_workers": exact_compute.get("active_workers"),
            "exact_probe_trial_chunk_size": exact_compute.get("trial_chunk_size"),
            "final_artifact_file_count": final_compute.get("artifact_file_count"),
            "final_artifact_bytes_written": final_compute.get("artifact_bytes_written"),
            "final_artifact_write_wall_time_share": final_compute.get("artifact_write_wall_time_share"),
            "ui_one_line_command": payload.get("ui_one_line_command"),
            "research_only": boundary.get("research_only", True),
            "observe_only": boundary.get("observe_only", True),
            "promotion_ready": boundary.get("promotion_ready", False),
            "speed_claimed": boundary.get("speed_claimed", False),
        }

    def _research_analysis_delta_summary(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        current = payload.get("current") if isinstance(payload.get("current"), Mapping) else {}
        previous = payload.get("previous") if isinstance(payload.get("previous"), Mapping) else {}
        scope = payload.get("comparison_scope") if isinstance(payload.get("comparison_scope"), Mapping) else {}
        blockers = scope.get("blocked_reasons") if isinstance(scope.get("blocked_reasons"), list) else []
        return {
            "delta_version": payload.get("delta_version"),
            "symbol": current.get("symbol") or previous.get("symbol"),
            "current_analysis_path": current.get("analysis_path"),
            "previous_analysis_path": previous.get("analysis_path"),
            "compatible": bool(scope.get("compatible")),
            "blocked_reasons": blockers,
            "blocked_reason_count": len(blockers),
            "research_only": payload.get("research_only"),
            "observe_only": payload.get("observe_only"),
            "promotion_ready": payload.get("promotion_ready"),
        }

    def _discovery_exit_lab_summary(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        outputs = payload.get("required_outputs") if isinstance(payload.get("required_outputs"), Mapping) else {}
        return {
            "exit_lab_version": payload.get("exit_lab_version"),
            "exit_lab_scope": payload.get("exit_lab_scope"),
            "symbol": payload.get("symbol"),
            "input_ranking_row_count": payload.get("input_ranking_row_count"),
            "selected_lead_count": payload.get("selected_lead_count"),
            "comparison_count": payload.get("comparison_count"),
            "candidate_gate_row_count": payload.get("candidate_gate_row_count"),
            "decision_counts": payload.get("decision_counts") or {},
            "blocked_reason": payload.get("blocked_reason"),
            "promotion_ready": payload.get("promotion_ready"),
            "research_only": payload.get("research_only"),
            "observe_only": payload.get("observe_only"),
            "candidate_gates": self._summarize_gate_artifact(outputs.get("discovery_exit_lab_candidate_gates")),
        }

    def _research_autopilot_summary(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        steps = payload.get("steps") if isinstance(payload.get("steps"), list) else []
        status_counts: dict[str, int] = {}
        for step in steps:
            if not isinstance(step, Mapping):
                continue
            status = str(step.get("status") or "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        active_step = dict(payload.get("active_step") or {}) if isinstance(payload.get("active_step"), Mapping) else None
        updated_at = self._parse_utc_datetime(str(payload.get("updated_at_utc") or payload.get("started_at_utc") or ""))
        last_update_age_seconds = None
        if updated_at is not None:
            last_update_age_seconds = round(max(0.0, (datetime.now(timezone.utc) - updated_at).total_seconds()))
        autopilot_status = payload.get("autopilot_status")
        telemetry_status = "active_step_recorded" if active_step else "inactive"
        if autopilot_status == "running" and not active_step:
            telemetry_status = "running_without_active_step_telemetry"
        stale_review = (
            autopilot_status == "running"
            and not active_step
            and last_update_age_seconds is not None
            and last_update_age_seconds > RESEARCH_AUTOPILOT_STALE_MANIFEST_SECONDS
        )
        return {
            "autopilot_version": payload.get("autopilot_version"),
            "autopilot_status": autopilot_status,
            "requested_symbols": payload.get("requested_symbols") if isinstance(payload.get("requested_symbols"), list) else [],
            "step_count": len(steps),
            "status_counts": status_counts,
            "executed_step_count": int(payload.get("executed_step_count") or 0),
            "latest_step": dict(steps[-1]) if steps else None,
            "active_step": active_step,
            "telemetry_status": telemetry_status,
            "stale_review": stale_review,
            "stale_review_reason": (
                "manifest_status_running_without_recent_active_step_update"
                if stale_review
                else None
            ),
            "last_update_age_seconds": last_update_age_seconds,
            "blocked_reason": payload.get("blocked_reason"),
            "research_only": payload.get("research_only"),
            "observe_only": payload.get("observe_only"),
            "promotion_ready": payload.get("promotion_ready"),
        }

    def _active_research_autopilot_progress(
        self,
        job: Mapping[str, Any],
        artifacts: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        job_id = str(job.get("job_id") or "")
        manifest_path: Path | None = None
        manifest: Mapping[str, Any] | None = None
        for artifact in artifacts:
            if artifact.get("type") != "research_autopilot":
                continue
            payload = artifact.get("manifest") if isinstance(artifact.get("manifest"), Mapping) else {}
            if str(payload.get("job_id") or "") != job_id:
                continue
            path = self._existing_path(artifact.get("path"))
            if path is not None:
                manifest_path = path
            manifest = payload
            break
        if manifest is None:
            candidate = self._research_root() / "operator_runs" / "research_autopilot" / _safe_operator_path_part(job_id) / "research_autopilot_manifest.json"
            payload = self._read_json_path(candidate)
            if isinstance(payload, Mapping):
                manifest = payload
                manifest_path = candidate
        if manifest is None:
            return {
                "available": False,
                "job_id": job_id,
                "job_status": job.get("status"),
                "telemetry_status": "autopilot_manifest_missing",
            }

        steps = [step for step in manifest.get("steps") or [] if isinstance(step, Mapping)]
        latest_step = dict(steps[-1]) if steps else None
        active_step = dict(manifest.get("active_step") or {}) if isinstance(manifest.get("active_step"), Mapping) else None
        started_at = self._parse_utc_datetime(str(active_step.get("started_at_utc") or "")) if active_step else None
        if started_at is None:
            started_at = self._progress_started_at(job, manifest)
        now = datetime.now(timezone.utc)
        elapsed_seconds = max(0.0, (now - started_at).total_seconds()) if started_at is not None else None
        estimated_duration = self._positive_int_or_none(
            active_step.get("estimated_duration_seconds") if active_step else None,
            field_name="estimated_duration_seconds",
        )
        eta_seconds = None
        if elapsed_seconds is not None and estimated_duration is not None:
            eta_seconds = round(max(0.0, float(estimated_duration) - elapsed_seconds))
        telemetry_status = "active_step_recorded" if active_step else "running_without_active_step_telemetry"
        return {
            "available": True,
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "job_id": job_id,
            "job_status": job.get("status"),
            "manifest_path": str(manifest_path) if manifest_path is not None else None,
            "autopilot_status": manifest.get("autopilot_status"),
            "telemetry_status": telemetry_status,
            "current_step": active_step,
            "latest_step": latest_step,
            "step_count": len(steps),
            "executed_step_count": int(manifest.get("executed_step_count") or 0),
            "max_steps": int(manifest.get("max_steps") or 0),
            "elapsed_seconds": round(elapsed_seconds, 1) if elapsed_seconds is not None else None,
            "eta_seconds": eta_seconds,
            "estimated_duration_seconds": estimated_duration,
            "eta_basis": active_step.get("eta_basis") if active_step else None,
            "note": (
                "Current helper step is recorded before it starts."
                if active_step
                else "This running autopilot was started before active-step telemetry or has not entered a helper step yet."
            ),
        }

    @staticmethod
    def _parse_utc_datetime(value: str) -> datetime | None:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            return None

    def _research_autopilot_active_step_payload(
        self,
        *,
        key: str,
        symbol: str | None,
        attempt: int,
        max_attempts: int,
        attempt_job_id: str,
        helper_args: list[Any],
    ) -> dict[str, Any]:
        estimate = self._research_autopilot_step_estimate(key=key, helper_args=helper_args)
        return {
            "key": key,
            "status": "running",
            "symbol": symbol,
            "attempt": attempt,
            "max_attempts": max_attempts,
            "attempt_job_id": attempt_job_id,
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "estimated_duration_seconds": estimate["estimated_duration_seconds"],
            "eta_basis": estimate["eta_basis"],
            "progress_scope": estimate["progress_scope"],
            "detail": estimate["detail"],
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
        }

    def _research_autopilot_step_estimate(self, *, key: str, helper_args: list[Any]) -> dict[str, Any]:
        default_seconds = RESEARCH_AUTOPILOT_STEP_ESTIMATES_SECONDS.get(key, 300)
        detail = "Helper is running inside the autopilot worker."
        progress_scope = "helper_step"
        eta_basis = "rough_static_step_estimate"
        estimated_duration_seconds = default_seconds

        request = helper_args[0] if helper_args and isinstance(helper_args[0], Mapping) else {}
        if key == "candidate_eligibility" and isinstance(request, Mapping):
            manifest_path = self._resolve_repo_path(request.get("discovery_manifest_path"))
            manifest = self._read_optional_json(manifest_path) if manifest_path is not None and manifest_path.is_file() else None
            counts = manifest.get("counts") if isinstance((manifest or {}).get("counts"), Mapping) else {}
            interesting = self._nonnegative_int(counts.get("interesting_candidates"))
            completed = self._nonnegative_int(counts.get("completed_trials"))
            if interesting or completed:
                estimated_duration_seconds = max(10, min(900, round(8 + interesting / 1800 + completed / 250000)))
                eta_basis = "discovery_counts_candidate_eligibility_estimate"
                detail = (
                    f"Evaluating candidate-pack eligibility for {interesting} interesting discovery rows "
                    f"from {completed} completed trials."
                )
                progress_scope = "discovery_candidate_pack_eligibility"
        elif key == "exact_discovery":
            detail = "Running exact discovery; durable run_state and snapshots provide the detailed trial ETA when available."
            progress_scope = "exact_discovery"
        elif key == "historical_cycle":
            detail = "Running historical research cycle; candidate-space and backtest artifacts provide detailed ETA when available."
            progress_scope = "historical_research_cycle"
        elif key == "historical_data_catalog":
            detail = "Refreshing catalog fixtures; collection_progress.json provides archive-level ETA when available."
            progress_scope = "historical_data_catalog"
        elif key == "research_analysis":
            detail = "Writing analysis from current cycle/discovery evidence."
            progress_scope = "research_analysis"
        elif key == "research_analysis_delta":
            detail = "Writing run-to-run analysis delta."
            progress_scope = "research_analysis_delta"
        elif key == "frozen_entry_exit_lab":
            detail = "Running frozen-entry exit-lab comparisons."
            progress_scope = "frozen_entry_exit_lab"

        return {
            "estimated_duration_seconds": estimated_duration_seconds,
            "eta_basis": eta_basis,
            "progress_scope": progress_scope,
            "detail": detail,
        }

    def _dedupe_research_progress_artifacts(self, artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_path: dict[str, dict[str, Any]] = {}
        for artifact in artifacts:
            path = str(artifact.get("path") or "")
            if path:
                by_path[path] = artifact
        return sorted(by_path.values(), key=lambda item: float(item.get("sort_time") or 0.0), reverse=True)

    def _historical_data_catalog_milestone(
        self,
        jobs: list[dict[str, Any]],
        artifacts: list[dict[str, Any]],
        readiness: Mapping[str, Any],
    ) -> dict[str, Any]:
        job = self._latest_research_job(jobs, "refresh-historical-data-catalog", None)
        active = job if job and job.get("status") in {"queued", "running"} else None
        failed = job if job and job.get("status") == "failed" else None
        artifact = self._latest_research_artifact(artifacts, "historical_data_catalog", None)
        if active is not None:
            status = "running" if active.get("status") == "running" else "queued"
            detail = "Refreshing the central historical data catalog and checksum-validating active BTC/ETH archive fixtures."
            blockers: list[str] = []
        elif bool(readiness.get("candidate_evidence_ready")):
            status = "complete"
            detail = "Historical Data Catalog has active BTC/ETH candidate-depth fixture packs for this checklist."
            blockers = []
        elif failed is not None:
            status = "failed"
            detail = str(failed.get("error_text") or "Historical Data Catalog refresh failed; inspect job logs.")
            blockers = [str(failed.get("error_text"))] if failed.get("error_text") else []
        else:
            status = "ready"
            detail = (
                "Refresh the R106 Historical Data Catalog first. "
                "It is the source of truth for active fixture/spec paths and provider limitations."
            )
            blockers = []
        return {
            "key": "historical_data_catalog",
            "label": "Refresh Historical Data Catalog",
            "symbol": "BTCUSDT + ETHUSDT",
            "status": status,
            "detail": detail,
            "job_id": job.get("job_id") if job else None,
            "artifact_path": artifact.get("path") if artifact else None,
            "blockers": blockers,
        }

    def _readiness_milestone(self, readiness: Mapping[str, Any]) -> dict[str, Any]:
        ready = bool(readiness.get("ready"))
        fixture_integrity_ready = bool(readiness.get("fixture_integrity_ready"))
        blockers = list(readiness.get("primary_blockers") or [])
        if ready:
            detail = str(readiness.get("recommended_next_action") or "Durable fixtures are candidate-depth ready.")
        elif fixture_integrity_ready:
            detail = str(
                readiness.get("recommended_next_action")
                or "Current fixtures are integrity-ready screening windows only; expand durable historical data first."
            )
        else:
            detail = str(readiness.get("recommended_next_action") or "Fix durable fixture integrity before research runs.")
        return {
            "key": "durable_readiness",
            "label": "Durable data depth",
            "symbol": None,
            "status": "complete" if ready else "blocked",
            "detail": detail,
            "job_id": None,
            "artifact_path": None,
            "blockers": blockers,
        }

    def _expected_cycle_id(self, readiness: Mapping[str, Any], symbol: str) -> str:
        item = self._readiness_item(readiness, symbol)
        return str((item or {}).get("cycle_id") or f"r104-{symbol.lower()}-durable-public-archive-deep-v1")

    def _expected_discovery_run_id(self, readiness: Mapping[str, Any], symbol: str) -> str:
        item = self._readiness_item(readiness, symbol)
        return str((item or {}).get("discovery_run_id") or f"exact_entry_sweep_{symbol.lower()}_durable_r104_v1")

    @staticmethod
    def _readiness_item(readiness: Mapping[str, Any], symbol: str) -> Mapping[str, Any] | None:
        for item in readiness.get("items") or []:
            if isinstance(item, Mapping) and str(item.get("symbol") or "").upper() == symbol.upper():
                return item
        return None

    def _artifact_job_milestone(
        self,
        key: str,
        label: str,
        symbol: str | None,
        job_type: str,
        artifact_type: str,
        jobs: list[dict[str, Any]],
        artifacts: list[dict[str, Any]],
        *,
        prerequisite_complete: bool,
        require_current_evidence: bool = True,
        ready_detail: str,
        waiting_detail: str,
        expected_artifact_ids: set[str] | None = None,
    ) -> dict[str, Any]:
        artifact = self._latest_research_artifact(artifacts, artifact_type, symbol, expected_ids=expected_artifact_ids)
        artifact_status = self._required_artifact_status(artifact, key, expected_artifact_ids)
        job = self._latest_research_job(jobs, job_type, symbol)
        active = job if job and job.get("status") in {"queued", "running"} else None
        failed = job if job and job.get("status") == "failed" else None
        if active is not None:
            status = "running" if active.get("status") == "running" else "queued"
            detail = "Operator job is queued or running; progress and ETA appear above when run_state or trial records exist."
            blockers: list[str] = []
        elif require_current_evidence and prerequisite_complete and artifact_status["complete"]:
            status = "complete"
            detail = "Current required artifact is indexed with matching coverage and boundary evidence."
            blockers = []
        elif not prerequisite_complete:
            status = "waiting"
            detail = waiting_detail
            blockers = list(artifact_status["blockers"]) if artifact is not None else []
        elif failed is not None:
            status = "failed"
            detail = str(failed.get("error_text") or "Latest job failed; inspect job logs.")
            blockers = [str(failed.get("error_text"))] if failed.get("error_text") else []
        elif artifact is not None and not artifact_status["complete"] and prerequisite_complete:
            status = "blocked"
            detail = "Indexed artifact is stale or incomplete for the current required evidence path; rerun this step."
            blockers = list(artifact_status["blockers"])
        elif prerequisite_complete:
            status = "ready"
            detail = ready_detail
            blockers = []
        return {
            "key": key,
            "label": label,
            "symbol": symbol,
            "status": status,
            "detail": detail,
            "job_id": job.get("job_id") if job else None,
            "artifact_path": artifact.get("path") if artifact else None,
            "blockers": blockers,
        }

    def _required_artifact_complete(
        self,
        artifacts: list[dict[str, Any]],
        artifact_type: str,
        symbol: str | None,
        key: str,
        expected_ids: set[str] | None,
    ) -> bool:
        artifact = self._latest_research_artifact(artifacts, artifact_type, symbol, expected_ids=expected_ids)
        return bool(self._required_artifact_status(artifact, key, expected_ids)["complete"])

    def _required_artifact_status(
        self,
        artifact: Mapping[str, Any] | None,
        key: str,
        expected_ids: set[str] | None,
    ) -> dict[str, Any]:
        blockers: list[str] = []
        if artifact is None:
            return {"complete": False, "blockers": ["required_artifact_missing"]}
        manifest = artifact.get("manifest") if isinstance(artifact.get("manifest"), Mapping) else {}
        summary = artifact.get("summary") if isinstance(artifact.get("summary"), Mapping) else {}
        artifact_type = str(artifact.get("type") or "")
        identity = self._artifact_identity(artifact)
        if expected_ids is not None and identity not in expected_ids:
            blockers.append("required_artifact_id_mismatch")
        if manifest.get("research_only") is not True:
            blockers.append("research_only_flag_missing")
        if manifest.get("observe_only") is not True:
            blockers.append("observe_only_flag_missing")
        if manifest.get("promotion_ready") is not False:
            blockers.append("promotion_ready_must_be_false")

        if key in {"btc_cycle", "eth_cycle"}:
            if artifact_type != "historical_research_cycle":
                blockers.append("historical_cycle_manifest_required")
            if not str(manifest.get("cycle_id") or "").strip():
                blockers.append("cycle_id_missing")
            required_outputs = manifest.get("required_outputs") if isinstance(manifest.get("required_outputs"), Mapping) else {}
            for output_key in ("cycle_spec_resolved", "candidate_rankings", "backtest_index"):
                if output_key not in required_outputs:
                    blockers.append(f"required_output_missing:{output_key}")
            if "candidate_gate_report" not in required_outputs and "gate_report" not in required_outputs:
                blockers.append("required_output_missing:candidate_gate_report")
            plan = manifest.get("candidate_selection_performance_plan")
            if isinstance(plan, Mapping):
                materialized_count = self._nonnegative_int(plan.get("materialized_search_candidate_count"))
                equivalent_count = self._nonnegative_int(plan.get("bruteforce_equivalent_candidate_count"))
                if materialized_count < DEEP_CYCLE_MIN_MATERIALIZED_CANDIDATES:
                    blockers.append("deep_cycle_materialized_candidate_count_below_current_floor")
                if equivalent_count < 2048:
                    blockers.append("deep_cycle_bruteforce_equivalent_count_below_current_floor")
            else:
                blockers.append("candidate_selection_performance_plan_missing")
            data_source = manifest.get("data_source") if isinstance(manifest.get("data_source"), Mapping) else {}
            readiness = (
                data_source.get("durable_public_archive_readiness")
                if isinstance(data_source.get("durable_public_archive_readiness"), Mapping)
                else {}
            )
            row_count = self._nonnegative_int(readiness.get("primary_bar_count") or readiness.get("row_count"))
            if row_count and row_count < CANDIDATE_READY_PRIMARY_15M_MIN_BARS:
                blockers.append(f"cycle_primary_15m_bars_below_candidate_floor:{row_count}<{CANDIDATE_READY_PRIMARY_15M_MIN_BARS}")

        elif key in {"btc_discovery", "eth_discovery", "candidate_eligibility"} and artifact_type == "discovery_run":
            if not identity or not identity.startswith("exact_entry_sweep_"):
                blockers.append("exact_required_discovery_run_id_missing")
            state = manifest.get("state") if isinstance(manifest.get("state"), Mapping) else {}
            if state.get("status") != "completed":
                blockers.append("discovery_run_state_not_completed")
            budget = manifest.get("budget") if isinstance(manifest.get("budget"), Mapping) else {}
            search_space = manifest.get("search_space") if isinstance(manifest.get("search_space"), Mapping) else {}
            counts = manifest.get("counts") if isinstance(manifest.get("counts"), Mapping) else {}
            planned_trials = self._nonnegative_int(search_space.get("planned_trials") or budget.get("max_trials"))
            completed_trials = self._nonnegative_int(counts.get("completed_trials") or summary.get("completed_trial_count"))
            if self._nonnegative_int(budget.get("max_trials")) != 570240:
                blockers.append("exact_discovery_budget_mismatch")
            if planned_trials != 570240:
                blockers.append("exact_discovery_planned_trials_mismatch")
            if search_space.get("exhaustive") is not True:
                blockers.append("exact_discovery_not_exhaustive")
            if self._float_or_zero(search_space.get("sampled_fraction")) != 1.0:
                blockers.append("exact_discovery_sampled_fraction_mismatch")
            if completed_trials != 570240:
                blockers.append("exact_discovery_completed_trials_mismatch")
            required_outputs = manifest.get("required_outputs") if isinstance(manifest.get("required_outputs"), Mapping) else {}
            for output_key in ("discovery_spec_resolved", "run_state", "blocked_candidates", "filter_blockers", "snapshots", "trials"):
                if output_key not in required_outputs:
                    blockers.append(f"required_output_missing:{output_key}")
            data_evidence = manifest.get("data_evidence") if isinstance(manifest.get("data_evidence"), Mapping) else {}
            primary_rows = self._nonnegative_int(data_evidence.get("row_count"))
            if primary_rows and primary_rows < CANDIDATE_READY_PRIMARY_15M_MIN_BARS:
                blockers.append(f"discovery_primary_15m_bars_below_candidate_floor:{primary_rows}<{CANDIDATE_READY_PRIMARY_15M_MIN_BARS}")

        elif key == "candidate_eligibility":
            if artifact_type != "candidate_pack_eligibility":
                blockers.append("candidate_pack_eligibility_manifest_required")
            if manifest.get("candidate_pack_written") is True:
                blockers.append("candidate_pack_write_not_allowed_for_required_review")
            blockers.extend(validate_discovery_candidate_pack_bridge_manifest(manifest))
            if manifest.get("discovery_candidate_pack_bridge_version") != DISCOVERY_CANDIDATE_PACK_BRIDGE_VERSION:
                blockers.append("discovery_candidate_pack_bridge_version_required")
            if manifest.get("eligibility_artifact_version") != DISCOVERY_CANDIDATE_PACK_ELIGIBILITY_VERSION:
                blockers.append("eligibility_artifact_version_required")
            if str(manifest.get("bridge_scope") or "") != "discovery_to_existing_research_candidate_pack_validator_eligibility_only":
                blockers.append("candidate_pack_eligibility_bridge_scope_required")
            required_outputs = manifest.get("required_outputs") if isinstance(manifest.get("required_outputs"), Mapping) else {}
            for output_key in (
                "candidate_pack_eligibility_manifest",
                "candidate_pack_eligibility",
                "candidate_pack_bridge_rejections",
            ):
                if output_key not in required_outputs:
                    blockers.append(f"required_output_missing:{output_key}")
            eligibility_path = self._resolve_repo_path(required_outputs.get("candidate_pack_eligibility"))
            if eligibility_path is None or not eligibility_path.is_file():
                blockers.append("candidate_pack_eligibility_output_missing")
            elif not _is_relative_to(eligibility_path, self._research_root()):
                blockers.append("candidate_pack_eligibility_output_outside_research_root")
            else:
                expected_sha = str(manifest.get("candidate_pack_eligibility_sha256") or "")
                if not expected_sha:
                    blockers.append("candidate_pack_eligibility_sha256_missing")
                elif self._file_sha256(eligibility_path) != expected_sha:
                    blockers.append("candidate_pack_eligibility_sha256_mismatch")
            if not str(manifest.get("source_discovery_manifest_sha256") or ""):
                blockers.append("source_discovery_manifest_sha256_missing")
            if not str(manifest.get("source_cycle_manifest_sha256") or ""):
                blockers.append("source_cycle_manifest_sha256_missing")

        elif key == "research_analysis":
            if artifact_type != "research_analysis":
                blockers.append("research_analysis_artifact_required")
            if not str(manifest.get("analysis_version") or "").strip():
                blockers.append("research_analysis_version_missing")
            cycle = manifest.get("cycle") if isinstance(manifest.get("cycle"), Mapping) else {}
            discovery = manifest.get("discovery") if isinstance(manifest.get("discovery"), Mapping) else {}
            if not bool(cycle.get("available")) and not bool(discovery.get("available")):
                blockers.append("research_analysis_input_evidence_missing")

        elif key == "research_analysis_delta":
            if artifact_type != "research_analysis_delta":
                blockers.append("research_analysis_delta_artifact_required")
            if not str(manifest.get("delta_version") or "").strip():
                blockers.append("research_analysis_delta_version_missing")
            current = manifest.get("current") if isinstance(manifest.get("current"), Mapping) else {}
            if not str(current.get("analysis_path") or "").strip():
                blockers.append("research_analysis_delta_current_analysis_missing")

        elif key == "frozen_entry_exit_lab":
            if artifact_type != "discovery_exit_lab":
                blockers.append("discovery_exit_lab_artifact_required")
            if not str(manifest.get("exit_lab_version") or "").strip():
                blockers.append("discovery_exit_lab_version_missing")
            if str(manifest.get("exit_lab_scope") or "") != "frozen_entry_primary_bar_exit_comparison":
                blockers.append("frozen_entry_exit_lab_scope_required")
            required_outputs = manifest.get("required_outputs") if isinstance(manifest.get("required_outputs"), Mapping) else {}
            if "discovery_exit_lab_candidate_gates" not in required_outputs:
                blockers.append("required_output_missing:discovery_exit_lab_candidate_gates")

        return {"complete": not blockers, "blockers": sorted(set(blockers))}

    def _active_historical_data_progress(self, job: Mapping[str, Any]) -> dict[str, Any] | None:
        job_id = str(job.get("job_id") or "")
        if not job_id:
            return None
        research_root = self._research_root()
        safe_job_id = _safe_operator_path_part(job_id)
        progress_path = research_root / "operator_runs" / "historical_data" / safe_job_id / "sources" / "binance_vision_public_archive" / "collection_progress.json"
        return self._read_historical_data_progress(progress_path, job=job)

    def _latest_historical_data_progress(self) -> dict[str, Any] | None:
        research_root = self._research_root()
        candidates = sorted(
            research_root.glob("operator_runs/historical_data/*/sources/binance_vision_public_archive/collection_progress.json"),
            key=lambda path: path.stat().st_mtime if path.exists() else 0,
            reverse=True,
        )
        if not candidates:
            return None
        return self._read_historical_data_progress(candidates[0], job=None)

    def _read_historical_data_progress(self, progress_path: Path, *, job: Mapping[str, Any] | None) -> dict[str, Any] | None:
        payload = self._read_json_path(progress_path)
        if not isinstance(payload, Mapping):
            return None
        return {
            "job_id": str(job.get("job_id")) if job else None,
            "status": str(payload.get("status") or "unknown"),
            "completed_archive_steps": self._nonnegative_int(payload.get("completed_archive_steps")),
            "total_archive_steps": self._nonnegative_int(payload.get("total_archive_steps")),
            "percent_complete": self._float_or_zero(payload.get("percent_complete")),
            "eta_seconds": payload.get("eta_seconds"),
            "elapsed_seconds": payload.get("elapsed_seconds"),
            "archive_steps_per_minute": payload.get("archive_steps_per_minute"),
            "current": payload.get("current"),
            "updated_at": payload.get("updated_at"),
            "progress_path": str(progress_path),
        }

    def _active_historical_cycle_progress(self, job: Mapping[str, Any]) -> dict[str, Any] | None:
        request = job.get("request") if isinstance(job.get("request"), Mapping) else {}
        raw_spec_path = request.get("spec_path")
        if not raw_spec_path:
            return None
        try:
            spec = HistoricalResearchCycleSpec.from_path(Path(str(raw_spec_path)))
        except Exception as exc:
            return {"available": False, "error": str(exc), "job_id": job.get("job_id")}
        job_id = str(job.get("job_id") or "")
        safe_job_id = _safe_operator_path_part(job_id or "operator-job")
        safe_cycle_id = _safe_operator_path_part(spec.cycle_id)
        output_dir = (self._research_root() / "operator_runs" / "historical_cycles" / safe_cycle_id / safe_job_id).resolve()
        return self._historical_cycle_progress_from_output_dir(
            output_dir,
            cycle_id=spec.cycle_id,
            symbol=spec.symbol,
            job=job,
        )

    def _historical_cycle_progress_from_output_dir(
        self,
        output_dir: Path,
        *,
        cycle_id: str,
        symbol: str,
        job: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        cycle_spec_path = output_dir / "cycle_spec_resolved.json"
        data_quality_path = output_dir / "data_quality_report.json"
        feature_build_path = output_dir / "feature_build_manifest.json"
        split_manifest_path = output_dir / "split_manifest.json"
        candidate_space_path = output_dir / "candidate_space_manifest.json"
        candidate_rankings_path = output_dir / "candidate_rankings.parquet"
        backtest_index_path = output_dir / "backtest_index.parquet"
        gate_report_path = output_dir / "candidate_gate_report.parquet"
        manifest_path = output_dir / "research_cycle_manifest.json"

        candidate_space = self._read_json_path(candidate_space_path)
        candidate_payload = candidate_space if isinstance(candidate_space, Mapping) else {}
        cycle_spec = self._read_json_path(cycle_spec_path)
        cycle_payload = cycle_spec if isinstance(cycle_spec, Mapping) else {}
        split_manifest = self._read_json_path(split_manifest_path)
        split_payload = split_manifest if isinstance(split_manifest, Mapping) else {}
        performance_plan = (
            candidate_payload.get("performance_plan")
            if isinstance(candidate_payload.get("performance_plan"), Mapping)
            else {}
        )
        compute_policy = (
            candidate_payload.get("compute_policy")
            if isinstance(candidate_payload.get("compute_policy"), Mapping)
            else performance_plan.get("compute_policy") if isinstance(performance_plan.get("compute_policy"), Mapping) else {}
        )
        total_candidates = self._nonnegative_int(performance_plan.get("materialized_search_candidate_count"))
        if total_candidates == 0:
            total_candidates = self._nonnegative_int(candidate_payload.get("candidate_count"))
        completed_candidates = self._count_direct_backtest_manifests(output_dir / "backtests")
        completed_backtest_evaluations = self._count_recursive_backtest_manifests(output_dir / "backtests")
        optimizer = cycle_payload.get("optimizer") if isinstance(cycle_payload.get("optimizer"), Mapping) else {}
        top_regions_to_refine = self._nonnegative_int(optimizer.get("top_regions_to_refine"))
        split_count = self._nonnegative_int(split_payload.get("split_count"))
        total_backtest_evaluations = total_candidates
        if top_regions_to_refine and split_count:
            total_backtest_evaluations += top_regions_to_refine * (split_count + CYCLE_COST_STRESS_SCENARIO_COUNT)
        if candidate_rankings_path.exists() and total_candidates:
            completed_candidates = max(completed_candidates, total_candidates)
        if manifest_path.exists() and total_candidates:
            completed_candidates = total_candidates
            completed_backtest_evaluations = max(completed_backtest_evaluations, total_backtest_evaluations)
        denominator = max(total_backtest_evaluations, completed_backtest_evaluations, total_candidates, completed_candidates, 1)
        percent = round((completed_backtest_evaluations / denominator) * 100, 2)
        aggregate_percent = round((completed_candidates / max(total_candidates, completed_candidates, 1)) * 100, 2)
        if manifest_path.exists():
            percent = 100.0
            phase = "complete"
        elif candidate_rankings_path.exists() or backtest_index_path.exists() or gate_report_path.exists():
            phase = "finalizing_reports"
            percent = max(percent, 95.0)
        elif total_backtest_evaluations > total_candidates and completed_candidates >= total_candidates:
            phase = "split_cost_stress_backtests"
        elif candidate_space_path.exists():
            phase = "aggregate_backtests"
        elif split_manifest_path.exists():
            phase = "building_candidate_space"
        elif feature_build_path.exists():
            phase = "building_splits"
        elif data_quality_path.exists():
            phase = "building_features"
        elif cycle_spec_path.exists():
            phase = "loading_data"
        elif output_dir.exists():
            phase = "preparing_output"
        else:
            phase = "queued"

        started_at = self._progress_started_at(job, {})
        if candidate_space_path.exists():
            try:
                started_at = datetime.fromtimestamp(candidate_space_path.stat().st_mtime, tz=timezone.utc)
            except OSError:
                pass
        now = datetime.now(timezone.utc)
        elapsed_seconds = max(0.0, (now - started_at).total_seconds()) if started_at is not None else None
        candidates_per_minute = (
            round(completed_candidates / max(elapsed_seconds / 60.0, 1e-9), 2)
            if elapsed_seconds is not None and completed_candidates > 0
            else None
        )
        backtest_evaluations_per_minute = (
            round(completed_backtest_evaluations / max(elapsed_seconds / 60.0, 1e-9), 2)
            if elapsed_seconds is not None and completed_backtest_evaluations > 0
            else None
        )
        eta_seconds = None
        if elapsed_seconds is not None and completed_backtest_evaluations > 0 and total_backtest_evaluations:
            rate = completed_backtest_evaluations / max(elapsed_seconds, 1e-9)
            eta_seconds = round(max(0, total_backtest_evaluations - completed_backtest_evaluations) / max(rate, 1e-9))

        return {
            "available": job is not None or output_dir.exists(),
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "cycle_id": cycle_id,
            "symbol": symbol,
            "job_id": job.get("job_id") if job is not None else None,
            "job_status": job.get("status") if job is not None else None,
            "output_dir": str(output_dir),
            "phase": phase,
            "progress_scope": "aggregate_candidate_backtests",
            "candidate_space_manifest_path": str(candidate_space_path) if candidate_space_path.exists() else None,
            "completed_candidates": completed_candidates,
            "total_candidates": total_candidates,
            "remaining_candidates": max(0, total_candidates - completed_candidates),
            "aggregate_percent": aggregate_percent,
            "completed_backtest_evaluations": completed_backtest_evaluations,
            "total_backtest_evaluations": total_backtest_evaluations,
            "remaining_backtest_evaluations": max(0, total_backtest_evaluations - completed_backtest_evaluations),
            "percent": percent,
            "candidate_backtests_per_minute": candidates_per_minute,
            "backtest_evaluations_per_minute": backtest_evaluations_per_minute,
            "elapsed_seconds": round(elapsed_seconds, 1) if elapsed_seconds is not None else None,
            "eta_seconds": eta_seconds,
            "bruteforce_equivalent_candidate_count": self._nonnegative_int(performance_plan.get("bruteforce_equivalent_candidate_count")),
            "sampled_fraction_of_bruteforce": performance_plan.get("sampled_fraction_of_bruteforce"),
            "bruteforce_avoidance_ratio": performance_plan.get("bruteforce_avoidance_ratio"),
            "search_mode": candidate_payload.get("search_mode"),
            "search_method": candidate_payload.get("search_method"),
            "top_regions_to_refine": top_regions_to_refine,
            "split_count": split_count,
            "cost_stress_scenario_count": CYCLE_COST_STRESS_SCENARIO_COUNT if top_regions_to_refine and split_count else 0,
            "compute_policy": compute_policy,
            "required_outputs": {
                "cycle_spec_resolved": str(cycle_spec_path) if cycle_spec_path.exists() else None,
                "data_quality_report": str(data_quality_path) if data_quality_path.exists() else None,
                "feature_build_manifest": str(feature_build_path) if feature_build_path.exists() else None,
                "split_manifest": str(split_manifest_path) if split_manifest_path.exists() else None,
                "candidate_rankings": str(candidate_rankings_path) if candidate_rankings_path.exists() else None,
                "backtest_index": str(backtest_index_path) if backtest_index_path.exists() else None,
                "candidate_gate_report": str(gate_report_path) if gate_report_path.exists() else None,
                "research_cycle_manifest": str(manifest_path) if manifest_path.exists() else None,
            },
        }

    def _active_discovery_progress(self, job: Mapping[str, Any]) -> dict[str, Any] | None:
        request = job.get("request") if isinstance(job.get("request"), Mapping) else {}
        raw_spec_path = request.get("spec_path")
        if not raw_spec_path:
            return None
        try:
            spec = DiscoveryRunSpec.from_path(Path(str(raw_spec_path)))
        except Exception as exc:
            return {"available": False, "error": str(exc), "job_id": job.get("job_id")}
        output_dir = self._discovery_output_dir_for_job_request(spec, job)
        return self._discovery_progress_from_output_dir(
            output_dir,
            run_id=spec.run_id,
            job=job,
            total_trials=spec.budget.max_trials,
        )

    def _latest_incomplete_discovery_progress(self, artifacts: list[dict[str, Any]]) -> dict[str, Any] | None:
        for artifact in artifacts:
            if artifact.get("type") != "discovery_run":
                continue
            manifest = artifact.get("manifest") if isinstance(artifact.get("manifest"), Mapping) else {}
            state = manifest.get("state") if isinstance(manifest.get("state"), Mapping) else {}
            if state.get("status") == "completed":
                continue
            required_outputs = manifest.get("required_outputs") if isinstance(manifest.get("required_outputs"), Mapping) else {}
            run_state_path = self._existing_path(required_outputs.get("run_state"))
            if run_state_path is None:
                continue
            return self._discovery_progress_from_output_dir(
                run_state_path.parent,
                run_id=str(manifest.get("run_id") or ""),
                job=None,
                total_trials=self._nonnegative_int((manifest.get("budget") or {}).get("max_trials") if isinstance(manifest.get("budget"), Mapping) else 0),
            )
        return None

    def _discovery_output_dir_for_job_request(self, spec: DiscoveryRunSpec, job: Mapping[str, Any]) -> Path:
        request = job.get("request") if isinstance(job.get("request"), Mapping) else {}
        research_root = self._research_root()
        safe_job_id = _safe_operator_path_part(str(job.get("job_id") or "operator-job"))
        safe_run_id = _safe_operator_path_part(spec.run_id)
        stable = (
            bool(request.get("stable_run_id"))
            or bool(request.get("resume"))
            or request.get("stop_after_trials") is not None
        )
        if stable:
            return (research_root / "operator_runs" / "discovery_runs" / safe_run_id).resolve()
        return (research_root / "operator_runs" / "discovery_runs" / safe_run_id / safe_job_id).resolve()

    def _discovery_progress_from_output_dir(
        self,
        output_dir: Path,
        *,
        run_id: str,
        job: Mapping[str, Any] | None,
        total_trials: int,
    ) -> dict[str, Any]:
        state_path = output_dir / "run_state.json"
        state = self._read_json_path(state_path)
        state_payload = state if isinstance(state, Mapping) else {}
        completed_from_state = len(state_payload.get("completed_trial_ids") or [])
        trial_record_count = completed_from_state
        trials_dir = output_dir / "trials"
        if trials_dir.is_dir() and completed_from_state == 0:
            trial_record_count = self._count_json_files(trials_dir)
        completed_trials = max(completed_from_state, trial_record_count)
        total = max(total_trials, completed_trials, 1)
        percent = round((completed_trials / total) * 100, 2)
        started_at = self._progress_started_at(job, state_payload)
        now = datetime.now(timezone.utc)
        elapsed_seconds = max(0.0, (now - started_at).total_seconds()) if started_at is not None else None
        trials_per_minute = (
            round(completed_trials / max(elapsed_seconds / 60.0, 1e-9), 2)
            if elapsed_seconds is not None and completed_trials > 0
            else None
        )
        eta_seconds = None
        if elapsed_seconds is not None and completed_trials > 0:
            rate = completed_trials / max(elapsed_seconds, 1e-9)
            eta_seconds = round((total - completed_trials) / max(rate, 1e-9))
        latest_snapshot_path = str(state_payload.get("last_snapshot_path") or "")
        if not latest_snapshot_path:
            latest_snapshot = self._latest_snapshot_path(output_dir / "snapshots")
            latest_snapshot_path = str(latest_snapshot) if latest_snapshot is not None else ""
        manifest_payload = self._read_json_path(output_dir / "discovery_run_manifest.json")
        performance = (
            self._discovery_performance_summary(manifest_payload)
            if isinstance(manifest_payload, Mapping)
            else {}
        )
        return {
            "available": job is not None or state_path.exists() or trials_dir.exists(),
            "run_id": run_id,
            "job_id": job.get("job_id") if job is not None else None,
            "job_status": job.get("status") if job is not None else state_payload.get("status"),
            "output_dir": str(output_dir),
            "run_state_path": str(state_path) if state_path.exists() else None,
            "completed_trials": completed_trials,
            "completed_trials_from_state": completed_from_state,
            "completed_trials_from_records": trial_record_count,
            "total_trials": total,
            "remaining_trials": max(0, total - completed_trials),
            "percent": percent,
            "trials_per_minute": trials_per_minute,
            "elapsed_seconds": round(elapsed_seconds, 1) if elapsed_seconds is not None else None,
            "eta_seconds": eta_seconds,
            "latest_snapshot_path": latest_snapshot_path or None,
            "snapshot_count": state_payload.get("snapshot_count"),
            "state_status": state_payload.get("status"),
            "performance": performance,
        }

    def _progress_started_at(self, job: Mapping[str, Any] | None, state: Mapping[str, Any]) -> datetime | None:
        created_at = str(state.get("created_at_utc") or "").strip()
        if created_at:
            try:
                return datetime.fromisoformat(created_at.replace("Z", "+00:00")).astimezone(timezone.utc)
            except ValueError:
                pass
        raw_ms = None
        if job is not None:
            raw_ms = job.get("started_at_ms") or job.get("requested_at_ms")
        try:
            return datetime.fromtimestamp(float(raw_ms) / 1000.0, tz=timezone.utc) if raw_ms is not None else None
        except (TypeError, ValueError, OSError):
            return None

    @staticmethod
    def _count_json_files(path: Path) -> int:
        try:
            return sum(1 for item in path.iterdir() if item.is_file() and item.suffix == ".json")
        except OSError:
            return 0

    @staticmethod
    def _count_direct_backtest_manifests(path: Path) -> int:
        try:
            children = list(path.iterdir())
        except OSError:
            return 0
        return sum(1 for item in children if item.is_dir() and (item / "backtest_manifest.json").is_file())

    @staticmethod
    def _count_recursive_backtest_manifests(path: Path) -> int:
        try:
            return sum(1 for item in path.rglob("backtest_manifest.json") if item.is_file())
        except OSError:
            return 0

    @staticmethod
    def _float_or_zero(value: object) -> float:
        try:
            return float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _latest_snapshot_path(path: Path) -> Path | None:
        try:
            snapshots = [item for item in path.iterdir() if item.is_file() and item.name.endswith("_snapshot.json")]
        except OSError:
            return None
        return max(snapshots, key=lambda item: item.stat().st_mtime) if snapshots else None

    def _research_next_action(self, milestones: list[dict[str, Any]], active_job: Mapping[str, Any] | None) -> str:
        if active_job is not None:
            return f"Wait for {active_job.get('job_type')} to finish; use the progress bar and ETA to decide whether to pause or resume later."
        for milestone in milestones:
            status = str(milestone.get("status") or "")
            if status == "failed":
                return f"Inspect failed {milestone.get('label')} job logs before queueing another run."
            if status == "blocked":
                return str(milestone.get("detail") or "Resolve blockers before continuing.")
            if status == "ready":
                if milestone.get("key") == "historical_data_catalog":
                    return str(milestone.get("detail") or "Run Refresh Historical Data Catalog.")
                return f"Run {milestone.get('label')}."
            if status == "waiting":
                return str(milestone.get("detail") or "Complete the prerequisite step.")
        return "All required research milestones are complete; inspect eligibility blockers and keep outputs research-only."

    def _latest_research_artifact(
        self,
        artifacts: list[dict[str, Any]],
        artifact_type: str,
        symbol: str | None,
        expected_ids: set[str] | None = None,
    ) -> dict[str, Any] | None:
        for artifact in artifacts:
            if artifact.get("type") != artifact_type:
                continue
            if symbol is None or self._research_symbol_from_payload(artifact) == symbol:
                if expected_ids is None or self._artifact_identity(artifact) in expected_ids:
                    return artifact
        return None

    def _artifact_identity(self, artifact: Mapping[str, Any]) -> str | None:
        summary = artifact.get("summary") if isinstance(artifact.get("summary"), Mapping) else {}
        manifest = artifact.get("manifest") if isinstance(artifact.get("manifest"), Mapping) else {}
        for value in (
            summary.get("run_id"),
            summary.get("cycle_id"),
            manifest.get("run_id"),
            manifest.get("cycle_id"),
        ):
            if value is not None and str(value).strip():
                return str(value)
        return None

    def _latest_research_job(
        self,
        jobs: list[dict[str, Any]],
        job_type: str,
        symbol: str | None,
    ) -> dict[str, Any] | None:
        active = [
            job for job in jobs
            if job.get("job_type") == job_type
            and (symbol is None or self._research_symbol_from_payload(job) == symbol)
            and job.get("status") in {"queued", "running"}
        ]
        if active:
            return active[0]
        for job in jobs:
            if job.get("job_type") == job_type and (symbol is None or self._research_symbol_from_payload(job) == symbol):
                return job
        return None

    def _research_symbol_from_payload(self, payload: Mapping[str, Any]) -> str | None:
        summary = payload.get("summary") if isinstance(payload.get("summary"), Mapping) else {}
        manifest = payload.get("manifest") if isinstance(payload.get("manifest"), Mapping) else {}
        request = payload.get("request") if isinstance(payload.get("request"), Mapping) else {}
        values = [
            summary.get("symbol"),
            manifest.get("symbol"),
            summary.get("cycle_id"),
            summary.get("run_id"),
            manifest.get("source_discovery_manifest_path"),
            manifest.get("source_cycle_manifest_path"),
            request.get("spec_path"),
            payload.get("path"),
        ]
        text = " ".join(str(value) for value in values if value is not None).lower()
        if "ethusdt" in text:
            return "ETHUSDT"
        if "btcusdt" in text:
            return "BTCUSDT"
        return None

    def list_artifacts(self) -> list[dict[str, Any]]:
        base_dir = self.config.research.output_dir
        if not base_dir.exists():
            return []
        artifacts: list[dict[str, Any]] = []
        artifact_paths = self._artifact_path_index(base_dir)
        for train_manifest in sorted(self._artifact_paths_from_index(artifact_paths, "train_manifest.json")):
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
        for manifest_path in sorted(self._artifact_paths_from_index(artifact_paths, "artifact_manifest.json")):
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
        for dataset_manifest in sorted(self._artifact_paths_from_index(artifact_paths, "dataset_manifest.json")):
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
        for pipeline_summary in sorted(self._artifact_paths_from_index(artifact_paths, "pipeline_summary.json")):
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
        for intake_manifest in sorted(self._artifact_paths_from_index(artifact_paths, "data_intake_manifest.json")):
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
        for data_quality_report in sorted(self._artifact_paths_from_index(artifact_paths, "data_quality_report.json")):
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
        for catalog_path in sorted(self._artifact_paths_from_index(artifact_paths, "historical_data_catalog.json")):
            payload = self._read_json_artifact(artifacts, catalog_path, "historical_data_catalog")
            if payload is None:
                continue
            symbols = payload.get("symbols") if isinstance(payload.get("symbols"), Mapping) else {}
            provider_states = payload.get("provider_states") if isinstance(payload.get("provider_states"), Mapping) else {}
            artifacts.append(
                {
                    "type": "historical_data_catalog",
                    "path": str(catalog_path),
                    "sort_time": catalog_path.stat().st_mtime,
                    "manifest": payload,
                    "summary": {
                        "source_name": ((payload.get("active_source") or {}).get("source_name") if isinstance(payload.get("active_source"), Mapping) else None),
                        "start_month": payload.get("start_month"),
                        "end_month": payload.get("end_month"),
                        "symbol_count": len(symbols),
                        "provider_count": len(provider_states),
                        "candidate_depth_ready": payload.get("candidate_depth_ready"),
                        "catalog_ready": payload.get("catalog_ready"),
                        "promotion_ready": payload.get("promotion_ready"),
                        "research_only": payload.get("research_only"),
                        "observe_only": payload.get("observe_only"),
                    },
                }
            )
        for collection_summary in sorted(self._artifact_paths_from_index(artifact_paths, "durable_fixture_collection_summary.json")):
            payload = self._read_json_artifact(artifacts, collection_summary, "durable_data_collection")
            if payload is None:
                continue
            symbols = payload.get("symbols") if isinstance(payload.get("symbols"), Mapping) else {}
            row_counts = {
                str(symbol): dict((item.get("row_counts") or {})) if isinstance(item, Mapping) else {}
                for symbol, item in sorted(symbols.items())
            }
            artifacts.append(
                {
                    "type": "durable_data_collection",
                    "path": str(collection_summary),
                    "sort_time": collection_summary.stat().st_mtime,
                    "manifest": payload,
                    "summary": {
                        "source_name": payload.get("source_name"),
                        "start_month": payload.get("start_month"),
                        "end_month": payload.get("end_month"),
                        "symbol_count": len(symbols),
                        "row_counts": row_counts,
                        "promotion_ready": payload.get("promotion_ready"),
                        "research_only": payload.get("research_only"),
                        "observe_only": payload.get("observe_only"),
                    },
                }
            )
        for modern_profile in sorted(self._artifact_paths_from_index(artifact_paths, "modern_window_profile.json")):
            payload = self._read_json_artifact(artifacts, modern_profile, "modern_window_profile")
            if payload is None:
                continue
            artifacts.append(
                {
                    "type": "modern_window_profile",
                    "path": str(modern_profile),
                    "sort_time": modern_profile.stat().st_mtime,
                    "manifest": payload,
                    "summary": self._modern_window_profile_summary(payload),
                }
            )
        for market_journal_manifest in sorted(self._artifact_paths_from_index(artifact_paths, "market_journal_manifest.json")):
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
        for provider_manifest in sorted(self._artifact_paths_from_index(artifact_paths, "*.manifest.json")):
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
        for experiment_manifest in sorted(self._artifact_paths_from_index(artifact_paths, "experiment_manifest.json")):
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
        for experiment_run_manifest in sorted(self._artifact_paths_from_index(artifact_paths, "experiment_run_manifest.json")):
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
        for cycle_manifest in sorted(self._artifact_paths_from_index(artifact_paths, "research_cycle_manifest.json")):
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
        for discovery_manifest in sorted(self._artifact_paths_from_index(artifact_paths, "discovery_run_manifest.json")):
            payload = self._read_json_artifact(artifacts, discovery_manifest, "discovery_run")
            if payload is None:
                continue
            required_outputs = payload.get("required_outputs") if isinstance(payload.get("required_outputs"), dict) else {}
            search_space = payload.get("search_space") if isinstance(payload.get("search_space"), dict) else {}
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
                        "search_space": search_space,
                        "search_space_total_combinations": search_space.get("total_combinations"),
                        "search_space_planned_trials": search_space.get("planned_trials"),
                        "search_space_sampled_fraction": search_space.get("sampled_fraction"),
                        "search_space_exhaustive": search_space.get("exhaustive"),
                        "search_space_coverage_label": search_space.get("coverage_label"),
                        "candidate_pack_written": payload.get("candidate_pack_written"),
                        "candidate_acceptance_scope": payload.get("candidate_acceptance_scope"),
                        "runtime_seconds": ((payload.get("runtime") or {}).get("elapsed_seconds")),
                        "research_only": payload.get("research_only"),
                        "observe_only": payload.get("observe_only"),
                        "promotion_ready": payload.get("promotion_ready"),
                        "counts": payload.get("counts") or {},
                        "performance": self._discovery_performance_summary(payload),
                        "interesting_candidates": self._summarize_discovery_ledger(required_outputs.get("interesting_candidates")),
                        "blocked_candidates": self._summarize_discovery_ledger(required_outputs.get("blocked_candidates")),
                        "filter_blockers": self._summarize_discovery_ledger(required_outputs.get("filter_blockers")),
                        "latest_snapshot": self._summarize_discovery_snapshot(required_outputs.get("snapshots")),
                    },
                }
            )
        for measurement_summary in sorted(self._artifact_paths_from_index(artifact_paths, "measurement_summary.json")):
            if "performance_utilization" not in str(measurement_summary).lower():
                continue
            payload = self._read_json_artifact(artifacts, measurement_summary, "performance_utilization_study")
            if payload is None:
                continue
            artifacts.append(
                {
                    "type": "performance_utilization_study",
                    "path": str(measurement_summary),
                    "sort_time": measurement_summary.stat().st_mtime,
                    "manifest": payload,
                    "summary": self._performance_utilization_study_summary(payload),
                }
            )
        for analysis_path in sorted(self._artifact_paths_from_index(artifact_paths, "research_analysis.json")):
            payload = self._read_json_artifact(artifacts, analysis_path, "research_analysis")
            if payload is None:
                continue
            markdown_path = analysis_path.with_suffix(".md")
            artifacts.append(
                {
                    "type": "research_analysis",
                    "path": str(analysis_path),
                    "sort_time": analysis_path.stat().st_mtime,
                    "manifest": payload,
                    "markdown_path": str(markdown_path) if markdown_path.exists() else None,
                    "summary": self._research_analysis_summary(payload),
                }
            )
        for delta_path in sorted(self._artifact_paths_from_index(artifact_paths, "research_analysis_delta.json")):
            payload = self._read_json_artifact(artifacts, delta_path, "research_analysis_delta")
            if payload is None:
                continue
            markdown_path = delta_path.with_suffix(".md")
            artifacts.append(
                {
                    "type": "research_analysis_delta",
                    "path": str(delta_path),
                    "sort_time": delta_path.stat().st_mtime,
                    "manifest": payload,
                    "markdown_path": str(markdown_path) if markdown_path.exists() else None,
                    "summary": self._research_analysis_delta_summary(payload),
                }
            )
        for autopilot_manifest in sorted(self._artifact_paths_from_index(artifact_paths, "research_autopilot_manifest.json")):
            payload = self._read_json_artifact(artifacts, autopilot_manifest, "research_autopilot")
            if payload is None:
                continue
            artifacts.append(
                {
                    "type": "research_autopilot",
                    "path": str(autopilot_manifest),
                    "sort_time": autopilot_manifest.stat().st_mtime,
                    "manifest": payload,
                    "summary": self._research_autopilot_summary(payload),
                }
            )
        for exit_lab_manifest in sorted(self._artifact_paths_from_index(artifact_paths, "discovery_exit_lab_manifest.json")):
            payload = self._read_json_artifact(artifacts, exit_lab_manifest, "discovery_exit_lab")
            if payload is None:
                continue
            artifacts.append(
                {
                    "type": "discovery_exit_lab",
                    "path": str(exit_lab_manifest),
                    "sort_time": exit_lab_manifest.stat().st_mtime,
                    "manifest": payload,
                    "summary": self._discovery_exit_lab_summary(payload),
                }
            )
        for multiple_testing_manifest in sorted(self._artifact_paths_from_index(artifact_paths, "discovery_multiple_testing_manifest.json")):
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
        for validation_floors_manifest in sorted(self._artifact_paths_from_index(artifact_paths, "discovery_validation_floors_manifest.json")):
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
        for bridge_manifest in sorted(self._artifact_paths_from_index(artifact_paths, "candidate_pack_eligibility_manifest.json")):
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
        for hardware_manifest in sorted(self._artifact_paths_from_index(artifact_paths, "hardware_utilization_report.json")):
            payload = self._read_json_artifact(artifacts, hardware_manifest, "hardware_utilization")
            if payload is None:
                continue
            cpu_probe = payload.get("cpu_probe") if isinstance(payload.get("cpu_probe"), dict) else {}
            gpu_probe = payload.get("gpu_probe") if isinstance(payload.get("gpu_probe"), dict) else {}
            recommendations = payload.get("recommendations") if isinstance(payload.get("recommendations"), dict) else {}
            readiness = (
                payload.get("prolonged_study_readiness")
                if isinstance(payload.get("prolonged_study_readiness"), dict)
                else {}
            )
            cpu_saturation_target_met = (
                cpu_probe.get("worker_capacity_saturation_status") == "saturated"
                if "worker_capacity_saturation_status" in cpu_probe
                else bool(readiness.get("cpu_worker_saturation_target_met", False))
            )
            artifacts.append(
                {
                    "type": "hardware_utilization",
                    "path": str(hardware_manifest),
                    "sort_time": hardware_manifest.stat().st_mtime,
                    "manifest": payload,
                    "summary": {
                        "cpu_probe_succeeded": cpu_probe.get("probe_succeeded"),
                        "gpu_probe_succeeded": gpu_probe.get("probe_succeeded"),
                        "cpu_workers": cpu_probe.get("active_workers"),
                        "logical_cpu_count": cpu_probe.get("logical_cpu_count"),
                        "physical_cpu_count": cpu_probe.get("physical_cpu_count"),
                        "cpu_worker_capacity_percent": cpu_probe.get("process_cpu_percent_of_worker_capacity"),
                        "cpu_logical_capacity_percent": cpu_probe.get("process_cpu_percent_of_logical_capacity"),
                        "cpu_worker_saturation_status": cpu_probe.get("worker_capacity_saturation_status"),
                        "cpu_logical_saturation_status": cpu_probe.get("logical_capacity_saturation_status"),
                        "cpu_saturation_target_met": cpu_saturation_target_met,
                        "ready_for_long_cpu_bound_research": cpu_saturation_target_met,
                        "gpu_execution_status": gpu_probe.get("gpu_execution_status"),
                        "gpu_name": ((gpu_probe.get("runtime_evidence") or {}).get("gpu_name")),
                        "gpu_gflops": gpu_probe.get("approx_gflops_per_second"),
                        "best_option": recommendations.get("best_option"),
                        "promotion_ready": payload.get("promotion_ready"),
                        "research_only": payload.get("research_only"),
                        "observe_only": payload.get("observe_only"),
                    },
                }
            )
        artifacts.sort(key=lambda item: float(item.get("sort_time") or 0.0), reverse=True)
        for artifact in artifacts:
            artifact.pop("sort_time", None)
        return artifacts

    def _artifact_path_index(self, base_dir: Path) -> dict[str, list[Path]]:
        if not base_dir.exists():
            return {}
        index: dict[str, list[Path]] = {}
        for dirpath, dirnames, filenames in os.walk(base_dir):
            dirnames[:] = [
                name
                for name in dirnames
                if name not in self._ARTIFACT_SCAN_SKIP_DIRS and not name.startswith(".")
            ]
            for filename in filenames:
                if not self._is_artifact_manifest_filename(filename):
                    continue
                path = Path(dirpath) / filename
                bucket = index.setdefault(filename, [])
                if len(bucket) < self._ARTIFACT_SCAN_MAX_MATCHES_PER_PATTERN:
                    bucket.append(path)
        return index

    def _artifact_paths_from_index(self, index: Mapping[str, list[Path]], pattern: str) -> list[Path]:
        if pattern.startswith("*."):
            matches: list[Path] = []
            for filename, paths in index.items():
                if filename.endswith(pattern[1:]):
                    matches.extend(paths)
            return matches[: self._ARTIFACT_SCAN_MAX_MATCHES_PER_PATTERN]
        return list(index.get(pattern, []))

    @staticmethod
    def _is_artifact_manifest_filename(filename: str) -> bool:
        return (
            filename.endswith(".manifest.json")
            or filename
            in {
                "artifact_manifest.json",
                "candidate_pack_eligibility_manifest.json",
                "data_intake_manifest.json",
                "data_quality_report.json",
                "dataset_manifest.json",
                "durable_fixture_collection_summary.json",
                "discovery_exit_lab_manifest.json",
                "discovery_multiple_testing_manifest.json",
                "discovery_run_manifest.json",
                "discovery_validation_floors_manifest.json",
                "experiment_manifest.json",
                "experiment_run_manifest.json",
                "hardware_utilization_report.json",
                "historical_data_catalog.json",
                "market_journal_manifest.json",
                "measurement_summary.json",
                "modern_window_profile.json",
                "pipeline_summary.json",
                "research_analysis.json",
                "research_analysis_delta.json",
                "research_autopilot_manifest.json",
                "research_cycle_manifest.json",
                "train_manifest.json",
            }
        )

    def _read_json_artifact(self, artifacts: list[dict[str, Any]], path: Path, artifact_type: str) -> dict[str, Any] | None:
        try:
            if artifact_type == "historical_data_catalog":
                payload = read_historical_data_catalog(path)
            else:
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

    def _read_historical_data_catalog_path(self, path: Path) -> dict[str, Any] | None:
        try:
            return read_historical_data_catalog(path)
        except Exception:
            return None

    def _read_operator_run_artifact_payload(self, path: Path) -> dict[str, Any]:
        payload = self._read_optional_json(path)
        if not isinstance(payload, dict):
            raise ValueError(f"{path.name} must be a JSON object")
        return normalize_operator_run_artifact_paths(payload, artifact_path=path)

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
        await self._assert_research_job_allowed()
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
        if job_type == "collect-durable-data":
            return await asyncio.to_thread(
                self._run_isolated_durable_data_collection,
                request,
                job_id,
            )
        if job_type == "refresh-historical-data-catalog":
            return await asyncio.to_thread(
                self._run_isolated_historical_data_catalog_refresh,
                request,
                job_id,
            )
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
                self._positive_int_or_none(request.get("stop_after_trials"), field_name="stop_after_trials"),
                bool(request.get("stable_run_id", False)),
            )
            return result
        if job_type == "analyze-research-results":
            return await asyncio.to_thread(
                self._run_isolated_research_analysis,
                request,
                job_id,
            )
        if job_type == "analyze-research-delta":
            return await asyncio.to_thread(
                self._run_isolated_research_analysis_delta,
                request,
                job_id,
            )
        if job_type == "run-frozen-entry-exit-lab":
            return await asyncio.to_thread(
                self._run_isolated_frozen_entry_exit_lab,
                request,
                job_id,
            )
        if job_type == "run-research-autopilot":
            return await self._run_research_autopilot(request, job_id)
        if job_type == "evaluate-discovery-candidate-pack-eligibility":
            return await asyncio.to_thread(
                self._run_isolated_discovery_candidate_pack_eligibility,
                request,
                job_id,
            )
        if job_type == "benchmark-hardware-utilization":
            return await asyncio.to_thread(
                self._run_isolated_hardware_utilization_benchmark,
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
        spec_payload = self._read_operator_run_artifact_payload(resolved_spec_path)
        spec = HistoricalResearchCycleSpec.from_payload(spec_payload, spec_path=resolved_spec_path)
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

    def _run_isolated_durable_data_collection(
        self,
        request: dict[str, Any],
        job_id: str,
    ) -> dict[str, Any]:
        research_root = self._research_root()
        safe_job_id = _safe_operator_path_part(job_id)
        output_dir = (research_root / "operator_runs" / "durable_data" / safe_job_id).resolve()
        if not _is_relative_to(output_dir, research_root):
            raise ValueError("durable data collection output_dir must stay inside the configured research output directory")
        if output_dir.exists() and any(output_dir.iterdir()):
            raise ValueError(f"durable data collection output_dir already contains files: {output_dir}")
        symbols = request.get("symbols")
        if not isinstance(symbols, list) or not symbols:
            symbols = list(DEFAULT_DURABLE_COLLECTION_SYMBOLS)
        result = collect_candidate_depth_public_archive_fixtures(
            output_dir=output_dir,
            symbols=[str(symbol) for symbol in symbols],
            start_month=str(request.get("start_month") or DEFAULT_DURABLE_COLLECTION_START_MONTH),
            end_month=str(request.get("end_month") or DEFAULT_DURABLE_COLLECTION_END_MONTH),
            repo_root=REPO_ROOT,
        )
        payload = result.to_payload()
        symbols_payload = payload.get("symbols") if isinstance(payload.get("symbols"), Mapping) else {}
        candidate_depth_ready = bool(symbols_payload) and all(
            isinstance(item, Mapping) and item.get("candidate_depth_thresholds_met") is True
            for item in symbols_payload.values()
        )
        return {
            **payload,
            "summary_path": str(result.summary_path),
            "candidate_depth_fixture_ready": candidate_depth_ready,
            "promotion_ready": False,
            "research_only": True,
            "observe_only": True,
        }

    def _run_isolated_historical_data_catalog_refresh(
        self,
        request: dict[str, Any],
        job_id: str,
    ) -> dict[str, Any]:
        research_root = self._research_root()
        safe_job_id = _safe_operator_path_part(job_id)
        output_dir = (research_root / "operator_runs" / "historical_data" / safe_job_id).resolve()
        if not _is_relative_to(output_dir, research_root):
            raise ValueError("historical data catalog output_dir must stay inside the configured research output directory")
        if output_dir.exists() and any(output_dir.iterdir()):
            raise ValueError(f"historical data catalog output_dir already contains files: {output_dir}")
        symbols = request.get("symbols")
        if not isinstance(symbols, list) or not symbols:
            symbols = list(DEFAULT_DURABLE_COLLECTION_SYMBOLS)
        download_cache_dir = (research_root / "historical_data_cache" / "binance_vision_public_archive" / "downloads").resolve()
        if not _is_relative_to(download_cache_dir, research_root):
            raise ValueError("historical data download cache must stay inside the configured research output directory")
        fallback_download_dirs = self._historical_data_download_fallback_dirs(research_root, download_cache_dir)
        fixture_fallback_dirs = self._historical_data_fixture_fallback_dirs(research_root, output_dir)
        result = refresh_historical_data_catalog(
            output_dir=output_dir,
            symbols=[str(symbol) for symbol in symbols],
            start_month=str(request.get("start_month") or DEFAULT_HISTORICAL_CATALOG_START_MONTH),
            end_month=str(request.get("end_month") or default_historical_catalog_end_month()),
            repo_root=REPO_ROOT,
            download_cache_dir=download_cache_dir,
            download_fallback_dirs=fallback_download_dirs,
            fixture_fallback_dirs=fixture_fallback_dirs,
        )
        payload = result.to_payload()
        symbols_payload = payload.get("symbols") if isinstance(payload.get("symbols"), Mapping) else {}
        candidate_depth_ready = bool(symbols_payload) and all(
            isinstance(item, Mapping) and item.get("candidate_depth_ready") is True
            for item in symbols_payload.values()
        )
        return {
            **payload,
            "historical_data_catalog_ready": candidate_depth_ready,
            "candidate_depth_fixture_ready": candidate_depth_ready,
            "download_cache_dir": str(download_cache_dir),
            "download_fallback_dir_count": len(fallback_download_dirs),
            "fixture_fallback_dir_count": len(fixture_fallback_dirs),
            "promotion_ready": False,
            "research_only": True,
            "observe_only": True,
        }

    def _historical_data_download_fallback_dirs(self, research_root: Path, download_cache_dir: Path) -> list[Path]:
        roots: list[Path] = []
        patterns = (
            "operator_runs/historical_data/*/sources/binance_vision_public_archive/downloads",
            "operator_runs/durable_data/*/downloads",
        )
        for pattern in patterns:
            for candidate in research_root.glob(pattern):
                resolved = candidate.resolve()
                if resolved == download_cache_dir or not resolved.is_dir():
                    continue
                if not _is_relative_to(resolved, research_root):
                    continue
                roots.append(resolved)
        return sorted(set(roots), key=lambda path: path.stat().st_mtime if path.exists() else 0, reverse=True)

    def _historical_data_fixture_fallback_dirs(self, research_root: Path, output_dir: Path) -> list[Path]:
        roots: list[Path] = []
        patterns = (
            "operator_runs/historical_data/*/sources/binance_vision_public_archive",
            "operator_runs/durable_data/*",
        )
        for pattern in patterns:
            for candidate in research_root.glob(pattern):
                resolved = candidate.resolve()
                if resolved == output_dir.resolve() or not resolved.is_dir():
                    continue
                if not _is_relative_to(resolved, research_root):
                    continue
                if not (resolved / "fixture_packs").is_dir():
                    continue
                roots.append(resolved)
        return sorted(set(roots), key=lambda path: path.stat().st_mtime if path.exists() else 0, reverse=True)

    def _run_isolated_discovery(
        self,
        spec_path: Path,
        job_id: str,
        resume: bool,
        stop_after_trials: int | None,
        stable_run_id: bool = False,
    ) -> dict[str, Any]:
        resolved_spec_path = Path(spec_path).expanduser().resolve()
        spec_payload = self._read_operator_run_artifact_payload(resolved_spec_path)
        spec = DiscoveryRunSpec.from_payload(spec_payload, spec_path=resolved_spec_path)
        research_root = self._research_root()
        safe_job_id = _safe_operator_path_part(job_id)
        safe_run_id = _safe_operator_path_part(spec.run_id)
        if resume or stop_after_trials is not None or stable_run_id:
            output_dir = (research_root / "operator_runs" / "discovery_runs" / safe_run_id).resolve()
            if resume:
                overwrite_protection = "resume_stable_run_id_output_dir"
            elif stop_after_trials is not None:
                overwrite_protection = "pauseable_stable_run_id_output_dir"
            else:
                overwrite_protection = "stable_run_id_output_dir"
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
        isolated_payload["operator_stable_run_id"] = stable_run_id
        isolated_payload["operator_requested_resume"] = resume
        effective_resume = bool(resume or (stable_run_id and (output_dir / "run_state.json").exists()))
        isolated_payload["operator_effective_resume"] = effective_resume
        isolated_spec_path.write_text(json.dumps(isolated_payload, indent=2, sort_keys=True), encoding="utf-8")

        result = run_discovery(
            spec_path=isolated_spec_path,
            app_config=self.config,
            resume=effective_resume,
            stop_after_trials=stop_after_trials,
        )
        return {
            "output_dir": str(result.output_dir),
            "isolated_spec_path": str(isolated_spec_path),
            "source_spec_path": str(resolved_spec_path),
            "overwrite_protection": overwrite_protection,
            "resume": effective_resume,
            "requested_resume": resume,
            "stable_run_id": stable_run_id,
            "stop_after_trials": stop_after_trials,
            "discovery_run_manifest_path": str(result.manifest_path),
            "run_state_path": str(result.run_state_path),
            "interesting_candidates_path": str(result.interesting_candidates_path),
            "blocked_candidates_path": str(result.blocked_candidates_path),
            "filter_blockers_path": str(result.filter_blockers_path),
            "snapshot_count": len(result.snapshot_paths),
        }

    def _run_isolated_research_analysis(
        self,
        request: dict[str, Any],
        job_id: str,
    ) -> dict[str, Any]:
        research_root = self._research_root()
        safe_job_id = _safe_operator_path_part(job_id)
        output_dir = (research_root / "operator_runs" / "analysis" / safe_job_id).resolve()
        if not _is_relative_to(output_dir, research_root):
            raise ValueError("research analysis output_dir must stay inside the configured research output directory")
        if output_dir.exists() and any(output_dir.iterdir()):
            raise ValueError(f"research analysis output_dir already contains files: {output_dir}")

        def optional_manifest_dir(field: str, expected_name: str) -> Path | None:
            raw = request.get(field)
            if raw is None or str(raw).strip() == "":
                return None
            path = Path(str(raw)).expanduser().resolve()
            if not path.is_file():
                raise ValueError(f"{field} does not exist")
            if path.name != expected_name:
                raise ValueError(f"{field} must reference {expected_name}")
            if not _is_relative_to(path, research_root):
                raise ValueError(f"{field} must stay inside the configured research output directory")
            return path.parent

        cycle_dir = optional_manifest_dir("cycle_manifest_path", "research_cycle_manifest.json")
        discovery_dir = optional_manifest_dir("discovery_manifest_path", "discovery_run_manifest.json")
        if cycle_dir is None and discovery_dir is None:
            raise ValueError("cycle_manifest_path or discovery_manifest_path is required")

        result = write_research_analysis_artifacts(
            cycle_dir=cycle_dir,
            discovery_dir=discovery_dir,
            output_dir=output_dir,
            include_trade_sortino=bool(request.get("include_trade_sortino", True)),
            max_sortino_trade_files=int(request.get("max_sortino_trade_files") or 1000),
        )
        summary = self._research_analysis_summary(result.analysis)
        return {
            "output_dir": str(output_dir),
            "research_analysis_path": str(result.analysis_json_path),
            "research_analysis_markdown_path": str(result.markdown_path),
            "cycle_manifest_path": str(cycle_dir / "research_cycle_manifest.json") if cycle_dir is not None else None,
            "discovery_manifest_path": str(discovery_dir / "discovery_run_manifest.json") if discovery_dir is not None else None,
            "cycle_available": summary.get("cycle_available"),
            "discovery_available": summary.get("discovery_available"),
            "symbol": summary.get("symbol"),
            "candidate_pack_written": False,
            "promotion_ready": False,
            "research_only": True,
            "observe_only": True,
        }

    def _run_isolated_research_analysis_delta(
        self,
        request: dict[str, Any],
        job_id: str,
    ) -> dict[str, Any]:
        research_root = self._research_root()
        safe_job_id = _safe_operator_path_part(job_id)
        output_dir = (research_root / "operator_runs" / "analysis_deltas" / safe_job_id).resolve()
        if not _is_relative_to(output_dir, research_root):
            raise ValueError("research analysis delta output_dir must stay inside the configured research output directory")
        if output_dir.exists() and any(output_dir.iterdir()):
            raise ValueError(f"research analysis delta output_dir already contains files: {output_dir}")

        symbol = str(request.get("symbol") or "").strip().upper() or None
        current_analysis_path = self._operator_research_artifact_path(
            request.get("current_analysis_path"),
            expected_name="research_analysis.json",
            research_root=research_root,
            required=False,
        )
        if current_analysis_path is None:
            current_analysis_path = self._latest_analysis_artifact_path(symbol=symbol)
        if current_analysis_path is None:
            raise ValueError("current_analysis_path is required when no research analysis artifact is indexed")
        previous_analysis_path = self._operator_research_artifact_path(
            request.get("previous_analysis_path"),
            expected_name="research_analysis.json",
            research_root=research_root,
            required=False,
        )
        if previous_analysis_path is None:
            previous_analysis_path = self._previous_analysis_artifact_path(current_analysis_path, symbol=symbol)

        result = write_research_analysis_delta_artifacts(
            current_analysis_path=current_analysis_path,
            previous_analysis_path=previous_analysis_path,
            output_dir=output_dir,
        )
        summary = self._research_analysis_delta_summary(result.delta)
        return {
            "output_dir": str(output_dir),
            "research_analysis_delta_path": str(result.delta_json_path),
            "research_analysis_delta_markdown_path": str(result.markdown_path),
            "current_analysis_path": str(current_analysis_path),
            "previous_analysis_path": str(previous_analysis_path) if previous_analysis_path is not None else None,
            "compatible": summary.get("compatible"),
            "blocked_reasons": summary.get("blocked_reasons"),
            "symbol": summary.get("symbol"),
            "candidate_pack_written": False,
            "promotion_ready": False,
            "research_only": True,
            "observe_only": True,
        }

    def _run_isolated_frozen_entry_exit_lab(
        self,
        request: dict[str, Any],
        job_id: str,
    ) -> dict[str, Any]:
        research_root = self._research_root()
        safe_job_id = _safe_operator_path_part(job_id)
        output_dir = (research_root / "operator_runs" / "frozen_entry_exit_lab" / safe_job_id).resolve()
        if not _is_relative_to(output_dir, research_root):
            raise ValueError("frozen-entry exit lab output_dir must stay inside the configured research output directory")
        if output_dir.exists() and any(output_dir.iterdir()):
            raise ValueError(f"frozen-entry exit lab output_dir already contains files: {output_dir}")

        discovery_manifest_path = self._operator_research_artifact_path(
            request.get("discovery_manifest_path"),
            expected_name="discovery_run_manifest.json",
            research_root=research_root,
            required=True,
        )
        assert discovery_manifest_path is not None
        entry_signals_path = self._operator_research_artifact_path(
            request.get("entry_signals_path"),
            research_root=research_root,
            required=False,
        )
        market_data_path = self._operator_research_artifact_path(
            request.get("market_data_path"),
            research_root=research_root,
            required=False,
        )
        max_candidates = int(request.get("max_candidates") or 12)
        if max_candidates <= 0 or max_candidates > 100:
            raise ValueError("max_candidates must be between 1 and 100")
        result = write_frozen_entry_exit_lab_artifacts(
            discovery_manifest_path=discovery_manifest_path,
            output_dir=output_dir,
            entry_signals_path=entry_signals_path,
            market_data_path=market_data_path,
            max_candidates=max_candidates,
        )
        summary = self._discovery_exit_lab_summary(result.manifest)
        return {
            "output_dir": str(result.output_dir),
            "exit_lab_manifest_path": str(result.manifest_path),
            "exit_lab_matrix_path": str(result.matrix_path),
            "exit_lab_candidate_gates_path": str(result.candidate_gates_path),
            "exit_lab_trades_path": str(result.trades_path),
            "discovery_manifest_path": str(discovery_manifest_path),
            "entry_signals_path": str(entry_signals_path) if entry_signals_path is not None else None,
            "market_data_path": str(market_data_path) if market_data_path is not None else None,
            "blocked_reason": summary.get("blocked_reason"),
            "comparison_count": summary.get("comparison_count"),
            "candidate_gate_row_count": summary.get("candidate_gate_row_count"),
            "symbol": summary.get("symbol"),
            "candidate_pack_written": False,
            "promotion_ready": False,
            "research_only": True,
            "observe_only": True,
        }

    def _operator_research_artifact_path(
        self,
        raw_path: object,
        *,
        research_root: Path,
        expected_name: str | None = None,
        required: bool,
    ) -> Path | None:
        if raw_path is None or str(raw_path).strip() == "":
            if required:
                raise ValueError("required research artifact path missing")
            return None
        path = Path(str(raw_path)).expanduser()
        path = path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()
        if not path.is_file():
            raise ValueError(f"research artifact path does not exist: {path}")
        if expected_name is not None and path.name != expected_name:
            raise ValueError(f"research artifact path must reference {expected_name}")
        if not _is_relative_to(path, research_root):
            raise ValueError("research artifact path must stay inside the configured research output directory")
        return path

    def _assert_research_manifest_outputs_stay_inside_root(self, manifest_path: Path, research_root: Path) -> None:
        manifest = self._read_optional_json(manifest_path)
        if not isinstance(manifest, Mapping):
            return
        manifest = normalize_operator_run_artifact_paths(
            manifest,
            artifact_path=manifest_path,
            anchor_root=manifest_path.parent,
        )
        required_outputs = manifest.get("required_outputs") if isinstance(manifest.get("required_outputs"), Mapping) else {}
        for output_key, raw_path in required_outputs.items():
            if raw_path is None or str(raw_path).strip() == "":
                continue
            output_path = Path(str(raw_path)).expanduser()
            output_path = output_path.resolve() if output_path.is_absolute() else (manifest_path.parent / output_path).resolve()
            if not _is_relative_to(output_path, research_root):
                raise ValueError(f"research manifest required output must stay inside the configured research output directory: {output_key}")

    def _research_symbol_from_manifest_path(self, manifest_path: Path) -> str | None:
        payload = self._read_optional_json(manifest_path) or {}
        return self._research_symbol_from_payload({"path": str(manifest_path), "manifest": payload})

    def _assert_same_research_symbol(self, expected_symbol: str | None, manifest_path: Path | None, *, field_name: str) -> None:
        if manifest_path is None or expected_symbol is None:
            return
        symbol = self._research_symbol_from_manifest_path(manifest_path)
        if symbol is not None and symbol != expected_symbol:
            raise ValueError(f"{field_name} must reference the same symbol as discovery_manifest_path")

    def _latest_analysis_artifact_path(self, *, symbol: str | None) -> Path | None:
        artifacts = self._research_progress_known_artifacts()
        artifact = self._latest_research_artifact(artifacts, "research_analysis", symbol)
        return Path(str(artifact.get("path"))).resolve() if artifact and artifact.get("path") else None

    def _previous_analysis_artifact_path(self, current_analysis_path: Path, *, symbol: str | None) -> Path | None:
        current = current_analysis_path.resolve()
        candidates = [
            artifact
            for artifact in self._research_progress_known_artifacts()
            if artifact.get("type") == "research_analysis"
            and artifact.get("path")
            and Path(str(artifact.get("path"))).resolve() != current
            and (symbol is None or self._research_symbol_from_payload(artifact) == symbol)
        ]
        candidates.sort(key=lambda item: float(item.get("sort_time") or 0.0), reverse=True)
        for artifact in candidates:
            path = Path(str(artifact.get("path"))).resolve()
            if path.is_file():
                return path
        return None

    async def _run_research_autopilot(
        self,
        request: dict[str, Any],
        job_id: str,
    ) -> dict[str, Any]:
        research_root = self._research_root()
        safe_job_id = _safe_operator_path_part(job_id)
        output_dir = (research_root / "operator_runs" / "research_autopilot" / safe_job_id).resolve()
        if not _is_relative_to(output_dir, research_root):
            raise ValueError("research autopilot output_dir must stay inside the configured research output directory")
        if output_dir.exists() and any(output_dir.iterdir()):
            raise ValueError(f"research autopilot output_dir already contains files: {output_dir}")
        output_dir.mkdir(parents=True, exist_ok=False)
        manifest_path = output_dir / "research_autopilot_manifest.json"

        raw_symbols = request.get("symbols")
        if isinstance(raw_symbols, list) and raw_symbols:
            symbols = [str(symbol).strip().upper() for symbol in raw_symbols if str(symbol).strip()]
        else:
            symbols = ["BTCUSDT", "ETHUSDT"]
        unsupported = sorted(set(symbols) - {"BTCUSDT", "ETHUSDT"})
        if unsupported:
            raise ValueError(f"unsupported autopilot symbols: {', '.join(unsupported)}")
        symbols = list(dict.fromkeys(symbols))
        max_steps = int(request.get("max_steps") or 100)
        if max_steps <= 0:
            raise ValueError("max_steps must be positive")
        max_step_attempts = int(request.get("max_step_attempts") or RESEARCH_AUTOPILOT_DEFAULT_STEP_ATTEMPTS)
        if max_step_attempts < 1 or max_step_attempts > RESEARCH_AUTOPILOT_MAX_STEP_ATTEMPTS:
            raise ValueError(f"max_step_attempts must be between 1 and {RESEARCH_AUTOPILOT_MAX_STEP_ATTEMPTS}")
        include_catalog_refresh = bool(request.get("include_catalog_refresh", True))
        include_eligibility = bool(request.get("include_eligibility", True))

        manifest: dict[str, Any] = {
            "autopilot_version": RESEARCH_AUTOPILOT_VERSION,
            "autopilot_status": "running",
            "job_id": job_id,
            "requested_symbols": symbols,
            "max_steps": max_steps,
            "max_step_attempts": max_step_attempts,
            "include_catalog_refresh": include_catalog_refresh,
            "include_eligibility": include_eligibility,
            "stale_recovery_attempt": self._nonnegative_int(request.get("_stale_recovery_attempt")),
            "recovered_from_job_id": request.get("recovered_from_job_id"),
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            "steps": [],
            "executed_step_count": 0,
            "blocked_reason": None,
            "active_step": None,
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "candidate_pack_written": False,
        }

        def write_manifest(status: str | None = None, blocked_reason: str | None = None) -> None:
            if status is not None:
                manifest["autopilot_status"] = status
            if blocked_reason is not None:
                manifest["blocked_reason"] = blocked_reason
            manifest["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, default=str), encoding="utf-8")

        async def add_step(
            key: str,
            status: str,
            *,
            symbol: str | None = None,
            detail: str = "",
            result: Mapping[str, Any] | None = None,
            blocker: str | None = None,
            attempt: int | None = None,
            max_attempts: int | None = None,
            attempt_job_id: str | None = None,
        ) -> None:
            step = {
                "key": key,
                "status": status,
                "symbol": symbol,
                "detail": detail,
                "blocker": blocker,
                "result": dict(result or {}),
                "attempt": attempt,
                "max_attempts": max_attempts,
                "attempt_job_id": attempt_job_id,
                "time_utc": datetime.now(timezone.utc).isoformat(),
            }
            manifest["steps"].append(step)
            write_manifest()
            await self.store.append_operator_job_log(
                job_id=job_id,
                time_ms=self.engine.clock(),
                level="error" if status in {"blocked", "failed"} else "info",
                message=f"autopilot {status}: {key}",
                payload={key: step},
            )

        async def context() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
            jobs = await self.list_jobs()
            artifacts = self._dedupe_research_progress_artifacts(
                [
                    *self._research_progress_artifacts_from_jobs(jobs),
                    *self._research_progress_known_artifacts(),
                ]
            )
            readiness = self.r104_readiness_diagnostics()
            return jobs, artifacts, readiness

        def can_execute() -> bool:
            return int(manifest["executed_step_count"]) < max_steps

        async def blocked(key: str, reason: str, *, symbol: str | None = None) -> dict[str, Any]:
            manifest["active_step"] = None
            await add_step(key, "blocked", symbol=symbol, detail=reason, blocker=reason)
            write_manifest("blocked", reason)
            return {
                "output_dir": str(output_dir),
                "research_autopilot_manifest_path": str(manifest_path),
                "autopilot_status": "blocked",
                "blocked_reason": reason,
                "executed_step_count": int(manifest["executed_step_count"]),
                "step_count": len(manifest["steps"]),
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "candidate_pack_written": False,
            }

        def readiness_spec_path(readiness: Mapping[str, Any], symbol: str, key: str) -> Path | None:
            item = self._readiness_item(readiness, symbol)
            raw = (item or {}).get(key)
            return Path(str(raw)).expanduser().resolve() if raw else None

        def complete_artifact(
            artifacts: list[dict[str, Any]],
            artifact_type: str,
            symbol: str | None,
            key: str,
            expected_ids: set[str] | None = None,
        ) -> dict[str, Any] | None:
            artifact = self._latest_research_artifact(artifacts, artifact_type, symbol, expected_ids=expected_ids)
            if self._required_artifact_status(artifact, key, expected_ids)["complete"]:
                return artifact
            return None

        async def execute_step(
            key: str,
            symbol: str | None,
            func,
            *args,
            job_id_arg_index: int = -1,
        ) -> Mapping[str, Any]:
            base_args = list(args)
            if not base_args:
                raise ValueError("autopilot direct step requires a helper job id argument")
            base_attempt_job_id = str(base_args[job_id_arg_index])
            for attempt in range(1, max_step_attempts + 1):
                if not can_execute():
                    raise RuntimeError("autopilot_step_limit_reached")
                attempt_args = list(base_args)
                attempt_job_id = base_attempt_job_id if attempt == 1 else f"{base_attempt_job_id}-retry-{attempt}"
                attempt_args[job_id_arg_index] = attempt_job_id
                manifest["executed_step_count"] = int(manifest["executed_step_count"]) + 1
                active_step = self._research_autopilot_active_step_payload(
                    key=key,
                    symbol=symbol,
                    attempt=attempt,
                    max_attempts=max_step_attempts,
                    attempt_job_id=attempt_job_id,
                    helper_args=attempt_args,
                )
                manifest["active_step"] = active_step
                write_manifest()
                await self.store.append_operator_job_log(
                    job_id=job_id,
                    time_ms=self.engine.clock(),
                    level="info",
                    message=f"autopilot running: {key}",
                    payload={key: active_step},
                )
                try:
                    result = await asyncio.to_thread(func, *attempt_args)
                except Exception as exc:
                    detail = str(exc)
                    manifest["active_step"] = None
                    if attempt < max_step_attempts:
                        await add_step(
                            key,
                            "retrying",
                            symbol=symbol,
                            detail=detail,
                            blocker=detail,
                            result={"error": detail},
                            attempt=attempt,
                            max_attempts=max_step_attempts,
                            attempt_job_id=attempt_job_id,
                        )
                        continue
                    await add_step(
                        key,
                        "failed",
                        symbol=symbol,
                        detail=detail,
                        blocker=detail,
                        result={"error": detail},
                        attempt=attempt,
                        max_attempts=max_step_attempts,
                        attempt_job_id=attempt_job_id,
                    )
                    write_manifest("failed", detail)
                    raise
                manifest["active_step"] = None
                result_payload = dict(result) if isinstance(result, Mapping) else {}
                result_payload.update(
                    {
                        "attempt": attempt,
                        "max_attempts": max_step_attempts,
                        "attempt_job_id": attempt_job_id,
                    }
                )
                await add_step(
                    key,
                    "executed",
                    symbol=symbol,
                    result=result_payload,
                    attempt=attempt,
                    max_attempts=max_step_attempts,
                    attempt_job_id=attempt_job_id,
                )
                return result_payload
            raise RuntimeError("autopilot_step_attempts_exhausted")

        write_manifest()
        _, artifacts, readiness = await context()

        if bool(readiness.get("candidate_evidence_ready")):
            await add_step("historical_data_catalog", "skipped", detail="candidate-depth catalog already ready")
        elif not include_catalog_refresh:
            return await blocked("historical_data_catalog", "historical_data_catalog_not_ready")
        else:
            if not can_execute():
                return await blocked("historical_data_catalog", "autopilot_step_limit_reached")
            await execute_step(
                "historical_data_catalog",
                None,
                self._run_isolated_historical_data_catalog_refresh,
                {
                    "symbols": symbols,
                    "start_month": str(request.get("start_month") or DEFAULT_HISTORICAL_CATALOG_START_MONTH),
                    "end_month": str(request.get("end_month") or default_historical_catalog_end_month()),
                    "source_name": "historical_data_catalog",
                    "market": "futures/um",
                },
                f"{job_id}-historical-data-catalog",
            )
            _, artifacts, readiness = await context()
            if not bool(readiness.get("candidate_evidence_ready")):
                return await blocked("historical_data_catalog", "historical_data_catalog_refresh_did_not_produce_candidate_ready_evidence")

        cycle_artifacts: dict[str, dict[str, Any]] = {}
        discovery_artifacts: dict[str, dict[str, Any]] = {}

        for symbol in symbols:
            cycle_key = "btc_cycle" if symbol == "BTCUSDT" else "eth_cycle"
            discovery_key = "btc_discovery" if symbol == "BTCUSDT" else "eth_discovery"
            expected_cycle_id = self._expected_cycle_id(readiness, symbol)
            expected_discovery_id = self._expected_discovery_run_id(readiness, symbol)

            cycle_artifact = complete_artifact(
                artifacts,
                "historical_research_cycle",
                symbol,
                cycle_key,
                {expected_cycle_id},
            )
            if cycle_artifact is not None:
                await add_step("historical_cycle", "skipped", symbol=symbol, detail="current cycle artifact already complete")
            else:
                cycle_spec_path = readiness_spec_path(readiness, symbol, "cycle_spec_path")
                if cycle_spec_path is None:
                    return await blocked("historical_cycle", "cycle_spec_path_missing", symbol=symbol)
                if not can_execute():
                    return await blocked("historical_cycle", "autopilot_step_limit_reached", symbol=symbol)
                await execute_step(
                    "historical_cycle",
                    symbol,
                    self._run_isolated_historical_research_cycle,
                    cycle_spec_path,
                    f"{job_id}-{symbol.lower()}-cycle",
                )
                _, artifacts, readiness = await context()
                cycle_artifact = complete_artifact(
                    artifacts,
                    "historical_research_cycle",
                    symbol,
                    cycle_key,
                    {expected_cycle_id},
                )
                if cycle_artifact is None:
                    return await blocked("historical_cycle", "historical_cycle_output_not_complete_after_run", symbol=symbol)

            discovery_artifact = complete_artifact(
                artifacts,
                "discovery_run",
                symbol,
                discovery_key,
                {expected_discovery_id},
            )
            if discovery_artifact is not None:
                await add_step("exact_discovery", "skipped", symbol=symbol, detail="current discovery artifact already complete")
            else:
                discovery_spec_path = readiness_spec_path(readiness, symbol, "discovery_spec_path")
                if discovery_spec_path is None:
                    return await blocked("exact_discovery", "discovery_spec_path_missing", symbol=symbol)
                if not can_execute():
                    return await blocked("exact_discovery", "autopilot_step_limit_reached", symbol=symbol)
                await execute_step(
                    "exact_discovery",
                    symbol,
                    self._run_isolated_discovery,
                    discovery_spec_path,
                    f"{job_id}-{symbol.lower()}-discovery",
                    True,
                    self._positive_int_or_none(request.get("discovery_stop_after_trials"), field_name="discovery_stop_after_trials"),
                    True,
                    job_id_arg_index=1,
                )
                _, artifacts, readiness = await context()
                discovery_artifact = complete_artifact(
                    artifacts,
                    "discovery_run",
                    symbol,
                    discovery_key,
                    {expected_discovery_id},
                )
                if discovery_artifact is None:
                    return await blocked("exact_discovery", "exact_discovery_output_not_complete_after_run", symbol=symbol)

            cycle_artifacts[symbol] = cycle_artifact
            discovery_artifacts[symbol] = discovery_artifact

        for symbol in symbols:
            cycle_artifact = cycle_artifacts.get(symbol)
            discovery_artifact = discovery_artifacts.get(symbol)
            if cycle_artifact is None or discovery_artifact is None:
                return await blocked("research_analysis", "autopilot_prerequisite_artifacts_missing", symbol=symbol)

            analysis_artifact = complete_artifact(artifacts, "research_analysis", symbol, "research_analysis")
            if analysis_artifact is not None:
                await add_step("research_analysis", "skipped", symbol=symbol, detail="analysis artifact already complete")
            else:
                if not can_execute():
                    return await blocked("research_analysis", "autopilot_step_limit_reached", symbol=symbol)
                await execute_step(
                    "research_analysis",
                    symbol,
                    self._run_isolated_research_analysis,
                    {
                        "cycle_manifest_path": cycle_artifact.get("path") if cycle_artifact else None,
                        "discovery_manifest_path": discovery_artifact.get("path") if discovery_artifact else None,
                        "include_trade_sortino": bool(request.get("include_trade_sortino", True)),
                        "max_sortino_trade_files": int(request.get("max_sortino_trade_files") or 1000),
                    },
                    f"{job_id}-{symbol.lower()}-analysis",
                )
                _, artifacts, readiness = await context()
                analysis_artifact = complete_artifact(artifacts, "research_analysis", symbol, "research_analysis")
                if analysis_artifact is None:
                    return await blocked("research_analysis", "research_analysis_output_not_complete_after_run", symbol=symbol)

            analysis_delta_artifact = complete_artifact(artifacts, "research_analysis_delta", symbol, "research_analysis_delta")
            if analysis_delta_artifact is not None:
                await add_step("research_analysis_delta", "skipped", symbol=symbol, detail="analysis delta artifact already complete")
            else:
                if not can_execute():
                    return await blocked("research_analysis_delta", "autopilot_step_limit_reached", symbol=symbol)
                await execute_step(
                    "research_analysis_delta",
                    symbol,
                    self._run_isolated_research_analysis_delta,
                    {
                        "current_analysis_path": analysis_artifact.get("path") if analysis_artifact else None,
                        "previous_analysis_path": None,
                        "symbol": symbol,
                    },
                    f"{job_id}-{symbol.lower()}-analysis-delta",
                )
                _, artifacts, readiness = await context()
                analysis_delta_artifact = complete_artifact(artifacts, "research_analysis_delta", symbol, "research_analysis_delta")
                if analysis_delta_artifact is None:
                    return await blocked("research_analysis_delta", "research_analysis_delta_output_not_complete_after_run", symbol=symbol)

            exit_lab_artifact = complete_artifact(artifacts, "discovery_exit_lab", symbol, "frozen_entry_exit_lab")
            if exit_lab_artifact is not None:
                await add_step("frozen_entry_exit_lab", "skipped", symbol=symbol, detail="frozen-entry exit lab artifact already complete")
            else:
                if not can_execute():
                    return await blocked("frozen_entry_exit_lab", "autopilot_step_limit_reached", symbol=symbol)
                await execute_step(
                    "frozen_entry_exit_lab",
                    symbol,
                    self._run_isolated_frozen_entry_exit_lab,
                    {
                        "discovery_manifest_path": discovery_artifact.get("path") if discovery_artifact else None,
                        "entry_signals_path": None,
                        "market_data_path": None,
                        "max_candidates": int(request.get("exit_lab_max_candidates") or 12),
                    },
                    f"{job_id}-{symbol.lower()}-frozen-entry-exit-lab",
                )
                _, artifacts, readiness = await context()
                exit_lab_artifact = complete_artifact(artifacts, "discovery_exit_lab", symbol, "frozen_entry_exit_lab")
                if exit_lab_artifact is None:
                    return await blocked("frozen_entry_exit_lab", "frozen_entry_exit_lab_output_not_complete_after_run", symbol=symbol)

            if not include_eligibility:
                await add_step("candidate_eligibility", "skipped", symbol=symbol, detail="eligibility disabled by request")
                continue
            eligibility_artifact = complete_artifact(artifacts, "candidate_pack_eligibility", symbol, "candidate_eligibility")
            if eligibility_artifact is not None:
                await add_step("candidate_eligibility", "skipped", symbol=symbol, detail="candidate eligibility artifact already complete")
                continue
            if not can_execute():
                return await blocked("candidate_eligibility", "autopilot_step_limit_reached", symbol=symbol)
            await execute_step(
                "candidate_eligibility",
                symbol,
                self._run_isolated_discovery_candidate_pack_eligibility,
                {
                    "discovery_manifest_path": discovery_artifact.get("path") if discovery_artifact else None,
                    "cycle_manifest_path": cycle_artifact.get("path") if cycle_artifact else None,
                    "exit_lab_manifest_path": exit_lab_artifact.get("path") if exit_lab_artifact else None,
                    "multiple_testing_manifest_path": None,
                    "validation_floors_manifest_path": None,
                },
                f"{job_id}-{symbol.lower()}-eligibility",
            )
            _, artifacts, readiness = await context()

        manifest["active_step"] = None
        write_manifest("completed")
        return {
            "output_dir": str(output_dir),
            "research_autopilot_manifest_path": str(manifest_path),
            "autopilot_status": "completed",
            "blocked_reason": None,
            "executed_step_count": int(manifest["executed_step_count"]),
            "step_count": len(manifest["steps"]),
            "requested_symbols": symbols,
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "candidate_pack_written": False,
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

        discovery_manifest_path = self._operator_research_artifact_path(
            request.get("discovery_manifest_path"),
            research_root=research_root,
            expected_name="discovery_run_manifest.json",
            required=True,
        )
        cycle_manifest_path = self._operator_research_artifact_path(
            request.get("cycle_manifest_path"),
            research_root=research_root,
            expected_name="research_cycle_manifest.json",
            required=False,
        )
        exit_lab_manifest_path = self._operator_research_artifact_path(
            request.get("exit_lab_manifest_path"),
            research_root=research_root,
            expected_name="discovery_exit_lab_manifest.json",
            required=False,
        )
        multiple_testing_manifest_path = self._operator_research_artifact_path(
            request.get("multiple_testing_manifest_path"),
            research_root=research_root,
            expected_name="discovery_multiple_testing_manifest.json",
            required=False,
        )
        validation_floors_manifest_path = self._operator_research_artifact_path(
            request.get("validation_floors_manifest_path"),
            research_root=research_root,
            expected_name="discovery_validation_floors_manifest.json",
            required=False,
        )
        assert discovery_manifest_path is not None
        for manifest_path in (
            discovery_manifest_path,
            cycle_manifest_path,
            exit_lab_manifest_path,
            multiple_testing_manifest_path,
            validation_floors_manifest_path,
        ):
            if manifest_path is not None:
                self._assert_research_manifest_outputs_stay_inside_root(manifest_path, research_root)
        discovery_symbol = self._research_symbol_from_manifest_path(discovery_manifest_path)
        self._assert_same_research_symbol(discovery_symbol, cycle_manifest_path, field_name="cycle_manifest_path")
        self._assert_same_research_symbol(discovery_symbol, exit_lab_manifest_path, field_name="exit_lab_manifest_path")
        self._assert_same_research_symbol(discovery_symbol, multiple_testing_manifest_path, field_name="multiple_testing_manifest_path")
        self._assert_same_research_symbol(discovery_symbol, validation_floors_manifest_path, field_name="validation_floors_manifest_path")

        result = evaluate_discovery_candidate_pack_eligibility(
            discovery_manifest_path=discovery_manifest_path,
            cycle_manifest_path=cycle_manifest_path,
            exit_lab_manifest_path=exit_lab_manifest_path,
            multiple_testing_manifest_path=multiple_testing_manifest_path,
            validation_floors_manifest_path=validation_floors_manifest_path,
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

    def _run_isolated_hardware_utilization_benchmark(
        self,
        request: dict[str, Any],
        job_id: str,
    ) -> dict[str, Any]:
        research_root = self._research_root()
        safe_job_id = _safe_operator_path_part(job_id)
        output_dir = (research_root / "operator_runs" / "hardware_utilization" / safe_job_id).resolve()
        if not _is_relative_to(output_dir, research_root):
            raise ValueError("hardware utilization output_dir must stay inside the configured research output directory")
        if output_dir.exists() and any(output_dir.iterdir()):
            raise ValueError(f"hardware utilization output_dir already contains files: {output_dir}")
        result = write_hardware_utilization_report(
            output_dir=output_dir,
            cpu_workers=self._positive_int_or_none(request.get("cpu_workers"), field_name="cpu_workers"),
            cpu_seconds=float(request.get("cpu_seconds") or 3.0),
            gpu_seconds=float(request.get("gpu_seconds") or 3.0),
            matrix_size=int(request.get("matrix_size") or 1024),
            app_config=self.config,
        )
        payload = self._read_optional_json(result.report_path) or {}
        cpu_probe = payload.get("cpu_probe") if isinstance(payload.get("cpu_probe"), dict) else {}
        gpu_probe = payload.get("gpu_probe") if isinstance(payload.get("gpu_probe"), dict) else {}
        readiness = (
            payload.get("prolonged_study_readiness")
            if isinstance(payload.get("prolonged_study_readiness"), dict)
            else {}
        )
        cpu_saturation_target_met = (
            cpu_probe.get("worker_capacity_saturation_status") == "saturated"
            if "worker_capacity_saturation_status" in cpu_probe
            else bool(readiness.get("cpu_worker_saturation_target_met", False))
        )
        return {
            "output_dir": str(result.output_dir),
            "hardware_utilization_report_path": str(result.report_path),
            "cpu_probe_succeeded": bool(cpu_probe.get("probe_succeeded", False)),
            "gpu_probe_succeeded": bool(gpu_probe.get("probe_succeeded", False)),
            "cpu_worker_capacity_percent": cpu_probe.get("process_cpu_percent_of_worker_capacity"),
            "cpu_logical_capacity_percent": cpu_probe.get("process_cpu_percent_of_logical_capacity"),
            "cpu_worker_saturation_status": cpu_probe.get("worker_capacity_saturation_status"),
            "cpu_logical_saturation_status": cpu_probe.get("logical_capacity_saturation_status"),
            "ready_for_long_cpu_bound_research": cpu_saturation_target_met,
            "gpu_execution_status": gpu_probe.get("gpu_execution_status"),
            "promotion_ready": False,
            "research_only": True,
            "observe_only": True,
        }

    def _positive_int_or_none(self, value: object, *, field_name: str) -> int | None:
        if value is None or str(value).strip() == "":
            return None
        parsed = int(value)  # type: ignore[arg-type]
        if parsed <= 0:
            raise ValueError(f"{field_name} must be positive when supplied")
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
