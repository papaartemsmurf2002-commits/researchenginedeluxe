from __future__ import annotations

import pandas as pd

from tradingbotsuite.strategies._helpers import RuleBasedStrategy, RuleSignal, confidence_from_strength, numeric, spaced_indices


class FundingBasisStrategy(RuleBasedStrategy):
    strategy_id = "funding_basis_v1"
    strategy_version = "v1"
    allowed_holding_periods = ("4h", "12h", "24h", "72h", "7d")
    required_feature_sets = ("features_perp_context_only", "features_full_context_no_wt", "features_full_context_wt3d")

    def _signals(self, frame: pd.DataFrame) -> list[RuleSignal]:
        funding_threshold = float(self.config.get("funding_threshold", 0.00004))
        basis_threshold = float(self.config.get("basis_bps_threshold", 1.0))
        allowed = spaced_indices(frame, int(self.config.get("spacing_bars", 12)))
        funding = numeric(frame, "funding_rate")
        basis = numeric(frame, "basis_bps")
        momentum = numeric(frame, "directional_slope_atr")
        signals: list[RuleSignal] = []
        for index in allowed:
            funding_value = float(funding.iloc[index])
            basis_value = float(basis.iloc[index])
            if abs(funding_value) < funding_threshold and abs(basis_value) < basis_threshold:
                continue
            side = "short" if funding_value > 0.0 or basis_value > basis_threshold else "long"
            if side == "short" and float(momentum.iloc[index]) > 0.75:
                continue
            if side == "long" and float(momentum.iloc[index]) < -0.75:
                continue
            strength = min(1.0, max(abs(funding_value) / max(funding_threshold, 1e-9), abs(basis_value) / max(basis_threshold, 1e-9)) / 4.0)
            signals.append(RuleSignal(index, side, strength, confidence_from_strength(strength)))
        return signals
