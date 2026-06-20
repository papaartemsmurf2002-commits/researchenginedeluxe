from __future__ import annotations

import json
from pathlib import Path

import pytest

from tradingbotsuite.research_discovery.state import (
    DiscoveryRunState,
    DiscoveryTrialRecord,
    read_trial_record,
    write_trial_record,
)


def _record(*, score: float = 1.0) -> DiscoveryTrialRecord:
    return DiscoveryTrialRecord(
        run_id="state-run",
        trial_id="trial-000001",
        attempt_id="attempt-001",
        trial_index=1,
        candidate_id="candidate-1",
        candidate_family="placeholder",
        ledger_kind="interesting",
        score=score,
        started_at_utc="2026-05-07T10:00:00Z",
        completed_at_utc="2026-05-07T10:00:00Z",
    )


def _failed_record() -> DiscoveryTrialRecord:
    return DiscoveryTrialRecord(
        run_id="state-run",
        trial_id="trial-000002",
        attempt_id="attempt-001",
        trial_index=2,
        candidate_id="candidate-2",
        candidate_family="placeholder",
        ledger_kind="blocked",
        blocker_code="trial_execution_error",
        score=0.0,
        status="failed",
        error_payload={"error": "boom"},
        started_at_utc="2026-05-07T10:00:00Z",
        completed_at_utc="2026-05-07T10:00:00Z",
    )


def test_completed_trial_record_is_immutable(tmp_path: Path) -> None:
    path = tmp_path / "trials" / "trial-000001.json"
    write_trial_record(path, _record(score=1.0))

    with pytest.raises(ValueError, match="immutable"):
        write_trial_record(path, _record(score=2.0))


def test_trial_record_hash_detects_tampering(tmp_path: Path) -> None:
    path = tmp_path / "trials" / "trial-000001.json"
    write_trial_record(path, _record(score=1.0))
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["score"] = 2.0
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    with pytest.raises(ValueError, match="hash mismatch"):
        read_trial_record(path)


def test_run_state_rejects_changed_completed_trial_hash() -> None:
    state = DiscoveryRunState.new(run_id="state-run", created_at_utc="2026-05-07T10:00:00Z")
    state = state.with_completed_trial(_record(score=1.0), updated_at_utc="2026-05-07T10:01:00Z")

    with pytest.raises(ValueError, match="changed after completion"):
        state.with_completed_trial(_record(score=2.0), updated_at_utc="2026-05-07T10:02:00Z")


def test_run_state_tracks_failed_trial_records_separately() -> None:
    state = DiscoveryRunState.new(run_id="state-run", created_at_utc="2026-05-07T10:00:00Z")
    state = state.with_completed_trial(_failed_record(), updated_at_utc="2026-05-07T10:01:00Z")

    assert state.completed_trial_ids == ("trial-000002",)
    assert state.failed_trial_ids == ("trial-000002",)
