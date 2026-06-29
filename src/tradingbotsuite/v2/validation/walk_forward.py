# V2-AUDIT-ID: V2-AUD-VAL-001
# V2-CONTRACTS: docs/contracts/validation_contract.md
# V2-BOUNDARY: research_only, walk_forward_validation, no_live_imports
# V2-OWNER: v2_validation
"""Walk-forward split and fold-stability helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import ensure_utc, utc_isoformat


class WalkForwardConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    min_train_rows: int = Field(ge=1)
    validation_rows: int = Field(ge=1)
    step_rows: int = Field(ge=1)
    purge_rows: int = Field(default=0, ge=0)
    embargo_rows: int = Field(default=0, ge=0)
    min_folds: int = Field(default=1, ge=1)
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False

    @model_validator(mode="after")
    def _validate_boundary(self) -> "WalkForwardConfig":
        if not self.research_only or not self.observe_only or self.promotion_ready:
            raise ValueError("walk-forward config must preserve the v2 research boundary")
        if self.purge_rows >= self.min_train_rows:
            raise ValueError("purge_rows must be smaller than min_train_rows")
        return self


class WalkForwardFold(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    fold_id: str = Field(min_length=1)
    fold_index: int = Field(ge=0)
    train_indices: tuple[int, ...]
    embargo_indices: tuple[int, ...] = ()
    validation_indices: tuple[int, ...]
    train_start: datetime
    train_end: datetime
    validation_start: datetime
    validation_end: datetime
    purge_rows: int = Field(ge=0)
    embargo_rows: int = Field(ge=0)
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False

    @field_validator("train_start", "train_end", "validation_start", "validation_end")
    @classmethod
    def _utc_timestamps(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @model_validator(mode="after")
    def _validate_fold(self) -> "WalkForwardFold":
        if not self.train_indices or not self.validation_indices:
            raise ValueError("walk-forward folds require train and validation indices")
        if max(self.train_indices) >= min(self.validation_indices):
            raise ValueError("train indices must be before validation indices")
        if set(self.train_indices) & set(self.validation_indices):
            raise ValueError("train and validation indices overlap")
        if set(self.embargo_indices) & set(self.validation_indices):
            raise ValueError("embargo and validation indices overlap")
        if set(self.embargo_indices) & set(self.train_indices):
            raise ValueError("embargo and train indices overlap")
        if self.train_end >= self.validation_start:
            raise ValueError("train_end must be before validation_start")
        if not self.research_only or not self.observe_only or self.promotion_ready:
            raise ValueError("walk-forward fold must preserve the v2 research boundary")
        return self


class FoldMetric(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    fold_id: str = Field(min_length=1)
    net_return: float
    gross_return: float | None = None
    trade_count: int | None = Field(default=None, ge=0)
    stability_pass: bool
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False


class FoldStabilitySummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    fold_count: int = Field(ge=0)
    positive_fold_count: int = Field(ge=0)
    fold_stability_score: float = Field(ge=0.0, le=1.0)
    median_net_return: float | None = None
    best_net_return: float | None = None
    worst_net_return: float | None = None
    stability_pass: bool
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False


def build_walk_forward_folds(
    rows: Iterable[Mapping[str, Any]],
    *,
    config: WalkForwardConfig,
    ts_field: str = "ts",
) -> tuple[WalkForwardFold, ...]:
    timestamps = [_parse_timestamp(row[ts_field]) for row in rows]
    if sorted(timestamps) != timestamps:
        raise ValueError("walk-forward rows must be sorted by timestamp")
    folds: list[WalkForwardFold] = []
    total = len(timestamps)
    anchor = config.min_train_rows
    fold_index = 0
    while True:
        train_end_exclusive = anchor - config.purge_rows
        validation_start = anchor + config.embargo_rows
        validation_end = validation_start + config.validation_rows
        if train_end_exclusive <= 0 or validation_end > total:
            break
        train_indices = tuple(range(0, train_end_exclusive))
        embargo_indices = tuple(range(train_end_exclusive, validation_start))
        validation_indices = tuple(range(validation_start, validation_end))
        folds.append(
            WalkForwardFold(
                fold_id=f"fold-{fold_index:04d}",
                fold_index=fold_index,
                train_indices=train_indices,
                embargo_indices=embargo_indices,
                validation_indices=validation_indices,
                train_start=timestamps[train_indices[0]],
                train_end=timestamps[train_indices[-1]],
                validation_start=timestamps[validation_indices[0]],
                validation_end=timestamps[validation_indices[-1]],
                purge_rows=config.purge_rows,
                embargo_rows=config.embargo_rows,
            )
        )
        fold_index += 1
        anchor += config.step_rows
    if len(folds) < config.min_folds:
        raise ValueError("walk-forward split produced fewer folds than min_folds")
    return tuple(folds)


def summarize_fold_stability(
    fold_metrics: Iterable[Mapping[str, Any] | FoldMetric],
    *,
    min_positive_share: float = 0.5,
) -> FoldStabilitySummary:
    metrics = [
        item if isinstance(item, FoldMetric) else FoldMetric.model_validate(item)
        for item in fold_metrics
    ]
    if not metrics:
        return FoldStabilitySummary(
            fold_count=0,
            positive_fold_count=0,
            fold_stability_score=0.0,
            stability_pass=False,
        )
    returns = sorted(metric.net_return for metric in metrics)
    positive = sum(1 for value in returns if value > 0.0)
    score = positive / len(returns)
    return FoldStabilitySummary(
        fold_count=len(returns),
        positive_fold_count=positive,
        fold_stability_score=score,
        median_net_return=_median(returns),
        best_net_return=max(returns),
        worst_net_return=min(returns),
        stability_pass=score >= min_positive_share,
    )


def fold_rows_for_artifact(folds: Iterable[WalkForwardFold]) -> list[dict[str, Any]]:
    return [
        {
            "fold_id": fold.fold_id,
            "fold_index": fold.fold_index,
            "train_start": utc_isoformat(fold.train_start),
            "train_end": utc_isoformat(fold.train_end),
            "validation_start": utc_isoformat(fold.validation_start),
            "validation_end": utc_isoformat(fold.validation_end),
            "train_row_count": len(fold.train_indices),
            "embargo_row_count": len(fold.embargo_indices),
            "validation_row_count": len(fold.validation_indices),
            "purge_rows": fold.purge_rows,
            "embargo_rows": fold.embargo_rows,
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
        }
        for fold in folds
    ]


def monthly_validation_fold_windows(
    start: datetime,
    end: datetime,
    *,
    max_folds: int = 4,
) -> tuple[tuple[datetime, datetime], ...]:
    """Return complete tested calendar-month windows, capped for validation."""

    start = ensure_utc(start)
    end = ensure_utc(end)
    if end <= start or max_folds <= 0:
        return ()
    current = datetime(start.year, start.month, 1, tzinfo=UTC)
    if start > current:
        current = _add_months(current, 1)
    windows: list[tuple[datetime, datetime]] = []
    while len(windows) < max_folds:
        next_month = _add_months(current, 1)
        if next_month > end:
            break
        windows.append((current, next_month))
        current = next_month
    return tuple(windows)


def expected_monthly_validation_fold_count(
    start: datetime,
    end: datetime,
    *,
    max_folds: int = 4,
) -> int:
    return len(monthly_validation_fold_windows(start, end, max_folds=max_folds))


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return ensure_utc(value)
    if isinstance(value, str):
        return ensure_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
    raise ValueError(f"unsupported timestamp value: {value!r}")


def _add_months(value: datetime, months: int) -> datetime:
    month_index = value.year * 12 + (value.month - 1) + months
    year = month_index // 12
    month = (month_index % 12) + 1
    return value.replace(year=year, month=month)


def _median(values: list[float]) -> float:
    midpoint = len(values) // 2
    if len(values) % 2:
        return values[midpoint]
    return (values[midpoint - 1] + values[midpoint]) / 2.0
