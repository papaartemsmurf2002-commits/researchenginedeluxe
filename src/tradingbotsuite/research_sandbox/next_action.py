from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from tradingbotsuite.research_sandbox.boundary import (
    SANDBOX_BOUNDARY_FLAGS,
    require_sandbox_boundary,
    sandbox_boundary_metadata,
)
from tradingbotsuite.research_sandbox.catalog import SANDBOX_ARTIFACT_CATALOG_JSON_NAME
from tradingbotsuite.research_sandbox.discovery import bounded_discover_files
from tradingbotsuite.research_sandbox.identity import digest_payload
from tradingbotsuite.research_sandbox.iteration_index import SANDBOX_ITERATION_INDEX_JSON_NAME


SANDBOX_NEXT_ACTION_REPORT_JSON_NAME = "sandbox_next_action_report.json"
SANDBOX_NEXT_ACTION_REPORT_PARQUET_NAME = "sandbox_next_action_report.parquet"
SANDBOX_NEXT_ACTION_REPORT_SCHEMA_VERSION = "sandbox_next_action_report_v1"

_CATALOG_NAMES = {SANDBOX_ARTIFACT_CATALOG_JSON_NAME}
_ITERATION_INDEX_NAMES = {SANDBOX_ITERATION_INDEX_JSON_NAME}
_ITERATION_MANIFEST_NAMES = {"sandbox_iteration_manifest.json"}
_QUEUE_ORDER = (
    "strategy_source_repair_queue",
    "preflight_repair_queue",
    "archive_window_repair_queue",
    "artifact_repair_queue",
    "strict_validation_request_queue",
    "venue_expansion_gap_queue",
    "rejection_review_queue",
    "missing_brief_queue",
)
_ACTION_BY_QUEUE = {
    "strategy_source_repair_queue": "repair_strategy_catalog_sources",
    "preflight_repair_queue": "repair_preflight_blockers",
    "archive_window_repair_queue": "repair_archive_manifest_or_requested_window",
    "artifact_repair_queue": "restore_or_rerun_missing_iteration_artifacts",
    "strict_validation_request_queue": "review_descriptor_only_strict_validation_requests",
    "venue_expansion_gap_queue": "repair_or_add_venue_expansion_archives",
    "rejection_review_queue": "review_rejections_and_falsified_hypotheses",
    "missing_brief_queue": "restore_or_regenerate_iteration_agent_brief",
}
_PACKET_BY_ACTION = {
    "restore_or_regenerate_iteration_agent_brief": "iteration_agent_brief_repair_packet",
    "restore_or_rerun_missing_iteration_artifacts": "artifact_integrity_repair_packet",
    "adjust_iteration_window_or_refresh_archive_manifest": "archive_window_repair_packet",
    "repair_archive_manifest_or_requested_window": "archive_window_repair_packet",
    "refresh_archive_source_integrity_metadata_or_restore_source_file": "archive_integrity_repair_packet",
    "repair_strategy_catalog_sources": "strategy_catalog_repair_packet",
    "repair_strategy_catalog_signal_columns_or_materialize_blueprints": "strategy_catalog_repair_packet",
    "add_required_ohlc_columns_or_use_fixed_hold_exit": "strategy_or_exit_descriptor_repair_packet",
    "repair_preflight_blockers": "preflight_repair_packet",
    "review_descriptor_only_strict_validation_requests": "strict_validation_descriptor_preflight_packet",
    "repair_or_add_venue_expansion_archives": "venue_expansion_materializer_packet",
    "review_rejections_and_falsified_hypotheses": "hypothesis_rejection_review_packet",
    "review_screened_results_and_request_thresholds": "hypothesis_threshold_review_packet",
    "inspect_blocked_or_empty_sandbox_iteration": "blocked_iteration_triage_packet",
    "index_rapid_strategy_sandbox_iterations": "sandbox_iteration_index_packet",
}


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _load_json_object(path: Path, *, payload_name: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{payload_name} must be a JSON object")
    require_sandbox_boundary(payload, payload_name=payload_name)
    return payload


def _row_for_parquet(payload: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, (dict, list, tuple)):
            row[key] = json.dumps(value, sort_keys=True, default=_json_default)
        else:
            row[key] = value
    return row


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _resolve_under_root(root: Path, path: str | Path, *, field_name: str) -> Path:
    root_path = root.expanduser().resolve()
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = root_path / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root_path)
    except ValueError as exc:
        raise ValueError(f"{field_name} must stay under sandbox next-action output root") from exc
    return resolved


def _discover_named_json(root: Path, names: set[str], *, max_files: int) -> list[Path]:
    matches, _ = bounded_discover_files(
        [root],
        max_files=max_files,
        missing_root_message="sandbox next-action discovery root not found",
        accepted_names=names,
    )
    return sorted(matches, key=lambda item: item.as_posix())


def _source_paths(
    root: Path,
    explicit_paths: list[str | Path] | None,
    *,
    names: set[str],
    max_files: int,
    field_name: str,
) -> list[Path]:
    if explicit_paths:
        return [_resolve_under_root(root, path, field_name=field_name) for path in explicit_paths]
    return _discover_named_json(root, names, max_files=max_files)


def _combined_explicit_paths(
    plural: list[str | Path] | None,
    singular: str | Path | None,
) -> list[str | Path] | None:
    paths: list[str | Path] = []
    if plural:
        paths.extend(plural)
    if singular is not None:
        paths.append(singular)
    return paths or None


def _first_action(iteration_indexes: list[dict[str, Any]]) -> dict[str, Any] | None:
    for payload in iteration_indexes:
        for item in _as_list(payload.get("agent_action_plan")):
            if isinstance(item, dict) and not bool(item.get("blocked_by_prior_action", False)):
                return dict(item)
        for item in _as_list(payload.get("agent_action_plan")):
            if isinstance(item, dict):
                return dict(item)
    return None


def _fallback_action(
    iteration_indexes: list[dict[str, Any]],
    catalogs: list[dict[str, Any]],
    *,
    unindexed_iteration_manifest_paths: list[Path],
) -> dict[str, Any]:
    for queue_name in _QUEUE_ORDER:
        for payload in iteration_indexes:
            queue_counts = _as_dict(payload.get("action_queue_counts"))
            if _safe_int(queue_counts.get(queue_name)) <= 0:
                continue
            queue_items = _as_list(_as_dict(payload.get("action_queues")).get(queue_name))
            action = _ACTION_BY_QUEUE.get(queue_name, queue_name.replace("_queue", ""))
            if queue_items and isinstance(queue_items[0], dict):
                action = str(queue_items[0].get("recommended_action") or queue_items[0].get("next_action") or action)
            return {"action": action, "source_queues": [queue_name], "reason_codes": [queue_name]}
    for catalog in catalogs:
        if _safe_int(catalog.get("strict_validation_descriptor_queue_count")) > 0:
            return {
                "action": "review_descriptor_only_strict_validation_requests",
                "source_queues": ["strict_validation_descriptor_queue"],
                "reason_codes": ["strict_validation_descriptor_queue"],
            }
    if unindexed_iteration_manifest_paths:
        return {
            "action": "index_rapid_strategy_sandbox_iterations",
            "source_queues": ["unindexed_iteration_manifest"],
            "reason_codes": ["unindexed_iteration_manifests_found"],
            "unindexed_iteration_manifest_count": len(unindexed_iteration_manifest_paths),
            "iteration_manifest_path": str(unindexed_iteration_manifest_paths[0]),
        }
    return {
        "action": "run_or_index_rapid_strategy_sandbox_iteration",
        "source_queues": [],
        "reason_codes": ["no_existing_action_queue_rows"],
    }


def _status_counts(iteration_indexes: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts: Counter[str] = Counter()
    next_action_counts: Counter[str] = Counter()
    queue_counts: Counter[str] = Counter()
    for payload in iteration_indexes:
        status_counts.update({str(key): _safe_int(value) for key, value in _as_dict(payload.get("iteration_status_counts")).items()})
        next_action_counts.update({str(key): _safe_int(value) for key, value in _as_dict(payload.get("next_action_counts")).items()})
        queue_counts.update({str(key): _safe_int(value) for key, value in _as_dict(payload.get("action_queue_counts")).items()})
    return {
        "iteration_index_count": len(iteration_indexes),
        "iteration_count": sum(_safe_int(payload.get("iteration_count")) for payload in iteration_indexes),
        "iteration_status_counts": dict(sorted(status_counts.items())),
        "next_action_counts": dict(sorted(next_action_counts.items())),
        "action_queue_counts": dict(sorted(queue_counts.items())),
    }


def _top_blockers(iteration_indexes: list[dict[str, Any]], catalogs: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for payload in iteration_indexes:
        for queue_name, summary in _as_dict(payload.get("action_queue_summaries")).items():
            summary_map = _as_dict(summary)
            for key in (
                "preflight_blocker_reason_counts",
                "archive_coverage_blocker_reason_counts",
                "strategy_source_skip_reason_counts",
                "archive_file_skip_reason_counts",
            ):
                for reason, count in _as_dict(summary_map.get(key)).items():
                    blockers.append(
                        {
                            **sandbox_boundary_metadata(),
                            "artifact_family": "rapid_strategy_iteration_sandbox_next_action_blocker",
                            "source_queue": queue_name,
                            "reason": str(reason),
                            "count": _safe_int(count),
                        }
                    )
    for catalog in catalogs:
        for row in _as_list(catalog.get("artifacts")):
            if not isinstance(row, dict):
                continue
            status = str(row.get("integrity_verification_status") or "not_applicable")
            failed_count = _safe_int(row.get("integrity_failed_artifact_count"))
            if status in {"failed", "verification_error"} or failed_count > 0:
                blockers.append(
                    {
                        **sandbox_boundary_metadata(),
                        "artifact_family": "rapid_strategy_iteration_sandbox_next_action_blocker",
                        "source_queue": "artifact_integrity",
                        "reason": f"artifact_integrity:{status}",
                        "count": max(1, failed_count),
                        "artifact_path": row.get("artifact_path"),
                        "integrity_failure_reasons": _as_list(row.get("integrity_failure_reasons")),
                    }
                )
    for item in blockers:
        require_sandbox_boundary(item, payload_name="sandbox_next_action_blocker")
    return sorted(blockers, key=lambda item: (-_safe_int(item.get("count")), str(item.get("reason"))))[:limit]


def _strict_validation_items(iteration_indexes: list[dict[str, Any]], catalogs: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for payload in iteration_indexes:
        queue = _as_list(_as_dict(payload.get("action_queues")).get("strict_validation_request_queue"))
        for item in queue:
            if isinstance(item, dict):
                items.append(dict(item))
        for plan_item in _as_list(payload.get("agent_action_plan")):
            if isinstance(plan_item, dict) and str(plan_item.get("action")) == "review_descriptor_only_strict_validation_requests":
                items.append(dict(plan_item))
    for catalog in catalogs:
        for item in _as_list(catalog.get("strict_validation_descriptor_queue")):
            if isinstance(item, dict):
                items.append(dict(item))
        for item in _as_list(catalog.get("global_evidence_request_priority_queue")):
            if isinstance(item, dict):
                items.append(dict(item))
    return items[:limit]


def _venue_expansion_items(iteration_indexes: list[dict[str, Any]], catalogs: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for payload in iteration_indexes:
        queue = _as_list(_as_dict(payload.get("action_queues")).get("venue_expansion_gap_queue"))
        for item in queue:
            if isinstance(item, dict):
                items.append(dict(item))
    for catalog in catalogs:
        summary = _as_dict(catalog.get("iteration_venue_expansion_gap_worklist_summary"))
        if _safe_int(summary.get("worklist_row_count")) > 0:
            items.append(
                {
                    **sandbox_boundary_metadata(),
                    "artifact_family": "rapid_strategy_iteration_sandbox_next_action_venue_expansion_pointer",
                    "summary": summary,
                    "worklist_parquet_path": catalog.get("iteration_venue_expansion_gap_worklist_parquet_path"),
                    "worklist_row_count": catalog.get("iteration_venue_expansion_gap_worklist_parquet_row_count"),
                    "descriptor_only": True,
                    "strict_validation_executed": False,
                    "candidate_pack_written": False,
                }
            )
    for item in items:
        if isinstance(item, dict):
            require_sandbox_boundary(item, payload_name="sandbox_next_action_venue_expansion_item")
    return items[:limit]


def _artifact_warnings(iteration_indexes: list[dict[str, Any]], catalogs: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    for payload in iteration_indexes:
        for row in _as_list(payload.get("rows")):
            if not isinstance(row, dict):
                continue
            missing_count = _safe_int(row.get("artifact_missing_count"))
            if missing_count > 0 or str(row.get("artifact_availability_status") or "") not in {"", "all_present"}:
                warnings.append(
                    {
                        **sandbox_boundary_metadata(),
                        "artifact_family": "rapid_strategy_iteration_sandbox_next_action_artifact_warning",
                        "warning_type": "iteration_artifact_availability",
                        "iteration_id": row.get("iteration_id"),
                        "artifact_availability_status": row.get("artifact_availability_status"),
                        "artifact_missing_count": missing_count,
                        "artifact_missing_keys": _as_list(row.get("artifact_missing_keys")),
                    }
                )
    for catalog in catalogs:
        for row in _as_list(catalog.get("artifacts")):
            if not isinstance(row, dict):
                continue
            status = str(row.get("integrity_verification_status") or "not_applicable")
            failed_count = _safe_int(row.get("integrity_failed_artifact_count"))
            if status in {"failed", "verification_error"} or failed_count > 0:
                warnings.append(
                    {
                        **sandbox_boundary_metadata(),
                        "artifact_family": "rapid_strategy_iteration_sandbox_next_action_artifact_warning",
                        "warning_type": "catalog_integrity",
                        "artifact_kind": row.get("artifact_kind"),
                        "artifact_path": row.get("artifact_path"),
                        "integrity_verification_status": status,
                        "integrity_failed_artifact_count": failed_count,
                        "integrity_failure_reasons": _as_list(row.get("integrity_failure_reasons")),
                    }
                )
    for item in warnings:
        require_sandbox_boundary(item, payload_name="sandbox_next_action_artifact_warning")
    return warnings[:limit]


def _best_hypothesis_pointers(catalogs: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    pointers: list[dict[str, Any]] = []
    for catalog in catalogs:
        for key, count_key in (
            ("global_top_hypotheses_parquet_path", "global_top_hypothesis_parquet_row_count"),
            ("global_bucket_top_buckets_parquet_path", "global_bucket_top_bucket_parquet_row_count"),
        ):
            path = catalog.get(key)
            count = _safe_int(catalog.get(count_key))
            if path and count > 0:
                pointers.append(
                    {
                        **sandbox_boundary_metadata(),
                        "artifact_family": "rapid_strategy_iteration_sandbox_next_action_best_hypothesis_pointer",
                        "sidecar_kind": key.replace("_parquet_path", ""),
                        "sidecar_path": path,
                        "row_count": count,
                    }
                )
    for item in pointers:
        require_sandbox_boundary(item, payload_name="sandbox_next_action_best_hypothesis_pointer")
    return pointers[:limit]


def _target_venue_counts(catalogs: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for catalog in catalogs:
        counts.update(
            {
                str(key): _safe_int(value)
                for key, value in _as_dict(
                    catalog.get("iteration_venue_expansion_gap_worklist_target_venue_counts")
                ).items()
            }
        )
    return dict(sorted(counts.items()))


def _exact_files_to_open(
    *,
    catalog_paths: list[Path],
    iteration_index_paths: list[Path],
    unindexed_iteration_manifest_paths: list[Path],
    iteration_indexes: list[dict[str, Any]],
    catalogs: list[dict[str, Any]],
    next_action: dict[str, Any],
    limit: int,
) -> list[str]:
    files: list[str] = []

    def add(value: Any) -> None:
        if value in (None, ""):
            return
        text = str(value)
        if text not in files:
            files.append(text)

    for path in catalog_paths:
        add(path)
    for path in iteration_index_paths:
        add(path)
    for path in unindexed_iteration_manifest_paths:
        add(path)
    for key in (
        "iteration_manifest_path",
        "agent_brief_json_path",
        "preflight_json_path",
        "archive_coverage_json_path",
        "strict_validation_request_bundle_json_path",
        "strategy_catalog_json_path",
        "strategy_build_report_json_path",
        "venue_archive_manifest_path",
        "archive_build_report_json_path",
    ):
        add(next_action.get(key))
    for catalog in catalogs:
        for key in (
            "catalog_sidecar_index_parquet_path",
            "iteration_agent_action_plan_parquet_path",
            "iteration_venue_expansion_gap_worklist_parquet_path",
            "strict_validation_descriptor_queue_parquet_path",
            "global_evidence_request_priority_queue_parquet_path",
            "global_evidence_request_source_priority_queue_parquet_path",
            "global_top_hypotheses_parquet_path",
        ):
            add(catalog.get(key))
    for payload in iteration_indexes:
        add(payload.get("agent_action_plan_parquet_path"))
    return files[:limit]


def _report_row(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_next_action_report_row",
        "report_id": payload["report_id"],
        "recommended_action": payload["recommended_action"],
        "next_recommended_packet_type": payload["next_recommended_packet_type"],
        "iteration_count": payload["current_iteration_status"]["iteration_count"],
        "artifact_catalog_count": payload["artifact_catalog_count"],
        "iteration_index_count": payload["iteration_index_count"],
        "unindexed_iteration_manifest_count": payload["unindexed_iteration_manifest_count"],
        "strict_validation_item_count": len(payload["highest_priority_strict_validation_descriptors"]),
        "venue_expansion_item_count": len(payload["highest_priority_venue_expansion_requests"]),
        "top_blocker_count": len(payload["top_blockers"]),
        "artifact_warning_count": len(payload["stale_or_tampered_artifact_warnings"]),
        "descriptor_only": True,
        "dashboard_only": True,
        "summarizes_existing_artifacts_only": True,
        "evidence_recomputed": False,
        "sandbox_sweep_executed": False,
        "artifact_indexer_executed": False,
        "strict_validation_executed": False,
        "strict_validation_authorized": False,
        "candidate_pack_written": False,
        "candidate_pack_write_authorized": False,
    }


def show_sandbox_next_action(
    output_root: str | Path,
    *,
    artifact_catalog_path: str | Path | None = None,
    artifact_catalog_paths: list[str | Path] | None = None,
    iteration_index_path: str | Path | None = None,
    iteration_index_paths: list[str | Path] | None = None,
    output_dir: str | Path | None = None,
    max_files: int = 5000,
    limit: int = 10,
    write_report: bool = True,
) -> dict[str, Any]:
    if max_files <= 0:
        raise ValueError("sandbox next-action max_files must be positive")
    if limit <= 0:
        raise ValueError("sandbox next-action limit must be positive")
    root_path = Path(output_root).expanduser().resolve()
    if root_path.exists() and not root_path.is_dir():
        raise ValueError(f"sandbox next-action output root must be a directory: {root_path}")
    if not root_path.exists() and write_report:
        root_path.mkdir(parents=True, exist_ok=True)
    catalog_paths = _source_paths(
        root_path,
        _combined_explicit_paths(artifact_catalog_paths, artifact_catalog_path),
        names=_CATALOG_NAMES,
        max_files=max_files,
        field_name="artifact_catalog",
    )
    index_paths = _source_paths(
        root_path,
        _combined_explicit_paths(iteration_index_paths, iteration_index_path),
        names=_ITERATION_INDEX_NAMES,
        max_files=max_files,
        field_name="iteration_index",
    )
    unindexed_iteration_manifest_paths = (
        _discover_named_json(root_path, _ITERATION_MANIFEST_NAMES, max_files=max_files)
        if not catalog_paths and not index_paths
        else []
    )
    catalogs = [
        _load_json_object(path, payload_name="sandbox_next_action_artifact_catalog")
        for path in catalog_paths
    ]
    iteration_indexes = [
        _load_json_object(path, payload_name="sandbox_next_action_iteration_index")
        for path in index_paths
    ]
    chosen_action = _first_action(iteration_indexes) or _fallback_action(
        iteration_indexes,
        catalogs,
        unindexed_iteration_manifest_paths=unindexed_iteration_manifest_paths,
    )
    recommended_action = str(chosen_action.get("action") or chosen_action.get("recommended_action") or "inspect_sandbox_artifacts")
    next_packet = _PACKET_BY_ACTION.get(recommended_action, "sandbox_next_action_followup_packet")
    status = _status_counts(iteration_indexes)
    top_blockers = _top_blockers(iteration_indexes, catalogs, limit=limit)
    strict_items = _strict_validation_items(iteration_indexes, catalogs, limit=limit)
    venue_items = _venue_expansion_items(iteration_indexes, catalogs, limit=limit)
    warnings = _artifact_warnings(iteration_indexes, catalogs, limit=limit)
    best_hypotheses = _best_hypothesis_pointers(catalogs, limit=limit)
    exact_files = _exact_files_to_open(
        catalog_paths=catalog_paths,
        iteration_index_paths=index_paths,
        unindexed_iteration_manifest_paths=unindexed_iteration_manifest_paths,
        iteration_indexes=iteration_indexes,
        catalogs=catalogs,
        next_action=chosen_action,
        limit=limit * 3,
    )
    report_id = digest_payload(
        {
            "schema_version": SANDBOX_NEXT_ACTION_REPORT_SCHEMA_VERSION,
            "catalog_paths": [str(path.relative_to(root_path)) for path in catalog_paths],
            "iteration_index_paths": [str(path.relative_to(root_path)) for path in index_paths],
            "recommended_action": recommended_action,
            "source_counts": {
                "artifact_catalog_count": len(catalogs),
                "iteration_index_count": len(iteration_indexes),
                "unindexed_iteration_manifest_count": len(unindexed_iteration_manifest_paths),
                "iteration_count": status["iteration_count"],
            },
        },
        prefix="sbxnextaction",
        length=24,
    )
    destination = (
        _resolve_under_root(root_path, output_dir, field_name="output_dir")
        if output_dir is not None
        else root_path / "rapid_strategy_sandbox_next_action" / report_id
    )
    json_path = destination / SANDBOX_NEXT_ACTION_REPORT_JSON_NAME
    parquet_path = destination / SANDBOX_NEXT_ACTION_REPORT_PARQUET_NAME
    payload = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_next_action_report",
        "schema_version": SANDBOX_NEXT_ACTION_REPORT_SCHEMA_VERSION,
        "report_id": report_id,
        "output_root": str(root_path),
        "artifact_catalog_count": len(catalogs),
        "iteration_index_count": len(iteration_indexes),
        "unindexed_iteration_manifest_count": len(unindexed_iteration_manifest_paths),
        "artifact_catalog_paths": [str(path) for path in catalog_paths],
        "iteration_index_paths": [str(path) for path in index_paths],
        "unindexed_iteration_manifest_paths": [
            str(path)
            for path in unindexed_iteration_manifest_paths[:limit]
        ],
        "unindexed_iteration_manifest_paths_truncated": len(unindexed_iteration_manifest_paths) > limit,
        "current_iteration_status": status,
        "top_blockers": top_blockers,
        "missing_venue_coverage": {
            "total_actionable_gap_count": sum(
                _safe_int(payload.get("total_venue_expansion_actionable_gap_count"))
                for payload in iteration_indexes
            ),
            "target_venue_counts": _target_venue_counts(catalogs),
            "items": venue_items,
        },
        "highest_priority_strict_validation_descriptors": strict_items,
        "highest_priority_venue_expansion_requests": venue_items,
        "stale_or_tampered_artifact_warnings": warnings,
        "best_hypotheses_by_source_bucket": best_hypotheses,
        "recommended_action": recommended_action,
        "next_recommended_packet_type": next_packet,
        "recommended_action_source": chosen_action,
        "exact_files_to_open_next": exact_files,
        "descriptor_only": True,
        "dashboard_only": True,
        "read_only_summary": True,
        "summarizes_existing_artifacts_only": True,
        "evidence_recomputed": False,
        "sandbox_sweep_executed": False,
        "artifact_index_recomputed": False,
        "artifact_indexer_executed": False,
        "strict_validation_executed": False,
        "strict_validation_authorized": False,
        "candidate_pack_written": False,
        "candidate_pack_write_authorized": False,
        "candidate_pack_paths": [],
        "report_json_path": str(json_path) if write_report else None,
        "report_parquet_path": str(parquet_path) if write_report else None,
    }
    require_sandbox_boundary(payload, payload_name="sandbox_next_action_report")
    row = _report_row(payload)
    require_sandbox_boundary(row, payload_name="sandbox_next_action_report_row")
    if write_report:
        destination.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=_json_default),
            encoding="utf-8",
        )
        pd.DataFrame([_row_for_parquet(row)]).to_parquet(parquet_path, index=False)
    return payload
