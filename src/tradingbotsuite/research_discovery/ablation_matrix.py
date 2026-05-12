from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from tradingbotsuite.research.live_readiness import research_boundary_metadata
from tradingbotsuite.research_discovery.feature_sets import (
    DiscoveryFeatureColumnSetManifest,
    load_feature_column_set_manifest,
)
from tradingbotsuite.research_discovery.state import atomic_write_json


PERP_FILTER_ABLATION_MATRIX_VERSION = "discovery-perp-filter-ablation-matrix-v1"
PERP_FILTER_ABLATION_MANIFEST_VERSION = "discovery-perp-filter-ablation-manifest-v1"
PERP_FILTER_ABLATION_ARTIFACT_VERSION = "discovery-perp-filter-ablation-artifacts-v1"
DEFAULT_AXES = (
    "no_perp",
    "perp_feature",
    "perp_filter",
    "perp_strategy",
    "perp_exit",
)
DEFAULT_GROUP_COLUMNS = (
    "holding_window",
    "exit_policy_params_json",
)
MATCHED_FILTER_DECISION_POLICY_V2 = "matched_filter_ablation_v2"
DEFAULT_MATCHED_GROUP_COLUMNS = (
    "symbol",
    "timeframe",
    "entry_family",
    "feature_set_id",
    "feature_column_set_id",
    "label_horizon",
    "regime_mode",
    "distance_metric",
    "k",
    "min_neighbor_count",
    "holding_window",
    "exit_policy_id",
    "exit_policy_params_json",
    "split_id",
    "cost_model_id",
)


@dataclass(frozen=True, slots=True)
class AblationComparisonSpec:
    comparison_id: str
    axis: str
    treatment_selector: Mapping[str, Any]
    comparator_selector: Mapping[str, Any] = field(default_factory=dict)
    min_score_delta: float = 0.0
    min_trade_count: int = 1
    max_missingness_rate: float = 1.0
    requires_comparator: bool = True
    filter_default_candidate: bool = False
    filter_family: str = ""
    required_finite_columns: tuple[str, ...] = ()
    min_sample_retention_ratio: float = 0.50
    min_split_consistency: float = 0.0
    min_cost_stress_survival: float = 0.0
    notes: str = ""

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "AblationComparisonSpec":
        if not isinstance(payload, Mapping):
            raise ValueError("ablation comparisons must be JSON objects")
        comparison_id = str(payload.get("comparison_id") or "").strip()
        if not comparison_id:
            raise ValueError("ablation comparison_id is required")
        axis = str(payload.get("axis") or "").strip()
        if axis not in DEFAULT_AXES:
            raise ValueError(f"unsupported ablation axis: {axis}")
        treatment = payload.get("treatment_selector") or {}
        comparator = payload.get("comparator_selector") or {}
        if not isinstance(treatment, Mapping) or not treatment:
            raise ValueError(f"ablation treatment_selector is required: {comparison_id}")
        if not isinstance(comparator, Mapping):
            raise ValueError(f"ablation comparator_selector must be an object: {comparison_id}")
        return cls(
            comparison_id=comparison_id,
            axis=axis,
            treatment_selector=dict(treatment),
            comparator_selector=dict(comparator),
            min_score_delta=float(payload.get("min_score_delta", 0.0)),
            min_trade_count=max(0, int(payload.get("min_trade_count", 1))),
            max_missingness_rate=float(payload.get("max_missingness_rate", 1.0)),
            requires_comparator=bool(payload.get("requires_comparator", True)),
            filter_default_candidate=bool(payload.get("filter_default_candidate", False)),
            filter_family=str(payload.get("filter_family") or ""),
            required_finite_columns=tuple(str(item) for item in payload.get("required_finite_columns", ())),
            min_sample_retention_ratio=float(payload.get("min_sample_retention_ratio", 0.50)),
            min_split_consistency=float(payload.get("min_split_consistency", 0.0)),
            min_cost_stress_survival=float(payload.get("min_cost_stress_survival", 0.0)),
            notes=str(payload.get("notes", "")),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "comparison_id": self.comparison_id,
            "axis": self.axis,
            "treatment_selector": dict(self.treatment_selector),
            "comparator_selector": dict(self.comparator_selector),
            "min_score_delta": float(self.min_score_delta),
            "min_trade_count": int(self.min_trade_count),
            "max_missingness_rate": float(self.max_missingness_rate),
            "requires_comparator": bool(self.requires_comparator),
            "filter_default_candidate": bool(self.filter_default_candidate),
            "filter_family": self.filter_family,
            "required_finite_columns": list(self.required_finite_columns),
            "min_sample_retention_ratio": float(self.min_sample_retention_ratio),
            "min_split_consistency": float(self.min_split_consistency),
            "min_cost_stress_survival": float(self.min_cost_stress_survival),
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class PerpFilterAblationMatrixSpec:
    matrix_id: str = "perp_filter_ablation_matrix_v4"
    group_columns: tuple[str, ...] = DEFAULT_GROUP_COLUMNS
    required_group_columns: tuple[str, ...] = ()
    decision_policy_version: str = "legacy_perp_filter_ablation_v1"
    comparisons: tuple[AblationComparisonSpec, ...] = ()
    feature_column_sets_path: Path | None = None
    min_feature_combination_score_delta: float = 0.0
    min_feature_combination_trade_count: int = 1

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "PerpFilterAblationMatrixSpec":
        if not isinstance(payload, Mapping):
            raise ValueError("perp filter ablation matrix spec must be a JSON object")
        comparisons = tuple(
            AblationComparisonSpec.from_payload(item)
            for item in payload.get("comparisons", ())
        )
        if not comparisons:
            raise ValueError("at least one ablation comparison is required")
        raw_feature_sets_path = payload.get("feature_column_sets_path")
        return cls(
            matrix_id=str(payload.get("matrix_id") or "perp_filter_ablation_matrix_v4"),
            group_columns=tuple(str(item) for item in payload.get("group_columns", DEFAULT_GROUP_COLUMNS)),
            required_group_columns=tuple(str(item) for item in payload.get("required_group_columns", ())),
            decision_policy_version=str(payload.get("decision_policy_version") or "legacy_perp_filter_ablation_v1"),
            comparisons=comparisons,
            feature_column_sets_path=Path(str(raw_feature_sets_path)).expanduser() if raw_feature_sets_path else None,
            min_feature_combination_score_delta=float(payload.get("min_feature_combination_score_delta", 0.0)),
            min_feature_combination_trade_count=max(0, int(payload.get("min_feature_combination_trade_count", 1))),
        )

    @classmethod
    def from_path(cls, path: Path) -> "PerpFilterAblationMatrixSpec":
        path = Path(path).expanduser()
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        spec = cls.from_payload(payload)
        feature_sets_path = spec.feature_column_sets_path
        if feature_sets_path is not None and not feature_sets_path.is_absolute():
            feature_sets_path = (path.parent / feature_sets_path).resolve()
            return cls(
                matrix_id=spec.matrix_id,
                group_columns=spec.group_columns,
                required_group_columns=spec.required_group_columns,
                decision_policy_version=spec.decision_policy_version,
                comparisons=spec.comparisons,
                feature_column_sets_path=feature_sets_path,
                min_feature_combination_score_delta=spec.min_feature_combination_score_delta,
                min_feature_combination_trade_count=spec.min_feature_combination_trade_count,
            )
        return spec

    def to_payload(self) -> dict[str, Any]:
        return {
            "matrix_id": self.matrix_id,
            "matrix_version": PERP_FILTER_ABLATION_MATRIX_VERSION,
            "group_columns": list(self.group_columns),
            "required_group_columns": list(self.required_group_columns),
            "decision_policy_version": self.decision_policy_version,
            "feature_column_sets_path": str(self.feature_column_sets_path) if self.feature_column_sets_path is not None else None,
            "min_feature_combination_score_delta": float(self.min_feature_combination_score_delta),
            "min_feature_combination_trade_count": int(self.min_feature_combination_trade_count),
            "comparisons": [comparison.to_payload() for comparison in self.comparisons],
        }


@dataclass(frozen=True, slots=True)
class PerpFilterAblationMatrixResult:
    manifest: dict[str, Any]
    matrix: pd.DataFrame
    feature_combination_stability: pd.DataFrame


@dataclass(frozen=True, slots=True)
class PerpFilterAblationArtifactResult:
    output_dir: Path
    manifest_path: Path
    matrix_path: Path
    feature_combination_stability_path: Path


def build_perp_filter_ablation_matrix(
    rankings: pd.DataFrame,
    *,
    spec: PerpFilterAblationMatrixSpec,
    feature_column_set_manifest: DiscoveryFeatureColumnSetManifest | None = None,
    feature_combination_evidence: pd.DataFrame | None = None,
) -> PerpFilterAblationMatrixResult:
    if feature_column_set_manifest is None and spec.feature_column_sets_path is not None:
        feature_column_set_manifest = load_feature_column_set_manifest(spec.feature_column_sets_path)
    matrix = _comparison_matrix(rankings, spec=spec)
    stability = _feature_combination_stability(
        feature_column_set_manifest,
        evidence=feature_combination_evidence,
        min_score_delta=spec.min_feature_combination_score_delta,
        min_trade_count=spec.min_feature_combination_trade_count,
    )
    manifest = {
        "ablation_manifest_version": PERP_FILTER_ABLATION_MANIFEST_VERSION,
        "matrix_version": PERP_FILTER_ABLATION_MATRIX_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "spec": spec.to_payload(),
        "spec_sha256": _stable_hash(spec.to_payload()),
        "input_ranking_row_count": int(len(rankings)),
        "comparison_count": int(len(spec.comparisons)),
        "matrix_row_count": int(len(matrix)),
        "feature_combination_stability_row_count": int(len(stability)),
        "required_axes": list(DEFAULT_AXES),
        "axis_status_counts": _axis_status_counts(matrix),
        "filter_default_candidate_count": int(matrix["filter_default_candidate"].sum()) if not matrix.empty else 0,
        "filter_default_allowed_count": int(matrix["filter_default_allowed"].sum()) if not matrix.empty else 0,
        "default_guard": {
            "no_filter_default_without_winning_ablation": True,
            "default_allowed_column": "filter_default_allowed",
            "pending_evidence_blocks_default": True,
            "matched_filter_v2_requires_edge_improving": spec.decision_policy_version == MATCHED_FILTER_DECISION_POLICY_V2,
        },
        "matched_filter_policy": {
            "decision_policy_version": spec.decision_policy_version,
            "matched_group_columns": list(spec.group_columns),
            "required_group_columns": list(spec.required_group_columns),
            "missing_finite_filter_columns_are_not_testable": True,
        },
        "feature_combination_guard": {
            "wt3d_requires_non_wt_comparator": True,
            "stability_diagnostics_do_not_replace_region_of_stability_gate": True,
        },
        "live_fetch_used": False,
        "order_placement_used": False,
        "runtime_mode_changed": False,
    }
    manifest["matrix_sha256"] = _frame_hash(matrix)
    manifest["feature_combination_stability_sha256"] = _frame_hash(stability)
    return PerpFilterAblationMatrixResult(
        manifest=manifest,
        matrix=matrix,
        feature_combination_stability=stability,
    )


def write_perp_filter_ablation_artifacts(
    output_dir: Path,
    result: PerpFilterAblationMatrixResult,
) -> PerpFilterAblationArtifactResult:
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "perp_filter_ablation_manifest.json"
    matrix_path = output_dir / "perp_filter_ablation_matrix.parquet"
    stability_path = output_dir / "feature_combination_stability.parquet"
    result.matrix.to_parquet(matrix_path, index=False)
    result.feature_combination_stability.to_parquet(stability_path, index=False)
    manifest = dict(result.manifest)
    manifest["artifact_version"] = PERP_FILTER_ABLATION_ARTIFACT_VERSION
    manifest["required_outputs"] = {
        "perp_filter_ablation_manifest": str(manifest_path),
        "perp_filter_ablation_matrix": str(matrix_path),
        "feature_combination_stability": str(stability_path),
    }
    manifest["perp_filter_ablation_matrix_sha256"] = _file_sha256(matrix_path)
    manifest["feature_combination_stability_artifact_sha256"] = _file_sha256(stability_path)
    atomic_write_json(manifest_path, manifest)
    return PerpFilterAblationArtifactResult(
        output_dir=output_dir,
        manifest_path=manifest_path,
        matrix_path=matrix_path,
        feature_combination_stability_path=stability_path,
    )


def _comparison_matrix(rankings: pd.DataFrame, *, spec: PerpFilterAblationMatrixSpec) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    missing_group_columns = [column for column in spec.required_group_columns if column not in rankings.columns]
    groups = _ranking_groups(rankings, spec.group_columns)
    if not groups:
        groups = [({}, rankings)]
    for comparison in spec.comparisons:
        for group_values, group in groups:
            treatment_rows = _matching_rows(group, comparison.treatment_selector)
            comparator_rows = _matching_rows(group, comparison.comparator_selector) if comparison.comparator_selector else pd.DataFrame()
            treatment = _best_row(treatment_rows)
            comparator = _best_row(comparator_rows)
            rows.append(
                _comparison_row(
                    comparison,
                    group_values=group_values,
                    treatment=treatment,
                    comparator=comparator,
                    treatment_rows=treatment_rows,
                    decision_policy_version=spec.decision_policy_version,
                    missing_group_columns=missing_group_columns,
                )
            )
    return pd.DataFrame(rows, columns=_matrix_columns())


def _comparison_row(
    comparison: AblationComparisonSpec,
    *,
    group_values: Mapping[str, Any],
    treatment: Mapping[str, Any] | None,
    comparator: Mapping[str, Any] | None,
    treatment_rows: pd.DataFrame,
    decision_policy_version: str,
    missing_group_columns: list[str],
) -> dict[str, Any]:
    reasons: list[str] = []
    status = "pending_evidence"
    treatment_score = _score(treatment)
    comparator_score = _score(comparator)
    treatment_trade_count = _int_value(treatment, "trade_count")
    comparator_trade_count = _int_value(comparator, "trade_count")
    treatment_missingness = _float_value(treatment, "feature_missingness_rate")
    score_delta = treatment_score - comparator_score if treatment is not None and comparator is not None else None
    selected_treatment = pd.DataFrame([treatment]) if treatment is not None else treatment_rows
    finite_reasons = _required_finite_filter_reasons(selected_treatment, comparison.required_finite_columns)
    sample_retention_ratio = (
        float(treatment_trade_count / comparator_trade_count)
        if treatment is not None and comparator is not None and comparator_trade_count > 0
        else None
    )
    if treatment is None:
        reasons.append("treatment_evidence_missing")
    if comparison.requires_comparator and comparator is None:
        reasons.append("comparator_evidence_missing")
        if decision_policy_version == MATCHED_FILTER_DECISION_POLICY_V2 and treatment is not None:
            reasons.append("matched_no_filter_comparator_missing")
    if missing_group_columns:
        reasons.append("matched_group_columns_missing:" + ",".join(missing_group_columns))
    reasons.extend(finite_reasons)
    if treatment is not None and treatment_trade_count < comparison.min_trade_count:
        reasons.append("treatment_trade_count_below_floor")
    if treatment is not None and treatment_missingness > comparison.max_missingness_rate:
        reasons.append("treatment_missingness_above_floor")
    if decision_policy_version == MATCHED_FILTER_DECISION_POLICY_V2:
        status = _matched_filter_decision(
            comparison,
            treatment=treatment,
            comparator=comparator,
            reasons=reasons,
            score_delta=score_delta,
            sample_retention_ratio=sample_retention_ratio,
        )
    else:
        if treatment is not None and (not comparison.requires_comparator or comparator is not None):
            if not comparison.requires_comparator and comparator is None:
                status = "baseline_reference"
            elif treatment_score - comparator_score >= comparison.min_score_delta:
                status = "passed"
            else:
                status = "failed"
                reasons.append("treatment_did_not_beat_comparator")
        if reasons and status in {"passed", "baseline_reference"}:
            status = "failed" if "treatment_evidence_missing" not in reasons and "comparator_evidence_missing" not in reasons else "pending_evidence"
        elif reasons and status == "pending_evidence":
            status = "pending_evidence"
    filter_default_allowed = bool(
        comparison.filter_default_candidate
        and not reasons
        and decision_policy_version == MATCHED_FILTER_DECISION_POLICY_V2
        and status == "edge_improving"
    )
    return {
        "comparison_id": comparison.comparison_id,
        "axis": comparison.axis,
        "filter_family": comparison.filter_family,
        **{f"group_{key}": value for key, value in group_values.items()},
        "decision": status,
        "failure_reasons": ";".join(reasons),
        "decision_policy_version": decision_policy_version,
        "matched_group_columns": ",".join(str(column) for column in DEFAULT_MATCHED_GROUP_COLUMNS),
        "required_finite_columns": ",".join(comparison.required_finite_columns),
        "finite_filter_columns_present": not finite_reasons,
        "treatment_candidate_id": _text_value(treatment, "candidate_id"),
        "treatment_strategy_id": _text_value(treatment, "strategy_id"),
        "treatment_feature_set_id": _text_value(treatment, "feature_set_id"),
        "treatment_exit_policy_id": _text_value(treatment, "exit_policy_id"),
        "treatment_final_score": treatment_score,
        "treatment_trade_count": treatment_trade_count,
        "treatment_feature_missingness_rate": treatment_missingness,
        "comparator_candidate_id": _text_value(comparator, "candidate_id"),
        "comparator_strategy_id": _text_value(comparator, "strategy_id"),
        "comparator_feature_set_id": _text_value(comparator, "feature_set_id"),
        "comparator_exit_policy_id": _text_value(comparator, "exit_policy_id"),
        "comparator_final_score": comparator_score,
        "comparator_trade_count": comparator_trade_count,
        "score_delta": score_delta,
        "sample_retention_ratio": sample_retention_ratio,
        "split_consistency": _float_value(treatment, "split_consistency"),
        "cost_stress_survival": _float_value(treatment, "cost_stress_survival"),
        "side_specific": _side_specific(treatment),
        "min_score_delta": float(comparison.min_score_delta),
        "min_trade_count": int(comparison.min_trade_count),
        "max_missingness_rate": float(comparison.max_missingness_rate),
        "min_sample_retention_ratio": float(comparison.min_sample_retention_ratio),
        "min_split_consistency": float(comparison.min_split_consistency),
        "min_cost_stress_survival": float(comparison.min_cost_stress_survival),
        "filter_default_candidate": bool(comparison.filter_default_candidate),
        "filter_default_allowed": filter_default_allowed,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "notes": comparison.notes,
    }


def _feature_combination_stability(
    manifest: DiscoveryFeatureColumnSetManifest | None,
    *,
    evidence: pd.DataFrame | None,
    min_score_delta: float,
    min_trade_count: int,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if manifest is None:
        return pd.DataFrame(rows, columns=_feature_stability_columns())
    by_id = manifest.set_by_id()
    evidence = evidence.copy() if evidence is not None else pd.DataFrame()
    for item in manifest.enabled_sets:
        comparator = by_id.get(item.required_comparator_set or "")
        treatment = _best_row(_matching_rows(evidence, {"feature_column_set_id": item.feature_column_set_id}))
        comparator_row = (
            _best_row(_matching_rows(evidence, {"feature_column_set_id": comparator.feature_column_set_id}))
            if comparator is not None
            else None
        )
        reasons: list[str] = []
        decision = "pending_evidence"
        if item.required_comparator_set and comparator is None:
            reasons.append("required_comparator_missing")
        if treatment is None:
            reasons.append("feature_combination_evidence_missing")
        if treatment is not None and _int_value(treatment, "trade_count") < min_trade_count:
            reasons.append("feature_combination_trade_count_below_floor")
        if comparator is not None and comparator_row is None:
            reasons.append("comparator_feature_combination_evidence_missing")
        if treatment is not None and (comparator is None or comparator_row is not None):
            if comparator is None:
                decision = "baseline_reference"
            elif _score(treatment) - _score(comparator_row) >= min_score_delta:
                decision = "passed"
            else:
                decision = "failed"
                reasons.append("feature_combination_did_not_beat_comparator")
        if reasons and decision == "passed":
            decision = "failed"
        rows.append(
            {
                "feature_column_set_id": item.feature_column_set_id,
                "registered_feature_set_id": item.registered_feature_set_id,
                "role": item.role,
                "contains_wt3d": item.contains_wt3d,
                "required_comparator_set": item.required_comparator_set,
                "decision": decision if not reasons or decision != "pending_evidence" else "pending_evidence",
                "failure_reasons": ";".join(reasons),
                "treatment_score": _score(treatment),
                "comparator_score": _score(comparator_row),
                "score_delta": _score(treatment) - _score(comparator_row) if treatment is not None and comparator_row is not None else None,
                "trade_count": _int_value(treatment, "trade_count"),
                "split_consistency": _float_value(treatment, "split_consistency"),
                "cost_stress_survival": _float_value(treatment, "cost_stress_survival"),
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
            }
        )
    return pd.DataFrame(rows, columns=_feature_stability_columns())


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
    if frame.empty or not selector:
        return frame.iloc[0:0].copy() if selector else frame.copy()
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


def _matched_filter_decision(
    comparison: AblationComparisonSpec,
    *,
    treatment: Mapping[str, Any] | None,
    comparator: Mapping[str, Any] | None,
    reasons: list[str],
    score_delta: float | None,
    sample_retention_ratio: float | None,
) -> str:
    if reasons:
        return "not_testable"
    if treatment is None or (comparison.requires_comparator and comparator is None):
        return "not_testable"
    if _float_value(treatment, "split_consistency") < comparison.min_split_consistency:
        reasons.append("filter_split_consistency_below_floor")
        return "unstable"
    if _float_value(treatment, "cost_stress_survival") < comparison.min_cost_stress_survival:
        reasons.append("filter_cost_stress_survival_below_floor")
        return "unstable"
    if _side_specific(treatment):
        return "side_specific"
    delta = float(score_delta or 0.0)
    if delta > float(comparison.min_score_delta):
        return "edge_improving"
    if delta < 0.0:
        reasons.append("filter_harmed_edge_vs_matched_comparator")
        return "harmful"
    if sample_retention_ratio is not None and sample_retention_ratio < 1.0:
        reasons.append("filter_reduced_sample_without_edge_improvement")
        return "sample_reducing_only"
    reasons.append("filter_did_not_improve_edge")
    return "harmful"


def _required_finite_filter_reasons(frame: pd.DataFrame, columns: tuple[str, ...]) -> list[str]:
    reasons: list[str] = []
    if frame.empty:
        return reasons
    for column in columns:
        if column not in frame.columns:
            reasons.append(f"finite_filter_column_missing:{column}")
            continue
        values = pd.to_numeric(frame[column], errors="coerce").dropna()
        if values.empty:
            reasons.append(f"finite_filter_column_not_testable:{column}")
            continue
        finite = values.map(lambda value: pd.notna(value) and abs(float(value)) != float("inf"))
        if not bool(finite.any()):
            reasons.append(f"finite_filter_column_not_testable:{column}")
    for column in columns:
        backed_column = f"{column}_provider_backed"
        if backed_column in frame.columns and not bool(frame[backed_column].map(_truthy).any()):
            reasons.append(f"filter_column_not_provider_backed:{column}")
    return reasons


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or pd.isna(value):
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _side_specific(row: Mapping[str, Any] | None) -> bool:
    if row is None:
        return False
    value = row.get("side_specific")
    if isinstance(value, bool):
        return value
    if value is not None and not pd.isna(value):
        return str(value).strip().lower() in {"1", "true", "yes", "y"}
    side_pass_ratio = _float_value(row, "side_pass_ratio")
    return 0.0 < side_pass_ratio < 1.0


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


def _axis_status_counts(matrix: pd.DataFrame) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    if matrix.empty:
        return counts
    for axis, group in matrix.groupby("axis", dropna=False):
        counts[str(axis)] = {str(key): int(value) for key, value in group["decision"].value_counts().sort_index().items()}
    return counts


def _matrix_columns() -> list[str]:
    return [
        "comparison_id",
        "axis",
        "filter_family",
        "group_entry_family",
        "group_feature_set_id",
        "group_feature_column_set_id",
        "group_label_horizon",
        "group_regime_mode",
        "group_distance_metric",
        "group_k",
        "group_min_neighbor_count",
        "group_holding_window",
        "group_exit_policy_id",
        "group_exit_policy_params_json",
        "group_split_id",
        "group_cost_model_id",
        "decision",
        "failure_reasons",
        "decision_policy_version",
        "matched_group_columns",
        "required_finite_columns",
        "finite_filter_columns_present",
        "treatment_candidate_id",
        "treatment_strategy_id",
        "treatment_feature_set_id",
        "treatment_exit_policy_id",
        "treatment_final_score",
        "treatment_trade_count",
        "treatment_feature_missingness_rate",
        "comparator_candidate_id",
        "comparator_strategy_id",
        "comparator_feature_set_id",
        "comparator_exit_policy_id",
        "comparator_final_score",
        "comparator_trade_count",
        "score_delta",
        "sample_retention_ratio",
        "split_consistency",
        "cost_stress_survival",
        "side_specific",
        "min_score_delta",
        "min_trade_count",
        "max_missingness_rate",
        "min_sample_retention_ratio",
        "min_split_consistency",
        "min_cost_stress_survival",
        "filter_default_candidate",
        "filter_default_allowed",
        "research_only",
        "observe_only",
        "promotion_ready",
        "notes",
    ]


def _feature_stability_columns() -> list[str]:
    return [
        "feature_column_set_id",
        "registered_feature_set_id",
        "role",
        "contains_wt3d",
        "required_comparator_set",
        "decision",
        "failure_reasons",
        "treatment_score",
        "comparator_score",
        "score_delta",
        "trade_count",
        "split_consistency",
        "cost_stress_survival",
        "research_only",
        "observe_only",
        "promotion_ready",
    ]


def _stable_hash(payload: Any) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False).encode("utf-8")).hexdigest()


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
