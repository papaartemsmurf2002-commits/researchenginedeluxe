from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from tradingbotsuite.research.live_readiness import research_boundary_metadata


RESEARCH_CANDIDATE_PACK_VERSION = "research-candidate-pack-v1"
LIVE_ADJACENT_VERSION_FIELDS = frozenset(
    {
        "promotion_candidate_manifest_version",
        "paper_run_manifest_version",
        "shadow_run_archive_manifest_version",
        "testnet_validation_manifest_version",
        "live_run_manifest_version",
    }
)
REQUIRED_PACK_EVIDENCE_OUTPUTS = frozenset(
    {
        "cycle_spec_resolved",
        "data_quality_report",
        "feature_build_manifest",
        "split_manifest",
        "candidate_rankings",
        "candidate_gate_report",
        "backtest_index",
        "metrics_by_split",
        "metrics_by_cost_stress",
        "metrics_by_regime",
        "metrics_by_side",
        "metrics_by_holding_window",
        "stability_regions",
        "ablation_report",
        "trial_budget_report",
        "overfit_adjustment_report",
        "rejection_report",
    }
)
CANDIDATE_METRIC_OUTPUTS = frozenset(
    {
        "metrics_by_split",
        "metrics_by_cost_stress",
        "metrics_by_regime",
        "metrics_by_side",
        "metrics_by_holding_window",
    }
)
REQUIRED_RESEARCH_COST_STRESS_SCENARIOS = frozenset(
    {
        "base_costs",
        "slippage_2x",
        "slippage_3x",
        "adverse_funding_shock",
        "wide_spread_stress",
        "missing_optional_context_stress",
        "high_volatility_only",
        "low_volatility_only",
        "trend_only",
        "range_only",
        "shock_transition_only",
    }
)
LOWER_TIMEFRAME_EXIT_POLICIES = frozenset({"triple_barrier", "triple_barrier_atr"})


@dataclass(frozen=True, slots=True)
class ResearchCandidateGate:
    candidate_id: str
    status: str
    reasons: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.status == "passed"


@dataclass(frozen=True, slots=True)
class ResearchCandidatePackResult:
    output_dir: Path
    manifest_path: Path
    evidence_index_path: Path


def evaluate_research_candidate_gate(
    *,
    cycle_manifest_path: Path,
    candidate_id: str,
) -> ResearchCandidateGate:
    cycle_manifest_path = Path(cycle_manifest_path)
    cycle_manifest = _read_json(cycle_manifest_path)
    manifest_reasons: list[str] = []
    try:
        _reject_live_adjacent_json(cycle_manifest_path)
    except ValueError:
        manifest_reasons.append("cycle_manifest_live_adjacent_or_invalid")
    manifest_reasons.extend(_cycle_manifest_gate_reasons(cycle_manifest))
    try:
        required_outputs = _required_outputs(cycle_manifest)
    except ValueError as exc:
        return ResearchCandidateGate(str(candidate_id), "blocked", tuple([*manifest_reasons, str(exc)]))
    output_reasons = _required_output_reasons(required_outputs)
    rankings_path = required_outputs.get("candidate_rankings")
    if rankings_path is None or not rankings_path.exists():
        reasons = [*manifest_reasons, *output_reasons, "candidate_rankings_required"]
        return ResearchCandidateGate(str(candidate_id), "blocked", tuple(dict.fromkeys(reasons)))
    rankings = pd.read_parquet(required_outputs["candidate_rankings"])
    matches = rankings.loc[rankings["candidate_id"].astype(str) == str(candidate_id)]
    if matches.empty:
        reasons = [*manifest_reasons, *output_reasons, "candidate_missing_from_rankings"]
        return ResearchCandidateGate(str(candidate_id), "blocked", tuple(dict.fromkeys(reasons)))
    row = matches.iloc[0].to_dict()
    spec_path = required_outputs.get("cycle_spec_resolved")
    spec = _read_json(spec_path) if spec_path is not None and spec_path.exists() else {}
    reasons = [
        *manifest_reasons,
        *output_reasons,
        *_gate_reasons(row, spec=spec),
        *_durable_evidence_reasons(str(candidate_id), ranking_row=row, spec=spec, required_outputs=required_outputs),
    ]
    return ResearchCandidateGate(str(candidate_id), "passed" if not reasons else "blocked", tuple(dict.fromkeys(reasons)))


def evaluate_research_candidate_gate_from_row(
    *,
    candidate_id: str,
    ranking_row: Mapping[str, Any],
    cycle_spec: Mapping[str, Any],
) -> ResearchCandidateGate:
    reasons = _gate_reasons(ranking_row, spec=cycle_spec)
    return ResearchCandidateGate(str(candidate_id), "passed" if not reasons else "blocked", tuple(reasons))


def write_research_candidate_pack(
    *,
    cycle_manifest_path: Path,
    candidate_id: str,
    output_dir: Path | None = None,
) -> ResearchCandidatePackResult:
    cycle_manifest_path = Path(cycle_manifest_path)
    cycle_manifest = _read_json(cycle_manifest_path)
    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest_path, candidate_id=candidate_id)
    if not gate.passed:
        raise ValueError("research candidate gate blocked: " + "|".join(gate.reasons))
    required_outputs = _required_outputs(cycle_manifest)
    rankings = pd.read_parquet(required_outputs["candidate_rankings"])
    ranking_row = rankings.loc[rankings["candidate_id"].astype(str) == str(candidate_id)].iloc[0].to_dict()
    output_dir = output_dir or cycle_manifest_path.parent / "research_candidate_pack" / _safe_name(candidate_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    evidence_rows = _evidence_rows(
        candidate_id=str(candidate_id),
        cycle_manifest_path=cycle_manifest_path,
        required_outputs=required_outputs,
    )
    source_data_evidence = _source_data_evidence(cycle_manifest)
    evidence_summary = _evidence_summary(evidence_rows)
    evidence_index_path = output_dir / "evidence_index.json"
    _write_json(evidence_index_path, {"evidence_summary": evidence_summary, "evidence": evidence_rows})

    manifest_path = output_dir / "research_candidate_pack_manifest.json"
    manifest = {
        "research_candidate_pack_manifest_version": RESEARCH_CANDIDATE_PACK_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "live_fetch_used": False,
        "order_placement_used": False,
        "intended_use": "research_observe_only",
        "candidate_id": str(candidate_id),
        "cycle_id": cycle_manifest.get("cycle_id"),
        "symbol": cycle_manifest.get("symbol"),
        "research_gate_status": gate.status,
        "research_gate_reasons": list(gate.reasons),
        "source_research_cycle_manifest_path": str(cycle_manifest_path),
        "source_research_cycle_manifest_sha256": _file_sha256(cycle_manifest_path),
        "source_data_evidence": source_data_evidence,
        "ranking_digest": _ranking_digest(ranking_row),
        "evidence_summary": evidence_summary,
        "required_outputs": {
            "research_candidate_pack_manifest": str(manifest_path),
            "evidence_index": str(evidence_index_path),
        },
        "evidence": evidence_rows,
        "promotion_candidate_manifest_path": None,
        "paper_run_manifest_path": None,
        "shadow_run_archive_manifest_path": None,
        "testnet_validation_manifest_path": None,
    }
    reasons = validate_research_candidate_pack_manifest(manifest)
    if reasons:
        raise ValueError("invalid research candidate pack manifest: " + "|".join(reasons))
    _write_json(manifest_path, manifest)
    return ResearchCandidatePackResult(
        output_dir=output_dir,
        manifest_path=manifest_path,
        evidence_index_path=evidence_index_path,
    )


def validate_research_candidate_pack_manifest(manifest: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if manifest.get("research_candidate_pack_manifest_version") != RESEARCH_CANDIDATE_PACK_VERSION:
        reasons.append("research_candidate_pack_manifest_version_required")
    if any(field in manifest for field in LIVE_ADJACENT_VERSION_FIELDS):
        reasons.append("live_or_promotion_manifest_version_forbidden")
    if manifest.get("research_only") is not True:
        reasons.append("research_only_must_be_true")
    if manifest.get("observe_only") is not True:
        reasons.append("observe_only_must_be_true")
    if manifest.get("promotion_ready") is not False:
        reasons.append("promotion_ready_must_be_false")
    if manifest.get("live_signal_input") is not False:
        reasons.append("live_signal_input_must_be_false")
    if manifest.get("position_sizing_input") is not False:
        reasons.append("position_sizing_input_must_be_false")
    if manifest.get("operator_control_input") is not False:
        reasons.append("operator_control_input_must_be_false")
    if manifest.get("live_execution_input") is not False:
        reasons.append("live_execution_input_must_be_false")
    if manifest.get("runtime_control_input") is not False:
        reasons.append("runtime_control_input_must_be_false")
    if manifest.get("live_fetch_used") is not False:
        reasons.append("live_fetch_used_must_be_false")
    if manifest.get("order_placement_used") is not False:
        reasons.append("order_placement_used_must_be_false")
    if str(manifest.get("intended_use") or "") != "research_observe_only":
        reasons.append("intended_use_must_be_research_observe_only")
    source = manifest.get("source_data_evidence")
    if not isinstance(source, Mapping):
        reasons.append("source_data_evidence_required")
    elif source.get("source_type") != "historical_fixture_pack":
        reasons.append("source_data_evidence_must_be_historical_fixture_pack")
    elif source.get("evidence_complete") is not True:
        reasons.append("source_data_evidence_must_be_complete")
    evidence_summary = manifest.get("evidence_summary")
    if not isinstance(evidence_summary, Mapping):
        reasons.append("evidence_summary_required")
    return reasons


def _cycle_manifest_gate_reasons(cycle_manifest: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if cycle_manifest.get("research_only") is not True:
        reasons.append("cycle_manifest_research_only_required")
    if cycle_manifest.get("observe_only") is not True:
        reasons.append("cycle_manifest_observe_only_required")
    if cycle_manifest.get("promotion_ready") is not False:
        reasons.append("cycle_manifest_promotion_ready_must_be_false")
    for field in (
        "live_signal_input",
        "position_sizing_input",
        "operator_control_input",
        "live_execution_input",
        "runtime_control_input",
        "live_fetch_used",
        "order_placement_used",
    ):
        if cycle_manifest.get(field) is not False:
            reasons.append(f"cycle_manifest_{field}_must_be_false")
    data_source = cycle_manifest.get("data_source")
    if not isinstance(data_source, Mapping):
        reasons.append("cycle_manifest_data_source_required")
        return reasons
    if data_source.get("source_type") != "historical_fixture_pack":
        reasons.append("historical_fixture_pack_source_required")
    if data_source.get("synthetic") is not False:
        reasons.append("non_synthetic_data_source_required")
    if not data_source.get("fixture_id"):
        reasons.append("fixture_id_required")
    validation = data_source.get("validation")
    if not isinstance(validation, Mapping) or validation.get("valid") is not True:
        reasons.append("fixture_pack_validation_required")
    manifest_path = data_source.get("manifest_path")
    if not manifest_path:
        reasons.append("fixture_manifest_path_required")
    else:
        path = Path(str(manifest_path))
        if not path.exists():
            reasons.append("fixture_manifest_path_missing")
        else:
            declared_sha = str(data_source.get("manifest_sha256") or "")
            if not declared_sha:
                reasons.append("fixture_manifest_sha256_required")
            elif declared_sha != _file_sha256(path):
                reasons.append("fixture_manifest_sha256_mismatch")
            try:
                fixture_manifest = _read_json(path)
                _reject_live_adjacent_json(path)
            except ValueError:
                reasons.append("fixture_manifest_live_adjacent_or_invalid")
            else:
                fixture_id = data_source.get("fixture_id")
                if fixture_id and str(fixture_manifest.get("fixture_id") or "") != str(fixture_id):
                    reasons.append("fixture_manifest_fixture_id_mismatch")
                if isinstance(validation, Mapping) and validation.get("fixture_id") and str(validation.get("fixture_id")) != str(fixture_id or ""):
                    reasons.append("fixture_validation_fixture_id_mismatch")
                fixture_source = fixture_manifest.get("source")
                if isinstance(fixture_source, Mapping):
                    if not isinstance(data_source.get("fixture_source"), Mapping):
                        reasons.append("fixture_source_required")
                    elif dict(data_source.get("fixture_source") or {}) != dict(fixture_source):
                        reasons.append("fixture_source_mismatch")
                fixture_derivation = fixture_manifest.get("derivation")
                if isinstance(fixture_derivation, Mapping):
                    if not isinstance(data_source.get("fixture_derivation"), Mapping):
                        reasons.append("fixture_derivation_required")
                    elif dict(data_source.get("fixture_derivation") or {}) != dict(fixture_derivation):
                        reasons.append("fixture_derivation_mismatch")
                if fixture_manifest.get("fixture_scope") is not None:
                    if data_source.get("fixture_scope") is None:
                        reasons.append("fixture_scope_required")
                    elif data_source.get("fixture_scope") != fixture_manifest.get("fixture_scope"):
                        reasons.append("fixture_scope_mismatch")
                fixture_omissions = fixture_manifest.get("omitted_optional_families")
                if isinstance(fixture_omissions, Mapping):
                    if not isinstance(data_source.get("omitted_optional_families"), Mapping):
                        reasons.append("fixture_omitted_optional_families_required")
                    elif dict(data_source.get("omitted_optional_families") or {}) != dict(fixture_omissions):
                        reasons.append("fixture_omitted_optional_families_mismatch")
                fixture_limitations = fixture_manifest.get("research_evidence_limitations")
                if isinstance(fixture_limitations, list):
                    if not isinstance(data_source.get("research_evidence_limitations"), list):
                        reasons.append("fixture_research_evidence_limitations_required")
                    elif list(data_source.get("research_evidence_limitations") or []) != list(fixture_limitations):
                        reasons.append("fixture_research_evidence_limitations_mismatch")
    dataset_path = data_source.get("dataset_path")
    if not dataset_path:
        reasons.append("fixture_dataset_path_required")
    elif not Path(str(dataset_path)).exists():
        reasons.append("fixture_dataset_path_missing")
    return reasons


def _gate_reasons(row: Mapping[str, Any], *, spec: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    validation = spec.get("validation") if isinstance(spec.get("validation"), Mapping) else {}
    trade_count_floor = int(validation.get("trade_count_floor", 50)) if isinstance(validation, Mapping) else 50
    max_single_split_pnl_share = float(validation.get("max_single_split_pnl_share", 0.5)) if isinstance(validation, Mapping) else 0.5
    min_cost_stress_survival_rate = (
        float(validation.get("min_cost_stress_survival_rate", 1.0)) if isinstance(validation, Mapping) else 1.0
    )
    if str(row.get("decision") or "").lower() not in {"research_gate_passed", "research_pack_eligible"}:
        reasons.append("ranking_decision_not_research_gate_passed")
    if bool(row.get("empirical_evidence")) is not True:
        reasons.append("empirical_evidence_required")
    if str(row.get("data_evidence_scope") or "") == "synthetic_fixture":
        reasons.append("synthetic_fixture_not_research_pack_evidence")
    if bool(row.get("split_evaluated")) is not True:
        reasons.append("split_evaluation_required")
    if bool(row.get("cost_stress_evaluated")) is not True:
        reasons.append("cost_stress_evaluation_required")
    if bool(row.get("stability_evaluated")) is not True:
        reasons.append("validated_stability_region_required")
    if str(row.get("stability_validation_scope") or "") != "split_cost_stress_enriched":
        reasons.append("split_cost_stress_stability_scope_required")
    split_count = int(row.get("split_evaluation_count", 0))
    required_split_count = int(row.get("required_split_count", 1))
    if split_count < required_split_count:
        reasons.append("split_evaluation_count_below_required")
    cost_count = int(row.get("cost_stress_evaluation_count", 0))
    required_cost_count = int(row.get("required_cost_stress_count", 1))
    if cost_count < required_cost_count:
        reasons.append("cost_stress_evaluation_count_below_required")
    if int(row.get("trade_count", 0)) < trade_count_floor:
        reasons.append("trade_count_below_research_floor")
    if float(row.get("split_consistency", 0.0)) <= 0.0:
        reasons.append("positive_split_consistency_required")
    if float(row.get("cost_stress_survival", 0.0)) <= 0.0:
        reasons.append("positive_cost_stress_survival_required")
    if float(row.get("cost_stress_survival", 0.0)) < min_cost_stress_survival_rate:
        reasons.append("cost_stress_survival_rate_below_required")
    if str(row.get("cost_stress_survival_floor_status") or "") == "failed":
        reasons.append("cost_stress_survival_floor_status_failed")
    if str(row.get("split_trade_count_floor_status") or "") == "failed":
        reasons.append("split_trade_count_floor_status_failed")
    if str(row.get("split_validation_method_status") or "") == "incomplete":
        reasons.append("split_validation_method_coverage_incomplete")
    if str(row.get("baseline_comparator_coverage_status") or "") != "complete":
        reasons.append("baseline_comparator_coverage_complete_required")
    expectancy_vs_no_trade = _optional_float(row.get("expectancy_vs_no_trade"))
    if expectancy_vs_no_trade is None or expectancy_vs_no_trade <= 0.0:
        reasons.append("positive_expectancy_vs_no_trade_required")
    if str(row.get("side_evidence_status") or "") != "complete":
        reasons.append("complete_side_evidence_required")
    if str(row.get("regime_evidence_status") or "") != "complete":
        reasons.append("complete_regime_evidence_required")
    if str(row.get("cost_stress_scenario_status") or "") != "complete":
        reasons.append("complete_cost_stress_scenario_evidence_required")
    scenario_ids = {item for item in str(row.get("cost_stress_scenarios") or "").split("|") if item}
    missing_cost_scenarios = sorted(REQUIRED_RESEARCH_COST_STRESS_SCENARIOS - scenario_ids)
    if missing_cost_scenarios:
        reasons.append("complete_cost_stress_scenario_set_required")
    if str(row.get("split_dominance_status") or "") != "complete":
        reasons.append("split_dominance_evidence_required")
    observed_max_split_share = _optional_float(row.get("max_single_split_pnl_share"))
    if observed_max_split_share is None:
        reasons.append("max_single_split_pnl_share_required")
    elif observed_max_split_share > max_single_split_pnl_share:
        reasons.append("max_single_split_pnl_share_above_limit")
    if bool(row.get("feature_ablation_passed")) is not True:
        reasons.append("candidate_feature_ablation_pass_required")
    if str(row.get("ablation_evidence_status") or "") not in {
        "baseline_feature_set_no_optional_claim",
        "comparator_feature_set_passed",
    }:
        reasons.append("candidate_feature_ablation_status_not_passing")
    if str(row.get("ablation_failure_reasons") or "").strip():
        reasons.append("candidate_feature_ablation_failure_reasons_not_empty")
    failure_reasons = str(row.get("failure_reasons") or "")
    for blocked in (
        "synthetic_fixture",
        "promotion_blocked",
        "candidate_acceptance_blocked",
        "split_and_cost_stress_evaluation_reserved_for_shortlist",
        "validated_stability_region_reserved_for_shortlist",
    ):
        if blocked in failure_reasons:
            reasons.append(f"blocked_failure_reason:{blocked}")
    return list(dict.fromkeys(reasons))


def _durable_evidence_reasons(
    candidate_id: str,
    *,
    ranking_row: Mapping[str, Any],
    spec: Mapping[str, Any],
    required_outputs: Mapping[str, Path],
) -> list[str]:
    reasons: list[str] = []
    gate_report_path = required_outputs.get("candidate_gate_report")
    if gate_report_path is None or not gate_report_path.exists():
        reasons.append("candidate_gate_report_required")
    else:
        gate_report = pd.read_parquet(gate_report_path)
        matches = gate_report.loc[gate_report["candidate_id"].astype(str) == candidate_id]
        if matches.empty:
            reasons.append("candidate_gate_report_row_required")
        else:
            gate_row = matches.iloc[0].to_dict()
            if str(gate_row.get("gate_status") or "") != "passed":
                reasons.append("candidate_gate_report_status_not_passed")
            if bool(gate_row.get("pack_eligible")) is not True:
                reasons.append("candidate_gate_report_not_pack_eligible")
            if str(gate_row.get("gate_reasons") or "").strip():
                reasons.append("candidate_gate_report_reasons_not_empty")
    stability_regions_path = required_outputs.get("stability_regions")
    if stability_regions_path is None or not stability_regions_path.exists():
        reasons.append("stability_region_artifact_required")
    else:
        stability_regions = pd.read_parquet(stability_regions_path)
        matches = stability_regions.loc[stability_regions["candidate_id"].astype(str) == candidate_id]
        if matches.empty:
            reasons.append("stability_region_row_required")
        else:
            region = matches.iloc[0].to_dict()
            if bool(region.get("validation_enriched")) is not True:
                reasons.append("stability_region_validation_enriched_required")
            if str(region.get("stability_validation_scope") or "") != "split_cost_stress_enriched":
                reasons.append("stability_region_split_cost_stress_scope_required")
            if str(region.get("decision") or "") != "accepted_region":
                reasons.append("stability_region_accepted_decision_required")
    reasons.extend(_candidate_metric_rows_reasons(candidate_id, ranking_row=ranking_row, spec=spec, required_outputs=required_outputs))
    reasons.extend(_candidate_backtest_evidence_reasons(candidate_id, required_outputs=required_outputs))
    reasons.extend(_candidate_lower_timeframe_evidence_reasons(candidate_id, ranking_row=ranking_row, required_outputs=required_outputs))
    reasons.extend(_candidate_ablation_evidence_reasons(candidate_id, ranking_row=ranking_row, required_outputs=required_outputs))
    return reasons


def _required_output_reasons(required_outputs: Mapping[str, Path]) -> list[str]:
    reasons: list[str] = []
    missing_names = sorted(REQUIRED_PACK_EVIDENCE_OUTPUTS - set(required_outputs))
    reasons.extend(f"required_output_missing:{name}" for name in missing_names)
    for name, path in sorted(required_outputs.items()):
        if not path.exists():
            reasons.append(f"required_output_path_missing:{name}")
            continue
        if path.suffix.lower() == ".json":
            try:
                _reject_live_adjacent_json(path)
            except ValueError:
                reasons.append(f"required_output_live_adjacent_or_promotion_ready:{name}")
    return reasons


def _candidate_metric_rows_reasons(
    candidate_id: str,
    *,
    ranking_row: Mapping[str, Any],
    spec: Mapping[str, Any],
    required_outputs: Mapping[str, Path],
) -> list[str]:
    reasons: list[str] = []
    holding_window = str(ranking_row.get("holding_window") or "")
    split_manifest = _split_manifest_payload(required_outputs)
    for name in sorted(CANDIDATE_METRIC_OUTPUTS):
        path = required_outputs.get(name)
        if path is None or not path.exists():
            continue
        try:
            frame = pd.read_parquet(path)
        except Exception:
            reasons.append(f"candidate_metric_artifact_invalid:{name}")
            continue
        if "candidate_id" not in frame.columns:
            reasons.append(f"candidate_metric_identity_column_required:{name}")
            continue
        matches = frame.loc[frame["candidate_id"].astype(str) == candidate_id]
        if name == "metrics_by_holding_window" and holding_window:
            matches = matches.loc[matches["holding_window"].astype(str) == holding_window] if "holding_window" in matches.columns else matches
        if matches.empty:
            reasons.append(f"candidate_metric_rows_required:{name}")
            continue
        if name == "metrics_by_split":
            reasons.extend(_split_metric_rows_reasons(matches, ranking_row=ranking_row, spec=spec, split_manifest=split_manifest))
        elif name == "metrics_by_cost_stress":
            reasons.extend(_cost_stress_metric_rows_reasons(matches, ranking_row=ranking_row, spec=spec))
        elif name == "metrics_by_regime":
            reasons.extend(_regime_metric_rows_reasons(matches))
        elif name == "metrics_by_side":
            reasons.extend(_side_metric_rows_reasons(matches, ranking_row=ranking_row))
    return reasons


def _split_manifest_payload(required_outputs: Mapping[str, Path]) -> Mapping[str, Any]:
    path = required_outputs.get("split_manifest")
    if path is None or not path.exists():
        return {}
    try:
        return _read_json(path)
    except ValueError:
        return {}


def _split_metric_rows_reasons(
    frame: pd.DataFrame,
    *,
    ranking_row: Mapping[str, Any],
    spec: Mapping[str, Any],
    split_manifest: Mapping[str, Any],
) -> list[str]:
    reasons: list[str] = []
    missing = _missing_columns(
        frame,
        {
            "split_id",
            "validation_method",
            "trade_count",
            "costed_expectancy",
            "net_return_after_fees_slippage_funding",
            "max_drawdown",
            "backtest_manifest_path",
        },
    )
    reasons.extend(f"candidate_split_metric_column_required:{column}" for column in missing)
    if missing:
        return reasons
    required_split_count = int(ranking_row.get("required_split_count", 1))
    validation = spec.get("validation") if isinstance(spec.get("validation"), Mapping) else {}
    trade_count_floor = int(validation.get("trade_count_floor", ranking_row.get("split_trade_count_floor", 50)))
    max_single_split_pnl_share = float(validation.get("max_single_split_pnl_share", 0.5))
    split_ids = {str(value) for value in frame["split_id"].dropna().tolist() if str(value)}
    if len(split_ids) < required_split_count:
        reasons.append("candidate_split_metric_count_below_required")
    if (pd.to_numeric(frame["trade_count"], errors="coerce").fillna(0).astype(int) <= 0).any():
        reasons.append("candidate_split_metric_trade_count_required")
    if (pd.to_numeric(frame["trade_count"], errors="coerce").fillna(0).astype(int) < trade_count_floor).any():
        reasons.append("candidate_split_metric_trade_count_below_floor")
    if not frame["validation_method"].astype(str).str.strip().all():
        reasons.append("candidate_split_metric_validation_method_required")
    validation_methods = {str(value) for value in frame["validation_method"].dropna().tolist() if str(value)}
    required_methods = {
        str(value)
        for value in split_manifest.get("validation_methods", ())
        if str(value)
    }
    if required_methods and not required_methods <= validation_methods:
        reasons.append("candidate_split_metric_validation_method_coverage_incomplete")
    method_counts = split_manifest.get("validation_method_counts")
    if isinstance(method_counts, Mapping):
        actual_counts = frame["validation_method"].astype(str).value_counts().to_dict()
        missing_counts = [
            str(method)
            for method, expected in method_counts.items()
            if int(actual_counts.get(str(method), 0)) < int(expected)
        ]
        if missing_counts:
            reasons.append("candidate_split_metric_validation_method_count_below_required")
    returns = pd.to_numeric(frame["net_return_after_fees_slippage_funding"], errors="coerce").abs().fillna(0.0)
    total_return = float(returns.sum())
    max_share = float(returns.max() / total_return) if total_return > 0.0 else 0.0
    if max_share > max_single_split_pnl_share:
        reasons.append("candidate_split_metric_max_single_split_pnl_share_above_limit")
    return reasons


def _cost_stress_metric_rows_reasons(
    frame: pd.DataFrame,
    *,
    ranking_row: Mapping[str, Any],
    spec: Mapping[str, Any],
) -> list[str]:
    reasons: list[str] = []
    missing = _missing_columns(
        frame,
        {
            "scenario_id",
            "fee_bps",
            "slippage_bps",
            "funding_rate",
            "scenario_group",
            "trade_count",
            "stressed_expectancy",
            "stressed_net_return",
            "spread_bps",
            "source_row_count",
            "scenario_status",
            "backtest_manifest_path",
        },
    )
    reasons.extend(f"candidate_cost_stress_metric_column_required:{column}" for column in missing)
    if missing:
        return reasons
    required_cost_count = int(ranking_row.get("required_cost_stress_count", 1))
    validation = spec.get("validation") if isinstance(spec.get("validation"), Mapping) else {}
    min_survival_rate = float(validation.get("min_cost_stress_survival_rate", 1.0))
    scenario_ids = {str(value) for value in frame["scenario_id"].dropna().tolist() if str(value)}
    if len(scenario_ids) < required_cost_count:
        reasons.append("candidate_cost_stress_metric_count_below_required")
    missing_required_scenarios = sorted(REQUIRED_RESEARCH_COST_STRESS_SCENARIOS - scenario_ids)
    if missing_required_scenarios:
        reasons.append("candidate_cost_stress_required_scenarios_missing")
    if required_cost_count > 1 and scenario_ids <= {"base_costs"}:
        reasons.append("candidate_cost_stress_non_base_scenario_required")
    if (pd.to_numeric(frame["trade_count"], errors="coerce").fillna(0).astype(int) <= 0).any():
        reasons.append("candidate_cost_stress_metric_trade_count_required")
    if (pd.to_numeric(frame["source_row_count"], errors="coerce").fillna(0).astype(int) <= 0).any():
        reasons.append("candidate_cost_stress_source_rows_required")
    if set(frame["scenario_status"].astype(str)) != {"evaluated"}:
        reasons.append("candidate_cost_stress_scenario_status_evaluated_required")
    required_frame = frame.loc[frame["scenario_id"].astype(str).isin(REQUIRED_RESEARCH_COST_STRESS_SCENARIOS)].copy()
    stress_scores = pd.to_numeric(
        required_frame.get("stress_survival_score", pd.Series(dtype=float)),
        errors="coerce",
    )
    if stress_scores.empty or stress_scores.isna().all():
        stress_scores = (
            pd.to_numeric(required_frame["stressed_expectancy"], errors="coerce").fillna(0.0)
            + pd.to_numeric(required_frame["stressed_net_return"], errors="coerce").fillna(0.0)
        )
    survival_rate = float((stress_scores > 0.0).sum() / len(REQUIRED_RESEARCH_COST_STRESS_SCENARIOS))
    if survival_rate < min_survival_rate:
        reasons.append("candidate_cost_stress_survival_rate_below_required")
    if (
        survival_rate < min_survival_rate
        and "stress_survival_status" in required_frame.columns
        and (required_frame["stress_survival_status"].astype(str) == "failed").any()
    ):
        reasons.append("candidate_cost_stress_survival_status_failed")
    missing_manifest_paths = [
        str(path) for path in frame["backtest_manifest_path"].astype(str).tolist()
        if not path or not Path(path).exists()
    ]
    if missing_manifest_paths:
        reasons.append("candidate_cost_stress_backtest_manifest_path_required")
    return reasons


def _regime_metric_rows_reasons(frame: pd.DataFrame) -> list[str]:
    reasons: list[str] = []
    missing = _missing_columns(
        frame,
        {
            "regime",
            "trade_count",
            "costed_expectancy",
            "net_return_after_fees_slippage_funding",
            "hit_rate",
            "backtest_manifest_path",
        },
    )
    reasons.extend(f"candidate_regime_metric_column_required:{column}" for column in missing)
    if missing:
        return reasons
    regimes = {str(value).lower() for value in frame["regime"].dropna().tolist()}
    invalid = {"", "all", "aggregate", "missing", "unknown"}
    if regimes & {"all", "aggregate", ""}:
        reasons.append("candidate_regime_metric_aggregate_label_forbidden")
    real_regimes = regimes - invalid
    if len(real_regimes) < 2:
        reasons.append("candidate_regime_metric_multiple_regimes_required")
    if (pd.to_numeric(frame["trade_count"], errors="coerce").fillna(0).astype(int) <= 0).all():
        reasons.append("candidate_regime_metric_trade_count_required")
    return reasons


def _side_metric_rows_reasons(frame: pd.DataFrame, *, ranking_row: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    missing = _missing_columns(
        frame,
        {
            "side",
            "trade_count",
            "costed_expectancy",
            "net_return_after_fees_slippage_funding",
            "hit_rate",
            "backtest_manifest_path",
        },
    )
    reasons.extend(f"candidate_side_metric_column_required:{column}" for column in missing)
    if missing:
        return reasons
    sides = {str(value).lower() for value in frame["side"].dropna().tolist()}
    if not sides <= {"long", "short"}:
        reasons.append("candidate_side_metric_invalid_side")
    if bool(ranking_row.get("side_evidence_exception")) is not True and sides != {"long", "short"}:
        reasons.append("candidate_side_metric_long_short_required")
    if (pd.to_numeric(frame["trade_count"], errors="coerce").fillna(0).astype(int) <= 0).any():
        reasons.append("candidate_side_metric_trade_count_required")
    return reasons


def _missing_columns(frame: pd.DataFrame, columns: set[str]) -> list[str]:
    return sorted(column for column in columns if column not in frame.columns)


def _candidate_backtest_evidence_reasons(candidate_id: str, *, required_outputs: Mapping[str, Path]) -> list[str]:
    reasons: list[str] = []
    backtest_index_path = required_outputs.get("backtest_index")
    if backtest_index_path is None or not backtest_index_path.exists():
        return ["backtest_index_required"]
    backtest_index = pd.read_parquet(backtest_index_path)
    matches = backtest_index.loc[backtest_index["candidate_id"].astype(str) == candidate_id]
    if matches.empty:
        return ["candidate_backtest_index_rows_required"]
    scopes = {str(scope) for scope in matches.get("evaluation_scope", pd.Series(dtype=object)).dropna().tolist()}
    required_scopes = {"aggregate", "walk_forward_split", "cost_stress"}
    for scope in sorted(required_scopes - scopes):
        reasons.append(f"candidate_backtest_scope_required:{scope}")
    if "aggregate" not in scopes:
        reasons.append("candidate_aggregate_backtest_required")
    for record in matches.to_dict("records"):
        raw_manifest_path = str(record.get("backtest_manifest_path") or "")
        raw_metrics_path = str(record.get("metrics_path") or "")
        manifest_path = Path(raw_manifest_path)
        metrics_path = Path(raw_metrics_path)
        scope = str(record.get("evaluation_scope") or "unknown")
        if not raw_manifest_path or not manifest_path.exists():
            reasons.append(f"candidate_backtest_manifest_missing:{scope}")
            continue
        try:
            manifest = _read_json(manifest_path)
            _reject_live_adjacent_json(manifest_path)
        except ValueError:
            reasons.append(f"candidate_backtest_manifest_live_adjacent_or_invalid:{scope}")
            continue
        if manifest.get("research_only") is not True:
            reasons.append(f"candidate_backtest_manifest_research_only_required:{scope}")
        if manifest.get("observe_only") is not True:
            reasons.append(f"candidate_backtest_manifest_observe_only_required:{scope}")
        if manifest.get("promotion_ready") is not False:
            reasons.append(f"candidate_backtest_manifest_promotion_ready_must_be_false:{scope}")
        if manifest.get("cache_lookup_used") is not False:
            reasons.append(f"candidate_backtest_cache_lookup_must_be_false:{scope}")
        if manifest.get("cache_hit") is not False:
            reasons.append(f"candidate_backtest_cache_hit_must_be_false:{scope}")
        if manifest.get("execution_cache_reuse_enabled") is not False:
            reasons.append(f"candidate_backtest_execution_cache_reuse_must_be_false:{scope}")
        if not raw_metrics_path or not metrics_path.exists():
            reasons.append(f"candidate_backtest_metrics_missing:{scope}")
            continue
        if metrics_path.suffix.lower() == ".json":
            try:
                _reject_live_adjacent_json(metrics_path)
            except ValueError:
                reasons.append(f"candidate_backtest_metrics_live_adjacent_or_invalid:{scope}")
    return reasons


def _candidate_lower_timeframe_evidence_reasons(
    candidate_id: str,
    *,
    ranking_row: Mapping[str, Any],
    required_outputs: Mapping[str, Path],
) -> list[str]:
    backtest_index_path = required_outputs.get("backtest_index")
    if backtest_index_path is None or not backtest_index_path.exists():
        return []
    backtest_index = pd.read_parquet(backtest_index_path)
    if "candidate_id" not in backtest_index.columns:
        return []
    matches = backtest_index.loc[backtest_index["candidate_id"].astype(str) == candidate_id].copy()
    if matches.empty:
        return []
    lower_required = _candidate_requires_lower_timeframe_evidence(ranking_row, matches)
    if not lower_required:
        return []

    reasons: list[str] = []
    source_evidence = _lower_timeframe_source_evidence(required_outputs)
    source_hash = str(source_evidence.get("sha256") or "")
    source_path = str(source_evidence.get("path") or "")
    if not source_evidence.get("complete"):
        reasons.append("candidate_lower_timeframe_source_evidence_required")
        if not source_evidence.get("family_present"):
            reasons.append("candidate_lower_timeframe_source_family_required")
        if not source_path:
            reasons.append("candidate_lower_timeframe_source_path_required")
        elif not Path(source_path).exists():
            reasons.append("candidate_lower_timeframe_source_path_missing")
        if not source_hash:
            reasons.append("candidate_lower_timeframe_source_sha256_required")
        elif source_path and Path(source_path).exists() and _file_sha256(Path(source_path)) != source_hash:
            reasons.append("candidate_lower_timeframe_source_sha256_mismatch")
        if int(source_evidence.get("row_count") or 0) <= 0:
            reasons.append("candidate_lower_timeframe_source_row_count_required")

    missing_columns = _missing_columns(
        matches,
        {
            "evaluation_scope",
            "exit_policy_id",
            "exit_price_source",
            "lower_timeframe_required",
            "lower_timeframe_sequence_used",
            "lower_timeframe_dataset_path",
            "lower_timeframe_dataset_sha256",
            "lower_timeframe_cache_key_component",
            "trade_count",
            "exit_sequence_proof_counts_json",
            "barrier_hit_type_counts_json",
            "exit_price_source_counts_json",
            "backtest_manifest_path",
        },
    )
    reasons.extend(f"candidate_lower_timeframe_backtest_index_column_required:{column}" for column in missing_columns)
    if missing_columns:
        return list(dict.fromkeys(reasons))

    for record in matches.to_dict("records"):
        scope = str(record.get("evaluation_scope") or "unknown")
        index_hash = str(record.get("lower_timeframe_dataset_sha256") or "")
        index_path = str(record.get("lower_timeframe_dataset_path") or "")
        trade_count = int(record.get("trade_count") or 0)
        if str(record.get("exit_policy_id") or "") not in LOWER_TIMEFRAME_EXIT_POLICIES:
            reasons.append(f"candidate_lower_timeframe_exit_policy_required:{scope}")
        if str(record.get("exit_price_source") or "") != "lower_timeframe_ohlc_sequence":
            reasons.append(f"candidate_lower_timeframe_exit_price_source_required:{scope}")
        if bool(record.get("lower_timeframe_required")) is not True:
            reasons.append(f"candidate_lower_timeframe_required_flag_missing:{scope}")
        if bool(record.get("lower_timeframe_sequence_used")) is not True:
            reasons.append(f"candidate_lower_timeframe_sequence_used_required:{scope}")
        if not index_path:
            reasons.append(f"candidate_lower_timeframe_dataset_path_required:{scope}")
        elif not Path(index_path).exists():
            reasons.append(f"candidate_lower_timeframe_dataset_path_missing:{scope}")
        if not index_hash:
            reasons.append(f"candidate_lower_timeframe_dataset_sha256_required:{scope}")
        elif source_hash and index_hash != source_hash:
            reasons.append(f"candidate_lower_timeframe_dataset_sha256_mismatch:{scope}")
        elif index_path and Path(index_path).exists() and _file_sha256(Path(index_path)) != index_hash:
            reasons.append(f"candidate_lower_timeframe_dataset_file_hash_mismatch:{scope}")
        if str(record.get("lower_timeframe_cache_key_component") or "") != index_hash:
            reasons.append(f"candidate_lower_timeframe_cache_component_mismatch:{scope}")

        proof_counts = _json_count_payload(record.get("exit_sequence_proof_counts_json"))
        barrier_counts = _json_count_payload(record.get("barrier_hit_type_counts_json"))
        price_source_counts = _json_count_payload(record.get("exit_price_source_counts_json"))
        if trade_count > 0:
            if int(proof_counts.get("lower_timeframe_ohlc", 0)) <= 0:
                reasons.append(f"candidate_lower_timeframe_sequence_proof_required:{scope}")
            if not barrier_counts:
                reasons.append(f"candidate_lower_timeframe_barrier_counts_required:{scope}")
            if int(price_source_counts.get("lower_timeframe_ohlc_sequence", 0)) != trade_count:
                reasons.append(f"candidate_lower_timeframe_exit_price_source_counts_mismatch:{scope}")

        manifest_path = Path(str(record.get("backtest_manifest_path") or ""))
        if manifest_path.exists():
            manifest_reasons = _lower_timeframe_backtest_manifest_reasons(
                manifest_path,
                scope=scope,
                expected_hash=index_hash,
                expected_path=index_path,
            )
            reasons.extend(manifest_reasons)
    return list(dict.fromkeys(reasons))


def _candidate_requires_lower_timeframe_evidence(ranking_row: Mapping[str, Any], backtest_rows: pd.DataFrame) -> bool:
    if str(ranking_row.get("exit_policy_id") or "") in LOWER_TIMEFRAME_EXIT_POLICIES:
        return True
    if bool(ranking_row.get("aggregate_backtest_lower_timeframe_required")) is True:
        return True
    if "exit_policy_id" in backtest_rows.columns:
        if set(backtest_rows["exit_policy_id"].dropna().astype(str)) & LOWER_TIMEFRAME_EXIT_POLICIES:
            return True
    if "lower_timeframe_required" in backtest_rows.columns:
        return bool(backtest_rows["lower_timeframe_required"].fillna(False).astype(bool).any())
    return False


def _lower_timeframe_source_evidence(required_outputs: Mapping[str, Path]) -> dict[str, Any]:
    path = required_outputs.get("research_cycle_manifest")
    if path is None or not path.exists():
        return {"complete": False, "family_present": False}
    try:
        cycle_manifest = _read_json(path)
    except ValueError:
        return {"complete": False, "family_present": False}
    raw = cycle_manifest.get("lower_timeframe_evidence")
    if not isinstance(raw, Mapping):
        raw = cycle_manifest.get("data_source") if isinstance(cycle_manifest.get("data_source"), Mapping) else {}
    evidence = dict(raw or {})
    family_present = bool(evidence.get("lower_timeframe_family_present", False))
    dataset_path = str(evidence.get("lower_timeframe_dataset_path") or "")
    sha256_value = str(evidence.get("lower_timeframe_dataset_sha256") or "")
    row_count = int(evidence.get("lower_timeframe_row_count") or 0)
    path_exists = bool(dataset_path) and Path(dataset_path).exists()
    sha_matches = bool(sha256_value) and path_exists and _file_sha256(Path(dataset_path)) == sha256_value
    return {
        "complete": bool(family_present and path_exists and sha_matches and row_count > 0),
        "family_present": family_present,
        "path": dataset_path,
        "sha256": sha256_value,
        "row_count": row_count,
        "path_exists": path_exists,
        "sha256_verified": sha_matches,
        "family": dict(evidence.get("lower_timeframe_family") or {}),
    }


def _lower_timeframe_backtest_manifest_reasons(
    manifest_path: Path,
    *,
    scope: str,
    expected_hash: str,
    expected_path: str,
) -> list[str]:
    reasons: list[str] = []
    try:
        manifest = _read_json(manifest_path)
    except ValueError:
        return [f"candidate_lower_timeframe_backtest_manifest_invalid:{scope}"]
    if str(manifest.get("exit_policy_id") or "") not in LOWER_TIMEFRAME_EXIT_POLICIES:
        reasons.append(f"candidate_lower_timeframe_manifest_exit_policy_required:{scope}")
    if str(manifest.get("exit_price_source") or "") != "lower_timeframe_ohlc_sequence":
        reasons.append(f"candidate_lower_timeframe_manifest_exit_price_source_required:{scope}")
    if str(manifest.get("lower_timeframe_dataset_path") or "") != expected_path:
        reasons.append(f"candidate_lower_timeframe_manifest_path_mismatch:{scope}")
    manifest_hash = str(manifest.get("lower_timeframe_dataset_sha256") or "")
    if manifest_hash != expected_hash:
        reasons.append(f"candidate_lower_timeframe_manifest_sha256_mismatch:{scope}")
    cache_components = manifest.get("cache_key_components")
    if not isinstance(cache_components, Mapping) or str(cache_components.get("lower_timeframe_dataset_sha256") or "") != expected_hash:
        reasons.append(f"candidate_lower_timeframe_manifest_cache_component_mismatch:{scope}")
    return reasons


def _json_count_payload(value: Any) -> dict[str, int]:
    if isinstance(value, Mapping):
        payload = value
    else:
        try:
            payload = json.loads(str(value or "{}"))
        except json.JSONDecodeError:
            return {}
    if not isinstance(payload, Mapping):
        return {}
    counts: dict[str, int] = {}
    for key, count in payload.items():
        try:
            counts[str(key)] = int(count)
        except (TypeError, ValueError):
            continue
    return counts


def _candidate_ablation_evidence_reasons(
    candidate_id: str,
    *,
    ranking_row: Mapping[str, Any],
    required_outputs: Mapping[str, Path],
) -> list[str]:
    path = required_outputs.get("ablation_report")
    if path is None or not path.exists():
        return ["candidate_ablation_report_required"]
    try:
        report = _read_json(path)
        _reject_live_adjacent_json(path)
    except ValueError:
        return ["candidate_ablation_report_live_adjacent_or_invalid"]
    rows = report.get("candidate_rows")
    if not isinstance(rows, list):
        return ["candidate_ablation_rows_required"]
    matches = [
        row for row in rows
        if isinstance(row, Mapping) and str(row.get("candidate_id") or "") == candidate_id
    ]
    if not matches:
        return ["candidate_ablation_row_required"]
    row = matches[0]
    reasons: list[str] = []
    if bool(row.get("feature_ablation_passed")) is not True:
        reasons.append("candidate_ablation_report_pass_required")
    if str(row.get("ablation_evidence_status") or "") != str(ranking_row.get("ablation_evidence_status") or ""):
        reasons.append("candidate_ablation_report_status_mismatch")
    if str(row.get("ablation_failure_reasons") or "").strip():
        reasons.append("candidate_ablation_report_failure_reasons_not_empty")
    comparator_required = bool(ranking_row.get("feature_ablation_required"))
    if comparator_required and not row.get("ablation_comparator_candidate_id"):
        reasons.append("candidate_ablation_report_comparator_required")
    return reasons


def _evidence_rows(
    *,
    candidate_id: str,
    cycle_manifest_path: Path,
    required_outputs: Mapping[str, Path],
) -> list[dict[str, Any]]:
    rows = [
        _evidence_row("research_cycle_manifest", cycle_manifest_path),
    ]
    for name, path in required_outputs.items():
        if name == "research_cycle_manifest":
            continue
        rows.append(_evidence_row(name, path))
    backtest_index_path = required_outputs.get("backtest_index")
    if backtest_index_path is not None and backtest_index_path.exists():
        backtest_index = pd.read_parquet(backtest_index_path)
        for record in backtest_index.loc[backtest_index["candidate_id"].astype(str) == candidate_id].to_dict("records"):
            manifest_path = Path(str(record.get("backtest_manifest_path")))
            if manifest_path.exists():
                rows.append(_evidence_row(f"candidate_backtest_manifest:{record.get('evaluation_scope')}", manifest_path))
            metrics_path = Path(str(record.get("metrics_path")))
            if metrics_path.exists():
                rows.append(_evidence_row(f"candidate_backtest_metrics:{record.get('evaluation_scope')}", metrics_path))
    return rows


def _source_data_evidence(cycle_manifest: Mapping[str, Any]) -> dict[str, Any]:
    data_source = cycle_manifest.get("data_source")
    if not isinstance(data_source, Mapping):
        return {"source_type": "missing", "evidence_complete": False}
    manifest_path = data_source.get("manifest_path")
    dataset_path = data_source.get("dataset_path")
    validation = data_source.get("validation")
    validation_payload = dict(validation) if isinstance(validation, Mapping) else {}
    manifest_sha256_verified = (
        bool(manifest_path)
        and Path(str(manifest_path)).exists()
        and str(data_source.get("manifest_sha256") or "") == _file_sha256(Path(str(manifest_path)))
    )
    fixture_manifest_safe = False
    fixture_manifest_fixture_id_matches = False
    fixture_source_matches_manifest = False
    fixture_derivation_matches_manifest = False
    fixture_scope_matches_manifest = False
    fixture_omitted_optional_families_matches_manifest = False
    fixture_research_evidence_limitations_match_manifest = False
    fixture_manifest_source: dict[str, Any] = {}
    fixture_manifest_derivation: dict[str, Any] = {}
    fixture_manifest_scope: Any = None
    fixture_manifest_omitted_optional_families: dict[str, Any] = {}
    fixture_manifest_limitations: list[Any] = []
    lower_timeframe_evidence = _source_lower_timeframe_evidence(cycle_manifest, data_source)
    if manifest_sha256_verified:
        try:
            fixture_manifest = _read_json(Path(str(manifest_path)))
            _reject_live_adjacent_json(Path(str(manifest_path)))
        except ValueError:
            fixture_manifest = {}
        else:
            fixture_manifest_safe = True
            fixture_manifest_fixture_id_matches = (
                bool(data_source.get("fixture_id"))
                and str(fixture_manifest.get("fixture_id") or "") == str(data_source.get("fixture_id"))
            )
            fixture_manifest_source = dict(fixture_manifest.get("source") or {})
            fixture_manifest_derivation = dict(fixture_manifest.get("derivation") or {})
            fixture_manifest_scope = fixture_manifest.get("fixture_scope")
            fixture_manifest_omitted_optional_families = dict(fixture_manifest.get("omitted_optional_families") or {})
            fixture_manifest_limitations = list(fixture_manifest.get("research_evidence_limitations") or [])
            fixture_source_matches_manifest = dict(data_source.get("fixture_source") or {}) == fixture_manifest_source
            fixture_derivation_matches_manifest = dict(data_source.get("fixture_derivation") or {}) == fixture_manifest_derivation
            fixture_scope_matches_manifest = data_source.get("fixture_scope") == fixture_manifest_scope
            fixture_omitted_optional_families_matches_manifest = (
                dict(data_source.get("omitted_optional_families") or {})
                == fixture_manifest_omitted_optional_families
            )
            fixture_research_evidence_limitations_match_manifest = (
                list(data_source.get("research_evidence_limitations") or []) == fixture_manifest_limitations
            )
    dataset_exists = bool(dataset_path) and Path(str(dataset_path)).exists()
    return {
        "source_type": data_source.get("source_type"),
        "synthetic": bool(data_source.get("synthetic", True)),
        "fixture_id": data_source.get("fixture_id"),
        "fixture_scope": data_source.get("fixture_scope"),
        "fixture_source": dict(data_source.get("fixture_source") or {}),
        "fixture_derivation": dict(data_source.get("fixture_derivation") or {}),
        "omitted_optional_families": dict(data_source.get("omitted_optional_families") or {}),
        "research_evidence_limitations": list(data_source.get("research_evidence_limitations") or []),
        "fixture_manifest_source": fixture_manifest_source,
        "fixture_manifest_derivation": fixture_manifest_derivation,
        "fixture_manifest_scope": fixture_manifest_scope,
        "fixture_manifest_omitted_optional_families": fixture_manifest_omitted_optional_families,
        "fixture_manifest_research_evidence_limitations": fixture_manifest_limitations,
        "fixture_source_matches_manifest": fixture_source_matches_manifest,
        "fixture_derivation_matches_manifest": fixture_derivation_matches_manifest,
        "fixture_scope_matches_manifest": fixture_scope_matches_manifest,
        "fixture_omitted_optional_families_matches_manifest": fixture_omitted_optional_families_matches_manifest,
        "fixture_research_evidence_limitations_match_manifest": fixture_research_evidence_limitations_match_manifest,
        "manifest_path": str(manifest_path) if manifest_path else None,
        "manifest_sha256": data_source.get("manifest_sha256"),
        "manifest_sha256_verified": manifest_sha256_verified,
        "fixture_manifest_safe": fixture_manifest_safe,
        "fixture_manifest_fixture_id_matches": fixture_manifest_fixture_id_matches,
        "dataset_path": str(dataset_path) if dataset_path else None,
        "dataset_exists": dataset_exists,
        "validation": validation_payload,
        "lower_timeframe_evidence": lower_timeframe_evidence,
        "evidence_complete": data_source.get("source_type") == "historical_fixture_pack"
        and data_source.get("synthetic") is False
        and bool(data_source.get("fixture_id"))
        and manifest_sha256_verified
        and fixture_manifest_safe
        and fixture_manifest_fixture_id_matches
        and dataset_exists
        and validation_payload.get("valid") is True,
    }


def _source_lower_timeframe_evidence(cycle_manifest: Mapping[str, Any], data_source: Mapping[str, Any]) -> dict[str, Any]:
    raw = cycle_manifest.get("lower_timeframe_evidence")
    if not isinstance(raw, Mapping):
        raw = data_source
    payload = dict(raw or {})
    dataset_path = str(payload.get("lower_timeframe_dataset_path") or "")
    sha256_value = str(payload.get("lower_timeframe_dataset_sha256") or "")
    row_count = int(payload.get("lower_timeframe_row_count") or 0)
    family_present = bool(payload.get("lower_timeframe_family_present", False))
    path_exists = bool(dataset_path) and Path(dataset_path).exists()
    sha256_verified = bool(sha256_value) and path_exists and _file_sha256(Path(dataset_path)) == sha256_value
    return {
        "family_present": family_present,
        "path": dataset_path or None,
        "sha256": sha256_value or None,
        "row_count": row_count if row_count > 0 else None,
        "path_exists": path_exists,
        "sha256_verified": sha256_verified,
        "family": dict(payload.get("lower_timeframe_family") or {}),
        "evidence_complete": bool(family_present and path_exists and sha256_verified and row_count > 0),
    }


def _evidence_summary(evidence_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "artifact_count": int(len(evidence_rows)),
        "total_size_bytes": int(sum(int(row.get("size_bytes", 0)) for row in evidence_rows)),
        "artifact_names": sorted(str(row.get("artifact_name")) for row in evidence_rows),
        "sha256_by_artifact": {
            str(row.get("artifact_name")): str(row.get("sha256"))
            for row in evidence_rows
        },
    }


def _evidence_row(name: str, path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"required evidence file missing: {path}")
    if path.suffix.lower() == ".json":
        _reject_live_adjacent_json(path)
    return {
        "artifact_name": name,
        "path": str(path),
        "sha256": _file_sha256(path),
        "size_bytes": int(path.stat().st_size),
    }


def _reject_live_adjacent_json(path: Path) -> None:
    payload = _read_json(path)
    if any(field in payload for field in LIVE_ADJACENT_VERSION_FIELDS):
        raise ValueError(f"live-adjacent evidence artifact forbidden: {path}")
    if "research_only" in payload and payload.get("research_only") is not True:
        raise ValueError(f"non-research evidence artifact forbidden: {path}")
    if "observe_only" in payload and payload.get("observe_only") is not True:
        raise ValueError(f"non-observe evidence artifact forbidden: {path}")
    if payload.get("promotion_ready") is True:
        raise ValueError(f"promotion-ready evidence artifact forbidden: {path}")
    for field in (
        "live_signal_input",
        "position_sizing_input",
        "operator_control_input",
        "live_execution_input",
        "runtime_control_input",
        "live_fetch_used",
        "order_placement_used",
    ):
        if field in payload and payload.get(field) is not False:
            raise ValueError(f"live-adjacent evidence artifact forbidden: {path}")


def _required_outputs(cycle_manifest: Mapping[str, Any]) -> dict[str, Path]:
    raw = cycle_manifest.get("required_outputs")
    if not isinstance(raw, Mapping):
        raise ValueError("cycle manifest required_outputs is missing")
    return {str(key): Path(str(value)) for key, value in raw.items()}


def _ranking_digest(row: Mapping[str, Any]) -> dict[str, Any]:
    fields = (
        "candidate_id",
        "strategy_id",
        "feature_set_id",
        "holding_window",
        "trade_count",
        "costed_expectancy",
        "net_return_after_fees_slippage_funding",
        "split_consistency",
        "cost_stress_survival",
        "optimizer_final_score",
        "decision",
    )
    return {field: row.get(field) for field in fields if field in row}


def _safe_name(value: str) -> str:
    safe = "".join(char.lower() if char.isalnum() else "-" for char in value).strip("-")
    return "-".join(part for part in safe.split("-") if part) or "candidate"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _optional_float(value: Any) -> float | None:
    try:
        if pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str, allow_nan=False) + "\n", encoding="utf-8")


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
