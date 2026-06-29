from __future__ import annotations

import json
import math
from pathlib import Path

import pyarrow.parquet as pq
import pytest
from pydantic import ValidationError

from tradingbotsuite.v2.backtest_engine import BacktestRunConfig, RunStatus, run_vectorized_backtest
from tradingbotsuite.v2.backtest_engine.artifacts import BacktestMetrics
from tradingbotsuite.v2.costs import (
    CostModelConfig,
    CostStressScenario,
    calculate_cost_breakdown,
)
from tradingbotsuite.v2.strategy_specs import example_strategy_payloads


HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64


def test_cost_model_applies_fees_to_turnover() -> None:
    config = CostModelConfig(fee_bps=10.0, spread_bps=0.0, slippage_bps=0.0, impact_bps=0.0)

    breakdown = calculate_cost_breakdown(
        config=config,
        weight_delta=0.4,
        applied_weight=0.0,
        funding_rate=0.0,
        volume_notional=1_000_000.0,
    )

    assert breakdown.fee_cost == pytest.approx(0.0004)
    assert breakdown.total_transaction_cost == pytest.approx(0.0004)


def test_cost_model_defaults_account_notional_and_five_bps_spread() -> None:
    config = CostModelConfig()

    assert config.account_notional_usd == pytest.approx(10_000.0)
    assert config.spread_bps == pytest.approx(5.0)


def test_capacity_participation_uses_usd_account_notional_regression() -> None:
    config = CostModelConfig(account_notional_usd=10_000.0)

    breakdown = calculate_cost_breakdown(
        config=config,
        weight_delta=0.025,
        applied_weight=0.0,
        funding_rate=0.0,
        volume_notional=92_487_298.3102,
    )

    assert breakdown.trade_notional_usd == pytest.approx(250.0)
    assert breakdown.participation_rate == pytest.approx(0.025 * 10_000.0 / 92_487_298.3102)


def test_maker_assumption_requires_queue_model() -> None:
    with pytest.raises(ValidationError, match="maker_assumption_requires_queue_model"):
        CostModelConfig(cost_model_id="mixed_maker_taker_research_v1", fee_side="maker")


def test_gross_only_result_cannot_enter_leaderboard() -> None:
    with pytest.raises(ValidationError, match="gross-only"):
        BacktestMetrics(
            run_id="gross-only",
            status=RunStatus.SUCCEEDED,
            gross_return=0.1,
            net_return=0.1,
            gross_equity_final=1.1,
            net_equity_final=1.1,
            total_fee_cost=0.0,
            total_spread_cost=0.0,
            total_slippage_cost=0.0,
            total_impact_cost=0.0,
            total_transaction_cost=0.0,
            total_funding_pnl=0.0,
            total_turnover=0.0,
            trade_count=0,
            position_row_count=0,
            gross_only=True,
        )


def test_funding_pnl_changes_net_return(tmp_path) -> None:
    spec = _short_spec("hl_cross_sectional_momentum_v1")
    funded = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="funded-run"),
        strategy_spec=spec,
        panel_rows=_panel_rows(funding_scale=1.0, spread=0.0),
    )
    unfunded = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="unfunded-run"),
        strategy_spec=spec,
        panel_rows=_panel_rows(funding_scale=0.0, spread=0.0),
    )

    assert funded.metrics is not None
    assert unfunded.metrics is not None
    assert funded.metrics.total_funding_pnl != 0
    assert unfunded.metrics.total_funding_pnl == 0
    assert funded.metrics.net_return != unfunded.metrics.net_return


def test_spread_slippage_and_impact_reduce_net_return(tmp_path) -> None:
    zero_cost = CostModelConfig(
        cost_model_id="zero_research_costs_v1",
        fee_bps=0.0,
        spread_bps=0.0,
        slippage_bps=0.0,
        impact_bps=0.0,
    )
    costed = CostModelConfig(
        cost_model_id="phase12_costed_research_v1",
        fee_bps=6.0,
        spread_bps=2.0,
        slippage_bps=3.0,
        impact_bps=1.0,
    )
    panel = _panel_rows(funding_scale=0.0, spread=0.0)
    spec = _short_spec("hl_cross_sectional_momentum_v1")

    zero_result = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="zero-cost", cost_model=zero_cost),
        strategy_spec=spec,
        panel_rows=panel,
    )
    costed_result = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="costed", cost_model=costed),
        strategy_spec=spec,
        panel_rows=panel,
    )

    assert zero_result.metrics is not None
    assert costed_result.metrics is not None
    assert costed_result.metrics.total_transaction_cost > zero_result.metrics.total_transaction_cost
    assert costed_result.metrics.total_spread_cost > 0
    assert costed_result.metrics.total_slippage_cost > 0
    assert costed_result.metrics.total_impact_cost > 0
    assert costed_result.metrics.net_return < zero_result.metrics.net_return


def test_explicit_spread_units_preferred_over_fraction_inference(tmp_path) -> None:
    cost_model = CostModelConfig(
        cost_model_id="explicit_spread_units_research_v1",
        fee_bps=0.0,
        spread_bps=0.0,
        slippage_bps=0.0,
        impact_bps=0.0,
    )
    panel = _panel_rows(funding_scale=0.0, spread=0.5)
    for row in panel:
        row["spread_units"] = "bps"

    result = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="explicit-spread-units", cost_model=cost_model),
        strategy_spec=_short_spec("hl_cross_sectional_momentum_v1"),
        panel_rows=panel,
    )

    assert result.metrics is not None
    assert result.metrics.total_spread_cost == pytest.approx(
        result.metrics.total_turnover * 0.5 / 10_000.0
    )


def test_stress_2x_and_3x_costs_are_reported(tmp_path) -> None:
    result = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="stress-matrix"),
        strategy_spec=_short_spec("hl_cross_sectional_momentum_v1"),
        panel_rows=_panel_rows(funding_scale=0.0, spread=0.0),
    )
    run_dir = Path(result.run_dir)
    cost_stress = pq.read_table(run_dir / "cost_stress.parquet").to_pylist()
    by_scenario = {row["scenario_id"]: row for row in cost_stress}

    assert set(by_scenario) == {"base", "stress_2x", "stress_3x"}
    assert by_scenario["stress_2x"]["cost_multiplier"] == 2.0
    assert by_scenario["stress_3x"]["cost_multiplier"] == 3.0
    assert math.isclose(
        by_scenario["stress_2x"]["total_transaction_cost"],
        by_scenario["base"]["total_transaction_cost"] * 2.0,
        rel_tol=1e-12,
    )
    assert math.isclose(
        by_scenario["stress_3x"]["total_transaction_cost"],
        by_scenario["base"]["total_transaction_cost"] * 3.0,
        rel_tol=1e-12,
    )
    assert by_scenario["stress_3x"]["net_return"] < by_scenario["base"]["net_return"]


def test_cost_manifest_records_model_hash_and_cost_sensitivity(tmp_path) -> None:
    result = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="cost-manifest"),
        strategy_spec=_short_spec("hl_cross_sectional_momentum_v1"),
        panel_rows=_panel_rows(funding_scale=0.0, spread=0.0),
    )
    run_dir = Path(result.run_dir)
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    cost_manifest = json.loads((run_dir / "cost_manifest.json").read_text(encoding="utf-8"))

    assert manifest["cost_model_hash"] == cost_manifest["cost_model_hash"]
    assert cost_manifest["schema_version"] == "cost_manifest_v1"
    assert manifest["account_notional_usd"] == pytest.approx(10_000.0)
    assert cost_manifest["cost_model_config"]["account_notional_usd"] == pytest.approx(10_000.0)
    assert cost_manifest["spread_model"]["configured_spread_bps"] == pytest.approx(5.0)
    assert cost_manifest["spread_model"]["default_fallback_bps"] == pytest.approx(5.0)
    assert cost_manifest["spread_model"]["explicit_spread_bps_preferred"] is True
    assert cost_manifest["funding_model"]["rate_units"] == "interval_return_fraction"
    assert cost_manifest["funding_model"]["positive_rate_sign_convention"] == "positive_funding_longs_pay_shorts"
    assert cost_manifest["stress_matrix"]["base"]["reported"] is True
    assert cost_manifest["stress_matrix"]["stress_2x"]["reported"] is True
    assert cost_manifest["stress_matrix"]["stress_3x"]["reported"] is True
    assert cost_manifest["cost_sensitivity"]["base_cost_net_return"] is not None
    assert cost_manifest["cost_sensitivity"]["stress_2x_net_return"] is not None
    assert cost_manifest["cost_sensitivity"]["stress_3x_net_return"] is not None
    assert cost_manifest["research_only"] is True
    assert cost_manifest["promotion_ready"] is False


def test_liquidity_participation_cap_rejects_oversized_trade(tmp_path) -> None:
    tight_cost_model = CostModelConfig(
        cost_model_id="tight_capacity_research_v1",
        max_volume_participation=0.000000000001,
    )

    result = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="capacity-blocked", cost_model=tight_cost_model),
        strategy_spec=_short_spec("hl_cross_sectional_momentum_v1"),
        panel_rows=_panel_rows(volume=1.0, spread=0.0),
    )

    assert result.manifest.status == RunStatus.FAILED
    assert "liquidity_participation_cap_exceeded" in (result.manifest.failure_reason or "")
    assert (Path(result.run_dir) / "cost_stress.parquet").exists()


def _config(
    output_root: Path,
    *,
    run_id: str,
    cost_model: CostModelConfig | None = None,
) -> BacktestRunConfig:
    return BacktestRunConfig(
        run_id=run_id,
        experiment_id="phase12-test",
        output_root=str(output_root),
        archive_snapshot_id="archive-snapshot",
        universe_snapshot_id="universe-snapshot",
        data_manifest_id="data-manifest",
        data_manifest_hash=HEX_A,
        validation_manifest_hash=HEX_B,
        cost_manifest_hash=HEX_C,
        cost_model_id=(cost_model.cost_model_id if cost_model is not None else "conservative_hyperliquid_taker_v1"),
        cost_model=cost_model,
        universe_mode="as_of",
        venue_scope="hyperliquid",
        git_sha="test-git-sha",
    )


def _short_spec(strategy_id: str):
    payload = example_strategy_payloads()[strategy_id]
    payload = json.loads(json.dumps(payload))
    payload["logic"]["lookback_hours"] = 2
    payload["logic"]["lookback_bars"] = 2
    payload["inputs"]["fields"] = sorted(
        {
            *payload["inputs"]["fields"],
            "open",
            "high",
            "low",
            "close",
            "volume",
            "funding",
            "funding_rate",
            "open_interest",
            "mark_price",
            "oracle_price",
            "spread",
            "coverage_ratio",
        }
    )
    return payload


def _panel_rows(
    *,
    funding_scale: float = 1.0,
    volume: float = 100_000.0,
    spread: float = 0.001,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    instruments = {
        "hyperliquid:perp:BTC": 100.0,
        "hyperliquid:perp:ETH": 80.0,
        "hyperliquid:perp:SOL": 40.0,
    }
    for hour in range(12):
        ts = f"2024-01-01T{hour:02d}:00:00Z"
        for offset, (instrument_id, base) in enumerate(instruments.items()):
            drift = (hour * (offset + 1)) * (1 if offset != 1 else -0.5)
            open_price = base + drift
            close = open_price * (1.01 if offset == 0 else 0.995 if offset == 1 else 1.002)
            funding = (0.0002 if offset == 0 else -0.0001 if offset == 1 else 0.0) * funding_scale
            rows.append(
                {
                    "ts": ts,
                    "instrument_id": instrument_id,
                    "open": open_price,
                    "high": max(open_price, close) * 1.01,
                    "low": min(open_price, close) * 0.99,
                    "close": close,
                    "volume": volume + (hour * 1000) + offset,
                    "funding": funding,
                    "funding_rate": funding,
                    "open_interest": 2_000_000.0 + offset,
                    "mark_price": close,
                    "oracle_price": close,
                    "spread": spread,
                    "coverage_ratio": 1.0,
                }
            )
    return rows
