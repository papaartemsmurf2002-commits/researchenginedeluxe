# V2-AUDIT-ID: V2-AUD-ARCH-004
# V2-CONTRACTS: docs/contracts/archive_contract.md, docs/contracts/data_quality_contract.md
# V2-BOUNDARY: research_only, bronze_silver_rebuild, no_live_imports
# V2-OWNER: v2_archive
"""Bronze and silver market-data rebuild helpers."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from tradingbotsuite.v2.archive.hashing import canonical_json_hash
from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.archive.manifest_store import ArchiveManifestStore
from tradingbotsuite.v2.archive.market_data import (
    BronzeAssetContextRow,
    BronzeCandleRow,
    BronzeFundingRow,
    NormalizationManifestRow,
    SilverAssetContextRow,
    SilverBarRow,
    SilverFundingIntervalRow,
)
from tradingbotsuite.v2.archive.normalization_store import NormalizationManifestStore
from tradingbotsuite.v2.archive.parquet_writer import write_parquet_rows
from tradingbotsuite.v2.archive.raw_writer import read_jsonl_zstd
from tradingbotsuite.v2.archive.schemas import ArchiveLayer, ArchiveSnapshotRecord, FileManifestRow
from tradingbotsuite.v2.archive.snapshots import create_archive_snapshot
from tradingbotsuite.v2.config.time import ensure_utc, utc_isoformat
from tradingbotsuite.v2.data_quality.coverage import coverage_report_for_bars, timeframe_to_timedelta
from tradingbotsuite.v2.data_quality.reports import CoverageManifestStore


DERIVED_BAR_TIMEFRAMES = ("5m", "15m", "1h")


@dataclass(frozen=True)
class RebuildResult:
    output_files: tuple[FileManifestRow, ...]
    normalization_manifests: tuple[NormalizationManifestRow, ...]
    coverage_report_ids: tuple[str, ...] = ()
    archive_snapshot_id: str | None = None


def raw_candles_to_bronze(
    *,
    archive_root: str | Path,
    raw_file_id: str,
    job_id: str,
    instrument_id: str | None = None,
    timeframe: str | None = None,
) -> RebuildResult:
    layout, store, raw_row, raw_records = _load_raw_records(archive_root, raw_file_id)
    rows, warnings = _parse_candle_rows(
        raw_records,
        raw_row=raw_row,
        instrument_id=instrument_id,
        timeframe=timeframe,
    )
    output = write_parquet_rows(
        layout=layout,
        store=store,
        rows=[row.model_dump(mode="json") for row in rows],
        layer=ArchiveLayer.BRONZE,
        dataset="candles",
        venue=raw_row.venue,
        datatype="candles",
        date=_date_for_rows(rows, fallback=raw_row.date),
        timeframe=rows[0].timeframe if rows else timeframe,
        job_id=job_id,
        source_file_ids=(raw_row.file_id,),
        instrument_id=rows[0].instrument_id if rows else instrument_id,
    )
    manifest = _normalization_manifest(
        source_file_id=raw_row.file_id,
        output_file_id=output.file_id,
        source_layer=ArchiveLayer.RAW,
        output_layer=ArchiveLayer.BRONZE,
        dataset="candles",
        venue=raw_row.venue,
        instrument_id=output.instrument_id,
        timeframe=output.timeframe,
        row_count_in=len(raw_records),
        row_count_out=len(rows),
        gap_reasons=tuple(warnings),
        decisions=("raw_candles_parsed_to_bronze",),
    )
    NormalizationManifestStore(layout).append(manifest)
    return RebuildResult(output_files=(output,), normalization_manifests=(manifest,))


def raw_funding_to_bronze(
    *,
    archive_root: str | Path,
    raw_file_id: str,
    job_id: str,
    instrument_id: str | None = None,
) -> RebuildResult:
    layout, store, raw_row, raw_records = _load_raw_records(archive_root, raw_file_id)
    rows, warnings = _parse_funding_rows(raw_records, raw_row=raw_row, instrument_id=instrument_id)
    output = write_parquet_rows(
        layout=layout,
        store=store,
        rows=[row.model_dump(mode="json") for row in rows],
        layer=ArchiveLayer.BRONZE,
        dataset="funding",
        venue=raw_row.venue,
        datatype="funding",
        date=_date_for_rows(rows, fallback=raw_row.date),
        job_id=job_id,
        source_file_ids=(raw_row.file_id,),
        instrument_id=rows[0].instrument_id if rows else instrument_id,
    )
    manifest = _normalization_manifest(
        source_file_id=raw_row.file_id,
        output_file_id=output.file_id,
        source_layer=ArchiveLayer.RAW,
        output_layer=ArchiveLayer.BRONZE,
        dataset="funding",
        venue=raw_row.venue,
        instrument_id=output.instrument_id,
        timeframe=None,
        row_count_in=len(raw_records),
        row_count_out=len(rows),
        gap_reasons=tuple(warnings),
        decisions=("raw_funding_parsed_to_bronze",),
    )
    NormalizationManifestStore(layout).append(manifest)
    return RebuildResult(output_files=(output,), normalization_manifests=(manifest,))


def raw_asset_contexts_to_bronze(
    *,
    archive_root: str | Path,
    raw_file_id: str,
    job_id: str,
    instrument_id: str | None = None,
) -> RebuildResult:
    layout, store, raw_row, raw_records = _load_raw_records(archive_root, raw_file_id)
    rows, warnings = _parse_context_rows(raw_records, raw_row=raw_row, instrument_id=instrument_id)
    output = write_parquet_rows(
        layout=layout,
        store=store,
        rows=[row.model_dump(mode="json") for row in rows],
        layer=ArchiveLayer.BRONZE,
        dataset="asset_contexts",
        venue=raw_row.venue,
        datatype="asset_contexts",
        date=_date_for_rows(rows, fallback=raw_row.date),
        job_id=job_id,
        source_file_ids=(raw_row.file_id,),
        instrument_id=rows[0].instrument_id if len({row.instrument_id for row in rows}) == 1 else instrument_id,
    )
    manifest = _normalization_manifest(
        source_file_id=raw_row.file_id,
        output_file_id=output.file_id,
        source_layer=ArchiveLayer.RAW,
        output_layer=ArchiveLayer.BRONZE,
        dataset="asset_contexts",
        venue=raw_row.venue,
        instrument_id=output.instrument_id,
        timeframe=None,
        row_count_in=len(raw_records),
        row_count_out=len(rows),
        gap_reasons=tuple(warnings),
        decisions=("raw_asset_contexts_parsed_to_bronze",),
    )
    NormalizationManifestStore(layout).append(manifest)
    return RebuildResult(output_files=(output,), normalization_manifests=(manifest,))


def bronze_candles_to_silver_bars(
    *,
    archive_root: str | Path,
    bronze_file_id: str,
    job_id: str,
    derive_timeframes: Iterable[str] = DERIVED_BAR_TIMEFRAMES,
    write_coverage: bool = True,
    create_snapshot: bool = False,
) -> RebuildResult:
    layout, store, bronze_file, rows = _load_table_records(archive_root, bronze_file_id)
    candles = sorted((BronzeCandleRow.model_validate(row) for row in rows), key=lambda row: row.ts)
    if not candles:
        raise ValueError("bronze candle file contains no rows")
    output_files: list[FileManifestRow] = []
    manifests: list[NormalizationManifestRow] = []
    coverage_ids: list[str] = []
    one_minute = [_silver_bar_from_candle(row, source_file_id=bronze_file.file_id) for row in candles]
    output_files.append(
        _write_silver_bars(
            layout=layout,
            store=store,
            bars=one_minute,
            source_file=bronze_file,
            job_id=job_id,
        )
    )
    manifests.append(
        _normalization_manifest(
            source_file_id=bronze_file.file_id,
            output_file_id=output_files[-1].file_id,
            source_layer=ArchiveLayer.BRONZE,
            output_layer=ArchiveLayer.SILVER,
            dataset="bars",
            venue=bronze_file.venue,
            instrument_id=one_minute[0].instrument_id,
            timeframe=one_minute[0].timeframe,
            row_count_in=len(candles),
            row_count_out=len(one_minute),
            gap_reasons=(),
            decisions=("bronze_candles_normalized_to_silver_1m_bars",),
        )
    )
    for timeframe in derive_timeframes:
        derived, gap_reasons = _derive_bars(one_minute, timeframe=timeframe)
        if not derived:
            manifests.append(
                _normalization_manifest(
                    source_file_id=bronze_file.file_id,
                    output_file_id=None,
                    source_layer=ArchiveLayer.BRONZE,
                    output_layer=ArchiveLayer.SILVER,
                    dataset="bars",
                    venue=bronze_file.venue,
                    instrument_id=one_minute[0].instrument_id,
                    timeframe=timeframe,
                    row_count_in=len(one_minute),
                    row_count_out=0,
                    gap_reasons=tuple(gap_reasons),
                    decisions=("derived_timeframe_not_written_no_complete_windows",),
                    status="skipped",
                )
            )
            continue
        output_files.append(
            _write_silver_bars(
                layout=layout,
                store=store,
                bars=derived,
                source_file=bronze_file,
                job_id=job_id,
            )
        )
        manifests.append(
            _normalization_manifest(
                source_file_id=bronze_file.file_id,
                output_file_id=output_files[-1].file_id,
                source_layer=ArchiveLayer.BRONZE,
                output_layer=ArchiveLayer.SILVER,
                dataset="bars",
                venue=bronze_file.venue,
                instrument_id=derived[0].instrument_id,
                timeframe=timeframe,
                row_count_in=len(one_minute),
                row_count_out=len(derived),
                gap_reasons=tuple(gap_reasons),
                decisions=(f"derived_{timeframe}_bars_from_1m",),
            )
        )
    norm_store = NormalizationManifestStore(layout)
    norm_store.extend(manifests)
    if write_coverage:
        coverage_ids = _write_bar_coverage_reports(archive_root, output_files)
    snapshot_id: str | None = None
    if create_snapshot:
        snapshot = create_silver_market_data_snapshot(
            archive_root=archive_root,
            venue_scope=bronze_file.venue,
            start_ts=min(bar.ts for bar in one_minute),
            end_ts=max(bar.end_ts for bar in one_minute),
            notes="phase8_silver_bar_build",
        )
        snapshot_id = snapshot.archive_snapshot_id
    return RebuildResult(
        output_files=tuple(output_files),
        normalization_manifests=tuple(manifests),
        coverage_report_ids=tuple(coverage_ids),
        archive_snapshot_id=snapshot_id,
    )


def bronze_funding_to_silver(
    *,
    archive_root: str | Path,
    bronze_file_id: str,
    job_id: str,
) -> RebuildResult:
    layout, store, bronze_file, rows = _load_table_records(archive_root, bronze_file_id)
    bronze_rows = sorted((BronzeFundingRow.model_validate(row) for row in rows), key=lambda row: row.ts)
    silver_rows = [
        SilverFundingIntervalRow(
            venue=row.venue,
            instrument_id=row.instrument_id,
            interval_start_ts=row.ts,
            interval_end_ts=row.end_ts,
            funding_rate=row.funding_rate,
            source_file_id=bronze_file.file_id,
        )
        for row in bronze_rows
    ]
    output = write_parquet_rows(
        layout=layout,
        store=store,
        rows=[row.model_dump(mode="json") for row in silver_rows],
        layer=ArchiveLayer.SILVER,
        dataset="funding",
        venue=bronze_file.venue,
        datatype="funding",
        date=_date_for_rows(silver_rows, fallback=bronze_file.date),
        job_id=job_id,
        source_file_ids=(bronze_file.file_id,),
        instrument_id=bronze_file.instrument_id,
    )
    manifest = _normalization_manifest(
        source_file_id=bronze_file.file_id,
        output_file_id=output.file_id,
        source_layer=ArchiveLayer.BRONZE,
        output_layer=ArchiveLayer.SILVER,
        dataset="funding",
        venue=bronze_file.venue,
        instrument_id=bronze_file.instrument_id,
        timeframe=None,
        row_count_in=len(bronze_rows),
        row_count_out=len(silver_rows),
        gap_reasons=(),
        decisions=("bronze_funding_normalized_to_utc_intervals",),
    )
    NormalizationManifestStore(layout).append(manifest)
    return RebuildResult(output_files=(output,), normalization_manifests=(manifest,))


def bronze_asset_contexts_to_silver(
    *,
    archive_root: str | Path,
    bronze_file_id: str,
    job_id: str,
) -> RebuildResult:
    layout, store, bronze_file, rows = _load_table_records(archive_root, bronze_file_id)
    bronze_rows = sorted((BronzeAssetContextRow.model_validate(row) for row in rows), key=lambda row: row.ts)
    silver_rows: list[SilverAssetContextRow] = []
    gap_reasons: list[str] = []
    for row in bronze_rows:
        missing = tuple(
            field
            for field in ("mark_price", "oracle_price", "open_interest", "day_notional_volume_usd")
            if getattr(row, field) is None
        )
        if missing:
            gap_reasons.append(f"{row.instrument_id}:{row.ts.isoformat()}:missing_{'_'.join(missing)}")
        silver_rows.append(
            SilverAssetContextRow(
                venue=row.venue,
                instrument_id=row.instrument_id,
                ts=row.ts,
                mark_price=row.mark_price,
                oracle_price=row.oracle_price,
                open_interest=row.open_interest,
                day_notional_volume_usd=row.day_notional_volume_usd,
                funding_rate=row.funding_rate,
                source_file_id=bronze_file.file_id,
                missing_fields=missing,
            )
        )
    output = write_parquet_rows(
        layout=layout,
        store=store,
        rows=[row.model_dump(mode="json") for row in silver_rows],
        layer=ArchiveLayer.SILVER,
        dataset="asset_contexts",
        venue=bronze_file.venue,
        datatype="asset_contexts",
        date=_date_for_rows(silver_rows, fallback=bronze_file.date),
        job_id=job_id,
        source_file_ids=(bronze_file.file_id,),
        instrument_id=bronze_file.instrument_id,
    )
    manifest = _normalization_manifest(
        source_file_id=bronze_file.file_id,
        output_file_id=output.file_id,
        source_layer=ArchiveLayer.BRONZE,
        output_layer=ArchiveLayer.SILVER,
        dataset="asset_contexts",
        venue=bronze_file.venue,
        instrument_id=bronze_file.instrument_id,
        timeframe=None,
        row_count_in=len(bronze_rows),
        row_count_out=len(silver_rows),
        gap_reasons=tuple(gap_reasons[:50]),
        decisions=("bronze_context_normalized_mark_oracle_open_interest",),
    )
    NormalizationManifestStore(layout).append(manifest)
    return RebuildResult(output_files=(output,), normalization_manifests=(manifest,))


def create_silver_market_data_snapshot(
    *,
    archive_root: str | Path,
    venue_scope: str,
    start_ts: datetime,
    end_ts: datetime,
    notes: str | None = None,
) -> ArchiveSnapshotRecord:
    layout = ArchiveLayout(archive_root)
    store = ArchiveManifestStore(layout)
    coverage_store = CoverageManifestStore(layout)
    quality_store = CoverageManifestStore(layout)
    return create_archive_snapshot(
        store=store,
        layer=ArchiveLayer.SILVER,
        venue_scope=venue_scope,
        start_ts=start_ts,
        end_ts=end_ts,
        coverage_rows=[row.model_dump(mode="json") for row in coverage_store.load_coverage_reports()],
        quality_rows=[row.model_dump(mode="json") for row in quality_store.load_quality_checks()],
        notes=notes,
    )


def _load_raw_records(
    archive_root: str | Path,
    raw_file_id: str,
) -> tuple[ArchiveLayout, ArchiveManifestStore, FileManifestRow, list[dict[str, Any]]]:
    layout = ArchiveLayout(archive_root)
    store = ArchiveManifestStore(layout)
    raw_row = _find_file(store, raw_file_id)
    if raw_row.layer != ArchiveLayer.RAW:
        raise ValueError("source file must be raw")
    if raw_row.uncompressed_size_bytes is None:
        raise ValueError("raw manifest row must include uncompressed_size_bytes")
    raw_records = read_jsonl_zstd(
        layout.resolve(raw_row.path),
        uncompressed_size=raw_row.uncompressed_size_bytes,
    )
    return layout, store, raw_row, raw_records


def _load_table_records(
    archive_root: str | Path,
    file_id: str,
) -> tuple[ArchiveLayout, ArchiveManifestStore, FileManifestRow, list[dict[str, Any]]]:
    layout = ArchiveLayout(archive_root)
    store = ArchiveManifestStore(layout)
    manifest_row = _find_file(store, file_id)
    rows = pq.ParquetFile(layout.resolve(manifest_row.path)).read().to_pylist()
    return layout, store, manifest_row, rows


def _find_file(store: ArchiveManifestStore, file_id: str) -> FileManifestRow:
    matches = [row for row in store.load_file_manifest() if row.file_id == file_id]
    if len(matches) != 1:
        raise KeyError(f"file_manifest row not found: {file_id}")
    return matches[0]


def _parse_candle_rows(
    records: Iterable[Mapping[str, Any]],
    *,
    raw_row: FileManifestRow,
    instrument_id: str | None,
    timeframe: str | None,
) -> tuple[list[BronzeCandleRow], list[str]]:
    rows: list[BronzeCandleRow] = []
    warnings: list[str] = []
    for index, record in enumerate(records):
        payload = _payload(record)
        try:
            row_timeframe = str(_first(payload, "timeframe", "interval", "i") or timeframe or raw_row.timeframe or "1m")
            ts = _timestamp(_first(payload, "ts", "start_ts", "t", "time"))
            end_value = _first(payload, "end_ts", "T", "close_time")
            end_ts = _timestamp(end_value) if end_value is not None else ts + timeframe_to_timedelta(row_timeframe)
            rows.append(
                BronzeCandleRow(
                    venue=raw_row.venue,
                    instrument_id=str(
                        _first(payload, "instrument_id", "symbol", "coin", "s")
                        or instrument_id
                        or raw_row.instrument_id
                        or "unknown"
                    ),
                    timeframe=row_timeframe,
                    ts=ts,
                    end_ts=end_ts,
                    open=_float(_first(payload, "open", "o")),
                    high=_float(_first(payload, "high", "h")),
                    low=_float(_first(payload, "low", "l")),
                    close=_float(_first(payload, "close", "c")),
                    volume=_float(_first(payload, "volume", "v")),
                    trade_count=_optional_int(_first(payload, "trade_count", "n")),
                    raw_file_id=raw_row.file_id,
                    source_sequence=index,
                )
            )
        except (TypeError, ValueError) as exc:
            warnings.append(f"parse_failure:{index}:{exc}")
    if not rows:
        raise ValueError("no valid candle rows parsed")
    return rows, warnings


def _parse_funding_rows(
    records: Iterable[Mapping[str, Any]],
    *,
    raw_row: FileManifestRow,
    instrument_id: str | None,
) -> tuple[list[BronzeFundingRow], list[str]]:
    rows: list[BronzeFundingRow] = []
    warnings: list[str] = []
    for index, record in enumerate(records):
        payload = _payload(record)
        try:
            ts = _timestamp(_first(payload, "ts", "time", "funding_time"))
            end_value = _first(payload, "end_ts", "interval_end_ts")
            end_ts = _timestamp(end_value) if end_value is not None else ts + timedelta(hours=1)
            rows.append(
                BronzeFundingRow(
                    venue=raw_row.venue,
                    instrument_id=str(
                        _first(payload, "instrument_id", "symbol", "coin", "s")
                        or instrument_id
                        or raw_row.instrument_id
                        or "unknown"
                    ),
                    ts=ts,
                    end_ts=end_ts,
                    funding_rate=_float(_first(payload, "funding_rate", "fundingRate", "funding")),
                    raw_file_id=raw_row.file_id,
                    source_sequence=index,
                )
            )
        except (TypeError, ValueError) as exc:
            warnings.append(f"parse_failure:{index}:{exc}")
    if not rows:
        raise ValueError("no valid funding rows parsed")
    return rows, warnings


def _parse_context_rows(
    records: Iterable[Mapping[str, Any]],
    *,
    raw_row: FileManifestRow,
    instrument_id: str | None,
) -> tuple[list[BronzeAssetContextRow], list[str]]:
    flattened = _flatten_context_records(records)
    rows: list[BronzeAssetContextRow] = []
    warnings: list[str] = []
    for index, payload in enumerate(flattened):
        try:
            ts_value = _first(payload, "ts", "time", "snapshot_ts") or raw_row.created_at
            rows.append(
                BronzeAssetContextRow(
                    venue=raw_row.venue,
                    instrument_id=str(
                        _first(payload, "instrument_id", "symbol", "coin", "name", "s")
                        or instrument_id
                        or raw_row.instrument_id
                        or "unknown"
                    ),
                    ts=_timestamp(ts_value),
                    mark_price=_optional_float(_first(payload, "mark_price", "markPx")),
                    oracle_price=_optional_float(_first(payload, "oracle_price", "oraclePx")),
                    open_interest=_optional_float(_first(payload, "open_interest", "openInterest")),
                    day_notional_volume_usd=_optional_float(
                        _first(payload, "day_notional_volume_usd", "dayNtlVlm")
                    ),
                    funding_rate=_optional_float(_first(payload, "funding_rate", "funding")),
                    raw_file_id=raw_row.file_id,
                    source_sequence=index,
                )
            )
        except (TypeError, ValueError) as exc:
            warnings.append(f"parse_failure:{index}:{exc}")
    if not rows:
        raise ValueError("no valid asset context rows parsed")
    return rows, warnings


def _flatten_context_records(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    materialized = [dict(record) for record in records]
    if len(materialized) == 1:
        first = materialized[0]
        if "contexts" in first and isinstance(first["contexts"], list):
            return [dict(item) for item in first["contexts"]]
        if "asset_contexts" in first and isinstance(first["asset_contexts"], list):
            return [dict(item) for item in first["asset_contexts"]]
    if len(materialized) == 2 and "universe" in materialized[0] and isinstance(materialized[1], list):
        universe = materialized[0]["universe"]
        contexts = materialized[1]
        rows: list[dict[str, Any]] = []
        for meta, context in zip(universe, contexts, strict=False):
            row = dict(context)
            row["name"] = meta.get("name")
            rows.append(row)
        return rows
    return materialized


def _silver_bar_from_candle(row: BronzeCandleRow, *, source_file_id: str) -> SilverBarRow:
    return SilverBarRow(
        venue=row.venue,
        instrument_id=row.instrument_id,
        timeframe=row.timeframe,
        ts=row.ts,
        end_ts=row.end_ts,
        open=row.open,
        high=row.high,
        low=row.low,
        close=row.close,
        volume=row.volume,
        trade_count=row.trade_count,
        source_timeframe=row.timeframe,
        source_file_id=source_file_id,
    )


def _derive_bars(rows: list[SilverBarRow], *, timeframe: str) -> tuple[list[SilverBarRow], list[str]]:
    step = timeframe_to_timedelta(timeframe)
    source_step = timeframe_to_timedelta(rows[0].timeframe)
    expected_count = int(step.total_seconds() // source_step.total_seconds())
    if expected_count <= 1:
        return [], [f"derive_timeframe_not_larger_than_source:{timeframe}"]
    by_window: dict[datetime, list[SilverBarRow]] = defaultdict(list)
    for row in rows:
        by_window[_floor_timestamp(row.ts, step)].append(row)
    derived: list[SilverBarRow] = []
    gaps: list[str] = []
    for window_start in sorted(by_window):
        window_rows = sorted(by_window[window_start], key=lambda row: row.ts)
        expected_ts = {window_start + (source_step * index) for index in range(expected_count)}
        observed_ts = {row.ts for row in window_rows}
        if observed_ts != expected_ts:
            gaps.append(
                f"incomplete_{timeframe}_window:{utc_isoformat(window_start)}:"
                f"expected={expected_count}:observed={len(observed_ts & expected_ts)}"
            )
            continue
        derived.append(
            SilverBarRow(
                venue=window_rows[0].venue,
                instrument_id=window_rows[0].instrument_id,
                timeframe=timeframe,
                ts=window_start,
                end_ts=window_start + step,
                open=window_rows[0].open,
                high=max(row.high for row in window_rows),
                low=min(row.low for row in window_rows),
                close=window_rows[-1].close,
                volume=sum(row.volume for row in window_rows),
                trade_count=_sum_optional(row.trade_count for row in window_rows),
                source_timeframe=rows[0].timeframe,
                source_file_id=rows[0].source_file_id,
                normalization_warnings=(),
            )
        )
    return derived, gaps[:100]


def _write_silver_bars(
    *,
    layout: ArchiveLayout,
    store: ArchiveManifestStore,
    bars: list[SilverBarRow],
    source_file: FileManifestRow,
    job_id: str,
) -> FileManifestRow:
    return write_parquet_rows(
        layout=layout,
        store=store,
        rows=[row.model_dump(mode="json") for row in bars],
        layer=ArchiveLayer.SILVER,
        dataset="bars",
        venue=source_file.venue,
        datatype="bars",
        date=_date_for_rows(bars, fallback=source_file.date),
        timeframe=bars[0].timeframe,
        job_id=job_id,
        source_file_ids=(source_file.file_id,),
        instrument_id=bars[0].instrument_id,
    )


def _write_bar_coverage_reports(archive_root: str | Path, silver_files: Iterable[FileManifestRow]) -> list[str]:
    store = CoverageManifestStore(ArchiveLayout(archive_root))
    report_ids: list[str] = []
    for silver_file in silver_files:
        if silver_file.datatype != "bars" or silver_file.timeframe is None:
            continue
        rows = pq.ParquetFile(ArchiveLayout(archive_root).resolve(silver_file.path)).read().to_pylist()
        if not rows:
            continue
        parsed = [SilverBarRow.model_validate(row) for row in rows]
        report = coverage_report_for_bars(
            [row.model_dump(mode="json") for row in parsed],
            venue=silver_file.venue,
            instrument_id=parsed[0].instrument_id,
            timeframe=parsed[0].timeframe,
            start_ts=min(row.ts for row in parsed),
            end_ts=max(row.end_ts for row in parsed),
            family="bars",
        )
        store.append_coverage_report(report)
        report_ids.append(report.coverage_report_id)
    return report_ids


def _normalization_manifest(
    *,
    source_file_id: str,
    output_file_id: str | None,
    source_layer: ArchiveLayer,
    output_layer: ArchiveLayer,
    dataset: str,
    venue: str,
    instrument_id: str | None,
    timeframe: str | None,
    row_count_in: int,
    row_count_out: int,
    gap_reasons: tuple[str, ...],
    decisions: tuple[str, ...],
    status: str = "succeeded",
) -> NormalizationManifestRow:
    dropped_rows = max(row_count_in - row_count_out, 0)
    identity = {
        "source_file_id": source_file_id,
        "output_file_id": output_file_id,
        "source_layer": source_layer.value,
        "output_layer": output_layer.value,
        "dataset": dataset,
        "venue": venue,
        "instrument_id": instrument_id,
        "timeframe": timeframe,
        "row_count_in": row_count_in,
        "row_count_out": row_count_out,
        "gap_reasons": gap_reasons,
        "decisions": decisions,
        "status": status,
    }
    return NormalizationManifestRow(
        normalization_manifest_id=canonical_json_hash(identity),
        source_file_id=source_file_id,
        output_file_id=output_file_id,
        source_layer=source_layer,
        output_layer=output_layer,
        dataset=dataset,
        venue=venue,
        instrument_id=instrument_id,
        timeframe=timeframe,
        row_count_in=row_count_in,
        row_count_out=row_count_out,
        dropped_rows=dropped_rows,
        gap_count=len(gap_reasons),
        gap_reasons=gap_reasons,
        decisions=decisions,
        status=status,
    )


def _payload(record: Mapping[str, Any]) -> Mapping[str, Any]:
    value = record.get("data")
    if isinstance(value, Mapping):
        return value
    return record


def _first(payload: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return None


def _float(value: Any) -> float:
    if value is None:
        raise ValueError("missing numeric value")
    return float(value)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return ensure_utc(value)
    if isinstance(value, int | float):
        numeric = float(value)
        if numeric > 10_000_000_000:
            numeric = numeric / 1000
        return datetime.fromtimestamp(numeric, tz=UTC)
    if isinstance(value, str):
        if value.isdigit():
            return _timestamp(int(value))
        return ensure_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
    raise ValueError(f"unsupported timestamp: {value!r}")


def _floor_timestamp(value: datetime, step: timedelta) -> datetime:
    ts = ensure_utc(value)
    epoch_seconds = int(ts.timestamp())
    step_seconds = int(step.total_seconds())
    return datetime.fromtimestamp(epoch_seconds - (epoch_seconds % step_seconds), tz=UTC)


def _sum_optional(values: Iterable[int | None]) -> int | None:
    materialized = [value for value in values if value is not None]
    if not materialized:
        return None
    return sum(materialized)


def _date_for_rows(rows: Iterable[Any], *, fallback: str | None) -> str:
    materialized = list(rows)
    if materialized:
        ts = getattr(materialized[0], "ts", None) or getattr(materialized[0], "interval_start_ts", None)
        if isinstance(ts, datetime):
            return ts.date().isoformat()
    if fallback:
        return fallback
    return datetime.now(tz=UTC).date().isoformat()
