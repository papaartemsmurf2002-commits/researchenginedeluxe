from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from tradingbotsuite.research.live_readiness import research_boundary_metadata
from tradingbotsuite.research_discovery.state import atomic_write_json


DISCOVERY_EXIT_LAB_VERSION = "discovery-exit-lab-v1"
DISCOVERY_EXIT_LAB_MANIFEST_VERSION = "discovery-exit-lab-manifest-v1"
DISCOVERY_EXIT_LAB_ARTIFACT_VERSION = "discovery-exit-lab-artifacts-v1"
DEFAULT_ENTRY_GROUP_COLUMNS = (
    "symbol",
    "timeframe",
    "side",
    "split_id",
    "validation_split_id",
    "strategy_id",
    "feature_set_id",
    "feature_column_set_id",
    "regime_mode",
    "regime_detector_type",
    "holding_window",
    "cost_model_id",
    "cost_stress_id",
    "cost_stress_status",
    "label_horizon",
    "distance_metric",
    "k",
    "min_neighbor_count",
    "parameters_json",
)
MATCHED_GROUP_EVIDENCE_COLUMNS = DEFAULT_ENTRY_GROUP_COLUMNS
SUPPORTED_EXIT_FAMILIES = (
    "fixed_holding",
    "barrier",
    "basis_premium_normalization",
    "gmm_transition",
    "knn_remaining_edge",
    "knn_dynamic_barrier",
    "funding_oi_supported",
    "funding_oi",
    "hmm_knn",
    "trailing_risk",
    "true_hmm_transition",
    "liquidity_adverse_selection",
)
EXIT_FAMILY_LABELS = {
    "fixed_holding": "fixed holding reference",
    "barrier": "price/volatility barrier",
    "basis_premium_normalization": "basis/premium normalization",
    "gmm_transition": "current GMM regime transition",
    "knn_remaining_edge": "KNN remaining-edge",
    "knn_dynamic_barrier": "KNN dynamic barrier",
    "funding_oi_supported": "supported funding/OI context",
    "funding_oi": "legacy supported funding/OI context",
    "hmm_knn": "legacy regime/KNN-adjacent label",
    "trailing_risk": "trailing/risk control",
    "true_hmm_transition": "true HMM transition deferred",
    "liquidity_adverse_selection": "liquidity/depth adverse-selection deferred",
}
DEFERRED_EXIT_FAMILY_REASONS = {
    "true_hmm_transition": "true_hmm_backend_deferred",
    "liquidity_adverse_selection": "durable_depth_l2_evidence_deferred",
}
PASSING_COST_STRESS_STATUSES = {"pass", "passed", "survived", "stable", "ok", "complete"}
ENTRY_LEAD_EVIDENCE_FIELDS = (
    "run_id",
    "trial_id",
    "candidate_id",
    "candidate_family",
    "score",
    "discovery_screen_score_v2",
    "final_score",
    "feature_column_set_id",
    "regime_mode",
    "regime_detector_type",
    "label_horizon",
    "distance_metric",
    "k",
    "min_neighbor_count",
    "independent_event_count",
    "event_signal_rate",
    "record_sha256",
)


@dataclass(frozen=True, slots=True)
class ExitLabComparisonSpec:
    comparison_id: str
    exit_family: str
    treatment_selector: Mapping[str, Any]
    baseline_selector: Mapping[str, Any] = field(default_factory=lambda: {"exit_policy_id": "fixed_holding_window"})
    min_entry_trade_count: int = 10
    min_treatment_trade_count: int = 1
    min_score_delta: float = 0.0
    notes: str = ""

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ExitLabComparisonSpec":
        if not isinstance(payload, Mapping):
            raise ValueError("exit lab comparisons must be JSON objects")
        comparison_id = str(payload.get("comparison_id") or "").strip()
        if not comparison_id:
            raise ValueError("exit lab comparison_id is required")
        family = str(payload.get("exit_family") or "").strip()
        if family not in SUPPORTED_EXIT_FAMILIES:
            raise ValueError(f"unsupported exit lab family: {family}")
        treatment = payload.get("treatment_selector") or {}
        baseline = payload.get("baseline_selector") or {"exit_policy_id": "fixed_holding_window"}
        if not isinstance(treatment, Mapping) or not treatment:
            raise ValueError(f"exit lab treatment_selector is required: {comparison_id}")
        if not isinstance(baseline, Mapping) or not baseline:
            raise ValueError(f"exit lab baseline_selector is required: {comparison_id}")
        return cls(
            comparison_id=comparison_id,
            exit_family=family,
            treatment_selector=dict(treatment),
            baseline_selector=dict(baseline),
            min_entry_trade_count=max(0, int(payload.get("min_entry_trade_count", 10))),
            min_treatment_trade_count=max(0, int(payload.get("min_treatment_trade_count", 1))),
            min_score_delta=float(payload.get("min_score_delta", 0.0)),
            notes=str(payload.get("notes", "")),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "comparison_id": self.comparison_id,
            "exit_family": self.exit_family,
            "treatment_selector": dict(self.treatment_selector),
            "baseline_selector": dict(self.baseline_selector),
            "min_entry_trade_count": int(self.min_entry_trade_count),
            "min_treatment_trade_count": int(self.min_treatment_trade_count),
            "min_score_delta": float(self.min_score_delta),
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class DiscoveryExitLabSpec:
    lab_id: str = "discovery_exit_lab_v4"
    entry_group_columns: tuple[str, ...] = DEFAULT_ENTRY_GROUP_COLUMNS
    comparisons: tuple[ExitLabComparisonSpec, ...] = ()

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "DiscoveryExitLabSpec":
        if not isinstance(payload, Mapping):
            raise ValueError("discovery exit lab spec must be a JSON object")
        comparisons = tuple(
            ExitLabComparisonSpec.from_payload(item)
            for item in payload.get("comparisons", ())
        )
        if not comparisons:
            raise ValueError("at least one exit lab comparison is required")
        return cls(
            lab_id=str(payload.get("lab_id") or "discovery_exit_lab_v4"),
            entry_group_columns=tuple(str(item) for item in payload.get("entry_group_columns", DEFAULT_ENTRY_GROUP_COLUMNS)),
            comparisons=comparisons,
        )

    @classmethod
    def from_path(cls, path: Path) -> "DiscoveryExitLabSpec":
        payload = json.loads(Path(path).expanduser().read_text(encoding="utf-8-sig"))
        return cls.from_payload(payload)

    def to_payload(self) -> dict[str, Any]:
        return {
            "lab_id": self.lab_id,
            "exit_lab_version": DISCOVERY_EXIT_LAB_VERSION,
            "entry_group_columns": list(self.entry_group_columns),
            "comparisons": [comparison.to_payload() for comparison in self.comparisons],
        }


@dataclass(frozen=True, slots=True)
class DiscoveryExitLabResult:
    manifest: dict[str, Any]
    matrix: pd.DataFrame
    family_summary: pd.DataFrame
    candidate_gates: pd.DataFrame


@dataclass(frozen=True, slots=True)
class DiscoveryExitLabArtifactResult:
    output_dir: Path
    manifest_path: Path
    matrix_path: Path
    family_summary_path: Path
    candidate_gates_path: Path


def discovery_entry_lead_evidence_sha256(record: Mapping[str, Any]) -> str:
    payload = {field: _stable_scalar(record.get(field, "")) for field in ENTRY_LEAD_EVIDENCE_FIELDS}
    return _stable_hash(payload)


def build_discovery_exit_lab(
    rankings: pd.DataFrame,
    *,
    spec: DiscoveryExitLabSpec,
) -> DiscoveryExitLabResult:
    matrix = _exit_lab_matrix(rankings, spec=spec)
    summary = _family_summary(matrix)
    candidate_gates = _candidate_gates(matrix)
    manifest = {
        "exit_lab_manifest_version": DISCOVERY_EXIT_LAB_MANIFEST_VERSION,
        "exit_lab_version": DISCOVERY_EXIT_LAB_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "spec": spec.to_payload(),
        "spec_sha256": _stable_hash(spec.to_payload()),
        "input_ranking_row_count": int(len(rankings)),
        "comparison_count": int(len(spec.comparisons)),
        "matrix_row_count": int(len(matrix)),
        "family_summary_row_count": int(len(summary)),
        "candidate_gate_row_count": int(len(candidate_gates)),
        "supported_exit_families": list(SUPPORTED_EXIT_FAMILIES),
        "exit_family_labels": dict(EXIT_FAMILY_LABELS),
        "deferred_exit_families": dict(DEFERRED_EXIT_FAMILY_REASONS),
        "comparison_grouping": {
            "entry_group_columns": list(spec.entry_group_columns),
            "matched_grouping_evidence_columns": list(MATCHED_GROUP_EVIDENCE_COLUMNS),
            "side_split_regime_holding_cost_feature_knn_setup_matched_where_present": True,
        },
        "trade_density_guard": {
            "baseline_exit_required": True,
            "entry_candidates_below_floor_are_not_compared": True,
            "trade_count_column": "trade_count",
        },
        "default_guard": {
            "exit_winner_is_research_only": True,
            "exit_winner_does_not_change_default_policy": True,
            "candidate_pack_bridge_unchanged": True,
        },
        "decision_counts": _decision_counts(matrix),
        "live_fetch_used": False,
        "order_placement_used": False,
        "runtime_mode_changed": False,
    }
    manifest["matrix_sha256"] = _frame_hash(matrix)
    manifest["family_summary_sha256"] = _frame_hash(summary)
    manifest["candidate_gates_sha256"] = _frame_hash(candidate_gates)
    return DiscoveryExitLabResult(
        manifest=manifest,
        matrix=matrix,
        family_summary=summary,
        candidate_gates=candidate_gates,
    )


def write_discovery_exit_lab_artifacts(
    output_dir: Path,
    result: DiscoveryExitLabResult,
) -> DiscoveryExitLabArtifactResult:
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "discovery_exit_lab_manifest.json"
    matrix_path = output_dir / "discovery_exit_lab_matrix.parquet"
    family_summary_path = output_dir / "discovery_exit_family_summary.parquet"
    candidate_gates_path = output_dir / "discovery_exit_lab_candidate_gates.parquet"
    result.matrix.to_parquet(matrix_path, index=False)
    result.family_summary.to_parquet(family_summary_path, index=False)
    result.candidate_gates.to_parquet(candidate_gates_path, index=False)
    manifest = dict(result.manifest)
    manifest["artifact_version"] = DISCOVERY_EXIT_LAB_ARTIFACT_VERSION
    manifest["required_outputs"] = {
        "discovery_exit_lab_manifest": str(manifest_path),
        "discovery_exit_lab_matrix": str(matrix_path),
        "discovery_exit_family_summary": str(family_summary_path),
        "discovery_exit_lab_candidate_gates": str(candidate_gates_path),
    }
    manifest["discovery_exit_lab_matrix_sha256"] = _file_sha256(matrix_path)
    manifest["discovery_exit_family_summary_sha256"] = _file_sha256(family_summary_path)
    manifest["discovery_exit_lab_candidate_gates_sha256"] = _file_sha256(candidate_gates_path)
    atomic_write_json(manifest_path, manifest)
    return DiscoveryExitLabArtifactResult(
        output_dir=output_dir,
        manifest_path=manifest_path,
        matrix_path=matrix_path,
        family_summary_path=family_summary_path,
        candidate_gates_path=candidate_gates_path,
    )


def _exit_lab_matrix(rankings: pd.DataFrame, *, spec: DiscoveryExitLabSpec) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    groups = _ranking_groups(rankings, spec.entry_group_columns)
    if not groups:
        groups = [({}, rankings)]
    for comparison in spec.comparisons:
        for group_values, group in groups:
            baseline = _best_row(_matching_rows(group, comparison.baseline_selector))
            treatment = _best_row(_matching_rows(group, comparison.treatment_selector))
            rows.append(_comparison_row(comparison, group_values=group_values, baseline=baseline, treatment=treatment))
    return pd.DataFrame(rows, columns=_matrix_columns(spec.entry_group_columns))


def _comparison_row(
    comparison: ExitLabComparisonSpec,
    *,
    group_values: Mapping[str, Any],
    baseline: Mapping[str, Any] | None,
    treatment: Mapping[str, Any] | None,
) -> dict[str, Any]:
    reasons: list[str] = []
    baseline_trade_count = _int_value(baseline, "trade_count")
    treatment_trade_count = _int_value(treatment, "trade_count")
    baseline_score = _score(baseline)
    treatment_score = _score(treatment)
    deferred_reason = _deferred_reason(comparison.exit_family)
    if baseline is None:
        reasons.append("baseline_exit_evidence_missing")
    if treatment is None:
        reasons.append("treatment_exit_evidence_missing")
    treatment_cost_status = _cost_stress_behavior(treatment)
    if treatment is not None and not _cost_stress_status_passes(treatment_cost_status):
        if treatment_cost_status == "unknown":
            reasons.append("cost_stress_evidence_missing")
        else:
            reasons.append(f"cost_stress_status_not_passing:{treatment_cost_status}")
    if baseline is not None and baseline_trade_count < comparison.min_entry_trade_count:
        reasons.append("entry_trade_count_below_exit_lab_floor")
    if treatment is not None and treatment_trade_count < comparison.min_treatment_trade_count:
        reasons.append("treatment_trade_count_below_exit_lab_floor")

    if "entry_trade_count_below_exit_lab_floor" in reasons:
        decision = "skipped_low_trade_density"
    elif deferred_reason:
        decision = "deferred_evidence"
        reasons.append(deferred_reason)
    elif baseline is None or treatment is None:
        decision = "pending_evidence"
    elif comparison.exit_family == "fixed_holding" and treatment_score - baseline_score >= comparison.min_score_delta:
        decision = "passed"
    elif any(reason.startswith("cost_stress_") for reason in reasons):
        decision = "pending_evidence" if "cost_stress_evidence_missing" in reasons else "failed"
    elif treatment_score - baseline_score > comparison.min_score_delta:
        decision = "passed"
    else:
        decision = "failed"
        reasons.append("treatment_exit_did_not_beat_baseline")

    score_delta = treatment_score - baseline_score if baseline is not None and treatment is not None else None
    return {
        "comparison_id": comparison.comparison_id,
        "exit_family": comparison.exit_family,
        "exit_family_label": _exit_family_label(comparison.exit_family),
        **{f"entry_{key}": value for key, value in group_values.items()},
        "decision": decision,
        "failure_reasons": ";".join(reasons),
        "exit_lab_status": _comparison_status(decision),
        "exit_lab_best_family": comparison.exit_family if decision == "passed" else "",
        "entry_candidate_id": _entry_candidate_id(baseline, treatment),
        "research_candidate_id": _research_candidate_id(baseline, treatment),
        "entry_lead_evidence_sha256": _entry_lead_hash(baseline, treatment),
        "entry_lead_record_sha256": _entry_lead_hash(baseline, treatment),
        "baseline_candidate_id": _text_value(baseline, "candidate_id"),
        "baseline_exit_policy_id": _text_value(baseline, "exit_policy_id"),
        "baseline_exit_policy_params_json": _text_value(baseline, "exit_policy_params_json"),
        "baseline_final_score": baseline_score,
        "baseline_trade_count": baseline_trade_count,
        "treatment_candidate_id": _text_value(treatment, "candidate_id"),
        "treatment_exit_policy_id": _text_value(treatment, "exit_policy_id"),
        "treatment_exit_policy_params_json": _text_value(treatment, "exit_policy_params_json"),
        "treatment_final_score": treatment_score,
        "treatment_trade_count": treatment_trade_count,
        "score_delta": score_delta,
        "fixed_holding_score_delta": score_delta,
        "fixed_holding_comparator_delta": score_delta,
        "cost_stress_behavior": _cost_stress_behavior(treatment, baseline),
        "cost_stress_status": _cost_stress_behavior(treatment, baseline),
        "no_improvement_reason": "no_exit_improved_executable_expectancy" if decision == "failed" else "",
        "deferred_reason": deferred_reason if decision == "deferred_evidence" else "",
        "min_score_delta": float(comparison.min_score_delta),
        "min_entry_trade_count": int(comparison.min_entry_trade_count),
        "min_treatment_trade_count": int(comparison.min_treatment_trade_count),
        "entry_density_passed": bool(baseline is not None and baseline_trade_count >= comparison.min_entry_trade_count),
        "exit_lab_winner": bool(decision == "passed"),
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "notes": comparison.notes,
    }


def _family_summary(matrix: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if matrix.empty:
        return pd.DataFrame(rows, columns=_summary_columns())
    for family, group in matrix.groupby("exit_family", dropna=False):
        decisions = group["decision"].astype(str).value_counts().to_dict()
        rows.append(
            {
                "exit_family": str(family),
                "exit_family_label": _exit_family_label(str(family)),
                "comparison_count": int(len(group)),
                "passed_count": int(decisions.get("passed", 0)),
                "failed_count": int(decisions.get("failed", 0)),
                "pending_count": int(decisions.get("pending_evidence", 0)),
                "deferred_count": int(decisions.get("deferred_evidence", 0)),
                "skipped_low_trade_density_count": int(decisions.get("skipped_low_trade_density", 0)),
                "winner_candidate_ids": sorted(
                    str(value)
                    for value in group.loc[group["decision"].eq("passed"), "treatment_candidate_id"].dropna().tolist()
                    if str(value)
                ),
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
            }
        )
    return pd.DataFrame(rows, columns=_summary_columns())


def _candidate_gates(matrix: pd.DataFrame) -> pd.DataFrame:
    if matrix.empty:
        return pd.DataFrame([], columns=_candidate_gate_columns())
    keys = [column for column in ("entry_candidate_id", "research_candidate_id", "entry_lead_evidence_sha256") if column in matrix.columns]
    if not keys:
        return pd.DataFrame([], columns=_candidate_gate_columns())
    rows: list[dict[str, Any]] = []
    for group_keys, group in matrix.groupby(keys, dropna=False):
        if len(keys) == 1:
            group_keys = (group_keys,)
        values = dict(zip(keys, group_keys, strict=True))
        rows.append(_candidate_gate_row(group, values=values))
    return pd.DataFrame(rows, columns=_candidate_gate_columns())


def _candidate_gate_row(group: pd.DataFrame, *, values: Mapping[str, Any]) -> dict[str, Any]:
    non_fixed = group.loc[group["exit_family"].astype(str).ne("fixed_holding")].copy()
    passed = non_fixed.loc[non_fixed["decision"].astype(str).eq("passed")].copy()
    if not passed.empty:
        ordered = passed.sort_values(["score_delta", "treatment_final_score"], ascending=[False, False], kind="mergesort")
        best = ordered.iloc[0].to_dict()
        reasons: list[str] = []
        gate_status = "passed"
    else:
        best = _best_candidate_gate_reference(group)
        reasons = _candidate_gate_reasons(group)
        gate_status = "blocked"
    status = "complete" if str(best.get("decision") or "") in {"passed", "failed"} else _comparison_status(str(best.get("decision") or ""))
    return {
        "entry_candidate_id": str(values.get("entry_candidate_id") or ""),
        "candidate_id": str(values.get("research_candidate_id") or ""),
        "entry_lead_evidence_sha256": str(values.get("entry_lead_evidence_sha256") or ""),
        "entry_lead_record_sha256": str(values.get("entry_lead_evidence_sha256") or ""),
        **_entry_group_evidence(best),
        "exit_lab_status": status,
        "exit_lab_gate_status": gate_status,
        "exit_lab_reasons": "|".join(reasons),
        "exit_lab_best_family": str(best.get("exit_family") or ""),
        "best_comparison_id": str(best.get("comparison_id") or ""),
        "baseline_candidate_id": str(best.get("baseline_candidate_id") or ""),
        "baseline_exit_policy_id": str(best.get("baseline_exit_policy_id") or ""),
        "baseline_final_score": _float_value(best, "baseline_final_score"),
        "baseline_trade_count": _int_value(best, "baseline_trade_count"),
        "treatment_candidate_id": str(best.get("treatment_candidate_id") or ""),
        "treatment_exit_policy_id": str(best.get("treatment_exit_policy_id") or ""),
        "treatment_final_score": _float_value(best, "treatment_final_score"),
        "treatment_trade_count": _int_value(best, "treatment_trade_count"),
        "fixed_holding_score_delta": _float_value(best, "fixed_holding_score_delta"),
        "fixed_holding_comparator_delta": _float_value(best, "fixed_holding_comparator_delta"),
        "cost_stress_behavior": str(best.get("cost_stress_behavior") or "unknown"),
        "cost_stress_status": str(best.get("cost_stress_status") or "unknown"),
        "no_improvement_reason": str(best.get("no_improvement_reason") or ""),
        "deferred_reason": str(best.get("deferred_reason") or ""),
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
    }


def _best_candidate_gate_reference(group: pd.DataFrame) -> dict[str, Any]:
    non_fixed = group.loc[group["exit_family"].astype(str).ne("fixed_holding")].copy()
    if not non_fixed.empty:
        ordered = non_fixed.sort_values(["score_delta", "treatment_final_score"], ascending=[False, False], kind="mergesort")
        return ordered.iloc[0].to_dict()
    fixed = group.loc[group["exit_family"].astype(str).eq("fixed_holding")].copy()
    if not fixed.empty:
        return fixed.iloc[0].to_dict()
    return group.iloc[0].to_dict()


def _candidate_gate_reasons(group: pd.DataFrame) -> list[str]:
    non_fixed = group.loc[group["exit_family"].astype(str).ne("fixed_holding")]
    reasons: list[str] = []
    if non_fixed.empty:
        reasons.append("exit_lab_fixed_holding_only")
    if not non_fixed.loc[non_fixed["decision"].astype(str).eq("failed")].empty:
        reasons.append("exit_lab_no_improving_exit_over_fixed_holding")
    if not non_fixed.loc[non_fixed["decision"].astype(str).eq("pending_evidence")].empty:
        reasons.append("exit_lab_pending_evidence")
    if not non_fixed.loc[non_fixed["decision"].astype(str).eq("deferred_evidence")].empty:
        reasons.append("exit_lab_deferred_evidence")
    if not non_fixed.loc[non_fixed["decision"].astype(str).eq("skipped_low_trade_density")].empty:
        reasons.append("exit_lab_insufficient_trade_density")
    if not reasons:
        reasons.append("exit_lab_status_not_passed")
    return list(dict.fromkeys(reasons))


def _ranking_groups(frame: pd.DataFrame, columns: tuple[str, ...]) -> list[tuple[dict[str, Any], pd.DataFrame]]:
    existing = [column for column in columns if column in frame.columns]
    if not existing:
        return []
    groups: list[tuple[dict[str, Any], pd.DataFrame]] = []
    for keys, group in frame.groupby(existing, dropna=False):
        if len(existing) == 1:
            keys = (keys,)
        groups.append((dict(zip(existing, keys, strict=True)), group.copy()))
    return groups


def _matching_rows(frame: pd.DataFrame, selector: Mapping[str, Any]) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    mask = pd.Series([True] * len(frame), index=frame.index)
    for key, value in selector.items():
        if key not in frame.columns:
            return frame.iloc[0:0].copy()
        allowed = set(value) if isinstance(value, (list, tuple, set)) and not isinstance(value, str) else {value}
        mask &= frame[key].map(lambda item: item in allowed)
    return frame.loc[mask].copy()


def _best_row(frame: pd.DataFrame) -> dict[str, Any] | None:
    if frame.empty:
        return None
    sort_columns = [column for column in ("final_score", "trade_count") if column in frame.columns]
    if not sort_columns:
        return frame.iloc[0].to_dict()
    ordered = frame.sort_values(sort_columns, ascending=[False] * len(sort_columns), kind="mergesort")
    return ordered.iloc[0].to_dict()


def _score(row: Mapping[str, Any] | None) -> float:
    if row is None:
        return 0.0
    for key in ("final_score", "optimizer_final_score", "score"):
        if key in row:
            return _float_value(row, key)
    return 0.0


def _comparison_status(decision: str) -> str:
    if decision in {"passed", "failed"}:
        return "complete"
    if decision == "pending_evidence":
        return "pending"
    if decision == "deferred_evidence":
        return "deferred"
    if decision == "skipped_low_trade_density":
        return "diagnostic_only"
    return "incomplete"


def _exit_family_label(exit_family: str) -> str:
    return str(EXIT_FAMILY_LABELS.get(str(exit_family), str(exit_family)))


def _deferred_reason(exit_family: str) -> str:
    return str(DEFERRED_EXIT_FAMILY_REASONS.get(str(exit_family), ""))


def _entry_group_evidence(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        f"entry_{column}": _stable_scalar(row.get(f"entry_{column}", ""))
        for column in MATCHED_GROUP_EVIDENCE_COLUMNS
    }


def _entry_candidate_id(*rows: Mapping[str, Any] | None) -> str:
    for row in rows:
        value = _text_value(row, "entry_candidate_id") or _text_value(row, "entry_lead_candidate_id") or _text_value(row, "discovery_candidate_id")
        if value:
            return value
    return ""


def _research_candidate_id(*rows: Mapping[str, Any] | None) -> str:
    for row in rows:
        value = _text_value(row, "research_candidate_id")
        if value:
            return value
    return _entry_candidate_id(*rows)


def _entry_lead_hash(*rows: Mapping[str, Any] | None) -> str:
    for row in rows:
        value = _text_value(row, "entry_lead_evidence_sha256") or _text_value(row, "entry_lead_record_sha256")
        if value:
            return value
    return ""


def _cost_stress_behavior(*rows: Mapping[str, Any] | None) -> str:
    for row in rows:
        value = _text_value(row, "cost_stress_behavior") or _text_value(row, "cost_stress_status")
        if value:
            return value.strip().lower()
    return "unknown"


def _cost_stress_status_passes(value: str) -> bool:
    return str(value or "").strip().lower() in PASSING_COST_STRESS_STATUSES


def _float_value(row: Mapping[str, Any] | None, key: str) -> float:
    if row is None:
        return 0.0
    try:
        value = row.get(key, 0.0)
        if pd.isna(value):
            return 0.0
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    return parsed if math.isfinite(parsed) else 0.0


def _int_value(row: Mapping[str, Any] | None, key: str) -> int:
    if row is None:
        return 0
    try:
        value = row.get(key, 0)
        if pd.isna(value):
            return 0
        return int(value)
    except (TypeError, ValueError):
        return 0


def _text_value(row: Mapping[str, Any] | None, key: str) -> str:
    if row is None:
        return ""
    value = row.get(key, "")
    if value is None or pd.isna(value):
        return ""
    return str(value)


def _decision_counts(matrix: pd.DataFrame) -> dict[str, int]:
    if matrix.empty:
        return {}
    return {str(key): int(value) for key, value in matrix["decision"].value_counts().sort_index().items()}


def _matrix_columns(entry_group_columns: tuple[str, ...] = ()) -> list[str]:
    group_columns = _entry_group_matrix_columns(entry_group_columns)
    return [
        "comparison_id",
        "exit_family",
        "exit_family_label",
        *group_columns,
        "decision",
        "failure_reasons",
        "exit_lab_status",
        "exit_lab_best_family",
        "entry_candidate_id",
        "research_candidate_id",
        "entry_lead_evidence_sha256",
        "entry_lead_record_sha256",
        "baseline_candidate_id",
        "baseline_exit_policy_id",
        "baseline_exit_policy_params_json",
        "baseline_final_score",
        "baseline_trade_count",
        "treatment_candidate_id",
        "treatment_exit_policy_id",
        "treatment_exit_policy_params_json",
        "treatment_final_score",
        "treatment_trade_count",
        "score_delta",
        "fixed_holding_score_delta",
        "fixed_holding_comparator_delta",
        "cost_stress_behavior",
        "cost_stress_status",
        "no_improvement_reason",
        "deferred_reason",
        "min_score_delta",
        "min_entry_trade_count",
        "min_treatment_trade_count",
        "entry_density_passed",
        "exit_lab_winner",
        "research_only",
        "observe_only",
        "promotion_ready",
        "notes",
    ]


def _entry_group_matrix_columns(entry_group_columns: tuple[str, ...] = ()) -> list[str]:
    columns = [*MATCHED_GROUP_EVIDENCE_COLUMNS, *entry_group_columns]
    return [f"entry_{column}" for column in dict.fromkeys(str(column) for column in columns)]


def _summary_columns() -> list[str]:
    return [
        "exit_family",
        "exit_family_label",
        "comparison_count",
        "passed_count",
        "failed_count",
        "pending_count",
        "deferred_count",
        "skipped_low_trade_density_count",
        "winner_candidate_ids",
        "research_only",
        "observe_only",
        "promotion_ready",
    ]


def _candidate_gate_columns() -> list[str]:
    return [
        "entry_candidate_id",
        "candidate_id",
        "entry_lead_evidence_sha256",
        "entry_lead_record_sha256",
        *_entry_group_matrix_columns(),
        "exit_lab_status",
        "exit_lab_gate_status",
        "exit_lab_reasons",
        "exit_lab_best_family",
        "best_comparison_id",
        "baseline_candidate_id",
        "baseline_exit_policy_id",
        "baseline_final_score",
        "baseline_trade_count",
        "treatment_candidate_id",
        "treatment_exit_policy_id",
        "treatment_final_score",
        "treatment_trade_count",
        "fixed_holding_score_delta",
        "fixed_holding_comparator_delta",
        "cost_stress_behavior",
        "cost_stress_status",
        "no_improvement_reason",
        "deferred_reason",
        "research_only",
        "observe_only",
        "promotion_ready",
    ]


def _stable_hash(payload: Any) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False).encode("utf-8")).hexdigest()


def _stable_scalar(value: Any) -> Any:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(value, bool) or value.__class__.__name__ == "bool_":
        return bool(value)
    if isinstance(value, int) or value.__class__.__name__.startswith("int"):
        return int(value)
    if isinstance(value, float) or value.__class__.__name__.startswith("float"):
        return float(value)
    return str(value)


def _frame_hash(frame: pd.DataFrame) -> str:
    if frame.empty:
        return _stable_hash({"columns": list(frame.columns), "rows": []})
    rows = frame.astype(object).where(pd.notna(frame), None).to_dict("records")
    return _stable_hash({"columns": list(frame.columns), "rows": rows})


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
