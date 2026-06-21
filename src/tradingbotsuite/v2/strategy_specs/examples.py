# V2-AUDIT-ID: V2-AUD-STRAT-001
# V2-CONTRACTS: docs/contracts/strategy_spec_contract.md
# V2-BOUNDARY: research_only, declarative_examples, no_live_imports
# V2-OWNER: v2_strategy_specs
"""Built-in declarative strategy spec examples for Phase 10."""

from __future__ import annotations

from typing import Any

from tradingbotsuite.v2.strategy_specs.schemas import STRATEGY_SPEC_SCHEMA_VERSION, StrategySpec


def example_strategy_payloads() -> dict[str, dict[str, Any]]:
    base = {
        "schema_version": STRATEGY_SPEC_SCHEMA_VERSION,
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
    return {
        "hl_cross_sectional_momentum_v1": {
            **base,
            "strategy_id": "hl_cross_sectional_momentum_v1",
            "strategy_family": "cross_sectional_momentum",
            "inputs": {
                "timeframe": "1h",
                "fields": ["close", "volume", "funding", "open_interest", "coverage_ratio"],
            },
            "logic": {
                "signal_type": "cross_sectional_rank",
                "lookback_hours": 168,
                "rank_metric": "return",
                "long_top_quantile": 0.10,
                "short_bottom_quantile": 0.10,
                "filters": {
                    "min_coverage": 0.98,
                    "max_funding_abs": 0.001,
                },
            },
        },
        "hl_mean_reversion_v1": {
            **base,
            "strategy_id": "hl_mean_reversion_v1",
            "strategy_family": "mean_reversion",
            "inputs": {
                "timeframe": "1h",
                "fields": ["close", "volume", "coverage_ratio"],
            },
            "logic": {
                "signal_type": "mean_reversion",
                "lookback_bars": 24,
                "rank_metric": "return",
                "entry_threshold": 1.5,
                "exit_threshold": 0.25,
                "filters": {
                    "min_coverage": 0.98,
                    "min_volume": 1000,
                },
            },
        },
        "hl_funding_carry_v1": {
            **base,
            "strategy_id": "hl_funding_carry_v1",
            "strategy_family": "funding_carry",
            "inputs": {
                "timeframe": "1h",
                "fields": ["close", "funding", "volume", "coverage_ratio"],
            },
            "logic": {
                "signal_type": "funding_carry",
                "lookback_bars": 1,
                "rank_metric": "funding",
                "entry_threshold": 0.0001,
                "filters": {
                    "min_coverage": 0.98,
                    "min_volume": 1000,
                },
            },
        },
        "hl_volatility_breakout_v1": {
            **base,
            "strategy_id": "hl_volatility_breakout_v1",
            "strategy_family": "volatility_breakout",
            "inputs": {
                "timeframe": "1h",
                "fields": ["close", "high", "low", "volume", "coverage_ratio"],
            },
            "logic": {
                "signal_type": "volatility_breakout",
                "lookback_bars": 48,
                "rank_metric": "volatility",
                "filters": {
                    "min_coverage": 0.98,
                    "min_volume": 1000,
                },
            },
        },
        "hl_liquidity_filtered_momentum_v1": {
            **base,
            "strategy_id": "hl_liquidity_filtered_momentum_v1",
            "strategy_family": "liquidity_filtered_momentum",
            "inputs": {
                "timeframe": "1h",
                "fields": ["close", "volume", "open_interest", "spread", "coverage_ratio"],
            },
            "logic": {
                "signal_type": "liquidity_filtered",
                "lookback_hours": 72,
                "rank_metric": "return",
                "long_top_quantile": 0.20,
                "short_bottom_quantile": 0.20,
                "filters": {
                    "min_coverage": 0.98,
                    "min_volume": 25000,
                    "min_open_interest": 100000,
                    "max_spread": 0.02,
                },
            },
        },
    }


def example_strategy_specs() -> dict[str, StrategySpec]:
    return {
        strategy_id: StrategySpec.model_validate(payload)
        for strategy_id, payload in example_strategy_payloads().items()
    }
