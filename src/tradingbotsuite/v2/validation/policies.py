# V2-AUDIT-ID: V2-AUD-CONTRACTS-001
# V2-CONTRACTS: docs/contracts/validation_contract.md, docs/contracts/backtest_data_service_contract.md
# V2-BOUNDARY: research_only, lockbox_enforced, no_live_imports
# V2-OWNER: v2_validation
"""Validation and lockbox policy skeletons for v2."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbotsuite.v2.config import defaults
from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION


class LockboxPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    policy_id: str = "dynamic_full_calendar_months_v1"
    mode: str = "dynamic_full_calendar_months"
    full_months: int = Field(default=defaults.DEFAULT_LOCKBOX_FULL_MONTHS, ge=1)


class ValidationConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    validation_policy_id: str = "v2_default_validation_v1"
    earliest_backtest_start: date = defaults.DEFAULT_EARLIEST_BACKTEST_START
    min_usable_months: int = Field(default=defaults.DEFAULT_MIN_USABLE_MONTHS, ge=6)
    preferred_usable_months: int = Field(
        default=defaults.DEFAULT_PREFERRED_USABLE_MONTHS,
        ge=6,
    )
    coverage_min: float = Field(default=defaults.DEFAULT_COVERAGE_MIN, ge=0.98, le=1.0)
    require_as_of_universe: bool = True
    lockbox_policy: LockboxPolicy = Field(default_factory=LockboxPolicy)

    @model_validator(mode="after")
    def _preferred_not_less_than_minimum(self) -> "ValidationConfig":
        if self.preferred_usable_months < self.min_usable_months:
            raise ValueError("preferred_usable_months must be >= min_usable_months")
        return self
