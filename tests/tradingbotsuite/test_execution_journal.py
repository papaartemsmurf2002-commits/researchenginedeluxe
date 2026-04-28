from __future__ import annotations

import json
from pathlib import Path

import pytest

from tradingbotsuite.research.execution_journal import (
    SCHEMA_VERSION,
    ExecutionJournalValidationError,
    append_journal_events,
    deterministic_cloid,
    read_journal_events,
    read_journal_for_replay,
    validate_event,
)


def _order_event(**updates: object) -> dict[str, object]:
    event: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "event_type": "order_submitted",
        "symbol": "BTCUSDT",
        "source_event_time_ms": 1_000,
        "receive_time_ms": 1_010,
        "source_row_index": 0,
        "cloid": deterministic_cloid("BTCUSDT", "entry", "signal-1"),
        "cloid_strategy": "deterministic",
        "side": "buy",
        "reduce_only": False,
        "raw_payload": {"status": "submitted"},
    }
    event.update(updates)
    return event


def test_order_validation_rejects_missing_cloid_except_pre_submit_reject() -> None:
    event = _order_event()
    event.pop("cloid")

    with pytest.raises(ExecutionJournalValidationError, match="deterministic_cloid_required"):
        validate_event(event)

    reject_event = _order_event(
        event_type="order_rejected",
        pre_submit_reject=True,
        raw_payload={"reason": "local risk rejected before cloid"},
    )
    reject_event.pop("cloid")

    validated = validate_event(reject_event)

    assert validated["event_type"] == "order_rejected"
    assert validated["pre_submit_reject"] is True


def test_exit_intent_requires_reduce_only_true() -> None:
    event = _order_event(event_type="order_intent", exit_intent=True, reduce_only=False)

    with pytest.raises(ExecutionJournalValidationError, match="exit_intent_requires_reduce_only_true"):
        validate_event(event)

    validated = validate_event({**event, "reduce_only": True})

    assert validated["exit_intent"] is True
    assert validated["reduce_only"] is True


def test_append_read_and_replay_journal_are_deterministic(tmp_path: Path) -> None:
    journal_path = tmp_path / "execution_journal.jsonl"
    events = [
        _order_event(
            event_type="order_filled",
            receive_time_ms=300,
            source_event_time_ms=250,
            source_row_index=2,
            raw_payload={"fill_price": "71000", "fill_size": "0.01"},
        ),
        _order_event(
            event_type="order_acknowledged",
            receive_time_ms=200,
            source_event_time_ms=150,
            source_row_index=1,
            raw_payload={"exchange_order_id": "123"},
        ),
        _order_event(
            event_type="order_intent",
            receive_time_ms=200,
            source_event_time_ms=100,
            source_row_index=0,
            raw_payload={"intent_id": "entry-1"},
        ),
    ]

    result = append_journal_events(journal_path, events)

    assert result.row_count == 3
    assert len(result.sha256) == 64
    assert len(result.manifest_hash) == 64
    assert result.manifest_path.exists()
    assert [event["event_type"] for event in read_journal_events(journal_path)] == [
        "order_filled",
        "order_acknowledged",
        "order_intent",
    ]
    assert [event["event_type"] for event in read_journal_for_replay(journal_path)] == [
        "order_intent",
        "order_acknowledged",
        "order_filled",
    ]

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == SCHEMA_VERSION
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["intended_use"] == "research_observe_only"
    assert manifest["live_signal_input"] is False
    assert manifest["position_sizing_input"] is False
    assert manifest["replay_order"] == ["receive_time_ms", "source_event_time_ms", "source_row_index"]


def test_funding_and_reconciliation_events_are_preserved(tmp_path: Path) -> None:
    journal_path = tmp_path / "account_journal.jsonl"
    funding_event = {
        "schema_version": SCHEMA_VERSION,
        "event_type": "funding_payment",
        "symbol": "BTCUSDT",
        "source_event_time_ms": 4_000,
        "receive_time_ms": 4_005,
        "source_row_index": 3,
        "funding_rate": "0.0001",
        "funding_payment": "-0.25",
        "raw_payload": {"coin": "BTC", "funding": "-0.25"},
    }
    reconciliation_event = {
        "schema_version": SCHEMA_VERSION,
        "event_type": "reconciliation",
        "symbol": "BTCUSDT",
        "source_event_time_ms": 4_100,
        "receive_time_unavailable_reason": "offline_replay_without_local_receive_clock",
        "source_row_index": 4,
        "position_size": "0.01",
        "open_order_cloids": [deterministic_cloid("BTCUSDT", "entry", "signal-1")],
        "payload": {"exchange_position_size": "0.01", "local_position_size": "0.01"},
    }

    append_journal_events(journal_path, [funding_event, reconciliation_event])
    events = read_journal_for_replay(journal_path)

    assert [event["event_type"] for event in events] == ["funding_payment", "reconciliation"]
    assert events[0]["funding_payment"] == "-0.25"
    assert events[1]["receive_time_unavailable_reason"] == "offline_replay_without_local_receive_clock"
    assert events[1]["open_order_cloids"] == [deterministic_cloid("BTCUSDT", "entry", "signal-1")]
    assert len(events[0]["payload_hash"]) == 64
    assert len(events[1]["payload_hash"]) == 64
