from __future__ import annotations

import pandas as pd

from tradingbot.models import OrderBlock, PositionState, Side


def long_exit_confirmed_by_block(block: OrderBlock, row: pd.Series) -> bool:
    return float(row["close"]) < block.bottom


def short_exit_confirmed_by_block(block: OrderBlock, row: pd.Series) -> bool:
    return float(row["close"]) > block.top


def confirm_pending_order_block_exit(position: PositionState, block: OrderBlock, five_minute_window: pd.DataFrame) -> tuple[bool, pd.Series | None]:
    if five_minute_window.empty:
        return False, None
    for _, row in five_minute_window.iterrows():
        if position.side == Side.LONG and long_exit_confirmed_by_block(block, row):
            return True, row
        if position.side == Side.SHORT and short_exit_confirmed_by_block(block, row):
            return True, row
    return False, None
