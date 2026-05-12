from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from tradingbotsuite.research_discovery.validation_floors import (
    DiscoveryValidationFloorSpec,
    blocker_registry_payload,
    build_discovery_validation_floor_report,
    build_discovery_validation_floor_report_from_manifest,
    registered_blocker_codes,
    write_discovery_validation_floor_artifacts,
)


def _candidate(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "candidate_id": "candidate-1",
        "record_sha256": "record-1",
        "candidate_family": "hmm_knn_local_analog_filter_v2",
        "feature_column_set_id": "features_discovery_screen_v1",
        "parameters_json": "{}",
        "exit_policy_id": "triple_barrier_atr",
        "regime_mode": "none",
        "distance_metric": "euclidean",
        "k": 8,
        "validation_mode": "purged_embargoed_walk_forward",
        "discovery_screen_score_v2": 0.20,
        "independent_event_count": 260,
        "overlap_ratio": 0.10,
        "split_pass_ratio": 0.80,
        "side_concentration": 0.55,
        "long_independent_event_count": 130,
        "short_independent_event_count": 130,
        "cost_stress_survival": 1.0,
        "stability_neighborhood_size": 4,
        "effective_trial_count": 120,
        "baseline_comparator_coverage_status": "complete",
        "expectancy_vs_no_trade": 0.01,
        "directional_comparator_status": "complete",
        "exit_lab_status": "complete",
        "filter_ablation_status": "edge_improving",
        "feature_ablation_status": "passed",
    }
    row.update(overrides)
    return row


def test_validation_floor_report_marks_candidate_ready_and_writes_registry(tmp_path: Path) -> None:
    spec = DiscoveryValidationFloorSpec(declared_search_space=100)

    result = build_discovery_validation_floor_report(pd.DataFrame([_candidate()]), spec=spec)
    artifact = write_discovery_validation_floor_artifacts(tmp_path / "validation-floors", result)
    manifest = json.loads(artifact.manifest_path.read_text(encoding="utf-8"))
    gates = pd.read_parquet(artifact.candidate_gates_path)

    assert manifest["validation_floors_manifest_version"] == "discovery-validation-floors-manifest-v1"
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["order_placement_used"] is False
    assert manifest["summary"]["candidate_ready_count"] == 1
    assert manifest["experiment_budget_ledger"]["sampled_fraction"] == 0.01
    assert manifest["blocker_registry"]["blocker_registry_version"] == "discovery-validation-blocker-registry-v1"
    assert gates.loc[0, "validation_floor_status"] == "passed"
    assert gates.loc[0, "research_maturity"] == "candidate-ready"
    assert gates.loc[0, "validation_floor_reasons"] == ""


def test_validation_floor_report_distinguishes_screen_worthy_from_candidate_ready() -> None:
    row = _candidate(
        independent_event_count=130,
        overlap_ratio=0.30,
        split_pass_ratio=0.65,
        cost_stress_survival=0.90,
        stability_neighborhood_size=2,
        exit_lab_status="",
        filter_ablation_status="",
        feature_ablation_status="",
    )

    result = build_discovery_validation_floor_report(pd.DataFrame([row]))
    gate = result.candidate_gates.iloc[0]

    assert gate["validation_floor_status"] == "blocked"
    assert gate["research_maturity"] == "screen-worthy"
    assert gate["screen_floor_reasons"] == ""
    assert "independent_event_count_below_floor" in gate["candidate_ready_floor_reasons"]
    assert "exit_lab_missing" in gate["candidate_ready_floor_reasons"]
    assert "filter_ablation_missing" in gate["candidate_ready_floor_reasons"]
    assert "feature_ablation_missing" in gate["candidate_ready_floor_reasons"]


def test_validation_floor_report_rejects_string_nan_numeric_evidence() -> None:
    result = build_discovery_validation_floor_report(
        pd.DataFrame(
            [
                _candidate(
                    independent_event_count="nan",
                    overlap_ratio="nan",
                    split_pass_ratio="nan",
                    side_concentration="nan",
                    long_independent_event_count="nan",
                    short_independent_event_count="nan",
                    cost_stress_survival="nan",
                    stability_neighborhood_size="nan",
                )
            ]
        )
    )
    reasons = result.candidate_gates.loc[0, "validation_floor_reasons"]

    assert result.candidate_gates.loc[0, "research_maturity"] == "diagnostic"
    assert "independent_event_accounting_missing" in reasons
    assert "overlap_ratio_required" in reasons
    assert "split_pass_ratio_required" in reasons
    assert "side_concentration_required" in reasons
    assert "cost_stress_survival_below_floor" in reasons
    assert "stability_neighborhood_size_below_floor" in reasons


def test_validation_floor_report_emits_standard_blockers_for_failure_modes() -> None:
    row = _candidate(
        latest_window_only=True,
        regime_smoothed_state_used_in_validation=True,
        knn_future_or_overlapping_neighbor=True,
        liquidation_zero_filled=True,
        depth_feature_claimed=True,
        funding_feature_future_leakage=True,
        funding_only_crowding_overfit=True,
        cross_symbol_future_alignment=True,
    )

    result = build_discovery_validation_floor_report(pd.DataFrame([row]))
    reasons = result.candidate_gates.loc[0, "validation_floor_reasons"]

    for code in (
        "latest_window_only_diagnostic",
        "regime_smoothed_state_used_in_validation",
        "knn_future_or_overlapping_neighbor",
        "liquidation_false_zero_window",
        "depth_sequence_integrity_missing",
        "funding_feature_future_leakage",
        "funding_only_crowding_overfit",
        "cross_symbol_future_alignment",
    ):
        assert code in reasons


def test_validation_floor_report_requires_no_regime_baseline_when_regime_is_claimed() -> None:
    result = build_discovery_validation_floor_report(
        pd.DataFrame([_candidate(regime_mode="gmm_same_regime_neighbors", no_regime_baseline_status="")])
    )
    gate = result.candidate_gates.iloc[0]

    assert gate["research_maturity"] == "screen-worthy"
    assert "no_regime_baseline_missing" in gate["validation_floor_reasons"]


def test_validation_floor_report_rejects_blocked_exit_lab_gate_status() -> None:
    result = build_discovery_validation_floor_report(
        pd.DataFrame([_candidate(exit_lab_status="complete", exit_lab_gate_status="blocked")])
    )
    gate = result.candidate_gates.iloc[0]

    assert gate["research_maturity"] == "screen-worthy"
    assert "exit_lab_missing" in gate["validation_floor_reasons"]


def test_validation_floor_report_from_manifest_ties_source_sha(tmp_path: Path) -> None:
    interesting_path = tmp_path / "interesting.parquet"
    spec_path = tmp_path / "resolved_spec.json"
    manifest_path = tmp_path / "discovery_run_manifest.json"
    pd.DataFrame([_candidate()]).to_parquet(interesting_path, index=False)
    spec_path.write_text(json.dumps({"budget": {"max_trials": 10}}), encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "required_outputs": {
                    "interesting_candidates": str(interesting_path),
                    "discovery_spec_resolved": str(spec_path),
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    result = build_discovery_validation_floor_report_from_manifest(manifest_path)
    row = result.candidate_gates.iloc[0]

    assert result.manifest["source_discovery_manifest_sha256"]
    assert row["source_discovery_manifest_sha256"] == result.manifest["source_discovery_manifest_sha256"]
    assert result.manifest["experiment_budget_ledger"]["declared_search_space"] == 10


def test_validation_blocker_registry_contains_roadmap_codes() -> None:
    codes = registered_blocker_codes()
    registry = blocker_registry_payload()

    for code in (
        "funding_feature_future_leakage",
        "regime_smoothed_state_used_in_validation",
        "knn_future_or_overlapping_neighbor",
        "latest_window_context_non_diagnostic_claim",
        "liquidation_false_zero_window",
        "depth_sequence_integrity_missing",
        "barrier_ordering_without_lower_tf_proof",
        "funding_only_crowding_overfit",
        "cross_symbol_future_alignment",
        "isolated_top_score_large_grid",
        "knn_sample_reduction_only",
        "baseline_comparator_missing",
        "no_regime_baseline_missing",
        "exit_lab_missing",
        "filter_ablation_missing",
        "feature_ablation_missing",
        "multiple_testing_stability_incomplete",
    ):
        assert code in codes
        assert code in registry["codes"]
