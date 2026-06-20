from __future__ import annotations

import pandas as pd

from tradingbotsuite.strategies._helpers import (
    RuleBasedStrategy,
    RuleSignal,
    confidence_from_strength,
    numeric,
    session_allowed_indices,
    spaced_indices,
)


class VolatilityBreakoutStrategy(RuleBasedStrategy):
    strategy_id = "volatility_breakout_v1"
    strategy_version = "v1"
    allowed_holding_periods = ("1h", "4h", "12h", "24h", "72h", "7d")
    required_feature_sets = (
        "features_price_trend_vol",
        "features_price_perp_aggflow_no_wt",
        "features_full_context_no_wt",
        "features_full_context_wt3d",
    )

    def _signals(self, frame: pd.DataFrame) -> list[RuleSignal]:
        shock_threshold = float(self.config.get("shock_threshold", 1.0))
        atr_threshold = float(self.config.get("atr_percentile_threshold", 0.45))
        allowed = spaced_indices(frame, int(self.config.get("spacing_bars", 10))) & session_allowed_indices(frame, self.config)
        shock = numeric(frame, "volatility_shock_zscore")
        atr = numeric(frame, "atr_percentile")
        slope = numeric(frame, "directional_slope_atr")
        signals: list[RuleSignal] = []
        for index in allowed:
            if float(shock.iloc[index]) < shock_threshold or float(atr.iloc[index]) < atr_threshold:
                continue
            raw_slope = float(slope.iloc[index])
            if raw_slope == 0.0:
                continue
            strength = min(1.0, abs(float(shock.iloc[index])) / max(shock_threshold, 1.0))
            signals.append(RuleSignal(index, "long" if raw_slope > 0.0 else "short", strength, confidence_from_strength(strength)))
        return signals
