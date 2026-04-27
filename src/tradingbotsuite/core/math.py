from __future__ import annotations

import math
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal, localcontext

from tradingbotsuite.core.models import Bar, ExitReason, PositionState, SignalDirection

BAR_INTERVAL_MS = 15 * 60 * 1000


def quantize_to_step(value: Decimal, step: Decimal, rounding: str = ROUND_HALF_UP) -> Decimal:
    if step <= 0:
        raise ValueError("step must be positive")
    with localcontext() as ctx:
        ctx.rounding = rounding
        units = (value / step).quantize(Decimal("1"))
    return units * step


def true_range(current: Bar, previous_close: Decimal) -> Decimal:
    high_low = current.high - current.low
    high_close = abs(current.high - previous_close)
    low_close = abs(current.low - previous_close)
    return max(high_low, high_close, low_close)


def atr_wilder(bars: list[Bar], length: int) -> Decimal:
    if length <= 0:
        raise ValueError("length must be positive")
    if len(bars) < length + 1:
        raise ValueError("need at least length + 1 closed bars")

    ranges = [true_range(bars[index], bars[index - 1].close) for index in range(1, len(bars))]
    atr = sum(ranges[:length], start=Decimal("0")) / Decimal(length)
    for current in ranges[length:]:
        atr = ((atr * Decimal(length - 1)) + current) / Decimal(length)
    return atr


def hurst_exponent(closes: list[Decimal], *, min_lag: int = 2, max_lag: int = 20) -> Decimal | None:
    if len(closes) < max(max_lag + 2, 32):
        return None
    values = [float(close) for close in closes]
    x_values: list[float] = []
    y_values: list[float] = []
    window = max(8, min_lag * 4)
    max_window = min(len(values) // 2, max(max_lag * 4, window))
    while window <= max_window:
        rs_values: list[float] = []
        chunk_count = len(values) // window
        for chunk_index in range(chunk_count):
            chunk = values[chunk_index * window : (chunk_index + 1) * window]
            if len(chunk) < window:
                continue
            mean = sum(chunk) / len(chunk)
            centered = [value - mean for value in chunk]
            cumulative = []
            running = 0.0
            for value in centered:
                running += value
                cumulative.append(running)
            range_rs = max(cumulative) - min(cumulative)
            variance = sum((value - mean) ** 2 for value in chunk) / len(chunk)
            if variance <= 0 or range_rs <= 0:
                continue
            rs_values.append(range_rs / math.sqrt(variance))
        if rs_values:
            x_values.append(math.log(window))
            y_values.append(math.log(sum(rs_values) / len(rs_values)))
        window *= 2

    if len(x_values) < 2:
        return None

    x_mean = sum(x_values) / len(x_values)
    y_mean = sum(y_values) / len(y_values)
    variance_x = sum((value - x_mean) ** 2 for value in x_values)
    if variance_x == 0:
        return None
    covariance = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values, strict=True))
    slope = covariance / variance_x
    bounded = min(max(slope, 0.0), 1.0)
    return Decimal(str(round(bounded, 6)))


def build_vertical_barrier(entry_bar_time_ms: int, bar_budget: int) -> int:
    if bar_budget <= 0:
        raise ValueError("bar_budget must be positive")
    return entry_bar_time_ms + (bar_budget * BAR_INTERVAL_MS)


def build_barriers(
    *,
    entry_price: Decimal,
    atr: Decimal,
    direction: SignalDirection,
    tp_multiple: Decimal,
    sl_multiple: Decimal,
    price_tick: Decimal,
) -> tuple[Decimal, Decimal]:
    tp_raw = entry_price + (tp_multiple * atr) if direction == SignalDirection.LONG else entry_price - (tp_multiple * atr)
    sl_raw = entry_price - (sl_multiple * atr) if direction == SignalDirection.LONG else entry_price + (sl_multiple * atr)
    if direction == SignalDirection.LONG:
        tp_price = quantize_to_step(tp_raw, price_tick, ROUND_FLOOR)
        sl_price = quantize_to_step(sl_raw, price_tick, ROUND_CEILING)
    else:
        tp_price = quantize_to_step(tp_raw, price_tick, ROUND_CEILING)
        sl_price = quantize_to_step(sl_raw, price_tick, ROUND_FLOOR)
    return tp_price, sl_price


def apply_slippage(price: Decimal, slippage_bps: Decimal, direction: SignalDirection) -> Decimal:
    multiplier = Decimal("1") + (slippage_bps / Decimal("10000"))
    if direction == SignalDirection.LONG:
        return price * multiplier
    return price / multiplier


def realized_slippage_bps(reference_price: Decimal, actual_price: Decimal, direction: SignalDirection) -> Decimal | None:
    if reference_price <= Decimal("0") or actual_price <= Decimal("0"):
        return None
    if direction == SignalDirection.LONG:
        return ((actual_price - reference_price) / reference_price) * Decimal("10000")
    return ((reference_price - actual_price) / reference_price) * Decimal("10000")


def evaluate_exit_on_bar(position: PositionState, bar: Bar, current_time_ms: int) -> ExitReason | None:
    if position.status != "open":
        return None
    if position.direction == SignalDirection.LONG:
        if position.sl_price is not None and bar.low <= position.sl_price:
            return ExitReason.STOP_LOSS
        if position.tp_price is not None and bar.high >= position.tp_price:
            return ExitReason.TAKE_PROFIT
    else:
        if position.sl_price is not None and bar.high >= position.sl_price:
            return ExitReason.STOP_LOSS
        if position.tp_price is not None and bar.low <= position.tp_price:
            return ExitReason.TAKE_PROFIT
    if position.vertical_barrier_time_ms is not None and current_time_ms >= position.vertical_barrier_time_ms:
        return ExitReason.TIME_BARRIER
    return None
