from __future__ import annotations

import pandas as pd

from tradingbotsuite.strategies._helpers import RuleBasedStrategy, RuleSignal, confidence_from_strength, numeric, spaced_indices


class TrendFollowingStrategy(RuleBasedStrategy):
    strategy_id = "trend_following_v1"
    strategy_version = "v1"
    allowed_holding_periods = ("4h", "12h", "24h", "72h", "7d")
    required_feature_sets = ("features_price_trend_vol", "features_full_context_no_wt", "features_full_context_wt3d")

    def _signals(self, frame: pd.DataFrame) -> list[RuleSignal]:
        threshold = float(self.config.get("slope_threshold", 0.12))
        max_chop = float(self.config.get("max_choppiness", 58.0))
        funding_penalty = float(self.config.get("funding_penalty_threshold", 0.00025))
        allowed = spaced_indices(frame, int(self.config.get("spacing_bars", 12)))
        slope = numeric(frame, "directional_slope_atr")
        chop = numeric(frame, "choppiness", 50.0)
        funding = numeric(frame, "funding_rate")
        signals: list[RuleSignal] = []
        for index in allowed:
            raw = float(slope.iloc[index])
            if abs(raw) < threshold or float(chop.iloc[index]) > max_chop:
                continue
            side = "long" if raw > 0.0 else "short"
            if side == "long" and float(funding.iloc[index]) > funding_penalty:
                continue
            if side == "short" and float(funding.iloc[index]) < -funding_penalty:
                continue
            strength = min(1.0, abs(raw))
            signals.append(RuleSignal(index, side, strength, confidence_from_strength(strength)))
        return signals
