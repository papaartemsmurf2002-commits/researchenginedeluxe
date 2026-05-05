"""Live guard public API. Read docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md before boundary edits."""

from __future__ import annotations

from tradingbotsuite.live.preflight import (
    LivePreflightError,
    LivePreflightReport,
    assert_live_preflight,
    assert_research_command_not_live,
    build_live_preflight_report,
)
from tradingbotsuite.live.shadow_loader import (
    ShadowComparisonInputs,
    ShadowLoadedCandidate,
    ShadowLoaderError,
    ShadowLoaderReport,
    build_shadow_loader_report,
    load_shadow_promotion_candidate,
)

__all__ = [
    "LivePreflightError",
    "LivePreflightReport",
    "ShadowComparisonInputs",
    "ShadowLoadedCandidate",
    "ShadowLoaderError",
    "ShadowLoaderReport",
    "assert_live_preflight",
    "assert_research_command_not_live",
    "build_live_preflight_report",
    "build_shadow_loader_report",
    "load_shadow_promotion_candidate",
]
