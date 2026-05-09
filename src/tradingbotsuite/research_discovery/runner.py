from __future__ import annotations

import json
import math
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Mapping

import pandas as pd

from tradingbotsuite.backtesting.splits import build_purged_walk_forward_splits
from tradingbotsuite.config import AppConfig
from tradingbotsuite.data.historical_fixture_pack import (
    assert_valid_historical_fixture_pack_manifest,
    resolve_fixture_pack_cycle_dataset_path,
)
from tradingbotsuite.features.builders import materialize_registered_feature_set
from tradingbotsuite.research_discovery.feature_sets import (
    DiscoveryFeatureColumnSet,
    load_feature_column_set_manifest,
    validate_feature_column_set_manifest,
)
from tradingbotsuite.research_discovery.hmm_materialization import (
    HMM_POSTERIOR_COLUMNS,
    HmmMaterializationResult,
    HmmMaterializationSpec,
    materialize_split_safe_hmm_regimes,
    write_hmm_materialization_artifacts,
)
from tradingbotsuite.research_discovery.knn_study import (
    KnnStudySpec,
    materialize_regime_local_knn_predictions,
    write_knn_study_artifacts,
)
from tradingbotsuite.research_discovery.manifests import discovery_manifest_payload
from tradingbotsuite.research_discovery.snapshots import atomic_write_json, iso_utc, utc_now, write_snapshot
from tradingbotsuite.research_discovery.spec import (
    DiscoveryRunSpec,
    DiscoveryTrialTemplate,
    generated_trial_templates,
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
    "feature_column_set_id",
    "hmm_state_count",
    "label_horizon",
    "distance_metric",
    "k",
    "min_neighbor_count",
    "trade_count",
    "signal_rate",
    "realized_expectancy",
    "accepted_prediction_count",
    "evaluated_prediction_count",
    "final_score",
    "record_sha256",
)

LABEL_HORIZON_RE = re.compile(r"^\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>bars?|b|m|min|minute|minutes|h|hour|hours|d|day|days)\s*$")


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
    started = time.perf_counter()
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

    if output_dir.exists() and not state_path.exists() and any(output_dir.iterdir()):
        raise ValueError(f"discovery output directory is not empty and has no run_state.json: {output_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    for directory in (output_dir / "trials", output_dir / "snapshots", ledger_root):
        directory.mkdir(parents=True, exist_ok=True)

    resolved_spec_payload = spec.to_payload()
    if state_path.exists():
        state = read_run_state(state_path)
        if state.run_id != spec.run_id:
            raise ValueError("existing run_state.json belongs to a different run_id")
        if state.status == "completed":
            raise ValueError("completed discovery runs refuse overwrite")
        if not resume:
            raise ValueError("existing incomplete discovery run requires resume=True")
        _assert_resolved_spec_unchanged(resolved_spec_path, resolved_spec_payload)
    else:
        state = DiscoveryRunState.new(run_id=spec.run_id, created_at_utc=iso_utc(now()))
        atomic_write_json(resolved_spec_path, resolved_spec_payload)
        write_run_state(state_path, state)

    existing_records = _load_existing_trial_records(output_dir / "trials", run_id=spec.run_id)
    _assert_state_trial_records_present(state, existing_records)
    state = _merge_state_records(state, existing_records, updated_at_utc=iso_utc(now()))
    write_run_state(state_path, state)

    templates = generated_trial_templates(spec)
    real_context = _prepare_real_discovery_context(spec, output_dir=output_dir) if _real_discovery_requested(spec, templates) else None
    completed_ids = set(state.completed_trial_ids)
    executed_this_call = 0
    snapshot_paths: list[Path] = []
    batch_completed = 0

    _write_ledgers(
        records=_ordered_records(existing_records.values()),
        interesting_path=interesting_path,
        blocked_path=blocked_path,
        filter_blockers_path=filter_blockers_path,
    )
    last_snapshot_at = now()
    initial_snapshot = _snapshot(
        output_dir,
        spec=spec,
        state=state,
        records=existing_records,
        sequence=state.snapshot_count + 1,
        created_at=last_snapshot_at,
    )
    snapshot_paths.append(initial_snapshot)
    state = state.with_snapshot(path=initial_snapshot, updated_at_utc=iso_utc(now()))
    write_run_state(state_path, state)

    pending_trials = [
        (index, template)
        for index, template in enumerate(templates, start=1)
        if template.trial_id not in completed_ids
    ]
    if stop_after_trials is not None:
        pending_trials = pending_trials[: max(0, int(stop_after_trials))]
    worker_count = _effective_worker_count(spec.execution.max_workers, pending_trials)
    with (ThreadPoolExecutor(max_workers=worker_count) if worker_count > 1 else _NullExecutor()) as executor:
        cursor = 0
        while cursor < len(pending_trials):
            chunk = pending_trials[cursor : cursor + worker_count]
            cursor += len(chunk)
            if executor is None:
                records = [
                    _evaluate_discovery_trial(
                        spec,
                        template,
                        context=real_context,
                        trial_index=index,
                        clock=now,
                        output_dir=output_dir,
                    )
                    for index, template in chunk
                ]
            else:
                futures = [
                    executor.submit(
                        _evaluate_discovery_trial,
                        spec,
                        template,
                        context=real_context,
                        trial_index=index,
                        clock=now,
                        output_dir=output_dir,
                    )
                    for index, template in chunk
                ]
                records = [future.result() for future in futures]
            for record in records:
                trial_path = output_dir / "trials" / f"{record.trial_id}.json"
                write_trial_record(trial_path, record)
                existing_records[record.trial_id] = record
                state = state.with_completed_trial(record, updated_at_utc=iso_utc(now()))
                write_run_state(state_path, state)
                completed_ids.add(record.trial_id)
                executed_this_call += 1
                batch_completed += 1
                snapshot_at = now()
                if batch_completed >= spec.budget.trial_batch_size or _snapshot_interval_due(
                    last_snapshot_at,
                    snapshot_at,
                    spec.budget.snapshot_interval_minutes,
                ):
                    _write_ledgers(
                        records=_ordered_records(existing_records.values()),
                        interesting_path=interesting_path,
                        blocked_path=blocked_path,
                        filter_blockers_path=filter_blockers_path,
                    )
                    snapshot = _snapshot(
                        output_dir,
                        spec=spec,
                        state=state,
                        records=existing_records,
                        sequence=state.snapshot_count + 1,
                        created_at=snapshot_at,
                    )
                    snapshot_paths.append(snapshot)
                    state = state.with_snapshot(path=snapshot, updated_at_utc=iso_utc(now()))
                    write_run_state(state_path, state)
                    batch_completed = 0
                    last_snapshot_at = snapshot_at

    if batch_completed:
        _write_ledgers(
            records=_ordered_records(existing_records.values()),
            interesting_path=interesting_path,
            blocked_path=blocked_path,
            filter_blockers_path=filter_blockers_path,
        )
        last_snapshot_at = now()
        snapshot = _snapshot(
            output_dir,
            spec=spec,
            state=state,
            records=existing_records,
            sequence=state.snapshot_count + 1,
            created_at=last_snapshot_at,
        )
        snapshot_paths.append(snapshot)
        state = state.with_snapshot(path=snapshot, updated_at_utc=iso_utc(now()))
        write_run_state(state_path, state)

    status_scope = "real discovery" if _real_discovery_requested(spec, templates) else "placeholder discovery"
    if len(state.completed_trial_ids) >= len(templates):
        state = state.with_status("completed", updated_at_utc=iso_utc(now()), message=f"{status_scope} run completed")
        write_run_state(state_path, state)
    else:
        state = state.with_status("in_progress", updated_at_utc=iso_utc(now()), message=f"{status_scope} run paused")
        write_run_state(state_path, state)

    _write_ledgers(
        records=_ordered_records(existing_records.values()),
        interesting_path=interesting_path,
        blocked_path=blocked_path,
        filter_blockers_path=filter_blockers_path,
    )
    final_snapshot = _snapshot(
        output_dir,
        spec=spec,
        state=state,
        records=existing_records,
        sequence=state.snapshot_count + 1,
        created_at=now(),
    )
    snapshot_paths.append(final_snapshot)
    state = state.with_snapshot(path=final_snapshot, updated_at_utc=iso_utc(now()))
    write_run_state(state_path, state)

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
        counts=_record_counts(existing_records),
        feature_column_set_evidence=feature_column_set_evidence,
        data_evidence=real_context.data_evidence if real_context is not None else {},
        runtime_seconds=time.perf_counter() - started,
    )
    atomic_write_json(manifest_path, manifest)

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
class _LabelSplitCacheEntry:
    labeled: pd.DataFrame
    splits: tuple[Any, ...]


@dataclass(frozen=True, slots=True)
class _RealDiscoveryContext:
    dataset: pd.DataFrame | None
    feature_sets: Mapping[str, DiscoveryFeatureColumnSet]
    frames_by_column_set: Mapping[str, pd.DataFrame]
    unavailable_feature_sets: Mapping[str, str]
    label_split_cache: dict[str, _LabelSplitCacheEntry]
    label_split_cache_lock: threading.Lock
    hmm_cache: dict[str, _HmmCacheEntry]
    hmm_cache_lock: threading.Lock
    interval_ms: int
    data_evidence: Mapping[str, Any]
    unavailable_reason: str = ""


def _real_discovery_requested(spec: DiscoveryRunSpec, templates: tuple[DiscoveryTrialTemplate, ...]) -> bool:
    return any(_real_trial_template(template) for template in templates)


def _real_trial_template(template: DiscoveryTrialTemplate) -> bool:
    return str(dict(template.payload).get("trial_kind") or "") == "hmm_knn_entry_discovery"


def _prepare_real_discovery_context(spec: DiscoveryRunSpec, *, output_dir: Path) -> _RealDiscoveryContext:
    if not spec.data.dataset_manifest_paths and spec.data.dataset_path is None:
        return _RealDiscoveryContext(
            dataset=None,
            feature_sets={},
            frames_by_column_set={},
            unavailable_feature_sets={},
            label_split_cache={},
            label_split_cache_lock=threading.Lock(),
            hmm_cache={},
            hmm_cache_lock=threading.Lock(),
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
            label_split_cache={},
            label_split_cache_lock=threading.Lock(),
            hmm_cache={},
            hmm_cache_lock=threading.Lock(),
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
    feature_root = output_dir / "feature_matrices"
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
    return _RealDiscoveryContext(
        dataset=dataset,
        feature_sets=selected,
        frames_by_column_set=frames_by_column_set,
        unavailable_feature_sets=unavailable_feature_sets,
        label_split_cache={},
        label_split_cache_lock=threading.Lock(),
        hmm_cache={},
        hmm_cache_lock=threading.Lock(),
        interval_ms=interval_ms,
        data_evidence={**data_evidence, "feature_materialization_errors": materialization_errors},
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
    trial_dir.mkdir(parents=True, exist_ok=True)
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
                "trial_kind": "hmm_knn_entry_discovery",
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


def _hmm_cache_key(
    *,
    column_set: DiscoveryFeatureColumnSet,
    hmm_spec: HmmMaterializationSpec,
    min_splits: int,
    purge_embargo_bars: int,
) -> str:
    return sha256(
        json.dumps(
            {
                "feature_column_set_id": column_set.feature_column_set_id,
                "registered_feature_set_id": column_set.registered_feature_set_id,
                "hmm_spec": hmm_spec.to_payload(),
                "min_splits": int(min_splits),
                "purge_embargo_bars": int(purge_embargo_bars),
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


def _persist_trial_artifacts(policy: str, *, ledger_kind: str) -> bool:
    if policy == "interesting_only":
        return ledger_kind == "interesting"
    return True


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
    available_feature_columns = tuple(column for column in column_set.columns if column in labeled.columns)
    if not available_feature_columns:
        return _blocked_real_trial_record(
            spec,
            template,
            trial_index=trial_index,
            started_at=started_at,
            completed_at=completed_at,
            blocker_code="feature_column_set_columns_missing",
            payload={"feature_column_set_id": column_set.feature_column_set_id, "label_horizon": label_horizon},
        )
    hmm_columns = _hmm_columns_for_trial(available_feature_columns)
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
        hmm_feature_pack_id=f"discovery_hmm_{column_set.feature_column_set_id}",
    )
    hmm, hmm_cache_hit = _materialize_hmm_with_cache(
        labeled,
        splits=splits,
        spec=hmm_spec,
        context=context,
        cache_key=_hmm_cache_key(
            column_set=column_set,
            hmm_spec=hmm_spec,
            min_splits=spec.search.min_splits,
            purge_embargo_bars=spec.search.purge_embargo_bars,
        ),
    )
    k_value = int(trial_payload.get("k", 8))
    min_neighbor_count = max(1, min(k_value, int(trial_payload.get("min_neighbor_count", min(4, k_value)))))
    knn_spec = KnnStudySpec(
        feature_columns=available_feature_columns,
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
        same_regime_only=bool(trial_payload.get("same_regime_only", True)),
        feature_column_set_id=column_set.feature_column_set_id,
        label_horizon=label_horizon,
    )
    knn = materialize_regime_local_knn_predictions(hmm.frame, splits=splits, spec=knn_spec)
    metrics = _knn_trial_metrics(knn.frame, search=spec.search)
    ledger_kind = "interesting" if metrics["passed"] else "blocked"
    blocker_code = "" if metrics["passed"] else str(metrics["primary_blocker"])
    persist_artifacts = _persist_trial_artifacts(spec.execution.persist_trial_artifacts, ledger_kind=ledger_kind)
    hmm_artifact_payload: dict[str, Any] = {"hmm_artifact_persisted": False}
    knn_artifact_payload: dict[str, Any] = {"knn_artifact_persisted": False}
    if persist_artifacts:
        hmm_artifacts = write_hmm_materialization_artifacts(trial_dir / "hmm", hmm)
        knn_artifacts = write_knn_study_artifacts(trial_dir / "knn", knn)
        hmm_artifact_payload = {
            "hmm_artifact_persisted": True,
            "hmm_manifest_path": str(hmm_artifacts.manifest_path),
            "hmm_regime_posteriors_path": str(hmm_artifacts.regime_posteriors_path),
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
        "feature_column_set_id": column_set.feature_column_set_id,
        "registered_feature_set_id": column_set.registered_feature_set_id,
        "hmm_state_count": int(hmm_spec.n_states),
        "hmm_posterior_threshold": float(hmm_spec.posterior_threshold),
        "hmm_entropy_threshold": float(hmm_spec.entropy_threshold),
        "label_horizon": label_horizon,
        "label_split_cache_hit": bool(label_split_cache_hit),
        "hmm_cache_hit": bool(hmm_cache_hit),
        "distance_metric": knn_spec.distance_metric,
        "k": int(knn_spec.k),
        "min_neighbor_count": int(knn_spec.min_neighbor_count),
        "trade_count": int(metrics["trade_count"]),
        "signal_rate": float(metrics["signal_rate"]),
        "realized_expectancy": float(metrics["realized_expectancy"]),
        "accepted_prediction_count": int(metrics["accepted_prediction_count"]),
        "evaluated_prediction_count": int(metrics["evaluated_prediction_count"]),
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
    return DiscoveryTrialRecord(
        run_id=spec.run_id,
        trial_id=template.trial_id,
        attempt_id="attempt-001",
        trial_index=trial_index,
        candidate_id=template.candidate_id,
        candidate_family=template.candidate_family or "hmm_knn_entry_discovery",
        ledger_kind="blocked",
        score=0.0,
        blocker_code=blocker_code,
        status="completed",
        started_at_utc=started_at,
        completed_at_utc=completed_at,
        payload={
            **trial_payload,
            "placeholder_trial": False,
            "trade_count": 0,
            "signal_rate": 0.0,
            "realized_expectancy": 0.0,
            "accepted_prediction_count": 0,
            "evaluated_prediction_count": 0,
            "final_score": 0.0,
            "hmm_artifact_persisted": False,
            "knn_artifact_persisted": False,
            "strategy_accounting_persisted": False,
        },
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
    label_return = (future_close / close) - 1.0
    result["label_return"] = label_return
    result["label_up"] = (label_return > 0.0).astype(float)
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


def _feature_set_preflight_reason(frame: pd.DataFrame, column_set: DiscoveryFeatureColumnSet) -> str:
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
    if len(usable_columns) < 2:
        return "feature_set_preflight_insufficient_finite_variant_columns"
    hmm_columns = _hmm_columns_for_trial(tuple(usable_columns))
    if len(hmm_columns) < 2:
        return "feature_set_preflight_insufficient_hmm_columns"
    return ""


def _knn_trial_metrics(frame: pd.DataFrame, *, search: Any) -> dict[str, Any]:
    evaluated = frame.loc[frame["knn_skip_reason"].astype(str).ne("not_evaluated")].copy()
    accepted = evaluated.loc[evaluated["accepted_by_knn"].map(_truthy)].copy()
    returns = pd.to_numeric(accepted.get("label_return", pd.Series(dtype=float)), errors="coerce").dropna()
    trade_count = int(len(returns))
    evaluated_count = int(len(evaluated))
    accepted_count = int(len(accepted))
    signal_rate = float(trade_count / max(1, len(frame)))
    realized_expectancy = float(returns.mean()) if trade_count else 0.0
    gross_return = float(returns.sum()) if trade_count else 0.0
    avg_neighbor_quality = _safe_mean(accepted.get("neighbor_distance_quality")) if not accepted.empty else 0.0
    avg_vote_margin = _safe_mean(accepted.get("knn_vote_margin")) if not accepted.empty else 0.0
    final_score = realized_expectancy + (0.05 * math.log1p(trade_count)) + (0.01 * avg_neighbor_quality) + (0.01 * avg_vote_margin)
    reasons: list[str] = []
    if trade_count < int(search.min_trade_count):
        reasons.append("trade_count_below_discovery_floor")
    if signal_rate < float(search.min_signal_rate):
        reasons.append("signal_rate_below_discovery_floor")
    if signal_rate > float(search.max_signal_rate):
        reasons.append("signal_rate_above_discovery_ceiling")
    if realized_expectancy < float(search.min_realized_expectancy):
        reasons.append("realized_expectancy_below_discovery_floor")
    if accepted_count == 0:
        reasons.append("no_accepted_knn_predictions")
    return {
        "trade_count": trade_count,
        "accepted_prediction_count": accepted_count,
        "evaluated_prediction_count": evaluated_count,
        "signal_rate": signal_rate,
        "realized_expectancy": realized_expectancy,
        "gross_realized_return": gross_return,
        "avg_neighbor_distance_quality": avg_neighbor_quality,
        "avg_vote_margin": avg_vote_margin,
        "final_score": float(final_score),
        "passed": not reasons,
        "primary_blocker": reasons[0] if reasons else "",
        "blocker_reasons": reasons,
    }


def _holding_window_from_label_horizon(label_horizon: str) -> str:
    normalized = str(label_horizon).strip().lower()
    if normalized in {"4h", "12h", "24h", "72h"}:
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


def _safe_mean(value: Any) -> float:
    series = pd.to_numeric(value, errors="coerce").dropna()
    return float(series.mean()) if not series.empty else 0.0


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


def _record_frame(records: list[DiscoveryTrialRecord]) -> pd.DataFrame:
    rows = []
    for record in records:
        payload = record.to_payload()
        trial_payload = payload.get("payload") if isinstance(payload.get("payload"), Mapping) else {}
        rows.append({column: payload.get(column, trial_payload.get(column, "")) for column in LEDGER_COLUMNS})
    return pd.DataFrame(rows, columns=list(LEDGER_COLUMNS))


def _ordered_records(records: Any) -> list[DiscoveryTrialRecord]:
    return sorted(records, key=lambda record: (int(record.trial_index), str(record.trial_id)))


def _snapshot(
    output_dir: Path,
    *,
    spec: DiscoveryRunSpec,
    state: DiscoveryRunState,
    records: Mapping[str, DiscoveryTrialRecord],
    sequence: int,
    created_at: datetime,
) -> Path:
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
            "completed_trial_count": len(records),
            "counts": _record_counts(records),
            "last_snapshot_path": state.last_snapshot_path,
        },
    )


def _record_counts(records: Mapping[str, DiscoveryTrialRecord]) -> dict[str, int]:
    values = list(records.values())
    return {
        "completed_trials": len(values),
        "interesting_candidates": sum(1 for record in values if record.ledger_kind == "interesting"),
        "blocked_candidates": sum(1 for record in values if record.ledger_kind == "blocked"),
        "filter_blockers": sum(1 for record in values if record.ledger_kind == "filter_blocked"),
    }


def _snapshot_interval_due(previous: datetime, current: datetime, interval_minutes: int) -> bool:
    previous_utc = previous if previous.tzinfo is not None else previous.replace(tzinfo=current.tzinfo)
    current_utc = current if current.tzinfo is not None else current.replace(tzinfo=previous_utc.tzinfo)
    return current_utc - previous_utc >= timedelta(minutes=int(interval_minutes))
