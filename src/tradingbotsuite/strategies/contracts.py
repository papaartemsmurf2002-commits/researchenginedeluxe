from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import pandas as pd

from tradingbotsuite.strategies.parameters import allowed_parameter_names

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
        "target_return",
        "stop_return",
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
    for column in ("symbol", "entry_policy", "exit_policy_id", "feature_set_id", "model_version"):
        if column in frame.columns and frame[column].astype(str).str.strip().eq("").any():
            errors.append(f"empty_signal_field:{column}")
    if "signal_time_ms" in frame.columns:
        signal_time = pd.to_numeric(frame["signal_time_ms"], errors="coerce")
        if signal_time.isna().any() or not np.isfinite(signal_time.to_numpy(dtype=float)).all():
            errors.append("signal_time_ms_non_finite")
    for column in ("strength", "confidence"):
        if column in frame.columns:
            values = pd.to_numeric(frame[column], errors="coerce")
            if values.isna().any() or not np.isfinite(values.to_numpy(dtype=float)).all():
                errors.append(f"{column}_non_finite")
            elif ((values < 0.0) | (values > 1.0)).any():
                errors.append(f"{column}_outside_unit_interval")
    if "research_only" in frame.columns:
        values = frame["research_only"]
        strict_true = values.map(lambda value: isinstance(value, (bool, np.bool_)) and bool(value))
        if not strict_true.all():
            errors.append("signals_must_be_research_only")
    if "target_holding_min_ms" in frame.columns and "target_holding_max_ms" in frame.columns:
        min_holding = pd.to_numeric(frame["target_holding_min_ms"], errors="coerce")
        max_holding = pd.to_numeric(frame["target_holding_max_ms"], errors="coerce")
        if min_holding.isna().any() or max_holding.isna().any():
            errors.append("target_holding_ms_non_finite")
        if (min_holding < 60 * 60 * 1000).any():
            errors.append("target_holding_min_below_one_hour")
        if (max_holding > 7 * 24 * 60 * 60 * 1000).any():
            errors.append("target_holding_max_above_one_week")
        if (min_holding > max_holding).any():
            errors.append("target_holding_min_exceeds_max")
    return StrategyValidation(valid=not errors, errors=tuple(errors))


def validate_strategy_config(config: StrategyConfig) -> StrategyValidation:
    errors: list[str] = []
    if not config.strategy_id.strip():
        errors.append("strategy_id_required")
    if not config.strategy_version.strip():
        errors.append("strategy_version_required")
    if not config.feature_set_id.strip():
        errors.append("feature_set_id_required")
    if not config.holding_period.strip():
        errors.append("holding_period_required")
    allowed = allowed_parameter_names(config.strategy_id)
    unknown = sorted(set(config.parameters) - allowed)
    if unknown:
        errors.append(f"unknown_strategy_parameters:{','.join(unknown)}")
    for key, value in config.parameters.items():
        if isinstance(value, bool) or value is None:
            continue
        if isinstance(value, (int, float, np.integer, np.floating)):
            if not np.isfinite(float(value)):
                errors.append(f"non_finite_strategy_parameter:{key}")
    if not errors:
        try:
            from tradingbotsuite.strategies.registry import get_strategy_plugin

            get_strategy_plugin(
                config.strategy_id,
                config={
                    **dict(config.parameters),
                    "feature_set_id": config.feature_set_id,
                    "holding_period": config.holding_period,
                },
            )
        except ValueError as exc:
            errors.append(str(exc))
    return StrategyValidation(valid=not errors, errors=tuple(errors))


def load_strategy_config(path: Path) -> StrategyConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    config = StrategyConfig(
        strategy_id=str(payload["strategy_id"]),
        strategy_version=str(payload.get("strategy_version", "v1")),
        enabled=bool(payload.get("enabled", True)),
        feature_set_id=str(payload.get("feature_set_id", "features_full_context_no_wt")),
        holding_period=str(payload.get("holding_period", "24h")),
        parameters=dict(payload.get("parameters", {})),
    )
    validation = validate_strategy_config(config)
    if not validation.valid:
        raise ValueError("; ".join(validation.errors))
    return config
