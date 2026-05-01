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
        pack_frame = _build_pack(prepared, pack_id=pack_id, price_column=price_column)
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


def _build_pack(frame: pd.DataFrame, *, pack_id: str, price_column: str | None) -> pd.DataFrame:
    if pack_id == "price_path_v1":
        return _price_path_features(frame, price_column=price_column)
    if pack_id == "trend_chop_v1":
        return _trend_chop_features(frame, price_column=price_column)
    if pack_id == "volatility_v1":
        return _volatility_features(frame, price_column=price_column)
    if pack_id == "perp_context_v1":
        return _context_features(frame, PERP_CONTEXT_COLUMNS)
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
        if rate > 0.0 and column in set(PERP_CONTEXT_COLUMNS + MICROSTRUCTURE_COLUMNS + CROSS_ASSET_COLUMNS)
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
