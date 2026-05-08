from __future__ import annotations

import json
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
        _row("hmm-knn", "hmm_knn_local_analog_filter_v2", "features_perp_context_v2", "fixed_holding_window", 0.11, 9),
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


def test_perp_filter_ablation_matrix_passes_and_blocks_filter_defaults() -> None:
    spec = PerpFilterAblationMatrixSpec.from_path(Path("configs/discovery/perp_filter_ablation_matrix_v4.json"))

    result = build_perp_filter_ablation_matrix(_rankings(), spec=spec)
    matrix = result.matrix
    by_id = {row["comparison_id"]: row for row in matrix.to_dict("records")}

    assert by_id["no_perp_reference"]["decision"] == "baseline_reference"
    assert by_id["perp_feature_addition_vs_no_perp"]["decision"] == "passed"
    assert by_id["perp_feature_addition_vs_no_perp"]["filter_default_allowed"] is True
    assert by_id["hmm_knn_filter_vs_perp_strategy"]["decision"] == "failed"
    assert by_id["hmm_knn_filter_vs_perp_strategy"]["filter_default_allowed"] is False
    assert "treatment_did_not_beat_comparator" in by_id["hmm_knn_filter_vs_perp_strategy"]["failure_reasons"]
    assert result.manifest["default_guard"]["no_filter_default_without_winning_ablation"] is True
    assert result.manifest["filter_default_candidate_count"] >= result.manifest["filter_default_allowed_count"]
    assert result.manifest["research_only"] is True
    assert result.manifest["observe_only"] is True
    assert result.manifest["promotion_ready"] is False


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
