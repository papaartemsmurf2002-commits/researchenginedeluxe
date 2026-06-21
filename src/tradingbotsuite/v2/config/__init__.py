# V2-AUDIT-ID: V2-AUD-PKG-001
# V2-CONTRACTS: docs/PRODUCT_SCOPE.md
# V2-BOUNDARY: research_only, no_live_imports, no_order_or_sizing
# V2-OWNER: v2_config
"""V2 configuration package."""

from __future__ import annotations

from tradingbotsuite.v2.config.settings import V2Settings, default_settings

__all__ = ["V2Settings", "default_settings"]
