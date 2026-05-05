from __future__ import annotations

import csv
import hashlib
import io
import json
import time
import asyncio
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

from tradingbotsuite.adapters.binance import INTERVAL_TO_MS, BinanceCandleClient
from tradingbotsuite.core.models import Bar
from tradingbotsuite.research.live_readiness import research_boundary_metadata
from tradingbotsuite.research.market_journal import (
    MARKET_JOURNAL_SCHEMA_VERSION,
    MARKET_JOURNAL_WRITER_VERSION,
    MarketJournalValidationError,
    MarketJournalWriter as _CanonicalMarketJournalWriter,
    read_market_journal_for_replay,
)

BINANCE_USDM_FAPI_URL = "https://fapi.binance.com"
BINANCE_VISION_BASE_URL = "https://data.binance.vision"
COLLECTOR_VERSION = "binance-usdm-chart-bars-v1"
BINANCE_USDM_CONTEXT_COLLECTOR_VERSION = "binance-usdm-context-rest-v1"
BINANCE_VISION_ARCHIVE_SCHEMA_VERSION = "binance-vision-archive-jsonl-v1"
BINANCE_VISION_ARCHIVE_INGESTOR_VERSION = "binance-vision-local-ingestor-v1"
BINANCE_VISION_DOWNLOADER_VERSION = "binance-vision-downloader-v1"
CRYPTO_LAKE_ARCHIVE_SCHEMA_VERSION = "crypto-lake-archive-jsonl-v1"
CRYPTO_LAKE_ARCHIVE_INGESTOR_VERSION = "crypto-lake-ingestor-v1"
RESEARCH_MARKET_DATA_ROOT = Path("data/research/market_data/binance_usdm")
RESEARCH_ARCHIVE_DATA_ROOT = Path("data/research/market_data/binance_vision")
RESEARCH_CRYPTO_LAKE_DATA_ROOT = Path("data/research/market_data/crypto_lake")
SUPPORTED_RESEARCH_SYMBOLS = frozenset({"BTCUSDT", "ETHUSDT"})
SUPPORTED_BINANCE_VISION_DATA_FAMILIES = frozenset({"kline", "agg_trade", "trade"})
SUPPORTED_CRYPTO_LAKE_DATA_FAMILIES = frozenset({"kline", "trade", "funding_rate", "open_interest", "liquidation"})
SUPPORTED_BINANCE_USDM_CONTEXT_FAMILIES = frozenset({"funding_rate", "premium_index", "open_interest"})
SUPPORTED_BINANCE_USDM_CONTEXT_PERIODS = frozenset({"5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d"})
PERP_CONTEXT_DATA_FAMILIES = frozenset({"funding_rate", "premium_index", "open_interest", "agg_trade", "liquidation"})

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


class BinanceUsdMContextFetcher(Protocol):
    async def fetch_context_rows(
        self,
        *,
        symbol: str,
        data_family: str,
        start_time_ms: int,
        end_time_ms: int,
        interval: str,
    ) -> list[Any]:
        ...


class MarketDataValidationError(ValueError):
    pass


class MarketDataGapError(MarketDataValidationError):
    pass


class CryptoLakeAccessError(MarketDataValidationError):
    pass


CRYPTO_LAKE_FREE_DATA_SETUP_MESSAGE = (
    "Crypto Lake free-data fallback fetch requires the optional lakeapi package. "
    'Install with `pip install -e ".[crypto-lake]"` or `pip install lakeapi`, then retry. '
    "The supported path uses anonymous free sample data and does not need provider credentials. "
    "See docs/runbooks/crypto_lake_free_data_runbook.md for the supported setup."
)


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


@dataclass(frozen=True, slots=True)
class BinanceVisionDownloadResult:
    url: str
    output_path: Path
    checksum_url: str | None
    checksum_path: Path | None
    sha256: str
    verified: bool


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


def _canonical_payload_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


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


def _validate_crypto_lake_data_family(data_family: str) -> str:
    normalized = data_family.strip().lower().replace("-", "_")
    if normalized in {"candles", "candle", "ohlcv", "ohlc", "klines"}:
        normalized = "kline"
    elif normalized in {"trades"}:
        normalized = "trade"
    elif normalized in {"funding", "funding_rates"}:
        normalized = "funding_rate"
    elif normalized in {"oi", "open_interest"}:
        normalized = "open_interest"
    elif normalized in {"liquidations", "force_order", "forceorder", "force_orders"}:
        normalized = "liquidation"
    if normalized not in SUPPORTED_CRYPTO_LAKE_DATA_FAMILIES:
        raise ValueError(
            f"crypto lake data_family must be one of: {', '.join(sorted(SUPPORTED_CRYPTO_LAKE_DATA_FAMILIES))}"
        )
    return normalized


def _validate_binance_usdm_context_data_family(data_family: str) -> str:
    normalized = data_family.strip().lower().replace("-", "_")
    if normalized in {"funding", "funding_rates"}:
        normalized = "funding_rate"
    elif normalized in {"premium", "premiumindex"}:
        normalized = "premium_index"
    elif normalized in {"oi", "openinterest"}:
        normalized = "open_interest"
    if normalized not in SUPPORTED_BINANCE_USDM_CONTEXT_FAMILIES:
        raise ValueError(
            "binance context data_family must be one of: "
            + ", ".join(sorted(SUPPORTED_BINANCE_USDM_CONTEXT_FAMILIES))
        )
    return normalized


def _validate_binance_usdm_context_interval(interval: str, *, data_family: str) -> str:
    normalized = _validate_interval(interval)
    if data_family == "open_interest" and normalized not in SUPPORTED_BINANCE_USDM_CONTEXT_PERIODS:
        raise ValueError(
            "open_interest period must be one of: "
            + ", ".join(sorted(SUPPORTED_BINANCE_USDM_CONTEXT_PERIODS))
        )
    return normalized


def _binance_vision_folder(data_family: str) -> str:
    if data_family == "kline":
        return "klines"
    if data_family == "agg_trade":
        return "aggTrades"
    if data_family == "trade":
        return "trades"
    raise ValueError(f"unsupported Binance Vision data family: {data_family}")


def _binance_vision_file_stem(*, symbol: str, data_family: str, interval: str | None, period: str) -> str:
    folder = _binance_vision_folder(data_family)
    if folder == "klines":
        if interval is None:
            raise ValueError("interval is required for Binance Vision klines")
        return f"{symbol}-{interval}-{period}"
    return f"{symbol}-{folder}-{period}"


def binance_vision_archive_url(
    *,
    symbol: str,
    data_family: str,
    period: str,
    interval: str | None = None,
    cadence: str = "daily",
    market: str = "futures/um",
    base_url: str = BINANCE_VISION_BASE_URL,
) -> str:
    normalized_symbol = _normalize_symbol(symbol)
    normalized_family = _validate_data_family(data_family)
    normalized_interval = _validate_interval(interval) if interval is not None else None
    normalized_cadence = cadence.strip().lower()
    if normalized_cadence not in {"daily", "monthly"}:
        raise ValueError("cadence must be daily or monthly")
    normalized_market = market.strip().strip("/")
    if normalized_market not in {"futures/um", "futures/cm", "spot"}:
        raise ValueError("market must be one of: futures/um, futures/cm, spot")
    folder = _binance_vision_folder(normalized_family)
    stem = _binance_vision_file_stem(
        symbol=normalized_symbol,
        data_family=normalized_family,
        interval=normalized_interval,
        period=period,
    )
    parts = [
        base_url.rstrip("/"),
        "data",
        *normalized_market.split("/"),
        normalized_cadence,
        folder,
        normalized_symbol,
    ]
    if folder == "klines":
        parts.append(str(normalized_interval))
    parts.append(f"{stem}.zip")
    return "/".join(parts)


def _fetch_bytes(url: str, *, timeout_seconds: float = 60.0) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout_seconds) as response:  # nosec B310 - research CLI fetcher
        return response.read()


def _fetch_json(url: str, *, timeout_seconds: float = 60.0) -> Any:
    return json.loads(_fetch_bytes(url, timeout_seconds=timeout_seconds).decode("utf-8"))


def _parse_checksum_payload(payload: bytes) -> str | None:
    text = payload.decode("utf-8", errors="replace").strip()
    if not text:
        return None
    token = text.split()[0].strip()
    if len(token) == 64 and all(character in "0123456789abcdefABCDEF" for character in token):
        return token.lower()
    return None


def download_binance_vision_archive(
    *,
    symbol: str,
    data_family: str,
    period: str,
    output_dir: Path | None = None,
    interval: str | None = None,
    cadence: str = "daily",
    market: str = "futures/um",
    verify_checksum: bool = True,
    fetcher: Callable[[str], bytes] | None = None,
) -> BinanceVisionDownloadResult:
    """Download one Binance Vision archive for research intake.

    The downloaded ZIP is not interpreted as live receive-time data; callers
    should pass it through ``ingest_binance_vision_archive`` before research use.
    """

    normalized_symbol = _normalize_symbol(symbol)
    normalized_family = _validate_data_family(data_family)
    normalized_interval = _validate_interval(interval) if interval is not None else None
    url = binance_vision_archive_url(
        symbol=normalized_symbol,
        data_family=normalized_family,
        period=period,
        interval=normalized_interval,
        cadence=cadence,
        market=market,
    )
    output_root = output_dir if output_dir is not None else RESEARCH_ARCHIVE_DATA_ROOT / "downloads"
    folder = _binance_vision_folder(normalized_family)
    target_dir = output_root / market.replace("/", "_") / cadence / folder / normalized_symbol
    if normalized_interval is not None:
        target_dir = target_dir / normalized_interval
    target_dir.mkdir(parents=True, exist_ok=True)
    output_path = target_dir / Path(url).name
    read_url = fetcher or _fetch_bytes
    payload = read_url(url)
    output_path.write_bytes(payload)
    observed_sha256 = _hash_file(output_path)

    checksum_url: str | None = None
    checksum_path: Path | None = None
    verified = False
    if verify_checksum:
        checksum_url = f"{url}.CHECKSUM"
        checksum_payload = read_url(checksum_url)
        checksum_path = output_path.with_name(f"{output_path.name}.CHECKSUM")
        checksum_path.write_bytes(checksum_payload)
        expected = _parse_checksum_payload(checksum_payload)
        if expected is None:
            raise MarketDataValidationError(f"could not parse Binance Vision checksum for {checksum_url}")
        if expected != observed_sha256:
            raise MarketDataValidationError(
                f"Binance Vision checksum mismatch for {output_path}: expected {expected}, observed {observed_sha256}"
            )
        verified = True

    download_manifest = {
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "downloader_version": BINANCE_VISION_DOWNLOADER_VERSION,
        "source_name": "binance_vision",
        "symbol": normalized_symbol,
        "data_family": normalized_family,
        "interval": normalized_interval,
        "cadence": cadence,
        "period": period,
        "market": market,
        "url": url,
        "output_path": str(output_path),
        "sha256": f"sha256:{observed_sha256}",
        "checksum_url": checksum_url,
        "checksum_path": str(checksum_path) if checksum_path is not None else None,
        "checksum_verified": verified,
        "notes": [
            "Research-only Binance Vision archive download.",
            "Downloaded files must be normalized before dataset or evidence stages consume them.",
        ],
    }
    output_path.with_name(f"{output_path.name}.download_manifest.json").write_text(
        json.dumps(download_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return BinanceVisionDownloadResult(
        url=url,
        output_path=output_path,
        checksum_url=checksum_url,
        checksum_path=checksum_path,
        sha256=f"sha256:{observed_sha256}",
        verified=verified,
    )


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


def _symbol_event_time_duplicate_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    seen: set[tuple[str, int]] = set()
    duplicates: list[dict[str, Any]] = []
    for row in rows:
        key = (str(row.get("symbol") or ""), int(row["event_time_ms"]))
        if key in seen:
            duplicates.append({"symbol": key[0], "event_time_ms": key[1]})
        seen.add(key)
    return {
        "duplicate_count": len(duplicates),
        "duplicates": duplicates,
        "duplicate_check_applicable": True,
        "duplicate_event_id_field": "symbol_event_time_ms",
    }


def _variable_cadence_gap_metadata() -> dict[str, Any]:
    return {
        "gap_count": 0,
        "gaps": [],
        "gap_check_applicable": False,
        "gap_check_status": "not_applicable_variable_cadence",
        "expected_interval_ms": None,
    }


def _no_duplicate_check_metadata() -> dict[str, Any]:
    return {
        "duplicate_count": 0,
        "duplicates": [],
        "duplicate_check_applicable": False,
        "duplicate_event_id_field": None,
    }


def _fixed_interval_gap_metadata(
    rows: list[dict[str, Any]],
    *,
    interval: str | None,
) -> dict[str, Any]:
    if interval is None:
        return _variable_cadence_gap_metadata()
    expected_interval_ms = INTERVAL_TO_MS[interval]
    unique_times = sorted({int(row["event_time_ms"]) for row in rows})
    gaps: list[dict[str, int]] = []
    for previous_time_ms, next_time_ms in zip(unique_times, unique_times[1:]):
        delta_ms = int(next_time_ms - previous_time_ms)
        if delta_ms != expected_interval_ms:
            gaps.append(
                {
                    "previous_event_time_ms": int(previous_time_ms),
                    "next_event_time_ms": int(next_time_ms),
                    "delta_ms": delta_ms,
                    "missing_event_count": max(0, int(delta_ms // expected_interval_ms) - 1),
                }
            )
    return {
        "gap_count": len(gaps),
        "gaps": gaps,
        "gap_check_applicable": True,
        "gap_check_status": "checked_fixed_interval",
        "expected_interval_ms": expected_interval_ms,
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
        report["gap_check_applicable"] = interval_ms is not None
        report["gap_check_status"] = "checked_fixed_interval" if interval_ms is not None else "not_applicable_missing_interval"
        report["expected_interval_ms"] = interval_ms
        return report
    if data_family == "agg_trade":
        report = _event_id_duplicate_report(rows, id_field="aggregate_trade_id")
        report.update(_variable_cadence_gap_metadata())
        return report
    if data_family in {"funding_rate", "premium_index", "open_interest"}:
        report = _symbol_event_time_duplicate_report(rows)
        if data_family in {"premium_index", "open_interest"}:
            report.update(_fixed_interval_gap_metadata(rows, interval=interval))
        else:
            report.update(_variable_cadence_gap_metadata())
        return report
    if data_family == "liquidation":
        report = _no_duplicate_check_metadata()
        report.update(_variable_cadence_gap_metadata())
        return report
    report = _event_id_duplicate_report(rows, id_field="trade_id")
    report.update(_variable_cadence_gap_metadata())
    return report


def _provider_coverage_metadata(
    *,
    source_name: str,
    data_family: str,
    source_access_mode: str | None = None,
) -> dict[str, Any]:
    context_metadata = (
        {"context_family_role": "perp_context"}
        if data_family in PERP_CONTEXT_DATA_FAMILIES
        else {}
    )
    stream_health = {
        "status": "not_applicable_batch_backfill",
        "reason": "rows are archive/backfill research data; no live stream continuity is claimed",
    }
    if source_name == "binance_usdm_rest":
        return {
            **context_metadata,
            "coverage_scope": "latest_window_backfill",
            "latest_window_only": True,
            "retention_policy": {
                "scope": "direct_endpoint_latest_window",
                "claim": "not_multi_year_coverage",
            },
            "stream_health": stream_health,
        }
    if source_name == "binance_vision":
        return {
            **context_metadata,
            "coverage_scope": "public_archive_partition",
            "latest_window_only": False,
            "retention_policy": {
                "scope": "public_archive_partition",
                "claim": "coverage_limited_to_downloaded_archive_partition",
            },
            "stream_health": stream_health,
        }
    if source_name == "crypto_lake" and source_access_mode == "free_sample":
        return {
            **context_metadata,
            "coverage_scope": "free_sample_diagnostic",
            "latest_window_only": False,
            "retention_policy": {
                "scope": "anonymous_free_sample",
                "claim": "sample_coverage_only",
            },
            "stream_health": stream_health,
        }
    if source_name == "crypto_lake":
        return {
            **context_metadata,
            "coverage_scope": "local_vendor_export",
            "latest_window_only": False,
            "retention_policy": {
                "scope": "local_export_file",
                "claim": "coverage_limited_to_local_export",
            },
            "stream_health": stream_health,
        }
    return {}


def _provider_coverage_quality_flags(metadata: Mapping[str, Any]) -> list[str]:
    if not metadata:
        return []
    flags: list[str] = []
    if metadata.get("context_family_role") == "perp_context":
        flags.append("perp_context_family")
    if metadata.get("latest_window_only") is True:
        flags.extend(["latest_window_only_context", "direct_endpoint_retention_limited"])
    if metadata.get("coverage_scope") == "free_sample_diagnostic":
        flags.append("free_sample_diagnostic_only")
    return flags


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
    coverage_metadata = _provider_coverage_metadata(
        source_name="binance_vision",
        data_family=normalized_family,
    )
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
        "gap_check_applicable": bool(report["gap_check_applicable"]),
        "gap_check_status": report["gap_check_status"],
        "expected_interval_ms": report["expected_interval_ms"],
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
        "quality_flags": [
            "receive_time_unavailable_non_promotable",
            *_provider_coverage_quality_flags(coverage_metadata),
        ],
        "non_promotable_notes": [
            "Research-only local Binance Vision archive ingestion.",
            "No network calls or live runtime state are used by this ingestor.",
            "Receive timestamps are unavailable, so rows are diagnostic and not live-promotable.",
            "Binance-derived archive rows are not Hyperliquid executable prices or fillability evidence.",
        ],
        **coverage_metadata,
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


def download_and_ingest_binance_vision_archive(
    *,
    symbol: str,
    data_family: str,
    period: str,
    output_dir: Path | None = None,
    interval: str | None = None,
    cadence: str = "daily",
    market: str = "futures/um",
    strict: bool = False,
    verify_checksum: bool = True,
    fetcher: Callable[[str], bytes] | None = None,
) -> MarketDataArchiveIngestionResult:
    download = download_binance_vision_archive(
        symbol=symbol,
        data_family=data_family,
        period=period,
        output_dir=(output_dir / "downloads") if output_dir is not None else None,
        interval=interval,
        cadence=cadence,
        market=market,
        verify_checksum=verify_checksum,
        fetcher=fetcher,
    )
    return ingest_binance_vision_archive(
        download.output_path,
        symbol=symbol,
        data_family=data_family,
        output_dir=output_dir,
        interval=interval,
        strict=strict,
    )


def _read_tabular_rows(source_path: Path) -> list[dict[str, Any]]:
    suffix = source_path.suffix.lower()
    if suffix == ".jsonl":
        rows = []
        for line in source_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                payload = json.loads(line)
                if not isinstance(payload, dict):
                    raise MarketDataValidationError("jsonl rows must be objects")
                rows.append(payload)
        if not rows:
            raise MarketDataValidationError("jsonl source has no rows")
        return rows
    if suffix == ".json":
        payload = json.loads(source_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            raw_rows = payload.get("rows") or payload.get("data") or payload.get("items")
        else:
            raw_rows = payload
        if not isinstance(raw_rows, list) or not all(isinstance(row, Mapping) for row in raw_rows):
            raise MarketDataValidationError("json source must contain a list of row objects")
        return [dict(row) for row in raw_rows]

    import pandas as pd

    if suffix == ".csv":
        frame = pd.read_csv(source_path)
    elif suffix in {".parquet", ".pq"}:
        frame = pd.read_parquet(source_path)
    else:
        raise ValueError("source_path must be .csv, .jsonl, .json, or .parquet")
    return frame.to_dict(orient="records")


def _first_present(row: Mapping[str, Any], names: tuple[str, ...]) -> Any:
    lower_map = {str(key).strip().lower(): value for key, value in row.items()}
    for name in names:
        if name in row and row[name] is not None and str(row[name]) != "":
            return row[name]
        lower = name.lower()
        if lower in lower_map and lower_map[lower] is not None and str(lower_map[lower]) != "":
            return lower_map[lower]
    return None


def _required_present(row: Mapping[str, Any], names: tuple[str, ...]) -> Any:
    value = _first_present(row, names)
    if value is None:
        raise MarketDataValidationError(f"missing required field; tried {', '.join(names)}")
    return value


def _timestamp_to_ms(value: Any) -> int:
    if hasattr(value, "to_pydatetime"):
        value = value.to_pydatetime()
    if isinstance(value, datetime):
        return int(value.timestamp() * 1000)
    if isinstance(value, date):
        return int(datetime(value.year, value.month, value.day).timestamp() * 1000)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            value = int(stripped)
        else:
            normalized = stripped.replace("Z", "+00:00")
            return int(datetime.fromisoformat(normalized).timestamp() * 1000)
    numeric = int(float(value))
    if numeric > 10_000_000_000_000_000:
        return numeric // 1_000_000
    if numeric > 10_000_000_000_000:
        return numeric // 1_000
    if numeric > 10_000_000_000:
        return numeric
    return numeric * 1000


def _optional_string_value(row: Mapping[str, Any], names: tuple[str, ...]) -> str | None:
    value = _first_present(row, names)
    if value is None:
        return None
    return str(value)


def _normalize_crypto_lake_row(
    row: Mapping[str, Any],
    *,
    symbol: str,
    data_family: str,
    interval: str | None,
    source_row_index: int,
    provider_symbol: str | None,
) -> dict[str, Any]:
    event_time_ms = _timestamp_to_ms(
        _required_present(row, ("event_time_ms", "origin_time", "timestamp", "time", "datetime", "open_time"))
    )
    receive_value = _first_present(row, ("receive_time_ms", "received_time", "ingest_time", "receipt_time"))
    raw_payload = {str(key): _json_scalar(value) for key, value in row.items()}
    if raw_payload.get("symbol") is not None and str(raw_payload["symbol"]).upper() != symbol:
        raw_payload["provider_symbol"] = raw_payload.pop("symbol")
    normalized: dict[str, Any] = {
        "source_name": "crypto_lake",
        "symbol": symbol,
        "provider_symbol": provider_symbol,
        "data_family": data_family,
        "source_row_index": source_row_index,
        "event_time_ms": event_time_ms,
        "provider_exchange": _first_present(row, ("exchange", "provider_exchange")),
        "provider_dataset": _first_present(row, ("table", "dataset", "provider_dataset")),
        "receive_time_ms": _timestamp_to_ms(receive_value) if receive_value is not None else None,
        "raw_payload": raw_payload,
    }
    if data_family == "kline":
        normalized.update(
            {
                "interval": interval,
                "open_time_ms": event_time_ms,
                "open_price": str(_required_present(row, ("open_price", "open"))),
                "open": str(_required_present(row, ("open_price", "open"))),
                "high_price": str(_required_present(row, ("high_price", "high"))),
                "high": str(_required_present(row, ("high_price", "high"))),
                "low_price": str(_required_present(row, ("low_price", "low"))),
                "low": str(_required_present(row, ("low_price", "low"))),
                "close_price": str(_required_present(row, ("close_price", "close"))),
                "close": str(_required_present(row, ("close_price", "close"))),
                "volume": str(_required_present(row, ("volume", "base_volume", "amount"))),
                "quote_volume": _string_or_none(_first_present(row, ("quote_volume", "quote_asset_volume"))),
                "trade_count": _int_or_none(_first_present(row, ("trade_count", "trades", "count"))),
            }
        )
    elif data_family == "trade":
        normalized.update(
            {
                "trade_id": _int_or_none(_first_present(row, ("trade_id", "id"))),
                "price": str(_required_present(row, ("price",))),
                "quantity": str(_required_present(row, ("quantity", "qty", "amount", "size"))),
                "side": _string_or_none(_first_present(row, ("side", "taker_side"))),
                "is_buyer_maker": _bool_or_none(_first_present(row, ("is_buyer_maker", "buyer_maker"))),
            }
        )
    elif data_family == "funding_rate":
        normalized.update(
            {
                "funding_rate": str(_required_present(row, ("funding_rate", "rate"))),
                "funding_time_ms": event_time_ms,
                "mark_price": _string_or_none(_first_present(row, ("mark_price",))),
                "index_price": _string_or_none(_first_present(row, ("index_price",))),
            }
        )
    elif data_family == "liquidation":
        normalized.update(
            {
                "side": _normalize_liquidation_side(
                    _required_present(row, ("side", "order_side", "liquidation_side", "S"))
                ),
                "price": str(_required_present(row, ("price", "p", "execution_price"))),
                "quantity": str(_required_present(row, ("quantity", "qty", "q", "amount", "size"))),
                "order_type": _string_or_none(_first_present(row, ("order_type", "type", "o"))),
                "time_in_force": _string_or_none(_first_present(row, ("time_in_force", "tif", "f"))),
                "average_price": _string_or_none(_first_present(row, ("average_price", "avg_price", "ap"))),
                "order_status": _string_or_none(_first_present(row, ("order_status", "status", "X"))),
                "last_filled_quantity": _string_or_none(
                    _first_present(row, ("last_filled_quantity", "last_filled_qty", "l"))
                ),
                "trade_time_ms": (
                    _timestamp_to_ms(_first_present(row, ("trade_time_ms", "trade_time", "T")))
                    if _first_present(row, ("trade_time_ms", "trade_time", "T")) is not None
                    else None
                ),
            }
        )
    else:
        normalized.update(
            {
                "open_interest": str(_required_present(row, ("open_interest", "open_interest_value", "oi"))),
                "open_interest_value_usd": _string_or_none(
                    _first_present(row, ("open_interest_value_usd", "open_interest_usd", "notional"))
                ),
            }
        )
    return {key: value for key, value in normalized.items() if value is not None}


def _normalize_liquidation_side(value: Any) -> str:
    text = str(value).strip().upper()
    aliases = {
        "B": "BUY",
        "BUYER": "BUY",
        "TAKER_BUY": "BUY",
        "S": "SELL",
        "SELLER": "SELL",
        "TAKER_SELL": "SELL",
    }
    return aliases.get(text, text)


def _json_scalar(value: Any) -> Any:
    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            pass
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _bool_or_none(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "t", "yes", "buy", "buyer"}:
        return True
    if text in {"false", "0", "f", "no", "sell", "seller"}:
        return False
    return None


def ingest_crypto_lake_archive(
    source_path: Path,
    *,
    symbol: str,
    data_family: str,
    output_dir: Path | None = None,
    interval: str | None = None,
    provider_symbol: str | None = None,
    source_access_mode: str = "local_export",
    strict: bool = False,
) -> MarketDataArchiveIngestionResult:
    normalized_symbol = _normalize_symbol(symbol)
    normalized_family = _validate_crypto_lake_data_family(data_family)
    normalized_interval = _validate_interval(interval) if interval is not None else None
    normalized_access_mode = _validate_crypto_lake_access_mode(source_access_mode)
    source_path = Path(source_path)
    if not source_path.is_file():
        raise FileNotFoundError(source_path)

    rows = [
        _normalize_crypto_lake_row(
            row,
            symbol=normalized_symbol,
            data_family=normalized_family,
            interval=normalized_interval,
            source_row_index=index,
            provider_symbol=provider_symbol,
        )
        for index, row in enumerate(_read_tabular_rows(source_path))
    ]
    rows = sorted(rows, key=lambda row: (int(row["event_time_ms"]), int(row["source_row_index"])))
    if not rows:
        raise MarketDataValidationError("Crypto Lake source has no rows")
    report = _archive_quality_report(rows, data_family=normalized_family, interval=normalized_interval)
    first_event_time_ms = int(rows[0]["event_time_ms"])
    last_event_time_ms = int(rows[-1]["event_time_ms"])
    source_hash = _hash_file(source_path)
    output_root = output_dir if output_dir is not None else RESEARCH_CRYPTO_LAKE_DATA_ROOT
    family_dir = output_root / normalized_symbol / normalized_family
    if normalized_interval is not None:
        family_dir = family_dir / normalized_interval
    interval_part = f"_{normalized_interval}" if normalized_interval is not None else ""
    stem = f"{normalized_symbol}_{normalized_family}{interval_part}_{source_hash[:16]}"
    data_path = family_dir / f"{stem}.jsonl"
    manifest_path = family_dir / f"{stem}.manifest.json"
    content_hash = _write_jsonl(data_path, rows)
    normalized_fields = sorted({key for row in rows for key in row if key != "raw_payload"})
    has_receive_time = any("receive_time_ms" in row for row in rows)
    coverage_metadata = _provider_coverage_metadata(
        source_name="crypto_lake",
        data_family=normalized_family,
        source_access_mode=normalized_access_mode,
    )
    manifest = {
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "source_name": "crypto_lake",
        "source_type": "commercial_archive",
        "source_access_mode": normalized_access_mode,
        "free_sample_data": normalized_access_mode == "free_sample",
        "symbol": normalized_symbol,
        "provider_symbol": provider_symbol,
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
        "gap_check_applicable": bool(report["gap_check_applicable"]),
        "gap_check_status": report["gap_check_status"],
        "expected_interval_ms": report["expected_interval_ms"],
        "duplicate_check_applicable": bool(report["duplicate_check_applicable"]),
        "duplicate_event_id_field": report["duplicate_event_id_field"],
        "event_time_field": "event_time_ms",
        "receive_time_field": "receive_time_ms" if has_receive_time else None,
        "receive_time_unavailable_reason": None if has_receive_time else "Crypto Lake export did not include local receive timestamps.",
        "schema_version": CRYPTO_LAKE_ARCHIVE_SCHEMA_VERSION,
        "ingestor_version": CRYPTO_LAKE_ARCHIVE_INGESTOR_VERSION,
        "source_path": str(source_path),
        "data_path": str(data_path),
        "manifest_path": str(manifest_path),
        "schema_fields": normalized_fields,
        "normalized_fields": normalized_fields,
        "missing_fields": [] if has_receive_time else ["receive_time_ms"],
        "zero_filled_fields": [],
        "quality_flags": [
            "crypto_lake_vendor_normalization",
            *_provider_coverage_quality_flags(coverage_metadata),
            *(
                ["crypto_lake_free_sample_data"]
                if normalized_access_mode == "free_sample"
                else []
            ),
            *([] if has_receive_time else ["receive_time_unavailable_non_promotable"]),
        ],
        "diagnostic_only": True,
        "non_promotable_notes": [
            "Research-only Crypto Lake archive ingestion.",
            *(
                [
                    "Crypto Lake free sample data is a diagnostic fallback only and is not full provider coverage.",
                ]
                if normalized_access_mode == "free_sample"
                else []
            ),
            "Vendor-normalized rows are diagnostic until checked against local point-in-time journals.",
            "Rows are not Hyperliquid executable prices or fillability evidence.",
        ],
        **coverage_metadata,
    }
    manifest = {key: value for key, value in manifest.items() if value is not None}
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    if strict and (report["gap_count"] or report["duplicate_count"]):
        raise MarketDataGapError(
            f"Crypto Lake archive quality checks failed for {normalized_symbol} {normalized_family}; "
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


def fetch_crypto_lake_archive(
    *,
    symbol: str,
    data_family: str,
    start_time: str,
    end_time: str,
    output_dir: Path | None = None,
    interval: str | None = None,
    exchange: str | None = None,
    table: str | None = None,
    provider_symbol: str | None = None,
    lakeapi_module: Any | None = None,
) -> MarketDataArchiveIngestionResult:
    """Fetch Crypto Lake free sample data via optional ``lakeapi`` and normalize it.

    The supported direct fetch mode is Crypto Lake's anonymous free sample
    dataset. Provider credentials are intentionally not required by this
    research fallback path. Local exports can still use
    ``ingest_crypto_lake_archive`` without network access.
    """

    normalized_symbol = _normalize_symbol(symbol)
    normalized_family = _validate_crypto_lake_data_family(data_family)
    normalized_provider_symbol = provider_symbol or normalized_symbol
    lakeapi_module = _resolve_lakeapi_module(lakeapi_module)
    _enable_crypto_lake_free_sample_data(lakeapi_module)

    table_name = table or _crypto_lake_default_table(normalized_family)
    load_start = _crypto_lake_load_datetime(start_time)
    load_end = _crypto_lake_load_datetime(end_time)
    frame = lakeapi_module.load_data(
        table=table_name,
        start=load_start,
        end=load_end,
        symbols=[normalized_provider_symbol],
        exchanges=[exchange] if exchange else None,
    )
    output_root = output_dir if output_dir is not None else RESEARCH_CRYPTO_LAKE_DATA_ROOT / "downloads"
    raw_dir = output_root / "raw" / normalized_symbol / normalized_family
    raw_dir.mkdir(parents=True, exist_ok=True)
    safe_start = start_time.replace(":", "").replace("-", "").replace(" ", "T")
    safe_end = end_time.replace(":", "").replace("-", "").replace(" ", "T")
    exchange_part = exchange or "all_exchanges"
    raw_path = raw_dir / f"{exchange_part}_{normalized_provider_symbol}_{table_name}_{safe_start}_{safe_end}_free_sample.csv"
    frame.to_csv(raw_path, index=False, lineterminator="\n")
    return ingest_crypto_lake_archive(
        raw_path,
        symbol=normalized_symbol,
        data_family=normalized_family,
        output_dir=output_dir,
        interval=interval,
        provider_symbol=normalized_provider_symbol,
        source_access_mode="free_sample",
    )


def _validate_crypto_lake_access_mode(value: str) -> str:
    normalized = str(value).strip().lower().replace("-", "_")
    if normalized not in {"local_export", "free_sample"}:
        raise ValueError("source_access_mode must be local_export or free_sample")
    return normalized


def _crypto_lake_load_datetime(value: str) -> datetime:
    text = str(value).strip()
    if not text:
        raise ValueError("Crypto Lake start_time/end_time must be non-empty")
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Crypto Lake time must be ISO-8601 compatible: {value}") from exc


def _resolve_lakeapi_module(lakeapi_module: Any | None) -> Any:
    if lakeapi_module is not None:
        return lakeapi_module
    try:
        import lakeapi as resolved_lakeapi_module  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        raise CryptoLakeAccessError(CRYPTO_LAKE_FREE_DATA_SETUP_MESSAGE) from exc
    return resolved_lakeapi_module


def _enable_crypto_lake_free_sample_data(lakeapi_module: Any) -> None:
    use_sample_data = getattr(lakeapi_module, "use_sample_data", None)
    if not callable(use_sample_data):
        raise CryptoLakeAccessError(
            "lakeapi module does not expose use_sample_data; cannot enable Crypto Lake free sample data"
        )
    use_sample_data(anonymous_access=True)


def _crypto_lake_default_table(data_family: str) -> str:
    if data_family == "kline":
        return "candles"
    if data_family == "trade":
        return "trades"
    if data_family == "funding_rate":
        return "funding"
    if data_family == "open_interest":
        return "open_interest"
    return "liquidations"


class MarketJournalWriter:
    """Compatibility wrapper for the canonical Binance-style market journal."""

    def __init__(self, journal_path: Path, manifest_path: Path | None = None) -> None:
        self._writer = _CanonicalMarketJournalWriter(journal_path, manifest_path=manifest_path)
        self.journal_path = self._writer.journal_path
        self.manifest_path = self._writer.manifest_path

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
        if schema_version != MARKET_JOURNAL_SCHEMA_VERSION:
            raise MarketJournalValidationError("schema_version_must_match_market_journal_contract")
        return self._writer.append(
            raw_payload=raw_payload,
            normalized_payload=normalized_payload,
            source_event_time_ms=source_event_time_ms,
            local_receive_time_ms=receive_time_ms,
            source_name=source_name,
            symbol=symbol,
            data_family=data_family,
            source_row_index=source_row_index,
        )

    def write_manifest(self, *, strict: bool = False) -> dict[str, Any]:
        return self._writer.write_manifest(strict=strict)


def read_market_journal(
    journal_path: Path,
    *,
    manifest_path: Path | None = None,
    validate_manifest: bool = True,
) -> list[dict[str, Any]]:
    """Read a research market journal in deterministic replay order."""

    return read_market_journal_for_replay(
        journal_path,
        manifest_path=manifest_path,
        validate_manifest=validate_manifest,
    )


class BinanceUsdMRestContextFetcher:
    def __init__(self, base_url: str = BINANCE_USDM_FAPI_URL, *, timeout_seconds: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def fetch_context_rows(
        self,
        *,
        symbol: str,
        data_family: str,
        start_time_ms: int,
        end_time_ms: int,
        interval: str,
    ) -> list[Any]:
        return await asyncio.to_thread(
            self._fetch_context_rows_sync,
            symbol=symbol,
            data_family=data_family,
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
            interval=interval,
        )

    def _fetch_context_rows_sync(
        self,
        *,
        symbol: str,
        data_family: str,
        start_time_ms: int,
        end_time_ms: int,
        interval: str,
    ) -> list[Any]:
        if data_family == "funding_rate":
            return self._fetch_paginated(
                path="/fapi/v1/fundingRate",
                params={"symbol": symbol, "limit": 1000},
                start_time_ms=start_time_ms,
                end_time_ms=end_time_ms,
                event_time_getter=lambda row: _timestamp_to_ms(_required_present(row, ("fundingTime", "funding_time_ms", "event_time_ms"))),
                next_start_delta_ms=1,
            )
        if data_family == "premium_index":
            return self._fetch_paginated(
                path="/fapi/v1/premiumIndexKlines",
                params={"symbol": symbol, "interval": interval, "limit": 1500},
                start_time_ms=start_time_ms,
                end_time_ms=end_time_ms,
                event_time_getter=lambda row: _timestamp_to_ms(row[0] if isinstance(row, list) else _required_present(row, ("open_time", "open_time_ms", "event_time_ms"))),
                next_start_delta_ms=INTERVAL_TO_MS[interval],
            )
        if data_family == "open_interest":
            return self._fetch_paginated_backward(
                path="/futures/data/openInterestHist",
                params={"symbol": symbol, "period": interval, "limit": 500},
                start_time_ms=start_time_ms,
                end_time_ms=end_time_ms,
                event_time_getter=lambda row: _timestamp_to_ms(_required_present(row, ("timestamp", "time_ms", "event_time_ms"))),
                previous_end_delta_ms=INTERVAL_TO_MS[interval],
            )
        raise ValueError(f"unsupported_binance_usdm_context_family:{data_family}")

    def _fetch_paginated(
        self,
        *,
        path: str,
        params: dict[str, object],
        start_time_ms: int,
        end_time_ms: int,
        event_time_getter: Callable[[Any], int],
        next_start_delta_ms: int,
    ) -> list[Any]:
        rows: list[Any] = []
        cursor = start_time_ms
        max_pages = 1000
        for _ in range(max_pages):
            query = dict(params)
            query["startTime"] = cursor
            query["endTime"] = end_time_ms
            url = f"{self.base_url}{path}?{urllib.parse.urlencode(query)}"
            payload = _fetch_json(url, timeout_seconds=self.timeout_seconds)
            if not isinstance(payload, list):
                raise MarketDataValidationError(f"binance context endpoint returned non-list payload:{path}")
            if not payload:
                break
            rows.extend(payload)
            last_event_time_ms = max(event_time_getter(row) for row in payload)
            next_cursor = last_event_time_ms + next_start_delta_ms
            if next_cursor > end_time_ms or next_cursor <= cursor:
                break
            cursor = next_cursor
            if len(payload) < int(params.get("limit", len(payload))):
                break
        else:
            raise MarketDataValidationError(f"binance context pagination exceeded page limit:{path}")
        return rows

    def _fetch_paginated_backward(
        self,
        *,
        path: str,
        params: dict[str, object],
        start_time_ms: int,
        end_time_ms: int,
        event_time_getter: Callable[[Any], int],
        previous_end_delta_ms: int,
    ) -> list[Any]:
        rows: list[Any] = []
        cursor_end = end_time_ms
        max_pages = 1000
        for _ in range(max_pages):
            limit = int(params.get("limit", 0) or 0)
            page_start_time_ms = start_time_ms
            if limit > 1:
                page_start_time_ms = max(start_time_ms, cursor_end - ((limit - 1) * previous_end_delta_ms))
            query = dict(params)
            query["startTime"] = page_start_time_ms
            query["endTime"] = cursor_end
            url = f"{self.base_url}{path}?{urllib.parse.urlencode(query)}"
            payload = _fetch_json(url, timeout_seconds=self.timeout_seconds)
            if not isinstance(payload, list):
                raise MarketDataValidationError(f"binance context endpoint returned non-list payload:{path}")
            if not payload:
                break
            rows.extend(payload)
            event_times = [event_time_getter(row) for row in payload]
            first_event_time_ms = min(event_times)
            next_cursor_end = first_event_time_ms - previous_end_delta_ms
            if first_event_time_ms <= start_time_ms or next_cursor_end < start_time_ms or next_cursor_end >= cursor_end:
                break
            cursor_end = next_cursor_end
            if len(payload) < int(params.get("limit", len(payload))) and page_start_time_ms <= start_time_ms:
                break
        else:
            raise MarketDataValidationError(f"binance context pagination exceeded page limit:{path}")
        return rows


async def collect_binance_usdm_context(
    *,
    symbol: str,
    data_family: str,
    start_time_ms: int,
    end_time_ms: int,
    output_dir: Path | None = None,
    interval: str = "5m",
    strict: bool = False,
    fetcher: BinanceUsdMContextFetcher | None = None,
) -> MarketDataArchiveIngestionResult:
    """Collect research-only Binance USD-M context rows for fixture-pack construction."""

    normalized_symbol = _normalize_symbol(symbol)
    normalized_family = _validate_binance_usdm_context_data_family(data_family)
    normalized_interval = _validate_binance_usdm_context_interval(interval, data_family=normalized_family)
    if start_time_ms < 0 or end_time_ms < 0:
        raise ValueError("start_time_ms and end_time_ms must be non-negative")
    if end_time_ms < start_time_ms:
        raise ValueError("end_time_ms must be greater than or equal to start_time_ms")

    context_fetcher = fetcher or BinanceUsdMRestContextFetcher()
    raw_rows = await context_fetcher.fetch_context_rows(
        symbol=normalized_symbol,
        data_family=normalized_family,
        start_time_ms=start_time_ms,
        end_time_ms=end_time_ms,
        interval=normalized_interval,
    )
    normalized_rows = [
        _normalize_binance_usdm_context_row(
            row,
            symbol=normalized_symbol,
            data_family=normalized_family,
            source_row_index=source_row_index,
        )
        for source_row_index, row in enumerate(raw_rows)
    ]
    normalized_rows = [
        row
        for row in normalized_rows
        if start_time_ms <= int(row["event_time_ms"]) <= end_time_ms
    ]
    normalized_rows = sorted(normalized_rows, key=lambda row: (int(row["event_time_ms"]), int(row["source_row_index"])))
    report = _context_quality_report(
        normalized_rows,
        data_family=normalized_family,
        interval=normalized_interval,
    )
    output_root = output_dir if output_dir is not None else RESEARCH_MARKET_DATA_ROOT
    interval_part = "" if normalized_family == "funding_rate" else f"_{normalized_interval}"
    data_dir = output_root / normalized_symbol / normalized_family
    if normalized_family != "funding_rate":
        data_dir = data_dir / normalized_interval
    stem = f"{normalized_symbol}_{normalized_family}{interval_part}_{start_time_ms}_{end_time_ms}"
    data_path = data_dir / f"{stem}.jsonl"
    manifest_path = data_dir / f"{stem}.manifest.json"
    content_hash = _write_jsonl(data_path, normalized_rows)
    source_hash = _canonical_payload_hash({"source": "binance_usdm_rest", "rows": raw_rows})
    normalized_fields = sorted({key for row in normalized_rows for key in row if key != "raw_payload"})
    first_event_time_ms = int(normalized_rows[0]["event_time_ms"]) if normalized_rows else None
    last_event_time_ms = int(normalized_rows[-1]["event_time_ms"]) if normalized_rows else None
    coverage_metadata = _provider_coverage_metadata(
        source_name="binance_usdm_rest",
        data_family=normalized_family,
    )

    manifest = {
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "source_name": "binance_usdm_rest",
        "source_type": "rest_backfill",
        "symbol": normalized_symbol,
        "data_family": normalized_family,
        "interval": None if normalized_family == "funding_rate" else normalized_interval,
        "start_time_ms": start_time_ms,
        "end_time_ms": end_time_ms,
        "row_count": len(normalized_rows),
        "first_event_time_ms": first_event_time_ms,
        "last_event_time_ms": last_event_time_ms,
        "content_hash": f"sha256:{content_hash}",
        "source_hash": f"sha256:{source_hash}",
        "gap_count": int(report["gap_count"]),
        "duplicate_count": int(report["duplicate_count"]),
        "gaps": report["gaps"],
        "duplicates": report["duplicates"],
        "gap_check_applicable": bool(report["gap_check_applicable"]),
        "gap_check_status": report["gap_check_status"],
        "expected_interval_ms": report["expected_interval_ms"],
        "duplicate_check_applicable": True,
        "duplicate_event_id_field": "symbol_event_time_ms",
        "event_time_field": "event_time_ms",
        "receive_time_field": None,
        "receive_time_unavailable_reason": (
            "Binance USD-M REST backfill rows include exchange event time but no original local receive timestamp."
        ),
        "schema_version": "binance-usdm-context-jsonl-v1",
        "collector_version": BINANCE_USDM_CONTEXT_COLLECTOR_VERSION,
        "endpoint_family": _binance_usdm_context_endpoint_family(normalized_family),
        "data_path": str(data_path),
        "manifest_path": str(manifest_path),
        "schema_fields": normalized_fields,
        "normalized_fields": normalized_fields,
        "missing_fields": ["receive_time_ms"],
        "zero_filled_fields": [],
        "quality_flags": [
            "receive_time_unavailable_non_promotable",
            *_provider_coverage_quality_flags(coverage_metadata),
        ],
        "non_promotable_notes": [
            "Research-only Binance USD-M REST context backfill.",
            "No legacy chart export, Pine marker, or parity artifact is used.",
            "No live runtime state, execution state, model pointer, or trading behavior is updated.",
            "Receive timestamps are unavailable, so rows are diagnostic and not live-promotable.",
        ],
        **coverage_metadata,
    }
    manifest = {key: value for key, value in manifest.items() if value is not None}
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    if strict and (report["duplicate_count"] or report["gap_count"]):
        raise MarketDataGapError(
            f"Binance USD-M context duplicate events or gaps for {normalized_symbol} {normalized_family}: "
            f"gaps={report['gaps']} duplicates={report['duplicates']} manifest_path={manifest_path}"
        )

    return MarketDataArchiveIngestionResult(
        output_dir=data_dir,
        data_path=data_path,
        manifest_path=manifest_path,
        row_count=len(normalized_rows),
        gap_count=int(report["gap_count"]),
        duplicate_count=int(report["duplicate_count"]),
        content_hash=f"sha256:{content_hash}",
        source_hash=f"sha256:{source_hash}",
    )


def _normalize_binance_usdm_context_row(
    row: Any,
    *,
    symbol: str,
    data_family: str,
    source_row_index: int,
) -> dict[str, Any]:
    if data_family == "premium_index" and isinstance(row, list):
        if len(row) < 5:
            raise MarketDataValidationError("premium index kline row must contain at least five fields")
        event_time_ms = _timestamp_to_ms(row[0])
        premium_close = str(row[4])
        return {
            "source_name": "binance_usdm_rest",
            "symbol": symbol,
            "data_family": data_family,
            "source_row_index": source_row_index,
            "event_time_ms": event_time_ms,
            "premium_open": str(row[1]),
            "premium_high": str(row[2]),
            "premium_low": str(row[3]),
            "premium_close": premium_close,
            "premium_index": premium_close,
            "premium_basis_rate": premium_close,
            "raw_payload": row,
        }
    if not isinstance(row, Mapping):
        raise MarketDataValidationError(f"context row must be mapping for {data_family}")
    row_symbol = str(row.get("symbol") or symbol).strip().upper()
    if row_symbol != symbol:
        raise MarketDataValidationError(f"context symbol mismatch:{row_symbol}:{symbol}")
    raw_payload = {str(key): _json_scalar(value) for key, value in row.items()}
    if data_family == "funding_rate":
        event_time_ms = _timestamp_to_ms(
            _required_present(row, ("event_time_ms", "fundingTime", "funding_time_ms", "funding_time"))
        )
        normalized = {
            "source_name": "binance_usdm_rest",
            "symbol": symbol,
            "data_family": data_family,
            "source_row_index": source_row_index,
            "event_time_ms": event_time_ms,
            "funding_time_ms": event_time_ms,
            "funding_rate": str(_required_present(row, ("funding_rate", "fundingRate", "rate"))),
            "mark_price": _optional_string_value(row, ("mark_price", "markPrice")),
            "raw_payload": raw_payload,
        }
    elif data_family == "premium_index":
        event_time_ms = _timestamp_to_ms(
            _required_present(row, ("event_time_ms", "open_time_ms", "openTime", "time", "timestamp"))
        )
        premium_value = str(_required_present(row, ("premium_index", "premium_basis_rate", "premium_close", "close")))
        normalized = {
            "source_name": "binance_usdm_rest",
            "symbol": symbol,
            "data_family": data_family,
            "source_row_index": source_row_index,
            "event_time_ms": event_time_ms,
            "premium_index": premium_value,
            "premium_basis_rate": premium_value,
            "premium_close": premium_value,
            "mark_price": _optional_string_value(row, ("mark_price", "markPrice")),
            "index_price": _optional_string_value(row, ("index_price", "indexPrice")),
            "raw_payload": raw_payload,
        }
    else:
        event_time_ms = _timestamp_to_ms(_required_present(row, ("event_time_ms", "timestamp", "time_ms", "time")))
        normalized = {
            "source_name": "binance_usdm_rest",
            "symbol": symbol,
            "data_family": data_family,
            "source_row_index": source_row_index,
            "event_time_ms": event_time_ms,
            "open_interest": str(_required_present(row, ("open_interest", "sumOpenInterest", "sum_open_interest", "oi"))),
            "open_interest_value": _optional_string_value(
                row,
                ("open_interest_value", "sumOpenInterestValue", "sum_open_interest_value", "open_interest_value_usd"),
            ),
            "open_interest_value_usd": _optional_string_value(
                row,
                ("open_interest_value_usd", "sumOpenInterestValue", "sum_open_interest_value", "open_interest_value"),
            ),
            "raw_payload": raw_payload,
        }
    return {key: value for key, value in normalized.items() if value is not None}


def _context_quality_report(
    rows: list[dict[str, Any]],
    *,
    data_family: str,
    interval: str,
) -> dict[str, Any]:
    seen: set[tuple[str, int]] = set()
    duplicates: list[dict[str, Any]] = []
    for row in rows:
        key = (str(row["symbol"]), int(row["event_time_ms"]))
        if key in seen:
            duplicates.append({"symbol": key[0], "event_time_ms": key[1]})
        seen.add(key)
    gaps: list[dict[str, int]] = []
    expected_interval_ms = INTERVAL_TO_MS.get(interval) if data_family in {"premium_index", "open_interest"} else None
    if expected_interval_ms is not None:
        unique_times = sorted({int(row["event_time_ms"]) for row in rows})
        for previous_time_ms, next_time_ms in zip(unique_times, unique_times[1:]):
            delta_ms = int(next_time_ms - previous_time_ms)
            if delta_ms != expected_interval_ms:
                gaps.append(
                    {
                        "previous_event_time_ms": int(previous_time_ms),
                        "next_event_time_ms": int(next_time_ms),
                        "delta_ms": delta_ms,
                        "missing_event_count": max(0, int(delta_ms // expected_interval_ms) - 1),
                    }
                )
        gap_check_status = "checked_fixed_interval"
    else:
        gap_check_status = "not_applicable_variable_cadence"
    return {
        "gap_count": len(gaps),
        "duplicate_count": len(duplicates),
        "gaps": gaps,
        "duplicates": duplicates,
        "gap_check_applicable": expected_interval_ms is not None,
        "gap_check_status": gap_check_status,
        "expected_interval_ms": expected_interval_ms,
    }


def _binance_usdm_context_endpoint_family(data_family: str) -> str:
    if data_family == "funding_rate":
        return "/fapi/v1/fundingRate"
    if data_family == "premium_index":
        return "/fapi/v1/premiumIndexKlines"
    if data_family == "open_interest":
        return "/futures/data/openInterestHist"
    raise ValueError(f"unsupported_binance_usdm_context_family:{data_family}")


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
