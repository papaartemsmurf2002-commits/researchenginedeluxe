from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from tradingbotsuite.research_discovery import snapshots
from tradingbotsuite.research_discovery.snapshots import atomic_write_json, write_snapshot


def test_snapshot_write_is_atomic_and_readable(tmp_path: Path) -> None:
    path = write_snapshot(
        tmp_path,
        run_id="snapshot-run",
        sequence=1,
        summary={"completed_trial_count": 1},
        created_at=datetime(2026, 5, 7, 10, 0, tzinfo=timezone.utc),
    )

    payload = json.loads(path.read_text(encoding="utf-8"))

    assert path.name == "20260507T100000Z_000001_snapshot.json"
    assert payload["snapshot_version"] == "discovery-run-snapshot-v1"
    assert payload["research_only"] is True
    assert payload["observe_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["summary"]["completed_trial_count"] == 1
    assert not list(path.parent.glob("*.tmp"))


def test_atomic_write_json_retries_transient_permission_error(
    tmp_path: Path,
    monkeypatch,
) -> None:
    path = tmp_path / "run_state.json"
    path.write_text('{"old": true}\n', encoding="utf-8")
    calls = {"count": 0}
    original_replace = snapshots._replace_path_once

    def flaky_replace(tmp_path_arg: Path, path_arg: Path) -> None:
        calls["count"] += 1
        if calls["count"] < 3:
            raise PermissionError("simulated transient windows replace contention")
        original_replace(tmp_path_arg, path_arg)

    monkeypatch.setenv(snapshots.ATOMIC_WRITE_REPLACE_ATTEMPTS_ENV, "3")
    monkeypatch.setenv(snapshots.ATOMIC_WRITE_REPLACE_BACKOFF_SECONDS_ENV, "0")
    monkeypatch.setattr(snapshots, "_replace_path_once", flaky_replace)

    atomic_write_json(path, {"new": True})

    assert calls["count"] == 3
    assert json.loads(path.read_text(encoding="utf-8")) == {"new": True}
    assert not list(tmp_path.glob("*.tmp"))
