from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from tradingbotsuite.research_sandbox.boundary import (
    SANDBOX_BOUNDARY_FLAGS,
    require_sandbox_boundary,
    sandbox_boundary_metadata,
)
from tradingbotsuite.research_sandbox.discovery import bounded_discover_files
from tradingbotsuite.research_sandbox.identity import digest_payload
from tradingbotsuite.research_sandbox.market_data import load_market_frame
from tradingbotsuite.research_sandbox.spec import (
    ALLOWED_DATA_FAMILIES,
    DataWindow,
    VENUE_ALIASES,
    VenueArchiveDescriptor,
    canonical_venue,
)


ARCHIVE_MANIFEST_JSON_NAME = "venue_archives.json"
ARCHIVE_MANIFEST_BUILD_REPORT_JSON_NAME = "archive_manifest_build_report.json"
ARCHIVE_MANIFEST_BUILD_REPORT_PARQUET_NAME = "archive_manifest_build_report.parquet"

SUPPORTED_ARCHIVE_SUFFIXES = frozenset(
    {
        ".csv",
        ".tsv",
        ".json",
        ".jsonl",
        ".ndjson",
        ".parquet",
        ".zip",
        ".tar",
        ".tar.gz",
        ".tgz",
        ".csv.gz",
        ".tsv.gz",
        ".json.gz",
        ".jsonl.gz",
        ".ndjson.gz",
    }
)

DATA_FAMILY_ALIASES: dict[str, str] = {
    "aggtrade": "agg_trade",
    "aggtrades": "agg_trade",
    "agg_trade": "agg_trade",
    "kline": "kline",
    "klines": "kline",
    "candle": "kline",
    "candles": "kline",
    "bar": "kline",
    "bars": "kline",
    "ohlcv": "kline",
    "trade": "trade",
    "trades": "trade",
    "funding": "funding",
    "fundingrate": "funding",
    "fundingrates": "funding",
    "openinterest": "open_interest",
    "open_interest": "open_interest",
    "oi": "open_interest",
    "mark": "mark_index",
    "index": "mark_index",
    "markindex": "mark_index",
    "book": "l2_book",
    "l2book": "l2_book",
    "orderbook": "l2_book",
    "l2": "l2_book",
    "assetcontext": "asset_context",
    "asset_context": "asset_context",
    "context": "asset_context",
}

QUOTE_TOKENS = {"USD", "USDT", "USDC", "PERP"}
BASE_TOKENS = {"BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX", "LINK", "LTC"}
CONTENT_VENUE_COLUMNS = ("venue", "exchange", "provider", "source_exchange", "source", "platform")
CONTENT_SYMBOL_COLUMNS = (
    "symbol",
    "inst_id",
    "instid",
    "instrument",
    "instrument_id",
    "instrumentid",
    "market",
    "pair",
)
CONTENT_BASE_COLUMNS = ("coin", "asset", "base", "base_coin", "basecoin", "base_currency", "basecurrency")
CONTENT_QUOTE_COLUMNS = ("quote", "quote_coin", "quotecoin", "quote_currency", "quotecurrency")
CONTENT_INTERVAL_COLUMNS = ("interval", "timeframe", "tf", "bar", "resolution", "res")
CONTENT_DATA_FAMILY_COLUMNS = ("data_family", "datafamily", "family", "channel", "topic", "type", "kind")


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


def _file_integrity(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"sha256": digest.hexdigest(), "byte_size": path.stat().st_size}


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


def _as_roots(archive_roots: str | Path | Sequence[str | Path]) -> list[Path]:
    if isinstance(archive_roots, (str, Path)):
        return [Path(archive_roots)]
    return [Path(root) for root in archive_roots]


def _tokens(path: Path) -> list[str]:
    return [token.lower() for token in re.split(r"[^A-Za-z0-9]+", str(path)) if token]


def _source_suffix(path: Path) -> str:
    suffixes = [suffix.lower() for suffix in path.suffixes]
    if len(suffixes) >= 2 and suffixes[-1] == ".gz":
        return f"{suffixes[-2]}.gz"
    return path.suffix.lower()


def _normalized_token(token: str) -> str:
    return re.sub(r"[^a-z0-9]", "", token.lower())


def _validate_override(value: str | None, *, allowed: frozenset[str], field_name: str) -> str | None:
    if value is None:
        return None
    normalized = value.lower()
    if normalized not in allowed:
        joined = ", ".join(sorted(allowed))
        raise ValueError(f"{field_name} must be one of: {joined}")
    return normalized


def _validate_venue_override(value: str | None) -> str | None:
    if value is None:
        return None
    return canonical_venue(value)


def _column_lookup(frame: pd.DataFrame) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for column in frame.columns:
        normalized = _normalized_token(str(column))
        if normalized and normalized not in lookup:
            lookup[normalized] = str(column)
    return lookup


def _first_content_value(frame: pd.DataFrame, aliases: Sequence[str]) -> str | None:
    lookup = _column_lookup(frame)
    for alias in aliases:
        column = lookup.get(_normalized_token(alias))
        if column is None:
            continue
        for value in frame[column].dropna().head(25):
            text = str(value).strip()
            if text and text.lower() != "nan":
                return text
    return None


def _venue_from_text(value: str) -> str | None:
    for token in [value, *re.split(r"[^A-Za-z0-9]+", value)]:
        candidate = VENUE_ALIASES.get(_normalized_token(token))
        if candidate is not None:
            return candidate
    normalized = _normalized_token(value)
    for alias, candidate in sorted(VENUE_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if _normalized_token(alias) in normalized:
            return candidate
    return None


def _normalize_interval_text(value: str, *, allow_numeric_only: bool = False) -> str | None:
    normalized = _normalized_token(value)
    if allow_numeric_only and normalized.isdigit():
        return f"{normalized}m"
    match = re.fullmatch(r"(\d+)(m|h|d|w|min|mins|minute|minutes|hour|hours|day|days|week|weeks)", normalized)
    if match is None:
        return None
    unit = match.group(2)
    unit_map = {
        "min": "m",
        "mins": "m",
        "minute": "m",
        "minutes": "m",
        "hour": "h",
        "hours": "h",
        "day": "d",
        "days": "d",
        "week": "w",
        "weeks": "w",
    }
    return f"{match.group(1)}{unit_map.get(unit, unit)}"


def _data_family_from_text(value: str) -> str | None:
    for token in [value, *re.split(r"[^A-Za-z0-9_]+", value)]:
        candidate = DATA_FAMILY_ALIASES.get(_normalized_token(token))
        if candidate is not None:
            return candidate
    normalized = _normalized_token(value)
    for alias, candidate in sorted(DATA_FAMILY_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if _normalized_token(alias) in normalized:
            return candidate
    return None


def _symbol_from_text(value: str, *, venue: str) -> str | None:
    upper = str(value).upper()
    tokens = [token for token in re.split(r"[^A-Z0-9]+", upper) if token]
    compact = re.sub(r"[^A-Z0-9]+", "", upper)
    compact_candidates = [compact]
    if compact.endswith("SWAP"):
        compact_candidates.append(compact[: -len("SWAP")])
    for candidate in compact_candidates:
        if len(candidate) >= 5 and candidate.endswith(("USDT", "USDC", "USD", "PERP")) and any(char.isalpha() for char in candidate):
            return candidate
    for token in tokens:
        if len(token) >= 5 and token.endswith(("USDT", "USDC", "USD", "PERP")) and any(char.isalpha() for char in token):
            return token
    for index, token in enumerate(tokens[:-1]):
        if token in BASE_TOKENS and tokens[index + 1] in QUOTE_TOKENS:
            return f"{token}{tokens[index + 1]}"
    if venue == "hyperliquid":
        for token in tokens:
            if token in BASE_TOKENS:
                return token
        if compact in BASE_TOKENS:
            return compact
    return None


def _infer_venue(path: Path, *, forced_venue: str | None, frame: pd.DataFrame | None = None) -> tuple[str, str]:
    if forced_venue is not None:
        return forced_venue, "override"
    for token in _tokens(path):
        candidate = VENUE_ALIASES.get(_normalized_token(token))
        if candidate is not None:
            return candidate, "path"
    normalized_path = _normalized_token(str(path))
    for alias, candidate in VENUE_ALIASES.items():
        if _normalized_token(alias) in normalized_path:
            return candidate, "path"
    if frame is not None:
        content_value = _first_content_value(frame, CONTENT_VENUE_COLUMNS)
        if content_value is not None:
            candidate = _venue_from_text(content_value)
            if candidate is not None:
                return candidate, "content"
    return "local_manifest", "default"


def _infer_data_family(path: Path, *, forced_data_family: str | None, frame: pd.DataFrame | None = None) -> tuple[str, str]:
    if forced_data_family is not None:
        return forced_data_family, "override"
    for token in _tokens(path):
        candidate = DATA_FAMILY_ALIASES.get(_normalized_token(token))
        if candidate is not None:
            return candidate, "path"
    if frame is not None:
        content_value = _first_content_value(frame, CONTENT_DATA_FAMILY_COLUMNS)
        if content_value is not None:
            candidate = _data_family_from_text(content_value)
            if candidate is not None:
                return candidate, "content"
        normalized_columns = {_normalized_token(str(column)) for column in frame.columns}
        if normalized_columns.intersection({"fundingrate", "fundingtime", "nextfundingtime"}):
            return "funding", "content_columns"
        if normalized_columns.intersection({"openinterest", "oi"}):
            return "open_interest", "content_columns"
        if normalized_columns.intersection({"markprice", "indexprice", "oraclepx"}):
            return "mark_index", "content_columns"
        if normalized_columns.intersection(
            {
                "bids",
                "asks",
                "bidpx",
                "askpx",
                "bestbidpx",
                "bestaskpx",
                "bestbidprice",
                "bestaskprice",
                "l2bookflattened",
                "orderbook",
            }
        ):
            return "l2_book", "content_columns"
        has_trade_shape = bool(normalized_columns.intersection({"px", "price", "lastprice"})) and bool(
            normalized_columns.intersection({"sz", "size", "qty", "quantity", "amount"})
        )
        has_ohlc_shape = {"open", "high", "low"}.issubset(normalized_columns)
        if has_trade_shape and not has_ohlc_shape:
            return "trade", "content_columns"
    return "kline", "default"


def _infer_interval(path: Path, *, forced_interval: str | None, frame: pd.DataFrame | None = None) -> tuple[str | None, str]:
    if forced_interval is not None:
        return forced_interval, "override"
    for token in _tokens(path):
        candidate = _normalize_interval_text(token)
        if candidate is not None:
            return candidate, "path"
    if frame is not None:
        content_value = _first_content_value(frame, CONTENT_INTERVAL_COLUMNS)
        if content_value is not None:
            candidate = _normalize_interval_text(content_value, allow_numeric_only=True)
            if candidate is not None:
                return candidate, "content"
    return None, "missing"


def _infer_symbol(
    path: Path,
    *,
    forced_symbol: str | None,
    venue: str,
    frame: pd.DataFrame | None = None,
) -> tuple[str | None, str]:
    if forced_symbol is not None:
        return forced_symbol.upper(), "override"
    upper_tokens = [token.upper() for token in re.split(r"[^A-Za-z0-9]+", str(path)) if token]
    for token in upper_tokens:
        if len(token) < 5:
            continue
        if token.endswith(("USDT", "USDC", "USD", "PERP")) and any(char.isalpha() for char in token):
            return token, "path"
    for index, token in enumerate(upper_tokens[:-1]):
        if token in BASE_TOKENS and upper_tokens[index + 1] in QUOTE_TOKENS:
            return f"{token}{upper_tokens[index + 1]}", "path"
    if venue == "hyperliquid":
        for token in upper_tokens:
            if token in BASE_TOKENS:
                return token, "path"
    if frame is not None:
        for aliases in (CONTENT_SYMBOL_COLUMNS, CONTENT_BASE_COLUMNS):
            content_value = _first_content_value(frame, aliases)
            if content_value is None:
                continue
            candidate = _symbol_from_text(content_value, venue=venue)
            if candidate is not None:
                return candidate, "content"
        base_value = _first_content_value(frame, CONTENT_BASE_COLUMNS)
        quote_value = _first_content_value(frame, CONTENT_QUOTE_COLUMNS)
        if base_value is not None and quote_value is not None:
            base = re.sub(r"[^A-Z0-9]+", "", base_value.upper())
            quote = re.sub(r"[^A-Z0-9]+", "", quote_value.upper())
            if base and quote:
                return f"{base}{quote}", "content"
    return None, "missing"


def _bounds(frame: pd.DataFrame) -> tuple[str | None, str | None]:
    if frame.empty or "timestamp" not in frame.columns:
        return None, None
    timestamps = pd.to_datetime(frame["timestamp"], utc=True)
    return timestamps.min().date().isoformat(), timestamps.max().date().isoformat()


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


def _overlaps_requested_window(
    *,
    window_start: str,
    window_end: str,
    requested_window: DataWindow | None,
) -> bool:
    if requested_window is None:
        return True
    observed_start = pd.Timestamp(window_start).date()
    observed_end = pd.Timestamp(window_end).date()
    return observed_end >= requested_window.start and observed_start <= requested_window.end


def _safe_component(value: str | None) -> str:
    if value is None:
        return "na"
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or "na"


def _descriptor_id(
    *,
    path: Path,
    venue: str,
    symbol: str,
    data_family: str,
    interval: str | None,
    window_start: str,
    window_end: str,
) -> str:
    digest = digest_payload(
        {
            "path": str(path),
            "venue": venue,
            "symbol": symbol,
            "data_family": data_family,
            "interval": interval,
            "window_start": window_start,
            "window_end": window_end,
        },
        prefix="sbxarchive",
        length=12,
    ).split("-", 1)[1]
    return "-".join(
        [
            _safe_component(venue),
            _safe_component(symbol),
            _safe_component(data_family),
            _safe_component(interval),
            digest,
        ]
    )


def _iter_files(roots: Iterable[Path], *, max_files: int) -> tuple[list[Path], bool]:
    return bounded_discover_files(
        roots,
        max_files=max_files,
        missing_root_message="sandbox archive root not found",
    )


def _base_row(
    path: Path,
    *,
    source_integrity: dict[str, Any],
    requested_window: DataWindow | None = None,
) -> dict[str, Any]:
    return {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_archive_manifest_build_row",
        **_requested_window_payload(requested_window),
        "source_path": str(path),
        "source_suffix": _source_suffix(path),
        "source_sha256": source_integrity.get("sha256"),
        "source_byte_size": source_integrity.get("byte_size"),
        "descriptor_id": None,
        "venue": None,
        "symbol": None,
        "data_family": None,
        "interval": None,
        "venue_inference_source": None,
        "symbol_inference_source": None,
        "data_family_inference_source": None,
        "interval_inference_source": None,
        "status": "skipped",
        "skip_reasons": [],
        "normalized_row_count": 0,
        "window_start": None,
        "window_end": None,
        "columns": [],
        "alias_columns": {},
        "alias_count": 0,
        "derived_columns": {},
        "derived_count": 0,
        "source_transformations": {},
        "source_transformation_count": 0,
        **_container_metadata_row_payload({}),
        "assigned_binance_kline_columns": False,
        "has_high_low": False,
    }


def _included_row(
    path: Path,
    *,
    descriptor: VenueArchiveDescriptor,
    frame: pd.DataFrame,
    source_integrity: dict[str, Any],
    inference_sources: dict[str, str],
    requested_window: DataWindow | None = None,
) -> dict[str, Any]:
    window_start, window_end = _bounds(frame)
    columns = [str(column) for column in frame.columns]
    metadata = dict(frame.attrs.get("sandbox_normalization_metadata") or {})
    row = {
        **_base_row(path, source_integrity=source_integrity, requested_window=requested_window),
        "descriptor_id": descriptor.descriptor_id,
        "venue": descriptor.venue,
        "symbol": descriptor.symbol,
        "data_family": descriptor.data_family,
        "interval": descriptor.interval,
        "venue_inference_source": inference_sources.get("venue"),
        "symbol_inference_source": inference_sources.get("symbol"),
        "data_family_inference_source": inference_sources.get("data_family"),
        "interval_inference_source": inference_sources.get("interval"),
        "status": "included",
        "normalized_row_count": int(len(frame)),
        "window_start": window_start,
        "window_end": window_end,
        "columns": columns,
        "alias_columns": metadata.get("alias_columns", {}),
        "alias_count": int(metadata.get("alias_count", 0) or 0),
        "derived_columns": metadata.get("derived_columns", {}),
        "derived_count": int(metadata.get("derived_count", 0) or 0),
        "source_transformations": metadata.get("source_transformations", {}),
        "source_transformation_count": int(metadata.get("source_transformation_count", 0) or 0),
        **_container_metadata_row_payload(metadata),
        "assigned_binance_kline_columns": bool(metadata.get("assigned_binance_kline_columns", False)),
        "has_high_low": "high" in columns and "low" in columns,
    }
    require_sandbox_boundary(row, payload_name="sandbox_archive_manifest_build_row")
    return row


def _skipped_row(
    path: Path,
    *,
    reasons: list[str],
    source_integrity: dict[str, Any],
    requested_window: DataWindow | None = None,
) -> dict[str, Any]:
    row = {
        **_base_row(path, source_integrity=source_integrity, requested_window=requested_window),
        "skip_reasons": reasons,
    }
    require_sandbox_boundary(row, payload_name="sandbox_archive_manifest_skip_row")
    return row


def _skipped_loaded_row(
    path: Path,
    *,
    reasons: list[str],
    frame: pd.DataFrame,
    source_integrity: dict[str, Any],
    requested_window: DataWindow | None = None,
) -> dict[str, Any]:
    window_start, window_end = _bounds(frame)
    columns = [str(column) for column in frame.columns]
    metadata = dict(frame.attrs.get("sandbox_normalization_metadata") or {})
    row = {
        **_base_row(path, source_integrity=source_integrity, requested_window=requested_window),
        "skip_reasons": reasons,
        "normalized_row_count": int(len(frame)),
        "window_start": window_start,
        "window_end": window_end,
        "columns": columns,
        "alias_columns": metadata.get("alias_columns", {}),
        "alias_count": int(metadata.get("alias_count", 0) or 0),
        "derived_columns": metadata.get("derived_columns", {}),
        "derived_count": int(metadata.get("derived_count", 0) or 0),
        "source_transformations": metadata.get("source_transformations", {}),
        "source_transformation_count": int(metadata.get("source_transformation_count", 0) or 0),
        **_container_metadata_row_payload(metadata),
        "assigned_binance_kline_columns": bool(metadata.get("assigned_binance_kline_columns", False)),
        "has_high_low": "high" in columns and "low" in columns,
    }
    require_sandbox_boundary(row, payload_name="sandbox_archive_manifest_loaded_skip_row")
    return row


def build_sandbox_archive_manifest(
    archive_roots: str | Path | Sequence[str | Path],
    *,
    output_dir: str | Path,
    venue: str | None = None,
    symbol: str | None = None,
    data_family: str | None = None,
    interval: str | None = None,
    max_files: int = 5000,
    requested_window: DataWindow | None = None,
) -> dict[str, Any]:
    roots = _as_roots(archive_roots)
    forced_venue = _validate_venue_override(venue)
    forced_data_family = _validate_override(data_family, allowed=ALLOWED_DATA_FAMILIES, field_name="data_family")
    forced_interval = interval.lower() if interval is not None else None
    forced_symbol = symbol.upper() if symbol is not None else None
    files, truncated = _iter_files(roots, max_files=max_files)

    descriptors: list[VenueArchiveDescriptor] = []
    rows: list[dict[str, Any]] = []
    for path in files:
        resolved_path = path.resolve()
        source_integrity = _file_integrity(resolved_path)
        if _source_suffix(resolved_path) not in SUPPORTED_ARCHIVE_SUFFIXES:
            rows.append(
                _skipped_row(
                    resolved_path,
                    reasons=["unsupported_suffix"],
                    source_integrity=source_integrity,
                    requested_window=requested_window,
                )
            )
            continue
        try:
            frame = load_market_frame(resolved_path)
        except Exception as exc:  # noqa: BLE001 - builder reports loader failures as skipped rows.
            rows.append(
                _skipped_row(
                    resolved_path,
                    reasons=[f"load_error:{type(exc).__name__}:{exc}"],
                    source_integrity=source_integrity,
                    requested_window=requested_window,
                )
            )
            continue
        if frame.empty:
            rows.append(
                _skipped_row(
                    resolved_path,
                    reasons=["no_normalized_2024_plus_rows"],
                    source_integrity=source_integrity,
                    requested_window=requested_window,
                )
            )
            continue

        inferred_venue, venue_source = _infer_venue(resolved_path, forced_venue=forced_venue, frame=frame)
        inferred_symbol, symbol_source = _infer_symbol(
            resolved_path,
            forced_symbol=forced_symbol,
            venue=inferred_venue,
            frame=frame,
        )
        inferred_data_family, data_family_source = _infer_data_family(
            resolved_path,
            forced_data_family=forced_data_family,
            frame=frame,
        )
        inferred_interval, interval_source = _infer_interval(
            resolved_path,
            forced_interval=forced_interval,
            frame=frame,
        )
        if inferred_symbol is None:
            rows.append(
                _skipped_loaded_row(
                    resolved_path,
                    reasons=["symbol_not_inferred"],
                    frame=frame,
                    source_integrity=source_integrity,
                    requested_window=requested_window,
                )
            )
            continue
        window_start, window_end = _bounds(frame)
        if window_start is None or window_end is None:
            rows.append(
                _skipped_row(
                    resolved_path,
                    reasons=["timestamp_bounds_not_available"],
                    source_integrity=source_integrity,
                    requested_window=requested_window,
                )
            )
            continue
        if not _overlaps_requested_window(
            window_start=window_start,
            window_end=window_end,
            requested_window=requested_window,
        ):
            rows.append(
                _skipped_loaded_row(
                    resolved_path,
                    reasons=["outside_requested_window"],
                    frame=frame,
                    source_integrity=source_integrity,
                    requested_window=requested_window,
                )
            )
            continue

        descriptor = VenueArchiveDescriptor(
            descriptor_id=_descriptor_id(
                path=resolved_path,
                venue=inferred_venue,
                symbol=inferred_symbol,
                data_family=inferred_data_family,
                interval=inferred_interval,
                window_start=window_start,
                window_end=window_end,
            ),
            venue=inferred_venue,
            symbol=inferred_symbol,
            data_family=inferred_data_family,
            interval=inferred_interval,
            data_path=resolved_path,
            window=DataWindow(window_start, window_end),
            source_access_mode="local_archive_manifest_builder",
            checksum_policy="required_for_strict_evidence",
            diagnostic_only=True,
            source_integrity=source_integrity,
            notes=("generated_by_sandbox_archive_manifest_builder",),
        )
        descriptors.append(descriptor)
        rows.append(
            _included_row(
                resolved_path,
                descriptor=descriptor,
                frame=frame,
                source_integrity=source_integrity,
                inference_sources={
                    "venue": venue_source,
                    "symbol": symbol_source,
                    "data_family": data_family_source,
                    "interval": interval_source,
                },
                requested_window=requested_window,
            )
        )

    descriptor_payloads = [descriptor.to_payload() for descriptor in descriptors]
    for payload in descriptor_payloads:
        require_sandbox_boundary(payload, payload_name="sandbox_archive_manifest_descriptor")

    manifest_id = digest_payload(
        {
            "archive_roots": [str(root.resolve()) for root in roots],
            "forced_venue": forced_venue,
            "forced_symbol": forced_symbol,
            "forced_data_family": forced_data_family,
            "forced_interval": forced_interval,
            "requested_window": _requested_window_payload(requested_window),
            "max_files": max_files,
            "descriptor_ids": [descriptor.descriptor_id for descriptor in descriptors],
            "source_integrity": {
                descriptor.descriptor_id: descriptor.source_integrity for descriptor in descriptors
            },
            "skipped": [
                {
                    "source_path": row["source_path"],
                    "source_sha256": row["source_sha256"],
                    "source_byte_size": row["source_byte_size"],
                    "skip_reasons": row["skip_reasons"],
                }
                for row in rows
                if row["status"] == "skipped"
            ],
        },
        prefix="sbxarchivemanifest",
        length=24,
    )
    destination = Path(output_dir) / manifest_id
    destination.mkdir(parents=True, exist_ok=True)
    manifest_path = destination / ARCHIVE_MANIFEST_JSON_NAME
    report_json_path = destination / ARCHIVE_MANIFEST_BUILD_REPORT_JSON_NAME
    report_parquet_path = destination / ARCHIVE_MANIFEST_BUILD_REPORT_PARQUET_NAME

    venue_counts: dict[str, int] = {}
    symbol_counts: dict[str, int] = {}
    data_family_counts: dict[str, int] = {}
    for descriptor in descriptors:
        venue_counts[descriptor.venue] = venue_counts.get(descriptor.venue, 0) + 1
        symbol_counts[descriptor.symbol] = symbol_counts.get(descriptor.symbol, 0) + 1
        data_family_counts[descriptor.data_family] = data_family_counts.get(descriptor.data_family, 0) + 1

    manifest_payload = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_archive_manifest",
        "manifest_id": manifest_id,
        "archive_roots": [str(root.resolve()) for root in roots],
        **_requested_window_payload(requested_window),
        "descriptor_count": len(descriptor_payloads),
        "venue_archive_manifest_path": str(manifest_path),
        "build_report_json_path": str(report_json_path),
        "build_report_parquet_path": str(report_parquet_path),
        "venue_archives": descriptor_payloads,
    }
    require_sandbox_boundary(manifest_payload, payload_name="sandbox_archive_manifest")

    report_payload = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_archive_manifest_build_report",
        "manifest_id": manifest_id,
        "archive_roots": [str(root.resolve()) for root in roots],
        **_requested_window_payload(requested_window),
        "output_dir": str(destination),
        "venue_archive_manifest_path": str(manifest_path),
        "build_report_json_path": str(report_json_path),
        "build_report_parquet_path": str(report_parquet_path),
        "file_count": len(files),
        "descriptor_count": len(descriptor_payloads),
        "skipped_count": sum(1 for row in rows if row["status"] == "skipped"),
        "truncated": truncated,
        "max_files": max_files,
        "venue_counts": dict(sorted(venue_counts.items())),
        "symbol_counts": dict(sorted(symbol_counts.items())),
        "data_family_counts": dict(sorted(data_family_counts.items())),
        "descriptors": descriptor_payloads,
        "files": rows,
    }
    require_sandbox_boundary(report_payload, payload_name="sandbox_archive_manifest_build_report")

    frame = pd.DataFrame([_row_for_parquet(row) for row in rows])
    if frame.empty:
        frame = pd.DataFrame(columns=["source_path", "status", *SANDBOX_BOUNDARY_FLAGS])
    frame.to_parquet(report_parquet_path, index=False)
    manifest_path.write_text(
        json.dumps(manifest_payload, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    report_json_path.write_text(
        json.dumps(report_payload, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    return report_payload
