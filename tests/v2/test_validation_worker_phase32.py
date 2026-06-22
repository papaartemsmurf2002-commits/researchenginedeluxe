from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from tradingbotsuite.v2.archive.hashing import file_sha256
from tradingbotsuite.v2.backtest_engine.artifacts import RunManifest
from tradingbotsuite.v2.workers.job_store import WorkerJobStore
from tradingbotsuite.v2.workers.models import WorkerJobKind, WorkerJobStatus
from tradingbotsuite.v2.workers.runner import run_one_job


HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64
HEX_D = "d" * 64


def test_validation_gate_worker_writes_pass_manifest(tmp_path) -> None:
    run_manifest_path = _write_run_artifacts(tmp_path / "runs" / "validation-pass")
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.VALIDATION_GATE,
        job_id="JOB-validation-pass",
        input_spec={
            "run_manifest_path": str(run_manifest_path),
            "evidence_mode": "accepted_research",
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.VALIDATION_GATE,
        worker_id="worker-validation-pass",
    )
    loaded = store.load_job(queued.job_id)
    report_path = run_manifest_path.parent / "validation_gate_manifest.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert loaded.status == WorkerJobStatus.SUCCEEDED
    assert "job_kind=validation_gate" in loaded.output_refs
    assert "validation_status=pass" in loaded.output_refs
    assert "blocker_reasons=" in loaded.output_refs
    assert any(ref.startswith("validation_manifest_sha256=") for ref in loaded.output_refs)
    assert any(ref.startswith("validation_manifest_id=") for ref in loaded.archive_manifest_refs)
    assert report["validation_status"] == "pass"
    assert report["blocker_reasons"] == []
    assert report["fold_count"] == 3
    assert report["positive_fold_count"] == 2
    assert report["fold_stability_score"] == 2 / 3
    assert set(report["cost_stress_scenarios"]) == {"base", "stress_2x", "stress_3x"}
    assert report["research_only"] is True
    assert report["observe_only"] is True
    assert report["promotion_ready"] is False
    assert report["candidate_evidence"] is False
    assert report["candidate_pack_eligible"] is False
    assert report["live_signal"] is False
    assert report["paper_signal"] is False
    assert report["sizing_instruction"] is False
    assert report["order_placement_instruction"] is False
    assert report["runtime_mode_change"] is False


def test_validation_gate_worker_reports_blockers_without_worker_failure(tmp_path) -> None:
    run_manifest_path = _write_run_artifacts(
        tmp_path / "runs" / "validation-blocked",
        run_updates={
            "validation_status": "fail",
            "universe_mode": "current",
            "backtest_start": "2023-12-01T00:00:00Z",
            "usable_months": 5,
            "data_coverage_min": 0.75,
            "lockbox_start": "2024-06-01T00:00:00Z",
            "lockbox_end": "2024-07-01T00:00:00Z",
        },
        fold_rows=[
            _fold_row("fold-0", -0.02),
            _fold_row("fold-1", -0.01),
        ],
        cost_rows=[
            _cost_row("base", 0.01),
            _cost_row("stress_2x", -0.02, cost_dependent_failure=True),
        ],
    )
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.VALIDATION_GATE,
        job_id="JOB-validation-blocked",
        input_spec={
            "run_manifest_path": str(run_manifest_path),
            "evidence_mode": "accepted_research",
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.VALIDATION_GATE,
        worker_id="worker-validation-blocked",
    )
    loaded = store.load_job(queued.job_id)
    report = json.loads(
        (run_manifest_path.parent / "validation_gate_manifest.json").read_text(encoding="utf-8")
    )

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert loaded.status == WorkerJobStatus.SUCCEEDED
    assert "validation_status=fail" in loaded.output_refs
    blockers = set(report["blocker_reasons"])
    assert "run_manifest_validation_status_fail" in blockers
    assert "backtest_start_before_2024" in blockers
    assert "usable_months_below_6" in blockers
    assert "coverage_below_0_98" in blockers
    assert "accepted_research_requires_asof_universe" in blockers
    assert "lockbox_overlap" in blockers
    assert "fold_stability_below_min_share" in blockers
    assert "cost_stress_scenario_missing:stress_3x" in blockers
    assert "cost_dependent_failure" in blockers


def test_validation_gate_worker_rejects_secret_like_report_path_before_write(tmp_path) -> None:
    run_manifest_path = _write_run_artifacts(tmp_path / "runs" / "validation-secret")
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.VALIDATION_GATE,
        job_id="JOB-validation-secret",
        max_attempts=1,
        input_spec={
            "run_manifest_path": str(run_manifest_path),
            "validation_manifest_path": str(run_manifest_path.parent / ".env"),
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.VALIDATION_GATE,
        worker_id="worker-validation-secret",
    )
    loaded = store.load_job(queued.job_id)

    assert result is not None
    assert result.status == WorkerJobStatus.FAILED
    assert loaded is not None
    assert "reserved for secrets or local state" in (loaded.failure_reason or "")
    assert not (run_manifest_path.parent / ".env").exists()


def _write_run_artifacts(
    run_dir: Path,
    *,
    run_updates: dict[str, Any] | None = None,
    fold_rows: list[dict[str, Any]] | None = None,
    cost_rows: list[dict[str, Any]] | None = None,
) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    fold_rows = fold_rows or [
        _fold_row("fold-0", 0.02),
        _fold_row("fold-1", 0.01),
        _fold_row("fold-2", -0.005),
    ]
    cost_rows = cost_rows or [
        _cost_row("base", 0.03),
        _cost_row("stress_2x", 0.02),
        _cost_row("stress_3x", 0.01),
    ]
    metrics = _metrics_payload(run_id=run_dir.name)
    artifact_specs: dict[str, tuple[str, str, Any, int | None]] = {
        "strategy_spec": ("json", "strategy_spec.json", {"strategy_id": "validation_worker_spec"}, None),
        "params": ("json", "params.json", {}, None),
        "data_manifest": ("json", "data_manifest.json", {"data_manifest_id": "data-manifest"}, None),
        "validation_manifest": ("json", "validation_manifest.json", {"status": "pass"}, None),
        "cost_manifest": ("json", "cost_manifest.json", {"cost_model_id": "conservative"}, None),
        "metrics": ("json", "metrics.json", metrics, None),
        "equity_curve": ("parquet", "equity_curve.parquet", [{"dummy": 1}], 1),
        "daily_returns": ("parquet", "daily_returns.parquet", [{"dummy": 1}], 1),
        "trades": ("parquet", "trades.parquet", [{"dummy": 1}], 1),
        "positions": ("parquet", "positions.parquet", [{"dummy": 1}], 1),
        "per_instrument_metrics": ("parquet", "per_instrument_metrics.parquet", [{"dummy": 1}], 1),
        "fold_metrics": ("parquet", "fold_metrics.parquet", fold_rows, len(fold_rows)),
        "cost_stress": ("parquet", "cost_stress.parquet", cost_rows, len(cost_rows)),
    }
    artifacts: dict[str, dict[str, Any]] = {}
    for name, (kind, filename, payload, row_count) in artifact_specs.items():
        path = run_dir / filename
        if kind == "json":
            path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        else:
            pq.write_table(pa.Table.from_pylist(payload), path)
        artifacts[name] = _artifact_ref(run_dir, path, name, row_count)
    log_path = run_dir / "logs" / "log.txt"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("validation worker test log\n", encoding="utf-8")
    artifacts["log"] = _artifact_ref(run_dir, log_path, "log", None)

    payload = {
        "schema_version": "run_manifest_v1",
        "run_id": run_dir.name,
        "experiment_id": "validation-worker",
        "trial_index": 0,
        "agent_or_user": "agent",
        "created_at": "2024-08-01T00:00:00Z",
        "status": "succeeded",
        "engine_lane": "vectorized",
        "strategy_lane": "declarative",
        "git_sha": "test-git-sha",
        "environment_hash": HEX_A,
        "strategy_id": "validation_worker_strategy",
        "strategy_version": "0.1.0",
        "strategy_hash": HEX_B,
        "strategy_spec_hash": HEX_B,
        "params_hash": HEX_C,
        "archive_snapshot_id": "archive-snapshot",
        "universe_snapshot_id": "universe-snapshot",
        "data_manifest_id": "data-manifest",
        "data_manifest_hash": HEX_A,
        "validation_manifest_hash": HEX_B,
        "cost_manifest_hash": HEX_C,
        "universe_mode": "as_of",
        "venue_scope": "hyperliquid",
        "instrument_count": 3,
        "timeframe": "1d",
        "backtest_start": "2024-01-01T00:00:00Z",
        "backtest_end": "2024-08-01T00:00:00Z",
        "usable_months": 7,
        "lockbox_policy_id": "dynamic_full_calendar_months_v1",
        "lockbox_start": None,
        "lockbox_end": None,
        "data_coverage_min": 0.98,
        "cost_model_id": "conservative_hyperliquid_taker_v1",
        "cost_model_hash": HEX_D,
        "validation_policy_id": "v2_default_validation_v1",
        "validation_status": "pass",
        "missing_data_policy": "fail_closed",
        "price_basis": "next_bar_open",
        "failure_reason": None,
        "metrics": metrics,
        "artifacts": artifacts,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "candidate_evidence": False,
        "candidate_pack_eligible": False,
        "live_signal": False,
        "paper_signal": False,
        "sizing_instruction": False,
        "order_placement_instruction": False,
        "runtime_mode_change": False,
    }
    payload.update(run_updates or {})
    RunManifest.model_validate(payload)
    path = run_dir / "run_manifest.json"
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return path


def _artifact_ref(run_dir: Path, path: Path, name: str, row_count: int | None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": name,
        "path": path.relative_to(run_dir).as_posix(),
        "sha256": file_sha256(path),
        "required": True,
    }
    if row_count is not None:
        payload["row_count"] = row_count
    return payload


def _metrics_payload(*, run_id: str) -> dict[str, Any]:
    return {
        "schema_version": "redx-v2-phase1-shell-v1",
        "run_id": run_id,
        "status": "succeeded",
        "gross_return": 0.04,
        "net_return": 0.03,
        "gross_equity_final": 1.04,
        "net_equity_final": 1.03,
        "total_fee_cost": 0.01,
        "total_spread_cost": 0.002,
        "total_slippage_cost": 0.003,
        "total_impact_cost": 0.001,
        "total_transaction_cost": 0.016,
        "total_funding_pnl": 0.0,
        "total_turnover": 2.0,
        "trade_count": 4,
        "position_row_count": 12,
        "capacity_blocked_count": 0,
        "gross_only": False,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "candidate_evidence": False,
        "candidate_pack_eligible": False,
        "live_signal": False,
        "paper_signal": False,
        "sizing_instruction": False,
        "order_placement_instruction": False,
        "runtime_mode_change": False,
    }


def _fold_row(fold_id: str, net_return: float) -> dict[str, Any]:
    return {
        "fold_id": fold_id,
        "start_ts": "2024-01-01T00:00:00Z",
        "end_ts": "2024-02-01T00:00:00Z",
        "gross_return": net_return + 0.001,
        "net_return": net_return,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
    }


def _cost_row(
    scenario_id: str,
    net_return: float,
    *,
    cost_dependent_failure: bool = False,
) -> dict[str, Any]:
    return {
        "scenario_id": scenario_id,
        "cost_model_id": "conservative_hyperliquid_taker_v1",
        "cost_model_hash": HEX_D,
        "cost_multiplier": 1.0,
        "gross_return": net_return + 0.01,
        "net_return": net_return,
        "gross_equity_final": 1.0 + net_return + 0.01,
        "net_equity_final": 1.0 + net_return,
        "total_fee_cost": 0.01,
        "total_spread_cost": 0.002,
        "total_slippage_cost": 0.003,
        "total_impact_cost": 0.001,
        "total_transaction_cost": 0.016,
        "total_funding_pnl": 0.0,
        "total_turnover": 2.0,
        "trade_count": 4,
        "capacity_blocked_count": 0,
        "cost_fragile_warning": cost_dependent_failure,
        "cost_dependent_failure": cost_dependent_failure,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
    }
