from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from tradingbotsuite.backtesting import BacktestEngine, BacktestSpec, write_backtest_benchmark_report
from tradingbotsuite.research.deterministic_datasets import build_hmm_knn_sweep_dataset, write_hmm_knn_sweep_dataset
from tradingbotsuite.strategies import required_signal_columns


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


def test_perp_basis_convergence_v2_runs_through_backtest_engine(tmp_path: Path) -> None:
    frame = _perp_context_v2_signal_frame(row_count=96)
    engine = BacktestEngine()

    result = engine.run(
        BacktestSpec(
            run_id="perp-basis-convergence-v2",
            symbol="BTCUSDT",
            output_dir=tmp_path / "backtests",
            strategy_id="perp_basis_convergence_v2",
            holding_window="24h",
            feature_set_id="features_perp_context_v2",
            strategy_config={
                "basis_vol_threshold": 2.0,
                "premium_z_threshold": 0.75,
                "min_edge_bps": 1.0,
                "funding_policy": "carry_adjusted",
                "spacing_bars": 1,
            },
        ),
        dataset=frame,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    metrics = json.loads(result.metrics_path.read_text(encoding="utf-8"))
    signals = pd.read_parquet(result.signals_path)

    assert manifest["strategy_metadata"]["signal_contract_valid"] is True
    assert manifest["strategy_metadata"]["strategy_id"] == "perp_basis_convergence_v2"
    assert manifest["feature_set_id"] == "features_perp_context_v2"
    assert metrics["trade_count"] > 0
    assert set(required_signal_columns()) <= set(signals.columns)
    assert signals["feature_set_id"].eq("features_perp_context_v2").all()
    assert set(signals["side"]) == {"long", "short"}


def test_perp_basis_convergence_backtest_rejects_invalid_feature_or_window(tmp_path: Path) -> None:
    frame = _perp_context_v2_signal_frame(row_count=96)
    engine = BacktestEngine()
    with pytest.raises(ValueError, match="strategy_feature_set_unsupported:perp_basis_convergence_v2:features_full_context_no_wt"):
        engine.run(
            BacktestSpec(
                run_id="bad-feature",
                symbol="BTCUSDT",
                output_dir=tmp_path / "backtests",
                strategy_id="perp_basis_convergence_v2",
                holding_window="24h",
                feature_set_id="features_full_context_no_wt",
            ),
            dataset=frame,
        )
    with pytest.raises(ValueError, match="strategy_holding_window_unsupported:perp_basis_convergence_v2:1h"):
        engine.run(
            BacktestSpec(
                run_id="bad-window",
                symbol="BTCUSDT",
                output_dir=tmp_path / "backtests",
                strategy_id="perp_basis_convergence_v2",
                holding_window="1h",
                feature_set_id="features_perp_context_v2",
            ),
            dataset=frame,
        )


def test_funding_crowding_fade_v2_runs_through_backtest_engine(tmp_path: Path) -> None:
    frame = _funding_crowding_v2_signal_frame(row_count=96)
    engine = BacktestEngine()

    result = engine.run(
        BacktestSpec(
            run_id="funding-crowding-fade-v2",
            symbol="BTCUSDT",
            output_dir=tmp_path / "backtests",
            strategy_id="funding_crowding_fade_v2",
            holding_window="24h",
            feature_set_id="features_perp_context_v2",
            strategy_config={"spacing_bars": 1},
        ),
        dataset=frame,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    metrics = json.loads(result.metrics_path.read_text(encoding="utf-8"))
    signals = pd.read_parquet(result.signals_path)

    assert manifest["strategy_metadata"]["signal_contract_valid"] is True
    assert manifest["strategy_metadata"]["strategy_id"] == "funding_crowding_fade_v2"
    assert manifest["feature_set_id"] == "features_perp_context_v2"
    assert metrics["trade_count"] > 0
    assert set(required_signal_columns()) <= set(signals.columns)
    assert signals["feature_set_id"].eq("features_perp_context_v2").all()
    assert set(signals["side"]) == {"long", "short"}


def test_funding_crowding_fade_backtest_rejects_invalid_feature_or_window(tmp_path: Path) -> None:
    frame = _funding_crowding_v2_signal_frame(row_count=96)
    engine = BacktestEngine()
    with pytest.raises(ValueError, match="strategy_feature_set_unsupported:funding_crowding_fade_v2:features_full_context_no_wt"):
        engine.run(
            BacktestSpec(
                run_id="bad-funding-feature",
                symbol="BTCUSDT",
                output_dir=tmp_path / "backtests",
                strategy_id="funding_crowding_fade_v2",
                holding_window="24h",
                feature_set_id="features_full_context_no_wt",
            ),
            dataset=frame,
        )
    with pytest.raises(ValueError, match="strategy_holding_window_unsupported:funding_crowding_fade_v2:1h"):
        engine.run(
            BacktestSpec(
                run_id="bad-funding-window",
                symbol="BTCUSDT",
                output_dir=tmp_path / "backtests",
                strategy_id="funding_crowding_fade_v2",
                holding_window="1h",
                feature_set_id="features_perp_context_v2",
            ),
            dataset=frame,
        )


def test_backtest_spec_exit_metadata_is_propagated_to_signal_artifact(tmp_path: Path) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=120, variant="balanced")
    result = BacktestEngine().run(
        BacktestSpec(
            run_id="exit-metadata",
            symbol="BTCUSDT",
            output_dir=tmp_path / "backtests",
            dataset_path=dataset.parquet_path,
            dataset_sha256=dataset.parquet_sha256,
            strategy_id="trend_following_v1",
            holding_window="24h",
            feature_set_id="features_price_trend_vol",
            exit_policy_id="custom_time_exit",
            target_return=0.02,
            stop_return=0.01,
            strategy_config={"slope_threshold": 0.1, "spacing_bars": 10},
        )
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    signals = pd.read_parquet(result.signals_path)

    assert manifest["exit_policy_id"] == "custom_time_exit"
    assert manifest["execution_assumptions"]["target_return"] == 0.02
    assert not signals.empty
    assert set(signals["exit_policy_id"]) == {"custom_time_exit"}
    assert set(signals["target_return"]) == {0.02}
    assert set(signals["stop_return"]) == {0.01}


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


def _perp_context_v2_signal_frame(*, row_count: int) -> pd.DataFrame:
    rows = []
    start_ms = 1_712_649_600_000
    interval_ms = 900_000
    price = 70_000.0
    for index in range(row_count):
        signal_time_ms = start_ms + index * interval_ms
        close = price + index * 12.0
        basis = 0.0
        premium_z = 0.0
        funding = 0.0
        if index % 12 == 0:
            basis = -0.00045
            premium_z = -1.25
            funding = -0.00001
        elif index % 12 == 6:
            basis = 0.00045
            premium_z = 1.25
            funding = 0.00001
        rows.append(
            {
                "bar_time_ms": signal_time_ms,
                "feature_time_ms": signal_time_ms,
                "symbol": "BTCUSDT",
                "open": close - 10.0,
                "high": close + 40.0,
                "low": close - 40.0,
                "close": close,
                "volume": 1_000.0 + index,
                "perp_mark_index_basis": basis,
                "perp_premium": basis,
                "perp_premium_z_7d": premium_z,
                "perp_premium_slope_8h": basis / 8.0,
                "perp_last_funding_rate": funding,
                "perp_funding_z_7d": funding * 10_000.0,
                "perp_funding_momentum": funding / 2.0,
                "cal_time_since_last_funding_h": float(index % 32) / 4.0,
                "cal_time_to_next_funding_h": 8.0 - (float(index % 32) / 4.0),
                "oi_notional": 1_000_000_000.0 + index * 100_000.0,
                "oi_delta_1h": 10_000.0 if basis else 0.0,
                "oi_delta_z_7d": 0.4 if basis else 0.0,
                "oi_volume_ratio": 0.9,
                "flow_buy_sell_ratio": 1.1 if basis > 0.0 else (0.9 if basis < 0.0 else 1.0),
                "flow_signed_taker_notional": 25_000.0 if basis > 0.0 else (-25_000.0 if basis < 0.0 else 0.0),
                "flow_signed_taker_z_7d": 0.7 if basis > 0.0 else (-0.7 if basis < 0.0 else 0.0),
                "quality_context_missing_count": 0.0,
                "quality_has_funding_gap": 0.0,
                "quality_has_oi_gap": 0.0,
                "quality_has_premium_gap": 0.0,
                "quality_provider_backed_all_required": 1.0,
                "quality_latest_window_context_only": 0.0,
            }
        )
    return pd.DataFrame(rows)


def _funding_crowding_v2_signal_frame(*, row_count: int) -> pd.DataFrame:
    frame = _perp_context_v2_signal_frame(row_count=row_count)
    frame.loc[:, [
        "perp_mark_index_basis",
        "perp_premium",
        "perp_premium_z_7d",
        "perp_last_funding_rate",
        "perp_funding_z_7d",
        "perp_funding_momentum",
        "oi_delta_z_7d",
        "flow_signed_taker_z_7d",
    ]] = 0.0
    short_rows = frame.index[frame.index % 12 == 6]
    long_rows = frame.index[frame.index % 12 == 0]
    frame.loc[short_rows, "perp_mark_index_basis"] = 0.00035
    frame.loc[short_rows, "perp_premium"] = 0.00035
    frame.loc[short_rows, "perp_premium_z_7d"] = 1.5
    frame.loc[short_rows, "perp_last_funding_rate"] = 0.00008
    frame.loc[short_rows, "perp_funding_z_7d"] = 1.8
    frame.loc[short_rows, "perp_funding_momentum"] = -0.00001
    frame.loc[short_rows, "oi_delta_z_7d"] = 0.8
    frame.loc[short_rows, "flow_signed_taker_z_7d"] = 0.8
    frame.loc[long_rows, "perp_mark_index_basis"] = -0.00035
    frame.loc[long_rows, "perp_premium"] = -0.00035
    frame.loc[long_rows, "perp_premium_z_7d"] = -1.5
    frame.loc[long_rows, "perp_last_funding_rate"] = -0.00008
    frame.loc[long_rows, "perp_funding_z_7d"] = -1.8
    frame.loc[long_rows, "perp_funding_momentum"] = 0.00001
    frame.loc[long_rows, "oi_delta_z_7d"] = 0.8
    frame.loc[long_rows, "flow_signed_taker_z_7d"] = -0.8
    return frame
