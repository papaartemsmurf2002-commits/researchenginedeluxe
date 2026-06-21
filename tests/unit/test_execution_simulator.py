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
    assert trades.iloc[0]["exit_policy"] == "fixed_holding_window"
    assert trades.iloc[0]["barrier_hit_type"] == "time"
    assert trades.iloc[0]["exit_sequence_proof"] == "primary_bar_time"
    assert equity.iloc[-1]["equity"] != 10_000.0


def test_signal_bar_close_plus_latency_uses_signal_close_after_latency_selection() -> None:
    market = _market()
    signals = pd.DataFrame(
        {
            "signal_id": ["s1"],
            "symbol": ["BTCUSDT"],
            "decision_time_ms": [int(market.iloc[0]["bar_time_ms"]) + 900_000],
            "side": ["long"],
            "signal_bar_close": [999.0],
        }
    )
    assumptions = ExecutionAssumptions(
        interval_ms=900_000,
        entry_latency_ms=900_000,
        entry_price_source="signal_bar_close_plus_latency",
        min_holding_ms=3_600_000,
        max_holding_ms=7 * 24 * 60 * 60 * 1000,
        holding_period_ms=3_600_000,
    )

    trades, _ = ExecutionSimulator().simulate(
        signals,
        market,
        costs=CostModel(fee_bps=0.0, slippage_bps=0.0, spread_bps=0.0),
        assumptions=assumptions,
        initial_equity=10_000.0,
    )

    assert trades.iloc[0]["entry_time_ms"] == market.iloc[2]["bar_time_ms"]
    assert trades.iloc[0]["entry_price"] == pytest.approx(999.0)
    assert trades.iloc[0]["entry_price"] != pytest.approx(market.iloc[2]["open"])


def test_primary_bar_open_plus_latency_uses_latency_bar_open() -> None:
    market = _market()
    signals = pd.DataFrame(
        {
            "signal_id": ["s1"],
            "symbol": ["BTCUSDT"],
            "decision_time_ms": [int(market.iloc[0]["bar_time_ms"]) + 900_000],
            "side": ["long"],
            "signal_bar_close": [999.0],
        }
    )
    assumptions = ExecutionAssumptions(
        interval_ms=900_000,
        entry_latency_ms=900_000,
        entry_price_source="primary_bar_open_plus_latency",
        min_holding_ms=3_600_000,
        max_holding_ms=7 * 24 * 60 * 60 * 1000,
        holding_period_ms=3_600_000,
    )

    trades, _ = ExecutionSimulator().simulate(
        signals,
        market,
        costs=CostModel(fee_bps=0.0, slippage_bps=0.0, spread_bps=0.0),
        assumptions=assumptions,
        initial_equity=10_000.0,
    )

    assert trades.iloc[0]["entry_time_ms"] == market.iloc[2]["bar_time_ms"]
    assert trades.iloc[0]["entry_price"] == pytest.approx(market.iloc[2]["open"])
    assert trades.iloc[0]["entry_price"] != 999.0


def test_execution_simulator_uses_perp_last_funding_rate_alias_for_costs() -> None:
    market = _market().drop(columns=["funding_rate"])
    market["perp_last_funding_rate"] = 0.00016
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

    trades, _ = ExecutionSimulator().simulate(
        signals,
        market,
        costs=CostModel(fee_bps=0.0, slippage_bps=0.0, spread_bps=0.0, funding_rate=0.0),
        assumptions=assumptions,
        initial_equity=10_000.0,
    )

    assert trades.iloc[0]["funding_return"] == pytest.approx(-0.00002)


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


def test_lower_timeframe_entry_source_uses_lower_open_at_latency_fill_time() -> None:
    market = _market()
    decision_time = int(market.iloc[0]["bar_time_ms"])
    lower = pd.DataFrame(
        {
            "symbol": ["BTCUSDT", "BTCUSDT", "BTCUSDT"],
            "bar_time_ms": [decision_time + 30_000, decision_time + 60_000, decision_time + 120_000],
            "open": [190.0, 200.0, 210.0],
            "high": [191.0, 201.0, 211.0],
            "low": [189.0, 199.0, 209.0],
            "close": [190.5, 200.5, 210.5],
        }
    )

    trades, _ = ExecutionSimulator().simulate(
        pd.DataFrame(
            {
                "signal_id": ["s1"],
                "symbol": ["BTCUSDT"],
                "decision_time_ms": [decision_time],
                "side": ["long"],
                "signal_bar_close": [100.5],
            }
        ),
        market,
        costs=CostModel(),
        assumptions=ExecutionAssumptions(
            interval_ms=900_000,
            entry_latency_ms=60_000,
            entry_price_source="lower_timeframe_execution_path",
            min_holding_ms=3_600_000,
            max_holding_ms=7 * 24 * 60 * 60 * 1000,
            holding_period_ms=3_600_000,
        ),
        initial_equity=10_000.0,
        lower_timeframe_market_data=lower,
    )

    row = trades.iloc[0]
    assert row["entry_target_time_ms"] == decision_time + 60_000
    assert row["entry_time_ms"] == decision_time + 60_000
    assert row["entry_primary_bar_time_ms"] == decision_time
    assert row["entry_bar_index"] == 0
    assert row["entry_price"] == pytest.approx(200.0)
    assert row["entry_sequence_proof"] == "lower_timeframe_open"
    assert row["entry_price_source"] == "lower_timeframe_execution_path"
    assert row["holding_ms"] == int(row["exit_time_ms"]) - int(row["entry_time_ms"])


def test_lower_timeframe_entry_source_uses_next_lower_open_after_unaligned_latency() -> None:
    market = _market()
    decision_time = int(market.iloc[0]["bar_time_ms"])
    lower = pd.DataFrame(
        {
            "bar_time_ms": [decision_time + 60_000, decision_time + 120_000],
            "open": [200.0, 210.0],
        }
    )

    trades, _ = ExecutionSimulator().simulate(
        pd.DataFrame(
            {
                "signal_id": ["s1"],
                "symbol": ["BTCUSDT"],
                "decision_time_ms": [decision_time],
                "side": ["long"],
                "signal_bar_close": [100.5],
            }
        ),
        market,
        costs=CostModel(),
        assumptions=ExecutionAssumptions(
            interval_ms=900_000,
            entry_latency_ms=90_000,
            entry_price_source="lower_timeframe_execution_path",
            min_holding_ms=3_600_000,
            max_holding_ms=7 * 24 * 60 * 60 * 1000,
            holding_period_ms=3_600_000,
        ),
        initial_equity=10_000.0,
        lower_timeframe_market_data=lower,
    )

    assert trades.iloc[0]["entry_target_time_ms"] == decision_time + 90_000
    assert trades.iloc[0]["entry_time_ms"] == decision_time + 120_000
    assert trades.iloc[0]["entry_price"] == pytest.approx(210.0)


def test_lower_timeframe_entry_source_fails_closed_without_open_or_coverage() -> None:
    market = _market()
    decision_time = int(market.iloc[0]["bar_time_ms"])
    assumptions = ExecutionAssumptions(
        interval_ms=900_000,
        entry_latency_ms=60_000,
        entry_price_source="lower_timeframe_execution_path",
        min_holding_ms=3_600_000,
        max_holding_ms=7 * 24 * 60 * 60 * 1000,
        holding_period_ms=3_600_000,
    )
    signals = pd.DataFrame(
        {
            "signal_id": ["s1"],
            "symbol": ["BTCUSDT"],
            "decision_time_ms": [decision_time],
            "side": ["long"],
            "signal_bar_close": [100.5],
        }
    )

    with pytest.raises(ValueError, match="missing required columns: open"):
        ExecutionSimulator().simulate(
            signals,
            market,
            costs=CostModel(),
            assumptions=assumptions,
            initial_equity=10_000.0,
            lower_timeframe_market_data=pd.DataFrame({"bar_time_ms": [decision_time + 60_000], "close": [200.0]}),
        )

    with pytest.raises(ValueError, match="entry sequence coverage missing"):
        ExecutionSimulator().simulate(
            signals,
            market,
            costs=CostModel(),
            assumptions=assumptions,
            initial_equity=10_000.0,
            lower_timeframe_market_data=pd.DataFrame({"bar_time_ms": [decision_time + 30_000], "open": [200.0]}),
        )


def test_same_primary_bar_exit_requires_lower_timeframe_sequence_proof() -> None:
    market = _market()
    entry_time = int(market.iloc[0]["bar_time_ms"])
    lower = pd.DataFrame(
        {
            "bar_time_ms": [entry_time + 60_000],
            "high": [103.0],
            "low": [100.0],
            "close": [102.5],
        }
    )

    trades, _ = ExecutionSimulator().simulate(
        pd.DataFrame(
            {
                "signal_id": ["s1"],
                "symbol": ["BTCUSDT"],
                "decision_time_ms": [entry_time],
                "side": ["long"],
                "signal_bar_close": [100.5],
            }
        ),
        market,
        costs=CostModel(),
        assumptions=ExecutionAssumptions(
            interval_ms=900_000,
            entry_latency_ms=0,
            entry_price_source="next_bar_open",
            min_holding_ms=3_600_000,
            max_holding_ms=7 * 24 * 60 * 60 * 1000,
            holding_period_ms=3_600_000,
            exit_policy_id="triple_barrier_atr",
            target_return=0.02,
            stop_return=0.01,
            exit_price_source="lower_timeframe_ohlc_sequence",
        ),
        initial_equity=10_000.0,
        lower_timeframe_market_data=lower,
    )

    assert trades.iloc[0]["exit_bar_index"] == trades.iloc[0]["entry_bar_index"]
    assert trades.iloc[0]["exit_sequence_proof"] == "lower_timeframe_ohlc"
    assert trades.iloc[0]["exit_reason"] == "triple_barrier_target"


def test_same_primary_bar_target_without_lower_frame_is_rejected() -> None:
    market = _market()
    assumptions = ExecutionAssumptions(
        interval_ms=900_000,
        entry_latency_ms=0,
        entry_price_source="next_bar_open",
        min_holding_ms=3_600_000,
        max_holding_ms=7 * 24 * 60 * 60 * 1000,
        holding_period_ms=3_600_000,
        exit_policy_id="triple_barrier_atr",
        target_return=0.02,
        stop_return=0.01,
        exit_price_source="lower_timeframe_ohlc_sequence",
    )

    with pytest.raises(ValueError, match="lower_timeframe_ohlc_sequence requires lower_timeframe_market_data"):
        ExecutionSimulator().simulate(
            pd.DataFrame(
                {
                    "signal_id": ["s1"],
                    "symbol": ["BTCUSDT"],
                    "decision_time_ms": [int(market.iloc[0]["bar_time_ms"])],
                    "side": ["long"],
                    "signal_bar_close": [100.5],
                }
            ),
            market,
            costs=CostModel(),
            assumptions=assumptions,
            initial_equity=10_000.0,
        )


def test_lower_timeframe_rows_at_or_before_entry_are_ignored() -> None:
    market = _market()
    entry_time = int(market.iloc[0]["bar_time_ms"])
    lower = pd.DataFrame(
        {
            "bar_time_ms": [entry_time, entry_time + 60_000, entry_time + 3_600_000],
            "high": [103.0, 100.5, 100.6],
            "low": [98.0, 99.5, 99.6],
            "close": [100.0, 100.1, 100.2],
        }
    )

    trades, _ = ExecutionSimulator().simulate(
        pd.DataFrame(
            {
                "signal_id": ["s1"],
                "symbol": ["BTCUSDT"],
                "decision_time_ms": [entry_time],
                "side": ["long"],
                "signal_bar_close": [100.5],
            }
        ),
        market,
        costs=CostModel(),
        assumptions=ExecutionAssumptions(
            interval_ms=900_000,
            entry_latency_ms=0,
            entry_price_source="next_bar_open",
            min_holding_ms=3_600_000,
            max_holding_ms=7 * 24 * 60 * 60 * 1000,
            holding_period_ms=3_600_000,
            exit_policy_id="triple_barrier_atr",
            target_return=0.02,
            stop_return=0.01,
            exit_price_source="lower_timeframe_ohlc_sequence",
        ),
        initial_equity=10_000.0,
        lower_timeframe_market_data=lower,
    )

    assert trades.iloc[0]["exit_reason"] == "holding_window"
    assert trades.iloc[0]["exit_time_ms"] == entry_time + 3_600_000
    assert trades.iloc[0]["exit_price"] == pytest.approx(100.2)
    assert trades.iloc[0]["exit_sequence_proof"] == "lower_timeframe_ohlc"


def test_triple_barrier_rejects_lower_timeframe_coverage_gap() -> None:
    market = _market()
    entry_time = int(market.iloc[0]["bar_time_ms"])
    lower = pd.DataFrame(
        {
            "bar_time_ms": [entry_time + 10_000_000],
            "high": [103.0],
            "low": [98.5],
            "close": [100.0],
        }
    )

    with pytest.raises(ValueError, match="sequence coverage missing"):
        ExecutionSimulator().simulate(
            pd.DataFrame(
                {
                    "signal_id": ["s1"],
                    "symbol": ["BTCUSDT"],
                    "decision_time_ms": [entry_time],
                    "side": ["long"],
                    "signal_bar_close": [100.5],
                }
            ),
            market,
            costs=CostModel(),
            assumptions=ExecutionAssumptions(
                interval_ms=900_000,
                entry_latency_ms=0,
                entry_price_source="next_bar_open",
                min_holding_ms=3_600_000,
                max_holding_ms=7 * 24 * 60 * 60 * 1000,
                holding_period_ms=3_600_000,
                exit_policy_id="triple_barrier_atr",
                target_return=0.02,
                stop_return=0.01,
                exit_price_source="lower_timeframe_ohlc_sequence",
            ),
            initial_equity=10_000.0,
            lower_timeframe_market_data=lower,
        )


def test_unsupported_exit_policy_is_rejected() -> None:
    market = _market()

    with pytest.raises(ValueError, match="unsupported exit_policy_id"):
        ExecutionSimulator().simulate(
            pd.DataFrame(
                {
                    "signal_id": ["s1"],
                    "symbol": ["BTCUSDT"],
                    "decision_time_ms": [int(market.iloc[0]["bar_time_ms"])],
                    "side": ["long"],
                    "signal_bar_close": [100.5],
                }
            ),
            market,
            costs=CostModel(),
            assumptions=ExecutionAssumptions(
                interval_ms=900_000,
                entry_latency_ms=0,
                entry_price_source="next_bar_open",
                min_holding_ms=3_600_000,
                max_holding_ms=7 * 24 * 60 * 60 * 1000,
                holding_period_ms=3_600_000,
                exit_policy_id="unknown_exit_policy",
            ),
            initial_equity=10_000.0,
        )


@pytest.mark.parametrize(
    ("policy", "target_return", "stop_return", "barrier", "approximate"),
    [
        ("volatility_scaled_barrier", 0.10, 0.01, "stop", True),
        ("regime_flip_exit", None, None, "regime_flip", False),
        ("funding_adverse_exit", 0.00005, None, "funding_adverse", False),
        ("alpha_decay_exit", 0.1, None, "alpha_decay", False),
        ("adverse_selection_exit", 20.0, 0.1, "adverse_selection", False),
        ("trailing_atr_after_profit", 0.02, 0.015, "trailing_stop", True),
        ("max_mae_stop", None, 0.01, "stop", True),
    ],
)
def test_primary_bar_exit_policies_record_trade_metadata(
    policy: str,
    target_return: float | None,
    stop_return: float | None,
    barrier: str,
    approximate: bool,
) -> None:
    market = _market()
    market["top_regime_label"] = ["trend", "trend", "range", "range", "range", "range", "range", "range", "range", "range", "range", "range"]
    market["directional_slope_atr"] = [0.4, 0.3, 0.05, -0.1, -0.2, -0.3, -0.3, -0.3, -0.3, -0.3, -0.3, -0.3]
    market["primary_signed_imbalance_ratio"] = [0.2, 0.1, -0.2, -0.3, -0.3, -0.3, -0.3, -0.3, -0.3, -0.3, -0.3, -0.3]
    market["realized_volatility"] = [0.01] * len(market)
    market.loc[2:, "funding_rate"] = 0.00009
    market.loc[2:, "spread_bps"] = 30.0
    market.loc[4:, "close"] = 99.0
    market.loc[4:, "low"] = 98.0
    signal_time = int(market.iloc[0]["bar_time_ms"])

    trades, _ = ExecutionSimulator().simulate(
        pd.DataFrame(
            {
                "signal_id": ["s1"],
                "symbol": ["BTCUSDT"],
                "decision_time_ms": [signal_time],
                "side": ["long"],
                "signal_bar_close": [100.5],
            }
        ),
        market,
        costs=CostModel(),
        assumptions=ExecutionAssumptions(
            interval_ms=900_000,
            entry_latency_ms=0,
            entry_price_source="next_bar_open",
            min_holding_ms=3_600_000,
            max_holding_ms=7 * 24 * 60 * 60 * 1000,
            holding_period_ms=3_600_000,
            exit_policy_id=policy,
            target_return=target_return,
            stop_return=stop_return,
            exit_price_source="primary_close",
        ),
        initial_equity=10_000.0,
    )

    row = trades.iloc[0]
    assert row["exit_policy"] == policy
    assert row["requested_exit_policy"] == policy
    if policy == "volatility_scaled_barrier":
        assert row["canonical_exit_policy"] == "static_primary_close_barrier"
    else:
        assert row["canonical_exit_policy"] == policy
    assert row["barrier_hit_type"] == barrier
    assert row["exit_sequence_proof"] == "primary_bar_time"
    assert row["exit_price_source"] == "primary_close"
    assert bool(row["exit_approximate"]) is approximate
    assert row["max_adverse_excursion"] >= 0.0
    assert row["max_favorable_excursion"] >= 0.0


def test_triple_barrier_trade_records_exit_policy_barrier_type_and_approximation() -> None:
    market = _market()
    entry_time = int(market.iloc[0]["bar_time_ms"])
    lower = pd.DataFrame(
        {
            "bar_time_ms": [entry_time + 60_000],
            "high": [103.0],
            "low": [98.5],
            "close": [100.0],
        }
    )

    trades, _ = ExecutionSimulator().simulate(
        pd.DataFrame(
            {
                "signal_id": ["s1"],
                "symbol": ["BTCUSDT"],
                "decision_time_ms": [entry_time],
                "side": ["long"],
                "signal_bar_close": [100.5],
            }
        ),
        market,
        costs=CostModel(),
        assumptions=ExecutionAssumptions(
            interval_ms=900_000,
            entry_latency_ms=0,
            entry_price_source="next_bar_open",
            min_holding_ms=3_600_000,
            max_holding_ms=7 * 24 * 60 * 60 * 1000,
            holding_period_ms=3_600_000,
            exit_policy_id="triple_barrier_atr",
            target_return=0.02,
            stop_return=0.01,
            exit_price_source="lower_timeframe_ohlc_sequence",
        ),
        initial_equity=10_000.0,
        lower_timeframe_market_data=lower,
    )

    assert trades.iloc[0]["exit_policy"] == "triple_barrier_atr"
    assert trades.iloc[0]["barrier_hit_type"] == "ambiguous_stop_conservative"
    assert bool(trades.iloc[0]["exit_approximate"]) is True
