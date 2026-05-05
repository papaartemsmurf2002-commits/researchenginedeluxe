from __future__ import annotations

import math
from typing import Any

import pandas as pd

from tradingbotsuite.strategies._helpers import HOLDING_MS, RuleBasedStrategy, RuleSignal, confidence_from_strength, spaced_indices

REQUIRED_FUNDING_CROWDING_FADE_COLUMNS = (
    "perp_last_funding_rate",
    "perp_funding_z_7d",
    "perp_funding_momentum",
    "perp_mark_index_basis",
    "perp_premium",
    "oi_delta_z_7d",
    "quality_context_missing_count",
    "quality_has_funding_gap",
    "quality_has_oi_gap",
    "quality_has_premium_gap",
    "quality_provider_backed_all_required",
    "quality_latest_window_context_only",
)
FUNDING_INTERVAL_MS = 8 * 60 * 60 * 1000


class FundingCrowdingFadeStrategy(RuleBasedStrategy):
    strategy_id = "funding_crowding_fade_v2"
    strategy_version = "v1"
    allowed_holding_periods = ("4h", "12h", "24h", "72h")
    required_feature_sets = ("features_perp_context_v2",)

    def _signals(self, frame: pd.DataFrame) -> list[RuleSignal]:
        if not _has_required_columns(frame):
            return []

        funding_z_threshold = _positive_float(self.config.get("funding_z_threshold", 1.25), default=1.25)
        funding_abs_bps_threshold = _positive_float(self.config.get("funding_rate_abs_bps_threshold", 0.4), default=0.4)
        premium_confirmation_bps = _positive_float(self.config.get("premium_confirmation_bps", 2.5), default=2.5)
        min_edge_bps = _positive_float(self.config.get("min_edge_bps", 1.0), default=1.0)
        oi_confirmation_z_min = _non_negative_float(self.config.get("oi_confirmation_z_min", 0.25), default=0.25)
        momentum_policy = str(self.config.get("funding_momentum_policy", "against_fade_filter")).strip().lower()
        allowed = spaced_indices(frame, int(self.config.get("spacing_bars", 12)))
        holding_ms = HOLDING_MS[self.holding_period]

        funding_rate = _finite_numeric(frame["perp_last_funding_rate"])
        funding_z = _finite_numeric(frame["perp_funding_z_7d"])
        funding_momentum = _finite_numeric(frame["perp_funding_momentum"])
        basis_bps = _finite_numeric(frame["perp_mark_index_basis"]) * 10_000.0
        premium_bps = _finite_numeric(frame["perp_premium"]) * 10_000.0
        oi_z = _finite_numeric(frame["oi_delta_z_7d"])
        flow_z = _finite_numeric(frame["flow_signed_taker_z_7d"]) if "flow_signed_taker_z_7d" in frame.columns else None

        signals: list[RuleSignal] = []
        for index in allowed:
            if not _quality_allows_signal(frame.iloc[index]):
                continue

            values = {
                "funding_rate": float(funding_rate.iloc[index]),
                "funding_z": float(funding_z.iloc[index]),
                "funding_momentum": float(funding_momentum.iloc[index]),
                "basis_bps": float(basis_bps.iloc[index]),
                "premium_bps": float(premium_bps.iloc[index]),
                "oi_z": float(oi_z.iloc[index]),
                "flow_z": None if flow_z is None else float(flow_z.iloc[index]),
            }
            if not _required_values_finite(values):
                continue
            funding_bps = values["funding_rate"] * 10_000.0
            crowding_bps = _confirming_premium_bps(values["basis_bps"], values["premium_bps"])

            if (
                funding_bps >= funding_abs_bps_threshold
                and values["funding_z"] >= funding_z_threshold
                and crowding_bps >= premium_confirmation_bps
            ):
                side = "short"
                crowding_sign = 1.0
            elif (
                funding_bps <= -funding_abs_bps_threshold
                and values["funding_z"] <= -funding_z_threshold
                and crowding_bps <= -premium_confirmation_bps
            ):
                side = "long"
                crowding_sign = -1.0
            else:
                continue

            if values["oi_z"] < oi_confirmation_z_min:
                continue
            if not _momentum_allows_fade(
                policy=momentum_policy,
                funding_momentum=values["funding_momentum"],
                crowding_sign=crowding_sign,
            ):
                continue

            edge_bps = abs(funding_bps) * (float(holding_ms) / float(FUNDING_INTERVAL_MS))
            if edge_bps < min_edge_bps:
                continue

            funding_score = abs(values["funding_z"]) / max(funding_z_threshold, 1e-9)
            premium_score = abs(crowding_bps) / max(premium_confirmation_bps, 1e-9)
            oi_score = max(values["oi_z"], 0.0) / max(oi_confirmation_z_min, 1e-9)
            edge_score = edge_bps / max(min_edge_bps, 1e-9)
            flow_score = 0.0
            if values["flow_z"] is not None and math.isfinite(values["flow_z"]):
                flow_score = max(crowding_sign * values["flow_z"], 0.0) / 2.0
            strength = min(1.0, max(funding_score, premium_score, oi_score, edge_score, flow_score) / 4.0)
            signals.append(RuleSignal(index, side, strength, confidence_from_strength(strength)))
        return signals


def _has_required_columns(frame: pd.DataFrame) -> bool:
    return set(REQUIRED_FUNDING_CROWDING_FADE_COLUMNS) <= set(frame.columns)


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


def _momentum_allows_fade(*, policy: str, funding_momentum: float, crowding_sign: float) -> bool:
    if policy in {"ignore", "allow"}:
        return True
    if policy == "require_reversal":
        return funding_momentum * crowding_sign < 0.0
    if policy in {"against_fade_filter", "avoid_acceleration"}:
        return funding_momentum * crowding_sign <= 0.0
    return False


def _required_values_finite(values: dict[str, float | None]) -> bool:
    for key in ("funding_rate", "funding_z", "funding_momentum", "basis_bps", "premium_bps", "oi_z"):
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
