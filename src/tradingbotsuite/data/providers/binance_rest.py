from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from tradingbotsuite.adapters.binance import INTERVAL_TO_MS
from tradingbotsuite.core.models import Bar
from tradingbotsuite.data.contracts import DATA_SCHEMA_VERSION, build_data_manifest, validate_data_manifest
from tradingbotsuite.data.quality import build_data_quality_report
from tradingbotsuite.data.storage.parquet_store import PartitionedParquetStore


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


@dataclass(frozen=True, slots=True)
class BinanceKlineIntakeResult:
    data_path: Path
    manifest_path: Path
    data_quality_report_path: Path
    row_count: int


async def collect_binance_kline_intake(
    *,
    symbol: str,
    interval: str,
    start_time_ms: int,
    end_time_ms: int,
    output_dir: Path,
    client: BinanceHistoricalBarClient,
) -> BinanceKlineIntakeResult:
    normalized_symbol = symbol.strip().upper()
    normalized_interval = interval.strip()
    if normalized_interval not in INTERVAL_TO_MS:
        raise ValueError(f"interval must be one of: {', '.join(sorted(INTERVAL_TO_MS))}")

    bars = await client.fetch_historical_closed_bar_range(
        normalized_symbol,
        start_time_ms=int(start_time_ms),
        end_time_ms=int(end_time_ms),
        interval=normalized_interval,
    )
    records = [
        {
            "event_time_ms": int(bar.time_ms),
            "symbol": normalized_symbol,
            "interval": normalized_interval,
            "open_price": _decimal_text(bar.open),
            "high_price": _decimal_text(bar.high),
            "low_price": _decimal_text(bar.low),
            "close_price": _decimal_text(bar.close),
            "volume": _decimal_text(bar.volume),
        }
        for bar in sorted(bars, key=lambda item: int(item.time_ms))
    ]
    if not records:
        raise ValueError("at least one bar is required for normalized intake")

    store = PartitionedParquetStore(output_dir)
    write_result = store.write_records(
        source_name="binance_rest",
        data_family="kline",
        symbol=normalized_symbol,
        records=records,
        event_time_field="event_time_ms",
    )
    spacing = _spacing_report([int(record["event_time_ms"]) for record in records], interval_ms=INTERVAL_TO_MS[normalized_interval])
    manifest = build_data_manifest(
        source_name="binance_rest",
        source_type="rest",
        symbol=normalized_symbol,
        data_family="kline",
        event_time_field="event_time_ms",
        receive_time_field=None,
        receive_time_unavailable_reason="historical REST backfill does not preserve original live receive timestamp",
        start_time_ms=min(int(record["event_time_ms"]) for record in records),
        end_time_ms=max(int(record["event_time_ms"]) for record in records) + 1,
        row_count=len(records),
        content_hash=write_result.content_hash,
        normalized_fields=tuple(records[0].keys()),
        missing_fields=("receive_time_ms",),
        quality_flags=("historical_rest_backfill", *spacing["quality_flags"]),
        non_promotable_reasons=("receive_time_unavailable",),
        schema_version=DATA_SCHEMA_VERSION,
        data_path=str(write_result.data_path),
        extra={
            "interval": normalized_interval,
            "gap_count": spacing["gap_count"],
            "duplicate_count": spacing["duplicate_count"],
            "storage_layout": write_result.storage_layout,
        },
    )
    validation = validate_data_manifest(manifest)
    if not validation.valid:
        raise ValueError("; ".join(validation.errors))

    manifest_path = write_result.data_path.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    quality = build_data_quality_report(manifest)
    data_quality_report_path = write_result.data_path.with_name("data_quality_report.json")
    data_quality_report_path.write_text(json.dumps(quality, indent=2, sort_keys=True), encoding="utf-8")

    return BinanceKlineIntakeResult(
        data_path=write_result.data_path,
        manifest_path=manifest_path,
        data_quality_report_path=data_quality_report_path,
        row_count=len(records),
    )


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


def _spacing_report(times: list[int], *, interval_ms: int) -> dict[str, object]:
    seen: set[int] = set()
    duplicates = 0
    for time_ms in times:
        if time_ms in seen:
            duplicates += 1
        seen.add(time_ms)
    unique_times = sorted(seen)
    gaps = 0
    for previous, current in zip(unique_times, unique_times[1:]):
        if current - previous != interval_ms:
            gaps += 1
    flags: list[str] = []
    if gaps:
        flags.append("gaps_detected")
    if duplicates:
        flags.append("duplicates_detected")
    return {"gap_count": gaps, "duplicate_count": duplicates, "quality_flags": flags}
