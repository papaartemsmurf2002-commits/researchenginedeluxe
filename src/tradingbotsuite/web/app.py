from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request

from tradingbotsuite.config import AppConfig
from tradingbotsuite.operator_console import OperatorConsoleService, OperatorContext, TraceRecorder
from tradingbotsuite.core.security import adapt_tradingview_payload, canonical_json_bytes, verify_hmac
from tradingbotsuite.runtime import build_engine
from tradingbotsuite.web.operator import register_operator_routes


def create_app(config: AppConfig | None = None) -> FastAPI:
    config = config or AppConfig.from_env()
    trace_recorder = TraceRecorder()
    engine = build_engine(config, trace_sink=trace_recorder)
    operator_service = OperatorConsoleService(OperatorContext(config=config, engine=engine, trace_recorder=trace_recorder))
    monitor_poll_seconds = max(float(os.getenv("TBS_SERVER_MONITOR_POLL_SECONDS", os.getenv("TBS_MANUAL_POLL_SECONDS", "5"))), 0.25)

    async def server_monitor_loop() -> None:
        symbol = "BTCUSDT"
        while True:
            try:
                await engine.refresh_market_data_health(symbol)
                await engine.refresh_execution_health()
                await engine.sync_execution_events(symbol)
                await engine.supervise_position_live(symbol)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                trace_recorder("server_monitor:error", {"symbol": symbol, "error": str(exc), "now_ms": engine.clock()})
            await asyncio.sleep(monitor_poll_seconds)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        monitor_task: asyncio.Task[None] | None = None
        await engine.initialize()
        await operator_service.start()
        monitor_task = asyncio.create_task(server_monitor_loop())
        try:
            yield
        finally:
            if monitor_task is not None:
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass
            await operator_service.shutdown()
            await engine.shutdown()

    app = FastAPI(title="Trading Bot Suite", version="0.1.0", lifespan=lifespan)
    app.state.engine = engine
    app.state.operator_service = operator_service

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "mode": engine.config.runtime_mode.value}

    @app.get("/health/details")
    async def health_details(symbol: str = "BTCUSDT") -> dict[str, object]:
        snapshot = await engine.collect_system_snapshot(symbol.upper())
        return snapshot

    @app.post("/webhooks/tradingview")
    async def tradingview_webhook(
        request: Request,
        x_signature: str = Header(..., alias="X-Signature"),
        x_timestamp_ms: int = Header(..., alias="X-Timestamp-Ms"),
    ) -> dict[str, object]:
        payload = await request.json()
        body = canonical_json_bytes(payload)
        now_ms = engine.clock()
        if not verify_hmac(
            secret=engine.config.webhook.secret,
            body=body,
            timestamp_ms=x_timestamp_ms,
            signature=x_signature,
            tolerance_seconds=engine.config.webhook.timestamp_tolerance_seconds,
            now_ms=now_ms,
        ):
            raise HTTPException(status_code=401, detail="invalid signature or stale timestamp")
        try:
            signal = adapt_tradingview_payload(payload, received_time_ms=now_ms)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        packet, reports, ticket = await engine.handle_signal(signal)
        return {
            "accepted": packet.accepted,
            "action": packet.action,
            "signal_id": signal.signal_id,
            "ticket_id": ticket.ticket_id,
            "reports": [report.model_dump(mode="json") for report in reports],
        }

    if config.operator_ui.enabled:
        register_operator_routes(app, config, operator_service)

    return app
