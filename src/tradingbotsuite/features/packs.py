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
    CALENDAR_COLUMNS,
    CROSS_ASSET_COLUMNS,
    MICROSTRUCTURE_COLUMNS,
    PERP_CONTEXT_COLUMNS,
    PERP_CONTEXT_V2_COLUMNS,
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
    features = prepared.loc[:, [bar_time_column, "feature_time_ms"]].copy()
    for pack_id in feature_packs:
        pack_frame = _build_pack(prepared, pack_id=pack_id, price_column=price_column, interval_ms=interval_ms)
        for column in pack_frame.columns:
            features[column] = pack_frame[column]

    for column in manifest.feature_columns:
        if column not in features.columns:
            features[column] = np.nan
        features[f"missing_{column}"] = features[column].isna().astype(int)

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
    if pack_id == "microstructure_context_v1":
        return _context_features(frame, MICROSTRUCTURE_COLUMNS)
    if pack_id == "wt3d_v1":
        return _wt3d_features(frame, price_column=price_column)
    if pack_id == "cross_asset_v1":
        return _cross_asset_features(frame)
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
        if rate > 0.0 and column in set(PERP_CONTEXT_COLUMNS + PERP_CONTEXT_V2_COLUMNS + MICROSTRUCTURE_COLUMNS + CROSS_ASSET_COLUMNS)
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
