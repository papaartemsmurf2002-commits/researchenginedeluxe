from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

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
        self.config = dict(config or {})
        self.feature_set_id = str(self.config.get("feature_set_id", self.required_feature_sets[0]))
        self.holding_period = str(self.config.get("holding_period", self.allowed_holding_periods[0]))

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


def confidence_from_strength(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return float(min(0.99, max(0.01, 0.5 + min(abs(value), 1.0) / 2.0)))
