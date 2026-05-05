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
from tradingbotsuite.features.registry import LIQUIDATION_CONTEXT_COLUMNS, WT3D_COLUMNS, manifest_from_preset
from tradingbotsuite.research.hmm_knn import WT3D_FEATURE_COLUMNS

PERP_CONTEXT_V2_COLUMNS = (
    "perp_mark_index_basis",
    "perp_premium",
    "perp_premium_z_7d",
    "perp_premium_slope_8h",
    "perp_last_funding_rate",
    "perp_funding_z_7d",
    "perp_funding_momentum",
    "cal_time_since_last_funding_h",
    "cal_time_to_next_funding_h",
    "oi_notional",
    "oi_delta_1h",
    "oi_delta_z_7d",
    "oi_volume_ratio",
    "flow_buy_sell_ratio",
    "flow_signed_taker_notional",
    "flow_signed_taker_z_7d",
    "quality_context_missing_count",
    "quality_has_funding_gap",
    "quality_has_oi_gap",
    "quality_has_premium_gap",
    "quality_provider_backed_all_required",
    "quality_latest_window_context_only",
)


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
        "perp_context_v2",
        "liquidation_context_v1",
        "microstructure_context_v1",
        "wt3d_v1",
        "cross_asset_v1",
        "calendar_v1",
    } <= set(registry)
    assert tuple(WT3D_FEATURE_COLUMNS) == WT3D_COLUMNS
    assert "wt3d_v1" not in feature_set_presets()["features_full_context_no_wt"]
    assert "wt3d_v1" in feature_set_presets()["features_full_context_wt3d"]
    assert feature_set_presets()["features_perp_context_v2"] == ("perp_context_v2",)
    assert registry["perp_context_v2"].input_families == ("funding_rate", "premium_index", "open_interest", "agg_trade")
    assert registry["perp_context_v2"].point_in_time_safe is True
    assert registry["perp_context_v2"].optional is True
    assert feature_set_presets()["features_liquidation_context_v1"] == ("liquidation_context_v1",)
    assert registry["liquidation_context_v1"].input_families == ("liquidation",)
    assert registry["liquidation_context_v1"].point_in_time_safe is True
    assert registry["liquidation_context_v1"].optional is True
    assert feature_set_presets()["features_microstructure_filter_only"] == ("microstructure_context_v1",)
    assert feature_set_presets()["features_cross_asset_context"] == ("cross_asset_v1",)


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


def test_perp_context_v2_manifest_contract_contains_required_columns_and_families() -> None:
    manifest = manifest_from_preset("features_perp_context_v2")

    assert manifest.feature_packs == ("perp_context_v2",)
    assert manifest.feature_columns == PERP_CONTEXT_V2_COLUMNS
    assert manifest.input_families == ("funding_rate", "premium_index", "open_interest", "agg_trade")
    assert not {"liquidation", "depth_snapshot", "book_ticker", "cross_exchange", "cross_asset", "eth"} & set(
        manifest.input_families
    )
    assert validate_feature_manifest(manifest).valid is True


def test_liquidation_context_v1_manifest_contract_contains_required_columns_and_family() -> None:
    manifest = manifest_from_preset("features_liquidation_context_v1")

    assert manifest.feature_packs == ("liquidation_context_v1",)
    assert manifest.feature_columns == LIQUIDATION_CONTEXT_COLUMNS
    assert manifest.input_families == ("liquidation",)
    assert not {"funding_rate", "open_interest", "premium_index", "agg_trade", "depth_snapshot", "book_ticker"} & set(
        manifest.input_families
    )
    assert validate_feature_manifest(manifest).valid is True


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


def test_perp_context_v2_missing_optional_context_is_nan_with_quality_flags() -> None:
    result = build_feature_frame(
        _bars().loc[:, ["bar_time_ms", "open", "high", "low", "close"]],
        feature_set_id="features_perp_context_v2",
        feature_packs=feature_set_presets()["features_perp_context_v2"],
        interval_ms=900_000,
    )

    assert result.frame["perp_last_funding_rate"].isna().all()
    assert result.frame["missing_perp_last_funding_rate"].eq(1).all()
    assert result.frame["perp_premium"].isna().all()
    assert result.frame["missing_perp_premium"].eq(1).all()
    assert result.frame["oi_notional"].isna().all()
    assert result.frame["missing_oi_notional"].eq(1).all()
    assert result.frame["quality_has_funding_gap"].eq(1.0).all()
    assert result.frame["quality_has_oi_gap"].eq(1.0).all()
    assert result.frame["quality_has_premium_gap"].eq(1.0).all()
    assert result.frame["quality_provider_backed_all_required"].eq(0.0).all()
    assert result.frame["quality_context_missing_count"].ge(3.0).all()
    assert result.frame["missing_quality_context_missing_count"].eq(0).all()
    assert "perp_last_funding_rate" in result.availability_report.missing_context_columns


def test_liquidation_context_missing_windows_are_nan_with_quality_flags() -> None:
    result = build_feature_frame(
        _bars().loc[:, ["bar_time_ms", "open", "high", "low", "close"]],
        feature_set_id="features_liquidation_context_v1",
        feature_packs=feature_set_presets()["features_liquidation_context_v1"],
        interval_ms=900_000,
    )

    assert result.frame["liq_event_count_1h"].isna().all()
    assert result.frame["missing_liq_event_count_1h"].eq(1).all()
    assert result.frame["liq_total_notional_1h"].isna().all()
    assert result.frame["quality_has_liquidation_gap"].eq(1.0).all()
    assert result.frame["quality_liquidation_provider_backed"].eq(0.0).all()
    assert result.frame["quality_liquidation_latest_window_context_only"].eq(0.0).all()
    assert "liq_event_count_1h" in result.availability_report.missing_context_columns


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
