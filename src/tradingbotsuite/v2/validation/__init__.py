# V2-AUDIT-ID: V2-AUD-PKG-001
# V2-CONTRACTS: docs/PRODUCT_SCOPE.md
# V2-BOUNDARY: research_only, no_live_imports, no_order_or_sizing
# V2-OWNER: v2_validation
"""V2 validation bounded context."""

from __future__ import annotations

from tradingbotsuite.v2.validation.final_hard_test import (
    FINAL_HARD_TEST_MAX_SLOTS,
    NON_LIVE_SURVIVOR_DISCLAIMER,
    DeepValidationManifest,
    DeepValidationScorecard,
    DeepValidationStatus,
    FinalHardTestSlot,
    FinalSurvivorReport,
    Pre2024FallbackDiagnostic,
    Pre2024FallbackStatus,
    allocate_final_hard_test_slot,
    build_final_survivor_report,
    build_pre_2024_fallback_diagnostic,
    complete_deep_validation,
    reject_parameter_edit_after_lockbox,
    start_deep_validation,
)
from tradingbotsuite.v2.validation.overfit import (
    SweepCompletenessReport,
    TrialFamilyReport,
    TrialResult,
    check_sweep_completeness,
    reject_post_lockbox_parameter_tuning,
    require_complete_sweep,
    trial_family_report,
)
from tradingbotsuite.v2.validation.policies import LockboxPolicy, ValidationConfig
from tradingbotsuite.v2.validation.walk_forward import (
    FoldMetric,
    FoldStabilitySummary,
    WalkForwardConfig,
    WalkForwardFold,
    build_walk_forward_folds,
    fold_rows_for_artifact,
    summarize_fold_stability,
)

__all__ = [
    "FoldMetric",
    "FoldStabilitySummary",
    "FINAL_HARD_TEST_MAX_SLOTS",
    "FinalHardTestSlot",
    "FinalSurvivorReport",
    "LockboxPolicy",
    "NON_LIVE_SURVIVOR_DISCLAIMER",
    "Pre2024FallbackDiagnostic",
    "Pre2024FallbackStatus",
    "SweepCompletenessReport",
    "DeepValidationManifest",
    "DeepValidationScorecard",
    "DeepValidationStatus",
    "TrialFamilyReport",
    "TrialResult",
    "ValidationConfig",
    "WalkForwardConfig",
    "WalkForwardFold",
    "allocate_final_hard_test_slot",
    "build_walk_forward_folds",
    "build_final_survivor_report",
    "build_pre_2024_fallback_diagnostic",
    "check_sweep_completeness",
    "complete_deep_validation",
    "fold_rows_for_artifact",
    "reject_parameter_edit_after_lockbox",
    "reject_post_lockbox_parameter_tuning",
    "require_complete_sweep",
    "start_deep_validation",
    "summarize_fold_stability",
    "trial_family_report",
]
