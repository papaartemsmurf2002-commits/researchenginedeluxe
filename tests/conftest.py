from __future__ import annotations

import asyncio
import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tradingbotsuite.config import AppConfig, BinanceConfig, HyperliquidConfig, StrategyConfig, WebhookConfig
from tradingbotsuite.core.models import Bar, RuntimeMode
from tradingbotsuite.web.app import create_app


if (
    sys.platform == "win32"
    and sys.version_info < (3, 14)
    and hasattr(asyncio, "WindowsSelectorEventLoopPolicy")
):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    if sys.platform != "win32":
        return

    indexed_items = list(enumerate(items))

    def _priority(indexed_item: tuple[int, pytest.Item]) -> tuple[int, int]:
        index, item = indexed_item
        item_path = str(item.path).replace("\\", "/")
        is_contract_async = "/tests/contracts/" in item_path and item.get_closest_marker("asyncio") is not None
        return (0 if is_contract_async else 1, index)

    items[:] = [item for _, item in sorted(indexed_items, key=_priority)]


class FakeBinanceCandleClient:
    def __init__(self, bars: list[Bar]):
        self.bars = bars

    async def fetch_recent_closed_bars(self, symbol: str, limit: int) -> list[Bar]:
        return self.bars[-limit:]

    async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True) -> Bar:
        return self.bars[-1]

    async def close(self) -> None:
        return None


@pytest.fixture
def sample_bars() -> list[Bar]:
    fixture_path = Path(__file__).parent / "fixtures" / "btc_15m_fixture.json"
    if not fixture_path.exists():
        fixture_path = Path(__file__).parent / "tradingbotsuite" / "fixtures" / "btc_15m_fixture.json"
    rows = json.loads(fixture_path.read_text(encoding="utf-8"))
    return [
        Bar(
            time_ms=row["time_ms"],
            open=Decimal(row["open"]),
            high=Decimal(row["high"]),
            low=Decimal(row["low"]),
            close=Decimal(row["close"]),
            volume=Decimal(row["volume"]),
        )
        for row in rows
    ]


@pytest.fixture
def app_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "suite.sqlite3",
        webhook=WebhookConfig(secret="test-secret", timestamp_tolerance_seconds=300),
        strategy=StrategyConfig(
            atr_length=14,
            take_profit_atr_multiple=Decimal("1.5"),
            stop_loss_atr_multiple=Decimal("1.0"),
            time_barrier_bars=24,
            order_size=Decimal("0.010"),
            entry_slippage_bps=Decimal("5"),
            exit_slippage_bps=Decimal("5"),
            price_tick=Decimal("0.1"),
            size_step=Decimal("0.001"),
            stale_bar_after_ms=10 * 365 * 24 * 60 * 60 * 1000,
            max_reconcile_gap_ms=60_000,
        ),
        binance=BinanceConfig(base_url="https://example.invalid"),
        hyperliquid=HyperliquidConfig(enable_live=False),
    )


@pytest.fixture
def test_client(app_config: AppConfig, sample_bars: list[Bar]) -> TestClient:
    app = create_app(app_config)
    app.state.engine.candle_client = FakeBinanceCandleClient(sample_bars)
    with TestClient(app) as client:
        yield client
