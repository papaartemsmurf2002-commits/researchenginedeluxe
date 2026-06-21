# V2-AUDIT-ID: V2-AUD-QUAL-001
# V2-CONTRACTS: docs/contracts/data_quality_contract.md
# V2-BOUNDARY: research_only, coverage_calculation, no_live_imports
# V2-OWNER: v2_data_quality
"""Expected-row and coverage-report calculations for v2 bar data."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta
from typing import Any

from tradingbotsuite.v2.archive.hashing import canonical_json_hash
from tradingbotsuite.v2.config.time import ensure_utc, utc_isoformat
from tradingbotsuite.v2.data_quality.checks import (
    build_quality_checks,
    parse_timestamp,
)
from tradingbotsuite.v2.data_quality.schemas import (
    DEFAULT_COVERAGE_MIN,
    CoverageReport,
    EvidenceMode,
    QualityStatus,
)

_TIMEFRAME_RE = re.compile(r"^(?P<count>[1-9][0-9]*)(?P<unit>[mhd])$")


def timeframe_to_timedelta(timeframe: str) -> timedelta:
    match = _TIMEFRAME_RE.fullmatch(timeframe)
    if not match:
        raise ValueError(f"unsupported bar timeframe: {timeframe!r}")
    count = int(match.group("count"))
    unit = match.group("unit")
    if unit == "m":
        return timedelta(minutes=count)
    if unit == "h":
        return timedelta(hours=count)
    if unit == "d":
        return timedelta(days=count)
    raise ValueError(f"unsupported bar timeframe unit: {unit!r}")


def expected_bar_count(start_ts: datetime, end_ts: datetime, timeframe: str) -> int:
    start = ensure_utc(start_ts)
    end = ensure_utc(end_ts)
    if end <= start:
        raise ValueError("end_ts must be greater than start_ts")
    step = timeframe_to_timedelta(timeframe)
    return int((end - start).total_seconds() // step.total_seconds())


def iter_expected_bar_timestamps(
    start_ts: datetime,
    end_ts: datetime,
    timeframe: str,
) -> Iterable[datetime]:
    start = ensure_utc(start_ts)
    step = timeframe_to_timedelta(timeframe)
    count = expected_bar_count(start, end_ts, timeframe)
    current = start
    for _index in range(count):
        yield current
        current = current + step


def coverage_report_for_bars(
    rows: Iterable[Mapping[str, Any]],
    *,
    venue: str,
    instrument_id: str,
    timeframe: str,
    start_ts: datetime,
    end_ts: datetime,
    family: str = "bars",
    ts_field: str = "ts",
    volume_field: str = "volume",
    price_field: str = "close",
    spread_field: str = "spread",
    funding_field: str = "funding",
    coverage_min: float = DEFAULT_COVERAGE_MIN,
    evidence_mode: EvidenceMode | str = EvidenceMode.ACCEPTED_RESEARCH,
) -> CoverageReport:
    start = ensure_utc(start_ts)
    end = ensure_utc(end_ts)
    mode = EvidenceMode(evidence_mode)
    materialized = list(rows)
    expected = list(iter_expected_bar_timestamps(start, end, timeframe))
    expected_set = set(expected)
    parsed_timestamps: list[datetime] = []
    parse_failures = 0
    for row in materialized:
        try:
            ts = parse_timestamp(row[ts_field])
        except (KeyError, TypeError, ValueError):
            parse_failures += 1
            continue
        if start <= ts < end:
            parsed_timestamps.append(ts)
    timestamp_counts = Counter(parsed_timestamps)
    duplicate_count = sum(count - 1 for count in timestamp_counts.values() if count > 1)
    observed_set = set(timestamp_counts) & expected_set
    missing = sorted(expected_set - observed_set)
    missing_days = tuple(sorted({ts.date().isoformat() for ts in missing}))
    expected_rows = len(expected)
    observed_rows = len(observed_set)
    coverage_ratio = observed_rows / expected_rows if expected_rows else 0.0
    quality_checks = build_quality_checks(
        materialized,
        venue=venue,
        instrument_id=instrument_id,
        family=family,
        timeframe=timeframe,
        start_ts=start,
        end_ts=end,
        ts_field=ts_field,
        volume_field=volume_field,
        price_field=price_field,
        spread_field=spread_field,
        funding_field=funding_field,
        evidence_mode=mode,
    )
    check_counts = {check.check_type: check.affected_count for check in quality_checks}
    return_outliers = check_counts.get("return_outliers", 0)
    spread_outliers = check_counts.get("spread_outliers", 0)
    funding_outliers = check_counts.get("funding_outliers", 0)
    blocker_reasons = _blocker_reasons(
        coverage_ratio=coverage_ratio,
        coverage_min=coverage_min,
        mode=mode,
        duplicate_timestamp_count=duplicate_count,
        zero_volume_count=check_counts.get("zero_volume", 0),
        stale_segment_count=check_counts.get("stale_segments", 0),
        outlier_count=return_outliers + spread_outliers + funding_outliers,
        parse_failure_count=parse_failures,
    )
    quality_status = (
        QualityStatus.NON_EVIDENCE
        if mode == EvidenceMode.SANDBOX_DIAGNOSTIC
        else QualityStatus.FAIL
        if blocker_reasons
        else QualityStatus.PASS
    )
    evidence_eligible = quality_status == QualityStatus.PASS
    caveats = (
        ("sandbox_diagnostic_non_evidence",)
        if mode == EvidenceMode.SANDBOX_DIAGNOSTIC
        else ()
    )
    identity = {
        "venue": venue,
        "instrument_id": instrument_id,
        "family": family,
        "timeframe": timeframe,
        "start_ts": utc_isoformat(start),
        "end_ts": utc_isoformat(end),
        "expected_rows": expected_rows,
        "observed_rows": observed_rows,
        "coverage_ratio": round(coverage_ratio, 12),
        "missing_timestamp_count": len(missing),
        "missing_days": missing_days,
        "duplicate_timestamp_count": duplicate_count,
        "zero_volume_count": check_counts.get("zero_volume", 0),
        "stale_segment_count": check_counts.get("stale_segments", 0),
        "return_outlier_count": return_outliers,
        "spread_outlier_count": spread_outliers,
        "funding_outlier_count": funding_outliers,
        "parse_failure_count": parse_failures,
        "evidence_mode": mode.value,
        "coverage_min": coverage_min,
    }
    return CoverageReport(
        coverage_report_id=canonical_json_hash(identity),
        venue=venue,
        instrument_id=instrument_id,
        family=family,
        timeframe=timeframe,
        start_ts=start,
        end_ts=end,
        expected_rows=expected_rows,
        observed_rows=observed_rows,
        source_row_count=len(materialized),
        coverage_ratio=coverage_ratio,
        coverage_min=coverage_min,
        missing_timestamp_count=len(missing),
        missing_timestamps_sample=tuple(utc_isoformat(ts) for ts in missing[:100]),
        missing_days=missing_days,
        duplicate_timestamp_count=duplicate_count,
        stale_segment_count=check_counts.get("stale_segments", 0),
        zero_volume_count=check_counts.get("zero_volume", 0),
        return_outlier_count=return_outliers,
        spread_outlier_count=spread_outliers,
        funding_outlier_count=funding_outliers,
        outlier_count=return_outliers + spread_outliers + funding_outliers,
        parse_failure_count=parse_failures,
        source_caveats=caveats,
        evidence_mode=mode,
        quality_status=quality_status,
        evidence_eligible=evidence_eligible,
        blocker_reasons=blocker_reasons,
    )


def _blocker_reasons(
    *,
    coverage_ratio: float,
    coverage_min: float,
    mode: EvidenceMode,
    duplicate_timestamp_count: int,
    zero_volume_count: int,
    stale_segment_count: int,
    outlier_count: int,
    parse_failure_count: int,
) -> tuple[str, ...]:
    if mode == EvidenceMode.SANDBOX_DIAGNOSTIC:
        return ("sandbox_diagnostic_non_evidence",)
    reasons: list[str] = []
    if coverage_ratio < coverage_min:
        reasons.append("coverage_below_minimum")
    if duplicate_timestamp_count:
        reasons.append("duplicate_timestamps")
    if zero_volume_count:
        reasons.append("zero_volume_rows")
    if stale_segment_count:
        reasons.append("stale_segments")
    if outlier_count:
        reasons.append("outliers")
    if parse_failure_count:
        reasons.append("parse_failures")
    return tuple(reasons)
