# V2-AUDIT-ID: V2-AUD-PKG-001
# V2-CONTRACTS: docs/PRODUCT_SCOPE.md, docs/V2_NO_TOUCH_PATHS.md
# V2-BOUNDARY: research_only, no_live_imports, no_order_or_sizing
# V2-OWNER: v2_security
"""V2 security bounded-context shell."""

from __future__ import annotations

from tradingbotsuite.v2.security.boundary import (
    BOUNDARY_FALSE_FIELDS,
    BOUNDARY_TRUE_FIELDS,
    CANONICAL_BOUNDARY_FLAGS,
    ResearchBoundaryError,
    boundary_subset_payload,
    boundary_violation_reasons,
    require_research_boundary,
    research_boundary_defaults,
)
from tradingbotsuite.v2.security.hygiene import (
    CommandClass,
    CommandClassification,
    REDACTED_VALUE,
    SecretPolicy,
    SecretScanResult,
    TrustedArtifactRef,
    TrustedArtifactValidation,
    redact_mapping,
    redact_text,
    validate_trusted_artifact,
)
from tradingbotsuite.v2.security.path_policy import PathPolicy, resolve_within_root

__all__ = [
    "BOUNDARY_FALSE_FIELDS",
    "BOUNDARY_TRUE_FIELDS",
    "CANONICAL_BOUNDARY_FLAGS",
    "CommandClass",
    "CommandClassification",
    "PathPolicy",
    "REDACTED_VALUE",
    "ResearchBoundaryError",
    "SecretPolicy",
    "SecretScanResult",
    "TrustedArtifactRef",
    "TrustedArtifactValidation",
    "boundary_subset_payload",
    "boundary_violation_reasons",
    "redact_mapping",
    "redact_text",
    "research_boundary_defaults",
    "require_research_boundary",
    "resolve_within_root",
    "validate_trusted_artifact",
]
