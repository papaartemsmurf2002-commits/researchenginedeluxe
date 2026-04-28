from __future__ import annotations

import pandas as pd
import pytest

from tradingbotsuite.research.feature_alignment import (
    align_completed_bar_features_to_events,
    feature_availability_column,
    prepare_completed_bar_feature_input,
    validate_completed_bar_continuity,
)


def test_prepare_completed_bar_feature_input_excludes_current_incomplete_bar() -> None:
    bars = pd.DataFrame(
        {
            "bar_time_ms": [0, 60_000, 120_000],
            "close": [100.0, 101.0, 102.0],
        }
    )

    prepared, validation = prepare_completed_bar_feature_input(
        bars,
        bar_time_column="bar_time_ms",
        interval_ms=60_000,
        current_time_ms=150_000,
    )

    assert validation.valid is True
    assert validation.incomplete_bar_times == (120_000,)
    assert "incomplete_current_bars" in validation.quality_flags
    assert prepared["bar_time_ms"].tolist() == [0, 60_000]
    assert prepared["feature_time_ms"].tolist() == [60_000, 120_000]


def test_completed_bar_validation_flags_duplicates_and_gaps() -> None:
    duplicate_bars = pd.DataFrame({"bar_time_ms": [0, 60_000, 60_000, 120_000]})
    duplicate_result = validate_completed_bar_continuity(
        duplicate_bars,
        bar_time_column="bar_time_ms",
        interval_ms=60_000,
    )

    assert duplicate_result.valid is False
    assert duplicate_result.duplicate_bar_times == (60_000,)
    assert "duplicate_bar_times" in duplicate_result.quality_flags
    assert "duplicate_bar_times:60000" in duplicate_result.errors
    with pytest.raises(ValueError, match="duplicate_bar_times:60000"):
        prepare_completed_bar_feature_input(
            duplicate_bars,
            bar_time_column="bar_time_ms",
            interval_ms=60_000,
        )

    gapped_bars = pd.DataFrame({"bar_time_ms": [0, 60_000, 180_000]})
    gap_result = validate_completed_bar_continuity(
        gapped_bars,
        bar_time_column="bar_time_ms",
        interval_ms=60_000,
    )

    assert gap_result.valid is False
    assert gap_result.gap_start_times == (60_000,)
    assert "bar_time_gaps" in gap_result.quality_flags
    assert "bar_time_gaps:60000" in gap_result.errors


def test_point_in_time_feature_join_never_uses_future_rows() -> None:
    events = pd.DataFrame(
        {
            "event_id": ["before", "middle", "late"],
            "decision_time_ms": [50_000, 150_000, 250_000],
        }
    )
    features = pd.DataFrame(
        {
            "feature_time_ms": [100_000, 200_000, 300_000],
            "wt3d_fast": [1.0, 2.0, 999.0],
        }
    )

    aligned = align_completed_bar_features_to_events(
        events,
        features,
        feature_columns=["wt3d_fast"],
    )

    assert aligned["event_id"].tolist() == ["before", "middle", "late"]
    assert pd.isna(aligned.loc[0, "wt3d_fast"])
    assert aligned.loc[1, "wt3d_fast"] == 1.0
    assert aligned.loc[2, "wt3d_fast"] == 2.0
    matched = aligned["feature_time_ms"].notna()
    assert aligned.loc[matched, "feature_time_ms"].le(aligned.loc[matched, "decision_time_ms"]).all()
    assert 999.0 not in set(aligned["wt3d_fast"].dropna())


def test_missing_features_produce_availability_flags_without_zero_fill() -> None:
    events = pd.DataFrame({"decision_time_ms": [50_000, 150_000, 250_000]})
    features = pd.DataFrame(
        {
            "feature_time_ms": [100_000, 200_000],
            "wt3d_fast": [1.25, None],
        }
    )

    aligned = align_completed_bar_features_to_events(
        events,
        features,
        feature_columns=["wt3d_fast", "wt3d_slow"],
    )

    fast_available = feature_availability_column("wt3d_fast")
    slow_available = feature_availability_column("wt3d_slow")
    assert aligned[fast_available].tolist() == [False, True, False]
    assert aligned[slow_available].tolist() == [False, False, False]
    assert aligned["feature_row_available"].tolist() == [False, True, True]
    assert aligned["feature_alignment_available"].tolist() == [False, False, False]
    assert pd.isna(aligned.loc[0, "wt3d_fast"])
    assert aligned.loc[1, "wt3d_fast"] == 1.25
    assert pd.isna(aligned.loc[2, "wt3d_fast"])
    assert aligned["wt3d_slow"].isna().all()
