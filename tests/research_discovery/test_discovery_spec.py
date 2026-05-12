from __future__ import annotations

import json
from pathlib import Path

import pytest

from tradingbotsuite.config import AppConfig, ResearchConfig
from tradingbotsuite.research_discovery.spec import DiscoveryRunSpec, generated_trial_templates, resolve_discovery_paths


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


def test_real_discovery_configs_generate_non_placeholder_search_templates() -> None:
    standard = DiscoveryRunSpec.from_path(Path("configs/discovery/standard_entry_discovery_btcusdt_v4.json"))
    deep = DiscoveryRunSpec.from_path(Path("configs/discovery/deep_candidate_harvest_btcusdt_v4.json"))

    standard_templates = generated_trial_templates(standard)
    deep_templates = generated_trial_templates(deep)

    assert standard.discovery_mode == "entry_discovery_standard"
    assert deep.discovery_mode == "deep_candidate_harvest"
    assert standard.execution.max_workers == 4
    assert deep.execution.max_workers == 8
    assert deep.execution.persist_trial_artifacts == "interesting_only"
    assert len(standard_templates) == standard.budget.max_trials
    assert len(deep_templates) == deep.budget.max_trials
    assert {template.candidate_family for template in standard_templates} == {"regime_knn_entry_discovery"}
    assert {template.payload["trial_kind"] for template in standard_templates[:10]} == {"regime_knn_entry_discovery"}
    assert set(standard.search.regime_modes) == {
        "none",
        "gmm_gate_only",
        "gmm_same_regime_neighbors",
        "gmm_all_regime_neighbors_with_gate",
    }
    assert all(template.payload["true_hmm_backend_used"] is False for template in standard_templates[:10])
    assert {template.payload["feature_column_set_id"] for template in standard_templates}.issuperset(
        {"price_trend_vol", "compact_wt3d_base", "alternative_non_wt_price_state"}
    )
    assert any(template.payload["hmm_state_count"] != 4 for template in deep_templates)
    assert any(template.payload["min_neighbor_count"] != 4 for template in deep_templates)


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
