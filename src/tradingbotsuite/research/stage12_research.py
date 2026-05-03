from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence

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
from tradingbotsuite.research.feature_ablation import write_feature_ablation_plan
from tradingbotsuite.research.live_readiness import research_boundary_metadata

STAGE12_RESEARCH_PLAN_VERSION = "stage12-research-plan-v1"
STAGE12_RESEARCH_MANIFEST_VERSION = "stage12-research-manifest-v1"


@dataclass(frozen=True, slots=True)
class Stage12ResearchTrack:
    substage: str
    hypothesis_id: str
    plan_track: str
    candidate: str
    comparison_group: str
    expected_role: str
    key_question: str
    report_outputs: tuple[str, ...]
    required_evidence: tuple[str, ...]
    prerequisites: tuple[str, ...] = ()
    optional_dependency: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "substage": self.substage,
            "hypothesis_id": self.hypothesis_id,
            "plan_track": self.plan_track,
            "candidate": self.candidate,
            "comparison_group": self.comparison_group,
            "expected_role": self.expected_role,
            "key_question": self.key_question,
            "report_outputs": list(self.report_outputs),
            "required_evidence": list(self.required_evidence),
            "prerequisites": list(self.prerequisites),
            "optional_dependency": self.optional_dependency,
        }


@dataclass(frozen=True, slots=True)
class Stage12ResearchPlanResult:
    output_dir: Path
    manifest_path: Path
    summary_path: Path
    rejected_hypotheses_path: Path
    limitations_path: Path
    experiment_spec_dir: Path
    feature_ablation_manifest_path: Path


BASE_EVIDENCE = (
    "oos_costed_expectancy",
    "stress_passed",
    "walk_forward_split_count",
    "max_single_split_pnl_share",
    "side_separated_outcomes",
)


def stage12_research_tracks() -> tuple[Stage12ResearchTrack, ...]:
    return (
        *stage12_regime_tracks(),
        *stage12_knn_tracks(),
        *stage12_meta_model_tracks(),
        *stage12_exit_model_tracks(),
        *stage12_portfolio_tracks(),
        *stage12_multi_asset_tracks(),
    )


def stage12_regime_tracks() -> tuple[Stage12ResearchTrack, ...]:
    outputs = ("regime_stability", "transition_frequency", "no_trade_rate", "per_regime_expectancy", "regime_drift_over_time")
    evidence = (*BASE_EVIDENCE, "rows_per_regime", *outputs)
    return (
        _track("12.2", "rule_based_regimes", "rule-based regimes", "rule_based_regime_v1", "regime_model", "transparent_baseline", outputs, evidence),
        _track("12.2", "gaussian_mixture_regimes", "Gaussian mixture", "gaussian_mixture_v1", "regime_model", "statistical_candidate", outputs, evidence),
        _track("12.2", "hmm_regime_model", "HMM", "hmm_v1", "regime_model", "state_model_candidate", outputs, evidence),
        _track("12.2", "deterministic_vol_trend_chop", "volatility/trend/chop deterministic states", "deterministic_vol_trend_chop_v1", "regime_model", "deterministic_baseline", outputs, evidence),
        _track(
            "12.2",
            "later_clustering_sufficient_data",
            "later clustering only after sufficient data",
            "deferred_clustering_v1",
            "regime_model",
            "deferred_candidate",
            outputs,
            evidence,
            prerequisites=("sufficient_regime_rows",),
        ),
    )


def stage12_knn_tracks() -> tuple[Stage12ResearchTrack, ...]:
    outputs = ("neighbor_quality", "pool_size_by_regime", "acceptance_lift_vs_baseline", "distance_stability", "fallback_rate")
    evidence = (*BASE_EVIDENCE, *outputs, "transparent_baseline_comparison")
    return (
        _track("12.3", "lorentzian_log_lorentzian_distance", "Lorentzian/log-Lorentzian distance", "lorentzian_log_lorentzian", "knn_distance", "current_candidate", outputs, evidence),
        _track("12.3", "euclidean_robust_z_distance", "Euclidean robust-z", "euclidean_robust_z", "knn_distance", "transparent_baseline", outputs, evidence),
        _track("12.3", "cosine_distance", "cosine", "cosine", "knn_distance", "alternative_distance", outputs, evidence),
        _track("12.3", "mahalanobis_distance", "Mahalanobis", "mahalanobis", "knn_distance", "covariance_candidate", outputs, evidence),
        _track("12.3", "feature_weighted_distance", "feature-weighted distance", "feature_weighted", "knn_distance", "weighted_candidate", outputs, evidence),
        _track("12.3", "compatible_regime_fallback", "compatible-regime fallback", "compatible_regime_fallback", "knn_pooling", "fallback_candidate", outputs, evidence),
        _track("12.3", "no_knn_baseline", "no KNN baseline", "no_knn", "knn_ablation", "transparent_baseline", outputs, evidence),
    )


def stage12_meta_model_tracks() -> tuple[Stage12ResearchTrack, ...]:
    outputs = ("calibration_curves", "brier_score", "probability_bucket_performance", "feature_importance_stability", "shap_importance_diagnostics")
    evidence = (*BASE_EVIDENCE, *outputs, "pure_knn_comparison")
    return (
        _track("12.4", "logistic_regression_meta_model", "logistic regression", "logistic_regression", "meta_model", "transparent_baseline", outputs, evidence),
        _track("12.4", "random_forest_meta_model", "random forest", "random_forest", "meta_model", "nonlinear_candidate", outputs, evidence),
        _track(
            "12.4",
            "xgboost_lightgbm_meta_model",
            "XGBoost/LightGBM if dependencies are accepted",
            "xgboost_lightgbm",
            "meta_model",
            "optional_dependency_candidate",
            outputs,
            evidence,
            prerequisites=("dependency_accepted",),
            optional_dependency="xgboost_or_lightgbm",
        ),
        _track("12.4", "calibrated_meta_models", "calibrated models", "calibrated_models", "meta_model", "calibration_candidate", outputs, evidence),
        _track("12.4", "no_meta_model", "no meta-model", "no_meta_model", "meta_model_ablation", "transparent_baseline", outputs, evidence),
    )


def stage12_exit_model_tracks() -> tuple[Stage12ResearchTrack, ...]:
    outputs = ("mfe_mae", "exit_reason_distribution", "holding_period_distribution", "cost_funding_contribution", "latency_slippage_sensitivity")
    evidence = (*BASE_EVIDENCE, *outputs)
    return (
        _track("12.5", "fixed_time_barrier_exit", "fixed time barrier", "fixed_time_barrier", "exit_model", "baseline_exit", outputs, evidence),
        _track("12.5", "volatility_scaled_triple_barrier_exit", "volatility-scaled triple barrier", "volatility_scaled_triple_barrier", "exit_model", "current_candidate", outputs, evidence),
        _track("12.5", "trailing_atr_stop_exit", "trailing ATR stop", "trailing_atr_stop", "exit_model", "risk_control_candidate", outputs, evidence),
        _track("12.5", "funding_cost_unwind_exit", "funding-cost unwind", "funding_cost_unwind", "exit_model", "perp_cost_candidate", outputs, evidence),
        _track("12.5", "regime_flip_exit", "regime flip exit", "regime_flip_exit", "exit_model", "regime_candidate", outputs, evidence),
        _track("12.5", "trend_decay_exit", "trend decay exit", "trend_decay_exit", "exit_model", "decay_candidate", outputs, evidence),
        _track("12.5", "adverse_selection_exit", "adverse-selection exit", "adverse_selection_exit", "exit_model", "microstructure_candidate", outputs, evidence),
    )


def stage12_portfolio_tracks() -> tuple[Stage12ResearchTrack, ...]:
    outputs = ("drawdown", "exposure_by_regime", "correlation_exposure", "turnover", "cash_allocation")
    evidence = (*BASE_EVIDENCE, *outputs, "single_strategy_evidence_passed", "risk_governor_live_owned")
    prerequisites = ("single_strategy_evidence_passed", "risk_governor_live_owned")
    return (
        _track("12.6", "volatility_targeting_allocation", "volatility targeting", "volatility_targeting", "portfolio_allocation", "allocation_candidate", outputs, evidence, prerequisites=prerequisites),
        _track("12.6", "max_risk_per_asset", "max risk per asset", "max_risk_per_asset", "portfolio_allocation", "risk_cap_candidate", outputs, evidence, prerequisites=prerequisites),
        _track("12.6", "max_correlated_exposure", "max correlated exposure", "max_correlated_exposure", "portfolio_allocation", "correlation_cap_candidate", outputs, evidence, prerequisites=prerequisites),
        _track("12.6", "drawdown_throttle", "drawdown throttle", "drawdown_throttle", "portfolio_allocation", "risk_throttle_candidate", outputs, evidence, prerequisites=prerequisites),
        _track("12.6", "regime_level_exposure_caps", "regime-level exposure caps", "regime_level_exposure_caps", "portfolio_allocation", "regime_risk_candidate", outputs, evidence, prerequisites=prerequisites),
        _track("12.6", "strategy_ensemble_allocation", "strategy ensemble allocation", "strategy_ensemble_allocation", "portfolio_allocation", "ensemble_candidate", outputs, evidence, prerequisites=prerequisites),
        _track("12.6", "no_trade_cash_allocation", "no-trade cash allocation", "no_trade_cash_allocation", "portfolio_allocation", "baseline_cash_policy", outputs, evidence, prerequisites=prerequisites),
    )


def stage12_multi_asset_tracks() -> tuple[Stage12ResearchTrack, ...]:
    outputs = ("asset_data_inventory", "provider_manifest_status", "feature_quality", "cost_funding_assumptions", "independent_backtest_status", "asset_rejection_rules")
    evidence = (*BASE_EVIDENCE, *outputs, "eth_data_inventory", "eth_provider_manifests", "btc_only_artifact_rejection")
    prerequisites = ("btc_phase1_single_strategy_evidence_passed",)
    return (
        _track("12.7", "eth_data_inventory", "ETH data inventory", "eth_data_inventory", "multi_asset", "phase2_prerequisite", outputs, evidence, prerequisites=prerequisites),
        _track("12.7", "eth_provider_manifests", "ETH provider manifests", "eth_provider_manifests", "multi_asset", "phase2_prerequisite", outputs, evidence, prerequisites=prerequisites),
        _track("12.7", "eth_feature_quality_report", "ETH feature quality report", "eth_feature_quality_report", "multi_asset", "phase2_prerequisite", outputs, evidence, prerequisites=prerequisites),
        _track("12.7", "eth_cost_funding_assumptions", "ETH-specific cost/funding assumptions", "eth_cost_funding_assumptions", "multi_asset", "phase2_prerequisite", outputs, evidence, prerequisites=prerequisites),
        _track("12.7", "eth_independent_backtests", "ETH backtests independent from BTC", "eth_independent_backtests", "multi_asset", "phase2_prerequisite", outputs, evidence, prerequisites=prerequisites),
        _track("12.7", "btc_to_eth_spillover_features", "BTC-to-ETH spillover features tested as explicit feature pack", "btc_to_eth_spillover_features", "multi_asset", "phase2_diagnostic", outputs, evidence, prerequisites=prerequisites),
        _track("12.7", "btc_only_artifacts_rejected_for_eth", "BTC-only artifacts rejected for ETH", "btc_only_artifact_rejection", "multi_asset", "safety_boundary", outputs, evidence),
    )


def write_stage12_research_plan(
    *,
    output_dir: Path,
    dataset_manifest_hash: str = "dataset_manifest_unavailable",
    evidence_by_hypothesis: Mapping[str, Mapping[str, Any]] | None = None,
) -> Stage12ResearchPlanResult:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    feature_result = write_feature_ablation_plan(
        output_dir=output_dir / "12_1_feature_ablation",
        dataset_manifest_hash=dataset_manifest_hash,
    )
    experiment_spec_dir = output_dir / "experiment_specs"
    experiment_spec_dir.mkdir(parents=True, exist_ok=True)
    evidence_by_hypothesis = evidence_by_hypothesis or {}
    rows = [
        _research_row(
            track,
            dataset_manifest_hash=dataset_manifest_hash,
            evidence=evidence_by_hypothesis.get(track.hypothesis_id),
        )
        for track in stage12_research_tracks()
    ]
    for row in rows:
        spec = _experiment_spec_for_row(row, dataset_manifest_hash=dataset_manifest_hash)
        spec_path = experiment_spec_dir / f"{row['substage'].replace('.', '_')}_{row['hypothesis_id']}.json"
        spec_path.write_text(_canonical_json(spec.to_payload(), indent=2) + "\n", encoding="utf-8")
        row["experiment_spec_path"] = str(spec_path)

    feature_manifest = _read_json(feature_result.manifest_path)
    feature_rows = [
        {
            "substage": "12.1",
            "hypothesis_id": track.get("hypothesis_id"),
            "plan_track": track.get("plan_track"),
            "candidate": track.get("feature_set_id"),
            "comparison_group": track.get("comparison_group"),
            "decision": track.get("decision"),
            "failure_reasons": track.get("failure_reasons") or [],
            "experiment_spec_path": track.get("experiment_spec_path"),
        }
        for track in feature_manifest.get("tracks", [])
    ]
    all_rows = [*feature_rows, *rows]
    summary_path = output_dir / "stage12_research_summary.csv"
    _write_summary_csv(summary_path, all_rows)
    rejected_path = output_dir / "stage12_rejected_hypotheses.md"
    rejected_path.write_text(_render_rejected_hypotheses(all_rows), encoding="utf-8")
    limitations_path = output_dir / "stage12_completion_limitations.md"
    limitations_path.write_text(_render_limitations(all_rows), encoding="utf-8")

    manifest = {
        "stage12_research_manifest_version": STAGE12_RESEARCH_MANIFEST_VERSION,
        "plan_version": STAGE12_RESEARCH_PLAN_VERSION,
        "generated_at_ms": int(time.time() * 1000),
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "dataset_manifest_hash": dataset_manifest_hash,
        "substage_status": _substage_status(all_rows),
        "hypothesis_count": len(all_rows),
        "accepted_hypotheses": [row["hypothesis_id"] for row in all_rows if row["decision"] == "accepted"],
        "rejected_hypotheses": [row["hypothesis_id"] for row in all_rows if row["decision"] == "rejected"],
        "blocked_hypotheses": [row["hypothesis_id"] for row in all_rows if row["decision"] == "blocked"],
        "pending_hypotheses": [row["hypothesis_id"] for row in all_rows if row["decision"] == "pending_evidence"],
        "tracks": all_rows,
        "outputs": {
            "summary_csv": str(summary_path),
            "rejected_hypotheses": str(rejected_path),
            "limitations": str(limitations_path),
            "experiment_spec_dir": str(experiment_spec_dir),
            "feature_ablation_manifest": str(feature_result.manifest_path),
        },
        "stage12_exit_gate": {
            "research_tracks_produce_reproducible_experiment_manifests": True,
            "rejected_hypotheses_documented": True,
            "accepted_hypotheses_pass_oos_and_stress_gates": True,
            "in_sample_only_promotion_allowed": False,
            "accepted_hypothesis_count": len([row for row in all_rows if row["decision"] == "accepted"]),
        },
        "empirical_completion": {
            "complete": False,
            "reason": "No new OOS/stress evidence was supplied or generated for the deeper Stage 12 hypotheses; generated artifacts are reproducible plans, not empirical acceptance results.",
        },
    }
    manifest_path = output_dir / "stage12_research_manifest.json"
    manifest_path.write_text(_canonical_json(manifest, indent=2) + "\n", encoding="utf-8")
    return Stage12ResearchPlanResult(
        output_dir=output_dir,
        manifest_path=manifest_path,
        summary_path=summary_path,
        rejected_hypotheses_path=rejected_path,
        limitations_path=limitations_path,
        experiment_spec_dir=experiment_spec_dir,
        feature_ablation_manifest_path=feature_result.manifest_path,
    )


def _track(
    substage: str,
    hypothesis_id: str,
    plan_track: str,
    candidate: str,
    comparison_group: str,
    expected_role: str,
    report_outputs: tuple[str, ...],
    required_evidence: tuple[str, ...],
    *,
    prerequisites: tuple[str, ...] = (),
    optional_dependency: str | None = None,
) -> Stage12ResearchTrack:
    return Stage12ResearchTrack(
        substage=substage,
        hypothesis_id=hypothesis_id,
        plan_track=plan_track,
        candidate=candidate,
        comparison_group=comparison_group,
        expected_role=expected_role,
        key_question=f"Does {plan_track} add robust OOS value without violating Stage 12 safety and evidence gates?",
        report_outputs=report_outputs,
        required_evidence=required_evidence,
        prerequisites=prerequisites,
        optional_dependency=optional_dependency,
    )


def _research_row(track: Stage12ResearchTrack, *, dataset_manifest_hash: str, evidence: Mapping[str, Any] | None) -> dict[str, Any]:
    decision, failure_reasons = _decide_track(track, evidence)
    validation_hash = _stable_hash({"required_evidence": track.required_evidence, "prerequisites": track.prerequisites})
    strategy_config_hash = _stable_hash({"hypothesis_id": track.hypothesis_id, "candidate": track.candidate, "substage": track.substage})
    return {
        **track.to_payload(),
        "decision": decision,
        "failure_reasons": failure_reasons,
        "evidence": dict(evidence or {}),
        "cache_key": deterministic_experiment_cache_key(
            dataset_manifest_hash=dataset_manifest_hash,
            feature_manifest_hash=f"stage12:{track.substage}:{track.comparison_group}",
            strategy_config_hash=strategy_config_hash,
            backtest_engine_version="stage12-research-plan-spec",
            validation_spec_hash=validation_hash,
        ),
    }


def _decide_track(track: Stage12ResearchTrack, evidence: Mapping[str, Any] | None) -> tuple[str, list[str]]:
    if not evidence:
        if track.prerequisites:
            return "blocked", [f"missing_prerequisite:{prerequisite}" for prerequisite in track.prerequisites]
        return "pending_evidence", ["evidence_not_supplied"]
    reasons = [f"missing_prerequisite:{item}" for item in track.prerequisites if evidence.get(item) is not True]
    for field in track.required_evidence:
        if field not in evidence:
            reasons.append(f"missing_required_evidence:{field}")
    if _float(evidence.get("oos_costed_expectancy")) <= 0.0:
        reasons.append("non_positive_oos_costed_expectancy")
    if evidence.get("stress_passed") is not True:
        reasons.append("stress_gates_not_passed")
    if _int(evidence.get("walk_forward_split_count")) < 6:
        reasons.append("insufficient_walk_forward_splits")
    if _float(evidence.get("max_single_split_pnl_share"), default=1.0) >= 0.50:
        reasons.append("single_split_pnl_dominance")
    side_outcomes = evidence.get("side_separated_outcomes")
    if not isinstance(side_outcomes, Mapping) or "long" not in side_outcomes or "short" not in side_outcomes:
        reasons.append("missing_long_short_outcomes")
    if evidence.get("in_sample_only") is True:
        reasons.append("in_sample_only_result_not_accepted")
    if track.optional_dependency and evidence.get("dependency_accepted") is not True:
        reasons.append(f"optional_dependency_not_accepted:{track.optional_dependency}")
    if reasons:
        return "blocked" if all(reason.startswith("missing_prerequisite:") for reason in reasons) else "rejected", sorted(set(reasons))
    return "accepted", []


def _experiment_spec_for_row(row: Mapping[str, Any], *, dataset_manifest_hash: str) -> ExperimentSpec:
    return ExperimentSpec(
        experiment_name=str(row["hypothesis_id"]),
        dataset=DatasetSpec(dataset_manifest_hash=dataset_manifest_hash),
        feature=FeatureSpec(
            feature_set_id=f"stage12_{row['comparison_group']}",
            feature_manifest_hash=str(row["cache_key"]),
        ),
        strategies=(
            StrategySpec("baseline_no_trade", config={"purpose": "stage12_floor"}),
            StrategySpec(
                str(row["candidate"]),
                strategy_type=f"stage12_{row['comparison_group']}",
                config={
                    "substage": row["substage"],
                    "hypothesis_id": row["hypothesis_id"],
                    "candidate": row["candidate"],
                    "report_outputs": row["report_outputs"],
                    "required_evidence": row["required_evidence"],
                },
            ),
        ),
        backtest=BacktestSpec(),
        validation=ValidationSpec(trade_count_floor=50, max_single_split_pnl_share=0.50, feature_missingness_ceiling=0.05),
        search=SearchSpec(
            method="grid",
            parameter_space={"candidate": (str(row["candidate"]),), "substage": (str(row["substage"]),)},
            max_candidates=1,
        ),
        report=ReportSpec(required_outputs=("experiment_manifest.json", "conclusion.md", *tuple(row["report_outputs"]))),
    )


def _write_summary_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    fields = ["substage", "hypothesis_id", "plan_track", "candidate", "comparison_group", "decision", "failure_reasons", "experiment_spec_path"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            payload = {field: row.get(field) for field in fields}
            payload["failure_reasons"] = "|".join(str(reason) for reason in row.get("failure_reasons", ()))
            writer.writerow(payload)


def _render_rejected_hypotheses(rows: Sequence[Mapping[str, Any]]) -> str:
    lines = [
        "# Stage 12 Hypotheses",
        "",
        "Research-only. Pending or blocked hypotheses are not promotion evidence. Accepted hypotheses require OOS and stress evidence.",
        "",
    ]
    for row in rows:
        reasons = row.get("failure_reasons") or []
        lines.extend(
            [
                f"## {row['substage']} - {row['hypothesis_id']}",
                "",
                f"- Plan track: {row['plan_track']}",
                f"- Candidate: `{row['candidate']}`",
                f"- Decision: `{row['decision']}`",
                f"- Reasons: `{', '.join(str(reason) for reason in reasons) if reasons else 'none'}`",
                f"- Experiment spec: `{row.get('experiment_spec_path')}`",
                "",
            ]
        )
    return "\n".join(lines)


def _render_limitations(rows: Sequence[Mapping[str, Any]]) -> str:
    accepted = [row for row in rows if row["decision"] == "accepted"]
    lines = [
        "# Stage 12 Completion Limitations",
        "",
        "Stage 12 planning and manifest generation is complete, but empirical Stage 12 research acceptance is not complete.",
        "",
        "Reasons:",
        "",
        "- No new OOS/stress evidence was supplied for the deeper 12.2-12.7 hypotheses.",
        "- Portfolio allocation tracks are blocked until single-strategy evidence passes.",
        "- ETH and multi-asset expansion remains Phase 2 and requires ETH data inventory, provider manifests, feature-quality reports, ETH cost assumptions, and independent ETH backtests.",
        "- Optional XGBoost/LightGBM work remains blocked unless those dependencies are explicitly accepted for the environment.",
        "- No hypothesis is promotion-ready from this artifact.",
        "",
        f"Accepted hypotheses in this generated manifest: `{len(accepted)}`.",
        "",
    ]
    return "\n".join(lines)


def _substage_status(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
    statuses: dict[str, dict[str, int]] = {}
    for row in rows:
        substage = str(row["substage"])
        decision = str(row["decision"])
        statuses.setdefault(substage, {"accepted": 0, "rejected": 0, "blocked": 0, "pending_evidence": 0})
        statuses[substage][decision] = statuses[substage].get(decision, 0) + 1
    return statuses


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


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
