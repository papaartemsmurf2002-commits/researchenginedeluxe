from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any, Literal

import pandas as pd


SPLIT_ENGINE_VERSION = "research-split-engine-v2"
SplitMode = Literal["anchored", "rolling"]
EVENT_END_TIME_COLUMNS = (
    "label_event_end_time_ms",
    "event_end_time_ms",
    "label_exit_time_ms",
    "label_interval_end_ms",
    "label_future_end_time_ms",
)


@dataclass(frozen=True, slots=True)
class LabelSpec:
    event_end_time_column: str | None = None
    event_start_time_column: str = "bar_time_ms"
    interval_ms: int | None = None
    require_event_end_time: bool = True
    label_id: str = "unspecified"

    def __post_init__(self) -> None:
        if self.event_end_time_column is not None and not str(self.event_end_time_column).strip():
            raise ValueError("event_end_time_column must not be empty")
        if self.event_start_time_column is not None and not str(self.event_start_time_column).strip():
            raise ValueError("event_start_time_column must not be empty")
        if self.interval_ms is not None and int(self.interval_ms) <= 0:
            raise ValueError("interval_ms must be positive")

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


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
    train_indices: tuple[int, ...] | None = None
    validation_indices: tuple[int, ...] | None = None
    purge_method: str = "fixed_bar"
    label_event_end_time_column: str | None = None
    label_event_start_time_column: str | None = None
    label_id: str | None = None
    purge_embargo_ms: int | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        train_index_summary = _index_summary(self.train_indices)
        if train_index_summary is not None:
            payload["train_indices"] = None
            payload["train_indices_manifest_policy"] = "compacted_sha256_summary"
            payload["train_index_summary"] = train_index_summary
        return payload


def infer_label_spec(
    frame: pd.DataFrame,
    *,
    time_column: str = "bar_time_ms",
    interval_ms: int | None = None,
    require_event_end_time: bool = False,
    label_id: str = "inferred",
) -> LabelSpec | None:
    for column in EVENT_END_TIME_COLUMNS:
        if column in frame.columns:
            return LabelSpec(
                event_end_time_column=column,
                event_start_time_column=time_column,
                interval_ms=interval_ms,
                require_event_end_time=require_event_end_time,
                label_id=label_id,
            )
    if require_event_end_time:
        return LabelSpec(
            event_end_time_column=EVENT_END_TIME_COLUMNS[0],
            event_start_time_column=time_column,
            interval_ms=interval_ms,
            require_event_end_time=True,
            label_id=label_id,
        )
    return None


def build_purged_walk_forward_splits(
    frame: pd.DataFrame,
    *,
    min_splits: int,
    purge_embargo_bars: int = 0,
    time_column: str = "bar_time_ms",
    validation_method: str = "purged_embargoed_walk_forward",
    split_mode: SplitMode = "anchored",
    train_window_bars: int | None = None,
    label_spec: LabelSpec | None = None,
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
    _validate_label_spec(ordered, label_spec=label_spec)
    event_end_purge_active = _event_end_purge_active(ordered, label_spec=label_spec)
    purge_embargo_ms = _purge_embargo_ms(
        ordered,
        purge_embargo_bars=purge_embargo_bars,
        time_column=time_column,
        label_spec=label_spec,
    )
    validation_size = max(1, row_count // (min_splits + 1))
    splits: list[WalkForwardSplit] = []
    for index in range(min_splits):
        validation_start = min(row_count - 1, validation_size * (index + 1))
        validation_end = min(row_count - 1, validation_start + validation_size - 1)
        if validation_start >= validation_end:
            continue
        train_positions = _train_positions(
            ordered,
            validation_start=validation_start,
            purge_embargo_bars=purge_embargo_bars,
            purge_embargo_ms=purge_embargo_ms,
            time_column=time_column,
            split_mode=split_mode,
            train_window_bars=train_window_bars,
            label_spec=label_spec,
        )
        train_start, train_end, train_start_time, train_end_time = _train_bounds(
            ordered,
            train_positions=train_positions,
            time_column=time_column,
        )
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
                train_indices=tuple(train_positions) if event_end_purge_active else None,
                purge_method="label_event_end_time" if event_end_purge_active else "fixed_bar",
                label_event_end_time_column=label_spec.event_end_time_column if event_end_purge_active else None,
                label_event_start_time_column=label_spec.event_start_time_column if event_end_purge_active else None,
                label_id=label_spec.label_id if event_end_purge_active else None,
                purge_embargo_ms=purge_embargo_ms,
            )
        )
    return tuple(splits)


def build_anchored_walk_forward_splits(
    frame: pd.DataFrame,
    *,
    min_splits: int,
    purge_embargo_bars: int = 0,
    time_column: str = "bar_time_ms",
    label_spec: LabelSpec | None = None,
) -> tuple[WalkForwardSplit, ...]:
    return build_purged_walk_forward_splits(
        frame,
        min_splits=min_splits,
        purge_embargo_bars=purge_embargo_bars,
        time_column=time_column,
        validation_method="anchored_walk_forward",
        split_mode="anchored",
        label_spec=label_spec,
    )


def build_rolling_walk_forward_splits(
    frame: pd.DataFrame,
    *,
    min_splits: int,
    train_window_bars: int,
    purge_embargo_bars: int = 0,
    time_column: str = "bar_time_ms",
    label_spec: LabelSpec | None = None,
) -> tuple[WalkForwardSplit, ...]:
    return build_purged_walk_forward_splits(
        frame,
        min_splits=min_splits,
        purge_embargo_bars=purge_embargo_bars,
        time_column=time_column,
        validation_method="rolling_walk_forward",
        split_mode="rolling",
        train_window_bars=train_window_bars,
        label_spec=label_spec,
    )


def build_shifted_walk_forward_splits(
    frame: pd.DataFrame,
    *,
    min_splits: int,
    anchor_offset_bars: int,
    purge_embargo_bars: int = 0,
    time_column: str = "bar_time_ms",
    label_spec: LabelSpec | None = None,
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
    _validate_label_spec(ordered, label_spec=label_spec)
    event_end_purge_active = _event_end_purge_active(ordered, label_spec=label_spec)
    purge_embargo_ms = _purge_embargo_ms(
        ordered,
        purge_embargo_bars=purge_embargo_bars,
        time_column=time_column,
        label_spec=label_spec,
    )
    validation_size = max(1, row_count // (min_splits + 1))
    splits: list[WalkForwardSplit] = []
    for index in range(min_splits):
        validation_start = validation_size * (index + 1) + int(anchor_offset_bars)
        if validation_start >= row_count:
            continue
        validation_end = min(row_count - 1, validation_start + validation_size - 1)
        if validation_start >= validation_end:
            continue
        train_positions = _train_positions(
            ordered,
            validation_start=validation_start,
            purge_embargo_bars=purge_embargo_bars,
            purge_embargo_ms=purge_embargo_ms,
            time_column=time_column,
            split_mode="anchored",
            train_window_bars=None,
            label_spec=label_spec,
        )
        train_start, train_end, train_start_time, train_end_time = _train_bounds(
            ordered,
            train_positions=train_positions,
            time_column=time_column,
        )
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
                train_indices=tuple(train_positions) if event_end_purge_active else None,
                purge_method="label_event_end_time" if event_end_purge_active else "fixed_bar",
                label_event_end_time_column=label_spec.event_end_time_column if event_end_purge_active else None,
                label_event_start_time_column=label_spec.event_start_time_column if event_end_purge_active else None,
                label_id=label_spec.label_id if event_end_purge_active else None,
                purge_embargo_ms=purge_embargo_ms,
            )
        )
    return tuple(splits)


def _validate_label_spec(ordered: pd.DataFrame, *, label_spec: LabelSpec | None) -> None:
    if label_spec is None:
        return
    if label_spec.event_start_time_column not in ordered.columns:
        raise ValueError(f"event_start_time_column missing: {label_spec.event_start_time_column}")
    if label_spec.event_end_time_column is None:
        if label_spec.require_event_end_time:
            raise ValueError("event_end_time_column is required for label-aware purge")
        return
    if label_spec.event_end_time_column not in ordered.columns:
        if label_spec.require_event_end_time:
            raise ValueError(f"event_end_time_column missing: {label_spec.event_end_time_column}")
        return


def _event_end_purge_active(ordered: pd.DataFrame, *, label_spec: LabelSpec | None) -> bool:
    return (
        label_spec is not None
        and label_spec.event_end_time_column is not None
        and label_spec.event_end_time_column in ordered.columns
    )


def _train_positions(
    ordered: pd.DataFrame,
    *,
    validation_start: int,
    purge_embargo_bars: int,
    purge_embargo_ms: int | None,
    time_column: str,
    split_mode: SplitMode,
    train_window_bars: int | None,
    label_spec: LabelSpec | None,
) -> tuple[int, ...]:
    if label_spec is None:
        train_end = int(validation_start) - int(purge_embargo_bars) - 1
        if train_end < 0:
            return ()
        train_start = 0 if split_mode == "anchored" else max(0, train_end - int(train_window_bars or 0) + 1)
        return tuple(range(train_start, train_end + 1))

    event_end_column = label_spec.event_end_time_column
    if event_end_column is None or event_end_column not in ordered.columns:
        if label_spec.require_event_end_time:
            raise ValueError(f"event_end_time_column missing: {event_end_column}")
        return _train_positions(
            ordered,
            validation_start=validation_start,
            purge_embargo_bars=purge_embargo_bars,
            purge_embargo_ms=purge_embargo_ms,
            time_column=time_column,
            split_mode=split_mode,
            train_window_bars=train_window_bars,
            label_spec=None,
        )

    validation_start_time = int(ordered.iloc[int(validation_start)][time_column])
    event_end = pd.to_numeric(ordered[event_end_column], errors="coerce")
    embargo = int(purge_embargo_ms or 0)
    eligible: list[int] = []
    for position in range(int(validation_start)):
        end_time = event_end.iloc[position]
        if pd.isna(end_time):
            continue
        if int(end_time) + embargo < validation_start_time:
            eligible.append(position)
    if split_mode == "rolling":
        eligible = eligible[-int(train_window_bars or 0) :]
    return tuple(eligible)


def _train_bounds(
    ordered: pd.DataFrame,
    *,
    train_positions: tuple[int, ...],
    time_column: str,
) -> tuple[int, int, int | None, int | None]:
    if not train_positions:
        return 0, -1, None, None
    train_start = int(train_positions[0])
    train_end = int(train_positions[-1])
    return (
        train_start,
        train_end,
        int(ordered.iloc[train_start][time_column]),
        int(ordered.iloc[train_end][time_column]),
    )


def _purge_embargo_ms(
    ordered: pd.DataFrame,
    *,
    purge_embargo_bars: int,
    time_column: str,
    label_spec: LabelSpec | None,
) -> int | None:
    if label_spec is not None and label_spec.interval_ms is not None:
        return int(purge_embargo_bars) * int(label_spec.interval_ms)
    if label_spec is None:
        return None
    if int(purge_embargo_bars) == 0:
        return 0
    interval_ms = _infer_interval_ms(ordered, time_column=time_column)
    if interval_ms is None:
        raise ValueError("event-end purge requires interval_ms when purge_embargo_bars is positive")
    return int(purge_embargo_bars) * int(interval_ms)


def _infer_interval_ms(ordered: pd.DataFrame, *, time_column: str) -> int | None:
    times = pd.to_numeric(ordered[time_column], errors="coerce").dropna().sort_values(kind="mergesort")
    diffs = times.diff().dropna()
    diffs = diffs[diffs > 0]
    if diffs.empty:
        return None
    interval = int(diffs.median())
    return interval if interval > 0 else None


def _index_summary(indices: tuple[int, ...] | None) -> dict[str, Any] | None:
    if indices is None:
        return None
    values = tuple(int(index) for index in indices)
    ranges = _index_ranges(values)
    return {
        "count": int(len(values)),
        "first": int(values[0]) if values else None,
        "last": int(values[-1]) if values else None,
        "contiguous": bool(len(ranges) <= 1),
        "range_count": int(len(ranges)),
        "sha256": sha256(",".join(str(index) for index in values).encode("utf-8")).hexdigest(),
        "ranges_preview": [
            {"start": int(start), "end": int(end)}
            for start, end in (ranges[:3] + ranges[-3:] if len(ranges) > 6 else ranges)
        ],
    }


def _index_ranges(indices: tuple[int, ...]) -> list[tuple[int, int]]:
    if not indices:
        return []
    ranges: list[tuple[int, int]] = []
    start = previous = int(indices[0])
    for value in indices[1:]:
        current = int(value)
        if current == previous + 1:
            previous = current
            continue
        ranges.append((start, previous))
        start = previous = current
    ranges.append((start, previous))
    return ranges


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
    return ordered.iloc[validation_positions_for_split(split, row_count=len(ordered))].copy()


def training_positions_for_split(split: WalkForwardSplit, *, row_count: int) -> list[int]:
    if split.train_indices is not None:
        return [int(position) for position in split.train_indices if 0 <= int(position) < row_count]
    if split.train_end_index < split.train_start_index:
        return []
    start = max(0, int(split.train_start_index))
    end = min(row_count - 1, int(split.train_end_index))
    if end < start:
        return []
    return list(range(start, end + 1))


def validation_positions_for_split(split: WalkForwardSplit, *, row_count: int) -> list[int]:
    if split.validation_indices is not None:
        return [int(position) for position in split.validation_indices if 0 <= int(position) < row_count]
    start = max(0, int(split.validation_start_index))
    end = min(row_count - 1, int(split.validation_end_index))
    if end < start:
        return []
    return list(range(start, end + 1))


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
