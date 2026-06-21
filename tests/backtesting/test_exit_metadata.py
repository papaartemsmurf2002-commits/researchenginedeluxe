from __future__ import annotations

import pandas as pd

from tradingbotsuite.backtesting.costs import CostModel
from tradingbotsuite.backtesting.execution_sim import ExecutionAssumptions, ExecutionSimulator
import pytest

from tradingbotsuite.backtesting.exits import (
    close_only_barrier_exit,
    fixed_holding_window_exit,
    triple_barrier_exit_from_lower_timeframe,
)


def _market(row_count: int = 8) -> pd.DataFrame:
    start = 1_712_649_600_000
    return pd.DataFrame(
        {
            "bar_time_ms": [start + index * 900_000 for index in range(row_count)],
            "open": [100.0 + index for index in range(row_count)],
            "high": [101.0 + index for index in range(row_count)],
            "low": [99.0 + index for index in range(row_count)],
            "close": [100.5 + index for index in range(row_count)],
            "volume": [1000.0] * row_count,
        }
    )


def _lower(entry_time_ms: int, rows: list[tuple[int, float, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "bar_time_ms": [entry_time_ms + offset for offset, _, _, _ in rows],
            "high": [high for _, high, _, _ in rows],
            "low": [low for _, _, low, _ in rows],
            "close": [close for _, _, _, close in rows],
        }
    )


def test_execution_simulator_adds_exit_metadata_columns() -> None:
    market = _market()
    trades, _ = ExecutionSimulator().simulate(
        pd.DataFrame(
            {
                "signal_id": ["s1"],
                "symbol": ["BTCUSDT"],
                "decision_time_ms": [int(market.iloc[0]["bar_time_ms"])],
                "side": ["long"],
                "signal_bar_close": [100.0],
            }
        ),
        market,
        costs=CostModel(),
        assumptions=ExecutionAssumptions(
            interval_ms=900_000,
            entry_latency_ms=900_000,
            entry_price_source="next_bar_open",
            min_holding_ms=3_600_000,
            max_holding_ms=7 * 24 * 60 * 60 * 1000,
            holding_period_ms=3_600_000,
        ),
        initial_equity=10_000.0,
    )

    assert {
        "entry_bar_index",
        "exit_bar_index",
        "exit_target_time_ms",
        "exit_used_fallback",
        "exit_policy",
        "requested_exit_policy",
        "canonical_exit_policy",
    } <= set(trades.columns)
    assert trades.iloc[0]["exit_reason"] == "holding_window"
    assert trades.iloc[0]["exit_policy"] == "fixed_holding_window"
    assert trades.iloc[0]["requested_exit_policy"] == "fixed_holding_window"
    assert trades.iloc[0]["canonical_exit_policy"] == "fixed_holding_window"


def test_execution_simulator_preserves_fixed_holding_alias_identity() -> None:
    market = _market()
    trades, _ = ExecutionSimulator().simulate(
        pd.DataFrame(
            {
                "signal_id": ["s1"],
                "symbol": ["BTCUSDT"],
                "decision_time_ms": [int(market.iloc[0]["bar_time_ms"])],
                "side": ["long"],
                "signal_bar_close": [100.0],
            }
        ),
        market,
        costs=CostModel(),
        assumptions=ExecutionAssumptions(
            interval_ms=900_000,
            entry_latency_ms=900_000,
            entry_price_source="next_bar_open",
            min_holding_ms=3_600_000,
            max_holding_ms=7 * 24 * 60 * 60 * 1000,
            holding_period_ms=3_600_000,
            exit_policy_id="4h_time_exit",
        ),
        initial_equity=10_000.0,
    )

    assert trades.iloc[0]["exit_policy"] == "fixed_holding_window"
    assert trades.iloc[0]["requested_exit_policy"] == "4h_time_exit"
    assert trades.iloc[0]["canonical_exit_policy"] == "fixed_holding_window"


def test_execution_simulator_applies_funding_from_position_path() -> None:
    market = _market()
    market["funding_rate"] = [0.0, 0.0, 0.0008, 0.0008, 0.0008, 0.0008, 0.0, 0.0]
    trades, _ = ExecutionSimulator().simulate(
        pd.DataFrame(
            {
                "signal_id": ["s1"],
                "symbol": ["BTCUSDT"],
                "decision_time_ms": [int(market.iloc[0]["bar_time_ms"])],
                "side": ["long"],
                "signal_bar_close": [100.0],
            }
        ),
        market,
        costs=CostModel(fee_bps=0.0, slippage_bps=0.0, spread_bps=0.0, funding_rate=0.0),
        assumptions=ExecutionAssumptions(
            interval_ms=900_000,
            entry_latency_ms=900_000,
            entry_price_source="next_bar_open",
            min_holding_ms=3_600_000,
            max_holding_ms=7 * 24 * 60 * 60 * 1000,
            holding_period_ms=3_600_000,
        ),
        initial_equity=10_000.0,
    )

    assert trades.iloc[0]["funding_return"] == pytest.approx(-0.000075)
    assert trades.iloc[0]["net_return"] < trades.iloc[0]["gross_return"]


def test_execution_simulator_marks_end_of_data_fallback() -> None:
    market = _market(row_count=6)
    trades, _ = ExecutionSimulator().simulate(
        pd.DataFrame(
            {
                "signal_id": ["s1"],
                "symbol": ["BTCUSDT"],
                "decision_time_ms": [int(market.iloc[0]["bar_time_ms"])],
                "side": ["long"],
                "signal_bar_close": [100.0],
            }
        ),
        market,
        costs=CostModel(),
        assumptions=ExecutionAssumptions(
            interval_ms=900_000,
            entry_latency_ms=900_000,
            entry_price_source="next_bar_open",
            min_holding_ms=3_600_000,
            max_holding_ms=7 * 24 * 60 * 60 * 1000,
            holding_period_ms=24 * 60 * 60 * 1000,
        ),
        initial_equity=10_000.0,
    )

    assert trades.iloc[0]["exit_reason"] == "end_of_data_min_holding"
    assert bool(trades.iloc[0]["exit_used_fallback"]) is True


def test_exit_policy_result_shapes_include_mae_mfe_and_approximation_flag() -> None:
    fixed = fixed_holding_window_exit(
        entry_time_ms=0,
        exit_time_ms=3_600_000,
        entry_price=100.0,
        exit_price=103.0,
        side="long",
        path_high=104.0,
        path_low=98.0,
        costs_applied=True,
    )
    barrier = close_only_barrier_exit(
        entry_time_ms=0,
        exit_time_ms=3_600_000,
        entry_price=100.0,
        exit_price=103.0,
        side="long",
        target_return=0.02,
        stop_return=0.01,
        path_high=104.0,
        path_low=98.0,
        costs_applied=False,
    )

    assert fixed.barrier_hit_type == "time"
    assert fixed.max_adverse_excursion > 0
    assert barrier.barrier_hit_type == "target"
    assert barrier.approximate is True


def test_lower_timeframe_triple_barrier_hits_target_before_time_barrier() -> None:
    entry_time = 1_712_649_600_000

    result = triple_barrier_exit_from_lower_timeframe(
        entry_time_ms=entry_time,
        entry_price=100.0,
        side="long",
        time_exit_ms=entry_time + 3_600_000,
        time_exit_price=100.5,
        target_return=0.02,
        stop_return=0.01,
        lower_timeframe_market_data=_lower(entry_time, [(60_000, 103.0, 100.0, 102.5)]),
        costs_applied=True,
    )

    assert result.exit_reason == "triple_barrier_target"
    assert result.barrier_hit_type == "target"
    assert result.exit_price == pytest.approx(102.0)


def test_lower_timeframe_triple_barrier_hits_stop_before_target() -> None:
    entry_time = 1_712_649_600_000

    result = triple_barrier_exit_from_lower_timeframe(
        entry_time_ms=entry_time,
        entry_price=100.0,
        side="long",
        time_exit_ms=entry_time + 3_600_000,
        time_exit_price=100.5,
        target_return=0.02,
        stop_return=0.01,
        lower_timeframe_market_data=_lower(
            entry_time,
            [
                (60_000, 100.5, 98.5, 99.0),
                (120_000, 103.0, 100.0, 102.0),
            ],
        ),
        costs_applied=True,
    )

    assert result.exit_reason == "triple_barrier_stop"
    assert result.barrier_hit_type == "stop"
    assert result.exit_price == pytest.approx(99.0)


def test_lower_timeframe_triple_barrier_same_child_bar_uses_conservative_stop() -> None:
    entry_time = 1_712_649_600_000

    result = triple_barrier_exit_from_lower_timeframe(
        entry_time_ms=entry_time,
        entry_price=100.0,
        side="long",
        time_exit_ms=entry_time + 3_600_000,
        time_exit_price=100.5,
        target_return=0.02,
        stop_return=0.01,
        lower_timeframe_market_data=_lower(entry_time, [(60_000, 103.0, 98.5, 100.0)]),
        costs_applied=True,
    )

    assert result.exit_reason == "triple_barrier_ambiguous_stop_conservative"
    assert result.barrier_hit_type == "ambiguous_stop_conservative"
    assert result.exit_price == pytest.approx(99.0)
    assert result.approximate is True


def test_triple_barrier_falls_back_to_time_exit_when_no_barrier_hit() -> None:
    entry_time = 1_712_649_600_000

    result = triple_barrier_exit_from_lower_timeframe(
        entry_time_ms=entry_time,
        entry_price=100.0,
        side="long",
        time_exit_ms=entry_time + 3_600_000,
        time_exit_price=100.5,
        target_return=0.02,
        stop_return=0.01,
        lower_timeframe_market_data=_lower(
            entry_time,
            [
                (3_540_000, 100.5, 99.5, 100.9),
                (3_600_000, 100.6, 99.6, 101.25),
            ],
        ),
        costs_applied=True,
    )

    assert result.exit_reason == "holding_window"
    assert result.barrier_hit_type == "time"
    assert result.exit_time_ms == entry_time + 3_600_000
    assert result.exit_price == pytest.approx(101.25)
    assert result.exit_policy_id == "triple_barrier_atr"


def test_triple_barrier_rejects_missing_lower_timeframe_coverage() -> None:
    entry_time = 1_712_649_600_000

    with pytest.raises(ValueError, match="sequence coverage missing"):
        triple_barrier_exit_from_lower_timeframe(
            entry_time_ms=entry_time,
            entry_price=100.0,
            side="long",
            time_exit_ms=entry_time + 3_600_000,
            time_exit_price=100.5,
            target_return=0.02,
            stop_return=0.01,
            lower_timeframe_market_data=_lower(entry_time, [(4_000_000, 103.0, 98.5, 100.0)]),
            costs_applied=True,
        )


def test_triple_barrier_rejects_stale_lower_timeframe_no_hit_horizon() -> None:
    entry_time = 1_712_649_600_000

    with pytest.raises(ValueError, match="scheduled exit horizon"):
        triple_barrier_exit_from_lower_timeframe(
            entry_time_ms=entry_time,
            entry_price=100.0,
            side="long",
            time_exit_ms=entry_time + 3_600_000,
            time_exit_price=100.5,
            target_return=0.02,
            stop_return=0.01,
            lower_timeframe_market_data=_lower(entry_time, [(60_000, 100.5, 99.5, 100.0)]),
            costs_applied=True,
        )


def test_triple_barrier_filters_lower_timeframe_rows_by_symbol() -> None:
    entry_time = 1_712_649_600_000
    lower = pd.DataFrame(
        {
            "symbol": ["ETHUSDT", "BTCUSDT", "BTCUSDT"],
            "bar_time_ms": [entry_time + 60_000, entry_time + 3_540_000, entry_time + 3_600_000],
            "high": [103.0, 100.5, 100.6],
            "low": [98.5, 99.5, 99.6],
            "close": [100.0, 100.1, 100.2],
        }
    )

    result = triple_barrier_exit_from_lower_timeframe(
        entry_time_ms=entry_time,
        entry_price=100.0,
        side="long",
        time_exit_ms=entry_time + 3_600_000,
        time_exit_price=100.5,
        target_return=0.02,
        stop_return=0.01,
        lower_timeframe_market_data=lower,
        costs_applied=True,
        symbol="BTCUSDT",
    )

    assert result.exit_reason == "holding_window"
    assert result.barrier_hit_type == "time"


def test_short_triple_barrier_uses_inverse_thresholds() -> None:
    entry_time = 1_712_649_600_000

    result = triple_barrier_exit_from_lower_timeframe(
        entry_time_ms=entry_time,
        entry_price=100.0,
        side="short",
        time_exit_ms=entry_time + 3_600_000,
        time_exit_price=100.5,
        target_return=0.02,
        stop_return=0.01,
        lower_timeframe_market_data=_lower(entry_time, [(60_000, 100.5, 97.5, 98.0)]),
        costs_applied=True,
    )

    assert result.exit_reason == "triple_barrier_target"
    assert result.exit_price == pytest.approx(98.0)
