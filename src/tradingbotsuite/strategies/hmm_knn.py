from __future__ import annotations

import pandas as pd

from tradingbotsuite.strategies._helpers import RuleBasedStrategy, RuleSignal, confidence_from_strength, numeric, spaced_indices


class HmmKnnDiagnosticStrategy(RuleBasedStrategy):
    strategy_id = "hmm_knn_diagnostic_v1"
    strategy_version = "v1"
    allowed_holding_periods = ("1h", "4h", "12h", "24h", "72h", "7d")
    required_feature_sets = ("features_full_context_no_wt", "features_full_context_wt3d")

    def _signals(self, frame: pd.DataFrame) -> list[RuleSignal]:
        allowed = spaced_indices(frame, int(self.config.get("spacing_bars", 8)))
        probability_threshold = float(self.config.get("probability_threshold", 0.55))
        expected_value_threshold = float(self.config.get("expected_value_threshold", 0.0))
        p_up = numeric(frame, "p_up_barrier", 0.5)
        p_down = numeric(frame, "p_down_barrier", 0.5)
        expected = numeric(frame, "expected_net_return_after_costs", 0.0)
        regime_no_trade = frame["regime_no_trade"].astype(bool) if "regime_no_trade" in frame.columns else pd.Series([False] * len(frame), index=frame.index)
        signals: list[RuleSignal] = []
        for index in allowed:
            if bool(regime_no_trade.iloc[index]) or float(expected.iloc[index]) < expected_value_threshold:
                continue
            up = float(p_up.iloc[index])
            down = float(p_down.iloc[index])
            if max(up, down) < probability_threshold:
                continue
            side = "long" if up >= down else "short"
            strength = min(1.0, abs(up - down) + max(float(expected.iloc[index]), 0.0))
            signals.append(RuleSignal(index, side, strength, confidence_from_strength(max(up, down) - 0.5)))
        return signals
