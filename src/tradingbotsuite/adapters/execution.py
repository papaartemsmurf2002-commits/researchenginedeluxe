from __future__ import annotations

import asyncio
from collections import deque
import threading
import time
from abc import ABC, abstractmethod
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from typing import Any
from uuid import uuid4

import requests
from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils.types import Cloid

from tradingbotsuite.config import HyperliquidConfig
from tradingbotsuite.core.math import apply_slippage, quantize_to_step
from tradingbotsuite.core.models import (
    DecisionPacket,
    ExecutionIntent,
    ExecutionIntentType,
    ExecutionReport,
    ExecutionStatus,
    PositionState,
    RuntimeMode,
    SignalDirection,
)


def make_cloid(prefix: str) -> str:
    return f"0x{uuid4().hex}"


def hyperliquid_symbol(symbol: str) -> str:
    if symbol == "BTCUSDT":
        return "BTC"
    if symbol == "ETHUSDT":
        return "ETH"
    return symbol


def internal_symbol(symbol: str) -> str:
    if symbol == "BTC":
        return "BTCUSDT"
    if symbol == "ETH":
        return "ETHUSDT"
    return symbol


def _normalize_order_status(value: Any) -> str:
    return str(value or "").strip().lower()


def _decimal_string(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral_value():
        return str(normalized.quantize(Decimal("1")))
    return format(normalized, "f")


def _is_terminal_order_status(status: str) -> bool:
    normalized = _normalize_order_status(status)
    return (
        normalized == "filled"
        or "cancel" in normalized
        or "reject" in normalized
        or "error" in normalized
        or "fail" in normalized
        or "margin" in normalized
    )


def _is_canceled_order_status(status: str) -> bool:
    normalized = _normalize_order_status(status)
    return "cancel" in normalized or "reject" in normalized or "error" in normalized or "fail" in normalized


def _is_open_order_status(status: str) -> bool:
    normalized = _normalize_order_status(status)
    return normalized in {"open", "triggered"}


def _is_benign_cancel_error(message: str) -> bool:
    normalized = _normalize_order_status(message)
    return "already canceled" in normalized or "already cancelled" in normalized or "never placed" in normalized or "filled" in normalized


def _normalize_spot_meta(spot_meta: dict[str, Any]) -> dict[str, Any]:
    tokens = spot_meta.get("tokens", [])
    if not tokens:
        return spot_meta
    max_index = max(int(token["index"]) for token in tokens)
    normalized_tokens: list[dict[str, Any]] = [{} for _ in range(max_index + 1)]
    for token in tokens:
        normalized_tokens[int(token["index"])] = token
    normalized = dict(spot_meta)
    normalized["tokens"] = normalized_tokens
    return normalized


def _fetch_hyperliquid_bootstrap_meta(base_url: str, timeout: float = 10.0) -> tuple[dict[str, Any], dict[str, Any]]:
    info_url = f"{base_url.rstrip('/')}/info"
    meta = requests.post(info_url, json={"type": "meta"}, timeout=timeout).json()
    spot_meta = requests.post(info_url, json={"type": "spotMeta"}, timeout=timeout).json()
    return meta, _normalize_spot_meta(spot_meta)


def build_close_intents(mode: RuntimeMode, position: PositionState) -> list[ExecutionIntent]:
    intents: list[ExecutionIntent] = []
    for order_cloid in (position.tp_order_cloid, position.sl_order_cloid):
        if order_cloid:
            intents.append(
                ExecutionIntent(
                    intent_id=f"cancel-{order_cloid}",
                    mode=mode,
                    intent_type=ExecutionIntentType.CANCEL,
                    symbol=position.symbol,
                    size=Decimal("0"),
                    cloid=order_cloid,
                    reduce_only=True,
                )
            )
    if position.position_size > 0 and position.direction is not None:
        intents.append(
            ExecutionIntent(
                intent_id=f"close-{position.symbol}-{uuid4().hex[:8]}",
                mode=mode,
                intent_type=ExecutionIntentType.CLOSE,
                symbol=position.symbol,
                direction=position.direction,
                size=position.position_size,
                reference_price=position.entry_price,
                cloid=make_cloid("close"),
                reduce_only=True,
            )
        )
    return intents


def build_entry_intents(packet: DecisionPacket, current_position: PositionState | None) -> list[ExecutionIntent]:
    intents: list[ExecutionIntent] = []
    if current_position and current_position.status == "open" and current_position.direction != packet.signal.direction:
        intents.extend(build_close_intents(packet.mode, current_position))
    intents.extend(build_open_intents(packet))
    return intents


def build_open_intents(packet: DecisionPacket) -> list[ExecutionIntent]:
    intents: list[ExecutionIntent] = []
    if packet.accepted and packet.entry_reference_price is not None and packet.intended_size > 0:
        entry_cloid = make_cloid("entry")
        intents.append(
            ExecutionIntent(
                intent_id=f"{packet.signal.signal_id}-enter",
                mode=packet.mode,
                intent_type=ExecutionIntentType.ENTER,
                symbol=packet.signal.symbol,
                direction=packet.signal.direction,
                size=packet.intended_size,
                reference_price=packet.entry_reference_price,
                cloid=entry_cloid,
                metadata={"signal_id": packet.signal.signal_id},
            )
        )
    return intents


def build_protective_intents(packet: DecisionPacket, entry_cloid: str | None = None) -> list[ExecutionIntent]:
    intents: list[ExecutionIntent] = []
    if packet.accepted and packet.intended_size > 0:
        if packet.tp_price is not None:
            intents.append(
                ExecutionIntent(
                    intent_id=f"{packet.signal.signal_id}-tp",
                    mode=packet.mode,
                    intent_type=ExecutionIntentType.PROTECTIVE_TP,
                    symbol=packet.signal.symbol,
                    direction=packet.signal.direction,
                    size=packet.intended_size,
                    reference_price=packet.tp_price,
                    trigger_price=packet.tp_price,
                    reduce_only=True,
                    cloid=make_cloid("tp"),
                    metadata={"entry_cloid": entry_cloid},
                )
            )
        if packet.sl_price is not None:
            intents.append(
                ExecutionIntent(
                    intent_id=f"{packet.signal.signal_id}-sl",
                    mode=packet.mode,
                    intent_type=ExecutionIntentType.PROTECTIVE_SL,
                    symbol=packet.signal.symbol,
                    direction=packet.signal.direction,
                    size=packet.intended_size,
                    reference_price=packet.sl_price,
                    trigger_price=packet.sl_price,
                    reduce_only=True,
                    cloid=make_cloid("sl"),
                    metadata={"entry_cloid": entry_cloid},
                )
            )
    return intents


class ExecutionAdapter(ABC):
    mode: RuntimeMode

    @abstractmethod
    async def execute(self, intents: list[ExecutionIntent]) -> list[ExecutionReport]:
        raise NotImplementedError

    def normalize_decision_packet(self, packet: DecisionPacket) -> DecisionPacket:
        return packet

    async def reconcile(self, symbol: str) -> dict[str, Any]:
        return {"symbol": symbol, "position_size": "0", "side": None, "open_order_cloids": []}

    async def shutdown(self) -> None:
        return None

    async def start_user_streams(self) -> None:
        return None

    def get_stream_status(self) -> dict[str, Any]:
        return {"enabled": False, "started": False}

    async def drain_execution_events(self) -> list[dict[str, Any]]:
        return []

    async def await_order_activity(
        self,
        *,
        symbol: str,
        cloid: str | None = None,
        exchange_order_id: str | None = None,
        timeout_ms: int | None = None,
    ) -> dict[str, Any] | None:
        return None

    def get_order_activity(self, *, cloid: str | None = None, exchange_order_id: str | None = None) -> dict[str, Any] | None:
        return None

    async def preflight_account(self) -> dict[str, Any]:
        return {"ok": True, "mode": str(self.mode)}

    async def get_market_snapshot(self, symbol: str) -> dict[str, Any] | None:
        return None

    async def list_frontend_open_orders(self, symbol: str) -> list[dict[str, Any]]:
        return []


class ShadowExecutionAdapter(ExecutionAdapter):
    mode = RuntimeMode.SHADOW

    async def execute(self, intents: list[ExecutionIntent]) -> list[ExecutionReport]:
        return [
            ExecutionReport(
                intent_id=intent.intent_id,
                intent_type=intent.intent_type,
                status=ExecutionStatus.INTENDED,
                symbol=intent.symbol,
                cloid=intent.cloid,
                filled_price=intent.reference_price,
                filled_size=intent.size,
                message="shadow mode",
                payload=intent.model_dump(mode="json"),
            )
            for intent in intents
        ]


class PaperExecutionAdapter(ExecutionAdapter):
    mode = RuntimeMode.PAPER

    def __init__(self, *, entry_slippage_bps: Decimal, exit_slippage_bps: Decimal, price_tick: Decimal, size_step: Decimal):
        self.entry_slippage_bps = entry_slippage_bps
        self.exit_slippage_bps = exit_slippage_bps
        self.price_tick = price_tick
        self.size_step = size_step

    async def execute(self, intents: list[ExecutionIntent]) -> list[ExecutionReport]:
        reports: list[ExecutionReport] = []
        for intent in intents:
            if intent.intent_type == ExecutionIntentType.CANCEL:
                reports.append(
                    ExecutionReport(
                        intent_id=intent.intent_id,
                        intent_type=intent.intent_type,
                        status=ExecutionStatus.CANCELED,
                        symbol=intent.symbol,
                        cloid=intent.cloid,
                        message="paper cancel acknowledged",
                    )
                )
                continue
            if intent.intent_type in {ExecutionIntentType.PROTECTIVE_TP, ExecutionIntentType.PROTECTIVE_SL}:
                reports.append(
                    ExecutionReport(
                        intent_id=intent.intent_id,
                        intent_type=intent.intent_type,
                        status=ExecutionStatus.ACKED,
                        symbol=intent.symbol,
                        cloid=intent.cloid,
                        message="paper protective order acknowledged",
                    )
                )
                continue

            fill_direction = SignalDirection.LONG
            if intent.intent_type == ExecutionIntentType.CLOSE and intent.direction == SignalDirection.LONG:
                fill_direction = SignalDirection.SHORT
            elif intent.direction is not None:
                fill_direction = intent.direction

            slippage_bps = self.entry_slippage_bps if intent.intent_type == ExecutionIntentType.ENTER else self.exit_slippage_bps
            reference = intent.reference_price or Decimal("0")
            fill_price = quantize_to_step(apply_slippage(reference, slippage_bps, fill_direction), self.price_tick)
            fill_size = quantize_to_step(intent.size, self.size_step)
            reports.append(
                ExecutionReport(
                    intent_id=intent.intent_id,
                    intent_type=intent.intent_type,
                    status=ExecutionStatus.FILLED,
                    symbol=intent.symbol,
                    exchange_order_id=uuid4().hex,
                    cloid=intent.cloid,
                    filled_price=fill_price,
                    filled_size=fill_size,
                    message="paper fill",
                )
            )
        return reports


class HyperliquidExecutionAdapter(ExecutionAdapter):
    mode = RuntimeMode.LIVE

    def __init__(
        self,
        config: HyperliquidConfig,
        *,
        exchange_client: Exchange | None = None,
        info_client: Info | None = None,
    ):
        self.config = config
        self._exchange = exchange_client
        self._info = info_client
        self._wallet = None
        self._enabled = False
        self._configured_account_address = config.account_address
        self._signing_address: str | None = None
        self._canonical_account_address: str | None = config.account_address
        self._account_role: str | None = None
        self._agent_source_address: str | None = None
        self._resolved_master_address: str | None = None
        self._last_preflight: dict[str, Any] | None = None
        self._stream_lock = threading.Lock()
        self._stream_started = False
        self._stream_started_ms: int | None = None
        self._last_ws_message_ms: int | None = None
        self._last_ws_channel: str | None = None
        self._last_order_update_ms: int | None = None
        self._last_user_event_ms: int | None = None
        self._last_fill_event_ms: int | None = None
        self._last_ws_payload: dict[str, Any] | None = None
        self._subscription_ids: list[tuple[dict[str, Any], int]] = []
        self._last_reconcile_ms: int | None = None
        self._stream_events: deque[dict[str, Any]] = deque(maxlen=512)
        self._seen_event_keys: deque[str] = deque(maxlen=2048)
        self._seen_event_key_set: set[str] = set()
        self._tracked_orders_by_cloid: dict[str, dict[str, Any]] = {}
        self._tracked_orders_by_oid: dict[str, dict[str, Any]] = {}
        if exchange_client is not None and info_client is not None:
            self._enabled = True
        elif config.enable_live and config.private_key:
            self._wallet = Account.from_key(config.private_key)
            self._signing_address = self._wallet.address
            meta, spot_meta = _fetch_hyperliquid_bootstrap_meta(config.base_url, timeout=10.0)
            self._info = Info(base_url=config.base_url, skip_ws=False, meta=meta, spot_meta=spot_meta, timeout=10.0)
            self._exchange = Exchange(
                wallet=self._wallet,
                base_url=config.base_url,
                meta=meta,
                vault_address=config.vault_address,
                account_address=config.account_address,
                spot_meta=spot_meta,
                timeout=10.0,
            )
            self._enabled = True
        if self._wallet is not None and self._signing_address is None:
            self._signing_address = self._wallet.address
        if self._enabled:
            self._resolve_account_context()

    def is_enabled(self) -> bool:
        return self._enabled

    def account_address(self) -> str | None:
        return self._canonical_account_address or self.config.vault_address or self._signing_address

    def signing_address(self) -> str | None:
        return self._signing_address

    def normalize_decision_packet(self, packet: DecisionPacket) -> DecisionPacket:
        if not packet.accepted:
            return packet
        normalized_size = self._normalize_size(packet.signal.symbol, packet.intended_size)
        normalized_tp = self._normalize_protective_price(packet, ExecutionIntentType.PROTECTIVE_TP)
        normalized_sl = self._normalize_protective_price(packet, ExecutionIntentType.PROTECTIVE_SL)
        feature_snapshot = dict(packet.feature_snapshot or {})
        if normalized_tp is not None:
            feature_snapshot["hyperliquid_tp_price"] = _decimal_string(normalized_tp)
        if normalized_sl is not None:
            feature_snapshot["hyperliquid_sl_price"] = _decimal_string(normalized_sl)
        if normalized_size != packet.intended_size:
            feature_snapshot["hyperliquid_size"] = _decimal_string(normalized_size)
        return packet.model_copy(
            update={
                "intended_size": normalized_size,
                "tp_price": normalized_tp,
                "sl_price": normalized_sl,
                "feature_snapshot": feature_snapshot,
            }
        )

    async def start_user_streams(self) -> None:
        if not self._enabled or self._info is None or self._stream_started or not hasattr(self._info, "subscribe"):
            return
        address = self.account_address()
        if address is None:
            return
        subscriptions = [
            {"type": "orderUpdates", "user": address},
            {"type": "userEvents", "user": address},
            {"type": "userFills", "user": address},
        ]
        for subscription in subscriptions:
            subscription_id = await asyncio.to_thread(self._info.subscribe, subscription, self._handle_ws_message)
            self._subscription_ids.append((subscription, subscription_id))
        self._stream_started = True
        self._stream_started_ms = int(time.time() * 1000)

    async def shutdown(self) -> None:
        if self._info is None:
            return
        if self._stream_started:
            for subscription, subscription_id in list(self._subscription_ids):
                try:
                    if hasattr(self._info, "unsubscribe"):
                        await asyncio.to_thread(self._info.unsubscribe, subscription, subscription_id)
                except Exception:  # pragma: no cover - defensive cleanup
                    pass
            self._subscription_ids.clear()
            self._stream_started = False
        if self._enabled:
            try:
                if hasattr(self._info, "disconnect_websocket"):
                    await asyncio.to_thread(self._info.disconnect_websocket)
            except Exception:  # pragma: no cover - defensive cleanup
                pass

    def get_stream_status(self) -> dict[str, Any]:
        ws_ready = None
        ws_keep_running = None
        ws_connected = None
        ws_manager = getattr(self._info, "ws_manager", None)
        if ws_manager is not None:
            ws_ready = bool(getattr(ws_manager, "ws_ready", False))
            ws_app = getattr(ws_manager, "ws", None)
            if ws_app is not None:
                keep_running = getattr(ws_app, "keep_running", None)
                ws_keep_running = bool(keep_running) if keep_running is not None else None
                ws_sock = getattr(ws_app, "sock", None)
                if ws_sock is not None:
                    connected = getattr(ws_sock, "connected", None)
                    ws_connected = bool(connected) if connected is not None else None
        with self._stream_lock:
            return {
                "enabled": self._enabled,
                "started": self._stream_started,
                "started_ms": self._stream_started_ms,
                "last_ws_message_ms": self._last_ws_message_ms,
                "last_ws_channel": self._last_ws_channel,
                "last_order_update_ms": self._last_order_update_ms,
                "last_user_event_ms": self._last_user_event_ms,
                "last_fill_event_ms": self._last_fill_event_ms,
                "subscription_count": len(self._subscription_ids),
                "account_address": self.account_address(),
                "configured_account_address": self._configured_account_address,
                "signing_address": self.signing_address(),
                "account_role": self._account_role,
                "resolved_master_address": self._resolved_master_address,
                "queued_event_count": len(self._stream_events),
                "tracked_order_count": len(self._tracked_orders_by_cloid),
                "last_reconcile_ms": self._last_reconcile_ms,
                "ws_ready": ws_ready,
                "ws_keep_running": ws_keep_running,
                "ws_connected": ws_connected,
            }

    def _handle_ws_message(self, ws_msg: Any) -> None:
        now_ms = int(time.time() * 1000)
        channel = ws_msg.get("channel") if isinstance(ws_msg, dict) else None
        normalized_events = self._normalize_stream_events(ws_msg, now_ms)
        with self._stream_lock:
            self._last_ws_message_ms = now_ms
            self._last_ws_channel = channel
            self._last_ws_payload = ws_msg if isinstance(ws_msg, dict) else {"raw": ws_msg}
            if channel == "orderUpdates":
                self._last_order_update_ms = now_ms
            elif channel == "user":
                self._last_user_event_ms = now_ms
            elif channel == "userFills":
                self._last_fill_event_ms = now_ms
            for event in normalized_events:
                self._record_stream_event_locked(event)

    async def drain_execution_events(self) -> list[dict[str, Any]]:
        with self._stream_lock:
            events = list(self._stream_events)
            self._stream_events.clear()
        return events

    def get_order_activity(self, *, cloid: str | None = None, exchange_order_id: str | None = None) -> dict[str, Any] | None:
        with self._stream_lock:
            tracked = self._lookup_tracked_order_locked(cloid=cloid, exchange_order_id=exchange_order_id)
            return dict(tracked) if tracked is not None else None

    async def await_order_activity(
        self,
        *,
        symbol: str,
        cloid: str | None = None,
        exchange_order_id: str | None = None,
        timeout_ms: int | None = None,
    ) -> dict[str, Any] | None:
        wait_window_ms = timeout_ms if timeout_ms is not None else max(self.config.order_timeout_seconds * 1000, 750)
        deadline = time.monotonic() + (wait_window_ms / 1000.0)
        last_snapshot: dict[str, Any] | None = None
        while time.monotonic() <= deadline:
            snapshot = self.get_order_activity(cloid=cloid, exchange_order_id=exchange_order_id)
            if snapshot is not None:
                last_snapshot = snapshot
                if snapshot.get("has_fill") or snapshot.get("terminal") or snapshot.get("last_order_status") or snapshot.get("submit_status") == ExecutionStatus.FILLED:
                    return snapshot
            external_status = await self.query_order_status(cloid=cloid, exchange_order_id=exchange_order_id)
            if external_status is not None:
                self._record_query_status(symbol=symbol, cloid=cloid, exchange_order_id=exchange_order_id, status_payload=external_status)
                snapshot = self.get_order_activity(cloid=cloid, exchange_order_id=exchange_order_id)
                if snapshot is not None:
                    last_snapshot = snapshot
                    if snapshot.get("has_fill") or snapshot.get("terminal") or snapshot.get("last_order_status"):
                        return snapshot
            await asyncio.sleep(0.05)
        return last_snapshot

    async def preflight_account(self) -> dict[str, Any]:
        result = {
            "ok": True,
            "enabled": self._enabled,
            "configured_account_address": self._configured_account_address,
            "signing_address": self.signing_address(),
            "account_address": self.account_address(),
            "account_role": self._account_role,
            "resolved_master_address": self._resolved_master_address,
        }
        if not self._enabled or self._info is None:
            result["ok"] = False
            result["reason"] = "live_execution_not_configured"
            self._last_preflight = result
            return result
        address = self.account_address()
        if address is None:
            result["ok"] = False
            result["reason"] = "missing_account_address"
            self._last_preflight = result
            return result

        user_state = await asyncio.to_thread(self._info.user_state, address)
        spot_state = await asyncio.to_thread(self._info.spot_user_state, address) if hasattr(self._info, "spot_user_state") else {"balances": []}
        abstraction = (
            await asyncio.to_thread(self._info.query_user_abstraction_state, address)
            if hasattr(self._info, "query_user_abstraction_state")
            else None
        )
        margin_account_value = Decimal(str(user_state.get("marginSummary", {}).get("accountValue", "0")))
        balances = spot_state.get("balances", [])
        spot_balances = [balance for balance in balances if Decimal(str(balance.get("total", "0"))) > Decimal("0")]
        result.update(
            {
                "margin_account_value": str(margin_account_value),
                "spot_balance_count": len(spot_balances),
                "spot_balances": spot_balances,
                "user_abstraction": abstraction,
            }
        )
        if margin_account_value <= Decimal("0") and not spot_balances:
            result["ok"] = False
            result["reason"] = "no_account_equity"
        self._last_preflight = result
        return result

    async def get_market_snapshot(self, symbol: str) -> dict[str, Any] | None:
        if not self._enabled or self._info is None or not hasattr(self._info, "all_mids"):
            return None
        mids = await asyncio.to_thread(self._info.all_mids)
        coin = hyperliquid_symbol(symbol)
        if coin not in mids:
            return None
        return {
            "symbol": symbol,
            "coin": coin,
            "mid_price": str(Decimal(str(mids[coin]))),
            "source": "hyperliquid_all_mids",
        }

    async def list_frontend_open_orders(self, symbol: str) -> list[dict[str, Any]]:
        if not self._enabled or self._info is None or not hasattr(self._info, "frontend_open_orders"):
            return []
        address = self.account_address()
        if address is None:
            return []
        orders = await asyncio.to_thread(self._info.frontend_open_orders, address)
        coin = hyperliquid_symbol(symbol)
        if not isinstance(orders, list):
            return []
        return [order for order in orders if isinstance(order, dict) and order.get("coin") == coin]

    async def query_order_status(self, *, cloid: str | None = None, exchange_order_id: str | None = None, dex: str = "") -> dict[str, Any] | None:
        if not self._enabled or self._info is None:
            return None
        address = self.account_address()
        if address is None:
            return None
        oid: int | str | None = None
        if exchange_order_id is not None:
            oid = int(exchange_order_id)
        elif cloid is not None:
            oid = cloid
        if oid is None:
            return None
        payload: dict[str, Any] = {"type": "orderStatus", "user": address, "oid": oid}
        if dex:
            payload["dex"] = dex
        return await asyncio.to_thread(self._info.post, "/info", payload)

    def _order_status_snapshot(self, status_payload: dict[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(status_payload, dict):
            return None
        status_type = _normalize_order_status(status_payload.get("status"))
        if status_type == "unknownoid":
            return {
                "status": status_type,
                "exchange_order_id": None,
                "cloid": None,
            }
        if status_type != "order":
            return None
        wrapper = status_payload.get("order", {})
        if not isinstance(wrapper, dict):
            return None
        order = wrapper.get("order", {})
        if not isinstance(order, dict):
            return None
        return {
            "status": _normalize_order_status(wrapper.get("status")),
            "exchange_order_id": (str(order.get("oid")) if order.get("oid") is not None else None),
            "cloid": (str(order.get("cloid")) if order.get("cloid") is not None else None),
        }

    def _report_from_exchange_result(self, intent: ExecutionIntent, result: Any) -> ExecutionReport:
        status = ExecutionStatus.ACKED
        exchange_order_id = None
        filled_price = None
        filled_size = None
        message = "live execution response"
        if isinstance(result, dict):
            statuses = result.get("response", {}).get("data", {}).get("statuses", [])
            if statuses:
                first = statuses[0]
                if "filled" in first:
                    status = ExecutionStatus.FILLED
                    exchange_order_id = str(first["filled"].get("oid"))
                    if first["filled"].get("avgPx") is not None:
                        filled_price = Decimal(str(first["filled"]["avgPx"]))
                    if first["filled"].get("totalSz") is not None:
                        filled_size = Decimal(str(first["filled"]["totalSz"]))
                elif "resting" in first:
                    status = ExecutionStatus.ACKED
                    exchange_order_id = str(first["resting"].get("oid"))
                elif "success" in first:
                    status = ExecutionStatus.CANCELED
                elif "error" in first:
                    message = str(first["error"])
                    status = (
                        ExecutionStatus.CANCELED
                        if intent.intent_type == ExecutionIntentType.CANCEL and _is_benign_cancel_error(message)
                        else ExecutionStatus.REJECTED
                    )
        return ExecutionReport(
            intent_id=intent.intent_id,
            intent_type=intent.intent_type,
            status=status,
            symbol=intent.symbol,
            exchange_order_id=exchange_order_id,
            cloid=intent.cloid,
            filled_price=filled_price,
            filled_size=filled_size,
            message=message,
            payload=result if isinstance(result, dict) else {"result": result},
        )

    async def _cancel_with_verification(self, intent: ExecutionIntent, coin: str) -> ExecutionReport:
        assert self._exchange is not None
        initial_result = await asyncio.to_thread(
            self._exchange.bulk_cancel_by_cloid,
            [{"coin": coin, "cloid": Cloid.from_str(intent.cloid)}],
        )
        report = self._report_from_exchange_result(intent, initial_result)
        status_payload = await self.query_order_status(cloid=intent.cloid, exchange_order_id=report.exchange_order_id)
        snapshot = self._order_status_snapshot(status_payload)
        if snapshot is not None:
            if snapshot["exchange_order_id"] is not None and report.exchange_order_id is None:
                report = report.model_copy(update={"exchange_order_id": snapshot["exchange_order_id"]})
            status_text = snapshot["status"]
            if status_text == "unknownoid" or _is_canceled_order_status(status_text):
                return report.model_copy(update={"status": ExecutionStatus.CANCELED})
            if _is_open_order_status(status_text) and snapshot["exchange_order_id"] is not None:
                fallback_result = await asyncio.to_thread(
                    self._exchange.bulk_cancel,
                    [{"coin": coin, "oid": int(snapshot["exchange_order_id"])}],
                )
                fallback_report = self._report_from_exchange_result(intent, fallback_result).model_copy(
                    update={"exchange_order_id": snapshot["exchange_order_id"]}
                )
                verified_payload = await self.query_order_status(exchange_order_id=snapshot["exchange_order_id"])
                verified_snapshot = self._order_status_snapshot(verified_payload)
                if verified_snapshot is None or verified_snapshot["status"] == "unknownoid" or _is_canceled_order_status(verified_snapshot["status"]):
                    return fallback_report.model_copy(update={"status": ExecutionStatus.CANCELED})
                return fallback_report.model_copy(
                    update={
                        "status": ExecutionStatus.REJECTED,
                        "message": f"cancel verification failed; order still {verified_snapshot['status']}",
                    }
                )
        frontend_orders = await self.list_frontend_open_orders(intent.symbol)
        for order in frontend_orders:
            cloid = order.get("cloid")
            if cloid is not None and intent.cloid is not None and str(cloid) != intent.cloid:
                continue
            oid = order.get("oid")
            if oid is None:
                continue
            fallback_result = await asyncio.to_thread(
                self._exchange.bulk_cancel,
                [{"coin": coin, "oid": int(oid)}],
            )
            fallback_report = self._report_from_exchange_result(intent, fallback_result).model_copy(
                update={"exchange_order_id": str(oid)}
            )
            return fallback_report.model_copy(update={"status": ExecutionStatus.CANCELED})
        return report

    def _normalize_stream_events(self, ws_msg: Any, now_ms: int) -> list[dict[str, Any]]:
        if not isinstance(ws_msg, dict):
            return []
        channel = ws_msg.get("channel")
        data = ws_msg.get("data")
        if channel == "orderUpdates":
            return self._normalize_order_update_events(data, now_ms)
        if channel == "userFills":
            return self._normalize_fill_events(data, now_ms, source="userFills")
        if channel == "user":
            return self._normalize_user_events(data, now_ms)
        return []

    def _normalize_order_update_events(self, data: Any, now_ms: int) -> list[dict[str, Any]]:
        raw_orders = data.get("orders") if isinstance(data, dict) and isinstance(data.get("orders"), list) else data
        if not isinstance(raw_orders, list):
            return []
        events: list[dict[str, Any]] = []
        for item in raw_orders:
            if not isinstance(item, dict):
                continue
            order = item.get("order", {})
            if not isinstance(order, dict):
                continue
            coin = str(order.get("coin") or "")
            oid = order.get("oid")
            cloid = order.get("cloid")
            status_raw = item.get("status")
            events.append(
                {
                    "event_type": "order_update",
                    "event_source": "orderUpdates",
                    "symbol": internal_symbol(coin),
                    "coin": coin,
                    "cloid": str(cloid) if cloid is not None else None,
                    "exchange_order_id": str(oid) if oid is not None else None,
                    "status": _normalize_order_status(status_raw),
                    "status_raw": status_raw,
                    "time_ms": int(item.get("statusTimestamp") or now_ms),
                    "limit_price": str(order.get("limitPx")) if order.get("limitPx") is not None else None,
                    "size": str(order.get("sz")) if order.get("sz") is not None else None,
                    "raw": item,
                }
            )
        return events

    def _normalize_fill_events(self, data: Any, now_ms: int, *, source: str) -> list[dict[str, Any]]:
        if not isinstance(data, dict):
            return []
        raw_fills = data.get("fills", [])
        if not isinstance(raw_fills, list):
            return []
        is_snapshot = bool(data.get("isSnapshot"))
        events: list[dict[str, Any]] = []
        for fill in raw_fills:
            if not isinstance(fill, dict):
                continue
            coin = str(fill.get("coin") or "")
            oid = fill.get("oid")
            events.append(
                {
                    "event_type": "fill",
                    "event_source": source,
                    "symbol": internal_symbol(coin),
                    "coin": coin,
                    "cloid": None,
                    "exchange_order_id": str(oid) if oid is not None else None,
                    "fill_price": str(fill.get("px")) if fill.get("px") is not None else None,
                    "fill_size": str(fill.get("sz")) if fill.get("sz") is not None else None,
                    "side": fill.get("side"),
                    "dir": fill.get("dir"),
                    "hash": fill.get("hash"),
                    "tid": fill.get("tid"),
                    "is_snapshot": is_snapshot,
                    "closed_pnl": str(fill.get("closedPnl")) if fill.get("closedPnl") is not None else None,
                    "time_ms": int(fill.get("time") or now_ms),
                    "raw": fill,
                }
            )
        return events

    def _normalize_user_events(self, data: Any, now_ms: int) -> list[dict[str, Any]]:
        if not isinstance(data, dict):
            return []
        if "fills" in data:
            return self._normalize_fill_events({"fills": data.get("fills", []), "isSnapshot": False}, now_ms, source="userEvents")
        if "nonUserCancel" in data and isinstance(data.get("nonUserCancel"), list):
            events: list[dict[str, Any]] = []
            for item in data["nonUserCancel"]:
                if not isinstance(item, dict):
                    continue
                coin = str(item.get("coin") or "")
                oid = item.get("oid")
                events.append(
                    {
                        "event_type": "non_user_cancel",
                        "event_source": "userEvents",
                        "symbol": internal_symbol(coin),
                        "coin": coin,
                        "cloid": None,
                        "exchange_order_id": str(oid) if oid is not None else None,
                        "time_ms": now_ms,
                        "raw": item,
                    }
                )
            return events
        if "funding" in data:
            funding = data["funding"]
            return [
                {
                    "event_type": "funding",
                    "event_source": "userEvents",
                    "symbol": None,
                    "coin": funding.get("coin"),
                    "time_ms": int(funding.get("time") or now_ms),
                    "raw": funding,
                }
            ]
        if "liquidation" in data:
            return [
                {
                    "event_type": "liquidation",
                    "event_source": "userEvents",
                    "symbol": None,
                    "coin": None,
                    "time_ms": now_ms,
                    "raw": data["liquidation"],
                }
            ]
        return []

    def _record_stream_event_locked(self, event: dict[str, Any]) -> None:
        if event["event_type"] == "fill" and event.get("is_snapshot"):
            return
        dedupe_key = self._stream_event_key(event)
        if dedupe_key is not None:
            if dedupe_key in self._seen_event_key_set:
                return
            self._seen_event_key_set.add(dedupe_key)
            self._seen_event_keys.append(dedupe_key)
            while len(self._seen_event_keys) > self._seen_event_keys.maxlen:
                expired = self._seen_event_keys.popleft()
                self._seen_event_key_set.discard(expired)

        tracked = self._lookup_tracked_order_locked(cloid=event.get("cloid"), exchange_order_id=event.get("exchange_order_id"))
        if tracked is None and (event.get("cloid") or event.get("exchange_order_id")):
            tracked = {
                "symbol": event.get("symbol"),
                "cloid": event.get("cloid"),
                "exchange_order_id": event.get("exchange_order_id"),
                "intent_type": None,
                "reduce_only": None,
                "submit_status": None,
                "last_order_status": None,
                "has_fill": False,
                "terminal": False,
                "last_update_ms": event.get("time_ms"),
            }
        if tracked is not None:
            if event.get("cloid") and not tracked.get("cloid"):
                tracked["cloid"] = event["cloid"]
            if event.get("exchange_order_id") and not tracked.get("exchange_order_id"):
                tracked["exchange_order_id"] = event["exchange_order_id"]
            tracked["symbol"] = tracked.get("symbol") or event.get("symbol")
            tracked["last_update_ms"] = event.get("time_ms")
            if event["event_type"] == "order_update":
                tracked["last_order_status"] = event.get("status")
                tracked["terminal"] = _is_terminal_order_status(event.get("status", ""))
            elif event["event_type"] == "fill":
                tracked["has_fill"] = True
                tracked["last_fill_price"] = event.get("fill_price")
                tracked["last_fill_size"] = event.get("fill_size")
                tracked["last_fill_time_ms"] = event.get("time_ms")
            elif event["event_type"] == "non_user_cancel":
                tracked["last_order_status"] = "non_user_cancel"
                tracked["terminal"] = True
            self._store_tracked_order_locked(tracked)
            event["tracked_intent_type"] = tracked.get("intent_type")
            event["tracked_reduce_only"] = tracked.get("reduce_only")
            event["cloid"] = event.get("cloid") or tracked.get("cloid")
            event["exchange_order_id"] = event.get("exchange_order_id") or tracked.get("exchange_order_id")
        self._stream_events.append(event)

    def _track_execution_report(self, intent: ExecutionIntent, report: ExecutionReport) -> None:
        with self._stream_lock:
            tracked = self._lookup_tracked_order_locked(cloid=report.cloid, exchange_order_id=report.exchange_order_id) or {}
            tracked.update(
                {
                    "symbol": intent.symbol,
                    "cloid": report.cloid,
                    "exchange_order_id": report.exchange_order_id,
                    "intent_type": str(intent.intent_type),
                    "reduce_only": intent.reduce_only,
                    "submit_status": str(report.status),
                    "last_update_ms": int(time.time() * 1000),
                    "terminal": report.status in {ExecutionStatus.CANCELED, ExecutionStatus.REJECTED},
                    "has_fill": report.status == ExecutionStatus.FILLED,
                }
            )
            if report.filled_price is not None:
                tracked["last_fill_price"] = str(report.filled_price)
            if report.filled_size is not None:
                tracked["last_fill_size"] = str(report.filled_size)
            self._store_tracked_order_locked(tracked)

    def _lookup_tracked_order_locked(self, *, cloid: str | None = None, exchange_order_id: str | None = None) -> dict[str, Any] | None:
        if cloid and cloid in self._tracked_orders_by_cloid:
            return self._tracked_orders_by_cloid[cloid]
        if exchange_order_id and exchange_order_id in self._tracked_orders_by_oid:
            return self._tracked_orders_by_oid[exchange_order_id]
        return None

    def _store_tracked_order_locked(self, tracked: dict[str, Any]) -> None:
        cloid = tracked.get("cloid")
        exchange_order_id = tracked.get("exchange_order_id")
        if cloid:
            self._tracked_orders_by_cloid[cloid] = tracked
        if exchange_order_id:
            self._tracked_orders_by_oid[exchange_order_id] = tracked

    def _stream_event_key(self, event: dict[str, Any]) -> str | None:
        if event["event_type"] == "fill":
            return ":".join(
                [
                    "fill",
                    str(event.get("hash") or ""),
                    str(event.get("exchange_order_id") or ""),
                    str(event.get("tid") or ""),
                    str(event.get("time_ms") or ""),
                    str(event.get("fill_size") or ""),
                    str(event.get("fill_price") or ""),
                ]
            )
        if event["event_type"] == "order_update":
            return ":".join(
                [
                    "order",
                    str(event.get("exchange_order_id") or ""),
                    str(event.get("cloid") or ""),
                    str(event.get("status") or ""),
                    str(event.get("time_ms") or ""),
                ]
            )
        if event["event_type"] == "non_user_cancel":
            return ":".join(
                [
                    "non_user_cancel",
                    str(event.get("exchange_order_id") or ""),
                    str(event.get("coin") or ""),
                    str(event.get("time_ms") or ""),
                ]
            )
        return None

    def _resolve_account_context(self) -> None:
        if self._info is None or not hasattr(self._info, "user_role"):
            return
        configured = self._configured_account_address
        signing = self._signing_address
        canonical = configured or signing
        role = None
        resolved_master = None
        agent_source = None

        addresses_to_probe: list[str] = []
        for candidate in (configured, signing):
            if candidate and candidate not in addresses_to_probe:
                addresses_to_probe.append(candidate)

        for candidate in addresses_to_probe:
            try:
                role_response = self._info.user_role(candidate)
            except Exception:
                continue
            candidate_role = role_response.get("role")
            if candidate_role == "agent":
                candidate_master = role_response.get("data", {}).get("user")
                if agent_source is None:
                    agent_source = candidate
                if candidate_master:
                    resolved_master = candidate_master
                if role is None:
                    role = candidate_role
                if configured is None and candidate_master:
                    canonical = candidate_master
            elif candidate_role and candidate == configured:
                role = candidate_role
                canonical = configured

        if resolved_master and configured is None:
            canonical = resolved_master
        elif resolved_master and configured and configured.lower() == resolved_master.lower():
            canonical = configured
            role = "agent"
        elif resolved_master and configured:
            canonical = resolved_master
            role = "agent"
        elif role is None and configured:
            role = "user"

        self._account_role = role
        self._agent_source_address = agent_source
        self._resolved_master_address = resolved_master
        self._canonical_account_address = canonical
        if self._exchange is not None and hasattr(self._exchange, "account_address"):
            self._exchange.account_address = canonical

    def _record_query_status(
        self,
        *,
        symbol: str,
        cloid: str | None,
        exchange_order_id: str | None,
        status_payload: dict[str, Any],
    ) -> None:
        status_type = status_payload.get("status")
        if status_type != "order":
            return
        order_wrapper = status_payload.get("order", {})
        if not isinstance(order_wrapper, dict):
            return
        status = order_wrapper.get("status")
        order = order_wrapper.get("order", {})
        if not isinstance(order, dict):
            return
        event = {
            "event_type": "order_query_status",
            "event_source": "orderStatus",
            "symbol": symbol,
            "coin": order.get("coin"),
            "cloid": str(order.get("cloid")) if order.get("cloid") is not None else cloid,
            "exchange_order_id": str(order.get("oid")) if order.get("oid") is not None else exchange_order_id,
            "status": _normalize_order_status(status),
            "status_raw": status,
            "time_ms": int(order_wrapper.get("statusTimestamp") or int(time.time() * 1000)),
            "limit_price": str(order.get("limitPx")) if order.get("limitPx") is not None else None,
            "size": str(order.get("sz")) if order.get("sz") is not None else None,
            "raw": status_payload,
        }
        with self._stream_lock:
            tracked = self._lookup_tracked_order_locked(cloid=event.get("cloid"), exchange_order_id=event.get("exchange_order_id")) or {}
            tracked.update(
                {
                    "symbol": symbol,
                    "cloid": event.get("cloid"),
                    "exchange_order_id": event.get("exchange_order_id"),
                    "last_order_status": event["status"],
                    "terminal": _is_terminal_order_status(event["status"]),
                    "last_update_ms": event["time_ms"],
                }
            )
            if event["status"] == "filled":
                tracked["has_fill"] = True
            self._store_tracked_order_locked(tracked)

    def _lookup_asset_rules(self, symbol: str) -> dict[str, Any] | None:
        coin = hyperliquid_symbol(symbol)
        for client in (self._info, getattr(self._exchange, "info", None)):
            if client is None:
                continue
            coin_to_asset = getattr(client, "coin_to_asset", None)
            asset_to_sz_decimals = getattr(client, "asset_to_sz_decimals", None)
            if coin_to_asset is None or asset_to_sz_decimals is None:
                continue
            asset = coin_to_asset.get(coin)
            if asset is None:
                continue
            sz_decimals = asset_to_sz_decimals.get(asset)
            if sz_decimals is None:
                continue
            return {
                "coin": coin,
                "asset": int(asset),
                "sz_decimals": int(sz_decimals),
                "is_spot": int(asset) >= 10_000,
            }
        return None

    def _size_step(self, sz_decimals: int) -> Decimal:
        return Decimal("1").scaleb(-sz_decimals) if sz_decimals > 0 else Decimal("1")

    def _max_price_decimals(self, *, is_spot: bool, sz_decimals: int) -> int:
        return max((8 if is_spot else 6) - sz_decimals, 0)

    def _significant_figures(self, value: Decimal) -> int:
        normalized = value.copy_abs().normalize()
        digits = "".join(str(digit) for digit in normalized.as_tuple().digits).lstrip("0")
        return len(digits) if digits else 1

    def _is_valid_hyperliquid_price(self, value: Decimal, *, is_spot: bool, sz_decimals: int) -> bool:
        if value <= Decimal("0"):
            return False
        if value == value.to_integral_value():
            return True
        max_decimals = self._max_price_decimals(is_spot=is_spot, sz_decimals=sz_decimals)
        exponent = value.normalize().as_tuple().exponent
        decimal_places = max(-exponent, 0)
        return decimal_places <= max_decimals and self._significant_figures(value) <= 5

    def _normalize_price(
        self,
        symbol: str,
        price: Decimal | None,
        *,
        rounding: str,
    ) -> Decimal | None:
        if price is None:
            return None
        rules = self._lookup_asset_rules(symbol)
        if rules is None:
            return price
        max_decimals = self._max_price_decimals(is_spot=rules["is_spot"], sz_decimals=rules["sz_decimals"])
        for decimals in range(max_decimals, -1, -1):
            step = Decimal("1").scaleb(-decimals) if decimals > 0 else Decimal("1")
            candidate = quantize_to_step(price, step, rounding)
            if self._is_valid_hyperliquid_price(candidate, is_spot=rules["is_spot"], sz_decimals=rules["sz_decimals"]):
                return candidate
        integer_candidate = quantize_to_step(price, Decimal("1"), rounding)
        if self._is_valid_hyperliquid_price(integer_candidate, is_spot=rules["is_spot"], sz_decimals=rules["sz_decimals"]):
            return integer_candidate
        raise ValueError(f"could not normalize Hyperliquid price for {symbol}: {price}")

    def _normalize_size(self, symbol: str, size: Decimal) -> Decimal:
        rules = self._lookup_asset_rules(symbol)
        if rules is None:
            return size
        normalized = quantize_to_step(size, self._size_step(rules["sz_decimals"]), ROUND_FLOOR)
        if normalized <= Decimal("0"):
            raise ValueError(f"size rounds to zero for {symbol}: {size}")
        return normalized

    def _protective_rounding(self, direction: SignalDirection | None, intent_type: ExecutionIntentType) -> str:
        if direction == SignalDirection.LONG:
            return ROUND_FLOOR if intent_type == ExecutionIntentType.PROTECTIVE_TP else ROUND_CEILING
        return ROUND_CEILING if intent_type == ExecutionIntentType.PROTECTIVE_TP else ROUND_FLOOR

    def _normalize_protective_price(self, packet: DecisionPacket, intent_type: ExecutionIntentType) -> Decimal | None:
        raw_price = packet.tp_price if intent_type == ExecutionIntentType.PROTECTIVE_TP else packet.sl_price
        return self._normalize_price(packet.signal.symbol, raw_price, rounding=self._protective_rounding(packet.signal.direction, intent_type))

    async def execute(self, intents: list[ExecutionIntent]) -> list[ExecutionReport]:
        if not self._enabled or self._exchange is None:
            return [
                ExecutionReport(
                    intent_id=intent.intent_id,
                    intent_type=intent.intent_type,
                    status=ExecutionStatus.REJECTED,
                    symbol=intent.symbol,
                    cloid=intent.cloid,
                    message="live execution is not configured",
                )
                for intent in intents
            ]
        reports: list[ExecutionReport] = []
        for intent in intents:
            try:
                reports.append(await asyncio.wait_for(self._execute_intent(intent), timeout=self.config.order_timeout_seconds))
            except TimeoutError:
                reports.append(
                    ExecutionReport(
                        intent_id=intent.intent_id,
                        intent_type=intent.intent_type,
                        status=ExecutionStatus.REJECTED,
                        symbol=intent.symbol,
                        cloid=intent.cloid,
                        message="execution timeout",
                    )
                )
        return reports

    async def _execute_intent(self, intent: ExecutionIntent) -> ExecutionReport:
        assert self._exchange is not None
        coin = hyperliquid_symbol(intent.symbol)
        try:
            if intent.intent_type == ExecutionIntentType.ENTER:
                normalized_size = self._normalize_size(intent.symbol, intent.size)
                result = await asyncio.to_thread(
                    self._exchange.market_open,
                    coin,
                    intent.direction == SignalDirection.LONG,
                    float(normalized_size),
                    float(intent.reference_price) if intent.reference_price is not None else None,
                    self.config.market_order_slippage,
                    Cloid.from_str(intent.cloid) if intent.cloid else None,
                )
            elif intent.intent_type == ExecutionIntentType.CLOSE:
                normalized_size = self._normalize_size(intent.symbol, intent.size)
                result = await asyncio.to_thread(
                    self._exchange.market_close,
                    coin,
                    float(normalized_size),
                    float(intent.reference_price) if intent.reference_price is not None else None,
                    self.config.market_order_slippage,
                    Cloid.from_str(intent.cloid) if intent.cloid else None,
                )
            elif intent.intent_type == ExecutionIntentType.CANCEL:
                report = await self._cancel_with_verification(intent, coin)
                self._track_execution_report(intent, report)
                return report
            elif intent.intent_type in {ExecutionIntentType.PROTECTIVE_TP, ExecutionIntentType.PROTECTIVE_SL}:
                tpsl = "tp" if intent.intent_type == ExecutionIntentType.PROTECTIVE_TP else "sl"
                is_buy = intent.direction != SignalDirection.LONG
                normalized_size = self._normalize_size(intent.symbol, intent.size)
                normalized_trigger_price = self._normalize_price(
                    intent.symbol,
                    intent.trigger_price,
                    rounding=self._protective_rounding(intent.direction, intent.intent_type),
                )
                if normalized_trigger_price is None:
                    raise ValueError("protective order missing trigger price")
                trigger_price = float(normalized_trigger_price)
                market_limit_price = self._exchange._slippage_price(coin, is_buy, 0.10, trigger_price)
                result = await asyncio.to_thread(
                    self._exchange.order,
                    coin,
                    is_buy,
                    float(normalized_size),
                    market_limit_price,
                    {"trigger": {"triggerPx": trigger_price, "isMarket": True, "tpsl": tpsl}},
                    True,
                    Cloid.from_str(intent.cloid) if intent.cloid else None,
                )
            else:  # pragma: no cover
                raise ValueError(f"unsupported intent {intent.intent_type}")
        except Exception as exc:  # pragma: no cover - defensive live path
            return ExecutionReport(
                intent_id=intent.intent_id,
                intent_type=intent.intent_type,
                status=ExecutionStatus.REJECTED,
                symbol=intent.symbol,
                cloid=intent.cloid,
                message=str(exc),
            )
        report = self._report_from_exchange_result(intent, result)
        self._track_execution_report(intent, report)
        return report

    async def reconcile(self, symbol: str) -> dict[str, Any]:
        if not self._enabled or self._info is None:
            return {"symbol": symbol, "position_size": "0", "side": None, "open_order_cloids": []}
        coin = hyperliquid_symbol(symbol)
        address = self.account_address()
        if address is None:
            return {"symbol": symbol, "position_size": "0", "side": None, "open_order_cloids": []}
        state = await asyncio.to_thread(self._info.user_state, address)
        open_orders = await asyncio.to_thread(self._info.open_orders, address)
        size = Decimal("0")
        side: str | None = None
        for position in state.get("assetPositions", []):
            item = position["position"]
            if item["coin"] == coin:
                signed_size = Decimal(str(item["szi"]))
                size = abs(signed_size)
                if signed_size > 0:
                    side = SignalDirection.LONG
                elif signed_size < 0:
                    side = SignalDirection.SHORT
                break
        cloids = [str(order.get("cloid")) for order in open_orders if order.get("coin") == coin and order.get("cloid")]
        with self._stream_lock:
            self._last_reconcile_ms = int(time.time() * 1000)
        return {"symbol": symbol, "position_size": str(size), "side": side, "open_order_cloids": cloids}


def make_execution_adapter(
    mode: RuntimeMode,
    *,
    entry_slippage_bps: Decimal,
    exit_slippage_bps: Decimal,
    price_tick: Decimal,
    size_step: Decimal,
    hyperliquid_config: HyperliquidConfig,
) -> ExecutionAdapter:
    if mode == RuntimeMode.SHADOW:
        return ShadowExecutionAdapter()
    if mode == RuntimeMode.PAPER:
        return PaperExecutionAdapter(
            entry_slippage_bps=entry_slippage_bps,
            exit_slippage_bps=exit_slippage_bps,
            price_tick=price_tick,
            size_step=size_step,
        )
    return HyperliquidExecutionAdapter(hyperliquid_config)
