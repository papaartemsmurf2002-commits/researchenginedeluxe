from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from tradingbotsuite.backtesting.costs import CostModel

EntryPriceSource = Literal[
    "next_bar_open",
    "signal_bar_close_plus_latency",
    "vwap_approximation",
    "lower_timeframe_execution_path",
]


@dataclass(frozen=True, slots=True)
class ExecutionAssumptions:
    interval_ms: int
    entry_latency_ms: int
    entry_price_source: EntryPriceSource
    min_holding_ms: int
    max_holding_ms: int
    holding_period_ms: int
    allow_same_bar_exit: bool = False

    def to_payload(self) -> dict[str, object]:
        return {
            "interval_ms": int(self.interval_ms),
            "entry_latency_ms": int(self.entry_latency_ms),
            "entry_price_source": self.entry_price_source,
            "min_holding_ms": int(self.min_holding_ms),
            "max_holding_ms": int(self.max_holding_ms),
            "holding_period_ms": int(self.holding_period_ms),
            "allow_same_bar_exit": bool(self.allow_same_bar_exit),
        }


class ExecutionSimulator:
    """Event overlay for deterministic bar-based entries and holding-window exits."""

    def simulate(
        self,
        signals: pd.DataFrame,
        market_data: pd.DataFrame,
        *,
        costs: CostModel,
        assumptions: ExecutionAssumptions,
        initial_equity: float,
        lower_timeframe_market_data: pd.DataFrame | None = None,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        self._validate_assumptions(assumptions, lower_timeframe_market_data)
        if signals.empty:
            return self._empty_trades(), _equity_curve(initial_equity, market_data)

        market = market_data.sort_values("bar_time_ms", kind="mergesort").reset_index(drop=True)
        candidate_rows: list[dict[str, object]] = []
        next_available_entry_time = -1
        for signal in signals.sort_values("decision_time_ms", kind="mergesort").to_dict("records"):
            entry_index = self._entry_index(signal, market, assumptions)
            if entry_index is None:
                continue
            entry_row = market.iloc[entry_index]
            entry_time = int(entry_row["bar_time_ms"])
            if entry_time < next_available_entry_time:
                continue
            exit_index = self._exit_index(entry_index, market, assumptions)
            if exit_index is None:
                continue
            exit_row = market.iloc[exit_index]
            if exit_index <= entry_index and not assumptions.allow_same_bar_exit:
                raise ValueError("same-bar entry/exit is forbidden without lower-timeframe sequence proof")
            entry_price = self._entry_price(signal, entry_row, assumptions)
            exit_price = float(exit_row["close"])
            side = str(signal["side"]).lower()
            holding_ms = int(exit_row["bar_time_ms"]) - int(entry_row["bar_time_ms"])
            funding_rate = _optional_float(entry_row.get("funding_rate"))
            spread_bps = _optional_float(entry_row.get("spread_bps"))
            cost = costs.estimate(
                entry_price=entry_price,
                exit_price=exit_price,
                side=side,
                holding_ms=holding_ms,
                funding_rate=funding_rate,
                spread_bps=spread_bps,
            )
            candidate_rows.append(
                {
                    "trade_id": f"trade-{len(candidate_rows):06d}",
                    "signal_id": str(signal.get("signal_id", f"signal-{len(candidate_rows):06d}")),
                    "symbol": str(signal.get("symbol", "")),
                    "side": side,
                    "entry_time_ms": int(entry_row["bar_time_ms"]),
                    "exit_time_ms": int(exit_row["bar_time_ms"]),
                    "entry_price": float(entry_price),
                    "exit_price": float(exit_price),
                    "holding_ms": int(holding_ms),
                    "gross_return": cost.gross_return,
                    "fee_return": cost.fee_return,
                    "slippage_return": cost.slippage_return,
                    "spread_return": cost.spread_return,
                    "funding_return": cost.funding_return,
                    "net_return": cost.net_return,
                    "entry_price_source": assumptions.entry_price_source,
                    "exit_reason": "holding_window",
                }
            )
            next_available_entry_time = int(exit_row["bar_time_ms"])

        trades = pd.DataFrame(candidate_rows)
        return trades, _equity_curve(initial_equity, market, trades)

    def _validate_assumptions(
        self,
        assumptions: ExecutionAssumptions,
        lower_timeframe_market_data: pd.DataFrame | None,
    ) -> None:
        if assumptions.interval_ms <= 0:
            raise ValueError("interval_ms must be positive")
        if assumptions.entry_latency_ms < 0:
            raise ValueError("entry_latency_ms must be non-negative")
        if assumptions.holding_period_ms < assumptions.min_holding_ms:
            raise ValueError("holding_period_ms must be at least min_holding_ms")
        if assumptions.holding_period_ms > assumptions.max_holding_ms:
            raise ValueError("holding_period_ms must be at most max_holding_ms")
        if assumptions.min_holding_ms < 60 * 60 * 1000:
            raise ValueError("minimum holding window must be at least approximately 1 hour")
        if assumptions.max_holding_ms > 7 * 24 * 60 * 60 * 1000:
            raise ValueError("maximum holding window must not exceed approximately 1 week")
        if assumptions.entry_price_source == "lower_timeframe_execution_path" and (
            lower_timeframe_market_data is None or lower_timeframe_market_data.empty
        ):
            raise ValueError("lower_timeframe_execution_path requires lower_timeframe_market_data")

    def _entry_index(
        self,
        signal: dict[str, object],
        market: pd.DataFrame,
        assumptions: ExecutionAssumptions,
    ) -> int | None:
        decision_time = int(signal["decision_time_ms"])
        if assumptions.entry_price_source == "signal_bar_close_plus_latency":
            target_time = decision_time + int(assumptions.entry_latency_ms)
        else:
            target_time = decision_time + int(assumptions.entry_latency_ms)
        candidates = market.index[market["bar_time_ms"] >= target_time]
        if len(candidates) == 0:
            return None
        return int(candidates[0])

    def _exit_index(
        self,
        entry_index: int,
        market: pd.DataFrame,
        assumptions: ExecutionAssumptions,
    ) -> int | None:
        entry_time = int(market.iloc[entry_index]["bar_time_ms"])
        target_exit = entry_time + int(assumptions.holding_period_ms)
        candidates = market.index[market["bar_time_ms"] >= target_exit]
        if len(candidates) > 0:
            return int(candidates[0])
        fallback_index = len(market) - 1
        if int(market.iloc[fallback_index]["bar_time_ms"]) - entry_time >= assumptions.min_holding_ms:
            return fallback_index
        return None

    def _entry_price(
        self,
        signal: dict[str, object],
        entry_row: pd.Series,
        assumptions: ExecutionAssumptions,
    ) -> float:
        if assumptions.entry_price_source == "signal_bar_close_plus_latency":
            value = signal.get("signal_bar_close")
            return float(entry_row["open"] if value is None else value)
        if assumptions.entry_price_source == "vwap_approximation":
            return float((float(entry_row["high"]) + float(entry_row["low"]) + float(entry_row["close"])) / 3.0)
        return float(entry_row["open"])

    def _empty_trades(self) -> pd.DataFrame:
        return pd.DataFrame(
            columns=[
                "trade_id",
                "signal_id",
                "symbol",
                "side",
                "entry_time_ms",
                "exit_time_ms",
                "entry_price",
                "exit_price",
                "holding_ms",
                "gross_return",
                "fee_return",
                "slippage_return",
                "spread_return",
                "funding_return",
                "net_return",
                "entry_price_source",
                "exit_reason",
            ]
        )


def _equity_curve(initial_equity: float, market_data: pd.DataFrame, trades: pd.DataFrame | None = None) -> pd.DataFrame:
    curve = pd.DataFrame(
        {
            "time_ms": market_data["bar_time_ms"].astype("int64"),
            "equity": float(initial_equity),
            "realized_net_return": 0.0,
        }
    )
    if trades is None or trades.empty:
        return curve
    equity = float(initial_equity)
    for trade in trades.to_dict("records"):
        equity *= 1.0 + float(trade["net_return"])
        mask = curve["time_ms"] >= int(trade["exit_time_ms"])
        curve.loc[mask, "equity"] = equity
        curve.loc[curve["time_ms"] == int(trade["exit_time_ms"]), "realized_net_return"] += float(trade["net_return"])
    return curve


def _optional_float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)
