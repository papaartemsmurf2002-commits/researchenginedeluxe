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
    assert len(standard_templates) == standard.budget.max_trials
    assert len(deep_templates) == deep.budget.max_trials
    assert {template.candidate_family for template in standard_templates} == {"hmm_knn_entry_discovery"}
    assert {template.payload["trial_kind"] for template in standard_templates[:10]} == {"hmm_knn_entry_discovery"}
    assert {template.payload["feature_column_set_id"] for template in standard_templates}.issuperset(
        {"price_trend_vol", "compact_wt3d_base", "alternative_non_wt_price_state"}
    )
    assert any(template.payload["hmm_state_count"] != 4 for template in deep_templates)
    assert any(template.payload["min_neighbor_count"] != 4 for template in deep_templates)
