# V2-AUDIT-ID: V2-AUD-PKG-001
# V2-CONTRACTS: docs/PRODUCT_SCOPE.md
# V2-BOUNDARY: research_only, no_live_imports, no_order_or_sizing
# V2-OWNER: v2_config
"""Shared v2 schema and boundary constants."""

from __future__ import annotations

from types import MappingProxyType

V2_PACKAGE_NAME = "tradingbotsuite.v2"
V2_SCHEMA_VERSION = "redx-v2-phase1-shell-v1"

RESEARCH_BOUNDARY = MappingProxyType(
    {
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "candidate_evidence": False,
        "candidate_pack_eligible": False,
        "live_signal": False,
        "paper_signal": False,
        "sizing_instruction": False,
        "order_placement_instruction": False,
        "runtime_mode_change": False,
    }
)

BOUNDED_CONTEXTS = (
    "archive",
    "universe",
    "venues",
    "collectors",
    "data_quality",
    "backtest_data",
    "strategy_specs",
    "strategy_plugins",
    "backtest_engine",
    "costs",
    "validation",
    "ledger",
    "lead_book",
    "workers",
    "audit",
    "security",
)
