# V2-AUDIT-ID: V2-AUD-PKG-001
# V2-CONTRACTS: docs/PRODUCT_SCOPE.md
# V2-BOUNDARY: research_only, no_live_imports, no_order_or_sizing
# V2-OWNER: v2_strategy_plugins
"""V2 strategy-plugin bounded-context shell."""

from __future__ import annotations

from tradingbotsuite.v2.strategy_plugins.manifests import (
    StrategyPluginManifest,
    StrategyPluginProtocol,
    StrategyPluginRegistryManifest,
    build_legacy_strategy_plugin_manifest,
    build_legacy_strategy_plugin_registry_manifest,
    write_strategy_plugin_manifest,
    write_strategy_plugin_registry_manifest,
)

__all__ = [
    "StrategyPluginManifest",
    "StrategyPluginProtocol",
    "StrategyPluginRegistryManifest",
    "build_legacy_strategy_plugin_manifest",
    "build_legacy_strategy_plugin_registry_manifest",
    "write_strategy_plugin_manifest",
    "write_strategy_plugin_registry_manifest",
]
