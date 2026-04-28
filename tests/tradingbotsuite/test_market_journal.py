from __future__ import annotations

import json
from pathlib import Path

import pytest

from tradingbotsuite.research.market_journal import (
    MARKET_JOURNAL_SCHEMA_VERSION,
    MarketJournalValidationError,
    MarketJournalWriter,
    build_market_journal_event,
    read_market_journal_events,
    read_market_journal_for_replay,
    validate_market_journal_event,
    validate_market_journal_events,
)


def _agg_trade_event(**updates: object) -> dict[str, object]:
    event = build_market_journal_event(
        raw_payload={"e": "aggTrade", "s": "BTCUSDT", "a": 7, "T": 2_000},
        normalized_payload={
            "source_name": "binance_um_futures",
            "symbol": "BTCUSDT",
            "data_family": "agg_trade",
            "aggregate_trade_id": 7,
            "price": "71000.1",
            "quantity": "0.01",
        },
        source_event_time_ms=2_000,
        local_receive_time_ms=2_050,
        source_name="binance_um_futures",
        symbol="BTCUSDT",
        data_family="agg_trade",
        sequence=7,
        source_row_index=0,
    )
    event.update(updates)
    if "payload_hash" not in updates:
        event["payload_hash"] = build_market_journal_event(
            raw_payload=event["raw_payload"],  # type: ignore[arg-type]
            normalized_payload=event["normalized_payload"],  # type: ignore[arg-type]
            source_event_time_ms=event["source_event_time_ms"],  # type: ignore[arg-type]
            local_receive_time_ms=event["local_receive_time_ms"],  # type: ignore[arg-type]
            source_name=event["source_name"],  # type: ignore[arg-type]
            symbol=event["symbol"],  # type: ignore[arg-type]
            data_family=event["data_family"],  # type: ignore[arg-type]
            sequence=event["sequence"],  # type: ignore[arg-type]
            source_row_index=event["source_row_index"],  # type: ignore[arg-type]
        )["payload_hash"]
    return event


def test_market_journal_writer_preserves_file_order_and_replays_deterministically(tmp_path: Path) -> None:
    journal_path = tmp_path / "binance_market.jsonl"
    writer = MarketJournalWriter(journal_path)

    writer.append(
        raw_payload={"e": "aggTrade", "s": "BTCUSDT", "a": 11, "T": 2_000},
        normalized_payload={"source_name": "binance_um_futures", "symbol": "BTCUSDT", "data_family": "agg_trade"},
        source_event_time_ms=2_000,
        local_receive_time_ms=None,
        source_name="binance_um_futures",
        symbol="BTCUSDT",
        data_family="agg_trade",
        sequence=11,
    )
    writer.append(
        raw_payload={"e": "aggTrade", "s": "BTCUSDT", "a": 10, "T": 1_000},
        normalized_payload={"source_name": "binance_um_futures", "symbol": "BTCUSDT", "data_family": "agg_trade"},
        source_event_time_ms=1_000,
        local_receive_time_ms=1_010,
        source_name="binance_um_futures",
        symbol="BTCUSDT",
        data_family="agg_trade",
        sequence=10,
    )
    writer.append(
        raw_payload={"e": "aggTrade", "s": "BTCUSDT", "a": 9, "T": 1_000},
        normalized_payload={"source_name": "binance_um_futures", "symbol": "BTCUSDT", "data_family": "agg_trade"},
        source_event_time_ms=1_000,
        local_receive_time_ms=1_015,
        source_name="binance_um_futures",
        symbol="BTCUSDT",
        data_family="agg_trade",
        sequence=9,
    )
    manifest = writer.write_manifest()

    file_order = read_market_journal_events(journal_path)
    replay_order = read_market_journal_for_replay(journal_path)

    assert [event["raw_payload"]["a"] for event in file_order] == [11, 10, 9]
    assert [event["raw_payload"]["a"] for event in replay_order] == [9, 10, 11]
    assert [event["source_row_index"] for event in file_order] == [0, 1, 2]
    assert all(event["schema_version"] == MARKET_JOURNAL_SCHEMA_VERSION for event in file_order)
    assert all(str(event["payload_hash"]).startswith("sha256:") for event in file_order)
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["intended_use"] == "research_observe_only"
    assert manifest["live_signal_input"] is False
    assert manifest["position_sizing_input"] is False
    assert manifest["event_count"] == 3
    assert manifest["event_counts_by_symbol"] == {"BTCUSDT": 3}
    assert manifest["event_counts_by_family"] == {"agg_trade": 3}
    assert manifest["first_source_event_time_ms"] == 1_000
    assert manifest["last_source_event_time_ms"] == 2_000


def test_market_journal_validation_rejects_missing_source_time_and_symbol_source_mismatch() -> None:
    missing_time = _agg_trade_event()
    missing_time.pop("source_event_time_ms")

    with pytest.raises(MarketJournalValidationError, match="source_event_time_ms_required"):
        validate_market_journal_event(missing_time)

    mismatch = _agg_trade_event()
    mismatch["normalized_payload"] = {
        "source_name": "other_source",
        "symbol": "ETHUSDT",
        "data_family": "agg_trade",
    }
    with pytest.raises(MarketJournalValidationError, match="symbol_mismatch"):
        validate_market_journal_event(mismatch)


def test_market_journal_validation_reports_duplicate_hashes_and_sequence_gaps() -> None:
    first = _agg_trade_event(sequence=1, source_row_index=0)
    gap = _agg_trade_event(
        raw_payload={"e": "aggTrade", "s": "BTCUSDT", "a": 3, "T": 3_000},
        normalized_payload={
            "source_name": "binance_um_futures",
            "symbol": "BTCUSDT",
            "data_family": "agg_trade",
            "aggregate_trade_id": 3,
        },
        source_event_time_ms=3_000,
        sequence=3,
        source_row_index=1,
    )
    duplicate = dict(gap)
    duplicate["source_row_index"] = 2

    report = validate_market_journal_events([first, gap, duplicate], strict=False)

    assert report["valid"] is False
    assert report["duplicate_hashes"] == [gap["payload_hash"]]
    assert report["sequence_gaps"] == [
        {
            "source_name": "binance_um_futures",
            "symbol": "BTCUSDT",
            "data_family": "agg_trade",
            "previous_sequence": 1,
            "next_sequence": 3,
            "missing_sequence_count": 1,
        }
    ]
    with pytest.raises(MarketJournalValidationError, match="duplicate_payload_hashes"):
        validate_market_journal_events([first, gap, duplicate], strict=True)


def test_market_journal_replay_validates_manifest_hash(tmp_path: Path) -> None:
    journal_path = tmp_path / "binance_market.jsonl"
    writer = MarketJournalWriter(journal_path)
    writer.append(
        raw_payload={"e": "trade", "s": "BTCUSDT", "t": 1, "T": 1_000},
        normalized_payload={"source_name": "binance_um_futures", "symbol": "BTCUSDT", "data_family": "trade"},
        source_event_time_ms=1_000,
        local_receive_time_ms=1_005,
        source_name="binance_um_futures",
        symbol="BTCUSDT",
        data_family="trade",
        sequence=1,
    )
    writer.write_manifest(strict=True)

    with journal_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps({"tampered": True}) + "\n")

    with pytest.raises(MarketJournalValidationError, match="journal hash mismatch"):
        read_market_journal_for_replay(journal_path)
