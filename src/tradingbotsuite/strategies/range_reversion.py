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


class RangeReversionStrategy(RuleBasedStrategy):
    strategy_id = "range_reversion_v1"
    strategy_version = "v1"
    allowed_holding_periods = ("1h", "4h", "12h", "24h")
    required_feature_sets = ("features_price_trend_vol", "features_full_context_no_wt")

    def _signals(self, frame: pd.DataFrame) -> list[RuleSignal]:
        chop_threshold = float(self.config.get("choppiness_threshold", 55.0))
        stretch_threshold = float(self.config.get("stretch_threshold", 0.10))
        slope_stretch_threshold = float(self.config.get("slope_stretch_threshold", min(stretch_threshold, 0.04)))
        allowed = spaced_indices(frame, int(self.config.get("spacing_bars", 8))) & session_allowed_indices(frame, self.config)
        chop = numeric(frame, "choppiness")
        slope = numeric(frame, "directional_slope_atr")
        zscore = numeric(frame, "path_zscore_20")
        signals: list[RuleSignal] = []
        for index in allowed:
            if float(chop.iloc[index]) < chop_threshold:
                continue
            zscore_stretch = float(zscore.iloc[index])
            slope_stretch = float(slope.iloc[index])
            if abs(zscore_stretch) >= stretch_threshold:
                stretch = zscore_stretch
            elif abs(slope_stretch) >= slope_stretch_threshold:
                stretch = slope_stretch
            else:
                continue
            side = "short" if stretch > 0.0 else "long"
            strength = min(1.0, abs(stretch))
            signals.append(RuleSignal(index, side, strength, confidence_from_strength(strength)))
        return signals
