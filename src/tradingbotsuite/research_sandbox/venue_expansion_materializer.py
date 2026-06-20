from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from tradingbotsuite.research_sandbox.archive_manifest import (
    ARCHIVE_MANIFEST_JSON_NAME,
    SUPPORTED_ARCHIVE_SUFFIXES,
    _bounds,
    _file_integrity,
    _infer_data_family,
    _infer_interval,
    _infer_symbol,
    _infer_venue,
    _iter_files,
    _overlaps_requested_window,
    _source_suffix,
)
from tradingbotsuite.research_sandbox.boundary import (
    SANDBOX_BOUNDARY_FLAGS,
    require_sandbox_boundary,
    sandbox_boundary_metadata,
)
from tradingbotsuite.research_sandbox.identity import digest_payload
from tradingbotsuite.research_sandbox.market_data import load_market_frame
from tradingbotsuite.research_sandbox.spec import (
    ALLOWED_DATA_FAMILIES,
    DataWindow,
    VenueArchiveDescriptor,
    canonical_venue,
)


VENUE_EXPANSION_DESCRIPTOR_CANDIDATES_JSON_NAME = (
    "sandbox_venue_expansion_descriptor_candidates.json"
)
VENUE_EXPANSION_DESCRIPTOR_CANDIDATES_PARQUET_NAME = (
    "sandbox_venue_expansion_descriptor_candidates.parquet"
)
VENUE_EXPANSION_MANIFEST_PATCH_DRY_RUN_JSON_NAME = (
    "sandbox_venue_expansion_manifest_patch_dry_run.json"
)
VENUE_EXPANSION_MANIFEST_PATCH_DRY_RUN_PARQUET_NAME = (
    "sandbox_venue_expansion_manifest_patch_dry_run.parquet"
)
VENUE_EXPANSION_MATERIALIZER_MINIMUM_WINDOW_START = "2024-01-01"
VENUE_EXPANSION_MATERIALIZER_EXECUTION_MODE = (
    "descriptor_candidate_manifest_patch_dry_run_no_execution"
)
VENUE_EXPANSION_CANDIDATE_MANIFEST_REPORT_JSON_NAME = (
    "sandbox_venue_expansion_candidate_manifest_report.json"
)
VENUE_EXPANSION_CANDIDATE_MANIFEST_REPORT_PARQUET_NAME = (
    "sandbox_venue_expansion_candidate_manifest_report.parquet"
)

_AUTHORIZATION_FALSE_FIELDS = (
    "pre_2024_data_allowed",
    "provider_download_authorized",
    "archive_manifest_write_authorized",
    "source_archive_mutation_authorized",
    "replay_command_execution_authorized",
    "strict_validation_authorized",
    "candidate_pack_write_authorized",
    "strict_validation_executed",
    "candidate_pack_written",
)

_CANDIDATE_PARQUET_COLUMNS = [
    "artifact_family",
    "materialization_id",
    "candidate_id",
    "request_id",
    "bundle_id",
    "target_venue",
    "market_symbol_key",
    "data_family",
    "interval",
    "target_bucket_key",
    "source_path",
    "source_suffix",
    "source_sha256",
    "source_byte_size",
    "venue",
    "symbol",
    "candidate_symbol_keys",
    "window_start",
    "window_end",
    "normalized_row_count",
    "descriptor_id",
    "descriptor_payload",
    "manifest_patch_operation",
    "dry_run_only",
    "descriptor_only",
    "provider_download_authorized",
    "archive_manifest_write_authorized",
    "source_archive_mutation_authorized",
    "archive_manifest_write_executed",
    "source_archive_mutation_executed",
    "strict_validation_executed",
    "candidate_pack_written",
    *SANDBOX_BOUNDARY_FLAGS,
]

_PATCH_PARQUET_COLUMNS = [
    "artifact_family",
    "materialization_id",
    "request_id",
    "bundle_id",
    "request_rank",
    "target_venue",
    "market_symbol_key",
    "data_family",
    "interval",
    "target_bucket_key",
    "target_action",
    "status",
    "blocker_reasons",
    "candidate_count",
    "candidate_ids",
    "matching_file_count_before_window",
    "outside_requested_window_file_count",
    "dry_run_only",
    "descriptor_only",
    "provider_download_authorized",
    "archive_manifest_write_authorized",
    "source_archive_mutation_authorized",
    "archive_manifest_write_executed",
    "source_archive_mutation_executed",
    "strict_validation_executed",
    "candidate_pack_written",
    *SANDBOX_BOUNDARY_FLAGS,
]

_CANDIDATE_MANIFEST_REPORT_PARQUET_COLUMNS = [
    "artifact_family",
    "manifest_id",
    "source_candidate_id",
    "source_request_id",
    "source_bundle_id",
    "source_materialization_id",
    "descriptor_id",
    "venue",
    "symbol",
    "data_family",
    "interval",
    "window_start",
    "window_end",
    "source_path",
    "source_sha256",
    "source_byte_size",
    "status",
    "provider_download_authorized",
    "source_archive_mutation_authorized",
    "existing_archive_manifest_mutation_authorized",
    "strict_validation_executed",
    "candidate_pack_written",
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


def _write_parquet(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    frame = pd.DataFrame([_row_for_parquet(row) for row in rows])
    if frame.empty:
        frame = pd.DataFrame(columns=columns)
    frame.to_parquet(path, index=False)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _compact_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _dict_value(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_filter_data_family(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized not in ALLOWED_DATA_FAMILIES:
        joined = ", ".join(sorted(ALLOWED_DATA_FAMILIES))
        raise ValueError(f"data_family must be one of: {joined}")
    return normalized


def _request_window(request: Mapping[str, Any]) -> DataWindow | None:
    start = request.get("requested_window_start")
    end = request.get("requested_window_end")
    if start in {None, ""} and end in {None, ""}:
        return None
    if start in {None, ""} or end in {None, ""}:
        raise ValueError(
            f"request {request.get('request_id')} must provide both requested window bounds"
        )
    return DataWindow(str(start), str(end))


def _require_no_authorization(payload: Mapping[str, Any], *, payload_name: str) -> None:
    errors = [
        f"{field}_must_be_false"
        for field in _AUTHORIZATION_FALSE_FIELDS
        if bool(payload.get(field, False))
    ]
    if errors:
        raise ValueError(f"{payload_name} authorizes forbidden behavior: {', '.join(errors)}")


def _require_materializer_request(payload: Mapping[str, Any], *, payload_name: str) -> None:
    require_sandbox_boundary(payload, payload_name=payload_name)
    _require_no_authorization(payload, payload_name=payload_name)
    if payload.get("descriptor_only") is not True:
        raise ValueError(f"{payload_name} must be descriptor_only")
    _request_window(payload)


def _descriptor_from_candidate_payload(
    payload: Mapping[str, Any],
    *,
    payload_name: str,
) -> VenueArchiveDescriptor:
    require_sandbox_boundary(payload, payload_name=payload_name)
    window = payload.get("window")
    if not isinstance(window, Mapping):
        raise ValueError(f"{payload_name} requires descriptor window")
    return VenueArchiveDescriptor(
        descriptor_id=str(payload["descriptor_id"]),
        venue=str(payload["venue"]),
        symbol=str(payload["symbol"]),
        data_family=str(payload["data_family"]),
        interval=payload.get("interval"),
        manifest_path=Path(str(payload["manifest_path"]))
        if payload.get("manifest_path") not in {None, ""}
        else None,
        data_path=Path(str(payload["data_path"]))
        if payload.get("data_path") not in {None, ""}
        else None,
        window=DataWindow(str(window["start"]), str(window["end"])),
        source_access_mode=str(payload.get("source_access_mode", "archive_or_manifest")),
        checksum_policy=str(
            payload.get("checksum_policy", "required_for_strict_evidence")
        ),
        diagnostic_only=bool(payload.get("diagnostic_only", True)),
        source_integrity=dict(payload.get("source_integrity", {}) or {}),
        notes=tuple(str(item) for item in payload.get("notes", []) or []),
    )


def _load_request_descriptors(request_bundle_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = _load_json(request_bundle_path)
    if not isinstance(payload, dict):
        raise ValueError("sandbox venue expansion request bundle must be a JSON object")
    _require_materializer_request(payload, payload_name="sandbox_venue_expansion_request_bundle")
    descriptors = payload.get("descriptors")
    if not isinstance(descriptors, list):
        raise ValueError("sandbox venue expansion request bundle descriptors must be a list")
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(descriptors, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"sandbox venue expansion request descriptor {index} must be an object")
        _require_materializer_request(
            item,
            payload_name=f"sandbox_venue_expansion_request_descriptor:{index}",
        )
        normalized.append(dict(item))
    return payload, normalized


def _bundle_integrity(path: Path) -> dict[str, Any]:
    return _file_integrity(path)


def _source_symbol_keys(symbol: str, *, venue: str) -> list[str]:
    compact = _compact_key(symbol)
    keys = [compact] if compact else []
    if venue == "hyperliquid" and compact and not compact.endswith(("usd", "usdt", "usdc", "perp")):
        keys.extend([f"{compact}usdt", f"{compact}usd", f"{compact}perp"])
    if compact.endswith("usdt") and len(compact) > 4:
        keys.append(compact[:-4])
    if compact.endswith("usd") and len(compact) > 3:
        keys.append(compact[:-3])
    return sorted(set(keys))


def _candidate_id(
    *,
    request: Mapping[str, Any],
    source_path: Path,
    source_integrity: Mapping[str, Any],
    venue: str,
    symbol: str,
    data_family: str,
    interval: str | None,
    window_start: str,
    window_end: str,
) -> str:
    return digest_payload(
        {
            "request_id": request.get("request_id"),
            "bundle_id": request.get("bundle_id"),
            "target_venue": request.get("target_venue"),
            "market_symbol_key": _compact_key(request.get("market_symbol_key")),
            "data_family": request.get("data_family"),
            "interval": request.get("interval"),
            "target_bucket_key": request.get("target_bucket_key"),
            "source_path": str(source_path),
            "source_sha256": source_integrity.get("sha256"),
            "source_byte_size": source_integrity.get("byte_size"),
            "venue": venue,
            "symbol": symbol,
            "candidate_data_family": data_family,
            "candidate_interval": interval,
            "window_start": window_start,
            "window_end": window_end,
        },
        prefix="sbxvenmat",
        length=24,
    )


def _scan_archive_roots(archive_roots: Sequence[str | Path], *, max_files: int) -> tuple[list[dict[str, Any]], bool]:
    roots = [Path(root).expanduser().resolve() for root in archive_roots]
    files, truncated = _iter_files(roots, max_files=max_files)
    scanned: list[dict[str, Any]] = []
    for raw_path in files:
        path = raw_path.expanduser().resolve()
        source_integrity = _file_integrity(path)
        suffix = _source_suffix(path)
        base = {
            "source_path": str(path),
            "source_suffix": suffix,
            "source_integrity": source_integrity,
            "source_sha256": source_integrity.get("sha256"),
            "source_byte_size": source_integrity.get("byte_size"),
        }
        if suffix not in SUPPORTED_ARCHIVE_SUFFIXES:
            scanned.append({**base, "scan_status": "skipped", "skip_reasons": ["unsupported_suffix"]})
            continue
        try:
            frame = load_market_frame(path)
        except Exception as exc:  # noqa: BLE001 - materializer reports load blockers.
            scanned.append(
                {
                    **base,
                    "scan_status": "skipped",
                    "skip_reasons": [f"load_error:{type(exc).__name__}:{exc}"],
                }
            )
            continue
        if frame.empty:
            scanned.append(
                {
                    **base,
                    "scan_status": "skipped",
                    "skip_reasons": ["no_normalized_2024_plus_rows"],
                }
            )
            continue
        venue, venue_source = _infer_venue(path, forced_venue=None, frame=frame)
        symbol, symbol_source = _infer_symbol(
            path,
            forced_symbol=None,
            venue=venue,
            frame=frame,
        )
        data_family, data_family_source = _infer_data_family(
            path,
            forced_data_family=None,
            frame=frame,
        )
        interval, interval_source = _infer_interval(
            path,
            forced_interval=None,
            frame=frame,
        )
        window_start, window_end = _bounds(frame)
        skip_reasons: list[str] = []
        if symbol is None:
            skip_reasons.append("symbol_not_inferred")
        if window_start is None or window_end is None:
            skip_reasons.append("timestamp_bounds_not_available")
        if skip_reasons:
            scanned.append(
                {
                    **base,
                    "scan_status": "skipped",
                    "skip_reasons": skip_reasons,
                    "venue": venue,
                    "symbol": symbol,
                    "data_family": data_family,
                    "interval": interval,
                    "normalized_row_count": int(len(frame)),
                }
            )
            continue
        scanned.append(
            {
                **base,
                "scan_status": "loadable",
                "skip_reasons": [],
                "venue": venue,
                "symbol": symbol,
                "data_family": data_family,
                "interval": interval,
                "venue_inference_source": venue_source,
                "symbol_inference_source": symbol_source,
                "data_family_inference_source": data_family_source,
                "interval_inference_source": interval_source,
                "window_start": window_start,
                "window_end": window_end,
                "normalized_row_count": int(len(frame)),
                "columns": [str(column) for column in frame.columns],
                "candidate_symbol_keys": _source_symbol_keys(symbol or "", venue=venue),
            }
        )
    return scanned, truncated


def _matches_request_before_window(source: Mapping[str, Any], request: Mapping[str, Any]) -> bool:
    if source.get("scan_status") != "loadable":
        return False
    return (
        source.get("venue") == request.get("target_venue")
        and _compact_key(request.get("market_symbol_key"))
        in set(source.get("candidate_symbol_keys") or [])
        and source.get("data_family") == str(request.get("data_family") or "").lower()
        and (request.get("interval") in {None, ""} or source.get("interval") == request.get("interval"))
    )


def _matches_request_window(source: Mapping[str, Any], request: Mapping[str, Any]) -> bool:
    window = _request_window(request)
    if window is None:
        return True
    return _overlaps_requested_window(
        window_start=str(source.get("window_start")),
        window_end=str(source.get("window_end")),
        requested_window=window,
    )


def _descriptor_for_candidate(
    *,
    candidate_id: str,
    source: Mapping[str, Any],
) -> VenueArchiveDescriptor:
    return VenueArchiveDescriptor(
        descriptor_id=f"{candidate_id}-descriptor",
        venue=str(source["venue"]),
        symbol=str(source["symbol"]),
        data_family=str(source["data_family"]),
        interval=source.get("interval"),
        data_path=Path(str(source["source_path"])),
        window=DataWindow(str(source["window_start"]), str(source["window_end"])),
        source_access_mode="local_archive_materializer_dry_run",
        checksum_policy="required_for_strict_evidence",
        diagnostic_only=True,
        source_integrity={
            "sha256": source.get("source_sha256"),
            "byte_size": source.get("source_byte_size"),
        },
        notes=(
            "generated_by_sandbox_venue_expansion_local_materializer",
            "dry_run_descriptor_candidate_only",
        ),
    )


def _candidate_row(
    *,
    materialization_id: str,
    request: Mapping[str, Any],
    source: Mapping[str, Any],
) -> dict[str, Any]:
    candidate_id = _candidate_id(
        request=request,
        source_path=Path(str(source["source_path"])),
        source_integrity=source.get("source_integrity", {}),
        venue=str(source["venue"]),
        symbol=str(source["symbol"]),
        data_family=str(source["data_family"]),
        interval=source.get("interval"),
        window_start=str(source["window_start"]),
        window_end=str(source["window_end"]),
    )
    descriptor = _descriptor_for_candidate(candidate_id=candidate_id, source=source)
    descriptor_payload = descriptor.to_payload()
    require_sandbox_boundary(
        descriptor_payload,
        payload_name="sandbox_venue_expansion_descriptor_candidate_payload",
    )
    row = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_venue_expansion_descriptor_candidate",
        "materialization_id": materialization_id,
        "candidate_id": candidate_id,
        "request_id": request.get("request_id"),
        "bundle_id": request.get("bundle_id"),
        "target_venue": request.get("target_venue"),
        "market_symbol_key": _compact_key(request.get("market_symbol_key")),
        "data_family": request.get("data_family"),
        "interval": request.get("interval"),
        "target_bucket_key": request.get("target_bucket_key"),
        "target_action": request.get("target_action"),
        "source_path": source.get("source_path"),
        "source_suffix": source.get("source_suffix"),
        "source_sha256": source.get("source_sha256"),
        "source_byte_size": source.get("source_byte_size"),
        "venue": source.get("venue"),
        "symbol": source.get("symbol"),
        "candidate_symbol_keys": list(source.get("candidate_symbol_keys") or []),
        "candidate_data_family": source.get("data_family"),
        "candidate_interval": source.get("interval"),
        "window_start": source.get("window_start"),
        "window_end": source.get("window_end"),
        "normalized_row_count": int(source.get("normalized_row_count", 0) or 0),
        "venue_inference_source": source.get("venue_inference_source"),
        "symbol_inference_source": source.get("symbol_inference_source"),
        "data_family_inference_source": source.get("data_family_inference_source"),
        "interval_inference_source": source.get("interval_inference_source"),
        "descriptor_id": descriptor.descriptor_id,
        "descriptor_payload": descriptor_payload,
        "manifest_patch_operation": "append_descriptor_candidate",
        "dry_run_only": True,
        "descriptor_only": True,
        "pre_2024_data_allowed": False,
        "provider_download_authorized": False,
        "archive_manifest_write_authorized": False,
        "source_archive_mutation_authorized": False,
        "archive_manifest_write_executed": False,
        "source_archive_mutation_executed": False,
        "replay_command_execution_authorized": False,
        "strict_validation_authorized": False,
        "candidate_pack_write_authorized": False,
        "strict_validation_executed": False,
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
    }
    require_sandbox_boundary(row, payload_name="sandbox_venue_expansion_descriptor_candidate")
    _require_no_authorization(row, payload_name="sandbox_venue_expansion_descriptor_candidate")
    return row


def _patch_row(
    *,
    materialization_id: str,
    request: Mapping[str, Any],
    candidate_rows: list[dict[str, Any]],
    matching_before_window: int,
    outside_requested_window: int,
    loadable_file_count: int,
) -> dict[str, Any]:
    blocker_reasons: list[str] = []
    if not candidate_rows:
        blocker_reasons.append("no_matching_local_archive_file")
        if loadable_file_count == 0:
            blocker_reasons.append("no_loadable_local_archive_files")
        if matching_before_window > 0 and outside_requested_window > 0:
            blocker_reasons.append("matching_files_outside_requested_window")
    status = "ready_descriptor_candidates" if candidate_rows else "blocked"
    row = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_venue_expansion_manifest_patch_dry_run_row",
        "materialization_id": materialization_id,
        "request_id": request.get("request_id"),
        "bundle_id": request.get("bundle_id"),
        "request_rank": int(request.get("request_rank", 0) or 0),
        "target_venue": request.get("target_venue"),
        "market_symbol_key": _compact_key(request.get("market_symbol_key")),
        "data_family": request.get("data_family"),
        "interval": request.get("interval"),
        "target_bucket_key": request.get("target_bucket_key"),
        "target_action": request.get("target_action"),
        "status": status,
        "blocker_reasons": blocker_reasons,
        "candidate_count": len(candidate_rows),
        "candidate_ids": [row["candidate_id"] for row in candidate_rows],
        "matching_file_count_before_window": matching_before_window,
        "outside_requested_window_file_count": outside_requested_window,
        "manifest_patch_operation": "append_descriptor_candidates_dry_run",
        "dry_run_only": True,
        "descriptor_only": True,
        "pre_2024_data_allowed": False,
        "provider_download_authorized": False,
        "archive_manifest_write_authorized": False,
        "source_archive_mutation_authorized": False,
        "archive_manifest_write_executed": False,
        "source_archive_mutation_executed": False,
        "replay_command_execution_authorized": False,
        "strict_validation_authorized": False,
        "candidate_pack_write_authorized": False,
        "strict_validation_executed": False,
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
    }
    require_sandbox_boundary(row, payload_name="sandbox_venue_expansion_manifest_patch_dry_run_row")
    _require_no_authorization(row, payload_name="sandbox_venue_expansion_manifest_patch_dry_run_row")
    return row


def _scan_status_counts(scanned: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts = Counter(str(row.get("scan_status") or "unknown") for row in scanned)
    return {key: counts[key] for key in sorted(counts)}


def _skip_reason_counts(scanned: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in scanned:
        for reason in row.get("skip_reasons") or []:
            counts[str(reason)] += 1
    return {key: counts[key] for key in sorted(counts)}


def _filter_requests(
    requests: list[dict[str, Any]],
    *,
    venue: str | None,
    symbol: str | None,
    data_family: str | None,
    interval: str | None,
) -> list[dict[str, Any]]:
    filtered = requests
    if venue is not None:
        target_venue = canonical_venue(venue)
        filtered = [row for row in filtered if row.get("target_venue") == target_venue]
    if symbol is not None:
        target_symbol = _compact_key(symbol)
        filtered = [row for row in filtered if _compact_key(row.get("market_symbol_key")) == target_symbol]
    if data_family is not None:
        target_family = _safe_filter_data_family(data_family)
        filtered = [row for row in filtered if row.get("data_family") == target_family]
    if interval is not None:
        target_interval = str(interval).strip().lower()
        filtered = [row for row in filtered if row.get("interval") == target_interval]
    return filtered


def materialize_sandbox_venue_expansion_requests(
    request_bundle_path: str | Path,
    archive_roots: Sequence[str | Path],
    *,
    output_dir: str | Path | None = None,
    venue: str | None = None,
    symbol: str | None = None,
    data_family: str | None = None,
    interval: str | None = None,
    max_files: int = 5000,
) -> dict[str, Any]:
    bundle_path = Path(request_bundle_path).expanduser().resolve()
    if not bundle_path.exists():
        raise FileNotFoundError(f"sandbox venue expansion request bundle not found: {bundle_path}")
    if not archive_roots:
        raise ValueError("at least one archive root is required")
    destination = Path(output_dir).expanduser().resolve() if output_dir is not None else bundle_path.parent
    destination.mkdir(parents=True, exist_ok=True)

    bundle_payload, all_requests = _load_request_descriptors(bundle_path)
    requests = _filter_requests(
        all_requests,
        venue=venue,
        symbol=symbol,
        data_family=data_family,
        interval=interval,
    )
    scanned, truncated = _scan_archive_roots(archive_roots, max_files=max_files)
    bundle_integrity = _bundle_integrity(bundle_path)
    materialization_id = digest_payload(
        {
            "request_bundle_id": bundle_payload.get("bundle_id"),
            "request_bundle_sha256": bundle_integrity.get("sha256"),
            "archive_roots": [str(Path(root).expanduser().resolve()) for root in archive_roots],
            "filters": {
                "venue": canonical_venue(venue) if venue is not None else None,
                "symbol": _compact_key(symbol) if symbol is not None else None,
                "data_family": _safe_filter_data_family(data_family),
                "interval": str(interval).strip().lower() if interval is not None else None,
            },
            "max_files": max_files,
            "request_ids": [row.get("request_id") for row in requests],
            "source_sha256": [
                row.get("source_sha256")
                for row in scanned
                if row.get("scan_status") == "loadable"
            ],
        },
        prefix="sbxvenmatrun",
        length=24,
    )

    loadable_file_count = sum(1 for row in scanned if row.get("scan_status") == "loadable")
    candidates: list[dict[str, Any]] = []
    patch_rows: list[dict[str, Any]] = []
    for request in requests:
        before_window = [
            row for row in scanned if _matches_request_before_window(row, request)
        ]
        matching_sources = [
            row for row in before_window if _matches_request_window(row, request)
        ]
        request_candidates = [
            _candidate_row(
                materialization_id=materialization_id,
                request=request,
                source=row,
            )
            for row in matching_sources
        ]
        candidates.extend(request_candidates)
        patch_rows.append(
            _patch_row(
                materialization_id=materialization_id,
                request=request,
                candidate_rows=request_candidates,
                matching_before_window=len(before_window),
                outside_requested_window=len(before_window) - len(matching_sources),
                loadable_file_count=loadable_file_count,
            )
        )

    candidate_json_path = destination / VENUE_EXPANSION_DESCRIPTOR_CANDIDATES_JSON_NAME
    candidate_parquet_path = destination / VENUE_EXPANSION_DESCRIPTOR_CANDIDATES_PARQUET_NAME
    patch_json_path = destination / VENUE_EXPANSION_MANIFEST_PATCH_DRY_RUN_JSON_NAME
    patch_parquet_path = destination / VENUE_EXPANSION_MANIFEST_PATCH_DRY_RUN_PARQUET_NAME

    _write_parquet(candidate_parquet_path, candidates, _CANDIDATE_PARQUET_COLUMNS)
    _write_parquet(patch_parquet_path, patch_rows, _PATCH_PARQUET_COLUMNS)

    common_payload = {
        **sandbox_boundary_metadata(),
        "materialization_id": materialization_id,
        "source_request_bundle_path": str(bundle_path),
        "source_request_bundle_id": bundle_payload.get("bundle_id"),
        "source_request_bundle_sha256": bundle_integrity.get("sha256"),
        "source_request_bundle_byte_size": bundle_integrity.get("byte_size"),
        "archive_roots": [str(Path(root).expanduser().resolve()) for root in archive_roots],
        "execution_mode": VENUE_EXPANSION_MATERIALIZER_EXECUTION_MODE,
        "dry_run_only": True,
        "descriptor_only": True,
        "minimum_window_start": VENUE_EXPANSION_MATERIALIZER_MINIMUM_WINDOW_START,
        "pre_2024_data_allowed": False,
        "provider_download_authorized": False,
        "archive_manifest_write_authorized": False,
        "source_archive_mutation_authorized": False,
        "archive_manifest_write_executed": False,
        "source_archive_mutation_executed": False,
        "replay_command_execution_authorized": False,
        "strict_validation_authorized": False,
        "candidate_pack_write_authorized": False,
        "strict_validation_executed": False,
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
        "request_filter": {
            "venue": canonical_venue(venue) if venue is not None else None,
            "symbol": _compact_key(symbol) if symbol is not None else None,
            "data_family": _safe_filter_data_family(data_family),
            "interval": str(interval).strip().lower() if interval is not None else None,
        },
        "source_request_count": len(all_requests),
        "filtered_request_count": len(requests),
        "archive_file_count": len(scanned),
        "loadable_archive_file_count": loadable_file_count,
        "archive_scan_truncated": truncated,
        "max_files": max_files,
        "archive_scan_status_counts": _scan_status_counts(scanned),
        "archive_skip_reason_counts": _skip_reason_counts(scanned),
        "descriptor_candidate_count": len(candidates),
        "dry_run_patch_row_count": len(patch_rows),
        "blocked_request_count": sum(1 for row in patch_rows if row["status"] == "blocked"),
        "ready_request_count": sum(
            1 for row in patch_rows if row["status"] == "ready_descriptor_candidates"
        ),
        "descriptor_candidates_json_path": str(candidate_json_path),
        "descriptor_candidates_parquet_path": str(candidate_parquet_path),
        "manifest_patch_dry_run_json_path": str(patch_json_path),
        "manifest_patch_dry_run_parquet_path": str(patch_parquet_path),
    }

    candidates_payload = {
        **common_payload,
        "artifact_family": "rapid_strategy_iteration_sandbox_venue_expansion_descriptor_candidates",
        "descriptor_candidates": candidates,
    }
    require_sandbox_boundary(
        candidates_payload,
        payload_name="sandbox_venue_expansion_descriptor_candidates",
    )
    _require_no_authorization(
        candidates_payload,
        payload_name="sandbox_venue_expansion_descriptor_candidates",
    )
    candidate_json_path.write_text(
        json.dumps(candidates_payload, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )

    patch_payload = {
        **common_payload,
        "artifact_family": "rapid_strategy_iteration_sandbox_venue_expansion_manifest_patch_dry_run",
        "manifest_patch_rows": patch_rows,
        "descriptor_candidates": candidates,
    }
    require_sandbox_boundary(
        patch_payload,
        payload_name="sandbox_venue_expansion_manifest_patch_dry_run",
    )
    _require_no_authorization(
        patch_payload,
        payload_name="sandbox_venue_expansion_manifest_patch_dry_run",
    )
    patch_json_path.write_text(
        json.dumps(patch_payload, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    return patch_payload


def export_sandbox_venue_expansion_candidate_manifest(
    descriptor_candidates_path: str | Path,
    *,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    candidates_path = Path(descriptor_candidates_path).expanduser().resolve()
    if not candidates_path.exists():
        raise FileNotFoundError(
            f"sandbox venue expansion descriptor candidates not found: {candidates_path}"
        )
    payload = _load_json(candidates_path)
    if not isinstance(payload, dict):
        raise ValueError("sandbox venue expansion descriptor candidates must be a JSON object")
    require_sandbox_boundary(
        payload,
        payload_name="sandbox_venue_expansion_descriptor_candidates",
    )
    _require_no_authorization(
        payload,
        payload_name="sandbox_venue_expansion_descriptor_candidates",
    )
    candidates = payload.get("descriptor_candidates")
    if not isinstance(candidates, list):
        raise ValueError("descriptor_candidates must be a list")
    if not candidates:
        raise ValueError("descriptor_candidates must contain at least one row")

    descriptor_payloads: list[dict[str, Any]] = []
    report_rows: list[dict[str, Any]] = []
    seen_descriptor_ids: set[str] = set()
    for index, candidate in enumerate(candidates, start=1):
        if not isinstance(candidate, dict):
            raise ValueError(f"descriptor candidate {index} must be an object")
        require_sandbox_boundary(
            candidate,
            payload_name=f"sandbox_venue_expansion_descriptor_candidate:{index}",
        )
        _require_no_authorization(
            candidate,
            payload_name=f"sandbox_venue_expansion_descriptor_candidate:{index}",
        )
        descriptor_payload = candidate.get("descriptor_payload")
        if not isinstance(descriptor_payload, dict):
            raise ValueError(f"descriptor candidate {index} requires descriptor_payload")
        descriptor = _descriptor_from_candidate_payload(
            descriptor_payload,
            payload_name=f"sandbox_venue_expansion_descriptor_payload:{index}",
        )
        if descriptor.descriptor_id in seen_descriptor_ids:
            raise ValueError(f"duplicate descriptor_id in descriptor candidates: {descriptor.descriptor_id}")
        seen_descriptor_ids.add(descriptor.descriptor_id)
        normalized_payload = descriptor.to_payload()
        require_sandbox_boundary(
            normalized_payload,
            payload_name=f"sandbox_venue_expansion_candidate_manifest_descriptor:{index}",
        )
        descriptor_payloads.append(normalized_payload)

    source_integrity = _file_integrity(candidates_path)
    manifest_id = digest_payload(
        {
            "source_descriptor_candidates_sha256": source_integrity.get("sha256"),
            "source_materialization_id": payload.get("materialization_id"),
            "descriptor_payloads": descriptor_payloads,
        },
        prefix="sbxvencandmanifest",
        length=24,
    )
    destination_root = (
        Path(output_dir).expanduser().resolve()
        if output_dir is not None
        else candidates_path.parent
    )
    destination = destination_root / manifest_id
    destination.mkdir(parents=True, exist_ok=True)
    manifest_path = destination / ARCHIVE_MANIFEST_JSON_NAME
    report_json_path = destination / VENUE_EXPANSION_CANDIDATE_MANIFEST_REPORT_JSON_NAME
    report_parquet_path = destination / VENUE_EXPANSION_CANDIDATE_MANIFEST_REPORT_PARQUET_NAME

    for candidate, descriptor_payload in zip(candidates, descriptor_payloads, strict=True):
        source_integrity_payload = dict(descriptor_payload.get("source_integrity", {}) or {})
        row = {
            **sandbox_boundary_metadata(),
            "artifact_family": "rapid_strategy_iteration_sandbox_venue_expansion_candidate_manifest_row",
            "manifest_id": manifest_id,
            "source_candidate_id": candidate.get("candidate_id"),
            "source_request_id": candidate.get("request_id"),
            "source_bundle_id": candidate.get("bundle_id"),
            "source_materialization_id": candidate.get("materialization_id"),
            "descriptor_id": descriptor_payload.get("descriptor_id"),
            "venue": descriptor_payload.get("venue"),
            "symbol": descriptor_payload.get("symbol"),
            "data_family": descriptor_payload.get("data_family"),
            "interval": descriptor_payload.get("interval"),
            "window_start": _dict_value(descriptor_payload.get("window")).get("start"),
            "window_end": _dict_value(descriptor_payload.get("window")).get("end"),
            "source_path": descriptor_payload.get("data_path")
            or descriptor_payload.get("manifest_path"),
            "source_sha256": source_integrity_payload.get("sha256"),
            "source_byte_size": source_integrity_payload.get("byte_size"),
            "status": "included",
            "provider_download_authorized": False,
            "source_archive_mutation_authorized": False,
            "existing_archive_manifest_mutation_authorized": False,
            "strict_validation_executed": False,
            "candidate_pack_written": False,
            "candidate_pack_paths": [],
        }
        require_sandbox_boundary(
            row,
            payload_name="sandbox_venue_expansion_candidate_manifest_row",
        )
        report_rows.append(row)

    manifest_payload = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_venue_expansion_candidate_manifest",
        "manifest_id": manifest_id,
        "source_descriptor_candidates_path": str(candidates_path),
        "source_descriptor_candidates_sha256": source_integrity.get("sha256"),
        "source_descriptor_candidates_byte_size": source_integrity.get("byte_size"),
        "source_materialization_id": payload.get("materialization_id"),
        "descriptor_candidate_count": len(candidates),
        "descriptor_count": len(descriptor_payloads),
        "venue_archive_manifest_path": str(manifest_path),
        "candidate_manifest_report_json_path": str(report_json_path),
        "candidate_manifest_report_parquet_path": str(report_parquet_path),
        "sandbox_archive_manifest_write_scope": "new_candidate_manifest_only",
        "provider_download_authorized": False,
        "source_archive_mutation_authorized": False,
        "existing_archive_manifest_mutation_authorized": False,
        "strict_validation_authorized": False,
        "candidate_pack_write_authorized": False,
        "strict_validation_executed": False,
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
        "venue_archives": descriptor_payloads,
    }
    require_sandbox_boundary(
        manifest_payload,
        payload_name="sandbox_venue_expansion_candidate_manifest",
    )

    report_payload = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_venue_expansion_candidate_manifest_report",
        "manifest_id": manifest_id,
        "source_descriptor_candidates_path": str(candidates_path),
        "source_descriptor_candidates_sha256": source_integrity.get("sha256"),
        "source_descriptor_candidates_byte_size": source_integrity.get("byte_size"),
        "source_materialization_id": payload.get("materialization_id"),
        "descriptor_candidate_count": len(candidates),
        "descriptor_count": len(descriptor_payloads),
        "venue_archive_manifest_path": str(manifest_path),
        "candidate_manifest_report_json_path": str(report_json_path),
        "candidate_manifest_report_parquet_path": str(report_parquet_path),
        "sandbox_archive_manifest_write_scope": "new_candidate_manifest_only",
        "provider_download_authorized": False,
        "source_archive_mutation_authorized": False,
        "existing_archive_manifest_mutation_authorized": False,
        "strict_validation_authorized": False,
        "candidate_pack_write_authorized": False,
        "strict_validation_executed": False,
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
        "descriptors": descriptor_payloads,
        "rows": report_rows,
    }
    require_sandbox_boundary(
        report_payload,
        payload_name="sandbox_venue_expansion_candidate_manifest_report",
    )

    _write_parquet(
        report_parquet_path,
        report_rows,
        _CANDIDATE_MANIFEST_REPORT_PARQUET_COLUMNS,
    )
    manifest_path.write_text(
        json.dumps(manifest_payload, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    report_json_path.write_text(
        json.dumps(report_payload, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    return report_payload
