from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(slots=True)
class TVBacktestResult:
    frame: pd.DataFrame
    summary: dict[str, float]


def run_tv_backtest(signal_frame: pd.DataFrame, max_bars_back_index: int, use_worst_case: bool) -> TVBacktestResult:
    frame = signal_frame.copy()
    market_price = frame["close"] if use_worst_case else (frame["high"] + frame["low"] + frame["open"] + frame["open"]) / 4.0
    start_long_trade = float(market_price.iloc[0]) if not frame.empty else 0.0
    start_short_trade = float(market_price.iloc[0]) if not frame.empty else 0.0
    total_short_profit = 0.0
    total_long_profit = 0.0
    wins = 0
    losses = 0
    early_signal_flip_count = 0
    lot_size = 1.0
    wins_series: list[float] = []
    losses_series: list[float] = []
    trade_count_series: list[float] = []
    early_flip_series: list[float] = []
    total_long_profit_series: list[float] = []
    total_short_profit_series: list[float] = []

    for idx, row in frame.iterrows():
        wins = 0
        losses = 0
        trade_count = 0
        early_signal_flip_count = 0
        total_long_profit = 0.0
        total_short_profit = 0.0
        if idx > max_bars_back_index:
            current_price = float(market_price.iloc[idx])
            if bool(row["start_long_trade"]):
                start_short_trade = 0.0
                early_signal_flip_count = 1 if bool(row["is_early_signal_flip"]) else 0
                start_long_trade = current_price
                trade_count = 1
            if bool(row["end_long_trade"]):
                delta = current_price - start_long_trade
                wins = 1 if delta > 0 else 0
                losses = 1 if delta < 0 else 0
                total_long_profit = delta * lot_size
            if bool(row["start_short_trade"]):
                start_long_trade = 0.0
                start_short_trade = current_price
                trade_count = 1
            if bool(row["end_short_trade"]):
                early_signal_flip_count = 1 if bool(row["is_early_signal_flip"]) else 0
                delta = start_short_trade - current_price
                wins = 1 if delta > 0 else 0
                losses = 1 if delta < 0 else 0
                total_short_profit = delta * lot_size
        wins_series.append(float(wins))
        losses_series.append(float(losses))
        trade_count_series.append(float(trade_count))
        early_flip_series.append(float(early_signal_flip_count))
        total_long_profit_series.append(float(total_long_profit))
        total_short_profit_series.append(float(total_short_profit))

    frame["tv_total_wins"] = pd.Series(wins_series, index=frame.index, dtype=float).cumsum()
    frame["tv_total_losses"] = pd.Series(losses_series, index=frame.index, dtype=float).cumsum()
    frame["tv_total_trades"] = (pd.Series(wins_series, index=frame.index, dtype=float) + pd.Series(losses_series, index=frame.index, dtype=float)).cumsum()
    frame["tv_total_early_signal_flips"] = pd.Series(early_flip_series, index=frame.index, dtype=float).cumsum()
    frame["tv_long_profit"] = pd.Series(total_long_profit_series, index=frame.index, dtype=float).cumsum()
    frame["tv_short_profit"] = pd.Series(total_short_profit_series, index=frame.index, dtype=float).cumsum()
    frame["tv_long_short_profit"] = frame["tv_long_profit"] + frame["tv_short_profit"]
    frame["tv_win_loss_ratio"] = frame["tv_total_wins"] / frame["tv_total_trades"].replace(0.0, pd.NA)
    frame["tv_win_rate"] = frame["tv_total_wins"] / (frame["tv_total_wins"] + frame["tv_total_losses"]).replace(0.0, pd.NA)

    summary = {
        "total_wins": float(frame["tv_total_wins"].iloc[-1]) if not frame.empty else 0.0,
        "total_losses": float(frame["tv_total_losses"].iloc[-1]) if not frame.empty else 0.0,
        "total_trades": float(frame["tv_total_trades"].iloc[-1]) if not frame.empty else 0.0,
        "early_signal_flips": float(frame["tv_total_early_signal_flips"].iloc[-1]) if not frame.empty else 0.0,
        "win_loss_ratio": float(frame["tv_win_loss_ratio"].iloc[-1]) if not frame.empty and pd.notna(frame["tv_win_loss_ratio"].iloc[-1]) else 0.0,
        "win_rate": float(frame["tv_win_rate"].iloc[-1]) if not frame.empty and pd.notna(frame["tv_win_rate"].iloc[-1]) else 0.0,
    }
    return TVBacktestResult(frame=frame, summary=summary)
