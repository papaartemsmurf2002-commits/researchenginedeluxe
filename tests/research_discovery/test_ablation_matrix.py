from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from tradingbotsuite.research_discovery.ablation_matrix import (
    PerpFilterAblationMatrixSpec,
    build_perp_filter_ablation_matrix,
    write_perp_filter_ablation_artifacts,
)
from tradingbotsuite.research_discovery.feature_sets import load_feature_column_set_manifest


def _rankings() -> pd.DataFrame:
    rows = [
        _row("no-perp", "trend_following_v1", "features_price_trend_vol", "fixed_holding_window", 0.10, 12),
        _row("perp-feature", "trend_following_v1", "features_perp_context_v2", "fixed_holding_window", 0.14, 11),
        _row("no-trade", "baseline_no_trade", "features_perp_context_v2", "fixed_holding_window", 0.00, 0),
        _row("perp-strategy", "perp_basis_convergence_v2", "features_perp_context_v2", "fixed_holding_window", 0.12, 10),
        _row("regime-knn", "hmm_knn_local_analog_filter_v2", "features_perp_context_v2", "fixed_holding_window", 0.11, 9),
        _row("perp-exit", "perp_basis_convergence_v2", "features_perp_context_v2", "funding_aware_exit_v1", 0.16, 10),
    ]
    return pd.DataFrame(rows)


def _row(
    candidate_id: str,
    strategy_id: str,
    feature_set_id: str,
    exit_policy_id: str,
    final_score: float,
    trade_count: int,
) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "strategy_id": strategy_id,
        "feature_set_id": feature_set_id,
        "holding_window": "24h",
        "exit_policy_id": exit_policy_id,
        "exit_policy_params_json": "{}",
        "final_score": final_score,
        "trade_count": trade_count,
        "feature_missingness_rate": 0.01,
    }


def _feature_combination_evidence() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "feature_column_set_id": "price_trend_vol",
                "final_score": 0.10,
                "trade_count": 12,
                "split_consistency": 0.70,
                "cost_stress_survival": 1.0,
            },
            {
                "feature_column_set_id": "compact_wt3d_base",
                "final_score": 0.09,
                "trade_count": 12,
                "split_consistency": 0.65,
                "cost_stress_survival": 1.0,
            },
            {
                "feature_column_set_id": "alternative_non_wt_price_state",
                "final_score": 0.12,
                "trade_count": 12,
                "split_consistency": 0.75,
                "cost_stress_survival": 1.0,
            },
        ]
    )


MATCH_COLUMNS = {
    "entry_family": "hmm_knn_local_analog_filter_v2",
    "feature_set_id": "features_perp_context_v2",
    "feature_column_set_id": "price_trend_vol",
    "label_horizon": "4h",
    "regime_mode": "none",
    "distance_metric": "euclidean",
    "k": 8,
    "min_neighbor_count": 2,
    "holding_window": "4h",
    "exit_policy_id": "fixed_holding_window",
    "exit_policy_params_json": "{}",
    "split_id": "wf-split-001",
    "cost_model_id": "cost-model-v1",
}


def _matched_row(
    candidate_id: str,
    *,
    filter_family: str,
    filter_enabled: bool,
    score: float,
    trade_count: int,
    filter_value: object = 0.50,
    provider_backed: bool = True,
    side_specific: bool = False,
    **overrides: object,
) -> dict[str, object]:
    row: dict[str, object] = {
        **MATCH_COLUMNS,
        "candidate_id": candidate_id,
        "strategy_id": "hmm_knn_local_analog_filter_v2",
        "filter_family": filter_family,
        "filter_enabled": filter_enabled,
        "final_score": score,
        "trade_count": trade_count,
        "feature_missingness_rate": 0.0,
        "hvp_realized_vol_percentile": filter_value,
        "hvp_realized_vol_percentile_provider_backed": provider_backed,
        "split_consistency": 0.8,
        "cost_stress_survival": 1.0,
        "side_specific": side_specific,
    }
    row.update(overrides)
    return row


def _matched_spec() -> PerpFilterAblationMatrixSpec:
    return PerpFilterAblationMatrixSpec.from_path(Path("configs/discovery/filter_ablation_matrix_v5.json"))


def test_perp_filter_ablation_matrix_passes_and_blocks_filter_defaults() -> None:
    spec = PerpFilterAblationMatrixSpec.from_path(Path("configs/discovery/perp_filter_ablation_matrix_v4.json"))

    result = build_perp_filter_ablation_matrix(_rankings(), spec=spec)
    matrix = result.matrix
    by_id = {row["comparison_id"]: row for row in matrix.to_dict("records")}

    assert by_id["no_perp_reference"]["decision"] == "baseline_reference"
    assert by_id["perp_feature_addition_vs_no_perp"]["decision"] == "passed"
    assert by_id["perp_feature_addition_vs_no_perp"]["filter_default_allowed"] is False
    assert by_id["hmm_knn_filter_vs_perp_strategy"]["decision"] == "failed"
    assert by_id["hmm_knn_filter_vs_perp_strategy"]["filter_default_allowed"] is False
    assert "treatment_did_not_beat_comparator" in by_id["hmm_knn_filter_vs_perp_strategy"]["failure_reasons"]
    assert result.manifest["default_guard"]["no_filter_default_without_winning_ablation"] is True
    assert result.manifest["filter_default_candidate_count"] >= result.manifest["filter_default_allowed_count"]
    assert result.manifest["filter_default_allowed_count"] == 0
    assert result.manifest["research_only"] is True
    assert result.manifest["observe_only"] is True
    assert result.manifest["promotion_ready"] is False


def test_filter_default_requires_exact_matched_no_filter_comparator() -> None:
    spec = _matched_spec()
    filtered = _matched_row("filtered", filter_family="hvp_realized_vol_percentile", filter_enabled=True, score=0.15, trade_count=8)
    unmatched = _matched_row(
        "unmatched-no-filter",
        filter_family="none",
        filter_enabled=False,
        score=0.10,
        trade_count=12,
        regime_mode="gmm_gate_only",
    )

    result = build_perp_filter_ablation_matrix(pd.DataFrame([filtered, unmatched]), spec=spec)
    row = result.matrix.loc[result.matrix["treatment_candidate_id"].eq("filtered")].iloc[0]

    assert row["decision"] == "not_testable"
    assert bool(row["filter_default_allowed"]) is False
    assert "matched_no_filter_comparator_missing" in row["failure_reasons"]

    matched = _matched_row("matched-no-filter", filter_family="none", filter_enabled=False, score=0.10, trade_count=12)
    passed = build_perp_filter_ablation_matrix(pd.DataFrame([filtered, matched]), spec=spec)
    passed_row = passed.matrix.loc[passed.matrix["comparison_id"].eq("matched_hvp_filter_vs_no_filter")].iloc[0]

    assert passed_row["decision"] == "edge_improving"
    assert bool(passed_row["filter_default_allowed"]) is True


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("entry_family", "other_entry"),
        ("feature_set_id", "features_price_trend_vol"),
        ("feature_column_set_id", "compact_wt3d_base"),
        ("label_horizon", "24h"),
        ("regime_mode", "gmm_gate_only"),
        ("distance_metric", "cosine"),
        ("k", 16),
        ("min_neighbor_count", 4),
        ("exit_policy_id", "triple_barrier_atr"),
        ("split_id", "wf-split-002"),
        ("cost_model_id", "cost-model-v2"),
    ],
)
def test_filter_default_match_keys_are_exhaustive(key: str, value: object) -> None:
    spec = _matched_spec()
    filtered = _matched_row("filtered", filter_family="hvp_realized_vol_percentile", filter_enabled=True, score=0.15, trade_count=8)
    unmatched = _matched_row(
        "unmatched-no-filter",
        filter_family="none",
        filter_enabled=False,
        score=0.10,
        trade_count=12,
        **{key: value},
    )

    result = build_perp_filter_ablation_matrix(pd.DataFrame([filtered, unmatched]), spec=spec)
    row = result.matrix.loc[result.matrix["comparison_id"].eq("matched_hvp_filter_vs_no_filter")].iloc[0]

    assert row["decision"] == "not_testable"
    assert bool(row["filter_default_allowed"]) is False


@pytest.mark.parametrize(
    ("column_updates", "reason"),
    [
        ({"hvp_realized_vol_percentile": float("nan")}, "finite_filter_column_not_testable:hvp_realized_vol_percentile"),
        ({"hvp_realized_vol_percentile": float("inf")}, "finite_filter_column_not_testable:hvp_realized_vol_percentile"),
        ({"hvp_realized_vol_percentile_provider_backed": False}, "filter_column_not_provider_backed:hvp_realized_vol_percentile"),
    ],
)
def test_missing_nonfinite_or_not_provider_backed_filter_columns_are_not_testable(
    column_updates: dict[str, object],
    reason: str,
) -> None:
    spec = _matched_spec()
    filtered = _matched_row(
        "filtered",
        filter_family="hvp_realized_vol_percentile",
        filter_enabled=True,
        score=0.15,
        trade_count=8,
        **column_updates,
    )
    comparator = _matched_row("no-filter", filter_family="none", filter_enabled=False, score=0.10, trade_count=12)

    result = build_perp_filter_ablation_matrix(pd.DataFrame([filtered, comparator]), spec=spec)
    row = result.matrix.loc[result.matrix["comparison_id"].eq("matched_hvp_filter_vs_no_filter")].iloc[0]

    assert row["decision"] == "not_testable"
    assert bool(row["filter_default_allowed"]) is False
    assert reason in row["failure_reasons"]


def test_missing_filter_column_is_not_testable() -> None:
    spec = _matched_spec()
    filtered = _matched_row("filtered", filter_family="hvp_realized_vol_percentile", filter_enabled=True, score=0.15, trade_count=8)
    comparator = _matched_row("no-filter", filter_family="none", filter_enabled=False, score=0.10, trade_count=12)
    del filtered["hvp_realized_vol_percentile"]
    del comparator["hvp_realized_vol_percentile"]

    result = build_perp_filter_ablation_matrix(pd.DataFrame([filtered, comparator]), spec=spec)
    row = result.matrix.loc[result.matrix["comparison_id"].eq("matched_hvp_filter_vs_no_filter")].iloc[0]

    assert row["decision"] == "not_testable"
    assert "finite_filter_column_missing:hvp_realized_vol_percentile" in row["failure_reasons"]


def test_selected_filter_row_must_have_finite_provider_backed_evidence() -> None:
    spec = _matched_spec()
    invalid_best = _matched_row(
        "invalid-best",
        filter_family="hvp_realized_vol_percentile",
        filter_enabled=True,
        score=0.20,
        trade_count=8,
        hvp_realized_vol_percentile_provider_backed=False,
    )
    valid_lower_rank = _matched_row(
        "valid-lower-rank",
        filter_family="hvp_realized_vol_percentile",
        filter_enabled=True,
        score=0.15,
        trade_count=8,
    )
    comparator = _matched_row("no-filter", filter_family="none", filter_enabled=False, score=0.10, trade_count=12)

    result = build_perp_filter_ablation_matrix(pd.DataFrame([valid_lower_rank, invalid_best, comparator]), spec=spec)
    row = result.matrix.loc[result.matrix["comparison_id"].eq("matched_hvp_filter_vs_no_filter")].iloc[0]

    assert row["treatment_candidate_id"] == "invalid-best"
    assert row["decision"] == "not_testable"
    assert bool(row["filter_default_allowed"]) is False
    assert "filter_column_not_provider_backed:hvp_realized_vol_percentile" in row["failure_reasons"]


def test_string_nan_split_consistency_blocks_filter_default() -> None:
    full_spec = _matched_spec()
    spec = replace(
        full_spec,
        comparisons=(replace(full_spec.comparisons[0], min_split_consistency=0.50),),
    )
    filtered = _matched_row(
        "filtered",
        filter_family="hvp_realized_vol_percentile",
        filter_enabled=True,
        score=0.15,
        trade_count=8,
        split_consistency="nan",
    )
    comparator = _matched_row("no-filter", filter_family="none", filter_enabled=False, score=0.10, trade_count=12)

    result = build_perp_filter_ablation_matrix(pd.DataFrame([filtered, comparator]), spec=spec)
    row = result.matrix.loc[result.matrix["comparison_id"].eq("matched_hvp_filter_vs_no_filter")].iloc[0]

    assert row["decision"] == "unstable"
    assert bool(row["filter_default_allowed"]) is False
    assert "filter_split_consistency_below_floor" in row["failure_reasons"]


def test_liquidation_filter_requires_provider_backed_evidence() -> None:
    spec = _matched_spec()
    filtered = _matched_row(
        "liquidation-filter",
        filter_family="liquidation",
        filter_enabled=True,
        score=0.15,
        trade_count=8,
        liquidation_absorption_score=0.5,
        liquidation_absorption_score_provider_backed=False,
    )
    comparator = _matched_row("no-filter", filter_family="none", filter_enabled=False, score=0.10, trade_count=12)

    result = build_perp_filter_ablation_matrix(pd.DataFrame([filtered, comparator]), spec=spec)
    row = result.matrix.loc[result.matrix["comparison_id"].eq("matched_liquidation_filter_vs_no_filter")].iloc[0]

    assert row["decision"] == "not_testable"
    assert bool(row["filter_default_allowed"]) is False
    assert "filter_column_not_provider_backed:liquidation_absorption_score" in row["failure_reasons"]


@pytest.mark.parametrize(
    ("filtered", "expected_decision", "expected_reason"),
    [
        (
            _matched_row("sample-reduced", filter_family="hvp_realized_vol_percentile", filter_enabled=True, score=0.10, trade_count=6),
            "sample_reducing_only",
            "filter_reduced_sample_without_edge_improvement",
        ),
        (
            _matched_row("harmful", filter_family="hvp_realized_vol_percentile", filter_enabled=True, score=0.08, trade_count=12),
            "harmful",
            "filter_harmed_edge_vs_matched_comparator",
        ),
        (
            _matched_row(
                "side-specific",
                filter_family="hvp_realized_vol_percentile",
                filter_enabled=True,
                score=0.15,
                trade_count=8,
                side_specific=True,
            ),
            "side_specific",
            "",
        ),
    ],
)
def test_sample_reducing_harmful_and_side_specific_labels_are_deterministic(
    filtered: dict[str, object],
    expected_decision: str,
    expected_reason: str,
) -> None:
    spec = _matched_spec()
    comparator = _matched_row("no-filter", filter_family="none", filter_enabled=False, score=0.10, trade_count=12)
    first = build_perp_filter_ablation_matrix(pd.DataFrame([filtered, comparator]), spec=spec)
    second = build_perp_filter_ablation_matrix(pd.DataFrame([comparator, filtered]), spec=spec)
    first_row = first.matrix.loc[first.matrix["comparison_id"].eq("matched_hvp_filter_vs_no_filter")].iloc[0]
    second_row = second.matrix.loc[second.matrix["comparison_id"].eq("matched_hvp_filter_vs_no_filter")].iloc[0]

    assert first_row["decision"] == expected_decision
    assert second_row["decision"] == expected_decision
    assert bool(first_row["filter_default_allowed"]) is False
    assert bool(second_row["filter_default_allowed"]) is False
    if expected_reason:
        assert expected_reason in first_row["failure_reasons"]


def test_only_edge_improving_matched_filters_can_default() -> None:
    spec = _matched_spec()
    filtered = _matched_row("filtered", filter_family="hvp_realized_vol_percentile", filter_enabled=True, score=0.15, trade_count=8)
    comparator = _matched_row("no-filter", filter_family="none", filter_enabled=False, score=0.10, trade_count=12)

    result = build_perp_filter_ablation_matrix(pd.DataFrame([filtered, comparator]), spec=spec)
    row = result.matrix.loc[result.matrix["comparison_id"].eq("matched_hvp_filter_vs_no_filter")].iloc[0]

    assert row["decision"] == "edge_improving"
    assert row["score_delta"] == pytest.approx(0.05)
    assert bool(row["finite_filter_columns_present"]) is True
    assert bool(row["filter_default_allowed"]) is True


def test_perp_filter_ablation_matrix_keeps_missing_evidence_pending() -> None:
    spec = PerpFilterAblationMatrixSpec.from_payload(
        {
            "comparisons": [
                {
                    "comparison_id": "missing-perp-filter",
                    "axis": "perp_filter",
                    "treatment_selector": {"strategy_id": "hmm_knn_local_analog_filter_v2"},
                    "comparator_selector": {"strategy_id": "perp_basis_convergence_v2"},
                    "filter_default_candidate": True,
                }
            ]
        }
    )

    result = build_perp_filter_ablation_matrix(_rankings().query("strategy_id != 'hmm_knn_local_analog_filter_v2'"), spec=spec)
    row = result.matrix.iloc[0]

    assert row["decision"] == "pending_evidence"
    assert bool(row["filter_default_allowed"]) is False
    assert "treatment_evidence_missing" in row["failure_reasons"]


def test_feature_combination_stability_requires_non_wt_comparators() -> None:
    spec = PerpFilterAblationMatrixSpec.from_path(Path("configs/discovery/perp_filter_ablation_matrix_v4.json"))
    manifest = load_feature_column_set_manifest(Path("configs/discovery/feature_column_sets_v4.json"))

    result = build_perp_filter_ablation_matrix(
        _rankings(),
        spec=spec,
        feature_column_set_manifest=manifest,
        feature_combination_evidence=_feature_combination_evidence(),
    )
    stability = {row["feature_column_set_id"]: row for row in result.feature_combination_stability.to_dict("records")}

    assert stability["price_trend_vol"]["decision"] == "baseline_reference"
    assert stability["compact_wt3d_base"]["contains_wt3d"] is True
    assert stability["compact_wt3d_base"]["decision"] == "failed"
    assert "feature_combination_did_not_beat_comparator" in stability["compact_wt3d_base"]["failure_reasons"]
    assert stability["alternative_non_wt_price_state"]["decision"] == "passed"
    assert result.manifest["feature_combination_guard"]["stability_diagnostics_do_not_replace_region_of_stability_gate"] is True


def test_perp_filter_ablation_artifacts_are_research_only(tmp_path: Path) -> None:
    spec = PerpFilterAblationMatrixSpec.from_path(Path("configs/discovery/perp_filter_ablation_matrix_v4.json"))
    result = build_perp_filter_ablation_matrix(_rankings(), spec=spec)

    artifacts = write_perp_filter_ablation_artifacts(tmp_path / "ablation", result)
    manifest = json.loads(artifacts.manifest_path.read_text(encoding="utf-8"))
    matrix = pd.read_parquet(artifacts.matrix_path)
    stability = pd.read_parquet(artifacts.feature_combination_stability_path)

    assert manifest["ablation_manifest_version"] == "discovery-perp-filter-ablation-manifest-v1"
    assert manifest["artifact_version"] == "discovery-perp-filter-ablation-artifacts-v1"
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["order_placement_used"] is False
    assert manifest["required_outputs"]["perp_filter_ablation_matrix"] == str(artifacts.matrix_path)
    assert not matrix.empty
    assert list(stability.columns)


def test_perp_filter_ablation_spec_rejects_unknown_axis() -> None:
    with pytest.raises(ValueError, match="unsupported ablation axis"):
        PerpFilterAblationMatrixSpec.from_payload(
            {
                "comparisons": [
                    {
                        "comparison_id": "bad",
                        "axis": "live_filter",
                        "treatment_selector": {"strategy_id": "hmm_knn_local_analog_filter_v2"},
                    }
                ]
            }
        )
