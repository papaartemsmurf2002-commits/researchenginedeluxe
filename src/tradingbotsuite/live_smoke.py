from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any

from tradingbotsuite.adapters.execution import build_close_intents, make_execution_adapter
from tradingbotsuite.config import AppConfig
from tradingbotsuite.core.models import ExecutionIntent, ExecutionIntentType, ExitReason, PositionState, RuntimeMode, SignalDirection, TradeStatus


async def run_live_smoke(
    config: AppConfig,
    *,
    symbol: str = "BTCUSDT",
    size: Decimal | None = None,
) -> dict[str, Any]:
    if config.runtime_mode != RuntimeMode.LIVE:
        raise ValueError("live smoke requires TBS_RUNTIME_MODE=live or a live AppConfig")

    adapter = make_execution_adapter(
        RuntimeMode.LIVE,
        entry_slippage_bps=config.strategy.entry_slippage_bps,
        exit_slippage_bps=config.strategy.exit_slippage_bps,
        price_tick=config.strategy.price_tick,
        size_step=config.strategy.size_step,
        hyperliquid_config=config.hyperliquid,
    )
    smoke_size = size if size is not None else config.strategy.order_size
    if smoke_size <= Decimal("0"):
        raise ValueError("smoke size must be positive")

    try:
        await adapter.start_user_streams()
        preflight = await adapter.preflight_account()
        market_snapshot = await adapter.get_market_snapshot(symbol)
        reconcile_before = await adapter.reconcile(symbol)
        if Decimal(str(reconcile_before.get("position_size", "0"))) > Decimal("0"):
            return {
                "ok": False,
                "reason": "account_not_flat",
                "preflight": preflight,
                "market_snapshot": market_snapshot,
                "reconcile_before": reconcile_before,
            }
        if market_snapshot is None:
            return {"ok": False, "reason": "missing_market_snapshot", "preflight": preflight}

        entry_intent = ExecutionIntent(
            intent_id="live-smoke-enter",
            mode=RuntimeMode.LIVE,
            intent_type=ExecutionIntentType.ENTER,
            symbol=symbol,
            direction=SignalDirection.LONG,
            size=smoke_size,
            reference_price=Decimal(str(market_snapshot["mid_price"])),
        )
        entry_report = (await adapter.execute([entry_intent]))[0]
        await adapter.await_order_activity(symbol=symbol, cloid=entry_report.cloid, exchange_order_id=entry_report.exchange_order_id)
        await asyncio.sleep(0.2)
        reconcile_after_entry = await adapter.reconcile(symbol)
        if Decimal(str(reconcile_after_entry.get("position_size", "0"))) <= Decimal("0"):
            return {
                "ok": False,
                "reason": "entry_not_confirmed",
                "preflight": preflight,
                "entry_report": entry_report.model_dump(mode="json"),
                "reconcile_after_entry": reconcile_after_entry,
                "stream_status": adapter.get_stream_status(),
            }

        close_reports = await adapter.execute(
            build_close_intents(
                RuntimeMode.LIVE,
                PositionState(
                    symbol=symbol,
                    status=TradeStatus.OPEN,
                    direction=reconcile_after_entry["side"],
                    position_size=Decimal(str(reconcile_after_entry["position_size"])),
                ),
            )
        )
        close_report = next((report for report in close_reports if report.intent_type == ExecutionIntentType.CLOSE), None)
        if close_report is not None:
            await adapter.await_order_activity(symbol=symbol, cloid=close_report.cloid, exchange_order_id=close_report.exchange_order_id)
        await asyncio.sleep(0.2)
        reconcile_after_close = await adapter.reconcile(symbol)
        return {
            "ok": Decimal(str(reconcile_after_close.get("position_size", "0"))) == Decimal("0"),
            "preflight": preflight,
            "market_snapshot": market_snapshot,
            "entry_report": entry_report.model_dump(mode="json"),
            "reconcile_after_entry": reconcile_after_entry,
            "close_reports": [report.model_dump(mode="json") for report in close_reports],
            "reconcile_after_close": reconcile_after_close,
            "stream_status": adapter.get_stream_status(),
            "expected_exit_reason": ExitReason.MANUAL,
        }
    finally:
        await adapter.shutdown()
