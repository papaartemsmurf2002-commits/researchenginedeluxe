from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from tradingbotsuite.features import (
    build_feature_frame,
    build_feature_manifest,
    feature_pack_registry,
    feature_set_presets,
    fit_train_only_preprocessor,
    validate_feature_manifest,
)
from tradingbotsuite.features.registry import WT3D_COLUMNS, manifest_from_preset
from tradingbotsuite.research.hmm_knn import WT3D_FEATURE_COLUMNS


def _bars(row_count: int = 96) -> pd.DataFrame:
    rows = []
    start_ms = 1712649600000
    price = 70_000.0
    for index in range(row_count):
        price += np.sin(index / 4.0) * 30.0 + 8.0
        rows.append(
            {
                "bar_time_ms": start_ms + index * 900_000,
                "open": price - 20.0,
                "high": price + 45.0,
                "low": price - 50.0,
                "close": price,
                "funding_rate": 0.0001 if index % 2 == 0 else None,
                "open_interest_change_pct": 0.02,
                "premium_basis_rate": 0.0002,
                "basis_bps": 2.5,
                "spread_bps": 3.0,
                "top_of_book_imbalance": 0.1,
                "queue_imbalance_l5": 0.05,
            }
        )
    return pd.DataFrame(rows)


def test_feature_registry_contains_stage_four_packs_and_presets() -> None:
    registry = feature_pack_registry()

    assert {
        "price_path_v1",
        "trend_chop_v1",
        "volatility_v1",
        "perp_context_v1",
        "microstructure_context_v1",
        "wt3d_v1",
        "cross_asset_v1",
        "calendar_v1",
    } <= set(registry)
    assert tuple(WT3D_FEATURE_COLUMNS) == WT3D_COLUMNS
    assert "wt3d_v1" not in feature_set_presets()["features_full_context_no_wt"]
    assert "wt3d_v1" in feature_set_presets()["features_full_context_wt3d"]


def test_feature_manifest_hash_is_deterministic_and_valid() -> None:
    first = build_feature_manifest(
        feature_set_id="features_price_trend_vol",
        feature_packs=feature_set_presets()["features_price_trend_vol"],
        tests=["contract"],
    )
    second = build_feature_manifest(
        feature_set_id="features_price_trend_vol",
        feature_packs=feature_set_presets()["features_price_trend_vol"],
        tests=["contract"],
    )

    assert first.manifest_sha256 == second.manifest_sha256
    validation = validate_feature_manifest(first)
    assert validation.valid is True
    assert validation.errors == ()
    assert "wt3d_fast" not in first.feature_columns


def test_preset_json_files_match_registered_manifests() -> None:
    preset_dir = Path("configs/features")

    for preset_id in feature_set_presets():
        path = preset_dir / f"{preset_id}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        manifest = manifest_from_preset(preset_id)

        assert payload == manifest.to_payload()
        assert validate_feature_manifest(payload).valid is True


def test_feature_frame_is_backward_only_when_future_price_changes() -> None:
    bars = _bars()
    base = build_feature_frame(
        bars,
        feature_set_id="features_price_trend_vol_wt3d",
        feature_packs=feature_set_presets()["features_price_trend_vol_wt3d"],
        interval_ms=900_000,
    ).frame
    shocked = bars.copy()
    shocked.loc[len(shocked) - 1, "close"] *= 10.0
    changed = build_feature_frame(
        shocked,
        feature_set_id="features_price_trend_vol_wt3d",
        feature_packs=feature_set_presets()["features_price_trend_vol_wt3d"],
        interval_ms=900_000,
    ).frame

    compare_columns = ["log_return_1", "trend_slope_20", "wt3d_normal", "realized_volatility"]
    pd.testing.assert_frame_equal(
        base.loc[: len(base) - 2, compare_columns],
        changed.loc[: len(changed) - 2, compare_columns],
    )


def test_missing_context_is_explicit_and_not_zero_filled() -> None:
    bars = _bars().drop(columns=["funding_rate", "open_interest_change_pct", "premium_basis_rate", "basis_bps"])
    result = build_feature_frame(
        bars,
        feature_set_id="features_perp_context_only",
        feature_packs=feature_set_presets()["features_perp_context_only"],
        interval_ms=900_000,
    )

    assert result.frame["funding_rate"].isna().all()
    assert result.frame["missing_funding_rate"].eq(1).all()
    assert "funding_rate" in result.availability_report.missing_context_columns
    assert result.availability_report.missing_rates["funding_rate"] == 1.0


def test_no_wt_feature_set_runs_without_wt_columns() -> None:
    result = build_feature_frame(
        _bars(),
        feature_set_id="features_full_context_no_wt",
        feature_packs=feature_set_presets()["features_full_context_no_wt"],
        interval_ms=900_000,
    )

    assert len(result.frame) == 96
    assert validate_feature_manifest(result.manifest).valid is True
    assert not any(column.startswith("wt3d_") for column in result.manifest.feature_columns)
    assert not any(column.startswith("wt3d_") for column in result.frame.columns)


def test_train_only_preprocessor_never_fits_on_validation_rows() -> None:
    train = pd.DataFrame({"x": [1.0, 2.0, 3.0], "y": [10.0, None, 14.0]})
    validation = pd.DataFrame({"x": [1_000.0, None], "y": [100.0, None]})

    preprocessor = fit_train_only_preprocessor(train, ["x", "y"])
    transformed = preprocessor.transform(validation)

    assert preprocessor.fit_row_count == 3
    assert preprocessor.median == (2.0, 12.0)
    assert transformed.loc[1, "x"] == 0.0
    assert transformed.loc[1, "missing_x"] == 1
    assert transformed.loc[1, "missing_y"] == 1
