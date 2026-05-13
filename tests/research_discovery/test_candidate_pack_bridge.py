from __future__ import annotations

import json
from argparse import Namespace
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

import pandas as pd
import pytest

from tradingbotsuite.config import AppConfig, ResearchConfig
from tradingbotsuite.main import _run_discovery_candidate_pack_bridge_command
from tradingbotsuite.research_discovery import candidate_pack_bridge
from tradingbotsuite.research_discovery.candidate_pack_bridge import (
    DISCOVERY_CANDIDATE_PACK_BRIDGE_VERSION,
    evaluate_discovery_candidate_pack_eligibility,
    write_discovery_candidate_pack_eligibility,
)
from tradingbotsuite.research_discovery.exit_lab import (
    DiscoveryExitLabSpec,
    build_discovery_exit_lab,
    discovery_entry_lead_evidence_sha256,
    write_discovery_exit_lab_artifacts,
)
from tradingbotsuite.research_discovery.multiple_testing import (
    DiscoveryMultipleTestingSpec,
    build_discovery_multiple_testing_report,
    write_discovery_multiple_testing_artifacts,
)
from tradingbotsuite.research_discovery.validation_floors import (
    DiscoveryValidationFloorSpec,
    build_discovery_validation_floor_report,
    write_discovery_validation_floor_artifacts,
)
from tradingbotsuite.research_discovery.runner import LEDGER_COLUMNS, run_discovery

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


def _write_exit_lab(
    tmp_path: Path,
    discovery,
    *,
    research_candidate_id: str = "candidate-1",
    treatment_score: float = 0.14,
    fixed_holding_only: bool = False,
    lead_hash: str | None = None,
):
    spec = DiscoveryExitLabSpec.from_path(Path("configs/discovery/discovery_exit_lab_v4.json"))
    if fixed_holding_only:
        spec = DiscoveryExitLabSpec(
            lab_id=spec.lab_id,
            entry_group_columns=spec.entry_group_columns,
            comparisons=(spec.comparisons[0],),
        )
    interesting = pd.read_parquet(discovery.interesting_candidates_path)
    lead = interesting.iloc[0].to_dict()
    entry_hash = lead_hash or discovery_entry_lead_evidence_sha256(lead)
    common = {
        "entry_candidate_id": str(lead["candidate_id"]),
        "research_candidate_id": research_candidate_id,
        "entry_lead_evidence_sha256": entry_hash,
        "strategy_id": "hmm_knn_local_analog_filter_v2",
        "feature_set_id": "features_discovery_screen_v1",
        "holding_window": "4h",
        "parameters_json": "{}",
        "feature_column_set_id": str(lead.get("feature_column_set_id") or ""),
        "regime_mode": str(lead.get("regime_mode") or ""),
        "distance_metric": str(lead.get("distance_metric") or ""),
        "k": int(float(lead.get("k") or 0)),
        "cost_stress_status": "passed",
    }
    rows = [
        {
            **common,
            "candidate_id": f"{research_candidate_id}-fixed",
            "exit_policy_id": "fixed_holding_window",
            "exit_policy_params_json": "{}",
            "final_score": 0.10,
            "trade_count": 12,
        }
    ]
    if not fixed_holding_only:
        rows.append(
            {
                **common,
                "candidate_id": f"{research_candidate_id}-barrier",
                "exit_policy_id": "triple_barrier_atr",
                "exit_policy_params_json": "{}",
                "final_score": treatment_score,
                "trade_count": 10,
            }
        )
    result = build_discovery_exit_lab(pd.DataFrame(rows), spec=spec)
    return write_discovery_exit_lab_artifacts(tmp_path / f"exit-lab-{research_candidate_id}", result)


def _write_multiple_testing(tmp_path: Path, discovery, *, blocked: bool = False):
    interesting = pd.read_parquet(discovery.interesting_candidates_path)
    interesting["split_window_concentration"] = 0.25
    interesting["side_concentration"] = 0.55
    spec = DiscoveryMultipleTestingSpec(
        declared_search_space=10_000 if blocked else 3,
        latest_window_only=blocked,
        min_stability_neighborhood_size=3 if blocked else 1,
        max_best_candidate_concentration=0.50 if blocked else 1.0,
    )
    result = build_discovery_multiple_testing_report(interesting, spec=spec)
    result.manifest["source_discovery_manifest_path"] = str(discovery.manifest_path)
    result.manifest["source_discovery_manifest_sha256"] = _sha256(discovery.manifest_path)
    return write_discovery_multiple_testing_artifacts(tmp_path / "multiple-testing", result)


def _write_validation_floors(
    tmp_path: Path,
    discovery,
    *,
    blocked: bool = False,
    record_sha: str | None = None,
):
    interesting = pd.read_parquet(discovery.interesting_candidates_path)
    frame = interesting.copy()
    if record_sha is not None:
        frame.loc[0, "record_sha256"] = record_sha
    frame["split_pass_ratio"] = 0.80 if not blocked else 0.20
    frame["side_concentration"] = 0.55
    frame["cost_stress_survival"] = 1.0
    frame["stability_neighborhood_size"] = 4
    frame["baseline_comparator_coverage_status"] = "complete"
    frame["expectancy_vs_no_trade"] = 0.01
    frame["directional_comparator_status"] = "complete"
    frame["no_regime_baseline_status"] = "complete"
    frame["exit_lab_status"] = "complete"
    frame["exit_lab_gate_status"] = "passed"
    frame["filter_ablation_status"] = "edge_improving"
    frame["feature_ablation_status"] = "passed"
    frame["source_provider_capability_present"] = True
    frame["source_provider_capability_candidate_ready_default"] = True
    frame["source_provider_capability_diagnostic_only_by_default"] = False
    frame["durable_public_archive_readiness_ready"] = True
    frame["durable_public_archive_readiness_status"] = "durable_public_archive_ready"
    if blocked:
        frame["independent_event_count"] = 25
        frame["overlap_ratio"] = 0.90
        frame["latest_window_only"] = True
    else:
        frame["independent_event_count"] = 260
        frame["overlap_ratio"] = 0.10
        frame["latest_window_only"] = False
    spec = DiscoveryValidationFloorSpec(declared_search_space=100)
    result = build_discovery_validation_floor_report(
        frame,
        spec=spec,
        source_discovery_manifest_path=discovery.manifest_path,
    )
    return write_discovery_validation_floor_artifacts(tmp_path / "validation-floors", result)


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_payload_sha256(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False).encode("utf-8")
    return sha256(encoded).hexdigest()


def test_bridge_ledger_columns_match_runner_columns() -> None:
    assert tuple(candidate_pack_bridge.DISCOVERY_LEDGER_COLUMNS) == tuple(LEDGER_COLUMNS)


def test_bridge_writes_eligibility_only_for_existing_gate_pass(tmp_path: Path) -> None:
    discovery = run_discovery(
        spec_path=_write_spec(tmp_path / "specs" / "discovery.json"),
        app_config=_app_config(tmp_path),
        clock=_clock,
    )
    cycle_manifest = _cycle_outputs(tmp_path / "cycle-fixture")
    exit_lab = _write_exit_lab(tmp_path, discovery)
    multiple_testing = _write_multiple_testing(tmp_path, discovery)
    validation_floors = _write_validation_floors(tmp_path, discovery)

    result = evaluate_discovery_candidate_pack_eligibility(
        discovery_manifest_path=discovery.manifest_path,
        cycle_manifest_path=cycle_manifest,
        exit_lab_manifest_path=exit_lab.manifest_path,
        multiple_testing_manifest_path=multiple_testing.manifest_path,
        validation_floors_manifest_path=validation_floors.manifest_path,
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
    assert manifest["exit_lab_gate_required"] is True
    assert manifest["summary"]["eligible_count"] == 1
    assert eligibility.loc[0, "bridge_status"] == "eligible"
    assert eligibility.loc[0, "exit_lab_status"] == "complete"
    assert eligibility.loc[0, "exit_lab_best_family"] == "barrier"
    assert eligibility.loc[0, "multiple_testing_status"] == "passed"
    assert eligibility.loc[0, "research_maturity"] == "candidate-ready"
    assert eligibility.loc[0, "validation_floor_status"] == "passed"
    assert bool(eligibility.loc[0, "candidate_pack_written"]) is False
    assert not (cycle_manifest.parent / "research_candidate_pack").exists()


def test_bridge_blocks_missing_exit_lab_even_when_cycle_gate_passes(tmp_path: Path) -> None:
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

    assert result.manifest["summary"]["eligible_count"] == 0
    assert result.eligibility.loc[0, "bridge_status"] == "blocked"
    assert "exit_lab_manifest_required" in result.eligibility.loc[0, "bridge_reasons"]
    assert result.eligibility.loc[0, "research_candidate_gate_status"] == "passed"


def test_bridge_blocks_missing_multiple_testing_even_when_exit_and_cycle_pass(tmp_path: Path) -> None:
    discovery = run_discovery(
        spec_path=_write_spec(tmp_path / "specs" / "discovery.json"),
        app_config=_app_config(tmp_path),
        clock=_clock,
    )
    cycle_manifest = _cycle_outputs(tmp_path / "cycle-fixture")
    exit_lab = _write_exit_lab(tmp_path, discovery)

    result = evaluate_discovery_candidate_pack_eligibility(
        discovery_manifest_path=discovery.manifest_path,
        cycle_manifest_path=cycle_manifest,
        exit_lab_manifest_path=exit_lab.manifest_path,
        candidate_id_map={"bridge-run-candidate-000001": "candidate-1"},
    )

    assert result.manifest["summary"]["eligible_count"] == 0
    assert result.eligibility.loc[0, "bridge_status"] == "blocked"
    assert "multiple_testing_manifest_required" in result.eligibility.loc[0, "bridge_reasons"]
    assert result.eligibility.loc[0, "research_candidate_gate_status"] == "passed"


def test_bridge_blocks_missing_validation_floors_even_when_other_gates_pass(tmp_path: Path) -> None:
    discovery = run_discovery(
        spec_path=_write_spec(tmp_path / "specs" / "discovery.json"),
        app_config=_app_config(tmp_path),
        clock=_clock,
    )
    cycle_manifest = _cycle_outputs(tmp_path / "cycle-fixture")
    exit_lab = _write_exit_lab(tmp_path, discovery)
    multiple_testing = _write_multiple_testing(tmp_path, discovery)

    result = evaluate_discovery_candidate_pack_eligibility(
        discovery_manifest_path=discovery.manifest_path,
        cycle_manifest_path=cycle_manifest,
        exit_lab_manifest_path=exit_lab.manifest_path,
        multiple_testing_manifest_path=multiple_testing.manifest_path,
        candidate_id_map={"bridge-run-candidate-000001": "candidate-1"},
    )

    assert result.manifest["summary"]["eligible_count"] == 0
    assert result.eligibility.loc[0, "bridge_status"] == "blocked"
    assert "validation_floor_manifest_required" in result.eligibility.loc[0, "bridge_reasons"]
    assert result.eligibility.loc[0, "research_candidate_gate_status"] == "passed"


def test_bridge_blocks_validation_floor_failures(tmp_path: Path) -> None:
    discovery = run_discovery(
        spec_path=_write_spec(tmp_path / "specs" / "discovery.json"),
        app_config=_app_config(tmp_path),
        clock=_clock,
    )
    cycle_manifest = _cycle_outputs(tmp_path / "cycle-fixture")
    exit_lab = _write_exit_lab(tmp_path, discovery)
    multiple_testing = _write_multiple_testing(tmp_path, discovery)
    validation_floors = _write_validation_floors(tmp_path, discovery, blocked=True)

    result = evaluate_discovery_candidate_pack_eligibility(
        discovery_manifest_path=discovery.manifest_path,
        cycle_manifest_path=cycle_manifest,
        exit_lab_manifest_path=exit_lab.manifest_path,
        multiple_testing_manifest_path=multiple_testing.manifest_path,
        validation_floors_manifest_path=validation_floors.manifest_path,
        candidate_id_map={"bridge-run-candidate-000001": "candidate-1"},
    )

    reasons = result.eligibility.loc[0, "bridge_reasons"]
    assert result.manifest["summary"]["eligible_count"] == 0
    assert result.eligibility.loc[0, "research_maturity"] == "diagnostic"
    assert "validation_floor_gate:candidate_ready_validation_required" in reasons
    assert "validation_floor_gate:independent_event_count_below_floor" in reasons
    assert "validation_floor_gate:overlap_ratio_above_ceiling" in reasons
    assert "validation_floor_gate:latest_window_only_diagnostic" in reasons


def test_bridge_blocks_validation_floor_record_hash_mismatch(tmp_path: Path) -> None:
    discovery = run_discovery(
        spec_path=_write_spec(tmp_path / "specs" / "discovery.json"),
        app_config=_app_config(tmp_path),
        clock=_clock,
    )
    cycle_manifest = _cycle_outputs(tmp_path / "cycle-fixture")
    exit_lab = _write_exit_lab(tmp_path, discovery)
    multiple_testing = _write_multiple_testing(tmp_path, discovery)
    validation_floors = _write_validation_floors(tmp_path, discovery, record_sha="wrong-record")

    result = evaluate_discovery_candidate_pack_eligibility(
        discovery_manifest_path=discovery.manifest_path,
        cycle_manifest_path=cycle_manifest,
        exit_lab_manifest_path=exit_lab.manifest_path,
        multiple_testing_manifest_path=multiple_testing.manifest_path,
        validation_floors_manifest_path=validation_floors.manifest_path,
        candidate_id_map={"bridge-run-candidate-000001": "candidate-1"},
    )

    assert result.manifest["summary"]["eligible_count"] == 0
    assert "validation_floor_gate:record_sha256_mismatch" in result.eligibility.loc[0, "bridge_reasons"]


def test_bridge_blocks_validation_floor_blocker_registry_hash_mismatch(tmp_path: Path) -> None:
    discovery = run_discovery(
        spec_path=_write_spec(tmp_path / "specs" / "discovery.json"),
        app_config=_app_config(tmp_path),
        clock=_clock,
    )
    cycle_manifest = _cycle_outputs(tmp_path / "cycle-fixture")
    exit_lab = _write_exit_lab(tmp_path, discovery)
    multiple_testing = _write_multiple_testing(tmp_path, discovery)
    validation_floors = _write_validation_floors(tmp_path, discovery)
    manifest = json.loads(validation_floors.manifest_path.read_text(encoding="utf-8"))
    manifest["blocker_registry_sha256"] = "wrong-registry"
    validation_floors.manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    result = evaluate_discovery_candidate_pack_eligibility(
        discovery_manifest_path=discovery.manifest_path,
        cycle_manifest_path=cycle_manifest,
        exit_lab_manifest_path=exit_lab.manifest_path,
        multiple_testing_manifest_path=multiple_testing.manifest_path,
        validation_floors_manifest_path=validation_floors.manifest_path,
        candidate_id_map={"bridge-run-candidate-000001": "candidate-1"},
    )

    assert result.manifest["summary"]["eligible_count"] == 0
    assert "validation_floor_blocker_registry_sha256_mismatch" in result.eligibility.loc[0, "bridge_reasons"]


def test_bridge_blocks_validation_floor_blocker_registry_payload_mismatch(tmp_path: Path) -> None:
    discovery = run_discovery(
        spec_path=_write_spec(tmp_path / "specs" / "discovery.json"),
        app_config=_app_config(tmp_path),
        clock=_clock,
    )
    cycle_manifest = _cycle_outputs(tmp_path / "cycle-fixture")
    exit_lab = _write_exit_lab(tmp_path, discovery)
    multiple_testing = _write_multiple_testing(tmp_path, discovery)
    validation_floors = _write_validation_floors(tmp_path, discovery)
    manifest = json.loads(validation_floors.manifest_path.read_text(encoding="utf-8"))
    registry = dict(manifest["blocker_registry"])
    codes = dict(registry["codes"])
    codes.pop("exit_lab_missing")
    registry["codes"] = codes
    manifest["blocker_registry"] = registry
    manifest["blocker_registry_sha256"] = _stable_payload_sha256(registry)
    validation_floors.manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    result = evaluate_discovery_candidate_pack_eligibility(
        discovery_manifest_path=discovery.manifest_path,
        cycle_manifest_path=cycle_manifest,
        exit_lab_manifest_path=exit_lab.manifest_path,
        multiple_testing_manifest_path=multiple_testing.manifest_path,
        validation_floors_manifest_path=validation_floors.manifest_path,
        candidate_id_map={"bridge-run-candidate-000001": "candidate-1"},
    )

    assert result.manifest["summary"]["eligible_count"] == 0
    assert "validation_floor_blocker_registry_payload_mismatch" in result.eligibility.loc[0, "bridge_reasons"]


def test_bridge_blocks_legacy_validation_floor_gate_without_exit_lab_gate_status(tmp_path: Path) -> None:
    discovery = run_discovery(
        spec_path=_write_spec(tmp_path / "specs" / "discovery.json"),
        app_config=_app_config(tmp_path),
        clock=_clock,
    )
    cycle_manifest = _cycle_outputs(tmp_path / "cycle-fixture")
    exit_lab = _write_exit_lab(tmp_path, discovery)
    multiple_testing = _write_multiple_testing(tmp_path, discovery)
    validation_floors = _write_validation_floors(tmp_path, discovery)
    gates = pd.read_parquet(validation_floors.candidate_gates_path).drop(columns=["exit_lab_gate_status"])
    gates.to_parquet(validation_floors.candidate_gates_path, index=False)
    manifest = json.loads(validation_floors.manifest_path.read_text(encoding="utf-8"))
    manifest["discovery_validation_floor_candidate_gates_sha256"] = _sha256(validation_floors.candidate_gates_path)
    validation_floors.manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    result = evaluate_discovery_candidate_pack_eligibility(
        discovery_manifest_path=discovery.manifest_path,
        cycle_manifest_path=cycle_manifest,
        exit_lab_manifest_path=exit_lab.manifest_path,
        multiple_testing_manifest_path=multiple_testing.manifest_path,
        validation_floors_manifest_path=validation_floors.manifest_path,
        candidate_id_map={"bridge-run-candidate-000001": "candidate-1"},
    )

    assert result.manifest["summary"]["eligible_count"] == 0
    assert "validation_floor_candidate_gates_schema_mismatch" in result.eligibility.loc[0, "bridge_reasons"]


def test_bridge_blocks_multiple_testing_gate_failures(tmp_path: Path) -> None:
    discovery = run_discovery(
        spec_path=_write_spec(tmp_path / "specs" / "discovery.json"),
        app_config=_app_config(tmp_path),
        clock=_clock,
    )
    cycle_manifest = _cycle_outputs(tmp_path / "cycle-fixture")
    exit_lab = _write_exit_lab(tmp_path, discovery)
    multiple_testing = _write_multiple_testing(tmp_path, discovery, blocked=True)

    result = evaluate_discovery_candidate_pack_eligibility(
        discovery_manifest_path=discovery.manifest_path,
        cycle_manifest_path=cycle_manifest,
        exit_lab_manifest_path=exit_lab.manifest_path,
        multiple_testing_manifest_path=multiple_testing.manifest_path,
        candidate_id_map={"bridge-run-candidate-000001": "candidate-1"},
    )

    reasons = result.eligibility.loc[0, "bridge_reasons"]
    assert result.manifest["summary"]["eligible_count"] == 0
    assert "multiple_testing_gate:sampled_fraction_below_candidate_ready_floor" in reasons
    assert "multiple_testing_gate:latest_window_only_evidence" in reasons


def test_bridge_blocks_multiple_testing_source_manifest_hash_mismatch(tmp_path: Path) -> None:
    discovery = run_discovery(
        spec_path=_write_spec(tmp_path / "specs" / "discovery.json"),
        app_config=_app_config(tmp_path),
        clock=_clock,
    )
    cycle_manifest = _cycle_outputs(tmp_path / "cycle-fixture")
    exit_lab = _write_exit_lab(tmp_path, discovery)
    multiple_testing = _write_multiple_testing(tmp_path, discovery)
    manifest = json.loads(multiple_testing.manifest_path.read_text(encoding="utf-8"))
    manifest["source_discovery_manifest_sha256"] = "wrong-source"
    multiple_testing.manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    result = evaluate_discovery_candidate_pack_eligibility(
        discovery_manifest_path=discovery.manifest_path,
        cycle_manifest_path=cycle_manifest,
        exit_lab_manifest_path=exit_lab.manifest_path,
        multiple_testing_manifest_path=multiple_testing.manifest_path,
        candidate_id_map={"bridge-run-candidate-000001": "candidate-1"},
    )

    assert result.manifest["summary"]["eligible_count"] == 0
    assert "multiple_testing_source_discovery_manifest_sha256_mismatch" in result.eligibility.loc[0, "bridge_reasons"]


def test_bridge_blocks_multiple_testing_candidate_record_hash_mismatch(tmp_path: Path) -> None:
    discovery = run_discovery(
        spec_path=_write_spec(tmp_path / "specs" / "discovery.json"),
        app_config=_app_config(tmp_path),
        clock=_clock,
    )
    cycle_manifest = _cycle_outputs(tmp_path / "cycle-fixture")
    exit_lab = _write_exit_lab(tmp_path, discovery)
    multiple_testing = _write_multiple_testing(tmp_path, discovery)
    gates = pd.read_parquet(multiple_testing.candidate_gates_path)
    gates.loc[0, "record_sha256"] = "wrong-record"
    gates.to_parquet(multiple_testing.candidate_gates_path, index=False)
    manifest = json.loads(multiple_testing.manifest_path.read_text(encoding="utf-8"))
    manifest["discovery_multiple_testing_candidate_gates_sha256"] = _sha256(multiple_testing.candidate_gates_path)
    multiple_testing.manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    result = evaluate_discovery_candidate_pack_eligibility(
        discovery_manifest_path=discovery.manifest_path,
        cycle_manifest_path=cycle_manifest,
        exit_lab_manifest_path=exit_lab.manifest_path,
        multiple_testing_manifest_path=multiple_testing.manifest_path,
        candidate_id_map={"bridge-run-candidate-000001": "candidate-1"},
    )

    assert result.manifest["summary"]["eligible_count"] == 0
    assert "multiple_testing_gate:record_sha256_mismatch" in result.eligibility.loc[0, "bridge_reasons"]


def test_bridge_blocks_exit_lab_entry_lead_hash_mismatch(tmp_path: Path) -> None:
    discovery = run_discovery(
        spec_path=_write_spec(tmp_path / "specs" / "discovery.json"),
        app_config=_app_config(tmp_path),
        clock=_clock,
    )
    cycle_manifest = _cycle_outputs(tmp_path / "cycle-fixture")
    exit_lab = _write_exit_lab(tmp_path, discovery, lead_hash="wrong-hash")

    result = evaluate_discovery_candidate_pack_eligibility(
        discovery_manifest_path=discovery.manifest_path,
        cycle_manifest_path=cycle_manifest,
        exit_lab_manifest_path=exit_lab.manifest_path,
        candidate_id_map={"bridge-run-candidate-000001": "candidate-1"},
    )

    assert result.manifest["summary"]["eligible_count"] == 0
    assert "exit_lab_entry_lead_hash_mismatch" in result.eligibility.loc[0, "bridge_reasons"]


def test_bridge_blocks_fixed_holding_only_exit_lab(tmp_path: Path) -> None:
    discovery = run_discovery(
        spec_path=_write_spec(tmp_path / "specs" / "discovery.json"),
        app_config=_app_config(tmp_path),
        clock=_clock,
    )
    cycle_manifest = _cycle_outputs(tmp_path / "cycle-fixture")
    exit_lab = _write_exit_lab(tmp_path, discovery, fixed_holding_only=True)

    result = evaluate_discovery_candidate_pack_eligibility(
        discovery_manifest_path=discovery.manifest_path,
        cycle_manifest_path=cycle_manifest,
        exit_lab_manifest_path=exit_lab.manifest_path,
        candidate_id_map={"bridge-run-candidate-000001": "candidate-1"},
    )

    assert result.manifest["summary"]["eligible_count"] == 0
    assert "exit_lab_gate:exit_lab_fixed_holding_only" in result.eligibility.loc[0, "bridge_reasons"]


def test_bridge_blocks_exit_lab_without_improving_exit(tmp_path: Path) -> None:
    discovery = run_discovery(
        spec_path=_write_spec(tmp_path / "specs" / "discovery.json"),
        app_config=_app_config(tmp_path),
        clock=_clock,
    )
    cycle_manifest = _cycle_outputs(tmp_path / "cycle-fixture")
    exit_lab = _write_exit_lab(tmp_path, discovery, treatment_score=0.10)

    result = evaluate_discovery_candidate_pack_eligibility(
        discovery_manifest_path=discovery.manifest_path,
        cycle_manifest_path=cycle_manifest,
        exit_lab_manifest_path=exit_lab.manifest_path,
        candidate_id_map={"bridge-run-candidate-000001": "candidate-1"},
    )

    assert result.manifest["summary"]["eligible_count"] == 0
    assert "exit_lab_gate:exit_lab_no_improving_exit_over_fixed_holding" in result.eligibility.loc[0, "bridge_reasons"]


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


def test_bridge_blocks_tampered_discovery_screen_score_v2(tmp_path: Path) -> None:
    discovery = run_discovery(
        spec_path=_write_spec(tmp_path / "specs" / "discovery.json"),
        app_config=_app_config(tmp_path),
        clock=_clock,
    )
    interesting = pd.read_parquet(discovery.interesting_candidates_path)
    interesting.loc[0, "discovery_screen_score_v2"] = 999.0
    interesting.to_parquet(discovery.interesting_candidates_path, index=False)
    cycle_manifest = _cycle_outputs(tmp_path / "cycle-fixture")

    result = evaluate_discovery_candidate_pack_eligibility(
        discovery_manifest_path=discovery.manifest_path,
        cycle_manifest_path=cycle_manifest,
        candidate_id_map={"bridge-run-candidate-000001": "candidate-1"},
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
    exit_lab = _write_exit_lab(tmp_path, discovery)
    multiple_testing = _write_multiple_testing(tmp_path, discovery)

    result = evaluate_discovery_candidate_pack_eligibility(
        discovery_manifest_path=discovery.manifest_path,
        cycle_manifest_path=cycle_manifest,
        exit_lab_manifest_path=exit_lab.manifest_path,
        multiple_testing_manifest_path=multiple_testing.manifest_path,
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
    exit_lab = _write_exit_lab(tmp_path, discovery)
    multiple_testing = _write_multiple_testing(tmp_path, discovery)
    validation_floors = _write_validation_floors(tmp_path, discovery)

    payload = _run_discovery_candidate_pack_bridge_command(
        Namespace(
            discovery_manifest=str(discovery.manifest_path),
            cycle_manifest=str(cycle_manifest),
            exit_lab_manifest=str(exit_lab.manifest_path),
            multiple_testing_manifest=str(multiple_testing.manifest_path),
            validation_floors_manifest=str(validation_floors.manifest_path),
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
    exit_lab = _write_exit_lab(tmp_path, discovery)
    multiple_testing = _write_multiple_testing(tmp_path, discovery)
    validation_floors = _write_validation_floors(tmp_path, discovery)

    payload = _run_discovery_candidate_pack_bridge_command(
        Namespace(
            discovery_manifest=str(discovery.manifest_path),
            cycle_manifest=str(cycle_manifest),
            exit_lab_manifest=str(exit_lab.manifest_path),
            multiple_testing_manifest=str(multiple_testing.manifest_path),
            validation_floors_manifest=str(validation_floors.manifest_path),
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
                exit_lab_manifest=None,
                multiple_testing_manifest=None,
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
