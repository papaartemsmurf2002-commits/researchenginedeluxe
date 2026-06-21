# V2-AUDIT-ID: V2-AUD-WORKER-001
# V2-CONTRACTS: docs/contracts/worker_job_contract.md
# V2-BOUNDARY: research_only, sqlite_wal_job_store, no_live_imports
# V2-OWNER: v2_workers
"""SQLite WAL durable job store for v2 workers."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from tradingbotsuite.v2.archive.hashing import canonical_json_hash
from tradingbotsuite.v2.config.time import ensure_utc, utc_isoformat, utc_now
from tradingbotsuite.v2.workers.models import (
    TERMINAL_STATUSES,
    WorkerGapRecord,
    WorkerHeartbeat,
    WorkerJobKind,
    WorkerJobRecord,
    WorkerJobStatus,
    WorkerTransition,
)


class WorkerJobStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS worker_jobs (
                    job_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    input_spec_hash TEXT NOT NULL,
                    input_spec_json TEXT NOT NULL,
                    record_json TEXT NOT NULL,
                    queued_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_worker_jobs_kind_status ON worker_jobs(kind, status, queued_at)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS worker_transitions (
                    transition_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    transition_json TEXT NOT NULL,
                    transitioned_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_worker_transitions_job ON worker_transitions(job_id, transitioned_at)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS worker_heartbeats (
                    heartbeat_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    heartbeat_json TEXT NOT NULL,
                    heartbeat_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_worker_heartbeats_job ON worker_heartbeats(job_id, heartbeat_at)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS worker_gap_records (
                    gap_record_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    gap_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_worker_gap_records_job ON worker_gap_records(job_id, created_at)"
            )

    def enqueue(
        self,
        *,
        kind: WorkerJobKind | str,
        input_spec: Mapping[str, Any],
        job_id: str | None = None,
        max_attempts: int = 3,
        reason: str = "job_enqueued",
    ) -> WorkerJobRecord:
        self.initialize()
        job_kind = WorkerJobKind(kind)
        spec = _jsonable(dict(input_spec))
        spec_hash = canonical_json_hash(spec)
        materialized_job_id = job_id or f"JOB-{canonical_json_hash({'kind': job_kind.value, 'spec': spec})[:24]}"
        record = WorkerJobRecord(
            job_id=materialized_job_id,
            kind=job_kind,
            input_spec_hash=spec_hash,
            input_spec=spec,
            max_attempts=max_attempts,
        )
        with self._connect() as connection:
            if self._load_job(connection, materialized_job_id) is not None:
                raise ValueError(f"job already exists: {materialized_job_id}")
            self._upsert_job(connection, record)
            self._insert_transition(
                connection,
                job_id=record.job_id,
                from_status=None,
                to_status=record.status,
                worker_id=None,
                reason=reason,
            )
        return record

    def load_job(self, job_id: str) -> WorkerJobRecord | None:
        self.initialize()
        with self._connect() as connection:
            return self._load_job(connection, job_id)

    def list_jobs(
        self,
        *,
        kind: WorkerJobKind | str | None = None,
        status: WorkerJobStatus | str | None = None,
    ) -> list[WorkerJobRecord]:
        self.initialize()
        query = "SELECT record_json FROM worker_jobs"
        clauses: list[str] = []
        values: list[str] = []
        if kind is not None:
            clauses.append("kind = ?")
            values.append(WorkerJobKind(kind).value)
        if status is not None:
            clauses.append("status = ?")
            values.append(WorkerJobStatus(status).value)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY queued_at, job_id"
        with self._connect() as connection:
            return [
                WorkerJobRecord.model_validate_json(row["record_json"])
                for row in connection.execute(query, values).fetchall()
            ]

    def claim_next(
        self,
        *,
        kind: WorkerJobKind | str,
        worker_id: str,
        reason: str = "job_claimed",
    ) -> WorkerJobRecord | None:
        self.initialize()
        job_kind = WorkerJobKind(kind)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT record_json FROM worker_jobs
                WHERE kind = ? AND status = ?
                ORDER BY queued_at, job_id
                LIMIT 1
                """,
                (job_kind.value, WorkerJobStatus.QUEUED.value),
            ).fetchone()
            if row is None:
                return None
            current = WorkerJobRecord.model_validate_json(row["record_json"])
            now = utc_now()
            claimed = current.model_copy(
                update={
                    "status": WorkerJobStatus.CLAIMED,
                    "attempts": current.attempts + 1,
                    "claimed_at": now,
                    "lock_owner": worker_id,
                    "terminal_state": False,
                }
            )
            self._upsert_job(connection, claimed)
            self._insert_transition(
                connection,
                job_id=claimed.job_id,
                from_status=current.status,
                to_status=claimed.status,
                worker_id=worker_id,
                reason=reason,
            )
            return claimed

    def start_job(self, job_id: str, *, worker_id: str, reason: str = "job_started") -> WorkerJobRecord:
        return self._transition_job(
            job_id,
            to_status=WorkerJobStatus.RUNNING,
            worker_id=worker_id,
            reason=reason,
            update={"started_at": utc_now(), "heartbeat_at": utc_now(), "lock_owner": worker_id},
            allowed_from={WorkerJobStatus.CLAIMED},
        )

    def heartbeat(
        self,
        job_id: str,
        *,
        worker_id: str,
        details: Mapping[str, str] | None = None,
    ) -> WorkerHeartbeat:
        self.initialize()
        with self._connect() as connection:
            current = self._require_job(connection, job_id)
            if current.status not in {WorkerJobStatus.CLAIMED, WorkerJobStatus.RUNNING}:
                raise ValueError(f"cannot heartbeat job in status {current.status.value}")
            now = utc_now()
            heartbeat = WorkerHeartbeat(
                heartbeat_id=canonical_json_hash(
                    {
                        "job_id": job_id,
                        "worker_id": worker_id,
                        "status": current.status.value,
                        "heartbeat_at": utc_isoformat(now),
                        "details": dict(details or {}),
                    }
                ),
                job_id=job_id,
                worker_id=worker_id,
                status=current.status,
                heartbeat_at=now,
                details=dict(details or {}),
            )
            updated = current.model_copy(update={"heartbeat_at": now, "lock_owner": worker_id})
            self._upsert_job(connection, updated)
            connection.execute(
                """
                INSERT OR REPLACE INTO worker_heartbeats
                (heartbeat_id, job_id, heartbeat_json, heartbeat_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    heartbeat.heartbeat_id,
                    heartbeat.job_id,
                    heartbeat.model_dump_json(),
                    utc_isoformat(heartbeat.heartbeat_at),
                ),
            )
            return heartbeat

    def succeed_job(
        self,
        job_id: str,
        *,
        worker_id: str,
        output_refs: tuple[str, ...] = (),
        archive_manifest_refs: tuple[str, ...] = (),
        gap_record_ids: tuple[str, ...] = (),
        reason: str = "job_succeeded",
    ) -> WorkerJobRecord:
        current = self.load_job(job_id)
        if current is None:
            raise KeyError(job_id)
        return self._transition_job(
            job_id,
            to_status=WorkerJobStatus.SUCCEEDED,
            worker_id=worker_id,
            reason=reason,
            update={
                "finished_at": utc_now(),
                "terminal_state": True,
                "output_refs": tuple(dict.fromkeys((*current.output_refs, *output_refs))),
                "archive_manifest_refs": tuple(
                    dict.fromkeys((*current.archive_manifest_refs, *archive_manifest_refs))
                ),
                "gap_record_ids": tuple(dict.fromkeys((*current.gap_record_ids, *gap_record_ids))),
            },
            allowed_from={WorkerJobStatus.RUNNING, WorkerJobStatus.CLAIMED},
        )

    def fail_job(
        self,
        job_id: str,
        *,
        worker_id: str,
        reason: str,
        retryable: bool = True,
        output_refs: tuple[str, ...] = (),
        archive_manifest_refs: tuple[str, ...] = (),
        gap_record_ids: tuple[str, ...] = (),
    ) -> WorkerJobRecord:
        self.initialize()
        with self._connect() as connection:
            current = self._require_job(connection, job_id)
            if current.status in TERMINAL_STATUSES:
                raise ValueError(f"cannot fail terminal job {job_id}")
            now = utc_now()
            failed = current.model_copy(
                update={
                    "status": WorkerJobStatus.FAILED,
                    "finished_at": now,
                    "failure_reason": reason,
                    "terminal_state": not (retryable and current.attempts < current.max_attempts),
                    "output_refs": tuple(dict.fromkeys((*current.output_refs, *output_refs))),
                    "archive_manifest_refs": tuple(
                        dict.fromkeys((*current.archive_manifest_refs, *archive_manifest_refs))
                    ),
                    "gap_record_ids": tuple(dict.fromkeys((*current.gap_record_ids, *gap_record_ids))),
                }
            )
            self._upsert_job(connection, failed)
            self._insert_transition(
                connection,
                job_id=job_id,
                from_status=current.status,
                to_status=WorkerJobStatus.FAILED,
                worker_id=worker_id,
                reason=reason,
            )
            if not retryable or current.attempts >= current.max_attempts:
                return failed
            retrying = failed.model_copy(
                update={
                    "status": WorkerJobStatus.RETRYING,
                    "terminal_state": False,
                    "retry_after": now,
                }
            )
            self._upsert_job(connection, retrying)
            self._insert_transition(
                connection,
                job_id=job_id,
                from_status=WorkerJobStatus.FAILED,
                to_status=WorkerJobStatus.RETRYING,
                worker_id=worker_id,
                reason="retry_scheduled",
            )
            queued = retrying.model_copy(
                update={
                    "status": WorkerJobStatus.QUEUED,
                    "lock_owner": None,
                    "claimed_at": None,
                    "started_at": None,
                    "heartbeat_at": None,
                    "terminal_state": False,
                }
            )
            self._upsert_job(connection, queued)
            self._insert_transition(
                connection,
                job_id=job_id,
                from_status=WorkerJobStatus.RETRYING,
                to_status=WorkerJobStatus.QUEUED,
                worker_id=worker_id,
                reason="retry_requeued",
            )
            return queued

    def retry_job(self, job_id: str, *, worker_id: str, reason: str = "manual_retry") -> WorkerJobRecord:
        return self._transition_job(
            job_id,
            to_status=WorkerJobStatus.QUEUED,
            worker_id=worker_id,
            reason=reason,
            update={
                "terminal_state": False,
                "failure_reason": None,
                "finished_at": None,
                "lock_owner": None,
                "claimed_at": None,
                "started_at": None,
                "heartbeat_at": None,
            },
            allowed_from={WorkerJobStatus.FAILED, WorkerJobStatus.STALE, WorkerJobStatus.CANCELLED},
        )

    def cancel_job(self, job_id: str, *, worker_id: str, reason: str = "job_cancelled") -> WorkerJobRecord:
        return self._transition_job(
            job_id,
            to_status=WorkerJobStatus.CANCELLED,
            worker_id=worker_id,
            reason=reason,
            update={"finished_at": utc_now(), "terminal_state": True},
            allowed_from={WorkerJobStatus.QUEUED, WorkerJobStatus.CLAIMED, WorkerJobStatus.RUNNING},
        )

    def mark_stale_jobs(
        self,
        *,
        stale_after: timedelta,
        worker_id: str = "stale-monitor",
        reason: str = "heartbeat_stale",
    ) -> list[WorkerJobRecord]:
        self.initialize()
        cutoff = utc_now() - stale_after
        stale_records: list[WorkerJobRecord] = []
        for job in self.list_jobs():
            if job.status != WorkerJobStatus.RUNNING:
                continue
            heartbeat_at = job.heartbeat_at or job.started_at or job.claimed_at
            if heartbeat_at is None or ensure_utc(heartbeat_at) > cutoff:
                continue
            stale_records.append(
                self._transition_job(
                    job.job_id,
                    to_status=WorkerJobStatus.STALE,
                    worker_id=worker_id,
                    reason=reason,
                    update={
                        "finished_at": utc_now(),
                        "failure_reason": reason,
                        "terminal_state": False,
                    },
                    allowed_from={WorkerJobStatus.RUNNING},
                )
            )
        return stale_records

    def record_gap(
        self,
        *,
        job_id: str,
        kind: WorkerJobKind | str,
        reason: str,
        worker_id: str | None = None,
        start_ts: datetime | None = None,
        end_ts: datetime | None = None,
        backoff_seconds: int = 0,
        reconnect_attempts: int = 0,
    ) -> WorkerGapRecord:
        self.initialize()
        gap = WorkerGapRecord(
            gap_record_id=canonical_json_hash(
                {
                    "job_id": job_id,
                    "kind": WorkerJobKind(kind).value,
                    "reason": reason,
                    "worker_id": worker_id,
                    "start_ts": utc_isoformat(start_ts) if start_ts else None,
                    "end_ts": utc_isoformat(end_ts) if end_ts else None,
                    "backoff_seconds": backoff_seconds,
                    "reconnect_attempts": reconnect_attempts,
                    "created_at": utc_isoformat(utc_now()),
                }
            ),
            job_id=job_id,
            worker_id=worker_id,
            kind=WorkerJobKind(kind),
            reason=reason,
            start_ts=start_ts,
            end_ts=end_ts,
            backoff_seconds=backoff_seconds,
            reconnect_attempts=reconnect_attempts,
        )
        with self._connect() as connection:
            current = self._require_job(connection, job_id)
            updated = current.model_copy(
                update={
                    "gap_record_ids": tuple(dict.fromkeys((*current.gap_record_ids, gap.gap_record_id)))
                }
            )
            self._upsert_job(connection, updated)
            connection.execute(
                """
                INSERT OR REPLACE INTO worker_gap_records
                (gap_record_id, job_id, gap_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (gap.gap_record_id, gap.job_id, gap.model_dump_json(), utc_isoformat(gap.created_at)),
            )
        return gap

    def list_transitions(self, job_id: str | None = None) -> list[WorkerTransition]:
        self.initialize()
        query = "SELECT transition_json FROM worker_transitions"
        values: list[str] = []
        if job_id is not None:
            query += " WHERE job_id = ?"
            values.append(job_id)
        query += " ORDER BY transitioned_at, rowid"
        with self._connect() as connection:
            return [
                WorkerTransition.model_validate_json(row["transition_json"])
                for row in connection.execute(query, values).fetchall()
            ]

    def list_heartbeats(self, job_id: str | None = None) -> list[WorkerHeartbeat]:
        self.initialize()
        query = "SELECT heartbeat_json FROM worker_heartbeats"
        values: list[str] = []
        if job_id is not None:
            query += " WHERE job_id = ?"
            values.append(job_id)
        query += " ORDER BY heartbeat_at, heartbeat_id"
        with self._connect() as connection:
            return [
                WorkerHeartbeat.model_validate_json(row["heartbeat_json"])
                for row in connection.execute(query, values).fetchall()
            ]

    def list_gap_records(self, job_id: str | None = None) -> list[WorkerGapRecord]:
        self.initialize()
        query = "SELECT gap_json FROM worker_gap_records"
        values: list[str] = []
        if job_id is not None:
            query += " WHERE job_id = ?"
            values.append(job_id)
        query += " ORDER BY created_at, gap_record_id"
        with self._connect() as connection:
            return [
                WorkerGapRecord.model_validate_json(row["gap_json"])
                for row in connection.execute(query, values).fetchall()
            ]

    def _transition_job(
        self,
        job_id: str,
        *,
        to_status: WorkerJobStatus,
        worker_id: str | None,
        reason: str,
        update: Mapping[str, Any],
        allowed_from: set[WorkerJobStatus],
    ) -> WorkerJobRecord:
        self.initialize()
        with self._connect() as connection:
            current = self._require_job(connection, job_id)
            if current.status not in allowed_from:
                allowed = ",".join(sorted(status.value for status in allowed_from))
                raise ValueError(f"cannot transition {job_id} from {current.status.value}; allowed: {allowed}")
            updated = current.model_copy(update={"status": to_status, **dict(update)})
            self._upsert_job(connection, updated)
            self._insert_transition(
                connection,
                job_id=job_id,
                from_status=current.status,
                to_status=to_status,
                worker_id=worker_id,
                reason=reason,
            )
            return updated

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def _load_job(self, connection: sqlite3.Connection, job_id: str) -> WorkerJobRecord | None:
        row = connection.execute(
            "SELECT record_json FROM worker_jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        if row is None:
            return None
        return WorkerJobRecord.model_validate_json(row["record_json"])

    def _require_job(self, connection: sqlite3.Connection, job_id: str) -> WorkerJobRecord:
        record = self._load_job(connection, job_id)
        if record is None:
            raise KeyError(job_id)
        return record

    def _upsert_job(self, connection: sqlite3.Connection, record: WorkerJobRecord) -> None:
        connection.execute(
            """
            INSERT OR REPLACE INTO worker_jobs
            (job_id, kind, status, input_spec_hash, input_spec_json, record_json, queued_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.job_id,
                record.kind.value,
                record.status.value,
                record.input_spec_hash,
                json.dumps(record.input_spec, sort_keys=True, separators=(",", ":")),
                record.model_dump_json(),
                utc_isoformat(record.queued_at),
                utc_isoformat(utc_now()),
            ),
        )

    def _insert_transition(
        self,
        connection: sqlite3.Connection,
        *,
        job_id: str,
        from_status: WorkerJobStatus | None,
        to_status: WorkerJobStatus,
        worker_id: str | None,
        reason: str,
    ) -> WorkerTransition:
        now = utc_now()
        transition = WorkerTransition(
            transition_id=canonical_json_hash(
                {
                    "job_id": job_id,
                    "from_status": from_status.value if from_status else None,
                    "to_status": to_status.value,
                    "worker_id": worker_id,
                    "reason": reason,
                    "transitioned_at": utc_isoformat(now),
                }
            ),
            job_id=job_id,
            from_status=from_status,
            to_status=to_status,
            worker_id=worker_id,
            reason=reason,
            transitioned_at=now,
        )
        connection.execute(
            """
            INSERT OR REPLACE INTO worker_transitions
            (transition_id, job_id, transition_json, transitioned_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                transition.transition_id,
                transition.job_id,
                transition.model_dump_json(),
                utc_isoformat(transition.transitioned_at),
            ),
        )
        return transition


def _jsonable(value: dict[str, Any]) -> dict[str, Any]:
    model = _JsonContainer(payload=value)
    return model.model_dump(mode="json")["payload"]


class _JsonContainer(BaseModel):
    payload: dict[str, Any]
