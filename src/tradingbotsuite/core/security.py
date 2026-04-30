from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from tradingbotsuite.core.models import SignalDirection, SignalIntent


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def compute_hmac(secret: str, body: bytes, timestamp_ms: int) -> str:
    signer = hmac.new(secret.encode("utf-8"), digestmod=hashlib.sha256)
    signer.update(str(timestamp_ms).encode("utf-8"))
    signer.update(b".")
    signer.update(body)
    return signer.hexdigest()


def verify_hmac(
    *,
    secret: str,
    body: bytes,
    timestamp_ms: int,
    signature: str,
    tolerance_seconds: int,
    now_ms: int,
) -> bool:
    age_ms = abs(now_ms - timestamp_ms)
    if age_ms > tolerance_seconds * 1000:
        return False
    expected = compute_hmac(secret, body, timestamp_ms)
    return hmac.compare_digest(expected, signature)


def _coerce_timestamp_ms(value: Any) -> int:
    if value is None:
        raise ValueError("missing timestamp")
    raw = int(value)
    return raw * 1000 if raw < 10_000_000_000 else raw


def _coerce_direction(payload: dict[str, Any]) -> SignalDirection:
    candidate = str(
        payload.get("direction")
        or payload.get("side")
        or payload.get("action")
        or payload.get("signal")
        or ""
    ).strip().lower()
    if candidate in {"buy", "long"}:
        return SignalDirection.LONG
    if candidate in {"sell", "short"}:
        return SignalDirection.SHORT
    raise ValueError("direction is missing or unsupported")


def adapt_signal_payload(payload: dict[str, Any], received_time_ms: int) -> SignalIntent:
    symbol = payload.get("symbol") or payload.get("ticker")
    if not symbol:
        raise ValueError("symbol is required")
    signal_id = str(payload.get("signal_id") or payload.get("id") or payload.get("alert_id") or "").strip()
    if not signal_id:
        raise ValueError("signal_id is required")
    bar_time_ms = _coerce_timestamp_ms(
        payload.get("signal_bar_time_ms")
        or payload.get("bar_time_ms")
        or payload.get("bar_timestamp")
        or payload.get("time")
    )
    return SignalIntent(
        signal_id=signal_id,
        source=str(payload.get("source") or "external_signal"),
        symbol=str(symbol),
        direction=_coerce_direction(payload),
        signal_bar_time_ms=bar_time_ms,
        received_time_ms=received_time_ms,
        raw_payload=payload,
    )
