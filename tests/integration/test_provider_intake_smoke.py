from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from tradingbotsuite.core.models import Bar
from tradingbotsuite.data.contracts import validate_data_manifest
from tradingbotsuite.data.providers.binance_rest import collect_binance_kline_intake


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


def _bar(time_ms: int, close: str) -> Bar:
    return Bar(
        time_ms=time_ms,
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal(close),
        volume=Decimal("12.5"),
    )


@pytest.mark.asyncio
async def test_binance_rest_kline_intake_writes_partitioned_parquet_manifest_and_quality(tmp_path: Path) -> None:
    client = FakeHistoricalBinanceClient([_bar(0, "101"), _bar(60_000, "102")])

    result = await collect_binance_kline_intake(
        symbol="btcusdt",
        interval="1m",
        start_time_ms=0,
        end_time_ms=60_000,
        output_dir=tmp_path,
        client=client,
    )

    assert client.calls == [
        {
            "symbol": "BTCUSDT",
            "start_time_ms": 0,
            "end_time_ms": 60_000,
            "interval": "1m",
        }
    ]
    assert result.row_count == 2
    assert result.data_path.parts[-5:] == (
        "source=binance_rest",
        "family=kline",
        "symbol=BTCUSDT",
        "date=1970-01-01",
        "part-000.parquet",
    )
    assert result.manifest_path.exists()
    assert result.data_quality_report_path.exists()

    frame = pd.read_parquet(result.data_path)
    assert list(frame["event_time_ms"]) == [0, 60_000]
    assert list(frame["close_price"]) == ["101", "102"]

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    validation = validate_data_manifest(manifest)
    assert validation.valid is True
    assert manifest["manifest_version"] == "data-manifest-v1"
    assert manifest["source_name"] == "binance_rest"
    assert manifest["source_type"] == "rest"
    assert manifest["data_family"] == "kline"
    assert manifest["row_count"] == 2
    assert manifest["receive_time_unavailable_reason"]
    assert manifest["content_hash"].startswith("sha256:")

    quality = json.loads(result.data_quality_report_path.read_text(encoding="utf-8"))
    assert quality["research_only"] is True
    assert quality["observe_only"] is True
    assert quality["promotion_ready"] is False
    assert quality["manifest_count"] == 1
    assert quality["source_counts"] == {"binance_rest": 1}
    assert quality["family_counts"] == {"kline": 1}
