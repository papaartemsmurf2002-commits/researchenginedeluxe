from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from tradingbotsuite.config import AppConfig, ResearchConfig
from tradingbotsuite.research_discovery.runner import run_discovery


def _write_spec(
    path: Path,
    *,
    run_id: str,
    max_trials: int = 3,
    trial_batch_size: int = 1,
    snapshot_interval_minutes: int = 30,
) -> Path:
    payload: dict[str, object] = {
        "run_id": run_id,
        "symbol": "BTCUSDT",
        "timeframe": "15m",
        "budget": {
            "max_trials": max_trials,
            "trial_batch_size": trial_batch_size,
            "snapshot_interval_minutes": snapshot_interval_minutes,
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _clock() -> datetime:
    return datetime(2026, 5, 7, 10, 0, tzinfo=timezone.utc)


def _app_config(tmp_path: Path) -> AppConfig:
    return AppConfig(research=ResearchConfig(output_dir=tmp_path / "research"))


def test_discovery_runner_writes_manifest_state_ledgers_and_snapshots(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path / "specs" / "quick.json", run_id="quick-run")

    result = run_discovery(spec_path=spec_path, app_config=_app_config(tmp_path), clock=_clock)

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    state = json.loads(result.run_state_path.read_text(encoding="utf-8"))
    interesting = pd.read_parquet(result.interesting_candidates_path)
    blocked = pd.read_parquet(result.blocked_candidates_path)
    filter_blockers = pd.read_parquet(result.filter_blockers_path)

    assert manifest["discovery_run_manifest_version"] == "discovery-run-manifest-v1"
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["order_placement_used"] is False
    assert manifest["candidate_pack_written"] is False
    assert state["status"] == "completed"
    assert state["completed_trial_ids"] == ["trial-000001", "trial-000002", "trial-000003"]
    assert len(interesting) == 1
    assert len(blocked) == 1
    assert len(filter_blockers) == 1
    assert len(list((result.output_dir / "snapshots").glob("*_snapshot.json"))) >= 2


def test_discovery_runner_resume_matches_uninterrupted_completed_ledgers(tmp_path: Path) -> None:
    full_spec = _write_spec(tmp_path / "full" / "quick.json", run_id="same-run")
    resumed_spec = _write_spec(tmp_path / "resumed" / "quick.json", run_id="same-run")

    full = run_discovery(spec_path=full_spec, app_config=_app_config(tmp_path / "full-output"), clock=_clock)
    partial = run_discovery(
        spec_path=resumed_spec,
        app_config=_app_config(tmp_path / "resumed-output"),
        stop_after_trials=1,
        clock=_clock,
    )
    resumed = run_discovery(
        spec_path=resumed_spec,
        app_config=_app_config(tmp_path / "resumed-output"),
        resume=True,
        clock=_clock,
    )

    full_interesting = pd.read_parquet(full.interesting_candidates_path)
    resumed_interesting = pd.read_parquet(resumed.interesting_candidates_path)
    resumed_state = json.loads(resumed.run_state_path.read_text(encoding="utf-8"))

    assert partial.output_dir == resumed.output_dir
    assert resumed_state["status"] == "completed"
    pd.testing.assert_frame_equal(full_interesting.reset_index(drop=True), resumed_interesting.reset_index(drop=True))


def test_discovery_runner_refuses_completed_run_overwrite(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path / "specs" / "quick.json", run_id="complete-run")
    run_discovery(spec_path=spec_path, app_config=_app_config(tmp_path), clock=_clock)

    with pytest.raises(ValueError, match="completed discovery runs refuse overwrite"):
        run_discovery(spec_path=spec_path, app_config=_app_config(tmp_path), resume=True, clock=_clock)


def test_discovery_runner_rejects_changed_spec_on_resume(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path / "specs" / "quick.json", run_id="changed-run", max_trials=3)
    run_discovery(spec_path=spec_path, app_config=_app_config(tmp_path), stop_after_trials=1, clock=_clock)
    _write_spec(spec_path, run_id="changed-run", max_trials=4)

    with pytest.raises(ValueError, match="changed discovery spec"):
        run_discovery(spec_path=spec_path, app_config=_app_config(tmp_path), resume=True, clock=_clock)


def test_discovery_runner_rejects_resume_with_missing_completed_trial_record(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path / "specs" / "quick.json", run_id="missing-record-run")
    partial = run_discovery(spec_path=spec_path, app_config=_app_config(tmp_path), stop_after_trials=1, clock=_clock)
    (partial.output_dir / "trials" / "trial-000001.json").unlink()

    with pytest.raises(ValueError, match="completed trial record missing on resume"):
        run_discovery(spec_path=spec_path, app_config=_app_config(tmp_path), resume=True, clock=_clock)


def test_discovery_runner_honors_snapshot_interval_between_batches(tmp_path: Path) -> None:
    spec_path = _write_spec(
        tmp_path / "specs" / "interval.json",
        run_id="interval-run",
        max_trials=3,
        trial_batch_size=99,
        snapshot_interval_minutes=30,
    )
    calls = {"count": 0}

    def advancing_clock() -> datetime:
        calls["count"] += 1
        return datetime(2026, 5, 7, 10, 0, tzinfo=timezone.utc) + timedelta(minutes=31 * calls["count"])

    result = run_discovery(spec_path=spec_path, app_config=_app_config(tmp_path), clock=advancing_clock)

    assert len(result.snapshot_paths) >= 4


def test_discovery_runner_records_feature_column_set_evidence(tmp_path: Path) -> None:
    spec_path = tmp_path / "specs" / "quick-feature-sets.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        json.dumps(
            {
                "run_id": "feature-set-run",
                "feature_column_sets_path": str(Path("configs/discovery/feature_column_sets_v4.json").resolve()),
                "feature_column_set_ids": ["price_trend_vol", "compact_wt3d_base"],
                "budget": {"max_trials": 1, "trial_batch_size": 1, "snapshot_interval_minutes": 30},
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    result = run_discovery(spec_path=spec_path, app_config=_app_config(tmp_path), clock=_clock)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    evidence = manifest["feature_column_set_evidence"]

    assert evidence["configured"] is True
    assert evidence["selected_feature_column_set_ids"] == ["price_trend_vol", "compact_wt3d_base"]
    assert evidence["selected_feature_column_set_count"] == 2
    assert evidence["wt3d_selected"] is True
    assert evidence["non_wt_selected"] is True
    assert evidence["promotion_ready"] is False
