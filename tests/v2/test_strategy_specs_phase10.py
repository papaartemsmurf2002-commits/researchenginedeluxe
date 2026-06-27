from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tradingbotsuite.v2.strategy_specs import (
    SignalRow,
    StrategySpec,
    compile_signal_frame,
    example_strategy_payloads,
    registry_summary,
    validate_strategy_spec,
)


ROOT = Path(__file__).resolve().parents[2]


def test_declarative_example_strategies_validate() -> None:
    examples = example_strategy_payloads()
    validated = [validate_strategy_spec(payload) for payload in examples.values()]

    assert len(examples) >= 3
    assert all(result.ok for result in validated)
    assert all(result.spec_hash for result in validated)


def test_strategy_spec_rejects_live_or_order_language() -> None:
    payload = _base_payload()
    payload["metadata"] = {"thesis": "use live place_order path after signal"}

    result = validate_strategy_spec(payload)

    assert result.ok is False
    assert _errors(result).count("forbidden strategy side-effect content")
    assert "place_order" in _errors(result)


def test_strategy_spec_rejects_unknown_data_fields() -> None:
    payload = _base_payload()
    payload["inputs"]["fields"] = ["close", "wallet_balance"]

    result = validate_strategy_spec(payload)

    assert result.ok is False
    assert "unsupported input fields: wallet_balance" in _errors(result)


def test_strategy_spec_requires_cost_model() -> None:
    payload = _base_payload()
    del payload["execution"]["fee_model"]

    result = validate_strategy_spec(payload)

    assert result.ok is False
    assert "execution.fee_model" in _errors(result)


def test_strategy_cannot_access_network_or_credentials() -> None:
    payload = _base_payload()
    payload["parameters"] = {
        "data_url": "https://example.invalid/panel.parquet",
        "credential_ref": "env:API_KEY",
    }

    result = validate_strategy_spec(payload)

    assert result.ok is False
    assert "forbidden_key_url" in _errors(result)
    assert "forbidden_key_credential" in _errors(result)


def test_strategy_spec_rejects_arbitrary_files_python_and_lockbox_access() -> None:
    file_payload = _base_payload()
    file_payload["parameters"] = {"data_path": "C:/Users/papaa/.env"}
    python_payload = _base_payload()
    python_payload["parameters"] = {"custom_formula": "lambda row: row['close']"}
    lockbox_payload = _base_payload()
    lockbox_payload["validation"]["exclude_lockbox"] = False

    file_result = validate_strategy_spec(file_payload)
    python_result = validate_strategy_spec(python_payload)
    lockbox_result = validate_strategy_spec(lockbox_payload)

    assert file_result.ok is False
    assert "forbidden_key_path" in _errors(file_result)
    assert python_result.ok is False
    assert "lambda" in _errors(python_result)
    assert lockbox_result.ok is False
    assert "validation.exclude_lockbox must be true" in _errors(lockbox_result)


def test_strategy_spec_rejects_unsupported_indicator_expression() -> None:
    payload = _base_payload()
    payload["logic"]["signal_type"] = "arbitrary_python"

    result = validate_strategy_spec(payload)

    assert result.ok is False
    assert "logic.signal_type" in _errors(result)


def test_strategy_hash_changes_when_spec_changes() -> None:
    first = StrategySpec.model_validate(_base_payload())
    changed_payload = _base_payload()
    changed_payload["logic"]["entry_threshold"] = 2.0
    second = StrategySpec.model_validate(changed_payload)

    assert first.spec_hash != second.spec_hash


def test_strategy_spec_compiles_in_memory_panel_to_deterministic_signal_frame() -> None:
    payload = _base_payload()
    payload["logic"] = {
        "signal_type": "cross_sectional_rank",
        "lookback_bars": 1,
        "rank_metric": "return",
        "long_top_quantile": 0.5,
        "short_bottom_quantile": 0.5,
        "filters": {"min_coverage": 0.98},
    }
    payload["inputs"]["fields"] = ["close", "volume", "funding", "open_interest", "coverage_ratio"]
    rows = [
        _panel_row("2024-01-01T00:00:00Z", "hyperliquid:perp:BTC", close=100, volume=10_000),
        _panel_row("2024-01-01T00:00:00Z", "hyperliquid:perp:ETH", close=100, volume=10_000),
        _panel_row("2024-01-01T01:00:00Z", "hyperliquid:perp:BTC", close=110, volume=10_000),
        _panel_row("2024-01-01T01:00:00Z", "hyperliquid:perp:ETH", close=90, volume=10_000),
    ]

    first = compile_signal_frame(payload, rows)
    second = compile_signal_frame(payload, rows)
    second_hour = [row for row in first.rows if row.ts.hour == 1]

    assert first == second
    assert first.research_only is True
    assert first.promotion_ready is False
    assert first.model_dump()["candidate_evidence"] is False
    assert first.model_dump()["candidate_pack_eligible"] is False
    assert first.model_dump()["live_signal"] is False
    assert first.model_dump()["paper_signal"] is False
    assert first.model_dump()["sizing_instruction"] is False
    assert first.model_dump()["order_placement_instruction"] is False
    assert first.model_dump()["runtime_mode_change"] is False
    assert all(row.candidate_evidence is False for row in first.rows)
    assert all(row.candidate_pack_eligible is False for row in first.rows)
    assert all(row.live_signal is False for row in first.rows)
    assert all(row.paper_signal is False for row in first.rows)
    assert all(row.sizing_instruction is False for row in first.rows)
    assert all(row.order_placement_instruction is False for row in first.rows)
    assert all(row.runtime_mode_change is False for row in first.rows)
    assert {row.instrument_id: row.side for row in second_hour} == {
        "hyperliquid:perp:BTC": "long",
        "hyperliquid:perp:ETH": "short",
    }
    assert all(abs(row.target_weight) <= 0.05 for row in second_hour)


def test_cross_sectional_rank_reversion_longs_bottom_and_shorts_top() -> None:
    payload = _base_payload()
    payload["logic"] = {
        "signal_type": "cross_sectional_rank",
        "lookback_bars": 1,
        "rank_metric": "return",
        "rank_direction": "reversion",
        "long_top_quantile": 0.5,
        "short_bottom_quantile": 0.5,
        "filters": {"min_coverage": 0.98},
    }
    payload["inputs"]["fields"] = ["close", "volume", "coverage_ratio"]
    rows = [
        _panel_row("2024-01-01T00:00:00Z", "hyperliquid:perp:BTC", close=100, volume=10_000),
        _panel_row("2024-01-01T00:00:00Z", "hyperliquid:perp:ETH", close=100, volume=10_000),
        _panel_row("2024-01-01T01:00:00Z", "hyperliquid:perp:BTC", close=110, volume=10_000),
        _panel_row("2024-01-01T01:00:00Z", "hyperliquid:perp:ETH", close=90, volume=10_000),
    ]

    frame = compile_signal_frame(payload, rows)
    second_hour = [row for row in frame.rows if row.ts.hour == 1]

    assert {row.instrument_id: row.side for row in second_hour} == {
        "hyperliquid:perp:BTC": "short",
        "hyperliquid:perp:ETH": "long",
    }


def test_vol_adjusted_trend_scales_portfolio_weights_by_realized_volatility() -> None:
    payload = _base_payload()
    payload["strategy_id"] = "hl_vol_adjusted_trend_test_v1"
    payload["strategy_family"] = "vol_adjusted_trend"
    payload["inputs"]["fields"] = ["open", "high", "low", "close", "volume", "coverage_ratio"]
    payload["logic"] = {
        "signal_type": "vol_adjusted_trend",
        "lookback_bars": 2,
        "rank_metric": "return_over_volatility",
        "entry_threshold": 0.5,
        "filters": {"min_coverage": 0.98, "min_volume": 1000},
    }
    payload["parameters"] = {
        "volatility_lookback_bars": 2,
        "target_volatility_per_bar": 0.001,
        "volatility_floor": 0.0001,
    }
    payload["risk"] = {
        "max_gross_leverage": 0.08,
        "max_instrument_weight": 0.05,
        "rebalance": "1h",
    }
    rows = [
        _panel_row("2024-01-01T00:00:00Z", "hyperliquid:perp:BTC", close=100, volume=10_000),
        _panel_row("2024-01-01T00:00:00Z", "hyperliquid:perp:ETH", close=100, volume=10_000),
        _panel_row("2024-01-01T01:00:00Z", "hyperliquid:perp:BTC", close=101, volume=10_000),
        _panel_row("2024-01-01T01:00:00Z", "hyperliquid:perp:ETH", close=99, volume=10_000),
        _panel_row("2024-01-01T02:00:00Z", "hyperliquid:perp:BTC", close=103, volume=10_000),
        _panel_row("2024-01-01T02:00:00Z", "hyperliquid:perp:ETH", close=97, volume=10_000),
    ]

    frame = compile_signal_frame(payload, rows)
    third_hour = [row for row in frame.rows if row.ts.hour == 2]

    assert {row.instrument_id: row.side for row in third_hour} == {
        "hyperliquid:perp:BTC": "long",
        "hyperliquid:perp:ETH": "short",
    }
    assert sum(abs(row.target_weight) for row in third_hour) <= 0.08
    assert all(abs(row.target_weight) <= 0.05 for row in third_hour)


def test_signal_row_rejects_forbidden_boundary_flags() -> None:
    payload = _base_payload()
    result = compile_signal_frame(
        payload,
        [_panel_row("2024-01-01T00:00:00Z", "hyperliquid:perp:BTC", close=100, volume=10_000)],
    )
    row = result.rows[0].model_dump()
    row["live_signal"] = True

    with pytest.raises(ValueError, match="live_signal_must_be_false"):
        SignalRow.model_validate(row)


def test_strategy_spec_cli_validate_and_registry(tmp_path) -> None:
    spec_file = tmp_path / "strategy.json"
    spec_file.write_text(json.dumps(_base_payload()), encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")

    valid = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradingbotsuite.v2.cli.main",
            "strategy-spec",
            "validate",
            "--spec-file",
            str(spec_file),
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    registry = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradingbotsuite.v2.cli.main",
            "strategy-spec",
            "registry",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert valid.returncode == 0
    assert "strategy_spec_valid=true" in valid.stdout
    assert "spec_hash=" in valid.stdout
    assert registry.returncode == 0
    assert "cross_sectional_rank" in registry.stdout
    assert "conservative_hyperliquid_taker_v1" in registry.stdout


def test_registry_exposes_allowed_declarative_surface() -> None:
    summary = registry_summary()

    assert "cross_sectional_rank" in summary["signal_types"]
    assert "vol_adjusted_trend" in summary["signal_types"]
    assert "close" in summary["input_fields"]
    assert "volume_participation_v1" in summary["slippage_models"]


def _base_payload():
    return {
        "schema_version": "strategy_spec_v1",
        "strategy_id": "hl_mean_reversion_test_v1",
        "strategy_family": "mean_reversion",
        "version": "0.1.0",
        "owner": "agent",
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "market_scope": {
            "venue": "hyperliquid",
            "market_type": "perp",
            "universe_rule": "hl_perps_day_ntl_vlm_gte_5m_v1",
        },
        "inputs": {
            "timeframe": "1h",
            "fields": ["close", "volume", "coverage_ratio"],
        },
        "logic": {
            "signal_type": "mean_reversion",
            "lookback_bars": 3,
            "rank_metric": "return",
            "entry_threshold": 1.5,
            "exit_threshold": 0.25,
            "filters": {
                "min_coverage": 0.98,
                "min_volume": 1000,
            },
        },
        "risk": {
            "max_gross_leverage": 1.0,
            "max_instrument_weight": 0.05,
            "rebalance": "1h",
        },
        "execution": {
            "price_basis": "next_bar_open",
            "fee_model": "conservative_hyperliquid_taker_v1",
            "slippage_model": "volume_participation_v1",
        },
        "validation": {
            "min_backtest_months": 12,
            "earliest_start": "2024-01-01",
            "exclude_lockbox": True,
            "universe_mode": "as_of",
            "evidence_mode": "accepted_research",
        },
    }


def _panel_row(ts: str, instrument_id: str, *, close: float, volume: float):
    return {
        "ts": ts,
        "instrument_id": instrument_id,
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "volume": volume,
        "funding": 0.0,
        "open_interest": 1_000_000.0,
        "coverage_ratio": 1.0,
    }


def _errors(result) -> str:
    return "\n".join(result.errors)
