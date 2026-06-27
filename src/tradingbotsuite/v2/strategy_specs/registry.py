# V2-AUDIT-ID: V2-AUD-STRAT-001
# V2-CONTRACTS: docs/contracts/strategy_spec_contract.md
# V2-BOUNDARY: research_only, declarative_specs_only, no_live_imports
# V2-OWNER: v2_strategy_specs
"""Allowed declarative strategy fields, indicators, and expressions."""

from __future__ import annotations

from enum import Enum


class StrategySignalType(str, Enum):
    CROSS_SECTIONAL_RANK = "cross_sectional_rank"
    MEAN_REVERSION = "mean_reversion"
    FUNDING_CARRY = "funding_carry"
    VOLATILITY_BREAKOUT = "volatility_breakout"
    VOL_ADJUSTED_TREND = "vol_adjusted_trend"
    LIQUIDITY_FILTERED = "liquidity_filtered"


class PriceBasis(str, Enum):
    CLOSE = "close"
    NEXT_BAR_OPEN = "next_bar_open"
    MARK = "mark"
    ORACLE = "oracle"


class UniverseMode(str, Enum):
    AS_OF = "as_of"
    CURRENT = "current"


class SpecEvidenceMode(str, Enum):
    ACCEPTED_RESEARCH = "accepted_research"
    REPORTED_EVIDENCE = "reported_evidence"
    SANDBOX_DIAGNOSTIC = "sandbox_diagnostic"


SUPPORTED_INPUT_FIELDS = frozenset(
    {
        "ts",
        "instrument_id",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "trade_count",
        "funding",
        "funding_rate",
        "open_interest",
        "mark_price",
        "oracle_price",
        "spread",
        "coverage_ratio",
    }
)

SUPPORTED_RANK_METRICS = frozenset(
    {
        "return",
        "funding",
        "volume",
        "volatility",
    }
)

SUPPORTED_FILTERS = frozenset(
    {
        "min_coverage",
        "max_funding_abs",
        "min_volume",
        "min_open_interest",
        "max_spread",
    }
)

SUPPORTED_FEE_MODELS = frozenset(
    {
        "conservative_hyperliquid_taker_v1",
        "conservative_perp_taker_v1",
        "v2_conservative_costs_v1",
    }
)

SUPPORTED_SLIPPAGE_MODELS = frozenset(
    {
        "volume_participation_v1",
        "conservative_bps_v1",
    }
)

REQUIRED_FIELDS_BY_SIGNAL_TYPE = {
    StrategySignalType.CROSS_SECTIONAL_RANK: frozenset({"close"}),
    StrategySignalType.MEAN_REVERSION: frozenset({"close"}),
    StrategySignalType.FUNDING_CARRY: frozenset({"funding"}),
    StrategySignalType.VOLATILITY_BREAKOUT: frozenset({"close"}),
    StrategySignalType.VOL_ADJUSTED_TREND: frozenset({"close"}),
    StrategySignalType.LIQUIDITY_FILTERED: frozenset({"close", "volume"}),
}

RANK_METRICS_BY_SIGNAL_TYPE = {
    StrategySignalType.CROSS_SECTIONAL_RANK: SUPPORTED_RANK_METRICS,
    StrategySignalType.LIQUIDITY_FILTERED: SUPPORTED_RANK_METRICS,
    StrategySignalType.FUNDING_CARRY: frozenset({"funding"}),
    StrategySignalType.MEAN_REVERSION: frozenset({"return", "volatility"}),
    StrategySignalType.VOLATILITY_BREAKOUT: frozenset({"return", "volatility"}),
    StrategySignalType.VOL_ADJUSTED_TREND: frozenset(
        {"return_over_volatility", "breakout_over_atr"}
    ),
}

FORBIDDEN_KEY_TOKENS = frozenset(
    {
        "api_key",
        "credential",
        "secret",
        "token",
        "private_key",
        "password",
        "wallet",
        "network",
        "url",
        "uri",
        "http",
        "https",
        "file",
        "path",
        "python",
        "import",
        "exec",
        "eval",
        "subprocess",
        "shell",
        "socket",
        "request",
        "live",
        "paper",
        "order",
        "sizing",
        "runtime",
        "account",
        "lockbox",
    }
)

FORBIDDEN_VALUE_TOKENS = frozenset(
    {
        "http://",
        "https://",
        "file://",
        "../",
        "..\\",
        ".env",
        "import ",
        "eval(",
        "exec(",
        "subprocess",
        "socket.",
        "requests.",
        "open(",
        "lambda ",
        "__import__",
        "os.",
        "sys.",
        "python:",
        "live",
        "paper",
        "place_order",
        "submit_order",
        "order_placement",
        "sizing_instruction",
        "runtime_mode",
        "private_key",
        "api_key",
        "credential",
        "secret",
    }
)


def registry_summary() -> dict[str, tuple[str, ...]]:
    return {
        "signal_types": tuple(item.value for item in StrategySignalType),
        "input_fields": tuple(sorted(SUPPORTED_INPUT_FIELDS)),
        "rank_metrics": tuple(sorted(SUPPORTED_RANK_METRICS)),
        "filters": tuple(sorted(SUPPORTED_FILTERS)),
        "fee_models": tuple(sorted(SUPPORTED_FEE_MODELS)),
        "slippage_models": tuple(sorted(SUPPORTED_SLIPPAGE_MODELS)),
        "price_basis": tuple(item.value for item in PriceBasis),
    }
