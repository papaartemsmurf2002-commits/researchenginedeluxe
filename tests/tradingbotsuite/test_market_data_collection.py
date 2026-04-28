from __future__ import annotations

import json
import sys
import zipfile
from decimal import Decimal
from pathlib import Path

import pytest

from tradingbotsuite.core.models import Bar
from tradingbotsuite.research.market_data import (
    MarketDataCollectionResult,
    MarketJournalValidationError,
    MarketJournalWriter,
    MarketDataGapError,
    ingest_binance_vision_archive,
    read_market_journal,
    collect_binance_usdm_bars,
)
from tradingbotsuite.research.archive_sources import assert_valid_archive_source_manifest


class FakeHistoricalBinanceClient:
    def __init__(self, bars: list[Bar]) -> None:
        self.bars = bars
        self.calls: list[dict[str, object]] = []

    async def fetch_historical_closed_bar_range(
        self,
        symbol: str,
        *,
        start_time_ms: int,
        end_time_ms: int,
        interval: str = "15m",
    ) -> list[Bar]:
        self.calls.append(
            {
                "symbol": symbol,
                "start_time_ms": start_time_ms,
                "end_time_ms": end_time_ms,
                "interval": interval,
            }
        )
        return self.bars


def _bar(time_ms: int, close: str = "101") -> Bar:
    return Bar(
        time_ms=time_ms,
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal(close),
        volume=Decimal("12.5"),
    )


@pytest.mark.asyncio
async def test_collect_binance_usdm_bars_writes_jsonl_and_manifest(tmp_path: Path) -> None:
    client = FakeHistoricalBinanceClient([_bar(0), _bar(60_000, "102"), _bar(120_000, "103")])

    result = await collect_binance_usdm_bars(
        symbol="btcusdt",
        interval="1m",
        start_time_ms=0,
        end_time_ms=120_000,
        output_dir=tmp_path,
        client=client,
    )

    assert client.calls == [{"symbol": "BTCUSDT", "start_time_ms": 0, "end_time_ms": 120_000, "interval": "1m"}]
    assert result.output_dir == tmp_path / "BTCUSDT" / "1m"
    assert result.row_count == 3
    assert result.gap_count == 0
    assert result.duplicate_count == 0

    rows = [json.loads(line) for line in result.data_path.read_text(encoding="utf-8").splitlines()]
    assert rows == [
        {"close": "101", "high": "110", "low": "90", "open": "100", "time_ms": 0, "volume": "12.5"},
        {"close": "102", "high": "110", "low": "90", "open": "100", "time_ms": 60_000, "volume": "12.5"},
        {"close": "103", "high": "110", "low": "90", "open": "100", "time_ms": 120_000, "volume": "12.5"},
    ]

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["intended_use"] == "research_observe_only"
    assert manifest["live_signal_input"] is False
    assert manifest["position_sizing_input"] is False
    assert manifest["source"] == "binance_usdm_klines"
    assert manifest["symbol"] == "BTCUSDT"
    assert manifest["interval"] == "1m"
    assert manifest["start_time_ms"] == 0
    assert manifest["end_time_ms"] == 120_000
    assert manifest["row_count"] == 3
    assert manifest["first_time_ms"] == 0
    assert manifest["last_time_ms"] == 120_000
    assert manifest["gap_count"] == 0
    assert manifest["duplicate_count"] == 0
    assert len(manifest["sha256"]) == 64
    assert manifest["collector_version"] == "binance-usdm-chart-bars-v1"
    assert any("not executable venue data" in note for note in manifest["notes"])


@pytest.mark.asyncio
async def test_collect_binance_usdm_bars_records_gaps_and_strict_raises(tmp_path: Path) -> None:
    client = FakeHistoricalBinanceClient([_bar(0), _bar(120_000), _bar(120_000, "104")])

    with pytest.raises(MarketDataGapError):
        await collect_binance_usdm_bars(
            symbol="ETHUSDT",
            interval="1m",
            start_time_ms=0,
            end_time_ms=120_000,
            output_dir=tmp_path,
            strict=True,
            client=client,
        )

    manifest_path = tmp_path / "ETHUSDT" / "1m" / "ETHUSDT_1m_0_120000.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["gap_count"] == 1
    assert manifest["duplicate_count"] == 1
    assert manifest["gaps"] == [
        {"delta_ms": 120_000, "missing_bar_count": 1, "next_time_ms": 120_000, "previous_time_ms": 0}
    ]
    assert manifest["duplicates"] == [120_000]


@pytest.mark.asyncio
async def test_collect_binance_usdm_bars_rejects_unapproved_inputs(tmp_path: Path) -> None:
    client = FakeHistoricalBinanceClient([])

    with pytest.raises(ValueError, match="symbol must be one of"):
        await collect_binance_usdm_bars(
            symbol="SOLUSDT",
            interval="1m",
            start_time_ms=0,
            end_time_ms=60_000,
            output_dir=tmp_path,
            client=client,
        )

    with pytest.raises(ValueError, match="interval must be one of"):
        await collect_binance_usdm_bars(
            symbol="BTCUSDT",
            interval="2m",
            start_time_ms=0,
            end_time_ms=60_000,
            output_dir=tmp_path,
            client=client,
        )


def test_collect_binance_bars_cli_parse_and_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from tradingbotsuite import main

    async def fake_collect_binance_usdm_bars(**kwargs):
        assert kwargs == {
            "symbol": "ETHUSDT",
            "interval": "5m",
            "start_time_ms": 1000,
            "end_time_ms": 2000,
            "output_dir": tmp_path,
            "strict": True,
        }
        return MarketDataCollectionResult(
            output_dir=tmp_path / "ETHUSDT" / "5m",
            data_path=tmp_path / "ETHUSDT" / "5m" / "bars.jsonl",
            manifest_path=tmp_path / "ETHUSDT" / "5m" / "bars.manifest.json",
            row_count=2,
            gap_count=0,
            duplicate_count=0,
        )

    monkeypatch.setattr(main, "collect_binance_usdm_bars", fake_collect_binance_usdm_bars)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "tradingbot",
            "collect-binance-bars",
            "--symbol",
            "ETHUSDT",
            "--interval",
            "5m",
            "--start-time-ms",
            "1000",
            "--end-time-ms",
            "2000",
            "--output-dir",
            str(tmp_path),
            "--strict",
        ],
    )

    args = main.parse_args()
    payload = main._run_collect_binance_bars_command(args)

    assert payload == {
        "output_dir": str(tmp_path / "ETHUSDT" / "5m"),
        "data_path": str(tmp_path / "ETHUSDT" / "5m" / "bars.jsonl"),
        "manifest_path": str(tmp_path / "ETHUSDT" / "5m" / "bars.manifest.json"),
        "row_count": 2,
        "gap_count": 0,
        "duplicate_count": 0,
    }


def test_ingest_binance_vision_kline_csv_reports_gaps_duplicates_and_is_deterministic(tmp_path: Path) -> None:
    source_path = tmp_path / "BTCUSDT-1m-klines.csv"
    source_path.write_text(
        "\n".join(
            [
                "open_time,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,"
                "taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore",
                "120000,102,103,101,102.5,2,179999,205,20,1,102,0",
                "0,100,101,99,100.5,1,59999,100,10,0.5,50,0",
                "120000,102,103,101,102.6,3,179999,307,30,1.5,154,0",
            ]
        ),
        encoding="utf-8",
    )

    first = ingest_binance_vision_archive(
        source_path,
        symbol="BTCUSDT",
        data_family="kline",
        interval="1m",
        output_dir=tmp_path / "out1",
    )
    second = ingest_binance_vision_archive(
        source_path,
        symbol="BTCUSDT",
        data_family="kline",
        interval="1m",
        output_dir=tmp_path / "out2",
    )

    assert first.row_count == 3
    assert first.gap_count == 1
    assert first.duplicate_count == 1
    assert first.content_hash == second.content_hash
    assert first.source_hash == second.source_hash

    rows = [json.loads(line) for line in first.data_path.read_text(encoding="utf-8").splitlines()]
    assert [(row["event_time_ms"], row["source_row_index"]) for row in rows] == [(0, 1), (120_000, 0), (120_000, 2)]

    manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    assert_valid_archive_source_manifest(manifest)
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["intended_use"] == "research_observe_only"
    assert manifest["live_signal_input"] is False
    assert manifest["position_sizing_input"] is False
    assert manifest["source_name"] == "binance_vision"
    assert manifest["source_type"] == "public_archive"
    assert manifest["data_family"] == "kline"
    assert manifest["event_time_field"] == "open_time_ms"
    assert manifest["receive_time_unavailable_reason"]
    assert manifest["gap_count"] == 1
    assert manifest["duplicate_count"] == 1
    assert manifest["gaps"] == [
        {"delta_ms": 120_000, "missing_bar_count": 1, "next_time_ms": 120_000, "previous_time_ms": 0}
    ]
    assert manifest["duplicates"] == [120_000]
    assert manifest["content_hash"] == first.content_hash
    assert manifest["source_hash"] == first.source_hash
    assert manifest["ingestor_version"] == "binance-vision-local-ingestor-v1"
    assert any("not live-promotable" in note for note in manifest["non_promotable_notes"])


def test_ingest_binance_vision_agg_trade_zip_reports_duplicate_ids(tmp_path: Path) -> None:
    source_path = tmp_path / "BTCUSDT-aggTrades.zip"
    csv_payload = "\n".join(
        [
            "aggregate_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker,is_best_match",
            "7,100.0,0.10,70,71,3000,false,true",
            "6,99.5,0.20,68,69,1000,true,true",
            "7,100.1,0.15,72,73,2000,false,true",
        ]
    )
    with zipfile.ZipFile(source_path, "w") as archive:
        archive.writestr("BTCUSDT-aggTrades.csv", csv_payload)

    result = ingest_binance_vision_archive(
        source_path,
        symbol="BTCUSDT",
        data_family="agg_trade",
        output_dir=tmp_path / "out",
    )

    rows = [json.loads(line) for line in result.data_path.read_text(encoding="utf-8").splitlines()]
    assert [(row["event_time_ms"], row["source_row_index"], row["aggregate_trade_id"]) for row in rows] == [
        (1000, 1, 6),
        (2000, 2, 7),
        (3000, 0, 7),
    ]

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert_valid_archive_source_manifest(manifest)
    assert manifest["archive_member"] == "BTCUSDT-aggTrades.csv"
    assert manifest["data_family"] == "agg_trade"
    assert manifest["event_time_field"] == "transact_time_ms"
    assert manifest["gap_count"] == 0
    assert manifest["duplicate_count"] == 1
    assert manifest["duplicate_event_id_field"] == "aggregate_trade_id"
    assert manifest["duplicates"] == [7]


def test_market_journal_replay_is_deterministic_and_validates_manifest_hash(tmp_path: Path) -> None:
    journal_path = tmp_path / "market_journal.jsonl"
    writer = MarketJournalWriter(journal_path)

    writer.append(
        raw_payload={"id": "2", "time": "2000"},
        normalized_payload={"trade_id": 2, "price": "101"},
        source_event_time_ms=2_000,
        receive_time_ms=None,
        source_name="binance_vision",
        symbol="BTCUSDT",
        data_family="trade",
        source_row_index=0,
    )
    writer.append(
        raw_payload={"id": "1", "time": "1000"},
        normalized_payload={"trade_id": 1, "price": "100"},
        source_event_time_ms=1_000,
        receive_time_ms=None,
        source_name="binance_vision",
        symbol="BTCUSDT",
        data_family="trade",
        source_row_index=1,
    )
    writer.append(
        raw_payload={"id": "3", "time": "1000"},
        normalized_payload={"trade_id": 3, "price": "100.5"},
        source_event_time_ms=1_000,
        receive_time_ms=None,
        source_name="binance_vision",
        symbol="BTCUSDT",
        data_family="trade",
        source_row_index=0,
    )
    manifest = writer.write_manifest()

    replayed = read_market_journal(journal_path)

    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["intended_use"] == "research_observe_only"
    assert manifest["live_signal_input"] is False
    assert manifest["position_sizing_input"] is False
    assert manifest["event_count"] == 3
    assert manifest["event_counts_by_family"] == {"trade": 3}
    assert manifest["event_counts_by_symbol"] == {"BTCUSDT": 3}
    assert [(event["source_event_time_ms"], event["source_row_index"]) for event in replayed] == [
        (1_000, 0),
        (1_000, 1),
        (2_000, 0),
    ]
    assert all(event["payload_hash"].startswith("sha256:") for event in replayed)

    with journal_path.open("a", encoding="utf-8") as handle:
        handle.write("{}\n")

    with pytest.raises(MarketJournalValidationError, match="journal hash mismatch"):
        read_market_journal(journal_path)
