from __future__ import annotations

import json
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from tradingbotsuite.config import AppConfig, ResearchConfig
from tradingbotsuite.main import _run_discovery_candidate_pack_bridge_command
from tradingbotsuite.research_discovery.candidate_pack_bridge import (
    DISCOVERY_CANDIDATE_PACK_BRIDGE_VERSION,
    evaluate_discovery_candidate_pack_eligibility,
    write_discovery_candidate_pack_eligibility,
)
from tradingbotsuite.research_discovery.runner import run_discovery

from tests.research_artifacts.test_candidate_pack import _cycle_outputs


def _clock() -> datetime:
    return datetime(2026, 5, 8, 10, 0, tzinfo=timezone.utc)


def _app_config(tmp_path: Path) -> AppConfig:
    return AppConfig(research=ResearchConfig(output_dir=tmp_path / "research"))


def _write_spec(
    path: Path,
    *,
    run_id: str = "bridge-run",
    max_trials: int = 3,
    trial_templates: list[dict[str, object]] | None = None,
) -> Path:
    payload: dict[str, object] = {
        "run_id": run_id,
        "symbol": "BTCUSDT",
        "timeframe": "15m",
        "budget": {"max_trials": max_trials, "trial_batch_size": 1, "snapshot_interval_minutes": 30},
    }
    if trial_templates is not None:
        payload["trial_templates"] = trial_templates
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def test_bridge_writes_eligibility_only_for_existing_gate_pass(tmp_path: Path) -> None:
    discovery = run_discovery(
        spec_path=_write_spec(tmp_path / "specs" / "discovery.json"),
        app_config=_app_config(tmp_path),
        clock=_clock,
    )
    cycle_manifest = _cycle_outputs(tmp_path / "cycle-fixture")

    result = evaluate_discovery_candidate_pack_eligibility(
        discovery_manifest_path=discovery.manifest_path,
        cycle_manifest_path=cycle_manifest,
        candidate_id_map={"bridge-run-candidate-000001": "candidate-1"},
    )
    artifact = write_discovery_candidate_pack_eligibility(output_dir=tmp_path / "bridge-output", result=result)
    manifest = json.loads(artifact.manifest_path.read_text(encoding="utf-8"))
    eligibility = pd.read_parquet(artifact.eligibility_path)

    assert manifest["discovery_candidate_pack_bridge_version"] == DISCOVERY_CANDIDATE_PACK_BRIDGE_VERSION
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["candidate_pack_written"] is False
    assert manifest["candidate_pack_paths"] == []
    assert manifest["summary"]["eligible_count"] == 1
    assert eligibility.loc[0, "bridge_status"] == "eligible"
    assert bool(eligibility.loc[0, "candidate_pack_written"]) is False
    assert not (cycle_manifest.parent / "research_candidate_pack").exists()


def test_bridge_blocks_discovery_only_candidate_without_cycle_manifest(tmp_path: Path) -> None:
    discovery = run_discovery(
        spec_path=_write_spec(tmp_path / "specs" / "discovery.json"),
        app_config=_app_config(tmp_path),
        clock=_clock,
    )

    result = evaluate_discovery_candidate_pack_eligibility(discovery_manifest_path=discovery.manifest_path)

    assert result.manifest["summary"]["eligible_count"] == 0
    assert result.eligibility.loc[0, "bridge_status"] == "blocked"
    assert "historical_cycle_manifest_required" in result.eligibility.loc[0, "bridge_reasons"]
    assert result.manifest["candidate_pack_written"] is False


def test_bridge_blocks_incomplete_discovery_state(tmp_path: Path) -> None:
    discovery = run_discovery(
        spec_path=_write_spec(tmp_path / "specs" / "discovery.json"),
        app_config=_app_config(tmp_path),
        stop_after_trials=1,
        clock=_clock,
    )
    cycle_manifest = _cycle_outputs(tmp_path / "cycle-fixture")

    result = evaluate_discovery_candidate_pack_eligibility(
        discovery_manifest_path=discovery.manifest_path,
        cycle_manifest_path=cycle_manifest,
        candidate_id_map={"bridge-run-candidate-000001": "candidate-1"},
    )

    assert result.manifest["summary"]["eligible_count"] == 0
    assert "discovery_run_state_must_be_completed" in result.eligibility.loc[0, "bridge_reasons"]


def test_bridge_blocks_tampered_trial_hash(tmp_path: Path) -> None:
    discovery = run_discovery(
        spec_path=_write_spec(tmp_path / "specs" / "discovery.json"),
        app_config=_app_config(tmp_path),
        clock=_clock,
    )
    trial_path = discovery.output_dir / "trials" / "trial-000001.json"
    payload = json.loads(trial_path.read_text(encoding="utf-8"))
    payload["score"] = 999.0
    trial_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    cycle_manifest = _cycle_outputs(tmp_path / "cycle-fixture")

    result = evaluate_discovery_candidate_pack_eligibility(
        discovery_manifest_path=discovery.manifest_path,
        cycle_manifest_path=cycle_manifest,
        candidate_id_map={"bridge-run-candidate-000001": "candidate-1"},
    )

    assert result.manifest["summary"]["eligible_count"] == 0
    assert "discovery_trial_record_hash_mismatch:trial-000001" in result.eligibility.loc[0, "bridge_reasons"]


def test_bridge_blocks_tampered_interesting_ledger_candidate(tmp_path: Path) -> None:
    discovery = run_discovery(
        spec_path=_write_spec(tmp_path / "specs" / "discovery.json"),
        app_config=_app_config(tmp_path),
        clock=_clock,
    )
    interesting = pd.read_parquet(discovery.interesting_candidates_path)
    fabricated = dict(interesting.iloc[0].to_dict())
    fabricated["candidate_id"] = "fabricated-candidate"
    pd.concat([interesting, pd.DataFrame([fabricated])], ignore_index=True).to_parquet(
        discovery.interesting_candidates_path,
        index=False,
    )
    cycle_manifest = _cycle_outputs(tmp_path / "cycle-fixture")

    result = evaluate_discovery_candidate_pack_eligibility(
        discovery_manifest_path=discovery.manifest_path,
        cycle_manifest_path=cycle_manifest,
        candidate_id_map={"fabricated-candidate": "candidate-1", "bridge-run-candidate-000001": "candidate-1"},
    )

    assert result.manifest["summary"]["eligible_count"] == 0
    assert "discovery_ledger_records_mismatch:interesting_candidates" in result.manifest["global_reasons"]
    assert result.eligibility["bridge_status"].eq("blocked").all()


def test_bridge_blocks_run_state_status_tamper_on_incomplete_run(tmp_path: Path) -> None:
    discovery = run_discovery(
        spec_path=_write_spec(tmp_path / "specs" / "discovery.json"),
        app_config=_app_config(tmp_path),
        stop_after_trials=1,
        clock=_clock,
    )
    state = json.loads(discovery.run_state_path.read_text(encoding="utf-8"))
    state["status"] = "completed"
    discovery.run_state_path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    cycle_manifest = _cycle_outputs(tmp_path / "cycle-fixture")

    result = evaluate_discovery_candidate_pack_eligibility(
        discovery_manifest_path=discovery.manifest_path,
        cycle_manifest_path=cycle_manifest,
        candidate_id_map={"bridge-run-candidate-000001": "candidate-1"},
    )

    assert result.manifest["summary"]["eligible_count"] == 0
    reasons = result.eligibility.loc[0, "bridge_reasons"]
    assert "discovery_run_state_manifest_state_mismatch" in reasons
    assert "discovery_completed_trial_count_mismatch" in reasons


def test_bridge_blocks_live_adjacent_trial_record_field(tmp_path: Path) -> None:
    discovery = run_discovery(
        spec_path=_write_spec(tmp_path / "specs" / "discovery.json"),
        app_config=_app_config(tmp_path),
        clock=_clock,
    )
    trial_path = discovery.output_dir / "trials" / "trial-000001.json"
    payload = json.loads(trial_path.read_text(encoding="utf-8"))
    payload["promotion_candidate_manifest_version"] = "forbidden"
    trial_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    cycle_manifest = _cycle_outputs(tmp_path / "cycle-fixture")

    result = evaluate_discovery_candidate_pack_eligibility(
        discovery_manifest_path=discovery.manifest_path,
        cycle_manifest_path=cycle_manifest,
        candidate_id_map={"bridge-run-candidate-000001": "candidate-1"},
    )

    assert result.manifest["summary"]["eligible_count"] == 0
    assert "discovery_trial_record_boundary_violation:trial-000001" in result.eligibility.loc[0, "bridge_reasons"]


def test_bridge_blocks_candidates_also_seen_in_blocker_ledgers(tmp_path: Path) -> None:
    candidate_id = "duplicate-candidate"
    discovery = run_discovery(
        spec_path=_write_spec(
            tmp_path / "specs" / "discovery.json",
            run_id="duplicate-run",
            trial_templates=[
                {"trial_id": "trial-000001", "candidate_id": candidate_id, "ledger_kind": "interesting", "score": 0.5},
                {
                    "trial_id": "trial-000002",
                    "candidate_id": candidate_id,
                    "ledger_kind": "blocked",
                    "score": 0.0,
                    "blocker_code": "duplicate_blocker",
                },
                {
                    "trial_id": "trial-000003",
                    "candidate_id": candidate_id,
                    "ledger_kind": "filter_blocked",
                    "score": 0.0,
                    "filter_blocker_code": "duplicate_filter",
                },
            ],
        ),
        app_config=_app_config(tmp_path),
        clock=_clock,
    )
    cycle_manifest = _cycle_outputs(tmp_path / "cycle-fixture")

    result = evaluate_discovery_candidate_pack_eligibility(
        discovery_manifest_path=discovery.manifest_path,
        cycle_manifest_path=cycle_manifest,
        candidate_id_map={candidate_id: "candidate-1"},
    )

    reasons = result.eligibility.loc[0, "bridge_reasons"]
    assert "candidate_present_in_blocked_candidates" in reasons
    assert "candidate_present_in_filter_blockers" in reasons
    assert result.eligibility.loc[0, "bridge_status"] == "blocked"


def test_bridge_propagates_existing_candidate_gate_reasons(tmp_path: Path) -> None:
    discovery = run_discovery(
        spec_path=_write_spec(tmp_path / "specs" / "discovery.json"),
        app_config=_app_config(tmp_path),
        clock=_clock,
    )
    cycle_manifest = _cycle_outputs(tmp_path / "cycle-fixture", synthetic=True)

    result = evaluate_discovery_candidate_pack_eligibility(
        discovery_manifest_path=discovery.manifest_path,
        cycle_manifest_path=cycle_manifest,
        candidate_id_map={"bridge-run-candidate-000001": "candidate-1"},
    )

    reasons = result.eligibility.loc[0, "bridge_reasons"]
    assert "research_candidate_gate:synthetic_fixture_not_research_pack_evidence" in reasons
    assert result.eligibility.loc[0, "research_candidate_gate_status"] == "blocked"


def test_bridge_cli_payload_writes_audit_artifacts_without_pack_paths(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("tradingbotsuite.main.AppConfig.from_env", lambda: _app_config(tmp_path))
    discovery = run_discovery(
        spec_path=_write_spec(tmp_path / "specs" / "discovery.json"),
        app_config=_app_config(tmp_path),
        clock=_clock,
    )
    cycle_manifest = _cycle_outputs(tmp_path / "cycle-fixture")

    payload = _run_discovery_candidate_pack_bridge_command(
        Namespace(
            discovery_manifest=str(discovery.manifest_path),
            cycle_manifest=str(cycle_manifest),
            output_dir=str(tmp_path / "research" / "cli-bridge"),
            candidate_id_map_json=json.dumps({"bridge-run-candidate-000001": "candidate-1"}),
        )
    )

    assert payload["eligible_count"] == 1
    assert payload["blocked_count"] == 0
    assert payload["candidate_pack_written"] is False
    assert payload["candidate_pack_paths"] == []
    assert Path(str(payload["bridge_manifest_path"])).exists()


def test_bridge_cli_default_output_is_isolated_under_research_root(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("tradingbotsuite.main.AppConfig.from_env", lambda: _app_config(tmp_path))
    discovery = run_discovery(
        spec_path=_write_spec(tmp_path / "specs" / "discovery.json"),
        app_config=_app_config(tmp_path),
        clock=_clock,
    )
    cycle_manifest = _cycle_outputs(tmp_path / "cycle-fixture")

    payload = _run_discovery_candidate_pack_bridge_command(
        Namespace(
            discovery_manifest=str(discovery.manifest_path),
            cycle_manifest=str(cycle_manifest),
            output_dir=None,
            candidate_id_map_json=json.dumps({"bridge-run-candidate-000001": "candidate-1"}),
        )
    )

    output_dir = Path(str(payload["output_dir"]))
    output_dir.relative_to((tmp_path / "research" / "discovery_candidate_pack_bridge").resolve())
    assert Path(str(payload["bridge_manifest_path"])).exists()


def test_bridge_cli_rejects_output_dir_outside_research_root(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("tradingbotsuite.main.AppConfig.from_env", lambda: _app_config(tmp_path))
    discovery = run_discovery(
        spec_path=_write_spec(tmp_path / "specs" / "discovery.json"),
        app_config=_app_config(tmp_path),
        clock=_clock,
    )
    cycle_manifest = _cycle_outputs(tmp_path / "cycle-fixture")

    with pytest.raises(ValueError, match="output_dir must stay inside"):
        _run_discovery_candidate_pack_bridge_command(
            Namespace(
                discovery_manifest=str(discovery.manifest_path),
                cycle_manifest=str(cycle_manifest),
                output_dir=str(tmp_path / "outside"),
                candidate_id_map_json=json.dumps({"bridge-run-candidate-000001": "candidate-1"}),
            )
        )


def test_bridge_writer_refuses_existing_audit_artifacts(tmp_path: Path) -> None:
    discovery = run_discovery(
        spec_path=_write_spec(tmp_path / "specs" / "discovery.json"),
        app_config=_app_config(tmp_path),
        clock=_clock,
    )
    cycle_manifest = _cycle_outputs(tmp_path / "cycle-fixture")
    result = evaluate_discovery_candidate_pack_eligibility(
        discovery_manifest_path=discovery.manifest_path,
        cycle_manifest_path=cycle_manifest,
        candidate_id_map={"bridge-run-candidate-000001": "candidate-1"},
    )
    output_dir = tmp_path / "bridge-output"
    write_discovery_candidate_pack_eligibility(output_dir=output_dir, result=result)

    with pytest.raises(ValueError, match="refusing to overwrite existing discovery candidate-pack bridge artifacts"):
        write_discovery_candidate_pack_eligibility(output_dir=output_dir, result=result)
