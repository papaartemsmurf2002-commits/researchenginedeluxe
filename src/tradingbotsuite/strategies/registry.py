from __future__ import annotations

from typing import Any

from tradingbotsuite.strategies.funding_crowding_fade import FundingCrowdingFadeStrategy
from tradingbotsuite.strategies.funding_basis import FundingBasisStrategy
from tradingbotsuite.strategies.hmm_knn import HmmKnnDiagnosticStrategy
from tradingbotsuite.strategies.lc_reference import LcReferenceStrategy
from tradingbotsuite.strategies.no_trade import NoTradeStrategy
from tradingbotsuite.strategies.oi_flow_breakout import OiFlowBreakoutStrategy
from tradingbotsuite.strategies.perp_basis_convergence import PerpBasisConvergenceStrategy
from tradingbotsuite.strategies.range_reversion import RangeReversionStrategy
from tradingbotsuite.strategies.regime_adaptive import RegimeAdaptiveStrategy
from tradingbotsuite.strategies.trend import TrendFollowingStrategy
from tradingbotsuite.strategies.volatility_breakout import VolatilityBreakoutStrategy


def strategy_registry() -> dict[str, type]:
    return {
        "trend_following_v1": TrendFollowingStrategy,
        "baseline_trend": TrendFollowingStrategy,
        "volatility_breakout_v1": VolatilityBreakoutStrategy,
        "range_reversion_v1": RangeReversionStrategy,
        "funding_basis_v1": FundingBasisStrategy,
        "funding_crowding_fade_v2": FundingCrowdingFadeStrategy,
        "oi_flow_breakout_v2": OiFlowBreakoutStrategy,
        "perp_basis_convergence_v2": PerpBasisConvergenceStrategy,
        "regime_adaptive_v1": RegimeAdaptiveStrategy,
        "lc_reference_v1": LcReferenceStrategy,
        "hmm_knn_diagnostic_v1": HmmKnnDiagnosticStrategy,
        "baseline_no_trade": NoTradeStrategy,
    }


def get_strategy_plugin(strategy_id: str, *, config: dict[str, Any] | None = None):
    registry = strategy_registry()
    if strategy_id not in registry:
        raise ValueError(f"unknown_strategy_id:{strategy_id}")
    return registry[strategy_id](config=config)
