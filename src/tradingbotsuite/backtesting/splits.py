from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

import pandas as pd


SPLIT_ENGINE_VERSION = "research-split-engine-v1"
SplitMode = Literal["anchored", "rolling"]


@dataclass(frozen=True, slots=True)
class WalkForwardSplit:
    split_id: str
    validation_method: str
    train_start_index: int
    train_end_index: int
    validation_start_index: int
    validation_end_index: int
    purge_embargo_bars: int
    train_start_time_ms: int | None
    train_end_time_ms: int | None
    validation_start_time_ms: int
    validation_end_time_ms: int
    split_mode: str = "anchored"
    train_window_bars: int | None = None
    validation_size_bars: int | None = None
    anchor_offset_bars: int | None = None
    validation_indices: tuple[int, ...] | None = None

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


def build_purged_walk_forward_splits(
    frame: pd.DataFrame,
    *,
    min_splits: int,
    purge_embargo_bars: int = 0,
    time_column: str = "bar_time_ms",
    validation_method: str = "purged_embargoed_walk_forward",
    split_mode: SplitMode = "anchored",
    train_window_bars: int | None = None,
) -> tuple[WalkForwardSplit, ...]:
    if min_splits < 1:
        raise ValueError("min_splits must be at least 1")
    if purge_embargo_bars < 0:
        raise ValueError("purge_embargo_bars must be non-negative")
    if split_mode not in {"anchored", "rolling"}:
        raise ValueError("split_mode must be anchored or rolling")
    if split_mode == "rolling" and (train_window_bars is None or int(train_window_bars) <= 0):
        raise ValueError("rolling split_mode requires positive train_window_bars")
    if time_column not in frame.columns:
        raise ValueError(f"time column missing: {time_column}")
    row_count = int(len(frame))
    if row_count < min_splits * 2:
        raise ValueError("not enough rows to build requested walk-forward splits")

    ordered = frame.sort_values(time_column, kind="mergesort").reset_index(drop=True)
    validation_size = max(1, row_count // (min_splits + 1))
    splits: list[WalkForwardSplit] = []
    for index in range(min_splits):
        validation_start = min(row_count - 1, validation_size * (index + 1))
        validation_end = min(row_count - 1, validation_start + validation_size - 1)
        if validation_start >= validation_end:
            continue
        train_end = validation_start - purge_embargo_bars - 1
        if train_end < 0:
            train_start = 0
            train_end = -1
            train_start_time = None
            train_end_time = None
        else:
            train_start = 0 if split_mode == "anchored" else max(0, train_end - int(train_window_bars or 0) + 1)
            train_start_time = int(ordered.iloc[train_start][time_column])
            train_end_time = int(ordered.iloc[train_end][time_column])
        splits.append(
            WalkForwardSplit(
                split_id=f"split-{index + 1:02d}",
                validation_method=validation_method,
                train_start_index=train_start,
                train_end_index=train_end,
                validation_start_index=validation_start,
                validation_end_index=validation_end,
                purge_embargo_bars=int(purge_embargo_bars),
                train_start_time_ms=train_start_time,
                train_end_time_ms=train_end_time,
                validation_start_time_ms=int(ordered.iloc[validation_start][time_column]),
                validation_end_time_ms=int(ordered.iloc[validation_end][time_column]),
                split_mode=split_mode,
                train_window_bars=train_window_bars,
                validation_size_bars=int(validation_end - validation_start + 1),
            )
        )
    return tuple(splits)


def build_anchored_walk_forward_splits(
    frame: pd.DataFrame,
    *,
    min_splits: int,
    purge_embargo_bars: int = 0,
    time_column: str = "bar_time_ms",
) -> tuple[WalkForwardSplit, ...]:
    return build_purged_walk_forward_splits(
        frame,
        min_splits=min_splits,
        purge_embargo_bars=purge_embargo_bars,
        time_column=time_column,
        validation_method="anchored_walk_forward",
        split_mode="anchored",
    )


def build_rolling_walk_forward_splits(
    frame: pd.DataFrame,
    *,
    min_splits: int,
    train_window_bars: int,
    purge_embargo_bars: int = 0,
    time_column: str = "bar_time_ms",
) -> tuple[WalkForwardSplit, ...]:
    return build_purged_walk_forward_splits(
        frame,
        min_splits=min_splits,
        purge_embargo_bars=purge_embargo_bars,
        time_column=time_column,
        validation_method="rolling_walk_forward",
        split_mode="rolling",
        train_window_bars=train_window_bars,
    )


def build_shifted_walk_forward_splits(
    frame: pd.DataFrame,
    *,
    min_splits: int,
    anchor_offset_bars: int,
    purge_embargo_bars: int = 0,
    time_column: str = "bar_time_ms",
) -> tuple[WalkForwardSplit, ...]:
    if min_splits < 1:
        raise ValueError("min_splits must be at least 1")
    if purge_embargo_bars < 0:
        raise ValueError("purge_embargo_bars must be non-negative")
    if anchor_offset_bars <= 0:
        raise ValueError("anchor_offset_bars must be positive")
    if time_column not in frame.columns:
        raise ValueError(f"time column missing: {time_column}")
    row_count = int(len(frame))
    if row_count < min_splits * 2:
        raise ValueError("not enough rows to build requested walk-forward splits")

    ordered = frame.sort_values(time_column, kind="mergesort").reset_index(drop=True)
    validation_size = max(1, row_count // (min_splits + 1))
    splits: list[WalkForwardSplit] = []
    for index in range(min_splits):
        validation_start = validation_size * (index + 1) + int(anchor_offset_bars)
        if validation_start >= row_count:
            continue
        validation_end = min(row_count - 1, validation_start + validation_size - 1)
        if validation_start >= validation_end:
            continue
        train_end = validation_start - purge_embargo_bars - 1
        if train_end < 0:
            train_start = 0
            train_end = -1
            train_start_time = None
            train_end_time = None
        else:
            train_start = 0
            train_start_time = int(ordered.iloc[train_start][time_column])
            train_end_time = int(ordered.iloc[train_end][time_column])
        splits.append(
            WalkForwardSplit(
                split_id=f"shift-{int(anchor_offset_bars):02d}-split-{index + 1:02d}",
                validation_method="shifted_purged_walk_forward",
                train_start_index=train_start,
                train_end_index=train_end,
                validation_start_index=int(validation_start),
                validation_end_index=int(validation_end),
                purge_embargo_bars=int(purge_embargo_bars),
                train_start_time_ms=train_start_time,
                train_end_time_ms=train_end_time,
                validation_start_time_ms=int(ordered.iloc[validation_start][time_column]),
                validation_end_time_ms=int(ordered.iloc[validation_end][time_column]),
                split_mode="shifted",
                validation_size_bars=int(validation_end - validation_start + 1),
                anchor_offset_bars=int(anchor_offset_bars),
            )
        )
    return tuple(splits)


def month_holdout_splits(
    frame: pd.DataFrame,
    *,
    time_column: str = "bar_time_ms",
) -> tuple[WalkForwardSplit, ...]:
    ordered = frame.sort_values(time_column, kind="mergesort").reset_index(drop=True)
    timestamps = pd.to_datetime(ordered[time_column].astype("int64"), unit="ms", utc=True)
    splits: list[WalkForwardSplit] = []
    for index, month in enumerate(sorted(timestamps.dt.strftime("%Y-%m").unique()), start=1):
        mask = timestamps.dt.strftime("%Y-%m") == month
        positions = ordered.index[mask].tolist()
        if not positions:
            continue
        validation_start = int(positions[0])
        validation_end = int(positions[-1])
        train_end = validation_start - 1
        splits.append(
            _holdout_split(
                ordered,
                split_id=f"month-{index:02d}",
                validation_method="month_holdout",
                validation_start=validation_start,
                validation_end=validation_end,
                train_end=train_end,
                time_column=time_column,
            )
        )
    return tuple(splits)


def regime_holdout_splits(
    frame: pd.DataFrame,
    *,
    regime_column: str = "regime",
    time_column: str = "bar_time_ms",
) -> tuple[WalkForwardSplit, ...]:
    if regime_column not in frame.columns:
        return ()
    ordered = frame.sort_values(time_column, kind="mergesort").reset_index(drop=True)
    splits: list[WalkForwardSplit] = []
    invalid_regimes = {"", "missing", "nan", "none", "unknown"}
    regimes = [
        regime
        for regime in sorted(ordered[regime_column].dropna().astype(str).unique())
        if regime.strip().lower() not in invalid_regimes
    ]
    for index, regime in enumerate(regimes, start=1):
        positions = ordered.index[ordered[regime_column].astype(str) == regime].tolist()
        if not positions:
            continue
        validation_start = int(positions[0])
        validation_end = int(positions[-1])
        splits.append(
            _holdout_split(
                ordered,
                split_id=f"regime-{index:02d}",
                validation_method="regime_holdout",
                validation_start=validation_start,
                validation_end=validation_end,
                train_end=validation_start - 1,
                time_column=time_column,
                validation_indices=tuple(int(position) for position in positions),
            )
        )
    return tuple(splits)


def stress_period_holdout_splits(
    frame: pd.DataFrame,
    *,
    volatility_column: str = "volatility_shock_zscore",
    threshold: float = 2.0,
    time_column: str = "bar_time_ms",
) -> tuple[WalkForwardSplit, ...]:
    if volatility_column not in frame.columns:
        return ()
    ordered = frame.sort_values(time_column, kind="mergesort").reset_index(drop=True)
    mask = pd.to_numeric(ordered[volatility_column], errors="coerce").fillna(0.0).abs() >= float(threshold)
    positions = ordered.index[mask].tolist()
    if not positions:
        return ()
    return (
        _holdout_split(
            ordered,
            split_id="stress-01",
            validation_method="stress_period_holdout",
            validation_start=int(positions[0]),
            validation_end=int(positions[-1]),
            train_end=int(positions[0]) - 1,
            time_column=time_column,
            validation_indices=tuple(int(position) for position in positions),
        ),
    )


def frame_for_split(frame: pd.DataFrame, split: WalkForwardSplit) -> pd.DataFrame:
    ordered = frame.sort_values("bar_time_ms", kind="mergesort").reset_index(drop=True)
    if split.validation_indices is not None:
        return ordered.iloc[list(split.validation_indices)].copy()
    return ordered.iloc[split.validation_start_index : split.validation_end_index + 1].copy()


def _holdout_split(
    ordered: pd.DataFrame,
    *,
    split_id: str,
    validation_method: str,
    validation_start: int,
    validation_end: int,
    train_end: int,
    time_column: str,
    validation_indices: tuple[int, ...] | None = None,
) -> WalkForwardSplit:
    train_end = min(train_end, validation_start - 1)
    train_start_time = int(ordered.iloc[0][time_column]) if train_end >= 0 else None
    train_end_time = int(ordered.iloc[train_end][time_column]) if train_end >= 0 else None
    return WalkForwardSplit(
        split_id=split_id,
        validation_method=validation_method,
        train_start_index=0,
        train_end_index=train_end,
        validation_start_index=validation_start,
        validation_end_index=validation_end,
        purge_embargo_bars=0,
        train_start_time_ms=train_start_time,
        train_end_time_ms=train_end_time,
        validation_start_time_ms=int(ordered.iloc[validation_start][time_column]),
        validation_end_time_ms=int(ordered.iloc[validation_end][time_column]),
        split_mode="holdout",
        validation_size_bars=(
            len(validation_indices)
            if validation_indices is not None
            else int(validation_end - validation_start + 1)
        ),
        validation_indices=validation_indices,
    )
