from __future__ import annotations

import asyncio
import time
from dataclasses import asdict, replace
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Callable
from uuid import uuid4

from tradingbotsuite.adapters.binance import BinanceCandleClient
from tradingbotsuite.adapters.execution import (
    ExecutionAdapter,
    HyperliquidExecutionAdapter,
    build_close_intents,
    build_open_intents,
    build_protective_intents,
    make_execution_adapter,
)
from tradingbotsuite.config import AppConfig
from tradingbotsuite.core.acceptance import RuleAcceptanceSettings, default_rule_acceptance_settings, evaluate_rule_acceptance
from tradingbotsuite.core.features import VolatilityFeatureConfig, build_extended_feature_snapshot
from tradingbotsuite.core.math import BAR_INTERVAL_MS, atr_wilder, build_barriers, build_vertical_barrier, evaluate_exit_on_bar, hurst_exponent
from tradingbotsuite.core.math import realized_slippage_bps
from tradingbotsuite.core.models import (
    ActionTicket,
    DecisionAction,
    DecisionPacket,
    ExitReason,
    ExecutionIntent,
    ExecutionIntentType,
    ExecutionReport,
    ExecutionStatus,
    RuntimeMode,
    SafeModeReason,
    SafetyState,
    SafetyStatus,
    SignalDirection,
    SignalIntent,
    TradeStatus,
)
from tradingbotsuite.persistence.sqlite_store import SQLiteStore
from tradingbotsuite.research.config import FeatureSettings, ResearchPlan, load_research_plan
from tradingbotsuite.research.inference import AcceptanceScorer


class TradingEngine:
    MANUAL_TESTNET_SUPERVISION_HOLDOFF_MS = 20_000
    TESTNET_VALIDATION_LOW_TRIGGER_PRICE = Decimal("70000")
    TESTNET_VALIDATION_HIGH_TRIGGER_PRICE = Decimal("75000")

    def __init__(
        self,
        config: AppConfig,
        store: SQLiteStore,
        candle_client: BinanceCandleClient,
        execution_adapter: ExecutionAdapter,
        *,
        clock: Callable[[], int] | None = None,
        trace_sink: Callable[[str, dict[str, Any]], None] | None = None,
        scorer: AcceptanceScorer | None = None,
    ):
        self.config = config
        self.store = store
        self.candle_client = candle_client
        self.execution_adapter = execution_adapter
        self.clock = clock or (lambda: int(time.time() * 1000))
        self.trace_sink = trace_sink
        self.scorer = scorer
        self.research_plan: ResearchPlan | None = (
            scorer.plan
            if scorer is not None and hasattr(scorer.plan, "features") and hasattr(scorer.plan, "exit_supervision")
            else None
        )
        self._op_locks_by_loop: dict[int, asyncio.Lock] = {}
        self._live_supervision_hold_until_by_symbol: dict[str, int] = {}

    @property
    def _op_lock(self) -> asyncio.Lock:
        # TestClient and direct asyncio.run checks can touch the same engine from
        # different event loops. Production uses one ASGI loop; this keeps tests
        # and diagnostics from binding a lock to the wrong loop.
        loop = asyncio.get_running_loop()
        key = id(loop)
        lock = self._op_locks_by_loop.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._op_locks_by_loop[key] = lock
        return lock

    async def initialize(self) -> None:
        self._trace("initialize:start", runtime_mode=self.config.runtime_mode, db_path=str(self.config.db_path))
        await self.store.initialize()
        if self.research_plan is None:
            try:
                self.research_plan = load_research_plan(self.config.research.config_path)
            except Exception as exc:
                self._trace("initialize:research_plan_unavailable", error=str(exc), config_path=str(self.config.research.config_path))
        if hasattr(self.candle_client, "start_market_streams"):
            await self.candle_client.start_market_streams(["BTCUSDT"])
        await self.execution_adapter.start_user_streams()
        preflight: dict[str, Any] | None = None
        if self.config.runtime_mode == RuntimeMode.LIVE:
            preflight = await self.execution_adapter.preflight_account()
            self._trace("initialize:preflight", preflight=preflight)
        existing = await self.store.get_safety_status()
        if existing is None:
            await self.store.set_safety_status(
                SafetyStatus(in_safe_mode=False, reason=SafeModeReason.NONE, detail="", updated_time_ms=self.clock())
            )
        if self.config.runtime_mode == RuntimeMode.LIVE and isinstance(self.execution_adapter, HyperliquidExecutionAdapter):
            if preflight is not None and not preflight.get("ok"):
                await self.set_safe_mode(SafeModeReason.ACCOUNT_NOT_CONFIGURED, str(preflight.get("reason", "live_preflight_failed")))
        self._trace(
            "initialize:done",
            safety_status=(existing.model_dump(mode="json") if existing else None),
            execution_stream=self.execution_adapter.get_stream_status(),
        )

    def _feature_settings(self) -> FeatureSettings:
        if self.research_plan is not None:
            return self.research_plan.features
        return FeatureSettings(
            realized_vol_window_bars=20,
            atr_percentile_window_bars=96,
            volatility_shock_window_bars=20,
            volatility_shock_zscore_threshold=2.0,
        )

    def _rule_acceptance_settings(self) -> RuleAcceptanceSettings:
        if self.research_plan is not None and hasattr(self.research_plan, "acceptance_filter"):
            return RuleAcceptanceSettings(**asdict(self.research_plan.acceptance_filter))  # type: ignore[name-defined]
        return default_rule_acceptance_settings()

    def _volatility_feature_config(self) -> VolatilityFeatureConfig:
        feature_settings = self._feature_settings()
        return VolatilityFeatureConfig(
            realized_vol_window_bars=feature_settings.realized_vol_window_bars,
            atr_percentile_window_bars=feature_settings.atr_percentile_window_bars,
            volatility_shock_window_bars=feature_settings.volatility_shock_window_bars,
            volatility_shock_zscore_threshold=feature_settings.volatility_shock_zscore_threshold,
        )

    async def shutdown(self) -> None:
        await self.execution_adapter.shutdown()
        if hasattr(self.candle_client, "close"):
            await self.candle_client.close()

    async def set_runtime_mode(self, mode: RuntimeMode) -> dict[str, Any]:
        async with self._op_lock:
            previous_mode = self.config.runtime_mode
            if mode == previous_mode:
                return {
                    "changed": False,
                    "previous_mode": str(previous_mode),
                    "mode": str(previous_mode),
                    "reason": "already_in_requested_mode",
                }
            open_positions = [position for position in await self.store.list_position_states() if position.status == TradeStatus.OPEN]
            if open_positions:
                raise RuntimeError("cannot switch runtime mode while a position is open")

            refreshed_hyperliquid = self.config.hyperliquid
            if mode == RuntimeMode.LIVE:
                refreshed_hyperliquid = AppConfig.from_env().hyperliquid
            new_config = replace(self.config, runtime_mode=mode, hyperliquid=refreshed_hyperliquid)
            new_adapter = make_execution_adapter(
                mode,
                entry_slippage_bps=new_config.strategy.entry_slippage_bps,
                exit_slippage_bps=new_config.strategy.exit_slippage_bps,
                price_tick=new_config.strategy.price_tick,
                size_step=new_config.strategy.size_step,
                hyperliquid_config=new_config.hyperliquid,
            )

            await self.execution_adapter.shutdown()
            self.execution_adapter = new_adapter
            self.config = new_config
            await self.execution_adapter.start_user_streams()

            preflight: dict[str, Any] | None = None
            if mode == RuntimeMode.LIVE:
                preflight = await self.execution_adapter.preflight_account()
                if not preflight.get("ok"):
                    await self.set_safe_mode(
                        SafeModeReason.ACCOUNT_NOT_CONFIGURED,
                        str(preflight.get("reason", "live_preflight_failed")),
                    )
            else:
                safety = await self.store.get_safety_status()
                if safety and safety.reason == SafeModeReason.ACCOUNT_NOT_CONFIGURED:
                    await self.clear_safe_mode()

            self._trace(
                "runtime_mode:switched",
                previous_mode=str(previous_mode),
                mode=str(mode),
                execution_stream=self.execution_adapter.get_stream_status(),
                preflight=preflight,
            )
            return {
                "changed": True,
                "previous_mode": str(previous_mode),
                "mode": str(mode),
                "preflight": preflight,
                "execution_stream_status": self.execution_adapter.get_stream_status(),
            }

    def _is_live_testnet_runtime(self) -> bool:
        return self.config.runtime_mode == RuntimeMode.LIVE and "testnet" in self.config.hyperliquid.base_url.lower()

    def _use_exchange_fill_for_canonical_pricing(self, packet: DecisionPacket) -> bool:
        if packet.mode != RuntimeMode.LIVE:
            return True
        return not self._is_live_testnet_runtime()

    def _manual_live_testnet_hold_until_ms(self, packet: DecisionPacket, now_ms: int) -> int | None:
        if not self._is_live_testnet_runtime():
            return None
        if packet.signal.source != "manual-cli":
            return None
        return now_ms + self.MANUAL_TESTNET_SUPERVISION_HOLDOFF_MS

    def _testnet_validation_config(self, packet: DecisionPacket) -> dict[str, Any] | None:
        if not self._is_live_testnet_runtime():
            return None
        if packet.signal.source != "manual-cli":
            return None
        raw = packet.signal.raw_payload or {}
        config = raw.get("manual_testnet_protection_test")
        if not isinstance(config, dict) or not config.get("requested"):
            return None
        return config

    def _default_testnet_validation_trigger_prices(
        self,
        direction: SignalDirection | None,
    ) -> tuple[Decimal, Decimal]:
        if direction == SignalDirection.LONG:
            return self.TESTNET_VALIDATION_HIGH_TRIGGER_PRICE, self.TESTNET_VALIDATION_LOW_TRIGGER_PRICE
        return self.TESTNET_VALIDATION_LOW_TRIGGER_PRICE, self.TESTNET_VALIDATION_HIGH_TRIGGER_PRICE

    def _testnet_validation_protection_packet(self, packet: DecisionPacket) -> DecisionPacket:
        config = self._testnet_validation_config(packet)
        if config is None:
            return packet
        # Temporary test harness: Hyperliquid testnet protection orders use fixed trigger
        # prices so adapter validation remains readable despite testnet price drift.
        default_tp, default_sl = self._default_testnet_validation_trigger_prices(packet.signal.direction)
        tp_price = Decimal(str(config.get("fixed_tp_trigger_price", default_tp)))
        sl_price = Decimal(str(config.get("fixed_sl_trigger_price", default_sl)))
        feature_snapshot = {
            **packet.feature_snapshot,
            "hyperliquid_testnet_validation_protection_mode": {
                "enabled": True,
                "testing_only": True,
                "remove_before_mainnet": True,
                "tp_trigger_price": str(tp_price),
                "sl_trigger_price": str(sl_price),
            },
        }
        overridden = packet.model_copy(
            update={
                "tp_price": tp_price,
                "sl_price": sl_price,
                "feature_snapshot": feature_snapshot,
            }
        )
        self._trace(
            "execution:testnet_protective_price_override",
            symbol=packet.signal.symbol,
            direction=str(packet.signal.direction),
            original_tp_price=str(packet.tp_price) if packet.tp_price is not None else None,
            original_sl_price=str(packet.sl_price) if packet.sl_price is not None else None,
            override_tp_price=str(tp_price),
            override_sl_price=str(sl_price),
            testing_only=True,
        )
        return overridden

    def _recommended_action(self, reason_code: str | SafeModeReason | None) -> str | None:
        code = str(reason_code) if reason_code is not None else None
        actions = {
            str(SafeModeReason.STALE_MARKET_DATA): "Check Binance stream freshness, then refresh health or restart the app.",
            str(SafeModeReason.HEARTBEAT_LOSS): "Check Hyperliquid websocket health and wait for heartbeat recovery before trading.",
            str(SafeModeReason.POSITION_AMBIGUITY): "Run Reconcile and keep trading disabled until local and exchange state match.",
            str(SafeModeReason.RECONCILIATION_MISMATCH): "Run Reconcile immediately and do not force new entries.",
            str(SafeModeReason.RECONCILIATION_STALE): "Refresh execution health or run Reconcile until the gap clears.",
            str(SafeModeReason.BASIS_DISLOCATION): "Do not force entries. Inspect Binance and Hyperliquid mids first.",
            str(SafeModeReason.ORDER_TIMEOUT): "Inspect exchange order state and reconcile before allowing another entry.",
            "stream_not_started": "Wait for the Hyperliquid user stream to initialize before trading.",
            "ws_not_ready": "Wait for the Hyperliquid websocket to finish connecting before trading.",
            "ws_not_running": "Check the Hyperliquid websocket worker and reconnect it before trading.",
            "ws_disconnected": "Check Hyperliquid websocket connectivity and wait for reconnection before trading.",
            "spread_abnormality": "Wait for the spread to normalize before taking a new BTC entry.",
            "daily_loss_limit": "Pause entries for the rest of the session and review realized PnL.",
            "open_risk_limit": "Reduce configured size or close risk before opening another trade.",
            "depth_degraded": "Wait for Binance diff-depth to resync before trusting queue imbalance inputs.",
        }
        return actions.get(code)

    async def set_safe_mode(self, reason: SafeModeReason, detail: str) -> None:
        self._trace("safe_mode:set", reason=reason, detail=detail)
        await self.store.set_safety_status(
            SafetyStatus(
                in_safe_mode=True,
                state=SafetyState.SAFE_MODE,
                reason=reason,
                reason_code=str(reason),
                detail=detail,
                recommended_action=self._recommended_action(reason),
                updated_time_ms=self.clock(),
            )
        )

    async def clear_safe_mode(self) -> None:
        self._trace("safe_mode:clear")
        await self.store.set_safety_status(
            SafetyStatus(
                in_safe_mode=False,
                state=SafetyState.HEALTHY,
                reason=SafeModeReason.NONE,
                reason_code=None,
                detail="",
                recommended_action=None,
                updated_time_ms=self.clock(),
            )
        )

    async def _record_health_transition(
        self,
        *,
        symbol: str,
        scope: str,
        state: str,
        reason_code: str | None,
        summary: str,
        payload: dict[str, Any],
    ) -> None:
        state_key = f"health:{scope}:{symbol}"
        next_state = {
            "symbol": symbol,
            "scope": scope,
            "state": state,
            "reason_code": reason_code,
            "summary": summary,
        }
        previous = await self.store.get_runtime_value(state_key)
        if previous == next_state:
            return
        await self.store.set_runtime_value(state_key, next_state)
        await self.store.append_health_event(
            event_id=uuid4().hex,
            symbol=symbol,
            scope=scope,
            state=state,
            reason_code=reason_code,
            event_time_ms=self.clock(),
            summary=summary,
            recommended_action=self._recommended_action(reason_code),
            payload=payload,
        )

    def _start_of_utc_day_ms(self, now_ms: int) -> int:
        current = datetime.fromtimestamp(now_ms / 1000.0, tz=UTC)
        start = current.replace(hour=0, minute=0, second=0, microsecond=0)
        return int(start.timestamp() * 1000)

    async def _daily_loss_blocked(self, symbol: str, now_ms: int) -> tuple[bool, dict[str, Any] | None]:
        limit = self.config.strategy.max_daily_loss_quote
        if limit <= Decimal("0"):
            return False, None
        pnl = await self.store.sum_realized_pnl_since(symbol=symbol, start_time_ms=self._start_of_utc_day_ms(now_ms))
        loss = abs(min(pnl, Decimal("0")))
        if loss < limit:
            return False, None
        return True, {
            "reason_code": "daily_loss_limit",
            "detail": f"realized daily loss {loss} exceeds configured limit {limit}",
            "realized_pnl_quote": str(pnl),
            "limit_quote": str(limit),
        }

    def _open_risk_block(self, *, reference_price: Decimal, intended_size: Decimal) -> dict[str, Any] | None:
        limit = self.config.strategy.max_open_risk_notional
        if limit <= Decimal("0"):
            return None
        notional = reference_price * intended_size
        if notional < limit:
            return None
        return {
            "reason_code": "open_risk_limit",
            "detail": f"intended notional {notional} exceeds configured open-risk limit {limit}",
            "notional": str(notional),
            "limit_notional": str(limit),
        }

    def _spread_block(self, microstructure: dict[str, Any] | None) -> dict[str, Any] | None:
        if microstructure is None or microstructure.get("spread_bps") is None:
            return None
        threshold = self.config.strategy.max_spread_bps
        if threshold <= Decimal("0"):
            return None
        spread_bps = Decimal(str(microstructure["spread_bps"]))
        if spread_bps <= threshold:
            return None
        return {
            "reason_code": "spread_abnormality",
            "detail": f"spread {spread_bps} bps exceeds configured threshold {threshold} bps",
            "spread_bps": str(spread_bps),
            "threshold_bps": str(threshold),
        }

    async def refresh_market_data_health(self, symbol: str) -> dict[str, Any]:
        now_ms = self.clock()
        try:
            bars = await self.candle_client.fetch_recent_closed_bars(symbol, 1)
        except Exception as exc:
            await self.set_safe_mode(SafeModeReason.STALE_MARKET_DATA, f"market data fetch failed: {exc}")
            result = {
                "symbol": symbol,
                "healthy": False,
                "state": SafetyState.SAFE_MODE,
                "reason_code": str(SafeModeReason.STALE_MARKET_DATA),
                "recommended_action": self._recommended_action(SafeModeReason.STALE_MARKET_DATA),
                "error": str(exc),
                "feed_health": {},
            }
            await self._record_health_transition(
                symbol=symbol,
                scope="market_data",
                state=str(SafetyState.SAFE_MODE),
                reason_code=str(SafeModeReason.STALE_MARKET_DATA),
                summary="Market data fetch failed",
                payload=result,
            )
            self._trace("market_data:health", **result)
            return result
        if not bars:
            await self.set_safe_mode(SafeModeReason.STALE_MARKET_DATA, "no closed bars returned during health refresh")
            result = {
                "symbol": symbol,
                "healthy": False,
                "state": SafetyState.SAFE_MODE,
                "reason_code": str(SafeModeReason.STALE_MARKET_DATA),
                "recommended_action": self._recommended_action(SafeModeReason.STALE_MARKET_DATA),
                "error": "no closed bars",
                "feed_health": {},
            }
            await self._record_health_transition(
                symbol=symbol,
                scope="market_data",
                state=str(SafetyState.SAFE_MODE),
                reason_code=str(SafeModeReason.STALE_MARKET_DATA),
                summary="No closed bars returned during health refresh",
                payload=result,
            )
            self._trace("market_data:health", **result)
            return result
        latest_bar = bars[-1]
        latest_bar_close_time_ms = latest_bar.time_ms + BAR_INTERVAL_MS
        healthy = (now_ms - latest_bar_close_time_ms) <= self.config.strategy.stale_bar_after_ms
        reason_code = None
        stream_status = self.candle_client.get_stream_status() if hasattr(self.candle_client, "get_stream_status") else {"enabled": False}
        stream_reason = None
        microstructure = None
        symbol_stream_status = stream_status.get("symbol_status", {}).get(symbol, {})
        feed_health: dict[str, Any] = {
            "bars": {
                "healthy": healthy,
                "last_time_ms": latest_bar_close_time_ms,
                "age_ms": now_ms - latest_bar_close_time_ms,
                "stale_after_ms": self.config.strategy.stale_bar_after_ms,
            }
        }
        if self.config.runtime_mode == RuntimeMode.LIVE and stream_status.get("enabled"):
            started_ms = symbol_stream_status.get("started_ms")
            last_kline_ws_message_ms = symbol_stream_status.get("last_kline_ws_message_ms")
            if started_ms is None:
                healthy = False
                stream_reason = "stream_not_started"
            elif last_kline_ws_message_ms is None:
                if now_ms - int(started_ms) > self.config.binance.ws_stale_after_ms:
                    healthy = False
                    stream_reason = "no_kline_ws_messages"
            elif now_ms - int(last_kline_ws_message_ms) > self.config.binance.ws_stale_after_ms:
                healthy = False
                stream_reason = "stale_kline_ws_messages"
            feed_health.update(
                {
                    "trades": {
                        "healthy": (
                            symbol_stream_status.get("last_trade_ws_message_ms") is not None
                            and now_ms - int(symbol_stream_status["last_trade_ws_message_ms"]) <= self.config.strategy.stale_trade_after_ms
                        ),
                        "last_time_ms": symbol_stream_status.get("last_trade_ws_message_ms"),
                        "stale_after_ms": self.config.strategy.stale_trade_after_ms,
                    },
                    "book_ticker": {
                        "healthy": (
                            symbol_stream_status.get("last_book_ws_message_ms") is not None
                            and now_ms - int(symbol_stream_status["last_book_ws_message_ms"]) <= self.config.strategy.stale_book_ticker_after_ms
                        ),
                        "last_time_ms": symbol_stream_status.get("last_book_ws_message_ms"),
                        "stale_after_ms": self.config.strategy.stale_book_ticker_after_ms,
                    },
                    "depth": {
                        "healthy": (
                            symbol_stream_status.get("last_depth_ws_message_ms") is not None
                            and now_ms - int(symbol_stream_status["last_depth_ws_message_ms"]) <= self.config.strategy.stale_depth_after_ms
                            and bool(symbol_stream_status.get("order_book_synced"))
                        ),
                        "last_time_ms": symbol_stream_status.get("last_depth_ws_message_ms"),
                        "stale_after_ms": self.config.strategy.stale_depth_after_ms,
                        "order_book_health_state": symbol_stream_status.get("order_book_health_state"),
                        "depth_sync_state": symbol_stream_status.get("depth_sync_state"),
                        "repair_in_flight": symbol_stream_status.get("repair_in_flight"),
                        "last_good_depth_time_ms": symbol_stream_status.get("last_good_depth_time_ms"),
                        "last_gap_time_ms": symbol_stream_status.get("last_gap_time_ms"),
                        "last_rate_limit_time_ms": symbol_stream_status.get("last_rate_limit_time_ms"),
                        "buffered_event_count": symbol_stream_status.get("buffered_event_count", 0),
                        "backoff_until_ms": symbol_stream_status.get("order_book_next_bootstrap_after_ms"),
                        "rest_budget_state": symbol_stream_status.get("rest_budget_state"),
                        "depth_gap_count": symbol_stream_status.get("depth_gap_count", 0),
                        "depth_resync_count": symbol_stream_status.get("depth_resync_count", 0),
                        "depth_reconnect_resync_count": symbol_stream_status.get("depth_reconnect_resync_count", 0),
                        "depth_rate_limit_count": symbol_stream_status.get("depth_rate_limit_count", 0),
                    },
                }
            )
            if healthy and hasattr(self.candle_client, "get_microstructure_snapshot"):
                microstructure = await self.candle_client.get_microstructure_snapshot(
                    symbol,
                    windows_seconds=self.config.strategy.microstructure_windows_seconds,
                    now_ms=now_ms,
                )
                spread_block = self._spread_block(microstructure)
                if not microstructure.get("healthy", False):
                    healthy = False
                    stream_reason = "microstructure_unhealthy"
                    reason_code = "depth_degraded"
                elif spread_block is not None:
                    healthy = False
                    stream_reason = spread_block["reason_code"]
                    reason_code = spread_block["reason_code"]
                elif microstructure.get("degraded"):
                    reason_code = "depth_degraded"
        if healthy:
            safety = await self.store.get_safety_status()
            if safety and safety.reason == SafeModeReason.STALE_MARKET_DATA:
                await self.clear_safe_mode()
            health_state = SafetyState.DEGRADED if reason_code == "depth_degraded" else SafetyState.HEALTHY
            summary = "Market data healthy" if health_state == SafetyState.HEALTHY else "Market data degraded but entry-capable"
        else:
            reason_code = reason_code or str(SafeModeReason.STALE_MARKET_DATA)
            detail = (
                f"market data stream unhealthy: {stream_reason}"
                if stream_reason is not None
                else f"latest closed bar is stale: {latest_bar.time_ms}"
            )
            if reason_code == str(SafeModeReason.STALE_MARKET_DATA):
                await self.set_safe_mode(SafeModeReason.STALE_MARKET_DATA, detail)
                health_state = SafetyState.SAFE_MODE
            else:
                safety = await self.store.get_safety_status()
                if safety and safety.reason == SafeModeReason.STALE_MARKET_DATA:
                    await self.clear_safe_mode()
                health_state = SafetyState.DEGRADED
            summary = detail
        result = {
            "symbol": symbol,
            "healthy": healthy,
            "state": health_state,
            "reason_code": reason_code,
            "recommended_action": self._recommended_action(reason_code),
            "latest_bar_time_ms": latest_bar.time_ms,
            "latest_bar_close_time_ms": latest_bar_close_time_ms,
            "age_ms": now_ms - latest_bar_close_time_ms,
            "stream_status": stream_status,
            "stream_reason": stream_reason,
            "microstructure": microstructure,
            "feed_health": feed_health,
            "stale_after_ms": self.config.strategy.stale_bar_after_ms,
        }
        await self.store.append_execution_metric(
            metric_id=uuid4().hex,
            signal_id=None,
            symbol=symbol,
            metric_type="market_health",
            recorded_time_ms=now_ms,
            payload={
                "healthy": healthy,
                "state": str(health_state),
                "reason_code": reason_code,
                "stream_reason": stream_reason,
                "feed_health": feed_health,
            },
        )
        await self._record_health_transition(
            symbol=symbol,
            scope="market_data",
            state=str(health_state),
            reason_code=reason_code,
            summary=summary,
            payload=result,
        )
        self._trace("market_data:health", **result)
        return result

    async def refresh_execution_health(self) -> dict[str, Any]:
        async with self._op_lock:
            status = self.execution_adapter.get_stream_status()
            now_ms = self.clock()
            enabled = bool(status.get("enabled"))
            started = bool(status.get("started"))
            last_ws_message_ms = status.get("last_ws_message_ms")
            healthy = True
            reason = None
            if self.config.runtime_mode == RuntimeMode.LIVE and enabled:
                ws_ready = status.get("ws_ready")
                ws_keep_running = status.get("ws_keep_running")
                ws_connected = status.get("ws_connected")
                ws_telemetry_available = any(value is not None for value in (ws_ready, ws_keep_running, ws_connected))
                if not started:
                    healthy = False
                    reason = "stream_not_started"
                elif ws_keep_running is False:
                    healthy = False
                    reason = "ws_not_running"
                elif ws_connected is False:
                    healthy = False
                    reason = "ws_disconnected"
                elif ws_ready is False and status.get("started_ms") is not None:
                    if now_ms - int(status["started_ms"]) > self.config.hyperliquid.ws_stale_after_ms:
                        healthy = False
                        reason = "ws_not_ready"
                elif not ws_telemetry_available:
                    if last_ws_message_ms is None and status.get("started_ms") is not None:
                        if now_ms - int(status["started_ms"]) > self.config.hyperliquid.ws_stale_after_ms:
                            healthy = False
                            reason = "no_ws_messages"
                    elif last_ws_message_ms is not None and now_ms - int(last_ws_message_ms) > self.config.hyperliquid.ws_stale_after_ms:
                        healthy = False
                        reason = "stale_ws_messages"

                if healthy:
                    reconcile_health = await self._refresh_reconciliation_health_locked()
                    if not reconcile_health["healthy"]:
                        healthy = False
                        reason = "stale_reconciliation_gap"
                basis_health = await self._basis_health_snapshot()
                if healthy and not basis_health["healthy"]:
                    healthy = False
                    reason = "basis_dislocation"
                if healthy:
                    safety = await self.store.get_safety_status()
                    if safety and safety.reason in {SafeModeReason.HEARTBEAT_LOSS, SafeModeReason.BASIS_DISLOCATION}:
                        await self.clear_safe_mode()
                else:
                    if reason == "stale_reconciliation_gap":
                        await self._set_reconciliation_stale_safe_mode()
                    elif reason == "basis_dislocation":
                        await self.set_safe_mode(SafeModeReason.BASIS_DISLOCATION, basis_health["detail"])
                    else:
                        await self.set_safe_mode(SafeModeReason.HEARTBEAT_LOSS, f"hyperliquid stream unhealthy: {reason}")
            result = {
                "healthy": healthy,
                "state": SafetyState.HEALTHY if healthy else SafetyState.SAFE_MODE,
                "recommended_action": self._recommended_action(reason),
                "reason": reason,
                "status": status,
                "reconcile_health": await self._reconciliation_health_snapshot(),
                "basis_health": await self._basis_health_snapshot(),
            }
            await self.store.append_execution_metric(
                metric_id=uuid4().hex,
                signal_id=None,
                symbol="BTCUSDT",
                metric_type="execution_health",
                recorded_time_ms=now_ms,
                payload={
                    "healthy": healthy,
                    "state": str(result["state"]),
                    "reason_code": reason,
                    "last_ws_message_ms": status.get("last_ws_message_ms"),
                    "basis_health": result["basis_health"],
                    "reconcile_health": result["reconcile_health"],
                },
            )
            await self._record_health_transition(
                symbol="BTCUSDT",
                scope="execution",
                state=str(result["state"]),
                reason_code=reason,
                summary=("Execution health healthy" if healthy else f"Execution health degraded: {reason}"),
                payload=result,
            )
            self._trace("execution:health", **result)
            return result

    async def collect_system_snapshot(self, symbol: str) -> dict[str, Any]:
        market_health = await self.refresh_market_data_health(symbol)
        microstructure = None
        if hasattr(self.candle_client, "get_microstructure_snapshot"):
            try:
                microstructure = await self.candle_client.get_microstructure_snapshot(
                    symbol,
                    windows_seconds=self.config.strategy.microstructure_windows_seconds,
                    now_ms=self.clock(),
                )
            except Exception as exc:
                microstructure = {
                    "symbol": symbol,
                    "healthy": False,
                    "reasons": ["snapshot_error"],
                    "bootstrap_error": str(exc),
                }
        self._merge_microstructure_into_market_health(market_health, microstructure)
        stream_events = await self.sync_execution_events(symbol)
        position = await self.store.get_position_state(symbol)
        safety = await self.store.get_safety_status()
        live_exit = await self.inspect_live_exit(symbol)
        execution_health = await self.refresh_execution_health()
        market_stream_status = self.candle_client.get_stream_status() if hasattr(self.candle_client, "get_stream_status") else None
        supervision = await self.store.get_latest_supervision_snapshot(symbol)
        attribution = await self.store.summarize_runtime_metrics(symbol)
        safety_state = await self._safety_state_snapshot(symbol, market_health=market_health, execution_health=execution_health)
        snapshot = {
            "mode": self.config.runtime_mode,
            "symbol": symbol,
            "db_path": str(self.config.db_path),
            "position": (position.model_dump(mode="json") if position else {"status": "flat"}),
            "safety": (safety.model_dump(mode="json") if safety else {"in_safe_mode": False}),
            "safety_state": safety_state,
            "execution_health": execution_health,
            "market_data_health": market_health,
            "microstructure": microstructure,
            "execution_stream_status": self.execution_adapter.get_stream_status(),
            "market_stream_status": market_stream_status,
            "fresh_stream_events": stream_events,
            "live_exit_snapshot": live_exit,
            "supervision": supervision,
            "attribution": attribution,
            "recent_health_events": await self.store.list_recent_health_events(symbol=symbol, limit=10),
        }
        self._trace("system:snapshot", snapshot=snapshot)
        return snapshot

    def _merge_microstructure_into_market_health(
        self,
        market_health: dict[str, Any],
        microstructure: dict[str, Any] | None,
    ) -> None:
        if not microstructure:
            return
        market_health["microstructure"] = microstructure
        feed_health = market_health.setdefault("feed_health", {})
        if "trade_flow_available" in microstructure:
            feed_health["trades"] = {
                **feed_health.get("trades", {}),
                "healthy": bool(microstructure.get("trade_flow_available")),
                "last_time_ms": microstructure.get("last_trade_time_ms"),
            }
        if "top_of_book_available" in microstructure:
            feed_health["book_ticker"] = {
                **feed_health.get("book_ticker", {}),
                "healthy": bool(microstructure.get("top_of_book_available")),
                "last_time_ms": microstructure.get("last_book_ticker_time_ms"),
            }
        feed_health["depth"] = {
            **feed_health.get("depth", {}),
            "healthy": bool(microstructure.get("depth_healthy")),
            "last_time_ms": microstructure.get("last_depth_time_ms"),
            "order_book_health_state": microstructure.get("order_book_health_state"),
            "depth_sync_state": microstructure.get("depth_sync_state"),
            "repair_in_flight": microstructure.get("repair_in_flight"),
            "last_good_depth_time_ms": microstructure.get("last_good_depth_time_ms"),
            "last_gap_time_ms": microstructure.get("last_gap_time_ms"),
            "last_invalid_book_time_ms": microstructure.get("last_invalid_book_time_ms"),
            "last_rate_limit_time_ms": microstructure.get("last_rate_limit_time_ms"),
            "last_planned_reconnect_time_ms": microstructure.get("last_planned_reconnect_time_ms"),
            "next_planned_reconnect_time_ms": microstructure.get("next_planned_reconnect_time_ms"),
            "buffered_event_count": microstructure.get("buffered_event_count", 0),
            "backoff_until_ms": microstructure.get("backoff_until_ms"),
            "depth_gap_count": microstructure.get("depth_gap_count", 0),
            "depth_resync_count": microstructure.get("depth_resync_count", 0),
            "depth_reconnect_resync_count": microstructure.get("depth_reconnect_resync_count", 0),
            "depth_rate_limit_count": microstructure.get("depth_rate_limit_count", 0),
            "depth_gap_resync_count": microstructure.get("depth_gap_resync_count", 0),
            "depth_planned_reconnect_count": microstructure.get("depth_planned_reconnect_count", 0),
            "depth_error_reconnect_count": microstructure.get("depth_error_reconnect_count", 0),
            "depth_alignment_mismatch_count": microstructure.get("depth_alignment_mismatch_count", 0),
            "depth_invalid_book_count": microstructure.get("depth_invalid_book_count", 0),
            "depth_dropped_buffered_event_count": microstructure.get("depth_dropped_buffered_event_count", 0),
            "depth_buffer_high_watermark": microstructure.get("depth_buffer_high_watermark", 0),
            "book_validity_issue": microstructure.get("book_validity_issue"),
            "depth_required_levels": microstructure.get("depth_required_levels"),
        }

    async def sync_execution_events(self, symbol: str | None = None) -> list[dict[str, Any]]:
        events = await self.execution_adapter.drain_execution_events()
        if not events:
            return []

        matched_events: list[dict[str, Any]] = []
        symbols_to_reconcile: dict[str, ExitReason | None] = {}
        for event in events:
            event_symbol = event.get("symbol")
            if symbol is None or event_symbol == symbol:
                matched_events.append(event)
            await self.store.append_trade_event(
                event_id=uuid4().hex,
                signal_id=None,
                symbol=event_symbol or "system",
                event_type=f"stream_{event['event_type']}",
                event_time_ms=int(event.get("time_ms") or self.clock()),
                payload=event,
            )
            hint = self._exit_reason_from_stream_event(event)
            if event_symbol is not None and hint is not None:
                symbols_to_reconcile[event_symbol] = hint
            elif event_symbol is not None and event["event_type"] in {"fill", "order_update", "non_user_cancel"}:
                symbols_to_reconcile.setdefault(event_symbol, None)

        for reconcile_symbol, hint in symbols_to_reconcile.items():
            await self._reconcile_symbol_state(reconcile_symbol, exit_reason_hint=hint)

        self._trace("execution:stream_sync", event_count=len(events), matched_count=len(matched_events), events=matched_events)
        return matched_events

    async def _build_feature_snapshot(
        self,
        *,
        symbol: str,
        direction: SignalDirection,
        signal_time_ms: int,
        latest_bar,
        bars,
        atr: Decimal,
        hurst: Decimal | None,
        microstructure: dict[str, Any] | None,
        basis_snapshot: dict[str, Any] | None,
        funding_context: dict[str, Any] | None = None,
        open_interest_context: dict[str, Any] | None = None,
        premium_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if funding_context is None and hasattr(self.candle_client, "fetch_funding_context"):
            funding_context = await self.candle_client.fetch_funding_context(symbol, as_of_ms=signal_time_ms)
        if open_interest_context is None and hasattr(self.candle_client, "fetch_open_interest_context"):
            open_interest_context = await self.candle_client.fetch_open_interest_context(symbol, as_of_ms=signal_time_ms)
        if premium_context is None and hasattr(self.candle_client, "fetch_premium_context"):
            premium_context = await self.candle_client.fetch_premium_context(symbol, as_of_ms=signal_time_ms)
        snapshot = build_extended_feature_snapshot(
            signal_direction=direction,
            signal_time_ms=signal_time_ms,
            latest_bar=latest_bar,
            bars=bars,
            atr=atr,
            atr_length=self.config.strategy.atr_length,
            hurst=hurst,
            microstructure=microstructure,
            basis_snapshot=basis_snapshot,
            funding_context=funding_context,
            open_interest_context=open_interest_context,
            premium_context=premium_context,
            primary_window_seconds=self.config.strategy.microstructure_primary_window_seconds,
            volatility_config=self._volatility_feature_config(),
        )
        snapshot["rule_acceptance"] = evaluate_rule_acceptance(snapshot, self._rule_acceptance_settings())
        return snapshot

    def _scoring_skipped_payload(self, reason: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "observe_only": True,
            "status": "skipped",
            "scoring_fallback_reason": reason,
            "confidence_bucket": "unscored",
        }
        if self.scorer is not None:
            payload.update(
                {
                    "probability_threshold": self.scorer.plan.model.probability_threshold,
                    "model_version": self.scorer.manifest.get("model_version", "unavailable"),
                    "calibration_version": self.scorer.manifest.get("calibration_version", "unavailable"),
                    "artifact_manifest_version": self.scorer.manifest.get("artifact_manifest_version")
                    or self.scorer.manifest.get("train_manifest_version"),
                    "artifact_manifest_sha256": self.scorer.manifest_sha256,
                }
            )
        return payload

    def _score_feature_snapshot(self, feature_snapshot: dict[str, Any]) -> dict[str, Any]:
        if self.scorer is None:
            return self._scoring_skipped_payload("no_artifact_loaded")
        score = self.scorer.score_snapshot(feature_snapshot)
        score["status"] = "scored"
        return score

    async def handle_signal(self, signal: SignalIntent) -> tuple[DecisionPacket, list[ExecutionReport], ActionTicket]:
        async with self._op_lock:
            now_ms = self.clock()
            self._trace("signal:received", signal=signal.model_dump(mode="json"), now_ms=now_ms)
            if not await self.store.reserve_signal(signal):
                self._trace("signal:duplicate", signal_id=signal.signal_id, symbol=signal.symbol)
                packet = DecisionPacket(
                    signal=signal,
                    mode=self.config.runtime_mode,
                    action=DecisionAction.IGNORE,
                    accepted=False,
                    rejection_reason="duplicate_signal",
                    feature_snapshot={"duplicate": True},
                )
                await self.store.update_signal_decision(signal, accepted=False, rejection_reason=packet.rejection_reason)
                ticket = self._build_ticket(packet, [], now_ms, "duplicate")
                await self.store.save_action_ticket(ticket)
                return packet, [], ticket

            if self.config.runtime_mode == RuntimeMode.LIVE:
                await self._refresh_reconciliation_health_locked([signal.symbol])
            safety = await self.store.get_safety_status()
            self._trace("safety:status", safety=(safety.model_dump(mode="json") if safety else None))
            if safety and safety.in_safe_mode:
                packet = DecisionPacket(
                    signal=signal,
                    mode=self.config.runtime_mode,
                    action=DecisionAction.REJECT,
                    accepted=False,
                    rejection_reason=f"safe_mode:{safety.reason}",
                    feature_snapshot={"safe_mode_reason": safety.reason, "safe_mode_detail": safety.detail},
                )
                await self._persist_decision(packet, [], now_ms)
                ticket = self._build_ticket(packet, [], now_ms, "safe_mode")
                await self.store.save_action_ticket(ticket)
                return packet, [], ticket

            self._trace("market_data:fetch:start", symbol=signal.symbol)
            bars = await self.candle_client.fetch_recent_closed_bars(
                signal.symbol,
                max(
                    self.config.strategy.atr_length + self.config.binance.kline_limit_padding,
                    self.config.strategy.hurst_window_bars + 1,
                ),
            )
            self._trace("market_data:fetch:done", symbol=signal.symbol, bar_count=len(bars))
            if not bars:
                await self.set_safe_mode(SafeModeReason.STALE_MARKET_DATA, "no bars returned")
                packet = DecisionPacket(
                    signal=signal,
                    mode=self.config.runtime_mode,
                    action=DecisionAction.REJECT,
                    accepted=False,
                    rejection_reason="no_market_data",
                )
                await self._persist_decision(packet, [], now_ms)
                ticket = self._build_ticket(packet, [], now_ms, "no_market_data")
                await self.store.save_action_ticket(ticket)
                return packet, [], ticket

            latest_bar = bars[-1]
            self._trace("market_data:latest_bar", latest_bar=latest_bar.model_dump(mode="json"), now_ms=now_ms)
            latest_bar_close_time_ms = latest_bar.time_ms + BAR_INTERVAL_MS
            if now_ms - latest_bar_close_time_ms > self.config.strategy.stale_bar_after_ms:
                await self.set_safe_mode(SafeModeReason.STALE_MARKET_DATA, f"latest closed bar is stale: {latest_bar.time_ms}")
                packet = DecisionPacket(
                    signal=signal,
                    mode=self.config.runtime_mode,
                    action=DecisionAction.REJECT,
                    accepted=False,
                    rejection_reason="stale_market_data",
                    feature_snapshot={"latest_bar_time_ms": latest_bar.time_ms},
                )
                await self._persist_decision(packet, [], now_ms)
                ticket = self._build_ticket(packet, [], now_ms, "stale_market_data")
                await self.store.save_action_ticket(ticket)
                return packet, [], ticket

            atr = atr_wilder(bars, self.config.strategy.atr_length)
            hurst = hurst_exponent([bar.close for bar in bars[-self.config.strategy.hurst_window_bars :]])
            microstructure = (
                await self.candle_client.get_microstructure_snapshot(
                    signal.symbol,
                    windows_seconds=self.config.strategy.microstructure_windows_seconds,
                    now_ms=now_ms,
                )
                if hasattr(self.candle_client, "get_microstructure_snapshot")
                else None
            )
            funding_context = (
                await self.candle_client.fetch_funding_context(
                    signal.symbol,
                    as_of_ms=now_ms,
                )
                if hasattr(self.candle_client, "fetch_funding_context")
                else None
            )
            open_interest_context = (
                await self.candle_client.fetch_open_interest_context(
                    signal.symbol,
                    as_of_ms=now_ms,
                )
                if hasattr(self.candle_client, "fetch_open_interest_context")
                else None
            )
            premium_context = (
                await self.candle_client.fetch_premium_context(
                    signal.symbol,
                    as_of_ms=now_ms,
                )
                if hasattr(self.candle_client, "fetch_premium_context")
                else None
            )
            reference_price = latest_bar.close
            tp_price, sl_price = build_barriers(
                entry_price=reference_price,
                atr=atr,
                direction=signal.direction,
                tp_multiple=self.config.strategy.take_profit_atr_multiple,
                sl_multiple=self.config.strategy.stop_loss_atr_multiple,
                price_tick=self.config.strategy.price_tick,
            )
            vertical_barrier_time_ms = build_vertical_barrier(signal.signal_bar_time_ms, self.config.strategy.time_barrier_bars)
            current_position = await self.store.get_position_state(signal.symbol)
            self._trace(
                "decision:inputs",
                atr=str(atr),
                hurst=(str(hurst) if hurst is not None else None),
                reference_price=str(reference_price),
                tp_price=str(tp_price),
                sl_price=str(sl_price),
                vertical_barrier_time_ms=vertical_barrier_time_ms,
                microstructure=microstructure,
                current_position=(current_position.model_dump(mode="json") if current_position else None),
            )

            action = DecisionAction.ACCEPT
            accepted = True
            rejection_reason = None
            entry_blocker: dict[str, Any] | None = None
            if current_position and current_position.status == TradeStatus.OPEN and current_position.direction == signal.direction:
                action = DecisionAction.IGNORE
                accepted = False
                rejection_reason = "same_direction_position_open"
            elif current_position and current_position.status == TradeStatus.OPEN and current_position.direction != signal.direction:
                action = DecisionAction.FLIP
            elif microstructure is not None:
                accepted, rejection_reason = self._apply_microstructure_veto(signal, microstructure)
                if not accepted:
                    action = DecisionAction.REJECT

            basis_snapshot = await self._basis_snapshot(signal.symbol, microstructure)
            if accepted and basis_snapshot is not None and basis_snapshot.get("threshold_exceeded"):
                accepted = False
                action = DecisionAction.REJECT
                rejection_reason = "basis_dislocation"
            if accepted:
                blocked, blocker_payload = await self._daily_loss_blocked(signal.symbol, now_ms)
                if blocked and blocker_payload is not None:
                    accepted = False
                    action = DecisionAction.REJECT
                    rejection_reason = blocker_payload["reason_code"]
                    entry_blocker = blocker_payload
            if accepted:
                blocker_payload = self._open_risk_block(reference_price=reference_price, intended_size=self.config.strategy.order_size)
                if blocker_payload is not None:
                    accepted = False
                    action = DecisionAction.REJECT
                    rejection_reason = blocker_payload["reason_code"]
                    entry_blocker = blocker_payload
            if accepted:
                blocker_payload = self._spread_block(microstructure)
                if blocker_payload is not None:
                    accepted = False
                    action = DecisionAction.REJECT
                    rejection_reason = blocker_payload["reason_code"]
                    entry_blocker = blocker_payload

            packet = DecisionPacket(
                signal=signal,
                mode=self.config.runtime_mode,
                action=action,
                accepted=accepted,
                rejection_reason=rejection_reason,
                intended_size=self.config.strategy.order_size if accepted else Decimal("0"),
                entry_reference_price=reference_price if accepted else None,
                atr=atr if accepted else None,
                tp_price=tp_price if accepted else None,
                sl_price=sl_price if accepted else None,
                vertical_barrier_time_ms=vertical_barrier_time_ms if accepted else None,
                feature_snapshot=await self._build_feature_snapshot(
                    symbol=signal.symbol,
                    direction=signal.direction,
                    signal_time_ms=signal.signal_bar_time_ms,
                    latest_bar=latest_bar,
                    bars=bars,
                    atr=atr,
                    hurst=hurst,
                    microstructure=microstructure,
                    basis_snapshot=basis_snapshot,
                    funding_context=funding_context,
                    open_interest_context=open_interest_context,
                    premium_context=premium_context,
                ),
            )
            if entry_blocker is not None:
                packet.feature_snapshot["entry_blocker"] = entry_blocker
            normalize_packet = getattr(self.execution_adapter, "normalize_decision_packet", lambda value: value)
            packet = normalize_packet(packet)
            if self.config.runtime_mode == RuntimeMode.SHADOW:
                try:
                    score = self._score_feature_snapshot(packet.feature_snapshot)
                except Exception as exc:
                    self._trace("decision:v2_scoring_skipped", reason=str(exc))
                    score = self._scoring_skipped_payload(str(exc))
                packet = packet.model_copy(
                    update={
                        "confidence_bucket": score["confidence_bucket"],
                        "model_version": score.get("model_version", packet.model_version),
                        "calibration_version": score.get("calibration_version", packet.calibration_version),
                        "feature_snapshot": {
                            **packet.feature_snapshot,
                            "v2_acceptance": score,
                        },
                    }
                )
            self._trace("decision:packet", packet=packet.model_dump(mode="json"))
            execution_packet = packet

            reports: list[ExecutionReport] = []
            if accepted and current_position and current_position.status == TradeStatus.OPEN and current_position.direction != signal.direction:
                close_intents = build_close_intents(packet.mode, current_position)
                self._trace("execution:close_intents", intents=[intent.model_dump(mode="json") for intent in close_intents])
                close_reports = await self.execution_adapter.execute(close_intents) if close_intents else []
                self._trace("execution:close_reports", reports=[report.model_dump(mode="json") for report in close_reports])
                reports.extend(close_reports)
                if not await self._confirm_close(current_position, close_reports):
                    await self.set_safe_mode(SafeModeReason.POSITION_AMBIGUITY, "flip close could not be confirmed")
                    await self._persist_decision(packet, reports, now_ms)
                    ticket = self._build_ticket(packet, reports, now_ms, "flip_close_unconfirmed")
                    await self.store.save_action_ticket(ticket)
                    return packet, reports, ticket
                if packet.mode != RuntimeMode.SHADOW:
                    await self._close_position(current_position, close_reports, ExitReason.FLIP)

            entry_reports: list[ExecutionReport] = []
            protection_reports: list[ExecutionReport] = []
            entry_confirmed = False
            if accepted:
                open_intents = build_open_intents(packet)
                self._trace("execution:open_intents", intents=[intent.model_dump(mode="json") for intent in open_intents])
                entry_reports = await self.execution_adapter.execute(open_intents) if open_intents else []
                self._trace("execution:open_reports", reports=[report.model_dump(mode="json") for report in entry_reports])
                reports.extend(entry_reports)
                entry_confirmed = await self._entry_confirmed(packet.signal.symbol, entry_reports)
                if entry_confirmed:
                    execution_packet = normalize_packet(self._packet_with_filled_entry(packet, entry_reports))
                    entry_cloid = next((report.cloid for report in entry_reports if report.intent_type == ExecutionIntentType.ENTER), None)
                    protection_packet = normalize_packet(self._testnet_validation_protection_packet(execution_packet))
                    protective_intents = build_protective_intents(protection_packet, entry_cloid=entry_cloid)
                    self._trace("execution:protective_intents", intents=[intent.model_dump(mode="json") for intent in protective_intents])
                    protection_reports = await self.execution_adapter.execute(protective_intents) if protective_intents else []
                    self._trace("execution:protective_reports", reports=[report.model_dump(mode="json") for report in protection_reports])
                    reports.extend(protection_reports)
                    if execution_packet.mode == RuntimeMode.LIVE and any(report.status == ExecutionStatus.REJECTED for report in protection_reports):
                        await self.set_safe_mode(SafeModeReason.POSITION_AMBIGUITY, "protective order placement failed")
                elif packet.mode == RuntimeMode.LIVE:
                    await self.set_safe_mode(SafeModeReason.ORDER_TIMEOUT, "entry order was not confirmed; protections not placed")

            await self._apply_reports(execution_packet, current_position, reports, now_ms, entry_confirmed=entry_confirmed)
            await self._persist_decision(execution_packet, reports, now_ms)
            await self.store.append_execution_metric(
                metric_id=uuid4().hex,
                signal_id=execution_packet.signal.signal_id,
                symbol=execution_packet.signal.symbol,
                metric_type="decision",
                recorded_time_ms=now_ms,
                payload={
                    "mode": str(execution_packet.mode),
                    "action": str(execution_packet.action),
                    "accepted": execution_packet.accepted,
                    "rejection_reason": execution_packet.rejection_reason,
                    "decision_time_ms": now_ms,
                    "received_time_ms": execution_packet.signal.received_time_ms,
                    "decision_latency_ms": max(now_ms - execution_packet.signal.received_time_ms, 0),
                    "report_statuses": [str(report.status) for report in reports],
                    "entry_blocker": entry_blocker,
                    "basis": execution_packet.feature_snapshot.get("basis"),
                },
            )
            if self.config.runtime_mode == RuntimeMode.LIVE:
                await self.sync_execution_events(execution_packet.signal.symbol)
            ticket = self._build_ticket(execution_packet, reports, now_ms, execution_packet.action)
            await self.store.save_action_ticket(ticket)
            self._trace("signal:complete", ticket=ticket.model_dump(mode="json"))
            return execution_packet, reports, ticket

    async def supervise_position(self, symbol: str) -> list[ExecutionReport]:
        async with self._op_lock:
            position = await self.store.get_position_state(symbol)
            self._trace("supervision:start", symbol=symbol, position=(position.model_dump(mode="json") if position else None))
            if position is None or position.status != TradeStatus.OPEN:
                return []
            bars = await self.candle_client.fetch_recent_closed_bars(
                symbol,
                max(
                    2,
                    self.config.strategy.hurst_window_bars,
                    self.config.strategy.atr_length + 1,
                    self.config.strategy.time_barrier_bars + 1,
                ),
            )
            latest = bars[-1]
            exit_reason = evaluate_exit_on_bar(position, latest, self.clock())
            if exit_reason is None:
                exit_reason = await self._evaluate_adverse_selection_exit(position, bars, latest)
            if exit_reason is None:
                exit_reason = await self._evaluate_alpha_decay_exit(position, bars, latest)
            microstructure = (
                await self.candle_client.get_microstructure_snapshot(
                    symbol,
                    windows_seconds=self.config.strategy.microstructure_windows_seconds,
                    now_ms=self.clock(),
                )
                if hasattr(self.candle_client, "get_microstructure_snapshot")
                else None
            )
            basis_snapshot = await self._basis_snapshot(symbol, microstructure)
            supervision_summary = self._supervision_summary(
                position=position,
                latest_bar=latest,
                now_ms=self.clock(),
                candidate_exit_reason=exit_reason,
                bars=bars,
                microstructure=microstructure,
                basis_snapshot=basis_snapshot,
            )
            await self._persist_supervision_summary(symbol, supervision_summary)
            self._trace(
                "supervision:evaluate",
                symbol=symbol,
                latest_bar=latest.model_dump(mode="json"),
                exit_reason=exit_reason,
                supervision=supervision_summary,
            )
            if exit_reason is None:
                return []
            intents = build_close_intents(self.config.runtime_mode, position)
            reports = await self.execution_adapter.execute(intents)
            self._trace("supervision:reports", reports=[report.model_dump(mode="json") for report in reports])
            await self._close_position(position, reports, exit_reason, close_context=supervision_summary)
            return reports

    async def _evaluate_adverse_selection_exit(self, position, bars, latest_bar) -> ExitReason | None:
        plan = self.research_plan
        if plan is None or not plan.exit_supervision.adverse_selection_enabled:
            return None
        if position.entry_price is None or position.entry_atr is None or position.entry_bar_time_ms is None or position.direction is None:
            return None
        bars_since_entry = max(0, int((latest_bar.time_ms - position.entry_bar_time_ms) / BAR_INTERVAL_MS))
        if bars_since_entry <= 0 or bars_since_entry > plan.exit_supervision.adverse_selection_window_bars:
            return None
        position_bars = [bar for bar in bars if bar.time_ms >= position.entry_bar_time_ms]
        if not position_bars:
            return None
        if position.direction == SignalDirection.LONG:
            max_favorable_price = max(bar.high for bar in position_bars)
            favorable_excursion_atr = (max_favorable_price - position.entry_price) / position.entry_atr
        else:
            min_favorable_price = min(bar.low for bar in position_bars)
            favorable_excursion_atr = (position.entry_price - min_favorable_price) / position.entry_atr
        if favorable_excursion_atr >= Decimal(str(plan.exit_supervision.adverse_selection_min_favorable_excursion_atr)):
            return None
        if not hasattr(self.candle_client, "get_microstructure_snapshot"):
            return None
        microstructure = await self.candle_client.get_microstructure_snapshot(
            position.symbol,
            windows_seconds=self.config.strategy.microstructure_windows_seconds,
            now_ms=self.clock(),
        )
        if not microstructure.get("healthy", False):
            return None
        primary_window = (microstructure.get("windows") or {}).get(str(self.config.strategy.microstructure_primary_window_seconds), {})
        signed_ratio = Decimal(str(primary_window.get("signed_ratio", "0")))
        book_ratio = Decimal(str(microstructure.get("top_of_book_imbalance", "0")))
        signed_threshold = Decimal(str(plan.exit_supervision.adverse_selection_signed_imbalance_flip_threshold))
        book_threshold = Decimal(str(plan.exit_supervision.adverse_selection_book_imbalance_flip_threshold))
        if position.direction == SignalDirection.LONG:
            triggered = signed_ratio <= (-signed_threshold) and book_ratio <= (-book_threshold)
        else:
            triggered = signed_ratio >= signed_threshold and book_ratio >= book_threshold
        if triggered:
            self._trace(
                "supervision:adverse_selection",
                symbol=position.symbol,
                bars_since_entry=bars_since_entry,
                favorable_excursion_atr=str(favorable_excursion_atr),
                signed_ratio=str(signed_ratio),
                book_ratio=str(book_ratio),
            )
            return ExitReason.ADVERSE_SELECTION
        return None

    async def _evaluate_alpha_decay_exit(self, position, bars, latest_bar) -> ExitReason | None:
        plan = self.research_plan
        if plan is None or not plan.exit_supervision.alpha_decay_enabled or self.scorer is None:
            return None
        if position.entry_bar_time_ms is None or position.direction is None:
            return None
        bars_since_entry = max(0, int((latest_bar.time_ms - position.entry_bar_time_ms) / BAR_INTERVAL_MS))
        if bars_since_entry <= 0 or (bars_since_entry % max(plan.exit_supervision.alpha_decay_recheck_bars, 1)) != 0:
            return None
        atr = atr_wilder(bars, self.config.strategy.atr_length)
        hurst = hurst_exponent([bar.close for bar in bars[-self.config.strategy.hurst_window_bars :]])
        microstructure = (
            await self.candle_client.get_microstructure_snapshot(
                position.symbol,
                windows_seconds=self.config.strategy.microstructure_windows_seconds,
                now_ms=self.clock(),
            )
            if hasattr(self.candle_client, "get_microstructure_snapshot")
            else None
        )
        basis_snapshot = await self._basis_snapshot(position.symbol, microstructure)
        feature_snapshot = await self._build_feature_snapshot(
            symbol=position.symbol,
            direction=position.direction,
            signal_time_ms=latest_bar.time_ms,
            latest_bar=latest_bar,
            bars=bars,
            atr=atr,
            hurst=hurst,
            microstructure=microstructure,
            basis_snapshot=basis_snapshot,
        )
        score = self._score_feature_snapshot(feature_snapshot)
        if score.get("status") != "scored":
            return None
        if float(score["accept_probability"]) < float(plan.exit_supervision.alpha_decay_viability_threshold):
            self._trace(
                "supervision:alpha_decay",
                symbol=position.symbol,
                bars_since_entry=bars_since_entry,
                accept_probability=score["accept_probability"],
                threshold=plan.exit_supervision.alpha_decay_viability_threshold,
            )
            return ExitReason.ALPHA_DECAY
        return None

    def _supervision_summary(
        self,
        *,
        position,
        latest_bar,
        now_ms: int,
        candidate_exit_reason: ExitReason | None,
        bars: list[Any],
        microstructure: dict[str, Any] | None,
        basis_snapshot: dict[str, Any] | None,
    ) -> dict[str, Any]:
        bars_since_entry = (
            max(0, int((latest_bar.time_ms - position.entry_bar_time_ms) / BAR_INTERVAL_MS))
            if position.entry_bar_time_ms is not None
            else None
        )
        elapsed_ms = (max(now_ms - position.entry_time_ms, 0) if position.entry_time_ms is not None else None)
        mfe_price = None
        mae_price = None
        mfe_atr = None
        mae_atr = None
        if position.entry_price is not None and position.direction is not None and position.entry_atr not in {None, Decimal("0")}:
            relevant_bars = [bar for bar in bars if position.entry_bar_time_ms is None or bar.time_ms >= position.entry_bar_time_ms]
            if relevant_bars:
                if position.direction == SignalDirection.LONG:
                    favorable = max(bar.high for bar in relevant_bars)
                    adverse = min(bar.low for bar in relevant_bars)
                    mfe_price = favorable - position.entry_price
                    mae_price = position.entry_price - adverse
                else:
                    favorable = min(bar.low for bar in relevant_bars)
                    adverse = max(bar.high for bar in relevant_bars)
                    mfe_price = position.entry_price - favorable
                    mae_price = adverse - position.entry_price
                mfe_atr = mfe_price / position.entry_atr
                mae_atr = mae_price / position.entry_atr
        primary_window = (microstructure or {}).get("windows", {}).get(str(self.config.strategy.microstructure_primary_window_seconds), {})
        summary = {
            "summary": f"{position.symbol} supervision {candidate_exit_reason or 'hold'}",
            "symbol": position.symbol,
            "position_status": str(position.status),
            "direction": str(position.direction) if position.direction is not None else None,
            "candidate_exit_reason": str(candidate_exit_reason) if candidate_exit_reason is not None else None,
            "latest_bar_time_ms": latest_bar.time_ms,
            "latest_close": str(latest_bar.close),
            "bars_since_entry": bars_since_entry,
            "elapsed_ms": elapsed_ms,
            "time_to_barrier_ms": (
                max(position.vertical_barrier_time_ms - now_ms, 0) if position.vertical_barrier_time_ms is not None else None
            ),
            "mfe_price": (str(mfe_price) if mfe_price is not None else None),
            "mae_price": (str(mae_price) if mae_price is not None else None),
            "mfe_atr": (str(mfe_atr) if mfe_atr is not None else None),
            "mae_atr": (str(mae_atr) if mae_atr is not None else None),
            "signed_imbalance_ratio": primary_window.get("signed_ratio"),
            "top_of_book_imbalance": (microstructure or {}).get("top_of_book_imbalance"),
            "queue_imbalance_l1": (microstructure or {}).get("queue_imbalance_l1"),
            "queue_imbalance_l5": (microstructure or {}).get("queue_imbalance_l5"),
            "queue_imbalance_l10": (microstructure or {}).get("queue_imbalance_l10"),
            "basis_bps": (basis_snapshot or {}).get("basis_bps"),
            "entry_basis_bps": None,
        }
        return summary

    async def _persist_supervision_summary(self, symbol: str, summary: dict[str, Any]) -> None:
        await self.store.append_supervision_snapshot(
            snapshot_id=uuid4().hex,
            symbol=symbol,
            time_ms=self.clock(),
            payload=summary,
        )

    async def inspect_live_exit(self, symbol: str) -> dict[str, Any]:
        position = await self.store.get_position_state(symbol)
        now_ms = self.clock()
        snapshot: dict[str, Any] = {
            "symbol": symbol,
            "position": position.model_dump(mode="json") if position else None,
            "has_open_position": bool(position and position.status == TradeStatus.OPEN),
        }
        if position is None or position.status != TradeStatus.OPEN:
            self._trace("live_exit:inspect", **snapshot)
            return snapshot
        bars = await self.candle_client.fetch_recent_closed_bars(
            symbol,
            max(
                2,
                self.config.strategy.hurst_window_bars,
                self.config.strategy.atr_length + 1,
                self.config.strategy.time_barrier_bars + 1,
            ),
        )
        live_bar = await self.candle_client.fetch_latest_bar(symbol, include_incomplete=True)
        microstructure = (
            await self.candle_client.get_microstructure_snapshot(
                symbol,
                windows_seconds=self.config.strategy.microstructure_windows_seconds,
                now_ms=now_ms,
            )
            if hasattr(self.candle_client, "get_microstructure_snapshot")
            else None
        )
        basis_snapshot = await self._basis_snapshot(symbol, microstructure)
        candidate_exit_reason = evaluate_exit_on_bar(position, live_bar, now_ms)
        hold_until_ms = self._live_supervision_hold_until_by_symbol.get(symbol)
        hold_remaining_ms = None
        exit_reason = candidate_exit_reason
        suppressed_exit_reason = None
        if hold_until_ms is not None:
            if now_ms < hold_until_ms:
                hold_remaining_ms = max(hold_until_ms - now_ms, 0)
                suppressed_exit_reason = candidate_exit_reason
                exit_reason = None
            else:
                self._live_supervision_hold_until_by_symbol.pop(symbol, None)
        supervision_summary = self._supervision_summary(
            position=position,
            latest_bar=live_bar,
            now_ms=now_ms,
            candidate_exit_reason=exit_reason,
            bars=(bars[:-1] + [live_bar]) if bars and bars[-1].time_ms == live_bar.time_ms else (bars + [live_bar]),
            microstructure=microstructure,
            basis_snapshot=basis_snapshot,
        )
        await self._persist_supervision_summary(symbol, supervision_summary)
        snapshot.update(
            {
                "live_bar": live_bar.model_dump(mode="json"),
                "exit_reason": exit_reason,
                "suppressed_exit_reason": suppressed_exit_reason,
                "current_price": str(live_bar.close),
                "tp_distance": (str(position.tp_price - live_bar.close) if position.tp_price is not None else None),
                "sl_distance": (str(live_bar.close - position.sl_price) if position.sl_price is not None else None),
                "time_to_barrier_ms": (
                    max(position.vertical_barrier_time_ms - now_ms, 0) if position.vertical_barrier_time_ms is not None else None
                ),
                "supervision_hold_until_ms": hold_until_ms if hold_remaining_ms is not None else None,
                "supervision_hold_remaining_ms": hold_remaining_ms,
                "supervision": supervision_summary,
            }
        )
        self._trace("live_exit:inspect", **snapshot)
        return snapshot

    async def supervise_position_live(self, symbol: str) -> tuple[dict[str, Any], list[ExecutionReport]]:
        async with self._op_lock:
            snapshot = await self.inspect_live_exit(symbol)
            position = await self.store.get_position_state(symbol)
            exit_reason = snapshot.get("exit_reason")
            if position is None or position.status != TradeStatus.OPEN or exit_reason is None:
                return snapshot, []
            intents = build_close_intents(self.config.runtime_mode, position)
            self._trace("live_exit:intents", intents=[intent.model_dump(mode="json") for intent in intents])
            reports = await self.execution_adapter.execute(intents)
            self._trace("live_exit:reports", reports=[report.model_dump(mode="json") for report in reports])
            await self._close_position(position, reports, exit_reason, close_context=snapshot.get("supervision"))
            return snapshot, reports

    async def cancel_testnet_protective_orders(
        self,
        symbol: str,
        *,
        expected_tp_cloid: str | None = None,
        expected_sl_cloid: str | None = None,
        reason: str = "manual_testnet_cleanup",
    ) -> dict[str, Any]:
        async with self._op_lock:
            await self.sync_execution_events(symbol)
            position = await self.store.get_position_state(symbol)
            now_ms = self.clock()
            result: dict[str, Any] = {
                "symbol": symbol,
                "requested_reason": reason,
                "position_open": bool(position and position.status == TradeStatus.OPEN),
                "canceled_cloids": [],
                "reports": [],
                "skipped_reason": None,
            }
            cancel_intents: list[ExecutionIntent] = []
            matched_cloids: list[str] = []
            candidate_cloids = [
                ("tp", expected_tp_cloid),
                ("sl", expected_sl_cloid),
            ]
            if position is not None:
                candidate_cloids.extend(
                    [
                        ("tp", position.tp_order_cloid),
                        ("sl", position.sl_order_cloid),
                    ]
                )
            seen_cloids: set[str] = set()
            for label, cloid in candidate_cloids:
                if cloid is None or cloid in seen_cloids:
                    continue
                seen_cloids.add(cloid)
                matched_cloids.append(cloid)
                cancel_intents.append(
                    ExecutionIntent(
                        intent_id=f"{reason}:{label}:{cloid}",
                        mode=self.config.runtime_mode,
                        intent_type=ExecutionIntentType.CANCEL,
                        symbol=symbol,
                        size=Decimal("0"),
                        cloid=cloid,
                        reduce_only=True,
                        metadata={"cleanup_reason": reason},
                    )
                )

            if not cancel_intents:
                result["skipped_reason"] = "no_matching_protective_orders"
                self._trace("testnet_protection_cleanup:skip", **result)
                return result

            reports = await self.execution_adapter.execute(cancel_intents)
            for report in reports:
                await self.store.append_trade_event(
                    event_id=uuid4().hex,
                    signal_id=None,
                    symbol=symbol,
                    event_type=f"execution_{report.intent_type}_{report.status}",
                    event_time_ms=now_ms,
                    payload=report.model_dump(mode="json"),
                )

            canceled_cloids = {
                report.cloid
                for report in reports
                if report.cloid and report.status == ExecutionStatus.CANCELED
            }
            if position is not None:
                updated_position = position.model_copy(
                    update={
                        "tp_order_cloid": None if position.tp_order_cloid in canceled_cloids else position.tp_order_cloid,
                        "sl_order_cloid": None if position.sl_order_cloid in canceled_cloids else position.sl_order_cloid,
                        "last_updated_ms": now_ms,
                    }
                )
                await self.store.upsert_position_state(updated_position)
            await self.store.append_execution_metric(
                metric_id=uuid4().hex,
                signal_id=None,
                symbol=symbol,
                metric_type="testnet_protection_cleanup",
                recorded_time_ms=now_ms,
                payload={
                    "reason": reason,
                    "matched_cloids": matched_cloids,
                    "canceled_cloids": sorted(canceled_cloids),
                    "report_statuses": [str(report.status) for report in reports],
                },
            )
            result.update(
                {
                    "canceled_cloids": sorted(canceled_cloids),
                    "reports": [report.model_dump(mode="json") for report in reports],
                }
            )
            self._trace("testnet_protection_cleanup:done", **result)
            return result

    async def bootstrap_reconcile(self, symbol: str) -> None:
        async with self._op_lock:
            await self._reconcile_symbol_state(symbol)

    async def _set_reconciliation_stale_safe_mode(self) -> None:
        snapshot = await self._reconciliation_health_snapshot()
        if not snapshot["healthy"]:
            detail = "; ".join(
                f"{violation['symbol']} age_ms={violation['age_ms']} last_reconcile_ms={violation['last_reconcile_ms']}"
                for violation in snapshot["violations"]
            )
            safety = await self.store.get_safety_status()
            if safety is None or not safety.in_safe_mode or safety.reason == SafeModeReason.RECONCILIATION_STALE:
                await self.set_safe_mode(SafeModeReason.RECONCILIATION_STALE, detail)

    async def _refresh_reconciliation_health_locked(self, symbols: list[str] | None = None) -> dict[str, Any]:
        snapshot = await self._reconciliation_health_snapshot(symbols)
        if snapshot["healthy"]:
            safety = await self.store.get_safety_status()
            if safety and safety.reason == SafeModeReason.RECONCILIATION_STALE:
                await self.clear_safe_mode()
            return snapshot

        for violation in snapshot["violations"]:
            try:
                await self._reconcile_symbol_state(violation["symbol"])
            except Exception as exc:
                violation["error"] = str(exc)
        refreshed = await self._reconciliation_health_snapshot(symbols)
        if not refreshed["healthy"]:
            await self._set_reconciliation_stale_safe_mode()
        return refreshed

    async def _reconciliation_health_snapshot(self, symbols: list[str] | None = None) -> dict[str, Any]:
        now_ms = self.clock()
        positions = await self.store.list_position_states()
        violations: list[dict[str, Any]] = []
        for position in positions:
            if position.status != TradeStatus.OPEN:
                continue
            if symbols is not None and position.symbol not in symbols:
                continue
            last_reconcile_ms = position.last_exchange_reconcile_ms
            age_ms = None if last_reconcile_ms is None else now_ms - last_reconcile_ms
            if last_reconcile_ms is None or age_ms > self.config.strategy.max_reconcile_gap_ms:
                violations.append(
                    {
                        "symbol": position.symbol,
                        "last_reconcile_ms": last_reconcile_ms,
                        "age_ms": age_ms,
                    }
                )
        return {
            "healthy": not violations,
            "checked_symbols": sorted(symbols) if symbols is not None else sorted(position.symbol for position in positions if position.status == TradeStatus.OPEN),
            "violations": violations,
        }

    async def heartbeat_lost(self, detail: str) -> None:
        await self.set_safe_mode(SafeModeReason.HEARTBEAT_LOSS, detail)

    async def unresolved_position_mismatch(self, detail: str) -> None:
        await self.set_safe_mode(SafeModeReason.POSITION_AMBIGUITY, detail)

    def _packet_with_filled_entry(self, packet: DecisionPacket, reports: list[ExecutionReport]) -> DecisionPacket:
        entry_report = next((report for report in reports if report.intent_type == ExecutionIntentType.ENTER), None)
        if entry_report is None or entry_report.filled_price is None or packet.atr is None:
            return packet
        if not self._use_exchange_fill_for_canonical_pricing(packet):
            self._trace(
                "decision:filled_entry_adjustment_skipped",
                mode=str(packet.mode),
                symbol=packet.signal.symbol,
                reference_entry_price=str(packet.entry_reference_price),
                filled_entry_price=str(entry_report.filled_price),
                reason="live_testnet_uses_binance_canonical_pricing",
            )
            return packet
        tp_price, sl_price = build_barriers(
            entry_price=entry_report.filled_price,
            atr=packet.atr,
            direction=packet.signal.direction,
            tp_multiple=self.config.strategy.take_profit_atr_multiple,
            sl_multiple=self.config.strategy.stop_loss_atr_multiple,
            price_tick=self.config.strategy.price_tick,
        )
        updated_packet = packet.model_copy(
            update={
                "entry_reference_price": entry_report.filled_price,
                "tp_price": tp_price,
                "sl_price": sl_price,
            }
        )
        self._trace(
            "decision:filled_entry_adjustment",
            original_entry_price=str(packet.entry_reference_price),
            filled_entry_price=str(entry_report.filled_price),
            adjusted_tp_price=str(tp_price),
            adjusted_sl_price=str(sl_price),
        )
        return updated_packet

    async def _reconcile_symbol_state(self, symbol: str, *, exit_reason_hint: ExitReason | None = None) -> dict[str, Any]:
        persisted = await self.store.get_position_state(symbol)
        exchange = await self.execution_adapter.reconcile(symbol)
        exchange_size = Decimal(str(exchange.get("position_size", "0")))
        exchange_side = exchange.get("side")
        open_order_cloids = {str(cloid) for cloid in exchange.get("open_order_cloids", []) if cloid}
        now_ms = self.clock()
        self._trace(
            "reconcile:compare",
            symbol=symbol,
            persisted=(persisted.model_dump(mode="json") if persisted else None),
            exchange=exchange,
            exit_reason_hint=exit_reason_hint,
        )

        safety = await self.store.get_safety_status()
        mismatch = False
        mismatch_detail = ""
        if persisted and persisted.status == TradeStatus.OPEN:
            if exchange_size == Decimal("0"):
                await self._close_position(persisted, [], exit_reason_hint or ExitReason.UNKNOWN)
                await self.store.append_trade_event(
                    event_id=uuid4().hex,
                    signal_id=None,
                    symbol=symbol,
                    event_type=f"reconcile_close_{exit_reason_hint or ExitReason.UNKNOWN}",
                    event_time_ms=now_ms,
                    payload=exchange,
                )
            elif exchange_size != persisted.position_size:
                mismatch = self.config.runtime_mode == RuntimeMode.LIVE
                mismatch_detail = f"{symbol} local={persisted.position_size} exchange={exchange_size}"
            elif exchange_side is not None and exchange_side != persisted.direction:
                mismatch = self.config.runtime_mode == RuntimeMode.LIVE
                mismatch_detail = f"{symbol} local_side={persisted.direction} exchange_side={exchange_side}"
            else:
                updated_position = persisted.model_copy(
                    update={
                        "tp_order_cloid": (
                            persisted.tp_order_cloid if persisted.tp_order_cloid in open_order_cloids or persisted.tp_order_cloid is None else None
                        ),
                        "sl_order_cloid": (
                            persisted.sl_order_cloid if persisted.sl_order_cloid in open_order_cloids or persisted.sl_order_cloid is None else None
                        ),
                        "last_exchange_reconcile_ms": now_ms,
                        "last_updated_ms": now_ms,
                    }
                )
                await self.store.upsert_position_state(updated_position)
        elif exchange_size > Decimal("0") and self.config.runtime_mode == RuntimeMode.LIVE:
            mismatch = True
            mismatch_detail = f"{symbol} local=flat exchange={exchange_size}"

        if mismatch:
            await self.set_safe_mode(SafeModeReason.RECONCILIATION_MISMATCH, mismatch_detail)
        elif safety and safety.reason == SafeModeReason.RECONCILIATION_MISMATCH:
            await self.clear_safe_mode()
        await self.store.append_execution_metric(
            metric_id=uuid4().hex,
            signal_id=None,
            symbol=symbol,
            metric_type="reconcile",
            recorded_time_ms=now_ms,
            payload={
                "exchange_position_size": str(exchange_size),
                "exchange_side": str(exchange_side) if exchange_side is not None else None,
                "open_order_cloid_count": len(open_order_cloids),
                "mismatch": mismatch,
                "mismatch_detail": mismatch_detail,
                "exit_reason_hint": str(exit_reason_hint) if exit_reason_hint is not None else None,
            },
        )
        return exchange

    def _exit_reason_from_stream_event(self, event: dict[str, Any]) -> ExitReason | None:
        tracked_intent_type = event.get("tracked_intent_type")
        if tracked_intent_type == ExecutionIntentType.PROTECTIVE_TP:
            return ExitReason.TAKE_PROFIT
        if tracked_intent_type == ExecutionIntentType.PROTECTIVE_SL:
            return ExitReason.STOP_LOSS
        if tracked_intent_type == ExecutionIntentType.CLOSE:
            return ExitReason.UNKNOWN
        return None

    async def _apply_reports(
        self,
        packet: DecisionPacket,
        current_position,
        reports: list[ExecutionReport],
        now_ms: int,
        *,
        entry_confirmed: bool = True,
    ) -> None:
        if not packet.accepted:
            return

        if packet.mode == RuntimeMode.SHADOW:
            self._trace("position:shadow_skip", symbol=packet.signal.symbol)
            return

        fill_report = next(
            (
                report
                for report in reports
                if report.intent_type == "enter" and report.status in {"filled", "acked", "intended"}
            ),
            None,
        )
        for report in reports:
            await self.store.append_trade_event(
                event_id=uuid4().hex,
                signal_id=packet.signal.signal_id,
                symbol=packet.signal.symbol,
                event_type=f"execution_{report.intent_type}_{report.status}",
                event_time_ms=now_ms,
                payload=report.model_dump(mode="json"),
            )

        if packet.mode == RuntimeMode.LIVE and not entry_confirmed:
            self._trace("position:live_unconfirmed_skip", symbol=packet.signal.symbol)
            return
        if fill_report is None:
            await self.set_safe_mode(SafeModeReason.ORDER_TIMEOUT, "entry order did not produce a report")
            return

        position = current_position.model_copy() if current_position else None
        entry_price = packet.entry_reference_price
        exchange_entry_price = fill_report.filled_price if fill_report and fill_report.filled_price is not None else None
        if exchange_entry_price is not None and self._use_exchange_fill_for_canonical_pricing(packet):
            entry_price = fill_report.filled_price
        tp_cloid = next((report.cloid for report in reports if report.intent_type == "protective_tp"), None)
        sl_cloid = next((report.cloid for report in reports if report.intent_type == "protective_sl"), None)
        entry_cloid = next((report.cloid for report in reports if report.intent_type == "enter"), None)
        from tradingbotsuite.core.models import PositionState  # local import avoids cycle in typing

        position = PositionState(
            symbol=packet.signal.symbol,
            status=TradeStatus.OPEN,
            direction=packet.signal.direction,
            position_size=packet.intended_size,
            entry_price=entry_price,
            entry_time_ms=now_ms,
            entry_bar_time_ms=packet.signal.signal_bar_time_ms,
            entry_atr=packet.atr,
            hurst_at_entry=Decimal(str(packet.feature_snapshot["hurst"])) if packet.feature_snapshot.get("hurst") is not None else None,
            imbalance_at_entry=(
                Decimal(str(packet.feature_snapshot.get("primary_signed_imbalance_ratio")))
                if packet.feature_snapshot.get("primary_signed_imbalance_ratio") is not None
                else None
            ),
            tp_price=packet.tp_price,
            sl_price=packet.sl_price,
            vertical_barrier_time_ms=packet.vertical_barrier_time_ms,
            entry_order_cloid=entry_cloid,
            tp_order_cloid=tp_cloid,
            sl_order_cloid=sl_cloid,
            last_exchange_reconcile_ms=now_ms,
            last_updated_ms=now_ms,
        )
        await self.store.upsert_position_state(position)
        hold_until_ms = self._manual_live_testnet_hold_until_ms(packet, now_ms)
        if hold_until_ms is not None:
            self._live_supervision_hold_until_by_symbol[packet.signal.symbol] = hold_until_ms
            self._trace(
                "live_exit:manual_testnet_hold_armed",
                symbol=packet.signal.symbol,
                hold_until_ms=hold_until_ms,
                hold_for_ms=self.MANUAL_TESTNET_SUPERVISION_HOLDOFF_MS,
            )
        entry_report = next((report for report in reports if report.intent_type == ExecutionIntentType.ENTER), None)
        entry_slippage = (
            realized_slippage_bps(packet.entry_reference_price, exchange_entry_price, packet.signal.direction)
            if packet.entry_reference_price is not None and exchange_entry_price is not None
            else None
        )
        await self.store.append_execution_metric(
            metric_id=uuid4().hex,
            signal_id=packet.signal.signal_id,
            symbol=packet.signal.symbol,
            metric_type="trade_entry",
            recorded_time_ms=now_ms,
            payload={
                "entry_time_ms": now_ms,
                "decision_time_ms": now_ms,
                "entry_price": str(entry_price) if entry_price is not None else None,
                "exchange_entry_price": str(exchange_entry_price) if exchange_entry_price is not None else None,
                "entry_reference_price": str(packet.entry_reference_price) if packet.entry_reference_price is not None else None,
                "entry_slippage_bps": (str(entry_slippage) if entry_slippage is not None else None),
                "basis_entry_bps": ((packet.feature_snapshot.get("basis") or {}).get("basis_bps")),
                "position_size": str(packet.intended_size),
                "entry_order_cloid": entry_cloid,
                "entry_exchange_order_id": entry_report.exchange_order_id if entry_report is not None else None,
                "canonical_entry_source": ("binance_reference" if not self._use_exchange_fill_for_canonical_pricing(packet) else "exchange_fill"),
            },
        )
        self._trace("position:opened", position=position.model_dump(mode="json"))

    async def _close_position(
        self,
        position,
        reports: list[ExecutionReport],
        reason: ExitReason,
        *,
        close_context: dict[str, Any] | None = None,
    ) -> None:
        now_ms = self.clock()
        close_report = next((report for report in reports if report.intent_type == ExecutionIntentType.CLOSE), None)
        exit_price = close_report.filled_price if close_report is not None else None
        realized_pnl_quote = None
        if (
            position.entry_price is not None
            and exit_price is not None
            and position.position_size is not None
            and position.direction is not None
        ):
            if position.direction == SignalDirection.LONG:
                realized_pnl_quote = (exit_price - position.entry_price) * position.position_size
            else:
                realized_pnl_quote = (position.entry_price - exit_price) * position.position_size
        closed_state = position.model_copy(
            update={
                "status": TradeStatus.FLAT,
                "position_size": Decimal("0"),
                "last_exit_reason": reason,
                "last_exchange_reconcile_ms": now_ms,
                "last_updated_ms": now_ms,
                "tp_order_cloid": None,
                "sl_order_cloid": None,
            }
        )
        self._live_supervision_hold_until_by_symbol.pop(position.symbol, None)
        await self.store.upsert_position_state(closed_state)
        await self.store.append_execution_metric(
            metric_id=uuid4().hex,
            signal_id=None,
            symbol=position.symbol,
            metric_type="trade_close",
            recorded_time_ms=now_ms,
            payload={
                "exit_reason": str(reason),
                "exit_price": str(exit_price) if exit_price is not None else None,
                "entry_price": str(position.entry_price) if position.entry_price is not None else None,
                "position_size": str(position.position_size),
                "holding_time_ms": (max(now_ms - position.entry_time_ms, 0) if position.entry_time_ms is not None else None),
                "holding_bars": (close_context or {}).get("bars_since_entry"),
                "realized_pnl_quote": (str(realized_pnl_quote) if realized_pnl_quote is not None else None),
                "entry_slippage_bps": ((close_context or {}).get("entry_slippage_bps")),
                "basis_entry_bps": ((close_context or {}).get("entry_basis_bps")),
                "basis_exit_bps": ((close_context or {}).get("basis_bps")),
                "mfe_atr": ((close_context or {}).get("mfe_atr")),
                "mae_atr": ((close_context or {}).get("mae_atr")),
                "first_barrier_touched": (
                    str(reason)
                    if reason in {ExitReason.TAKE_PROFIT, ExitReason.STOP_LOSS, ExitReason.TIME_BARRIER}
                    else None
                ),
            },
        )
        self._trace("position:closed", symbol=position.symbol, reason=reason, state=closed_state.model_dump(mode="json"))
        for report in reports:
            await self.store.append_trade_event(
                event_id=uuid4().hex,
                signal_id=None,
                symbol=position.symbol,
                event_type=f"close_{reason}_{report.intent_type}_{report.status}",
                event_time_ms=now_ms,
                payload=report.model_dump(mode="json"),
            )

    async def _persist_decision(self, packet: DecisionPacket, reports: list[ExecutionReport], now_ms: int) -> None:
        await self.store.update_signal_decision(packet.signal, accepted=packet.accepted, rejection_reason=packet.rejection_reason)
        await self.store.save_decision_packet(packet, now_ms)
        await self.store.append_trade_event(
            event_id=uuid4().hex,
            signal_id=packet.signal.signal_id,
            symbol=packet.signal.symbol,
            event_type=f"decision_{packet.action}",
            event_time_ms=now_ms,
            payload={
                "packet": packet.model_dump(mode="json"),
                "reports": [report.model_dump(mode="json") for report in reports],
            },
        )
        self._trace("persistence:decision_saved", signal_id=packet.signal.signal_id, report_count=len(reports))

    def _build_ticket(
        self,
        packet: DecisionPacket,
        reports: list[ExecutionReport],
        now_ms: int,
        action_type: str,
    ) -> ActionTicket:
        readable_summary = f"{packet.signal.symbol} {packet.signal.direction} {packet.action} in {packet.mode}"
        return ActionTicket(
            ticket_id=uuid4().hex,
            signal_id=packet.signal.signal_id,
            mode=packet.mode,
            symbol=packet.signal.symbol,
            decision_time_ms=now_ms,
            action_type=str(action_type),
            readable_summary=readable_summary,
            features_json=packet.feature_snapshot,
            intended_orders_json=[report.model_dump(mode="json") for report in reports],
            rationale_json={
                "accepted": packet.accepted,
                "rejection_reason": packet.rejection_reason,
                "vertical_barrier_time_ms": packet.vertical_barrier_time_ms,
            },
        )

    def _trace(self, stage: str, **details: Any) -> None:
        if self.trace_sink is not None:
            self.trace_sink(stage, details)

    async def _safety_state_snapshot(
        self,
        symbol: str,
        *,
        market_health: dict[str, Any],
        execution_health: dict[str, Any],
    ) -> dict[str, Any]:
        safety = await self.store.get_safety_status()
        if safety and safety.in_safe_mode:
            return {
                "state": str(SafetyState.SAFE_MODE),
                "reason_code": safety.reason_code or str(safety.reason),
                "detail": safety.detail,
                "recommended_action": safety.recommended_action,
            }
        if not market_health.get("healthy", True):
            return {
                "state": str(market_health.get("state") or SafetyState.DEGRADED),
                "reason_code": market_health.get("reason_code"),
                "detail": market_health.get("stream_reason") or market_health.get("error") or "",
                "recommended_action": market_health.get("recommended_action"),
            }
        if not execution_health.get("healthy", True):
            return {
                "state": str(execution_health.get("state") or SafetyState.DEGRADED),
                "reason_code": execution_health.get("reason"),
                "detail": ((execution_health.get("basis_health") or {}).get("detail") or ""),
                "recommended_action": execution_health.get("recommended_action"),
            }
        return {
            "state": str(SafetyState.HEALTHY),
            "reason_code": None,
            "detail": "",
            "recommended_action": None,
        }

    def _apply_microstructure_veto(self, signal: SignalIntent, microstructure: dict[str, Any]) -> tuple[bool, str | None]:
        if not microstructure.get("healthy", False):
            return False, "microstructure_unhealthy"
        primary_window_key = str(self.config.strategy.microstructure_primary_window_seconds)
        primary_window = microstructure.get("windows", {}).get(primary_window_key)
        if not primary_window:
            return False, "missing_microstructure_window"
        signed_ratio = Decimal(str(primary_window.get("signed_ratio", "0")))
        book_ratio = Decimal(str(microstructure.get("top_of_book_imbalance", "0")))
        signed_threshold = self.config.strategy.signed_imbalance_ratio_threshold
        book_threshold = self.config.strategy.book_imbalance_ratio_threshold
        if signal.direction == "long":
            if signed_ratio < signed_threshold:
                return False, "signed_imbalance_veto"
            if book_ratio < book_threshold:
                return False, "book_imbalance_veto"
        else:
            if signed_ratio > (-signed_threshold):
                return False, "signed_imbalance_veto"
            if book_ratio > (-book_threshold):
                return False, "book_imbalance_veto"
        return True, None

    async def _basis_snapshot(self, symbol: str, microstructure: dict[str, Any] | None) -> dict[str, Any] | None:
        if self.config.runtime_mode != RuntimeMode.LIVE:
            return None
        if not hasattr(self.execution_adapter, "get_market_snapshot"):
            return None
        market_snapshot = await self.execution_adapter.get_market_snapshot(symbol)
        if market_snapshot is None or microstructure is None or microstructure.get("mid_price") is None:
            return None
        binance_mid = Decimal(str(microstructure["mid_price"]))
        hyperliquid_mid = Decimal(str(market_snapshot["mid_price"]))
        if binance_mid <= Decimal("0"):
            return None
        basis_bps = ((hyperliquid_mid - binance_mid) / binance_mid) * Decimal("10000")
        threshold = self.config.hyperliquid.max_basis_bps
        return {
            "binance_mid_price": str(binance_mid),
            "hyperliquid_mid_price": str(hyperliquid_mid),
            "basis_bps": str(basis_bps),
            "threshold_bps": str(threshold),
            "threshold_exceeded": threshold > Decimal("0") and abs(basis_bps) > threshold,
        }

    async def _basis_health_snapshot(self) -> dict[str, Any]:
        if self.config.runtime_mode != RuntimeMode.LIVE:
            return {"healthy": True, "violations": [], "detail": ""}
        positions = await self.store.list_position_states()
        violations: list[dict[str, Any]] = []
        for position in positions:
            if position.status != TradeStatus.OPEN:
                continue
            microstructure = (
                await self.candle_client.get_microstructure_snapshot(
                    position.symbol,
                    windows_seconds=self.config.strategy.microstructure_windows_seconds,
                    now_ms=self.clock(),
                )
                if hasattr(self.candle_client, "get_microstructure_snapshot")
                else None
            )
            snapshot = await self._basis_snapshot(position.symbol, microstructure)
            if snapshot is not None and snapshot.get("threshold_exceeded"):
                violations.append({"symbol": position.symbol, **snapshot})
        detail = "; ".join(
            f"{violation['symbol']} basis_bps={violation['basis_bps']} threshold_bps={violation['threshold_bps']}"
            for violation in violations
        )
        return {"healthy": not violations, "violations": violations, "detail": detail}

    async def _confirm_close(self, position, reports: list[ExecutionReport]) -> bool:
        close_report = next((report for report in reports if report.intent_type == ExecutionIntentType.CLOSE), None)
        if close_report is None:
            return False
        if self.config.runtime_mode in {RuntimeMode.PAPER, RuntimeMode.SHADOW}:
            return close_report.status in {ExecutionStatus.FILLED, ExecutionStatus.INTENDED}
        if isinstance(self.execution_adapter, HyperliquidExecutionAdapter):
            await self.execution_adapter.await_order_activity(
                symbol=position.symbol,
                cloid=close_report.cloid,
                exchange_order_id=close_report.exchange_order_id,
            )
            reconcile = await self.execution_adapter.reconcile(position.symbol)
            return Decimal(str(reconcile.get("position_size", "0"))) == Decimal("0")
        return False

    async def _entry_confirmed(self, symbol: str, reports: list[ExecutionReport]) -> bool:
        entry_report = next((report for report in reports if report.intent_type == ExecutionIntentType.ENTER), None)
        if entry_report is None:
            return False
        if self.config.runtime_mode == RuntimeMode.SHADOW:
            return True
        if self.config.runtime_mode == RuntimeMode.PAPER:
            return entry_report.status == ExecutionStatus.FILLED
        if isinstance(self.execution_adapter, HyperliquidExecutionAdapter):
            await self.execution_adapter.await_order_activity(
                symbol=symbol,
                cloid=entry_report.cloid,
                exchange_order_id=entry_report.exchange_order_id,
            )
            reconcile = await self.execution_adapter.reconcile(symbol)
            return Decimal(str(reconcile.get("position_size", "0"))) > Decimal("0")
        return False
