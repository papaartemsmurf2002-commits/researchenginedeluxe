from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Any, Iterable

from tradingbotsuite.optimization.candidate import CandidateResult


@dataclass(frozen=True, slots=True)
class StabilityRegion:
    center_candidate_id: str
    member_candidate_ids: tuple[str, ...]
    region_median_score: float
    region_lower_quantile_score: float
    region_score_std: float
    region_pass_rate: float
    connected_region_size: int
    region_best_to_median_gap: float
    split_stability: float
    side_balance: float
    regime_coverage: float
    cost_stress_survival: float
    missingness_rate: float
    concentration_penalty: float
    stability_score: float
    decision: str
    stability_validation_scope: str
    validation_enriched: bool
    split_evaluation_count: int
    cost_stress_evaluation_count: int
    validated_member_count: int
    aggregate_only_member_count: int

    def to_payload(self) -> dict[str, Any]:
        return {
            "center_candidate_id": self.center_candidate_id,
            "member_candidate_ids": list(self.member_candidate_ids),
            "region_median_score": self.region_median_score,
            "region_lower_quantile_score": self.region_lower_quantile_score,
            "region_score_std": self.region_score_std,
            "region_pass_rate": self.region_pass_rate,
            "connected_region_size": self.connected_region_size,
            "region_best_to_median_gap": self.region_best_to_median_gap,
            "split_stability": self.split_stability,
            "side_balance": self.side_balance,
            "regime_coverage": self.regime_coverage,
            "cost_stress_survival": self.cost_stress_survival,
            "missingness_rate": self.missingness_rate,
            "concentration_penalty": self.concentration_penalty,
            "stability_score": self.stability_score,
            "decision": self.decision,
            "stability_validation_scope": self.stability_validation_scope,
            "validation_enriched": self.validation_enriched,
            "split_evaluation_count": self.split_evaluation_count,
            "cost_stress_evaluation_count": self.cost_stress_evaluation_count,
            "validated_member_count": self.validated_member_count,
            "aggregate_only_member_count": self.aggregate_only_member_count,
        }


def rank_by_stability(
    results: Iterable[CandidateResult],
    *,
    pass_score: float = 0.0,
    min_region_size: int = 2,
    require_validation_evidence: bool = False,
) -> list[StabilityRegion]:
    items = _unique_results(results)
    regions = [
        stability_region_for(
            result,
            items,
            pass_score=pass_score,
            min_region_size=min_region_size,
            require_validation_evidence=require_validation_evidence,
        )
        for result in items
    ]
    return sorted(regions, key=lambda region: (region.stability_score, region.connected_region_size), reverse=True)


def stability_region_for(
    center: CandidateResult,
    all_results: Iterable[CandidateResult],
    *,
    pass_score: float = 0.0,
    min_region_size: int = 2,
    require_validation_evidence: bool = False,
) -> StabilityRegion:
    members = _unique_results(
        result
        for result in all_results
        if _same_stability_family(center, result)
        and _normalized_distance(center, result) <= 0.25
    )
    scores = sorted(result.final_score for result in members)
    if not scores:
        scores = [center.final_score]
        members = [center]
    lower = _quantile(scores, 0.25)
    med = median(scores)
    best = max(scores)
    std = _std(scores)
    pass_rate = sum(score >= pass_score for score in scores) / len(scores)
    connected_size = len(members)
    gap = best - med
    split_stability = sum(result.split_consistency for result in members) / connected_size
    side_balance = sum(result.side_balance for result in members) / connected_size
    regime_coverage = sum(result.regime_coverage for result in members) / connected_size
    cost_stress = sum(result.cost_stress_survival for result in members) / connected_size
    missingness = sum(result.missingness_rate for result in members) / connected_size
    concentration = 1.0 / max(connected_size, 1)
    center_split_count = _metadata_count(center, "split_evaluation_count")
    center_cost_count = _metadata_count(center, "cost_stress_evaluation_count")
    center_validation_enriched = center_split_count > 0 and center_cost_count > 0
    validated_member_count = sum(
        _metadata_count(result, "split_evaluation_count") > 0
        and _metadata_count(result, "cost_stress_evaluation_count") > 0
        for result in members
    )
    aggregate_only_member_count = connected_size - validated_member_count
    validation_enriched = center_validation_enriched and aggregate_only_member_count == 0
    stability_score = (
        0.30 * lower
        + 0.20 * pass_rate
        + 0.15 * split_stability
        + 0.10 * side_balance
        + 0.10 * regime_coverage
        + 0.10 * cost_stress
        + 0.05 * min(1.0, connected_size / 10.0)
        - 0.20 * max(0.0, gap)
        - 0.20 * concentration
        - 0.10 * missingness
    )
    if require_validation_evidence and not validation_enriched:
        decision = "rejected_incomplete_validation"
    elif connected_size >= min_region_size and pass_rate >= 0.5 and lower >= pass_score:
        decision = "accepted_region"
    else:
        decision = "rejected_spike_or_unstable_region"
    if validation_enriched:
        validation_scope = "split_cost_stress_enriched"
    elif center_validation_enriched:
        validation_scope = "mixed_validation_neighborhood"
    else:
        validation_scope = "aggregate_only_unvalidated_neighborhood"
    return StabilityRegion(
        center_candidate_id=center.candidate_id,
        member_candidate_ids=tuple(result.candidate_id for result in members),
        region_median_score=float(med),
        region_lower_quantile_score=float(lower),
        region_score_std=float(std),
        region_pass_rate=float(pass_rate),
        connected_region_size=connected_size,
        region_best_to_median_gap=float(gap),
        split_stability=float(split_stability),
        side_balance=float(side_balance),
        regime_coverage=float(regime_coverage),
        cost_stress_survival=float(cost_stress),
        missingness_rate=float(missingness),
        concentration_penalty=float(concentration),
        stability_score=float(stability_score),
        decision=decision,
        stability_validation_scope=validation_scope,
        validation_enriched=bool(validation_enriched),
        split_evaluation_count=center_split_count,
        cost_stress_evaluation_count=center_cost_count,
        validated_member_count=int(validated_member_count),
        aggregate_only_member_count=int(aggregate_only_member_count),
    )


def _normalized_distance(left: CandidateResult, right: CandidateResult) -> float:
    left_params = dict(left.config.parameters)
    right_params = dict(right.config.parameters)
    keys = sorted(set(left_params) | set(right_params))
    if not keys:
        return 0.0
    distances = []
    for key in keys:
        left_value = left_params.get(key)
        right_value = right_params.get(key)
        if isinstance(left_value, (int, float)) and isinstance(right_value, (int, float)):
            scale = max(abs(float(left_value)), abs(float(right_value)), 1.0)
            distances.append(abs(float(left_value) - float(right_value)) / scale)
        else:
            distances.append(0.0 if left_value == right_value else 1.0)
    return sum(distances) / len(distances)


def _same_stability_family(left: CandidateResult, right: CandidateResult) -> bool:
    return (
        left.config.strategy_id == right.config.strategy_id
        and left.config.feature_set_id == right.config.feature_set_id
        and left.config.holding_window == right.config.holding_window
        and left.config.exit_policy_id == right.config.exit_policy_id
        and _normalized_mapping(left.config.exit_policy_params) == _normalized_mapping(right.config.exit_policy_params)
    )


def _normalized_mapping(payload: Any) -> dict[str, Any]:
    return dict(sorted(dict(payload or {}).items()))


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    index = min(len(values) - 1, max(0, int(round((len(values) - 1) * q))))
    return float(values[index])


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return float((sum((value - mean) ** 2 for value in values) / len(values)) ** 0.5)


def _metadata_count(result: CandidateResult, key: str) -> int:
    value = result.metadata.get(key, 0)
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _unique_results(results: Iterable[CandidateResult]) -> list[CandidateResult]:
    seen: set[str] = set()
    unique: list[CandidateResult] = []
    for result in results:
        if result.candidate_id in seen:
            continue
        seen.add(result.candidate_id)
        unique.append(result)
    return unique
