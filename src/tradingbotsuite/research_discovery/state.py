from __future__ import annotations

import json
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

from tradingbotsuite.research_discovery.snapshots import atomic_write_json


DISCOVERY_RUN_STATE_VERSION = "discovery-run-state-v1"
DISCOVERY_TRIAL_RECORD_VERSION = "discovery-trial-record-v1"
LIVE_ADJACENT_VERSION_FIELDS = frozenset(
    {
        "promotion_candidate_manifest_version",
        "paper_run_manifest_version",
        "shadow_run_archive_manifest_version",
        "testnet_validation_manifest_version",
        "live_run_manifest_version",
    }
)
LIVE_BOUNDARY_FIELDS = (
    "live_signal_input",
    "position_sizing_input",
    "operator_control_input",
    "live_execution_input",
    "runtime_control_input",
    "live_fetch_used",
    "order_placement_used",
    "runtime_mode_changed",
)


@dataclass(frozen=True, slots=True)
class DiscoveryTrialRecord:
    run_id: str
    trial_id: str
    attempt_id: str
    trial_index: int
    candidate_id: str
    candidate_family: str
    ledger_kind: str
    score: float
    blocker_code: str = ""
    filter_blocker_code: str = ""
    status: str = "completed"
    started_at_utc: str = ""
    completed_at_utc: str = ""
    error_payload: Mapping[str, Any] = field(default_factory=dict)
    payload: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "DiscoveryTrialRecord":
        if not isinstance(payload, Mapping):
            raise ValueError("trial record must be a JSON object")
        return cls(
            run_id=str(payload.get("run_id") or ""),
            trial_id=str(payload.get("trial_id") or ""),
            attempt_id=str(payload.get("attempt_id") or "attempt-001"),
            trial_index=int(payload.get("trial_index") or 0),
            candidate_id=str(payload.get("candidate_id") or ""),
            candidate_family=str(payload.get("candidate_family") or ""),
            ledger_kind=str(payload.get("ledger_kind") or ""),
            score=float(payload.get("score") or 0.0),
            blocker_code=str(payload.get("blocker_code") or ""),
            filter_blocker_code=str(payload.get("filter_blocker_code") or ""),
            status=str(payload.get("status") or "completed"),
            started_at_utc=str(payload.get("started_at_utc") or ""),
            completed_at_utc=str(payload.get("completed_at_utc") or ""),
            error_payload=dict(payload.get("error_payload") or {}),
            payload=dict(payload.get("payload") or {}),
        )

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "trial_record_version": DISCOVERY_TRIAL_RECORD_VERSION,
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "run_id": self.run_id,
            "trial_id": self.trial_id,
            "attempt_id": self.attempt_id,
            "trial_index": self.trial_index,
            "candidate_id": self.candidate_id,
            "candidate_family": self.candidate_family,
            "ledger_kind": self.ledger_kind,
            "score": self.score,
            "blocker_code": self.blocker_code,
            "filter_blocker_code": self.filter_blocker_code,
            "status": self.status,
            "started_at_utc": self.started_at_utc,
            "completed_at_utc": self.completed_at_utc,
            "error_payload": dict(self.error_payload),
            "payload": dict(self.payload),
        }
        payload["record_sha256"] = payload_sha256(payload)
        return payload


@dataclass(frozen=True, slots=True)
class DiscoveryRunState:
    run_id: str
    status: str
    started_at_utc: str
    updated_at_utc: str
    completed_trial_ids: tuple[str, ...] = ()
    failed_trial_ids: tuple[str, ...] = ()
    completed_trial_hashes: Mapping[str, str] = field(default_factory=dict)
    snapshot_count: int = 0
    last_snapshot_path: str = ""
    message: str = ""

    @classmethod
    def new(cls, *, run_id: str, created_at_utc: str) -> "DiscoveryRunState":
        return cls(
            run_id=run_id,
            status="in_progress",
            started_at_utc=created_at_utc,
            updated_at_utc=created_at_utc,
        )

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "DiscoveryRunState":
        if not isinstance(payload, Mapping):
            raise ValueError("run state must be a JSON object")
        return cls(
            run_id=str(payload.get("run_id") or ""),
            status=str(payload.get("status") or ""),
            started_at_utc=str(payload.get("started_at_utc") or ""),
            updated_at_utc=str(payload.get("updated_at_utc") or ""),
            completed_trial_ids=tuple(str(item) for item in payload.get("completed_trial_ids") or ()),
            failed_trial_ids=tuple(str(item) for item in payload.get("failed_trial_ids") or ()),
            completed_trial_hashes=dict(payload.get("completed_trial_hashes") or {}),
            snapshot_count=int(payload.get("snapshot_count") or 0),
            last_snapshot_path=str(payload.get("last_snapshot_path") or ""),
            message=str(payload.get("message") or ""),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "run_state_version": DISCOVERY_RUN_STATE_VERSION,
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "run_id": self.run_id,
            "status": self.status,
            "started_at_utc": self.started_at_utc,
            "updated_at_utc": self.updated_at_utc,
            "completed_trial_ids": list(self.completed_trial_ids),
            "failed_trial_ids": list(self.failed_trial_ids),
            "completed_trial_hashes": dict(self.completed_trial_hashes),
            "snapshot_count": self.snapshot_count,
            "last_snapshot_path": self.last_snapshot_path,
            "message": self.message,
        }

    def with_completed_trial(self, record: DiscoveryTrialRecord, *, updated_at_utc: str) -> "DiscoveryRunState":
        payload = record.to_payload()
        record_hash = str(payload["record_sha256"])
        hashes = dict(self.completed_trial_hashes)
        if record.trial_id in hashes and hashes[record.trial_id] != record_hash:
            raise ValueError(f"completed trial record changed after completion: {record.trial_id}")
        hashes[record.trial_id] = record_hash
        completed_ids = tuple(dict.fromkeys((*self.completed_trial_ids, record.trial_id)))
        return DiscoveryRunState(
            run_id=self.run_id,
            status=self.status,
            started_at_utc=self.started_at_utc,
            updated_at_utc=updated_at_utc,
            completed_trial_ids=completed_ids,
            failed_trial_ids=self.failed_trial_ids,
            completed_trial_hashes=hashes,
            snapshot_count=self.snapshot_count,
            last_snapshot_path=self.last_snapshot_path,
            message=self.message,
        )

    def with_snapshot(self, *, path: Path, updated_at_utc: str) -> "DiscoveryRunState":
        return DiscoveryRunState(
            run_id=self.run_id,
            status=self.status,
            started_at_utc=self.started_at_utc,
            updated_at_utc=updated_at_utc,
            completed_trial_ids=self.completed_trial_ids,
            failed_trial_ids=self.failed_trial_ids,
            completed_trial_hashes=self.completed_trial_hashes,
            snapshot_count=self.snapshot_count + 1,
            last_snapshot_path=str(path),
            message=self.message,
        )

    def with_status(self, status: str, *, updated_at_utc: str, message: str = "") -> "DiscoveryRunState":
        return DiscoveryRunState(
            run_id=self.run_id,
            status=status,
            started_at_utc=self.started_at_utc,
            updated_at_utc=updated_at_utc,
            completed_trial_ids=self.completed_trial_ids,
            failed_trial_ids=self.failed_trial_ids,
            completed_trial_hashes=self.completed_trial_hashes,
            snapshot_count=self.snapshot_count,
            last_snapshot_path=self.last_snapshot_path,
            message=message,
        )


def read_run_state(path: Path) -> DiscoveryRunState:
    return DiscoveryRunState.from_payload(json.loads(path.read_text(encoding="utf-8")))


def write_run_state(path: Path, state: DiscoveryRunState) -> Path:
    return atomic_write_json(path, state.to_payload())


def read_trial_record(path: Path) -> DiscoveryTrialRecord:
    payload = json.loads(path.read_text(encoding="utf-8"))
    reasons = _trial_record_boundary_reasons(payload)
    if reasons:
        raise ValueError(f"trial record boundary violation at {path}: {';'.join(reasons)}")
    expected_hash = str(payload.get("record_sha256") or "")
    actual_hash = payload_sha256(payload)
    if expected_hash and expected_hash != actual_hash:
        raise ValueError(f"trial record hash mismatch: {path}")
    return DiscoveryTrialRecord.from_payload(payload)


def write_trial_record(path: Path, record: DiscoveryTrialRecord) -> Path:
    payload = record.to_payload()
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if payload_sha256(existing) != str(payload["record_sha256"]):
            raise ValueError(f"completed trial record is immutable: {path}")
        return path
    return atomic_write_json(path, payload)


def payload_sha256(payload: Mapping[str, Any]) -> str:
    normalized = dict(payload)
    normalized.pop("record_sha256", None)
    encoded = json.dumps(normalized, sort_keys=True, default=str, allow_nan=False).encode("utf-8")
    return sha256(encoded).hexdigest()


def _trial_record_boundary_reasons(payload: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if any(field in payload for field in LIVE_ADJACENT_VERSION_FIELDS):
        reasons.append("live_or_promotion_manifest_version_forbidden")
    if payload.get("research_only") is not True:
        reasons.append("research_only_required")
    if payload.get("observe_only") is not True:
        reasons.append("observe_only_required")
    if payload.get("promotion_ready") is not False:
        reasons.append("promotion_ready_must_be_false")
    for field in LIVE_BOUNDARY_FIELDS:
        if field in payload and payload.get(field) is not False:
            reasons.append(f"{field}_must_be_false")
    return reasons
