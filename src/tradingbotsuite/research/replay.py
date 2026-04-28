from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Iterable, Literal, Mapping

ReplayOrderMode = Literal["source_time", "receive_time"]

REPLAY_CONTRACT_VERSION = "research-replay-determinism-v1"
SOURCE_TIME_FIELDS = ("source_event_time_ms", "event_time_ms", "time_ms")
RECEIVE_TIME_FIELDS = ("receive_time_ms",)
TIE_BREAKER_FIELDS = (
    "source_name",
    "symbol",
    "data_family",
    "event_type",
    "schema_version",
    "payload_hash",
    "source_row_index",
    "aggregate_trade_id",
    "trade_id",
    "cloid",
    "signal_id",
)


class ReplayDeterminismError(ValueError):
    pass


def order_replay_events(
    events: Iterable[Mapping[str, Any]],
    *,
    order_by: ReplayOrderMode = "source_time",
) -> list[dict[str, Any]]:
    """Return events in deterministic replay order.

    This is an offline research helper. It does not read exchanges, mutate
    runtime state, or make promotion decisions.
    """

    normalized = [_normalize_event(event) for event in events]
    return sorted(normalized, key=lambda event: _sort_key(event, order_by=order_by))


def hash_replay_events(
    events: Iterable[Mapping[str, Any]],
    *,
    order_by: ReplayOrderMode = "source_time",
) -> dict[str, Any]:
    ordered_events = order_replay_events(events, order_by=order_by)
    ordered_hashes = [_event_hash(event) for event in ordered_events]
    digest_material = {
        "contract_version": REPLAY_CONTRACT_VERSION,
        "order_by": order_by,
        "ordered_event_hashes": ordered_hashes,
    }
    return {
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "contract_version": REPLAY_CONTRACT_VERSION,
        "order_by": order_by,
        "event_count": len(ordered_events),
        "sha256": _sha256_hex(digest_material),
        "ordered_event_hashes": ordered_hashes,
        "ordered_events": ordered_events,
    }


def compare_replay_runs(
    left_events: Iterable[Mapping[str, Any]],
    right_events: Iterable[Mapping[str, Any]],
    *,
    order_by: ReplayOrderMode = "source_time",
) -> dict[str, Any]:
    left = hash_replay_events(left_events, order_by=order_by)
    right = hash_replay_events(right_events, order_by=order_by)
    first_mismatch_index = _first_mismatch_index(left["ordered_event_hashes"], right["ordered_event_hashes"])
    return {
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "contract_version": REPLAY_CONTRACT_VERSION,
        "order_by": order_by,
        "match": left["sha256"] == right["sha256"],
        "left_sha256": left["sha256"],
        "right_sha256": right["sha256"],
        "left_event_count": left["event_count"],
        "right_event_count": right["event_count"],
        "first_mismatch_index": first_mismatch_index,
        "first_mismatch": _first_mismatch(left, right, first_mismatch_index),
    }


def _sort_key(event: Mapping[str, Any], *, order_by: ReplayOrderMode) -> tuple[Any, ...]:
    if order_by == "source_time":
        primary = _required_timestamp(event, SOURCE_TIME_FIELDS, mode=order_by)
        secondary = _optional_timestamp(event, RECEIVE_TIME_FIELDS)
    elif order_by == "receive_time":
        primary = _required_timestamp(event, RECEIVE_TIME_FIELDS, mode=order_by)
        secondary = _optional_timestamp(event, SOURCE_TIME_FIELDS)
    else:
        raise ReplayDeterminismError(f"unsupported replay order mode: {order_by}")

    return (
        primary,
        secondary if secondary is not None else math.inf,
        *(_tie_value(event, field_name) for field_name in TIE_BREAKER_FIELDS),
        _event_hash(event),
    )


def _required_timestamp(event: Mapping[str, Any], field_names: tuple[str, ...], *, mode: ReplayOrderMode) -> int:
    for field_name in field_names:
        value = event.get(field_name)
        if value is None:
            continue
        timestamp = _int_or_none(value)
        if timestamp is None:
            raise ReplayDeterminismError(f"{field_name} must be an integer timestamp for replay order {mode}")
        if timestamp < 0:
            raise ReplayDeterminismError(f"{field_name} must be non-negative for replay order {mode}")
        return timestamp
    raise ReplayDeterminismError(f"missing required timestamp for replay order {mode}: one of {', '.join(field_names)}")


def _optional_timestamp(event: Mapping[str, Any], field_names: tuple[str, ...]) -> int | None:
    for field_name in field_names:
        value = event.get(field_name)
        if value is None:
            continue
        timestamp = _int_or_none(value)
        if timestamp is None or timestamp < 0:
            return None
        return timestamp
    return None


def _tie_value(event: Mapping[str, Any], field_name: str) -> tuple[int, str]:
    value = event.get(field_name)
    if value is None:
        return (1, "")
    return (0, _canonical_json(value))


def _event_hash(event: Mapping[str, Any]) -> str:
    return _sha256_hex(_normalize_event(event))


def _sha256_hex(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _canonical_json(payload: Any) -> str:
    return json.dumps(_normalize_payload(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _normalize_event(event: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(event, Mapping):
        raise ReplayDeterminismError("replay events must be mappings")
    normalized = _normalize_payload(event)
    if not isinstance(normalized, dict):
        raise ReplayDeterminismError("replay events must normalize to dictionaries")
    return normalized


def _normalize_payload(payload: Any) -> Any:
    if isinstance(payload, Mapping):
        return {str(key): _normalize_payload(value) for key, value in payload.items()}
    if isinstance(payload, list | tuple):
        return [_normalize_payload(value) for value in payload]
    if isinstance(payload, set | frozenset):
        return sorted((_normalize_payload(value) for value in payload), key=_canonical_json)
    if isinstance(payload, bytes):
        return payload.hex()
    if payload is None or isinstance(payload, str | int | float | bool):
        return payload
    return str(payload)


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _first_mismatch_index(left_hashes: list[str], right_hashes: list[str]) -> int | None:
    for index, (left_hash, right_hash) in enumerate(zip(left_hashes, right_hashes)):
        if left_hash != right_hash:
            return index
    if len(left_hashes) != len(right_hashes):
        return min(len(left_hashes), len(right_hashes))
    return None


def _first_mismatch(left: Mapping[str, Any], right: Mapping[str, Any], index: int | None) -> dict[str, Any] | None:
    if index is None:
        return None
    left_hashes = left["ordered_event_hashes"]
    right_hashes = right["ordered_event_hashes"]
    left_events = left["ordered_events"]
    right_events = right["ordered_events"]
    return {
        "index": index,
        "left_event_hash": left_hashes[index] if index < len(left_hashes) else None,
        "right_event_hash": right_hashes[index] if index < len(right_hashes) else None,
        "left_event": left_events[index] if index < len(left_events) else None,
        "right_event": right_events[index] if index < len(right_events) else None,
    }
