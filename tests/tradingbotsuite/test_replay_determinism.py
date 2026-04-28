from __future__ import annotations

import pytest

from tradingbotsuite.research.replay import (
    ReplayDeterminismError,
    compare_replay_runs,
    hash_replay_events,
    order_replay_events,
)


def _event(event_id: str, *, source_time: int, receive_time: int | None, row_index: int) -> dict[str, object]:
    event = {
        "schema_version": "market-journal-jsonl-v1",
        "source_name": "binance_vision",
        "symbol": "BTCUSDT",
        "data_family": "trade",
        "source_event_time_ms": source_time,
        "source_row_index": row_index,
        "payload_hash": f"sha256:{event_id}",
        "raw_payload": {"event_id": event_id},
    }
    if receive_time is not None:
        event["receive_time_ms"] = receive_time
    return event


def test_ordered_hash_is_stable_across_input_order_variations() -> None:
    events = [
        _event("b", source_time=200, receive_time=1_000, row_index=1),
        _event("a", source_time=100, receive_time=1_010, row_index=0),
        _event("c", source_time=200, receive_time=1_000, row_index=2),
    ]

    first = hash_replay_events(events, order_by="source_time")
    second = hash_replay_events(list(reversed(events)), order_by="source_time")

    assert first["research_only"] is True
    assert first["observe_only"] is True
    assert first["promotion_ready"] is False
    assert first["sha256"] == second["sha256"]
    assert [event["raw_payload"]["event_id"] for event in first["ordered_events"]] == ["a", "b", "c"]


def test_source_time_and_receive_time_modes_can_order_differently() -> None:
    events = [
        _event("source-first", source_time=100, receive_time=300, row_index=0),
        _event("receive-first", source_time=200, receive_time=100, row_index=1),
    ]

    source_order = order_replay_events(events, order_by="source_time")
    receive_order = order_replay_events(events, order_by="receive_time")

    assert [event["raw_payload"]["event_id"] for event in source_order] == ["source-first", "receive-first"]
    assert [event["raw_payload"]["event_id"] for event in receive_order] == ["receive-first", "source-first"]
    assert hash_replay_events(events, order_by="source_time")["sha256"] != hash_replay_events(events, order_by="receive_time")["sha256"]


def test_missing_required_order_timestamp_fails_clearly() -> None:
    missing_receive = [_event("missing-receive", source_time=100, receive_time=None, row_index=0)]
    missing_source = [_event("missing-source", source_time=100, receive_time=110, row_index=0)]
    missing_source[0].pop("source_event_time_ms")

    with pytest.raises(ReplayDeterminismError, match="missing required timestamp for replay order receive_time"):
        hash_replay_events(missing_receive, order_by="receive_time")

    with pytest.raises(ReplayDeterminismError, match="missing required timestamp for replay order source_time"):
        hash_replay_events(missing_source, order_by="source_time")


def test_replay_comparison_reports_mismatch_without_throwing() -> None:
    left = [
        _event("same", source_time=100, receive_time=110, row_index=0),
        _event("left-only-value", source_time=200, receive_time=210, row_index=1),
    ]
    right = [
        _event("same", source_time=100, receive_time=110, row_index=0),
        _event("right-only-value", source_time=200, receive_time=210, row_index=1),
    ]

    comparison = compare_replay_runs(left, right, order_by="source_time")

    assert comparison["research_only"] is True
    assert comparison["observe_only"] is True
    assert comparison["promotion_ready"] is False
    assert comparison["match"] is False
    assert comparison["first_mismatch_index"] == 1
    assert comparison["first_mismatch"]["left_event"]["raw_payload"]["event_id"] == "left-only-value"
    assert comparison["first_mismatch"]["right_event"]["raw_payload"]["event_id"] == "right-only-value"
