"""Research-only discovery run manager foundation."""

from __future__ import annotations

from tradingbotsuite.research_discovery.runner import DiscoveryRunResult, run_discovery
from tradingbotsuite.research_discovery.ablation_matrix import (
    AblationComparisonSpec,
    PerpFilterAblationArtifactResult,
    PerpFilterAblationMatrixResult,
    PerpFilterAblationMatrixSpec,
    build_perp_filter_ablation_matrix,
    write_perp_filter_ablation_artifacts,
)
from tradingbotsuite.research_discovery.exit_lab import (
    DiscoveryExitLabArtifactResult,
    DiscoveryExitLabResult,
    DiscoveryExitLabSpec,
    ExitLabComparisonSpec,
    build_discovery_exit_lab,
    write_discovery_exit_lab_artifacts,
)
from tradingbotsuite.research_discovery.feature_sets import (
    DiscoveryFeatureColumnSetManifest,
    load_feature_column_set_manifest,
)
from tradingbotsuite.research_discovery.hmm_materialization import (
    HmmMaterializationArtifactResult,
    HmmMaterializationResult,
    HmmMaterializationSpec,
    materialize_split_safe_hmm_regimes,
    write_hmm_materialization_artifacts,
)
from tradingbotsuite.research_discovery.knn_study import (
    KnnStudyArtifactResult,
    KnnStudyResult,
    KnnStudySpec,
    materialize_regime_local_knn_predictions,
    write_knn_study_artifacts,
)
from tradingbotsuite.research_discovery.strategy_integration import (
    DiscoveryStrategyAccountingArtifactResult,
    DiscoveryStrategyAccountingResult,
    account_hmm_knn_local_analog_strategy,
    write_strategy_accounting_artifacts,
)
from tradingbotsuite.research_discovery.spec import DiscoveryRunSpec

__all__ = [
    "DiscoveryFeatureColumnSetManifest",
    "DiscoveryExitLabArtifactResult",
    "DiscoveryExitLabResult",
    "DiscoveryExitLabSpec",
    "DiscoveryStrategyAccountingArtifactResult",
    "DiscoveryStrategyAccountingResult",
    "ExitLabComparisonSpec",
    "HmmMaterializationArtifactResult",
    "HmmMaterializationResult",
    "HmmMaterializationSpec",
    "KnnStudyArtifactResult",
    "KnnStudyResult",
    "KnnStudySpec",
    "AblationComparisonSpec",
    "DiscoveryRunResult",
    "DiscoveryRunSpec",
    "PerpFilterAblationArtifactResult",
    "PerpFilterAblationMatrixResult",
    "PerpFilterAblationMatrixSpec",
    "account_hmm_knn_local_analog_strategy",
    "build_discovery_exit_lab",
    "build_perp_filter_ablation_matrix",
    "load_feature_column_set_manifest",
    "materialize_split_safe_hmm_regimes",
    "materialize_regime_local_knn_predictions",
    "run_discovery",
    "write_hmm_materialization_artifacts",
    "write_knn_study_artifacts",
    "write_discovery_exit_lab_artifacts",
    "write_perp_filter_ablation_artifacts",
    "write_strategy_accounting_artifacts",
]
