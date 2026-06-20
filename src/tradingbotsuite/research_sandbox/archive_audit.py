from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from tradingbotsuite.research_sandbox.boundary import (
    SANDBOX_BOUNDARY_FLAGS,
    require_sandbox_boundary,
    sandbox_boundary_metadata,
)
from tradingbotsuite.research_sandbox.identity import digest_payload
from tradingbotsuite.research_sandbox.intake import load_venue_archive_descriptors
from tradingbotsuite.research_sandbox.market_data import (
    SandboxMarketDataCache,
)
from tradingbotsuite.research_sandbox.spec import DataWindow, VenueArchiveDescriptor


ARCHIVE_DESCRIPTOR_AUDIT_JSON_NAME = "archive_descriptor_audit.json"
ARCHIVE_DESCRIPTOR_AUDIT_PARQUET_NAME = "archive_descriptor_audit.parquet"


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


def _container_metadata_row_payload(metadata: dict[str, Any]) -> dict[str, Any]:
    container_metadata = metadata.get("container_member_metadata", {}) or {}
    if not isinstance(container_metadata, dict):
        container_metadata = {}
    selected_sample = container_metadata.get("selected_member_name_sample", [])
    if not isinstance(selected_sample, (list, tuple)):
        selected_sample = []
    suffix_counts = container_metadata.get("available_member_suffix_counts", {})
    if not isinstance(suffix_counts, dict):
        suffix_counts = {}
    return {
        "container_member_metadata": container_metadata,
        "container_kind": container_metadata.get("container_kind"),
        "selected_member_suffix": container_metadata.get("selected_member_suffix"),
        "selected_member_count": int(container_metadata.get("selected_member_count", 0) or 0),
        "selected_member_name_sample": [str(name) for name in selected_sample],
        "selected_member_names_truncated": bool(container_metadata.get("selected_member_names_truncated", False)),
        "available_member_suffix_counts": {str(key): int(value) for key, value in suffix_counts.items()},
        "available_member_suffix_count": int(container_metadata.get("available_member_suffix_count", 0) or 0),
        "loadable_member_count": int(container_metadata.get("loadable_member_count", 0) or 0),
    }


def _frame_window(frame: pd.DataFrame, descriptor: VenueArchiveDescriptor) -> pd.DataFrame:
    timestamps = pd.to_datetime(frame["timestamp"], utc=True)
    start = pd.Timestamp(descriptor.window.start, tz="UTC")
    end_exclusive = pd.Timestamp(descriptor.window.end, tz="UTC") + pd.Timedelta(days=1)
    return frame[(timestamps >= start) & (timestamps < end_exclusive)]


def _requested_frame_window(frame: pd.DataFrame, requested_window: DataWindow | None) -> pd.DataFrame | None:
    if requested_window is None:
        return None
    timestamps = pd.to_datetime(frame["timestamp"], utc=True)
    start = pd.Timestamp(requested_window.start, tz="UTC")
    end_exclusive = pd.Timestamp(requested_window.end, tz="UTC") + pd.Timedelta(days=1)
    return frame[(timestamps >= start) & (timestamps < end_exclusive)]


def _bounds(frame: pd.DataFrame) -> tuple[str | None, str | None]:
    if frame.empty or "timestamp" not in frame.columns:
        return None, None
    timestamps = pd.to_datetime(frame["timestamp"], utc=True)
    return timestamps.min().isoformat(), timestamps.max().isoformat()


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


def _source_path(descriptor: VenueArchiveDescriptor, shared_market_data_path: str | Path | None) -> Path | None:
    if shared_market_data_path is not None:
        return Path(shared_market_data_path)
    return descriptor.data_path


def _audit_descriptor(
    descriptor: VenueArchiveDescriptor,
    *,
    shared_market_data_path: str | Path | None,
    market_data_cache: SandboxMarketDataCache,
    requested_window: DataWindow | None = None,
) -> dict[str, Any]:
    source_path = _source_path(descriptor, shared_market_data_path)
    routing_mode = "shared_market_data_path" if shared_market_data_path is not None else "descriptor_data_path"
    blocker_reasons: list[str] = []
    warning_reasons: list[str] = []
    normalized_row_count = 0
    descriptor_window_row_count = 0
    market_start: str | None = None
    market_end: str | None = None
    window_start: str | None = None
    window_end: str | None = None
    requested_window_row_count: int | None = None
    requested_window_observed_start: str | None = None
    requested_window_observed_end: str | None = None
    columns: list[str] = []
    alias_columns: dict[str, str] = {}
    alias_count = 0
    container_metadata_payload = _container_metadata_row_payload({})
    assigned_binance_kline_columns = False

    if source_path is None:
        blocker_reasons.append("missing_data_path")
    else:
        try:
            source_path = Path(source_path)
            if not source_path.exists():
                blocker_reasons.append("data_path_not_found")
            else:
                if shared_market_data_path is None:
                    source_integrity_errors = market_data_cache.descriptor_source_integrity_errors(
                        descriptor,
                        data_path=source_path,
                    )
                    if source_integrity_errors:
                        blocker_reasons.extend(source_integrity_errors)
                if not blocker_reasons:
                    frame = market_data_cache.load_frame(source_path)
                    columns = [str(column) for column in frame.columns]
                    metadata = dict(frame.attrs.get("sandbox_normalization_metadata") or {})
                    alias_columns = dict(metadata.get("alias_columns") or {})
                    alias_count = int(metadata.get("alias_count", 0) or 0)
                    container_metadata_payload = _container_metadata_row_payload(metadata)
                    assigned_binance_kline_columns = bool(metadata.get("assigned_binance_kline_columns", False))
                    normalized_row_count = int(len(frame))
                    market_start, market_end = _bounds(frame)
                    window_frame = _frame_window(frame, descriptor)
                    descriptor_window_row_count = int(len(window_frame))
                    window_start, window_end = _bounds(window_frame)
                    requested_frame = _requested_frame_window(frame, requested_window)
                    if requested_frame is not None:
                        requested_window_row_count = int(len(requested_frame))
                        requested_window_observed_start, requested_window_observed_end = _bounds(requested_frame)
                    if normalized_row_count == 0:
                        blocker_reasons.append("no_normalized_2024_plus_rows")
                    elif descriptor_window_row_count == 0:
                        blocker_reasons.append("no_rows_in_descriptor_window")
                    if requested_frame is not None and requested_window_row_count == 0:
                        blocker_reasons.append("no_rows_in_requested_window")
                    for column in ("high", "low"):
                        if column not in frame.columns:
                            warning_reasons.append(f"missing_ohlc_column:{column}")
        except Exception as exc:  # noqa: BLE001 - audit should report loader failures as blockers.
            blocker_reasons.append(f"load_error:{type(exc).__name__}:{exc}")

    status = "blocked" if blocker_reasons else "ready"
    row = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_archive_descriptor_audit_row",
        **_requested_window_payload(requested_window),
        "descriptor_id": descriptor.descriptor_id,
        "venue": descriptor.venue,
        "symbol": descriptor.symbol,
        "data_family": descriptor.data_family,
        "interval": descriptor.interval,
        "routing_mode": routing_mode,
        "source_path": str(source_path) if source_path is not None else None,
        "manifest_path": str(descriptor.manifest_path) if descriptor.manifest_path is not None else None,
        "diagnostic_only": descriptor.diagnostic_only,
        "source_access_mode": descriptor.source_access_mode,
        "checksum_policy": descriptor.checksum_policy,
        "window": descriptor.window.to_payload(),
        "normalized_row_count": normalized_row_count,
        "descriptor_window_row_count": descriptor_window_row_count,
        "requested_window_row_count": requested_window_row_count,
        "market_start": market_start,
        "market_end": market_end,
        "window_start": window_start,
        "window_end": window_end,
        "requested_window_observed_start": requested_window_observed_start,
        "requested_window_observed_end": requested_window_observed_end,
        "columns": columns,
        "alias_columns": alias_columns,
        "alias_count": alias_count,
        **container_metadata_payload,
        "assigned_binance_kline_columns": assigned_binance_kline_columns,
        "has_high_low": "high" in columns and "low" in columns,
        "status": status,
        "blocker_reasons": blocker_reasons,
        "warning_reasons": warning_reasons,
    }
    require_sandbox_boundary(row, payload_name="sandbox_archive_descriptor_audit_row")
    return row


def audit_sandbox_archive_descriptors(
    venue_archives_path: str | Path,
    *,
    output_dir: str | Path,
    shared_market_data_path: str | Path | None = None,
    requested_window: DataWindow | None = None,
    market_data_cache: SandboxMarketDataCache | None = None,
) -> dict[str, Any]:
    descriptor_path = Path(venue_archives_path)
    descriptors = load_venue_archive_descriptors(descriptor_path)
    if not descriptors:
        raise ValueError("sandbox archive descriptor audit requires at least one descriptor")
    cache = market_data_cache or SandboxMarketDataCache()
    rows = [
        _audit_descriptor(
            descriptor,
            shared_market_data_path=shared_market_data_path,
            market_data_cache=cache,
            requested_window=requested_window,
        )
        for descriptor in descriptors
    ]
    status_counts: dict[str, int] = {}
    venue_counts: dict[str, int] = {}
    for row in rows:
        status = str(row["status"])
        venue = str(row["venue"])
        status_counts[status] = status_counts.get(status, 0) + 1
        venue_counts[venue] = venue_counts.get(venue, 0) + 1

    audit_id = digest_payload(
        {
            "descriptor_path": str(descriptor_path),
            "shared_market_data_path": str(shared_market_data_path) if shared_market_data_path is not None else None,
            "requested_window": _requested_window_payload(requested_window),
            "descriptor_ids": [descriptor.descriptor_id for descriptor in descriptors],
        },
        prefix="sbxarchiveaudit",
        length=24,
    )
    destination = Path(output_dir) / audit_id
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / ARCHIVE_DESCRIPTOR_AUDIT_JSON_NAME
    parquet_path = destination / ARCHIVE_DESCRIPTOR_AUDIT_PARQUET_NAME

    frame = pd.DataFrame([_row_for_parquet(row) for row in rows])
    if frame.empty:
        frame = pd.DataFrame(columns=["descriptor_id", "status", *SANDBOX_BOUNDARY_FLAGS])
    frame.to_parquet(parquet_path, index=False)
    payload = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_archive_descriptor_audit",
        "audit_id": audit_id,
        "venue_archives_path": str(descriptor_path),
        "shared_market_data_path": str(shared_market_data_path) if shared_market_data_path is not None else None,
        **_requested_window_payload(requested_window),
        "audit_dir": str(destination),
        "audit_json_path": str(json_path),
        "audit_parquet_path": str(parquet_path),
        "descriptor_count": len(rows),
        "ready_count": int(status_counts.get("ready", 0)),
        "blocked_count": int(status_counts.get("blocked", 0)),
        "requested_window_row_count": sum(int(row.get("requested_window_row_count", 0) or 0) for row in rows),
        "status_counts": dict(sorted(status_counts.items())),
        "venue_counts": dict(sorted(venue_counts.items())),
        "descriptors": rows,
    }
    require_sandbox_boundary(payload, payload_name="sandbox_archive_descriptor_audit")
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    return payload
