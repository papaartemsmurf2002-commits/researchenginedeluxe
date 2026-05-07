"""Research-only discovery run manager foundation."""

from __future__ import annotations

from tradingbotsuite.research_discovery.runner import DiscoveryRunResult, run_discovery
from tradingbotsuite.research_discovery.feature_sets import (
    DiscoveryFeatureColumnSetManifest,
    load_feature_column_set_manifest,
)
from tradingbotsuite.research_discovery.spec import DiscoveryRunSpec

__all__ = [
    "DiscoveryFeatureColumnSetManifest",
    "DiscoveryRunResult",
    "DiscoveryRunSpec",
    "load_feature_column_set_manifest",
    "run_discovery",
]
