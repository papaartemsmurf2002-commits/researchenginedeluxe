from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import time
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from threading import Event
from types import SimpleNamespace

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from tradingbotsuite.config import AppConfig, BinanceConfig, OperatorUIConfig
from tradingbotsuite.core.models import PositionState, RuntimeMode, SignalDirection, TradeStatus
from tradingbotsuite.operator_commands import execute_manual_signal
from tradingbotsuite.operator_console import OperatorConsoleService, OperatorContext, TraceRecorder
from tradingbotsuite.persistence.sqlite_store import SQLiteStore
from tradingbotsuite.research_discovery.candidate_pack_bridge import (
    DISCOVERY_CANDIDATE_PACK_BRIDGE_VERSION,
    DISCOVERY_CANDIDATE_PACK_ELIGIBILITY_VERSION,
)
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


class TrackingCandles(FakeCandles):
    def __init__(self, bars):
        super().__init__(bars)
        self.started_symbols: list[list[str]] = []

    async def start_market_streams(self, symbols: list[str]):
        self.started_symbols.append(list(symbols))
        return None


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
    strategy = app_config.strategy
    hyperliquid = app_config.hyperliquid
    if mode == RuntimeMode.LIVE:
        strategy = replace(
            strategy,
            max_daily_loss_quote=Decimal("25"),
            max_open_risk_notional=Decimal("100"),
        )
        hyperliquid = replace(
            hyperliquid,
            base_url="https://api.hyperliquid-testnet.xyz",
            enable_live=True,
            account_address="0x1111111111111111111111111111111111111111",
            private_key="0x" + "2" * 64,
        )
    return AppConfig(
        runtime_mode=mode,
        db_path=app_config.db_path,
        webhook=app_config.webhook,
        strategy=strategy,
        binance=app_config.binance,
        hyperliquid=hyperliquid,
        research=app_config.research,
        operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
    )


def _write_completed_catalog_fixture(
    research_dir: Path,
    *,
    write_artifacts: bool = False,
    stale_run_root: Path | None = None,
) -> dict[str, Path]:
    run_root = research_dir / "operator_runs" / "historical_data" / "refresh-historical-data-catalog-test"
    source_root = run_root / "sources" / "binance_vision_public_archive"
    fixture_root = source_root / "fixture_packs"
    readiness_root = source_root / "active_readiness"
    specs_root = source_root / "active_specs"
    readiness_root.mkdir(parents=True, exist_ok=True)
    specs_root.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    def recorded_path(path: Path) -> str:
        if stale_run_root is None:
            return str(path)
        return str(stale_run_root / path.relative_to(run_root))

    symbols = {
        "BTCUSDT": {
            "cycle_id": "r105-btcusdt-durable-public-archive-candidate-depth-v1",
            "discovery_run_id": "exact_entry_sweep_btcusdt_candidate_depth_v1",
        },
        "ETHUSDT": {
            "cycle_id": "r105-ethusdt-durable-public-archive-candidate-depth-v1",
            "discovery_run_id": "exact_entry_sweep_ethusdt_candidate_depth_v1",
        },
    }
    symbol_payloads: dict[str, dict[str, object]] = {}
    for symbol, ids in symbols.items():
        lower = symbol.lower()
        manifest_path = fixture_root / f"{lower}_public_archive_candidate_depth_v1" / "fixture_pack_manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "symbol": symbol,
                    "research_only": True,
                    "observe_only": True,
                    "promotion_ready": False,
                    "base_interval": "15m",
                    "families": {},
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        manifest_sha = "sha256:" + hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        readiness_path = readiness_root / f"durable_public_archive_fixture_readiness_{lower}_candidate_depth_v1.json"
        cycle_spec_path = specs_root / f"{ids['cycle_id']}.json"
        discovery_spec_path = specs_root / f"{ids['discovery_run_id']}.json"
        readiness_path.write_text(
            json.dumps(
                {
                    "symbol": symbol,
                    "readiness_status": "durable_public_archive_ready",
                    "research_only": True,
                    "observe_only": True,
                    "promotion_ready": False,
                    "fixture_manifest_path": recorded_path(manifest_path),
                    "fixture_manifest_sha256": manifest_sha,
                    "fixture_row_counts": {
                        "bars": 221_952,
                        "lower_timeframe_bars": 3_329_280,
                        "agg_trade": 3_291_128,
                    },
                    "candidate_depth_evidence": {"candidate_depth_thresholds_met": True},
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        cycle_spec_path.write_text(
            json.dumps(
                {
                    "cycle_id": ids["cycle_id"],
                    "symbol": symbol,
                    "research_only": True,
                    "observe_only": True,
                    "promotion_ready": False,
                    "data": {"dataset_manifest_paths": [recorded_path(manifest_path)]},
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        discovery_spec_path.write_text(
            json.dumps(
                {
                    "spec_version": "discovery-run-spec-v1",
                    "run_id": ids["discovery_run_id"],
                    "symbol": symbol,
                    "timeframe": "15m",
                    "research_output_dir": recorded_path(source_root),
                    "data": {"dataset_manifest_paths": [recorded_path(manifest_path)]},
                    "budget": {"max_trials": 570_240},
                    "execution": {"max_workers": 2},
                    "search": {
                        "k_values": [3],
                        "probability_thresholds": [0.5],
                        "distance_metrics": ["euclidean"],
                        "label_horizons": ["1h"],
                    },
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        symbol_payloads[symbol] = {
            "symbol": symbol,
            "status": "candidate_depth_ready",
            "candidate_depth_ready": True,
            "candidate_depth_thresholds_met": True,
            "collection_thresholds_met": True,
            "source_summary_path": recorded_path(source_root / "durable_fixture_collection_summary.json"),
            "fixture_manifest_path": recorded_path(manifest_path),
            "fixture_manifest_sha256": manifest_sha,
            "readiness_config_path": recorded_path(readiness_path),
            "cycle_spec_path": recorded_path(cycle_spec_path),
            "discovery_spec_path": recorded_path(discovery_spec_path),
            "cycle_id": ids["cycle_id"],
            "discovery_run_id": ids["discovery_run_id"],
            "row_counts": {
                "bars": 221_952,
                "lower_timeframe_bars": 3_329_280,
                "agg_trade": 3_291_128,
            },
            "effective_coverage_hours": 55_488.0,
            "download_count": 228,
            "checksum_verified_count": 228,
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
        }
        paths[f"{symbol}_cycle_spec"] = cycle_spec_path
        paths[f"{symbol}_discovery_spec"] = discovery_spec_path
        paths[f"{symbol}_fixture_manifest"] = manifest_path

        if write_artifacts and symbol == "BTCUSDT":
            cycle_manifest = (
                research_dir
                / "historical_cycles"
                / str(ids["cycle_id"]).replace("-", "_")
                / "research_cycle_manifest.json"
            )
            cycle_manifest.parent.mkdir(parents=True, exist_ok=True)
            cycle_manifest.write_text(
                json.dumps(
                    {
                        "cycle_id": ids["cycle_id"],
                        "symbol": symbol,
                        "candidate_count": 63,
                        "research_only": True,
                        "observe_only": True,
                        "promotion_ready": False,
                        "required_outputs": {
                            "cycle_spec_resolved": "cycle_spec_resolved.json",
                            "candidate_rankings": "candidate_rankings.json",
                            "candidate_gate_report": "candidate_gate_report.parquet",
                            "backtest_index": "backtest_index.json",
                        },
                        "candidate_selection_performance_plan": {
                            "materialized_search_candidate_count": 63,
                            "bruteforce_equivalent_candidate_count": 2048,
                        },
                        "data_source": {
                            "durable_public_archive_readiness": {"primary_bar_count": 221_952}
                        },
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            discovery_manifest = research_dir / "discovery_runs" / ids["discovery_run_id"] / "discovery_run_manifest.json"
            discovery_manifest.parent.mkdir(parents=True, exist_ok=True)
            discovery_manifest.write_text(
                json.dumps(
                    {
                        "run_id": ids["discovery_run_id"],
                        "symbol": symbol,
                        "research_only": True,
                        "observe_only": True,
                        "promotion_ready": False,
                        "state": {"status": "completed"},
                        "budget": {"max_trials": 570_240},
                        "search_space": {
                            "planned_trials": 570_240,
                            "exhaustive": True,
                            "sampled_fraction": 1.0,
                        },
                        "counts": {"completed_trials": 570_240},
                        "required_outputs": {
                            "discovery_spec_resolved": "discovery_spec_resolved.json",
                            "run_state": "run_state.json",
                            "blocked_candidates": "blocked_candidates.json",
                            "filter_blockers": "filter_blockers.json",
                            "snapshots": "snapshots",
                            "trials": "trials",
                        },
                        "data_evidence": {"row_count": 221_952},
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )

    summary_path = source_root / "durable_fixture_collection_summary.json"
    summary_path.write_text(
        json.dumps({"symbols": symbol_payloads, "research_only": True, "observe_only": True, "promotion_ready": False}),
        encoding="utf-8",
    )
    catalog_path = run_root / "historical_data_catalog.json"
    catalog_path.write_text(
        json.dumps(
            {
                "historical_data_catalog_version": "historical-data-catalog-v1",
                "stage": "R106",
                "source_of_truth": "historical_data_catalog",
                "catalog_ready": True,
                "candidate_depth_ready": True,
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "symbols": symbol_payloads,
                "provider_states": {},
                "start_month": "2020-01",
                "end_month": "2026-04",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    paths["catalog"] = catalog_path
    return paths


def test_operator_server_can_disable_binance_market_stream_startup(app_config, sample_bars, tmp_path) -> None:
    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "operator_no_market_streams.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=BinanceConfig(base_url="https://example.invalid", market_streams_enabled=False),
        hyperliquid=app_config.hyperliquid,
        research=app_config.research,
        operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
    )
    app = create_app(config)
    candles = TrackingCandles(sample_bars)
    app.state.engine.candle_client = candles
    with TestClient(app):
        pass

    assert candles.started_symbols == []
    assert any(
        item["summary"] == "initialize:market_streams_skipped"
        for item in app.state.operator_service.context.trace_recorder.list_recent(limit=20)
    )


def _patch_runtime_live_adapter(monkeypatch) -> None:
    def fake_make_execution_adapter(mode: RuntimeMode, **kwargs):
        if mode == RuntimeMode.LIVE:
            return FakeLiveAdapter()
        raise AssertionError(f"unexpected mode in live adapter test: {mode}")

    monkeypatch.setattr("tradingbotsuite.runtime.make_execution_adapter", fake_make_execution_adapter)


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


def test_operator_artifacts_include_historical_cycle_profitability_summary(app_config, sample_bars, tmp_path) -> None:
    research_dir = tmp_path / "research"
    cycle_dir = research_dir / "historical_cycles" / "fixture-cycle"
    cycle_dir.mkdir(parents=True)
    rankings_path = cycle_dir / "candidate_rankings.parquet"
    gate_path = cycle_dir / "candidate_gate_report.parquet"
    holding_path = cycle_dir / "metrics_by_holding_window.parquet"
    pd.DataFrame(
        [
            {
                "candidate_id": "candidate-a",
                "strategy_id": "perp_basis_convergence_v2",
                "feature_set_id": "features_perp_context_v2",
                "holding_window": "4h",
                "exit_policy_id": "fixed_holding_window",
                "decision": "rejected",
                "final_score": 0.04,
                "costed_expectancy": 0.01,
                "net_return_after_fees_slippage_funding": 0.03,
                "max_drawdown": -0.01,
                "profit_factor": 1.2,
                "trade_count": 4,
                "failure_reasons": "research_gate_rejected",
            },
            {
                "candidate_id": "candidate-b",
                "strategy_id": "baseline_no_trade",
                "feature_set_id": "features_perp_context_v2",
                "holding_window": "1h",
                "exit_policy_id": "fixed_holding_window",
                "decision": "comparator",
                "final_score": 0.0,
                "costed_expectancy": 0.0,
                "net_return_after_fees_slippage_funding": 0.0,
                "max_drawdown": 0.0,
                "profit_factor": 0.0,
                "trade_count": 0,
                "failure_reasons": "",
            },
        ]
    ).to_parquet(rankings_path, index=False)
    pd.DataFrame(
        [
            {"candidate_id": "candidate-a", "candidate_acceptance_scope": "research_gate_evaluated_fail_closed", "gate_passed": False, "decision": "rejected"},
            {"candidate_id": "candidate-b", "candidate_acceptance_scope": "comparator_only", "gate_passed": False, "decision": "comparator"},
        ]
    ).to_parquet(gate_path, index=False)
    pd.DataFrame(
        [
            {"holding_window": "4h", "candidate_count": 1, "holding_window_trade_count": 4, "median_costed_expectancy": 0.01, "best_final_score": 0.04},
            {"holding_window": "1h", "candidate_count": 1, "holding_window_trade_count": 0, "median_costed_expectancy": 0.0, "best_final_score": 0.0},
        ]
    ).to_parquet(holding_path, index=False)
    (cycle_dir / "research_cycle_manifest.json").write_text(
        json.dumps(
            {
                "research_cycle_manifest_version": "historical-research-cycle-manifest-v1",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "cycle_id": "fixture-cycle",
                "symbol": "BTCUSDT",
                "candidate_count": 2,
                "candidate_search_mode": "metadata_default_search",
                "candidate_search_method": "metadata_capped_grid",
                "aggregate_backtest_count": 2,
                "split_backtest_count": 1,
                "cost_stress_backtest_count": 1,
                "candidate_pack_written": False,
                "candidate_acceptance_scope": "research_gate_evaluated_fail_closed",
                "backtest_backend_requested": "reference",
                "compute_policy": {
                    "gpu_execution_profile": "fastest_exact",
                    "cpu_threads": 48,
                    "aggregate_backtest_workers_used": 48,
                    "gpu_execution_status": "gpu_execution_profile_fastest_exact_vector_selected",
                    "selected_cuda_backend": "",
                    "cuda_runtime_checked": False,
                    "r97_batched_cuda_requested": False,
                    "tensorcore_screening_requested": False,
                },
                "backtest_backend_summary": {"used_counts": {"vector_fixed_holding": 2, "reference": 2}},
                "runtime": {"elapsed_seconds": 1.25},
                "data_source": {"source_type": "historical_fixture_pack"},
                "required_outputs": {
                    "candidate_rankings": str(rankings_path),
                    "candidate_gate_report": str(gate_path),
                    "metrics_by_holding_window": str(holding_path),
                },
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

    cycle = next(artifact for artifact in payload["items"] if artifact["type"] == "historical_research_cycle")
    assert cycle["summary"]["cycle_id"] == "fixture-cycle"
    assert cycle["summary"]["rankings"]["best_net_return"] == 0.03
    assert cycle["summary"]["rankings"]["strategy_counts"]["perp_basis_convergence_v2"] == 1
    assert cycle["summary"]["rankings"]["decision_counts"]["rejected"] == 1
    assert cycle["summary"]["gate_report"]["passed_count"] == 0
    assert cycle["summary"]["holding_windows"]["rows"][0]["holding_window"] == "4h"
    assert cycle["summary"]["compute_profile"] == "fastest_exact"
    assert cycle["summary"]["aggregate_backtest_workers_used"] == 48
    assert cycle["summary"]["gpu_execution_status"] == "gpu_execution_profile_fastest_exact_vector_selected"
    assert cycle["summary"]["selected_cuda_backend"] == ""
    assert cycle["summary"]["cuda_runtime_checked"] is False
    assert cycle["summary"]["backtest_backend_used_counts"] == {"vector_fixed_holding": 2, "reference": 2}


def test_operator_research_page_keeps_hmm_knn_monitoring_observe_only(app_config, sample_bars) -> None:
    config = _operator_config(app_config)
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    with TestClient(app) as client:
        _login(client, "operator-secret")
        response = client.get("/ui/research")

    assert response.status_code == 200
    assert "Research Operations" in response.text
    assert "Required Evidence Checklist" in response.text
    assert "Only this checklist is required." in response.text
    assert "Checklist Progress" in response.text
    assert "Required Action Buttons" in response.text
    assert "Run Research Autopilot" in response.text
    assert "0. Refresh Historical Data Catalog" in response.text
    assert "Refresh Historical Catalog" in response.text
    assert "central source of truth" in response.text
    assert "downloads the implemented Binance Vision BTC/ETH archive fixture path" in response.text
    assert "Bybit, Crypto Lake, and Hyperliquid remain visible provider slots" in response.text
    assert "The required workflow uses the R106 Historical Data Catalog" in response.text
    assert "1. Check Catalog Inputs" in response.text
    assert "Run after Step 0" in response.text
    assert "2. BTC Evidence Path" in response.text
    assert "ETH Mirror" in response.text
    assert "4. Analyze Evidence" in response.text
    assert "5. Compare Runs" in response.text
    assert "6. Frozen-Entry Exit Lab" in response.text
    assert "7. Review Eligibility" in response.text
    assert "Current Evidence State" in response.text
    assert "Required Checklist Map" in response.text
    assert "Data Readiness" in response.text
    assert "Current Run" in response.text
    assert "Progress" in response.text
    assert "Latest Snapshot" in response.text
    assert "Catalog Workflow Details" in response.text
    assert "Catalog Readiness" in response.text
    assert "Checklist Details" in response.text
    assert "Recommended Defaults" in response.text
    assert "Candidate Eligibility Review" in response.text
    assert "Check Catalog Readiness" in response.text
    assert "Show Data Gap" in response.text
    assert "Data Required" in response.text
    assert "BTC Deep Cycle" in response.text
    assert "BTC Exact Sweep" in response.text
    assert "ETH Deep Cycle" in response.text
    assert "ETH Exact Sweep" in response.text
    assert "Blockers" in response.text
    assert "Leads" in response.text
    assert "Maturity" in response.text
    assert "Diagnostic" in response.text
    assert "Screen-worthy" in response.text
    assert "Candidate-ready" in response.text
    assert "Open Latest Snapshot" in response.text
    assert "Review Candidate Eligibility" in response.text
    assert "Open Artifact List" in response.text
    assert "Manual Presets And Optional Diagnostics" in response.text
    assert "Secondary controls are not the required path." in response.text
    assert "Required Manual Presets" in response.text
    assert "required manual preset" in response.text
    assert "Optional Diagnostics And Legacy Compatibility" in response.text
    assert "Provider Pipeline Diagnostics" in response.text
    assert "Run Provider Diagnostic" in response.text
    assert "Intake" in response.text
    assert "Dataset" in response.text
    assert "Evidence" in response.text
    assert "All" in response.text
    assert "What The Research System Builds" in response.text
    assert "Historical Cycle Review" in response.text
    assert "run-historical-research-cycle" in response.text
    assert "Run Historical Cycle" in response.text
    assert "BTCUSDT durable deep cycle" in response.text
    assert "ETHUSDT durable deep cycle" in response.text
    assert "BTCUSDT durable deep R104 cycle" not in response.text
    assert "ETHUSDT durable deep R104 cycle" not in response.text
    assert "Operator queued runs write isolated output" in response.text
    assert "Compute Profile" in response.text
    assert "Backend Mix" in response.text
    assert "GPU Status" in response.text
    assert "CUDA Selected" in response.text
    assert "Durable Discovery Search" in response.text
    assert "R104 Durable Discovery Run" not in response.text
    assert "Run Discovery" in response.text
    assert "Resume Discovery" in response.text
    assert "Hardware Utilization Benchmark" in response.text
    assert "Run Hardware Benchmark" in response.text
    assert "hardware_utilization" in response.text
    assert "cpu_below_target" in response.text
    assert "CPU Worker Status" in response.text
    assert "Long CPU Study" in response.text
    assert "performance_utilization_study" in response.text
    assert "Performance utilization measurement" in response.text
    assert "Worker Plan" in response.text
    assert "Artifact Pressure" in response.text
    assert "Process Chunks" in response.text
    assert "BTCUSDT exact bounded sweep" in response.text
    assert "ETHUSDT exact bounded sweep" in response.text
    assert "BTCUSDT durable standard discovery" in response.text
    assert "ETHUSDT durable standard discovery" in response.text
    assert "BTCUSDT legacy compatibility sparse harvest" in response.text
    assert "BTCUSDT diagnostic plumbing check" in response.text
    assert "Exact bounded BTC sweep" in response.text
    assert "not exhaustive" in response.text
    assert "570240" in response.text
    assert "Real HMM-regime plus local KNN entry discovery" not in response.text
    assert "Queueing evidence review bundle" in response.text
    assert "Discovery Ledger" in response.text
    assert "discovery_run" in response.text
    assert "candidate_pack_eligibility" in response.text
    assert "discovery_exit_lab" in response.text
    assert "discovery_multiple_testing" in response.text
    assert "discovery_validation_floors" in response.text
    assert "Queue Evidence Review Bundle" in response.text
    assert "Local Action History / Timeline" in response.text
    assert "isolated job-specific output directories" in response.text
    assert "Required Evidence Profitability Chart" in response.text
    assert "Waiting for profitability artifacts." in response.text
    assert "Required Evidence Graphs" in response.text
    assert "Diagnostic and benchmark cycles are ignored here." in response.text
    assert "No required durable historical cycle found." in response.text
    assert "No required candidate strategy mix yet. Run Historical Cycle Review." in response.text
    assert "No required gate decisions yet. Run Historical Cycle Review and inspect rejection evidence." in response.text
    assert "No required holding-window metrics yet. Run Historical Cycle Review." in response.text
    assert "No required discovery ledger yet. Run BTC/ETH Exact Sweep after the matching deep cycle." in response.text
    assert "Promotion Boundary" in response.text
    assert "promotion_review_required" in response.text
    assert "summary.last_snapshot_path" in response.text
    assert "latestSnapshot.path" in response.text
    assert 'discoveryLedgerCount(discoverySummary, "blocked_candidates", "blocked_candidates")' in response.text
    assert 'discoveryLedgerCount(discoverySummary, "filter_blockers", "filter_blockers")' in response.text
    assert 'interestingDiscoveryLeadCount(discovery)' in response.text
    assert "countPositiveValues(discoverySummary.counts || {}) > 0" not in response.text
    assert 'pickLatest("data_pipeline_intake")' in response.text
    assert 'pickLatest("provider_archive_manifest")' in response.text
    assert "planning panel only" not in response.text
    assert "Planning panel only" in response.text
    assert "historical_research_cycle" in response.text
    assert "HMM/KNN Monitoring" in response.text
    assert "Shadow Diagnostics" in response.text
    assert "Stage 13 Readiness" in response.text
    assert "/api/operator/shadow/diagnostics" in response.text
    assert "/api/operator/stage13/readiness" in response.text
    assert "/api/operator/research/r104-readiness" in response.text
    assert "/api/operator/research/historical-data-catalog" in response.text
    assert "/api/operator/research/progress" in response.text
    assert "0. Refresh Historical Data Catalog" in response.text
    assert "Refresh Historical Catalog" in response.text
    assert "This is the only required data step" in response.text
    assert "Catalog Workflow Details" in response.text
    assert "Provider Pipeline Diagnostics" in response.text
    assert "/api/operator/research/jobs/prepare-hmm-knn-research-data" in response.text
    assert "/api/operator/research/jobs/refresh-historical-data-catalog" in response.text
    assert "/api/operator/research/jobs/run-research-autopilot" in response.text
    assert "/api/operator/research/jobs/run-historical-research-cycle" in response.text
    assert "/api/operator/research/jobs/run-discovery" in response.text
    assert "/api/operator/research/jobs/analyze-research-results" in response.text
    assert "/api/operator/research/jobs/analyze-research-delta" in response.text
    assert "/api/operator/research/jobs/run-frozen-entry-exit-lab" in response.text
    assert "/api/operator/research/jobs/evaluate-discovery-candidate-pack-eligibility" in response.text
    assert "/api/operator/research/jobs/benchmark-hardware-utilization" in response.text
    assert "Analyze Current Evidence" in response.text
    assert "Analyze Run Delta" in response.text
    assert "Run Frozen Entry Exit Lab" in response.text
    assert "research_analysis" in response.text
    assert "research_analysis_delta" in response.text
    assert "research_autopilot" in response.text
    assert "hmm_knn_artifact" in response.text
    assert "observe_only" in response.text
    assert "Live Canary" not in response.text
    assert "Promotion Ready" not in response.text
    assert "R104 Command Center" not in response.text
    assert "Collect Durable Data" not in response.text
    assert "Function Blocks" not in response.text
    assert "Primary BTC Path" not in response.text
    assert "Choose Evidence Task" not in response.text
    assert "R104 Durable Candidate Validation" not in response.text
    assert "Recommended Run Order" not in response.text
    assert "current branch workflow" not in response.text
    assert "older persisted" not in response.text
    assert "legacy compatibility" in response.text
    assert ("Trading" + "View") not in response.text
    assert ("trading" + "view") not in response.text
    assert "/api/operator/commands/" not in response.text
    assert "set-mode" not in response.text
    assert "manual-signal" not in response.text
    assert "smoke-live" not in response.text


def test_operator_research_progress_api_reports_r104_milestones(app_config, sample_bars, tmp_path) -> None:
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_ui.sqlite3",
            webhook=app_config.webhook,
            strategy=app_config.strategy,
            binance=app_config.binance,
            hyperliquid=app_config.hyperliquid,
            research=replace(app_config.research, output_dir=tmp_path / "research"),
            operator_ui=app_config.operator_ui,
        )
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)

    async def fake_jobs_with_non_r104_active() -> list[dict[str, object]]:
        return [
            {
                "job_id": "stale-entry" + "-gate-job",
                "job_type": "optimize-entry" + "-gates",
                "status": "running",
                "requested_at_ms": 1712665800000,
                "started_at_ms": 1712665800000,
                "finished_at_ms": None,
                "request": {},
                "result": None,
                "error_text": None,
            }
        ]

    app.state.operator_service.list_jobs = fake_jobs_with_non_r104_active
    with TestClient(app) as client:
        _login(client, "operator-secret")
        response = client.get("/api/operator/research/progress")

    assert response.status_code == 200
    payload = response.json()
    assert payload["stage"] == "R106"
    assert payload["research_only"] is True
    assert payload["observe_only"] is True
    assert payload["promotion_ready"] is False
    keys = {item["key"] for item in payload["milestones"]}
    assert {
        "historical_data_catalog",
        "durable_readiness",
        "btc_cycle",
        "btc_discovery",
        "eth_cycle",
        "eth_discovery",
        "research_analysis",
        "research_analysis_delta",
        "frozen_entry_exit_lab",
        "candidate_eligibility",
    } <= keys
    by_key = {item["key"]: item for item in payload["milestones"]}
    assert by_key["historical_data_catalog"]["status"] == "ready"
    assert "Refresh the R106 Historical Data Catalog" in by_key["historical_data_catalog"]["detail"]
    assert by_key["durable_readiness"]["status"] == "blocked"
    assert by_key["btc_cycle"]["status"] == "waiting"
    assert "Candidate-depth durable data" in by_key["btc_cycle"]["detail"]
    assert by_key["btc_discovery"]["status"] == "waiting"
    assert "BTC brute-force cycle" in by_key["btc_discovery"]["detail"]
    assert by_key["eth_cycle"]["status"] == "waiting"
    assert by_key["eth_discovery"]["status"] == "waiting"
    assert "ETH brute-force cycle" in by_key["eth_discovery"]["detail"]
    assert by_key["research_analysis"]["status"] == "waiting"
    assert by_key["research_analysis_delta"]["status"] == "waiting"
    assert by_key["frozen_entry_exit_lab"]["status"] == "waiting"
    assert by_key["candidate_eligibility"]["status"] == "waiting"
    assert payload["progress"]["total"] == len(payload["milestones"])
    assert payload["progress"]["active_job_type"] is None
    assert "optimize-entry" + "-gates" not in payload["next_action"]
    assert "stable resumable output directory" in payload["settings"]["output_policy"]
    assert "570240" in payload["settings"]["primary_discovery_profile"]
    assert "Refresh the R106 Historical Data Catalog" in payload["next_action"]


def test_operator_research_progress_api_indexes_bounded_r104_disk_artifacts(app_config, sample_bars, tmp_path) -> None:
    research_dir = tmp_path / "research"
    cycle_manifest = (
        research_dir
        / "operator_runs"
        / "historical_cycles"
        / "r104-btcusdt-durable-public-archive-deep-v1"
        / "run-historical-research-cycle-btc"
        / "research_cycle_manifest.json"
    )
    discovery_manifest = (
        research_dir
        / "operator_runs"
        / "discovery_runs"
        / "exact-entry-sweep-btcusdt-durable-r104-v1"
        / "run-discovery-btc"
        / "discovery_run_manifest.json"
    )
    cycle_manifest.parent.mkdir(parents=True)
    discovery_manifest.parent.mkdir(parents=True)
    cycle_manifest.write_text(
        json.dumps(
            {
                "cycle_id": "r104-btcusdt-durable-public-archive-deep-v1",
                "symbol": "BTCUSDT",
                "candidate_count": 128,
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
            }
        ),
        encoding="utf-8",
    )
    discovery_manifest.write_text(
        json.dumps(
            {
                "run_id": "exact_entry_sweep_btcusdt_durable_r104_v1",
                "symbol": "BTCUSDT",
                "state": {"status": "completed", "completed_trial_ids": ["trial-000001"], "snapshot_count": 1},
                "budget": {"max_trials": 570240},
                "search_space": {
                    "planned_trials": 570240,
                    "total_combinations": 570240,
                    "sampled_fraction": 1.0,
                    "exhaustive": True,
                    "coverage_label": "exhaustive",
                },
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
            }
        ),
        encoding="utf-8",
    )
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_ui_disk_artifacts.sqlite3",
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

    async def no_jobs() -> list[dict[str, object]]:
        return []

    app.state.operator_service.list_jobs = no_jobs
    with TestClient(app) as client:
        _login(client, "operator-secret")
        response = client.get("/api/operator/research/progress")

    assert response.status_code == 200
    by_key = {item["key"]: item for item in response.json()["milestones"]}
    assert by_key["btc_cycle"]["status"] == "waiting"
    assert by_key["btc_discovery"]["status"] == "waiting"
    assert by_key["research_analysis"]["status"] == "waiting"
    assert by_key["research_analysis_delta"]["status"] == "waiting"
    assert by_key["frozen_entry_exit_lab"]["status"] == "waiting"
    assert by_key["candidate_eligibility"]["status"] == "waiting"
    assert "research_cycle_manifest.json" in by_key["btc_cycle"]["artifact_path"]
    assert "discovery_run_manifest.json" in by_key["btc_discovery"]["artifact_path"]


def test_operator_timeline_page_renders_job_status_detail(app_config, sample_bars) -> None:
    config = _operator_config(app_config)
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    with TestClient(app) as client:
        _login(client, "operator-secret")
        response = client.get("/ui/timeline")

    assert response.status_code == 200
    assert "timeline-job-meta" in response.text
    assert "jobStatusBadge" in response.text
    assert "status stored by operator job loop" in response.text
    assert "request.spec_path" in response.text


def test_operator_r104_readiness_api_reports_durable_btc_eth(app_config, sample_bars, tmp_path) -> None:
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_ui_readiness.sqlite3",
            webhook=app_config.webhook,
            strategy=app_config.strategy,
            binance=app_config.binance,
            hyperliquid=app_config.hyperliquid,
            research=replace(app_config.research, output_dir=tmp_path / "research"),
            operator_ui=app_config.operator_ui,
        )
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    with TestClient(app) as client:
        _login(client, "operator-secret")
        response = client.get("/api/operator/research/r104-readiness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["stage"] == "R106"
    assert payload["source_of_truth"] == "historical_data_catalog"
    assert payload["research_only"] is True
    assert payload["observe_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["ready"] is False
    assert payload["fixture_integrity_ready"] is True
    assert payload["candidate_evidence_ready"] is False
    assert payload["ready_count"] == 0
    assert payload["fixture_integrity_ready_count"] == 2
    assert payload["evidence_depth_ready_count"] == 0
    by_symbol = {item["symbol"]: item for item in payload["items"]}
    assert set(by_symbol) == {"BTCUSDT", "ETHUSDT"}
    assert "full_cycle_btcusdt_durable_public_archive_r104_deep_v1.json" in by_symbol["BTCUSDT"]["cycle_spec_path"]
    assert "full_cycle_ethusdt_durable_public_archive_r104_deep_v1.json" in by_symbol["ETHUSDT"]["cycle_spec_path"]
    assert "exact_entry_sweep_btcusdt_durable_r104_v1.json" in by_symbol["BTCUSDT"]["discovery_spec_path"]
    assert "exact_entry_sweep_ethusdt_durable_r104_v1.json" in by_symbol["ETHUSDT"]["discovery_spec_path"]
    assert "full_cycle_btcusdt_durable_public_archive_r104_v1.json" in by_symbol["BTCUSDT"]["standard_cycle_spec_path"]
    assert by_symbol["BTCUSDT"]["fixture_row_counts"]["bars"] > 0
    assert by_symbol["ETHUSDT"]["fixture_row_counts"]["bars"] > 0
    assert by_symbol["BTCUSDT"]["fixture_integrity_ready"] is True
    assert by_symbol["BTCUSDT"]["candidate_evidence_ready"] is False
    assert by_symbol["BTCUSDT"]["evidence_depth"]["primary_bars"] == 32
    assert by_symbol["BTCUSDT"]["evidence_depth"]["required_primary_15m_bars"] == 35040
    assert any("primary_15m_bars_below_candidate_floor" in item for item in by_symbol["BTCUSDT"]["evidence_depth_blockers"])


def test_operator_research_job_routes_default_to_r104_deep_and_exact_specs(app_config, sample_bars, tmp_path) -> None:
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_ui_default_specs.sqlite3",
            webhook=app_config.webhook,
            strategy=app_config.strategy,
            binance=app_config.binance,
            hyperliquid=app_config.hyperliquid,
            research=replace(app_config.research, output_dir=tmp_path / "research"),
            operator_ui=app_config.operator_ui,
        )
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    observed: list[tuple[str, dict[str, object]]] = []

    async def fake_queue_job(job_type: str, payload: dict[str, object]) -> dict[str, object]:
        observed.append((job_type, payload))
        return {"job_id": f"job-{len(observed)}", "status": "queued", "job_type": job_type}

    app.state.operator_service.queue_job = fake_queue_job
    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        catalog_response = client.post(
            "/api/operator/research/jobs/refresh-historical-data-catalog",
            json={},
            headers={"X-CSRF-Token": csrf_token},
        )
        cycle_response = client.post(
            "/api/operator/research/jobs/run-historical-research-cycle",
            json={},
            headers={"X-CSRF-Token": csrf_token},
        )
        discovery_response = client.post(
            "/api/operator/research/jobs/run-discovery",
            json={},
            headers={"X-CSRF-Token": csrf_token},
        )
        hardware_response = client.post(
            "/api/operator/research/jobs/benchmark-hardware-utilization",
            json={"cpu_workers": 2, "cpu_seconds": 0.5, "gpu_seconds": 0.5, "matrix_size": 128},
            headers={"X-CSRF-Token": csrf_token},
        )

    assert catalog_response.status_code == 200
    assert cycle_response.status_code == 200
    assert discovery_response.status_code == 200
    assert hardware_response.status_code == 200
    assert observed[0][0] == "refresh-historical-data-catalog"
    assert observed[0][1]["symbols"] == ["BTCUSDT", "ETHUSDT"]
    assert observed[0][1]["start_month"] == "2020-01"
    assert observed[0][1]["source_name"] == "historical_data_catalog"
    assert observed[1][0] == "run-historical-research-cycle"
    assert observed[2][0] == "run-discovery"
    assert observed[3][0] == "benchmark-hardware-utilization"
    assert "full_cycle_btcusdt_durable_public_archive_r104_deep_v1.json" in str(observed[1][1]["spec_path"])
    assert "exact_entry_sweep_btcusdt_durable_r104_v1.json" in str(observed[2][1]["spec_path"])
    assert observed[2][1]["stable_run_id"] is True
    assert observed[2][1]["overwrite_protection"] == "stable_run_id_output_dir"
    assert observed[3][1]["cpu_workers"] == 2
    assert observed[3][1]["matrix_size"] == 128


def test_operator_research_job_routes_default_to_active_catalog_specs(app_config, sample_bars, tmp_path) -> None:
    research_dir = tmp_path / "research"
    active_paths = _write_completed_catalog_fixture(research_dir)
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_ui_active_catalog_specs.sqlite3",
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
    observed: list[tuple[str, dict[str, object]]] = []

    async def fake_queue_job(job_type: str, payload: dict[str, object]) -> dict[str, object]:
        observed.append((job_type, payload))
        return {"job_id": f"job-{len(observed)}", "status": "queued", "job_type": job_type}

    app.state.operator_service.queue_job = fake_queue_job
    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        cycle_response = client.post(
            "/api/operator/research/jobs/run-historical-research-cycle",
            json={},
            headers={"X-CSRF-Token": csrf_token},
        )
        discovery_response = client.post(
            "/api/operator/research/jobs/run-discovery",
            json={},
            headers={"X-CSRF-Token": csrf_token},
        )

    assert cycle_response.status_code == 200
    assert discovery_response.status_code == 200
    assert observed[0][0] == "run-historical-research-cycle"
    assert observed[1][0] == "run-discovery"
    assert observed[0][1]["spec_path"] == str(active_paths["BTCUSDT_cycle_spec"])
    assert observed[1][1]["spec_path"] == str(active_paths["BTCUSDT_discovery_spec"])
    assert observed[1][1]["stable_run_id"] is True
    assert observed[1][1]["overwrite_protection"] == "stable_run_id_output_dir"


def test_operator_research_job_routes_rebase_migrated_active_catalog_specs(app_config, sample_bars, tmp_path) -> None:
    research_dir = tmp_path / "research"
    stale_run_root = (
        Path(r"C:\Users\papaa\Music\tradingbotsuite\data\research\operator_runs\historical_data")
        / "refresh-historical-data-catalog-test"
    )
    active_paths = _write_completed_catalog_fixture(research_dir, stale_run_root=stale_run_root)
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_ui_migrated_catalog_specs.sqlite3",
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
    observed: list[tuple[str, dict[str, object]]] = []

    async def fake_queue_job(job_type: str, payload: dict[str, object]) -> dict[str, object]:
        observed.append((job_type, payload))
        return {"job_id": f"job-{len(observed)}", "status": "queued", "job_type": job_type}

    app.state.operator_service.queue_job = fake_queue_job
    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        cycle_response = client.post(
            "/api/operator/research/jobs/run-historical-research-cycle",
            json={},
            headers={"X-CSRF-Token": csrf_token},
        )
        discovery_response = client.post(
            "/api/operator/research/jobs/run-discovery",
            json={},
            headers={"X-CSRF-Token": csrf_token},
        )

    assert cycle_response.status_code == 200
    assert discovery_response.status_code == 200
    assert observed[0][1]["spec_path"] == str(active_paths["BTCUSDT_cycle_spec"])
    assert observed[1][1]["spec_path"] == str(active_paths["BTCUSDT_discovery_spec"])


def test_operator_start_recovers_interrupted_running_jobs(app_config, sample_bars, tmp_path) -> None:
    db_path = tmp_path / "operator_ui_recover_running.sqlite3"
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=db_path,
            webhook=app_config.webhook,
            strategy=app_config.strategy,
            binance=app_config.binance,
            hyperliquid=app_config.hyperliquid,
            research=replace(app_config.research, output_dir=tmp_path / "research"),
            operator_ui=app_config.operator_ui,
        )
    )

    async def seed_running_job() -> None:
        store = SQLiteStore(db_path)
        await store.initialize()
        await store.queue_operator_job(
            job_id="run-discovery-stale-test",
            job_type="run-discovery",
            requested_at_ms=1712665800000,
            request={"symbol": "BTCUSDT"},
        )
        await store.mark_operator_job_started("run-discovery-stale-test", 1712665800000)

    asyncio.run(seed_running_job())
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    with TestClient(app) as client:
        _login(client, "operator-secret")
        response = client.get("/api/operator/research/jobs/run-discovery-stale-test")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"
    assert payload["error_text"] == "stale_running_job_recovered_after_operator_restart"


def test_operator_restart_requeues_stale_autopilot_once(app_config, tmp_path) -> None:
    db_path = tmp_path / "operator_autopilot_recover_running.sqlite3"
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=db_path,
            webhook=app_config.webhook,
            strategy=app_config.strategy,
            binance=app_config.binance,
            hyperliquid=app_config.hyperliquid,
            research=replace(app_config.research, output_dir=tmp_path / "research"),
            operator_ui=app_config.operator_ui,
        )
    )

    async def recover() -> tuple[dict[str, object], dict[str, object]]:
        store = SQLiteStore(db_path)
        await store.initialize()
        await store.queue_operator_job(
            job_id="run-research-autopilot-stale-test",
            job_type="run-research-autopilot",
            requested_at_ms=1712665800000,
            request={"symbols": ["BTCUSDT"], "include_catalog_refresh": False},
        )
        await store.mark_operator_job_started("run-research-autopilot-stale-test", 1712665800000)
        engine = SimpleNamespace(config=config, store=store, clock=lambda: 1712665900000)
        service = OperatorConsoleService(OperatorContext(config=config, engine=engine, trace_recorder=TraceRecorder()))
        await service._recover_interrupted_running_jobs()
        original = await store.get_operator_job("run-research-autopilot-stale-test")
        retry = await store.get_operator_job("run-research-autopilot-stale-test-restart-retry-1")
        assert original is not None
        assert retry is not None
        return original, retry

    original, retry = asyncio.run(recover())

    assert original["status"] == "failed"
    assert original["error_text"] == "stale_running_job_recovered_after_operator_restart"
    assert retry["status"] == "queued"
    assert retry["job_type"] == "run-research-autopilot"
    assert retry["request"]["_stale_recovery_attempt"] == 1
    assert retry["request"]["recovered_from_job_id"] == "run-research-autopilot-stale-test"


def test_operator_progress_accepts_candidate_depth_catalog_artifact_ids(app_config, sample_bars, tmp_path) -> None:
    research_dir = tmp_path / "research"
    _write_completed_catalog_fixture(research_dir, write_artifacts=True)
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_ui_active_catalog_artifacts.sqlite3",
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

    async def no_jobs() -> list[dict[str, object]]:
        return []

    app.state.operator_service.list_jobs = no_jobs
    with TestClient(app) as client:
        _login(client, "operator-secret")
        readiness_response = client.get("/api/operator/research/r104-readiness")
        progress_response = client.get("/api/operator/research/progress")

    assert readiness_response.status_code == 200
    readiness = readiness_response.json()
    assert readiness["ready"] is True
    by_symbol = {item["symbol"]: item for item in readiness["items"]}
    assert by_symbol["BTCUSDT"]["cycle_id"] == "r105-btcusdt-durable-public-archive-candidate-depth-v1"
    assert by_symbol["BTCUSDT"]["discovery_run_id"] == "exact_entry_sweep_btcusdt_candidate_depth_v1"

    assert progress_response.status_code == 200
    by_key = {item["key"]: item for item in progress_response.json()["milestones"]}
    assert by_key["historical_data_catalog"]["status"] == "complete"
    assert by_key["durable_readiness"]["status"] == "complete"
    assert by_key["btc_cycle"]["status"] == "complete"
    assert "deep_cycle_materialized_candidate_count_below_current_floor" not in by_key["btc_cycle"]["blockers"]
    assert "required_output_missing:candidate_gate_report" not in by_key["btc_cycle"]["blockers"]
    assert by_key["btc_discovery"]["status"] == "complete"
    assert "exact_required_discovery_run_id_missing" not in by_key["btc_discovery"]["blockers"]
    assert by_key["research_analysis"]["status"] == "ready"
    assert by_key["research_analysis_delta"]["status"] == "waiting"
    assert by_key["frozen_entry_exit_lab"]["status"] == "waiting"
    assert by_key["candidate_eligibility"]["status"] == "waiting"
    assert by_key["eth_cycle"]["status"] == "ready"


def test_operator_progress_prefers_repaired_discovery_artifact_over_failed_job(app_config, sample_bars, tmp_path) -> None:
    research_dir = tmp_path / "research"
    paths = _write_completed_catalog_fixture(research_dir, write_artifacts=True)
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_ui_repaired_discovery.sqlite3",
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

    async def failed_discovery_job() -> list[dict[str, object]]:
        return [
            {
                "job_id": "run-discovery-failed-after-final-compute",
                "job_type": "run-discovery",
                "status": "failed",
                "request": {
                    "spec_path": str(paths["BTCUSDT_discovery_spec"]),
                    "resume": True,
                    "stable_run_id": True,
                },
                "error_text": "ledger parquet write failed",
            },
            {
                "job_id": "run-discovery-eth-before-cycle",
                "job_type": "run-discovery",
                "status": "failed",
                "request": {
                    "spec_path": str(paths["ETHUSDT_discovery_spec"]),
                    "resume": True,
                    "stable_run_id": True,
                },
                "error_text": "prerequisite cycle missing",
            },
        ]

    app.state.operator_service.list_jobs = failed_discovery_job
    with TestClient(app) as client:
        _login(client, "operator-secret")
        progress_response = client.get("/api/operator/research/progress")

    assert progress_response.status_code == 200
    by_key = {item["key"]: item for item in progress_response.json()["milestones"]}
    assert by_key["btc_discovery"]["status"] == "complete"
    assert by_key["btc_discovery"]["blockers"] == []
    assert by_key["eth_discovery"]["status"] == "waiting"
    assert "failed BTC exact discovery" not in progress_response.json()["next_action"]


def test_operator_research_progress_reports_historical_data_refresh_journal(app_config, sample_bars, tmp_path) -> None:
    research_root = tmp_path / "research"
    job_id = "refresh-historical-data-catalog-test"
    progress_path = research_root / "operator_runs" / "historical_data" / job_id / "sources" / "binance_vision_public_archive" / "collection_progress.json"
    progress_path.parent.mkdir(parents=True)
    progress_path.write_text(
        json.dumps(
            {
                "progress_version": "durable-public-archive-fixture-collection-progress-v1",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "status": "running",
                "completed_archive_steps": 7,
                "total_archive_steps": 456,
                "percent_complete": 1.54,
                "eta_seconds": 1234,
                "elapsed_seconds": 55,
                "archive_steps_per_minute": 7.6,
                "current": {"symbol": "BTCUSDT", "period": "2020-03", "data_family": "agg_trade", "interval": None},
                "updated_at": "2026-05-21T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_progress_data.sqlite3",
            webhook=app_config.webhook,
            strategy=app_config.strategy,
            binance=app_config.binance,
            hyperliquid=app_config.hyperliquid,
            research=replace(app_config.research, output_dir=research_root),
            operator_ui=app_config.operator_ui,
        )
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)

    async def fake_jobs() -> list[dict[str, object]]:
        return [
            {
                "job_id": job_id,
                "job_type": "refresh-historical-data-catalog",
                "status": "running",
                "request": {},
                "result": {},
                "error": None,
            }
        ]

    app.state.operator_service.list_jobs = fake_jobs
    with TestClient(app) as client:
        _login(client, "operator-secret")
        response = client.get("/api/operator/research/progress")

    assert response.status_code == 200
    payload = response.json()
    data_progress = payload["active_historical_data_progress"]
    assert data_progress["job_id"] == job_id
    assert data_progress["completed_archive_steps"] == 7
    assert data_progress["total_archive_steps"] == 456
    assert data_progress["percent_complete"] == 1.54
    assert data_progress["current"]["period"] == "2020-03"


def test_operator_research_progress_does_not_show_completed_refresh_as_active(app_config, sample_bars, tmp_path) -> None:
    research_root = tmp_path / "research"
    progress_path = (
        research_root
        / "operator_runs"
        / "historical_data"
        / "refresh-historical-data-catalog-complete"
        / "sources"
        / "binance_vision_public_archive"
        / "collection_progress.json"
    )
    progress_path.parent.mkdir(parents=True)
    progress_path.write_text(
        json.dumps(
            {
                "progress_version": "durable-public-archive-fixture-collection-progress-v1",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "status": "complete",
                "completed_archive_steps": 456,
                "total_archive_steps": 456,
                "percent_complete": 100.0,
                "eta_seconds": 0,
            }
        ),
        encoding="utf-8",
    )
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_progress_no_active_data.sqlite3",
            webhook=app_config.webhook,
            strategy=app_config.strategy,
            binance=app_config.binance,
            hyperliquid=app_config.hyperliquid,
            research=replace(app_config.research, output_dir=research_root),
            operator_ui=app_config.operator_ui,
        )
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)

    async def no_jobs() -> list[dict[str, object]]:
        return []

    app.state.operator_service.list_jobs = no_jobs
    with TestClient(app) as client:
        _login(client, "operator-secret")
        response = client.get("/api/operator/research/progress")

    assert response.status_code == 200
    assert response.json()["active_historical_data_progress"] is None


def test_operator_research_progress_reports_historical_cycle_progress(app_config, sample_bars, tmp_path) -> None:
    research_root = tmp_path / "research"
    job_id = "run-historical-research-cycle-progress-test"
    cycle_id = "btc-full-cycle-v1"
    output_dir = research_root / "operator_runs" / "historical_cycles" / cycle_id / job_id
    output_dir.mkdir(parents=True)
    (output_dir / "candidate_space_manifest.json").write_text(
        json.dumps(
            {
                "candidate_space_manifest_version": "historical-research-candidate-space-v1",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "candidate_count": 64,
                "search_mode": "metadata_default_search",
                "search_method": "metadata_capped_grid",
                "performance_plan": {
                    "materialized_search_candidate_count": 64,
                    "bruteforce_equivalent_candidate_count": 2048,
                    "sampled_fraction_of_bruteforce": 0.03125,
                    "bruteforce_avoidance_ratio": 32.0,
                    "compute_policy": {"cpu_threads": 48},
                },
                "compute_policy": {"cpu_threads": 48},
            }
        ),
        encoding="utf-8",
    )
    backtest_root = output_dir / "backtests"
    for index in range(7):
        candidate_dir = backtest_root / f"agg-{index}"
        candidate_dir.mkdir(parents=True)
        (candidate_dir / "backtest_manifest.json").write_text(
            json.dumps(
                {
                    "backtest_manifest_version": "test",
                    "research_only": True,
                    "observe_only": True,
                    "promotion_ready": False,
                }
            ),
            encoding="utf-8",
        )
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_progress_cycle.sqlite3",
            webhook=app_config.webhook,
            strategy=app_config.strategy,
            binance=app_config.binance,
            hyperliquid=app_config.hyperliquid,
            research=replace(app_config.research, output_dir=research_root),
            operator_ui=app_config.operator_ui,
        )
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)

    async def fake_jobs() -> list[dict[str, object]]:
        return [
            {
                "job_id": job_id,
                "job_type": "run-historical-research-cycle",
                "status": "running",
                "started_at_ms": int(time.time() * 1000) - 120_000,
                "request": {"spec_path": str(Path("configs/research/full_cycle_btc_v1.json").resolve())},
                "result": {},
                "error": None,
            }
        ]

    app.state.operator_service.list_jobs = fake_jobs
    with TestClient(app) as client:
        _login(client, "operator-secret")
        response = client.get("/api/operator/research/progress")

    assert response.status_code == 200
    payload = response.json()
    cycle_progress = payload["active_historical_cycle_progress"]
    assert cycle_progress["cycle_id"] == cycle_id
    assert cycle_progress["symbol"] == "BTCUSDT"
    assert cycle_progress["phase"] == "aggregate_backtests"
    assert cycle_progress["progress_scope"] == "aggregate_candidate_backtests"
    assert cycle_progress["completed_candidates"] == 7
    assert cycle_progress["total_candidates"] == 64
    assert cycle_progress["completed_backtest_evaluations"] == 7
    assert cycle_progress["total_backtest_evaluations"] == 64
    assert cycle_progress["percent"] == 10.94
    assert cycle_progress["bruteforce_equivalent_candidate_count"] == 2048


def test_sqlite_operator_job_log_append_is_concurrency_safe(tmp_path) -> None:
    async def _run() -> None:
        store = SQLiteStore(tmp_path / "operator_job_logs.sqlite3")
        await store.initialize()
        await store.queue_operator_job(
            job_id="refresh-historical-data-catalog-test",
            job_type="refresh-historical-data-catalog",
            requested_at_ms=100,
            request={"symbols": ["BTCUSDT", "ETHUSDT"]},
        )

        async def append(index: int) -> None:
            await store.append_operator_job_log(
                job_id="refresh-historical-data-catalog-test",
                time_ms=100 + index,
                level="info",
                message=f"log-{index}",
                payload={"index": index},
            )

        await asyncio.gather(*(append(index) for index in range(24)))
        job = await store.get_operator_job("refresh-historical-data-catalog-test")
        assert job is not None
        logs = job["logs"]
        assert len(logs) == 24
        assert [log["seq"] for log in logs] == list(range(1, 25))
        assert sorted(log["payload"]["index"] for log in logs) == list(range(24))

    asyncio.run(_run())


def test_operator_hardware_utilization_route_rejects_invalid_payloads(
    app_config,
    sample_bars,
    tmp_path,
) -> None:
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_invalid_hardware_payload.sqlite3",
            webhook=app_config.webhook,
            strategy=app_config.strategy,
            binance=app_config.binance,
            hyperliquid=app_config.hyperliquid,
            research=replace(app_config.research, output_dir=tmp_path / "research"),
            operator_ui=app_config.operator_ui,
        )
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    observed: list[tuple[str, dict[str, object]]] = []

    async def fake_queue_job(job_type: str, payload: dict[str, object]) -> dict[str, object]:
        observed.append((job_type, payload))
        return {"job_id": "unexpected", "status": "queued", "job_type": job_type}

    app.state.operator_service.queue_job = fake_queue_job
    invalid_payloads = [
        {"cpu_workers": 1.5, "cpu_seconds": 0.5, "gpu_seconds": 0.5, "matrix_size": 128},
        {"cpu_workers": 1, "cpu_seconds": 0.01, "gpu_seconds": 0.5, "matrix_size": 128},
        {"cpu_workers": 1, "cpu_seconds": 0.5, "gpu_seconds": 121.0, "matrix_size": 128},
        {"cpu_workers": 1, "cpu_seconds": 0.5, "gpu_seconds": 0.5, "matrix_size": 1},
        {"cpu_workers": 1, "cpu_seconds": 0.5, "gpu_seconds": 0.5, "matrix_size": "64.5"},
    ]

    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        responses = [
            client.post(
                "/api/operator/research/jobs/benchmark-hardware-utilization",
                json=payload,
                headers={"X-CSRF-Token": csrf_token},
            )
            for payload in invalid_payloads
        ]

    assert [response.status_code for response in responses] == [400, 400, 400, 400, 400]
    assert observed == []


def test_operator_research_artifacts_survives_corrupt_json(app_config, sample_bars, tmp_path) -> None:
    research_dir = tmp_path / "research"
    bad_manifest = research_dir / "bad_run" / "research_cycle_manifest.json"
    bad_manifest.parent.mkdir(parents=True)
    bad_manifest.write_text("{not-json", encoding="utf-8")
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_artifact_read_error.sqlite3",
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
        response = client.get("/api/operator/research/artifacts")

    assert response.status_code == 200
    errors = [item for item in response.json()["items"] if item["type"] == "artifact_read_error"]
    assert errors
    assert errors[0]["summary"]["intended_type"] == "historical_research_cycle"
    assert "Expecting property name" in errors[0]["summary"]["error"]


def test_operator_research_artifacts_include_hardware_utilization_summary(
    app_config,
    sample_bars,
    tmp_path,
) -> None:
    research_dir = tmp_path / "research"
    manifest = research_dir / "operator_runs" / "hardware_utilization" / "job-1" / "hardware_utilization_report.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "hardware_utilization_report_version": "hardware-utilization-study-readiness-v1",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "cpu_probe": {
                    "probe_succeeded": True,
                    "active_workers": 16,
                    "logical_cpu_count": 16,
                    "physical_cpu_count": 8,
                    "process_cpu_percent_of_worker_capacity": 96.5,
                    "process_cpu_percent_of_logical_capacity": 48.25,
                    "worker_capacity_saturation_status": "saturated",
                    "logical_capacity_saturation_status": "below_target",
                },
                "gpu_probe": {
                    "probe_succeeded": True,
                    "gpu_execution_status": "cupy_matrix_probe_executed",
                    "approx_gflops_per_second": 4321.0,
                    "runtime_evidence": {"gpu_name": "NVIDIA Test GPU"},
                },
                "recommendations": {"best_option": "hybrid_process_pool_cpu_plus_cuda_supported_fixed_holding"},
                "prolonged_study_readiness": {
                    "cpu_worker_saturation_target_met": True,
                    "ready_for_long_cpu_bound_research": True,
                },
            }
        ),
        encoding="utf-8",
    )
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_hardware_artifact.sqlite3",
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
        response = client.get("/api/operator/research/artifacts")

    assert response.status_code == 200
    hardware = next(item for item in response.json()["items"] if item["type"] == "hardware_utilization")
    assert hardware["summary"]["cpu_workers"] == 16
    assert hardware["summary"]["physical_cpu_count"] == 8
    assert hardware["summary"]["cpu_worker_saturation_status"] == "saturated"
    assert hardware["summary"]["cpu_logical_saturation_status"] == "below_target"
    assert hardware["summary"]["cpu_saturation_target_met"] is True
    assert hardware["summary"]["ready_for_long_cpu_bound_research"] is True
    assert hardware["summary"]["gpu_execution_status"] == "cupy_matrix_probe_executed"
    assert hardware["summary"]["gpu_name"] == "NVIDIA Test GPU"
    assert hardware["summary"]["best_option"] == "hybrid_process_pool_cpu_plus_cuda_supported_fixed_holding"
    assert hardware["summary"]["promotion_ready"] is False


def test_operator_research_artifacts_include_discovery_performance_summary(app_config, sample_bars, tmp_path) -> None:
    research_dir = tmp_path / "research"
    run_dir = research_dir / "operator_runs" / "discovery_runs" / "perf-run"
    manifest = run_dir / "discovery_run_manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "discovery_run_manifest_version": "discovery-run-manifest-v1",
                "run_id": "perf-run",
                "symbol": "BTCUSDT",
                "timeframe": "15m",
                "discovery_mode": "entry_discovery_standard",
                "state": {"status": "completed", "message": "done", "completed_trial_ids": ["trial-000001"], "failed_trial_ids": [], "snapshot_count": 1},
                "budget": {"max_trials": 4},
                "search_space": {"planned_trials": 4, "total_combinations": 4, "sampled_fraction": 1.0, "exhaustive": True, "coverage_label": "exhaustive"},
                "counts": {"completed_trials": 4, "interesting_candidates": 1, "blocked_candidates": 3, "filter_blockers": 0},
                "required_outputs": {},
                "runtime": {"elapsed_seconds": 12.5},
                "compute_telemetry": {
                    "telemetry_version": "discovery-compute-telemetry-v2",
                    "executor": "process",
                    "configured_executor": "process",
                    "configured_max_workers": 8,
                    "requested_workers": 8,
                    "active_workers": 8,
                    "worker_plan": {"active_workers": 8, "reason": "real_discovery_process_worker_cap_not_needed"},
                    "trial_chunk_size": 16,
                    "wall_time_seconds": 12.5,
                    "trials_per_minute": 19.2,
                    "completed_trials": 4,
                    "total_planned_trials": 4,
                    "remaining_trials": 0,
                    "estimated_seconds_remaining": 0,
                    "process_cpu_percent_of_worker_capacity": 77.0,
                    "process_cpu_percent_of_logical_capacity": 38.5,
                    "process_pool_child_cpu_not_in_parent_process_cpu_seconds": True,
                    "artifact_write_time_seconds_observed": 2.0,
                    "artifact_write_wall_time_share": 0.16,
                    "artifact_file_count": 12,
                    "artifact_bytes_written": 4096,
                    "artifact_count_scope": "observed_parent_writes_this_call",
                    "artifact_count_strategy": "recorded_artifact_write_paths_no_recursive_scan",
                    "cache_hit_rates": {"feature_materialization": 0.5, "neighbor": 0.75},
                    "cache_counts": {"neighbor": {"hits": 3, "lookups": 4}},
                    "wall_time_seconds_by_stage": {"trial_execution": 8.0, "final_ledger_materialization": 1.5},
                    "process_chunk_timing": {"measured": True, "chunk_count": 2, "worker_process_count": 2, "total_records": 4},
                },
                "execution_observed": {
                    "executor": "process",
                    "configured_max_workers": 8,
                    "requested_workers": 8,
                    "active_workers": 8,
                    "trial_chunk_size": 16,
                    "process_pool_child_cpu_not_in_parent_process_cpu_seconds": True,
                },
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
            }
        ),
        encoding="utf-8",
    )
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_discovery_performance.sqlite3",
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
        response = client.get("/api/operator/research/artifacts")

    assert response.status_code == 200
    discovery = next(item for item in response.json()["items"] if item["type"] == "discovery_run")
    performance = discovery["summary"]["performance"]
    assert performance["executor"] == "process"
    assert performance["active_workers"] == 8
    assert performance["trial_chunk_size"] == 16
    assert performance["artifact_count_strategy"] == "recorded_artifact_write_paths_no_recursive_scan"
    assert performance["cache_hit_rates"]["neighbor"] == 0.75
    assert performance["process_chunk_timing"]["chunk_count"] == 2
    assert performance["top_stage_seconds"]["trial_execution"] == 8.0


def test_operator_research_progress_reports_discovery_performance_summary(app_config, sample_bars, tmp_path) -> None:
    research_dir = tmp_path / "research"
    run_id = "standard_entry_discovery_btcusdt_v4"
    run_dir = research_dir / "operator_runs" / "discovery_runs" / "standard-entry-discovery-btcusdt-v4"
    run_dir.mkdir(parents=True)
    state_path = run_dir / "run_state.json"
    state_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "status": "in_progress",
                "created_at_utc": "2026-05-26T00:00:00+00:00",
                "updated_at_utc": "2026-05-26T00:01:00+00:00",
                "message": "paused",
                "completed_trial_ids": ["trial-000001", "trial-000002"],
                "failed_trial_ids": [],
                "snapshot_count": 1,
                "last_snapshot_path": str(run_dir / "snapshots" / "000001_snapshot.json"),
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "discovery_run_manifest.json").write_text(
        json.dumps(
            {
                "discovery_run_manifest_version": "discovery-run-manifest-v1",
                "run_id": run_id,
                "symbol": "BTCUSDT",
                "state": {"status": "in_progress", "completed_trial_ids": ["trial-000001", "trial-000002"], "failed_trial_ids": [], "snapshot_count": 1},
                "budget": {"max_trials": 4},
                "required_outputs": {"run_state": str(state_path)},
                "search_space": {"planned_trials": 4, "total_combinations": 4, "sampled_fraction": 1.0, "exhaustive": True, "coverage_label": "exhaustive"},
                "compute_telemetry": {
                    "executor": "process",
                    "active_workers": 4,
                    "requested_workers": 4,
                    "trial_chunk_size": 8,
                    "artifact_bytes_written": 8192,
                    "artifact_write_wall_time_share": 0.2,
                    "artifact_count_strategy": "recorded_artifact_write_paths_no_recursive_scan",
                    "cache_hit_rates": {"feature_materialization": 1.0},
                    "process_pool_child_cpu_not_in_parent_process_cpu_seconds": True,
                },
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
            }
        ),
        encoding="utf-8",
    )
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_progress_discovery_performance.sqlite3",
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
        response = client.get("/api/operator/research/progress")

    assert response.status_code == 200
    active = response.json()["active_discovery_progress"]
    assert active["run_id"] == run_id
    assert active["completed_trials"] == 2
    assert active["performance"]["executor"] == "process"
    assert active["performance"]["active_workers"] == 4
    assert active["performance"]["cache_hit_rates"]["feature_materialization"] == 1.0
    assert active["performance"]["artifact_count_strategy"] == "recorded_artifact_write_paths_no_recursive_scan"


def test_operator_research_artifacts_include_performance_utilization_study_summary(app_config, sample_bars, tmp_path) -> None:
    research_dir = tmp_path / "research"
    summary_path = research_dir / "operator_runs" / "performance_utilization_wpr106_19" / "measurement_summary.json"
    summary_path.parent.mkdir(parents=True)
    summary_path.write_text(
        json.dumps(
            {
                "summary_version": "wpr106-19-performance-utilization-summary-v1",
                "machine": {"cpu": "Test CPU", "physical_cores": 8, "logical_cpus": 16},
                "hardware": [
                    {
                        "name": "hardware_cpu16_gpu45",
                        "active_workers": 16,
                        "cpu_worker_capacity_percent": 88.0,
                        "cpu_logical_capacity_percent": 88.0,
                        "worker_saturation": "saturated",
                        "logical_saturation": "saturated",
                        "gpu_status": "cupy_matrix_probe_executed",
                        "gpu_approx_gflops_per_second": 1234.5,
                    }
                ],
                "historical_cycle_provider_latest_month": {"summary": {"candidate_backtests_per_minute_mean": 60.7, "elapsed_seconds_mean": 24.7}},
                "exact_btc_candidate_depth_probe_16": {"compute_telemetry": {"trials_per_minute": 0.93, "wall_time_seconds": 1033.6, "active_workers": 8, "trial_chunk_size": 8}},
                "active_btc_exact_final_manifest_artifact_rebuild_evidence": {"compute_telemetry": {"artifact_file_count": 570555, "artifact_bytes_written": 7077885918, "artifact_write_wall_time_share": 0.86}},
                "research_boundary": {"research_only": True, "observe_only": True, "promotion_ready": False, "speed_claimed": False},
                "ui_one_line_command": "tradingbotsuite serve --host 127.0.0.1 --port 8000",
            }
        ),
        encoding="utf-8",
    )
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_performance_utilization.sqlite3",
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
        response = client.get("/api/operator/research/artifacts")

    assert response.status_code == 200
    study = next(item for item in response.json()["items"] if item["type"] == "performance_utilization_study")
    assert study["summary"]["best_hardware_profile"] == "hardware_cpu16_gpu45"
    assert study["summary"]["best_hardware_workers"] == 16
    assert study["summary"]["historical_candidate_backtests_per_minute"] == 60.7
    assert study["summary"]["exact_probe_active_workers"] == 8
    assert study["summary"]["final_artifact_file_count"] == 570555
    assert study["summary"]["speed_claimed"] is False


def test_operator_candidate_eligibility_route_requires_research_root_paths(app_config, sample_bars, tmp_path) -> None:
    research_dir = tmp_path / "research"
    research_dir.mkdir()
    outside_manifest = tmp_path / "outside_discovery_run_manifest.json"
    outside_manifest.write_text("{}", encoding="utf-8")
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_candidate_eligibility.sqlite3",
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
        csrf_token = _login(client, "operator-secret")
        response = client.post(
            "/api/operator/research/jobs/evaluate-discovery-candidate-pack-eligibility",
            json={"discovery_manifest_path": str(outside_manifest)},
            headers={"X-CSRF-Token": csrf_token},
        )

    assert response.status_code == 400
    assert "must be inside the research output directory" in response.text


def test_operator_candidate_eligibility_service_requires_research_root_paths(app_config, sample_bars, tmp_path) -> None:
    research_dir = tmp_path / "research"
    research_dir.mkdir()
    outside_manifest = tmp_path / "discovery_run_manifest.json"
    outside_manifest.write_text("{}", encoding="utf-8")
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_candidate_eligibility_service.sqlite3",
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

    with pytest.raises(ValueError, match="configured research output directory"):
        app.state.operator_service._run_isolated_discovery_candidate_pack_eligibility(
            {"discovery_manifest_path": str(outside_manifest)},
            "candidate-eligibility-outside-root",
        )


def test_operator_candidate_eligibility_service_rejects_manifest_outputs_outside_root(
    app_config,
    sample_bars,
    tmp_path,
) -> None:
    research_dir = tmp_path / "research"
    discovery_manifest = research_dir / "discovery_runs" / "exact_entry_sweep_btcusdt_candidate_depth_v1" / "discovery_run_manifest.json"
    discovery_manifest.parent.mkdir(parents=True)
    outside_state = tmp_path / "outside_run_state.json"
    outside_state.write_text("{}", encoding="utf-8")
    discovery_manifest.write_text(
        json.dumps(
            {
                "run_id": "exact_entry_sweep_btcusdt_candidate_depth_v1",
                "symbol": "BTCUSDT",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "required_outputs": {"run_state": str(outside_state)},
            }
        ),
        encoding="utf-8",
    )
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_candidate_eligibility_outputs.sqlite3",
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

    with pytest.raises(ValueError, match="required output must stay inside"):
        app.state.operator_service._run_isolated_discovery_candidate_pack_eligibility(
            {"discovery_manifest_path": str(discovery_manifest)},
            "candidate-eligibility-outside-output",
        )


def test_operator_candidate_eligibility_service_rebases_migrated_manifest_outputs(
    app_config,
    sample_bars,
    tmp_path,
    monkeypatch,
) -> None:
    research_dir = tmp_path / "research"
    run_name = "exact-entry-sweep-btcusdt-candidate-depth-v1"
    current_run_dir = research_dir / "operator_runs" / "discovery_runs" / run_name
    stale_run_dir = Path(r"C:\Users\papaa\Music\tradingbotsuite\data\research\operator_runs\discovery_runs") / run_name
    ledger_dir = current_run_dir / "candidate_ledgers"
    trials_dir = current_run_dir / "trials"
    snapshots_dir = current_run_dir / "snapshots"
    ledger_dir.mkdir(parents=True)
    trials_dir.mkdir()
    snapshots_dir.mkdir()
    discovery_manifest = current_run_dir / "discovery_run_manifest.json"
    run_state = current_run_dir / "run_state.json"
    interesting = ledger_dir / "interesting_candidates.parquet"
    blocked = ledger_dir / "blocked_candidates.parquet"
    filter_blockers = ledger_dir / "filter_blockers.parquet"
    for path in (run_state, interesting, blocked, filter_blockers):
        path.write_text("{}", encoding="utf-8")
    discovery_manifest.write_text(
        json.dumps(
            {
                "run_id": "exact_entry_sweep_btcusdt_candidate_depth_v1",
                "symbol": "BTCUSDT",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "required_outputs": {
                    "run_state": str(stale_run_dir / "run_state.json"),
                    "interesting_candidates": str(stale_run_dir / "candidate_ledgers" / "interesting_candidates.parquet"),
                    "blocked_candidates": str(stale_run_dir / "candidate_ledgers" / "blocked_candidates.parquet"),
                    "filter_blockers": str(stale_run_dir / "candidate_ledgers" / "filter_blockers.parquet"),
                    "trials": str(stale_run_dir / "trials"),
                    "snapshots": str(stale_run_dir / "snapshots"),
                },
            }
        ),
        encoding="utf-8",
    )
    cycle_run_name = "r105-btcusdt-durable-public-archive-candidate-depth-v1"
    current_cycle_dir = (
        research_dir
        / "operator_runs"
        / "historical_cycles"
        / cycle_run_name
        / "run-historical-research-cycle-migrated"
    )
    stale_cycle_dir = (
        Path(r"C:\Users\papaa\Music\tradingbotsuite\data\research\operator_runs\historical_cycles")
        / cycle_run_name
        / current_cycle_dir.name
    )
    current_cycle_dir.mkdir(parents=True)
    ablation_report = current_cycle_dir / "ablation_report.json"
    ablation_report.write_text(
        json.dumps({"research_only": True, "observe_only": True, "promotion_ready": False}),
        encoding="utf-8",
    )
    cycle_manifest = current_cycle_dir / "research_cycle_manifest.json"
    cycle_manifest.write_text(
        json.dumps(
            {
                "cycle_id": cycle_run_name,
                "symbol": "BTCUSDT",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "required_outputs": {
                    "ablation_report": str(stale_cycle_dir / "ablation_report.json"),
                },
            }
        ),
        encoding="utf-8",
    )
    observed: dict[str, object] = {}

    def fake_evaluate_discovery_candidate_pack_eligibility(**kwargs):
        observed.update(kwargs)
        return SimpleNamespace(
            eligibility=pd.DataFrame([{"eligible_for_existing_candidate_pack_validator": False}]),
        )

    def fake_write_discovery_candidate_pack_eligibility(*, output_dir, result):
        output = Path(output_dir)
        output.mkdir(parents=True)
        manifest_path = output / "candidate_pack_eligibility_manifest.json"
        eligibility_path = output / "candidate_pack_eligibility.parquet"
        rejections_path = output / "candidate_pack_bridge_rejections.md"
        manifest_path.write_text("{}", encoding="utf-8")
        result.eligibility.to_parquet(eligibility_path)
        rejections_path.write_text("", encoding="utf-8")
        return SimpleNamespace(
            output_dir=output,
            manifest_path=manifest_path,
            eligibility_path=eligibility_path,
            rejections_path=rejections_path,
        )

    monkeypatch.setattr(
        "tradingbotsuite.operator_console.evaluate_discovery_candidate_pack_eligibility",
        fake_evaluate_discovery_candidate_pack_eligibility,
    )
    monkeypatch.setattr(
        "tradingbotsuite.operator_console.write_discovery_candidate_pack_eligibility",
        fake_write_discovery_candidate_pack_eligibility,
    )
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_candidate_eligibility_migrated_outputs.sqlite3",
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

    result = app.state.operator_service._run_isolated_discovery_candidate_pack_eligibility(
        {"discovery_manifest_path": str(discovery_manifest), "cycle_manifest_path": str(cycle_manifest)},
        "candidate-eligibility-migrated-output",
    )

    assert result["row_count"] == 1
    assert observed["discovery_manifest_path"] == discovery_manifest.resolve()
    assert observed["cycle_manifest_path"] == cycle_manifest.resolve()


def test_operator_candidate_eligibility_service_rejects_mixed_symbol_inputs(
    app_config,
    sample_bars,
    tmp_path,
) -> None:
    research_dir = tmp_path / "research"
    discovery_manifest = research_dir / "discovery_runs" / "exact_entry_sweep_btcusdt_candidate_depth_v1" / "discovery_run_manifest.json"
    exit_lab_manifest = research_dir / "operator_runs" / "frozen_entry_exit_lab" / "eth" / "discovery_exit_lab_manifest.json"
    discovery_manifest.parent.mkdir(parents=True)
    exit_lab_manifest.parent.mkdir(parents=True)
    discovery_manifest.write_text(
        json.dumps(
            {
                "run_id": "exact_entry_sweep_btcusdt_candidate_depth_v1",
                "symbol": "BTCUSDT",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "required_outputs": {},
            }
        ),
        encoding="utf-8",
    )
    exit_lab_manifest.write_text(
        json.dumps(
            {
                "exit_lab_version": "discovery-exit-lab-v1",
                "symbol": "ETHUSDT",
                "source_discovery_manifest_path": str(
                    research_dir / "discovery_runs" / "exact_entry_sweep_ethusdt_candidate_depth_v1" / "discovery_run_manifest.json"
                ),
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "required_outputs": {},
            }
        ),
        encoding="utf-8",
    )
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_candidate_eligibility_mixed_symbol.sqlite3",
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

    with pytest.raises(ValueError, match="same symbol"):
        app.state.operator_service._run_isolated_discovery_candidate_pack_eligibility(
            {
                "discovery_manifest_path": str(discovery_manifest),
                "exit_lab_manifest_path": str(exit_lab_manifest),
            },
            "candidate-eligibility-mixed-symbol",
        )


def test_operator_candidate_eligibility_completion_rejects_malformed_manifest(
    app_config,
    sample_bars,
    tmp_path,
) -> None:
    research_dir = tmp_path / "research"
    output_dir = research_dir / "operator_runs" / "candidate_pack_eligibility" / "malformed"
    output_dir.mkdir(parents=True)
    eligibility_path = output_dir / "candidate_pack_eligibility.parquet"
    pd.DataFrame([{"candidate_id": "bad"}]).to_parquet(eligibility_path)
    manifest_path = output_dir / "candidate_pack_eligibility_manifest.json"
    manifest = {
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "candidate_pack_written": False,
        "required_outputs": {"candidate_pack_eligibility": str(eligibility_path)},
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_candidate_eligibility_malformed.sqlite3",
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

    status = app.state.operator_service._required_artifact_status(
        {
            "type": "candidate_pack_eligibility",
            "path": str(manifest_path),
            "manifest": manifest,
            "summary": {},
        },
        "candidate_eligibility",
        None,
    )

    assert status["complete"] is False
    assert "discovery_candidate_pack_bridge_version_required" in status["blockers"]
    assert "eligibility_artifact_version_required" in status["blockers"]


def test_operator_research_analysis_route_requires_research_root_paths(app_config, sample_bars, tmp_path) -> None:
    research_dir = tmp_path / "research"
    research_dir.mkdir()
    outside_manifest = tmp_path / "outside_discovery_run_manifest.json"
    outside_manifest.write_text("{}", encoding="utf-8")
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_analysis_reject.sqlite3",
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
        csrf_token = _login(client, "operator-secret")
        response = client.post(
            "/api/operator/research/jobs/analyze-research-results",
            json={"discovery_manifest_path": str(outside_manifest)},
            headers={"X-CSRF-Token": csrf_token},
        )

    assert response.status_code == 400
    assert "must be inside the research output directory" in response.text


def test_operator_research_delta_and_exit_lab_routes_require_research_root_paths(app_config, sample_bars, tmp_path) -> None:
    research_dir = tmp_path / "research"
    research_dir.mkdir()
    outside_analysis = tmp_path / "research_analysis.json"
    outside_discovery = tmp_path / "discovery_run_manifest.json"
    outside_analysis.write_text("{}", encoding="utf-8")
    outside_discovery.write_text("{}", encoding="utf-8")
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_delta_exit_lab_reject.sqlite3",
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
        csrf_token = _login(client, "operator-secret")
        delta_response = client.post(
            "/api/operator/research/jobs/analyze-research-delta",
            json={"current_analysis_path": str(outside_analysis)},
            headers={"X-CSRF-Token": csrf_token},
        )
        exit_lab_response = client.post(
            "/api/operator/research/jobs/run-frozen-entry-exit-lab",
            json={"discovery_manifest_path": str(outside_discovery)},
            headers={"X-CSRF-Token": csrf_token},
        )

    assert delta_response.status_code == 400
    assert "must be inside the research output directory" in delta_response.text
    assert exit_lab_response.status_code == 400
    assert "must be inside the research output directory" in exit_lab_response.text


def test_operator_research_analysis_job_queues_completes_and_lists_artifact(
    app_config,
    sample_bars,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("TBS_SERVER_MONITOR_POLL_SECONDS", "3600")
    research_dir = tmp_path / "research"
    _write_completed_catalog_fixture(research_dir, write_artifacts=True)
    cycle_manifest = (
        research_dir
        / "historical_cycles"
        / "r105_btcusdt_durable_public_archive_candidate_depth_v1"
        / "research_cycle_manifest.json"
    )
    discovery_manifest = (
        research_dir
        / "discovery_runs"
        / "exact_entry_sweep_btcusdt_candidate_depth_v1"
        / "discovery_run_manifest.json"
    )
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_analysis.sqlite3",
            webhook=app_config.webhook,
            strategy=app_config.strategy,
            binance=app_config.binance,
            hyperliquid=app_config.hyperliquid,
            research=replace(app_config.research, output_dir=research_dir),
            operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
        )
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)

    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        response = client.post(
            "/api/operator/research/jobs/analyze-research-results",
            json={
                "cycle_manifest_path": str(cycle_manifest),
                "discovery_manifest_path": str(discovery_manifest),
                "include_trade_sortino": False,
            },
            headers={"X-CSRF-Token": csrf_token},
        )
        job = _wait_for_job(client, response.json()["job_id"])
        artifacts = client.get("/api/operator/research/artifacts").json()["items"]
        progress = client.get("/api/operator/research/progress").json()

    assert response.status_code == 200
    assert job["status"] == "succeeded"
    assert Path(str(job["result"]["research_analysis_path"])).exists()
    assert Path(str(job["result"]["research_analysis_markdown_path"])).exists()
    assert job["result"]["research_only"] is True
    assert job["result"]["observe_only"] is True
    assert job["result"]["promotion_ready"] is False

    analysis = next(item for item in artifacts if item["type"] == "research_analysis")
    assert analysis["summary"]["cycle_available"] is True
    assert analysis["summary"]["discovery_available"] is True
    assert analysis["summary"]["promotion_ready"] is False
    assert analysis["markdown_path"].endswith("research_analysis.md")

    by_key = {item["key"]: item for item in progress["milestones"]}
    assert by_key["research_analysis"]["status"] == "complete"
    assert by_key["research_analysis_delta"]["status"] == "ready"
    assert by_key["frozen_entry_exit_lab"]["status"] == "waiting"
    assert by_key["candidate_eligibility"]["status"] == "waiting"


def test_operator_delta_and_frozen_exit_lab_jobs_queue_complete_and_list_artifacts(
    app_config,
    sample_bars,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("TBS_SERVER_MONITOR_POLL_SECONDS", "3600")
    research_dir = tmp_path / "research"
    _write_completed_catalog_fixture(research_dir, write_artifacts=True)
    cycle_manifest = (
        research_dir
        / "historical_cycles"
        / "r105_btcusdt_durable_public_archive_candidate_depth_v1"
        / "research_cycle_manifest.json"
    )
    discovery_manifest = (
        research_dir
        / "discovery_runs"
        / "exact_entry_sweep_btcusdt_candidate_depth_v1"
        / "discovery_run_manifest.json"
    )
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_delta_exit_lab.sqlite3",
            webhook=app_config.webhook,
            strategy=app_config.strategy,
            binance=app_config.binance,
            hyperliquid=app_config.hyperliquid,
            research=replace(app_config.research, output_dir=research_dir),
            operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
        )
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)

    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        analysis_response = client.post(
            "/api/operator/research/jobs/analyze-research-results",
            json={
                "cycle_manifest_path": str(cycle_manifest),
                "discovery_manifest_path": str(discovery_manifest),
                "include_trade_sortino": False,
            },
            headers={"X-CSRF-Token": csrf_token},
        )
        analysis_job = _wait_for_job(client, analysis_response.json()["job_id"])
        delta_response = client.post(
            "/api/operator/research/jobs/analyze-research-delta",
            json={"current_analysis_path": analysis_job["result"]["research_analysis_path"]},
            headers={"X-CSRF-Token": csrf_token},
        )
        delta_job = _wait_for_job(client, delta_response.json()["job_id"])
        exit_lab_response = client.post(
            "/api/operator/research/jobs/run-frozen-entry-exit-lab",
            json={"discovery_manifest_path": str(discovery_manifest)},
            headers={"X-CSRF-Token": csrf_token},
        )
        exit_lab_job = _wait_for_job(client, exit_lab_response.json()["job_id"])
        artifacts = client.get("/api/operator/research/artifacts").json()["items"]
        progress = client.get("/api/operator/research/progress").json()

    assert delta_response.status_code == 200
    assert delta_job["status"] == "succeeded"
    assert Path(str(delta_job["result"]["research_analysis_delta_path"])).exists()
    assert delta_job["result"]["research_only"] is True
    assert delta_job["result"]["promotion_ready"] is False
    assert exit_lab_response.status_code == 200
    assert exit_lab_job["status"] == "succeeded"
    assert Path(str(exit_lab_job["result"]["exit_lab_manifest_path"])).exists()
    assert exit_lab_job["result"]["blocked_reason"] == "interesting_candidates_missing"
    assert any(item["type"] == "research_analysis_delta" for item in artifacts)
    assert any(item["type"] == "discovery_exit_lab" for item in artifacts)
    by_key = {item["key"]: item for item in progress["milestones"]}
    assert by_key["research_analysis_delta"]["status"] == "complete"
    assert by_key["frozen_entry_exit_lab"]["status"] == "complete"
    assert by_key["candidate_eligibility"]["status"] == "ready"


def test_operator_research_autopilot_blocks_when_catalog_missing_without_refresh(
    app_config,
    sample_bars,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("TBS_SERVER_MONITOR_POLL_SECONDS", "3600")
    research_dir = tmp_path / "research"
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_autopilot_blocked.sqlite3",
            webhook=app_config.webhook,
            strategy=app_config.strategy,
            binance=app_config.binance,
            hyperliquid=app_config.hyperliquid,
            research=replace(app_config.research, output_dir=research_dir),
            operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
        )
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)

    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        response = client.post(
            "/api/operator/research/jobs/run-research-autopilot",
            json={"symbols": ["BTCUSDT"], "include_catalog_refresh": False},
            headers={"X-CSRF-Token": csrf_token},
        )
        job = _wait_for_job(client, response.json()["job_id"])
        artifacts = client.get("/api/operator/research/artifacts").json()["items"]

    assert response.status_code == 200
    assert job["status"] == "succeeded"
    assert job["result"]["autopilot_status"] == "blocked"
    assert job["result"]["blocked_reason"] == "historical_data_catalog_not_ready"
    manifest = json.loads(Path(str(job["result"]["research_autopilot_manifest_path"])).read_text(encoding="utf-8"))
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["autopilot_status"] == "blocked"
    autopilot = next(item for item in artifacts if item["type"] == "research_autopilot")
    assert autopilot["summary"]["autopilot_status"] == "blocked"


def test_operator_research_artifacts_marks_stale_running_autopilot_manifest(
    app_config,
    sample_bars,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("TBS_SERVER_MONITOR_POLL_SECONDS", "3600")
    research_dir = tmp_path / "research"
    manifest_dir = research_dir / "operator_runs" / "research_autopilot" / "run-research-autopilot-stale"
    manifest_dir.mkdir(parents=True)
    updated_at = datetime.now(timezone.utc) - timedelta(hours=1)
    (manifest_dir / "research_autopilot_manifest.json").write_text(
        json.dumps(
            {
                "autopilot_version": "r106-research-autopilot-v1",
                "autopilot_status": "running",
                "job_id": "run-research-autopilot-stale",
                "requested_symbols": ["BTCUSDT", "ETHUSDT"],
                "executed_step_count": 0,
                "max_steps": 100,
                "steps": [
                    {
                        "key": "historical_data_catalog",
                        "status": "skipped",
                        "detail": "candidate-depth catalog already ready",
                        "time_utc": updated_at.isoformat(),
                    }
                ],
                "updated_at_utc": updated_at.isoformat(),
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
            }
        ),
        encoding="utf-8",
    )
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_autopilot_stale_manifest.sqlite3",
            webhook=app_config.webhook,
            strategy=app_config.strategy,
            binance=app_config.binance,
            hyperliquid=app_config.hyperliquid,
            research=replace(app_config.research, output_dir=research_dir),
            operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
        )
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)

    with TestClient(app) as client:
        _login(client, "operator-secret")
        artifacts = client.get("/api/operator/research/artifacts").json()["items"]

    autopilot = next(item for item in artifacts if item["type"] == "research_autopilot")
    assert autopilot["summary"]["autopilot_status"] == "running"
    assert autopilot["summary"]["telemetry_status"] == "running_without_active_step_telemetry"
    assert autopilot["summary"]["stale_review"] is True
    assert autopilot["summary"]["stale_review_reason"] == "manifest_status_running_without_recent_active_step_update"
    assert autopilot["summary"]["latest_step"]["key"] == "historical_data_catalog"
    assert autopilot["summary"]["last_update_age_seconds"] >= 900


def test_operator_research_progress_reports_active_autopilot_step(
    app_config,
    sample_bars,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("TBS_SERVER_MONITOR_POLL_SECONDS", "3600")
    research_dir = tmp_path / "research"
    _write_completed_catalog_fixture(research_dir, write_artifacts=True)
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_autopilot_active_step.sqlite3",
            webhook=app_config.webhook,
            strategy=app_config.strategy,
            binance=app_config.binance,
            hyperliquid=app_config.hyperliquid,
            research=replace(app_config.research, output_dir=research_dir),
            operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
        )
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    analysis_started = Event()
    release_analysis = Event()

    def slow_analysis(request: dict[str, object], job_id: str) -> dict[str, object]:
        analysis_started.set()
        if not release_analysis.wait(10):
            raise RuntimeError("test timed out waiting to release analysis")
        output_dir = research_dir / "operator_runs" / "analysis" / job_id
        output_dir.mkdir(parents=True)
        manifest_path = output_dir / "research_analysis.json"
        markdown_path = output_dir / "research_analysis.md"
        manifest_path.write_text(
            json.dumps(
                {
                    "analysis_version": "research-analysis-v1",
                    "research_only": True,
                    "observe_only": True,
                    "promotion_ready": False,
                    "cycle": {"available": True, "manifest": {"symbol": "BTCUSDT", "cycle_id": "cycle-btcusdt"}},
                    "discovery": {
                        "available": True,
                        "symbol": "BTCUSDT",
                        "run_id": "exact_entry_sweep_btcusdt_candidate_depth_v1",
                    },
                }
            ),
            encoding="utf-8",
        )
        markdown_path.write_text("analysis\n", encoding="utf-8")
        return {"research_analysis_path": str(manifest_path), "research_analysis_markdown_path": str(markdown_path)}

    app.state.operator_service._run_isolated_research_analysis = slow_analysis

    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        response = client.post(
            "/api/operator/research/jobs/run-research-autopilot",
            json={"symbols": ["BTCUSDT"], "include_catalog_refresh": False, "include_eligibility": False, "max_steps": 1},
            headers={"X-CSRF-Token": csrf_token},
        )
        job_id = response.json()["job_id"]
        assert analysis_started.wait(10)
        progress = None
        for _ in range(50):
            payload = client.get("/api/operator/research/progress").json()
            active = payload.get("active_autopilot_progress") or {}
            current = active.get("current_step") or {}
            if current.get("key") == "research_analysis":
                progress = active
                break
            time.sleep(0.05)
        assert progress is not None
        assert progress["telemetry_status"] == "active_step_recorded"
        assert progress["current_step"]["symbol"] == "BTCUSDT"
        assert progress["current_step"]["attempt"] == 1
        assert progress["eta_seconds"] is not None
        assert progress["manifest_path"]

        manifest = json.loads(Path(str(progress["manifest_path"])).read_text(encoding="utf-8"))
        assert manifest["active_step"]["key"] == "research_analysis"
        release_analysis.set()
        job = _wait_for_job(client, job_id)

    assert response.status_code == 200
    assert job["status"] == "succeeded"
    assert job["result"]["autopilot_status"] == "blocked"
    assert job["result"]["blocked_reason"] == "autopilot_step_limit_reached"
    manifest = json.loads(Path(str(job["result"]["research_autopilot_manifest_path"])).read_text(encoding="utf-8"))
    assert manifest["active_step"] is None
    assert ("research_analysis", "executed") in {(step["key"], step["status"]) for step in manifest["steps"]}


def test_operator_research_autopilot_reuses_completed_outputs_and_runs_analysis_and_eligibility(
    app_config,
    sample_bars,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("TBS_SERVER_MONITOR_POLL_SECONDS", "3600")
    research_dir = tmp_path / "research"
    _write_completed_catalog_fixture(research_dir, write_artifacts=True)
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_autopilot.sqlite3",
            webhook=app_config.webhook,
            strategy=app_config.strategy,
            binance=app_config.binance,
            hyperliquid=app_config.hyperliquid,
            research=replace(app_config.research, output_dir=research_dir),
            operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
        )
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)

    def fake_eligibility(request: dict[str, object], job_id: str) -> dict[str, object]:
        assert request.get("exit_lab_manifest_path")
        output_dir = research_dir / "operator_runs" / "candidate_pack_eligibility" / job_id
        output_dir.mkdir(parents=True)
        eligibility_path = output_dir / "candidate_pack_eligibility.parquet"
        pd.DataFrame(
            [
                {
                    "candidate_id": "blocked-candidate",
                    "eligible_for_existing_candidate_pack_validator": False,
                    "reasons": "test_fixture_blocks_candidate_pack",
                }
            ]
        ).to_parquet(eligibility_path)
        rejections_path = output_dir / "candidate_pack_bridge_rejections.md"
        rejections_path.write_text("blocked\n", encoding="utf-8")
        discovery_manifest = Path(str(request.get("discovery_manifest_path")))
        cycle_manifest = Path(str(request.get("cycle_manifest_path")))
        manifest_path = output_dir / "candidate_pack_eligibility_manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "discovery_candidate_pack_bridge_version": DISCOVERY_CANDIDATE_PACK_BRIDGE_VERSION,
                    "eligibility_artifact_version": DISCOVERY_CANDIDATE_PACK_ELIGIBILITY_VERSION,
                    "bridge_scope": "discovery_to_existing_research_candidate_pack_validator_eligibility_only",
                    "claim_scope": "audit_only_no_pack_write_no_live_or_promotion_claim",
                    "research_only": True,
                    "observe_only": True,
                    "promotion_ready": False,
                    "live_signal_input": False,
                    "position_sizing_input": False,
                    "operator_control_input": False,
                    "live_execution_input": False,
                    "runtime_control_input": False,
                    "live_fetch_used": False,
                    "order_placement_used": False,
                    "runtime_mode_changed": False,
                    "exit_lab_gate_required": True,
                    "multiple_testing_gate_required": True,
                    "validation_floor_gate_required": True,
                    "candidate_pack_written": False,
                    "candidate_pack_paths": [],
                    "source_discovery_manifest_path": request.get("discovery_manifest_path"),
                    "source_discovery_manifest_sha256": hashlib.sha256(discovery_manifest.read_bytes()).hexdigest(),
                    "source_cycle_manifest_path": request.get("cycle_manifest_path"),
                    "source_cycle_manifest_sha256": hashlib.sha256(cycle_manifest.read_bytes()).hexdigest(),
                    "required_outputs": {
                        "candidate_pack_eligibility_manifest": str(manifest_path),
                        "candidate_pack_eligibility": str(eligibility_path),
                        "candidate_pack_bridge_rejections": str(rejections_path),
                    },
                    "candidate_pack_eligibility_sha256": hashlib.sha256(eligibility_path.read_bytes()).hexdigest(),
                    "candidate_pack_bridge_rejections_sha256": hashlib.sha256(rejections_path.read_bytes()).hexdigest(),
                    "summary": {"candidate_count": 1, "eligible_count": 0, "blocked_count": 1},
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return {
            "output_dir": str(output_dir),
            "candidate_pack_eligibility_manifest_path": str(manifest_path),
            "candidate_pack_eligibility_path": str(eligibility_path),
            "eligible_count": 0,
            "row_count": 1,
            "candidate_pack_written": False,
            "promotion_ready": False,
            "research_only": True,
            "observe_only": True,
        }

    app.state.operator_service._run_isolated_discovery_candidate_pack_eligibility = fake_eligibility

    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        response = client.post(
            "/api/operator/research/jobs/run-research-autopilot",
            json={"symbols": ["BTCUSDT"], "include_catalog_refresh": False, "include_eligibility": True},
            headers={"X-CSRF-Token": csrf_token},
        )
        job = _wait_for_job(client, response.json()["job_id"])
        artifacts = client.get("/api/operator/research/artifacts").json()["items"]

    assert response.status_code == 200
    assert job["status"] == "succeeded"
    assert job["result"]["autopilot_status"] == "completed"
    assert job["result"]["executed_step_count"] == 4
    manifest = json.loads(Path(str(job["result"]["research_autopilot_manifest_path"])).read_text(encoding="utf-8"))
    statuses = {(step["key"], step["status"]) for step in manifest["steps"]}
    assert ("historical_data_catalog", "skipped") in statuses
    assert ("historical_cycle", "skipped") in statuses
    assert ("exact_discovery", "skipped") in statuses
    assert ("research_analysis", "executed") in statuses
    assert ("research_analysis_delta", "executed") in statuses
    assert ("frozen_entry_exit_lab", "executed") in statuses
    assert ("candidate_eligibility", "executed") in statuses
    assert any(item["type"] == "research_autopilot" for item in artifacts)
    assert any(item["type"] == "research_analysis" for item in artifacts)
    assert any(item["type"] == "research_analysis_delta" for item in artifacts)
    assert any(item["type"] == "discovery_exit_lab" for item in artifacts)
    assert any(item["type"] == "candidate_pack_eligibility" for item in artifacts)


def test_operator_research_autopilot_retries_failed_step_with_new_attempt_job_id(
    app_config,
    sample_bars,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("TBS_SERVER_MONITOR_POLL_SECONDS", "3600")
    research_dir = tmp_path / "research"
    _write_completed_catalog_fixture(research_dir, write_artifacts=True)
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_autopilot_retry.sqlite3",
            webhook=app_config.webhook,
            strategy=app_config.strategy,
            binance=app_config.binance,
            hyperliquid=app_config.hyperliquid,
            research=replace(app_config.research, output_dir=research_dir),
            operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
        )
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    analysis_job_ids: list[str] = []

    def flaky_analysis(request: dict[str, object], job_id: str) -> dict[str, object]:
        analysis_job_ids.append(job_id)
        output_dir = research_dir / "operator_runs" / "analysis" / job_id
        output_dir.mkdir(parents=True)
        (output_dir / "partial_attempt_marker.txt").write_text("attempt\n", encoding="utf-8")
        if len(analysis_job_ids) == 1:
            raise RuntimeError("transient analysis failure")
        manifest_path = output_dir / "research_analysis.json"
        markdown_path = output_dir / "research_analysis.md"
        manifest_path.write_text(
            json.dumps(
                {
                    "analysis_version": "research-analysis-v1",
                    "research_only": True,
                    "observe_only": True,
                    "promotion_ready": False,
                    "cycle": {"available": True, "manifest": {"symbol": "BTCUSDT", "cycle_id": "cycle-btcusdt"}},
                    "discovery": {"available": True, "symbol": "BTCUSDT", "run_id": "exact_entry_sweep_btcusdt_candidate_depth_v1"},
                }
            ),
            encoding="utf-8",
        )
        markdown_path.write_text("analysis\n", encoding="utf-8")
        return {"research_analysis_path": str(manifest_path), "research_analysis_markdown_path": str(markdown_path)}

    def write_delta(request: dict[str, object], job_id: str) -> dict[str, object]:
        output_dir = research_dir / "operator_runs" / "analysis_deltas" / job_id
        output_dir.mkdir(parents=True)
        manifest_path = output_dir / "research_analysis_delta.json"
        markdown_path = output_dir / "research_analysis_delta.md"
        manifest_path.write_text(
            json.dumps(
                {
                    "delta_version": "research-discovery-analysis-delta-v1",
                    "research_only": True,
                    "observe_only": True,
                    "promotion_ready": False,
                    "current": {"analysis_path": request.get("current_analysis_path"), "symbol": "BTCUSDT"},
                    "comparison_scope": {"compatible": True, "blocked_reasons": []},
                }
            ),
            encoding="utf-8",
        )
        markdown_path.write_text("delta\n", encoding="utf-8")
        return {"research_analysis_delta_path": str(manifest_path), "research_analysis_delta_markdown_path": str(markdown_path)}

    def write_exit_lab(request: dict[str, object], job_id: str) -> dict[str, object]:
        _ = request
        output_dir = research_dir / "operator_runs" / "frozen_entry_exit_lab" / job_id
        output_dir.mkdir(parents=True)
        gates_path = output_dir / "frozen_entry_exit_lab_candidate_gates.parquet"
        pd.DataFrame([{"candidate_id": "blocked-candidate", "exit_lab_gate_status": "blocked"}]).to_parquet(gates_path)
        manifest_path = output_dir / "discovery_exit_lab_manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "exit_lab_version": "discovery-exit-lab-v1",
                    "exit_lab_scope": "frozen_entry_primary_bar_exit_comparison",
                    "symbol": "BTCUSDT",
                    "research_only": True,
                    "observe_only": True,
                    "promotion_ready": False,
                    "required_outputs": {"discovery_exit_lab_candidate_gates": str(gates_path)},
                }
            ),
            encoding="utf-8",
        )
        return {"exit_lab_manifest_path": str(manifest_path), "research_only": True, "observe_only": True, "promotion_ready": False}

    app.state.operator_service._run_isolated_research_analysis = flaky_analysis
    app.state.operator_service._run_isolated_research_analysis_delta = write_delta
    app.state.operator_service._run_isolated_frozen_entry_exit_lab = write_exit_lab

    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        response = client.post(
            "/api/operator/research/jobs/run-research-autopilot",
            json={"symbols": ["BTCUSDT"], "include_catalog_refresh": False, "include_eligibility": False},
            headers={"X-CSRF-Token": csrf_token},
        )
        job_id = response.json()["job_id"]
        job = _wait_for_job(client, job_id)

    assert response.status_code == 200
    assert job["status"] == "succeeded"
    assert analysis_job_ids == [f"{job_id}-btcusdt-analysis", f"{job_id}-btcusdt-analysis-retry-2"]
    manifest = json.loads(
        (research_dir / "operator_runs" / "research_autopilot" / job_id / "research_autopilot_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    retry_step = next(step for step in manifest["steps"] if step["key"] == "research_analysis" and step["status"] == "retrying")
    executed_step = next(step for step in manifest["steps"] if step["key"] == "research_analysis" and step["status"] == "executed")
    assert retry_step["attempt"] == 1
    assert executed_step["attempt"] == 2
    assert executed_step["attempt_job_id"].endswith("-retry-2")


def test_operator_research_autopilot_fails_after_retry_exhaustion(
    app_config,
    sample_bars,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("TBS_SERVER_MONITOR_POLL_SECONDS", "3600")
    research_dir = tmp_path / "research"
    _write_completed_catalog_fixture(research_dir, write_artifacts=True)
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_autopilot_retry_exhausted.sqlite3",
            webhook=app_config.webhook,
            strategy=app_config.strategy,
            binance=app_config.binance,
            hyperliquid=app_config.hyperliquid,
            research=replace(app_config.research, output_dir=research_dir),
            operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
        )
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    analysis_job_ids: list[str] = []

    def failing_analysis(request: dict[str, object], job_id: str) -> dict[str, object]:
        _ = request
        analysis_job_ids.append(job_id)
        output_dir = research_dir / "operator_runs" / "analysis" / job_id
        output_dir.mkdir(parents=True)
        (output_dir / "partial_attempt_marker.txt").write_text("attempt\n", encoding="utf-8")
        raise RuntimeError("persistent analysis failure")

    app.state.operator_service._run_isolated_research_analysis = failing_analysis

    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        response = client.post(
            "/api/operator/research/jobs/run-research-autopilot",
            json={"symbols": ["BTCUSDT"], "include_catalog_refresh": False, "include_eligibility": False},
            headers={"X-CSRF-Token": csrf_token},
        )
        job_id = response.json()["job_id"]
        job = _wait_for_job(client, job_id)

    assert response.status_code == 200
    assert job["status"] == "failed"
    assert job["error_text"] == "persistent analysis failure"
    assert analysis_job_ids == [f"{job_id}-btcusdt-analysis", f"{job_id}-btcusdt-analysis-retry-2"]
    manifest = json.loads(
        (research_dir / "operator_runs" / "research_autopilot" / job_id / "research_autopilot_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["autopilot_status"] == "failed"
    retry_step = next(step for step in manifest["steps"] if step["key"] == "research_analysis" and step["status"] == "retrying")
    failed_step = next(step for step in manifest["steps"] if step["key"] == "research_analysis" and step["status"] == "failed")
    assert retry_step["attempt"] == 1
    assert failed_step["attempt"] == 2
    assert failed_step["attempt_job_id"].endswith("-retry-2")


def test_operator_research_autopilot_completes_all_discoveries_before_eligibility(
    app_config,
    sample_bars,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("TBS_SERVER_MONITOR_POLL_SECONDS", "3600")
    research_dir = tmp_path / "research"
    _write_completed_catalog_fixture(research_dir, write_artifacts=False)
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_autopilot_two_symbol_order.sqlite3",
            webhook=app_config.webhook,
            strategy=app_config.strategy,
            binance=app_config.binance,
            hyperliquid=app_config.hyperliquid,
            research=replace(app_config.research, output_dir=research_dir),
            operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
        )
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    sequence: list[str] = []

    def safe_part(value: str) -> str:
        safe = "".join(char.lower() if char.isalnum() else "-" for char in str(value)).strip("-")
        return safe[:96] or "operator-job"

    def write_cycle(spec_path: Path, job_id: str) -> dict[str, object]:
        spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
        cycle_id = str(spec["cycle_id"])
        symbol = str(spec["symbol"])
        sequence.append(f"cycle:{symbol}")
        manifest_path = research_dir / "operator_runs" / "historical_cycles" / safe_part(cycle_id) / job_id / "research_cycle_manifest.json"
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "cycle_id": cycle_id,
                    "symbol": symbol,
                    "candidate_count": 63,
                    "research_only": True,
                    "observe_only": True,
                    "promotion_ready": False,
                    "required_outputs": {
                        "cycle_spec_resolved": "cycle_spec_resolved.json",
                        "candidate_rankings": "candidate_rankings.json",
                        "candidate_gate_report": "candidate_gate_report.parquet",
                        "backtest_index": "backtest_index.json",
                    },
                    "candidate_selection_performance_plan": {
                        "materialized_search_candidate_count": 63,
                        "bruteforce_equivalent_candidate_count": 2048,
                    },
                    "data_source": {"durable_public_archive_readiness": {"primary_bar_count": 221_952}},
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return {"cycle_manifest_path": str(manifest_path), "research_only": True, "observe_only": True, "promotion_ready": False}

    def write_discovery(
        spec_path: Path,
        job_id: str,
        resume: bool,
        stop_after_trials: int | None,
        stable_run_id: bool,
    ) -> dict[str, object]:
        _ = resume, stop_after_trials, stable_run_id
        spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
        run_id = str(spec["run_id"])
        symbol = str(spec["symbol"])
        sequence.append(f"discovery:{symbol}")
        manifest_path = research_dir / "operator_runs" / "discovery_runs" / safe_part(run_id) / job_id / "discovery_run_manifest.json"
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "symbol": symbol,
                    "research_only": True,
                    "observe_only": True,
                    "promotion_ready": False,
                    "state": {"status": "completed"},
                    "budget": {"max_trials": 570_240},
                    "search_space": {
                        "planned_trials": 570_240,
                        "exhaustive": True,
                        "sampled_fraction": 1.0,
                    },
                    "counts": {"completed_trials": 570_240},
                    "required_outputs": {
                        "discovery_spec_resolved": "discovery_spec_resolved.json",
                        "run_state": "run_state.json",
                        "blocked_candidates": "blocked_candidates.json",
                        "filter_blockers": "filter_blockers.json",
                        "snapshots": "snapshots",
                        "trials": "trials",
                    },
                    "data_evidence": {"row_count": 221_952},
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return {"manifest_path": str(manifest_path), "research_only": True, "observe_only": True, "promotion_ready": False}

    def symbol_from_request(request: dict[str, object]) -> str:
        text = json.dumps(request).lower()
        return "ETHUSDT" if "ethusdt" in text else "BTCUSDT"

    def write_analysis(request: dict[str, object], job_id: str) -> dict[str, object]:
        symbol = symbol_from_request(request)
        sequence.append(f"analysis:{symbol}")
        manifest_path = research_dir / "operator_runs" / "analysis" / job_id / "research_analysis.json"
        markdown_path = manifest_path.with_suffix(".md")
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "analysis_version": "research-analysis-v1",
                    "research_only": True,
                    "observe_only": True,
                    "promotion_ready": False,
                    "cycle": {"available": True, "manifest": {"symbol": symbol, "cycle_id": f"cycle-{symbol.lower()}"}},
                    "discovery": {"available": True, "symbol": symbol, "run_id": f"run-{symbol.lower()}"},
                }
            ),
            encoding="utf-8",
        )
        markdown_path.write_text("analysis\n", encoding="utf-8")
        return {"research_analysis_path": str(manifest_path), "research_analysis_markdown_path": str(markdown_path)}

    def write_delta(request: dict[str, object], job_id: str) -> dict[str, object]:
        symbol = symbol_from_request(request)
        sequence.append(f"delta:{symbol}")
        manifest_path = research_dir / "operator_runs" / "analysis_deltas" / job_id / "research_analysis_delta.json"
        markdown_path = manifest_path.with_suffix(".md")
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "delta_version": "research-discovery-analysis-delta-v1",
                    "research_only": True,
                    "observe_only": True,
                    "promotion_ready": False,
                    "current": {"analysis_path": request.get("current_analysis_path"), "symbol": symbol},
                    "previous": {},
                    "comparison_scope": {"compatible": True, "blocked_reasons": []},
                }
            ),
            encoding="utf-8",
        )
        markdown_path.write_text("delta\n", encoding="utf-8")
        return {"research_analysis_delta_path": str(manifest_path), "research_analysis_delta_markdown_path": str(markdown_path)}

    def write_exit_lab(request: dict[str, object], job_id: str) -> dict[str, object]:
        symbol = symbol_from_request(request)
        sequence.append(f"exit_lab:{symbol}")
        output_dir = research_dir / "operator_runs" / "frozen_entry_exit_lab" / job_id
        output_dir.mkdir(parents=True)
        gates_path = output_dir / "frozen_entry_exit_lab_candidate_gates.parquet"
        pd.DataFrame([{"candidate_id": f"candidate-{symbol.lower()}", "exit_lab_gate_status": "blocked"}]).to_parquet(gates_path)
        manifest_path = output_dir / "discovery_exit_lab_manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "exit_lab_version": "discovery-exit-lab-v1",
                    "exit_lab_scope": "frozen_entry_primary_bar_exit_comparison",
                    "symbol": symbol,
                    "research_only": True,
                    "observe_only": True,
                    "promotion_ready": False,
                    "required_outputs": {"discovery_exit_lab_candidate_gates": str(gates_path)},
                }
            ),
            encoding="utf-8",
        )
        return {"exit_lab_manifest_path": str(manifest_path), "research_only": True, "observe_only": True, "promotion_ready": False}

    def write_eligibility(request: dict[str, object], job_id: str) -> dict[str, object]:
        symbol = symbol_from_request(request)
        sequence.append(f"eligibility:{symbol}")
        output_dir = research_dir / "operator_runs" / "candidate_pack_eligibility" / job_id
        output_dir.mkdir(parents=True)
        eligibility_path = output_dir / "candidate_pack_eligibility.parquet"
        rejections_path = output_dir / "candidate_pack_bridge_rejections.md"
        pd.DataFrame([{"candidate_id": f"candidate-{symbol.lower()}", "eligible_for_existing_candidate_pack_validator": False}]).to_parquet(eligibility_path)
        rejections_path.write_text("blocked\n", encoding="utf-8")
        discovery_manifest = Path(str(request.get("discovery_manifest_path")))
        cycle_manifest = Path(str(request.get("cycle_manifest_path")))
        manifest_path = output_dir / "candidate_pack_eligibility_manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "discovery_candidate_pack_bridge_version": DISCOVERY_CANDIDATE_PACK_BRIDGE_VERSION,
                    "eligibility_artifact_version": DISCOVERY_CANDIDATE_PACK_ELIGIBILITY_VERSION,
                    "bridge_scope": "discovery_to_existing_research_candidate_pack_validator_eligibility_only",
                    "research_only": True,
                    "observe_only": True,
                    "promotion_ready": False,
                    "live_signal_input": False,
                    "position_sizing_input": False,
                    "operator_control_input": False,
                    "live_execution_input": False,
                    "runtime_control_input": False,
                    "live_fetch_used": False,
                    "order_placement_used": False,
                    "runtime_mode_changed": False,
                    "exit_lab_gate_required": True,
                    "multiple_testing_gate_required": True,
                    "validation_floor_gate_required": True,
                    "candidate_pack_written": False,
                    "candidate_pack_paths": [],
                    "source_discovery_manifest_path": str(discovery_manifest),
                    "source_discovery_manifest_sha256": hashlib.sha256(discovery_manifest.read_bytes()).hexdigest(),
                    "source_cycle_manifest_path": str(cycle_manifest),
                    "source_cycle_manifest_sha256": hashlib.sha256(cycle_manifest.read_bytes()).hexdigest(),
                    "required_outputs": {
                        "candidate_pack_eligibility_manifest": str(manifest_path),
                        "candidate_pack_eligibility": str(eligibility_path),
                        "candidate_pack_bridge_rejections": str(rejections_path),
                    },
                    "candidate_pack_eligibility_sha256": hashlib.sha256(eligibility_path.read_bytes()).hexdigest(),
                    "candidate_pack_bridge_rejections_sha256": hashlib.sha256(rejections_path.read_bytes()).hexdigest(),
                }
            ),
            encoding="utf-8",
        )
        return {"candidate_pack_eligibility_manifest_path": str(manifest_path), "research_only": True, "observe_only": True, "promotion_ready": False}

    app.state.operator_service._run_isolated_historical_research_cycle = write_cycle
    app.state.operator_service._run_isolated_discovery = write_discovery
    app.state.operator_service._run_isolated_research_analysis = write_analysis
    app.state.operator_service._run_isolated_research_analysis_delta = write_delta
    app.state.operator_service._run_isolated_frozen_entry_exit_lab = write_exit_lab
    app.state.operator_service._run_isolated_discovery_candidate_pack_eligibility = write_eligibility

    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        response = client.post(
            "/api/operator/research/jobs/run-research-autopilot",
            json={"symbols": ["BTCUSDT", "ETHUSDT"], "include_catalog_refresh": False, "include_eligibility": True},
            headers={"X-CSRF-Token": csrf_token},
        )
        job = _wait_for_job(client, response.json()["job_id"])

    assert response.status_code == 200
    assert job["status"] == "succeeded"
    assert job["result"]["autopilot_status"] == "completed"
    first_analysis_index = min(index for index, item in enumerate(sequence) if item.startswith("analysis:"))
    last_discovery_index = max(index for index, item in enumerate(sequence) if item.startswith("discovery:"))
    first_eligibility_index = min(index for index, item in enumerate(sequence) if item.startswith("eligibility:"))
    assert last_discovery_index < first_analysis_index < first_eligibility_index
    assert {"discovery:BTCUSDT", "discovery:ETHUSDT"} <= set(sequence[:first_analysis_index])


def test_operator_research_autopilot_rejects_live_mode(app_config, sample_bars, tmp_path, monkeypatch) -> None:
    _patch_runtime_live_adapter(monkeypatch)
    research_dir = tmp_path / "research"
    config = AppConfig(
        runtime_mode=RuntimeMode.LIVE,
        db_path=tmp_path / "operator_autopilot_live.sqlite3",
        webhook=app_config.webhook,
        strategy=replace(
            app_config.strategy,
            max_daily_loss_quote=Decimal("25"),
            max_open_risk_notional=Decimal("100"),
        ),
        binance=app_config.binance,
        hyperliquid=replace(
            app_config.hyperliquid,
            base_url="https://api.hyperliquid-testnet.xyz",
            enable_live=True,
            account_address="0x1111111111111111111111111111111111111111",
            private_key="0x" + "2" * 64,
        ),
        research=replace(app_config.research, output_dir=research_dir),
        operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    app.state.engine.execution_adapter = FakeLiveAdapter()
    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        response = client.post(
            "/api/operator/research/jobs/run-research-autopilot",
            json={"symbols": ["BTCUSDT"], "include_catalog_refresh": False},
            headers={"X-CSRF-Token": csrf_token},
        )

    assert response.status_code == 409
    assert "live mode" in response.json()["detail"]


def test_operator_stage13_readiness_api_is_read_only_blocked(app_config, sample_bars, tmp_path) -> None:
    config = _operator_config(
        AppConfig(
            runtime_mode=RuntimeMode.PAPER,
            db_path=tmp_path / "operator_stage13.sqlite3",
            webhook=app_config.webhook,
            strategy=app_config.strategy,
            binance=app_config.binance,
            hyperliquid=app_config.hyperliquid,
            research=replace(app_config.research, output_dir=tmp_path / "research"),
            operator_ui=app_config.operator_ui,
        )
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    with TestClient(app) as client:
        _login(client, "operator-secret")
        payload = client.get("/api/operator/stage13/readiness").json()

    assert payload["ready"] is False
    assert payload["blocked"] is True
    assert payload["operator_control_input"] is False
    assert payload["live_execution_input"] is False
    assert payload["runtime_control_input"] is False
    assert payload["live_canary_authorized"] is False


def test_operator_shadow_diagnostics_api_is_observe_only(app_config, sample_bars) -> None:
    config = _operator_config(app_config, mode=RuntimeMode.SHADOW)
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        signal_response = client.post(
            "/api/operator/commands/manual-signal",
            json={"symbol": "BTCUSDT", "direction": "long"},
            headers={"X-CSRF-Token": csrf_token},
        )
        diagnostics_response = client.get("/api/operator/shadow/diagnostics?symbol=BTCUSDT")

    assert signal_response.status_code == 200
    assert diagnostics_response.status_code == 200
    payload = diagnostics_response.json()
    assert payload["observe_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["live_execution_input"] is False
    assert payload["operator_control_input"] is False
    assert payload["summary"]["shadow_decision_count"] == 1
    assert payload["summary"]["skipped_count"] == 1
    assert payload["summary"]["skip_reasons"] == {"no_artifact_loaded": 1}
    assert payload["items"][0]["status"] == "skipped"
    assert payload["items"][0]["scoring_fallback_reason"] == "no_artifact_loaded"


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
    _patch_runtime_live_adapter(monkeypatch)
    config = _operator_config(app_config, mode=RuntimeMode.LIVE)
    config = AppConfig(
        runtime_mode=config.runtime_mode,
        db_path=config.db_path,
        webhook=config.webhook,
        strategy=config.strategy,
        binance=config.binance,
        hyperliquid=config.hyperliquid,
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


def test_operator_feed_derives_job_symbol_from_request_spec_path(app_config, sample_bars, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TBS_SERVER_MONITOR_POLL_SECONDS", "3600")
    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "operator_feed_job_symbols.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=app_config.research,
        operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    with TestClient(app) as client:
        _login(client, "operator-secret")
        asyncio.run(
            app.state.engine.store.queue_operator_job(
                job_id="eth-cycle-job",
                job_type="run-historical-research-cycle",
                requested_at_ms=1712665800000,
                request={"spec_path": "configs/research/full_cycle_ethusdt_durable_public_archive_r104_v1.json"},
            )
        )
        feed = client.get("/api/operator/feed?limit=20").json()

    item = next(item for item in feed["items"] if item["kind"] == "operator_job")
    assert item["symbol"] == "ETHUSDT"
    assert item["payload"]["request"]["spec_path"].endswith("ethusdt_durable_public_archive_r104_v1.json")


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


def test_operator_research_job_blocked_in_live_mode_without_position(app_config, sample_bars, tmp_path, monkeypatch) -> None:
    _patch_runtime_live_adapter(monkeypatch)
    config = AppConfig(
        runtime_mode=RuntimeMode.LIVE,
        db_path=tmp_path / "operator_live.sqlite3",
        webhook=app_config.webhook,
        strategy=replace(
            app_config.strategy,
            max_daily_loss_quote=Decimal("25"),
            max_open_risk_notional=Decimal("100"),
        ),
        binance=app_config.binance,
        hyperliquid=replace(
            app_config.hyperliquid,
            base_url="https://api.hyperliquid-testnet.xyz",
            enable_live=True,
            account_address="0x1111111111111111111111111111111111111111",
            private_key="0x" + "2" * 64,
        ),
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
        collect_response = client.post(
            "/api/operator/research/jobs/collect-durable-data",
            json={},
            headers={"X-CSRF-Token": csrf_token},
        )
        catalog_response = client.post(
            "/api/operator/research/jobs/refresh-historical-data-catalog",
            json={},
            headers={"X-CSRF-Token": csrf_token},
        )
        hardware_response = client.post(
            "/api/operator/research/jobs/benchmark-hardware-utilization",
            json={"cpu_workers": 1, "cpu_seconds": 0.5, "gpu_seconds": 0.5, "matrix_size": 64},
            headers={"X-CSRF-Token": csrf_token},
        )
    assert response.status_code == 409
    assert "live mode" in response.json()["detail"]
    assert collect_response.status_code == 409
    assert "live mode" in collect_response.json()["detail"]
    assert catalog_response.status_code == 409
    assert "live mode" in catalog_response.json()["detail"]
    assert hardware_response.status_code == 409
    assert "live mode" in hardware_response.json()["detail"]


@pytest.mark.parametrize(
    ("endpoint", "field_name"),
    [
        ("/api/operator/research/jobs/train-model", "dataset_path"),
        ("/api/operator/research/jobs/calibrate-model", "train_manifest_path"),
        ("/api/operator/research/jobs/replay-eval", "artifact_manifest_path"),
    ],
)
def test_operator_model_artifact_jobs_reject_paths_outside_research_root(
    app_config,
    sample_bars,
    tmp_path,
    endpoint: str,
    field_name: str,
) -> None:
    research_dir = tmp_path / "research"
    outside_file = tmp_path / "outside" / "artifact.json"
    outside_file.parent.mkdir(parents=True)
    outside_file.write_text("{}", encoding="utf-8")
    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / f"{field_name}.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=replace(app_config.research, output_dir=research_dir),
        operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)

    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        response = client.post(
            endpoint,
            json={field_name: str(outside_file)},
            headers={"X-CSRF-Token": csrf_token},
        )

    assert response.status_code == 400
    assert "must be inside the research output directory" in response.json()["detail"]


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


def test_operator_hardware_utilization_job_queues_completes_and_lists_artifact(
    app_config,
    sample_bars,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("TBS_SERVER_MONITOR_POLL_SECONDS", "3600")
    research_dir = tmp_path / "research"

    def fake_write_hardware_utilization_report(*, output_dir, cpu_workers, cpu_seconds, gpu_seconds, matrix_size, app_config):
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True)
        report_path = output_dir / "hardware_utilization_report.json"
        report_path.write_text(
            json.dumps(
                {
                    "hardware_utilization_report_version": "hardware-utilization-study-readiness-v1",
                    "research_only": True,
                    "observe_only": True,
                    "promotion_ready": False,
                    "cpu_probe": {
                        "probe_succeeded": True,
                        "active_workers": int(cpu_workers or 1),
                        "logical_cpu_count": 16,
                        "physical_cpu_count": 8,
                        "process_cpu_percent_of_worker_capacity": 99.0,
                        "process_cpu_percent_of_logical_capacity": 49.5,
                        "worker_capacity_saturation_status": "saturated",
                        "logical_capacity_saturation_status": "below_target",
                    },
                    "gpu_probe": {
                        "probe_succeeded": True,
                        "gpu_execution_status": "cupy_matrix_probe_executed",
                        "approx_gflops_per_second": 1200.0,
                        "runtime_evidence": {"gpu_name": "Fake CUDA GPU"},
                    },
                    "recommendations": {"best_option": "hybrid_process_pool_cpu_plus_cuda_supported_fixed_holding"},
                    "prolonged_study_readiness": {
                        "cpu_worker_saturation_target_met": True,
                        "ready_for_long_cpu_bound_research": True,
                    },
                }
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(output_dir=output_dir, report_path=report_path)

    monkeypatch.setattr(
        "tradingbotsuite.operator_console.write_hardware_utilization_report",
        fake_write_hardware_utilization_report,
    )
    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "operator_hardware.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=replace(app_config.research, output_dir=research_dir),
        operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)

    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        response = client.post(
            "/api/operator/research/jobs/benchmark-hardware-utilization",
            json={"cpu_workers": 1, "cpu_seconds": 0.1, "gpu_seconds": 0.1, "matrix_size": 64},
            headers={"X-CSRF-Token": csrf_token},
        )
        job = _wait_for_job(client, response.json()["job_id"])
        artifacts = client.get("/api/operator/research/artifacts").json()["items"]

    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    assert job["status"] == "succeeded"
    assert Path(str(job["result"]["hardware_utilization_report_path"])).exists()
    hardware = next(artifact for artifact in artifacts if artifact["type"] == "hardware_utilization")
    assert hardware["summary"]["cpu_probe_succeeded"] is True
    assert hardware["summary"]["cpu_saturation_target_met"] is True
    assert hardware["summary"]["ready_for_long_cpu_bound_research"] is True
    assert hardware["summary"]["gpu_execution_status"] == "cupy_matrix_probe_executed"
    assert hardware["summary"]["promotion_ready"] is False


def test_operator_research_experiment_rejects_live_mode(app_config, sample_bars, tmp_path, monkeypatch) -> None:
    _patch_runtime_live_adapter(monkeypatch)
    research_dir = tmp_path / "research"
    config = AppConfig(
        runtime_mode=RuntimeMode.LIVE,
        db_path=tmp_path / "operator_experiment_live.sqlite3",
        webhook=app_config.webhook,
        strategy=replace(
            app_config.strategy,
            max_daily_loss_quote=Decimal("25"),
            max_open_risk_notional=Decimal("100"),
        ),
        binance=app_config.binance,
        hyperliquid=replace(
            app_config.hyperliquid,
            base_url="https://api.hyperliquid-testnet.xyz",
            enable_live=True,
            account_address="0x1111111111111111111111111111111111111111",
            private_key="0x" + "2" * 64,
        ),
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


def test_operator_historical_cycle_job_writes_isolated_output(app_config, sample_bars, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TBS_SERVER_MONITOR_POLL_SECONDS", "3600")
    research_dir = tmp_path / "research"
    original_output_dir = tmp_path / "checked_cycle_output"
    observed: dict[str, object] = {}

    def fake_run_historical_research_cycle(*, spec_path, app_config):
        payload = json.loads(Path(spec_path).read_text(encoding="utf-8"))
        output_dir = Path(str(payload["output_dir"]))
        output_dir.mkdir(parents=True)
        manifest_path = output_dir / "research_cycle_manifest.json"
        rankings_path = output_dir / "candidate_rankings.parquet"
        backtest_index_path = output_dir / "backtest_index.parquet"
        rejection_report_path = output_dir / "rejection_report.md"
        manifest_path.write_text(
            json.dumps(
                {
                    "research_only": True,
                    "observe_only": True,
                    "promotion_ready": False,
                    "cycle_id": payload["cycle_id"],
                    "output_dir": str(output_dir),
                }
            ),
            encoding="utf-8",
        )
        rankings_path.write_text("fake", encoding="utf-8")
        backtest_index_path.write_text("fake", encoding="utf-8")
        rejection_report_path.write_text("fake", encoding="utf-8")
        observed["spec_path"] = str(spec_path)
        observed["payload"] = payload
        return SimpleNamespace(
            output_dir=output_dir,
            manifest_path=manifest_path,
            candidate_rankings_path=rankings_path,
            backtest_index_path=backtest_index_path,
            rejection_report_path=rejection_report_path,
        )

    monkeypatch.setattr(
        "tradingbotsuite.operator_console.run_historical_research_cycle",
        fake_run_historical_research_cycle,
    )
    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "operator_historical_cycle.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=replace(app_config.research, output_dir=research_dir),
        operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    spec_path = research_dir / "cycle_specs" / "cycle.json"
    spec_path.parent.mkdir(parents=True)
    spec_path.write_text(
        json.dumps(
            {
                "cycle_id": "operator-cycle",
                "symbol": "BTCUSDT",
                "output_dir": str(original_output_dir),
                "holding_windows": ["4h"],
                "data": {"synthetic_fixture": True, "synthetic_row_count": 20},
                "features": {"feature_sets": ["features_price_trend_vol"]},
                "strategies": ["baseline_no_trade"],
                "validation": {"min_splits": 1, "trade_count_floor": 0},
                "optimizer": {"max_candidates_per_strategy": 1},
            }
        ),
        encoding="utf-8",
    )

    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        response = client.post(
            "/api/operator/research/jobs/run-historical-research-cycle",
            json={"spec_path": str(spec_path)},
            headers={"X-CSRF-Token": csrf_token},
        )
        job = _wait_for_job(client, response.json()["job_id"])

    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    assert job["status"] == "succeeded"
    assert job["result"]["overwrite_protection"] == "isolated_output_dir"
    isolated_payload = observed["payload"]
    isolated_output_dir = Path(str(isolated_payload["output_dir"]))
    isolated_output_dir.resolve().relative_to(research_dir.resolve())
    assert isolated_output_dir != original_output_dir
    assert not original_output_dir.exists()
    assert Path(str(job["result"]["isolated_spec_path"])).exists()
    assert Path(str(job["result"]["research_cycle_manifest_path"])).exists()


def test_operator_isolated_research_jobs_rebase_migrated_spec_payload_paths(
    app_config,
    sample_bars,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("TBS_SERVER_MONITOR_POLL_SECONDS", "3600")
    research_dir = tmp_path / "research"
    stale_run_root = (
        Path(r"C:\Users\papaa\Music\tradingbotsuite\data\research\operator_runs\historical_data")
        / "refresh-historical-data-catalog-test"
    )
    active_paths = _write_completed_catalog_fixture(research_dir, stale_run_root=stale_run_root)
    observed: dict[str, dict[str, object]] = {}

    def fake_run_historical_research_cycle(*, spec_path, app_config):
        payload = json.loads(Path(spec_path).read_text(encoding="utf-8"))
        output_dir = Path(str(payload["output_dir"]))
        output_dir.mkdir(parents=True)
        manifest_path = output_dir / "research_cycle_manifest.json"
        rankings_path = output_dir / "candidate_rankings.parquet"
        backtest_index_path = output_dir / "backtest_index.parquet"
        rejection_report_path = output_dir / "rejection_report.md"
        manifest_path.write_text(
            json.dumps(
                {
                    "research_only": True,
                    "observe_only": True,
                    "promotion_ready": False,
                    "cycle_id": payload["cycle_id"],
                    "output_dir": str(output_dir),
                }
            ),
            encoding="utf-8",
        )
        rankings_path.write_text("fake", encoding="utf-8")
        backtest_index_path.write_text("fake", encoding="utf-8")
        rejection_report_path.write_text("fake", encoding="utf-8")
        observed["cycle"] = payload
        return SimpleNamespace(
            output_dir=output_dir,
            manifest_path=manifest_path,
            candidate_rankings_path=rankings_path,
            backtest_index_path=backtest_index_path,
            rejection_report_path=rejection_report_path,
        )

    def fake_run_discovery(*, spec_path, app_config, resume, stop_after_trials):
        payload = json.loads(Path(spec_path).read_text(encoding="utf-8"))
        output_dir = Path(str(payload["output_dir"]))
        output_dir.mkdir(parents=True)
        manifest_path = output_dir / "discovery_run_manifest.json"
        run_state_path = output_dir / "run_state.json"
        interesting_path = output_dir / "interesting_candidates.json"
        blocked_path = output_dir / "blocked_candidates.json"
        filter_blockers_path = output_dir / "filter_blockers.json"
        for path in (manifest_path, run_state_path, interesting_path, blocked_path, filter_blockers_path):
            path.write_text(
                json.dumps({"research_only": True, "observe_only": True, "promotion_ready": False}),
                encoding="utf-8",
            )
        observed["discovery"] = payload
        return SimpleNamespace(
            output_dir=output_dir,
            manifest_path=manifest_path,
            run_state_path=run_state_path,
            interesting_candidates_path=interesting_path,
            blocked_candidates_path=blocked_path,
            filter_blockers_path=filter_blockers_path,
            snapshot_paths=[],
        )

    monkeypatch.setattr(
        "tradingbotsuite.operator_console.run_historical_research_cycle",
        fake_run_historical_research_cycle,
    )
    monkeypatch.setattr("tradingbotsuite.operator_console.run_discovery", fake_run_discovery)
    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "operator_migrated_specs.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=replace(app_config.research, output_dir=research_dir),
        operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)

    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        cycle_response = client.post(
            "/api/operator/research/jobs/run-historical-research-cycle",
            json={"spec_path": str(active_paths["BTCUSDT_cycle_spec"])},
            headers={"X-CSRF-Token": csrf_token},
        )
        discovery_response = client.post(
            "/api/operator/research/jobs/run-discovery",
            json={"spec_path": str(active_paths["BTCUSDT_discovery_spec"])},
            headers={"X-CSRF-Token": csrf_token},
        )
        cycle_job = _wait_for_job(client, cycle_response.json()["job_id"])
        discovery_job = _wait_for_job(client, discovery_response.json()["job_id"])

    assert cycle_response.status_code == 200
    assert discovery_response.status_code == 200
    assert cycle_job["status"] == "succeeded"
    assert discovery_job["status"] == "succeeded"
    expected_manifest = str(active_paths["BTCUSDT_fixture_manifest"].resolve())
    assert observed["cycle"]["data"]["dataset_manifest_paths"] == [expected_manifest]
    assert observed["discovery"]["data"]["dataset_manifest_paths"] == [expected_manifest]
    assert observed["discovery"]["research_output_dir"] == str(research_dir.resolve())
    assert "tradingbotsuite" not in json.dumps(observed, sort_keys=True).lower()


def test_operator_historical_cycle_rejects_unallowlisted_spec_path(app_config, sample_bars, tmp_path) -> None:
    research_dir = tmp_path / "research"
    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "operator_historical_cycle_reject.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=replace(app_config.research, output_dir=research_dir),
        operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    spec_path = tmp_path / "outside_specs" / "cycle.json"
    spec_path.parent.mkdir(parents=True)
    spec_path.write_text(json.dumps({"cycle_id": "bad-cycle"}), encoding="utf-8")

    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        response = client.post(
            "/api/operator/research/jobs/run-historical-research-cycle",
            json={"spec_path": str(spec_path)},
            headers={"X-CSRF-Token": csrf_token},
        )

    assert response.status_code == 400
    assert "spec_path must be inside" in response.json()["detail"]


def test_operator_discovery_job_writes_research_only_artifacts(app_config, sample_bars, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TBS_SERVER_MONITOR_POLL_SECONDS", "3600")
    research_dir = tmp_path / "research"
    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "operator_discovery.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=replace(app_config.research, output_dir=research_dir),
        operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)

    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        response = client.post(
            "/api/operator/research/jobs/run-discovery",
            json={"spec_path": "configs/discovery/quick_smoke_btcusdt_v4.json"},
            headers={"X-CSRF-Token": csrf_token},
        )
        job = _wait_for_job(client, response.json()["job_id"])
        artifacts = client.get("/api/operator/research/artifacts").json()["items"]

    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    assert job["status"] == "succeeded"
    assert job["result"]["overwrite_protection"] == "isolated_job_output_dir"
    output_dir = Path(str(job["result"]["output_dir"]))
    output_dir.resolve().relative_to(research_dir.resolve())
    assert Path(str(job["result"]["isolated_spec_path"])).exists()
    assert Path(str(job["result"]["discovery_run_manifest_path"])).exists()
    assert Path(str(job["result"]["run_state_path"])).exists()

    discovery = next(artifact for artifact in artifacts if artifact["type"] == "discovery_run")
    assert discovery["summary"]["run_id"] == "quick_smoke_btcusdt_v4"
    assert discovery["summary"]["status"] == "completed"
    assert discovery["summary"]["research_only"] is True
    assert discovery["summary"]["observe_only"] is True
    assert discovery["summary"]["promotion_ready"] is False
    assert discovery["summary"]["candidate_pack_written"] is False
    assert discovery["summary"]["counts"]["completed_trials"] == 3
    assert discovery["summary"]["interesting_candidates"]["row_count"] == 1
    assert discovery["summary"]["blocked_candidates"]["row_count"] == 1
    assert discovery["summary"]["filter_blockers"]["row_count"] == 1
    assert discovery["summary"]["last_snapshot_path"]
    assert discovery["summary"]["latest_snapshot"]["available"] is True
    assert discovery["summary"]["latest_snapshot"]["path"]


def test_operator_discovery_job_can_pause_and_resume(app_config, sample_bars, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TBS_SERVER_MONITOR_POLL_SECONDS", "3600")
    research_dir = tmp_path / "research"
    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "operator_discovery_resume.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=replace(app_config.research, output_dir=research_dir),
        operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)

    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        first_response = client.post(
            "/api/operator/research/jobs/run-discovery",
            json={"spec_path": "configs/discovery/quick_smoke_btcusdt_v4.json", "stop_after_trials": 1},
            headers={"X-CSRF-Token": csrf_token},
        )
        first_job = _wait_for_job(client, first_response.json()["job_id"])
        first_state = json.loads(Path(str(first_job["result"]["run_state_path"])).read_text(encoding="utf-8"))
        second_response = client.post(
            "/api/operator/research/jobs/run-discovery",
            json={"spec_path": "configs/discovery/quick_smoke_btcusdt_v4.json", "resume": True},
            headers={"X-CSRF-Token": csrf_token},
        )
        second_job = _wait_for_job(client, second_response.json()["job_id"])
        artifacts = client.get("/api/operator/research/artifacts").json()["items"]

    assert first_response.status_code == 200
    assert first_job["status"] == "succeeded"
    assert first_job["result"]["overwrite_protection"] == "pauseable_stable_run_id_output_dir"
    assert first_state["status"] == "in_progress"
    assert first_state["completed_trial_ids"] == ["trial-000001"]
    assert second_response.status_code == 200
    assert second_job["status"] == "succeeded"
    assert second_job["result"]["resume"] is True
    assert second_job["result"]["overwrite_protection"] == "resume_stable_run_id_output_dir"
    assert second_job["result"]["output_dir"] == first_job["result"]["output_dir"]
    discovery = next(artifact for artifact in artifacts if artifact["type"] == "discovery_run")
    assert discovery["summary"]["status"] == "completed"
    assert discovery["summary"]["counts"]["completed_trials"] == 3


def test_operator_discovery_rejects_unallowlisted_spec_path(app_config, sample_bars, tmp_path) -> None:
    research_dir = tmp_path / "research"
    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "operator_discovery_reject.sqlite3",
        webhook=app_config.webhook,
        strategy=app_config.strategy,
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=replace(app_config.research, output_dir=research_dir),
        operator_ui=OperatorUIConfig(enabled=True, secret="operator-secret"),
    )
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    spec_path = tmp_path / "outside_specs" / "discovery.json"
    spec_path.parent.mkdir(parents=True)
    spec_path.write_text(json.dumps({"run_id": "bad-discovery"}), encoding="utf-8")

    with TestClient(app) as client:
        csrf_token = _login(client, "operator-secret")
        response = client.post(
            "/api/operator/research/jobs/run-discovery",
            json={"spec_path": str(spec_path)},
            headers={"X-CSRF-Token": csrf_token},
        )

    assert response.status_code == 400
    assert "spec_path must be inside" in response.json()["detail"]


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
    assert "Operator Quickstart" in response.text
    assert "First Safe Run" in response.text
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
    assert titles[0] == "Operator Quickstart"
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
