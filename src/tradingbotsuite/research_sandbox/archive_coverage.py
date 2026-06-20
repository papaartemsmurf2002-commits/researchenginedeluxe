from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from tradingbotsuite.research_sandbox.archive_audit import audit_sandbox_archive_descriptors
from tradingbotsuite.research_sandbox.boundary import (
    SANDBOX_BOUNDARY_FLAGS,
    require_sandbox_boundary,
    sandbox_boundary_metadata,
)
from tradingbotsuite.research_sandbox.identity import digest_payload
from tradingbotsuite.research_sandbox.market_data import SandboxMarketDataCache
from tradingbotsuite.research_sandbox.spec import DataWindow


ARCHIVE_COVERAGE_MATRIX_JSON_NAME = "archive_coverage_matrix.json"
ARCHIVE_COVERAGE_MATRIX_PARQUET_NAME = "archive_coverage_matrix.parquet"
ARCHIVE_COVERAGE_VENUE_EXPANSION_GAPS_PARQUET_NAME = "archive_coverage_venue_expansion_gaps.parquet"
CONTAINER_MEMBER_NAME_SAMPLE_LIMIT = 12
VENUE_EXPANSION_TARGET_VENUES = ("okx", "bybit", "hyperliquid")
VENUE_EXPANSION_GAP_PARQUET_COLUMNS = [
    "artifact_family",
    "gap_rank",
    "market_symbol_key",
    "data_family",
    "interval",
    "target_venue",
    "target_bucket_key",
    "target_venue_observed",
    "target_missing",
    "target_status",
    "target_action",
    "observed_symbols",
    "source_coverage_key",
    "descriptor_count",
    "ready_descriptor_count",
    "blocked_descriptor_count",
    "ready_window_row_count",
    "ready_requested_window_row_count",
    "requested_window_filter_applied",
    "requested_window_start",
    "requested_window_end",
    "observed_window_start",
    "observed_window_end",
    "source_paths",
    "manifest_paths",
    "blocker_reason_counts",
    *SANDBOX_BOUNDARY_FLAGS,
]


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _row_for_parquet(payload: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, (dict, list, tuple)):
            row[key] = json.dumps(value, sort_keys=True, default=_json_default)
        else:
            row[key] = value
    return row


def _string_values(rows: list[dict[str, Any]], key: str) -> list[str]:
    values: list[str] = []
    for row in rows:
        value = row.get(key)
        if value is None or value == "":
            continue
        text = str(value)
        if text not in values:
            values.append(text)
    return sorted(values)


def _bound(rows: list[dict[str, Any]], key: str, *, side: str) -> str | None:
    values = _string_values(rows, key)
    if not values:
        return None
    return values[0] if side == "min" else values[-1]


def _reason_counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        reasons = row.get(key)
        if not isinstance(reasons, list):
            continue
        for reason in reasons:
            reason_key = str(reason)
            counts[reason_key] = counts.get(reason_key, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _sum_mapping_counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        values = row.get(key)
        if not isinstance(values, dict):
            continue
        for name, value in values.items():
            counts[str(name)] = counts.get(str(name), 0) + int(value or 0)
    return dict(sorted(counts.items()))


def _selected_member_suffix_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        suffix = row.get("selected_member_suffix")
        if suffix is None or suffix == "":
            continue
        key = str(suffix)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _container_member_name_sample(rows: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for row in rows:
        sample = row.get("selected_member_name_sample")
        if not isinstance(sample, list):
            continue
        for name in sample:
            text = str(name)
            if text not in names:
                names.append(text)
            if len(names) >= CONTAINER_MEMBER_NAME_SAMPLE_LIMIT:
                return names
    return names


def _window_bound(rows: list[dict[str, Any]], key: str, *, side: str) -> str | None:
    values: list[str] = []
    for row in rows:
        window = row.get("window")
        if not isinstance(window, dict):
            continue
        value = window.get(key)
        if value is not None and value != "":
            values.append(str(value))
    values = sorted(set(values))
    if not values:
        return None
    return values[0] if side == "min" else values[-1]


def _requested_window_payload(requested_window: DataWindow | None) -> dict[str, Any]:
    if requested_window is None:
        return {
            "requested_window_filter_applied": False,
            "requested_window_start": None,
            "requested_window_end": None,
        }
    return {
        "requested_window_filter_applied": True,
        "requested_window_start": requested_window.start.isoformat(),
        "requested_window_end": requested_window.end.isoformat(),
    }


def _market_symbol_key(symbol: Any) -> str:
    text = str(symbol or "").upper()
    compact = "".join(char for char in text if char.isalnum())
    for suffix in ("USDTSWAP", "USDCSWAP", "USDSWAP", "USDT", "USDC", "USD", "PERP", "SWAP"):
        if compact.endswith(suffix) and len(compact) > len(suffix):
            compact = compact[: -len(suffix)]
            break
    return compact or "missing"


def _bucket_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(row.get("venue") or "missing"),
        str(row.get("symbol") or "missing"),
        str(row.get("data_family") or "missing"),
        str(row.get("interval") or "na"),
    )


def _coverage_row(*, audit_id: str, bucket_rows: list[dict[str, Any]]) -> dict[str, Any]:
    venue, symbol, data_family, interval = _bucket_key(bucket_rows[0])
    ready_rows = [row for row in bucket_rows if row.get("status") == "ready"]
    blocked_rows = [row for row in bucket_rows if row.get("status") == "blocked"]
    descriptor_ids = _string_values(bucket_rows, "descriptor_id")
    ready_descriptor_ids = _string_values(ready_rows, "descriptor_id")
    blocked_descriptor_ids = _string_values(blocked_rows, "descriptor_id")
    container_rows = [row for row in bucket_rows if row.get("container_kind")]
    ready_container_rows = [row for row in ready_rows if row.get("container_kind")]
    row = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_archive_coverage_row",
        "audit_id": audit_id,
        "coverage_key": "|".join((venue, symbol, data_family, interval)),
        "venue": venue,
        "symbol": symbol,
        "data_family": data_family,
        "interval": None if interval == "na" else interval,
        "descriptor_count": len(bucket_rows),
        "ready_descriptor_count": len(ready_rows),
        "blocked_descriptor_count": len(blocked_rows),
        "status": "ready" if ready_rows and not blocked_rows else "blocked" if blocked_rows and not ready_rows else "mixed",
        "descriptor_ids": descriptor_ids,
        "ready_descriptor_ids": ready_descriptor_ids,
        "blocked_descriptor_ids": blocked_descriptor_ids,
        "source_paths": _string_values(bucket_rows, "source_path"),
        "manifest_paths": _string_values(bucket_rows, "manifest_path"),
        "routing_modes": _string_values(bucket_rows, "routing_mode"),
        "normalized_row_count": sum(int(row.get("normalized_row_count", 0) or 0) for row in bucket_rows),
        "descriptor_window_row_count": sum(int(row.get("descriptor_window_row_count", 0) or 0) for row in bucket_rows),
        "ready_window_row_count": sum(int(row.get("descriptor_window_row_count", 0) or 0) for row in ready_rows),
        "requested_window_filter_applied": any(bool(row.get("requested_window_filter_applied", False)) for row in bucket_rows),
        "requested_window_start": _bound(bucket_rows, "requested_window_start", side="min"),
        "requested_window_end": _bound(bucket_rows, "requested_window_end", side="max"),
        "requested_window_row_count": sum(int(row.get("requested_window_row_count", 0) or 0) for row in bucket_rows),
        "ready_requested_window_row_count": sum(int(row.get("requested_window_row_count", 0) or 0) for row in ready_rows),
        "market_start": _bound(bucket_rows, "market_start", side="min"),
        "market_end": _bound(bucket_rows, "market_end", side="max"),
        "observed_window_start": _bound(bucket_rows, "window_start", side="min"),
        "observed_window_end": _bound(bucket_rows, "window_end", side="max"),
        "requested_window_observed_start": _bound(bucket_rows, "requested_window_observed_start", side="min"),
        "requested_window_observed_end": _bound(bucket_rows, "requested_window_observed_end", side="max"),
        "declared_window_start": _window_bound(bucket_rows, "start", side="min"),
        "declared_window_end": _window_bound(bucket_rows, "end", side="max"),
        "has_any_high_low": any(bool(row.get("has_high_low", False)) for row in bucket_rows),
        "all_ready_have_high_low": bool(ready_rows) and all(bool(row.get("has_high_low", False)) for row in ready_rows),
        "container_kinds": _string_values(container_rows, "container_kind"),
        "selected_member_suffixes": _string_values(container_rows, "selected_member_suffix"),
        "container_descriptor_count": len(container_rows),
        "ready_container_descriptor_count": len(ready_container_rows),
        "selected_member_count": sum(int(row.get("selected_member_count", 0) or 0) for row in container_rows),
        "ready_selected_member_count": sum(int(row.get("selected_member_count", 0) or 0) for row in ready_container_rows),
        "loadable_member_count": sum(int(row.get("loadable_member_count", 0) or 0) for row in container_rows),
        "selected_member_suffix_counts": _selected_member_suffix_counts(container_rows),
        "available_member_suffix_counts": _sum_mapping_counts(container_rows, "available_member_suffix_counts"),
        "selected_member_name_sample": _container_member_name_sample(container_rows),
        "blocker_reason_counts": _reason_counts(bucket_rows, "blocker_reasons"),
        "warning_reason_counts": _reason_counts(bucket_rows, "warning_reasons"),
    }
    require_sandbox_boundary(row, payload_name="sandbox_archive_coverage_row")
    return row


def _coverage_rows(audit: dict[str, Any]) -> list[dict[str, Any]]:
    raw_rows = audit.get("descriptors")
    if not isinstance(raw_rows, list):
        raise ValueError("sandbox archive coverage requires audit descriptors")
    buckets: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for item in raw_rows:
        if not isinstance(item, dict):
            raise ValueError("sandbox archive coverage audit descriptors must be objects")
        require_sandbox_boundary(item, payload_name="sandbox_archive_coverage_audit_row")
        buckets.setdefault(_bucket_key(item), []).append(item)
    rows = [_coverage_row(audit_id=str(audit.get("audit_id")), bucket_rows=bucket_rows) for bucket_rows in buckets.values()]
    return sorted(rows, key=lambda row: (str(row["venue"]), str(row["symbol"]), str(row["data_family"]), str(row["interval"])))


def _venue_expansion_action(status: str) -> str:
    if status == "ready":
        return "use_ready_archive_bucket"
    if status == "mixed":
        return "repair_blocked_descriptors_or_use_ready_bucket"
    if status == "blocked":
        return "repair_blocked_archive_bucket"
    return "add_archive_descriptor_for_target_venue"


def _venue_expansion_gap_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (
            _market_symbol_key(row.get("symbol")),
            str(row.get("data_family") or "missing"),
            str(row.get("interval") or "na"),
        )
        groups.setdefault(key, []).append(row)

    gap_rows: list[dict[str, Any]] = []
    for group_key in sorted(groups):
        group_rows = groups[group_key]
        market_symbol_key, data_family, interval = group_key
        observed_symbols = _string_values(group_rows, "symbol")
        by_venue = {str(row.get("venue")): row for row in group_rows}
        for target_venue in VENUE_EXPANSION_TARGET_VENUES:
            source_row = by_venue.get(target_venue)
            target_missing = source_row is None
            target_status = (
                "missing_archive_descriptor" if target_missing else str(source_row.get("status") or "missing")
            )
            row = {
                **sandbox_boundary_metadata(),
                "artifact_family": "rapid_strategy_iteration_sandbox_archive_coverage_venue_expansion_gap_row",
                "gap_rank": len(gap_rows) + 1,
                "market_symbol_key": market_symbol_key,
                "data_family": data_family,
                "interval": None if interval == "na" else interval,
                "target_venue": target_venue,
                "target_bucket_key": "|".join((target_venue, market_symbol_key, data_family, interval)),
                "target_venue_observed": source_row is not None,
                "target_missing": target_missing,
                "target_status": target_status,
                "target_action": _venue_expansion_action(target_status),
                "observed_symbols": observed_symbols,
                "source_coverage_key": None if source_row is None else source_row.get("coverage_key"),
                "descriptor_count": 0 if source_row is None else int(source_row.get("descriptor_count", 0) or 0),
                "ready_descriptor_count": 0 if source_row is None else int(source_row.get("ready_descriptor_count", 0) or 0),
                "blocked_descriptor_count": 0 if source_row is None else int(source_row.get("blocked_descriptor_count", 0) or 0),
                "ready_window_row_count": 0 if source_row is None else int(source_row.get("ready_window_row_count", 0) or 0),
                "ready_requested_window_row_count": (
                    0
                    if source_row is None
                    else int(source_row.get("ready_requested_window_row_count", 0) or 0)
                ),
                "requested_window_filter_applied": (
                    False if source_row is None else bool(source_row.get("requested_window_filter_applied", False))
                ),
                "requested_window_start": None if source_row is None else source_row.get("requested_window_start"),
                "requested_window_end": None if source_row is None else source_row.get("requested_window_end"),
                "observed_window_start": None if source_row is None else source_row.get("observed_window_start"),
                "observed_window_end": None if source_row is None else source_row.get("observed_window_end"),
                "source_paths": [] if source_row is None else source_row.get("source_paths", []),
                "manifest_paths": [] if source_row is None else source_row.get("manifest_paths", []),
                "blocker_reason_counts": {} if source_row is None else source_row.get("blocker_reason_counts", {}),
            }
            require_sandbox_boundary(row, payload_name="sandbox_archive_coverage_venue_expansion_gap_row")
            gap_rows.append(row)
    return gap_rows


def summarize_sandbox_archive_coverage(
    venue_archives_path: str | Path,
    *,
    output_dir: str | Path,
    shared_market_data_path: str | Path | None = None,
    requested_window: DataWindow | None = None,
    market_data_cache: SandboxMarketDataCache | None = None,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    audit = audit_sandbox_archive_descriptors(
        venue_archives_path,
        output_dir=output_path / "_archive_audit",
        shared_market_data_path=shared_market_data_path,
        requested_window=requested_window,
        market_data_cache=market_data_cache,
    )
    require_sandbox_boundary(audit, payload_name="sandbox_archive_coverage_source_audit")
    rows = _coverage_rows(audit)
    status_counts: dict[str, int] = {}
    venue_counts: dict[str, int] = {}
    for row in rows:
        status = str(row["status"])
        venue = str(row["venue"])
        status_counts[status] = status_counts.get(status, 0) + 1
        venue_counts[venue] = venue_counts.get(venue, 0) + 1
    venue_expansion_gap_rows = _venue_expansion_gap_rows(rows)
    venue_expansion_status_counts: dict[str, int] = {}
    venue_expansion_action_counts: dict[str, int] = {}
    for row in venue_expansion_gap_rows:
        status = str(row["target_status"])
        action = str(row["target_action"])
        venue_expansion_status_counts[status] = venue_expansion_status_counts.get(status, 0) + 1
        venue_expansion_action_counts[action] = venue_expansion_action_counts.get(action, 0) + 1

    coverage_id = digest_payload(
        {
            "venue_archives_path": str(venue_archives_path),
            "shared_market_data_path": str(shared_market_data_path) if shared_market_data_path is not None else None,
            "requested_window": _requested_window_payload(requested_window),
            "audit_id": audit.get("audit_id"),
            "rows": rows,
            "venue_expansion_gap_rows": venue_expansion_gap_rows,
        },
        prefix="sbxarchivecoverage",
        length=24,
    )
    destination = output_path / coverage_id
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / ARCHIVE_COVERAGE_MATRIX_JSON_NAME
    parquet_path = destination / ARCHIVE_COVERAGE_MATRIX_PARQUET_NAME
    venue_expansion_gaps_parquet_path = destination / ARCHIVE_COVERAGE_VENUE_EXPANSION_GAPS_PARQUET_NAME

    frame = pd.DataFrame([_row_for_parquet(row) for row in rows])
    if frame.empty:
        frame = pd.DataFrame(columns=["coverage_key", "venue", "symbol", "status", *SANDBOX_BOUNDARY_FLAGS])
    frame.to_parquet(parquet_path, index=False)
    venue_expansion_gap_frame = pd.DataFrame([_row_for_parquet(row) for row in venue_expansion_gap_rows])
    if venue_expansion_gap_frame.empty:
        venue_expansion_gap_frame = pd.DataFrame(columns=VENUE_EXPANSION_GAP_PARQUET_COLUMNS)
    venue_expansion_gap_frame.to_parquet(venue_expansion_gaps_parquet_path, index=False)

    payload = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_archive_coverage_matrix",
        "coverage_id": coverage_id,
        "venue_archives_path": str(venue_archives_path),
        "shared_market_data_path": str(shared_market_data_path) if shared_market_data_path is not None else None,
        **_requested_window_payload(requested_window),
        "coverage_dir": str(destination),
        "coverage_json_path": str(json_path),
        "coverage_parquet_path": str(parquet_path),
        "venue_expansion_gaps_parquet_path": str(venue_expansion_gaps_parquet_path),
        "source_audit_id": audit.get("audit_id"),
        "source_audit_json_path": audit.get("audit_json_path"),
        "source_audit_parquet_path": audit.get("audit_parquet_path"),
        "descriptor_count": int(audit.get("descriptor_count", 0) or 0),
        "ready_descriptor_count": int(audit.get("ready_count", 0) or 0),
        "blocked_descriptor_count": int(audit.get("blocked_count", 0) or 0),
        "requested_window_row_count": int(audit.get("requested_window_row_count", 0) or 0),
        "coverage_bucket_count": len(rows),
        "ready_bucket_count": int(status_counts.get("ready", 0) or 0),
        "blocked_bucket_count": int(status_counts.get("blocked", 0) or 0),
        "mixed_bucket_count": int(status_counts.get("mixed", 0) or 0),
        "status_counts": dict(sorted(status_counts.items())),
        "venue_counts": dict(sorted(venue_counts.items())),
        "venue_expansion_target_venues": list(VENUE_EXPANSION_TARGET_VENUES),
        "venue_expansion_gap_row_count": len(venue_expansion_gap_rows),
        "venue_expansion_missing_target_count": int(
            venue_expansion_status_counts.get("missing_archive_descriptor", 0) or 0
        ),
        "venue_expansion_ready_target_count": int(venue_expansion_status_counts.get("ready", 0) or 0),
        "venue_expansion_blocked_target_count": int(venue_expansion_status_counts.get("blocked", 0) or 0),
        "venue_expansion_mixed_target_count": int(venue_expansion_status_counts.get("mixed", 0) or 0),
        "venue_expansion_status_counts": dict(sorted(venue_expansion_status_counts.items())),
        "venue_expansion_action_counts": dict(sorted(venue_expansion_action_counts.items())),
        "venue_expansion_gap_rows": venue_expansion_gap_rows,
        "coverage_rows": rows,
    }
    require_sandbox_boundary(payload, payload_name="sandbox_archive_coverage_matrix")
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    return payload
