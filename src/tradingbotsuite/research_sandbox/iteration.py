from __future__ import annotations

import json
import time
import tracemalloc
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence

import pandas as pd

from tradingbotsuite.research_sandbox.analytics import summarize_sandbox_run
from tradingbotsuite.research_sandbox.archive_coverage import summarize_sandbox_archive_coverage
from tradingbotsuite.research_sandbox.archive_manifest import build_sandbox_archive_manifest
from tradingbotsuite.research_sandbox.boundary import (
    SANDBOX_BOUNDARY_FLAGS,
    require_sandbox_boundary,
    sandbox_boundary_metadata,
)
from tradingbotsuite.research_sandbox.falsification import summarize_sandbox_hypotheses
from tradingbotsuite.research_sandbox.identity import digest_payload
from tradingbotsuite.research_sandbox.integrity import require_sandbox_artifact_integrity
from tradingbotsuite.research_sandbox.intake import (
    load_sandbox_run_spec,
    load_strategy_catalog,
    load_venue_archive_descriptors,
)
from tradingbotsuite.research_sandbox.leaderboard import build_sandbox_global_leaderboard
from tradingbotsuite.research_sandbox.market_data import SandboxMarketDataCache
from tradingbotsuite.research_sandbox.preflight import preflight_sandbox_compatibility
from tradingbotsuite.research_sandbox.runner import run_sandbox_archive_sweep
from tradingbotsuite.research_sandbox.spec import MIN_SANDBOX_DATE, DataWindow, SandboxRunSpec, StrategyCatalogRow, VenueArchiveDescriptor
from tradingbotsuite.research_sandbox.strategy_catalog_materializer import materialize_sandbox_strategy_catalog
from tradingbotsuite.research_sandbox.validation_bundle import export_sandbox_validation_request_bundle


SANDBOX_ITERATION_MANIFEST_JSON_NAME = "sandbox_iteration_manifest.json"
SANDBOX_ITERATION_STEPS_PARQUET_NAME = "sandbox_iteration_steps.parquet"
SANDBOX_ITERATION_AGENT_BRIEF_JSON_NAME = "sandbox_iteration_agent_brief.json"
SANDBOX_ITERATION_AGENT_BRIEF_PARQUET_NAME = "sandbox_iteration_agent_brief.parquet"
DEFAULT_ITERATION_WINDOW_START = "2024-01-01"
DEFAULT_ITERATION_WINDOW_END = "2024-12-31"
DEFAULT_ITERATION_WINDOW_PRESET = "explicit"
DEFAULT_ITERATION_RECENT_LOOKBACK_DAYS = 365
SANDBOX_ITERATION_PREFLIGHT_GATE_VERSION = 1
SANDBOX_ITERATION_ARCHIVE_COVERAGE_STEP_VERSION = 1
SANDBOX_ITERATION_AGENT_BRIEF_VERSION = 1
SANDBOX_ITERATION_THROUGHPUT_TELEMETRY_VERSION = 1
SANDBOX_ITERATION_SOURCE_SUMMARY_LIMIT = 8
SANDBOX_ITERATION_STRATEGY_SOURCE_SUMMARY_LIMIT = SANDBOX_ITERATION_SOURCE_SUMMARY_LIMIT
_CACHED_JSON_ARTIFACT_KEYS = (
    "agent_brief_json_path",
    "archive_coverage_json_path",
    "archive_coverage_source_audit_json_path",
    "preflight_json_path",
    "analysis_report_path",
    "hypothesis_falsification_json_path",
    "strict_validation_request_bundle_json_path",
    "global_leaderboard_json_path",
)
_CACHED_FILE_ARTIFACT_KEYS = (
    "agent_brief_parquet_path",
    "archive_coverage_parquet_path",
    "archive_coverage_venue_expansion_gaps_parquet_path",
    "archive_coverage_source_audit_parquet_path",
    "preflight_parquet_path",
    "hypothesis_falsification_parquet_path",
    "strict_validation_request_bundle_parquet_path",
    "global_leaderboard_parquet_path",
    "iteration_steps_parquet_path",
)
_CACHED_PREFLIGHT_REQUIRED_KEYS = (
    "agent_brief_json_path",
    "agent_brief_parquet_path",
    "archive_coverage_json_path",
    "archive_coverage_parquet_path",
    "archive_coverage_source_audit_json_path",
    "archive_coverage_source_audit_parquet_path",
    "preflight_json_path",
    "preflight_parquet_path",
    "iteration_steps_parquet_path",
)
_CACHED_COMPLETED_REQUIRED_KEYS = (
    "run_manifest_path",
    "analysis_report_path",
    "hypothesis_falsification_json_path",
    "hypothesis_falsification_parquet_path",
    "strict_validation_request_bundle_json_path",
    "strict_validation_request_bundle_parquet_path",
    "global_leaderboard_json_path",
    "global_leaderboard_parquet_path",
)


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _perf_counter() -> float:
    return time.perf_counter()


def _stage_telemetry(
    *,
    stage_id: str,
    started_at: float,
    status: str,
    counts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_throughput_stage",
        "telemetry_version": SANDBOX_ITERATION_THROUGHPUT_TELEMETRY_VERSION,
        "stage_id": stage_id,
        "status": status,
        "duration_seconds": round(max(0.0, _perf_counter() - started_at), 9),
        "counts": counts or {},
        "strict_validation_executed": False,
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
    }


def _memory_snapshot() -> dict[str, Any]:
    if not tracemalloc.is_tracing():
        return {
            "memory_telemetry_available": False,
            "current_traced_memory_bytes": None,
            "peak_traced_memory_bytes": None,
        }
    current, peak = tracemalloc.get_traced_memory()
    return {
        "memory_telemetry_available": True,
        "current_traced_memory_bytes": int(current),
        "peak_traced_memory_bytes": int(peak),
    }


def _throughput_telemetry(
    *,
    iteration_id: str | None,
    total_started_at: float,
    stage_timings: list[dict[str, Any]],
    market_data_cache: SandboxMarketDataCache | None,
    workers_requested: int = 1,
    workers_used: int = 1,
) -> dict[str, Any]:
    stage_runtime_seconds = {
        str(stage.get("stage_id")): float(stage.get("duration_seconds", 0.0) or 0.0)
        for stage in stage_timings
    }
    cache_stats = market_data_cache.stats() if market_data_cache is not None else {}
    payload = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_throughput_telemetry",
        "telemetry_version": SANDBOX_ITERATION_THROUGHPUT_TELEMETRY_VERSION,
        "iteration_id": iteration_id,
        "total_runtime_seconds": round(max(0.0, _perf_counter() - total_started_at), 9),
        "stage_count": len(stage_timings),
        "stage_timings": stage_timings,
        "stage_runtime_seconds": stage_runtime_seconds,
        "market_data_cache_stats": cache_stats,
        "workers_requested": int(workers_requested),
        "workers_used": int(workers_used),
        "benchmark_execution_mode": "single_iteration_observed_runtime",
        "speedup_claimed": False,
        "strict_validation_executed": False,
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
        **_memory_snapshot(),
    }
    require_sandbox_boundary(payload, payload_name="sandbox_iteration_throughput_telemetry")
    return payload


def _row_for_parquet(payload: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, (dict, list, tuple)):
            row[key] = json.dumps(value, sort_keys=True, default=_json_default)
        else:
            row[key] = value
    return row


def _as_paths(values: Sequence[str | Path] | None) -> list[Path]:
    return [Path(value) for value in values or ()]


def _resolved_path_string(value: str | Path | None) -> str | None:
    if value is None:
        return None
    return str(Path(value).expanduser().resolve())


def _resolved_path_strings(values: Sequence[str | Path] | None) -> list[str]:
    return [_resolved_path_string(value) or "" for value in values or ()]


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _count_strings(values: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[str(value)] = counts.get(str(value), 0) + 1
    return dict(sorted(counts.items()))


def _merge_count_dicts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = row.get(key)
        if not isinstance(value, dict):
            continue
        for item_key, item_count in value.items():
            text_key = str(item_key)
            counts[text_key] = counts.get(text_key, 0) + _int_value(item_count)
    return dict(sorted(counts.items()))


def _bounded_unique_strings(values: list[Any], *, limit: int = SANDBOX_ITERATION_STRATEGY_SOURCE_SUMMARY_LIMIT) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value)
        if text in seen:
            continue
        seen.add(text)
        output.append(text)
        if len(output) >= limit:
            break
    return output


def _source_skip_reason_counts(sources: list[dict[str, Any]]) -> dict[str, int]:
    reasons: list[str] = []
    for source in sources:
        raw_reasons = source.get("skip_reasons", [])
        if isinstance(raw_reasons, list):
            reasons.extend(str(reason) for reason in raw_reasons)
    return _count_strings(reasons)


def _skipped_source_samples(
    sources: list[dict[str, Any]],
    *,
    limit: int = SANDBOX_ITERATION_STRATEGY_SOURCE_SUMMARY_LIMIT,
) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for source in sources:
        if source.get("status") != "skipped":
            continue
        raw_reasons = source.get("skip_reasons", [])
        skip_reasons = [str(reason) for reason in raw_reasons] if isinstance(raw_reasons, list) else []
        samples.append(
            {
                "source_path": source.get("source_path"),
                "source_suffix": source.get("source_suffix"),
                "skip_reasons": skip_reasons,
            }
        )
        if len(samples) >= limit:
            break
    return samples


def _skipped_archive_file_samples(
    files: list[dict[str, Any]],
    *,
    limit: int = SANDBOX_ITERATION_SOURCE_SUMMARY_LIMIT,
) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for row in files:
        if row.get("status") != "skipped":
            continue
        raw_reasons = row.get("skip_reasons", [])
        skip_reasons = [str(reason) for reason in raw_reasons] if isinstance(raw_reasons, list) else []
        samples.append(
            {
                "source_path": row.get("source_path"),
                "source_suffix": row.get("source_suffix"),
                "source_sha256": row.get("source_sha256"),
                "source_byte_size": _int_value(row.get("source_byte_size")),
                "skip_reasons": skip_reasons,
                "normalized_row_count": _int_value(row.get("normalized_row_count")),
                "window_start": row.get("window_start"),
                "window_end": row.get("window_end"),
                "requested_window_start": row.get("requested_window_start"),
                "requested_window_end": row.get("requested_window_end"),
            }
        )
        if len(samples) >= limit:
            break
    return samples


def _sheet_name_sample(workbook_sources: list[dict[str, Any]], key: str) -> list[str]:
    values: list[Any] = []
    for source in workbook_sources:
        names = source.get(key, [])
        if isinstance(names, list):
            values.extend(names)
    return _bounded_unique_strings(values)


def _strategy_source_summary_from_materializer(payload: dict[str, Any]) -> dict[str, Any]:
    sources = [source for source in payload.get("sources", []) if isinstance(source, dict)]
    workbook_sources = [source for source in sources if source.get("source_kind") == "workbook_strategy_catalog"]
    skipped_sources = [source for source in sources if source.get("status") == "skipped"]
    workbook_source_summaries = [
        {
            "source_path": source.get("source_path"),
            "strategy_count": _int_value(source.get("strategy_count")),
            "workbook_sheet_count": _int_value(source.get("workbook_sheet_count")),
            "workbook_included_sheet_count": _int_value(source.get("workbook_included_sheet_count")),
            "workbook_skipped_sheet_count": _int_value(source.get("workbook_skipped_sheet_count")),
            "workbook_included_sheet_names": list(source.get("workbook_included_sheet_names", []) or []),
            "workbook_skipped_sheet_names": list(source.get("workbook_skipped_sheet_names", []) or []),
        }
        for source in workbook_sources[:SANDBOX_ITERATION_STRATEGY_SOURCE_SUMMARY_LIMIT]
    ]
    return {
        "mode": "materialized_strategy_catalog",
        "catalog_id": payload.get("catalog_id"),
        "strategy_count": _int_value(payload.get("strategy_count")),
        "source_count": _int_value(payload.get("source_count")),
        "included_source_count": _int_value(payload.get("included_source_count")),
        "skipped_source_count": _int_value(payload.get("skipped_source_count")),
        "family_counts": dict(payload.get("family_counts", {}) or {}),
        "side_counts": dict(payload.get("side_counts", {}) or {}),
        "blueprint_counts": dict(payload.get("blueprint_counts", {}) or {}),
        "source_status_counts": _count_strings([str(source.get("status") or "unknown") for source in sources]),
        "source_suffix_counts": _count_strings([str(source.get("source_suffix") or "") for source in sources]),
        "source_skip_reason_counts": _source_skip_reason_counts(sources),
        "skipped_source_samples": _skipped_source_samples(sources),
        "skipped_source_samples_truncated": len(skipped_sources) > SANDBOX_ITERATION_STRATEGY_SOURCE_SUMMARY_LIMIT,
        "workbook_source_count": len(workbook_sources),
        "workbook_sheet_count": sum(_int_value(source.get("workbook_sheet_count")) for source in workbook_sources),
        "workbook_included_sheet_count": sum(
            _int_value(source.get("workbook_included_sheet_count")) for source in workbook_sources
        ),
        "workbook_skipped_sheet_count": sum(
            _int_value(source.get("workbook_skipped_sheet_count")) for source in workbook_sources
        ),
        "workbook_strategy_count": sum(_int_value(source.get("workbook_strategy_count")) for source in workbook_sources),
        "workbook_sheet_status_counts": _merge_count_dicts(workbook_sources, "workbook_sheet_status_counts"),
        "workbook_sheet_kind_counts": _merge_count_dicts(workbook_sources, "workbook_sheet_kind_counts"),
        "workbook_sheet_name_sample": _sheet_name_sample(workbook_sources, "workbook_sheet_names"),
        "workbook_included_sheet_name_sample": _sheet_name_sample(workbook_sources, "workbook_included_sheet_names"),
        "workbook_skipped_sheet_name_sample": _sheet_name_sample(workbook_sources, "workbook_skipped_sheet_names"),
        "workbook_source_summaries": workbook_source_summaries,
        "workbook_source_summaries_truncated": len(workbook_sources) > SANDBOX_ITERATION_STRATEGY_SOURCE_SUMMARY_LIMIT,
    }


def _strategy_source_summary_from_existing(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "mode": source.get("mode"),
        "strategy_count": _int_value(source.get("strategy_count")),
    }


def _strategy_source_summary_from_source(source: dict[str, Any]) -> dict[str, Any]:
    summary = source.get("strategy_source_summary")
    if isinstance(summary, dict):
        return dict(summary)
    return _strategy_source_summary_from_existing(source)


def _archive_source_summary_from_builder(payload: dict[str, Any]) -> dict[str, Any]:
    files = [row for row in payload.get("files", []) if isinstance(row, dict)]
    skipped_files = [row for row in files if row.get("status") == "skipped"]
    return {
        "mode": "built_venue_archive_manifest",
        "manifest_id": payload.get("manifest_id"),
        "descriptor_count": _int_value(payload.get("descriptor_count")),
        "file_count": _int_value(payload.get("file_count")),
        "skipped_count": _int_value(payload.get("skipped_count")),
        "requested_window_filter_applied": bool(payload.get("requested_window_filter_applied", False)),
        "requested_window_start": payload.get("requested_window_start"),
        "requested_window_end": payload.get("requested_window_end"),
        "file_status_counts": _count_strings([str(row.get("status") or "unknown") for row in files]),
        "file_suffix_counts": _count_strings([str(row.get("source_suffix") or "") for row in files]),
        "file_skip_reason_counts": _source_skip_reason_counts(files),
        "skipped_file_samples": _skipped_archive_file_samples(files),
        "skipped_file_samples_truncated": len(skipped_files) > SANDBOX_ITERATION_SOURCE_SUMMARY_LIMIT,
    }


def _archive_source_summary_from_existing(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "mode": source.get("mode"),
        "descriptor_count": _int_value(source.get("descriptor_count")),
    }


def _archive_source_summary_from_source(source: dict[str, Any]) -> dict[str, Any]:
    summary = source.get("archive_source_summary")
    if isinstance(summary, dict):
        return dict(summary)
    return _archive_source_summary_from_existing(source)


def _spec_identity_payload(spec: SandboxRunSpec, *, include_run_id: bool) -> dict[str, Any]:
    payload = spec.to_payload()
    payload.pop("created_at", None)
    if not include_run_id:
        payload.pop("run_id", None)
    return payload


def _coerce_window_date(value: date | datetime | str | None, *, field_name: str) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError as exc:
            raise ValueError(f"{field_name} must be ISO date or datetime") from exc
    raise TypeError(f"{field_name} must be date, datetime, ISO string, or None")


def _recent_window_days(window_preset: str, window_lookback_days: int) -> int:
    preset = window_preset.strip().lower()
    if preset == "recent_365d":
        return DEFAULT_ITERATION_RECENT_LOOKBACK_DAYS
    if preset == "recent_days":
        return int(window_lookback_days)
    if preset.startswith("recent_") and preset.endswith("d"):
        try:
            return int(preset[len("recent_") : -1])
        except ValueError as exc:
            raise ValueError(f"unsupported sandbox iteration window_preset: {window_preset}") from exc
    raise ValueError(f"unsupported sandbox iteration window_preset: {window_preset}")


def _resolve_iteration_window(
    *,
    window_start: str,
    window_end: str,
    window_preset: str | None,
    window_as_of_date: date | datetime | str | None,
    window_lookback_days: int,
) -> tuple[DataWindow, dict[str, Any]]:
    preset = (window_preset or DEFAULT_ITERATION_WINDOW_PRESET).strip().lower()
    if preset in {"", "explicit"}:
        data_window = DataWindow(window_start, window_end)
        return data_window, {
            "window_selection_mode": "explicit",
            "window_preset": "explicit",
            "window_as_of_date": None,
            "window_lookback_days": None,
            "resolved_window_start": data_window.start.isoformat(),
            "resolved_window_end": data_window.end.isoformat(),
            "window_start_clipped_to_min_date": False,
            "min_sandbox_date": MIN_SANDBOX_DATE.isoformat(),
        }

    lookback_days = _recent_window_days(preset, window_lookback_days)
    if lookback_days <= 0:
        raise ValueError("window_lookback_days must be positive")
    as_of = _coerce_window_date(window_as_of_date, field_name="window_as_of_date") or datetime.now(timezone.utc).date()
    if as_of < MIN_SANDBOX_DATE:
        raise ValueError("sandbox iteration window_as_of_date must be on or after 2024-01-01")
    raw_start = as_of - timedelta(days=lookback_days - 1)
    start = max(raw_start, MIN_SANDBOX_DATE)
    data_window = DataWindow(start, as_of)
    return data_window, {
        "window_selection_mode": "recent",
        "window_preset": preset,
        "window_as_of_date": as_of.isoformat(),
        "window_lookback_days": lookback_days,
        "resolved_window_start": data_window.start.isoformat(),
        "resolved_window_end": data_window.end.isoformat(),
        "raw_window_start": raw_start.isoformat(),
        "window_start_clipped_to_min_date": raw_start < MIN_SANDBOX_DATE,
        "min_sandbox_date": MIN_SANDBOX_DATE.isoformat(),
    }


def _default_spec(
    *,
    run_id: str,
    data_window: DataWindow,
    holding_periods: Sequence[int],
    round_trip_cost_bps: float,
    min_trades: int,
    max_evidence_requests: int,
    rank_top_n: int,
) -> SandboxRunSpec:
    return SandboxRunSpec(
        run_id=run_id,
        data_window=data_window,
        holding_periods=tuple(int(value) for value in holding_periods),
        round_trip_cost_bps=float(round_trip_cost_bps),
        min_trades=int(min_trades),
        max_evidence_requests=int(max_evidence_requests),
        rank_top_n=int(rank_top_n),
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        description="Generated by run-rapid-strategy-sandbox-iteration for agent preflight.",
    )


def _append_argv_value(argv: list[str], flag: str, value: Any) -> None:
    if value is None:
        return
    argv.extend([flag, str(value)])


def _append_argv_paths(argv: list[str], flag: str, paths: Sequence[str]) -> None:
    for path in paths:
        if path:
            argv.extend([flag, path])


def _iteration_input_replay_context(
    *,
    output_root: Path,
    spec_path: str | Path | None,
    strategy_catalog_path: str | Path | None,
    catalog_roots: Sequence[str | Path] | None,
    venue_archives_path: str | Path | None,
    archive_roots: Sequence[str | Path] | None,
    run_id: str | None,
    window_start: str,
    window_end: str,
    window_preset: str | None,
    window_as_of_date: date | datetime | str | None,
    window_lookback_days: int,
    holding_periods: Sequence[int],
    round_trip_cost_bps: float,
    min_trades: int,
    max_evidence_requests: int,
    rank_top_n: int,
    min_request_score: float,
    catalog_max_files: int,
    archive_max_files: int,
    archive_venue: str | None,
    archive_symbol: str | None,
    archive_data_family: str | None,
    archive_interval: str | None,
    leaderboard_max_runs: int,
    leaderboard_top_n: int,
) -> dict[str, Any]:
    spec_input_path = _resolved_path_string(spec_path)
    strategy_catalog_input_path = _resolved_path_string(strategy_catalog_path)
    catalog_root_paths = _resolved_path_strings(catalog_roots)
    venue_archives_input_path = _resolved_path_string(venue_archives_path)
    archive_root_paths = _resolved_path_strings(archive_roots)
    strategy_input_mode = "strategy_catalog" if strategy_catalog_input_path else "catalog_roots"
    archive_input_mode = "venue_archives" if venue_archives_input_path else "archive_roots"
    argv = [
        "python",
        "-m",
        "tradingbotsuite.main",
        "run-rapid-strategy-sandbox-iteration",
        "--output-dir",
        str(output_root),
    ]
    if spec_input_path:
        argv.extend(["--spec", spec_input_path])
    else:
        argv.extend(
            [
                "--window-start",
                str(window_start),
                "--window-end",
                str(window_end),
                "--window-preset",
                str(window_preset or DEFAULT_ITERATION_WINDOW_PRESET),
                "--window-lookback-days",
                str(int(window_lookback_days)),
                "--holding-periods",
                ",".join(str(int(value)) for value in holding_periods),
                "--round-trip-cost-bps",
                str(float(round_trip_cost_bps)),
                "--min-trades",
                str(int(min_trades)),
                "--max-evidence-requests",
                str(int(max_evidence_requests)),
                "--rank-top-n",
                str(int(rank_top_n)),
            ]
        )
        _append_argv_value(argv, "--window-as-of-date", window_as_of_date)
    _append_argv_value(argv, "--run-id", run_id)
    if strategy_catalog_input_path:
        argv.extend(["--strategy-catalog", strategy_catalog_input_path])
    else:
        _append_argv_paths(argv, "--catalog-root", catalog_root_paths)
        argv.extend(["--catalog-max-files", str(int(catalog_max_files))])
    if venue_archives_input_path:
        argv.extend(["--venue-archives", venue_archives_input_path])
    else:
        _append_argv_paths(argv, "--archive-root", archive_root_paths)
        argv.extend(["--archive-max-files", str(int(archive_max_files))])
        _append_argv_value(argv, "--archive-venue", archive_venue)
        _append_argv_value(argv, "--archive-symbol", archive_symbol)
        _append_argv_value(argv, "--archive-data-family", archive_data_family)
        _append_argv_value(argv, "--archive-interval", archive_interval)
    argv.extend(
        [
            "--min-request-score",
            str(float(min_request_score)),
            "--leaderboard-max-runs",
            str(int(leaderboard_max_runs)),
            "--leaderboard-top-n",
            str(int(leaderboard_top_n)),
        ]
    )
    context_identity = {
        "command_argv": argv,
        "strategy_input_mode": strategy_input_mode,
        "archive_input_mode": archive_input_mode,
        "spec_input_path": spec_input_path,
        "strategy_catalog_input_path": strategy_catalog_input_path,
        "catalog_root_paths": catalog_root_paths,
        "venue_archives_input_path": venue_archives_input_path,
        "archive_root_paths": archive_root_paths,
    }
    context = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_input_replay_context",
        "replay_context_id": digest_payload(context_identity, prefix="sbxreplayctx", length=24),
        "command": "run-rapid-strategy-sandbox-iteration",
        "command_argv": argv,
        "command_argv_truncated": False,
        "execution_mode": "descriptor_only_no_execution",
        "strict_validation_executed": False,
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
        "output_dir": str(output_root),
        "spec_input_path": spec_input_path,
        "strategy_input_mode": strategy_input_mode,
        "strategy_catalog_input_path": strategy_catalog_input_path,
        "catalog_root_paths": catalog_root_paths,
        "venue_input_mode": archive_input_mode,
        "venue_archives_input_path": venue_archives_input_path,
        "archive_root_paths": archive_root_paths,
        "run_id": run_id,
        "window_start": str(window_start),
        "window_end": str(window_end),
        "window_preset": str(window_preset or DEFAULT_ITERATION_WINDOW_PRESET),
        "window_as_of_date": str(window_as_of_date) if window_as_of_date is not None else None,
        "window_lookback_days": int(window_lookback_days),
        "holding_periods": [int(value) for value in holding_periods],
        "round_trip_cost_bps": float(round_trip_cost_bps),
        "min_trades": int(min_trades),
        "max_evidence_requests": int(max_evidence_requests),
        "rank_top_n": int(rank_top_n),
        "min_request_score": float(min_request_score),
        "catalog_max_files": int(catalog_max_files),
        "archive_max_files": int(archive_max_files),
        "archive_venue": archive_venue,
        "archive_symbol": archive_symbol,
        "archive_data_family": archive_data_family,
        "archive_interval": archive_interval,
        "leaderboard_max_runs": int(leaderboard_max_runs),
        "leaderboard_top_n": int(leaderboard_top_n),
    }
    require_sandbox_boundary(context, payload_name="sandbox_iteration_input_replay_context")
    return context


def _load_or_materialize_strategies(
    *,
    strategy_catalog_path: str | Path | None,
    catalog_roots: Sequence[str | Path] | None,
    output_root: Path,
    max_files: int,
) -> tuple[list[StrategyCatalogRow], dict[str, Any]]:
    if strategy_catalog_path is not None and catalog_roots:
        raise ValueError("use either strategy_catalog_path or catalog_roots, not both")
    if strategy_catalog_path is None and not catalog_roots:
        raise ValueError("sandbox iteration requires strategy_catalog_path or at least one catalog_root")
    if strategy_catalog_path is not None:
        catalog_path = Path(strategy_catalog_path).resolve()
        strategies = load_strategy_catalog(catalog_path)
        source = {
            "mode": "existing_strategy_catalog",
            "strategy_catalog_json_path": str(catalog_path),
            "strategy_count": len(strategies),
        }
        source["strategy_source_summary"] = _strategy_source_summary_from_existing(source)
        return strategies, source

    payload = materialize_sandbox_strategy_catalog(
        _as_paths(catalog_roots),
        output_dir=output_root / "_materialized_inputs" / "strategy_catalogs",
        max_files=max_files,
    )
    strategies = load_strategy_catalog(Path(str(payload["strategy_catalog_json_path"])))
    source = {
        "mode": "materialized_strategy_catalog",
        "catalog_id": payload["catalog_id"],
        "strategy_catalog_json_path": payload["strategy_catalog_json_path"],
        "strategy_catalog_parquet_path": payload["strategy_catalog_parquet_path"],
        "build_report_json_path": payload["build_report_json_path"],
        "build_report_parquet_path": payload["build_report_parquet_path"],
        "strategy_count": payload["strategy_count"],
        "included_source_count": payload["included_source_count"],
        "skipped_source_count": payload["skipped_source_count"],
    }
    source["strategy_source_summary"] = _strategy_source_summary_from_materializer(payload)
    return strategies, source


def _load_or_build_archives(
    *,
    venue_archives_path: str | Path | None,
    archive_roots: Sequence[str | Path] | None,
    output_root: Path,
    venue: str | None,
    symbol: str | None,
    data_family: str | None,
    interval: str | None,
    max_files: int,
    requested_window: DataWindow | None = None,
) -> tuple[list[VenueArchiveDescriptor], dict[str, Any]]:
    if venue_archives_path is not None and archive_roots:
        raise ValueError("use either venue_archives_path or archive_roots, not both")
    if venue_archives_path is None and not archive_roots:
        raise ValueError("sandbox iteration requires venue_archives_path or at least one archive_root")
    if venue_archives_path is not None:
        manifest_path = Path(venue_archives_path).resolve()
        venues = load_venue_archive_descriptors(manifest_path)
        source = {
            "mode": "existing_venue_archive_manifest",
            "venue_archive_manifest_path": str(manifest_path),
            "descriptor_count": len(venues),
        }
        source["archive_source_summary"] = _archive_source_summary_from_existing(source)
        return venues, source

    payload = build_sandbox_archive_manifest(
        _as_paths(archive_roots),
        output_dir=output_root / "_materialized_inputs" / "archive_manifests",
        venue=venue,
        symbol=symbol,
        data_family=data_family,
        interval=interval,
        max_files=max_files,
        requested_window=requested_window,
    )
    venues = load_venue_archive_descriptors(Path(str(payload["venue_archive_manifest_path"])))
    source = {
        "mode": "built_venue_archive_manifest",
        "manifest_id": payload["manifest_id"],
        "venue_archive_manifest_path": payload["venue_archive_manifest_path"],
        "build_report_json_path": payload["build_report_json_path"],
        "build_report_parquet_path": payload["build_report_parquet_path"],
        "descriptor_count": payload["descriptor_count"],
        "file_count": payload["file_count"],
        "skipped_count": payload["skipped_count"],
    }
    source["archive_source_summary"] = _archive_source_summary_from_builder(payload)
    return venues, source


def _iteration_id(
    *,
    strategies: list[StrategyCatalogRow],
    venues: list[VenueArchiveDescriptor],
    spec: SandboxRunSpec,
    include_run_id: bool,
    window_selection: dict[str, Any],
    min_request_score: float,
    strategy_source: dict[str, Any],
    archive_source: dict[str, Any],
) -> str:
    return digest_payload(
        {
            "strategies": [strategy.to_payload() for strategy in strategies],
            "venues": [venue.to_payload() for venue in venues],
            "spec": _spec_identity_payload(spec, include_run_id=include_run_id),
            "window_selection": window_selection,
            "min_request_score": float(min_request_score),
            "strategy_source_mode": strategy_source["mode"],
            "archive_source_mode": archive_source["mode"],
            "preflight_gate_version": SANDBOX_ITERATION_PREFLIGHT_GATE_VERSION,
            "archive_coverage_step_version": SANDBOX_ITERATION_ARCHIVE_COVERAGE_STEP_VERSION,
            "agent_brief_version": SANDBOX_ITERATION_AGENT_BRIEF_VERSION,
        },
        prefix="sbxiteration",
        length=24,
    )


def _step(
    *,
    iteration_id: str,
    step_id: str,
    status: str,
    artifact_paths: dict[str, Any] | None = None,
    counts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_iteration_step",
        "iteration_id": iteration_id,
        "step_id": step_id,
        "status": status,
        "artifact_paths": artifact_paths or {},
        "counts": counts or {},
    }
    require_sandbox_boundary(row, payload_name="sandbox_iteration_step")
    return row


def _preflight_step_counts(preflight: dict[str, Any]) -> dict[str, Any]:
    return {
        "row_count": preflight["row_count"],
        "strategy_count": preflight["strategy_count"],
        "descriptor_count": preflight["descriptor_count"],
        "trial_estimate": preflight["trial_estimate"],
        "runnable_trial_estimate": preflight["runnable_trial_estimate"],
        "blocked_trial_estimate": preflight["blocked_trial_estimate"],
        "status_counts": preflight["status_counts"],
        "blocker_reason_counts": preflight["blocker_reason_counts"],
    }


def _preflight_artifact_paths(preflight: dict[str, Any]) -> dict[str, Any]:
    return {
        "preflight_json_path": preflight["preflight_json_path"],
        "preflight_parquet_path": preflight["preflight_parquet_path"],
        "preflight_output_dir": preflight["output_dir"],
    }


def _preflight_manifest_fields(preflight: dict[str, Any]) -> dict[str, Any]:
    blocker_samples, blocker_samples_truncated = _preflight_blocker_sample_payload(preflight)
    return {
        "preflight_json_path": preflight["preflight_json_path"],
        "preflight_parquet_path": preflight["preflight_parquet_path"],
        "preflight_output_dir": preflight["output_dir"],
        "preflight_row_count": preflight["row_count"],
        "preflight_status_counts": preflight["status_counts"],
        "preflight_trial_estimate": preflight["trial_estimate"],
        "preflight_runnable_trial_estimate": preflight["runnable_trial_estimate"],
        "preflight_blocked_trial_estimate": preflight["blocked_trial_estimate"],
        "preflight_blocker_reason_counts": preflight["blocker_reason_counts"],
        "preflight_blocker_samples": blocker_samples,
        "preflight_blocker_samples_truncated": blocker_samples_truncated,
    }


def _preflight_blocker_sample_payload(
    preflight: dict[str, Any],
    *,
    limit: int = SANDBOX_ITERATION_SOURCE_SUMMARY_LIMIT,
) -> tuple[list[dict[str, Any]], bool]:
    rows = preflight.get("rows", [])
    if not isinstance(rows, list):
        return [], False
    blocked_rows: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        blocker_counts = row.get("blocker_reason_counts", {})
        has_blocker_counts = isinstance(blocker_counts, dict) and bool(blocker_counts)
        if (
            str(row.get("status") or "") != "blocked"
            and _int_value(row.get("blocked_trial_estimate")) <= 0
            and not has_blocker_counts
        ):
            continue
        blocked_rows.append(row)

    samples: list[dict[str, Any]] = []
    for row in blocked_rows[:limit]:
        blocker_counts = {
            str(reason): _int_value(count)
            for reason, count in dict(row.get("blocker_reason_counts", {}) or {}).items()
            if _int_value(count) > 0
        }
        columns = [str(column) for column in list(row.get("columns", []) or [])]
        samples.append(
            {
                "descriptor_id": row.get("descriptor_id"),
                "venue": row.get("venue"),
                "symbol": row.get("symbol"),
                "data_family": row.get("data_family"),
                "interval": row.get("interval"),
                "hypothesis_id": row.get("hypothesis_id"),
                "family": row.get("family"),
                "source_id": row.get("source_id"),
                "signal_column": row.get("signal_column"),
                "side": row.get("side"),
                "strategy_filter_column": row.get("strategy_filter_column"),
                "status": row.get("status"),
                "trial_estimate": _int_value(row.get("trial_estimate")),
                "runnable_trial_estimate": _int_value(row.get("runnable_trial_estimate")),
                "blocked_trial_estimate": _int_value(row.get("blocked_trial_estimate")),
                "blocker_reasons": [str(reason) for reason in list(row.get("blocker_reasons", []) or [])],
                "blocker_reason_counts": dict(sorted(blocker_counts.items())),
                "active_signal_count": _int_value(row.get("active_signal_count")),
                "market_row_count": _int_value(row.get("market_row_count")),
                "normalized_row_count": _int_value(row.get("normalized_row_count")),
                "routing_mode": row.get("routing_mode"),
                "source_path": row.get("source_path"),
                "has_high_low": bool(row.get("has_high_low", False)),
                "columns_sample": columns[:limit],
                "columns_truncated": len(columns) > limit,
                "container_kind": row.get("container_kind"),
                "selected_member_suffix": row.get("selected_member_suffix"),
                "selected_member_count": _int_value(row.get("selected_member_count")),
            }
        )
    return samples, len(blocked_rows) > limit


def _archive_coverage_step_counts(coverage: dict[str, Any]) -> dict[str, Any]:
    return {
        "descriptor_count": coverage["descriptor_count"],
        "ready_descriptor_count": coverage["ready_descriptor_count"],
        "blocked_descriptor_count": coverage["blocked_descriptor_count"],
        "requested_window_row_count": coverage.get("requested_window_row_count", 0),
        "coverage_bucket_count": coverage["coverage_bucket_count"],
        "ready_bucket_count": coverage["ready_bucket_count"],
        "blocked_bucket_count": coverage["blocked_bucket_count"],
        "mixed_bucket_count": coverage["mixed_bucket_count"],
        "status_counts": coverage["status_counts"],
        "venue_counts": coverage["venue_counts"],
    }


def _archive_coverage_artifact_paths(coverage: dict[str, Any]) -> dict[str, Any]:
    return {
        "archive_coverage_json_path": coverage["coverage_json_path"],
        "archive_coverage_parquet_path": coverage["coverage_parquet_path"],
        "archive_coverage_venue_expansion_gaps_parquet_path": coverage.get(
            "venue_expansion_gaps_parquet_path"
        ),
        "archive_coverage_dir": coverage["coverage_dir"],
        "archive_coverage_source_audit_json_path": coverage["source_audit_json_path"],
        "archive_coverage_source_audit_parquet_path": coverage["source_audit_parquet_path"],
    }


def _archive_coverage_blocker_sample_payload(
    coverage: dict[str, Any],
    *,
    limit: int = SANDBOX_ITERATION_SOURCE_SUMMARY_LIMIT,
) -> tuple[list[dict[str, Any]], bool]:
    rows = coverage.get("coverage_rows", [])
    if not isinstance(rows, list):
        return [], False
    blocked_rows: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        blocker_counts = row.get("blocker_reason_counts", {})
        if not isinstance(blocker_counts, dict):
            blocker_counts = {}
        if (
            _int_value(row.get("blocked_descriptor_count")) <= 0
            and not blocker_counts
            and str(row.get("status") or "") == "ready"
        ):
            continue
        blocked_rows.append(row)

    samples: list[dict[str, Any]] = []
    for row in blocked_rows[:limit]:
        blocker_counts = {
            str(reason): _int_value(count)
            for reason, count in dict(row.get("blocker_reason_counts", {}) or {}).items()
            if _int_value(count) > 0
        }
        samples.append(
            {
                "coverage_key": row.get("coverage_key"),
                "venue": row.get("venue"),
                "symbol": row.get("symbol"),
                "data_family": row.get("data_family"),
                "interval": row.get("interval"),
                "status": row.get("status"),
                "blocked_descriptor_count": _int_value(row.get("blocked_descriptor_count")),
                "ready_descriptor_count": _int_value(row.get("ready_descriptor_count")),
                "blocked_descriptor_ids": _bounded_unique_strings(
                    list(row.get("blocked_descriptor_ids", []) or []),
                    limit=limit,
                ),
                "source_paths": _bounded_unique_strings(list(row.get("source_paths", []) or []), limit=limit),
                "routing_modes": _bounded_unique_strings(list(row.get("routing_modes", []) or []), limit=limit),
                "blocker_reason_counts": dict(sorted(blocker_counts.items())),
                "requested_window_start": row.get("requested_window_start"),
                "requested_window_end": row.get("requested_window_end"),
                "requested_window_row_count": _int_value(row.get("requested_window_row_count")),
                "ready_requested_window_row_count": _int_value(row.get("ready_requested_window_row_count")),
                "requested_window_observed_start": row.get("requested_window_observed_start"),
                "requested_window_observed_end": row.get("requested_window_observed_end"),
                "observed_window_start": row.get("observed_window_start"),
                "observed_window_end": row.get("observed_window_end"),
                "declared_window_start": row.get("declared_window_start"),
                "declared_window_end": row.get("declared_window_end"),
                "market_start": row.get("market_start"),
                "market_end": row.get("market_end"),
            }
        )
    return samples, len(blocked_rows) > limit


def _venue_expansion_actionable_count(action_counts: Any) -> int:
    if not isinstance(action_counts, dict):
        return 0
    return sum(
        _int_value(count)
        for action, count in action_counts.items()
        if str(action) != "use_ready_archive_bucket"
    )


def _archive_coverage_venue_expansion_gap_sample_payload(
    coverage: dict[str, Any],
    *,
    limit: int = SANDBOX_ITERATION_SOURCE_SUMMARY_LIMIT,
) -> tuple[list[dict[str, Any]], bool]:
    rows = coverage.get("venue_expansion_gap_rows", [])
    if not isinstance(rows, list):
        return [], False
    actionable_rows = [
        row
        for row in rows
        if isinstance(row, dict) and str(row.get("target_action") or "") != "use_ready_archive_bucket"
    ]
    samples: list[dict[str, Any]] = []
    for row in actionable_rows[:limit]:
        samples.append(
            {
                "gap_rank": _int_value(row.get("gap_rank")),
                "market_symbol_key": row.get("market_symbol_key"),
                "data_family": row.get("data_family"),
                "interval": row.get("interval"),
                "target_venue": row.get("target_venue"),
                "target_bucket_key": row.get("target_bucket_key"),
                "target_venue_observed": bool(row.get("target_venue_observed", False)),
                "target_missing": bool(row.get("target_missing", False)),
                "target_status": row.get("target_status"),
                "target_action": row.get("target_action"),
                "observed_symbols": _bounded_unique_strings(
                    list(row.get("observed_symbols", []) or []),
                    limit=limit,
                ),
                "source_coverage_key": row.get("source_coverage_key"),
                "descriptor_count": _int_value(row.get("descriptor_count")),
                "ready_descriptor_count": _int_value(row.get("ready_descriptor_count")),
                "blocked_descriptor_count": _int_value(row.get("blocked_descriptor_count")),
                "ready_window_row_count": _int_value(row.get("ready_window_row_count")),
                "ready_requested_window_row_count": _int_value(row.get("ready_requested_window_row_count")),
                "requested_window_filter_applied": bool(row.get("requested_window_filter_applied", False)),
                "requested_window_start": row.get("requested_window_start"),
                "requested_window_end": row.get("requested_window_end"),
                "observed_window_start": row.get("observed_window_start"),
                "observed_window_end": row.get("observed_window_end"),
                "source_paths": _bounded_unique_strings(list(row.get("source_paths", []) or []), limit=limit),
                "manifest_paths": _bounded_unique_strings(list(row.get("manifest_paths", []) or []), limit=limit),
                "blocker_reason_counts": _compact_count_map(row.get("blocker_reason_counts")),
            }
        )
    return samples, len(actionable_rows) > limit


def _archive_coverage_manifest_fields(coverage: dict[str, Any]) -> dict[str, Any]:
    blocker_samples, blocker_samples_truncated = _archive_coverage_blocker_sample_payload(coverage)
    gap_samples, gap_samples_truncated = _archive_coverage_venue_expansion_gap_sample_payload(coverage)
    venue_expansion_action_counts = dict(coverage.get("venue_expansion_action_counts", {}) or {})
    return {
        "archive_coverage_step_version": SANDBOX_ITERATION_ARCHIVE_COVERAGE_STEP_VERSION,
        "archive_coverage_id": coverage["coverage_id"],
        "archive_coverage_dir": coverage["coverage_dir"],
        "archive_coverage_json_path": coverage["coverage_json_path"],
        "archive_coverage_parquet_path": coverage["coverage_parquet_path"],
        "archive_coverage_venue_expansion_gaps_parquet_path": coverage.get(
            "venue_expansion_gaps_parquet_path"
        ),
        "archive_coverage_source_audit_id": coverage["source_audit_id"],
        "archive_coverage_source_audit_json_path": coverage["source_audit_json_path"],
        "archive_coverage_source_audit_parquet_path": coverage["source_audit_parquet_path"],
        **{
            f"archive_coverage_{key}": value
            for key, value in _archive_coverage_step_counts(coverage).items()
        },
        "archive_coverage_blocker_reason_counts": _aggregate_coverage_blockers(coverage),
        "archive_coverage_blocker_samples": blocker_samples,
        "archive_coverage_blocker_samples_truncated": blocker_samples_truncated,
        "archive_coverage_venue_expansion_target_venues": list(
            coverage.get("venue_expansion_target_venues", []) or []
        ),
        "archive_coverage_venue_expansion_gap_row_count": _int_value(
            coverage.get("venue_expansion_gap_row_count")
        ),
        "archive_coverage_venue_expansion_actionable_gap_count": _venue_expansion_actionable_count(
            venue_expansion_action_counts
        ),
        "archive_coverage_venue_expansion_missing_target_count": _int_value(
            coverage.get("venue_expansion_missing_target_count")
        ),
        "archive_coverage_venue_expansion_ready_target_count": _int_value(
            coverage.get("venue_expansion_ready_target_count")
        ),
        "archive_coverage_venue_expansion_blocked_target_count": _int_value(
            coverage.get("venue_expansion_blocked_target_count")
        ),
        "archive_coverage_venue_expansion_mixed_target_count": _int_value(
            coverage.get("venue_expansion_mixed_target_count")
        ),
        "archive_coverage_venue_expansion_status_counts": dict(
            coverage.get("venue_expansion_status_counts", {}) or {}
        ),
        "archive_coverage_venue_expansion_action_counts": venue_expansion_action_counts,
        "archive_coverage_venue_expansion_gap_samples": gap_samples,
        "archive_coverage_venue_expansion_gap_samples_truncated": gap_samples_truncated,
    }


def _top_counts(counts: dict[str, Any] | None, *, limit: int = 5) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for reason, count in (counts or {}).items():
        rows.append({"reason": str(reason), "count": int(count or 0)})
    return sorted(rows, key=lambda row: (-int(row["count"]), str(row["reason"])))[:limit]


def _aggregate_coverage_blockers(coverage: dict[str, Any]) -> dict[str, int]:
    aggregate: dict[str, int] = {}
    rows = coverage.get("coverage_rows", [])
    if not isinstance(rows, list):
        return aggregate
    for row in rows:
        if not isinstance(row, dict):
            continue
        blockers = row.get("blocker_reason_counts", {})
        if not isinstance(blockers, dict):
            continue
        for reason, count in blockers.items():
            reason_key = str(reason)
            aggregate[reason_key] = aggregate.get(reason_key, 0) + int(count or 0)
    return dict(sorted(aggregate.items(), key=lambda item: (-item[1], item[0])))


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _float_value(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _compact_validation_requests(validation_bundle: dict[str, Any] | None, *, limit: int = 5) -> list[dict[str, Any]]:
    descriptors = (validation_bundle or {}).get("descriptors", [])
    if not isinstance(descriptors, list):
        return []
    rows: list[dict[str, Any]] = []
    for descriptor in descriptors:
        if not isinstance(descriptor, dict):
            continue
        source_metrics = descriptor.get("source_metrics", {})
        if not isinstance(source_metrics, dict):
            source_metrics = {}
        source_context = descriptor.get("source_trial_context", {})
        if not isinstance(source_context, dict):
            source_context = {}
        source_market_source = descriptor.get("source_market_source", {})
        if not isinstance(source_market_source, dict):
            source_market_source = source_context.get("market_source", {})
        if not isinstance(source_market_source, dict):
            source_market_source = {}
        source_summary = {
            key: source_market_source.get(key)
            for key in (
                "routing_mode",
                "descriptor_id",
                "venue",
                "symbol",
                "data_family",
                "data_path",
                "shared_market_data_path",
                "container_kind",
                "selected_member_suffix",
                "selected_member_count",
                "selected_member_name_sample",
                "selected_member_names_truncated",
                "available_member_suffix_counts",
                "available_member_suffix_count",
                "loadable_member_count",
            )
            if source_market_source.get(key) not in (None, "", [], {})
        }
        rows.append(
            {
                "descriptor_id": descriptor.get("descriptor_id"),
                "source_request_id": descriptor.get("source_request_id"),
                "source_trial_id": descriptor.get("source_trial_id"),
                "source_venue_descriptor_id": descriptor.get("source_venue_descriptor_id")
                or source_context.get("venue_descriptor_id")
                or source_summary.get("descriptor_id"),
                "hypothesis_id": descriptor.get("hypothesis_id"),
                "family": descriptor.get("family"),
                "venue": descriptor.get("venue"),
                "symbol": descriptor.get("symbol"),
                "reason": descriptor.get("reason"),
                "requested_validation": descriptor.get("requested_validation"),
                "strict_validation_command": descriptor.get("strict_validation_command"),
                "source_market_source": source_summary,
                "source_routing_mode": source_summary.get("routing_mode"),
                "source_data_path": source_summary.get("data_path"),
                "source_container_kind": descriptor.get("source_container_kind") or source_summary.get("container_kind"),
                "source_selected_member_suffix": descriptor.get("source_selected_member_suffix")
                or source_summary.get("selected_member_suffix"),
                "source_selected_member_count": _safe_int(
                    descriptor.get("source_selected_member_count")
                    or source_summary.get("selected_member_count")
                    or 0
                ),
                "source_selected_member_name_sample": descriptor.get("source_selected_member_name_sample")
                or source_summary.get("selected_member_name_sample")
                or [],
                "source_loadable_member_count": _safe_int(
                    descriptor.get("source_loadable_member_count")
                    or source_summary.get("loadable_member_count")
                    or 0
                ),
                "source_metrics": {
                    key: source_metrics.get(key)
                    for key in ("rank", "score", "trade_count", "total_return_pct", "sharpe")
                    if key in source_metrics
                },
                "source_market_start": descriptor.get("source_market_start") or source_context.get("market_start"),
                "source_market_end": descriptor.get("source_market_end") or source_context.get("market_end"),
            }
        )
    return rows[:limit]


def _compact_count_map(raw_counts: Any) -> dict[str, int]:
    if not isinstance(raw_counts, dict):
        return {}
    counts = {
        str(reason): _int_value(count)
        for reason, count in raw_counts.items()
        if _int_value(count) > 0
    }
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _analysis_results_by_trial_id(analysis: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    results = (analysis or {}).get("top_results", [])
    if not isinstance(results, list):
        return {}
    by_trial: dict[str, dict[str, Any]] = {}
    for result in results:
        if not isinstance(result, dict):
            continue
        trial_id = result.get("trial_id")
        if trial_id in (None, ""):
            continue
        by_trial[str(trial_id)] = result
    return by_trial


def _rejection_falsification_sample_payload(
    falsification: dict[str, Any] | None,
    analysis: dict[str, Any] | None,
    *,
    limit: int = SANDBOX_ITERATION_SOURCE_SUMMARY_LIMIT,
) -> tuple[list[dict[str, Any]], bool]:
    hypotheses = (falsification or {}).get("hypotheses", [])
    if not isinstance(hypotheses, list):
        return [], False
    review_rows = [
        row
        for row in hypotheses
        if isinstance(row, dict)
        and str(row.get("falsification_decision") or "") != "request_strict_validation"
    ]
    top_results = _analysis_results_by_trial_id(analysis)
    samples: list[dict[str, Any]] = []
    for row in review_rows[:limit]:
        best_trial_id = row.get("best_trial_id")
        best_result = top_results.get(str(best_trial_id)) if best_trial_id not in (None, "") else None
        if not isinstance(best_result, dict):
            best_result = {}
        rejection_reasons = best_result.get("rejection_reasons", [])
        if not isinstance(rejection_reasons, list):
            rejection_reasons = []
        samples.append(
            {
                "hypothesis_id": row.get("hypothesis_id"),
                "family": row.get("family"),
                "falsification_decision": row.get("falsification_decision"),
                "decision_reason": row.get("decision_reason"),
                "result_count": _int_value(row.get("result_count")),
                "screened_count": _int_value(row.get("screened_count")),
                "rejected_count": _int_value(row.get("rejected_count")),
                "blocked_count": _int_value(row.get("blocked_count")),
                "evidence_request_count": _int_value(row.get("evidence_request_count")),
                "best_trial_id": best_trial_id,
                "best_rank": _int_value(row.get("best_rank")),
                "best_status": row.get("best_status"),
                "best_score": _float_value(row.get("best_score")),
                "best_net_return_sum": _float_value(row.get("best_net_return_sum")),
                "best_trade_count": _int_value(row.get("best_trade_count")),
                "best_active_days": _int_value(row.get("best_active_days")),
                "best_venue": row.get("best_venue"),
                "best_symbol": row.get("best_symbol"),
                "best_exit_variant_id": row.get("best_exit_variant_id"),
                "best_filter_variant_id": row.get("best_filter_variant_id"),
                "venues_tested": _bounded_unique_strings(list(row.get("venues_tested", []) or []), limit=limit),
                "symbols_tested": _bounded_unique_strings(list(row.get("symbols_tested", []) or []), limit=limit),
                "exit_variant_ids_tested": _bounded_unique_strings(
                    list(row.get("exit_variant_ids_tested", []) or []),
                    limit=limit,
                ),
                "filter_variant_ids_tested": _bounded_unique_strings(
                    list(row.get("filter_variant_ids_tested", []) or []),
                    limit=limit,
                ),
                "source_ids": _bounded_unique_strings(list(row.get("source_ids", []) or []), limit=limit),
                "blocked_reason_counts": _compact_count_map(row.get("blocked_reason_counts")),
                "rejected_reason_counts": _compact_count_map(row.get("rejected_reason_counts")),
                "all_reason_counts": _compact_count_map(row.get("all_reason_counts")),
                "best_rejection_reasons": [str(reason) for reason in rejection_reasons[:limit]],
            }
        )
    return samples, len(review_rows) > limit


def _agent_brief_next_action(payload: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if payload.get("iteration_status") == "blocked_by_preflight":
        reasons.append("preflight_blocked_all_trials")
        return "repair_preflight_blockers", reasons
    if int(payload.get("deduped_validation_request_count", 0) or 0) > 0:
        reasons.append("descriptor_only_validation_requests_available")
        return "review_descriptor_only_strict_validation_requests", reasons
    if int(payload.get("result_count", 0) or 0) <= 0:
        reasons.append("no_sandbox_results_written")
        return "inspect_blocked_or_empty_sandbox_iteration", reasons
    if int(payload.get("screened_count", 0) or 0) > 0:
        reasons.append("screened_results_without_validation_requests")
        return "review_screened_results_and_request_thresholds", reasons
    reasons.append("no_screened_results")
    return "review_rejections_and_falsified_hypotheses", reasons


def _agent_brief_artifact_paths(payload: dict[str, Any]) -> dict[str, Any]:
    path_keys = (
        "iteration_manifest_path",
        "iteration_steps_parquet_path",
        "archive_coverage_json_path",
        "archive_coverage_parquet_path",
        "archive_coverage_venue_expansion_gaps_parquet_path",
        "archive_coverage_source_audit_json_path",
        "archive_coverage_source_audit_parquet_path",
        "preflight_json_path",
        "preflight_parquet_path",
        "run_manifest_path",
        "analysis_report_path",
        "hypothesis_falsification_json_path",
        "hypothesis_falsification_parquet_path",
        "strict_validation_request_bundle_json_path",
        "strict_validation_request_bundle_parquet_path",
        "global_leaderboard_json_path",
        "global_leaderboard_parquet_path",
    )
    return {key: payload.get(key) for key in path_keys if payload.get(key)}


def _write_iteration_agent_brief(
    *,
    iteration_dir: Path,
    payload: dict[str, Any],
    steps: list[dict[str, Any]],
    archive_coverage: dict[str, Any],
    preflight: dict[str, Any],
    validation_bundle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    destination = iteration_dir / "agent_brief"
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / SANDBOX_ITERATION_AGENT_BRIEF_JSON_NAME
    parquet_path = destination / SANDBOX_ITERATION_AGENT_BRIEF_PARQUET_NAME
    next_action, reason_codes = _agent_brief_next_action(payload)
    coverage_blockers = _aggregate_coverage_blockers(archive_coverage)
    archive_blocker_samples = list(payload.get("archive_coverage_blocker_samples", []) or [])
    archive_blocker_samples_truncated = bool(payload.get("archive_coverage_blocker_samples_truncated", False))
    venue_expansion_gap_samples = list(payload.get("archive_coverage_venue_expansion_gap_samples", []) or [])
    venue_expansion_gap_samples_truncated = bool(
        payload.get("archive_coverage_venue_expansion_gap_samples_truncated", False)
    )
    venue_expansion_actionable_gap_count = int(
        payload.get("archive_coverage_venue_expansion_actionable_gap_count", 0) or 0
    )
    preflight_blocker_samples = list(payload.get("preflight_blocker_samples", []) or [])
    preflight_blocker_samples_truncated = bool(payload.get("preflight_blocker_samples_truncated", False))
    rejection_falsification_samples = list(payload.get("rejection_falsification_samples", []) or [])
    rejection_falsification_samples_truncated = bool(payload.get("rejection_falsification_samples_truncated", False))
    input_replay_context = dict(payload.get("input_replay_context", {}) or {})
    if int(payload.get("archive_coverage_blocked_descriptor_count", 0) or 0) > 0:
        reason_codes.append("archive_coverage_has_blocked_descriptors")
    if venue_expansion_actionable_gap_count > 0:
        reason_codes.append("archive_coverage_has_venue_expansion_gaps")
    if int(payload.get("preflight_blocked_trial_estimate", 0) or 0) > 0:
        reason_codes.append("preflight_has_blocked_trials")

    spec_payload = payload.get("spec", {})
    run_id = spec_payload.get("run_id") if isinstance(spec_payload, dict) else None
    top_validation_requests = _compact_validation_requests(validation_bundle)
    strategy_source = payload.get("strategy_source", {})
    strategy_source_summary = (
        _strategy_source_summary_from_source(strategy_source) if isinstance(strategy_source, dict) else {}
    )
    archive_source = payload.get("archive_source", {})
    archive_source_summary = (
        _archive_source_summary_from_source(archive_source) if isinstance(archive_source, dict) else {}
    )
    brief_identity = {
        "version": SANDBOX_ITERATION_AGENT_BRIEF_VERSION,
        "iteration_id": payload["iteration_id"],
        "iteration_status": payload["iteration_status"],
        "next_action": next_action,
        "reason_codes": sorted(set(reason_codes)),
        "strategy_source_summary": strategy_source_summary,
        "archive_source_summary": archive_source_summary,
        "archive_blocker_samples": archive_blocker_samples,
        "archive_blocker_samples_truncated": archive_blocker_samples_truncated,
        "venue_expansion_action_counts": dict(
            payload.get("archive_coverage_venue_expansion_action_counts", {}) or {}
        ),
        "venue_expansion_gap_samples": venue_expansion_gap_samples,
        "venue_expansion_gap_samples_truncated": venue_expansion_gap_samples_truncated,
        "preflight_blocker_samples": preflight_blocker_samples,
        "preflight_blocker_samples_truncated": preflight_blocker_samples_truncated,
        "rejection_falsification_samples": rejection_falsification_samples,
        "rejection_falsification_samples_truncated": rejection_falsification_samples_truncated,
        "input_replay_context": input_replay_context,
        "top_validation_request_ids": [
            request.get("descriptor_id") for request in top_validation_requests if request.get("descriptor_id") is not None
        ],
    }
    brief = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_agent_brief",
        "brief_version": SANDBOX_ITERATION_AGENT_BRIEF_VERSION,
        "brief_id": digest_payload(brief_identity, prefix="sbxagentbrief", length=24),
        "iteration_id": payload["iteration_id"],
        "run_id": run_id,
        "iteration_status": payload["iteration_status"],
        "next_action": next_action,
        "reason_codes": sorted(set(reason_codes)),
        "strict_validation_executed": False,
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
        "counts": {
            "strategy_count": int(payload.get("strategy_source", {}).get("strategy_count", 0) or 0)
            if isinstance(payload.get("strategy_source"), dict)
            else 0,
            "descriptor_count": int(payload.get("archive_source", {}).get("descriptor_count", 0) or 0)
            if isinstance(payload.get("archive_source"), dict)
            else 0,
            "archive_coverage_ready_descriptor_count": int(payload.get("archive_coverage_ready_descriptor_count", 0) or 0),
            "archive_coverage_blocked_descriptor_count": int(payload.get("archive_coverage_blocked_descriptor_count", 0) or 0),
            "venue_expansion_gap_row_count": int(
                payload.get("archive_coverage_venue_expansion_gap_row_count", 0) or 0
            ),
            "venue_expansion_actionable_gap_count": venue_expansion_actionable_gap_count,
            "venue_expansion_missing_target_count": int(
                payload.get("archive_coverage_venue_expansion_missing_target_count", 0) or 0
            ),
            "venue_expansion_blocked_target_count": int(
                payload.get("archive_coverage_venue_expansion_blocked_target_count", 0) or 0
            ),
            "venue_expansion_mixed_target_count": int(
                payload.get("archive_coverage_venue_expansion_mixed_target_count", 0) or 0
            ),
            "preflight_trial_estimate": int(payload.get("preflight_trial_estimate", 0) or 0),
            "preflight_runnable_trial_estimate": int(payload.get("preflight_runnable_trial_estimate", 0) or 0),
            "preflight_blocked_trial_estimate": int(payload.get("preflight_blocked_trial_estimate", 0) or 0),
            "result_count": int(payload.get("result_count", 0) or 0),
            "screened_count": int(payload.get("screened_count", 0) or 0),
            "rejected_count": int(payload.get("rejected_count", 0) or 0),
            "blocked_count": int(payload.get("blocked_count", 0) or 0),
            "evidence_request_count": int(payload.get("evidence_request_count", 0) or 0),
            "deduped_validation_request_count": int(payload.get("deduped_validation_request_count", 0) or 0),
            "leaderboard_hypothesis_count": int(payload.get("leaderboard_hypothesis_count", 0) or 0),
        },
        "window_selection": dict(payload.get("window_selection", {}) or {}),
        "input_replay_context": input_replay_context,
        "coverage_status_counts": dict(payload.get("archive_coverage_status_counts", {}) or {}),
        "archive_blocker_reason_counts": coverage_blockers,
        "venue_expansion_target_venues": list(
            payload.get("archive_coverage_venue_expansion_target_venues", []) or []
        ),
        "venue_expansion_status_counts": dict(
            payload.get("archive_coverage_venue_expansion_status_counts", {}) or {}
        ),
        "venue_expansion_action_counts": dict(
            payload.get("archive_coverage_venue_expansion_action_counts", {}) or {}
        ),
        "venue_expansion_gap_samples": venue_expansion_gap_samples,
        "venue_expansion_gap_samples_truncated": venue_expansion_gap_samples_truncated,
        "preflight_status_counts": dict(preflight.get("status_counts", {}) or {}),
        "preflight_blocker_reason_counts": dict(payload.get("preflight_blocker_reason_counts", {}) or {}),
        "falsification_decision_counts": dict(payload.get("falsification_decision_counts", {}) or {}),
        "strategy_source_summary": strategy_source_summary,
        "archive_source_summary": archive_source_summary,
        "archive_blocker_samples": archive_blocker_samples,
        "archive_blocker_samples_truncated": archive_blocker_samples_truncated,
        "preflight_blocker_samples": preflight_blocker_samples,
        "preflight_blocker_samples_truncated": preflight_blocker_samples_truncated,
        "rejection_falsification_samples": rejection_falsification_samples,
        "rejection_falsification_samples_truncated": rejection_falsification_samples_truncated,
        "top_archive_blockers": _top_counts(coverage_blockers),
        "top_preflight_blockers": _top_counts(payload.get("preflight_blocker_reason_counts", {})),
        "top_validation_requests": top_validation_requests,
        "artifact_paths": _agent_brief_artifact_paths(payload),
        "steps": [
            {
                "step_id": step.get("step_id"),
                "status": step.get("status"),
                "counts": step.get("counts", {}),
                "artifact_paths": step.get("artifact_paths", {}),
            }
            for step in steps
        ],
        "brief_json_path": str(json_path),
        "brief_parquet_path": str(parquet_path),
    }
    require_sandbox_boundary(brief, payload_name="sandbox_iteration_agent_brief")
    frame = pd.DataFrame([_row_for_parquet(brief)])
    frame.to_parquet(parquet_path, index=False)
    json_path.write_text(
        json.dumps(brief, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    return brief


def _agent_brief_manifest_fields(brief: dict[str, Any]) -> dict[str, Any]:
    return {
        "agent_brief_version": brief["brief_version"],
        "agent_brief_id": brief["brief_id"],
        "agent_brief_next_action": brief["next_action"],
        "agent_brief_reason_codes": brief["reason_codes"],
        "agent_brief_json_path": brief["brief_json_path"],
        "agent_brief_parquet_path": brief["brief_parquet_path"],
    }


def _skipped_step(
    *,
    iteration_id: str,
    step_id: str,
    preflight: dict[str, Any],
) -> dict[str, Any]:
    return _step(
        iteration_id=iteration_id,
        step_id=step_id,
        status="skipped_preflight_blocked",
        counts={
            "runnable_trial_estimate": preflight["runnable_trial_estimate"],
            "blocked_trial_estimate": preflight["blocked_trial_estimate"],
        },
    )


def _write_iteration_payload(
    *,
    iteration_dir: Path,
    payload: dict[str, Any],
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    iteration_dir.mkdir(parents=True, exist_ok=True)
    steps_path = iteration_dir / SANDBOX_ITERATION_STEPS_PARQUET_NAME
    manifest_path = iteration_dir / SANDBOX_ITERATION_MANIFEST_JSON_NAME
    frame = pd.DataFrame([_row_for_parquet(step) for step in steps])
    if frame.empty:
        frame = pd.DataFrame(columns=["iteration_id", "step_id", "status", *SANDBOX_BOUNDARY_FLAGS])
    frame.to_parquet(steps_path, index=False)
    final_payload = {
        **payload,
        "iteration_manifest_path": str(manifest_path),
        "iteration_steps_parquet_path": str(steps_path),
        "step_count": len(steps),
        "steps": steps,
    }
    require_sandbox_boundary(final_payload, payload_name="sandbox_iteration_manifest")
    manifest_path.write_text(
        json.dumps(final_payload, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    return final_payload


def _cached_artifact_path(raw_path: Any, *, manifest_path: Path, field_name: str) -> Path | None:
    if raw_path is None or raw_path == "":
        return None
    path = Path(str(raw_path)).expanduser()
    if not path.is_absolute():
        path = manifest_path.parent / path
    path = path.resolve()
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"cached sandbox iteration artifact missing for {field_name}: {path}")
    return path


def _require_cached_json_boundary(raw_path: Any, *, manifest_path: Path, field_name: str) -> None:
    path = _cached_artifact_path(raw_path, manifest_path=manifest_path, field_name=field_name)
    if path is None:
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"cached sandbox iteration JSON artifact must be an object for {field_name}: {path}")
    require_sandbox_boundary(payload, payload_name=f"sandbox_cached_iteration_artifact:{field_name}")


def _require_cached_file(raw_path: Any, *, manifest_path: Path, field_name: str) -> None:
    _cached_artifact_path(raw_path, manifest_path=manifest_path, field_name=field_name)


def _validate_existing_iteration_cache(payload: dict[str, Any], *, manifest_path: Path) -> None:
    for key in _CACHED_PREFLIGHT_REQUIRED_KEYS:
        if payload.get(key) is None or payload.get(key) == "":
            raise FileNotFoundError(f"cached sandbox iteration missing required artifact reference for {key}: {manifest_path}")
    for key in _CACHED_JSON_ARTIFACT_KEYS:
        _require_cached_json_boundary(payload.get(key), manifest_path=manifest_path, field_name=key)
    for key in _CACHED_FILE_ARTIFACT_KEYS:
        _require_cached_file(payload.get(key), manifest_path=manifest_path, field_name=key)

    if payload.get("iteration_status") != "completed":
        return
    for key in _CACHED_COMPLETED_REQUIRED_KEYS:
        if payload.get(key) is None or payload.get(key) == "":
            raise FileNotFoundError(f"cached sandbox iteration missing required completed artifact reference for {key}: {manifest_path}")
    run_manifest_path = _cached_artifact_path(
        payload.get("run_manifest_path"),
        manifest_path=manifest_path,
        field_name="run_manifest_path",
    )
    if run_manifest_path is None:
        raise FileNotFoundError(f"cached sandbox iteration completed without run_manifest_path: {manifest_path}")
    require_sandbox_artifact_integrity(run_manifest_path, payload_name="sandbox_iteration_cached_run_source")


def _load_existing_iteration(manifest_path: Path) -> dict[str, Any]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("sandbox iteration manifest must be a JSON object")
    require_sandbox_boundary(payload, payload_name="sandbox_existing_iteration_manifest")
    _validate_existing_iteration_cache(payload, manifest_path=manifest_path)
    payload = dict(payload)
    payload["reused_existing"] = True
    payload["cached_iteration_validation_status"] = "passed"
    return payload


def run_sandbox_agent_iteration(
    *,
    output_dir: str | Path,
    spec_path: str | Path | None = None,
    strategy_catalog_path: str | Path | None = None,
    catalog_roots: Sequence[str | Path] | None = None,
    venue_archives_path: str | Path | None = None,
    archive_roots: Sequence[str | Path] | None = None,
    run_id: str | None = None,
    window_start: str = DEFAULT_ITERATION_WINDOW_START,
    window_end: str = DEFAULT_ITERATION_WINDOW_END,
    window_preset: str | None = DEFAULT_ITERATION_WINDOW_PRESET,
    window_as_of_date: date | datetime | str | None = None,
    window_lookback_days: int = DEFAULT_ITERATION_RECENT_LOOKBACK_DAYS,
    holding_periods: Sequence[int] = (1, 2, 4, 8),
    round_trip_cost_bps: float = 8.0,
    min_trades: int = 5,
    max_evidence_requests: int = 10,
    rank_top_n: int = 100,
    min_request_score: float = 0.0,
    catalog_max_files: int = 5000,
    archive_max_files: int = 5000,
    archive_venue: str | None = None,
    archive_symbol: str | None = None,
    archive_data_family: str | None = None,
    archive_interval: str | None = None,
    leaderboard_max_runs: int = 5000,
    leaderboard_top_n: int = 100,
) -> dict[str, Any]:
    telemetry_started_at = _perf_counter()
    stage_timings: list[dict[str, Any]] = []
    memory_started_here = False
    if not tracemalloc.is_tracing():
        tracemalloc.start()
        memory_started_here = True
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    stage_started_at = _perf_counter()
    input_replay_context = _iteration_input_replay_context(
        output_root=output_root,
        spec_path=spec_path,
        strategy_catalog_path=strategy_catalog_path,
        catalog_roots=catalog_roots,
        venue_archives_path=venue_archives_path,
        archive_roots=archive_roots,
        run_id=run_id,
        window_start=window_start,
        window_end=window_end,
        window_preset=window_preset,
        window_as_of_date=window_as_of_date,
        window_lookback_days=window_lookback_days,
        holding_periods=holding_periods,
        round_trip_cost_bps=round_trip_cost_bps,
        min_trades=min_trades,
        max_evidence_requests=max_evidence_requests,
        rank_top_n=rank_top_n,
        min_request_score=min_request_score,
        catalog_max_files=catalog_max_files,
        archive_max_files=archive_max_files,
        archive_venue=archive_venue,
        archive_symbol=archive_symbol,
        archive_data_family=archive_data_family,
        archive_interval=archive_interval,
        leaderboard_max_runs=leaderboard_max_runs,
        leaderboard_top_n=leaderboard_top_n,
    )
    stage_timings.append(
        _stage_telemetry(
            stage_id="input_replay_context",
            started_at=stage_started_at,
            status="completed",
        )
    )
    stage_started_at = _perf_counter()
    strategies, strategy_source = _load_or_materialize_strategies(
        strategy_catalog_path=strategy_catalog_path,
        catalog_roots=catalog_roots,
        output_root=output_root,
        max_files=catalog_max_files,
    )
    stage_timings.append(
        _stage_telemetry(
            stage_id="strategy_catalog_input",
            started_at=stage_started_at,
            status=str(strategy_source["mode"]),
            counts={
                "strategy_count": len(strategies),
                **{key: value for key, value in strategy_source.items() if key.endswith("_count")},
            },
        )
    )
    stage_started_at = _perf_counter()
    if spec_path is not None:
        preset = (window_preset or DEFAULT_ITERATION_WINDOW_PRESET).strip().lower()
        if preset not in {"", "explicit"}:
            raise ValueError("sandbox iteration window_preset cannot override a spec_path")
        if window_as_of_date is not None:
            raise ValueError("sandbox iteration window_as_of_date cannot override a spec_path")
        if int(window_lookback_days) != DEFAULT_ITERATION_RECENT_LOOKBACK_DAYS:
            raise ValueError("sandbox iteration window_lookback_days cannot override a spec_path")
        spec = load_sandbox_run_spec(Path(spec_path))
        include_run_id = True
        window_selection = {
            "window_selection_mode": "spec_path",
            "window_preset": "spec_path",
            "window_as_of_date": None,
            "window_lookback_days": None,
            "resolved_window_start": spec.data_window.start.isoformat(),
            "resolved_window_end": spec.data_window.end.isoformat(),
            "window_start_clipped_to_min_date": False,
            "min_sandbox_date": MIN_SANDBOX_DATE.isoformat(),
        }
    else:
        data_window, window_selection = _resolve_iteration_window(
            window_start=window_start,
            window_end=window_end,
            window_preset=window_preset,
            window_as_of_date=window_as_of_date,
            window_lookback_days=window_lookback_days,
        )
        generated_spec = _default_spec(
            run_id=run_id or "sandbox-agent-iteration-run",
            data_window=data_window,
            holding_periods=holding_periods,
            round_trip_cost_bps=round_trip_cost_bps,
            min_trades=min_trades,
            max_evidence_requests=max_evidence_requests,
            rank_top_n=rank_top_n,
        )
        include_run_id = run_id is not None
        spec = generated_spec
    stage_timings.append(
        _stage_telemetry(
            stage_id="run_spec_window",
            started_at=stage_started_at,
            status=str(window_selection["window_selection_mode"]),
            counts={
                "holding_period_count": len(spec.holding_periods),
                "window_start": spec.data_window.start.isoformat(),
                "window_end": spec.data_window.end.isoformat(),
            },
        )
    )
    stage_started_at = _perf_counter()
    venues, archive_source = _load_or_build_archives(
        venue_archives_path=venue_archives_path,
        archive_roots=archive_roots,
        output_root=output_root,
        venue=archive_venue,
        symbol=archive_symbol,
        data_family=archive_data_family,
        interval=archive_interval,
        max_files=archive_max_files,
        requested_window=spec.data_window if archive_roots else None,
    )
    stage_timings.append(
        _stage_telemetry(
            stage_id="venue_archive_input",
            started_at=stage_started_at,
            status=str(archive_source["mode"]),
            counts={
                "descriptor_count": len(venues),
                **{key: value for key, value in archive_source.items() if key.endswith("_count")},
            },
        )
    )

    iteration_id = _iteration_id(
        strategies=strategies,
        venues=venues,
        spec=spec,
        include_run_id=include_run_id,
        window_selection=window_selection,
        min_request_score=min_request_score,
        strategy_source=strategy_source,
        archive_source=archive_source,
    )
    if spec_path is None and run_id is None:
        spec = replace(spec, run_id=f"{iteration_id}-run")
    iteration_dir = output_root / iteration_id
    existing_manifest = iteration_dir / SANDBOX_ITERATION_MANIFEST_JSON_NAME
    if existing_manifest.exists():
        cached_payload = _load_existing_iteration(existing_manifest)
        if memory_started_here:
            tracemalloc.stop()
        return cached_payload

    market_data_cache = SandboxMarketDataCache()
    steps = [
        _step(
            iteration_id=iteration_id,
            step_id="strategy_catalog",
            status=str(strategy_source["mode"]),
            artifact_paths={key: value for key, value in strategy_source.items() if key.endswith("_path")},
            counts={"strategy_count": len(strategies), **{key: value for key, value in strategy_source.items() if key.endswith("_count")}},
        ),
        _step(
            iteration_id=iteration_id,
            step_id="venue_archive_manifest",
            status=str(archive_source["mode"]),
            artifact_paths={key: value for key, value in archive_source.items() if key.endswith("_path")},
            counts={"descriptor_count": len(venues), **{key: value for key, value in archive_source.items() if key.endswith("_count")}},
        ),
    ]
    stage_started_at = _perf_counter()
    archive_coverage = summarize_sandbox_archive_coverage(
        archive_source["venue_archive_manifest_path"],
        output_dir=iteration_dir / "archive_coverage",
        requested_window=spec.data_window,
        market_data_cache=market_data_cache,
    )
    stage_timings.append(
        _stage_telemetry(
            stage_id="archive_coverage_matrix",
            started_at=stage_started_at,
            status="completed",
            counts=_archive_coverage_step_counts(archive_coverage),
        )
    )
    steps.append(
        _step(
            iteration_id=iteration_id,
            step_id="archive_coverage_matrix",
            status="completed",
            artifact_paths=_archive_coverage_artifact_paths(archive_coverage),
            counts=_archive_coverage_step_counts(archive_coverage),
        )
    )
    stage_started_at = _perf_counter()
    preflight = preflight_sandbox_compatibility(
        spec=spec,
        strategies=strategies,
        venues=venues,
        output_dir=iteration_dir / "compatibility_preflight",
        market_data_cache=market_data_cache,
    )
    preflight_status = "runnable" if int(preflight["runnable_trial_estimate"]) > 0 else "blocked"
    stage_timings.append(
        _stage_telemetry(
            stage_id="compatibility_preflight",
            started_at=stage_started_at,
            status=preflight_status,
            counts=_preflight_step_counts(preflight),
        )
    )
    steps.append(
        _step(
            iteration_id=iteration_id,
            step_id="compatibility_preflight",
            status=preflight_status,
            artifact_paths=_preflight_artifact_paths(preflight),
            counts=_preflight_step_counts(preflight),
        )
    )
    if int(preflight["runnable_trial_estimate"]) <= 0:
        for step_id in (
            "archive_sweep",
            "analysis_summary",
            "hypothesis_falsification",
            "strict_validation_request_bundle",
            "global_leaderboard",
        ):
            steps.append(_skipped_step(iteration_id=iteration_id, step_id=step_id, preflight=preflight))
        payload = {
            **sandbox_boundary_metadata(),
            "artifact_family": "rapid_strategy_iteration_sandbox_agent_iteration",
            "iteration_id": iteration_id,
            "iteration_dir": str(iteration_dir),
            "output_root": str(output_root),
            "iteration_status": "blocked_by_preflight",
            "reused_existing": False,
            "strict_validation_executed": False,
            "candidate_pack_written": False,
            "candidate_pack_paths": [],
            "strategy_source": strategy_source,
            "archive_source": archive_source,
            "input_replay_context": input_replay_context,
            "window_selection": window_selection,
            "spec": spec.to_payload(),
            **_archive_coverage_manifest_fields(archive_coverage),
            **_preflight_manifest_fields(preflight),
            "run_dir": None,
            "run_manifest_path": None,
            "analysis_report_path": None,
            "hypothesis_falsification_json_path": None,
            "hypothesis_falsification_parquet_path": None,
            "strict_validation_request_bundle_json_path": None,
            "strict_validation_request_bundle_parquet_path": None,
            "global_leaderboard_json_path": None,
            "global_leaderboard_parquet_path": None,
            "result_count": 0,
            "screened_count": 0,
            "rejected_count": 0,
            "blocked_count": 0,
            "evidence_request_count": 0,
            "deduped_validation_request_count": 0,
            "leaderboard_hypothesis_count": 0,
            "falsification_decision_counts": {},
            "rejection_falsification_samples": [],
            "rejection_falsification_samples_truncated": False,
        }
        payload["iteration_manifest_path"] = str(iteration_dir / SANDBOX_ITERATION_MANIFEST_JSON_NAME)
        payload["iteration_steps_parquet_path"] = str(iteration_dir / SANDBOX_ITERATION_STEPS_PARQUET_NAME)
        payload["throughput_telemetry"] = _throughput_telemetry(
            iteration_id=iteration_id,
            total_started_at=telemetry_started_at,
            stage_timings=stage_timings,
            market_data_cache=market_data_cache,
        )
        stage_started_at = _perf_counter()
        agent_brief = _write_iteration_agent_brief(
            iteration_dir=iteration_dir,
            payload=payload,
            steps=steps,
            archive_coverage=archive_coverage,
            preflight=preflight,
        )
        stage_timings.append(
            _stage_telemetry(
                stage_id="agent_brief",
                started_at=stage_started_at,
                status="completed",
                counts=agent_brief["counts"],
            )
        )
        payload["throughput_telemetry"] = _throughput_telemetry(
            iteration_id=iteration_id,
            total_started_at=telemetry_started_at,
            stage_timings=stage_timings,
            market_data_cache=market_data_cache,
        )
        steps.append(
            _step(
                iteration_id=iteration_id,
                step_id="agent_brief",
                status="completed",
                artifact_paths={
                    "agent_brief_json_path": agent_brief["brief_json_path"],
                    "agent_brief_parquet_path": agent_brief["brief_parquet_path"],
                },
                counts=agent_brief["counts"],
            )
        )
        payload.update(_agent_brief_manifest_fields(agent_brief))
        require_sandbox_boundary(payload, payload_name="sandbox_iteration_payload")
        stage_started_at = _perf_counter()
        final_payload = _write_iteration_payload(iteration_dir=iteration_dir, payload=payload, steps=steps)
        stage_timings.append(
            _stage_telemetry(
                stage_id="iteration_manifest_write",
                started_at=stage_started_at,
                status="completed",
                counts={"step_count": len(steps)},
            )
        )
        final_payload["throughput_telemetry"] = _throughput_telemetry(
            iteration_id=iteration_id,
            total_started_at=telemetry_started_at,
            stage_timings=stage_timings,
            market_data_cache=market_data_cache,
        )
        final_payload = _write_iteration_payload(iteration_dir=iteration_dir, payload=final_payload, steps=steps)
        if memory_started_here:
            tracemalloc.stop()
        return final_payload

    stage_started_at = _perf_counter()
    result = run_sandbox_archive_sweep(
        spec=spec,
        strategies=strategies,
        venues=venues,
        output_root=iteration_dir,
        min_request_score=min_request_score,
        market_data_cache=market_data_cache,
    )
    stage_timings.append(
        _stage_telemetry(
            stage_id="archive_sweep",
            started_at=stage_started_at,
            status="completed",
            counts={
                "result_count": len(result.results),
                "evidence_request_count": len(result.evidence_requests),
            },
        )
    )
    steps.append(
        _step(
            iteration_id=iteration_id,
            step_id="archive_sweep",
            status="completed",
            artifact_paths=result.artifacts.to_payload(),
            counts={
                "result_count": len(result.results),
                "evidence_request_count": len(result.evidence_requests),
            },
        )
    )
    stage_started_at = _perf_counter()
    analysis = summarize_sandbox_run(result.artifacts.run_dir)
    stage_timings.append(
        _stage_telemetry(
            stage_id="analysis_summary",
            started_at=stage_started_at,
            status="completed",
            counts={
                "result_count": analysis["result_count"],
                "evidence_request_count": analysis["evidence_request_count"],
            },
        )
    )
    steps.append(
        _step(
            iteration_id=iteration_id,
            step_id="analysis_summary",
            status="completed",
            artifact_paths={"analysis_report_path": analysis["analysis_report_path"]},
            counts={"result_count": analysis["result_count"], "evidence_request_count": analysis["evidence_request_count"]},
        )
    )
    stage_started_at = _perf_counter()
    falsification = summarize_sandbox_hypotheses(result.artifacts.run_dir)
    rejection_falsification_samples, rejection_falsification_samples_truncated = _rejection_falsification_sample_payload(
        falsification,
        analysis,
    )
    stage_timings.append(
        _stage_telemetry(
            stage_id="hypothesis_falsification",
            started_at=stage_started_at,
            status="completed",
            counts={"hypothesis_count": falsification["hypothesis_count"]},
        )
    )
    steps.append(
        _step(
            iteration_id=iteration_id,
            step_id="hypothesis_falsification",
            status="completed",
            artifact_paths={
                "hypothesis_falsification_json_path": falsification["hypothesis_falsification_json_path"],
                "hypothesis_falsification_parquet_path": falsification["hypothesis_falsification_parquet_path"],
            },
            counts={"hypothesis_count": falsification["hypothesis_count"]},
        )
    )
    stage_started_at = _perf_counter()
    validation_bundle = export_sandbox_validation_request_bundle(result.artifacts.run_dir)
    stage_timings.append(
        _stage_telemetry(
            stage_id="strict_validation_request_bundle",
            started_at=stage_started_at,
            status="descriptor_only",
            counts={
                "request_count": validation_bundle["request_count"],
                "deduped_request_count": validation_bundle["deduped_request_count"],
            },
        )
    )
    steps.append(
        _step(
            iteration_id=iteration_id,
            step_id="strict_validation_request_bundle",
            status="descriptor_only",
            artifact_paths={
                "bundle_json_path": validation_bundle["bundle_json_path"],
                "bundle_parquet_path": validation_bundle["bundle_parquet_path"],
            },
            counts={
                "request_count": validation_bundle["request_count"],
                "deduped_request_count": validation_bundle["deduped_request_count"],
            },
        )
    )
    stage_started_at = _perf_counter()
    leaderboard = build_sandbox_global_leaderboard(
        output_root,
        output_dir=iteration_dir / "global_leaderboard",
        max_runs=leaderboard_max_runs,
        top_n=leaderboard_top_n,
    )
    stage_timings.append(
        _stage_telemetry(
            stage_id="global_leaderboard",
            started_at=stage_started_at,
            status="completed",
            counts={"hypothesis_count": leaderboard["hypothesis_count"]},
        )
    )
    steps.append(
        _step(
            iteration_id=iteration_id,
            step_id="global_leaderboard",
            status="completed",
            artifact_paths={
                "leaderboard_json_path": leaderboard["leaderboard_json_path"],
                "leaderboard_parquet_path": leaderboard["leaderboard_parquet_path"],
            },
            counts={
                "source_run_count": leaderboard["source_run_count"],
                "hypothesis_count": leaderboard["hypothesis_count"],
            },
        )
    )

    payload = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_agent_iteration",
        "iteration_id": iteration_id,
        "iteration_dir": str(iteration_dir),
        "output_root": str(output_root),
        "iteration_status": "completed",
        "reused_existing": False,
        "strict_validation_executed": False,
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
        "strategy_source": strategy_source,
        "archive_source": archive_source,
        "input_replay_context": input_replay_context,
        "window_selection": window_selection,
        "spec": spec.to_payload(),
        **_archive_coverage_manifest_fields(archive_coverage),
        **_preflight_manifest_fields(preflight),
        "run_dir": str(result.artifacts.run_dir),
        "run_manifest_path": str(result.artifacts.manifest_path),
        "analysis_report_path": analysis["analysis_report_path"],
        "hypothesis_falsification_json_path": falsification["hypothesis_falsification_json_path"],
        "hypothesis_falsification_parquet_path": falsification["hypothesis_falsification_parquet_path"],
        "strict_validation_request_bundle_json_path": validation_bundle["bundle_json_path"],
        "strict_validation_request_bundle_parquet_path": validation_bundle["bundle_parquet_path"],
        "global_leaderboard_json_path": leaderboard["leaderboard_json_path"],
        "global_leaderboard_parquet_path": leaderboard["leaderboard_parquet_path"],
        "result_count": len(result.results),
        "screened_count": sum(1 for item in result.results if item.status == "screened"),
        "rejected_count": sum(1 for item in result.results if item.status == "rejected"),
        "blocked_count": sum(1 for item in result.results if item.status == "blocked"),
        "evidence_request_count": len(result.evidence_requests),
        "deduped_validation_request_count": validation_bundle["deduped_request_count"],
        "leaderboard_hypothesis_count": leaderboard["hypothesis_count"],
        "falsification_decision_counts": dict(falsification.get("decision_counts", {}) or {}),
        "rejection_falsification_samples": rejection_falsification_samples,
        "rejection_falsification_samples_truncated": rejection_falsification_samples_truncated,
    }
    payload["iteration_manifest_path"] = str(iteration_dir / SANDBOX_ITERATION_MANIFEST_JSON_NAME)
    payload["iteration_steps_parquet_path"] = str(iteration_dir / SANDBOX_ITERATION_STEPS_PARQUET_NAME)
    payload["throughput_telemetry"] = _throughput_telemetry(
        iteration_id=iteration_id,
        total_started_at=telemetry_started_at,
        stage_timings=stage_timings,
        market_data_cache=market_data_cache,
    )
    stage_started_at = _perf_counter()
    agent_brief = _write_iteration_agent_brief(
        iteration_dir=iteration_dir,
        payload=payload,
        steps=steps,
        archive_coverage=archive_coverage,
        preflight=preflight,
        validation_bundle=validation_bundle,
    )
    stage_timings.append(
        _stage_telemetry(
            stage_id="agent_brief",
            started_at=stage_started_at,
            status="completed",
            counts=agent_brief["counts"],
        )
    )
    payload["throughput_telemetry"] = _throughput_telemetry(
        iteration_id=iteration_id,
        total_started_at=telemetry_started_at,
        stage_timings=stage_timings,
        market_data_cache=market_data_cache,
    )
    steps.append(
        _step(
            iteration_id=iteration_id,
            step_id="agent_brief",
            status="completed",
            artifact_paths={
                "agent_brief_json_path": agent_brief["brief_json_path"],
                "agent_brief_parquet_path": agent_brief["brief_parquet_path"],
            },
            counts=agent_brief["counts"],
        )
    )
    payload.update(_agent_brief_manifest_fields(agent_brief))
    require_sandbox_boundary(payload, payload_name="sandbox_iteration_payload")
    stage_started_at = _perf_counter()
    final_payload = _write_iteration_payload(iteration_dir=iteration_dir, payload=payload, steps=steps)
    stage_timings.append(
        _stage_telemetry(
            stage_id="iteration_manifest_write",
            started_at=stage_started_at,
            status="completed",
            counts={"step_count": len(steps)},
        )
    )
    final_payload["throughput_telemetry"] = _throughput_telemetry(
        iteration_id=iteration_id,
        total_started_at=telemetry_started_at,
        stage_timings=stage_timings,
        market_data_cache=market_data_cache,
    )
    final_payload = _write_iteration_payload(iteration_dir=iteration_dir, payload=final_payload, steps=steps)
    if memory_started_here:
        tracemalloc.stop()
    return final_payload
