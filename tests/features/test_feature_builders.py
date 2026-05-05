from __future__ import annotations

import json

import pandas as pd
import pytest

from tradingbotsuite.backtesting.splits import build_anchored_walk_forward_splits
from tradingbotsuite.features.builders import (
    FEATURE_BUILDER_VERSION,
    build_registered_feature_set,
    canonicalize_bar_frame,
    materialize_fixture_family_context,
    materialize_registered_feature_set,
)
from tradingbotsuite.features.cache import (
    FeatureCacheIdentity,
    feature_cache_paths,
    load_feature_cache_artifact,
    write_feature_cache_artifact,
)
from tradingbotsuite.features.split_transforms import fit_transform_split_train_only
from tradingbotsuite.research.deterministic_datasets import build_hmm_knn_sweep_dataset


def test_canonicalize_deterministic_signal_bars_and_build_price_features() -> None:
    frame = build_hmm_knn_sweep_dataset(row_count=120)

    bars, mapping = canonicalize_bar_frame(frame)
    built = build_registered_feature_set(frame, feature_set_id="features_price_trend_vol")

    assert mapping["bar_time_ms"] == "signal_bar_time_ms"
    assert {"bar_time_ms", "open", "high", "low", "close", "volume"} <= set(bars.columns)
    assert built.result.completed_bar_validation.valid
    assert "directional_slope_atr" in built.result.frame.columns
    assert built.result.manifest.feature_set_id == "features_price_trend_vol"


def test_feature_cache_key_is_deterministic() -> None:
    identity = FeatureCacheIdentity(
        dataset_sha256="dataset",
        feature_set_id="features_price_trend_vol",
        feature_manifest_sha256="feature",
        builder_version="builder",
        interval_ms=900_000,
        source_column_mapping={"close": "signal_bar_close", "bar_time_ms": "signal_bar_time_ms"},
    )

    assert identity.key() == FeatureCacheIdentity(
        dataset_sha256="dataset",
        feature_set_id="features_price_trend_vol",
        feature_manifest_sha256="feature",
        builder_version="builder",
        interval_ms=900_000,
        source_column_mapping={"bar_time_ms": "signal_bar_time_ms", "close": "signal_bar_close"},
    ).key()


def test_feature_cache_key_includes_fixture_family_context_identity() -> None:
    base = FeatureCacheIdentity(
        dataset_sha256="dataset",
        feature_set_id="features_price_trend_vol",
        feature_manifest_sha256="feature",
        builder_version="builder",
        interval_ms=900_000,
        source_column_mapping={"close": "signal_bar_close", "bar_time_ms": "signal_bar_time_ms"},
        fixture_family_context_sha256="context-a",
    )

    changed = FeatureCacheIdentity(
        dataset_sha256="dataset",
        feature_set_id="features_price_trend_vol",
        feature_manifest_sha256="feature",
        builder_version="builder",
        interval_ms=900_000,
        source_column_mapping={"close": "signal_bar_close", "bar_time_ms": "signal_bar_time_ms"},
        fixture_family_context_sha256="context-b",
    )

    assert base.key() != changed.key()


def test_fixture_family_context_materialization_uses_backward_asof_without_lookahead(tmp_path) -> None:
    cycle = pd.DataFrame(
        {
            "signal_bar_time_ms": [1000, 2000, 3000],
            "symbol": ["BTCUSDT", "BTCUSDT", "BTCUSDT"],
            "signal_bar_open": [100.0, 101.0, 102.0],
            "signal_bar_high": [101.0, 102.0, 103.0],
            "signal_bar_low": [99.0, 100.0, 101.0],
            "signal_bar_close": [100.5, 101.5, 102.5],
            "signal_bar_volume": [10.0, 11.0, 12.0],
        }
    )
    funding = pd.DataFrame(
        {
            "event_time_ms": [1500, 4000],
            "symbol": ["BTCUSDT", "BTCUSDT"],
            "funding_rate": [0.001, 0.999],
        }
    )
    funding_path = tmp_path / "funding_rate.parquet"
    funding.to_parquet(funding_path, index=False)

    materialized = materialize_fixture_family_context(
        cycle,
        optional_context_families={
            "funding_rate": {
                "path": str(funding_path),
                "sha256": "funding-hash",
                "row_count": len(funding),
                "columns": list(funding.columns),
                "event_time_field": "event_time_ms",
            }
        },
    )

    assert pd.isna(materialized.frame["funding_rate"].iloc[0])
    assert materialized.frame["funding_rate"].tolist()[1:] == [0.001, 0.001]
    assert materialized.evidence["joined_families"] == ["funding_rate"]
    assert materialized.evidence["joined_columns"] == ["funding_rate", "funding_rate_change"]
    assert materialized.evidence["family_records"][0]["matched_row_count"] == 2
    assert materialized.evidence["family_records"][0]["unmatched_row_count"] == 1
    assert materialized.evidence["fixture_family_context_sha256"] == materialized.context_sha256


def test_fixture_family_context_materialization_rejects_duplicate_family_events(tmp_path) -> None:
    cycle = pd.DataFrame(
        {
            "bar_time_ms": [1000, 2000],
            "symbol": ["BTCUSDT", "BTCUSDT"],
            "open": [100.0, 101.0],
            "high": [101.0, 102.0],
            "low": [99.0, 100.0],
            "close": [100.5, 101.5],
            "volume": [10.0, 11.0],
        }
    )
    agg_trade = pd.DataFrame(
        {
            "event_time_ms": [1000, 1000],
            "symbol": ["BTCUSDT", "BTCUSDT"],
            "taker_buy_quote_volume": [6.0, 7.0],
            "quote_volume": [10.0, 10.0],
        }
    )
    agg_trade_path = tmp_path / "agg_trade.parquet"
    agg_trade.to_parquet(agg_trade_path, index=False)

    with pytest.raises(ValueError, match="fixture_context_family_duplicate_events:agg_trade"):
        materialize_fixture_family_context(
            cycle,
            optional_context_families={
                "agg_trade": {
                    "path": str(agg_trade_path),
                    "sha256": "agg-hash",
                    "row_count": len(agg_trade),
                    "columns": list(agg_trade.columns),
                    "event_time_field": "event_time_ms",
                }
            },
        )


def test_materialized_feature_set_replaces_stale_source_feature_columns() -> None:
    frame = build_hmm_knn_sweep_dataset(row_count=120)
    frame["directional_slope_atr"] = 999.0
    frame["wt3d_fast"] = 999.0
    frame["missing_wt3d_fast"] = 0

    materialized = materialize_registered_feature_set(frame, feature_set_id="features_price_trend_vol")

    assert {"bar_time_ms", "open", "high", "low", "close", "symbol", "feature_time_ms"} <= set(materialized.frame.columns)
    assert "directional_slope_atr" in materialized.frame.columns
    assert "wt3d_fast" not in materialized.frame.columns
    assert "missing_wt3d_fast" not in materialized.frame.columns
    assert materialized.frame["directional_slope_atr"].dropna().abs().max() < 999.0
    assert materialized.materialization_scope == "registered_features_merged_with_execution_context"


def test_feature_cache_artifact_round_trips_with_content_hash(tmp_path) -> None:
    frame = build_hmm_knn_sweep_dataset(row_count=120)
    materialized = materialize_registered_feature_set(frame, feature_set_id="features_price_trend_vol")
    identity = FeatureCacheIdentity(
        dataset_sha256="dataset",
        feature_set_id="features_price_trend_vol",
        feature_manifest_sha256=materialized.built.result.manifest.manifest_sha256,
        builder_version=FEATURE_BUILDER_VERSION,
        interval_ms=900_000,
        source_column_mapping=materialized.built.source_column_mapping,
    )

    manifest = write_feature_cache_artifact(
        tmp_path / "cache",
        identity,
        frame=materialized.frame,
        feature_columns=materialized.feature_columns,
        availability_columns=materialized.availability_columns,
        feature_manifest=materialized.built.result.manifest.to_payload(),
        availability_report=materialized.built.result.availability_report.to_payload(),
        materialization_scope=materialized.materialization_scope,
    )
    loaded = load_feature_cache_artifact(tmp_path / "cache", identity)

    assert manifest["feature_cache_key"] == identity.key()
    assert manifest["feature_frame_sha256"]
    assert manifest["feature_manifest"]["manifest_sha256"] == materialized.built.result.manifest.manifest_sha256
    assert loaded is not None
    loaded_frame, loaded_manifest = loaded
    assert len(loaded_frame) == len(materialized.frame)
    assert loaded_manifest["feature_frame_sha256"] == manifest["feature_frame_sha256"]


def test_feature_cache_artifact_rejects_tampered_manifest_identity(tmp_path) -> None:
    frame = build_hmm_knn_sweep_dataset(row_count=120)
    materialized = materialize_registered_feature_set(frame, feature_set_id="features_price_trend_vol")
    identity = FeatureCacheIdentity(
        dataset_sha256="dataset",
        feature_set_id="features_price_trend_vol",
        feature_manifest_sha256=materialized.built.result.manifest.manifest_sha256,
        builder_version=FEATURE_BUILDER_VERSION,
        interval_ms=900_000,
        source_column_mapping=materialized.built.source_column_mapping,
    )

    write_feature_cache_artifact(
        tmp_path / "cache",
        identity,
        frame=materialized.frame,
        feature_columns=materialized.feature_columns,
        availability_columns=materialized.availability_columns,
        feature_manifest=materialized.built.result.manifest.to_payload(),
        availability_report=materialized.built.result.availability_report.to_payload(),
        materialization_scope=materialized.materialization_scope,
    )
    _, manifest_path = feature_cache_paths(tmp_path / "cache", identity)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["feature_set_id"] = "features_full_context_no_wt"
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    assert load_feature_cache_artifact(tmp_path / "cache", identity) is None


def test_split_transform_fits_only_training_rows() -> None:
    frame = build_hmm_knn_sweep_dataset(row_count=120)
    built = build_registered_feature_set(frame, feature_set_id="features_price_trend_vol")
    splits = build_anchored_walk_forward_splits(built.result.frame, min_splits=2, time_column="bar_time_ms")

    result = fit_transform_split_train_only(
        built.result.frame,
        splits[1],
        feature_columns=built.result.manifest.feature_columns,
    )

    assert result.preprocessor.fit_row_count == splits[1].train_end_index - splits[1].train_start_index + 1
    assert len(result.validation_matrix) == splits[1].validation_size_bars
    assert result.to_payload()["promotion_ready"] is False
