from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from tradingbotsuite.research_sandbox.boundary import (
    SANDBOX_BOUNDARY_FLAGS,
    require_sandbox_boundary,
    sandbox_boundary_metadata,
)
from tradingbotsuite.research_sandbox.identity import digest_payload


VENUE_EXPANSION_REQUEST_BUNDLE_JSON_NAME = "sandbox_venue_expansion_request_bundle.json"
VENUE_EXPANSION_REQUEST_BUNDLE_PARQUET_NAME = "sandbox_venue_expansion_request_bundle.parquet"
VENUE_EXPANSION_REQUEST_SOURCE_REFERENCE_LIMIT = 10
VENUE_EXPANSION_TARGET_WORKLIST_ACTION = "repair_or_add_venue_expansion_archives"
VENUE_EXPANSION_DESCRIPTOR_EXECUTION_MODE = "descriptor_only_no_execution"
VENUE_EXPANSION_MINIMUM_WINDOW_START = "2024-01-01"

VENUE_EXPANSION_REQUEST_PARQUET_COLUMNS = [
    "artifact_family",
    "bundle_id",
    "request_id",
    "dedupe_key",
    "request_rank",
    "requested_operation",
    "execution_mode",
    "descriptor_only",
    "target_venue",
    "market_symbol_key",
    "data_family",
    "interval",
    "target_bucket_key",
    "target_status",
    "target_action",
    "target_venue_observed",
    "target_missing",
    "observed_symbols",
    "source_coverage_key",
    "source_worklist_row_count",
    "source_iteration_ids",
    "source_run_ids",
    "source_queues",
    "source_queue_counts",
    "source_artifact_paths",
    "source_artifact_path_relatives",
    "source_iteration_manifest_paths",
    "source_agent_brief_json_paths",
    "source_strategy_catalog_json_paths",
    "source_venue_archive_manifest_paths",
    "source_archive_build_report_json_paths",
    "source_archive_coverage_venue_expansion_gaps_parquet_paths",
    "source_paths",
    "manifest_paths",
    "source_reference_count",
    "source_references",
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
    "blocker_reason_counts",
    "minimum_window_start",
    "pre_2024_data_allowed",
    "provider_download_authorized",
    "archive_manifest_write_authorized",
    "source_archive_mutation_authorized",
    "replay_command_execution_authorized",
    "strict_validation_authorized",
    "candidate_pack_write_authorized",
    "strict_validation_executed",
    "candidate_pack_written",
    "candidate_pack_paths",
    *SANDBOX_BOUNDARY_FLAGS,
]


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _scalar(value: Any) -> Any:
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _parse_json_cell(value: Any) -> Any:
    value = _scalar(value)
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped or stripped[0] not in "[{":
        return value
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return value


def _list_value(value: Any) -> list[Any]:
    parsed = _parse_json_cell(value)
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, tuple):
        return list(parsed)
    if parsed is None:
        return []
    return [parsed]


def _dict_value(value: Any) -> dict[str, Any]:
    parsed = _parse_json_cell(value)
    if isinstance(parsed, dict):
        return {str(key): item for key, item in parsed.items()}
    return {}


def _safe_int(value: Any) -> int:
    value = _scalar(value)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _bool_value(value: Any, *, default: bool = False) -> bool:
    value = _scalar(value)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y"}:
            return True
        if lowered in {"0", "false", "no", "n"}:
            return False
        return default
    return bool(value)


def _str_or_none(value: Any) -> str | None:
    value = _scalar(value)
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _row_for_parquet(payload: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, (dict, list, tuple)):
            row[key] = json.dumps(value, sort_keys=True, default=_json_default)
        else:
            row[key] = value
    return row


def _add_unique(target: list[str], value: Any) -> None:
    text = _str_or_none(value)
    if text is not None and text not in target:
        target.append(text)


def _add_unique_many(target: list[str], values: Any) -> None:
    for value in _list_value(values):
        _add_unique(target, value)


def _add_count(counts: dict[str, int], value: Any, *, increment: int = 1) -> None:
    text = _str_or_none(value)
    if text is not None:
        counts[text] = counts.get(text, 0) + increment


def _sorted_count_map(counts: dict[str, int]) -> dict[str, int]:
    return {key: counts[key] for key in sorted(counts)}


def _value_counts(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        _add_count(counts, row.get(field))
    return _sorted_count_map(counts)


def _source_row_sort_key(row: dict[str, Any]) -> tuple[str, str, str, str, str, str, int, int]:
    return (
        str(row.get("target_venue") or ""),
        str(row.get("market_symbol_key") or ""),
        str(row.get("data_family") or ""),
        str(row.get("interval") or ""),
        str(row.get("target_action") or ""),
        str(row.get("target_bucket_key") or ""),
        _safe_int(row.get("worklist_row_rank")),
        _safe_int(row.get("venue_expansion_gap_sample_rank")),
    )


def _source_reference(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_artifact_path": row.get("source_artifact_path"),
        "source_artifact_path_relative": row.get("source_artifact_path_relative"),
        "source_index_id": row.get("source_index_id"),
        "iteration_id": row.get("iteration_id"),
        "run_id": row.get("run_id"),
        "worklist_row_rank": _safe_int(row.get("worklist_row_rank")),
        "action_plan_row_rank": _safe_int(row.get("action_plan_row_rank")),
        "venue_expansion_gap_sample_rank": _safe_int(
            row.get("venue_expansion_gap_sample_rank")
        ),
        "source_gap_rank": _safe_int(row.get("source_gap_rank")),
        "source_queues": _list_value(row.get("source_queues")),
        "iteration_manifest_path": row.get("iteration_manifest_path"),
        "agent_brief_json_path": row.get("agent_brief_json_path"),
        "strategy_catalog_json_path": row.get("strategy_catalog_json_path"),
        "venue_archive_manifest_path": row.get("venue_archive_manifest_path"),
        "archive_build_report_json_path": row.get("archive_build_report_json_path"),
        "archive_coverage_venue_expansion_gaps_parquet_path": row.get(
            "archive_coverage_venue_expansion_gaps_parquet_path"
        ),
    }


def _require_source_row_boundary(row: dict[str, Any]) -> None:
    errors: list[str] = []
    for key, expected in SANDBOX_BOUNDARY_FLAGS.items():
        if _bool_value(row.get(key), default=not expected) is not expected:
            errors.append(f"{key}_must_be_{str(expected).lower()}")
    for key in (
        "live_signal",
        "paper_signal",
        "sizing_instruction",
        "order_placement_instruction",
        "runtime_mode_change",
    ):
        if _bool_value(row.get(key), default=False):
            errors.append(f"{key}_must_not_be_true")
    if errors:
        joined = ", ".join(errors)
        raise ValueError(
            "sandbox_venue_expansion_worklist_row violates sandbox boundary: "
            f"{joined}"
        )


def _require_2024_or_later_window(row: dict[str, Any]) -> None:
    minimum = date.fromisoformat(VENUE_EXPANSION_MINIMUM_WINDOW_START)
    for key in ("requested_window_start", "observed_window_start"):
        value = _str_or_none(row.get(key))
        if value is None:
            continue
        try:
            observed = date.fromisoformat(value[:10])
        except ValueError:
            continue
        if observed < minimum:
            rank = _safe_int(row.get("worklist_row_rank"))
            raise ValueError(
                "sandbox venue expansion request bundle refuses pre-2024 "
                f"{key} on worklist row {rank}: {value}"
            )


def _normalized_worklist_rows(worklist_path: Path) -> list[dict[str, Any]]:
    frame = pd.read_parquet(worklist_path)
    rows: list[dict[str, Any]] = []
    for raw_row in frame.to_dict("records"):
        row = {str(key): _parse_json_cell(value) for key, value in raw_row.items()}
        _require_source_row_boundary(row)
        if str(row.get("action") or "") != VENUE_EXPANSION_TARGET_WORKLIST_ACTION:
            continue
        if str(row.get("target_action") or "") == "use_ready_archive_bucket":
            continue
        _require_2024_or_later_window(row)
        rows.append(row)
    return sorted(rows, key=_source_row_sort_key)


def _resolve_worklist_path(
    catalog: dict[str, Any],
    *,
    catalog_path: Path,
    worklist_path: str | Path | None,
) -> Path:
    raw_path = (
        worklist_path
        if worklist_path is not None
        else catalog.get("iteration_venue_expansion_gap_worklist_parquet_path")
    )
    if raw_path is None or str(raw_path) == "":
        raise ValueError(
            "sandbox artifact catalog does not reference an iteration venue "
            "expansion gap worklist parquet path"
        )
    resolved = Path(raw_path)
    if not resolved.is_absolute():
        resolved = catalog_path.parent / resolved
    resolved = resolved.resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"sandbox venue expansion worklist not found: {resolved}")
    return resolved


def _dedupe_key_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_venue": row.get("target_venue"),
        "market_symbol_key": row.get("market_symbol_key"),
        "data_family": row.get("data_family"),
        "interval": row.get("interval"),
        "target_action": row.get("target_action"),
        "target_bucket_key": row.get("target_bucket_key"),
    }


def _initial_request(row: dict[str, Any], *, dedupe_key: str) -> dict[str, Any]:
    return {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_venue_expansion_request_descriptor",
        "bundle_id": None,
        "request_id": None,
        "dedupe_key": dedupe_key,
        "request_rank": 0,
        "requested_operation": "archive_descriptor_intake_request",
        "execution_mode": VENUE_EXPANSION_DESCRIPTOR_EXECUTION_MODE,
        "descriptor_only": True,
        "target_venue": row.get("target_venue"),
        "market_symbol_key": row.get("market_symbol_key"),
        "data_family": row.get("data_family"),
        "interval": row.get("interval"),
        "target_bucket_key": row.get("target_bucket_key"),
        "target_status": row.get("target_status"),
        "target_action": row.get("target_action"),
        "target_venue_observed": _bool_value(row.get("target_venue_observed")),
        "target_missing": _bool_value(row.get("target_missing")),
        "observed_symbols": [],
        "source_coverage_key": row.get("source_coverage_key"),
        "source_worklist_row_count": 0,
        "source_iteration_ids": [],
        "source_run_ids": [],
        "source_queues": [],
        "source_queue_counts": {},
        "source_artifact_paths": [],
        "source_artifact_path_relatives": [],
        "source_iteration_manifest_paths": [],
        "source_agent_brief_json_paths": [],
        "source_strategy_catalog_json_paths": [],
        "source_venue_archive_manifest_paths": [],
        "source_archive_build_report_json_paths": [],
        "source_archive_coverage_venue_expansion_gaps_parquet_paths": [],
        "source_paths": [],
        "manifest_paths": [],
        "source_reference_count": 0,
        "source_references": [],
        "descriptor_count": _safe_int(row.get("descriptor_count")),
        "ready_descriptor_count": _safe_int(row.get("ready_descriptor_count")),
        "blocked_descriptor_count": _safe_int(row.get("blocked_descriptor_count")),
        "ready_window_row_count": _safe_int(row.get("ready_window_row_count")),
        "ready_requested_window_row_count": _safe_int(
            row.get("ready_requested_window_row_count")
        ),
        "requested_window_filter_applied": _bool_value(
            row.get("requested_window_filter_applied")
        ),
        "requested_window_start": row.get("requested_window_start"),
        "requested_window_end": row.get("requested_window_end"),
        "observed_window_start": row.get("observed_window_start"),
        "observed_window_end": row.get("observed_window_end"),
        "blocker_reason_counts": _dict_value(row.get("blocker_reason_counts")),
        "minimum_window_start": VENUE_EXPANSION_MINIMUM_WINDOW_START,
        "pre_2024_data_allowed": False,
        "provider_download_authorized": False,
        "archive_manifest_write_authorized": False,
        "source_archive_mutation_authorized": False,
        "replay_command_execution_authorized": False,
        "strict_validation_authorized": False,
        "candidate_pack_write_authorized": False,
        "strict_validation_executed": False,
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
    }


def _merge_source_row(request: dict[str, Any], row: dict[str, Any]) -> None:
    request["source_worklist_row_count"] = _safe_int(
        request.get("source_worklist_row_count")
    ) + 1
    _add_unique_many(request["observed_symbols"], row.get("observed_symbols"))
    _add_unique(request["source_iteration_ids"], row.get("iteration_id"))
    _add_unique(request["source_run_ids"], row.get("run_id"))
    _add_unique(request["source_artifact_paths"], row.get("source_artifact_path"))
    _add_unique(
        request["source_artifact_path_relatives"],
        row.get("source_artifact_path_relative"),
    )
    _add_unique(
        request["source_iteration_manifest_paths"],
        row.get("iteration_manifest_path"),
    )
    _add_unique(request["source_agent_brief_json_paths"], row.get("agent_brief_json_path"))
    _add_unique(
        request["source_strategy_catalog_json_paths"],
        row.get("strategy_catalog_json_path"),
    )
    _add_unique(
        request["source_venue_archive_manifest_paths"],
        row.get("venue_archive_manifest_path"),
    )
    _add_unique(
        request["source_archive_build_report_json_paths"],
        row.get("archive_build_report_json_path"),
    )
    _add_unique(
        request["source_archive_coverage_venue_expansion_gaps_parquet_paths"],
        row.get("archive_coverage_venue_expansion_gaps_parquet_path"),
    )
    _add_unique_many(request["source_paths"], row.get("source_paths"))
    _add_unique_many(request["manifest_paths"], row.get("manifest_paths"))
    queue_counts = request["source_queue_counts"]
    for queue in _list_value(row.get("source_queues")):
        _add_unique(request["source_queues"], queue)
        _add_count(queue_counts, queue)
    references = request["source_references"]
    if len(references) < VENUE_EXPANSION_REQUEST_SOURCE_REFERENCE_LIMIT:
        references.append(_source_reference(row))
    request["source_reference_count"] = len(references)
    request["source_queue_counts"] = _sorted_count_map(queue_counts)
    for field in (
        "descriptor_count",
        "ready_descriptor_count",
        "blocked_descriptor_count",
        "ready_window_row_count",
        "ready_requested_window_row_count",
    ):
        request[field] = max(_safe_int(request.get(field)), _safe_int(row.get(field)))


def _deduped_requests(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        dedupe_key = digest_payload(
            _dedupe_key_payload(row),
            prefix="sbxvenuegapkey",
            length=24,
        )
        if dedupe_key not in grouped:
            grouped[dedupe_key] = _initial_request(row, dedupe_key=dedupe_key)
        _merge_source_row(grouped[dedupe_key], row)
    return sorted(grouped.values(), key=_source_row_sort_key)


def export_sandbox_venue_expansion_request_bundle(
    catalog_path: str | Path,
    *,
    output_dir: str | Path | None = None,
    worklist_path: str | Path | None = None,
) -> dict[str, Any]:
    catalog_json_path = Path(catalog_path).resolve()
    if not catalog_json_path.exists():
        raise FileNotFoundError(f"sandbox artifact catalog not found: {catalog_json_path}")
    catalog = _load_json(catalog_json_path)
    if not isinstance(catalog, dict):
        raise ValueError("sandbox artifact catalog must be a JSON object")
    require_sandbox_boundary(
        catalog,
        payload_name="sandbox_venue_expansion_request_bundle_catalog",
    )

    resolved_worklist_path = _resolve_worklist_path(
        catalog,
        catalog_path=catalog_json_path,
        worklist_path=worklist_path,
    )
    destination = Path(output_dir).resolve() if output_dir is not None else catalog_json_path.parent
    destination.mkdir(parents=True, exist_ok=True)

    source_rows = _normalized_worklist_rows(resolved_worklist_path)
    requests = _deduped_requests(source_rows)
    bundle_id = digest_payload(
        {
            "source_catalog_path": str(catalog_json_path),
            "source_worklist_parquet_path": str(resolved_worklist_path),
            "dedupe_keys": [str(row.get("dedupe_key")) for row in requests],
        },
        prefix="sbxvenreqbundle",
        length=24,
    )
    for rank, request in enumerate(requests, start=1):
        request["bundle_id"] = bundle_id
        request["request_rank"] = rank
        request["request_id"] = digest_payload(
            {
                "bundle_id": bundle_id,
                "dedupe_key": request.get("dedupe_key"),
                "request_rank": rank,
            },
            prefix="sbxvenreq",
            length=24,
        )
        require_sandbox_boundary(
            request,
            payload_name="sandbox_venue_expansion_request_descriptor",
        )

    bundle_json_path = destination / VENUE_EXPANSION_REQUEST_BUNDLE_JSON_NAME
    bundle_parquet_path = destination / VENUE_EXPANSION_REQUEST_BUNDLE_PARQUET_NAME
    frame = pd.DataFrame([_row_for_parquet(row) for row in requests])
    if frame.empty:
        frame = pd.DataFrame(columns=VENUE_EXPANSION_REQUEST_PARQUET_COLUMNS)
    frame.to_parquet(bundle_parquet_path, index=False)

    payload = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_venue_expansion_request_bundle",
        "bundle_id": bundle_id,
        "source_catalog_path": str(catalog_json_path),
        "source_worklist_parquet_path": str(resolved_worklist_path),
        "source_worklist_row_count": len(source_rows),
        "execution_mode": VENUE_EXPANSION_DESCRIPTOR_EXECUTION_MODE,
        "descriptor_only": True,
        "minimum_window_start": VENUE_EXPANSION_MINIMUM_WINDOW_START,
        "pre_2024_data_allowed": False,
        "provider_download_authorized": False,
        "archive_manifest_write_authorized": False,
        "source_archive_mutation_authorized": False,
        "replay_command_execution_authorized": False,
        "strict_validation_authorized": False,
        "candidate_pack_write_authorized": False,
        "strict_validation_executed": False,
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
        "request_count": len(source_rows),
        "deduped_request_count": len(requests),
        "descriptor_count": len(requests),
        "duplicates_removed": len(source_rows) - len(requests),
        "target_venue_counts": _value_counts(requests, "target_venue"),
        "target_action_counts": _value_counts(requests, "target_action"),
        "target_status_counts": _value_counts(requests, "target_status"),
        "data_family_counts": _value_counts(requests, "data_family"),
        "interval_counts": _value_counts(requests, "interval"),
        "market_symbol_key_counts": _value_counts(requests, "market_symbol_key"),
        "bundle_json_path": str(bundle_json_path),
        "bundle_parquet_path": str(bundle_parquet_path),
        "descriptors": requests,
    }
    require_sandbox_boundary(
        payload,
        payload_name="sandbox_venue_expansion_request_bundle",
    )
    bundle_json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    return payload
