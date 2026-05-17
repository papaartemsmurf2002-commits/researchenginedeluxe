from __future__ import annotations

import asyncio
import json
import os
import re
import time
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
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
    assert "R104 Command Center" in response.text
    assert "Progress Meter" in response.text
    assert "Function Blocks" in response.text
    assert "Primary BTC Path" in response.text
    assert "ETH Mirror" in response.text
    assert "Operator Board" in response.text
    assert "Choose Evidence Task" in response.text
    assert "Data Readiness" in response.text
    assert "Current Run" in response.text
    assert "Progress" in response.text
    assert "Latest Snapshot" in response.text
    assert "R104 Durable Candidate Validation" in response.text
    assert "Durable Readiness" in response.text
    assert "Recommended Run Order" in response.text
    assert "Recommended Defaults" in response.text
    assert "Candidate Eligibility Review" in response.text
    assert "Check Durable Readiness" in response.text
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
    assert "Diagnostic Smoke" in response.text
    assert "BTC Standard Screen" in response.text
    assert "Pause After One Trial" in response.text
    assert "Resume Run" in response.text
    assert "Open Latest Snapshot" in response.text
    assert "Review Candidate Eligibility" in response.text
    assert "Open Artifact List" in response.text
    assert "Evaluate Eligibility" in response.text
    assert "Run Provider Diagnostic" in response.text
    assert "Intake" in response.text
    assert "Dataset" in response.text
    assert "Evidence" in response.text
    assert "All" in response.text
    assert "What The Research System Builds" in response.text
    assert "Historical Cycle Review" in response.text
    assert "run-historical-research-cycle" in response.text
    assert "Run Historical Cycle" in response.text
    assert "BTCUSDT durable deep R104 cycle" in response.text
    assert "ETHUSDT durable deep R104 cycle" in response.text
    assert "Operator queued runs write isolated output" in response.text
    assert "Compute Profile" in response.text
    assert "Backend Mix" in response.text
    assert "GPU Status" in response.text
    assert "CUDA Selected" in response.text
    assert "R104 Durable Discovery Run" in response.text
    assert "Run Discovery" in response.text
    assert "Resume Discovery" in response.text
    assert "BTCUSDT exact bounded sweep" in response.text
    assert "ETHUSDT exact bounded sweep" in response.text
    assert "BTCUSDT durable standard discovery" in response.text
    assert "ETHUSDT durable standard discovery" in response.text
    assert "BTCUSDT compatibility sparse harvest" in response.text
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
    assert "Profitability Chart" in response.text
    assert "Waiting for profitability artifacts." in response.text
    assert "Research Graphs" in response.text
    assert "No candidate strategy mix yet. Run Historical Cycle Review." in response.text
    assert "No gate decisions yet. Run Historical Cycle Review and inspect rejection evidence." in response.text
    assert "No holding-window metrics yet. Run Historical Cycle Review." in response.text
    assert "No discovery run ledgers yet. Run durable discovery for real search or a quick plumbing check." in response.text
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
    assert "/api/operator/research/progress" in response.text
    assert "Provider Pipeline" in response.text
    assert "/api/operator/research/jobs/prepare-hmm-knn-research-data" in response.text
    assert "/api/operator/research/jobs/run-historical-research-cycle" in response.text
    assert "/api/operator/research/jobs/run-discovery" in response.text
    assert "/api/operator/research/jobs/evaluate-discovery-candidate-pack-eligibility" in response.text
    assert "hmm_knn_artifact" in response.text
    assert "observe_only" in response.text
    assert "Live Canary" not in response.text
    assert "Promotion Ready" not in response.text
    assert "current branch workflow" not in response.text
    assert "older persisted" not in response.text
    assert "Legacy" not in response.text
    assert "legacy" not in response.text
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
    assert payload["stage"] == "R104"
    assert payload["research_only"] is True
    assert payload["observe_only"] is True
    assert payload["promotion_ready"] is False
    keys = {item["key"] for item in payload["milestones"]}
    assert {
        "durable_readiness",
        "btc_cycle",
        "btc_discovery",
        "eth_cycle",
        "eth_discovery",
        "candidate_eligibility",
    } <= keys
    by_key = {item["key"]: item for item in payload["milestones"]}
    assert by_key["durable_readiness"]["status"] == "complete"
    assert by_key["btc_cycle"]["status"] == "ready"
    assert by_key["btc_discovery"]["status"] == "waiting"
    assert "BTC brute-force cycle" in by_key["btc_discovery"]["detail"]
    assert by_key["eth_cycle"]["status"] == "ready"
    assert by_key["eth_discovery"]["status"] == "waiting"
    assert "ETH brute-force cycle" in by_key["eth_discovery"]["detail"]
    assert payload["progress"]["total"] == len(payload["milestones"])
    assert payload["progress"]["active_job_type"] is None
    assert "optimize-entry" + "-gates" not in payload["next_action"]
    assert payload["settings"]["output_policy"] == "isolated operator output directories"
    assert "570240" in payload["settings"]["primary_discovery_profile"]
    assert "Run" in payload["next_action"] or "Fix" in payload["next_action"]


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
    assert by_key["btc_cycle"]["status"] == "complete"
    assert by_key["btc_discovery"]["status"] == "complete"
    assert by_key["candidate_eligibility"]["status"] == "ready"
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


def test_operator_r104_readiness_api_reports_durable_btc_eth(app_config, sample_bars) -> None:
    config = _operator_config(app_config)
    app = create_app(config)
    app.state.engine.candle_client = FakeCandles(sample_bars)
    with TestClient(app) as client:
        _login(client, "operator-secret")
        response = client.get("/api/operator/research/r104-readiness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["stage"] == "R104"
    assert payload["research_only"] is True
    assert payload["observe_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["ready"] is True
    assert payload["ready_count"] == 2
    by_symbol = {item["symbol"]: item for item in payload["items"]}
    assert set(by_symbol) == {"BTCUSDT", "ETHUSDT"}
    assert "full_cycle_btcusdt_durable_public_archive_r104_deep_v1.json" in by_symbol["BTCUSDT"]["cycle_spec_path"]
    assert "full_cycle_ethusdt_durable_public_archive_r104_deep_v1.json" in by_symbol["ETHUSDT"]["cycle_spec_path"]
    assert "exact_entry_sweep_btcusdt_durable_r104_v1.json" in by_symbol["BTCUSDT"]["discovery_spec_path"]
    assert "exact_entry_sweep_ethusdt_durable_r104_v1.json" in by_symbol["ETHUSDT"]["discovery_spec_path"]
    assert "full_cycle_btcusdt_durable_public_archive_r104_v1.json" in by_symbol["BTCUSDT"]["standard_cycle_spec_path"]
    assert by_symbol["BTCUSDT"]["fixture_row_counts"]["bars"] > 0
    assert by_symbol["ETHUSDT"]["fixture_row_counts"]["bars"] > 0


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
    assert "full_cycle_btcusdt_durable_public_archive_r104_deep_v1.json" in str(observed[0][1]["spec_path"])
    assert "exact_entry_sweep_btcusdt_durable_r104_v1.json" in str(observed[1][1]["spec_path"])


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
    assert response.status_code == 409
    assert "live mode" in response.json()["detail"]


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
