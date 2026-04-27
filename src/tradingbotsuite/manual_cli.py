from __future__ import annotations

import asyncio
import json
import os
from datetime import UTC, datetime
from typing import Any

from tradingbotsuite.config import AppConfig
from tradingbotsuite.core.models import SignalDirection
from tradingbotsuite.operator_commands import build_manual_signal, execute_reconcile, execute_refresh_health, execute_supervise
from tradingbotsuite.runtime import build_engine

MANUAL_SYMBOL = "BTCUSDT"
DEFAULT_POLL_SECONDS = float(os.getenv("TBS_MANUAL_POLL_SECONDS", "5"))


async def _build_manual_signal(engine, direction: SignalDirection, symbol: str):
    return await build_manual_signal(engine, direction, symbol)


def _format_value(value: Any) -> str:
    if isinstance(value, dict):
        return json.dumps(value, indent=2, sort_keys=True, default=str)
    if isinstance(value, list):
        return json.dumps(value, indent=2, default=str)
    return str(value)


class ConsoleTraceReporter:
    def __init__(self) -> None:
        self.enabled = True

    def __call__(self, stage: str, details: dict[str, Any]) -> None:
        if not self.enabled:
            return
        print(f"\n[{stage}]")
        for key, value in details.items():
            rendered = _format_value(value)
            if "\n" in rendered:
                print(f"  {key}:")
                for line in rendered.splitlines():
                    print(f"    {line}")
            else:
                print(f"  {key}: {rendered}")


async def run_manual_shell(config: AppConfig | None = None) -> None:
    config = config or AppConfig.from_env()
    reporter = ConsoleTraceReporter()
    engine = build_engine(config, trace_sink=reporter)
    await engine.initialize()
    await engine.refresh_market_data_health(MANUAL_SYMBOL)
    await engine.refresh_execution_health()
    poll_seconds = DEFAULT_POLL_SECONDS
    monitor_stop = asyncio.Event()

    print("Trading Bot Suite manual shell")
    print(f"Mode: {config.runtime_mode.value} | Symbol: {MANUAL_SYMBOL} | Poll: {poll_seconds}s | Time: {datetime.now(UTC).isoformat(timespec='seconds')}")
    print("Commands: l, s, status, supervise, reconcile, trace on, trace off, help, quit")

    async def monitor_loop() -> None:
        last_rendered: str | None = None
        while not monitor_stop.is_set():
            try:
                await engine.refresh_market_data_health(MANUAL_SYMBOL)
                await engine.refresh_execution_health()
                stream_events = await engine.sync_execution_events(MANUAL_SYMBOL)
                snapshot, reports = await engine.supervise_position_live(MANUAL_SYMBOL)
            except Exception as exc:
                print(f"\n[live-monitor:error] {exc}")
                await asyncio.sleep(poll_seconds)
                continue

            if stream_events:
                print("\n[execution-stream]")
                print(_format_value(stream_events))

            if snapshot.get("has_open_position"):
                summary = {
                    "symbol": snapshot["symbol"],
                    "current_price": snapshot.get("current_price"),
                    "exit_reason": snapshot.get("exit_reason"),
                    "tp_distance": snapshot.get("tp_distance"),
                    "sl_distance": snapshot.get("sl_distance"),
                    "time_to_barrier_ms": snapshot.get("time_to_barrier_ms"),
                }
                rendered = _format_value(summary)
                if rendered != last_rendered or reports:
                    print("\n[live-monitor]")
                    print(rendered)
                    if reports:
                        print("  auto_exit_reports:")
                        for line in _format_value([report.model_dump(mode="json") for report in reports]).splitlines():
                            print(f"    {line}")
                    last_rendered = rendered
            else:
                last_rendered = None
            await asyncio.sleep(poll_seconds)

    monitor_task = asyncio.create_task(monitor_loop())

    try:
        while True:
            raw = await asyncio.to_thread(input, "\nmanual> ")
            command = raw.strip().lower()
            if command in {"q", "quit", "exit"}:
                break
            if command in {"help", "h", "?"}:
                print("l -> inject long signal")
                print("s -> inject short signal")
                print("status -> print persisted position and safety state")
                print("supervise -> run one live exit supervision pass immediately")
                print("reconcile -> compare local state with adapter reconcile output")
                print("trace on/off -> enable or suppress stage logs")
                print("quit -> exit shell")
                continue
            if command == "trace on":
                reporter.enabled = True
                print("Tracing enabled.")
                continue
            if command == "trace off":
                reporter.enabled = False
                print("Tracing disabled.")
                continue
            if command == "status":
                system_snapshot = await engine.collect_system_snapshot(MANUAL_SYMBOL)
                print("\nPosition:")
                print(_format_value(system_snapshot["position"]))
                print("\nSafety:")
                print(_format_value(system_snapshot["safety"]))
                print("\nExecution health:")
                print(_format_value(system_snapshot["execution_health"]))
                print("\nMarket data health:")
                print(_format_value(system_snapshot["market_data_health"]))
                if system_snapshot["microstructure"] is not None:
                    print("\nMicrostructure snapshot:")
                    print(_format_value(system_snapshot["microstructure"]))
                print("\nExecution stream status:")
                print(_format_value(system_snapshot["execution_stream_status"]))
                if system_snapshot["market_stream_status"] is not None:
                    print("\nMarket stream status:")
                    print(_format_value(system_snapshot["market_stream_status"]))
                if system_snapshot["fresh_stream_events"]:
                    print("\nFresh stream events:")
                    print(_format_value(system_snapshot["fresh_stream_events"]))
                print("\nLive exit snapshot:")
                print(_format_value(system_snapshot["live_exit_snapshot"]))
                continue
            if command == "supervise":
                result = await execute_supervise(engine, symbol=MANUAL_SYMBOL)
                if result["stream_events"]:
                    print("\nFresh stream events:")
                    print(_format_value(result["stream_events"]))
                print("\nLive supervision snapshot:")
                print(_format_value(result["snapshot"]))
                print("\nSupervision reports:")
                print(_format_value(result["reports"] or [{"result": "no_exit"}]))
                continue
            if command == "reconcile":
                result = await execute_reconcile(engine, symbol=MANUAL_SYMBOL)
                if result["stream_events"]:
                    print("\nFresh stream events:")
                    print(_format_value(result["stream_events"]))
                print("\nPost-reconcile safety:")
                print(_format_value(result["safety"]))
                continue
            if command in {"l", "long", "s", "short"}:
                direction = SignalDirection.LONG if command.startswith("l") else SignalDirection.SHORT
                try:
                    signal = await build_manual_signal(engine, direction, MANUAL_SYMBOL)
                    packet, reports, ticket = await engine.handle_signal(signal)
                except Exception as exc:
                    print(f"\nManual signal failed: {exc}")
                    continue
                print("\nDecision packet:")
                print(_format_value(packet.model_dump(mode="json")))
                print("\nExecution reports:")
                print(_format_value([report.model_dump(mode="json") for report in reports]))
                print("\nAction ticket:")
                print(_format_value(ticket.model_dump(mode="json")))
                continue
            if command == "":
                continue
            print(f"Unknown command: {raw!r}. Type 'help' for commands.")
    finally:
        monitor_stop.set()
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        await engine.shutdown()
