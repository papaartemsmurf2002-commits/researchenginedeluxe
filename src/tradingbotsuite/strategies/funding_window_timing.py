from __future__ import annotations

import math
from typing import Any

import pandas as pd

from tradingbotsuite.strategies._helpers import RuleBasedStrategy, RuleSignal, confidence_from_strength, spaced_indices

REQUIRED_FUNDING_WINDOW_TIMING_COLUMNS = (
    "perp_last_funding_rate",
    "perp_funding_z_7d",
    "perp_funding_momentum",
    "cal_time_since_last_funding_h",
    "cal_time_to_next_funding_h",
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


class FundingWindowTimingStrategy(RuleBasedStrategy):
    strategy_id = "funding_window_timing_v1"
    strategy_version = "v1"
    allowed_holding_periods = ("4h", "12h", "24h", "72h")
    required_feature_sets = ("features_perp_context_v2",)

    def _signals(self, frame: pd.DataFrame) -> list[RuleSignal]:
        if not _has_required_columns(frame):
            return []

        funding_z_threshold = _positive_float_or_none(self.config.get("funding_z_threshold", 1.0))
        funding_abs_bps_threshold = _positive_float_or_none(self.config.get("funding_rate_abs_bps_threshold", 0.4))
        premium_confirmation_bps = _positive_float_or_none(self.config.get("premium_confirmation_bps", 2.5))
        entry_window_h = _positive_float_or_none(self.config.get("entry_window_h", 1.0))
        window_mode = str(self.config.get("window_mode", "pre_funding")).strip().lower()
        momentum_policy = str(self.config.get("funding_momentum_policy", "avoid_acceleration")).strip().lower()
        oi_confirmation_z_min = _non_negative_float_or_none(self.config.get("oi_confirmation_z_min", 0.0))
        spacing_bars = _positive_int_or_none(self.config.get("spacing_bars", 4))
        if (
            funding_z_threshold is None
            or funding_abs_bps_threshold is None
            or premium_confirmation_bps is None
            or entry_window_h is None
            or oi_confirmation_z_min is None
            or spacing_bars is None
        ):
            return []
        allowed = spaced_indices(frame, spacing_bars)

        funding_rate = _finite_numeric(frame["perp_last_funding_rate"])
        funding_z = _finite_numeric(frame["perp_funding_z_7d"])
        funding_momentum = _finite_numeric(frame["perp_funding_momentum"])
        since_last_h = _finite_numeric(frame["cal_time_since_last_funding_h"])
        to_next_h = _finite_numeric(frame["cal_time_to_next_funding_h"])
        basis_bps = _finite_numeric(frame["perp_mark_index_basis"]) * 10_000.0
        premium_bps = _finite_numeric(frame["perp_premium"]) * 10_000.0
        oi_z = _finite_numeric(frame["oi_delta_z_7d"])

        signals: list[RuleSignal] = []
        for index in allowed:
            if not _quality_allows_signal(frame.iloc[index]):
                continue

            values = {
                "funding_rate": float(funding_rate.iloc[index]),
                "funding_z": float(funding_z.iloc[index]),
                "funding_momentum": float(funding_momentum.iloc[index]),
                "since_last_h": float(since_last_h.iloc[index]),
                "to_next_h": float(to_next_h.iloc[index]),
                "basis_bps": float(basis_bps.iloc[index]),
                "premium_bps": float(premium_bps.iloc[index]),
                "oi_z": float(oi_z.iloc[index]),
            }
            if not _required_values_finite(values):
                continue

            timing_score = _timing_score(
                window_mode=window_mode,
                to_next_h=values["to_next_h"],
                since_last_h=values["since_last_h"],
                entry_window_h=entry_window_h,
            )
            if timing_score <= 0.0:
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
            if not _momentum_allows_timing(
                policy=momentum_policy,
                funding_momentum=values["funding_momentum"],
                crowding_sign=crowding_sign,
            ):
                continue

            funding_score = abs(values["funding_z"]) / max(funding_z_threshold, 1e-9)
            rate_score = abs(funding_bps) / max(funding_abs_bps_threshold, 1e-9)
            premium_score = abs(crowding_bps) / max(premium_confirmation_bps, 1e-9)
            oi_score = 0.0 if oi_confirmation_z_min <= 0.0 else max(values["oi_z"], 0.0) / max(oi_confirmation_z_min, 1e-9)
            strength = min(1.0, max(funding_score, rate_score, premium_score, timing_score, oi_score) / 4.0)
            signals.append(RuleSignal(index, side, strength, confidence_from_strength(strength)))
        return signals


def _has_required_columns(frame: pd.DataFrame) -> bool:
    return set(REQUIRED_FUNDING_WINDOW_TIMING_COLUMNS) <= set(frame.columns)


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
        and float(checks["quality_latest_window_context_only"]) == 0.0
    )


def _confirming_premium_bps(basis_bps: float, premium_bps: float) -> float:
    if abs(basis_bps) >= abs(premium_bps):
        return basis_bps
    return premium_bps


def _timing_score(*, window_mode: str, to_next_h: float, since_last_h: float, entry_window_h: float) -> float:
    pre_score = 0.0
    post_score = 0.0
    if 0.0 < to_next_h <= entry_window_h:
        pre_score = (entry_window_h - to_next_h + 0.25) / max(entry_window_h, 1e-9)
    if 0.0 < since_last_h <= entry_window_h:
        post_score = (entry_window_h - since_last_h + 0.25) / max(entry_window_h, 1e-9)
    if window_mode in {"pre_funding", "pre"}:
        return max(pre_score, 0.0)
    if window_mode in {"post_funding", "post"}:
        return max(post_score, 0.0)
    if window_mode in {"both", "pre_or_post"}:
        return max(pre_score, post_score, 0.0)
    return 0.0


def _momentum_allows_timing(*, policy: str, funding_momentum: float, crowding_sign: float) -> bool:
    if policy == "ignore":
        return True
    if policy == "require_reversal":
        return funding_momentum * crowding_sign < 0.0
    if policy == "avoid_acceleration":
        return funding_momentum * crowding_sign <= 0.0
    return False


def _required_values_finite(values: dict[str, float]) -> bool:
    return all(math.isfinite(float(value)) for value in values.values())


def _finite_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


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


def _non_negative_float_or_none(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed) or parsed < 0.0:
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
