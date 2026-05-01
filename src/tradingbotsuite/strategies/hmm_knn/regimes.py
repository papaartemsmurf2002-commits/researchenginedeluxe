from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class DeterministicRegimeModel:
    n_states: int = 4
    backend: str = "deterministic_rule_baseline"
    state_labels: dict[int, str] | None = None

    def posterior(self, frame: pd.DataFrame) -> np.ndarray:
        return deterministic_regime_posterior(frame, n_states=self.n_states)


def deterministic_regime_posterior(frame: pd.DataFrame, *, n_states: int = 4) -> np.ndarray:
    n_states = max(int(n_states), 1)
    posterior = np.zeros((len(frame), n_states), dtype=float)
    if len(frame) == 0:
        return posterior
    slope = pd.to_numeric(frame.get("directional_slope_atr", pd.Series([0.0] * len(frame))), errors="coerce").fillna(0.0)
    chop = pd.to_numeric(frame.get("choppiness", pd.Series([50.0] * len(frame))), errors="coerce").fillna(50.0)
    vol = pd.to_numeric(frame.get("volatility_shock_zscore", pd.Series([0.0] * len(frame))), errors="coerce").fillna(0.0)
    for row_index, (slope_value, chop_value, vol_value) in enumerate(zip(slope, chop, vol, strict=False)):
        if n_states == 1:
            state = 0
        elif vol_value >= 2.0 and n_states >= 4:
            state = 3
        elif slope_value >= 0.15 and chop_value < 60.0 and n_states >= 2:
            state = 1
        elif slope_value <= -0.15 and n_states >= 3:
            state = 2
        else:
            state = 0
        posterior[row_index, min(state, n_states - 1)] = 1.0
    return posterior
