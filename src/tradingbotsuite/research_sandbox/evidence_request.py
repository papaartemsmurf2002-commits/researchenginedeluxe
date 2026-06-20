from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tradingbotsuite.research_sandbox.boundary import sandbox_boundary_metadata
from tradingbotsuite.research_sandbox.fast_backtest import TrialResult
from tradingbotsuite.research_sandbox.identity import digest_payload
from tradingbotsuite.research_sandbox.spec import stable_payload


@dataclass(frozen=True)
class EvidenceRequestDescriptor:
    request_id: str
    source_run_id: str
    source_trial_id: str
    hypothesis_id: str
    family: str
    venue: str
    symbol: str
    reason: str
    requested_validation: str = "strict_research_cycle_request"
    required_evidence: tuple[str, ...] = (
        "provider_archive_manifest",
        "completed_bar_feature_manifest",
        "walk_forward_splits",
        "cost_stress",
        "baseline_comparators",
        "feature_ablation",
        "multiple_testing",
        "validation_floor",
        "candidate_gate_recheck",
    )
    source_metrics: dict[str, Any] = field(default_factory=dict)
    source_trial_context: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {
            **sandbox_boundary_metadata(),
            "artifact_family": "sandbox_evidence_request",
            "request_id": self.request_id,
            "source_run_id": self.source_run_id,
            "source_trial_id": self.source_trial_id,
            "hypothesis_id": self.hypothesis_id,
            "family": self.family,
            "venue": self.venue,
            "symbol": self.symbol,
            "reason": self.reason,
            "requested_validation": self.requested_validation,
            "required_evidence": list(self.required_evidence),
            "source_metrics": self.source_metrics,
            "source_trial_context": stable_payload(self.source_trial_context),
        }


def _source_trial_context(result: TrialResult) -> dict[str, Any]:
    metadata = dict(result.metadata or {})
    market_source = metadata.get("market_source")
    if not isinstance(market_source, dict):
        market_source = {}
    execution_assumption_keys = (
        "entry_price_source",
        "exit_price_source",
        "same_bar_entry_exit_allowed",
        "same_bar_target_stop_policy",
        "round_trip_cost_bps",
        "target_return",
        "stop_return",
        "exit_profile",
        "exit_variant_id",
        "filter_variant_id",
        "filter_variant",
        "sandbox_blueprint_id",
        "sandbox_proxy_signal",
    )
    execution_assumptions = {
        key: metadata[key]
        for key in execution_assumption_keys
        if key in metadata and metadata[key] is not None
    }
    return stable_payload(
        {
            "source_trial_id": result.trial_id,
            "source_run_id": result.run_id,
            "hypothesis_id": result.hypothesis_id,
            "family": result.family,
            "source_id": result.source_id,
            "venue": result.venue,
            "symbol": result.symbol,
            "data_family": result.data_family,
            "signal_column": result.signal_column,
            "side": result.side,
            "holding_period": result.holding_period,
            "exit_profile": result.exit_profile,
            "exit_variant_id": result.exit_variant_id,
            "filter_variant_id": result.filter_variant_id,
            "market_start": result.market_start,
            "market_end": result.market_end,
            "status": result.status,
            "rejection_reasons": list(result.rejection_reasons),
            "venue_descriptor_id": market_source.get("descriptor_id"),
            "market_source": market_source,
            "execution_assumptions": execution_assumptions,
        }
    )


def _request_for_result(result: TrialResult) -> EvidenceRequestDescriptor:
    metrics = {
        "rank": result.rank,
        "score": result.score,
        "trade_count": result.trade_count,
        "active_days": result.active_days,
        "net_return_sum": result.net_return_sum,
        "avg_trade_return": result.avg_trade_return,
        "win_rate": result.win_rate,
        "max_drawdown": result.max_drawdown,
        "holding_period": result.holding_period,
        "status": result.status,
    }
    request_id = digest_payload(
        {
            "source_run_id": result.run_id,
            "source_trial_id": result.trial_id,
            "requested_validation": "strict_research_cycle_request",
        },
        prefix="sbxrequest",
        length=24,
    )
    return EvidenceRequestDescriptor(
        request_id=request_id,
        source_run_id=result.run_id,
        source_trial_id=result.trial_id,
        hypothesis_id=result.hypothesis_id,
        family=result.family,
        venue=result.venue,
        symbol=result.symbol,
        reason="sandbox_screened_positive_after_costs_request_strict_validation",
        source_metrics=metrics,
        source_trial_context=_source_trial_context(result),
    )


def build_evidence_requests(
    results: list[TrialResult],
    *,
    max_requests: int,
    min_score: float = 0.0,
) -> list[EvidenceRequestDescriptor]:
    if max_requests <= 0:
        return []
    requests: list[EvidenceRequestDescriptor] = []
    for result in sorted(results, key=lambda item: item.rank or 10**9):
        if result.status != "screened":
            continue
        if result.score < min_score:
            continue
        requests.append(_request_for_result(result))
        if len(requests) >= max_requests:
            break
    return requests
