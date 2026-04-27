from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from tradingbotsuite.core.features import (
    compute_atr_percentile,
    compute_realized_volatility,
    compute_volatility_shock,
    infer_time_to_next_funding_ms,
    session_features,
)
from tradingbotsuite.core.math import BAR_INTERVAL_MS, atr_wilder, build_barriers, build_vertical_barrier, evaluate_exit_on_bar, hurst_exponent
from tradingbotsuite.core.models import Bar, PositionState, SignalDirection, TradeStatus


def atr_reference(bars: list[Bar], length: int) -> Decimal:
    ranges: list[Decimal] = []
    for index in range(1, len(bars)):
        current = bars[index]
        previous_close = bars[index - 1].close
        ranges.append(max(current.high - current.low, abs(current.high - previous_close), abs(current.low - previous_close)))
    atr = sum(ranges[:length], start=Decimal("0")) / Decimal(length)
    for current in ranges[length:]:
        atr = ((atr * Decimal(length - 1)) + current) / Decimal(length)
    return atr


def test_atr_matches_reference(sample_bars: list[Bar]) -> None:
    assert atr_wilder(sample_bars, 14) == atr_reference(sample_bars, 14)


def test_barrier_construction_is_directionally_symmetric() -> None:
    entry = Decimal("70500")
    atr = Decimal("250")
    long_tp, long_sl = build_barriers(
        entry_price=entry,
        atr=atr,
        direction=SignalDirection.LONG,
        tp_multiple=Decimal("1.5"),
        sl_multiple=Decimal("1.0"),
        price_tick=Decimal("0.1"),
    )
    short_tp, short_sl = build_barriers(
        entry_price=entry,
        atr=atr,
        direction=SignalDirection.SHORT,
        tp_multiple=Decimal("1.5"),
        sl_multiple=Decimal("1.0"),
        price_tick=Decimal("0.1"),
    )
    assert long_tp > entry > long_sl
    assert short_tp < entry < short_sl
    assert (long_tp - entry) == (entry - short_tp)
    assert (short_sl - entry) == (entry - long_sl)


@given(
    base=st.decimals(min_value="100", max_value="100000", places=1),
    atr=st.decimals(min_value="1", max_value="1000", places=1),
    scale=st.integers(min_value=1, max_value=10),
)
def test_barrier_scale_invariance(base: Decimal, atr: Decimal, scale: int) -> None:
    scale_decimal = Decimal(scale)
    tp1, sl1 = build_barriers(
        entry_price=base,
        atr=atr,
        direction=SignalDirection.LONG,
        tp_multiple=Decimal("1.5"),
        sl_multiple=Decimal("1.0"),
        price_tick=Decimal("0.1"),
    )
    tp2, sl2 = build_barriers(
        entry_price=base * scale_decimal,
        atr=atr * scale_decimal,
        direction=SignalDirection.LONG,
        tp_multiple=Decimal("1.5"),
        sl_multiple=Decimal("1.0"),
        price_tick=Decimal("0.1") * scale_decimal,
    )
    assert tp2 == tp1 * scale_decimal
    assert sl2 == sl1 * scale_decimal


def test_vertical_barrier_alignment() -> None:
    entry_bar_time_ms = 1712649600000
    assert build_vertical_barrier(entry_bar_time_ms, 24) == entry_bar_time_ms + (24 * BAR_INTERVAL_MS)


def test_first_trigger_wins_is_stop_loss_conservative() -> None:
    position = PositionState(
        symbol="BTCUSDT",
        status=TradeStatus.OPEN,
        direction=SignalDirection.LONG,
        position_size=Decimal("0.01"),
        entry_price=Decimal("100"),
        tp_price=Decimal("110"),
        sl_price=Decimal("95"),
        vertical_barrier_time_ms=9999999999999,
    )
    bar = Bar(time_ms=1, open=Decimal("100"), high=Decimal("111"), low=Decimal("94"), close=Decimal("100"))
    assert evaluate_exit_on_bar(position, bar, current_time_ms=1) == "stop_loss"


def test_hurst_exponent_distinguishes_persistent_from_mean_reverting_series() -> None:
    persistent = [Decimal(100 + index + (index % 3)) for index in range(64)]
    mean_reverting = [Decimal(100 + (1 if index % 2 == 0 else -1)) for index in range(64)]
    persistent_hurst = hurst_exponent(persistent, max_lag=10)
    mean_reverting_hurst = hurst_exponent(mean_reverting, max_lag=10)
    assert persistent_hurst is not None
    assert mean_reverting_hurst is not None
    assert persistent_hurst > mean_reverting_hurst


def test_realized_volatility_returns_value_for_valid_window(sample_bars: list[Bar]) -> None:
    closes = [bar.close for bar in (sample_bars * 2)[:40]]
    realized = compute_realized_volatility(closes, 20)
    assert realized is not None
    assert realized > Decimal("0")


def test_atr_percentile_is_bounded(sample_bars: list[Bar]) -> None:
    percentile = compute_atr_percentile(sample_bars * 2, atr_length=14, percentile_window_bars=20)
    assert percentile is not None
    assert Decimal("0") <= percentile <= Decimal("1")


def test_volatility_shock_detects_large_recent_change() -> None:
    closes = [Decimal("100") + Decimal(index) for index in range(30)] + [Decimal("180"), Decimal("240"), Decimal("320"), Decimal("410")]
    zscore, flagged = compute_volatility_shock(closes, window_bars=10, zscore_threshold=1.5)
    assert zscore is not None
    assert flagged is True


def test_time_to_next_funding_is_aligned_to_eight_hours() -> None:
    timestamp_ms = 1712649600000 + (3 * 60 * 60 * 1000)
    next_funding_ms = infer_time_to_next_funding_ms(timestamp_ms)
    assert (next_funding_ms - timestamp_ms) == 5 * 60 * 60 * 1000


def test_session_features_map_expected_utc_windows() -> None:
    asia_ts = int(datetime(2026, 4, 11, 3, 0, tzinfo=UTC).timestamp() * 1000)
    europe_ts = int(datetime(2026, 4, 11, 9, 0, tzinfo=UTC).timestamp() * 1000)
    us_ts = int(datetime(2026, 4, 11, 15, 0, tzinfo=UTC).timestamp() * 1000)
    asia = session_features(asia_ts)
    europe = session_features(europe_ts)
    us = session_features(us_ts)
    assert asia["session_asia"] == 1
    assert asia["session_europe"] == 0
    assert europe["session_europe"] == 1
    assert us["session_us"] == 1
