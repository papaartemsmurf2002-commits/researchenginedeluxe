from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from tradingbotsuite.core.features import numeric_feature_map


def _clip(value: float, lower: float = -100.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, value))


@dataclass(frozen=True, slots=True)
class RuleAcceptanceSettings:
    core_score_threshold: float
    perp_score_floor: float
    total_score_threshold: float
    slope_minimum: float
    er_minimum: float
    di_spread_minimum: float
    chop_maximum: float
    corridor_width_minimum: float
    basis_soft_bps: float
    basis_hard_bps: float
    premium_soft_rate: float
    funding_adverse_threshold: float
    near_funding_minutes: int
    liquidity_soft_spread_bps: float
    liquidity_hard_spread_bps: float
    signed_support_threshold: float
    book_support_threshold: float


def default_rule_acceptance_settings() -> RuleAcceptanceSettings:
    return RuleAcceptanceSettings(
        core_score_threshold=5.0,
        perp_score_floor=-15.0,
        total_score_threshold=0.0,
        slope_minimum=0.35,
        er_minimum=0.20,
        di_spread_minimum=10.0,
        chop_maximum=55.0,
        corridor_width_minimum=0.005,
        basis_soft_bps=5.0,
        basis_hard_bps=15.0,
        premium_soft_rate=0.0002,
        funding_adverse_threshold=0.0001,
        near_funding_minutes=60,
        liquidity_soft_spread_bps=5.0,
        liquidity_hard_spread_bps=12.0,
        signed_support_threshold=0.05,
        book_support_threshold=0.05,
    )


def evaluate_rule_acceptance(snapshot: dict[str, Any], settings: RuleAcceptanceSettings | None = None) -> dict[str, Any]:
    settings = settings or default_rule_acceptance_settings()
    features = numeric_feature_map(snapshot)
    direction = str(snapshot.get("direction") or "").lower()
    direction_sign = 1.0 if direction == "long" else -1.0
    missing = snapshot.get("missing") or {}
    reasons: list[str] = []

    def available(key: str) -> bool:
        return not bool(missing.get(key))

    def support_component(value: float, threshold: float) -> float:
        return _clip(((value - threshold) / max(abs(threshold), 1e-6)) * 100.0)

    def inverse_component(value: float, maximum: float) -> float:
        return _clip(((maximum - value) / max(abs(maximum), 1e-6)) * 100.0)

    core_parts: list[tuple[float, float]] = []
    if available("directional_slope_atr"):
        slope_component = support_component(features["directional_slope_atr"], settings.slope_minimum)
        core_parts.append((0.30, slope_component))
        if features["directional_slope_atr"] < settings.slope_minimum:
            reasons.append("weak_directional_slope")
    else:
        slope_component = None
    if available("efficiency_ratio"):
        er_component = support_component(features["efficiency_ratio"], settings.er_minimum)
        core_parts.append((0.20, er_component))
        if features["efficiency_ratio"] < settings.er_minimum:
            reasons.append("low_efficiency_ratio")
    else:
        er_component = None
    if available("directional_di_spread"):
        di_component = support_component(features["directional_di_spread"], settings.di_spread_minimum)
        core_parts.append((0.20, di_component))
        if features["directional_di_spread"] < settings.di_spread_minimum:
            reasons.append("weak_directional_di")
    else:
        di_component = None
    if available("choppiness"):
        chop_component = inverse_component(features["choppiness"], settings.chop_maximum)
        core_parts.append((0.15, chop_component))
        if features["choppiness"] > settings.chop_maximum:
            reasons.append("high_chop")
    else:
        chop_component = None
    if available("range_width"):
        range_component = support_component(features["range_width"], settings.corridor_width_minimum)
        core_parts.append((0.15, range_component))
        if features["range_width"] < settings.corridor_width_minimum:
            reasons.append("narrow_corridor")
    else:
        range_component = None
    core_weight = sum(weight for weight, _ in core_parts)
    core_score = sum(weight * value for weight, value in core_parts) / core_weight if core_weight > 0 else 0.0
    core_pass = core_weight > 0 and core_score >= settings.core_score_threshold

    perp_parts: list[tuple[float, float]] = []
    basis_hard_fail = False
    basis_bps = abs(features["basis_bps"])
    if available("basis_bps"):
        if basis_bps > settings.basis_hard_bps:
            basis_hard_fail = True
            reasons.append("basis_dislocation")
        basis_component = _clip(((settings.basis_soft_bps - basis_bps) / max(settings.basis_soft_bps, 1e-6)) * 60.0, -100.0, 20.0)
        perp_parts.append((0.45, basis_component))
    else:
        basis_component = None
    premium_rate = abs(features["premium_basis_rate"])
    if available("premium_basis_rate"):
        premium_component = _clip(((settings.premium_soft_rate - premium_rate) / max(settings.premium_soft_rate, 1e-6)) * 50.0, -100.0, 15.0)
        perp_parts.append((0.25, premium_component))
        if premium_rate > settings.premium_soft_rate:
            reasons.append("wide_premium_basis")
    else:
        premium_component = None
    if available("funding_rate"):
        directional_funding = (-direction_sign) * features["funding_rate"]
        funding_component = _clip((directional_funding / max(settings.funding_adverse_threshold, 1e-8)) * 40.0, -60.0, 40.0)
        hours_to_funding = features["time_to_next_funding_hours"]
        if available("time_to_next_funding_hours") and (hours_to_funding * 60.0) <= settings.near_funding_minutes and funding_component < 0:
            funding_component *= 1.5
        perp_parts.append((0.30, funding_component))
        if funding_component < 0:
            reasons.append("adverse_funding")
    else:
        funding_component = None
    perp_weight = sum(weight for weight, _ in perp_parts)
    perp_score = sum(weight * value for weight, value in perp_parts) / perp_weight if perp_weight > 0 else 0.0
    perp_pass = not basis_hard_fail and (perp_weight == 0 or perp_score >= settings.perp_score_floor)

    micro = snapshot.get("microstructure") or {}
    trade_flow_available = micro.get("trade_flow_available")
    top_of_book_available = micro.get("top_of_book_available")
    spread_bps = features["spread_bps"]
    liquidity_support = 0.0
    liquidity_status = "unknown"
    liquidity_hard_fail = False
    if available("spread_bps"):
        if spread_bps > settings.liquidity_hard_spread_bps:
            liquidity_hard_fail = True
            liquidity_status = "fail"
            reasons.append("wide_spread")
        elif spread_bps > settings.liquidity_soft_spread_bps:
            liquidity_status = "warn"
            liquidity_support -= 20.0
            reasons.append("elevated_spread")
        else:
            liquidity_status = "pass"
            liquidity_support += 10.0
    if trade_flow_available is False or top_of_book_available is False:
        liquidity_hard_fail = True
        liquidity_status = "fail"
        reasons.append("liquidity_stream_unhealthy")
    if available("primary_signed_imbalance_ratio"):
        signed_alignment = direction_sign * features["primary_signed_imbalance_ratio"]
        liquidity_support += _clip((signed_alignment / max(settings.signed_support_threshold, 1e-6)) * 15.0, -20.0, 20.0)
    if available("top_of_book_imbalance"):
        book_alignment = direction_sign * features["top_of_book_imbalance"]
        liquidity_support += _clip((book_alignment / max(settings.book_support_threshold, 1e-6)) * 10.0, -15.0, 15.0)
    if liquidity_status == "unknown" and (available("primary_signed_imbalance_ratio") or available("top_of_book_imbalance")):
        liquidity_status = "pass"

    total_score = (0.7 * core_score) + (0.3 * perp_score) + liquidity_support
    accept_candidate = core_pass and perp_pass and not liquidity_hard_fail and total_score >= settings.total_score_threshold
    if not accept_candidate and not reasons:
        reasons.append("score_below_threshold")
    return {
        "observe_only": True,
        "status": "scored",
        "version": "rule_acceptance_v1",
        "core_score": round(core_score, 6),
        "perp_score": round(perp_score, 6),
        "liquidity_support": round(liquidity_support, 6),
        "total_score": round(total_score, 6),
        "core_pass": core_pass,
        "perp_pass": perp_pass,
        "liquidity_status": liquidity_status,
        "liquidity_hard_fail": liquidity_hard_fail,
        "accept_candidate": accept_candidate,
        "reasons": sorted(set(reasons)),
        "components": {
            "slope_component": slope_component,
            "efficiency_ratio_component": er_component,
            "directional_di_component": di_component,
            "chop_component": chop_component,
            "range_component": range_component,
            "basis_component": basis_component,
            "premium_component": premium_component,
            "funding_component": funding_component,
        },
        "settings": asdict(settings),
    }
