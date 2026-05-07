from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4


DISCOVERY_SNAPSHOT_VERSION = "discovery-run-snapshot-v1"


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
    tmp_path.replace(path)
    return path


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
