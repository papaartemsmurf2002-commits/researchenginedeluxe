from __future__ import annotations

import csv
import hashlib
import json
import re
import time
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from tradingbotsuite.config import AppConfig
from tradingbotsuite.core.models import SignalDirection, SignalIntent
from tradingbotsuite.persistence.sqlite_store import SQLiteStore

TRADINGVIEW_CHART_EXPORT_SOURCE = "tradingview_chart_export"
TRADINGVIEW_CHART_EXPORT_SOURCE_MODE = "chart_export"
ENTRY_PRICE_SOURCE_NEXT_OPEN_SLIPPAGE = "next_bar_open_plus_configured_slippage"
SUPPORTED_TIMEFRAME = "15m"
STRATEGY_VERSION_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


@dataclass(frozen=True, slots=True)
class TradingViewChartImportResult:
    batch_id: str
    manifest_path: Path
    imported_count: int
    skipped_count: int
    duplicate_count: int
    candidate_count: int
    buy_count: int
    sell_count: int


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")


def _normalize_timestamp_ms(value: str) -> int:
    timestamp = int(Decimal(str(value)))
    return timestamp if timestamp > 10_000_000_000 else timestamp * 1000


def _column_index(header: list[str], name: str) -> int:
    try:
        return header.index(name)
    except ValueError as exc:
        raise ValueError(f"TradingView chart export is missing required column {name!r}") from exc


def _row_value(row: list[str], index: int) -> str:
    return row[index].strip() if index < len(row) else ""


def _slippage_adjusted_entry(next_open: Decimal, direction: SignalDirection, slippage_bps: Decimal) -> Decimal:
    multiplier = Decimal("1") + (slippage_bps / Decimal("10000"))
    if direction == SignalDirection.SHORT:
        multiplier = Decimal("1") - (slippage_bps / Decimal("10000"))
    return next_open * multiplier


def _source_raw_columns(header: list[str], row: list[str]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    duplicate_counts: Counter[str] = Counter()
    for index, name in enumerate(header):
        value = _row_value(row, index)
        if name in values:
            duplicate_counts[name] += 1
            values[f"{name}#{duplicate_counts[name] + 1}"] = value
        else:
            duplicate_counts[name] += 1
            values[name] = value
    return values


async def import_tradingview_chart_export(
    config: AppConfig,
    *,
    path: Path,
    symbol: str,
    strategy_version: str,
    timeframe: str = SUPPORTED_TIMEFRAME,
    mode: str = "replace-batch",
    notes: str | None = None,
    manifest_dir: Path = Path("data/imports"),
) -> TradingViewChartImportResult:
    symbol = symbol.upper().strip()
    if symbol != "BTCUSDT":
        raise ValueError("TradingView chart-export import is BTC-only in this phase")
    if timeframe != SUPPORTED_TIMEFRAME:
        raise ValueError(f"unsupported TradingView export timeframe {timeframe!r}; expected {SUPPORTED_TIMEFRAME!r}")
    if mode not in {"replace-batch", "append-only"}:
        raise ValueError("import mode must be replace-batch or append-only")
    if not strategy_version or not STRATEGY_VERSION_RE.fullmatch(strategy_version):
        raise ValueError("strategy_version must contain only letters, numbers, underscore, dash, or dot")

    source_path = path.expanduser().resolve()
    if not source_path.exists() or not source_path.is_file():
        raise FileNotFoundError(source_path)

    source_hash = _hash_file(source_path)
    file_hash_prefix = source_hash[:12]
    batch_id = f"tv-chart:{symbol}:{strategy_version}:{file_hash_prefix}"
    import_time_ms = int(time.time() * 1000)

    with source_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        if not header:
            raise ValueError("TradingView chart export is empty")
        rows = list(reader)

    time_idx = _column_index(header, "time")
    open_idx = _column_index(header, "open")
    high_idx = _column_index(header, "high")
    low_idx = _column_index(header, "low")
    close_idx = _column_index(header, "close")
    buy_idx = _column_index(header, "Buy")
    sell_idx = _column_index(header, "Sell")

    signals: list[SignalIntent] = []
    skip_reasons: Counter[str] = Counter()
    buy_count = 0
    sell_count = 0
    for row_index, row in enumerate(rows):
        source_row_number = row_index + 2
        buy_marker = _row_value(row, buy_idx)
        sell_marker = _row_value(row, sell_idx)
        if not buy_marker and not sell_marker:
            continue
        if buy_marker and sell_marker:
            skip_reasons["ambiguous_buy_and_sell"] += 1
            continue
        if row_index + 1 >= len(rows):
            skip_reasons["missing_next_bar"] += 1
            continue

        try:
            tv_bar_time_ms = _normalize_timestamp_ms(_row_value(row, time_idx))
            next_row = rows[row_index + 1]
            next_bar_time_ms = _normalize_timestamp_ms(_row_value(next_row, time_idx))
            marker_price = Decimal(buy_marker or sell_marker)
            next_open = Decimal(_row_value(next_row, open_idx))
            direction = SignalDirection.LONG if buy_marker else SignalDirection.SHORT
            normalized_entry_price = _slippage_adjusted_entry(
                next_open,
                direction,
                config.strategy.entry_slippage_bps,
            )
        except Exception:
            skip_reasons["malformed_signal_row"] += 1
            continue

        if direction == SignalDirection.LONG:
            buy_count += 1
        else:
            sell_count += 1
        signal_id = f"{batch_id}:{tv_bar_time_ms}:{direction}"
        raw_payload = {
            "source_mode": TRADINGVIEW_CHART_EXPORT_SOURCE_MODE,
            "source": TRADINGVIEW_CHART_EXPORT_SOURCE,
            "source_file_name": source_path.name,
            "source_path": str(source_path),
            "source_sha256": source_hash,
            "source_row_number": source_row_number,
            "source_header": header,
            "source_raw_columns": _source_raw_columns(header, row),
            "symbol": symbol,
            "strategy_version": strategy_version,
            "import_batch_id": batch_id,
            "import_time_ms": import_time_ms,
            "timeframe": timeframe,
            "signal_marker_price": str(marker_price),
            "signal_open": _row_value(row, open_idx),
            "signal_high": _row_value(row, high_idx),
            "signal_low": _row_value(row, low_idx),
            "signal_close": _row_value(row, close_idx),
            "next_bar_time_ms": next_bar_time_ms,
            "next_bar_open": str(next_open),
            "normalized_entry_price": str(normalized_entry_price),
            "entry_price_source": ENTRY_PRICE_SOURCE_NEXT_OPEN_SLIPPAGE,
            "entry_slippage_bps": str(config.strategy.entry_slippage_bps),
            "ignored_columns": ["StopBuy", "StopSell", "Shapes", "Chars"],
        }
        signals.append(
            SignalIntent(
                signal_id=signal_id,
                source=TRADINGVIEW_CHART_EXPORT_SOURCE,
                symbol=symbol,
                direction=direction,
                tv_bar_time_ms=tv_bar_time_ms,
                received_time_ms=import_time_ms,
                raw_payload=raw_payload,
            )
        )

    first_signal_time_ms = min((signal.tv_bar_time_ms for signal in signals), default=None)
    last_signal_time_ms = max((signal.tv_bar_time_ms for signal in signals), default=None)
    skipped_count = sum(skip_reasons.values())
    batch = {
        "batch_id": batch_id,
        "source": TRADINGVIEW_CHART_EXPORT_SOURCE,
        "source_mode": TRADINGVIEW_CHART_EXPORT_SOURCE_MODE,
        "symbol": symbol,
        "strategy_version": strategy_version,
        "timeframe": timeframe,
        "source_path": str(source_path),
        "source_sha256": source_hash,
        "source_file_name": source_path.name,
        "source_header": header,
        "import_mode": mode,
        "candidate_count": len(signals),
        "buy_count": buy_count,
        "sell_count": sell_count,
        "skipped_count": skipped_count,
        "skip_reasons": dict(sorted(skip_reasons.items())),
        "first_signal_time_ms": first_signal_time_ms,
        "last_signal_time_ms": last_signal_time_ms,
        "import_time_ms": import_time_ms,
        "notes": notes,
        "entry_price_source": ENTRY_PRICE_SOURCE_NEXT_OPEN_SLIPPAGE,
        "entry_slippage_bps": str(config.strategy.entry_slippage_bps),
    }

    store = SQLiteStore(config.db_path)
    await store.initialize()
    save_counts = await store.save_signal_import_batch(batch=batch, signals=signals, mode=mode)
    manifest = {
        **batch,
        **save_counts,
    }
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"tv-chart_{symbol}_{_safe_filename(strategy_version)}_{file_hash_prefix}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return TradingViewChartImportResult(
        batch_id=batch_id,
        manifest_path=manifest_path,
        imported_count=save_counts["imported_count"],
        skipped_count=skipped_count,
        duplicate_count=save_counts["duplicate_count"],
        candidate_count=len(signals),
        buy_count=buy_count,
        sell_count=sell_count,
    )
