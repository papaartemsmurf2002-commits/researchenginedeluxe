from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import pandas as pd

FEATURE_ALIGNMENT_CONTRACT_VERSION = "v1-completed-bar-point-in-time-alignment"


@dataclass(frozen=True, slots=True)
class CompletedBarValidation:
    valid: bool
    errors: tuple[str, ...]
    quality_flags: tuple[str, ...]
    duplicate_bar_times: tuple[int, ...]
    gap_start_times: tuple[int, ...]
    incomplete_bar_times: tuple[int, ...]
    row_count: int


def validate_completed_bar_continuity(
    bars: pd.DataFrame,
    *,
    bar_time_column: str,
    interval_ms: int,
    current_time_ms: int | None = None,
    require_continuous: bool = True,
) -> CompletedBarValidation:
    """Validate that bars are unique, interval-spaced, and completed if a clock is given."""

    _validate_interval(interval_ms)
    errors: list[str] = []
    quality_flags: list[str] = []
    if bar_time_column not in bars.columns:
        return CompletedBarValidation(
            valid=False,
            errors=(f"missing_bar_time_column:{bar_time_column}",),
            quality_flags=("missing_bar_time_column",),
            duplicate_bar_times=(),
            gap_start_times=(),
            incomplete_bar_times=(),
            row_count=len(bars),
        )

    times = _numeric_time_series(bars[bar_time_column], bar_time_column)
    if times.isna().any():
        errors.append(f"bar_time_column_contains_null_or_non_numeric:{bar_time_column}")
        return CompletedBarValidation(
            valid=False,
            errors=tuple(errors),
            quality_flags=("invalid_bar_time",),
            duplicate_bar_times=(),
            gap_start_times=(),
            incomplete_bar_times=(),
            row_count=len(bars),
        )

    ordered_times = times.astype("int64").sort_values(kind="mergesort").reset_index(drop=True)
    duplicate_times = tuple(int(value) for value in ordered_times[ordered_times.duplicated()].drop_duplicates())
    if duplicate_times:
        quality_flags.append("duplicate_bar_times")
        errors.append(f"duplicate_bar_times:{','.join(str(value) for value in duplicate_times)}")

    unique_times = ordered_times.drop_duplicates().reset_index(drop=True)
    gap_start_times: tuple[int, ...] = ()
    if require_continuous and len(unique_times) > 1:
        diffs = unique_times.diff().iloc[1:]
        gap_indexes = [int(index) for index, diff in diffs.items() if int(diff) != int(interval_ms)]
        if gap_indexes:
            gap_start_times = tuple(int(unique_times.iloc[index - 1]) for index in gap_indexes)
            quality_flags.append("bar_time_gaps")
            errors.append(f"bar_time_gaps:{','.join(str(value) for value in gap_start_times)}")

    incomplete_bar_times: tuple[int, ...] = ()
    if current_time_ms is not None:
        current_ms = int(current_time_ms)
        incomplete = unique_times[(unique_times + int(interval_ms)) > current_ms]
        incomplete_bar_times = tuple(int(value) for value in incomplete)
        if incomplete_bar_times:
            quality_flags.append("incomplete_current_bars")

    if len(bars) == 0:
        quality_flags.append("empty_bar_series")

    return CompletedBarValidation(
        valid=not errors,
        errors=tuple(errors),
        quality_flags=tuple(sorted(set(quality_flags))),
        duplicate_bar_times=duplicate_times,
        gap_start_times=gap_start_times,
        incomplete_bar_times=incomplete_bar_times,
        row_count=len(bars),
    )


def prepare_completed_bar_feature_input(
    bars: pd.DataFrame,
    *,
    bar_time_column: str,
    interval_ms: int,
    current_time_ms: int | None = None,
    feature_time_column: str = "feature_time_ms",
    require_continuous: bool = True,
    raise_on_error: bool = True,
) -> tuple[pd.DataFrame, CompletedBarValidation]:
    """Return sorted completed bars with feature time set to bar close time."""

    validation = validate_completed_bar_continuity(
        bars,
        bar_time_column=bar_time_column,
        interval_ms=interval_ms,
        current_time_ms=current_time_ms,
        require_continuous=require_continuous,
    )
    if raise_on_error and not validation.valid:
        raise ValueError("; ".join(validation.errors))

    if bar_time_column not in bars.columns:
        return bars.copy(), validation

    prepared = bars.copy()
    prepared[bar_time_column] = _required_integer_time_series(prepared[bar_time_column], bar_time_column)
    if current_time_ms is not None:
        prepared = prepared[(prepared[bar_time_column] + int(interval_ms)) <= int(current_time_ms)].copy()
    prepared = prepared.sort_values(bar_time_column, kind="mergesort").reset_index(drop=True)
    prepared[feature_time_column] = prepared[bar_time_column] + int(interval_ms)
    return prepared, validation


def align_completed_bar_features_to_events(
    events: pd.DataFrame,
    features: pd.DataFrame,
    *,
    feature_columns: Sequence[str],
    decision_time_column: str = "decision_time_ms",
    feature_time_column: str = "feature_time_ms",
    availability_prefix: str = "feature_available_",
    max_feature_age_ms: int | None = None,
) -> pd.DataFrame:
    """As-of join completed-bar features to events without looking forward."""

    if decision_time_column not in events.columns:
        raise ValueError(f"missing_decision_time_column:{decision_time_column}")
    if feature_time_column not in features.columns:
        raise ValueError(f"missing_feature_time_column:{feature_time_column}")
    if max_feature_age_ms is not None and int(max_feature_age_ms) < 0:
        raise ValueError("max_feature_age_ms must be non-negative")

    feature_columns = tuple(str(column) for column in feature_columns)
    event_frame = events.copy()
    event_frame[decision_time_column] = _required_integer_time_series(
        event_frame[decision_time_column],
        decision_time_column,
    )
    event_frame["_feature_alignment_order"] = range(len(event_frame))

    existing_feature_columns = [column for column in feature_columns if column in features.columns]
    feature_frame = features.loc[:, [feature_time_column, *existing_feature_columns]].copy()
    feature_frame[feature_time_column] = _required_integer_time_series(
        feature_frame[feature_time_column],
        feature_time_column,
    )
    feature_frame = feature_frame.sort_values(feature_time_column, kind="mergesort").reset_index(drop=True)
    if feature_frame[feature_time_column].duplicated().any():
        duplicates = feature_frame.loc[feature_frame[feature_time_column].duplicated(), feature_time_column]
        duplicate_text = ",".join(str(int(value)) for value in duplicates.drop_duplicates())
        raise ValueError(f"duplicate_feature_time:{duplicate_text}")

    merged = pd.merge_asof(
        event_frame.sort_values(decision_time_column, kind="mergesort"),
        feature_frame,
        left_on=decision_time_column,
        right_on=feature_time_column,
        direction="backward",
        allow_exact_matches=True,
    )
    if not merged.empty and (
        merged[feature_time_column].notna()
        & (merged[feature_time_column] > merged[decision_time_column])
    ).any():  # pragma: no cover - defensive guard around merge_asof
        raise AssertionError("feature alignment used a future feature row")

    feature_age = merged[decision_time_column] - merged[feature_time_column]
    age_available = merged[feature_time_column].notna()
    if max_feature_age_ms is not None:
        age_available = age_available & (feature_age <= int(max_feature_age_ms))
    merged["feature_age_ms"] = feature_age
    merged["feature_row_available"] = age_available.astype(bool)

    availability_columns: list[str] = []
    for column in feature_columns:
        if column not in merged.columns:
            merged[column] = pd.NA
        availability_column = feature_availability_column(column, prefix=availability_prefix)
        availability_columns.append(availability_column)
        merged[availability_column] = (age_available & merged[column].notna()).astype(bool)

    if availability_columns:
        merged["feature_alignment_available"] = merged[availability_columns].all(axis=1).astype(bool)
    else:
        merged["feature_alignment_available"] = merged["feature_row_available"].astype(bool)

    return (
        merged.sort_values("_feature_alignment_order", kind="mergesort")
        .drop(columns=["_feature_alignment_order"])
        .reset_index(drop=True)
    )


def feature_availability_column(feature_column: str, *, prefix: str = "feature_available_") -> str:
    return f"{prefix}{feature_column}"


def _validate_interval(interval_ms: int) -> None:
    if int(interval_ms) <= 0:
        raise ValueError("interval_ms must be positive")


def _numeric_time_series(series: pd.Series, column_name: str) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    if values.isna().any():
        return values
    if ((values % 1) != 0).any():
        raise ValueError(f"time_column_must_be_integer_ms:{column_name}")
    return values.astype("int64")


def _required_integer_time_series(series: pd.Series, column_name: str) -> pd.Series:
    values = _numeric_time_series(series, column_name)
    if values.isna().any():
        raise ValueError(f"time_column_contains_null_or_non_numeric:{column_name}")
    return values.astype("int64")
