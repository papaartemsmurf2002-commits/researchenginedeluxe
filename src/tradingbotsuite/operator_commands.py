from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from tradingbotsuite.core.models import SignalDirection, SignalIntent
from tradingbotsuite.live_smoke import run_live_smoke

DEFAULT_SYMBOL = "BTCUSDT"
TESTNET_PROTECTION_CLEANUP_SECONDS = 10
TESTNET_VALIDATION_LOW_TRIGGER_PRICE = "70000"
TESTNET_VALIDATION_HIGH_TRIGGER_PRICE = "75000"
_BACKGROUND_TASKS: set[asyncio.Task[Any]] = set()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _fixed_testnet_validation_trigger_prices(direction: SignalDirection) -> tuple[str, str]:
    if direction == SignalDirection.LONG:
        return TESTNET_VALIDATION_HIGH_TRIGGER_PRICE, TESTNET_VALIDATION_LOW_TRIGGER_PRICE
    return TESTNET_VALIDATION_LOW_TRIGGER_PRICE, TESTNET_VALIDATION_HIGH_TRIGGER_PRICE


def _track_background_task(task: Any) -> None:
    _BACKGROUND_TASKS.add(task)
    add_done_callback = getattr(task, "add_done_callback", None)
    if callable(add_done_callback):
        add_done_callback(_BACKGROUND_TASKS.discard)


async def build_manual_signal(
    engine,
    direction: SignalDirection,
    symbol: str = DEFAULT_SYMBOL,
) -> SignalIntent:
    return await build_manual_signal_with_options(engine, direction, symbol)


async def build_manual_signal_with_options(
    engine,
    direction: SignalDirection,
    symbol: str = DEFAULT_SYMBOL,
    *,
    testnet_short_lived_protections: bool = False,
) -> SignalIntent:
    try:
        bars = await engine.candle_client.fetch_recent_closed_bars(symbol, 1)
    except Exception as exc:
        raise RuntimeError(
            "Unable to build manual signal because Binance closed-bar data is temporarily unavailable. "
            f"Detail: {exc}"
        ) from exc
    if not bars:
        raise RuntimeError(f"no closed bars available for {symbol}")
    latest_bar = bars[-1]
    now_ms = engine.clock()
    signal_id = f"manual-{direction}-{now_ms}"
    raw_payload = {
        "source": "manual-cli",
        "typed_command": direction,
        "generated_at": _now_iso(),
        "latest_closed_bar_time_ms": latest_bar.time_ms,
    }
    if testnet_short_lived_protections:
        fixed_tp_trigger_price, fixed_sl_trigger_price = _fixed_testnet_validation_trigger_prices(direction)
        raw_payload["manual_testnet_protection_test"] = {
            "requested": True,
            "cleanup_after_seconds": TESTNET_PROTECTION_CLEANUP_SECONDS,
            "fixed_tp_trigger_price": fixed_tp_trigger_price,
            "fixed_sl_trigger_price": fixed_sl_trigger_price,
            "testing_only": True,
            "remove_before_mainnet": True,
        }
    return SignalIntent(
        signal_id=signal_id,
        source="manual-cli",
        symbol=symbol,
        direction=direction,
        tv_bar_time_ms=latest_bar.time_ms,
        received_time_ms=now_ms,
        raw_payload=raw_payload,
    )


def _is_live_testnet_engine(engine: Any) -> bool:
    config = getattr(engine, "config", None)
    runtime_mode = getattr(config, "runtime_mode", None)
    hyperliquid = getattr(config, "hyperliquid", None)
    base_url = str(getattr(hyperliquid, "base_url", "") or "").lower()
    return str(runtime_mode) == "live" and "testnet" in base_url


async def _delayed_testnet_protection_cleanup(
    engine: Any,
    *,
    symbol: str,
    expected_tp_cloid: str | None,
    expected_sl_cloid: str | None,
    signal_id: str,
    delay_seconds: int,
) -> None:
    try:
        await asyncio.sleep(delay_seconds)
        await engine.cancel_testnet_protective_orders(
            symbol,
            expected_tp_cloid=expected_tp_cloid,
            expected_sl_cloid=expected_sl_cloid,
            reason=f"manual_testnet_cleanup:{signal_id}",
        )
    except Exception as exc:  # pragma: no cover - defensive background path
        trace = getattr(engine, "_trace", None)
        if callable(trace):
            trace("testnet_protection_cleanup:error", symbol=symbol, signal_id=signal_id, error=str(exc))


def _schedule_testnet_protection_cleanup(
    engine: Any,
    *,
    requested: bool,
    packet: Any,
    reports: list[Any],
) -> dict[str, Any]:
    status: dict[str, Any] = {
        "requested": requested,
        "eligible": False,
        "armed": False,
        "cleanup_after_seconds": TESTNET_PROTECTION_CLEANUP_SECONDS,
        "reason": None,
        "tp_order_cloid": None,
        "sl_order_cloid": None,
    }
    if not requested:
        status["reason"] = "not_requested"
        return status
    if not _is_live_testnet_engine(engine):
        status["reason"] = "live_testnet_only"
        return status
    if not getattr(packet, "accepted", False):
        status["reason"] = "decision_rejected"
        return status
    if str(getattr(packet, "mode", "")) != "live":
        status["reason"] = "not_live_mode"
        return status

    tp_report = next((report for report in reports if getattr(report, "intent_type", None) == "protective_tp"), None)
    sl_report = next((report for report in reports if getattr(report, "intent_type", None) == "protective_sl"), None)
    if tp_report is None and sl_report is None:
        status["reason"] = "no_protective_orders_placed"
        return status

    status["eligible"] = True
    status["tp_order_cloid"] = getattr(tp_report, "cloid", None)
    status["sl_order_cloid"] = getattr(sl_report, "cloid", None)
    protective_reports = [report for report in (tp_report, sl_report) if report is not None]
    if any(getattr(report, "status", None) == "rejected" for report in protective_reports):
        status["reason"] = "protective_order_rejected"
        return status

    status["armed"] = True
    status["reason"] = "cleanup_scheduled"
    task = asyncio.create_task(
        _delayed_testnet_protection_cleanup(
            engine,
            symbol=packet.signal.symbol,
            expected_tp_cloid=status["tp_order_cloid"],
            expected_sl_cloid=status["sl_order_cloid"],
            signal_id=packet.signal.signal_id,
            delay_seconds=TESTNET_PROTECTION_CLEANUP_SECONDS,
        )
    )
    _track_background_task(task)
    return status


async def execute_manual_signal(
    engine,
    *,
    symbol: str,
    direction: SignalDirection,
    testnet_short_lived_protections: bool = False,
) -> dict[str, Any]:
    signal = await build_manual_signal_with_options(
        engine,
        direction,
        symbol,
        testnet_short_lived_protections=testnet_short_lived_protections,
    )
    packet, reports, ticket = await engine.handle_signal(signal)
    cleanup_status = _schedule_testnet_protection_cleanup(
        engine,
        requested=testnet_short_lived_protections,
        packet=packet,
        reports=reports,
    )
    return {
        "signal": signal.model_dump(mode="json"),
        "packet": packet.model_dump(mode="json"),
        "reports": [report.model_dump(mode="json") for report in reports],
        "ticket": ticket.model_dump(mode="json"),
        "testnet_short_lived_protections": cleanup_status,
    }


async def execute_supervise(engine, *, symbol: str) -> dict[str, Any]:
    stream_events = await engine.sync_execution_events(symbol)
    snapshot, reports = await engine.supervise_position_live(symbol)
    return {
        "stream_events": stream_events,
        "snapshot": snapshot,
        "reports": [report.model_dump(mode="json") for report in reports],
    }


async def execute_reconcile(engine, *, symbol: str) -> dict[str, Any]:
    stream_events = await engine.sync_execution_events(symbol)
    reconcile = await engine.bootstrap_reconcile(symbol)
    safety = await engine.store.get_safety_status()
    return {
        "stream_events": stream_events,
        "reconcile": reconcile,
        "safety": safety.model_dump(mode="json") if safety else {"in_safe_mode": False},
    }


async def execute_refresh_health(engine, *, symbol: str) -> dict[str, Any]:
    market = await engine.refresh_market_data_health(symbol)
    execution = await engine.refresh_execution_health()
    snapshot = await engine.collect_system_snapshot(symbol)
    return {
        "market_data_health": market,
        "execution_health": execution,
        "snapshot": snapshot,
    }


async def execute_smoke_live(engine, *, size: Decimal | None) -> dict[str, Any]:
    return await run_live_smoke(engine.config, size=size)


def command_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"
