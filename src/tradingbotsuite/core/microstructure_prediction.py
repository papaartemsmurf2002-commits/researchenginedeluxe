from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _clamp(value: Decimal, lower: Decimal, upper: Decimal) -> Decimal:
    return max(lower, min(upper, value))


def _component(name: str, value: Decimal | None, weight: Decimal, available: bool, description: str) -> dict[str, Any]:
    return {
        "name": name,
        "value": str(value) if value is not None else None,
        "weight": str(weight),
        "available": available,
        "description": description,
    }


def build_microstructure_prediction(microstructure: dict[str, Any] | None) -> dict[str, Any]:
    """Build an operator-facing, heuristic microstructure pressure summary.

    This is intentionally not a calibrated model. It converts signed flow and
    order-book pressure into readable live probabilities for visualization only.
    """
    if not microstructure:
        return {
            "status": "unavailable",
            "method": "heuristic_microstructure_pressure_v1",
            "observe_only": True,
            "calibrated": False,
            "reason": "missing_microstructure_snapshot",
            "probabilities": {"up": None, "down": None, "neutral": None},
            "components": [],
        }

    primary_window = (microstructure.get("windows") or {}).get("20") or {}
    signed_ratio = _decimal(primary_window.get("signed_ratio"))
    sqrt_signed_ratio = _decimal(primary_window.get("sqrt_signed_ratio")) or signed_ratio
    flow_price_alignment_bps = _decimal(primary_window.get("flow_price_alignment_bps"))
    if flow_price_alignment_bps is not None:
        # Alignment is in bps. Compress it into [-1, 1] for display scoring;
        # this is not a strategy threshold.
        flow_price_alignment = _clamp(flow_price_alignment_bps / Decimal("5"), Decimal("-1"), Decimal("1"))
    else:
        flow_price_alignment = None
    top_imbalance = _decimal(microstructure.get("top_of_book_imbalance"))
    queue_values = [
        _decimal(microstructure.get("queue_imbalance_l1")),
        _decimal(microstructure.get("queue_imbalance_l5")),
        _decimal(microstructure.get("queue_imbalance_l10")),
    ]
    queue_available_values = [value for value in queue_values if value is not None]
    queue_imbalance = (
        sum(queue_available_values, start=Decimal("0")) / Decimal(len(queue_available_values))
        if queue_available_values
        else None
    )
    depletion = microstructure.get("depth_depletion") or {}
    bid_depletion_l5 = _decimal(depletion.get("bid_l5"))
    ask_depletion_l5 = _decimal(depletion.get("ask_l5"))
    depth_depletion_bias = (
        _clamp(ask_depletion_l5 - bid_depletion_l5, Decimal("-1"), Decimal("1"))
        if bid_depletion_l5 is not None and ask_depletion_l5 is not None
        else None
    )
    spread_bps = _decimal(microstructure.get("spread_bps"))
    spread_penalty = Decimal("0")
    if spread_bps is not None:
        # This only affects confidence, not direction. 2 bps is treated as a
        # practical visualization anchor, not a trading threshold.
        spread_penalty = _clamp(spread_bps / Decimal("2"), Decimal("0"), Decimal("0.60"))

    raw_components = [
        ("sqrt_signed_flow_20s", sqrt_signed_ratio, Decimal("0.34"), bool(microstructure.get("trade_flow_available")), "Square-root transformed aggressive flow over the primary 20s window."),
        ("flow_price_alignment", flow_price_alignment, Decimal("0.12"), bool(microstructure.get("trade_flow_available")) and flow_price_alignment is not None, "Whether recent price response aligns with signed flow."),
        ("top_of_book", top_imbalance, Decimal("0.26"), bool(microstructure.get("top_of_book_available")), "Best bid/ask quantity imbalance from bookTicker."),
        ("queue_depth", queue_imbalance, Decimal("0.18"), bool(microstructure.get("queue_imbalance_available")), "Average local-book queue imbalance across L1/L5/L10."),
        ("depth_depletion", depth_depletion_bias, Decimal("0.10"), bool(microstructure.get("depth_depletion_available")), "Ask-side depletion minus bid-side depletion at L5; positive means thinner ask side."),
    ]
    components: list[dict[str, Any]] = []
    weighted_sum = Decimal("0")
    available_weight = Decimal("0")
    pressure_weight = Decimal("0")
    for name, value, weight, available, description in raw_components:
        clipped = _clamp(value, Decimal("-1"), Decimal("1")) if value is not None and available else None
        components.append(_component(name, clipped, weight, clipped is not None, description))
        if clipped is None:
            continue
        weighted_sum += clipped * weight
        available_weight += weight
        pressure_weight += abs(clipped) * weight

    if available_weight <= 0:
        return {
            "status": "unavailable",
            "method": "heuristic_microstructure_pressure_v1",
            "observe_only": True,
            "calibrated": False,
            "reason": "no_available_microstructure_components",
            "probabilities": {"up": None, "down": None, "neutral": None},
            "components": components,
        }

    directional_score = _clamp(weighted_sum / available_weight, Decimal("-1"), Decimal("1"))
    coverage = _clamp(available_weight / Decimal("1.00"), Decimal("0"), Decimal("1"))
    pressure_strength = _clamp(pressure_weight / available_weight, Decimal("0"), Decimal("1"))
    confidence = _clamp((coverage * Decimal("0.55")) + (pressure_strength * Decimal("0.45")) - spread_penalty, Decimal("0"), Decimal("1"))
    neutral_probability = _clamp(
        Decimal("0.12") + ((Decimal("1") - confidence) * Decimal("0.45")) + ((Decimal("1") - abs(directional_score)) * Decimal("0.25")),
        Decimal("0.08"),
        Decimal("0.75"),
    )
    directional_pool = Decimal("1") - neutral_probability
    up_share = (Decimal("1") + directional_score) / Decimal("2")
    up_probability = _clamp(directional_pool * up_share, Decimal("0"), Decimal("1"))
    down_probability = _clamp(directional_pool - up_probability, Decimal("0"), Decimal("1"))
    direction = "up" if directional_score > Decimal("0.05") else ("down" if directional_score < Decimal("-0.05") else "neutral")

    return {
        "status": "scored",
        "method": "heuristic_microstructure_pressure_v1",
        "observe_only": True,
        "calibrated": False,
        "horizon": "short_horizon_order_flow_pressure",
        "warning": "Visualization only: these probabilities are heuristic and are not approved live gating inputs.",
        "direction": direction,
        "directional_score": str(directional_score),
        "confidence": str(confidence),
        "coverage": str(coverage),
        "pressure_strength": str(pressure_strength),
        "spread_penalty": str(spread_penalty),
        "probabilities": {
            "up": str(up_probability),
            "down": str(down_probability),
            "neutral": str(neutral_probability),
        },
        "components": components,
        "inputs": {
            "primary_window_seconds": 20,
            "signed_ratio": str(signed_ratio) if signed_ratio is not None else None,
            "sqrt_signed_ratio": str(sqrt_signed_ratio) if sqrt_signed_ratio is not None else None,
            "flow_price_alignment_bps": str(flow_price_alignment_bps) if flow_price_alignment_bps is not None else None,
            "top_of_book_imbalance": str(top_imbalance) if top_imbalance is not None else None,
            "queue_imbalance": str(queue_imbalance) if queue_imbalance is not None else None,
            "depth_depletion_bias": str(depth_depletion_bias) if depth_depletion_bias is not None else None,
            "spread_bps": str(spread_bps) if spread_bps is not None else None,
        },
    }
