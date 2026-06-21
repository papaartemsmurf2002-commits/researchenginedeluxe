# V2-AUDIT-ID: V2-AUD-QUAL-001
# V2-CONTRACTS: docs/contracts/data_quality_contract.md
# V2-BOUNDARY: research_only, coverage_gate, no_live_imports
# V2-OWNER: v2_data_quality
"""Schema models for v2 data coverage and quality reports."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import utc_now


DEFAULT_COVERAGE_MIN = 0.98


class EvidenceMode(str, Enum):
    ACCEPTED_RESEARCH = "accepted_research"
    REPORTED_EVIDENCE = "reported_evidence"
    SANDBOX_DIAGNOSTIC = "sandbox_diagnostic"


class QualityStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    NON_EVIDENCE = "non_evidence"


class CoverageReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    coverage_report_id: str = Field(min_length=64, max_length=64)
    schema_version: str = V2_SCHEMA_VERSION
    created_at: datetime = Field(default_factory=utc_now)
    venue: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    family: str = Field(default="bars", min_length=1)
    timeframe: str = Field(min_length=1)
    start_ts: datetime
    end_ts: datetime
    expected_rows: int = Field(ge=0)
    observed_rows: int = Field(ge=0)
    source_row_count: int = Field(ge=0)
    coverage_ratio: float = Field(ge=0.0, le=1.0)
    coverage_min: float = Field(default=DEFAULT_COVERAGE_MIN, ge=0.0, le=1.0)
    missing_timestamp_count: int = Field(ge=0)
    missing_timestamps_sample: tuple[str, ...] = ()
    missing_days: tuple[str, ...] = ()
    duplicate_timestamp_count: int = Field(ge=0)
    stale_segment_count: int = Field(ge=0)
    zero_volume_count: int = Field(ge=0)
    return_outlier_count: int = Field(ge=0)
    spread_outlier_count: int = Field(ge=0)
    funding_outlier_count: int = Field(ge=0)
    outlier_count: int = Field(ge=0)
    parse_failure_count: int = Field(ge=0)
    source_caveats: tuple[str, ...] = ()
    evidence_mode: EvidenceMode = EvidenceMode.ACCEPTED_RESEARCH
    quality_status: QualityStatus
    evidence_eligible: bool
    blocker_reasons: tuple[str, ...] = ()
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
    def _validate_report(self) -> "CoverageReport":
        if self.end_ts <= self.start_ts:
            raise ValueError("end_ts must be greater than start_ts")
        if self.observed_rows > self.expected_rows and self.expected_rows > 0:
            raise ValueError("observed_rows cannot exceed expected_rows")
        if self.outlier_count != (
            self.return_outlier_count
            + self.spread_outlier_count
            + self.funding_outlier_count
        ):
            raise ValueError("outlier_count must equal the sum of outlier families")
        boundary = (
            self.research_only
            and self.observe_only
            and not self.promotion_ready
            and not self.candidate_evidence
            and not self.candidate_pack_eligible
            and not self.live_signal
            and not self.paper_signal
            and not self.sizing_instruction
            and not self.order_placement_instruction
            and not self.runtime_mode_change
        )
        if not boundary:
            raise ValueError("coverage reports must preserve the v2 research boundary")
        if self.evidence_mode == EvidenceMode.SANDBOX_DIAGNOSTIC:
            if self.evidence_eligible:
                raise ValueError("sandbox diagnostics cannot be evidence eligible")
            if "sandbox_diagnostic_non_evidence" not in self.blocker_reasons:
                raise ValueError("sandbox diagnostics must be labeled non-evidence")
        if self.evidence_eligible and self.blocker_reasons:
            raise ValueError("evidence eligible reports cannot have blocker reasons")
        return self


class DataQualityCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    check_id: str = Field(min_length=64, max_length=64)
    schema_version: str = V2_SCHEMA_VERSION
    created_at: datetime = Field(default_factory=utc_now)
    venue: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    family: str = Field(default="bars", min_length=1)
    timeframe: str = Field(min_length=1)
    start_ts: datetime
    end_ts: datetime
    check_type: str = Field(min_length=1)
    status: QualityStatus
    affected_count: int = Field(ge=0)
    affected_timestamps_sample: tuple[str, ...] = ()
    severity: str = "blocker"
    details: dict[str, str] = Field(default_factory=dict)
    evidence_mode: EvidenceMode = EvidenceMode.ACCEPTED_RESEARCH
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False

    @model_validator(mode="after")
    def _validate_check(self) -> "DataQualityCheck":
        if self.end_ts <= self.start_ts:
            raise ValueError("end_ts must be greater than start_ts")
        if not self.research_only or not self.observe_only or self.promotion_ready:
            raise ValueError("quality checks must preserve the v2 research boundary")
        if self.status == QualityStatus.PASS and self.affected_count != 0:
            raise ValueError("passing quality checks cannot have affected rows")
        return self
