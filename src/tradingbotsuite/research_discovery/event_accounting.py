from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True, slots=True)
class IndependentEventAccounting:
    accepted_bar_count: int
    independent_event_count: int
    suppressed_overlap_count: int
    overlap_ratio: float
    event_signal_rate: float
    long_independent_event_count: int
    short_independent_event_count: int
    side_collapse_ratio: float
    independent_event_expectancy: float
    gross_independent_event_return: float
    avg_independent_neighbor_quality: float
    avg_independent_vote_margin: float
    event_spacing_bars: int
    near_signal_ceiling: bool

    def to_payload(self) -> dict[str, Any]:
        return {
            "accepted_bar_count": self.accepted_bar_count,
            "independent_event_count": self.independent_event_count,
            "suppressed_overlap_count": self.suppressed_overlap_count,
            "overlap_ratio": self.overlap_ratio,
            "event_signal_rate": self.event_signal_rate,
            "long_independent_event_count": self.long_independent_event_count,
            "short_independent_event_count": self.short_independent_event_count,
            "side_collapse_ratio": self.side_collapse_ratio,
            "independent_event_expectancy": self.independent_event_expectancy,
            "gross_independent_event_return": self.gross_independent_event_return,
            "avg_independent_neighbor_quality": self.avg_independent_neighbor_quality,
            "avg_independent_vote_margin": self.avg_independent_vote_margin,
            "event_spacing_bars": self.event_spacing_bars,
            "near_signal_ceiling": self.near_signal_ceiling,
        }


def account_independent_events(
    accepted: pd.DataFrame,
    *,
    total_row_count: int,
    label_horizon_bars: int,
    max_signal_rate: float,
    minimum_spacing_bars: int | None = None,
) -> IndependentEventAccounting:
    if accepted.empty:
        return IndependentEventAccounting(
            accepted_bar_count=0,
            independent_event_count=0,
            suppressed_overlap_count=0,
            overlap_ratio=0.0,
            event_signal_rate=0.0,
            long_independent_event_count=0,
            short_independent_event_count=0,
            side_collapse_ratio=0.0,
            independent_event_expectancy=0.0,
            gross_independent_event_return=0.0,
            avg_independent_neighbor_quality=0.0,
            avg_independent_vote_margin=0.0,
            event_spacing_bars=max(1, int(minimum_spacing_bars or label_horizon_bars or 1)),
            near_signal_ceiling=False,
        )
    spacing = max(1, int(minimum_spacing_bars or label_horizon_bars or 1))
    ordered = _accepted_event_rows(accepted)
    independent_rows: list[dict[str, Any]] = []
    blocked_until_by_symbol: dict[str, int] = {}
    for row in ordered:
        symbol = str(row.get("symbol") or "")
        source_row = int(row["source_row_index"])
        blocked_until = blocked_until_by_symbol.get(symbol, -1)
        if source_row <= blocked_until:
            continue
        independent_rows.append(row)
        blocked_until_by_symbol[symbol] = source_row + spacing - 1

    accepted_count = int(len(ordered))
    independent_count = int(len(independent_rows))
    suppressed_count = int(max(0, accepted_count - independent_count))
    event_signal_rate = float(independent_count / max(1, int(total_row_count)))
    overlap_ratio = float(suppressed_count / max(1, accepted_count))
    long_count = sum(1 for row in independent_rows if row["side"] == "long")
    short_count = sum(1 for row in independent_rows if row["side"] == "short")
    side_collapse_ratio = float(max(long_count, short_count) / independent_count) if independent_count else 0.0
    returns = [float(row["side_adjusted_return"]) for row in independent_rows if math.isfinite(float(row["side_adjusted_return"]))]
    gross_return = float(sum(returns)) if returns else 0.0
    expectancy = float(gross_return / len(returns)) if returns else 0.0
    neighbor_quality = _mean_optional_float(row.get("neighbor_distance_quality") for row in independent_rows)
    vote_margin = _mean_optional_float(row.get("knn_vote_margin") for row in independent_rows)
    ceiling = max(float(max_signal_rate), 1e-12)
    near_signal_ceiling = bool((accepted_count / max(1, int(total_row_count))) >= ceiling * 0.90)
    return IndependentEventAccounting(
        accepted_bar_count=accepted_count,
        independent_event_count=independent_count,
        suppressed_overlap_count=suppressed_count,
        overlap_ratio=overlap_ratio,
        event_signal_rate=event_signal_rate,
        long_independent_event_count=int(long_count),
        short_independent_event_count=int(short_count),
        side_collapse_ratio=side_collapse_ratio,
        independent_event_expectancy=expectancy,
        gross_independent_event_return=gross_return,
        avg_independent_neighbor_quality=neighbor_quality,
        avg_independent_vote_margin=vote_margin,
        event_spacing_bars=spacing,
        near_signal_ceiling=near_signal_ceiling,
    )


def _accepted_event_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for original_position, (index, row) in enumerate(frame.iterrows()):
        source_row = _integer(row.get("source_row_index"))
        if source_row is None:
            continue
        p_up = _finite_float(row.get("p_up_barrier"))
        p_down = _finite_float(row.get("p_down_barrier"))
        raw_return = _finite_float(row.get("label_return"))
        if p_up is None or p_down is None or raw_return is None:
            continue
        side = "short" if p_down > p_up else "long"
        side_multiplier = -1.0 if side == "short" else 1.0
        rows.append(
            {
                "symbol": str(row.get("symbol") or ""),
                "source_row_index": int(source_row),
                "original_position": int(original_position),
                "side": side,
                "side_adjusted_return": float(raw_return * side_multiplier),
                "neighbor_distance_quality": _finite_float(row.get("neighbor_distance_quality")),
                "knn_vote_margin": _finite_float(row.get("knn_vote_margin")),
            }
        )
    return sorted(rows, key=lambda item: (str(item["symbol"]), int(item["source_row_index"]), int(item["original_position"])))


def _mean_optional_float(values: Any) -> float:
    finite = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    return float(sum(finite) / len(finite)) if finite else 0.0


def _integer(value: Any) -> int | None:
    parsed = _finite_float(value)
    if parsed is None:
        return None
    integer = int(parsed)
    if float(integer) != parsed:
        return None
    return integer


def _finite_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None
