# V2-AUDIT-ID: V2-AUD-QUAL-001
# V2-CONTRACTS: docs/contracts/data_quality_contract.md, docs/contracts/archive_contract.md
# V2-BOUNDARY: research_only, coverage_manifest, no_live_imports
# V2-OWNER: v2_data_quality
"""Parquet-backed coverage and data-quality report manifests."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta
from pathlib import Path
from typing import TypeVar

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel

from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.data_quality.schemas import CoverageReport, DataQualityCheck

ModelT = TypeVar("ModelT", bound=BaseModel)


class CoverageManifestStore:
    def __init__(self, layout: ArchiveLayout) -> None:
        self.layout = layout

    @property
    def coverage_reports_path(self) -> Path:
        return self.layout.resolve("manifests", "data_coverage.parquet")

    @property
    def quality_checks_path(self) -> Path:
        return self.layout.resolve("manifests", "data_quality_checks.parquet")

    def append_coverage_report(self, report: CoverageReport) -> None:
        self.append_coverage_reports((report,))

    def append_coverage_reports(self, reports: Iterable[CoverageReport]) -> None:
        incoming_by_id = {report.coverage_report_id: report for report in reports}
        incoming = list(incoming_by_id.values())
        if not incoming:
            return
        records = [
            existing
            for existing in self.load_coverage_reports()
            if existing.coverage_report_id not in incoming_by_id
        ]
        records.extend(incoming)
        records.sort(
            key=lambda item: (
                item.venue,
                item.instrument_id,
                item.family,
                item.timeframe,
                item.start_ts,
                item.end_ts,
                item.coverage_report_id,
            )
        )
        _write_models(self.coverage_reports_path, records)

    def append_quality_checks(self, checks: Iterable[DataQualityCheck]) -> None:
        incoming = list(checks)
        if not incoming:
            return
        incoming_ids = {check.check_id for check in incoming}
        records = [
            existing
            for existing in self.load_quality_checks()
            if existing.check_id not in incoming_ids
        ]
        records.extend(incoming)
        records.sort(
            key=lambda item: (
                item.venue,
                item.instrument_id,
                item.family,
                item.timeframe,
                item.check_type,
                item.start_ts,
                item.check_id,
            )
        )
        _write_models(self.quality_checks_path, records)

    def load_coverage_reports(self) -> list[CoverageReport]:
        return _read_models(self.coverage_reports_path, CoverageReport)

    def load_quality_checks(self) -> list[DataQualityCheck]:
        return _read_models(self.quality_checks_path, DataQualityCheck)

    def query_coverage_reports(
        self,
        *,
        venue: str | None = None,
        instrument_id: str | None = None,
        family: str | None = None,
        timeframe: str | None = None,
        window_date: date | str | None = None,
    ) -> list[CoverageReport]:
        date_value = date.fromisoformat(window_date) if isinstance(window_date, str) else window_date
        reports = self.load_coverage_reports()
        filtered: list[CoverageReport] = []
        for report in reports:
            if venue is not None and report.venue != venue:
                continue
            if instrument_id is not None and report.instrument_id != instrument_id:
                continue
            if family is not None and report.family != family:
                continue
            if timeframe is not None and report.timeframe != timeframe:
                continue
            last_included_date = (report.end_ts - timedelta(microseconds=1)).date()
            if date_value is not None and not (report.start_ts.date() <= date_value <= last_included_date):
                continue
            filtered.append(report)
        return filtered


def write_coverage_manifest(
    archive_root: str | Path,
    reports: Iterable[CoverageReport],
) -> list[CoverageReport]:
    store = CoverageManifestStore(ArchiveLayout(archive_root))
    materialized = list(reports)
    store.append_coverage_reports(materialized)
    return materialized


def query_coverage_reports(
    archive_root: str | Path,
    *,
    venue: str | None = None,
    instrument_id: str | None = None,
    family: str | None = None,
    timeframe: str | None = None,
    window_date: date | str | None = None,
) -> list[CoverageReport]:
    return CoverageManifestStore(ArchiveLayout(archive_root)).query_coverage_reports(
        venue=venue,
        instrument_id=instrument_id,
        family=family,
        timeframe=timeframe,
        window_date=window_date,
    )


def _read_models(path: Path, model: type[ModelT]) -> list[ModelT]:
    if not path.exists():
        return []
    table = pq.read_table(path)
    return [model.model_validate(row) for row in table.to_pylist()]


def _write_models(path: Path, records: Iterable[BaseModel]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [record.model_dump(mode="json") for record in records]
    pq.write_table(pa.Table.from_pylist(rows), path, compression="zstd")
