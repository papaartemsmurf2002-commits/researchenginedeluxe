# V2-AUDIT-ID: V2-AUD-PKG-001
# V2-CONTRACTS: docs/PRODUCT_SCOPE.md
# V2-BOUNDARY: research_only, no_live_imports, no_order_or_sizing
# V2-OWNER: v2_config
"""V2 settings shell."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from tradingbotsuite.v2.config import defaults
from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION


class V2Settings(BaseModel):
    """Static defaults for the Phase 1 v2 shell."""

    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    archive_root: str = defaults.DEFAULT_ARCHIVE_ROOT
    runs_root: str = defaults.DEFAULT_RUNS_ROOT
    primary_venue: str = defaults.DEFAULT_PRIMARY_VENUE
    market_type: str = defaults.DEFAULT_MARKET_TYPE
    min_day_notional_usd: int = Field(
        default=defaults.DEFAULT_MIN_DAY_NOTIONAL_USD,
        ge=5_000_000,
    )
    coverage_min: float = Field(default=defaults.DEFAULT_COVERAGE_MIN, ge=0.0, le=1.0)
    earliest_backtest_start: date = defaults.DEFAULT_EARLIEST_BACKTEST_START
    min_usable_months: int = Field(default=defaults.DEFAULT_MIN_USABLE_MONTHS, ge=6)
    preferred_usable_months: int = Field(
        default=defaults.DEFAULT_PREFERRED_USABLE_MONTHS,
        ge=6,
    )
    lockbox_full_months: int = Field(default=defaults.DEFAULT_LOCKBOX_FULL_MONTHS, ge=1)


def default_settings() -> V2Settings:
    return V2Settings()
