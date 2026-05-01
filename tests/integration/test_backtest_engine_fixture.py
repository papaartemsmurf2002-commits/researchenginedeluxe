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
