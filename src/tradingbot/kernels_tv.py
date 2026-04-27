from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd


def _series(values: pd.Series | Iterable[float]) -> pd.Series:
    if isinstance(values, pd.Series):
        return values.astype(float)
    return pd.Series(values, dtype=float)


def rational_quadratic(values: pd.Series | Iterable[float], lookback: int, relative_weight: float, start_at_bar: int) -> pd.Series:
    series = _series(values)
    output = pd.Series(np.nan, index=series.index, dtype=float)
    loop_upper = 1 + start_at_bar
    for idx in range(len(series)):
        if idx < loop_upper:
            continue
        current_weight = 0.0
        cumulative_weight = 0.0
        for offset in range(loop_upper + 1):
            y = float(series.iloc[idx - offset])
            if not np.isfinite(y):
                current_weight = np.nan
                break
            weight = (1.0 + ((offset**2) / (((lookback**2) * 2.0 * relative_weight)))) ** (-relative_weight)
            current_weight += y * weight
            cumulative_weight += weight
        output.iloc[idx] = current_weight / cumulative_weight if cumulative_weight and np.isfinite(current_weight) else np.nan
    return output


def gaussian(values: pd.Series | Iterable[float], lookback: int, start_at_bar: int) -> pd.Series:
    series = _series(values)
    output = pd.Series(np.nan, index=series.index, dtype=float)
    loop_upper = 1 + start_at_bar
    for idx in range(len(series)):
        if idx < loop_upper:
            continue
        current_weight = 0.0
        cumulative_weight = 0.0
        for offset in range(loop_upper + 1):
            y = float(series.iloc[idx - offset])
            if not np.isfinite(y):
                current_weight = np.nan
                break
            weight = np.exp(-(offset**2) / (2.0 * (lookback**2)))
            current_weight += y * weight
            cumulative_weight += weight
        output.iloc[idx] = current_weight / cumulative_weight if cumulative_weight and np.isfinite(current_weight) else np.nan
    return output
