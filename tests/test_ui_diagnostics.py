import pandas as pd

from tradingbot.config import default_app_config
from tradingbot.ui import _marker_bool, build_lc_diagnostics_payload


def test_ui_marker_bool_handles_shape_and_numeric_diagnostic_exports():
    frame = pd.DataFrame(
        {
            "Buy": ["", 101.25, None, 102.0],
            "startLongTrade": [0, 1, "0", "1"],
        }
    )

    assert _marker_bool(frame, "Buy").tolist() == [False, True, False, True]
    assert _marker_bool(frame, "startLongTrade").tolist() == [False, True, False, True]


def test_lc_diagnostics_payload_supports_chart_and_overrides(tmp_path):
    timestamps = pd.date_range("2026-01-01", periods=90, freq="15min", tz="UTC")
    closes = [100 + i * 0.25 + ((-1) ** i) * 0.4 for i in range(90)]
    frame = pd.DataFrame(
        {
            "time": [int(ts.timestamp()) for ts in timestamps],
            "open": closes,
            "high": [value + 1.0 for value in closes],
            "low": [value - 1.0 for value in closes],
            "close": closes,
            "Kernel Regression Estimate": closes,
            "Buy": [closes[5] if i == 5 else "" for i in range(90)],
            "Sell": [closes[20] if i == 20 else "" for i in range(90)],
            "StopBuy": [closes[30] if i == 30 else "" for i in range(90)],
            "StopSell": [closes[40] if i == 40 else "" for i in range(90)],
        }
    )
    csv_path = tmp_path / "tv_export.csv"
    frame.to_csv(csv_path, index=False)

    config = default_app_config()
    payload = build_lc_diagnostics_payload(
        csv_path,
        config,
        "BTC",
        overrides={
            "neighbors_count": 8,
            "max_bars_back": 2000,
            "feature_count": 5,
            "features": [
                {"name": "RSI", "param_a": 14, "param_b": 1},
                {"name": "WT", "param_a": 10, "param_b": 11},
                {"name": "CCI", "param_a": 20, "param_b": 1},
                {"name": "ADX", "param_a": 20, "param_b": 2},
                {"name": "RSI", "param_a": 9, "param_b": 1},
            ],
        },
        max_chart_points=50,
        window_mode="full",
        include_last_bar=True,
    )

    assert payload["summary"]["rows"] == 90
    assert payload["summary"]["chart_rows"] == 50
    assert payload["summary"]["tradingview_counts"]["buy"] == 1
    assert payload["summary"]["entry_mismatch_count"] == payload["summary"]["marker_mismatch_count"]
    assert payload["summary"]["last_timestamp"] == timestamps[-1].isoformat()
    assert "max_bars_back_index" in payload["summary"]
    assert "max_bars_back_timestamp" in payload["summary"]
    assert payload["settings"]["features"][2]["param_a"] == 20
    assert payload["chart"]["bars"]
    assert payload["latest_tradingview_entries"][-1]["side"] == "short"
    assert "marker_mismatch_count" in payload["summary"]
