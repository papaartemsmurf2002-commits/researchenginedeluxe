from __future__ import annotations

import json

import pytest

from tradingbotsuite.v2.strategy_plugins import (
    StrategyPluginManifest,
    build_legacy_strategy_plugin_manifest,
    build_legacy_strategy_plugin_registry_manifest,
    write_strategy_plugin_manifest,
    write_strategy_plugin_registry_manifest,
)


def test_legacy_strategy_metadata_wraps_into_v2_manifest_without_execution() -> None:
    manifest = build_legacy_strategy_plugin_manifest("trend_following_v1")

    assert manifest.strategy_id == "trend_following_v1"
    assert manifest.legacy_subsystem == "strategy_plugins"
    assert manifest.legacy_classification == "wrap_into_v2"
    assert manifest.source_sha256 and len(manifest.source_sha256) == 64
    assert manifest.legacy_metadata_sha256 and len(manifest.legacy_metadata_sha256) == 64
    assert manifest.default_parameters["slope_threshold"] == 0.12
    assert manifest.parameter_space["slope_threshold"] == (0.08, 0.12, 0.16)
    assert manifest.signal_density["max_turnover"] == 0.35
    assert "trend_below_slope_threshold" in manifest.failure_modes
    assert manifest.plugin_execution_allowed is False
    assert manifest.protocol.execution_enabled is False
    assert manifest.order_placement_allowed is False
    assert manifest.sizing_allowed is False
    assert manifest.runtime_mode_change_allowed is False
    assert manifest.research_only is True
    assert manifest.observe_only is True
    assert manifest.promotion_ready is False


def test_legacy_strategy_manifest_writer_records_v2_evidence(tmp_path) -> None:
    manifest = build_legacy_strategy_plugin_manifest("volatility_breakout_v1")
    path = write_strategy_plugin_manifest(tmp_path / "strategy_plugin_manifest.json", manifest)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["manifest_id"] == manifest.manifest_id
    assert payload["strategy_id"] == "volatility_breakout_v1"
    assert payload["plugin_execution_allowed"] is False
    assert payload["candidate_pack_write_allowed"] is False
    assert payload["promotion_ready"] is False


def test_legacy_strategy_registry_manifest_is_metadata_only(tmp_path) -> None:
    registry = build_legacy_strategy_plugin_registry_manifest(
        ["baseline_no_trade", "trend_following_v1"]
    )
    path = write_strategy_plugin_registry_manifest(tmp_path / "registry.json", registry)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert registry.strategy_count == 2
    assert [manifest.strategy_id for manifest in registry.manifests] == [
        "baseline_no_trade",
        "trend_following_v1",
    ]
    assert payload["strategy_count"] == 2
    assert all(manifest.plugin_execution_allowed is False for manifest in registry.manifests)
    assert all(manifest.candidate_evidence is False for manifest in registry.manifests)


def test_unknown_legacy_strategy_metadata_fails_closed() -> None:
    with pytest.raises(ValueError, match="unknown_legacy_strategy_metadata"):
        build_legacy_strategy_plugin_manifest("not_a_legacy_strategy")


def test_strategy_plugin_manifest_rejects_execution_live_order_and_sizing_flags() -> None:
    manifest = build_legacy_strategy_plugin_manifest("trend_following_v1")
    payload = manifest.model_dump()
    payload["plugin_execution_allowed"] = True
    with pytest.raises(ValueError, match="plugin_execution_allowed"):
        StrategyPluginManifest.model_validate(payload)

    for flag in (
        "network_access_allowed",
        "secrets_access_allowed",
        "arbitrary_file_access_allowed",
        "live_runtime_access_allowed",
        "order_placement_allowed",
        "sizing_allowed",
        "runtime_mode_change_allowed",
        "candidate_pack_write_allowed",
        "live_signal",
        "paper_signal",
        "sizing_instruction",
        "order_placement_instruction",
        "runtime_mode_change",
    ):
        blocked = manifest.model_dump()
        blocked[flag] = True
        with pytest.raises(ValueError, match=flag):
            StrategyPluginManifest.model_validate(blocked)
