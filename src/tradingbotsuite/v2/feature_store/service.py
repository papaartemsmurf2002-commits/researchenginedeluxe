# V2-AUDIT-ID: V2-AUD-DATASRC-060
# V2-CONTRACTS: docs/contracts/data_source_registry_contract.md
# V2-BOUNDARY: research_only, feature_catalog, no_live_imports, no_archive_writes
# V2-OWNER: v2_feature_store
"""Read-only discovery over materialized feature-store artifacts."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from tradingbotsuite.v2.archive.hashing import canonical_json_hash
from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.archive.manifest_store import ArchiveManifestStore
from tradingbotsuite.v2.archive.schemas import ArchiveLayer, FileManifestRow
from tradingbotsuite.v2.config.schemas import RESEARCH_BOUNDARY, V2_SCHEMA_VERSION
from tradingbotsuite.v2.data_quality.reports import CoverageManifestStore
from tradingbotsuite.v2.data_quality.schemas import CoverageReport
from tradingbotsuite.v2.feature_store.schemas import FeatureCatalog, FeatureCatalogEntry
from tradingbotsuite.v2.security.boundary import require_research_boundary


DEFAULT_FEATURE_MATERIALIZATION_GLOB = (
    "data/research/of_style_feature_materialization/**/manifests/*feature-materialization-report.json"
)


class FeatureStoreCatalogService:
    """Build a catalog from existing feature materialization reports.

    The service is intentionally read-only. It does not inspect venues, fetch
    files, or materialize rows.
    """

    def __init__(
        self,
        *,
        repo_root: str | Path = ".",
        archive_root: str | Path | None = "data/research/central_market_history",
        materialization_report_paths: Iterable[str | Path] | None = None,
    ) -> None:
        self.repo_root = Path(repo_root)
        self.archive_root = None if archive_root is None else Path(archive_root)
        self.materialization_report_paths = (
            tuple(Path(path) for path in materialization_report_paths)
            if materialization_report_paths is not None
            else None
        )

    def build_catalog(self) -> FeatureCatalog:
        entries: list[FeatureCatalogEntry] = []
        for report_path in self._report_paths():
            entries.extend(self._entries_from_report(report_path))
        entries.extend(self._entries_from_archive_features())
        entries = sorted(
            entries,
            key=lambda item: (
                item.feature_family,
                item.symbol,
                item.source_family,
                item.timeframe or "",
                item.start_ts or datetime.min.replace(tzinfo=UTC),
                item.output_ref,
            ),
        )
        payload = {
            "entries": tuple(entries),
            "feature_families": tuple(sorted({entry.feature_family for entry in entries})),
            "source_families": tuple(sorted({entry.source_family for entry in entries})),
            "symbols": tuple(sorted({entry.symbol for entry in entries})),
            "entry_count": len(entries),
            "total_feature_rows": sum(entry.row_count for entry in entries),
            **dict(RESEARCH_BOUNDARY),
        }
        return FeatureCatalog(
            **payload,
            catalog_id=canonical_json_hash(
                {
                    "schema_version": V2_SCHEMA_VERSION,
                    "entries": [entry.model_dump(mode="json") for entry in entries],
                }
            ),
        )

    def query(
        self,
        *,
        feature_family: str | None = None,
        source_family: str | None = None,
        venue: str | None = None,
        symbol: str | None = None,
        instrument_id: str | None = None,
        instrument_ids: tuple[str, ...] = (),
        timeframe: str | None = None,
        evidence_scope: str | None = None,
        accepted_only: bool = False,
        start_ts: datetime | None = None,
        end_ts: datetime | None = None,
    ) -> tuple[FeatureCatalogEntry, ...]:
        entries = self.build_catalog().entries
        filtered: list[FeatureCatalogEntry] = []
        symbol_upper = symbol.upper() if symbol else None
        instrument_filter = tuple(dict.fromkeys((instrument_id,) if instrument_id is not None else instrument_ids))
        for entry in entries:
            if feature_family is not None and entry.feature_family != feature_family:
                continue
            if source_family is not None and entry.source_family != source_family:
                continue
            if venue is not None and entry.venue != venue:
                continue
            if symbol_upper is not None and entry.symbol.upper() != symbol_upper:
                continue
            if instrument_filter and entry.instrument_id not in instrument_filter:
                continue
            if timeframe is not None and entry.timeframe != timeframe:
                continue
            if evidence_scope is not None and entry.evidence_scope != evidence_scope:
                continue
            if accepted_only and not entry.accepted_research_evidence_allowed:
                continue
            if start_ts is not None and entry.end_ts is not None and entry.end_ts <= start_ts:
                continue
            if end_ts is not None and entry.start_ts is not None and entry.start_ts >= end_ts:
                continue
            filtered.append(entry)
        return tuple(filtered)

    def _report_paths(self) -> tuple[Path, ...]:
        if self.materialization_report_paths is not None:
            return tuple(path for path in self.materialization_report_paths if path.exists())
        return tuple(sorted(self.repo_root.glob(DEFAULT_FEATURE_MATERIALIZATION_GLOB)))

    def _entries_from_report(self, report_path: Path) -> tuple[FeatureCatalogEntry, ...]:
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return ()
        if report.get("report_type") != "of_style_feature_materialization_report":
            return ()
        try:
            require_research_boundary(report, context="feature materialization report")
        except ValueError:
            return ()
        report_id = str(report.get("materialization_report_id") or "")
        report_ref = _relative_ref(report_path, self.repo_root)
        rows = report.get("source_results", ())
        if not isinstance(rows, list):
            return ()
        entries: list[FeatureCatalogEntry] = []
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            if str(row.get("status", "")) != "materialized":
                continue
            try:
                entries.append(
                    _entry_from_source_result(
                        row,
                        report_id=report_id,
                        report_ref=report_ref,
                    )
                )
            except (TypeError, ValueError):
                continue
        return tuple(entries)

    def _entries_from_archive_features(self) -> tuple[FeatureCatalogEntry, ...]:
        if self.archive_root is None:
            return ()
        archive_root = self.archive_root if self.archive_root.is_absolute() else self.repo_root / self.archive_root
        if not archive_root.exists():
            return ()
        layout = ArchiveLayout(archive_root)
        store = ArchiveManifestStore(layout)
        try:
            files = [row for row in store.load_file_manifest() if row.layer == ArchiveLayer.SILVER]
            coverage_reports = CoverageManifestStore(layout).load_coverage_reports()
        except Exception:
            return ()
        coverage_by_key: dict[tuple[str, str, str, str], list[CoverageReport]] = defaultdict(list)
        for report in coverage_reports:
            coverage_by_key[(report.venue, report.instrument_id, report.family, report.timeframe)].append(report)
        entries: list[FeatureCatalogEntry] = []
        for row in files:
            if row.instrument_id is None or row.timeframe is None:
                continue
            fields = _parquet_fields(layout, row)
            feature_families = _archive_feature_families(fields)
            if not feature_families:
                continue
            coverage = _best_coverage_report(
                coverage_by_key.get((row.venue, str(row.instrument_id), row.datatype, row.timeframe), ())
            )
            for feature_family in feature_families:
                try:
                    entries.append(
                        _entry_from_archive_feature(
                            row,
                            feature_family=feature_family,
                            fields=fields,
                            coverage_report=coverage,
                            archive_root=archive_root,
                        )
                    )
                except (TypeError, ValueError):
                    continue
        return tuple(entries)


def _entry_from_source_result(
    row: Mapping[str, Any],
    *,
    report_id: str,
    report_ref: str,
) -> FeatureCatalogEntry:
    require_research_boundary(row, context="feature materialization source result")
    family = str(row["family"])
    feature_family = str(row["feature_family"])
    symbol = str(row["symbol"]).upper()
    venue_symbol = str(row["venue_symbol"]).upper()
    timeframe = row.get("interval")
    start_ts, end_ts = _window_from_day(row.get("day"), timeframe)
    output_ref = str(row["output_ref"])
    output_sha256 = row.get("output_sha256")
    payload = {
        "feature_family": feature_family,
        "source_family": family,
        "source_id": f"binance_usdm_daily_{family}",
        "venue": "binance_usdm",
        "symbol": symbol,
        "venue_symbol": venue_symbol,
        "instrument_id": f"binance:perp:{venue_symbol}",
        "timeframe": timeframe,
        "start_ts": start_ts,
        "end_ts": end_ts,
        "row_count": int(row.get("feature_row_count", 0)),
        "input_row_count": int(row.get("input_row_count", 0)),
        "output_format": str(row.get("output_format", "jsonl")),
        "output_ref": output_ref,
        "output_sha256": output_sha256 if output_sha256 else None,
        "output_part_refs": tuple(str(ref) for ref in row.get("output_part_refs", ()) or ()),
        "materialization_report_id": report_id or "unknown",
        "materialization_report_ref": report_ref,
        "evidence_scope": "feature_materialization",
        "accepted_research_evidence_allowed": False,
        "usable_archive_ref": f"feature://{feature_family}/{symbol}/{output_ref}",
        "blocker_reasons": ("not_accepted_historical_coverage_proof",),
        **dict(RESEARCH_BOUNDARY),
    }
    return FeatureCatalogEntry(
        **payload,
        feature_catalog_id=canonical_json_hash(
            {
                "schema_version": V2_SCHEMA_VERSION,
                "feature_family": feature_family,
                "source_family": family,
                "symbol": symbol,
                "timeframe": timeframe,
                "start_ts": None if start_ts is None else start_ts.isoformat(),
                "end_ts": None if end_ts is None else end_ts.isoformat(),
                "output_ref": output_ref,
                "output_sha256": output_sha256,
                "report_id": report_id,
            }
        ),
    )


def _entry_from_archive_feature(
    row: FileManifestRow,
    *,
    feature_family: str,
    fields: tuple[str, ...],
    coverage_report: CoverageReport | None,
    archive_root: Path,
) -> FeatureCatalogEntry:
    instrument_id = str(row.instrument_id)
    symbol = _symbol_from_instrument(instrument_id)
    start_ts = None if coverage_report is None else coverage_report.start_ts
    end_ts = None if coverage_report is None else coverage_report.end_ts
    accepted = bool(
        coverage_report is not None
        and coverage_report.evidence_eligible
        and coverage_report.quality_status.value == "pass"
    )
    output_ref = f"archive://{row.venue}/{row.datatype}/{instrument_id}/{row.timeframe}/{row.file_id}"
    payload = {
        "feature_family": feature_family,
        "source_family": row.datatype,
        "source_id": row.created_by_job_id,
        "venue": row.venue,
        "symbol": symbol,
        "venue_symbol": symbol,
        "instrument_id": instrument_id,
        "timeframe": row.timeframe,
        "start_ts": start_ts,
        "end_ts": end_ts,
        "row_count": int(row.row_count or 0),
        "input_row_count": int(row.row_count or 0),
        "output_format": "archive_parquet_projection",
        "output_ref": output_ref,
        "output_sha256": row.sha256,
        "output_part_refs": (),
        "materialization_report_id": "archive_feature_projection",
        "materialization_report_ref": _relative_ref(archive_root / "manifests" / "file_manifest.parquet", archive_root),
        "evidence_scope": "archive_feature_projection",
        "accepted_research_evidence_allowed": accepted,
        "usable_archive_ref": output_ref,
        "blocker_reasons": () if accepted else ("accepted_coverage_report_missing",),
        **dict(RESEARCH_BOUNDARY),
    }
    return FeatureCatalogEntry(
        **payload,
        feature_catalog_id=canonical_json_hash(
            {
                "schema_version": V2_SCHEMA_VERSION,
                "feature_family": feature_family,
                "source_family": row.datatype,
                "instrument_id": instrument_id,
                "timeframe": row.timeframe,
                "fields": fields,
                "file_id": row.file_id,
                "coverage_report_id": None if coverage_report is None else coverage_report.coverage_report_id,
            }
        ),
    )


def _archive_feature_families(fields: tuple[str, ...]) -> tuple[str, ...]:
    field_set = set(fields)
    families: list[str] = []
    if {"funding", "funding_rate"} & field_set:
        families.append("funding")
    if "open_interest" in field_set:
        families.append("open_interest")
    if "spread" in field_set or "spread_bps" in field_set:
        families.append("bbo_spread")
    if {"mark_price", "oracle_price"} & field_set:
        families.append("kline_context")
    if {"open", "high", "low", "close", "volume"} <= field_set:
        families.append("derived_bar_context")
    return tuple(dict.fromkeys(families))


def _best_coverage_report(reports: Iterable[CoverageReport]) -> CoverageReport | None:
    rows = tuple(reports)
    if not rows:
        return None
    return sorted(
        rows,
        key=lambda item: (
            item.evidence_eligible,
            item.coverage_ratio,
            item.start_ts,
            item.end_ts,
            item.coverage_report_id,
        ),
        reverse=True,
    )[0]


def _parquet_fields(layout: ArchiveLayout, row: FileManifestRow) -> tuple[str, ...]:
    try:
        path = layout.resolve(row.path)
        if not path.exists():
            return ()
        return tuple(pq.ParquetFile(path).schema.names)
    except Exception:
        return ()


def _symbol_from_instrument(instrument_id: str) -> str:
    return instrument_id.split(":")[-1].upper().removesuffix("USDT")


def _window_from_day(value: Any, timeframe: Any) -> tuple[datetime | None, datetime | None]:
    if not value:
        return None, None
    try:
        start = datetime.fromisoformat(str(value)).replace(tzinfo=UTC)
    except ValueError:
        return None, None
    seconds = _interval_seconds(timeframe)
    if seconds is None:
        return start, start + timedelta(days=1)
    return start, start + timedelta(days=1)


def _interval_seconds(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value)
    if len(text) < 2:
        return None
    try:
        amount = int(text[:-1])
    except ValueError:
        return None
    if text.endswith("m"):
        return amount * 60
    if text.endswith("h"):
        return amount * 60 * 60
    if text.endswith("d"):
        return amount * 24 * 60 * 60
    return None


def _relative_ref(path: Path, root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(root.resolve(strict=False)).as_posix()
    except ValueError:
        return str(path.resolve(strict=False))
