from __future__ import annotations

import pandas as pd

from tradingbotsuite.strategies._helpers import RuleBasedStrategy, RuleSignal, confidence_from_strength, numeric, spaced_indices


class RegimeAdaptiveStrategy(RuleBasedStrategy):
    strategy_id = "regime_adaptive_v1"
    strategy_version = "v1"
    allowed_holding_periods = ("4h", "12h", "24h", "72h", "7d")
    required_feature_sets = ("features_full_context_no_wt", "features_full_context_wt3d")

    def _signals(self, frame: pd.DataFrame) -> list[RuleSignal]:
        allowed = spaced_indices(frame, int(self.config.get("spacing_bars", 12)))
        slope = numeric(frame, "directional_slope_atr")
        chop = numeric(frame, "choppiness", 50.0)
        vol = numeric(frame, "volatility_shock_zscore")
        funding = numeric(frame, "funding_rate")
        signals: list[RuleSignal] = []
        for index in allowed:
            slope_value = float(slope.iloc[index])
            chop_value = float(chop.iloc[index])
            vol_value = float(vol.iloc[index])
            funding_value = float(funding.iloc[index])
            if abs(funding_value) > 0.00008 and vol_value < 2.5:
                side = "short" if funding_value > 0 else "long"
                strength = min(1.0, abs(funding_value) / 0.0002)
            elif chop_value < 50.0 and abs(slope_value) > 0.18:
                side = "long" if slope_value > 0 else "short"
                strength = min(1.0, abs(slope_value))
            else:
                continue
            signals.append(RuleSignal(index, side, strength, confidence_from_strength(strength)))
        return signals
