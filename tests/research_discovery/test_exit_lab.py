from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from tradingbotsuite.research_discovery.exit_lab import (
    DiscoveryExitLabSpec,
    build_discovery_exit_lab,
    discovery_entry_lead_evidence_sha256,
    write_discovery_exit_lab_artifacts,
)


def _rankings(*, baseline_trade_count: int = 12) -> pd.DataFrame:
    rows = [
        _row("fixed", "fixed_holding_window", 0.10, baseline_trade_count),
        _row("barrier", "triple_barrier_atr", 0.14, 10),
        _row("basis", "basis_normalization_exit_v1", 0.13, 10),
        _row("gmm", "regime_flip_exit", 0.125, 10),
        _row("funding", "funding_aware_exit_v1", 0.09, 10),
        _row("oi", "oi_contraction_exit_v1", 0.12, 10),
        _row("trailing", "trailing_atr_after_profit", 0.15, 9),
    ]
    return pd.DataFrame(rows)


def _row(candidate_id: str, exit_policy_id: str, final_score: float, trade_count: int) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "strategy_id": "perp_basis_convergence_v2",
        "feature_set_id": "features_perp_context_v2",
        "holding_window": "24h",
        "parameters_json": "{}",
        "exit_policy_id": exit_policy_id,
        "exit_policy_params_json": "{}",
        "final_score": final_score,
        "trade_count": trade_count,
        "cost_stress_status": "passed",
    }


def _lead_record() -> dict[str, object]:
    return {
        "run_id": "bridge-run",
        "trial_id": "trial-000001",
        "candidate_id": "bridge-run-candidate-000001",
        "candidate_family": "regime_knn_entry_discovery",
        "score": 0.42,
        "discovery_screen_score_v2": 0.42,
        "final_score": 0.42,
        "feature_column_set_id": "price_trend_vol",
        "regime_mode": "none",
        "regime_detector_type": "none",
        "label_horizon": "4h",
        "distance_metric": "euclidean",
        "k": 8,
        "min_neighbor_count": 2,
        "independent_event_count": 12,
        "event_signal_rate": 0.12,
        "record_sha256": "lead-record-hash",
    }


def _candidate_tied_rankings(*, treatment_score: float = 0.14) -> pd.DataFrame:
    lead_hash = discovery_entry_lead_evidence_sha256(_lead_record())
    rows = [
        _row("fixed", "fixed_holding_window", 0.10, 12),
        _row("barrier", "triple_barrier_atr", treatment_score, 10),
    ]
    for row in rows:
        row["entry_candidate_id"] = "bridge-run-candidate-000001"
        row["research_candidate_id"] = "candidate-1"
        row["entry_lead_evidence_sha256"] = lead_hash
        row["cost_stress_status"] = "passed"
    return pd.DataFrame(rows)


def test_exit_lab_compares_exit_families_after_trade_density_gate() -> None:
    spec = DiscoveryExitLabSpec.from_path(Path("configs/discovery/discovery_exit_lab_v4.json"))

    result = build_discovery_exit_lab(_rankings(), spec=spec)
    rows = {row["comparison_id"]: row for row in result.matrix.to_dict("records")}

    assert rows["fixed_holding_reference"]["decision"] == "passed"
    assert rows["barrier_exit_vs_fixed_holding"]["decision"] == "passed"
    assert rows["barrier_exit_vs_fixed_holding"]["exit_lab_winner"] is True
    assert rows["basis_premium_normalization_exit_vs_fixed_holding"]["decision"] == "passed"
    assert rows["gmm_transition_exit_vs_fixed_holding"]["decision"] == "passed"
    assert rows["gmm_transition_exit_vs_fixed_holding"]["treatment_exit_policy_id"] == "regime_flip_exit"
    assert rows["funding_oi_exit_vs_fixed_holding"]["decision"] == "passed"
    assert rows["funding_oi_exit_vs_fixed_holding"]["treatment_exit_policy_id"] == "oi_contraction_exit_v1"
    assert rows["knn_remaining_edge_exit_vs_fixed_holding"]["decision"] == "pending_evidence"
    assert rows["knn_dynamic_barrier_exit_vs_fixed_holding"]["decision"] == "pending_evidence"
    assert rows["trailing_risk_exit_vs_fixed_holding"]["decision"] == "passed"
    assert rows["true_hmm_transition_exit_vs_fixed_holding"]["decision"] == "deferred_evidence"
    assert rows["liquidity_adverse_selection_exit_vs_fixed_holding"]["decision"] == "deferred_evidence"
    assert result.manifest["exit_family_labels"]["gmm_transition"] == "current GMM regime transition"
    assert result.manifest["deferred_exit_families"]["true_hmm_transition"] == "true_hmm_backend_deferred"
    assert result.manifest["comparison_grouping"][
        "side_split_regime_holding_cost_feature_knn_setup_matched_where_present"
    ] is True
    assert result.manifest["trade_density_guard"]["entry_candidates_below_floor_are_not_compared"] is True
    assert result.manifest["default_guard"]["exit_winner_does_not_change_default_policy"] is True
    assert result.manifest["research_only"] is True
    assert result.manifest["observe_only"] is True
    assert result.manifest["promotion_ready"] is False


def test_exit_lab_writes_candidate_tied_gate_evidence(tmp_path: Path) -> None:
    spec = DiscoveryExitLabSpec.from_path(Path("configs/discovery/discovery_exit_lab_v4.json"))

    result = build_discovery_exit_lab(_candidate_tied_rankings(), spec=spec)
    gate = result.candidate_gates.iloc[0]
    artifacts = write_discovery_exit_lab_artifacts(tmp_path / "exit_lab", result)
    manifest = json.loads(artifacts.manifest_path.read_text(encoding="utf-8"))
    gates = pd.read_parquet(artifacts.candidate_gates_path)

    assert gate["entry_candidate_id"] == "bridge-run-candidate-000001"
    assert gate["candidate_id"] == "candidate-1"
    assert gate["exit_lab_status"] == "complete"
    assert gate["exit_lab_gate_status"] == "passed"
    assert gate["exit_lab_best_family"] == "barrier"
    assert gate["fixed_holding_score_delta"] == pytest.approx(0.04)
    assert gate["cost_stress_status"] == "passed"
    assert gate["entry_lead_evidence_sha256"] == discovery_entry_lead_evidence_sha256(_lead_record())
    assert manifest["required_outputs"]["discovery_exit_lab_candidate_gates"] == str(artifacts.candidate_gates_path)
    assert manifest["candidate_gate_row_count"] == 1
    assert not gates.empty


def test_exit_lab_equal_or_worse_treatment_is_not_candidate_ready() -> None:
    spec = DiscoveryExitLabSpec.from_path(Path("configs/discovery/discovery_exit_lab_v4.json"))

    result = build_discovery_exit_lab(_candidate_tied_rankings(treatment_score=0.10), spec=spec)
    gate = result.candidate_gates.iloc[0]
    barrier = result.matrix.loc[result.matrix["comparison_id"].eq("barrier_exit_vs_fixed_holding")].iloc[0]

    assert barrier["decision"] == "failed"
    assert gate["exit_lab_gate_status"] == "blocked"
    assert "exit_lab_no_improving_exit_over_fixed_holding" in gate["exit_lab_reasons"]
    assert gate["no_improvement_reason"] == "no_exit_improved_executable_expectancy"


@pytest.mark.parametrize(
    ("cost_status", "expected_decision", "expected_reason"),
    [
        ("failed", "failed", "cost_stress_status_not_passing:failed"),
        (pd.NA, "pending_evidence", "cost_stress_evidence_missing"),
    ],
)
def test_exit_lab_blocks_missing_or_failed_cost_stress_evidence(
    cost_status: object,
    expected_decision: str,
    expected_reason: str,
) -> None:
    spec = DiscoveryExitLabSpec.from_path(Path("configs/discovery/discovery_exit_lab_v4.json"))
    rankings = _candidate_tied_rankings()
    rankings["cost_stress_status"] = cost_status

    result = build_discovery_exit_lab(rankings, spec=spec)
    gate = result.candidate_gates.iloc[0]
    barrier = result.matrix.loc[result.matrix["comparison_id"].eq("barrier_exit_vs_fixed_holding")].iloc[0]

    assert barrier["decision"] == expected_decision
    assert expected_reason in barrier["failure_reasons"]
    assert gate["exit_lab_gate_status"] == "blocked"


def test_exit_lab_string_nan_treatment_score_is_not_candidate_ready() -> None:
    spec = DiscoveryExitLabSpec.from_path(Path("configs/discovery/discovery_exit_lab_v4.json"))

    result = build_discovery_exit_lab(_candidate_tied_rankings(treatment_score="nan"), spec=spec)
    gate = result.candidate_gates.iloc[0]
    barrier = result.matrix.loc[result.matrix["comparison_id"].eq("barrier_exit_vs_fixed_holding")].iloc[0]

    assert barrier["decision"] == "failed"
    assert bool(barrier["exit_lab_winner"]) is False
    assert gate["exit_lab_gate_status"] == "blocked"
    assert "exit_lab_no_improving_exit_over_fixed_holding" in gate["exit_lab_reasons"]


def test_exit_lab_fixed_holding_only_is_not_candidate_ready() -> None:
    full_spec = DiscoveryExitLabSpec.from_path(Path("configs/discovery/discovery_exit_lab_v4.json"))
    spec = DiscoveryExitLabSpec(
        lab_id=full_spec.lab_id,
        entry_group_columns=full_spec.entry_group_columns,
        comparisons=(full_spec.comparisons[0],),
    )

    result = build_discovery_exit_lab(_candidate_tied_rankings(), spec=spec)
    gate = result.candidate_gates.iloc[0]

    assert gate["exit_lab_status"] == "complete"
    assert gate["exit_lab_gate_status"] == "blocked"
    assert gate["exit_lab_best_family"] == "fixed_holding"
    assert "exit_lab_fixed_holding_only" in gate["exit_lab_reasons"]


def test_exit_lab_grouping_matches_side_split_regime_cost_feature_and_knn_setup() -> None:
    full_spec = DiscoveryExitLabSpec.from_path(Path("configs/discovery/discovery_exit_lab_v4.json"))
    spec = DiscoveryExitLabSpec(
        lab_id=full_spec.lab_id,
        entry_group_columns=full_spec.entry_group_columns,
        comparisons=full_spec.comparisons[:2],
    )

    def grouped(row: dict[str, object], *, cost_stress_id: str) -> dict[str, object]:
        row.update(
            {
                "symbol": "BTCUSDT",
                "timeframe": "15m",
                "side": "long",
                "split_id": "wf-split-01",
                "validation_split_id": "validation-01",
                "feature_column_set_id": "price_perp_aggflow",
                "regime_mode": "gmm_same_regime_neighbors",
                "regime_detector_type": "gmm",
                "cost_model_id": "research_costs_v2",
                "cost_stress_id": cost_stress_id,
                "cost_stress_status": "passed",
                "label_horizon": "4h",
                "distance_metric": "lorentzian",
                "k": 8,
                "min_neighbor_count": 2,
            }
        )
        return row

    rows = [
        grouped(_row("fixed-normal", "fixed_holding_window", 0.10, 12), cost_stress_id="normal"),
        grouped(_row("barrier-normal", "triple_barrier_atr", 0.14, 10), cost_stress_id="normal"),
        grouped(_row("barrier-stress", "triple_barrier_atr", 0.30, 10), cost_stress_id="fee_2x"),
    ]

    result = build_discovery_exit_lab(pd.DataFrame(rows), spec=spec)
    barrier_rows = result.matrix.loc[result.matrix["comparison_id"].eq("barrier_exit_vs_fixed_holding")]
    normal = barrier_rows.loc[barrier_rows["entry_cost_stress_id"].eq("normal")].iloc[0]
    stress = barrier_rows.loc[barrier_rows["entry_cost_stress_id"].eq("fee_2x")].iloc[0]

    assert normal["decision"] == "passed"
    assert normal["baseline_candidate_id"] == "fixed-normal"
    assert normal["treatment_candidate_id"] == "barrier-normal"
    assert normal["entry_side"] == "long"
    assert normal["entry_split_id"] == "wf-split-01"
    assert normal["entry_regime_mode"] == "gmm_same_regime_neighbors"
    assert normal["entry_holding_window"] == "24h"
    assert normal["entry_feature_column_set_id"] == "price_perp_aggflow"
    assert normal["entry_distance_metric"] == "lorentzian"
    assert int(normal["entry_k"]) == 8
    assert int(normal["entry_min_neighbor_count"]) == 2
    assert stress["decision"] == "pending_evidence"
    assert stress["baseline_candidate_id"] == ""
    assert "baseline_exit_evidence_missing" in stress["failure_reasons"]


def test_exit_lab_skips_candidates_below_entry_trade_density_floor() -> None:
    spec = DiscoveryExitLabSpec.from_path(Path("configs/discovery/discovery_exit_lab_v4.json"))

    result = build_discovery_exit_lab(_rankings(baseline_trade_count=3), spec=spec)

    assert set(result.matrix["decision"]) == {"skipped_low_trade_density"}
    assert not result.matrix["exit_lab_winner"].any()
    assert result.manifest["decision_counts"]["skipped_low_trade_density"] == len(result.matrix)


def test_exit_lab_keeps_missing_knn_exit_evidence_pending() -> None:
    spec = DiscoveryExitLabSpec.from_path(Path("configs/discovery/discovery_exit_lab_v4.json"))

    result = build_discovery_exit_lab(_rankings(), spec=spec)
    row = result.matrix.loc[result.matrix["comparison_id"].eq("knn_remaining_edge_exit_vs_fixed_holding")].iloc[0]

    assert row["decision"] == "pending_evidence"
    assert bool(row["exit_lab_winner"]) is False
    assert "treatment_exit_evidence_missing" in row["failure_reasons"]


def test_exit_lab_defers_true_hmm_and_depth_even_when_treatment_rows_exist() -> None:
    full_spec = DiscoveryExitLabSpec.from_path(Path("configs/discovery/discovery_exit_lab_v4.json"))
    comparisons = tuple(
        comparison
        for comparison in full_spec.comparisons
        if comparison.comparison_id
        in {
            "fixed_holding_reference",
            "true_hmm_transition_exit_vs_fixed_holding",
            "liquidity_adverse_selection_exit_vs_fixed_holding",
        }
    )
    spec = DiscoveryExitLabSpec(
        lab_id=full_spec.lab_id,
        entry_group_columns=full_spec.entry_group_columns,
        comparisons=comparisons,
    )
    rows = [
        _row("fixed", "fixed_holding_window", 0.10, 12),
        _row("true-hmm", "true_hmm_transition_exit_v1", 0.50, 10),
        _row("depth", "adverse_selection_exit", 0.40, 10),
    ]

    result = build_discovery_exit_lab(pd.DataFrame(rows), spec=spec)
    matrix = {row["comparison_id"]: row for row in result.matrix.to_dict("records")}
    gate = result.candidate_gates.iloc[0]

    assert matrix["true_hmm_transition_exit_vs_fixed_holding"]["decision"] == "deferred_evidence"
    assert matrix["true_hmm_transition_exit_vs_fixed_holding"]["exit_lab_status"] == "deferred"
    assert matrix["true_hmm_transition_exit_vs_fixed_holding"]["deferred_reason"] == "true_hmm_backend_deferred"
    assert matrix["liquidity_adverse_selection_exit_vs_fixed_holding"]["decision"] == "deferred_evidence"
    assert matrix["liquidity_adverse_selection_exit_vs_fixed_holding"]["deferred_reason"] == "durable_depth_l2_evidence_deferred"
    assert not matrix["true_hmm_transition_exit_vs_fixed_holding"]["exit_lab_winner"]
    assert not matrix["liquidity_adverse_selection_exit_vs_fixed_holding"]["exit_lab_winner"]
    assert gate["exit_lab_gate_status"] == "blocked"
    assert "exit_lab_deferred_evidence" in gate["exit_lab_reasons"]
    assert bool(gate["research_only"]) is True
    assert bool(gate["observe_only"]) is True
    assert bool(gate["promotion_ready"]) is False


def test_exit_lab_family_summary_counts_winners_and_pending_rows() -> None:
    spec = DiscoveryExitLabSpec.from_path(Path("configs/discovery/discovery_exit_lab_v4.json"))

    result = build_discovery_exit_lab(_rankings(), spec=spec)
    summary = {row["exit_family"]: row for row in result.family_summary.to_dict("records")}

    assert summary["barrier"]["passed_count"] == 1
    assert summary["knn_remaining_edge"]["pending_count"] == 1
    assert summary["true_hmm_transition"]["deferred_count"] == 1
    assert summary["funding_oi_supported"]["winner_candidate_ids"] == ["oi"]
    assert summary["fixed_holding"]["research_only"] is True


def test_exit_lab_artifacts_are_research_only(tmp_path: Path) -> None:
    spec = DiscoveryExitLabSpec.from_path(Path("configs/discovery/discovery_exit_lab_v4.json"))
    result = build_discovery_exit_lab(_rankings(), spec=spec)

    artifacts = write_discovery_exit_lab_artifacts(tmp_path / "exit_lab", result)
    manifest = json.loads(artifacts.manifest_path.read_text(encoding="utf-8"))
    matrix = pd.read_parquet(artifacts.matrix_path)
    summary = pd.read_parquet(artifacts.family_summary_path)

    assert manifest["exit_lab_manifest_version"] == "discovery-exit-lab-manifest-v1"
    assert manifest["artifact_version"] == "discovery-exit-lab-artifacts-v1"
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["order_placement_used"] is False
    assert manifest["required_outputs"]["discovery_exit_lab_matrix"] == str(artifacts.matrix_path)
    assert manifest["required_outputs"]["discovery_exit_lab_candidate_gates"] == str(artifacts.candidate_gates_path)
    assert not matrix.empty
    assert not summary.empty


def test_exit_lab_spec_rejects_unknown_exit_family() -> None:
    with pytest.raises(ValueError, match="unsupported exit lab family"):
        DiscoveryExitLabSpec.from_payload(
            {
                "comparisons": [
                    {
                        "comparison_id": "bad-family",
                        "exit_family": "live_sizing",
                        "treatment_selector": {"exit_policy_id": "fixed_holding_window"},
                    }
                ]
            }
        )

