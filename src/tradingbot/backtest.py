
from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import numpy as np
import pandas as pd

from tradingbot.execution_rules import confirm_pending_order_block_exit
from tradingbot.indicators import (
    adx_filter,
    annualized_sharpe,
    bps_to_multiplier,
    ema,
    feature_series,
    gaussian,
    max_consecutive_losses,
    normalize_frame,
    pct_drawdown,
    rational_quadratic,
    regime_filter,
    safe_mean,
    sma,
    volatility_filter,
)
from tradingbot.lorentz import LorentzianClassifier
from tradingbot.lorentz_lc import _half_up_round
from tradingbot.market_structure import MarketStructureEngine
from tradingbot.models import AppConfig, ExitReason, OrderBlock, PositionState, Side, TradeResult
from tradingbot.order_blocks import OrderBlockEngine
from tradingbot.risk import compute_initial_stop, compute_position_size


@dataclass
class BacktestReport:
    symbol: str
    trades: list[TradeResult]
    metrics: dict[str, float]
    equity_curve: pd.Series
    signals: pd.DataFrame
    blocks: list[OrderBlock]
    latest_decision: dict | None = None
    execution_summary: dict[str, Any] = field(default_factory=dict)


class Backtester:
    def __init__(self) -> None:
        self.lorentz = LorentzianClassifier()
        self.market_structure = MarketStructureEngine()
        self.order_blocks = OrderBlockEngine()

    def run(
        self,
        base_df: pd.DataFrame,
        execution_df: pd.DataFrame | None,
        app_config: AppConfig,
        symbol: str,
        fallback_execution_df: pd.DataFrame | None = None,
    ) -> BacktestReport:
        strategy = app_config.strategies[symbol]
        base = normalize_frame(base_df)
        execution = normalize_frame(execution_df) if execution_df is not None else None
        fallback_execution = normalize_frame(fallback_execution_df) if fallback_execution_df is not None else None
        signal_frame = self.lorentz.generate(base, strategy)

        if app_config.backtest.use_subcandle_execution and execution is not None and not strategy.use_order_block_exits:
            if app_config.backtest.slow_reference_mode:
                return self._run_subcandle_reference(base, execution, signal_frame, app_config, symbol)
            return self._run_zoom_execution(base, signal_frame, execution, fallback_execution, app_config, symbol)

        if strategy.use_order_block_exits:
            if execution is None:
                raise ValueError("execution_df is required when order block exits are enabled")
            structure_events = self.market_structure.generate(base, strategy)
            block_timeline = self.order_blocks.process(base, structure_events, strategy)
        else:
            block_timeline = SimpleNamespace(blocks=[], active_by_index={})

        equity = app_config.risk.initial_equity
        equity_points = [equity]
        equity_index = [base.iloc[0]["timestamp"]]
        trades: list[TradeResult] = []
        position: PositionState | None = None

        for idx, row in signal_frame.iterrows():
            active_blocks = block_timeline.active_by_index.get(idx, [])
            interval_start = row["timestamp"]
            interval_end = signal_frame.iloc[idx + 1]["timestamp"] if idx + 1 < len(signal_frame) else row["timestamp"]
            if execution is None:
                lower_window = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume", "symbol"])
            else:
                lower_window = execution[(execution["timestamp"] >= interval_start) & (execution["timestamp"] < interval_end)]

            if position is not None:
                lorentz_exit = (position.side == Side.LONG and bool(row["end_long_trade"])) or (
                    position.side == Side.SHORT and bool(row["end_short_trade"])
                )
                if lorentz_exit:
                    trade = self._close_trade(position, row["timestamp"], float(row["close"]), equity, strategy, ExitReason.LORENTZ, idx)
                    equity += trade.net_pnl
                    trades.append(trade)
                    equity_points.append(equity)
                    equity_index.append(row["timestamp"])
                    position = None
                elif self._risk_exit_hit(position, row):
                    trade = self._close_trade(position, row["timestamp"], position.stop_price, equity, strategy, ExitReason.RISK, idx)
                    equity += trade.net_pnl
                    trades.append(trade)
                    equity_points.append(equity)
                    equity_index.append(row["timestamp"])
                    position = None
                elif strategy.use_order_block_exits:
                    pending_block = None
                    if position.pending_order_block_id:
                        pending_block = next((block for block in active_blocks if block.block_id == position.pending_order_block_id), None)
                    if pending_block is None:
                        pending_block = self.order_blocks.find_qualifying_opposite_block(active_blocks, position.side, row, strategy)
                        if pending_block is not None:
                            position.pending_order_block_id = pending_block.block_id
                            position.pending_order_block_side = pending_block.side
                            position.pending_close_reason = ExitReason.ORDER_BLOCK.value
                            position.pending_created_at = row["timestamp"]
                    if pending_block is not None:
                        confirmed, trigger_row = confirm_pending_order_block_exit(position, pending_block, lower_window)
                        if confirmed and trigger_row is not None:
                            trade = self._close_trade(
                                position,
                                trigger_row["timestamp"],
                                float(trigger_row["close"]),
                                equity,
                                strategy,
                                ExitReason.ORDER_BLOCK,
                                idx,
                            )
                            equity += trade.net_pnl
                            trades.append(trade)
                            equity_points.append(equity)
                            equity_index.append(trigger_row["timestamp"])
                            position = None

            if position is None:
                if bool(row["start_long_trade"]) and strategy.allow_long:
                    stop = compute_initial_stop(base, idx, Side.LONG, app_config.risk)
                    qty = compute_position_size(equity, float(row["close"]), stop, app_config.risk)
                    if qty > 0:
                        position = PositionState(
                            side=Side.LONG,
                            entry_index=idx,
                            entry_timestamp=row["timestamp"],
                            entry_price=float(row["close"]),
                            quantity=qty,
                            stop_price=stop,
                            symbol=symbol,
                            open_reason="lorentz_long",
                        )
                elif bool(row["start_short_trade"]) and strategy.allow_short:
                    stop = compute_initial_stop(base, idx, Side.SHORT, app_config.risk)
                    qty = compute_position_size(equity, float(row["close"]), stop, app_config.risk)
                    if qty > 0:
                        position = PositionState(
                            side=Side.SHORT,
                            entry_index=idx,
                            entry_timestamp=row["timestamp"],
                            entry_price=float(row["close"]),
                            quantity=qty,
                            stop_price=stop,
                            symbol=symbol,
                            open_reason="lorentz_short",
                        )

        if position is not None:
            last_row = signal_frame.iloc[-1]
            trade = self._close_trade(position, last_row["timestamp"], float(last_row["close"]), equity, strategy, ExitReason.END_OF_TEST, len(signal_frame) - 1)
            equity += trade.net_pnl
            trades.append(trade)
            equity_points.append(equity)
            equity_index.append(last_row["timestamp"])

        equity_curve = pd.Series(equity_points, index=pd.to_datetime(equity_index, utc=True), dtype=float)
        metrics = self._metrics(equity_curve, trades, app_config)
        return BacktestReport(
            symbol=symbol,
            trades=trades,
            metrics=metrics,
            equity_curve=equity_curve,
            signals=signal_frame,
            blocks=block_timeline.blocks,
            latest_decision=self._decision_from_signal_row(signal_frame.iloc[-1]) if not signal_frame.empty else None,
            execution_summary={"execution_timeframe_used": "15m", "zoomed_signal_candles": 0, "fallback_to_5m_count": 0, "fallback_to_15m_close_count": 0},
        )
    def _run_zoom_execution(
        self,
        base: pd.DataFrame,
        signal_frame: pd.DataFrame,
        execution_primary: pd.DataFrame,
        execution_fallback: pd.DataFrame | None,
        app_config: AppConfig,
        symbol: str,
    ) -> BacktestReport:
        strategy = app_config.strategies[symbol]
        equity = app_config.risk.initial_equity
        equity_points = [equity]
        equity_index = [base.iloc[0]["timestamp"]]
        trades: list[TradeResult] = []
        position: PositionState | None = None
        base_delta = self._timeframe_delta(strategy.base_timeframe)
        primary_delta = self._timeframe_delta(app_config.backtest.execution_timeframe_primary)
        fallback_delta = self._timeframe_delta(app_config.backtest.execution_timeframe_fallback)
        primary_map = self._group_execution_rows(execution_primary, strategy.base_timeframe)
        fallback_map = self._group_execution_rows(execution_fallback, strategy.base_timeframe) if execution_fallback is not None else {}
        used_timeframes: set[str] = set()
        zoomed_signal_candles = 0
        fallback_to_5m_count = 0
        fallback_to_15m_close_count = 0
        latest_decision = self._decision_from_signal_row(signal_frame.iloc[-1]) if not signal_frame.empty else None

        for idx, row in signal_frame.iterrows():
            child_rows, timeframe_used, used_fallback = self._select_execution_rows(
                primary_map.get(row["timestamp"]),
                fallback_map.get(row["timestamp"]),
                base_delta,
                primary_delta,
                fallback_delta,
                app_config.backtest.execution_timeframe_primary,
                app_config.backtest.execution_timeframe_fallback,
                app_config.backtest.execution_timeframe_policy,
            )
            if child_rows is not None and not child_rows.empty:
                used_timeframes.add(timeframe_used)

            needs_zoom = bool(row["start_long_trade"] or row["start_short_trade"] or row["end_long_trade"] or row["end_short_trade"])
            step_cache: dict[int, dict[str, Any]] = {}
            closed_this_bar = False
            if needs_zoom:
                zoomed_signal_candles += 1
                if used_fallback:
                    fallback_to_5m_count += 1

            entry_child_index: int | None = None

            if position is not None:
                if child_rows is not None and not child_rows.empty:
                    for child_index, child in enumerate(child_rows.itertuples(index=False)):
                        child_series = self._child_tuple_to_series(child)
                        if self._risk_exit_hit(position, child_series):
                            trade = self._close_trade(position, child_series["timestamp"], position.stop_price, equity, strategy, ExitReason.RISK, idx)
                            equity += trade.net_pnl
                            trades.append(trade)
                            equity_points.append(equity)
                            equity_index.append(child_series["timestamp"])
                            position = None
                            closed_this_bar = True
                            break
                        if needs_zoom:
                            step = self._intrabar_step(base, signal_frame, idx, child_rows, child_index, strategy, step_cache)
                            signal = step["signal"]
                            if (position.side == Side.LONG and bool(signal["end_long_trade"])) or (position.side == Side.SHORT and bool(signal["end_short_trade"])):
                                action = "close_long" if position.side == Side.LONG else "close_short"
                                fill_price = self._directional_fill_price(child_series["open"], child_series["close"], action)
                                trade = self._close_trade(position, child_series["timestamp"], fill_price, equity, strategy, ExitReason.LORENTZ, idx)
                                equity += trade.net_pnl
                                trades.append(trade)
                                equity_points.append(equity)
                                equity_index.append(child_series["timestamp"])
                                position = None
                                closed_this_bar = True
                                break
                if position is not None and self._risk_exit_hit(position, row):
                    trade = self._close_trade(position, row["timestamp"], position.stop_price, equity, strategy, ExitReason.RISK, idx)
                    equity += trade.net_pnl
                    trades.append(trade)
                    equity_points.append(equity)
                    equity_index.append(row["timestamp"])
                    position = None
                    closed_this_bar = True
                elif position is not None and ((position.side == Side.LONG and bool(row["end_long_trade"])) or (position.side == Side.SHORT and bool(row["end_short_trade"]))):
                    trade = self._close_trade(position, row["timestamp"], float(row["close"]), equity, strategy, ExitReason.LORENTZ, idx)
                    equity += trade.net_pnl
                    trades.append(trade)
                    equity_points.append(equity)
                    equity_index.append(row["timestamp"])
                    position = None
                    closed_this_bar = True
                    fallback_to_15m_close_count += 1

            if position is None and (app_config.backtest.allow_same_bar_flip or not closed_this_bar):
                if needs_zoom and child_rows is not None and not child_rows.empty:
                    for child_index in range(len(child_rows)):
                        step = self._intrabar_step(base, signal_frame, idx, child_rows, child_index, strategy, step_cache)
                        child = step["child"]
                        signal = step["signal"]
                        intrabar_frame = step["frame"]
                        if bool(signal["start_long_trade"]) and strategy.allow_long:
                            fill_price = self._directional_fill_price(child["open"], child["close"], "open_long")
                            stop = compute_initial_stop(intrabar_frame, len(intrabar_frame) - 1, Side.LONG, app_config.risk, entry_price=fill_price)
                            qty = compute_position_size(equity, fill_price, stop, app_config.risk)
                            if qty > 0:
                                position = PositionState(
                                    side=Side.LONG,
                                    entry_index=idx,
                                    entry_timestamp=child["timestamp"],
                                    entry_price=fill_price,
                                    quantity=qty,
                                    stop_price=stop,
                                    symbol=symbol,
                                    open_reason="lorentz_long_zoom",
                                )
                                entry_child_index = child_index
                                break
                        if bool(signal["start_short_trade"]) and strategy.allow_short:
                            fill_price = self._directional_fill_price(child["open"], child["close"], "open_short")
                            stop = compute_initial_stop(intrabar_frame, len(intrabar_frame) - 1, Side.SHORT, app_config.risk, entry_price=fill_price)
                            qty = compute_position_size(equity, fill_price, stop, app_config.risk)
                            if qty > 0:
                                position = PositionState(
                                    side=Side.SHORT,
                                    entry_index=idx,
                                    entry_timestamp=child["timestamp"],
                                    entry_price=fill_price,
                                    quantity=qty,
                                    stop_price=stop,
                                    symbol=symbol,
                                    open_reason="lorentz_short_zoom",
                                )
                                entry_child_index = child_index
                                break
                if position is None:
                    if bool(row["start_long_trade"]) and strategy.allow_long:
                        fill_price = float(row["close"])
                        stop = compute_initial_stop(base, idx, Side.LONG, app_config.risk, entry_price=fill_price)
                        qty = compute_position_size(equity, fill_price, stop, app_config.risk)
                        if qty > 0:
                            position = PositionState(
                                side=Side.LONG,
                                entry_index=idx,
                                entry_timestamp=row["timestamp"],
                                entry_price=fill_price,
                                quantity=qty,
                                stop_price=stop,
                                symbol=symbol,
                                open_reason="lorentz_long_15m_fallback",
                            )
                            fallback_to_15m_close_count += 1
                    elif bool(row["start_short_trade"]) and strategy.allow_short:
                        fill_price = float(row["close"])
                        stop = compute_initial_stop(base, idx, Side.SHORT, app_config.risk, entry_price=fill_price)
                        qty = compute_position_size(equity, fill_price, stop, app_config.risk)
                        if qty > 0:
                            position = PositionState(
                                side=Side.SHORT,
                                entry_index=idx,
                                entry_timestamp=row["timestamp"],
                                entry_price=fill_price,
                                quantity=qty,
                                stop_price=stop,
                                symbol=symbol,
                                open_reason="lorentz_short_15m_fallback",
                            )
                            fallback_to_15m_close_count += 1

            if position is not None and child_rows is not None and not child_rows.empty and entry_child_index is not None:
                for child_index in range(entry_child_index + 1, len(child_rows)):
                    child = child_rows.iloc[child_index]
                    if self._risk_exit_hit(position, child):
                        trade = self._close_trade(position, child["timestamp"], position.stop_price, equity, strategy, ExitReason.RISK, idx)
                        equity += trade.net_pnl
                        trades.append(trade)
                        equity_points.append(equity)
                        equity_index.append(child["timestamp"])
                        position = None
                        break
                    if needs_zoom:
                        step = self._intrabar_step(base, signal_frame, idx, child_rows, child_index, strategy, step_cache)
                        signal = step["signal"]
                        if (position.side == Side.LONG and bool(signal["end_long_trade"])) or (position.side == Side.SHORT and bool(signal["end_short_trade"])):
                            action = "close_long" if position.side == Side.LONG else "close_short"
                            fill_price = self._directional_fill_price(child["open"], child["close"], action)
                            trade = self._close_trade(position, child["timestamp"], fill_price, equity, strategy, ExitReason.LORENTZ, idx)
                            equity += trade.net_pnl
                            trades.append(trade)
                            equity_points.append(equity)
                            equity_index.append(child["timestamp"])
                            position = None
                            break

        if position is not None:
            last_row = signal_frame.iloc[-1]
            trade = self._close_trade(position, last_row["timestamp"], float(last_row["close"]), equity, strategy, ExitReason.END_OF_TEST, len(signal_frame) - 1)
            equity += trade.net_pnl
            trades.append(trade)
            equity_points.append(equity)
            equity_index.append(last_row["timestamp"])

        equity_curve = pd.Series(equity_points, index=pd.to_datetime(equity_index, utc=True), dtype=float)
        metrics = self._metrics(equity_curve, trades, app_config)
        execution_timeframe_used = "15m"
        if len(used_timeframes) == 1:
            execution_timeframe_used = next(iter(used_timeframes))
        elif len(used_timeframes) > 1:
            execution_timeframe_used = "mixed"
        return BacktestReport(
            symbol=symbol,
            trades=trades,
            metrics=metrics,
            equity_curve=equity_curve,
            signals=signal_frame,
            blocks=[],
            latest_decision=latest_decision,
            execution_summary={
                "execution_timeframe_used": execution_timeframe_used,
                "zoomed_signal_candles": zoomed_signal_candles,
                "fallback_to_5m_count": fallback_to_5m_count,
                "fallback_to_15m_close_count": fallback_to_15m_close_count,
            },
        )
    def _run_subcandle_reference(
        self,
        base: pd.DataFrame,
        execution: pd.DataFrame,
        signal_frame: pd.DataFrame,
        app_config: AppConfig,
        symbol: str,
    ) -> BacktestReport:
        strategy = app_config.strategies[symbol]
        equity = app_config.risk.initial_equity
        equity_points = [equity]
        equity_index = [base.iloc[0]["timestamp"]]
        trades: list[TradeResult] = []
        position: PositionState | None = None
        latest_decision: dict | None = None

        for execution_idx, execution_row in execution.iterrows():
            current_ts = execution_row["timestamp"]
            current_close = float(execution_row["close"])

            if position is not None and self._risk_exit_hit(position, execution_row):
                trade = self._close_trade(position, current_ts, position.stop_price, equity, strategy, ExitReason.RISK, position.entry_index)
                equity += trade.net_pnl
                trades.append(trade)
                equity_points.append(equity)
                equity_index.append(current_ts)
                position = None

            intrabar_frame = self._build_intrabar_base_frame(base, execution.iloc[: execution_idx + 1], strategy.base_timeframe)
            intrabar_signals = self.lorentz.generate(intrabar_frame, strategy)
            latest_signal = intrabar_signals.iloc[-1]
            latest_decision = self._decision_from_signal_row(latest_signal, position.side if position is not None else None)
            base_index = len(intrabar_frame) - 1
            closed_this_candle = False

            if position is not None:
                should_close_long = position.side == Side.LONG and bool(latest_signal["end_long_trade"])
                should_close_short = position.side == Side.SHORT and bool(latest_signal["end_short_trade"])
                if should_close_long or should_close_short:
                    trade = self._close_trade(position, current_ts, current_close, equity, strategy, ExitReason.LORENTZ, base_index)
                    equity += trade.net_pnl
                    trades.append(trade)
                    equity_points.append(equity)
                    equity_index.append(current_ts)
                    position = None
                    closed_this_candle = True

            can_flip_same_candle = app_config.backtest.allow_same_bar_flip or not closed_this_candle
            if position is None and can_flip_same_candle:
                if bool(latest_signal["start_long_trade"]) and strategy.allow_long:
                    stop = compute_initial_stop(intrabar_frame, base_index, Side.LONG, app_config.risk, entry_price=current_close)
                    qty = compute_position_size(equity, current_close, stop, app_config.risk)
                    if qty > 0:
                        position = PositionState(
                            side=Side.LONG,
                            entry_index=base_index,
                            entry_timestamp=current_ts,
                            entry_price=current_close,
                            quantity=qty,
                            stop_price=stop,
                            symbol=symbol,
                            open_reason="lorentz_long_subcandle_reference",
                        )
                elif bool(latest_signal["start_short_trade"]) and strategy.allow_short:
                    stop = compute_initial_stop(intrabar_frame, base_index, Side.SHORT, app_config.risk, entry_price=current_close)
                    qty = compute_position_size(equity, current_close, stop, app_config.risk)
                    if qty > 0:
                        position = PositionState(
                            side=Side.SHORT,
                            entry_index=base_index,
                            entry_timestamp=current_ts,
                            entry_price=current_close,
                            quantity=qty,
                            stop_price=stop,
                            symbol=symbol,
                            open_reason="lorentz_short_subcandle_reference",
                        )

        if position is not None:
            last_row = execution.iloc[-1]
            trade = self._close_trade(position, last_row["timestamp"], float(last_row["close"]), equity, strategy, ExitReason.END_OF_TEST, len(base) - 1)
            equity += trade.net_pnl
            trades.append(trade)
            equity_points.append(equity)
            equity_index.append(last_row["timestamp"])

        equity_curve = pd.Series(equity_points, index=pd.to_datetime(equity_index, utc=True), dtype=float)
        metrics = self._metrics(equity_curve, trades, app_config)
        return BacktestReport(
            symbol=symbol,
            trades=trades,
            metrics=metrics,
            equity_curve=equity_curve,
            signals=signal_frame,
            blocks=[],
            latest_decision=latest_decision,
            execution_summary={
                "execution_timeframe_used": app_config.backtest.execution_timeframe_primary,
                "zoomed_signal_candles": len(execution),
                "fallback_to_5m_count": 0,
                "fallback_to_15m_close_count": 0,
                "reference_mode": True,
            },
        )

    def _intrabar_step(
        self,
        base: pd.DataFrame,
        signal_frame: pd.DataFrame,
        base_index: int,
        child_rows: pd.DataFrame,
        child_index: int,
        strategy,
        step_cache: dict[int, dict[str, Any]],
    ) -> dict[str, Any]:
        if child_index in step_cache:
            return step_cache[child_index]
        history = base.iloc[:base_index][["timestamp", "open", "high", "low", "close", "volume", "symbol"]].copy()
        history_signals = signal_frame.iloc[:base_index].reset_index(drop=True)
        bucket_start = base.iloc[base_index]["timestamp"]
        open_price = float(child_rows.iloc[0]["open"])
        feature_names = [f"f{i + 1}" for i in range(strategy.feature_count)]
        current_children = child_rows.iloc[: child_index + 1]
        child = current_children.iloc[-1]
        partial_row = pd.DataFrame(
            [
                {
                    "timestamp": bucket_start,
                    "open": open_price,
                    "high": float(current_children["high"].max()),
                    "low": float(current_children["low"].min()),
                    "close": float(child["close"]),
                    "volume": float(current_children["volume"].sum()),
                    "symbol": str(child["symbol"]),
                }
            ]
        )
        intrabar_frame = pd.concat([history, partial_row], ignore_index=True)
        latest_signal = self._evaluate_partial_signal(intrabar_frame, history_signals, strategy, feature_names)
        step = {"signal": latest_signal, "frame": intrabar_frame, "child": child}
        step_cache[child_index] = step
        return step

    def _evaluate_partial_signal(
        self,
        intrabar_frame: pd.DataFrame,
        history_signals: pd.DataFrame,
        strategy,
        feature_names: list[str],
    ) -> pd.Series:
        # Keep intrabar zoom decisions on the same LC implementation as the main
        # chart/backtest path. The older hand-rolled evaluator below is left
        # unreachable for now to avoid silently drifting on ANN/indexing modes.
        _ = (history_signals, feature_names)
        return self.lorentz.generate(intrabar_frame, strategy).iloc[-1]

        current_index = len(intrabar_frame) - 1
        frame = intrabar_frame.reset_index(drop=True)
        current_features = []
        for feature_idx, (name, param_a, param_b) in enumerate(strategy.feature_definitions[: strategy.feature_count]):
            feature_value = float(feature_series(frame, name, param_a, param_b).iloc[-1])
            current_features.append(feature_value)
        current_features_np = pd.Series(current_features, index=feature_names[: len(current_features)], dtype=float).fillna(0.0).to_numpy(dtype=float)

        historical_features = history_signals[feature_names].ffill().fillna(0.0).to_numpy(dtype=float) if not history_signals.empty else None
        source = frame[strategy.source].astype(float)
        previous_signal = int(history_signals.iloc[-1]["signal"]) if not history_signals.empty else 0
        previous_bars_held = int(history_signals.iloc[-1]["bars_held"]) if not history_signals.empty else 0
        prediction_state = (
            list(history_signals.iloc[-1]["prediction_state"])
            if (not history_signals.empty and "prediction_state" in history_signals.columns)
            else []
        )
        distance_state = (
            list(history_signals.iloc[-1]["distance_state"])
            if (not history_signals.empty and "distance_state" in history_signals.columns)
            else []
        )
        neighbor_index_state = (
            list(history_signals.iloc[-1]["neighbor_index_state"])
            if (not history_signals.empty and "neighbor_index_state" in history_signals.columns)
            else []
        )
        current_prediction = float(history_signals.iloc[-1]["prediction"]) if not history_signals.empty else 0.0

        max_bars_back_index = max(len(frame) - 1 - strategy.max_bars_back, 0) if len(frame) - 1 >= strategy.max_bars_back else 0
        accepted_this_bar = 0
        if current_index >= max_bars_back_index:
            current_source = float(source.iloc[-1])
            label_source = float(source.iloc[-5]) if len(source) > 4 else current_source
            current_label = -1 if label_source < current_source else 1 if label_source > current_source else 0
            if historical_features is not None and len(historical_features) > 0:
                candidate_labels = (
                    -(frame[strategy.source].shift(4).iloc[:current_index] < frame[strategy.source].iloc[:current_index]).astype(int)
                    + (frame[strategy.source].shift(4).iloc[:current_index] > frame[strategy.source].iloc[:current_index]).astype(int)
                ).fillna(0).astype(int).to_numpy()
            else:
                candidate_labels = pd.Series(dtype=int).to_numpy()
            all_features = [row for row in (historical_features if historical_features is not None else [])]
            all_features.append(current_features_np)
            all_labels = list(candidate_labels)
            all_labels.append(current_label)
            last_distance = -1.0
            size = min(strategy.max_bars_back - 1, current_index)
            size_loop = min(strategy.max_bars_back - 1, size)
            if getattr(strategy, "lc_mode", "static") == "rolling_research":
                historical_indices = list(range(max(0, current_index - size_loop), current_index + 1))
            else:
                historical_indices = list(range(0, size_loop + 1))
            for relative_idx, historical_idx in enumerate(historical_indices):
                feature_row = all_features[historical_idx]
                distance = float(np.log1p(np.abs(current_features_np - feature_row)).sum())
                modulo_index = relative_idx if getattr(strategy, "lc_mode", "static") == "rolling_research" else historical_idx
                if distance >= last_distance and modulo_index % 4:
                    last_distance = distance
                    distance_state.append(last_distance)
                    prediction_state.append(_half_up_round(float(all_labels[historical_idx])))
                    neighbor_index_state.append(historical_idx)
                    accepted_this_bar += 1
                    if len(prediction_state) > strategy.neighbors_count:
                        pivot = _half_up_round(strategy.neighbors_count * 3 / 4)
                        pivot = min(max(pivot, 0), len(distance_state) - 1)
                        last_distance = distance_state[pivot]
                        distance_state.pop(0)
                        prediction_state.pop(0)
                        neighbor_index_state.pop(0)
            current_prediction = float(sum(prediction_state))

        volatility_ok = bool(volatility_filter(frame, strategy.use_volatility_filter).iloc[-1])
        regime_ok = bool(regime_filter(frame, strategy.regime_threshold, strategy.use_regime_filter).iloc[-1])
        adx_ok = bool(adx_filter(frame, strategy.adx_threshold, strategy.use_adx_filter).iloc[-1])
        filter_all = volatility_ok and regime_ok and adx_ok
        ema_uptrend = True if not strategy.use_ema_filter else bool((frame["close"] > ema(frame["close"], strategy.ema_period)).iloc[-1])
        ema_downtrend = True if not strategy.use_ema_filter else bool((frame["close"] < ema(frame["close"], strategy.ema_period)).iloc[-1])
        sma_uptrend = True if not strategy.use_sma_filter else bool((frame["close"] > sma(frame["close"], strategy.sma_period)).iloc[-1])
        sma_downtrend = True if not strategy.use_sma_filter else bool((frame["close"] < sma(frame["close"], strategy.sma_period)).iloc[-1])

        current_signal = previous_signal
        if current_prediction > 0 and filter_all:
            current_signal = 1
        elif current_prediction < 0 and filter_all:
            current_signal = -1

        signal_change = current_signal != previous_signal
        bars_held = 1 if current_index == 0 else (0 if signal_change else previous_bars_held + 1)
        if not history_signals.empty and "signal_change" in history_signals.columns:
            prior_changes = history_signals["signal_change"].tail(3).fillna(False).tolist()
        elif len(history_signals) > 1:
            prior_changes = (
                history_signals["signal"].astype(int).diff().fillna(0).ne(0).tail(3).tolist()
            )
        else:
            prior_changes = []
        is_early_signal_flip = signal_change and any(bool(value) for value in prior_changes)
        is_buy_signal = current_signal == 1 and ema_uptrend and sma_uptrend
        is_sell_signal = current_signal == -1 and ema_downtrend and sma_downtrend
        is_new_buy = is_buy_signal and signal_change
        is_new_sell = is_sell_signal and signal_change

        lookback = strategy.kernel_regression_level + 3
        kernel_source = source.tail(lookback).reset_index(drop=True)
        current_yhat1 = float(rational_quadratic(kernel_source, strategy.kernel_lookback, strategy.kernel_relative_weight, strategy.kernel_regression_level).iloc[-1])
        current_yhat2 = float(gaussian(kernel_source, max(strategy.kernel_lookback - strategy.kernel_lag, 1), strategy.kernel_regression_level).iloc[-1])
        previous_yhat1 = float(history_signals.iloc[-1]["yhat1"]) if (not history_signals.empty and "yhat1" in history_signals.columns) else current_yhat1
        previous_yhat2 = float(history_signals.iloc[-1]["yhat2"]) if (not history_signals.empty and "yhat2" in history_signals.columns) else current_yhat2
        previous_previous_yhat1 = float(history_signals.iloc[-2]["yhat1"]) if (len(history_signals) > 1 and "yhat1" in history_signals.columns) else previous_yhat1
        was_bearish_rate = previous_previous_yhat1 > previous_yhat1
        was_bullish_rate = previous_previous_yhat1 < previous_yhat1
        is_bearish_rate = previous_yhat1 > current_yhat1
        is_bullish_rate = previous_yhat1 < current_yhat1
        is_bearish_change = is_bearish_rate and was_bullish_rate
        is_bullish_change = is_bullish_rate and was_bearish_rate
        bullish_cross_alert = (current_yhat2 > current_yhat1) and (previous_yhat2 <= previous_yhat1)
        bearish_cross_alert = (current_yhat2 < current_yhat1) and (previous_yhat2 >= previous_yhat1)
        bullish_smooth = current_yhat2 >= current_yhat1
        bearish_smooth = current_yhat2 <= current_yhat1
        alert_bullish = bullish_cross_alert if strategy.use_kernel_smoothing else is_bullish_change
        alert_bearish = bearish_cross_alert if strategy.use_kernel_smoothing else is_bearish_change
        is_bullish = (bullish_smooth if strategy.use_kernel_smoothing else is_bullish_rate) if strategy.use_kernel_filter else True
        is_bearish = (bearish_smooth if strategy.use_kernel_smoothing else is_bearish_rate) if strategy.use_kernel_filter else True

        start_long_trade = bool(is_new_buy and is_bullish and ema_uptrend and sma_uptrend and strategy.allow_long)
        start_short_trade = bool(is_new_sell and is_bearish and ema_downtrend and sma_downtrend and strategy.allow_short)

        previous_valid_long_exit = bool(history_signals.iloc[-1]["is_valid_long_exit"]) if (not history_signals.empty and "is_valid_long_exit" in history_signals.columns) else False
        previous_valid_short_exit = bool(history_signals.iloc[-1]["is_valid_short_exit"]) if (not history_signals.empty and "is_valid_short_exit" in history_signals.columns) else False
        valid_long_exit = previous_valid_long_exit or bool(alert_bearish)
        valid_short_exit = previous_valid_short_exit or bool(alert_bullish)
        end_long_dynamic = bool(is_bearish_change and previous_valid_long_exit)
        end_short_dynamic = bool(is_bullish_change and previous_valid_short_exit)

        is_held_four = bars_held == 4
        is_held_less_than_four = 1 <= bars_held <= 3
        last_signal_index = len(history_signals) - 4
        is_last_signal_buy = False
        is_last_signal_sell = False
        shifted_start_long = False
        shifted_start_short = False
        if last_signal_index >= 0:
            shifted_row = history_signals.iloc[last_signal_index]
            ema_up = bool(shifted_row["ema_uptrend"]) if "ema_uptrend" in history_signals.columns else True
            sma_up = bool(shifted_row["sma_uptrend"]) if "sma_uptrend" in history_signals.columns else True
            ema_down = bool(shifted_row["ema_downtrend"]) if "ema_downtrend" in history_signals.columns else True
            sma_down = bool(shifted_row["sma_downtrend"]) if "sma_downtrend" in history_signals.columns else True
            is_last_signal_buy = bool(shifted_row["signal"] == 1 and ema_up and sma_up)
            is_last_signal_sell = bool(shifted_row["signal"] == -1 and ema_down and sma_down)
            shifted_start_long = bool(shifted_row["start_long_trade"])
            shifted_start_short = bool(shifted_row["start_short_trade"])

        end_long_strict = bool(((is_held_four and is_last_signal_buy) or (is_held_less_than_four and is_new_sell and is_last_signal_buy)) and shifted_start_long)
        end_short_strict = bool(((is_held_four and is_last_signal_sell) or (is_held_less_than_four and is_new_buy and is_last_signal_sell)) and shifted_start_short)
        dynamic_valid = (not strategy.use_ema_filter) and (not strategy.use_sma_filter) and (not strategy.use_kernel_smoothing)
        end_long_trade = end_long_dynamic if strategy.use_dynamic_exits and dynamic_valid else end_long_strict
        end_short_trade = end_short_dynamic if strategy.use_dynamic_exits and dynamic_valid else end_short_strict

        row = {
            "timestamp": frame.iloc[-1]["timestamp"],
            "symbol": frame.iloc[-1]["symbol"],
            "open": float(frame.iloc[-1]["open"]),
            "high": float(frame.iloc[-1]["high"]),
            "low": float(frame.iloc[-1]["low"]),
            "close": float(frame.iloc[-1]["close"]),
            "volume": float(frame.iloc[-1]["volume"]),
            "prediction": current_prediction,
            "signal": current_signal,
            "bars_held": bars_held,
            "signal_change": signal_change,
            "is_early_signal_flip": is_early_signal_flip,
            "yhat1": current_yhat1,
            "yhat2": current_yhat2,
            "kernel_estimate": current_yhat1,
            "alert_bullish": alert_bullish,
            "alert_bearish": alert_bearish,
            "is_bullish": is_bullish,
            "is_bearish": is_bearish,
            "volatility_filter": volatility_ok,
            "regime_filter": regime_ok,
            "adx_filter": adx_ok,
            "filter_all": filter_all,
            "ema_uptrend": ema_uptrend,
            "ema_downtrend": ema_downtrend,
            "sma_uptrend": sma_uptrend,
            "sma_downtrend": sma_downtrend,
            "is_valid_long_exit": valid_long_exit,
            "is_valid_short_exit": valid_short_exit,
            "prediction_state": tuple(prediction_state),
            "distance_state": tuple(distance_state),
            "neighbor_index_state": tuple(neighbor_index_state),
            "neighbor_label_state": tuple(prediction_state),
            "neighbor_index_last": neighbor_index_state[-1] if neighbor_index_state else np.nan,
            "neighbor_label_last": prediction_state[-1] if prediction_state else np.nan,
            "distance_last": distance_state[-1] if distance_state else np.nan,
            "y_train": current_label,
            "ann_window_start": max(0, current_index - min(strategy.max_bars_back - 1, current_index)) if getattr(strategy, "lc_mode", "static") == "rolling_research" else 0,
            "ann_window_end": current_index if getattr(strategy, "lc_mode", "static") == "rolling_research" else min(strategy.max_bars_back - 1, current_index),
            "ann_considered_count": min(strategy.max_bars_back, current_index + 1),
            "ann_accepted_count": accepted_this_bar,
            "lc_mode": getattr(strategy, "lc_mode", "static"),
            "start_long_trade": start_long_trade,
            "start_short_trade": start_short_trade,
            "end_long_trade": bool(end_long_trade),
            "end_short_trade": bool(end_short_trade),
            "atr_stop": float((frame.iloc[-1]["open"] + frame.iloc[-1]["high"] + frame.iloc[-1]["low"] + frame.iloc[-1]["close"]) / 4.0),
        }
        for feature_name, feature_value in zip(feature_names, current_features):
            row[feature_name] = feature_value
        return pd.Series(row)

    def _select_execution_rows(
        self,
        primary_rows: pd.DataFrame | None,
        fallback_rows: pd.DataFrame | None,
        base_delta: pd.Timedelta,
        primary_delta: pd.Timedelta,
        fallback_delta: pd.Timedelta,
        primary_name: str,
        fallback_name: str,
        policy: str,
    ) -> tuple[pd.DataFrame | None, str, bool]:
        primary = primary_rows if primary_rows is not None else pd.DataFrame()
        fallback = fallback_rows if fallback_rows is not None else pd.DataFrame()
        expected_primary = max(int(base_delta / primary_delta), 1)
        expected_fallback = max(int(base_delta / fallback_delta), 1)
        if not primary.empty and len(primary) >= expected_primary:
            return primary.reset_index(drop=True), primary_name, False
        if not fallback.empty and len(fallback) >= expected_fallback:
            return fallback.reset_index(drop=True), fallback_name, True
        if policy == "best_effort":
            if not primary.empty:
                return primary.reset_index(drop=True), primary_name, False
            if not fallback.empty:
                return fallback.reset_index(drop=True), fallback_name, True
        return None, "15m", False

    def _group_execution_rows(self, execution_df: pd.DataFrame | None, base_timeframe: str) -> dict[pd.Timestamp, pd.DataFrame]:
        if execution_df is None or execution_df.empty:
            return {}
        frame = execution_df.copy()
        frame["parent_timestamp"] = frame["timestamp"].dt.floor(self._pandas_timeframe(base_timeframe))
        grouped: dict[pd.Timestamp, pd.DataFrame] = {}
        for parent_timestamp, child_frame in frame.groupby("parent_timestamp", sort=True):
            grouped[parent_timestamp] = child_frame[["timestamp", "open", "high", "low", "close", "volume", "symbol"]].reset_index(drop=True)
        return grouped

    def _build_intrabar_base_frame(self, base: pd.DataFrame, execution_slice: pd.DataFrame, base_timeframe: str) -> pd.DataFrame:
        current_ts = execution_slice.iloc[-1]["timestamp"]
        bucket_start = current_ts.floor(self._pandas_timeframe(base_timeframe))
        closed_base = base[base["timestamp"] < bucket_start].copy()
        current_bucket = execution_slice[execution_slice["timestamp"] >= bucket_start].copy()
        partial_row = pd.DataFrame(
            [
                {
                    "timestamp": bucket_start,
                    "open": float(current_bucket.iloc[0]["open"]),
                    "high": float(current_bucket["high"].max()),
                    "low": float(current_bucket["low"].min()),
                    "close": float(current_bucket.iloc[-1]["close"]),
                    "volume": float(current_bucket["volume"].sum()),
                    "symbol": str(current_bucket.iloc[-1]["symbol"]),
                }
            ]
        )
        return pd.concat([closed_base[["timestamp", "open", "high", "low", "close", "volume", "symbol"]], partial_row], ignore_index=True)
    def _timeframe_delta(self, timeframe: str) -> pd.Timedelta:
        mapping = {
            "1m": pd.Timedelta(minutes=1),
            "3m": pd.Timedelta(minutes=3),
            "5m": pd.Timedelta(minutes=5),
            "15m": pd.Timedelta(minutes=15),
            "30m": pd.Timedelta(minutes=30),
            "1h": pd.Timedelta(hours=1),
            "2h": pd.Timedelta(hours=2),
            "4h": pd.Timedelta(hours=4),
            "8h": pd.Timedelta(hours=8),
            "12h": pd.Timedelta(hours=12),
            "1d": pd.Timedelta(days=1),
        }
        if timeframe not in mapping:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        return mapping[timeframe]

    def _pandas_timeframe(self, timeframe: str) -> str:
        lowered = timeframe.lower().strip()
        if lowered.endswith("m"):
            return f"{lowered[:-1]}min"
        return lowered

    def _directional_fill_price(self, candle_open: float, candle_close: float, action: str) -> float:
        if action == "open_long":
            return max(float(candle_open), float(candle_close))
        if action == "open_short":
            return min(float(candle_open), float(candle_close))
        if action == "close_long":
            return min(float(candle_open), float(candle_close))
        if action == "close_short":
            return max(float(candle_open), float(candle_close))
        return float(candle_close)

    def _child_tuple_to_series(self, child_row: Any) -> pd.Series:
        return pd.Series(
            {
                "timestamp": child_row.timestamp,
                "open": float(child_row.open),
                "high": float(child_row.high),
                "low": float(child_row.low),
                "close": float(child_row.close),
                "volume": float(child_row.volume),
                "symbol": child_row.symbol,
            }
        )

    def _decision_from_signal_row(self, row: pd.Series, position_side: Side | None = None) -> dict:
        decision = {"timestamp": str(row["timestamp"]), "action": "hold"}
        if bool(row["start_long_trade"]):
            decision["action"] = "open_long"
        elif bool(row["start_short_trade"]):
            decision["action"] = "open_short"
        elif bool(row["end_long_trade"]) or bool(row["end_short_trade"]):
            decision["action"] = "close_position"
            if position_side is not None:
                decision["position_side"] = position_side.value
        return decision

    def _risk_exit_hit(self, position: PositionState, row: pd.Series) -> bool:
        if position.side == Side.LONG:
            return float(row["low"]) <= position.stop_price
        return float(row["high"]) >= position.stop_price

    def _close_trade(
        self,
        position: PositionState,
        exit_timestamp,
        exit_price: float,
        equity: float,
        strategy,
        exit_reason: ExitReason,
        current_index: int,
    ) -> TradeResult:
        side_mult = 1.0 if position.side == Side.LONG else -1.0
        gross = (exit_price - position.entry_price) * position.quantity * side_mult
        notional = position.entry_price * position.quantity
        fees = notional * (bps_to_multiplier(strategy.fee_bps) + bps_to_multiplier(strategy.slippage_bps))
        bars_held = max(current_index - position.entry_index, 1)
        funding = notional * strategy.funding_rate_per_bar * bars_held
        net = gross - fees - funding
        return_pct = (net / equity) * 100.0 if equity else 0.0
        return TradeResult(
            symbol=position.symbol,
            side=position.side,
            entry_timestamp=position.entry_timestamp,
            exit_timestamp=exit_timestamp,
            entry_price=position.entry_price,
            exit_price=exit_price,
            quantity=position.quantity,
            gross_pnl=gross,
            net_pnl=net,
            return_pct=return_pct,
            exit_reason=exit_reason,
            bars_held=bars_held,
        )

    def _metrics(self, equity_curve: pd.Series, trades: list[TradeResult], app_config: AppConfig) -> dict[str, float]:
        pnls = [trade.net_pnl for trade in trades]
        wins = [trade for trade in trades if trade.net_pnl > 0]
        returns = equity_curve.pct_change().dropna()
        return {
            "initial_equity": app_config.risk.initial_equity,
            "final_equity": float(equity_curve.iloc[-1]) if not equity_curve.empty else app_config.risk.initial_equity,
            "net_profit": float(sum(pnls)),
            "gross_profit": float(sum(trade.gross_pnl for trade in trades)),
            "trade_count": float(len(trades)),
            "win_rate": (len(wins) / len(trades)) * 100.0 if trades else 0.0,
            "avg_trade_pnl": safe_mean(pnls),
            "max_drawdown_pct": abs(pct_drawdown(equity_curve)),
            "max_consecutive_losses": float(max_consecutive_losses(pnls)),
            "expectancy": safe_mean([trade.return_pct for trade in trades]),
            "sharpe_like": annualized_sharpe(returns),
        }
