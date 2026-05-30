from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from tradingbotsuite.research_discovery.multiple_testing import (
    DiscoveryMultipleTestingSpec,
    build_discovery_multiple_testing_report,
    build_discovery_multiple_testing_report_from_manifest,
    write_discovery_multiple_testing_artifacts,
)


def _candidates(*, latest_window_only: bool = False, stability_neighborhood_size: int = 4) -> pd.DataFrame:
    rows = []
    for candidate_id, score in (
        ("candidate-1", 0.20),
        ("candidate-2", 0.16),
        ("candidate-3", 0.14),
        ("candidate-4", 0.12),
    ):
        rows.append(
            {
                "candidate_id": candidate_id,
                "discovery_screen_score_v2": score,
                "feature_column_set_id": "price_trend_vol",
                "regime_mode": "none",
                "label_horizon": "4h",
                "distance_metric": "euclidean",
                "k": 8,
                "min_neighbor_count": 2,
                "effective_trial_count": 100,
                "stability_neighborhood_size": stability_neighborhood_size,
                "split_window_concentration": 0.25,
                "side_concentration": 0.55,
                "latest_window_only": latest_window_only,
            }
        )
    return pd.DataFrame(rows)


def test_multiple_testing_report_passes_stable_non_concentrated_leads(tmp_path) -> None:
    spec = DiscoveryMultipleTestingSpec(declared_search_space=100)

    result = build_discovery_multiple_testing_report(_candidates(), spec=spec)
    artifact = write_discovery_multiple_testing_artifacts(tmp_path / "multiple-testing", result)
    manifest = json.loads(artifact.manifest_path.read_text(encoding="utf-8"))
    gates = pd.read_parquet(artifact.candidate_gates_path)

    assert manifest["multiple_testing_manifest_version"] == "discovery-multiple-testing-stability-manifest-v1"
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["order_placement_used"] is False
    assert manifest["summary"]["passed_count"] == 4
    assert gates["multiple_testing_status"].eq("passed").all()
    assert gates.loc[gates["candidate_id"].eq("candidate-1"), "sampled_fraction"].iloc[0] == 0.04


def test_multiple_testing_derives_stability_neighborhoods_without_quadratic_scan() -> None:
    candidates = _candidates().drop(columns=["stability_neighborhood_size"])
    candidates.loc[3, "distance_metric"] = "cosine"
    spec = DiscoveryMultipleTestingSpec(
        declared_search_space=100,
        min_stability_neighborhood_size=1,
    )

    result = build_discovery_multiple_testing_report(candidates, spec=spec)
    sizes = dict(
        zip(
            result.candidate_gates["candidate_id"].astype(str),
            result.candidate_gates["stability_neighborhood_size"].astype(int),
            strict=True,
        )
    )

    assert sizes == {
        "candidate-1": 3,
        "candidate-2": 3,
        "candidate-3": 3,
        "candidate-4": 1,
    }


def test_multiple_testing_report_derives_search_space_from_discovery_manifest(tmp_path) -> None:
    interesting_path = tmp_path / "interesting.parquet"
    spec_path = tmp_path / "resolved_spec.json"
    manifest_path = tmp_path / "discovery_run_manifest.json"
    pd.DataFrame(
        [
            {
                "candidate_id": "candidate-1",
                "record_sha256": "record-1",
                "discovery_screen_score_v2": 0.20,
                "split_window_concentration": 0.25,
                "side_concentration": 0.55,
            }
        ]
    ).to_parquet(interesting_path, index=False)
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
    spec = DiscoveryMultipleTestingSpec(
        declared_search_space=0,
        min_stability_neighborhood_size=1,
        max_best_candidate_concentration=1.0,
    )

    result = build_discovery_multiple_testing_report_from_manifest(manifest_path, spec=spec)
    row = result.candidate_gates.iloc[0]

    assert result.manifest["source_discovery_manifest_sha256"]
    assert result.manifest["declared_search_space_source"] == "discovery_manifest_or_trial_records"
    assert row["declared_search_space"] == 10
    assert row["sampled_fraction"] == 0.1
    assert row["record_sha256"] == "record-1"


def test_multiple_testing_prefers_manifest_budget_before_trial_record_scan(tmp_path, monkeypatch) -> None:
    interesting_path = tmp_path / "interesting.parquet"
    trials_dir = tmp_path / "trials"
    trials_dir.mkdir()
    (trials_dir / "trial-000001.json").write_text("{}", encoding="utf-8")
    manifest_path = tmp_path / "discovery_run_manifest.json"
    pd.DataFrame(
        [
            {
                "candidate_id": "candidate-1",
                "record_sha256": "record-1",
                "discovery_screen_score_v2": 0.20,
                "split_window_concentration": 0.25,
                "side_concentration": 0.55,
            }
        ]
    ).to_parquet(interesting_path, index=False)
    manifest_path.write_text(
        json.dumps(
            {
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "budget": {"max_trials": 570240},
                "counts": {"completed_trials": 570240},
                "required_outputs": {
                    "interesting_candidates": str(interesting_path),
                    "trials": str(trials_dir),
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    def fail_read_trial_record(path):
        raise AssertionError("trial records should not be scanned when manifest budget is present")

    monkeypatch.setattr(
        "tradingbotsuite.research_discovery.multiple_testing.read_trial_record",
        fail_read_trial_record,
    )

    result = build_discovery_multiple_testing_report_from_manifest(manifest_path)

    assert result.candidate_gates.loc[0, "declared_search_space"] == 570240


def test_multiple_testing_manifest_candidates_without_concentration_evidence_are_blocked(tmp_path) -> None:
    interesting_path = tmp_path / "interesting.parquet"
    spec_path = tmp_path / "resolved_spec.json"
    manifest_path = tmp_path / "discovery_run_manifest.json"
    pd.DataFrame(
        [
            {
                "candidate_id": "candidate-1",
                "record_sha256": "record-1",
                "discovery_screen_score_v2": 0.20,
            }
        ]
    ).to_parquet(interesting_path, index=False)
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
    spec = DiscoveryMultipleTestingSpec(
        declared_search_space=0,
        min_stability_neighborhood_size=1,
        max_best_candidate_concentration=1.0,
    )

    result = build_discovery_multiple_testing_report_from_manifest(manifest_path, spec=spec)
    row = result.candidate_gates.iloc[0]

    assert row["multiple_testing_status"] == "blocked"
    assert "split_window_concentration_required" in row["multiple_testing_reasons"]
    assert "side_concentration_required" in row["multiple_testing_reasons"]


def test_multiple_testing_blocks_isolated_large_grid_latest_window_lead() -> None:
    spec = DiscoveryMultipleTestingSpec(declared_search_space=10_000, latest_window_only=True)

    result = build_discovery_multiple_testing_report(_candidates(stability_neighborhood_size=1), spec=spec)
    row = result.candidate_gates.loc[result.candidate_gates["candidate_id"].eq("candidate-1")].iloc[0]

    assert row["multiple_testing_status"] == "blocked"
    assert "sampled_fraction_below_candidate_ready_floor" in row["multiple_testing_reasons"]
    assert "stability_neighborhood_size_below_floor" in row["multiple_testing_reasons"]
    assert "latest_window_only_evidence" in row["multiple_testing_reasons"]


def test_multiple_testing_blocks_split_and_side_concentration() -> None:
    candidates = _candidates()
    candidates.loc[0, "split_window_concentration"] = 0.95
    candidates.loc[0, "side_concentration"] = 0.98
    spec = DiscoveryMultipleTestingSpec(declared_search_space=100)

    result = build_discovery_multiple_testing_report(candidates, spec=spec)
    row = result.candidate_gates.loc[result.candidate_gates["candidate_id"].eq("candidate-1")].iloc[0]

    assert "split_window_concentration_above_ceiling" in row["multiple_testing_reasons"]
    assert "side_concentration_above_ceiling" in row["multiple_testing_reasons"]
