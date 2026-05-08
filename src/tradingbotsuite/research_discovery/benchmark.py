from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from tradingbotsuite.config import AppConfig
from tradingbotsuite.research.live_readiness import research_boundary_metadata
from tradingbotsuite.research_discovery.runner import DiscoveryRunResult, run_discovery
from tradingbotsuite.research_discovery.state import read_trial_record


DISCOVERY_BENCHMARK_REPORT_VERSION = "discovery-benchmark-report-v1"
DISCOVERY_BENCHMARK_GATE_VERSION = "discovery-benchmark-gate-v1"

DISCOVERY_BENCHMARK_TIERS: dict[str, dict[str, Any]] = {
    "quick": {
        "discovery_mode": "quick_smoke",
        "symbol": "BTCUSDT",
        "timeframe": "15m",
        "max_trials": 3,
        "trial_batch_size": 1,
        "snapshot_interval_minutes": 30,
        "feature_column_set_ids": ["price_trend_vol"],
    },
    "standard": {
        "discovery_mode": "entry_discovery_standard",
        "symbol": "BTCUSDT",
        "timeframe": "15m",
        "max_trials": 5,
        "trial_batch_size": 2,
        "snapshot_interval_minutes": 30,
        "feature_column_set_ids": ["price_trend_vol", "alternative_non_wt_price_state"],
    },
    "deep": {
        "discovery_mode": "deep_candidate_harvest",
        "symbol": "BTCUSDT",
        "timeframe": "15m",
        "max_trials": 8,
        "trial_batch_size": 2,
        "snapshot_interval_minutes": 30,
        "feature_column_set_ids": ["price_trend_vol", "compact_wt3d_base", "alternative_non_wt_price_state"],
    },
}

DISCOVERY_BENCHMARK_THRESHOLDS: dict[str, dict[str, Any]] = {
    "quick": {
        "max_elapsed_seconds_per_trial": 5.0,
        "max_artifact_bytes_per_completed_trial": 512 * 1024,
        "min_snapshot_count": 2,
    },
    "standard": {
        "max_elapsed_seconds_per_trial": 5.0,
        "max_artifact_bytes_per_completed_trial": 512 * 1024,
        "min_snapshot_count": 2,
    },
    "deep": {
        "max_elapsed_seconds_per_trial": 5.0,
        "max_artifact_bytes_per_completed_trial": 512 * 1024,
        "min_snapshot_count": 2,
    },
}


@dataclass(frozen=True, slots=True)
class DiscoveryBenchmarkResult:
    output_dir: Path
    report_path: Path


def write_discovery_benchmark_report(
    *,
    output_dir: Path | None = None,
    tier: str = "quick",
    repeat: int = 1,
    app_config: AppConfig | None = None,
) -> DiscoveryBenchmarkResult:
    tier_id = str(tier).strip().lower()
    if tier_id not in DISCOVERY_BENCHMARK_TIERS:
        raise ValueError(f"tier must be one of: {', '.join(sorted(DISCOVERY_BENCHMARK_TIERS))}")
    repeat_count = max(int(repeat), 1)
    config = app_config or AppConfig.from_env()
    benchmark_dir = (
        output_dir
        or config.research.output_dir / "benchmarks" / "research_discovery" / tier_id
    ).expanduser().resolve()
    benchmark_dir.mkdir(parents=True, exist_ok=True)

    runs_root = benchmark_dir / "runs"
    specs_root = benchmark_dir / "specs"
    if runs_root.exists():
        shutil.rmtree(runs_root)
    if specs_root.exists():
        shutil.rmtree(specs_root)

    tier_config = dict(DISCOVERY_BENCHMARK_TIERS[tier_id])
    repetitions: list[dict[str, Any]] = []
    for repeat_index in range(repeat_count):
        repetitions.append(
            _run_benchmark_repetition(
                benchmark_dir=benchmark_dir,
                tier_id=tier_id,
                tier_config=tier_config,
                repeat_index=repeat_index,
                app_config=config,
            )
        )

    report_path = benchmark_dir / "discovery_benchmark_report.json"
    report = {
        "discovery_benchmark_report_version": DISCOVERY_BENCHMARK_REPORT_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "benchmark_scope": "research_discovery_run_manager",
        "claim_scope": "discovery_resume_snapshot_regression_guardrail_not_live_or_profit_claim",
        "tier": tier_id,
        "tier_dimensions": tier_config,
        "regression_threshold_policy": dict(DISCOVERY_BENCHMARK_THRESHOLDS[tier_id]),
        "repeat": repeat_count,
        "runs": repetitions,
        "summary": _summary(repetitions),
        "artifact_overhead": {},
        "benchmark_gate": {},
        "live_fetch_used": False,
        "order_placement_used": False,
        "runtime_mode_changed": False,
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
    }
    _write_json(report_path, report)
    artifact_overhead = _artifact_overhead(benchmark_dir)
    report["artifact_overhead"] = artifact_overhead
    report["benchmark_gate"] = _discovery_benchmark_gate(
        tier_id=tier_id,
        tier_config=tier_config,
        repetitions=repetitions,
        artifact_overhead=artifact_overhead,
    )
    _write_json(report_path, report)
    return DiscoveryBenchmarkResult(output_dir=benchmark_dir, report_path=report_path)


def _run_benchmark_repetition(
    *,
    benchmark_dir: Path,
    tier_id: str,
    tier_config: Mapping[str, Any],
    repeat_index: int,
    app_config: AppConfig,
) -> dict[str, Any]:
    run_id = f"benchmark-{tier_id}-repeat-{repeat_index:02d}"
    clock = _fixed_clock(repeat_index)
    full_spec = _write_discovery_benchmark_spec(
        benchmark_dir / "specs" / f"repeat_{repeat_index:02d}" / "full" / "discovery_spec.json",
        run_id=run_id,
        research_output_dir=benchmark_dir,
        output_dir=benchmark_dir / "runs" / f"repeat_{repeat_index:02d}" / "full",
        tier_config=tier_config,
    )
    resumed_spec = _write_discovery_benchmark_spec(
        benchmark_dir / "specs" / f"repeat_{repeat_index:02d}" / "resumed" / "discovery_spec.json",
        run_id=run_id,
        research_output_dir=benchmark_dir,
        output_dir=benchmark_dir / "runs" / f"repeat_{repeat_index:02d}" / "resumed",
        tier_config=tier_config,
    )

    started = time.perf_counter()
    full_result = run_discovery(spec_path=full_spec, app_config=app_config, clock=clock)
    full_elapsed = max(time.perf_counter() - started, 1e-9)

    stop_after_trials = max(1, int(tier_config["max_trials"]) // 2)
    partial_result = run_discovery(
        spec_path=resumed_spec,
        app_config=app_config,
        stop_after_trials=stop_after_trials,
        clock=clock,
    )
    partial_payload = _run_payload(partial_result, elapsed_seconds=None)

    started = time.perf_counter()
    resumed_result = run_discovery(
        spec_path=resumed_spec,
        app_config=app_config,
        resume=True,
        clock=clock,
    )
    resumed_elapsed = max(time.perf_counter() - started, 1e-9)

    full_payload = _run_payload(full_result, elapsed_seconds=full_elapsed)
    resumed_payload = _run_payload(resumed_result, elapsed_seconds=resumed_elapsed)
    resume_ledger_hash_equal = full_payload["ledger_sha256"] == resumed_payload["ledger_sha256"]
    return {
        "repeat_index": repeat_index,
        "run_id": run_id,
        "stop_after_trials": stop_after_trials,
        "full": full_payload,
        "partial": partial_payload,
        "resumed": resumed_payload,
        "resume_ledger_hash_equal": resume_ledger_hash_equal,
        "completed_trial_ids_equal": full_payload["completed_trial_ids"] == resumed_payload["completed_trial_ids"],
        "snapshot_integrity_passed": bool(
            full_payload["snapshot_integrity"]["passed"]
            and partial_payload["snapshot_integrity"]["passed"]
            and resumed_payload["snapshot_integrity"]["passed"]
        ),
        "promotion_ready": False,
        "candidate_pack_written": False,
    }


def _write_discovery_benchmark_spec(
    path: Path,
    *,
    run_id: str,
    research_output_dir: Path,
    output_dir: Path,
    tier_config: Mapping[str, Any],
) -> Path:
    payload = {
        "spec_version": "discovery-run-spec-v1",
        "run_id": run_id,
        "symbol": str(tier_config["symbol"]),
        "timeframe": str(tier_config["timeframe"]),
        "discovery_mode": str(tier_config["discovery_mode"]),
        "research_output_dir": str(research_output_dir.resolve()),
        "output_dir": str(output_dir.resolve()),
        "feature_column_sets_path": "configs/discovery/feature_column_sets_v4.json",
        "feature_column_set_ids": list(tier_config.get("feature_column_set_ids") or []),
        "budget": {
            "max_trials": int(tier_config["max_trials"]),
            "trial_batch_size": int(tier_config["trial_batch_size"]),
            "snapshot_interval_minutes": int(tier_config["snapshot_interval_minutes"]),
            "rng_seed": 81,
        },
    }
    _write_json(path, payload)
    return path


def _run_payload(result: DiscoveryRunResult, *, elapsed_seconds: float | None) -> dict[str, Any]:
    manifest = _read_json(result.manifest_path)
    state = _read_json(result.run_state_path)
    ledger = _ledger_payload(result)
    snapshot_integrity = _snapshot_integrity(result.output_dir / "snapshots", run_id=str(manifest["run_id"]), state=state)
    trial_integrity = _trial_integrity(result.output_dir / "trials", state=state)
    completed_trial_count = len(state.get("completed_trial_ids") or [])
    payload = {
        "output_dir": str(result.output_dir),
        "manifest_path": str(result.manifest_path),
        "run_state_path": str(result.run_state_path),
        "status": state.get("status"),
        "message": state.get("message"),
        "completed_trial_ids": list(state.get("completed_trial_ids") or []),
        "completed_trial_count": completed_trial_count,
        "state_sha256": _stable_hash({"state": state}),
        "ledger_sha256": ledger["ledger_sha256"],
        "ledger_counts": ledger["ledger_counts"],
        "snapshot_integrity": snapshot_integrity,
        "trial_integrity": trial_integrity,
        "research_only": manifest.get("research_only"),
        "observe_only": manifest.get("observe_only"),
        "promotion_ready": manifest.get("promotion_ready"),
        "candidate_pack_written": manifest.get("candidate_pack_written"),
        "live_fetch_used": manifest.get("live_fetch_used"),
        "order_placement_used": manifest.get("order_placement_used"),
        "runtime_mode_changed": manifest.get("runtime_mode_changed"),
    }
    if elapsed_seconds is not None:
        payload["elapsed_seconds"] = round(float(elapsed_seconds), 6)
        payload["elapsed_seconds_per_completed_trial"] = round(float(elapsed_seconds) / max(completed_trial_count, 1), 6)
        payload["trials_per_second"] = round(float(completed_trial_count) / max(float(elapsed_seconds), 1e-9), 6)
    payload["deterministic_result_hash"] = _stable_hash(
        {
            "state_sha256": payload["state_sha256"],
            "ledger_sha256": payload["ledger_sha256"],
            "completed_trial_ids": payload["completed_trial_ids"],
            "snapshot_count": payload["snapshot_integrity"]["snapshot_count"],
        }
    )
    return payload


def _ledger_payload(result: DiscoveryRunResult) -> dict[str, Any]:
    frames = []
    for path in (result.interesting_candidates_path, result.blocked_candidates_path, result.filter_blockers_path):
        frame = pd.read_parquet(path)
        if not frame.empty:
            frames.append(frame)
    ledger = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if ledger.empty:
        records: list[dict[str, Any]] = []
    else:
        records = (
            ledger.sort_values(["trial_index", "trial_id", "ledger_kind"], kind="mergesort")
            .astype(object)
            .where(pd.notna(ledger), "")
            .to_dict("records")
        )
    return {
        "ledger_counts": {
            "row_count": len(records),
            "interesting_candidates": int((ledger.get("ledger_kind", pd.Series(dtype=str)) == "interesting").sum()) if not ledger.empty else 0,
            "blocked_candidates": int((ledger.get("ledger_kind", pd.Series(dtype=str)) == "blocked").sum()) if not ledger.empty else 0,
            "filter_blockers": int((ledger.get("ledger_kind", pd.Series(dtype=str)) == "filter_blocked").sum()) if not ledger.empty else 0,
        },
        "ledger_sha256": _stable_hash({"records": records}),
    }


def _snapshot_integrity(snapshot_dir: Path, *, run_id: str, state: Mapping[str, Any]) -> dict[str, Any]:
    paths = sorted(snapshot_dir.glob("*_snapshot.json"))
    readable_payloads: list[dict[str, Any]] = []
    failures: list[str] = []
    for path in paths:
        try:
            payload = _read_json(path)
        except Exception as exc:
            failures.append(f"{path.name}:{exc}")
            continue
        readable_payloads.append(payload)
        if payload.get("run_id") != run_id:
            failures.append(f"{path.name}:run_id_mismatch")
        if payload.get("snapshot_version") != "discovery-run-snapshot-v1":
            failures.append(f"{path.name}:snapshot_version_mismatch")
        if payload.get("research_only") is not True or payload.get("observe_only") is not True or payload.get("promotion_ready") is not False:
            failures.append(f"{path.name}:research_boundary_flags_invalid")
        if not isinstance(payload.get("summary"), dict):
            failures.append(f"{path.name}:summary_missing")
    sequences = [int(payload.get("snapshot_sequence") or 0) for payload in readable_payloads]
    if sequences != sorted(sequences) or len(sequences) != len(set(sequences)):
        failures.append("snapshot_sequence_not_monotonic_unique")
    tmp_files = sorted(snapshot_dir.glob("*.tmp"))
    if tmp_files:
        failures.extend(f"{path.name}:tmp_file_left_behind" for path in tmp_files)
    latest = readable_payloads[-1] if readable_payloads else {}
    latest_summary = latest.get("summary") if isinstance(latest.get("summary"), dict) else {}
    if latest_summary:
        if latest_summary.get("status") != state.get("status"):
            failures.append("latest_snapshot_status_mismatch")
        if int(latest_summary.get("completed_trial_count") or 0) != len(state.get("completed_trial_ids") or []):
            failures.append("latest_snapshot_completed_trial_count_mismatch")
    return {
        "passed": not failures and bool(paths),
        "snapshot_dir": str(snapshot_dir),
        "snapshot_count": len(paths),
        "readable_count": len(readable_payloads),
        "latest_snapshot_path": str(paths[-1]) if paths else None,
        "latest_summary": latest_summary or {},
        "tmp_file_count": len(tmp_files),
        "failure_reasons": failures,
    }


def _trial_integrity(trial_dir: Path, *, state: Mapping[str, Any]) -> dict[str, Any]:
    expected_hashes = dict(state.get("completed_trial_hashes") or {})
    failures: list[str] = []
    readable = 0
    for trial_id, expected_hash in sorted(expected_hashes.items()):
        path = trial_dir / f"{trial_id}.json"
        if not path.exists():
            failures.append(f"{trial_id}:trial_file_missing")
            continue
        try:
            record = read_trial_record(path)
        except Exception as exc:
            failures.append(f"{trial_id}:{exc}")
            continue
        readable += 1
        actual_hash = str(record.to_payload().get("record_sha256") or "")
        if actual_hash != str(expected_hash):
            failures.append(f"{trial_id}:state_hash_mismatch")
    tmp_files = sorted(trial_dir.glob("*.tmp"))
    if tmp_files:
        failures.extend(f"{path.name}:tmp_file_left_behind" for path in tmp_files)
    return {
        "passed": not failures and readable == len(expected_hashes),
        "trial_dir": str(trial_dir),
        "expected_completed_trial_count": len(expected_hashes),
        "readable_trial_count": readable,
        "tmp_file_count": len(tmp_files),
        "failure_reasons": failures,
    }


def _summary(repetitions: list[dict[str, Any]]) -> dict[str, Any]:
    full_elapsed = [float(row["full"].get("elapsed_seconds", 0.0)) for row in repetitions]
    resumed_elapsed = [float(row["resumed"].get("elapsed_seconds", 0.0)) for row in repetitions]
    return {
        "repeat_count": len(repetitions),
        "resume_ledger_hash_equal_count": sum(1 for row in repetitions if row["resume_ledger_hash_equal"]),
        "snapshot_integrity_passed_count": sum(1 for row in repetitions if row["snapshot_integrity_passed"]),
        "full_elapsed_seconds_mean": round(sum(full_elapsed) / max(len(full_elapsed), 1), 6),
        "resumed_elapsed_seconds_mean": round(sum(resumed_elapsed) / max(len(resumed_elapsed), 1), 6),
        "completed_trial_count_mean": round(
            sum(int(row["resumed"]["completed_trial_count"]) for row in repetitions) / max(len(repetitions), 1),
            6,
        ),
    }


def _artifact_overhead(root: Path) -> dict[str, Any]:
    files = sorted(path for path in root.rglob("*") if path.is_file())
    total_bytes = sum(int(path.stat().st_size) for path in files)
    completed_trials = 0
    for state_path in root.rglob("run_state.json"):
        try:
            state = _read_json(state_path)
        except Exception:
            continue
        completed_trials += len(state.get("completed_trial_ids") or [])
    report_path = root / "discovery_benchmark_report.json"
    return {
        "scope": "discovery_benchmark_directory_after_report_write",
        "root": str(root),
        "file_count": len(files),
        "total_bytes": total_bytes,
        "completed_trial_records_counted": completed_trials,
        "bytes_per_completed_trial": round(float(total_bytes) / max(completed_trials, 1), 6),
        "includes_final_report": report_path.is_file(),
        "final_report_path": str(report_path),
        "final_report_bytes": int(report_path.stat().st_size) if report_path.is_file() else 0,
    }


def _discovery_benchmark_gate(
    *,
    tier_id: str,
    tier_config: Mapping[str, Any],
    repetitions: list[dict[str, Any]],
    artifact_overhead: Mapping[str, Any],
) -> dict[str, Any]:
    thresholds = DISCOVERY_BENCHMARK_THRESHOLDS[tier_id]
    expected_trials = int(tier_config["max_trials"])
    checks = [
        _threshold_check(
            "completed_trials_match_tier_budget",
            actual=all(int(row["resumed"]["completed_trial_count"]) == expected_trials for row in repetitions),
            threshold=True,
            operator="is",
            passed=all(int(row["resumed"]["completed_trial_count"]) == expected_trials for row in repetitions),
        ),
        _threshold_check(
            "partial_run_pauses_before_completion",
            actual=all(row["partial"]["status"] == "in_progress" for row in repetitions),
            threshold=True,
            operator="is",
            passed=all(row["partial"]["status"] == "in_progress" for row in repetitions),
        ),
        _threshold_check(
            "resumed_run_completes",
            actual=all(row["resumed"]["status"] == "completed" for row in repetitions),
            threshold=True,
            operator="is",
            passed=all(row["resumed"]["status"] == "completed" for row in repetitions),
        ),
        _threshold_check(
            "resume_ledger_hash_equal",
            actual=all(bool(row["resume_ledger_hash_equal"]) for row in repetitions),
            threshold=True,
            operator="is",
            passed=all(bool(row["resume_ledger_hash_equal"]) for row in repetitions),
        ),
        _threshold_check(
            "completed_trial_ids_equal",
            actual=all(bool(row["completed_trial_ids_equal"]) for row in repetitions),
            threshold=True,
            operator="is",
            passed=all(bool(row["completed_trial_ids_equal"]) for row in repetitions),
        ),
        _threshold_check(
            "snapshot_integrity_passed",
            actual=all(bool(row["snapshot_integrity_passed"]) for row in repetitions),
            threshold=True,
            operator="is",
            passed=all(bool(row["snapshot_integrity_passed"]) for row in repetitions),
        ),
        _threshold_check(
            "trial_integrity_passed",
            actual=all(
                bool(row["full"]["trial_integrity"]["passed"])
                and bool(row["partial"]["trial_integrity"]["passed"])
                and bool(row["resumed"]["trial_integrity"]["passed"])
                for row in repetitions
            ),
            threshold=True,
            operator="is",
            passed=all(
                bool(row["full"]["trial_integrity"]["passed"])
                and bool(row["partial"]["trial_integrity"]["passed"])
                and bool(row["resumed"]["trial_integrity"]["passed"])
                for row in repetitions
            ),
        ),
        _threshold_check(
            "snapshot_count_minimum",
            actual=min(
                int(row["resumed"]["snapshot_integrity"].get("snapshot_count", 0))
                for row in repetitions
            )
            if repetitions
            else 0,
            threshold=int(thresholds["min_snapshot_count"]),
            operator=">=",
            passed=all(
                int(row["resumed"]["snapshot_integrity"].get("snapshot_count", 0)) >= int(thresholds["min_snapshot_count"])
                for row in repetitions
            ),
        ),
        _threshold_check(
            "elapsed_seconds_per_trial",
            actual=max(
                float(row["full"].get("elapsed_seconds_per_completed_trial", 0.0))
                for row in repetitions
            )
            if repetitions
            else 0.0,
            threshold=float(thresholds["max_elapsed_seconds_per_trial"]),
            operator="<=",
            passed=all(
                float(row["full"].get("elapsed_seconds_per_completed_trial", 0.0)) <= float(thresholds["max_elapsed_seconds_per_trial"])
                for row in repetitions
            ),
        ),
        _threshold_check(
            "artifact_bytes_per_completed_trial",
            actual=float(artifact_overhead.get("bytes_per_completed_trial", 0.0)),
            threshold=float(thresholds["max_artifact_bytes_per_completed_trial"]),
            operator="<=",
            passed=float(artifact_overhead.get("bytes_per_completed_trial", 0.0)) <= float(thresholds["max_artifact_bytes_per_completed_trial"]),
        ),
        _threshold_check(
            "artifact_overhead_includes_final_report",
            actual=bool(artifact_overhead.get("includes_final_report", False)),
            threshold=True,
            operator="is",
            passed=bool(artifact_overhead.get("includes_final_report", False)),
            evidence_required=True,
        ),
        _threshold_check(
            "research_boundary_flags_preserved",
            actual=all(
                row["full"]["research_only"] is True
                and row["full"]["observe_only"] is True
                and row["full"]["promotion_ready"] is False
                and row["resumed"]["research_only"] is True
                and row["resumed"]["observe_only"] is True
                and row["resumed"]["promotion_ready"] is False
                for row in repetitions
            ),
            threshold=True,
            operator="is",
            passed=all(
                row["full"]["research_only"] is True
                and row["full"]["observe_only"] is True
                and row["full"]["promotion_ready"] is False
                and row["resumed"]["research_only"] is True
                and row["resumed"]["observe_only"] is True
                and row["resumed"]["promotion_ready"] is False
                for row in repetitions
            ),
        ),
        _threshold_check(
            "no_live_or_pack_outputs",
            actual=all(
                row["full"]["live_fetch_used"] is False
                and row["full"]["order_placement_used"] is False
                and row["full"]["runtime_mode_changed"] is False
                and row["full"]["candidate_pack_written"] is False
                and row["resumed"]["live_fetch_used"] is False
                and row["resumed"]["order_placement_used"] is False
                and row["resumed"]["runtime_mode_changed"] is False
                and row["resumed"]["candidate_pack_written"] is False
                for row in repetitions
            ),
            threshold=True,
            operator="is",
            passed=all(
                row["full"]["live_fetch_used"] is False
                and row["full"]["order_placement_used"] is False
                and row["full"]["runtime_mode_changed"] is False
                and row["full"]["candidate_pack_written"] is False
                and row["resumed"]["live_fetch_used"] is False
                and row["resumed"]["order_placement_used"] is False
                and row["resumed"]["runtime_mode_changed"] is False
                and row["resumed"]["candidate_pack_written"] is False
                for row in repetitions
            ),
        ),
    ]
    failure_reasons = [
        str(check["failure_reason"])
        for check in checks
        if str(check["status"]) == "failed" and str(check["failure_reason"])
    ]
    incomplete_evidence_reasons = [
        str(check["failure_reason"])
        for check in checks
        if bool(check.get("evidence_required", False))
        and str(check["status"]) == "failed"
        and str(check["failure_reason"])
    ]
    return {
        "gate_version": DISCOVERY_BENCHMARK_GATE_VERSION,
        "profile_version": f"discovery-benchmark-{tier_id}-thresholds-v1",
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "scope": "research_discovery_resume_snapshot_integrity",
        "claim_scope": "regression_guardrail_not_live_or_profit_claim",
        "checks": checks,
        "thresholds": dict(thresholds),
        "evidence_complete": not incomplete_evidence_reasons,
        "passed": not failure_reasons and not incomplete_evidence_reasons,
        "failure_reasons": failure_reasons,
        "skipped_reasons": [],
        "incomplete_evidence_reasons": incomplete_evidence_reasons,
    }


def _threshold_check(
    name: str,
    *,
    actual: Any,
    threshold: Any,
    operator: str,
    passed: bool,
    failure_reason: str | None = None,
    evidence_required: bool = False,
) -> dict[str, Any]:
    return {
        "check_id": name,
        "name": name,
        "metric": name,
        "observed": actual,
        "actual": actual,
        "threshold": threshold,
        "comparator": operator,
        "operator": operator,
        "passed": bool(passed),
        "status": "passed" if passed else "failed",
        "failure_reason": failure_reason if failure_reason is not None else ("" if passed else f"{name}_failed"),
        "evidence_required": bool(evidence_required),
    }


def _fixed_clock(repeat_index: int):
    value = datetime(2026, 5, 8, 12, min(repeat_index, 59), tzinfo=timezone.utc)

    def clock() -> datetime:
        return value

    return clock


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True, default=str, allow_nan=False) + "\n", encoding="utf-8")


def _stable_hash(payload: Any) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False).encode("utf-8")).hexdigest()
