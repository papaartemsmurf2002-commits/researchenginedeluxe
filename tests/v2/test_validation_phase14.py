from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from tradingbotsuite.v2.ledger import LedgerAppendRequest, append_run_to_ledger, leaderboard
from tradingbotsuite.v2.validation import (
    TrialResult,
    WalkForwardConfig,
    build_walk_forward_folds,
    check_sweep_completeness,
    reject_post_lockbox_parameter_tuning,
    require_complete_sweep,
    trial_family_report,
)


HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64


def test_experiment_sweep_records_all_trials() -> None:
    report = check_sweep_completeness(
        experiment_id="sweep-1",
        expected_trial_ids=("trial-1", "trial-2", "trial-3"),
        observed_trial_ids=("trial-1", "trial-2", "trial-3"),
    )
    require_complete_sweep(report)

    incomplete = check_sweep_completeness(
        experiment_id="sweep-1",
        expected_trial_ids=("trial-1", "trial-2", "trial-3"),
        observed_trial_ids=("trial-1", "trial-3"),
    )
    assert incomplete.missing_trial_ids == ("trial-2",)
    with pytest.raises(ValueError, match="sweep_trial_logging_incomplete"):
        require_complete_sweep(incomplete)


def test_walk_forward_folds_are_time_ordered() -> None:
    rows = _timestamp_rows(20)
    folds = build_walk_forward_folds(
        rows,
        config=WalkForwardConfig(min_train_rows=8, validation_rows=3, step_rows=3),
    )

    assert len(folds) >= 3
    for fold in folds:
        assert max(fold.train_indices) < min(fold.validation_indices)
        assert fold.train_end < fold.validation_start


def test_embargo_gap_excludes_boundary_rows() -> None:
    rows = _timestamp_rows(16)
    folds = build_walk_forward_folds(
        rows,
        config=WalkForwardConfig(
            min_train_rows=6,
            validation_rows=2,
            step_rows=4,
            purge_rows=1,
            embargo_rows=2,
        ),
    )
    first = folds[0]

    assert first.train_indices == (0, 1, 2, 3, 4)
    assert first.embargo_indices == (5, 6, 7)
    assert first.validation_indices == (8, 9)
    assert set(first.embargo_indices).isdisjoint(first.train_indices)
    assert set(first.embargo_indices).isdisjoint(first.validation_indices)


def test_leaderboard_warns_when_best_result_is_from_many_trials() -> None:
    trials = [
        TrialResult(
            run_id=f"trial-{index:02d}",
            experiment_id="sweep-many",
            family_id="family-a",
            net_return=-0.01,
            fold_returns=(-0.01, -0.02, -0.01),
        )
        for index in range(19)
    ]
    trials.append(
        TrialResult(
            run_id="trial-best",
            experiment_id="sweep-many",
            family_id="family-a",
            net_return=0.25,
            fold_returns=(0.4, -0.2, -0.1),
        )
    )

    report = trial_family_report(trials, large_family_threshold=20)

    assert report.trial_count == 20
    assert report.large_weak_family_warning is True
    assert "large_weak_family_best_result_warning" in report.blocker_reasons


def test_validation_rejects_missing_experiment_id_for_sweep() -> None:
    with pytest.raises(ValueError, match="experiment_id is required"):
        check_sweep_completeness(
            experiment_id="",
            expected_trial_ids=("trial-1",),
            observed_trial_ids=("trial-1",),
        )


def test_validation_rejects_post_lockbox_parameter_tuning() -> None:
    with pytest.raises(ValueError, match="post_lockbox_parameter_tuning_rejected"):
        reject_post_lockbox_parameter_tuning(
            tuned_at=datetime(2026, 5, 2, tzinfo=UTC),
            lockbox_start=datetime(2026, 5, 1, tzinfo=UTC),
        )


def test_pbo_diagnostic_runs_for_large_strategy_family() -> None:
    trials = [
        TrialResult(
            run_id="overfit-best",
            experiment_id="sweep-pbo",
            family_id="family-pbo",
            net_return=0.5,
            fold_returns=(-0.1, -0.1, -0.1),
        )
    ]
    trials.extend(
        TrialResult(
            run_id=f"stable-{index}",
            experiment_id="sweep-pbo",
            family_id="family-pbo",
            net_return=0.05 + index * 0.001,
            fold_returns=(0.04, 0.05, 0.06),
        )
        for index in range(7)
    )

    report = trial_family_report(trials, min_trials_for_pbo=6)

    assert report.pbo_diagnostic_ran is True
    assert report.pbo_score is not None
    assert report.pbo_score >= 0.5
    assert "pbo_overfit_warning" in report.blocker_reasons


def test_leaderboard_includes_trial_count_and_fold_stability(tmp_path) -> None:
    ledger_path = tmp_path / "ledger.parquet"
    first = _write_run_manifest_with_fold_metrics(
        tmp_path,
        "fold-stable-1",
        net_return=0.12,
        fold_returns=(0.03, 0.02, 0.01),
    )
    second = _write_run_manifest_with_fold_metrics(
        tmp_path,
        "fold-stable-2",
        net_return=0.08,
        fold_returns=(0.02, -0.01, 0.01),
    )
    for manifest_path in (first, second):
        append_run_to_ledger(
            LedgerAppendRequest(
                run_manifest_path=str(manifest_path),
                ledger_path=str(ledger_path),
                evidence_mode="accepted_research",
            )
        )

    rows = leaderboard(
        ledger_path=ledger_path,
        require_validation_pass=True,
        exclude_sandbox=True,
    )

    assert rows[0].trial_count == 2
    assert rows[0].fold_count == 3
    assert rows[0].fold_stability_score == 1.0


def _timestamp_rows(count: int) -> list[dict[str, str]]:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    return [{"ts": (start + timedelta(hours=index)).isoformat()} for index in range(count)]


def _write_run_manifest_with_fold_metrics(
    root: Path,
    run_id: str,
    *,
    net_return: float,
    fold_returns: tuple[float, ...],
) -> Path:
    run_dir = root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        pa.Table.from_pylist(
            [
                {
                    "fold_id": f"fold-{index}",
                    "start_ts": f"2024-0{index + 1}-01T00:00:00Z",
                    "end_ts": f"2024-0{index + 2}-01T00:00:00Z",
                    "gross_return": value,
                    "net_return": value,
                    "research_only": True,
                    "observe_only": True,
                    "promotion_ready": False,
                }
                for index, value in enumerate(fold_returns)
            ]
        ),
        run_dir / "fold_metrics.parquet",
    )
    payload = _manifest_payload(run_id, net_return=net_return)
    path = run_dir / "run_manifest.json"
    path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
    return path


def _manifest_payload(run_id: str, *, net_return: float) -> dict[str, object]:
    return {
        "schema_version": "run_manifest_v1",
        "run_id": run_id,
        "experiment_id": "phase14-family",
        "trial_index": 0,
        "agent_or_user": "agent",
        "created_at": "2024-08-01T00:00:00Z",
        "status": "succeeded",
        "engine_lane": "vectorized",
        "strategy_lane": "declarative",
        "git_sha": "test-git-sha",
        "environment_hash": HEX_A,
        "strategy_id": "fold_stability_strategy",
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
        "timeframe": "1h",
        "backtest_start": "2024-01-01T00:00:00Z",
        "backtest_end": "2024-08-01T00:00:00Z",
        "usable_months": 7,
        "lockbox_policy_id": "dynamic_full_calendar_months_v1",
        "lockbox_start": None,
        "lockbox_end": None,
        "data_coverage_min": 0.98,
        "cost_model_id": "conservative_hyperliquid_taker_v1",
        "cost_model_hash": HEX_A,
        "validation_policy_id": "validation-v1",
        "validation_status": "pass",
        "missing_data_policy": "fail_closed",
        "price_basis": "next_bar_open",
        "failure_reason": None,
        "metrics": {
            "schema_version": "v2",
            "run_id": run_id,
            "status": "succeeded",
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
            "position_row_count": 12,
            "capacity_blocked_count": 0,
            "gross_only": False,
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
        },
        "artifacts": {
            name: {"name": name, "path": path, "sha256": HEX_A, "required": True}
            for name, path in _artifact_paths().items()
        },
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


def _artifact_paths() -> dict[str, str]:
    return {
        "strategy_spec": "strategy_spec.json",
        "params": "params.json",
        "data_manifest": "data_manifest.json",
        "validation_manifest": "validation_manifest.json",
        "cost_manifest": "cost_manifest.json",
        "cost_stress": "cost_stress.parquet",
        "metrics": "metrics.json",
        "equity_curve": "equity_curve.parquet",
        "daily_returns": "daily_returns.parquet",
        "trades": "trades.parquet",
        "positions": "positions.parquet",
        "per_instrument_metrics": "per_instrument_metrics.parquet",
        "fold_metrics": "fold_metrics.parquet",
        "log": "logs/log.txt",
    }
