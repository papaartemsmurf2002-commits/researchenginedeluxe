from __future__ import annotations

import asyncio
import os
import re
import time
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient

from tradingbotsuite.config import AppConfig, OperatorUIConfig
from tradingbotsuite.core.models import PositionState, RuntimeMode, SignalDirection, TradeStatus
from tradingbotsuite.operator_commands import execute_manual_signal
from tradingbotsuite.web.app import create_app


class FakeCandles:
    def __init__(self, bars):
        self.bars = bars

    async def fetch_recent_closed_bars(self, symbol: str, limit: int):
        return self.bars[-limit:]

    async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True):
        return self.bars[-1]

    async def start_market_streams(self, symbols: list[str]):
        return None

    def get_stream_status(self):
        return {"enabled": False, "started": False}

    async def close(self):
        return None


class FakeLiveAdapter:
    mode = RuntimeMode.LIVE

    async def start_user_streams(self):
        return None

    async def preflight_account(self):
        return {"ok": True}

    async def shutdown(self):
        return None

    def get_stream_status(self):
        return {"enabled": False, "started": False}

    async def drain_execution_events(self):
        return []

    async def execute(self, intents):
        return []

    async def reconcile(self, symbol: str):
        return {"symbol": symbol, "position_size": "0", "side": None, "open_order_cloids": []}

    async def get_market_snapshot(self, symbol: str):
        return {"mid_price": "70000"}


def _write_signal_export(path: Path, sample_bars) -> Path:
    lines = ["time,open,high,low,close,Buy,Sell,StopBuy,StopSell,Shapes,Chars"]
    signal_rows = {70: ("65000", ""), 88: ("", "65500"), 104: ("64800", ""), 122: ("", "65200")}
    base_bars = list(sample_bars)
    synthetic_rows = []
    for index in range(140):
        template = base_bars[index % len(base_bars)]
        cycle = index // len(base_bars)
        drift = Decimal(cycle) * Decimal("25")
        time_ms = int(base_bars[0].time_ms + index * 15 * 60 * 1000)
        synthetic_rows.append(
            {
                "time_ms": time_ms,
                "open": template.open + drift,
                "high": template.high + drift,
                "low": template.low + drift,
                "close": template.close + drift,
            }
        )
    for index, bar in enumerate(synthetic_rows):
        buy, sell = signal_rows.get(index, ("", ""))
        lines.append(
            ",".join(
                [
                    str(int(bar["time_ms"])),
                    str(bar["open"]),
                    str(bar["high"]),
                    str(bar["low"]),
                    str(bar["close"]),
                    buy,
                    sell,
                    "",
                    "",
                    "",
                    "",
                ]
            )
        )
    export_path = path / "signal_export.csv"
    export_path.write_text("\n".join(lines), encoding="utf-8")
    return export_path


def _login(client: TestClient, secret: str) -> str:
    response = client.post("/ui/login", data={"password": secret}, follow_redirects=True)
    assert response.status_code == 200
    match = re.search(r'csrfToken:\s*"([^"]+)"', response.text)
    assert match is not None
    return match.group(1)


def _operator_config(app_config: AppConfig, *, mode: RuntimeMode = RuntimeMode.PAPER) -> AppConfig:
    return AppConfig(
        runtime_mode=mode,
        db_path=app_config.db_path,
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=app_config.research,
        operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
    )


def test_operator_ui_disabled_returns_404(app_config, sample_bars) -> None:
    app = create_app(app_config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    with TestClient(app) as client:
        response = client.get("/ui")
    assert response.status_code == 404


def test_operator_ui_requires_auth_and_csrf(app_config, sample_bars) -> None:
    config = _operator_config(app_config)
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    with TestClient(app) as client:
        unauth = client.post("/api/operator/commands/manual-signal", json={"symbol": "BTCUSDT", "direction": "long"})
        assert unauth.status_code == 401

        csrf_token = _login(client, "operator-secret")
        missing_csrf = client.post("/api/operator/commands/manual-signal", json={"symbol": "BTCUSDT", "direction": "long"})
        assert missing_csrf.status_code == 403

        ok = client.post(
            "/api/operator/commands/manual-signal",
            json={"symbol": "BTCUSDT", "direction": "long"},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert ok.status_code == 200
        payload = ok.json()
        assert payload["success"] is True
        assert payload["result"]["packet"]["signal"]["direction"] == "long"


def test_operator_snapshot_matches_engine_snapshot(app_config, sample_bars) -> None:
    config = _operator_config(app_config)
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    with TestClient(app) as client:
        _login(client, "operator-secret")
        api_snapshot = client.get("/api/operator/snapshot?symbol=BTCUSDT").json()
        direct_snapshot = asyncio.run(app.state.engine.collect_system_snapshot("BTCUSDT"))
    assert api_snapshot["position"] == direct_snapshot["position"]
    assert api_snapshot["market_data_health"]["healthy"] == direct_snapshot["market_data_health"]["healthy"]
    assert api_snapshot["market_data_health"]["latest_bar_time_ms"] == direct_snapshot["market_data_health"]["latest_bar_time_ms"]
    assert api_snapshot["execution_health"]["healthy"] == direct_snapshot["execution_health"]["healthy"]


def test_operator_snapshot_includes_microstructure_prediction(app_config, sample_bars) -> None:
    config = _operator_config(app_config)
    app = create_app(config)

    class PredictableCandles(FakeCandles):
        async def get_microstructure_snapshot(self, symbol: str, *, windows_seconds, now_ms):
            return {
                "symbol": symbol,
                "healthy": True,
                "entry_ready": True,
                "trade_flow_available": True,
                "top_of_book_available": True,
                "queue_imbalance_available": True,
                "depth_depletion_available": True,
                "depth_healthy": True,
                "windows": {"20": {"signed_ratio": "0.55", "sqrt_signed_ratio": "0.42", "flow_price_alignment_bps": "2.0"}},
                "top_of_book_imbalance": "0.35",
                "queue_imbalance_l1": "0.1",
                "queue_imbalance_l5": "0.2",
                "queue_imbalance_l10": "0.3",
                "depth_depletion": {"bid_l5": "0.1", "ask_l5": "0.4"},
                "spread_bps": "0.5",
            }

    app.state.engine.candle_client = PredictableCandles(sample_bars)
    with TestClient(app) as client:
        _login(client, "operator-secret")
        payload = client.get("/api/operator/snapshot?symbol=BTCUSDT").json()

    prediction = payload["microstructure_prediction"]
    assert prediction["status"] == "scored"
    assert prediction["direction"] == "up"
    assert prediction["calibrated"] is False
    assert Decimal(prediction["probabilities"]["up"]) > Decimal(prediction["probabilities"]["down"])


def test_operator_manual_signal_matches_direct_command_shape(app_config, sample_bars, tmp_path) -> None:
    browser_config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "operator_ui_browser.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=app_config.research,
        operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
    )

    app = create_app(browser_config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    app.state.engine.clock = lambda: 1712665800000
    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        browser_response = client.post(
            "/api/operator/commands/manual-signal",
            json={"symbol": "BTCUSDT", "direction": "short"},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert browser_response.status_code == 200
        browser_packet = browser_response.json()["result"]["packet"]

    direct_config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "operator_ui_direct.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=app_config.research,
        operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
    )
    second_app = create_app(direct_config)
    second_app.state.engine.candle_client = FakeCandles(sample_bars)
    second_app.state.engine.clock = lambda: 1712665800000
    with TestClient(second_app):
        direct_result = asyncio.run(execute_manual_signal(second_app.state.engine, symbol="BTCUSDT", direction=SignalDirection.SHORT))
    direct_packet = direct_result["packet"]

    assert browser_packet["action"] == direct_packet["action"]
    assert browser_packet["accepted"] == direct_packet["accepted"]
    assert browser_packet["signal"]["direction"] == direct_packet["signal"]["direction"]
    assert browser_packet["feature_snapshot"]["latest_bar_time_ms"] == direct_packet["feature_snapshot"]["latest_bar_time_ms"]


def test_operator_manual_signal_forwards_testnet_protection_toggle(app_config, sample_bars, monkeypatch) -> None:
    config = _operator_config(app_config, mode=RuntimeMode.LIVE)
    config = AppConfig(
        runtime_mode=config.runtime_mode,
        db_path=config.db_path,
        webhook=config.webhook,
        strategy=config.strategy,
        binance=config.binance,
        hyperliquid=replace(config.hyperliquid, base_url="https://api.hyperliquid-testnet.xyz"),
        research=config.research,
        operator_ui=config.operator_ui,
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)

    captured: dict[str, object] = {}

    async def fake_execute_manual_signal(engine, *, symbol: str, direction: SignalDirection, testnet_short_lived_protections: bool = False):
        captured["symbol"] = symbol
        captured["direction"] = direction
        captured["testnet_short_lived_protections"] = testnet_short_lived_protections
        return {
            "signal": {"signal_id": "manual-test"},
            "packet": {"signal": {"direction": str(direction)}, "action": "accept", "accepted": True},
            "reports": [],
            "ticket": {"action_type": "accept"},
            "testnet_short_lived_protections": {"requested": testnet_short_lived_protections, "reason": "cleanup_scheduled"},
        }

    monkeypatch.setattr("tradingbotsuite.operator_console.execute_manual_signal", fake_execute_manual_signal)
    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        response = client.post(
            "/api/operator/commands/manual-signal",
            json={"symbol": "BTCUSDT", "direction": "long", "testnet_short_lived_protections": True},
            headers={"X-CSRF-Token": csrf_token},
        )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert captured["symbol"] == "BTCUSDT"
    assert captured["direction"] == SignalDirection.LONG
    assert captured["testnet_short_lived_protections"] is True


def test_operator_mode_switch_changes_runtime_mode(app_config, sample_bars) -> None:
    config = _operator_config(app_config, mode=RuntimeMode.PAPER)
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)

    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        response = client.post(
            "/api/operator/commands/set-mode",
            json={"mode": "shadow"},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        assert payload["result"]["mode"] == "shadow"
        control_page = client.get("/ui/control")

    assert app.state.engine.config.runtime_mode == RuntimeMode.SHADOW
    assert "shadow" in control_page.text.lower()


def test_operator_mode_switch_blocked_when_position_open(app_config, sample_bars) -> None:
    config = _operator_config(app_config, mode=RuntimeMode.PAPER)
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)

    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        asyncio.run(
            app.state.engine.store.upsert_position_state(
                PositionState(
                    symbol="BTCUSDT",
                    status=TradeStatus.OPEN,
                    direction=SignalDirection.LONG,
                    position_size=Decimal("0.001"),
                    entry_price=Decimal("70000"),
                    last_updated_ms=1712665800000,
                )
            )
        )
        response = client.post(
            "/api/operator/commands/set-mode",
            json={"mode": "shadow"},
            headers={"X-CSRF-Token": csrf_token},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert "cannot switch runtime mode while a position is open" in payload["result"]["error"]


def test_operator_feed_is_deterministic(app_config, sample_bars, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TBS_SERVER_MONITOR_POLL_SECONDS", "3600")
    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "operator_feed.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=app_config.research,
        operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    app.state.engine.clock = lambda: 1712665800000
    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        client.post(
            "/api/operator/commands/manual-signal",
            json={"symbol": "BTCUSDT", "direction": "long"},
            headers={"X-CSRF-Token": csrf_token},
        )
        time.sleep(0.4)
        first = client.get("/api/operator/feed?limit=20").json()
        second = client.get("/api/operator/feed?limit=20").json()
    assert [item["id"] for item in first["items"]] == [item["id"] for item in second["items"]]


def test_operator_feed_can_hide_health_and_execution_metrics(app_config, sample_bars, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TBS_SERVER_MONITOR_POLL_SECONDS", "3600")
    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "operator_feed_filters.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=app_config.research,
        operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    app.state.engine.clock = lambda: 1712665800000
    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        asyncio.run(
            app.state.engine.store.append_health_event(
                event_id="health-1",
                symbol="BTCUSDT",
                scope="market_data",
                state="degraded",
                reason_code="depth_degraded",
                event_time_ms=1712665800000,
                summary="Market data degraded but entry-capable",
                recommended_action="wait",
                payload={},
            )
        )
        asyncio.run(
            app.state.engine.store.append_execution_metric(
                metric_id="metric-1",
                signal_id=None,
                symbol="BTCUSDT",
                metric_type="market_health",
                recorded_time_ms=1712665800001,
                payload={"healthy": False},
            )
        )
        client.post(
            "/api/operator/commands/manual-signal",
            json={"symbol": "BTCUSDT", "direction": "long"},
            headers={"X-CSRF-Token": csrf_token},
        )
        filtered = client.get(
            "/api/operator/feed?limit=50&include_health_events=false&include_execution_metrics=false"
        ).json()

    kinds = {item["kind"] for item in filtered["items"]}
    assert "health_event" not in kinds
    assert "execution_metric" not in kinds
    assert "operator_command" in kinds


def test_operator_research_job_blocked_for_live_open_position(app_config, sample_bars, tmp_path) -> None:
    config = AppConfig(
        runtime_mode=RuntimeMode.LIVE,
        db_path=tmp_path / "operator_live.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=app_config.research,
        operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    app.state.engine.execution_adapter = FakeLiveAdapter()
    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        asyncio.run(
            app.state.engine.store.upsert_position_state(
                PositionState(
                    symbol="BTCUSDT",
                    status=TradeStatus.OPEN,
                    direction=SignalDirection.LONG,
                    position_size=Decimal("0.001"),
                    entry_price=Decimal("70000"),
                    last_updated_ms=1712665800000,
                )
            )
        )
        response = client.post(
            "/api/operator/research/jobs/build-dataset",
            json={},
            headers={"X-CSRF-Token": csrf_token},
        )
    assert response.status_code == 409
    assert "live position is open" in response.json()["detail"]


def test_operator_snapshot_handles_microstructure_exception(app_config, sample_bars) -> None:
    config = _operator_config(app_config)
    app = create_app(config)

    class FailingCandles(FakeCandles):
        async def get_microstructure_snapshot(self, symbol: str, *, windows_seconds, now_ms):
            raise RuntimeError("depth bootstrap rate limited")

    app.state.engine.candle_client = FailingCandles(sample_bars)
    with TestClient(app) as client:
        _login(client, "operator-secret")
        response = client.get("/api/operator/snapshot?symbol=BTCUSDT")
    assert response.status_code == 200
    payload = response.json()
    assert payload["microstructure"]["healthy"] is False
    assert payload["microstructure"]["reasons"] == ["snapshot_error"]


def test_operator_guides_page_includes_embedded_docs(app_config, sample_bars) -> None:
    config = _operator_config(app_config)
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    with TestClient(app) as client:
        _login(client, "operator-secret")
        response = client.get("/ui/guides")
    assert response.status_code == 200
    assert "Operator Guide" in response.text
    assert "Microstructure Reliability" in response.text


def test_operator_guides_api_returns_docs(app_config, sample_bars) -> None:
    config = _operator_config(app_config)
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    with TestClient(app) as client:
        _login(client, "operator-secret")
        response = client.get("/api/operator/guides")
    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["items"]]
    assert "Operator Guide" in titles


def test_operator_predictions_page_renders(app_config, sample_bars) -> None:
    config = _operator_config(app_config)
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    with TestClient(app) as client:
        _login(client, "operator-secret")
        page = client.get("/ui/predictions")

    assert page.status_code == 200
    assert "Live Predictions" in page.text
    assert "Microstructure-derived short-horizon pressure" in page.text


def test_server_monitor_auto_supervises_open_position(app_config, sample_bars, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TBS_SERVER_MONITOR_POLL_SECONDS", "0.25")
    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "operator_auto_supervise.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=app_config.research,
        operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
    )
    app = create_app(config)

    class ExitHitCandles(FakeCandles):
        async def get_microstructure_snapshot(self, symbol: str, *, windows_seconds, now_ms):
            return {
                "healthy": True,
                "mid_price": "72890",
                "top_of_book_imbalance": "0.1",
                "queue_imbalance_l1": "0.1",
                "queue_imbalance_l5": "0.1",
                "queue_imbalance_l10": "0.1",
                "windows": {"20": {"signed_ratio": "0.1"}},
            }

        async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True):
            return type(self.bars[-1])(
                time_ms=self.bars[-1].time_ms,
                open=self.bars[-1].open,
                high=self.bars[-1].high,
                low=Decimal("72800"),
                close=Decimal("72890"),
                volume=self.bars[-1].volume,
            )

    app.state.engine.candle_client = ExitHitCandles(sample_bars)
    with TestClient(app):
        asyncio.run(
            app.state.engine.store.upsert_position_state(
                PositionState(
                    symbol="BTCUSDT",
                    status=TradeStatus.OPEN,
                    direction=SignalDirection.LONG,
                    position_size=Decimal("0.001"),
                    entry_price=Decimal("73166.8"),
                    entry_time_ms=1712665800000,
                    entry_bar_time_ms=1712662200000,
                    entry_atr=Decimal("256.6"),
                    tp_price=Decimal("73551.7"),
                    sl_price=Decimal("72910.2"),
                    vertical_barrier_time_ms=1712683800000,
                    last_updated_ms=1712665800000,
                )
            )
        )
        time.sleep(0.6)
        position = asyncio.run(app.state.engine.store.get_position_state("BTCUSDT"))
    assert position is not None
    assert position.status == TradeStatus.FLAT
