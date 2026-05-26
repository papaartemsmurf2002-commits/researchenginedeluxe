from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from tradingbotsuite.research_discovery.analysis_report import (
    build_research_analysis,
    write_research_analysis_artifacts,
)


def test_analysis_report_summarizes_cycle_discovery_and_sortino(tmp_path: Path) -> None:
    cycle_dir = tmp_path / "cycle"
    discovery_dir = tmp_path / "discovery"
    cycle_dir.mkdir()
    discovery_dir.mkdir()

    trades_dir = cycle_dir / "backtests" / "agg-candidate-a"
    trades_dir.mkdir(parents=True)
    trades_path = trades_dir / "trades.parquet"
    pd.DataFrame({"net_return": [0.03, -0.01, 0.02, -0.005]}).to_parquet(trades_path, index=False)

    rankings_path = cycle_dir / "candidate_rankings.parquet"
    pd.DataFrame(
        [
            {
                "candidate_id": "candidate-a",
                "strategy_id": "trend_following_v1",
                "feature_set_id": "features_price_trend_vol",
                "holding_window": "4h",
                "exit_policy_id": "fixed_holding_window",
                "costed_expectancy": 0.002,
                "net_return_after_fees_slippage_funding": 0.11,
                "trade_count": 4,
                "hit_rate": 0.5,
                "profit_factor": 2.0,
                "max_drawdown": -0.02,
                "final_score": 1.5,
                "decision": "review",
                "failure_reasons": "split_evidence_required|cost_stress_required",
            },
            {
                "candidate_id": "candidate-b",
                "strategy_id": "range_reversion_v1",
                "feature_set_id": "features_aggtrade_orderflow_v1",
                "holding_window": "1h",
                "exit_policy_id": "fixed_holding_window",
                "costed_expectancy": -0.001,
                "net_return_after_fees_slippage_funding": -0.03,
                "trade_count": 3,
                "hit_rate": 0.33,
                "profit_factor": 0.8,
                "max_drawdown": -0.05,
                "final_score": -0.4,
                "decision": "rejected",
                "failure_reasons": "no_trade_baseline_not_beaten",
            },
        ]
    ).to_parquet(rankings_path, index=False)
    gate_path = cycle_dir / "candidate_gate_report.parquet"
    pd.DataFrame(
        [
            {
                "candidate_id": "candidate-a",
                "pack_eligible": True,
                "gate_reasons": "ranking_decision_not_research_gate_passed|positive_cost_stress_survival_required",
            },
            {
                "candidate_id": "candidate-b",
                "pack_eligible": False,
                "gate_reasons": "positive_cost_stress_survival_required",
            },
        ]
    ).to_parquet(gate_path, index=False)
    split_path = cycle_dir / "metrics_by_split.parquet"
    pd.DataFrame(
        [
            {
                "candidate_id": "candidate-a",
                "validation_method": "purged_embargoed_walk_forward",
                "split_mode": "anchored",
                "trade_count": 2,
                "net_return_after_fees_slippage_funding": 0.05,
            }
        ]
    ).to_parquet(split_path, index=False)
    backtest_index_path = cycle_dir / "backtest_index.parquet"
    pd.DataFrame(
        [
            {
                "candidate_id": "candidate-a",
                "evaluation_scope": "aggregate",
                "trades_path": str(trades_path),
            }
        ]
    ).to_parquet(backtest_index_path, index=False)
    (cycle_dir / "research_cycle_manifest.json").write_text(
        json.dumps(
            {
                "cycle_id": "cycle-test",
                "symbol": "BTCUSDT",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "candidate_acceptance_scope": "research_gate_evaluated_fail_closed",
                "candidate_pack_written": False,
                "candidate_count": 2,
                "required_outputs": {
                    "candidate_rankings": str(rankings_path),
                    "candidate_gate_report": str(gate_path),
                    "metrics_by_split": str(split_path),
                    "backtest_index": str(backtest_index_path),
                },
            }
        ),
        encoding="utf-8",
    )
    (cycle_dir / "data_quality_report.json").write_text(
        json.dumps(
            {
                "row_count": 100,
                "time_span": {"first_time": "2024-01-01", "last_time": "2024-01-02"},
                "data_source": {"base_interval": "15m"},
            }
        ),
        encoding="utf-8",
    )

    ledgers_dir = discovery_dir / "candidate_ledgers"
    ledgers_dir.mkdir()
    interesting_path = ledgers_dir / "interesting_candidates.parquet"
    blocked_path = ledgers_dir / "blocked_candidates.parquet"
    filter_path = ledgers_dir / "filter_blockers.parquet"
    pd.DataFrame(
        [
            {
                "candidate_id": "knn-a",
                "ledger_kind": "interesting",
                "feature_column_set_id": "compact_wt3d_base",
                "label_horizon": "1h",
                "distance_metric": "cosine",
                "k": 13,
                "min_neighbor_count": 2,
                "regime_mode": "none",
                "trade_count": 10,
                "accepted_bar_count": 40,
                "independent_event_count": 10,
                "realized_expectancy": 0.001,
                "independent_event_expectancy": 0.001,
                "signal_rate": 0.12,
                "event_signal_rate": 0.03,
                "overlap_ratio": 0.2,
                "side_collapse_ratio": 0.52,
                "final_score": 0.6,
            }
        ]
    ).to_parquet(interesting_path, index=False)
    pd.DataFrame(
        [
            {
                "candidate_id": "knn-b",
                "ledger_kind": "blocked",
                "blocker_code": "overlap_ratio_above_ceiling",
                "feature_column_set_id": "compact_wt3d_base",
                "label_horizon": "1h",
                "distance_metric": "cosine",
                "k": 13,
                "min_neighbor_count": 2,
                "regime_mode": "none",
                "realized_expectancy": 0.0005,
                "final_score": 0.4,
            }
        ]
    ).to_parquet(blocked_path, index=False)
    pd.DataFrame(columns=pd.read_parquet(interesting_path).columns).to_parquet(filter_path, index=False)
    (discovery_dir / "discovery_run_manifest.json").write_text(
        json.dumps(
            {
                "run_id": "exact-test",
                "symbol": "BTCUSDT",
                "timeframe": "15m",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "candidate_acceptance_scope": "real_discovery_ledgers_no_pack_gate",
                "counts": {"completed_trials": 2, "interesting_candidates": 1, "blocked_candidates": 1, "filter_blockers": 0},
                "required_outputs": {
                    "interesting_candidates": str(interesting_path),
                    "blocked_candidates": str(blocked_path),
                    "filter_blockers": str(filter_path),
                },
            }
        ),
        encoding="utf-8",
    )

    analysis = build_research_analysis(cycle_dir=cycle_dir, discovery_dir=discovery_dir)

    assert analysis["research_only"] is True
    assert analysis["cycle"]["rankings"]["pack_eligible_count"] == 1
    assert analysis["cycle"]["rankings"]["positive_pure_roi_count"] == 1
    assert analysis["cycle"]["rankings"]["feature_set_performance"][0]["feature_set_id"] == "features_price_trend_vol"
    assert analysis["cycle"]["rankings"]["top_candidates_by_sortino"][0]["candidate_id"] == "candidate-a"
    assert analysis["discovery"]["counts"]["interesting_candidates"] == 1
    assert analysis["discovery"]["knn_setting_summary"][0]["interesting_trials"] == 1
    assert analysis["discovery"]["blocker_counts"][0] == {"value": "overlap_ratio_above_ceiling", "count": 1}


def test_write_analysis_artifacts_creates_json_and_markdown(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"

    result = write_research_analysis_artifacts(cycle_dir=None, discovery_dir=None, output_dir=output_dir)

    assert result.analysis_json_path.exists()
    assert result.markdown_path.exists()
    assert json.loads(result.analysis_json_path.read_text(encoding="utf-8"))["promotion_ready"] is False
    assert "research-only evidence review" in result.markdown_path.read_text(encoding="utf-8")

