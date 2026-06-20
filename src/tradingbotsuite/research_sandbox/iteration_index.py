from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path
from typing import Any

import pandas as pd

from tradingbotsuite.research_sandbox.boundary import (
    SANDBOX_BOUNDARY_FLAGS,
    require_sandbox_boundary,
    sandbox_boundary_metadata,
)
from tradingbotsuite.research_sandbox.identity import digest_payload
from tradingbotsuite.research_sandbox.iteration import SANDBOX_ITERATION_MANIFEST_JSON_NAME


SANDBOX_ITERATION_INDEX_JSON_NAME = "sandbox_iteration_index.json"
SANDBOX_ITERATION_INDEX_PARQUET_NAME = "sandbox_iteration_index.parquet"
SANDBOX_ITERATION_AGENT_ACTION_PLAN_PARQUET_NAME = "sandbox_iteration_agent_action_plan.parquet"
SANDBOX_ITERATION_INPUT_REPLAY_WORKLIST_JSON_NAME = "sandbox_iteration_input_replay_worklist.json"
SANDBOX_ITERATION_INPUT_REPLAY_WORKLIST_PARQUET_NAME = "sandbox_iteration_input_replay_worklist.parquet"
SANDBOX_ITERATION_INPUT_REPLAY_BATCH_PLAN_JSON_NAME = "sandbox_iteration_input_replay_batch_plan.json"
SANDBOX_ITERATION_INPUT_REPLAY_BATCH_PLAN_PARQUET_NAME = "sandbox_iteration_input_replay_batch_plan.parquet"
SANDBOX_ITERATION_ACTION_QUEUE_VERSION = 14
SANDBOX_ITERATION_ACTION_QUEUE_LIMIT = 25
SANDBOX_ITERATION_AGENT_ACTION_PLAN_VERSION = 1
SANDBOX_ITERATION_AGENT_ACTION_PLAN_LIMIT = 50
SANDBOX_ITERATION_INPUT_REPLAY_WORKLIST_VERSION = 1
SANDBOX_ITERATION_INPUT_REPLAY_BATCH_PLAN_VERSION = 1
_AGENT_ACTION_PRIORITIES = {
    "restore_or_regenerate_iteration_agent_brief": 10,
    "restore_or_rerun_missing_iteration_artifacts": 20,
    "adjust_iteration_window_or_refresh_archive_manifest": 30,
    "repair_archive_manifest_or_requested_window": 35,
    "refresh_archive_source_integrity_metadata_or_restore_source_file": 40,
    "repair_strategy_catalog_sources": 45,
    "repair_strategy_catalog_signal_columns_or_materialize_blueprints": 50,
    "add_required_ohlc_columns_or_use_fixed_hold_exit": 55,
    "repair_preflight_blockers": 60,
    "review_descriptor_only_strict_validation_requests": 70,
    "repair_or_add_venue_expansion_archives": 75,
    "review_rejections_and_falsified_hypotheses": 80,
    "inspect_blocked_or_empty_sandbox_iteration": 90,
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


def _load_json_object(path: Path, *, payload_name: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{payload_name} must be a JSON object: {path}")
    require_sandbox_boundary(payload, payload_name=payload_name)
    return payload


def _resolve_artifact_path(raw_path: Any, *, manifest_path: Path) -> Path | None:
    if raw_path is None or raw_path == "":
        return None
    path = Path(str(raw_path)).expanduser()
    if not path.is_absolute():
        path = manifest_path.parent / path
    return path.resolve()


def _load_brief(manifest: dict[str, Any], *, manifest_path: Path) -> tuple[dict[str, Any] | None, str, Path | None]:
    brief_path = _resolve_artifact_path(manifest.get("agent_brief_json_path"), manifest_path=manifest_path)
    if brief_path is None:
        return None, "missing_reference", None
    if not brief_path.exists() or not brief_path.is_file():
        return None, "missing_file", brief_path
    brief = _load_json_object(brief_path, payload_name="sandbox_iteration_index_agent_brief")
    return brief, "present", brief_path


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _count_value(source: dict[str, Any], key: str) -> int:
    value = source.get(key)
    return int(value or 0)


def _brief_counts(brief: dict[str, Any] | None) -> dict[str, Any]:
    return _as_dict((brief or {}).get("counts"))


def _strategy_source_summary(manifest: dict[str, Any], brief: dict[str, Any] | None) -> dict[str, Any]:
    brief_summary = _as_dict((brief or {}).get("strategy_source_summary"))
    if brief_summary:
        return brief_summary
    strategy_source = _as_dict(manifest.get("strategy_source"))
    return _as_dict(strategy_source.get("strategy_source_summary"))


def _archive_source_summary(manifest: dict[str, Any], brief: dict[str, Any] | None) -> dict[str, Any]:
    brief_summary = _as_dict((brief or {}).get("archive_source_summary"))
    if brief_summary:
        return brief_summary
    archive_source = _as_dict(manifest.get("archive_source"))
    return _as_dict(archive_source.get("archive_source_summary"))


def _archive_blocker_samples(manifest: dict[str, Any], brief: dict[str, Any] | None) -> list[Any]:
    brief_samples = _as_list((brief or {}).get("archive_blocker_samples"))
    if brief_samples:
        return brief_samples
    return _as_list(manifest.get("archive_coverage_blocker_samples"))


def _archive_blocker_samples_truncated(manifest: dict[str, Any], brief: dict[str, Any] | None) -> bool:
    if isinstance(brief, dict) and "archive_blocker_samples_truncated" in brief:
        return bool(brief.get("archive_blocker_samples_truncated", False))
    return bool(manifest.get("archive_coverage_blocker_samples_truncated", False))


def _venue_expansion_target_venues(manifest: dict[str, Any], brief: dict[str, Any] | None) -> list[Any]:
    brief_targets = _as_list((brief or {}).get("venue_expansion_target_venues"))
    if brief_targets:
        return brief_targets
    return _as_list(manifest.get("archive_coverage_venue_expansion_target_venues"))


def _venue_expansion_status_counts(manifest: dict[str, Any], brief: dict[str, Any] | None) -> dict[str, Any]:
    brief_counts = _as_dict((brief or {}).get("venue_expansion_status_counts"))
    if brief_counts:
        return brief_counts
    return _as_dict(manifest.get("archive_coverage_venue_expansion_status_counts"))


def _venue_expansion_action_counts(manifest: dict[str, Any], brief: dict[str, Any] | None) -> dict[str, Any]:
    brief_counts = _as_dict((brief or {}).get("venue_expansion_action_counts"))
    if brief_counts:
        return brief_counts
    return _as_dict(manifest.get("archive_coverage_venue_expansion_action_counts"))


def _venue_expansion_gap_samples(manifest: dict[str, Any], brief: dict[str, Any] | None) -> list[Any]:
    brief_samples = _as_list((brief or {}).get("venue_expansion_gap_samples"))
    if brief_samples:
        return brief_samples
    return _as_list(manifest.get("archive_coverage_venue_expansion_gap_samples"))


def _venue_expansion_gap_samples_truncated(manifest: dict[str, Any], brief: dict[str, Any] | None) -> bool:
    if isinstance(brief, dict) and "venue_expansion_gap_samples_truncated" in brief:
        return bool(brief.get("venue_expansion_gap_samples_truncated", False))
    return bool(manifest.get("archive_coverage_venue_expansion_gap_samples_truncated", False))


def _preflight_blocker_samples(manifest: dict[str, Any], brief: dict[str, Any] | None) -> list[Any]:
    brief_samples = _as_list((brief or {}).get("preflight_blocker_samples"))
    if brief_samples:
        return brief_samples
    return _as_list(manifest.get("preflight_blocker_samples"))


def _preflight_blocker_samples_truncated(manifest: dict[str, Any], brief: dict[str, Any] | None) -> bool:
    if isinstance(brief, dict) and "preflight_blocker_samples_truncated" in brief:
        return bool(brief.get("preflight_blocker_samples_truncated", False))
    return bool(manifest.get("preflight_blocker_samples_truncated", False))


def _rejection_falsification_samples(manifest: dict[str, Any], brief: dict[str, Any] | None) -> list[Any]:
    brief_samples = _as_list((brief or {}).get("rejection_falsification_samples"))
    if brief_samples:
        return brief_samples
    return _as_list(manifest.get("rejection_falsification_samples"))


def _rejection_falsification_samples_truncated(manifest: dict[str, Any], brief: dict[str, Any] | None) -> bool:
    if isinstance(brief, dict) and "rejection_falsification_samples_truncated" in brief:
        return bool(brief.get("rejection_falsification_samples_truncated", False))
    return bool(manifest.get("rejection_falsification_samples_truncated", False))


def _input_replay_context(manifest: dict[str, Any], brief: dict[str, Any] | None) -> dict[str, Any]:
    brief_context = _as_dict((brief or {}).get("input_replay_context"))
    if brief_context:
        return brief_context
    return _as_dict(manifest.get("input_replay_context"))


def _blocker_counts_from_top(top_blockers: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for blocker in top_blockers:
        if not isinstance(blocker, dict):
            continue
        reason = blocker.get("reason")
        if reason is None:
            continue
        counts[str(reason)] = counts.get(str(reason), 0) + int(blocker.get("count", 0) or 0)
    return counts


def _artifact_paths(manifest: dict[str, Any], brief: dict[str, Any] | None) -> dict[str, Any]:
    paths = _as_dict((brief or {}).get("artifact_paths"))
    for key in (
        "iteration_manifest_path",
        "iteration_steps_parquet_path",
        "agent_brief_json_path",
        "agent_brief_parquet_path",
        "archive_coverage_json_path",
        "archive_coverage_parquet_path",
        "archive_coverage_venue_expansion_gaps_parquet_path",
        "preflight_json_path",
        "preflight_parquet_path",
        "run_manifest_path",
        "strict_validation_request_bundle_json_path",
        "strict_validation_request_bundle_parquet_path",
        "global_leaderboard_json_path",
        "global_leaderboard_parquet_path",
    ):
        value = manifest.get(key)
        if value and key not in paths:
            paths[key] = value
    strategy_source = _as_dict(manifest.get("strategy_source"))
    archive_source = _as_dict(manifest.get("archive_source"))
    source_paths = {
        "strategy_catalog_json_path": strategy_source.get("strategy_catalog_json_path"),
        "strategy_catalog_parquet_path": strategy_source.get("strategy_catalog_parquet_path"),
        "strategy_build_report_json_path": strategy_source.get("build_report_json_path"),
        "strategy_build_report_parquet_path": strategy_source.get("build_report_parquet_path"),
        "venue_archive_manifest_path": archive_source.get("venue_archive_manifest_path"),
        "archive_build_report_json_path": archive_source.get("build_report_json_path"),
        "archive_build_report_parquet_path": archive_source.get("build_report_parquet_path"),
    }
    for key, value in source_paths.items():
        if value and key not in paths:
            paths[key] = value
    return paths


def _artifact_availability(paths: dict[str, Any], *, manifest_path: Path) -> dict[str, Any]:
    references: dict[str, Path] = {}
    for key, value in paths.items():
        if value is None or value == "":
            continue
        resolved = _resolve_artifact_path(value, manifest_path=manifest_path)
        if resolved is not None:
            references[str(key)] = resolved
    missing_keys = sorted(
        key for key, path in references.items() if not path.exists() or not path.is_file()
    )
    present_count = len(references) - len(missing_keys)
    if not references:
        status = "no_artifact_references"
    elif missing_keys:
        status = "missing_artifacts"
    else:
        status = "all_present"
    return {
        "artifact_availability_status": status,
        "artifact_reference_count": len(references),
        "artifact_present_count": present_count,
        "artifact_missing_count": len(missing_keys),
        "artifact_missing_keys": missing_keys,
    }


def _iteration_row(
    *,
    index_id: str,
    root_dir: Path,
    manifest_path: Path,
    manifest: dict[str, Any],
    brief: dict[str, Any] | None,
    brief_status: str,
    brief_path: Path | None,
) -> dict[str, Any]:
    spec = _as_dict(manifest.get("spec"))
    strategy_source = _as_dict(manifest.get("strategy_source"))
    archive_source = _as_dict(manifest.get("archive_source"))
    counts = _brief_counts(brief)
    strategy_source_summary = _strategy_source_summary(manifest, brief)
    archive_source_summary = _archive_source_summary(manifest, brief)
    archive_coverage_blocker_samples = _archive_blocker_samples(manifest, brief)
    archive_coverage_blocker_samples_truncated = _archive_blocker_samples_truncated(manifest, brief)
    venue_expansion_target_venues = _venue_expansion_target_venues(manifest, brief)
    venue_expansion_status_counts = _venue_expansion_status_counts(manifest, brief)
    venue_expansion_action_counts = _venue_expansion_action_counts(manifest, brief)
    venue_expansion_gap_samples = _venue_expansion_gap_samples(manifest, brief)
    venue_expansion_gap_samples_truncated = _venue_expansion_gap_samples_truncated(manifest, brief)
    preflight_blocker_samples = _preflight_blocker_samples(manifest, brief)
    preflight_blocker_samples_truncated = _preflight_blocker_samples_truncated(manifest, brief)
    rejection_falsification_samples = _rejection_falsification_samples(manifest, brief)
    rejection_falsification_samples_truncated = _rejection_falsification_samples_truncated(manifest, brief)
    input_replay_context = _input_replay_context(manifest, brief)
    reason_codes = _as_list((brief or {}).get("reason_codes") or manifest.get("agent_brief_reason_codes"))
    next_action = (brief or {}).get("next_action") or manifest.get("agent_brief_next_action") or "unknown"
    top_archive_blockers = _as_list((brief or {}).get("top_archive_blockers"))
    top_preflight_blockers = _as_list((brief or {}).get("top_preflight_blockers"))
    archive_blocker_counts = (
        _as_dict((brief or {}).get("archive_blocker_reason_counts"))
        or _as_dict(manifest.get("archive_coverage_blocker_reason_counts"))
        or _blocker_counts_from_top(top_archive_blockers)
    )
    preflight_blocker_counts = (
        _as_dict((brief or {}).get("preflight_blocker_reason_counts"))
        or _as_dict(manifest.get("preflight_blocker_reason_counts"))
        or _blocker_counts_from_top(top_preflight_blockers)
    )
    artifact_paths = _artifact_paths(manifest, brief)
    artifact_availability = _artifact_availability(artifact_paths, manifest_path=manifest_path)
    row = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_iteration_index_row",
        "index_id": index_id,
        "iteration_id": manifest.get("iteration_id"),
        "run_id": spec.get("run_id"),
        "iteration_status": manifest.get("iteration_status"),
        "next_action": next_action,
        "reason_codes": [str(reason) for reason in reason_codes],
        "input_replay_context": input_replay_context,
        "input_replay_context_id": input_replay_context.get("replay_context_id"),
        "input_replay_command": input_replay_context.get("command"),
        "input_replay_command_argv": _as_list(input_replay_context.get("command_argv")),
        "input_replay_strategy_input_mode": input_replay_context.get("strategy_input_mode"),
        "input_replay_venue_input_mode": input_replay_context.get("venue_input_mode"),
        "brief_status": brief_status,
        "iteration_manifest_path": str(manifest_path),
        "iteration_manifest_path_relative": str(manifest_path.relative_to(root_dir)),
        "iteration_dir": manifest.get("iteration_dir") or str(manifest_path.parent),
        "agent_brief_json_path": str(brief_path) if brief_path is not None else manifest.get("agent_brief_json_path"),
        "agent_brief_parquet_path": manifest.get("agent_brief_parquet_path"),
        "strategy_source_mode": strategy_source.get("mode"),
        "strategy_catalog_id": strategy_source.get("catalog_id"),
        "strategy_catalog_json_path": strategy_source.get("strategy_catalog_json_path"),
        "strategy_catalog_parquet_path": strategy_source.get("strategy_catalog_parquet_path"),
        "strategy_build_report_json_path": strategy_source.get("build_report_json_path"),
        "strategy_build_report_parquet_path": strategy_source.get("build_report_parquet_path"),
        "archive_source_mode": archive_source.get("mode"),
        "archive_manifest_id": archive_source.get("manifest_id"),
        "venue_archive_manifest_path": archive_source.get("venue_archive_manifest_path"),
        "archive_build_report_json_path": archive_source.get("build_report_json_path"),
        "archive_build_report_parquet_path": archive_source.get("build_report_parquet_path"),
        "archive_coverage_venue_expansion_gaps_parquet_path": manifest.get(
            "archive_coverage_venue_expansion_gaps_parquet_path"
        ),
        "strategy_count": _count_value(strategy_source, "strategy_count"),
        "strategy_included_source_count": _count_value(strategy_source, "included_source_count"),
        "strategy_skipped_source_count": _count_value(strategy_source, "skipped_source_count"),
        "strategy_source_summary": strategy_source_summary,
        "strategy_source_status_counts": _as_dict(strategy_source_summary.get("source_status_counts")),
        "strategy_source_suffix_counts": _as_dict(strategy_source_summary.get("source_suffix_counts")),
        "strategy_source_skip_reason_counts": _as_dict(strategy_source_summary.get("source_skip_reason_counts")),
        "strategy_skipped_source_samples": _as_list(strategy_source_summary.get("skipped_source_samples")),
        "strategy_skipped_source_samples_truncated": bool(
            strategy_source_summary.get("skipped_source_samples_truncated", False)
        ),
        "strategy_workbook_source_count": _count_value(strategy_source_summary, "workbook_source_count"),
        "strategy_workbook_sheet_count": _count_value(strategy_source_summary, "workbook_sheet_count"),
        "strategy_workbook_included_sheet_count": _count_value(strategy_source_summary, "workbook_included_sheet_count"),
        "strategy_workbook_skipped_sheet_count": _count_value(strategy_source_summary, "workbook_skipped_sheet_count"),
        "strategy_workbook_strategy_count": _count_value(strategy_source_summary, "workbook_strategy_count"),
        "strategy_workbook_sheet_status_counts": _as_dict(strategy_source_summary.get("workbook_sheet_status_counts")),
        "strategy_workbook_sheet_kind_counts": _as_dict(strategy_source_summary.get("workbook_sheet_kind_counts")),
        "strategy_workbook_sheet_name_sample": _as_list(strategy_source_summary.get("workbook_sheet_name_sample")),
        "strategy_workbook_included_sheet_name_sample": _as_list(
            strategy_source_summary.get("workbook_included_sheet_name_sample")
        ),
        "strategy_workbook_skipped_sheet_name_sample": _as_list(
            strategy_source_summary.get("workbook_skipped_sheet_name_sample")
        ),
        "strategy_workbook_source_summaries": _as_list(strategy_source_summary.get("workbook_source_summaries")),
        "descriptor_count": _count_value(archive_source, "descriptor_count"),
        "archive_file_count": _count_value(archive_source, "file_count"),
        "archive_skipped_count": _count_value(archive_source, "skipped_count"),
        "archive_source_summary": archive_source_summary,
        "archive_file_status_counts": _as_dict(archive_source_summary.get("file_status_counts")),
        "archive_file_suffix_counts": _as_dict(archive_source_summary.get("file_suffix_counts")),
        "archive_file_skip_reason_counts": _as_dict(archive_source_summary.get("file_skip_reason_counts")),
        "archive_skipped_file_samples": _as_list(archive_source_summary.get("skipped_file_samples")),
        "archive_skipped_file_samples_truncated": bool(
            archive_source_summary.get("skipped_file_samples_truncated", False)
        ),
        "archive_coverage_ready_descriptor_count": _count_value(manifest, "archive_coverage_ready_descriptor_count"),
        "archive_coverage_blocked_descriptor_count": _count_value(manifest, "archive_coverage_blocked_descriptor_count"),
        "archive_coverage_requested_window_row_count": _count_value(
            manifest,
            "archive_coverage_requested_window_row_count",
        ),
        "venue_expansion_target_venues": [str(venue) for venue in venue_expansion_target_venues],
        "venue_expansion_gap_row_count": _count_value(
            manifest,
            "archive_coverage_venue_expansion_gap_row_count",
        ),
        "venue_expansion_actionable_gap_count": _count_value(
            manifest,
            "archive_coverage_venue_expansion_actionable_gap_count",
        ),
        "venue_expansion_missing_target_count": _count_value(
            manifest,
            "archive_coverage_venue_expansion_missing_target_count",
        ),
        "venue_expansion_ready_target_count": _count_value(
            manifest,
            "archive_coverage_venue_expansion_ready_target_count",
        ),
        "venue_expansion_blocked_target_count": _count_value(
            manifest,
            "archive_coverage_venue_expansion_blocked_target_count",
        ),
        "venue_expansion_mixed_target_count": _count_value(
            manifest,
            "archive_coverage_venue_expansion_mixed_target_count",
        ),
        "venue_expansion_status_counts": venue_expansion_status_counts,
        "venue_expansion_action_counts": venue_expansion_action_counts,
        "venue_expansion_gap_samples": venue_expansion_gap_samples,
        "venue_expansion_gap_samples_truncated": venue_expansion_gap_samples_truncated,
        "preflight_trial_estimate": _count_value(manifest, "preflight_trial_estimate"),
        "preflight_runnable_trial_estimate": _count_value(manifest, "preflight_runnable_trial_estimate"),
        "preflight_blocked_trial_estimate": _count_value(manifest, "preflight_blocked_trial_estimate"),
        "result_count": _count_value(manifest, "result_count"),
        "screened_count": _count_value(manifest, "screened_count"),
        "rejected_count": _count_value(manifest, "rejected_count"),
        "blocked_count": _count_value(manifest, "blocked_count"),
        "evidence_request_count": _count_value(manifest, "evidence_request_count"),
        "deduped_validation_request_count": _count_value(manifest, "deduped_validation_request_count"),
        "leaderboard_hypothesis_count": _count_value(manifest, "leaderboard_hypothesis_count"),
        "brief_result_count": _count_value(counts, "result_count"),
        "brief_deduped_validation_request_count": _count_value(counts, "deduped_validation_request_count"),
        "coverage_status_counts": _as_dict((brief or {}).get("coverage_status_counts") or manifest.get("archive_coverage_status_counts")),
        "archive_coverage_blocker_reason_counts": archive_blocker_counts,
        "archive_coverage_blocker_samples": archive_coverage_blocker_samples,
        "archive_coverage_blocker_samples_truncated": archive_coverage_blocker_samples_truncated,
        "preflight_status_counts": _as_dict((brief or {}).get("preflight_status_counts") or manifest.get("preflight_status_counts")),
        "preflight_blocker_reason_counts": preflight_blocker_counts,
        "preflight_blocker_samples": preflight_blocker_samples,
        "preflight_blocker_samples_truncated": preflight_blocker_samples_truncated,
        "falsification_decision_counts": _as_dict(
            (brief or {}).get("falsification_decision_counts") or manifest.get("falsification_decision_counts")
        ),
        "rejection_falsification_samples": rejection_falsification_samples,
        "rejection_falsification_samples_truncated": rejection_falsification_samples_truncated,
        "top_archive_blockers": top_archive_blockers,
        "top_preflight_blockers": top_preflight_blockers,
        "top_validation_requests": _as_list((brief or {}).get("top_validation_requests")),
        "artifact_paths": artifact_paths,
        **artifact_availability,
        "strict_validation_executed": bool(manifest.get("strict_validation_executed", False)),
        "candidate_pack_written": bool(manifest.get("candidate_pack_written", False)),
        "candidate_pack_paths": _as_list(manifest.get("candidate_pack_paths")),
    }
    recommended_actions = _recommended_actions(row)
    row["recommended_actions"] = recommended_actions
    row["recommended_action"] = recommended_actions[0]["action"] if recommended_actions else "none"
    require_sandbox_boundary(row, payload_name="sandbox_iteration_index_row")
    return row


def _discover_iteration_manifests(root_dir: Path, *, max_files: int) -> list[Path]:
    if max_files <= 0:
        raise ValueError("max_files must be positive")
    paths: list[Path] = []
    for path in root_dir.rglob(SANDBOX_ITERATION_MANIFEST_JSON_NAME):
        paths.append(path.resolve())
        if len(paths) >= max_files:
            break
    return sorted(paths)


def _row_int(row: dict[str, Any], key: str) -> int:
    return int(row.get(key, 0) or 0)


def _validation_request_count(row: dict[str, Any]) -> int:
    return max(
        _row_int(row, "deduped_validation_request_count"),
        _row_int(row, "brief_deduped_validation_request_count"),
    )


def _append_recommended_action(
    actions: list[dict[str, Any]],
    *,
    action: str,
    reason_code: str | None = None,
    reason_codes: list[str] | None = None,
    count: int = 0,
    details: dict[str, Any] | None = None,
) -> None:
    codes = [
        str(code)
        for code in (reason_codes if reason_codes is not None else [reason_code])
        if code not in (None, "")
    ]
    if not codes:
        codes = ["unspecified"]
    for entry in actions:
        if entry.get("action") != action:
            continue
        entry["count"] = int(entry.get("count", 0) or 0) + int(count or 0)
        existing_reason_codes = _as_list(entry.get("reason_codes"))
        for code in codes:
            if code not in existing_reason_codes:
                existing_reason_codes.append(code)
        entry["reason_codes"] = existing_reason_codes
        for key, value in (details or {}).items():
            if value not in (None, "", [], {}) and key not in entry:
                entry[key] = value
        return
    entry = {
        "action": action,
        "reason_codes": codes,
        "count": int(count or 0),
    }
    for key, value in (details or {}).items():
        if value not in (None, "", [], {}):
            entry[key] = value
    actions.append(entry)


def _preflight_repair_action(reason: str) -> str:
    if reason.startswith("missing_signal_column:"):
        return "repair_strategy_catalog_signal_columns_or_materialize_blueprints"
    if reason.startswith("missing_ohlc_column:"):
        return "add_required_ohlc_columns_or_use_fixed_hold_exit"
    if (
        reason.startswith("source_integrity_")
        or "sha256_mismatch" in reason
        or "byte_size_mismatch" in reason
    ):
        return "refresh_archive_source_integrity_metadata_or_restore_source_file"
    if reason in {"no_ready_archive_descriptors", "archive_coverage_not_ready"}:
        return "repair_archive_manifest_or_requested_window"
    return "repair_preflight_blockers"


def _preflight_blocker_samples_for_reason(row: dict[str, Any], reason: str, *, limit: int = 5) -> list[Any]:
    samples: list[Any] = []
    for sample in _as_list(row.get("preflight_blocker_samples")):
        if not isinstance(sample, dict):
            continue
        reason_counts = _as_dict(sample.get("blocker_reason_counts"))
        reasons = [str(item) for item in _as_list(sample.get("blocker_reasons"))]
        if reason not in reason_counts and reason not in reasons:
            continue
        samples.append(sample)
        if len(samples) >= limit:
            break
    return samples


def _strategy_source_repair_count(row: dict[str, Any]) -> int:
    skip_reason_counts = _count_map(row.get("strategy_source_skip_reason_counts"))
    return max(
        _row_int(row, "strategy_skipped_source_count"),
        sum(int(count or 0) for count in skip_reason_counts.values()),
    )


def _strategy_source_repair_reason_codes(row: dict[str, Any]) -> list[str]:
    skip_reason_counts = _count_map(row.get("strategy_source_skip_reason_counts"))
    reason_codes = [
        reason
        for reason, count in sorted(skip_reason_counts.items())
        if int(count or 0) > 0
    ]
    if reason_codes:
        return reason_codes
    return ["strategy_source_skipped"]


def _recommended_actions(row: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    brief_status = str(row.get("brief_status") or "missing")
    if brief_status != "present":
        _append_recommended_action(
            actions,
            action="restore_or_regenerate_iteration_agent_brief",
            reason_code=f"brief_status:{brief_status}",
            count=1,
            details={"brief_status": brief_status},
        )
    artifact_missing_count = _row_int(row, "artifact_missing_count")
    artifact_missing_keys = _as_list(row.get("artifact_missing_keys"))
    if artifact_missing_count > 0:
        _append_recommended_action(
            actions,
            action="restore_or_rerun_missing_iteration_artifacts",
            reason_code="missing_referenced_artifacts",
            count=artifact_missing_count,
            details={"artifact_missing_keys": artifact_missing_keys},
        )
    archive_window_blocker_count = _archive_blocker_count(row, "no_rows_in_requested_window")
    if archive_window_blocker_count > 0:
        _append_recommended_action(
            actions,
            action="adjust_iteration_window_or_refresh_archive_manifest",
            reason_code="no_rows_in_requested_window",
            count=archive_window_blocker_count,
            details={
                "archive_file_skip_reason_counts": _as_dict(row.get("archive_file_skip_reason_counts")),
                "archive_skipped_file_samples": _as_list(row.get("archive_skipped_file_samples"))[:5],
                "archive_skipped_file_samples_truncated": bool(
                    row.get("archive_skipped_file_samples_truncated", False)
                ),
                "archive_coverage_blocker_samples": _as_list(row.get("archive_coverage_blocker_samples"))[:5],
                "archive_coverage_blocker_samples_truncated": bool(
                    row.get("archive_coverage_blocker_samples_truncated", False)
                ),
            },
        )
    strategy_source_repair_count = _strategy_source_repair_count(row)
    if strategy_source_repair_count > 0:
        _append_recommended_action(
            actions,
            action="repair_strategy_catalog_sources",
            reason_codes=_strategy_source_repair_reason_codes(row),
            count=strategy_source_repair_count,
            details={
                "strategy_source_skip_reason_counts": _as_dict(
                    row.get("strategy_source_skip_reason_counts")
                ),
                "strategy_skipped_source_samples": _as_list(row.get("strategy_skipped_source_samples"))[:5],
                "strategy_skipped_source_samples_truncated": bool(
                    row.get("strategy_skipped_source_samples_truncated", False)
                ),
            },
        )
    if archive_window_blocker_count <= 0:
        preflight_counts = _count_map(row.get("preflight_blocker_reason_counts"))
        for reason, count in sorted(preflight_counts.items()):
            if int(count or 0) <= 0:
                continue
            _append_recommended_action(
                actions,
                action=_preflight_repair_action(reason),
                reason_code=reason,
                count=int(count),
                details={
                    "preflight_blocker_samples": _preflight_blocker_samples_for_reason(row, reason),
                    "preflight_blocker_samples_truncated": bool(
                        row.get("preflight_blocker_samples_truncated", False)
                    ),
                },
            )
    validation_count = _validation_request_count(row)
    if validation_count > 0:
        _append_recommended_action(
            actions,
            action="review_descriptor_only_strict_validation_requests",
            reason_code="deduped_validation_requests",
            count=validation_count,
        )
    venue_expansion_gap_count = _venue_expansion_actionable_gap_count(row)
    if venue_expansion_gap_count > 0:
        _append_recommended_action(
            actions,
            action="repair_or_add_venue_expansion_archives",
            reason_codes=_venue_expansion_reason_codes(row),
            count=venue_expansion_gap_count,
            details={
                "venue_expansion_target_venues": _as_list(row.get("venue_expansion_target_venues")),
                "venue_expansion_status_counts": _as_dict(row.get("venue_expansion_status_counts")),
                "venue_expansion_action_counts": _as_dict(row.get("venue_expansion_action_counts")),
                "venue_expansion_gap_samples": _as_list(row.get("venue_expansion_gap_samples"))[:5],
                "venue_expansion_gap_samples_truncated": bool(
                    row.get("venue_expansion_gap_samples_truncated", False)
                ),
                "archive_coverage_venue_expansion_gaps_parquet_path": row.get(
                    "archive_coverage_venue_expansion_gaps_parquet_path"
                ),
            },
        )
    rejection_or_block_count = _row_int(row, "rejected_count") + _row_int(row, "blocked_count")
    next_action = str(row.get("next_action") or "")
    if validation_count <= 0 and (
        rejection_or_block_count > 0
        or next_action
        in {
            "review_rejections_and_falsified_hypotheses",
            "review_screened_results_and_request_thresholds",
            "inspect_blocked_or_empty_sandbox_iteration",
        }
    ):
        rejection_action = "review_rejections_and_falsified_hypotheses"
        if next_action == "inspect_blocked_or_empty_sandbox_iteration":
            rejection_action = next_action
        _append_recommended_action(
            actions,
            action=rejection_action,
            reason_code="sandbox_rejections_or_blocks",
            count=max(1, rejection_or_block_count),
            details={
                "falsification_decision_counts": _as_dict(row.get("falsification_decision_counts")),
                "rejection_falsification_samples": _as_list(row.get("rejection_falsification_samples"))[:5],
                "rejection_falsification_samples_truncated": bool(
                    row.get("rejection_falsification_samples_truncated", False)
                ),
            },
        )
    return actions


def _row_recommended_actions(row: dict[str, Any]) -> list[dict[str, Any]]:
    actions = _as_list(row.get("recommended_actions"))
    if actions:
        return actions
    return _recommended_actions(row)


def _queue_item(row: dict[str, Any]) -> dict[str, Any]:
    recommended_actions = _row_recommended_actions(row)
    item = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_action_queue_item",
        "iteration_id": row.get("iteration_id"),
        "run_id": row.get("run_id"),
        "iteration_status": row.get("iteration_status"),
        "next_action": row.get("next_action"),
        "recommended_action": recommended_actions[0]["action"] if recommended_actions else "none",
        "recommended_actions": recommended_actions,
        "reason_codes": _as_list(row.get("reason_codes")),
        "input_replay_context": _as_dict(row.get("input_replay_context")),
        "input_replay_context_id": row.get("input_replay_context_id"),
        "input_replay_command": row.get("input_replay_command"),
        "input_replay_command_argv": _as_list(row.get("input_replay_command_argv")),
        "input_replay_strategy_input_mode": row.get("input_replay_strategy_input_mode"),
        "input_replay_venue_input_mode": row.get("input_replay_venue_input_mode"),
        "brief_status": row.get("brief_status"),
        "iteration_manifest_path": row.get("iteration_manifest_path"),
        "agent_brief_json_path": row.get("agent_brief_json_path"),
        "strategy_source_mode": row.get("strategy_source_mode"),
        "strategy_catalog_id": row.get("strategy_catalog_id"),
        "strategy_catalog_json_path": row.get("strategy_catalog_json_path"),
        "strategy_catalog_parquet_path": row.get("strategy_catalog_parquet_path"),
        "strategy_build_report_json_path": row.get("strategy_build_report_json_path"),
        "strategy_build_report_parquet_path": row.get("strategy_build_report_parquet_path"),
        "strategy_source_status_counts": _as_dict(row.get("strategy_source_status_counts")),
        "strategy_source_suffix_counts": _as_dict(row.get("strategy_source_suffix_counts")),
        "strategy_source_skip_reason_counts": _as_dict(row.get("strategy_source_skip_reason_counts")),
        "strategy_skipped_source_samples": _as_list(row.get("strategy_skipped_source_samples"))[:10],
        "strategy_skipped_source_samples_truncated": bool(row.get("strategy_skipped_source_samples_truncated", False)),
        "strategy_workbook_source_count": _row_int(row, "strategy_workbook_source_count"),
        "strategy_workbook_sheet_count": _row_int(row, "strategy_workbook_sheet_count"),
        "strategy_workbook_included_sheet_count": _row_int(row, "strategy_workbook_included_sheet_count"),
        "strategy_workbook_skipped_sheet_count": _row_int(row, "strategy_workbook_skipped_sheet_count"),
        "strategy_workbook_sheet_status_counts": _as_dict(row.get("strategy_workbook_sheet_status_counts")),
        "strategy_workbook_sheet_kind_counts": _as_dict(row.get("strategy_workbook_sheet_kind_counts")),
        "strategy_workbook_skipped_sheet_name_sample": _as_list(
            row.get("strategy_workbook_skipped_sheet_name_sample")
        )[:10],
        "archive_source_mode": row.get("archive_source_mode"),
        "archive_manifest_id": row.get("archive_manifest_id"),
        "venue_archive_manifest_path": row.get("venue_archive_manifest_path"),
        "archive_build_report_json_path": row.get("archive_build_report_json_path"),
        "archive_build_report_parquet_path": row.get("archive_build_report_parquet_path"),
        "archive_coverage_venue_expansion_gaps_parquet_path": row.get(
            "archive_coverage_venue_expansion_gaps_parquet_path"
        ),
        "archive_file_status_counts": _as_dict(row.get("archive_file_status_counts")),
        "archive_file_suffix_counts": _as_dict(row.get("archive_file_suffix_counts")),
        "archive_file_skip_reason_counts": _as_dict(row.get("archive_file_skip_reason_counts")),
        "archive_skipped_file_samples": _as_list(row.get("archive_skipped_file_samples"))[:10],
        "archive_skipped_file_samples_truncated": bool(row.get("archive_skipped_file_samples_truncated", False)),
        "counts": {
            "strategy_count": _row_int(row, "strategy_count"),
            "strategy_included_source_count": _row_int(row, "strategy_included_source_count"),
            "strategy_skipped_source_count": _row_int(row, "strategy_skipped_source_count"),
            "descriptor_count": _row_int(row, "descriptor_count"),
            "archive_file_count": _row_int(row, "archive_file_count"),
            "archive_skipped_count": _row_int(row, "archive_skipped_count"),
            "archive_coverage_ready_descriptor_count": _row_int(row, "archive_coverage_ready_descriptor_count"),
            "archive_coverage_blocked_descriptor_count": _row_int(row, "archive_coverage_blocked_descriptor_count"),
            "archive_coverage_requested_window_row_count": _row_int(
                row,
                "archive_coverage_requested_window_row_count",
            ),
            "venue_expansion_gap_row_count": _row_int(row, "venue_expansion_gap_row_count"),
            "venue_expansion_actionable_gap_count": _venue_expansion_actionable_gap_count(row),
            "venue_expansion_missing_target_count": _row_int(row, "venue_expansion_missing_target_count"),
            "venue_expansion_blocked_target_count": _row_int(row, "venue_expansion_blocked_target_count"),
            "venue_expansion_mixed_target_count": _row_int(row, "venue_expansion_mixed_target_count"),
            "preflight_trial_estimate": _row_int(row, "preflight_trial_estimate"),
            "preflight_runnable_trial_estimate": _row_int(row, "preflight_runnable_trial_estimate"),
            "preflight_blocked_trial_estimate": _row_int(row, "preflight_blocked_trial_estimate"),
            "result_count": _row_int(row, "result_count"),
            "screened_count": _row_int(row, "screened_count"),
            "rejected_count": _row_int(row, "rejected_count"),
            "blocked_count": _row_int(row, "blocked_count"),
            "evidence_request_count": _row_int(row, "evidence_request_count"),
            "deduped_validation_request_count": _validation_request_count(row),
            "leaderboard_hypothesis_count": _row_int(row, "leaderboard_hypothesis_count"),
            "artifact_reference_count": _row_int(row, "artifact_reference_count"),
            "artifact_present_count": _row_int(row, "artifact_present_count"),
            "artifact_missing_count": _row_int(row, "artifact_missing_count"),
        },
        "artifact_availability_status": row.get("artifact_availability_status"),
        "artifact_missing_keys": _as_list(row.get("artifact_missing_keys")),
        "top_archive_blockers": _as_list(row.get("top_archive_blockers"))[:5],
        "coverage_status_counts": _as_dict(row.get("coverage_status_counts")),
        "archive_coverage_blocker_reason_counts": _as_dict(row.get("archive_coverage_blocker_reason_counts")),
        "archive_coverage_blocker_samples": _as_list(row.get("archive_coverage_blocker_samples"))[:10],
        "archive_coverage_blocker_samples_truncated": bool(
            row.get("archive_coverage_blocker_samples_truncated", False)
        ),
        "venue_expansion_target_venues": _as_list(row.get("venue_expansion_target_venues")),
        "venue_expansion_status_counts": _as_dict(row.get("venue_expansion_status_counts")),
        "venue_expansion_action_counts": _as_dict(row.get("venue_expansion_action_counts")),
        "venue_expansion_gap_samples": _as_list(row.get("venue_expansion_gap_samples"))[:10],
        "venue_expansion_gap_samples_truncated": bool(row.get("venue_expansion_gap_samples_truncated", False)),
        "top_preflight_blockers": _as_list(row.get("top_preflight_blockers"))[:5],
        "preflight_status_counts": _as_dict(row.get("preflight_status_counts")),
        "preflight_blocker_reason_counts": _as_dict(row.get("preflight_blocker_reason_counts")),
        "preflight_blocker_samples": _as_list(row.get("preflight_blocker_samples"))[:10],
        "preflight_blocker_samples_truncated": bool(row.get("preflight_blocker_samples_truncated", False)),
        "falsification_decision_counts": _as_dict(row.get("falsification_decision_counts")),
        "rejection_falsification_samples": _as_list(row.get("rejection_falsification_samples"))[:10],
        "rejection_falsification_samples_truncated": bool(
            row.get("rejection_falsification_samples_truncated", False)
        ),
        "top_validation_requests": _as_list(row.get("top_validation_requests"))[:5],
        "artifact_paths": _as_dict(row.get("artifact_paths")),
        "strict_validation_executed": bool(row.get("strict_validation_executed", False)),
        "candidate_pack_written": bool(row.get("candidate_pack_written", False)),
        "candidate_pack_paths": _as_list(row.get("candidate_pack_paths")),
    }
    require_sandbox_boundary(item, payload_name="sandbox_iteration_action_queue_item")
    return item


def _queue_payload(
    rows: list[dict[str, Any]],
    *,
    predicate: Callable[[dict[str, Any]], bool],
    sort_key: Callable[[dict[str, Any]], tuple[Any, ...]],
    limit: int,
) -> tuple[list[dict[str, Any]], int, dict[str, Any]]:
    matching = sorted((row for row in rows if predicate(row)), key=sort_key)
    items = [_queue_item(row) for row in matching[:limit]]
    return items, len(matching), _queue_summary(matching, visible_item_count=len(items))


def _archive_blocker_count(row: dict[str, Any], reason: str) -> int:
    full_counts = _as_dict(row.get("archive_coverage_blocker_reason_counts"))
    if reason in full_counts:
        return int(full_counts.get(reason, 0) or 0)
    total = 0
    for blocker in _as_list(row.get("top_archive_blockers")):
        if not isinstance(blocker, dict):
            continue
        if str(blocker.get("reason")) == reason:
            total += int(blocker.get("count", 0) or 0)
    return total


def _venue_expansion_actionable_gap_count(row: dict[str, Any]) -> int:
    row_count = _row_int(row, "venue_expansion_actionable_gap_count")
    if row_count > 0:
        return row_count
    return sum(
        int(count or 0)
        for action, count in _count_map(row.get("venue_expansion_action_counts")).items()
        if str(action) != "use_ready_archive_bucket"
    )


def _venue_expansion_reason_codes(row: dict[str, Any]) -> list[str]:
    action_counts = _count_map(row.get("venue_expansion_action_counts"))
    reason_codes = [
        f"venue_expansion_action:{action}"
        for action, count in sorted(action_counts.items())
        if str(action) != "use_ready_archive_bucket" and int(count or 0) > 0
    ]
    if reason_codes:
        return reason_codes
    return ["venue_expansion_gaps"]


def _count_map(raw_counts: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for key, value in _as_dict(raw_counts).items():
        counts[str(key)] = counts.get(str(key), 0) + int(value or 0)
    return counts


def _merge_count_map(target: dict[str, int], raw_counts: Any) -> None:
    for key, value in _count_map(raw_counts).items():
        target[key] = target.get(key, 0) + int(value or 0)


def _sorted_counts(counts: dict[str, int]) -> dict[str, int]:
    return dict(sorted(counts.items(), key=lambda item: (-int(item[1]), item[0])))


def _row_value_counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "missing")
        counts[value] = counts.get(value, 0) + 1
    return _sorted_counts(counts)


def _row_count_map(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        _merge_count_map(counts, row.get(key))
    return _sorted_counts(counts)


def _row_list_counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        for value in _as_list(row.get(key)):
            item = str(value)
            counts[item] = counts.get(item, 0) + 1
    return _sorted_counts(counts)


def _recommended_action_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        actions = _row_recommended_actions(row)
        if not actions:
            counts["none"] = counts.get("none", 0) + 1
            continue
        for action in actions:
            if isinstance(action, dict):
                name = str(action.get("action") or "unknown")
            else:
                name = str(action or "unknown")
            counts[name] = counts.get(name, 0) + 1
    return _sorted_counts(counts)


def _agent_action_priority(action: str) -> int:
    return int(_AGENT_ACTION_PRIORITIES.get(action, 100))


def _row_action_source_queues(row: dict[str, Any], action: str) -> list[str]:
    queues: list[str] = []
    if action == "review_descriptor_only_strict_validation_requests" and _validation_request_count(row) > 0:
        queues.append("strict_validation_request_queue")
    if action in {
        "repair_archive_manifest_or_requested_window",
        "refresh_archive_source_integrity_metadata_or_restore_source_file",
        "repair_strategy_catalog_signal_columns_or_materialize_blueprints",
        "add_required_ohlc_columns_or_use_fixed_hold_exit",
        "repair_preflight_blockers",
    }:
        queues.append("preflight_repair_queue")
    if action == "repair_strategy_catalog_sources" and _strategy_source_repair_count(row) > 0:
        queues.append("strategy_source_repair_queue")
    if action == "adjust_iteration_window_or_refresh_archive_manifest":
        queues.append("archive_window_repair_queue")
    if action == "repair_or_add_venue_expansion_archives":
        queues.append("venue_expansion_gap_queue")
    if action == "restore_or_regenerate_iteration_agent_brief":
        queues.append("missing_brief_queue")
    if action == "restore_or_rerun_missing_iteration_artifacts":
        queues.append("artifact_repair_queue")
    if action in {
        "review_rejections_and_falsified_hypotheses",
        "inspect_blocked_or_empty_sandbox_iteration",
    }:
        queues.append("rejection_review_queue")
    return sorted(set(queues))


def _agent_action_plan_item(
    row: dict[str, Any],
    action_entry: Any,
    *,
    action_rank: int,
) -> dict[str, Any]:
    entry = dict(action_entry) if isinstance(action_entry, dict) else {"action": str(action_entry)}
    action = str(entry.get("action") or "unknown")
    item = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_agent_action_plan_item",
        "iteration_id": row.get("iteration_id"),
        "run_id": row.get("run_id"),
        "iteration_status": row.get("iteration_status"),
        "next_action": row.get("next_action"),
        "primary_recommended_action": row.get("recommended_action"),
        "action": action,
        "action_priority": _agent_action_priority(action),
        "action_rank": int(action_rank),
        "is_primary_action": int(action_rank) == 1,
        "blocked_by_prior_action": int(action_rank) > 1,
        "reason_codes": _as_list(entry.get("reason_codes")),
        "row_reason_codes": _as_list(row.get("reason_codes")),
        "source_queues": _row_action_source_queues(row, action),
        "input_replay_context": _as_dict(row.get("input_replay_context")),
        "input_replay_context_id": row.get("input_replay_context_id"),
        "input_replay_command": row.get("input_replay_command"),
        "input_replay_command_argv": _as_list(row.get("input_replay_command_argv")),
        "input_replay_strategy_input_mode": row.get("input_replay_strategy_input_mode"),
        "input_replay_venue_input_mode": row.get("input_replay_venue_input_mode"),
        "brief_status": row.get("brief_status"),
        "artifact_availability_status": row.get("artifact_availability_status"),
        "artifact_missing_keys": _as_list(row.get("artifact_missing_keys")),
        "iteration_manifest_path": row.get("iteration_manifest_path"),
        "agent_brief_json_path": row.get("agent_brief_json_path"),
        "strategy_catalog_json_path": row.get("strategy_catalog_json_path"),
        "strategy_build_report_json_path": row.get("strategy_build_report_json_path"),
        "strategy_source_status_counts": _as_dict(row.get("strategy_source_status_counts")),
        "strategy_source_skip_reason_counts": _as_dict(row.get("strategy_source_skip_reason_counts")),
        "strategy_skipped_source_samples": _as_list(row.get("strategy_skipped_source_samples"))[:10],
        "strategy_skipped_source_samples_truncated": bool(row.get("strategy_skipped_source_samples_truncated", False)),
        "venue_archive_manifest_path": row.get("venue_archive_manifest_path"),
        "archive_build_report_json_path": row.get("archive_build_report_json_path"),
        "archive_coverage_venue_expansion_gaps_parquet_path": row.get(
            "archive_coverage_venue_expansion_gaps_parquet_path"
        ),
        "archive_file_status_counts": _as_dict(row.get("archive_file_status_counts")),
        "archive_file_suffix_counts": _as_dict(row.get("archive_file_suffix_counts")),
        "archive_file_skip_reason_counts": _as_dict(row.get("archive_file_skip_reason_counts")),
        "archive_skipped_file_samples": _as_list(row.get("archive_skipped_file_samples"))[:10],
        "archive_skipped_file_samples_truncated": bool(row.get("archive_skipped_file_samples_truncated", False)),
        "counts": {
            "action_count": int(entry.get("count", 0) or 0),
            "strategy_count": _row_int(row, "strategy_count"),
            "strategy_skipped_source_count": _row_int(row, "strategy_skipped_source_count"),
            "descriptor_count": _row_int(row, "descriptor_count"),
            "archive_file_count": _row_int(row, "archive_file_count"),
            "archive_skipped_count": _row_int(row, "archive_skipped_count"),
            "archive_coverage_blocked_descriptor_count": _row_int(
                row,
                "archive_coverage_blocked_descriptor_count",
            ),
            "archive_coverage_requested_window_row_count": _row_int(
                row,
                "archive_coverage_requested_window_row_count",
            ),
            "venue_expansion_gap_row_count": _row_int(row, "venue_expansion_gap_row_count"),
            "venue_expansion_actionable_gap_count": _venue_expansion_actionable_gap_count(row),
            "venue_expansion_missing_target_count": _row_int(row, "venue_expansion_missing_target_count"),
            "venue_expansion_blocked_target_count": _row_int(row, "venue_expansion_blocked_target_count"),
            "venue_expansion_mixed_target_count": _row_int(row, "venue_expansion_mixed_target_count"),
            "preflight_blocked_trial_estimate": _row_int(row, "preflight_blocked_trial_estimate"),
            "result_count": _row_int(row, "result_count"),
            "screened_count": _row_int(row, "screened_count"),
            "rejected_count": _row_int(row, "rejected_count"),
            "blocked_count": _row_int(row, "blocked_count"),
            "deduped_validation_request_count": _validation_request_count(row),
            "artifact_missing_count": _row_int(row, "artifact_missing_count"),
        },
        "coverage_status_counts": _as_dict(row.get("coverage_status_counts")),
        "archive_coverage_blocker_reason_counts": _as_dict(row.get("archive_coverage_blocker_reason_counts")),
        "archive_coverage_blocker_samples": _as_list(row.get("archive_coverage_blocker_samples"))[:10],
        "archive_coverage_blocker_samples_truncated": bool(
            row.get("archive_coverage_blocker_samples_truncated", False)
        ),
        "venue_expansion_target_venues": _as_list(row.get("venue_expansion_target_venues")),
        "venue_expansion_status_counts": _as_dict(row.get("venue_expansion_status_counts")),
        "venue_expansion_action_counts": _as_dict(row.get("venue_expansion_action_counts")),
        "venue_expansion_gap_samples": _as_list(row.get("venue_expansion_gap_samples"))[:10],
        "venue_expansion_gap_samples_truncated": bool(row.get("venue_expansion_gap_samples_truncated", False)),
        "preflight_status_counts": _as_dict(row.get("preflight_status_counts")),
        "preflight_blocker_reason_counts": _as_dict(row.get("preflight_blocker_reason_counts")),
        "top_archive_blockers": _as_list(row.get("top_archive_blockers"))[:5],
        "top_preflight_blockers": _as_list(row.get("top_preflight_blockers"))[:5],
        "preflight_blocker_samples": _as_list(row.get("preflight_blocker_samples"))[:10],
        "preflight_blocker_samples_truncated": bool(row.get("preflight_blocker_samples_truncated", False)),
        "falsification_decision_counts": _as_dict(row.get("falsification_decision_counts")),
        "rejection_falsification_samples": _as_list(row.get("rejection_falsification_samples"))[:10],
        "rejection_falsification_samples_truncated": bool(
            row.get("rejection_falsification_samples_truncated", False)
        ),
        "top_validation_requests": _as_list(row.get("top_validation_requests"))[:5],
        "artifact_paths": _as_dict(row.get("artifact_paths")),
        "strict_validation_executed": bool(row.get("strict_validation_executed", False)),
        "candidate_pack_written": bool(row.get("candidate_pack_written", False)),
        "candidate_pack_paths": _as_list(row.get("candidate_pack_paths")),
    }
    require_sandbox_boundary(item, payload_name="sandbox_iteration_agent_action_plan_item")
    return item


def _agent_action_plan_summary(items: list[dict[str, Any]], *, visible_item_count: int) -> dict[str, Any]:
    action_counts: dict[str, int] = {}
    source_queue_counts: dict[str, int] = {}
    iteration_status_counts: dict[str, int] = {}
    blocked_by_prior_action_count = 0
    primary_action_count = 0
    for item in items:
        action = str(item.get("action") or "unknown")
        action_counts[action] = action_counts.get(action, 0) + 1
        status = str(item.get("iteration_status") or "missing")
        iteration_status_counts[status] = iteration_status_counts.get(status, 0) + 1
        if bool(item.get("blocked_by_prior_action", False)):
            blocked_by_prior_action_count += 1
        if bool(item.get("is_primary_action", False)):
            primary_action_count += 1
        for queue_name in _as_list(item.get("source_queues")):
            key = str(queue_name)
            source_queue_counts[key] = source_queue_counts.get(key, 0) + 1
    return {
        "matched_action_item_count": len(items),
        "visible_item_count": int(visible_item_count),
        "truncated_count": max(0, len(items) - int(visible_item_count)),
        "action_counts": _sorted_counts(action_counts),
        "source_queue_counts": _sorted_counts(source_queue_counts),
        "iteration_status_counts": _sorted_counts(iteration_status_counts),
        "primary_action_count": primary_action_count,
        "blocked_by_prior_action_count": blocked_by_prior_action_count,
    }


def _build_agent_action_plan(
    rows: list[dict[str, Any]],
    *,
    limit: int = SANDBOX_ITERATION_AGENT_ACTION_PLAN_LIMIT,
) -> tuple[list[dict[str, Any]], int, int, dict[str, Any]]:
    if limit <= 0:
        raise ValueError("agent action plan limit must be positive")
    items: list[dict[str, Any]] = []
    for row in rows:
        for action_rank, action_entry in enumerate(_row_recommended_actions(row), start=1):
            items.append(_agent_action_plan_item(row, action_entry, action_rank=action_rank))
    items = sorted(
        items,
        key=lambda item: (
            int(item.get("action_priority", 100)),
            bool(item.get("blocked_by_prior_action", False)),
            -int(_as_dict(item.get("counts")).get("action_count", 0) or 0),
            str(item.get("iteration_id") or ""),
            str(item.get("action") or ""),
        ),
    )
    visible = items[:limit]
    return (
        visible,
        len(items),
        max(0, len(items) - len(visible)),
        _agent_action_plan_summary(items, visible_item_count=len(visible)),
    )


def _input_replay_path_reference(key: str, raw_path: Any, *, expected_type: str) -> dict[str, Any]:
    path = Path(str(raw_path)).expanduser()
    exists = path.exists()
    is_file = path.is_file() if exists else False
    is_dir = path.is_dir() if exists else False
    if not exists:
        status = "missing"
    elif expected_type == "file" and not is_file:
        status = "wrong_type"
    elif expected_type == "directory" and not is_dir:
        status = "wrong_type"
    else:
        status = "present"
    return {
        "key": key,
        "path": str(path),
        "expected_type": expected_type,
        "status": status,
        "exists": exists,
        "is_file": is_file,
        "is_dir": is_dir,
    }


def _input_replay_path_availability(context: dict[str, Any]) -> dict[str, Any]:
    references: list[dict[str, Any]] = []
    output_dir = context.get("output_dir")
    if output_dir:
        references.append(_input_replay_path_reference("output_dir", output_dir, expected_type="directory"))
    spec_path = context.get("spec_input_path")
    if spec_path:
        references.append(_input_replay_path_reference("spec_input_path", spec_path, expected_type="file"))
    strategy_catalog_path = context.get("strategy_catalog_input_path")
    if strategy_catalog_path:
        references.append(
            _input_replay_path_reference(
                "strategy_catalog_input_path",
                strategy_catalog_path,
                expected_type="file",
            )
        )
    for index, path in enumerate(_as_list(context.get("catalog_root_paths")), start=1):
        if path:
            references.append(
                _input_replay_path_reference(
                    f"catalog_root_paths[{index}]",
                    path,
                    expected_type="directory",
                )
            )
    venue_archives_path = context.get("venue_archives_input_path")
    if venue_archives_path:
        references.append(
            _input_replay_path_reference(
                "venue_archives_input_path",
                venue_archives_path,
                expected_type="file",
            )
        )
    for index, path in enumerate(_as_list(context.get("archive_root_paths")), start=1):
        if path:
            references.append(
                _input_replay_path_reference(
                    f"archive_root_paths[{index}]",
                    path,
                    expected_type="directory",
                )
            )
    missing_keys = sorted(str(reference["key"]) for reference in references if reference["status"] == "missing")
    wrong_type_keys = sorted(str(reference["key"]) for reference in references if reference["status"] == "wrong_type")
    present_count = sum(1 for reference in references if reference["status"] == "present")
    if not references:
        status = "no_input_references"
    elif missing_keys or wrong_type_keys:
        status = "missing_or_invalid_inputs"
    else:
        status = "all_present"
    status_counts: dict[str, int] = {}
    for reference in references:
        key = str(reference.get("status") or "missing")
        status_counts[key] = status_counts.get(key, 0) + 1
    return {
        "status": status,
        "reference_count": len(references),
        "present_count": present_count,
        "missing_count": len(missing_keys),
        "wrong_type_count": len(wrong_type_keys),
        "missing_keys": missing_keys,
        "wrong_type_keys": wrong_type_keys,
        "status_counts": _sorted_counts(status_counts),
        "references": references,
    }


def _input_replay_worklist_item(row: dict[str, Any], *, worklist_rank: int) -> dict[str, Any]:
    context = _as_dict(row.get("input_replay_context"))
    command_argv = _as_list(row.get("input_replay_command_argv"))
    recommended_actions = _row_recommended_actions(row)
    recommended_action = recommended_actions[0]["action"] if recommended_actions else "none"
    path_availability = _input_replay_path_availability(context)
    blocker_reasons: list[str] = []
    if not command_argv:
        blocker_reasons.append("missing_command_argv")
    if row.get("input_replay_command") != "run-rapid-strategy-sandbox-iteration":
        blocker_reasons.append("unexpected_replay_command")
    if context.get("execution_mode") != "descriptor_only_no_execution":
        blocker_reasons.append("unexpected_execution_mode")
    if int(path_availability["missing_count"]) > 0:
        blocker_reasons.append("missing_input_replay_paths")
    if int(path_availability["wrong_type_count"]) > 0:
        blocker_reasons.append("wrong_type_input_replay_paths")
    item = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_input_replay_worklist_item",
        "worklist_version": SANDBOX_ITERATION_INPUT_REPLAY_WORKLIST_VERSION,
        "worklist_rank": int(worklist_rank),
        "iteration_id": row.get("iteration_id"),
        "run_id": row.get("run_id"),
        "iteration_status": row.get("iteration_status"),
        "next_action": row.get("next_action"),
        "recommended_action": recommended_action,
        "recommended_actions": recommended_actions,
        "action_priority": _agent_action_priority(recommended_action),
        "source_queues": _row_action_source_queues(row, recommended_action),
        "input_replay_context": context,
        "input_replay_context_id": row.get("input_replay_context_id"),
        "input_replay_command": row.get("input_replay_command"),
        "input_replay_command_argv": command_argv,
        "input_replay_command_argv_truncated": bool(context.get("command_argv_truncated", False)),
        "input_replay_execution_mode": context.get("execution_mode"),
        "input_replay_strategy_input_mode": row.get("input_replay_strategy_input_mode"),
        "input_replay_venue_input_mode": row.get("input_replay_venue_input_mode"),
        "input_replay_output_dir": context.get("output_dir"),
        "input_replay_spec_input_path": context.get("spec_input_path"),
        "input_replay_strategy_catalog_input_path": context.get("strategy_catalog_input_path"),
        "input_replay_catalog_root_paths": _as_list(context.get("catalog_root_paths")),
        "input_replay_venue_archives_input_path": context.get("venue_archives_input_path"),
        "input_replay_archive_root_paths": _as_list(context.get("archive_root_paths")),
        "input_replay_window_start": context.get("window_start"),
        "input_replay_window_end": context.get("window_end"),
        "input_replay_window_preset": context.get("window_preset"),
        "input_replay_window_as_of_date": context.get("window_as_of_date"),
        "input_replay_window_lookback_days": context.get("window_lookback_days"),
        "input_replay_holding_periods": _as_list(context.get("holding_periods")),
        "input_replay_round_trip_cost_bps": context.get("round_trip_cost_bps"),
        "input_replay_min_trades": context.get("min_trades"),
        "input_replay_max_evidence_requests": context.get("max_evidence_requests"),
        "input_replay_rank_top_n": context.get("rank_top_n"),
        "input_replay_min_request_score": context.get("min_request_score"),
        "input_replay_catalog_max_files": context.get("catalog_max_files"),
        "input_replay_archive_max_files": context.get("archive_max_files"),
        "input_replay_archive_venue": context.get("archive_venue"),
        "input_replay_archive_symbol": context.get("archive_symbol"),
        "input_replay_archive_data_family": context.get("archive_data_family"),
        "input_replay_archive_interval": context.get("archive_interval"),
        "input_replay_leaderboard_max_runs": context.get("leaderboard_max_runs"),
        "input_replay_leaderboard_top_n": context.get("leaderboard_top_n"),
        "input_replay_ready": not blocker_reasons,
        "input_replay_blocker_reasons": blocker_reasons,
        "input_replay_path_availability_status": path_availability["status"],
        "input_replay_path_reference_count": path_availability["reference_count"],
        "input_replay_path_present_count": path_availability["present_count"],
        "input_replay_path_missing_count": path_availability["missing_count"],
        "input_replay_path_wrong_type_count": path_availability["wrong_type_count"],
        "input_replay_path_missing_keys": path_availability["missing_keys"],
        "input_replay_path_wrong_type_keys": path_availability["wrong_type_keys"],
        "input_replay_path_status_counts": path_availability["status_counts"],
        "input_replay_path_references": path_availability["references"],
        "brief_status": row.get("brief_status"),
        "artifact_availability_status": row.get("artifact_availability_status"),
        "artifact_missing_keys": _as_list(row.get("artifact_missing_keys")),
        "artifact_missing_count": _row_int(row, "artifact_missing_count"),
        "iteration_manifest_path": row.get("iteration_manifest_path"),
        "agent_brief_json_path": row.get("agent_brief_json_path"),
        "strategy_catalog_json_path": row.get("strategy_catalog_json_path"),
        "strategy_build_report_json_path": row.get("strategy_build_report_json_path"),
        "venue_archive_manifest_path": row.get("venue_archive_manifest_path"),
        "archive_build_report_json_path": row.get("archive_build_report_json_path"),
        "deduped_validation_request_count": _validation_request_count(row),
        "preflight_blocked_trial_estimate": _row_int(row, "preflight_blocked_trial_estimate"),
        "result_count": _row_int(row, "result_count"),
        "rejected_count": _row_int(row, "rejected_count"),
        "blocked_count": _row_int(row, "blocked_count"),
        "strict_validation_executed": bool(row.get("strict_validation_executed", False)),
        "candidate_pack_written": bool(row.get("candidate_pack_written", False)),
        "candidate_pack_paths": _as_list(row.get("candidate_pack_paths")),
    }
    require_sandbox_boundary(item, payload_name="sandbox_iteration_input_replay_worklist_item")
    return item


def _input_replay_worklist_summary(items: list[dict[str, Any]], *, missing_context_count: int) -> dict[str, Any]:
    ready_count = 0
    blocker_counts: dict[str, int] = {}
    total_path_reference_count = 0
    total_path_present_count = 0
    total_path_missing_count = 0
    total_path_wrong_type_count = 0
    for item in items:
        if bool(item.get("input_replay_ready", False)):
            ready_count += 1
        for reason in _as_list(item.get("input_replay_blocker_reasons")):
            key = str(reason)
            blocker_counts[key] = blocker_counts.get(key, 0) + 1
        total_path_reference_count += _row_int(item, "input_replay_path_reference_count")
        total_path_present_count += _row_int(item, "input_replay_path_present_count")
        total_path_missing_count += _row_int(item, "input_replay_path_missing_count")
        total_path_wrong_type_count += _row_int(item, "input_replay_path_wrong_type_count")
    context_group_counts = _input_replay_context_group_counts(items)
    duplicate_group_counts = {
        key: count for key, count in context_group_counts.items() if int(count or 0) > 1
    }
    return {
        "item_count": len(items),
        "missing_context_count": int(missing_context_count),
        "ready_count": ready_count,
        "blocked_count": max(0, len(items) - ready_count),
        "iteration_status_counts": _row_value_counts(items, "iteration_status"),
        "recommended_action_counts": _row_value_counts(items, "recommended_action"),
        "artifact_availability_status_counts": _row_value_counts(items, "artifact_availability_status"),
        "command_counts": _row_value_counts(items, "input_replay_command"),
        "strategy_input_mode_counts": _row_value_counts(items, "input_replay_strategy_input_mode"),
        "venue_input_mode_counts": _row_value_counts(items, "input_replay_venue_input_mode"),
        "archive_venue_counts": _row_value_counts(items, "input_replay_archive_venue"),
        "archive_symbol_counts": _row_value_counts(items, "input_replay_archive_symbol"),
        "archive_data_family_counts": _row_value_counts(items, "input_replay_archive_data_family"),
        "archive_interval_counts": _row_value_counts(items, "input_replay_archive_interval"),
        "archive_bucket_counts": _input_replay_archive_bucket_counts(items),
        "archive_bucket_ready_counts": _input_replay_archive_bucket_counts(
            [item for item in items if bool(item.get("input_replay_ready", False))]
        ),
        "archive_bucket_blocked_counts": _input_replay_archive_bucket_counts(
            [item for item in items if not bool(item.get("input_replay_ready", False))]
        ),
        "window_start_counts": _row_value_counts(items, "input_replay_window_start"),
        "window_end_counts": _row_value_counts(items, "input_replay_window_end"),
        "window_preset_counts": _row_value_counts(items, "input_replay_window_preset"),
        "window_bucket_counts": _input_replay_window_bucket_counts(items),
        "archive_window_bucket_counts": _input_replay_archive_window_bucket_counts(items),
        "archive_window_ready_counts": _input_replay_archive_window_bucket_counts(
            [item for item in items if bool(item.get("input_replay_ready", False))]
        ),
        "archive_window_blocked_counts": _input_replay_archive_window_bucket_counts(
            [item for item in items if not bool(item.get("input_replay_ready", False))]
        ),
        "unique_replay_context_count": len(context_group_counts),
        "replay_context_group_counts": context_group_counts,
        "duplicate_replay_context_group_count": len(duplicate_group_counts),
        "duplicate_replay_context_item_count": sum(duplicate_group_counts.values()),
        "duplicate_replay_context_group_counts": duplicate_group_counts,
        "duplicate_replay_context_group_keys": list(duplicate_group_counts),
        "archive_bucket_unique_replay_context_counts": _input_replay_archive_bucket_unique_context_counts(items),
        "archive_window_unique_replay_context_counts": _input_replay_archive_window_unique_context_counts(items),
        "path_availability_status_counts": _row_value_counts(items, "input_replay_path_availability_status"),
        "path_missing_key_counts": _row_list_counts(items, "input_replay_path_missing_keys"),
        "path_wrong_type_key_counts": _row_list_counts(items, "input_replay_path_wrong_type_keys"),
        "total_path_reference_count": total_path_reference_count,
        "total_path_present_count": total_path_present_count,
        "total_path_missing_count": total_path_missing_count,
        "total_path_wrong_type_count": total_path_wrong_type_count,
        "replay_blocker_reason_counts": _sorted_counts(blocker_counts),
    }


def _input_replay_duplicate_group_key(item: dict[str, Any]) -> str:
    context_id = item.get("input_replay_context_id")
    if context_id:
        return str(context_id)
    return digest_payload(
        {
            "input_replay_context": _as_dict(item.get("input_replay_context")),
            "input_replay_command_argv": _as_list(item.get("input_replay_command_argv")),
        },
        prefix="sbxreplayctx",
    )


def _input_replay_context_group_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        key = str(item.get("input_replay_duplicate_group_key") or _input_replay_duplicate_group_key(item))
        counts[key] = counts.get(key, 0) + 1
    return _sorted_counts(counts)


def _input_replay_archive_bucket_key(item: dict[str, Any]) -> str:
    return "|".join(
        [
            str(item.get("input_replay_archive_venue") or "missing"),
            str(item.get("input_replay_archive_symbol") or "missing"),
            str(item.get("input_replay_archive_data_family") or "missing"),
            str(item.get("input_replay_archive_interval") or "missing"),
        ]
    )


def _input_replay_window_bucket_key(item: dict[str, Any]) -> str:
    return "|".join(
        [
            str(item.get("input_replay_window_start") or "missing"),
            str(item.get("input_replay_window_end") or "missing"),
            str(item.get("input_replay_window_preset") or "missing"),
        ]
    )


def _input_replay_archive_window_bucket_key(item: dict[str, Any]) -> str:
    return "|".join(
        [
            _input_replay_archive_bucket_key(item),
            str(item.get("input_replay_window_start") or "missing"),
            str(item.get("input_replay_window_end") or "missing"),
        ]
    )


def _input_replay_unique_context_counts_by_bucket(
    items: list[dict[str, Any]],
    bucket_for_item: Callable[[dict[str, Any]], str],
) -> dict[str, int]:
    grouped: dict[str, set[str]] = {}
    for item in items:
        bucket = bucket_for_item(item)
        grouped.setdefault(bucket, set()).add(_input_replay_duplicate_group_key(item))
    return _sorted_counts({bucket: len(keys) for bucket, keys in grouped.items()})


def _input_replay_archive_bucket_unique_context_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    return _input_replay_unique_context_counts_by_bucket(items, _input_replay_archive_bucket_key)


def _input_replay_archive_window_unique_context_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    return _input_replay_unique_context_counts_by_bucket(items, _input_replay_archive_window_bucket_key)


def _annotate_input_replay_duplicates(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    group_counts = _input_replay_context_group_counts(items)
    for item in items:
        group_key = _input_replay_duplicate_group_key(item)
        duplicate_count = int(group_counts.get(group_key, 0) or 0)
        item["input_replay_duplicate_group_key"] = group_key
        item["input_replay_context_duplicate_count"] = duplicate_count
        item["input_replay_context_is_duplicate"] = duplicate_count > 1
        require_sandbox_boundary(item, payload_name="sandbox_iteration_input_replay_worklist_item")
    return items


def _input_replay_archive_bucket_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        bucket = _input_replay_archive_bucket_key(item)
        counts[bucket] = counts.get(bucket, 0) + 1
    return _sorted_counts(counts)


def _input_replay_window_bucket_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        bucket = _input_replay_window_bucket_key(item)
        counts[bucket] = counts.get(bucket, 0) + 1
    return _sorted_counts(counts)


def _input_replay_archive_window_bucket_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        bucket = _input_replay_archive_window_bucket_key(item)
        counts[bucket] = counts.get(bucket, 0) + 1
    return _sorted_counts(counts)


def _build_input_replay_worklist(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int, dict[str, Any]]:
    source_rows = [row for row in rows if _as_dict(row.get("input_replay_context"))]
    source_rows = sorted(
        source_rows,
        key=lambda row: (
            _agent_action_priority(row.get("recommended_action") or "none"),
            str(row.get("iteration_status") or ""),
            str(row.get("iteration_id") or ""),
        ),
    )
    items = [
        _input_replay_worklist_item(row, worklist_rank=rank)
        for rank, row in enumerate(source_rows, start=1)
    ]
    items = _annotate_input_replay_duplicates(items)
    missing_context_count = max(0, len(rows) - len(items))
    return (
        items,
        missing_context_count,
        _input_replay_worklist_summary(items, missing_context_count=missing_context_count),
    )


def _input_replay_batch_plan_item(source_items: list[dict[str, Any]], *, batch_rank: int) -> dict[str, Any]:
    sorted_items = sorted(source_items, key=lambda item: _row_int(item, "worklist_rank"))
    representative = sorted_items[0]
    source_iteration_ids = [
        str(item.get("iteration_id"))
        for item in sorted_items
        if item.get("iteration_id") is not None
    ]
    source_worklist_ranks = [_row_int(item, "worklist_rank") for item in sorted_items]
    item = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_input_replay_batch_plan_item",
        "plan_version": SANDBOX_ITERATION_INPUT_REPLAY_BATCH_PLAN_VERSION,
        "batch_rank": int(batch_rank),
        "descriptor_only": True,
        "replay_command_execution_authorized": False,
        "strict_validation_authorized": False,
        "candidate_pack_write_authorized": False,
        "input_replay_context": _as_dict(representative.get("input_replay_context")),
        "input_replay_context_id": representative.get("input_replay_context_id"),
        "input_replay_duplicate_group_key": representative.get("input_replay_duplicate_group_key")
        or _input_replay_duplicate_group_key(representative),
        "input_replay_command": representative.get("input_replay_command"),
        "input_replay_command_argv": _as_list(representative.get("input_replay_command_argv")),
        "input_replay_command_argv_truncated": bool(
            representative.get("input_replay_command_argv_truncated", False)
        ),
        "input_replay_execution_mode": representative.get("input_replay_execution_mode"),
        "input_replay_ready": True,
        "input_replay_blocker_reasons": [],
        "input_replay_strategy_input_mode": representative.get("input_replay_strategy_input_mode"),
        "input_replay_venue_input_mode": representative.get("input_replay_venue_input_mode"),
        "input_replay_archive_venue": representative.get("input_replay_archive_venue"),
        "input_replay_archive_symbol": representative.get("input_replay_archive_symbol"),
        "input_replay_archive_data_family": representative.get("input_replay_archive_data_family"),
        "input_replay_archive_interval": representative.get("input_replay_archive_interval"),
        "input_replay_window_start": representative.get("input_replay_window_start"),
        "input_replay_window_end": representative.get("input_replay_window_end"),
        "input_replay_window_preset": representative.get("input_replay_window_preset"),
        "input_replay_window_as_of_date": representative.get("input_replay_window_as_of_date"),
        "input_replay_window_lookback_days": representative.get("input_replay_window_lookback_days"),
        "input_replay_output_dir": representative.get("input_replay_output_dir"),
        "input_replay_spec_input_path": representative.get("input_replay_spec_input_path"),
        "input_replay_strategy_catalog_input_path": representative.get("input_replay_strategy_catalog_input_path"),
        "input_replay_catalog_root_paths": _as_list(representative.get("input_replay_catalog_root_paths")),
        "input_replay_venue_archives_input_path": representative.get("input_replay_venue_archives_input_path"),
        "input_replay_archive_root_paths": _as_list(representative.get("input_replay_archive_root_paths")),
        "input_replay_holding_periods": _as_list(representative.get("input_replay_holding_periods")),
        "input_replay_round_trip_cost_bps": representative.get("input_replay_round_trip_cost_bps"),
        "input_replay_min_trades": representative.get("input_replay_min_trades"),
        "input_replay_max_evidence_requests": representative.get("input_replay_max_evidence_requests"),
        "input_replay_rank_top_n": representative.get("input_replay_rank_top_n"),
        "input_replay_min_request_score": representative.get("input_replay_min_request_score"),
        "input_replay_catalog_max_files": representative.get("input_replay_catalog_max_files"),
        "input_replay_archive_max_files": representative.get("input_replay_archive_max_files"),
        "input_replay_leaderboard_max_runs": representative.get("input_replay_leaderboard_max_runs"),
        "input_replay_leaderboard_top_n": representative.get("input_replay_leaderboard_top_n"),
        "input_replay_path_availability_status": representative.get("input_replay_path_availability_status"),
        "input_replay_path_reference_count": _row_int(representative, "input_replay_path_reference_count"),
        "input_replay_path_present_count": _row_int(representative, "input_replay_path_present_count"),
        "input_replay_path_missing_count": _row_int(representative, "input_replay_path_missing_count"),
        "input_replay_path_wrong_type_count": _row_int(representative, "input_replay_path_wrong_type_count"),
        "input_replay_path_status_counts": _as_dict(representative.get("input_replay_path_status_counts")),
        "representative_iteration_id": representative.get("iteration_id"),
        "representative_worklist_rank": _row_int(representative, "worklist_rank"),
        "source_item_count": len(sorted_items),
        "suppressed_duplicate_count": max(0, len(sorted_items) - 1),
        "source_iteration_ids": source_iteration_ids,
        "source_worklist_ranks": source_worklist_ranks,
        "suppressed_duplicate_iteration_ids": source_iteration_ids[1:],
        "source_recommended_action_counts": _row_value_counts(sorted_items, "recommended_action"),
        "source_artifact_availability_status_counts": _row_value_counts(
            sorted_items,
            "artifact_availability_status",
        ),
        "source_path_availability_status_counts": _row_value_counts(
            sorted_items,
            "input_replay_path_availability_status",
        ),
        "source_deduped_validation_request_count": sum(
            _row_int(item, "deduped_validation_request_count")
            for item in sorted_items
        ),
        "recommended_action": representative.get("recommended_action"),
        "artifact_availability_status": representative.get("artifact_availability_status"),
        "artifact_missing_count": _row_int(representative, "artifact_missing_count"),
        "iteration_manifest_path": representative.get("iteration_manifest_path"),
        "agent_brief_json_path": representative.get("agent_brief_json_path"),
        "strategy_catalog_json_path": representative.get("strategy_catalog_json_path"),
        "venue_archive_manifest_path": representative.get("venue_archive_manifest_path"),
    }
    require_sandbox_boundary(item, payload_name="sandbox_iteration_input_replay_batch_plan_item")
    return item


def _input_replay_batch_plan_summary(
    plan_items: list[dict[str, Any]],
    *,
    source_worklist_items: list[dict[str, Any]],
) -> dict[str, Any]:
    ready_items = [
        item for item in source_worklist_items if bool(item.get("input_replay_ready", False))
    ]
    blocked_items = [
        item for item in source_worklist_items if not bool(item.get("input_replay_ready", False))
    ]
    suppressed_duplicate_count = sum(
        _row_int(item, "suppressed_duplicate_count") for item in plan_items
    )
    return {
        "source_worklist_item_count": len(source_worklist_items),
        "ready_source_item_count": len(ready_items),
        "blocked_source_item_count": len(blocked_items),
        "plan_item_count": len(plan_items),
        "unique_ready_replay_context_count": len(plan_items),
        "suppressed_duplicate_source_item_count": suppressed_duplicate_count,
        "ready_duplicate_group_counts": _input_replay_context_group_counts(ready_items),
        "planned_duplicate_group_keys": [
            str(item.get("input_replay_duplicate_group_key"))
            for item in plan_items
            if item.get("input_replay_duplicate_group_key") is not None
        ],
        "blocked_replay_blocker_reason_counts": _row_list_counts(
            blocked_items,
            "input_replay_blocker_reasons",
        ),
        "source_path_availability_status_counts": _row_value_counts(
            source_worklist_items,
            "input_replay_path_availability_status",
        ),
        "ready_path_availability_status_counts": _row_value_counts(
            ready_items,
            "input_replay_path_availability_status",
        ),
        "blocked_path_availability_status_counts": _row_value_counts(
            blocked_items,
            "input_replay_path_availability_status",
        ),
        "ready_archive_bucket_counts": _input_replay_archive_bucket_counts(ready_items),
        "plan_archive_bucket_counts": _input_replay_archive_bucket_counts(plan_items),
        "ready_archive_window_bucket_counts": _input_replay_archive_window_bucket_counts(ready_items),
        "plan_archive_window_bucket_counts": _input_replay_archive_window_bucket_counts(plan_items),
        "source_recommended_action_counts": _row_value_counts(source_worklist_items, "recommended_action"),
        "plan_recommended_action_counts": _row_value_counts(plan_items, "recommended_action"),
    }


def _build_input_replay_batch_plan(
    worklist_items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    ready_items = [
        item for item in worklist_items if bool(item.get("input_replay_ready", False))
    ]
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in ready_items:
        group_key = str(item.get("input_replay_duplicate_group_key") or _input_replay_duplicate_group_key(item))
        groups.setdefault(group_key, []).append(item)
    grouped_items = sorted(
        groups.values(),
        key=lambda group: (
            min(_row_int(item, "worklist_rank") for item in group),
            str(_input_replay_duplicate_group_key(group[0])),
        ),
    )
    plan_items = [
        _input_replay_batch_plan_item(group, batch_rank=rank)
        for rank, group in enumerate(grouped_items, start=1)
    ]
    return (
        plan_items,
        _input_replay_batch_plan_summary(
            plan_items,
            source_worklist_items=worklist_items,
        ),
    )


def _queue_summary(rows: list[dict[str, Any]], *, visible_item_count: int) -> dict[str, Any]:
    return {
        "matched_iteration_count": len(rows),
        "visible_item_count": int(visible_item_count),
        "truncated_count": max(0, len(rows) - int(visible_item_count)),
        "iteration_status_counts": _row_value_counts(rows, "iteration_status"),
        "next_action_counts": _row_value_counts(rows, "next_action"),
        "recommended_action_counts": _recommended_action_counts(rows),
        "artifact_availability_status_counts": _row_value_counts(rows, "artifact_availability_status"),
        "artifact_missing_key_counts": _row_list_counts(rows, "artifact_missing_keys"),
        "strategy_source_status_counts": _row_count_map(rows, "strategy_source_status_counts"),
        "strategy_source_suffix_counts": _row_count_map(rows, "strategy_source_suffix_counts"),
        "strategy_source_skip_reason_counts": _row_count_map(rows, "strategy_source_skip_reason_counts"),
        "strategy_workbook_sheet_status_counts": _row_count_map(rows, "strategy_workbook_sheet_status_counts"),
        "strategy_workbook_sheet_kind_counts": _row_count_map(rows, "strategy_workbook_sheet_kind_counts"),
        "archive_file_status_counts": _row_count_map(rows, "archive_file_status_counts"),
        "archive_file_suffix_counts": _row_count_map(rows, "archive_file_suffix_counts"),
        "archive_file_skip_reason_counts": _row_count_map(rows, "archive_file_skip_reason_counts"),
        "coverage_status_counts": _row_count_map(rows, "coverage_status_counts"),
        "archive_coverage_blocker_reason_counts": _row_count_map(rows, "archive_coverage_blocker_reason_counts"),
        "venue_expansion_status_counts": _row_count_map(rows, "venue_expansion_status_counts"),
        "venue_expansion_action_counts": _row_count_map(rows, "venue_expansion_action_counts"),
        "preflight_status_counts": _row_count_map(rows, "preflight_status_counts"),
        "preflight_blocker_reason_counts": _row_count_map(rows, "preflight_blocker_reason_counts"),
        "falsification_decision_counts": _row_count_map(rows, "falsification_decision_counts"),
        "counts": {
            "strategy_count": sum(_row_int(row, "strategy_count") for row in rows),
            "strategy_included_source_count": sum(_row_int(row, "strategy_included_source_count") for row in rows),
            "strategy_skipped_source_count": sum(_row_int(row, "strategy_skipped_source_count") for row in rows),
            "descriptor_count": sum(_row_int(row, "descriptor_count") for row in rows),
            "archive_file_count": sum(_row_int(row, "archive_file_count") for row in rows),
            "archive_skipped_count": sum(_row_int(row, "archive_skipped_count") for row in rows),
            "archive_coverage_ready_descriptor_count": sum(
                _row_int(row, "archive_coverage_ready_descriptor_count") for row in rows
            ),
            "archive_coverage_blocked_descriptor_count": sum(
                _row_int(row, "archive_coverage_blocked_descriptor_count") for row in rows
            ),
            "archive_coverage_requested_window_row_count": sum(
                _row_int(row, "archive_coverage_requested_window_row_count") for row in rows
            ),
            "venue_expansion_gap_row_count": sum(_row_int(row, "venue_expansion_gap_row_count") for row in rows),
            "venue_expansion_actionable_gap_count": sum(
                _venue_expansion_actionable_gap_count(row) for row in rows
            ),
            "venue_expansion_missing_target_count": sum(
                _row_int(row, "venue_expansion_missing_target_count") for row in rows
            ),
            "venue_expansion_blocked_target_count": sum(
                _row_int(row, "venue_expansion_blocked_target_count") for row in rows
            ),
            "venue_expansion_mixed_target_count": sum(
                _row_int(row, "venue_expansion_mixed_target_count") for row in rows
            ),
            "preflight_trial_estimate": sum(_row_int(row, "preflight_trial_estimate") for row in rows),
            "preflight_runnable_trial_estimate": sum(
                _row_int(row, "preflight_runnable_trial_estimate") for row in rows
            ),
            "preflight_blocked_trial_estimate": sum(
                _row_int(row, "preflight_blocked_trial_estimate") for row in rows
            ),
            "result_count": sum(_row_int(row, "result_count") for row in rows),
            "screened_count": sum(_row_int(row, "screened_count") for row in rows),
            "rejected_count": sum(_row_int(row, "rejected_count") for row in rows),
            "blocked_count": sum(_row_int(row, "blocked_count") for row in rows),
            "evidence_request_count": sum(_row_int(row, "evidence_request_count") for row in rows),
            "deduped_validation_request_count": sum(_validation_request_count(row) for row in rows),
            "leaderboard_hypothesis_count": sum(_row_int(row, "leaderboard_hypothesis_count") for row in rows),
            "artifact_reference_count": sum(_row_int(row, "artifact_reference_count") for row in rows),
            "artifact_present_count": sum(_row_int(row, "artifact_present_count") for row in rows),
            "artifact_missing_count": sum(_row_int(row, "artifact_missing_count") for row in rows),
        },
    }


def _build_action_queues(
    rows: list[dict[str, Any]],
    *,
    limit: int = SANDBOX_ITERATION_ACTION_QUEUE_LIMIT,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, int], dict[str, int], dict[str, dict[str, Any]]]:
    request_queue, request_count, request_summary = _queue_payload(
        rows,
        predicate=lambda row: _validation_request_count(row) > 0,
        sort_key=lambda row: (
            -_validation_request_count(row),
            -_row_int(row, "screened_count"),
            -_row_int(row, "result_count"),
            str(row.get("iteration_id") or ""),
        ),
        limit=limit,
    )
    preflight_queue, preflight_count, preflight_summary = _queue_payload(
        rows,
        predicate=lambda row: row.get("next_action") == "repair_preflight_blockers"
        or row.get("iteration_status") == "blocked_by_preflight"
        or _row_int(row, "preflight_blocked_trial_estimate") > 0,
        sort_key=lambda row: (
            -_row_int(row, "preflight_blocked_trial_estimate"),
            -_row_int(row, "archive_coverage_blocked_descriptor_count"),
            str(row.get("iteration_id") or ""),
        ),
        limit=limit,
    )
    archive_window_queue, archive_window_count, archive_window_summary = _queue_payload(
        rows,
        predicate=lambda row: _archive_blocker_count(row, "no_rows_in_requested_window") > 0,
        sort_key=lambda row: (
            -_archive_blocker_count(row, "no_rows_in_requested_window"),
            -_row_int(row, "archive_coverage_blocked_descriptor_count"),
            _row_int(row, "archive_coverage_requested_window_row_count"),
            str(row.get("iteration_id") or ""),
        ),
        limit=limit,
    )
    venue_expansion_queue, venue_expansion_count, venue_expansion_summary = _queue_payload(
        rows,
        predicate=lambda row: _venue_expansion_actionable_gap_count(row) > 0,
        sort_key=lambda row: (
            -_venue_expansion_actionable_gap_count(row),
            -_row_int(row, "venue_expansion_missing_target_count"),
            -_row_int(row, "venue_expansion_blocked_target_count"),
            str(row.get("iteration_id") or ""),
        ),
        limit=limit,
    )
    strategy_source_queue, strategy_source_count, strategy_source_summary = _queue_payload(
        rows,
        predicate=lambda row: _strategy_source_repair_count(row) > 0,
        sort_key=lambda row: (
            -_strategy_source_repair_count(row),
            -len(_strategy_source_repair_reason_codes(row)),
            str(row.get("iteration_id") or ""),
        ),
        limit=limit,
    )
    missing_brief_queue, missing_brief_count, missing_brief_summary = _queue_payload(
        rows,
        predicate=lambda row: row.get("brief_status") != "present",
        sort_key=lambda row: (
            str(row.get("brief_status") or "missing"),
            str(row.get("iteration_id") or ""),
        ),
        limit=limit,
    )
    artifact_repair_queue, artifact_repair_count, artifact_repair_summary = _queue_payload(
        rows,
        predicate=lambda row: _row_int(row, "artifact_missing_count") > 0,
        sort_key=lambda row: (
            -_row_int(row, "artifact_missing_count"),
            str(row.get("artifact_availability_status") or ""),
            str(row.get("iteration_id") or ""),
        ),
        limit=limit,
    )
    rejection_queue, rejection_count, rejection_summary = _queue_payload(
        rows,
        predicate=lambda row: row.get("next_action") in {
            "review_rejections_and_falsified_hypotheses",
            "review_screened_results_and_request_thresholds",
            "inspect_blocked_or_empty_sandbox_iteration",
        }
        or (
            _validation_request_count(row) <= 0
            and (_row_int(row, "rejected_count") > 0 or _row_int(row, "blocked_count") > 0)
        ),
        sort_key=lambda row: (
            -_row_int(row, "rejected_count"),
            -_row_int(row, "blocked_count"),
            -_row_int(row, "result_count"),
            str(row.get("iteration_id") or ""),
        ),
        limit=limit,
    )
    queues = {
        "strict_validation_request_queue": request_queue,
        "preflight_repair_queue": preflight_queue,
        "archive_window_repair_queue": archive_window_queue,
        "venue_expansion_gap_queue": venue_expansion_queue,
        "strategy_source_repair_queue": strategy_source_queue,
        "missing_brief_queue": missing_brief_queue,
        "artifact_repair_queue": artifact_repair_queue,
        "rejection_review_queue": rejection_queue,
    }
    counts = {
        "strict_validation_request_queue": request_count,
        "preflight_repair_queue": preflight_count,
        "archive_window_repair_queue": archive_window_count,
        "venue_expansion_gap_queue": venue_expansion_count,
        "strategy_source_repair_queue": strategy_source_count,
        "missing_brief_queue": missing_brief_count,
        "artifact_repair_queue": artifact_repair_count,
        "rejection_review_queue": rejection_count,
    }
    truncated_counts = {
        name: max(0, counts[name] - len(queues[name]))
        for name in queues
    }
    summaries = {
        "strict_validation_request_queue": request_summary,
        "preflight_repair_queue": preflight_summary,
        "archive_window_repair_queue": archive_window_summary,
        "venue_expansion_gap_queue": venue_expansion_summary,
        "strategy_source_repair_queue": strategy_source_summary,
        "missing_brief_queue": missing_brief_summary,
        "artifact_repair_queue": artifact_repair_summary,
        "rejection_review_queue": rejection_summary,
    }
    return queues, counts, truncated_counts, summaries


def build_sandbox_iteration_index(
    root_dir: str | Path,
    *,
    output_dir: str | Path | None = None,
    max_files: int = 5000,
    write_report: bool = True,
) -> dict[str, Any]:
    root_path = Path(root_dir)
    if not root_path.exists():
        raise FileNotFoundError(f"sandbox iteration index root not found: {root_path}")
    if not root_path.is_dir():
        raise ValueError(f"sandbox iteration index root must be a directory: {root_path}")
    root_path = root_path.resolve()
    manifest_paths = _discover_iteration_manifests(root_path, max_files=max_files)
    index_id = digest_payload(
        {
            "root_dir": str(root_path),
            "manifest_paths": [str(path.relative_to(root_path)) for path in manifest_paths],
            "max_files": int(max_files),
        },
        prefix="sbxiterationindex",
        length=24,
    )
    rows: list[dict[str, Any]] = []
    for manifest_path in manifest_paths:
        manifest = _load_json_object(manifest_path, payload_name="sandbox_iteration_index_manifest")
        brief, brief_status, brief_path = _load_brief(manifest, manifest_path=manifest_path)
        rows.append(
            _iteration_row(
                index_id=index_id,
                root_dir=root_path,
                manifest_path=manifest_path,
                manifest=manifest,
                brief=brief,
                brief_status=brief_status,
                brief_path=brief_path,
            )
        )

    status_counts: dict[str, int] = {}
    next_action_counts: dict[str, int] = {}
    brief_status_counts: dict[str, int] = {}
    artifact_availability_status_counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get("iteration_status") or "missing")
        next_action = str(row.get("next_action") or "unknown")
        brief_status = str(row.get("brief_status") or "missing")
        artifact_status = str(row.get("artifact_availability_status") or "missing")
        status_counts[status] = status_counts.get(status, 0) + 1
        next_action_counts[next_action] = next_action_counts.get(next_action, 0) + 1
        brief_status_counts[brief_status] = brief_status_counts.get(brief_status, 0) + 1
        artifact_availability_status_counts[artifact_status] = artifact_availability_status_counts.get(artifact_status, 0) + 1

    destination = Path(output_dir).resolve() if output_dir is not None else root_path
    json_path = destination / SANDBOX_ITERATION_INDEX_JSON_NAME
    parquet_path = destination / SANDBOX_ITERATION_INDEX_PARQUET_NAME
    action_plan_parquet_path = destination / SANDBOX_ITERATION_AGENT_ACTION_PLAN_PARQUET_NAME
    replay_worklist_json_path = destination / SANDBOX_ITERATION_INPUT_REPLAY_WORKLIST_JSON_NAME
    replay_worklist_parquet_path = destination / SANDBOX_ITERATION_INPUT_REPLAY_WORKLIST_PARQUET_NAME
    replay_batch_plan_json_path = destination / SANDBOX_ITERATION_INPUT_REPLAY_BATCH_PLAN_JSON_NAME
    replay_batch_plan_parquet_path = destination / SANDBOX_ITERATION_INPUT_REPLAY_BATCH_PLAN_PARQUET_NAME
    action_queues, action_queue_counts, action_queue_truncated_counts, action_queue_summaries = _build_action_queues(rows)
    agent_action_plan, agent_action_plan_count, agent_action_plan_truncated_count, agent_action_plan_summary = (
        _build_agent_action_plan(rows)
    )
    input_replay_worklist, input_replay_context_missing_count, input_replay_worklist_summary = (
        _build_input_replay_worklist(rows)
    )
    input_replay_batch_plan, input_replay_batch_plan_summary = _build_input_replay_batch_plan(
        input_replay_worklist
    )
    input_replay_worklist_payload = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_input_replay_worklist",
        "index_id": index_id,
        "root_dir": str(root_path),
        "output_dir": str(destination),
        "worklist_version": SANDBOX_ITERATION_INPUT_REPLAY_WORKLIST_VERSION,
        "item_count": len(input_replay_worklist),
        "missing_context_count": input_replay_context_missing_count,
        "truncated": len(rows) >= max_files,
        "summary": input_replay_worklist_summary,
        "items": input_replay_worklist,
    }
    require_sandbox_boundary(
        input_replay_worklist_payload,
        payload_name="sandbox_iteration_input_replay_worklist",
    )
    input_replay_batch_plan_payload = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_input_replay_batch_plan",
        "index_id": index_id,
        "root_dir": str(root_path),
        "output_dir": str(destination),
        "plan_version": SANDBOX_ITERATION_INPUT_REPLAY_BATCH_PLAN_VERSION,
        "descriptor_only": True,
        "replay_command_execution_authorized": False,
        "strict_validation_authorized": False,
        "candidate_pack_write_authorized": False,
        "item_count": len(input_replay_batch_plan),
        "descriptor_count": len(input_replay_batch_plan),
        "source_worklist_item_count": len(input_replay_worklist),
        "ready_source_item_count": int(input_replay_batch_plan_summary["ready_source_item_count"]),
        "blocked_source_item_count": int(input_replay_batch_plan_summary["blocked_source_item_count"]),
        "suppressed_duplicate_source_item_count": int(
            input_replay_batch_plan_summary["suppressed_duplicate_source_item_count"]
        ),
        "truncated": len(rows) >= max_files,
        "summary": input_replay_batch_plan_summary,
        "items": input_replay_batch_plan,
    }
    require_sandbox_boundary(
        input_replay_batch_plan_payload,
        payload_name="sandbox_iteration_input_replay_batch_plan",
    )
    payload = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_iteration_index",
        "index_id": index_id,
        "root_dir": str(root_path),
        "output_dir": str(destination),
        "iteration_count": len(rows),
        "iteration_status_counts": dict(sorted(status_counts.items())),
        "next_action_counts": dict(sorted(next_action_counts.items())),
        "recommended_action_counts": _recommended_action_counts(rows),
        "brief_status_counts": dict(sorted(brief_status_counts.items())),
        "artifact_availability_status_counts": dict(sorted(artifact_availability_status_counts.items())),
        "total_deduped_validation_request_count": sum(int(row.get("deduped_validation_request_count", 0) or 0) for row in rows),
        "total_preflight_blocked_trial_estimate": sum(int(row.get("preflight_blocked_trial_estimate", 0) or 0) for row in rows),
        "total_strategy_skipped_source_count": sum(int(row.get("strategy_skipped_source_count", 0) or 0) for row in rows),
        "total_strategy_workbook_source_count": sum(
            int(row.get("strategy_workbook_source_count", 0) or 0) for row in rows
        ),
        "total_strategy_workbook_sheet_count": sum(int(row.get("strategy_workbook_sheet_count", 0) or 0) for row in rows),
        "total_strategy_workbook_skipped_sheet_count": sum(
            int(row.get("strategy_workbook_skipped_sheet_count", 0) or 0) for row in rows
        ),
        "total_archive_skipped_count": sum(int(row.get("archive_skipped_count", 0) or 0) for row in rows),
        "total_artifact_reference_count": sum(int(row.get("artifact_reference_count", 0) or 0) for row in rows),
        "total_artifact_present_count": sum(int(row.get("artifact_present_count", 0) or 0) for row in rows),
        "total_artifact_missing_count": sum(int(row.get("artifact_missing_count", 0) or 0) for row in rows),
        "total_archive_coverage_requested_window_row_count": sum(
            int(row.get("archive_coverage_requested_window_row_count", 0) or 0)
            for row in rows
        ),
        "total_venue_expansion_gap_row_count": sum(
            int(row.get("venue_expansion_gap_row_count", 0) or 0) for row in rows
        ),
        "total_venue_expansion_actionable_gap_count": sum(
            _venue_expansion_actionable_gap_count(row) for row in rows
        ),
        "total_venue_expansion_missing_target_count": sum(
            int(row.get("venue_expansion_missing_target_count", 0) or 0) for row in rows
        ),
        "total_venue_expansion_blocked_target_count": sum(
            int(row.get("venue_expansion_blocked_target_count", 0) or 0) for row in rows
        ),
        "total_venue_expansion_mixed_target_count": sum(
            int(row.get("venue_expansion_mixed_target_count", 0) or 0) for row in rows
        ),
        "action_queue_version": SANDBOX_ITERATION_ACTION_QUEUE_VERSION,
        "action_queue_limit": SANDBOX_ITERATION_ACTION_QUEUE_LIMIT,
        "action_queue_counts": action_queue_counts,
        "action_queue_truncated_counts": action_queue_truncated_counts,
        "action_queue_summaries": action_queue_summaries,
        "action_queues": action_queues,
        "agent_action_plan_version": SANDBOX_ITERATION_AGENT_ACTION_PLAN_VERSION,
        "agent_action_plan_limit": SANDBOX_ITERATION_AGENT_ACTION_PLAN_LIMIT,
        "agent_action_plan_count": agent_action_plan_count,
        "agent_action_plan_truncated_count": agent_action_plan_truncated_count,
        "agent_action_plan_summary": agent_action_plan_summary,
        "agent_action_plan": agent_action_plan,
        "agent_action_plan_parquet_path": str(action_plan_parquet_path) if write_report else None,
        "input_replay_worklist_version": SANDBOX_ITERATION_INPUT_REPLAY_WORKLIST_VERSION,
        "input_replay_worklist_count": len(input_replay_worklist),
        "input_replay_context_missing_count": input_replay_context_missing_count,
        "input_replay_worklist_summary": input_replay_worklist_summary,
        "input_replay_worklist": input_replay_worklist,
        "input_replay_worklist_json_path": str(replay_worklist_json_path) if write_report else None,
        "input_replay_worklist_parquet_path": str(replay_worklist_parquet_path) if write_report else None,
        "input_replay_batch_plan_version": SANDBOX_ITERATION_INPUT_REPLAY_BATCH_PLAN_VERSION,
        "input_replay_batch_plan_count": len(input_replay_batch_plan),
        "input_replay_batch_plan_summary": input_replay_batch_plan_summary,
        "input_replay_batch_plan": input_replay_batch_plan,
        "input_replay_batch_plan_json_path": str(replay_batch_plan_json_path) if write_report else None,
        "input_replay_batch_plan_parquet_path": str(replay_batch_plan_parquet_path) if write_report else None,
        "max_files": int(max_files),
        "truncated": len(rows) >= max_files,
        "iteration_index_json_path": str(json_path) if write_report else None,
        "iteration_index_parquet_path": str(parquet_path) if write_report else None,
        "rows": rows,
    }
    require_sandbox_boundary(payload, payload_name="sandbox_iteration_index")
    if write_report:
        destination.mkdir(parents=True, exist_ok=True)
        frame = pd.DataFrame([_row_for_parquet(row) for row in rows])
        if frame.empty:
            frame = pd.DataFrame(columns=["index_id", "iteration_id", "iteration_status", *SANDBOX_BOUNDARY_FLAGS])
        frame.to_parquet(parquet_path, index=False)
        action_plan_frame = pd.DataFrame([_row_for_parquet(item) for item in agent_action_plan])
        if action_plan_frame.empty:
            action_plan_frame = pd.DataFrame(
                columns=[
                    "iteration_id",
                    "action",
                    "action_priority",
                    "blocked_by_prior_action",
                    *SANDBOX_BOUNDARY_FLAGS,
                ]
            )
        action_plan_frame.to_parquet(action_plan_parquet_path, index=False)
        replay_worklist_frame = pd.DataFrame([_row_for_parquet(item) for item in input_replay_worklist])
        if replay_worklist_frame.empty:
            replay_worklist_frame = pd.DataFrame(
                columns=[
                    "iteration_id",
                    "input_replay_context_id",
                    "input_replay_command",
                    "input_replay_ready",
                    *SANDBOX_BOUNDARY_FLAGS,
                ]
            )
        replay_worklist_frame.to_parquet(replay_worklist_parquet_path, index=False)
        replay_batch_plan_frame = pd.DataFrame([_row_for_parquet(item) for item in input_replay_batch_plan])
        if replay_batch_plan_frame.empty:
            replay_batch_plan_frame = pd.DataFrame(
                columns=[
                    "input_replay_context_id",
                    "input_replay_duplicate_group_key",
                    "input_replay_command",
                    "input_replay_ready",
                    *SANDBOX_BOUNDARY_FLAGS,
                ]
            )
        replay_batch_plan_frame.to_parquet(replay_batch_plan_parquet_path, index=False)
        replay_worklist_json_path.write_text(
            json.dumps(input_replay_worklist_payload, indent=2, sort_keys=True, default=_json_default),
            encoding="utf-8",
        )
        replay_batch_plan_json_path.write_text(
            json.dumps(input_replay_batch_plan_payload, indent=2, sort_keys=True, default=_json_default),
            encoding="utf-8",
        )
        json_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=_json_default),
            encoding="utf-8",
        )
    return payload
