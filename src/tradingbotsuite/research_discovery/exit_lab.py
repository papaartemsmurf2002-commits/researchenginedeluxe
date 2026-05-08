from __future__ import annotations

import json
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
    "strategy_id",
    "feature_set_id",
    "holding_window",
    "parameters_json",
)
SUPPORTED_EXIT_FAMILIES = (
    "fixed_holding",
    "barrier",
    "funding_oi",
    "hmm_knn",
    "trailing_risk",
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


@dataclass(frozen=True, slots=True)
class DiscoveryExitLabArtifactResult:
    output_dir: Path
    manifest_path: Path
    matrix_path: Path
    family_summary_path: Path


def build_discovery_exit_lab(
    rankings: pd.DataFrame,
    *,
    spec: DiscoveryExitLabSpec,
) -> DiscoveryExitLabResult:
    matrix = _exit_lab_matrix(rankings, spec=spec)
    summary = _family_summary(matrix)
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
        "supported_exit_families": list(SUPPORTED_EXIT_FAMILIES),
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
    return DiscoveryExitLabResult(manifest=manifest, matrix=matrix, family_summary=summary)


def write_discovery_exit_lab_artifacts(
    output_dir: Path,
    result: DiscoveryExitLabResult,
) -> DiscoveryExitLabArtifactResult:
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "discovery_exit_lab_manifest.json"
    matrix_path = output_dir / "discovery_exit_lab_matrix.parquet"
    family_summary_path = output_dir / "discovery_exit_family_summary.parquet"
    result.matrix.to_parquet(matrix_path, index=False)
    result.family_summary.to_parquet(family_summary_path, index=False)
    manifest = dict(result.manifest)
    manifest["artifact_version"] = DISCOVERY_EXIT_LAB_ARTIFACT_VERSION
    manifest["required_outputs"] = {
        "discovery_exit_lab_manifest": str(manifest_path),
        "discovery_exit_lab_matrix": str(matrix_path),
        "discovery_exit_family_summary": str(family_summary_path),
    }
    manifest["discovery_exit_lab_matrix_sha256"] = _file_sha256(matrix_path)
    manifest["discovery_exit_family_summary_sha256"] = _file_sha256(family_summary_path)
    atomic_write_json(manifest_path, manifest)
    return DiscoveryExitLabArtifactResult(
        output_dir=output_dir,
        manifest_path=manifest_path,
        matrix_path=matrix_path,
        family_summary_path=family_summary_path,
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
    return pd.DataFrame(rows, columns=_matrix_columns())


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
    if baseline is None:
        reasons.append("baseline_exit_evidence_missing")
    if treatment is None:
        reasons.append("treatment_exit_evidence_missing")
    if baseline is not None and baseline_trade_count < comparison.min_entry_trade_count:
        reasons.append("entry_trade_count_below_exit_lab_floor")
    if treatment is not None and treatment_trade_count < comparison.min_treatment_trade_count:
        reasons.append("treatment_trade_count_below_exit_lab_floor")

    if "entry_trade_count_below_exit_lab_floor" in reasons:
        decision = "skipped_low_trade_density"
    elif baseline is None or treatment is None:
        decision = "pending_evidence"
    elif treatment_score - baseline_score >= comparison.min_score_delta:
        decision = "passed"
    else:
        decision = "failed"
        reasons.append("treatment_exit_did_not_beat_baseline")

    return {
        "comparison_id": comparison.comparison_id,
        "exit_family": comparison.exit_family,
        **{f"entry_{key}": value for key, value in group_values.items()},
        "decision": decision,
        "failure_reasons": ";".join(reasons),
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
        "score_delta": treatment_score - baseline_score if baseline is not None and treatment is not None else None,
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
                "comparison_count": int(len(group)),
                "passed_count": int(decisions.get("passed", 0)),
                "failed_count": int(decisions.get("failed", 0)),
                "pending_count": int(decisions.get("pending_evidence", 0)),
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


def _float_value(row: Mapping[str, Any] | None, key: str) -> float:
    if row is None:
        return 0.0
    try:
        value = row.get(key, 0.0)
        if pd.isna(value):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


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


def _matrix_columns() -> list[str]:
    return [
        "comparison_id",
        "exit_family",
        "entry_strategy_id",
        "entry_feature_set_id",
        "entry_holding_window",
        "entry_parameters_json",
        "decision",
        "failure_reasons",
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


def _summary_columns() -> list[str]:
    return [
        "exit_family",
        "comparison_count",
        "passed_count",
        "failed_count",
        "pending_count",
        "skipped_low_trade_density_count",
        "winner_candidate_ids",
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
