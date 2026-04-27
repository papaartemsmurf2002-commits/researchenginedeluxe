from __future__ import annotations

import math
from collections.abc import Iterable

import numpy as np
import pandas as pd

from tradingbot.features_tv import (
    atr as tv_atr,
    cci as tv_cci,
    ema as tv_ema,
    filter_adx as tv_filter_adx,
    filter_volatility as tv_filter_volatility,
    n_adx,
    n_cci,
    n_rsi,
    n_wt,
    regime_filter as tv_regime_filter,
    rma as tv_rma,
    rsi as tv_rsi,
)
from tradingbot.kernels_tv import gaussian as tv_gaussian
from tradingbot.kernels_tv import rational_quadratic as tv_rational_quadratic


def _series(values: pd.Series | Iterable[float]) -> pd.Series:
    if isinstance(values, pd.Series):
        return values.astype(float)
    return pd.Series(values, dtype=float)


def hlc3(df: pd.DataFrame) -> pd.Series:
    return (df["high"] + df["low"] + df["close"]) / 3.0


def ohlc4(df: pd.DataFrame) -> pd.Series:
    return (df["open"] + df["high"] + df["low"] + df["close"]) / 4.0


def sma(values: pd.Series | Iterable[float], period: int) -> pd.Series:
    return _series(values).rolling(period, min_periods=period).mean()


def _pine_ma(values: pd.Series | Iterable[float], period: int, alpha: float) -> pd.Series:
    series = _series(values)
    output = pd.Series(np.nan, index=series.index, dtype=float)
    if period <= 0 or len(series) < period:
        return output
    seed = float(series.iloc[:period].mean())
    output.iloc[period - 1] = seed
    previous = seed
    for idx in range(period, len(series)):
        current = float(series.iloc[idx])
        previous = alpha * current + (1.0 - alpha) * previous
        output.iloc[idx] = previous
    return output


def ema(values: pd.Series | Iterable[float], period: int) -> pd.Series:
    return tv_ema(values, period)


def rma(values: pd.Series | Iterable[float], period: int) -> pd.Series:
    return tv_rma(values, period)


def rsi(values: pd.Series | Iterable[float], period: int) -> pd.Series:
    return tv_rsi(values, period)


def cci(values: pd.Series | Iterable[float], period: int) -> pd.Series:
    return tv_cci(values, period)


def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    return pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)


def atr(df: pd.DataFrame, period: int) -> pd.Series:
    return tv_atr(df, period)


def adx(df: pd.DataFrame, period: int) -> pd.Series:
    up_move = df["high"].diff()
    down_move = -df["low"].diff()
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index)
    atr_values = atr(df, period).replace(0.0, np.nan)
    plus_di = 100 * rma(plus_dm, period) / atr_values
    minus_di = 100 * rma(minus_dm, period) / atr_values
    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)).fillna(0.0)
    return rma(dx, period).fillna(0.0)


def wt(values: pd.Series | Iterable[float], channel_length: int, average_length: int) -> pd.Series:
    values = _series(values)
    esa = ema(values, channel_length)
    deviation = ema((values - esa).abs(), channel_length).replace(0.0, np.nan)
    ci = (values - esa) / (0.015 * deviation)
    return ema(ci.fillna(0.0), average_length).fillna(0.0)


def rational_quadratic(values: pd.Series | Iterable[float], lookback: int, weight: float, start_at_bar: int) -> pd.Series:
    return tv_rational_quadratic(values, lookback, weight, start_at_bar)


def gaussian(values: pd.Series | Iterable[float], lookback: int, start_at_bar: int) -> pd.Series:
    return tv_gaussian(values, lookback, start_at_bar)


def volatility_filter(df: pd.DataFrame, enabled: bool) -> pd.Series:
    return tv_filter_volatility(df, 1, 10, enabled).fillna(False)


def regime_filter(df: pd.DataFrame, threshold: float, enabled: bool) -> pd.Series:
    return tv_regime_filter(df, ohlc4(df), threshold, enabled).fillna(False)


def adx_filter(df: pd.DataFrame, threshold: int, enabled: bool) -> pd.Series:
    return tv_filter_adx(df, df["close"], 14, threshold, enabled).fillna(False)


def feature_series(
    df: pd.DataFrame,
    feature_name: str,
    param_a: int,
    param_b: int,
    *,
    adx_zero_previous_on_first_bar: bool = True,
) -> pd.Series:
    feature_name = feature_name.upper()
    if feature_name == "RSI":
        return n_rsi(df["close"], param_a, param_b)
    if feature_name == "WT":
        return n_wt(hlc3(df), param_a, param_b)
    if feature_name == "CCI":
        return n_cci(df["close"], param_a, param_b)
    if feature_name == "ADX":
        return n_adx(df["high"], df["low"], df["close"], param_a, zero_previous_on_first_bar=adx_zero_previous_on_first_bar)
    raise ValueError(f"Unsupported feature: {feature_name}")


def lorentzian_distance(current: np.ndarray, historical: np.ndarray) -> float:
    return float(np.sum(np.log1p(np.abs(current - historical))))


def normalize_frame(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    if "timestamp" not in frame.columns and "time" in frame.columns:
        frame = frame.rename(columns={"time": "timestamp"})
    if "timestamp" in frame.columns:
        if pd.api.types.is_numeric_dtype(frame["timestamp"]):
            max_timestamp = float(frame["timestamp"].dropna().max()) if frame["timestamp"].notna().any() else 0.0
            unit = "ms" if max_timestamp > 10_000_000_000 else "s"
            frame["timestamp"] = pd.to_datetime(frame["timestamp"], unit=unit, utc=True)
        else:
            frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
        frame = frame.sort_values("timestamp").reset_index(drop=True)
    if "volume" not in frame.columns:
        frame["volume"] = 0.0
    expected = {"open", "high", "low", "close", "volume"}
    missing = expected - set(frame.columns)
    if missing:
        raise ValueError(f"Missing OHLCV columns: {sorted(missing)}")
    for column in expected:
        frame[column] = frame[column].astype(float)
    if "symbol" not in frame.columns:
        frame["symbol"] = "UNKNOWN"
    return frame


def pct_drawdown(equity_curve: pd.Series) -> float:
    running_max = equity_curve.cummax().replace(0.0, np.nan)
    dd = ((equity_curve - running_max) / running_max) * 100.0
    return float(dd.min()) if not dd.empty else 0.0


def max_consecutive_losses(pnls: list[float]) -> int:
    worst = 0
    current = 0
    for pnl in pnls:
        if pnl < 0:
            current += 1
            worst = max(worst, current)
        else:
            current = 0
    return worst


def bps_to_multiplier(bps: float) -> float:
    return bps / 10_000.0


def safe_mean(values: list[float]) -> float:
    return float(sum(values) / len(values)) if values else 0.0


def round_step(value: float, decimals: int) -> float:
    return round(float(value), max(decimals, 0))


def annualized_sharpe(returns: pd.Series, periods_per_year: int = 365 * 24 * 4) -> float:
    if returns.empty or returns.std(ddof=0) == 0:
        return 0.0
    return float(math.sqrt(periods_per_year) * returns.mean() / returns.std(ddof=0))
