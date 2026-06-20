"""Rapid research-only strategy iteration sandbox.

This package is intentionally isolated from the strict historical research
cycle. It triages hypotheses and can emit strict-validation requests, but it
does not create candidate evidence or promotion artifacts.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any


_EXPORTS: dict[str, str] = {
    "DataWindow": "tradingbotsuite.research_sandbox.spec",
    "EvidenceRequestDescriptor": "tradingbotsuite.research_sandbox.evidence_request",
    "ExitVariant": "tradingbotsuite.research_sandbox.spec",
    "FilterVariant": "tradingbotsuite.research_sandbox.spec",
    "FixedHoldSweepConfig": "tradingbotsuite.research_sandbox.fast_backtest",
    "ANALYSIS_REPORT_NAME": "tradingbotsuite.research_sandbox.analytics",
    "ARCHIVE_COVERAGE_MATRIX_JSON_NAME": "tradingbotsuite.research_sandbox.archive_coverage",
    "ARCHIVE_COVERAGE_MATRIX_PARQUET_NAME": "tradingbotsuite.research_sandbox.archive_coverage",
    "ARCHIVE_DESCRIPTOR_AUDIT_JSON_NAME": "tradingbotsuite.research_sandbox.archive_audit",
    "ARCHIVE_DESCRIPTOR_AUDIT_PARQUET_NAME": "tradingbotsuite.research_sandbox.archive_audit",
    "ARCHIVE_MANIFEST_BUILD_REPORT_JSON_NAME": "tradingbotsuite.research_sandbox.archive_manifest",
    "ARCHIVE_MANIFEST_BUILD_REPORT_PARQUET_NAME": "tradingbotsuite.research_sandbox.archive_manifest",
    "ARCHIVE_MANIFEST_JSON_NAME": "tradingbotsuite.research_sandbox.archive_manifest",
    "HYPOTHESIS_FALSIFICATION_JSON_NAME": "tradingbotsuite.research_sandbox.falsification",
    "HYPOTHESIS_FALSIFICATION_PARQUET_NAME": "tradingbotsuite.research_sandbox.falsification",
    "MATERIALIZED_STRATEGY_CATALOG_JSON_NAME": "tradingbotsuite.research_sandbox.strategy_catalog_materializer",
    "MATERIALIZED_STRATEGY_CATALOG_PARQUET_NAME": "tradingbotsuite.research_sandbox.strategy_catalog_materializer",
    "ResultStore": "tradingbotsuite.research_sandbox.store",
    "SANDBOX_ARTIFACT_CATALOG_JSON_NAME": "tradingbotsuite.research_sandbox.catalog",
    "SANDBOX_ARTIFACT_CATALOG_PARQUET_NAME": "tradingbotsuite.research_sandbox.catalog",
    "SANDBOX_ARTIFACT_INTEGRITY_REPORT_JSON_NAME": "tradingbotsuite.research_sandbox.integrity",
    "SANDBOX_ARTIFACT_INTEGRITY_REPORT_PARQUET_NAME": "tradingbotsuite.research_sandbox.integrity",
    "SANDBOX_BOUNDARY_FLAGS": "tradingbotsuite.research_sandbox.boundary",
    "SANDBOX_COMPATIBILITY_PREFLIGHT_JSON_NAME": "tradingbotsuite.research_sandbox.preflight",
    "SANDBOX_COMPATIBILITY_PREFLIGHT_PARQUET_NAME": "tradingbotsuite.research_sandbox.preflight",
    "SANDBOX_GLOBAL_LEADERBOARD_JSON_NAME": "tradingbotsuite.research_sandbox.leaderboard",
    "SANDBOX_GLOBAL_LEADERBOARD_PARQUET_NAME": "tradingbotsuite.research_sandbox.leaderboard",
    "SANDBOX_ITERATION_MANIFEST_JSON_NAME": "tradingbotsuite.research_sandbox.iteration",
    "SANDBOX_ITERATION_INDEX_JSON_NAME": "tradingbotsuite.research_sandbox.iteration_index",
    "SANDBOX_ITERATION_INDEX_PARQUET_NAME": "tradingbotsuite.research_sandbox.iteration_index",
    "SANDBOX_ITERATION_STEPS_PARQUET_NAME": "tradingbotsuite.research_sandbox.iteration",
    "SANDBOX_NEXT_ACTION_REPORT_JSON_NAME": "tradingbotsuite.research_sandbox.next_action",
    "SANDBOX_NEXT_ACTION_REPORT_PARQUET_NAME": "tradingbotsuite.research_sandbox.next_action",
    "SANDBOX_THROUGHPUT_ITERATION_SUMMARY_PARQUET_NAME": "tradingbotsuite.research_sandbox.throughput",
    "SANDBOX_THROUGHPUT_REPORT_JSON_NAME": "tradingbotsuite.research_sandbox.throughput",
    "SANDBOX_THROUGHPUT_STAGE_SUMMARY_PARQUET_NAME": "tradingbotsuite.research_sandbox.throughput",
    "SandboxArtifacts": "tradingbotsuite.research_sandbox.store",
    "SandboxRunResult": "tradingbotsuite.research_sandbox.runner",
    "SandboxRunSpec": "tradingbotsuite.research_sandbox.spec",
    "SandboxStrategyBlueprint": "tradingbotsuite.research_sandbox.strategy_blueprints",
    "SandboxSuiteArtifacts": "tradingbotsuite.research_sandbox.suite",
    "SandboxSuiteCase": "tradingbotsuite.research_sandbox.suite",
    "SandboxSuiteCaseResult": "tradingbotsuite.research_sandbox.suite",
    "SandboxSuiteRunResult": "tradingbotsuite.research_sandbox.suite",
    "SandboxSuiteSpec": "tradingbotsuite.research_sandbox.suite",
    "StrategyCatalogRow": "tradingbotsuite.research_sandbox.spec",
    "STRATEGY_CATALOG_BUILD_REPORT_JSON_NAME": "tradingbotsuite.research_sandbox.strategy_catalog_materializer",
    "STRATEGY_CATALOG_BUILD_REPORT_PARQUET_NAME": "tradingbotsuite.research_sandbox.strategy_catalog_materializer",
    "STRICT_VALIDATION_REQUEST_BUNDLE_JSON_NAME": "tradingbotsuite.research_sandbox.validation_bundle",
    "STRICT_VALIDATION_REQUEST_BUNDLE_PARQUET_NAME": "tradingbotsuite.research_sandbox.validation_bundle",
    "STRICT_VALIDATION_DESCRIPTOR_PREFLIGHT_JSON_NAME": "tradingbotsuite.research_sandbox.strict_validation_preflight",
    "STRICT_VALIDATION_DESCRIPTOR_PREFLIGHT_PARQUET_NAME": "tradingbotsuite.research_sandbox.strict_validation_preflight",
    "SUITE_HYPOTHESIS_FALSIFICATION_JSON_NAME": "tradingbotsuite.research_sandbox.falsification",
    "SUITE_HYPOTHESIS_FALSIFICATION_PARQUET_NAME": "tradingbotsuite.research_sandbox.falsification",
    "SUITE_STRICT_VALIDATION_REQUEST_BUNDLE_JSON_NAME": "tradingbotsuite.research_sandbox.validation_bundle",
    "SUITE_STRICT_VALIDATION_REQUEST_BUNDLE_PARQUET_NAME": "tradingbotsuite.research_sandbox.validation_bundle",
    "TrialResult": "tradingbotsuite.research_sandbox.fast_backtest",
    "VENUE_EXPANSION_REQUEST_BUNDLE_JSON_NAME": "tradingbotsuite.research_sandbox.venue_expansion_requests",
    "VENUE_EXPANSION_REQUEST_BUNDLE_PARQUET_NAME": "tradingbotsuite.research_sandbox.venue_expansion_requests",
    "VENUE_EXPANSION_CANDIDATE_MANIFEST_REPORT_JSON_NAME": (
        "tradingbotsuite.research_sandbox.venue_expansion_materializer"
    ),
    "VENUE_EXPANSION_CANDIDATE_MANIFEST_REPORT_PARQUET_NAME": (
        "tradingbotsuite.research_sandbox.venue_expansion_materializer"
    ),
    "VENUE_EXPANSION_DESCRIPTOR_CANDIDATES_JSON_NAME": (
        "tradingbotsuite.research_sandbox.venue_expansion_materializer"
    ),
    "VENUE_EXPANSION_DESCRIPTOR_CANDIDATES_PARQUET_NAME": (
        "tradingbotsuite.research_sandbox.venue_expansion_materializer"
    ),
    "VENUE_EXPANSION_MANIFEST_PATCH_DRY_RUN_JSON_NAME": (
        "tradingbotsuite.research_sandbox.venue_expansion_materializer"
    ),
    "VENUE_EXPANSION_MANIFEST_PATCH_DRY_RUN_PARQUET_NAME": (
        "tradingbotsuite.research_sandbox.venue_expansion_materializer"
    ),
    "ValidationProfile": "tradingbotsuite.research_sandbox.spec",
    "VenueArchiveDescriptor": "tradingbotsuite.research_sandbox.spec",
    "audit_sandbox_archive_descriptors": "tradingbotsuite.research_sandbox.archive_audit",
    "build_evidence_requests": "tradingbotsuite.research_sandbox.evidence_request",
    "build_sandbox_archive_manifest": "tradingbotsuite.research_sandbox.archive_manifest",
    "build_sandbox_global_leaderboard": "tradingbotsuite.research_sandbox.leaderboard",
    "build_sandbox_iteration_index": "tradingbotsuite.research_sandbox.iteration_index",
    "compile_spreadsheet_lead_frame": "tradingbotsuite.research_sandbox.strategy_blueprints",
    "compile_strategy_config_payload": "tradingbotsuite.research_sandbox.strategy_blueprints",
    "deterministic_run_id": "tradingbotsuite.research_sandbox.identity",
    "deterministic_trial_id": "tradingbotsuite.research_sandbox.identity",
    "export_sandbox_suite_validation_request_bundle": "tradingbotsuite.research_sandbox.validation_bundle",
    "export_sandbox_validation_request_bundle": "tradingbotsuite.research_sandbox.validation_bundle",
    "export_sandbox_venue_expansion_candidate_manifest": (
        "tradingbotsuite.research_sandbox.venue_expansion_materializer"
    ),
    "export_sandbox_venue_expansion_request_bundle": "tradingbotsuite.research_sandbox.venue_expansion_requests",
    "index_sandbox_artifacts": "tradingbotsuite.research_sandbox.catalog",
    "load_strategy_catalog": "tradingbotsuite.research_sandbox.intake",
    "load_market_frame": "tradingbotsuite.research_sandbox.market_data",
    "load_market_frame_for_descriptor": "tradingbotsuite.research_sandbox.market_data",
    "load_market_frames_for_descriptors": "tradingbotsuite.research_sandbox.market_data",
    "load_sandbox_run_spec": "tradingbotsuite.research_sandbox.intake",
    "load_sandbox_suite_spec": "tradingbotsuite.research_sandbox.suite",
    "load_venue_archive_descriptors": "tradingbotsuite.research_sandbox.intake",
    "materialize_strategy_signals": "tradingbotsuite.research_sandbox.strategy_blueprints",
    "materialize_sandbox_strategy_catalog": "tradingbotsuite.research_sandbox.strategy_catalog_materializer",
    "materialize_sandbox_venue_expansion_requests": (
        "tradingbotsuite.research_sandbox.venue_expansion_materializer"
    ),
    "normalize_market_frame": "tradingbotsuite.research_sandbox.market_data",
    "preflight_sandbox_compatibility": "tradingbotsuite.research_sandbox.preflight",
    "preflight_sandbox_strict_validation_descriptors": "tradingbotsuite.research_sandbox.strict_validation_preflight",
    "require_sandbox_artifact_integrity": "tradingbotsuite.research_sandbox.integrity",
    "run_sandbox_archive_sweep": "tradingbotsuite.research_sandbox.runner",
    "run_sandbox_agent_iteration": "tradingbotsuite.research_sandbox.iteration",
    "run_fixed_hold_sweep": "tradingbotsuite.research_sandbox.fast_backtest",
    "run_fixed_hold_sweep_for_venue_frames": "tradingbotsuite.research_sandbox.fast_backtest",
    "run_sandbox_suite": "tradingbotsuite.research_sandbox.suite",
    "run_sandbox_sweep": "tradingbotsuite.research_sandbox.runner",
    "sandbox_boundary_metadata": "tradingbotsuite.research_sandbox.boundary",
    "show_sandbox_next_action": "tradingbotsuite.research_sandbox.next_action",
    "summarize_sandbox_archive_coverage": "tradingbotsuite.research_sandbox.archive_coverage",
    "summarize_sandbox_hypotheses": "tradingbotsuite.research_sandbox.falsification",
    "summarize_sandbox_run": "tradingbotsuite.research_sandbox.analytics",
    "summarize_sandbox_throughput": "tradingbotsuite.research_sandbox.throughput",
    "summarize_sandbox_suite_hypotheses": "tradingbotsuite.research_sandbox.falsification",
    "verify_sandbox_artifact_integrity": "tradingbotsuite.research_sandbox.integrity",
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
