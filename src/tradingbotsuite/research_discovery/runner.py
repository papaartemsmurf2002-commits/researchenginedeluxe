from __future__ import annotations

import json
import gc
import math
import os
import re
import threading
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Mapping

import pandas as pd
import numpy as np

from tradingbotsuite.backtesting.splits import LabelSpec, build_purged_walk_forward_splits
from tradingbotsuite.config import AppConfig
from tradingbotsuite.data.historical_fixture_pack import (
    assert_valid_historical_fixture_pack_manifest,
    resolve_fixture_pack_cycle_dataset_path,
)
from tradingbotsuite.features.builders import materialize_registered_feature_set
from tradingbotsuite.research_discovery.event_accounting import account_independent_events, account_independent_events_arrays
from tradingbotsuite.research_discovery.feature_sets import (
    DiscoveryFeatureColumnSet,
    load_feature_column_set_manifest,
    validate_feature_column_set_manifest,
)
from tradingbotsuite.research_discovery.hmm_materialization import (
    HMM_POSTERIOR_COLUMNS,
    HmmMaterializationResult,
    HmmMaterializationSpec,
    materialize_no_regime_baseline,
    materialize_split_safe_hmm_regimes,
    write_hmm_materialization_artifacts,
)
from tradingbotsuite.research_discovery.knn_study import (
    KnnStudyResult,
    KnnStudySpec,
    materialize_regime_local_knn_predictions,
    write_knn_study_artifacts,
)
from tradingbotsuite.research_discovery.manifests import discovery_manifest_payload
from tradingbotsuite.research_discovery.neighbor_cache import ExactNeighborCache
from tradingbotsuite.research_discovery.snapshots import atomic_write_json, iso_utc, utc_now, write_snapshot
from tradingbotsuite.research_discovery.spec import (
    DiscoveryRunSpec,
    DiscoveryTrialTemplate,
    discovery_search_space_summary,
    generated_trial_templates,
    regime_mode_settings,
    resolve_discovery_paths,
)
from tradingbotsuite.research_discovery.state import (
    DiscoveryRunState,
    DiscoveryTrialRecord,
    read_run_state,
    read_trial_record,
    write_run_state,
    write_trial_record,
)
from tradingbotsuite.research_discovery.telemetry import (
    build_compute_telemetry,
    start_telemetry_session,
    stop_telemetry_session,
)


LEDGER_COLUMNS = (
    "run_id",
    "trial_id",
    "attempt_id",
    "trial_index",
    "candidate_id",
    "candidate_family",
    "ledger_kind",
    "score",
    "blocker_code",
    "filter_blocker_code",
    "research_only",
    "observe_only",
    "promotion_ready",
    "discovery_score_policy_version",
    "feature_column_set_id",
    "hmm_state_count",
    "regime_mode",
    "regime_detector_type",
    "regime_model_backend",
    "regime_gate_enabled",
    "same_regime_neighbor_pool_enabled",
    "true_hmm_backend_used",
    "label_horizon",
    "distance_metric",
    "k",
    "min_neighbor_count",
    "trade_count",
    "accepted_bar_count",
    "independent_event_count",
    "suppressed_overlap_count",
    "overlap_ratio",
    "event_signal_rate",
    "side_collapse_ratio",
    "near_signal_ceiling",
    "long_independent_event_count",
    "short_independent_event_count",
    "event_spacing_bars",
    "signal_rate",
    "realized_expectancy",
    "independent_event_expectancy",
    "accepted_prediction_count",
    "evaluated_prediction_count",
    "legacy_density_score",
    "discovery_screen_score_v2",
    "signal_rate_ceiling_penalty",
    "overlap_penalty",
    "side_collapse_penalty",
    "final_score",
    "record_sha256",
)
LEDGER_INT_COLUMNS = frozenset(
    {
        "trial_index",
        "hmm_state_count",
        "k",
        "min_neighbor_count",
        "trade_count",
        "accepted_bar_count",
        "independent_event_count",
        "suppressed_overlap_count",
        "long_independent_event_count",
        "short_independent_event_count",
        "event_spacing_bars",
        "accepted_prediction_count",
        "evaluated_prediction_count",
    }
)
LEDGER_FLOAT_COLUMNS = frozenset(
    {
        "score",
        "overlap_ratio",
        "event_signal_rate",
        "side_collapse_ratio",
        "signal_rate",
        "realized_expectancy",
        "independent_event_expectancy",
        "legacy_density_score",
        "discovery_screen_score_v2",
        "signal_rate_ceiling_penalty",
        "overlap_penalty",
        "side_collapse_penalty",
        "final_score",
    }
)
LEDGER_BOOL_COLUMNS = frozenset(
    {
        "research_only",
        "observe_only",
        "promotion_ready",
        "regime_gate_enabled",
        "same_regime_neighbor_pool_enabled",
        "true_hmm_backend_used",
        "near_signal_ceiling",
    }
)
DISCOVERY_SCORE_POLICY_VERSION = "discovery-screen-score-v3-effective-feature-columns"
REAL_DISCOVERY_TRIAL_KIND = "regime_knn_entry_discovery"
LEGACY_REAL_DISCOVERY_TRIAL_KIND = "hmm_knn_entry_discovery"
REAL_DISCOVERY_TRIAL_KINDS = {REAL_DISCOVERY_TRIAL_KIND, LEGACY_REAL_DISCOVERY_TRIAL_KIND}
REAL_DISCOVERY_PROCESS_WORKER_CAP_ENV = "TBS_DISCOVERY_REAL_PROCESS_MAX_WORKERS"
REAL_DISCOVERY_PROCESS_CHUNK_SIZE_ENV = "TBS_DISCOVERY_REAL_PROCESS_CHUNK_SIZE"
REAL_DISCOVERY_PREFLIGHT_TRIALS_ENV = "TBS_DISCOVERY_REAL_PREFLIGHT_TRIALS"
REAL_DISCOVERY_PREFLIGHT_MIN_PLANNED_TRIALS_ENV = "TBS_DISCOVERY_REAL_PREFLIGHT_MIN_PLANNED_TRIALS"
DISCOVERY_RESUME_FULL_RECORD_LOAD_LIMIT_ENV = "TBS_DISCOVERY_RESUME_FULL_RECORD_LOAD_LIMIT"
DEFAULT_REAL_DISCOVERY_PROCESS_WORKER_CAP = 8
DEFAULT_REAL_DISCOVERY_PROCESS_CHUNK_SIZE = 8
DEFAULT_REAL_DISCOVERY_PREFLIGHT_TRIALS = 24
DEFAULT_REAL_DISCOVERY_PREFLIGHT_MIN_PLANNED_TRIALS = 1_000
DEFAULT_DISCOVERY_RESUME_FULL_RECORD_LOAD_LIMIT = 100_000
_PROCESS_DISCOVERY_SPEC: DiscoveryRunSpec | None = None
_PROCESS_DISCOVERY_CONTEXT: Any = None
_PROCESS_DISCOVERY_OUTPUT_DIR: Path | None = None
_PROCESS_DISCOVERY_CONTEXT_INITIALIZATION_SECONDS: float | None = None

LABEL_HORIZON_RE = re.compile(r"^\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>bars?|b|m|min|minute|minutes|h|hour|hours|d|day|days)\s*$")
REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True, slots=True)
class DiscoveryRunResult:
    output_dir: Path
    manifest_path: Path
    resolved_spec_path: Path
    run_state_path: Path
    interesting_candidates_path: Path
    blocked_candidates_path: Path
    filter_blockers_path: Path
    snapshot_paths: tuple[Path, ...]


@dataclass(frozen=True, slots=True)
class _WorkerPlan:
    configured_executor: str
    executor: str
    configured_max_workers: int
    requested_workers: int
    active_workers: int
    real_discovery_requested: bool
    process_worker_cap: int | None = None
    process_worker_cap_source: str = ""
    process_worker_cap_applied: bool = False
    reason: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "configured_executor": self.configured_executor,
            "executor": self.executor,
            "configured_max_workers": int(self.configured_max_workers),
            "requested_workers": int(self.requested_workers),
            "active_workers": int(self.active_workers),
            "real_discovery_requested": bool(self.real_discovery_requested),
            "process_worker_cap": self.process_worker_cap,
            "process_worker_cap_source": self.process_worker_cap_source,
            "process_worker_cap_applied": bool(self.process_worker_cap_applied),
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class _ResumeCatalog:
    records: dict[str, DiscoveryTrialRecord]
    state: DiscoveryRunState
    fully_hydrated: bool
    mode: str
    trial_file_count: int
    recovered_trial_file_count: int
    full_record_load_limit: int


@dataclass(frozen=True, slots=True)
class _LedgerSummary:
    counts: dict[str, int]
    observed_trial_regime_modes: tuple[str, ...] = ()
    observed_trial_regime_detector_types: tuple[str, ...] = ()
    observed_trial_regime_model_backends: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _ProcessChunkResult:
    records: tuple[DiscoveryTrialRecord, ...]
    worker_pid: int
    chunk_size: int
    chunk_wall_seconds: float
    chunk_process_cpu_seconds: float
    worker_context_initialization_seconds: float | None


class _ArtifactWriteObserver:
    def __init__(self) -> None:
        self._paths: set[Path] = set()

    def record(self, value: Any) -> None:
        if value is None:
            return
        if isinstance(value, (str, Path)):
            self._record_path(Path(value))
            return
        if isinstance(value, Mapping):
            for item in value.values():
                self.record(item)
            return
        if isinstance(value, (list, tuple, set, frozenset)):
            for item in value:
                self.record(item)

    def _record_path(self, path: Path) -> None:
        try:
            resolved = path.expanduser().resolve()
        except OSError:
            return
        if resolved.is_file():
            self._paths.add(resolved)

    def counts(self) -> dict[str, Any]:
        byte_count = 0
        existing_paths = 0
        for path in sorted(self._paths):
            try:
                byte_count += int(path.stat().st_size)
                existing_paths += 1
            except OSError:
                continue
        return {
            "artifact_file_count": int(existing_paths),
            "artifact_bytes_written": int(byte_count),
            "artifact_count_scope": "observed_parent_writes_this_call",
            "artifact_count_strategy": "recorded_artifact_write_paths_no_recursive_scan",
        }


class _NullExecutor:
    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        return False


def run_discovery(
    *,
    spec_path: Path,
    app_config: AppConfig | None = None,
    resume: bool = False,
    stop_after_trials: int | None = None,
    clock: Callable[[], datetime] | None = None,
) -> DiscoveryRunResult:
    telemetry_session = start_telemetry_session()
    started = telemetry_session.wall_started
    stage_wall_seconds: dict[str, float] = {}
    artifact_write_seconds = 0.0
    artifact_observer = _ArtifactWriteObserver()
    process_chunk_results: list[_ProcessChunkResult] = []
    stage_started = time.perf_counter()
    now = clock or utc_now
    spec_path = Path(spec_path).expanduser().resolve()
    spec = DiscoveryRunSpec.from_path(spec_path)
    resolved_paths = resolve_discovery_paths(spec, app_config=app_config)
    feature_column_set_evidence = _feature_column_set_evidence(spec)
    output_dir = resolved_paths.output_dir
    resolved_spec_path = output_dir / "discovery_spec_resolved.json"
    state_path = output_dir / "run_state.json"
    manifest_path = output_dir / "discovery_run_manifest.json"
    ledger_root = output_dir / "candidate_ledgers"
    interesting_path = ledger_root / "interesting_candidates.parquet"
    blocked_path = ledger_root / "blocked_candidates.parquet"
    filter_blockers_path = ledger_root / "filter_blockers.parquet"
    stage_wall_seconds["spec_and_path_resolution"] = time.perf_counter() - stage_started

    def record_artifact_write(operation: Callable[[], Any], paths: Any = None) -> Any:
        nonlocal artifact_write_seconds
        started_at = time.perf_counter()
        try:
            result = operation()
            artifact_observer.record(paths)
            artifact_observer.record(result)
            return result
        finally:
            artifact_write_seconds += time.perf_counter() - started_at

    if output_dir.exists() and not state_path.exists() and any(output_dir.iterdir()):
        raise ValueError(f"discovery output directory is not empty and has no run_state.json: {output_dir}")

    stage_started = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    for directory in (output_dir / "trials", output_dir / "snapshots", ledger_root):
        directory.mkdir(parents=True, exist_ok=True)

    resolved_spec_payload = spec.to_payload()
    if state_path.exists():
        state = read_run_state(state_path)
        if state.run_id != spec.run_id:
            raise ValueError("existing run_state.json belongs to a different run_id")
        if state.status == "completed":
            if not (
                resume
                and _completed_run_needs_artifact_repair(
                    manifest_path=manifest_path,
                    interesting_path=interesting_path,
                    blocked_path=blocked_path,
                    filter_blockers_path=filter_blockers_path,
                    completed_count=len(state.completed_trial_ids),
                )
            ):
                raise ValueError("completed discovery runs refuse overwrite")
        if not resume:
            raise ValueError("existing incomplete discovery run requires resume=True")
        _assert_resolved_spec_unchanged(resolved_spec_path, resolved_spec_payload)
    else:
        state = DiscoveryRunState.new(run_id=spec.run_id, created_at_utc=iso_utc(now()))
        record_artifact_write(lambda: atomic_write_json(resolved_spec_path, resolved_spec_payload), resolved_spec_path)
        record_artifact_write(lambda: write_run_state(state_path, state), state_path)

    templates = generated_trial_templates(spec)
    real_discovery_requested = _real_discovery_requested(spec, templates)
    resume_catalog = _load_resume_catalog(
        output_dir / "trials",
        run_id=spec.run_id,
        state=state,
        updated_at_utc=iso_utc(now()),
    )
    existing_records = resume_catalog.records
    state = resume_catalog.state
    record_artifact_write(lambda: write_run_state(state_path, state), state_path)
    stage_wall_seconds["resume_state_merge"] = time.perf_counter() - stage_started

    completed_ids = set(state.completed_trial_ids)
    executed_this_call = 0
    snapshot_paths: list[Path] = []
    batch_completed = 0
    ledgers_complete = resume_catalog.fully_hydrated
    preflight_summary: dict[str, Any] = {
        "enabled": False,
        "status": "not_run",
        "trial_count": 0,
        "failed_trial_count": 0,
        "reason": "not_required",
    }
    preflight_blocked = False

    if ledgers_complete:
        record_artifact_write(
            lambda: _write_ledgers(
                records=_ordered_records(existing_records.values()),
                interesting_path=interesting_path,
                blocked_path=blocked_path,
                filter_blockers_path=filter_blockers_path,
            ),
            (interesting_path, blocked_path, filter_blockers_path),
        )
    last_snapshot_at = now()
    initial_snapshot = record_artifact_write(
        lambda: _snapshot(
            output_dir,
            spec=spec,
            state=state,
            records=existing_records,
            counts=_counts_for_state(state, existing_records, complete=ledgers_complete),
            counts_scope=_counts_scope(ledgers_complete),
            sequence=state.snapshot_count + 1,
            created_at=last_snapshot_at,
        )
    )
    snapshot_paths.append(initial_snapshot)
    state = state.with_snapshot(path=initial_snapshot, updated_at_utc=iso_utc(now()))
    record_artifact_write(lambda: write_run_state(state_path, state), state_path)

    pending_trials = [
        (index, template)
        for index, template in enumerate(templates, start=1)
        if template.trial_id not in completed_ids
    ]
    if real_discovery_requested:
        pending_trials = _cache_affinity_ordered_trials(
            pending_trials,
            block_size=DEFAULT_REAL_DISCOVERY_PROCESS_CHUNK_SIZE,
        )
    if stop_after_trials is not None:
        pending_trials = pending_trials[: max(0, int(stop_after_trials))]
    worker_plan = _effective_worker_plan(
        spec,
        pending_trials,
        real_discovery_requested=real_discovery_requested,
        clock_supplied=clock is not None,
    )
    worker_count = worker_plan.active_workers
    executor_kind = worker_plan.executor

    stage_started = time.perf_counter()
    real_context = (
        _prepare_real_discovery_context(spec, output_dir=output_dir)
        if real_discovery_requested and pending_trials
        else None
    )
    real_context_data_evidence = real_context.data_evidence if real_context is not None else {}
    real_context_feature_cache_summary = real_context.feature_cache_summary if real_context is not None else {}
    real_context_neighbor_cache_summary = real_context.neighbor_cache.summary() if real_context is not None else {}
    stage_wall_seconds["real_context_preparation"] = time.perf_counter() - stage_started

    trial_stage_started = time.perf_counter()
    progress_checkpoint_records = 0
    progress_checkpoint_interval = max(1, min(int(spec.budget.trial_batch_size), 5000))
    last_progress_checkpoint_wall = time.perf_counter()

    def persist_evaluated_records(records: list[DiscoveryTrialRecord]) -> None:
        nonlocal batch_completed
        nonlocal executed_this_call
        nonlocal last_progress_checkpoint_wall
        nonlocal last_snapshot_at
        nonlocal progress_checkpoint_records
        nonlocal state
        for record in records:
            trial_path = output_dir / "trials" / f"{record.trial_id}.json"
            record_artifact_write(lambda path=trial_path, item=record: write_trial_record(path, item), trial_path)
            existing_records[record.trial_id] = record
            state = state.with_completed_trial(record, updated_at_utc=iso_utc(now()))
            completed_ids.add(record.trial_id)
            executed_this_call += 1
            batch_completed += 1
            progress_checkpoint_records += 1
            snapshot_at = now()
            if batch_completed >= spec.budget.trial_batch_size or _snapshot_interval_due(
                last_snapshot_at,
                snapshot_at,
                spec.budget.snapshot_interval_minutes,
            ):
                if ledgers_complete:
                    record_artifact_write(
                        lambda: _write_ledgers(
                            records=_ordered_records(existing_records.values()),
                            interesting_path=interesting_path,
                            blocked_path=blocked_path,
                            filter_blockers_path=filter_blockers_path,
                        ),
                        (interesting_path, blocked_path, filter_blockers_path),
                    )
                snapshot = record_artifact_write(
                    lambda: _snapshot(
                        output_dir,
                        spec=spec,
                        state=state,
                        records=existing_records,
                        counts=_counts_for_state(state, existing_records, complete=ledgers_complete),
                        counts_scope=_counts_scope(ledgers_complete),
                        sequence=state.snapshot_count + 1,
                        created_at=snapshot_at,
                    )
                )
                snapshot_paths.append(snapshot)
                state = state.with_snapshot(path=snapshot, updated_at_utc=iso_utc(now()))
                record_artifact_write(lambda: write_run_state(state_path, state), state_path)
                batch_completed = 0
                progress_checkpoint_records = 0
                last_progress_checkpoint_wall = time.perf_counter()
                last_snapshot_at = snapshot_at
            elif (
                progress_checkpoint_records >= progress_checkpoint_interval
                or time.perf_counter() - last_progress_checkpoint_wall >= 30.0
            ):
                record_artifact_write(lambda: write_run_state(state_path, state), state_path)
                progress_checkpoint_records = 0
                last_progress_checkpoint_wall = time.perf_counter()

    preflight_trials, preflight_reason = _real_discovery_preflight_trials(
        pending_trials,
        real_discovery_requested=real_discovery_requested,
        stop_after_trials=stop_after_trials,
    )
    if preflight_trials and real_context is not None:
        records = _evaluate_discovery_trial_thread_chunk(
            spec,
            tuple(preflight_trials),
            context=real_context,
            clock=now,
            output_dir=output_dir,
        )
        persist_evaluated_records(records)
        failed_records = [record for record in records if _trial_execution_failed(record)]
        preflight_summary = {
            "enabled": True,
            "status": "failed" if failed_records else "passed",
            "trial_count": int(len(records)),
            "failed_trial_count": int(len(failed_records)),
            "reason": preflight_reason,
            "trial_ids": [record.trial_id for record in records],
            "failed_trial_ids": [record.trial_id for record in failed_records],
            "failure_reasons": sorted(
                {
                    str(record.error_payload.get("error") or record.blocker_code or record.status)
                    for record in failed_records
                }
            ),
        }
        pending_trials = [(index, template) for index, template in pending_trials if template.trial_id not in completed_ids]
        preflight_blocked = bool(failed_records)
        if preflight_blocked:
            pending_trials = []
    else:
        preflight_summary = {
            "enabled": False,
            "status": "not_run",
            "trial_count": 0,
            "failed_trial_count": 0,
            "reason": preflight_reason,
        }
    if executor_kind == "process" and real_context is not None:
        real_context = None
        gc.collect()

    trial_chunk_size = (
        _process_chunk_size(spec, worker_count, real_discovery_requested=real_discovery_requested)
        if executor_kind == "process"
        else 1
    )
    if real_discovery_requested:
        if (
            executor_kind == "process"
            and stop_after_trials is None
            and not _real_discovery_process_chunk_size_env_present()
        ):
            trial_chunk_size = max(trial_chunk_size, _max_cache_affinity_group_size(pending_trials))
        pending_trials = _cache_affinity_ordered_trials(pending_trials, block_size=trial_chunk_size)
    cache_affinity_group_chunks = (
        _cache_affinity_trial_chunks(pending_trials)
        if real_discovery_requested
        and executor_kind == "process"
        and stop_after_trials is None
        and not _real_discovery_process_chunk_size_env_present()
        else None
    )
    if cache_affinity_group_chunks:
        trial_chunk_size = max(len(chunk) for chunk in cache_affinity_group_chunks)

    if executor_kind == "process":
        executor_context = ProcessPoolExecutor(
            max_workers=worker_count,
            initializer=_init_process_discovery_worker,
            initargs=(spec.to_payload(), str(output_dir)),
        )
    else:
        executor_context = ThreadPoolExecutor(max_workers=worker_count) if worker_count > 1 else _NullExecutor()
    with executor_context as executor:
        cursor = 0
        while cursor < (len(cache_affinity_group_chunks) if cache_affinity_group_chunks is not None else len(pending_trials)):
            if cache_affinity_group_chunks is not None:
                chunks = cache_affinity_group_chunks[cursor : cursor + worker_count]
                cursor += len(chunks)
            else:
                cursor, chunks = _chunked_trials(
                    pending_trials,
                    start=cursor,
                    worker_count=worker_count,
                    chunk_size=trial_chunk_size,
                )
            if executor is None:
                records = [
                    record
                    for chunk in chunks
                    for record in _evaluate_discovery_trial_thread_chunk(
                        spec,
                        tuple(chunk),
                        context=real_context,
                        clock=now,
                        output_dir=output_dir,
                    )
                ]
                persist_evaluated_records(records)
            elif executor_kind == "process":
                futures = [
                    executor.submit(
                        _evaluate_discovery_trial_process_chunk,
                        tuple(chunk),
                    )
                    for chunk in chunks
                ]
                try:
                    for future in as_completed(futures):
                        chunk_result = future.result()
                        process_chunk_results.append(chunk_result)
                        persist_evaluated_records(list(chunk_result.records))
                except Exception as exc:
                    for future in futures:
                        future.cancel()
                    if type(exc).__name__ == "BrokenProcessPool":
                        raise RuntimeError(
                            "discovery_process_pool_terminated_abruptly:"
                            f" active_workers={worker_count}"
                            f" requested_workers={worker_plan.requested_workers}"
                            f" configured_max_workers={worker_plan.configured_max_workers}"
                            f" process_worker_cap={worker_plan.process_worker_cap}"
                            f" cap_source={worker_plan.process_worker_cap_source}"
                        ) from exc
                    raise
            else:
                futures = [
                    executor.submit(
                        _evaluate_discovery_trial_thread_chunk,
                        spec,
                        tuple(chunk),
                        context=real_context,
                        clock=now,
                        output_dir=output_dir,
                    )
                    for chunk in chunks
                ]
                for future in as_completed(futures):
                    persist_evaluated_records(list(future.result()))
    stage_wall_seconds["trial_execution"] = time.perf_counter() - trial_stage_started

    if batch_completed:
        stage_started = time.perf_counter()
        if ledgers_complete:
            record_artifact_write(
                lambda: _write_ledgers(
                    records=_ordered_records(existing_records.values()),
                    interesting_path=interesting_path,
                    blocked_path=blocked_path,
                    filter_blockers_path=filter_blockers_path,
                ),
                (interesting_path, blocked_path, filter_blockers_path),
            )
        last_snapshot_at = now()
        snapshot = record_artifact_write(
            lambda: _snapshot(
                output_dir,
                spec=spec,
                state=state,
                records=existing_records,
                counts=_counts_for_state(state, existing_records, complete=ledgers_complete),
                counts_scope=_counts_scope(ledgers_complete),
                sequence=state.snapshot_count + 1,
                created_at=last_snapshot_at,
            )
        )
        snapshot_paths.append(snapshot)
        state = state.with_snapshot(path=snapshot, updated_at_utc=iso_utc(now()))
        record_artifact_write(lambda: write_run_state(state_path, state), state_path)
        stage_wall_seconds["final_batch_snapshot_state_write"] = time.perf_counter() - stage_started

    stage_started = time.perf_counter()
    status_scope = "real discovery" if real_discovery_requested else "placeholder discovery"
    if preflight_blocked:
        state = state.with_status(
            "blocked",
            updated_at_utc=iso_utc(now()),
            message="real discovery preflight failed; full sweep skipped",
        )
        record_artifact_write(lambda: write_run_state(state_path, state), state_path)
    elif real_discovery_requested and state.failed_trial_ids:
        state = state.with_status(
            "blocked",
            updated_at_utc=iso_utc(now()),
            message="real discovery trial execution failed; run blocked fail-closed",
        )
        record_artifact_write(lambda: write_run_state(state_path, state), state_path)
    elif len(state.completed_trial_ids) >= len(templates):
        state = state.with_status("completed", updated_at_utc=iso_utc(now()), message=f"{status_scope} run completed")
        record_artifact_write(lambda: write_run_state(state_path, state), state_path)
    else:
        state = state.with_status("in_progress", updated_at_utc=iso_utc(now()), message=f"{status_scope} run paused")
        record_artifact_write(lambda: write_run_state(state_path, state), state_path)
    stage_wall_seconds["final_status_state_write"] = time.perf_counter() - stage_started

    stage_started = time.perf_counter()
    if ledgers_complete:
        record_artifact_write(
            lambda: _write_ledgers(
                records=_ordered_records(existing_records.values()),
                interesting_path=interesting_path,
                blocked_path=blocked_path,
                filter_blockers_path=filter_blockers_path,
            ),
            (interesting_path, blocked_path, filter_blockers_path),
        )
        ledger_summary = _ledger_summary_from_records(existing_records)
    elif len(state.completed_trial_ids) >= len(templates):
        ledger_summary = record_artifact_write(
            lambda: _write_ledgers_from_trial_dir(
                trial_dir=output_dir / "trials",
                run_id=spec.run_id,
                interesting_path=interesting_path,
                blocked_path=blocked_path,
                filter_blockers_path=filter_blockers_path,
            ),
            (interesting_path, blocked_path, filter_blockers_path),
        )
        ledgers_complete = True
    elif state.status == "blocked" and existing_records:
        record_artifact_write(
            lambda: _write_ledgers(
                records=_ordered_records(existing_records.values()),
                interesting_path=interesting_path,
                blocked_path=blocked_path,
                filter_blockers_path=filter_blockers_path,
            ),
            (interesting_path, blocked_path, filter_blockers_path),
        )
        ledger_summary = _ledger_summary_from_records(existing_records, completed_count=len(state.completed_trial_ids))
    else:
        ledger_summary = _ledger_summary_from_records(existing_records, completed_count=len(state.completed_trial_ids))
    stage_wall_seconds["final_ledger_materialization"] = time.perf_counter() - stage_started

    stage_started = time.perf_counter()
    final_snapshot = record_artifact_write(
        lambda: _snapshot(
            output_dir,
            spec=spec,
            state=state,
            records=existing_records,
            counts=ledger_summary.counts,
            counts_scope=_counts_scope(ledgers_complete),
            sequence=state.snapshot_count + 1,
            created_at=now(),
        )
    )
    snapshot_paths.append(final_snapshot)
    state = state.with_snapshot(path=final_snapshot, updated_at_utc=iso_utc(now()))
    record_artifact_write(lambda: write_run_state(state_path, state), state_path)
    stage_wall_seconds["final_snapshot_state_write"] = time.perf_counter() - stage_started

    stage_started = time.perf_counter()
    required_outputs = {
        "discovery_run_manifest": str(manifest_path),
        "discovery_spec_resolved": str(resolved_spec_path),
        "run_state": str(state_path),
        "interesting_candidates": str(interesting_path),
        "blocked_candidates": str(blocked_path),
        "filter_blockers": str(filter_blockers_path),
        "snapshots": str(output_dir / "snapshots"),
        "trials": str(output_dir / "trials"),
    }
    manifest = discovery_manifest_payload(
        spec=spec,
        spec_path=spec_path,
        resolved_paths=resolved_paths,
        state=state.to_payload(),
        required_outputs=required_outputs,
        counts=ledger_summary.counts,
        feature_column_set_evidence=feature_column_set_evidence,
        data_evidence=real_context_data_evidence,
        runtime_seconds=time.perf_counter() - started,
    )
    manifest["state_checkpoint_policy"] = {
        "policy_version": "discovery-run-state-checkpoint-policy-v1",
        "durable_trial_record_before_state_checkpoint": True,
        "run_state_write_scope": "initial_resume_merge_progress_snapshot_pause_completion_final",
        "resume_recovers_completed_trials_from_trial_records": True,
        "resume_catalog_mode": resume_catalog.mode,
        "resume_trial_file_count": resume_catalog.trial_file_count,
        "resume_recovered_trial_file_count": resume_catalog.recovered_trial_file_count,
        "resume_full_record_load_limit": resume_catalog.full_record_load_limit,
        "resume_fully_hydrated_existing_records": resume_catalog.fully_hydrated,
        "progress_checkpoint_interval_trials": progress_checkpoint_interval,
    }
    manifest["trial_artifact_policy"] = {
        "policy_version": "discovery-trial-artifact-policy-v2",
        "configured_persist_trial_artifacts": spec.execution.persist_trial_artifacts,
        "persist_full_artifacts_inline": spec.execution.persist_trial_artifacts == "all",
        "persist_prediction_artifacts_without_neighbor_diagnostics": spec.execution.persist_trial_artifacts
        == "predictions_only",
        "interesting_only_defers_heavy_artifacts": spec.execution.persist_trial_artifacts == "interesting_only",
        "trial_records_and_candidate_ledgers_remain_durable": True,
    }
    manifest["execution_order_policy"] = {
        "policy_version": "discovery-execution-order-policy-v1",
        "real_discovery_cache_affinity_ordering": bool(real_discovery_requested),
        "trial_id_payload_mapping_preserved": True,
        "real_discovery_cache_group_block_size": int(trial_chunk_size) if real_discovery_requested else None,
        "real_discovery_cache_groups_round_robin": bool(real_discovery_requested),
        "ordered_by": [
            "feature_column_set_id",
            "regime_mode",
            "label_horizon",
            "distance_metric",
            "hmm_parameters",
            "k",
            "threshold_variants_share_cached_base_knn",
            "original_trial_index",
        ]
        if real_discovery_requested
        else ["original_trial_index"],
    }
    manifest["execution_observed"] = {
        "executor": executor_kind,
        "configured_executor": spec.execution.executor,
        "configured_max_workers": int(spec.execution.max_workers),
        "requested_workers": int(worker_plan.requested_workers),
        "active_workers": worker_count,
        "real_discovery_requested": bool(real_discovery_requested),
        "process_worker_cap": worker_plan.process_worker_cap,
        "process_worker_cap_source": worker_plan.process_worker_cap_source,
        "process_worker_cap_applied": worker_plan.process_worker_cap_applied,
        "trial_chunk_size": int(trial_chunk_size),
        "worker_plan_reason": worker_plan.reason,
        "process_pool_child_cpu_not_in_parent_process_cpu_seconds": executor_kind == "process",
    }
    manifest["preflight"] = dict(preflight_summary)
    manifest["regime_truthfulness"]["observed_trial_regime_modes"] = list(ledger_summary.observed_trial_regime_modes)
    manifest["regime_truthfulness"]["observed_trial_regime_detector_types"] = list(
        ledger_summary.observed_trial_regime_detector_types
    )
    manifest["regime_truthfulness"]["observed_trial_regime_model_backends"] = list(
        ledger_summary.observed_trial_regime_model_backends
    )
    manifest["regime_truthfulness"]["observed_trial_regime_values_complete"] = bool(ledgers_complete)
    stage_wall_seconds["manifest_assembly_pre_telemetry"] = time.perf_counter() - stage_started
    manifest["compute_telemetry"] = build_compute_telemetry(
        session=telemetry_session,
        output_dir=output_dir,
        completed_records=_ordered_records(existing_records.values()),
        active_workers=worker_count,
        executed_this_call=executed_this_call,
        artifact_write_seconds=artifact_write_seconds,
        feature_cache_summary=(
            real_context.feature_cache_summary if real_context is not None else real_context_feature_cache_summary
        ),
        neighbor_cache_summary=(
            real_context.neighbor_cache.summary() if real_context is not None else real_context_neighbor_cache_summary
        ),
        stage_wall_seconds=stage_wall_seconds,
        observed_artifact_counts=artifact_observer.counts(),
        process_chunk_timing=_process_chunk_timing_summary(process_chunk_results),
    )
    manifest["compute_telemetry"]["executor"] = executor_kind
    manifest["compute_telemetry"]["configured_executor"] = spec.execution.executor
    manifest["compute_telemetry"]["configured_max_workers"] = int(spec.execution.max_workers)
    manifest["compute_telemetry"]["requested_workers"] = int(worker_plan.requested_workers)
    manifest["compute_telemetry"]["real_discovery_requested"] = bool(real_discovery_requested)
    manifest["compute_telemetry"]["process_worker_cap"] = worker_plan.process_worker_cap
    manifest["compute_telemetry"]["process_worker_cap_source"] = worker_plan.process_worker_cap_source
    manifest["compute_telemetry"]["process_worker_cap_applied"] = worker_plan.process_worker_cap_applied
    manifest["compute_telemetry"]["trial_chunk_size"] = int(trial_chunk_size)
    manifest["compute_telemetry"]["worker_plan"] = worker_plan.to_payload()
    manifest["compute_telemetry"]["process_pool_child_cpu_not_in_parent_process_cpu_seconds"] = executor_kind == "process"
    manifest["compute_telemetry"]["completed_records_scope"] = _counts_scope(ledgers_complete)
    manifest["compute_telemetry"]["resume_catalog_mode"] = resume_catalog.mode
    remaining_trials = max(0, len(templates) - len(state.completed_trial_ids))
    observed_trials_per_second = float(executed_this_call / max(time.perf_counter() - started, 1e-12))
    manifest["compute_telemetry"]["completed_trials"] = int(ledger_summary.counts.get("completed_trials", 0))
    manifest["compute_telemetry"]["failed_trials"] = int(ledger_summary.counts.get("failed_trials", 0))
    manifest["compute_telemetry"]["durable_trial_records"] = int(
        ledger_summary.counts.get("durable_trial_records", len(state.completed_trial_ids))
    )
    manifest["compute_telemetry"]["processed_trial_records"] = int(len(state.completed_trial_ids))
    manifest["compute_telemetry"]["total_planned_trials"] = int(len(templates))
    manifest["compute_telemetry"]["remaining_trials"] = int(remaining_trials)
    manifest["compute_telemetry"]["estimated_seconds_remaining"] = (
        float(remaining_trials / observed_trials_per_second)
        if executed_this_call > 0 and observed_trials_per_second > 0.0
        else None
    )
    manifest["runtime"]["compute_telemetry_version"] = manifest["compute_telemetry"]["telemetry_version"]
    record_artifact_write(lambda: atomic_write_json(manifest_path, manifest), manifest_path)
    stop_telemetry_session(telemetry_session)

    return DiscoveryRunResult(
        output_dir=output_dir,
        manifest_path=manifest_path,
        resolved_spec_path=resolved_spec_path,
        run_state_path=state_path,
        interesting_candidates_path=interesting_path,
        blocked_candidates_path=blocked_path,
        filter_blockers_path=filter_blockers_path,
        snapshot_paths=tuple(snapshot_paths),
    )


def _feature_column_set_evidence(spec: DiscoveryRunSpec) -> dict[str, Any]:
    if spec.feature_column_sets_path is None:
        return {
            "configured": False,
            "selected_feature_column_set_ids": list(spec.feature_column_set_ids),
            "reason": "feature_column_sets_path_not_configured",
        }
    manifest = load_feature_column_set_manifest(spec.feature_column_sets_path)
    selected_ids = spec.feature_column_set_ids or tuple(item.feature_column_set_id for item in manifest.enabled_sets)
    validate_feature_column_set_manifest(manifest, selected_ids=selected_ids)
    by_id = manifest.set_by_id()
    selected = [by_id[item_id] for item_id in selected_ids]
    return {
        "configured": True,
        "manifest_path": str(spec.feature_column_sets_path),
        "manifest_id": manifest.manifest_id,
        "manifest_sha256": manifest.manifest_sha256,
        "selected_feature_column_set_ids": list(selected_ids),
        "selected_feature_column_set_count": len(selected),
        "selected_registered_feature_set_ids": sorted({item.registered_feature_set_id for item in selected}),
        "max_selected_dimensions": max((len(item.columns) for item in selected), default=0),
        "wt3d_selected": any(item.contains_wt3d for item in selected),
        "non_wt_selected": any(not item.contains_wt3d for item in selected),
        "research_only": manifest.research_only,
        "observe_only": manifest.observe_only,
        "promotion_ready": manifest.promotion_ready,
    }


def _assert_resolved_spec_unchanged(path: Path, payload: Mapping[str, Any]) -> None:
    if not path.exists():
        raise ValueError("existing discovery run is missing discovery_spec_resolved.json")
    existing = json.loads(path.read_text(encoding="utf-8"))
    if existing != dict(payload):
        raise ValueError("changed discovery spec requires a new run_id")


def _completed_run_needs_artifact_repair(
    *,
    manifest_path: Path,
    interesting_path: Path,
    blocked_path: Path,
    filter_blockers_path: Path,
    completed_count: int,
) -> bool:
    if not manifest_path.exists():
        return True
    for path in (interesting_path, blocked_path, filter_blockers_path):
        if not Path(path).exists():
            return True
    ledger_total = 0
    for path in (interesting_path, blocked_path, filter_blockers_path):
        row_count = _ledger_parquet_row_count(Path(path))
        if row_count is None:
            return True
        ledger_total += row_count
    if ledger_total != int(completed_count):
        return True
    try:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True
    counts = manifest.get("counts") if isinstance(manifest.get("counts"), Mapping) else {}
    return int(counts.get("completed_trials") or 0) != int(completed_count)


def _ledger_parquet_row_count(path: Path) -> int | None:
    try:
        return len(pd.read_parquet(path, columns=["trial_id"]))
    except Exception:
        return None


def _placeholder_trial_record(
    spec: DiscoveryRunSpec,
    template: DiscoveryTrialTemplate,
    *,
    trial_index: int,
    clock: Callable[[], datetime],
) -> DiscoveryTrialRecord:
    started_at = iso_utc(clock())
    completed_at = iso_utc(clock())
    return DiscoveryTrialRecord(
        run_id=spec.run_id,
        trial_id=template.trial_id,
        attempt_id="attempt-001",
        trial_index=trial_index,
        candidate_id=template.candidate_id,
        candidate_family=template.candidate_family,
        ledger_kind=template.ledger_kind,
        score=template.score,
        blocker_code=template.blocker_code,
        filter_blocker_code=template.filter_blocker_code,
        status="completed",
        started_at_utc=started_at,
        completed_at_utc=completed_at,
        payload={
            "placeholder_trial": True,
            "discovery_mode": spec.discovery_mode,
            "symbol": spec.symbol,
            "timeframe": spec.timeframe,
            **dict(template.payload),
        },
    )


def _effective_worker_count(max_workers: int, pending_trials: list[tuple[int, DiscoveryTrialTemplate]]) -> int:
    if not pending_trials:
        return 1
    return max(1, min(int(max_workers), len(pending_trials)))


def _cache_affinity_ordered_trials(
    pending_trials: list[tuple[int, DiscoveryTrialTemplate]],
    *,
    block_size: int = DEFAULT_REAL_DISCOVERY_PROCESS_CHUNK_SIZE,
) -> list[tuple[int, DiscoveryTrialTemplate]]:
    if not pending_trials:
        return []
    group_size = max(1, int(block_size))
    grouped: dict[tuple[Any, ...], list[tuple[int, DiscoveryTrialTemplate]]] = {}
    for item in sorted(pending_trials, key=lambda item: (int(item[0]), str(item[1].trial_id))):
        grouped.setdefault(_trial_cache_affinity_key(item[1]), []).append(item)
    ordered_keys = sorted(grouped)
    ordered: list[tuple[int, DiscoveryTrialTemplate]] = []
    while ordered_keys:
        next_keys: list[tuple[Any, ...]] = []
        for key in ordered_keys:
            group = grouped[key]
            ordered.extend(group[:group_size])
            remaining = group[group_size:]
            if remaining:
                grouped[key] = remaining
                next_keys.append(key)
        ordered_keys = next_keys
    return ordered


def _max_cache_affinity_group_size(pending_trials: list[tuple[int, DiscoveryTrialTemplate]]) -> int:
    counts: dict[tuple[Any, ...], int] = {}
    for _, template in pending_trials:
        key = _trial_cache_affinity_key(template)
        counts[key] = counts.get(key, 0) + 1
    return max(counts.values(), default=1)


def _cache_affinity_trial_chunks(
    pending_trials: list[tuple[int, DiscoveryTrialTemplate]],
) -> list[list[tuple[int, DiscoveryTrialTemplate]]]:
    grouped: dict[tuple[Any, ...], list[tuple[int, DiscoveryTrialTemplate]]] = {}
    for item in sorted(pending_trials, key=lambda item: (_trial_cache_affinity_key(item[1]), int(item[0]), str(item[1].trial_id))):
        grouped.setdefault(_trial_cache_affinity_key(item[1]), []).append(item)
    return [grouped[key] for key in sorted(grouped)]


def _trial_cache_affinity_key(template: DiscoveryTrialTemplate) -> tuple[Any, ...]:
    payload = dict(template.payload or {})
    return (
        str(payload.get("feature_column_set_id") or ""),
        str(payload.get("regime_mode") or ""),
        str(payload.get("label_horizon") or ""),
        str(payload.get("distance_metric") or ""),
        int(payload.get("hmm_state_count") or 0),
        float(payload.get("hmm_posterior_threshold") or 0.0),
        float(payload.get("hmm_entropy_threshold") or 0.0),
        int(payload.get("k") or 0),
    )


def _effective_worker_plan(
    spec: DiscoveryRunSpec,
    pending_trials: list[tuple[int, DiscoveryTrialTemplate]],
    *,
    real_discovery_requested: bool,
    clock_supplied: bool,
) -> _WorkerPlan:
    configured_max_workers = max(1, int(spec.execution.max_workers))
    requested_workers = _effective_worker_count(configured_max_workers, pending_trials)
    executor = (
        "process"
        if spec.execution.executor == "process" and requested_workers > 1 and not clock_supplied
        else "thread"
    )
    active_workers = requested_workers
    cap: int | None = None
    cap_source = ""
    cap_applied = False
    reasons: list[str] = []

    if spec.execution.executor == "process" and clock_supplied:
        reasons.append("clock_supplied_thread_executor_for_determinism")
    if requested_workers <= 1:
        reasons.append("single_worker_thread_executor")

    if executor == "process" and real_discovery_requested:
        cap, cap_source = _real_discovery_process_worker_cap()
        if requested_workers > cap:
            active_workers = cap
            cap_applied = True
            reasons.append(f"real_discovery_process_worker_cap:{requested_workers}->{active_workers}")
        else:
            reasons.append("real_discovery_process_worker_cap_not_needed")

    if active_workers <= 1:
        executor = "thread"

    return _WorkerPlan(
        configured_executor=spec.execution.executor,
        executor=executor,
        configured_max_workers=configured_max_workers,
        requested_workers=requested_workers,
        active_workers=max(1, int(active_workers)),
        real_discovery_requested=real_discovery_requested,
        process_worker_cap=cap,
        process_worker_cap_source=cap_source,
        process_worker_cap_applied=cap_applied,
        reason=";".join(reasons) or "configured_worker_plan",
    )


def _real_discovery_process_worker_cap() -> tuple[int, str]:
    raw = os.getenv(REAL_DISCOVERY_PROCESS_WORKER_CAP_ENV)
    if raw is not None and str(raw).strip():
        try:
            value = max(1, int(str(raw).strip()))
            return value, f"env:{REAL_DISCOVERY_PROCESS_WORKER_CAP_ENV}"
        except ValueError:
            return DEFAULT_REAL_DISCOVERY_PROCESS_WORKER_CAP, (
                f"default_invalid_env:{REAL_DISCOVERY_PROCESS_WORKER_CAP_ENV}"
            )
    return DEFAULT_REAL_DISCOVERY_PROCESS_WORKER_CAP, "default_real_discovery_process_worker_cap"


def _process_chunk_size(spec: DiscoveryRunSpec, worker_count: int, *, real_discovery_requested: bool = False) -> int:
    if spec.execution.executor != "process":
        return 1
    if real_discovery_requested:
        raw = os.getenv(REAL_DISCOVERY_PROCESS_CHUNK_SIZE_ENV)
        if raw is not None and str(raw).strip():
            try:
                return max(1, min(64, int(str(raw).strip())))
            except ValueError:
                return DEFAULT_REAL_DISCOVERY_PROCESS_CHUNK_SIZE
        return DEFAULT_REAL_DISCOVERY_PROCESS_CHUNK_SIZE
    target = max(1, int(spec.budget.trial_batch_size) // max(1, int(worker_count) * 4))
    return max(1, min(64, target))


def _real_discovery_process_chunk_size_env_present() -> bool:
    raw = os.getenv(REAL_DISCOVERY_PROCESS_CHUNK_SIZE_ENV)
    return raw is not None and str(raw).strip() != ""


def _real_discovery_preflight_trials(
    pending_trials: list[tuple[int, DiscoveryTrialTemplate]],
    *,
    real_discovery_requested: bool,
    stop_after_trials: int | None,
) -> tuple[list[tuple[int, DiscoveryTrialTemplate]], str]:
    if not real_discovery_requested:
        return [], "placeholder_discovery"
    if stop_after_trials is not None:
        return [], "bounded_stop_after_trials"
    if not pending_trials:
        return [], "no_pending_trials"
    preflight_count = _real_discovery_preflight_trial_count()
    if preflight_count <= 0:
        return [], f"disabled_by_env:{REAL_DISCOVERY_PREFLIGHT_TRIALS_ENV}"
    minimum_planned = _real_discovery_preflight_min_planned_trials()
    if len(pending_trials) < minimum_planned:
        return [], f"planned_trials_below_preflight_minimum:{len(pending_trials)}<{minimum_planned}"
    return _representative_preflight_trials(pending_trials, limit=preflight_count), "large_real_discovery_preflight"


def _real_discovery_preflight_trial_count() -> int:
    raw = os.getenv(REAL_DISCOVERY_PREFLIGHT_TRIALS_ENV)
    if raw is not None and str(raw).strip():
        try:
            return max(0, min(256, int(str(raw).strip())))
        except ValueError:
            return DEFAULT_REAL_DISCOVERY_PREFLIGHT_TRIALS
    return DEFAULT_REAL_DISCOVERY_PREFLIGHT_TRIALS


def _real_discovery_preflight_min_planned_trials() -> int:
    raw = os.getenv(REAL_DISCOVERY_PREFLIGHT_MIN_PLANNED_TRIALS_ENV)
    if raw is not None and str(raw).strip():
        try:
            return max(1, int(str(raw).strip()))
        except ValueError:
            return DEFAULT_REAL_DISCOVERY_PREFLIGHT_MIN_PLANNED_TRIALS
    return DEFAULT_REAL_DISCOVERY_PREFLIGHT_MIN_PLANNED_TRIALS


def _representative_preflight_trials(
    pending_trials: list[tuple[int, DiscoveryTrialTemplate]],
    *,
    limit: int,
) -> list[tuple[int, DiscoveryTrialTemplate]]:
    selected: list[tuple[int, DiscoveryTrialTemplate]] = []
    selected_ids: set[str] = set()
    seen_dimensions: set[tuple[str, str, str, str]] = set()
    for item in pending_trials:
        _, template = item
        payload = template.payload
        dimension = (
            str(payload.get("feature_column_set_id") or ""),
            str(payload.get("regime_mode") or ""),
            str(payload.get("label_horizon") or ""),
            str(payload.get("distance_metric") or ""),
        )
        if dimension in seen_dimensions:
            continue
        seen_dimensions.add(dimension)
        selected.append(item)
        selected_ids.add(template.trial_id)
        if len(selected) >= limit:
            return selected
    for item in pending_trials:
        _, template = item
        if template.trial_id in selected_ids:
            continue
        selected.append(item)
        if len(selected) >= limit:
            break
    return selected


def _trial_execution_failed(record: DiscoveryTrialRecord) -> bool:
    return record.status != "completed" or record.blocker_code == "trial_execution_error"


def _chunked_trials(
    pending_trials: list[tuple[int, DiscoveryTrialTemplate]],
    *,
    start: int,
    worker_count: int,
    chunk_size: int,
) -> tuple[int, list[list[tuple[int, DiscoveryTrialTemplate]]]]:
    chunks: list[list[tuple[int, DiscoveryTrialTemplate]]] = []
    cursor = start
    for _ in range(max(1, worker_count)):
        chunk = pending_trials[cursor : cursor + max(1, chunk_size)]
        if not chunk:
            break
        chunks.append(chunk)
        cursor += len(chunk)
    return cursor, chunks


def _init_process_discovery_worker(spec_payload: Mapping[str, Any], output_dir_text: str) -> None:
    global _PROCESS_DISCOVERY_SPEC, _PROCESS_DISCOVERY_CONTEXT, _PROCESS_DISCOVERY_OUTPUT_DIR
    global _PROCESS_DISCOVERY_CONTEXT_INITIALIZATION_SECONDS
    started = time.perf_counter()
    output_dir = Path(output_dir_text).expanduser().resolve()
    spec = DiscoveryRunSpec.from_payload(dict(spec_payload), spec_path=output_dir / "process_discovery_spec.json", repo_root=REPO_ROOT)
    _PROCESS_DISCOVERY_SPEC = spec
    _PROCESS_DISCOVERY_OUTPUT_DIR = output_dir
    templates = generated_trial_templates(spec)
    _PROCESS_DISCOVERY_CONTEXT = (
        _prepare_real_discovery_context(
            spec,
            output_dir=output_dir,
            persist_feature_matrices=False,
        )
        if _real_discovery_requested(spec, templates)
        else None
    )
    _PROCESS_DISCOVERY_CONTEXT_INITIALIZATION_SECONDS = max(0.0, time.perf_counter() - started)


def _evaluate_discovery_trial_process_chunk(
    chunk: tuple[tuple[int, DiscoveryTrialTemplate], ...],
) -> _ProcessChunkResult:
    if _PROCESS_DISCOVERY_SPEC is None or _PROCESS_DISCOVERY_OUTPUT_DIR is None:
        raise RuntimeError("process discovery worker was not initialized")
    wall_started = time.perf_counter()
    cpu_started = time.process_time()
    records = tuple(
        _evaluate_discovery_trial(
            _PROCESS_DISCOVERY_SPEC,
            template,
            context=_PROCESS_DISCOVERY_CONTEXT,
            trial_index=index,
            clock=utc_now,
            output_dir=_PROCESS_DISCOVERY_OUTPUT_DIR,
        )
        for index, template in chunk
    )
    return _ProcessChunkResult(
        records=records,
        worker_pid=int(os.getpid()),
        chunk_size=len(chunk),
        chunk_wall_seconds=max(0.0, time.perf_counter() - wall_started),
        chunk_process_cpu_seconds=max(0.0, time.process_time() - cpu_started),
        worker_context_initialization_seconds=_PROCESS_DISCOVERY_CONTEXT_INITIALIZATION_SECONDS,
    )


def _evaluate_discovery_trial_thread_chunk(
    spec: DiscoveryRunSpec,
    chunk: tuple[tuple[int, DiscoveryTrialTemplate], ...],
    *,
    context: "_RealDiscoveryContext | None",
    clock: Callable[[], datetime],
    output_dir: Path,
) -> list[DiscoveryTrialRecord]:
    return [
        _evaluate_discovery_trial(
            spec,
            template,
            context=context,
            trial_index=index,
            clock=clock,
            output_dir=output_dir,
        )
        for index, template in chunk
    ]


def _evaluate_discovery_trial(
    spec: DiscoveryRunSpec,
    template: DiscoveryTrialTemplate,
    *,
    context: "_RealDiscoveryContext | None",
    trial_index: int,
    clock: Callable[[], datetime],
    output_dir: Path,
) -> DiscoveryTrialRecord:
    if _real_trial_template(template):
        return _real_discovery_trial_record(
            spec,
            template,
            context=context,
            trial_index=trial_index,
            clock=clock,
            output_dir=output_dir,
        )
    return _placeholder_trial_record(spec, template, trial_index=trial_index, clock=clock)


@dataclass(frozen=True, slots=True)
class _HmmCacheEntry:
    result: HmmMaterializationResult


@dataclass(frozen=True, slots=True)
class _KnnBaseCacheEntry:
    result: KnnStudyResult
    metric_view: "_KnnThresholdMetricView"


@dataclass(frozen=True, slots=True)
class _KnnThresholdMetricView:
    base_skip: np.ndarray
    active: np.ndarray
    evaluated_count: int
    neighbor_count: np.ndarray
    probability: np.ndarray
    expected_value: np.ndarray
    agreement: np.ndarray
    distance_quality: np.ndarray
    vote_margin: np.ndarray
    symbol_codes: np.ndarray
    source_row_index: np.ndarray
    p_up_barrier: np.ndarray
    p_down_barrier: np.ndarray
    side_adjusted_return: np.ndarray
    label_return_finite: np.ndarray
    row_count: int


@dataclass(frozen=True, slots=True)
class _LabelSplitCacheEntry:
    labeled: pd.DataFrame
    splits: tuple[Any, ...]


@dataclass(frozen=True, slots=True)
class _RealDiscoveryContext:
    dataset: pd.DataFrame | None
    feature_sets: Mapping[str, DiscoveryFeatureColumnSet]
    frames_by_column_set: Mapping[str, pd.DataFrame]
    unavailable_feature_sets: Mapping[str, str]
    feature_cache_summary: Mapping[str, Any]
    label_split_cache: dict[str, _LabelSplitCacheEntry]
    label_split_cache_lock: threading.Lock
    hmm_cache: dict[str, _HmmCacheEntry]
    hmm_cache_lock: threading.Lock
    knn_base_cache: dict[str, _KnnBaseCacheEntry]
    knn_base_cache_lock: threading.Lock
    neighbor_cache: ExactNeighborCache
    interval_ms: int
    data_evidence: Mapping[str, Any]
    unavailable_reason: str = ""


def _real_discovery_requested(spec: DiscoveryRunSpec, templates: tuple[DiscoveryTrialTemplate, ...]) -> bool:
    return any(_real_trial_template(template) for template in templates)


def _real_trial_template(template: DiscoveryTrialTemplate) -> bool:
    return str(dict(template.payload).get("trial_kind") or "") in REAL_DISCOVERY_TRIAL_KINDS


def _prepare_real_discovery_context(
    spec: DiscoveryRunSpec,
    *,
    output_dir: Path,
    persist_feature_matrices: bool = True,
) -> _RealDiscoveryContext:
    if not spec.data.dataset_manifest_paths and spec.data.dataset_path is None:
        return _RealDiscoveryContext(
            dataset=None,
            feature_sets={},
            frames_by_column_set={},
            unavailable_feature_sets={},
            feature_cache_summary={},
            label_split_cache={},
            label_split_cache_lock=threading.Lock(),
            hmm_cache={},
            hmm_cache_lock=threading.Lock(),
            knn_base_cache={},
            knn_base_cache_lock=threading.Lock(),
            neighbor_cache=ExactNeighborCache(),
            interval_ms=900_000,
            data_evidence={"status": "missing", "reason": "real_discovery_data_required"},
            unavailable_reason="real_discovery_data_required",
        )

    dataset, data_evidence = _load_discovery_dataset(spec)
    dataset = _sort_discovery_dataset(dataset)
    interval_ms = _infer_interval_ms(dataset)
    manifest = load_feature_column_set_manifest(spec.feature_column_sets_path) if spec.feature_column_sets_path is not None else None
    if manifest is None:
        return _RealDiscoveryContext(
            dataset=dataset,
            feature_sets={},
            frames_by_column_set={},
            unavailable_feature_sets={},
            feature_cache_summary={},
            label_split_cache={},
            label_split_cache_lock=threading.Lock(),
            hmm_cache={},
            hmm_cache_lock=threading.Lock(),
            knn_base_cache={},
            knn_base_cache_lock=threading.Lock(),
            neighbor_cache=ExactNeighborCache(),
            interval_ms=interval_ms,
            data_evidence=data_evidence,
            unavailable_reason="feature_column_sets_path_required",
        )
    selected_ids = spec.feature_column_set_ids or tuple(item.feature_column_set_id for item in manifest.enabled_sets)
    validate_feature_column_set_manifest(manifest, selected_ids=selected_ids)
    by_id = manifest.set_by_id()
    selected = {item_id: by_id[item_id] for item_id in selected_ids}
    frames_by_registered: dict[str, pd.DataFrame] = {}
    frames_by_column_set: dict[str, pd.DataFrame] = {}
    unavailable_feature_sets: dict[str, str] = {}
    materialization_errors: dict[str, dict[str, str]] = {}
    registered_feature_set_build_count = 0
    registered_feature_set_reuse_count = 0
    feature_root = output_dir / "feature_matrices"
    if persist_feature_matrices:
        feature_root.mkdir(parents=True, exist_ok=True)
    for column_set_id, column_set in selected.items():
        if column_set.registered_feature_set_id not in frames_by_registered:
            try:
                materialized = materialize_registered_feature_set(
                    dataset,
                    feature_set_id=column_set.registered_feature_set_id,
                    interval_ms=interval_ms,
                    require_continuous=False,
                )
                frame = _sort_discovery_dataset(materialized.frame)
                preflight_reason = _feature_set_preflight_reason(frame, column_set)
                if preflight_reason:
                    unavailable_feature_sets[column_set_id] = preflight_reason
                    materialization_errors[column_set_id] = {
                        "registered_feature_set_id": column_set.registered_feature_set_id,
                        "error_type": "FeaturePreflightBlocked",
                        "error": preflight_reason,
                    }
                    continue
                frames_by_registered[column_set.registered_feature_set_id] = frame
                registered_feature_set_build_count += 1
                if persist_feature_matrices:
                    frame.to_parquet(feature_root / f"{_safe_path_part(column_set.registered_feature_set_id)}.parquet", index=False)
            except Exception as exc:
                unavailable_feature_sets[column_set_id] = "feature_set_materialization_failed"
                materialization_errors[column_set_id] = {
                    "registered_feature_set_id": column_set.registered_feature_set_id,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
                continue
        if column_set.registered_feature_set_id in frames_by_registered:
            registered_feature_set_reuse_count += 1 if column_set.registered_feature_set_id in frames_by_registered else 0
            frame = frames_by_registered[column_set.registered_feature_set_id]
            preflight_reason = _feature_set_preflight_reason(frame, column_set)
            if preflight_reason:
                unavailable_feature_sets[column_set_id] = preflight_reason
                materialization_errors[column_set_id] = {
                    "registered_feature_set_id": column_set.registered_feature_set_id,
                    "error_type": "FeaturePreflightBlocked",
                    "error": preflight_reason,
                }
                continue
            frames_by_column_set[column_set_id] = frame
    feature_cache_summary = {
        "requested_feature_column_set_count": int(len(selected)),
        "materialized_registered_feature_set_count": int(registered_feature_set_build_count),
        "registered_feature_set_reuse_count": int(max(0, len(frames_by_column_set) - registered_feature_set_build_count)),
        "unavailable_feature_set_count": int(len(unavailable_feature_sets)),
        "feature_matrix_cache_scope": "registered_feature_set_materialization_reuse_within_run",
    }
    return _RealDiscoveryContext(
        dataset=dataset,
        feature_sets=selected,
        frames_by_column_set=frames_by_column_set,
        unavailable_feature_sets=unavailable_feature_sets,
        feature_cache_summary=feature_cache_summary,
        label_split_cache={},
        label_split_cache_lock=threading.Lock(),
        hmm_cache={},
        hmm_cache_lock=threading.Lock(),
        knn_base_cache={},
        knn_base_cache_lock=threading.Lock(),
        neighbor_cache=ExactNeighborCache(),
        interval_ms=interval_ms,
        data_evidence={
            **data_evidence,
            "feature_materialization_errors": materialization_errors,
            "feature_cache_summary": feature_cache_summary,
        },
    )


def _real_discovery_trial_record(
    spec: DiscoveryRunSpec,
    template: DiscoveryTrialTemplate,
    *,
    context: _RealDiscoveryContext | None,
    trial_index: int,
    clock: Callable[[], datetime],
    output_dir: Path,
) -> DiscoveryTrialRecord:
    started_at = iso_utc(clock())
    if context is None or context.unavailable_reason:
        return _blocked_real_trial_record(
            spec,
            template,
            trial_index=trial_index,
            started_at=started_at,
            completed_at=iso_utc(clock()),
            blocker_code=(context.unavailable_reason if context is not None else "real_discovery_context_missing"),
        )

    trial_payload = dict(template.payload)
    column_set_id = str(trial_payload.get("feature_column_set_id") or "")
    column_set = context.feature_sets.get(column_set_id)
    frame = context.frames_by_column_set.get(column_set_id)
    if column_set is None or frame is None:
        return _blocked_real_trial_record(
            spec,
            template,
            trial_index=trial_index,
            started_at=started_at,
            completed_at=iso_utc(clock()),
            blocker_code=str(context.unavailable_feature_sets.get(column_set_id, "feature_column_set_not_materialized")),
        )

    attempt_id = _next_trial_attempt_id(output_dir, template.trial_id)
    trial_dir = output_dir / "trial_artifacts" / template.trial_id / attempt_id
    try:
        record = _evaluate_hmm_knn_trial(
            spec,
            template,
            attempt_id=attempt_id,
            trial_index=trial_index,
            started_at=started_at,
            completed_at=iso_utc(clock()),
            column_set=column_set,
            frame=frame,
            context=context,
            interval_ms=context.interval_ms,
            trial_dir=trial_dir,
        )
    except Exception as exc:
        try:
            mode_payload = _regime_settings_from_trial_payload(trial_payload).to_payload()
        except ValueError:
            mode_payload = {}
        return DiscoveryTrialRecord(
            run_id=spec.run_id,
            trial_id=template.trial_id,
            attempt_id=attempt_id,
            trial_index=trial_index,
            candidate_id=template.candidate_id,
            candidate_family=template.candidate_family,
            ledger_kind="blocked",
            score=0.0,
            blocker_code="trial_execution_error",
            status="failed",
            started_at_utc=started_at,
            completed_at_utc=iso_utc(clock()),
            error_payload={"error": str(exc), "error_type": type(exc).__name__},
            payload={
                **trial_payload,
                **mode_payload,
                "trial_kind": str(trial_payload.get("trial_kind") or REAL_DISCOVERY_TRIAL_KIND),
                "discovery_score_policy_version": DISCOVERY_SCORE_POLICY_VERSION,
                "feature_column_set_id": column_set_id,
                "final_score": 0.0,
                "trade_count": 0,
                "hmm_artifact_persisted": False,
                "knn_artifact_persisted": False,
                "strategy_accounting_persisted": False,
            },
        )
    return replace(record, completed_at_utc=iso_utc(clock()))


def _next_trial_attempt_id(output_dir: Path, trial_id: str) -> str:
    trial_root = output_dir / "trial_artifacts" / trial_id
    if not trial_root.exists():
        return "attempt-001"
    existing = []
    for path in trial_root.glob("attempt-*"):
        suffix = path.name.removeprefix("attempt-")
        if suffix.isdigit():
            existing.append(int(suffix))
    return f"attempt-{(max(existing, default=0) + 1):03d}"


def _materialize_hmm_with_cache(
    frame: pd.DataFrame,
    *,
    splits: Any,
    spec: HmmMaterializationSpec,
    context: _RealDiscoveryContext,
    cache_key: str,
) -> tuple[HmmMaterializationResult, bool]:
    with context.hmm_cache_lock:
        cached = context.hmm_cache.get(cache_key)
    if cached is not None:
        return _hmm_result_for_labeled_frame(cached.result, frame), True

    result = materialize_split_safe_hmm_regimes(frame, splits=splits, spec=spec)
    with context.hmm_cache_lock:
        existing = context.hmm_cache.get(cache_key)
        if existing is not None:
            return _hmm_result_for_labeled_frame(existing.result, frame), True
        context.hmm_cache[cache_key] = _HmmCacheEntry(result=result)
    return result, False


def _materialize_no_regime_with_cache(
    frame: pd.DataFrame,
    *,
    splits: Any,
    context: _RealDiscoveryContext,
    feature_pack_id: str,
    column_set_id: str,
    label_horizon: str,
    min_splits: int,
    purge_embargo_bars: int,
) -> tuple[HmmMaterializationResult, bool]:
    cache_key = _no_regime_cache_key(
        frame,
        column_set_id=column_set_id,
        label_horizon=label_horizon,
        min_splits=min_splits,
        purge_embargo_bars=purge_embargo_bars,
    )
    with context.hmm_cache_lock:
        cached = context.hmm_cache.get(cache_key)
    if cached is not None:
        return cached.result, True
    result = materialize_no_regime_baseline(frame, splits=splits, feature_pack_id=feature_pack_id)
    with context.hmm_cache_lock:
        existing = context.hmm_cache.get(cache_key)
        if existing is not None:
            return existing.result, True
        context.hmm_cache[cache_key] = _HmmCacheEntry(result=result)
    return result, False


def _materialize_knn_threshold_view_with_cache(
    frame: pd.DataFrame,
    *,
    splits: Any,
    spec: KnnStudySpec,
    context: _RealDiscoveryContext,
    source_identity: Mapping[str, Any],
    neighbor_cache_k_limit: int,
    include_neighbor_diagnostics: bool,
) -> tuple[KnnStudyResult, bool]:
    if include_neighbor_diagnostics:
        return (
            materialize_regime_local_knn_predictions(
                frame,
                splits=splits,
                spec=spec,
                neighbor_cache=context.neighbor_cache,
                neighbor_cache_k_limit=neighbor_cache_k_limit,
                source_identity=source_identity,
                include_neighbor_diagnostics=True,
            ),
            False,
        )
    base, _, cache_hit = _materialize_knn_base_with_cache(
        frame,
        splits=splits,
        spec=spec,
        context=context,
        source_identity=source_identity,
        neighbor_cache_k_limit=neighbor_cache_k_limit,
    )
    return _threshold_knn_result(base, spec=spec, cache_hit=cache_hit), cache_hit


def _materialize_knn_base_with_cache(
    frame: pd.DataFrame,
    *,
    splits: Any,
    spec: KnnStudySpec,
    context: _RealDiscoveryContext,
    source_identity: Mapping[str, Any],
    neighbor_cache_k_limit: int,
) -> tuple[KnnStudyResult, _KnnThresholdMetricView, bool]:
    base_spec = KnnStudySpec(
        feature_columns=spec.feature_columns,
        label_column=spec.label_column,
        pnl_column=spec.pnl_column,
        k=spec.k,
        distance_metric=spec.distance_metric,
        probability_threshold=0.0,
        expected_value_threshold=-1.0e9,
        min_neighbor_count=1,
        min_neighbor_agreement=0.0,
        min_distance_quality=0.0,
        vote_margin_threshold=0.0,
        same_regime_only=spec.same_regime_only,
        regime_mode=spec.regime_mode,
        regime_detector_type=spec.regime_detector_type,
        regime_model_backend=spec.regime_model_backend,
        regime_gate_enabled=spec.regime_gate_enabled,
        same_regime_neighbor_pool_enabled=spec.same_regime_neighbor_pool_enabled,
        true_hmm_backend_used=spec.true_hmm_backend_used,
        feature_column_set_id=spec.feature_column_set_id,
        label_horizon=spec.label_horizon,
    )
    cache_key = _knn_base_cache_key(
        spec=base_spec,
        source_identity=source_identity,
        neighbor_cache_k_limit=neighbor_cache_k_limit,
    )
    with context.knn_base_cache_lock:
        cached = context.knn_base_cache.get(cache_key)
    if cached is not None:
        return cached.result, cached.metric_view, True

    base = materialize_regime_local_knn_predictions(
        frame,
        splits=splits,
        spec=base_spec,
        neighbor_cache=context.neighbor_cache,
        neighbor_cache_k_limit=neighbor_cache_k_limit,
        source_identity=source_identity,
        include_neighbor_diagnostics=False,
    )
    with context.knn_base_cache_lock:
        existing = context.knn_base_cache.get(cache_key)
        if existing is None:
            metric_view = _knn_threshold_metric_view(base.frame)
            _trim_knn_base_cache(context.knn_base_cache, max_entries=2)
            context.knn_base_cache[cache_key] = _KnnBaseCacheEntry(result=base, metric_view=metric_view)
            cached_result = base
            cached_metric_view = metric_view
            cache_hit = False
        else:
            cached_result = existing.result
            cached_metric_view = existing.metric_view
            cache_hit = True
    return cached_result, cached_metric_view, cache_hit


def _threshold_knn_result(base: KnnStudyResult, *, spec: KnnStudySpec, cache_hit: bool) -> KnnStudyResult:
    frame = base.frame.copy()
    accepted, reasons = _threshold_acceptance_mask(base.frame, spec=spec)
    frame["accepted_by_knn"] = accepted
    frame["knn_skip_reason"] = reasons
    manifest = dict(base.manifest)
    manifest["spec"] = spec.to_payload()
    manifest["spec_sha256"] = spec.spec_sha256()
    manifest["knn_base_cache_hit"] = bool(cache_hit)
    manifest["threshold_view_from_base_knn"] = True
    manifest["neighbor_diagnostics_included"] = False
    return KnnStudyResult(frame=frame, manifest=manifest, neighbor_diagnostics=pd.DataFrame(columns=base.neighbor_diagnostics.columns))


def _threshold_acceptance_mask(frame: pd.DataFrame, *, spec: KnnStudySpec) -> tuple[np.ndarray, np.ndarray]:
    view = _knn_threshold_metric_view(frame)
    accepted, reasons = _threshold_acceptance_from_view(view, spec=spec)
    return accepted, reasons


def _knn_threshold_metric_view(frame: pd.DataFrame) -> _KnnThresholdMetricView:
    base_skip = frame["knn_skip_reason"].astype(str).to_numpy(dtype=object)
    p_up = pd.to_numeric(frame["p_up_barrier"], errors="coerce").to_numpy(dtype=float)
    p_down = pd.to_numeric(frame["p_down_barrier"], errors="coerce").to_numpy(dtype=float)
    label_return = pd.to_numeric(frame.get("label_return", pd.Series(np.nan, index=frame.index)), errors="coerce").to_numpy(dtype=float)
    source_row_index = pd.to_numeric(
        frame.get("source_row_index", pd.Series(np.nan, index=frame.index)),
        errors="coerce",
    ).to_numpy(dtype=float)
    if "symbol" in frame.columns:
        symbol_codes = pd.factorize(frame["symbol"].astype(str), sort=True)[0].astype("int64", copy=False)
    else:
        symbol_codes = np.zeros(len(frame), dtype="int64")
    side_multiplier = np.where(p_down > p_up, -1.0, 1.0)
    side_adjusted_return = label_return * side_multiplier
    return _KnnThresholdMetricView(
        base_skip=base_skip,
        active=np.equal(base_skip, ""),
        evaluated_count=int(np.count_nonzero(base_skip != "not_evaluated")),
        neighbor_count=pd.to_numeric(frame["neighbor_count"], errors="coerce").fillna(0).to_numpy(dtype=float),
        probability=np.maximum(p_up, p_down),
        expected_value=pd.to_numeric(frame["expected_net_return_after_costs"], errors="coerce").to_numpy(dtype=float),
        agreement=pd.to_numeric(frame["neighbor_agreement"], errors="coerce").to_numpy(dtype=float),
        distance_quality=pd.to_numeric(frame["neighbor_distance_quality"], errors="coerce").to_numpy(dtype=float),
        vote_margin=pd.to_numeric(frame["knn_vote_margin"], errors="coerce").to_numpy(dtype=float),
        symbol_codes=symbol_codes,
        source_row_index=source_row_index,
        p_up_barrier=p_up,
        p_down_barrier=p_down,
        side_adjusted_return=side_adjusted_return,
        label_return_finite=np.isfinite(label_return),
        row_count=int(len(frame)),
    )


def _threshold_acceptance_from_view(
    view: _KnnThresholdMetricView,
    *,
    spec: KnnStudySpec,
) -> tuple[np.ndarray, np.ndarray]:
    reasons = view.base_skip.copy()
    accepted = view.active.copy()
    checks = (
        (
            view.neighbor_count >= int(spec.min_neighbor_count),
            "insufficient_regime_neighbors" if spec.same_regime_neighbor_pool_enabled else "insufficient_neighbors",
        ),
        (view.probability >= float(spec.probability_threshold), "probability_below_threshold"),
        (view.expected_value >= float(spec.expected_value_threshold), "expected_value_below_threshold"),
        (view.agreement >= float(spec.min_neighbor_agreement), "neighbor_agreement_below_threshold"),
        (view.distance_quality >= float(spec.min_distance_quality), "distance_quality_below_threshold"),
        (view.vote_margin >= float(spec.vote_margin_threshold), "vote_margin_below_threshold"),
    )
    for passed, reason in checks:
        passed_mask = np.asarray(passed, dtype=bool)
        failed = accepted & ~passed_mask
        reasons[failed] = reason
        accepted = accepted & passed_mask
    reasons[accepted] = ""
    return accepted, reasons


def _knn_threshold_metrics_from_view(
    view: _KnnThresholdMetricView,
    *,
    spec: KnnStudySpec,
    search: Any,
    label_horizon_bars: int = 1,
) -> dict[str, Any]:
    accepted, _ = _threshold_acceptance_from_view(view, spec=spec)
    return _knn_metrics_from_threshold_view(
        view,
        accepted,
        search=search,
        label_horizon_bars=label_horizon_bars,
    )


def _knn_threshold_metrics_from_base(
    base: KnnStudyResult,
    *,
    spec: KnnStudySpec,
    search: Any,
    label_horizon_bars: int = 1,
) -> dict[str, Any]:
    return _knn_threshold_metrics_from_view(
        _knn_threshold_metric_view(base.frame),
        spec=spec,
        search=search,
        label_horizon_bars=label_horizon_bars,
    )


def _knn_base_cache_key(
    *,
    spec: KnnStudySpec,
    source_identity: Mapping[str, Any],
    neighbor_cache_k_limit: int,
) -> str:
    return sha256(
        json.dumps(
            {
                "knn_base_cache_version": "discovery-knn-base-cache-v1",
                "spec": spec.to_payload(),
                "source_identity": dict(source_identity),
                "neighbor_cache_k_limit": int(neighbor_cache_k_limit),
            },
            sort_keys=True,
            allow_nan=False,
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _trim_knn_base_cache(cache: dict[str, _KnnBaseCacheEntry], *, max_entries: int) -> None:
    while len(cache) >= max(1, int(max_entries)):
        oldest = next(iter(cache))
        cache.pop(oldest, None)


def _hmm_cache_key(
    *,
    column_set: DiscoveryFeatureColumnSet,
    hmm_spec: HmmMaterializationSpec,
    label_horizon: str,
    min_splits: int,
    purge_embargo_bars: int,
) -> str:
    return sha256(
        json.dumps(
            {
                "feature_column_set_id": column_set.feature_column_set_id,
                "registered_feature_set_id": column_set.registered_feature_set_id,
                "hmm_spec": hmm_spec.to_payload(),
                "label_horizon": str(label_horizon),
                "min_splits": int(min_splits),
                "purge_embargo_bars": int(purge_embargo_bars),
            },
            sort_keys=True,
            default=str,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _no_regime_cache_key(
    frame: pd.DataFrame,
    *,
    column_set_id: str,
    label_horizon: str,
    min_splits: int,
    purge_embargo_bars: int,
) -> str:
    time_start = frame["bar_time_ms"].iloc[0] if "bar_time_ms" in frame.columns and len(frame) else ""
    time_end = frame["bar_time_ms"].iloc[-1] if "bar_time_ms" in frame.columns and len(frame) else ""
    return sha256(
        json.dumps(
            {
                "no_regime_cache_version": "discovery-no-regime-baseline-cache-v1",
                "column_set_id": column_set_id,
                "label_horizon": label_horizon,
                "min_splits": int(min_splits),
                "purge_embargo_bars": int(purge_embargo_bars),
                "row_count": int(len(frame)),
                "time_start": str(time_start),
                "time_end": str(time_end),
            },
            sort_keys=True,
            default=str,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _hmm_result_for_labeled_frame(cached: HmmMaterializationResult, frame: pd.DataFrame) -> HmmMaterializationResult:
    current = frame.reset_index(drop=True).copy()
    cached_frame = cached.frame.reset_index(drop=True)
    if len(current) != len(cached_frame):
        raise ValueError("cached HMM frame row count does not match current labeled frame")
    for column in _hmm_output_columns(cached_frame):
        current[column] = cached_frame[column].to_numpy(copy=True)
    manifest = dict(cached.manifest)
    manifest["cache_reused_for_labeled_frame"] = True
    return HmmMaterializationResult(frame=current, manifest=manifest)


def _hmm_output_columns(frame: pd.DataFrame) -> tuple[str, ...]:
    return tuple(
        str(column)
        for column in frame.columns
        if str(column).startswith("regime_p_") or str(column) in HMM_POSTERIOR_COLUMNS
    )


def _knn_source_identity(
    *,
    spec: DiscoveryRunSpec,
    column_set: DiscoveryFeatureColumnSet,
    context: _RealDiscoveryContext,
    hmm_manifest: Mapping[str, Any],
    interval_ms: int,
) -> dict[str, Any]:
    data_evidence = dict(context.data_evidence)
    return {
        "run_symbol": spec.symbol,
        "timeframe": spec.timeframe,
        "interval_ms": int(interval_ms),
        "feature_column_set": column_set.to_payload(),
        "dataset_sha256": data_evidence.get("dataset_sha256"),
        "fixture_manifest_sha256": data_evidence.get("manifest_sha256"),
        "hmm_manifest_sha256": _stable_json_sha256(_normalized_hmm_cache_identity(hmm_manifest)),
        "scaler_policy": column_set.scaler_policy,
        "clamp_policy": column_set.clamp_policy,
    }


def _normalized_hmm_cache_identity(manifest: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(manifest)
    payload.pop("cache_reused_for_labeled_frame", None)
    return payload


def _persist_trial_artifacts(policy: str, *, ledger_kind: str) -> bool:
    return policy in {"all", "predictions_only"}


def _labeled_splits_with_cache(
    frame: pd.DataFrame,
    *,
    context: _RealDiscoveryContext,
    column_set_id: str,
    label_horizon: str,
    interval_ms: int,
    min_splits: int,
    purge_embargo_bars: int,
) -> tuple[_LabelSplitCacheEntry, bool]:
    cache_key = _label_split_cache_key(
        frame,
        column_set_id=column_set_id,
        label_horizon=label_horizon,
        interval_ms=interval_ms,
        min_splits=min_splits,
        purge_embargo_bars=purge_embargo_bars,
    )
    with context.label_split_cache_lock:
        cached = context.label_split_cache.get(cache_key)
    if cached is not None:
        return cached, True

    labeled = _with_directional_labels(frame, label_horizon=label_horizon, interval_ms=interval_ms)
    splits = tuple(
        build_purged_walk_forward_splits(
            labeled,
            min_splits=min_splits,
            purge_embargo_bars=purge_embargo_bars,
            time_column="bar_time_ms",
            validation_method="purged_embargoed_walk_forward",
            split_mode="anchored",
            label_spec=LabelSpec(
                event_end_time_column="label_event_end_time_ms",
                event_start_time_column="bar_time_ms",
                interval_ms=interval_ms,
                require_event_end_time=True,
                label_id=f"directional:{label_horizon}",
            ),
        )
    )
    entry = _LabelSplitCacheEntry(labeled=labeled, splits=splits)
    with context.label_split_cache_lock:
        existing = context.label_split_cache.get(cache_key)
        if existing is not None:
            return existing, True
        context.label_split_cache[cache_key] = entry
    return entry, False


def _label_split_cache_key(
    frame: pd.DataFrame,
    *,
    column_set_id: str,
    label_horizon: str,
    interval_ms: int,
    min_splits: int,
    purge_embargo_bars: int,
) -> str:
    time_start = frame["bar_time_ms"].iloc[0] if "bar_time_ms" in frame.columns and len(frame) else ""
    time_end = frame["bar_time_ms"].iloc[-1] if "bar_time_ms" in frame.columns and len(frame) else ""
    return sha256(
        json.dumps(
            {
                "column_set_id": column_set_id,
                "label_horizon": label_horizon,
                "interval_ms": int(interval_ms),
                "min_splits": int(min_splits),
                "purge_embargo_bars": int(purge_embargo_bars),
                "row_count": int(len(frame)),
                "time_start": str(time_start),
                "time_end": str(time_end),
            },
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _evaluate_hmm_knn_trial(
    spec: DiscoveryRunSpec,
    template: DiscoveryTrialTemplate,
    *,
    attempt_id: str,
    trial_index: int,
    started_at: str,
    completed_at: str,
    column_set: DiscoveryFeatureColumnSet,
    frame: pd.DataFrame,
    context: _RealDiscoveryContext,
    interval_ms: int,
    trial_dir: Path,
) -> DiscoveryTrialRecord:
    trial_payload = dict(template.payload)
    regime_settings = _regime_settings_from_trial_payload(trial_payload)
    label_horizon = str(trial_payload.get("label_horizon") or "4h")
    label_split_entry, label_split_cache_hit = _labeled_splits_with_cache(
        frame,
        context=context,
        column_set_id=column_set.feature_column_set_id,
        label_horizon=label_horizon,
        interval_ms=interval_ms,
        min_splits=spec.search.min_splits,
        purge_embargo_bars=spec.search.purge_embargo_bars,
    )
    labeled = label_split_entry.labeled
    splits = label_split_entry.splits
    effective_feature_columns = _usable_feature_columns(labeled, column_set)
    if not effective_feature_columns:
        return _blocked_real_trial_record(
            spec,
            template,
            trial_index=trial_index,
            started_at=started_at,
            completed_at=completed_at,
            blocker_code="feature_column_set_columns_missing",
            payload={
                "feature_column_set_id": column_set.feature_column_set_id,
                "label_horizon": label_horizon,
                "configured_feature_columns": list(column_set.columns),
                "effective_feature_columns": [],
            },
        )
    if regime_settings.regime_detector_type == "none":
        hmm_columns: tuple[str, ...] = ()
        hmm_spec: HmmMaterializationSpec | None = None
        hmm, hmm_cache_hit = _materialize_no_regime_with_cache(
            labeled,
            splits=splits,
            context=context,
            feature_pack_id=f"discovery_no_regime_{column_set.feature_column_set_id}",
            column_set_id=column_set.feature_column_set_id,
            label_horizon=label_horizon,
            min_splits=spec.search.min_splits,
            purge_embargo_bars=spec.search.purge_embargo_bars,
        )
    else:
        hmm_columns = _hmm_columns_for_trial(effective_feature_columns)
        hmm_spec = HmmMaterializationSpec(
            feature_columns=hmm_columns,
            n_states=int(trial_payload.get("hmm_state_count", 4)),
            posterior_threshold=float(trial_payload.get("hmm_posterior_threshold", 0.60)),
            entropy_threshold=float(trial_payload.get("hmm_entropy_threshold", 0.78)),
            flip_cooldown_bars=2,
            min_training_rows=max(32, len(hmm_columns) * 4),
            random_state=int(spec.budget.rng_seed),
            max_iter=100,
            covariance_type="diag",
            hmm_feature_pack_id=f"discovery_gmm_{column_set.feature_column_set_id}",
            regime_detector_type="gmm",
            true_hmm_backend_used=False,
        )
        hmm, hmm_cache_hit = _materialize_hmm_with_cache(
            labeled,
            splits=splits,
            spec=hmm_spec,
            context=context,
            cache_key=_hmm_cache_key(
                column_set=column_set,
                hmm_spec=hmm_spec,
                label_horizon=label_horizon,
                min_splits=spec.search.min_splits,
                purge_embargo_bars=spec.search.purge_embargo_bars,
            ),
        )
    k_value = int(trial_payload.get("k", 8))
    min_neighbor_count = max(1, min(k_value, int(trial_payload.get("min_neighbor_count", min(4, k_value)))))
    knn_spec = KnnStudySpec(
        feature_columns=effective_feature_columns,
        label_column="label_up",
        pnl_column="label_return",
        k=k_value,
        distance_metric=str(trial_payload.get("distance_metric") or "euclidean"),
        probability_threshold=float(trial_payload.get("probability_threshold", 0.55)),
        expected_value_threshold=float(trial_payload.get("expected_value_threshold", 0.0)),
        min_neighbor_count=min_neighbor_count,
        min_neighbor_agreement=float(trial_payload.get("min_neighbor_agreement", 0.55)),
        min_distance_quality=float(trial_payload.get("min_distance_quality", 0.01)),
        vote_margin_threshold=float(trial_payload.get("vote_margin_threshold", 0.05)),
        same_regime_only=regime_settings.same_regime_only,
        regime_mode=regime_settings.regime_mode,
        regime_detector_type=regime_settings.regime_detector_type,
        regime_model_backend=regime_settings.regime_model_backend,
        regime_gate_enabled=regime_settings.regime_gate_enabled,
        same_regime_neighbor_pool_enabled=regime_settings.same_regime_neighbor_pool_enabled,
        true_hmm_backend_used=regime_settings.true_hmm_backend_used,
        feature_column_set_id=column_set.feature_column_set_id,
        label_horizon=label_horizon,
    )
    knn_source_identity = _knn_source_identity(
        spec=spec,
        column_set=column_set,
        context=context,
        hmm_manifest=hmm.manifest,
        interval_ms=interval_ms,
    )
    include_neighbor_diagnostics = spec.execution.persist_trial_artifacts == "all"
    knn: KnnStudyResult | None
    base_knn_for_screening: KnnStudyResult | None = None
    if include_neighbor_diagnostics:
        knn, knn_base_cache_hit = _materialize_knn_threshold_view_with_cache(
            hmm.frame,
            splits=splits,
            spec=knn_spec,
            context=context,
            source_identity=knn_source_identity,
            neighbor_cache_k_limit=max(spec.search.k_values or (k_value,)),
            include_neighbor_diagnostics=True,
        )
        knn_manifest = dict(knn.manifest)
        metrics = _knn_trial_metrics(
            knn.frame,
            search=spec.search,
            label_horizon_bars=int(knn_manifest.get("label_horizon_bars") or 1),
        )
    else:
        base_knn, base_metric_view, knn_base_cache_hit = _materialize_knn_base_with_cache(
            hmm.frame,
            splits=splits,
            spec=knn_spec,
            context=context,
            source_identity=knn_source_identity,
            neighbor_cache_k_limit=max(spec.search.k_values or (k_value,)),
        )
        base_knn_for_screening = base_knn
        knn = None
        knn_manifest = dict(base_knn.manifest)
        knn_manifest["spec"] = knn_spec.to_payload()
        knn_manifest["spec_sha256"] = knn_spec.spec_sha256()
        knn_manifest["knn_base_cache_hit"] = bool(knn_base_cache_hit)
        knn_manifest["threshold_metrics_from_base_knn"] = True
        knn_manifest["neighbor_diagnostics_included"] = False
        metrics = _knn_threshold_metrics_from_view(
            base_metric_view,
            spec=knn_spec,
            search=spec.search,
            label_horizon_bars=int(knn_manifest.get("label_horizon_bars") or 1),
        )
    ledger_kind = "interesting" if metrics["passed"] else "blocked"
    blocker_code = "" if metrics["passed"] else str(metrics["primary_blocker"])
    persist_artifacts = _persist_trial_artifacts(spec.execution.persist_trial_artifacts, ledger_kind=ledger_kind)
    hmm_artifact_payload: dict[str, Any] = {"hmm_artifact_persisted": False, "regime_artifact_persisted": False}
    knn_artifact_payload: dict[str, Any] = {"knn_artifact_persisted": False}
    if spec.execution.persist_trial_artifacts == "interesting_only" and ledger_kind == "interesting":
        hmm_artifact_payload["trial_artifacts_deferred"] = True
        knn_artifact_payload["trial_artifacts_deferred"] = True
        knn_artifact_payload["artifact_deferred_reason"] = "exact_sweep_screening_defers_heavy_per_trial_artifacts"
    if persist_artifacts:
        if not include_neighbor_diagnostics:
            if base_knn_for_screening is None:
                raise RuntimeError("screening KNN base missing before interesting-only artifact write")
            knn = _threshold_knn_result(base_knn_for_screening, spec=knn_spec, cache_hit=knn_base_cache_hit)
            knn_manifest = dict(knn.manifest)
            knn_manifest["threshold_metrics_from_base_knn"] = True
        if knn is None:
            raise RuntimeError("knn artifacts requested before KNN predictions were materialized")
        knn_artifacts = write_knn_study_artifacts(trial_dir / "knn", knn)
        if spec.execution.persist_trial_artifacts == "all":
            hmm_artifacts = write_hmm_materialization_artifacts(trial_dir / "hmm", hmm)
            hmm_artifact_payload = {
                "hmm_artifact_persisted": True,
                "hmm_manifest_path": str(hmm_artifacts.manifest_path),
                "hmm_regime_posteriors_path": str(hmm_artifacts.regime_posteriors_path),
                "hmm_split_summary_path": str(hmm_artifacts.split_summary_path),
                "regime_artifact_persisted": True,
                "regime_manifest_path": str(hmm_artifacts.manifest_path),
                "regime_posteriors_path": str(hmm_artifacts.regime_posteriors_path),
                "regime_split_summary_path": str(hmm_artifacts.split_summary_path),
            }
        else:
            hmm_artifact_payload = {
                "hmm_artifact_persisted": False,
                "hmm_artifact_deferred_reason": "predictions_only_policy_persists_knn_predictions_without_hmm_posteriors",
                "regime_artifact_persisted": False,
                "regime_artifact_deferred_reason": "predictions_only_policy_persists_knn_predictions_without_regime_posteriors",
            }
        knn_artifact_payload = {
            "knn_artifact_persisted": True,
            "knn_manifest_path": str(knn_artifacts.manifest_path),
            "knn_predictions_path": str(knn_artifacts.predictions_path),
        }
    accounting_payload: dict[str, Any] = {}
    if not persist_artifacts:
        accounting_payload = {"strategy_accounting_persisted": False}
    else:
        try:
            from tradingbotsuite.research_discovery.strategy_integration import (
                account_hmm_knn_local_analog_strategy,
                write_strategy_accounting_artifacts,
            )

            accounting = account_hmm_knn_local_analog_strategy(
                knn.frame,
                symbol=spec.symbol,
                holding_window=_holding_window_from_label_horizon(label_horizon),
                strategy_config={
                    "probability_threshold": knn_spec.probability_threshold,
                    "expected_value_threshold": knn_spec.expected_value_threshold,
                    "min_neighbor_count": knn_spec.min_neighbor_count,
                    "min_neighbor_agreement": knn_spec.min_neighbor_agreement,
                    "min_neighbor_distance_quality": knn_spec.min_distance_quality,
                    "min_vote_margin": knn_spec.vote_margin_threshold,
                    "spacing_bars": 1,
                },
                executed_trade_count=int(metrics["trade_count"]),
            )
            accounting_artifacts = write_strategy_accounting_artifacts(trial_dir / "strategy_accounting", accounting)
            accounting_payload = {
                "strategy_accounting_persisted": True,
                "strategy_accounting_manifest_path": str(accounting_artifacts.manifest_path),
                "strategy_signal_count": int(accounting.manifest["plugin_signal_count"]),
                "strategy_executable_signal_count": int(accounting.manifest["backtest_executable_signal_count"]),
            }
        except Exception as exc:
            accounting_payload = {"strategy_accounting_persisted": False, "strategy_accounting_error": str(exc)}

    payload = {
        **trial_payload,
        "placeholder_trial": False,
        "discovery_score_policy_version": DISCOVERY_SCORE_POLICY_VERSION,
        "feature_column_set_id": column_set.feature_column_set_id,
        "registered_feature_set_id": column_set.registered_feature_set_id,
        "configured_feature_columns": list(column_set.columns),
        "effective_feature_columns": list(effective_feature_columns),
        "pruned_feature_column_count": int(len(column_set.columns) - len(effective_feature_columns)),
        "hmm_state_count": int(hmm_spec.n_states) if hmm_spec is not None else 0,
        "hmm_posterior_threshold": float(hmm_spec.posterior_threshold) if hmm_spec is not None else None,
        "hmm_entropy_threshold": float(hmm_spec.entropy_threshold) if hmm_spec is not None else None,
        "regime_state_count": int(hmm_spec.n_states) if hmm_spec is not None else 0,
        "regime_posterior_threshold": float(hmm_spec.posterior_threshold) if hmm_spec is not None else None,
        "regime_entropy_threshold": float(hmm_spec.entropy_threshold) if hmm_spec is not None else None,
        "regime_mode": regime_settings.regime_mode,
        "regime_detector_type": regime_settings.regime_detector_type,
        "regime_model_backend": regime_settings.regime_model_backend,
        "regime_gate_enabled": regime_settings.regime_gate_enabled,
        "same_regime_neighbor_pool_enabled": regime_settings.same_regime_neighbor_pool_enabled,
        "same_regime_only": regime_settings.same_regime_only,
        "true_hmm_backend_used": regime_settings.true_hmm_backend_used,
        "label_horizon": label_horizon,
        "label_split_cache_hit": bool(label_split_cache_hit),
        "hmm_cache_hit": bool(hmm_cache_hit),
        "regime_cache_hit": bool(hmm_cache_hit),
        "neighbor_cache_hit": bool(int(knn_manifest.get("neighbor_cache_hit_count") or 0) > 0),
        "neighbor_cache_lookup_count": int(knn_manifest.get("neighbor_cache_lookup_count") or 0),
        "neighbor_cache_hit_count": int(knn_manifest.get("neighbor_cache_hit_count") or 0),
        "knn_base_cache_hit": bool(knn_base_cache_hit),
        "neighbor_diagnostics_included": bool(knn_manifest.get("neighbor_diagnostics_included", True)),
        "threshold_metrics_from_base_knn": bool(knn_manifest.get("threshold_metrics_from_base_knn", False)),
        "distance_metric": knn_spec.distance_metric,
        "k": int(knn_spec.k),
        "min_neighbor_count": int(knn_spec.min_neighbor_count),
        "trade_count": int(metrics["trade_count"]),
        "accepted_bar_count": int(metrics["accepted_bar_count"]),
        "independent_event_count": int(metrics["independent_event_count"]),
        "suppressed_overlap_count": int(metrics["suppressed_overlap_count"]),
        "overlap_ratio": float(metrics["overlap_ratio"]),
        "event_signal_rate": float(metrics["event_signal_rate"]),
        "side_collapse_ratio": float(metrics["side_collapse_ratio"]),
        "near_signal_ceiling": bool(metrics["near_signal_ceiling"]),
        "long_independent_event_count": int(metrics["long_independent_event_count"]),
        "short_independent_event_count": int(metrics["short_independent_event_count"]),
        "event_spacing_bars": int(metrics["event_spacing_bars"]),
        "signal_rate": float(metrics["signal_rate"]),
        "realized_expectancy": float(metrics["realized_expectancy"]),
        "independent_event_expectancy": float(metrics["independent_event_expectancy"]),
        "accepted_prediction_count": int(metrics["accepted_prediction_count"]),
        "evaluated_prediction_count": int(metrics["evaluated_prediction_count"]),
        "legacy_density_score": float(metrics["legacy_density_score"]),
        "discovery_screen_score_v2": float(metrics["discovery_screen_score_v2"]),
        "signal_rate_ceiling_penalty": float(metrics["signal_rate_ceiling_penalty"]),
        "overlap_penalty": float(metrics["overlap_penalty"]),
        "side_collapse_penalty": float(metrics["side_collapse_penalty"]),
        "final_score": float(metrics["final_score"]),
        "primary_blocker": str(metrics["primary_blocker"]),
        "blocker_reasons": list(metrics["blocker_reasons"]),
        **hmm_artifact_payload,
        **knn_artifact_payload,
        **accounting_payload,
    }
    return DiscoveryTrialRecord(
        run_id=spec.run_id,
        trial_id=template.trial_id,
        attempt_id=attempt_id,
        trial_index=trial_index,
        candidate_id=template.candidate_id,
        candidate_family=template.candidate_family,
        ledger_kind=ledger_kind,
        score=float(metrics["final_score"]),
        blocker_code=blocker_code,
        filter_blocker_code="",
        status="completed",
        started_at_utc=started_at,
        completed_at_utc=completed_at,
        payload=payload,
    )


def _blocked_real_trial_record(
    spec: DiscoveryRunSpec,
    template: DiscoveryTrialTemplate,
    *,
    trial_index: int,
    started_at: str,
    completed_at: str,
    blocker_code: str,
    payload: Mapping[str, Any] | None = None,
) -> DiscoveryTrialRecord:
    trial_payload = {**dict(template.payload), **dict(payload or {})}
    try:
        mode_payload = _regime_settings_from_trial_payload(trial_payload).to_payload()
    except ValueError:
        mode_payload = {}
    return DiscoveryTrialRecord(
        run_id=spec.run_id,
        trial_id=template.trial_id,
        attempt_id="attempt-001",
        trial_index=trial_index,
        candidate_id=template.candidate_id,
        candidate_family=template.candidate_family or REAL_DISCOVERY_TRIAL_KIND,
        ledger_kind="blocked",
        score=0.0,
        blocker_code=blocker_code,
        status="completed",
        started_at_utc=started_at,
        completed_at_utc=completed_at,
        payload={
            **trial_payload,
            **mode_payload,
            "placeholder_trial": False,
            "discovery_score_policy_version": DISCOVERY_SCORE_POLICY_VERSION,
            "trade_count": 0,
            "accepted_bar_count": 0,
            "independent_event_count": 0,
            "suppressed_overlap_count": 0,
            "overlap_ratio": 0.0,
            "event_signal_rate": 0.0,
            "side_collapse_ratio": 0.0,
            "near_signal_ceiling": False,
            "long_independent_event_count": 0,
            "short_independent_event_count": 0,
            "event_spacing_bars": 0,
            "signal_rate": 0.0,
            "realized_expectancy": 0.0,
            "independent_event_expectancy": 0.0,
            "accepted_prediction_count": 0,
            "evaluated_prediction_count": 0,
            "legacy_density_score": 0.0,
            "discovery_screen_score_v2": 0.0,
            "signal_rate_ceiling_penalty": 0.0,
            "overlap_penalty": 0.0,
            "side_collapse_penalty": 0.0,
            "final_score": 0.0,
            "hmm_artifact_persisted": False,
            "knn_artifact_persisted": False,
            "strategy_accounting_persisted": False,
        },
    )


def _regime_settings_from_trial_payload(payload: Mapping[str, Any]) -> Any:
    return regime_mode_settings(
        str(
            payload.get("regime_mode")
            or (
                "gmm_same_regime_neighbors"
                if _truthy(payload.get("same_regime_only", True))
                else "gmm_all_regime_neighbors_with_gate"
            )
        )
    )


def _load_discovery_dataset(spec: DiscoveryRunSpec) -> tuple[pd.DataFrame, dict[str, Any]]:
    if spec.data.dataset_path is not None:
        frame = pd.read_parquet(spec.data.dataset_path)
        return frame, {
            "source_type": "parquet_dataset",
            "dataset_path": str(spec.data.dataset_path),
            "dataset_sha256": _file_sha256(spec.data.dataset_path),
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
        }
    if not spec.data.dataset_manifest_paths:
        raise ValueError("real_discovery_data_required")
    manifest_path = Path(spec.data.dataset_manifest_paths[0]).expanduser().resolve()
    manifest = _read_json_object(manifest_path)
    validation = assert_valid_historical_fixture_pack_manifest(manifest, manifest_path=manifest_path)
    dataset_path = resolve_fixture_pack_cycle_dataset_path(manifest, manifest_path=manifest_path)
    frame = pd.read_parquet(dataset_path)
    return frame, {
        "source_type": "historical_fixture_pack",
        "manifest_path": str(manifest_path),
        "manifest_sha256": _file_sha256(manifest_path),
        "dataset_path": str(dataset_path),
        "dataset_sha256": _file_sha256(dataset_path),
        "fixture_id": validation.fixture_id,
        "row_count": validation.row_count,
        "validation": validation.to_payload(),
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
    }


def _sort_discovery_dataset(frame: pd.DataFrame) -> pd.DataFrame:
    if "bar_time_ms" in frame.columns:
        return frame.sort_values("bar_time_ms", kind="mergesort").reset_index(drop=True)
    if "time_ms" in frame.columns:
        return frame.sort_values("time_ms", kind="mergesort").reset_index(drop=True)
    return frame.reset_index(drop=True)


def _infer_interval_ms(frame: pd.DataFrame) -> int:
    if "bar_time_ms" not in frame.columns or len(frame) < 2:
        return 900_000
    times = pd.to_numeric(frame["bar_time_ms"], errors="coerce").dropna().sort_values(kind="mergesort")
    diffs = times.diff().dropna()
    diffs = diffs[diffs > 0]
    if diffs.empty:
        return 900_000
    return max(1, int(diffs.median()))


def _with_directional_labels(frame: pd.DataFrame, *, label_horizon: str, interval_ms: int) -> pd.DataFrame:
    if "close" not in frame.columns:
        raise ValueError("discovery_dataset_close_column_required")
    horizon_bars = _label_horizon_bars(label_horizon, interval_ms=interval_ms)
    result = frame.copy().reset_index(drop=True)
    close = pd.to_numeric(result["close"], errors="coerce")
    future_close = close.shift(-horizon_bars)
    event_end_time = pd.to_numeric(result["bar_time_ms"], errors="coerce").shift(-horizon_bars)
    label_return = (future_close / close) - 1.0
    result["label_return"] = label_return
    result["label_up"] = (label_return > 0.0).astype(float)
    result["label_event_end_time_ms"] = event_end_time
    result["label_horizon_bars"] = int(horizon_bars)
    if "source_row_index" not in result.columns:
        result["source_row_index"] = range(len(result))
    source = pd.to_numeric(result["source_row_index"], errors="coerce")
    fallback = pd.Series(range(len(result)), index=result.index)
    result["source_row_index"] = source.where(source.notna(), fallback).astype("int64")
    return result


def _label_horizon_bars(label_horizon: str, *, interval_ms: int) -> int:
    match = LABEL_HORIZON_RE.match(str(label_horizon))
    if not match:
        raise ValueError(f"invalid_label_horizon:{label_horizon}")
    value = float(match.group("value"))
    unit = match.group("unit").lower()
    if unit in {"bar", "bars", "b"}:
        return max(1, int(round(value)))
    if unit in {"m", "min", "minute", "minutes"}:
        horizon_ms = value * 60_000
    elif unit in {"h", "hour", "hours"}:
        horizon_ms = value * 60 * 60_000
    elif unit in {"d", "day", "days"}:
        horizon_ms = value * 24 * 60 * 60_000
    else:
        raise ValueError(f"invalid_label_horizon_unit:{label_horizon}")
    return max(1, int(round(horizon_ms / max(1, interval_ms))))


def _hmm_columns_for_trial(columns: tuple[str, ...]) -> tuple[str, ...]:
    preferred = (
        "log_return_1",
        "log_return_4",
        "trend_slope_20",
        "efficiency_ratio",
        "directional_slope_atr",
        "realized_volatility",
        "atr_percentile",
    )
    selected = tuple(column for column in preferred if column in columns)
    return selected or columns[: min(8, len(columns))]


def _usable_feature_columns(frame: pd.DataFrame, column_set: DiscoveryFeatureColumnSet) -> tuple[str, ...]:
    usable_columns = []
    for column in column_set.columns:
        if column not in frame.columns:
            continue
        values = pd.to_numeric(frame[column], errors="coerce")
        finite = values.loc[values.map(math.isfinite)]
        non_null_ratio = float(len(finite) / max(1, len(values)))
        if non_null_ratio < 0.05:
            continue
        if float(finite.nunique(dropna=True)) <= 1.0:
            continue
        usable_columns.append(column)
    return tuple(usable_columns)


def _feature_set_preflight_reason(frame: pd.DataFrame, column_set: DiscoveryFeatureColumnSet) -> str:
    usable_columns = _usable_feature_columns(frame, column_set)
    if len(usable_columns) < 2:
        return "feature_set_preflight_insufficient_finite_variant_columns"
    hmm_columns = _hmm_columns_for_trial(usable_columns)
    if len(hmm_columns) < 2:
        return "feature_set_preflight_insufficient_hmm_columns"
    return ""


def _knn_trial_metrics(frame: pd.DataFrame, *, search: Any, label_horizon_bars: int = 1) -> dict[str, Any]:
    skip_reason = frame["knn_skip_reason"].astype(str)
    evaluated_count = int(skip_reason.ne("not_evaluated").sum())
    accepted_mask = frame["accepted_by_knn"].map(_truthy).to_numpy(dtype=bool) & skip_reason.map(_skip_reason_clear).to_numpy(dtype=bool)
    return _knn_metrics_from_accepted_mask(
        frame,
        accepted_mask,
        evaluated_count=evaluated_count,
        search=search,
        label_horizon_bars=label_horizon_bars,
    )


def _knn_metrics_from_accepted_mask(
    frame: pd.DataFrame,
    accepted_mask: np.ndarray,
    *,
    evaluated_count: int,
    search: Any,
    label_horizon_bars: int = 1,
) -> dict[str, Any]:
    accepted = frame.loc[np.asarray(accepted_mask, dtype=bool), _metric_accounting_columns(frame)].copy()
    returns = _side_adjusted_label_returns(accepted)
    accepted_bar_count = int(len(returns))
    accepted_count = int(len(accepted))
    signal_rate = float(accepted_bar_count / max(1, len(frame)))
    accepted_bar_expectancy = float(returns.mean()) if accepted_bar_count else 0.0
    accepted_bar_gross_return = float(returns.sum()) if accepted_bar_count else 0.0
    event_accounting = account_independent_events(
        accepted,
        total_row_count=len(frame),
        label_horizon_bars=label_horizon_bars,
        max_signal_rate=float(search.max_signal_rate),
    )
    trade_count = int(event_accounting.independent_event_count)
    realized_expectancy = float(event_accounting.independent_event_expectancy)
    gross_return = float(event_accounting.gross_independent_event_return)
    accepted_bar_neighbor_quality = _safe_mean(accepted.get("neighbor_distance_quality")) if not accepted.empty else 0.0
    accepted_bar_vote_margin = _safe_mean(accepted.get("knn_vote_margin")) if not accepted.empty else 0.0
    avg_neighbor_quality = float(event_accounting.avg_independent_neighbor_quality)
    avg_vote_margin = float(event_accounting.avg_independent_vote_margin)
    legacy_density_score = (
        accepted_bar_expectancy
        + (0.05 * math.log1p(accepted_bar_count))
        + (0.01 * accepted_bar_neighbor_quality)
        + (0.01 * accepted_bar_vote_margin)
    )
    ceiling = max(float(search.max_signal_rate), 1e-12)
    signal_rate_ceiling_penalty = max(0.0, (signal_rate - (0.80 * ceiling)) / ceiling) * 0.05
    overlap_penalty = float(event_accounting.overlap_ratio) * 0.10
    side_collapse_penalty = max(0.0, float(event_accounting.side_collapse_ratio) - 0.80) * 0.25
    discovery_screen_score_v2 = (
        realized_expectancy
        + (0.05 * math.log1p(trade_count))
        + (0.01 * avg_neighbor_quality)
        + (0.01 * avg_vote_margin)
        - signal_rate_ceiling_penalty
        - overlap_penalty
        - side_collapse_penalty
    )
    reasons: list[str] = []
    if trade_count < int(search.min_trade_count):
        reasons.append("independent_event_count_below_floor")
    if signal_rate < float(search.min_signal_rate):
        reasons.append("signal_rate_below_discovery_floor")
    if signal_rate > float(search.max_signal_rate):
        reasons.append("signal_rate_above_discovery_ceiling")
    if event_accounting.near_signal_ceiling:
        reasons.append("signal_rate_near_ceiling")
    if event_accounting.overlap_ratio > 0.50 and accepted_bar_count >= int(search.min_trade_count):
        reasons.append("overlap_ratio_above_ceiling")
    if event_accounting.side_collapse_ratio >= 0.95 and trade_count >= max(4, int(search.min_trade_count)):
        reasons.append("side_collapse_ratio_above_ceiling")
    if realized_expectancy < float(search.min_realized_expectancy):
        reasons.append("realized_expectancy_below_discovery_floor")
    if accepted_count == 0:
        reasons.append("no_accepted_knn_predictions")
    return {
        "trade_count": trade_count,
        "accepted_bar_count": accepted_bar_count,
        "independent_event_count": event_accounting.independent_event_count,
        "suppressed_overlap_count": event_accounting.suppressed_overlap_count,
        "overlap_ratio": event_accounting.overlap_ratio,
        "event_signal_rate": event_accounting.event_signal_rate,
        "long_independent_event_count": event_accounting.long_independent_event_count,
        "short_independent_event_count": event_accounting.short_independent_event_count,
        "event_spacing_bars": event_accounting.event_spacing_bars,
        "side_collapse_ratio": event_accounting.side_collapse_ratio,
        "near_signal_ceiling": event_accounting.near_signal_ceiling,
        "accepted_prediction_count": accepted_count,
        "evaluated_prediction_count": evaluated_count,
        "signal_rate": signal_rate,
        "realized_expectancy": realized_expectancy,
        "accepted_bar_realized_expectancy": accepted_bar_expectancy,
        "accepted_bar_gross_realized_return": accepted_bar_gross_return,
        "independent_event_expectancy": event_accounting.independent_event_expectancy,
        "gross_realized_return": gross_return,
        "avg_neighbor_distance_quality": avg_neighbor_quality,
        "avg_vote_margin": avg_vote_margin,
        "legacy_density_score": float(legacy_density_score),
        "discovery_screen_score_v2": float(discovery_screen_score_v2),
        "signal_rate_ceiling_penalty": float(signal_rate_ceiling_penalty),
        "overlap_penalty": float(overlap_penalty),
        "side_collapse_penalty": float(side_collapse_penalty),
        "final_score": float(discovery_screen_score_v2),
        "passed": not reasons,
        "primary_blocker": reasons[0] if reasons else "",
        "blocker_reasons": reasons,
    }


def _knn_metrics_from_threshold_view(
    view: _KnnThresholdMetricView,
    accepted_mask: np.ndarray,
    *,
    search: Any,
    label_horizon_bars: int = 1,
) -> dict[str, Any]:
    accepted = np.asarray(accepted_mask, dtype=bool)
    returns_mask = accepted & view.label_return_finite & np.isfinite(view.side_adjusted_return)
    returns = view.side_adjusted_return[returns_mask]
    accepted_bar_count = int(len(returns))
    accepted_count = int(np.count_nonzero(accepted))
    signal_rate = float(accepted_bar_count / max(1, view.row_count))
    accepted_bar_expectancy = float(returns.mean()) if accepted_bar_count else 0.0
    accepted_bar_gross_return = float(returns.sum()) if accepted_bar_count else 0.0
    event_accounting = account_independent_events_arrays(
        accepted_mask=accepted,
        symbol_codes=view.symbol_codes,
        source_row_index=view.source_row_index,
        p_up_barrier=view.p_up_barrier,
        p_down_barrier=view.p_down_barrier,
        side_adjusted_return=view.side_adjusted_return,
        neighbor_distance_quality=view.distance_quality,
        knn_vote_margin=view.vote_margin,
        total_row_count=view.row_count,
        label_horizon_bars=label_horizon_bars,
        max_signal_rate=float(search.max_signal_rate),
    )
    trade_count = int(event_accounting.independent_event_count)
    realized_expectancy = float(event_accounting.independent_event_expectancy)
    accepted_bar_neighbor_quality = _safe_mean_array(view.distance_quality[accepted]) if accepted_count else 0.0
    accepted_bar_vote_margin = _safe_mean_array(view.vote_margin[accepted]) if accepted_count else 0.0
    avg_neighbor_quality = float(event_accounting.avg_independent_neighbor_quality)
    avg_vote_margin = float(event_accounting.avg_independent_vote_margin)
    legacy_density_score = (
        accepted_bar_expectancy
        + (0.05 * math.log1p(accepted_bar_count))
        + (0.01 * accepted_bar_neighbor_quality)
        + (0.01 * accepted_bar_vote_margin)
    )
    ceiling = max(float(search.max_signal_rate), 1e-12)
    signal_rate_ceiling_penalty = max(0.0, (signal_rate - (0.80 * ceiling)) / ceiling) * 0.05
    overlap_penalty = float(event_accounting.overlap_ratio) * 0.10
    side_collapse_penalty = max(0.0, float(event_accounting.side_collapse_ratio) - 0.80) * 0.25
    discovery_screen_score_v2 = (
        realized_expectancy
        + (0.05 * math.log1p(trade_count))
        + (0.01 * avg_neighbor_quality)
        + (0.01 * avg_vote_margin)
        - signal_rate_ceiling_penalty
        - overlap_penalty
        - side_collapse_penalty
    )
    reasons: list[str] = []
    if trade_count < int(search.min_trade_count):
        reasons.append("independent_event_count_below_floor")
    if signal_rate < float(search.min_signal_rate):
        reasons.append("signal_rate_below_discovery_floor")
    if signal_rate > float(search.max_signal_rate):
        reasons.append("signal_rate_above_discovery_ceiling")
    if event_accounting.near_signal_ceiling:
        reasons.append("signal_rate_near_ceiling")
    if event_accounting.overlap_ratio > 0.50 and accepted_bar_count >= int(search.min_trade_count):
        reasons.append("overlap_ratio_above_ceiling")
    if event_accounting.side_collapse_ratio >= 0.95 and trade_count >= max(4, int(search.min_trade_count)):
        reasons.append("side_collapse_ratio_above_ceiling")
    if realized_expectancy < float(search.min_realized_expectancy):
        reasons.append("realized_expectancy_below_discovery_floor")
    if accepted_count == 0:
        reasons.append("no_accepted_knn_predictions")
    return {
        "trade_count": trade_count,
        "accepted_bar_count": accepted_bar_count,
        "independent_event_count": event_accounting.independent_event_count,
        "suppressed_overlap_count": event_accounting.suppressed_overlap_count,
        "overlap_ratio": event_accounting.overlap_ratio,
        "event_signal_rate": event_accounting.event_signal_rate,
        "long_independent_event_count": event_accounting.long_independent_event_count,
        "short_independent_event_count": event_accounting.short_independent_event_count,
        "event_spacing_bars": event_accounting.event_spacing_bars,
        "side_collapse_ratio": event_accounting.side_collapse_ratio,
        "near_signal_ceiling": event_accounting.near_signal_ceiling,
        "accepted_prediction_count": accepted_count,
        "evaluated_prediction_count": view.evaluated_count,
        "signal_rate": signal_rate,
        "realized_expectancy": realized_expectancy,
        "accepted_bar_realized_expectancy": accepted_bar_expectancy,
        "accepted_bar_gross_realized_return": accepted_bar_gross_return,
        "independent_event_expectancy": event_accounting.independent_event_expectancy,
        "gross_realized_return": float(event_accounting.gross_independent_event_return),
        "avg_neighbor_distance_quality": avg_neighbor_quality,
        "avg_vote_margin": avg_vote_margin,
        "legacy_density_score": float(legacy_density_score),
        "discovery_screen_score_v2": float(discovery_screen_score_v2),
        "signal_rate_ceiling_penalty": float(signal_rate_ceiling_penalty),
        "overlap_penalty": float(overlap_penalty),
        "side_collapse_penalty": float(side_collapse_penalty),
        "final_score": float(discovery_screen_score_v2),
        "passed": not reasons,
        "primary_blocker": reasons[0] if reasons else "",
        "blocker_reasons": reasons,
    }


def _metric_accounting_columns(frame: pd.DataFrame) -> list[str]:
    return [
        column
        for column in (
            "symbol",
            "source_row_index",
            "p_up_barrier",
            "p_down_barrier",
            "label_return",
            "neighbor_distance_quality",
            "knn_vote_margin",
        )
        if column in frame.columns
    ]


def _side_adjusted_label_returns(frame: pd.DataFrame) -> pd.Series:
    if frame.empty or "label_return" not in frame:
        return pd.Series(dtype=float)
    returns = pd.to_numeric(frame["label_return"], errors="coerce")
    p_up = pd.to_numeric(frame.get("p_up_barrier", pd.Series(0.5, index=frame.index)), errors="coerce")
    p_down = pd.to_numeric(frame.get("p_down_barrier", pd.Series(0.5, index=frame.index)), errors="coerce")
    side_multiplier = pd.Series(1.0, index=frame.index, dtype=float)
    side_multiplier.loc[p_down > p_up] = -1.0
    return (returns * side_multiplier).dropna()


def _holding_window_from_label_horizon(label_horizon: str) -> str:
    normalized = str(label_horizon).strip().lower()
    if normalized in {"1h", "4h", "12h", "24h", "72h"}:
        return normalized
    if normalized in {"1d", "24 hours", "24hour", "24hours"}:
        return "24h"
    return "4h"


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _skip_reason_clear(value: Any) -> bool:
    if value is None or pd.isna(value):
        return True
    return str(value).strip().lower() in {"", "none", "nan", "null"}


def _safe_mean(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, pd.Series):
        series = pd.to_numeric(value, errors="coerce").dropna()
    else:
        series = pd.to_numeric(pd.Series([value]), errors="coerce").dropna()
    return float(series.mean()) if not series.empty else 0.0


def _safe_mean_array(value: np.ndarray) -> float:
    array = np.asarray(value, dtype=float)
    finite = array[np.isfinite(array)]
    return float(finite.mean()) if len(finite) else 0.0


def _safe_path_part(value: str) -> str:
    safe = "".join(char.lower() if char.isalnum() else "-" for char in str(value)).strip("-")
    return safe[:96] or "artifact"


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_json_sha256(payload: Mapping[str, Any]) -> str:
    return sha256(
        json.dumps(dict(payload), sort_keys=True, default=str, allow_nan=False).encode("utf-8")
    ).hexdigest()


def _load_existing_trial_records(trial_dir: Path, *, run_id: str) -> dict[str, DiscoveryTrialRecord]:
    records: dict[str, DiscoveryTrialRecord] = {}
    if not trial_dir.exists():
        return records
    for path in sorted(trial_dir.glob("*.json")):
        record = read_trial_record(path)
        if record.run_id != run_id:
            raise ValueError(f"trial record belongs to a different run_id: {path}")
        if record.trial_id in records:
            raise ValueError(f"duplicate trial record id: {record.trial_id}")
        records[record.trial_id] = record
    return records


def _load_resume_catalog(
    trial_dir: Path,
    *,
    run_id: str,
    state: DiscoveryRunState,
    updated_at_utc: str,
) -> _ResumeCatalog:
    full_record_load_limit = _resume_full_record_load_limit()
    trial_paths = _trial_record_paths_by_id(trial_dir)
    completed_ids = set(state.completed_trial_ids)
    hash_ids = {str(item) for item in state.completed_trial_hashes}
    missing_hashes = sorted(completed_ids - hash_ids, key=_trial_id_sort_key)
    if missing_hashes:
        raise ValueError(f"completed trial state hash missing on resume: {','.join(missing_hashes)}")
    missing_completed = sorted((trial_id for trial_id in completed_ids if trial_id not in trial_paths), key=_trial_id_sort_key)
    if missing_completed:
        raise ValueError(f"completed trial record missing on resume: {','.join(missing_completed)}")
    missing_hash_records = sorted((hash_ids - set(trial_paths)), key=_trial_id_sort_key)
    if missing_hash_records:
        raise ValueError(f"completed trial hash references missing record: {','.join(missing_hash_records)}")

    if len(trial_paths) <= full_record_load_limit:
        records = _load_existing_trial_records(trial_dir, run_id=run_id)
        _assert_real_trial_score_policy_compatible(records)
        _assert_state_trial_records_present(state, records)
        merged = _merge_state_records(state, records, updated_at_utc=updated_at_utc)
        return _ResumeCatalog(
            records=records,
            state=merged,
            fully_hydrated=True,
            mode="full_trial_record_hydration",
            trial_file_count=len(trial_paths),
            recovered_trial_file_count=max(0, len(records) - len(completed_ids)),
            full_record_load_limit=full_record_load_limit,
        )

    lagging_trial_ids = sorted((set(trial_paths) - completed_ids), key=_trial_id_sort_key)
    records = _load_existing_trial_records_by_id(trial_paths, run_id=run_id, trial_ids=lagging_trial_ids)
    _assert_real_trial_score_policy_compatible(records)
    merged = _merge_state_records(state, records, updated_at_utc=updated_at_utc)
    return _ResumeCatalog(
        records=records,
        state=merged,
        fully_hydrated=False,
        mode="state_checkpoint_with_lagging_trial_file_recovery",
        trial_file_count=len(trial_paths),
        recovered_trial_file_count=len(records),
        full_record_load_limit=full_record_load_limit,
    )


def _trial_record_paths_by_id(trial_dir: Path) -> dict[str, Path]:
    if not trial_dir.exists():
        return {}
    paths: dict[str, Path] = {}
    for path in sorted(trial_dir.glob("*.json")):
        trial_id = path.stem
        if trial_id in paths:
            raise ValueError(f"duplicate trial record id: {trial_id}")
        paths[trial_id] = path
    return paths


def _load_existing_trial_records_by_id(
    trial_paths: Mapping[str, Path],
    *,
    run_id: str,
    trial_ids: list[str],
) -> dict[str, DiscoveryTrialRecord]:
    records: dict[str, DiscoveryTrialRecord] = {}
    for trial_id in trial_ids:
        path = trial_paths.get(trial_id)
        if path is None:
            raise ValueError(f"completed trial record missing on resume: {trial_id}")
        record = read_trial_record(path)
        if record.run_id != run_id:
            raise ValueError(f"trial record belongs to a different run_id: {path}")
        records[record.trial_id] = record
    return records


def _resume_full_record_load_limit() -> int:
    raw = os.getenv(DISCOVERY_RESUME_FULL_RECORD_LOAD_LIMIT_ENV)
    if raw is not None and str(raw).strip():
        try:
            return max(0, int(str(raw).strip()))
        except ValueError:
            return DEFAULT_DISCOVERY_RESUME_FULL_RECORD_LOAD_LIMIT
    return DEFAULT_DISCOVERY_RESUME_FULL_RECORD_LOAD_LIMIT


def _trial_id_sort_key(trial_id: str) -> tuple[int, str]:
    match = re.search(r"(\d+)$", str(trial_id))
    if match:
        return (int(match.group(1)), str(trial_id))
    return (0, str(trial_id))


def _merge_state_records(
    state: DiscoveryRunState,
    records: Mapping[str, DiscoveryTrialRecord],
    *,
    updated_at_utc: str,
) -> DiscoveryRunState:
    merged = state
    for record in _ordered_records(records.values()):
        merged = merged.with_completed_trial(record, updated_at_utc=updated_at_utc)
    return merged


def _assert_state_trial_records_present(
    state: DiscoveryRunState,
    records: Mapping[str, DiscoveryTrialRecord],
) -> None:
    completed_ids = set(state.completed_trial_ids)
    hash_ids = set(str(item) for item in state.completed_trial_hashes)
    missing_completed = sorted(completed_ids - set(records))
    missing_hash_records = sorted(hash_ids - set(records))
    missing_hashes = sorted(completed_ids - hash_ids)
    if missing_completed:
        raise ValueError(f"completed trial record missing on resume: {','.join(missing_completed)}")
    if missing_hash_records:
        raise ValueError(f"completed trial hash references missing record: {','.join(missing_hash_records)}")
    if missing_hashes:
        raise ValueError(f"completed trial state hash missing on resume: {','.join(missing_hashes)}")


def _assert_real_trial_score_policy_compatible(records: Mapping[str, DiscoveryTrialRecord]) -> None:
    incompatible = []
    for trial_id, record in records.items():
        payload = dict(record.payload or {})
        is_real_discovery = str(payload.get("trial_kind") or "") in REAL_DISCOVERY_TRIAL_KINDS or (
            str(record.candidate_family or "") in REAL_DISCOVERY_TRIAL_KINDS
            and payload.get("placeholder_trial") is False
        )
        if not is_real_discovery:
            continue
        if str(payload.get("discovery_score_policy_version") or "") != DISCOVERY_SCORE_POLICY_VERSION:
            incompatible.append(str(trial_id))
    if incompatible:
        raise ValueError(
            "existing real discovery trial records require a new run_id after score policy upgrade: "
            + ",".join(sorted(incompatible))
        )


def _write_ledgers(
    *,
    records: list[DiscoveryTrialRecord],
    interesting_path: Path,
    blocked_path: Path,
    filter_blockers_path: Path,
) -> None:
    interesting = [record for record in records if record.ledger_kind == "interesting"]
    blocked = [record for record in records if record.ledger_kind == "blocked"]
    filter_blocked = [record for record in records if record.ledger_kind == "filter_blocked"]
    _record_frame(interesting).to_parquet(interesting_path, index=False)
    _record_frame(blocked).to_parquet(blocked_path, index=False)
    _record_frame(filter_blocked).to_parquet(filter_blockers_path, index=False)


def _write_ledgers_from_trial_dir(
    *,
    trial_dir: Path,
    run_id: str,
    interesting_path: Path,
    blocked_path: Path,
    filter_blockers_path: Path,
) -> _LedgerSummary:
    rows_by_kind: dict[str, list[dict[str, Any]]] = {
        "interesting": [],
        "blocked": [],
        "filter_blocked": [],
    }
    observed_modes: set[str] = set()
    observed_detectors: set[str] = set()
    observed_backends: set[str] = set()
    completed_trials = 0
    failed_trials = 0
    durable_trial_records = 0
    for path in sorted(Path(trial_dir).glob("*.json"), key=lambda item: _trial_id_sort_key(item.stem)):
        record = read_trial_record(path)
        if record.run_id != run_id:
            raise ValueError(f"trial record belongs to a different run_id: {path}")
        _assert_real_trial_score_policy_compatible({record.trial_id: record})
        durable_trial_records += 1
        if record.status == "completed":
            completed_trials += 1
        else:
            failed_trials += 1
        row = _ledger_row_from_record(record)
        if record.ledger_kind in rows_by_kind:
            rows_by_kind[record.ledger_kind].append(row)
        mode = str(record.payload.get("regime_mode") or "").strip()
        detector = str(record.payload.get("regime_detector_type") or "").strip()
        backend = str(record.payload.get("regime_model_backend") or "").strip()
        if mode:
            observed_modes.add(mode)
        if detector:
            observed_detectors.add(detector)
        if backend:
            observed_backends.add(backend)
    _ledger_frame_from_rows(rows_by_kind["interesting"]).to_parquet(interesting_path, index=False)
    _ledger_frame_from_rows(rows_by_kind["blocked"]).to_parquet(blocked_path, index=False)
    _ledger_frame_from_rows(rows_by_kind["filter_blocked"]).to_parquet(filter_blockers_path, index=False)
    return _LedgerSummary(
        counts={
            "completed_trials": completed_trials,
            "failed_trials": failed_trials,
            "durable_trial_records": durable_trial_records,
            "processed_trial_records": durable_trial_records,
            "interesting_candidates": len(rows_by_kind["interesting"]),
            "blocked_candidates": len(rows_by_kind["blocked"]),
            "filter_blockers": len(rows_by_kind["filter_blocked"]),
        },
        observed_trial_regime_modes=tuple(sorted(observed_modes)),
        observed_trial_regime_detector_types=tuple(sorted(observed_detectors)),
        observed_trial_regime_model_backends=tuple(sorted(observed_backends)),
    )


def _record_frame(records: list[DiscoveryTrialRecord]) -> pd.DataFrame:
    rows = [_ledger_row_from_record(record) for record in records]
    return _ledger_frame_from_rows(rows)


def _ledger_frame_from_rows(rows: list[Mapping[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows, columns=list(LEDGER_COLUMNS))
    for column in LEDGER_INT_COLUMNS:
        if column in frame.columns:
            frame[column] = pd.to_numeric(_empty_strings_to_na(frame[column]), errors="coerce").astype("Int64")
    for column in LEDGER_FLOAT_COLUMNS:
        if column in frame.columns:
            frame[column] = pd.to_numeric(_empty_strings_to_na(frame[column]), errors="coerce").astype("Float64")
    for column in LEDGER_BOOL_COLUMNS:
        if column in frame.columns:
            frame[column] = _empty_strings_to_na(frame[column]).astype("boolean")
    return frame


def _empty_strings_to_na(series: pd.Series) -> pd.Series:
    return series.replace({"": pd.NA, "none": pd.NA, "None": pd.NA, "nan": pd.NA, "NaN": pd.NA})


def _ledger_row_from_record(record: DiscoveryTrialRecord) -> dict[str, Any]:
    payload = record.to_payload()
    trial_payload = payload.get("payload") if isinstance(payload.get("payload"), Mapping) else {}
    return {column: payload.get(column, trial_payload.get(column, "")) for column in LEDGER_COLUMNS}


def _ordered_records(records: Any) -> list[DiscoveryTrialRecord]:
    return sorted(records, key=lambda record: (int(record.trial_index), str(record.trial_id)))


def _snapshot(
    output_dir: Path,
    *,
    spec: DiscoveryRunSpec,
    state: DiscoveryRunState,
    records: Mapping[str, DiscoveryTrialRecord],
    counts: Mapping[str, int] | None = None,
    counts_scope: str = "complete_loaded_records",
    sequence: int,
    created_at: datetime,
) -> Path:
    summary_counts = dict(counts or _record_counts(records))
    return write_snapshot(
        output_dir,
        run_id=spec.run_id,
        sequence=sequence,
        created_at=created_at,
        summary={
            "status": state.status,
            "discovery_mode": spec.discovery_mode,
            "symbol": spec.symbol,
            "timeframe": spec.timeframe,
            "budget_max_trials": spec.budget.max_trials,
            "search_space": discovery_search_space_summary(spec),
            "completed_trial_count": int(summary_counts.get("completed_trials", len(records))),
            "failed_trial_count": int(summary_counts.get("failed_trials", 0)),
            "durable_trial_record_count": int(summary_counts.get("durable_trial_records", len(records))),
            "processed_trial_record_count": int(summary_counts.get("processed_trial_records", len(records))),
            "counts": summary_counts,
            "counts_scope": counts_scope,
            "last_snapshot_path": state.last_snapshot_path,
        },
    )


def _record_counts(records: Mapping[str, DiscoveryTrialRecord]) -> dict[str, int]:
    values = list(records.values())
    completed_trials = sum(1 for record in values if record.status == "completed")
    failed_trials = sum(1 for record in values if record.status != "completed")
    return {
        "completed_trials": completed_trials,
        "failed_trials": failed_trials,
        "durable_trial_records": len(values),
        "processed_trial_records": len(values),
        "interesting_candidates": sum(1 for record in values if record.ledger_kind == "interesting"),
        "blocked_candidates": sum(1 for record in values if record.ledger_kind == "blocked"),
        "filter_blockers": sum(1 for record in values if record.ledger_kind == "filter_blocked"),
    }


def _counts_for_state(
    state: DiscoveryRunState,
    records: Mapping[str, DiscoveryTrialRecord],
    *,
    complete: bool,
) -> dict[str, int]:
    counts = _record_counts(records)
    if not complete:
        counts["completed_trials"] = max(int(counts.get("completed_trials", 0)), len(state.completed_trial_ids))
        counts["processed_trial_records"] = len(state.completed_trial_ids)
        counts["durable_trial_records"] = max(int(counts.get("durable_trial_records", 0)), len(state.completed_trial_ids))
    return counts


def _counts_scope(complete: bool) -> str:
    return "complete_loaded_records" if complete else "state_completed_with_partial_loaded_ledger_counts"


def _process_chunk_timing_summary(results: list[_ProcessChunkResult]) -> dict[str, Any]:
    if not results:
        return {
            "measured": False,
            "scope": "process_executor_chunks",
            "chunk_count": 0,
        }
    wall_values = [max(0.0, float(item.chunk_wall_seconds)) for item in results]
    cpu_values = [max(0.0, float(item.chunk_process_cpu_seconds)) for item in results]
    init_values = [
        max(0.0, float(item.worker_context_initialization_seconds))
        for item in results
        if item.worker_context_initialization_seconds is not None
    ]
    worker_pids = sorted({int(item.worker_pid) for item in results})
    total_records = sum(int(item.chunk_size) for item in results)
    total_wall = sum(wall_values)
    total_cpu = sum(cpu_values)
    return {
        "measured": True,
        "scope": "process_executor_chunks_excludes_parent_persistence",
        "chunk_count": int(len(results)),
        "worker_process_count": int(len(worker_pids)),
        "worker_pids": worker_pids[:64],
        "total_records": int(total_records),
        "chunk_size_min": int(min(item.chunk_size for item in results)),
        "chunk_size_max": int(max(item.chunk_size for item in results)),
        "chunk_wall_seconds_sum": float(total_wall),
        "chunk_wall_seconds_min": float(min(wall_values)),
        "chunk_wall_seconds_max": float(max(wall_values)),
        "chunk_process_cpu_seconds_sum": float(total_cpu),
        "chunk_process_cpu_seconds_min": float(min(cpu_values)),
        "chunk_process_cpu_seconds_max": float(max(cpu_values)),
        "chunk_process_cpu_percent_of_chunk_wall": float((total_cpu / total_wall) * 100.0) if total_wall > 0 else None,
        "worker_context_initialization_seconds_max": float(max(init_values)) if init_values else None,
        "worker_context_initialization_seconds_sum_unique_workers_approx": (
            float(sum({pid: value for pid, value in (
                (item.worker_pid, max(0.0, float(item.worker_context_initialization_seconds)))
                for item in results
                if item.worker_context_initialization_seconds is not None
            )}.values()))
            if init_values
            else None
        ),
    }


def _ledger_summary_from_records(
    records: Mapping[str, DiscoveryTrialRecord],
    *,
    completed_count: int | None = None,
) -> _LedgerSummary:
    counts = _record_counts(records)
    if completed_count is not None:
        counts["completed_trials"] = max(int(counts.get("completed_trials", 0)), int(completed_count))
        counts["processed_trial_records"] = int(completed_count)
        counts["durable_trial_records"] = max(int(counts.get("durable_trial_records", 0)), int(completed_count))
    return _LedgerSummary(
        counts=counts,
        observed_trial_regime_modes=tuple(
            sorted(
                {
                    str(record.payload.get("regime_mode")).strip()
                    for record in records.values()
                    if str(record.payload.get("regime_mode") or "").strip()
                }
            )
        ),
        observed_trial_regime_detector_types=tuple(
            sorted(
                {
                    str(record.payload.get("regime_detector_type")).strip()
                    for record in records.values()
                    if str(record.payload.get("regime_detector_type") or "").strip()
                }
            )
        ),
        observed_trial_regime_model_backends=tuple(
            sorted(
                {
                    str(record.payload.get("regime_model_backend")).strip()
                    for record in records.values()
                    if str(record.payload.get("regime_model_backend") or "").strip()
                }
            )
        ),
    )


def _snapshot_interval_due(previous: datetime, current: datetime, interval_minutes: int) -> bool:
    previous_utc = previous if previous.tzinfo is not None else previous.replace(tzinfo=current.tzinfo)
    current_utc = current if current.tzinfo is not None else current.replace(tzinfo=previous_utc.tzinfo)
    return current_utc - previous_utc >= timedelta(minutes=int(interval_minutes))
