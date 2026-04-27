from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

import pandas as pd

from tradingbot.indicators import normalize_frame
from tradingbot.models import MarketStructureEvent, OrderBlock, Side, StrategyConfig


@dataclass
class OrderBlockTimeline:
    blocks: list[OrderBlock]
    active_by_index: dict[int, list[OrderBlock]]


class OrderBlockEngine:
    def process(
        self,
        df: pd.DataFrame,
        events: list[MarketStructureEvent],
        config: StrategyConfig,
    ) -> OrderBlockTimeline:
        frame = normalize_frame(df)
        events_by_index: dict[int, list[MarketStructureEvent]] = {}
        for event in events:
            events_by_index.setdefault(event.index, []).append(event)

        blocks: list[OrderBlock] = []
        active_blocks: list[OrderBlock] = []
        snapshots: dict[int, list[OrderBlock]] = {}

        for idx in range(len(frame)):
            for event in events_by_index.get(idx, []):
                if config.order_block_filter != "None" and event.kind.value != config.order_block_filter:
                    continue
                block = self._build_block(frame, event, config)
                active_blocks = [existing for existing in active_blocks if existing.active]
                active_blocks.append(block)
                self._apply_overlap(active_blocks, config)
                self._recalculate_relevance(active_blocks)
                blocks.append(block)

            for block in active_blocks:
                if not block.active:
                    continue
                if self._is_mitigated(block, frame.iloc[idx], config):
                    block.mitigated_index = idx
                    continue
                if self._touches_block(block, frame.iloc[idx]):
                    block.touched_index = idx

            active_blocks = [block for block in active_blocks if block.active]
            self._recalculate_relevance(active_blocks)
            snapshots[idx] = [block for block in active_blocks]

        return OrderBlockTimeline(blocks=blocks, active_by_index=snapshots)

    def _build_block(self, frame: pd.DataFrame, event: MarketStructureEvent, config: StrategyConfig) -> OrderBlock:
        segment = frame.iloc[event.pivot_index : event.index + 1].copy()
        if segment.empty:
            segment = frame.iloc[[event.index]].copy()

        if event.side == Side.LONG:
            anchor_idx = int(segment["low"].idxmin())
            anchor = frame.loc[anchor_idx]
            bottom = float(segment["low"].min())
            top = self._bullish_top(anchor, config)
        else:
            anchor_idx = int(segment["high"].idxmax())
            anchor = frame.loc[anchor_idx]
            top = float(segment["high"].max())
            bottom = self._bearish_bottom(anchor, config)

        midpoint = (top + bottom) / 2.0
        return OrderBlock(
            block_id=uuid4().hex[:12],
            created_index=event.index,
            created_timestamp=event.timestamp,
            scope=event.scope,
            side=event.side,
            top=top,
            bottom=bottom,
            midpoint=midpoint,
            anchor_index=anchor_idx,
            anchor_volume=float(anchor["volume"]),
            metadata={"event_kind": event.kind.value, "pivot_price": event.pivot_price},
        )

    def _bullish_top(self, anchor: pd.Series, config: StrategyConfig) -> float:
        if config.order_block_position == "Full":
            return float(anchor["high"])
        if config.order_block_position == "Middle":
            return float((anchor["open"] + anchor["high"] + anchor["low"] + anchor["close"]) / 4.0)
        return float((anchor["high"] + anchor["low"]) / 2.0)

    def _bearish_bottom(self, anchor: pd.Series, config: StrategyConfig) -> float:
        if config.order_block_position == "Full":
            return float(anchor["low"])
        if config.order_block_position == "Middle":
            return float((anchor["open"] + anchor["high"] + anchor["low"] + anchor["close"]) / 4.0)
        return float((anchor["high"] + anchor["low"]) / 2.0)

    def _apply_overlap(self, active_blocks: list[OrderBlock], config: StrategyConfig) -> None:
        if not config.order_block_overlap or len(active_blocks) < 2:
            return
        newest = active_blocks[-1]
        for previous in active_blocks[:-1]:
            if previous.side != newest.side or previous.scope != newest.scope or not previous.active:
                continue
            overlaps = newest.bottom < previous.top and newest.top > previous.bottom
            if not overlaps:
                continue
            if config.order_block_overlap_method == "Recent":
                newest.mitigated_index = newest.created_index
            else:
                previous.mitigated_index = newest.created_index

    def _recalculate_relevance(self, active_blocks: list[OrderBlock]) -> None:
        total = sum(block.anchor_volume for block in active_blocks) or 1.0
        for block in active_blocks:
            block.relevance_pct = (block.anchor_volume / total) * 100.0

    def _is_mitigated(self, block: OrderBlock, row: pd.Series, config: StrategyConfig) -> bool:
        trigger = block.midpoint if config.order_block_mitigation == "Middle" else (block.bottom if block.side == Side.LONG else block.top)
        close = float(row["close"])
        if block.side == Side.LONG:
            return close < trigger
        return close > trigger

    def _touches_block(self, block: OrderBlock, row: pd.Series) -> bool:
        return float(row["high"]) >= block.bottom and float(row["low"]) <= block.top

    def find_qualifying_opposite_block(
        self,
        active_blocks: list[OrderBlock],
        position_side: Side,
        row: pd.Series,
        config: StrategyConfig,
    ) -> OrderBlock | None:
        desired_side = Side.SHORT if position_side == Side.LONG else Side.LONG
        candidates = [
            block
            for block in active_blocks
            if block.side == desired_side and block.relevance_pct >= config.order_block_relevance_pct and self._touches_block(block, row)
        ]
        if not candidates:
            return None
        return sorted(candidates, key=lambda block: (block.relevance_pct, block.created_index), reverse=True)[0]
