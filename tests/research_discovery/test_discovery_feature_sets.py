from __future__ import annotations

import json
from pathlib import Path

import pytest

from tradingbotsuite.research_discovery.feature_sets import (
    DEFAULT_MAX_ENABLED_DIMENSIONS,
    DiscoveryFeatureColumnSetManifest,
    load_feature_column_set_manifest,
    stable_feature_column_set_hash,
    validate_feature_column_set_manifest,
)


def _manifest_payload() -> dict[str, object]:
    return {
        "manifest_version": "discovery-feature-column-set-manifest-v1",
        "manifest_id": "test_feature_column_sets",
        "feature_column_set_version": "v1",
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "feature_column_sets": [
            {
                "feature_column_set_id": "price_trend_vol",
                "registered_feature_set_id": "features_price_trend_vol",
                "columns": ["log_return_1", "efficiency_ratio", "realized_volatility"],
                "maximum_dimensions": DEFAULT_MAX_ENABLED_DIMENSIONS,
                "enabled": True,
            },
            {
                "feature_column_set_id": "compact_wt3d_base",
                "registered_feature_set_id": "features_price_trend_vol_wt3d",
                "columns": ["log_return_1", "efficiency_ratio", "wt3d_normal"],
                "maximum_dimensions": DEFAULT_MAX_ENABLED_DIMENSIONS,
                "required_comparator_set": "price_trend_vol",
                "enabled": True,
            },
        ],
    }


def test_checked_discovery_feature_column_set_manifest_is_valid() -> None:
    manifest = load_feature_column_set_manifest(Path("configs/discovery/feature_column_sets_v4.json"))

    validate_feature_column_set_manifest(
        manifest,
        selected_ids=(
            "price_trend_vol",
            "compact_wt3d_base",
            "alternative_non_wt_price_state",
            "durable_aggtrade_orderflow_proxy",
        ),
    )

    assert manifest.research_only is True
    assert manifest.observe_only is True
    assert manifest.promotion_ready is False
    assert manifest.manifest_sha256 == stable_feature_column_set_hash(manifest.to_payload(include_hash=False))
    assert any(not item.contains_wt3d for item in manifest.enabled_sets)
    assert manifest.set_by_id()["compact_wt3d_base"].required_comparator_set == "price_trend_vol"
    assert manifest.set_by_id()["durable_aggtrade_orderflow_proxy"].required_comparator_set == "price_trend_vol"
    assert manifest.set_by_id()["future_ntri_entropy_additions"].enabled is False


def test_feature_column_set_validation_rejects_unknown_columns() -> None:
    payload = _manifest_payload()
    payload["feature_column_sets"][0]["columns"] = ["not_a_registered_column"]  # type: ignore[index]

    with pytest.raises(ValueError, match="unknown_feature_columns"):
        DiscoveryFeatureColumnSetManifest.from_payload(payload)


def test_feature_column_set_validation_rejects_unbounded_enabled_set() -> None:
    payload = _manifest_payload()
    payload["feature_column_sets"][0]["columns"] = [  # type: ignore[index]
        "log_return_1",
        "log_return_4",
        "log_return_16",
        "momentum_4",
        "momentum_16",
        "path_zscore_20",
        "trend_slope_20",
        "efficiency_ratio",
        "choppiness",
    ]

    with pytest.raises(ValueError, match="feature_column_set_exceeds_maximum_dimensions"):
        DiscoveryFeatureColumnSetManifest.from_payload(payload)


def test_feature_column_set_validation_rejects_wt_without_non_wt_comparator() -> None:
    payload = _manifest_payload()
    payload["feature_column_sets"][1].pop("required_comparator_set")  # type: ignore[index]

    with pytest.raises(ValueError, match="wt3d_feature_column_set_requires_comparator"):
        DiscoveryFeatureColumnSetManifest.from_payload(payload)


def test_feature_column_set_manifest_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    payload = _manifest_payload()
    payload["manifest_sha256"] = "bad"
    path = tmp_path / "feature_column_sets.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    with pytest.raises(ValueError, match="hash mismatch"):
        load_feature_column_set_manifest(path)


def test_selected_disabled_feature_column_set_fails_closed() -> None:
    manifest = load_feature_column_set_manifest(Path("configs/discovery/feature_column_sets_v4.json"))

    with pytest.raises(ValueError, match="selected_feature_column_set_disabled"):
        validate_feature_column_set_manifest(manifest, selected_ids=("future_ntri_entropy_additions",))


def test_selected_wt3d_feature_column_set_requires_selected_comparator() -> None:
    manifest = load_feature_column_set_manifest(Path("configs/discovery/feature_column_sets_v4.json"))

    with pytest.raises(ValueError, match="selected_wt3d_feature_column_set_requires_selected_comparator"):
        validate_feature_column_set_manifest(manifest, selected_ids=("compact_wt3d_base",))
