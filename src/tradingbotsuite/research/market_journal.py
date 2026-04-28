from __future__ import annotations

import hashlib
import json
import math
import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tradingbotsuite.research.live_readiness import research_boundary_metadata

MARKET_JOURNAL_SCHEMA_VERSION = "binance-market-journal-v1"
MARKET_JOURNAL_WRITER_VERSION = "binance-market-journal-writer-v1"
SUPPORTED_MARKET_JOURNAL_SYMBOLS = frozenset({"BTCUSDT", "ETHUSDT"})
SUPPORTED_MARKET_JOURNAL_FAMILIES = frozenset(
    {
        "agg_trade",
        "trade",
        "kline",
        "book_ticker",
        "depth",
        "mark_price",
        "funding",
        "open_interest",
        "force_order",
    }
)


class MarketJournalValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class MarketJournalWriteResult:
    journal_path: Path
    manifest_path: Path
    event_count: int
    journal_hash: str
    manifest_hash: str


def build_market_journal_event(
    *,
    raw_payload: Mapping[str, Any],
    normalized_payload: Mapping[str, Any],
    source_event_time_ms: int,
    local_receive_time_ms: int | None,
    source_name: str,
    symbol: str,
    data_family: str,
    source_row_index: int,
    sequence: int | None = None,
    schema_version: str = MARKET_JOURNAL_SCHEMA_VERSION,
) -> dict[str, Any]:
    event = {
        "raw_payload": _normalize_payload(raw_payload),
        "normalized_payload": _normalize_payload(normalized_payload),
        "source_event_time_ms": int(source_event_time_ms),
        "local_receive_time_ms": int(local_receive_time_ms) if local_receive_time_ms is not None else None,
        "source_name": _normalize_source_name(source_name),
        "symbol": _normalize_symbol(symbol),
        "data_family": _normalize_data_family(data_family),
        "schema_version": str(schema_version),
        "sequence": int(sequence) if sequence is not None else None,
        "source_row_index": int(source_row_index),
    }
    event["payload_hash"] = _payload_hash(event)
    return validate_market_journal_event(event)


def validate_market_journal_event(event: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(_normalize_payload(event))
    errors: list[str] = []

    if normalized.get("schema_version") != MARKET_JOURNAL_SCHEMA_VERSION:
        errors.append("schema_version_must_match_market_journal_contract")

    raw_payload = normalized.get("raw_payload")
    normalized_payload = normalized.get("normalized_payload")
    if not isinstance(raw_payload, Mapping):
        errors.append("raw_payload_required")
    if not isinstance(normalized_payload, Mapping):
        errors.append("normalized_payload_required")

    source_event_time_ms = _int_or_none(normalized.get("source_event_time_ms"))
    if source_event_time_ms is None:
        errors.append("source_event_time_ms_required")
    elif source_event_time_ms < 0:
        errors.append("source_event_time_ms_must_be_non_negative")

    local_receive_time_ms = normalized.get("local_receive_time_ms")
    if local_receive_time_ms is not None:
        receive_time = _int_or_none(local_receive_time_ms)
        if receive_time is None:
            errors.append("local_receive_time_ms_must_be_integer_or_null")
        elif receive_time < 0:
            errors.append("local_receive_time_ms_must_be_non_negative")

    source_name = _optional_str(normalized.get("source_name"))
    if source_name is None:
        errors.append("source_name_required")
    symbol = _optional_str(normalized.get("symbol"))
    if symbol is None:
        errors.append("symbol_required")
    else:
        try:
            normalized["symbol"] = _normalize_symbol(symbol)
        except ValueError as exc:
            errors.append(str(exc))
    data_family = _optional_str(normalized.get("data_family"))
    if data_family is None:
        errors.append("data_family_required")
    else:
        try:
            normalized["data_family"] = _normalize_data_family(data_family)
        except ValueError as exc:
            errors.append(str(exc))

    sequence = normalized.get("sequence")
    if sequence is not None:
        sequence_value = _int_or_none(sequence)
        if sequence_value is None:
            errors.append("sequence_must_be_integer_or_null")
        elif sequence_value < 0:
            errors.append("sequence_must_be_non_negative")
        else:
            normalized["sequence"] = sequence_value

    source_row_index = _int_or_none(normalized.get("source_row_index"))
    if source_row_index is None:
        errors.append("source_row_index_required")
    elif source_row_index < 0:
        errors.append("source_row_index_must_be_non_negative")
    else:
        normalized["source_row_index"] = source_row_index

    if isinstance(normalized_payload, Mapping):
        errors.extend(_payload_mismatch_errors(normalized, normalized_payload))
    if isinstance(raw_payload, Mapping):
        errors.extend(_payload_mismatch_errors(normalized, raw_payload, raw=True))

    payload_hash = _optional_str(normalized.get("payload_hash"))
    if payload_hash is None:
        errors.append("payload_hash_required")
    elif payload_hash != _payload_hash(normalized):
        errors.append("payload_hash_mismatch")

    if errors:
        raise MarketJournalValidationError("; ".join(errors))
    return normalized


def validate_market_journal_events(
    events: Iterable[Mapping[str, Any]],
    *,
    strict: bool = True,
) -> dict[str, Any]:
    validation_errors: list[dict[str, Any]] = []
    validated_events: list[dict[str, Any]] = []
    for index, event in enumerate(events):
        try:
            validated_events.append(validate_market_journal_event(event))
        except MarketJournalValidationError as exc:
            validation_errors.append({"event_index": index, "error": str(exc)})

    duplicate_hashes = _duplicate_payload_hashes(validated_events)
    sequence_gaps = _sequence_gaps(validated_events)
    errors = list(validation_errors)
    if duplicate_hashes:
        errors.append({"error": "duplicate_payload_hashes", "payload_hashes": duplicate_hashes})
    if sequence_gaps:
        errors.append({"error": "sequence_gaps", "gaps": sequence_gaps})

    report = {
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "schema_version": MARKET_JOURNAL_SCHEMA_VERSION,
        "event_count": len(validated_events),
        "valid": not errors,
        "errors": errors,
        "duplicate_hashes": duplicate_hashes,
        "sequence_gaps": sequence_gaps,
    }
    if strict and errors:
        raise MarketJournalValidationError("; ".join(str(error) for error in errors))
    return report


class MarketJournalWriter:
    """Append-only JSONL writer for research Binance-style market events."""

    def __init__(self, journal_path: Path | str, manifest_path: Path | str | None = None) -> None:
        self.journal_path = Path(journal_path)
        self.manifest_path = (
            Path(manifest_path)
            if manifest_path is not None
            else self.journal_path.with_suffix(self.journal_path.suffix + ".manifest.json")
        )
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        self._next_source_row_index = _line_count(self.journal_path)

    def append(
        self,
        *,
        raw_payload: Mapping[str, Any],
        normalized_payload: Mapping[str, Any],
        source_event_time_ms: int,
        local_receive_time_ms: int | None,
        source_name: str,
        symbol: str,
        data_family: str,
        sequence: int | None = None,
        source_row_index: int | None = None,
    ) -> dict[str, Any]:
        row_index = self._next_source_row_index if source_row_index is None else int(source_row_index)
        event = build_market_journal_event(
            raw_payload=raw_payload,
            normalized_payload=normalized_payload,
            source_event_time_ms=source_event_time_ms,
            local_receive_time_ms=local_receive_time_ms,
            source_name=source_name,
            symbol=symbol,
            data_family=data_family,
            sequence=sequence,
            source_row_index=row_index,
        )
        with self.journal_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(_canonical_json(event) + "\n")
        self._next_source_row_index = max(self._next_source_row_index, row_index + 1)
        return event

    def write_manifest(self, *, strict: bool = False) -> dict[str, Any]:
        manifest = build_market_journal_manifest(self.journal_path, strict=strict)
        self.manifest_path.write_text(_canonical_json(manifest, indent=2) + "\n", encoding="utf-8")
        return manifest


def append_market_journal_events(
    journal_path: Path | str,
    events: Iterable[Mapping[str, Any]],
    *,
    manifest_path: Path | str | None = None,
    strict_manifest: bool = False,
) -> MarketJournalWriteResult:
    writer = MarketJournalWriter(journal_path, manifest_path=manifest_path)
    for event in events:
        writer.append(
            raw_payload=_mapping_value(event, "raw_payload"),
            normalized_payload=_mapping_value(event, "normalized_payload"),
            source_event_time_ms=int(event["source_event_time_ms"]),
            local_receive_time_ms=_int_or_none(event.get("local_receive_time_ms")),
            source_name=str(event["source_name"]),
            symbol=str(event["symbol"]),
            data_family=str(event["data_family"]),
            sequence=_int_or_none(event.get("sequence")),
            source_row_index=_int_or_none(event.get("source_row_index")),
        )
    manifest = writer.write_manifest(strict=strict_manifest)
    return MarketJournalWriteResult(
        journal_path=writer.journal_path,
        manifest_path=writer.manifest_path,
        event_count=int(manifest["event_count"]),
        journal_hash=str(manifest["journal_hash"]),
        manifest_hash=str(manifest["manifest_hash"]),
    )


def read_market_journal_events(
    journal_path: Path | str,
    *,
    validate: bool = True,
) -> list[dict[str, Any]]:
    events = _read_jsonl_events(Path(journal_path))
    if not validate:
        return events
    validate_market_journal_events(events, strict=True)
    return [validate_market_journal_event(event) for event in events]


def read_market_journal_for_replay(
    journal_path: Path | str,
    *,
    manifest_path: Path | str | None = None,
    validate_manifest: bool = True,
) -> list[dict[str, Any]]:
    journal_path = Path(journal_path)
    if validate_manifest:
        resolved_manifest_path = (
            Path(manifest_path)
            if manifest_path is not None
            else journal_path.with_suffix(journal_path.suffix + ".manifest.json")
        )
        manifest = json.loads(resolved_manifest_path.read_text(encoding="utf-8"))
        actual_hash = _hash_file(journal_path)
        if manifest.get("journal_hash") != actual_hash:
            raise MarketJournalValidationError(
                f"journal hash mismatch: expected {manifest.get('journal_hash')}, observed {actual_hash}"
            )
    return sorted(read_market_journal_events(journal_path), key=_replay_sort_key)


def build_market_journal_manifest(journal_path: Path | str, *, strict: bool = False) -> dict[str, Any]:
    journal_path = Path(journal_path)
    events = read_market_journal_events(journal_path, validate=False)
    report = validate_market_journal_events(events, strict=strict)
    event_times = [_int_or_none(event.get("source_event_time_ms")) for event in events]
    receive_times = [_int_or_none(event.get("local_receive_time_ms")) for event in events]
    manifest = {
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "schema_version": MARKET_JOURNAL_SCHEMA_VERSION,
        "writer_version": MARKET_JOURNAL_WRITER_VERSION,
        "journal_type": "binance_style_market_event_journal",
        "journal_path": str(journal_path),
        "journal_hash": _hash_file(journal_path),
        "event_count": len(events),
        "event_counts_by_source": _counts_by(events, "source_name"),
        "event_counts_by_symbol": _counts_by(events, "symbol"),
        "event_counts_by_family": _counts_by(events, "data_family"),
        "first_source_event_time_ms": _min_or_none(event_times),
        "last_source_event_time_ms": _max_or_none(event_times),
        "first_local_receive_time_ms": _min_or_none(receive_times),
        "last_local_receive_time_ms": _max_or_none(receive_times),
        "duplicate_hash_count": len(report["duplicate_hashes"]),
        "duplicate_hashes": report["duplicate_hashes"],
        "sequence_gap_count": len(report["sequence_gaps"]),
        "sequence_gaps": report["sequence_gaps"],
        "validation_errors": report["errors"],
        "replay_order": ["source_event_time_ms", "sequence", "source_row_index", "payload_hash"],
        "manifest_generated_at_ms": int(time.time() * 1000),
        "non_promotable_notes": [
            "Research-only append-only Binance-style market event journal.",
            "This journal is a replay/data-quality contract only and is not Hyperliquid fillability evidence.",
            "No DB indexes, live runtime hooks, operator controls, or execution behavior are modified by this module.",
        ],
    }
    manifest["manifest_hash"] = _hash_payload(
        {key: value for key, value in manifest.items() if key != "manifest_generated_at_ms"}
    )
    return manifest


def _payload_hash(event: Mapping[str, Any]) -> str:
    material = {
        "raw_payload": event.get("raw_payload"),
        "normalized_payload": event.get("normalized_payload"),
        "source_event_time_ms": event.get("source_event_time_ms"),
        "source_name": event.get("source_name"),
        "symbol": event.get("symbol"),
        "data_family": event.get("data_family"),
        "schema_version": event.get("schema_version"),
        "sequence": event.get("sequence"),
    }
    return _hash_payload(material)


def _payload_mismatch_errors(event: Mapping[str, Any], payload: Mapping[str, Any], *, raw: bool = False) -> list[str]:
    errors: list[str] = []
    symbol_value = _first_present(payload, ("symbol", "s"))
    if symbol_value is not None and _optional_str(symbol_value) != event.get("symbol"):
        errors.append("raw_symbol_mismatch" if raw else "symbol_mismatch")
    source_value = _first_present(payload, ("source_name", "source"))
    if source_value is not None and _optional_str(source_value) != event.get("source_name"):
        errors.append("raw_source_mismatch" if raw else "source_mismatch")
    family_value = _first_present(payload, ("data_family", "event_type"))
    if family_value is not None:
        try:
            normalized_family = _normalize_data_family(str(family_value))
        except ValueError:
            normalized_family = str(family_value)
        if normalized_family != event.get("data_family"):
            errors.append("raw_data_family_mismatch" if raw else "data_family_mismatch")
    return errors


def _duplicate_payload_hashes(events: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for event in events:
        payload_hash = str(event.get("payload_hash"))
        if payload_hash in seen:
            duplicates.add(payload_hash)
        seen.add(payload_hash)
    return sorted(duplicates)


def _sequence_gaps(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_stream: dict[tuple[str, str, str], list[int]] = {}
    for event in events:
        sequence = _int_or_none(event.get("sequence"))
        if sequence is None:
            continue
        key = (str(event["source_name"]), str(event["symbol"]), str(event["data_family"]))
        by_stream.setdefault(key, []).append(sequence)

    gaps: list[dict[str, Any]] = []
    for (source_name, symbol, data_family), sequences in sorted(by_stream.items()):
        ordered = sorted(set(sequences))
        for previous, current in zip(ordered, ordered[1:]):
            if current != previous + 1:
                gaps.append(
                    {
                        "source_name": source_name,
                        "symbol": symbol,
                        "data_family": data_family,
                        "previous_sequence": previous,
                        "next_sequence": current,
                        "missing_sequence_count": current - previous - 1,
                    }
                )
    return gaps


def _replay_sort_key(event: Mapping[str, Any]) -> tuple[Any, ...]:
    sequence = _int_or_none(event.get("sequence"))
    return (
        int(event["source_event_time_ms"]),
        sequence if sequence is not None else math.inf,
        int(event["source_row_index"]),
        str(event["payload_hash"]),
    )


def _normalize_source_name(source_name: str) -> str:
    normalized = str(source_name).strip().lower().replace("-", "_")
    if not normalized:
        raise ValueError("source_name_required")
    return normalized


def _normalize_symbol(symbol: str) -> str:
    normalized = str(symbol).strip().upper()
    if normalized not in SUPPORTED_MARKET_JOURNAL_SYMBOLS:
        raise ValueError(f"symbol must be one of: {', '.join(sorted(SUPPORTED_MARKET_JOURNAL_SYMBOLS))}")
    return normalized


def _normalize_data_family(data_family: str) -> str:
    normalized = str(data_family).strip().lower().replace("-", "_")
    aliases = {
        "aggtrade": "agg_trade",
        "aggtrades": "agg_trade",
        "agg_trades": "agg_trade",
        "bookticker": "book_ticker",
        "markprice": "mark_price",
        "openinterest": "open_interest",
        "forceorder": "force_order",
        "liquidation": "force_order",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in SUPPORTED_MARKET_JOURNAL_FAMILIES:
        raise ValueError(f"data_family must be one of: {', '.join(sorted(SUPPORTED_MARKET_JOURNAL_FAMILIES))}")
    return normalized


def _read_jsonl_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise MarketJournalValidationError(f"invalid JSONL at {path}:{line_number}") from exc
            if not isinstance(event, dict):
                raise MarketJournalValidationError(f"journal event must be an object at {path}:{line_number}")
            events.append(event)
    return events


def _line_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _mapping_value(mapping: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = mapping.get(key)
    if not isinstance(value, Mapping):
        raise MarketJournalValidationError(f"{key}_required")
    return value


def _counts_by(events: list[Mapping[str, Any]], field_name: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        value = str(event.get(field_name) or "missing")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _first_present(payload: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return None


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _hash_payload(payload: Any) -> str:
    return f"sha256:{hashlib.sha256(_canonical_json(payload).encode('utf-8')).hexdigest()}"


def _canonical_json(payload: Any, *, indent: int | None = None) -> str:
    return json.dumps(
        _normalize_payload(payload),
        sort_keys=True,
        separators=(",", ":") if indent is None else None,
        indent=indent,
        ensure_ascii=True,
    )


def _normalize_payload(payload: Any) -> Any:
    if isinstance(payload, Mapping):
        return {str(key): _normalize_payload(value) for key, value in payload.items()}
    if isinstance(payload, list | tuple):
        return [_normalize_payload(value) for value in payload]
    if isinstance(payload, set | frozenset):
        return sorted((_normalize_payload(value) for value in payload), key=lambda value: _canonical_json(value))
    if isinstance(payload, bytes):
        return payload.hex()
    if payload is None or isinstance(payload, str | int | float | bool):
        return payload
    return str(payload)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
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
