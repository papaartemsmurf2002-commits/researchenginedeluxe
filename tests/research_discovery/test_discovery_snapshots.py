from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from tradingbotsuite.research_discovery.snapshots import write_snapshot


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
