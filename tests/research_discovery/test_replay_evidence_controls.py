from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pandas as pd

from tradingbotsuite.research_discovery.replay_evidence_controls import (
    WPR10647_REPLAY_EVIDENCE_MANIFEST_VERSION,
    WPR10647_REPLAY_EVIDENCE_POLICY,
    WPR10648_NEGATIVE_CONTROL_MANIFEST_VERSION,
    WPR10647SymbolEvidenceInput,
    WPR10648NegativeControlInput,
    build_wpr10647_replay_evidence,
    build_wpr10648_negative_control_artifacts,
    validate_wpr10647_replay_evidence_manifest,
    validate_wpr10648_negative_control_manifest,
    write_wpr10647_replay_evidence_artifacts,
    write_wpr10648_negative_control_artifacts,
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


def test_wpr10648_negative_control_artifacts_are_control_only_not_candidate_evidence(tmp_path: Path) -> None:
    source = _write_control_source(tmp_path, include_label=True, include_timestamp=True)
    replay_profile = _write_json(tmp_path / "modern_window_profile.json", {"research_only": True})
    validation_manifest = _write_json(tmp_path / "validation_manifest.json", {"research_only": True})
    modern_profile = _write_json(tmp_path / "modern_profile.json", {"research_only": True})

    result = build_wpr10648_negative_control_artifacts(
        symbol_inputs=[
            WPR10648NegativeControlInput(
                symbol="BTCUSDT",
                source_manifest_path=source["manifest"],
                source_rows_path=source["rows"],
                replay_profile_path=replay_profile,
                validation_manifest_path=validation_manifest,
                modern_window_profile_path=modern_profile,
                require_modern_window_evidence=True,
                deterministic_seed=7,
                shift_size=1,
            )
        ]
    )
    artifact = write_wpr10648_negative_control_artifacts(output_dir=tmp_path / "wpr10648-controls", result=result)

    manifest = json.loads(artifact.manifest_path.read_text(encoding="utf-8"))
    rows = pd.read_parquet(artifact.control_rows_path)

    assert validate_wpr10648_negative_control_manifest(manifest) == []
    assert manifest["wpr10648_negative_control_manifest_version"] == WPR10648_NEGATIVE_CONTROL_MANIFEST_VERSION
    assert manifest["artifact_family"] == "negative_control"
    assert manifest["control_only"] is True
    assert manifest["candidate_evidence"] is False
    assert manifest["candidate_pack_eligible"] is False
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["control_status_counts"] == {"available": 8}
    assert set(rows["control_family"]) == {
        "shuffled_labels",
        "shifted_context",
        "no_knn_overlay",
        "no_regime_backend",
    }
    assert rows["control_only"].eq(True).all()
    assert rows["candidate_evidence"].eq(False).all()
    assert rows["candidate_pack_eligible"].eq(False).all()
    assert rows["candidate_pack_written"].eq(False).all()
    shuffled = rows.loc[rows["control_family"].eq("shuffled_labels")]
    assert shuffled["source_label_hash"].str.len().gt(0).all()
    assert shuffled["shuffled_label_hash"].str.len().gt(0).all()
    assert shuffled["label_distribution_match"].eq(True).all()
    assert shuffled["derangement_rate"].gt(0).all()
    no_knn = rows.loc[rows["control_family"].eq("no_knn_overlay")]
    assert no_knn["overlay_used"].eq(False).all()
    assert no_knn["knn_artifact_input"].fillna("").eq("").all()
    no_regime = rows.loc[rows["control_family"].eq("no_regime_backend")]
    assert no_regime["regime_model_backend"].eq("none").all()


def test_wpr10648_shuffled_label_control_blocks_no_effect_labels(tmp_path: Path) -> None:
    source = _write_control_source(
        tmp_path,
        include_label=True,
        include_timestamp=True,
        labels=[1, 1],
    )
    replay_profile = _write_json(tmp_path / "modern_window_profile.json", {"research_only": True})
    validation_manifest = _write_json(tmp_path / "validation_manifest.json", {"research_only": True})
    modern_profile = _write_json(tmp_path / "modern_profile.json", {"research_only": True})

    result = build_wpr10648_negative_control_artifacts(
        symbol_inputs=[
            WPR10648NegativeControlInput(
                symbol="BTCUSDT",
                source_manifest_path=source["manifest"],
                source_rows_path=source["rows"],
                replay_profile_path=replay_profile,
                validation_manifest_path=validation_manifest,
                modern_window_profile_path=modern_profile,
                require_modern_window_evidence=True,
                deterministic_seed=7,
                shift_size=1,
            )
        ]
    )

    shuffled = result.control_rows.loc[result.control_rows["control_family"].eq("shuffled_labels")]
    assert shuffled["control_status"].eq("blocked").all()
    reasons = "|".join(shuffled["control_reasons"].astype(str))
    assert "shuffled_label_no_effect" in reasons
    assert "shuffled_label_hash_unchanged" in reasons


def test_wpr10648_shifted_context_control_requires_unique_timestamps_and_context_columns(tmp_path: Path) -> None:
    source = _write_control_source(
        tmp_path,
        include_label=True,
        include_timestamp=True,
        timestamps=[1000, 1000],
        include_context=False,
    )
    replay_profile = _write_json(tmp_path / "modern_window_profile.json", {"research_only": True})
    validation_manifest = _write_json(tmp_path / "validation_manifest.json", {"research_only": True})
    modern_profile = _write_json(tmp_path / "modern_profile.json", {"research_only": True})

    result = build_wpr10648_negative_control_artifacts(
        symbol_inputs=[
            WPR10648NegativeControlInput(
                symbol="BTCUSDT",
                source_manifest_path=source["manifest"],
                source_rows_path=source["rows"],
                replay_profile_path=replay_profile,
                validation_manifest_path=validation_manifest,
                modern_window_profile_path=modern_profile,
                require_modern_window_evidence=True,
                deterministic_seed=7,
                shift_size=1,
            )
        ]
    )

    shifted = result.control_rows.loc[result.control_rows["control_family"].eq("shifted_context")]
    assert shifted["control_status"].eq("blocked").all()
    reasons = "|".join(shifted["control_reasons"].astype(str))
    assert "source_timestamp_not_monotonic" in reasons
    assert "source_timestamp_not_unique" in reasons
    assert "shifted_context_columns_missing" in reasons


def test_wpr10648_negative_control_artifacts_fail_closed_when_profile_and_validation_are_missing(
    tmp_path: Path,
) -> None:
    source = _write_control_source(tmp_path, include_label=False, include_timestamp=False)

    result = build_wpr10648_negative_control_artifacts(
        symbol_inputs=[
            WPR10648NegativeControlInput(
                symbol="ETHUSDT",
                source_manifest_path=source["manifest"],
                source_rows_path=source["rows"],
                require_modern_window_evidence=True,
            )
        ]
    )

    assert result.manifest["control_status_counts"] == {"blocked": 8}
    reasons = "|".join(result.control_rows["control_reasons"].fillna("").astype(str).tolist())
    assert "replay_profile_provenance_missing" in reasons
    assert "validation_manifest_missing" in reasons
    assert "modern_window_evidence_required" in reasons
    assert "source_label_column_missing" in reasons
    assert "source_timestamp_column_missing" in reasons
    assert result.control_rows["candidate_evidence"].eq(False).all()


def test_wpr10647_control_rows_validate_first_class_control_artifact_before_available(
    tmp_path: Path,
) -> None:
    symbol_input = _write_symbol_input(tmp_path)
    source = _write_control_source(tmp_path, include_label=True, include_timestamp=True)
    control_result = build_wpr10648_negative_control_artifacts(
        symbol_inputs=[
            WPR10648NegativeControlInput(
                symbol="BTCUSDT",
                source_manifest_path=source["manifest"],
                source_rows_path=source["rows"],
            )
        ]
    )
    control_artifact = write_wpr10648_negative_control_artifacts(
        output_dir=tmp_path / "blocked-first-class-controls",
        result=control_result,
    )
    symbol_input = WPR10647SymbolEvidenceInput(
        symbol=symbol_input.symbol,
        preflight_manifest_path=symbol_input.preflight_manifest_path,
        preflight_rows_path=symbol_input.preflight_rows_path,
        spec_draft_manifest_path=symbol_input.spec_draft_manifest_path,
        spec_draft_rows_path=symbol_input.spec_draft_rows_path,
        exit_lab_manifest_path=symbol_input.exit_lab_manifest_path,
        control_artifact_paths={
            "shuffled_labels": control_artifact.manifest_path,
            "shifted_context": control_artifact.manifest_path,
            "no_knn_baseline": control_artifact.manifest_path,
            "no_regime_baseline": control_artifact.manifest_path,
        },
    )

    result = build_wpr10647_replay_evidence(symbol_inputs=[symbol_input])

    assert result.negative_control_rows["control_status"].eq("blocked").all()
    reasons = "|".join(result.negative_control_rows["control_reasons"].astype(str).tolist())
    assert "first_class_negative_control_artifact_blocked" in reasons
    assert "replay_profile_provenance_missing" in reasons


def test_wpr10647_control_rows_reject_tampered_first_class_control_rows_hash(
    tmp_path: Path,
) -> None:
    symbol_input = _write_symbol_input(tmp_path)
    source = _write_control_source(tmp_path, include_label=True, include_timestamp=True)
    control_result = build_wpr10648_negative_control_artifacts(
        symbol_inputs=[
            WPR10648NegativeControlInput(
                symbol="BTCUSDT",
                source_manifest_path=source["manifest"],
                source_rows_path=source["rows"],
            )
        ]
    )
    control_artifact = write_wpr10648_negative_control_artifacts(
        output_dir=tmp_path / "first-class-controls",
        result=control_result,
    )
    rows = pd.read_parquet(control_artifact.control_rows_path)
    rows.loc[:, "control_status"] = "available"
    rows.to_parquet(control_artifact.control_rows_path, index=False)
    symbol_input = WPR10647SymbolEvidenceInput(
        symbol=symbol_input.symbol,
        preflight_manifest_path=symbol_input.preflight_manifest_path,
        preflight_rows_path=symbol_input.preflight_rows_path,
        spec_draft_manifest_path=symbol_input.spec_draft_manifest_path,
        spec_draft_rows_path=symbol_input.spec_draft_rows_path,
        exit_lab_manifest_path=symbol_input.exit_lab_manifest_path,
        control_artifact_paths={"shuffled_labels": control_artifact.manifest_path},
    )

    result = build_wpr10647_replay_evidence(symbol_inputs=[symbol_input])

    reasons = "|".join(result.negative_control_rows["control_reasons"].astype(str).tolist())
    assert "negative_control_rows_sha256_mismatch" in reasons
    assert result.negative_control_rows["control_status"].eq("blocked").all()


def test_wpr10647_control_rows_reject_tampered_first_class_control_row_boundary_flags(
    tmp_path: Path,
) -> None:
    symbol_input = _write_symbol_input(tmp_path)
    source = _write_control_source(tmp_path, include_label=True, include_timestamp=True)
    replay_profile = _write_json(tmp_path / "replay_profile.json", {"research_only": True})
    validation_manifest = _write_json(tmp_path / "validation_manifest.json", {"research_only": True})
    modern_profile = _write_json(tmp_path / "modern_profile.json", {"research_only": True})
    control_result = build_wpr10648_negative_control_artifacts(
        symbol_inputs=[
            WPR10648NegativeControlInput(
                symbol="BTCUSDT",
                source_manifest_path=source["manifest"],
                source_rows_path=source["rows"],
                replay_profile_path=replay_profile,
                validation_manifest_path=validation_manifest,
                modern_window_profile_path=modern_profile,
                require_modern_window_evidence=True,
            )
        ]
    )
    control_artifact = write_wpr10648_negative_control_artifacts(
        output_dir=tmp_path / "first-class-controls",
        result=control_result,
    )
    rows = pd.read_parquet(control_artifact.control_rows_path)
    rows.loc[rows["control_family"].eq("shuffled_labels"), "candidate_evidence"] = True
    rows.loc[rows["control_family"].eq("shuffled_labels"), "candidate_pack_eligible"] = True
    rows.loc[rows["control_family"].eq("shuffled_labels"), "promotion_ready"] = True
    rows.to_parquet(control_artifact.control_rows_path, index=False)
    manifest = json.loads(control_artifact.manifest_path.read_text(encoding="utf-8"))
    manifest["control_rows_sha256"] = _sha256(control_artifact.control_rows_path)
    control_artifact.manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    symbol_input = WPR10647SymbolEvidenceInput(
        symbol=symbol_input.symbol,
        preflight_manifest_path=symbol_input.preflight_manifest_path,
        preflight_rows_path=symbol_input.preflight_rows_path,
        spec_draft_manifest_path=symbol_input.spec_draft_manifest_path,
        spec_draft_rows_path=symbol_input.spec_draft_rows_path,
        exit_lab_manifest_path=symbol_input.exit_lab_manifest_path,
        control_artifact_paths={"shuffled_labels": control_artifact.manifest_path},
    )

    result = build_wpr10647_replay_evidence(symbol_inputs=[symbol_input])

    reasons = "|".join(result.negative_control_rows["control_reasons"].astype(str).tolist())
    assert "negative_control_rows_candidate_evidence_must_be_false" in reasons
    assert "negative_control_rows_candidate_pack_eligible_must_be_false" in reasons
    assert "negative_control_rows_promotion_ready_must_be_false" in reasons
    assert result.negative_control_rows["control_status"].eq("blocked").all()


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


def _write_control_source(
    tmp_path: Path,
    *,
    include_label: bool,
    include_timestamp: bool,
    labels: list[int] | None = None,
    timestamps: list[int] | None = None,
    include_context: bool = True,
) -> dict[str, Path]:
    source_dir = tmp_path / f"control-source-{include_label}-{include_timestamp}"
    source_dir.mkdir(parents=True)
    replay_spec = _write_json(source_dir / "replay_spec.json", {"research_only": True})
    discovery_manifest = _write_json(source_dir / "discovery_manifest.json", {"research_only": True})
    manifest = _write_json(
        source_dir / "source_manifest.json",
        {
            "replay_overlay_cycle_preflight_manifest_version": "replay-overlay-cycle-spec-preflight-v1",
            "symbol": "BTCUSDT",
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "candidate_pack_written": False,
            "source_replay_spec_path": str(replay_spec),
            "source_replay_spec_sha256": _sha256(replay_spec),
            "source_discovery_manifest_path": str(discovery_manifest),
            "source_discovery_manifest_sha256": _sha256(discovery_manifest),
        },
    )
    rows = pd.DataFrame(
        [
            {
                "candidate_id": "candidate-a",
                "materialized_candidate_id": "mat-a",
                "source_trial_id": "trial-a",
                "source_record_sha256": "record-a",
                **({"context_bucket": "trend"} if include_context else {}),
            },
            {
                "candidate_id": "candidate-b",
                "materialized_candidate_id": "mat-b",
                "source_trial_id": "trial-b",
                "source_record_sha256": "record-b",
                **({"context_bucket": "range"} if include_context else {}),
            },
        ]
    )
    if include_label:
        rows["label"] = labels or [1, -1]
    if include_timestamp:
        rows["timestamp_ms"] = timestamps or [1000, 2000]
    rows_path = source_dir / "source_rows.parquet"
    rows.to_parquet(rows_path, index=False)
    return {"manifest": manifest, "rows": rows_path}


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
