# V2-AUDIT-ID: V2-AUD-PKG-001
# V2-CONTRACTS: docs/PRODUCT_SCOPE.md
# V2-BOUNDARY: research_only, no_live_imports, no_order_or_sizing
# V2-OWNER: v2_package
"""ResearchEngineDeluxe v2 package shell.

The v2 package is research-only infrastructure. It intentionally avoids imports
from live, paper, order-placement, sizing, runtime, candidate-pack promotion,
and promotion modules.
"""

from __future__ import annotations

from tradingbotsuite.v2.config.schemas import (
    RESEARCH_BOUNDARY,
    V2_PACKAGE_NAME,
    V2_SCHEMA_VERSION,
)

__all__ = ["RESEARCH_BOUNDARY", "V2_PACKAGE_NAME", "V2_SCHEMA_VERSION"]
