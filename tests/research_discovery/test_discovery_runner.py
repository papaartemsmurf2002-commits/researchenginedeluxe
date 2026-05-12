from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from tradingbotsuite.config import AppConfig, ResearchConfig
from tradingbotsuite.research_discovery import runner as discovery_runner
from tradingbotsuite.research_discovery.runner import run_discovery
from tradingbotsuite.research_discovery.state import payload_sha256


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
    assert telemetry["telemetry_version"] == "discovery-compute-telemetry-v1"
    assert telemetry["wall_time_seconds"] >= 0.0
    assert telemetry["process_cpu_seconds"] >= 0.0
    assert telemetry["active_workers"] == 1
    assert telemetry["trials_per_minute"] >= 0.0
    assert telemetry["artifact_bytes_written"] > 0
    assert "spec_and_path_resolution" in telemetry["wall_time_seconds_by_stage"]
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
    assert [item[0] for item in knn_inputs] == ["1h", "4h", "1h"]
    assert [payload["hmm_cache_hit"] for payload in trial_payloads] == [False, True, True]
    assert [payload["label_split_cache_hit"] for payload in trial_payloads] == [False, False, True]
    assert [payload["neighbor_cache_hit"] for payload in trial_payloads] == [False, False, True]
    assert all(payload["neighbor_cache_lookup_count"] > 0 for payload in trial_payloads)
    pd.testing.assert_series_equal(knn_inputs[0][1], knn_inputs[2][1])
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
    assert not (result.output_dir / "trial_artifacts" / "trial-000001" / "hmm").exists()
    assert not (result.output_dir / "trial_artifacts" / "trial-000001" / "knn").exists()
    assert not list((result.output_dir / "trial_artifacts" / "trial-000001").rglob("*.parquet"))
