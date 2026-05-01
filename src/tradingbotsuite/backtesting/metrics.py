from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


REQUIRED_BACKTEST_METRICS = (
    "net_return_after_fees_slippage_funding",
    "trade_count",
    "long_count",
    "short_count",
    "hit_rate",
    "expectancy_per_trade",
    "average_holding_time_ms",
    "median_holding_time_ms",
    "max_drawdown",
    "profit_factor",
    "exposure",
    "turnover",
    "slippage_sensitivity",
    "funding_contribution",
    "split_by_regime",
    "split_by_month",
    "split_by_volatility_bucket",
    "capacity_liquidity_flags",
)


def calculate_backtest_metrics(
    *,
    trades: pd.DataFrame,
    signals: pd.DataFrame,
    equity_curve: pd.DataFrame,
    market_data: pd.DataFrame,
    initial_equity: float,
) -> dict[str, Any]:
    if trades.empty:
        return _empty_metrics(signals=signals, equity_curve=equity_curve, market_data=market_data)

    net_returns = pd.to_numeric(trades["net_return"], errors="coerce").fillna(0.0)
    gross_returns = pd.to_numeric(trades["gross_return"], errors="coerce").fillna(0.0)
    winners = net_returns[net_returns > 0.0]
    losers = net_returns[net_returns < 0.0]
    equity = pd.to_numeric(equity_curve["equity"], errors="coerce").fillna(float(initial_equity))
    peak = equity.cummax()
    drawdown = ((equity / peak.replace(0.0, np.nan)) - 1.0).fillna(0.0)
    total_span = max(int(market_data["bar_time_ms"].max()) - int(market_data["bar_time_ms"].min()), 1)
    holding_sum = pd.to_numeric(trades["holding_ms"], errors="coerce").fillna(0.0).sum()
    slippage_cost = pd.to_numeric(trades["slippage_return"], errors="coerce").fillna(0.0)
    funding = pd.to_numeric(trades["funding_return"], errors="coerce").fillna(0.0)
    metrics: dict[str, Any] = {
        "net_return_after_fees_slippage_funding": float((1.0 + net_returns).prod() - 1.0),
        "gross_return_before_costs": float((1.0 + gross_returns).prod() - 1.0),
        "trade_count": int(len(trades)),
        "long_count": int((trades["side"].astype(str).str.lower() == "long").sum()),
        "short_count": int((trades["side"].astype(str).str.lower() == "short").sum()),
        "hit_rate": float((net_returns > 0.0).mean()),
        "expectancy_per_trade": float(net_returns.mean()),
        "average_holding_time_ms": float(pd.to_numeric(trades["holding_ms"], errors="coerce").mean()),
        "median_holding_time_ms": float(pd.to_numeric(trades["holding_ms"], errors="coerce").median()),
        "max_drawdown": float(drawdown.min()),
        "profit_factor": _profit_factor(winners, losers),
        "exposure": float(min(1.0, holding_sum / total_span)),
        "turnover": float(len(trades) / max(len(market_data), 1)),
        "slippage_sensitivity": float(slippage_cost.sum()),
        "funding_contribution": float(funding.sum()),
        "split_by_regime": _split_metrics(trades, "regime"),
        "split_by_month": _split_metrics(trades, "entry_month"),
        "split_by_volatility_bucket": _split_metrics(trades, "volatility_bucket"),
        "capacity_liquidity_flags": _capacity_flags(trades),
    }
    missing = [key for key in REQUIRED_BACKTEST_METRICS if key not in metrics]
    if missing:  # pragma: no cover - defensive contract guard
        raise AssertionError(f"missing required metrics: {missing}")
    return metrics


def _empty_metrics(*, signals: pd.DataFrame, equity_curve: pd.DataFrame, market_data: pd.DataFrame) -> dict[str, Any]:
    _ = equity_curve
    return {
        "net_return_after_fees_slippage_funding": 0.0,
        "gross_return_before_costs": 0.0,
        "trade_count": 0,
        "long_count": 0,
        "short_count": 0,
        "hit_rate": 0.0,
        "expectancy_per_trade": 0.0,
        "average_holding_time_ms": 0.0,
        "median_holding_time_ms": 0.0,
        "max_drawdown": 0.0,
        "profit_factor": 0.0,
        "exposure": 0.0,
        "turnover": 0.0,
        "slippage_sensitivity": 0.0,
        "funding_contribution": 0.0,
        "split_by_regime": {},
        "split_by_month": {},
        "split_by_volatility_bucket": {},
        "capacity_liquidity_flags": {
            "available": False,
            "reason": "no_trades",
            "signal_count": int(len(signals)),
            "market_row_count": int(len(market_data)),
        },
    }


def _profit_factor(winners: pd.Series, losers: pd.Series) -> float:
    gains = float(winners.sum())
    losses = abs(float(losers.sum()))
    if losses == 0.0:
        return 999999.0 if gains > 0.0 else 0.0
    return gains / losses


def _split_metrics(trades: pd.DataFrame, column: str) -> dict[str, dict[str, float | int]]:
    if column not in trades.columns or trades.empty:
        return {}
    result: dict[str, dict[str, float | int]] = {}
    for value, group in trades.groupby(column, dropna=False):
        key = "missing" if pd.isna(value) else str(value)
        returns = pd.to_numeric(group["net_return"], errors="coerce").fillna(0.0)
        result[key] = {
            "trade_count": int(len(group)),
            "net_return_sum": float(returns.sum()),
            "expectancy": float(returns.mean()) if len(returns) else 0.0,
            "hit_rate": float((returns > 0.0).mean()) if len(returns) else 0.0,
        }
    return dict(sorted(result.items()))


def _capacity_flags(trades: pd.DataFrame) -> dict[str, Any]:
    if "spread_bps" not in trades.columns:
        return {"available": False, "reason": "spread_bps_missing"}
    spread = pd.to_numeric(trades["spread_bps"], errors="coerce")
    return {
        "available": True,
        "max_spread_bps": float(spread.max()) if len(spread.dropna()) else 0.0,
        "wide_spread_trade_count": int((spread > 10.0).sum()),
    }
