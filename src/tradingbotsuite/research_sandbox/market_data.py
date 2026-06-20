from __future__ import annotations

from io import BytesIO
from dataclasses import dataclass, field
import gzip
import hashlib
import json
import os
import tarfile
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd

from tradingbotsuite.research_sandbox.spec import MIN_SANDBOX_DATE, VenueArchiveDescriptor


BINANCE_KLINE_COLUMNS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_asset_volume",
    "number_of_trades",
    "taker_buy_base_asset_volume",
    "taker_buy_quote_asset_volume",
    "ignore",
]

TIMESTAMP_ALIASES = (
    "timestamp",
    "open_time",
    "start_time",
    "starttime",
    "start",
    "time",
    "datetime",
    "date",
    "ts",
    "t",
)

COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "open": ("open", "open_price", "openprice", "o", "px_open"),
    "high": ("high", "high_price", "highprice", "h", "px_high"),
    "low": ("low", "low_price", "lowprice", "l", "px_low"),
    "close": (
        "close",
        "close_price",
        "closeprice",
        "last",
        "last_price",
        "lastprice",
        "price",
        "px",
        "mark_price",
        "markprice",
        "mark_px",
        "markpx",
        "index_price",
        "indexprice",
        "index_px",
        "indexpx",
        "idx_price",
        "idxprice",
        "idx_px",
        "idxpx",
        "mid",
        "mid_price",
        "midprice",
        "mid_px",
        "midpx",
        "c",
        "px_close",
    ),
    "volume": ("volume", "vol", "base_volume", "basevolume", "size", "sz", "qty", "quantity", "amount", "v"),
}

BID_PRICE_ALIASES = (
    "bid",
    "bid_price",
    "bidprice",
    "bid_px",
    "bidpx",
    "best_bid",
    "bestbid",
    "best_bid_price",
    "bestbidprice",
    "best_bid_px",
    "bestbidpx",
)

ASK_PRICE_ALIASES = (
    "ask",
    "ask_price",
    "askprice",
    "ask_px",
    "askpx",
    "best_ask",
    "bestask",
    "best_ask_price",
    "bestaskprice",
    "best_ask_px",
    "bestaskpx",
)

MARKET_DATA_MEMBER_SUFFIX_PRIORITY = (
    ".csv",
    ".csv.gz",
    ".tsv",
    ".tsv.gz",
    ".json",
    ".json.gz",
    ".jsonl",
    ".jsonl.gz",
    ".ndjson",
    ".ndjson.gz",
)
CONTAINER_MEMBER_NAME_SAMPLE_LIMIT = 12
CONTAINER_MEMBER_READ_CHUNK_BYTES = 1024 * 1024


def _positive_int_from_env(name: str, default: int) -> int:
    raw_value = os.environ.get(name)
    if raw_value is None or str(raw_value).strip() == "":
        return default
    try:
        value = int(str(raw_value).strip())
    except ValueError:
        return default
    return value if value > 0 else default


MAX_CONTAINER_SELECTED_MEMBERS = _positive_int_from_env(
    "TRADINGBOTSUITE_SANDBOX_MAX_CONTAINER_SELECTED_MEMBERS",
    256,
)
MAX_CONTAINER_MEMBER_BYTES = _positive_int_from_env(
    "TRADINGBOTSUITE_SANDBOX_MAX_CONTAINER_MEMBER_BYTES",
    256 * 1024 * 1024,
)
MAX_CONTAINER_SELECTED_TOTAL_BYTES = _positive_int_from_env(
    "TRADINGBOTSUITE_SANDBOX_MAX_CONTAINER_SELECTED_TOTAL_BYTES",
    1024 * 1024 * 1024,
)
MAX_CONTAINER_GZIP_DECOMPRESSED_BYTES = _positive_int_from_env(
    "TRADINGBOTSUITE_SANDBOX_MAX_CONTAINER_GZIP_DECOMPRESSED_BYTES",
    512 * 1024 * 1024,
)


def _normalized_name(value: object) -> str:
    return "".join(char for char in str(value).strip().lower() if char.isalnum())


def _looks_like_headerless_numeric_table(frame: pd.DataFrame) -> bool:
    if frame.empty or len(frame.columns) == 0:
        return False
    try:
        float(str(frame.columns[0]))
    except ValueError:
        return False
    return True


def _read_text_table(path: Path, *, sep: str = ",") -> pd.DataFrame:
    return _read_text_table_source(path, sep=sep)


def _read_text_table_source(source: Any, *, sep: str = ",") -> pd.DataFrame:
    try:
        frame = pd.read_csv(source, sep=sep)
    except pd.errors.ParserError:
        if hasattr(source, "seek"):
            source.seek(0)
        return pd.read_csv(source, sep=sep, header=None)
    normalized_columns = {_normalized_name(column) for column in frame.columns}
    has_known_time = bool({_normalized_name(alias) for alias in TIMESTAMP_ALIASES}.intersection(normalized_columns))
    has_known_close = bool({_normalized_name(alias) for alias in COLUMN_ALIASES["close"]}.intersection(normalized_columns))
    has_known_header = has_known_time and has_known_close
    if not has_known_header and frame.shape[1] >= 6:
        if not _looks_like_headerless_numeric_table(frame):
            return frame
        if hasattr(source, "seek"):
            source.seek(0)
        return pd.read_csv(source, sep=sep, header=None)
    return frame


def _read_gzip_text_table(path: Path, *, sep: str = ",") -> pd.DataFrame:
    return _read_text_table_source(path, sep=sep)


def _read_json_table(path: Path) -> pd.DataFrame:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return _json_payload_frame(payload)


def _first_normalized_key(payload: dict[Any, Any], name: str) -> Any | None:
    normalized = _normalized_name(name)
    for key in payload:
        if _normalized_name(key) == normalized:
            return key
    return None


def _first_level(levels: Any) -> Any | None:
    if isinstance(levels, (list, tuple)):
        return levels[0] if levels else None
    if isinstance(levels, dict):
        return levels
    return None


def _l2_sides(levels: Any) -> tuple[Any, Any] | None:
    if isinstance(levels, dict):
        bid_key = next(
            (key for key in levels if _normalized_name(key) in {"bid", "bids"}),
            None,
        )
        ask_key = next(
            (key for key in levels if _normalized_name(key) in {"ask", "asks"}),
            None,
        )
        if bid_key is None or ask_key is None:
            return None
        return levels[bid_key], levels[ask_key]
    if isinstance(levels, (list, tuple)) and len(levels) >= 2:
        return levels[0], levels[1]
    return None


def _level_value(level: Any, aliases: tuple[str, ...], *, sequence_index: int) -> Any | None:
    if isinstance(level, dict):
        lookup = {_normalized_name(key): value for key, value in level.items()}
        for alias in aliases:
            value = lookup.get(_normalized_name(alias))
            if value is not None:
                return value
        return None
    if isinstance(level, (list, tuple)) and len(level) > sequence_index:
        return level[sequence_index]
    return None


def _l2_parent_metadata(payload: dict[Any, Any]) -> dict[str, Any]:
    return {
        str(key): value
        for key, value in payload.items()
        if _normalized_name(key) not in {"data", "rows", "marketframe", "klines", "levels"}
        and not isinstance(value, (dict, list, tuple))
    }


def _flatten_l2_book_row(payload: Any, *, parent_metadata: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    levels_key = _first_normalized_key(payload, "levels")
    if levels_key is None:
        data_key = _first_normalized_key(payload, "data")
        nested = payload.get(data_key) if data_key is not None else None
        if isinstance(nested, dict):
            nested_parent = {**parent_metadata, **_l2_parent_metadata(payload)}
            return _flatten_l2_book_row(nested, parent_metadata=nested_parent)
        return None

    sides = _l2_sides(payload[levels_key])
    if sides is None:
        return None
    bid_level = _first_level(sides[0])
    ask_level = _first_level(sides[1])
    bid_px = _level_value(bid_level, ("px", "price", "bid_px", "bid_price"), sequence_index=0)
    ask_px = _level_value(ask_level, ("px", "price", "ask_px", "ask_price"), sequence_index=0)
    if bid_px is None or ask_px is None:
        return None

    flattened = dict(parent_metadata)
    for key, value in payload.items():
        if key != levels_key:
            flattened[str(key)] = value
    flattened["bestBidPx"] = bid_px
    flattened["bestAskPx"] = ask_px
    bid_size = _level_value(bid_level, ("sz", "size", "bid_size", "bid_sz"), sequence_index=1)
    ask_size = _level_value(ask_level, ("sz", "size", "ask_size", "ask_sz"), sequence_index=1)
    if bid_size is not None:
        flattened["bidSize"] = bid_size
    if ask_size is not None:
        flattened["askSize"] = ask_size
    bid_count = _level_value(bid_level, ("n", "count", "orders", "order_count"), sequence_index=2)
    ask_count = _level_value(ask_level, ("n", "count", "orders", "order_count"), sequence_index=2)
    if bid_count is not None:
        flattened["bidOrderCount"] = bid_count
    if ask_count is not None:
        flattened["askOrderCount"] = ask_count
    flattened["l2BookFlattened"] = True
    return flattened


def _flatten_l2_book_rows(rows: Any, *, parent_metadata: dict[str, Any]) -> tuple[Any, int]:
    if isinstance(rows, dict):
        flattened = _flatten_l2_book_row(rows, parent_metadata=parent_metadata)
        if flattened is not None:
            return [flattened], 1
        return rows, 0
    if not isinstance(rows, list):
        return rows, 0

    output_rows: list[Any] = []
    flattened_count = 0
    for row in rows:
        flattened = _flatten_l2_book_row(row, parent_metadata=parent_metadata)
        if flattened is None:
            output_rows.append(row)
            continue
        output_rows.append(flattened)
        flattened_count += 1
    return output_rows, flattened_count


def _json_payload_frame(payload: Any) -> pd.DataFrame:
    rows: Any = payload
    parent_metadata: dict[str, Any] = {}
    if isinstance(payload, dict):
        parent_metadata = _l2_parent_metadata(payload)
        for key in ("rows", "data", "market_frame", "klines"):
            if key in payload:
                rows = payload[key]
                break
    rows, flattened_count = _flatten_l2_book_rows(rows, parent_metadata=parent_metadata)
    frame = pd.DataFrame(rows)
    if flattened_count:
        frame.attrs["sandbox_source_transformations"] = {
            "hyperliquid_l2_levels": {
                "method": "best_bid_ask_from_levels",
                "row_count": flattened_count,
            }
        }
    return frame


def _read_gzip_json_table(path: Path) -> pd.DataFrame:
    with gzip.open(path, mode="rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    return _json_payload_frame(payload)


def _read_jsonl_table(path: Path) -> pd.DataFrame:
    return _jsonl_text_frame(path.read_text(encoding="utf-8"))


def _read_gzip_jsonl_table(path: Path) -> pd.DataFrame:
    with gzip.open(path, mode="rt", encoding="utf-8") as handle:
        return _jsonl_text_frame(handle.read())


def _jsonl_text_frame(text: str) -> pd.DataFrame:
    rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    return _json_payload_frame(rows)


def _container_member_suffix(name: str) -> str:
    suffixes = [suffix.lower() for suffix in Path(name).suffixes]
    if len(suffixes) >= 2 and suffixes[-1] == ".gz":
        return f"{suffixes[-2]}.gz"
    return Path(name).suffix.lower()


def _container_member_metadata(
    *,
    container_kind: str,
    selected_suffix: str,
    selected_member_names: list[str],
    members_by_suffix: dict[str, list[Any]],
    selected_member_declared_byte_total: int | None = None,
    selected_member_declared_byte_count: int = 0,
) -> dict[str, Any]:
    suffix_counts = {str(suffix): len(members) for suffix, members in sorted(members_by_suffix.items())}
    loadable_member_count = sum(
        count for suffix, count in suffix_counts.items() if suffix in MARKET_DATA_MEMBER_SUFFIX_PRIORITY
    )
    selected_sample = selected_member_names[:CONTAINER_MEMBER_NAME_SAMPLE_LIMIT]
    return {
        "container_kind": container_kind,
        "selected_member_suffix": selected_suffix,
        "selected_member_count": len(selected_member_names),
        "selected_member_name_sample": selected_sample,
        "selected_member_names_truncated": len(selected_member_names) > len(selected_sample),
        "available_member_suffix_counts": suffix_counts,
        "available_member_suffix_count": len(suffix_counts),
        "loadable_member_count": loadable_member_count,
        "selected_member_declared_byte_total": selected_member_declared_byte_total,
        "selected_member_declared_byte_count": selected_member_declared_byte_count,
        "container_loader_limits": {
            "max_selected_members": MAX_CONTAINER_SELECTED_MEMBERS,
            "max_member_bytes": MAX_CONTAINER_MEMBER_BYTES,
            "max_selected_total_bytes": MAX_CONTAINER_SELECTED_TOTAL_BYTES,
            "max_gzip_decompressed_bytes": MAX_CONTAINER_GZIP_DECOMPRESSED_BYTES,
        },
    }


def _attach_container_member_metadata(frame: pd.DataFrame, metadata: dict[str, Any]) -> pd.DataFrame:
    frame.attrs["sandbox_container_member_metadata"] = metadata
    return frame


def _container_member_name(member: Any) -> str:
    if isinstance(member, str):
        return member
    return str(getattr(member, "filename", None) or getattr(member, "name", None) or member)


def _container_member_declared_size(member: Any) -> int | None:
    raw_size = getattr(member, "file_size", None)
    if raw_size is None:
        raw_size = getattr(member, "size", None)
    if raw_size is None:
        return None
    try:
        size = int(raw_size)
    except (TypeError, ValueError):
        return None
    return size if size >= 0 else None


def _container_limit_error(
    reason: str,
    *,
    container_kind: str,
    path: Path,
    member_name: str,
    observed: int,
    limit: int,
) -> ValueError:
    return ValueError(
        f"{reason}: container_kind={container_kind} path={path} "
        f"member={member_name} observed={observed} limit={limit}"
    )


def _selected_member_bounds(
    *,
    container_kind: str,
    path: Path,
    suffix: str,
    members: list[Any],
) -> tuple[int | None, int]:
    selected_count = len(members)
    if selected_count > MAX_CONTAINER_SELECTED_MEMBERS:
        raise _container_limit_error(
            "container_selected_member_count_limit_exceeded",
            container_kind=container_kind,
            path=path,
            member_name=suffix,
            observed=selected_count,
            limit=MAX_CONTAINER_SELECTED_MEMBERS,
        )
    declared_total = 0
    declared_count = 0
    for member in members:
        declared_size = _container_member_declared_size(member)
        if declared_size is None:
            continue
        declared_count += 1
        member_name = _container_member_name(member)
        if declared_size > MAX_CONTAINER_MEMBER_BYTES:
            raise _container_limit_error(
                "container_member_bytes_limit_exceeded",
                container_kind=container_kind,
                path=path,
                member_name=member_name,
                observed=declared_size,
                limit=MAX_CONTAINER_MEMBER_BYTES,
            )
        declared_total += declared_size
        if declared_total > MAX_CONTAINER_SELECTED_TOTAL_BYTES:
            raise _container_limit_error(
                "container_selected_member_total_bytes_limit_exceeded",
                container_kind=container_kind,
                path=path,
                member_name=suffix,
                observed=declared_total,
                limit=MAX_CONTAINER_SELECTED_TOTAL_BYTES,
            )
    if declared_count == 0:
        return None, 0
    return declared_total, declared_count


def _read_binary_limited(
    handle: Any,
    *,
    limit: int,
    reason: str,
    container_kind: str,
    path: Path,
    member_name: str,
) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = handle.read(CONTAINER_MEMBER_READ_CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise _container_limit_error(
                reason,
                container_kind=container_kind,
                path=path,
                member_name=member_name,
                observed=total,
                limit=limit,
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _gzip_decompress_limited(
    payload: bytes,
    *,
    container_kind: str,
    path: Path,
    member_name: str,
) -> bytes:
    with gzip.GzipFile(fileobj=BytesIO(payload), mode="rb") as handle:
        return _read_binary_limited(
            handle,
            limit=MAX_CONTAINER_GZIP_DECOMPRESSED_BYTES,
            reason="container_member_decompressed_bytes_limit_exceeded",
            container_kind=container_kind,
            path=path,
            member_name=member_name,
        )


def _read_zip_table(path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(path) as archive:
        names = sorted(name for name in archive.namelist() if not name.endswith("/"))
        members_by_suffix: dict[str, list[str]] = {}
        for name in names:
            members_by_suffix.setdefault(_container_member_suffix(name), []).append(name)
        for suffix in MARKET_DATA_MEMBER_SUFFIX_PRIORITY:
            members = members_by_suffix.get(suffix)
            if not members:
                continue
            member_infos = [archive.getinfo(member) for member in members]
            declared_total, declared_count = _selected_member_bounds(
                container_kind="zip",
                path=path,
                suffix=suffix,
                members=member_infos,
            )
            frames: list[pd.DataFrame] = []
            for member in members:
                with archive.open(member) as handle:
                    payload = _read_binary_limited(
                        handle,
                        limit=MAX_CONTAINER_MEMBER_BYTES,
                        reason="container_member_bytes_limit_exceeded",
                        container_kind="zip",
                        path=path,
                        member_name=member,
                    )
                    frames.append(
                        _table_from_member_payload(
                            payload,
                            suffix=suffix,
                            container_kind="zip",
                            path=path,
                            member_name=member,
                        )
                    )
            metadata = _container_member_metadata(
                container_kind="zip",
                selected_suffix=suffix,
                selected_member_names=members,
                members_by_suffix=members_by_suffix,
                selected_member_declared_byte_total=declared_total,
                selected_member_declared_byte_count=declared_count,
            )
            return _attach_container_member_metadata(_concat_member_frames(frames), metadata)
    raise ValueError(f"zip archive contains no CSV/TSV/JSON/JSONL/NDJSON market data member: {path}")


def _table_from_member_payload(
    payload: bytes,
    *,
    suffix: str,
    container_kind: str = "container",
    path: Path | None = None,
    member_name: str = "<member>",
) -> pd.DataFrame:
    if suffix.endswith(".gz"):
        payload = _gzip_decompress_limited(
            payload,
            container_kind=container_kind,
            path=path or Path("<memory>"),
            member_name=member_name,
        )
        suffix = suffix[: -len(".gz")]
    if suffix == ".csv":
        return _read_text_table_source(BytesIO(payload))
    if suffix == ".tsv":
        return _read_text_table_source(BytesIO(payload), sep="\t")
    if suffix == ".json":
        return _json_payload_frame(json.loads(payload.decode("utf-8")))
    return _jsonl_text_frame(payload.decode("utf-8"))


def _merge_source_transformations(frames: list[pd.DataFrame]) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for frame in frames:
        transformations = frame.attrs.get("sandbox_source_transformations") or {}
        for key, value in transformations.items():
            if not isinstance(value, dict):
                continue
            normalized_value = {str(name): item for name, item in value.items()}
            row_count = int(normalized_value.pop("row_count", 0) or 0)
            target = merged.setdefault(str(key), normalized_value)
            if "row_count" in value:
                target["row_count"] = int(target.get("row_count", 0) or 0) + row_count
    return merged


def _concat_member_frames(frames: list[pd.DataFrame]) -> pd.DataFrame:
    if len(frames) == 1:
        return frames[0]
    combined = pd.concat(frames, ignore_index=True, sort=False)
    source_transformations = _merge_source_transformations(frames)
    if source_transformations:
        combined.attrs["sandbox_source_transformations"] = source_transformations
    return combined


def _read_tar_table(path: Path) -> pd.DataFrame:
    with tarfile.open(path, mode="r:*") as archive:
        members_by_suffix: dict[str, list[tarfile.TarInfo]] = {}
        for member in sorted(archive.getmembers(), key=lambda item: item.name):
            if not member.isfile():
                continue
            members_by_suffix.setdefault(_container_member_suffix(member.name), []).append(member)
        for suffix in MARKET_DATA_MEMBER_SUFFIX_PRIORITY:
            members = members_by_suffix.get(suffix)
            if not members:
                continue
            declared_total, declared_count = _selected_member_bounds(
                container_kind="tar",
                path=path,
                suffix=suffix,
                members=members,
            )
            frames: list[pd.DataFrame] = []
            for member in members:
                handle = archive.extractfile(member)
                if handle is None:
                    continue
                with handle:
                    payload = _read_binary_limited(
                        handle,
                        limit=MAX_CONTAINER_MEMBER_BYTES,
                        reason="container_member_bytes_limit_exceeded",
                        container_kind="tar",
                        path=path,
                        member_name=member.name,
                    )
                    frames.append(
                        _table_from_member_payload(
                            payload,
                            suffix=suffix,
                            container_kind="tar",
                            path=path,
                            member_name=member.name,
                        )
                    )
            if frames:
                selected_member_names = [member.name for member in members]
                metadata = _container_member_metadata(
                    container_kind="tar",
                    selected_suffix=suffix,
                    selected_member_names=selected_member_names,
                    members_by_suffix=members_by_suffix,
                    selected_member_declared_byte_total=declared_total,
                    selected_member_declared_byte_count=declared_count,
                )
                return _attach_container_member_metadata(_concat_member_frames(frames), metadata)
    raise ValueError(f"tar archive contains no CSV/TSV/JSON/JSONL/NDJSON market data member: {path}")


def _compound_suffix(path: Path) -> str:
    suffixes = [suffix.lower() for suffix in path.suffixes]
    if len(suffixes) >= 2 and suffixes[-1] == ".gz":
        return f"{suffixes[-2]}.gz"
    return path.suffix.lower()


def _read_raw_table(path: Path) -> pd.DataFrame:
    suffix = _compound_suffix(path)
    if suffix == ".csv":
        return _read_text_table(path)
    if suffix == ".csv.gz":
        return _read_gzip_text_table(path)
    if suffix == ".tsv":
        return _read_text_table(path, sep="\t")
    if suffix == ".tsv.gz":
        return _read_gzip_text_table(path, sep="\t")
    if suffix == ".json":
        return _read_json_table(path)
    if suffix == ".json.gz":
        return _read_gzip_json_table(path)
    if suffix in {".jsonl", ".ndjson"}:
        return _read_jsonl_table(path)
    if suffix in {".jsonl.gz", ".ndjson.gz"}:
        return _read_gzip_jsonl_table(path)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix == ".zip":
        return _read_zip_table(path)
    if suffix in {".tar", ".tar.gz", ".tgz"}:
        return _read_tar_table(path)
    raise ValueError(f"unsupported sandbox market data format: {''.join(path.suffixes) or path.suffix}")


def _assign_binance_kline_columns(frame: pd.DataFrame) -> pd.DataFrame:
    if "close" in frame.columns and ("timestamp" in frame.columns or "open_time" in frame.columns):
        return frame
    normalized_columns = {_normalized_name(column) for column in frame.columns}
    has_known_time = bool({_normalized_name(alias) for alias in TIMESTAMP_ALIASES}.intersection(normalized_columns))
    has_known_close = bool({_normalized_name(alias) for alias in COLUMN_ALIASES["close"]}.intersection(normalized_columns))
    if has_known_time and has_known_close:
        return frame
    if frame.shape[1] < 6:
        return frame
    if not _looks_like_headerless_numeric_table(frame):
        return frame
    renamed = frame.copy()
    renamed.columns = BINANCE_KLINE_COLUMNS[: frame.shape[1]]
    return renamed


def _column_lookup(frame: pd.DataFrame) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for column in frame.columns:
        normalized = _normalized_name(column)
        if normalized and normalized not in lookup:
            lookup[normalized] = str(column)
    return lookup


def _first_alias_column(frame: pd.DataFrame, aliases: tuple[str, ...]) -> str | None:
    lookup = _column_lookup(frame)
    for alias in aliases:
        column = lookup.get(_normalized_name(alias))
        if column is not None:
            return column
    return None


def _looks_like_compact_yyyymmdd(values: pd.Series) -> bool:
    sample = values.dropna().astype(str).str.strip().head(25)
    if sample.empty:
        return False
    return bool(sample.str.fullmatch(r"\d{8}").all())


def _epoch_unit(numeric: pd.Series) -> str:
    median = float(numeric.dropna().abs().median())
    if median >= 100_000_000_000_000_000:
        return "ns"
    if median >= 100_000_000_000_000:
        return "us"
    if median >= 100_000_000_000:
        return "ms"
    return "s"


def _timestamp_series(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    if _looks_like_compact_yyyymmdd(values):
        return pd.to_datetime(values.astype(str).str.strip(), utc=True)
    if not numeric.dropna().empty:
        return pd.to_datetime(numeric, unit=_epoch_unit(numeric), utc=True)
    return pd.to_datetime(values, utc=True)


def _timestamp_from_columns(frame: pd.DataFrame) -> tuple[pd.Series, str]:
    column = _first_alias_column(frame, TIMESTAMP_ALIASES)
    if column is None:
        raise ValueError("sandbox market data requires timestamp, open_time, time, datetime, or venue timestamp alias")
    return _timestamp_series(frame[column]), column


def _bid_ask_midpoint_columns(frame: pd.DataFrame) -> tuple[str, str] | None:
    bid_column = _first_alias_column(frame, BID_PRICE_ALIASES)
    ask_column = _first_alias_column(frame, ASK_PRICE_ALIASES)
    if bid_column is None or ask_column is None:
        return None
    return bid_column, ask_column


def _close_series_from_columns(frame: pd.DataFrame) -> tuple[pd.Series, str | None, dict[str, Any] | None]:
    close_column = _first_alias_column(frame, COLUMN_ALIASES["close"])
    if close_column is not None:
        return pd.to_numeric(frame[close_column], errors="coerce"), close_column, None
    midpoint_columns = _bid_ask_midpoint_columns(frame)
    if midpoint_columns is None:
        raise ValueError("sandbox market data requires a close column or bid/ask price columns")
    bid_column, ask_column = midpoint_columns
    bid = pd.to_numeric(frame[bid_column], errors="coerce")
    ask = pd.to_numeric(frame[ask_column], errors="coerce")
    return (
        (bid + ask) / 2.0,
        None,
        {"method": "bid_ask_midpoint", "bid_column": bid_column, "ask_column": ask_column},
    )


def market_frame_normalization_metadata(frame: pd.DataFrame) -> dict[str, Any]:
    candidate = _assign_binance_kline_columns(frame)
    source_transformations = dict(frame.attrs.get("sandbox_source_transformations") or {})
    container_member_metadata = dict(frame.attrs.get("sandbox_container_member_metadata") or {})
    lookup = _column_lookup(candidate)
    aliases: dict[str, str] = {}
    for canonical, candidates in {"timestamp": TIMESTAMP_ALIASES, **COLUMN_ALIASES}.items():
        source = None
        for alias in candidates:
            column = lookup.get(_normalized_name(alias))
            if column is not None:
                source = column
                break
        if source is not None and source != canonical:
            aliases[canonical] = source
    derived_columns: dict[str, dict[str, str]] = {}
    if _first_alias_column(candidate, COLUMN_ALIASES["close"]) is None:
        midpoint_columns = _bid_ask_midpoint_columns(candidate)
        if midpoint_columns is not None:
            bid_column, ask_column = midpoint_columns
            derived_columns["close"] = {
                "method": "bid_ask_midpoint",
                "bid_column": bid_column,
                "ask_column": ask_column,
            }
    return {
        "input_columns": [str(column) for column in frame.columns],
        "assigned_binance_kline_columns": list(candidate.columns) != [str(column) for column in frame.columns],
        "alias_columns": aliases,
        "alias_count": len(aliases),
        "derived_columns": derived_columns,
        "derived_count": len(derived_columns),
        "source_transformations": source_transformations,
        "source_transformation_count": len(source_transformations),
        "container_member_metadata": container_member_metadata,
        "container_member_count": int(container_member_metadata.get("selected_member_count", 0) or 0),
    }


def normalize_market_frame(frame: pd.DataFrame) -> pd.DataFrame:
    candidate = _assign_binance_kline_columns(frame)
    metadata = market_frame_normalization_metadata(frame)
    close_series, _, close_derivation = _close_series_from_columns(candidate)
    if close_derivation is not None:
        metadata["derived_columns"]["close"] = close_derivation
        metadata["derived_count"] = len(metadata["derived_columns"])
    normalized = candidate.copy()
    timestamps, timestamp_column = _timestamp_from_columns(candidate)
    normalized["timestamp"] = timestamps
    normalized["close"] = close_series
    for canonical in ("open", "high", "low", "volume"):
        column = _first_alias_column(candidate, COLUMN_ALIASES[canonical])
        if column is not None:
            normalized[canonical] = pd.to_numeric(candidate[column], errors="coerce")
    if timestamp_column not in normalized.columns:
        normalized[timestamp_column] = candidate[timestamp_column]
    normalized = normalized.dropna(subset=["timestamp", "close"])
    normalized = normalized[normalized["timestamp"].dt.date >= MIN_SANDBOX_DATE]
    normalized = normalized.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last")
    normalized = normalized.reset_index(drop=True)
    normalized.attrs["sandbox_normalization_metadata"] = metadata
    return normalized


def load_market_frame(path: str | Path) -> pd.DataFrame:
    source_path = Path(path)
    return normalize_market_frame(_read_raw_table(source_path))


def _normalized_load_path(path: str | Path) -> str:
    return str(Path(path).expanduser().resolve())


def normalized_market_data_source_key(path: str | Path) -> str:
    return _normalized_load_path(path)


def _file_integrity(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"sha256": digest.hexdigest(), "byte_size": path.stat().st_size}


@dataclass
class SandboxMarketDataCache:
    frame_cache: dict[str, pd.DataFrame] = field(default_factory=dict)
    integrity_cache: dict[str, dict[str, Any]] = field(default_factory=dict)
    frame_cache_hit_count: int = 0
    frame_cache_miss_count: int = 0
    integrity_cache_hit_count: int = 0
    integrity_cache_miss_count: int = 0
    rows_loaded_after_2024_filter: int = 0
    source_bytes_read: int = 0

    def load_frame(self, path: str | Path) -> pd.DataFrame:
        cache_key = normalized_market_data_source_key(path)
        frame = self.frame_cache.get(cache_key)
        if frame is None:
            self.frame_cache_miss_count += 1
            source_path = Path(path).expanduser()
            if source_path.exists() and source_path.is_file():
                self.source_bytes_read += int(source_path.stat().st_size)
            frame = load_market_frame(path)
            self.frame_cache[cache_key] = frame
            self.rows_loaded_after_2024_filter += int(len(frame))
        else:
            self.frame_cache_hit_count += 1
        return frame

    def descriptor_source_integrity_errors(
        self,
        descriptor: VenueArchiveDescriptor,
        *,
        data_path: str | Path | None = None,
    ) -> list[str]:
        source_path = Path(data_path) if data_path is not None else descriptor.data_path
        if descriptor.source_integrity and source_path is not None:
            path = Path(source_path)
            if path.exists() and path.is_file():
                cache_key = _normalized_load_path(path)
                if cache_key in self.integrity_cache:
                    self.integrity_cache_hit_count += 1
                else:
                    self.integrity_cache_miss_count += 1
        return descriptor_source_integrity_errors_with_cache(
            descriptor,
            data_path=data_path,
            integrity_cache=self.integrity_cache,
        )

    def require_descriptor_source_integrity(
        self,
        descriptor: VenueArchiveDescriptor,
        *,
        data_path: str | Path | None = None,
    ) -> None:
        reasons = self.descriptor_source_integrity_errors(descriptor, data_path=data_path)
        if reasons:
            joined = ", ".join(reasons)
            raise ValueError(f"venue descriptor source integrity mismatch for {descriptor.descriptor_id}: {joined}")

    def stats(self) -> dict[str, Any]:
        frame_request_count = self.frame_cache_hit_count + self.frame_cache_miss_count
        integrity_request_count = self.integrity_cache_hit_count + self.integrity_cache_miss_count
        return {
            "frame_cache_hit_count": self.frame_cache_hit_count,
            "frame_cache_miss_count": self.frame_cache_miss_count,
            "frame_cache_request_count": frame_request_count,
            "frame_cache_entry_count": len(self.frame_cache),
            "frame_cache_hit_rate": (
                self.frame_cache_hit_count / frame_request_count if frame_request_count else None
            ),
            "integrity_cache_hit_count": self.integrity_cache_hit_count,
            "integrity_cache_miss_count": self.integrity_cache_miss_count,
            "integrity_cache_request_count": integrity_request_count,
            "integrity_cache_entry_count": len(self.integrity_cache),
            "integrity_cache_hit_rate": (
                self.integrity_cache_hit_count / integrity_request_count if integrity_request_count else None
            ),
            "rows_loaded_after_2024_filter": self.rows_loaded_after_2024_filter,
            "source_bytes_read": self.source_bytes_read,
            "cached_frame_rows": {
                cache_key: int(len(frame))
                for cache_key, frame in sorted(self.frame_cache.items())
            },
        }


def _cached_file_integrity(path: Path, cache: dict[str, dict[str, Any]]) -> dict[str, Any]:
    cache_key = _normalized_load_path(path)
    actual = cache.get(cache_key)
    if actual is None:
        actual = _file_integrity(path)
        cache[cache_key] = actual
    return actual


def _descriptor_source_integrity_errors(
    descriptor: VenueArchiveDescriptor,
    *,
    source_path: str | Path | None = None,
    actual_integrity: dict[str, Any] | None = None,
) -> list[str]:
    expected = dict(descriptor.source_integrity or {})
    if not expected:
        return []
    if source_path is None:
        return ["source_integrity_data_path_missing"]
    source_path = Path(source_path)
    if not source_path.exists() or not source_path.is_file():
        return ["source_integrity_file_missing"]

    reasons: list[str] = []
    expected_sha256 = expected.get("sha256")
    expected_byte_size = expected.get("byte_size")
    if expected_sha256 is None or expected_sha256 == "":
        reasons.append("source_integrity_expected_sha256_missing")
    if expected_byte_size is None or expected_byte_size == "":
        reasons.append("source_integrity_expected_byte_size_missing")

    actual = actual_integrity if actual_integrity is not None else _file_integrity(source_path)
    if expected_sha256 is not None and str(expected_sha256) != str(actual["sha256"]):
        reasons.append("source_integrity_sha256_mismatch")
    if expected_byte_size is not None and expected_byte_size != "":
        try:
            expected_byte_size_int = int(expected_byte_size)
        except (TypeError, ValueError):
            reasons.append("source_integrity_expected_byte_size_invalid")
        else:
            if expected_byte_size_int != int(actual["byte_size"]):
                reasons.append("source_integrity_byte_size_mismatch")
    return sorted(set(reasons))


def descriptor_source_integrity_errors(
    descriptor: VenueArchiveDescriptor,
    *,
    data_path: str | Path | None = None,
) -> list[str]:
    source_path = Path(data_path) if data_path is not None else descriptor.data_path
    return _descriptor_source_integrity_errors(descriptor, source_path=source_path)


def descriptor_source_integrity_errors_with_cache(
    descriptor: VenueArchiveDescriptor,
    *,
    data_path: str | Path | None = None,
    integrity_cache: dict[str, dict[str, Any]],
) -> list[str]:
    if not descriptor.source_integrity:
        return []
    source_path = Path(data_path) if data_path is not None else descriptor.data_path
    if source_path is None:
        return _descriptor_source_integrity_errors(descriptor, source_path=source_path)
    path = Path(source_path)
    if not path.exists() or not path.is_file():
        return _descriptor_source_integrity_errors(descriptor, source_path=path)
    actual = _cached_file_integrity(path, integrity_cache)
    return _descriptor_source_integrity_errors(
        descriptor,
        source_path=path,
        actual_integrity=actual,
    )


def require_descriptor_source_integrity(
    descriptor: VenueArchiveDescriptor,
    *,
    data_path: str | Path | None = None,
) -> None:
    reasons = descriptor_source_integrity_errors(descriptor, data_path=data_path)
    if reasons:
        joined = ", ".join(reasons)
        raise ValueError(f"venue descriptor source integrity mismatch for {descriptor.descriptor_id}: {joined}")


def _require_descriptor_source_integrity_with_cache(
    descriptor: VenueArchiveDescriptor,
    *,
    data_path: str | Path | None,
    integrity_cache: dict[str, dict[str, Any]],
) -> None:
    if not descriptor.source_integrity:
        return
    reasons = descriptor_source_integrity_errors_with_cache(
        descriptor,
        data_path=data_path,
        integrity_cache=integrity_cache,
    )
    if reasons:
        joined = ", ".join(reasons)
        raise ValueError(f"venue descriptor source integrity mismatch for {descriptor.descriptor_id}: {joined}")


def load_market_frame_for_descriptor(
    descriptor: VenueArchiveDescriptor,
    *,
    fallback_path: str | Path | None = None,
) -> pd.DataFrame:
    data_path = descriptor.data_path or (Path(fallback_path) if fallback_path is not None else None)
    if data_path is None:
        raise ValueError("venue descriptor requires data_path or CLI market_data path for sandbox execution")
    if descriptor.data_path is not None:
        require_descriptor_source_integrity(descriptor, data_path=data_path)
    return load_market_frame(data_path)


def load_market_frames_for_descriptors(
    descriptors: list[VenueArchiveDescriptor],
    *,
    shared_market_data_path: str | Path | None = None,
    market_data_cache: SandboxMarketDataCache | None = None,
) -> dict[str, pd.DataFrame]:
    if not descriptors:
        raise ValueError("at least one venue descriptor is required")
    cache = market_data_cache or SandboxMarketDataCache()
    if shared_market_data_path is not None:
        shared_frame = cache.load_frame(shared_market_data_path)
        return {descriptor.descriptor_id: shared_frame for descriptor in descriptors}
    frames: dict[str, pd.DataFrame] = {}
    missing = [descriptor.descriptor_id for descriptor in descriptors if descriptor.data_path is None]
    if missing:
        joined = ", ".join(sorted(missing))
        raise ValueError(f"venue descriptors require data_path when no shared market_data is supplied: {joined}")
    for descriptor in descriptors:
        cache.require_descriptor_source_integrity(descriptor, data_path=descriptor.data_path)
    for descriptor in descriptors:
        data_path = descriptor.data_path
        if data_path is None:
            raise ValueError("venue descriptor requires data_path or CLI market_data path for sandbox execution")
        frames[descriptor.descriptor_id] = cache.load_frame(data_path)
    return frames
