from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "hyperliquid-execution-journal-v1"

EVENT_TYPES = frozenset(
    {
        "order_intent",
        "order_submitted",
        "order_acknowledged",
        "order_rejected",
        "order_partially_filled",
        "order_filled",
        "order_cancel_requested",
        "order_cancel_acknowledged",
        "position_snapshot",
        "funding_payment",
        "reconciliation",
        "schedule_cancel_set",
        "schedule_cancel_triggered",
    }
)

ORDER_EVENT_TYPES = frozenset(event_type for event_type in EVENT_TYPES if event_type.startswith("order_"))
SYMBOL_SCOPED_EVENT_TYPES = ORDER_EVENT_TYPES | frozenset({"position_snapshot", "funding_payment"})
ENVELOPE_HASH_EXCLUDE_FIELDS = frozenset(
    {
        "schema_version",
        "event_type",
        "source_event_time_ms",
        "receive_time_ms",
        "receive_time_unavailable_reason",
        "source_row_index",
        "payload_hash",
        "raw_payload",
        "payload",
    }
)


class ExecutionJournalValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ExecutionJournalWriteResult:
    data_path: Path
    manifest_path: Path
    row_count: int
    sha256: str
    manifest_hash: str


def deterministic_cloid(*parts: object, prefix: str = "tbs") -> str:
    """Build a deterministic Hyperliquid-compatible client order id.

    The return shape is `0x` plus 32 hex characters so it can be used as a
    future Cloid value without importing Hyperliquid runtime dependencies.
    """

    if not parts:
        raise ValueError("at least one cloid input part is required")
    material = _canonical_json({"prefix": prefix, "parts": [str(part) for part in parts]})
    return "0x" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]


def payload_hash(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def validate_event(event: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(event)
    errors: list[str] = []

    event_type = _optional_str(normalized.get("event_type"))
    if event_type not in EVENT_TYPES:
        errors.append(f"unsupported_event_type:{event_type}")

    if normalized.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_must_match_execution_journal_contract")

    _validate_int_field(normalized, "source_event_time_ms", errors, required=True)
    receive_time_ms = _validate_int_field(normalized, "receive_time_ms", errors, required=False)
    receive_unavailable_reason = _optional_str(normalized.get("receive_time_unavailable_reason"))
    if receive_time_ms is None and receive_unavailable_reason is None:
        errors.append("receive_time_ms_or_unavailable_reason_required")

    if event_type in SYMBOL_SCOPED_EVENT_TYPES or (event_type == "reconciliation" and normalized.get("scope") != "account"):
        if _optional_str(normalized.get("symbol")) is None:
            errors.append("symbol_required_for_symbol_scoped_event")

    if event_type in ORDER_EVENT_TYPES:
        _validate_order_cloid(normalized, event_type, errors)

    if normalized.get("exit_intent") is True and normalized.get("reduce_only") is not True:
        errors.append("exit_intent_requires_reduce_only_true")

    raw_payload = normalized.get("raw_payload")
    payload = normalized.get("payload")
    existing_payload_hash = _optional_str(normalized.get("payload_hash"))
    hash_material = _hash_material_from_event(normalized)
    if existing_payload_hash is not None:
        if len(existing_payload_hash) != 64:
            errors.append("payload_hash_must_be_sha256_hex")
    elif raw_payload is not None:
        normalized["payload_hash"] = payload_hash(raw_payload)
    elif payload is not None:
        normalized["payload_hash"] = payload_hash(payload)
    elif hash_material:
        normalized["payload_hash"] = payload_hash(hash_material)
    else:
        errors.append("payload_hash_raw_payload_or_hashable_fields_required")

    source_row_index = normalized.get("source_row_index")
    if source_row_index is not None and _int_or_none(source_row_index) is None:
        errors.append("source_row_index_must_be_integer")

    if errors:
        raise ExecutionJournalValidationError("; ".join(errors))
    return normalized


def append_journal_events(
    data_path: Path | str,
    events: Iterable[Mapping[str, Any]],
    *,
    manifest_path: Path | str | None = None,
) -> ExecutionJournalWriteResult:
    path = Path(data_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    validated_events = [validate_event(event) for event in events]
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for event in validated_events:
            handle.write(_canonical_json(event) + "\n")

    manifest_target = Path(manifest_path) if manifest_path is not None else path.with_suffix(path.suffix + ".manifest.json")
    manifest = build_journal_manifest(path)
    manifest_target.write_text(_canonical_json(manifest, indent=2) + "\n", encoding="utf-8")
    return ExecutionJournalWriteResult(
        data_path=path,
        manifest_path=manifest_target,
        row_count=int(manifest["row_count"]),
        sha256=str(manifest["sha256"]),
        manifest_hash=str(manifest["manifest_hash"]),
    )


def read_journal_events(data_path: Path | str, *, validate: bool = True) -> list[dict[str, Any]]:
    path = Path(data_path)
    events: list[dict[str, Any]] = []
    if not path.exists():
        return events
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        events.append(validate_event(event) if validate else event)
    return events


def replay_order(events: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    indexed_events = [(index, validate_event(event)) for index, event in enumerate(events)]
    indexed_events.sort(key=lambda item: _replay_sort_key(item[1], item[0]))
    return [event for _, event in indexed_events]


def read_journal_for_replay(data_path: Path | str) -> list[dict[str, Any]]:
    return replay_order(read_journal_events(data_path))


def build_journal_manifest(data_path: Path | str) -> dict[str, Any]:
    path = Path(data_path)
    events = read_journal_events(path)
    sha256 = _file_sha256(path)
    receive_times = [_int_or_none(event.get("receive_time_ms")) for event in events]
    source_times = [_int_or_none(event.get("source_event_time_ms")) for event in events]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "research_only": True,
        "journal_type": "hyperliquid_execution_account_journal",
        "data_path": str(path),
        "row_count": len(events),
        "sha256": sha256,
        "event_types": sorted({str(event.get("event_type")) for event in events}),
        "first_receive_time_ms": _min_or_none(receive_times),
        "last_receive_time_ms": _max_or_none(receive_times),
        "first_source_event_time_ms": _min_or_none(source_times),
        "last_source_event_time_ms": _max_or_none(source_times),
        "replay_order": ["receive_time_ms", "source_event_time_ms", "source_row_index"],
        "generated_at_ms": int(time.time() * 1000),
        "notes": [
            "Research-only execution/account journal contract.",
            "This module validates offline journal records only and does not place, cancel, size, or supervise live orders.",
            "Order events require deterministic cloid evidence except explicit pre-submit rejects.",
        ],
    }
    manifest["manifest_hash"] = payload_hash({key: value for key, value in manifest.items() if key != "generated_at_ms"})
    return manifest


def _validate_order_cloid(event: Mapping[str, Any], event_type: str, errors: list[str]) -> None:
    pre_submit_reject = event_type == "order_rejected" and event.get("pre_submit_reject") is True
    cloid = _optional_str(event.get("cloid"))
    if cloid is None:
        if not pre_submit_reject:
            errors.append("deterministic_cloid_required")
        return
    if not (
        event.get("cloid_deterministic") is True
        or _optional_str(event.get("cloid_strategy")) == "deterministic"
        or _optional_str(event.get("cloid_derivation")) is not None
    ):
        errors.append("deterministic_cloid_evidence_required")


def _validate_int_field(event: Mapping[str, Any], field_name: str, errors: list[str], *, required: bool) -> int | None:
    value = _int_or_none(event.get(field_name))
    if value is None:
        if required:
            errors.append(f"{field_name}_must_be_integer")
        return None
    if value < 0:
        errors.append(f"{field_name}_must_be_non_negative")
    return value


def _replay_sort_key(event: Mapping[str, Any], file_index: int) -> tuple[int | float, int | float, int | float]:
    receive_time_ms = _int_or_none(event.get("receive_time_ms"))
    source_event_time_ms = _int_or_none(event.get("source_event_time_ms"))
    source_row_index = _int_or_none(event.get("source_row_index"))
    return (
        receive_time_ms if receive_time_ms is not None else math.inf,
        source_event_time_ms if source_event_time_ms is not None else math.inf,
        source_row_index if source_row_index is not None else file_index,
    )


def _hash_material_from_event(event: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(key): value
        for key, value in sorted(event.items(), key=lambda item: str(item[0]))
        if key not in ENVELOPE_HASH_EXCLUDE_FIELDS and value is not None
    }


def _canonical_json(payload: Any, *, indent: int | None = None) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":") if indent is None else None, indent=indent, default=str)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    if not path.exists():
        return digest.hexdigest()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _min_or_none(values: Iterable[int | None]) -> int | None:
    present = [value for value in values if value is not None]
    return min(present) if present else None


def _max_or_none(values: Iterable[int | None]) -> int | None:
    present = [value for value in values if value is not None]
    return max(present) if present else None
