# V2-AUDIT-ID: V2-AUD-BTDATA-001
# V2-CONTRACTS: docs/contracts/backtest_data_service_contract.md, docs/contracts/validation_contract.md
# V2-BOUNDARY: research_only, lockbox_enforced, no_live_imports
# V2-OWNER: v2_backtest_data
"""Dynamic latest full-calendar-month lockbox calculator."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from tradingbotsuite.v2.validation.policies import LockboxPolicy


@dataclass(frozen=True)
class LockboxWindow:
    policy_id: str
    start_ts: datetime
    end_ts: datetime


def latest_full_calendar_month_lockbox(
    *,
    asof_date: date | None = None,
    policy: LockboxPolicy | None = None,
) -> LockboxWindow:
    """Return the dynamic lockbox as a half-open UTC interval [start, end)."""

    effective_policy = policy or LockboxPolicy()
    today = asof_date or date.today()
    current_month_start = date(today.year, today.month, 1)
    start_date = add_months(current_month_start, -effective_policy.full_months)
    return LockboxWindow(
        policy_id=effective_policy.policy_id,
        start_ts=datetime.combine(start_date, datetime.min.time(), tzinfo=UTC),
        end_ts=datetime.combine(current_month_start, datetime.min.time(), tzinfo=UTC),
    )


def add_months(value: date, months: int) -> date:
    month_index = (value.year * 12) + (value.month - 1) + months
    year = month_index // 12
    month = (month_index % 12) + 1
    return date(year, month, 1)


def windows_overlap(
    *,
    left_start: datetime,
    left_end: datetime,
    right_start: datetime,
    right_end: datetime,
) -> bool:
    if left_end <= left_start:
        raise ValueError("left_end must be greater than left_start")
    if right_end <= right_start:
        raise ValueError("right_end must be greater than right_start")
    return left_start < right_end and right_start < left_end
