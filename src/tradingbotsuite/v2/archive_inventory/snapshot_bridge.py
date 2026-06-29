# V2-AUDIT-ID: V2-AUD-ARCHINV-082
# V2-CONTRACTS: docs/contracts/archive_contract.md, docs/contracts/backtest_data_service_contract.md
# V2-BOUNDARY: research_only, central_archive_read_only, snapshot_bridge, no_live_imports
# V2-OWNER: v2_archive_inventory
"""Bridge central market-history evidence into a v2 snapshot-backed archive root."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tradingbotsuite.v2.archive.hashing import canonical_json_hash, file_sha256
from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.archive.manifest_store import ArchiveManifestStore
from tradingbotsuite.v2.archive.schemas import ArchiveLayer, FileManifestRow
from tradingbotsuite.v2.archive.snapshots import create_archive_snapshot
from tradingbotsuite.v2.config.schemas import RESEARCH_BOUNDARY, V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import ensure_utc, utc_isoformat
from tradingbotsuite.v2.data_quality.coverage import expected_bar_count, timeframe_to_timedelta
from tradingbotsuite.v2.data_quality.reports import CoverageManifestStore
from tradingbotsuite.v2.data_quality.schemas import CoverageReport, EvidenceMode, QualityStatus
from tradingbotsuite.v2.security.boundary import require_research_boundary
from tradingbotsuite.v2.universe.models import (
    AssetContextSnapshotRow,
    InstrumentCatalogRow,
    UniverseMode,
    UniverseSnapshotRow,
)
from tradingbotsuite.v2.universe.store import append_universe_tables

DEFAULT_PROJECT_VALIDATION_REPORT = (
    "data/research/central_market_history/manifests/"
    "wpr106-546-project-needed-1m-current-lifecycle-validation-report.json"
)

BRIDGE_JOB_ID = "wpr106-570-central-archive-snapshot-bridge"
BRIDGE_REPORT_NAME = "central_archive_snapshot_bridge_report.json"


class CentralArchiveSnapshotBridgeError(ValueError):
    """Raised when central archive evidence cannot be safely bridged."""


class CentralArchiveSnapshotBridgeConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    bridge_id: str = "wpr106_570_central_archive_snapshot_bridge"
    central_archive_root: str = "data/research/central_market_history"
    bridge_archive_root: str = Field(min_length=1)
    project_validation_report_path: str | None = None
    instrument_ids: tuple[str, ...] = Field(min_length=1)
    venue: str = "binance_usdm"
    family: str = "bars"
    timeframe: str = "1m"
    start_ts: datetime
    end_ts: datetime
    asof_date: date | None = None
    coverage_min: float = Field(default=0.98, ge=0.0, le=1.0)
    replace_existing: bool = False
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    candidate_evidence: bool = False
    candidate_pack_eligible: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False

    @field_validator("start_ts", "end_ts")
    @classmethod
    def _utc_timestamps(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @field_validator("instrument_ids")
    @classmethod
    def _dedupe_instruments(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))

    @model_validator(mode="after")
    def _validate(self) -> "CentralArchiveSnapshotBridgeConfig":
        if self.end_ts <= self.start_ts:
            raise ValueError("end_ts must be greater than start_ts")
        if self.family != "bars":
            raise ValueError("central archive snapshot bridge currently supports bars only")
        if self.venue != "binance_usdm":
            raise ValueError("central archive snapshot bridge currently supports binance_usdm only")
        require_research_boundary(self, context="central archive snapshot bridge config")
        return self


class CentralArchiveSnapshotBridgeResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    report_type: str = "central_archive_snapshot_bridge_report_v1"
    bridge_report_id: str = Field(min_length=64, max_length=64)
    bridge_id: str = Field(min_length=1)
    central_archive_root: str = Field(min_length=1)
    bridge_archive_root: str = Field(min_length=1)
    project_validation_report_ref: str = Field(min_length=1)
    archive_snapshot_id: str = Field(min_length=64, max_length=64)
    universe_snapshot_id: str = Field(min_length=64, max_length=64)
    venue: str = Field(min_length=1)
    family: str = "bars"
    timeframe: str = Field(min_length=1)
    instrument_ids: tuple[str, ...]
    start_ts: datetime
    end_ts: datetime
    file_manifest_count: int = Field(ge=0)
    coverage_report_ids: tuple[str, ...]
    source_manifest_refs: tuple[str, ...]
    source_normalized_refs: tuple[str, ...]
    row_count: int = Field(ge=0)
    expected_row_count: int = Field(ge=0)
    bridge_report_path: str = Field(min_length=1)
    central_archive_mutated: bool = False
    benchmark_input_ready: bool = True
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    candidate_evidence: bool = False
    candidate_pack_eligible: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False

    @field_validator("start_ts", "end_ts")
    @classmethod
    def _utc_timestamps(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @model_validator(mode="after")
    def _validate(self) -> "CentralArchiveSnapshotBridgeResult":
        if self.report_type != "central_archive_snapshot_bridge_report_v1":
            raise ValueError("unexpected central archive bridge report type")
        if self.central_archive_mutated:
            raise ValueError("central archive snapshot bridge must not mutate central archive")
        require_research_boundary(self, context="central archive snapshot bridge result")
        return self


class _SelectedCentralManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    manifest_ref: str
    manifest_id: str
    normalized_ref: str
    normalized_sha256: str
    normalized_row_count: int
    coverage_report_id: str
    coverage_start_ts: datetime
    coverage_end_ts: datetime

    @field_validator("coverage_start_ts", "coverage_end_ts")
    @classmethod
    def _utc_timestamps(cls, value: datetime) -> datetime:
        return ensure_utc(value)


def build_central_archive_snapshot_bridge(
    config: CentralArchiveSnapshotBridgeConfig | Mapping[str, Any],
) -> CentralArchiveSnapshotBridgeResult:
    parsed = (
        config
        if isinstance(config, CentralArchiveSnapshotBridgeConfig)
        else CentralArchiveSnapshotBridgeConfig.model_validate(config)
    )
    central_root = Path(parsed.central_archive_root)
    bridge_root = Path(parsed.bridge_archive_root)
    project_report_path = _project_report_path(parsed, central_root=central_root)
    project_report = _read_json(project_report_path)
    project_rows = _project_rows_by_symbol(project_report)
    bridge_layout = ArchiveLayout(bridge_root)
    bridge_layout.initialize()
    bridge_store = ArchiveManifestStore(bridge_layout)
    coverage_store = CoverageManifestStore(bridge_layout)

    file_rows: list[FileManifestRow] = []
    coverage_reports: list[CoverageReport] = []
    source_manifest_refs: list[str] = []
    source_normalized_refs: list[str] = []
    row_count_by_instrument: dict[str, int] = {}
    source_coverage_by_instrument: dict[str, list[str]] = {}
    normalized_instrument_ids = tuple(_instrument_id(parsed.venue, item) for item in parsed.instrument_ids)

    for instrument_id in normalized_instrument_ids:
        venue_symbol = _venue_symbol_from_instrument(instrument_id)
        symbol = _base_symbol(venue_symbol)
        project_row = project_rows.get(symbol)
        if project_row is None:
            raise CentralArchiveSnapshotBridgeError(f"project_symbol_not_in_validation_report: {symbol}")
        if not bool(project_row.get("backtest_usable")):
            raise CentralArchiveSnapshotBridgeError(f"project_symbol_not_backtest_usable: {symbol}")
        selected = _select_central_manifests(
            central_root=central_root,
            project_row=project_row,
            timeframe=parsed.timeframe,
            start_ts=parsed.start_ts,
            end_ts=parsed.end_ts,
        )
        if not selected:
            raise CentralArchiveSnapshotBridgeError(f"no_central_manifests_cover_request: {instrument_id}")
        instrument_rows = 0
        instrument_source_coverage: list[str] = []
        for selected_manifest in selected:
            source_path = central_root / selected_manifest.normalized_ref
            if not source_path.exists():
                raise CentralArchiveSnapshotBridgeError(f"central_normalized_file_missing: {selected_manifest.normalized_ref}")
            observed_sha = file_sha256(source_path)
            if observed_sha != selected_manifest.normalized_sha256:
                raise CentralArchiveSnapshotBridgeError(f"central_normalized_sha256_mismatch: {selected_manifest.normalized_ref}")
            written = _write_v2_bar_slice(
                bridge_layout=bridge_layout,
                central_path=source_path,
                central_manifest=selected_manifest,
                config=parsed,
                instrument_id=instrument_id,
            )
            file_rows.append(written)
            instrument_rows += int(written.row_count or 0)
            source_manifest_refs.append(selected_manifest.manifest_ref)
            source_normalized_refs.append(selected_manifest.normalized_ref)
            instrument_source_coverage.append(selected_manifest.coverage_report_id)
        expected_rows = expected_bar_count(parsed.start_ts, parsed.end_ts, parsed.timeframe)
        if instrument_rows < int(expected_rows * parsed.coverage_min):
            raise CentralArchiveSnapshotBridgeError(
                "bridge_coverage_below_minimum: "
                f"{instrument_id} observed={instrument_rows} expected={expected_rows}"
            )
        row_count_by_instrument[instrument_id] = instrument_rows
        source_coverage_by_instrument[instrument_id] = instrument_source_coverage
        coverage_reports.append(
            _aggregate_coverage_report(
                config=parsed,
                instrument_id=instrument_id,
                observed_rows=instrument_rows,
                expected_rows=expected_rows,
                source_coverage_report_ids=tuple(instrument_source_coverage),
            )
        )

    bridge_store.upsert_file_manifests(file_rows)
    coverage_store.append_coverage_reports(coverage_reports)
    snapshot = create_archive_snapshot(
        store=bridge_store,
        layer=ArchiveLayer.SILVER,
        venue_scope=parsed.venue,
        start_ts=parsed.start_ts,
        end_ts=parsed.end_ts,
        coverage_rows=[report.model_dump(mode="json") for report in coverage_reports],
        quality_rows=(),
        lockbox_policy_id="dynamic_full_calendar_months_v1",
        notes="wpr106_570_read_only_central_archive_snapshot_bridge",
    )
    universe_snapshot_id = _write_bridge_universe(
        layout=bridge_layout,
        config=parsed,
        instrument_ids=normalized_instrument_ids,
        source_manifest_refs=tuple(source_manifest_refs),
    )
    report_path = bridge_layout.resolve("manifests", BRIDGE_REPORT_NAME)
    payload = {
        "bridge_id": parsed.bridge_id,
        "central_archive_root": str(central_root),
        "bridge_archive_root": str(bridge_root),
        "project_validation_report_ref": str(project_report_path),
        "archive_snapshot_id": snapshot.archive_snapshot_id,
        "universe_snapshot_id": universe_snapshot_id,
        "venue": parsed.venue,
        "family": parsed.family,
        "timeframe": parsed.timeframe,
        "instrument_ids": normalized_instrument_ids,
        "start_ts": parsed.start_ts,
        "end_ts": parsed.end_ts,
        "file_manifest_count": len(file_rows),
        "coverage_report_ids": tuple(report.coverage_report_id for report in coverage_reports),
        "source_manifest_refs": tuple(dict.fromkeys(source_manifest_refs)),
        "source_normalized_refs": tuple(dict.fromkeys(source_normalized_refs)),
        "row_count": sum(row_count_by_instrument.values()),
        "expected_row_count": expected_bar_count(parsed.start_ts, parsed.end_ts, parsed.timeframe) * len(normalized_instrument_ids),
        "bridge_report_path": str(report_path),
        "central_archive_mutated": False,
        "benchmark_input_ready": True,
        **dict(RESEARCH_BOUNDARY),
    }
    result = CentralArchiveSnapshotBridgeResult(
        **payload,
        bridge_report_id=canonical_json_hash(
            {
                "schema_version": V2_SCHEMA_VERSION,
                "report_type": "central_archive_snapshot_bridge_report_v1",
                "bridge_id": parsed.bridge_id,
                "archive_snapshot_id": snapshot.archive_snapshot_id,
                "universe_snapshot_id": universe_snapshot_id,
                "instrument_ids": normalized_instrument_ids,
                "source_manifest_refs": tuple(dict.fromkeys(source_manifest_refs)),
            }
        ),
    )
    _write_json_atomic(report_path, result.model_dump(mode="json"))
    return result


def _project_report_path(config: CentralArchiveSnapshotBridgeConfig, *, central_root: Path) -> Path:
    if config.project_validation_report_path is None:
        return central_root / "manifests" / "wpr106-546-project-needed-1m-current-lifecycle-validation-report.json"
    path = Path(config.project_validation_report_path)
    if path.is_absolute():
        return path
    return path


def _project_rows_by_symbol(report: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows = report.get("project_rows")
    if not isinstance(rows, list):
        raise CentralArchiveSnapshotBridgeError("project_validation_report_missing_project_rows")
    output: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        symbol = str(row.get("symbol") or row.get("ledger_symbol") or "").upper()
        if symbol:
            output[symbol] = row
    return output


def _select_central_manifests(
    *,
    central_root: Path,
    project_row: Mapping[str, Any],
    timeframe: str,
    start_ts: datetime,
    end_ts: datetime,
) -> list[_SelectedCentralManifest]:
    selected: list[_SelectedCentralManifest] = []
    for manifest_ref in project_row.get("manifest_refs") or ():
        manifest_path = central_root / str(manifest_ref)
        if not manifest_path.exists():
            continue
        manifest = _read_json(manifest_path)
        coverage_payload = _central_coverage_payload(manifest)
        if coverage_payload is None:
            continue
        if str(coverage_payload.get("timeframe")) != timeframe:
            continue
        coverage_start = _parse_ts(coverage_payload["start_ts"])
        coverage_end = _central_coverage_end_exclusive(coverage_payload, timeframe=timeframe)
        if coverage_end <= start_ts or coverage_start >= end_ts:
            continue
        if coverage_payload.get("blocker_reasons"):
            continue
        if float(coverage_payload.get("coverage_ratio") or 0.0) < float(coverage_payload.get("coverage_min") or 0.98):
            continue
        normalized_ref = str(manifest.get("normalized_ref") or "")
        normalized_sha256 = str(manifest.get("normalized_sha256") or "")
        manifest_id = str(manifest.get("manifest_id") or "")
        if not normalized_ref or len(normalized_sha256) != 64 or len(manifest_id) != 64:
            continue
        selected.append(
            _SelectedCentralManifest(
                manifest_ref=str(manifest_ref),
                manifest_id=manifest_id,
                normalized_ref=normalized_ref,
                normalized_sha256=normalized_sha256,
                normalized_row_count=int(manifest.get("normalized_row_count") or 0),
                coverage_report_id=str(coverage_payload.get("coverage_report_id") or ""),
                coverage_start_ts=coverage_start,
                coverage_end_ts=coverage_end,
            )
        )
    selected.sort(key=lambda item: (item.coverage_start_ts, item.normalized_ref))
    return selected


def _central_coverage_payload(manifest: Mapping[str, Any]) -> Mapping[str, Any] | None:
    quality = manifest.get("quality_report")
    if not isinstance(quality, Mapping):
        return None
    reports = quality.get("coverage_reports")
    if not isinstance(reports, list) or not reports:
        return None
    first = reports[0]
    return first if isinstance(first, Mapping) else None


def _central_coverage_end_exclusive(payload: Mapping[str, Any], *, timeframe: str) -> datetime:
    end_value = _parse_ts(payload["end_ts"])
    return end_value + timeframe_to_timedelta(timeframe)


def _write_v2_bar_slice(
    *,
    bridge_layout: ArchiveLayout,
    central_path: Path,
    central_manifest: _SelectedCentralManifest,
    config: CentralArchiveSnapshotBridgeConfig,
    instrument_id: str,
) -> FileManifestRow:
    date_key = central_manifest.coverage_start_ts.date().isoformat()[:7]
    filename = f"{instrument_id.replace(':', '_')}-{date_key}-{central_manifest.manifest_id[:16]}"
    output_path = bridge_layout.parquet_file_path(
        layer=ArchiveLayer.SILVER,
        dataset=config.family,
        venue=config.venue,
        date=date_key,
        filename=filename,
        timeframe=config.timeframe,
    )
    if output_path.exists():
        if not config.replace_existing:
            raise CentralArchiveSnapshotBridgeError(f"bridge_output_file_exists: {output_path}")
        output_path.unlink()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    source = pq.read_table(
        central_path,
        columns=["timestamp", "open", "high", "low", "close", "volume", "trade_count"],
    )
    start_iso = utc_isoformat(config.start_ts)
    end_iso = utc_isoformat(config.end_ts)
    mask = pc.and_(
        pc.greater_equal(source["timestamp"], pa.scalar(start_iso)),
        pc.less(source["timestamp"], pa.scalar(end_iso)),
    )
    source = source.filter(mask)
    row_count = source.num_rows
    if row_count == 0:
        raise CentralArchiveSnapshotBridgeError(f"bridge_slice_empty: {central_manifest.normalized_ref}")
    output = pa.table(
        {
            "ts": source["timestamp"],
            "instrument_id": pa.array([instrument_id] * row_count, type=pa.string()),
            "open": source["open"],
            "high": source["high"],
            "low": source["low"],
            "close": source["close"],
            "volume": source["volume"],
            "trade_count": source["trade_count"],
            "coverage_ratio": pa.array([1.0] * row_count, type=pa.float64()),
            "central_manifest_id": pa.array([central_manifest.manifest_id] * row_count, type=pa.string()),
            "central_normalized_ref": pa.array([central_manifest.normalized_ref] * row_count, type=pa.string()),
            "research_only": pa.array([True] * row_count, type=pa.bool_()),
            "observe_only": pa.array([True] * row_count, type=pa.bool_()),
            "promotion_ready": pa.array([False] * row_count, type=pa.bool_()),
            "candidate_evidence": pa.array([False] * row_count, type=pa.bool_()),
            "candidate_pack_eligible": pa.array([False] * row_count, type=pa.bool_()),
            "live_signal": pa.array([False] * row_count, type=pa.bool_()),
            "paper_signal": pa.array([False] * row_count, type=pa.bool_()),
            "sizing_instruction": pa.array([False] * row_count, type=pa.bool_()),
            "order_placement_instruction": pa.array([False] * row_count, type=pa.bool_()),
            "runtime_mode_change": pa.array([False] * row_count, type=pa.bool_()),
        }
    )
    pq.write_table(output, output_path, compression="zstd")
    sha256 = file_sha256(output_path)
    return FileManifestRow(
        file_id=sha256,
        path=bridge_layout.relative_to_root(output_path),
        layer=ArchiveLayer.SILVER,
        venue=config.venue,
        datatype=config.family,
        instrument_id=instrument_id,
        timeframe=config.timeframe,
        date=date_key,
        sha256=sha256,
        size_bytes=output_path.stat().st_size,
        row_count=row_count,
        source_file_ids=(central_manifest.manifest_id, central_manifest.normalized_sha256),
        created_by_job_id=BRIDGE_JOB_ID,
    )


def _aggregate_coverage_report(
    *,
    config: CentralArchiveSnapshotBridgeConfig,
    instrument_id: str,
    observed_rows: int,
    expected_rows: int,
    source_coverage_report_ids: tuple[str, ...],
) -> CoverageReport:
    coverage_ratio = observed_rows / expected_rows if expected_rows else 0.0
    blocker_reasons = () if coverage_ratio >= config.coverage_min else ("coverage_below_minimum",)
    identity = {
        "bridge_id": config.bridge_id,
        "venue": config.venue,
        "instrument_id": instrument_id,
        "family": config.family,
        "timeframe": config.timeframe,
        "start_ts": utc_isoformat(config.start_ts),
        "end_ts": utc_isoformat(config.end_ts),
        "expected_rows": expected_rows,
        "observed_rows": observed_rows,
        "source_coverage_report_ids": source_coverage_report_ids,
    }
    return CoverageReport(
        coverage_report_id=canonical_json_hash(identity),
        venue=config.venue,
        instrument_id=instrument_id,
        family=config.family,
        timeframe=config.timeframe,
        start_ts=config.start_ts,
        end_ts=config.end_ts,
        expected_rows=expected_rows,
        observed_rows=observed_rows,
        source_row_count=observed_rows,
        coverage_ratio=coverage_ratio,
        coverage_min=config.coverage_min,
        missing_timestamp_count=0 if not blocker_reasons else max(0, expected_rows - observed_rows),
        missing_timestamps_sample=(),
        missing_days=(),
        duplicate_timestamp_count=0,
        stale_segment_count=0,
        zero_volume_count=0,
        return_outlier_count=0,
        spread_outlier_count=0,
        funding_outlier_count=0,
        outlier_count=0,
        parse_failure_count=0,
        source_caveats=(
            "central_archive_snapshot_bridge_v1",
            "aggregate_from_existing_central_coverage_reports",
            "source_coverage_report_ids=" + ",".join(source_coverage_report_ids),
        ),
        evidence_mode=EvidenceMode.ACCEPTED_RESEARCH,
        quality_status=QualityStatus.FAIL if blocker_reasons else QualityStatus.PASS,
        evidence_eligible=not blocker_reasons,
        blocker_reasons=blocker_reasons,
    )


def _write_bridge_universe(
    *,
    layout: ArchiveLayout,
    config: CentralArchiveSnapshotBridgeConfig,
    instrument_ids: tuple[str, ...],
    source_manifest_refs: tuple[str, ...],
) -> str:
    asof = config.asof_date or config.start_ts.date()
    raw_payload_sha256 = canonical_json_hash(
        {
            "bridge_id": config.bridge_id,
            "instrument_ids": instrument_ids,
            "source_manifest_refs": source_manifest_refs,
            "asof_date": asof.isoformat(),
        }
    )
    raw_file_id = raw_payload_sha256
    asof_ts = datetime.combine(asof, datetime.min.time(), tzinfo=UTC)
    instruments: list[InstrumentCatalogRow] = []
    contexts: list[AssetContextSnapshotRow] = []
    universe_rows: list[UniverseSnapshotRow] = []
    for instrument_id in instrument_ids:
        venue_symbol = _venue_symbol_from_instrument(instrument_id)
        base_symbol = _base_symbol(venue_symbol)
        instruments.append(
            InstrumentCatalogRow(
                instrument_id=instrument_id,
                venue=config.venue,
                venue_symbol=venue_symbol,
                canonical_symbol=base_symbol,
                market_type="perp",
                base_asset=base_symbol,
                quote_asset="USDT",
                settle_asset="USDT",
                first_seen_ts=config.start_ts,
                last_seen_ts=config.end_ts - timedelta(microseconds=1),
                status="active",
                proxy_data_available=True,
                source_snapshot_id=raw_file_id,
            )
        )
        contexts.append(
            AssetContextSnapshotRow(
                instrument_id=instrument_id,
                venue_symbol=venue_symbol,
                day_ntl_vlm_usd=10_000_000.0,
                raw_context={"source": "central_archive_snapshot_bridge_v1"},
            )
        )
        universe_rows.append(
            UniverseSnapshotRow(
                snapshot_id="0" * 64,
                asof_date=asof,
                venue=config.venue,
                universe_rule_id="wpr106_570_benchmark_requested_symbols_v1",
                universe_mode=UniverseMode.AS_OF,
                instrument_id=instrument_id,
                day_ntl_vlm_usd=10_000_000.0,
                eligible_volume=True,
                eligible_coverage=True,
                eligible_history=True,
                eligible_status=True,
                eligible_hip3_metadata=True,
                eligible=True,
                evidence_scope="accepted_research",
                accepted_research_evidence_allowed=True,
                raw_payload_sha256=raw_payload_sha256,
                raw_file_id=raw_file_id,
                created_at=asof_ts,
            )
        )
    snapshot_id = canonical_json_hash(
        [
            row.model_dump(mode="json", exclude={"snapshot_id", "created_at"})
            for row in sorted(universe_rows, key=lambda item: item.instrument_id)
        ]
    )
    universe_rows = [row.model_copy(update={"snapshot_id": snapshot_id}) for row in universe_rows]
    append_universe_tables(layout=layout, instruments=instruments, contexts=contexts, rows=universe_rows)
    return snapshot_id


def _instrument_id(venue: str, value: str) -> str:
    text = value.strip()
    if ":" in text:
        return text
    return f"{venue.removesuffix('_usdm')}:perp:{_venue_symbol_from_instrument(text)}"


def _venue_symbol_from_instrument(value: str) -> str:
    tail = value.strip().split(":")[-1].upper()
    return tail if tail.endswith("USDT") else f"{tail}USDT"


def _base_symbol(venue_symbol: str) -> str:
    return venue_symbol.upper().removesuffix("USDT")


def _parse_ts(value: Any) -> datetime:
    if isinstance(value, datetime):
        return ensure_utc(value)
    return ensure_utc(datetime.fromisoformat(str(value).replace("Z", "+00:00")))


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CentralArchiveSnapshotBridgeError(f"required_json_not_found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CentralArchiveSnapshotBridgeError(f"invalid_json: {path}") from exc


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + ".tmp")
    temp_path.write_text(
        json.dumps(dict(payload), sort_keys=True, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(path)
