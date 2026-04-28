from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from tradingbotsuite.core.models import Bar
from tradingbotsuite.research.market_data import (
    MarketDataCollectionResult,
    MarketDataGapError,
    collect_binance_usdm_bars,
)


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
