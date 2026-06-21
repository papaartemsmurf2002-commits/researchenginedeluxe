from __future__ import annotations

import math
from typing import Any

import pandas as pd

from tradingbotsuite.strategies._helpers import HOLDING_MS, RuleBasedStrategy, RuleSignal, confidence_from_strength, spaced_indices

REQUIRED_PERP_CONTEXT_V2_COLUMNS = (
    "perp_mark_index_basis",
    "perp_premium",
    "perp_premium_z_7d",
    "perp_last_funding_rate",
    "quality_context_missing_count",
    "quality_has_funding_gap",
    "quality_has_oi_gap",
    "quality_has_premium_gap",
    "quality_provider_backed_all_required",
    "quality_latest_window_context_only",
)
FUNDING_INTERVAL_MS = 8 * 60 * 60 * 1000


class PerpBasisConvergenceStrategy(RuleBasedStrategy):
    strategy_id = "perp_basis_convergence_v2"
    strategy_version = "v1"
    allowed_holding_periods = ("4h", "12h", "24h", "72h")
    required_feature_sets = ("features_perp_context_v2",)

    def _signals(self, frame: pd.DataFrame) -> list[RuleSignal]:
        if not _has_required_columns(frame):
            return []

        basis_threshold_bps = _positive_float(self.config.get("basis_vol_threshold", 10.0), default=10.0)
        premium_z_threshold = _positive_float(self.config.get("premium_z_threshold", 1.25), default=1.25)
        min_edge_bps = _positive_float(self.config.get("min_edge_bps", 5.0), default=5.0)
        funding_policy = str(self.config.get("funding_policy", "require_aligned_or_neutral")).strip().lower()
        allowed = spaced_indices(frame, int(self.config.get("spacing_bars", 12)))

        basis_rate = _finite_numeric(frame["perp_mark_index_basis"])
        premium_rate = _finite_numeric(frame["perp_premium"])
        premium_z = _finite_numeric(frame["perp_premium_z_7d"])
        funding_rate = _finite_numeric(frame["perp_last_funding_rate"])
        basis_bps = basis_rate * 10_000.0
        holding_ms = HOLDING_MS[self.holding_period]

        signals: list[RuleSignal] = []
        for index in allowed:
            if not _quality_allows_signal(frame.iloc[index]):
                continue

            basis_value = float(basis_bps.iloc[index])
            premium_value = float(premium_rate.iloc[index])
            premium_z_value = float(premium_z.iloc[index])
            funding_value = float(funding_rate.iloc[index])
            if not all(math.isfinite(value) for value in (basis_value, premium_value, premium_z_value, funding_value)):
                continue
            if abs(basis_value) < basis_threshold_bps or abs(premium_z_value) < premium_z_threshold:
                continue

            if basis_value < 0.0 and premium_value <= 0.0 and premium_z_value < 0.0:
                side = "long"
            elif basis_value > 0.0 and premium_value >= 0.0 and premium_z_value > 0.0:
                side = "short"
            else:
                continue

            edge_bps = _carry_adjusted_edge_bps(
                side=side,
                basis_bps=abs(basis_value),
                funding_rate=funding_value,
                holding_ms=holding_ms,
                min_edge_bps=min_edge_bps,
                funding_policy=funding_policy,
            )
            if edge_bps < min_edge_bps:
                continue

            basis_score = abs(basis_value) / max(basis_threshold_bps, 1e-9)
            premium_score = abs(premium_z_value) / max(premium_z_threshold, 1e-9)
            edge_score = edge_bps / max(min_edge_bps, 1e-9)
            strength = min(1.0, max(basis_score, premium_score, edge_score) / 4.0)
            signals.append(RuleSignal(index, side, strength, confidence_from_strength(strength)))
        return signals


def _has_required_columns(frame: pd.DataFrame) -> bool:
    return set(REQUIRED_PERP_CONTEXT_V2_COLUMNS) <= set(frame.columns)


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


def _carry_adjusted_edge_bps(
    *,
    side: str,
    basis_bps: float,
    funding_rate: float,
    holding_ms: int,
    min_edge_bps: float,
    funding_policy: str,
) -> float:
    side_sign = 1.0 if side == "long" else -1.0
    funding_carry_bps = -side_sign * funding_rate * (float(holding_ms) / float(FUNDING_INTERVAL_MS)) * 10_000.0
    if funding_policy in {"ignore", "no_funding_filter"}:
        funding_carry_bps = 0.0
    elif funding_policy in {"require_aligned_or_neutral", "avoid_adverse"} and funding_carry_bps < -min_edge_bps:
        return 0.0
    elif funding_policy in {"favor_carry", "aligned_only"} and funding_carry_bps < 0.0:
        return 0.0
    elif funding_policy != "carry_adjusted" and funding_policy not in {
        "require_aligned_or_neutral",
        "avoid_adverse",
        "ignore",
        "no_funding_filter",
        "favor_carry",
        "aligned_only",
    }:
        return 0.0
    return float(basis_bps + funding_carry_bps)


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
