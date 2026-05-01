from __future__ import annotations

import pandas as pd

from tradingbotsuite.strategies._helpers import RuleBasedStrategy, RuleSignal


class NoTradeStrategy(RuleBasedStrategy):
    strategy_id = "baseline_no_trade"
    strategy_version = "v1"
    allowed_holding_periods = ("1h", "4h", "12h", "24h", "72h", "7d")
    required_feature_sets = ("features_price_trend_vol", "features_full_context_no_wt", "features_full_context_wt3d")

    def _signals(self, frame: pd.DataFrame) -> list[RuleSignal]:
        _ = frame
        return []
