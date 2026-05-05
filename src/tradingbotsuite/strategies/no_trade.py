from __future__ import annotations

import pandas as pd

from tradingbotsuite.strategies._helpers import RuleBasedStrategy, RuleSignal


class NoTradeStrategy(RuleBasedStrategy):
    strategy_id = "baseline_no_trade"
    strategy_version = "v1"
    allowed_holding_periods = ("1h", "4h", "12h", "24h", "72h", "7d")
    required_feature_sets = (
        "features_price_trend_vol",
        "features_price_trend_vol_wt3d",
        "features_full_context_no_wt",
        "features_full_context_wt3d",
        "features_perp_context_only",
        "features_microstructure_filter_only",
        "features_cross_asset_context",
        "features_price_perp_micro_no_wt",
        "features_perp_context_v2",
        "features_liquidation_context_v1",
    )

    def _signals(self, frame: pd.DataFrame) -> list[RuleSignal]:
        _ = frame
        return []
