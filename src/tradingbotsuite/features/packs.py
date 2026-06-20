from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd

from tradingbotsuite.features.alignment import (
    CompletedBarValidation,
    prepare_completed_bar_feature_input,
)
from tradingbotsuite.features.registry import (
    AGGTRADE_ORDERFLOW_COLUMNS,
    CALENDAR_COLUMNS,
    CROSS_ASSET_BTC_ETH_V2_COLUMNS,
    CROSS_ASSET_COLUMNS,
    LIQUIDATION_CONTEXT_COLUMNS,
    MICROSTRUCTURE_COLUMNS,
    PERP_CONTEXT_COLUMNS,
    PERP_CONTEXT_V2_COLUMNS,
    PERP_CONTEXT_V3_COLUMNS,
    PRICE_PATH_COLUMNS,
    TREND_CHOP_COLUMNS,
    VOLATILITY_COLUMNS,
    WT3D_COLUMNS,
    FeatureAvailabilityReport,
    FeatureManifest,
    build_feature_manifest,
)


@dataclass(frozen=True, slots=True)
class FeatureFrameResult:
    frame: pd.DataFrame
    manifest: FeatureManifest
    availability_report: FeatureAvailabilityReport
    completed_bar_validation: CompletedBarValidation


def build_feature_frame(
    bars: pd.DataFrame,
    *,
    feature_set_id: str,
    feature_packs: Sequence[str],
    interval_ms: int,
    bar_time_column: str = "bar_time_ms",
    current_time_ms: int | None = None,
    price_column: str | None = None,
    require_continuous: bool = True,
) -> FeatureFrameResult:
    """Build a completed-bar, point-in-time feature frame for registered packs."""

    prepared, validation = prepare_completed_bar_feature_input(
        bars,
        bar_time_column=bar_time_column,
        interval_ms=interval_ms,
        current_time_ms=current_time_ms,
        require_continuous=require_continuous,
    )
    manifest = build_feature_manifest(
        feature_set_id=feature_set_id,
        feature_packs=tuple(feature_packs),
        tests=(
            "tests/contracts/test_feature_contracts.py",
            "tests/tradingbotsuite/test_feature_alignment.py",
        ),
    )
    feature_parts = [prepared.loc[:, [bar_time_column, "feature_time_ms"]]]
    for pack_id in feature_packs:
        pack_frame = _build_pack(prepared, pack_id=pack_id, price_column=price_column, interval_ms=interval_ms)
        feature_parts.append(pack_frame)

    features = pd.concat(feature_parts, axis=1)
    missing_feature_parts: list[pd.Series] = []
    missing_parts: list[pd.Series] = []
    for column in manifest.feature_columns:
        if column not in features.columns:
            feature_column = pd.Series(np.nan, index=features.index, name=column)
            missing_feature_parts.append(feature_column)
        else:
            feature_column = features[column]
        missing_parts.append(feature_column.isna().astype(int).rename(f"missing_{column}"))
    if missing_feature_parts:
        features = pd.concat([features, pd.concat(missing_feature_parts, axis=1)], axis=1)
    if missing_parts:
        features = pd.concat([features, pd.concat(missing_parts, axis=1)], axis=1)
    features = features.copy()

    availability_report = _availability_report(features, manifest)
    return FeatureFrameResult(
        frame=features,
        manifest=manifest,
        availability_report=availability_report,
        completed_bar_validation=validation,
    )


def _build_pack(frame: pd.DataFrame, *, pack_id: str, price_column: str | None, interval_ms: int) -> pd.DataFrame:
    if pack_id == "price_path_v1":
        return _price_path_features(frame, price_column=price_column)
    if pack_id == "trend_chop_v1":
        return _trend_chop_features(frame, price_column=price_column)
    if pack_id == "volatility_v1":
        return _volatility_features(frame, price_column=price_column)
    if pack_id == "perp_context_v1":
        return _context_features(frame, PERP_CONTEXT_COLUMNS)
    if pack_id == "perp_context_v2":
        return _perp_context_v2_features(frame, interval_ms=interval_ms)
    if pack_id == "perp_context_v3":
        return _perp_context_v3_features(frame, interval_ms=interval_ms)
    if pack_id == "aggtrade_orderflow_v1":
        return _aggtrade_orderflow_features(frame, interval_ms=interval_ms)
    if pack_id == "liquidation_context_v1":
        return _liquidation_context_features(frame, interval_ms=interval_ms)
    if pack_id == "microstructure_context_v1":
        return _context_features(frame, MICROSTRUCTURE_COLUMNS)
    if pack_id == "wt3d_v1":
        return _wt3d_features(frame, price_column=price_column)
    if pack_id == "cross_asset_v1":
        return _cross_asset_features(frame)
    if pack_id == "cross_asset_btc_eth_v2":
        return _cross_asset_btc_eth_v2_features(frame, interval_ms=interval_ms)
    if pack_id == "calendar_v1":
        return _calendar_features(frame)
    raise ValueError(f"unknown_feature_pack:{pack_id}")


def _price_path_features(frame: pd.DataFrame, *, price_column: str | None) -> pd.DataFrame:
    price = _price_series(frame, price_column=price_column)
    log_price = np.log(price.where(price > 0))
    result = pd.DataFrame(index=frame.index)
    result["log_return_1"] = log_price.diff(1)
    result["log_return_4"] = log_price.diff(4)
    result["log_return_16"] = log_price.diff(16)
    result["momentum_4"] = price.pct_change(4)
    result["momentum_16"] = price.pct_change(16)
    rolling_mean = price.rolling(20, min_periods=20).mean()
    rolling_std = price.rolling(20, min_periods=20).std(ddof=0)
    result["path_zscore_20"] = (price - rolling_mean) / rolling_std.replace(0.0, np.nan)
    result["trend_slope_20"] = _rolling_slope(price, 20)
    return result.loc[:, PRICE_PATH_COLUMNS]


def _trend_chop_features(frame: pd.DataFrame, *, price_column: str | None) -> pd.DataFrame:
    price = _price_series(frame, price_column=price_column)
    high = _numeric_or_default(frame, "high", price)
    low = _numeric_or_default(frame, "low", price)
    atr = _true_range(high, low, price).rolling(14, min_periods=14).mean()
    result = pd.DataFrame(index=frame.index)
    net_change = (price - price.shift(24)).abs()
    path = price.diff().abs().rolling(24, min_periods=24).sum()
    result["efficiency_ratio"] = net_change / path.replace(0.0, np.nan)
    range_width_raw = high.rolling(24, min_periods=24).max() - low.rolling(24, min_periods=24).min()
    result["range_width"] = range_width_raw / price.replace(0.0, np.nan)
    tr_sum = _true_range(high, low, price).rolling(14, min_periods=14).sum()
    high_low_range = (high.rolling(14, min_periods=14).max() - low.rolling(14, min_periods=14).min()).replace(0.0, np.nan)
    result["choppiness"] = 100.0 * np.log10(tr_sum / high_low_range) / math.log10(14)
    result["directional_slope_atr"] = _rolling_slope(price, 24) * 24.0 / atr.replace(0.0, np.nan)
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    plus_di = 100.0 * plus_dm.rolling(14, min_periods=14).sum() / atr.replace(0.0, np.nan)
    minus_di = 100.0 * minus_dm.rolling(14, min_periods=14).sum() / atr.replace(0.0, np.nan)
    result["directional_di_spread"] = plus_di - minus_di
    result["hurst_proxy"] = price.rolling(64, min_periods=64).apply(_hurst_proxy, raw=True)
    result["adx_proxy"] = result["directional_di_spread"].abs().rolling(14, min_periods=14).mean()
    return result.loc[:, TREND_CHOP_COLUMNS]


def _volatility_features(frame: pd.DataFrame, *, price_column: str | None) -> pd.DataFrame:
    price = _price_series(frame, price_column=price_column)
    high = _numeric_or_default(frame, "high", price)
    low = _numeric_or_default(frame, "low", price)
    returns = np.log(price.where(price > 0)).diff()
    atr = _true_range(high, low, price).rolling(14, min_periods=14).mean()
    realized_vol = returns.rolling(20, min_periods=20).std(ddof=0)
    result = pd.DataFrame(index=frame.index)
    result["atr"] = atr
    result["realized_volatility"] = realized_vol
    result["atr_percentile"] = atr.rolling(96, min_periods=20).apply(_last_value_percentile, raw=True)
    vol_mean = realized_vol.rolling(20, min_periods=20).mean()
    vol_std = realized_vol.rolling(20, min_periods=20).std(ddof=0)
    result["volatility_shock_zscore"] = (realized_vol - vol_mean) / vol_std.replace(0.0, np.nan)
    result["vol_of_vol"] = realized_vol.rolling(20, min_periods=20).std(ddof=0)
    return result.loc[:, VOLATILITY_COLUMNS]


def _context_features(frame: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    result = pd.DataFrame(index=frame.index)
    for column in columns:
        if column in frame.columns:
            result[column] = pd.to_numeric(frame[column], errors="coerce")
        else:
            result[column] = np.nan
    return result


def _perp_context_v2_features(frame: pd.DataFrame, *, interval_ms: int) -> pd.DataFrame:
    result = pd.DataFrame(index=frame.index)
    row_count = len(frame)
    bars_1h = _bars_for_duration(interval_ms=interval_ms, duration_ms=3_600_000)
    bars_8h = _bars_for_duration(interval_ms=interval_ms, duration_ms=8 * 3_600_000)
    bars_7d = _bars_for_duration(interval_ms=interval_ms, duration_ms=7 * 24 * 3_600_000)

    mark_price = _optional_numeric(frame, "mark_price")
    index_price = _optional_numeric(frame, "index_price")
    basis_bps = _optional_numeric(frame, "basis_bps")
    premium_basis_rate = _first_available_numeric(frame, ("premium_basis_rate", "premium_close", "premium_index"))
    funding_rate = _optional_numeric(frame, "funding_rate")
    open_interest = _optional_numeric(frame, "open_interest")
    oi_notional = _first_available_numeric(frame, ("open_interest_value", "open_interest_value_usd", "oi_notional"))
    signed_ratio = _first_available_numeric(frame, ("primary_signed_imbalance_ratio", "signed_imbalance_ratio"))
    quote_volume = _optional_numeric(frame, "quote_volume")
    taker_buy_quote = _optional_numeric(frame, "taker_buy_quote_volume")
    sell_quote = _optional_numeric(frame, "sell_quote_volume")

    if premium_basis_rate is None and mark_price is not None and index_price is not None:
        premium_basis_rate = (mark_price - index_price) / index_price.replace(0.0, np.nan)
    if premium_basis_rate is None and basis_bps is not None:
        premium_basis_rate = basis_bps / 10_000.0
    if oi_notional is None and open_interest is not None:
        close = _optional_numeric(frame, "close")
        oi_notional = open_interest * close if close is not None else open_interest

    result["perp_mark_index_basis"] = premium_basis_rate if premium_basis_rate is not None else _nan_series(frame)
    result["perp_premium"] = premium_basis_rate if premium_basis_rate is not None else _nan_series(frame)
    result["perp_premium_z_7d"] = _rolling_zscore(result["perp_premium"], bars_7d)
    result["perp_premium_slope_8h"] = _rolling_slope(result["perp_premium"], bars_8h)
    result["perp_last_funding_rate"] = funding_rate if funding_rate is not None else _nan_series(frame)
    result["perp_funding_z_7d"] = _rolling_zscore(result["perp_last_funding_rate"], bars_7d)
    funding_change = _optional_numeric(frame, "funding_rate_change")
    result["perp_funding_momentum"] = funding_change if funding_change is not None else result["perp_last_funding_rate"].diff(bars_8h)
    result["cal_time_since_last_funding_h"] = _hours_since_last_funding(frame, funding_rate is not None)
    result["cal_time_to_next_funding_h"] = _hours_to_next_funding(frame)
    result["oi_notional"] = oi_notional if oi_notional is not None else _nan_series(frame)
    result["oi_delta_1h"] = result["oi_notional"].diff(bars_1h)
    result["oi_delta_z_7d"] = _rolling_zscore(result["oi_delta_1h"], bars_7d)
    result["oi_volume_ratio"] = _oi_volume_ratio(result["oi_notional"], frame)

    result["flow_buy_sell_ratio"] = _flow_buy_sell_ratio(frame, taker_buy_quote, sell_quote, quote_volume)
    result["flow_signed_taker_notional"] = _flow_signed_notional(frame, signed_ratio, quote_volume, taker_buy_quote, sell_quote)
    result["flow_signed_taker_z_7d"] = _rolling_zscore(result["flow_signed_taker_notional"], bars_7d)

    funding_present = _source_present(frame, ("funding_rate", "last_funding_rate"))
    premium_present = _source_present(frame, ("premium_basis_rate", "premium_index", "premium_close", "mark_price", "index_price"))
    oi_present = _source_present(frame, ("open_interest", "open_interest_value", "open_interest_value_usd"))
    latest_window_only = _optional_numeric(frame, "quality_latest_window_context_only_source")
    if latest_window_only is None:
        latest_window_only = _optional_numeric(frame, "latest_window_only")

    missing_required = pd.concat(
        [
            (~funding_present).astype(int),
            (~premium_present).astype(int),
            (~oi_present).astype(int),
        ],
        axis=1,
    )
    result["quality_context_missing_count"] = missing_required.sum(axis=1).astype(float)
    result["quality_has_funding_gap"] = (~funding_present).astype(float)
    result["quality_has_oi_gap"] = (~oi_present).astype(float)
    result["quality_has_premium_gap"] = (~premium_present).astype(float)
    result["quality_provider_backed_all_required"] = (result["quality_context_missing_count"] == 0).astype(float)
    result["quality_latest_window_context_only"] = (
        pd.to_numeric(latest_window_only, errors="coerce").fillna(0.0).clip(lower=0.0, upper=1.0)
        if latest_window_only is not None
        else pd.Series(np.zeros(row_count, dtype=float), index=frame.index)
    )

    return result.loc[:, PERP_CONTEXT_V2_COLUMNS]


def _perp_context_v3_features(frame: pd.DataFrame, *, interval_ms: int) -> pd.DataFrame:
    result = _perp_context_v2_features(frame, interval_ms=interval_ms).copy()
    durable = _source_flag_any(
        frame,
        (
            "quality_context_durable_provider_archive_source",
            "context_durable_provider_archive",
            "durable_provider_archive",
        ),
    )
    self_archived = _source_flag_any(
        frame,
        (
            "quality_context_self_archived_source",
            "context_self_archived",
            "self_archived",
        ),
    )
    latest_window = _source_flag_any(
        frame,
        (
            "quality_context_latest_window_diagnostic_source",
            "quality_latest_window_context_only_source",
            "latest_window_only",
        ),
    )
    latest_window = pd.concat(
        [
            latest_window,
            pd.to_numeric(result["quality_latest_window_context_only"], errors="coerce").fillna(0.0),
        ],
        axis=1,
    ).max(axis=1).clip(lower=0.0, upper=1.0)

    explicit_missing_unknown = _source_flag_any(
        frame,
        (
            "quality_context_missing_unknown_source",
            "context_missing_unknown",
            "missing_unknown",
        ),
    )
    source_known = (durable.gt(0.0) | self_archived.gt(0.0) | latest_window.gt(0.0)).astype(float)
    missing_required = pd.to_numeric(result["quality_context_missing_count"], errors="coerce").fillna(0.0).gt(0.0)
    missing_unknown = (
        missing_required
        | explicit_missing_unknown.gt(0.0)
        | source_known.eq(0.0)
    ).astype(float)

    flow_proxy = pd.concat(
        [
            _source_flag_any(
                frame,
                (
                    "quality_agg_trade_flow_proxy_not_ofi_source",
                    "agg_trade_flow_proxy_not_ofi",
                ),
            ),
            result["flow_buy_sell_ratio"].notna().astype(float),
            result["flow_signed_taker_notional"].notna().astype(float),
        ],
        axis=1,
    ).max(axis=1).clip(lower=0.0, upper=1.0)

    provider_backed = pd.to_numeric(result["quality_provider_backed_all_required"], errors="coerce").fillna(0.0)
    source_candidate_eligible = durable.gt(0.0) | self_archived.gt(0.0)
    candidate_ready = (
        provider_backed.eq(1.0)
        & source_candidate_eligible
        & latest_window.eq(0.0)
        & missing_unknown.eq(0.0)
    ).astype(float)

    result["quality_context_durable_provider_archive"] = durable
    result["quality_context_self_archived"] = self_archived
    result["quality_context_latest_window_diagnostic"] = latest_window
    result["quality_context_missing_unknown"] = missing_unknown
    result["quality_context_candidate_ready_eligible"] = candidate_ready
    result["quality_agg_trade_flow_proxy_not_ofi"] = flow_proxy
    return result.loc[:, PERP_CONTEXT_V3_COLUMNS]


def _aggtrade_orderflow_features(frame: pd.DataFrame, *, interval_ms: int) -> pd.DataFrame:
    result = pd.DataFrame(index=frame.index)
    bars_1h = _bars_for_duration(interval_ms=interval_ms, duration_ms=3_600_000)
    bars_7d = _bars_for_duration(interval_ms=interval_ms, duration_ms=7 * 24 * 3_600_000)

    quote_volume = _first_available_numeric(frame, ("quote_volume", "agg_quote_volume", "notional", "quote_quantity"))
    taker_buy_quote = _first_available_numeric(
        frame,
        ("taker_buy_quote_volume", "buy_quote_volume", "agg_taker_buy_quote_volume"),
    )
    sell_quote = _first_available_numeric(frame, ("sell_quote_volume", "sell_quantity", "agg_sell_quote_volume"))
    signed_ratio = _first_available_numeric(frame, ("primary_signed_imbalance_ratio", "signed_imbalance_ratio", "signed_ratio"))
    trade_count = _first_available_numeric(frame, ("agg_trade_count", "trade_count", "count"))
    large_trade_count = _first_available_numeric(frame, ("agg_large_trade_count", "large_trade_count"))
    large_buy_count = _first_available_numeric(frame, ("agg_large_buy_count", "large_buy_count"))
    large_sell_count = _first_available_numeric(frame, ("agg_large_sell_count", "large_sell_count"))

    buy_share = _agg_taker_buy_share(frame, taker_buy_quote, sell_quote, quote_volume, signed_ratio)
    signed_imbalance = _agg_signed_imbalance(frame, taker_buy_quote, sell_quote, quote_volume, signed_ratio)
    signed_notional = _flow_signed_notional(frame, signed_imbalance, quote_volume, taker_buy_quote, sell_quote)
    cvd = signed_notional.cumsum()
    trade_count_zscore = _rolling_zscore(trade_count, bars_7d) if trade_count is not None else _nan_series(frame)
    quote_volume_zscore = _rolling_zscore(quote_volume, bars_7d) if quote_volume is not None else _nan_series(frame)
    burst_base = pd.concat([trade_count_zscore, quote_volume_zscore], axis=1).max(axis=1).clip(lower=0.0)
    flow_burst = burst_base * signed_imbalance.abs()
    source_present = (
        buy_share.notna()
        | signed_imbalance.notna()
        | (trade_count.notna() if trade_count is not None else pd.Series(False, index=frame.index))
        | (quote_volume.notna() if quote_volume is not None else pd.Series(False, index=frame.index))
    )
    latest_window = _source_flag_any(
        frame,
        (
            "quality_context_latest_window_diagnostic_source",
            "quality_latest_window_context_only_source",
            "latest_window_only",
        ),
    )
    flow_proxy = pd.concat(
        [
            _source_flag_any(
                frame,
                (
                    "quality_agg_trade_flow_proxy_not_ofi_source",
                    "agg_trade_flow_proxy_not_ofi",
                ),
            ),
            source_present.astype(float),
        ],
        axis=1,
    ).max(axis=1).clip(lower=0.0, upper=1.0)

    result["agg_taker_buy_quote_share"] = buy_share
    result["agg_signed_quote_imbalance"] = signed_imbalance
    result["agg_sqrt_signed_quote_imbalance"] = np.sign(signed_imbalance) * np.sqrt(
        signed_imbalance.abs().clip(lower=0.0, upper=1.0)
    )
    result["agg_cvd_slope"] = _rolling_slope(cvd, bars_1h)
    result["agg_trade_count_zscore"] = trade_count_zscore
    result["agg_quote_volume_zscore"] = quote_volume_zscore
    result["agg_large_trade_count"] = large_trade_count if large_trade_count is not None else _nan_series(frame)
    result["agg_large_trade_side_imbalance"] = _agg_large_trade_side_imbalance(
        frame,
        large_buy_count=large_buy_count,
        large_sell_count=large_sell_count,
        fallback_signed_imbalance=signed_imbalance if large_trade_count is not None else None,
    )
    result["agg_flow_burst_score"] = flow_burst.where(source_present)
    result["agg_sweep_proxy"] = result["agg_sqrt_signed_quote_imbalance"] * burst_base
    result["quality_aggtrade_context_missing"] = (~source_present).astype(float)
    result["quality_aggtrade_source_present"] = source_present.astype(float)
    result["quality_aggtrade_latest_window_diagnostic"] = latest_window
    result["quality_aggtrade_flow_proxy_not_ofi"] = flow_proxy
    return result.loc[:, AGGTRADE_ORDERFLOW_COLUMNS]


def _liquidation_context_features(frame: pd.DataFrame, *, interval_ms: int) -> pd.DataFrame:
    result = pd.DataFrame(index=frame.index)
    row_count = len(frame)
    bars_7d = _bars_for_duration(interval_ms=interval_ms, duration_ms=7 * 24 * 3_600_000)

    event_count = _first_available_numeric(frame, ("liquidation_event_count_1h", "liquidation_event_count"))
    total_notional = _first_available_numeric(
        frame,
        ("liquidation_quote_notional_1h", "liquidation_quote_notional", "quote_notional", "notional"),
    )
    buy_notional = _first_available_numeric(frame, ("liquidation_buy_notional_1h", "liquidation_buy_notional"))
    sell_notional = _first_available_numeric(frame, ("liquidation_sell_notional_1h", "liquidation_sell_notional"))
    imbalance = _first_available_numeric(
        frame,
        ("liquidation_side_imbalance_1h", "liquidation_side_imbalance"),
    )
    last_event_age_ms = _optional_numeric(frame, "liquidation_last_event_age_ms")
    vwap_price = _first_available_numeric(
        frame,
        ("liquidation_vwap_price_1h", "liquidation_vwap_price", "average_price", "price"),
    )
    close = _optional_numeric(frame, "close")

    result["liq_event_count_1h"] = event_count if event_count is not None else _nan_series(frame)
    result["liq_total_notional_1h"] = total_notional if total_notional is not None else _nan_series(frame)
    result["liq_buy_notional_1h"] = buy_notional if buy_notional is not None else _nan_series(frame)
    result["liq_sell_notional_1h"] = sell_notional if sell_notional is not None else _nan_series(frame)
    buy_sell_available = (
        buy_notional is not None
        and sell_notional is not None
        and (buy_notional.notna() & sell_notional.notna()).any()
    )
    if buy_sell_available:
        result["liq_net_notional_1h"] = buy_notional - sell_notional
    elif imbalance is not None and total_notional is not None:
        result["liq_net_notional_1h"] = imbalance * total_notional
    else:
        result["liq_net_notional_1h"] = _nan_series(frame)
    if imbalance is not None:
        result["liq_imbalance_ratio_1h"] = imbalance
    elif total_notional is not None:
        result["liq_imbalance_ratio_1h"] = result["liq_net_notional_1h"] / total_notional.replace(0.0, np.nan)
    else:
        result["liq_imbalance_ratio_1h"] = _nan_series(frame)
    result["liq_total_notional_z_7d"] = _rolling_zscore(result["liq_total_notional_1h"], bars_7d)
    result["liq_time_since_last_event_h"] = (
        last_event_age_ms / 3_600_000.0
        if last_event_age_ms is not None
        else _nan_series(frame)
    )
    if vwap_price is not None and close is not None:
        signed_reclaim = -np.sign(result["liq_imbalance_ratio_1h"]) * ((close - vwap_price) / vwap_price.replace(0.0, np.nan))
        result["liq_absorption_reclaim_bps"] = signed_reclaim * 10_000.0
    else:
        result["liq_absorption_reclaim_bps"] = _nan_series(frame)

    latest_window_only = _optional_numeric(frame, "quality_latest_window_context_only_source")
    if latest_window_only is None:
        latest_window_only = _optional_numeric(frame, "latest_window_only")
    has_event_context = result["liq_event_count_1h"].notna()
    result["quality_has_liquidation_gap"] = (~has_event_context).astype(float)
    result["quality_liquidation_provider_backed"] = has_event_context.astype(float)
    result["quality_liquidation_latest_window_context_only"] = (
        pd.to_numeric(latest_window_only, errors="coerce").fillna(0.0).clip(lower=0.0, upper=1.0)
        if latest_window_only is not None
        else pd.Series(np.zeros(row_count, dtype=float), index=frame.index)
    )
    return result.loc[:, LIQUIDATION_CONTEXT_COLUMNS]


def _wt3d_features(frame: pd.DataFrame, *, price_column: str | None) -> pd.DataFrame:
    price = _price_series(frame, price_column=price_column).ffill().fillna(0.0)

    def oscillator(length: int) -> pd.Series:
        basis = price.ewm(span=max(int(length), 2), adjust=False, min_periods=1).mean()
        deviation = (price - basis).abs().ewm(span=max(int(length), 2), adjust=False, min_periods=1).mean()
        raw = (price - basis) / deviation.replace(0.0, np.nan)
        return np.tanh(raw.fillna(0.0) / 3.0)

    result = pd.DataFrame(index=frame.index)
    result["wt3d_fast"] = oscillator(10)
    result["wt3d_normal"] = oscillator(21)
    result["wt3d_slow"] = oscillator(55)
    result["wt3d_fast_normal_spread"] = result["wt3d_fast"] - result["wt3d_normal"]
    result["wt3d_normal_slow_spread"] = result["wt3d_normal"] - result["wt3d_slow"]
    result["wt3d_slope"] = result["wt3d_normal"].diff(1)
    result["wt3d_acceleration"] = result["wt3d_slope"].diff(1).clip(-2.0, 2.0)
    cross = np.sign(result["wt3d_fast_normal_spread"]).diff().fillna(0.0).ne(0.0)
    result["wt3d_bars_since_cross"] = _bars_since_true(cross)
    result["wt3d_reversal_intensity"] = (result["wt3d_normal"].abs() - 0.75).clip(lower=0.0)
    slow_context = result["wt3d_slow"].rolling(4, min_periods=1).mean().shift(1)
    result["wt3d_mtf_agreement"] = np.sign(result["wt3d_normal"]) * np.sign(slow_context)
    return result.loc[:, WT3D_COLUMNS]


def _cross_asset_features(frame: pd.DataFrame) -> pd.DataFrame:
    result = pd.DataFrame(index=frame.index)
    if {"btc_close", "eth_close"}.issubset(frame.columns):
        btc = pd.to_numeric(frame["btc_close"], errors="coerce")
        eth = pd.to_numeric(frame["eth_close"], errors="coerce")
        btc_returns = np.log(btc.where(btc > 0)).diff()
        eth_returns = np.log(eth.where(eth > 0)).diff()
        result["btc_eth_lead_lag_corr_24"] = btc_returns.shift(1).rolling(24, min_periods=24).corr(eth_returns)
        result["eth_btc_relative_return_24"] = eth_returns.rolling(24, min_periods=24).sum() - btc_returns.rolling(24, min_periods=24).sum()
    else:
        for column in CROSS_ASSET_COLUMNS:
            result[column] = np.nan
    return result.loc[:, CROSS_ASSET_COLUMNS]


def _cross_asset_btc_eth_v2_features(frame: pd.DataFrame, *, interval_ms: int) -> pd.DataFrame:
    result = pd.DataFrame(index=frame.index)
    bars_1h = _bars_for_duration(interval_ms=interval_ms, duration_ms=3_600_000)
    window_96 = 96

    btc_close = _first_available_numeric(
        frame,
        ("btc_close", "btcusdt_close", "BTCUSDT_close", "btc_signal_bar_close"),
    )
    eth_close = _first_available_numeric(
        frame,
        ("eth_close", "ethusdt_close", "ETHUSDT_close", "eth_signal_bar_close"),
    )
    btc_return = _log_return_or_nan(frame, btc_close)
    eth_return = _log_return_or_nan(frame, eth_close)
    beta = _rolling_beta(eth_return, btc_return, window_96)
    residual = eth_return - (beta * btc_return)
    ethbtc_ratio = _safe_ratio(eth_close, btc_close) if eth_close is not None and btc_close is not None else _nan_series(frame)
    ethbtc_log_ratio = np.log(ethbtc_ratio.where(ethbtc_ratio > 0.0))

    btc_funding = _first_available_numeric(
        frame,
        ("btc_funding_rate", "btc_perp_last_funding_rate", "btc_last_funding_rate"),
    )
    eth_funding = _first_available_numeric(
        frame,
        ("eth_funding_rate", "eth_perp_last_funding_rate", "eth_last_funding_rate"),
    )
    funding_spread = (
        eth_funding - btc_funding
        if eth_funding is not None and btc_funding is not None
        else _nan_series(frame)
    )

    btc_oi_delta = _first_available_numeric(frame, ("btc_oi_delta_1h", "btc_open_interest_delta_1h"))
    eth_oi_delta = _first_available_numeric(frame, ("eth_oi_delta_1h", "eth_open_interest_delta_1h"))
    if btc_oi_delta is None:
        btc_oi = _first_available_numeric(frame, ("btc_oi_notional", "btc_open_interest_value", "btc_open_interest"))
        btc_oi_delta = btc_oi.diff(bars_1h) if btc_oi is not None else None
    if eth_oi_delta is None:
        eth_oi = _first_available_numeric(frame, ("eth_oi_notional", "eth_open_interest_value", "eth_open_interest"))
        eth_oi_delta = eth_oi.diff(bars_1h) if eth_oi is not None else None
    oi_delta_spread = (
        eth_oi_delta - btc_oi_delta
        if eth_oi_delta is not None and btc_oi_delta is not None
        else _nan_series(frame)
    )

    btc_time = _cross_asset_source_time(frame, "btc")
    eth_time = _cross_asset_source_time(frame, "eth")
    future_alignment = _cross_asset_future_alignment_risk(frame, btc_time, eth_time)
    matched_interval = _cross_asset_matched_interval(
        frame,
        btc_time,
        eth_time,
        future_alignment,
        interval_ms=interval_ms,
    )
    btc_durable = _cross_asset_durable_flag(frame, "btc")
    eth_durable = _cross_asset_durable_flag(frame, "eth")
    missing_btc = btc_close.isna() if btc_close is not None else pd.Series(True, index=frame.index)
    missing_eth = eth_close.isna() if eth_close is not None else pd.Series(True, index=frame.index)
    missing_funding = funding_spread.isna()
    missing_oi = oi_delta_spread.isna()
    missing_durable = btc_durable.eq(0.0) | eth_durable.eq(0.0)
    point_in_time_join = (
        matched_interval.eq(1.0)
        & future_alignment.eq(0.0)
        & (~missing_btc)
        & (~missing_eth)
    ).astype(float)
    candidate_ready = (
        point_in_time_join.eq(1.0)
        & btc_durable.eq(1.0)
        & eth_durable.eq(1.0)
    ).astype(float)

    result["btc_return_1"] = btc_return
    result["eth_return_1"] = eth_return
    result["eth_beta_to_btc_96"] = beta
    result["eth_btc_residual_return_1"] = residual
    result["eth_btc_residual_z_96"] = _rolling_zscore(residual, window_96)
    result["ethbtc_trend_96"] = _rolling_slope(ethbtc_log_ratio, window_96)
    result["ethbtc_state"] = np.sign(result["ethbtc_trend_96"]).replace(0.0, np.nan)
    result["btc_eth_corr_96"] = btc_return.rolling(window_96, min_periods=min(20, window_96)).corr(eth_return)
    result["funding_spread"] = funding_spread
    result["funding_spread_z_96"] = _rolling_zscore(funding_spread, window_96)
    result["oi_delta_spread_1h"] = oi_delta_spread
    result["oi_delta_spread_z_96"] = _rolling_zscore(oi_delta_spread, window_96)
    result["quality_cross_asset_missing_btc_context"] = missing_btc.astype(float)
    result["quality_cross_asset_missing_eth_context"] = missing_eth.astype(float)
    result["quality_cross_asset_missing_context"] = (missing_btc | missing_eth).astype(float)
    result["quality_cross_asset_missing_durable_context"] = missing_durable.astype(float)
    result["quality_cross_asset_missing_funding_context"] = missing_funding.astype(float)
    result["quality_cross_asset_missing_oi_context"] = missing_oi.astype(float)
    result["quality_cross_asset_future_alignment_risk"] = future_alignment
    result["quality_cross_asset_matched_interval"] = matched_interval
    result["quality_cross_asset_point_in_time_join"] = point_in_time_join
    result["quality_cross_asset_candidate_ready_eligible"] = candidate_ready
    return result.loc[:, CROSS_ASSET_BTC_ETH_V2_COLUMNS]


def _calendar_features(frame: pd.DataFrame) -> pd.DataFrame:
    feature_time = pd.to_datetime(frame["feature_time_ms"], unit="ms", utc=True)
    hour = feature_time.dt.hour + (feature_time.dt.minute / 60.0)
    result = pd.DataFrame(index=frame.index)
    result["session_hour_sin"] = np.sin(2.0 * math.pi * hour / 24.0)
    result["session_hour_cos"] = np.cos(2.0 * math.pi * hour / 24.0)
    result["session_weekday"] = feature_time.dt.weekday.astype(float)
    next_funding_hour = ((feature_time.dt.hour // 8) + 1) * 8
    hours_to_next = (next_funding_hour - feature_time.dt.hour - (feature_time.dt.minute / 60.0)) % 8
    result["hours_to_next_funding"] = hours_to_next.astype(float)
    result["weekend_session"] = feature_time.dt.weekday.isin([5, 6]).astype(float)
    return result.loc[:, CALENDAR_COLUMNS]


def _availability_report(frame: pd.DataFrame, manifest: FeatureManifest) -> FeatureAvailabilityReport:
    missing_counts = {
        column: int(frame[column].isna().sum())
        for column in manifest.feature_columns
        if column in frame.columns
    }
    row_count = max(int(len(frame)), 1)
    missing_rates = {column: count / row_count for column, count in missing_counts.items()}
    missing_context_columns = tuple(
        column
        for column, rate in missing_rates.items()
        if rate > 0.0
        and column
        in set(
            PERP_CONTEXT_COLUMNS
            + PERP_CONTEXT_V2_COLUMNS
            + AGGTRADE_ORDERFLOW_COLUMNS
            + LIQUIDATION_CONTEXT_COLUMNS
            + MICROSTRUCTURE_COLUMNS
            + CROSS_ASSET_COLUMNS
            + CROSS_ASSET_BTC_ETH_V2_COLUMNS
        )
    )
    return FeatureAvailabilityReport(
        row_count=int(len(frame)),
        feature_columns=manifest.feature_columns,
        availability_columns=manifest.availability_columns,
        missing_counts=missing_counts,
        missing_rates=missing_rates,
        missing_context_columns=missing_context_columns,
    )


def _price_series(frame: pd.DataFrame, *, price_column: str | None) -> pd.Series:
    candidates = [price_column, "close", "entry_price", "premium_close"]
    for candidate in candidates:
        if candidate and candidate in frame.columns:
            return pd.to_numeric(frame[candidate], errors="coerce").replace([np.inf, -np.inf], np.nan)
    return pd.Series(np.arange(len(frame), dtype=float), index=frame.index)


def _numeric_or_default(frame: pd.DataFrame, column: str, default: pd.Series) -> pd.Series:
    if column in frame.columns:
        return pd.to_numeric(frame[column], errors="coerce").replace([np.inf, -np.inf], np.nan)
    return default


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    previous_close = close.shift(1)
    ranges = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    )
    return ranges.max(axis=1)


def _rolling_slope(series: pd.Series, window: int) -> pd.Series:
    x = np.arange(window, dtype=float)
    x = x - x.mean()
    denominator = float(np.sum(x * x))

    def slope(values: np.ndarray) -> float:
        if not np.isfinite(values).all() or denominator <= 0:
            return np.nan
        y = values - values.mean()
        return float(np.sum(x * y) / denominator)

    return series.rolling(window, min_periods=window).apply(slope, raw=True)


def _bars_for_duration(*, interval_ms: int, duration_ms: int) -> int:
    if interval_ms <= 0:
        return 1
    return max(1, int(round(duration_ms / interval_ms)))


def _rolling_zscore(series: pd.Series, window: int) -> pd.Series:
    mean = series.rolling(window, min_periods=min(20, window)).mean()
    std = series.rolling(window, min_periods=min(20, window)).std(ddof=0)
    return (series - mean) / std.replace(0.0, np.nan)


def _nan_series(frame: pd.DataFrame) -> pd.Series:
    return pd.Series(np.nan, index=frame.index, dtype="float64")


def _optional_numeric(frame: pd.DataFrame, column: str) -> pd.Series | None:
    if column not in frame.columns:
        return None
    return pd.to_numeric(frame[column], errors="coerce").replace([np.inf, -np.inf], np.nan)


def _log_return_or_nan(frame: pd.DataFrame, series: pd.Series | None) -> pd.Series:
    if series is None:
        return _nan_series(frame)
    return np.log(series.where(series > 0.0)).diff()


def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return numerator / denominator.replace(0.0, np.nan)


def _rolling_beta(dependent: pd.Series, independent: pd.Series, window: int) -> pd.Series:
    min_periods = min(20, window)
    covariance = dependent.rolling(window, min_periods=min_periods).cov(independent)
    variance = independent.rolling(window, min_periods=min_periods).var(ddof=0)
    return covariance / variance.replace(0.0, np.nan)


def _cross_asset_source_time(frame: pd.DataFrame, prefix: str) -> pd.Series | None:
    columns = (
        f"{prefix}_source_time_ms",
        f"{prefix}_feature_time_ms",
        f"{prefix}_bar_time_ms",
        f"{prefix}usdt_bar_time_ms",
        f"{prefix.upper()}USDT_bar_time_ms",
    )
    return _first_available_numeric(frame, columns)


def _cross_asset_feature_time(frame: pd.DataFrame) -> pd.Series:
    feature_time = _optional_numeric(frame, "feature_time_ms")
    if feature_time is not None:
        return feature_time
    bar_time = _optional_numeric(frame, "bar_time_ms")
    if bar_time is not None:
        return bar_time
    return pd.Series(np.arange(len(frame), dtype=float), index=frame.index)


def _cross_asset_future_alignment_risk(
    frame: pd.DataFrame,
    btc_time: pd.Series | None,
    eth_time: pd.Series | None,
) -> pd.Series:
    feature_time = _cross_asset_feature_time(frame)
    risk = pd.Series(False, index=frame.index)
    if btc_time is not None:
        risk = risk | btc_time.gt(feature_time)
    if eth_time is not None:
        risk = risk | eth_time.gt(feature_time)
    return risk.astype(float)


def _cross_asset_matched_interval(
    frame: pd.DataFrame,
    btc_time: pd.Series | None,
    eth_time: pd.Series | None,
    future_alignment: pd.Series,
    *,
    interval_ms: int,
) -> pd.Series:
    if btc_time is None or eth_time is None:
        return pd.Series(np.zeros(len(frame), dtype=float), index=frame.index)
    max_lag_ms = max(float(interval_ms), 1.0)
    matched = (btc_time - eth_time).abs().le(max_lag_ms) & future_alignment.eq(0.0)
    return matched.astype(float)


def _cross_asset_durable_flag(frame: pd.DataFrame, prefix: str) -> pd.Series:
    return _source_flag_any(
        frame,
        (
            f"{prefix}_quality_context_durable_provider_archive",
            f"{prefix}_quality_context_durable_provider_archive_source",
            f"{prefix}_durable_provider_archive",
            f"{prefix}_public_archive",
        ),
    )


def _first_available_numeric(frame: pd.DataFrame, columns: Sequence[str]) -> pd.Series | None:
    for column in columns:
        series = _optional_numeric(frame, column)
        if series is not None:
            return series
    return None


def _source_present(frame: pd.DataFrame, columns: Sequence[str]) -> pd.Series:
    present = pd.Series(False, index=frame.index)
    for column in columns:
        series = _optional_numeric(frame, column)
        if series is not None:
            present = present | series.notna()
    return present


def _source_flag_any(frame: pd.DataFrame, columns: Sequence[str]) -> pd.Series:
    flags = []
    for column in columns:
        series = _optional_numeric(frame, column)
        if series is not None:
            flags.append(pd.to_numeric(series, errors="coerce").fillna(0.0).clip(lower=0.0, upper=1.0))
    if not flags:
        return pd.Series(np.zeros(len(frame), dtype=float), index=frame.index)
    return pd.concat(flags, axis=1).max(axis=1).clip(lower=0.0, upper=1.0)


def _hours_since_last_funding(frame: pd.DataFrame, funding_context_available: bool) -> pd.Series:
    if not funding_context_available:
        return _nan_series(frame)
    time_ms = _optional_numeric(frame, "bar_time_ms")
    if time_ms is None:
        time_ms = _optional_numeric(frame, "feature_time_ms")
    if time_ms is None:
        return _nan_series(frame)
    timestamp = pd.to_datetime(time_ms, unit="ms", utc=True)
    hour = timestamp.dt.hour + (timestamp.dt.minute / 60.0) + (timestamp.dt.second / 3600.0)
    return (hour % 8.0).astype(float)


def _hours_to_next_funding(frame: pd.DataFrame) -> pd.Series:
    time_ms = _optional_numeric(frame, "bar_time_ms")
    if time_ms is None:
        time_ms = _optional_numeric(frame, "feature_time_ms")
    if time_ms is None:
        return _nan_series(frame)
    timestamp = pd.to_datetime(time_ms, unit="ms", utc=True)
    hour = timestamp.dt.hour + (timestamp.dt.minute / 60.0) + (timestamp.dt.second / 3600.0)
    return ((8.0 - (hour % 8.0)) % 8.0).astype(float)


def _oi_volume_ratio(oi_notional: pd.Series, frame: pd.DataFrame) -> pd.Series:
    volume = _first_available_numeric(frame, ("quote_volume", "volume"))
    if volume is None:
        return _nan_series(frame)
    return oi_notional / volume.replace(0.0, np.nan)


def _flow_buy_sell_ratio(
    frame: pd.DataFrame,
    taker_buy_quote: pd.Series | None,
    sell_quote: pd.Series | None,
    quote_volume: pd.Series | None,
) -> pd.Series:
    if taker_buy_quote is not None and sell_quote is not None:
        return taker_buy_quote / sell_quote.replace(0.0, np.nan)
    if taker_buy_quote is not None and quote_volume is not None:
        sell = quote_volume - taker_buy_quote
        return taker_buy_quote / sell.replace(0.0, np.nan)
    return _nan_series(frame)


def _flow_signed_notional(
    frame: pd.DataFrame,
    signed_ratio: pd.Series | None,
    quote_volume: pd.Series | None,
    taker_buy_quote: pd.Series | None,
    sell_quote: pd.Series | None,
) -> pd.Series:
    if signed_ratio is not None and quote_volume is not None:
        return signed_ratio * quote_volume
    if taker_buy_quote is not None and sell_quote is not None:
        return taker_buy_quote - sell_quote
    if taker_buy_quote is not None and quote_volume is not None:
        return (2.0 * taker_buy_quote) - quote_volume
    return _nan_series(frame)


def _agg_taker_buy_share(
    frame: pd.DataFrame,
    taker_buy_quote: pd.Series | None,
    sell_quote: pd.Series | None,
    quote_volume: pd.Series | None,
    signed_ratio: pd.Series | None,
) -> pd.Series:
    if taker_buy_quote is not None and quote_volume is not None:
        return (taker_buy_quote / quote_volume.replace(0.0, np.nan)).clip(lower=0.0, upper=1.0)
    if taker_buy_quote is not None and sell_quote is not None:
        denominator = (taker_buy_quote + sell_quote).replace(0.0, np.nan)
        return (taker_buy_quote / denominator).clip(lower=0.0, upper=1.0)
    if signed_ratio is not None:
        return ((signed_ratio.clip(lower=-1.0, upper=1.0) + 1.0) / 2.0).clip(lower=0.0, upper=1.0)
    return _nan_series(frame)


def _agg_signed_imbalance(
    frame: pd.DataFrame,
    taker_buy_quote: pd.Series | None,
    sell_quote: pd.Series | None,
    quote_volume: pd.Series | None,
    signed_ratio: pd.Series | None,
) -> pd.Series:
    if signed_ratio is not None:
        return signed_ratio.clip(lower=-1.0, upper=1.0)
    if taker_buy_quote is not None and sell_quote is not None:
        denominator = (taker_buy_quote + sell_quote).replace(0.0, np.nan)
        return ((taker_buy_quote - sell_quote) / denominator).clip(lower=-1.0, upper=1.0)
    if taker_buy_quote is not None and quote_volume is not None:
        return (((2.0 * taker_buy_quote) / quote_volume.replace(0.0, np.nan)) - 1.0).clip(
            lower=-1.0,
            upper=1.0,
        )
    return _nan_series(frame)


def _agg_large_trade_side_imbalance(
    frame: pd.DataFrame,
    *,
    large_buy_count: pd.Series | None,
    large_sell_count: pd.Series | None,
    fallback_signed_imbalance: pd.Series | None,
) -> pd.Series:
    if large_buy_count is not None and large_sell_count is not None:
        denominator = (large_buy_count + large_sell_count).replace(0.0, np.nan)
        return ((large_buy_count - large_sell_count) / denominator).clip(lower=-1.0, upper=1.0)
    if fallback_signed_imbalance is not None:
        return fallback_signed_imbalance
    return _nan_series(frame)


def _hurst_proxy(values: np.ndarray) -> float:
    values = values[np.isfinite(values)]
    if len(values) < 16:
        return np.nan
    lag1 = np.diff(values, 1)
    lag2 = values[2:] - values[:-2]
    std1 = np.std(lag1)
    std2 = np.std(lag2)
    if std1 <= 0 or std2 <= 0:
        return np.nan
    return float(np.clip(math.log(std2 / std1) / math.log(2.0), 0.0, 1.0))


def _last_value_percentile(values: np.ndarray) -> float:
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return np.nan
    return float((values <= values[-1]).sum() / len(values))


def _bars_since_true(mask: pd.Series) -> list[int]:
    result: list[int] = []
    last_seen: int | None = None
    for index, value in enumerate(mask.tolist()):
        if bool(value):
            last_seen = index
            result.append(0)
        elif last_seen is None:
            result.append(index + 1)
        else:
            result.append(index - last_seen)
    return result
