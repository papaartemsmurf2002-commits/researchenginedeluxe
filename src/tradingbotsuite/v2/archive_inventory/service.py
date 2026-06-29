# V2-AUDIT-ID: V2-AUD-ARCH-020
# V2-CONTRACTS: docs/contracts/archive_contract.md, docs/contracts/backtest_data_service_contract.md
# V2-BOUNDARY: research_only, archive_inventory, no_live_imports, no_archive_writes
# V2-OWNER: v2_archive_inventory
"""Archive inventory and strategy data-requirement resolver."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from tradingbotsuite.v2.archive.hashing import canonical_json_hash
from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.archive.manifest_store import ArchiveManifestStore
from tradingbotsuite.v2.archive.schemas import ArchiveLayer, ArchiveSnapshotRecord, FileManifestRow
from tradingbotsuite.v2.archive_inventory.schemas import (
    ArchiveInventory,
    ArchiveInventoryRecord,
    ArchiveInventorySummary,
    ArtifactMode,
    DataGapRequest,
    StrategyDataRequirementReport,
    StrategyDataRequirementRequest,
)
from tradingbotsuite.v2.backtest_data.lockbox import latest_full_calendar_month_lockbox, windows_overlap
from tradingbotsuite.v2.config.schemas import RESEARCH_BOUNDARY, V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import ensure_utc, utc_isoformat
from tradingbotsuite.v2.data_quality.reports import CoverageManifestStore
from tradingbotsuite.v2.data_quality.schemas import CoverageReport
from tradingbotsuite.v2.feature_store import FeatureStoreCatalogService
from tradingbotsuite.v2.strategy_specs import parse_strategy_spec
from tradingbotsuite.v2.strategy_specs.registry import PriceBasis

CENTRAL_COLLECTION_LEDGER = (
    "data/research/central_market_history/manifests/"
    "wpr106-544-central-market-history-exhaustive-coverage-v2-collection_ledger-ef0cfdcda209.json"
)

BAR_FIELDS = frozenset(
    {
        "ts",
        "instrument_id",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "trade_count",
        "coverage_ratio",
    }
)
FIELD_FAMILY_CANDIDATES: dict[str, tuple[str, ...]] = {
    "ts": ("bars",),
    "instrument_id": ("bars",),
    "open": ("bars",),
    "high": ("bars",),
    "low": ("bars",),
    "close": ("bars",),
    "volume": ("bars",),
    "trade_count": ("bars", "orderflow"),
    "coverage_ratio": ("coverage",),
    "funding": ("bars", "funding", "derivatives_context"),
    "funding_rate": ("bars", "funding", "derivatives_context"),
    "open_interest": ("bars", "open_interest", "derivatives_context"),
    "mark_price": ("bars", "mark_price", "kline_context"),
    "oracle_price": ("bars", "mark_price", "kline_context"),
    "spread": ("bars", "bbo_spread"),
}
FEATURE_FAMILIES = frozenset(
    {
        "funding",
        "orderflow",
        "bbo_spread",
        "l2_depth",
        "derivatives_context",
        "kline_context",
        "open_interest",
        "mark_price",
        "derived_bar_context",
    }
)
LARGE_SWEEP_INSTRUMENT_THRESHOLD = 10


class ArchiveInventoryError(ValueError):
    """Raised when inventory or resolver input is invalid."""


class ArchiveInventoryService:
    """Build deterministic inventory records from existing local evidence."""

    def __init__(
        self,
        *,
        repo_root: str | Path = ".",
        archive_root: str | Path = "data/research/central_market_history",
        collection_ledger_path: str | Path | None = None,
        feature_catalog_service: FeatureStoreCatalogService | None = None,
    ) -> None:
        self.repo_root = Path(repo_root)
        self.archive_root = Path(archive_root)
        self.collection_ledger_path = (
            Path(collection_ledger_path)
            if collection_ledger_path is not None
            else self.repo_root / CENTRAL_COLLECTION_LEDGER
        )
        self.feature_catalog_service = feature_catalog_service or FeatureStoreCatalogService(
            repo_root=self.repo_root,
            archive_root=self.archive_root,
        )

    def build_inventory(self) -> ArchiveInventory:
        records: list[ArchiveInventoryRecord] = []
        records.extend(self._records_from_archive_manifests())
        records.extend(self._records_from_collection_ledger())
        records.extend(self._records_from_feature_catalog())
        records = _dedupe_records(records)
        records = sorted(
            records,
            key=lambda item: (
                item.venue,
                item.instrument_id,
                item.family,
                item.timeframe or "",
                item.start_ts or datetime.min.replace(tzinfo=UTC),
                item.end_ts or datetime.min.replace(tzinfo=UTC),
                item.usable_archive_ref,
            ),
        )
        starts = [record.start_ts for record in records if record.start_ts is not None]
        ends = [record.end_ts for record in records if record.end_ts is not None]
        payload = {
            "record_count": len(records),
            "instruments": tuple(sorted({record.instrument_id for record in records})),
            "venues": tuple(sorted({record.venue for record in records})),
            "source_families": tuple(sorted({record.family for record in records})),
            "timeframes": tuple(sorted({record.timeframe for record in records if record.timeframe})),
            "feature_families": tuple(sorted({record.family for record in records if record.family in FEATURE_FAMILIES})),
            "earliest_start_ts": min(starts) if starts else None,
            "latest_end_ts": max(ends) if ends else None,
            "total_rows": sum(record.row_count for record in records),
            "accepted_research_record_count": sum(1 for record in records if record.accepted_research_evidence_allowed),
            **dict(RESEARCH_BOUNDARY),
        }
        summary = ArchiveInventorySummary(
            **payload,
            inventory_hash=canonical_json_hash(
                {
                    "schema_version": V2_SCHEMA_VERSION,
                    "records": [record.model_dump(mode="json") for record in records],
                }
            ),
        )
        return ArchiveInventory(summary=summary, records=tuple(records))

    def query(
        self,
        *,
        symbol: str | None = None,
        instrument_id: str | None = None,
        instrument_ids: tuple[str, ...] = (),
        venue: str | None = None,
        family: str | None = None,
        timeframe: str | None = None,
        evidence_scope: str | None = None,
        coverage_report_id: str | None = None,
        accepted_only: bool = False,
        start_ts: datetime | None = None,
        end_ts: datetime | None = None,
    ) -> tuple[ArchiveInventoryRecord, ...]:
        records = self.build_inventory().records
        symbol_upper = symbol.upper() if symbol else None
        instrument_filter = tuple(dict.fromkeys((instrument_id,) if instrument_id is not None else instrument_ids))
        filtered: list[ArchiveInventoryRecord] = []
        for record in records:
            if instrument_filter and record.instrument_id not in instrument_filter:
                continue
            if symbol_upper is not None and not _record_matches_symbol(record, symbol_upper):
                continue
            if venue is not None and record.venue != venue:
                continue
            if family is not None and record.family != family:
                continue
            if timeframe is not None and record.timeframe != timeframe:
                continue
            if evidence_scope is not None and record.evidence_scope != evidence_scope:
                continue
            if accepted_only and not record.accepted_research_evidence_allowed:
                continue
            if coverage_report_id is not None and coverage_report_id not in record.coverage_report_ids:
                continue
            if start_ts is not None and record.end_ts is not None and record.end_ts <= start_ts:
                continue
            if end_ts is not None and record.start_ts is not None and record.start_ts >= end_ts:
                continue
            filtered.append(record)
        return tuple(filtered)

    def resolve_strategy_data_requirements(
        self,
        request: StrategyDataRequirementRequest | Mapping[str, Any],
        *,
        asof_date: date | None = None,
    ) -> StrategyDataRequirementReport:
        parsed_request = (
            request
            if isinstance(request, StrategyDataRequirementRequest)
            else StrategyDataRequirementRequest.model_validate(request)
        )
        spec = parse_strategy_spec(parsed_request.strategy_spec)
        evidence_mode = str(parsed_request.evidence_mode or spec.validation.evidence_mode.value)
        artifact_mode = parsed_request.artifact_mode
        inventory = self.build_inventory()
        feature_catalog = self.feature_catalog_service.build_catalog()
        blockers: list[str] = []
        gap_requests: list[DataGapRequest] = []
        usable_refs: list[str] = []
        required_materializations: list[str] = []
        recommended_collection_tasks: list[str] = []
        missing_fields: set[str] = set()
        missing_families: set[str] = set()
        missing_time_ranges: set[str] = set()

        if evidence_mode in {"accepted_research", "reported_evidence"}:
            if parsed_request.start_ts.date() < spec.validation.earliest_start:
                blockers.append(
                    f"reported_start_before_earliest:{parsed_request.start_ts.date().isoformat()}"
                )
            minimum_months = max(6, int(spec.validation.min_backtest_months))
            if _calendar_months(parsed_request.start_ts, parsed_request.end_ts) < minimum_months:
                blockers.append(f"usable_months_below_minimum:{minimum_months}")
            lockbox = latest_full_calendar_month_lockbox(asof_date=asof_date)
            if spec.validation.exclude_lockbox and windows_overlap(
                left_start=parsed_request.start_ts,
                left_end=parsed_request.end_ts,
                right_start=lockbox.start_ts,
                right_end=lockbox.end_ts,
            ):
                blockers.append(
                    "lockbox_overlap:"
                    f"{utc_isoformat(lockbox.start_ts)}..{utc_isoformat(lockbox.end_ts)}"
                )

        requested_fields = _required_fields_for_strategy(spec)
        instrument_ids = _requested_instruments(parsed_request, inventory=inventory, venue=parsed_request.venue or spec.market_scope.venue)
        recommended_lane, reference_audit_required, fast_lane_reason = _fast_lane_recommendation(
            parsed_request,
            instrument_count=len(instrument_ids),
        )
        if not instrument_ids:
            blockers.append("no_requested_or_inventory_instruments")

        usable_instruments: list[str] = []
        missing_instruments: list[str] = []
        records_by_instrument = _records_by_instrument(inventory.records)
        for instrument_id in instrument_ids:
            instrument_records = records_by_instrument.get(instrument_id, ())
            instrument_missing_fields: set[str] = set()
            instrument_missing_families: set[str] = set()
            instrument_refs: list[str] = []
            missing_refs_by_family: dict[str, list[str]] = defaultdict(list)
            missing_coverage_ids_by_family: dict[str, list[str]] = defaultdict(list)
            for field in requested_fields:
                resolution = _resolve_field(
                    field,
                    instrument_id=instrument_id,
                    records=instrument_records,
                    feature_entries=feature_catalog.entries,
                    request=parsed_request,
                    venue=parsed_request.venue or spec.market_scope.venue,
                    timeframe=spec.inputs.timeframe,
                    evidence_mode=evidence_mode,
                )
                instrument_refs.extend(resolution["usable_refs"])
                required_materializations.extend(resolution["required_materializations"])
                if not resolution["ready"]:
                    instrument_missing_fields.add(field)
                    instrument_missing_families.update(resolution["missing_families"])
                    for family in resolution["missing_families"]:
                        missing_refs_by_family[family].extend(resolution["checked_refs"])
                        missing_coverage_ids_by_family[family].extend(resolution["missing_coverage_report_ids"])
                    missing_time_ranges.add(
                        f"{instrument_id}:{field}:{utc_isoformat(parsed_request.start_ts)}..{utc_isoformat(parsed_request.end_ts)}"
                    )
            if instrument_missing_fields or instrument_missing_families:
                missing_instruments.append(instrument_id)
                missing_fields.update(instrument_missing_fields)
                missing_families.update(instrument_missing_families)
                for family in sorted(instrument_missing_families):
                    fields_for_family = tuple(
                        field for field in sorted(instrument_missing_fields)
                        if family in FIELD_FAMILY_CANDIDATES.get(field, (family,))
                    )
                    gap_requests.append(
                        _data_gap_request(
                            strategy_id=spec.strategy_id,
                            family=family,
                            fields=fields_for_family or tuple(sorted(instrument_missing_fields)),
                            instrument_ids=(instrument_id,),
                            venue=parsed_request.venue or spec.market_scope.venue,
                            start_ts=parsed_request.start_ts,
                            end_ts=parsed_request.end_ts,
                            existing_refs=tuple(dict.fromkeys(missing_refs_by_family[family])),
                            missing_coverage_report_ids=tuple(
                                dict.fromkeys(missing_coverage_ids_by_family[family])
                            ),
                            reason=_gap_reason_for_family(family),
                        )
                    )
                usable_refs.extend(instrument_refs)
            else:
                usable_instruments.append(instrument_id)
                usable_refs.extend(instrument_refs)

        if missing_families:
            for family in sorted(missing_families):
                if family in FEATURE_FAMILIES:
                    task = f"materialize_feature_family:{family}:{utc_isoformat(parsed_request.start_ts)}..{utc_isoformat(parsed_request.end_ts)}"
                    required_materializations.append(task)
                else:
                    recommended_collection_tasks.append(
                        f"bounded_gap_collection:{family}:{utc_isoformat(parsed_request.start_ts)}..{utc_isoformat(parsed_request.end_ts)}"
                    )

        if blockers and not gap_requests:
            do_not_collect_reason = ";".join(blockers)
        elif not missing_families and not missing_fields and usable_instruments:
            do_not_collect_reason = "existing_archive_refs_sufficient"
        elif set(missing_families).issubset(FEATURE_FAMILIES):
            do_not_collect_reason = "feature_materialization_required_before_collection"
        else:
            do_not_collect_reason = None

        ready = bool(usable_instruments) and not missing_fields and not missing_families and not blockers
        payload = {
            "strategy_id": spec.strategy_id,
            "spec_hash": spec.spec_hash,
            "ready": ready,
            "usable_instruments": tuple(dict.fromkeys(usable_instruments)),
            "missing_instruments": tuple(dict.fromkeys(missing_instruments)),
            "missing_fields": tuple(sorted(missing_fields)),
            "missing_families": tuple(sorted(missing_families)),
            "missing_time_ranges": tuple(sorted(missing_time_ranges)),
            "usable_archive_refs": tuple(dict.fromkeys(usable_refs)),
            "required_feature_materializations": tuple(dict.fromkeys(required_materializations)),
            "recommended_collection_tasks": tuple(dict.fromkeys(recommended_collection_tasks)),
            "do_not_collect_reason": do_not_collect_reason,
            "data_gap_requests": tuple(gap_requests),
            "archive_inventory_hash": inventory.summary.inventory_hash,
            "feature_catalog_id": feature_catalog.catalog_id,
            "recommended_engine_lane": recommended_lane,
            "reference_audit_required": reference_audit_required,
            "fast_lane_reason": fast_lane_reason,
            "artifact_mode": artifact_mode,
            "replayable_to_full_artifacts": artifact_mode in {ArtifactMode.FULL, ArtifactMode.SUMMARY, ArtifactMode.METRICS_ONLY},
            "blocker_reasons": tuple(dict.fromkeys(blockers)),
            **dict(RESEARCH_BOUNDARY),
        }
        return StrategyDataRequirementReport(
            **payload,
            requirement_report_id=canonical_json_hash(
                {
                    "schema_version": V2_SCHEMA_VERSION,
                    "strategy_id": spec.strategy_id,
                    "spec_hash": spec.spec_hash,
                    "request": parsed_request.model_dump(mode="json"),
                    "usable_instruments": payload["usable_instruments"],
                    "usable_archive_refs": payload["usable_archive_refs"],
                    "missing_fields": payload["missing_fields"],
                    "missing_families": payload["missing_families"],
                    "gap_ids": [gap.data_gap_request_id for gap in gap_requests],
                    "inventory_hash": inventory.summary.inventory_hash,
                    "feature_catalog_id": feature_catalog.catalog_id,
                    "recommended_engine_lane": recommended_lane,
                    "reference_audit_required": reference_audit_required,
                    "fast_lane_reason": fast_lane_reason,
                }
            ),
        )

    def _records_from_archive_manifests(self) -> list[ArchiveInventoryRecord]:
        archive_root = self._resolve_root(self.archive_root)
        if not archive_root.exists():
            return []
        layout = ArchiveLayout(archive_root)
        store = ArchiveManifestStore(layout)
        coverage_store = CoverageManifestStore(layout)
        try:
            files = [row for row in store.load_file_manifest() if row.layer == ArchiveLayer.SILVER]
            snapshots = store.load_archive_snapshots()
            coverage_reports = coverage_store.load_coverage_reports()
        except Exception:
            return []
        coverage_by_key: dict[tuple[str, str, str, str], list[CoverageReport]] = defaultdict(list)
        for report in coverage_reports:
            coverage_by_key[(report.venue, report.instrument_id, report.family, report.timeframe)].append(report)
        files_by_key: dict[tuple[str, str, str, str], list[FileManifestRow]] = defaultdict(list)
        for file_row in files:
            if file_row.instrument_id is None or file_row.timeframe is None:
                continue
            files_by_key[(file_row.venue, file_row.instrument_id, file_row.datatype, file_row.timeframe)].append(file_row)
        records: list[ArchiveInventoryRecord] = []
        for key, key_files in files_by_key.items():
            venue, instrument_id, family, timeframe = key
            reports = coverage_by_key.get(key, [])
            if reports:
                for report in reports:
                    records.append(
                        self._record_from_manifest_group(
                            layout=layout,
                            key_files=key_files,
                            coverage_report=report,
                            snapshots=snapshots,
                        )
                    )
            else:
                records.append(
                    self._record_from_manifest_group(
                        layout=layout,
                        key_files=key_files,
                        coverage_report=None,
                        snapshots=snapshots,
                    )
                )
        return records

    def _record_from_manifest_group(
        self,
        *,
        layout: ArchiveLayout,
        key_files: list[FileManifestRow],
        coverage_report: CoverageReport | None,
        snapshots: list[ArchiveSnapshotRecord],
    ) -> ArchiveInventoryRecord:
        first = key_files[0]
        source_file_ids = tuple(row.file_id for row in key_files)
        row_count = sum(int(row.row_count or 0) for row in key_files)
        fields = tuple(sorted({field for row in key_files for field in _parquet_fields(layout, row)}))
        snapshot = _matching_snapshot(snapshots, source_file_ids, coverage_report=coverage_report)
        start_ts = coverage_report.start_ts if coverage_report is not None else None
        end_ts = coverage_report.end_ts if coverage_report is not None else None
        coverage_report_ids = (coverage_report.coverage_report_id,) if coverage_report is not None else ()
        accepted = bool(
            coverage_report is not None
            and coverage_report.evidence_eligible
            and coverage_report.quality_status.value == "pass"
        )
        payload = {
            "instrument_id": str(first.instrument_id),
            "venue": first.venue,
            "source_id": first.created_by_job_id,
            "family": first.datatype,
            "timeframe": first.timeframe,
            "start_ts": start_ts,
            "end_ts": end_ts,
            "row_count": row_count,
            "coverage_ratio": None if coverage_report is None else coverage_report.coverage_ratio,
            "coverage_min": None if coverage_report is None else coverage_report.coverage_min,
            "field_names": fields,
            "source_file_ids": source_file_ids,
            "archive_snapshot_id": None if snapshot is None else snapshot.archive_snapshot_id,
            "coverage_report_id": None if coverage_report is None else coverage_report.coverage_report_id,
            "coverage_report_ids": coverage_report_ids,
            "universe_snapshot_id": None,
            "evidence_scope": "accepted_research" if accepted else "archive_manifest",
            "accepted_research_evidence_allowed": accepted,
            "native_to_hyperliquid": first.venue == "hyperliquid",
            "proxy_to_hyperliquid": first.venue != "hyperliquid",
            "data_quality_status": "unknown" if coverage_report is None else coverage_report.quality_status.value,
            "known_gap_reasons": () if accepted else tuple(coverage_report.blocker_reasons) if coverage_report else ("coverage_report_missing",),
            "usable_archive_ref": f"archive://{first.venue}/{first.datatype}/{first.instrument_id}/{first.timeframe}/{','.join(source_file_ids)}",
            **dict(RESEARCH_BOUNDARY),
        }
        return ArchiveInventoryRecord(
            **payload,
            inventory_id=canonical_json_hash(
                {
                    "schema_version": V2_SCHEMA_VERSION,
                    "venue": first.venue,
                    "instrument_id": first.instrument_id,
                    "family": first.datatype,
                    "timeframe": first.timeframe,
                    "coverage_report_id": payload["coverage_report_id"],
                    "source_file_ids": source_file_ids,
                    "archive_snapshot_id": payload["archive_snapshot_id"],
                }
            ),
        )

    def _records_from_collection_ledger(self) -> list[ArchiveInventoryRecord]:
        path = self._resolve_root(self.collection_ledger_path)
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(payload, Mapping) or not isinstance(payload.get("entries"), list):
            return []
        records: list[ArchiveInventoryRecord] = []
        for entry in payload["entries"]:
            if not isinstance(entry, Mapping):
                continue
            try:
                records.append(self._record_from_collection_ledger_entry(entry, path))
            except (KeyError, TypeError, ValueError):
                continue
        return records

    def _record_from_collection_ledger_entry(
        self,
        entry: Mapping[str, Any],
        path: Path,
    ) -> ArchiveInventoryRecord:
        provider = str(entry.get("provider") or entry.get("venue") or "unknown")
        venue_symbol = str(entry.get("venue_symbol") or entry.get("normalized_symbol") or "UNKNOWN")
        family = _normalized_family(str(entry.get("family") or "unknown"))
        timeframe = None if entry.get("timeframe") is None else str(entry.get("timeframe"))
        start_ts = _month_start(entry.get("start"))
        end_ts = _month_end(entry.get("end"))
        status = str(entry.get("status") or "unknown")
        backtest_usable = bool(entry.get("backtest_usable", False))
        manifest_refs = tuple(str(ref) for ref in entry.get("manifest_refs", ()) or ())
        blockers = tuple(str(reason) for reason in entry.get("notes", ()) or ())
        if entry.get("reason"):
            blockers = (*blockers, str(entry["reason"]))
        instrument_id = f"binance:perp:{venue_symbol.upper()}" if provider == "binance_usdm" else f"{provider}:perp:{venue_symbol.upper()}"
        payload = {
            "instrument_id": instrument_id,
            "venue": provider,
            "source_id": str(entry.get("source_id") or "central_collection_ledger"),
            "family": family,
            "timeframe": timeframe,
            "start_ts": start_ts,
            "end_ts": end_ts,
            "row_count": int(entry.get("parsed_row_count") or entry.get("source_count") or 0),
            "coverage_ratio": 1.0 if backtest_usable else None,
            "coverage_min": 0.98 if backtest_usable else None,
            "field_names": _family_default_fields(family),
            "source_file_ids": manifest_refs,
            "archive_snapshot_id": None,
            "coverage_report_id": None,
            "coverage_report_ids": (),
            "universe_snapshot_id": None,
            "evidence_scope": "central_collection_ledger",
            "accepted_research_evidence_allowed": backtest_usable,
            "native_to_hyperliquid": provider == "hyperliquid",
            "proxy_to_hyperliquid": provider != "hyperliquid",
            "data_quality_status": "pass" if backtest_usable else status,
            "known_gap_reasons": blockers,
            "usable_archive_ref": f"ledger://{_relative_ref(path, self.repo_root)}#{provider}/{family}/{venue_symbol}/{timeframe or 'native'}",
            **dict(RESEARCH_BOUNDARY),
        }
        return ArchiveInventoryRecord(
            **payload,
            inventory_id=canonical_json_hash(
                {
                    "schema_version": V2_SCHEMA_VERSION,
                    "ledger": str(path),
                    "provider": provider,
                    "venue_symbol": venue_symbol,
                    "family": family,
                    "timeframe": timeframe,
                    "start": entry.get("start"),
                    "end": entry.get("end"),
                    "status": status,
                    "manifest_refs": manifest_refs,
                }
            ),
        )

    def _records_from_feature_catalog(self) -> list[ArchiveInventoryRecord]:
        try:
            catalog = self.feature_catalog_service.build_catalog()
        except Exception:
            return []
        records: list[ArchiveInventoryRecord] = []
        for entry in catalog.entries:
            payload = {
                "instrument_id": entry.instrument_id,
                "venue": entry.venue,
                "source_id": entry.source_id,
                "family": entry.feature_family,
                "timeframe": entry.timeframe,
                "start_ts": entry.start_ts,
                "end_ts": entry.end_ts,
                "row_count": entry.row_count,
                "coverage_ratio": None,
                "coverage_min": None,
                "field_names": _feature_family_fields(entry.feature_family),
                "source_file_ids": (entry.output_ref,),
                "archive_snapshot_id": None,
                "coverage_report_id": None,
                "coverage_report_ids": (),
                "universe_snapshot_id": None,
                "evidence_scope": entry.evidence_scope,
                "accepted_research_evidence_allowed": entry.accepted_research_evidence_allowed,
                "native_to_hyperliquid": False,
                "proxy_to_hyperliquid": True,
                "data_quality_status": "materialized",
                "known_gap_reasons": entry.blocker_reasons,
                "usable_archive_ref": entry.usable_archive_ref,
                **dict(RESEARCH_BOUNDARY),
            }
            records.append(
                ArchiveInventoryRecord(
                    **payload,
                    inventory_id=canonical_json_hash(
                        {
                            "schema_version": V2_SCHEMA_VERSION,
                            "feature_catalog_id": entry.feature_catalog_id,
                            "usable_archive_ref": entry.usable_archive_ref,
                        }
                    ),
                )
            )
        return records

    def _resolve_root(self, path: str | Path) -> Path:
        candidate = Path(path)
        if candidate.is_absolute():
            return candidate
        return self.repo_root / candidate


def _resolve_field(
    field: str,
    *,
    instrument_id: str,
    records: tuple[ArchiveInventoryRecord, ...],
    feature_entries: tuple[Any, ...],
    request: StrategyDataRequirementRequest,
    venue: str,
    timeframe: str,
    evidence_mode: str,
) -> dict[str, Any]:
    families = FIELD_FAMILY_CANDIDATES.get(field, (field,))
    if field == "coverage_ratio":
        candidate_records = [
            record
            for record in records
            if record.family == "bars"
            and record.timeframe == timeframe
        ]
        coverage_records = [
            record
            for record in candidate_records
            if _record_covers(record, request.start_ts, request.end_ts)
        ]
        checked_refs = tuple(record.usable_archive_ref for record in candidate_records)
        coverage_report_ids = _coverage_report_ids_from_records(candidate_records)
        return {
            "ready": bool(coverage_records),
            "usable_refs": tuple(record.usable_archive_ref for record in coverage_records),
            "checked_refs": checked_refs,
            "missing_coverage_report_ids": () if coverage_records else coverage_report_ids,
            "missing_families": () if coverage_records else ("coverage",),
            "required_materializations": (),
        }
    checked_refs_by_family: dict[str, list[str]] = defaultdict(list)
    coverage_ids_by_family: dict[str, list[str]] = defaultdict(list)
    missing_family_candidates: list[str] = []
    for family in families:
        if family in FEATURE_FAMILIES:
            candidate_entries = [
                entry
                for entry in feature_entries
                if entry.feature_family == family
                and _entry_matches_instrument(entry, instrument_id)
                and (entry.timeframe is None or entry.timeframe == timeframe)
                and _feature_entry_covers(entry, request.start_ts, request.end_ts)
            ]
            checked_refs_by_family[family].extend(entry.usable_archive_ref for entry in candidate_entries)
            matches = [
                entry
                for entry in candidate_entries
                if _feature_entry_allowed_for_evidence(entry, evidence_mode)
            ]
            if matches:
                return {
                    "ready": True,
                    "usable_refs": tuple(entry.usable_archive_ref for entry in matches),
                    "checked_refs": tuple(entry.usable_archive_ref for entry in candidate_entries),
                    "missing_coverage_report_ids": (),
                    "missing_families": (),
                    "required_materializations": (),
                }
            missing_family_candidates.append(family)
            continue
        candidate_records = [
            record
            for record in records
            if record.family == family
            and (record.venue == venue or record.proxy_to_hyperliquid)
            and (record.timeframe is None or record.timeframe == timeframe)
        ]
        checked_refs_by_family[family].extend(record.usable_archive_ref for record in candidate_records)
        coverage_ids_by_family[family].extend(_coverage_report_ids_from_records(candidate_records))
        family_default_fields = _family_default_fields(family)
        family_declares_field = field in family_default_fields
        family_observed_field = any(field in record.field_names for record in candidate_records)
        matches = [
            record
            for record in candidate_records
            if (field in record.field_names or family_declares_field)
            and _record_covers(record, request.start_ts, request.end_ts)
            and (
                evidence_mode == "sandbox_diagnostic"
                or record.accepted_research_evidence_allowed
                or record.evidence_scope == "central_collection_ledger"
            )
        ]
        if matches:
            return {
                "ready": True,
                "usable_refs": tuple(record.usable_archive_ref for record in matches),
                "checked_refs": tuple(record.usable_archive_ref for record in candidate_records),
                "missing_coverage_report_ids": (),
                "missing_families": (),
                "required_materializations": (),
            }
        if family_declares_field or family_observed_field:
            missing_family_candidates.append(family)
    missing_families = tuple(dict.fromkeys(missing_family_candidates or families))
    checked_refs = tuple(
        dict.fromkeys(
            ref
            for family in missing_families
            for ref in checked_refs_by_family.get(family, ())
        )
    )
    missing_coverage_report_ids = tuple(
        dict.fromkeys(
            coverage_id
            for family in missing_families
            for coverage_id in coverage_ids_by_family.get(family, ())
        )
    )
    return {
        "ready": False,
        "usable_refs": (),
        "checked_refs": checked_refs,
        "missing_coverage_report_ids": missing_coverage_report_ids,
        "missing_families": missing_families,
        "required_materializations": tuple(
            f"materialize_feature_family:{family}" for family in missing_families if family in FEATURE_FAMILIES
        ),
    }


def _required_fields_for_strategy(spec: Any) -> tuple[str, ...]:
    fields: list[str] = ["ts", "instrument_id"]
    fields.extend(str(field) for field in spec.inputs.fields)
    price_basis = spec.execution.price_basis
    price_basis_value = price_basis.value if isinstance(price_basis, PriceBasis) else str(price_basis)
    if price_basis_value == PriceBasis.NEXT_BAR_OPEN.value:
        fields.extend(["open", "close"])
    elif price_basis_value == PriceBasis.CLOSE.value:
        fields.append("close")
    elif price_basis_value == PriceBasis.MARK.value:
        fields.append("mark_price")
    elif price_basis_value == PriceBasis.ORACLE.value:
        fields.append("oracle_price")
    fields.append("volume")
    if "max_spread" in spec.logic.filters:
        fields.append("spread")
    return tuple(dict.fromkeys(fields))


def _requested_instruments(
    request: StrategyDataRequirementRequest,
    *,
    inventory: ArchiveInventory,
    venue: str,
) -> tuple[str, ...]:
    if request.instrument_ids:
        return request.instrument_ids
    candidates = [
        record.instrument_id
        for record in inventory.records
        if record.venue == venue and record.family == "bars"
    ]
    if candidates:
        return tuple(dict.fromkeys(candidates))
    return tuple(dict.fromkeys(record.instrument_id for record in inventory.records if record.family == "bars"))


def _fast_lane_recommendation(
    request: StrategyDataRequirementRequest,
    *,
    instrument_count: int,
) -> tuple[str, bool, str | None]:
    reasons: list[str] = []
    if request.prefer_fast_lane:
        reasons.append("prefer_fast_lane_requested")
    if instrument_count >= LARGE_SWEEP_INSTRUMENT_THRESHOLD:
        reasons.append(f"large_sweep_instrument_count>={LARGE_SWEEP_INSTRUMENT_THRESHOLD}")
    if reasons:
        return "fast_vectorized", True, ";".join(reasons)
    if request.require_reference_audit:
        return "vectorized", True, "reference_audit_requested"
    return "vectorized", False, None


def _data_gap_request(
    *,
    strategy_id: str,
    family: str,
    fields: tuple[str, ...],
    instrument_ids: tuple[str, ...],
    venue: str,
    start_ts: datetime,
    end_ts: datetime,
    existing_refs: tuple[str, ...],
    reason: str,
    missing_coverage_report_ids: tuple[str, ...] = (),
) -> DataGapRequest:
    suggested_collector = None
    venue_probe_allowed = False
    if family not in FEATURE_FAMILIES and family != "coverage":
        suggested_collector = f"research_only_{family}_gap_collector_template"
        venue_probe_allowed = True
    proof_refs = existing_refs
    if venue_probe_allowed and not proof_refs and not missing_coverage_report_ids:
        proof_refs = (
            "archive_inventory://checked/no_usable_refs"
            f"?family={family}&venue={venue}&instruments={','.join(instrument_ids)}",
        )
    payload = {
        "strategy_id": strategy_id,
        "requested_family": family,
        "requested_fields": fields,
        "instrument_ids": instrument_ids,
        "venue_preference": (venue,),
        "start_ts": start_ts,
        "end_ts": end_ts,
        "reason": reason,
        "existing_archive_refs_checked": proof_refs,
        "missing_coverage_report_ids": missing_coverage_report_ids,
        "suggested_collector": suggested_collector,
        "estimated_size_bytes": None,
        "priority": "normal",
        "venue_probe_allowed": venue_probe_allowed,
        **dict(RESEARCH_BOUNDARY),
    }
    return DataGapRequest(
        **payload,
        data_gap_request_id=canonical_json_hash(
            {
                "schema_version": V2_SCHEMA_VERSION,
                "strategy_id": strategy_id,
                "family": family,
                "fields": fields,
                "instrument_ids": instrument_ids,
                "venue": venue,
                "start_ts": utc_isoformat(start_ts),
                "end_ts": utc_isoformat(end_ts),
                "reason": reason,
            }
        ),
    )


def _gap_reason_for_family(family: str) -> str:
    if family in FEATURE_FAMILIES:
        return "existing_raw_or_feature_archive_refs_do_not_cover_requested_window"
    if family == "coverage":
        return "coverage_report_missing_or_incomplete_for_requested_window"
    return "archive_inventory_has_no_usable_family_window_for_strategy"


def _records_by_instrument(records: Iterable[ArchiveInventoryRecord]) -> dict[str, tuple[ArchiveInventoryRecord, ...]]:
    grouped: dict[str, list[ArchiveInventoryRecord]] = defaultdict(list)
    for record in records:
        grouped[record.instrument_id].append(record)
    return {key: tuple(value) for key, value in grouped.items()}


def _record_covers(record: ArchiveInventoryRecord, start_ts: datetime, end_ts: datetime) -> bool:
    if record.start_ts is None or record.end_ts is None:
        return False
    if record.start_ts > start_ts or record.end_ts < end_ts:
        return False
    if record.coverage_ratio is not None and record.coverage_min is not None:
        return record.coverage_ratio >= record.coverage_min
    return True


def _coverage_report_ids_from_records(records: Iterable[ArchiveInventoryRecord]) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            coverage_report_id
            for record in records
            for coverage_report_id in record.coverage_report_ids
            if coverage_report_id
        )
    )


def _feature_entry_covers(entry: Any, start_ts: datetime, end_ts: datetime) -> bool:
    if entry.start_ts is None or entry.end_ts is None:
        return False
    return entry.start_ts <= start_ts and entry.end_ts >= end_ts


def _feature_entry_allowed_for_evidence(entry: Any, evidence_mode: str) -> bool:
    if evidence_mode == "sandbox_diagnostic":
        return True
    return bool(entry.accepted_research_evidence_allowed)


def _entry_matches_instrument(entry: Any, instrument_id: str) -> bool:
    if entry.instrument_id == instrument_id:
        return True
    return _symbol_from_instrument(entry.instrument_id) == _symbol_from_instrument(instrument_id)


def _record_matches_symbol(record: ArchiveInventoryRecord, symbol: str) -> bool:
    return _symbol_from_instrument(record.instrument_id) == symbol or symbol in record.usable_archive_ref.upper()


def _symbol_from_instrument(instrument_id: str) -> str:
    tail = instrument_id.split(":")[-1].upper()
    return tail.removesuffix("USDT")


def _parquet_fields(layout: ArchiveLayout, row: FileManifestRow) -> tuple[str, ...]:
    try:
        path = layout.resolve(row.path)
        if not path.exists():
            return ()
        return tuple(pq.ParquetFile(path).schema.names)
    except Exception:
        return ()


def _matching_snapshot(
    snapshots: list[ArchiveSnapshotRecord],
    source_file_ids: tuple[str, ...],
    *,
    coverage_report: CoverageReport | None,
) -> ArchiveSnapshotRecord | None:
    source_set = set(source_file_ids)
    matches = [
        snapshot
        for snapshot in snapshots
        if source_set.issubset(set(snapshot.included_file_ids))
        and (coverage_report is None or (
            ensure_utc(snapshot.start_ts) <= ensure_utc(coverage_report.start_ts)
            and ensure_utc(snapshot.end_ts) >= ensure_utc(coverage_report.end_ts)
        ))
    ]
    if not matches:
        return None
    return sorted(matches, key=lambda item: (item.created_at, item.archive_snapshot_id), reverse=True)[0]


def _dedupe_records(records: Iterable[ArchiveInventoryRecord]) -> list[ArchiveInventoryRecord]:
    by_id: dict[str, ArchiveInventoryRecord] = {}
    for record in records:
        by_id[record.inventory_id] = record
    return list(by_id.values())


def _normalized_family(value: str) -> str:
    normalized = value.strip()
    if normalized in {"ohlcv", "klines", "candles"}:
        return "bars"
    if normalized == "aggTrades":
        return "orderflow"
    if normalized == "bookTicker":
        return "bbo_spread"
    if normalized == "bookDepth":
        return "l2_depth"
    if normalized == "metrics":
        return "derivatives_context"
    if normalized in {"markPriceKlines", "indexPriceKlines", "premiumIndexKlines"}:
        return "kline_context"
    return normalized


def _family_default_fields(family: str) -> tuple[str, ...]:
    if family == "bars":
        return ("ts", "instrument_id", "open", "high", "low", "close", "volume", "trade_count")
    if family in {"funding", "derivatives_context"}:
        return ("ts", "instrument_id", "funding", "funding_rate", "open_interest")
    if family == "open_interest":
        return ("ts", "instrument_id", "open_interest")
    if family == "mark_price":
        return ("ts", "instrument_id", "mark_price", "oracle_price")
    if family == "bbo_spread":
        return ("ts", "instrument_id", "spread")
    if family == "orderflow":
        return ("ts", "instrument_id", "trade_count")
    if family == "kline_context":
        return ("ts", "instrument_id", "mark_price", "oracle_price")
    if family == "coverage":
        return ("coverage_ratio",)
    if family == "derived_bar_context":
        return ("ts", "instrument_id", "open", "high", "low", "close", "volume", "trade_count")
    return ()


def _feature_family_fields(family: str) -> tuple[str, ...]:
    return _family_default_fields(family)


def _month_start(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value)
    try:
        if len(text) == 7:
            return datetime.fromisoformat(text + "-01").replace(tzinfo=UTC)
        return ensure_utc(datetime.fromisoformat(text.replace("Z", "+00:00")))
    except ValueError:
        return None


def _month_end(value: Any) -> datetime | None:
    start = _month_start(value)
    if start is None:
        return None
    month_index = start.year * 12 + start.month
    year = month_index // 12
    month = (month_index % 12) + 1
    return start.replace(year=year, month=month, day=1)


def _calendar_months(start_ts: datetime, end_ts: datetime) -> int:
    return max(0, (end_ts.year - start_ts.year) * 12 + (end_ts.month - start_ts.month))


def _relative_ref(path: Path, root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(root.resolve(strict=False)).as_posix()
    except ValueError:
        return str(path.resolve(strict=False))
