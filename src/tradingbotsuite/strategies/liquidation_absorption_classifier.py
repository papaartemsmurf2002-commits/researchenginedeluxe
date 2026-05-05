from __future__ import annotations

import math
from typing import Any

import pandas as pd

from tradingbotsuite.strategies._helpers import RuleBasedStrategy, RuleSignal, confidence_from_strength, spaced_indices

REQUIRED_LIQUIDATION_ABSORPTION_COLUMNS = (
    "liq_event_count_1h",
    "liq_total_notional_1h",
    "liq_total_notional_z_7d",
    "liq_imbalance_ratio_1h",
    "liq_time_since_last_event_h",
    "liq_absorption_reclaim_bps",
    "quality_has_liquidation_gap",
    "quality_liquidation_provider_backed",
    "quality_liquidation_latest_window_context_only",
)


class LiquidationAbsorptionClassifierStrategy(RuleBasedStrategy):
    strategy_id = "liquidation_absorption_classifier_v1"
    strategy_version = "v1"
    allowed_holding_periods = ("1h", "4h", "12h", "24h")
    required_feature_sets = ("features_liquidation_context_v1",)

    def _signals(self, frame: pd.DataFrame) -> list[RuleSignal]:
        if not _has_required_columns(frame):
            return []

        notional_z_threshold = _positive_float_or_none(self.config.get("notional_z_threshold", 1.25))
        imbalance_abs_threshold = _bounded_positive_float_or_none(
            self.config.get("imbalance_abs_threshold", 0.65),
            maximum=1.0,
        )
        reclaim_bps_threshold = _positive_float_or_none(self.config.get("reclaim_bps_threshold", 15.0))
        min_event_count = _positive_float_or_none(self.config.get("min_event_count", 3.0))
        max_event_age_h = _positive_float_or_none(self.config.get("max_event_age_h", 1.0))
        spacing_bars = _positive_int_or_none(self.config.get("spacing_bars", 4))
        allow_latest_window_context = _bool_param(self.config.get("allow_latest_window_context", False))
        if (
            notional_z_threshold is None
            or imbalance_abs_threshold is None
            or reclaim_bps_threshold is None
            or min_event_count is None
            or max_event_age_h is None
            or spacing_bars is None
            or allow_latest_window_context is None
        ):
            return []

        event_count = _finite_numeric(frame["liq_event_count_1h"])
        total_notional = _finite_numeric(frame["liq_total_notional_1h"])
        notional_z = _finite_numeric(frame["liq_total_notional_z_7d"])
        imbalance = _finite_numeric(frame["liq_imbalance_ratio_1h"])
        event_age_h = _finite_numeric(frame["liq_time_since_last_event_h"])
        reclaim_bps = _finite_numeric(frame["liq_absorption_reclaim_bps"])

        signals: list[RuleSignal] = []
        for index in spaced_indices(frame, spacing_bars):
            if not _quality_allows_signal(
                frame.iloc[index],
                allow_latest_window_context=allow_latest_window_context,
            ):
                continue
            values = {
                "event_count": float(event_count.iloc[index]),
                "total_notional": float(total_notional.iloc[index]),
                "notional_z": float(notional_z.iloc[index]),
                "imbalance": float(imbalance.iloc[index]),
                "event_age_h": float(event_age_h.iloc[index]),
                "reclaim_bps": float(reclaim_bps.iloc[index]),
            }
            if not _required_values_finite(values):
                continue
            if values["event_count"] < min_event_count:
                continue
            if values["total_notional"] <= 0.0:
                continue
            if values["notional_z"] < notional_z_threshold:
                continue
            if abs(values["imbalance"]) < imbalance_abs_threshold:
                continue
            if values["event_age_h"] > max_event_age_h:
                continue
            if values["reclaim_bps"] < reclaim_bps_threshold:
                continue

            side = "long" if values["imbalance"] < 0.0 else "short"
            z_score = values["notional_z"] / max(notional_z_threshold, 1e-9)
            imbalance_score = abs(values["imbalance"]) / max(imbalance_abs_threshold, 1e-9)
            reclaim_score = values["reclaim_bps"] / max(reclaim_bps_threshold, 1e-9)
            event_score = values["event_count"] / max(min_event_count, 1e-9)
            recency_score = max(0.0, (max_event_age_h - values["event_age_h"]) / max(max_event_age_h, 1e-9))
            strength = min(1.0, max(z_score, imbalance_score, reclaim_score, event_score, recency_score) / 4.0)
            signals.append(RuleSignal(index, side, strength, confidence_from_strength(strength)))
        return signals


def _has_required_columns(frame: pd.DataFrame) -> bool:
    return set(REQUIRED_LIQUIDATION_ABSORPTION_COLUMNS) <= set(frame.columns)


def _quality_allows_signal(row: pd.Series, *, allow_latest_window_context: bool) -> bool:
    checks: dict[str, Any] = {
        "quality_has_liquidation_gap": row.get("quality_has_liquidation_gap"),
        "quality_liquidation_provider_backed": row.get("quality_liquidation_provider_backed"),
        "quality_liquidation_latest_window_context_only": row.get("quality_liquidation_latest_window_context_only"),
    }
    if not all(_finite_scalar(value) for value in checks.values()):
        return False
    if float(checks["quality_has_liquidation_gap"]) != 0.0:
        return False
    if float(checks["quality_liquidation_provider_backed"]) != 1.0:
        return False
    if not allow_latest_window_context and float(checks["quality_liquidation_latest_window_context_only"]) != 0.0:
        return False
    return True


def _required_values_finite(values: dict[str, float]) -> bool:
    return all(math.isfinite(float(value)) for value in values.values())


def _finite_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").replace([math.inf, -math.inf], math.nan)


def _finite_scalar(value: Any) -> bool:
    if value is None or pd.isna(value):
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _positive_float_or_none(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed) or parsed <= 0.0:
        return None
    return parsed


def _bounded_positive_float_or_none(value: Any, *, maximum: float) -> float | None:
    parsed = _positive_float_or_none(value)
    if parsed is None or parsed > maximum:
        return None
    return parsed


def _positive_int_or_none(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if parsed <= 0:
        return None
    return parsed


def _bool_param(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    return None
