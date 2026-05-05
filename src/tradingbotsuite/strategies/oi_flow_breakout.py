from __future__ import annotations

import math
from typing import Any

import pandas as pd

from tradingbotsuite.strategies._helpers import RuleBasedStrategy, RuleSignal, confidence_from_strength, spaced_indices

REQUIRED_OI_FLOW_BREAKOUT_COLUMNS = (
    "perp_mark_index_basis",
    "perp_premium",
    "perp_premium_slope_8h",
    "oi_notional",
    "oi_delta_1h",
    "oi_delta_z_7d",
    "quality_context_missing_count",
    "quality_has_funding_gap",
    "quality_has_oi_gap",
    "quality_has_premium_gap",
    "quality_provider_backed_all_required",
    "quality_latest_window_context_only",
)


class OiFlowBreakoutStrategy(RuleBasedStrategy):
    strategy_id = "oi_flow_breakout_v2"
    strategy_version = "v1"
    allowed_holding_periods = ("4h", "12h", "24h", "72h")
    required_feature_sets = ("features_perp_context_v2",)

    def _signals(self, frame: pd.DataFrame) -> list[RuleSignal]:
        if not _has_required_columns(frame):
            return []

        oi_delta_z_threshold = _positive_float(self.config.get("oi_delta_z_threshold", 1.0), default=1.0)
        oi_delta_min_notional = _non_negative_float(self.config.get("oi_delta_min_notional", 0.0), default=0.0)
        premium_confirmation_bps = _positive_float(self.config.get("premium_confirmation_bps", 5.0), default=5.0)
        premium_slope_min_bps = _non_negative_float(self.config.get("premium_slope_min_bps", 0.0), default=0.0)
        flow_z_threshold = _positive_float(self.config.get("flow_z_threshold", 0.75), default=0.75)
        flow_policy = str(self.config.get("flow_confirmation_policy", "optional_when_missing")).strip().lower()
        spacing_bars = _positive_int_or_none(self.config.get("spacing_bars", 12))
        if spacing_bars is None:
            return []
        allowed = spaced_indices(frame, spacing_bars)

        basis_bps = _finite_numeric(frame["perp_mark_index_basis"]) * 10_000.0
        premium_bps = _finite_numeric(frame["perp_premium"]) * 10_000.0
        premium_slope_bps = _finite_numeric(frame["perp_premium_slope_8h"]) * 10_000.0
        oi_notional = _finite_numeric(frame["oi_notional"])
        oi_delta = _finite_numeric(frame["oi_delta_1h"])
        oi_z = _finite_numeric(frame["oi_delta_z_7d"])
        flow_z = _finite_numeric(frame["flow_signed_taker_z_7d"]) if "flow_signed_taker_z_7d" in frame.columns else None

        signals: list[RuleSignal] = []
        for index in allowed:
            if not _quality_allows_signal(frame.iloc[index]):
                continue

            values = {
                "basis_bps": float(basis_bps.iloc[index]),
                "premium_bps": float(premium_bps.iloc[index]),
                "premium_slope_bps": float(premium_slope_bps.iloc[index]),
                "oi_notional": float(oi_notional.iloc[index]),
                "oi_delta": float(oi_delta.iloc[index]),
                "oi_z": float(oi_z.iloc[index]),
                "flow_z": None if flow_z is None else float(flow_z.iloc[index]),
            }
            if not _required_values_finite(values):
                continue
            if values["oi_delta"] <= max(oi_delta_min_notional, 0.0):
                continue
            if values["oi_z"] < oi_delta_z_threshold:
                continue

            confirming_bps = _confirming_premium_bps(values["basis_bps"], values["premium_bps"])
            if abs(confirming_bps) < premium_confirmation_bps:
                continue
            if confirming_bps > 0.0:
                side = "long"
                direction_sign = 1.0
            elif confirming_bps < 0.0:
                side = "short"
                direction_sign = -1.0
            else:
                continue

            if not _slope_allows_breakout(
                side=side,
                premium_slope_bps=values["premium_slope_bps"],
                premium_slope_min_bps=premium_slope_min_bps,
            ):
                continue
            if not _flow_allows_breakout(
                policy=flow_policy,
                flow_z=values["flow_z"],
                direction_sign=direction_sign,
                flow_z_threshold=flow_z_threshold,
            ):
                continue

            oi_score = values["oi_z"] / max(oi_delta_z_threshold, 1e-9)
            delta_score = 1.0 if oi_delta_min_notional <= 0.0 else values["oi_delta"] / max(oi_delta_min_notional, 1e-9)
            premium_score = abs(confirming_bps) / max(premium_confirmation_bps, 1e-9)
            slope_score = (
                0.0
                if premium_slope_min_bps <= 0.0
                else abs(values["premium_slope_bps"]) / max(premium_slope_min_bps, 1e-9)
            )
            flow_score = 0.0
            if values["flow_z"] is not None and math.isfinite(values["flow_z"]):
                flow_score = max(direction_sign * values["flow_z"], 0.0) / max(flow_z_threshold, 1e-9)
            strength = min(1.0, max(oi_score, delta_score, premium_score, slope_score, flow_score) / 4.0)
            signals.append(RuleSignal(index, side, strength, confidence_from_strength(strength)))
        return signals


def _has_required_columns(frame: pd.DataFrame) -> bool:
    return set(REQUIRED_OI_FLOW_BREAKOUT_COLUMNS) <= set(frame.columns)


def _quality_allows_signal(row: pd.Series) -> bool:
    checks: dict[str, Any] = {
        "quality_context_missing_count": row.get("quality_context_missing_count"),
        "quality_has_funding_gap": row.get("quality_has_funding_gap"),
        "quality_has_oi_gap": row.get("quality_has_oi_gap"),
        "quality_has_premium_gap": row.get("quality_has_premium_gap"),
        "quality_provider_backed_all_required": row.get("quality_provider_backed_all_required"),
        "quality_latest_window_context_only": row.get("quality_latest_window_context_only"),
    }
    if not all(_finite_scalar(value) for value in checks.values()):
        return False
    return (
        float(checks["quality_context_missing_count"]) == 0.0
        and float(checks["quality_has_funding_gap"]) == 0.0
        and float(checks["quality_has_oi_gap"]) == 0.0
        and float(checks["quality_has_premium_gap"]) == 0.0
        and float(checks["quality_provider_backed_all_required"]) == 1.0
    )


def _confirming_premium_bps(basis_bps: float, premium_bps: float) -> float:
    if abs(basis_bps) >= abs(premium_bps):
        return basis_bps
    return premium_bps


def _slope_allows_breakout(*, side: str, premium_slope_bps: float, premium_slope_min_bps: float) -> bool:
    if premium_slope_min_bps <= 0.0:
        return True
    if side == "long":
        return premium_slope_bps >= premium_slope_min_bps
    if side == "short":
        return premium_slope_bps <= -premium_slope_min_bps
    return False


def _flow_allows_breakout(
    *,
    policy: str,
    flow_z: float | None,
    direction_sign: float,
    flow_z_threshold: float,
) -> bool:
    if policy == "ignore":
        return True
    flow_is_finite = flow_z is not None and math.isfinite(float(flow_z))
    if not flow_is_finite:
        return policy in {"optional_when_missing", "require_when_present"}
    aligned = direction_sign * float(flow_z) >= flow_z_threshold
    if policy in {"optional_when_missing", "require_when_present", "required"}:
        return aligned
    return False


def _required_values_finite(values: dict[str, float | None]) -> bool:
    for key in ("basis_bps", "premium_bps", "premium_slope_bps", "oi_notional", "oi_delta", "oi_z"):
        value = values[key]
        if value is None or not math.isfinite(float(value)):
            return False
    return True


def _finite_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _finite_scalar(value: Any) -> bool:
    if value is None or pd.isna(value):
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _positive_float(value: Any, *, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(parsed) or parsed <= 0.0:
        return default
    return parsed


def _non_negative_float(value: Any, *, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(parsed) or parsed < 0.0:
        return default
    return parsed


def _positive_int_or_none(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if parsed <= 0:
        return None
    return parsed
