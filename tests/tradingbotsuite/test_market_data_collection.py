from __future__ import annotations

import builtins
import json
import sys
import urllib.error
import zipfile
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from tradingbotsuite.core.models import Bar
from tradingbotsuite.data.durable_public_archive import collect_candidate_depth_public_archive_fixtures
from tradingbotsuite.data.historical_data_catalog import (
    HISTORICAL_DATA_CATALOG_VERSION,
    normalize_operator_run_artifact_paths,
    read_historical_data_catalog,
    refresh_historical_data_catalog,
)
from tradingbotsuite.data.historical_fixture_pack import (
    assert_public_archive_fixture_ready,
    assert_valid_historical_fixture_pack_manifest,
)
from tradingbotsuite.research import market_data as market_data_module
from tradingbotsuite.research.market_data import (
    BinanceUsdMRestContextFetcher,
    MARKET_JOURNAL_SCHEMA_VERSION,
    MARKET_JOURNAL_WRITER_VERSION,
    MarketDataCollectionResult,
    MarketDataArchiveIngestionResult,
    CryptoLakeAccessError,
    MarketJournalValidationError,
    MarketJournalWriter,
    MarketDataGapError,
    MarketDataValidationError,
    binance_vision_archive_url,
    download_and_ingest_binance_vision_archive,
    download_binance_vision_archive,
    fetch_crypto_lake_archive,
    ingest_crypto_lake_archive,
    ingest_binance_vision_archive,
    read_market_journal,
    collect_binance_usdm_bars,
    collect_binance_usdm_context,
)
from tradingbotsuite.research.archive_sources import assert_valid_archive_source_manifest

REMOVED_CHART_SOURCE = "trading" + "view"


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


class FakeBinanceContextFetcher:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows
        self.calls: list[dict[str, object]] = []

    async def fetch_context_rows(
        self,
        *,
        symbol: str,
        data_family: str,
        start_time_ms: int,
        end_time_ms: int,
        interval: str,
    ) -> list[object]:
        self.calls.append(
            {
                "symbol": symbol,
                "data_family": data_family,
                "start_time_ms": start_time_ms,
                "end_time_ms": end_time_ms,
                "interval": interval,
            }
        )
        return self.rows


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


@pytest.mark.asyncio
async def test_collect_binance_usdm_context_writes_sorted_funding_manifest(tmp_path: Path) -> None:
    start = 1_712_649_600_000
    fetcher = FakeBinanceContextFetcher(
        [
            {"symbol": "BTCUSDT", "fundingRate": "0.0002", "fundingTime": start + 120_000, "markPrice": "101.5"},
            {"symbol": "BTCUSDT", "fundingRate": "0.0001", "fundingTime": start + 60_000, "markPrice": "100.5"},
        ]
    )

    first = await collect_binance_usdm_context(
        symbol="btcusdt",
        data_family="funding",
        start_time_ms=start,
        end_time_ms=start + 180_000,
        output_dir=tmp_path / "first",
        fetcher=fetcher,
    )
    second = await collect_binance_usdm_context(
        symbol="BTCUSDT",
        data_family="funding_rate",
        start_time_ms=start,
        end_time_ms=start + 180_000,
        output_dir=tmp_path / "second",
        fetcher=FakeBinanceContextFetcher(fetcher.rows),
    )

    assert fetcher.calls == [
        {
            "symbol": "BTCUSDT",
            "data_family": "funding_rate",
            "start_time_ms": start,
            "end_time_ms": start + 180_000,
            "interval": "5m",
        }
    ]
    assert first.content_hash == second.content_hash
    assert first.source_hash == second.source_hash
    rows = [json.loads(line) for line in first.data_path.read_text(encoding="utf-8").splitlines()]
    assert [row["event_time_ms"] for row in rows] == [start + 60_000, start + 120_000]
    assert rows[0]["source_name"] == "binance_usdm_rest"
    assert rows[0]["data_family"] == "funding_rate"
    assert rows[0]["funding_rate"] == "0.0001"
    assert rows[0]["funding_time_ms"] == start + 60_000

    manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["source_name"] == "binance_usdm_rest"
    assert manifest["source_type"] == "rest_backfill"
    assert manifest["data_family"] == "funding_rate"
    assert manifest["event_time_field"] == "event_time_ms"
    assert manifest["row_count"] == 2
    assert manifest["first_event_time_ms"] == start + 60_000
    assert manifest["last_event_time_ms"] == start + 120_000
    assert manifest["content_hash"] == first.content_hash
    assert manifest["collector_version"] == "binance-usdm-context-rest-v1"
    assert manifest["context_family_role"] == "perp_context"
    assert manifest["coverage_scope"] == "latest_window_backfill"
    assert manifest["latest_window_only"] is True
    assert manifest["retention_policy"]["claim"] == "not_multi_year_coverage"
    assert manifest["stream_health"]["status"] == "not_applicable_batch_backfill"
    assert "latest_window_only_context" in manifest["quality_flags"]
    assert "receive_time_unavailable_non_promotable" in manifest["quality_flags"]
    assert not any(REMOVED_CHART_SOURCE in str(note).lower() for note in manifest["non_promotable_notes"])
    assert any("No legacy chart export" in note for note in manifest["non_promotable_notes"])


@pytest.mark.asyncio
async def test_collect_binance_usdm_context_normalizes_premium_and_open_interest(tmp_path: Path) -> None:
    start = 1_712_649_600_000
    premium = await collect_binance_usdm_context(
        symbol="BTCUSDT",
        data_family="premium_index",
        interval="15m",
        start_time_ms=start,
        end_time_ms=start + 60_000,
        output_dir=tmp_path / "premium",
        fetcher=FakeBinanceContextFetcher(
            [
                [start + 60_000, "-0.0001", "0.0002", "-0.0002", "0.00015", "0", start + 119_999, "0", 1, "0", "0", "0"],
                {
                    "symbol": "BTCUSDT",
                    "event_time_ms": start,
                    "premium_index": "0.0001",
                    "mark_price": "101",
                    "index_price": "100",
                },
            ]
        ),
    )
    premium_rows = [json.loads(line) for line in premium.data_path.read_text(encoding="utf-8").splitlines()]
    assert [row["event_time_ms"] for row in premium_rows] == [start, start + 60_000]
    assert premium_rows[0]["premium_basis_rate"] == "0.0001"
    assert premium_rows[0]["mark_price"] == "101"
    assert premium_rows[0]["index_price"] == "100"
    assert premium_rows[1]["premium_index"] == "0.00015"

    open_interest = await collect_binance_usdm_context(
        symbol="ETHUSDT",
        data_family="open_interest",
        interval="5m",
        start_time_ms=start,
        end_time_ms=start + 60_000,
        output_dir=tmp_path / "oi",
        fetcher=FakeBinanceContextFetcher(
            [
                {
                    "symbol": "ETHUSDT",
                    "timestamp": str(start + 60_000),
                    "sumOpenInterest": "20403.63700000",
                    "sumOpenInterestValue": "150570784.07809979",
                }
            ]
        ),
    )
    oi_rows = [json.loads(line) for line in open_interest.data_path.read_text(encoding="utf-8").splitlines()]
    assert oi_rows == [
        {
            "data_family": "open_interest",
            "event_time_ms": start + 60_000,
            "open_interest": "20403.63700000",
            "open_interest_value": "150570784.07809979",
            "open_interest_value_usd": "150570784.07809979",
            "raw_payload": {
                "sumOpenInterest": "20403.63700000",
                "sumOpenInterestValue": "150570784.07809979",
                "symbol": "ETHUSDT",
                "timestamp": str(start + 60_000),
            },
            "source_name": "binance_usdm_rest",
            "source_row_index": 0,
            "symbol": "ETHUSDT",
        }
    ]


@pytest.mark.asyncio
async def test_collect_binance_usdm_context_detects_fixed_interval_gaps(tmp_path: Path) -> None:
    start = 1_712_649_600_000

    result = await collect_binance_usdm_context(
        symbol="BTCUSDT",
        data_family="premium_index",
        interval="15m",
        start_time_ms=start,
        end_time_ms=start + 30 * 60_000,
        output_dir=tmp_path / "premium-gap",
        fetcher=FakeBinanceContextFetcher(
            [
                [start, "-0.0001", "0.0002", "-0.0002", "0.00015"],
                [start + 30 * 60_000, "-0.0001", "0.0002", "-0.0002", "0.00016"],
            ]
        ),
    )
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert result.gap_count == 1
    assert manifest["context_family_role"] == "perp_context"
    assert manifest["coverage_scope"] == "latest_window_backfill"
    assert manifest["latest_window_only"] is True
    assert manifest["gap_check_applicable"] is True
    assert manifest["gap_check_status"] == "checked_fixed_interval"
    assert manifest["expected_interval_ms"] == 15 * 60_000
    assert manifest["gaps"] == [
        {
            "delta_ms": 30 * 60_000,
            "missing_event_count": 1,
            "next_event_time_ms": start + 30 * 60_000,
            "previous_event_time_ms": start,
        }
    ]

    strict_output_dir = tmp_path / "oi-gap"
    with pytest.raises(MarketDataGapError, match="manifest_path"):
        await collect_binance_usdm_context(
            symbol="BTCUSDT",
            data_family="open_interest",
            interval="15m",
            start_time_ms=start,
            end_time_ms=start + 30 * 60_000,
            output_dir=strict_output_dir,
            strict=True,
            fetcher=FakeBinanceContextFetcher(
                [
                    {"symbol": "BTCUSDT", "timestamp": str(start), "sumOpenInterest": "1"},
                    {"symbol": "BTCUSDT", "timestamp": str(start + 30 * 60_000), "sumOpenInterest": "2"},
                ]
            ),
        )
    strict_manifest_path = (
        strict_output_dir
        / "BTCUSDT"
        / "open_interest"
        / "15m"
        / f"BTCUSDT_open_interest_15m_{start}_{start + 30 * 60_000}.manifest.json"
    )
    strict_manifest = json.loads(strict_manifest_path.read_text(encoding="utf-8"))
    assert strict_manifest["gap_count"] == 1
    assert strict_manifest["coverage_scope"] == "latest_window_backfill"


def test_binance_usdm_open_interest_fetcher_pages_backward_with_bounded_endpoint_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    interval_ms = 15 * 60 * 1000
    start = 1_775_574_000_000
    row_count = 672
    event_times = [start + (index * interval_ms) for index in range(row_count)]
    calls: list[dict[str, int]] = []

    def fake_fetch_json(url: str, *, timeout_seconds: float) -> list[dict[str, str]]:
        del timeout_seconds
        from urllib.parse import parse_qs, urlparse

        query = parse_qs(urlparse(url).query)
        call = {
            "startTime": int(query["startTime"][0]),
            "endTime": int(query["endTime"][0]),
            "limit": int(query["limit"][0]),
        }
        calls.append(call)
        available = [time_ms for time_ms in event_times if call["startTime"] <= time_ms <= call["endTime"]]
        page = available[-call["limit"] :]
        return [
            {
                "symbol": "BTCUSDT",
                "sumOpenInterest": str(100_000 + index),
                "sumOpenInterestValue": str(1_000_000 + index),
                "timestamp": str(time_ms),
            }
            for index, time_ms in enumerate(page)
        ]

    monkeypatch.setattr("tradingbotsuite.research.market_data._fetch_json", fake_fetch_json)

    fetcher = BinanceUsdMRestContextFetcher(base_url="https://example.test")
    rows = fetcher._fetch_context_rows_sync(
        symbol="BTCUSDT",
        data_family="open_interest",
        start_time_ms=start,
        end_time_ms=event_times[-1],
        interval="15m",
    )

    assert len(rows) == row_count
    assert len(calls) == 2
    assert calls[0] == {"startTime": event_times[172], "endTime": event_times[-1], "limit": 500}
    assert calls[1] == {"startTime": start, "endTime": event_times[171], "limit": 500}
    assert all(call["endTime"] - call["startTime"] <= 499 * interval_ms for call in calls)
    assert {int(row["timestamp"]) for row in rows} == set(event_times)


@pytest.mark.asyncio
async def test_collect_binance_usdm_context_rejects_inputs_and_strict_duplicates(tmp_path: Path) -> None:
    start = 1_712_649_600_000
    with pytest.raises(ValueError, match="binance context data_family must be one of"):
        await collect_binance_usdm_context(
            symbol="BTCUSDT",
            data_family="trade",
            start_time_ms=0,
            end_time_ms=60_000,
            output_dir=tmp_path,
            fetcher=FakeBinanceContextFetcher([]),
        )

    with pytest.raises(ValueError, match="open_interest period must be one of"):
        await collect_binance_usdm_context(
            symbol="BTCUSDT",
            data_family="open_interest",
            interval="1m",
            start_time_ms=0,
            end_time_ms=60_000,
            output_dir=tmp_path,
            fetcher=FakeBinanceContextFetcher([]),
        )

    with pytest.raises(MarketDataGapError, match="duplicate events"):
        await collect_binance_usdm_context(
            symbol="BTCUSDT",
            data_family="funding_rate",
            start_time_ms=start,
            end_time_ms=start + 60_000,
            output_dir=tmp_path,
            strict=True,
            fetcher=FakeBinanceContextFetcher(
                [
                    {"symbol": "BTCUSDT", "fundingRate": "0.0001", "fundingTime": start + 60_000},
                    {"symbol": "BTCUSDT", "fundingRate": "0.0002", "fundingTime": start + 60_000},
                ]
            ),
        )


def test_collect_binance_bars_cli_parse_and_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from tradingbotsuite import main

    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(tmp_path))

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


def test_collect_binance_context_cli_parse_and_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from tradingbotsuite import main

    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(tmp_path))

    async def fake_collect_binance_usdm_context(**kwargs):
        assert kwargs == {
            "symbol": "BTCUSDT",
            "data_family": "open_interest",
            "start_time_ms": 1000,
            "end_time_ms": 2000,
            "interval": "15m",
            "output_dir": tmp_path,
            "strict": True,
        }
        return MarketDataArchiveIngestionResult(
            output_dir=tmp_path / "BTCUSDT" / "open_interest" / "15m",
            data_path=tmp_path / "BTCUSDT" / "open_interest" / "15m" / "context.jsonl",
            manifest_path=tmp_path / "BTCUSDT" / "open_interest" / "15m" / "context.manifest.json",
            row_count=2,
            gap_count=0,
            duplicate_count=0,
            content_hash="sha256:content",
            source_hash="sha256:source",
        )

    monkeypatch.setattr(main, "collect_binance_usdm_context", fake_collect_binance_usdm_context)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "tradingbot",
            "collect-binance-context",
            "--symbol",
            "BTCUSDT",
            "--data-family",
            "open_interest",
            "--start-time-ms",
            "1000",
            "--end-time-ms",
            "2000",
            "--interval",
            "15m",
            "--output-dir",
            str(tmp_path),
            "--strict",
        ],
    )

    args = main.parse_args()
    payload = main._run_collect_binance_context_command(args)

    assert payload == {
        "output_dir": str(tmp_path / "BTCUSDT" / "open_interest" / "15m"),
        "data_path": str(tmp_path / "BTCUSDT" / "open_interest" / "15m" / "context.jsonl"),
        "manifest_path": str(tmp_path / "BTCUSDT" / "open_interest" / "15m" / "context.manifest.json"),
        "row_count": 2,
        "gap_count": 0,
        "duplicate_count": 0,
        "content_hash": "sha256:content",
        "source_hash": "sha256:source",
    }


def test_fetch_market_data_cli_parse_and_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from tradingbotsuite import main

    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(tmp_path))

    class Result:
        output_dir = tmp_path / "out"
        data_path = tmp_path / "out" / "data.jsonl"
        manifest_path = tmp_path / "out" / "manifest.json"
        row_count = 2
        gap_count = 0
        duplicate_count = 0
        content_hash = "sha256:content"
        source_hash = "sha256:source"

    captured: dict[str, object] = {}

    def fake_crypto_lake_archive(path, **kwargs):
        captured["path"] = path
        captured.update(kwargs)
        return Result()

    monkeypatch.setattr(main, "ingest_crypto_lake_archive", fake_crypto_lake_archive)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "tradingbot",
            "fetch-crypto-lake",
            "--symbol",
            "BTCUSDT",
            "--data-family",
            "liquidation",
            "--path",
            str(tmp_path / "crypto.csv"),
            "--provider-symbol",
            "BTC-USDT-PERP",
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    args = main.parse_args()
    payload = main._run_fetch_crypto_lake_command(args)

    assert captured["path"] == tmp_path / "crypto.csv"
    assert captured["symbol"] == "BTCUSDT"
    assert captured["data_family"] == "liquidation"
    assert captured["interval"] is None
    assert captured["provider_symbol"] == "BTC-USDT-PERP"
    assert payload["manifest_path"] == str(tmp_path / "out" / "manifest.json")


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
    assert manifest["gap_check_applicable"] is False
    assert manifest["gap_check_status"] == "not_applicable_variable_cadence"
    assert manifest["expected_interval_ms"] is None
    assert manifest["duplicate_count"] == 1
    assert manifest["duplicate_event_id_field"] == "aggregate_trade_id"
    assert manifest["duplicates"] == [7]


def test_download_binance_vision_archive_verifies_checksum_and_can_ingest(tmp_path: Path) -> None:
    csv_payload = "\n".join(
        [
            "open_time,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,"
            "taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore",
            "0,100,101,99,100.5,1,59999,100,10,0.5,50,0",
        ]
    )
    zip_bytes = __import__("io").BytesIO()
    with zipfile.ZipFile(zip_bytes, "w") as archive:
        archive.writestr("BTCUSDT-1m-2024-01-01.csv", csv_payload)
    payload = zip_bytes.getvalue()
    sha256 = __import__("hashlib").sha256(payload).hexdigest()
    urls: list[str] = []

    def fake_fetch(url: str) -> bytes:
        urls.append(url)
        if url.endswith(".CHECKSUM"):
            return f"{sha256}  BTCUSDT-1m-2024-01-01.zip\n".encode("utf-8")
        return payload

    assert binance_vision_archive_url(
        symbol="BTCUSDT",
        data_family="kline",
        interval="1m",
        period="2024-01-01",
    ).endswith("/data/futures/um/daily/klines/BTCUSDT/1m/BTCUSDT-1m-2024-01-01.zip")

    download = download_binance_vision_archive(
        symbol="BTCUSDT",
        data_family="kline",
        interval="1m",
        period="2024-01-01",
        output_dir=tmp_path / "downloads",
        fetcher=fake_fetch,
    )
    assert download.verified is True
    assert download.sha256 == f"sha256:{sha256}"
    assert download.output_path.exists()
    assert download.checksum_path is not None and download.checksum_path.exists()
    assert len(urls) == 2

    result = download_and_ingest_binance_vision_archive(
        symbol="BTCUSDT",
        data_family="kline",
        interval="1m",
        period="2024-01-01",
        output_dir=tmp_path / "ingested",
        fetcher=fake_fetch,
    )
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert_valid_archive_source_manifest(manifest)
    assert manifest["source_name"] == "binance_vision"
    assert manifest["row_count"] == 1
    assert result.row_count == 1


def test_download_binance_vision_archive_retries_transient_fetch_errors(tmp_path: Path) -> None:
    csv_payload = "\n".join(
        [
            "open_time,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,"
            "taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore",
            "0,100,101,99,100.5,1,59999,100,10,0.5,50,0",
        ]
    )
    zip_bytes = __import__("io").BytesIO()
    with zipfile.ZipFile(zip_bytes, "w") as archive:
        archive.writestr("BTCUSDT-1m-2024-01-01.csv", csv_payload)
    payload = zip_bytes.getvalue()
    sha256 = __import__("hashlib").sha256(payload).hexdigest()
    attempts: dict[str, int] = {}

    def fake_fetch(url: str) -> bytes:
        attempts[url] = attempts.get(url, 0) + 1
        if attempts[url] == 1:
            raise urllib.error.URLError("[Errno 11001] getaddrinfo failed")
        if url.endswith(".CHECKSUM"):
            return f"{sha256}  BTCUSDT-1m-2024-01-01.zip\n".encode("utf-8")
        return payload

    download = download_binance_vision_archive(
        symbol="BTCUSDT",
        data_family="kline",
        interval="1m",
        period="2024-01-01",
        output_dir=tmp_path / "downloads",
        fetcher=fake_fetch,
        max_fetch_attempts=3,
        fetch_retry_backoff_seconds=0,
    )

    assert download.verified is True
    assert download.archive_fetch_attempts == 2
    assert download.checksum_fetch_attempts == 2
    assert download.fetch_retry_count == 2
    manifest = json.loads(download.output_path.with_name(f"{download.output_path.name}.download_manifest.json").read_text(encoding="utf-8"))
    assert manifest["fetch_retry_count"] == 2


def test_download_binance_vision_archive_uses_env_retry_budget_with_capped_backoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csv_payload = "\n".join(
        [
            "open_time,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,"
            "taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore",
            "0,100,101,99,100.5,1,59999,100,10,0.5,50,0",
        ]
    )
    zip_bytes = __import__("io").BytesIO()
    with zipfile.ZipFile(zip_bytes, "w") as archive:
        archive.writestr("ETHUSDT-1m-2021-08.csv", csv_payload)
    payload = zip_bytes.getvalue()
    sha256 = __import__("hashlib").sha256(payload).hexdigest()
    attempts: dict[str, int] = {}
    sleeps: list[float] = []

    monkeypatch.setenv("TBS_BINANCE_VISION_DOWNLOAD_MAX_ATTEMPTS", "4")
    monkeypatch.setenv("TBS_BINANCE_VISION_DOWNLOAD_RETRY_BACKOFF_SECONDS", "1.5")
    monkeypatch.setenv("TBS_BINANCE_VISION_DOWNLOAD_RETRY_MAX_BACKOFF_SECONDS", "2.5")
    monkeypatch.setattr(market_data_module.time, "sleep", sleeps.append)

    def fake_fetch(url: str) -> bytes:
        attempts[url] = attempts.get(url, 0) + 1
        if not url.endswith(".CHECKSUM") and attempts[url] < 4:
            raise TimeoutError("temporary DNS outage")
        if url.endswith(".CHECKSUM"):
            return f"{sha256}  ETHUSDT-1m-2021-08.zip\n".encode("utf-8")
        return payload

    download = download_binance_vision_archive(
        symbol="ETHUSDT",
        data_family="kline",
        interval="1m",
        period="2021-08",
        cadence="monthly",
        output_dir=tmp_path / "downloads",
        fetcher=fake_fetch,
    )

    assert download.verified is True
    assert download.archive_fetch_attempts == 4
    assert download.checksum_fetch_attempts == 1
    assert download.fetch_retry_count == 3
    assert download.max_fetch_attempts == 4
    assert download.fetch_retry_backoff_seconds == pytest.approx(1.5)
    assert download.fetch_retry_max_backoff_seconds == pytest.approx(2.5)
    assert sleeps == pytest.approx([1.5, 2.5, 2.5])

    manifest = json.loads(
        download.output_path.with_name(f"{download.output_path.name}.download_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["max_fetch_attempts"] == 4
    assert manifest["fetch_retry_backoff_seconds"] == pytest.approx(1.5)
    assert manifest["fetch_retry_max_backoff_seconds"] == pytest.approx(2.5)


def test_download_binance_vision_archive_does_not_retry_checksum_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csv_payload = "\n".join(
        [
            "open_time,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,"
            "taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore",
            "0,100,101,99,100.5,1,59999,100,10,0.5,50,0",
        ]
    )
    zip_bytes = __import__("io").BytesIO()
    with zipfile.ZipFile(zip_bytes, "w") as archive:
        archive.writestr("BTCUSDT-1m-2024-01-01.csv", csv_payload)
    payload = zip_bytes.getvalue()
    attempts: dict[str, int] = {}
    sleeps: list[float] = []

    monkeypatch.setenv("TBS_BINANCE_VISION_DOWNLOAD_MAX_ATTEMPTS", "10")
    monkeypatch.setattr(market_data_module.time, "sleep", sleeps.append)

    def fake_fetch(url: str) -> bytes:
        attempts[url] = attempts.get(url, 0) + 1
        if url.endswith(".CHECKSUM"):
            return ("0" * 64 + "  BTCUSDT-1m-2024-01-01.zip\n").encode("utf-8")
        return payload

    with pytest.raises(MarketDataValidationError, match="checksum mismatch"):
        download_binance_vision_archive(
            symbol="BTCUSDT",
            data_family="kline",
            interval="1m",
            period="2024-01-01",
            output_dir=tmp_path / "downloads",
            fetcher=fake_fetch,
        )

    assert sum(attempts.values()) == 2
    assert sleeps == []


def test_collect_candidate_depth_public_archive_fixtures_writes_active_specs_with_checksum_evidence(tmp_path: Path) -> None:
    start_ms = 1_704_067_200_000

    def zip_payload(member_name: str, rows: list[str]) -> bytes:
        buffer = __import__("io").BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr(member_name, "\n".join(rows))
        return buffer.getvalue()

    payloads: dict[str, bytes] = {}

    def payload_for(url: str) -> bytes:
        if url.endswith(".CHECKSUM"):
            data = payload_for(url.removesuffix(".CHECKSUM"))
            digest = __import__("hashlib").sha256(data).hexdigest()
            return f"{digest}  {Path(url.removesuffix('.CHECKSUM')).name}\n".encode("utf-8")
        member = Path(url).name.replace(".zip", ".csv")
        if "/15m/" in url:
            return zip_payload(
                member,
                [
                    "open_time,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore",
                    f"{start_ms},100,101,99,100.5,1,{start_ms + 899999},100,10,0.5,50,0",
                    f"{start_ms + 900000},100.5,102,100,101.5,2,{start_ms + 1799999},203,11,1,102,0",
                ],
            )
        if "/1m/" in url:
            return zip_payload(
                member,
                [
                    "open_time,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore",
                    f"{start_ms},100,101,99,100.5,1,{start_ms + 59999},100,10,0.5,50,0",
                    f"{start_ms + 60000},100.5,102,100,101.5,2,{start_ms + 119999},203,11,1,102,0",
                ],
            )
        return zip_payload(
            member,
            [
                "aggregate_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker,is_best_match",
                f"1,100,3,1,1,{start_ms},false,true",
                f"2,100,1,2,2,{start_ms + 1000},true,true",
                f"3,101,2,3,3,{start_ms + 60000},true,true",
            ],
        )

    def fake_fetch(url: str) -> bytes:
        payloads.setdefault(url, payload_for(url))
        return payloads[url]

    result = collect_candidate_depth_public_archive_fixtures(
        output_dir=tmp_path / "durable",
        symbols=["BTCUSDT"],
        start_month="2024-01",
        end_month="2024-01",
        fetcher=fake_fetch,
        min_primary_15m_bars=2,
        min_context_1m_rows=2,
        min_effective_hours=0,
    )

    manifest_path = result.fixture_manifest_paths["BTCUSDT"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert_valid_historical_fixture_pack_manifest(manifest, manifest_path=manifest_path)
    assert_public_archive_fixture_ready(manifest, manifest_path=manifest_path)
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["families"]["bars"]["row_count"] == 2
    assert manifest["families"]["lower_timeframe_bars"]["row_count"] == 2
    assert manifest["families"]["agg_trade"]["row_count"] == 2
    assert all(item["checksum_verified"] is True for item in manifest["source"]["source_archive_downloads"])
    agg_frame = pd.read_parquet(manifest_path.parent / manifest["families"]["agg_trade"]["path"])
    first_agg = agg_frame.sort_values("event_time_ms").iloc[0]
    assert first_agg["primary_signed_imbalance_ratio"] == pytest.approx(0.5)
    assert first_agg["primary_sqrt_signed_imbalance_ratio"] == pytest.approx(0.5**0.5)

    readiness = json.loads(result.readiness_config_paths["BTCUSDT"].read_text(encoding="utf-8"))
    assert readiness["generated_candidate_depth_fixture"] is False
    assert readiness["fixture_manifest_sha256"].startswith("sha256:")
    assert readiness["candidate_depth_evidence"]["candidate_depth_thresholds_met"] is False
    assert readiness["candidate_depth_evidence"]["collection_acceptance_thresholds"]["primary_15m_bars"] == 2
    assert readiness["cycle_spec_path"] == str(result.cycle_spec_paths["BTCUSDT"])
    assert readiness["discovery_spec_path"] == str(result.discovery_spec_paths["BTCUSDT"])
    cycle_spec = json.loads(result.cycle_spec_paths["BTCUSDT"].read_text(encoding="utf-8"))
    discovery_spec = json.loads(result.discovery_spec_paths["BTCUSDT"].read_text(encoding="utf-8"))
    assert cycle_spec["data"]["dataset_manifest_paths"] == [str(manifest_path)]
    assert discovery_spec["data"]["dataset_manifest_paths"] == [str(manifest_path)]
    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert summary["symbols"]["BTCUSDT"]["candidate_depth_thresholds_met"] is False
    assert summary["symbols"]["BTCUSDT"]["collection_thresholds_met"] is True


def test_collect_candidate_depth_public_archive_fixtures_records_agg_trade_id_order_anomalies(tmp_path: Path) -> None:
    start_ms = 1_704_067_200_000

    def zip_payload(member_name: str, rows: list[str]) -> bytes:
        buffer = __import__("io").BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr(member_name, "\n".join(rows))
        return buffer.getvalue()

    payloads: dict[str, bytes] = {}

    def payload_for(url: str) -> bytes:
        if url.endswith(".CHECKSUM"):
            data = payload_for(url.removesuffix(".CHECKSUM"))
            digest = __import__("hashlib").sha256(data).hexdigest()
            return f"{digest}  {Path(url.removesuffix('.CHECKSUM')).name}\n".encode("utf-8")
        member = Path(url).name.replace(".zip", ".csv")
        if "/15m/" in url:
            return zip_payload(
                member,
                [
                    "open_time,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore",
                    f"{start_ms},100,101,99,100.5,1,{start_ms + 899999},100,10,0.5,50,0",
                    f"{start_ms + 900000},100.5,102,100,101.5,2,{start_ms + 1799999},203,11,1,102,0",
                ],
            )
        if "/1m/" in url:
            return zip_payload(
                member,
                [
                    "open_time,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore",
                    f"{start_ms},100,101,99,100.5,1,{start_ms + 59999},100,10,0.5,50,0",
                    f"{start_ms + 60000},100.5,102,100,101.5,2,{start_ms + 119999},203,11,1,102,0",
                ],
            )
        return zip_payload(
            member,
            [
                "aggregate_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker,is_best_match",
                f"2,100,3,1,1,{start_ms},false,true",
                f"1,101,2,2,2,{start_ms + 60000},true,true",
            ],
        )

    def fake_fetch(url: str) -> bytes:
        payloads.setdefault(url, payload_for(url))
        return payloads[url]

    result = collect_candidate_depth_public_archive_fixtures(
        output_dir=tmp_path / "durable",
        symbols=["BTCUSDT"],
        start_month="2024-01",
        end_month="2024-01",
        fetcher=fake_fetch,
        min_primary_15m_bars=2,
        min_context_1m_rows=2,
        min_effective_hours=0,
    )

    manifest = json.loads(result.fixture_manifest_paths["BTCUSDT"].read_text(encoding="utf-8"))
    agg_family = manifest["families"]["agg_trade"]
    assert agg_family["row_count"] == 2
    assert agg_family["source_selected_row_count"] == 2
    assert agg_family["duplicate_count"] == 0
    assert agg_family["duplicate_check_status"] == "not_checked_full_trade_id_set_memory_bounded"
    assert agg_family["agg_trade_id_order_anomaly_count"] == 1

    readiness = json.loads(result.readiness_config_paths["BTCUSDT"].read_text(encoding="utf-8"))
    assert readiness["required_context"]["agg_trade"]["agg_trade_id_order_anomaly_count"] == 1


def test_collect_candidate_depth_public_archive_fixtures_reuses_verified_cache_and_writes_progress(tmp_path: Path) -> None:
    start_ms = 1_704_067_200_000

    def zip_payload(member_name: str, rows: list[str]) -> bytes:
        buffer = __import__("io").BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr(member_name, "\n".join(rows))
        return buffer.getvalue()

    payloads: dict[str, bytes] = {}
    fetch_counts: dict[str, int] = {}

    def payload_for(url: str) -> bytes:
        if url.endswith(".CHECKSUM"):
            data = payload_for(url.removesuffix(".CHECKSUM"))
            digest = __import__("hashlib").sha256(data).hexdigest()
            return f"{digest}  {Path(url.removesuffix('.CHECKSUM')).name}\n".encode("utf-8")
        member = Path(url).name.replace(".zip", ".csv")
        if "/15m/" in url:
            return zip_payload(
                member,
                [
                    "open_time,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore",
                    f"{start_ms},100,101,99,100.5,1,{start_ms + 899999},100,10,0.5,50,0",
                    f"{start_ms + 900000},100.5,102,100,101.5,2,{start_ms + 1799999},203,11,1,102,0",
                ],
            )
        if "/1m/" in url:
            return zip_payload(
                member,
                [
                    "open_time,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore",
                    f"{start_ms},100,101,99,100.5,1,{start_ms + 59999},100,10,0.5,50,0",
                    f"{start_ms + 60000},100.5,102,100,101.5,2,{start_ms + 119999},203,11,1,102,0",
                ],
            )
        return zip_payload(
            member,
            [
                "aggregate_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker,is_best_match",
                f"1,100,3,1,1,{start_ms},false,true",
                f"2,101,2,2,2,{start_ms + 60000},true,true",
            ],
        )

    def fake_fetch(url: str) -> bytes:
        fetch_counts[url] = fetch_counts.get(url, 0) + 1
        payloads.setdefault(url, payload_for(url))
        return payloads[url]

    old_cache = tmp_path / "old_cache"
    collect_candidate_depth_public_archive_fixtures(
        output_dir=tmp_path / "first",
        symbols=["BTCUSDT"],
        start_month="2024-01",
        end_month="2024-01",
        fetcher=fake_fetch,
        download_cache_dir=old_cache,
        min_primary_15m_bars=2,
        min_context_1m_rows=2,
        min_effective_hours=0,
    )
    assert len(fetch_counts) == 6

    def fail_fetch(url: str) -> bytes:
        raise AssertionError(f"cache was not reused for {url}")

    result = collect_candidate_depth_public_archive_fixtures(
        output_dir=tmp_path / "second",
        symbols=["BTCUSDT"],
        start_month="2024-01",
        end_month="2024-01",
        fetcher=fail_fetch,
        download_cache_dir=tmp_path / "new_cache",
        download_fallback_dirs=[old_cache],
        min_primary_15m_bars=2,
        min_context_1m_rows=2,
        min_effective_hours=0,
    )

    progress = json.loads((result.output_dir / "collection_progress.json").read_text(encoding="utf-8"))
    assert progress["status"] == "complete"
    assert progress["completed_archive_steps"] == 3
    assert progress["total_archive_steps"] == 3
    assert progress["percent_complete"] == 100.0
    assert Path(progress["summary_path"]) == result.summary_path
    manifest = json.loads(result.fixture_manifest_paths["BTCUSDT"].read_text(encoding="utf-8"))
    assert manifest["families"]["agg_trade"]["source_selected_row_count"] == 2


def test_collect_candidate_depth_public_archive_fixtures_reuses_completed_symbol_fixture_pack(tmp_path: Path) -> None:
    start_ms = 1_704_067_200_000

    def zip_payload(member_name: str, rows: list[str]) -> bytes:
        buffer = __import__("io").BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr(member_name, "\n".join(rows))
        return buffer.getvalue()

    def payload_for(url: str) -> bytes:
        if url.endswith(".CHECKSUM"):
            data = payload_for(url.removesuffix(".CHECKSUM"))
            digest = __import__("hashlib").sha256(data).hexdigest()
            return f"{digest}  {Path(url.removesuffix('.CHECKSUM')).name}\n".encode("utf-8")
        member = Path(url).name.replace(".zip", ".csv")
        if "/15m/" in url:
            return zip_payload(
                member,
                [
                    "open_time,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore",
                    f"{start_ms},100,101,99,100.5,1,{start_ms + 899999},100,10,0.5,50,0",
                    f"{start_ms + 900000},100.5,102,100,101.5,2,{start_ms + 1799999},203,11,1,102,0",
                ],
            )
        if "/1m/" in url:
            return zip_payload(
                member,
                [
                    "open_time,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore",
                    f"{start_ms},100,101,99,100.5,1,{start_ms + 59999},100,10,0.5,50,0",
                    f"{start_ms + 60000},100.5,102,100,101.5,2,{start_ms + 119999},203,11,1,102,0",
                ],
            )
        return zip_payload(
            member,
            [
                "aggregate_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker,is_best_match",
                f"1,100,3,1,1,{start_ms},false,true",
                f"2,101,2,2,2,{start_ms + 60000},true,true",
            ],
        )

    first = collect_candidate_depth_public_archive_fixtures(
        output_dir=tmp_path / "first",
        symbols=["BTCUSDT"],
        start_month="2024-01",
        end_month="2024-01",
        fetcher=payload_for,
        min_primary_15m_bars=2,
        min_context_1m_rows=2,
        min_effective_hours=0,
    )

    def fail_fetch(url: str) -> bytes:
        raise AssertionError(f"completed fixture pack should have been reused before fetching {url}")

    second = collect_candidate_depth_public_archive_fixtures(
        output_dir=tmp_path / "second",
        symbols=["BTCUSDT"],
        start_month="2024-01",
        end_month="2024-01",
        fetcher=fail_fetch,
        fixture_fallback_dirs=[first.output_dir],
        min_primary_15m_bars=2,
        min_context_1m_rows=2,
        min_effective_hours=0,
    )

    payload = second.symbol_payloads["BTCUSDT"]
    assert payload["reused_fixture_pack"] is True
    assert Path(str(payload["reused_fixture_pack_source"])).name == "btcusdt_public_archive_candidate_depth_v1"
    progress = json.loads((second.output_dir / "collection_progress.json").read_text(encoding="utf-8"))
    assert progress["status"] == "complete"
    assert progress["completed_archive_steps"] == 3
    assert progress["current"]["reused_fixture_pack"] is True
    assert second.fixture_manifest_paths["BTCUSDT"].read_text(encoding="utf-8") == first.fixture_manifest_paths["BTCUSDT"].read_text(encoding="utf-8")


def test_refresh_historical_data_catalog_records_provider_states_and_active_fixture_paths(tmp_path: Path) -> None:
    start_ms = 1_704_067_200_000

    def zip_payload(member_name: str, rows: list[str]) -> bytes:
        buffer = __import__("io").BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr(member_name, "\n".join(rows))
        return buffer.getvalue()

    def payload_for(url: str) -> bytes:
        if url.endswith(".CHECKSUM"):
            data = payload_for(url.removesuffix(".CHECKSUM"))
            digest = __import__("hashlib").sha256(data).hexdigest()
            return f"{digest}  {Path(url.removesuffix('.CHECKSUM')).name}\n".encode("utf-8")
        member = Path(url).name.replace(".zip", ".csv")
        if "/15m/" in url:
            return zip_payload(
                member,
                [
                    "open_time,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore",
                    f"{start_ms},100,101,99,100.5,1,{start_ms + 899999},100,10,0.5,50,0",
                    f"{start_ms + 900000},100.5,102,100,101.5,2,{start_ms + 1799999},203,11,1,102,0",
                ],
            )
        if "/1m/" in url:
            return zip_payload(
                member,
                [
                    "open_time,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore",
                    f"{start_ms},100,101,99,100.5,1,{start_ms + 59999},100,10,0.5,50,0",
                    f"{start_ms + 60000},100.5,102,100,101.5,2,{start_ms + 119999},203,11,1,102,0",
                ],
            )
        return zip_payload(
            member,
            [
                "aggregate_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker,is_best_match",
                f"1,100,3,1,1,{start_ms},false,true",
                f"2,101,2,2,2,{start_ms + 60000},true,true",
            ],
        )

    result = refresh_historical_data_catalog(
        output_dir=tmp_path / "catalog",
        symbols=["BTCUSDT"],
        start_month="2024-01",
        end_month="2024-01",
        fetcher=payload_for,
        min_primary_15m_bars=2,
        min_context_1m_rows=2,
        min_effective_hours=0,
    )

    catalog = json.loads(result.catalog_path.read_text(encoding="utf-8"))
    assert catalog["historical_data_catalog_version"] == HISTORICAL_DATA_CATALOG_VERSION
    assert catalog["stage"] == "R106"
    assert catalog["research_only"] is True
    assert catalog["observe_only"] is True
    assert catalog["promotion_ready"] is False
    assert catalog["catalog_ready"] is False
    assert catalog["symbols"]["BTCUSDT"]["fixture_valid"] is True
    assert catalog["symbols"]["BTCUSDT"]["candidate_depth_ready"] is False
    assert catalog["symbols"]["BTCUSDT"]["status"] == "fixture_valid_below_candidate_depth_floor"
    assert "fixture_manifest_path" in catalog["symbols"]["BTCUSDT"]
    assert Path(catalog["symbols"]["BTCUSDT"]["fixture_manifest_path"]).exists()
    provider_states = catalog["provider_states"]
    assert provider_states["binance_vision"]["catalog_state"] == "active_implemented_primary"
    assert provider_states["binance_vision"]["implemented_for_catalog_refresh"] is True
    assert provider_states["crypto_lake"]["catalog_state"] == "implemented_local_export_not_auto_collected"
    assert provider_states["bybit_archive"]["catalog_state"] == "public_archive_registered_ingestion_not_implemented"
    assert provider_states["hyperliquid_archive"]["catalog_state"] == "archive_registered_requester_pays_ingestion_not_implemented"
    assert result.catalog_sha256.startswith("sha256:")


def test_read_historical_data_catalog_rebases_migrated_operator_run_paths(tmp_path: Path) -> None:
    run_root = tmp_path / "research" / "operator_runs" / "historical_data" / "refresh-historical-data-catalog-test"
    source_root = run_root / "sources" / "binance_vision_public_archive"
    manifest_path = source_root / "fixture_packs" / "btcusdt_public_archive_candidate_depth_v1" / "fixture_pack_manifest.json"
    readiness_path = source_root / "active_readiness" / "durable_public_archive_fixture_readiness_btcusdt_candidate_depth_v1.json"
    cycle_spec_path = source_root / "active_specs" / "r105-btcusdt-durable-public-archive-candidate-depth-v1.json"
    discovery_spec_path = source_root / "active_specs" / "exact_entry_sweep_btcusdt_candidate_depth_v1.json"
    summary_path = source_root / "durable_fixture_collection_summary.json"
    profile_path = source_root / "modern_window_profiles" / "btcusdt_modern" / "modern_window_profile.json"
    dataset_path = profile_path.parent / "cycle_dataset.parquet"
    for path in (manifest_path, readiness_path, cycle_spec_path, discovery_spec_path, summary_path, profile_path, dataset_path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")

    stale_run_root = Path(r"C:\Users\papaa\Music\tradingbotsuite\data\research\operator_runs\historical_data") / run_root.name

    def stale(path: Path) -> str:
        return str(stale_run_root / path.relative_to(run_root))

    catalog_path = run_root / "historical_data_catalog.json"
    catalog_path.write_text(
        json.dumps(
            {
                "historical_data_catalog_version": HISTORICAL_DATA_CATALOG_VERSION,
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "active_source": {"source_summary_path": stale(summary_path)},
                "symbols": {
                    "BTCUSDT": {
                        "candidate_depth_ready": True,
                        "source_summary_path": stale(summary_path),
                        "fixture_manifest_path": stale(manifest_path),
                        "readiness_config_path": stale(readiness_path),
                        "cycle_spec_path": stale(cycle_spec_path),
                        "discovery_spec_path": stale(discovery_spec_path),
                        "modern_window_profile_count": 1,
                        "modern_window_profiles": {
                            "modern": {
                                "profile_manifest_path": stale(profile_path),
                                "dataset_path": stale(dataset_path),
                            }
                        },
                        "research_only": True,
                        "observe_only": True,
                        "promotion_ready": False,
                    }
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    catalog = read_historical_data_catalog(catalog_path)

    assert catalog["path_portability"]["migrated_absolute_paths_rebased"] is True
    assert catalog["active_source"]["source_summary_path"] == str(summary_path.resolve())
    symbol_payload = catalog["symbols"]["BTCUSDT"]
    assert symbol_payload["fixture_manifest_path"] == str(manifest_path.resolve())
    assert symbol_payload["cycle_spec_path"] == str(cycle_spec_path.resolve())
    assert symbol_payload["discovery_spec_path"] == str(discovery_spec_path.resolve())
    assert symbol_payload["modern_window_profiles"]["modern"]["profile_manifest_path"] == str(profile_path.resolve())
    assert symbol_payload["modern_window_profiles"]["modern"]["dataset_path"] == str(dataset_path.resolve())


def test_operator_run_path_normalizer_rebases_repo_relative_old_root_paths() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    artifact_path = repo_root / "data" / "research" / "operator_runs" / "analysis" / "unit" / "research_analysis.json"
    payload = {
        "cycle": {
            "data_window": {
                "dataset_path": r"C:\Users\papaa\Music\tradingbotsuite\data\research\fixtures\btcusdt_public_archive_multi_window_v1\cycle_dataset.parquet",
            }
        },
        "feature_column_set_evidence": {
            "manifest_path": r"C:\Users\papaa\Music\tradingbotsuite\configs\discovery\feature_column_sets_v4.json",
        },
        "resolved_paths": {
            "repo_root": r"C:\Users\papaa\Music\tradingbotsuite",
        },
    }

    normalized = normalize_operator_run_artifact_paths(payload, artifact_path=artifact_path, anchor_root=artifact_path.parent)

    assert normalized["cycle"]["data_window"]["dataset_path"] == str(
        (repo_root / "data" / "research" / "fixtures" / "btcusdt_public_archive_multi_window_v1" / "cycle_dataset.parquet").resolve()
    )
    assert normalized["feature_column_set_evidence"]["manifest_path"] == str(
        (repo_root / "configs" / "discovery" / "feature_column_sets_v4.json").resolve()
    )
    assert normalized["resolved_paths"]["repo_root"] == str(repo_root.resolve())


def test_collect_candidate_depth_public_archive_fixtures_rejects_duplicate_source_bars(tmp_path: Path) -> None:
    start_ms = 1_704_067_200_000

    def zip_payload(member_name: str, rows: list[str]) -> bytes:
        buffer = __import__("io").BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr(member_name, "\n".join(rows))
        return buffer.getvalue()

    def payload_for(url: str) -> bytes:
        if url.endswith(".CHECKSUM"):
            data = payload_for(url.removesuffix(".CHECKSUM"))
            digest = __import__("hashlib").sha256(data).hexdigest()
            return f"{digest}  {Path(url.removesuffix('.CHECKSUM')).name}\n".encode("utf-8")
        member = Path(url).name.replace(".zip", ".csv")
        header = "open_time,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore"
        if "/15m/" in url:
            return zip_payload(
                member,
                [
                    header,
                    f"{start_ms},100,101,99,100.5,1,{start_ms + 899999},100,10,0.5,50,0",
                    f"{start_ms},100,101,99,100.5,1,{start_ms + 899999},100,10,0.5,50,0",
                ],
            )
        if "/1m/" in url:
            return zip_payload(
                member,
                [
                    header,
                    f"{start_ms},100,101,99,100.5,1,{start_ms + 59999},100,10,0.5,50,0",
                ],
            )
        return zip_payload(
            member,
            [
                "aggregate_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker,is_best_match",
                f"1,100,1,1,1,{start_ms},false,true",
            ],
        )

    with pytest.raises(ValueError, match="primary_bar_archive_quality_failed"):
        collect_candidate_depth_public_archive_fixtures(
            output_dir=tmp_path / "durable",
            symbols=["BTCUSDT"],
            start_month="2024-01",
            end_month="2024-01",
            fetcher=payload_for,
            min_primary_15m_bars=1,
            min_context_1m_rows=1,
            min_effective_hours=0,
        )


def test_ingest_crypto_lake_kline_csv_writes_archive_manifest(tmp_path: Path) -> None:
    source_path = tmp_path / "crypto_lake_candles.csv"
    source_path.write_text(
        "\n".join(
            [
                "origin_time,exchange,symbol,open,high,low,close,volume,quote_volume,received_time",
                "2024-01-01T00:00:00+00:00,BINANCE,BTC-USDT-PERP,100,101,99,100.5,10,1000,2024-01-01T00:00:01+00:00",
                "2024-01-01T00:01:00+00:00,BINANCE,BTC-USDT-PERP,100.5,102,100,101.5,12,1200,2024-01-01T00:01:01+00:00",
            ]
        ),
        encoding="utf-8",
    )

    result = ingest_crypto_lake_archive(
        source_path,
        symbol="BTCUSDT",
        provider_symbol="BTC-USDT-PERP",
        data_family="kline",
        interval="1m",
        output_dir=tmp_path / "out",
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    validation = assert_valid_archive_source_manifest(manifest)
    rows = [json.loads(line) for line in result.data_path.read_text(encoding="utf-8").splitlines()]

    assert result.row_count == 2
    assert result.gap_count == 0
    assert manifest["source_name"] == "crypto_lake"
    assert manifest["source_type"] == "commercial_archive"
    assert manifest["receive_time_field"] == "receive_time_ms"
    assert manifest["provider_symbol"] == "BTC-USDT-PERP"
    assert "provider_symbol_differs_from_symbol" in validation.quality_flags
    assert [row["event_time_ms"] for row in rows] == [1704067200000, 1704067260000]
    assert rows[0]["receive_time_ms"] == 1704067201000


def test_ingest_crypto_lake_context_reports_symbol_time_duplicates_and_gaps(tmp_path: Path) -> None:
    source_path = tmp_path / "crypto_lake_open_interest.csv"
    source_path.write_text(
        "\n".join(
            [
                "origin_time,exchange,symbol,open_interest",
                "2024-01-01T00:00:00+00:00,BINANCE,BTC-USDT-PERP,100",
                "2024-01-01T00:30:00+00:00,BINANCE,BTC-USDT-PERP,110",
                "2024-01-01T00:30:00+00:00,BINANCE,BTC-USDT-PERP,111",
            ]
        ),
        encoding="utf-8",
    )

    result = ingest_crypto_lake_archive(
        source_path,
        symbol="BTCUSDT",
        provider_symbol="BTC-USDT-PERP",
        data_family="open_interest",
        interval="15m",
        output_dir=tmp_path / "out",
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["context_family_role"] == "perp_context"
    assert manifest["coverage_scope"] == "local_vendor_export"
    assert manifest["latest_window_only"] is False
    assert manifest["gap_check_applicable"] is True
    assert manifest["gap_count"] == 1
    assert manifest["duplicate_check_applicable"] is True
    assert manifest["duplicate_event_id_field"] == "symbol_event_time_ms"
    assert manifest["duplicate_count"] == 1
    assert manifest["duplicates"] == [{"event_time_ms": 1704069000000, "symbol": "BTCUSDT"}]


def test_ingest_crypto_lake_liquidation_csv_writes_context_manifest(tmp_path: Path) -> None:
    source_path = tmp_path / "crypto_lake_liquidations.csv"
    source_path.write_text(
        "\n".join(
            [
                "origin_time,received_time,exchange,symbol,side,price,quantity,average_price,order_status",
                "2024-01-01T00:00:00+00:00,2024-01-01T00:00:01+00:00,BINANCE,BTC-USDT-PERP,SELL,100.0,2.5,99.5,FILLED",
                "2024-01-01T00:00:00+00:00,2024-01-01T00:00:02+00:00,BINANCE,BTC-USDT-PERP,BUY,101.0,1.0,101.0,FILLED",
            ]
        ),
        encoding="utf-8",
    )

    result = ingest_crypto_lake_archive(
        source_path,
        symbol="BTCUSDT",
        provider_symbol="BTC-USDT-PERP",
        data_family="liquidation",
        output_dir=tmp_path / "out",
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    validation = assert_valid_archive_source_manifest(manifest)
    rows = [json.loads(line) for line in result.data_path.read_text(encoding="utf-8").splitlines()]

    assert result.row_count == 2
    assert result.duplicate_count == 0
    assert manifest["data_family"] == "liquidation"
    assert manifest["context_family_role"] == "perp_context"
    assert manifest["coverage_scope"] == "local_vendor_export"
    assert manifest["duplicate_check_applicable"] is False
    assert manifest["gap_check_status"] == "not_applicable_variable_cadence"
    assert validation.valid is True
    assert "perp_context_family" in manifest["quality_flags"]
    assert [row["side"] for row in rows] == ["SELL", "BUY"]
    assert rows[0]["price"] == "100.0"
    assert rows[0]["quantity"] == "2.5"
    assert rows[0]["receive_time_ms"] == 1704067201000


def test_fetch_crypto_lake_archive_uses_optional_lakeapi_module(tmp_path: Path) -> None:
    class FakeLakeApi:
        sample_data_enabled = False

        @classmethod
        def use_sample_data(cls, *, anonymous_access):
            assert anonymous_access is True
            cls.sample_data_enabled = True

        @staticmethod
        def load_data(**kwargs):
            assert kwargs["table"] == "candles"
            assert kwargs["start"].date().isoformat() == "2024-01-01"
            assert kwargs["end"].date().isoformat() == "2024-01-02"
            assert kwargs["symbols"] == ["BTC-USDT-PERP"]
            assert kwargs["exchanges"] == ["BINANCE"]
            return pd.DataFrame(
                [
                    {
                        "origin_time": "2024-01-01T00:00:00+00:00",
                        "received_time": "2024-01-01T00:00:01+00:00",
                        "exchange": "BINANCE",
                        "symbol": "BTC-USDT-PERP",
                        "open": "100",
                        "high": "101",
                        "low": "99",
                        "close": "100.5",
                        "volume": "10",
                    }
                ]
            )

    result = fetch_crypto_lake_archive(
        symbol="BTCUSDT",
        provider_symbol="BTC-USDT-PERP",
        data_family="kline",
        start_time="2024-01-01",
        end_time="2024-01-02",
        exchange="BINANCE",
        table="candles",
        interval="1m",
        output_dir=tmp_path / "out",
        lakeapi_module=FakeLakeApi(),
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert FakeLakeApi.sample_data_enabled is True
    assert result.row_count == 1
    assert manifest["source_name"] == "crypto_lake"
    assert manifest["provider_symbol"] == "BTC-USDT-PERP"
    assert manifest["source_access_mode"] == "free_sample"
    assert manifest["free_sample_data"] is True
    assert manifest["coverage_scope"] == "free_sample_diagnostic"
    assert manifest["latest_window_only"] is False
    assert manifest["retention_policy"]["claim"] == "sample_coverage_only"
    assert manifest["diagnostic_only"] is True
    assert "crypto_lake_free_sample_data" in manifest["quality_flags"]
    assert "free_sample_diagnostic_only" in manifest["quality_flags"]


def test_fetch_crypto_lake_archive_supports_liquidation_free_sample(tmp_path: Path) -> None:
    class FakeLakeApi:
        sample_data_enabled = False

        @classmethod
        def use_sample_data(cls, *, anonymous_access):
            assert anonymous_access is True
            cls.sample_data_enabled = True

        @staticmethod
        def load_data(**kwargs):
            assert kwargs["table"] == "liquidations"
            assert kwargs["symbols"] == ["BTC-USDT-PERP"]
            return pd.DataFrame(
                [
                    {
                        "origin_time": "2024-01-01T00:00:00+00:00",
                        "received_time": "2024-01-01T00:00:01+00:00",
                        "exchange": "BINANCE",
                        "symbol": "BTC-USDT-PERP",
                        "side": "SELL",
                        "price": "100.0",
                        "quantity": "2.5",
                    }
                ]
            )

    result = fetch_crypto_lake_archive(
        symbol="BTCUSDT",
        provider_symbol="BTC-USDT-PERP",
        data_family="liquidation",
        start_time="2024-01-01",
        end_time="2024-01-02",
        output_dir=tmp_path / "out",
        lakeapi_module=FakeLakeApi(),
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in result.data_path.read_text(encoding="utf-8").splitlines()]
    assert FakeLakeApi.sample_data_enabled is True
    assert manifest["data_family"] == "liquidation"
    assert manifest["source_access_mode"] == "free_sample"
    assert manifest["coverage_scope"] == "free_sample_diagnostic"
    assert rows[0]["side"] == "SELL"


def test_fetch_crypto_lake_archive_missing_lakeapi_has_setup_guidance(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "lakeapi":
            raise ModuleNotFoundError("No module named 'lakeapi'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(CryptoLakeAccessError, match="Crypto Lake free-data fallback fetch requires the optional lakeapi package"):
        fetch_crypto_lake_archive(
            symbol="BTCUSDT",
            data_family="trade",
            start_time="2024-01-01",
            end_time="2024-01-02",
            output_dir=tmp_path / "out",
        )


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
    assert manifest["schema_version"] == MARKET_JOURNAL_SCHEMA_VERSION
    assert manifest["writer_version"] == MARKET_JOURNAL_WRITER_VERSION
    assert manifest["journal_type"] == "binance_style_market_event_journal"
    assert manifest["event_count"] == 3
    assert manifest["event_counts_by_family"] == {"trade": 3}
    assert manifest["event_counts_by_symbol"] == {"BTCUSDT": 3}
    assert [(event["source_event_time_ms"], event["source_row_index"]) for event in replayed] == [
        (1_000, 0),
        (1_000, 1),
        (2_000, 0),
    ]
    assert all("local_receive_time_ms" in event for event in replayed)
    assert all("receive_time_ms" not in event for event in replayed)
    assert all(event["payload_hash"].startswith("sha256:") for event in replayed)

    with journal_path.open("a", encoding="utf-8") as handle:
        handle.write("{}\n")

    with pytest.raises(MarketJournalValidationError, match="journal hash mismatch"):
        read_market_journal(journal_path)
