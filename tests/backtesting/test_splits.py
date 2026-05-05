from __future__ import annotations

import pandas as pd
import pytest

from tradingbotsuite.backtesting.splits import (
    build_anchored_walk_forward_splits,
    build_rolling_walk_forward_splits,
    build_shifted_walk_forward_splits,
    frame_for_split,
    month_holdout_splits,
    regime_holdout_splits,
    stress_period_holdout_splits,
)


def _frame(row_count: int = 96) -> pd.DataFrame:
    start = 1_712_649_600_000
    return pd.DataFrame(
        {
            "bar_time_ms": [start + index * 900_000 for index in range(row_count)],
            "regime": ["trend" if index < row_count // 2 else "range" for index in range(row_count)],
            "volatility_shock_zscore": [3.0 if index % 17 == 0 else 0.2 for index in range(row_count)],
        }
    )


def test_anchored_and_rolling_walk_forward_splits_have_distinct_train_windows() -> None:
    frame = _frame()

    anchored = build_anchored_walk_forward_splits(frame, min_splits=3, purge_embargo_bars=2)
    rolling = build_rolling_walk_forward_splits(frame, min_splits=3, train_window_bars=12, purge_embargo_bars=2)

    assert anchored[1].split_mode == "anchored"
    assert anchored[1].train_start_index == 0
    assert rolling[1].split_mode == "rolling"
    assert rolling[1].train_window_bars == 12
    assert rolling[1].train_end_index - rolling[1].train_start_index + 1 <= 12


def test_rolling_split_requires_train_window() -> None:
    with pytest.raises(ValueError, match="train_window_bars"):
        build_rolling_walk_forward_splits(_frame(), min_splits=2, train_window_bars=0)


def test_shifted_walk_forward_splits_move_validation_anchor() -> None:
    frame = _frame()

    base = build_anchored_walk_forward_splits(frame, min_splits=2, purge_embargo_bars=2)
    shifted = build_shifted_walk_forward_splits(frame, min_splits=2, anchor_offset_bars=3, purge_embargo_bars=2)

    assert [split.validation_start_index for split in shifted] == [
        split.validation_start_index + 3 for split in base
    ]
    assert {split.validation_method for split in shifted} == {"shifted_purged_walk_forward"}
    assert {split.split_mode for split in shifted} == {"shifted"}
    assert {split.anchor_offset_bars for split in shifted} == {3}
    assert {split.purge_embargo_bars for split in shifted} == {2}


def test_holdout_split_modes_emit_metadata() -> None:
    frame = _frame()

    assert month_holdout_splits(frame)[0].validation_method == "month_holdout"
    assert {split.validation_method for split in regime_holdout_splits(frame)} == {"regime_holdout"}
    assert stress_period_holdout_splits(frame)[0].validation_method == "stress_period_holdout"


def test_regime_holdout_frame_uses_only_matching_non_contiguous_rows() -> None:
    frame = _frame(12)
    frame["regime"] = ["trend" if index % 2 == 0 else "range" for index in range(len(frame))]

    trend_split = [
        split
        for split in regime_holdout_splits(frame)
        if set(frame_for_split(frame, split)["regime"]) == {"trend"}
    ][0]
    held_out = frame_for_split(frame, trend_split)

    assert set(held_out["regime"]) == {"trend"}
    assert trend_split.validation_size_bars == len(held_out) == 6


def test_stress_holdout_frame_uses_only_scattered_shock_rows() -> None:
    frame = _frame(12)
    frame["volatility_shock_zscore"] = [3.0 if index in {1, 7, 10} else 0.1 for index in range(len(frame))]

    split = stress_period_holdout_splits(frame, threshold=2.0)[0]
    held_out = frame_for_split(frame, split)

    assert held_out.index.tolist() == [1, 7, 10]
    assert set(held_out["volatility_shock_zscore"]) == {3.0}
    assert split.validation_size_bars == 3
