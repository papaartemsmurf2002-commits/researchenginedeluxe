from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from tradingbotsuite.research_discovery.discovery_lead_materialization import (
    DISCOVERY_LEAD_MATERIALIZATION_MANIFEST_VERSION,
    DiscoveryLeadMaterializationSpec,
    materialize_discovery_leads_from_manifest,
    validate_discovery_lead_materialization_manifest,
    write_discovery_lead_materialization_artifacts,
)
from tradingbotsuite.research_discovery.state import DiscoveryTrialRecord, write_trial_record


def test_materialization_selects_bounded_signature_diverse_descriptors(tmp_path: Path) -> None:
    manifest_path = _write_discovery_fixture(
        tmp_path,
        [
            _lead("candidate-a", "trial-000001", final_score=0.91, event_spacing_bars=4),
            _lead("candidate-a-duplicate-same-entry", "trial-000002", final_score=0.90, event_spacing_bars=4),
            _lead("candidate-b", "trial-000003", final_score=0.80, event_spacing_bars=8),
        ],
    )
    spec = DiscoveryLeadMaterializationSpec(max_candidates=2, max_per_entry_signature=1)

    result = materialize_discovery_leads_from_manifest(manifest_path, spec=spec)
    rerun = materialize_discovery_leads_from_manifest(manifest_path, spec=spec)

    assert result.manifest["discovery_lead_materialization_manifest_version"] == DISCOVERY_LEAD_MATERIALIZATION_MANIFEST_VERSION
    assert result.manifest["research_only"] is True
    assert result.manifest["observe_only"] is True
    assert result.manifest["promotion_ready"] is False
    assert result.manifest["candidate_pack_written"] is False
    assert result.manifest["candidate_pack_paths"] == []
    assert result.manifest["summary"] == {
        "materialized_candidate_count": 2,
        "descriptor_only_count": 2,
        "candidate_pack_written": False,
        "candidate_pack_eligible_count": 0,
        "promotion_ready": False,
        "skipped_by_entry_signature_cap": 1,
        "skipped_by_materialization_budget": 0,
        "required_downstream_gate_count": 9,
        "status": "descriptor_only_not_backtested",
    }
    assert result.materialized_leads["source_discovery_candidate_id"].tolist() == ["candidate-a", "candidate-b"]
    assert result.materialized_leads["materialized_candidate_id"].tolist() == rerun.materialized_leads[
        "materialized_candidate_id"
    ].tolist()
    assert result.materialized_leads["materialized_candidate_id"].str.startswith("mat-").all()
    assert result.materialized_leads["candidate_pack_eligible"].eq(False).all()
    assert result.materialized_leads["promotion_ready"].eq(False).all()
    assert result.materialized_leads["missing_evidence"].str.contains("cycle_backtest_required").all()
    assert result.materialized_leads["entry_event_signature_hash"].nunique() == 2
    assert result.candidate_specs[0]["claim_scope"] == "descriptor_only_not_backtested_not_ranked_not_candidate_pack_evidence"
    assert result.candidate_specs[0]["required_downstream_gates"][0] == "cycle_backtest_required"


def test_materialization_writes_valid_artifacts_and_refuses_overwrite(tmp_path: Path) -> None:
    manifest_path = _write_discovery_fixture(tmp_path, [_lead("candidate-a", "trial-000001")])
    result = materialize_discovery_leads_from_manifest(
        manifest_path,
        spec=DiscoveryLeadMaterializationSpec(max_candidates=1),
    )

    artifact = write_discovery_lead_materialization_artifacts(tmp_path / "materialized", result)

    manifest = json.loads(artifact.manifest_path.read_text(encoding="utf-8"))
    assert validate_discovery_lead_materialization_manifest(manifest) == []
    assert manifest["required_outputs"]["materialized_discovery_leads"] == str(artifact.materialized_leads_path)
    assert manifest["required_outputs"]["materialization_candidate_specs"] == str(artifact.candidate_specs_path)
    assert manifest["materialized_discovery_leads_sha256"]
    assert manifest["materialization_candidate_specs_sha256"]
    assert pd.read_parquet(artifact.materialized_leads_path).loc[0, "source_discovery_candidate_id"] == "candidate-a"
    specs = [json.loads(line) for line in artifact.candidate_specs_path.read_text(encoding="utf-8").splitlines()]
    assert specs[0]["materialized_candidate_id"] == result.materialized_leads.loc[0, "materialized_candidate_id"]
    with pytest.raises(ValueError, match="refusing to overwrite"):
        write_discovery_lead_materialization_artifacts(tmp_path / "materialized", result)


def test_materialization_rejects_trial_record_hash_mismatch(tmp_path: Path) -> None:
    manifest_path = _write_discovery_fixture(tmp_path, [_lead("candidate-a", "trial-000001")])
    ledger_path = tmp_path / "candidate_ledgers" / "interesting_candidates.parquet"
    ledger = pd.read_parquet(ledger_path)
    ledger.loc[0, "record_sha256"] = "wrong"
    ledger.to_parquet(ledger_path, index=False)

    with pytest.raises(ValueError, match="source discovery trial record hash mismatch"):
        materialize_discovery_leads_from_manifest(manifest_path)


def _write_discovery_fixture(tmp_path: Path, lead_payloads: list[dict[str, object]]) -> Path:
    ledgers_dir = tmp_path / "candidate_ledgers"
    trials_dir = tmp_path / "trials"
    ledgers_dir.mkdir(parents=True)
    trials_dir.mkdir(parents=True)
    rows: list[dict[str, object]] = []
    for index, payload in enumerate(lead_payloads):
        trial_id = str(payload["trial_id"])
        candidate_id = str(payload["candidate_id"])
        record = DiscoveryTrialRecord(
            run_id="test-discovery-run",
            trial_id=trial_id,
            attempt_id="attempt-001",
            trial_index=index,
            candidate_id=candidate_id,
            candidate_family="regime_knn_entry_discovery",
            ledger_kind="interesting",
            score=float(payload["final_score"]),
            payload=payload,
        )
        write_trial_record(trials_dir / f"{trial_id}.json", record)
        stored = json.loads((trials_dir / f"{trial_id}.json").read_text(encoding="utf-8"))
        rows.append(
            {
                "run_id": stored["run_id"],
                "trial_id": stored["trial_id"],
                "attempt_id": stored["attempt_id"],
                "trial_index": stored["trial_index"],
                "candidate_id": stored["candidate_id"],
                "candidate_family": stored["candidate_family"],
                "ledger_kind": stored["ledger_kind"],
                "score": stored["score"],
                "blocker_code": "",
                "filter_blocker_code": "",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                **stored["payload"],
                "record_sha256": stored["record_sha256"],
            }
        )
    interesting_path = ledgers_dir / "interesting_candidates.parquet"
    pd.DataFrame(rows).to_parquet(interesting_path, index=False)
    manifest_path = tmp_path / "discovery_run_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "discovery_run_manifest_version": "discovery-run-manifest-v1",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "symbol": "BTCUSDT",
                "timeframe": "15m",
                "run_id": "test-discovery-run",
                "required_outputs": {
                    "interesting_candidates": str(interesting_path),
                    "trials": str(trials_dir),
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return manifest_path


def _lead(candidate_id: str, trial_id: str, *, final_score: float = 0.75, event_spacing_bars: int = 4) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "trial_id": trial_id,
        "candidate_family": "regime_knn_entry_discovery",
        "feature_column_set_id": "compact_wt3d_base",
        "registered_feature_set_id": "features_price_trend_vol_wt3d",
        "regime_mode": "none",
        "regime_detector_type": "none",
        "label_horizon": "1h",
        "distance_metric": "euclidean",
        "k": 34,
        "min_neighbor_count": 2,
        "probability_threshold": 0.62,
        "expected_value_threshold": 0.0002,
        "min_neighbor_agreement": 0.6,
        "min_distance_quality": 0.0,
        "vote_margin_threshold": 0.02,
        "accepted_prediction_count": 100,
        "evaluated_prediction_count": 500,
        "accepted_bar_count": 80,
        "independent_event_count": 72,
        "long_independent_event_count": 40,
        "short_independent_event_count": 32,
        "suppressed_overlap_count": 8,
        "event_spacing_bars": event_spacing_bars,
        "overlap_ratio": 0.10,
        "side_collapse_ratio": 0.55,
        "signal_rate": 0.05,
        "realized_expectancy": 0.0001,
        "independent_event_expectancy": 0.00012,
        "discovery_screen_score_v2": final_score,
        "final_score": final_score,
        "trade_count": 72,
    }
