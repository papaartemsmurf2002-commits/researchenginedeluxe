from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Mapping

import pandas as pd

from tradingbotsuite.config import AppConfig
from tradingbotsuite.research_discovery.feature_sets import (
    load_feature_column_set_manifest,
    validate_feature_column_set_manifest,
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
    "record_sha256",
)


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

    for index, template in enumerate(templates, start=1):
        if template.trial_id in completed_ids:
            continue
        if stop_after_trials is not None and executed_this_call >= stop_after_trials:
            break
        record = _placeholder_trial_record(spec, template, trial_index=index, clock=now)
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

    if len(state.completed_trial_ids) >= len(templates):
        state = state.with_status("completed", updated_at_utc=iso_utc(now()), message="placeholder discovery run completed")
        write_run_state(state_path, state)
    else:
        state = state.with_status("in_progress", updated_at_utc=iso_utc(now()), message="placeholder discovery run paused")
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
        rows.append({column: payload.get(column, "") for column in LEDGER_COLUMNS})
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
