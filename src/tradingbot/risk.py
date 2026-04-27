from __future__ import annotations

import pandas as pd

from tradingbot.indicators import atr
from tradingbot.models import RiskConfig, Side


def compute_stop_distance(df: pd.DataFrame, index: int, risk: RiskConfig, entry_price: float | None = None) -> float:
    price = float(entry_price if entry_price is not None else df.iloc[index]["close"])
    if risk.use_fixed_stop_loss:
        return price * risk.fixed_stop_loss_pct
    atr_values = atr(df, risk.atr_stop_period).bfill().fillna(0.0)
    return max(float(atr_values.iloc[index]) * risk.atr_stop_multiplier, price * risk.min_stop_distance_pct)


def compute_initial_stop(df: pd.DataFrame, index: int, side: Side, risk: RiskConfig, entry_price: float | None = None) -> float:
    price = float(entry_price if entry_price is not None else df.iloc[index]["close"])
    stop_distance = compute_stop_distance(df, index, risk, price)
    if side == Side.LONG:
        return price - stop_distance
    return price + stop_distance


def compute_position_size(equity: float, entry_price: float, stop_price: float, risk: RiskConfig) -> float:
    stop_distance = abs(entry_price - stop_price)
    if stop_distance <= 0:
        return 0.0
    dollar_risk = equity * risk.risk_per_trade
    raw_qty = dollar_risk / stop_distance
    max_notional = equity * risk.leverage_cap
    capped_qty = min(raw_qty, max_notional / max(entry_price, 1e-9))
    return max(capped_qty, 0.0)
