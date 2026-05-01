from __future__ import annotations

import pandas as pd
import pytest

from tradingbotsuite.backtesting.costs import CostModel
from tradingbotsuite.backtesting.execution_sim import ExecutionAssumptions, ExecutionSimulator


def _market() -> pd.DataFrame:
    start = 1_712_649_600_000
    return pd.DataFrame(
        {
            "bar_time_ms": [start + index * 900_000 for index in range(12)],
            "open": [100.0 + index for index in range(12)],
            "high": [101.0 + index for index in range(12)],
            "low": [99.0 + index for index in range(12)],
            "close": [100.5 + index for index in range(12)],
            "volume": [1000.0] * 12,
            "funding_rate": [0.0001] * 12,
            "spread_bps": [2.0] * 12,
        }
    )


def test_execution_simulator_applies_latency_costs_and_funding() -> None:
    market = _market()
    signals = pd.DataFrame(
        {
            "signal_id": ["s1"],
            "symbol": ["BTCUSDT"],
            "decision_time_ms": [int(market.iloc[0]["bar_time_ms"]) + 900_000],
            "side": ["long"],
            "signal_bar_close": [100.5],
        }
    )
    assumptions = ExecutionAssumptions(
        interval_ms=900_000,
        entry_latency_ms=900_000,
        entry_price_source="next_bar_open",
        min_holding_ms=3_600_000,
        max_holding_ms=7 * 24 * 60 * 60 * 1000,
        holding_period_ms=3_600_000,
    )

    trades, equity = ExecutionSimulator().simulate(
        signals,
        market,
        costs=CostModel(fee_bps=5.0, slippage_bps=5.0, spread_bps=1.0),
        assumptions=assumptions,
        initial_equity=10_000.0,
    )

    assert len(trades) == 1
    assert trades.iloc[0]["entry_time_ms"] == market.iloc[2]["bar_time_ms"]
    assert trades.iloc[0]["holding_ms"] == 3_600_000
    assert trades.iloc[0]["fee_return"] > 0
    assert trades.iloc[0]["slippage_return"] > 0
    assert trades.iloc[0]["funding_return"] < 0
    assert equity.iloc[-1]["equity"] != 10_000.0


def test_same_bar_exit_is_rejected_without_sequence_proof() -> None:
    market = _market()
    signals = pd.DataFrame(
        {
            "signal_id": ["s1"],
            "symbol": ["BTCUSDT"],
            "decision_time_ms": [int(market.iloc[0]["bar_time_ms"])],
            "side": ["long"],
            "signal_bar_close": [100.5],
        }
    )
    assumptions = ExecutionAssumptions(
        interval_ms=900_000,
        entry_latency_ms=0,
        entry_price_source="next_bar_open",
        min_holding_ms=3_600_000,
        max_holding_ms=7 * 24 * 60 * 60 * 1000,
        holding_period_ms=0,
    )

    with pytest.raises(ValueError, match="holding_period_ms"):
        ExecutionSimulator().simulate(
            signals,
            market,
            costs=CostModel(),
            assumptions=assumptions,
            initial_equity=10_000.0,
        )


def test_lower_timeframe_entry_source_requires_lower_frame() -> None:
    assumptions = ExecutionAssumptions(
        interval_ms=900_000,
        entry_latency_ms=0,
        entry_price_source="lower_timeframe_execution_path",
        min_holding_ms=3_600_000,
        max_holding_ms=7 * 24 * 60 * 60 * 1000,
        holding_period_ms=3_600_000,
    )

    with pytest.raises(ValueError, match="requires lower_timeframe_market_data"):
        ExecutionSimulator().simulate(
            pd.DataFrame(),
            _market(),
            costs=CostModel(),
            assumptions=assumptions,
            initial_equity=10_000.0,
        )
