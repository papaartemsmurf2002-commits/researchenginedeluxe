# V2-AUDIT-ID: V2-AUD-CONTRACTS-001
# V2-CONTRACTS: docs/contracts/ledger_contract.md
# V2-BOUNDARY: research_only, append_only_ledger, no_live_imports
# V2-OWNER: v2_ledger
"""Append-only experiment ledger schemas for v2."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import ensure_utc
from tradingbotsuite.v2.security.boundary import require_research_boundary

LEDGER_SCHEMA_VERSION = "ledger_row_v1"


class LedgerAppendRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_manifest_path: str = Field(min_length=1)
    validation_manifest_path: str | None = None
    ledger_path: str = Field(min_length=1)
    evidence_mode: str = "sandbox_diagnostic"
    notes: str = ""

    @field_validator("evidence_mode")
    @classmethod
    def _known_evidence_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"sandbox_diagnostic", "accepted_research"}:
            raise ValueError("evidence_mode must be sandbox_diagnostic or accepted_research")
        return normalized


class LedgerRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = LEDGER_SCHEMA_VERSION
    ledger_index: int = Field(default=0, ge=0)
    row_hash: str | None = Field(default=None, min_length=64, max_length=64)
    run_id: str = Field(min_length=1)
    experiment_id: str = "unknown"
    trial_index: int = Field(default=0, ge=0)
    agent_or_user: str = "agent"
    created_at: datetime | None = None
    row_status: str = "blocked"
    evidence_mode: str = "sandbox_diagnostic"
    git_sha: str = "unknown"
    environment_hash: str = Field(default="0" * 64, min_length=64, max_length=64)
    strategy_id: str = "unknown"
    strategy_version: str = "unknown"
    strategy_hash: str = Field(default="0" * 64, min_length=64, max_length=64)
    params_hash: str = Field(default="0" * 64, min_length=64, max_length=64)
    strategy_lane: str = "declarative"
    archive_snapshot_id: str = Field(min_length=1)
    universe_snapshot_id: str = Field(min_length=1)
    feature_snapshot_id: str = ""
    universe_mode: str = "as_of"
    venue_scope: str = "unknown"
    instrument_count: int = Field(default=0, ge=0)
    timeframe: str = "unknown"
    backtest_start: datetime | None = None
    backtest_end: datetime | None = None
    usable_months: int = Field(default=0, ge=0)
    lockbox_policy_id: str = "unknown"
    lockbox_start: datetime | None = None
    lockbox_end: datetime | None = None
    data_coverage_min: float = Field(default=0.0, ge=0.0, le=1.0)
    strategy_spec_hash: str = Field(min_length=64, max_length=64)
    cost_model_id: str = Field(min_length=1)
    cost_model_hash: str = Field(default="0" * 64, min_length=64, max_length=64)
    gross_return: float | None = None
    validation_status: str = "not_validated"
    net_return: float | None = None
    roi_observed: float | None = None
    annualized_return: float | None = None
    annualized_vol: float | None = None
    sharpe: float | None = None
    sortino: float | None = None
    max_drawdown: float | None = None
    calmar: float | None = None
    turnover: float | None = None
    avg_daily_trades: float | None = None
    fee_paid: float | None = None
    funding_pnl: float | None = None
    slippage_cost: float | None = None
    impact_cost: float | None = None
    walk_forward_pass: bool | None = None
    pbo_score: float | None = None
    trial_count: int = Field(default=1, ge=0)
    fold_count: int = Field(default=0, ge=0)
    fold_stability_score: float | None = Field(default=None, ge=0.0, le=1.0)
    family_median_net_return: float | None = None
    best_vs_median_gap: float | None = None
    failure_reason: str | None = None
    diminishing_returns_warning: bool = False
    profit_concentration_warning: bool = False
    minimum_trade_frequency_pass: bool | None = None
    monthly_stability_pass: bool | None = None
    cost_fragile_warning: bool = False
    survivorship_bias_status: str = "not_evaluated"
    artifact_path: str = Field(default="", min_length=0)
    artifact_sha256: str = Field(default="0" * 64, min_length=64, max_length=64)
    validation_manifest_path: str = ""
    metrics_path: str = ""
    notes: str = ""
    gross_only: bool = False
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

    @field_validator(
        "created_at",
        "backtest_start",
        "backtest_end",
        "lockbox_start",
        "lockbox_end",
    )
    @classmethod
    def _utc_timestamps(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return ensure_utc(value)

    @model_validator(mode="after")
    def _validate_ledger_row(self) -> "LedgerRow":
        if self.gross_only:
            raise ValueError("ledger rows cannot be gross-only")
        require_research_boundary(self, context="ledger row")
        if self.row_status == "succeeded" and self.net_return is None:
            raise ValueError("succeeded ledger rows require net_return")
        if self.validation_status == "":
            raise ValueError("ledger rows require validation_status")
        return self


class LeaderboardRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    rank: int = Field(ge=1)
    run_id: str = Field(min_length=1)
    experiment_id: str = Field(min_length=1)
    strategy_id: str = Field(min_length=1)
    net_return: float
    gross_return: float | None = None
    max_drawdown: float | None = None
    composite_score: float
    validation_status: str
    evidence_mode: str
    trial_count: int = Field(ge=0)
    fold_count: int = Field(ge=0)
    fold_stability_score: float | None = Field(default=None, ge=0.0, le=1.0)
    overfit_warning: bool = False
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
