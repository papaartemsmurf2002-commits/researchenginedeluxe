from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from tradingbotsuite.adapters.binance import INTERVAL_TO_MS, BinanceCandleClient
from tradingbotsuite.core.models import Bar

BINANCE_USDM_FAPI_URL = "https://fapi.binance.com"
COLLECTOR_VERSION = "binance-usdm-chart-bars-v1"
RESEARCH_MARKET_DATA_ROOT = Path("data/research/market_data/binance_usdm")
SUPPORTED_RESEARCH_SYMBOLS = frozenset({"BTCUSDT", "ETHUSDT"})


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


@dataclass(frozen=True, slots=True)
class MarketDataCollectionResult:
    output_dir: Path
    data_path: Path
    manifest_path: Path
    row_count: int
    gap_count: int
    duplicate_count: int


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
