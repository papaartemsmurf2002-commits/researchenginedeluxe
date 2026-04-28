from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from tradingbotsuite.research.archive_sources import validate_archive_source_manifest

DATA_QUALITY_REPORT_VERSION = "v2-archive-market-data-quality-report-1"

_RECEIVE_FIELD_KEYS = (
    "receive_time_field",
    "local_receive_time_field",
    "ingest_time_field",
    "received_at_field",
)
_RECEIVE_VALUE_KEYS = (
    "receive_time_ms",
    "receive_time_min_ms",
    "receive_time_max_ms",
    "min_receive_time_ms",
    "max_receive_time_ms",
    "last_receive_time_ms",
    "received_at_ms",
)
_EVENT_MAX_KEYS = ("event_time_max_ms", "max_event_time_ms", "last_time_ms", "end_time_ms")


def build_manifest_data_quality_report(
    *manifests: Mapping[str, Any] | Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Return an observe-only data-quality report for manifest dictionaries.

    The function is intentionally pure: it reads no files, makes no network
    calls, and does not touch runtime controls. Inputs may be archive source
    manifests, market-data collector manifests, or append-only journal
    manifests that expose similar metadata fields.
    """

    manifest_list = _coerce_manifest_list(manifests)
    alerts: list[dict[str, Any]] = []
    source_counts: dict[str, int] = {}
    family_counts: dict[str, int] = {}
    symbol_counts: dict[str, int] = {}
    summaries: list[dict[str, Any]] = []
    timestamp_drift_flags: list[dict[str, Any]] = []
    missing_receive_time_flags: list[dict[str, Any]] = []
    stale_receive_time_flags: list[dict[str, Any]] = []

    gap_count_total = 0
    duplicate_count_total = 0
    missing_receive_time_count = 0
    non_promotable_count = 0
    source_mismatch_count = 0
    missing_research_only_count = 0
    zero_row_manifest_count = 0

    for index, manifest in enumerate(manifest_list):
        source = _source_name(manifest)
        family = _family_name(manifest)
        symbol = _symbol_name(manifest)
        _increment(source_counts, source)
        _increment(family_counts, family)
        _increment(symbol_counts, symbol)

        gap_count = _manifest_count(manifest, "gap_count", "gaps")
        duplicate_count = _manifest_count(manifest, "duplicate_count", "duplicates")
        gap_count_total += gap_count
        duplicate_count_total += duplicate_count

        row_count = _int_or_none(manifest.get("row_count"))
        zero_row = row_count == 0
        if zero_row:
            zero_row_manifest_count += 1

        research_only = manifest.get("research_only") is True
        if not research_only:
            missing_research_only_count += 1

        receive_time_available = _has_receive_time(manifest)
        if not receive_time_available:
            missing_receive_time_count += 1
            missing_receive_time_flags.append(
                {
                    "manifest_index": index,
                    "source": source,
                    "symbol": symbol,
                    "reason": "receive_time_field_missing",
                }
            )

        source_mismatch = _has_source_mismatch(manifest)
        archive_errors: tuple[str, ...] = ()
        archive_quality_flags: tuple[str, ...] = ()
        archive_diagnostic_only = False
        archive_promotable: bool | None = None
        if "source_name" in manifest or "data_family" in manifest:
            validation = validate_archive_source_manifest(manifest)
            archive_errors = validation.errors
            archive_quality_flags = validation.quality_flags
            archive_diagnostic_only = validation.diagnostic_only
            archive_promotable = validation.promotable
            source_mismatch = source_mismatch or "source_mismatch" in validation.quality_flags

        if source_mismatch:
            source_mismatch_count += 1

        timestamp_drift_flags.extend(_timestamp_drift_flags(index, manifest, source, symbol))
        stale_receive_time_flags.extend(_stale_receive_time_flags(index, manifest, source, symbol))

        non_promotable = _is_non_promotable_manifest(
            manifest,
            archive_promotable=archive_promotable,
            archive_diagnostic_only=archive_diagnostic_only,
            archive_errors=archive_errors,
            receive_time_available=receive_time_available,
            research_only=research_only,
            source_mismatch=source_mismatch,
            zero_row=zero_row,
        )
        if non_promotable:
            non_promotable_count += 1

        summaries.append(
            {
                "manifest_index": index,
                "source": source,
                "family": family,
                "symbol": symbol,
                "row_count": row_count,
                "research_only": research_only,
                "receive_time_available": receive_time_available,
                "promotable": False if non_promotable else bool(manifest.get("promotable", False)),
                "non_promotable": non_promotable,
                "gap_count": gap_count,
                "duplicate_count": duplicate_count,
                "source_mismatch": source_mismatch,
                "archive_validation_errors": list(archive_errors),
                "archive_quality_flags": list(archive_quality_flags),
            }
        )

    if missing_receive_time_count:
        _append_alert(
            alerts,
            code="missing_receive_time",
            severity="warn",
            message="One or more manifests do not expose receive-time metadata.",
            details={"manifest_count": missing_receive_time_count, "flags": missing_receive_time_flags},
        )
    if gap_count_total:
        _append_alert(
            alerts,
            code="gaps_detected",
            severity="warn",
            message="One or more manifests report timestamp gaps.",
            details={"gap_count_total": gap_count_total},
        )
    if duplicate_count_total:
        _append_alert(
            alerts,
            code="duplicates_detected",
            severity="warn",
            message="One or more manifests report duplicate timestamps or rows.",
            details={"duplicate_count_total": duplicate_count_total},
        )
    if source_mismatch_count:
        _append_alert(
            alerts,
            code="source_mismatch",
            severity="warn",
            message="One or more manifests report provider/source mismatch.",
            details={"manifest_count": source_mismatch_count},
        )
    if non_promotable_count:
        _append_alert(
            alerts,
            code="non_promotable_source",
            severity="info",
            message="One or more input manifests are diagnostic or non-promotable.",
            details={"manifest_count": non_promotable_count},
        )
    if missing_research_only_count:
        _append_alert(
            alerts,
            code="missing_research_only",
            severity="warn",
            message="One or more manifests are missing research_only: true.",
            details={"manifest_count": missing_research_only_count},
        )
    if zero_row_manifest_count:
        _append_alert(
            alerts,
            code="zero_row_manifest",
            severity="warn",
            message="One or more manifests report zero rows.",
            details={"manifest_count": zero_row_manifest_count},
        )
    if timestamp_drift_flags:
        _append_alert(
            alerts,
            code="timestamp_drift",
            severity="warn",
            message="One or more manifests contain inconsistent timestamp bounds.",
            details={"flag_count": len(timestamp_drift_flags), "flags": timestamp_drift_flags},
        )
    if stale_receive_time_flags:
        _append_alert(
            alerts,
            code="stale_receive_time",
            severity="warn",
            message="One or more manifests contain receive times older than event times.",
            details={"flag_count": len(stale_receive_time_flags), "flags": stale_receive_time_flags},
        )

    return {
        "data_quality_report_version": DATA_QUALITY_REPORT_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "manifest_count": len(manifest_list),
        "source_counts": dict(sorted(source_counts.items())),
        "family_counts": dict(sorted(family_counts.items())),
        "symbol_counts": dict(sorted(symbol_counts.items())),
        "gap_count_total": gap_count_total,
        "duplicate_count_total": duplicate_count_total,
        "missing_receive_time_count": missing_receive_time_count,
        "non_promotable_count": non_promotable_count,
        "source_mismatch_count": source_mismatch_count,
        "missing_research_only_count": missing_research_only_count,
        "zero_row_manifest_count": zero_row_manifest_count,
        "timestamp_drift_flags": timestamp_drift_flags,
        "missing_receive_time_flags": missing_receive_time_flags,
        "stale_receive_time_flags": stale_receive_time_flags,
        "alerts": alerts,
        "manifest_summaries": summaries,
    }


def _coerce_manifest_list(
    manifests: tuple[Mapping[str, Any] | Iterable[Mapping[str, Any]], ...],
) -> list[Mapping[str, Any]]:
    if len(manifests) == 1:
        only = manifests[0]
        if isinstance(only, Mapping):
            return [only]
        result = list(only)
        if not all(isinstance(item, Mapping) for item in result):
            raise TypeError("manifests must be mappings")
        if not result:
            raise ValueError("at least one manifest is required")
        return result
    result = list(manifests)
    if not all(isinstance(item, Mapping) for item in result):
        raise TypeError("manifests must be mappings")
    if not result:
        raise ValueError("at least one manifest is required")
    return result


def _source_name(manifest: Mapping[str, Any]) -> str:
    return _non_empty_str(
        manifest.get("source_name")
        or manifest.get("source")
        or manifest.get("journal_source")
        or manifest.get("provider")
        or "missing"
    )


def _family_name(manifest: Mapping[str, Any]) -> str:
    raw = manifest.get("data_family") or manifest.get("family") or manifest.get("journal_family")
    if raw:
        return _non_empty_str(raw)
    if manifest.get("source") == "binance_usdm_klines" or manifest.get("interval"):
        return "kline"
    return "missing"


def _symbol_name(manifest: Mapping[str, Any]) -> str:
    return _non_empty_str(manifest.get("symbol") or manifest.get("asset") or "missing")


def _non_empty_str(value: Any) -> str:
    text = str(value).strip()
    return text if text else "missing"


def _increment(counts: dict[str, int], key: str) -> None:
    counts[key] = counts.get(key, 0) + 1


def _manifest_count(manifest: Mapping[str, Any], count_key: str, list_key: str) -> int:
    count = _int_or_none(manifest.get(count_key))
    if count is not None:
        return max(count, 0)
    raw_items = manifest.get(list_key)
    if isinstance(raw_items, (list, tuple)):
        return len(raw_items)
    return 0


def _has_receive_time(manifest: Mapping[str, Any]) -> bool:
    for key in _RECEIVE_FIELD_KEYS:
        if _optional_str(manifest.get(key)):
            return True
    return any(_int_or_none(manifest.get(key)) is not None for key in _RECEIVE_VALUE_KEYS)


def _has_source_mismatch(manifest: Mapping[str, Any]) -> bool:
    if bool(manifest.get("source_mismatch")) or _optional_str(manifest.get("source_mismatch_reason")):
        return True
    provider_symbol = _optional_str(manifest.get("provider_symbol"))
    symbol = _optional_str(manifest.get("symbol"))
    return bool(provider_symbol and symbol and provider_symbol != symbol)


def _is_non_promotable_manifest(
    manifest: Mapping[str, Any],
    *,
    archive_promotable: bool | None,
    archive_diagnostic_only: bool,
    archive_errors: tuple[str, ...],
    receive_time_available: bool,
    research_only: bool,
    source_mismatch: bool,
    zero_row: bool,
) -> bool:
    if archive_promotable is False or archive_diagnostic_only or archive_errors:
        return True
    if manifest.get("promotable") is False or manifest.get("promotion_ready") is False:
        return True
    if manifest.get("non_promotable") is True or manifest.get("diagnostic_only") is True:
        return True
    return not research_only or not receive_time_available or source_mismatch or zero_row


def _timestamp_drift_flags(
    manifest_index: int,
    manifest: Mapping[str, Any],
    source: str,
    symbol: str,
) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    start_time = _int_or_none(manifest.get("start_time_ms"))
    end_time = _int_or_none(manifest.get("end_time_ms"))
    if start_time is not None and end_time is not None and start_time > end_time:
        flags.append(_flag(manifest_index, source, symbol, "start_time_after_end_time", "start_time_ms", "end_time_ms"))

    first_time = _first_numeric(manifest, ("first_time_ms", "event_time_min_ms", "min_event_time_ms"))
    last_time = _first_numeric(manifest, ("last_time_ms", "event_time_max_ms", "max_event_time_ms"))
    if first_time is not None and start_time is not None and first_time < start_time:
        flags.append(_flag(manifest_index, source, symbol, "first_time_before_start_time", "first_time_ms", "start_time_ms"))
    if last_time is not None and end_time is not None and last_time > end_time:
        flags.append(_flag(manifest_index, source, symbol, "last_time_after_end_time", "last_time_ms", "end_time_ms"))
    if first_time is not None and last_time is not None and first_time > last_time:
        flags.append(_flag(manifest_index, source, symbol, "first_time_after_last_time", "first_time_ms", "last_time_ms"))
    return flags


def _stale_receive_time_flags(
    manifest_index: int,
    manifest: Mapping[str, Any],
    source: str,
    symbol: str,
) -> list[dict[str, Any]]:
    if bool(manifest.get("stale_receive_time")) or bool(manifest.get("receive_time_stale")):
        return [_flag(manifest_index, source, symbol, "stale_receive_time", "receive_time", "event_time")]

    event_max = _first_numeric(manifest, _EVENT_MAX_KEYS)
    receive_max = _first_numeric(manifest, ("receive_time_max_ms", "max_receive_time_ms", "last_receive_time_ms"))
    if event_max is None or receive_max is None or receive_max >= event_max:
        return []
    return [_flag(manifest_index, source, symbol, "receive_time_before_event_time", "receive_time_max_ms", "event_time_max_ms")]


def _flag(
    manifest_index: int,
    source: str,
    symbol: str,
    code: str,
    field: str,
    reference_field: str,
) -> dict[str, Any]:
    return {
        "manifest_index": manifest_index,
        "source": source,
        "symbol": symbol,
        "code": code,
        "field": field,
        "reference_field": reference_field,
    }


def _first_numeric(manifest: Mapping[str, Any], keys: tuple[str, ...]) -> int | None:
    for key in keys:
        value = _int_or_none(manifest.get(key))
        if value is not None:
            return value
    return None


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _append_alert(
    alerts: list[dict[str, Any]],
    *,
    severity: str,
    code: str,
    message: str,
    details: dict[str, Any],
) -> None:
    alerts.append({"severity": severity, "code": code, "message": message, "observe_only": True, "details": details})
