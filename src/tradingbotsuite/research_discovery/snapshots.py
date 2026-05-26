from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4


DISCOVERY_SNAPSHOT_VERSION = "discovery-run-snapshot-v1"
ATOMIC_WRITE_REPLACE_ATTEMPTS_ENV = "TBS_ATOMIC_WRITE_REPLACE_ATTEMPTS"
ATOMIC_WRITE_REPLACE_BACKOFF_SECONDS_ENV = "TBS_ATOMIC_WRITE_REPLACE_BACKOFF_SECONDS"
DEFAULT_ATOMIC_WRITE_REPLACE_ATTEMPTS = 60
DEFAULT_ATOMIC_WRITE_REPLACE_BACKOFF_SECONDS = 0.05


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_timestamp(value: datetime | None = None) -> str:
    current = value or utc_now()
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def iso_utc(value: datetime | None = None) -> str:
    current = value or utc_now()
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    text = json.dumps(payload, indent=2, sort_keys=True, default=str, allow_nan=False) + "\n"
    tmp_path.write_text(text, encoding="utf-8")
    _replace_path_with_retry(tmp_path, path)
    return path


def _replace_path_with_retry(tmp_path: Path, path: Path) -> None:
    attempts = _atomic_write_replace_attempts()
    backoff = _atomic_write_replace_backoff_seconds()
    for attempt in range(1, attempts + 1):
        try:
            _replace_path_once(tmp_path, path)
            return
        except PermissionError:
            if attempt >= attempts:
                raise
            time.sleep(min(1.0, backoff * attempt))


def _replace_path_once(tmp_path: Path, path: Path) -> None:
    tmp_path.replace(path)


def _atomic_write_replace_attempts() -> int:
    raw = os.getenv(ATOMIC_WRITE_REPLACE_ATTEMPTS_ENV)
    if raw is not None and str(raw).strip():
        try:
            return max(1, int(str(raw).strip()))
        except ValueError:
            return DEFAULT_ATOMIC_WRITE_REPLACE_ATTEMPTS
    return DEFAULT_ATOMIC_WRITE_REPLACE_ATTEMPTS


def _atomic_write_replace_backoff_seconds() -> float:
    raw = os.getenv(ATOMIC_WRITE_REPLACE_BACKOFF_SECONDS_ENV)
    if raw is not None and str(raw).strip():
        try:
            return max(0.0, float(str(raw).strip()))
        except ValueError:
            return DEFAULT_ATOMIC_WRITE_REPLACE_BACKOFF_SECONDS
    return DEFAULT_ATOMIC_WRITE_REPLACE_BACKOFF_SECONDS


def write_snapshot(
    output_dir: Path,
    *,
    run_id: str,
    sequence: int,
    summary: Mapping[str, Any],
    created_at: datetime | None = None,
) -> Path:
    timestamp = utc_timestamp(created_at)
    path = output_dir / "snapshots" / f"{timestamp}_{sequence:06d}_snapshot.json"
    payload = {
        "snapshot_version": DISCOVERY_SNAPSHOT_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "run_id": run_id,
        "snapshot_sequence": sequence,
        "created_at_utc": iso_utc(created_at),
        "summary": dict(summary),
    }
    return atomic_write_json(path, payload)
