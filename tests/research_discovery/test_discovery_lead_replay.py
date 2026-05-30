from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from tradingbotsuite.research_discovery.discovery_lead_replay import (
    aggregate_discovery_replay_entry_signals,
    build_discovery_lead_replay_spec,
    validate_discovery_replay_entry_signal_manifest,
    write_discovery_lead_replay_spec,
    write_discovery_replay_entry_signal_artifacts,
)
from tradingbotsuite.research_discovery.state import DiscoveryTrialRecord, write_trial_record


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _source_trial() -> DiscoveryTrialRecord:
    return DiscoveryTrialRecord(
        run_id="source-discovery",
        trial_id="trial-000001",
        attempt_id="attempt-001",
        trial_index=1,
        candidate_id="source-candidate-1",
        candidate_family="regime_knn_entry_discovery",
        ledger_kind="interesting",
        score=0.42,
        payload={
            "trial_kind": "regime_knn_entry_discovery",
            "feature_column_set_id": "compact_wt3d_base",
            "registered_feature_set_id": "features_price_trend_vol_wt3d",
            "regime_mode": "none",
            "regime_detector_type": "none",
            "label_horizon": "1h",
            "distance_metric": "cosine",
            "k": 13,
            "min_neighbor_count": 5,
            "probability_threshold": 0.62,
            "expected_value_threshold": -0.0002,
            "min_neighbor_agreement": 0.55,
            "min_distance_quality": 0.0,
            "vote_margin_threshold": 0.03,
        },
    )


def _write_source_materialization_fixture(tmp_path: Path) -> Path:
    source_dir = tmp_path / "source_discovery"
    trials_dir = source_dir / "trials"
    trial = _source_trial()
    trial_path = trials_dir / "trial-000001.json"
    write_trial_record(trial_path, trial)
    trial_sha = trial.to_payload()["record_sha256"]
    resolved_spec = {
        "spec_version": "discovery-run-spec-v1",
        "run_id": "source-discovery",
        "symbol": "BTCUSDT",
        "timeframe": "15m",
        "discovery_mode": "deep_candidate_harvest",
        "research_output_dir": str(tmp_path / "data" / "research"),
        "output_dir": str(source_dir),
        "feature_column_sets_path": str(tmp_path / "configs" / "discovery" / "feature_column_sets_v4.json"),
        "feature_column_set_ids": ["price_trend_vol", "compact_wt3d_base"],
        "data": {"dataset_path": str(tmp_path / "dataset.parquet"), "dataset_manifest_paths": []},
        "budget": {"max_trials": 100, "trial_batch_size": 10, "snapshot_interval_minutes": 15, "rng_seed": 7},
        "execution": {"max_workers": 1, "executor": "thread", "persist_trial_artifacts": "interesting_only"},
        "search": {
            "hmm_state_counts": [3],
            "hmm_posterior_thresholds": [0.55],
            "hmm_entropy_thresholds": [0.78],
            "label_horizons": ["1h"],
            "k_values": [13],
            "min_neighbor_counts": [5],
            "distance_metrics": ["cosine"],
            "probability_thresholds": [0.62],
            "expected_value_thresholds": [-0.0002],
            "min_neighbor_agreements": [0.55],
            "min_distance_qualities": [0.0],
            "vote_margin_thresholds": [0.03],
            "same_regime_only_values": [False],
            "regime_modes": ["none"],
            "min_splits": 2,
            "purge_embargo_bars": 2,
            "min_trade_count": 1,
            "min_signal_rate": 0.0007,
            "max_signal_rate": 0.45,
            "min_realized_expectancy": -0.00015,
        },
        "trial_templates": [],
    }
    resolved_spec_path = _write_json(source_dir / "discovery_spec_resolved.json", resolved_spec)
    source_manifest_path = _write_json(
        source_dir / "discovery_run_manifest.json",
        {
            "discovery_run_manifest_version": "discovery-run-manifest-v1",
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "run_id": "source-discovery",
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "required_outputs": {
                "discovery_spec_resolved": str(resolved_spec_path),
                "trials": str(trials_dir),
            },
        },
    )
    materialized = pd.DataFrame(
        [
            {
                "materialized_candidate_id": "mat-0001",
                "materialized_candidate_family": "frozen_knn_entry_lead_v1",
                "source_run_id": "source-discovery",
                "source_trial_id": "trial-000001",
                "source_discovery_candidate_id": "source-candidate-1",
                "source_candidate_family": "regime_knn_entry_discovery",
                "source_record_sha256": trial_sha,
                "feature_column_set_id": "compact_wt3d_base",
                "prediction_signature_hash": "pred-sha",
                "entry_event_signature_hash": "entry-sha",
                "effective_trial_key": "trial-key",
                "final_score": 0.42,
            }
        ]
    )
    materialized_path = tmp_path / "materialized" / "materialized_discovery_leads.parquet"
    materialized_path.parent.mkdir(parents=True, exist_ok=True)
    materialized.to_parquet(materialized_path, index=False)
    return _write_json(
        tmp_path / "materialized" / "discovery_lead_materialization_manifest.json",
        {
            "discovery_lead_materialization_manifest_version": "discovery-lead-materialization-manifest-v1",
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "source_symbol": "BTCUSDT",
            "source_timeframe": "15m",
            "source_discovery_manifest_path": str(source_manifest_path),
            "source_trials_dir": str(trials_dir),
            "required_outputs": {"materialized_discovery_leads": str(materialized_path)},
        },
    )


def test_build_discovery_lead_replay_spec_preserves_source_identity(tmp_path: Path) -> None:
    materialization_manifest = _write_source_materialization_fixture(tmp_path)

    result = build_discovery_lead_replay_spec(
        materialization_manifest_path=materialization_manifest,
        run_id="wpr106-31-replay-btcusdt",
        output_dir=tmp_path / "replay" / "discovery_run",
        research_output_dir=tmp_path / "data" / "research",
    )
    artifact = write_discovery_lead_replay_spec(tmp_path / "replay" / "discovery_replay_spec.json", result)

    payload = result.spec_payload
    template = payload["trial_templates"][0]
    inner = template["payload"]
    assert artifact.spec_path.exists()
    assert payload["execution"]["persist_trial_artifacts"] == "predictions_only"
    assert payload["budget"]["max_trials"] == 1
    assert payload["feature_column_set_ids"] == ["price_trend_vol", "compact_wt3d_base"]
    assert template["candidate_id"] == "mat-0001"
    assert inner["trial_kind"] == "regime_knn_entry_discovery"
    assert inner["source_discovery_candidate_id"] == "source-candidate-1"
    assert inner["source_record_sha256"]
    assert inner["materialized_candidate_id"] == "mat-0001"


def test_aggregate_discovery_replay_entry_signals_adds_exit_lab_join_keys(tmp_path: Path) -> None:
    replay_dir = tmp_path / "replay"
    trials_dir = replay_dir / "trials"
    accounting_dir = replay_dir / "trial_artifacts" / "trial-000001" / "attempt-001" / "strategy_accounting"
    signals_path = accounting_dir / "strategy_signals.parquet"
    signals_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "signal_id": "sig-1",
                "signal_time_ms": 1712649600000,
                "symbol": "BTCUSDT",
                "side": "long",
                "strength": 0.7,
                "confidence": 0.8,
                "signal_bar_close": 100.0,
                "strategy_id": "hmm_knn_local_analog_filter_v2",
                "feature_set_id": "features_perp_context_v2",
                "skip_reason": "",
                "research_only": True,
            }
        ]
    ).to_parquet(signals_path, index=False)
    accounting_manifest = _write_json(
        accounting_dir / "strategy_accounting_manifest.json",
        {
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "required_outputs": {"strategy_signals": str(signals_path)},
        },
    )
    trial = DiscoveryTrialRecord(
        run_id="replay-run",
        trial_id="trial-000001",
        attempt_id="attempt-001",
        trial_index=1,
        candidate_id="mat-0001",
        candidate_family="regime_knn_entry_discovery",
        ledger_kind="interesting",
        score=0.42,
        payload={
            "strategy_accounting_manifest_path": str(accounting_manifest),
            "source_record_sha256": "source-record",
            "source_discovery_candidate_id": "source-candidate-1",
            "materialized_candidate_id": "mat-0001",
            "source_trial_id": "trial-source",
        },
    )
    write_trial_record(trials_dir / "trial-000001.json", trial)
    interesting_path = replay_dir / "candidate_ledgers" / "interesting_candidates.parquet"
    interesting_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"trial_id": "trial-000001", "candidate_id": "mat-0001"}]).to_parquet(interesting_path, index=False)
    manifest_path = _write_json(
        replay_dir / "discovery_run_manifest.json",
        {
            "discovery_run_manifest_version": "discovery-run-manifest-v1",
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "required_outputs": {
                "interesting_candidates": str(interesting_path),
                "trials": str(trials_dir),
            },
        },
    )

    result = aggregate_discovery_replay_entry_signals(replay_discovery_manifest_path=manifest_path)
    artifact = write_discovery_replay_entry_signal_artifacts(tmp_path / "entry_signals", result)

    assert artifact.manifest_path.exists()
    assert artifact.signals_path.exists()
    manifest = json.loads(artifact.manifest_path.read_text(encoding="utf-8"))
    assert validate_discovery_replay_entry_signal_manifest(manifest) == []
    signals = pd.read_parquet(artifact.signals_path)
    assert signals.loc[0, "candidate_id"] == "mat-0001"
    assert signals.loc[0, "trial_id"] == "trial-000001"
    assert signals.loc[0, "record_sha256"] == trial.to_payload()["record_sha256"]
    assert signals.loc[0, "decision_time_ms"] == 1712649600000
    assert signals.loc[0, "source_discovery_candidate_id"] == "source-candidate-1"
    assert result.manifest["candidate_pack_written"] is False
    assert result.manifest["promotion_ready"] is False
