from __future__ import annotations

import json
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class CandidateConfig:
    strategy_id: str
    parameters: Mapping[str, Any] = field(default_factory=dict)
    feature_set_id: str = "features_full_context_no_wt"
    holding_window: str = "24h"
    exit_policy_id: str = "fixed_holding_window"
    exit_policy_params: Mapping[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "feature_set_id": self.feature_set_id,
            "holding_window": self.holding_window,
            "exit_policy_id": self.exit_policy_id,
            "exit_policy_params": dict(sorted(dict(self.exit_policy_params).items())),
            "parameters": dict(sorted(dict(self.parameters).items())),
        }

    def cache_key(self) -> str:
        return _stable_hash(self.to_payload())


@dataclass(frozen=True, slots=True)
class CandidateResult:
    config: CandidateConfig
    base_score: float
    risk_score: float = 0.0
    robustness_score: float = 0.0
    penalties: float = 0.0
    trade_count: int = 0
    split_consistency: float = 0.0
    side_balance: float = 0.0
    regime_coverage: float = 0.0
    cost_stress_survival: float = 0.0
    missingness_rate: float = 0.0
    turnover: float = 0.0
    max_drawdown: float = 0.0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def candidate_id(self) -> str:
        return self.config.cache_key()

    @property
    def final_score(self) -> float:
        return float(self.base_score + self.risk_score + self.robustness_score - self.penalties)

    def to_payload(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "config": self.config.to_payload(),
            "base_score": float(self.base_score),
            "risk_score": float(self.risk_score),
            "robustness_score": float(self.robustness_score),
            "penalties": float(self.penalties),
            "final_score": self.final_score,
            "trade_count": int(self.trade_count),
            "split_consistency": float(self.split_consistency),
            "side_balance": float(self.side_balance),
            "regime_coverage": float(self.regime_coverage),
            "cost_stress_survival": float(self.cost_stress_survival),
            "missingness_rate": float(self.missingness_rate),
            "turnover": float(self.turnover),
            "max_drawdown": float(self.max_drawdown),
            "metadata": dict(self.metadata),
        }


def _stable_hash(payload: Any) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False).encode("utf-8")).hexdigest()
