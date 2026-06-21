# V2-AUDIT-ID: V2-AUD-PKG-001
# V2-CONTRACTS: docs/PRODUCT_SCOPE.md
# V2-BOUNDARY: research_only, no_live_imports, no_order_or_sizing
# V2-OWNER: v2_config
"""Default v2 policy constants."""

from __future__ import annotations

from datetime import date

DEFAULT_ARCHIVE_ROOT = "data/archive"
DEFAULT_RUNS_ROOT = "runs"
DEFAULT_PRIMARY_VENUE = "hyperliquid"
DEFAULT_MARKET_TYPE = "perpetual"
DEFAULT_MIN_DAY_NOTIONAL_USD = 5_000_000
DEFAULT_COVERAGE_MIN = 0.98
DEFAULT_EARLIEST_BACKTEST_START = date(2024, 1, 1)
DEFAULT_MIN_USABLE_MONTHS = 6
DEFAULT_PREFERRED_USABLE_MONTHS = 12
DEFAULT_LOCKBOX_FULL_MONTHS = 1
