from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import pandas as pd

from tradingbotsuite.strategies._helpers import HOLDING_MS, RuleBasedStrategy, RuleSignal, confidence_from_strength, spaced_indices

REQUIRED_HMM_ROUTED_ALPHA_COLUMNS = (
    "top_regime_label",
    "max_regime_probability",
    "posterior_entropy",
    "recent_regime_flip",
    "regime_no_trade",
    "hmm_fit_end_row",
    "source_row_index",
    "perp_mark_index_basis",
    "perp_premium",
    "perp_premium_z_7d",
    "perp_premium_slope_8h",
    "perp_last_funding_rate",
    "perp_funding_z_7d",
    "oi_delta_1h",
    "oi_delta_z_7d",
    "quality_context_missing_count",
    "quality_has_funding_gap",
    "quality_has_oi_gap",
    "quality_has_premium_gap",
    "quality_provider_backed_all_required",
    "quality_latest_window_context_only",
)
FUNDING_INTERVAL_MS = 8 * 60 * 60 * 1000


@dataclass(frozen=True, slots=True)
class _RouterParams:
    posterior_threshold: float
    entropy_threshold: float
    basis_bps_threshold: float
    premium_z_threshold: float
    funding_z_threshold: float
    oi_delta_z_threshold: float
    oi_delta_min_notional: float
    premium_slope_min_bps: float
    flow_alignment_z_min: float
    min_edge_bps: float
    spacing_bars: int


class HmmRoutedAlphaSleevesStrategy(RuleBasedStrategy):
    strategy_id = "hmm_routed_alpha_sleeves_v2"
    strategy_version = "v1"
    allowed_holding_periods = ("4h", "12h", "24h", "72h")
    required_feature_sets = ("features_perp_context_v2",)

    def _signals(self, frame: pd.DataFrame) -> list[RuleSignal]:
        if not _has_required_columns(frame):
            return []
        params = _params_from_config(self.config)
        if params is None:
            return []

        signals: list[RuleSignal] = []
        allowed = spaced_indices(frame, params.spacing_bars)
        for index in allowed:
            row = frame.iloc[index]
            routing = _routing_context(row, params)
            if routing is None:
                continue
            routed = _route_regime_sleeve(
                row,
                params=params,
                holding_ms=HOLDING_MS[self.holding_period],
                regime_bucket=routing["regime_bucket"],
                posterior_probability=routing["posterior_probability"],
            )
            if routed is None:
                continue
            side, strength, sleeve = routed
            signals.append(RuleSignal(index, side, strength, confidence_from_strength(strength), skip_reason=sleeve))
        return signals


def _has_required_columns(frame: pd.DataFrame) -> bool:
    return set(REQUIRED_HMM_ROUTED_ALPHA_COLUMNS) <= set(frame.columns)


def _params_from_config(config: dict[str, Any]) -> _RouterParams | None:
    posterior_threshold = _config_float(config, "posterior_threshold", 0.60, positive=True)
    entropy_threshold = _config_float(config, "entropy_threshold", 0.78, positive=True)
    basis_bps_threshold = _config_float(config, "basis_bps_threshold", 6.0, positive=True)
    premium_z_threshold = _config_float(config, "premium_z_threshold", 1.0, positive=True)
    funding_z_threshold = _config_float(config, "funding_z_threshold", 1.0, positive=True)
    oi_delta_z_threshold = _config_float(config, "oi_delta_z_threshold", 0.75, positive=True)
    oi_delta_min_notional = _config_float(config, "oi_delta_min_notional", 0.0, non_negative=True)
    premium_slope_min_bps = _config_float(config, "premium_slope_min_bps", 0.0, non_negative=True)
    flow_alignment_z_min = _config_float(config, "flow_alignment_z_min", 0.0, non_negative=True)
    min_edge_bps = _config_float(config, "min_edge_bps", 1.0, positive=True)
    spacing_bars = _config_int(config, "spacing_bars", 12, positive=True)
    values: tuple[float | int | None, ...] = (
        posterior_threshold,
        entropy_threshold,
        basis_bps_threshold,
        premium_z_threshold,
        funding_z_threshold,
        oi_delta_z_threshold,
        oi_delta_min_notional,
        premium_slope_min_bps,
        flow_alignment_z_min,
        min_edge_bps,
        spacing_bars,
    )
    if any(value is None for value in values):
        return None
    if posterior_threshold is None or posterior_threshold > 1.0:
        return None
    if entropy_threshold is None or entropy_threshold > 1.0:
        return None
    return _RouterParams(
        posterior_threshold=float(posterior_threshold),
        entropy_threshold=float(entropy_threshold),
        basis_bps_threshold=float(basis_bps_threshold),
        premium_z_threshold=float(premium_z_threshold),
        funding_z_threshold=float(funding_z_threshold),
        oi_delta_z_threshold=float(oi_delta_z_threshold),
        oi_delta_min_notional=float(oi_delta_min_notional),
        premium_slope_min_bps=float(premium_slope_min_bps),
        flow_alignment_z_min=float(flow_alignment_z_min),
        min_edge_bps=float(min_edge_bps),
        spacing_bars=int(spacing_bars),
    )


def _routing_context(row: pd.Series, params: _RouterParams) -> dict[str, float | str] | None:
    if not _quality_allows_signal(row) or not _split_safe_posterior_row(row):
        return None
    regime_no_trade = _bool_flag(row.get("regime_no_trade"))
    recent_regime_flip = _bool_flag(row.get("recent_regime_flip"))
    if regime_no_trade is None or recent_regime_flip is None:
        return None
    if regime_no_trade or recent_regime_flip:
        return None
    posterior_probability = _finite_float(row.get("max_regime_probability"))
    entropy = _finite_float(row.get("posterior_entropy"))
    if posterior_probability is None or entropy is None:
        return None
    if posterior_probability < params.posterior_threshold or entropy > params.entropy_threshold:
        return None
    regime_bucket = _regime_bucket(row.get("top_regime_label"))
    if regime_bucket not in {"bull", "bear", "range"}:
        return None
    return {"regime_bucket": regime_bucket, "posterior_probability": posterior_probability}


def _route_regime_sleeve(
    row: pd.Series,
    *,
    params: _RouterParams,
    holding_ms: int,
    regime_bucket: str,
    posterior_probability: float,
) -> tuple[str, float, str] | None:
    if regime_bucket in {"bull", "bear"}:
        return _trend_sleeve(row, params=params, regime_bucket=regime_bucket, posterior_probability=posterior_probability)
    if regime_bucket == "range":
        return _range_fade_sleeve(row, params=params, holding_ms=holding_ms, posterior_probability=posterior_probability)
    return None


def _trend_sleeve(
    row: pd.Series,
    *,
    params: _RouterParams,
    regime_bucket: str,
    posterior_probability: float,
) -> tuple[str, float, str] | None:
    oi_delta = _finite_float(row.get("oi_delta_1h"))
    oi_z = _finite_float(row.get("oi_delta_z_7d"))
    premium = _finite_float(row.get("perp_premium"))
    slope_bps = _rate_to_bps(_finite_float(row.get("perp_premium_slope_8h")))
    if None in {oi_delta, oi_z, premium, slope_bps}:
        return None
    if float(oi_delta) < params.oi_delta_min_notional or float(oi_z) < params.oi_delta_z_threshold:
        return None
    if regime_bucket == "bull":
        side = "long"
        side_sign = 1.0
        if float(slope_bps) < params.premium_slope_min_bps or float(premium) < 0.0:
            return None
    else:
        side = "short"
        side_sign = -1.0
        if float(slope_bps) > -params.premium_slope_min_bps or float(premium) > 0.0:
            return None
    flow_z = _finite_float(row.get("flow_signed_taker_z_7d"))
    if params.flow_alignment_z_min > 0.0 and flow_z is None:
        return None
    if flow_z is not None and side_sign * flow_z < params.flow_alignment_z_min:
        return None
    strength = _bounded_strength(
        max(
            posterior_probability,
            float(oi_z) / params.oi_delta_z_threshold,
            abs(float(slope_bps)) / max(params.premium_slope_min_bps, 1e-9) if params.premium_slope_min_bps > 0.0 else 1.0,
        )
        / 3.0
    )
    return side, strength, f"hmm_router_{regime_bucket}_trend_oi_flow"


def _range_fade_sleeve(
    row: pd.Series,
    *,
    params: _RouterParams,
    holding_ms: int,
    posterior_probability: float,
) -> tuple[str, float, str] | None:
    basis_bps = _rate_to_bps(_finite_float(row.get("perp_mark_index_basis")))
    premium_z = _finite_float(row.get("perp_premium_z_7d"))
    funding_z = _finite_float(row.get("perp_funding_z_7d"))
    funding_rate = _finite_float(row.get("perp_last_funding_rate"))
    if None in {basis_bps, premium_z, funding_z, funding_rate}:
        return None

    if float(basis_bps) >= params.basis_bps_threshold and float(premium_z) >= params.premium_z_threshold:
        side = "short"
        crowding_sign = 1.0
    elif float(basis_bps) <= -params.basis_bps_threshold and float(premium_z) <= -params.premium_z_threshold:
        side = "long"
        crowding_sign = -1.0
    elif float(funding_z) >= params.funding_z_threshold and float(premium_z) >= params.premium_z_threshold:
        side = "short"
        crowding_sign = 1.0
    elif float(funding_z) <= -params.funding_z_threshold and float(premium_z) <= -params.premium_z_threshold:
        side = "long"
        crowding_sign = -1.0
    else:
        return None

    edge_bps = abs(float(basis_bps)) + max(crowding_sign * float(funding_rate), 0.0) * (holding_ms / FUNDING_INTERVAL_MS) * 10_000.0
    if edge_bps < params.min_edge_bps:
        return None
    strength = _bounded_strength(
        max(
            posterior_probability,
            abs(float(basis_bps)) / params.basis_bps_threshold,
            abs(float(premium_z)) / params.premium_z_threshold,
            abs(float(funding_z)) / params.funding_z_threshold,
            edge_bps / params.min_edge_bps,
        )
        / 5.0
    )
    return side, strength, "hmm_router_range_basis_funding_fade"


def _quality_allows_signal(row: pd.Series) -> bool:
    checks: dict[str, Any] = {
        "quality_context_missing_count": row.get("quality_context_missing_count"),
        "quality_has_funding_gap": row.get("quality_has_funding_gap"),
        "quality_has_oi_gap": row.get("quality_has_oi_gap"),
        "quality_has_premium_gap": row.get("quality_has_premium_gap"),
        "quality_provider_backed_all_required": row.get("quality_provider_backed_all_required"),
        "quality_latest_window_context_only": row.get("quality_latest_window_context_only"),
    }
    if not all(_finite_float(value) is not None for value in checks.values()):
        return False
    return (
        float(checks["quality_context_missing_count"]) == 0.0
        and float(checks["quality_has_funding_gap"]) == 0.0
        and float(checks["quality_has_oi_gap"]) == 0.0
        and float(checks["quality_has_premium_gap"]) == 0.0
        and float(checks["quality_provider_backed_all_required"]) == 1.0
        and float(checks["quality_latest_window_context_only"]) == 0.0
    )


def _split_safe_posterior_row(row: pd.Series) -> bool:
    fit_end = _integer_marker(row.get("hmm_fit_end_row"))
    source_row = _integer_marker(row.get("source_row_index"))
    return fit_end is not None and source_row is not None and fit_end >= 0 and source_row >= 0 and fit_end < source_row


def _regime_bucket(value: Any) -> str:
    label = str(value or "").strip().lower()
    if not label:
        return "unknown"
    if "shock" in label or "transition" in label or "volatile" in label:
        return "shock"
    if "bull" in label or "uptrend" in label or "up_trend" in label:
        return "bull"
    if "bear" in label or "downtrend" in label or "down_trend" in label:
        return "bear"
    if "range" in label or "chop" in label or "mean_revert" in label:
        return "range"
    return "unknown"


def _bool_flag(value: Any) -> bool | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, bool):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y"}:
            return True
        if normalized in {"0", "false", "no", "n"}:
            return False
        return None
    numeric = _finite_float(value)
    if numeric == 0.0:
        return False
    if numeric == 1.0:
        return True
    return None


def _finite_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if value is None or pd.isna(value):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _config_float(
    config: dict[str, Any],
    key: str,
    default: float,
    *,
    positive: bool = False,
    non_negative: bool = False,
) -> float | None:
    value = _finite_float(config.get(key, default))
    if value is None:
        return None
    if positive and value <= 0.0:
        return None
    if non_negative and value < 0.0:
        return None
    return value


def _config_int(config: dict[str, Any], key: str, default: int, *, positive: bool = False) -> int | None:
    value = _finite_float(config.get(key, default))
    if value is None:
        return None
    integer = int(value)
    if float(integer) != float(value):
        return None
    if positive and integer <= 0:
        return None
    return integer


def _integer_marker(value: Any) -> int | None:
    parsed = _finite_float(value)
    if parsed is None:
        return None
    integer = int(parsed)
    if float(integer) != parsed:
        return None
    return integer


def _rate_to_bps(value: float | None) -> float | None:
    if value is None:
        return None
    return float(value) * 10_000.0


def _bounded_strength(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return float(max(0.01, min(1.0, value)))
