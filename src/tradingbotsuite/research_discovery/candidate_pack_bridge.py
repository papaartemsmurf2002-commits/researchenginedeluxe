from __future__ import annotations

import json
import numbers
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

import pandas as pd

from tradingbotsuite.data.historical_data_catalog import normalize_operator_run_artifact_paths
from tradingbotsuite.research.live_readiness import research_boundary_metadata
from tradingbotsuite.research_artifacts.candidate_pack import (
    build_research_candidate_gate_context,
    evaluate_research_candidate_gate_from_context,
)
from tradingbotsuite.research_discovery.exit_lab import (
    DISCOVERY_EXIT_LAB_MANIFEST_VERSION,
    discovery_entry_lead_evidence_sha256,
)
from tradingbotsuite.research_discovery.manifests import DISCOVERY_RUN_MANIFEST_VERSION
from tradingbotsuite.research_discovery.multiple_testing import DISCOVERY_MULTIPLE_TESTING_MANIFEST_VERSION
from tradingbotsuite.research_discovery.snapshots import atomic_write_json
from tradingbotsuite.research_discovery.state import read_trial_record
from tradingbotsuite.research_discovery.validation_floors import (
    DISCOVERY_VALIDATION_FLOORS_MANIFEST_VERSION,
    MATURITY_CANDIDATE_READY,
    blocker_registry_payload,
)


DISCOVERY_CANDIDATE_PACK_BRIDGE_VERSION = "discovery-candidate-pack-bridge-v1"
DISCOVERY_CANDIDATE_PACK_ELIGIBILITY_VERSION = "discovery-candidate-pack-eligibility-v1"
REJECTION_MARKDOWN_MAX_BLOCKED_ROWS = 250
FULL_TRIAL_RECORD_AUDIT_LIMIT = 10_000
TRIAL_RECORD_AUDIT_SAMPLE_SIZE = 256

LIVE_ADJACENT_VERSION_FIELDS = frozenset(
    {
        "promotion_candidate_manifest_version",
        "paper_run_manifest_version",
        "shadow_run_archive_manifest_version",
        "testnet_validation_manifest_version",
        "live_run_manifest_version",
    }
)
DISCOVERY_LEDGER_COLUMNS = (
    "run_id",
    "trial_id",
    "attempt_id",
    "trial_index",
    "candidate_id",
    "candidate_family",
    "ledger_kind",
    "score",
    "blocker_code",
    "filter_blocker_code",
    "research_only",
    "observe_only",
    "promotion_ready",
    "discovery_score_policy_version",
    "feature_column_set_id",
    "hmm_state_count",
    "regime_mode",
    "regime_detector_type",
    "regime_model_backend",
    "regime_gate_enabled",
    "same_regime_neighbor_pool_enabled",
    "true_hmm_backend_used",
    "label_horizon",
    "distance_metric",
    "k",
    "min_neighbor_count",
    "trade_count",
    "accepted_bar_count",
    "independent_event_count",
    "suppressed_overlap_count",
    "overlap_ratio",
    "event_signal_rate",
    "side_collapse_ratio",
    "near_signal_ceiling",
    "long_independent_event_count",
    "short_independent_event_count",
    "event_spacing_bars",
    "signal_rate",
    "realized_expectancy",
    "independent_event_expectancy",
    "accepted_prediction_count",
    "evaluated_prediction_count",
    "legacy_density_score",
    "discovery_screen_score_v2",
    "signal_rate_ceiling_penalty",
    "overlap_penalty",
    "side_collapse_penalty",
    "final_score",
    "record_sha256",
)


@dataclass(frozen=True, slots=True)
class DiscoveryCandidatePackBridgeResult:
    discovery_manifest_path: Path
    cycle_manifest_path: Path | None
    manifest: Mapping[str, Any]
    eligibility: pd.DataFrame
    rejections_markdown: str


@dataclass(frozen=True, slots=True)
class DiscoveryCandidatePackBridgeArtifactResult:
    output_dir: Path
    manifest_path: Path
    eligibility_path: Path
    rejections_path: Path


def evaluate_discovery_candidate_pack_eligibility(
    *,
    discovery_manifest_path: Path,
    cycle_manifest_path: Path | None = None,
    exit_lab_manifest_path: Path | None = None,
    multiple_testing_manifest_path: Path | None = None,
    validation_floors_manifest_path: Path | None = None,
    candidate_id_map: Mapping[str, str] | None = None,
) -> DiscoveryCandidatePackBridgeResult:
    discovery_manifest_path = Path(discovery_manifest_path).expanduser().resolve()
    cycle_manifest_resolved = Path(cycle_manifest_path).expanduser().resolve() if cycle_manifest_path is not None else None
    exit_lab_manifest_resolved = Path(exit_lab_manifest_path).expanduser().resolve() if exit_lab_manifest_path is not None else None
    multiple_testing_manifest_resolved = (
        Path(multiple_testing_manifest_path).expanduser().resolve() if multiple_testing_manifest_path is not None else None
    )
    validation_floors_manifest_resolved = (
        Path(validation_floors_manifest_path).expanduser().resolve() if validation_floors_manifest_path is not None else None
    )
    candidate_map = {str(key): str(value) for key, value in dict(candidate_id_map or {}).items()}
    manifest = _read_discovery_manifest(discovery_manifest_path)
    global_reasons = _discovery_manifest_reasons(manifest, discovery_manifest_path)
    exit_lab_manifest, exit_lab_candidate_gates, exit_lab_reasons = _exit_lab_evidence(exit_lab_manifest_resolved)
    multiple_testing_manifest, multiple_testing_gates, multiple_testing_reasons = _multiple_testing_evidence(
        multiple_testing_manifest_resolved,
        discovery_manifest_path=discovery_manifest_path,
    )
    validation_floors_manifest, validation_floor_gates, validation_floor_reasons = _validation_floor_evidence(
        validation_floors_manifest_resolved,
        discovery_manifest_path=discovery_manifest_path,
    )
    required_outputs = manifest.get("required_outputs") if isinstance(manifest.get("required_outputs"), Mapping) else {}
    state_payload = _read_required_json(required_outputs.get("run_state"), global_reasons, "run_state", normalize=False)
    if state_payload is not None:
        global_reasons.extend(_run_state_reasons(state_payload, required_outputs, manifest))
    interesting = _read_required_frame(required_outputs.get("interesting_candidates"), global_reasons, "interesting_candidates")
    blocked = _read_required_frame(required_outputs.get("blocked_candidates"), global_reasons, "blocked_candidates")
    filter_blockers = _read_required_frame(required_outputs.get("filter_blockers"), global_reasons, "filter_blockers")
    if state_payload is not None:
        global_reasons.extend(
            _ledger_integrity_reasons(
                state_payload=state_payload,
                required_outputs=required_outputs,
                interesting=interesting,
                blocked=blocked,
                filter_blockers=filter_blockers,
            )
        )

    rows: list[dict[str, Any]] = []
    gate_context = None
    if interesting is not None and not interesting.empty:
        blocked_ids = _candidate_ids(blocked)
        filter_blocked_ids = _candidate_ids(filter_blockers)
        exit_lab_entry_lookup, exit_lab_candidate_gate_lookup = _exit_lab_gate_lookups(exit_lab_candidate_gates)
        multiple_testing_gate_lookup = _candidate_gate_lookup(multiple_testing_gates)
        validation_floor_gate_lookup = _candidate_gate_lookup(validation_floor_gates)
        gate_context = (
            build_research_candidate_gate_context(cycle_manifest_path=cycle_manifest_resolved)
            if cycle_manifest_resolved is not None and cycle_manifest_resolved.exists()
            else None
        )
        for record in interesting.to_dict("records"):
            discovery_candidate_id = str(record.get("candidate_id") or "")
            research_candidate_id = candidate_map.get(discovery_candidate_id, discovery_candidate_id)
            reasons = list(global_reasons)
            if not discovery_candidate_id:
                reasons.append("discovery_candidate_id_required")
            if discovery_candidate_id in blocked_ids:
                reasons.append("candidate_present_in_blocked_candidates")
            if discovery_candidate_id in filter_blocked_ids:
                reasons.append("candidate_present_in_filter_blockers")
            exit_lab_gate = _exit_lab_gate_row_from_lookup(
                entry_candidate_lookup=exit_lab_entry_lookup,
                candidate_lookup=exit_lab_candidate_gate_lookup,
                discovery_candidate_id=discovery_candidate_id,
                research_candidate_id=research_candidate_id,
            )
            reasons.extend(exit_lab_reasons)
            reasons.extend(_exit_lab_gate_reasons(record, exit_lab_gate))
            multiple_testing_gate = _candidate_gate_row_from_lookup(
                multiple_testing_gate_lookup,
                discovery_candidate_id=discovery_candidate_id,
            )
            reasons.extend(multiple_testing_reasons)
            reasons.extend(_multiple_testing_gate_reasons(record, multiple_testing_gate))
            validation_floor_gate = _candidate_gate_row_from_lookup(
                validation_floor_gate_lookup,
                discovery_candidate_id=discovery_candidate_id,
            )
            reasons.extend(validation_floor_reasons)
            reasons.extend(_validation_floor_gate_reasons(record, validation_floor_gate))
            gate_status = "not_evaluated"
            gate_reasons: tuple[str, ...] = ()
            if cycle_manifest_resolved is None:
                reasons.append("historical_cycle_manifest_required")
            elif not cycle_manifest_resolved.exists():
                reasons.append("historical_cycle_manifest_missing")
            elif gate_context is None:
                reasons.append("historical_cycle_manifest_missing")
            else:
                gate = evaluate_research_candidate_gate_from_context(
                    context=gate_context,
                    candidate_id=research_candidate_id,
                )
                gate_status = gate.status
                gate_reasons = gate.reasons
                if not gate.passed:
                    reasons.extend(f"research_candidate_gate:{reason}" for reason in gate.reasons)
            reasons = list(dict.fromkeys(reasons))
            rows.append(
                {
                    "discovery_candidate_id": discovery_candidate_id,
                    "research_candidate_id": research_candidate_id,
                    "eligible_for_existing_candidate_pack_validator": bool(not reasons),
                    "bridge_status": "eligible" if not reasons else "blocked",
                    "bridge_reasons": "|".join(reasons),
                    "research_candidate_gate_status": gate_status,
                    "research_candidate_gate_reasons": "|".join(gate_reasons),
                    "exit_lab_status": _gate_text(exit_lab_gate, "exit_lab_status"),
                    "exit_lab_gate_status": _gate_text(exit_lab_gate, "exit_lab_gate_status"),
                    "exit_lab_reasons": _gate_text(exit_lab_gate, "exit_lab_reasons"),
                    "exit_lab_best_family": _gate_text(exit_lab_gate, "exit_lab_best_family"),
                    "exit_lab_best_comparison_id": _gate_text(exit_lab_gate, "best_comparison_id"),
                    "exit_lab_best_exit_policy_id": _gate_text(exit_lab_gate, "treatment_exit_policy_id"),
                    "exit_vs_fixed_final_score_delta": _gate_text(exit_lab_gate, "fixed_holding_score_delta"),
                    "exit_lab_cost_stress_status": _gate_text(exit_lab_gate, "cost_stress_status"),
                    "entry_lead_evidence_sha256": _gate_text(exit_lab_gate, "entry_lead_evidence_sha256"),
                    "exit_lab_no_improvement_reasons": _gate_text(exit_lab_gate, "no_improvement_reason"),
                    "multiple_testing_status": _gate_text(multiple_testing_gate, "multiple_testing_status"),
                    "multiple_testing_reasons": _gate_text(multiple_testing_gate, "multiple_testing_reasons"),
                    "multiple_testing_effective_trial_count": _gate_text(multiple_testing_gate, "effective_trial_count"),
                    "multiple_testing_sampled_fraction": _gate_text(multiple_testing_gate, "sampled_fraction"),
                    "multiple_testing_stability_neighborhood_size": _gate_text(
                        multiple_testing_gate,
                        "stability_neighborhood_size",
                    ),
                    "multiple_testing_latest_window_only_penalty": _gate_text(
                        multiple_testing_gate,
                        "latest_window_only_penalty",
                    ),
                    "validation_floor_status": _gate_text(validation_floor_gate, "validation_floor_status"),
                    "research_maturity": _gate_text(validation_floor_gate, "research_maturity"),
                    "validation_floor_reasons": _gate_text(validation_floor_gate, "validation_floor_reasons"),
                    "validation_floor_independent_event_count": _gate_text(
                        validation_floor_gate,
                        "independent_event_count",
                    ),
                    "validation_floor_overlap_ratio": _gate_text(validation_floor_gate, "overlap_ratio"),
                    "validation_floor_split_pass_ratio": _gate_text(validation_floor_gate, "split_pass_ratio"),
                    "validation_floor_side_concentration": _gate_text(validation_floor_gate, "side_concentration"),
                    "validation_floor_cost_stress_survival": _gate_text(validation_floor_gate, "cost_stress_survival"),
                    "validation_floor_stability_neighborhood_size": _gate_text(
                        validation_floor_gate,
                        "stability_neighborhood_size",
                    ),
                    "discovery_run_id": str(manifest.get("run_id") or ""),
                    "cycle_manifest_path": str(cycle_manifest_resolved) if cycle_manifest_resolved is not None else "",
                    "candidate_pack_written": False,
                    "candidate_pack_paths": "",
                    "research_only": True,
                    "observe_only": True,
                    "promotion_ready": False,
                }
            )
    eligibility = pd.DataFrame(rows, columns=_eligibility_columns())
    reason_counts = _reason_counts(eligibility)
    candidate_universe_alignment = _candidate_universe_alignment(
        eligibility,
        gate_context=gate_context,
        candidate_id_map=candidate_map,
    )
    summary = _summary(
        eligibility,
        global_reasons,
        reason_counts=reason_counts,
        candidate_universe_alignment=candidate_universe_alignment,
    )
    bridge_manifest = {
        "discovery_candidate_pack_bridge_version": DISCOVERY_CANDIDATE_PACK_BRIDGE_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "bridge_scope": "discovery_to_existing_research_candidate_pack_validator_eligibility_only",
        "claim_scope": "audit_only_no_pack_write_no_live_or_promotion_claim",
        "source_discovery_manifest_path": str(discovery_manifest_path),
        "source_discovery_manifest_sha256": _file_sha256(discovery_manifest_path) if discovery_manifest_path.exists() else None,
        "source_cycle_manifest_path": str(cycle_manifest_resolved) if cycle_manifest_resolved is not None else None,
        "source_cycle_manifest_sha256": (
            _file_sha256(cycle_manifest_resolved)
            if cycle_manifest_resolved is not None and cycle_manifest_resolved.exists()
            else None
        ),
        "source_exit_lab_manifest_path": str(exit_lab_manifest_resolved) if exit_lab_manifest_resolved is not None else None,
        "source_exit_lab_manifest_sha256": (
            _file_sha256(exit_lab_manifest_resolved)
            if exit_lab_manifest_resolved is not None and exit_lab_manifest_resolved.exists()
            else None
        ),
        "exit_lab_gate_required": True,
        "exit_lab_candidate_gates_sha256": (
            str(exit_lab_manifest.get("discovery_exit_lab_candidate_gates_sha256") or "")
            if exit_lab_manifest is not None
            else ""
        ),
        "exit_lab_summary": _exit_lab_summary(exit_lab_candidate_gates, exit_lab_reasons),
        "source_multiple_testing_manifest_path": (
            str(multiple_testing_manifest_resolved) if multiple_testing_manifest_resolved is not None else None
        ),
        "source_multiple_testing_manifest_sha256": (
            _file_sha256(multiple_testing_manifest_resolved)
            if multiple_testing_manifest_resolved is not None and multiple_testing_manifest_resolved.exists()
            else None
        ),
        "multiple_testing_gate_required": True,
        "multiple_testing_candidate_gates_sha256": (
            str(multiple_testing_manifest.get("discovery_multiple_testing_candidate_gates_sha256") or "")
            if multiple_testing_manifest is not None
            else ""
        ),
        "multiple_testing_summary": _multiple_testing_summary(multiple_testing_gates, multiple_testing_reasons),
        "source_validation_floors_manifest_path": (
            str(validation_floors_manifest_resolved) if validation_floors_manifest_resolved is not None else None
        ),
        "source_validation_floors_manifest_sha256": (
            _file_sha256(validation_floors_manifest_resolved)
            if validation_floors_manifest_resolved is not None and validation_floors_manifest_resolved.exists()
            else None
        ),
        "validation_floor_gate_required": True,
        "validation_floor_candidate_gates_sha256": (
            str(validation_floors_manifest.get("discovery_validation_floor_candidate_gates_sha256") or "")
            if validation_floors_manifest is not None
            else ""
        ),
        "validation_floor_summary": _validation_floor_summary(validation_floor_gates, validation_floor_reasons),
        "validation_blocker_registry_sha256": (
            str(validation_floors_manifest.get("blocker_registry_sha256") or "")
            if validation_floors_manifest is not None
            else ""
        ),
        "experiment_budget_ledger": (
            dict(validation_floors_manifest.get("experiment_budget_ledger") or {})
            if validation_floors_manifest is not None
            else {}
        ),
        "candidate_id_map": candidate_map,
        "candidate_universe_alignment": candidate_universe_alignment,
        "reason_counts": reason_counts,
        "summary": summary,
        "global_reasons": list(dict.fromkeys(global_reasons)),
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
        "live_fetch_used": False,
        "order_placement_used": False,
        "runtime_mode_changed": False,
        "required_outputs": {},
    }
    validation_reasons = validate_discovery_candidate_pack_bridge_manifest(bridge_manifest)
    if validation_reasons:
        raise ValueError("invalid discovery candidate pack bridge manifest: " + "|".join(validation_reasons))
    return DiscoveryCandidatePackBridgeResult(
        discovery_manifest_path=discovery_manifest_path,
        cycle_manifest_path=cycle_manifest_resolved,
        manifest=bridge_manifest,
        eligibility=eligibility,
        rejections_markdown=_rejections_markdown(eligibility, global_reasons),
    )


def write_discovery_candidate_pack_eligibility(
    *,
    output_dir: Path,
    result: DiscoveryCandidatePackBridgeResult,
) -> DiscoveryCandidatePackBridgeArtifactResult:
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "candidate_pack_eligibility_manifest.json"
    eligibility_path = output_dir / "candidate_pack_eligibility.parquet"
    rejections_path = output_dir / "candidate_pack_bridge_rejections.md"
    _assert_new_artifact_paths(manifest_path, eligibility_path, rejections_path)
    _atomic_write_parquet(result.eligibility, eligibility_path)
    _atomic_write_text(rejections_path, result.rejections_markdown)
    manifest = dict(result.manifest)
    manifest["eligibility_artifact_version"] = DISCOVERY_CANDIDATE_PACK_ELIGIBILITY_VERSION
    manifest["required_outputs"] = {
        "candidate_pack_eligibility_manifest": str(manifest_path),
        "candidate_pack_eligibility": str(eligibility_path),
        "candidate_pack_bridge_rejections": str(rejections_path),
    }
    manifest["candidate_pack_eligibility_sha256"] = _file_sha256(eligibility_path)
    manifest["candidate_pack_bridge_rejections_sha256"] = _file_sha256(rejections_path)
    validation_reasons = validate_discovery_candidate_pack_bridge_manifest(manifest)
    if validation_reasons:
        raise ValueError("invalid discovery candidate pack bridge manifest: " + "|".join(validation_reasons))
    atomic_write_json(manifest_path, manifest)
    return DiscoveryCandidatePackBridgeArtifactResult(
        output_dir=output_dir,
        manifest_path=manifest_path,
        eligibility_path=eligibility_path,
        rejections_path=rejections_path,
    )


def validate_discovery_candidate_pack_bridge_manifest(manifest: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if manifest.get("discovery_candidate_pack_bridge_version") != DISCOVERY_CANDIDATE_PACK_BRIDGE_VERSION:
        reasons.append("discovery_candidate_pack_bridge_version_required")
    if manifest.get("research_only") is not True:
        reasons.append("research_only_must_be_true")
    if manifest.get("observe_only") is not True:
        reasons.append("observe_only_must_be_true")
    if manifest.get("promotion_ready") is not False:
        reasons.append("promotion_ready_must_be_false")
    for field in (
        "live_signal_input",
        "position_sizing_input",
        "operator_control_input",
        "live_execution_input",
        "runtime_control_input",
        "live_fetch_used",
        "order_placement_used",
        "runtime_mode_changed",
    ):
        if manifest.get(field) is not False:
            reasons.append(f"{field}_must_be_false")
    if manifest.get("candidate_pack_written") is not False:
        reasons.append("candidate_pack_written_must_be_false")
    if list(manifest.get("candidate_pack_paths") or []) != []:
        reasons.append("candidate_pack_paths_must_be_empty")
    if manifest.get("exit_lab_gate_required") is not True:
        reasons.append("exit_lab_gate_required_must_be_true")
    if manifest.get("multiple_testing_gate_required") is not True:
        reasons.append("multiple_testing_gate_required_must_be_true")
    if manifest.get("validation_floor_gate_required") is not True:
        reasons.append("validation_floor_gate_required_must_be_true")
    if any(field in manifest for field in LIVE_ADJACENT_VERSION_FIELDS):
        reasons.append("live_or_promotion_manifest_version_forbidden")
    return reasons


def _discovery_manifest_reasons(manifest: Mapping[str, Any], path: Path) -> list[str]:
    reasons: list[str] = []
    if manifest.get("discovery_run_manifest_version") != DISCOVERY_RUN_MANIFEST_VERSION:
        reasons.append("discovery_run_manifest_version_required")
    reasons.extend(_research_boundary_reasons(manifest, "discovery_manifest"))
    reasons.extend(_replay_bridge_requirement_reasons(manifest, "discovery_manifest", anchor_dir=path.parent))
    if manifest.get("candidate_pack_written") is not False:
        reasons.append("discovery_manifest_candidate_pack_written_must_be_false")
    if list(manifest.get("candidate_pack_paths") or []) != []:
        reasons.append("discovery_manifest_candidate_pack_paths_must_be_empty")
    if not path.exists():
        reasons.append("discovery_manifest_missing")
    required_outputs = manifest.get("required_outputs")
    if not isinstance(required_outputs, Mapping):
        reasons.append("discovery_manifest_required_outputs_required")
    return reasons


def _run_state_reasons(
    state_payload: Mapping[str, Any],
    required_outputs: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> list[str]:
    reasons: list[str] = []
    reasons.extend(_research_boundary_reasons(state_payload, "run_state"))
    manifest_state = manifest.get("state")
    if not isinstance(manifest_state, Mapping):
        reasons.append("discovery_manifest_embedded_state_required")
    elif dict(manifest_state) != dict(state_payload):
        reasons.append("discovery_run_state_manifest_state_mismatch")
    if state_payload.get("status") != "completed":
        reasons.append("discovery_run_state_must_be_completed")
    if str(state_payload.get("run_id") or "") != str(manifest.get("run_id") or ""):
        reasons.append("discovery_run_state_run_id_mismatch")
    completed_ids = [str(item) for item in state_payload.get("completed_trial_ids") or []]
    counts = manifest.get("counts") if isinstance(manifest.get("counts"), Mapping) else {}
    manifest_completed = counts.get("completed_trials")
    if manifest_completed is not None and int(manifest_completed) != len(completed_ids):
        reasons.append("discovery_manifest_completed_trial_count_mismatch")
    expected_trials = _expected_trial_count(required_outputs, reasons)
    if state_payload.get("status") == "completed" and expected_trials is not None and len(completed_ids) != expected_trials:
        reasons.append("discovery_completed_trial_count_mismatch")
    trials_dir_raw = required_outputs.get("trials")
    if not trials_dir_raw:
        reasons.append("discovery_trials_dir_required")
        return reasons
    trials_dir = Path(str(trials_dir_raw))
    if not trials_dir.exists():
        reasons.append("discovery_trials_dir_missing")
        return reasons
    hashes = dict(state_payload.get("completed_trial_hashes") or {})
    for trial_id in _trial_ids_for_integrity_audit(completed_ids):
        trial_path = trials_dir / f"{trial_id}.json"
        if not trial_path.exists():
            reasons.append(f"discovery_trial_record_missing:{trial_id}")
            continue
        try:
            record = read_trial_record(trial_path)
        except ValueError as exc:
            message = str(exc)
            if "boundary violation" in message:
                reasons.append(f"discovery_trial_record_boundary_violation:{trial_id}")
            else:
                reasons.append(f"discovery_trial_record_hash_mismatch:{trial_id}")
            continue
        expected_hash = str(hashes.get(trial_id) or "")
        actual_hash = str(record.to_payload().get("record_sha256") or "")
        if not expected_hash:
            reasons.append(f"discovery_trial_state_hash_required:{trial_id}")
        elif expected_hash != actual_hash:
            reasons.append(f"discovery_trial_state_hash_mismatch:{trial_id}")
        if record.status != "completed":
            reasons.append(f"discovery_trial_status_not_completed:{trial_id}")
    return reasons


def _ledger_integrity_reasons(
    *,
    state_payload: Mapping[str, Any],
    required_outputs: Mapping[str, Any],
    interesting: pd.DataFrame | None,
    blocked: pd.DataFrame | None,
    filter_blockers: pd.DataFrame | None,
) -> list[str]:
    reasons: list[str] = []
    trials_dir_raw = required_outputs.get("trials")
    if not trials_dir_raw:
        return reasons
    trials_dir = Path(str(trials_dir_raw))
    completed_ids = [str(item) for item in state_payload.get("completed_trial_ids") or []]
    if len(completed_ids) > FULL_TRIAL_RECORD_AUDIT_LIMIT:
        return _sampled_ledger_integrity_reasons(
            state_payload=state_payload,
            trials_dir=trials_dir,
            completed_ids=completed_ids,
            interesting=interesting,
            blocked=blocked,
            filter_blockers=filter_blockers,
        )
    expected_by_name = {
        "interesting_candidates": [],
        "blocked_candidates": [],
        "filter_blockers": [],
    }
    ledger_name_by_kind = {
        "interesting": "interesting_candidates",
        "blocked": "blocked_candidates",
        "filter_blocked": "filter_blockers",
    }
    for trial_id in completed_ids:
        trial_path = trials_dir / f"{trial_id}.json"
        if not trial_path.exists():
            continue
        try:
            record = read_trial_record(trial_path)
        except ValueError:
            continue
        ledger_name = ledger_name_by_kind.get(record.ledger_kind)
        if ledger_name is None:
            reasons.append(f"discovery_trial_record_unknown_ledger_kind:{trial_id}:{record.ledger_kind}")
            continue
        payload = record.to_payload()
        trial_payload = payload.get("payload") if isinstance(payload.get("payload"), Mapping) else {}
        expected_by_name[ledger_name].append(
            {column: payload.get(column, trial_payload.get(column, "")) for column in DISCOVERY_LEDGER_COLUMNS}
        )
    for name, frame in {
        "interesting_candidates": interesting,
        "blocked_candidates": blocked,
        "filter_blockers": filter_blockers,
    }.items():
        if frame is None:
            continue
        normalized_frame, schema_reasons = _ledger_frame_for_integrity(frame, ledger_name=name)
        if schema_reasons:
            reasons.extend(schema_reasons)
            continue
        expected = _normalized_ledger_rows(pd.DataFrame(expected_by_name[name], columns=list(DISCOVERY_LEDGER_COLUMNS)))
        actual = _normalized_ledger_rows(normalized_frame)
        if actual != expected:
            reasons.append(f"discovery_ledger_records_mismatch:{name}")
    return reasons


def _sampled_ledger_integrity_reasons(
    *,
    state_payload: Mapping[str, Any],
    trials_dir: Path,
    completed_ids: list[str],
    interesting: pd.DataFrame | None,
    blocked: pd.DataFrame | None,
    filter_blockers: pd.DataFrame | None,
) -> list[str]:
    reasons: list[str] = []
    frames: list[pd.DataFrame] = []
    for name, frame in {
        "interesting_candidates": interesting,
        "blocked_candidates": blocked,
        "filter_blockers": filter_blockers,
    }.items():
        if frame is None:
            continue
        normalized_frame, schema_reasons = _ledger_frame_for_integrity(frame, ledger_name=name)
        if schema_reasons:
            reasons.extend(schema_reasons)
            continue
        if not normalized_frame.empty:
            frames.append(normalized_frame)
    if not frames:
        if completed_ids:
            reasons.append("discovery_ledger_records_missing")
        return reasons

    combined = pd.concat(frames, ignore_index=True)
    trial_ids = combined["trial_id"].astype(str)
    if len(combined) != len(completed_ids):
        reasons.append("discovery_ledger_record_count_mismatch")
    if trial_ids.duplicated().any():
        reasons.append("discovery_ledger_trial_id_duplicates")
    completed_id_set = set(completed_ids)
    ledger_id_set = set(trial_ids.tolist())
    if ledger_id_set - completed_id_set:
        reasons.append("discovery_ledger_unknown_completed_trial_ids")
    if completed_id_set - ledger_id_set:
        reasons.append("discovery_ledger_missing_completed_trial_ids")

    state_hashes = {str(key): str(value) for key, value in dict(state_payload.get("completed_trial_hashes") or {}).items()}
    expected_hashes = trial_ids.map(state_hashes).fillna("")
    actual_hashes = combined["record_sha256"].astype(str)
    if bool((expected_hashes == "").any()):
        reasons.append("discovery_ledger_state_hashes_missing")
    if bool((actual_hashes != expected_hashes).any()):
        reasons.append("discovery_ledger_record_state_hash_mismatch")

    sample_ids = _trial_ids_for_integrity_audit(completed_ids)
    sample = combined.loc[trial_ids.isin(set(sample_ids))].copy()
    for trial_id in sample_ids:
        trial_path = trials_dir / f"{trial_id}.json"
        if not trial_path.exists():
            reasons.append(f"discovery_trial_record_missing:{trial_id}")
            continue
        try:
            record = read_trial_record(trial_path)
        except ValueError as exc:
            message = str(exc)
            if "boundary violation" in message:
                reasons.append(f"discovery_trial_record_boundary_violation:{trial_id}")
            else:
                reasons.append(f"discovery_trial_record_hash_mismatch:{trial_id}")
            continue
        expected = _normalized_ledger_rows(
            pd.DataFrame([_ledger_row_from_trial_record(record)], columns=list(DISCOVERY_LEDGER_COLUMNS))
        )
        actual_rows = sample.loc[sample["trial_id"].astype(str) == trial_id]
        actual = _normalized_ledger_rows(actual_rows)
        if actual != expected:
            reasons.append(f"discovery_ledger_sample_record_mismatch:{trial_id}")
    return list(dict.fromkeys(reasons))


def _ledger_frame_for_integrity(frame: pd.DataFrame, *, ledger_name: str) -> tuple[pd.DataFrame, list[str]]:
    required_identity_columns = {"trial_id", "candidate_id", "record_sha256"}
    if not required_identity_columns.issubset(set(frame.columns)):
        return frame, [f"discovery_ledger_schema_mismatch:{ledger_name}"]
    normalized = pd.DataFrame(index=frame.index)
    for column in DISCOVERY_LEDGER_COLUMNS:
        if column in frame.columns:
            normalized[column] = frame[column]
        else:
            normalized[column] = _ledger_column_default(column, ledger_name=ledger_name)
    return normalized.loc[:, list(DISCOVERY_LEDGER_COLUMNS)], []


def _ledger_column_default(column: str, *, ledger_name: str) -> Any:
    if column == "ledger_kind":
        return {
            "interesting_candidates": "interesting",
            "blocked_candidates": "blocked",
            "filter_blockers": "filter_blocked",
        }.get(ledger_name, "")
    if column == "research_only":
        return True
    if column == "observe_only":
        return True
    if column == "promotion_ready":
        return False
    if column in {
        "trial_index",
        "hmm_state_count",
        "k",
        "min_neighbor_count",
        "trade_count",
        "accepted_bar_count",
        "independent_event_count",
        "suppressed_overlap_count",
        "long_independent_event_count",
        "short_independent_event_count",
        "event_spacing_bars",
        "accepted_prediction_count",
        "evaluated_prediction_count",
    }:
        return 0
    if column in {
        "score",
        "overlap_ratio",
        "event_signal_rate",
        "side_collapse_ratio",
        "signal_rate",
        "realized_expectancy",
        "independent_event_expectancy",
        "legacy_density_score",
        "discovery_screen_score_v2",
        "signal_rate_ceiling_penalty",
        "overlap_penalty",
        "side_collapse_penalty",
        "final_score",
    }:
        return 0.0
    if column in {
        "regime_gate_enabled",
        "same_regime_neighbor_pool_enabled",
        "true_hmm_backend_used",
        "near_signal_ceiling",
    }:
        return False
    return ""


def _ledger_row_from_trial_record(record: Any) -> dict[str, Any]:
    payload = record.to_payload()
    trial_payload = payload.get("payload") if isinstance(payload.get("payload"), Mapping) else {}
    return {column: payload.get(column, trial_payload.get(column, "")) for column in DISCOVERY_LEDGER_COLUMNS}


def _trial_ids_for_integrity_audit(completed_ids: list[str]) -> list[str]:
    if len(completed_ids) <= FULL_TRIAL_RECORD_AUDIT_LIMIT:
        return completed_ids
    if not completed_ids:
        return []
    if TRIAL_RECORD_AUDIT_SAMPLE_SIZE <= 0:
        return []
    sample_size = min(TRIAL_RECORD_AUDIT_SAMPLE_SIZE, len(completed_ids))
    if sample_size == len(completed_ids):
        return completed_ids
    if sample_size == 1:
        return [completed_ids[0]]
    indexes = {
        round(index * (len(completed_ids) - 1) / (sample_size - 1))
        for index in range(sample_size)
    }
    return [completed_ids[index] for index in sorted(indexes)]


def _expected_trial_count(required_outputs: Mapping[str, Any], reasons: list[str]) -> int | None:
    resolved_spec_raw = required_outputs.get("discovery_spec_resolved")
    if not resolved_spec_raw:
        reasons.append("discovery_resolved_spec_path_required")
        return None
    resolved_spec_path = Path(str(resolved_spec_raw))
    if not resolved_spec_path.exists():
        reasons.append("discovery_resolved_spec_path_missing")
        return None
    try:
        payload = _read_json(resolved_spec_path)
    except ValueError:
        reasons.append("discovery_resolved_spec_invalid_json")
        return None
    budget = payload.get("budget") if isinstance(payload.get("budget"), Mapping) else {}
    max_trials = int(budget.get("max_trials") or 0)
    templates = payload.get("trial_templates") if isinstance(payload.get("trial_templates"), list) else []
    return min(max_trials, len(templates)) if templates else max_trials


def _read_required_json(raw_path: Any, reasons: list[str], name: str, *, normalize: bool = True) -> dict[str, Any] | None:
    if not raw_path:
        reasons.append(f"{name}_path_required")
        return None
    path = Path(str(raw_path))
    if not path.exists():
        reasons.append(f"{name}_path_missing")
        return None
    try:
        payload = _read_json(path) if normalize else _read_json_raw(path)
    except ValueError:
        reasons.append(f"{name}_invalid_json")
        return None
    return payload


def _read_required_frame(raw_path: Any, reasons: list[str], name: str) -> pd.DataFrame | None:
    if not raw_path:
        reasons.append(f"{name}_path_required")
        return None
    path = Path(str(raw_path))
    if not path.exists():
        reasons.append(f"{name}_path_missing")
        return None
    try:
        return pd.read_parquet(path)
    except Exception:
        reasons.append(f"{name}_invalid_parquet")
        return None


def _exit_lab_evidence(path: Path | None) -> tuple[dict[str, Any] | None, pd.DataFrame | None, list[str]]:
    reasons: list[str] = []
    if path is None:
        return None, None, ["exit_lab_manifest_required"]
    if not path.exists():
        return None, None, ["exit_lab_manifest_missing"]
    try:
        manifest = _read_json(path)
    except ValueError:
        return None, None, ["exit_lab_manifest_invalid_json"]
    reasons.extend(_research_boundary_reasons(manifest, "exit_lab_manifest"))
    if manifest.get("exit_lab_manifest_version") != DISCOVERY_EXIT_LAB_MANIFEST_VERSION:
        reasons.append("exit_lab_manifest_version_required")
    required_outputs = manifest.get("required_outputs") if isinstance(manifest.get("required_outputs"), Mapping) else {}
    raw_path = required_outputs.get("discovery_exit_lab_candidate_gates")
    if not raw_path:
        reasons.append("exit_lab_candidate_gates_required")
        return manifest, None, reasons
    gate_path = Path(str(raw_path))
    if not gate_path.exists():
        reasons.append("exit_lab_candidate_gates_missing")
        return manifest, None, reasons
    expected_sha = str(manifest.get("discovery_exit_lab_candidate_gates_sha256") or "")
    if expected_sha and expected_sha != _file_sha256(gate_path):
        reasons.append("exit_lab_candidate_gates_sha256_mismatch")
    try:
        gates = pd.read_parquet(gate_path)
    except Exception:
        reasons.append("exit_lab_candidate_gates_invalid_parquet")
        return manifest, None, reasons
    reasons.extend(_exit_lab_candidate_gate_reasons(gates))
    return manifest, gates, reasons


def _multiple_testing_evidence(
    path: Path | None,
    *,
    discovery_manifest_path: Path,
) -> tuple[dict[str, Any] | None, pd.DataFrame | None, list[str]]:
    reasons: list[str] = []
    if path is None:
        return None, None, ["multiple_testing_manifest_required"]
    if not path.exists():
        return None, None, ["multiple_testing_manifest_missing"]
    try:
        manifest = _read_json(path)
    except ValueError:
        return None, None, ["multiple_testing_manifest_invalid_json"]
    reasons.extend(_research_boundary_reasons(manifest, "multiple_testing_manifest"))
    if manifest.get("multiple_testing_manifest_version") != DISCOVERY_MULTIPLE_TESTING_MANIFEST_VERSION:
        reasons.append("multiple_testing_manifest_version_required")
    expected_source_sha = str(manifest.get("source_discovery_manifest_sha256") or "")
    actual_source_sha = _file_sha256(discovery_manifest_path) if discovery_manifest_path.exists() else ""
    if expected_source_sha and expected_source_sha != actual_source_sha:
        reasons.append("multiple_testing_source_discovery_manifest_sha256_mismatch")
    required_outputs = manifest.get("required_outputs") if isinstance(manifest.get("required_outputs"), Mapping) else {}
    raw_path = required_outputs.get("discovery_multiple_testing_candidate_gates")
    if not raw_path:
        reasons.append("multiple_testing_candidate_gates_required")
        return manifest, None, reasons
    gate_path = Path(str(raw_path))
    if not gate_path.exists():
        reasons.append("multiple_testing_candidate_gates_missing")
        return manifest, None, reasons
    expected_sha = str(manifest.get("discovery_multiple_testing_candidate_gates_sha256") or "")
    if expected_sha and expected_sha != _file_sha256(gate_path):
        reasons.append("multiple_testing_candidate_gates_sha256_mismatch")
    try:
        gates = pd.read_parquet(gate_path)
    except Exception:
        reasons.append("multiple_testing_candidate_gates_invalid_parquet")
        return manifest, None, reasons
    reasons.extend(_multiple_testing_candidate_gate_reasons(gates))
    return manifest, gates, reasons


def _validation_floor_evidence(
    path: Path | None,
    *,
    discovery_manifest_path: Path,
) -> tuple[dict[str, Any] | None, pd.DataFrame | None, list[str]]:
    reasons: list[str] = []
    if path is None:
        return None, None, ["validation_floor_manifest_required"]
    if not path.exists():
        return None, None, ["validation_floor_manifest_missing"]
    try:
        manifest = _read_json(path)
    except ValueError:
        return None, None, ["validation_floor_manifest_invalid_json"]
    reasons.extend(_research_boundary_reasons(manifest, "validation_floor_manifest"))
    if manifest.get("validation_floors_manifest_version") != DISCOVERY_VALIDATION_FLOORS_MANIFEST_VERSION:
        reasons.append("validation_floor_manifest_version_required")
    registry = manifest.get("blocker_registry")
    expected_registry = blocker_registry_payload()
    if not isinstance(registry, Mapping):
        reasons.append("validation_floor_blocker_registry_required")
    else:
        registry_hash = str(manifest.get("blocker_registry_sha256") or "")
        if not registry_hash:
            reasons.append("validation_floor_blocker_registry_sha256_required")
        elif registry_hash != _stable_payload_sha256(registry):
            reasons.append("validation_floor_blocker_registry_sha256_mismatch")
        if dict(registry) != expected_registry:
            reasons.append("validation_floor_blocker_registry_payload_mismatch")
    expected_source_sha = str(manifest.get("source_discovery_manifest_sha256") or "")
    actual_source_sha = _file_sha256(discovery_manifest_path) if discovery_manifest_path.exists() else ""
    if expected_source_sha and expected_source_sha != actual_source_sha:
        reasons.append("validation_floor_source_discovery_manifest_sha256_mismatch")
    required_outputs = manifest.get("required_outputs") if isinstance(manifest.get("required_outputs"), Mapping) else {}
    raw_path = required_outputs.get("discovery_validation_floor_candidate_gates")
    if not raw_path:
        reasons.append("validation_floor_candidate_gates_required")
        return manifest, None, reasons
    gate_path = Path(str(raw_path))
    if not gate_path.exists():
        reasons.append("validation_floor_candidate_gates_missing")
        return manifest, None, reasons
    expected_sha = str(manifest.get("discovery_validation_floor_candidate_gates_sha256") or "")
    if expected_sha and expected_sha != _file_sha256(gate_path):
        reasons.append("validation_floor_candidate_gates_sha256_mismatch")
    try:
        gates = pd.read_parquet(gate_path)
    except Exception:
        reasons.append("validation_floor_candidate_gates_invalid_parquet")
        return manifest, None, reasons
    reasons.extend(_validation_floor_candidate_gate_reasons(gates))
    return manifest, gates, reasons


def _multiple_testing_candidate_gate_reasons(frame: pd.DataFrame) -> list[str]:
    required = {
        "candidate_id",
        "record_sha256",
        "multiple_testing_status",
        "multiple_testing_reasons",
        "research_only",
        "observe_only",
        "promotion_ready",
    }
    if not required.issubset(set(frame.columns)):
        return ["multiple_testing_candidate_gates_schema_mismatch"]
    reasons: list[str] = []
    for column, expected, reason in (
        ("research_only", True, "multiple_testing_candidate_gates_research_only_required"),
        ("observe_only", True, "multiple_testing_candidate_gates_observe_only_required"),
        ("promotion_ready", False, "multiple_testing_candidate_gates_promotion_ready_must_be_false"),
    ):
        if not frame[column].map(lambda value: bool(value) is expected).all():
            reasons.append(reason)
    return reasons


def _validation_floor_candidate_gate_reasons(frame: pd.DataFrame) -> list[str]:
    required = {
        "candidate_id",
        "record_sha256",
        "validation_floor_status",
        "research_maturity",
        "validation_floor_reasons",
        "exit_lab_gate_status",
        "research_only",
        "observe_only",
        "promotion_ready",
    }
    if not required.issubset(set(frame.columns)):
        return ["validation_floor_candidate_gates_schema_mismatch"]
    reasons: list[str] = []
    for column, expected, reason in (
        ("research_only", True, "validation_floor_candidate_gates_research_only_required"),
        ("observe_only", True, "validation_floor_candidate_gates_observe_only_required"),
        ("promotion_ready", False, "validation_floor_candidate_gates_promotion_ready_must_be_false"),
    ):
        if not frame[column].map(lambda value: bool(value) is expected).all():
            reasons.append(reason)
    return reasons


def _exit_lab_candidate_gate_reasons(frame: pd.DataFrame) -> list[str]:
    reasons: list[str] = []
    required = {
        "entry_candidate_id",
        "candidate_id",
        "entry_lead_evidence_sha256",
        "exit_lab_status",
        "exit_lab_gate_status",
        "exit_lab_best_family",
        "research_only",
        "observe_only",
        "promotion_ready",
    }
    if not required.issubset(set(frame.columns)):
        return ["exit_lab_candidate_gates_schema_mismatch"]
    for column, expected, reason in (
        ("research_only", True, "exit_lab_candidate_gates_research_only_required"),
        ("observe_only", True, "exit_lab_candidate_gates_observe_only_required"),
        ("promotion_ready", False, "exit_lab_candidate_gates_promotion_ready_must_be_false"),
    ):
        if not frame[column].map(lambda value: bool(value) is expected).all():
            reasons.append(reason)
    return reasons


def _exit_lab_gate_lookups(
    gates: pd.DataFrame | None,
) -> tuple[dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    if gates is None or gates.empty:
        return {}, {}
    entry_lookup = _candidate_gate_lookup(gates, candidate_id_column="entry_candidate_id")
    candidate_lookup = _candidate_gate_lookup(gates, candidate_id_column="candidate_id")
    return entry_lookup, candidate_lookup


def _candidate_gate_lookup(
    gates: pd.DataFrame | None,
    *,
    candidate_id_column: str = "candidate_id",
) -> dict[str, Mapping[str, Any]]:
    if gates is None or gates.empty or candidate_id_column not in gates.columns:
        return {}
    frame = gates.copy()
    if candidate_id_column == "entry_candidate_id":
        sort_columns = [column for column in ("exit_lab_gate_status", "fixed_holding_score_delta") if column in frame.columns]
        if sort_columns:
            frame = frame.sort_values(sort_columns, ascending=[False] * len(sort_columns), kind="mergesort")
    rows: dict[str, Mapping[str, Any]] = {}
    for record in frame.to_dict("records"):
        candidate_id = str(record.get(candidate_id_column) or "")
        if candidate_id and candidate_id not in rows:
            rows[candidate_id] = record
    return rows


def _exit_lab_gate_row_from_lookup(
    *,
    entry_candidate_lookup: Mapping[str, Mapping[str, Any]],
    candidate_lookup: Mapping[str, Mapping[str, Any]],
    discovery_candidate_id: str,
    research_candidate_id: str,
) -> Mapping[str, Any] | None:
    return entry_candidate_lookup.get(discovery_candidate_id) or candidate_lookup.get(research_candidate_id)


def _candidate_gate_row_from_lookup(
    gate_lookup: Mapping[str, Mapping[str, Any]],
    *,
    discovery_candidate_id: str,
) -> Mapping[str, Any] | None:
    return gate_lookup.get(discovery_candidate_id)


def _exit_lab_gate_row(
    gates: pd.DataFrame | None,
    *,
    discovery_candidate_id: str,
    research_candidate_id: str,
) -> Mapping[str, Any] | None:
    entry_lookup, candidate_lookup = _exit_lab_gate_lookups(gates)
    return _exit_lab_gate_row_from_lookup(
        entry_candidate_lookup=entry_lookup,
        candidate_lookup=candidate_lookup,
        discovery_candidate_id=discovery_candidate_id,
        research_candidate_id=research_candidate_id,
    )


def _exit_lab_gate_reasons(record: Mapping[str, Any], gate: Mapping[str, Any] | None) -> list[str]:
    if gate is None:
        return ["exit_lab_candidate_gate_row_required"]
    reasons: list[str] = []
    expected_hash = discovery_entry_lead_evidence_sha256(record)
    gate_hash = _gate_text(gate, "entry_lead_evidence_sha256") or _gate_text(gate, "entry_lead_record_sha256")
    if gate_hash != expected_hash:
        reasons.append("exit_lab_entry_lead_hash_mismatch")
    status = _gate_text(gate, "exit_lab_status")
    if status != "complete":
        reasons.append("exit_lab_gate:exit_lab_status_not_complete")
    gate_status = _gate_text(gate, "exit_lab_gate_status")
    best_family = _gate_text(gate, "exit_lab_best_family")
    gate_reasons = [reason for reason in _gate_text(gate, "exit_lab_reasons").split("|") if reason]
    if best_family in {"fixed_holding", "fixed_holding_only"}:
        reasons.append("exit_lab_gate:exit_lab_fixed_holding_only")
    if "exit_lab_no_improving_exit_over_fixed_holding" in gate_reasons or _gate_text(gate, "no_improvement_reason"):
        reasons.append("exit_lab_gate:exit_lab_no_improving_exit_over_fixed_holding")
    if gate_status != "passed":
        reasons.extend(f"exit_lab_gate:{reason}" for reason in gate_reasons)
        if not gate_reasons:
            reasons.append("exit_lab_gate:exit_lab_status_not_passed")
    return list(dict.fromkeys(reasons))


def _multiple_testing_gate_row(
    gates: pd.DataFrame | None,
    *,
    discovery_candidate_id: str,
) -> Mapping[str, Any] | None:
    if gates is None or gates.empty or "candidate_id" not in gates.columns:
        return None
    matches = gates.loc[gates["candidate_id"].astype(str).eq(discovery_candidate_id)].copy()
    if matches.empty:
        return None
    return matches.iloc[0].to_dict()


def _validation_floor_gate_row(
    gates: pd.DataFrame | None,
    *,
    discovery_candidate_id: str,
) -> Mapping[str, Any] | None:
    if gates is None or gates.empty or "candidate_id" not in gates.columns:
        return None
    matches = gates.loc[gates["candidate_id"].astype(str).eq(discovery_candidate_id)].copy()
    if matches.empty:
        return None
    return matches.iloc[0].to_dict()


def _multiple_testing_gate_reasons(record: Mapping[str, Any], gate: Mapping[str, Any] | None) -> list[str]:
    if gate is None:
        return ["multiple_testing_candidate_gate_row_required"]
    reasons: list[str] = []
    expected_record_sha = str(record.get("record_sha256") or "")
    gate_record_sha = _gate_text(gate, "record_sha256")
    if expected_record_sha and gate_record_sha != expected_record_sha:
        reasons.append("multiple_testing_gate:record_sha256_mismatch")
    status = _gate_text(gate, "multiple_testing_status")
    gate_reasons = [reason for reason in _gate_text(gate, "multiple_testing_reasons").split("|") if reason]
    if status != "passed":
        if gate_reasons:
            reasons.extend(f"multiple_testing_gate:{reason}" for reason in gate_reasons)
        else:
            reasons.append("multiple_testing_gate:multiple_testing_status_not_passed")
    return list(dict.fromkeys(reasons))


def _validation_floor_gate_reasons(record: Mapping[str, Any], gate: Mapping[str, Any] | None) -> list[str]:
    if gate is None:
        return ["validation_floor_candidate_gate_row_required"]
    reasons: list[str] = []
    expected_record_sha = str(record.get("record_sha256") or "")
    gate_record_sha = _gate_text(gate, "record_sha256")
    if expected_record_sha and gate_record_sha != expected_record_sha:
        reasons.append("validation_floor_gate:record_sha256_mismatch")
    status = _gate_text(gate, "validation_floor_status")
    maturity = _gate_text(gate, "research_maturity")
    gate_reasons = [reason for reason in _gate_text(gate, "validation_floor_reasons").split("|") if reason]
    if maturity != MATURITY_CANDIDATE_READY:
        reasons.append("validation_floor_gate:candidate_ready_validation_required")
    if _gate_text(gate, "exit_lab_gate_status") != "passed":
        reasons.append("validation_floor_gate:exit_lab_gate_status_not_passed")
    if status != "passed":
        if gate_reasons:
            reasons.extend(f"validation_floor_gate:{reason}" for reason in gate_reasons)
        else:
            reasons.append("validation_floor_gate:validation_floor_status_not_passed")
    return list(dict.fromkeys(reasons))


def _gate_text(gate: Mapping[str, Any] | None, key: str) -> str:
    if gate is None:
        return ""
    value = gate.get(key, "")
    if value is None or pd.isna(value):
        return ""
    return str(value)


def _exit_lab_summary(gates: pd.DataFrame | None, reasons: list[str]) -> dict[str, Any]:
    if gates is None or gates.empty:
        return {
            "candidate_count": 0,
            "passed_count": 0,
            "blocked_count": 0,
            "reason_count": int(len(dict.fromkeys(reasons))),
        }
    passed = int(gates["exit_lab_gate_status"].astype(str).eq("passed").sum()) if "exit_lab_gate_status" in gates else 0
    return {
        "candidate_count": int(len(gates)),
        "passed_count": passed,
        "blocked_count": int(len(gates) - passed),
        "reason_count": int(len(dict.fromkeys(reasons))),
    }


def _multiple_testing_summary(gates: pd.DataFrame | None, reasons: list[str]) -> dict[str, Any]:
    if gates is None or gates.empty:
        return {
            "candidate_count": 0,
            "passed_count": 0,
            "blocked_count": 0,
            "reason_count": int(len(dict.fromkeys(reasons))),
        }
    passed = int(gates["multiple_testing_status"].astype(str).eq("passed").sum()) if "multiple_testing_status" in gates else 0
    return {
        "candidate_count": int(len(gates)),
        "passed_count": passed,
        "blocked_count": int(len(gates) - passed),
        "reason_count": int(len(dict.fromkeys(reasons))),
    }


def _validation_floor_summary(gates: pd.DataFrame | None, reasons: list[str]) -> dict[str, Any]:
    if gates is None or gates.empty:
        return {
            "candidate_count": 0,
            "candidate_ready_count": 0,
            "screen_worthy_count": 0,
            "diagnostic_count": 0,
            "blocked_count": 0,
            "reason_count": int(len(dict.fromkeys(reasons))),
        }
    maturity = gates["research_maturity"].astype(str) if "research_maturity" in gates.columns else pd.Series(dtype=str)
    ready = int(maturity.eq(MATURITY_CANDIDATE_READY).sum())
    screen = int(maturity.eq("screen-worthy").sum())
    diagnostic = int(maturity.eq("diagnostic").sum())
    return {
        "candidate_count": int(len(gates)),
        "candidate_ready_count": ready,
        "screen_worthy_count": screen,
        "diagnostic_count": diagnostic,
        "blocked_count": int(len(gates) - ready),
        "reason_count": int(len(dict.fromkeys(reasons))),
    }


def _research_boundary_reasons(payload: Mapping[str, Any], prefix: str) -> list[str]:
    reasons: list[str] = []
    if any(field in payload for field in LIVE_ADJACENT_VERSION_FIELDS):
        reasons.append(f"{prefix}_live_or_promotion_manifest_version_forbidden")
    if payload.get("control_only") is True:
        reasons.append(f"{prefix}_control_only_forbidden")
    if str(payload.get("artifact_family") or "") == "negative_control":
        reasons.append(f"{prefix}_negative_control_artifact_forbidden")
    if payload.get("research_only") is not True:
        reasons.append(f"{prefix}_research_only_required")
    if payload.get("observe_only") is not True:
        reasons.append(f"{prefix}_observe_only_required")
    if payload.get("promotion_ready") is not False:
        reasons.append(f"{prefix}_promotion_ready_must_be_false")
    for field in (
        "live_signal_input",
        "position_sizing_input",
        "operator_control_input",
        "live_execution_input",
        "runtime_control_input",
        "live_fetch_used",
        "order_placement_used",
        "runtime_mode_changed",
    ):
        if field in payload and payload.get(field) is not False:
            reasons.append(f"{prefix}_{field}_must_be_false")
    return reasons


def _replay_bridge_requirement_reasons(payload: Mapping[str, Any], prefix: str, *, anchor_dir: Path) -> list[str]:
    requirements = payload.get("replay_bridge_requirements")
    if not isinstance(requirements, Mapping):
        requirements = payload.get("candidate_bridge_requirements")
    replay_scoped = isinstance(requirements, Mapping) or isinstance(payload.get("replay_metadata"), Mapping)
    if not replay_scoped:
        return []
    req = dict(requirements or {})
    reasons: list[str] = []
    if bool(req.get("require_replay_profile_provenance", True)):
        reasons.extend(
            _path_hash_provenance_reasons(
                payload.get("replay_profile_provenance") or payload.get("replay_profile"),
                prefix=prefix,
                field="replay_profile_provenance",
                anchor_dir=anchor_dir,
            )
        )
    if bool(req.get("require_validation_manifest", True)):
        reasons.extend(
            _path_hash_provenance_reasons(
                payload.get("validation_manifest_provenance") or payload.get("validation_manifest"),
                prefix=prefix,
                field="validation_manifest",
                anchor_dir=anchor_dir,
            )
        )
    if bool(req.get("require_exact_replay_lineage", True)):
        reasons.extend(_exact_replay_lineage_reasons(payload, prefix=prefix, anchor_dir=anchor_dir))
    if bool(req.get("require_modern_window_evidence", False)):
        reasons.extend(
            _path_hash_provenance_reasons(
                payload.get("modern_window_evidence") or payload.get("modern_window_profile"),
                prefix=prefix,
                field="modern_window_evidence",
                anchor_dir=anchor_dir,
            )
        )
    return reasons


def _path_hash_provenance_reasons(value: Any, *, prefix: str, field: str, anchor_dir: Path) -> list[str]:
    if not isinstance(value, Mapping):
        return [f"{prefix}_{field}_required"]
    path = str(value.get("path") or value.get("manifest_path") or value.get("profile_path") or "")
    sha = str(value.get("sha256") or value.get("manifest_sha256") or value.get("profile_sha256") or "")
    if not path or not sha:
        return [f"{prefix}_{field}_required"]
    resolved = _resolve_provenance_path(path, anchor_dir=anchor_dir)
    if not resolved.exists():
        return [f"{prefix}_{field}_path_missing"]
    if _normalize_sha256(sha) != _file_sha256(resolved):
        return [f"{prefix}_{field}_sha256_mismatch"]
    return []


def _exact_replay_lineage_reasons(payload: Mapping[str, Any], *, prefix: str, anchor_dir: Path) -> list[str]:
    lineage = _exact_replay_lineage_payload(payload)
    if not lineage:
        return [f"{prefix}_exact_replay_lineage_required"]
    path_pairs = (
        (
            "exact_replay_lineage_replay",
            lineage.get("source_replay_spec_path") or lineage.get("source_materialization_manifest_path"),
            lineage.get("source_replay_spec_sha256") or lineage.get("source_materialization_manifest_sha256"),
        ),
        (
            "exact_replay_lineage_discovery",
            lineage.get("source_discovery_manifest_path"),
            lineage.get("source_discovery_manifest_sha256"),
        ),
    )
    reasons: list[str] = []
    for field, raw_path, raw_sha in path_pairs:
        if not raw_path or not raw_sha:
            reasons.append(f"{prefix}_{field}_required")
            continue
        resolved = _resolve_provenance_path(str(raw_path), anchor_dir=anchor_dir)
        if not resolved.exists():
            reasons.append(f"{prefix}_{field}_path_missing")
            continue
        if _normalize_sha256(str(raw_sha)) != _file_sha256(resolved):
            reasons.append(f"{prefix}_{field}_sha256_mismatch")
    return reasons


def _exact_replay_lineage_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    lineage = payload.get("exact_replay_lineage")
    if isinstance(lineage, Mapping):
        replay_path = str(lineage.get("source_replay_spec_path") or lineage.get("source_materialization_manifest_path") or "")
        discovery_path = str(lineage.get("source_discovery_manifest_path") or "")
        if replay_path and discovery_path:
            return dict(lineage)
    replay_metadata = payload.get("replay_metadata")
    if isinstance(replay_metadata, Mapping):
        replay_path = str(replay_metadata.get("source_materialization_manifest_path") or "")
        discovery_path = str(replay_metadata.get("source_discovery_manifest_path") or "")
        if replay_path and discovery_path:
            return dict(replay_metadata)
    replay_path = str(payload.get("source_replay_spec_path") or "")
    discovery_path = str(payload.get("source_discovery_manifest_path") or "")
    if replay_path and discovery_path:
        return {
            "source_replay_spec_path": replay_path,
            "source_replay_spec_sha256": str(payload.get("source_replay_spec_sha256") or ""),
            "source_discovery_manifest_path": discovery_path,
            "source_discovery_manifest_sha256": str(payload.get("source_discovery_manifest_sha256") or ""),
        }
    return {}


def _resolve_provenance_path(value: str, *, anchor_dir: Path) -> Path:
    candidate = Path(value).expanduser()
    if candidate.is_absolute() or candidate.exists():
        return candidate.resolve()
    return (anchor_dir / candidate).resolve()


def _normalize_sha256(value: str) -> str:
    text = str(value).strip()
    return text.split(":", 1)[1] if text.startswith("sha256:") else text


def _candidate_ids(frame: pd.DataFrame | None) -> set[str]:
    if frame is None or frame.empty or "candidate_id" not in frame.columns:
        return set()
    return {str(value) for value in frame["candidate_id"].dropna().tolist() if str(value)}


def _normalized_ledger_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    ordered = frame.loc[:, list(DISCOVERY_LEDGER_COLUMNS)].sort_values(
        ["trial_index", "trial_id", "ledger_kind"],
        kind="mergesort",
    )
    rows: list[dict[str, Any]] = []
    for row in ordered.to_dict("records"):
        rows.append({column: _normalized_ledger_value(row.get(column, "")) for column in DISCOVERY_LEDGER_COLUMNS})
    return rows


def _normalized_ledger_value(value: Any) -> Any:
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, bool) or value.__class__.__name__ == "bool_":
        return bool(value)
    if isinstance(value, numbers.Integral):
        return int(value)
    if isinstance(value, numbers.Real):
        return float(value)
    return str(value)


def _summary(
    eligibility: pd.DataFrame,
    global_reasons: list[str],
    *,
    reason_counts: Mapping[str, int],
    candidate_universe_alignment: Mapping[str, Any],
) -> dict[str, Any]:
    eligible_count = int(eligibility["eligible_for_existing_candidate_pack_validator"].sum()) if not eligibility.empty else 0
    blocked_count = int(len(eligibility) - eligible_count)
    return {
        "candidate_count": int(len(eligibility)),
        "eligible_count": eligible_count,
        "blocked_count": blocked_count,
        "global_reason_count": int(len(dict.fromkeys(global_reasons))),
        "top_reason_counts": dict(sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))[:12]),
        "ranking_overlap_count": int(candidate_universe_alignment.get("mapped_research_candidate_overlap_count") or 0),
        "cycle_ranking_candidate_count": int(candidate_universe_alignment.get("cycle_ranking_candidate_count") or 0),
        "candidate_universe_status": candidate_universe_alignment.get("status"),
        "candidate_pack_written": False,
        "promotion_ready": False,
    }


def _reason_counts(eligibility: pd.DataFrame) -> dict[str, int]:
    counts: dict[str, int] = {}
    if eligibility.empty or "bridge_reasons" not in eligibility.columns:
        return counts
    for raw_reasons in eligibility["bridge_reasons"].fillna("").astype(str).tolist():
        for reason in raw_reasons.split("|"):
            normalized = reason.strip()
            if not normalized:
                continue
            counts[normalized] = counts.get(normalized, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _candidate_universe_alignment(
    eligibility: pd.DataFrame,
    *,
    gate_context: Any,
    candidate_id_map: Mapping[str, str],
) -> dict[str, Any]:
    discovery_ids = _column_ids(eligibility, "discovery_candidate_id")
    research_ids = _column_ids(eligibility, "research_candidate_id")
    ranking_ids = set(getattr(gate_context, "ranking_candidate_ids", frozenset()) or frozenset())
    overlap = research_ids & ranking_ids
    mapped_count = sum(1 for discovery_id in discovery_ids if discovery_id in candidate_id_map)
    if not ranking_ids:
        status = "cycle_ranking_candidates_missing"
    elif not overlap:
        status = "no_mapped_discovery_candidates_in_cycle_rankings"
    elif len(overlap) < len(research_ids):
        status = "partial_discovery_to_cycle_ranking_overlap"
    else:
        status = "all_discovery_candidates_mapped_to_cycle_rankings"
    return {
        "status": status,
        "discovery_candidate_count": int(len(discovery_ids)),
        "research_candidate_count": int(len(research_ids)),
        "cycle_ranking_candidate_count": int(len(ranking_ids)),
        "candidate_id_map_count": int(len(candidate_id_map)),
        "mapped_discovery_candidate_count": int(mapped_count),
        "mapped_research_candidate_overlap_count": int(len(overlap)),
        "unmapped_discovery_candidate_count": int(max(0, len(discovery_ids) - mapped_count)),
    }


def _column_ids(frame: pd.DataFrame, column: str) -> set[str]:
    if frame.empty or column not in frame.columns:
        return set()
    return {str(value) for value in frame[column].dropna().tolist() if str(value)}


def _rejections_markdown(eligibility: pd.DataFrame, global_reasons: list[str]) -> str:
    lines = [
        "# Discovery Candidate Pack Bridge Rejections",
        "",
        "Research-only eligibility report. No candidate packs are written by this bridge.",
        "",
    ]
    if global_reasons:
        lines.extend(["## Global Reasons", ""])
        lines.extend(f"- {reason}" for reason in dict.fromkeys(global_reasons))
        lines.append("")
    blocked = eligibility.loc[~eligibility["eligible_for_existing_candidate_pack_validator"]] if not eligibility.empty else eligibility
    reason_counts = _reason_counts(eligibility)
    if reason_counts:
        lines.extend(["## Reason Counts", ""])
        for reason, count in list(reason_counts.items())[:25]:
            lines.append(f"- {reason}: {count}")
        lines.append("")
    lines.extend(["## Blocked Candidates", ""])
    if blocked.empty:
        lines.append("- None")
    else:
        if len(blocked) > REJECTION_MARKDOWN_MAX_BLOCKED_ROWS:
            lines.append(
                f"- Showing first {REJECTION_MARKDOWN_MAX_BLOCKED_ROWS} of {len(blocked)} blocked rows; "
                "the Parquet eligibility table contains every row."
            )
        for row in blocked.head(REJECTION_MARKDOWN_MAX_BLOCKED_ROWS).to_dict("records"):
            reasons = str(row.get("bridge_reasons") or "blocked").replace("|", ", ")
            lines.append(f"- {row.get('discovery_candidate_id')} -> {row.get('research_candidate_id')}: {reasons}")
    lines.append("")
    return "\n".join(lines)


def _eligibility_columns() -> list[str]:
    return [
        "discovery_candidate_id",
        "research_candidate_id",
        "eligible_for_existing_candidate_pack_validator",
        "bridge_status",
        "bridge_reasons",
        "research_candidate_gate_status",
        "research_candidate_gate_reasons",
        "exit_lab_status",
        "exit_lab_gate_status",
        "exit_lab_reasons",
        "exit_lab_best_family",
        "exit_lab_best_comparison_id",
        "exit_lab_best_exit_policy_id",
        "exit_vs_fixed_final_score_delta",
        "exit_lab_cost_stress_status",
        "entry_lead_evidence_sha256",
        "exit_lab_no_improvement_reasons",
        "multiple_testing_status",
        "multiple_testing_reasons",
        "multiple_testing_effective_trial_count",
        "multiple_testing_sampled_fraction",
        "multiple_testing_stability_neighborhood_size",
        "multiple_testing_latest_window_only_penalty",
        "validation_floor_status",
        "research_maturity",
        "validation_floor_reasons",
        "validation_floor_independent_event_count",
        "validation_floor_overlap_ratio",
        "validation_floor_split_pass_ratio",
        "validation_floor_side_concentration",
        "validation_floor_cost_stress_survival",
        "validation_floor_stability_neighborhood_size",
        "discovery_run_id",
        "cycle_manifest_path",
        "candidate_pack_written",
        "candidate_pack_paths",
        "research_only",
        "observe_only",
        "promotion_ready",
    ]


def _read_discovery_manifest(path: Path) -> dict[str, Any]:
    resolved_path = Path(path).expanduser().resolve()
    payload = _read_json_raw(resolved_path)
    normalized = dict(payload)
    required_outputs = payload.get("required_outputs")
    if isinstance(required_outputs, Mapping):
        scoped = normalize_operator_run_artifact_paths(
            {"required_outputs": dict(required_outputs)},
            artifact_path=resolved_path,
            anchor_root=resolved_path.parent,
        )
        normalized["required_outputs"] = dict(scoped.get("required_outputs") or {})
    return normalized


def _read_json_raw(path: Path) -> dict[str, Any]:
    resolved_path = Path(path).expanduser().resolve()
    try:
        payload = json.loads(resolved_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON at {resolved_path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {resolved_path}")
    return payload


def _read_json(path: Path) -> dict[str, Any]:
    resolved_path = Path(path).expanduser().resolve()
    payload = _read_json_raw(resolved_path)
    return normalize_operator_run_artifact_paths(payload, artifact_path=resolved_path, anchor_root=resolved_path.parent)


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_payload_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False).encode("utf-8")
    return sha256(encoded).hexdigest()


def _assert_new_artifact_paths(*paths: Path) -> None:
    existing = [str(path) for path in paths if path.exists()]
    if existing:
        raise ValueError("refusing to overwrite existing discovery candidate-pack bridge artifacts: " + ",".join(existing))


def _atomic_write_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        frame.to_parquet(tmp_path, index=False)
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        tmp_path.write_text(text, encoding="utf-8")
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
