# V2-AUDIT-ID: V2-AUD-BTDATA-001
# V2-CONTRACTS: docs/contracts/backtest_data_service_contract.md, docs/contracts/validation_contract.md
# V2-BOUNDARY: research_only, archive_snapshot_reads, coverage_gate, lockbox_enforced, no_live_imports
# V2-OWNER: v2_backtest_data
"""Local archive-backed v2 backtest data service."""

from __future__ import annotations

import calendar
from collections.abc import Mapping
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel

from tradingbotsuite.v2.archive.hashing import canonical_json_hash
from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.archive.manifest_store import ArchiveManifestStore
from tradingbotsuite.v2.archive.schemas import ArchiveLayer, ArchiveSnapshotRecord, FileManifestRow
from tradingbotsuite.v2.backtest_data.coverage_gate import (
    CoverageGateError,
    require_coverage_for_evidence,
)
from tradingbotsuite.v2.backtest_data.lockbox import (
    LockboxWindow,
    latest_full_calendar_month_lockbox,
    windows_overlap,
)
from tradingbotsuite.v2.backtest_data.schemas import (
    EVIDENCE_MODES,
    BacktestDataManifest,
    BacktestDataRequest,
    BacktestDataSlice,
    BacktestEvidenceMode,
)
from tradingbotsuite.v2.config.time import ensure_utc, utc_isoformat
from tradingbotsuite.v2.data_quality.checks import parse_timestamp
from tradingbotsuite.v2.data_quality.reports import CoverageManifestStore
from tradingbotsuite.v2.data_quality.schemas import CoverageReport
from tradingbotsuite.v2.universe.hyperliquid import load_universe_rows
from tradingbotsuite.v2.universe.models import UniverseMode, UniverseSnapshotRow


class BacktestDataError(ValueError):
    """Raised when a v2 backtest data request cannot be safely satisfied."""


class BacktestDataService:
    """Deterministic panel loader over local silver archive Parquet files."""

    def __init__(self, archive_root: str | Path | None = None) -> None:
        self.archive_root = Path(archive_root) if archive_root is not None else None

    def load_panel(
        self,
        request: BacktestDataRequest | Mapping[str, Any],
        *,
        asof_date: date | None = None,
        write_manifest: bool = True,
    ) -> BacktestDataSlice:
        parsed = (
            request
            if isinstance(request, BacktestDataRequest)
            else BacktestDataRequest.model_validate(request)
        )
        archive_root = self.archive_root or Path(parsed.archive_root)
        if self.archive_root is not None and Path(parsed.archive_root) != self.archive_root:
            parsed = parsed.model_copy(update={"archive_root": str(self.archive_root)})
        layout = ArchiveLayout(archive_root)
        store = ArchiveManifestStore(layout)
        load_start = parsed.warmup_start_ts or parsed.start_ts
        lockbox_window = self._enforce_temporal_policy(parsed, load_start=load_start, asof_date=asof_date)
        snapshot = self._load_archive_snapshot(store, parsed)
        self._enforce_snapshot_window(snapshot, parsed, load_start=load_start)
        universe_row = self._load_universe_row(archive_root, parsed)
        self._enforce_universe(parsed, universe_row)
        coverage_report = self._select_coverage_report(layout, parsed, load_start=load_start)
        if parsed.evidence_mode in EVIDENCE_MODES:
            try:
                require_coverage_for_evidence(
                    coverage_report,
                    coverage_min=parsed.validation_config.coverage_min,
                )
            except CoverageGateError as exc:
                raise BacktestDataError(str(exc)) from exc
        files = self._matching_snapshot_files(store, snapshot, parsed)
        rows, source_file_ids, warmup_count, reported_count = self._read_panel_rows(
            layout=layout,
            files=files,
            request=parsed,
            load_start=load_start,
        )
        if reported_count == 0:
            raise BacktestDataError("no_reported_rows_loaded")
        manifest = self._build_manifest(
            request=parsed,
            snapshot=snapshot,
            coverage_report=coverage_report,
            source_file_ids=source_file_ids,
            rows=rows,
            warmup_count=warmup_count,
            reported_count=reported_count,
            lockbox_window=lockbox_window,
        )
        if write_manifest:
            self._append_data_manifest(layout, manifest)
        return BacktestDataSlice(
            request=parsed,
            rows=tuple(rows),
            data_manifest=manifest,
            archive_snapshot_id=snapshot.archive_snapshot_id,
            universe_snapshot_id=parsed.universe_snapshot_id,
            coverage_report_id=coverage_report.coverage_report_id,
            loaded_fields=parsed.requested_fields,
            warmup_row_count=warmup_count,
            reported_row_count=reported_count,
        )

    def _enforce_temporal_policy(
        self,
        request: BacktestDataRequest,
        *,
        load_start: datetime,
        asof_date: date | None,
    ) -> LockboxWindow | None:
        if request.evidence_mode not in EVIDENCE_MODES:
            return None
        earliest = request.validation_config.earliest_backtest_start
        if request.start_ts.date() < earliest:
            raise BacktestDataError(
                f"reported_start_before_earliest: start={request.start_ts.date().isoformat()} "
                f"earliest={earliest.isoformat()}"
            )
        minimum_end = _add_calendar_months(
            request.start_ts,
            request.validation_config.min_usable_months,
        )
        if request.end_ts < minimum_end:
            raise BacktestDataError(
                "usable_months_below_minimum: "
                f"minimum={request.validation_config.min_usable_months}"
            )
        lockbox = latest_full_calendar_month_lockbox(
            asof_date=asof_date,
            policy=request.validation_config.lockbox_policy,
        )
        if request.exclude_lockbox and windows_overlap(
            left_start=load_start,
            left_end=request.end_ts,
            right_start=lockbox.start_ts,
            right_end=lockbox.end_ts,
        ):
            raise BacktestDataError(
                "lockbox_overlap: "
                f"request={utc_isoformat(load_start)}..{utc_isoformat(request.end_ts)} "
                f"lockbox={utc_isoformat(lockbox.start_ts)}..{utc_isoformat(lockbox.end_ts)}"
            )
        return lockbox

    def _load_archive_snapshot(
        self,
        store: ArchiveManifestStore,
        request: BacktestDataRequest,
    ) -> ArchiveSnapshotRecord:
        matches = [
            row
            for row in store.load_archive_snapshots()
            if row.archive_snapshot_id == request.archive_snapshot_id
        ]
        if len(matches) != 1:
            raise BacktestDataError(f"archive_snapshot_not_found: {request.archive_snapshot_id}")
        snapshot = matches[0]
        if snapshot.layer != ArchiveLayer.SILVER:
            raise BacktestDataError("archive_snapshot_layer_not_silver")
        if snapshot.venue_scope not in {request.venue, "all", "*"}:
            raise BacktestDataError(
                f"archive_snapshot_venue_scope_mismatch: {snapshot.venue_scope}"
            )
        return snapshot

    def _enforce_snapshot_window(
        self,
        snapshot: ArchiveSnapshotRecord,
        request: BacktestDataRequest,
        *,
        load_start: datetime,
    ) -> None:
        start = ensure_utc(snapshot.start_ts)
        end = ensure_utc(snapshot.end_ts)
        if start > load_start or end < request.end_ts:
            raise BacktestDataError(
                "archive_snapshot_window_incomplete: "
                f"snapshot={utc_isoformat(start)}..{utc_isoformat(end)} "
                f"request={utc_isoformat(load_start)}..{utc_isoformat(request.end_ts)}"
            )

    def _load_universe_row(
        self,
        archive_root: Path,
        request: BacktestDataRequest,
    ) -> UniverseSnapshotRow:
        rows = [
            row
            for row in load_universe_rows(archive_root)
            if row.snapshot_id == request.universe_snapshot_id
        ]
        if not rows:
            raise BacktestDataError(f"universe_snapshot_not_found: {request.universe_snapshot_id}")
        matches = [row for row in rows if row.instrument_id == request.instrument_id]
        if len(matches) != 1:
            raise BacktestDataError(
                f"instrument_not_in_universe_snapshot: {request.instrument_id}"
            )
        return matches[0]

    def _enforce_universe(
        self,
        request: BacktestDataRequest,
        universe_row: UniverseSnapshotRow,
    ) -> None:
        if request.evidence_mode in EVIDENCE_MODES:
            if universe_row.universe_mode != UniverseMode.AS_OF:
                raise BacktestDataError("current_universe_evidence_rejected")
            if not universe_row.accepted_research_evidence_allowed:
                raise BacktestDataError("instrument_not_evidence_allowed")
            if universe_row.evidence_scope != BacktestEvidenceMode.ACCEPTED_RESEARCH.value:
                raise BacktestDataError(f"universe_evidence_scope_not_accepted: {universe_row.evidence_scope}")
            return
        if universe_row.universe_mode == UniverseMode.CURRENT_LABELED_SANDBOX:
            return
        if universe_row.universe_mode == UniverseMode.AS_OF:
            return
        raise BacktestDataError(f"unsupported_sandbox_universe_mode: {universe_row.universe_mode.value}")

    def _select_coverage_report(
        self,
        layout: ArchiveLayout,
        request: BacktestDataRequest,
        *,
        load_start: datetime,
    ) -> CoverageReport:
        store = CoverageManifestStore(layout)
        reports = [
            report
            for report in store.query_coverage_reports(
                venue=request.venue,
                instrument_id=request.instrument_id,
                family=request.family,
                timeframe=request.timeframe,
            )
            if ensure_utc(report.start_ts) <= load_start and ensure_utc(report.end_ts) >= request.end_ts
        ]
        if not reports:
            raise BacktestDataError("coverage_report_not_found")
        return sorted(
            reports,
            key=lambda report: (
                report.coverage_ratio,
                ensure_utc(report.start_ts),
                ensure_utc(report.end_ts),
                report.coverage_report_id,
            ),
            reverse=True,
        )[0]

    def _matching_snapshot_files(
        self,
        store: ArchiveManifestStore,
        snapshot: ArchiveSnapshotRecord,
        request: BacktestDataRequest,
    ) -> list[FileManifestRow]:
        included_file_ids = set(snapshot.included_file_ids)
        rows = [
            row
            for row in store.load_file_manifest()
            if row.file_id in included_file_ids
            and row.layer == ArchiveLayer.SILVER
            and row.venue == request.venue
            and row.datatype == request.family
            and row.instrument_id == request.instrument_id
            and row.timeframe == request.timeframe
        ]
        if not rows:
            raise BacktestDataError("archive_snapshot_no_matching_files")
        return sorted(rows, key=lambda row: (row.date or "", row.path, row.file_id))

    def _read_panel_rows(
        self,
        *,
        layout: ArchiveLayout,
        files: list[FileManifestRow],
        request: BacktestDataRequest,
        load_start: datetime,
    ) -> tuple[list[dict[str, Any]], tuple[str, ...], int, int]:
        output_rows: list[tuple[datetime, str, dict[str, Any]]] = []
        source_file_ids: list[str] = []
        read_fields = set(request.requested_fields) | {"ts"}
        for file_row in files:
            path = layout.resolve(file_row.path)
            if not path.exists():
                raise BacktestDataError(f"archive_snapshot_file_missing: {file_row.path}")
            parquet_file = pq.ParquetFile(path)
            available_fields = set(parquet_file.schema.names)
            missing_fields = sorted(read_fields - available_fields)
            if missing_fields:
                raise BacktestDataError(
                    "requested_field_not_found: " + ",".join(missing_fields)
                )
            table = parquet_file.read(columns=sorted(read_fields))
            file_had_rows = False
            for row in table.to_pylist():
                ts = parse_timestamp(row["ts"])
                if load_start <= ts < request.end_ts:
                    file_had_rows = True
                    output = {
                        field: ts if field == "ts" else row.get(field)
                        for field in request.requested_fields
                    }
                    output_rows.append((ts, file_row.file_id, output))
            if file_had_rows:
                source_file_ids.append(file_row.file_id)
        if not output_rows:
            raise BacktestDataError("no_archive_rows_loaded")
        output_rows.sort(key=lambda item: (item[0], item[1]))
        rows = [row for _ts, _file_id, row in output_rows]
        warmup_count = sum(1 for ts, _file_id, _row in output_rows if ts < request.start_ts)
        reported_count = sum(1 for ts, _file_id, _row in output_rows if request.start_ts <= ts < request.end_ts)
        return rows, tuple(dict.fromkeys(source_file_ids)), warmup_count, reported_count

    def _build_manifest(
        self,
        *,
        request: BacktestDataRequest,
        snapshot: ArchiveSnapshotRecord,
        coverage_report: CoverageReport,
        source_file_ids: tuple[str, ...],
        rows: list[dict[str, Any]],
        warmup_count: int,
        reported_count: int,
        lockbox_window: LockboxWindow | None,
    ) -> BacktestDataManifest:
        request_hash = canonical_json_hash(request.model_dump(mode="json"))
        identity = {
            "request_hash": request_hash,
            "archive_snapshot_id": snapshot.archive_snapshot_id,
            "universe_snapshot_id": request.universe_snapshot_id,
            "coverage_report_id": coverage_report.coverage_report_id,
            "source_file_ids": source_file_ids,
            "loaded_fields": request.requested_fields,
            "row_count": len(rows),
            "warmup_row_count": warmup_count,
            "reported_row_count": reported_count,
        }
        return BacktestDataManifest(
            data_manifest_id=canonical_json_hash(identity),
            request_hash=request_hash,
            archive_snapshot_id=snapshot.archive_snapshot_id,
            universe_snapshot_id=request.universe_snapshot_id,
            coverage_report_id=coverage_report.coverage_report_id,
            source_file_ids=source_file_ids,
            venue=request.venue,
            instrument_id=request.instrument_id,
            family=request.family,
            timeframe=request.timeframe,
            evidence_mode=request.evidence_mode,
            loaded_fields=request.requested_fields,
            start_ts=request.start_ts,
            end_ts=request.end_ts,
            warmup_start_ts=request.warmup_start_ts,
            lockbox_start_ts=lockbox_window.start_ts if lockbox_window else None,
            lockbox_end_ts=lockbox_window.end_ts if lockbox_window else None,
            coverage_ratio=coverage_report.coverage_ratio,
            coverage_min=request.validation_config.coverage_min,
            row_count=len(rows),
            warmup_row_count=warmup_count,
            reported_row_count=reported_count,
        )

    def _append_data_manifest(
        self,
        layout: ArchiveLayout,
        manifest: BacktestDataManifest,
    ) -> None:
        path = layout.resolve("manifests", "backtest_data_requests.parquet")
        records = []
        if path.exists():
            records = pq.read_table(path).to_pylist()
        by_id = {row["data_manifest_id"]: row for row in records}
        by_id[manifest.data_manifest_id] = _model_row(manifest)
        ordered = sorted(by_id.values(), key=lambda row: row["data_manifest_id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pylist(ordered), path, compression="zstd")


def _add_calendar_months(value: datetime, months: int) -> datetime:
    month_index = (value.year * 12) + (value.month - 1) + months
    year = month_index // 12
    month = (month_index % 12) + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _model_row(record: BaseModel) -> dict[str, Any]:
    return record.model_dump(mode="json")
