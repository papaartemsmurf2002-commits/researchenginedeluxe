# V2-AUDIT-ID: V2-AUD-DATASRC-044
# V2-CONTRACTS: docs/contracts/gold_research_panel_contract.md
# V2-BOUNDARY: research_only, no_archive_writes, no_gold_panel_rows
# V2-OWNER: v2_data_sources
"""Gold research panel manifest helpers for v2 market-data research."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbotsuite.v2.archive.hashing import canonical_json_hash, file_sha256, manifest_rows_hash
from tradingbotsuite.v2.archive.layout import ArchiveLayout, safe_partition_value
from tradingbotsuite.v2.archive.manifest_store import ArchiveManifestStore
from tradingbotsuite.v2.archive.parquet_writer import write_parquet_rows
from tradingbotsuite.v2.archive.schemas import ArchiveLayer
from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import utc_now
from tradingbotsuite.v2.data_sources.coverage_gates import DataFamilyCoverageGateResult
from tradingbotsuite.v2.data_sources.schemas import ALLOWED_DATA_FAMILIES, CoverageLabel
from tradingbotsuite.v2.security.boundary import require_research_boundary


GoldPanelValue = int | float | str | bool | None


class GoldResearchPanelFeatureRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    ref_type: str = "gold_research_panel_feature_ref"
    column_name: str = Field(min_length=1)
    family: str = Field(min_length=1)
    feature_report_id: str = Field(min_length=1)
    source_registry_ref: str = Field(min_length=1)
    symbol_map_ref: str = Field(min_length=1)
    source_ids: tuple[str, ...] = Field(min_length=1)
    venue: str | None = None
    venue_symbol: str | None = None
    coverage_label: CoverageLabel
    row_count: int = Field(ge=0)
    row_manifest_hash: str = Field(min_length=64, max_length=64)
    nullable: bool = False
    coverage_flag_column: str = Field(min_length=1)
    blocker_reasons: tuple[str, ...] = ()
    native_to_hyperliquid: bool = False
    accepted_historical_coverage_proof: bool = False
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

    @model_validator(mode="after")
    def _validate_feature_ref(self) -> "GoldResearchPanelFeatureRef":
        require_research_boundary(self, context="gold research panel feature ref")
        if self.ref_type != "gold_research_panel_feature_ref":
            raise ValueError("ref_type must be gold_research_panel_feature_ref")
        if self.family not in ALLOWED_DATA_FAMILIES:
            raise ValueError(f"unknown feature family: {self.family}")
        if self.native_to_hyperliquid and self.coverage_label != CoverageLabel.NATIVE_HYPERLIQUID:
            raise ValueError("native feature refs require native_hyperliquid label")
        if not self.native_to_hyperliquid and self.coverage_label == CoverageLabel.NATIVE_HYPERLIQUID:
            raise ValueError("external feature refs cannot use native_hyperliquid label")
        if self.row_count == 0 and not self.blocker_reasons:
            raise ValueError("empty feature refs require blocker reasons")
        if self.accepted_historical_coverage_proof:
            raise ValueError("gold panel feature refs are not accepted coverage proof")
        return self


class GoldResearchPanelManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    manifest_type: str = "gold_research_panel_manifest"
    panel_id: str = Field(min_length=64, max_length=64)
    panel_name: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    interval: str = Field(min_length=1)
    universe_snapshot_ref: str = Field(min_length=1)
    source_registry_ref: str = Field(min_length=1)
    symbol_map_ref: str = Field(min_length=1)
    archive_snapshot_ref: str | None = None
    coverage_gate_id: str = Field(min_length=64, max_length=64)
    coverage_gate_passed: bool = False
    required_families: tuple[str, ...] = Field(min_length=1)
    coverage_report_ids: tuple[str, ...] = ()
    accepted_family_report_ids: dict[str, str] = Field(default_factory=dict)
    feature_refs: tuple[GoldResearchPanelFeatureRef, ...] = ()
    feature_count: int = Field(ge=0)
    minimum_feature_row_count: int = Field(ge=0)
    feature_ref_manifest_hash: str = Field(min_length=64, max_length=64)
    coverage_flags: dict[str, bool] = Field(default_factory=dict)
    missing_feature_families: tuple[str, ...] = ()
    uncovered_feature_families: tuple[str, ...] = ()
    blocker_reasons: tuple[str, ...] = ()
    panel_ready: bool = False
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
    accepted_historical_coverage_proof: bool = False
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

    @model_validator(mode="after")
    def _validate_manifest(self) -> "GoldResearchPanelManifest":
        require_research_boundary(self, context="gold research panel manifest")
        if self.manifest_type != "gold_research_panel_manifest":
            raise ValueError("manifest_type must be gold_research_panel_manifest")
        if tuple(sorted(set(self.required_families))) != self.required_families:
            raise ValueError("required_families must be sorted and unique")
        unknown_families = sorted(set(self.required_families) - ALLOWED_DATA_FAMILIES)
        if unknown_families:
            raise ValueError("unknown required families: " + ",".join(unknown_families))
        if self.feature_count != len(self.feature_refs):
            raise ValueError("feature_count must match feature_refs length")
        column_names = [ref.column_name for ref in self.feature_refs]
        if len(set(column_names)) != len(column_names):
            raise ValueError("feature_refs must use unique column_name values")
        if self.minimum_feature_row_count != _minimum_feature_row_count(self.feature_refs):
            raise ValueError("minimum_feature_row_count must match feature refs")
        if self.feature_ref_manifest_hash != gold_research_panel_feature_refs_hash(self.feature_refs):
            raise ValueError("feature_ref_manifest_hash does not match feature refs")
        if set(self.coverage_flags) != set(self.required_families):
            raise ValueError("coverage_flags must contain every required family only")
        required = set(self.required_families)
        for ref in self.feature_refs:
            if ref.source_registry_ref != self.source_registry_ref:
                raise ValueError("feature ref source_registry_ref mismatch")
            if ref.symbol_map_ref != self.symbol_map_ref:
                raise ValueError("feature ref symbol_map_ref mismatch")
            if ref.family not in required and ref.family not in self.uncovered_feature_families:
                raise ValueError("feature ref family is not covered by the gate")
        if self.panel_ready:
            if not self.coverage_gate_passed:
                raise ValueError("ready gold panels require a passed coverage gate")
            if self.archive_snapshot_ref is None:
                raise ValueError("ready gold panels require archive_snapshot_ref")
            if not self.coverage_report_ids:
                raise ValueError("ready gold panels require coverage report refs")
            if not self.feature_refs:
                raise ValueError("ready gold panels require feature refs")
            if self.blocker_reasons:
                raise ValueError("ready gold panels cannot carry blocker reasons")
            if self.missing_feature_families or self.uncovered_feature_families:
                raise ValueError("ready gold panels cannot carry missing or uncovered families")
            if not all(self.coverage_flags.values()):
                raise ValueError("ready gold panels require true coverage flags")
            if set(self.accepted_family_report_ids) != required:
                raise ValueError("ready gold panels require accepted reports for every family")
            if any(ref.blocker_reasons or ref.row_count == 0 for ref in self.feature_refs):
                raise ValueError("ready gold panels cannot reference blocked or empty features")
        elif not self.blocker_reasons:
            raise ValueError("blocked gold panel manifests require blocker reasons")
        if self.accepted_historical_coverage_proof:
            raise ValueError("gold panel manifests are not accepted historical coverage proof")
        expected_id = gold_research_panel_manifest_id_for(
            panel_name=self.panel_name,
            symbol=self.symbol,
            interval=self.interval,
            universe_snapshot_ref=self.universe_snapshot_ref,
            source_registry_ref=self.source_registry_ref,
            symbol_map_ref=self.symbol_map_ref,
            archive_snapshot_ref=self.archive_snapshot_ref,
            coverage_gate_id=self.coverage_gate_id,
            coverage_gate_passed=self.coverage_gate_passed,
            required_families=self.required_families,
            coverage_report_ids=self.coverage_report_ids,
            accepted_family_report_ids=self.accepted_family_report_ids,
            feature_count=self.feature_count,
            minimum_feature_row_count=self.minimum_feature_row_count,
            feature_ref_manifest_hash=self.feature_ref_manifest_hash,
            coverage_flags=self.coverage_flags,
            missing_feature_families=self.missing_feature_families,
            uncovered_feature_families=self.uncovered_feature_families,
            blocker_reasons=self.blocker_reasons,
            panel_ready=self.panel_ready,
        )
        if self.panel_id != expected_id:
            raise ValueError("panel_id does not match gold research panel manifest")
        return self


class GoldResearchPanelInputValue(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    value_type: str = "gold_research_panel_input_value"
    column_name: str = Field(min_length=1)
    family: str = Field(min_length=1)
    feature_report_id: str = Field(min_length=1)
    timestamp_ms: int = Field(ge=0)
    value: GoldPanelValue = None
    source_row_hash: str | None = Field(default=None, min_length=64, max_length=64)
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

    @model_validator(mode="after")
    def _validate_input_value(self) -> "GoldResearchPanelInputValue":
        require_research_boundary(self, context="gold research panel input value")
        if self.value_type != "gold_research_panel_input_value":
            raise ValueError("value_type must be gold_research_panel_input_value")
        if self.family not in ALLOWED_DATA_FAMILIES:
            raise ValueError(f"unknown input family: {self.family}")
        return self


class GoldResearchPanelRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    row_type: str = "gold_research_panel_row"
    panel_id: str = Field(min_length=64, max_length=64)
    symbol: str = Field(min_length=1)
    interval: str = Field(min_length=1)
    timestamp_ms: int = Field(ge=0)
    values: dict[str, GoldPanelValue] = Field(default_factory=dict)
    coverage_flags: dict[str, bool] = Field(default_factory=dict)
    source_row_hashes: tuple[str, ...] = ()
    row_hash: str = Field(min_length=64, max_length=64)
    accepted_historical_coverage_proof: bool = False
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

    @model_validator(mode="after")
    def _validate_row(self) -> "GoldResearchPanelRow":
        require_research_boundary(self, context="gold research panel row")
        if self.row_type != "gold_research_panel_row":
            raise ValueError("row_type must be gold_research_panel_row")
        if not self.values:
            raise ValueError("gold research panel rows require values")
        if not self.coverage_flags:
            raise ValueError("gold research panel rows require coverage flags")
        if self.accepted_historical_coverage_proof:
            raise ValueError("gold panel rows are not accepted coverage proof")
        if self.row_hash != gold_research_panel_row_hash(self):
            raise ValueError("row_hash does not match gold research panel row")
        return self


class GoldResearchPanelAssemblyResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    result_type: str = "gold_research_panel_assembly_result"
    assembly_id: str = Field(min_length=64, max_length=64)
    panel_id: str = Field(min_length=64, max_length=64)
    panel_name: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    interval: str = Field(min_length=1)
    panel_manifest_ready: bool = False
    feature_columns: tuple[str, ...] = ()
    input_value_count: int = Field(ge=0)
    rows: tuple[GoldResearchPanelRow, ...] = ()
    row_count: int = Field(ge=0)
    row_manifest_hash: str = Field(min_length=64, max_length=64)
    blocker_reasons: tuple[str, ...] = ()
    assembly_ready: bool = False
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
    accepted_historical_coverage_proof: bool = False
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

    @model_validator(mode="after")
    def _validate_result(self) -> "GoldResearchPanelAssemblyResult":
        require_research_boundary(self, context="gold research panel assembly result")
        if self.result_type != "gold_research_panel_assembly_result":
            raise ValueError("result_type must be gold_research_panel_assembly_result")
        if tuple(sorted(set(self.feature_columns))) != self.feature_columns:
            raise ValueError("feature_columns must be sorted and unique")
        if self.row_count != len(self.rows):
            raise ValueError("row_count must match rows length")
        if self.row_manifest_hash != gold_research_panel_rows_hash(self.rows):
            raise ValueError("row_manifest_hash does not match rows")
        if self.assembly_ready:
            if not self.panel_manifest_ready:
                raise ValueError("ready assembly requires a ready panel manifest")
            if not self.feature_columns:
                raise ValueError("ready assembly requires feature columns")
            if not self.rows:
                raise ValueError("ready assembly requires rows")
            if self.blocker_reasons:
                raise ValueError("ready assembly cannot carry blocker reasons")
        elif not self.blocker_reasons:
            raise ValueError("blocked assembly results require blocker reasons")
        if self.accepted_historical_coverage_proof:
            raise ValueError("gold panel assembly results are not accepted coverage proof")
        expected_id = gold_research_panel_assembly_id_for(
            panel_id=self.panel_id,
            panel_name=self.panel_name,
            symbol=self.symbol,
            interval=self.interval,
            panel_manifest_ready=self.panel_manifest_ready,
            feature_columns=self.feature_columns,
            input_value_count=self.input_value_count,
            row_count=self.row_count,
            row_manifest_hash=self.row_manifest_hash,
            blocker_reasons=self.blocker_reasons,
            assembly_ready=self.assembly_ready,
        )
        if self.assembly_id != expected_id:
            raise ValueError("assembly_id does not match gold panel assembly result")
        return self


class GoldResearchPanelWriteResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    result_type: str = "gold_research_panel_write_result"
    write_id: str = Field(min_length=64, max_length=64)
    panel_id: str = Field(min_length=64, max_length=64)
    assembly_id: str = Field(min_length=64, max_length=64)
    job_id: str = Field(min_length=1)
    dataset: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    date: str = Field(min_length=10)
    timeframe: str = Field(min_length=1)
    gold_panel_ref: str = Field(min_length=1)
    gold_panel_file_id: str = Field(min_length=64, max_length=64)
    gold_panel_sha256: str = Field(min_length=64, max_length=64)
    assembly_manifest_ref: str = Field(min_length=1)
    assembly_manifest_sha256: str = Field(min_length=64, max_length=64)
    row_count: int = Field(gt=0)
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
    accepted_historical_coverage_proof: bool = False
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

    @model_validator(mode="after")
    def _validate_write_result(self) -> "GoldResearchPanelWriteResult":
        require_research_boundary(self, context="gold research panel write result")
        if self.result_type != "gold_research_panel_write_result":
            raise ValueError("result_type must be gold_research_panel_write_result")
        if self.accepted_historical_coverage_proof:
            raise ValueError("gold panel write results are not accepted coverage proof")
        expected_id = gold_research_panel_write_id_for(
            panel_id=self.panel_id,
            assembly_id=self.assembly_id,
            job_id=self.job_id,
            dataset=self.dataset,
            venue=self.venue,
            date=self.date,
            timeframe=self.timeframe,
            gold_panel_ref=self.gold_panel_ref,
            gold_panel_file_id=self.gold_panel_file_id,
            gold_panel_sha256=self.gold_panel_sha256,
            assembly_manifest_ref=self.assembly_manifest_ref,
            assembly_manifest_sha256=self.assembly_manifest_sha256,
            row_count=self.row_count,
        )
        if self.write_id != expected_id:
            raise ValueError("write_id does not match gold panel write result")
        return self


def build_gold_research_panel_manifest(
    *,
    coverage_gate: DataFamilyCoverageGateResult | Mapping[str, Any],
    feature_refs: Iterable[GoldResearchPanelFeatureRef | Mapping[str, Any]],
    panel_name: str,
    interval: str,
    symbol: str | None = None,
) -> GoldResearchPanelManifest:
    gate = (
        coverage_gate
        if isinstance(coverage_gate, DataFamilyCoverageGateResult)
        else DataFamilyCoverageGateResult.model_validate(dict(coverage_gate))
    )
    panel_symbol = symbol or gate.symbol
    if panel_symbol != gate.symbol:
        raise ValueError("panel symbol must match coverage gate symbol")
    refs = tuple(
        ref
        if isinstance(ref, GoldResearchPanelFeatureRef)
        else GoldResearchPanelFeatureRef.model_validate(dict(ref))
        for ref in feature_refs
    )
    _validate_feature_refs_match_gate(refs=refs, gate=gate)
    feature_families = set(ref.family for ref in refs)
    required_families = set(gate.required_families)
    missing_feature_families = tuple(
        family for family in gate.required_families if family not in feature_families
    )
    uncovered_feature_families = tuple(sorted(feature_families - required_families))
    blocker_reasons: list[str] = []
    if not gate.passed:
        blocker_reasons.append("coverage_gate_not_passed")
    if gate.archive_snapshot_ref is None:
        blocker_reasons.append("missing_archive_snapshot_ref")
    if not refs:
        blocker_reasons.append("empty_feature_refs")
    if missing_feature_families:
        blocker_reasons.append("missing_required_feature_family")
    if uncovered_feature_families:
        blocker_reasons.append("feature_family_not_covered_by_gate")
    if any(ref.blocker_reasons for ref in refs):
        blocker_reasons.append("blocked_feature_ref")
    if any(ref.row_count == 0 for ref in refs):
        blocker_reasons.append("empty_feature_ref")
    coverage_flags = {
        family: (
            gate.passed
            and family in gate.accepted_family_report_ids
            and family in feature_families
        )
        for family in gate.required_families
    }
    return _gold_research_panel_manifest(
        panel_name=panel_name,
        symbol=panel_symbol,
        interval=interval,
        gate=gate,
        feature_refs=refs,
        coverage_flags=coverage_flags,
        missing_feature_families=missing_feature_families,
        uncovered_feature_families=uncovered_feature_families,
        blocker_reasons=tuple(blocker_reasons),
        panel_ready=not blocker_reasons,
    )


def assemble_gold_research_panel_rows(
    *,
    manifest: GoldResearchPanelManifest | Mapping[str, Any],
    input_values: Iterable[GoldResearchPanelInputValue | Mapping[str, Any]],
) -> GoldResearchPanelAssemblyResult:
    panel_manifest = (
        manifest
        if isinstance(manifest, GoldResearchPanelManifest)
        else GoldResearchPanelManifest.model_validate(dict(manifest))
    )
    values = tuple(
        value
        if isinstance(value, GoldResearchPanelInputValue)
        else GoldResearchPanelInputValue.model_validate(dict(value))
        for value in input_values
    )
    feature_refs = tuple(sorted(panel_manifest.feature_refs, key=lambda item: item.column_name))
    refs_by_column = {ref.column_name: ref for ref in feature_refs}
    blockers: list[str] = []
    if not panel_manifest.panel_ready:
        _append_blocker(blockers, "panel_manifest_not_ready")
    if not values:
        _append_blocker(blockers, "empty_feature_values")
    values_by_key: dict[tuple[int, str], GoldResearchPanelInputValue] = {}
    duplicate_seen = False
    for value in values:
        ref = refs_by_column.get(value.column_name)
        if ref is None:
            raise ValueError("input column_name is not in panel manifest")
        if value.family != ref.family:
            raise ValueError("input family does not match feature ref")
        if value.feature_report_id != ref.feature_report_id:
            raise ValueError("input feature_report_id does not match feature ref")
        key = (value.timestamp_ms, value.column_name)
        if key in values_by_key:
            duplicate_seen = True
            continue
        values_by_key[key] = value
        if value.value is None and not ref.nullable:
            _append_blocker(blockers, "missing_required_column_value")
    if duplicate_seen:
        _append_blocker(blockers, "duplicate_column_timestamp")
    rows: list[GoldResearchPanelRow] = []
    if panel_manifest.panel_ready and not duplicate_seen:
        for timestamp_ms in sorted({value.timestamp_ms for value in values}):
            row_values: dict[str, GoldPanelValue] = {}
            source_row_hashes: list[str] = []
            missing_required = False
            for ref in feature_refs:
                value = values_by_key.get((timestamp_ms, ref.column_name))
                if value is None:
                    if ref.nullable:
                        row_values[ref.column_name] = None
                        continue
                    missing_required = True
                    continue
                row_values[ref.column_name] = value.value
                if value.source_row_hash:
                    source_row_hashes.append(value.source_row_hash)
            if missing_required:
                _append_blocker(blockers, "missing_required_column_value")
                continue
            coverage_flags = _row_coverage_flags(
                manifest=panel_manifest,
                feature_refs=feature_refs,
                row_values=row_values,
            )
            rows.append(
                _gold_research_panel_row(
                    panel_id=panel_manifest.panel_id,
                    symbol=panel_manifest.symbol,
                    interval=panel_manifest.interval,
                    timestamp_ms=timestamp_ms,
                    values=row_values,
                    coverage_flags=coverage_flags,
                    source_row_hashes=tuple(sorted(source_row_hashes)),
                )
            )
    return _gold_research_panel_assembly_result(
        manifest=panel_manifest,
        feature_columns=tuple(sorted(ref.column_name for ref in feature_refs)),
        input_value_count=len(values),
        rows=tuple(rows),
        blocker_reasons=tuple(blockers),
        assembly_ready=not blockers,
    )


def write_gold_research_panel_artifacts(
    *,
    archive_root: str | Path,
    assembly_result: GoldResearchPanelAssemblyResult | Mapping[str, Any],
    job_id: str,
    dataset: str = "feature_panels",
    venue: str = "hyperliquid",
) -> GoldResearchPanelWriteResult:
    result = (
        assembly_result
        if isinstance(assembly_result, GoldResearchPanelAssemblyResult)
        else GoldResearchPanelAssemblyResult.model_validate(dict(assembly_result))
    )
    if not result.assembly_ready:
        raise ValueError("gold panel assembly result is not ready")
    if not result.rows:
        raise ValueError("gold panel assembly result has no rows")
    layout = ArchiveLayout(archive_root)
    layout.initialize()
    store = ArchiveManifestStore(layout)
    date = _gold_panel_partition_date(result.rows[0])
    parquet_row = write_parquet_rows(
        layout=layout,
        store=store,
        rows=(_flatten_gold_panel_row(row) for row in result.rows),
        layer=ArchiveLayer.GOLD,
        dataset=safe_partition_value(dataset),
        venue=safe_partition_value(venue),
        datatype="gold_research_panel",
        date=date,
        job_id=job_id,
        source_file_ids=(result.assembly_id,),
        filename=f"panel-{result.panel_id[:16]}-{result.assembly_id[:16]}",
        timeframe=result.interval,
        snapshot_id=result.panel_id,
        instrument_id=result.symbol,
    )
    assembly_manifest_path = layout.resolve(
        "manifests",
        "gold_panels",
        f"assembly_{result.assembly_id[:16]}.json",
    )
    _write_json_model(assembly_manifest_path, result)
    assembly_manifest_ref = layout.relative_to_root(assembly_manifest_path)
    assembly_manifest_sha256 = file_sha256(assembly_manifest_path)
    write_id = gold_research_panel_write_id_for(
        panel_id=result.panel_id,
        assembly_id=result.assembly_id,
        job_id=job_id,
        dataset=dataset,
        venue=venue,
        date=date,
        timeframe=result.interval,
        gold_panel_ref=parquet_row.path,
        gold_panel_file_id=parquet_row.file_id,
        gold_panel_sha256=parquet_row.sha256,
        assembly_manifest_ref=assembly_manifest_ref,
        assembly_manifest_sha256=assembly_manifest_sha256,
        row_count=result.row_count,
    )
    return GoldResearchPanelWriteResult(
        write_id=write_id,
        panel_id=result.panel_id,
        assembly_id=result.assembly_id,
        job_id=job_id,
        dataset=dataset,
        venue=venue,
        date=date,
        timeframe=result.interval,
        gold_panel_ref=parquet_row.path,
        gold_panel_file_id=parquet_row.file_id,
        gold_panel_sha256=parquet_row.sha256,
        assembly_manifest_ref=assembly_manifest_ref,
        assembly_manifest_sha256=assembly_manifest_sha256,
        row_count=result.row_count,
    )


def gold_research_panel_feature_refs_hash(
    feature_refs: tuple[GoldResearchPanelFeatureRef, ...],
) -> str:
    return manifest_rows_hash(
        ref.model_dump(mode="json")
        for ref in sorted(feature_refs, key=lambda item: item.column_name)
    )


def gold_research_panel_row_hash(row: GoldResearchPanelRow) -> str:
    return gold_research_panel_row_hash_for(
        panel_id=row.panel_id,
        symbol=row.symbol,
        interval=row.interval,
        timestamp_ms=row.timestamp_ms,
        values=row.values,
        coverage_flags=row.coverage_flags,
        source_row_hashes=row.source_row_hashes,
    )


def gold_research_panel_row_hash_for(
    *,
    panel_id: str,
    symbol: str,
    interval: str,
    timestamp_ms: int,
    values: dict[str, GoldPanelValue],
    coverage_flags: dict[str, bool],
    source_row_hashes: tuple[str, ...],
) -> str:
    return canonical_json_hash(
        {
            "row_type": "gold_research_panel_row",
            "panel_id": panel_id,
            "symbol": symbol,
            "interval": interval,
            "timestamp_ms": timestamp_ms,
            "values": values,
            "coverage_flags": coverage_flags,
            "source_row_hashes": source_row_hashes,
        }
    )


def gold_research_panel_rows_hash(rows: tuple[GoldResearchPanelRow, ...]) -> str:
    return manifest_rows_hash(row.model_dump(mode="json") for row in rows)


def gold_research_panel_assembly_id_for(
    *,
    panel_id: str,
    panel_name: str,
    symbol: str,
    interval: str,
    panel_manifest_ready: bool,
    feature_columns: tuple[str, ...],
    input_value_count: int,
    row_count: int,
    row_manifest_hash: str,
    blocker_reasons: tuple[str, ...],
    assembly_ready: bool,
) -> str:
    return canonical_json_hash(
        {
            "result_type": "gold_research_panel_assembly_result",
            "panel_id": panel_id,
            "panel_name": panel_name,
            "symbol": symbol,
            "interval": interval,
            "panel_manifest_ready": panel_manifest_ready,
            "feature_columns": feature_columns,
            "input_value_count": input_value_count,
            "row_count": row_count,
            "row_manifest_hash": row_manifest_hash,
            "blocker_reasons": blocker_reasons,
            "assembly_ready": assembly_ready,
        }
    )


def gold_research_panel_write_id_for(
    *,
    panel_id: str,
    assembly_id: str,
    job_id: str,
    dataset: str,
    venue: str,
    date: str,
    timeframe: str,
    gold_panel_ref: str,
    gold_panel_file_id: str,
    gold_panel_sha256: str,
    assembly_manifest_ref: str,
    assembly_manifest_sha256: str,
    row_count: int,
) -> str:
    return canonical_json_hash(
        {
            "result_type": "gold_research_panel_write_result",
            "panel_id": panel_id,
            "assembly_id": assembly_id,
            "job_id": job_id,
            "dataset": dataset,
            "venue": venue,
            "date": date,
            "timeframe": timeframe,
            "gold_panel_ref": gold_panel_ref,
            "gold_panel_file_id": gold_panel_file_id,
            "gold_panel_sha256": gold_panel_sha256,
            "assembly_manifest_ref": assembly_manifest_ref,
            "assembly_manifest_sha256": assembly_manifest_sha256,
            "row_count": row_count,
        }
    )


def gold_research_panel_manifest_id_for(
    *,
    panel_name: str,
    symbol: str,
    interval: str,
    universe_snapshot_ref: str,
    source_registry_ref: str,
    symbol_map_ref: str,
    archive_snapshot_ref: str | None,
    coverage_gate_id: str,
    coverage_gate_passed: bool,
    required_families: tuple[str, ...],
    coverage_report_ids: tuple[str, ...],
    accepted_family_report_ids: dict[str, str],
    feature_count: int,
    minimum_feature_row_count: int,
    feature_ref_manifest_hash: str,
    coverage_flags: dict[str, bool],
    missing_feature_families: tuple[str, ...],
    uncovered_feature_families: tuple[str, ...],
    blocker_reasons: tuple[str, ...],
    panel_ready: bool,
) -> str:
    return canonical_json_hash(
        {
            "manifest_type": "gold_research_panel_manifest",
            "panel_name": panel_name,
            "symbol": symbol,
            "interval": interval,
            "universe_snapshot_ref": universe_snapshot_ref,
            "source_registry_ref": source_registry_ref,
            "symbol_map_ref": symbol_map_ref,
            "archive_snapshot_ref": archive_snapshot_ref,
            "coverage_gate_id": coverage_gate_id,
            "coverage_gate_passed": coverage_gate_passed,
            "required_families": required_families,
            "coverage_report_ids": coverage_report_ids,
            "accepted_family_report_ids": accepted_family_report_ids,
            "feature_count": feature_count,
            "minimum_feature_row_count": minimum_feature_row_count,
            "feature_ref_manifest_hash": feature_ref_manifest_hash,
            "coverage_flags": coverage_flags,
            "missing_feature_families": missing_feature_families,
            "uncovered_feature_families": uncovered_feature_families,
            "blocker_reasons": blocker_reasons,
            "panel_ready": panel_ready,
        }
    )


def _append_blocker(blockers: list[str], reason: str) -> None:
    if reason not in blockers:
        blockers.append(reason)


def _validate_feature_refs_match_gate(
    *,
    refs: tuple[GoldResearchPanelFeatureRef, ...],
    gate: DataFamilyCoverageGateResult,
) -> None:
    for ref in refs:
        if ref.source_registry_ref != gate.source_registry_ref:
            raise ValueError("feature ref source_registry_ref mismatch")
        if ref.symbol_map_ref != gate.symbol_map_ref:
            raise ValueError("feature ref symbol_map_ref mismatch")


def _minimum_feature_row_count(
    feature_refs: tuple[GoldResearchPanelFeatureRef, ...],
) -> int:
    if not feature_refs:
        return 0
    return min(ref.row_count for ref in feature_refs)


def _row_coverage_flags(
    *,
    manifest: GoldResearchPanelManifest,
    feature_refs: tuple[GoldResearchPanelFeatureRef, ...],
    row_values: dict[str, GoldPanelValue],
) -> dict[str, bool]:
    flags: dict[str, bool] = {}
    for family in manifest.required_families:
        family_refs = [ref for ref in feature_refs if ref.family == family]
        has_value = any(row_values.get(ref.column_name) is not None for ref in family_refs)
        flags[family] = bool(manifest.coverage_flags[family] and has_value)
    return flags


def _gold_research_panel_row(
    *,
    panel_id: str,
    symbol: str,
    interval: str,
    timestamp_ms: int,
    values: dict[str, GoldPanelValue],
    coverage_flags: dict[str, bool],
    source_row_hashes: tuple[str, ...],
) -> GoldResearchPanelRow:
    row_hash = gold_research_panel_row_hash_for(
        panel_id=panel_id,
        symbol=symbol,
        interval=interval,
        timestamp_ms=timestamp_ms,
        values=values,
        coverage_flags=coverage_flags,
        source_row_hashes=source_row_hashes,
    )
    return GoldResearchPanelRow(
        panel_id=panel_id,
        symbol=symbol,
        interval=interval,
        timestamp_ms=timestamp_ms,
        values=values,
        coverage_flags=coverage_flags,
        source_row_hashes=source_row_hashes,
        row_hash=row_hash,
    )


def _gold_research_panel_assembly_result(
    *,
    manifest: GoldResearchPanelManifest,
    feature_columns: tuple[str, ...],
    input_value_count: int,
    rows: tuple[GoldResearchPanelRow, ...],
    blocker_reasons: tuple[str, ...],
    assembly_ready: bool,
) -> GoldResearchPanelAssemblyResult:
    row_manifest_hash = gold_research_panel_rows_hash(rows)
    assembly_id = gold_research_panel_assembly_id_for(
        panel_id=manifest.panel_id,
        panel_name=manifest.panel_name,
        symbol=manifest.symbol,
        interval=manifest.interval,
        panel_manifest_ready=manifest.panel_ready,
        feature_columns=feature_columns,
        input_value_count=input_value_count,
        row_count=len(rows),
        row_manifest_hash=row_manifest_hash,
        blocker_reasons=blocker_reasons,
        assembly_ready=assembly_ready,
    )
    return GoldResearchPanelAssemblyResult(
        assembly_id=assembly_id,
        panel_id=manifest.panel_id,
        panel_name=manifest.panel_name,
        symbol=manifest.symbol,
        interval=manifest.interval,
        panel_manifest_ready=manifest.panel_ready,
        feature_columns=feature_columns,
        input_value_count=input_value_count,
        rows=rows,
        row_count=len(rows),
        row_manifest_hash=row_manifest_hash,
        blocker_reasons=blocker_reasons,
        assembly_ready=assembly_ready,
    )


def _flatten_gold_panel_row(row: GoldResearchPanelRow) -> dict[str, Any]:
    flattened: dict[str, Any] = {
        "schema_version": row.schema_version,
        "panel_id": row.panel_id,
        "symbol": row.symbol,
        "interval": row.interval,
        "timestamp_ms": row.timestamp_ms,
        "row_hash": row.row_hash,
        "source_row_hashes": list(row.source_row_hashes),
        "research_only": row.research_only,
        "observe_only": row.observe_only,
        "promotion_ready": row.promotion_ready,
        "candidate_evidence": row.candidate_evidence,
        "candidate_pack_eligible": row.candidate_pack_eligible,
        "live_signal": row.live_signal,
        "paper_signal": row.paper_signal,
        "sizing_instruction": row.sizing_instruction,
        "order_placement_instruction": row.order_placement_instruction,
        "runtime_mode_change": row.runtime_mode_change,
    }
    flattened.update(row.values)
    for family, flag in row.coverage_flags.items():
        flattened[f"coverage_flag_{family}"] = flag
    return flattened


def _gold_panel_partition_date(row: GoldResearchPanelRow) -> str:
    return datetime.fromtimestamp(row.timestamp_ms / 1000, tz=UTC).date().isoformat()


def _write_json_model(path: Path, model: BaseModel) -> None:
    if path.exists():
        raise FileExistsError(f"gold panel manifest already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(model.model_dump(mode="json"), sort_keys=True, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def _gold_research_panel_manifest(
    *,
    panel_name: str,
    symbol: str,
    interval: str,
    gate: DataFamilyCoverageGateResult,
    feature_refs: tuple[GoldResearchPanelFeatureRef, ...],
    coverage_flags: dict[str, bool],
    missing_feature_families: tuple[str, ...],
    uncovered_feature_families: tuple[str, ...],
    blocker_reasons: tuple[str, ...],
    panel_ready: bool,
) -> GoldResearchPanelManifest:
    feature_ref_manifest_hash = gold_research_panel_feature_refs_hash(feature_refs)
    feature_count = len(feature_refs)
    minimum_feature_row_count = _minimum_feature_row_count(feature_refs)
    panel_id = gold_research_panel_manifest_id_for(
        panel_name=panel_name,
        symbol=symbol,
        interval=interval,
        universe_snapshot_ref=gate.universe_snapshot_ref,
        source_registry_ref=gate.source_registry_ref,
        symbol_map_ref=gate.symbol_map_ref,
        archive_snapshot_ref=gate.archive_snapshot_ref,
        coverage_gate_id=gate.gate_id,
        coverage_gate_passed=gate.passed,
        required_families=gate.required_families,
        coverage_report_ids=gate.report_ids,
        accepted_family_report_ids=gate.accepted_family_report_ids,
        feature_count=feature_count,
        minimum_feature_row_count=minimum_feature_row_count,
        feature_ref_manifest_hash=feature_ref_manifest_hash,
        coverage_flags=coverage_flags,
        missing_feature_families=missing_feature_families,
        uncovered_feature_families=uncovered_feature_families,
        blocker_reasons=blocker_reasons,
        panel_ready=panel_ready,
    )
    return GoldResearchPanelManifest(
        panel_id=panel_id,
        panel_name=panel_name,
        symbol=symbol,
        interval=interval,
        universe_snapshot_ref=gate.universe_snapshot_ref,
        source_registry_ref=gate.source_registry_ref,
        symbol_map_ref=gate.symbol_map_ref,
        archive_snapshot_ref=gate.archive_snapshot_ref,
        coverage_gate_id=gate.gate_id,
        coverage_gate_passed=gate.passed,
        required_families=gate.required_families,
        coverage_report_ids=gate.report_ids,
        accepted_family_report_ids=gate.accepted_family_report_ids,
        feature_refs=feature_refs,
        feature_count=feature_count,
        minimum_feature_row_count=minimum_feature_row_count,
        feature_ref_manifest_hash=feature_ref_manifest_hash,
        coverage_flags=coverage_flags,
        missing_feature_families=missing_feature_families,
        uncovered_feature_families=uncovered_feature_families,
        blocker_reasons=blocker_reasons,
        panel_ready=panel_ready,
    )
