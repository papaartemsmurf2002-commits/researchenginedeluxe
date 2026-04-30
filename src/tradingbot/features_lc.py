from __future__ import annotations

import math
from collections.abc import Iterable

import numpy as np
import pandas as pd


def _series(values: pd.Series | Iterable[float]) -> pd.Series:
    if isinstance(values, pd.Series):
        return values.astype(float)
    return pd.Series(values, dtype=float)


def _pine_sum(values: pd.Series, period: int) -> pd.Series:
    return values.rolling(period, min_periods=1).sum()


def sma(values: pd.Series | Iterable[float], period: int) -> pd.Series:
    return _series(values).rolling(period, min_periods=period).mean()


def _pine_ema(values: pd.Series | Iterable[float], period: int) -> pd.Series:
    series = _series(values)
    length = len(series)
    output = np.full(length, np.nan, dtype=float)
    if period <= 0:
        return pd.Series(output, index=series.index, dtype=float)
    alpha = 2.0 / (period + 1.0)
    values_np = series.to_numpy(dtype=float, copy=False)
    seed_values: list[float] = []
    previous = np.nan
    for idx in range(length):
        current = float(values_np[idx])
        if not np.isfinite(current):
            output[idx] = previous
            continue
        if not np.isfinite(previous):
            seed_values.append(current)
            if len(seed_values) == period:
                previous = float(np.mean(seed_values))
                output[idx] = previous
            continue
        previous = alpha * current + (1.0 - alpha) * previous
        output[idx] = previous
    return pd.Series(output, index=series.index, dtype=float)


def _pine_rma(values: pd.Series | Iterable[float], period: int) -> pd.Series:
    series = _series(values)
    length = len(series)
    output = np.full(length, np.nan, dtype=float)
    if period <= 0:
        return pd.Series(output, index=series.index, dtype=float)
    alpha = 1.0 / period
    values_np = series.to_numpy(dtype=float, copy=False)
    seed_values: list[float] = []
    previous = np.nan
    for idx in range(length):
        current = float(values_np[idx])
        if not np.isfinite(current):
            output[idx] = previous
            continue
        if not np.isfinite(previous):
            seed_values.append(current)
            if len(seed_values) == period:
                previous = float(np.mean(seed_values))
                output[idx] = previous
            continue
        previous = alpha * current + (1.0 - alpha) * previous
        output[idx] = previous
    return pd.Series(output, index=series.index, dtype=float)


def ema(values: pd.Series | Iterable[float], period: int) -> pd.Series:
    return _pine_ema(values, period)


def rma(values: pd.Series | Iterable[float], period: int) -> pd.Series:
    return _pine_rma(values, period)


def rsi(values: pd.Series | Iterable[float], period: int) -> pd.Series:
    series = _series(values)
    delta = series.diff()
    gains = delta.clip(lower=0.0)
    losses = -delta.clip(upper=0.0)
    avg_gain = rma(gains, period)
    avg_loss = rma(losses, period)
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    result = 100.0 - (100.0 / (1.0 + rs))
    result = result.mask(avg_loss.eq(0.0) & avg_gain.gt(0.0), 100.0)
    result = result.mask(avg_gain.eq(0.0) & avg_loss.gt(0.0), 0.0)
    return result


def cci(values: pd.Series | Iterable[float], period: int) -> pd.Series:
    series = _series(values)
    mean = series.rolling(period, min_periods=period).mean()
    values_np = series.to_numpy(dtype=float, copy=False)
    mean_np = mean.to_numpy(dtype=float, copy=False)
    mad = np.full(len(series), np.nan, dtype=float)
    for idx in range(period - 1, len(series)):
        current_mean = mean_np[idx]
        if not np.isfinite(current_mean):
            continue
        window = values_np[idx - period + 1 : idx + 1]
        finite_window = window[np.isfinite(window)]
        if len(finite_window) == period:
            mad[idx] = float(np.mean(np.abs(finite_window - current_mean)))
    mad_series = pd.Series(mad, index=series.index, dtype=float)
    denom = (0.015 * mad_series).replace(0.0, np.nan)
    return (series - mean) / denom


def true_range(df: pd.DataFrame, source: pd.Series | None = None) -> pd.Series:
    reference = df["close"] if source is None else _series(source)
    prev_source = reference.shift(1).fillna(reference)
    return pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_source).abs(),
            (df["low"] - prev_source).abs(),
        ],
        axis=1,
    ).max(axis=1)


def atr(df: pd.DataFrame, period: int, source: pd.Series | None = None) -> pd.Series:
    return rma(true_range(df, source), period)


def normalize_deriv(src: pd.Series | Iterable[float], quadratic_mean_length: int) -> pd.Series:
    series = _series(src)
    deriv = series - series.shift(2)
    quadratic_mean = np.sqrt(_pine_sum(deriv.pow(2), quadratic_mean_length) / quadratic_mean_length)
    return deriv / quadratic_mean.replace(0.0, np.nan)


def normalize(src: pd.Series | Iterable[float], target_min: float, target_max: float) -> pd.Series:
    series = _series(src)
    historic_min = []
    historic_max = []
    min_value = 10e10
    max_value = -10e10
    for value in series.tolist():
        if not pd.isna(value):
            min_value = min(value, min_value)
            max_value = max(value, max_value)
        historic_min.append(min_value)
        historic_max.append(max_value)
    hist_min_series = pd.Series(historic_min, index=series.index, dtype=float)
    hist_max_series = pd.Series(historic_max, index=series.index, dtype=float)
    denom = (hist_max_series - hist_min_series).clip(lower=10e-10)
    return target_min + (target_max - target_min) * (series - hist_min_series) / denom


def rescale(src: pd.Series | Iterable[float], old_min: float, old_max: float, new_min: float, new_max: float) -> pd.Series:
    series = _series(src)
    return new_min + (new_max - new_min) * (series - old_min) / max(old_max - old_min, 10e-10)


def tanh(src: pd.Series | Iterable[float]) -> pd.Series:
    series = _series(src)
    return -1.0 + 2.0 / (1.0 + np.exp(-2.0 * series))


def dual_pole_filter(src: pd.Series | Iterable[float], lookback: int) -> pd.Series:
    series = _series(src)
    omega = -99 * math.pi / (70 * lookback)
    alpha = math.exp(omega)
    beta = -(alpha**2)
    gamma = math.cos(omega) * 2 * alpha
    delta = 1 - gamma - beta
    sliding_avg = 0.5 * (series + series.shift(1).fillna(series))
    output = np.full(len(series), np.nan, dtype=float)
    filter_prev_1 = 0.0
    filter_prev_2 = 0.0
    for idx, value in enumerate(sliding_avg.tolist()):
        filtered = (delta * value) + gamma * filter_prev_1 + beta * filter_prev_2
        output[idx] = filtered
        filter_prev_2 = filter_prev_1
        filter_prev_1 = filtered
    return pd.Series(output, index=series.index, dtype=float)


def tanh_transform(src: pd.Series | Iterable[float], smoothing_frequency: int, quadratic_mean_length: int) -> pd.Series:
    return dual_pole_filter(tanh(normalize_deriv(src, quadratic_mean_length)), smoothing_frequency)


def n_rsi(src: pd.Series | Iterable[float], n1: int, n2: int) -> pd.Series:
    return rescale(ema(rsi(src, n1), n2), 0.0, 100.0, 0.0, 1.0)


def n_cci(src: pd.Series | Iterable[float], n1: int, n2: int) -> pd.Series:
    return normalize(ema(cci(src, n1), n2), 0.0, 1.0)


def n_wt(src: pd.Series | Iterable[float], n1: int = 10, n2: int = 11) -> pd.Series:
    series = _series(src)
    ema1 = ema(series, n1)
    ema2 = ema((series - ema1).abs(), n1)
    ci = (series - ema1) / (0.015 * ema2.replace(0.0, np.nan))
    wt1 = ema(ci, n2)
    wt2 = sma(wt1, 4)
    return normalize(wt1 - wt2, 0.0, 1.0)


def _pine_adx(df: pd.DataFrame, source: pd.Series, length: int, *, zero_previous_on_first_bar: bool = True) -> pd.Series:
    previous_fill_close = 0.0 if zero_previous_on_first_bar else _series(source)
    previous_fill_high = 0.0 if zero_previous_on_first_bar else df["high"]
    previous_fill_low = 0.0 if zero_previous_on_first_bar else df["low"]
    prev_close = _series(source).shift(1).fillna(previous_fill_close)
    prev_high = df["high"].shift(1).fillna(previous_fill_high)
    prev_low = df["low"].shift(1).fillna(previous_fill_low)
    tr_values = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    directional_plus = pd.Series(
        np.where(
            (df["high"] - prev_high) > (prev_low - df["low"]),
            np.maximum(df["high"] - prev_high, 0.0),
            0.0,
        ),
        index=df.index,
        dtype=float,
    )
    neg_movement = pd.Series(
        np.where(
            (prev_low - df["low"]) > (df["high"] - prev_high),
            np.maximum(prev_low - df["low"], 0.0),
            0.0,
        ),
        index=df.index,
        dtype=float,
    )
    size = len(df)
    tr_values_np = tr_values.to_numpy(dtype=float, copy=False)
    directional_plus_np = directional_plus.to_numpy(dtype=float, copy=False)
    neg_movement_np = neg_movement.to_numpy(dtype=float, copy=False)
    tr_smooth = np.zeros(size, dtype=float)
    smooth_plus = np.zeros(size, dtype=float)
    smooth_neg = np.zeros(size, dtype=float)
    for idx in range(size):
        prev_tr = tr_smooth[idx - 1] if idx > 0 else 0.0
        prev_plus = smooth_plus[idx - 1] if idx > 0 else 0.0
        prev_neg = smooth_neg[idx - 1] if idx > 0 else 0.0
        tr_smooth[idx] = prev_tr - prev_tr / length + tr_values_np[idx]
        smooth_plus[idx] = prev_plus - prev_plus / length + directional_plus_np[idx]
        smooth_neg[idx] = prev_neg - prev_neg / length + neg_movement_np[idx]
    tr_smooth_series = pd.Series(tr_smooth, index=df.index, dtype=float)
    smooth_plus_series = pd.Series(smooth_plus, index=df.index, dtype=float)
    smooth_neg_series = pd.Series(smooth_neg, index=df.index, dtype=float)
    di_positive = smooth_plus_series / tr_smooth_series.replace(0.0, np.nan) * 100.0
    di_negative = smooth_neg_series / tr_smooth_series.replace(0.0, np.nan) * 100.0
    dx = ((di_positive - di_negative).abs() / (di_positive + di_negative).replace(0.0, np.nan) * 100.0).replace([np.inf, -np.inf], np.nan)
    return rma(dx, length)


def n_adx(
    high_src: pd.Series | Iterable[float],
    low_src: pd.Series | Iterable[float],
    close_src: pd.Series | Iterable[float],
    n1: int,
    *,
    zero_previous_on_first_bar: bool = True,
) -> pd.Series:
    df = pd.DataFrame({"high": _series(high_src), "low": _series(low_src), "close": _series(close_src)})
    adx_values = _pine_adx(df, df["close"], n1, zero_previous_on_first_bar=zero_previous_on_first_bar)
    return rescale(adx_values, 0.0, 100.0, 0.0, 1.0)


def regime_filter(df: pd.DataFrame, src: pd.Series | Iterable[float], threshold: float, use_regime_filter: bool) -> pd.Series:
    if not use_regime_filter:
        return pd.Series(True, index=df.index)
    source = _series(src)
    size = len(df)
    source_np = source.to_numpy(dtype=float, copy=False)
    high_np = df["high"].to_numpy(dtype=float, copy=False)
    low_np = df["low"].to_numpy(dtype=float, copy=False)
    value1 = np.zeros(size, dtype=float)
    value2 = np.zeros(size, dtype=float)
    klmf = np.zeros(size, dtype=float)
    for idx in range(size):
        src_prev = source_np[idx - 1] if idx > 0 else source_np[idx]
        v1_prev = value1[idx - 1] if idx > 0 else 0.0
        v2_prev = value2[idx - 1] if idx > 0 else 0.0
        klmf_prev = klmf[idx - 1] if idx > 0 else 0.0
        value1[idx] = 0.2 * (source_np[idx] - src_prev) + 0.8 * v1_prev
        value2[idx] = 0.1 * (high_np[idx] - low_np[idx]) + 0.8 * v2_prev
        omega = abs(value1[idx] / value2[idx]) if value2[idx] != 0.0 else 0.0
        alpha = (-(omega**2) + math.sqrt((omega**4) + 16 * (omega**2))) / 8 if omega != 0.0 else 0.0
        klmf[idx] = alpha * source_np[idx] + (1 - alpha) * klmf_prev
    klmf_series = pd.Series(klmf, index=df.index, dtype=float)
    abs_curve_slope = (klmf_series - klmf_series.shift(1)).abs()
    exponential_average = ema(abs_curve_slope, 200)
    normalized = (abs_curve_slope - exponential_average) / exponential_average.replace(0.0, np.nan)
    return normalized >= threshold


def filter_adx(df: pd.DataFrame, src: pd.Series | Iterable[float], length: int, adx_threshold: int, use_adx_filter: bool) -> pd.Series:
    if not use_adx_filter:
        return pd.Series(True, index=df.index)
    source = _series(src)
    adx_values = _pine_adx(df, source, length)
    return adx_values > adx_threshold


def filter_volatility(df: pd.DataFrame, min_length: int = 1, max_length: int = 10, use_volatility_filter: bool = True) -> pd.Series:
    if not use_volatility_filter:
        return pd.Series(True, index=df.index)
    recent_atr = atr(df, min_length)
    historical_atr = atr(df, max_length)
    return recent_atr > historical_atr
