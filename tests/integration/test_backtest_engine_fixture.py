from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from tradingbotsuite.backtesting import BacktestEngine, BacktestSpec, write_backtest_benchmark_report
from tradingbotsuite.research.deterministic_datasets import build_hmm_knn_sweep_dataset, write_hmm_knn_sweep_dataset


def test_baseline_trend_and_no_trade_share_engine(tmp_path: Path) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=120, variant="balanced")
    engine = BacktestEngine()
    trend = engine.run(
        BacktestSpec(
            run_id="trend",
            symbol="BTCUSDT",
            output_dir=tmp_path / "backtests",
            dataset_path=dataset.parquet_path,
            dataset_sha256=dataset.parquet_sha256,
            strategy_id="baseline_trend",
            holding_window="24h",
            strategy_config={"slope_threshold": 0.1, "spacing_bars": 10},
        )
    )
    no_trade = engine.run(
        BacktestSpec(
            run_id="no-trade",
            symbol="BTCUSDT",
            output_dir=tmp_path / "backtests",
            dataset_path=dataset.parquet_path,
            dataset_sha256=dataset.parquet_sha256,
            strategy_id="baseline_no_trade",
            holding_window="24h",
        )
    )

    trend_metrics = json.loads(trend.metrics_path.read_text(encoding="utf-8"))
    no_trade_metrics = json.loads(no_trade.metrics_path.read_text(encoding="utf-8"))
    assert trend_metrics["trade_count"] > 0
    assert no_trade_metrics["trade_count"] == 0
    assert json.loads(trend.manifest_path.read_text(encoding="utf-8"))["engine_version"] == json.loads(
        no_trade.manifest_path.read_text(encoding="utf-8")
    )["engine_version"]


def test_stage_six_baseline_plugins_share_backtest_engine(tmp_path: Path) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=120, variant="balanced")
    engine = BacktestEngine()
    strategies = {
        "trend_following_v1": {"slope_threshold": 0.1, "spacing_bars": 10},
        "volatility_breakout_v1": {"shock_threshold": 0.7, "atr_percentile_threshold": 0.25, "spacing_bars": 10},
        "range_reversion_v1": {"choppiness_threshold": 55.0, "stretch_threshold": 0.04, "spacing_bars": 8},
        "funding_basis_v1": {"funding_threshold": 0.00003, "basis_bps_threshold": 1.0, "spacing_bars": 10},
    }
    trade_counts = {}

    for strategy_id, parameters in strategies.items():
        result = engine.run(
            BacktestSpec(
                run_id=strategy_id,
                symbol="BTCUSDT",
                output_dir=tmp_path / "backtests",
                dataset_path=dataset.parquet_path,
                dataset_sha256=dataset.parquet_sha256,
                strategy_id=strategy_id,
                holding_window="24h",
                feature_set_id="features_full_context_no_wt",
                strategy_config=parameters,
            )
        )
        manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
        metrics = json.loads(result.metrics_path.read_text(encoding="utf-8"))
        signals = pd.read_parquet(result.signals_path)
        trade_counts[strategy_id] = int(metrics["trade_count"])

        assert manifest["strategy_metadata"]["signal_contract_valid"] is True
        assert manifest["strategy_metadata"]["strategy_id"] == strategy_id
        assert {"signal_time_ms", "side", "feature_set_id", "research_only"} <= set(signals.columns)

    assert len(trade_counts) == 4
    assert all(count > 0 for count in trade_counts.values())


def test_future_rows_do_not_change_prior_trades(tmp_path: Path) -> None:
    frame = build_hmm_knn_sweep_dataset(row_count=120, variant="balanced")
    baseline = BacktestEngine().run(
        BacktestSpec(
            run_id="baseline",
            symbol="BTCUSDT",
            output_dir=tmp_path / "backtests",
            strategy_id="baseline_trend",
            holding_window="24h",
            strategy_config={"slope_threshold": 0.1, "spacing_bars": 10},
        ),
        dataset=frame,
    )
    shocked = frame.copy()
    shocked.loc[80:, "directional_slope_atr"] = shocked.loc[80:, "directional_slope_atr"] * -20.0
    shocked.loc[80:, "signal_bar_close"] = shocked.loc[80:, "signal_bar_close"] * 3.0
    changed = BacktestEngine().run(
        BacktestSpec(
            run_id="changed",
            symbol="BTCUSDT",
            output_dir=tmp_path / "backtests",
            strategy_id="baseline_trend",
            holding_window="24h",
            strategy_config={"slope_threshold": 0.1, "spacing_bars": 10},
        ),
        dataset=shocked,
    )

    baseline_trades = pd.read_parquet(baseline.trades_path)
    changed_trades = pd.read_parquet(changed.trades_path)
    columns = ["entry_time_ms", "exit_time_ms", "side", "entry_price", "exit_price", "net_return"]
    cutoff = int(frame.loc[80, "signal_bar_time_ms"])
    pd.testing.assert_frame_equal(
        baseline_trades.loc[baseline_trades["exit_time_ms"] < cutoff, columns].reset_index(drop=True),
        changed_trades.loc[changed_trades["exit_time_ms"] < cutoff, columns].reset_index(drop=True),
    )


def test_backtest_benchmark_artifacts_are_written(tmp_path: Path) -> None:
    backtest_report_path, optimizer_report_path = write_backtest_benchmark_report(output_dir=tmp_path / "benchmarks", row_count=120, repeat=2)
    report = json.loads(backtest_report_path.read_text(encoding="utf-8"))
    optimizer = json.loads(optimizer_report_path.read_text(encoding="utf-8"))

    assert backtest_report_path.name == "backtest_engine_baseline.json"
    assert optimizer_report_path.name == "optimizer_baseline.json"
    assert report["dimensions"]["deterministic_repeat_hash"]
    assert len(report["runs"]) == 2
    assert optimizer["status"] == "registered_baseline"
