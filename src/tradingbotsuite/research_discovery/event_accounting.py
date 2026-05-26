from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
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
    ordered = _accepted_event_frame(accepted)
    if ordered.empty:
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
            event_spacing_bars=spacing,
            near_signal_ceiling=False,
        )
    symbols = ordered["symbol"].astype(str).to_numpy()
    source_rows = ordered["source_row_index"].astype("int64").to_numpy()
    independent_mask = np.zeros(len(ordered), dtype=bool)
    blocked_until_by_symbol: dict[str, int] = {}
    for index, (symbol, source_row) in enumerate(zip(symbols, source_rows, strict=True)):
        blocked_until = blocked_until_by_symbol.get(symbol, -1)
        if source_row <= blocked_until:
            continue
        independent_mask[index] = True
        blocked_until_by_symbol[symbol] = int(source_row) + spacing - 1

    accepted_count = int(len(ordered))
    independent = ordered.loc[independent_mask]
    independent_count = int(len(independent))
    suppressed_count = int(max(0, accepted_count - independent_count))
    event_signal_rate = float(independent_count / max(1, int(total_row_count)))
    overlap_ratio = float(suppressed_count / max(1, accepted_count))
    side_values = independent["side"].astype(str) if independent_count else pd.Series(dtype=str)
    long_count = int(side_values.eq("long").sum()) if independent_count else 0
    short_count = int(side_values.eq("short").sum()) if independent_count else 0
    side_collapse_ratio = float(max(long_count, short_count) / independent_count) if independent_count else 0.0
    returns = pd.to_numeric(independent.get("side_adjusted_return", pd.Series(dtype=float)), errors="coerce").dropna()
    returns = returns[np.isfinite(returns.to_numpy(dtype=float))]
    gross_return = float(returns.sum()) if not returns.empty else 0.0
    expectancy = float(gross_return / len(returns)) if not returns.empty else 0.0
    neighbor_quality = _series_mean_optional_float(independent.get("neighbor_distance_quality"))
    vote_margin = _series_mean_optional_float(independent.get("knn_vote_margin"))
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


def account_independent_events_arrays(
    *,
    accepted_mask: np.ndarray,
    symbol_codes: np.ndarray,
    source_row_index: np.ndarray,
    p_up_barrier: np.ndarray,
    p_down_barrier: np.ndarray,
    side_adjusted_return: np.ndarray,
    neighbor_distance_quality: np.ndarray,
    knn_vote_margin: np.ndarray,
    total_row_count: int,
    label_horizon_bars: int,
    max_signal_rate: float,
    minimum_spacing_bars: int | None = None,
) -> IndependentEventAccounting:
    spacing = max(1, int(minimum_spacing_bars or label_horizon_bars or 1))
    accepted = np.asarray(accepted_mask, dtype=bool)
    valid = (
        accepted
        & np.isfinite(source_row_index)
        & np.isfinite(p_up_barrier)
        & np.isfinite(p_down_barrier)
        & np.isfinite(side_adjusted_return)
    )
    positions = np.flatnonzero(valid)
    if len(positions) == 0:
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
            event_spacing_bars=spacing,
            near_signal_ceiling=False,
        )

    source_values = source_row_index[positions].astype("int64", copy=False)
    symbol_values = symbol_codes[positions].astype("int64", copy=False)
    order = np.lexsort((positions, source_values, symbol_values))
    ordered_positions = positions[order]
    ordered_sources = source_row_index[ordered_positions].astype("int64", copy=False)
    ordered_symbols = symbol_codes[ordered_positions].astype("int64", copy=False)

    independent_positions: list[int] = []
    blocked_until_by_symbol: dict[int, int] = {}
    for position, symbol, source_row in zip(ordered_positions, ordered_symbols, ordered_sources, strict=True):
        blocked_until = blocked_until_by_symbol.get(int(symbol), -1)
        if int(source_row) <= blocked_until:
            continue
        independent_positions.append(int(position))
        blocked_until_by_symbol[int(symbol)] = int(source_row) + spacing - 1

    accepted_count = int(len(positions))
    independent_index = np.asarray(independent_positions, dtype=int)
    independent_count = int(len(independent_index))
    suppressed_count = int(max(0, accepted_count - independent_count))
    event_signal_rate = float(independent_count / max(1, int(total_row_count)))
    overlap_ratio = float(suppressed_count / max(1, accepted_count))
    short_mask = p_down_barrier[independent_index] > p_up_barrier[independent_index] if independent_count else np.asarray([], dtype=bool)
    short_count = int(np.count_nonzero(short_mask)) if independent_count else 0
    long_count = int(independent_count - short_count)
    side_collapse_ratio = float(max(long_count, short_count) / independent_count) if independent_count else 0.0
    returns = side_adjusted_return[independent_index] if independent_count else np.asarray([], dtype=float)
    finite_returns = returns[np.isfinite(returns)]
    gross_return = float(finite_returns.sum()) if len(finite_returns) else 0.0
    expectancy = float(gross_return / len(finite_returns)) if len(finite_returns) else 0.0
    neighbor_quality = _array_mean_optional_float(neighbor_distance_quality[independent_index]) if independent_count else 0.0
    vote_margin = _array_mean_optional_float(knn_vote_margin[independent_index]) if independent_count else 0.0
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


def _accepted_event_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(
            columns=[
                "symbol",
                "source_row_index",
                "original_position",
                "side",
                "side_adjusted_return",
                "neighbor_distance_quality",
                "knn_vote_margin",
            ]
        )
    source = pd.to_numeric(frame.get("source_row_index"), errors="coerce")
    p_up = pd.to_numeric(frame.get("p_up_barrier"), errors="coerce")
    p_down = pd.to_numeric(frame.get("p_down_barrier"), errors="coerce")
    raw_return = pd.to_numeric(frame.get("label_return"), errors="coerce")
    source_values = source.to_numpy(dtype=float)
    finite_source = np.isfinite(source_values)
    integer_source = finite_source & (source_values == np.floor(source_values))
    valid = (
        integer_source
        & np.isfinite(p_up.to_numpy(dtype=float))
        & np.isfinite(p_down.to_numpy(dtype=float))
        & np.isfinite(raw_return.to_numpy(dtype=float))
    )
    if not bool(np.any(valid)):
        return pd.DataFrame(
            columns=[
                "symbol",
                "source_row_index",
                "original_position",
                "side",
                "side_adjusted_return",
                "neighbor_distance_quality",
                "knn_vote_margin",
            ]
        )
    symbols = (
        frame["symbol"].astype(str).fillna("")
        if "symbol" in frame.columns
        else pd.Series([""] * len(frame), index=frame.index, dtype=object)
    )
    side_short = p_down.to_numpy(dtype=float) > p_up.to_numpy(dtype=float)
    side_multiplier = np.where(side_short, -1.0, 1.0)
    valid_positions = np.flatnonzero(valid)
    result = pd.DataFrame(
        {
            "symbol": symbols.to_numpy(dtype=object)[valid_positions],
            "source_row_index": source_values[valid_positions].astype("int64"),
            "original_position": valid_positions.astype("int64"),
            "side": np.where(side_short, "short", "long")[valid_positions],
            "side_adjusted_return": (raw_return.to_numpy(dtype=float) * side_multiplier)[valid_positions],
            "neighbor_distance_quality": pd.to_numeric(
                frame.get("neighbor_distance_quality", pd.Series([np.nan] * len(frame), index=frame.index)),
                errors="coerce",
            ).to_numpy(dtype=float)[valid_positions],
            "knn_vote_margin": pd.to_numeric(
                frame.get("knn_vote_margin", pd.Series([np.nan] * len(frame), index=frame.index)),
                errors="coerce",
            ).to_numpy(dtype=float)[valid_positions],
        }
    )
    return result.sort_values(["symbol", "source_row_index", "original_position"], kind="mergesort").reset_index(drop=True)


def _series_mean_optional_float(values: Any) -> float:
    if values is None:
        return 0.0
    series = pd.to_numeric(values, errors="coerce").dropna()
    if series.empty:
        return 0.0
    finite = series[np.isfinite(series.to_numpy(dtype=float))]
    return float(finite.mean()) if not finite.empty else 0.0


def _array_mean_optional_float(values: np.ndarray) -> float:
    array = np.asarray(values, dtype=float)
    finite = array[np.isfinite(array)]
    return float(finite.mean()) if len(finite) else 0.0


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
