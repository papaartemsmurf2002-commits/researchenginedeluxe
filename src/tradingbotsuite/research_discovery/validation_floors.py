from __future__ import annotations

import json
import math
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from tradingbotsuite.research.live_readiness import research_boundary_metadata
from tradingbotsuite.research_discovery.state import atomic_write_json


DISCOVERY_VALIDATION_FLOORS_VERSION = "discovery-validation-floors-v1"
DISCOVERY_VALIDATION_FLOORS_MANIFEST_VERSION = "discovery-validation-floors-manifest-v1"
DISCOVERY_VALIDATION_FLOORS_ARTIFACT_VERSION = "discovery-validation-floors-artifacts-v1"
VALIDATION_BLOCKER_REGISTRY_VERSION = "discovery-validation-blocker-registry-v1"

MATURITY_DIAGNOSTIC = "diagnostic"
MATURITY_SCREEN_WORTHY = "screen-worthy"
MATURITY_CANDIDATE_READY = "candidate-ready"


STANDARD_BLOCKER_REGISTRY: dict[str, str] = {
    "baseline_comparator_missing": "Transparent baseline or no-trade comparator evidence is missing.",
    "barrier_ordering_without_lower_tf_proof": "Barrier exits claim ordering without lower-timeframe sequence proof.",
    "best_candidate_concentration_above_ceiling": "Top candidate score concentration is above the validation ceiling.",
    "candidate_ready_validation_required": "Candidate-ready validation maturity is required.",
    "cost_stress_survival_below_floor": "Cost-stress survival is missing or below the configured floor.",
    "cross_symbol_future_alignment": "Cross-symbol context has not proven point-in-time alignment.",
    "declared_search_space_required": "Declared search-space evidence is missing.",
    "depth_sequence_integrity_missing": "Depth/L2 sequence integrity proof is missing.",
    "directional_comparator_missing": "Long/short directional comparator evidence is incomplete.",
    "effective_trial_count_requires_stability_neighborhood": "Large effective trial count lacks stability-neighborhood evidence.",
    "exit_lab_incomplete": "Exit-lab evidence is present but incomplete.",
    "exit_lab_missing": "Exit-lab evidence is missing.",
    "feature_ablation_missing": "Feature-ablation evidence is missing.",
    "feature_ablation_not_passing": "Feature-ablation evidence is not passing.",
    "filter_ablation_missing": "Matched filter-ablation evidence is missing.",
    "filter_ablation_not_passing": "Matched filter-ablation evidence is not passing.",
    "funding_feature_future_leakage": "Funding context may leak future funding information.",
    "funding_only_crowding_overfit": "Funding-only crowding evidence has not cleared overfit checks.",
    "independent_event_accounting_missing": "Independent event-accounting evidence is missing.",
    "independent_event_count_below_floor": "Independent event count is below the configured floor.",
    "isolated_top_score_large_grid": "A large-grid top score is isolated from stable neighbors.",
    "knn_future_or_overlapping_neighbor": "KNN evidence uses future or overlapping neighbors.",
    "knn_sample_reduction_only": "Filter evidence only reduces sample count without edge improvement.",
    "latest_window_context_non_diagnostic_claim": "Latest-window context is being claimed beyond diagnostic scope.",
    "latest_window_only_diagnostic": "Latest-window-only evidence is diagnostic only.",
    "latest_window_only_evidence": "Multiple-testing evidence is latest-window only.",
    "liquidation_false_zero_window": "Liquidation context may have false zero-filled windows.",
    "liquidation_feature_not_testable": "Liquidation feature evidence is not provider-backed/testable.",
    "multiple_testing_stability_incomplete": "Multiple-testing or stability evidence is incomplete.",
    "no_regime_baseline_missing": "Regime-claimed candidate lacks a no-regime baseline.",
    "no_trade_comparator_missing": "No-trade comparator evidence is missing.",
    "orderflow_feature_not_testable": "AggTrade/orderflow proxy evidence is not testable.",
    "overlap_ratio_above_ceiling": "Overlapping bar signal ratio is above the configured ceiling.",
    "overlap_ratio_required": "Overlap ratio evidence is missing.",
    "regime_smoothed_state_used_in_validation": "Smoothed regime states were used in validation.",
    "sampled_fraction_below_candidate_ready_floor": "Sampled fraction is below the candidate-ready floor.",
    "side_collapse_ratio_above_ceiling": "Directional side collapse is above the configured ceiling.",
    "side_concentration_above_ceiling": "Side concentration is above the configured ceiling.",
    "side_concentration_required": "Side concentration evidence is missing.",
    "signal_rate_above_discovery_ceiling": "Signal rate is above the discovery ceiling.",
    "signal_rate_below_discovery_floor": "Signal rate is below the discovery floor.",
    "signal_rate_near_ceiling": "Signal rate is near its ceiling and may be dense overlapping bars.",
    "split_pass_ratio_below_floor": "Split pass ratio is below the configured floor.",
    "split_pass_ratio_required": "Split pass ratio evidence is missing.",
    "split_window_concentration_above_ceiling": "Split/window concentration is above the configured ceiling.",
    "split_window_concentration_required": "Split/window concentration evidence is missing.",
    "source_provider_capability_diagnostic_only": "Source provider capability is diagnostic-only by default.",
    "source_provider_capability_missing": "Source provider capability metadata is missing.",
    "source_provider_capability_not_candidate_ready": "Source provider capability is not candidate-ready by default.",
    "durable_public_archive_readiness_missing": "Durable public-archive fixture readiness evidence is missing.",
    "durable_public_archive_readiness_not_ready": "Durable public-archive fixture readiness evidence is not ready.",
    "stability_neighborhood_size_below_floor": "Stability-neighborhood size is below the configured floor.",
    "validation_floor_candidate_gate_row_required": "Validation-floor gate row is missing.",
    "validation_floor_manifest_required": "Validation-floor manifest is required.",
}
PASSING_STATUSES = {
    "available",
    "baseline_feature_set_no_optional_claim",
    "candidate-ready",
    "candidate_ready",
    "complete",
    "edge_improving",
    "not_required",
    "passed",
}
BLOCKING_STATUSES = {
    "blocked",
    "deferred_evidence",
    "failed",
    "harmful",
    "incomplete",
    "missing",
    "not_testable",
    "pending",
    "pending_evidence",
    "sample_reducing_only",
}


@dataclass(frozen=True, slots=True)
class DiscoveryValidationFloorSpec:
    screen_independent_event_count_min: int = 120
    candidate_ready_independent_event_count_min: int = 250
    screen_overlap_ratio_max: float = 0.35
    candidate_ready_overlap_ratio_max: float = 0.25
    screen_split_pass_ratio_min: float = 0.60
    candidate_ready_split_pass_ratio_min: float = 0.70
    screen_side_concentration_max: float = 0.90
    candidate_ready_side_concentration_max: float = 0.80
    screen_cost_stress_survival_min: float = 0.80
    candidate_ready_cost_stress_survival_min: float = 1.00
    screen_stability_neighborhood_min: int = 2
    candidate_ready_stability_neighborhood_min: int = 3
    declared_search_space: int = 0

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "DiscoveryValidationFloorSpec":
        if not isinstance(payload, Mapping):
            raise ValueError("validation-floor spec must be a JSON object")
        return cls(
            screen_independent_event_count_min=max(0, int(payload.get("screen_independent_event_count_min", 120))),
            candidate_ready_independent_event_count_min=max(
                0,
                int(payload.get("candidate_ready_independent_event_count_min", 250)),
            ),
            screen_overlap_ratio_max=float(payload.get("screen_overlap_ratio_max", 0.35)),
            candidate_ready_overlap_ratio_max=float(payload.get("candidate_ready_overlap_ratio_max", 0.25)),
            screen_split_pass_ratio_min=float(payload.get("screen_split_pass_ratio_min", 0.60)),
            candidate_ready_split_pass_ratio_min=float(payload.get("candidate_ready_split_pass_ratio_min", 0.70)),
            screen_side_concentration_max=float(payload.get("screen_side_concentration_max", 0.90)),
            candidate_ready_side_concentration_max=float(payload.get("candidate_ready_side_concentration_max", 0.80)),
            screen_cost_stress_survival_min=float(payload.get("screen_cost_stress_survival_min", 0.80)),
            candidate_ready_cost_stress_survival_min=float(payload.get("candidate_ready_cost_stress_survival_min", 1.00)),
            screen_stability_neighborhood_min=max(0, int(payload.get("screen_stability_neighborhood_min", 2))),
            candidate_ready_stability_neighborhood_min=max(
                0,
                int(payload.get("candidate_ready_stability_neighborhood_min", 3)),
            ),
            declared_search_space=max(0, int(payload.get("declared_search_space", 0))),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "screen_independent_event_count_min": int(self.screen_independent_event_count_min),
            "candidate_ready_independent_event_count_min": int(self.candidate_ready_independent_event_count_min),
            "screen_overlap_ratio_max": float(self.screen_overlap_ratio_max),
            "candidate_ready_overlap_ratio_max": float(self.candidate_ready_overlap_ratio_max),
            "screen_split_pass_ratio_min": float(self.screen_split_pass_ratio_min),
            "candidate_ready_split_pass_ratio_min": float(self.candidate_ready_split_pass_ratio_min),
            "screen_side_concentration_max": float(self.screen_side_concentration_max),
            "candidate_ready_side_concentration_max": float(self.candidate_ready_side_concentration_max),
            "screen_cost_stress_survival_min": float(self.screen_cost_stress_survival_min),
            "candidate_ready_cost_stress_survival_min": float(self.candidate_ready_cost_stress_survival_min),
            "screen_stability_neighborhood_min": int(self.screen_stability_neighborhood_min),
            "candidate_ready_stability_neighborhood_min": int(self.candidate_ready_stability_neighborhood_min),
            "declared_search_space": int(self.declared_search_space),
        }


@dataclass(frozen=True, slots=True)
class DiscoveryValidationFloorResult:
    manifest: dict[str, Any]
    candidate_gates: pd.DataFrame


@dataclass(frozen=True, slots=True)
class DiscoveryValidationFloorArtifactResult:
    output_dir: Path
    manifest_path: Path
    candidate_gates_path: Path


def build_discovery_validation_floor_report(
    candidates: pd.DataFrame,
    *,
    spec: DiscoveryValidationFloorSpec | None = None,
    source_discovery_manifest_path: Path | None = None,
) -> DiscoveryValidationFloorResult:
    effective_spec = spec or DiscoveryValidationFloorSpec()
    source_path = Path(source_discovery_manifest_path).expanduser().resolve() if source_discovery_manifest_path else None
    source_sha = _file_sha256(source_path) if source_path is not None and source_path.exists() else ""
    normalized = candidates.copy()
    if source_sha and not normalized.empty and "source_discovery_manifest_sha256" not in normalized.columns:
        normalized["source_discovery_manifest_sha256"] = source_sha
    candidate_gates = _candidate_gates(normalized, spec=effective_spec)
    registry_payload = blocker_registry_payload()
    manifest = {
        "validation_floors_manifest_version": DISCOVERY_VALIDATION_FLOORS_MANIFEST_VERSION,
        "validation_floors_version": DISCOVERY_VALIDATION_FLOORS_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "spec": effective_spec.to_payload(),
        "spec_sha256": _stable_hash(effective_spec.to_payload()),
        "input_candidate_row_count": int(len(normalized)),
        "candidate_gate_row_count": int(len(candidate_gates)),
        "summary": _summary(candidate_gates),
        "experiment_budget_ledger": _experiment_budget_ledger(normalized, spec=effective_spec),
        "blocker_registry": registry_payload,
        "blocker_registry_sha256": _stable_hash(registry_payload),
        "claim_scope": "research_validation_floor_labels_only_no_live_or_promotion_claim",
        "source_discovery_manifest_path": str(source_path) if source_path is not None else "",
        "source_discovery_manifest_sha256": source_sha,
        "live_fetch_used": False,
        "order_placement_used": False,
        "runtime_mode_changed": False,
    }
    manifest["candidate_gates_sha256"] = _frame_hash(candidate_gates)
    return DiscoveryValidationFloorResult(manifest=manifest, candidate_gates=candidate_gates)


def build_discovery_validation_floor_report_from_manifest(
    discovery_manifest_path: Path,
    *,
    spec: DiscoveryValidationFloorSpec | None = None,
) -> DiscoveryValidationFloorResult:
    discovery_manifest_path = Path(discovery_manifest_path).expanduser().resolve()
    manifest = _read_json(discovery_manifest_path)
    required_outputs = manifest.get("required_outputs") if isinstance(manifest.get("required_outputs"), Mapping) else {}
    interesting_path = Path(str(required_outputs.get("interesting_candidates") or ""))
    candidates = pd.read_parquet(interesting_path) if interesting_path.exists() else pd.DataFrame()
    effective_spec = spec or DiscoveryValidationFloorSpec(
        declared_search_space=_declared_search_space(manifest, required_outputs, candidates),
    )
    if effective_spec.declared_search_space <= 0:
        effective_spec = DiscoveryValidationFloorSpec.from_payload(
            {
                **effective_spec.to_payload(),
                "declared_search_space": _declared_search_space(manifest, required_outputs, candidates),
            }
        )
    return build_discovery_validation_floor_report(
        candidates,
        spec=effective_spec,
        source_discovery_manifest_path=discovery_manifest_path,
    )


def write_discovery_validation_floor_artifacts(
    output_dir: Path,
    result: DiscoveryValidationFloorResult,
) -> DiscoveryValidationFloorArtifactResult:
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "discovery_validation_floors_manifest.json"
    candidate_gates_path = output_dir / "discovery_validation_floor_candidate_gates.parquet"
    result.candidate_gates.to_parquet(candidate_gates_path, index=False)
    manifest = dict(result.manifest)
    manifest["artifact_version"] = DISCOVERY_VALIDATION_FLOORS_ARTIFACT_VERSION
    manifest["required_outputs"] = {
        "discovery_validation_floors_manifest": str(manifest_path),
        "discovery_validation_floor_candidate_gates": str(candidate_gates_path),
    }
    manifest["discovery_validation_floor_candidate_gates_sha256"] = _file_sha256(candidate_gates_path)
    atomic_write_json(manifest_path, manifest)
    return DiscoveryValidationFloorArtifactResult(
        output_dir=output_dir,
        manifest_path=manifest_path,
        candidate_gates_path=candidate_gates_path,
    )


def blocker_registry_payload() -> dict[str, Any]:
    return {
        "blocker_registry_version": VALIDATION_BLOCKER_REGISTRY_VERSION,
        "codes": dict(sorted(STANDARD_BLOCKER_REGISTRY.items())),
    }


def registered_blocker_codes() -> frozenset[str]:
    return frozenset(STANDARD_BLOCKER_REGISTRY)


def _candidate_gates(candidates: pd.DataFrame, *, spec: DiscoveryValidationFloorSpec) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for record in candidates.to_dict("records"):
        screen_reasons = _floor_reasons(record, spec=spec, profile="screen")
        candidate_reasons = _floor_reasons(record, spec=spec, profile="candidate_ready")
        maturity = _maturity(screen_reasons=screen_reasons, candidate_reasons=candidate_reasons)
        status = "passed" if maturity == MATURITY_CANDIDATE_READY else "blocked"
        blockers = list(dict.fromkeys(candidate_reasons))
        rows.append(
            {
                "candidate_id": str(record.get("candidate_id") or ""),
                "record_sha256": str(record.get("record_sha256") or ""),
                "source_discovery_manifest_sha256": str(record.get("source_discovery_manifest_sha256") or ""),
                "validation_floor_status": status,
                "research_maturity": maturity,
                "validation_floor_reasons": "|".join(blockers),
                "screen_floor_reasons": "|".join(screen_reasons),
                "candidate_ready_floor_reasons": "|".join(candidate_reasons),
                "independent_event_count": _optional_int(record.get("independent_event_count")) or 0,
                "independent_event_count_min": int(spec.candidate_ready_independent_event_count_min),
                "overlap_ratio": _optional_float(record.get("overlap_ratio")),
                "overlap_ratio_max": float(spec.candidate_ready_overlap_ratio_max),
                "split_pass_ratio": _split_pass_ratio(record),
                "split_pass_ratio_min": float(spec.candidate_ready_split_pass_ratio_min),
                "side_concentration": _side_concentration(record),
                "side_concentration_max": float(spec.candidate_ready_side_concentration_max),
                "cost_stress_survival": _optional_float(record.get("cost_stress_survival")),
                "cost_stress_survival_min": float(spec.candidate_ready_cost_stress_survival_min),
                "stability_neighborhood_size": _optional_int(record.get("stability_neighborhood_size")) or 0,
                "stability_neighborhood_min": int(spec.candidate_ready_stability_neighborhood_min),
                "baseline_comparator_status": _status_value(record, "baseline_comparator_status", "baseline_comparator_coverage_status"),
                "no_regime_baseline_status": _status_value(record, "no_regime_baseline_status", "regime_baseline_status"),
                "exit_lab_status": _status_value(record, "exit_lab_status"),
                "exit_lab_gate_status": _status_value(record, "exit_lab_gate_status"),
                "filter_ablation_status": _status_value(record, "filter_ablation_status", "matched_filter_ablation_status"),
                "feature_ablation_status": _status_value(record, "feature_ablation_status", "ablation_evidence_status"),
                "latest_window_only": bool(_truthy(record.get("latest_window_only")) or _truthy(record.get("latest_window_only_penalty"))),
                "source_provider_capability_present": _source_provider_capability_present(record),
                "source_provider_capability_candidate_ready_default": _source_provider_capability_candidate_ready_default(record),
                "source_provider_capability_diagnostic_only_by_default": _source_provider_capability_diagnostic_only_by_default(record),
                "durable_public_archive_readiness_ready": _durable_public_archive_readiness_ready(record),
                "durable_public_archive_readiness_status": _status_value(
                    record,
                    "durable_public_archive_readiness_status",
                    "public_archive_readiness_status",
                ),
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
            }
        )
    return pd.DataFrame(rows, columns=_candidate_gate_columns())


def _floor_reasons(record: Mapping[str, Any], *, spec: DiscoveryValidationFloorSpec, profile: str) -> list[str]:
    if profile == "screen":
        independent_min = spec.screen_independent_event_count_min
        overlap_max = spec.screen_overlap_ratio_max
        split_min = spec.screen_split_pass_ratio_min
        side_max = spec.screen_side_concentration_max
        cost_min = spec.screen_cost_stress_survival_min
        stability_min = spec.screen_stability_neighborhood_min
    elif profile == "candidate_ready":
        independent_min = spec.candidate_ready_independent_event_count_min
        overlap_max = spec.candidate_ready_overlap_ratio_max
        split_min = spec.candidate_ready_split_pass_ratio_min
        side_max = spec.candidate_ready_side_concentration_max
        cost_min = spec.candidate_ready_cost_stress_survival_min
        stability_min = spec.candidate_ready_stability_neighborhood_min
    else:
        raise ValueError(f"unsupported validation floor profile: {profile}")

    reasons: list[str] = []
    independent_events = _optional_int(record.get("independent_event_count"))
    if independent_events is None:
        reasons.append("independent_event_accounting_missing")
    elif independent_events < independent_min:
        reasons.append("independent_event_count_below_floor")
    overlap = _optional_float(record.get("overlap_ratio"))
    if overlap is None:
        reasons.append("overlap_ratio_required")
    elif overlap > overlap_max:
        reasons.append("overlap_ratio_above_ceiling")
    split_ratio = _split_pass_ratio(record)
    if split_ratio is None:
        reasons.append("split_pass_ratio_required")
    elif split_ratio < split_min:
        reasons.append("split_pass_ratio_below_floor")
    side_concentration = _side_concentration(record)
    if side_concentration is None:
        reasons.append("side_concentration_required")
    elif side_concentration > side_max:
        reasons.append("side_concentration_above_ceiling")
        if _optional_float(record.get("side_collapse_ratio")) is not None:
            reasons.append("side_collapse_ratio_above_ceiling")
    cost_survival = _optional_float(record.get("cost_stress_survival"))
    if cost_survival is None or cost_survival < cost_min:
        reasons.append("cost_stress_survival_below_floor")
    stability_neighborhood = _optional_int(record.get("stability_neighborhood_size"))
    if stability_neighborhood is None or stability_neighborhood < stability_min:
        reasons.append("stability_neighborhood_size_below_floor")
    reasons.extend(_semantic_blockers(record))
    if profile == "candidate_ready":
        reasons.extend(_candidate_ready_contract_reasons(record))
    return [reason for reason in dict.fromkeys(reasons) if reason in STANDARD_BLOCKER_REGISTRY]


def _semantic_blockers(record: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if _truthy(record.get("funding_feature_future_leakage")):
        reasons.append("funding_feature_future_leakage")
    if _truthy(record.get("regime_smoothed_state_used_in_validation")):
        reasons.append("regime_smoothed_state_used_in_validation")
    if _truthy(record.get("knn_future_or_overlapping_neighbor")) or _truthy(record.get("knn_neighbor_overlap_detected")):
        reasons.append("knn_future_or_overlapping_neighbor")
    if _truthy(record.get("latest_window_context_non_diagnostic_claim")):
        reasons.append("latest_window_context_non_diagnostic_claim")
    if _truthy(record.get("latest_window_only")) or _truthy(record.get("latest_window_only_penalty")):
        reasons.append("latest_window_only_diagnostic")
    if _truthy(record.get("liquidation_zero_filled")) or str(record.get("liquidation_context_status") or "") == "false_zero_window":
        reasons.append("liquidation_false_zero_window")
    if _truthy(record.get("depth_feature_claimed")) and str(record.get("depth_sequence_integrity_status") or "") != "complete":
        reasons.append("depth_sequence_integrity_missing")
    if _truthy(record.get("barrier_ordering_claimed")) and not _truthy(record.get("lower_timeframe_sequence_proof")):
        reasons.append("barrier_ordering_without_lower_tf_proof")
    if _truthy(record.get("funding_only_crowding_overfit")):
        reasons.append("funding_only_crowding_overfit")
    if _truthy(record.get("cross_symbol_future_alignment")) or str(record.get("cross_symbol_alignment_status") or "") == "future_aligned":
        reasons.append("cross_symbol_future_alignment")
    if _truthy(record.get("signal_rate_near_ceiling")) or _truthy(record.get("near_signal_ceiling")):
        reasons.append("signal_rate_near_ceiling")
    if _truthy(record.get("orderflow_feature_not_testable")):
        reasons.append("orderflow_feature_not_testable")
    if _truthy(record.get("liquidation_feature_not_testable")):
        reasons.append("liquidation_feature_not_testable")
    reasons.extend(_source_capability_blockers(record))
    for key in ("blocker_code", "filter_blocker_code"):
        value = str(record.get(key) or "").strip()
        if value in STANDARD_BLOCKER_REGISTRY:
            reasons.append(value)
    return reasons


def _source_capability_blockers(record: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    readiness = _durable_public_archive_readiness_ready(record)
    if not _source_provider_capability_present(record):
        reasons.append("source_provider_capability_missing")
    if _source_provider_capability_candidate_ready_default(record) is not True and readiness is not True:
        reasons.append("source_provider_capability_not_candidate_ready")
    if _source_provider_capability_diagnostic_only_by_default(record) is True and readiness is not True:
        reasons.append("source_provider_capability_diagnostic_only")
    if readiness is None:
        reasons.append("durable_public_archive_readiness_missing")
    elif readiness is not True:
        reasons.append("durable_public_archive_readiness_not_ready")
    return reasons


def _source_provider_capability_present(record: Mapping[str, Any]) -> bool:
    if _truthy(record.get("source_provider_capability_present")) or _truthy(record.get("provider_capability_present")):
        return True
    if isinstance(record.get("provider_capability"), Mapping):
        return True
    return any(
        key in record
        for key in (
            "source_provider_capability_candidate_ready_default",
            "provider_capability_candidate_ready_default",
            "candidate_ready_default",
            "source_provider_capability_diagnostic_only_by_default",
            "provider_capability_diagnostic_only_by_default",
            "diagnostic_only_by_default",
        )
    )


def _source_provider_capability_candidate_ready_default(record: Mapping[str, Any]) -> bool | None:
    return _optional_bool(
        record,
        "source_provider_capability_candidate_ready_default",
        "provider_capability_candidate_ready_default",
        "candidate_ready_default",
    )


def _source_provider_capability_diagnostic_only_by_default(record: Mapping[str, Any]) -> bool | None:
    return _optional_bool(
        record,
        "source_provider_capability_diagnostic_only_by_default",
        "provider_capability_diagnostic_only_by_default",
        "diagnostic_only_by_default",
    )


def _durable_public_archive_readiness_ready(record: Mapping[str, Any]) -> bool | None:
    return _optional_bool(
        record,
        "durable_public_archive_readiness_ready",
        "public_archive_readiness_ready",
    )


def _candidate_ready_contract_reasons(record: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if not _status_passes(record, ("baseline_comparator_status", "baseline_comparator_coverage_status")):
        reasons.append("baseline_comparator_missing")
    expectancy_vs_no_trade = _optional_float(record.get("expectancy_vs_no_trade"))
    if expectancy_vs_no_trade is None or expectancy_vs_no_trade <= 0.0:
        reasons.append("no_trade_comparator_missing")
    if not _directional_comparator_complete(record):
        reasons.append("directional_comparator_missing")
    if _regime_claimed(record) and not _status_passes(record, ("no_regime_baseline_status", "regime_baseline_status")):
        reasons.append("no_regime_baseline_missing")
    if not _exit_lab_gate_passes(record):
        reasons.append("exit_lab_missing")
    filter_status = _status_value(record, "filter_ablation_status", "matched_filter_ablation_status")
    if not filter_status:
        reasons.append("filter_ablation_missing")
    elif filter_status == "sample_reducing_only":
        reasons.append("knn_sample_reduction_only")
    elif filter_status not in {"edge_improving", "passed", "complete", "not_required", "baseline_feature_set_no_optional_claim"}:
        reasons.append("filter_ablation_not_passing")
    feature_status = _status_value(record, "feature_ablation_status", "ablation_evidence_status")
    if not feature_status:
        reasons.append("feature_ablation_missing")
    elif feature_status not in {"passed", "complete", "not_required", "baseline_feature_set_no_optional_claim", "comparator_feature_set_passed"}:
        reasons.append("feature_ablation_not_passing")
    if _truthy(record.get("multiple_testing_stability_incomplete")):
        reasons.append("multiple_testing_stability_incomplete")
    if _truthy(record.get("isolated_top_score_large_grid")):
        reasons.append("isolated_top_score_large_grid")
    return reasons


def _maturity(*, screen_reasons: list[str], candidate_reasons: list[str]) -> str:
    if not candidate_reasons:
        return MATURITY_CANDIDATE_READY
    if not screen_reasons:
        return MATURITY_SCREEN_WORTHY
    return MATURITY_DIAGNOSTIC


def _experiment_budget_ledger(candidates: pd.DataFrame, *, spec: DiscoveryValidationFloorSpec) -> dict[str, Any]:
    candidate_count = int(len(candidates))
    declared = int(spec.declared_search_space)
    effective = _effective_trial_count(candidates, candidate_count)
    return {
        "strategy_families": _unique_values(candidates, "candidate_family", "strategy_family", "strategy_id"),
        "feature_set_variants": _unique_values(candidates, "feature_column_set_id", "feature_set_id"),
        "parameter_combinations": _unique_values(candidates, "parameters_sha256", "parameters_json"),
        "exit_variants": _unique_values(candidates, "exit_policy_id"),
        "regime_modes": _unique_values(candidates, "regime_mode"),
        "knn_k_values": _unique_values(candidates, "k"),
        "distance_metrics": _unique_values(candidates, "distance_metric"),
        "validation_modes": _unique_values(candidates, "validation_mode", "validation_method"),
        "candidate_count": candidate_count,
        "effective_trial_count": effective,
        "declared_search_space": declared,
        "sampled_fraction": float(candidate_count / declared) if declared else 0.0,
        "best_candidate_concentration": _best_candidate_concentration(candidates),
        "stability_neighborhood_size": _max_optional_int(candidates, "stability_neighborhood_size"),
    }


def _summary(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {
            "candidate_count": 0,
            "candidate_ready_count": 0,
            "screen_worthy_count": 0,
            "diagnostic_count": 0,
            "blocked_count": 0,
        }
    maturity = frame["research_maturity"].astype(str)
    ready = int(maturity.eq(MATURITY_CANDIDATE_READY).sum())
    screen = int(maturity.eq(MATURITY_SCREEN_WORTHY).sum())
    diagnostic = int(maturity.eq(MATURITY_DIAGNOSTIC).sum())
    return {
        "candidate_count": int(len(frame)),
        "candidate_ready_count": ready,
        "screen_worthy_count": screen,
        "diagnostic_count": diagnostic,
        "blocked_count": int(len(frame) - ready),
    }


def _candidate_gate_columns() -> list[str]:
    return [
        "candidate_id",
        "record_sha256",
        "source_discovery_manifest_sha256",
        "validation_floor_status",
        "research_maturity",
        "validation_floor_reasons",
        "screen_floor_reasons",
        "candidate_ready_floor_reasons",
        "independent_event_count",
        "independent_event_count_min",
        "overlap_ratio",
        "overlap_ratio_max",
        "split_pass_ratio",
        "split_pass_ratio_min",
        "side_concentration",
        "side_concentration_max",
        "cost_stress_survival",
        "cost_stress_survival_min",
        "stability_neighborhood_size",
        "stability_neighborhood_min",
        "baseline_comparator_status",
        "no_regime_baseline_status",
        "exit_lab_status",
        "exit_lab_gate_status",
        "filter_ablation_status",
        "feature_ablation_status",
        "latest_window_only",
        "source_provider_capability_present",
        "source_provider_capability_candidate_ready_default",
        "source_provider_capability_diagnostic_only_by_default",
        "durable_public_archive_readiness_ready",
        "durable_public_archive_readiness_status",
        "research_only",
        "observe_only",
        "promotion_ready",
    ]


def _declared_search_space(
    manifest: Mapping[str, Any],
    required_outputs: Mapping[str, Any],
    candidates: pd.DataFrame,
) -> int:
    if "search_space_total_combinations" in candidates.columns:
        values = pd.to_numeric(candidates["search_space_total_combinations"], errors="coerce").dropna()
        if not values.empty:
            return int(max(0, values.max()))
    resolved_spec_raw = required_outputs.get("discovery_spec_resolved")
    if resolved_spec_raw and Path(str(resolved_spec_raw)).exists():
        payload = _read_json(Path(str(resolved_spec_raw)))
        templates = payload.get("trial_templates") if isinstance(payload.get("trial_templates"), list) else []
        budget = payload.get("budget") if isinstance(payload.get("budget"), Mapping) else {}
        if templates:
            return int(max(1, len(templates)))
        max_trials = int(budget.get("max_trials") or 0)
        if max_trials:
            return max_trials
    counts = manifest.get("counts") if isinstance(manifest.get("counts"), Mapping) else {}
    completed = int(counts.get("completed_trials") or 0)
    return int(max(completed, len(candidates)))


def _effective_trial_count(candidates: pd.DataFrame, candidate_count: int) -> int:
    if candidates.empty:
        return 0
    if "effective_trial_count" in candidates.columns:
        values = pd.to_numeric(candidates["effective_trial_count"], errors="coerce").dropna()
        if not values.empty:
            return int(max(0, values.max()))
    identity_columns = [
        column
        for column in (
            "candidate_family",
            "strategy_id",
            "feature_column_set_id",
            "feature_set_id",
            "regime_mode",
            "label_horizon",
            "distance_metric",
            "k",
            "exit_policy_id",
        )
        if column in candidates.columns
    ]
    if not identity_columns:
        return int(candidate_count)
    return int(candidates.loc[:, identity_columns].drop_duplicates().shape[0])


def _unique_values(candidates: pd.DataFrame, *columns: str) -> list[str]:
    values: list[str] = []
    for column in columns:
        if column not in candidates.columns:
            continue
        for value in candidates[column].dropna().tolist():
            text = str(value)
            if text and text not in values:
                values.append(text)
    return sorted(values)


def _best_candidate_concentration(candidates: pd.DataFrame) -> float:
    if candidates.empty:
        return 0.0
    scores = [_score(row) for row in candidates.to_dict("records")]
    total = sum(max(0.0, score) for score in scores)
    if total <= 0.0:
        return 0.0
    return float(max(max(0.0, score) for score in scores) / total)


def _score(record: Mapping[str, Any]) -> float:
    for key in ("discovery_screen_score_v2", "final_score", "score"):
        value = _optional_float(record.get(key))
        if value is not None:
            return value
    return 0.0


def _max_optional_int(candidates: pd.DataFrame, column: str) -> int:
    if candidates.empty or column not in candidates.columns:
        return 0
    values = pd.to_numeric(candidates[column], errors="coerce").dropna()
    if values.empty:
        return 0
    return int(max(0, values.max()))


def _split_pass_ratio(record: Mapping[str, Any]) -> float | None:
    value = _optional_float(record.get("split_pass_ratio"))
    if value is not None:
        return value
    split_count = _optional_float(record.get("split_evaluation_count"))
    required = _optional_float(record.get("required_split_count"))
    if split_count is not None and required and required > 0:
        return min(1.0, split_count / required)
    if str(record.get("split_validation_method_status") or "") == "complete":
        return 1.0
    return None


def _side_concentration(record: Mapping[str, Any]) -> float | None:
    value = _optional_float(record.get("side_concentration"))
    if value is not None:
        return value
    collapse = _optional_float(record.get("side_collapse_ratio"))
    if collapse is not None:
        return collapse
    long_count = _optional_float(record.get("long_independent_event_count"))
    short_count = _optional_float(record.get("short_independent_event_count"))
    if long_count is not None and short_count is not None and long_count + short_count > 0:
        return max(long_count, short_count) / (long_count + short_count)
    return None


def _directional_comparator_complete(record: Mapping[str, Any]) -> bool:
    status = str(record.get("directional_comparator_status") or "").strip().lower()
    if status:
        return status in {"complete", "passed", "available"}
    long_count = _optional_int(record.get("long_independent_event_count"))
    short_count = _optional_int(record.get("short_independent_event_count"))
    if long_count is not None and short_count is not None:
        return long_count > 0 and short_count > 0
    sides = {item for item in str(record.get("side_evidence_sides") or "").split("|") if item}
    return {"long", "short"} <= sides


def _exit_lab_gate_passes(record: Mapping[str, Any]) -> bool:
    gate_status = _status_value(record, "exit_lab_gate_status")
    if gate_status:
        return gate_status == "passed"
    return False


def _regime_claimed(record: Mapping[str, Any]) -> bool:
    mode = str(record.get("regime_mode") or "").strip().lower()
    if mode in {"", "none", "no_regime", "no-regime", "no_regime_baseline"}:
        return False
    return True


def _status_passes(record: Mapping[str, Any], keys: tuple[str, ...]) -> bool:
    statuses = [_status_value(record, key) for key in keys]
    statuses = [status for status in statuses if status]
    if any(status in BLOCKING_STATUSES for status in statuses):
        return False
    return any(status in PASSING_STATUSES for status in statuses)


def _status_value(record: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = record.get(key)
        if value is None or pd.isna(value):
            continue
        text = str(value).strip().lower()
        if text:
            return text
    return ""


def _optional_float(value: Any) -> float | None:
    try:
        if pd.isna(value):
            return None
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _optional_int(value: Any) -> int | None:
    parsed = _optional_float(value)
    if parsed is None:
        return None
    return int(parsed)


def _optional_bool(record: Mapping[str, Any], *keys: str) -> bool | None:
    for key in keys:
        if key not in record:
            continue
        value = record.get(key)
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if pd.isna(value):
                continue
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "y", "passed", "ready", "candidate-ready"}:
                return True
            if normalized in {"0", "false", "no", "n", "blocked", "missing", "not_ready", "diagnostic_or_incomplete"}:
                return False
            if normalized in {"", "nan", "none", "null"}:
                continue
    return None


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or pd.isna(value):
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False).encode("utf-8")
    return sha256(encoded).hexdigest()


def _frame_hash(frame: pd.DataFrame) -> str:
    if frame.empty:
        return _stable_hash({"columns": list(frame.columns), "rows": []})
    rows = frame.astype(object).where(pd.notna(frame), None).to_dict("records")
    return _stable_hash({"columns": list(frame.columns), "rows": rows})


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
