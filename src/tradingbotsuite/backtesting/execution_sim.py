from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import pandas as pd

from tradingbotsuite.backtesting.costs import CostModel
from tradingbotsuite.backtesting.exits import (
    ExitPolicyResult,
    fixed_holding_window_exit,
    primary_bar_research_exit,
    triple_barrier_exit_from_lower_timeframe,
)

EntryPriceSource = Literal[
    "next_bar_open",
    "signal_bar_close_plus_latency",
    "vwap_approximation",
    "lower_timeframe_execution_path",
]
ExitPriceSource = Literal["primary_close", "lower_timeframe_ohlc_sequence"]


@dataclass(frozen=True, slots=True)
class ExecutionAssumptions:
    interval_ms: int
    entry_latency_ms: int
    entry_price_source: EntryPriceSource
    min_holding_ms: int
    max_holding_ms: int
    holding_period_ms: int
    allow_same_bar_exit: bool = False
    exit_policy_id: str = "fixed_holding_window"
    target_return: float | None = None
    stop_return: float | None = None
    exit_price_source: ExitPriceSource = "primary_close"
    exit_policy_params: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, object]:
        return {
            "interval_ms": int(self.interval_ms),
            "entry_latency_ms": int(self.entry_latency_ms),
            "entry_price_source": self.entry_price_source,
            "min_holding_ms": int(self.min_holding_ms),
            "max_holding_ms": int(self.max_holding_ms),
            "holding_period_ms": int(self.holding_period_ms),
            "allow_same_bar_exit": bool(self.allow_same_bar_exit),
            "exit_policy_id": self.exit_policy_id,
            "target_return": self.target_return,
            "stop_return": self.stop_return,
            "exit_price_source": self.exit_price_source,
            "exit_policy_params": dict(self.exit_policy_params),
        }


@dataclass(frozen=True, slots=True)
class ExitResult:
    primary_exit_index: int
    exit_reason: str
    target_exit_time_ms: int
    target_holding_ms: int
    realized_holding_ms: int
    used_end_of_data_fallback: bool
    policy_result: ExitPolicyResult
    sequence_proof: str = "primary_bar_time"

    @property
    def exit_index(self) -> int:
        return self.primary_exit_index


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
            entry_price = self._entry_price(signal, entry_row, assumptions)
            side = str(signal["side"]).lower()
            exit_result = self._exit_result(
                entry_index,
                market,
                assumptions,
                entry_price=entry_price,
                side=side,
                symbol=str(signal.get("symbol", "")),
                lower_timeframe_market_data=lower_timeframe_market_data,
            )
            if exit_result is None:
                continue
            exit_index = exit_result.exit_index
            if (
                exit_index <= entry_index
                and not assumptions.allow_same_bar_exit
                and not (
                    exit_result.sequence_proof == "lower_timeframe_ohlc"
                    and int(exit_result.policy_result.exit_time_ms) > entry_time
                )
            ):
                raise ValueError("same-bar entry/exit is forbidden without lower-timeframe sequence proof")
            exit_price = float(exit_result.policy_result.exit_price)
            holding_ms = int(exit_result.policy_result.exit_time_ms) - int(entry_row["bar_time_ms"])
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
                    "exit_time_ms": int(exit_result.policy_result.exit_time_ms),
                    "entry_bar_index": int(entry_index),
                    "exit_bar_index": int(exit_index),
                    "entry_price": float(entry_price),
                    "exit_price": float(exit_price),
                    "holding_ms": int(holding_ms),
                    "exit_target_time_ms": int(exit_result.target_exit_time_ms),
                    "exit_target_holding_ms": int(exit_result.target_holding_ms),
                    "exit_used_fallback": bool(exit_result.used_end_of_data_fallback),
                    "exit_policy": exit_result.policy_result.exit_policy_id,
                    "barrier_hit_type": exit_result.policy_result.barrier_hit_type,
                    "max_adverse_excursion": exit_result.policy_result.max_adverse_excursion,
                    "max_favorable_excursion": exit_result.policy_result.max_favorable_excursion,
                    "exit_approximate": exit_result.policy_result.approximate,
                    "exit_sequence_proof": exit_result.sequence_proof,
                    "exit_price_source": assumptions.exit_price_source,
                    "gross_return": cost.gross_return,
                    "fee_return": cost.fee_return,
                    "slippage_return": cost.slippage_return,
                    "spread_return": cost.spread_return,
                    "funding_return": cost.funding_return,
                    "net_return": cost.net_return,
                    "entry_price_source": assumptions.entry_price_source,
                    "exit_reason": exit_result.policy_result.exit_reason,
                }
            )
            next_available_entry_time = int(exit_result.policy_result.exit_time_ms)

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
        if assumptions.exit_price_source == "lower_timeframe_ohlc_sequence" and (
            lower_timeframe_market_data is None or lower_timeframe_market_data.empty
        ):
            raise ValueError("lower_timeframe_ohlc_sequence requires lower_timeframe_market_data")
        if _is_triple_barrier(assumptions.exit_policy_id):
            if assumptions.target_return is None or assumptions.stop_return is None:
                raise ValueError("triple-barrier exits require target_return and stop_return")
            if assumptions.target_return <= 0.0 or assumptions.stop_return <= 0.0:
                raise ValueError("target_return and stop_return must be positive for triple-barrier exits")
        elif _is_primary_bar_research_exit_policy(assumptions.exit_policy_id):
            if assumptions.exit_price_source != "primary_close":
                raise ValueError("primary-bar research exits require primary_close exit_price_source")
        elif not _is_fixed_holding_policy(assumptions.exit_policy_id):
            raise ValueError(f"unsupported exit_policy_id: {assumptions.exit_policy_id}")

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
        result = self._exit_result(
            entry_index,
            market,
            assumptions,
            entry_price=float(market.iloc[entry_index]["open"]),
            side="long",
            symbol=None,
            lower_timeframe_market_data=None,
        )
        return None if result is None else result.exit_index

    def _exit_result(
        self,
        entry_index: int,
        market: pd.DataFrame,
        assumptions: ExecutionAssumptions,
        *,
        entry_price: float,
        side: str,
        symbol: str | None,
        lower_timeframe_market_data: pd.DataFrame | None,
    ) -> ExitResult | None:
        entry_time = int(market.iloc[entry_index]["bar_time_ms"])
        target_exit = entry_time + int(assumptions.holding_period_ms)
        candidates = market.index[market["bar_time_ms"] >= target_exit]
        if len(candidates) > 0:
            exit_index = int(candidates[0])
            exit_time = int(market.iloc[exit_index]["bar_time_ms"])
            policy_result = self._policy_result(
                entry_index=entry_index,
                exit_index=exit_index,
                target_exit_time_ms=target_exit,
                market=market,
                assumptions=assumptions,
                entry_price=entry_price,
                side=side,
                symbol=symbol,
                lower_timeframe_market_data=lower_timeframe_market_data,
                exit_reason="holding_window",
            )
            primary_exit_index = _primary_index_for_time(market, policy_result.exit_time_ms)
            return ExitResult(
                primary_exit_index=primary_exit_index,
                exit_reason=policy_result.exit_reason,
                target_exit_time_ms=target_exit,
                target_holding_ms=int(assumptions.holding_period_ms),
                realized_holding_ms=int(policy_result.exit_time_ms) - entry_time,
                used_end_of_data_fallback=False,
                policy_result=policy_result,
                sequence_proof=_sequence_proof(assumptions, policy_result),
            )
        fallback_index = len(market) - 1
        fallback_time = int(market.iloc[fallback_index]["bar_time_ms"])
        if fallback_time - entry_time >= assumptions.min_holding_ms:
            policy_result = self._policy_result(
                entry_index=entry_index,
                exit_index=fallback_index,
                target_exit_time_ms=target_exit,
                market=market,
                assumptions=assumptions,
                entry_price=entry_price,
                side=side,
                symbol=symbol,
                lower_timeframe_market_data=lower_timeframe_market_data,
                exit_reason="end_of_data_min_holding",
            )
            primary_exit_index = _primary_index_for_time(market, policy_result.exit_time_ms)
            return ExitResult(
                primary_exit_index=primary_exit_index,
                exit_reason=policy_result.exit_reason,
                target_exit_time_ms=target_exit,
                target_holding_ms=int(assumptions.holding_period_ms),
                realized_holding_ms=int(policy_result.exit_time_ms) - entry_time,
                used_end_of_data_fallback=True,
                policy_result=policy_result,
                sequence_proof=_sequence_proof(assumptions, policy_result),
            )
        return None

    def _policy_result(
        self,
        *,
        entry_index: int,
        exit_index: int,
        target_exit_time_ms: int,
        market: pd.DataFrame,
        assumptions: ExecutionAssumptions,
        entry_price: float,
        side: str,
        symbol: str | None,
        lower_timeframe_market_data: pd.DataFrame | None,
        exit_reason: str,
    ) -> ExitPolicyResult:
        entry_time = int(market.iloc[entry_index]["bar_time_ms"])
        time_exit = int(market.iloc[exit_index]["bar_time_ms"])
        time_exit_price = float(market.iloc[exit_index]["close"])
        if _is_triple_barrier(assumptions.exit_policy_id):
            if assumptions.exit_price_source != "lower_timeframe_ohlc_sequence":
                raise ValueError("triple-barrier exits require lower_timeframe_ohlc_sequence exit_price_source")
            if lower_timeframe_market_data is None or lower_timeframe_market_data.empty:
                raise ValueError("triple-barrier exits require lower_timeframe_market_data")
            return triple_barrier_exit_from_lower_timeframe(
                entry_time_ms=entry_time,
                entry_price=entry_price,
                side=side,
                time_exit_ms=time_exit,
                time_exit_price=time_exit_price,
                target_return=float(assumptions.target_return),
                stop_return=float(assumptions.stop_return),
                lower_timeframe_market_data=lower_timeframe_market_data,
                costs_applied=True,
                exit_policy_id=assumptions.exit_policy_id,
                symbol=symbol,
            )
        if _is_primary_bar_research_exit_policy(assumptions.exit_policy_id):
            path = market.iloc[min(entry_index, exit_index) : max(entry_index, exit_index) + 1]
            return primary_bar_research_exit(
                entry_time_ms=entry_time,
                time_exit_ms=time_exit,
                time_exit_price=time_exit_price,
                entry_price=entry_price,
                side=side,
                primary_path=path,
                costs_applied=True,
                exit_policy_id=assumptions.exit_policy_id,
                target_return=assumptions.target_return,
                stop_return=assumptions.stop_return,
                policy_params=assumptions.exit_policy_params,
                exit_reason=exit_reason,
            )
        if not _is_fixed_holding_policy(assumptions.exit_policy_id):
            raise ValueError(f"unsupported exit_policy_id: {assumptions.exit_policy_id}")
        path = market.iloc[min(entry_index, exit_index) : max(entry_index, exit_index) + 1]
        return fixed_holding_window_exit(
            entry_time_ms=entry_time,
            exit_time_ms=time_exit,
            entry_price=entry_price,
            exit_price=time_exit_price,
            side=side,
            path_high=float(path["high"].max()),
            path_low=float(path["low"].min()),
            costs_applied=True,
            exit_reason=exit_reason,
        )

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
                "entry_bar_index",
                "exit_bar_index",
                "entry_price",
                "exit_price",
                "holding_ms",
                "exit_target_time_ms",
                "exit_target_holding_ms",
                "exit_used_fallback",
                "exit_policy",
                "barrier_hit_type",
                "max_adverse_excursion",
                "max_favorable_excursion",
                "exit_approximate",
                "exit_sequence_proof",
                "exit_price_source",
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


def _is_triple_barrier(exit_policy_id: str) -> bool:
    return str(exit_policy_id).lower() in {"triple_barrier", "triple_barrier_atr"}


def _is_primary_bar_research_exit_policy(exit_policy_id: str) -> bool:
    return str(exit_policy_id).lower() in {
        "volatility_scaled_barrier",
        "regime_flip_exit",
        "funding_adverse_exit",
        "alpha_decay_exit",
        "adverse_selection_exit",
        "trailing_atr_after_profit",
        "max_mae_stop",
    }


def _is_fixed_holding_policy(exit_policy_id: str) -> bool:
    value = str(exit_policy_id).lower()
    return value == "fixed_holding_window" or value.endswith("_time_exit")


def _sequence_proof(assumptions: ExecutionAssumptions, policy_result: ExitPolicyResult) -> str:
    if assumptions.exit_price_source == "lower_timeframe_ohlc_sequence" and policy_result.barrier_hit_type != "time":
        return "lower_timeframe_ohlc"
    return "primary_bar_time"


def _primary_index_for_time(market: pd.DataFrame, time_ms: int) -> int:
    candidates = market.index[market["bar_time_ms"] <= int(time_ms)]
    if len(candidates) == 0:
        return 0
    return int(candidates[-1])
