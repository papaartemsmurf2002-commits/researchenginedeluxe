from __future__ import annotations

import pandas as pd
import numpy as np
import pytest

from tradingbotsuite.research_discovery.event_accounting import account_independent_events, account_independent_events_arrays
from tradingbotsuite.research_discovery.runner import _knn_trial_metrics


def _accepted_rows(source_rows: list[int], *, side: str = "long") -> pd.DataFrame:
    p_up = 0.70 if side == "long" else 0.30
    p_down = 0.30 if side == "long" else 0.70
    return pd.DataFrame(
        {
            "source_row_index": source_rows,
            "label_return": [0.01] * len(source_rows),
            "p_up_barrier": [p_up] * len(source_rows),
            "p_down_barrier": [p_down] * len(source_rows),
        }
    )


def test_independent_event_accounting_suppresses_overlapping_label_windows() -> None:
    accounting = account_independent_events(
        _accepted_rows([10, 11, 12, 15, 21]),
        total_row_count=100,
        label_horizon_bars=6,
        max_signal_rate=0.45,
    )

    assert accounting.accepted_bar_count == 5
    assert accounting.independent_event_count == 2
    assert accounting.suppressed_overlap_count == 3
    assert accounting.overlap_ratio == pytest.approx(0.6)
    assert accounting.event_signal_rate == pytest.approx(0.02)
    assert accounting.long_independent_event_count == 2
    assert accounting.short_independent_event_count == 0
    assert accounting.side_collapse_ratio == pytest.approx(1.0)


def test_independent_event_accounting_skips_rows_without_reproducible_labels_or_source() -> None:
    frame = pd.DataFrame(
        [
            {
                "symbol": "BTCUSDT",
                "source_row_index": 10,
                "label_return": 0.02,
                "p_up_barrier": 0.70,
                "p_down_barrier": 0.30,
            },
            {
                "symbol": "BTCUSDT",
                "source_row_index": 11,
                "label_return": 0.04,
                "p_up_barrier": 0.70,
                "p_down_barrier": 0.30,
            },
            {
                "symbol": "BTCUSDT",
                "source_row_index": 15,
                "label_return": -0.03,
                "p_up_barrier": 0.25,
                "p_down_barrier": 0.75,
            },
            {
                "symbol": "ETHUSDT",
                "source_row_index": 11,
                "label_return": -0.05,
                "p_up_barrier": 0.25,
                "p_down_barrier": 0.75,
            },
            {
                "symbol": "BTCUSDT",
                "source_row_index": None,
                "label_return": 0.99,
                "p_up_barrier": 0.70,
                "p_down_barrier": 0.30,
            },
            {
                "symbol": "BTCUSDT",
                "source_row_index": 22,
                "label_return": None,
                "p_up_barrier": 0.70,
                "p_down_barrier": 0.30,
            },
        ]
    )
    accounting = account_independent_events(
        frame,
        total_row_count=100,
        label_horizon_bars=4,
        max_signal_rate=0.45,
    )
    p_up = frame["p_up_barrier"].to_numpy(dtype=float)
    p_down = frame["p_down_barrier"].to_numpy(dtype=float)
    label_return = pd.to_numeric(frame["label_return"], errors="coerce").to_numpy(dtype=float)
    array_accounting = account_independent_events_arrays(
        accepted_mask=np.ones(len(frame), dtype=bool),
        symbol_codes=pd.factorize(frame["symbol"].astype(str), sort=True)[0],
        source_row_index=pd.to_numeric(frame["source_row_index"], errors="coerce").to_numpy(dtype=float),
        p_up_barrier=p_up,
        p_down_barrier=p_down,
        side_adjusted_return=label_return * np.where(p_down > p_up, -1.0, 1.0),
        neighbor_distance_quality=np.full(len(frame), np.nan),
        knn_vote_margin=np.full(len(frame), np.nan),
        total_row_count=100,
        label_horizon_bars=4,
        max_signal_rate=0.45,
    )

    assert accounting.accepted_bar_count == 4
    assert accounting.independent_event_count == 3
    assert accounting.suppressed_overlap_count == 1
    assert accounting.long_independent_event_count == 1
    assert accounting.short_independent_event_count == 2
    assert accounting.gross_independent_event_return == pytest.approx(0.10)
    assert array_accounting.to_payload() == accounting.to_payload()


def test_knn_trial_metrics_keep_legacy_density_score_but_rank_by_score_v2() -> None:
    dense = pd.DataFrame(
        {
            "source_row_index": list(range(20)),
            "accepted_by_knn": [True] * 20,
            "knn_skip_reason": [""] * 20,
            "label_return": [0.01] * 20,
            "p_up_barrier": [0.70] * 20,
            "p_down_barrier": [0.30] * 20,
            "neighbor_distance_quality": [0.50] * 20,
            "knn_vote_margin": [0.40] * 20,
        }
    )
    selective = pd.DataFrame(
        {
            "source_row_index": list(range(0, 200, 20)),
            "accepted_by_knn": [True] * 10,
            "knn_skip_reason": [""] * 10,
            "label_return": [0.01] * 10,
            "p_up_barrier": [0.70] * 10,
            "p_down_barrier": [0.30] * 10,
            "neighbor_distance_quality": [0.50] * 10,
            "knn_vote_margin": [0.40] * 10,
        }
    )
    search = type(
        "Search",
        (),
        {
            "min_trade_count": 1,
            "min_signal_rate": 0.0,
            "max_signal_rate": 1.0,
            "min_realized_expectancy": -1.0,
        },
    )()

    dense_metrics = _knn_trial_metrics(dense, search=search, label_horizon_bars=10)
    selective_metrics = _knn_trial_metrics(selective, search=search, label_horizon_bars=10)

    assert dense_metrics["accepted_bar_count"] == 20
    assert dense_metrics["independent_event_count"] == 2
    assert dense_metrics["overlap_ratio"] == pytest.approx(0.9)
    assert dense_metrics["legacy_density_score"] > selective_metrics["legacy_density_score"]
    assert dense_metrics["discovery_screen_score_v2"] < selective_metrics["discovery_screen_score_v2"]
    assert dense_metrics["final_score"] == dense_metrics["discovery_screen_score_v2"]


def test_score_v2_uses_independent_event_quality_terms() -> None:
    search = type(
        "Search",
        (),
        {
            "min_trade_count": 1,
            "min_signal_rate": 0.0,
            "max_signal_rate": 1.0,
            "min_realized_expectancy": -1.0,
        },
    )()
    dense = pd.DataFrame(
        {
            "source_row_index": [0, 1, 2, 3, 4],
            "accepted_by_knn": [True] * 5,
            "knn_skip_reason": [""] * 5,
            "label_return": [0.01] * 5,
            "p_up_barrier": [0.70] * 5,
            "p_down_barrier": [0.30] * 5,
            "neighbor_distance_quality": [0.10, 1.00, 1.00, 1.00, 1.00],
            "knn_vote_margin": [0.05, 1.00, 1.00, 1.00, 1.00],
        }
    )
    sparse = pd.DataFrame(
        {
            "source_row_index": [0],
            "accepted_by_knn": [True],
            "knn_skip_reason": [""],
            "label_return": [0.01],
            "p_up_barrier": [0.70],
            "p_down_barrier": [0.30],
            "neighbor_distance_quality": [0.10],
            "knn_vote_margin": [0.05],
        }
    )

    dense_metrics = _knn_trial_metrics(dense, search=search, label_horizon_bars=10)
    sparse_metrics = _knn_trial_metrics(sparse, search=search, label_horizon_bars=10)

    assert dense_metrics["independent_event_count"] == 1
    assert sparse_metrics["independent_event_count"] == 1
    assert dense_metrics["legacy_density_score"] > sparse_metrics["legacy_density_score"]
    assert dense_metrics["discovery_screen_score_v2"] < sparse_metrics["discovery_screen_score_v2"]


def test_knn_trial_metrics_emit_independent_event_blocker_reasons() -> None:
    search = type(
        "Search",
        (),
        {
            "min_trade_count": 4,
            "min_signal_rate": 0.0,
            "max_signal_rate": 1.0,
            "min_realized_expectancy": -1.0,
        },
    )()
    frame = pd.DataFrame(
        {
            "source_row_index": [0, 1, 2, 3, 4, 5],
            "accepted_by_knn": [True] * 6,
            "knn_skip_reason": [""] * 6,
            "label_return": [0.01] * 6,
            "p_up_barrier": [0.70] * 6,
            "p_down_barrier": [0.30] * 6,
        }
    )

    metrics = _knn_trial_metrics(frame, search=search, label_horizon_bars=10)

    assert metrics["independent_event_count"] == 1
    assert "independent_event_count_below_floor" in metrics["blocker_reasons"]
    assert "signal_rate_near_ceiling" in metrics["blocker_reasons"]
    assert "overlap_ratio_above_ceiling" in metrics["blocker_reasons"]


def test_knn_trial_metrics_emit_side_collapse_blocker_reason() -> None:
    search = type(
        "Search",
        (),
        {
            "min_trade_count": 4,
            "min_signal_rate": 0.0,
            "max_signal_rate": 2.0,
            "min_realized_expectancy": -1.0,
        },
    )()
    frame = pd.DataFrame(
        {
            "source_row_index": [0, 10, 20, 30],
            "accepted_by_knn": [True] * 4,
            "knn_skip_reason": [""] * 4,
            "label_return": [0.01] * 4,
            "p_up_barrier": [0.70] * 4,
            "p_down_barrier": [0.30] * 4,
        }
    )

    metrics = _knn_trial_metrics(frame, search=search, label_horizon_bars=1)

    assert metrics["independent_event_count"] == 4
    assert metrics["side_collapse_ratio"] == pytest.approx(1.0)
    assert "side_collapse_ratio_above_ceiling" in metrics["blocker_reasons"]
