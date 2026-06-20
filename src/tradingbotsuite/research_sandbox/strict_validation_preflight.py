from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from tradingbotsuite.research_sandbox.boundary import (
    SANDBOX_BOUNDARY_FLAGS,
    require_sandbox_boundary,
    sandbox_boundary_metadata,
)
from tradingbotsuite.research_sandbox.identity import digest_payload
from tradingbotsuite.research_sandbox.validation_bundle import (
    DESCRIPTOR_EXECUTION_MODE,
    STRICT_VALIDATION_COMMAND,
    STRICT_VALIDATION_ENTRYPOINT,
)


STRICT_VALIDATION_DESCRIPTOR_PREFLIGHT_JSON_NAME = "strict_validation_descriptor_preflight.json"
STRICT_VALIDATION_DESCRIPTOR_PREFLIGHT_PARQUET_NAME = "strict_validation_descriptor_preflight.parquet"
STRICT_VALIDATION_DESCRIPTOR_PREFLIGHT_SCHEMA_VERSION = "sandbox_strict_validation_descriptor_preflight_v1"

ACCEPTED_FOR_STRICT_VALIDATION_PLANNING = "accepted_for_strict_validation_planning"
BLOCKED_MISSING_SOURCE_CONTEXT = "blocked_missing_source_context"
BLOCKED_MISSING_ARCHIVE_IDENTITY = "blocked_missing_archive_identity"
BLOCKED_PROXY_ONLY_STRATEGY = "blocked_proxy_only_strategy"
BLOCKED_MISSING_REQUIRED_VALIDATION_REQUIREMENTS = "blocked_missing_required_validation_requirements"
BLOCKED_BOUNDARY_VIOLATION = "blocked_boundary_violation"
BLOCKED_PRE_2024_WINDOW = "blocked_pre_2024_window"
BLOCKED_CANDIDATE_PACK_OR_PROMOTION_FLAG = "blocked_candidate_pack_or_promotion_flag"

_MIN_SANDBOX_DATE = date(2024, 1, 1)
_REQUIRED_SOURCE_CONTEXT_KEYS = (
    "source_trial_id",
    "source_run_id",
    "hypothesis_id",
    "family",
    "venue",
    "symbol",
    "data_family",
    "market_start",
    "market_end",
    "execution_assumptions",
)
_REQUIRED_ARCHIVE_IDENTITY_KEYS = ("descriptor_id", "routing_mode")


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _row_for_parquet(payload: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, (dict, list, tuple)):
            row[key] = json.dumps(value, sort_keys=True, default=_json_default)
        else:
            row[key] = value
    return row


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(value.strip().replace("Z", "+00:00")).date()
        except ValueError:
            return None
    return None


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _candidate_or_promotion_flags(descriptor: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    for key in (
        "promotion_ready",
        "candidate_evidence",
        "candidate_pack_eligible",
        "strict_validation_executed",
        "candidate_pack_written",
        "live_signal",
        "paper_signal",
        "sizing_instruction",
        "order_placement_instruction",
        "runtime_mode_change",
        "live_config_writes_allowed",
        "candidate_pack_writes_allowed",
    ):
        expected_false = key not in {"promotion_ready", "candidate_evidence", "candidate_pack_eligible"}
        if expected_false and _truthy(descriptor.get(key)):
            reasons.append(key)
        if key in {"promotion_ready", "candidate_evidence", "candidate_pack_eligible"} and descriptor.get(key) is not False:
            reasons.append(key)
    if _as_list(descriptor.get("candidate_pack_paths")):
        reasons.append("candidate_pack_paths")
    return sorted(set(reasons))


def _require_descriptor_only_mode(payload: dict[str, Any], *, payload_name: str) -> None:
    if payload.get("descriptor_only") is not True:
        raise ValueError(f"{payload_name} must remain descriptor-only")
    if payload.get("execution_mode") != DESCRIPTOR_EXECUTION_MODE:
        raise ValueError(f"{payload_name} must use {DESCRIPTOR_EXECUTION_MODE}")


def _source_context_blocked(source_trial_context: dict[str, Any], descriptor: dict[str, Any]) -> bool:
    if not source_trial_context:
        return True
    missing = [key for key in _REQUIRED_SOURCE_CONTEXT_KEYS if source_trial_context.get(key) in (None, "", [])]
    if missing:
        return True
    if not descriptor.get("source_trial_id") or not descriptor.get("source_run_id"):
        return True
    if not _as_dict(source_trial_context.get("execution_assumptions")):
        return True
    if not _as_dict(descriptor.get("source_metrics")):
        return True
    return False


def _archive_identity_blocked(source_trial_context: dict[str, Any], descriptor: dict[str, Any]) -> bool:
    market_source = _as_dict(descriptor.get("source_market_source")) or _as_dict(source_trial_context.get("market_source"))
    source_descriptor_id = (
        descriptor.get("source_venue_descriptor_id")
        or source_trial_context.get("venue_descriptor_id")
        or market_source.get("descriptor_id")
    )
    if not source_descriptor_id:
        return True
    if any(market_source.get(key) in (None, "") for key in _REQUIRED_ARCHIVE_IDENTITY_KEYS):
        return True
    if not (
        market_source.get("data_path")
        or market_source.get("shared_market_data_path")
        or market_source.get("manifest_path")
        or market_source.get("archive_identity")
    ):
        return True
    if not (descriptor.get("venue") or source_trial_context.get("venue")):
        return True
    if not (descriptor.get("symbol") or source_trial_context.get("symbol")):
        return True
    if not source_trial_context.get("data_family"):
        return True
    return False


def _pre_2024_blocked(source_trial_context: dict[str, Any], descriptor: dict[str, Any]) -> bool:
    starts = [
        _parse_date(source_trial_context.get("market_start")),
        _parse_date(descriptor.get("source_market_start")),
    ]
    ends = [
        _parse_date(source_trial_context.get("market_end")),
        _parse_date(descriptor.get("source_market_end")),
    ]
    known_dates = [item for item in (*starts, *ends) if item is not None]
    return any(item < _MIN_SANDBOX_DATE for item in known_dates)


def _proxy_only_blocked(source_trial_context: dict[str, Any], descriptor: dict[str, Any]) -> bool:
    execution_assumptions = _as_dict(source_trial_context.get("execution_assumptions"))
    source_request_context = _as_dict(_as_dict(descriptor.get("source_request_payload")).get("source_trial_context"))
    source_request_assumptions = _as_dict(source_request_context.get("execution_assumptions"))
    return any(
        _truthy(container.get("sandbox_proxy_only")) or _truthy(container.get("sandbox_proxy_signal"))
        for container in (execution_assumptions, source_request_assumptions)
    )


def _missing_required_evidence(descriptor: dict[str, Any]) -> bool:
    required_evidence = _as_list(descriptor.get("required_evidence"))
    return not required_evidence or any(not str(item).strip() for item in required_evidence)


def _warning_reasons(source_trial_context: dict[str, Any], descriptor: dict[str, Any]) -> list[str]:
    market_source = _as_dict(descriptor.get("source_market_source")) or _as_dict(source_trial_context.get("market_source"))
    warnings: list[str] = []
    if not (market_source.get("source_integrity") or source_trial_context.get("source_integrity")):
        warnings.append("missing_source_integrity_metadata")
    if not (market_source.get("interval") or source_trial_context.get("interval")):
        warnings.append("missing_interval_metadata")
    return warnings


def _descriptor_status(descriptor: dict[str, Any]) -> tuple[str, list[str], list[str]]:
    reasons: list[str] = []
    source_trial_context = _as_dict(descriptor.get("source_trial_context"))
    if _candidate_or_promotion_flags(descriptor):
        reasons.append(BLOCKED_CANDIDATE_PACK_OR_PROMOTION_FLAG)
    if _source_context_blocked(source_trial_context, descriptor):
        reasons.append(BLOCKED_MISSING_SOURCE_CONTEXT)
    if _archive_identity_blocked(source_trial_context, descriptor):
        reasons.append(BLOCKED_MISSING_ARCHIVE_IDENTITY)
    if _proxy_only_blocked(source_trial_context, descriptor):
        reasons.append(BLOCKED_PROXY_ONLY_STRATEGY)
    if _missing_required_evidence(descriptor):
        reasons.append(BLOCKED_MISSING_REQUIRED_VALIDATION_REQUIREMENTS)
    if _pre_2024_blocked(source_trial_context, descriptor):
        reasons.append(BLOCKED_PRE_2024_WINDOW)
    deduped = sorted(set(reasons))
    status = ACCEPTED_FOR_STRICT_VALIDATION_PLANNING if not deduped else "blocked"
    return status, deduped, _warning_reasons(source_trial_context, descriptor)


def _descriptor_preflight_row(
    descriptor: dict[str, Any],
    *,
    source_bundle_id: str,
    source_bundle_path: Path,
) -> dict[str, Any]:
    require_sandbox_boundary(descriptor, payload_name="sandbox_strict_validation_descriptor_preflight_descriptor")
    _require_descriptor_only_mode(
        descriptor,
        payload_name="sandbox_strict_validation_descriptor_preflight_descriptor",
    )
    source_trial_context = _as_dict(descriptor.get("source_trial_context"))
    source_market_source = _as_dict(descriptor.get("source_market_source")) or _as_dict(
        source_trial_context.get("market_source")
    )
    execution_assumptions = _as_dict(source_trial_context.get("execution_assumptions"))
    source_metrics = _as_dict(descriptor.get("source_metrics"))
    status, blocker_reasons, warning_reasons = _descriptor_status(descriptor)
    row_identity = {
        "schema_version": STRICT_VALIDATION_DESCRIPTOR_PREFLIGHT_SCHEMA_VERSION,
        "source_bundle_id": source_bundle_id,
        "descriptor_id": descriptor.get("descriptor_id"),
        "source_request_id": descriptor.get("source_request_id"),
        "source_trial_id": descriptor.get("source_trial_id"),
        "status": status,
        "blocker_reasons": blocker_reasons,
    }
    row = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_strict_validation_descriptor_preflight_row",
        "schema_version": STRICT_VALIDATION_DESCRIPTOR_PREFLIGHT_SCHEMA_VERSION,
        "preflight_row_id": digest_payload(row_identity, prefix="sbxstrictprefrow", length=24),
        "source_bundle_id": source_bundle_id,
        "source_bundle_path": str(source_bundle_path),
        "descriptor_id": descriptor.get("descriptor_id"),
        "source_request_id": descriptor.get("source_request_id"),
        "source_run_id": descriptor.get("source_run_id"),
        "source_trial_id": descriptor.get("source_trial_id"),
        "suite_id": descriptor.get("suite_id"),
        "case_id": descriptor.get("case_id"),
        "hypothesis_id": descriptor.get("hypothesis_id"),
        "family": descriptor.get("family"),
        "venue": descriptor.get("venue") or source_trial_context.get("venue"),
        "symbol": descriptor.get("symbol") or source_trial_context.get("symbol"),
        "data_family": source_trial_context.get("data_family"),
        "requested_validation": descriptor.get("requested_validation"),
        "required_evidence": _as_list(descriptor.get("required_evidence")),
        "strict_validation_entrypoint": STRICT_VALIDATION_ENTRYPOINT,
        "strict_validation_command": STRICT_VALIDATION_COMMAND,
        "execution_mode": DESCRIPTOR_EXECUTION_MODE,
        "descriptor_only": True,
        "strict_validation_preflight_only": True,
        "accepted_for_strict_validation_planning": status == ACCEPTED_FOR_STRICT_VALIDATION_PLANNING,
        "preflight_status": status,
        "blocker_reasons": blocker_reasons,
        "warning_reasons": warning_reasons,
        "strict_validation_executed": False,
        "strict_validation_authorized": False,
        "candidate_pack_written": False,
        "candidate_pack_write_authorized": False,
        "candidate_pack_paths": [],
        "source_metrics": source_metrics,
        "source_trial_context": source_trial_context,
        "source_venue_descriptor_id": (
            descriptor.get("source_venue_descriptor_id")
            or source_trial_context.get("venue_descriptor_id")
            or source_market_source.get("descriptor_id")
        ),
        "source_market_start": source_trial_context.get("market_start") or descriptor.get("source_market_start"),
        "source_market_end": source_trial_context.get("market_end") or descriptor.get("source_market_end"),
        "source_market_source": source_market_source,
        "source_integrity": source_market_source.get("source_integrity") or source_trial_context.get("source_integrity"),
        "source_integrity_present": bool(
            source_market_source.get("source_integrity") or source_trial_context.get("source_integrity")
        ),
        "execution_assumptions": execution_assumptions,
        "exit_profile": source_trial_context.get("exit_profile") or execution_assumptions.get("exit_profile"),
        "exit_variant_id": source_trial_context.get("exit_variant_id") or execution_assumptions.get("exit_variant_id"),
        "filter_variant_id": source_trial_context.get("filter_variant_id")
        or execution_assumptions.get("filter_variant_id"),
        "source_descriptor_payload": descriptor,
    }
    require_sandbox_boundary(row, payload_name="sandbox_strict_validation_descriptor_preflight_row")
    return row


def _preflight_id(source_bundle_id: str, rows: list[dict[str, Any]]) -> str:
    return digest_payload(
        {
            "schema_version": STRICT_VALIDATION_DESCRIPTOR_PREFLIGHT_SCHEMA_VERSION,
            "source_bundle_id": source_bundle_id,
            "rows": [
                {
                    "preflight_row_id": row.get("preflight_row_id"),
                    "descriptor_id": row.get("descriptor_id"),
                    "source_trial_id": row.get("source_trial_id"),
                    "preflight_status": row.get("preflight_status"),
                    "blocker_reasons": row.get("blocker_reasons"),
                }
                for row in rows
            ],
        },
        prefix="sbxstrictpreflight",
        length=24,
    )


def _count_reasons(rows: list[dict[str, Any]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        counter.update(str(reason) for reason in _as_list(row.get("blocker_reasons")))
    return dict(sorted(counter.items()))


def preflight_sandbox_strict_validation_descriptors(
    bundle_path: str | Path,
    *,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    source_bundle_path = Path(bundle_path).expanduser().resolve()
    payload = _load_json(source_bundle_path)
    if not isinstance(payload, dict):
        raise ValueError("sandbox strict-validation descriptor preflight bundle must be a JSON object")
    require_sandbox_boundary(payload, payload_name="sandbox_strict_validation_descriptor_preflight_bundle")
    _require_descriptor_only_mode(
        payload,
        payload_name="sandbox_strict_validation_descriptor_preflight_bundle",
    )
    descriptors = payload.get("descriptors")
    if not isinstance(descriptors, list):
        raise ValueError("sandbox strict-validation descriptor preflight bundle requires descriptors list")
    source_bundle_id = str(payload.get("bundle_id") or "")
    if not source_bundle_id:
        raise ValueError("sandbox strict-validation descriptor preflight bundle requires bundle_id")

    rows = [
        _descriptor_preflight_row(
            dict(descriptor),
            source_bundle_id=source_bundle_id,
            source_bundle_path=source_bundle_path,
        )
        for descriptor in descriptors
        if isinstance(descriptor, dict)
    ]
    if len(rows) != len(descriptors):
        raise ValueError("sandbox strict-validation descriptor preflight descriptors must be objects")
    preflight_id = _preflight_id(source_bundle_id, rows)
    for row in rows:
        row["preflight_id"] = preflight_id
    status_counts = dict(sorted(Counter(str(row.get("preflight_status")) for row in rows).items()))
    blocker_counts = _count_reasons(rows)

    destination = (Path(output_dir) if output_dir is not None else source_bundle_path.parent) / preflight_id
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / STRICT_VALIDATION_DESCRIPTOR_PREFLIGHT_JSON_NAME
    parquet_path = destination / STRICT_VALIDATION_DESCRIPTOR_PREFLIGHT_PARQUET_NAME
    frame = pd.DataFrame([_row_for_parquet(row) for row in rows])
    if frame.empty:
        frame = pd.DataFrame(
            columns=["preflight_id", "preflight_row_id", "preflight_status", *SANDBOX_BOUNDARY_FLAGS]
        )
    frame.to_parquet(parquet_path, index=False)
    result = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_strict_validation_descriptor_preflight",
        "schema_version": STRICT_VALIDATION_DESCRIPTOR_PREFLIGHT_SCHEMA_VERSION,
        "preflight_id": preflight_id,
        "source_bundle_id": source_bundle_id,
        "source_bundle_path": str(source_bundle_path),
        "strict_validation_entrypoint": STRICT_VALIDATION_ENTRYPOINT,
        "strict_validation_command": STRICT_VALIDATION_COMMAND,
        "execution_mode": DESCRIPTOR_EXECUTION_MODE,
        "descriptor_only": True,
        "strict_validation_preflight_only": True,
        "strict_validation_executed": False,
        "strict_validation_authorized": False,
        "candidate_pack_written": False,
        "candidate_pack_write_authorized": False,
        "candidate_pack_paths": [],
        "descriptor_count": len(rows),
        "accepted_descriptor_count": status_counts.get(ACCEPTED_FOR_STRICT_VALIDATION_PLANNING, 0),
        "blocked_descriptor_count": status_counts.get("blocked", 0),
        "status_counts": status_counts,
        "blocker_reason_counts": blocker_counts,
        "preflight_json_path": str(json_path),
        "preflight_parquet_path": str(parquet_path),
        "descriptors": rows,
    }
    require_sandbox_boundary(result, payload_name="sandbox_strict_validation_descriptor_preflight")
    json_path.write_text(
        json.dumps(result, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    return result
