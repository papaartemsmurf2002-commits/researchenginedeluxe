from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import pandas as pd

STRATEGY_CONTRACT_VERSION = "strategy-plugin-contract-v1"
ALLOWED_SIGNAL_SIDES = {"long", "short", "flat"}


@dataclass(frozen=True, slots=True)
class StrategyConfig:
    strategy_id: str
    strategy_version: str = "v1"
    enabled: bool = True
    feature_set_id: str = "features_full_context_no_wt"
    holding_period: str = "24h"
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "enabled": bool(self.enabled),
            "feature_set_id": self.feature_set_id,
            "holding_period": self.holding_period,
            "parameters": dict(self.parameters),
            "contract_version": STRATEGY_CONTRACT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class StrategyValidation:
    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...] = ()


class StrategyPlugin(Protocol):
    strategy_id: str
    strategy_version: str
    allowed_holding_periods: tuple[str, ...]
    required_feature_sets: tuple[str, ...]

    def prepare(self, train_context: pd.DataFrame | None = None) -> None: ...

    def predict(self, feature_frame: pd.DataFrame) -> pd.DataFrame: ...

    def explain(self, prediction_frame: pd.DataFrame) -> dict[str, Any]: ...


def required_signal_columns() -> tuple[str, ...]:
    return (
        "signal_time_ms",
        "symbol",
        "side",
        "strength",
        "confidence",
        "target_holding_min_ms",
        "target_holding_max_ms",
        "entry_policy",
        "exit_policy_id",
        "feature_set_id",
        "model_version",
        "skip_reason",
        "research_only",
    )


def validate_signal_frame(frame: pd.DataFrame) -> StrategyValidation:
    errors: list[str] = []
    missing = [column for column in required_signal_columns() if column not in frame.columns]
    if missing:
        errors.append(f"missing_signal_columns:{','.join(missing)}")
    if "side" in frame.columns:
        sides = set(frame["side"].astype(str).str.lower().unique())
        invalid_sides = sorted(sides - ALLOWED_SIGNAL_SIDES)
        if invalid_sides:
            errors.append(f"invalid_signal_sides:{','.join(invalid_sides)}")
    if "research_only" in frame.columns and not frame["research_only"].astype(bool).all():
        errors.append("signals_must_be_research_only")
    if "target_holding_min_ms" in frame.columns and "target_holding_max_ms" in frame.columns:
        min_holding = pd.to_numeric(frame["target_holding_min_ms"], errors="coerce")
        max_holding = pd.to_numeric(frame["target_holding_max_ms"], errors="coerce")
        if (min_holding < 60 * 60 * 1000).any():
            errors.append("target_holding_min_below_one_hour")
        if (max_holding > 7 * 24 * 60 * 60 * 1000).any():
            errors.append("target_holding_max_above_one_week")
        if (min_holding > max_holding).any():
            errors.append("target_holding_min_exceeds_max")
    return StrategyValidation(valid=not errors, errors=tuple(errors))


def load_strategy_config(path: Path) -> StrategyConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return StrategyConfig(
        strategy_id=str(payload["strategy_id"]),
        strategy_version=str(payload.get("strategy_version", "v1")),
        enabled=bool(payload.get("enabled", True)),
        feature_set_id=str(payload.get("feature_set_id", "features_full_context_no_wt")),
        holding_period=str(payload.get("holding_period", "24h")),
        parameters=dict(payload.get("parameters", {})),
    )
