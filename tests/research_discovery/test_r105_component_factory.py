from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from tradingbotsuite.research_discovery.artifact_keys import effective_trial_key
from tradingbotsuite.research_discovery.r105_component_factory import (
    build_r105_latest_sweep_postmortem,
    write_r105_latest_sweep_postmortem_artifacts,
)


def test_r105_postmortem_collapses_no_regime_noop_dimensions(tmp_path: Path) -> None:
    run_dir = _write_tiny_discovery_run(tmp_path)

    result = build_r105_latest_sweep_postmortem(run_dir)

    assert result.manifest["research_only"] is True
    assert result.manifest["observe_only"] is True
    assert result.manifest["promotion_ready"] is False
    assert result.manifest["candidate_pack_written"] is False
    assert result.manifest["order_placement_used"] is False
    assert result.manifest["summary"]["scheduled_trial_count"] == 4
    assert result.manifest["summary"]["effective_trial_count"] == 1
    assert "hmm_state_count" in result.manifest["summary"]["inactive_dimensions_dropped_under_no_regime"]
    assert "hmm_posterior_threshold" in result.manifest["summary"]["inactive_dimensions_dropped_under_no_regime"]
    assert set(result.effective_trial_summary["scheduled_trial_count"]) == {4}
    assert result.effective_trial_summary["prediction_cluster_count"].iloc[0] == 1
    assert result.effective_trial_summary["entry_cluster_count"].iloc[0] == 1
    helper_record = {
        "candidate_family": "regime_knn_entry_discovery",
        "feature_column_set_id": "price_trend_vol",
        "regime_mode": "none",
        "label_horizon": "1h",
        "distance_metric": "euclidean",
        "k": 3,
        "min_neighbor_count": 2,
        "probability_threshold": 0.55,
        "expected_value_threshold": 0.0,
        "min_neighbor_agreement": 0.55,
        "min_distance_quality": 0.0,
        "vote_margin_threshold": 0.0,
    }
    assert result.effective_trial_summary["effective_trial_key"].iloc[0] == effective_trial_key(helper_record)
    assert result.prediction_hash_clusters["row_count"].iloc[0] == 4
    assert "ledger-summary prediction" in result.markdown_report


def test_r105_postmortem_writes_required_artifacts(tmp_path: Path) -> None:
    run_dir = _write_tiny_discovery_run(tmp_path)
    result = build_r105_latest_sweep_postmortem(run_dir)

    artifacts = write_r105_latest_sweep_postmortem_artifacts(tmp_path / "out", result)
    manifest = json.loads(artifacts.manifest_path.read_text(encoding="utf-8"))
    effective = pd.read_parquet(artifacts.effective_trial_summary_path)
    predictions = pd.read_parquet(artifacts.prediction_hash_clusters_path)
    top_blocked = pd.read_parquet(artifacts.top_blocked_by_cluster_path)

    assert artifacts.manifest_path.exists()
    assert artifacts.markdown_report_path.exists()
    assert manifest["required_outputs"]["effective_trial_summary"] == str(artifacts.effective_trial_summary_path)
    assert manifest["output_sha256s"]["prediction_hash_clusters"]
    assert manifest["hash_scope"]["prediction_hash"] == "ledger_summary_no_per_bar_prediction_artifacts"
    assert manifest["issue_status"]["ISSUE-R104-001"] == "open_not_closed_by_this_postmortem"
    assert effective["effective_trial_key"].nunique() == 1
    assert predictions["prediction_hash"].nunique() == 1
    assert top_blocked["rows"].sum() == 4


def _write_tiny_discovery_run(tmp_path: Path) -> Path:
    run_dir = tmp_path / "run"
    ledger_dir = run_dir / "candidate_ledgers"
    ledger_dir.mkdir(parents=True)
    spec_path = run_dir / "discovery_spec_resolved.json"
    manifest_path = run_dir / "discovery_run_manifest.json"
    blocked_path = ledger_dir / "blocked_candidates.parquet"
    spec_payload = {
        "run_id": "tiny_r105_postmortem",
        "symbol": "BTCUSDT",
        "timeframe": "15m",
        "discovery_mode": "deep_candidate_harvest",
        "research_output_dir": str(tmp_path),
        "output_dir": str(run_dir),
        "feature_column_set_ids": ["price_trend_vol"],
        "search": {
            "hmm_state_counts": [3, 4],
            "hmm_posterior_thresholds": [0.55, 0.65],
            "hmm_entropy_thresholds": [0.78],
            "label_horizons": ["1h"],
            "k_values": [3],
            "min_neighbor_counts": [2],
            "distance_metrics": ["euclidean"],
            "probability_thresholds": [0.55],
            "expected_value_thresholds": [0.0],
            "min_neighbor_agreements": [0.55],
            "min_distance_qualities": [0.0],
            "vote_margin_thresholds": [0.0],
            "same_regime_only_values": [False],
            "regime_modes": ["none"],
            "min_splits": 1,
            "purge_embargo_bars": 0,
            "min_trade_count": 1,
            "min_signal_rate": 0.0,
            "max_signal_rate": 0.5,
            "min_realized_expectancy": -0.001,
        },
        "execution": {"max_workers": 1, "persist_trial_artifacts": "interesting_only"},
        "budget": {"max_trials": 4, "trial_batch_size": 4, "snapshot_interval_minutes": 30, "rng_seed": 17},
    }
    spec_path.write_text(json.dumps(spec_payload, indent=2, sort_keys=True), encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "discovery_run_manifest_version": "discovery-run-manifest-v1",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "run_id": "tiny_r105_postmortem",
                "symbol": "BTCUSDT",
                "timeframe": "15m",
                "search_space": {
                    "planned_trials": 4,
                    "total_combinations": 4,
                    "sampled_fraction": 1.0,
                    "exhaustive": True,
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    pd.DataFrame(
        [
            {
                "run_id": "tiny_r105_postmortem",
                "trial_id": f"trial-{index:06d}",
                "candidate_id": f"candidate-{index}",
                "candidate_family": "regime_knn_entry_discovery",
                "ledger_kind": "blocked",
                "score": 0.01 * index,
                "blocker_code": "independent_event_count_below_floor",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "feature_column_set_id": "price_trend_vol",
                "hmm_state_count": 3 if index <= 2 else 4,
                "regime_mode": "none",
                "regime_detector_type": "none",
                "regime_gate_enabled": False,
                "same_regime_neighbor_pool_enabled": False,
                "true_hmm_backend_used": False,
                "label_horizon": "1h",
                "distance_metric": "euclidean",
                "k": 3,
                "min_neighbor_count": 2,
                "trade_count": 1,
                "accepted_bar_count": 2,
                "independent_event_count": 1,
                "suppressed_overlap_count": 1,
                "overlap_ratio": 0.5,
                "event_signal_rate": 0.25,
                "side_collapse_ratio": 0.5,
                "long_independent_event_count": 1,
                "short_independent_event_count": 0,
                "event_spacing_bars": 4,
                "signal_rate": 0.25,
                "realized_expectancy": 0.001,
                "independent_event_expectancy": 0.001,
                "accepted_prediction_count": 2,
                "evaluated_prediction_count": 8,
                "final_score": 0.01 * index,
                "record_sha256": f"record-{index}",
            }
            for index in range(1, 5)
        ]
    ).to_parquet(blocked_path, index=False)
    return run_dir
