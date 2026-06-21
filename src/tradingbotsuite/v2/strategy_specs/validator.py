# V2-AUDIT-ID: V2-AUD-STRAT-001
# V2-CONTRACTS: docs/contracts/strategy_spec_contract.md
# V2-BOUNDARY: research_only, declarative_specs_only, no_live_imports
# V2-OWNER: v2_strategy_specs
"""Validation helpers for v2 declarative strategy specs."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from tradingbotsuite.v2.strategy_specs.schemas import (
    StrategySpec,
    StrategySpecValidationResult,
)


def validate_strategy_spec(payload: Mapping[str, Any] | StrategySpec) -> StrategySpecValidationResult:
    try:
        spec = payload if isinstance(payload, StrategySpec) else StrategySpec.model_validate(payload)
    except ValidationError as exc:
        return StrategySpecValidationResult(
            ok=False,
            errors=tuple(_format_error(error) for error in exc.errors()),
        )
    return StrategySpecValidationResult(
        ok=True,
        spec_hash=spec.spec_hash,
        strategy_id=spec.strategy_id,
    )


def parse_strategy_spec(payload: Mapping[str, Any] | StrategySpec) -> StrategySpec:
    if isinstance(payload, StrategySpec):
        return payload
    return StrategySpec.model_validate(payload)


def load_strategy_spec_file(path: str | Path) -> dict[str, Any]:
    spec_path = Path(path)
    text = spec_path.read_text(encoding="utf-8")
    if spec_path.suffix.lower() in {".yaml", ".yml"}:
        import yaml

        loaded = yaml.safe_load(text)
    else:
        loaded = json.loads(text)
    if not isinstance(loaded, dict):
        raise ValueError("strategy spec file must contain an object")
    return loaded


def _format_error(error: Mapping[str, Any]) -> str:
    loc = ".".join(str(part) for part in error.get("loc", ())) or "$"
    message = str(error.get("msg", "validation error"))
    return f"{loc}: {message}"
