# V2-AUDIT-ID: V2-AUD-QUAL-001
# V2-CONTRACTS: docs/contracts/data_quality_contract.md
# V2-BOUNDARY: research_only, data_quality_checks, no_live_imports
# V2-OWNER: v2_data_quality
"""Data-quality check helpers for v2 market-data rows."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Any

from tradingbotsuite.v2.archive.hashing import canonical_json_hash
from tradingbotsuite.v2.config.time import ensure_utc, utc_isoformat
from tradingbotsuite.v2.data_quality.schemas import (
    DataQualityCheck,
    EvidenceMode,
    QualityStatus,
)


def build_quality_checks(
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
    stale_min_run_length: int = 3,
    max_abs_return: float = 0.5,
    max_spread: float = 0.1,
    max_abs_funding: float = 0.1,
    evidence_mode: EvidenceMode = EvidenceMode.ACCEPTED_RESEARCH,
) -> list[DataQualityCheck]:
    mode = EvidenceMode(evidence_mode)
    materialized = list(rows)
    start = ensure_utc(start_ts)
    end = ensure_utc(end_ts)
    parsed_rows = [
        item for item in _parse_rows(materialized, ts_field=ts_field) if start <= item[0] < end
    ]
    return [
        _quality_check(
            venue=venue,
            instrument_id=instrument_id,
            family=family,
            timeframe=timeframe,
            start_ts=start,
            end_ts=end,
            check_type="duplicate_timestamps",
            affected_timestamps=detect_duplicate_timestamps(parsed_rows),
            evidence_mode=mode,
        ),
        _quality_check(
            venue=venue,
            instrument_id=instrument_id,
            family=family,
            timeframe=timeframe,
            start_ts=start,
            end_ts=end,
            check_type="zero_volume",
            affected_timestamps=detect_zero_volume(parsed_rows, volume_field=volume_field),
            evidence_mode=mode,
        ),
        _quality_check(
            venue=venue,
            instrument_id=instrument_id,
            family=family,
            timeframe=timeframe,
            start_ts=start,
            end_ts=end,
            check_type="stale_segments",
            affected_timestamps=detect_stale_segments(
                parsed_rows,
                value_field=price_field,
                min_run_length=stale_min_run_length,
            ),
            evidence_mode=mode,
        ),
        _quality_check(
            venue=venue,
            instrument_id=instrument_id,
            family=family,
            timeframe=timeframe,
            start_ts=start,
            end_ts=end,
            check_type="return_outliers",
            affected_timestamps=detect_return_outliers(
                parsed_rows,
                price_field=price_field,
                max_abs_return=max_abs_return,
            ),
            evidence_mode=mode,
        ),
        _quality_check(
            venue=venue,
            instrument_id=instrument_id,
            family=family,
            timeframe=timeframe,
            start_ts=start,
            end_ts=end,
            check_type="spread_outliers",
            affected_timestamps=detect_spread_outliers(
                parsed_rows,
                spread_field=spread_field,
                max_spread=max_spread,
            ),
            evidence_mode=mode,
        ),
        _quality_check(
            venue=venue,
            instrument_id=instrument_id,
            family=family,
            timeframe=timeframe,
            start_ts=start,
            end_ts=end,
            check_type="funding_outliers",
            affected_timestamps=detect_funding_outliers(
                parsed_rows,
                funding_field=funding_field,
                max_abs_funding=max_abs_funding,
            ),
            evidence_mode=mode,
        ),
    ]


def detect_duplicate_timestamps(parsed_rows: Iterable[tuple[datetime, Mapping[str, Any]]]) -> list[datetime]:
    counts = Counter(ts for ts, _row in parsed_rows)
    return sorted(ts for ts, count in counts.items() if count > 1)


def detect_zero_volume(
    parsed_rows: Iterable[tuple[datetime, Mapping[str, Any]]],
    *,
    volume_field: str = "volume",
) -> list[datetime]:
    affected: list[datetime] = []
    for ts, row in parsed_rows:
        value = _optional_float(row.get(volume_field))
        if value == 0.0:
            affected.append(ts)
    return affected


def detect_stale_segments(
    parsed_rows: Iterable[tuple[datetime, Mapping[str, Any]]],
    *,
    value_field: str = "close",
    min_run_length: int = 3,
) -> list[datetime]:
    if min_run_length < 2:
        raise ValueError("min_run_length must be >= 2")
    sorted_rows = sorted(parsed_rows, key=lambda item: item[0])
    affected: list[datetime] = []
    current_value: float | str | None = None
    current_run: list[datetime] = []
    for ts, row in sorted_rows:
        raw_value = row.get(value_field)
        if raw_value is None:
            current_value = None
            current_run = []
            continue
        value = str(raw_value)
        if value == current_value:
            current_run.append(ts)
        else:
            if len(current_run) >= min_run_length:
                affected.append(current_run[0])
            current_value = value
            current_run = [ts]
    if len(current_run) >= min_run_length:
        affected.append(current_run[0])
    return affected


def detect_return_outliers(
    parsed_rows: Iterable[tuple[datetime, Mapping[str, Any]]],
    *,
    price_field: str = "close",
    max_abs_return: float = 0.5,
) -> list[datetime]:
    if max_abs_return <= 0:
        raise ValueError("max_abs_return must be positive")
    sorted_rows = sorted(parsed_rows, key=lambda item: item[0])
    affected: list[datetime] = []
    previous_price: float | None = None
    for ts, row in sorted_rows:
        price = _optional_float(row.get(price_field))
        if price is None or price <= 0:
            previous_price = price
            continue
        if previous_price is not None and previous_price > 0:
            realized_return = (price / previous_price) - 1.0
            if abs(realized_return) > max_abs_return:
                affected.append(ts)
        previous_price = price
    return affected


def detect_spread_outliers(
    parsed_rows: Iterable[tuple[datetime, Mapping[str, Any]]],
    *,
    spread_field: str = "spread",
    max_spread: float = 0.1,
) -> list[datetime]:
    if max_spread < 0:
        raise ValueError("max_spread must be non-negative")
    affected: list[datetime] = []
    for ts, row in parsed_rows:
        spread = _optional_float(row.get(spread_field))
        if spread is not None and spread > max_spread:
            affected.append(ts)
    return affected


def detect_funding_outliers(
    parsed_rows: Iterable[tuple[datetime, Mapping[str, Any]]],
    *,
    funding_field: str = "funding",
    max_abs_funding: float = 0.1,
) -> list[datetime]:
    if max_abs_funding < 0:
        raise ValueError("max_abs_funding must be non-negative")
    affected: list[datetime] = []
    for ts, row in parsed_rows:
        funding = _optional_float(row.get(funding_field))
        if funding is not None and abs(funding) > max_abs_funding:
            affected.append(ts)
    return affected


def parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return ensure_utc(value)
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        return ensure_utc(datetime.fromisoformat(normalized))
    raise ValueError(f"unsupported timestamp value: {value!r}")


def _parse_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    ts_field: str,
) -> list[tuple[datetime, Mapping[str, Any]]]:
    parsed: list[tuple[datetime, Mapping[str, Any]]] = []
    for row in rows:
        try:
            parsed.append((parse_timestamp(row[ts_field]), row))
        except (KeyError, TypeError, ValueError):
            continue
    return parsed


def _quality_check(
    *,
    venue: str,
    instrument_id: str,
    family: str,
    timeframe: str,
    start_ts: datetime,
    end_ts: datetime,
    check_type: str,
    affected_timestamps: list[datetime],
    evidence_mode: EvidenceMode,
) -> DataQualityCheck:
    affected_sample = tuple(utc_isoformat(ts) for ts in affected_timestamps[:50])
    status = (
        QualityStatus.NON_EVIDENCE
        if evidence_mode == EvidenceMode.SANDBOX_DIAGNOSTIC
        else QualityStatus.FAIL
        if affected_timestamps
        else QualityStatus.PASS
    )
    identity = {
        "venue": venue,
        "instrument_id": instrument_id,
        "family": family,
        "timeframe": timeframe,
        "start_ts": utc_isoformat(start_ts),
        "end_ts": utc_isoformat(end_ts),
        "check_type": check_type,
        "affected_timestamps_sample": affected_sample,
        "affected_count": len(affected_timestamps),
        "evidence_mode": evidence_mode.value,
    }
    return DataQualityCheck(
        check_id=canonical_json_hash(identity),
        venue=venue,
        instrument_id=instrument_id,
        family=family,
        timeframe=timeframe,
        start_ts=start_ts,
        end_ts=end_ts,
        check_type=check_type,
        status=status,
        affected_count=len(affected_timestamps),
        affected_timestamps_sample=affected_sample,
        severity="non_evidence" if status == QualityStatus.NON_EVIDENCE else "blocker",
        details={"sample_limit": "50"},
        evidence_mode=evidence_mode,
    )


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
