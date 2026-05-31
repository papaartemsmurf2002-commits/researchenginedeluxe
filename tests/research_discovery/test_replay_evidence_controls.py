from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from tradingbotsuite.research_discovery.replay_evidence_controls import (
    WPR10647_REPLAY_EVIDENCE_MANIFEST_VERSION,
    WPR10647_REPLAY_EVIDENCE_POLICY,
    WPR10647SymbolEvidenceInput,
    build_wpr10647_replay_evidence,
    validate_wpr10647_replay_evidence_manifest,
    write_wpr10647_replay_evidence_artifacts,
)


def test_wpr10647_replay_evidence_writes_separated_exit_window_and_control_artifacts(tmp_path: Path) -> None:
    symbol_input = _write_symbol_input(tmp_path)

    result = build_wpr10647_replay_evidence(symbol_inputs=[symbol_input])
    artifact = write_wpr10647_replay_evidence_artifacts(output_dir=tmp_path / "wpr10647", result=result)

    manifest = json.loads(artifact.manifest_path.read_text(encoding="utf-8"))
    exit_rows = pd.read_parquet(artifact.exit_lab_rows_path)
    window_rows = pd.read_parquet(artifact.window_rows_path)
    control_rows = pd.read_parquet(artifact.negative_control_rows_path)

    assert validate_wpr10647_replay_evidence_manifest(manifest) == []
    assert manifest["wpr10647_replay_evidence_manifest_version"] == WPR10647_REPLAY_EVIDENCE_MANIFEST_VERSION
    assert manifest["wpr10647_replay_evidence_policy"] == WPR10647_REPLAY_EVIDENCE_POLICY
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["candidate_pack_written"] is False
    assert manifest["candidate_pack_paths"] == []
    assert manifest["full_replay_lead_count"] == 2
    assert manifest["full_replay_exit_lab_status_counts"] == {"blocked": 1, "passed": 1}
    assert manifest["window_scope_status_counts"] == {"available": 1, "blocked": 1}
    assert manifest["negative_control_row_count"] == 8
    assert manifest["negative_control_status_counts"] == {"blocked": 8}
    assert set(exit_rows["evidence_scope"]) == {"full_48_exact_replay_exit_lab"}
    assert set(window_rows["evidence_scope"]) == {"full_window_replay_overlay", "modern_window_replay_overlay"}
    assert set(control_rows["control_kind"]) == {
        "shuffled_labels",
        "shifted_context",
        "no_knn_baseline",
        "no_regime_baseline",
    }
    assert set(control_rows["control_only"]) == {True}
    assert set(control_rows["candidate_pack_eligible"]) == {False}
    assert set(control_rows["promotion_ready"]) == {False}


def test_wpr10647_manifest_validator_rejects_live_adjacent_flags(tmp_path: Path) -> None:
    symbol_input = _write_symbol_input(tmp_path)
    result = build_wpr10647_replay_evidence(symbol_inputs=[symbol_input])

    manifest = dict(result.manifest)
    manifest["promotion_ready"] = True
    manifest["candidate_pack_written"] = True
    manifest["live_fetch_used"] = True
    manifest["required_outputs"] = {
        "wpr10647_replay_evidence_manifest": "manifest.json",
        "full_replay_exit_lab_rows": "exit.parquet",
        "window_comparison_rows": "window.parquet",
        "negative_control_rows": "controls.parquet",
    }

    reasons = validate_wpr10647_replay_evidence_manifest(manifest)
    assert "promotion_ready_must_be_false" in reasons
    assert "candidate_pack_written_must_be_false" in reasons
    assert "live_fetch_used_must_be_false" in reasons


def _write_symbol_input(tmp_path: Path) -> WPR10647SymbolEvidenceInput:
    preflight_dir = tmp_path / "preflight"
    preflight_dir.mkdir(parents=True)
    preflight_rows_path = preflight_dir / "replay_overlay_cycle_preflight_rows.parquet"
    preflight_manifest_path = preflight_dir / "replay_overlay_cycle_preflight_manifest.json"
    preflight = pd.DataFrame(
        [
            {
                "symbol": "BTCUSDT",
                "materialized_candidate_id": "mat-a",
                "generated_candidate_id": "cache-a",
                "source_trial_id": "trial-a",
                "source_discovery_candidate_id": "source-a",
                "source_record_sha256": "record-a",
                "representable_by_current_historical_cycle_contract": True,
            },
            {
                "symbol": "BTCUSDT",
                "materialized_candidate_id": "mat-b",
                "generated_candidate_id": "cache-b",
                "source_trial_id": "trial-b",
                "source_discovery_candidate_id": "source-b",
                "source_record_sha256": "record-b",
                "representable_by_current_historical_cycle_contract": True,
            },
        ]
    )
    preflight.to_parquet(preflight_rows_path, index=False)
    preflight_manifest_path.write_text(
        json.dumps(
            {
                "replay_overlay_cycle_preflight_manifest_version": "replay-overlay-cycle-spec-preflight-v1",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "source_trial_count": 2,
                "representable_candidate_count": 2,
                "candidate_pack_written": False,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    spec_dir = tmp_path / "spec_drafts"
    spec_dir.mkdir()
    spec_rows_path = spec_dir / "replay_overlay_cycle_spec_draft_rows.parquet"
    spec_manifest_path = spec_dir / "replay_overlay_cycle_spec_draft_manifest.json"
    pd.DataFrame(
        [
            {"materialized_candidate_id": "mat-a", "spec_generation_status": "drafted"},
            {"materialized_candidate_id": "mat-b", "spec_generation_status": "drafted"},
        ]
    ).to_parquet(spec_rows_path, index=False)
    spec_manifest_path.write_text(
        json.dumps(
            {
                "replay_overlay_cycle_spec_draft_manifest_version": "replay-overlay-cycle-spec-draft-v1",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "candidate_pack_written": False,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    exit_dir = tmp_path / "exit_lab"
    exit_dir.mkdir()
    gates_path = exit_dir / "frozen_entry_exit_lab_candidate_gates.parquet"
    exit_manifest_path = exit_dir / "discovery_exit_lab_manifest.json"
    pd.DataFrame(
        [
            {
                "entry_candidate_id": "mat-a",
                "candidate_id": "mat-a",
                "exit_lab_status": "complete",
                "exit_lab_gate_status": "passed",
                "exit_lab_reasons": "",
                "exit_lab_best_family": "trailing_risk",
                "fixed_holding_score_delta": 0.1,
            },
            {
                "entry_candidate_id": "mat-b",
                "candidate_id": "mat-b",
                "exit_lab_status": "complete",
                "exit_lab_gate_status": "blocked",
                "exit_lab_reasons": "exit_lab_no_improving_exit_over_fixed_holding",
                "exit_lab_best_family": "",
                "fixed_holding_score_delta": -0.1,
            },
        ]
    ).to_parquet(gates_path, index=False)
    exit_manifest_path.write_text(
        json.dumps(
            {
                "exit_lab_manifest_version": "discovery-exit-lab-manifest-v1",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "required_outputs": {"discovery_exit_lab_candidate_gates": str(gates_path)},
                "candidate_pack_written": False,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return WPR10647SymbolEvidenceInput(
        symbol="BTCUSDT",
        preflight_manifest_path=preflight_manifest_path,
        preflight_rows_path=preflight_rows_path,
        spec_draft_manifest_path=spec_manifest_path,
        spec_draft_rows_path=spec_rows_path,
        exit_lab_manifest_path=exit_manifest_path,
    )
