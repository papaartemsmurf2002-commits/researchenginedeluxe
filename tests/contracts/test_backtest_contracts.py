from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pandas as pd
import pytest

from tradingbotsuite.backtesting import COST_PROFILE_CONTRACT_VERSION, BacktestEngine, BacktestSpec
from tradingbotsuite.backtesting.engine import BACKTEST_CACHE_POLICY, SUPPORTED_HOLDING_WINDOWS_MS, _market_frame
from tradingbotsuite.backtesting.metrics import REQUIRED_BACKTEST_METRICS
from tradingbotsuite.research.deterministic_datasets import write_hmm_knn_sweep_dataset


REQUIRED_OUTPUTS = {
    "backtest_manifest.json",
    "trades.parquet",
    "signals.parquet",
    "equity_curve.parquet",
    "metrics.json",
    "config_resolved.json",
}


def _run_fixture(tmp_path: Path, *, strategy_id: str = "baseline_trend", holding_window: str = "24h"):
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=120, variant="balanced")
    spec = BacktestSpec(
        run_id=f"{strategy_id}-{holding_window}",
        symbol="BTCUSDT",
        output_dir=tmp_path / "backtests",
        dataset_path=dataset.parquet_path,
        dataset_sha256=dataset.parquet_sha256,
        strategy_id=strategy_id,  # type: ignore[arg-type]
        holding_window=holding_window,
        feature_set_id="features_price_trend_vol",
        feature_manifest_sha256="test-feature-hash",
        strategy_config={"slope_threshold": 0.1, "spacing_bars": 10},
    )
    return BacktestEngine().run(spec), dataset


def test_backtest_writes_required_artifact_contract(tmp_path: Path) -> None:
    result, dataset = _run_fixture(tmp_path)
    produced = {path.name for path in result.output_dir.iterdir()}
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert REQUIRED_OUTPUTS <= produced
    assert manifest["backtest_manifest_version"] == "backtest-manifest-v1"
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["dataset_sha256"] == dataset.parquet_sha256
    assert manifest["cache_policy"] == BACKTEST_CACHE_POLICY
    assert manifest["cache_lookup_used"] is False
    assert manifest["cache_hit"] is False
    assert manifest["execution_cache_reuse_enabled"] is False
    assert manifest["cache_key_components"]["cache_policy"] == BACKTEST_CACHE_POLICY
    assert manifest["cache_key_components"]["dataset_sha256"] == dataset.parquet_sha256
    assert manifest["cache_key_components"]["feature_manifest_sha256"] == "test-feature-hash"
    assert manifest["cache_key"] == _stable_test_hash(manifest["cache_key_components"])
    assert manifest["required_metrics_present"] is True
    assert manifest["same_bar_entry_exit_allowed"] is False
    assert manifest["exit_policy_id"] == "fixed_holding_window"
    assert manifest["execution_assumptions"]["exit_policy_id"] == "fixed_holding_window"
    assert manifest["execution_assumptions"]["exit_price_source"] == "primary_close"
    assert manifest["cost_model"]["cost_profile_contract_version"] == COST_PROFILE_CONTRACT_VERSION
    assert manifest["cost_model"]["cost_profile_id"] == "binance_usdm_research_baseline"
    assert manifest["cost_model"]["fill_profile_id"] == "primary_bar_latency_fill"
    assert manifest["cost_model"]["source_venue"] == "binance_usdm"
    assert manifest["cost_model"]["execution_venue"] == "binance_usdm_research"
    assert manifest["cost_model"]["execution_proof_scope"] == "historical_research_only_not_live_execution_proof"
    assert "hyperliquid" in manifest["cost_model"]["not_execution_proof_for"]
    assert manifest["validity"]["fees_slippage_funding_included"] is True


def test_required_metrics_include_costs_and_splits(tmp_path: Path) -> None:
    result, _ = _run_fixture(tmp_path)
    metrics = json.loads(result.metrics_path.read_text(encoding="utf-8"))
    trades = pd.read_parquet(result.trades_path)

    assert set(REQUIRED_BACKTEST_METRICS) <= set(metrics)
    assert metrics["trade_count"] == len(trades)
    assert metrics["gross_return_before_costs"] != metrics["net_return_after_fees_slippage_funding"]
    assert metrics["slippage_sensitivity"] > 0
    assert metrics["funding_contribution"] != 0
    assert metrics["split_by_regime"]
    assert metrics["split_by_month"]
    assert metrics["split_by_volatility_bucket"]


def test_backtest_market_frame_preserves_last_funding_rate_alias() -> None:
    source = pd.DataFrame(
        {
            "bar_time_ms": [1_700_000_000_000, 1_700_000_900_000],
            "symbol": ["BTCUSDT", "BTCUSDT"],
            "open": [100.0, 101.0],
            "high": [101.0, 102.0],
            "low": [99.0, 100.0],
            "close": [100.5, 101.5],
            "volume": [1.0, 1.0],
            "last_funding_rate": [0.0001, 0.0002],
        }
    )

    market = _market_frame(source, symbol="BTCUSDT")

    assert "last_funding_rate" in market.columns
    assert market["last_funding_rate"].tolist() == [0.0001, 0.0002]


def test_backtest_result_hash_is_reproducible(tmp_path: Path) -> None:
    first, dataset = _run_fixture(tmp_path)
    second = BacktestEngine().run(
        BacktestSpec(
            run_id="repeat",
            symbol="BTCUSDT",
            output_dir=tmp_path / "backtests",
            dataset_path=dataset.parquet_path,
            dataset_sha256=dataset.parquet_sha256,
            strategy_id="baseline_trend",
            holding_window="24h",
            feature_set_id="features_price_trend_vol",
            feature_manifest_sha256="test-feature-hash",
            strategy_config={"slope_threshold": 0.1, "spacing_bars": 10},
        )
    )

    assert first.result_sha256 == second.result_sha256
    assert json.loads(first.metrics_path.read_text(encoding="utf-8")) == json.loads(second.metrics_path.read_text(encoding="utf-8"))
    first_manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    second_manifest = json.loads(second.manifest_path.read_text(encoding="utf-8"))
    assert first_manifest["cache_key"] == second_manifest["cache_key"]


def test_supported_holding_windows_run(tmp_path: Path) -> None:
    for holding_window in ("1h", "4h", "12h", "24h", "72h", "7d"):
        result, _ = _run_fixture(tmp_path, strategy_id="baseline_no_trade", holding_window=holding_window)
        manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
        assert manifest["execution_assumptions"]["holding_period_ms"] == SUPPORTED_HOLDING_WINDOWS_MS[holding_window]


def test_invalid_holding_window_rejected(tmp_path: Path) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=120, variant="balanced")
    spec = BacktestSpec(
        run_id="invalid",
        symbol="BTCUSDT",
        output_dir=tmp_path / "backtests",
        dataset_path=dataset.parquet_path,
        strategy_id="baseline_trend",
        holding_window="15m",
    )

    with pytest.raises(ValueError, match="holding_window"):
        BacktestEngine().run(spec)


def test_strategy_holding_and_feature_compatibility_rejected(tmp_path: Path) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=120, variant="balanced")
    unsupported_window = BacktestSpec(
        run_id="unsupported-window",
        symbol="BTCUSDT",
        output_dir=tmp_path / "backtests",
        dataset_path=dataset.parquet_path,
        strategy_id="range_reversion_v1",
        holding_window="72h",
        feature_set_id="features_price_trend_vol",
    )
    unsupported_feature = BacktestSpec(
        run_id="unsupported-feature",
        symbol="BTCUSDT",
        output_dir=tmp_path / "backtests",
        dataset_path=dataset.parquet_path,
        strategy_id="funding_basis_v1",
        holding_window="24h",
        feature_set_id="features_price_trend_vol",
    )

    with pytest.raises(ValueError, match="strategy_holding_window_unsupported"):
        BacktestEngine().run(unsupported_window)
    with pytest.raises(ValueError, match="strategy_feature_set_unsupported"):
        BacktestEngine().run(unsupported_feature)


def test_lower_timeframe_content_hash_participates_in_manifest_identity(tmp_path: Path) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=120, variant="balanced")
    lower = pd.DataFrame(
        {
            "symbol": ["BTCUSDT"] * 8,
            "bar_time_ms": [1_712_649_600_000 + index * 60_000 for index in range(8)],
            "open": [100.0] * 8,
            "high": [100.5] * 8,
            "low": [99.5] * 8,
            "close": [100.0] * 8,
            "volume": [1.0] * 8,
        }
    )
    lower_path = tmp_path / "datasets" / "lower.parquet"
    lower.to_parquet(lower_path, index=False)
    spec = BacktestSpec(
        run_id="lower-hash",
        symbol="BTCUSDT",
        output_dir=tmp_path / "backtests",
        dataset_path=dataset.parquet_path,
        dataset_sha256=dataset.parquet_sha256,
        strategy_id="baseline_no_trade",
        holding_window="1h",
        feature_set_id="features_price_trend_vol",
        lower_timeframe_dataset_path=lower_path,
    )

    result = BacktestEngine().run(spec)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert manifest["lower_timeframe_dataset_path"] == str(lower_path)
    assert isinstance(manifest["lower_timeframe_dataset_sha256"], str)
    assert manifest["lower_timeframe_dataset_sha256"]
    assert manifest["cache_key_components"]["lower_timeframe_dataset_sha256"] == manifest["lower_timeframe_dataset_sha256"]


def test_lower_timeframe_cache_key_is_path_independent_when_content_matches(tmp_path: Path) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=120, variant="balanced")
    lower = pd.DataFrame(
        {
            "symbol": ["BTCUSDT"] * 8,
            "bar_time_ms": [1_712_649_600_000 + index * 60_000 for index in range(8)],
            "open": [100.0] * 8,
            "high": [100.5] * 8,
            "low": [99.5] * 8,
            "close": [100.0] * 8,
            "volume": [1.0] * 8,
        }
    )
    first_lower_path = tmp_path / "datasets" / "lower-a.parquet"
    second_lower_path = tmp_path / "relocated" / "lower-b.parquet"
    second_lower_path.parent.mkdir(parents=True, exist_ok=True)
    lower.to_parquet(first_lower_path, index=False)
    lower.to_parquet(second_lower_path, index=False)
    common = {
        "symbol": "BTCUSDT",
        "dataset_path": dataset.parquet_path,
        "dataset_sha256": dataset.parquet_sha256,
        "strategy_id": "baseline_no_trade",
        "holding_window": "1h",
        "feature_set_id": "features_price_trend_vol",
    }

    first = BacktestEngine().run(
        BacktestSpec(
            run_id="lower-a",
            output_dir=tmp_path / "backtests-a",
            lower_timeframe_dataset_path=first_lower_path,
            **common,
        )
    )
    second = BacktestEngine().run(
        BacktestSpec(
            run_id="lower-b",
            output_dir=tmp_path / "backtests-b",
            lower_timeframe_dataset_path=second_lower_path,
            **common,
        )
    )
    first_manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    second_manifest = json.loads(second.manifest_path.read_text(encoding="utf-8"))

    assert first_manifest["lower_timeframe_dataset_sha256"] == second_manifest["lower_timeframe_dataset_sha256"]
    assert first_manifest["cache_key"] == second_manifest["cache_key"]


def test_lower_timeframe_content_changes_cache_key(tmp_path: Path) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=120, variant="balanced")
    lower = pd.DataFrame(
        {
            "symbol": ["BTCUSDT"] * 8,
            "bar_time_ms": [1_712_649_600_000 + index * 60_000 for index in range(8)],
            "open": [100.0] * 8,
            "high": [100.5] * 8,
            "low": [99.5] * 8,
            "close": [100.0] * 8,
            "volume": [1.0] * 8,
        }
    )
    changed = lower.copy()
    changed.loc[0, "high"] = 101.0
    first_lower_path = tmp_path / "datasets" / "lower-a.parquet"
    second_lower_path = tmp_path / "datasets" / "lower-b.parquet"
    lower.to_parquet(first_lower_path, index=False)
    changed.to_parquet(second_lower_path, index=False)
    common = {
        "symbol": "BTCUSDT",
        "dataset_path": dataset.parquet_path,
        "dataset_sha256": dataset.parquet_sha256,
        "strategy_id": "baseline_no_trade",
        "holding_window": "1h",
        "feature_set_id": "features_price_trend_vol",
    }

    first = BacktestEngine().run(
        BacktestSpec(
            run_id="lower-a",
            output_dir=tmp_path / "backtests-a",
            lower_timeframe_dataset_path=first_lower_path,
            **common,
        )
    )
    second = BacktestEngine().run(
        BacktestSpec(
            run_id="lower-b",
            output_dir=tmp_path / "backtests-b",
            lower_timeframe_dataset_path=second_lower_path,
            **common,
        )
    )
    first_manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    second_manifest = json.loads(second.manifest_path.read_text(encoding="utf-8"))

    assert first_manifest["lower_timeframe_dataset_sha256"] != second_manifest["lower_timeframe_dataset_sha256"]
    assert first_manifest["cache_key"] != second_manifest["cache_key"]


def test_cache_key_changes_for_execution_assumptions_and_cost_model(tmp_path: Path) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=120, variant="balanced")
    common = {
        "symbol": "BTCUSDT",
        "output_dir": tmp_path / "backtests",
        "dataset_path": dataset.parquet_path,
        "dataset_sha256": dataset.parquet_sha256,
        "strategy_id": "baseline_no_trade",
        "holding_window": "1h",
        "feature_set_id": "features_price_trend_vol",
    }

    base = BacktestEngine().run(BacktestSpec(run_id="base", **common))
    latency = BacktestEngine().run(BacktestSpec(run_id="latency", entry_latency_ms=1_800_000, **common))
    costs = BacktestEngine().run(BacktestSpec(run_id="costs", fee_bps=12.0, **common))
    base_manifest = json.loads(base.manifest_path.read_text(encoding="utf-8"))
    latency_manifest = json.loads(latency.manifest_path.read_text(encoding="utf-8"))
    costs_manifest = json.loads(costs.manifest_path.read_text(encoding="utf-8"))

    assert base_manifest["cache_key"] != latency_manifest["cache_key"]
    assert base_manifest["cache_key"] != costs_manifest["cache_key"]


def test_backtest_cost_profile_and_fill_profile_participate_in_cache_identity(tmp_path: Path) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=120, variant="balanced")
    common = {
        "symbol": "BTCUSDT",
        "output_dir": tmp_path / "backtests",
        "dataset_path": dataset.parquet_path,
        "dataset_sha256": dataset.parquet_sha256,
        "strategy_id": "baseline_no_trade",
        "holding_window": "1h",
        "feature_set_id": "features_price_trend_vol",
    }

    base = BacktestEngine().run(BacktestSpec(run_id="base-profile", **common))
    stress_profile = BacktestEngine().run(
        BacktestSpec(
            run_id="stress-profile",
            cost_profile_id="binance_usdm_research_slippage_2x",
            slippage_bps=10.0,
            **common,
        )
    )
    explicit_fill = BacktestEngine().run(
        BacktestSpec(run_id="explicit-fill", fill_profile_id="vwap_approximation_fill", **common)
    )
    base_manifest = json.loads(base.manifest_path.read_text(encoding="utf-8"))
    stress_manifest = json.loads(stress_profile.manifest_path.read_text(encoding="utf-8"))
    fill_manifest = json.loads(explicit_fill.manifest_path.read_text(encoding="utf-8"))

    assert base_manifest["cache_key"] != stress_manifest["cache_key"]
    assert base_manifest["cache_key"] != fill_manifest["cache_key"]
    assert stress_manifest["cost_model"]["cost_profile_source"] == "registered_profile"
    assert stress_manifest["cost_model"]["cost_profile_id"] == "binance_usdm_research_slippage_2x"
    assert fill_manifest["cost_model"]["cost_profile_source"] == "registered_profile_with_numeric_or_fill_override"
    assert fill_manifest["cost_model"]["fill_profile_id"] == "vwap_approximation_fill"


def test_unknown_cost_or_fill_profile_fails_closed(tmp_path: Path) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=120, variant="balanced")
    common = {
        "symbol": "BTCUSDT",
        "output_dir": tmp_path / "backtests",
        "dataset_path": dataset.parquet_path,
        "dataset_sha256": dataset.parquet_sha256,
        "strategy_id": "baseline_no_trade",
        "holding_window": "1h",
        "feature_set_id": "features_price_trend_vol",
    }

    with pytest.raises(ValueError, match="unknown_cost_profile_id"):
        BacktestEngine().run(BacktestSpec(run_id="bad-cost-profile", cost_profile_id="unknown_venue", **common))
    with pytest.raises(ValueError, match="unknown_fill_profile_id"):
        BacktestEngine().run(BacktestSpec(run_id="bad-fill-profile", fill_profile_id="optimistic_fill", **common))


def test_signal_close_and_primary_open_latency_sources_have_distinct_fill_profiles(tmp_path: Path) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=120, variant="balanced")
    common = {
        "symbol": "BTCUSDT",
        "output_dir": tmp_path / "backtests",
        "dataset_path": dataset.parquet_path,
        "dataset_sha256": dataset.parquet_sha256,
        "strategy_id": "baseline_no_trade",
        "holding_window": "1h",
        "feature_set_id": "features_price_trend_vol",
    }

    old_source = BacktestEngine().run(
        BacktestSpec(
            run_id="signal-close-latency",
            entry_price_source="signal_bar_close_plus_latency",
            **common,
        )
    )
    explicit_open = BacktestEngine().run(
        BacktestSpec(
            run_id="primary-open-latency",
            entry_price_source="primary_bar_open_plus_latency",
            **common,
        )
    )
    old_manifest = json.loads(old_source.manifest_path.read_text(encoding="utf-8"))
    open_manifest = json.loads(explicit_open.manifest_path.read_text(encoding="utf-8"))

    assert old_manifest["execution_assumptions"]["entry_price_source"] == "signal_bar_close_plus_latency"
    assert old_manifest["cost_model"]["fill_profile_id"] == "signal_close_latency_fill"
    assert open_manifest["execution_assumptions"]["entry_price_source"] == "primary_bar_open_plus_latency"
    assert open_manifest["cost_model"]["fill_profile_id"] == "primary_bar_latency_fill"
    assert old_manifest["cache_key"] != open_manifest["cache_key"]


def test_backtest_manifest_records_non_fixed_exit_policy_identity(tmp_path: Path) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=120, variant="balanced")
    result = BacktestEngine().run(
        BacktestSpec(
            run_id="max-mae-stop",
            symbol="BTCUSDT",
            output_dir=tmp_path / "backtests",
            dataset_path=dataset.parquet_path,
            dataset_sha256=dataset.parquet_sha256,
            strategy_id="baseline_no_trade",
            holding_window="1h",
            feature_set_id="features_price_trend_vol",
            exit_policy_id="max_mae_stop",
            stop_return=0.01,
            exit_policy_params={"stop_return": 0.01},
        )
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert manifest["exit_policy_id"] == "max_mae_stop"
    assert manifest["execution_assumptions"]["exit_policy_id"] == "max_mae_stop"
    assert manifest["execution_assumptions"]["exit_policy_params"] == {"stop_return": 0.01}
    assert manifest["execution_assumptions"]["exit_price_source"] == "primary_close"


@pytest.mark.parametrize(
    "exit_policy_id",
    [
        "basis_normalization_exit_v1",
        "premium_normalization_exit_v1",
        "gmm_transition_exit_v1",
        "knn_remaining_edge_exit_v1",
        "knn_dynamic_barriers_v1",
    ],
)
def test_backtest_manifest_records_remaining_edge_exit_policy_identity(
    tmp_path: Path,
    exit_policy_id: str,
) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=120, variant="balanced")

    result = BacktestEngine().run(
        BacktestSpec(
            run_id=exit_policy_id,
            symbol="BTCUSDT",
            output_dir=tmp_path / "backtests",
            dataset_path=dataset.parquet_path,
            dataset_sha256=dataset.parquet_sha256,
            strategy_id="baseline_no_trade",
            holding_window="1h",
            feature_set_id="features_price_trend_vol",
            exit_policy_id=exit_policy_id,
        )
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert manifest["exit_policy_id"] == exit_policy_id
    assert manifest["execution_assumptions"]["exit_policy_id"] == exit_policy_id
    assert manifest["execution_assumptions"]["exit_price_source"] == "primary_close"
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False


def test_cache_key_changes_for_exit_policy_and_policy_parameters(tmp_path: Path) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=120, variant="balanced")
    common = {
        "symbol": "BTCUSDT",
        "output_dir": tmp_path / "backtests",
        "dataset_path": dataset.parquet_path,
        "dataset_sha256": dataset.parquet_sha256,
        "strategy_id": "baseline_no_trade",
        "holding_window": "1h",
        "feature_set_id": "features_price_trend_vol",
    }

    fixed = BacktestEngine().run(BacktestSpec(run_id="fixed", **common))
    first = BacktestEngine().run(
        BacktestSpec(
            run_id="funding-a",
            exit_policy_id="funding_adverse_exit",
            exit_policy_params={"funding_threshold": 0.00005},
            **common,
        )
    )
    second = BacktestEngine().run(
        BacktestSpec(
            run_id="funding-b",
            exit_policy_id="funding_adverse_exit",
            exit_policy_params={"funding_threshold": 0.0001},
            **common,
        )
    )
    funding_aware = BacktestEngine().run(
        BacktestSpec(
            run_id="funding-aware",
            exit_policy_id="funding_aware_exit_v1",
            exit_policy_params={
                "funding_threshold": 0.00005,
                "pre_funding_window_h": 1.0,
                "min_expected_cost_bps": 0.5,
                "edge_buffer_bps": 2.0,
            },
            **common,
        )
    )
    oi_contraction = BacktestEngine().run(
        BacktestSpec(
            run_id="oi-contraction",
            exit_policy_id="oi_contraction_exit_v1",
            exit_policy_params={
                "oi_delta_z_threshold": 1.0,
                "min_oi_delta_abs": 0.0,
                "max_unrealized_edge_bps": 5.0,
            },
            **common,
        )
    )
    fixed_manifest = json.loads(fixed.manifest_path.read_text(encoding="utf-8"))
    first_manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    second_manifest = json.loads(second.manifest_path.read_text(encoding="utf-8"))
    funding_aware_manifest = json.loads(funding_aware.manifest_path.read_text(encoding="utf-8"))
    oi_contraction_manifest = json.loads(oi_contraction.manifest_path.read_text(encoding="utf-8"))

    assert fixed_manifest["cache_key"] != first_manifest["cache_key"]
    assert first_manifest["cache_key"] != second_manifest["cache_key"]
    assert first_manifest["cache_key"] != funding_aware_manifest["cache_key"]
    assert funding_aware_manifest["cache_key"] != oi_contraction_manifest["cache_key"]
    assert funding_aware_manifest["execution_assumptions"]["exit_policy_id"] == "funding_aware_exit_v1"
    assert oi_contraction_manifest["execution_assumptions"]["exit_policy_id"] == "oi_contraction_exit_v1"


def _stable_test_hash(payload: object) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False).encode("utf-8")).hexdigest()
