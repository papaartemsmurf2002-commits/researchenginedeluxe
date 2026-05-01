from __future__ import annotations

import pandas as pd

from tradingbotsuite.strategies._helpers import RuleBasedStrategy, RuleSignal, confidence_from_strength, numeric, spaced_indices


class LcReferenceStrategy(RuleBasedStrategy):
    strategy_id = "lc_reference_v1"
    strategy_version = "v1"
    allowed_holding_periods = ("1h", "4h", "12h", "24h", "72h", "7d")
    required_feature_sets = (
        "features_price_trend_vol",
        "features_price_trend_vol_wt3d",
        "features_full_context_no_wt",
        "features_full_context_wt3d",
    )

    def _signals(self, frame: pd.DataFrame) -> list[RuleSignal]:
        allowed = spaced_indices(frame, int(self.config.get("spacing_bars", 12)))
        direction_long = numeric(frame, "direction_long", 0.5)
        slope = numeric(frame, "directional_slope_atr")
        threshold = float(self.config.get("slope_threshold", 0.10))
        signals: list[RuleSignal] = []
        for index in allowed:
            slope_value = float(slope.iloc[index])
            if abs(slope_value) < threshold:
                continue
            side = "long" if float(direction_long.iloc[index]) >= 0.5 else "short"
            strength = min(1.0, abs(slope_value))
            signals.append(RuleSignal(index, side, strength, confidence_from_strength(strength)))
        return signals
