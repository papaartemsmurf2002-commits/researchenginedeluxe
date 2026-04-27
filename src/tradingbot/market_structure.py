from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from tradingbot.indicators import normalize_frame
from tradingbot.models import EventKind, MarketStructureEvent, Side, StrategyConfig, StructureScope


@dataclass
class _PivotState:
    highs: list[tuple[int, float]] = field(default_factory=list)
    lows: list[tuple[int, float]] = field(default_factory=list)
    trend: int = 0


class MarketStructureEngine:
    def generate(self, df: pd.DataFrame, config: StrategyConfig) -> list[MarketStructureEvent]:
        frame = normalize_frame(df)
        events: list[MarketStructureEvent] = []
        internal = _PivotState()
        swing = _PivotState()

        for idx in range(len(frame)):
            self._collect_pivot(frame, idx, config.internal_lookback, internal)
            self._collect_pivot(frame, idx, config.swing_lookback, swing)
            events.extend(self._check_breakouts(frame, idx, internal, StructureScope.INTERNAL))
            if config.use_swing_order_blocks:
                events.extend(self._check_breakouts(frame, idx, swing, StructureScope.SWING))
        return events

    def _collect_pivot(self, frame: pd.DataFrame, idx: int, lookback: int, state: _PivotState) -> None:
        if idx < lookback * 2:
            return
        pivot_idx = idx - lookback
        low_window = frame["low"].iloc[pivot_idx - lookback : pivot_idx + lookback + 1]
        high_window = frame["high"].iloc[pivot_idx - lookback : pivot_idx + lookback + 1]
        if frame.at[pivot_idx, "high"] >= high_window.max():
            state.highs.insert(0, (pivot_idx, float(frame.at[pivot_idx, "high"])))
            state.highs = state.highs[:10]
        if frame.at[pivot_idx, "low"] <= low_window.min():
            state.lows.insert(0, (pivot_idx, float(frame.at[pivot_idx, "low"])))
            state.lows = state.lows[:10]

    def _check_breakouts(
        self,
        frame: pd.DataFrame,
        idx: int,
        state: _PivotState,
        scope: StructureScope,
    ) -> list[MarketStructureEvent]:
        events: list[MarketStructureEvent] = []
        close = float(frame.at[idx, "close"])

        if state.highs and len(state.lows) > 1 and close > state.highs[0][1]:
            kind = EventKind.BOS
            if state.trend < 0:
                kind = EventKind.CHOCH_PLUS if state.lows[0][1] > state.lows[1][1] else EventKind.CHOCH
            events.append(
                MarketStructureEvent(
                    index=idx,
                    timestamp=frame.at[idx, "timestamp"],
                    kind=kind,
                    scope=scope,
                    side=Side.LONG,
                    pivot_index=state.highs[0][0],
                    pivot_price=state.highs[0][1],
                    breakout_price=close,
                )
            )
            state.trend = 1
            state.highs.clear()

        if state.lows and len(state.highs) > 1 and close < state.lows[0][1]:
            kind = EventKind.BOS
            if state.trend > 0:
                kind = EventKind.CHOCH_PLUS if state.highs[0][1] < state.highs[1][1] else EventKind.CHOCH
            events.append(
                MarketStructureEvent(
                    index=idx,
                    timestamp=frame.at[idx, "timestamp"],
                    kind=kind,
                    scope=scope,
                    side=Side.SHORT,
                    pivot_index=state.lows[0][0],
                    pivot_price=state.lows[0][1],
                    breakout_price=close,
                )
            )
            state.trend = -1
            state.lows.clear()

        return events
