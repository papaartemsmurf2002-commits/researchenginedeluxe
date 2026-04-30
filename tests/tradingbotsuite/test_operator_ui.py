from __future__ import annotations

import asyncio
import json
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


def _wait_for_job(client: TestClient, job_id: str, *, timeout_seconds: float = 8.0) -> dict[str, object]:
    deadline = time.time() + timeout_seconds
    last_job: dict[str, object] | None = None
    while time.time() < deadline:
        response = client.get(f"/api/operator/research/jobs/{job_id}")
        assert response.status_code == 200
        last_job = response.json()
        if last_job["status"] in {"succeeded", "failed"}:
            return last_job
        time.sleep(0.2)
    raise AssertionError(f"job {job_id} did not finish; last state: {last_job}")


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


def test_operator_artifacts_include_hmm_knn_monitoring_summary(app_config, sample_bars, tmp_path) -> None:
    research_dir = tmp_path / "research"
    artifact_dir = research_dir / "v2-btc-hmm-multi-knn-1"
    artifact_dir.mkdir(parents=True)
    metrics_path = artifact_dir / "walk_forward_metrics.json"
    monitoring_path = artifact_dir / "monitoring_report.json"
    manifest_path = artifact_dir / "artifact_manifest.json"
    metrics_path.write_text(
        json.dumps(
            {
                "research_only": True,
                "promotion_ready": False,
                "comparison": {
                    "hmm_knn_meta_model": {
                        "trade_count": 7,
                        "expectancy_after_cost": 0.12,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    monitoring_path.write_text(
        json.dumps(
            {
                "research_only": True,
                "promotion_ready": False,
                "entropy_no_trade": {"regime_no_trade_rate": 0.25, "posterior_entropy_p95": 0.72},
                "regime_distribution_drift": {"max_drift": 0.18},
                "neighbor_quality": {"neighbor_distance_quality_p05": 0.31},
                "alerts": [{"severity": "warn", "code": "feature_outage", "message": "observe only", "observe_only": True}],
            }
        ),
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(
            {
                "artifact_manifest_version": "v2-hmm-knn-artifact-manifest-1",
                "research_only": True,
                "plan_version": "v2-btc-hmm-multi-knn-1",
                "symbol": "BTCUSDT",
                "row_count": 42,
                "metrics_path": str(metrics_path),
            }
        ),
        encoding="utf-8",
    )
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_ui.sqlite3",
            webhook=app_config.webhook,
            strategy=app_config.strategy,
            binance=app_config.binance,
            hyperliquid=app_config.hyperliquid,
            research=replace(app_config.research, output_dir=research_dir),
            operator_ui=app_config.operator_ui,
        )
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    with TestClient(app) as client:
        _login(client, "operator-secret")
        payload = client.get("/api/operator/research/artifacts").json()

    item = next(artifact for artifact in payload["items"] if artifact["type"] == "hmm_knn_artifact")
    assert item["summary"]["plan_version"] == "v2-btc-hmm-multi-knn-1"
    assert item["summary"]["promotion_ready"] is False
    assert item["summary"]["monitoring_alert_count"] == 1
    assert item["summary"]["monitoring_alert_counts"] == {"warn": 1}
    assert item["summary"]["regime_no_trade_rate"] == 0.25
    assert item["monitoring"]["alerts"][0]["observe_only"] is True


def test_operator_artifacts_include_provider_pipeline_outputs(app_config, sample_bars, tmp_path) -> None:
    research_dir = tmp_path / "research"
    pipeline_dir = research_dir / "v2-btc-hmm-knn-provider-pipeline-1"
    experiment_dir = pipeline_dir / "evidence" / "experiments"
    pipeline_dir.mkdir(parents=True)
    experiment_dir.mkdir(parents=True)
    (pipeline_dir / "data_intake_manifest.json").write_text(
        json.dumps(
            {
                "data_pipeline_manifest_version": "v2-hmm-knn-provider-data-pipeline-1",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "version": "fixture-pipeline",
                "stage_requested": "all",
                "providers": [{"source_name": "binance_vision", "status": "completed"}],
                "stage_status": {"dataset": {"status": "completed"}, "evidence": {"status": "completed"}},
            }
        ),
        encoding="utf-8",
    )
    (pipeline_dir / "data_quality_report.json").write_text(
        json.dumps(
            {
                "data_quality_report_version": "v2-archive-market-data-quality-report-1",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "manifest_count": 2,
                "alerts": [{"severity": "warn", "code": "missing_receive_time"}],
                "gap_count_total": 0,
                "duplicate_count_total": 0,
                "non_promotable_count": 1,
            }
        ),
        encoding="utf-8",
    )
    (pipeline_dir / "market_journal_manifest.json").write_text(
        json.dumps(
            {
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "event_count": 3,
                "event_counts_by_source": {"binance_vision": 3},
                "event_counts_by_symbol": {"BTCUSDT": 3},
                "event_counts_by_family": {"kline": 3},
                "duplicate_hash_count": 0,
                "sequence_gap_count": 0,
            }
        ),
        encoding="utf-8",
    )
    provider_dir = pipeline_dir / "archives" / "BTCUSDT" / "kline" / "15m"
    provider_dir.mkdir(parents=True)
    (provider_dir / "BTCUSDT_kline_15m_fixture.manifest.json").write_text(
        json.dumps(
            {
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "source_name": "binance_vision",
                "symbol": "BTCUSDT",
                "data_family": "kline",
                "interval": "15m",
                "row_count": 3,
                "gap_count": 0,
                "duplicate_count": 0,
                "content_hash": "sha256:fixture",
                "diagnostic_only": True,
            }
        ),
        encoding="utf-8",
    )
    (experiment_dir / "experiment_manifest.json").write_text(
        json.dumps(
            {
                "experiment_manifest_version": "v2-hmm-knn-experiment-manifest-1",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "name": "fixture matrix",
                "overall_status": "passed",
                "effective_workers": 2,
                "promotion_failure_counts": {"research_only_not_live_promotable": 1},
                "research_boundary": {"passed": True},
                "experiments": [{"status": "passed", "metrics_digest": {"promotion_ready": False}}],
            }
        ),
        encoding="utf-8",
    )
    (pipeline_dir / "pipeline_summary.json").write_text(
        json.dumps(
            {
                "pipeline_summary_version": "v2-hmm-knn-provider-data-pipeline-summary-1",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "version": "fixture-pipeline",
                "stage_requested": "all",
                "data_quality": {"alert_count": 1},
                "evidence": {"mode": "experiment_matrix", "status": "passed"},
                "top_failure_reasons": [{"code": "missing_receive_time"}],
                "conclusion": {"status": "inconclusive", "reason": "data-quality alerts require review"},
            }
        ),
        encoding="utf-8",
    )
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_ui.sqlite3",
            webhook=app_config.webhook,
            strategy=app_config.strategy,
            binance=app_config.binance,
            hyperliquid=app_config.hyperliquid,
            research=replace(app_config.research, output_dir=research_dir),
            operator_ui=app_config.operator_ui,
        )
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    with TestClient(app) as client:
        _login(client, "operator-secret")
        payload = client.get("/api/operator/research/artifacts").json()

    by_type = {artifact["type"]: artifact for artifact in payload["items"]}
    assert by_type["research_pipeline"]["summary"]["conclusion_status"] == "inconclusive"
    assert by_type["research_pipeline"]["summary"]["data_quality_alert_count"] == 1
    assert by_type["data_pipeline_intake"]["summary"]["provider_count"] == 1
    assert by_type["data_quality_report"]["summary"]["alert_count"] == 1
    assert by_type["market_journal_manifest"]["summary"]["event_count"] == 3
    assert by_type["market_journal_manifest"]["summary"]["event_counts_by_family"] == {"kline": 3}
    assert by_type["provider_archive_manifest"]["summary"]["source_name"] == "binance_vision"
    assert by_type["provider_archive_manifest"]["summary"]["row_count"] == 3
    assert by_type["hmm_knn_experiment_matrix"]["summary"]["experiment_count"] == 1
    assert by_type["hmm_knn_experiment_matrix"]["summary"]["research_boundary_passed"] is True


def test_operator_research_page_keeps_hmm_knn_monitoring_observe_only(app_config, sample_bars) -> None:
    config = _operator_config(app_config)
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    with TestClient(app) as client:
        _login(client, "operator-secret")
        response = client.get("/ui/research")

    assert response.status_code == 200
    assert "HMM/KNN Monitoring" in response.text
    assert "Provider Pipeline" in response.text
    assert "/api/operator/research/jobs/prepare-hmm-knn-research-data" in response.text
    assert "hmm_knn_artifact" in response.text
    assert "observe_only" in response.text
    assert "/api/operator/commands/" not in response.text
    assert "set-mode" not in response.text
    assert "manual-signal" not in response.text
    assert "smoke-live" not in response.text


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


def test_operator_research_job_blocked_in_live_mode_without_position(app_config, sample_bars, tmp_path) -> None:
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
        response = client.post(
            "/api/operator/research/jobs/build-dataset",
            json={},
            headers={"X-CSRF-Token": csrf_token},
        )
    assert response.status_code == 409
    assert "live mode" in response.json()["detail"]


def test_operator_provider_pipeline_job_defaults_to_intake_and_completes(app_config, sample_bars, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TBS_SERVER_MONITOR_POLL_SECONDS", "3600")
    research_dir = tmp_path / "research"
    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "operator_pipeline.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=replace(app_config.research, output_dir=research_dir),
        operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    spec_path = research_dir / "pipeline_specs" / "pipeline_spec.json"
    spec_path.parent.mkdir(parents=True)
    spec_path.write_text(
        json.dumps(
            {
                "version": "operator-pipeline",
                "asset_scope": ["BTCUSDT"],
                "output_dir": str(research_dir / "operator-pipeline"),
                "providers": [],
                "dataset_stage": {"enabled": False},
                "evidence_stage": {"enabled": False},
            }
        ),
        encoding="utf-8",
    )
    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        response = client.post(
            "/api/operator/research/jobs/prepare-hmm-knn-research-data",
            json={"spec_path": str(spec_path)},
            headers={"X-CSRF-Token": csrf_token},
        )
        job = _wait_for_job(client, response.json()["job_id"])
        jobs = client.get("/api/operator/research/jobs").json()["items"]

    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    pipeline_job = next(job for job in jobs if job["job_type"] == "prepare-hmm-knn-research-data")
    assert pipeline_job["request"]["spec_path"] == str(spec_path)
    assert pipeline_job["request"]["stage"] == "intake"
    assert job["status"] == "succeeded"
    assert Path(str(job["result"]["data_intake_manifest_path"])).exists()
    assert Path(str(job["result"]["pipeline_summary_path"])).exists()


def test_operator_provider_pipeline_rejects_unallowlisted_spec_path(app_config, sample_bars, tmp_path) -> None:
    research_dir = tmp_path / "research"
    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "operator_pipeline_reject.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=replace(app_config.research, output_dir=research_dir),
        operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    spec_path = tmp_path / "outside_specs" / "pipeline_spec.json"
    spec_path.parent.mkdir(parents=True)
    spec_path.write_text(
        json.dumps(
            {
                "version": "operator-pipeline",
                "asset_scope": ["BTCUSDT"],
                "output_dir": str(research_dir / "operator-pipeline"),
                "providers": [],
                "dataset_stage": {"enabled": False},
                "evidence_stage": {"enabled": False},
            }
        ),
        encoding="utf-8",
    )
    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        response = client.post(
            "/api/operator/research/jobs/prepare-hmm-knn-research-data",
            json={"spec_path": str(spec_path), "stage": "intake"},
            headers={"X-CSRF-Token": csrf_token},
        )

    assert response.status_code == 400
    assert "spec_path must be inside" in response.json()["detail"]


def test_operator_provider_pipeline_rejects_output_outside_research_root(app_config, sample_bars, tmp_path) -> None:
    research_dir = tmp_path / "research"
    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "operator_pipeline_output_reject.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=replace(app_config.research, output_dir=research_dir),
        operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    spec_path = research_dir / "pipeline_specs" / "pipeline_spec.json"
    spec_path.parent.mkdir(parents=True)
    spec_path.write_text(
        json.dumps(
            {
                "version": "operator-pipeline",
                "asset_scope": ["BTCUSDT"],
                "output_dir": str(tmp_path / "outside_output"),
                "providers": [],
                "dataset_stage": {"enabled": False},
                "evidence_stage": {"enabled": False},
            }
        ),
        encoding="utf-8",
    )
    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        response = client.post(
            "/api/operator/research/jobs/prepare-hmm-knn-research-data",
            json={"spec_path": str(spec_path), "stage": "intake"},
            headers={"X-CSRF-Token": csrf_token},
        )

    assert response.status_code == 400
    assert "output_dir must be inside" in response.json()["detail"]


def test_operator_research_experiment_job_queues_completes_and_lists_artifact(app_config, sample_bars, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TBS_SERVER_MONITOR_POLL_SECONDS", "3600")
    research_dir = tmp_path / "research"
    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "operator_experiment.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=replace(app_config.research, output_dir=research_dir),
        operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    pipeline_spec = research_dir / "experiment_specs" / "pipeline.json"
    experiment_spec = research_dir / "experiment_specs" / "research_experiment.json"
    pipeline_spec.parent.mkdir(parents=True)
    pipeline_spec.write_text(
        json.dumps(
            {
                "version": "operator-experiment-pipeline",
                "asset_scope": ["BTCUSDT"],
                "output_dir": str(research_dir / "will-be-overridden"),
                "providers": [],
                "dataset_stage": {"enabled": False},
                "evidence_stage": {"enabled": False},
            }
        ),
        encoding="utf-8",
    )
    experiment_spec.write_text(
        json.dumps(
            {
                "version": "operator-experiment",
                "name": "Operator Experiment",
                "pipeline_spec": str(pipeline_spec),
                "pipeline_stage": "all",
                "output_dir": str(research_dir / "experiments" / "operator-experiment"),
                "required_artifacts": {"data_quality": True, "dataset": False, "evidence": False},
            }
        ),
        encoding="utf-8",
    )

    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        response = client.post(
            "/api/operator/research/jobs/run-research-experiment",
            json={"spec_path": str(experiment_spec)},
            headers={"X-CSRF-Token": csrf_token},
        )
        job = _wait_for_job(client, response.json()["job_id"])
        artifacts = client.get("/api/operator/research/artifacts").json()["items"]

    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    assert job["status"] == "succeeded"
    assert Path(str(job["result"]["experiment_run_manifest_path"])).exists()
    assert Path(str(job["result"]["conclusion_path"])).exists()
    assert any(item["type"] == "research_experiment_run" for item in artifacts)


def test_operator_research_experiment_rejects_live_mode(app_config, sample_bars, tmp_path) -> None:
    research_dir = tmp_path / "research"
    config = AppConfig(
        runtime_mode=RuntimeMode.LIVE,
        db_path=tmp_path / "operator_experiment_live.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=replace(app_config.research, output_dir=research_dir),
        operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    app.state.engine.execution_adapter = FakeLiveAdapter()
    pipeline_spec = research_dir / "experiment_specs" / "pipeline.json"
    experiment_spec = research_dir / "experiment_specs" / "research_experiment.json"
    pipeline_spec.parent.mkdir(parents=True)
    pipeline_spec.write_text(
        json.dumps(
            {
                "version": "operator-experiment-pipeline",
                "asset_scope": ["BTCUSDT"],
                "output_dir": str(research_dir / "will-be-overridden"),
                "providers": [],
                "dataset_stage": {"enabled": False},
                "evidence_stage": {"enabled": False},
            }
        ),
        encoding="utf-8",
    )
    experiment_spec.write_text(
        json.dumps(
            {
                "version": "operator-experiment",
                "name": "Operator Experiment",
                "pipeline_spec": str(pipeline_spec),
                "output_dir": str(research_dir / "experiments" / "operator-experiment"),
                "required_artifacts": {"data_quality": True, "dataset": False, "evidence": False},
            }
        ),
        encoding="utf-8",
    )

    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        response = client.post(
            "/api/operator/research/jobs/run-research-experiment",
            json={"spec_path": str(experiment_spec)},
            headers={"X-CSRF-Token": csrf_token},
        )

    assert response.status_code == 409
    assert "live mode" in response.json()["detail"]


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
