"""Feature public API. Read docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md before registry/cache edits."""

from __future__ import annotations

from tradingbotsuite.features.builders import (
    BuiltFeatureSet,
    MaterializedFeatureSet,
    build_registered_feature_set,
    canonicalize_bar_frame,
    materialize_registered_feature_set,
    registered_feature_columns,
)
from tradingbotsuite.features.cache import (
    FeatureCacheIdentity,
    feature_cache_paths,
    load_feature_cache_artifact,
    read_feature_cache_manifest,
    write_feature_cache_artifact,
    write_feature_cache_manifest,
)
from tradingbotsuite.features.split_transforms import SplitTransformResult, fit_transform_split_train_only

from tradingbotsuite.features.alignment import (
    FEATURE_ALIGNMENT_CONTRACT_VERSION,
    CompletedBarValidation,
    align_completed_bar_features_to_events,
    feature_availability_column,
    prepare_completed_bar_feature_input,
    validate_completed_bar_continuity,
)
from tradingbotsuite.features.packs import FeatureFrameResult, build_feature_frame
from tradingbotsuite.features.preprocessing import (
    TrainOnlyFeaturePreprocessor,
    fit_train_only_preprocessor,
)
from tradingbotsuite.features.registry import (
    FEATURE_MANIFEST_VERSION,
    FeatureAvailabilityReport,
    FeatureManifest,
    FeaturePack,
    FeatureSpec,
    build_feature_manifest,
    feature_pack_registry,
    feature_set_presets,
    manifest_from_preset,
    validate_feature_manifest,
)

__all__ = [
    "FEATURE_ALIGNMENT_CONTRACT_VERSION",
    "FEATURE_MANIFEST_VERSION",
    "BuiltFeatureSet",
    "CompletedBarValidation",
    "FeatureCacheIdentity",
    "FeatureAvailabilityReport",
    "FeatureManifest",
    "FeaturePack",
    "FeatureSpec",
    "FeatureFrameResult",
    "MaterializedFeatureSet",
    "SplitTransformResult",
    "TrainOnlyFeaturePreprocessor",
    "align_completed_bar_features_to_events",
    "build_registered_feature_set",
    "build_feature_frame",
    "build_feature_manifest",
    "canonicalize_bar_frame",
    "feature_availability_column",
    "feature_cache_paths",
    "feature_pack_registry",
    "feature_set_presets",
    "fit_transform_split_train_only",
    "fit_train_only_preprocessor",
    "load_feature_cache_artifact",
    "materialize_registered_feature_set",
    "manifest_from_preset",
    "prepare_completed_bar_feature_input",
    "read_feature_cache_manifest",
    "registered_feature_columns",
    "validate_completed_bar_continuity",
    "validate_feature_manifest",
    "write_feature_cache_artifact",
    "write_feature_cache_manifest",
]
