from __future__ import annotations

import json
import warnings

import pandas as pd
import pytest

from tradingbotsuite.backtesting.splits import (
    LabelSpec,
    build_anchored_walk_forward_splits,
    build_purged_walk_forward_splits,
)
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
from tradingbotsuite.features.registry import (
    AGGTRADE_ORDERFLOW_COLUMNS,
    CROSS_ASSET_BTC_ETH_V2_COLUMNS,
    LIQUIDATION_CONTEXT_COLUMNS,
    PERP_CONTEXT_V2_COLUMNS,
    PERP_CONTEXT_V3_COLUMNS,
)
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


def test_train_only_split_transform_honors_event_safe_train_indices() -> None:
    start = 1_712_649_600_000
    frame = pd.DataFrame(
        {
            "bar_time_ms": [start + index * 900_000 for index in range(24)],
            "feature": [float(index) for index in range(24)],
            "label_event_end_time_ms": [start + index * 900_000 for index in range(24)],
        }
    )
    frame.loc[2, "label_event_end_time_ms"] = frame.loc[8, "bar_time_ms"]
    frame.loc[4, "label_event_end_time_ms"] = pd.NA
    split = build_purged_walk_forward_splits(
        frame,
        min_splits=2,
        purge_embargo_bars=0,
        label_spec=LabelSpec(event_end_time_column="label_event_end_time_ms", interval_ms=900_000),
    )[0]

    result = fit_transform_split_train_only(frame, split, feature_columns=["feature"])

    assert split.train_indices == (0, 1, 3, 5, 6, 7)
    assert result.preprocessor.fit_row_count == 6
    assert result.train_matrix.index.tolist() == [0, 1, 3, 5, 6, 7]


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


def _price_frame_for_times(times: list[int]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "bar_time_ms": times,
            "symbol": ["BTCUSDT"] * len(times),
            "open": [100.0 + index for index in range(len(times))],
            "high": [101.0 + index for index in range(len(times))],
            "low": [99.0 + index for index in range(len(times))],
            "close": [100.5 + index for index in range(len(times))],
            "volume": [10.0] * len(times),
        }
    )


def test_materialized_feature_set_segments_intentional_bar_gaps_without_cross_gap_returns() -> None:
    interval_ms = 900_000
    first_window = [index * interval_ms for index in range(6)]
    second_window = [10 * interval_ms + index * interval_ms for index in range(6)]
    times = first_window + second_window
    frame = _price_frame_for_times(times)

    with pytest.raises(ValueError, match="bar_time_gaps"):
        materialize_registered_feature_set(frame, feature_set_id="features_price_trend_vol")

    materialized = materialize_registered_feature_set(
        frame,
        feature_set_id="features_price_trend_vol",
        require_continuous=False,
    )

    second_window_first = materialized.frame.loc[materialized.frame["bar_time_ms"] == second_window[0]].iloc[0]
    second_window_second = materialized.frame.loc[materialized.frame["bar_time_ms"] == second_window[1]].iloc[0]
    assert pd.isna(second_window_first["log_return_1"])
    assert pd.notna(second_window_second["log_return_1"])
    assert materialized.materialization_scope == "registered_features_merged_with_execution_context_segmented_on_bar_time_gaps"
    assert "segmented_non_contiguous_bars" in materialized.built.result.completed_bar_validation.quality_flags


def test_materialized_feature_set_rejects_duplicate_bars_inside_intentional_gap_segments() -> None:
    interval_ms = 900_000
    frame = _price_frame_for_times([0, interval_ms, interval_ms, 10 * interval_ms, 11 * interval_ms])

    with pytest.raises(ValueError, match="duplicate_bar_times"):
        materialize_registered_feature_set(
            frame,
            feature_set_id="features_price_trend_vol",
            require_continuous=False,
        )


def test_materialized_feature_set_rejects_short_intervals_when_continuity_is_relaxed() -> None:
    interval_ms = 900_000
    frame = _price_frame_for_times([0, interval_ms, interval_ms + interval_ms // 2, 10 * interval_ms])

    with pytest.raises(ValueError, match="bar_time_short_intervals"):
        materialize_registered_feature_set(
            frame,
            feature_set_id="features_price_trend_vol",
            require_continuous=False,
        )


def test_perp_context_v2_feature_pack_derives_registered_columns() -> None:
    frame = _perp_context_v2_frame(row_count=200)

    built = build_registered_feature_set(frame, feature_set_id="features_perp_context_v2")
    features = built.result.frame

    assert built.result.manifest.feature_columns == PERP_CONTEXT_V2_COLUMNS
    assert set(PERP_CONTEXT_V2_COLUMNS) <= set(features.columns)
    assert features["perp_mark_index_basis"].dropna().iloc[-1] > 0.0
    assert features["perp_premium"].dropna().iloc[-1] > 0.0
    assert features["perp_premium_z_7d"].notna().sum() > 0
    assert features["perp_last_funding_rate"].dropna().iloc[-1] > 0.0
    assert features["oi_delta_1h"].dropna().iloc[-1] > 0.0
    assert features["flow_buy_sell_ratio"].dropna().iloc[-1] > 1.0
    assert features["flow_signed_taker_notional"].dropna().iloc[-1] > 0.0
    assert features["quality_context_missing_count"].eq(0.0).all()
    assert features["quality_provider_backed_all_required"].eq(1.0).all()
    assert features["quality_latest_window_context_only"].eq(1.0).all()


def test_perp_context_v2_keeps_missing_optional_flow_as_nan() -> None:
    frame = _perp_context_v2_frame(row_count=48).drop(
        columns=["quote_volume", "taker_buy_quote_volume", "sell_quote_volume", "primary_signed_imbalance_ratio"]
    )

    built = build_registered_feature_set(frame, feature_set_id="features_perp_context_v2")
    features = built.result.frame

    assert features["flow_buy_sell_ratio"].isna().all()
    assert features["missing_flow_buy_sell_ratio"].eq(1).all()
    assert features["flow_signed_taker_notional"].isna().all()
    assert features["quality_context_missing_count"].eq(0.0).all()
    assert "flow_buy_sell_ratio" in built.result.availability_report.missing_context_columns


def test_perp_context_v2_uses_materialized_backward_asof_without_lookahead(tmp_path) -> None:
    cycle = pd.DataFrame(
        {
            "bar_time_ms": [1000, 2000, 3000],
            "symbol": ["BTCUSDT", "BTCUSDT", "BTCUSDT"],
            "open": [100.0, 101.0, 102.0],
            "high": [101.0, 102.0, 103.0],
            "low": [99.0, 100.0, 101.0],
            "close": [100.5, 101.5, 102.5],
            "volume": [10.0, 11.0, 12.0],
        }
    )
    premium = pd.DataFrame(
        {
            "event_time_ms": [2500],
            "symbol": ["BTCUSDT"],
            "mark_price": [102.0],
            "index_price": [100.0],
        }
    )
    premium_path = tmp_path / "premium_index.parquet"
    premium.to_parquet(premium_path, index=False)

    materialized = materialize_fixture_family_context(
        cycle,
        optional_context_families={
            "premium_index": {
                "path": str(premium_path),
                "sha256": "premium-hash",
                "row_count": len(premium),
                "columns": list(premium.columns),
                "event_time_field": "event_time_ms",
            }
        },
    )
    built = build_registered_feature_set(
        materialized.frame,
        feature_set_id="features_perp_context_v2",
        interval_ms=1000,
    )

    assert pd.isna(built.result.frame["perp_mark_index_basis"].iloc[1])
    assert built.result.frame["perp_mark_index_basis"].iloc[2] == 0.02
    assert built.result.frame["quality_has_premium_gap"].tolist() == [1.0, 1.0, 0.0]


def test_perp_context_v2_preserves_latest_window_fixture_family_provenance(tmp_path) -> None:
    cycle = pd.DataFrame(
        {
            "bar_time_ms": [1000, 2000, 3000],
            "symbol": ["BTCUSDT", "BTCUSDT", "BTCUSDT"],
            "open": [100.0, 101.0, 102.0],
            "high": [101.0, 102.0, 103.0],
            "low": [99.0, 100.0, 101.0],
            "close": [100.5, 101.5, 102.5],
            "volume": [10.0, 11.0, 12.0],
        }
    )
    premium = pd.DataFrame(
        {
            "event_time_ms": [1000],
            "symbol": ["BTCUSDT"],
            "premium_basis_rate": [0.002],
        }
    )
    premium_path = tmp_path / "premium_index.parquet"
    premium.to_parquet(premium_path, index=False)

    materialized = materialize_fixture_family_context(
        cycle,
        optional_context_families={
            "premium_index": {
                "path": str(premium_path),
                "sha256": "premium-hash",
                "row_count": len(premium),
                "columns": list(premium.columns),
                "event_time_field": "event_time_ms",
                "latest_window_only": True,
                "coverage_scope": "latest_window_backfill",
                "retention_policy": {
                    "claim": "not_multi_year_coverage",
                    "scope": "direct_endpoint_latest_window",
                },
            }
        },
    )
    built = build_registered_feature_set(
        materialized.frame,
        feature_set_id="features_perp_context_v2",
        interval_ms=1000,
    )

    record = materialized.evidence["family_records"][0]
    assert record["latest_window_only"] is True
    assert record["coverage_scope"] == "latest_window_backfill"
    assert record["retention_policy"]["claim"] == "not_multi_year_coverage"
    assert materialized.frame["quality_latest_window_context_only_source"].eq(1.0).all()
    assert built.result.frame["quality_latest_window_context_only"].eq(1.0).all()


def test_perp_context_v2_uses_backward_asof_context_for_all_current_families(tmp_path) -> None:
    cycle = pd.DataFrame(
        {
            "bar_time_ms": [1000, 2000, 3000, 4000],
            "symbol": ["BTCUSDT"] * 4,
            "open": [100.0, 101.0, 102.0, 103.0],
            "high": [101.0, 102.0, 103.0, 104.0],
            "low": [99.0, 100.0, 101.0, 102.0],
            "close": [100.5, 101.5, 102.5, 103.5],
            "volume": [10.0, 11.0, 12.0, 13.0],
        }
    )
    families = {
        "funding_rate": pd.DataFrame(
            {
                "event_time_ms": [1500, 4500],
                "symbol": ["BTCUSDT", "BTCUSDT"],
                "funding_rate": [0.001, 0.999],
            }
        ),
        "premium_index": pd.DataFrame(
            {
                "event_time_ms": [1500, 4500],
                "symbol": ["BTCUSDT", "BTCUSDT"],
                "premium_basis_rate": [0.002, 0.999],
            }
        ),
        "open_interest": pd.DataFrame(
            {
                "event_time_ms": [1500, 4500],
                "symbol": ["BTCUSDT", "BTCUSDT"],
                "open_interest_value": [10_000.0, 999_999.0],
            }
        ),
        "agg_trade": pd.DataFrame(
            {
                "event_time_ms": [1500, 4500],
                "symbol": ["BTCUSDT", "BTCUSDT"],
                "quote_volume": [100.0, 999.0],
                "taker_buy_quote_volume": [60.0, 999.0],
                "sell_quote_volume": [40.0, 1.0],
            }
        ),
    }
    payloads = {}
    for family, family_frame in families.items():
        path = tmp_path / f"{family}.parquet"
        family_frame.to_parquet(path, index=False)
        payloads[family] = {
            "path": str(path),
            "sha256": f"{family}-hash",
            "row_count": len(family_frame),
            "columns": list(family_frame.columns),
            "event_time_field": "event_time_ms",
        }

    context = materialize_fixture_family_context(cycle, optional_context_families=payloads)
    built = build_registered_feature_set(context.frame, feature_set_id="features_perp_context_v2", interval_ms=1000)
    features = built.result.frame

    assert context.evidence["asof_direction"] == "backward"
    assert all(record["lookahead_policy"] == "family_event_time_ms_lte_cycle_bar_time_ms" for record in context.evidence["family_records"])
    assert pd.isna(features["perp_last_funding_rate"].iloc[0])
    assert features["perp_last_funding_rate"].iloc[1:4].tolist() == [0.001, 0.001, 0.001]
    assert features["perp_premium"].iloc[1:4].tolist() == [0.002, 0.002, 0.002]
    assert features["oi_notional"].iloc[1:4].tolist() == [10_000.0, 10_000.0, 10_000.0]
    assert features["flow_buy_sell_ratio"].iloc[1:4].tolist() == [1.5, 1.5, 1.5]


def test_perp_context_v3_marks_durable_public_archive_source_candidate_ready(tmp_path) -> None:
    cycle = pd.DataFrame(
        {
            "bar_time_ms": [1000, 2000, 3000, 4000],
            "symbol": ["BTCUSDT"] * 4,
            "open": [100.0, 101.0, 102.0, 103.0],
            "high": [101.0, 102.0, 103.0, 104.0],
            "low": [99.0, 100.0, 101.0, 102.0],
            "close": [100.5, 101.5, 102.5, 103.5],
            "volume": [10.0, 11.0, 12.0, 13.0],
        }
    )
    families = {
        "funding_rate": pd.DataFrame(
            {"event_time_ms": [1000], "symbol": ["BTCUSDT"], "funding_rate": [0.001]}
        ),
        "premium_index": pd.DataFrame(
            {"event_time_ms": [1000], "symbol": ["BTCUSDT"], "premium_basis_rate": [0.002]}
        ),
        "open_interest": pd.DataFrame(
            {"event_time_ms": [1000], "symbol": ["BTCUSDT"], "open_interest_value": [10_000.0]}
        ),
        "agg_trade": pd.DataFrame(
            {
                "event_time_ms": [1000],
                "symbol": ["BTCUSDT"],
                "quote_volume": [100.0],
                "taker_buy_quote_volume": [60.0],
                "sell_quote_volume": [40.0],
            }
        ),
    }
    payloads = {}
    for family, family_frame in families.items():
        path = tmp_path / f"{family}.parquet"
        family_frame.to_parquet(path, index=False)
        payloads[family] = {
            "path": str(path),
            "sha256": f"{family}-hash",
            "row_count": len(family_frame),
            "columns": list(family_frame.columns),
            "event_time_field": "event_time_ms",
            "source_name": "binance_vision",
            "source_access_mode": "public_archive",
            "schema_version": "public_archive_fixture_v1",
            "collector_version": "fixture-collector-v1",
            "ingestor_version": "fixture-ingestor-v1",
            "coverage_scope": "public_archive_partition",
        }

    context = materialize_fixture_family_context(cycle, optional_context_families=payloads)
    built = build_registered_feature_set(context.frame, feature_set_id="features_perp_context_v3", interval_ms=1000)
    features = built.result.frame
    funding_record = context.evidence["family_records"][0]

    assert built.result.manifest.feature_columns == PERP_CONTEXT_V3_COLUMNS
    assert funding_record["source_name"] == "binance_vision"
    assert funding_record["schema_version"] == "public_archive_fixture_v1"
    assert context.frame["quality_context_durable_provider_archive_source"].eq(1.0).all()
    assert context.frame["quality_agg_trade_flow_proxy_not_ofi_source"].eq(1.0).all()
    assert features["quality_provider_backed_all_required"].eq(1.0).all()
    assert features["quality_context_durable_provider_archive"].eq(1.0).all()
    assert features["quality_context_latest_window_diagnostic"].eq(0.0).all()
    assert features["quality_context_missing_unknown"].eq(0.0).all()
    assert features["quality_context_candidate_ready_eligible"].eq(1.0).all()
    assert features["quality_agg_trade_flow_proxy_not_ofi"].eq(1.0).all()


def test_perp_context_v3_marks_latest_window_context_diagnostic_only(tmp_path) -> None:
    cycle = pd.DataFrame(
        {
            "bar_time_ms": [1000, 2000, 3000],
            "symbol": ["BTCUSDT"] * 3,
            "open": [100.0, 101.0, 102.0],
            "high": [101.0, 102.0, 103.0],
            "low": [99.0, 100.0, 101.0],
            "close": [100.5, 101.5, 102.5],
            "volume": [10.0, 11.0, 12.0],
        }
    )
    families = {
        "funding_rate": pd.DataFrame(
            {"event_time_ms": [1000], "symbol": ["BTCUSDT"], "funding_rate": [0.001]}
        ),
        "premium_index": pd.DataFrame(
            {"event_time_ms": [1000], "symbol": ["BTCUSDT"], "premium_basis_rate": [0.002]}
        ),
        "open_interest": pd.DataFrame(
            {"event_time_ms": [1000], "symbol": ["BTCUSDT"], "open_interest_value": [10_000.0]}
        ),
    }
    payloads = {}
    for family, family_frame in families.items():
        path = tmp_path / f"{family}.parquet"
        family_frame.to_parquet(path, index=False)
        payloads[family] = {
            "path": str(path),
            "sha256": f"{family}-hash",
            "row_count": len(family_frame),
            "columns": list(family_frame.columns),
            "event_time_field": "event_time_ms",
            "source_name": "binance_usdm_rest",
            "source_access_mode": "rest_latest_window",
            "latest_window_only": True,
            "coverage_scope": "latest_window_backfill",
            "retention_policy": {"claim": "not_multi_year_coverage"},
        }

    context = materialize_fixture_family_context(cycle, optional_context_families=payloads)
    built = build_registered_feature_set(context.frame, feature_set_id="features_perp_context_v3", interval_ms=1000)
    features = built.result.frame

    assert context.frame["quality_context_latest_window_diagnostic_source"].eq(1.0).all()
    assert features["quality_provider_backed_all_required"].eq(1.0).all()
    assert features["quality_context_latest_window_diagnostic"].eq(1.0).all()
    assert features["quality_context_missing_unknown"].eq(0.0).all()
    assert features["quality_context_candidate_ready_eligible"].eq(0.0).all()


def test_aggtrade_orderflow_v1_derives_trade_flow_proxy_columns() -> None:
    frame = _perp_context_v2_frame(row_count=240)
    frame["agg_trade_count"] = [20.0 + (index % 5) for index in range(len(frame))]
    frame["agg_large_trade_count"] = 3.0
    frame["agg_large_buy_count"] = 2.0
    frame["agg_large_sell_count"] = 1.0
    frame["quality_agg_trade_flow_proxy_not_ofi_source"] = 1.0

    built = build_registered_feature_set(frame, feature_set_id="features_aggtrade_orderflow_v1")
    features = built.result.frame

    assert built.result.manifest.feature_columns == AGGTRADE_ORDERFLOW_COLUMNS
    assert set(AGGTRADE_ORDERFLOW_COLUMNS) <= set(features.columns)
    assert features["agg_taker_buy_quote_share"].dropna().iloc[-1] == pytest.approx(0.6)
    assert features["agg_signed_quote_imbalance"].dropna().iloc[-1] == pytest.approx(0.2)
    assert features["agg_sqrt_signed_quote_imbalance"].dropna().iloc[-1] == pytest.approx(0.2**0.5)
    assert features["agg_cvd_slope"].notna().sum() > 0
    assert features["agg_trade_count_zscore"].notna().sum() > 0
    assert features["agg_quote_volume_zscore"].notna().sum() > 0
    assert features["agg_large_trade_side_imbalance"].dropna().iloc[-1] == pytest.approx(1.0 / 3.0)
    assert features["agg_flow_burst_score"].notna().sum() > 0
    assert features["agg_sweep_proxy"].notna().sum() > 0
    assert features["quality_aggtrade_context_missing"].eq(0.0).all()
    assert features["quality_aggtrade_source_present"].eq(1.0).all()
    assert features["quality_aggtrade_flow_proxy_not_ofi"].eq(1.0).all()
    assert "top_of_book_imbalance" not in built.result.manifest.feature_columns


def test_price_perp_aggflow_no_wt_builds_wide_missingness_without_fragmentation_warning() -> None:
    frame = _perp_context_v2_frame(row_count=240)
    frame["agg_trade_count"] = [20.0 + (index % 5) for index in range(len(frame))]
    frame["agg_large_trade_count"] = 3.0
    frame["agg_large_buy_count"] = 2.0
    frame["agg_large_sell_count"] = 1.0
    frame["quality_agg_trade_flow_proxy_not_ofi_source"] = 1.0

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        built = build_registered_feature_set(frame, feature_set_id="features_price_perp_aggflow_no_wt")

    performance_warnings = [
        warning for warning in caught if issubclass(warning.category, pd.errors.PerformanceWarning)
    ]
    features = built.result.frame

    assert performance_warnings == []
    assert "missing_agg_trade_count_zscore" in features.columns
    assert "missing_directional_slope_atr" in features.columns
    assert "missing_volatility_shock_zscore" in features.columns
    assert set(built.result.manifest.feature_columns) <= set(features.columns)


def test_aggtrade_orderflow_v1_uses_materialized_agg_trade_without_depth_claim(tmp_path) -> None:
    cycle = pd.DataFrame(
        {
            "bar_time_ms": [1000, 2000, 3000],
            "symbol": ["BTCUSDT"] * 3,
            "open": [100.0, 101.0, 102.0],
            "high": [101.0, 102.0, 103.0],
            "low": [99.0, 100.0, 101.0],
            "close": [100.5, 101.5, 102.5],
            "volume": [10.0, 11.0, 12.0],
        }
    )
    agg_trade = pd.DataFrame(
        {
            "event_time_ms": [1000, 2000],
            "symbol": ["BTCUSDT", "BTCUSDT"],
            "quote_volume": [100.0, 120.0],
            "taker_buy_quote_volume": [60.0, 48.0],
            "sell_quote_volume": [40.0, 72.0],
            "agg_trade_count": [10.0, 12.0],
            "top_of_book_imbalance": [0.99, -0.99],
        }
    )
    agg_trade_path = tmp_path / "agg_trade.parquet"
    agg_trade.to_parquet(agg_trade_path, index=False)

    context = materialize_fixture_family_context(
        cycle,
        optional_context_families={
            "agg_trade": {
                "path": str(agg_trade_path),
                "sha256": "agg-hash",
                "row_count": len(agg_trade),
                "columns": list(agg_trade.columns),
                "event_time_field": "event_time_ms",
                "source_name": "binance_vision",
                "source_access_mode": "public_archive",
                "coverage_scope": "public_archive_partition",
            }
        },
    )
    built = build_registered_feature_set(
        context.frame,
        feature_set_id="features_aggtrade_orderflow_v1",
        interval_ms=1000,
    )
    features = built.result.frame

    assert "top_of_book_imbalance" in context.frame.columns
    assert "top_of_book_imbalance" not in features.columns
    assert features["agg_taker_buy_quote_share"].tolist() == [0.6, 0.4, 0.4]
    assert features["agg_signed_quote_imbalance"].tolist() == [0.2, -0.2, -0.2]
    assert features["quality_aggtrade_flow_proxy_not_ofi"].eq(1.0).all()


def test_cross_asset_btc_eth_v2_is_point_in_time_and_future_rows_do_not_leak() -> None:
    frame = _cross_asset_btc_eth_frame(row_count=140)
    baseline = build_registered_feature_set(
        frame,
        feature_set_id="features_cross_asset_btc_eth_v2",
        interval_ms=900_000,
    ).result.frame

    mutated = frame.copy()
    mutated.loc[120:, "btc_close"] = 1_000_000.0
    mutated.loc[120:, "eth_close"] = 100_000.0
    changed = build_registered_feature_set(
        mutated,
        feature_set_id="features_cross_asset_btc_eth_v2",
        interval_ms=900_000,
    ).result.frame

    stable_columns = [
        "btc_return_1",
        "eth_return_1",
        "eth_beta_to_btc_96",
        "eth_btc_residual_return_1",
        "eth_btc_residual_z_96",
        "ethbtc_trend_96",
        "btc_eth_corr_96",
        "funding_spread_z_96",
        "oi_delta_spread_z_96",
        "quality_cross_asset_point_in_time_join",
    ]
    pd.testing.assert_frame_equal(
        baseline.loc[:90, stable_columns],
        changed.loc[:90, stable_columns],
        check_dtype=False,
        check_exact=False,
        rtol=1e-12,
        atol=1e-12,
    )
    assert baseline["quality_cross_asset_future_alignment_risk"].eq(0.0).all()
    assert baseline["quality_cross_asset_matched_interval"].eq(1.0).all()
    assert baseline["quality_cross_asset_point_in_time_join"].eq(1.0).all()
    assert baseline["quality_cross_asset_candidate_ready_eligible"].eq(1.0).all()
    assert baseline["eth_btc_residual_z_96"].notna().sum() > 0


def test_cross_asset_btc_eth_v2_flags_future_alignment_and_missing_context() -> None:
    frame = _cross_asset_btc_eth_frame(row_count=120)
    frame.loc[40:45, "eth_source_time_ms"] = frame.loc[40:45, "bar_time_ms"] + 1_800_000
    frame = frame.drop(columns=["eth_funding_rate", "btc_oi_delta_1h", "eth_oi_delta_1h"])

    built = build_registered_feature_set(
        frame,
        feature_set_id="features_cross_asset_btc_eth_v2",
        interval_ms=900_000,
    )
    features = built.result.frame

    assert built.result.manifest.feature_columns == CROSS_ASSET_BTC_ETH_V2_COLUMNS
    assert features.loc[40:45, "quality_cross_asset_future_alignment_risk"].eq(1.0).all()
    assert features.loc[40:45, "quality_cross_asset_point_in_time_join"].eq(0.0).all()
    assert features.loc[40:45, "quality_cross_asset_candidate_ready_eligible"].eq(0.0).all()
    assert features["funding_spread"].isna().all()
    assert features["oi_delta_spread_1h"].isna().all()
    assert features["quality_cross_asset_missing_funding_context"].eq(1.0).all()
    assert features["quality_cross_asset_missing_oi_context"].eq(1.0).all()
    assert "funding_spread" in built.result.availability_report.missing_context_columns
    assert "oi_delta_spread_1h" in built.result.availability_report.missing_context_columns


def test_liquidation_context_materialization_uses_window_without_carryforward(tmp_path) -> None:
    cycle = pd.DataFrame(
        {
            "bar_time_ms": [1_000, 2_000, 3_604_000],
            "symbol": ["BTCUSDT", "BTCUSDT", "BTCUSDT"],
            "open": [100.0, 101.0, 102.0],
            "high": [101.0, 102.0, 103.0],
            "low": [99.0, 100.0, 101.0],
            "close": [100.5, 101.5, 102.5],
            "volume": [10.0, 11.0, 12.0],
        }
    )
    liquidation = pd.DataFrame(
        {
            "event_time_ms": [1_500],
            "symbol": ["BTCUSDT"],
            "liquidation_event_count": [2.0],
            "liquidation_quote_notional": [300.0],
            "liquidation_buy_notional": [100.0],
            "liquidation_sell_notional": [200.0],
            "liquidation_quantity": [3.0],
        }
    )
    liquidation_path = tmp_path / "liquidation.parquet"
    liquidation.to_parquet(liquidation_path, index=False)

    context = materialize_fixture_family_context(
        cycle,
        optional_context_families={
            "liquidation": {
                "path": str(liquidation_path),
                "sha256": "liquidation-hash",
                "row_count": len(liquidation),
                "columns": list(liquidation.columns),
                "event_time_field": "event_time_ms",
            }
        },
    )

    assert pd.isna(context.frame["liquidation_event_count_1h"].iloc[0])
    assert context.frame["liquidation_event_count_1h"].iloc[1] == 2.0
    assert pd.isna(context.frame["liquidation_event_count_1h"].iloc[2])
    assert context.frame["liquidation_quote_notional_1h"].iloc[1] == 300.0
    assert context.frame["liquidation_side_imbalance_1h"].iloc[1] == pytest.approx((100.0 - 200.0) / 300.0)
    record = context.evidence["family_records"][0]
    assert record["family"] == "liquidation"
    assert record["asof_direction"] == "windowed_backward"
    assert record["aggregation_window_ms"] == 3_600_000
    assert record["matched_row_count"] == 1


def test_liquidation_context_v1_feature_pack_derives_registered_columns(tmp_path) -> None:
    cycle = pd.DataFrame(
        {
            "bar_time_ms": [1_000 + (index * 900_000) for index in range(240)],
            "symbol": ["BTCUSDT"] * 240,
            "open": [100.0 + index * 0.1 for index in range(240)],
            "high": [101.0 + index * 0.1 for index in range(240)],
            "low": [99.0 + index * 0.1 for index in range(240)],
            "close": [100.5 + index * 0.1 for index in range(240)],
            "volume": [10.0 + index for index in range(240)],
        }
    )
    liquidation = pd.DataFrame(
        {
            "event_time_ms": [int(cycle["bar_time_ms"].iloc[index]) for index in range(32, 240, 16)],
            "symbol": ["BTCUSDT"] * 13,
            "liquidation_event_count": [1.0 + (index % 3) for index in range(13)],
            "liquidation_quote_notional": [1_000.0 + index * 250.0 for index in range(13)],
            "liquidation_buy_notional": [350.0 + index * 100.0 for index in range(13)],
            "liquidation_sell_notional": [650.0 + index * 150.0 for index in range(13)],
            "liquidation_quantity": [10.0 + index for index in range(13)],
        }
    )
    liquidation_path = tmp_path / "liquidation.parquet"
    liquidation.to_parquet(liquidation_path, index=False)

    context = materialize_fixture_family_context(
        cycle,
        optional_context_families={
            "liquidation": {
                "path": str(liquidation_path),
                "sha256": "liquidation-hash",
                "row_count": len(liquidation),
                "columns": list(liquidation.columns),
                "event_time_field": "event_time_ms",
                "latest_window_only": True,
                "coverage_scope": "latest_window_backfill",
                "retention_policy": {"claim": "not_multi_year_coverage"},
            }
        },
    )
    built = build_registered_feature_set(
        context.frame,
        feature_set_id="features_liquidation_context_v1",
        interval_ms=900_000,
    )
    features = built.result.frame

    assert built.result.manifest.feature_columns == LIQUIDATION_CONTEXT_COLUMNS
    assert set(LIQUIDATION_CONTEXT_COLUMNS) <= set(features.columns)
    assert features["liq_event_count_1h"].notna().any()
    assert features["liq_total_notional_1h"].notna().any()
    assert features["liq_net_notional_1h"].dropna().lt(0.0).any()
    assert features["liq_imbalance_ratio_1h"].dropna().between(-1.0, 1.0).all()
    assert features["liq_total_notional_z_7d"].notna().sum() > 0
    assert features["liq_time_since_last_event_h"].dropna().ge(0.0).all()
    assert features["quality_has_liquidation_gap"].isin([0.0, 1.0]).all()
    assert features["quality_liquidation_provider_backed"].max() == 1.0
    assert features["quality_liquidation_latest_window_context_only"].eq(1.0).all()


def test_liquidation_context_v1_uses_notional_weighted_side_imbalance(tmp_path) -> None:
    cycle = pd.DataFrame(
        {
            "bar_time_ms": [1_000, 2_000, 3_000],
            "symbol": ["BTCUSDT", "BTCUSDT", "BTCUSDT"],
            "open": [100.0, 101.0, 102.0],
            "high": [101.0, 102.0, 103.0],
            "low": [99.0, 100.0, 101.0],
            "close": [100.5, 101.5, 102.5],
            "volume": [10.0, 11.0, 12.0],
        }
    )
    liquidation = pd.DataFrame(
        {
            "event_time_ms": [1_500, 2_500],
            "symbol": ["BTCUSDT", "BTCUSDT"],
            "liquidation_event_count": [1.0, 1.0],
            "liquidation_quote_notional": [100.0, 300.0],
            "liquidation_side_imbalance": [-1.0, 1.0],
        }
    )
    liquidation_path = tmp_path / "liquidation.parquet"
    liquidation.to_parquet(liquidation_path, index=False)
    context = materialize_fixture_family_context(
        cycle,
        optional_context_families={
            "liquidation": {
                "path": str(liquidation_path),
                "sha256": "liquidation-hash",
                "row_count": len(liquidation),
                "columns": list(liquidation.columns),
                "event_time_field": "event_time_ms",
            }
        },
    )
    built = build_registered_feature_set(
        context.frame,
        feature_set_id="features_liquidation_context_v1",
        interval_ms=1000,
    )
    features = built.result.frame

    assert features["liq_total_notional_1h"].iloc[2] == 400.0
    assert features["liq_imbalance_ratio_1h"].iloc[2] == pytest.approx((300.0 - 100.0) / 400.0)
    assert features["liq_net_notional_1h"].iloc[2] == pytest.approx(200.0)
    assert features["liq_buy_notional_1h"].isna().all()
    assert features["liq_sell_notional_1h"].isna().all()


def test_required_liquidation_context_without_supported_measure_is_rejected(tmp_path) -> None:
    cycle = pd.DataFrame(
        {
            "bar_time_ms": [1_000, 2_000],
            "symbol": ["BTCUSDT", "BTCUSDT"],
            "open": [100.0, 101.0],
            "high": [101.0, 102.0],
            "low": [99.0, 100.0],
            "close": [100.5, 101.5],
            "volume": [10.0, 11.0],
        }
    )
    liquidation = pd.DataFrame(
        {
            "event_time_ms": [1_500],
            "symbol": ["BTCUSDT"],
        }
    )
    liquidation_path = tmp_path / "liquidation.parquet"
    liquidation.to_parquet(liquidation_path, index=False)

    with pytest.raises(ValueError, match="fixture_context_family_no_supported_columns:liquidation"):
        materialize_fixture_family_context(
            cycle,
            optional_context_families={
                "liquidation": {
                    "path": str(liquidation_path),
                    "sha256": "liquidation-hash",
                    "row_count": len(liquidation),
                    "columns": list(liquidation.columns),
                    "event_time_field": "event_time_ms",
                    "required": True,
                }
            },
        )


def test_liquidation_context_feature_cache_identity_includes_context_family_hash(tmp_path) -> None:
    frame = _perp_context_v2_frame(row_count=48)
    liquidation = pd.DataFrame(
        {
            "event_time_ms": [int(frame["bar_time_ms"].iloc[4])],
            "symbol": ["BTCUSDT"],
            "liquidation_event_count": [1.0],
            "liquidation_quote_notional": [1_000.0],
        }
    )
    liquidation_path = tmp_path / "liquidation.parquet"
    liquidation.to_parquet(liquidation_path, index=False)
    context = materialize_fixture_family_context(
        frame,
        optional_context_families={
            "liquidation": {
                "path": str(liquidation_path),
                "sha256": "liquidation-hash",
                "row_count": len(liquidation),
                "columns": list(liquidation.columns),
                "event_time_field": "event_time_ms",
            }
        },
    )
    materialized = materialize_registered_feature_set(context.frame, feature_set_id="features_liquidation_context_v1")
    identity = FeatureCacheIdentity(
        dataset_sha256="dataset",
        feature_set_id="features_liquidation_context_v1",
        feature_manifest_sha256=materialized.built.result.manifest.manifest_sha256,
        builder_version=FEATURE_BUILDER_VERSION,
        interval_ms=900_000,
        source_column_mapping=materialized.built.source_column_mapping,
        fixture_family_context_sha256=context.context_sha256,
    )
    changed = FeatureCacheIdentity(
        dataset_sha256="dataset",
        feature_set_id="features_liquidation_context_v1",
        feature_manifest_sha256=materialized.built.result.manifest.manifest_sha256,
        builder_version=FEATURE_BUILDER_VERSION,
        interval_ms=900_000,
        source_column_mapping=materialized.built.source_column_mapping,
        fixture_family_context_sha256="different-context",
    )

    assert identity.key() != changed.key()


def test_perp_context_v2_feature_cache_identity_includes_context_family_hash(tmp_path) -> None:
    frame = _perp_context_v2_frame(row_count=48)
    context = materialize_fixture_family_context(frame, optional_context_families={})
    materialized = materialize_registered_feature_set(context.frame, feature_set_id="features_perp_context_v2")
    identity = FeatureCacheIdentity(
        dataset_sha256="dataset",
        feature_set_id="features_perp_context_v2",
        feature_manifest_sha256=materialized.built.result.manifest.manifest_sha256,
        builder_version=FEATURE_BUILDER_VERSION,
        interval_ms=900_000,
        source_column_mapping=materialized.built.source_column_mapping,
        fixture_family_context_sha256=context.context_sha256,
    )
    changed = FeatureCacheIdentity(
        dataset_sha256="dataset",
        feature_set_id="features_perp_context_v2",
        feature_manifest_sha256=materialized.built.result.manifest.manifest_sha256,
        builder_version=FEATURE_BUILDER_VERSION,
        interval_ms=900_000,
        source_column_mapping=materialized.built.source_column_mapping,
        fixture_family_context_sha256="different-context",
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
        fixture_family_context=context.evidence,
    )

    assert identity.key() != changed.key()
    assert manifest["fixture_family_context_sha256"] == context.context_sha256
    assert manifest["fixture_family_context"]["fixture_family_context_sha256"] == context.context_sha256
    assert load_feature_cache_artifact(tmp_path / "cache", identity) is not None
    assert load_feature_cache_artifact(tmp_path / "cache", changed) is None


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


def _perp_context_v2_frame(*, row_count: int) -> pd.DataFrame:
    rows = []
    start_ms = 1_712_649_600_000
    for index in range(row_count):
        mark_price = 100.0 + index * 0.1
        index_price = 99.5 + index * 0.08
        quote_volume = 1_000.0 + index
        taker_buy_quote = quote_volume * 0.6
        sell_quote = quote_volume - taker_buy_quote
        rows.append(
            {
                "bar_time_ms": start_ms + index * 900_000,
                "symbol": "BTCUSDT",
                "open": mark_price - 0.2,
                "high": mark_price + 0.5,
                "low": mark_price - 0.5,
                "close": mark_price,
                "volume": 10.0 + index,
                "mark_price": mark_price,
                "index_price": index_price,
                "premium_basis_rate": (mark_price - index_price) / index_price,
                "funding_rate": 0.0001 + index * 0.000001,
                "open_interest": 10_000.0 + index * 5.0,
                "open_interest_value": 1_000_000.0 + index * 250.0,
                "quote_volume": quote_volume,
                "taker_buy_quote_volume": taker_buy_quote,
                "sell_quote_volume": sell_quote,
                "primary_signed_imbalance_ratio": (taker_buy_quote - sell_quote) / quote_volume,
                "quality_latest_window_context_only_source": 1.0,
            }
        )
    return pd.DataFrame(rows)


def _cross_asset_btc_eth_frame(*, row_count: int) -> pd.DataFrame:
    rows = []
    start_ms = 1_712_649_600_000
    for index in range(row_count):
        bar_time_ms = start_ms + index * 900_000
        btc_close = 70_000.0 + index * 20.0 + (index % 7) * 5.0
        eth_close = 3_500.0 + index * 2.2 + (index % 5) * 1.5
        rows.append(
            {
                "bar_time_ms": bar_time_ms,
                "symbol": "ETHUSDT",
                "open": eth_close - 1.0,
                "high": eth_close + 2.0,
                "low": eth_close - 2.0,
                "close": eth_close,
                "volume": 100.0 + index,
                "btc_close": btc_close,
                "eth_close": eth_close,
                "btc_source_time_ms": bar_time_ms,
                "eth_source_time_ms": bar_time_ms,
                "btc_quality_context_durable_provider_archive": 1.0,
                "eth_quality_context_durable_provider_archive": 1.0,
                "btc_funding_rate": 0.00005 + index * 0.0000001,
                "eth_funding_rate": 0.00007 + index * 0.0000002,
                "btc_oi_delta_1h": 1_000.0 + index,
                "eth_oi_delta_1h": 900.0 + index * 1.5,
            }
        )
    return pd.DataFrame(rows)
