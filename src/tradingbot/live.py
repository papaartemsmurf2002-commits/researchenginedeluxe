from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from tradingbot.backtest import Backtester
from tradingbot.data.hyperliquid import HyperliquidClient
from tradingbot.models import AppConfig, Side


class LiveTrader:
    def __init__(self, app_config: AppConfig, symbol: str) -> None:
        self.app_config = app_config
        self.symbol = symbol
        self.client = HyperliquidClient(app_config.execution)
        self.backtester = Backtester()
        self.state_path = Path(app_config.execution.state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def load_state(self) -> dict:
        if not self.state_path.exists():
            return {}
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def save_state(self, state: dict) -> None:
        self.state_path.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")

    def run_once(self, base_df: pd.DataFrame, confirm_df: pd.DataFrame | None = None) -> dict:
        report = self.backtester.run(base_df, confirm_df, self.app_config, self.symbol)
        decision = report.latest_decision or {"symbol": self.symbol, "action": "hold"}
        decision["symbol"] = self.symbol
        self.save_state({"latest_decision": decision, "metrics": report.metrics})
        return decision

    def execute_decision(self, decision: dict, size: float) -> None:
        if not self.app_config.execution.enable_live_trading:
            return
        action = decision.get("action")
        if action == "open_long":
            self.client.place_order(self.symbol, is_buy=True, size=size, price=None, reduce_only=False)
        elif action == "open_short":
            self.client.place_order(self.symbol, is_buy=False, size=size, price=None, reduce_only=False)
        elif action == "close_position":
            side = Side.LONG if decision.get("position_side") == "long" else Side.SHORT
            self.client.close_position_reduce_only(self.symbol, side, size)
