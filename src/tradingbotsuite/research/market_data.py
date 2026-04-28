from __future__ import annotations

import csv
import hashlib
import io
import json
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol

from tradingbotsuite.adapters.binance import INTERVAL_TO_MS, BinanceCandleClient
from tradingbotsuite.core.models import Bar
from tradingbotsuite.research.live_readiness import research_boundary_metadata

BINANCE_USDM_FAPI_URL = "https://fapi.binance.com"
COLLECTOR_VERSION = "binance-usdm-chart-bars-v1"
BINANCE_VISION_ARCHIVE_SCHEMA_VERSION = "binance-vision-archive-jsonl-v1"
BINANCE_VISION_ARCHIVE_INGESTOR_VERSION = "binance-vision-local-ingestor-v1"
MARKET_JOURNAL_SCHEMA_VERSION = "market-journal-jsonl-v1"
MARKET_JOURNAL_WRITER_VERSION = "market-journal-writer-v1"
RESEARCH_MARKET_DATA_ROOT = Path("data/research/market_data/binance_usdm")
RESEARCH_ARCHIVE_DATA_ROOT = Path("data/research/market_data/binance_vision")
SUPPORTED_RESEARCH_SYMBOLS = frozenset({"BTCUSDT", "ETHUSDT"})
SUPPORTED_BINANCE_VISION_DATA_FAMILIES = frozenset({"kline", "agg_trade", "trade"})

_KLINE_HEADER = (
    "open_time_ms",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time_ms",
    "quote_asset_volume",
    "trade_count",
    "taker_buy_base_asset_volume",
    "taker_buy_quote_asset_volume",
    "ignore",
)
_AGG_TRADE_HEADER = (
    "aggregate_trade_id",
    "price",
    "quantity",
    "first_trade_id",
    "last_trade_id",
    "transact_time_ms",
    "is_buyer_maker",
    "is_best_match",
)
_TRADE_HEADER = (
    "trade_id",
    "price",
    "quantity",
    "quote_quantity",
    "time_ms",
    "is_buyer_maker",
    "is_best_match",
)
_HEADERLESS_FIELDS_BY_FAMILY = {
    "kline": _KLINE_HEADER,
    "agg_trade": _AGG_TRADE_HEADER,
    "trade": _TRADE_HEADER,
}
_FIELD_ALIASES = {
    "open_time": "open_time_ms",
    "open_time_ms": "open_time_ms",
    "close_time": "close_time_ms",
    "close_time_ms": "close_time_ms",
    "quote_asset_volume": "quote_asset_volume",
    "number_of_trades": "trade_count",
    "trade_count": "trade_count",
    "taker_buy_base_asset_volume": "taker_buy_base_asset_volume",
    "taker_buy_quote_asset_volume": "taker_buy_quote_asset_volume",
    "ignore": "ignore",
    "id": "trade_id",
    "trade_id": "trade_id",
    "time": "time_ms",
    "time_ms": "time_ms",
    "a": "aggregate_trade_id",
    "aggregate_trade_id": "aggregate_trade_id",
    "agg_trade_id": "aggregate_trade_id",
    "aggtradeid": "aggregate_trade_id",
    "p": "price",
    "price": "price",
    "q": "quantity",
    "qty": "quantity",
    "quantity": "quantity",
    "quote_qty": "quote_quantity",
    "quote_quantity": "quote_quantity",
    "f": "first_trade_id",
    "first_trade_id": "first_trade_id",
    "l": "last_trade_id",
    "last_trade_id": "last_trade_id",
    "t": "transact_time_ms",
    "transact_time": "transact_time_ms",
    "transact_time_ms": "transact_time_ms",
    "timestamp": "transact_time_ms",
    "m": "is_buyer_maker",
    "is_buyer_maker": "is_buyer_maker",
    "is_best_match": "is_best_match",
    "best_match": "is_best_match",
    "M": "is_best_match",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "volume": "volume",
}


class BinanceHistoricalBarClient(Protocol):
    async def fetch_historical_closed_bar_range(
        self,
        symbol: str,
        *,
        start_time_ms: int,
        end_time_ms: int,
        interval: str = "15m",
    ) -> list[Bar]:
        ...


class MarketDataValidationError(ValueError):
    pass


class MarketDataGapError(MarketDataValidationError):
    pass


class MarketJournalValidationError(MarketDataValidationError):
    pass


@dataclass(frozen=True, slots=True)
class MarketDataCollectionResult:
    output_dir: Path
    data_path: Path
    manifest_path: Path
    row_count: int
    gap_count: int
    duplicate_count: int


@dataclass(frozen=True, slots=True)
class MarketDataArchiveIngestionResult:
    output_dir: Path
    data_path: Path
    manifest_path: Path
    row_count: int
    gap_count: int
    duplicate_count: int
    content_hash: str
    source_hash: str


def _normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if normalized not in SUPPORTED_RESEARCH_SYMBOLS:
        raise ValueError(f"symbol must be one of: {', '.join(sorted(SUPPORTED_RESEARCH_SYMBOLS))}")
    return normalized


def _validate_interval(interval: str) -> str:
    normalized = interval.strip()
    if normalized not in INTERVAL_TO_MS:
        raise ValueError(f"interval must be one of: {', '.join(sorted(INTERVAL_TO_MS))}")
    return normalized


def _bar_record(bar: Bar) -> dict[str, Any]:
    return {
        "time_ms": int(bar.time_ms),
        "open": str(bar.open),
        "high": str(bar.high),
        "low": str(bar.low),
        "close": str(bar.close),
        "volume": str(bar.volume),
    }


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            line = json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
            encoded = line.encode("utf-8")
            digest.update(encoded)
            handle.write(line)
    return digest.hexdigest()


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _canonical_hash(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def _spacing_report(bars: list[Bar], *, interval_ms: int) -> dict[str, Any]:
    sorted_times = sorted(int(bar.time_ms) for bar in bars)
    seen: set[int] = set()
    duplicates: list[int] = []
    for time_ms in sorted_times:
        if time_ms in seen:
            duplicates.append(time_ms)
        seen.add(time_ms)

    unique_times = sorted(seen)
    gaps: list[dict[str, int]] = []
    for previous, current in zip(unique_times, unique_times[1:]):
        delta_ms = current - previous
        if delta_ms != interval_ms:
            missing_count = max((delta_ms // interval_ms) - 1, 0)
            gaps.append(
                {
                    "previous_time_ms": previous,
                    "next_time_ms": current,
                    "delta_ms": delta_ms,
                    "missing_bar_count": missing_count,
                }
            )

    return {
        "gap_count": len(gaps),
        "duplicate_count": len(duplicates),
        "gaps": gaps,
        "duplicates": duplicates,
    }


def _validate_data_family(data_family: str) -> str:
    normalized = data_family.strip().lower().replace("-", "_")
    if normalized in {"aggtrade", "aggtrades", "agg_trade", "agg_trades"}:
        normalized = "agg_trade"
    elif normalized in {"kline", "klines"}:
        normalized = "kline"
    elif normalized in {"trade", "trades"}:
        normalized = "trade"
    if normalized not in SUPPORTED_BINANCE_VISION_DATA_FAMILIES:
        raise ValueError(
            f"data_family must be one of: {', '.join(sorted(SUPPORTED_BINANCE_VISION_DATA_FAMILIES))}"
        )
    return normalized


def _field_name(value: str) -> str:
    normalized = value.strip().replace(" ", "_").replace("-", "_")
    lower = normalized.lower()
    return _FIELD_ALIASES.get(normalized, _FIELD_ALIASES.get(lower, lower))


def _has_csv_header(first_row: list[str]) -> bool:
    known_fields = set(_FIELD_ALIASES) | set(_FIELD_ALIASES.values())
    normalized = {_field_name(cell) for cell in first_row}
    return bool(normalized & known_fields)


def _read_binance_vision_csv(source_path: Path, data_family: str) -> tuple[list[dict[str, str]], str | None]:
    suffix = source_path.suffix.lower()
    if suffix == ".zip":
        with zipfile.ZipFile(source_path) as archive:
            csv_members = [name for name in archive.namelist() if name.lower().endswith(".csv") and not name.endswith("/")]
            if len(csv_members) != 1:
                raise MarketDataValidationError("zip archive must contain exactly one CSV file")
            csv_member = csv_members[0]
            text = archive.read(csv_member).decode("utf-8-sig")
        return _parse_csv_text(text, data_family), csv_member
    if suffix != ".csv":
        raise ValueError("source_path must be a local .csv file or .zip containing one CSV file")
    return _parse_csv_text(source_path.read_text(encoding="utf-8-sig"), data_family), None


def _parse_csv_text(text: str, data_family: str) -> list[dict[str, str]]:
    reader = csv.reader(io.StringIO(text, newline=""))
    rows = [row for row in reader if row and any(cell.strip() for cell in row)]
    if not rows:
        raise MarketDataValidationError("archive CSV has no data rows")

    if _has_csv_header(rows[0]):
        fieldnames = [_field_name(cell) for cell in rows[0]]
        data_rows = rows[1:]
    else:
        fieldnames = list(_HEADERLESS_FIELDS_BY_FAMILY[data_family])
        data_rows = rows

    parsed: list[dict[str, str]] = []
    for row in data_rows:
        raw: dict[str, str] = {}
        for index, value in enumerate(row):
            field_name = fieldnames[index] if index < len(fieldnames) else f"extra_{index}"
            raw[field_name] = value.strip()
        parsed.append(raw)
    if not parsed:
        raise MarketDataValidationError("archive CSV has a header but no data rows")
    return parsed


def _required_value(row: Mapping[str, str], *field_names: str) -> str:
    for field_name in field_names:
        value = row.get(field_name)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    raise MarketDataValidationError(f"missing required field; tried {', '.join(field_names)}")


def _optional_value(row: Mapping[str, str], *field_names: str) -> str | None:
    for field_name in field_names:
        value = row.get(field_name)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return None


def _int_value(row: Mapping[str, str], *field_names: str) -> int:
    value = _required_value(row, *field_names)
    try:
        return int(value)
    except ValueError as exc:
        raise MarketDataValidationError(f"field must be an integer timestamp/id: {field_names[0]}={value}") from exc


def _optional_int_value(row: Mapping[str, str], *field_names: str) -> int | None:
    value = _optional_value(row, *field_names)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise MarketDataValidationError(f"field must be an integer id: {field_names[0]}={value}") from exc


def _optional_bool_value(row: Mapping[str, str], *field_names: str) -> bool | None:
    value = _optional_value(row, *field_names)
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"true", "1", "t", "yes", "y"}:
        return True
    if normalized in {"false", "0", "f", "no", "n"}:
        return False
    raise MarketDataValidationError(f"field must be boolean: {field_names[0]}={value}")


def _clean_raw_payload(row: Mapping[str, str]) -> dict[str, str]:
    return {str(key): str(value) for key, value in sorted(row.items()) if str(value) != ""}


def _normalize_archive_row(
    row: Mapping[str, str],
    *,
    symbol: str,
    data_family: str,
    source_row_index: int,
    interval: str | None = None,
) -> dict[str, Any]:
    raw_payload = _clean_raw_payload(row)
    if data_family == "kline":
        event_time_ms = _int_value(row, "open_time_ms")
        normalized = {
            "source_name": "binance_vision",
            "symbol": symbol,
            "data_family": data_family,
            "source_row_index": source_row_index,
            "event_time_ms": event_time_ms,
            "interval": interval,
            "open_time_ms": event_time_ms,
            "open_price": _required_value(row, "open"),
            "open": _required_value(row, "open"),
            "high_price": _required_value(row, "high"),
            "high": _required_value(row, "high"),
            "low_price": _required_value(row, "low"),
            "low": _required_value(row, "low"),
            "close_price": _required_value(row, "close"),
            "close": _required_value(row, "close"),
            "volume": _required_value(row, "volume"),
            "close_time_ms": _optional_int_value(row, "close_time_ms"),
            "quote_volume": _optional_value(row, "quote_asset_volume"),
            "quote_asset_volume": _optional_value(row, "quote_asset_volume"),
            "trade_count": _optional_int_value(row, "trade_count"),
            "taker_buy_base_volume": _optional_value(row, "taker_buy_base_asset_volume"),
            "taker_buy_base_asset_volume": _optional_value(row, "taker_buy_base_asset_volume"),
            "taker_buy_quote_volume": _optional_value(row, "taker_buy_quote_asset_volume"),
            "taker_buy_quote_asset_volume": _optional_value(row, "taker_buy_quote_asset_volume"),
            "raw_payload": raw_payload,
        }
    elif data_family == "agg_trade":
        event_time_ms = _int_value(row, "transact_time_ms")
        normalized = {
            "source_name": "binance_vision",
            "symbol": symbol,
            "data_family": data_family,
            "source_row_index": source_row_index,
            "event_time_ms": event_time_ms,
            "agg_trade_id": _optional_int_value(row, "aggregate_trade_id"),
            "aggregate_trade_id": _optional_int_value(row, "aggregate_trade_id"),
            "price": _required_value(row, "price"),
            "quantity": _required_value(row, "quantity"),
            "first_trade_id": _optional_int_value(row, "first_trade_id"),
            "last_trade_id": _optional_int_value(row, "last_trade_id"),
            "is_buyer_maker": _optional_bool_value(row, "is_buyer_maker"),
            "is_best_match": _optional_bool_value(row, "is_best_match"),
            "raw_payload": raw_payload,
        }
    else:
        event_time_ms = _int_value(row, "time_ms")
        normalized = {
            "source_name": "binance_vision",
            "symbol": symbol,
            "data_family": data_family,
            "source_row_index": source_row_index,
            "event_time_ms": event_time_ms,
            "trade_id": _optional_int_value(row, "trade_id"),
            "price": _required_value(row, "price"),
            "quantity": _required_value(row, "quantity"),
            "quote_quantity": _optional_value(row, "quote_quantity"),
            "is_buyer_maker": _optional_bool_value(row, "is_buyer_maker"),
            "is_best_match": _optional_bool_value(row, "is_best_match"),
            "raw_payload": raw_payload,
        }
    return {key: value for key, value in normalized.items() if value is not None}


def _archive_event_time_field(data_family: str) -> str:
    if data_family == "kline":
        return "open_time_ms"
    if data_family == "agg_trade":
        return "transact_time_ms"
    return "time_ms"


def _kline_spacing_report(rows: list[dict[str, Any]], *, interval_ms: int | None) -> dict[str, Any]:
    sorted_times = sorted(int(row["event_time_ms"]) for row in rows)
    seen: set[int] = set()
    duplicates: list[int] = []
    for time_ms in sorted_times:
        if time_ms in seen:
            duplicates.append(time_ms)
        seen.add(time_ms)

    gaps: list[dict[str, int]] = []
    if interval_ms is not None:
        for previous, current in zip(sorted(seen), sorted(seen)[1:]):
            delta_ms = current - previous
            if delta_ms != interval_ms:
                missing_count = max((delta_ms // interval_ms) - 1, 0)
                gaps.append(
                    {
                        "previous_time_ms": previous,
                        "next_time_ms": current,
                        "delta_ms": delta_ms,
                        "missing_bar_count": missing_count,
                    }
                )
    return {
        "gap_count": len(gaps),
        "duplicate_count": len(duplicates),
        "gaps": gaps,
        "duplicates": duplicates,
    }


def _event_id_duplicate_report(rows: list[dict[str, Any]], *, id_field: str) -> dict[str, Any]:
    seen: set[int] = set()
    duplicate_ids: list[int] = []
    id_available = False
    for row in rows:
        event_id = row.get(id_field)
        if event_id is None:
            continue
        id_available = True
        normalized_id = int(event_id)
        if normalized_id in seen:
            duplicate_ids.append(normalized_id)
        seen.add(normalized_id)
    return {
        "duplicate_count": len(duplicate_ids),
        "duplicates": duplicate_ids,
        "duplicate_check_applicable": id_available,
        "duplicate_event_id_field": id_field if id_available else None,
    }


def _archive_quality_report(
    rows: list[dict[str, Any]],
    *,
    data_family: str,
    interval: str | None,
) -> dict[str, Any]:
    if data_family == "kline":
        interval_ms = INTERVAL_TO_MS[interval] if interval is not None else None
        report = _kline_spacing_report(rows, interval_ms=interval_ms)
        report["duplicate_check_applicable"] = True
        report["duplicate_event_id_field"] = "open_time_ms"
        return report
    if data_family == "agg_trade":
        report = _event_id_duplicate_report(rows, id_field="aggregate_trade_id")
        report["gap_count"] = 0
        report["gaps"] = []
        return report
    report = _event_id_duplicate_report(rows, id_field="trade_id")
    report["gap_count"] = 0
    report["gaps"] = []
    return report


def ingest_binance_vision_archive(
    source_path: Path,
    *,
    symbol: str,
    data_family: str,
    output_dir: Path | None = None,
    interval: str | None = None,
    strict: bool = False,
) -> MarketDataArchiveIngestionResult:
    """Ingest a local Binance Vision-style CSV/ZIP archive into research JSONL.

    This function intentionally reads only local files. It does not fetch
    Binance Vision, Binance REST/WebSocket, Hyperliquid, or any live runtime
    source. The resulting manifest is diagnostic and non-promotable because
    Binance Vision archives do not carry local receive timestamps.
    """

    normalized_symbol = _normalize_symbol(symbol)
    normalized_family = _validate_data_family(data_family)
    normalized_interval = _validate_interval(interval) if interval is not None else None
    source_path = Path(source_path)
    if not source_path.is_file():
        raise FileNotFoundError(source_path)

    raw_rows, archive_member = _read_binance_vision_csv(source_path, normalized_family)
    rows = [
        _normalize_archive_row(
            raw_row,
            symbol=normalized_symbol,
            data_family=normalized_family,
            source_row_index=source_row_index,
            interval=normalized_interval,
        )
        for source_row_index, raw_row in enumerate(raw_rows)
    ]
    rows = sorted(rows, key=lambda row: (int(row["event_time_ms"]), int(row["source_row_index"])))
    report = _archive_quality_report(rows, data_family=normalized_family, interval=normalized_interval)

    first_event_time_ms = int(rows[0]["event_time_ms"])
    last_event_time_ms = int(rows[-1]["event_time_ms"])
    source_hash = _hash_file(source_path)
    output_root = output_dir if output_dir is not None else RESEARCH_ARCHIVE_DATA_ROOT
    family_dir = output_root / normalized_symbol / normalized_family
    if normalized_interval is not None:
        family_dir = family_dir / normalized_interval
    interval_part = f"_{normalized_interval}" if normalized_interval is not None else ""
    stem = f"{normalized_symbol}_{normalized_family}{interval_part}_{source_hash[:16]}"
    data_path = family_dir / f"{stem}.jsonl"
    manifest_path = family_dir / f"{stem}.manifest.json"
    content_hash = _write_jsonl(data_path, rows)

    event_time_field = _archive_event_time_field(normalized_family)
    normalized_fields = sorted({key for row in rows for key in row if key != "raw_payload"})
    missing_fields = ["interval"] if normalized_family == "kline" and normalized_interval is None else []
    manifest = {
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "source_name": "binance_vision",
        "source_type": "public_archive",
        "symbol": normalized_symbol,
        "data_family": normalized_family,
        "interval": normalized_interval,
        "start_time_ms": first_event_time_ms,
        "end_time_ms": last_event_time_ms if last_event_time_ms > first_event_time_ms else last_event_time_ms + 1,
        "row_count": len(rows),
        "first_event_time_ms": first_event_time_ms,
        "last_event_time_ms": last_event_time_ms,
        "content_hash": f"sha256:{content_hash}",
        "source_hash": f"sha256:{source_hash}",
        "gap_count": int(report["gap_count"]),
        "duplicate_count": int(report["duplicate_count"]),
        "gaps": report["gaps"],
        "duplicates": report["duplicates"],
        "duplicate_check_applicable": bool(report["duplicate_check_applicable"]),
        "duplicate_event_id_field": report["duplicate_event_id_field"],
        "event_time_field": event_time_field,
        "receive_time_unavailable_reason": (
            "Binance Vision local historical archive rows include exchange event time but no local receive timestamp."
        ),
        "schema_version": BINANCE_VISION_ARCHIVE_SCHEMA_VERSION,
        "collector_version": "not_applicable_local_archive",
        "ingestor_version": BINANCE_VISION_ARCHIVE_INGESTOR_VERSION,
        "source_path": str(source_path),
        "archive_member": archive_member,
        "data_path": str(data_path),
        "manifest_path": str(manifest_path),
        "schema_fields": normalized_fields,
        "normalized_fields": normalized_fields,
        "missing_fields": missing_fields,
        "zero_filled_fields": [],
        "quality_flags": ["receive_time_unavailable_non_promotable"],
        "non_promotable_notes": [
            "Research-only local Binance Vision archive ingestion.",
            "No network calls or live runtime state are used by this ingestor.",
            "Receive timestamps are unavailable, so rows are diagnostic and not live-promotable.",
            "Binance-derived archive rows are not Hyperliquid executable prices or fillability evidence.",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    if strict and (report["gap_count"] or report["duplicate_count"]):
        raise MarketDataGapError(
            f"archive quality checks failed for {normalized_symbol} {normalized_family}; "
            f"manifest_path={manifest_path}"
        )

    return MarketDataArchiveIngestionResult(
        output_dir=family_dir,
        data_path=data_path,
        manifest_path=manifest_path,
        row_count=len(rows),
        gap_count=int(report["gap_count"]),
        duplicate_count=int(report["duplicate_count"]),
        content_hash=f"sha256:{content_hash}",
        source_hash=f"sha256:{source_hash}",
    )


def _market_journal_event(
    *,
    raw_payload: Mapping[str, Any],
    normalized_payload: Mapping[str, Any],
    source_event_time_ms: int,
    receive_time_ms: int | None,
    source_name: str,
    symbol: str,
    data_family: str,
    source_row_index: int,
    schema_version: str = MARKET_JOURNAL_SCHEMA_VERSION,
) -> dict[str, Any]:
    if source_event_time_ms < 0:
        raise ValueError("source_event_time_ms must be non-negative")
    if receive_time_ms is not None and receive_time_ms < 0:
        raise ValueError("receive_time_ms must be non-negative or None")
    event = {
        "raw_payload": dict(raw_payload),
        "normalized_payload": dict(normalized_payload),
        "source_event_time_ms": int(source_event_time_ms),
        "receive_time_ms": int(receive_time_ms) if receive_time_ms is not None else None,
        "source_name": str(source_name),
        "symbol": _normalize_symbol(symbol),
        "data_family": _validate_data_family(data_family),
        "schema_version": str(schema_version),
        "source_row_index": int(source_row_index),
    }
    event["payload_hash"] = f"sha256:{_canonical_hash(event)}"
    return event


class MarketJournalWriter:
    """File-backed append-only JSONL writer for research market events."""

    def __init__(self, journal_path: Path, manifest_path: Path | None = None) -> None:
        self.journal_path = Path(journal_path)
        self.manifest_path = Path(manifest_path) if manifest_path is not None else self.journal_path.with_suffix(
            self.journal_path.suffix + ".manifest.json"
        )
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)

    def append(
        self,
        *,
        raw_payload: Mapping[str, Any],
        normalized_payload: Mapping[str, Any],
        source_event_time_ms: int,
        receive_time_ms: int | None,
        source_name: str,
        symbol: str,
        data_family: str,
        source_row_index: int,
        schema_version: str = MARKET_JOURNAL_SCHEMA_VERSION,
    ) -> dict[str, Any]:
        event = _market_journal_event(
            raw_payload=raw_payload,
            normalized_payload=normalized_payload,
            source_event_time_ms=source_event_time_ms,
            receive_time_ms=receive_time_ms,
            source_name=source_name,
            symbol=symbol,
            data_family=data_family,
            source_row_index=source_row_index,
            schema_version=schema_version,
        )
        line = json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
        with self.journal_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line)
        return event

    def write_manifest(self) -> dict[str, Any]:
        events = _read_jsonl_events(self.journal_path)
        journal_hash = _hash_file(self.journal_path)
        counts_by_family: dict[str, int] = {}
        counts_by_symbol: dict[str, int] = {}
        for event in events:
            data_family = str(event["data_family"])
            symbol = str(event["symbol"])
            counts_by_family[data_family] = counts_by_family.get(data_family, 0) + 1
            counts_by_symbol[symbol] = counts_by_symbol.get(symbol, 0) + 1
        event_times = [int(event["source_event_time_ms"]) for event in events]
        manifest = {
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            **research_boundary_metadata(),
            "schema_version": MARKET_JOURNAL_SCHEMA_VERSION,
            "writer_version": MARKET_JOURNAL_WRITER_VERSION,
            "journal_path": str(self.journal_path),
            "journal_hash": f"sha256:{journal_hash}",
            "event_count": len(events),
            "event_counts_by_family": dict(sorted(counts_by_family.items())),
            "event_counts_by_symbol": dict(sorted(counts_by_symbol.items())),
            "first_source_event_time_ms": min(event_times) if event_times else None,
            "last_source_event_time_ms": max(event_times) if event_times else None,
            "manifest_generated_at_ms": int(time.time() * 1000),
            "non_promotable_notes": [
                "Research-only append-only market event journal.",
                "Journal replay is deterministic and does not imply live execution readiness.",
            ],
        }
        self.manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        return manifest


def _read_jsonl_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise MarketJournalValidationError(f"invalid JSONL at {path}:{line_number}") from exc
    return events


def _validate_journal_payload_hash(event: Mapping[str, Any]) -> None:
    payload_hash = event.get("payload_hash")
    if not isinstance(payload_hash, str) or not payload_hash.startswith("sha256:"):
        raise MarketJournalValidationError("journal event missing payload_hash")
    without_hash = {key: value for key, value in event.items() if key != "payload_hash"}
    expected = f"sha256:{_canonical_hash(without_hash)}"
    if payload_hash != expected:
        raise MarketJournalValidationError("journal event payload_hash mismatch")


def read_market_journal(
    journal_path: Path,
    *,
    manifest_path: Path | None = None,
    validate_manifest: bool = True,
) -> list[dict[str, Any]]:
    """Read a research market journal in deterministic replay order."""

    journal_path = Path(journal_path)
    resolved_manifest_path = (
        Path(manifest_path)
        if manifest_path is not None
        else journal_path.with_suffix(journal_path.suffix + ".manifest.json")
    )
    if validate_manifest:
        manifest = json.loads(resolved_manifest_path.read_text(encoding="utf-8"))
        expected_hash = manifest.get("journal_hash")
        actual_hash = f"sha256:{_hash_file(journal_path)}"
        if expected_hash != actual_hash:
            raise MarketJournalValidationError(
                f"journal hash mismatch: expected {expected_hash}, observed {actual_hash}"
            )
    events = _read_jsonl_events(journal_path)
    for event in events:
        _validate_journal_payload_hash(event)
    return sorted(events, key=lambda event: (int(event["source_event_time_ms"]), int(event["source_row_index"])))


async def collect_binance_usdm_bars(
    *,
    symbol: str,
    interval: str,
    start_time_ms: int,
    end_time_ms: int,
    output_dir: Path | None = None,
    strict: bool = False,
    client: BinanceHistoricalBarClient | None = None,
) -> MarketDataCollectionResult:
    """Collect research-only Binance USD-M closed chart bars.

    The output is intentionally offline data for research and replay. It is not
    executable venue data and must not be used as a Hyperliquid fill source.
    """

    normalized_symbol = _normalize_symbol(symbol)
    normalized_interval = _validate_interval(interval)
    if start_time_ms < 0 or end_time_ms < 0:
        raise ValueError("start_time_ms and end_time_ms must be non-negative")
    if end_time_ms < start_time_ms:
        raise ValueError("end_time_ms must be greater than or equal to start_time_ms")

    output_root = output_dir if output_dir is not None else RESEARCH_MARKET_DATA_ROOT
    interval_ms = INTERVAL_TO_MS[normalized_interval]
    owns_client = client is None
    bar_client = client or BinanceCandleClient(BINANCE_USDM_FAPI_URL)
    try:
        bars = await bar_client.fetch_historical_closed_bar_range(
            normalized_symbol,
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
            interval=normalized_interval,
        )
    finally:
        if owns_client and isinstance(bar_client, BinanceCandleClient):
            await bar_client.close()

    rows_by_time = {_bar_record(bar)["time_ms"]: _bar_record(bar) for bar in bars}
    rows = [rows_by_time[time_ms] for time_ms in sorted(rows_by_time)]
    report = _spacing_report(bars, interval_ms=interval_ms)

    data_dir = output_root / normalized_symbol / normalized_interval
    stem = f"{normalized_symbol}_{normalized_interval}_{start_time_ms}_{end_time_ms}"
    data_path = data_dir / f"{stem}.jsonl"
    manifest_path = data_dir / f"{stem}.manifest.json"
    sha256 = _write_jsonl(data_path, rows)

    manifest = {
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "source": "binance_usdm_klines",
        "symbol": normalized_symbol,
        "interval": normalized_interval,
        "start_time_ms": start_time_ms,
        "end_time_ms": end_time_ms,
        "row_count": len(rows),
        "first_time_ms": rows[0]["time_ms"] if rows else None,
        "last_time_ms": rows[-1]["time_ms"] if rows else None,
        "sha256": sha256,
        "generated_at_ms": int(time.time() * 1000),
        "collector_version": COLLECTOR_VERSION,
        "gap_count": report["gap_count"],
        "duplicate_count": report["duplicate_count"],
        "gaps": report["gaps"],
        "duplicates": report["duplicates"],
        "data_path": str(data_path),
        "notes": [
            "Research-only Binance USD-M historical closed chart bars.",
            "This is not executable venue data and must not be treated as Hyperliquid fillability evidence.",
            "No live model pointers, execution state, or runtime trading behavior are updated by this collector.",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    if strict and (report["gap_count"] or report["duplicate_count"]):
        raise MarketDataGapError(
            f"collected bars are not continuous for {normalized_symbol} {normalized_interval}; "
            f"manifest_path={manifest_path}"
        )

    return MarketDataCollectionResult(
        output_dir=data_dir,
        data_path=data_path,
        manifest_path=manifest_path,
        row_count=len(rows),
        gap_count=int(report["gap_count"]),
        duplicate_count=int(report["duplicate_count"]),
    )
