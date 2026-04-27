from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import websockets

from tradingbot.indicators import normalize_frame, round_step
from tradingbot.models import ExecutionConfig, Side


@dataclass(slots=True)
class HyperliquidSymbolMeta:
    name: str
    size_decimals: int = 3
    price_decimals: int = 2


class HyperliquidClient:
    def __init__(self, config: ExecutionConfig) -> None:
        self.config = config
        self.http = httpx.Client(base_url=config.rest_base_url, timeout=30.0)
        self._sdk_exchange = None
        self._sdk_info = None

    def close(self) -> None:
        self.http.close()

    def _ensure_private_clients(self) -> None:
        if self._sdk_exchange is not None and self._sdk_info is not None:
            return
        try:
            from hyperliquid.exchange import Exchange
            from hyperliquid.info import Info
            from hyperliquid.utils import constants
            from eth_account import Account
        except ImportError as exc:
            raise RuntimeError("Hyperliquid SDK dependencies are not installed") from exc
        if not self.config.secret_key:
            raise RuntimeError("Execution secret_key is required for exchange actions")
        account = Account.from_key(self.config.secret_key)
        base_url = constants.MAINNET_API_URL if not self.config.testnet else constants.TESTNET_API_URL
        self._sdk_info = Info(base_url, skip_ws=True)
        self._sdk_exchange = Exchange(account, base_url, account_address=self.config.account_address or account.address)

    def post_info(self, payload: dict[str, Any]) -> Any:
        response = self.http.post("/info", json=payload)
        response.raise_for_status()
        return response.json()

    def fetch_meta(self) -> Any:
        return self.post_info({"type": "meta"})

    def fetch_clearinghouse_state(self, account_address: str) -> Any:
        return self.post_info({"type": "clearinghouseState", "user": account_address})

    def fetch_candles(self, coin: str, interval: str, start_time_ms: int, end_time_ms: int) -> pd.DataFrame:
        payload = {
            "type": "candleSnapshot",
            "req": {
                "coin": coin,
                "interval": interval,
                "startTime": int(start_time_ms),
                "endTime": int(end_time_ms),
            },
        }
        data = self.post_info(payload)
        frame = pd.DataFrame(data)
        if frame.empty:
            return frame
        column_map = {"t": "timestamp", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"}
        frame = frame.rename(columns=column_map)
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], unit="ms", utc=True)
        frame["symbol"] = coin
        return normalize_frame(frame[["timestamp", "open", "high", "low", "close", "volume", "symbol"]])

    async def subscribe(self, subscriptions: list[dict[str, Any]]):
        async with websockets.connect(self.config.websocket_url, ping_interval=20, ping_timeout=20) as socket:
            for sub in subscriptions:
                await socket.send(json.dumps({"method": "subscribe", "subscription": sub}))
            while True:
                raw = await socket.recv()
                yield json.loads(raw)

    def schedule_dead_mans_switch(self, cancel_after_secs: int | None = None) -> Any:
        self._ensure_private_clients()
        return self._sdk_exchange.schedule_cancel(cancel_after_secs or self.config.dead_mans_switch_secs)

    def update_leverage(self, coin: str, leverage: float, is_cross: bool = True) -> Any:
        self._ensure_private_clients()
        return self._sdk_exchange.update_leverage(int(leverage), coin, is_cross=is_cross)

    def place_order(self, coin: str, is_buy: bool, size: float, price: float | None = None, reduce_only: bool = False) -> Any:
        self._ensure_private_clients()
        order_type = {"limit": {"tif": "Gtc"}} if price is not None else {"market": {}}
        return self._sdk_exchange.order(
            coin=coin,
            is_buy=is_buy,
            sz=size,
            limit_px=price if price is not None else 0.0,
            order_type=order_type,
            reduce_only=reduce_only,
        )

    def cancel_order(self, coin: str, oid: int) -> Any:
        self._ensure_private_clients()
        return self._sdk_exchange.cancel(coin, oid)

    def close_position_reduce_only(self, coin: str, side: Side, size: float) -> Any:
        is_buy = side == Side.SHORT
        return self.place_order(coin, is_buy=is_buy, size=size, price=None, reduce_only=True)

    def normalize_price(self, price: float, meta: HyperliquidSymbolMeta) -> float:
        return round_step(price, meta.price_decimals)

    def normalize_size(self, size: float, meta: HyperliquidSymbolMeta) -> float:
        return round_step(size, meta.size_decimals)


class HyperliquidCandleProvider:
    def __init__(self, config: ExecutionConfig) -> None:
        self.client = HyperliquidClient(config)

    def close(self) -> None:
        self.client.close()

    def fetch_candles(self, symbol: str, interval: str, start_time_ms: int, end_time_ms: int) -> pd.DataFrame:
        return self.client.fetch_candles(symbol, interval, start_time_ms, end_time_ms)


class HistoricalRecorder:
    def __init__(self, target_path: str | Path) -> None:
        self.target_path = Path(target_path)
        self.target_path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, rows: list[dict[str, Any]]) -> None:
        with self.target_path.open("a", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row) + "\n")

    async def record_stream(self, client: HyperliquidClient, subscriptions: list[dict[str, Any]]) -> None:
        async for message in client.subscribe(subscriptions):
            self.append([message])
            await asyncio.sleep(0)
