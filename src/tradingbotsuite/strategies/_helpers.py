from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np
import pandas as pd

from tradingbotsuite.strategies.parameters import defaults_for_holding_window

HOLDING_MS = {
    "1h": 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
    "12h": 12 * 60 * 60 * 1000,
    "24h": 24 * 60 * 60 * 1000,
    "72h": 72 * 60 * 60 * 1000,
    "7d": 7 * 24 * 60 * 60 * 1000,
}


@dataclass(frozen=True, slots=True)
class RuleSignal:
    row_index: int
    side: str
    strength: float
    confidence: float
    skip_reason: str = ""


class RuleBasedStrategy:
    strategy_id: str
    strategy_version: str = "v1"
    allowed_holding_periods: tuple[str, ...] = ("24h",)
    required_feature_sets: tuple[str, ...] = ("features_full_context_no_wt",)

    def __init__(self, *, config: dict[str, Any] | None = None) -> None:
        raw_config = dict(config or {})
        self.feature_set_id = str(raw_config.get("feature_set_id", self.required_feature_sets[0]))
        self.holding_period = str(raw_config.get("holding_period", self.allowed_holding_periods[0]))
        if self.holding_period not in self.allowed_holding_periods:
            raise ValueError(f"invalid_holding_period:{self.strategy_id}:{self.holding_period}")
        if self.feature_set_id not in self.required_feature_sets:
            raise ValueError(f"invalid_feature_set:{self.strategy_id}:{self.feature_set_id}")
        self.config = {
            **defaults_for_holding_window(self.strategy_id, self.holding_period),
            **raw_config,
            "feature_set_id": self.feature_set_id,
            "holding_period": self.holding_period,
        }

    def prepare(self, train_context: pd.DataFrame | None = None) -> None:
        _ = train_context

    def predict(self, feature_frame: pd.DataFrame) -> pd.DataFrame:
        rows = []
        for signal in self._signals(feature_frame):
            base = feature_frame.iloc[signal.row_index]
            signal_time = int(base.get("feature_time_ms", base.get("bar_time_ms", base.get("signal_bar_time_ms"))))
            symbol = str(base.get("symbol", self.config.get("symbol", "BTCUSDT"))).upper()
            holding_ms = HOLDING_MS[self.holding_period]
            rows.append(
                {
                    "signal_id": f"{self.strategy_id}-{signal_time}-{signal.row_index}",
                    "signal_time_ms": signal_time,
                    "symbol": symbol,
                    "side": signal.side,
                    "strength": float(signal.strength),
                    "confidence": float(signal.confidence),
                    "target_holding_min_ms": min(HOLDING_MS["1h"], holding_ms),
                    "target_holding_max_ms": holding_ms,
                    "entry_policy": str(self.config.get("entry_policy", "next_bar_open")),
                    "exit_policy_id": str(self.config.get("exit_policy_id", f"{self.holding_period}_time_exit")),
                    "target_return": self.config.get("target_return"),
                    "stop_return": self.config.get("stop_return"),
                    "feature_set_id": self.feature_set_id,
                    "model_version": self.strategy_version,
                    "skip_reason": signal.skip_reason,
                    "research_only": True,
                    "strategy_id": self.strategy_id,
                    "strategy_version": self.strategy_version,
                    "signal_bar_close": float(base.get("close", base.get("signal_bar_close", base.get("entry_price", 0.0)))),
                }
            )
        return pd.DataFrame(rows, columns=_signal_columns())

    def explain(self, prediction_frame: pd.DataFrame) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "signal_count": int(len(prediction_frame)),
            "side_counts": prediction_frame["side"].value_counts().to_dict() if "side" in prediction_frame else {},
            "feature_set_id": self.feature_set_id,
        }

    def _signals(self, frame: pd.DataFrame) -> list[RuleSignal]:
        raise NotImplementedError


def _signal_columns() -> list[str]:
    return [
        "signal_id",
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
        "strategy_id",
        "strategy_version",
        "signal_bar_close",
    ]


def numeric(frame: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column not in frame.columns:
        return pd.Series([default] * len(frame), index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(default)


def spaced_indices(frame: pd.DataFrame, spacing: int) -> set[int]:
    spacing = max(int(spacing), 1)
    return {index for index in range(len(frame)) if index % spacing == 0}


def session_allowed_indices(frame: pd.DataFrame, config: Mapping[str, Any]) -> set[int]:
    allowed_hours = _parse_integer_filter(config.get("allowed_hours_utc", "any"), minimum=0, maximum=23)
    allowed_weekdays = _parse_integer_filter(config.get("allowed_weekdays_utc", "any"), minimum=0, maximum=6)
    if allowed_hours == set() or allowed_weekdays == set():
        return set()
    if allowed_hours is None and allowed_weekdays is None:
        return set(range(len(frame)))

    time_column = next(
        (column for column in ("feature_time_ms", "bar_time_ms", "signal_bar_time_ms") if column in frame.columns),
        None,
    )
    if time_column is None:
        return set()
    raw_time = pd.to_numeric(frame[time_column], errors="coerce")
    timestamps = pd.to_datetime(raw_time, unit="ms", utc=True, errors="coerce")
    valid = timestamps.notna()
    if allowed_hours is not None:
        valid &= timestamps.dt.hour.isin(allowed_hours)
    if allowed_weekdays is not None:
        valid &= timestamps.dt.weekday.isin(allowed_weekdays)
    return set(np.flatnonzero(valid.to_numpy()))


def confidence_from_strength(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return float(min(0.99, max(0.01, 0.5 + min(abs(value), 1.0) / 2.0)))


def _parse_integer_filter(raw: Any, *, minimum: int, maximum: int) -> set[int] | None:
    text = str(raw).strip().lower()
    if text in {"", "*", "all", "any", "off"}:
        return None
    values: set[int] = set()
    for item in text.replace("|", ",").replace(";", ",").split(","):
        item = item.strip()
        if not item:
            continue
        try:
            value = int(item)
        except ValueError:
            return set()
        if str(value) != item and not (item.startswith("+") and item[1:] == str(value)):
            return set()
        if value < minimum or value > maximum:
            return set()
        values.add(value)
    return values if values else set()
