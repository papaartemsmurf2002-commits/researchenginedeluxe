from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx
import pandas as pd

from tradingbot.indicators import normalize_frame


@dataclass(slots=True)
class BinanceFuturesCandleProvider:
    base_url: str = "https://fapi.binance.com"
    http: httpx.Client = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.http = httpx.Client(base_url=self.base_url, timeout=30.0)

    def close(self) -> None:
        self.http.close()

    def _symbol_to_binance(self, symbol: str) -> str:
        normalized = symbol.upper()
        if normalized.endswith("USDT"):
            return normalized
        return f"{normalized}USDT"

    def fetch_candles(self, symbol: str, interval: str, start_time_ms: int, end_time_ms: int) -> pd.DataFrame:
        market = self._symbol_to_binance(symbol)
        cursor = int(start_time_ms)
        rows: list[list[Any]] = []
        last_open_time: int | None = None

        while cursor < int(end_time_ms):
            response = self.http.get(
                "/fapi/v1/klines",
                params={
                    "symbol": market,
                    "interval": interval,
                    "startTime": cursor,
                    "endTime": int(end_time_ms),
                    "limit": 1500,
                },
            )
            response.raise_for_status()
            batch = response.json()
            if not batch:
                break
            rows.extend(batch)
            last_open_time = int(batch[-1][0])
            next_cursor = int(batch[-1][6]) + 1
            if next_cursor <= cursor or last_open_time == cursor:
                break
            cursor = next_cursor
            if len(batch) < 1500:
                break

        if not rows:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume", "symbol"])

        frame = pd.DataFrame(
            rows,
            columns=[
                "open_time",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "close_time",
                "quote_volume",
                "trade_count",
                "taker_buy_base_volume",
                "taker_buy_quote_volume",
                "ignore",
            ],
        )
        frame["timestamp"] = pd.to_datetime(frame["open_time"], unit="ms", utc=True)
        frame["symbol"] = symbol.upper()
        frame = frame[["timestamp", "open", "high", "low", "close", "volume", "symbol"]]
        return normalize_frame(frame)
