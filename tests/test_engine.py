from __future__ import annotations

import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import time

import pytest

from tradingbotsuite.adapters.execution import (
    HyperliquidExecutionAdapter,
    PaperExecutionAdapter,
    ShadowExecutionAdapter,
    _normalize_spot_meta,
    build_open_intents,
    build_protective_intents,
    build_entry_intents,
)
from tradingbotsuite.config import AppConfig, HyperliquidConfig
from tradingbotsuite.core.engine import TradingEngine
from tradingbotsuite.core.math import BAR_INTERVAL_MS, build_barriers
from tradingbotsuite.core.models import (
    ActionTicket,
    Bar,
    DecisionAction,
    DecisionPacket,
    ExecutionIntent,
    ExecutionIntentType,
    ExecutionReport,
    ExecutionStatus,
    PositionState,
    RuntimeMode,
    SafeModeReason,
    SignalDirection,
    ExitReason,
    SignalIntent,
    TradeStatus,
)
from tradingbotsuite.core.security import canonical_json_bytes, compute_hmac
from tradingbotsuite.manual_cli import _build_manual_signal
from tradingbotsuite.operator_commands import execute_manual_signal
from tradingbotsuite.persistence.sqlite_store import SQLiteStore


def make_payload(signal_id: str, direction: str, bar_time_ms: int) -> dict[str, object]:
    return {
        "signal_id": signal_id,
        "symbol": "BTCUSDT",
        "direction": direction,
        "signal_bar_time_ms": bar_time_ms,
    }


def sign_payload(secret: str, payload: dict[str, object], timestamp_ms: int) -> str:
    return compute_hmac(secret, canonical_json_bytes(payload), timestamp_ms)


def test_normalize_spot_meta_handles_sparse_indices() -> None:
    normalized = _normalize_spot_meta(
        {
            "universe": [{"tokens": [2, 0], "name": "@1", "index": 1}],
            "tokens": [
                {"index": 0, "name": "USDC"},
                {"index": 2, "name": "ALT"},
            ],
        }
    )
    assert len(normalized["tokens"]) == 3
    assert normalized["tokens"][0]["name"] == "USDC"
    assert normalized["tokens"][2]["name"] == "ALT"


def test_webhook_accepts_and_is_idempotent(test_client, app_config: AppConfig) -> None:
    payload = make_payload("s1", "long", 1712662200000)
    timestamp_ms = int(time.time() * 1000)
    signature = sign_payload(app_config.webhook.secret, payload, timestamp_ms)
    headers = {"X-Signature": signature, "X-Timestamp-Ms": str(timestamp_ms)}
    first = test_client.post("/webhooks/signal", json=payload, headers=headers)
    second = test_client.post("/webhooks/signal", json=payload, headers=headers)
    assert first.status_code == 200
    assert first.json()["accepted"] is True
    assert second.status_code == 200
    assert second.json()["accepted"] is False
    assert second.json()["action"] == "ignore"


def test_health_details_exposes_canonical_system_snapshot(test_client) -> None:
    response = test_client.get("/health/details")

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "BTCUSDT"
    assert payload["mode"] == "paper"
    assert "market_data_health" in payload
    assert "execution_health" in payload
    assert "position" in payload
    assert "safety" in payload
    assert "safety_state" in payload
    assert "attribution" in payload


@pytest.mark.asyncio
async def test_flip_closes_then_reopens(app_config, sample_bars, tmp_path) -> None:
    store = SQLiteStore(tmp_path / "flip.sqlite3")
    await store.initialize()

    class FakeCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

    adapter = PaperExecutionAdapter(
        entry_slippage_bps=Decimal("5"),
        exit_slippage_bps=Decimal("5"),
        price_tick=Decimal("0.1"),
        size_step=Decimal("0.001"),
    )
    clock_values = iter([1712665800000, 1712665800001, 1712665800002, 1712665800003])
    engine = TradingEngine(app_config, store, FakeCandles(), adapter, clock=lambda: next(clock_values))
    await engine.initialize()
    first_signal = SignalIntent(
        signal_id="long-1",
        symbol="BTCUSDT",
        direction=SignalDirection.LONG,
        signal_bar_time_ms=1712662200000,
        received_time_ms=1712665800000,
        raw_payload={},
    )
    second_signal = SignalIntent(
        signal_id="short-1",
        symbol="BTCUSDT",
        direction=SignalDirection.SHORT,
        signal_bar_time_ms=1712663100000,
        received_time_ms=1712665800001,
        raw_payload={},
    )
    first_packet, _, _ = await engine.handle_signal(first_signal)
    second_packet, reports, _ = await engine.handle_signal(second_signal)
    state = await store.get_position_state("BTCUSDT")
    assert first_packet.action == DecisionAction.ACCEPT
    assert second_packet.action == DecisionAction.FLIP
    assert any(report.intent_type == ExecutionIntentType.CLOSE for report in reports)
    assert state is not None
    assert state.direction == SignalDirection.SHORT
    assert state.status == TradeStatus.OPEN


@pytest.mark.asyncio
async def test_restart_recovery_reads_persisted_state(app_config, sample_bars, tmp_path) -> None:
    store = SQLiteStore(tmp_path / "recovery.sqlite3")
    await store.initialize()
    position = PositionState(
        symbol="BTCUSDT",
        status=TradeStatus.OPEN,
        direction=SignalDirection.LONG,
        position_size=Decimal("0.01"),
        entry_price=Decimal("70000"),
        entry_time_ms=1712665800000,
        entry_bar_time_ms=1712662200000,
        entry_atr=Decimal("250"),
        tp_price=Decimal("70375"),
        sl_price=Decimal("69750"),
        vertical_barrier_time_ms=1712683800000,
        entry_order_cloid="entry-1",
        tp_order_cloid="tp-1",
        sl_order_cloid="sl-1",
        last_updated_ms=1712665800000,
    )
    await store.upsert_position_state(position)

    class FakeCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

    engine = TradingEngine(
        app_config,
        store,
        FakeCandles(),
        PaperExecutionAdapter(
            entry_slippage_bps=Decimal("5"),
            exit_slippage_bps=Decimal("5"),
            price_tick=Decimal("0.1"),
            size_step=Decimal("0.001"),
        ),
        clock=lambda: 1712665800000,
    )
    await engine.initialize()
    restored = await engine.store.get_position_state("BTCUSDT")
    assert restored is not None
    assert restored.direction == SignalDirection.LONG
    assert restored.entry_order_cloid == "entry-1"


@pytest.mark.asyncio
async def test_stale_data_enters_safe_mode(app_config, tmp_path) -> None:
    store = SQLiteStore(tmp_path / "safe.sqlite3")
    await store.initialize()
    stale_bars = [
        Bar(
            time_ms=1712600000000,
            open=Decimal("70000"),
            high=Decimal("70100"),
            low=Decimal("69900"),
            close=Decimal("70050"),
            volume=Decimal("100"),
        )
        for _ in range(20)
    ]

    class StaleCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return stale_bars[-limit:]

    stale_config = AppConfig(
        runtime_mode=app_config.runtime_mode,
        db_path=app_config.db_path,
        webhook=app_config.webhook,
        strategy=replace(app_config.strategy, stale_bar_after_ms=1),
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
    )
    engine = TradingEngine(
        stale_config,
        store,
        StaleCandles(),
        PaperExecutionAdapter(
            entry_slippage_bps=Decimal("5"),
            exit_slippage_bps=Decimal("5"),
            price_tick=Decimal("0.1"),
            size_step=Decimal("0.001"),
        ),
        clock=lambda: 1712665800000,
    )
    await engine.initialize()
    packet, _, _ = await engine.handle_signal(
        SignalIntent(
            signal_id="stale-1",
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            signal_bar_time_ms=1712662200000,
            received_time_ms=1712665800000,
            raw_payload={},
        )
    )
    safety = await store.get_safety_status()
    assert packet.accepted is False
    assert safety is not None
    assert safety.reason == SafeModeReason.STALE_MARKET_DATA


@pytest.mark.asyncio
async def test_execution_path_parity() -> None:
    packet = DecisionPacket(
        signal=SignalIntent(
            signal_id="p1",
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            signal_bar_time_ms=1712662200000,
            received_time_ms=1712665800000,
            raw_payload={},
        ),
        mode=RuntimeMode.PAPER,
        action=DecisionAction.ACCEPT,
        accepted=True,
        intended_size=Decimal("0.01"),
        entry_reference_price=Decimal("70000"),
        atr=Decimal("250"),
        tp_price=Decimal("70375"),
        sl_price=Decimal("69750"),
        vertical_barrier_time_ms=1712683800000,
    )
    shadow_intents = build_entry_intents(packet.model_copy(update={"mode": RuntimeMode.SHADOW}), None)
    paper_intents = build_entry_intents(packet, None)
    live_intents = build_entry_intents(packet.model_copy(update={"mode": RuntimeMode.LIVE}), None)
    assert [intent.intent_type for intent in shadow_intents] == [intent.intent_type for intent in paper_intents] == [intent.intent_type for intent in live_intents]


@pytest.mark.asyncio
async def test_shadow_mode_does_not_persist_open_position(app_config, sample_bars, tmp_path) -> None:
    shadow_config = AppConfig(
        runtime_mode=RuntimeMode.SHADOW,
        db_path=tmp_path / "shadow.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
    )
    store = SQLiteStore(shadow_config.db_path)
    await store.initialize()

    class FakeCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

        async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True):
            return sample_bars[-1]

        async def close(self):
            return None

    engine = TradingEngine(
        shadow_config,
        store,
        FakeCandles(),
        ShadowExecutionAdapter(),
        clock=lambda: 1712665800000,
    )
    await engine.initialize()
    packet, reports, _ = await engine.handle_signal(
        SignalIntent(
            signal_id="shadow-1",
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            signal_bar_time_ms=1712662200000,
            received_time_ms=1712665800000,
            raw_payload={},
        )
    )
    state = await store.get_position_state("BTCUSDT")
    assert packet.accepted is True
    assert reports
    assert state is None


@pytest.mark.asyncio
async def test_supervision_adverse_selection_exit_is_disabled_by_default(app_config, sample_bars, tmp_path) -> None:
    store = SQLiteStore(tmp_path / "adverse_default.sqlite3")
    await store.initialize()
    await store.upsert_position_state(
        PositionState(
            symbol="BTCUSDT",
            status=TradeStatus.OPEN,
            direction=SignalDirection.LONG,
            position_size=Decimal("0.001"),
            entry_price=Decimal("70000"),
            entry_time_ms=sample_bars[-3].time_ms + BAR_INTERVAL_MS,
            entry_bar_time_ms=sample_bars[-3].time_ms,
            entry_atr=Decimal("250"),
            tp_price=Decimal("80000"),
            sl_price=Decimal("65000"),
            vertical_barrier_time_ms=sample_bars[-1].time_ms + (10 * BAR_INTERVAL_MS),
            last_updated_ms=sample_bars[-1].time_ms,
        )
    )

    class AdverseCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

        async def get_microstructure_snapshot(self, symbol: str, *, windows_seconds, now_ms):
            return {
                "healthy": True,
                "mid_price": "69920",
                "top_of_book_imbalance": "-0.40",
                "windows": {"20": {"signed_ratio": "-0.50"}},
            }

    engine = TradingEngine(
        app_config,
        store,
        AdverseCandles(),
        PaperExecutionAdapter(
            entry_slippage_bps=Decimal("5"),
            exit_slippage_bps=Decimal("5"),
            price_tick=Decimal("0.1"),
            size_step=Decimal("0.001"),
        ),
        clock=lambda: sample_bars[-1].time_ms + BAR_INTERVAL_MS,
    )
    await engine.initialize()
    reports = await engine.supervise_position("BTCUSDT")
    state = await store.get_position_state("BTCUSDT")
    assert reports == []
    assert state is not None
    assert state.status == TradeStatus.OPEN


@pytest.mark.asyncio
async def test_supervision_alpha_decay_exit_triggers_when_enabled(app_config, sample_bars, tmp_path) -> None:
    plan_payload = json.loads(Path("configs/v2_btc_research.json").read_text(encoding="utf-8"))
    plan_payload["exit_supervision"]["alpha_decay_enabled"] = True
    plan_payload["exit_supervision"]["alpha_decay_viability_threshold"] = 0.60
    plan_path = tmp_path / "research.json"
    plan_path.write_text(json.dumps(plan_payload, indent=2), encoding="utf-8")

    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "alpha_decay.sqlite3",
        webhook=app_config.webhook,
        strategy=replace(app_config.strategy, hurst_window_bars=32),
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=app_config.research.__class__(
            output_dir=app_config.research.output_dir,
            config_path=plan_path,
            artifact_manifest_path=app_config.research.artifact_manifest_path,
        ),
    )
    store = SQLiteStore(config.db_path)
    await store.initialize()
    await store.upsert_position_state(
        PositionState(
            symbol="BTCUSDT",
            status=TradeStatus.OPEN,
            direction=SignalDirection.LONG,
            position_size=Decimal("0.001"),
            entry_price=sample_bars[-3].close,
            entry_time_ms=sample_bars[-3].time_ms + BAR_INTERVAL_MS,
            entry_bar_time_ms=sample_bars[-3].time_ms,
            entry_atr=Decimal("250"),
            tp_price=Decimal("71000"),
            sl_price=Decimal("69750"),
            vertical_barrier_time_ms=sample_bars[-1].time_ms + (10 * BAR_INTERVAL_MS),
            last_updated_ms=sample_bars[-1].time_ms,
        )
    )

    class AlphaCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            extended = sample_bars * 3
            return extended[-limit:]

        async def get_microstructure_snapshot(self, symbol: str, *, windows_seconds, now_ms):
            return {
                "healthy": True,
                "mid_price": "70020",
                "top_of_book_imbalance": "0.10",
                "queue_imbalance_l1": "0.02",
                "queue_imbalance_l5": "0.01",
                "queue_imbalance_l10": "0.01",
                "windows": {"20": {"signed_ratio": "0.05"}},
            }

        async def fetch_funding_context(self, symbol: str, *, as_of_ms: int, history_limit: int = 8):
            return {"funding_rate": "0.0001", "funding_rate_change": "0.00002", "time_to_next_funding_ms": 1_800_000}

        async def fetch_open_interest_context(self, symbol: str, *, as_of_ms: int, period: str = "5m", lookback_points: int = 13):
            return {"open_interest": "1000", "open_interest_change": "50", "open_interest_change_pct": "0.05", "open_interest_value": "70500000"}

        async def fetch_premium_context(self, symbol: str, *, as_of_ms: int, interval: str = "5m"):
            return {"basis_rate": "0.0003", "basis": "21", "premium_close": "0.0002"}

    class LowScoreScorer:
        def __init__(self):
            self.plan = type("Plan", (), {"model": type("Model", (), {"probability_threshold": 0.55})()})()
            self.manifest = {
                "model_version": "test-model",
                "calibration_version": "test-cal",
                "artifact_manifest_version": "v2-artifact-manifest-1",
            }
            self.manifest_sha256 = "fixture"

        def score_snapshot(self, snapshot: dict):
            return {
                "accept_probability": 0.40,
                "base_probability": 0.41,
                "confidence_bucket": "low",
                "size_multiplier_candidate": 0.0,
                "model_version": "test-model",
                "calibration_version": "test-cal",
                "probability_threshold": 0.55,
                "artifact_manifest_version": "v2-artifact-manifest-1",
                "artifact_manifest_sha256": "fixture",
                "scoring_fallback_reason": None,
                "observe_only": True,
            }

    engine = TradingEngine(
        config,
        store,
        AlphaCandles(),
        PaperExecutionAdapter(
            entry_slippage_bps=Decimal("5"),
            exit_slippage_bps=Decimal("5"),
            price_tick=Decimal("0.1"),
            size_step=Decimal("0.001"),
        ),
        scorer=LowScoreScorer(),
        clock=lambda: sample_bars[-1].time_ms + BAR_INTERVAL_MS,
    )
    await engine.initialize()
    reports = await engine.supervise_position("BTCUSDT")
    state = await store.get_position_state("BTCUSDT")
    assert reports
    assert state is not None
    assert state.status == TradeStatus.FLAT
    assert state.last_exit_reason == ExitReason.ALPHA_DECAY


@pytest.mark.asyncio
async def test_trace_sink_receives_pipeline_events(app_config, sample_bars, tmp_path) -> None:
    store = SQLiteStore(tmp_path / "trace.sqlite3")
    await store.initialize()
    trace_events: list[str] = []

    class FakeCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

    engine = TradingEngine(
        app_config,
        store,
        FakeCandles(),
        PaperExecutionAdapter(
            entry_slippage_bps=Decimal("5"),
            exit_slippage_bps=Decimal("5"),
            price_tick=Decimal("0.1"),
            size_step=Decimal("0.001"),
        ),
        clock=lambda: 1712665800000,
        trace_sink=lambda stage, details: trace_events.append(stage),
    )
    await engine.initialize()
    await engine.handle_signal(
        SignalIntent(
            signal_id="trace-1",
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            signal_bar_time_ms=1712662200000,
            received_time_ms=1712665800000,
            raw_payload={},
        )
    )
    assert "signal:received" in trace_events
    assert "decision:packet" in trace_events
    assert "execution:open_intents" in trace_events
    assert "execution:open_reports" in trace_events
    assert "execution:protective_intents" in trace_events
    assert "execution:protective_reports" in trace_events
    assert "signal:complete" in trace_events


@pytest.mark.asyncio
async def test_collect_system_snapshot_returns_canonical_status_shape(app_config, sample_bars, tmp_path) -> None:
    store = SQLiteStore(tmp_path / "snapshot.sqlite3")
    await store.initialize()

    class FakeCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

        async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True):
            return sample_bars[-1]

        async def get_microstructure_snapshot(self, symbol: str, *, windows_seconds, now_ms: int):
            return {
                "symbol": symbol,
                "healthy": True,
                "trade_flow_available": True,
                "top_of_book_available": True,
                "depth_healthy": True,
                "last_trade_time_ms": now_ms,
                "last_book_ticker_time_ms": now_ms,
                "last_depth_time_ms": now_ms,
                "order_book_health_state": "healthy",
                "depth_sync_state": "synced",
                "repair_in_flight": False,
                "buffered_event_count": 0,
                "windows": {
                    str(app_config.strategy.microstructure_primary_window_seconds): {
                        "signed_ratio": "0.1",
                    }
                },
                "top_of_book_imbalance": "0.2",
            }

        def get_stream_status(self):
            return {"enabled": True, "symbol_status": {"BTCUSDT": {"started_ms": sample_bars[-1].time_ms}}}

        async def close(self):
            return None

    engine = TradingEngine(
        app_config,
        store,
        FakeCandles(),
        PaperExecutionAdapter(
            entry_slippage_bps=Decimal("5"),
            exit_slippage_bps=Decimal("5"),
            price_tick=Decimal("0.1"),
            size_step=Decimal("0.001"),
        ),
        clock=lambda: sample_bars[-1].time_ms + 60_000,
    )
    await engine.initialize()
    snapshot = await engine.collect_system_snapshot("BTCUSDT")

    assert snapshot["symbol"] == "BTCUSDT"
    assert snapshot["mode"] == RuntimeMode.PAPER
    assert snapshot["position"]["status"] == "flat"
    assert snapshot["market_data_health"]["healthy"] is True
    assert snapshot["execution_health"]["healthy"] is True
    assert snapshot["microstructure"]["healthy"] is True
    assert snapshot["market_data_health"]["feed_health"]["trades"]["healthy"] is True
    assert snapshot["market_data_health"]["feed_health"]["depth"]["healthy"] is True
    assert snapshot["market_data_health"]["feed_health"]["depth"]["depth_sync_state"] == "synced"
    assert snapshot["fresh_stream_events"] == []
    assert snapshot["safety_state"]["state"] == "healthy"
    assert "attribution" in snapshot


@pytest.mark.asyncio
async def test_signal_is_rejected_when_spread_abnormality_hits_limit(app_config, sample_bars, tmp_path) -> None:
    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "spread_block.sqlite3",
        webhook=app_config.webhook,
        strategy=replace(app_config.strategy, max_spread_bps=Decimal("5")),
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=app_config.research,
        operator_ui=app_config.operator_ui,
    )
    store = SQLiteStore(config.db_path)
    await store.initialize()

    class FakeCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

        async def get_microstructure_snapshot(self, symbol: str, *, windows_seconds, now_ms):
            return {
                "healthy": True,
                "spread_bps": "12",
                "top_of_book_imbalance": "0.2",
                "windows": {"20": {"signed_ratio": "0.1"}},
            }

    adapter = PaperExecutionAdapter(
        entry_slippage_bps=Decimal("5"),
        exit_slippage_bps=Decimal("5"),
        price_tick=Decimal("0.1"),
        size_step=Decimal("0.001"),
    )
    engine = TradingEngine(config, store, FakeCandles(), adapter, clock=lambda: 1712665800000)
    await engine.initialize()
    packet, reports, _ = await engine.handle_signal(
        SignalIntent(
            signal_id="spread-block-1",
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            signal_bar_time_ms=1712662200000,
            received_time_ms=1712665800000,
            raw_payload={},
        )
    )
    assert packet.accepted is False
    assert packet.rejection_reason == "spread_abnormality"
    assert reports == []


@pytest.mark.asyncio
async def test_signal_is_rejected_when_daily_loss_limit_hit(app_config, sample_bars, tmp_path) -> None:
    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "daily_loss_block.sqlite3",
        webhook=app_config.webhook,
        strategy=replace(app_config.strategy, max_daily_loss_quote=Decimal("10")),
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=app_config.research,
        operator_ui=app_config.operator_ui,
    )
    store = SQLiteStore(config.db_path)
    await store.initialize()
    await store.append_execution_metric(
        metric_id="close-1",
        signal_id=None,
        symbol="BTCUSDT",
        metric_type="trade_close",
        recorded_time_ms=1712665700000,
        payload={"realized_pnl_quote": "-15"},
    )

    class FakeCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

        async def get_microstructure_snapshot(self, symbol: str, *, windows_seconds, now_ms):
            return {
                "healthy": True,
                "spread_bps": "2",
                "top_of_book_imbalance": "0.2",
                "windows": {"20": {"signed_ratio": "0.1"}},
            }

    adapter = PaperExecutionAdapter(
        entry_slippage_bps=Decimal("5"),
        exit_slippage_bps=Decimal("5"),
        price_tick=Decimal("0.1"),
        size_step=Decimal("0.001"),
    )
    engine = TradingEngine(config, store, FakeCandles(), adapter, clock=lambda: 1712665800000)
    await engine.initialize()
    packet, reports, _ = await engine.handle_signal(
        SignalIntent(
            signal_id="daily-loss-1",
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            signal_bar_time_ms=1712662200000,
            received_time_ms=1712665800000,
            raw_payload={},
        )
    )
    assert packet.accepted is False
    assert packet.rejection_reason == "daily_loss_limit"
    assert reports == []


@pytest.mark.asyncio
async def test_supervision_persists_runtime_snapshot(app_config, sample_bars, tmp_path) -> None:
    store = SQLiteStore(tmp_path / "supervision.sqlite3")
    await store.initialize()
    await store.upsert_position_state(
        PositionState(
            symbol="BTCUSDT",
            status=TradeStatus.OPEN,
            direction=SignalDirection.LONG,
            position_size=Decimal("0.01"),
            entry_price=sample_bars[-3].close,
            entry_time_ms=sample_bars[-3].time_ms + 60_000,
            entry_bar_time_ms=sample_bars[-3].time_ms,
            entry_atr=Decimal("250"),
            tp_price=sample_bars[-3].close + Decimal("400"),
            sl_price=sample_bars[-3].close - Decimal("300"),
            vertical_barrier_time_ms=sample_bars[-3].time_ms + (24 * BAR_INTERVAL_MS),
            last_updated_ms=sample_bars[-3].time_ms + 60_000,
        )
    )

    class FakeCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

        async def get_microstructure_snapshot(self, symbol: str, *, windows_seconds, now_ms):
            return {
                "healthy": True,
                "top_of_book_imbalance": "0.15",
                "queue_imbalance_l1": "0.10",
                "queue_imbalance_l5": "0.08",
                "queue_imbalance_l10": "0.05",
                "windows": {"20": {"signed_ratio": "0.04"}},
            }

    adapter = PaperExecutionAdapter(
        entry_slippage_bps=Decimal("5"),
        exit_slippage_bps=Decimal("5"),
        price_tick=Decimal("0.1"),
        size_step=Decimal("0.001"),
    )
    engine = TradingEngine(app_config, store, FakeCandles(), adapter, clock=lambda: sample_bars[-1].time_ms + 60_000)
    await engine.initialize()
    reports = await engine.supervise_position("BTCUSDT")
    latest = await store.get_latest_supervision_snapshot("BTCUSDT")
    assert reports == []
    assert latest is not None
    assert latest["symbol"] == "BTCUSDT"
    assert latest["candidate_exit_reason"] is None
    assert latest["mfe_atr"] is not None


@pytest.mark.asyncio
async def test_barriers_anchor_to_filled_entry_price(app_config, sample_bars, tmp_path) -> None:
    store = SQLiteStore(tmp_path / "filled_anchor.sqlite3")
    await store.initialize()

    class FakeCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

    adapter = PaperExecutionAdapter(
        entry_slippage_bps=Decimal("50"),
        exit_slippage_bps=Decimal("5"),
        price_tick=Decimal("0.1"),
        size_step=Decimal("0.001"),
    )
    engine = TradingEngine(app_config, store, FakeCandles(), adapter, clock=lambda: 1712665800000)
    await engine.initialize()
    packet, reports, _ = await engine.handle_signal(
        SignalIntent(
            signal_id="fill-anchor-1",
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            signal_bar_time_ms=1712662200000,
            received_time_ms=1712665800000,
            raw_payload={},
        )
    )
    state = await store.get_position_state("BTCUSDT")
    entry_report = next(report for report in reports if report.intent_type == ExecutionIntentType.ENTER)
    assert state is not None
    assert packet.entry_reference_price == entry_report.filled_price
    assert state.entry_price == entry_report.filled_price
    expected_tp, expected_sl = build_barriers(
        entry_price=entry_report.filled_price,
        atr=packet.atr,
        direction=packet.signal.direction,
        tp_multiple=app_config.strategy.take_profit_atr_multiple,
        sl_multiple=app_config.strategy.stop_loss_atr_multiple,
        price_tick=app_config.strategy.price_tick,
    )
    assert packet.tp_price == expected_tp
    assert packet.sl_price == expected_sl


@pytest.mark.asyncio
async def test_manual_signal_builder_uses_latest_closed_bar(sample_bars) -> None:
    class FakeEngine:
        def __init__(self):
            self.clock = lambda: 1712665800000

            class FakeCandles:
                async def fetch_recent_closed_bars(self, symbol: str, limit: int):
                    return sample_bars[-limit:]

                async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True):
                    return sample_bars[-1]

            self.candle_client = FakeCandles()

    signal = await _build_manual_signal(FakeEngine(), SignalDirection.SHORT, "BTCUSDT")
    assert signal.source == "manual-cli"
    assert signal.direction == SignalDirection.SHORT
    assert signal.signal_bar_time_ms == sample_bars[-1].time_ms
    assert signal.signal_id.startswith("manual-short-")


@pytest.mark.asyncio
async def test_manual_signal_builder_surfaces_friendly_market_data_error() -> None:
    class FakeEngine:
        def __init__(self):
            self.clock = lambda: 1712665800000

            class FakeCandles:
                async def fetch_recent_closed_bars(self, symbol: str, limit: int):
                    raise RuntimeError("Binance kline bootstrap rate limited. HTTP 418; backing off until 1712665900000")

            self.candle_client = FakeCandles()

    with pytest.raises(RuntimeError, match="Unable to build manual signal because Binance closed-bar data is temporarily unavailable"):
        await _build_manual_signal(FakeEngine(), SignalDirection.LONG, "BTCUSDT")


@pytest.mark.asyncio
async def test_live_exit_snapshot_and_auto_close(app_config, tmp_path) -> None:
    store = SQLiteStore(tmp_path / "live_exit.sqlite3")
    await store.initialize()
    position = PositionState(
        symbol="BTCUSDT",
        status=TradeStatus.OPEN,
        direction=SignalDirection.LONG,
        position_size=Decimal("0.01"),
        entry_price=Decimal("70000"),
        entry_time_ms=1712665800000,
        entry_bar_time_ms=1712662200000,
        entry_atr=Decimal("250"),
        tp_price=Decimal("70375"),
        sl_price=Decimal("69750"),
        vertical_barrier_time_ms=1712683800000,
        entry_order_cloid="0x11111111111111111111111111111111",
        tp_order_cloid="0x22222222222222222222222222222222",
        sl_order_cloid="0x33333333333333333333333333333333",
        last_updated_ms=1712665800000,
    )
    await store.upsert_position_state(position)

    class FakeCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return [
                Bar(
                    time_ms=1712665800000,
                    open=Decimal("70200"),
                    high=Decimal("70300"),
                    low=Decimal("70100"),
                    close=Decimal("70280"),
                    volume=Decimal("120"),
                )
            ] * limit

        async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True):
            return Bar(
                time_ms=1712666700000,
                open=Decimal("70280"),
                high=Decimal("70410"),
                low=Decimal("70220"),
                close=Decimal("70390"),
                volume=Decimal("25"),
            )

    engine = TradingEngine(
        app_config,
        store,
        FakeCandles(),
        PaperExecutionAdapter(
            entry_slippage_bps=Decimal("5"),
            exit_slippage_bps=Decimal("5"),
            price_tick=Decimal("0.1"),
            size_step=Decimal("0.001"),
        ),
        clock=lambda: 1712666800000,
    )
    await engine.initialize()
    snapshot = await engine.inspect_live_exit("BTCUSDT")
    assert snapshot["has_open_position"] is True
    assert snapshot["exit_reason"] == "take_profit"
    _, reports = await engine.supervise_position_live("BTCUSDT")
    state = await store.get_position_state("BTCUSDT")
    assert reports
    assert state is not None
    assert state.status == TradeStatus.FLAT
    assert state.last_exit_reason == "take_profit"


@pytest.mark.asyncio
async def test_live_testnet_manual_supervision_hold_suppresses_immediate_exit(app_config, tmp_path) -> None:
    live_config = AppConfig(
        runtime_mode=RuntimeMode.LIVE,
        db_path=tmp_path / "live_testnet_hold.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=replace(app_config.hyperliquid, base_url="https://api.hyperliquid-testnet.xyz"),
        research=app_config.research,
        operator_ui=app_config.operator_ui,
    )
    store = SQLiteStore(live_config.db_path)
    await store.initialize()
    await store.upsert_position_state(
        PositionState(
            symbol="BTCUSDT",
            status=TradeStatus.OPEN,
            direction=SignalDirection.LONG,
            position_size=Decimal("0.001"),
            entry_price=Decimal("70000"),
            entry_time_ms=1712665800000,
            entry_bar_time_ms=1712662200000,
            entry_atr=Decimal("250"),
            tp_price=Decimal("70375"),
            sl_price=Decimal("69750"),
            vertical_barrier_time_ms=1712683800000,
            last_updated_ms=1712665800000,
        )
    )

    class FakeCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return [
                Bar(
                    time_ms=1712665800000,
                    open=Decimal("70280"),
                    high=Decimal("70350"),
                    low=Decimal("70220"),
                    close=Decimal("70300"),
                    volume=Decimal("20"),
                )
            ] * limit

        async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True):
            return Bar(
                time_ms=1712666700000,
                open=Decimal("70300"),
                high=Decimal("70410"),
                low=Decimal("70290"),
                close=Decimal("70395"),
                volume=Decimal("10"),
            )

    class FakeLiveAdapter:
        mode = RuntimeMode.LIVE

        async def start_user_streams(self):
            return None

        async def shutdown(self):
            return None

        async def execute(self, intents):
            return []

        async def drain_execution_events(self):
            return []

        def get_stream_status(self):
            return {"enabled": False, "started": False}

    engine = TradingEngine(live_config, store, FakeCandles(), FakeLiveAdapter(), clock=lambda: 1712666800000)
    engine._live_supervision_hold_until_by_symbol["BTCUSDT"] = 1712666820000

    snapshot = await engine.inspect_live_exit("BTCUSDT")
    _, reports = await engine.supervise_position_live("BTCUSDT")
    state = await store.get_position_state("BTCUSDT")

    assert snapshot["suppressed_exit_reason"] == "take_profit"
    assert snapshot["exit_reason"] is None
    assert snapshot["supervision_hold_remaining_ms"] == 20000
    assert reports == []
    assert state is not None
    assert state.status == TradeStatus.OPEN


@pytest.mark.asyncio
async def test_refresh_market_data_health_clears_stale_safe_mode(app_config, sample_bars, tmp_path) -> None:
    store = SQLiteStore(tmp_path / "health.sqlite3")
    await store.initialize()

    class FakeCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

        async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True):
            return sample_bars[-1]

        async def close(self):
            return None

    engine = TradingEngine(
        app_config,
        store,
        FakeCandles(),
        PaperExecutionAdapter(
            entry_slippage_bps=Decimal("5"),
            exit_slippage_bps=Decimal("5"),
            price_tick=Decimal("0.1"),
            size_step=Decimal("0.001"),
        ),
        clock=lambda: sample_bars[-1].time_ms + 60_000,
    )
    await engine.initialize()
    await engine.set_safe_mode(SafeModeReason.STALE_MARKET_DATA, "old stale condition")
    status_before = await store.get_safety_status()
    assert status_before is not None
    assert status_before.in_safe_mode is True
    result = await engine.refresh_market_data_health("BTCUSDT")
    status_after = await store.get_safety_status()
    assert result["healthy"] is True
    assert status_after is not None
    assert status_after.in_safe_mode is False


@pytest.mark.asyncio
async def test_refresh_market_data_health_requires_live_binance_stream(app_config, sample_bars, tmp_path) -> None:
    live_config = AppConfig(
        runtime_mode=RuntimeMode.LIVE,
        db_path=tmp_path / "market_stream.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=replace(app_config.binance, ws_stale_after_ms=1),
        hyperliquid=HyperliquidConfig(enable_live=False),
    )
    store = SQLiteStore(live_config.db_path)
    await store.initialize()

    class FakeCandles:
        async def start_market_streams(self, symbols: list[str]):
            return None

        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

        async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True):
            return sample_bars[-1]

        def get_stream_status(self):
            return {
                "enabled": True,
                "symbol_status": {"BTCUSDT": {"started_ms": 0, "last_kline_ws_message_ms": 0}},
            }

        async def close(self):
            return None

    engine = TradingEngine(
        live_config,
        store,
        FakeCandles(),
        PaperExecutionAdapter(
            entry_slippage_bps=Decimal("5"),
            exit_slippage_bps=Decimal("5"),
            price_tick=Decimal("0.1"),
            size_step=Decimal("0.001"),
        ),
        clock=lambda: 20_000,
    )
    await engine.initialize()
    result = await engine.refresh_market_data_health("BTCUSDT")
    safety = await store.get_safety_status()
    assert result["healthy"] is False
    assert result["stream_reason"] == "stale_kline_ws_messages"
    assert safety is not None
    assert safety.reason == SafeModeReason.STALE_MARKET_DATA


@pytest.mark.asyncio
async def test_signal_is_rejected_when_microstructure_veto_fails(app_config, sample_bars, tmp_path) -> None:
    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "micro_veto.sqlite3",
        webhook=app_config.webhook,
        strategy=replace(
            app_config.strategy,
            microstructure_primary_window_seconds=20,
            signed_imbalance_ratio_threshold=Decimal("0"),
            book_imbalance_ratio_threshold=Decimal("0"),
        ),
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
    )
    store = SQLiteStore(config.db_path)
    await store.initialize()

    class FakeCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

        async def get_microstructure_snapshot(self, symbol: str, *, windows_seconds, now_ms):
            return {
                "healthy": True,
                "top_of_book_imbalance": "-0.5",
                "windows": {"20": {"signed_ratio": "-0.2"}},
            }

    adapter = PaperExecutionAdapter(
        entry_slippage_bps=Decimal("5"),
        exit_slippage_bps=Decimal("5"),
        price_tick=Decimal("0.1"),
        size_step=Decimal("0.001"),
    )
    engine = TradingEngine(config, store, FakeCandles(), adapter, clock=lambda: 1712665800000)
    await engine.initialize()
    packet, reports, _ = await engine.handle_signal(
        SignalIntent(
            signal_id="micro-veto-1",
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            signal_bar_time_ms=1712662200000,
            received_time_ms=1712665800000,
            raw_payload={},
        )
    )
    assert packet.accepted is False
    assert packet.rejection_reason == "signed_imbalance_veto"
    assert reports == []


@pytest.mark.asyncio
async def test_signal_can_still_be_accepted_when_queue_depth_is_degraded_but_entry_microstructure_is_ready(app_config, sample_bars, tmp_path) -> None:
    store = SQLiteStore(tmp_path / "depth_degraded_signal.sqlite3")
    await store.initialize()

    class FakeCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

        async def get_microstructure_snapshot(self, symbol: str, *, windows_seconds, now_ms):
            return {
                "healthy": True,
                "entry_ready": True,
                "degraded": True,
                "depth_healthy": False,
                "warnings": ["order_book_unsynced"],
                "top_of_book_imbalance": "0.2",
                "windows": {"20": {"signed_ratio": "0.1"}},
            }

    adapter = PaperExecutionAdapter(
        entry_slippage_bps=Decimal("5"),
        exit_slippage_bps=Decimal("5"),
        price_tick=Decimal("0.1"),
        size_step=Decimal("0.001"),
    )
    engine = TradingEngine(app_config, store, FakeCandles(), adapter, clock=lambda: 1712665800000)
    await engine.initialize()
    packet, reports, _ = await engine.handle_signal(
        SignalIntent(
            signal_id="depth-degraded-1",
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            signal_bar_time_ms=1712662200000,
            received_time_ms=1712665800000,
            raw_payload={},
        )
    )
    assert packet.accepted is True
    assert packet.rejection_reason is None
    assert reports


@pytest.mark.asyncio
async def test_signal_feature_snapshot_includes_hurst_microstructure_and_basis(app_config, sample_bars, tmp_path) -> None:
    extended_bars = sample_bars * 2
    config = AppConfig(
        runtime_mode=RuntimeMode.LIVE,
        db_path=tmp_path / "feature_packet.sqlite3",
        webhook=app_config.webhook,
        strategy=replace(
            app_config.strategy,
            hurst_window_bars=32,
            microstructure_primary_window_seconds=20,
        ),
        binance=app_config.binance,
        hyperliquid=replace(app_config.hyperliquid, enable_live=False, max_basis_bps=Decimal("200")),
    )
    store = SQLiteStore(config.db_path)
    await store.initialize()

    class FakeCandles:
        async def start_market_streams(self, symbols: list[str]):
            return None

        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return extended_bars[-limit:]

        async def get_microstructure_snapshot(self, symbol: str, *, windows_seconds, now_ms):
            return {
                "healthy": True,
                "mid_price": "70580",
                "top_of_book_imbalance": "0.25",
                "windows": {"20": {"signed_ratio": "0.1", "sqrt_signed_ratio": "0.09", "flow_price_alignment_bps": "1.0"}},
            }

        async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True):
            return extended_bars[-1]

    class PassiveLiveAdapter:
        mode = RuntimeMode.LIVE

        async def start_user_streams(self):
            return None

        async def preflight_account(self):
            return {"ok": True}

        async def shutdown(self):
            return None

        def get_stream_status(self):
            return {"enabled": True, "started": True, "started_ms": 0, "last_ws_message_ms": 1712665800000}

        async def drain_execution_events(self):
            return []

        async def execute(self, intents):
            return []

        async def get_market_snapshot(self, symbol: str):
            return {"mid_price": "70585"}

    engine = TradingEngine(config, store, FakeCandles(), PassiveLiveAdapter(), clock=lambda: 1712665800000)
    await engine.initialize()
    packet, _, _ = await engine.handle_signal(
        SignalIntent(
            signal_id="feature-1",
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            signal_bar_time_ms=1712662200000,
            received_time_ms=1712665800000,
            raw_payload={},
        )
    )
    assert packet.feature_snapshot["hurst"] is not None
    assert packet.feature_snapshot["microstructure"]["top_of_book_imbalance"] == "0.25"
    assert packet.feature_snapshot["primary_signed_imbalance_ratio"] == "0.1"
    assert packet.feature_snapshot["primary_sqrt_signed_imbalance_ratio"] == "0.09"
    assert packet.feature_snapshot["basis"]["basis_bps"] is not None
    assert packet.feature_snapshot["rule_acceptance"]["status"] == "scored"


@pytest.mark.asyncio
async def test_basis_dislocation_rejects_live_signal(app_config, sample_bars, tmp_path) -> None:
    config = AppConfig(
        runtime_mode=RuntimeMode.LIVE,
        db_path=tmp_path / "basis_reject.sqlite3",
        webhook=app_config.webhook,
        strategy=replace(app_config.strategy, microstructure_primary_window_seconds=20),
        binance=app_config.binance,
        hyperliquid=replace(app_config.hyperliquid, enable_live=False, max_basis_bps=Decimal("5")),
    )
    store = SQLiteStore(config.db_path)
    await store.initialize()

    class FakeCandles:
        async def start_market_streams(self, symbols: list[str]):
            return None

        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

        async def get_microstructure_snapshot(self, symbol: str, *, windows_seconds, now_ms):
            return {
                "healthy": True,
                "mid_price": "70000",
                "top_of_book_imbalance": "0.25",
                "windows": {"20": {"signed_ratio": "0.1"}},
            }

        async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True):
            return sample_bars[-1]

    class PassiveLiveAdapter:
        mode = RuntimeMode.LIVE

        async def start_user_streams(self):
            return None

        async def preflight_account(self):
            return {"ok": True}

        async def shutdown(self):
            return None

        def get_stream_status(self):
            return {"enabled": True, "started": True, "started_ms": 0, "last_ws_message_ms": 1712665800000}

        async def drain_execution_events(self):
            return []

        async def execute(self, intents):
            return []

        async def get_market_snapshot(self, symbol: str):
            return {"mid_price": "70100"}

    engine = TradingEngine(config, store, FakeCandles(), PassiveLiveAdapter(), clock=lambda: 1712665800000)
    await engine.initialize()
    packet, reports, _ = await engine.handle_signal(
        SignalIntent(
            signal_id="basis-1",
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            signal_bar_time_ms=1712662200000,
            received_time_ms=1712665800000,
            raw_payload={},
        )
    )
    assert packet.accepted is False
    assert packet.rejection_reason == "basis_dislocation"
    assert reports == []


@pytest.mark.asyncio
async def test_reconcile_does_not_clear_unrelated_safe_mode(app_config, sample_bars, tmp_path) -> None:
    store = SQLiteStore(tmp_path / "reconcile_safe.sqlite3")
    await store.initialize()

    class FakeCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

        async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True):
            return sample_bars[-1]

    adapter = PaperExecutionAdapter(
        entry_slippage_bps=Decimal("5"),
        exit_slippage_bps=Decimal("5"),
        price_tick=Decimal("0.1"),
        size_step=Decimal("0.001"),
    )
    engine = TradingEngine(app_config, store, FakeCandles(), adapter, clock=lambda: sample_bars[-1].time_ms + 60_000)
    await engine.initialize()
    await engine.set_safe_mode(SafeModeReason.HEARTBEAT_LOSS, "heartbeat missing")
    await engine.bootstrap_reconcile("BTCUSDT")
    status = await store.get_safety_status()
    assert status is not None
    assert status.reason == SafeModeReason.HEARTBEAT_LOSS


@pytest.mark.asyncio
async def test_refresh_execution_health_recovers_stale_reconcile_gap(app_config, sample_bars, tmp_path) -> None:
    live_config = AppConfig(
        runtime_mode=RuntimeMode.LIVE,
        db_path=tmp_path / "reconcile_recover.sqlite3",
        webhook=app_config.webhook,
        strategy=replace(app_config.strategy, max_reconcile_gap_ms=1),
        binance=app_config.binance,
        hyperliquid=HyperliquidConfig(enable_live=False),
    )
    store = SQLiteStore(live_config.db_path)
    await store.initialize()
    await store.upsert_position_state(
        PositionState(
            symbol="BTCUSDT",
            status=TradeStatus.OPEN,
            direction=SignalDirection.LONG,
            position_size=Decimal("0.01"),
            entry_price=Decimal("70000"),
            entry_time_ms=100,
            entry_bar_time_ms=0,
            entry_atr=Decimal("250"),
            tp_price=Decimal("70375"),
            sl_price=Decimal("69750"),
            vertical_barrier_time_ms=1000,
            last_exchange_reconcile_ms=0,
            last_updated_ms=0,
        )
    )

    class FakeCandles:
        async def start_market_streams(self, symbols: list[str]):
            return None

        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

        async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True):
            return sample_bars[-1]

    class FreshReconcileAdapter:
        mode = RuntimeMode.LIVE

        async def start_user_streams(self) -> None:
            return None

        async def preflight_account(self) -> dict[str, object]:
            return {"ok": True}

        async def shutdown(self) -> None:
            return None

        def get_stream_status(self) -> dict[str, object]:
            return {"enabled": True, "started": True, "started_ms": 0, "last_ws_message_ms": 10_000}

        async def drain_execution_events(self) -> list[dict[str, object]]:
            return []

        async def reconcile(self, symbol: str) -> dict[str, object]:
            return {"symbol": symbol, "position_size": "0.01", "side": SignalDirection.LONG, "open_order_cloids": []}

    engine = TradingEngine(live_config, store, FakeCandles(), FreshReconcileAdapter(), clock=lambda: 10_000)
    await engine.initialize()
    result = await engine.refresh_execution_health()
    position = await store.get_position_state("BTCUSDT")
    safety = await store.get_safety_status()
    assert result["healthy"] is True
    assert position is not None
    assert position.last_exchange_reconcile_ms == 10_000
    assert safety is not None
    assert safety.in_safe_mode is False


@pytest.mark.asyncio
async def test_refresh_execution_health_enters_safe_mode_when_reconcile_gap_cannot_refresh(app_config, sample_bars, tmp_path) -> None:
    live_config = AppConfig(
        runtime_mode=RuntimeMode.LIVE,
        db_path=tmp_path / "reconcile_stale.sqlite3",
        webhook=app_config.webhook,
        strategy=replace(app_config.strategy, max_reconcile_gap_ms=1),
        binance=app_config.binance,
        hyperliquid=HyperliquidConfig(enable_live=False),
    )
    store = SQLiteStore(live_config.db_path)
    await store.initialize()
    await store.upsert_position_state(
        PositionState(
            symbol="BTCUSDT",
            status=TradeStatus.OPEN,
            direction=SignalDirection.LONG,
            position_size=Decimal("0.01"),
            entry_price=Decimal("70000"),
            entry_time_ms=100,
            entry_bar_time_ms=0,
            entry_atr=Decimal("250"),
            tp_price=Decimal("70375"),
            sl_price=Decimal("69750"),
            vertical_barrier_time_ms=1000,
            last_exchange_reconcile_ms=0,
            last_updated_ms=0,
        )
    )

    class FakeCandles:
        async def start_market_streams(self, symbols: list[str]):
            return None

        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

        async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True):
            return sample_bars[-1]

    class FailingReconcileAdapter:
        mode = RuntimeMode.LIVE

        async def start_user_streams(self) -> None:
            return None

        async def preflight_account(self) -> dict[str, object]:
            return {"ok": True}

        async def shutdown(self) -> None:
            return None

        def get_stream_status(self) -> dict[str, object]:
            return {"enabled": True, "started": True, "started_ms": 0, "last_ws_message_ms": 10_000}

        async def drain_execution_events(self) -> list[dict[str, object]]:
            return []

        async def reconcile(self, symbol: str) -> dict[str, object]:
            raise RuntimeError("reconcile unavailable")

    engine = TradingEngine(live_config, store, FakeCandles(), FailingReconcileAdapter(), clock=lambda: 10_000)
    await engine.initialize()
    result = await engine.refresh_execution_health()
    safety = await store.get_safety_status()
    assert result["healthy"] is False
    assert result["reason"] == "stale_reconciliation_gap"
    assert result["reconcile_health"]["healthy"] is False
    assert safety is not None
    assert safety.reason == SafeModeReason.RECONCILIATION_STALE


@pytest.mark.asyncio
async def test_hyperliquid_stream_starts_and_reports_health(app_config, sample_bars, tmp_path) -> None:
    live_config = AppConfig(
        runtime_mode=RuntimeMode.LIVE,
        db_path=tmp_path / "stream.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=HyperliquidConfig(
            base_url="https://api.hyperliquid-testnet.xyz",
            account_address="0xabc",
            enable_live=False,
            ws_stale_after_ms=120000,
        ),
    )
    store = SQLiteStore(live_config.db_path)
    await store.initialize()

    class FakeCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

        async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True):
            return sample_bars[-1]

    class FakeInfo:
        def __init__(self):
            self.subscriptions = []
            self.unsubscribed = []
            self.disconnected = False

        def user_role(self, address):
            return {"role": "user"}

        def spot_user_state(self, address):
            return {"balances": [{"coin": "USDC", "total": "10.0"}]}

        def query_user_abstraction_state(self, address):
            return "unifiedAccount"

        def subscribe(self, subscription, callback):
            self.subscriptions.append(subscription)
            callback({"channel": "orderUpdates", "data": {"orders": []}})
            return len(self.subscriptions)

        def unsubscribe(self, subscription, subscription_id):
            self.unsubscribed.append((subscription, subscription_id))
            return True

        def disconnect_websocket(self):
            self.disconnected = True

        def user_state(self, address, dex=""):
            return {"assetPositions": []}

        def open_orders(self, address, dex=""):
            return []

        def post(self, url_path, payload):
            return {"status": "unknownOid"}

    adapter = HyperliquidExecutionAdapter(live_config.hyperliquid, exchange_client=object(), info_client=FakeInfo())
    engine = TradingEngine(live_config, store, FakeCandles(), adapter, clock=lambda: sample_bars[-1].time_ms + 60_000)
    await engine.initialize()
    execution_health = await engine.refresh_execution_health()
    assert execution_health["healthy"] is True
    assert execution_health["status"]["started"] is True
    assert execution_health["status"]["subscription_count"] == 3
    await engine.shutdown()
    assert adapter.get_stream_status()["started"] is False


@pytest.mark.asyncio
async def test_hyperliquid_agent_address_resolves_master_account_for_queries_and_streams(app_config, sample_bars, tmp_path) -> None:
    live_config = AppConfig(
        runtime_mode=RuntimeMode.LIVE,
        db_path=tmp_path / "agent_resolve.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=HyperliquidConfig(
            account_address="0xagent",
            enable_live=False,
        ),
    )
    store = SQLiteStore(live_config.db_path)
    await store.initialize()

    class FakeCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

        async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True):
            return sample_bars[-1]

    class FakeInfo:
        def __init__(self):
            self.subscriptions = []

        def user_role(self, address):
            return {"role": "user"}

        def spot_user_state(self, address):
            return {"balances": [{"coin": "USDC", "total": "10.0"}]}

        def query_user_abstraction_state(self, address):
            return "unifiedAccount"

        def user_role(self, address):
            if address == "0xagent":
                return {"role": "agent", "data": {"user": "0xmain"}}
            if address == "0xmain":
                return {"role": "user"}
            return {"role": "unknown"}

        def user_state(self, address, dex=""):
            assert address == "0xmain"
            return {"marginSummary": {"accountValue": "0.0"}, "assetPositions": []}

        def spot_user_state(self, address):
            assert address == "0xmain"
            return {"balances": [{"coin": "USDC", "total": "10.0"}]}

        def query_user_abstraction_state(self, address):
            assert address == "0xmain"
            return "unifiedAccount"

        def subscribe(self, subscription, callback):
            self.subscriptions.append(subscription)
            return len(self.subscriptions)

        def unsubscribe(self, subscription, subscription_id):
            return True

        def disconnect_websocket(self):
            return None

        def open_orders(self, address, dex=""):
            assert address == "0xmain"
            return []

        def post(self, url_path, payload):
            return {"status": "unknownOid"}

    adapter = HyperliquidExecutionAdapter(live_config.hyperliquid, exchange_client=object(), info_client=FakeInfo())
    adapter._signing_address = "0xagent"
    adapter._resolve_account_context()
    engine = TradingEngine(live_config, store, FakeCandles(), adapter, clock=lambda: sample_bars[-1].time_ms + 60_000)
    await engine.initialize()
    preflight = await adapter.preflight_account()
    assert adapter.account_address() == "0xmain"
    assert preflight["ok"] is True
    assert preflight["account_address"] == "0xmain"
    assert preflight["account_role"] == "agent"
    assert adapter.get_stream_status()["account_address"] == "0xmain"


@pytest.mark.asyncio
async def test_hyperliquid_await_order_activity_uses_full_configured_timeout() -> None:
    class DelayedStatusAdapter(HyperliquidExecutionAdapter):
        def __init__(self):
            super().__init__(
                HyperliquidConfig(enable_live=False, order_timeout_seconds=1),
                exchange_client=object(),
                info_client=object(),
            )
            self.started_at = time.monotonic()

        async def query_order_status(self, *, cloid: str | None = None, exchange_order_id: str | None = None, dex: str = ""):
            if time.monotonic() - self.started_at < 0.85:
                return None
            return {
                "status": "order",
                "order": {
                    "order": {
                        "coin": "BTC",
                        "oid": int(exchange_order_id),
                        "cloid": cloid,
                        "limitPx": "72500.0",
                        "sz": "0.001",
                    },
                    "status": "filled",
                    "statusTimestamp": 1712665800000,
                },
            }

    adapter = DelayedStatusAdapter()
    intent = ExecutionIntent(
        intent_id="enter-delayed",
        mode=RuntimeMode.LIVE,
        intent_type=ExecutionIntentType.ENTER,
        symbol="BTCUSDT",
        direction=SignalDirection.LONG,
        size=Decimal("0.001"),
        reference_price=Decimal("72500"),
        cloid="0x1234567890abcdef1234567890abcdef",
    )
    report = ExecutionReport(
        intent_id=intent.intent_id,
        intent_type=intent.intent_type,
        status=ExecutionStatus.ACKED,
        symbol=intent.symbol,
        exchange_order_id="12345",
        cloid=intent.cloid,
    )
    adapter._track_execution_report(intent, report)

    activity = await adapter.await_order_activity(symbol="BTCUSDT", cloid=intent.cloid, exchange_order_id="12345")

    assert activity is not None
    assert activity["last_order_status"] == "filled"


@pytest.mark.asyncio
async def test_hyperliquid_normalize_decision_packet_uses_exchange_valid_prices() -> None:
    class FakeInfo:
        coin_to_asset = {"BTC": 3}
        asset_to_sz_decimals = {3: 5}

    adapter = HyperliquidExecutionAdapter(HyperliquidConfig(enable_live=False), exchange_client=object(), info_client=FakeInfo())
    packet = DecisionPacket(
        signal=SignalIntent(
            signal_id="normalize-1",
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            signal_bar_time_ms=1712662200000,
            received_time_ms=1712665800000,
            raw_payload={},
        ),
        mode=RuntimeMode.LIVE,
        action=DecisionAction.ACCEPT,
        accepted=True,
        intended_size=Decimal("0.001239"),
        entry_reference_price=Decimal("72154.8"),
        atr=Decimal("373.9"),
        tp_price=Decimal("72715.65"),
        sl_price=Decimal("71780.95"),
        vertical_barrier_time_ms=1712683800000,
        feature_snapshot={},
    )

    normalized = adapter.normalize_decision_packet(packet)

    assert normalized.intended_size == Decimal("0.00123")
    assert normalized.tp_price == Decimal("72715")
    assert normalized.sl_price == Decimal("71781")
    assert normalized.feature_snapshot["hyperliquid_tp_price"] == "72715"
    assert normalized.feature_snapshot["hyperliquid_sl_price"] == "71781"


@pytest.mark.asyncio
async def test_live_testnet_keeps_binance_barriers_when_exchange_fill_drifts(app_config) -> None:
    live_config = AppConfig(
        runtime_mode=RuntimeMode.LIVE,
        db_path=app_config.db_path,
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=replace(app_config.hyperliquid, base_url="https://api.hyperliquid-testnet.xyz"),
        research=app_config.research,
        operator_ui=app_config.operator_ui,
    )
    engine = TradingEngine(live_config, SQLiteStore(live_config.db_path), object(), ShadowExecutionAdapter())
    packet = DecisionPacket(
        signal=SignalIntent(
            signal_id="live-testnet-canonical",
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            signal_bar_time_ms=1712662200000,
            received_time_ms=1712665800000,
            raw_payload={},
        ),
        mode=RuntimeMode.LIVE,
        action=DecisionAction.ACCEPT,
        accepted=True,
        intended_size=Decimal("0.001"),
        entry_reference_price=Decimal("70000"),
        atr=Decimal("250"),
        tp_price=Decimal("70375"),
        sl_price=Decimal("69750"),
        vertical_barrier_time_ms=1712683800000,
        feature_snapshot={},
    )
    reports = [
        ExecutionReport(
            intent_id="enter-1",
            intent_type=ExecutionIntentType.ENTER,
            status=ExecutionStatus.FILLED,
            symbol="BTCUSDT",
            cloid="0xentry",
            filled_price=Decimal("73166.8"),
            filled_size=Decimal("0.001"),
        )
    ]

    adjusted = engine._packet_with_filled_entry(packet, reports)

    assert adjusted.entry_reference_price == Decimal("70000")
    assert adjusted.tp_price == Decimal("70375")
    assert adjusted.sl_price == Decimal("69750")


@pytest.mark.asyncio
async def test_live_testnet_position_state_keeps_binance_entry_and_records_exchange_fill(app_config, tmp_path) -> None:
    live_config = AppConfig(
        runtime_mode=RuntimeMode.LIVE,
        db_path=tmp_path / "live_testnet_entry.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=replace(app_config.hyperliquid, base_url="https://api.hyperliquid-testnet.xyz"),
        research=app_config.research,
        operator_ui=app_config.operator_ui,
    )
    store = SQLiteStore(live_config.db_path)
    await store.initialize()
    engine = TradingEngine(live_config, store, object(), ShadowExecutionAdapter(), clock=lambda: 1712665800000)
    packet = DecisionPacket(
        signal=SignalIntent(
            signal_id="live-testnet-entry-state",
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            signal_bar_time_ms=1712662200000,
            received_time_ms=1712665800000,
            raw_payload={},
        ),
        mode=RuntimeMode.LIVE,
        action=DecisionAction.ACCEPT,
        accepted=True,
        intended_size=Decimal("0.001"),
        entry_reference_price=Decimal("70000"),
        atr=Decimal("250"),
        tp_price=Decimal("70375"),
        sl_price=Decimal("69750"),
        vertical_barrier_time_ms=1712683800000,
        feature_snapshot={"basis": {"basis_bps": "1.25"}},
    )
    reports = [
        ExecutionReport(
            intent_id="enter-1",
            intent_type=ExecutionIntentType.ENTER,
            status=ExecutionStatus.FILLED,
            symbol="BTCUSDT",
            cloid="0xentry",
            filled_price=Decimal("73166.8"),
            filled_size=Decimal("0.001"),
            exchange_order_id="12345",
        )
    ]

    await engine._apply_reports(packet, None, reports, 1712665800000, entry_confirmed=True)
    state = await store.get_position_state("BTCUSDT")
    metrics = await store.summarize_runtime_metrics("BTCUSDT")

    assert state is not None
    assert state.entry_price == Decimal("70000")
    trade_entry_metric = next(metric for metric in metrics["recent_metrics"] if metric["metric_type"] == "trade_entry")
    assert trade_entry_metric["payload"]["entry_price"] == "70000"
    assert trade_entry_metric["payload"]["exchange_entry_price"] == "73166.8"
    assert trade_entry_metric["payload"]["canonical_entry_source"] == "binance_reference"


@pytest.mark.asyncio
async def test_hyperliquid_stream_staleness_enters_safe_mode(app_config, sample_bars, tmp_path) -> None:
    live_config = AppConfig(
        runtime_mode=RuntimeMode.LIVE,
        db_path=tmp_path / "stream_stale.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=HyperliquidConfig(
            base_url="https://api.hyperliquid-testnet.xyz",
            account_address="0xabc",
            enable_live=False,
            ws_stale_after_ms=1,
        ),
    )
    store = SQLiteStore(live_config.db_path)
    await store.initialize()

    class FakeCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

        async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True):
            return sample_bars[-1]

    class FakeInfo:
        def __init__(self):
            self.subscriptions = []

        def subscribe(self, subscription, callback):
            self.subscriptions.append(subscription)
            return len(self.subscriptions)

        def unsubscribe(self, subscription, subscription_id):
            return True

        def disconnect_websocket(self):
            return None

        def user_state(self, address, dex=""):
            return {"assetPositions": []}

        def open_orders(self, address, dex=""):
            return []

    adapter = HyperliquidExecutionAdapter(live_config.hyperliquid, exchange_client=object(), info_client=FakeInfo())
    engine = TradingEngine(live_config, store, FakeCandles(), adapter, clock=lambda: 20_000)
    await engine.initialize()
    adapter._stream_started_ms = 0
    result = await engine.refresh_execution_health()
    safety = await store.get_safety_status()
    assert result["healthy"] is False
    assert safety is not None
    assert safety.reason == SafeModeReason.HEARTBEAT_LOSS


@pytest.mark.asyncio
async def test_refresh_execution_health_keeps_connected_quiet_ws_healthy(app_config, sample_bars, tmp_path) -> None:
    live_config = AppConfig(
        runtime_mode=RuntimeMode.LIVE,
        db_path=tmp_path / "stream_quiet.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=HyperliquidConfig(
            base_url="https://api.hyperliquid-testnet.xyz",
            account_address="0xabc",
            enable_live=False,
            ws_stale_after_ms=1,
        ),
    )
    store = SQLiteStore(live_config.db_path)
    await store.initialize()

    class FakeCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

        async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True):
            return sample_bars[-1]

    class FakeSocket:
        keep_running = True

        class Sock:
            connected = True

        sock = Sock()

    class FakeWsManager:
        ws_ready = True
        ws = FakeSocket()

    class FakeInfo:
        def __init__(self):
            self.subscriptions = []
            self.ws_manager = FakeWsManager()

        def subscribe(self, subscription, callback):
            self.subscriptions.append(subscription)
            return len(self.subscriptions)

        def unsubscribe(self, subscription, subscription_id):
            return True

        def disconnect_websocket(self):
            return None

        def user_state(self, address, dex=""):
            return {"assetPositions": [], "marginSummary": {"accountValue": "100"}}

        def spot_user_state(self, address):
            return {"balances": []}

        def open_orders(self, address, dex=""):
            return []

        def all_mids(self):
            return {"BTC": "70000"}

    adapter = HyperliquidExecutionAdapter(live_config.hyperliquid, exchange_client=object(), info_client=FakeInfo())
    engine = TradingEngine(live_config, store, FakeCandles(), adapter, clock=lambda: 20_000)
    await engine.initialize()
    adapter._stream_started_ms = 0

    result = await engine.refresh_execution_health()
    safety = await store.get_safety_status()

    assert result["healthy"] is True
    assert result["reason"] is None
    assert safety is not None
    assert safety.in_safe_mode is False


@pytest.mark.asyncio
async def test_live_testnet_manual_validation_uses_fixed_protective_trigger_prices(app_config, sample_bars, tmp_path) -> None:
    live_config = AppConfig(
        runtime_mode=RuntimeMode.LIVE,
        db_path=tmp_path / "live_testnet_validation.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=replace(app_config.hyperliquid, base_url="https://api.hyperliquid-testnet.xyz"),
        research=app_config.research,
        operator_ui=app_config.operator_ui,
    )
    store = SQLiteStore(live_config.db_path)
    await store.initialize()

    class FakeCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

        async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True):
            return sample_bars[-1]

    class FakeAdapter:
        mode = RuntimeMode.LIVE

        def __init__(self):
            self.intents = []

        async def start_user_streams(self):
            return None

        async def shutdown(self):
            return None

        async def preflight_account(self):
            return {"ok": True}

        def normalize_decision_packet(self, packet):
            return packet

        def get_stream_status(self):
            return {"enabled": False, "started": False}

    engine = TradingEngine(live_config, store, FakeCandles(), FakeAdapter(), clock=lambda: 1712665800000)
    await engine.initialize()

    packet = DecisionPacket(
        signal=SignalIntent(
            signal_id="manual-long-validation",
            source="manual-cli",
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            signal_bar_time_ms=sample_bars[-1].time_ms,
            received_time_ms=1712665800000,
            raw_payload={
                "manual_testnet_protection_test": {
                    "requested": True,
                    "cleanup_after_seconds": 10,
                    "fixed_tp_trigger_price": "75000",
                    "fixed_sl_trigger_price": "70000",
                    "testing_only": True,
                    "remove_before_mainnet": True,
                }
            },
        ),
        mode=RuntimeMode.LIVE,
        action=DecisionAction.ACCEPT,
        accepted=True,
        intended_size=Decimal("0.001"),
        entry_reference_price=Decimal("73166.8"),
        atr=Decimal("256.6"),
        tp_price=Decimal("73551.7"),
        sl_price=Decimal("72910.2"),
        vertical_barrier_time_ms=1712752200000,
        feature_snapshot={},
    )
    override_packet = engine._testnet_validation_protection_packet(packet)
    protective_intents = build_protective_intents(override_packet)
    tp_intent = next(intent for intent in protective_intents if intent.intent_type == ExecutionIntentType.PROTECTIVE_TP)
    sl_intent = next(intent for intent in protective_intents if intent.intent_type == ExecutionIntentType.PROTECTIVE_SL)

    assert packet.tp_price == Decimal("73551.7")
    assert packet.sl_price == Decimal("72910.2")
    assert tp_intent.trigger_price == Decimal("75000")
    assert sl_intent.trigger_price == Decimal("70000")
    assert override_packet.feature_snapshot["hyperliquid_testnet_validation_protection_mode"]["testing_only"] is True


@pytest.mark.asyncio
async def test_live_mode_does_not_place_protective_orders_before_confirmed_entry(app_config, sample_bars, tmp_path) -> None:
    live_config = AppConfig(
        runtime_mode=RuntimeMode.LIVE,
        db_path=tmp_path / "live_confirm.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=HyperliquidConfig(account_address="0xmain", enable_live=False),
    )
    store = SQLiteStore(live_config.db_path)
    await store.initialize()

    class FakeCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

        async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True):
            return sample_bars[-1]

    class FakeExchange:
        def __init__(self):
            self.calls = []

        def _slippage_price(self, name: str, is_buy: bool, slippage: float, px: float | None = None) -> float:
            assert px is not None
            return px

        def market_open(self, *args):
            self.calls.append(("market_open", args))
            return {"response": {"data": {"statuses": [{"resting": {"oid": 12345}}]}}}

        def market_close(self, *args):
            self.calls.append(("market_close", args))
            return {"response": {"data": {"statuses": [{"filled": {"oid": 12346}}]}}}

        def bulk_cancel_by_cloid(self, *args):
            self.calls.append(("bulk_cancel_by_cloid", args))
            return {"response": {"data": {"statuses": [{"success": True}]}}}

        def order(self, *args):
            self.calls.append(("order", args))
            return {"response": {"data": {"statuses": [{"resting": {"oid": 12347}}]}}}

    class FakeInfo:
        def user_role(self, address):
            return {"role": "user"}

        def spot_user_state(self, address):
            return {"balances": [{"coin": "USDC", "total": "10.0"}]}

        def query_user_abstraction_state(self, address):
            return "unifiedAccount"

        def user_state(self, address, dex=""):
            return {"assetPositions": []}

        def open_orders(self, address, dex=""):
            return []

        def post(self, url_path, payload):
            return {"status": "unknownOid"}

    adapter = HyperliquidExecutionAdapter(live_config.hyperliquid, exchange_client=FakeExchange(), info_client=FakeInfo())
    engine = TradingEngine(live_config, store, FakeCandles(), adapter, clock=lambda: 1712665800000)
    await engine.initialize()
    _, reports, _ = await engine.handle_signal(
        SignalIntent(
            signal_id="live-no-confirm",
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            signal_bar_time_ms=1712662200000,
            received_time_ms=1712665800000,
            raw_payload={},
        )
    )
    safety = await store.get_safety_status()
    assert len(reports) == 1
    assert reports[0].intent_type == ExecutionIntentType.ENTER
    assert safety is not None
    assert safety.reason == SafeModeReason.ORDER_TIMEOUT


@pytest.mark.asyncio
async def test_manual_signal_can_arm_short_lived_testnet_protection_cleanup(app_config, sample_bars, monkeypatch) -> None:
    class FakeCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

    packet = DecisionPacket(
        signal=SignalIntent(
            signal_id="manual-live-test",
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            signal_bar_time_ms=1712662200000,
            received_time_ms=1712665800000,
            raw_payload={},
        ),
        mode=RuntimeMode.LIVE,
        action=DecisionAction.ACCEPT,
        accepted=True,
        intended_size=Decimal("0.001"),
        entry_reference_price=Decimal("70000"),
        atr=Decimal("250"),
        tp_price=Decimal("70375"),
        sl_price=Decimal("69750"),
        vertical_barrier_time_ms=1712683800000,
    )
    reports = [
        ExecutionReport(
            intent_id="enter-1",
            intent_type=ExecutionIntentType.ENTER,
            status=ExecutionStatus.FILLED,
            symbol="BTCUSDT",
            cloid="0xentry",
            filled_price=Decimal("70005"),
            filled_size=Decimal("0.001"),
        ),
        ExecutionReport(
            intent_id="tp-1",
            intent_type=ExecutionIntentType.PROTECTIVE_TP,
            status=ExecutionStatus.ACKED,
            symbol="BTCUSDT",
            cloid="0xtp",
        ),
        ExecutionReport(
            intent_id="sl-1",
            intent_type=ExecutionIntentType.PROTECTIVE_SL,
            status=ExecutionStatus.ACKED,
            symbol="BTCUSDT",
            cloid="0xsl",
        ),
    ]
    ticket = ActionTicket(
        ticket_id="ticket-1",
        signal_id="manual-live-test",
        mode=RuntimeMode.LIVE,
        symbol="BTCUSDT",
        decision_time_ms=1712665800000,
        action_type="accept",
        readable_summary="manual live test accepted",
    )

    class FakeEngine:
        def __init__(self, config):
            self.config = config
            self.candle_client = FakeCandles()

        def clock(self):
            return 1712665800000

        async def handle_signal(self, signal):
            return packet, reports, ticket

        async def cancel_testnet_protective_orders(self, symbol: str, **kwargs):
            return {"symbol": symbol, **kwargs}

    live_config = AppConfig(
        runtime_mode=RuntimeMode.LIVE,
        db_path=app_config.db_path,
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=replace(app_config.hyperliquid, base_url="https://api.hyperliquid-testnet.xyz"),
        research=app_config.research,
        operator_ui=app_config.operator_ui,
    )
    engine = FakeEngine(live_config)
    captured: dict[str, object] = {"armed": False}

    def fake_create_task(coro):
        captured["armed"] = True
        coro.close()

        class DummyTask:
            pass

        return DummyTask()

    monkeypatch.setattr("tradingbotsuite.operator_commands.asyncio.create_task", fake_create_task)
    result = await execute_manual_signal(
        engine,
        symbol="BTCUSDT",
        direction=SignalDirection.LONG,
        testnet_short_lived_protections=True,
    )

    cleanup = result["testnet_short_lived_protections"]
    assert cleanup["requested"] is True
    assert cleanup["eligible"] is True
    assert cleanup["armed"] is True
    assert cleanup["reason"] == "cleanup_scheduled"
    assert cleanup["tp_order_cloid"] == "0xtp"
    assert cleanup["sl_order_cloid"] == "0xsl"
    assert captured["armed"] is True
    assert result["signal"]["raw_payload"]["manual_testnet_protection_test"]["cleanup_after_seconds"] == 10


@pytest.mark.asyncio
async def test_cancel_testnet_protective_orders_clears_position_cloids(app_config, sample_bars, tmp_path) -> None:
    live_config = AppConfig(
        runtime_mode=RuntimeMode.LIVE,
        db_path=tmp_path / "testnet_cleanup.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=replace(app_config.hyperliquid, base_url="https://api.hyperliquid-testnet.xyz"),
        research=app_config.research,
        operator_ui=app_config.operator_ui,
    )
    store = SQLiteStore(live_config.db_path)
    await store.initialize()

    class FakeCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

        async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True):
            return sample_bars[-1]

    class FakeAdapter:
        mode = RuntimeMode.LIVE

        def __init__(self):
            self.intents = []

        async def start_user_streams(self):
            return None

        async def shutdown(self):
            return None

        async def drain_execution_events(self):
            return []

        async def execute(self, intents):
            self.intents.extend(intents)
            return [
                ExecutionReport(
                    intent_id=intent.intent_id,
                    intent_type=intent.intent_type,
                    status=ExecutionStatus.CANCELED,
                    symbol=intent.symbol,
                    cloid=intent.cloid,
                )
                for intent in intents
            ]

        async def reconcile(self, symbol: str):
            return {"symbol": symbol, "position_size": "0.001", "side": "long", "open_order_cloids": []}

    adapter = FakeAdapter()
    engine = TradingEngine(live_config, store, FakeCandles(), adapter, clock=lambda: 1712665810000)
    await store.upsert_position_state(
        PositionState(
            symbol="BTCUSDT",
            status=TradeStatus.OPEN,
            direction=SignalDirection.LONG,
            position_size=Decimal("0.001"),
            entry_price=Decimal("70000"),
            entry_time_ms=1712665800000,
            entry_bar_time_ms=1712662200000,
            entry_atr=Decimal("250"),
            tp_price=Decimal("70375"),
            sl_price=Decimal("69750"),
            tp_order_cloid="0xtp",
            sl_order_cloid="0xsl",
            last_updated_ms=1712665800000,
        )
    )

    result = await engine.cancel_testnet_protective_orders(
        "BTCUSDT",
        expected_tp_cloid="0xtp",
        expected_sl_cloid="0xsl",
        reason="manual_testnet_cleanup:manual-live-test",
    )
    state = await store.get_position_state("BTCUSDT")

    assert result["skipped_reason"] is None
    assert sorted(result["canceled_cloids"]) == ["0xsl", "0xtp"]
    assert [intent.intent_type for intent in adapter.intents] == [ExecutionIntentType.CANCEL, ExecutionIntentType.CANCEL]
    assert state is not None
    assert state.status == TradeStatus.OPEN
    assert state.tp_order_cloid is None
    assert state.sl_order_cloid is None


@pytest.mark.asyncio
async def test_cancel_testnet_protective_orders_uses_expected_cloids_when_position_state_lost_them(
    app_config,
    sample_bars,
    tmp_path,
) -> None:
    live_config = AppConfig(
        runtime_mode=RuntimeMode.LIVE,
        db_path=tmp_path / "testnet_cleanup_expected.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=replace(app_config.hyperliquid, base_url="https://api.hyperliquid-testnet.xyz"),
        research=app_config.research,
        operator_ui=app_config.operator_ui,
    )
    store = SQLiteStore(live_config.db_path)
    await store.initialize()

    class FakeCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

        async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True):
            return sample_bars[-1]

    class FakeAdapter:
        mode = RuntimeMode.LIVE

        def __init__(self):
            self.intents = []

        async def start_user_streams(self):
            return None

        async def shutdown(self):
            return None

        async def drain_execution_events(self):
            return []

        async def execute(self, intents):
            self.intents.extend(intents)
            return [
                ExecutionReport(
                    intent_id=intent.intent_id,
                    intent_type=intent.intent_type,
                    status=ExecutionStatus.CANCELED,
                    symbol=intent.symbol,
                    cloid=intent.cloid,
                )
                for intent in intents
            ]

        async def reconcile(self, symbol: str):
            return {"symbol": symbol, "position_size": "0.001", "side": "long", "open_order_cloids": []}

    adapter = FakeAdapter()
    engine = TradingEngine(live_config, store, FakeCandles(), adapter, clock=lambda: 1712665810000)
    await store.upsert_position_state(
        PositionState(
            symbol="BTCUSDT",
            status=TradeStatus.OPEN,
            direction=SignalDirection.LONG,
            position_size=Decimal("0.001"),
            entry_price=Decimal("70000"),
            entry_time_ms=1712665800000,
            entry_bar_time_ms=1712662200000,
            entry_atr=Decimal("250"),
            tp_price=Decimal("70375"),
            sl_price=Decimal("69750"),
            tp_order_cloid=None,
            sl_order_cloid=None,
            last_updated_ms=1712665800000,
        )
    )

    result = await engine.cancel_testnet_protective_orders(
        "BTCUSDT",
        expected_tp_cloid="0xtp",
        expected_sl_cloid="0xsl",
        reason="manual_testnet_cleanup:manual-live-test",
    )

    assert result["skipped_reason"] is None
    assert sorted(result["canceled_cloids"]) == ["0xsl", "0xtp"]
    assert [intent.cloid for intent in adapter.intents] == ["0xtp", "0xsl"]


@pytest.mark.asyncio
async def test_cancel_testnet_protective_orders_runs_without_open_position_when_expected_cloids_are_known(
    app_config,
    sample_bars,
    tmp_path,
) -> None:
    live_config = AppConfig(
        runtime_mode=RuntimeMode.LIVE,
        db_path=tmp_path / "testnet_cleanup_flat.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=replace(app_config.hyperliquid, base_url="https://api.hyperliquid-testnet.xyz"),
        research=app_config.research,
        operator_ui=app_config.operator_ui,
    )
    store = SQLiteStore(live_config.db_path)
    await store.initialize()

    class FakeCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

        async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True):
            return sample_bars[-1]

    class FakeAdapter:
        mode = RuntimeMode.LIVE

        def __init__(self):
            self.intents = []

        async def start_user_streams(self):
            return None

        async def shutdown(self):
            return None

        async def drain_execution_events(self):
            return []

        async def execute(self, intents):
            self.intents.extend(intents)
            return [
                ExecutionReport(
                    intent_id=intent.intent_id,
                    intent_type=intent.intent_type,
                    status=ExecutionStatus.CANCELED,
                    symbol=intent.symbol,
                    cloid=intent.cloid,
                )
                for intent in intents
            ]

        async def reconcile(self, symbol: str):
            return {"symbol": symbol, "position_size": "0", "side": None, "open_order_cloids": []}

    adapter = FakeAdapter()
    engine = TradingEngine(live_config, store, FakeCandles(), adapter, clock=lambda: 1712665810000)

    result = await engine.cancel_testnet_protective_orders(
        "BTCUSDT",
        expected_tp_cloid="0xtp",
        expected_sl_cloid="0xsl",
        reason="manual_testnet_cleanup:manual-live-test",
    )

    assert result["position_open"] is False
    assert result["skipped_reason"] is None
    assert sorted(result["canceled_cloids"]) == ["0xsl", "0xtp"]
    assert [intent.cloid for intent in adapter.intents] == ["0xtp", "0xsl"]


@pytest.mark.asyncio
async def test_engine_can_switch_runtime_mode_when_flat(app_config, sample_bars, tmp_path) -> None:
    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "switch_mode.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=app_config.research,
        operator_ui=app_config.operator_ui,
    )
    store = SQLiteStore(config.db_path)
    await store.initialize()

    class FakeCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

        async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True):
            return sample_bars[-1]

    engine = TradingEngine(
        config,
        store,
        FakeCandles(),
        PaperExecutionAdapter(
            entry_slippage_bps=config.strategy.entry_slippage_bps,
            exit_slippage_bps=config.strategy.exit_slippage_bps,
            price_tick=config.strategy.price_tick,
            size_step=config.strategy.size_step,
        ),
        clock=lambda: 1712665800000,
    )
    result = await engine.set_runtime_mode(RuntimeMode.SHADOW)

    assert result["changed"] is True
    assert result["previous_mode"] == "paper"
    assert result["mode"] == "shadow"
    assert engine.config.runtime_mode == RuntimeMode.SHADOW
    assert engine.execution_adapter.mode == RuntimeMode.SHADOW


@pytest.mark.asyncio
async def test_engine_runtime_mode_switch_is_blocked_when_position_open(app_config, sample_bars, tmp_path) -> None:
    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "switch_mode_blocked.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=app_config.research,
        operator_ui=app_config.operator_ui,
    )
    store = SQLiteStore(config.db_path)
    await store.initialize()

    class FakeCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

        async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True):
            return sample_bars[-1]

    engine = TradingEngine(
        config,
        store,
        FakeCandles(),
        PaperExecutionAdapter(
            entry_slippage_bps=config.strategy.entry_slippage_bps,
            exit_slippage_bps=config.strategy.exit_slippage_bps,
            price_tick=config.strategy.price_tick,
            size_step=config.strategy.size_step,
        ),
        clock=lambda: 1712665800000,
    )
    await store.upsert_position_state(
        PositionState(
            symbol="BTCUSDT",
            status=TradeStatus.OPEN,
            direction=SignalDirection.LONG,
            position_size=Decimal("0.001"),
            entry_price=Decimal("70000"),
            last_updated_ms=1712665800000,
        )
    )

    with pytest.raises(RuntimeError, match="cannot switch runtime mode while a position is open"):
        await engine.set_runtime_mode(RuntimeMode.SHADOW)


@pytest.mark.asyncio
async def test_engine_live_mode_switch_reloads_hyperliquid_config_from_env(app_config, sample_bars, tmp_path, monkeypatch) -> None:
    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "switch_mode_live_reload.sqlite3",
        webhook=app_config.webhook,
        strategy=replace(
            app_config.strategy,
            max_daily_loss_quote=Decimal("25"),
            max_open_risk_notional=Decimal("100"),
        ),
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=app_config.research,
        operator_ui=app_config.operator_ui,
    )
    store = SQLiteStore(config.db_path)
    await store.initialize()

    class FakeCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

        async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True):
            return sample_bars[-1]

    reloaded_hyperliquid = replace(
        app_config.hyperliquid,
        base_url="https://api.hyperliquid-testnet.xyz",
        enable_live=True,
        account_address="0x1111111111111111111111111111111111111111",
        private_key="0x2222222222222222222222222222222222222222222222222222222222222222",
    )
    reloaded_config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=config.db_path,
        webhook=config.webhook,
        strategy=replace(
            config.strategy,
            max_daily_loss_quote=Decimal("25"),
            max_open_risk_notional=Decimal("100"),
        ),
        binance=config.binance,
        hyperliquid=reloaded_hyperliquid,
        research=config.research,
        operator_ui=config.operator_ui,
    )
    monkeypatch.setattr("tradingbotsuite.core.engine.AppConfig.from_env", classmethod(lambda cls: reloaded_config))

    class FakeLiveExecutionAdapter:
        mode = RuntimeMode.LIVE

        async def shutdown(self):
            return None

        async def start_user_streams(self):
            return None

        async def preflight_account(self):
            return {"ok": True}

        def get_stream_status(self):
            return {"enabled": False, "started": False}

    def fake_make_execution_adapter(mode: RuntimeMode, **kwargs):
        if mode == RuntimeMode.LIVE:
            return FakeLiveExecutionAdapter()
        raise AssertionError(f"unexpected mode: {mode}")

    monkeypatch.setattr("tradingbotsuite.core.engine.make_execution_adapter", fake_make_execution_adapter)

    engine = TradingEngine(
        config,
        store,
        FakeCandles(),
        PaperExecutionAdapter(
            entry_slippage_bps=config.strategy.entry_slippage_bps,
            exit_slippage_bps=config.strategy.exit_slippage_bps,
            price_tick=config.strategy.price_tick,
            size_step=config.strategy.size_step,
        ),
        clock=lambda: 1712665800000,
    )
    result = await engine.set_runtime_mode(RuntimeMode.LIVE)

    assert result["mode"] == "live"
    assert engine.config.hyperliquid.base_url == "https://api.hyperliquid-testnet.xyz"
    assert engine.config.hyperliquid.account_address == "0x1111111111111111111111111111111111111111"


@pytest.mark.asyncio
async def test_live_filled_report_without_reconcile_does_not_persist_open_position(app_config, sample_bars, tmp_path) -> None:
    live_config = AppConfig(
        runtime_mode=RuntimeMode.LIVE,
        db_path=tmp_path / "live_false_fill.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=HyperliquidConfig(account_address="0xmain", enable_live=False),
    )
    store = SQLiteStore(live_config.db_path)
    await store.initialize()

    class FakeCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

        async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True):
            return sample_bars[-1]

    class FakeExchange:
        def __init__(self):
            self.calls = []

        def _slippage_price(self, name: str, is_buy: bool, slippage: float, px: float | None = None) -> float:
            assert px is not None
            return px

        def market_open(self, *args):
            self.calls.append(("market_open", args))
            return {"response": {"data": {"statuses": [{"filled": {"oid": 12345, "avgPx": "70010", "totalSz": "0.01"}}]}}}

        def market_close(self, *args):
            self.calls.append(("market_close", args))
            return {"response": {"data": {"statuses": [{"filled": {"oid": 12346, "avgPx": "70000", "totalSz": "0.01"}}]}}}

        def bulk_cancel_by_cloid(self, *args):
            self.calls.append(("bulk_cancel_by_cloid", args))
            return {"response": {"data": {"statuses": [{"success": True}]}}}

        def order(self, *args):
            self.calls.append(("order", args))
            return {"response": {"data": {"statuses": [{"resting": {"oid": 12347}}]}}}

    class FlatInfo:
        def user_role(self, address):
            return {"role": "user"}

        def spot_user_state(self, address):
            return {"balances": [{"coin": "USDC", "total": "10.0"}]}

        def query_user_abstraction_state(self, address):
            return "unifiedAccount"

        def user_state(self, address, dex=""):
            return {"assetPositions": []}

        def open_orders(self, address, dex=""):
            return []

    adapter = HyperliquidExecutionAdapter(live_config.hyperliquid, exchange_client=FakeExchange(), info_client=FlatInfo())
    engine = TradingEngine(live_config, store, FakeCandles(), adapter, clock=lambda: 1712665800000)
    await engine.initialize()
    _, reports, _ = await engine.handle_signal(
        SignalIntent(
            signal_id="live-false-fill",
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            signal_bar_time_ms=1712662200000,
            received_time_ms=1712665800000,
            raw_payload={},
        )
    )
    state = await store.get_position_state("BTCUSDT")
    safety = await store.get_safety_status()
    assert reports
    assert state is None
    assert safety is not None
    assert safety.reason == SafeModeReason.ORDER_TIMEOUT


@pytest.mark.asyncio
async def test_hyperliquid_adapter_fixture_contract() -> None:
    class FakeExchange:
        def __init__(self):
            self.calls = []

        def _slippage_price(self, name: str, is_buy: bool, slippage: float, px: float | None = None) -> float:
            assert px is not None
            return px

        def market_open(self, *args):
            self.calls.append(("market_open", args))
            return {"response": {"data": {"statuses": [{"filled": {"oid": 12345}}]}}}

        def market_close(self, *args):
            self.calls.append(("market_close", args))
            return {"response": {"data": {"statuses": [{"filled": {"oid": 12346}}]}}}

        def bulk_cancel_by_cloid(self, *args):
            self.calls.append(("bulk_cancel_by_cloid", args))
            return {"response": {"data": {"statuses": [{"success": True}]}}}

        def order(self, *args):
            self.calls.append(("order", args))
            return {"response": {"data": {"statuses": [{"resting": {"oid": 12347}}]}}}

    adapter = HyperliquidExecutionAdapter(HyperliquidConfig(enable_live=False), exchange_client=FakeExchange(), info_client=object())
    packet = DecisionPacket(
        signal=SignalIntent(
            signal_id="l1",
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            signal_bar_time_ms=1712662200000,
            received_time_ms=1712665800000,
            raw_payload={},
        ),
        mode=RuntimeMode.LIVE,
        action=DecisionAction.ACCEPT,
        accepted=True,
        intended_size=Decimal("0.01"),
        entry_reference_price=Decimal("70000"),
        atr=Decimal("250"),
        tp_price=Decimal("70375"),
        sl_price=Decimal("69750"),
        vertical_barrier_time_ms=1712683800000,
    )
    intents = build_open_intents(packet) + build_protective_intents(packet)
    reports = await adapter.execute(intents)
    assert reports[0].status in {ExecutionStatus.FILLED, ExecutionStatus.ACKED}
    assert len(reports) == 3


@pytest.mark.asyncio
async def test_hyperliquid_trigger_error_is_rejected() -> None:
    class FakeExchange:
        def _slippage_price(self, name: str, is_buy: bool, slippage: float, px: float | None = None) -> float:
            assert px is not None
            return px

        def order(self, *args):
            return {"response": {"data": {"statuses": [{"error": "Invalid TP/SL price. asset=3"}]}}}

    adapter = HyperliquidExecutionAdapter(HyperliquidConfig(enable_live=False), exchange_client=FakeExchange(), info_client=object())
    reports = await adapter.execute(
        [
            ExecutionIntent(
                intent_id="tp-err",
                mode=RuntimeMode.LIVE,
                intent_type=ExecutionIntentType.PROTECTIVE_TP,
                symbol="BTCUSDT",
                direction=SignalDirection.LONG,
                size=Decimal("0.01"),
                trigger_price=Decimal("70375"),
                cloid="0x11111111111111111111111111111111",
                reduce_only=True,
            )
        ]
    )
    assert reports[0].status == ExecutionStatus.REJECTED
    assert "Invalid TP/SL price" in (reports[0].message or "")


@pytest.mark.asyncio
async def test_hyperliquid_protective_orders_round_trigger_price_before_submit() -> None:
    class FakeExchange:
        def __init__(self):
            self.calls = []

        def _slippage_price(self, name: str, is_buy: bool, slippage: float, px: float | None = None) -> float:
            assert px is not None
            return px

        def order(self, *args):
            self.calls.append(args)
            return {"response": {"data": {"statuses": [{"resting": {"oid": 12347}}]}}}

    class FakeInfo:
        coin_to_asset = {"BTC": 3}
        asset_to_sz_decimals = {3: 5}

    exchange = FakeExchange()
    adapter = HyperliquidExecutionAdapter(
        HyperliquidConfig(enable_live=False, account_address="0xabc"),
        exchange_client=exchange,
        info_client=FakeInfo(),
    )
    reports = await adapter.execute(
        [
            ExecutionIntent(
                intent_id="tp-round",
                mode=RuntimeMode.LIVE,
                intent_type=ExecutionIntentType.PROTECTIVE_TP,
                symbol="BTCUSDT",
                direction=SignalDirection.LONG,
                size=Decimal("0.001239"),
                trigger_price=Decimal("72715.65"),
                cloid="0x22222222222222222222222222222222",
                reduce_only=True,
            )
        ]
    )

    order_call = exchange.calls[0]
    assert reports[0].status == ExecutionStatus.ACKED
    assert order_call[2] == 0.00123
    assert order_call[3] == 72715.0
    assert order_call[4]["trigger"]["triggerPx"] == 72715.0


@pytest.mark.asyncio
async def test_hyperliquid_benign_cancel_error_maps_to_canceled() -> None:
    class FakeExchange:
        def bulk_cancel_by_cloid(self, *args):
            return {
                "response": {
                    "data": {
                        "statuses": [
                            {"error": "Order was never placed, already canceled, or filled. asset=3"}
                        ]
                    }
                }
            }

    adapter = HyperliquidExecutionAdapter(HyperliquidConfig(enable_live=False), exchange_client=FakeExchange(), info_client=object())
    reports = await adapter.execute(
        [
            ExecutionIntent(
                intent_id="cancel-1",
                mode=RuntimeMode.LIVE,
                intent_type=ExecutionIntentType.CANCEL,
                symbol="BTCUSDT",
                size=Decimal("0"),
                cloid="0x33333333333333333333333333333333",
                reduce_only=True,
            )
        ]
    )

    assert reports[0].status == ExecutionStatus.CANCELED


@pytest.mark.asyncio
async def test_hyperliquid_cancel_falls_back_to_oid_when_cloid_cancel_does_not_remove_open_order() -> None:
    class FakeExchange:
        def __init__(self):
            self.calls = []

        def bulk_cancel_by_cloid(self, requests):
            self.calls.append(("bulk_cancel_by_cloid", requests))
            return {"response": {"data": {"statuses": [{"success": True}]}}}

        def bulk_cancel(self, requests):
            self.calls.append(("bulk_cancel", requests))
            return {"response": {"data": {"statuses": [{"success": True}]}}}

    class FakeInfo:
        def __init__(self):
            self.query_count = 0

        def user_role(self, address):
            return {"role": "user"}

        def post(self, url_path, payload):
            self.query_count += 1
            oid = payload.get("oid")
            if oid == "0x33333333333333333333333333333333":
                return {
                    "status": "order",
                    "order": {
                        "order": {
                            "coin": "BTC",
                            "oid": 12345,
                            "cloid": "0x33333333333333333333333333333333",
                        },
                        "status": "open",
                        "statusTimestamp": 1712665800000,
                    },
                }
            if oid == 12345:
                return {"status": "unknownOid"}
            raise AssertionError(f"unexpected oid query: {oid}")

        def frontend_open_orders(self, address, dex=""):
            return []

    exchange = FakeExchange()
    adapter = HyperliquidExecutionAdapter(
        HyperliquidConfig(enable_live=False, account_address="0xabc"),
        exchange_client=exchange,
        info_client=FakeInfo(),
    )
    reports = await adapter.execute(
        [
            ExecutionIntent(
                intent_id="cancel-1",
                mode=RuntimeMode.LIVE,
                intent_type=ExecutionIntentType.CANCEL,
                symbol="BTCUSDT",
                size=Decimal("0"),
                cloid="0x33333333333333333333333333333333",
                reduce_only=True,
            )
        ]
    )

    assert reports[0].status == ExecutionStatus.CANCELED
    assert reports[0].exchange_order_id == "12345"
    assert [call[0] for call in exchange.calls] == ["bulk_cancel_by_cloid", "bulk_cancel"]


@pytest.mark.asyncio
async def test_hyperliquid_ignores_snapshot_fills_in_event_queue() -> None:
    adapter = HyperliquidExecutionAdapter(HyperliquidConfig(enable_live=False), exchange_client=object(), info_client=object())
    adapter._handle_ws_message(
        {
            "channel": "userFills",
            "data": {
                "isSnapshot": True,
                "user": "0xabc",
                "fills": [
                    {
                        "coin": "BTC",
                        "px": "70375",
                        "sz": "0.01",
                        "side": "A",
                        "time": 1712666800000,
                        "dir": "Close Long",
                        "closedPnl": "3.75",
                        "hash": "0xsnapshot",
                        "oid": 456,
                        "tid": 777,
                    }
                ],
            },
        }
    )

    events = await adapter.drain_execution_events()

    assert events == []


@pytest.mark.asyncio
async def test_hyperliquid_stream_dedupes_duplicate_fills_across_channels() -> None:
    adapter = HyperliquidExecutionAdapter(HyperliquidConfig(enable_live=False), exchange_client=object(), info_client=object())
    tracked_intent = ExecutionIntent(
        intent_id="tp-1",
        mode=RuntimeMode.LIVE,
        intent_type=ExecutionIntentType.PROTECTIVE_TP,
        symbol="BTCUSDT",
        size=Decimal("0.01"),
        cloid="0xtp",
        reduce_only=True,
    )
    tracked_report = ExecutionReport(
        intent_id="tp-1",
        intent_type=ExecutionIntentType.PROTECTIVE_TP,
        status=ExecutionStatus.ACKED,
        symbol="BTCUSDT",
        exchange_order_id="456",
        cloid="0xtp",
    )
    adapter._track_execution_report(tracked_intent, tracked_report)
    fill_payload = {
        "coin": "BTC",
        "px": "70375",
        "sz": "0.01",
        "side": "A",
        "time": 1712666800000,
        "startPosition": "0.01",
        "dir": "Close Long",
        "closedPnl": "3.75",
        "hash": "0xfill",
        "oid": 456,
        "crossed": True,
        "fee": "-0.1",
        "tid": 777,
        "feeToken": "USDC",
    }

    adapter._handle_ws_message({"channel": "userFills", "data": {"isSnapshot": False, "user": "0xabc", "fills": [fill_payload]}})
    adapter._handle_ws_message({"channel": "user", "data": {"fills": [fill_payload]}})

    events = await adapter.drain_execution_events()
    fill_events = [event for event in events if event["event_type"] == "fill"]
    assert len(fill_events) == 1
    assert fill_events[0]["tracked_intent_type"] == ExecutionIntentType.PROTECTIVE_TP


@pytest.mark.asyncio
async def test_stream_fill_reconcile_closes_position_with_take_profit(app_config, sample_bars, tmp_path) -> None:
    live_config = AppConfig(
        runtime_mode=RuntimeMode.LIVE,
        db_path=tmp_path / "stream_reconcile.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=HyperliquidConfig(enable_live=False),
    )
    store = SQLiteStore(live_config.db_path)
    await store.initialize()
    await store.upsert_position_state(
        PositionState(
            symbol="BTCUSDT",
            status=TradeStatus.OPEN,
            direction=SignalDirection.LONG,
            position_size=Decimal("0.01"),
            entry_price=Decimal("70000"),
            entry_time_ms=1712665800000,
            entry_bar_time_ms=1712662200000,
            entry_atr=Decimal("250"),
            tp_price=Decimal("70375"),
            sl_price=Decimal("69750"),
            vertical_barrier_time_ms=1712683800000,
            entry_order_cloid="0xentry",
            tp_order_cloid="0xtp",
            sl_order_cloid="0xsl",
            last_updated_ms=1712665800000,
        )
    )

    class FakeCandles:
        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            return sample_bars[-limit:]

        async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True):
            return sample_bars[-1]

    class ReconcileAwareAdapter(HyperliquidExecutionAdapter):
        async def reconcile(self, symbol: str) -> dict[str, object]:
            return {"symbol": symbol, "position_size": "0", "side": None, "open_order_cloids": []}

    adapter = ReconcileAwareAdapter(live_config.hyperliquid, exchange_client=object(), info_client=object())
    tracked_intent = ExecutionIntent(
        intent_id="tp-1",
        mode=RuntimeMode.LIVE,
        intent_type=ExecutionIntentType.PROTECTIVE_TP,
        symbol="BTCUSDT",
        size=Decimal("0.01"),
        cloid="0xtp",
        reduce_only=True,
    )
    tracked_report = ExecutionReport(
        intent_id="tp-1",
        intent_type=ExecutionIntentType.PROTECTIVE_TP,
        status=ExecutionStatus.ACKED,
        symbol="BTCUSDT",
        exchange_order_id="456",
        cloid="0xtp",
    )
    adapter._track_execution_report(tracked_intent, tracked_report)
    adapter._handle_ws_message(
        {
            "channel": "userFills",
            "data": {
                "isSnapshot": False,
                "user": "0xabc",
                "fills": [
                    {
                        "coin": "BTC",
                        "px": "70375",
                        "sz": "0.01",
                        "side": "A",
                        "time": 1712666800000,
                        "startPosition": "0.01",
                        "dir": "Close Long",
                        "closedPnl": "3.75",
                        "hash": "0xfill",
                        "oid": 456,
                        "crossed": True,
                        "fee": "-0.1",
                        "tid": 777,
                        "feeToken": "USDC",
                    }
                ],
            },
        }
    )

    engine = TradingEngine(live_config, store, FakeCandles(), adapter, clock=lambda: 1712666801000)
    await engine.initialize()
    events = await engine.sync_execution_events("BTCUSDT")
    state = await store.get_position_state("BTCUSDT")
    assert events
    assert state is not None
    assert state.status == TradeStatus.FLAT
    assert state.last_exit_reason == ExitReason.TAKE_PROFIT
