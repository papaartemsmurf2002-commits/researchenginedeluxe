from __future__ import annotations

import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from tradingbotsuite.config import AppConfig, ResearchConfig
from tradingbotsuite.core.models import Bar, RuntimeMode, SignalDirection, SignalIntent
from tradingbotsuite.persistence.sqlite_store import SQLiteStore
from tradingbotsuite.research.config import load_research_plan
from tradingbotsuite.research.dataset import ResearchDatasetBuilder
from tradingbotsuite.research.tradingview_import import import_tradingview_chart_export


def _write_chart_export(path: Path, rows: list[list[str]]) -> None:
    header = "time,open,high,low,close,Buy,Sell,StopBuy,StopSell,Shapes,Chars\n"
    body = "\n".join(",".join(row) for row in rows)
    path.write_text(header + body + "\n", encoding="utf-8")


@pytest.mark.asyncio
async def test_tradingview_chart_export_imports_current_btc_csv_shape(app_config, tmp_path) -> None:
    source_path = Path("BINANCE_BTCUSDT.P, 15 (2).csv")
    if not source_path.exists():
        pytest.skip("local TradingView chart export is not present")
    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "tv-import.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=app_config.research,
    )

    result = await import_tradingview_chart_export(
        config,
        path=source_path,
        symbol="BTCUSDT",
        strategy_version="kernel_v1",
        manifest_dir=tmp_path / "imports",
    )
    store = SQLiteStore(config.db_path)
    rows = await store.list_research_signals("BTCUSDT")
    first_five = rows[:5]
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert result.candidate_count == 1173
    assert result.imported_count == 1173
    assert result.buy_count == 565
    assert result.sell_count == 608
    assert manifest["source_mode"] == "chart_export"
    assert manifest["strategy_version"] == "kernel_v1"
    assert [(row["tv_bar_time_ms"], row["direction"]) for row in first_five] == [
        (1764594900000, "long"),
        (1764603000000, "short"),
        (1764610200000, "long"),
        (1764645300000, "short"),
        (1764647100000, "long"),
    ]
    assert first_five[0]["raw_payload"]["next_bar_open"] == "85953.3"
    assert first_five[1]["raw_payload"]["next_bar_open"] == "83920.5"
    assert first_five[0]["raw_payload"]["entry_price_source"] == "next_bar_open_plus_configured_slippage"

    second = await import_tradingview_chart_export(
        config,
        path=source_path,
        symbol="BTCUSDT",
        strategy_version="kernel_v1",
        manifest_dir=tmp_path / "imports",
    )
    rows_after_second = await store.list_research_signals("BTCUSDT")
    assert second.imported_count == 1173
    assert len(rows_after_second) == 1173

    third = await import_tradingview_chart_export(
        config,
        path=source_path,
        symbol="BTCUSDT",
        strategy_version="kernel_v2",
        manifest_dir=tmp_path / "imports",
    )
    rows_after_third = await store.list_research_signals("BTCUSDT")
    assert third.imported_count == 1173
    assert len(rows_after_third) == 2346


@pytest.mark.asyncio
async def test_tradingview_chart_export_skips_stops_ambiguous_and_missing_next_bar(app_config, tmp_path) -> None:
    source_path = tmp_path / "chart.csv"
    _write_chart_export(
        source_path,
        [
            ["1712649600", "100", "110", "90", "105", "", "", "99", "", "", ""],
            ["1712650500", "105", "112", "101", "108", "101", "112", "", "", "", ""],
            ["1712651400", "108", "115", "107", "114", "107", "", "", "", "", ""],
            ["1712652300", "114", "116", "110", "111", "", "116", "", "", "", ""],
        ],
    )
    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "tv-skip.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=app_config.research,
    )

    result = await import_tradingview_chart_export(
        config,
        path=source_path,
        symbol="BTCUSDT",
        strategy_version="skip_test",
        manifest_dir=tmp_path / "imports",
    )
    store = SQLiteStore(config.db_path)
    rows = await store.list_research_signals("BTCUSDT")
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert result.imported_count == 1
    assert result.skipped_count == 2
    assert manifest["skip_reasons"] == {
        "ambiguous_buy_and_sell": 1,
        "missing_next_bar": 1,
    }
    assert rows[0]["direction"] == "long"
    assert rows[0]["raw_payload"]["source_row_number"] == 4
    assert rows[0]["raw_payload"]["next_bar_open"] == "114"


@pytest.mark.asyncio
async def test_dataset_builder_uses_chart_export_normalized_entry_price(app_config, tmp_path) -> None:
    plan = load_research_plan(Path("configs/v2_btc_research.json"))
    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "tv-dataset.sqlite3",
        webhook=app_config.webhook,
        strategy=replace(app_config.strategy, hurst_window_bars=32, stale_bar_after_ms=10_000_000_000),
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=ResearchConfig(output_dir=tmp_path / "research", config_path=Path("configs/v2_btc_research.json")),
    )
    store = SQLiteStore(config.db_path)
    await store.initialize()

    bars: list[Bar] = []
    start_ms = 1712649600000
    price = Decimal("70000")
    for index in range(430):
        open_price = price
        close_price = price + Decimal("10")
        high = close_price + Decimal("20")
        low = open_price - Decimal("20")
        if index > 392:
            high = close_price + Decimal("500")
        bars.append(
            Bar(
                time_ms=start_ms + (index * 900_000),
                open=open_price,
                high=high,
                low=low,
                close=close_price,
                volume=Decimal("100"),
            )
        )
        price = close_price

    signal_bar = bars[390]
    signal = SignalIntent(
        signal_id="tv-chart:BTCUSDT:kernel_v1:test:1",
        source="tradingview_chart_export",
        symbol="BTCUSDT",
        direction=SignalDirection.LONG,
        tv_bar_time_ms=signal_bar.time_ms,
        received_time_ms=signal_bar.time_ms + 900_000,
        raw_payload={
            "source_mode": "chart_export",
            "strategy_version": "kernel_v1",
            "import_batch_id": "tv-chart:BTCUSDT:kernel_v1:test",
            "source_row_number": 392,
            "signal_marker_price": "73900",
            "next_bar_open": "73910",
            "normalized_entry_price": "73946.955",
            "entry_price_source": "next_bar_open_plus_configured_slippage",
            "import_time_ms": signal_bar.time_ms + 1,
        },
    )
    await store.reserve_signal(signal)

    class FakeResearchClient:
        async def fetch_historical_closed_bar_range(self, symbol: str, *, start_time_ms: int, end_time_ms: int, interval: str = "15m"):
            return [bar for bar in bars if start_time_ms <= bar.time_ms <= end_time_ms]

        async def fetch_historical_closed_bars(self, symbol: str, *, limit: int, end_time_ms: int | None = None, interval: str = "15m"):
            eligible = [bar for bar in bars if end_time_ms is None or (bar.time_ms + 899_999) <= end_time_ms]
            return eligible[-limit:]

        async def fetch_funding_context(self, symbol: str, *, as_of_ms: int, history_limit: int = 8):
            return {"funding_rate": "0.0001", "funding_rate_change": "0.00002", "time_to_next_funding_ms": 1_800_000}

        async def fetch_open_interest_context(self, symbol: str, *, as_of_ms: int, period: str = "5m", lookback_points: int = 13):
            return {"open_interest": "1000", "open_interest_change": "50", "open_interest_change_pct": "0.05", "open_interest_value": "70500000"}

        async def fetch_premium_context(self, symbol: str, *, as_of_ms: int, interval: str = "5m"):
            return {"basis_rate": "0.0003", "basis": "21", "premium_close": "0.0002"}

    result = await ResearchDatasetBuilder(
        config=config,
        plan=plan,
        store=store,
        candle_client=FakeResearchClient(),
    ).build()
    frame = pd.read_parquet(result.dataset_path)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert frame.iloc[0]["entry_price"] == pytest.approx(73946.955)
    assert frame.iloc[0]["entry_price_source"] == "next_bar_open_plus_configured_slippage"
    assert frame.iloc[0]["source_mode"] == "chart_export"
    assert frame.iloc[0]["strategy_version"] == "kernel_v1"
    assert frame.iloc[0]["import_batch_id"] == "tv-chart:BTCUSDT:kernel_v1:test"
    assert frame.iloc[0]["source_row_number"] == 392
    assert manifest["source_counts"] == {"tradingview_chart_export": 1}
    assert manifest["source_mode_counts"] == {"chart_export": 1}
    assert manifest["strategy_version_counts"] == {"kernel_v1": 1}
