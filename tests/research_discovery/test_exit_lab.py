from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from tradingbotsuite.research_discovery.exit_lab import (
    DiscoveryExitLabSpec,
    build_discovery_exit_lab,
    write_discovery_exit_lab_artifacts,
)


def _rankings(*, baseline_trade_count: int = 12) -> pd.DataFrame:
    rows = [
        _row("fixed", "fixed_holding_window", 0.10, baseline_trade_count),
        _row("barrier", "triple_barrier_atr", 0.14, 10),
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
    }


def test_exit_lab_compares_exit_families_after_trade_density_gate() -> None:
    spec = DiscoveryExitLabSpec.from_path(Path("configs/discovery/discovery_exit_lab_v4.json"))

    result = build_discovery_exit_lab(_rankings(), spec=spec)
    rows = {row["comparison_id"]: row for row in result.matrix.to_dict("records")}

    assert rows["fixed_holding_reference"]["decision"] == "passed"
    assert rows["barrier_exit_vs_fixed_holding"]["decision"] == "passed"
    assert rows["barrier_exit_vs_fixed_holding"]["exit_lab_winner"] is True
    assert rows["funding_oi_exit_vs_fixed_holding"]["decision"] == "passed"
    assert rows["funding_oi_exit_vs_fixed_holding"]["treatment_exit_policy_id"] == "oi_contraction_exit_v1"
    assert rows["trailing_risk_exit_vs_fixed_holding"]["decision"] == "passed"
    assert result.manifest["trade_density_guard"]["entry_candidates_below_floor_are_not_compared"] is True
    assert result.manifest["default_guard"]["exit_winner_does_not_change_default_policy"] is True
    assert result.manifest["research_only"] is True
    assert result.manifest["observe_only"] is True
    assert result.manifest["promotion_ready"] is False


def test_exit_lab_skips_candidates_below_entry_trade_density_floor() -> None:
    spec = DiscoveryExitLabSpec.from_path(Path("configs/discovery/discovery_exit_lab_v4.json"))

    result = build_discovery_exit_lab(_rankings(baseline_trade_count=3), spec=spec)

    assert set(result.matrix["decision"]) == {"skipped_low_trade_density"}
    assert not result.matrix["exit_lab_winner"].any()
    assert result.manifest["decision_counts"]["skipped_low_trade_density"] == len(result.matrix)


def test_exit_lab_keeps_missing_hmm_knn_exit_evidence_pending() -> None:
    spec = DiscoveryExitLabSpec.from_path(Path("configs/discovery/discovery_exit_lab_v4.json"))

    result = build_discovery_exit_lab(_rankings(), spec=spec)
    row = result.matrix.loc[result.matrix["comparison_id"].eq("hmm_knn_exit_vs_fixed_holding")].iloc[0]

    assert row["decision"] == "pending_evidence"
    assert bool(row["exit_lab_winner"]) is False
    assert "treatment_exit_evidence_missing" in row["failure_reasons"]


def test_exit_lab_family_summary_counts_winners_and_pending_rows() -> None:
    spec = DiscoveryExitLabSpec.from_path(Path("configs/discovery/discovery_exit_lab_v4.json"))

    result = build_discovery_exit_lab(_rankings(), spec=spec)
    summary = {row["exit_family"]: row for row in result.family_summary.to_dict("records")}

    assert summary["barrier"]["passed_count"] == 1
    assert summary["hmm_knn"]["pending_count"] == 1
    assert summary["funding_oi"]["winner_candidate_ids"] == ["oi"]
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

