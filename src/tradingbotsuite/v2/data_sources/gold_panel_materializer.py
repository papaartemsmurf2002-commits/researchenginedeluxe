# V2-AUDIT-ID: V2-AUD-DATASRC-049
# V2-CONTRACTS: docs/contracts/gold_research_panel_contract.md
# V2-BOUNDARY: research_only, gold_panel_materializer, archive_gold_writes_only
# V2-OWNER: v2_data_sources
"""All-or-nothing materializer for ready gold research panel preflights."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbotsuite.v2.archive.hashing import canonical_json_hash, manifest_rows_hash
from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import utc_now
from tradingbotsuite.v2.data_sources.gold_panel_preflight import (
    GoldPanelPreflightResult,
    GoldPanelPreflightSymbolResult,
)
from tradingbotsuite.v2.data_sources.gold_panels import (
    GoldResearchPanelAssemblyResult,
    GoldResearchPanelInputValue,
    GoldResearchPanelWriteResult,
    assemble_gold_research_panel_rows,
    write_gold_research_panel_artifacts,
)
from tradingbotsuite.v2.security.boundary import require_research_boundary


class GoldPanelMaterializerSymbolResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    result_type: str = "gold_panel_materializer_symbol_result"
    result_id: str = Field(min_length=64, max_length=64)
    symbol: str = Field(min_length=1)
    preflight_symbol_result_id: str = Field(min_length=64, max_length=64)
    panel_id: str = Field(min_length=64, max_length=64)
    assembly_result: GoldResearchPanelAssemblyResult
    write_result: GoldResearchPanelWriteResult | None = None
    input_value_count: int = Field(ge=0)
    row_count: int = Field(ge=0)
    write_id: str | None = Field(default=None, min_length=64, max_length=64)
    gold_panel_ref: str | None = None
    assembly_manifest_ref: str | None = None
    materialized: bool = False
    blocker_reasons: tuple[str, ...] = ()
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
    def _validate_symbol_result(self) -> "GoldPanelMaterializerSymbolResult":
        require_research_boundary(self, context="gold panel materializer symbol result")
        if self.result_type != "gold_panel_materializer_symbol_result":
            raise ValueError("result_type must be gold_panel_materializer_symbol_result")
        if self.assembly_result.symbol != self.symbol:
            raise ValueError("assembly result symbol mismatch")
        if self.assembly_result.panel_id != self.panel_id:
            raise ValueError("assembly result panel_id mismatch")
        if self.input_value_count != self.assembly_result.input_value_count:
            raise ValueError("input_value_count must match assembly result")
        if self.row_count != self.assembly_result.row_count:
            raise ValueError("row_count must match assembly result")
        if self.write_result is not None:
            if self.write_result.panel_id != self.panel_id:
                raise ValueError("write result panel_id mismatch")
            if self.write_result.assembly_id != self.assembly_result.assembly_id:
                raise ValueError("write result assembly_id mismatch")
            if self.write_id != self.write_result.write_id:
                raise ValueError("write_id must match write result")
            if self.gold_panel_ref != self.write_result.gold_panel_ref:
                raise ValueError("gold_panel_ref must match write result")
            if self.assembly_manifest_ref != self.write_result.assembly_manifest_ref:
                raise ValueError("assembly_manifest_ref must match write result")
        if self.materialized:
            if self.blocker_reasons:
                raise ValueError("materialized symbols cannot carry blocker reasons")
            if self.write_result is None:
                raise ValueError("materialized symbols require a write result")
            if not self.assembly_result.assembly_ready:
                raise ValueError("materialized symbols require a ready assembly")
            if self.row_count <= 0:
                raise ValueError("materialized symbols require rows")
        else:
            if not self.blocker_reasons:
                raise ValueError("blocked materializer symbols require blocker reasons")
            if self.write_result is not None:
                raise ValueError("blocked materializer symbols cannot carry write results")
        if self.accepted_historical_coverage_proof:
            raise ValueError("gold panel materializer symbols are not accepted coverage proof")
        expected_id = gold_panel_materializer_symbol_result_id_for(
            symbol=self.symbol,
            preflight_symbol_result_id=self.preflight_symbol_result_id,
            panel_id=self.panel_id,
            assembly_id=self.assembly_result.assembly_id,
            write_id=self.write_id,
            input_value_count=self.input_value_count,
            row_count=self.row_count,
            gold_panel_ref=self.gold_panel_ref,
            assembly_manifest_ref=self.assembly_manifest_ref,
            materialized=self.materialized,
            blocker_reasons=self.blocker_reasons,
        )
        if self.result_id != expected_id:
            raise ValueError("result_id does not match gold panel materializer symbol result")
        return self


class GoldPanelMaterializerResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    result_type: str = "gold_panel_materializer_result"
    materializer_id: str = Field(min_length=64, max_length=64)
    preflight_id: str = Field(min_length=64, max_length=64)
    panel_name: str = Field(min_length=1)
    interval: str = Field(min_length=1)
    archive_root_ref: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    dataset: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    symbols: tuple[str, ...] = Field(min_length=1)
    symbol_results: tuple[GoldPanelMaterializerSymbolResult, ...] = Field(min_length=1)
    symbol_count: int = Field(ge=1)
    materialized_symbol_count: int = Field(ge=0)
    blocked_symbol_count: int = Field(ge=0)
    input_value_count: int = Field(ge=0)
    row_count: int = Field(ge=0)
    write_ids: tuple[str, ...] = ()
    gold_panel_refs: tuple[str, ...] = ()
    blocker_reasons: tuple[str, ...] = ()
    all_symbols_materialized: bool = False
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
    def _validate_result(self) -> "GoldPanelMaterializerResult":
        require_research_boundary(self, context="gold panel materializer result")
        if self.result_type != "gold_panel_materializer_result":
            raise ValueError("result_type must be gold_panel_materializer_result")
        if tuple(sorted(set(self.symbols))) != self.symbols:
            raise ValueError("symbols must be sorted and unique")
        if self.symbol_count != len(self.symbol_results):
            raise ValueError("symbol_count must match symbol_results length")
        if self.symbol_count != len(self.symbols):
            raise ValueError("symbol_count must match symbols length")
        if tuple(result.symbol for result in self.symbol_results) != self.symbols:
            raise ValueError("symbol_results must match symbols order")
        if self.materialized_symbol_count != sum(1 for result in self.symbol_results if result.materialized):
            raise ValueError("materialized_symbol_count does not match symbol results")
        if self.blocked_symbol_count != self.symbol_count - self.materialized_symbol_count:
            raise ValueError("blocked_symbol_count does not match symbol results")
        if self.input_value_count != sum(result.input_value_count for result in self.symbol_results):
            raise ValueError("input_value_count does not match symbol results")
        if self.row_count != sum(result.row_count for result in self.symbol_results):
            raise ValueError("row_count does not match symbol results")
        expected_write_ids = tuple(result.write_id for result in self.symbol_results if result.write_id)
        if self.write_ids != expected_write_ids:
            raise ValueError("write_ids must match symbol result write IDs")
        expected_refs = tuple(result.gold_panel_ref for result in self.symbol_results if result.gold_panel_ref)
        if self.gold_panel_refs != expected_refs:
            raise ValueError("gold_panel_refs must match symbol result refs")
        if self.all_symbols_materialized != (self.materialized_symbol_count == self.symbol_count):
            raise ValueError("all_symbols_materialized does not match symbol readiness")
        if self.all_symbols_materialized and self.blocker_reasons:
            raise ValueError("materialized results cannot carry blocker reasons")
        if not self.all_symbols_materialized and not self.blocker_reasons:
            raise ValueError("blocked materializer results require blocker reasons")
        if self.accepted_historical_coverage_proof:
            raise ValueError("gold panel materializer results are not accepted coverage proof")
        expected_id = gold_panel_materializer_result_id_for(
            preflight_id=self.preflight_id,
            panel_name=self.panel_name,
            interval=self.interval,
            archive_root_ref=self.archive_root_ref,
            job_id=self.job_id,
            dataset=self.dataset,
            venue=self.venue,
            symbols=self.symbols,
            symbol_result_ids=tuple(result.result_id for result in self.symbol_results),
            write_ids=self.write_ids,
            gold_panel_refs=self.gold_panel_refs,
            input_value_count=self.input_value_count,
            row_count=self.row_count,
            all_symbols_materialized=self.all_symbols_materialized,
            blocker_reasons=self.blocker_reasons,
        )
        if self.materializer_id != expected_id:
            raise ValueError("materializer_id does not match gold panel materializer result")
        return self


def materialize_gold_research_panels(
    *,
    archive_root: str | Path,
    preflight_result: GoldPanelPreflightResult | Mapping[str, Any],
    input_values_by_symbol: Mapping[str, Iterable[GoldResearchPanelInputValue | Mapping[str, Any]]],
    job_id: str,
    dataset: str = "feature_panels",
    venue: str = "hyperliquid",
) -> GoldPanelMaterializerResult:
    preflight = (
        preflight_result
        if isinstance(preflight_result, GoldPanelPreflightResult)
        else GoldPanelPreflightResult.model_validate(dict(preflight_result))
    )
    archive_root_ref = str(Path(archive_root).resolve(strict=False))
    declared_symbols = set(preflight.symbols)
    unknown_symbols = sorted(set(input_values_by_symbol) - declared_symbols)
    if unknown_symbols:
        raise ValueError("row-value inputs include symbols outside preflight: " + ",".join(unknown_symbols))
    parsed_values_by_symbol = {
        symbol: tuple(
            value
            if isinstance(value, GoldResearchPanelInputValue)
            else GoldResearchPanelInputValue.model_validate(dict(value))
            for value in values
        )
        for symbol, values in input_values_by_symbol.items()
    }

    pending: list[
        tuple[
            GoldPanelPreflightSymbolResult,
            GoldResearchPanelAssemblyResult,
            tuple[str, ...],
        ]
    ] = []
    for symbol_result in preflight.symbol_results:
        values = parsed_values_by_symbol.get(symbol_result.symbol, ())
        assembly = assemble_gold_research_panel_rows(
            manifest=symbol_result.gold_panel_manifest,
            input_values=values,
        )
        blockers = _symbol_materializer_blockers(
            preflight=preflight,
            symbol_result=symbol_result,
            values=values,
            assembly=assembly,
        )
        pending.append((symbol_result, assembly, blockers))

    if any(blockers for _symbol_result, _assembly, blockers in pending):
        blocked_results = tuple(
            _gold_panel_materializer_symbol_result(
                symbol_result=symbol_result,
                assembly_result=assembly,
                write_result=None,
                blocker_reasons=blockers or ("materializer_not_all_symbols_ready",),
            )
            for symbol_result, assembly, blockers in pending
        )
        return _gold_panel_materializer_result(
            preflight=preflight,
            archive_root_ref=archive_root_ref,
            job_id=job_id,
            dataset=dataset,
            venue=venue,
            symbol_results=blocked_results,
        )

    written_results: list[GoldPanelMaterializerSymbolResult] = []
    for symbol_result, assembly, _blockers in pending:
        write_result = write_gold_research_panel_artifacts(
            archive_root=archive_root,
            assembly_result=assembly,
            job_id=job_id,
            dataset=dataset,
            venue=venue,
        )
        written_results.append(
            _gold_panel_materializer_symbol_result(
                symbol_result=symbol_result,
                assembly_result=assembly,
                write_result=write_result,
                blocker_reasons=(),
            )
        )

    return _gold_panel_materializer_result(
        preflight=preflight,
        archive_root_ref=archive_root_ref,
        job_id=job_id,
        dataset=dataset,
        venue=venue,
        symbol_results=tuple(written_results),
    )


def gold_panel_materializer_symbol_result_id_for(
    *,
    symbol: str,
    preflight_symbol_result_id: str,
    panel_id: str,
    assembly_id: str,
    write_id: str | None,
    input_value_count: int,
    row_count: int,
    gold_panel_ref: str | None,
    assembly_manifest_ref: str | None,
    materialized: bool,
    blocker_reasons: tuple[str, ...],
) -> str:
    return canonical_json_hash(
        {
            "result_type": "gold_panel_materializer_symbol_result",
            "symbol": symbol,
            "preflight_symbol_result_id": preflight_symbol_result_id,
            "panel_id": panel_id,
            "assembly_id": assembly_id,
            "write_id": write_id,
            "input_value_count": input_value_count,
            "row_count": row_count,
            "gold_panel_ref": gold_panel_ref,
            "assembly_manifest_ref": assembly_manifest_ref,
            "materialized": materialized,
            "blocker_reasons": blocker_reasons,
        }
    )


def gold_panel_materializer_result_id_for(
    *,
    preflight_id: str,
    panel_name: str,
    interval: str,
    archive_root_ref: str,
    job_id: str,
    dataset: str,
    venue: str,
    symbols: tuple[str, ...],
    symbol_result_ids: tuple[str, ...],
    write_ids: tuple[str, ...],
    gold_panel_refs: tuple[str, ...],
    input_value_count: int,
    row_count: int,
    all_symbols_materialized: bool,
    blocker_reasons: tuple[str, ...],
) -> str:
    return canonical_json_hash(
        {
            "result_type": "gold_panel_materializer_result",
            "preflight_id": preflight_id,
            "panel_name": panel_name,
            "interval": interval,
            "archive_root_ref": archive_root_ref,
            "job_id": job_id,
            "dataset": dataset,
            "venue": venue,
            "symbols": symbols,
            "symbol_result_ids": symbol_result_ids,
            "write_ids": write_ids,
            "gold_panel_refs": gold_panel_refs,
            "input_value_count": input_value_count,
            "row_count": row_count,
            "all_symbols_materialized": all_symbols_materialized,
            "blocker_reasons": blocker_reasons,
        }
    )


def gold_panel_materializer_symbol_results_hash(
    results: tuple[GoldPanelMaterializerSymbolResult, ...],
) -> str:
    return manifest_rows_hash(result.model_dump(mode="json") for result in results)


def _symbol_materializer_blockers(
    *,
    preflight: GoldPanelPreflightResult,
    symbol_result: GoldPanelPreflightSymbolResult,
    values: tuple[GoldResearchPanelInputValue, ...],
    assembly: GoldResearchPanelAssemblyResult,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if not preflight.all_symbols_ready:
        blockers.append("preflight_all_symbols_not_ready")
    if not symbol_result.panel_ready:
        blockers.extend(symbol_result.blocker_reasons)
    blockers.extend(assembly.blocker_reasons)
    if values and any(value.source_row_hash is None for value in values):
        blockers.append("missing_source_row_hash")
    return _unique(tuple(blockers))


def _gold_panel_materializer_symbol_result(
    *,
    symbol_result: GoldPanelPreflightSymbolResult,
    assembly_result: GoldResearchPanelAssemblyResult,
    write_result: GoldResearchPanelWriteResult | None,
    blocker_reasons: tuple[str, ...],
) -> GoldPanelMaterializerSymbolResult:
    materialized = write_result is not None and not blocker_reasons
    write_id = None if write_result is None else write_result.write_id
    gold_panel_ref = None if write_result is None else write_result.gold_panel_ref
    assembly_manifest_ref = None if write_result is None else write_result.assembly_manifest_ref
    result_id = gold_panel_materializer_symbol_result_id_for(
        symbol=symbol_result.symbol,
        preflight_symbol_result_id=symbol_result.result_id,
        panel_id=symbol_result.gold_panel_manifest.panel_id,
        assembly_id=assembly_result.assembly_id,
        write_id=write_id,
        input_value_count=assembly_result.input_value_count,
        row_count=assembly_result.row_count,
        gold_panel_ref=gold_panel_ref,
        assembly_manifest_ref=assembly_manifest_ref,
        materialized=materialized,
        blocker_reasons=blocker_reasons,
    )
    return GoldPanelMaterializerSymbolResult(
        result_id=result_id,
        symbol=symbol_result.symbol,
        preflight_symbol_result_id=symbol_result.result_id,
        panel_id=symbol_result.gold_panel_manifest.panel_id,
        assembly_result=assembly_result,
        write_result=write_result,
        input_value_count=assembly_result.input_value_count,
        row_count=assembly_result.row_count,
        write_id=write_id,
        gold_panel_ref=gold_panel_ref,
        assembly_manifest_ref=assembly_manifest_ref,
        materialized=materialized,
        blocker_reasons=blocker_reasons,
    )


def _gold_panel_materializer_result(
    *,
    preflight: GoldPanelPreflightResult,
    archive_root_ref: str,
    job_id: str,
    dataset: str,
    venue: str,
    symbol_results: tuple[GoldPanelMaterializerSymbolResult, ...],
) -> GoldPanelMaterializerResult:
    blockers = _unique(tuple(reason for result in symbol_results for reason in result.blocker_reasons))
    write_ids = tuple(result.write_id for result in symbol_results if result.write_id)
    gold_panel_refs = tuple(result.gold_panel_ref for result in symbol_results if result.gold_panel_ref)
    materialized_symbol_count = sum(1 for result in symbol_results if result.materialized)
    all_symbols_materialized = materialized_symbol_count == len(symbol_results)
    input_value_count = sum(result.input_value_count for result in symbol_results)
    row_count = sum(result.row_count for result in symbol_results)
    materializer_id = gold_panel_materializer_result_id_for(
        preflight_id=preflight.preflight_id,
        panel_name=preflight.panel_name,
        interval=preflight.interval,
        archive_root_ref=archive_root_ref,
        job_id=job_id,
        dataset=dataset,
        venue=venue,
        symbols=preflight.symbols,
        symbol_result_ids=tuple(result.result_id for result in symbol_results),
        write_ids=write_ids,
        gold_panel_refs=gold_panel_refs,
        input_value_count=input_value_count,
        row_count=row_count,
        all_symbols_materialized=all_symbols_materialized,
        blocker_reasons=blockers,
    )
    return GoldPanelMaterializerResult(
        materializer_id=materializer_id,
        preflight_id=preflight.preflight_id,
        panel_name=preflight.panel_name,
        interval=preflight.interval,
        archive_root_ref=archive_root_ref,
        job_id=job_id,
        dataset=dataset,
        venue=venue,
        symbols=preflight.symbols,
        symbol_results=symbol_results,
        symbol_count=len(symbol_results),
        materialized_symbol_count=materialized_symbol_count,
        blocked_symbol_count=len(symbol_results) - materialized_symbol_count,
        input_value_count=input_value_count,
        row_count=row_count,
        write_ids=write_ids,
        gold_panel_refs=gold_panel_refs,
        blocker_reasons=blockers,
        all_symbols_materialized=all_symbols_materialized,
    )


def _unique(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))
