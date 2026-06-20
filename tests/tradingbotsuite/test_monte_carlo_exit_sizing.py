from __future__ import annotations

import pytest
import pandas as pd

from tradingbotsuite.research.monte_carlo_exit_sizing import (
    conservative_one_to_two_barrier_returns,
    martingale_fee_positive_recovery_streak,
    max_loss_streak,
    monte_carlo_summary,
    reprice_gross_returns,
    round_trip_fee_return,
)


def test_reprice_gross_returns_uses_taker_round_trip_without_funding_or_slippage() -> None:
    trades = pd.DataFrame(
        {
            "side": ["long", "short"],
            "gross_return": [0.01, -0.02],
        }
    )

    assert round_trip_fee_return(0.000432) == pytest.approx(0.000864)
    assert reprice_gross_returns(trades, taker_fee_rate=0.000432).tolist() == pytest.approx(
        [0.009136, -0.020864]
    )
    assert reprice_gross_returns(trades, taker_fee_rate=0.000432, side="long").tolist() == pytest.approx(
        [0.009136]
    )


def test_conservative_one_to_two_barrier_counts_ambiguous_as_stop_first() -> None:
    trades = pd.DataFrame(
        {
            "side": ["long", "long", "long", "long"],
            "gross_return": [0.0, 0.0, 0.003, -0.001],
            "max_adverse_excursion": [0.001, 0.006, 0.006, 0.001],
            "max_favorable_excursion": [0.011, 0.003, 0.011, 0.003],
        }
    )

    returns, audit = conservative_one_to_two_barrier_returns(
        trades,
        stop_return=0.005,
        taker_fee_rate=0.000432,
    )

    assert returns.tolist() == pytest.approx([0.009136, -0.005864, -0.005864, -0.001864])
    assert audit["target_only_count"] == 1
    assert audit["stop_only_count"] == 1
    assert audit["ambiguous_stop_first_count"] == 1
    assert audit["time_exit_count"] == 1


def test_martingale_recovery_streak_shrinks_when_fee_is_large_relative_to_stop() -> None:
    assert martingale_fee_positive_recovery_streak(stop_return=0.003, taker_fee_rate=0.000432) == 2
    assert martingale_fee_positive_recovery_streak(stop_return=0.005, taker_fee_rate=0.000432) == 3
    assert martingale_fee_positive_recovery_streak(stop_return=0.01, taker_fee_rate=0.000432) == 5


def test_monte_carlo_summary_is_seed_deterministic_and_reports_loss_streaks() -> None:
    returns = [0.02, -0.01, -0.01, 0.02, -0.01]

    first = monte_carlo_summary(returns, paths=250, seed=123)
    second = monte_carlo_summary(returns, paths=250, seed=123)

    assert first == second
    assert first["available"] is True
    assert first["horizon_trades"] == 5
    assert first["max_loss_streak_p95"] >= 2
    assert max_loss_streak(returns) == 2
