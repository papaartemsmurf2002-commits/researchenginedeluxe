from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pandas as pd
import pytest

from tradingbotsuite.research_discovery.replay_overlay_preflight import (
    REPLAY_OVERLAY_CYCLE_PREFLIGHT_POLICY,
    REPLAY_OVERLAY_CYCLE_SPEC_DRAFT_POLICY,
    build_replay_overlay_cycle_spec_drafts,
    preflight_replay_overlay_cycle_specs,
    validate_replay_overlay_cycle_preflight_manifest,
    validate_replay_overlay_cycle_spec_draft_manifest,
    write_replay_overlay_cycle_preflight_artifacts,
    write_replay_overlay_cycle_spec_draft_artifacts,
)
from tradingbotsuite.research_discovery.state import DiscoveryTrialRecord, write_trial_record
from tradingbotsuite.research_cycle.spec import HistoricalResearchCycleSpec


def test_replay_overlay_preflight_builds_candidate_overlay_for_exact_representable_lead(tmp_path: Path) -> None:
    replay_spec_path, discovery_manifest_path = _write_replay_fixture(
        tmp_path,
        [
            _lead(
                "mat-exact",
                "trial-000001",
                label_horizon="4h",
                event_spacing_bars=8,
                min_neighbor_count=8,
                probability_threshold=0.60,
                expected_value_threshold=0.0,
                min_neighbor_agreement=0.60,
                min_distance_quality=0.05,
                vote_margin_threshold=0.05,
            )
        ],
    )

    result = preflight_replay_overlay_cycle_specs(
        replay_spec_path=replay_spec_path,
        replay_discovery_manifest_path=discovery_manifest_path,
    )
    artifact = write_replay_overlay_cycle_preflight_artifacts(tmp_path / "preflight", result)

    manifest = json.loads(artifact.manifest_path.read_text(encoding="utf-8"))
    rows = pd.read_parquet(artifact.rows_path)
    assert validate_replay_overlay_cycle_preflight_manifest(manifest) == []
    assert manifest["preflight_policy"] == REPLAY_OVERLAY_CYCLE_PREFLIGHT_POLICY
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["candidate_pack_written"] is False
    assert manifest["candidate_pack_paths"] == []
    assert manifest["representable_candidate_count"] == 1
    assert manifest["zero_representable_candidates_is_valid_evidence"] is False
    assert bool(rows.loc[0, "representable_by_current_historical_cycle_contract"]) is True
    assert rows.loc[0, "preflight_reasons"] == ""
    assert rows.loc[0, "generated_candidate_id"]
    overlay = json.loads(rows.loc[0, "candidate_scoped_overlay_json"])
    assert overlay["scope"] == "candidate"
    assert overlay["candidate_cache_key"] == rows.loc[0, "generated_candidate_id"]
    assert overlay["materialized_candidate_id"] == "mat-exact"
    with pytest.raises(ValueError, match="refusing to overwrite"):
        write_replay_overlay_cycle_preflight_artifacts(tmp_path / "preflight", result)


def test_replay_overlay_spec_draft_writer_emits_singleton_1h_candidate_cache_key_specs(tmp_path: Path) -> None:
    replay_spec_path, discovery_manifest_path = _write_replay_fixture(
        tmp_path,
        [
            _lead(
                "mat-1h-exact",
                "trial-000001",
                label_horizon="1h",
                event_spacing_bars=6,
                min_neighbor_count=None,
                probability_threshold=0.60,
                expected_value_threshold=0.0,
                min_neighbor_agreement=None,
                min_distance_quality=None,
                vote_margin_threshold=None,
            )
        ],
    )
    base_cycle_spec_path = _write_base_cycle_spec(tmp_path)

    preflight = preflight_replay_overlay_cycle_specs(
        replay_spec_path=replay_spec_path,
        replay_discovery_manifest_path=discovery_manifest_path,
        target_feature_set_id="features_full_context_no_wt",
        strategy_id="hmm_knn_diagnostic_v1",
    )
    draft = build_replay_overlay_cycle_spec_drafts(
        preflight,
        base_cycle_spec_path=base_cycle_spec_path,
        cycle_output_root=tmp_path / "cycle_outputs",
    )
    artifact = write_replay_overlay_cycle_spec_draft_artifacts(tmp_path / "spec_drafts", draft)

    manifest = json.loads(artifact.manifest_path.read_text(encoding="utf-8"))
    rows = pd.read_parquet(artifact.rows_path)
    spec_payload = json.loads(artifact.spec_paths[0].read_text(encoding="utf-8"))
    parsed_spec = HistoricalResearchCycleSpec.from_path(artifact.spec_paths[0])
    overlay = spec_payload["features"]["materialized_prediction_overlays"][0]
    search_space = spec_payload["optimizer"]["search_spaces"][0]

    assert validate_replay_overlay_cycle_spec_draft_manifest(manifest) == []
    assert manifest["spec_draft_policy"] == REPLAY_OVERLAY_CYCLE_SPEC_DRAFT_POLICY
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["candidate_pack_written"] is False
    assert manifest["overlay_cycle_spec_draft_count"] == 1
    assert manifest["overlay_cycle_specs_emitted"] == [str(artifact.spec_paths[0])]
    assert preflight.manifest["overlay_cycle_specs_emitted"] == []
    assert bool(preflight.rows.loc[0, "representable_by_current_historical_cycle_contract"]) is True
    assert rows.loc[0, "spec_generation_status"] == "drafted"
    assert rows.loc[0, "overlay_cycle_spec_path"] == str(artifact.spec_paths[0])
    assert spec_payload["research_only"] is True
    assert spec_payload["observe_only"] is True
    assert spec_payload["promotion_ready"] is False
    assert spec_payload["candidate_pack_written"] is False
    assert spec_payload["candidate_pack_eligible"] is False
    assert spec_payload["holding_windows"] == ["1h"]
    assert parsed_spec.holding_windows == ("1h",)
    assert search_space["holding_window"] == "1h"
    assert search_space["parameters"] == {
        "expected_value_threshold": [0.0],
        "probability_threshold": [0.6],
        "spacing_bars": [6],
    }
    assert overlay["scope"] == "candidate"
    assert "candidate_id" not in overlay
    assert overlay["candidate_cache_key"] == rows.loc[0, "generated_candidate_id"]
    assert overlay["materialized_candidate_id"] == "mat-1h-exact"


def test_replay_overlay_preflight_rejects_out_of_domain_unrepresentable_lead(tmp_path: Path) -> None:
    replay_spec_path, discovery_manifest_path = _write_replay_fixture(
        tmp_path,
        [
            _lead(
                "mat-blocked",
                "trial-000001",
                label_horizon="1h",
                event_spacing_bars=3,
                min_neighbor_count=6,
                probability_threshold=0.63,
                expected_value_threshold=-0.0003,
                min_neighbor_agreement=0.49,
                min_distance_quality=0.004,
                vote_margin_threshold=0.025,
            )
        ],
    )

    result = preflight_replay_overlay_cycle_specs(
        replay_spec_path=replay_spec_path,
        replay_discovery_manifest_path=discovery_manifest_path,
    )

    row = result.rows.loc[0]
    reasons = set(str(row["preflight_reasons"]).split("|"))
    assert result.manifest["representable_candidate_count"] == 0
    assert result.manifest["unrepresentable_candidate_count"] == 1
    assert result.manifest["zero_representable_candidates_is_valid_evidence"] is True
    assert result.manifest["overlay_cycle_specs_emitted"] == []
    assert result.manifest["candidate_pack_written"] is False
    assert bool(row["representable_by_current_historical_cycle_contract"]) is False
    assert row["generated_candidate_id"] is None
    assert row["candidate_scoped_overlay_json"] == ""
    assert "parameter_value_outside_historical_strategy_domain:spacing_bars=3" in reasons
    assert "parameter_value_outside_historical_strategy_domain:min_neighbor_count=6" in reasons
    assert "parameter_value_outside_historical_strategy_domain:probability_threshold=0.63" in reasons
    assert "parameter_value_outside_historical_strategy_domain:expected_value_threshold=-0.0003" in reasons
    assert "parameter_value_outside_historical_strategy_domain:min_neighbor_agreement=0.49" in reasons
    assert "parameter_value_outside_historical_strategy_domain:min_neighbor_distance_quality=0.004" in reasons
    assert "parameter_value_outside_historical_strategy_domain:min_vote_margin=0.025" in reasons


def test_replay_overlay_spec_draft_writer_skips_unrepresentable_rows(tmp_path: Path) -> None:
    replay_spec_path, discovery_manifest_path = _write_replay_fixture(
        tmp_path,
        [
            _lead(
                "mat-blocked",
                "trial-000001",
                label_horizon="1h",
                event_spacing_bars=3,
                min_neighbor_count=6,
                probability_threshold=0.63,
                expected_value_threshold=-0.0003,
                min_neighbor_agreement=0.49,
                min_distance_quality=0.004,
                vote_margin_threshold=0.025,
            )
        ],
    )
    preflight = preflight_replay_overlay_cycle_specs(
        replay_spec_path=replay_spec_path,
        replay_discovery_manifest_path=discovery_manifest_path,
    )
    draft = build_replay_overlay_cycle_spec_drafts(
        preflight,
        base_cycle_spec_path=_write_base_cycle_spec(tmp_path),
        cycle_output_root=tmp_path / "cycle_outputs",
    )
    artifact = write_replay_overlay_cycle_spec_draft_artifacts(tmp_path / "blocked_spec_drafts", draft)

    manifest = json.loads(artifact.manifest_path.read_text(encoding="utf-8"))
    rows = pd.read_parquet(artifact.rows_path)
    reasons = set(str(rows.loc[0, "spec_generation_reasons"]).split("|"))

    assert validate_replay_overlay_cycle_spec_draft_manifest(manifest) == []
    assert artifact.spec_paths == ()
    assert manifest["overlay_cycle_spec_draft_count"] == 0
    assert manifest["overlay_cycle_specs_emitted"] == []
    assert rows.loc[0, "spec_generation_status"] == "blocked"
    assert "preflight_row_not_representable" in reasons
    assert "candidate_cache_key_required" in reasons
    assert "candidate_scoped_overlay_required" in reasons


def test_replay_overlay_preflight_requires_prediction_manifest_and_sha_match(tmp_path: Path) -> None:
    replay_spec_path, discovery_manifest_path = _write_replay_fixture(
        tmp_path,
        [
            _lead(
                "mat-bad-sha",
                "trial-000001",
                label_horizon="4h",
                event_spacing_bars=8,
                min_neighbor_count=8,
            )
        ],
        manifest_prediction_sha="wrong",
    )

    result = preflight_replay_overlay_cycle_specs(
        replay_spec_path=replay_spec_path,
        replay_discovery_manifest_path=discovery_manifest_path,
    )

    assert result.manifest["representable_candidate_count"] == 0
    assert "materialized_prediction_overlay_manifest_predictions_sha_mismatch" in result.rows.loc[0, "preflight_reasons"]


def test_replay_overlay_preflight_rejects_missing_prediction_and_unsafe_manifest(tmp_path: Path) -> None:
    replay_spec_path, discovery_manifest_path = _write_replay_fixture(
        tmp_path,
        [
            _lead(
                "mat-unsafe",
                "trial-000001",
                label_horizon="4h",
                event_spacing_bars=8,
                min_neighbor_count=8,
            )
        ],
        omit_prediction=True,
        manifest_updates={"promotion_ready": True, "split_safety_passed": False},
    )

    result = preflight_replay_overlay_cycle_specs(
        replay_spec_path=replay_spec_path,
        replay_discovery_manifest_path=discovery_manifest_path,
    )

    reasons = set(str(result.rows.loc[0, "preflight_reasons"]).split("|"))
    assert result.manifest["representable_candidate_count"] == 0
    assert "materialized_prediction_overlay_missing_predictions" in reasons
    assert "materialized_prediction_overlay_manifest_promotion_ready" in reasons
    assert "materialized_prediction_overlay_manifest_split_safety_failed" in reasons


def test_replay_overlay_preflight_manifest_validation_rejects_live_adjacent_flags(tmp_path: Path) -> None:
    replay_spec_path, discovery_manifest_path = _write_replay_fixture(
        tmp_path,
        [_lead("mat-exact", "trial-000001", label_horizon="4h", event_spacing_bars=8, min_neighbor_count=8)],
    )
    result = preflight_replay_overlay_cycle_specs(
        replay_spec_path=replay_spec_path,
        replay_discovery_manifest_path=discovery_manifest_path,
    )

    manifest = dict(result.manifest)
    manifest["promotion_ready"] = True
    manifest["candidate_pack_written"] = True
    manifest["overlay_cycle_specs_emitted"] = ["cycle.json"]

    reasons = validate_replay_overlay_cycle_preflight_manifest(manifest)
    assert "promotion_ready_must_be_false" in reasons
    assert "candidate_pack_written_must_be_false" in reasons
    assert "overlay_cycle_specs_emitted_must_be_empty" in reasons


def _write_replay_fixture(
    tmp_path: Path,
    lead_payloads: list[dict[str, object]],
    *,
    omit_prediction: bool = False,
    manifest_prediction_sha: str | None = None,
    manifest_updates: dict[str, object] | None = None,
) -> tuple[Path, Path]:
    replay_spec_path = tmp_path / "replay_spec" / "discovery_replay_spec.json"
    replay_spec_path.parent.mkdir(parents=True, exist_ok=True)
    replay_spec_path.write_text(
        json.dumps(
            {
                "spec_version": "discovery-lead-replay-spec-v1",
                "run_id": "test-replay",
                "symbol": "BTCUSDT",
                "timeframe": "15m",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    discovery_dir = tmp_path / "discovery_run"
    trials_dir = discovery_dir / "trials"
    ledgers_dir = discovery_dir / "candidate_ledgers"
    ledgers_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for index, lead in enumerate(lead_payloads, start=1):
        trial_id = str(lead["trial_id"])
        artifact_dir = discovery_dir / "trial_artifacts" / trial_id / "attempt-001" / "knn"
        prediction_path = artifact_dir / "knn_predictions.parquet"
        manifest_path = artifact_dir / "knn_study_manifest.json"
        prediction_sha = ""
        if not omit_prediction:
            _write_prediction_frame(prediction_path)
            prediction_sha = _file_sha256(prediction_path)
        manifest = {
            "knn_study_manifest_version": "discovery-knn-study-manifest-v1",
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "split_safety_passed": True,
            "knn_predictions_sha256": manifest_prediction_sha if manifest_prediction_sha is not None else prediction_sha,
            "required_outputs": {"knn_predictions": str(prediction_path)},
            "spec": {
                "label_horizon": lead["label_horizon"],
                "probability_threshold": lead["probability_threshold"],
            },
        }
        manifest.update(manifest_updates or {})
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        payload = {
            **lead,
            "trial_kind": "regime_knn_entry_discovery",
            "registered_feature_set_id": "features_price_trend_vol_wt3d",
            "feature_column_set_id": "compact_wt3d_base",
            "source_trial_id": trial_id,
            "source_discovery_candidate_id": f"source-{lead['materialized_candidate_id']}",
            "source_record_sha256": f"source-sha-{index}",
            "source_prediction_signature_hash": f"prediction-sha-{index}",
            "source_entry_event_signature_hash": f"entry-sha-{index}",
            "knn_predictions_path": str(prediction_path),
            "knn_manifest_path": str(manifest_path),
        }
        record = DiscoveryTrialRecord(
            run_id="test-replay-run",
            trial_id=trial_id,
            attempt_id="attempt-001",
            trial_index=index,
            candidate_id=str(lead["materialized_candidate_id"]),
            candidate_family="regime_knn_entry_discovery",
            ledger_kind="interesting",
            score=float(lead.get("final_score", 0.1)),
            payload=payload,
        )
        write_trial_record(trials_dir / f"{trial_id}.json", record)
        stored = json.loads((trials_dir / f"{trial_id}.json").read_text(encoding="utf-8"))
        rows.append(
            {
                "trial_id": trial_id,
                "candidate_id": str(lead["materialized_candidate_id"]),
                "candidate_family": "regime_knn_entry_discovery",
                "ledger_kind": "interesting",
                "score": float(lead.get("final_score", 0.1)),
                "record_sha256": stored["record_sha256"],
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                **lead,
            }
        )
    interesting_path = ledgers_dir / "interesting_candidates.parquet"
    pd.DataFrame(rows).to_parquet(interesting_path, index=False)
    discovery_manifest_path = discovery_dir / "discovery_run_manifest.json"
    discovery_manifest_path.write_text(
        json.dumps(
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
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return replay_spec_path, discovery_manifest_path


def _lead(
    materialized_candidate_id: str,
    trial_id: str,
    *,
    label_horizon: str,
    event_spacing_bars: int,
    min_neighbor_count: int | None,
    probability_threshold: float = 0.60,
    expected_value_threshold: float = 0.0,
    min_neighbor_agreement: float | None = 0.60,
    min_distance_quality: float | None = 0.05,
    vote_margin_threshold: float | None = 0.05,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "materialized_candidate_id": materialized_candidate_id,
        "trial_id": trial_id,
        "label_horizon": label_horizon,
        "event_spacing_bars": event_spacing_bars,
        "probability_threshold": probability_threshold,
        "expected_value_threshold": expected_value_threshold,
        "final_score": 0.25,
    }
    optional_values = {
        "min_neighbor_count": min_neighbor_count,
        "min_neighbor_agreement": min_neighbor_agreement,
        "min_distance_quality": min_distance_quality,
        "vote_margin_threshold": vote_margin_threshold,
    }
    payload.update({key: value for key, value in optional_values.items() if value is not None})
    return payload


def _write_base_cycle_spec(tmp_path: Path) -> Path:
    spec_path = tmp_path / "base_cycle" / "cycle.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        json.dumps(
            {
                "spec_version": "historical-research-cycle-spec-v1",
                "cycle_id": "base-replay-overlay-cycle",
                "symbol": "BTCUSDT",
                "output_dir": str(tmp_path / "cycle_outputs" / "base-replay-overlay-cycle"),
                "holding_windows": ["1h"],
                "data": {
                    "synthetic_fixture": True,
                    "synthetic_row_count": 120,
                    "synthetic_variant": "balanced",
                },
                "features": {"feature_sets": ["features_full_context_no_wt"]},
                "strategies": ["hmm_knn_diagnostic_v1"],
                "validation": {
                    "purge_embargo_bars": 2,
                    "min_splits": 2,
                    "trade_count_floor": 1,
                },
                "optimizer": {
                    "method_sequence": ["grid"],
                    "max_candidates_per_strategy": 1,
                    "top_regions_to_refine": 1,
                },
                "compute": {"cpu_threads": 1, "gpu_acceleration": "disabled"},
                "backtest_backend": "reference",
                "operator_job_id": "operator-wrapped-base-cycle",
                "operator_original_spec_path": str(tmp_path / "original_cycle_spec.json"),
                "operator_overwrite_protection": True,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return spec_path


def _write_prediction_frame(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "source_row_index": 0,
                "p_up_barrier": 0.6,
                "p_down_barrier": 0.4,
                "expected_net_return_after_costs": 0.001,
                "neighbor_agreement": 0.6,
                "neighbor_distance_quality": 0.1,
                "neighbor_count": 8,
                "neighbor_min_source_index": 0,
                "neighbor_max_source_index": 0,
                "knn_vote_margin": 0.1,
                "accepted_by_knn": True,
                "knn_skip_reason": "",
            }
        ]
    ).to_parquet(path, index=False)


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
