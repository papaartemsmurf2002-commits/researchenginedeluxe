from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from tradingbotsuite.config import AppConfig, ResearchConfig
from tradingbotsuite.research_discovery.knn_study import KnnStudyResult, KnnStudySpec
from tradingbotsuite.research_discovery import runner as discovery_runner
from tradingbotsuite.research_discovery import telemetry as discovery_telemetry
from tradingbotsuite.research_discovery.runner import run_discovery
from tradingbotsuite.research_discovery.spec import DiscoveryRunSpec, DiscoveryTrialTemplate
from tradingbotsuite.research_discovery.state import DiscoveryTrialRecord, payload_sha256


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
    telemetry = manifest["compute_telemetry"]
    assert telemetry["telemetry_version"] == "discovery-compute-telemetry-v2"
    assert telemetry["wall_time_seconds"] >= 0.0
    assert telemetry["process_cpu_seconds"] >= 0.0
    assert telemetry["active_workers"] == 1
    assert telemetry["logical_cpu_count"] >= 1
    assert telemetry["process_cpu_percent_of_worker_capacity"] is not None
    assert telemetry["process_cpu_percent_of_logical_capacity"] is not None
    assert telemetry["processor_utilization"]["active_workers"] == 1
    assert telemetry["processor_utilization"]["logical_cpu_count"] == telemetry["logical_cpu_count"]
    assert telemetry["processor_utilization"]["diagnostic_reasons"]
    assert telemetry["trials_per_minute"] >= 0.0
    assert telemetry["artifact_write_time_seconds_observed"] > 0.0
    assert telemetry["artifact_write_wall_time_share"] is not None
    assert telemetry["artifact_write_time_scope"] == (
        "runner_parent_resolved_spec_state_trial_records_ledgers_snapshots_excludes_final_manifest_write"
    )
    assert telemetry["artifact_bytes_written"] > 0
    assert telemetry["artifact_count_scope"] == "observed_parent_writes_this_call"
    assert telemetry["artifact_count_strategy"] == "recorded_artifact_write_paths_no_recursive_scan"
    assert "spec_and_path_resolution" in telemetry["wall_time_seconds_by_stage"]
    assert "final_status_state_write" in telemetry["wall_time_seconds_by_stage"]
    assert "final_ledger_materialization" in telemetry["wall_time_seconds_by_stage"]
    assert "final_snapshot_state_write" in telemetry["wall_time_seconds_by_stage"]
    assert "manifest_assembly_pre_telemetry" in telemetry["wall_time_seconds_by_stage"]
    assert {"feature_materialization", "label_split", "gmm_regime", "neighbor"} <= set(telemetry["cache_hit_rates"])
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


def test_discovery_runner_process_executor_smoke(tmp_path: Path) -> None:
    spec_path = tmp_path / "specs" / "process.json"
    payload = {
        "run_id": "process-executor-run",
        "symbol": "BTCUSDT",
        "timeframe": "15m",
        "budget": {"max_trials": 4, "trial_batch_size": 2, "snapshot_interval_minutes": 30},
        "execution": {"max_workers": 2, "executor": "process", "persist_trial_artifacts": "all"},
    }
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    result = run_discovery(spec_path=spec_path, app_config=_app_config(tmp_path))

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    state = json.loads(result.run_state_path.read_text(encoding="utf-8"))
    assert state["status"] == "completed"
    assert manifest["execution"]["executor"] == "process"
    assert manifest["execution_observed"]["executor"] == "process"
    assert manifest["execution_observed"]["configured_max_workers"] == 2
    assert manifest["execution_observed"]["requested_workers"] == 2
    assert manifest["compute_telemetry"]["executor"] == "process"
    assert manifest["compute_telemetry"]["worker_plan"]["active_workers"] == 2
    assert manifest["compute_telemetry"]["worker_plan"]["process_worker_cap_applied"] is False
    process_chunk_timing = manifest["compute_telemetry"]["process_chunk_timing"]
    assert process_chunk_timing["measured"] is True
    assert process_chunk_timing["chunk_count"] >= 1
    assert process_chunk_timing["worker_process_count"] >= 1
    assert process_chunk_timing["total_records"] == 4
    assert manifest["counts"]["completed_trials"] == 4


def test_discovery_runner_uses_observed_artifact_counts_without_recursive_scan(tmp_path: Path, monkeypatch) -> None:
    spec_path = _write_spec(tmp_path / "specs" / "quick.json", run_id="observed-counts-run")

    def fail_recursive_scan(output_dir: Path) -> dict[str, object]:
        raise AssertionError(f"unexpected recursive artifact scan: {output_dir}")

    monkeypatch.setattr(discovery_telemetry, "_artifact_counts", fail_recursive_scan)

    result = run_discovery(spec_path=spec_path, app_config=_app_config(tmp_path), clock=_clock)

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    telemetry = manifest["compute_telemetry"]
    assert telemetry["artifact_count_scope"] == "observed_parent_writes_this_call"
    assert telemetry["artifact_count_strategy"] == "recorded_artifact_write_paths_no_recursive_scan"
    assert telemetry["artifact_file_count"] > 0


def test_knn_threshold_view_reuses_base_predictions_without_changing_threshold_semantics() -> None:
    base_frame = pd.DataFrame(
        {
            "symbol": ["BTCUSDT", "BTCUSDT", "BTCUSDT", "BTCUSDT"],
            "source_row_index": [1, 2, 3, 4],
            "p_up_barrier": [0.70, 0.52, 0.80, 0.65],
            "p_down_barrier": [0.30, 0.48, 0.20, 0.35],
            "label_return": [0.01, 0.02, -0.01, 0.03],
            "expected_net_return_after_costs": [0.01, 0.02, -0.01, 0.03],
            "neighbor_agreement": [0.70, 0.52, 0.80, 0.65],
            "neighbor_distance_quality": [0.10, 0.10, 0.10, 0.001],
            "neighbor_count": [3, 3, 3, 1],
            "neighbor_min_source_index": [1, 1, 1, 1],
            "neighbor_max_source_index": [3, 3, 3, 1],
            "knn_vote_margin": [0.40, 0.04, 0.60, 0.30],
            "accepted_by_knn": [True, True, True, True],
            "knn_skip_reason": ["", "", "", ""],
        }
    )
    base = KnnStudyResult(
        frame=base_frame,
        manifest={"neighbor_diagnostics_included": False},
        neighbor_diagnostics=pd.DataFrame(),
    )
    spec = KnnStudySpec.from_payload(
        {
            "feature_columns": ["x"],
            "k": 3,
            "min_neighbor_count": 2,
            "probability_threshold": 0.60,
            "expected_value_threshold": 0.0,
            "min_neighbor_agreement": 0.60,
            "min_distance_quality": 0.01,
            "vote_margin_threshold": 0.10,
            "same_regime_only": False,
            "regime_mode": "none",
            "regime_detector_type": "none",
            "regime_gate_enabled": False,
            "same_regime_neighbor_pool_enabled": False,
        }
    )

    result = discovery_runner._threshold_knn_result(base, spec=spec, cache_hit=True)

    assert result.frame["accepted_by_knn"].tolist() == [True, False, False, False]
    assert result.frame["knn_skip_reason"].tolist() == [
        "",
        "probability_below_threshold",
        "expected_value_below_threshold",
        "insufficient_neighbors",
    ]
    assert discovery_runner._knn_threshold_metrics_from_base(
        base,
        spec=spec,
        search=SimpleNamespace(max_signal_rate=1.0, min_trade_count=1, min_signal_rate=0.0, min_realized_expectancy=-1.0),
        label_horizon_bars=1,
    ) == discovery_runner._knn_trial_metrics(
        result.frame,
        search=SimpleNamespace(max_signal_rate=1.0, min_trade_count=1, min_signal_rate=0.0, min_realized_expectancy=-1.0),
        label_horizon_bars=1,
    )
    assert result.manifest["knn_base_cache_hit"] is True
    assert result.manifest["threshold_view_from_base_knn"] is True


def test_cache_affinity_order_round_robins_base_knn_groups() -> None:
    def template(index: int, *, label_horizon: str, k: int, min_neighbor_count: int) -> DiscoveryTrialTemplate:
        return DiscoveryTrialTemplate(
            trial_id=f"trial-{index:06d}",
            candidate_id=f"candidate-{index:06d}",
            payload={
                "trial_kind": "regime_knn_entry_discovery",
                "feature_column_set_id": "price_trend_vol",
                "regime_mode": "none",
                "label_horizon": label_horizon,
                "distance_metric": "euclidean",
                "k": k,
                "min_neighbor_count": min_neighbor_count,
            },
        )

    pending = [
        (1, template(1, label_horizon="1h", k=8, min_neighbor_count=2)),
        (2, template(2, label_horizon="1h", k=8, min_neighbor_count=4)),
        (3, template(3, label_horizon="1h", k=8, min_neighbor_count=6)),
        (4, template(4, label_horizon="4h", k=8, min_neighbor_count=2)),
        (5, template(5, label_horizon="4h", k=8, min_neighbor_count=4)),
        (6, template(6, label_horizon="4h", k=8, min_neighbor_count=6)),
    ]

    ordered = discovery_runner._cache_affinity_ordered_trials(pending, block_size=2)
    chunks = discovery_runner._cache_affinity_trial_chunks(pending)

    assert [item[0] for item in ordered] == [1, 2, 4, 5, 3, 6]
    assert discovery_runner._max_cache_affinity_group_size(pending) == 3
    assert [[item[0] for item in chunk] for chunk in chunks] == [[1, 2, 3], [4, 5, 6]]


def test_interesting_only_policy_defers_heavy_trial_artifacts() -> None:
    assert discovery_runner._persist_trial_artifacts("all", ledger_kind="interesting") is True
    assert discovery_runner._persist_trial_artifacts("all", ledger_kind="blocked") is True
    assert discovery_runner._persist_trial_artifacts("interesting_only", ledger_kind="interesting") is False
    assert discovery_runner._persist_trial_artifacts("interesting_only", ledger_kind="blocked") is False


def test_real_discovery_process_worker_plan_caps_expanded_fixtures(monkeypatch) -> None:
    monkeypatch.delenv(discovery_runner.REAL_DISCOVERY_PROCESS_WORKER_CAP_ENV, raising=False)
    spec = DiscoveryRunSpec.from_payload(
        {
            "run_id": "worker-cap-run",
            "discovery_mode": "entry_discovery_standard",
            "execution": {"max_workers": 48, "executor": "process", "persist_trial_artifacts": "interesting_only"},
            "budget": {"max_trials": 64, "trial_batch_size": 10000, "snapshot_interval_minutes": 30},
        },
        spec_path=Path("worker-cap-run.json").resolve(),
    )
    pending = [
        (
            index,
            DiscoveryTrialTemplate(
                trial_id=f"trial-{index:06d}",
                candidate_id=f"candidate-{index:06d}",
                payload={"trial_kind": "regime_knn_entry_discovery"},
            ),
        )
        for index in range(1, 65)
    ]

    plan = discovery_runner._effective_worker_plan(
        spec,
        pending,
        real_discovery_requested=True,
        clock_supplied=False,
    )

    assert plan.executor == "process"
    assert plan.configured_max_workers == 48
    assert plan.requested_workers == 48
    assert plan.active_workers == discovery_runner.DEFAULT_REAL_DISCOVERY_PROCESS_WORKER_CAP
    assert plan.process_worker_cap_applied is True
    assert plan.process_worker_cap_source == "default_real_discovery_process_worker_cap"
    assert (
        f"real_discovery_process_worker_cap:48->{discovery_runner.DEFAULT_REAL_DISCOVERY_PROCESS_WORKER_CAP}"
        in plan.reason
    )


def test_real_discovery_process_worker_plan_honors_env_override(monkeypatch) -> None:
    monkeypatch.setenv(discovery_runner.REAL_DISCOVERY_PROCESS_WORKER_CAP_ENV, "3")
    spec = DiscoveryRunSpec.from_payload(
        {
            "run_id": "worker-cap-env-run",
            "discovery_mode": "entry_discovery_standard",
            "execution": {"max_workers": 48, "executor": "process", "persist_trial_artifacts": "interesting_only"},
            "budget": {"max_trials": 64, "trial_batch_size": 10000, "snapshot_interval_minutes": 30},
        },
        spec_path=Path("worker-cap-env-run.json").resolve(),
    )
    pending = [
        (
            index,
            DiscoveryTrialTemplate(
                trial_id=f"trial-{index:06d}",
                candidate_id=f"candidate-{index:06d}",
                payload={"trial_kind": "regime_knn_entry_discovery"},
            ),
        )
        for index in range(1, 65)
    ]

    plan = discovery_runner._effective_worker_plan(
        spec,
        pending,
        real_discovery_requested=True,
        clock_supplied=False,
    )

    assert plan.active_workers == 3
    assert plan.process_worker_cap == 3
    assert plan.process_worker_cap_source == f"env:{discovery_runner.REAL_DISCOVERY_PROCESS_WORKER_CAP_ENV}"
    assert plan.to_payload()["process_worker_cap_applied"] is True


def test_discovery_runner_resume_recovers_when_run_state_lags_trial_records(tmp_path: Path) -> None:
    spec_path = _write_spec(
        tmp_path / "specs" / "lagging-state.json",
        run_id="lagging-state-run",
        max_trials=3,
        trial_batch_size=3,
    )
    partial = run_discovery(
        spec_path=spec_path,
        app_config=_app_config(tmp_path),
        stop_after_trials=2,
        clock=_clock,
    )
    state_path = partial.run_state_path
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["completed_trial_ids"] == ["trial-000001", "trial-000002"]

    state["completed_trial_ids"] = ["trial-000001"]
    state["completed_trial_hashes"].pop("trial-000002")
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")

    resumed = run_discovery(spec_path=spec_path, app_config=_app_config(tmp_path), resume=True, clock=_clock)
    resumed_state = json.loads(resumed.run_state_path.read_text(encoding="utf-8"))
    ledgers = pd.concat(
        [
            pd.read_parquet(resumed.interesting_candidates_path),
            pd.read_parquet(resumed.blocked_candidates_path),
            pd.read_parquet(resumed.filter_blockers_path),
        ],
        ignore_index=True,
    )

    assert resumed_state["status"] == "completed"
    assert resumed_state["completed_trial_ids"] == ["trial-000001", "trial-000002", "trial-000003"]
    assert set(ledgers["trial_id"]) == {"trial-000001", "trial-000002", "trial-000003"}


def test_discovery_runner_large_zero_stop_resume_recovers_lag_without_full_hydration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec_path = _write_spec(
        tmp_path / "specs" / "large-lagging-state.json",
        run_id="large-lagging-state-run",
        max_trials=3,
        trial_batch_size=3,
    )
    partial = run_discovery(
        spec_path=spec_path,
        app_config=_app_config(tmp_path),
        stop_after_trials=2,
        clock=_clock,
    )
    state_path = partial.run_state_path
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["completed_trial_ids"] = ["trial-000001"]
    state["completed_trial_hashes"].pop("trial-000002")
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    monkeypatch.setenv(discovery_runner.DISCOVERY_RESUME_FULL_RECORD_LOAD_LIMIT_ENV, "1")

    def fail_full_hydration(*_args, **_kwargs):
        raise AssertionError("full trial hydration should be skipped for large resume")

    monkeypatch.setattr(discovery_runner, "_load_existing_trial_records", fail_full_hydration)

    resumed = run_discovery(
        spec_path=spec_path,
        app_config=_app_config(tmp_path),
        resume=True,
        stop_after_trials=0,
        clock=_clock,
    )
    resumed_state = json.loads(resumed.run_state_path.read_text(encoding="utf-8"))
    manifest = json.loads(resumed.manifest_path.read_text(encoding="utf-8"))

    assert resumed_state["status"] == "in_progress"
    assert resumed_state["completed_trial_ids"] == ["trial-000001", "trial-000002"]
    assert manifest["counts"]["completed_trials"] == 2
    assert manifest["state_checkpoint_policy"]["resume_catalog_mode"] == "state_checkpoint_with_lagging_trial_file_recovery"
    assert manifest["state_checkpoint_policy"]["resume_recovered_trial_file_count"] == 1
    assert manifest["compute_telemetry"]["completed_records_scope"] == "state_completed_with_partial_loaded_ledger_counts"


def test_discovery_runner_zero_stop_real_resume_skips_context_preparation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec_path = tmp_path / "specs" / "real-zero-stop.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        json.dumps(
            {
                "run_id": "real-zero-stop-run",
                "symbol": "BTCUSDT",
                "timeframe": "15m",
                "discovery_mode": "entry_discovery_standard",
                "feature_column_sets_path": str(Path("configs/discovery/feature_column_sets_v4.json").resolve()),
                "feature_column_set_ids": ["price_trend_vol"],
                "data": {
                    "dataset_manifest_paths": [
                        str(
                            Path(
                                "data/research/fixtures/btcusdt_context_provider_latest_month_v1/fixture_pack_manifest.json"
                            ).resolve()
                        )
                    ]
                },
                "budget": {"max_trials": 1, "trial_batch_size": 1, "snapshot_interval_minutes": 30, "rng_seed": 73},
                "execution": {"max_workers": 1, "persist_trial_artifacts": "interesting_only"},
                "search": {
                    "min_splits": 2,
                    "purge_embargo_bars": 2,
                    "label_horizons": ["1h"],
                    "k_values": [8],
                    "min_neighbor_counts": [1],
                    "probability_thresholds": [0.0],
                    "expected_value_thresholds": [-999999999.0],
                    "min_neighbor_agreements": [0.0],
                    "min_distance_qualities": [0.0],
                    "vote_margin_thresholds": [0.0],
                    "distance_metrics": ["cosine"],
                    "regime_modes": ["none"],
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    def fail_context(*_args, **_kwargs):
        raise AssertionError("zero-trial real resume should not prepare real discovery context")

    monkeypatch.setattr(discovery_runner, "_prepare_real_discovery_context", fail_context)

    result = run_discovery(
        spec_path=spec_path,
        app_config=_app_config(tmp_path),
        stop_after_trials=0,
        clock=_clock,
    )
    state = json.loads(result.run_state_path.read_text(encoding="utf-8"))

    assert state["status"] == "in_progress"
    assert state["completed_trial_ids"] == []


def test_discovery_runner_rejects_resume_with_old_real_score_policy(tmp_path: Path) -> None:
    spec_path = tmp_path / "specs" / "score-policy.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        json.dumps(
            {
                "run_id": "score-policy-run",
                "symbol": "BTCUSDT",
                "timeframe": "15m",
                "discovery_mode": "entry_discovery_standard",
                "feature_column_sets_path": str(Path("configs/discovery/feature_column_sets_v4.json").resolve()),
                "feature_column_set_ids": ["price_trend_vol"],
                "data": {
                    "dataset_manifest_paths": [
                        str(
                            Path(
                                "data/research/fixtures/btcusdt_context_provider_latest_month_v1/fixture_pack_manifest.json"
                            ).resolve()
                        )
                    ]
                },
                "budget": {"max_trials": 2, "trial_batch_size": 1, "snapshot_interval_minutes": 30, "rng_seed": 73},
                "execution": {"max_workers": 1, "persist_trial_artifacts": "interesting_only"},
                "search": {
                    "hmm_state_counts": [3],
                    "hmm_posterior_thresholds": [0.55],
                    "hmm_entropy_thresholds": [0.78],
                    "label_horizons": ["4h"],
                    "k_values": [8],
                    "min_neighbor_counts": [2, 4],
                    "distance_metrics": ["euclidean"],
                    "probability_thresholds": [0.52],
                    "expected_value_thresholds": [-0.0002],
                    "min_neighbor_agreements": [0.52],
                    "min_distance_qualities": [0.0],
                    "vote_margin_thresholds": [0.0],
                    "same_regime_only_values": [False],
                    "min_splits": 4,
                    "purge_embargo_bars": 8,
                    "min_trade_count": 1,
                    "min_signal_rate": 0.0,
                    "max_signal_rate": 1.0,
                    "min_realized_expectancy": -1.0,
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    partial = run_discovery(spec_path=spec_path, app_config=_app_config(tmp_path), stop_after_trials=1, clock=_clock)
    trial_path = partial.output_dir / "trials" / "trial-000001.json"
    trial_payload = json.loads(trial_path.read_text(encoding="utf-8"))
    trial_payload["payload"].pop("discovery_score_policy_version")
    trial_payload["record_sha256"] = payload_sha256(trial_payload)
    trial_path.write_text(json.dumps(trial_payload, indent=2, sort_keys=True), encoding="utf-8")

    with pytest.raises(ValueError, match="score policy upgrade"):
        run_discovery(spec_path=spec_path, app_config=_app_config(tmp_path), resume=True, clock=_clock)


def test_discovery_knn_metrics_use_side_adjusted_returns() -> None:
    frame = pd.DataFrame(
        [
            {
                "source_row_index": 0,
                "accepted_by_knn": True,
                "knn_skip_reason": "",
                "label_return": 0.02,
                "p_up_barrier": 0.70,
                "p_down_barrier": 0.30,
                "neighbor_distance_quality": 0.8,
                "knn_vote_margin": 0.4,
            },
            {
                "source_row_index": 1,
                "accepted_by_knn": True,
                "knn_skip_reason": "",
                "label_return": -0.03,
                "p_up_barrier": 0.25,
                "p_down_barrier": 0.75,
                "neighbor_distance_quality": 0.7,
                "knn_vote_margin": 0.5,
            },
            {
                "source_row_index": 2,
                "accepted_by_knn": True,
                "knn_skip_reason": "",
                "label_return": -0.04,
                "p_up_barrier": 0.35,
                "p_down_barrier": 0.65,
                "neighbor_distance_quality": 0.6,
                "knn_vote_margin": 0.3,
            },
        ]
    )
    search = SimpleNamespace(
        min_trade_count=3,
        min_signal_rate=0.0,
        max_signal_rate=2.0,
        min_realized_expectancy=0.025,
    )

    metrics = discovery_runner._knn_trial_metrics(frame, search=search)

    assert metrics["trade_count"] == 3
    assert metrics["realized_expectancy"] == pytest.approx(0.03)
    assert metrics["gross_realized_return"] == pytest.approx(0.09)
    assert metrics["passed"] is True


def test_discovery_runner_refuses_completed_run_overwrite(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path / "specs" / "quick.json", run_id="complete-run")
    run_discovery(spec_path=spec_path, app_config=_app_config(tmp_path), clock=_clock)

    with pytest.raises(ValueError, match="completed discovery runs refuse overwrite"):
        run_discovery(spec_path=spec_path, app_config=_app_config(tmp_path), resume=True, clock=_clock)


def test_discovery_runner_repairs_completed_run_with_stale_manifest(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path / "specs" / "quick.json", run_id="complete-repair-run")
    completed = run_discovery(spec_path=spec_path, app_config=_app_config(tmp_path), clock=_clock)
    manifest = json.loads(completed.manifest_path.read_text(encoding="utf-8"))
    manifest["counts"]["completed_trials"] = 1
    completed.manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    repaired = run_discovery(spec_path=spec_path, app_config=_app_config(tmp_path), resume=True, clock=_clock)
    repaired_state = json.loads(repaired.run_state_path.read_text(encoding="utf-8"))
    repaired_manifest = json.loads(repaired.manifest_path.read_text(encoding="utf-8"))

    assert repaired_state["status"] == "completed"
    assert repaired_manifest["counts"]["completed_trials"] == 3
    assert pd.read_parquet(repaired.blocked_candidates_path)["accepted_bar_count"].dtype.name == "Int64"


def test_discovery_runner_repairs_completed_run_with_corrupt_ledger(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path / "specs" / "quick.json", run_id="complete-ledger-repair-run")
    completed = run_discovery(spec_path=spec_path, app_config=_app_config(tmp_path), clock=_clock)
    completed.blocked_candidates_path.write_text("not parquet", encoding="utf-8")

    repaired = run_discovery(spec_path=spec_path, app_config=_app_config(tmp_path), resume=True, clock=_clock)

    repaired_manifest = json.loads(repaired.manifest_path.read_text(encoding="utf-8"))
    repaired_rows = (
        len(pd.read_parquet(repaired.interesting_candidates_path))
        + len(pd.read_parquet(repaired.blocked_candidates_path))
        + len(pd.read_parquet(repaired.filter_blockers_path))
    )
    assert repaired_manifest["counts"]["completed_trials"] == 3
    assert repaired_rows == 3


def test_discovery_ledger_frame_normalizes_empty_numeric_values(tmp_path: Path) -> None:
    records = [
        DiscoveryTrialRecord(
            run_id="ledger-schema-run",
            trial_id="trial-000001",
            attempt_id="attempt-001",
            trial_index=1,
            candidate_id="candidate-000001",
            candidate_family="regime_knn_entry_discovery",
            ledger_kind="blocked",
            score=0.0,
            payload={
                "accepted_bar_count": 3,
                "trade_count": 3,
                "near_signal_ceiling": False,
                "discovery_score_policy_version": discovery_runner.DISCOVERY_SCORE_POLICY_VERSION,
            },
        ),
        DiscoveryTrialRecord(
            run_id="ledger-schema-run",
            trial_id="trial-000002",
            attempt_id="attempt-001",
            trial_index=2,
            candidate_id="candidate-000002",
            candidate_family="regime_knn_entry_discovery",
            ledger_kind="blocked",
            score=0.0,
            payload={
                "accepted_bar_count": "",
                "trade_count": "",
                "near_signal_ceiling": "",
                "discovery_score_policy_version": discovery_runner.DISCOVERY_SCORE_POLICY_VERSION,
            },
        ),
    ]
    frame = discovery_runner._record_frame(records)
    path = tmp_path / "ledger.parquet"

    frame.to_parquet(path, index=False)
    loaded = pd.read_parquet(path)

    assert frame["accepted_bar_count"].dtype.name == "Int64"
    assert frame["near_signal_ceiling"].dtype.name == "boolean"
    assert loaded["accepted_bar_count"].isna().iloc[1]


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


def test_discovery_runner_executes_real_hmm_knn_trials(tmp_path: Path) -> None:
    spec_path = tmp_path / "specs" / "real-discovery.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        json.dumps(
            {
                "run_id": "real-discovery-run",
                "symbol": "BTCUSDT",
                "timeframe": "15m",
                "discovery_mode": "entry_discovery_standard",
                "feature_column_sets_path": str(Path("configs/discovery/feature_column_sets_v4.json").resolve()),
                "feature_column_set_ids": ["price_trend_vol", "compact_wt3d_base"],
                "data": {
                    "dataset_manifest_paths": [
                        str(
                            Path(
                                "data/research/fixtures/btcusdt_context_provider_latest_month_v1/fixture_pack_manifest.json"
                            ).resolve()
                        )
                    ]
                },
                "budget": {"max_trials": 2, "trial_batch_size": 1, "snapshot_interval_minutes": 30, "rng_seed": 73},
                "execution": {"max_workers": 2, "persist_trial_artifacts": "all"},
                "search": {
                    "hmm_state_counts": [3, 4],
                    "hmm_posterior_thresholds": [0.55],
                    "hmm_entropy_thresholds": [0.78],
                    "label_horizons": ["4h"],
                    "k_values": [8],
                    "min_neighbor_counts": [2, 4],
                    "distance_metrics": ["euclidean"],
                    "probability_thresholds": [0.52],
                    "expected_value_thresholds": [-0.0002],
                    "min_neighbor_agreements": [0.52],
                    "min_distance_qualities": [0.0],
                    "vote_margin_thresholds": [0.0],
                    "same_regime_only_values": [True, False],
                    "min_splits": 4,
                    "purge_embargo_bars": 8,
                    "min_trade_count": 1,
                    "min_signal_rate": 0.0,
                    "max_signal_rate": 1.0,
                    "min_realized_expectancy": -1.0,
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    result = run_discovery(spec_path=spec_path, app_config=_app_config(tmp_path), clock=_clock)

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    state = json.loads(result.run_state_path.read_text(encoding="utf-8"))
    ledger_parts = [
        frame
        for frame in (
            pd.read_parquet(result.interesting_candidates_path),
            pd.read_parquet(result.blocked_candidates_path),
            pd.read_parquet(result.filter_blockers_path),
        )
        if not frame.empty
    ]
    ledgers = pd.concat(ledger_parts, ignore_index=True)
    trial_record = json.loads((result.output_dir / "trials" / "trial-000001.json").read_text(encoding="utf-8"))
    payload = trial_record["payload"]

    assert manifest["candidate_acceptance_scope"] == "real_discovery_ledgers_no_pack_gate"
    assert manifest["execution"]["max_workers"] == 2
    assert manifest["execution"]["persist_trial_artifacts"] == "all"
    assert state["status"] == "completed"
    assert state["message"] == "real discovery run completed"
    assert len(ledgers) == 2
    assert ledgers["trade_count"].astype(int).sum() > 0
    assert set(ledgers["feature_column_set_id"]).issubset({"price_trend_vol", "compact_wt3d_base"})
    assert payload["placeholder_trial"] is False
    assert payload["trial_kind"] == "regime_knn_entry_discovery"
    assert payload["regime_mode"] in {
        "none",
        "gmm_gate_only",
        "gmm_same_regime_neighbors",
        "gmm_all_regime_neighbors_with_gate",
    }
    assert payload["regime_detector_type"] in {"none", "gmm"}
    assert payload["true_hmm_backend_used"] is False
    assert {
        "regime_mode",
        "regime_detector_type",
        "regime_gate_enabled",
        "same_regime_neighbor_pool_enabled",
        "true_hmm_backend_used",
        "discovery_score_policy_version",
        "accepted_bar_count",
        "independent_event_count",
        "suppressed_overlap_count",
        "overlap_ratio",
        "event_signal_rate",
        "side_collapse_ratio",
        "event_spacing_bars",
        "legacy_density_score",
        "discovery_screen_score_v2",
    } <= set(ledgers.columns)
    assert payload["trade_count"] > 0
    assert payload["trade_count"] == payload["independent_event_count"]
    assert payload["accepted_bar_count"] >= payload["independent_event_count"]
    assert payload["final_score"] == payload["discovery_screen_score_v2"]
    assert payload["hmm_artifact_persisted"] is True
    assert payload["knn_artifact_persisted"] is True
    assert Path(payload["hmm_manifest_path"]).exists()
    assert Path(payload["knn_manifest_path"]).exists()
    assert manifest["regime_truthfulness"]["true_hmm_backend_used"] is False
    assert manifest["regime_truthfulness"]["current_gmm_backend"] == "sklearn.mixture.GaussianMixture"
    assert manifest["event_accounting_policy"]["active_score_field"] == "discovery_screen_score_v2"
    assert manifest["event_accounting_policy"]["overlapping_bar_signals_count_as_independent_trades"] is False


def test_discovery_runner_no_regime_trial_skips_gmm_materializer(tmp_path: Path, monkeypatch) -> None:
    spec_path = tmp_path / "specs" / "no-regime-discovery.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        json.dumps(
            {
                "run_id": "no-regime-run",
                "symbol": "BTCUSDT",
                "timeframe": "15m",
                "discovery_mode": "entry_discovery_standard",
                "feature_column_sets_path": str(Path("configs/discovery/feature_column_sets_v4.json").resolve()),
                "feature_column_set_ids": ["price_trend_vol"],
                "data": {
                    "dataset_manifest_paths": [
                        str(
                            Path(
                                "data/research/fixtures/btcusdt_context_provider_latest_month_v1/fixture_pack_manifest.json"
                            ).resolve()
                        )
                    ]
                },
                "budget": {"max_trials": 1, "trial_batch_size": 1, "snapshot_interval_minutes": 30, "rng_seed": 73},
                "execution": {"max_workers": 1, "persist_trial_artifacts": "all"},
                "search": {
                    "min_splits": 4,
                    "purge_embargo_bars": 8,
                    "min_trade_count": 999999,
                    "min_signal_rate": 0.0,
                    "max_signal_rate": 1.0,
                    "min_realized_expectancy": 0.0,
                },
                "trial_templates": [
                    {
                        "trial_id": "trial-000001",
                        "candidate_id": "no-regime-candidate",
                        "candidate_family": "regime_knn_entry_discovery",
                        "ledger_kind": "blocked",
                        "blocker_code": "not_evaluated",
                        "payload": {
                            "trial_kind": "regime_knn_entry_discovery",
                            "feature_column_set_id": "price_trend_vol",
                            "regime_mode": "none",
                            "label_horizon": "4h",
                            "k": 8,
                            "min_neighbor_count": 2,
                            "distance_metric": "euclidean",
                            "probability_threshold": 0.52,
                            "expected_value_threshold": -0.0002,
                            "min_neighbor_agreement": 0.52,
                            "min_distance_quality": 0.0,
                            "vote_margin_threshold": 0.0,
                            "same_regime_only": False,
                        },
                    }
                ],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    def fail_gmm(*args, **kwargs):
        raise AssertionError("no-regime mode must not call the GMM materializer")

    monkeypatch.setattr(discovery_runner, "materialize_split_safe_hmm_regimes", fail_gmm)

    result = discovery_runner.run_discovery(spec_path=spec_path, app_config=_app_config(tmp_path), clock=_clock)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    trial_record = json.loads((result.output_dir / "trials" / "trial-000001.json").read_text(encoding="utf-8"))
    payload = trial_record["payload"]
    regime_manifest = json.loads(Path(payload["hmm_manifest_path"]).read_text(encoding="utf-8"))
    knn_manifest = json.loads(Path(payload["knn_manifest_path"]).read_text(encoding="utf-8"))

    assert trial_record["status"] == "completed"
    assert payload["regime_mode"] == "none"
    assert payload["regime_detector_type"] == "none"
    assert payload["regime_gate_enabled"] is False
    assert payload["same_regime_neighbor_pool_enabled"] is False
    assert payload["same_regime_only"] is False
    assert payload["true_hmm_backend_used"] is False
    assert payload["hmm_state_count"] == 0
    assert payload["hmm_posterior_threshold"] is None
    assert payload["hmm_entropy_threshold"] is None
    assert payload["hmm_cache_hit"] is False
    assert regime_manifest["regime_detector_type"] == "none"
    assert regime_manifest["regime_gate_enabled"] is False
    assert knn_manifest["regime_mode"] == "none"
    assert knn_manifest["regime_gate_enabled"] is False
    assert manifest["regime_truthfulness"]["observed_trial_regime_modes"] == ["none"]
    assert manifest["regime_truthfulness"]["observed_trial_regime_detector_types"] == ["none"]
    assert manifest["regime_truthfulness"]["true_hmm_backend_used"] is False


def test_discovery_runner_passes_trial_knn_payload_to_evaluator(tmp_path: Path, monkeypatch) -> None:
    spec_path = tmp_path / "specs" / "knn-payload-discovery.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        json.dumps(
            {
                "run_id": "knn-payload-run",
                "symbol": "BTCUSDT",
                "timeframe": "15m",
                "discovery_mode": "entry_discovery_standard",
                "feature_column_sets_path": str(Path("configs/discovery/feature_column_sets_v4.json").resolve()),
                "feature_column_set_ids": ["price_trend_vol"],
                "data": {
                    "dataset_manifest_paths": [
                        str(
                            Path(
                                "data/research/fixtures/btcusdt_public_archive_multi_window_v1/fixture_pack_manifest.json"
                            ).resolve()
                        )
                    ]
                },
                "budget": {"max_trials": 1, "trial_batch_size": 1, "snapshot_interval_minutes": 30, "rng_seed": 73},
                "execution": {"max_workers": 1, "persist_trial_artifacts": "interesting_only"},
                "search": {
                    "min_splits": 2,
                    "purge_embargo_bars": 2,
                    "min_trade_count": 1,
                    "min_signal_rate": 0.0,
                    "max_signal_rate": 1.0,
                    "min_realized_expectancy": -1.0,
                },
                "trial_templates": [
                    {
                        "trial_id": "trial-000001",
                        "candidate_id": "knn-payload-candidate",
                        "candidate_family": "regime_knn_entry_discovery",
                        "ledger_kind": "blocked",
                        "blocker_code": "not_evaluated",
                        "payload": {
                            "trial_kind": "regime_knn_entry_discovery",
                            "feature_column_set_id": "price_trend_vol",
                            "regime_mode": "none",
                            "label_horizon": "1h",
                            "k": 13,
                            "min_neighbor_count": 5,
                            "distance_metric": "cosine",
                            "probability_threshold": 0.58,
                            "expected_value_threshold": 0.0002,
                            "min_neighbor_agreement": 0.60,
                            "min_distance_quality": 0.01,
                            "vote_margin_threshold": 0.05,
                            "same_regime_only": False,
                        },
                    }
                ],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    captured_specs = []

    def fake_knn(frame, *, splits, spec, **kwargs):
        captured_specs.append(spec)
        result = frame.copy()
        result["p_up_barrier"] = 0.5
        result["p_down_barrier"] = 0.5
        result["expected_net_return_after_costs"] = 0.0
        result["neighbor_agreement"] = 0.0
        result["neighbor_distance_quality"] = 0.0
        result["neighbor_count"] = 0
        result["neighbor_min_source_index"] = -1
        result["neighbor_max_source_index"] = -1
        result["knn_vote_margin"] = 0.0
        result["accepted_by_knn"] = False
        result["knn_skip_reason"] = "probability_below_threshold"
        return KnnStudyResult(
            frame=result,
            manifest={
                "label_horizon_bars": 4,
                "neighbor_cache_lookup_count": 0,
                "neighbor_cache_hit_count": 0,
            },
            neighbor_diagnostics=pd.DataFrame(),
        )

    monkeypatch.setattr(discovery_runner, "materialize_regime_local_knn_predictions", fake_knn)

    result = discovery_runner.run_discovery(spec_path=spec_path, app_config=_app_config(tmp_path), clock=_clock)
    trial_record = json.loads((result.output_dir / "trials" / "trial-000001.json").read_text(encoding="utf-8"))
    payload = trial_record["payload"]
    knn_spec = captured_specs[0]

    assert trial_record["status"] == "completed"
    assert len(captured_specs) == 1
    assert knn_spec.feature_column_set_id == "price_trend_vol"
    assert knn_spec.label_horizon == "1h"
    assert knn_spec.k == 13
    assert knn_spec.min_neighbor_count == 1
    assert knn_spec.distance_metric == "cosine"
    assert knn_spec.probability_threshold == pytest.approx(0.0)
    assert knn_spec.expected_value_threshold < -1.0e8
    assert knn_spec.min_neighbor_agreement == pytest.approx(0.0)
    assert knn_spec.min_distance_quality == pytest.approx(0.0)
    assert knn_spec.vote_margin_threshold == pytest.approx(0.0)
    assert knn_spec.regime_mode == "none"
    assert knn_spec.regime_detector_type == "none"
    assert knn_spec.regime_gate_enabled is False
    assert knn_spec.same_regime_neighbor_pool_enabled is False
    assert knn_spec.same_regime_only is False
    assert knn_spec.feature_columns == ("log_return_1", "log_return_4")
    assert payload["feature_column_set_id"] == "price_trend_vol"
    assert payload["configured_feature_columns"] == [
        "log_return_1",
        "log_return_4",
        "trend_slope_20",
        "efficiency_ratio",
        "directional_slope_atr",
        "realized_volatility",
        "atr_percentile",
    ]
    assert payload["effective_feature_columns"] == ["log_return_1", "log_return_4"]
    assert payload["pruned_feature_column_count"] == 5
    assert payload["label_horizon"] == "1h"
    assert payload["k"] == 13
    assert payload["min_neighbor_count"] == 5
    assert payload["distance_metric"] == "cosine"
    assert payload["probability_threshold"] == pytest.approx(0.58)
    assert payload["expected_value_threshold"] == pytest.approx(0.0002)
    assert payload["min_neighbor_agreement"] == pytest.approx(0.60)
    assert payload["min_distance_quality"] == pytest.approx(0.01)
    assert payload["vote_margin_threshold"] == pytest.approx(0.05)


def test_discovery_runner_failed_real_trial_preserves_search_payload(tmp_path: Path, monkeypatch) -> None:
    spec_path = tmp_path / "specs" / "failed-knn-payload-discovery.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        json.dumps(
            {
                "run_id": "failed-knn-payload-run",
                "symbol": "BTCUSDT",
                "timeframe": "15m",
                "discovery_mode": "entry_discovery_standard",
                "feature_column_sets_path": str(Path("configs/discovery/feature_column_sets_v4.json").resolve()),
                "feature_column_set_ids": ["price_trend_vol"],
                "data": {
                    "dataset_manifest_paths": [
                        str(
                            Path(
                                "data/research/fixtures/btcusdt_public_archive_multi_window_v1/fixture_pack_manifest.json"
                            ).resolve()
                        )
                    ]
                },
                "budget": {"max_trials": 1, "trial_batch_size": 1, "snapshot_interval_minutes": 30, "rng_seed": 73},
                "execution": {"max_workers": 1, "persist_trial_artifacts": "interesting_only"},
                "search": {
                    "min_splits": 2,
                    "purge_embargo_bars": 2,
                    "min_trade_count": 1,
                    "min_signal_rate": 0.0,
                    "max_signal_rate": 1.0,
                    "min_realized_expectancy": -1.0,
                },
                "trial_templates": [
                    {
                        "trial_id": "trial-000001",
                        "candidate_id": "failed-knn-payload-candidate",
                        "candidate_family": "regime_knn_entry_discovery",
                        "ledger_kind": "blocked",
                        "blocker_code": "not_evaluated",
                        "payload": {
                            "trial_kind": "regime_knn_entry_discovery",
                            "feature_column_set_id": "price_trend_vol",
                            "regime_mode": "none",
                            "label_horizon": "2h",
                            "k": 21,
                            "min_neighbor_count": 4,
                            "distance_metric": "manhattan",
                            "probability_threshold": 0.62,
                            "expected_value_threshold": -0.0002,
                            "min_neighbor_agreement": 0.55,
                            "min_distance_quality": 0.005,
                            "vote_margin_threshold": 0.03,
                            "same_regime_only": False,
                        },
                    }
                ],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    def fail_knn(*args, **kwargs):
        raise RuntimeError("forced knn failure")

    monkeypatch.setattr(discovery_runner, "materialize_regime_local_knn_predictions", fail_knn)

    result = discovery_runner.run_discovery(spec_path=spec_path, app_config=_app_config(tmp_path), clock=_clock)
    trial_record = json.loads((result.output_dir / "trials" / "trial-000001.json").read_text(encoding="utf-8"))
    payload = trial_record["payload"]

    assert trial_record["status"] == "failed"
    assert trial_record["error_payload"]["error_type"] == "RuntimeError"
    assert payload["feature_column_set_id"] == "price_trend_vol"
    assert payload["regime_mode"] == "none"
    assert payload["regime_detector_type"] == "none"
    assert payload["same_regime_only"] is False
    assert payload["label_horizon"] == "2h"
    assert payload["k"] == 21
    assert payload["min_neighbor_count"] == 4
    assert payload["distance_metric"] == "manhattan"
    assert payload["probability_threshold"] == pytest.approx(0.62)
    assert payload["expected_value_threshold"] == pytest.approx(-0.0002)
    assert payload["min_neighbor_agreement"] == pytest.approx(0.55)
    assert payload["min_distance_quality"] == pytest.approx(0.005)
    assert payload["vote_margin_threshold"] == pytest.approx(0.03)
    assert payload["final_score"] == 0.0
    assert payload["knn_artifact_persisted"] is False


def test_discovery_runner_reuses_hmm_across_horizons_without_label_leak(tmp_path: Path, monkeypatch) -> None:
    spec_path = tmp_path / "specs" / "horizon-cache-discovery.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)

    def trial_template(index: int, label_horizon: str) -> dict[str, object]:
        return {
            "trial_id": f"trial-{index:06d}",
            "candidate_id": f"horizon-cache-candidate-{index:06d}",
            "candidate_family": "regime_knn_entry_discovery",
            "ledger_kind": "blocked",
            "blocker_code": "not_evaluated",
            "payload": {
                "trial_kind": "regime_knn_entry_discovery",
                "feature_column_set_id": "price_trend_vol",
                "hmm_state_count": 3,
                "hmm_posterior_threshold": 0.55,
                "hmm_entropy_threshold": 0.78,
                "label_horizon": label_horizon,
                "k": 8,
                "min_neighbor_count": 2,
                "distance_metric": "euclidean",
                "probability_threshold": 0.52,
                "expected_value_threshold": -0.0002,
                "min_neighbor_agreement": 0.52,
                "min_distance_quality": 0.0,
                "vote_margin_threshold": 0.0,
                "same_regime_only": True,
            },
        }

    spec_path.write_text(
        json.dumps(
            {
                "run_id": "horizon-cache-run",
                "symbol": "BTCUSDT",
                "timeframe": "15m",
                "discovery_mode": "entry_discovery_standard",
                "feature_column_sets_path": str(Path("configs/discovery/feature_column_sets_v4.json").resolve()),
                "feature_column_set_ids": ["price_trend_vol"],
                "data": {
                    "dataset_manifest_paths": [
                        str(
                            Path(
                                "data/research/fixtures/btcusdt_context_provider_latest_month_v1/fixture_pack_manifest.json"
                            ).resolve()
                        )
                    ]
                },
                "budget": {"max_trials": 3, "trial_batch_size": 3, "snapshot_interval_minutes": 30, "rng_seed": 73},
                "execution": {"max_workers": 1, "persist_trial_artifacts": "interesting_only"},
                "search": {
                    "min_splits": 4,
                    "purge_embargo_bars": 8,
                    "min_trade_count": 999999,
                    "min_signal_rate": 0.0,
                    "max_signal_rate": 1.0,
                    "min_realized_expectancy": 0.0,
                },
                "trial_templates": [trial_template(1, "1h"), trial_template(2, "4h"), trial_template(3, "1h")],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    hmm_calls = []
    knn_inputs = []
    original_hmm = discovery_runner.materialize_split_safe_hmm_regimes
    original_knn = discovery_runner.materialize_regime_local_knn_predictions

    def wrapped_hmm(frame, *, splits, spec):
        hmm_calls.append(pd.to_numeric(frame["label_return"], errors="coerce").reset_index(drop=True))
        return original_hmm(frame, splits=splits, spec=spec)

    def wrapped_knn(frame, *, splits, spec, **kwargs):
        knn_inputs.append((spec.label_horizon, pd.to_numeric(frame["label_return"], errors="coerce").reset_index(drop=True)))
        return original_knn(frame, splits=splits, spec=spec, **kwargs)

    monkeypatch.setattr(discovery_runner, "materialize_split_safe_hmm_regimes", wrapped_hmm)
    monkeypatch.setattr(discovery_runner, "materialize_regime_local_knn_predictions", wrapped_knn)

    result = discovery_runner.run_discovery(spec_path=spec_path, app_config=_app_config(tmp_path), clock=_clock)
    trial_payloads = [
        json.loads((result.output_dir / "trials" / f"trial-{index:06d}.json").read_text(encoding="utf-8"))["payload"]
        for index in range(1, 4)
    ]

    assert len(hmm_calls) == 1
    assert [item[0] for item in knn_inputs] == ["1h", "4h"]
    assert [payload["hmm_cache_hit"] for payload in trial_payloads] == [False, True, True]
    assert [payload["label_split_cache_hit"] for payload in trial_payloads] == [False, False, True]
    assert [payload["knn_base_cache_hit"] for payload in trial_payloads] == [False, False, True]
    assert all(payload["neighbor_cache_lookup_count"] > 0 for payload in trial_payloads)
    assert not knn_inputs[0][1].equals(knn_inputs[1][1])


def test_discovery_runner_compacts_blocked_real_trial_artifacts(tmp_path: Path) -> None:
    spec_path = tmp_path / "specs" / "compact-blocked-discovery.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        json.dumps(
            {
                "run_id": "compact-blocked-run",
                "symbol": "BTCUSDT",
                "timeframe": "15m",
                "discovery_mode": "entry_discovery_standard",
                "feature_column_sets_path": str(Path("configs/discovery/feature_column_sets_v4.json").resolve()),
                "feature_column_set_ids": ["price_trend_vol"],
                "data": {
                    "dataset_manifest_paths": [
                        str(
                            Path(
                                "data/research/fixtures/btcusdt_context_provider_latest_month_v1/fixture_pack_manifest.json"
                            ).resolve()
                        )
                    ]
                },
                "budget": {"max_trials": 1, "trial_batch_size": 1, "snapshot_interval_minutes": 30, "rng_seed": 73},
                "execution": {"max_workers": 1, "persist_trial_artifacts": "interesting_only"},
                "search": {
                    "label_horizons": ["4h"],
                    "k_values": [8],
                    "min_neighbor_counts": [4],
                    "distance_metrics": ["euclidean"],
                    "probability_thresholds": [0.99],
                    "expected_value_thresholds": [1.0],
                    "min_neighbor_agreements": [0.99],
                    "min_distance_qualities": [1.0],
                    "vote_margin_thresholds": [0.99],
                    "same_regime_only_values": [True],
                    "min_splits": 4,
                    "purge_embargo_bars": 8,
                    "min_trade_count": 999999,
                    "min_signal_rate": 0.0,
                    "max_signal_rate": 1.0,
                    "min_realized_expectancy": 0.0,
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    result = run_discovery(spec_path=spec_path, app_config=_app_config(tmp_path), clock=_clock)
    trial_record = json.loads((result.output_dir / "trials" / "trial-000001.json").read_text(encoding="utf-8"))
    payload = trial_record["payload"]

    assert trial_record["ledger_kind"] == "blocked"
    assert payload["hmm_artifact_persisted"] is False
    assert payload["knn_artifact_persisted"] is False
    assert payload["strategy_accounting_persisted"] is False
    assert not (result.output_dir / "trial_artifacts" / "trial-000001").exists()
    assert not (result.output_dir / "trial_artifacts" / "trial-000001" / "hmm").exists()
    assert not (result.output_dir / "trial_artifacts" / "trial-000001" / "knn").exists()
    assert not list((result.output_dir / "trial_artifacts" / "trial-000001").rglob("*.parquet"))
