from __future__ import annotations

from collections import Counter
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


SANDBOX_THROUGHPUT_REPORT_JSON_NAME = "sandbox_throughput_report.json"
SANDBOX_THROUGHPUT_ITERATION_SUMMARY_PARQUET_NAME = "sandbox_throughput_iteration_summary.parquet"
SANDBOX_THROUGHPUT_STAGE_SUMMARY_PARQUET_NAME = "sandbox_throughput_stage_summary.parquet"
SANDBOX_THROUGHPUT_REPORT_SCHEMA_VERSION = "sandbox_throughput_report_v1"


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


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _resolve_under_root(root: Path, path: str | Path, *, field_name: str) -> Path:
    root_path = root.expanduser().resolve()
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = root_path / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root_path)
    except ValueError as exc:
        raise ValueError(f"{field_name} must stay under sandbox throughput root") from exc
    return resolved


def _load_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"sandbox iteration manifest must be a JSON object: {path}")
    require_sandbox_boundary(payload, payload_name="sandbox_throughput_iteration_manifest")
    return payload


def _discover_iteration_manifests(root: Path, *, max_files: int) -> list[Path]:
    manifests: list[Path] = []
    scanned = 0
    if not root.exists():
        return manifests
    for path in root.rglob("*.json"):
        scanned += 1
        if scanned > max_files:
            break
        if path.name == SANDBOX_ITERATION_MANIFEST_JSON_NAME:
            manifests.append(path.resolve())
    return sorted(manifests, key=lambda item: item.as_posix())


def _collect_artifact_path_values(value: Any, *, key: str = "") -> list[Any]:
    values: list[Any] = []
    if isinstance(value, dict):
        for raw_key, child in value.items():
            child_key = str(raw_key)
            if child_key.endswith("_path") and child not in (None, ""):
                values.append(child)
            elif child_key.endswith("_paths"):
                values.extend(_as_list(child))
            values.extend(_collect_artifact_path_values(child, key=child_key))
    elif isinstance(value, list):
        for item in value:
            values.extend(_collect_artifact_path_values(item, key=key))
    return values


def _artifact_size_summary(payload: dict[str, Any], *, root: Path, manifest_path: Path) -> dict[str, Any]:
    path_values = _collect_artifact_path_values(payload)
    seen: set[str] = set()
    total_bytes = 0
    present_count = 0
    missing_count = 0
    outside_root_count = 0
    for raw_path in path_values:
        if raw_path in (None, ""):
            continue
        candidate = Path(str(raw_path)).expanduser()
        if not candidate.is_absolute():
            candidate = manifest_path.parent / candidate
        resolved = candidate.resolve()
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        try:
            resolved.relative_to(root)
        except ValueError:
            outside_root_count += 1
            continue
        if resolved.exists() and resolved.is_file():
            present_count += 1
            total_bytes += int(resolved.stat().st_size)
        else:
            missing_count += 1
    return {
        "artifact_reference_count": len(seen),
        "artifact_present_count": present_count,
        "artifact_missing_count": missing_count,
        "artifact_outside_root_count": outside_root_count,
        "artifact_bytes_written_estimate": total_bytes,
    }


def _cache_stats(telemetry: dict[str, Any]) -> dict[str, Any]:
    return _as_dict(telemetry.get("market_data_cache_stats"))


def _iteration_row(payload: dict[str, Any], *, manifest_path: Path, root: Path) -> dict[str, Any]:
    telemetry = _as_dict(payload.get("throughput_telemetry"))
    cache_stats = _cache_stats(telemetry)
    artifact_sizes = _artifact_size_summary(payload, root=root, manifest_path=manifest_path)
    telemetry_present = bool(telemetry)
    row = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_throughput_iteration_summary",
        "schema_version": SANDBOX_THROUGHPUT_REPORT_SCHEMA_VERSION,
        "iteration_id": payload.get("iteration_id"),
        "run_id": _as_dict(payload.get("spec")).get("run_id"),
        "iteration_status": payload.get("iteration_status"),
        "iteration_manifest_path": str(manifest_path),
        "iteration_manifest_path_relative": str(manifest_path.relative_to(root)),
        "telemetry_status": "present" if telemetry_present else "missing_telemetry",
        "total_runtime_seconds": _safe_float(telemetry.get("total_runtime_seconds")),
        "stage_count": _safe_int(telemetry.get("stage_count")),
        "peak_traced_memory_bytes": telemetry.get("peak_traced_memory_bytes"),
        "memory_telemetry_available": bool(telemetry.get("memory_telemetry_available", False)),
        "workers_requested": _safe_int(telemetry.get("workers_requested") or 1),
        "workers_used": _safe_int(telemetry.get("workers_used") or 1),
        "preflight_trial_estimate": _safe_int(payload.get("preflight_trial_estimate")),
        "preflight_runnable_trial_estimate": _safe_int(payload.get("preflight_runnable_trial_estimate")),
        "preflight_blocked_trial_estimate": _safe_int(payload.get("preflight_blocked_trial_estimate")),
        "result_count": _safe_int(payload.get("result_count")),
        "screened_count": _safe_int(payload.get("screened_count")),
        "rejected_count": _safe_int(payload.get("rejected_count")),
        "blocked_count": _safe_int(payload.get("blocked_count")),
        "evidence_request_count": _safe_int(payload.get("evidence_request_count")),
        "frame_cache_hit_count": _safe_int(cache_stats.get("frame_cache_hit_count")),
        "frame_cache_miss_count": _safe_int(cache_stats.get("frame_cache_miss_count")),
        "frame_cache_hit_rate": cache_stats.get("frame_cache_hit_rate"),
        "integrity_cache_hit_count": _safe_int(cache_stats.get("integrity_cache_hit_count")),
        "integrity_cache_miss_count": _safe_int(cache_stats.get("integrity_cache_miss_count")),
        "integrity_cache_hit_rate": cache_stats.get("integrity_cache_hit_rate"),
        "rows_loaded_after_2024_filter": _safe_int(cache_stats.get("rows_loaded_after_2024_filter")),
        "source_bytes_read": _safe_int(cache_stats.get("source_bytes_read")),
        **artifact_sizes,
        "benchmark_execution_mode": telemetry.get("benchmark_execution_mode") or "summarize_existing_iteration_manifest",
        "speedup_claimed": False,
        "strict_validation_executed": False,
        "strict_validation_authorized": False,
        "candidate_pack_written": False,
        "candidate_pack_write_authorized": False,
        "candidate_pack_paths": [],
    }
    require_sandbox_boundary(row, payload_name="sandbox_throughput_iteration_row")
    return row


def _stage_rows(payload: dict[str, Any], *, manifest_path: Path, root: Path) -> list[dict[str, Any]]:
    telemetry = _as_dict(payload.get("throughput_telemetry"))
    rows: list[dict[str, Any]] = []
    for rank, stage in enumerate(_as_list(telemetry.get("stage_timings")), start=1):
        if not isinstance(stage, dict):
            continue
        row = {
            **sandbox_boundary_metadata(),
            "artifact_family": "rapid_strategy_iteration_sandbox_throughput_stage_summary",
            "schema_version": SANDBOX_THROUGHPUT_REPORT_SCHEMA_VERSION,
            "iteration_id": payload.get("iteration_id"),
            "iteration_manifest_path": str(manifest_path),
            "iteration_manifest_path_relative": str(manifest_path.relative_to(root)),
            "stage_rank": rank,
            "stage_id": stage.get("stage_id"),
            "stage_status": stage.get("status"),
            "duration_seconds": _safe_float(stage.get("duration_seconds")),
            "counts": _as_dict(stage.get("counts")),
            "speedup_claimed": False,
            "strict_validation_executed": False,
            "strict_validation_authorized": False,
            "candidate_pack_written": False,
            "candidate_pack_write_authorized": False,
            "candidate_pack_paths": [],
        }
        require_sandbox_boundary(row, payload_name="sandbox_throughput_stage_row")
        rows.append(row)
    return rows


def _bottleneck_ranking(stage_rows: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    ranked = sorted(stage_rows, key=lambda row: (-_safe_float(row.get("duration_seconds")), str(row.get("stage_id"))))
    items: list[dict[str, Any]] = []
    for rank, row in enumerate(ranked[:limit], start=1):
        item = {
            **sandbox_boundary_metadata(),
            "artifact_family": "rapid_strategy_iteration_sandbox_throughput_bottleneck",
            "bottleneck_rank": rank,
            "iteration_id": row.get("iteration_id"),
            "stage_id": row.get("stage_id"),
            "duration_seconds": row.get("duration_seconds"),
            "stage_status": row.get("stage_status"),
            "speedup_claimed": False,
            "strict_validation_executed": False,
            "candidate_pack_written": False,
            "candidate_pack_paths": [],
        }
        require_sandbox_boundary(item, payload_name="sandbox_throughput_bottleneck")
        items.append(item)
    return items


def _summary(iteration_rows: list[dict[str, Any]], stage_rows: list[dict[str, Any]], *, limit: int) -> dict[str, Any]:
    status_counts = Counter(str(row.get("iteration_status") or "unknown") for row in iteration_rows)
    telemetry_counts = Counter(str(row.get("telemetry_status") or "unknown") for row in iteration_rows)
    stage_runtime = Counter()
    for row in stage_rows:
        stage_runtime[str(row.get("stage_id") or "unknown")] += _safe_float(row.get("duration_seconds"))
    summary = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_throughput_summary",
        "iteration_count": len(iteration_rows),
        "telemetry_iteration_count": telemetry_counts.get("present", 0),
        "missing_telemetry_count": telemetry_counts.get("missing_telemetry", 0),
        "iteration_status_counts": dict(sorted(status_counts.items())),
        "telemetry_status_counts": dict(sorted(telemetry_counts.items())),
        "total_runtime_seconds": round(sum(_safe_float(row.get("total_runtime_seconds")) for row in iteration_rows), 9),
        "total_source_bytes_read": sum(_safe_int(row.get("source_bytes_read")) for row in iteration_rows),
        "total_rows_loaded_after_2024_filter": sum(
            _safe_int(row.get("rows_loaded_after_2024_filter")) for row in iteration_rows
        ),
        "total_artifact_bytes_written_estimate": sum(
            _safe_int(row.get("artifact_bytes_written_estimate")) for row in iteration_rows
        ),
        "total_frame_cache_hit_count": sum(_safe_int(row.get("frame_cache_hit_count")) for row in iteration_rows),
        "total_frame_cache_miss_count": sum(_safe_int(row.get("frame_cache_miss_count")) for row in iteration_rows),
        "total_integrity_cache_hit_count": sum(
            _safe_int(row.get("integrity_cache_hit_count")) for row in iteration_rows
        ),
        "total_integrity_cache_miss_count": sum(
            _safe_int(row.get("integrity_cache_miss_count")) for row in iteration_rows
        ),
        "stage_runtime_seconds": {key: round(value, 9) for key, value in sorted(stage_runtime.items())},
        "bottleneck_ranking": _bottleneck_ranking(stage_rows, limit=limit),
        "speedup_claimed": False,
        "strict_validation_executed": False,
        "strict_validation_authorized": False,
        "candidate_pack_written": False,
        "candidate_pack_write_authorized": False,
        "candidate_pack_paths": [],
    }
    require_sandbox_boundary(summary, payload_name="sandbox_throughput_summary")
    return summary


def summarize_sandbox_throughput(
    root_dir: str | Path,
    *,
    output_dir: str | Path | None = None,
    containment_root: str | Path | None = None,
    max_files: int = 5000,
    limit: int = 10,
    write_report: bool = True,
) -> dict[str, Any]:
    if max_files <= 0:
        raise ValueError("sandbox throughput max_files must be positive")
    if limit <= 0:
        raise ValueError("sandbox throughput limit must be positive")
    root_path = Path(root_dir).expanduser().resolve()
    if root_path.exists() and not root_path.is_dir():
        raise ValueError(f"sandbox throughput root must be a directory: {root_path}")
    if not root_path.exists() and write_report:
        root_path.mkdir(parents=True, exist_ok=True)
    containment_path = Path(containment_root).expanduser().resolve() if containment_root is not None else root_path
    manifest_paths = _discover_iteration_manifests(root_path, max_files=max_files)
    manifests = [_load_manifest(path) for path in manifest_paths]
    iteration_rows = [
        _iteration_row(payload, manifest_path=path, root=root_path)
        for payload, path in zip(manifests, manifest_paths, strict=True)
    ]
    stage_rows: list[dict[str, Any]] = []
    for payload, path in zip(manifests, manifest_paths, strict=True):
        stage_rows.extend(_stage_rows(payload, manifest_path=path, root=root_path))
    report_id = digest_payload(
        {
            "schema_version": SANDBOX_THROUGHPUT_REPORT_SCHEMA_VERSION,
            "manifest_paths": [str(path.relative_to(root_path)) for path in manifest_paths],
            "iteration_count": len(iteration_rows),
            "stage_count": len(stage_rows),
        },
        prefix="sbxthroughput",
        length=24,
    )
    destination = (
        _resolve_under_root(containment_path, output_dir, field_name="output_dir")
        if output_dir is not None
        else root_path / "rapid_strategy_sandbox_throughput" / report_id
    )
    report_json_path = destination / SANDBOX_THROUGHPUT_REPORT_JSON_NAME
    iteration_parquet_path = destination / SANDBOX_THROUGHPUT_ITERATION_SUMMARY_PARQUET_NAME
    stage_parquet_path = destination / SANDBOX_THROUGHPUT_STAGE_SUMMARY_PARQUET_NAME
    summary = _summary(iteration_rows, stage_rows, limit=limit)
    payload = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_throughput_report",
        "schema_version": SANDBOX_THROUGHPUT_REPORT_SCHEMA_VERSION,
        "report_id": report_id,
        "root_dir": str(root_path),
        "output_dir": str(destination) if write_report else None,
        "manifest_count": len(manifest_paths),
        "manifest_paths": [str(path) for path in manifest_paths],
        "summary": summary,
        "iteration_rows": iteration_rows,
        "stage_rows": stage_rows,
        "descriptor_only": True,
        "report_only": True,
        "summarizes_existing_artifacts_only": True,
        "benchmark_execution_mode": "summarize_existing_iteration_manifests_only",
        "speedup_claimed": False,
        "sandbox_sweep_executed": False,
        "artifact_indexer_executed": False,
        "strict_validation_executed": False,
        "strict_validation_authorized": False,
        "candidate_pack_written": False,
        "candidate_pack_write_authorized": False,
        "candidate_pack_paths": [],
        "report_json_path": str(report_json_path) if write_report else None,
        "iteration_summary_parquet_path": str(iteration_parquet_path) if write_report else None,
        "stage_summary_parquet_path": str(stage_parquet_path) if write_report else None,
    }
    require_sandbox_boundary(payload, payload_name="sandbox_throughput_report")
    if write_report:
        destination.mkdir(parents=True, exist_ok=True)
        report_json_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=_json_default),
            encoding="utf-8",
        )
        iteration_frame = pd.DataFrame([_row_for_parquet(row) for row in iteration_rows])
        if iteration_frame.empty:
            iteration_frame = pd.DataFrame(columns=["iteration_id", "telemetry_status", *SANDBOX_BOUNDARY_FLAGS])
        iteration_frame.to_parquet(iteration_parquet_path, index=False)
        stage_frame = pd.DataFrame([_row_for_parquet(row) for row in stage_rows])
        if stage_frame.empty:
            stage_frame = pd.DataFrame(columns=["iteration_id", "stage_id", "duration_seconds", *SANDBOX_BOUNDARY_FLAGS])
        stage_frame.to_parquet(stage_parquet_path, index=False)
    return payload
