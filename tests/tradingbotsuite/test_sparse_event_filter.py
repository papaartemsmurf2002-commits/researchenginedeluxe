from __future__ import annotations

import pandas as pd

from tradingbotsuite.strategies import sparse_event_filter
from tradingbotsuite.strategies.sparse_event_filter import SparseEventFilterStrategy


def test_sparse_event_filter_caches_flow_confirmation_columns(monkeypatch) -> None:
    row_count = 20
    slope = [0.2 if index % 2 == 0 else -0.2 for index in range(row_count)]
    frame = pd.DataFrame(
        {
            "feature_time_ms": [index * 15 * 60 * 1000 for index in range(row_count)],
            "symbol": ["BTCUSDT"] * row_count,
            "close": [100.0 + index for index in range(row_count)],
            "volatility_shock_zscore": [2.0] * row_count,
            "atr_percentile": [1.0] * row_count,
            "directional_slope_atr": slope,
            "quality_aggtrade_source_present": [1.0] * row_count,
            "quality_aggtrade_context_missing": [0.0] * row_count,
            "quality_aggtrade_latest_window_diagnostic": [0.0] * row_count,
            "agg_signed_quote_imbalance": [0.2 if value > 0 else -0.2 for value in slope],
            "agg_trade_count_zscore": [1.0] * row_count,
        }
    )
    calls: dict[str, int] = {}
    original_numeric = sparse_event_filter.numeric

    def counting_numeric(source_frame: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
        calls[column] = calls.get(column, 0) + 1
        return original_numeric(source_frame, column, default)

    monkeypatch.setattr(sparse_event_filter, "numeric", counting_numeric)
    strategy = SparseEventFilterStrategy(
        config={
            "feature_set_id": "features_price_perp_aggflow_no_wt",
            "holding_period": "24h",
            "base_model": "volatility_breakout",
            "spacing_bars": 1,
            "min_score": 0.0,
            "score_window_bars": 96,
            "top_n_per_window": row_count,
            "flow_confirmation": "aligned",
            "flow_abs_threshold": 0.1,
            "flow_count_z_min": 0.0,
        }
    )

    predictions = strategy.predict(frame)

    assert len(predictions) == row_count
    assert calls["quality_aggtrade_source_present"] == 1
    assert calls["quality_aggtrade_context_missing"] == 1
    assert calls["quality_aggtrade_latest_window_diagnostic"] == 1
    assert calls["agg_signed_quote_imbalance"] == 1
    assert calls["agg_trade_count_zscore"] == 1
