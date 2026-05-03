from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence

from tradingbotsuite.features import manifest_from_preset, validate_feature_manifest
from tradingbotsuite.research.experiment_runner import (
    BacktestSpec,
    DatasetSpec,
    ExperimentSpec,
    FeatureSpec,
    ReportSpec,
    SearchSpec,
    StrategySpec,
    ValidationSpec,
    deterministic_experiment_cache_key,
)
from tradingbotsuite.research.live_readiness import research_boundary_metadata

FEATURE_ABLATION_PLAN_VERSION = "stage12-feature-ablation-plan-v1"
FEATURE_ABLATION_MANIFEST_VERSION = "stage12-feature-ablation-manifest-v1"


@dataclass(frozen=True, slots=True)
class FeatureAblationTrack:
    hypothesis_id: str
    plan_track: str
    feature_set_id: str
    comparison_group: str
    expected_role: str
    key_question: str
    required_evidence: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "plan_track": self.plan_track,
            "feature_set_id": self.feature_set_id,
            "comparison_group": self.comparison_group,
            "expected_role": self.expected_role,
            "key_question": self.key_question,
            "required_evidence": list(self.required_evidence),
        }


@dataclass(frozen=True, slots=True)
class FeatureAblationPlanResult:
    output_dir: Path
    manifest_path: Path
    summary_path: Path
    rejected_hypotheses_path: Path
    experiment_spec_dir: Path


DEFAULT_REQUIRED_EVIDENCE = (
    "oos_costed_expectancy",
    "stress_passed",
    "walk_forward_split_count",
    "max_single_split_pnl_share",
    "feature_missingness_rate",
    "side_separated_outcomes",
)


def stage12_feature_ablation_tracks() -> tuple[FeatureAblationTrack, ...]:
    return (
        FeatureAblationTrack(
            hypothesis_id="full_wt3d_feature_pack",
            plan_track="full WT3D feature pack",
            feature_set_id="features_price_trend_vol_wt3d",
            comparison_group="wt3d_isolated",
            expected_role="candidate_signal_context",
            key_question="Does WT3D add stable out-of-sample value after costs over price/trend/vol?",
            required_evidence=(*DEFAULT_REQUIRED_EVIDENCE, "wt3d_ablation_survives"),
        ),
        FeatureAblationTrack(
            hypothesis_id="no_wt3d",
            plan_track="no WT3D",
            feature_set_id="features_full_context_no_wt",
            comparison_group="full_context_wt3d",
            expected_role="ablation_baseline",
            key_question="Does removing WT3D preserve or improve full-context OOS performance?",
            required_evidence=DEFAULT_REQUIRED_EVIDENCE,
        ),
        FeatureAblationTrack(
            hypothesis_id="price_trend_vol_only",
            plan_track="price/trend/vol only",
            feature_set_id="features_price_trend_vol",
            comparison_group="minimal_price_context",
            expected_role="transparent_baseline",
            key_question="Does a transparent price/trend/vol baseline explain most observed edge?",
            required_evidence=DEFAULT_REQUIRED_EVIDENCE,
        ),
        FeatureAblationTrack(
            hypothesis_id="perp_context_only",
            plan_track="perp context only",
            feature_set_id="features_perp_context_only",
            comparison_group="context_only",
            expected_role="diagnostic_context",
            key_question="Do funding, basis, and open-interest context carry standalone value?",
            required_evidence=DEFAULT_REQUIRED_EVIDENCE,
        ),
        FeatureAblationTrack(
            hypothesis_id="microstructure_context_filter_only",
            plan_track="microstructure context only as filter",
            feature_set_id="features_microstructure_filter_only",
            comparison_group="context_only",
            expected_role="entry_filter_only",
            key_question="Does microstructure improve trade selection without becoming a direct sizing or execution input?",
            required_evidence=DEFAULT_REQUIRED_EVIDENCE,
        ),
        FeatureAblationTrack(
            hypothesis_id="full_context_no_wt",
            plan_track="full context no WT",
            feature_set_id="features_full_context_no_wt",
            comparison_group="full_context_wt3d",
            expected_role="full_context_baseline",
            key_question="Does full context without WT3D beat minimal baselines after costs?",
            required_evidence=DEFAULT_REQUIRED_EVIDENCE,
        ),
        FeatureAblationTrack(
            hypothesis_id="full_context_with_wt",
            plan_track="full context with WT",
            feature_set_id="features_full_context_wt3d",
            comparison_group="full_context_wt3d",
            expected_role="full_context_candidate",
            key_question="Does adding WT3D to full context add stable OOS value after costs?",
            required_evidence=(*DEFAULT_REQUIRED_EVIDENCE, "wt3d_ablation_survives"),
        ),
        FeatureAblationTrack(
            hypothesis_id="cross_asset_context",
            plan_track="cross-asset context",
            feature_set_id="features_cross_asset_context",
            comparison_group="context_only",
            expected_role="phase2_diagnostic",
            key_question="Do BTC/ETH spillover features add value without leaking ETH-specific assumptions into BTC Phase 1?",
            required_evidence=DEFAULT_REQUIRED_EVIDENCE,
        ),
    )


def write_feature_ablation_plan(
    *,
    output_dir: Path,
    dataset_manifest_hash: str = "dataset_manifest_unavailable",
    evidence_by_hypothesis: Mapping[str, Mapping[str, Any]] | None = None,
    experiment_name: str = "stage12-feature-ablation",
) -> FeatureAblationPlanResult:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    experiment_spec_dir = output_dir / "experiment_specs"
    experiment_spec_dir.mkdir(parents=True, exist_ok=True)
    evidence_by_hypothesis = evidence_by_hypothesis or {}

    tracks = stage12_feature_ablation_tracks()
    rows = [
        _ablation_row(
            track,
            dataset_manifest_hash=dataset_manifest_hash,
            evidence=evidence_by_hypothesis.get(track.hypothesis_id),
            experiment_name=experiment_name,
        )
        for track in tracks
    ]
    for row in rows:
        spec = _experiment_spec_for_row(row, dataset_manifest_hash=dataset_manifest_hash)
        spec_path = experiment_spec_dir / f"{row['hypothesis_id']}.json"
        spec_path.write_text(_canonical_json(spec.to_payload(), indent=2) + "\n", encoding="utf-8")
        row["experiment_spec_path"] = str(spec_path)

    summary_path = output_dir / "feature_ablation_summary.csv"
    _write_summary_csv(summary_path, rows)
    rejected_path = output_dir / "rejected_hypotheses.md"
    rejected_path.write_text(_render_rejected_hypotheses(rows), encoding="utf-8")

    manifest = {
        "feature_ablation_manifest_version": FEATURE_ABLATION_MANIFEST_VERSION,
        "plan_version": FEATURE_ABLATION_PLAN_VERSION,
        "generated_at_ms": int(time.time() * 1000),
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "experiment_name": experiment_name,
        "dataset_manifest_hash": dataset_manifest_hash,
        "required_plan_tracks": [track.plan_track for track in tracks],
        "hypothesis_count": len(rows),
        "accepted_hypotheses": [row["hypothesis_id"] for row in rows if row["decision"] == "accepted"],
        "rejected_hypotheses": [row["hypothesis_id"] for row in rows if row["decision"] == "rejected"],
        "pending_hypotheses": [row["hypothesis_id"] for row in rows if row["decision"] == "pending_evidence"],
        "tracks": rows,
        "outputs": {
            "summary_csv": str(summary_path),
            "rejected_hypotheses": str(rejected_path),
            "experiment_spec_dir": str(experiment_spec_dir),
        },
        "promotion_guard": {
            "accepted_requires_oos_and_stress": True,
            "in_sample_only_acceptance_allowed": False,
            "live_signal_input": False,
            "position_sizing_input": False,
            "live_execution_input": False,
        },
    }
    manifest_path = output_dir / "feature_ablation_manifest.json"
    manifest_path.write_text(_canonical_json(manifest, indent=2) + "\n", encoding="utf-8")
    return FeatureAblationPlanResult(
        output_dir=output_dir,
        manifest_path=manifest_path,
        summary_path=summary_path,
        rejected_hypotheses_path=rejected_path,
        experiment_spec_dir=experiment_spec_dir,
    )


def _ablation_row(
    track: FeatureAblationTrack,
    *,
    dataset_manifest_hash: str,
    evidence: Mapping[str, Any] | None,
    experiment_name: str,
) -> dict[str, Any]:
    feature_manifest = manifest_from_preset(track.feature_set_id)
    validation = validate_feature_manifest(feature_manifest)
    decision, failure_reasons = _decide_hypothesis(track, evidence)
    validation_hash = _stable_hash({"required_evidence": track.required_evidence, "comparison_group": track.comparison_group})
    strategy_config_hash = _stable_hash({"hypothesis_id": track.hypothesis_id, "feature_set_id": track.feature_set_id})
    return {
        **track.to_payload(),
        "experiment_name": experiment_name,
        "feature_manifest_hash": feature_manifest.manifest_sha256,
        "feature_packs": list(feature_manifest.feature_packs),
        "feature_columns": list(feature_manifest.feature_columns),
        "uses_wt3d": "wt3d_v1" in feature_manifest.feature_packs,
        "uses_cross_asset": "cross_asset_v1" in feature_manifest.feature_packs,
        "microstructure_filter_only": track.expected_role == "entry_filter_only",
        "manifest_valid": validation.valid,
        "manifest_errors": list(validation.errors),
        "decision": decision,
        "failure_reasons": failure_reasons,
        "evidence": dict(evidence or {}),
        "cache_key": deterministic_experiment_cache_key(
            dataset_manifest_hash=dataset_manifest_hash,
            feature_manifest_hash=feature_manifest.manifest_sha256,
            strategy_config_hash=strategy_config_hash,
            backtest_engine_version="stage12-feature-ablation-spec",
            validation_spec_hash=validation_hash,
        ),
    }


def _decide_hypothesis(track: FeatureAblationTrack, evidence: Mapping[str, Any] | None) -> tuple[str, list[str]]:
    if not evidence:
        return "pending_evidence", ["evidence_not_supplied"]
    reasons: list[str] = []
    if _float(evidence.get("oos_costed_expectancy")) <= 0.0:
        reasons.append("non_positive_oos_costed_expectancy")
    if evidence.get("stress_passed") is not True:
        reasons.append("stress_gates_not_passed")
    if _int(evidence.get("walk_forward_split_count")) < 6:
        reasons.append("insufficient_walk_forward_splits")
    if _float(evidence.get("max_single_split_pnl_share"), default=1.0) >= 0.50:
        reasons.append("single_split_pnl_dominance")
    if _float(evidence.get("feature_missingness_rate"), default=1.0) > _float(evidence.get("feature_missingness_ceiling"), default=0.05):
        reasons.append("feature_missingness_above_ceiling")
    side_outcomes = evidence.get("side_separated_outcomes")
    if not isinstance(side_outcomes, Mapping) or "long" not in side_outcomes or "short" not in side_outcomes:
        reasons.append("missing_long_short_outcomes")
    if any(item == "wt3d_ablation_survives" for item in track.required_evidence) and evidence.get("wt3d_ablation_survives") is not True:
        reasons.append("wt3d_ablation_did_not_survive")
    if evidence.get("in_sample_only") is True:
        reasons.append("in_sample_only_result_not_accepted")
    return ("rejected", reasons) if reasons else ("accepted", [])


def _experiment_spec_for_row(row: Mapping[str, Any], *, dataset_manifest_hash: str) -> ExperimentSpec:
    return ExperimentSpec(
        experiment_name=str(row["hypothesis_id"]),
        dataset=DatasetSpec(dataset_manifest_hash=dataset_manifest_hash),
        feature=FeatureSpec(
            feature_set_id=str(row["feature_set_id"]),
            feature_manifest_hash=str(row["feature_manifest_hash"]),
        ),
        strategies=(
            StrategySpec("baseline_no_trade", config={"purpose": "floor"}),
            StrategySpec(
                "hmm_knn_diagnostic_v1",
                strategy_type="hmm_knn_research",
                config={
                    "hypothesis_id": row["hypothesis_id"],
                    "feature_set_id": row["feature_set_id"],
                    "microstructure_filter_only": bool(row["microstructure_filter_only"]),
                },
            ),
        ),
        backtest=BacktestSpec(),
        validation=ValidationSpec(trade_count_floor=50, max_single_split_pnl_share=0.50, feature_missingness_ceiling=0.05),
        search=SearchSpec(
            method="grid",
            parameter_space={
                "feature_set_id": (str(row["feature_set_id"]),),
                "hypothesis_id": (str(row["hypothesis_id"]),),
            },
            max_candidates=1,
        ),
        report=ReportSpec(),
    )


def _write_summary_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    fields = [
        "hypothesis_id",
        "plan_track",
        "feature_set_id",
        "comparison_group",
        "expected_role",
        "feature_manifest_hash",
        "uses_wt3d",
        "uses_cross_asset",
        "microstructure_filter_only",
        "decision",
        "failure_reasons",
        "cache_key",
        "experiment_spec_path",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            payload = {field: row.get(field) for field in fields}
            payload["failure_reasons"] = "|".join(str(reason) for reason in row.get("failure_reasons", ()))
            writer.writerow(payload)


def _render_rejected_hypotheses(rows: Sequence[Mapping[str, Any]]) -> str:
    lines = [
        "# Stage 12.1 Feature Ablation Hypotheses",
        "",
        "Research-only. Pending hypotheses are not promotion evidence. Accepted hypotheses require OOS and stress evidence.",
        "",
    ]
    for row in rows:
        reasons = row.get("failure_reasons") or []
        lines.extend(
            [
                f"## {row['hypothesis_id']}",
                "",
                f"- Plan track: {row['plan_track']}",
                f"- Feature set: `{row['feature_set_id']}`",
                f"- Decision: `{row['decision']}`",
                f"- Reasons: `{', '.join(str(reason) for reason in reasons) if reasons else 'none'}`",
                "",
            ]
        )
    return "\n".join(lines)


def _float(value: object, *, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _int(value: object, *, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _stable_hash(payload: Any) -> str:
    return sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _canonical_json(payload: Any, *, indent: int | None = None) -> str:
    return json.dumps(payload, indent=indent, sort_keys=True, default=str)
