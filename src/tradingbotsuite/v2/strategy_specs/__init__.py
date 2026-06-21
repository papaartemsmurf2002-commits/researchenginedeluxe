# V2-AUDIT-ID: V2-AUD-PKG-001
# V2-CONTRACTS: docs/PRODUCT_SCOPE.md
# V2-BOUNDARY: research_only, no_live_imports, no_order_or_sizing
# V2-OWNER: v2_strategy_specs
"""V2 declarative strategy-spec bounded context."""

from __future__ import annotations

from tradingbotsuite.v2.strategy_specs.compiler import compile_signal_frame
from tradingbotsuite.v2.strategy_specs.examples import (
    example_strategy_payloads,
    example_strategy_specs,
)
from tradingbotsuite.v2.strategy_specs.registry import (
    PriceBasis,
    SpecEvidenceMode,
    StrategySignalType,
    UniverseMode,
    registry_summary,
)
from tradingbotsuite.v2.strategy_specs.schemas import (
    STRATEGY_SPEC_SCHEMA_VERSION,
    ExecutionConfig,
    MarketScope,
    RiskConfig,
    SignalFrame,
    SignalRow,
    StrategyInputs,
    StrategyLogic,
    StrategySpec,
    StrategySpecValidationResult,
    StrategyValidationConfig,
    strategy_spec_hash,
)
from tradingbotsuite.v2.strategy_specs.validator import (
    load_strategy_spec_file,
    parse_strategy_spec,
    validate_strategy_spec,
)

__all__ = [
    "STRATEGY_SPEC_SCHEMA_VERSION",
    "ExecutionConfig",
    "MarketScope",
    "PriceBasis",
    "RiskConfig",
    "SignalFrame",
    "SignalRow",
    "SpecEvidenceMode",
    "StrategyInputs",
    "StrategyLogic",
    "StrategySignalType",
    "StrategySpec",
    "StrategySpecValidationResult",
    "StrategyValidationConfig",
    "UniverseMode",
    "compile_signal_frame",
    "example_strategy_payloads",
    "example_strategy_specs",
    "load_strategy_spec_file",
    "parse_strategy_spec",
    "registry_summary",
    "strategy_spec_hash",
    "validate_strategy_spec",
]
