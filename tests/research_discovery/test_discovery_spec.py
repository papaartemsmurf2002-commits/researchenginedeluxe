from __future__ import annotations

from itertools import product
import json
from pathlib import Path

import pytest

from tradingbotsuite.config import AppConfig, ResearchConfig
from tradingbotsuite.research_discovery import spec as discovery_spec
from tradingbotsuite.research_discovery.spec import (
    DiscoveryRunSpec,
    discovery_search_space_summary,
    generated_trial_templates,
    resolve_discovery_paths,
)


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def test_discovery_spec_defaults_and_repo_root_output_resolution(tmp_path: Path) -> None:
    spec_path = _write_json(tmp_path / "quick.json", {"run_id": "quick-smoke"})
    spec = DiscoveryRunSpec.from_path(spec_path)
    app_config = AppConfig(research=ResearchConfig(output_dir=tmp_path / "research"))

    paths = resolve_discovery_paths(spec, app_config=app_config)

    assert spec.symbol == "BTCUSDT"
    assert spec.discovery_mode == "quick_smoke"
    assert spec.execution.max_workers == 1
    assert spec.execution.persist_trial_artifacts == "all"
    assert spec.execution.executor == "thread"
    assert spec.budget.snapshot_interval_minutes == 30
    assert paths.output_dir == (tmp_path / "research" / "discovery_runs" / "quick-smoke").resolve()
    assert paths.output_dir.is_relative_to(paths.research_output_dir)


def test_discovery_spec_rejects_unsafe_run_id(tmp_path: Path) -> None:
    spec_path = _write_json(tmp_path / "bad.json", {"run_id": "../bad"})

    with pytest.raises(ValueError, match="safe file-system identifier"):
        DiscoveryRunSpec.from_path(spec_path)


def test_discovery_paths_reject_output_outside_research_root(tmp_path: Path) -> None:
    spec_path = _write_json(
        tmp_path / "bad-output.json",
        {
            "run_id": "bad-output",
            "research_output_dir": str(tmp_path / "research"),
            "output_dir": str(tmp_path / "elsewhere" / "bad-output"),
        },
    )
    spec = DiscoveryRunSpec.from_path(spec_path)

    with pytest.raises(ValueError, match="configured research output"):
        resolve_discovery_paths(spec)


def test_discovery_spec_rejects_invalid_budget(tmp_path: Path) -> None:
    spec_path = _write_json(
        tmp_path / "bad-budget.json",
        {"run_id": "bad-budget", "budget": {"max_trials": 0}},
    )

    with pytest.raises(ValueError, match="budget.max_trials"):
        DiscoveryRunSpec.from_path(spec_path)


def test_discovery_spec_rejects_unsafe_trial_id(tmp_path: Path) -> None:
    spec_path = _write_json(
        tmp_path / "bad-trial.json",
        {"run_id": "bad-trial", "trial_templates": [{"trial_id": "../trial"}]},
    )

    with pytest.raises(ValueError, match="trial_templates.trial_id"):
        DiscoveryRunSpec.from_path(spec_path)


def test_real_discovery_spec_rejects_duplicate_search_dimension_values(tmp_path: Path) -> None:
    spec_path = _write_json(
        tmp_path / "duplicate-search.json",
        {
            "run_id": "duplicate-search",
            "discovery_mode": "entry_discovery_standard",
            "feature_column_set_ids": ["price_trend_vol"],
            "search": {
                "k_values": [3, 3],
            },
        },
    )

    with pytest.raises(ValueError, match="search.k_values must not contain duplicate values"):
        DiscoveryRunSpec.from_path(spec_path)


def test_real_discovery_spec_rejects_duplicate_feature_column_set_ids(tmp_path: Path) -> None:
    spec_path = _write_json(
        tmp_path / "duplicate-feature-sets.json",
        {
            "run_id": "duplicate-feature-sets",
            "discovery_mode": "entry_discovery_standard",
            "feature_column_set_ids": ["price_trend_vol", "price_trend_vol"],
        },
    )

    with pytest.raises(ValueError, match="feature_column_set_ids must not contain duplicate values"):
        DiscoveryRunSpec.from_path(spec_path)


def test_real_discovery_configs_generate_non_placeholder_search_templates() -> None:
    standard = DiscoveryRunSpec.from_path(Path("configs/discovery/standard_entry_discovery_btcusdt_durable_r104_v1.json"))
    eth_standard = DiscoveryRunSpec.from_path(Path("configs/discovery/standard_entry_discovery_ethusdt_durable_r104_v1.json"))
    deep = DiscoveryRunSpec.from_path(Path("configs/discovery/deep_candidate_harvest_btcusdt_v4.json"))
    exact_btc = DiscoveryRunSpec.from_path(Path("configs/discovery/exact_entry_sweep_btcusdt_durable_r104_v1.json"))
    exact_eth = DiscoveryRunSpec.from_path(Path("configs/discovery/exact_entry_sweep_ethusdt_durable_r104_v1.json"))

    standard_templates = generated_trial_templates(standard)
    eth_templates = generated_trial_templates(eth_standard)
    deep_templates = generated_trial_templates(deep)
    standard_summary = discovery_search_space_summary(standard)
    deep_summary = discovery_search_space_summary(deep)
    exact_btc_summary = discovery_search_space_summary(exact_btc)
    exact_eth_summary = discovery_search_space_summary(exact_eth)

    assert standard.discovery_mode == "entry_discovery_standard"
    assert eth_standard.discovery_mode == "entry_discovery_standard"
    assert eth_standard.symbol == "ETHUSDT"
    assert deep.discovery_mode == "deep_candidate_harvest"
    assert exact_btc.discovery_mode == "deep_candidate_harvest"
    assert exact_eth.symbol == "ETHUSDT"
    assert standard.execution.max_workers == 8
    assert eth_standard.execution.max_workers == 8
    assert deep.execution.max_workers == 8
    assert exact_btc.execution.max_workers == 48
    assert exact_btc.execution.executor == "process"
    assert exact_eth.execution.executor == "process"
    assert deep.execution.persist_trial_artifacts == "interesting_only"
    assert len(standard_templates) == standard.budget.max_trials
    assert len(eth_templates) == eth_standard.budget.max_trials
    assert len(deep_templates) == deep.budget.max_trials
    assert {template.candidate_family for template in standard_templates} == {"regime_knn_entry_discovery"}
    assert {template.candidate_family for template in eth_templates} == {"regime_knn_entry_discovery"}
    assert {template.payload["trial_kind"] for template in standard_templates[:10]} == {"regime_knn_entry_discovery"}
    assert set(standard.search.regime_modes) == {
        "none",
        "gmm_gate_only",
        "gmm_same_regime_neighbors",
        "gmm_all_regime_neighbors_with_gate",
    }
    assert all(template.payload["true_hmm_backend_used"] is False for template in standard_templates[:10])
    assert {template.payload["feature_column_set_id"] for template in standard_templates} == {
        "price_trend_vol",
        "compact_wt3d_base",
    }
    assert standard.search.min_splits == 2
    assert standard.search.min_trade_count == 1
    assert "btcusdt_public_archive_multi_window_v1" in str(standard.data.dataset_manifest_paths[0])
    assert "ethusdt_public_archive_multi_window_v1" in str(eth_standard.data.dataset_manifest_paths[0])
    assert any(template.payload["hmm_state_count"] != 4 for template in deep_templates)
    assert any(template.payload["min_neighbor_count"] != 4 for template in deep_templates)
    assert standard_summary["coverage_label"] == "sparse_sample"
    assert standard_summary["planned_trials"] == 720
    assert standard_summary["sampled_fraction"] < 0.01
    assert deep_summary["coverage_label"] == "sparse_sample"
    assert deep_summary["exhaustive"] is False
    assert exact_btc_summary["total_combinations"] == 570240
    assert exact_btc_summary["planned_trials"] == 570240
    assert exact_btc_summary["sampled_fraction"] == 1.0
    assert exact_btc_summary["exhaustive"] is True
    assert exact_btc_summary["coverage_label"] == "exhaustive"
    assert exact_eth_summary["total_combinations"] == 570240
    assert exact_eth_summary["exhaustive"] is True


def test_exact_r104_discovery_search_space_dimensions_match_configured_axes() -> None:
    expected_counts = {
        "feature_column_set_id": 2,
        "hmm_state_count": 1,
        "hmm_posterior_threshold": 1,
        "hmm_entropy_threshold": 1,
        "label_horizon": 3,
        "knn_neighbor_pair": 22,
        "distance_metric": 3,
        "probability_threshold": 6,
        "expected_value_threshold": 4,
        "min_neighbor_agreement": 5,
        "min_distance_quality": 3,
        "vote_margin_threshold": 4,
        "regime_mode": 1,
    }
    expected_neighbor_pairs = {
        (k_value, min_neighbor_count)
        for k_value in (3, 5, 8, 13, 21, 34)
        for min_neighbor_count in (2, 3, 4, 5)
        if min_neighbor_count <= k_value
    }

    for path in (
        Path("configs/discovery/exact_entry_sweep_btcusdt_durable_r104_v1.json"),
        Path("configs/discovery/exact_entry_sweep_ethusdt_durable_r104_v1.json"),
    ):
        spec = DiscoveryRunSpec.from_path(path)
        summary = discovery_search_space_summary(spec)
        dimensions = dict(discovery_spec._real_discovery_dimensions(spec))
        neighbor_pairs = {
            (int(item["k"]), int(item["min_neighbor_count"]))
            for item in dimensions["knn_neighbor_pair"]
        }

        assert summary["search_space_kind"] == "real_regime_knn_entry_discovery"
        assert summary["dimension_counts"] == expected_counts
        assert summary["total_combinations"] == 570240
        assert summary["planned_trials"] == 570240
        assert summary["exhaustive"] is True
        assert dimensions["feature_column_set_id"] == ("price_trend_vol", "compact_wt3d_base")
        assert dimensions["label_horizon"] == ("1h", "2h", "4h")
        assert dimensions["distance_metric"] == ("euclidean", "manhattan", "cosine")
        assert dimensions["probability_threshold"] == (0.48, 0.5, 0.52, 0.55, 0.58, 0.62)
        assert dimensions["expected_value_threshold"] == (-0.0004, -0.0002, 0.0, 0.0002)
        assert dimensions["min_neighbor_agreement"] == (0.48, 0.5, 0.52, 0.55, 0.6)
        assert dimensions["min_distance_quality"] == (0.0, 0.005, 0.01)
        assert dimensions["vote_margin_threshold"] == (0.0, 0.02, 0.03, 0.05)
        assert dimensions["regime_mode"] == ("none",)
        assert neighbor_pairs == expected_neighbor_pairs
        assert discovery_spec._dimension_space_size(tuple(dimensions.items())) == summary["total_combinations"]


def test_real_discovery_small_exact_generation_is_unique_and_exhaustive(tmp_path: Path) -> None:
    spec_path = _write_json(
        tmp_path / "small-exact.json",
        {
            "run_id": "small-exact",
            "discovery_mode": "entry_discovery_standard",
            "feature_column_set_ids": ["price_trend_vol", "compact_wt3d_base"],
            "budget": {"max_trials": 16, "rng_seed": 11},
            "search": {
                "hmm_state_counts": [3],
                "hmm_posterior_thresholds": [0.55],
                "hmm_entropy_thresholds": [0.78],
                "label_horizons": ["1h", "4h"],
                "k_values": [3, 5],
                "min_neighbor_counts": [2],
                "distance_metrics": ["euclidean", "cosine"],
                "probability_thresholds": [0.52],
                "expected_value_thresholds": [0.0],
                "min_neighbor_agreements": [0.52],
                "min_distance_qualities": [0.0],
                "vote_margin_thresholds": [0.0],
                "regime_modes": ["none"],
            },
        },
    )
    spec = DiscoveryRunSpec.from_path(spec_path)

    templates = generated_trial_templates(spec)
    payload_combinations = {
        (
            payload["feature_column_set_id"],
            payload["label_horizon"],
            payload["k"],
            payload["min_neighbor_count"],
            payload["distance_metric"],
            payload["regime_mode"],
        )
        for payload in (template.payload for template in templates)
    }
    expected_combinations = set(
        product(
            ("price_trend_vol", "compact_wt3d_base"),
            ("1h", "4h"),
            (3, 5),
            (2,),
            ("euclidean", "cosine"),
            ("none",),
        )
    )

    assert discovery_search_space_summary(spec)["exhaustive"] is True
    assert len(templates) == 16
    assert len({template.trial_id for template in templates}) == 16
    assert len({template.candidate_id for template in templates}) == 16
    assert payload_combinations == expected_combinations
    assert all(template.payload["trial_kind"] == "regime_knn_entry_discovery" for template in templates)
    assert all(template.payload["search_space_exhaustive"] is True for template in templates)


def test_real_discovery_sparse_generation_samples_unique_combinations(tmp_path: Path) -> None:
    spec_path = _write_json(
        tmp_path / "small-sparse.json",
        {
            "run_id": "small-sparse",
            "discovery_mode": "entry_discovery_standard",
            "feature_column_set_ids": ["price_trend_vol"],
            "budget": {"max_trials": 5, "rng_seed": 11},
            "search": {
                "hmm_state_counts": [3],
                "hmm_posterior_thresholds": [0.55],
                "hmm_entropy_thresholds": [0.78],
                "label_horizons": ["1h", "2h", "4h"],
                "k_values": [3, 5],
                "min_neighbor_counts": [2, 3],
                "distance_metrics": ["euclidean", "cosine"],
                "probability_thresholds": [0.52],
                "expected_value_thresholds": [0.0],
                "min_neighbor_agreements": [0.52],
                "min_distance_qualities": [0.0],
                "vote_margin_thresholds": [0.0],
                "regime_modes": ["none"],
            },
        },
    )
    spec = DiscoveryRunSpec.from_path(spec_path)

    templates = generated_trial_templates(spec)
    payload_combinations = {
        (
            payload["label_horizon"],
            payload["k"],
            payload["min_neighbor_count"],
            payload["distance_metric"],
        )
        for payload in (template.payload for template in templates)
    }

    assert discovery_search_space_summary(spec)["exhaustive"] is False
    assert len(templates) == 5
    assert len(payload_combinations) == 5
    assert all(template.payload["search_space_total_combinations"] == 24 for template in templates)


def test_real_discovery_candidate_ids_are_parameter_identity_stable_across_seed(tmp_path: Path) -> None:
    def write_seeded_spec(seed: int) -> Path:
        return _write_json(
            tmp_path / f"seed-{seed}.json",
            {
                "run_id": "stable-candidate-ids",
                "discovery_mode": "entry_discovery_standard",
                "feature_column_set_ids": ["price_trend_vol", "compact_wt3d_base"],
                "budget": {"max_trials": 16, "rng_seed": seed},
                "search": {
                    "hmm_state_counts": [3],
                    "hmm_posterior_thresholds": [0.55],
                    "hmm_entropy_thresholds": [0.78],
                    "label_horizons": ["1h", "4h"],
                    "k_values": [3, 5],
                    "min_neighbor_counts": [2],
                    "distance_metrics": ["euclidean", "cosine"],
                    "probability_thresholds": [0.52],
                    "expected_value_thresholds": [0.0],
                    "min_neighbor_agreements": [0.52],
                    "min_distance_qualities": [0.0],
                    "vote_margin_thresholds": [0.0],
                    "regime_modes": ["none"],
                },
            },
        )

    def candidates_by_payload_key(spec: DiscoveryRunSpec) -> dict[tuple[object, ...], str]:
        result = {}
        for template in generated_trial_templates(spec):
            payload = template.payload
            key = (
                payload["feature_column_set_id"],
                payload["label_horizon"],
                payload["k"],
                payload["min_neighbor_count"],
                payload["distance_metric"],
            )
            result[key] = template.candidate_id
        return result

    first = candidates_by_payload_key(DiscoveryRunSpec.from_path(write_seeded_spec(11)))
    second = candidates_by_payload_key(DiscoveryRunSpec.from_path(write_seeded_spec(29)))

    assert len(first) == 16
    assert first == second


def test_real_discovery_templates_expand_explicit_regime_modes(tmp_path: Path) -> None:
    spec_path = _write_json(
        tmp_path / "regime-modes.json",
        {
            "run_id": "regime-modes",
            "discovery_mode": "entry_discovery_standard",
            "feature_column_set_ids": ["price_trend_vol"],
            "budget": {"max_trials": 4, "rng_seed": 1},
            "search": {
                "hmm_state_counts": [4],
                "hmm_posterior_thresholds": [0.6],
                "hmm_entropy_thresholds": [0.78],
                "label_horizons": ["4h"],
                "k_values": [8],
                "min_neighbor_counts": [4],
                "distance_metrics": ["euclidean"],
                "probability_thresholds": [0.55],
                "expected_value_thresholds": [0.0],
                "min_neighbor_agreements": [0.55],
                "min_distance_qualities": [0.01],
                "vote_margin_thresholds": [0.05],
                "regime_modes": [
                    "none",
                    "gmm_gate_only",
                    "gmm_same_regime_neighbors",
                    "gmm_all_regime_neighbors_with_gate",
                ],
            },
        },
    )
    spec = DiscoveryRunSpec.from_path(spec_path)

    templates = generated_trial_templates(spec)
    by_mode = {str(template.payload["regime_mode"]): template.payload for template in templates}

    assert set(by_mode) == {
        "none",
        "gmm_gate_only",
        "gmm_same_regime_neighbors",
        "gmm_all_regime_neighbors_with_gate",
    }
    assert by_mode["none"]["regime_detector_type"] == "none"
    assert by_mode["none"]["regime_gate_enabled"] is False
    assert by_mode["none"]["same_regime_neighbor_pool_enabled"] is False
    assert by_mode["gmm_same_regime_neighbors"]["regime_detector_type"] == "gmm"
    assert by_mode["gmm_same_regime_neighbors"]["regime_gate_enabled"] is True
    assert by_mode["gmm_same_regime_neighbors"]["same_regime_neighbor_pool_enabled"] is True
    assert by_mode["gmm_all_regime_neighbors_with_gate"]["same_regime_neighbor_pool_enabled"] is False
    assert {payload["true_hmm_backend_used"] for payload in by_mode.values()} == {False}
