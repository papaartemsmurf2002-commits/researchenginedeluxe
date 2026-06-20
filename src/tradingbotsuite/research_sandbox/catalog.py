from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from tradingbotsuite.research_sandbox.boundary import (
    SANDBOX_BOUNDARY_FLAGS,
    require_sandbox_boundary,
    sandbox_boundary_metadata,
)
from tradingbotsuite.research_sandbox.integrity import verify_sandbox_artifact_integrity


SANDBOX_ARTIFACT_CATALOG_JSON_NAME = "sandbox_artifact_catalog.json"
SANDBOX_ARTIFACT_CATALOG_PARQUET_NAME = "sandbox_artifact_catalog.parquet"
SANDBOX_ARTIFACT_CATALOG_SIDECAR_INDEX_PARQUET_NAME = (
    "sandbox_artifact_catalog_sidecar_index.parquet"
)
SANDBOX_ARTIFACT_CATALOG_ANALYSIS_BUCKET_ROLLUPS_PARQUET_NAME = (
    "sandbox_artifact_catalog_analysis_bucket_rollups.parquet"
)
SANDBOX_ARTIFACT_CATALOG_GLOBAL_TOP_HYPOTHESES_PARQUET_NAME = (
    "sandbox_artifact_catalog_global_top_hypotheses.parquet"
)
SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUESTS_PARQUET_NAME = (
    "sandbox_artifact_catalog_global_evidence_requests.parquet"
)
SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_SOURCE_SUMMARY_PARQUET_NAME = (
    "sandbox_artifact_catalog_global_evidence_request_source_summary.parquet"
)
SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_SOURCE_PRIORITY_QUEUE_PARQUET_NAME = (
    "sandbox_artifact_catalog_global_evidence_request_source_priority_queue.parquet"
)
SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_PRIORITY_QUEUE_PARQUET_NAME = (
    "sandbox_artifact_catalog_global_evidence_request_priority_queue.parquet"
)
SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_BUCKET_QUEUE_PARQUET_NAME = (
    "sandbox_artifact_catalog_global_evidence_request_bucket_queue.parquet"
)
SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_BUCKET_REPRESENTATIVES_PARQUET_NAME = (
    "sandbox_artifact_catalog_global_evidence_request_bucket_representatives.parquet"
)
SANDBOX_ARTIFACT_CATALOG_GLOBAL_BUCKET_TOP_BUCKETS_PARQUET_NAME = (
    "sandbox_artifact_catalog_global_bucket_top_buckets.parquet"
)
SANDBOX_ARTIFACT_CATALOG_ITERATION_ACTION_PLAN_PARQUET_NAME = (
    "sandbox_artifact_catalog_iteration_agent_action_plan.parquet"
)
SANDBOX_ARTIFACT_CATALOG_ITERATION_ACTION_PLAN_BUCKET_QUEUE_PARQUET_NAME = (
    "sandbox_artifact_catalog_iteration_agent_action_plan_bucket_queue.parquet"
)
SANDBOX_ARTIFACT_CATALOG_ITERATION_ACTION_PLAN_BUCKET_REPRESENTATIVES_PARQUET_NAME = (
    "sandbox_artifact_catalog_iteration_agent_action_plan_bucket_representatives.parquet"
)
SANDBOX_ARTIFACT_CATALOG_ITERATION_VENUE_EXPANSION_GAP_WORKLIST_PARQUET_NAME = (
    "sandbox_artifact_catalog_iteration_venue_expansion_gap_worklist.parquet"
)
SANDBOX_ARTIFACT_CATALOG_REPLAY_BUCKET_QUEUE_PARQUET_NAME = (
    "sandbox_artifact_catalog_replay_batch_plan_bucket_queue.parquet"
)
SANDBOX_ARTIFACT_CATALOG_REPLAY_BUCKET_REPRESENTATIVES_PARQUET_NAME = (
    "sandbox_artifact_catalog_replay_batch_plan_bucket_representatives.parquet"
)
SANDBOX_ARTIFACT_CATALOG_STRICT_VALIDATION_BUNDLE_QUEUE_PARQUET_NAME = (
    "sandbox_artifact_catalog_strict_validation_bundle_queue.parquet"
)
SANDBOX_ARTIFACT_CATALOG_STRICT_VALIDATION_DESCRIPTOR_PARQUET_NAME = (
    "sandbox_artifact_catalog_strict_validation_descriptors.parquet"
)
SANDBOX_ARTIFACT_CATALOG_STRICT_VALIDATION_DESCRIPTOR_QUEUE_PARQUET_NAME = (
    "sandbox_artifact_catalog_strict_validation_descriptor_queue.parquet"
)
SANDBOX_ARTIFACT_CATALOG_STRICT_VALIDATION_DESCRIPTOR_BUCKET_QUEUE_PARQUET_NAME = (
    "sandbox_artifact_catalog_strict_validation_descriptor_bucket_queue.parquet"
)
SANDBOX_ARTIFACT_CATALOG_STRICT_VALIDATION_DESCRIPTOR_BUCKET_REPRESENTATIVES_PARQUET_NAME = (
    "sandbox_artifact_catalog_strict_validation_descriptor_bucket_representatives.parquet"
)
SANDBOX_ARTIFACT_CATALOG_REPLAY_BATCH_PLAN_QUEUE_LIMIT = 25
SANDBOX_ARTIFACT_CATALOG_REPLAY_BATCH_PLAN_BUCKET_QUEUE_LIMIT = 50
SANDBOX_ARTIFACT_CATALOG_REPLAY_BATCH_PLAN_BUCKET_REPRESENTATIVE_LIMIT = 5
SANDBOX_ARTIFACT_CATALOG_ITERATION_ACTION_PLAN_BUCKET_QUEUE_LIMIT = 50
SANDBOX_ARTIFACT_CATALOG_ITERATION_ACTION_PLAN_BUCKET_REPRESENTATIVE_LIMIT = 5
SANDBOX_ARTIFACT_CATALOG_STRICT_VALIDATION_BUNDLE_QUEUE_LIMIT = 25
SANDBOX_ARTIFACT_CATALOG_STRICT_VALIDATION_DESCRIPTOR_QUEUE_LIMIT = 50
SANDBOX_ARTIFACT_CATALOG_STRICT_VALIDATION_DESCRIPTOR_BUCKET_QUEUE_LIMIT = 50
SANDBOX_ARTIFACT_CATALOG_STRICT_VALIDATION_DESCRIPTOR_BUCKET_REPRESENTATIVE_LIMIT = 5
SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_PRIORITY_QUEUE_LIMIT = 50
SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_BUCKET_QUEUE_LIMIT = 75
SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_BUCKET_REPRESENTATIVE_LIMIT = 5
SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_SOURCE_SUMMARY_REPRESENTATIVE_LIMIT = 5
SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_SOURCE_PRIORITY_QUEUE_LIMIT = 50

CATALOG_SIDECAR_INDEX_PARQUET_COLUMNS = [
    "artifact_family",
    "sidecar_rank",
    "sidecar_category",
    "sidecar_name",
    "sidecar_role",
    "agent_read_order",
    "agent_read_group",
    "agent_first_read",
    "agent_navigation_hint",
    "sidecar_file_name",
    "sidecar_path",
    "sidecar_exists",
    "sidecar_size_bytes",
    "sidecar_sha256",
    "row_count",
    "empty",
    "parquet_written",
    "descriptor_only",
    "strict_validation_executed",
    "candidate_pack_written",
    "replay_command_execution_authorized",
    "strict_validation_authorized",
    "candidate_pack_write_authorized",
    *SANDBOX_BOUNDARY_FLAGS,
]

SIDECAR_AGENT_NAVIGATION_OVERRIDES = {
    "artifact_catalog": {
        "agent_read_order": 10,
        "agent_read_group": "catalog_start",
        "agent_first_read": True,
        "agent_navigation_hint": "Read first for indexed sandbox artifact paths and catalog-level counts.",
    },
    "global_evidence_request_source_priority_queue": {
        "agent_read_order": 20,
        "agent_read_group": "strict_validation_source_triage",
        "agent_first_read": True,
        "agent_navigation_hint": "Read to choose the highest-priority source venue, symbol, family, interval, and data-path coverage rows.",
    },
    "global_evidence_request_priority_queue": {
        "agent_read_order": 30,
        "agent_read_group": "strict_validation_trial_triage",
        "agent_first_read": True,
        "agent_navigation_hint": "Read to choose concrete descriptor-only evidence-request trial rows.",
    },
    "strict_validation_descriptor_queue": {
        "agent_read_order": 40,
        "agent_read_group": "strict_validation_bundle_triage",
        "agent_first_read": True,
        "agent_navigation_hint": "Read to inspect bundled strict-validation descriptors from run or suite handoffs.",
    },
    "iteration_agent_action_plan": {
        "agent_read_order": 50,
        "agent_read_group": "iteration_action_triage",
        "agent_first_read": True,
        "agent_navigation_hint": "Read to inspect next agent actions emitted by iteration indexes.",
    },
    "iteration_venue_expansion_gap_worklist": {
        "agent_read_order": 55,
        "agent_read_group": "iteration_action_triage",
        "agent_first_read": True,
        "agent_navigation_hint": "Read to inspect concrete OKX, Bybit, and Hyperliquid archive repair/add targets from iteration action plans.",
    },
    "replay_batch_plan_bucket_queue": {
        "agent_read_order": 60,
        "agent_read_group": "replay_batch_triage",
        "agent_first_read": True,
        "agent_navigation_hint": "Read to inspect archive bucket and window replay batch queues.",
    },
    "global_top_hypotheses": {
        "agent_read_order": 70,
        "agent_read_group": "leaderboard_triage",
        "agent_first_read": False,
        "agent_navigation_hint": "Read for flattened cross-run top hypothesis rows after queue triage.",
    },
    "global_bucket_top_buckets": {
        "agent_read_order": 80,
        "agent_read_group": "leaderboard_bucket_triage",
        "agent_first_read": False,
        "agent_navigation_hint": "Read for flattened cross-run venue, symbol, family, exit, and filter bucket leaders.",
    },
    "global_evidence_request_source_summary": {
        "agent_read_order": 90,
        "agent_read_group": "strict_validation_source_triage",
        "agent_first_read": False,
        "agent_navigation_hint": "Read for complete source-context counts after the source priority queue.",
    },
    "global_evidence_requests": {
        "agent_read_order": 100,
        "agent_read_group": "strict_validation_trial_triage",
        "agent_first_read": False,
        "agent_navigation_hint": "Read for the complete flattened global evidence-request rows after the priority queue.",
    },
    "strict_validation_descriptors": {
        "agent_read_order": 110,
        "agent_read_group": "strict_validation_bundle_triage",
        "agent_first_read": False,
        "agent_navigation_hint": "Read for complete cross-bundle strict-validation descriptor rows after queue triage.",
    },
}

SIDECAR_AGENT_NAVIGATION_CATEGORY_DEFAULTS = {
    "catalog": {
        "base_order": 200,
        "agent_read_group": "catalog_support",
        "agent_navigation_hint": "Read for catalog support rows.",
    },
    "strict_validation": {
        "base_order": 300,
        "agent_read_group": "strict_validation_support",
        "agent_navigation_hint": "Read for descriptor-only strict-validation support rows.",
    },
    "iteration_index": {
        "base_order": 400,
        "agent_read_group": "iteration_index_support",
        "agent_navigation_hint": "Read for iteration-index support rows.",
    },
    "replay_batch_plan": {
        "base_order": 500,
        "agent_read_group": "replay_batch_support",
        "agent_navigation_hint": "Read for replay batch planning support rows.",
    },
    "leaderboard": {
        "base_order": 600,
        "agent_read_group": "leaderboard_support",
        "agent_navigation_hint": "Read for leaderboard support rows.",
    },
    "analysis": {
        "base_order": 700,
        "agent_read_group": "analysis_support",
        "agent_navigation_hint": "Read for analysis bucket support rows.",
    },
}
ANALYSIS_BUCKET_ROLLUP_PARQUET_COLUMNS = [
    "artifact_family",
    "source_artifact_path",
    "source_artifact_path_relative",
    "source_artifact_dir",
    "source_run_id",
    "source_manifest_path",
    "source_rankings_parquet_path",
    "source_evidence_requests_json_path",
    "rollup_row_rank",
    "rollup_version",
    "rollup_type",
    "bucket_key",
    "bucket_values",
    "result_count",
    "screened_count",
    "rejected_count",
    "blocked_count",
    "status_counts",
    "positive_net_result_count",
    "evidence_request_count",
    "best_rank",
    "best_trial_id",
    "best_hypothesis_id",
    "best_family",
    "best_venue",
    "best_symbol",
    "best_exit_profile",
    "best_exit_variant_id",
    "best_filter_variant_id",
    "best_status",
    "best_score",
    "best_net_return_sum",
    "best_trade_count",
    "descriptor_only",
    "strict_validation_executed",
    "candidate_pack_written",
    "replay_command_execution_authorized",
    "strict_validation_authorized",
    "candidate_pack_write_authorized",
    *SANDBOX_BOUNDARY_FLAGS,
]
GLOBAL_TOP_HYPOTHESIS_PARQUET_COLUMNS = [
    "artifact_family",
    "source_artifact_path",
    "source_artifact_path_relative",
    "source_artifact_dir",
    "source_root_dir",
    "source_output_dir",
    "source_leaderboard_json_path",
    "source_leaderboard_parquet_path",
    "source_bucket_leaderboard_parquet_path",
    "source_run_manifest_count",
    "source_run_count",
    "source_result_count",
    "source_hypothesis_count",
    "source_decision_counts",
    "top_hypothesis_row_rank",
    "leaderboard_rank",
    "hypothesis_id",
    "family",
    "source_ids",
    "sides",
    "venues_tested",
    "symbols_tested",
    "data_families_tested",
    "holding_periods_tested",
    "exit_profiles_tested",
    "exit_variant_ids_tested",
    "filter_variant_ids_tested",
    "run_ids",
    "source_run_ids",
    "source_run_dirs",
    "source_manifest_paths",
    "run_count",
    "result_count",
    "screened_count",
    "rejected_count",
    "blocked_count",
    "best_trial_id",
    "best_run_id",
    "best_source_run_dir",
    "best_status",
    "best_rank",
    "best_score",
    "best_net_return_sum",
    "best_trade_count",
    "best_active_days",
    "best_win_rate",
    "best_max_drawdown",
    "best_venue",
    "best_symbol",
    "best_exit_variant_id",
    "best_filter_variant_id",
    "evidence_request_count",
    "evidence_request_trial_ids",
    "evidence_request_source_context_count",
    "evidence_request_source_context_limit",
    "evidence_request_source_contexts_truncated",
    "evidence_request_source_contexts",
    "blocked_reason_counts",
    "rejected_reason_counts",
    "all_reason_counts",
    "leaderboard_decision",
    "decision_reason",
    "descriptor_only",
    "strict_validation_executed",
    "candidate_pack_written",
    "replay_command_execution_authorized",
    "strict_validation_authorized",
    "candidate_pack_write_authorized",
    *SANDBOX_BOUNDARY_FLAGS,
]
GLOBAL_EVIDENCE_REQUEST_SOURCE_CONTEXT_PARQUET_COLUMNS = [
    "source_context_available",
    "source_request_id",
    "source_request_run_id",
    "source_request_run_dir",
    "source_request_manifest_path",
    "source_requested_validation",
    "source_required_evidence",
    "source_reason",
    "source_venue",
    "source_symbol",
    "source_data_family",
    "source_interval",
    "source_metric_rank",
    "source_metric_score",
    "source_metric_net_return_sum",
    "source_metric_trade_count",
    "source_metric_active_days",
    "source_venue_descriptor_id",
    "source_market_start",
    "source_market_end",
    "source_routing_mode",
    "source_data_path",
    "source_container_kind",
    "source_selected_member_suffix",
    "source_selected_member_count",
    "source_market_source",
    "source_execution_assumptions",
]
GLOBAL_EVIDENCE_REQUEST_PARQUET_COLUMNS = [
    "artifact_family",
    "source_artifact_path",
    "source_artifact_path_relative",
    "source_artifact_dir",
    "source_root_dir",
    "source_output_dir",
    "source_leaderboard_json_path",
    "source_leaderboard_parquet_path",
    "source_bucket_leaderboard_parquet_path",
    "source_run_manifest_count",
    "source_run_count",
    "source_result_count",
    "source_hypothesis_count",
    "source_decision_counts",
    "evidence_request_row_rank",
    "evidence_request_index",
    "evidence_request_trial_id",
    "source_trial_id",
    "requested_validation",
    *GLOBAL_EVIDENCE_REQUEST_SOURCE_CONTEXT_PARQUET_COLUMNS,
    "top_hypothesis_row_rank",
    "leaderboard_rank",
    "hypothesis_id",
    "family",
    "source_ids",
    "sides",
    "venues_tested",
    "symbols_tested",
    "data_families_tested",
    "holding_periods_tested",
    "exit_profiles_tested",
    "exit_variant_ids_tested",
    "filter_variant_ids_tested",
    "run_ids",
    "source_run_ids",
    "source_run_dirs",
    "source_manifest_paths",
    "run_count",
    "result_count",
    "screened_count",
    "rejected_count",
    "blocked_count",
    "best_trial_id",
    "best_run_id",
    "best_source_run_dir",
    "best_status",
    "best_rank",
    "best_score",
    "best_net_return_sum",
    "best_trade_count",
    "best_active_days",
    "best_win_rate",
    "best_max_drawdown",
    "best_venue",
    "best_symbol",
    "best_exit_variant_id",
    "best_filter_variant_id",
    "evidence_request_count",
    "leaderboard_decision",
    "decision_reason",
    "blocked_reason_counts",
    "rejected_reason_counts",
    "all_reason_counts",
    "descriptor_only",
    "strict_validation_executed",
    "candidate_pack_written",
    "replay_command_execution_authorized",
    "strict_validation_authorized",
    "candidate_pack_write_authorized",
    *SANDBOX_BOUNDARY_FLAGS,
]
GLOBAL_EVIDENCE_REQUEST_SOURCE_SUMMARY_PARQUET_COLUMNS = [
    "artifact_family",
    "summary_row_rank",
    "source_context_field",
    "source_context_value",
    "source_context_count",
    "unique_evidence_request_trial_count",
    "source_leaderboard_count",
    "source_market_start_min",
    "source_market_start_max",
    "source_market_end_min",
    "source_market_end_max",
    "best_leaderboard_rank",
    "best_score",
    "best_source_metric_rank",
    "best_source_metric_score",
    "best_source_metric_net_return_sum",
    "best_source_metric_trade_count",
    "best_evidence_request_trial_id",
    "best_source_trial_id",
    "best_hypothesis_id",
    "best_family",
    "representative_limit",
    "representative_count",
    "representative_evidence_request_trial_ids",
    "representative_source_trial_ids",
    "representative_source_request_ids",
    "representative_source_artifact_paths",
    "representative_source_leaderboard_json_paths",
    "evidence_request_count",
    "source_context_available_count",
    "source_context_missing_count",
    "descriptor_only",
    "strict_validation_executed",
    "candidate_pack_written",
    "replay_command_execution_authorized",
    "strict_validation_authorized",
    "candidate_pack_write_authorized",
    *SANDBOX_BOUNDARY_FLAGS,
]
GLOBAL_EVIDENCE_REQUEST_SOURCE_PRIORITY_QUEUE_PARQUET_COLUMNS = [
    "artifact_family",
    "queue_rank",
    "source_summary_row_rank",
    *GLOBAL_EVIDENCE_REQUEST_SOURCE_SUMMARY_PARQUET_COLUMNS[2:],
]
GLOBAL_EVIDENCE_REQUEST_PRIORITY_QUEUE_PARQUET_COLUMNS = [
    "artifact_family",
    "queue_rank",
    "source_evidence_request_row_rank",
    "evidence_request_trial_id",
    "source_trial_id",
    "requested_validation",
    *GLOBAL_EVIDENCE_REQUEST_SOURCE_CONTEXT_PARQUET_COLUMNS,
    "source_artifact_path",
    "source_artifact_path_relative",
    "source_artifact_dir",
    "source_leaderboard_json_path",
    "source_leaderboard_parquet_path",
    "source_bucket_leaderboard_parquet_path",
    "top_hypothesis_row_rank",
    "leaderboard_rank",
    "hypothesis_id",
    "family",
    "venues_tested",
    "symbols_tested",
    "data_families_tested",
    "holding_periods_tested",
    "exit_profiles_tested",
    "exit_variant_ids_tested",
    "filter_variant_ids_tested",
    "run_count",
    "result_count",
    "screened_count",
    "rejected_count",
    "blocked_count",
    "best_trial_id",
    "best_run_id",
    "best_status",
    "best_rank",
    "best_score",
    "best_net_return_sum",
    "best_trade_count",
    "best_active_days",
    "best_win_rate",
    "best_max_drawdown",
    "best_venue",
    "best_symbol",
    "best_exit_variant_id",
    "best_filter_variant_id",
    "leaderboard_decision",
    "decision_reason",
    "blocked_reason_counts",
    "rejected_reason_counts",
    "all_reason_counts",
    "descriptor_only",
    "strict_validation_executed",
    "candidate_pack_written",
    "replay_command_execution_authorized",
    "strict_validation_authorized",
    "candidate_pack_write_authorized",
    *SANDBOX_BOUNDARY_FLAGS,
]
GLOBAL_EVIDENCE_REQUEST_BUCKET_QUEUE_PARQUET_COLUMNS = [
    "artifact_family",
    "bucket_type",
    "bucket_key",
    "queue_rank",
    "requested_validation",
    "hypothesis_id",
    "family",
    "venue",
    "symbol",
    "leaderboard_decision",
    "source_context_available",
    "source_venue",
    "source_symbol",
    "source_data_family",
    "source_interval",
    "source_venue_descriptor_id",
    "source_routing_mode",
    "source_data_path",
    "evidence_request_count",
    "unique_evidence_request_trial_count",
    "unique_hypothesis_count",
    "unique_family_count",
    "source_leaderboard_count",
    "best_leaderboard_rank",
    "best_score",
    "representative_limit",
    "representative_count",
    "representative_evidence_request_trial_ids",
    "representative_hypothesis_ids",
    "representative_families",
    "representative_leaderboard_ranks",
    "descriptor_only",
    "strict_validation_executed",
    "candidate_pack_written",
    "replay_command_execution_authorized",
    "strict_validation_authorized",
    "candidate_pack_write_authorized",
    *SANDBOX_BOUNDARY_FLAGS,
]
GLOBAL_EVIDENCE_REQUEST_BUCKET_REPRESENTATIVE_PARQUET_COLUMNS = [
    "artifact_family",
    "bucket_type",
    "bucket_key",
    "bucket_queue_rank",
    "representative_rank",
    "bucket_requested_validation",
    "bucket_hypothesis_id",
    "bucket_family",
    "bucket_venue",
    "bucket_symbol",
    "bucket_leaderboard_decision",
    "bucket_source_context_available",
    "bucket_source_venue",
    "bucket_source_symbol",
    "bucket_source_data_family",
    "bucket_source_interval",
    "bucket_source_venue_descriptor_id",
    "bucket_source_routing_mode",
    "bucket_source_data_path",
    "bucket_evidence_request_count",
    "evidence_request_trial_id",
    "source_trial_id",
    "requested_validation",
    *GLOBAL_EVIDENCE_REQUEST_SOURCE_CONTEXT_PARQUET_COLUMNS,
    "source_artifact_path",
    "source_artifact_path_relative",
    "source_artifact_dir",
    "source_leaderboard_json_path",
    "source_leaderboard_parquet_path",
    "source_bucket_leaderboard_parquet_path",
    "top_hypothesis_row_rank",
    "leaderboard_rank",
    "hypothesis_id",
    "family",
    "source_ids",
    "sides",
    "venues_tested",
    "symbols_tested",
    "data_families_tested",
    "holding_periods_tested",
    "exit_profiles_tested",
    "exit_variant_ids_tested",
    "filter_variant_ids_tested",
    "run_ids",
    "source_run_ids",
    "source_run_dirs",
    "source_manifest_paths",
    "run_count",
    "result_count",
    "screened_count",
    "rejected_count",
    "blocked_count",
    "best_trial_id",
    "best_run_id",
    "best_source_run_dir",
    "best_status",
    "best_rank",
    "best_score",
    "best_net_return_sum",
    "best_trade_count",
    "best_active_days",
    "best_win_rate",
    "best_max_drawdown",
    "best_venue",
    "best_symbol",
    "best_exit_variant_id",
    "best_filter_variant_id",
    "leaderboard_decision",
    "decision_reason",
    "descriptor_only",
    "strict_validation_executed",
    "candidate_pack_written",
    "replay_command_execution_authorized",
    "strict_validation_authorized",
    "candidate_pack_write_authorized",
    *SANDBOX_BOUNDARY_FLAGS,
]
GLOBAL_BUCKET_TOP_BUCKET_PARQUET_COLUMNS = [
    "artifact_family",
    "source_artifact_path",
    "source_artifact_path_relative",
    "source_artifact_dir",
    "source_root_dir",
    "source_output_dir",
    "source_leaderboard_json_path",
    "source_leaderboard_parquet_path",
    "source_bucket_leaderboard_parquet_path",
    "source_run_manifest_count",
    "source_run_count",
    "source_result_count",
    "source_hypothesis_count",
    "source_bucket_count",
    "source_bucket_decision_counts",
    "top_bucket_row_rank",
    "bucket_leaderboard_rank",
    "bucket_type",
    "bucket_key",
    "bucket_columns",
    "bucket_values",
    "hypotheses_tested",
    "families_tested",
    "venues_tested",
    "symbols_tested",
    "exit_profiles_tested",
    "exit_variant_ids_tested",
    "filter_variant_ids_tested",
    "source_run_ids",
    "source_run_dirs",
    "source_manifest_paths",
    "run_count",
    "result_count",
    "screened_count",
    "rejected_count",
    "blocked_count",
    "positive_net_result_count",
    "evidence_request_count",
    "evidence_request_trial_ids",
    "best_trial_id",
    "best_run_id",
    "best_source_run_dir",
    "best_status",
    "best_rank",
    "best_score",
    "best_net_return_sum",
    "best_trade_count",
    "best_active_days",
    "best_win_rate",
    "best_max_drawdown",
    "best_hypothesis_id",
    "best_family",
    "best_venue",
    "best_symbol",
    "best_exit_profile",
    "best_exit_variant_id",
    "best_filter_variant_id",
    "blocked_reason_counts",
    "rejected_reason_counts",
    "all_reason_counts",
    "bucket_leaderboard_decision",
    "decision_reason",
    "descriptor_only",
    "strict_validation_executed",
    "candidate_pack_written",
    "replay_command_execution_authorized",
    "strict_validation_authorized",
    "candidate_pack_write_authorized",
    *SANDBOX_BOUNDARY_FLAGS,
]
ITERATION_ACTION_PLAN_PARQUET_COLUMNS = [
    "artifact_family",
    "source_artifact_path",
    "source_artifact_path_relative",
    "source_artifact_dir",
    "source_index_id",
    "source_root_dir",
    "source_output_dir",
    "action_plan_row_rank",
    "iteration_id",
    "run_id",
    "iteration_status",
    "next_action",
    "primary_recommended_action",
    "action",
    "action_priority",
    "action_rank",
    "is_primary_action",
    "blocked_by_prior_action",
    "reason_codes",
    "row_reason_codes",
    "source_queues",
    "input_replay_context_id",
    "input_replay_command",
    "input_replay_strategy_input_mode",
    "input_replay_venue_input_mode",
    "brief_status",
    "artifact_availability_status",
    "artifact_missing_keys",
    "iteration_manifest_path",
    "agent_brief_json_path",
    "strategy_catalog_json_path",
    "venue_archive_manifest_path",
    "action_count",
    "strategy_count",
    "descriptor_count",
    "result_count",
    "screened_count",
    "rejected_count",
    "blocked_count",
    "deduped_validation_request_count",
    "preflight_blocked_trial_estimate",
    "artifact_missing_count",
    "descriptor_only",
    "strict_validation_executed",
    "candidate_pack_written",
    "replay_command_execution_authorized",
    "strict_validation_authorized",
    "candidate_pack_write_authorized",
    *SANDBOX_BOUNDARY_FLAGS,
]
ITERATION_VENUE_EXPANSION_GAP_WORKLIST_PARQUET_COLUMNS = [
    "artifact_family",
    "source_artifact_path",
    "source_artifact_path_relative",
    "source_artifact_dir",
    "source_index_id",
    "source_root_dir",
    "source_output_dir",
    "worklist_row_rank",
    "action_plan_row_rank",
    "venue_expansion_gap_sample_rank",
    "source_gap_rank",
    "iteration_id",
    "run_id",
    "iteration_status",
    "next_action",
    "primary_recommended_action",
    "action",
    "action_priority",
    "action_rank",
    "is_primary_action",
    "blocked_by_prior_action",
    "reason_codes",
    "row_reason_codes",
    "source_queues",
    "input_replay_context_id",
    "input_replay_command",
    "input_replay_strategy_input_mode",
    "input_replay_venue_input_mode",
    "brief_status",
    "artifact_availability_status",
    "artifact_missing_keys",
    "iteration_manifest_path",
    "agent_brief_json_path",
    "strategy_catalog_json_path",
    "venue_archive_manifest_path",
    "archive_build_report_json_path",
    "archive_coverage_venue_expansion_gaps_parquet_path",
    "venue_expansion_target_venues",
    "venue_expansion_status_counts",
    "venue_expansion_action_counts",
    "venue_expansion_gap_samples_truncated",
    "iteration_action_count",
    "iteration_strategy_count",
    "iteration_archive_descriptor_count",
    "iteration_result_count",
    "iteration_screened_count",
    "iteration_rejected_count",
    "iteration_blocked_count",
    "iteration_deduped_validation_request_count",
    "iteration_preflight_blocked_trial_estimate",
    "iteration_artifact_missing_count",
    "target_venue",
    "market_symbol_key",
    "data_family",
    "interval",
    "target_bucket_key",
    "target_venue_observed",
    "target_missing",
    "target_status",
    "target_action",
    "observed_symbols",
    "source_coverage_key",
    "descriptor_count",
    "ready_descriptor_count",
    "blocked_descriptor_count",
    "ready_window_row_count",
    "ready_requested_window_row_count",
    "requested_window_filter_applied",
    "requested_window_start",
    "requested_window_end",
    "observed_window_start",
    "observed_window_end",
    "source_paths",
    "manifest_paths",
    "blocker_reason_counts",
    "descriptor_only",
    "strict_validation_executed",
    "candidate_pack_written",
    "replay_command_execution_authorized",
    "strict_validation_authorized",
    "candidate_pack_write_authorized",
    *SANDBOX_BOUNDARY_FLAGS,
]
ITERATION_ACTION_PLAN_BUCKET_QUEUE_PARQUET_COLUMNS = [
    "artifact_family",
    "bucket_type",
    "bucket_key",
    "queue_rank",
    "action",
    "source_queue",
    "action_item_count",
    "unique_iteration_count",
    "primary_action_count",
    "blocked_by_prior_action_count",
    "total_action_count",
    "total_deduped_validation_request_count",
    "total_preflight_blocked_trial_estimate",
    "total_artifact_missing_count",
    "representative_limit",
    "representative_count",
    "representative_iteration_ids",
    "representative_actions",
    "representative_source_queues",
    "descriptor_only",
    "strict_validation_executed",
    "candidate_pack_written",
    "replay_command_execution_authorized",
    "strict_validation_authorized",
    "candidate_pack_write_authorized",
    *SANDBOX_BOUNDARY_FLAGS,
]
ITERATION_ACTION_PLAN_BUCKET_REPRESENTATIVE_PARQUET_COLUMNS = [
    "artifact_family",
    "bucket_type",
    "bucket_key",
    "bucket_queue_rank",
    "representative_rank",
    "bucket_action",
    "bucket_source_queue",
    "iteration_id",
    "run_id",
    "iteration_status",
    "next_action",
    "primary_recommended_action",
    "representative_action",
    "action_priority",
    "action_rank",
    "is_primary_action",
    "blocked_by_prior_action",
    "source_queues",
    "input_replay_context_id",
    "input_replay_command",
    "input_replay_strategy_input_mode",
    "input_replay_venue_input_mode",
    "brief_status",
    "artifact_availability_status",
    "artifact_missing_keys",
    "iteration_manifest_path",
    "agent_brief_json_path",
    "strategy_catalog_json_path",
    "venue_archive_manifest_path",
    "action_count",
    "deduped_validation_request_count",
    "preflight_blocked_trial_estimate",
    "artifact_missing_count",
    "descriptor_only",
    "strict_validation_executed",
    "candidate_pack_written",
    "replay_command_execution_authorized",
    "strict_validation_authorized",
    "candidate_pack_write_authorized",
    *SANDBOX_BOUNDARY_FLAGS,
]
REPLAY_BUCKET_QUEUE_PARQUET_COLUMNS = [
    "artifact_family",
    "bucket_type",
    "bucket_key",
    "archive_bucket",
    "archive_window_bucket",
    "queue_rank",
    "artifact_count",
    "ready_artifact_count",
    "plan_artifact_count",
    "ready_source_item_count",
    "plan_item_count",
    "representative_limit",
    "representative_count",
    "representative_artifact_paths_relative",
    *SANDBOX_BOUNDARY_FLAGS,
]
REPLAY_BUCKET_REPRESENTATIVE_PARQUET_COLUMNS = [
    "artifact_family",
    "bucket_type",
    "bucket_key",
    "archive_bucket",
    "archive_window_bucket",
    "bucket_queue_rank",
    "representative_rank",
    "artifact_path",
    "artifact_path_relative",
    "artifact_dir",
    "replay_batch_plan_status",
    "bucket_ready_source_item_count",
    "bucket_plan_item_count",
    "source_worklist_item_count",
    "ready_source_item_count",
    "blocked_source_item_count",
    "suppressed_duplicate_source_item_count",
    "descriptor_only",
    "replay_command_execution_authorized",
    "strict_validation_authorized",
    "candidate_pack_write_authorized",
    *SANDBOX_BOUNDARY_FLAGS,
]
STRICT_VALIDATION_BUNDLE_QUEUE_PARQUET_COLUMNS = [
    "artifact_family",
    "queue_rank",
    "strict_validation_bundle_status",
    "artifact_kind",
    "artifact_path",
    "artifact_path_relative",
    "artifact_dir",
    "bundle_id",
    "source_scope",
    "source_dir",
    "source_manifest_path",
    "strict_validation_entrypoint",
    "strict_validation_command",
    "execution_mode",
    "descriptor_only",
    "request_count",
    "deduped_request_count",
    "duplicates_removed",
    "descriptor_count",
    "strict_validation_executed",
    "candidate_pack_written",
    "strict_validation_authorized",
    "candidate_pack_write_authorized",
    *SANDBOX_BOUNDARY_FLAGS,
]
STRICT_VALIDATION_DESCRIPTOR_PARQUET_COLUMNS = [
    "artifact_family",
    "descriptor_rank",
    "artifact_kind",
    "bundle_artifact_path",
    "bundle_artifact_path_relative",
    "bundle_artifact_dir",
    "bundle_id",
    "descriptor_id",
    "dedupe_key",
    "source_scope",
    "source_dir",
    "source_manifest_path",
    "source_request_id",
    "source_run_id",
    "source_trial_id",
    "suite_id",
    "case_id",
    "hypothesis_id",
    "family",
    "venue",
    "symbol",
    "reason",
    "requested_validation",
    "strict_validation_entrypoint",
    "strict_validation_command",
    "execution_mode",
    "descriptor_only",
    "required_evidence_count",
    "required_evidence",
    "source_metric_score",
    "source_metric_rank",
    "source_metric_net_return",
    "source_metric_expectancy",
    "source_metric_trade_count",
    "source_venue_descriptor_id",
    "source_market_start",
    "source_market_end",
    "source_routing_mode",
    "source_data_path",
    "source_container_kind",
    "source_selected_member_suffix",
    "source_selected_member_count",
    "strict_validation_executed",
    "candidate_pack_written",
    "strict_validation_authorized",
    "candidate_pack_write_authorized",
    *SANDBOX_BOUNDARY_FLAGS,
]
STRICT_VALIDATION_DESCRIPTOR_QUEUE_PARQUET_COLUMNS = [
    "artifact_family",
    "queue_rank",
    "descriptor_status",
    "artifact_kind",
    "bundle_artifact_path",
    "bundle_artifact_path_relative",
    "bundle_artifact_dir",
    "bundle_id",
    "descriptor_id",
    "dedupe_key",
    "source_scope",
    "source_dir",
    "source_manifest_path",
    "source_request_id",
    "source_run_id",
    "source_trial_id",
    "suite_id",
    "case_id",
    "hypothesis_id",
    "family",
    "venue",
    "symbol",
    "reason",
    "requested_validation",
    "strict_validation_entrypoint",
    "strict_validation_command",
    "execution_mode",
    "required_evidence_count",
    "required_evidence",
    "source_metric_score",
    "source_metric_rank",
    "source_metric_net_return",
    "source_metric_expectancy",
    "source_metric_trade_count",
    "source_venue_descriptor_id",
    "source_market_start",
    "source_market_end",
    "source_routing_mode",
    "source_data_path",
    "descriptor_only",
    "strict_validation_executed",
    "candidate_pack_written",
    "strict_validation_authorized",
    "candidate_pack_write_authorized",
    *SANDBOX_BOUNDARY_FLAGS,
]
STRICT_VALIDATION_DESCRIPTOR_BUCKET_QUEUE_PARQUET_COLUMNS = [
    "artifact_family",
    "bucket_type",
    "bucket_key",
    "queue_rank",
    "venue",
    "symbol",
    "requested_validation",
    "source_scope",
    "descriptor_count",
    "bundle_count",
    "source_trial_count",
    "top_source_metric_score",
    "representative_limit",
    "representative_count",
    "representative_descriptor_ids",
    "representative_source_trial_ids",
    "representative_bundle_ids",
    "descriptor_only",
    "strict_validation_executed",
    "candidate_pack_written",
    "strict_validation_authorized",
    "candidate_pack_write_authorized",
    *SANDBOX_BOUNDARY_FLAGS,
]
STRICT_VALIDATION_DESCRIPTOR_BUCKET_REPRESENTATIVE_PARQUET_COLUMNS = [
    "artifact_family",
    "bucket_type",
    "bucket_key",
    "bucket_queue_rank",
    "representative_rank",
    "descriptor_id",
    "bundle_id",
    "source_scope",
    "source_request_id",
    "source_run_id",
    "source_trial_id",
    "suite_id",
    "case_id",
    "hypothesis_id",
    "family",
    "venue",
    "symbol",
    "requested_validation",
    "source_metric_score",
    "source_metric_rank",
    "source_market_start",
    "source_market_end",
    "source_routing_mode",
    "source_data_path",
    "descriptor_only",
    "strict_validation_executed",
    "candidate_pack_written",
    "strict_validation_authorized",
    "candidate_pack_write_authorized",
    *SANDBOX_BOUNDARY_FLAGS,
]

KNOWN_SANDBOX_JSON_ARTIFACTS: dict[str, str] = {
    "manifest.json": "run_manifest",
    "suite_manifest.json": "suite_manifest",
    "analysis_summary.json": "run_analysis",
    "hypothesis_falsification.json": "run_hypothesis_falsification",
    "suite_hypothesis_falsification.json": "suite_hypothesis_falsification",
    "strict_validation_request_bundle.json": "run_strict_validation_request_bundle",
    "suite_strict_validation_request_bundle.json": "suite_strict_validation_request_bundle",
    "sandbox_venue_expansion_request_bundle.json": "venue_expansion_request_bundle",
    "sandbox_venue_expansion_descriptor_candidates.json": "venue_expansion_descriptor_candidates",
    "sandbox_venue_expansion_manifest_patch_dry_run.json": "venue_expansion_manifest_patch_dry_run",
    "venue_archives.json": "archive_manifest",
    "archive_manifest_build_report.json": "archive_manifest_build_report",
    "archive_coverage_matrix.json": "archive_coverage_matrix",
    "sandbox_global_leaderboard.json": "global_leaderboard",
    "strategy_catalog.json": "strategy_catalog",
    "strategy_catalog_build_report.json": "strategy_catalog_build_report",
    "sandbox_iteration_manifest.json": "agent_iteration_manifest",
    "sandbox_iteration_agent_brief.json": "agent_iteration_brief",
    "sandbox_iteration_index.json": "iteration_index",
    "sandbox_iteration_input_replay_worklist.json": "iteration_input_replay_worklist",
    "sandbox_iteration_input_replay_batch_plan.json": "iteration_input_replay_batch_plan",
    "sandbox_compatibility_preflight.json": "compatibility_preflight",
}


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _row_for_parquet(payload: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, (dict, list, tuple)):
            row[key] = json.dumps(value, sort_keys=True, default=_json_default)
        else:
            row[key] = value
    return row


def _sidecar_file_identity(
    sidecar_path: Path,
    *,
    parquet_written: bool,
) -> dict[str, Any]:
    if not parquet_written or not sidecar_path.is_file():
        return {
            "sidecar_exists": False,
            "sidecar_size_bytes": None,
            "sidecar_sha256": None,
        }

    digest = hashlib.sha256()
    with sidecar_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "sidecar_exists": True,
        "sidecar_size_bytes": int(sidecar_path.stat().st_size),
        "sidecar_sha256": digest.hexdigest(),
    }


def _catalog_sidecar_agent_navigation(
    *,
    sidecar_rank: int,
    sidecar_category: str,
    sidecar_name: str,
) -> dict[str, Any]:
    override = SIDECAR_AGENT_NAVIGATION_OVERRIDES.get(sidecar_name)
    if override is not None:
        return {
            "agent_read_order": int(override["agent_read_order"]),
            "agent_read_group": str(override["agent_read_group"]),
            "agent_first_read": bool(override["agent_first_read"]),
            "agent_navigation_hint": str(override["agent_navigation_hint"]),
        }

    fallback = SIDECAR_AGENT_NAVIGATION_CATEGORY_DEFAULTS.get(
        sidecar_category,
        {
            "base_order": 900,
            "agent_read_group": "other_support",
            "agent_navigation_hint": "Read for supporting sandbox sidecar rows.",
        },
    )
    return {
        "agent_read_order": int(fallback["base_order"]) + int(sidecar_rank),
        "agent_read_group": str(fallback["agent_read_group"]),
        "agent_first_read": False,
        "agent_navigation_hint": str(fallback["agent_navigation_hint"]),
    }


def _catalog_sidecar_index_row(
    *,
    sidecar_rank: int,
    sidecar_category: str,
    sidecar_name: str,
    sidecar_role: str,
    sidecar_path: Path,
    row_count: int,
    parquet_written: bool,
) -> dict[str, Any]:
    identity = _sidecar_file_identity(
        sidecar_path,
        parquet_written=parquet_written,
    )
    navigation = _catalog_sidecar_agent_navigation(
        sidecar_rank=sidecar_rank,
        sidecar_category=sidecar_category,
        sidecar_name=sidecar_name,
    )
    row = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_artifact_catalog_sidecar_index_row",
        "sidecar_rank": int(sidecar_rank),
        "sidecar_category": sidecar_category,
        "sidecar_name": sidecar_name,
        "sidecar_role": sidecar_role,
        "agent_read_order": navigation["agent_read_order"],
        "agent_read_group": navigation["agent_read_group"],
        "agent_first_read": navigation["agent_first_read"],
        "agent_navigation_hint": navigation["agent_navigation_hint"],
        "sidecar_file_name": sidecar_path.name,
        "sidecar_path": str(sidecar_path) if parquet_written else None,
        "sidecar_exists": identity["sidecar_exists"],
        "sidecar_size_bytes": identity["sidecar_size_bytes"],
        "sidecar_sha256": identity["sidecar_sha256"],
        "row_count": int(row_count),
        "empty": int(row_count) == 0,
        "parquet_written": bool(parquet_written),
        "descriptor_only": True,
        "strict_validation_executed": False,
        "candidate_pack_written": False,
        "replay_command_execution_authorized": False,
        "strict_validation_authorized": False,
        "candidate_pack_write_authorized": False,
    }
    require_sandbox_boundary(
        row,
        payload_name="sandbox_artifact_catalog_sidecar_index_row",
    )
    return row


def _catalog_sidecar_index_rows(
    sidecars: list[dict[str, Any]],
    *,
    write_report: bool,
) -> list[dict[str, Any]]:
    return [
        _catalog_sidecar_index_row(
            sidecar_rank=rank,
            sidecar_category=str(sidecar["sidecar_category"]),
            sidecar_name=str(sidecar["sidecar_name"]),
            sidecar_role=str(sidecar["sidecar_role"]),
            sidecar_path=Path(sidecar["sidecar_path"]),
            row_count=int(sidecar["row_count"]),
            parquet_written=write_report,
        )
        for rank, sidecar in enumerate(sidecars, start=1)
    ]


def _load_artifact(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"sandbox artifact catalog found invalid JSON: {path}") from exc
    if not isinstance(payload, dict):
        return None
    if not any(key in payload for key in SANDBOX_BOUNDARY_FLAGS):
        return None
    require_sandbox_boundary(payload, payload_name=f"sandbox_artifact_catalog_source:{path.name}")
    return payload


def _utc_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def _artifact_ids(payload: dict[str, Any], *, kind: str) -> tuple[str | None, str | None]:
    if kind == "run_manifest":
        spec = payload.get("spec", {})
        return (str(spec.get("run_id")) if isinstance(spec, dict) and spec.get("run_id") is not None else None, None)
    if kind == "suite_manifest":
        suite_spec = payload.get("suite_spec", {})
        return (
            None,
            str(suite_spec.get("suite_id")) if isinstance(suite_spec, dict) and suite_spec.get("suite_id") is not None else None,
        )
    run_id = payload.get("run_id")
    suite_id = payload.get("suite_id")
    return (
        str(run_id) if run_id is not None else None,
        str(suite_id) if suite_id is not None else None,
    )


def _count_value(payload: dict[str, Any], *names: str) -> int:
    for name in names:
        value = payload.get(name)
        if value is not None:
            return int(value)
    return 0


def _summary_count_value(payload: dict[str, Any], *names: str) -> int:
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        return 0
    for name in names:
        value = summary.get(name)
        if value is not None:
            return int(value)
    return 0


def _summary_count_map(payload: dict[str, Any], name: str) -> dict[str, int]:
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        return {}
    raw = summary.get(name)
    if not isinstance(raw, dict):
        return {}
    return {
        str(key): int(value or 0)
        for key, value in raw.items()
        if int(value or 0) > 0
    }


def _integrity_catalog_fields(path: Path, *, kind: str) -> dict[str, Any]:
    if kind not in {"run_manifest", "suite_manifest"}:
        return {
            "integrity_verification_status": "not_applicable",
            "integrity_checked_artifact_count": 0,
            "integrity_verified_artifact_count": 0,
            "integrity_failed_artifact_count": 0,
            "integrity_mismatched_artifact_count": 0,
            "integrity_missing_artifact_count": 0,
            "integrity_failure_artifact_keys": [],
            "integrity_failure_reasons": [],
        }
    try:
        report = verify_sandbox_artifact_integrity(path, write_report=False)
    except Exception as exc:
        return {
            "integrity_verification_status": "verification_error",
            "integrity_checked_artifact_count": 0,
            "integrity_verified_artifact_count": 0,
            "integrity_failed_artifact_count": 1,
            "integrity_mismatched_artifact_count": 0,
            "integrity_missing_artifact_count": 0,
            "integrity_failure_artifact_keys": [],
            "integrity_failure_reasons": [f"verification_error:{type(exc).__name__}:{exc}"],
        }
    failed_rows = [row for row in report.get("rows", []) if isinstance(row, dict) and row.get("status") != "matched"]
    failure_reasons = sorted(
        {
            str(reason)
            for row in failed_rows
            for reason in (row.get("reasons") if isinstance(row.get("reasons"), list) else [])
        }
    )
    return {
        "integrity_verification_status": report.get("verification_status"),
        "integrity_checked_artifact_count": int(report.get("checked_artifact_count", 0) or 0),
        "integrity_verified_artifact_count": int(report.get("verified_artifact_count", 0) or 0),
        "integrity_failed_artifact_count": int(report.get("failed_artifact_count", 0) or 0),
        "integrity_mismatched_artifact_count": int(report.get("mismatched_artifact_count", 0) or 0),
        "integrity_missing_artifact_count": int(report.get("missing_artifact_count", 0) or 0),
        "integrity_failure_artifact_keys": sorted(str(row.get("artifact_key")) for row in failed_rows if row.get("artifact_key")),
        "integrity_failure_reasons": failure_reasons,
    }


def _add_count(counts: dict[str, int], value: Any, *, amount: int = 1) -> None:
    if value is None or str(value) == "":
        return
    key = str(value)
    counts[key] = counts.get(key, 0) + int(amount)


def _add_list_counts(
    counts: dict[str, int],
    values: Any,
    *,
    amount: int = 1,
) -> None:
    for value in _list_value(values):
        _add_count(counts, value, amount=amount)


def _sorted_count_map(counts: dict[str, int]) -> dict[str, int]:
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _global_leaderboard_evidence_request_metadata(
    *,
    kind: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    metadata = {
        "global_evidence_request_count": 0,
        "global_evidence_request_unique_trial_count": 0,
        "global_evidence_request_hypothesis_count": 0,
        "global_evidence_request_unique_hypothesis_count": 0,
        "global_evidence_request_requested_validation_counts": {},
        "global_evidence_request_leaderboard_decision_counts": {},
        "global_evidence_request_family_counts": {},
        "global_evidence_request_tested_venue_counts": {},
        "global_evidence_request_tested_symbol_counts": {},
        "global_evidence_request_source_context_count": 0,
        "global_evidence_request_source_context_truncated_hypothesis_count": 0,
    }
    if kind != "global_leaderboard":
        return metadata

    requested_validation_counts: dict[str, int] = {}
    leaderboard_decision_counts: dict[str, int] = {}
    family_counts: dict[str, int] = {}
    tested_venue_counts: dict[str, int] = {}
    tested_symbol_counts: dict[str, int] = {}
    unique_trial_ids: set[str] = set()
    unique_hypothesis_ids: set[str] = set()
    hypothesis_count = 0
    request_count = 0
    source_context_count = 0
    source_context_truncated_hypothesis_count = 0

    for hypothesis in _list_value(payload.get("top_hypotheses")):
        if not isinstance(hypothesis, dict):
            continue
        request_ids = [
            str(trial_id)
            for trial_id in _list_value(hypothesis.get("evidence_request_trial_ids"))
            if trial_id is not None and str(trial_id) != ""
        ]
        if not request_ids:
            continue
        request_total = len(request_ids)
        source_context_count += min(
            _row_int(hypothesis, "evidence_request_source_context_count"),
            request_total,
        )
        if bool(hypothesis.get("evidence_request_source_contexts_truncated", False)):
            source_context_truncated_hypothesis_count += 1
        request_count += request_total
        unique_trial_ids.update(request_ids)
        hypothesis_count += 1
        hypothesis_id = hypothesis.get("hypothesis_id")
        if hypothesis_id is not None and str(hypothesis_id) != "":
            unique_hypothesis_ids.add(str(hypothesis_id))
        _add_count(
            requested_validation_counts,
            "strict_validation",
            amount=request_total,
        )
        _add_count(
            leaderboard_decision_counts,
            hypothesis.get("leaderboard_decision") or "unknown",
            amount=request_total,
        )
        _add_count(
            family_counts,
            hypothesis.get("family") or "unknown",
            amount=request_total,
        )
        _add_list_counts(
            tested_venue_counts,
            hypothesis.get("venues_tested"),
            amount=request_total,
        )
        _add_list_counts(
            tested_symbol_counts,
            hypothesis.get("symbols_tested"),
            amount=request_total,
        )

    metadata.update(
        {
            "global_evidence_request_count": request_count,
            "global_evidence_request_unique_trial_count": len(unique_trial_ids),
            "global_evidence_request_hypothesis_count": hypothesis_count,
            "global_evidence_request_unique_hypothesis_count": len(
                unique_hypothesis_ids
            ),
            "global_evidence_request_requested_validation_counts": _sorted_count_map(
                requested_validation_counts
            ),
            "global_evidence_request_leaderboard_decision_counts": _sorted_count_map(
                leaderboard_decision_counts
            ),
            "global_evidence_request_family_counts": _sorted_count_map(family_counts),
            "global_evidence_request_tested_venue_counts": _sorted_count_map(
                tested_venue_counts
            ),
            "global_evidence_request_tested_symbol_counts": _sorted_count_map(
                tested_symbol_counts
            ),
            "global_evidence_request_source_context_count": source_context_count,
            "global_evidence_request_source_context_truncated_hypothesis_count": (
                source_context_truncated_hypothesis_count
            ),
        }
    )
    return metadata


def _catalog_row(path: Path, *, root_dir: Path, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    run_id, suite_id = _artifact_ids(payload, kind=kind)
    row = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_artifact_catalog_row",
        "artifact_kind": kind,
        "source_artifact_family": payload.get("artifact_family"),
        "artifact_path": str(path),
        "artifact_path_relative": str(path.relative_to(root_dir)),
        "artifact_dir": str(path.parent),
        "run_id": run_id,
        "suite_id": suite_id,
        "scope": payload.get("scope"),
        "result_count": _count_value(payload, "result_count"),
        "case_count": _count_value(payload, "case_count"),
        "hypothesis_count": _count_value(payload, "hypothesis_count"),
        "global_bucket_count": _count_value(payload, "bucket_count")
        if kind == "global_leaderboard"
        else 0,
        "global_top_bucket_count": len(_list_value(payload.get("top_buckets")))
        if kind == "global_leaderboard"
        else 0,
        "global_bucket_leaderboard_parquet_path": payload.get(
            "bucket_leaderboard_parquet_path"
        )
        if kind == "global_leaderboard"
        else None,
        "global_bucket_decision_counts": _dict_value(
            payload.get("bucket_decision_counts")
        )
        if kind == "global_leaderboard"
        else {},
        "global_top_bucket_types": sorted(
            {
                str(bucket.get("bucket_type"))
                for bucket in _list_value(payload.get("top_buckets"))
                if isinstance(bucket, dict) and bucket.get("bucket_type") is not None
            }
        )
        if kind == "global_leaderboard"
        else [],
        **_global_leaderboard_evidence_request_metadata(
            kind=kind,
            payload=payload,
        ),
        "descriptor_count": _count_value(payload, "descriptor_count", "deduped_request_count"),
        "strategy_count": _count_value(payload, "strategy_count"),
        "evidence_request_count": _count_value(payload, "evidence_request_count", "request_count"),
        "analysis_bucket_rollup_count": _count_value(payload, "analysis_bucket_rollup_count")
        if kind == "run_analysis"
        else 0,
        "deduped_request_count": _count_value(payload, "deduped_request_count"),
        "duplicates_removed": _count_value(payload, "duplicates_removed"),
        "bundle_id": payload.get("bundle_id"),
        "source_dir": payload.get("source_dir"),
        "source_manifest_path": payload.get("source_manifest_path"),
        "strict_validation_request_count": _count_value(payload, "request_count"),
        "strict_validation_deduped_request_count": _count_value(payload, "deduped_request_count"),
        "strict_validation_duplicates_removed": _count_value(payload, "duplicates_removed"),
        "strict_validation_source_scope": payload.get("source_scope"),
        "strict_validation_entrypoint": payload.get("strict_validation_entrypoint"),
        "strict_validation_execution_mode": payload.get("execution_mode"),
        "source_worklist_item_count": _count_value(payload, "source_worklist_item_count"),
        "ready_source_item_count": _count_value(payload, "ready_source_item_count"),
        "blocked_source_item_count": _count_value(payload, "blocked_source_item_count"),
        "suppressed_duplicate_source_item_count": _count_value(
            payload,
            "suppressed_duplicate_source_item_count",
        ),
        "plan_item_count": _summary_count_value(payload, "plan_item_count"),
        "unique_ready_replay_context_count": _summary_count_value(
            payload,
            "unique_ready_replay_context_count",
        ),
        "ready_archive_bucket_counts": _summary_count_map(payload, "ready_archive_bucket_counts"),
        "plan_archive_bucket_counts": _summary_count_map(payload, "plan_archive_bucket_counts"),
        "ready_archive_window_bucket_counts": _summary_count_map(
            payload,
            "ready_archive_window_bucket_counts",
        ),
        "plan_archive_window_bucket_counts": _summary_count_map(
            payload,
            "plan_archive_window_bucket_counts",
        ),
        "iteration_index_id": payload.get("index_id") if kind == "iteration_index" else None,
        "iteration_count": _count_value(payload, "iteration_count")
        if kind == "iteration_index"
        else 0,
        "iteration_agent_action_plan_count": _count_value(
            payload,
            "agent_action_plan_count",
        )
        if kind == "iteration_index"
        else 0,
        "iteration_agent_action_plan_visible_count": len(
            _list_value(payload.get("agent_action_plan"))
        )
        if kind == "iteration_index"
        else 0,
        "iteration_agent_action_plan_truncated_count": _count_value(
            payload,
            "agent_action_plan_truncated_count",
        )
        if kind == "iteration_index"
        else 0,
        "iteration_agent_action_counts": _dict_value(
            _dict_value(payload.get("agent_action_plan_summary")).get("action_counts")
        )
        if kind == "iteration_index"
        else {},
        "iteration_agent_source_queue_counts": _dict_value(
            _dict_value(payload.get("agent_action_plan_summary")).get(
                "source_queue_counts"
            )
        )
        if kind == "iteration_index"
        else {},
        "iteration_action_queue_counts": _dict_value(payload.get("action_queue_counts"))
        if kind == "iteration_index"
        else {},
        "venue_expansion_materialization_id": payload.get("materialization_id")
        if kind
        in {
            "venue_expansion_descriptor_candidates",
            "venue_expansion_manifest_patch_dry_run",
        }
        else None,
        "venue_expansion_source_request_count": _count_value(payload, "source_request_count")
        if kind
        in {
            "venue_expansion_descriptor_candidates",
            "venue_expansion_manifest_patch_dry_run",
        }
        else 0,
        "venue_expansion_filtered_request_count": _count_value(payload, "filtered_request_count")
        if kind
        in {
            "venue_expansion_descriptor_candidates",
            "venue_expansion_manifest_patch_dry_run",
        }
        else 0,
        "venue_expansion_descriptor_candidate_count": _count_value(payload, "descriptor_candidate_count")
        if kind
        in {
            "venue_expansion_descriptor_candidates",
            "venue_expansion_manifest_patch_dry_run",
        }
        else 0,
        "venue_expansion_dry_run_patch_row_count": _count_value(payload, "dry_run_patch_row_count")
        if kind
        in {
            "venue_expansion_descriptor_candidates",
            "venue_expansion_manifest_patch_dry_run",
        }
        else 0,
        "venue_expansion_ready_request_count": _count_value(payload, "ready_request_count")
        if kind
        in {
            "venue_expansion_descriptor_candidates",
            "venue_expansion_manifest_patch_dry_run",
        }
        else 0,
        "venue_expansion_blocked_request_count": _count_value(payload, "blocked_request_count")
        if kind
        in {
            "venue_expansion_descriptor_candidates",
            "venue_expansion_manifest_patch_dry_run",
        }
        else 0,
        "venue_expansion_archive_file_count": _count_value(payload, "archive_file_count")
        if kind
        in {
            "venue_expansion_descriptor_candidates",
            "venue_expansion_manifest_patch_dry_run",
        }
        else 0,
        "venue_expansion_loadable_archive_file_count": _count_value(
            payload,
            "loadable_archive_file_count",
        )
        if kind
        in {
            "venue_expansion_descriptor_candidates",
            "venue_expansion_manifest_patch_dry_run",
        }
        else 0,
        "venue_expansion_archive_scan_status_counts": _dict_value(
            payload.get("archive_scan_status_counts")
        )
        if kind
        in {
            "venue_expansion_descriptor_candidates",
            "venue_expansion_manifest_patch_dry_run",
        }
        else {},
        "venue_expansion_archive_skip_reason_counts": _dict_value(
            payload.get("archive_skip_reason_counts")
        )
        if kind
        in {
            "venue_expansion_descriptor_candidates",
            "venue_expansion_manifest_patch_dry_run",
        }
        else {},
        "venue_expansion_descriptor_candidates_json_path": payload.get(
            "descriptor_candidates_json_path"
        )
        if kind
        in {
            "venue_expansion_descriptor_candidates",
            "venue_expansion_manifest_patch_dry_run",
        }
        else None,
        "venue_expansion_descriptor_candidates_parquet_path": payload.get(
            "descriptor_candidates_parquet_path"
        )
        if kind
        in {
            "venue_expansion_descriptor_candidates",
            "venue_expansion_manifest_patch_dry_run",
        }
        else None,
        "venue_expansion_manifest_patch_dry_run_json_path": payload.get(
            "manifest_patch_dry_run_json_path"
        )
        if kind
        in {
            "venue_expansion_descriptor_candidates",
            "venue_expansion_manifest_patch_dry_run",
        }
        else None,
        "venue_expansion_manifest_patch_dry_run_parquet_path": payload.get(
            "manifest_patch_dry_run_parquet_path"
        )
        if kind
        in {
            "venue_expansion_descriptor_candidates",
            "venue_expansion_manifest_patch_dry_run",
        }
        else None,
        "provider_download_authorized": bool(payload.get("provider_download_authorized", False)),
        "archive_manifest_write_authorized": bool(payload.get("archive_manifest_write_authorized", False)),
        "source_archive_mutation_authorized": bool(payload.get("source_archive_mutation_authorized", False)),
        "archive_manifest_write_executed": bool(payload.get("archive_manifest_write_executed", False)),
        "source_archive_mutation_executed": bool(payload.get("source_archive_mutation_executed", False)),
        "strict_validation_command": payload.get("strict_validation_command"),
        "strict_validation_executed": bool(payload.get("strict_validation_executed", False)),
        "candidate_pack_written": bool(payload.get("candidate_pack_written", False)),
        "descriptor_only": bool(payload.get("descriptor_only", False)),
        **_integrity_catalog_fields(path, kind=kind),
        "modified_at": _utc_mtime(path),
    }
    require_sandbox_boundary(row, payload_name="sandbox_artifact_catalog_row")
    return row


def _row_int(row: dict[str, Any], key: str) -> int:
    return int(row.get(key, 0) or 0)


def _row_count_map(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = row.get(key)
        if not isinstance(value, dict):
            continue
        for item_key, item_value in value.items():
            count = int(item_value or 0)
            if count <= 0:
                continue
            key_text = str(item_key)
            counts[key_text] = counts.get(key_text, 0) + count
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _row_map_count(row: dict[str, Any], key: str, item_key: str) -> int:
    value = row.get(key)
    if not isinstance(value, dict):
        return 0
    return int(value.get(item_key, 0) or 0)


def _dict_value(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list_value(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _global_evidence_request_source_contexts_by_trial_id(
    hypothesis: dict[str, Any],
    *,
    path: Path,
) -> dict[str, dict[str, Any]]:
    contexts: dict[str, dict[str, Any]] = {}
    for context in _list_value(hypothesis.get("evidence_request_source_contexts")):
        if not isinstance(context, dict):
            raise ValueError(
                f"sandbox global leaderboard evidence request source context must be an object: {path}"
            )
        require_sandbox_boundary(
            context,
            payload_name="sandbox_artifact_catalog_global_evidence_request_source_context",
        )
        if bool(context.get("strict_validation_authorized", False)) or bool(
            context.get("candidate_pack_write_authorized", False)
        ) or bool(context.get("candidate_pack_authorized", False)):
            raise ValueError(
                f"sandbox global leaderboard evidence request source context must not authorize validation or candidate packs: {path}"
            )
        trial_id = context.get("source_trial_id")
        if trial_id is None or str(trial_id) == "":
            continue
        contexts.setdefault(str(trial_id), context)
    return contexts


def _empty_global_evidence_request_source_context_columns() -> dict[str, Any]:
    return {
        "source_context_available": False,
        "source_request_id": None,
        "source_request_run_id": None,
        "source_request_run_dir": None,
        "source_request_manifest_path": None,
        "source_requested_validation": None,
        "source_required_evidence": [],
        "source_reason": None,
        "source_venue": None,
        "source_symbol": None,
        "source_data_family": None,
        "source_interval": None,
        "source_metric_rank": 0,
        "source_metric_score": 0.0,
        "source_metric_net_return_sum": 0.0,
        "source_metric_trade_count": 0,
        "source_metric_active_days": 0,
        "source_venue_descriptor_id": None,
        "source_market_start": None,
        "source_market_end": None,
        "source_routing_mode": None,
        "source_data_path": None,
        "source_container_kind": None,
        "source_selected_member_suffix": None,
        "source_selected_member_count": 0,
        "source_market_source": {},
        "source_execution_assumptions": {},
    }


def _global_evidence_request_source_context_columns(
    context: dict[str, Any] | None,
) -> dict[str, Any]:
    if not context:
        return _empty_global_evidence_request_source_context_columns()
    return {
        "source_context_available": True,
        "source_request_id": context.get("source_request_id"),
        "source_request_run_id": context.get("source_run_id"),
        "source_request_run_dir": context.get("source_run_dir"),
        "source_request_manifest_path": context.get("source_manifest_path"),
        "source_requested_validation": context.get("source_requested_validation"),
        "source_required_evidence": _list_value(
            context.get("source_required_evidence")
        ),
        "source_reason": context.get("source_reason"),
        "source_venue": context.get("venue")
        or _dict_value(context.get("source_market_source")).get("venue"),
        "source_symbol": context.get("symbol")
        or _dict_value(context.get("source_market_source")).get("symbol"),
        "source_data_family": context.get("data_family")
        or _dict_value(context.get("source_market_source")).get("data_family"),
        "source_interval": _dict_value(context.get("source_market_source")).get(
            "interval"
        ),
        "source_metric_rank": _row_int(context, "source_metric_rank"),
        "source_metric_score": _optional_float(
            context.get("source_metric_score")
        ),
        "source_metric_net_return_sum": _optional_float(
            context.get("source_metric_net_return_sum")
        ),
        "source_metric_trade_count": _row_int(
            context,
            "source_metric_trade_count",
        ),
        "source_metric_active_days": _row_int(
            context,
            "source_metric_active_days",
        ),
        "source_venue_descriptor_id": context.get("source_venue_descriptor_id"),
        "source_market_start": context.get("source_market_start"),
        "source_market_end": context.get("source_market_end"),
        "source_routing_mode": context.get("source_routing_mode"),
        "source_data_path": context.get("source_data_path"),
        "source_container_kind": context.get("source_container_kind"),
        "source_selected_member_suffix": context.get(
            "source_selected_member_suffix"
        ),
        "source_selected_member_count": _row_int(
            context,
            "source_selected_member_count",
        ),
        "source_market_source": _dict_value(context.get("source_market_source")),
        "source_execution_assumptions": _dict_value(
            context.get("source_execution_assumptions")
        ),
    }


def _global_evidence_request_source_context_columns_from_row(
    row: dict[str, Any],
) -> dict[str, Any]:
    values = _empty_global_evidence_request_source_context_columns()
    for key in values:
        if key in row:
            values[key] = row.get(key)
    values["source_context_available"] = bool(
        values.get("source_context_available")
    )
    values["source_required_evidence"] = _list_value(
        values.get("source_required_evidence")
    )
    values["source_market_source"] = _dict_value(
        values.get("source_market_source")
    )
    values["source_execution_assumptions"] = _dict_value(
        values.get("source_execution_assumptions")
    )
    values["source_metric_rank"] = _row_int(values, "source_metric_rank")
    values["source_metric_trade_count"] = _row_int(
        values,
        "source_metric_trade_count",
    )
    values["source_metric_active_days"] = _row_int(
        values,
        "source_metric_active_days",
    )
    values["source_selected_member_count"] = _row_int(
        values,
        "source_selected_member_count",
    )
    values["source_metric_score"] = _optional_float(
        values.get("source_metric_score")
    )
    values["source_metric_net_return_sum"] = _optional_float(
        values.get("source_metric_net_return_sum")
    )
    return values


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _analysis_bucket_rollup_parquet_rows(
    path: Path,
    *,
    root_dir: Path,
    kind: str,
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    if kind != "run_analysis":
        return []
    rows: list[dict[str, Any]] = []
    for rollup_rank, rollup in enumerate(
        _list_value(payload.get("analysis_bucket_rollups")),
        start=1,
    ):
        if not isinstance(rollup, dict):
            raise ValueError(f"sandbox analysis bucket rollup must be an object: {path}")
        require_sandbox_boundary(
            rollup,
            payload_name="sandbox_artifact_catalog_analysis_bucket_rollup_source",
        )
        if bool(rollup.get("strict_validation_authorized", False)) or bool(
            rollup.get("candidate_pack_authorized", False)
        ):
            raise ValueError(
                f"sandbox analysis bucket rollup must not authorize validation or candidate packs: {path}"
            )
        row = {
            **sandbox_boundary_metadata(),
            "artifact_family": "rapid_strategy_iteration_sandbox_artifact_catalog_analysis_bucket_rollup_parquet_row",
            "source_artifact_path": str(path),
            "source_artifact_path_relative": str(path.relative_to(root_dir)),
            "source_artifact_dir": str(path.parent),
            "source_run_id": payload.get("run_id"),
            "source_manifest_path": payload.get("source_manifest_path"),
            "source_rankings_parquet_path": payload.get("rankings_parquet_path"),
            "source_evidence_requests_json_path": payload.get("evidence_requests_json_path"),
            "rollup_row_rank": int(rollup_rank),
            "rollup_version": _optional_int(rollup.get("rollup_version")),
            "rollup_type": rollup.get("rollup_type"),
            "bucket_key": rollup.get("bucket_key"),
            "bucket_values": _dict_value(rollup.get("bucket_values")),
            "result_count": _optional_int(rollup.get("result_count")) or 0,
            "screened_count": _optional_int(rollup.get("screened_count")) or 0,
            "rejected_count": _optional_int(rollup.get("rejected_count")) or 0,
            "blocked_count": _optional_int(rollup.get("blocked_count")) or 0,
            "status_counts": _dict_value(rollup.get("status_counts")),
            "positive_net_result_count": _optional_int(
                rollup.get("positive_net_result_count")
            )
            or 0,
            "evidence_request_count": _optional_int(rollup.get("evidence_request_count"))
            or 0,
            "best_rank": _optional_int(rollup.get("best_rank")),
            "best_trial_id": rollup.get("best_trial_id"),
            "best_hypothesis_id": rollup.get("best_hypothesis_id"),
            "best_family": rollup.get("best_family"),
            "best_venue": rollup.get("best_venue"),
            "best_symbol": rollup.get("best_symbol"),
            "best_exit_profile": rollup.get("best_exit_profile"),
            "best_exit_variant_id": rollup.get("best_exit_variant_id"),
            "best_filter_variant_id": rollup.get("best_filter_variant_id"),
            "best_status": rollup.get("best_status"),
            "best_score": _optional_float(rollup.get("best_score")),
            "best_net_return_sum": _optional_float(rollup.get("best_net_return_sum")),
            "best_trade_count": _optional_int(rollup.get("best_trade_count")),
            "descriptor_only": True,
            "strict_validation_executed": False,
            "candidate_pack_written": False,
            "replay_command_execution_authorized": False,
            "strict_validation_authorized": False,
            "candidate_pack_write_authorized": False,
        }
        require_sandbox_boundary(
            row,
            payload_name="sandbox_artifact_catalog_analysis_bucket_rollup_parquet_row",
        )
        rows.append(row)
    return rows


def _global_top_hypothesis_parquet_rows(
    path: Path,
    *,
    root_dir: Path,
    kind: str,
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    if kind != "global_leaderboard":
        return []
    rows: list[dict[str, Any]] = []
    for hypothesis_rank, hypothesis in enumerate(
        _list_value(payload.get("top_hypotheses")),
        start=1,
    ):
        if not isinstance(hypothesis, dict):
            raise ValueError(f"sandbox global leaderboard top hypothesis must be an object: {path}")
        require_sandbox_boundary(
            hypothesis,
            payload_name="sandbox_artifact_catalog_global_top_hypothesis_source",
        )
        if bool(hypothesis.get("strict_validation_authorized", False)) or bool(
            hypothesis.get("candidate_pack_write_authorized", False)
        ) or bool(hypothesis.get("candidate_pack_authorized", False)):
            raise ValueError(
                f"sandbox global leaderboard top hypothesis must not authorize validation or candidate packs: {path}"
            )
        row = {
            **sandbox_boundary_metadata(),
            "artifact_family": "rapid_strategy_iteration_sandbox_artifact_catalog_global_top_hypothesis_parquet_row",
            "source_artifact_path": str(path),
            "source_artifact_path_relative": str(path.relative_to(root_dir)),
            "source_artifact_dir": str(path.parent),
            "source_root_dir": payload.get("root_dir"),
            "source_output_dir": payload.get("output_dir"),
            "source_leaderboard_json_path": payload.get("leaderboard_json_path"),
            "source_leaderboard_parquet_path": payload.get("leaderboard_parquet_path"),
            "source_bucket_leaderboard_parquet_path": payload.get(
                "bucket_leaderboard_parquet_path"
            ),
            "source_run_manifest_count": _count_value(payload, "run_manifest_count"),
            "source_run_count": _count_value(payload, "source_run_count"),
            "source_result_count": _count_value(payload, "result_count"),
            "source_hypothesis_count": _count_value(payload, "hypothesis_count"),
            "source_decision_counts": _dict_value(payload.get("decision_counts")),
            "top_hypothesis_row_rank": int(hypothesis_rank),
            "leaderboard_rank": _row_int(hypothesis, "leaderboard_rank"),
            "hypothesis_id": hypothesis.get("hypothesis_id"),
            "family": hypothesis.get("family"),
            "source_ids": _list_value(hypothesis.get("source_ids")),
            "sides": _list_value(hypothesis.get("sides")),
            "venues_tested": _list_value(hypothesis.get("venues_tested")),
            "symbols_tested": _list_value(hypothesis.get("symbols_tested")),
            "data_families_tested": _list_value(
                hypothesis.get("data_families_tested")
            ),
            "holding_periods_tested": _list_value(
                hypothesis.get("holding_periods_tested")
            ),
            "exit_profiles_tested": _list_value(
                hypothesis.get("exit_profiles_tested")
            ),
            "exit_variant_ids_tested": _list_value(
                hypothesis.get("exit_variant_ids_tested")
            ),
            "filter_variant_ids_tested": _list_value(
                hypothesis.get("filter_variant_ids_tested")
            ),
            "run_ids": _list_value(hypothesis.get("run_ids")),
            "source_run_ids": _list_value(hypothesis.get("source_run_ids")),
            "source_run_dirs": _list_value(hypothesis.get("source_run_dirs")),
            "source_manifest_paths": _list_value(
                hypothesis.get("source_manifest_paths")
            ),
            "run_count": _row_int(hypothesis, "run_count"),
            "result_count": _row_int(hypothesis, "result_count"),
            "screened_count": _row_int(hypothesis, "screened_count"),
            "rejected_count": _row_int(hypothesis, "rejected_count"),
            "blocked_count": _row_int(hypothesis, "blocked_count"),
            "best_trial_id": hypothesis.get("best_trial_id"),
            "best_run_id": hypothesis.get("best_run_id"),
            "best_source_run_dir": hypothesis.get("best_source_run_dir"),
            "best_status": hypothesis.get("best_status"),
            "best_rank": _row_int(hypothesis, "best_rank"),
            "best_score": _optional_float(hypothesis.get("best_score")),
            "best_net_return_sum": _optional_float(
                hypothesis.get("best_net_return_sum")
            ),
            "best_trade_count": _row_int(hypothesis, "best_trade_count"),
            "best_active_days": _row_int(hypothesis, "best_active_days"),
            "best_win_rate": _optional_float(hypothesis.get("best_win_rate")),
            "best_max_drawdown": _optional_float(
                hypothesis.get("best_max_drawdown")
            ),
            "best_venue": hypothesis.get("best_venue"),
            "best_symbol": hypothesis.get("best_symbol"),
            "best_exit_variant_id": hypothesis.get("best_exit_variant_id"),
            "best_filter_variant_id": hypothesis.get("best_filter_variant_id"),
            "evidence_request_count": _row_int(hypothesis, "evidence_request_count"),
            "evidence_request_trial_ids": _list_value(
                hypothesis.get("evidence_request_trial_ids")
            ),
            "evidence_request_source_context_count": _row_int(
                hypothesis,
                "evidence_request_source_context_count",
            ),
            "evidence_request_source_context_limit": _row_int(
                hypothesis,
                "evidence_request_source_context_limit",
            ),
            "evidence_request_source_contexts_truncated": bool(
                hypothesis.get("evidence_request_source_contexts_truncated", False)
            ),
            "evidence_request_source_contexts": _list_value(
                hypothesis.get("evidence_request_source_contexts")
            ),
            "blocked_reason_counts": _dict_value(
                hypothesis.get("blocked_reason_counts")
            ),
            "rejected_reason_counts": _dict_value(
                hypothesis.get("rejected_reason_counts")
            ),
            "all_reason_counts": _dict_value(hypothesis.get("all_reason_counts")),
            "leaderboard_decision": hypothesis.get("leaderboard_decision"),
            "decision_reason": hypothesis.get("decision_reason"),
            "descriptor_only": True,
            "strict_validation_executed": False,
            "candidate_pack_written": False,
            "replay_command_execution_authorized": False,
            "strict_validation_authorized": False,
            "candidate_pack_write_authorized": False,
        }
        require_sandbox_boundary(
            row,
            payload_name="sandbox_artifact_catalog_global_top_hypothesis_parquet_row",
        )
        rows.append(row)
    return rows


def _global_evidence_request_parquet_rows(
    path: Path,
    *,
    root_dir: Path,
    kind: str,
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    if kind != "global_leaderboard":
        return []
    rows: list[dict[str, Any]] = []
    for hypothesis_rank, hypothesis in enumerate(
        _list_value(payload.get("top_hypotheses")),
        start=1,
    ):
        if not isinstance(hypothesis, dict):
            raise ValueError(f"sandbox global leaderboard top hypothesis must be an object: {path}")
        require_sandbox_boundary(
            hypothesis,
            payload_name="sandbox_artifact_catalog_global_evidence_request_source",
        )
        if bool(hypothesis.get("strict_validation_authorized", False)) or bool(
            hypothesis.get("candidate_pack_write_authorized", False)
        ) or bool(hypothesis.get("candidate_pack_authorized", False)):
            raise ValueError(
                f"sandbox global leaderboard evidence request source must not authorize validation or candidate packs: {path}"
            )
        source_contexts_by_trial_id = (
            _global_evidence_request_source_contexts_by_trial_id(
                hypothesis,
                path=path,
            )
        )
        for request_index, request_trial_id in enumerate(
            _list_value(hypothesis.get("evidence_request_trial_ids")),
            start=1,
        ):
            if request_trial_id is None or str(request_trial_id) == "":
                raise ValueError(
                    f"sandbox global leaderboard evidence request trial id must be non-empty: {path}"
                )
            request_trial_id_text = str(request_trial_id)
            source_context_columns = _global_evidence_request_source_context_columns(
                source_contexts_by_trial_id.get(request_trial_id_text)
            )
            row = {
                **sandbox_boundary_metadata(),
                "artifact_family": "rapid_strategy_iteration_sandbox_artifact_catalog_global_evidence_request_parquet_row",
                "source_artifact_path": str(path),
                "source_artifact_path_relative": str(path.relative_to(root_dir)),
                "source_artifact_dir": str(path.parent),
                "source_root_dir": payload.get("root_dir"),
                "source_output_dir": payload.get("output_dir"),
                "source_leaderboard_json_path": payload.get("leaderboard_json_path"),
                "source_leaderboard_parquet_path": payload.get("leaderboard_parquet_path"),
                "source_bucket_leaderboard_parquet_path": payload.get(
                    "bucket_leaderboard_parquet_path"
                ),
                "source_run_manifest_count": _count_value(payload, "run_manifest_count"),
                "source_run_count": _count_value(payload, "source_run_count"),
                "source_result_count": _count_value(payload, "result_count"),
                "source_hypothesis_count": _count_value(payload, "hypothesis_count"),
                "source_decision_counts": _dict_value(payload.get("decision_counts")),
                "evidence_request_row_rank": len(rows) + 1,
                "evidence_request_index": int(request_index),
                "evidence_request_trial_id": request_trial_id_text,
                "source_trial_id": request_trial_id_text,
                "requested_validation": "strict_validation",
                **source_context_columns,
                "top_hypothesis_row_rank": int(hypothesis_rank),
                "leaderboard_rank": _row_int(hypothesis, "leaderboard_rank"),
                "hypothesis_id": hypothesis.get("hypothesis_id"),
                "family": hypothesis.get("family"),
                "source_ids": _list_value(hypothesis.get("source_ids")),
                "sides": _list_value(hypothesis.get("sides")),
                "venues_tested": _list_value(hypothesis.get("venues_tested")),
                "symbols_tested": _list_value(hypothesis.get("symbols_tested")),
                "data_families_tested": _list_value(
                    hypothesis.get("data_families_tested")
                ),
                "holding_periods_tested": _list_value(
                    hypothesis.get("holding_periods_tested")
                ),
                "exit_profiles_tested": _list_value(
                    hypothesis.get("exit_profiles_tested")
                ),
                "exit_variant_ids_tested": _list_value(
                    hypothesis.get("exit_variant_ids_tested")
                ),
                "filter_variant_ids_tested": _list_value(
                    hypothesis.get("filter_variant_ids_tested")
                ),
                "run_ids": _list_value(hypothesis.get("run_ids")),
                "source_run_ids": _list_value(hypothesis.get("source_run_ids")),
                "source_run_dirs": _list_value(hypothesis.get("source_run_dirs")),
                "source_manifest_paths": _list_value(
                    hypothesis.get("source_manifest_paths")
                ),
                "run_count": _row_int(hypothesis, "run_count"),
                "result_count": _row_int(hypothesis, "result_count"),
                "screened_count": _row_int(hypothesis, "screened_count"),
                "rejected_count": _row_int(hypothesis, "rejected_count"),
                "blocked_count": _row_int(hypothesis, "blocked_count"),
                "best_trial_id": hypothesis.get("best_trial_id"),
                "best_run_id": hypothesis.get("best_run_id"),
                "best_source_run_dir": hypothesis.get("best_source_run_dir"),
                "best_status": hypothesis.get("best_status"),
                "best_rank": _row_int(hypothesis, "best_rank"),
                "best_score": _optional_float(hypothesis.get("best_score")),
                "best_net_return_sum": _optional_float(
                    hypothesis.get("best_net_return_sum")
                ),
                "best_trade_count": _row_int(hypothesis, "best_trade_count"),
                "best_active_days": _row_int(hypothesis, "best_active_days"),
                "best_win_rate": _optional_float(hypothesis.get("best_win_rate")),
                "best_max_drawdown": _optional_float(
                    hypothesis.get("best_max_drawdown")
                ),
                "best_venue": hypothesis.get("best_venue"),
                "best_symbol": hypothesis.get("best_symbol"),
                "best_exit_variant_id": hypothesis.get("best_exit_variant_id"),
                "best_filter_variant_id": hypothesis.get("best_filter_variant_id"),
                "evidence_request_count": _row_int(
                    hypothesis,
                    "evidence_request_count",
                ),
                "leaderboard_decision": hypothesis.get("leaderboard_decision"),
                "decision_reason": hypothesis.get("decision_reason"),
                "blocked_reason_counts": _dict_value(
                    hypothesis.get("blocked_reason_counts")
                ),
                "rejected_reason_counts": _dict_value(
                    hypothesis.get("rejected_reason_counts")
                ),
                "all_reason_counts": _dict_value(hypothesis.get("all_reason_counts")),
                "descriptor_only": True,
                "strict_validation_executed": False,
                "candidate_pack_written": False,
                "replay_command_execution_authorized": False,
                "strict_validation_authorized": False,
                "candidate_pack_write_authorized": False,
            }
            require_sandbox_boundary(
                row,
                payload_name="sandbox_artifact_catalog_global_evidence_request_parquet_row",
            )
            rows.append(row)
    return rows


def _score_sort_value(value: Any) -> float:
    if value is None:
        return float("inf")
    return -float(value)


def _global_evidence_request_priority_queue(
    rows: list[dict[str, Any]],
    *,
    limit: int = SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_PRIORITY_QUEUE_LIMIT,
) -> list[dict[str, Any]]:
    sorted_rows: list[dict[str, Any]] = []
    for row in rows:
        require_sandbox_boundary(
            row,
            payload_name="sandbox_artifact_catalog_global_evidence_request_priority_source",
        )
        if bool(row.get("strict_validation_authorized", False)) or bool(
            row.get("candidate_pack_write_authorized", False)
        ):
            raise ValueError(
                "sandbox global evidence request priority source must not authorize validation or candidate packs"
            )
        sorted_rows.append(row)

    sorted_rows = sorted(
        sorted_rows,
        key=lambda row: (
            _row_int(row, "leaderboard_rank"),
            _score_sort_value(row.get("best_score")),
            _row_int(row, "evidence_request_row_rank"),
            str(row.get("source_artifact_path") or ""),
            str(row.get("evidence_request_trial_id") or ""),
        ),
    )

    queue: list[dict[str, Any]] = []
    for queue_rank, source_row in enumerate(sorted_rows[:limit], start=1):
        source_context_columns = (
            _global_evidence_request_source_context_columns_from_row(source_row)
        )
        row = {
            **sandbox_boundary_metadata(),
            "artifact_family": "rapid_strategy_iteration_sandbox_artifact_catalog_global_evidence_request_priority_queue_row",
            "queue_rank": int(queue_rank),
            "source_evidence_request_row_rank": _row_int(
                source_row,
                "evidence_request_row_rank",
            ),
            "evidence_request_trial_id": source_row.get("evidence_request_trial_id"),
            "source_trial_id": source_row.get("source_trial_id"),
            "requested_validation": source_row.get("requested_validation"),
            **source_context_columns,
            "source_artifact_path": source_row.get("source_artifact_path"),
            "source_artifact_path_relative": source_row.get(
                "source_artifact_path_relative"
            ),
            "source_artifact_dir": source_row.get("source_artifact_dir"),
            "source_leaderboard_json_path": source_row.get(
                "source_leaderboard_json_path"
            ),
            "source_leaderboard_parquet_path": source_row.get(
                "source_leaderboard_parquet_path"
            ),
            "source_bucket_leaderboard_parquet_path": source_row.get(
                "source_bucket_leaderboard_parquet_path"
            ),
            "top_hypothesis_row_rank": _row_int(
                source_row,
                "top_hypothesis_row_rank",
            ),
            "leaderboard_rank": _row_int(source_row, "leaderboard_rank"),
            "hypothesis_id": source_row.get("hypothesis_id"),
            "family": source_row.get("family"),
            "venues_tested": _list_value(source_row.get("venues_tested")),
            "symbols_tested": _list_value(source_row.get("symbols_tested")),
            "data_families_tested": _list_value(
                source_row.get("data_families_tested")
            ),
            "holding_periods_tested": _list_value(
                source_row.get("holding_periods_tested")
            ),
            "exit_profiles_tested": _list_value(
                source_row.get("exit_profiles_tested")
            ),
            "exit_variant_ids_tested": _list_value(
                source_row.get("exit_variant_ids_tested")
            ),
            "filter_variant_ids_tested": _list_value(
                source_row.get("filter_variant_ids_tested")
            ),
            "run_count": _row_int(source_row, "run_count"),
            "result_count": _row_int(source_row, "result_count"),
            "screened_count": _row_int(source_row, "screened_count"),
            "rejected_count": _row_int(source_row, "rejected_count"),
            "blocked_count": _row_int(source_row, "blocked_count"),
            "best_trial_id": source_row.get("best_trial_id"),
            "best_run_id": source_row.get("best_run_id"),
            "best_status": source_row.get("best_status"),
            "best_rank": _row_int(source_row, "best_rank"),
            "best_score": _optional_float(source_row.get("best_score")),
            "best_net_return_sum": _optional_float(
                source_row.get("best_net_return_sum")
            ),
            "best_trade_count": _row_int(source_row, "best_trade_count"),
            "best_active_days": _row_int(source_row, "best_active_days"),
            "best_win_rate": _optional_float(source_row.get("best_win_rate")),
            "best_max_drawdown": _optional_float(
                source_row.get("best_max_drawdown")
            ),
            "best_venue": source_row.get("best_venue"),
            "best_symbol": source_row.get("best_symbol"),
            "best_exit_variant_id": source_row.get("best_exit_variant_id"),
            "best_filter_variant_id": source_row.get("best_filter_variant_id"),
            "leaderboard_decision": source_row.get("leaderboard_decision"),
            "decision_reason": source_row.get("decision_reason"),
            "blocked_reason_counts": _dict_value(
                source_row.get("blocked_reason_counts")
            ),
            "rejected_reason_counts": _dict_value(
                source_row.get("rejected_reason_counts")
            ),
            "all_reason_counts": _dict_value(source_row.get("all_reason_counts")),
            "descriptor_only": True,
            "strict_validation_executed": False,
            "candidate_pack_written": False,
            "replay_command_execution_authorized": False,
            "strict_validation_authorized": False,
            "candidate_pack_write_authorized": False,
        }
        require_sandbox_boundary(
            row,
            payload_name="sandbox_artifact_catalog_global_evidence_request_priority_queue_row",
        )
        queue.append(row)
    return queue


def _unique_text_values(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return sorted({str(value) for value in values if value is not None and str(value) != ""})


def _text_value(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text != "" else None


def _global_evidence_request_bucket_memberships(
    row: dict[str, Any],
) -> list[tuple[str, str, dict[str, Any]]]:
    memberships: list[tuple[str, str, dict[str, Any]]] = []

    def add(bucket_type: str, bucket_key: str, fields: dict[str, Any]) -> None:
        memberships.append((bucket_type, bucket_key, fields))

    requested_validation = str(row.get("requested_validation") or "unknown")
    hypothesis_id = str(row.get("hypothesis_id") or "unknown")
    family = str(row.get("family") or "unknown")
    leaderboard_decision = str(row.get("leaderboard_decision") or "unknown")
    venues = _unique_text_values(row.get("venues_tested"))
    symbols = _unique_text_values(row.get("symbols_tested"))
    source_context_available = bool(row.get("source_context_available", False))
    source_venue = _text_value(row.get("source_venue"))
    source_symbol = _text_value(row.get("source_symbol"))
    source_data_family = _text_value(row.get("source_data_family"))
    source_interval = _text_value(row.get("source_interval"))
    source_venue_descriptor_id = _text_value(row.get("source_venue_descriptor_id"))
    source_routing_mode = _text_value(row.get("source_routing_mode"))
    source_data_path = _text_value(row.get("source_data_path"))

    add(
        "requested_validation",
        f"requested_validation={requested_validation}",
        {"requested_validation": requested_validation},
    )
    add(
        "hypothesis",
        f"hypothesis_id={hypothesis_id}",
        {"hypothesis_id": hypothesis_id},
    )
    add("family", f"family={family}", {"family": family})
    add(
        "leaderboard_decision",
        f"leaderboard_decision={leaderboard_decision}",
        {"leaderboard_decision": leaderboard_decision},
    )
    for venue in venues:
        add("tested_venue", f"tested_venue={venue}", {"venue": venue})
        add(
            "tested_venue_family",
            f"tested_venue={venue}|family={family}",
            {"venue": venue, "family": family},
        )
    for symbol in symbols:
        add("tested_symbol", f"tested_symbol={symbol}", {"symbol": symbol})
    for venue in venues:
        for symbol in symbols:
            add(
                "tested_venue_symbol",
                f"tested_venue={venue}|tested_symbol={symbol}",
                {"venue": venue, "symbol": symbol},
            )

    if source_context_available:
        context_fields = {"source_context_available": True}
        if source_venue is not None:
            add(
                "source_venue",
                f"source_venue={source_venue}",
                {**context_fields, "source_venue": source_venue},
            )
            add(
                "source_venue_family",
                f"source_venue={source_venue}|family={family}",
                {
                    **context_fields,
                    "source_venue": source_venue,
                    "family": family,
                },
            )
        if source_symbol is not None:
            add(
                "source_symbol",
                f"source_symbol={source_symbol}",
                {**context_fields, "source_symbol": source_symbol},
            )
        if source_venue is not None and source_symbol is not None:
            add(
                "source_venue_symbol",
                f"source_venue={source_venue}|source_symbol={source_symbol}",
                {
                    **context_fields,
                    "source_venue": source_venue,
                    "source_symbol": source_symbol,
                },
            )
        if source_data_family is not None:
            add(
                "source_data_family",
                f"source_data_family={source_data_family}",
                {**context_fields, "source_data_family": source_data_family},
            )
        if source_interval is not None:
            add(
                "source_interval",
                f"source_interval={source_interval}",
                {**context_fields, "source_interval": source_interval},
            )
        if source_venue_descriptor_id is not None:
            add(
                "source_venue_descriptor",
                f"source_venue_descriptor_id={source_venue_descriptor_id}",
                {
                    **context_fields,
                    "source_venue_descriptor_id": source_venue_descriptor_id,
                },
            )
        if source_routing_mode is not None:
            add(
                "source_routing_mode",
                f"source_routing_mode={source_routing_mode}",
                {**context_fields, "source_routing_mode": source_routing_mode},
            )
        if source_data_path is not None:
            add(
                "source_data_path",
                f"source_data_path={source_data_path}",
                {**context_fields, "source_data_path": source_data_path},
            )
    return memberships


def _ordered_unique_row_values(rows: list[dict[str, Any]], key: str) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for row in rows:
        value = row.get(key)
        if value is None or str(value) == "":
            continue
        value_text = str(value)
        if value_text in seen:
            continue
        seen.add(value_text)
        values.append(value_text)
    return values


def _global_evidence_request_bucket_queue(
    rows: list[dict[str, Any]],
    *,
    limit: int = SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_BUCKET_QUEUE_LIMIT,
    representative_limit: int = SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_BUCKET_REPRESENTATIVE_LIMIT,
) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        require_sandbox_boundary(
            row,
            payload_name="sandbox_artifact_catalog_global_evidence_request_bucket_source",
        )
        if bool(row.get("strict_validation_authorized", False)) or bool(
            row.get("candidate_pack_write_authorized", False)
        ):
            raise ValueError(
                "sandbox global evidence request bucket source must not authorize validation or candidate packs"
            )
        for bucket_type, bucket_key, fields in _global_evidence_request_bucket_memberships(row):
            bucket = buckets.setdefault(
                (bucket_type, bucket_key),
                {
                    "bucket_type": bucket_type,
                    "bucket_key": bucket_key,
                    "fields": fields,
                    "rows": [],
                },
            )
            bucket["rows"].append(row)

    queue_rows: list[dict[str, Any]] = []
    for bucket in buckets.values():
        bucket_rows = sorted(
            bucket["rows"],
            key=lambda row: (
                _row_int(row, "leaderboard_rank"),
                _row_int(row, "evidence_request_row_rank"),
                str(row.get("evidence_request_trial_id") or ""),
            ),
        )
        representatives = bucket_rows[:representative_limit]
        scores = [
            float(row["best_score"])
            for row in bucket_rows
            if row.get("best_score") is not None
        ]
        fields = dict(bucket["fields"])
        queue_rows.append(
            {
                **sandbox_boundary_metadata(),
                "artifact_family": "rapid_strategy_iteration_sandbox_artifact_catalog_global_evidence_request_bucket_queue_row",
                "bucket_type": bucket["bucket_type"],
                "bucket_key": bucket["bucket_key"],
                "queue_rank": 0,
                "requested_validation": fields.get("requested_validation"),
                "hypothesis_id": fields.get("hypothesis_id"),
                "family": fields.get("family"),
                "venue": fields.get("venue"),
                "symbol": fields.get("symbol"),
                "leaderboard_decision": fields.get("leaderboard_decision"),
                "source_context_available": bool(
                    fields.get("source_context_available", False)
                ),
                "source_venue": fields.get("source_venue"),
                "source_symbol": fields.get("source_symbol"),
                "source_data_family": fields.get("source_data_family"),
                "source_interval": fields.get("source_interval"),
                "source_venue_descriptor_id": fields.get(
                    "source_venue_descriptor_id"
                ),
                "source_routing_mode": fields.get("source_routing_mode"),
                "source_data_path": fields.get("source_data_path"),
                "evidence_request_count": len(bucket_rows),
                "unique_evidence_request_trial_count": len(
                    set(_ordered_unique_row_values(bucket_rows, "evidence_request_trial_id"))
                ),
                "unique_hypothesis_count": len(
                    set(_ordered_unique_row_values(bucket_rows, "hypothesis_id"))
                ),
                "unique_family_count": len(
                    set(_ordered_unique_row_values(bucket_rows, "family"))
                ),
                "source_leaderboard_count": len(
                    set(_ordered_unique_row_values(bucket_rows, "source_artifact_path"))
                ),
                "best_leaderboard_rank": min(
                    _row_int(row, "leaderboard_rank") for row in bucket_rows
                ),
                "best_score": max(scores) if scores else None,
                "representative_limit": representative_limit,
                "representative_count": len(representatives),
                "representative_evidence_request_trial_ids": _ordered_unique_row_values(
                    representatives,
                    "evidence_request_trial_id",
                ),
                "representative_hypothesis_ids": _ordered_unique_row_values(
                    representatives,
                    "hypothesis_id",
                ),
                "representative_families": _ordered_unique_row_values(
                    representatives,
                    "family",
                ),
                "representative_leaderboard_ranks": [
                    _row_int(row, "leaderboard_rank") for row in representatives
                ],
                "descriptor_only": True,
                "strict_validation_executed": False,
                "candidate_pack_written": False,
                "replay_command_execution_authorized": False,
                "strict_validation_authorized": False,
                "candidate_pack_write_authorized": False,
            }
        )

    queue_rows = sorted(
        queue_rows,
        key=lambda row: (
            -_row_int(row, "unique_evidence_request_trial_count"),
            -_row_int(row, "evidence_request_count"),
            _row_int(row, "best_leaderboard_rank"),
            str(row.get("bucket_type") or ""),
            str(row.get("bucket_key") or ""),
        ),
    )[:limit]
    for queue_rank, row in enumerate(queue_rows, start=1):
        row["queue_rank"] = queue_rank
        require_sandbox_boundary(
            row,
            payload_name="sandbox_artifact_catalog_global_evidence_request_bucket_queue_row",
        )
    return queue_rows


def _global_evidence_request_bucket_representative_parquet_rows(
    bucket_queue: list[dict[str, Any]],
    request_rows: list[dict[str, Any]],
    *,
    representative_limit: int = SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_BUCKET_REPRESENTATIVE_LIMIT,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    request_rows_by_bucket: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for request_row in request_rows:
        require_sandbox_boundary(
            request_row,
            payload_name="sandbox_artifact_catalog_global_evidence_request_bucket_representative_source",
        )
        if bool(request_row.get("strict_validation_authorized", False)) or bool(
            request_row.get("candidate_pack_write_authorized", False)
        ):
            raise ValueError(
                "sandbox global evidence request representative source must not authorize validation or candidate packs"
            )
        for bucket_type, bucket_key, _fields in _global_evidence_request_bucket_memberships(
            request_row
        ):
            request_rows_by_bucket.setdefault((bucket_type, bucket_key), []).append(
                request_row
            )

    for bucket in sorted(bucket_queue, key=lambda row: _row_int(row, "queue_rank")):
        require_sandbox_boundary(
            bucket,
            payload_name="sandbox_artifact_catalog_global_evidence_request_bucket_representative_bucket",
        )
        bucket_type = str(bucket.get("bucket_type") or "")
        bucket_key = str(bucket.get("bucket_key") or "")
        bucket_rows = sorted(
            request_rows_by_bucket.get((bucket_type, bucket_key), []),
            key=lambda row: (
                _row_int(row, "leaderboard_rank"),
                _row_int(row, "evidence_request_row_rank"),
                str(row.get("evidence_request_trial_id") or ""),
            ),
        )[:representative_limit]
        for representative_rank, request_row in enumerate(bucket_rows, start=1):
            source_context_columns = (
                _global_evidence_request_source_context_columns_from_row(
                    request_row
                )
            )
            row = {
                **sandbox_boundary_metadata(),
                "artifact_family": "rapid_strategy_iteration_sandbox_artifact_catalog_global_evidence_request_bucket_representative_parquet_row",
                "bucket_type": bucket_type,
                "bucket_key": bucket_key,
                "bucket_queue_rank": _row_int(bucket, "queue_rank"),
                "representative_rank": int(representative_rank),
                "bucket_requested_validation": bucket.get("requested_validation"),
                "bucket_hypothesis_id": bucket.get("hypothesis_id"),
                "bucket_family": bucket.get("family"),
                "bucket_venue": bucket.get("venue"),
                "bucket_symbol": bucket.get("symbol"),
                "bucket_leaderboard_decision": bucket.get("leaderboard_decision"),
                "bucket_source_context_available": bool(
                    bucket.get("source_context_available", False)
                ),
                "bucket_source_venue": bucket.get("source_venue"),
                "bucket_source_symbol": bucket.get("source_symbol"),
                "bucket_source_data_family": bucket.get("source_data_family"),
                "bucket_source_interval": bucket.get("source_interval"),
                "bucket_source_venue_descriptor_id": bucket.get(
                    "source_venue_descriptor_id"
                ),
                "bucket_source_routing_mode": bucket.get("source_routing_mode"),
                "bucket_source_data_path": bucket.get("source_data_path"),
                "bucket_evidence_request_count": _row_int(
                    bucket,
                    "evidence_request_count",
                ),
                "evidence_request_trial_id": request_row.get(
                    "evidence_request_trial_id"
                ),
                "source_trial_id": request_row.get("source_trial_id"),
                "requested_validation": request_row.get("requested_validation"),
                **source_context_columns,
                "source_artifact_path": request_row.get("source_artifact_path"),
                "source_artifact_path_relative": request_row.get(
                    "source_artifact_path_relative"
                ),
                "source_artifact_dir": request_row.get("source_artifact_dir"),
                "source_leaderboard_json_path": request_row.get(
                    "source_leaderboard_json_path"
                ),
                "source_leaderboard_parquet_path": request_row.get(
                    "source_leaderboard_parquet_path"
                ),
                "source_bucket_leaderboard_parquet_path": request_row.get(
                    "source_bucket_leaderboard_parquet_path"
                ),
                "top_hypothesis_row_rank": _row_int(
                    request_row,
                    "top_hypothesis_row_rank",
                ),
                "leaderboard_rank": _row_int(request_row, "leaderboard_rank"),
                "hypothesis_id": request_row.get("hypothesis_id"),
                "family": request_row.get("family"),
                "source_ids": _list_value(request_row.get("source_ids")),
                "sides": _list_value(request_row.get("sides")),
                "venues_tested": _list_value(request_row.get("venues_tested")),
                "symbols_tested": _list_value(request_row.get("symbols_tested")),
                "data_families_tested": _list_value(
                    request_row.get("data_families_tested")
                ),
                "holding_periods_tested": _list_value(
                    request_row.get("holding_periods_tested")
                ),
                "exit_profiles_tested": _list_value(
                    request_row.get("exit_profiles_tested")
                ),
                "exit_variant_ids_tested": _list_value(
                    request_row.get("exit_variant_ids_tested")
                ),
                "filter_variant_ids_tested": _list_value(
                    request_row.get("filter_variant_ids_tested")
                ),
                "run_ids": _list_value(request_row.get("run_ids")),
                "source_run_ids": _list_value(request_row.get("source_run_ids")),
                "source_run_dirs": _list_value(request_row.get("source_run_dirs")),
                "source_manifest_paths": _list_value(
                    request_row.get("source_manifest_paths")
                ),
                "run_count": _row_int(request_row, "run_count"),
                "result_count": _row_int(request_row, "result_count"),
                "screened_count": _row_int(request_row, "screened_count"),
                "rejected_count": _row_int(request_row, "rejected_count"),
                "blocked_count": _row_int(request_row, "blocked_count"),
                "best_trial_id": request_row.get("best_trial_id"),
                "best_run_id": request_row.get("best_run_id"),
                "best_source_run_dir": request_row.get("best_source_run_dir"),
                "best_status": request_row.get("best_status"),
                "best_rank": _row_int(request_row, "best_rank"),
                "best_score": _optional_float(request_row.get("best_score")),
                "best_net_return_sum": _optional_float(
                    request_row.get("best_net_return_sum")
                ),
                "best_trade_count": _row_int(request_row, "best_trade_count"),
                "best_active_days": _row_int(request_row, "best_active_days"),
                "best_win_rate": _optional_float(request_row.get("best_win_rate")),
                "best_max_drawdown": _optional_float(
                    request_row.get("best_max_drawdown")
                ),
                "best_venue": request_row.get("best_venue"),
                "best_symbol": request_row.get("best_symbol"),
                "best_exit_variant_id": request_row.get("best_exit_variant_id"),
                "best_filter_variant_id": request_row.get("best_filter_variant_id"),
                "leaderboard_decision": request_row.get("leaderboard_decision"),
                "decision_reason": request_row.get("decision_reason"),
                "descriptor_only": True,
                "strict_validation_executed": False,
                "candidate_pack_written": False,
                "replay_command_execution_authorized": False,
                "strict_validation_authorized": False,
                "candidate_pack_write_authorized": False,
            }
            require_sandbox_boundary(
                row,
                payload_name="sandbox_artifact_catalog_global_evidence_request_bucket_representative_parquet_row",
            )
            rows.append(row)
    return rows


def _global_evidence_request_summary(
    request_rows: list[dict[str, Any]],
    priority_queue_rows: list[dict[str, Any]],
    bucket_queue_rows: list[dict[str, Any]],
    representative_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    requested_validation_counts: dict[str, int] = {}
    leaderboard_decision_counts: dict[str, int] = {}
    family_counts: dict[str, int] = {}
    tested_venue_counts: dict[str, int] = {}
    tested_symbol_counts: dict[str, int] = {}
    bucket_type_counts: dict[str, int] = {}
    source_venue_counts: dict[str, int] = {}
    source_symbol_counts: dict[str, int] = {}
    source_data_family_counts: dict[str, int] = {}
    source_interval_counts: dict[str, int] = {}
    source_routing_mode_counts: dict[str, int] = {}
    source_venue_descriptor_counts: dict[str, int] = {}
    source_data_path_counts: dict[str, int] = {}
    unique_trial_ids: set[str] = set()
    unique_hypothesis_ids: set[str] = set()
    source_leaderboards: set[str] = set()
    source_context_available_count = 0

    for row in request_rows:
        require_sandbox_boundary(
            row,
            payload_name="sandbox_artifact_catalog_global_evidence_request_summary_source",
        )
        _add_count(requested_validation_counts, row.get("requested_validation"))
        _add_count(leaderboard_decision_counts, row.get("leaderboard_decision"))
        _add_count(family_counts, row.get("family"))
        _add_list_counts(tested_venue_counts, row.get("venues_tested"))
        _add_list_counts(tested_symbol_counts, row.get("symbols_tested"))
        if bool(row.get("source_context_available", False)):
            source_context_available_count += 1
            _add_count(source_venue_counts, row.get("source_venue"))
            _add_count(source_symbol_counts, row.get("source_symbol"))
            _add_count(source_data_family_counts, row.get("source_data_family"))
            _add_count(source_interval_counts, row.get("source_interval"))
            _add_count(source_routing_mode_counts, row.get("source_routing_mode"))
            _add_count(
                source_venue_descriptor_counts,
                row.get("source_venue_descriptor_id"),
            )
            _add_count(source_data_path_counts, row.get("source_data_path"))
        trial_id = row.get("evidence_request_trial_id")
        if trial_id is not None and str(trial_id) != "":
            unique_trial_ids.add(str(trial_id))
        hypothesis_id = row.get("hypothesis_id")
        if hypothesis_id is not None and str(hypothesis_id) != "":
            unique_hypothesis_ids.add(str(hypothesis_id))
        source_path = row.get("source_artifact_path") or row.get(
            "source_leaderboard_json_path"
        )
        if source_path is not None and str(source_path) != "":
            source_leaderboards.add(str(source_path))

    for row in bucket_queue_rows:
        require_sandbox_boundary(
            row,
            payload_name="sandbox_artifact_catalog_global_evidence_request_summary_bucket",
        )
        _add_count(bucket_type_counts, row.get("bucket_type"))

    for row in priority_queue_rows:
        require_sandbox_boundary(
            row,
            payload_name="sandbox_artifact_catalog_global_evidence_request_summary_priority",
        )

    for row in representative_rows:
        require_sandbox_boundary(
            row,
            payload_name="sandbox_artifact_catalog_global_evidence_request_summary_representative",
        )

    summary = {
        **sandbox_boundary_metadata(),
        "evidence_request_count": len(request_rows),
        "unique_evidence_request_trial_count": len(unique_trial_ids),
        "requesting_hypothesis_count": len(unique_hypothesis_ids),
        "source_leaderboard_count": len(source_leaderboards),
        "priority_queue_count": len(priority_queue_rows),
        "bucket_queue_count": len(bucket_queue_rows),
        "bucket_representative_count": len(representative_rows),
        "source_context_available_count": source_context_available_count,
        "source_context_missing_count": len(request_rows)
        - source_context_available_count,
        "requested_validation_counts": _sorted_count_map(
            requested_validation_counts
        ),
        "leaderboard_decision_counts": _sorted_count_map(
            leaderboard_decision_counts
        ),
        "family_counts": _sorted_count_map(family_counts),
        "tested_venue_counts": _sorted_count_map(tested_venue_counts),
        "tested_symbol_counts": _sorted_count_map(tested_symbol_counts),
        "bucket_type_counts": _sorted_count_map(bucket_type_counts),
        "source_venue_counts": _sorted_count_map(source_venue_counts),
        "source_symbol_counts": _sorted_count_map(source_symbol_counts),
        "source_data_family_counts": _sorted_count_map(source_data_family_counts),
        "source_interval_counts": _sorted_count_map(source_interval_counts),
        "source_routing_mode_counts": _sorted_count_map(source_routing_mode_counts),
        "source_venue_descriptor_counts": _sorted_count_map(
            source_venue_descriptor_counts
        ),
        "source_data_path_counts": _sorted_count_map(source_data_path_counts),
        "descriptor_only": True,
        "strict_validation_executed": False,
        "candidate_pack_written": False,
        "replay_command_execution_authorized": False,
        "strict_validation_authorized": False,
        "candidate_pack_write_authorized": False,
    }
    require_sandbox_boundary(
        summary,
        payload_name="sandbox_artifact_catalog_global_evidence_request_summary",
    )
    return summary


def _global_evidence_request_source_summary_rows(
    summary: dict[str, Any],
    request_rows: list[dict[str, Any]],
    *,
    representative_limit: int = SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_SOURCE_SUMMARY_REPRESENTATIVE_LIMIT,
) -> list[dict[str, Any]]:
    require_sandbox_boundary(
        summary,
        payload_name="sandbox_artifact_catalog_global_evidence_request_source_summary_source",
    )
    count_maps = [
        ("source_venue", "source_venue_counts"),
        ("source_symbol", "source_symbol_counts"),
        ("source_data_family", "source_data_family_counts"),
        ("source_interval", "source_interval_counts"),
        ("source_routing_mode", "source_routing_mode_counts"),
        ("source_venue_descriptor_id", "source_venue_descriptor_counts"),
        ("source_data_path", "source_data_path_counts"),
    ]
    aggregates: dict[tuple[str, str], dict[str, Any]] = {}
    for row in request_rows:
        require_sandbox_boundary(
            row,
            payload_name="sandbox_artifact_catalog_global_evidence_request_source_summary_request_row",
        )
        if not bool(row.get("source_context_available", False)):
            continue
        for source_context_field, _summary_key in count_maps:
            value = _text_value(row.get(source_context_field))
            if value is None:
                continue
            aggregate = aggregates.setdefault(
                (source_context_field, value),
                {
                    "trial_ids": set(),
                    "source_leaderboards": set(),
                    "source_market_starts": [],
                    "source_market_ends": [],
                    "rows": [],
                },
            )
            aggregate["rows"].append(row)
            trial_id = row.get("evidence_request_trial_id")
            if trial_id is not None and str(trial_id) != "":
                aggregate["trial_ids"].add(str(trial_id))
            source_path = row.get("source_artifact_path") or row.get(
                "source_leaderboard_json_path"
            )
            if source_path is not None and str(source_path) != "":
                aggregate["source_leaderboards"].add(str(source_path))
            market_start = row.get("source_market_start")
            if market_start is not None and str(market_start) != "":
                aggregate["source_market_starts"].append(str(market_start))
            market_end = row.get("source_market_end")
            if market_end is not None and str(market_end) != "":
                aggregate["source_market_ends"].append(str(market_end))

    rows: list[dict[str, Any]] = []
    for source_context_field, summary_key in count_maps:
        counts = _dict_value(summary.get(summary_key))
        for source_context_value, source_context_count in sorted(
            counts.items(),
            key=lambda item: (-int(item[1]), str(item[0])),
        ):
            aggregate = aggregates.get(
                (source_context_field, str(source_context_value)),
                {},
            )
            source_market_starts = list(aggregate.get("source_market_starts", []))
            source_market_ends = list(aggregate.get("source_market_ends", []))
            aggregate_rows = sorted(
                list(aggregate.get("rows", [])),
                key=lambda row: (
                    _row_int(row, "leaderboard_rank"),
                    _score_sort_value(row.get("best_score")),
                    _row_int(row, "evidence_request_row_rank"),
                    str(row.get("source_artifact_path") or ""),
                    str(row.get("evidence_request_trial_id") or ""),
                ),
            )
            representatives = aggregate_rows[:representative_limit]
            best_row = aggregate_rows[0] if aggregate_rows else {}
            row = {
                **sandbox_boundary_metadata(),
                "artifact_family": "rapid_strategy_iteration_sandbox_artifact_catalog_global_evidence_request_source_summary_row",
                "summary_row_rank": len(rows) + 1,
                "source_context_field": source_context_field,
                "source_context_value": str(source_context_value),
                "source_context_count": int(source_context_count),
                "unique_evidence_request_trial_count": len(
                    aggregate.get("trial_ids", set())
                ),
                "source_leaderboard_count": len(
                    aggregate.get("source_leaderboards", set())
                ),
                "source_market_start_min": (
                    min(source_market_starts) if source_market_starts else None
                ),
                "source_market_start_max": (
                    max(source_market_starts) if source_market_starts else None
                ),
                "source_market_end_min": (
                    min(source_market_ends) if source_market_ends else None
                ),
                "source_market_end_max": (
                    max(source_market_ends) if source_market_ends else None
                ),
                "best_leaderboard_rank": (
                    _row_int(best_row, "leaderboard_rank") if best_row else None
                ),
                "best_score": (
                    _optional_float(best_row.get("best_score"))
                    if best_row
                    else None
                ),
                "best_source_metric_rank": (
                    _row_int(best_row, "source_metric_rank") if best_row else None
                ),
                "best_source_metric_score": (
                    _optional_float(best_row.get("source_metric_score"))
                    if best_row
                    else None
                ),
                "best_source_metric_net_return_sum": (
                    _optional_float(best_row.get("source_metric_net_return_sum"))
                    if best_row
                    else None
                ),
                "best_source_metric_trade_count": (
                    _row_int(best_row, "source_metric_trade_count")
                    if best_row
                    else None
                ),
                "best_evidence_request_trial_id": (
                    best_row.get("evidence_request_trial_id") if best_row else None
                ),
                "best_source_trial_id": (
                    best_row.get("source_trial_id") if best_row else None
                ),
                "best_hypothesis_id": (
                    best_row.get("hypothesis_id") if best_row else None
                ),
                "best_family": best_row.get("family") if best_row else None,
                "representative_limit": int(representative_limit),
                "representative_count": len(representatives),
                "representative_evidence_request_trial_ids": _ordered_unique_row_values(
                    representatives,
                    "evidence_request_trial_id",
                ),
                "representative_source_trial_ids": _ordered_unique_row_values(
                    representatives,
                    "source_trial_id",
                ),
                "representative_source_request_ids": _ordered_unique_row_values(
                    representatives,
                    "source_request_id",
                ),
                "representative_source_artifact_paths": _ordered_unique_row_values(
                    representatives,
                    "source_artifact_path",
                ),
                "representative_source_leaderboard_json_paths": _ordered_unique_row_values(
                    representatives,
                    "source_leaderboard_json_path",
                ),
                "evidence_request_count": _row_int(
                    summary,
                    "evidence_request_count",
                ),
                "source_context_available_count": _row_int(
                    summary,
                    "source_context_available_count",
                ),
                "source_context_missing_count": _row_int(
                    summary,
                    "source_context_missing_count",
                ),
                "descriptor_only": True,
                "strict_validation_executed": False,
                "candidate_pack_written": False,
                "replay_command_execution_authorized": False,
                "strict_validation_authorized": False,
                "candidate_pack_write_authorized": False,
            }
            require_sandbox_boundary(
                row,
                payload_name="sandbox_artifact_catalog_global_evidence_request_source_summary_row",
            )
            rows.append(row)
    return rows


def _rank_sort_value(row: dict[str, Any], key: str) -> float:
    value = row.get(key)
    if value is None or str(value) == "":
        return float("inf")
    return float(value)


def _global_evidence_request_source_priority_queue(
    source_summary_rows: list[dict[str, Any]],
    *,
    limit: int = SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_SOURCE_PRIORITY_QUEUE_LIMIT,
) -> list[dict[str, Any]]:
    sortable_rows: list[dict[str, Any]] = []
    for row in source_summary_rows:
        require_sandbox_boundary(
            row,
            payload_name="sandbox_artifact_catalog_global_evidence_request_source_priority_queue_source",
        )
        if bool(row.get("strict_validation_authorized", False)) or bool(
            row.get("candidate_pack_write_authorized", False)
        ):
            raise ValueError(
                "sandbox global evidence request source priority queue source must not authorize validation or candidate packs"
            )
        sortable_rows.append(row)

    sorted_rows = sorted(
        sortable_rows,
        key=lambda row: (
            _rank_sort_value(row, "best_leaderboard_rank"),
            _score_sort_value(row.get("best_score")),
            _rank_sort_value(row, "best_source_metric_rank"),
            _score_sort_value(row.get("best_source_metric_score")),
            -_row_int(row, "unique_evidence_request_trial_count"),
            -_row_int(row, "source_context_count"),
            str(row.get("source_context_field") or ""),
            str(row.get("source_context_value") or ""),
            _row_int(row, "summary_row_rank"),
        ),
    )[:limit]

    queue: list[dict[str, Any]] = []
    for queue_rank, source_row in enumerate(sorted_rows, start=1):
        row = {
            **sandbox_boundary_metadata(),
            "artifact_family": "rapid_strategy_iteration_sandbox_artifact_catalog_global_evidence_request_source_priority_queue_row",
            "queue_rank": int(queue_rank),
            "source_summary_row_rank": _row_int(source_row, "summary_row_rank"),
        }
        for column in GLOBAL_EVIDENCE_REQUEST_SOURCE_SUMMARY_PARQUET_COLUMNS:
            if column in {"artifact_family", "summary_row_rank", *SANDBOX_BOUNDARY_FLAGS}:
                continue
            row[column] = source_row.get(column)
        require_sandbox_boundary(
            row,
            payload_name="sandbox_artifact_catalog_global_evidence_request_source_priority_queue_row",
        )
        queue.append(row)
    return queue


def _global_bucket_top_bucket_parquet_rows(
    path: Path,
    *,
    root_dir: Path,
    kind: str,
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    if kind != "global_leaderboard":
        return []
    rows: list[dict[str, Any]] = []
    for bucket_rank, bucket in enumerate(
        _list_value(payload.get("top_buckets")),
        start=1,
    ):
        if not isinstance(bucket, dict):
            raise ValueError(f"sandbox global leaderboard top bucket must be an object: {path}")
        require_sandbox_boundary(
            bucket,
            payload_name="sandbox_artifact_catalog_global_bucket_top_bucket_source",
        )
        if bool(bucket.get("strict_validation_authorized", False)) or bool(
            bucket.get("candidate_pack_write_authorized", False)
        ) or bool(bucket.get("candidate_pack_authorized", False)):
            raise ValueError(
                f"sandbox global leaderboard top bucket must not authorize validation or candidate packs: {path}"
            )
        row = {
            **sandbox_boundary_metadata(),
            "artifact_family": "rapid_strategy_iteration_sandbox_artifact_catalog_global_bucket_top_bucket_parquet_row",
            "source_artifact_path": str(path),
            "source_artifact_path_relative": str(path.relative_to(root_dir)),
            "source_artifact_dir": str(path.parent),
            "source_root_dir": payload.get("root_dir"),
            "source_output_dir": payload.get("output_dir"),
            "source_leaderboard_json_path": payload.get("leaderboard_json_path"),
            "source_leaderboard_parquet_path": payload.get("leaderboard_parquet_path"),
            "source_bucket_leaderboard_parquet_path": payload.get(
                "bucket_leaderboard_parquet_path"
            ),
            "source_run_manifest_count": _count_value(payload, "run_manifest_count"),
            "source_run_count": _count_value(payload, "source_run_count"),
            "source_result_count": _count_value(payload, "result_count"),
            "source_hypothesis_count": _count_value(payload, "hypothesis_count"),
            "source_bucket_count": _count_value(payload, "bucket_count"),
            "source_bucket_decision_counts": _dict_value(
                payload.get("bucket_decision_counts")
            ),
            "top_bucket_row_rank": int(bucket_rank),
            "bucket_leaderboard_rank": _row_int(bucket, "bucket_leaderboard_rank"),
            "bucket_type": bucket.get("bucket_type"),
            "bucket_key": bucket.get("bucket_key"),
            "bucket_columns": _list_value(bucket.get("bucket_columns")),
            "bucket_values": _dict_value(bucket.get("bucket_values")),
            "hypotheses_tested": _list_value(bucket.get("hypotheses_tested")),
            "families_tested": _list_value(bucket.get("families_tested")),
            "venues_tested": _list_value(bucket.get("venues_tested")),
            "symbols_tested": _list_value(bucket.get("symbols_tested")),
            "exit_profiles_tested": _list_value(bucket.get("exit_profiles_tested")),
            "exit_variant_ids_tested": _list_value(
                bucket.get("exit_variant_ids_tested")
            ),
            "filter_variant_ids_tested": _list_value(
                bucket.get("filter_variant_ids_tested")
            ),
            "source_run_ids": _list_value(bucket.get("source_run_ids")),
            "source_run_dirs": _list_value(bucket.get("source_run_dirs")),
            "source_manifest_paths": _list_value(bucket.get("source_manifest_paths")),
            "run_count": _row_int(bucket, "run_count"),
            "result_count": _row_int(bucket, "result_count"),
            "screened_count": _row_int(bucket, "screened_count"),
            "rejected_count": _row_int(bucket, "rejected_count"),
            "blocked_count": _row_int(bucket, "blocked_count"),
            "positive_net_result_count": _row_int(
                bucket,
                "positive_net_result_count",
            ),
            "evidence_request_count": _row_int(bucket, "evidence_request_count"),
            "evidence_request_trial_ids": _list_value(
                bucket.get("evidence_request_trial_ids")
            ),
            "best_trial_id": bucket.get("best_trial_id"),
            "best_run_id": bucket.get("best_run_id"),
            "best_source_run_dir": bucket.get("best_source_run_dir"),
            "best_status": bucket.get("best_status"),
            "best_rank": _row_int(bucket, "best_rank"),
            "best_score": _optional_float(bucket.get("best_score")),
            "best_net_return_sum": _optional_float(bucket.get("best_net_return_sum")),
            "best_trade_count": _row_int(bucket, "best_trade_count"),
            "best_active_days": _row_int(bucket, "best_active_days"),
            "best_win_rate": _optional_float(bucket.get("best_win_rate")),
            "best_max_drawdown": _optional_float(bucket.get("best_max_drawdown")),
            "best_hypothesis_id": bucket.get("best_hypothesis_id"),
            "best_family": bucket.get("best_family"),
            "best_venue": bucket.get("best_venue"),
            "best_symbol": bucket.get("best_symbol"),
            "best_exit_profile": bucket.get("best_exit_profile"),
            "best_exit_variant_id": bucket.get("best_exit_variant_id"),
            "best_filter_variant_id": bucket.get("best_filter_variant_id"),
            "blocked_reason_counts": _dict_value(bucket.get("blocked_reason_counts")),
            "rejected_reason_counts": _dict_value(bucket.get("rejected_reason_counts")),
            "all_reason_counts": _dict_value(bucket.get("all_reason_counts")),
            "bucket_leaderboard_decision": bucket.get("bucket_leaderboard_decision"),
            "decision_reason": bucket.get("decision_reason"),
            "descriptor_only": True,
            "strict_validation_executed": False,
            "candidate_pack_written": False,
            "replay_command_execution_authorized": False,
            "strict_validation_authorized": False,
            "candidate_pack_write_authorized": False,
        }
        require_sandbox_boundary(
            row,
            payload_name="sandbox_artifact_catalog_global_bucket_top_bucket_parquet_row",
        )
        rows.append(row)
    return rows


def _sorted_counts(counts: dict[str, int]) -> dict[str, int]:
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _row_value_counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = row.get(key)
        if value in (None, ""):
            continue
        key_text = str(value)
        counts[key_text] = counts.get(key_text, 0) + 1
    return _sorted_counts(counts)


def _row_list_counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        for value in _list_value(row.get(key)):
            key_text = str(value)
            counts[key_text] = counts.get(key_text, 0) + 1
    return _sorted_counts(counts)


def _numeric_value(source: dict[str, Any], key: str) -> float | None:
    value = source.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _iteration_action_plan_parquet_rows(
    path: Path,
    *,
    root_dir: Path,
    kind: str,
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    if kind != "iteration_index":
        return []
    rows: list[dict[str, Any]] = []
    for row_rank, raw_item in enumerate(_list_value(payload.get("agent_action_plan")), start=1):
        if not isinstance(raw_item, dict):
            continue
        item = dict(raw_item)
        counts = _dict_value(item.get("counts"))
        row = {
            **sandbox_boundary_metadata(),
            "artifact_family": "rapid_strategy_iteration_sandbox_artifact_catalog_iteration_action_plan_parquet_row",
            "source_artifact_path": str(path),
            "source_artifact_path_relative": str(path.relative_to(root_dir)),
            "source_artifact_dir": str(path.parent),
            "source_index_id": payload.get("index_id"),
            "source_root_dir": payload.get("root_dir"),
            "source_output_dir": payload.get("output_dir"),
            "action_plan_row_rank": int(row_rank),
            "iteration_id": item.get("iteration_id"),
            "run_id": item.get("run_id"),
            "iteration_status": item.get("iteration_status"),
            "next_action": item.get("next_action"),
            "primary_recommended_action": item.get("primary_recommended_action"),
            "action": item.get("action"),
            "action_priority": _row_int(item, "action_priority"),
            "action_rank": _row_int(item, "action_rank"),
            "is_primary_action": bool(item.get("is_primary_action", False)),
            "blocked_by_prior_action": bool(item.get("blocked_by_prior_action", False)),
            "reason_codes": _list_value(item.get("reason_codes")),
            "row_reason_codes": _list_value(item.get("row_reason_codes")),
            "source_queues": _list_value(item.get("source_queues")),
            "input_replay_context_id": item.get("input_replay_context_id"),
            "input_replay_command": item.get("input_replay_command"),
            "input_replay_strategy_input_mode": item.get(
                "input_replay_strategy_input_mode"
            ),
            "input_replay_venue_input_mode": item.get("input_replay_venue_input_mode"),
            "brief_status": item.get("brief_status"),
            "artifact_availability_status": item.get("artifact_availability_status"),
            "artifact_missing_keys": _list_value(item.get("artifact_missing_keys")),
            "iteration_manifest_path": item.get("iteration_manifest_path"),
            "agent_brief_json_path": item.get("agent_brief_json_path"),
            "strategy_catalog_json_path": item.get("strategy_catalog_json_path"),
            "venue_archive_manifest_path": item.get("venue_archive_manifest_path"),
            "action_count": int(counts.get("action_count", 0) or 0),
            "strategy_count": int(counts.get("strategy_count", 0) or 0),
            "descriptor_count": int(counts.get("descriptor_count", 0) or 0),
            "result_count": int(counts.get("result_count", 0) or 0),
            "screened_count": int(counts.get("screened_count", 0) or 0),
            "rejected_count": int(counts.get("rejected_count", 0) or 0),
            "blocked_count": int(counts.get("blocked_count", 0) or 0),
            "deduped_validation_request_count": int(
                counts.get("deduped_validation_request_count", 0) or 0
            ),
            "preflight_blocked_trial_estimate": int(
                counts.get("preflight_blocked_trial_estimate", 0) or 0
            ),
            "artifact_missing_count": int(counts.get("artifact_missing_count", 0) or 0),
            "descriptor_only": True,
            "strict_validation_executed": bool(
                item.get("strict_validation_executed", False)
            ),
            "candidate_pack_written": bool(item.get("candidate_pack_written", False)),
            "replay_command_execution_authorized": False,
            "strict_validation_authorized": False,
            "candidate_pack_write_authorized": False,
        }
        require_sandbox_boundary(
            row,
            payload_name="sandbox_artifact_catalog_iteration_action_plan_parquet_row",
        )
        rows.append(row)
    return rows


def _iteration_venue_expansion_gap_worklist_parquet_rows(
    path: Path,
    *,
    root_dir: Path,
    kind: str,
    payload: dict[str, Any],
    start_rank: int,
) -> list[dict[str, Any]]:
    if kind != "iteration_index":
        return []
    rows: list[dict[str, Any]] = []
    for row_rank, raw_item in enumerate(_list_value(payload.get("agent_action_plan")), start=1):
        if not isinstance(raw_item, dict):
            continue
        item = dict(raw_item)
        action = str(item.get("action") or "")
        if action != "repair_or_add_venue_expansion_archives":
            continue
        samples = _list_value(item.get("venue_expansion_gap_samples"))
        if not samples:
            continue
        counts = _dict_value(item.get("counts"))
        for sample_rank, raw_sample in enumerate(samples, start=1):
            if not isinstance(raw_sample, dict):
                continue
            sample = dict(raw_sample)
            target_action = str(sample.get("target_action") or "")
            if target_action == "use_ready_archive_bucket":
                continue
            row = {
                **sandbox_boundary_metadata(),
                "artifact_family": "rapid_strategy_iteration_sandbox_artifact_catalog_iteration_venue_expansion_gap_worklist_row",
                "source_artifact_path": str(path),
                "source_artifact_path_relative": str(path.relative_to(root_dir)),
                "source_artifact_dir": str(path.parent),
                "source_index_id": payload.get("index_id"),
                "source_root_dir": payload.get("root_dir"),
                "source_output_dir": payload.get("output_dir"),
                "worklist_row_rank": int(start_rank + len(rows)),
                "action_plan_row_rank": int(row_rank),
                "venue_expansion_gap_sample_rank": int(sample_rank),
                "source_gap_rank": _row_int(sample, "gap_rank"),
                "iteration_id": item.get("iteration_id"),
                "run_id": item.get("run_id"),
                "iteration_status": item.get("iteration_status"),
                "next_action": item.get("next_action"),
                "primary_recommended_action": item.get("primary_recommended_action"),
                "action": action,
                "action_priority": _row_int(item, "action_priority"),
                "action_rank": _row_int(item, "action_rank"),
                "is_primary_action": bool(item.get("is_primary_action", False)),
                "blocked_by_prior_action": bool(
                    item.get("blocked_by_prior_action", False)
                ),
                "reason_codes": _list_value(item.get("reason_codes")),
                "row_reason_codes": _list_value(item.get("row_reason_codes")),
                "source_queues": _list_value(item.get("source_queues")),
                "input_replay_context_id": item.get("input_replay_context_id"),
                "input_replay_command": item.get("input_replay_command"),
                "input_replay_strategy_input_mode": item.get(
                    "input_replay_strategy_input_mode"
                ),
                "input_replay_venue_input_mode": item.get(
                    "input_replay_venue_input_mode"
                ),
                "brief_status": item.get("brief_status"),
                "artifact_availability_status": item.get(
                    "artifact_availability_status"
                ),
                "artifact_missing_keys": _list_value(item.get("artifact_missing_keys")),
                "iteration_manifest_path": item.get("iteration_manifest_path"),
                "agent_brief_json_path": item.get("agent_brief_json_path"),
                "strategy_catalog_json_path": item.get("strategy_catalog_json_path"),
                "venue_archive_manifest_path": item.get("venue_archive_manifest_path"),
                "archive_build_report_json_path": item.get(
                    "archive_build_report_json_path"
                ),
                "archive_coverage_venue_expansion_gaps_parquet_path": item.get(
                    "archive_coverage_venue_expansion_gaps_parquet_path"
                ),
                "venue_expansion_target_venues": _list_value(
                    item.get("venue_expansion_target_venues")
                ),
                "venue_expansion_status_counts": _dict_value(
                    item.get("venue_expansion_status_counts")
                ),
                "venue_expansion_action_counts": _dict_value(
                    item.get("venue_expansion_action_counts")
                ),
                "venue_expansion_gap_samples_truncated": bool(
                    item.get("venue_expansion_gap_samples_truncated", False)
                ),
                "iteration_action_count": int(counts.get("action_count", 0) or 0),
                "iteration_strategy_count": int(counts.get("strategy_count", 0) or 0),
                "iteration_archive_descriptor_count": int(
                    counts.get("descriptor_count", 0) or 0
                ),
                "iteration_result_count": int(counts.get("result_count", 0) or 0),
                "iteration_screened_count": int(counts.get("screened_count", 0) or 0),
                "iteration_rejected_count": int(counts.get("rejected_count", 0) or 0),
                "iteration_blocked_count": int(counts.get("blocked_count", 0) or 0),
                "iteration_deduped_validation_request_count": int(
                    counts.get("deduped_validation_request_count", 0) or 0
                ),
                "iteration_preflight_blocked_trial_estimate": int(
                    counts.get("preflight_blocked_trial_estimate", 0) or 0
                ),
                "iteration_artifact_missing_count": int(
                    counts.get("artifact_missing_count", 0) or 0
                ),
                "target_venue": sample.get("target_venue"),
                "market_symbol_key": sample.get("market_symbol_key"),
                "data_family": sample.get("data_family"),
                "interval": sample.get("interval"),
                "target_bucket_key": sample.get("target_bucket_key"),
                "target_venue_observed": bool(
                    sample.get("target_venue_observed", False)
                ),
                "target_missing": bool(sample.get("target_missing", False)),
                "target_status": sample.get("target_status"),
                "target_action": sample.get("target_action"),
                "observed_symbols": _list_value(sample.get("observed_symbols")),
                "source_coverage_key": sample.get("source_coverage_key"),
                "descriptor_count": _row_int(sample, "descriptor_count"),
                "ready_descriptor_count": _row_int(sample, "ready_descriptor_count"),
                "blocked_descriptor_count": _row_int(
                    sample,
                    "blocked_descriptor_count",
                ),
                "ready_window_row_count": _row_int(sample, "ready_window_row_count"),
                "ready_requested_window_row_count": _row_int(
                    sample,
                    "ready_requested_window_row_count",
                ),
                "requested_window_filter_applied": bool(
                    sample.get("requested_window_filter_applied", False)
                ),
                "requested_window_start": sample.get("requested_window_start"),
                "requested_window_end": sample.get("requested_window_end"),
                "observed_window_start": sample.get("observed_window_start"),
                "observed_window_end": sample.get("observed_window_end"),
                "source_paths": _list_value(sample.get("source_paths")),
                "manifest_paths": _list_value(sample.get("manifest_paths")),
                "blocker_reason_counts": _dict_value(
                    sample.get("blocker_reason_counts")
                ),
                "descriptor_only": True,
                "strict_validation_executed": bool(
                    item.get("strict_validation_executed", False)
                ),
                "candidate_pack_written": bool(
                    item.get("candidate_pack_written", False)
                ),
                "replay_command_execution_authorized": False,
                "strict_validation_authorized": False,
                "candidate_pack_write_authorized": False,
            }
            require_sandbox_boundary(
                row,
                payload_name="sandbox_artifact_catalog_iteration_venue_expansion_gap_worklist_row",
            )
            rows.append(row)
    return rows


def _iteration_action_plan_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "artifact_count": len(
            {
                str(row.get("source_artifact_path"))
                for row in rows
                if row.get("source_artifact_path") is not None
            }
        ),
        "action_item_count": len(rows),
        "primary_action_count": sum(
            1 for row in rows if bool(row.get("is_primary_action", False))
        ),
        "blocked_by_prior_action_count": sum(
            1 for row in rows if bool(row.get("blocked_by_prior_action", False))
        ),
        "action_counts": _row_value_counts(rows, "action"),
        "source_queue_counts": _row_list_counts(rows, "source_queues"),
        "iteration_status_counts": _row_value_counts(rows, "iteration_status"),
    }


def _iteration_venue_expansion_gap_worklist_summary(
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "worklist_row_count": len(rows),
        "source_artifact_count": len(
            {
                str(row.get("source_artifact_path"))
                for row in rows
                if row.get("source_artifact_path") is not None
            }
        ),
        "source_iteration_count": len(
            {
                str(row.get("iteration_id"))
                for row in rows
                if row.get("iteration_id") is not None
            }
        ),
        "target_venue_counts": _row_value_counts(rows, "target_venue"),
        "target_action_counts": _row_value_counts(rows, "target_action"),
        "target_status_counts": _row_value_counts(rows, "target_status"),
        "source_action_counts": _row_value_counts(rows, "action"),
        "source_queue_counts": _row_list_counts(rows, "source_queues"),
        "blocked_by_prior_action_count": sum(
            1 for row in rows if bool(row.get("blocked_by_prior_action", False))
        ),
    }


def _iteration_action_plan_bucket_keys(row: dict[str, Any]) -> list[tuple[str, str]]:
    keys = [("action", str(row.get("action") or "unknown"))]
    source_queues = _list_value(row.get("source_queues"))
    if not source_queues:
        keys.append(("source_queue", "none"))
    else:
        for source_queue in source_queues:
            keys.append(("source_queue", str(source_queue)))
    return keys


def _iteration_action_plan_bucket_representatives(
    rows: list[dict[str, Any]],
    *,
    representative_limit: int,
) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            _row_int(row, "action_priority"),
            bool(row.get("blocked_by_prior_action", False)),
            _row_int(row, "action_rank"),
            str(row.get("iteration_id") or ""),
            str(row.get("action") or ""),
        ),
    )[:representative_limit]


def _iteration_action_plan_bucket_queue_item(
    *,
    queue_rank: int,
    bucket_type: str,
    bucket_key: str,
    bucket_rows: list[dict[str, Any]],
    representative_limit: int,
) -> dict[str, Any]:
    representatives = _iteration_action_plan_bucket_representatives(
        bucket_rows,
        representative_limit=representative_limit,
    )
    item = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_artifact_catalog_iteration_action_plan_bucket_queue_row",
        "bucket_type": bucket_type,
        "bucket_key": bucket_key,
        "queue_rank": int(queue_rank),
        "action": bucket_key if bucket_type == "action" else None,
        "source_queue": bucket_key if bucket_type == "source_queue" else None,
        "action_item_count": len(bucket_rows),
        "unique_iteration_count": len(
            {
                str(row.get("iteration_id"))
                for row in bucket_rows
                if row.get("iteration_id") is not None
            }
        ),
        "primary_action_count": sum(
            1 for row in bucket_rows if bool(row.get("is_primary_action", False))
        ),
        "blocked_by_prior_action_count": sum(
            1
            for row in bucket_rows
            if bool(row.get("blocked_by_prior_action", False))
        ),
        "total_action_count": sum(_row_int(row, "action_count") for row in bucket_rows),
        "total_deduped_validation_request_count": sum(
            _row_int(row, "deduped_validation_request_count") for row in bucket_rows
        ),
        "total_preflight_blocked_trial_estimate": sum(
            _row_int(row, "preflight_blocked_trial_estimate") for row in bucket_rows
        ),
        "total_artifact_missing_count": sum(
            _row_int(row, "artifact_missing_count") for row in bucket_rows
        ),
        "representative_limit": int(representative_limit),
        "representative_count": len(representatives),
        "representative_iteration_ids": [
            str(row.get("iteration_id"))
            for row in representatives
            if row.get("iteration_id") is not None
        ],
        "representative_actions": [
            str(row.get("action"))
            for row in representatives
            if row.get("action") is not None
        ],
        "representative_source_queues": [
            _list_value(row.get("source_queues")) for row in representatives
        ],
        "descriptor_only": all(bool(row.get("descriptor_only", False)) for row in bucket_rows),
        "strict_validation_executed": any(
            bool(row.get("strict_validation_executed", False)) for row in bucket_rows
        ),
        "candidate_pack_written": any(
            bool(row.get("candidate_pack_written", False)) for row in bucket_rows
        ),
        "replay_command_execution_authorized": False,
        "strict_validation_authorized": False,
        "candidate_pack_write_authorized": False,
    }
    require_sandbox_boundary(
        item,
        payload_name="sandbox_artifact_catalog_iteration_action_plan_bucket_queue_row",
    )
    return item


def _iteration_action_plan_bucket_queue(
    rows: list[dict[str, Any]],
    *,
    limit: int = SANDBOX_ARTIFACT_CATALOG_ITERATION_ACTION_PLAN_BUCKET_QUEUE_LIMIT,
    representative_limit: int = SANDBOX_ARTIFACT_CATALOG_ITERATION_ACTION_PLAN_BUCKET_REPRESENTATIVE_LIMIT,
) -> list[dict[str, Any]]:
    if limit <= 0:
        raise ValueError("iteration action-plan bucket queue limit must be positive")
    bucket_rows: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        for key in _iteration_action_plan_bucket_keys(row):
            bucket_rows.setdefault(key, []).append(row)
    sorted_buckets = sorted(
        bucket_rows.items(),
        key=lambda item: (
            -len(item[1]),
            -sum(1 for row in item[1] if bool(row.get("is_primary_action", False))),
            item[0][0],
            item[0][1],
        ),
    )
    return [
        _iteration_action_plan_bucket_queue_item(
            queue_rank=rank,
            bucket_type=bucket_type,
            bucket_key=bucket_key,
            bucket_rows=rows_for_bucket,
            representative_limit=representative_limit,
        )
        for rank, ((bucket_type, bucket_key), rows_for_bucket) in enumerate(
            sorted_buckets[:limit],
            start=1,
        )
    ]


def _iteration_action_plan_bucket_representative_parquet_rows(
    bucket_queue: list[dict[str, Any]],
    action_plan_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bucket_item in bucket_queue:
        bucket_type = str(bucket_item.get("bucket_type") or "")
        bucket_key = str(bucket_item.get("bucket_key") or "")
        bucket_rows = [
            row
            for row in action_plan_rows
            if (bucket_type, bucket_key) in _iteration_action_plan_bucket_keys(row)
        ]
        representatives = _iteration_action_plan_bucket_representatives(
            bucket_rows,
            representative_limit=_row_int(bucket_item, "representative_limit"),
        )
        for representative_rank, representative in enumerate(
            representatives,
            start=1,
        ):
            row = {
                **sandbox_boundary_metadata(),
                "artifact_family": "rapid_strategy_iteration_sandbox_artifact_catalog_iteration_action_plan_bucket_representative_parquet_row",
                "bucket_type": bucket_type,
                "bucket_key": bucket_key,
                "bucket_queue_rank": _row_int(bucket_item, "queue_rank"),
                "representative_rank": int(representative_rank),
                "bucket_action": bucket_key if bucket_type == "action" else None,
                "bucket_source_queue": bucket_key if bucket_type == "source_queue" else None,
                "iteration_id": representative.get("iteration_id"),
                "run_id": representative.get("run_id"),
                "iteration_status": representative.get("iteration_status"),
                "next_action": representative.get("next_action"),
                "primary_recommended_action": representative.get(
                    "primary_recommended_action"
                ),
                "representative_action": representative.get("action"),
                "action_priority": _row_int(representative, "action_priority"),
                "action_rank": _row_int(representative, "action_rank"),
                "is_primary_action": bool(
                    representative.get("is_primary_action", False)
                ),
                "blocked_by_prior_action": bool(
                    representative.get("blocked_by_prior_action", False)
                ),
                "source_queues": _list_value(representative.get("source_queues")),
                "input_replay_context_id": representative.get(
                    "input_replay_context_id"
                ),
                "input_replay_command": representative.get("input_replay_command"),
                "input_replay_strategy_input_mode": representative.get(
                    "input_replay_strategy_input_mode"
                ),
                "input_replay_venue_input_mode": representative.get(
                    "input_replay_venue_input_mode"
                ),
                "brief_status": representative.get("brief_status"),
                "artifact_availability_status": representative.get(
                    "artifact_availability_status"
                ),
                "artifact_missing_keys": _list_value(
                    representative.get("artifact_missing_keys")
                ),
                "iteration_manifest_path": representative.get(
                    "iteration_manifest_path"
                ),
                "agent_brief_json_path": representative.get("agent_brief_json_path"),
                "strategy_catalog_json_path": representative.get(
                    "strategy_catalog_json_path"
                ),
                "venue_archive_manifest_path": representative.get(
                    "venue_archive_manifest_path"
                ),
                "action_count": _row_int(representative, "action_count"),
                "deduped_validation_request_count": _row_int(
                    representative,
                    "deduped_validation_request_count",
                ),
                "preflight_blocked_trial_estimate": _row_int(
                    representative,
                    "preflight_blocked_trial_estimate",
                ),
                "artifact_missing_count": _row_int(
                    representative,
                    "artifact_missing_count",
                ),
                "descriptor_only": bool(representative.get("descriptor_only", False)),
                "strict_validation_executed": bool(
                    representative.get("strict_validation_executed", False)
                ),
                "candidate_pack_written": bool(
                    representative.get("candidate_pack_written", False)
                ),
                "replay_command_execution_authorized": False,
                "strict_validation_authorized": False,
                "candidate_pack_write_authorized": False,
            }
            require_sandbox_boundary(
                row,
                payload_name="sandbox_artifact_catalog_iteration_action_plan_bucket_representative_parquet_row",
            )
            rows.append(row)
    return rows


def _strict_validation_bundle_catalog_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if row.get("artifact_kind")
        in {"run_strict_validation_request_bundle", "suite_strict_validation_request_bundle"}
    ]


def _strict_validation_bundle_status(row: dict[str, Any]) -> str:
    if bool(row.get("candidate_pack_written", False)):
        return "invalid_candidate_pack_written"
    if bool(row.get("strict_validation_executed", False)):
        return "validation_executed"
    if _row_int(row, "strict_validation_deduped_request_count") > 0:
        return "descriptor_ready"
    if _row_int(row, "strict_validation_request_count") > 0:
        return "deduped_empty"
    return "empty"


def _strict_validation_bundle_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    bundle_rows = _strict_validation_bundle_catalog_rows(rows)
    source_scope_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    for row in bundle_rows:
        source_scope = str(row.get("strict_validation_source_scope") or row.get("scope") or "unknown")
        source_scope_counts[source_scope] = source_scope_counts.get(source_scope, 0) + 1
        status = _strict_validation_bundle_status(row)
        status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "artifact_count": len(bundle_rows),
        "request_count": sum(_row_int(row, "strict_validation_request_count") for row in bundle_rows),
        "deduped_request_count": sum(
            _row_int(row, "strict_validation_deduped_request_count") for row in bundle_rows
        ),
        "duplicates_removed": sum(
            _row_int(row, "strict_validation_duplicates_removed") for row in bundle_rows
        ),
        "descriptor_count": sum(_row_int(row, "descriptor_count") for row in bundle_rows),
        "source_scope_counts": dict(sorted(source_scope_counts.items())),
        "status_counts": dict(sorted(status_counts.items())),
    }


def _strict_validation_bundle_queue_item(row: dict[str, Any], *, queue_rank: int) -> dict[str, Any]:
    item = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_artifact_catalog_strict_validation_bundle_queue_item",
        "queue_rank": int(queue_rank),
        "strict_validation_bundle_status": _strict_validation_bundle_status(row),
        "artifact_kind": row.get("artifact_kind"),
        "artifact_path": row.get("artifact_path"),
        "artifact_path_relative": row.get("artifact_path_relative"),
        "artifact_dir": row.get("artifact_dir"),
        "bundle_id": row.get("bundle_id"),
        "source_scope": row.get("strict_validation_source_scope") or row.get("scope"),
        "source_dir": row.get("source_dir"),
        "source_manifest_path": row.get("source_manifest_path"),
        "strict_validation_entrypoint": row.get("strict_validation_entrypoint"),
        "strict_validation_command": row.get("strict_validation_command"),
        "execution_mode": row.get("strict_validation_execution_mode"),
        "descriptor_only": bool(row.get("descriptor_only", False)),
        "request_count": _row_int(row, "strict_validation_request_count"),
        "deduped_request_count": _row_int(row, "strict_validation_deduped_request_count"),
        "duplicates_removed": _row_int(row, "strict_validation_duplicates_removed"),
        "descriptor_count": _row_int(row, "descriptor_count"),
        "strict_validation_executed": bool(row.get("strict_validation_executed", False)),
        "candidate_pack_written": bool(row.get("candidate_pack_written", False)),
        "strict_validation_authorized": False,
        "candidate_pack_write_authorized": False,
    }
    require_sandbox_boundary(
        item,
        payload_name="sandbox_artifact_catalog_strict_validation_bundle_queue_item",
    )
    return item


def _strict_validation_bundle_queue(
    rows: list[dict[str, Any]],
    *,
    limit: int = SANDBOX_ARTIFACT_CATALOG_STRICT_VALIDATION_BUNDLE_QUEUE_LIMIT,
) -> list[dict[str, Any]]:
    bundle_rows = sorted(
        _strict_validation_bundle_catalog_rows(rows),
        key=lambda row: (
            -_row_int(row, "strict_validation_deduped_request_count"),
            -_row_int(row, "strict_validation_request_count"),
            -_row_int(row, "strict_validation_duplicates_removed"),
            str(row.get("artifact_path_relative") or row.get("artifact_path") or ""),
        ),
    )
    return [
        _strict_validation_bundle_queue_item(row, queue_rank=rank)
        for rank, row in enumerate(bundle_rows[:limit], start=1)
    ]


def _strict_validation_bundle_queue_parquet_rows(
    queue: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in queue:
        row = {
            **sandbox_boundary_metadata(),
            "artifact_family": "rapid_strategy_iteration_sandbox_artifact_catalog_strict_validation_bundle_queue_parquet_row",
            "queue_rank": _row_int(item, "queue_rank"),
            "strict_validation_bundle_status": item.get("strict_validation_bundle_status"),
            "artifact_kind": item.get("artifact_kind"),
            "artifact_path": item.get("artifact_path"),
            "artifact_path_relative": item.get("artifact_path_relative"),
            "artifact_dir": item.get("artifact_dir"),
            "bundle_id": item.get("bundle_id"),
            "source_scope": item.get("source_scope"),
            "source_dir": item.get("source_dir"),
            "source_manifest_path": item.get("source_manifest_path"),
            "strict_validation_entrypoint": item.get("strict_validation_entrypoint"),
            "strict_validation_command": item.get("strict_validation_command"),
            "execution_mode": item.get("execution_mode"),
            "descriptor_only": bool(item.get("descriptor_only", False)),
            "request_count": _row_int(item, "request_count"),
            "deduped_request_count": _row_int(item, "deduped_request_count"),
            "duplicates_removed": _row_int(item, "duplicates_removed"),
            "descriptor_count": _row_int(item, "descriptor_count"),
            "strict_validation_executed": bool(item.get("strict_validation_executed", False)),
            "candidate_pack_written": bool(item.get("candidate_pack_written", False)),
            "strict_validation_authorized": False,
            "candidate_pack_write_authorized": False,
        }
        require_sandbox_boundary(
            row,
            payload_name="sandbox_artifact_catalog_strict_validation_bundle_queue_parquet_row",
        )
        rows.append(row)
    return rows


def _strict_validation_descriptor_status(row: dict[str, Any]) -> str:
    if bool(row.get("candidate_pack_written", False)):
        return "invalid_candidate_pack_written"
    if bool(row.get("strict_validation_executed", False)):
        return "validation_executed"
    if bool(row.get("descriptor_only", False)):
        return "descriptor_ready"
    return "not_descriptor_only"


def _strict_validation_descriptor_parquet_row(
    descriptor: dict[str, Any],
    *,
    descriptor_rank: int,
    bundle_path: Path,
    root_dir: Path,
    kind: str,
    bundle_payload: dict[str, Any],
) -> dict[str, Any]:
    require_sandbox_boundary(
        descriptor,
        payload_name="sandbox_artifact_catalog_strict_validation_descriptor_source",
    )
    required_evidence = _list_value(descriptor.get("required_evidence"))
    source_metrics = _dict_value(descriptor.get("source_metrics"))
    source_trial_context = _dict_value(descriptor.get("source_trial_context"))
    market_source = _dict_value(
        source_trial_context.get("market_source") or descriptor.get("source_market_source")
    )
    row = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_artifact_catalog_strict_validation_descriptor_parquet_row",
        "descriptor_rank": int(descriptor_rank),
        "artifact_kind": kind,
        "bundle_artifact_path": str(bundle_path),
        "bundle_artifact_path_relative": str(bundle_path.relative_to(root_dir)),
        "bundle_artifact_dir": str(bundle_path.parent),
        "bundle_id": descriptor.get("bundle_id") or bundle_payload.get("bundle_id"),
        "descriptor_id": descriptor.get("descriptor_id"),
        "dedupe_key": descriptor.get("dedupe_key"),
        "source_scope": descriptor.get("source_scope") or bundle_payload.get("source_scope"),
        "source_dir": descriptor.get("source_dir") or bundle_payload.get("source_dir"),
        "source_manifest_path": descriptor.get("source_manifest_path")
        or bundle_payload.get("source_manifest_path"),
        "source_request_id": descriptor.get("source_request_id"),
        "source_run_id": descriptor.get("source_run_id"),
        "source_trial_id": descriptor.get("source_trial_id"),
        "suite_id": descriptor.get("suite_id"),
        "case_id": descriptor.get("case_id"),
        "hypothesis_id": descriptor.get("hypothesis_id"),
        "family": descriptor.get("family"),
        "venue": descriptor.get("venue"),
        "symbol": descriptor.get("symbol"),
        "reason": descriptor.get("reason"),
        "requested_validation": descriptor.get("requested_validation"),
        "strict_validation_entrypoint": descriptor.get("strict_validation_entrypoint")
        or bundle_payload.get("strict_validation_entrypoint"),
        "strict_validation_command": descriptor.get("strict_validation_command")
        or bundle_payload.get("strict_validation_command"),
        "execution_mode": descriptor.get("execution_mode") or bundle_payload.get("execution_mode"),
        "descriptor_only": bool(descriptor.get("descriptor_only", False)),
        "required_evidence_count": len(required_evidence),
        "required_evidence": [str(item) for item in required_evidence],
        "source_metric_score": _numeric_value(source_metrics, "score"),
        "source_metric_rank": _numeric_value(source_metrics, "rank"),
        "source_metric_net_return": _numeric_value(source_metrics, "net_return"),
        "source_metric_expectancy": _numeric_value(source_metrics, "expectancy"),
        "source_metric_trade_count": _numeric_value(source_metrics, "trade_count"),
        "source_venue_descriptor_id": descriptor.get("source_venue_descriptor_id")
        or source_trial_context.get("venue_descriptor_id"),
        "source_market_start": descriptor.get("source_market_start")
        or source_trial_context.get("market_start"),
        "source_market_end": descriptor.get("source_market_end")
        or source_trial_context.get("market_end"),
        "source_routing_mode": market_source.get("routing_mode"),
        "source_data_path": market_source.get("data_path"),
        "source_container_kind": descriptor.get("source_container_kind")
        or market_source.get("container_kind"),
        "source_selected_member_suffix": descriptor.get("source_selected_member_suffix")
        or market_source.get("selected_member_suffix"),
        "source_selected_member_count": int(
            descriptor.get("source_selected_member_count")
            or market_source.get("selected_member_count")
            or 0
        ),
        "strict_validation_executed": bool(descriptor.get("strict_validation_executed", False)),
        "candidate_pack_written": bool(descriptor.get("candidate_pack_written", False)),
        "strict_validation_authorized": False,
        "candidate_pack_write_authorized": False,
    }
    require_sandbox_boundary(
        row,
        payload_name="sandbox_artifact_catalog_strict_validation_descriptor_parquet_row",
    )
    return row


def _strict_validation_descriptor_parquet_rows(
    path: Path,
    *,
    root_dir: Path,
    kind: str,
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    if kind not in {"run_strict_validation_request_bundle", "suite_strict_validation_request_bundle"}:
        return []
    descriptors = payload.get("descriptors", [])
    if not isinstance(descriptors, list):
        raise ValueError(f"strict-validation request bundle descriptors must be a list: {path}")
    rows: list[dict[str, Any]] = []
    for descriptor_rank, descriptor in enumerate(descriptors, start=1):
        if not isinstance(descriptor, dict):
            raise ValueError(f"strict-validation request bundle descriptor must be an object: {path}")
        rows.append(
            _strict_validation_descriptor_parquet_row(
                descriptor,
                descriptor_rank=descriptor_rank,
                bundle_path=path,
                root_dir=root_dir,
                kind=kind,
                bundle_payload=payload,
            )
        )
    return rows


def _strict_validation_descriptor_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    source_scope_counts: dict[str, int] = {}
    venue_counts: dict[str, int] = {}
    symbol_counts: dict[str, int] = {}
    requested_validation_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    for row in rows:
        for counts, key in (
            (source_scope_counts, "source_scope"),
            (venue_counts, "venue"),
            (symbol_counts, "symbol"),
            (requested_validation_counts, "requested_validation"),
        ):
            value = str(row.get(key) or "unknown")
            counts[value] = counts.get(value, 0) + 1
        status = _strict_validation_descriptor_status(row)
        status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "descriptor_count": len(rows),
        "source_scope_counts": dict(sorted(source_scope_counts.items())),
        "venue_counts": dict(sorted(venue_counts.items())),
        "symbol_counts": dict(sorted(symbol_counts.items())),
        "requested_validation_counts": dict(sorted(requested_validation_counts.items())),
        "status_counts": dict(sorted(status_counts.items())),
    }


def _source_metric_sort_value(row: dict[str, Any]) -> float:
    value = row.get("source_metric_score")
    if value is None:
        return 0.0
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    if score != score:
        return 0.0
    return score


def _source_metric_rank_sort_value(row: dict[str, Any]) -> float:
    value = row.get("source_metric_rank")
    if value is None:
        return 999999999.0
    try:
        rank = float(value)
    except (TypeError, ValueError):
        return 999999999.0
    if rank != rank:
        return 999999999.0
    return rank


def _strict_validation_descriptor_queue_item(
    row: dict[str, Any],
    *,
    queue_rank: int,
) -> dict[str, Any]:
    item = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_artifact_catalog_strict_validation_descriptor_queue_item",
        "queue_rank": int(queue_rank),
        "descriptor_status": _strict_validation_descriptor_status(row),
        "artifact_kind": row.get("artifact_kind"),
        "bundle_artifact_path": row.get("bundle_artifact_path"),
        "bundle_artifact_path_relative": row.get("bundle_artifact_path_relative"),
        "bundle_artifact_dir": row.get("bundle_artifact_dir"),
        "bundle_id": row.get("bundle_id"),
        "descriptor_id": row.get("descriptor_id"),
        "dedupe_key": row.get("dedupe_key"),
        "source_scope": row.get("source_scope"),
        "source_dir": row.get("source_dir"),
        "source_manifest_path": row.get("source_manifest_path"),
        "source_request_id": row.get("source_request_id"),
        "source_run_id": row.get("source_run_id"),
        "source_trial_id": row.get("source_trial_id"),
        "suite_id": row.get("suite_id"),
        "case_id": row.get("case_id"),
        "hypothesis_id": row.get("hypothesis_id"),
        "family": row.get("family"),
        "venue": row.get("venue"),
        "symbol": row.get("symbol"),
        "reason": row.get("reason"),
        "requested_validation": row.get("requested_validation"),
        "strict_validation_entrypoint": row.get("strict_validation_entrypoint"),
        "strict_validation_command": row.get("strict_validation_command"),
        "execution_mode": row.get("execution_mode"),
        "required_evidence_count": _row_int(row, "required_evidence_count"),
        "required_evidence": list(row.get("required_evidence") or []),
        "source_metric_score": row.get("source_metric_score"),
        "source_metric_rank": row.get("source_metric_rank"),
        "source_metric_net_return": row.get("source_metric_net_return"),
        "source_metric_expectancy": row.get("source_metric_expectancy"),
        "source_metric_trade_count": row.get("source_metric_trade_count"),
        "source_venue_descriptor_id": row.get("source_venue_descriptor_id"),
        "source_market_start": row.get("source_market_start"),
        "source_market_end": row.get("source_market_end"),
        "source_routing_mode": row.get("source_routing_mode"),
        "source_data_path": row.get("source_data_path"),
        "descriptor_only": bool(row.get("descriptor_only", False)),
        "strict_validation_executed": bool(row.get("strict_validation_executed", False)),
        "candidate_pack_written": bool(row.get("candidate_pack_written", False)),
        "strict_validation_authorized": False,
        "candidate_pack_write_authorized": False,
    }
    require_sandbox_boundary(
        item,
        payload_name="sandbox_artifact_catalog_strict_validation_descriptor_queue_item",
    )
    return item


def _strict_validation_descriptor_queue(
    rows: list[dict[str, Any]],
    *,
    limit: int = SANDBOX_ARTIFACT_CATALOG_STRICT_VALIDATION_DESCRIPTOR_QUEUE_LIMIT,
) -> list[dict[str, Any]]:
    sorted_rows = sorted(
        rows,
        key=lambda row: (
            -_source_metric_sort_value(row),
            _source_metric_rank_sort_value(row),
            _row_int(row, "descriptor_rank"),
            str(row.get("descriptor_id") or ""),
            str(row.get("bundle_id") or ""),
        ),
    )
    return [
        _strict_validation_descriptor_queue_item(row, queue_rank=rank)
        for rank, row in enumerate(sorted_rows[:limit], start=1)
    ]


def _strict_validation_descriptor_queue_parquet_rows(
    queue: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in queue:
        row = {
            **sandbox_boundary_metadata(),
            "artifact_family": "rapid_strategy_iteration_sandbox_artifact_catalog_strict_validation_descriptor_queue_parquet_row",
            "queue_rank": _row_int(item, "queue_rank"),
            "descriptor_status": item.get("descriptor_status"),
            "artifact_kind": item.get("artifact_kind"),
            "bundle_artifact_path": item.get("bundle_artifact_path"),
            "bundle_artifact_path_relative": item.get("bundle_artifact_path_relative"),
            "bundle_artifact_dir": item.get("bundle_artifact_dir"),
            "bundle_id": item.get("bundle_id"),
            "descriptor_id": item.get("descriptor_id"),
            "dedupe_key": item.get("dedupe_key"),
            "source_scope": item.get("source_scope"),
            "source_dir": item.get("source_dir"),
            "source_manifest_path": item.get("source_manifest_path"),
            "source_request_id": item.get("source_request_id"),
            "source_run_id": item.get("source_run_id"),
            "source_trial_id": item.get("source_trial_id"),
            "suite_id": item.get("suite_id"),
            "case_id": item.get("case_id"),
            "hypothesis_id": item.get("hypothesis_id"),
            "family": item.get("family"),
            "venue": item.get("venue"),
            "symbol": item.get("symbol"),
            "reason": item.get("reason"),
            "requested_validation": item.get("requested_validation"),
            "strict_validation_entrypoint": item.get("strict_validation_entrypoint"),
            "strict_validation_command": item.get("strict_validation_command"),
            "execution_mode": item.get("execution_mode"),
            "required_evidence_count": _row_int(item, "required_evidence_count"),
            "required_evidence": list(item.get("required_evidence") or []),
            "source_metric_score": item.get("source_metric_score"),
            "source_metric_rank": item.get("source_metric_rank"),
            "source_metric_net_return": item.get("source_metric_net_return"),
            "source_metric_expectancy": item.get("source_metric_expectancy"),
            "source_metric_trade_count": item.get("source_metric_trade_count"),
            "source_venue_descriptor_id": item.get("source_venue_descriptor_id"),
            "source_market_start": item.get("source_market_start"),
            "source_market_end": item.get("source_market_end"),
            "source_routing_mode": item.get("source_routing_mode"),
            "source_data_path": item.get("source_data_path"),
            "descriptor_only": bool(item.get("descriptor_only", False)),
            "strict_validation_executed": bool(
                item.get("strict_validation_executed", False)
            ),
            "candidate_pack_written": bool(item.get("candidate_pack_written", False)),
            "strict_validation_authorized": False,
            "candidate_pack_write_authorized": False,
        }
        require_sandbox_boundary(
            row,
            payload_name="sandbox_artifact_catalog_strict_validation_descriptor_queue_parquet_row",
        )
        rows.append(row)
    return rows


def _strict_validation_descriptor_bucket_key(
    row: dict[str, Any],
    *,
    bucket_type: str,
) -> tuple[str, dict[str, Any]]:
    venue = str(row.get("venue") or "unknown")
    symbol = str(row.get("symbol") or "unknown")
    requested_validation = str(row.get("requested_validation") or "unknown")
    if bucket_type == "venue_symbol_requested_validation":
        return (
            f"{venue}|{symbol}|{requested_validation}",
            {
                "venue": venue,
                "symbol": symbol,
                "requested_validation": requested_validation,
                "source_scope": None,
            },
        )
    return (
        f"{venue}|{symbol}",
        {
            "venue": venue,
            "symbol": symbol,
            "requested_validation": None,
            "source_scope": None,
        },
    )


def _strict_validation_descriptor_bucket_representative(
    row: dict[str, Any],
) -> dict[str, Any]:
    item = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_artifact_catalog_strict_validation_descriptor_bucket_representative",
        "descriptor_id": row.get("descriptor_id"),
        "bundle_id": row.get("bundle_id"),
        "source_scope": row.get("source_scope"),
        "source_request_id": row.get("source_request_id"),
        "source_run_id": row.get("source_run_id"),
        "source_trial_id": row.get("source_trial_id"),
        "suite_id": row.get("suite_id"),
        "case_id": row.get("case_id"),
        "hypothesis_id": row.get("hypothesis_id"),
        "family": row.get("family"),
        "venue": row.get("venue"),
        "symbol": row.get("symbol"),
        "requested_validation": row.get("requested_validation"),
        "source_metric_score": row.get("source_metric_score"),
        "source_metric_rank": row.get("source_metric_rank"),
        "source_market_start": row.get("source_market_start"),
        "source_market_end": row.get("source_market_end"),
        "source_routing_mode": row.get("source_routing_mode"),
        "source_data_path": row.get("source_data_path"),
        "descriptor_only": bool(row.get("descriptor_only", False)),
        "strict_validation_executed": bool(row.get("strict_validation_executed", False)),
        "candidate_pack_written": bool(row.get("candidate_pack_written", False)),
        "strict_validation_authorized": False,
        "candidate_pack_write_authorized": False,
    }
    require_sandbox_boundary(
        item,
        payload_name="sandbox_artifact_catalog_strict_validation_descriptor_bucket_representative",
    )
    return item


def _strict_validation_descriptor_bucket_queue_item(
    bucket_key: str,
    bucket_rows: list[dict[str, Any]],
    *,
    queue_rank: int,
    bucket_type: str,
    representative_limit: int,
    bucket_fields: dict[str, Any],
) -> dict[str, Any]:
    sorted_rows = sorted(
        bucket_rows,
        key=lambda row: (
            -_source_metric_sort_value(row),
            str(row.get("descriptor_id") or ""),
            str(row.get("source_trial_id") or ""),
        ),
    )
    representatives = sorted_rows[:representative_limit]
    representative_items = [
        _strict_validation_descriptor_bucket_representative(row) for row in representatives
    ]
    scores = [_source_metric_sort_value(row) for row in bucket_rows]
    item = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_artifact_catalog_strict_validation_descriptor_bucket_queue_item",
        "bucket_type": bucket_type,
        "bucket_key": bucket_key,
        "queue_rank": int(queue_rank),
        "venue": bucket_fields.get("venue"),
        "symbol": bucket_fields.get("symbol"),
        "requested_validation": bucket_fields.get("requested_validation"),
        "source_scope": bucket_fields.get("source_scope"),
        "descriptor_count": len(bucket_rows),
        "bundle_count": len({str(row.get("bundle_id")) for row in bucket_rows if row.get("bundle_id")}),
        "source_trial_count": len(
            {str(row.get("source_trial_id")) for row in bucket_rows if row.get("source_trial_id")}
        ),
        "top_source_metric_score": max(scores) if scores else None,
        "representative_limit": int(representative_limit),
        "representative_count": len(representative_items),
        "representative_descriptor_ids": [
            str(row.get("descriptor_id")) for row in representatives if row.get("descriptor_id")
        ],
        "representative_source_trial_ids": [
            str(row.get("source_trial_id")) for row in representatives if row.get("source_trial_id")
        ],
        "representative_bundle_ids": [
            str(row.get("bundle_id")) for row in representatives if row.get("bundle_id")
        ],
        "representatives": representative_items,
        "descriptor_only": all(bool(row.get("descriptor_only", False)) for row in bucket_rows),
        "strict_validation_executed": any(
            bool(row.get("strict_validation_executed", False)) for row in bucket_rows
        ),
        "candidate_pack_written": any(
            bool(row.get("candidate_pack_written", False)) for row in bucket_rows
        ),
        "strict_validation_authorized": False,
        "candidate_pack_write_authorized": False,
    }
    require_sandbox_boundary(
        item,
        payload_name="sandbox_artifact_catalog_strict_validation_descriptor_bucket_queue_item",
    )
    return item


def _strict_validation_descriptor_bucket_queue(
    rows: list[dict[str, Any]],
    *,
    limit: int = SANDBOX_ARTIFACT_CATALOG_STRICT_VALIDATION_DESCRIPTOR_BUCKET_QUEUE_LIMIT,
    representative_limit: int = SANDBOX_ARTIFACT_CATALOG_STRICT_VALIDATION_DESCRIPTOR_BUCKET_REPRESENTATIVE_LIMIT,
) -> list[dict[str, Any]]:
    bucket_rows: dict[tuple[str, str], tuple[dict[str, Any], list[dict[str, Any]]]] = {}
    for row in rows:
        for bucket_type in ("venue_symbol", "venue_symbol_requested_validation"):
            bucket_key, bucket_fields = _strict_validation_descriptor_bucket_key(
                row,
                bucket_type=bucket_type,
            )
            bucket_rows.setdefault((bucket_type, bucket_key), (bucket_fields, []))[1].append(row)

    sorted_buckets = sorted(
        bucket_rows.items(),
        key=lambda item: (
            -len(item[1][1]),
            -max((_source_metric_sort_value(row) for row in item[1][1]), default=0.0),
            item[0][0],
            item[0][1],
        ),
    )
    return [
        _strict_validation_descriptor_bucket_queue_item(
            bucket_key,
            rows_for_bucket,
            queue_rank=rank,
            bucket_type=bucket_type,
            representative_limit=representative_limit,
            bucket_fields=bucket_fields,
        )
        for rank, ((bucket_type, bucket_key), (bucket_fields, rows_for_bucket)) in enumerate(
            sorted_buckets[:limit],
            start=1,
        )
    ]


def _strict_validation_descriptor_bucket_queue_parquet_rows(
    queue: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in queue:
        row = {
            **sandbox_boundary_metadata(),
            "artifact_family": "rapid_strategy_iteration_sandbox_artifact_catalog_strict_validation_descriptor_bucket_queue_parquet_row",
            "bucket_type": item.get("bucket_type"),
            "bucket_key": item.get("bucket_key"),
            "queue_rank": _row_int(item, "queue_rank"),
            "venue": item.get("venue"),
            "symbol": item.get("symbol"),
            "requested_validation": item.get("requested_validation"),
            "source_scope": item.get("source_scope"),
            "descriptor_count": _row_int(item, "descriptor_count"),
            "bundle_count": _row_int(item, "bundle_count"),
            "source_trial_count": _row_int(item, "source_trial_count"),
            "top_source_metric_score": item.get("top_source_metric_score"),
            "representative_limit": _row_int(item, "representative_limit"),
            "representative_count": _row_int(item, "representative_count"),
            "representative_descriptor_ids": list(item.get("representative_descriptor_ids") or []),
            "representative_source_trial_ids": list(
                item.get("representative_source_trial_ids") or []
            ),
            "representative_bundle_ids": list(item.get("representative_bundle_ids") or []),
            "descriptor_only": bool(item.get("descriptor_only", False)),
            "strict_validation_executed": bool(item.get("strict_validation_executed", False)),
            "candidate_pack_written": bool(item.get("candidate_pack_written", False)),
            "strict_validation_authorized": False,
            "candidate_pack_write_authorized": False,
        }
        require_sandbox_boundary(
            row,
            payload_name="sandbox_artifact_catalog_strict_validation_descriptor_bucket_queue_parquet_row",
        )
        rows.append(row)
    return rows


def _strict_validation_descriptor_bucket_representative_parquet_rows(
    queue: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in queue:
        for representative_rank, representative in enumerate(
            item.get("representatives", []),
            start=1,
        ):
            if not isinstance(representative, dict):
                continue
            row = {
                **sandbox_boundary_metadata(),
                "artifact_family": "rapid_strategy_iteration_sandbox_artifact_catalog_strict_validation_descriptor_bucket_representative_parquet_row",
                "bucket_type": item.get("bucket_type"),
                "bucket_key": item.get("bucket_key"),
                "bucket_queue_rank": _row_int(item, "queue_rank"),
                "representative_rank": int(representative_rank),
                "descriptor_id": representative.get("descriptor_id"),
                "bundle_id": representative.get("bundle_id"),
                "source_scope": representative.get("source_scope"),
                "source_request_id": representative.get("source_request_id"),
                "source_run_id": representative.get("source_run_id"),
                "source_trial_id": representative.get("source_trial_id"),
                "suite_id": representative.get("suite_id"),
                "case_id": representative.get("case_id"),
                "hypothesis_id": representative.get("hypothesis_id"),
                "family": representative.get("family"),
                "venue": representative.get("venue"),
                "symbol": representative.get("symbol"),
                "requested_validation": representative.get("requested_validation"),
                "source_metric_score": representative.get("source_metric_score"),
                "source_metric_rank": representative.get("source_metric_rank"),
                "source_market_start": representative.get("source_market_start"),
                "source_market_end": representative.get("source_market_end"),
                "source_routing_mode": representative.get("source_routing_mode"),
                "source_data_path": representative.get("source_data_path"),
                "descriptor_only": bool(representative.get("descriptor_only", False)),
                "strict_validation_executed": bool(
                    representative.get("strict_validation_executed", False)
                ),
                "candidate_pack_written": bool(
                    representative.get("candidate_pack_written", False)
                ),
                "strict_validation_authorized": False,
                "candidate_pack_write_authorized": False,
            }
            require_sandbox_boundary(
                row,
                payload_name="sandbox_artifact_catalog_strict_validation_descriptor_bucket_representative_parquet_row",
            )
            rows.append(row)
    return rows


def _replay_batch_plan_catalog_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row for row in rows if row.get("artifact_kind") == "iteration_input_replay_batch_plan"
    ]


def _replay_batch_plan_status(row: dict[str, Any]) -> str:
    plan_count = _row_int(row, "plan_item_count")
    ready_count = _row_int(row, "ready_source_item_count")
    blocked_count = _row_int(row, "blocked_source_item_count")
    if plan_count > 0 and blocked_count > 0:
        return "ready_with_blocked_sources"
    if plan_count > 0:
        return "ready"
    if ready_count > 0:
        return "ready_without_plan_items"
    if blocked_count > 0:
        return "blocked_only"
    return "empty"


def _replay_batch_plan_catalog_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    replay_rows = _replay_batch_plan_catalog_rows(rows)
    status_counts: dict[str, int] = {}
    for row in replay_rows:
        status = _replay_batch_plan_status(row)
        status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "artifact_count": len(replay_rows),
        "descriptor_count": sum(_row_int(row, "descriptor_count") for row in replay_rows),
        "source_worklist_item_count": sum(
            _row_int(row, "source_worklist_item_count") for row in replay_rows
        ),
        "ready_source_item_count": sum(
            _row_int(row, "ready_source_item_count") for row in replay_rows
        ),
        "blocked_source_item_count": sum(
            _row_int(row, "blocked_source_item_count") for row in replay_rows
        ),
        "suppressed_duplicate_source_item_count": sum(
            _row_int(row, "suppressed_duplicate_source_item_count")
            for row in replay_rows
        ),
        "plan_item_count": sum(_row_int(row, "plan_item_count") for row in replay_rows),
        "unique_ready_replay_context_count": sum(
            _row_int(row, "unique_ready_replay_context_count") for row in replay_rows
        ),
        "ready_archive_bucket_counts": _row_count_map(replay_rows, "ready_archive_bucket_counts"),
        "plan_archive_bucket_counts": _row_count_map(replay_rows, "plan_archive_bucket_counts"),
        "ready_archive_window_bucket_counts": _row_count_map(
            replay_rows,
            "ready_archive_window_bucket_counts",
        ),
        "plan_archive_window_bucket_counts": _row_count_map(
            replay_rows,
            "plan_archive_window_bucket_counts",
        ),
        "status_counts": dict(sorted(status_counts.items())),
    }


def _replay_batch_plan_queue_item(row: dict[str, Any], *, queue_rank: int) -> dict[str, Any]:
    item = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_artifact_catalog_replay_batch_plan_queue_item",
        "queue_rank": int(queue_rank),
        "replay_batch_plan_status": _replay_batch_plan_status(row),
        "artifact_path": row.get("artifact_path"),
        "artifact_path_relative": row.get("artifact_path_relative"),
        "artifact_dir": row.get("artifact_dir"),
        "source_artifact_family": row.get("source_artifact_family"),
        "descriptor_only": bool(row.get("descriptor_only", False)),
        "descriptor_count": _row_int(row, "descriptor_count"),
        "source_worklist_item_count": _row_int(row, "source_worklist_item_count"),
        "ready_source_item_count": _row_int(row, "ready_source_item_count"),
        "blocked_source_item_count": _row_int(row, "blocked_source_item_count"),
        "suppressed_duplicate_source_item_count": _row_int(
            row,
            "suppressed_duplicate_source_item_count",
        ),
        "plan_item_count": _row_int(row, "plan_item_count"),
        "unique_ready_replay_context_count": _row_int(
            row,
            "unique_ready_replay_context_count",
        ),
        "ready_archive_bucket_counts": dict(row.get("ready_archive_bucket_counts") or {}),
        "plan_archive_bucket_counts": dict(row.get("plan_archive_bucket_counts") or {}),
        "ready_archive_window_bucket_counts": dict(row.get("ready_archive_window_bucket_counts") or {}),
        "plan_archive_window_bucket_counts": dict(row.get("plan_archive_window_bucket_counts") or {}),
        "strict_validation_executed": bool(row.get("strict_validation_executed", False)),
        "candidate_pack_written": bool(row.get("candidate_pack_written", False)),
    }
    require_sandbox_boundary(item, payload_name="sandbox_artifact_catalog_replay_batch_plan_queue_item")
    return item


def _replay_batch_plan_queue(
    rows: list[dict[str, Any]],
    *,
    limit: int = SANDBOX_ARTIFACT_CATALOG_REPLAY_BATCH_PLAN_QUEUE_LIMIT,
) -> list[dict[str, Any]]:
    replay_rows = sorted(
        _replay_batch_plan_catalog_rows(rows),
        key=lambda row: (
            -_row_int(row, "plan_item_count"),
            -_row_int(row, "suppressed_duplicate_source_item_count"),
            -_row_int(row, "ready_source_item_count"),
            _row_int(row, "blocked_source_item_count"),
            str(row.get("artifact_path_relative") or row.get("artifact_path") or ""),
        ),
    )
    return [
        _replay_batch_plan_queue_item(row, queue_rank=rank)
        for rank, row in enumerate(replay_rows[:limit], start=1)
    ]


def _replay_batch_plan_bucket_representative(
    row: dict[str, Any],
    *,
    bucket: str,
    ready_key: str,
    plan_key: str,
) -> dict[str, Any]:
    item = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_artifact_catalog_replay_batch_plan_bucket_representative",
        "artifact_path": row.get("artifact_path"),
        "artifact_path_relative": row.get("artifact_path_relative"),
        "artifact_dir": row.get("artifact_dir"),
        "replay_batch_plan_status": _replay_batch_plan_status(row),
        "bucket_ready_source_item_count": _row_map_count(row, ready_key, bucket),
        "bucket_plan_item_count": _row_map_count(row, plan_key, bucket),
        "source_worklist_item_count": _row_int(row, "source_worklist_item_count"),
        "ready_source_item_count": _row_int(row, "ready_source_item_count"),
        "blocked_source_item_count": _row_int(row, "blocked_source_item_count"),
        "suppressed_duplicate_source_item_count": _row_int(
            row,
            "suppressed_duplicate_source_item_count",
        ),
        "descriptor_only": bool(row.get("descriptor_only", False)),
        "strict_validation_executed": bool(row.get("strict_validation_executed", False)),
        "candidate_pack_written": bool(row.get("candidate_pack_written", False)),
        "replay_command_execution_authorized": False,
        "strict_validation_authorized": False,
        "candidate_pack_write_authorized": False,
    }
    require_sandbox_boundary(
        item,
        payload_name="sandbox_artifact_catalog_replay_batch_plan_bucket_representative",
    )
    return item


def _replay_batch_plan_bucket_queue_item(
    bucket: str,
    bucket_rows: list[dict[str, Any]],
    *,
    queue_rank: int,
    bucket_type: str,
    bucket_field: str,
    ready_key: str,
    plan_key: str,
    representative_limit: int,
) -> dict[str, Any]:
    sorted_rows = sorted(
        bucket_rows,
        key=lambda row: (
            -_row_map_count(row, plan_key, bucket),
            -_row_map_count(row, ready_key, bucket),
            str(row.get("artifact_path_relative") or row.get("artifact_path") or ""),
        ),
    )
    representatives = [
        _replay_batch_plan_bucket_representative(
            row,
            bucket=bucket,
            ready_key=ready_key,
            plan_key=plan_key,
        )
        for row in sorted_rows[:representative_limit]
    ]
    item = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_artifact_catalog_replay_batch_plan_bucket_queue_item",
        "queue_rank": int(queue_rank),
        "bucket_type": bucket_type,
        bucket_field: bucket,
        "artifact_count": len(bucket_rows),
        "ready_artifact_count": sum(
            1 for row in bucket_rows if _row_map_count(row, ready_key, bucket) > 0
        ),
        "plan_artifact_count": sum(
            1 for row in bucket_rows if _row_map_count(row, plan_key, bucket) > 0
        ),
        "ready_source_item_count": sum(
            _row_map_count(row, ready_key, bucket) for row in bucket_rows
        ),
        "plan_item_count": sum(
            _row_map_count(row, plan_key, bucket) for row in bucket_rows
        ),
        "representative_limit": representative_limit,
        "representative_count": len(representatives),
        "representatives": representatives,
        "descriptor_only": all(bool(row.get("descriptor_only", False)) for row in bucket_rows),
        "strict_validation_executed": any(
            bool(row.get("strict_validation_executed", False)) for row in bucket_rows
        ),
        "candidate_pack_written": any(
            bool(row.get("candidate_pack_written", False)) for row in bucket_rows
        ),
        "replay_command_execution_authorized": False,
        "strict_validation_authorized": False,
        "candidate_pack_write_authorized": False,
    }
    require_sandbox_boundary(
        item,
        payload_name="sandbox_artifact_catalog_replay_batch_plan_bucket_queue_item",
    )
    return item


def _replay_batch_plan_bucket_queue(
    rows: list[dict[str, Any]],
    *,
    bucket_type: str,
    bucket_field: str,
    ready_key: str,
    plan_key: str,
    limit: int = SANDBOX_ARTIFACT_CATALOG_REPLAY_BATCH_PLAN_BUCKET_QUEUE_LIMIT,
    representative_limit: int = SANDBOX_ARTIFACT_CATALOG_REPLAY_BATCH_PLAN_BUCKET_REPRESENTATIVE_LIMIT,
) -> list[dict[str, Any]]:
    bucket_rows: dict[str, list[dict[str, Any]]] = {}
    for row in _replay_batch_plan_catalog_rows(rows):
        buckets = set()
        ready_value = row.get(ready_key)
        if isinstance(ready_value, dict):
            buckets.update(str(key) for key, value in ready_value.items() if int(value or 0) > 0)
        plan_value = row.get(plan_key)
        if isinstance(plan_value, dict):
            buckets.update(str(key) for key, value in plan_value.items() if int(value or 0) > 0)
        for bucket in buckets:
            bucket_rows.setdefault(bucket, []).append(row)

    queue_input = sorted(
        bucket_rows.items(),
        key=lambda item: (
            -sum(_row_map_count(row, plan_key, item[0]) for row in item[1]),
            -sum(_row_map_count(row, ready_key, item[0]) for row in item[1]),
            item[0],
        ),
    )
    return [
        _replay_batch_plan_bucket_queue_item(
            bucket,
            rows_for_bucket,
            queue_rank=rank,
            bucket_type=bucket_type,
            bucket_field=bucket_field,
            ready_key=ready_key,
            plan_key=plan_key,
            representative_limit=representative_limit,
        )
        for rank, (bucket, rows_for_bucket) in enumerate(queue_input[:limit], start=1)
    ]


def _bucket_queue_key(item: dict[str, Any]) -> str:
    return str(
        item.get("archive_bucket")
        if item.get("bucket_type") == "archive_bucket"
        else item.get("archive_window_bucket")
    )


def _replay_bucket_queue_parquet_rows(
    archive_bucket_queue: list[dict[str, Any]],
    archive_window_bucket_queue: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in [*archive_bucket_queue, *archive_window_bucket_queue]:
        bucket_type = str(item.get("bucket_type") or "")
        bucket_key = _bucket_queue_key(item)
        row = {
            **sandbox_boundary_metadata(),
            "artifact_family": "rapid_strategy_iteration_sandbox_artifact_catalog_replay_bucket_queue_parquet_row",
            "bucket_type": bucket_type,
            "bucket_key": bucket_key,
            "archive_bucket": bucket_key if bucket_type == "archive_bucket" else None,
            "archive_window_bucket": bucket_key if bucket_type == "archive_window_bucket" else None,
            "queue_rank": _row_int(item, "queue_rank"),
            "artifact_count": _row_int(item, "artifact_count"),
            "ready_artifact_count": _row_int(item, "ready_artifact_count"),
            "plan_artifact_count": _row_int(item, "plan_artifact_count"),
            "ready_source_item_count": _row_int(item, "ready_source_item_count"),
            "plan_item_count": _row_int(item, "plan_item_count"),
            "representative_limit": _row_int(item, "representative_limit"),
            "representative_count": _row_int(item, "representative_count"),
            "representative_artifact_paths_relative": [
                str(representative.get("artifact_path_relative") or representative.get("artifact_path") or "")
                for representative in item.get("representatives", [])
                if isinstance(representative, dict)
            ],
            "descriptor_only": bool(item.get("descriptor_only", False)),
            "strict_validation_executed": bool(item.get("strict_validation_executed", False)),
            "candidate_pack_written": bool(item.get("candidate_pack_written", False)),
            "replay_command_execution_authorized": False,
            "strict_validation_authorized": False,
            "candidate_pack_write_authorized": False,
        }
        require_sandbox_boundary(
            row,
            payload_name="sandbox_artifact_catalog_replay_bucket_queue_parquet_row",
        )
        rows.append(row)
    return rows


def _replay_bucket_representative_parquet_rows(
    archive_bucket_queue: list[dict[str, Any]],
    archive_window_bucket_queue: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in [*archive_bucket_queue, *archive_window_bucket_queue]:
        bucket_type = str(item.get("bucket_type") or "")
        bucket_key = _bucket_queue_key(item)
        for representative_rank, representative in enumerate(
            item.get("representatives", []),
            start=1,
        ):
            if not isinstance(representative, dict):
                continue
            row = {
                **sandbox_boundary_metadata(),
                "artifact_family": "rapid_strategy_iteration_sandbox_artifact_catalog_replay_bucket_representative_parquet_row",
                "bucket_type": bucket_type,
                "bucket_key": bucket_key,
                "archive_bucket": bucket_key if bucket_type == "archive_bucket" else None,
                "archive_window_bucket": bucket_key if bucket_type == "archive_window_bucket" else None,
                "bucket_queue_rank": _row_int(item, "queue_rank"),
                "representative_rank": int(representative_rank),
                "artifact_path": representative.get("artifact_path"),
                "artifact_path_relative": representative.get("artifact_path_relative"),
                "artifact_dir": representative.get("artifact_dir"),
                "replay_batch_plan_status": representative.get("replay_batch_plan_status"),
                "bucket_ready_source_item_count": _row_int(
                    representative,
                    "bucket_ready_source_item_count",
                ),
                "bucket_plan_item_count": _row_int(
                    representative,
                    "bucket_plan_item_count",
                ),
                "source_worklist_item_count": _row_int(
                    representative,
                    "source_worklist_item_count",
                ),
                "ready_source_item_count": _row_int(
                    representative,
                    "ready_source_item_count",
                ),
                "blocked_source_item_count": _row_int(
                    representative,
                    "blocked_source_item_count",
                ),
                "suppressed_duplicate_source_item_count": _row_int(
                    representative,
                    "suppressed_duplicate_source_item_count",
                ),
                "descriptor_only": bool(representative.get("descriptor_only", False)),
                "strict_validation_executed": bool(
                    representative.get("strict_validation_executed", False)
                ),
                "candidate_pack_written": bool(
                    representative.get("candidate_pack_written", False)
                ),
                "replay_command_execution_authorized": False,
                "strict_validation_authorized": False,
                "candidate_pack_write_authorized": False,
            }
            require_sandbox_boundary(
                row,
                payload_name="sandbox_artifact_catalog_replay_bucket_representative_parquet_row",
            )
            rows.append(row)
    return rows


def _discover_artifact_paths(root_dir: Path, *, max_files: int) -> list[Path]:
    if max_files <= 0:
        raise ValueError("max_files must be positive")
    paths: list[Path] = []
    known_names = set(KNOWN_SANDBOX_JSON_ARTIFACTS)
    for path in root_dir.rglob("*.json"):
        if path.name not in known_names:
            continue
        paths.append(path)
        if len(paths) >= max_files:
            break
    return sorted(paths)


def index_sandbox_artifacts(
    root_dir: str | Path,
    *,
    output_dir: str | Path | None = None,
    max_files: int = 5000,
    write_report: bool = True,
) -> dict[str, Any]:
    root_path = Path(root_dir)
    if not root_path.exists():
        raise FileNotFoundError(f"sandbox artifact catalog root not found: {root_path}")
    if not root_path.is_dir():
        raise ValueError(f"sandbox artifact catalog root must be a directory: {root_path}")
    root_path = root_path.resolve()
    rows: list[dict[str, Any]] = []
    analysis_bucket_rollup_parquet_rows: list[dict[str, Any]] = []
    global_top_hypothesis_parquet_rows: list[dict[str, Any]] = []
    global_evidence_request_parquet_rows: list[dict[str, Any]] = []
    global_bucket_top_bucket_parquet_rows: list[dict[str, Any]] = []
    strict_validation_descriptor_parquet_rows: list[dict[str, Any]] = []
    iteration_action_plan_parquet_rows: list[dict[str, Any]] = []
    iteration_venue_expansion_gap_worklist_parquet_rows: list[dict[str, Any]] = []
    for path in _discover_artifact_paths(root_path, max_files=max_files):
        payload = _load_artifact(path)
        if payload is None:
            continue
        kind = KNOWN_SANDBOX_JSON_ARTIFACTS[path.name]
        resolved_path = path.resolve()
        rows.append(_catalog_row(resolved_path, root_dir=root_path, kind=kind, payload=payload))
        analysis_bucket_rollup_parquet_rows.extend(
            _analysis_bucket_rollup_parquet_rows(
                resolved_path,
                root_dir=root_path,
                kind=kind,
                payload=payload,
            )
        )
        global_top_hypothesis_parquet_rows.extend(
            _global_top_hypothesis_parquet_rows(
                resolved_path,
                root_dir=root_path,
                kind=kind,
                payload=payload,
            )
        )
        global_evidence_request_parquet_rows.extend(
            _global_evidence_request_parquet_rows(
                resolved_path,
                root_dir=root_path,
                kind=kind,
                payload=payload,
            )
        )
        global_bucket_top_bucket_parquet_rows.extend(
            _global_bucket_top_bucket_parquet_rows(
                resolved_path,
                root_dir=root_path,
                kind=kind,
                payload=payload,
            )
        )
        iteration_action_plan_parquet_rows.extend(
            _iteration_action_plan_parquet_rows(
                resolved_path,
                root_dir=root_path,
                kind=kind,
                payload=payload,
            )
        )
        iteration_venue_expansion_gap_worklist_parquet_rows.extend(
            _iteration_venue_expansion_gap_worklist_parquet_rows(
                resolved_path,
                root_dir=root_path,
                kind=kind,
                payload=payload,
                start_rank=len(iteration_venue_expansion_gap_worklist_parquet_rows) + 1,
            )
        )
        strict_validation_descriptor_parquet_rows.extend(
            _strict_validation_descriptor_parquet_rows(
                resolved_path,
                root_dir=root_path,
                kind=kind,
                payload=payload,
            )
        )

    kind_counts: dict[str, int] = {}
    family_counts: dict[str, int] = {}
    for row in rows:
        kind = str(row.get("artifact_kind", "missing"))
        family = str(row.get("source_artifact_family", "missing"))
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
        family_counts[family] = family_counts.get(family, 0) + 1
    replay_batch_plan_summary = _replay_batch_plan_catalog_summary(rows)
    replay_batch_plan_queue = _replay_batch_plan_queue(rows)
    strict_validation_bundle_summary = _strict_validation_bundle_summary(rows)
    strict_validation_bundle_queue = _strict_validation_bundle_queue(rows)
    strict_validation_descriptor_summary = _strict_validation_descriptor_summary(
        strict_validation_descriptor_parquet_rows
    )
    strict_validation_descriptor_queue = _strict_validation_descriptor_queue(
        strict_validation_descriptor_parquet_rows
    )
    strict_validation_descriptor_bucket_queue = _strict_validation_descriptor_bucket_queue(
        strict_validation_descriptor_parquet_rows
    )
    global_evidence_request_priority_queue = _global_evidence_request_priority_queue(
        global_evidence_request_parquet_rows
    )
    replay_batch_plan_archive_bucket_queue = _replay_batch_plan_bucket_queue(
        rows,
        bucket_type="archive_bucket",
        bucket_field="archive_bucket",
        ready_key="ready_archive_bucket_counts",
        plan_key="plan_archive_bucket_counts",
    )
    replay_batch_plan_archive_window_bucket_queue = _replay_batch_plan_bucket_queue(
        rows,
        bucket_type="archive_window_bucket",
        bucket_field="archive_window_bucket",
        ready_key="ready_archive_window_bucket_counts",
        plan_key="plan_archive_window_bucket_counts",
    )
    iteration_action_plan_summary = _iteration_action_plan_summary(
        iteration_action_plan_parquet_rows
    )
    iteration_venue_expansion_gap_worklist_summary = (
        _iteration_venue_expansion_gap_worklist_summary(
            iteration_venue_expansion_gap_worklist_parquet_rows
        )
    )
    iteration_action_plan_bucket_queue = _iteration_action_plan_bucket_queue(
        iteration_action_plan_parquet_rows
    )
    iteration_action_plan_bucket_representative_parquet_rows = (
        _iteration_action_plan_bucket_representative_parquet_rows(
            iteration_action_plan_bucket_queue,
            iteration_action_plan_parquet_rows,
        )
    )
    global_evidence_request_bucket_queue = _global_evidence_request_bucket_queue(
        global_evidence_request_parquet_rows
    )
    global_evidence_request_bucket_representative_parquet_rows = (
        _global_evidence_request_bucket_representative_parquet_rows(
            global_evidence_request_bucket_queue,
            global_evidence_request_parquet_rows,
        )
    )
    global_evidence_request_summary = _global_evidence_request_summary(
        global_evidence_request_parquet_rows,
        global_evidence_request_priority_queue,
        global_evidence_request_bucket_queue,
        global_evidence_request_bucket_representative_parquet_rows,
    )
    global_evidence_request_source_summary_rows = (
        _global_evidence_request_source_summary_rows(
            global_evidence_request_summary,
            global_evidence_request_parquet_rows,
        )
    )
    global_evidence_request_source_priority_queue = (
        _global_evidence_request_source_priority_queue(
            global_evidence_request_source_summary_rows
        )
    )

    destination = Path(output_dir).resolve() if output_dir is not None else root_path
    json_path = destination / SANDBOX_ARTIFACT_CATALOG_JSON_NAME
    parquet_path = destination / SANDBOX_ARTIFACT_CATALOG_PARQUET_NAME
    sidecar_index_parquet_path = (
        destination / SANDBOX_ARTIFACT_CATALOG_SIDECAR_INDEX_PARQUET_NAME
    )
    analysis_bucket_rollups_parquet_path = (
        destination / SANDBOX_ARTIFACT_CATALOG_ANALYSIS_BUCKET_ROLLUPS_PARQUET_NAME
    )
    global_top_hypotheses_parquet_path = (
        destination / SANDBOX_ARTIFACT_CATALOG_GLOBAL_TOP_HYPOTHESES_PARQUET_NAME
    )
    global_evidence_requests_parquet_path = (
        destination / SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUESTS_PARQUET_NAME
    )
    global_evidence_request_source_summary_parquet_path = (
        destination
        / SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_SOURCE_SUMMARY_PARQUET_NAME
    )
    global_evidence_request_source_priority_queue_parquet_path = (
        destination
        / SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_SOURCE_PRIORITY_QUEUE_PARQUET_NAME
    )
    global_evidence_request_priority_queue_parquet_path = (
        destination
        / SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_PRIORITY_QUEUE_PARQUET_NAME
    )
    global_evidence_request_bucket_queue_parquet_path = (
        destination
        / SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_BUCKET_QUEUE_PARQUET_NAME
    )
    global_evidence_request_bucket_representatives_parquet_path = (
        destination
        / SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_BUCKET_REPRESENTATIVES_PARQUET_NAME
    )
    global_bucket_top_buckets_parquet_path = (
        destination / SANDBOX_ARTIFACT_CATALOG_GLOBAL_BUCKET_TOP_BUCKETS_PARQUET_NAME
    )
    iteration_action_plan_parquet_path = (
        destination / SANDBOX_ARTIFACT_CATALOG_ITERATION_ACTION_PLAN_PARQUET_NAME
    )
    iteration_action_plan_bucket_queue_parquet_path = (
        destination
        / SANDBOX_ARTIFACT_CATALOG_ITERATION_ACTION_PLAN_BUCKET_QUEUE_PARQUET_NAME
    )
    iteration_action_plan_bucket_representatives_parquet_path = (
        destination
        / SANDBOX_ARTIFACT_CATALOG_ITERATION_ACTION_PLAN_BUCKET_REPRESENTATIVES_PARQUET_NAME
    )
    iteration_venue_expansion_gap_worklist_parquet_path = (
        destination
        / SANDBOX_ARTIFACT_CATALOG_ITERATION_VENUE_EXPANSION_GAP_WORKLIST_PARQUET_NAME
    )
    bucket_queue_parquet_path = destination / SANDBOX_ARTIFACT_CATALOG_REPLAY_BUCKET_QUEUE_PARQUET_NAME
    bucket_representatives_parquet_path = (
        destination / SANDBOX_ARTIFACT_CATALOG_REPLAY_BUCKET_REPRESENTATIVES_PARQUET_NAME
    )
    strict_validation_bundle_queue_parquet_path = (
        destination / SANDBOX_ARTIFACT_CATALOG_STRICT_VALIDATION_BUNDLE_QUEUE_PARQUET_NAME
    )
    strict_validation_descriptor_parquet_path = (
        destination / SANDBOX_ARTIFACT_CATALOG_STRICT_VALIDATION_DESCRIPTOR_PARQUET_NAME
    )
    strict_validation_descriptor_queue_parquet_path = (
        destination / SANDBOX_ARTIFACT_CATALOG_STRICT_VALIDATION_DESCRIPTOR_QUEUE_PARQUET_NAME
    )
    strict_validation_descriptor_bucket_queue_parquet_path = (
        destination / SANDBOX_ARTIFACT_CATALOG_STRICT_VALIDATION_DESCRIPTOR_BUCKET_QUEUE_PARQUET_NAME
    )
    strict_validation_descriptor_bucket_representatives_parquet_path = (
        destination
        / SANDBOX_ARTIFACT_CATALOG_STRICT_VALIDATION_DESCRIPTOR_BUCKET_REPRESENTATIVES_PARQUET_NAME
    )
    bucket_queue_parquet_rows = _replay_bucket_queue_parquet_rows(
        replay_batch_plan_archive_bucket_queue,
        replay_batch_plan_archive_window_bucket_queue,
    )
    bucket_representative_parquet_rows = _replay_bucket_representative_parquet_rows(
        replay_batch_plan_archive_bucket_queue,
        replay_batch_plan_archive_window_bucket_queue,
    )
    strict_validation_bundle_queue_parquet_rows = _strict_validation_bundle_queue_parquet_rows(
        strict_validation_bundle_queue
    )
    strict_validation_descriptor_queue_parquet_rows = (
        _strict_validation_descriptor_queue_parquet_rows(strict_validation_descriptor_queue)
    )
    strict_validation_descriptor_bucket_queue_parquet_rows = (
        _strict_validation_descriptor_bucket_queue_parquet_rows(
            strict_validation_descriptor_bucket_queue
        )
    )
    strict_validation_descriptor_bucket_representative_parquet_rows = (
        _strict_validation_descriptor_bucket_representative_parquet_rows(
            strict_validation_descriptor_bucket_queue
        )
    )
    sidecar_index_specs = [
        {
            "sidecar_category": "catalog",
            "sidecar_name": "artifact_catalog",
            "sidecar_role": "all_indexed_sandbox_artifacts",
            "sidecar_path": parquet_path,
            "row_count": len(rows),
        },
        {
            "sidecar_category": "analysis",
            "sidecar_name": "analysis_bucket_rollups",
            "sidecar_role": "flattened_run_analysis_bucket_rollup_rows",
            "sidecar_path": analysis_bucket_rollups_parquet_path,
            "row_count": len(analysis_bucket_rollup_parquet_rows),
        },
        {
            "sidecar_category": "leaderboard",
            "sidecar_name": "global_top_hypotheses",
            "sidecar_role": "flattened_global_leaderboard_top_hypothesis_rows",
            "sidecar_path": global_top_hypotheses_parquet_path,
            "row_count": len(global_top_hypothesis_parquet_rows),
        },
        {
            "sidecar_category": "strict_validation",
            "sidecar_name": "global_evidence_requests",
            "sidecar_role": "flattened_global_leaderboard_evidence_request_trial_rows",
            "sidecar_path": global_evidence_requests_parquet_path,
            "row_count": len(global_evidence_request_parquet_rows),
        },
        {
            "sidecar_category": "strict_validation",
            "sidecar_name": "global_evidence_request_source_summary",
            "sidecar_role": "global_evidence_request_source_context_count_rows",
            "sidecar_path": global_evidence_request_source_summary_parquet_path,
            "row_count": len(global_evidence_request_source_summary_rows),
        },
        {
            "sidecar_category": "strict_validation",
            "sidecar_name": "global_evidence_request_source_priority_queue",
            "sidecar_role": "bounded_global_evidence_request_source_summary_priority_queue_rows",
            "sidecar_path": global_evidence_request_source_priority_queue_parquet_path,
            "row_count": len(global_evidence_request_source_priority_queue),
        },
        {
            "sidecar_category": "strict_validation",
            "sidecar_name": "global_evidence_request_priority_queue",
            "sidecar_role": "bounded_global_leaderboard_evidence_request_priority_queue_rows",
            "sidecar_path": global_evidence_request_priority_queue_parquet_path,
            "row_count": len(global_evidence_request_priority_queue),
        },
        {
            "sidecar_category": "strict_validation",
            "sidecar_name": "global_evidence_request_bucket_queue",
            "sidecar_role": "global_evidence_request_bucket_queue_rows",
            "sidecar_path": global_evidence_request_bucket_queue_parquet_path,
            "row_count": len(global_evidence_request_bucket_queue),
        },
        {
            "sidecar_category": "strict_validation",
            "sidecar_name": "global_evidence_request_bucket_representatives",
            "sidecar_role": "global_evidence_request_bucket_representative_rows",
            "sidecar_path": global_evidence_request_bucket_representatives_parquet_path,
            "row_count": len(
                global_evidence_request_bucket_representative_parquet_rows
            ),
        },
        {
            "sidecar_category": "leaderboard",
            "sidecar_name": "global_bucket_top_buckets",
            "sidecar_role": "flattened_global_leaderboard_top_bucket_rows",
            "sidecar_path": global_bucket_top_buckets_parquet_path,
            "row_count": len(global_bucket_top_bucket_parquet_rows),
        },
        {
            "sidecar_category": "iteration_index",
            "sidecar_name": "iteration_agent_action_plan",
            "sidecar_role": "flattened_iteration_index_agent_action_plan_rows",
            "sidecar_path": iteration_action_plan_parquet_path,
            "row_count": len(iteration_action_plan_parquet_rows),
        },
        {
            "sidecar_category": "iteration_index",
            "sidecar_name": "iteration_venue_expansion_gap_worklist",
            "sidecar_role": "flattened_iteration_index_venue_expansion_gap_worklist_rows",
            "sidecar_path": iteration_venue_expansion_gap_worklist_parquet_path,
            "row_count": len(iteration_venue_expansion_gap_worklist_parquet_rows),
        },
        {
            "sidecar_category": "iteration_index",
            "sidecar_name": "iteration_agent_action_plan_bucket_queue",
            "sidecar_role": "action_and_source_queue_bucket_rows",
            "sidecar_path": iteration_action_plan_bucket_queue_parquet_path,
            "row_count": len(iteration_action_plan_bucket_queue),
        },
        {
            "sidecar_category": "iteration_index",
            "sidecar_name": "iteration_agent_action_plan_bucket_representatives",
            "sidecar_role": "action_and_source_queue_bucket_representative_rows",
            "sidecar_path": iteration_action_plan_bucket_representatives_parquet_path,
            "row_count": len(iteration_action_plan_bucket_representative_parquet_rows),
        },
        {
            "sidecar_category": "replay_batch_plan",
            "sidecar_name": "replay_batch_plan_bucket_queue",
            "sidecar_role": "archive_bucket_and_window_queue_rows",
            "sidecar_path": bucket_queue_parquet_path,
            "row_count": len(bucket_queue_parquet_rows),
        },
        {
            "sidecar_category": "replay_batch_plan",
            "sidecar_name": "replay_batch_plan_bucket_representatives",
            "sidecar_role": "archive_bucket_and_window_representative_rows",
            "sidecar_path": bucket_representatives_parquet_path,
            "row_count": len(bucket_representative_parquet_rows),
        },
        {
            "sidecar_category": "strict_validation",
            "sidecar_name": "strict_validation_bundle_queue",
            "sidecar_role": "descriptor_only_bundle_queue_rows",
            "sidecar_path": strict_validation_bundle_queue_parquet_path,
            "row_count": len(strict_validation_bundle_queue_parquet_rows),
        },
        {
            "sidecar_category": "strict_validation",
            "sidecar_name": "strict_validation_descriptors",
            "sidecar_role": "cross_bundle_descriptor_rows",
            "sidecar_path": strict_validation_descriptor_parquet_path,
            "row_count": len(strict_validation_descriptor_parquet_rows),
        },
        {
            "sidecar_category": "strict_validation",
            "sidecar_name": "strict_validation_descriptor_queue",
            "sidecar_role": "bounded_descriptor_priority_queue_rows",
            "sidecar_path": strict_validation_descriptor_queue_parquet_path,
            "row_count": len(strict_validation_descriptor_queue_parquet_rows),
        },
        {
            "sidecar_category": "strict_validation",
            "sidecar_name": "strict_validation_descriptor_bucket_queue",
            "sidecar_role": "venue_symbol_descriptor_bucket_queue_rows",
            "sidecar_path": strict_validation_descriptor_bucket_queue_parquet_path,
            "row_count": len(strict_validation_descriptor_bucket_queue_parquet_rows),
        },
        {
            "sidecar_category": "strict_validation",
            "sidecar_name": "strict_validation_descriptor_bucket_representatives",
            "sidecar_role": "venue_symbol_descriptor_bucket_representative_rows",
            "sidecar_path": strict_validation_descriptor_bucket_representatives_parquet_path,
            "row_count": len(
                strict_validation_descriptor_bucket_representative_parquet_rows
            ),
        },
    ]
    sidecar_index_rows = _catalog_sidecar_index_rows(
        sidecar_index_specs,
        write_report=write_report,
    )
    payload = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_artifact_catalog",
        "root_dir": str(root_path),
        "output_dir": str(destination),
        "artifact_count": len(rows),
        "artifact_kind_counts": dict(sorted(kind_counts.items())),
        "source_artifact_family_counts": dict(sorted(family_counts.items())),
        "replay_batch_plan_queue_limit": SANDBOX_ARTIFACT_CATALOG_REPLAY_BATCH_PLAN_QUEUE_LIMIT,
        "replay_batch_plan_queue_count": len(replay_batch_plan_queue),
        "strict_validation_bundle_queue_limit": SANDBOX_ARTIFACT_CATALOG_STRICT_VALIDATION_BUNDLE_QUEUE_LIMIT,
        "strict_validation_bundle_queue_count": len(strict_validation_bundle_queue),
        "strict_validation_bundle_summary": strict_validation_bundle_summary,
        "strict_validation_bundle_queue": strict_validation_bundle_queue,
        "strict_validation_bundle_queue_parquet_path": (
            str(strict_validation_bundle_queue_parquet_path) if write_report else None
        ),
        "strict_validation_bundle_queue_parquet_row_count": len(
            strict_validation_bundle_queue_parquet_rows
        ),
        "strict_validation_descriptor_summary": strict_validation_descriptor_summary,
        "strict_validation_descriptor_parquet_path": (
            str(strict_validation_descriptor_parquet_path) if write_report else None
        ),
        "strict_validation_descriptor_parquet_row_count": len(
            strict_validation_descriptor_parquet_rows
        ),
        "strict_validation_descriptor_queue_limit": (
            SANDBOX_ARTIFACT_CATALOG_STRICT_VALIDATION_DESCRIPTOR_QUEUE_LIMIT
        ),
        "strict_validation_descriptor_queue_count": len(strict_validation_descriptor_queue),
        "strict_validation_descriptor_queue": strict_validation_descriptor_queue,
        "strict_validation_descriptor_queue_parquet_path": (
            str(strict_validation_descriptor_queue_parquet_path) if write_report else None
        ),
        "strict_validation_descriptor_queue_parquet_row_count": len(
            strict_validation_descriptor_queue_parquet_rows
        ),
        "strict_validation_descriptor_bucket_queue_limit": (
            SANDBOX_ARTIFACT_CATALOG_STRICT_VALIDATION_DESCRIPTOR_BUCKET_QUEUE_LIMIT
        ),
        "strict_validation_descriptor_bucket_representative_limit": (
            SANDBOX_ARTIFACT_CATALOG_STRICT_VALIDATION_DESCRIPTOR_BUCKET_REPRESENTATIVE_LIMIT
        ),
        "strict_validation_descriptor_bucket_queue_count": len(
            strict_validation_descriptor_bucket_queue
        ),
        "strict_validation_descriptor_bucket_queue": strict_validation_descriptor_bucket_queue,
        "strict_validation_descriptor_bucket_queue_parquet_path": (
            str(strict_validation_descriptor_bucket_queue_parquet_path) if write_report else None
        ),
        "strict_validation_descriptor_bucket_queue_parquet_row_count": len(
            strict_validation_descriptor_bucket_queue_parquet_rows
        ),
        "strict_validation_descriptor_bucket_representatives_parquet_path": (
            str(strict_validation_descriptor_bucket_representatives_parquet_path)
            if write_report
            else None
        ),
        "strict_validation_descriptor_bucket_representative_parquet_row_count": len(
            strict_validation_descriptor_bucket_representative_parquet_rows
        ),
        "replay_batch_plan_bucket_queue_limit": SANDBOX_ARTIFACT_CATALOG_REPLAY_BATCH_PLAN_BUCKET_QUEUE_LIMIT,
        "replay_batch_plan_bucket_representative_limit": SANDBOX_ARTIFACT_CATALOG_REPLAY_BATCH_PLAN_BUCKET_REPRESENTATIVE_LIMIT,
        "replay_batch_plan_archive_bucket_queue_count": len(
            replay_batch_plan_archive_bucket_queue
        ),
        "replay_batch_plan_archive_window_bucket_queue_count": len(
            replay_batch_plan_archive_window_bucket_queue
        ),
        "replay_batch_plan_summary": replay_batch_plan_summary,
        "replay_batch_plan_queue": replay_batch_plan_queue,
        "replay_batch_plan_archive_bucket_queue": replay_batch_plan_archive_bucket_queue,
        "replay_batch_plan_archive_window_bucket_queue": replay_batch_plan_archive_window_bucket_queue,
        "max_files": max_files,
        "truncated": len(rows) >= max_files,
        "catalog_json_path": str(json_path) if write_report else None,
        "catalog_parquet_path": str(parquet_path) if write_report else None,
        "catalog_sidecar_index_parquet_path": (
            str(sidecar_index_parquet_path) if write_report else None
        ),
        "catalog_sidecar_index_row_count": len(sidecar_index_rows),
        "catalog_sidecar_index": sidecar_index_rows,
        "analysis_bucket_rollups_parquet_path": (
            str(analysis_bucket_rollups_parquet_path) if write_report else None
        ),
        "analysis_bucket_rollup_parquet_row_count": len(
            analysis_bucket_rollup_parquet_rows
        ),
        "global_top_hypotheses_parquet_path": (
            str(global_top_hypotheses_parquet_path) if write_report else None
        ),
        "global_top_hypothesis_parquet_row_count": len(
            global_top_hypothesis_parquet_rows
        ),
        "global_evidence_requests_parquet_path": (
            str(global_evidence_requests_parquet_path) if write_report else None
        ),
        "global_evidence_request_parquet_row_count": len(
            global_evidence_request_parquet_rows
        ),
        "global_evidence_request_summary": global_evidence_request_summary,
        "global_evidence_request_source_summary_parquet_path": (
            str(global_evidence_request_source_summary_parquet_path)
            if write_report
            else None
        ),
        "global_evidence_request_source_summary_parquet_row_count": len(
            global_evidence_request_source_summary_rows
        ),
        "global_evidence_request_source_priority_queue_limit": (
            SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_SOURCE_PRIORITY_QUEUE_LIMIT
        ),
        "global_evidence_request_source_priority_queue_count": len(
            global_evidence_request_source_priority_queue
        ),
        "global_evidence_request_source_priority_queue": (
            global_evidence_request_source_priority_queue
        ),
        "global_evidence_request_source_priority_queue_parquet_path": (
            str(global_evidence_request_source_priority_queue_parquet_path)
            if write_report
            else None
        ),
        "global_evidence_request_source_priority_queue_parquet_row_count": len(
            global_evidence_request_source_priority_queue
        ),
        "global_evidence_request_count": global_evidence_request_summary[
            "evidence_request_count"
        ],
        "global_evidence_request_unique_trial_count": (
            global_evidence_request_summary["unique_evidence_request_trial_count"]
        ),
        "global_evidence_request_hypothesis_count": (
            global_evidence_request_summary["requesting_hypothesis_count"]
        ),
        "global_evidence_request_source_leaderboard_count": (
            global_evidence_request_summary["source_leaderboard_count"]
        ),
        "global_evidence_request_requested_validation_counts": (
            global_evidence_request_summary["requested_validation_counts"]
        ),
        "global_evidence_request_leaderboard_decision_counts": (
            global_evidence_request_summary["leaderboard_decision_counts"]
        ),
        "global_evidence_request_family_counts": (
            global_evidence_request_summary["family_counts"]
        ),
        "global_evidence_request_tested_venue_counts": (
            global_evidence_request_summary["tested_venue_counts"]
        ),
        "global_evidence_request_tested_symbol_counts": (
            global_evidence_request_summary["tested_symbol_counts"]
        ),
        "global_evidence_request_bucket_type_counts": (
            global_evidence_request_summary["bucket_type_counts"]
        ),
        "global_evidence_request_source_context_available_count": (
            global_evidence_request_summary["source_context_available_count"]
        ),
        "global_evidence_request_source_context_missing_count": (
            global_evidence_request_summary["source_context_missing_count"]
        ),
        "global_evidence_request_source_venue_counts": (
            global_evidence_request_summary["source_venue_counts"]
        ),
        "global_evidence_request_source_symbol_counts": (
            global_evidence_request_summary["source_symbol_counts"]
        ),
        "global_evidence_request_source_data_family_counts": (
            global_evidence_request_summary["source_data_family_counts"]
        ),
        "global_evidence_request_source_interval_counts": (
            global_evidence_request_summary["source_interval_counts"]
        ),
        "global_evidence_request_source_routing_mode_counts": (
            global_evidence_request_summary["source_routing_mode_counts"]
        ),
        "global_evidence_request_source_venue_descriptor_counts": (
            global_evidence_request_summary["source_venue_descriptor_counts"]
        ),
        "global_evidence_request_source_data_path_counts": (
            global_evidence_request_summary["source_data_path_counts"]
        ),
        "global_evidence_request_priority_queue_limit": (
            SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_PRIORITY_QUEUE_LIMIT
        ),
        "global_evidence_request_priority_queue_count": len(
            global_evidence_request_priority_queue
        ),
        "global_evidence_request_priority_queue": global_evidence_request_priority_queue,
        "global_evidence_request_priority_queue_parquet_path": (
            str(global_evidence_request_priority_queue_parquet_path)
            if write_report
            else None
        ),
        "global_evidence_request_priority_queue_parquet_row_count": len(
            global_evidence_request_priority_queue
        ),
        "global_evidence_request_bucket_queue_limit": (
            SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_BUCKET_QUEUE_LIMIT
        ),
        "global_evidence_request_bucket_queue_count": len(
            global_evidence_request_bucket_queue
        ),
        "global_evidence_request_bucket_queue": global_evidence_request_bucket_queue,
        "global_evidence_request_bucket_queue_parquet_path": (
            str(global_evidence_request_bucket_queue_parquet_path)
            if write_report
            else None
        ),
        "global_evidence_request_bucket_queue_parquet_row_count": len(
            global_evidence_request_bucket_queue
        ),
        "global_evidence_request_bucket_representatives_parquet_path": (
            str(global_evidence_request_bucket_representatives_parquet_path)
            if write_report
            else None
        ),
        "global_evidence_request_bucket_representative_parquet_row_count": len(
            global_evidence_request_bucket_representative_parquet_rows
        ),
        "global_bucket_top_buckets_parquet_path": (
            str(global_bucket_top_buckets_parquet_path) if write_report else None
        ),
        "global_bucket_top_bucket_parquet_row_count": len(
            global_bucket_top_bucket_parquet_rows
        ),
        "iteration_agent_action_plan_summary": iteration_action_plan_summary,
        "iteration_agent_action_plan_bucket_queue_limit": (
            SANDBOX_ARTIFACT_CATALOG_ITERATION_ACTION_PLAN_BUCKET_QUEUE_LIMIT
        ),
        "iteration_agent_action_plan_bucket_representative_limit": (
            SANDBOX_ARTIFACT_CATALOG_ITERATION_ACTION_PLAN_BUCKET_REPRESENTATIVE_LIMIT
        ),
        "iteration_agent_action_plan_bucket_queue_count": len(
            iteration_action_plan_bucket_queue
        ),
        "iteration_agent_action_plan_bucket_queue": iteration_action_plan_bucket_queue,
        "iteration_agent_action_plan_parquet_path": (
            str(iteration_action_plan_parquet_path) if write_report else None
        ),
        "iteration_agent_action_plan_parquet_row_count": len(
            iteration_action_plan_parquet_rows
        ),
        "iteration_venue_expansion_gap_worklist_summary": (
            iteration_venue_expansion_gap_worklist_summary
        ),
        "iteration_venue_expansion_gap_worklist_parquet_path": (
            str(iteration_venue_expansion_gap_worklist_parquet_path)
            if write_report
            else None
        ),
        "iteration_venue_expansion_gap_worklist_parquet_row_count": len(
            iteration_venue_expansion_gap_worklist_parquet_rows
        ),
        "iteration_venue_expansion_gap_worklist_source_artifact_count": (
            iteration_venue_expansion_gap_worklist_summary["source_artifact_count"]
        ),
        "iteration_venue_expansion_gap_worklist_source_iteration_count": (
            iteration_venue_expansion_gap_worklist_summary["source_iteration_count"]
        ),
        "iteration_venue_expansion_gap_worklist_target_venue_counts": (
            iteration_venue_expansion_gap_worklist_summary["target_venue_counts"]
        ),
        "iteration_venue_expansion_gap_worklist_target_action_counts": (
            iteration_venue_expansion_gap_worklist_summary["target_action_counts"]
        ),
        "iteration_venue_expansion_gap_worklist_target_status_counts": (
            iteration_venue_expansion_gap_worklist_summary["target_status_counts"]
        ),
        "iteration_venue_expansion_gap_worklist_source_queue_counts": (
            iteration_venue_expansion_gap_worklist_summary["source_queue_counts"]
        ),
        "iteration_agent_action_plan_bucket_queue_parquet_path": (
            str(iteration_action_plan_bucket_queue_parquet_path) if write_report else None
        ),
        "iteration_agent_action_plan_bucket_queue_parquet_row_count": len(
            iteration_action_plan_bucket_queue
        ),
        "iteration_agent_action_plan_bucket_representatives_parquet_path": (
            str(iteration_action_plan_bucket_representatives_parquet_path)
            if write_report
            else None
        ),
        "iteration_agent_action_plan_bucket_representative_parquet_row_count": len(
            iteration_action_plan_bucket_representative_parquet_rows
        ),
        "replay_batch_plan_bucket_queue_parquet_path": (
            str(bucket_queue_parquet_path) if write_report else None
        ),
        "replay_batch_plan_bucket_representatives_parquet_path": (
            str(bucket_representatives_parquet_path) if write_report else None
        ),
        "replay_batch_plan_bucket_queue_parquet_row_count": len(bucket_queue_parquet_rows),
        "replay_batch_plan_bucket_representative_parquet_row_count": len(
            bucket_representative_parquet_rows
        ),
        "artifacts": rows,
    }
    require_sandbox_boundary(payload, payload_name="sandbox_artifact_catalog")
    if write_report:
        destination.mkdir(parents=True, exist_ok=True)
        frame = pd.DataFrame([_row_for_parquet(row) for row in rows])
        if frame.empty:
            frame = pd.DataFrame(columns=["artifact_kind", "artifact_path", *SANDBOX_BOUNDARY_FLAGS])
        frame.to_parquet(parquet_path, index=False)
        analysis_bucket_rollup_frame = pd.DataFrame(
            [_row_for_parquet(row) for row in analysis_bucket_rollup_parquet_rows]
        )
        if analysis_bucket_rollup_frame.empty:
            analysis_bucket_rollup_frame = pd.DataFrame(
                columns=ANALYSIS_BUCKET_ROLLUP_PARQUET_COLUMNS
            )
        analysis_bucket_rollup_frame.to_parquet(
            analysis_bucket_rollups_parquet_path,
            index=False,
        )
        global_top_hypothesis_frame = pd.DataFrame(
            [_row_for_parquet(row) for row in global_top_hypothesis_parquet_rows]
        )
        if global_top_hypothesis_frame.empty:
            global_top_hypothesis_frame = pd.DataFrame(
                columns=GLOBAL_TOP_HYPOTHESIS_PARQUET_COLUMNS
            )
        global_top_hypothesis_frame.to_parquet(
            global_top_hypotheses_parquet_path,
            index=False,
        )
        global_evidence_request_frame = pd.DataFrame(
            [_row_for_parquet(row) for row in global_evidence_request_parquet_rows]
        )
        if global_evidence_request_frame.empty:
            global_evidence_request_frame = pd.DataFrame(
                columns=GLOBAL_EVIDENCE_REQUEST_PARQUET_COLUMNS
            )
        global_evidence_request_frame.to_parquet(
            global_evidence_requests_parquet_path,
            index=False,
        )
        global_evidence_request_source_summary_frame = pd.DataFrame(
            [_row_for_parquet(row) for row in global_evidence_request_source_summary_rows]
        )
        if global_evidence_request_source_summary_frame.empty:
            global_evidence_request_source_summary_frame = pd.DataFrame(
                columns=GLOBAL_EVIDENCE_REQUEST_SOURCE_SUMMARY_PARQUET_COLUMNS
            )
        global_evidence_request_source_summary_frame.to_parquet(
            global_evidence_request_source_summary_parquet_path,
            index=False,
        )
        global_evidence_request_source_priority_queue_frame = pd.DataFrame(
            [
                _row_for_parquet(row)
                for row in global_evidence_request_source_priority_queue
            ]
        )
        if global_evidence_request_source_priority_queue_frame.empty:
            global_evidence_request_source_priority_queue_frame = pd.DataFrame(
                columns=GLOBAL_EVIDENCE_REQUEST_SOURCE_PRIORITY_QUEUE_PARQUET_COLUMNS
            )
        global_evidence_request_source_priority_queue_frame.to_parquet(
            global_evidence_request_source_priority_queue_parquet_path,
            index=False,
        )
        global_evidence_request_priority_queue_frame = pd.DataFrame(
            [_row_for_parquet(row) for row in global_evidence_request_priority_queue]
        )
        if global_evidence_request_priority_queue_frame.empty:
            global_evidence_request_priority_queue_frame = pd.DataFrame(
                columns=GLOBAL_EVIDENCE_REQUEST_PRIORITY_QUEUE_PARQUET_COLUMNS
            )
        global_evidence_request_priority_queue_frame.to_parquet(
            global_evidence_request_priority_queue_parquet_path,
            index=False,
        )
        global_evidence_request_bucket_queue_frame = pd.DataFrame(
            [_row_for_parquet(row) for row in global_evidence_request_bucket_queue]
        )
        if global_evidence_request_bucket_queue_frame.empty:
            global_evidence_request_bucket_queue_frame = pd.DataFrame(
                columns=GLOBAL_EVIDENCE_REQUEST_BUCKET_QUEUE_PARQUET_COLUMNS
            )
        global_evidence_request_bucket_queue_frame.to_parquet(
            global_evidence_request_bucket_queue_parquet_path,
            index=False,
        )
        global_evidence_request_bucket_representatives_frame = pd.DataFrame(
            [
                _row_for_parquet(row)
                for row in global_evidence_request_bucket_representative_parquet_rows
            ]
        )
        if global_evidence_request_bucket_representatives_frame.empty:
            global_evidence_request_bucket_representatives_frame = pd.DataFrame(
                columns=GLOBAL_EVIDENCE_REQUEST_BUCKET_REPRESENTATIVE_PARQUET_COLUMNS
            )
        global_evidence_request_bucket_representatives_frame.to_parquet(
            global_evidence_request_bucket_representatives_parquet_path,
            index=False,
        )
        global_bucket_top_bucket_frame = pd.DataFrame(
            [_row_for_parquet(row) for row in global_bucket_top_bucket_parquet_rows]
        )
        if global_bucket_top_bucket_frame.empty:
            global_bucket_top_bucket_frame = pd.DataFrame(
                columns=GLOBAL_BUCKET_TOP_BUCKET_PARQUET_COLUMNS
            )
        global_bucket_top_bucket_frame.to_parquet(
            global_bucket_top_buckets_parquet_path,
            index=False,
        )
        iteration_action_plan_frame = pd.DataFrame(
            [_row_for_parquet(row) for row in iteration_action_plan_parquet_rows]
        )
        if iteration_action_plan_frame.empty:
            iteration_action_plan_frame = pd.DataFrame(
                columns=ITERATION_ACTION_PLAN_PARQUET_COLUMNS
            )
        iteration_action_plan_frame.to_parquet(
            iteration_action_plan_parquet_path,
            index=False,
        )
        iteration_venue_expansion_gap_worklist_frame = pd.DataFrame(
            [
                _row_for_parquet(row)
                for row in iteration_venue_expansion_gap_worklist_parquet_rows
            ]
        )
        if iteration_venue_expansion_gap_worklist_frame.empty:
            iteration_venue_expansion_gap_worklist_frame = pd.DataFrame(
                columns=ITERATION_VENUE_EXPANSION_GAP_WORKLIST_PARQUET_COLUMNS
            )
        iteration_venue_expansion_gap_worklist_frame.to_parquet(
            iteration_venue_expansion_gap_worklist_parquet_path,
            index=False,
        )
        iteration_action_plan_bucket_queue_frame = pd.DataFrame(
            [_row_for_parquet(row) for row in iteration_action_plan_bucket_queue]
        )
        if iteration_action_plan_bucket_queue_frame.empty:
            iteration_action_plan_bucket_queue_frame = pd.DataFrame(
                columns=ITERATION_ACTION_PLAN_BUCKET_QUEUE_PARQUET_COLUMNS
            )
        iteration_action_plan_bucket_queue_frame.to_parquet(
            iteration_action_plan_bucket_queue_parquet_path,
            index=False,
        )
        iteration_action_plan_bucket_representatives_frame = pd.DataFrame(
            [
                _row_for_parquet(row)
                for row in iteration_action_plan_bucket_representative_parquet_rows
            ]
        )
        if iteration_action_plan_bucket_representatives_frame.empty:
            iteration_action_plan_bucket_representatives_frame = pd.DataFrame(
                columns=ITERATION_ACTION_PLAN_BUCKET_REPRESENTATIVE_PARQUET_COLUMNS
            )
        iteration_action_plan_bucket_representatives_frame.to_parquet(
            iteration_action_plan_bucket_representatives_parquet_path,
            index=False,
        )
        bucket_queue_frame = pd.DataFrame(
            [_row_for_parquet(row) for row in bucket_queue_parquet_rows]
        )
        if bucket_queue_frame.empty:
            bucket_queue_frame = pd.DataFrame(columns=REPLAY_BUCKET_QUEUE_PARQUET_COLUMNS)
        bucket_queue_frame.to_parquet(bucket_queue_parquet_path, index=False)
        bucket_representatives_frame = pd.DataFrame(
            [_row_for_parquet(row) for row in bucket_representative_parquet_rows]
        )
        if bucket_representatives_frame.empty:
            bucket_representatives_frame = pd.DataFrame(
                columns=REPLAY_BUCKET_REPRESENTATIVE_PARQUET_COLUMNS
            )
        bucket_representatives_frame.to_parquet(
            bucket_representatives_parquet_path,
            index=False,
        )
        strict_validation_bundle_queue_frame = pd.DataFrame(
            [_row_for_parquet(row) for row in strict_validation_bundle_queue_parquet_rows]
        )
        if strict_validation_bundle_queue_frame.empty:
            strict_validation_bundle_queue_frame = pd.DataFrame(
                columns=STRICT_VALIDATION_BUNDLE_QUEUE_PARQUET_COLUMNS
            )
        strict_validation_bundle_queue_frame.to_parquet(
            strict_validation_bundle_queue_parquet_path,
            index=False,
        )
        strict_validation_descriptor_frame = pd.DataFrame(
            [_row_for_parquet(row) for row in strict_validation_descriptor_parquet_rows]
        )
        if strict_validation_descriptor_frame.empty:
            strict_validation_descriptor_frame = pd.DataFrame(
                columns=STRICT_VALIDATION_DESCRIPTOR_PARQUET_COLUMNS
            )
        strict_validation_descriptor_frame.to_parquet(
            strict_validation_descriptor_parquet_path,
            index=False,
        )
        strict_validation_descriptor_queue_frame = pd.DataFrame(
            [_row_for_parquet(row) for row in strict_validation_descriptor_queue_parquet_rows]
        )
        if strict_validation_descriptor_queue_frame.empty:
            strict_validation_descriptor_queue_frame = pd.DataFrame(
                columns=STRICT_VALIDATION_DESCRIPTOR_QUEUE_PARQUET_COLUMNS
            )
        strict_validation_descriptor_queue_frame.to_parquet(
            strict_validation_descriptor_queue_parquet_path,
            index=False,
        )
        strict_validation_descriptor_bucket_queue_frame = pd.DataFrame(
            [
                _row_for_parquet(row)
                for row in strict_validation_descriptor_bucket_queue_parquet_rows
            ]
        )
        if strict_validation_descriptor_bucket_queue_frame.empty:
            strict_validation_descriptor_bucket_queue_frame = pd.DataFrame(
                columns=STRICT_VALIDATION_DESCRIPTOR_BUCKET_QUEUE_PARQUET_COLUMNS
            )
        strict_validation_descriptor_bucket_queue_frame.to_parquet(
            strict_validation_descriptor_bucket_queue_parquet_path,
            index=False,
        )
        strict_validation_descriptor_bucket_representatives_frame = pd.DataFrame(
            [
                _row_for_parquet(row)
                for row in strict_validation_descriptor_bucket_representative_parquet_rows
            ]
        )
        if strict_validation_descriptor_bucket_representatives_frame.empty:
            strict_validation_descriptor_bucket_representatives_frame = pd.DataFrame(
                columns=STRICT_VALIDATION_DESCRIPTOR_BUCKET_REPRESENTATIVE_PARQUET_COLUMNS
            )
        strict_validation_descriptor_bucket_representatives_frame.to_parquet(
            strict_validation_descriptor_bucket_representatives_parquet_path,
            index=False,
        )
        sidecar_index_rows = _catalog_sidecar_index_rows(
            sidecar_index_specs,
            write_report=True,
        )
        payload["catalog_sidecar_index_row_count"] = len(sidecar_index_rows)
        payload["catalog_sidecar_index"] = sidecar_index_rows
        require_sandbox_boundary(payload, payload_name="sandbox_artifact_catalog")
        sidecar_index_frame = pd.DataFrame(
            [_row_for_parquet(row) for row in sidecar_index_rows]
        )
        if sidecar_index_frame.empty:
            sidecar_index_frame = pd.DataFrame(
                columns=CATALOG_SIDECAR_INDEX_PARQUET_COLUMNS
            )
        sidecar_index_frame.to_parquet(
            sidecar_index_parquet_path,
            index=False,
        )
        json_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=_json_default),
            encoding="utf-8",
        )
    return payload
