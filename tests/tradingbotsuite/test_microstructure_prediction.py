from __future__ import annotations

from decimal import Decimal

from tradingbotsuite.core.microstructure_prediction import build_microstructure_prediction


def test_microstructure_prediction_scores_up_pressure() -> None:
    prediction = build_microstructure_prediction(
        {
            "trade_flow_available": True,
            "top_of_book_available": True,
            "queue_imbalance_available": True,
            "depth_depletion_available": True,
            "spread_bps": "0.5",
            "windows": {"20": {"signed_ratio": "0.6", "sqrt_signed_ratio": "0.45", "flow_price_alignment_bps": "2.5"}},
            "top_of_book_imbalance": "0.4",
            "queue_imbalance_l1": "0.2",
            "queue_imbalance_l5": "0.3",
            "queue_imbalance_l10": "0.4",
            "depth_depletion": {"bid_l5": "0.1", "ask_l5": "0.5"},
        }
    )

    probabilities = prediction["probabilities"]
    assert prediction["status"] == "scored"
    assert prediction["observe_only"] is True
    assert prediction["calibrated"] is False
    assert prediction["direction"] == "up"
    assert Decimal(probabilities["up"]) > Decimal(probabilities["down"])
    assert Decimal(probabilities["up"]) + Decimal(probabilities["down"]) + Decimal(probabilities["neutral"]) == Decimal("1.000000")


def test_microstructure_prediction_degrades_when_only_top_of_book_available() -> None:
    prediction = build_microstructure_prediction(
        {
            "trade_flow_available": False,
            "top_of_book_available": True,
            "queue_imbalance_available": False,
            "depth_depletion_available": False,
            "spread_bps": "1.0",
            "windows": {"20": {"signed_ratio": "0.9"}},
            "top_of_book_imbalance": "-0.5",
        }
    )

    assert prediction["status"] == "scored"
    assert prediction["direction"] == "down"
    assert Decimal(prediction["coverage"]) < Decimal("0.5")
    assert [item["available"] for item in prediction["components"]] == [False, False, True, False, False]


def test_microstructure_prediction_is_unavailable_without_inputs() -> None:
    prediction = build_microstructure_prediction(None)

    assert prediction["status"] == "unavailable"
    assert prediction["probabilities"] == {"up": None, "down": None, "neutral": None}
