# V2-AUDIT-ID: V2-AUD-COLLECT-020
# V2-CONTRACTS: docs/contracts/collector_job_contract.md
# V2-BOUNDARY: research_only, gap_request_required, no_live_imports, no_network_fetch
# V2-OWNER: v2_collectors
"""Research-only collector adapter templates for proven data gaps."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbotsuite.v2.archive.hashing import canonical_json_hash
from tradingbotsuite.v2.archive_inventory import DataGapRequest
from tradingbotsuite.v2.config.schemas import RESEARCH_BOUNDARY, V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import utc_isoformat
from tradingbotsuite.v2.security.boundary import require_research_boundary


class ResearchCollectorAdapterTemplate(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    template_id: str = Field(min_length=64, max_length=64)
    adapter_id: str = Field(min_length=1)
    data_gap_request_id: str = Field(min_length=64, max_length=64)
    requested_family: str = Field(min_length=1)
    requested_fields: tuple[str, ...] = ()
    instrument_ids: tuple[str, ...] = Field(min_length=1)
    venue_preference: tuple[str, ...] = ()
    allowed_venues: tuple[str, ...] = ()
    start_ts: str = Field(min_length=1)
    end_ts: str = Field(min_length=1)
    gap_reason: str = Field(min_length=1)
    existing_archive_refs_checked: tuple[str, ...] = ()
    missing_coverage_report_ids: tuple[str, ...] = ()
    gap_evidence_provided: bool = False
    source_access_mode: str = "official_public_no_paid"
    raw_before_normalized_required: bool = True
    manifest_refs_required: tuple[str, ...] = (
        "raw_source_ref",
        "source_sha256",
        "row_count",
        "coverage_report_id",
        "quality_status",
        "boundary_flags",
    )
    collection_scope: Literal["bounded_gap_request_only"] = "bounded_gap_request_only"
    venue_probe_allowed: bool = False
    venue_expansion_allowed: bool = False
    collection_authorized: bool = False
    authorization_note: str = "template_only_requires_scoped_packet_before_fetch"
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
    def _validate_template(self) -> "ResearchCollectorAdapterTemplate":
        if self.collection_authorized:
            raise ValueError("collector templates cannot authorize collection")
        if self.venue_expansion_allowed:
            raise ValueError("collector templates cannot allow venue expansion")
        allowed_venues = set(self.allowed_venues)
        preferred_venues = set(self.venue_preference)
        if self.venue_probe_allowed and not self.data_gap_request_id:
            raise ValueError("venue probes require a data gap request")
        if self.venue_probe_allowed and not self.gap_evidence_provided:
            raise ValueError("venue probes require checked archive refs or coverage report evidence")
        if self.venue_probe_allowed and not allowed_venues:
            raise ValueError("venue probes require allowed venues from the data gap request")
        if allowed_venues and not preferred_venues:
            raise ValueError("allowed venues require data gap venue preference")
        if not allowed_venues.issubset(preferred_venues):
            raise ValueError("allowed venues must be bounded by venue_preference")
        if self.gap_evidence_provided and not (self.existing_archive_refs_checked or self.missing_coverage_report_ids):
            raise ValueError("gap_evidence_provided requires checked refs or coverage reports")
        require_research_boundary(self, context="research collector adapter template")
        return self


def collector_template_from_gap_request(
    gap: DataGapRequest,
    *,
    adapter_id: str | None = None,
) -> ResearchCollectorAdapterTemplate:
    """Convert a proven gap into a bounded template without fetching data."""

    require_research_boundary(gap, context="data gap request")
    resolved_adapter = adapter_id or gap.suggested_collector
    if not resolved_adapter:
        raise ValueError("data gap request has no suggested collector")
    evidence_provided = bool(gap.existing_archive_refs_checked or gap.missing_coverage_report_ids)
    payload = {
        "adapter_id": resolved_adapter,
        "data_gap_request_id": gap.data_gap_request_id,
        "requested_family": gap.requested_family,
        "requested_fields": gap.requested_fields,
        "instrument_ids": gap.instrument_ids,
        "venue_preference": gap.venue_preference,
        "allowed_venues": gap.venue_preference,
        "start_ts": utc_isoformat(gap.start_ts),
        "end_ts": utc_isoformat(gap.end_ts),
        "gap_reason": gap.reason,
        "existing_archive_refs_checked": gap.existing_archive_refs_checked,
        "missing_coverage_report_ids": gap.missing_coverage_report_ids,
        "gap_evidence_provided": evidence_provided,
        "collection_scope": "bounded_gap_request_only",
        "venue_probe_allowed": gap.venue_probe_allowed,
        "venue_expansion_allowed": False,
        "collection_authorized": False,
        **dict(RESEARCH_BOUNDARY),
    }
    return ResearchCollectorAdapterTemplate(
        **payload,
        template_id=canonical_json_hash(
            {
                "schema_version": V2_SCHEMA_VERSION,
                "adapter_id": resolved_adapter,
                "data_gap_request_id": gap.data_gap_request_id,
                "requested_family": gap.requested_family,
                "instrument_ids": gap.instrument_ids,
                "allowed_venues": gap.venue_preference,
                "start_ts": utc_isoformat(gap.start_ts),
                "end_ts": utc_isoformat(gap.end_ts),
                "gap_evidence_provided": evidence_provided,
                "collection_scope": "bounded_gap_request_only",
                "venue_expansion_allowed": False,
            }
        ),
    )
