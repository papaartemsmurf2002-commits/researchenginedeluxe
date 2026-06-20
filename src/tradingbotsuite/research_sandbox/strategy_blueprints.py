from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from tradingbotsuite.research_sandbox.spec import StrategyCatalogRow, stable_payload


BLUEPRINT_PARAM_KEY = "sandbox_blueprint_id"
BLUEPRINT_VERSION = "sandbox_blueprint_v1"
SIGNAL_ALIAS_ATTR = "sandbox_signal_column_aliases"
BLUEPRINT_SIGNAL_PARAM_KEYS: dict[str, tuple[str, ...]] = {
    "close_momentum_proxy": ("lookback_bars", "return_threshold"),
    "range_reversion_proxy": ("lookback_bars", "zscore_threshold"),
    "volatility_breakout_proxy": ("lookback_bars",),
    "no_trade_proxy": (),
}


@dataclass(frozen=True)
class SandboxStrategyBlueprint:
    blueprint_id: str
    family: str
    signal_kind: str
    required_columns: tuple[str, ...] = ("close",)
    default_params: dict[str, Any] = field(default_factory=dict)
    diagnostic_only: bool = True


BUILTIN_BLUEPRINTS: dict[str, SandboxStrategyBlueprint] = {
    "close_momentum_proxy": SandboxStrategyBlueprint(
        blueprint_id="close_momentum_proxy",
        family="momentum",
        signal_kind="completed_bar_close_momentum",
        default_params={"lookback_bars": 2, "return_threshold": 0.0},
    ),
    "range_reversion_proxy": SandboxStrategyBlueprint(
        blueprint_id="range_reversion_proxy",
        family="range_reversion",
        signal_kind="completed_bar_rolling_zscore_reversion",
        default_params={"lookback_bars": 5, "zscore_threshold": 0.75},
    ),
    "volatility_breakout_proxy": SandboxStrategyBlueprint(
        blueprint_id="volatility_breakout_proxy",
        family="volatility_breakout",
        signal_kind="completed_bar_prior_range_breakout",
        required_columns=("close", "high", "low"),
        default_params={"lookback_bars": 4},
    ),
    "no_trade_proxy": SandboxStrategyBlueprint(
        blueprint_id="no_trade_proxy",
        family="no_trade",
        signal_kind="completed_bar_no_trade_proxy",
        default_params={},
    ),
}

STRATEGY_ID_BLUEPRINTS: dict[str, str] = {
    "trend_following_v1": "close_momentum_proxy",
    "volatility_breakout_v1": "volatility_breakout_proxy",
    "range_reversion_v1": "range_reversion_proxy",
    "baseline_no_trade": "no_trade_proxy",
    "funding_basis_v1": "close_momentum_proxy",
    "perp_basis_convergence_v2": "close_momentum_proxy",
    "funding_crowding_fade_v2": "range_reversion_proxy",
    "funding_window_timing_v1": "close_momentum_proxy",
    "oi_flow_breakout_v2": "volatility_breakout_proxy",
    "hmm_knn_local_analog_filter_v2": "close_momentum_proxy",
}

FAMILY_ALIASES: dict[str, str] = {
    "trend_continuation": "close_momentum_proxy",
    "trend": "close_momentum_proxy",
    "momentum": "close_momentum_proxy",
    "knn": "close_momentum_proxy",
    "flow": "close_momentum_proxy",
    "lead": "close_momentum_proxy",
    "vwap": "close_momentum_proxy",
    "range": "range_reversion_proxy",
    "reversion": "range_reversion_proxy",
    "fade": "range_reversion_proxy",
    "mean": "range_reversion_proxy",
    "motif": "range_reversion_proxy",
    "breakout": "volatility_breakout_proxy",
    "squeeze": "volatility_breakout_proxy",
    "volatility": "volatility_breakout_proxy",
    "wick": "volatility_breakout_proxy",
}


def _slug(value: Any, *, fallback: str = "strategy") -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", str(value).strip().lower()).strip("_")
    return text or fallback


def _short_hash(payload: Any, *, length: int = 10) -> str:
    encoded = repr(stable_payload(payload)).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:length]


def signal_column_for(hypothesis_id: str, blueprint_id: str, side: str) -> str:
    slug = _slug(hypothesis_id, fallback="hypothesis")[:36]
    digest = _short_hash({"hypothesis_id": hypothesis_id, "blueprint_id": blueprint_id, "side": side}, length=8)
    return f"sandbox_signal_{_slug(blueprint_id)}_{slug}_{side}_{digest}"


def infer_blueprint_id(*values: Any) -> str:
    text = " ".join(str(value).lower() for value in values if value is not None)
    for token, blueprint_id in FAMILY_ALIASES.items():
        if token in text:
            return blueprint_id
    return "close_momentum_proxy"


def infer_sides(*values: Any, default_sides: tuple[str, ...] = ("long", "short")) -> tuple[str, ...]:
    text = " ".join(str(value).lower() for value in values if value is not None)
    has_long = "long" in text
    has_short = "short" in text
    if has_long and not has_short:
        return ("long",)
    if has_short and not has_long:
        return ("short",)
    if "anti" in text or "inverse" in text:
        return ("short",)
    return default_sides


def _coerce_params(params: dict[str, Any] | None) -> dict[str, Any]:
    if params is None:
        return {}
    return {str(key): stable_payload(value) for key, value in params.items()}


def _strategy_row(
    *,
    hypothesis_id: str,
    family: str,
    source_id: str,
    blueprint_id: str,
    side: str,
    source_metadata: dict[str, Any] | None = None,
    blueprint_params: dict[str, Any] | None = None,
    tags: tuple[str, ...] = (),
    notes: str = "",
) -> StrategyCatalogRow:
    if blueprint_id not in BUILTIN_BLUEPRINTS:
        raise ValueError(f"unsupported sandbox blueprint_id: {blueprint_id}")
    signal_column = signal_column_for(hypothesis_id, blueprint_id, side)
    blueprint = BUILTIN_BLUEPRINTS[blueprint_id]
    params = {
        BLUEPRINT_PARAM_KEY: blueprint_id,
        "sandbox_blueprint_version": BLUEPRINT_VERSION,
        "sandbox_proxy_signal": True,
        "sandbox_proxy_only": True,
        "proxy_strategy_policy": "proxy_only_diagnostic_not_strict_strategy_evidence",
        "strict_cycle_strategy_execution": False,
        "candidate_evidence_from_proxy_allowed": False,
        "signal_kind": blueprint.signal_kind,
        "required_columns": list(blueprint.required_columns),
        "diagnostic_only": blueprint.diagnostic_only,
        **blueprint.default_params,
        **_coerce_params(blueprint_params),
    }
    if source_metadata:
        params["source_metadata"] = stable_payload(source_metadata)
    return StrategyCatalogRow(
        hypothesis_id=hypothesis_id,
        family=family,
        source_id=source_id,
        signal_column=signal_column,
        side=side,
        params=params,
        tags=("sandbox_blueprint", "proxy_signal", *tags),
        notes=notes,
    )


def compile_strategy_config_payload(payload: Any, *, source_path: str | Path) -> list[StrategyCatalogRow]:
    source = Path(source_path)
    if isinstance(payload, list):
        rows: list[StrategyCatalogRow] = []
        for item in payload:
            rows.extend(compile_strategy_config_payload(item, source_path=source))
        return _dedupe_rows(rows)
    if not isinstance(payload, dict):
        return []

    if "strategy_id" in payload:
        return _compile_single_strategy_config(payload, source_path=source)

    rows = []
    for key in ("strategy_configs", "configs"):
        value = payload.get(key)
        if isinstance(value, list):
            for item in value:
                rows.extend(compile_strategy_config_payload(item, source_path=source))

    families = payload.get("families")
    if isinstance(families, list):
        for family in families:
            if isinstance(family, dict):
                rows.extend(_compile_strategy_family_payload(family, source_path=source))
    return _dedupe_rows(rows)


def _compile_single_strategy_config(payload: dict[str, Any], *, source_path: Path) -> list[StrategyCatalogRow]:
    strategy_id = str(payload["strategy_id"])
    blueprint_id = STRATEGY_ID_BLUEPRINTS.get(strategy_id, infer_blueprint_id(strategy_id, payload.get("feature_set_id")))
    family = str(payload.get("family_id") or payload.get("family") or strategy_id)
    version = payload.get("strategy_version")
    base_hypothesis = _slug("-".join(str(item) for item in (strategy_id, version) if item), fallback=strategy_id)
    source_metadata = {
        "source_type": "repo_strategy_config",
        "source_path": str(source_path),
        "strategy_id": strategy_id,
        "strategy_version": version,
        "feature_set_id": payload.get("feature_set_id"),
        "holding_period": payload.get("holding_period"),
        "enabled": payload.get("enabled", True),
        "source_parameters": stable_payload(payload.get("parameters", {})),
    }
    return [
        _strategy_row(
            hypothesis_id=f"{base_hypothesis}-{side}",
            family=family,
            source_id=str(source_path),
            blueprint_id=blueprint_id,
            side=side,
            source_metadata=source_metadata,
            tags=("repo_strategy_config", strategy_id),
            notes="Sandbox proxy compiled from repo strategy config.",
        )
        for side in infer_sides(strategy_id, payload.get("parameters"))
    ]


def _compile_strategy_family_payload(payload: dict[str, Any], *, source_path: Path) -> list[StrategyCatalogRow]:
    family_id = str(payload.get("family_id") or payload.get("display_name") or "strategy_family")
    plugin_rows = payload.get("selected_strategy_plugins") or []
    rows: list[StrategyCatalogRow] = []
    for plugin in plugin_rows:
        if not isinstance(plugin, dict) or not plugin.get("strategy_id"):
            continue
        strategy_id = str(plugin["strategy_id"])
        blueprint_id = STRATEGY_ID_BLUEPRINTS.get(strategy_id, infer_blueprint_id(family_id, strategy_id))
        for side in infer_sides(strategy_id, family_id):
            hypothesis_id = f"{_slug(family_id)}-{_slug(strategy_id)}-{side}"
            rows.append(
                _strategy_row(
                    hypothesis_id=hypothesis_id,
                    family=family_id,
                    source_id=str(source_path),
                    blueprint_id=blueprint_id,
                    side=side,
                    source_metadata={
                        "source_type": "repo_strategy_family_matrix",
                        "source_path": str(source_path),
                        "family_id": family_id,
                        "strategy_id": strategy_id,
                        "role": plugin.get("role"),
                        "feature_set_id": payload.get("feature_set_id"),
                        "holding_windows": stable_payload(payload.get("holding_windows", [])),
                    },
                    tags=("repo_strategy_family_matrix", strategy_id),
                    notes="Sandbox proxy compiled from repo strategy-family matrix.",
                )
            )
    return rows


LEAD_COLUMNS = {
    "lead",
    "candidate",
    "family",
    "template",
    "packet",
    "next_check",
    "promising_check",
    "detail_key",
}


def is_spreadsheet_lead_frame(frame: pd.DataFrame) -> bool:
    normalized = {_slug(column) for column in frame.columns}
    return bool(normalized.intersection(LEAD_COLUMNS)) and "signal_column" not in normalized


def compile_spreadsheet_lead_frame(
    frame: pd.DataFrame,
    *,
    source_path: str | Path,
) -> list[StrategyCatalogRow]:
    if not is_spreadsheet_lead_frame(frame):
        return []
    source = Path(source_path)
    rows: list[StrategyCatalogRow] = []
    for index, record in frame.reset_index(drop=True).iterrows():
        payload = {str(key): value for key, value in record.to_dict().items() if not _is_missing(value)}
        if not payload:
            continue
        text_values = tuple(payload.values())
        family = str(_first_present(payload, "Family", "Lead", "Packet", default="spreadsheet_lead"))
        lead_name = str(_first_present(payload, "Candidate", "Lead", "Template", "Detail Key", "Packet", default=f"lead-{index}"))
        source_sheet = payload.get("source_sheet")
        source_id = f"{source}#{source_sheet}" if source_sheet else str(source)
        blueprint_id = infer_blueprint_id(*text_values)
        for side in infer_sides(*text_values):
            hypothesis_id = f"{_slug(lead_name, fallback='lead')}-{side}-{index}"
            rows.append(
                _strategy_row(
                    hypothesis_id=hypothesis_id,
                    family=family,
                    source_id=source_id,
                    blueprint_id=blueprint_id,
                    side=side,
                    source_metadata={
                        "source_type": "spreadsheet_lead_catalog",
                        "source_path": str(source),
                        "source_sheet": source_sheet,
                        "row_index": index,
                        "source_columns": stable_payload(payload),
                    },
                    tags=("spreadsheet_lead_catalog",),
                    notes="Sandbox proxy compiled from spreadsheet-like lead catalog.",
                )
            )
    return _dedupe_rows(rows)


def _first_present(payload: dict[str, Any], *names: str, default: Any) -> Any:
    normalized = {_slug(key): key for key in payload}
    for name in names:
        key = normalized.get(_slug(name))
        if key is not None:
            return payload[key]
    return default


def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, float) and pd.isna(value)) or value == ""


def _dedupe_rows(rows: list[StrategyCatalogRow]) -> list[StrategyCatalogRow]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[StrategyCatalogRow] = []
    for row in rows:
        key = (row.hypothesis_id, row.side, row.signal_column)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def strategy_uses_blueprint(strategy: StrategyCatalogRow) -> bool:
    return str(strategy.params.get(BLUEPRINT_PARAM_KEY, "")) in BUILTIN_BLUEPRINTS


def blueprint_signal_cache_key(strategy: StrategyCatalogRow) -> tuple[Any, ...] | None:
    blueprint_id = str(strategy.params.get(BLUEPRINT_PARAM_KEY, ""))
    blueprint = BUILTIN_BLUEPRINTS.get(blueprint_id)
    if blueprint is None:
        return None
    params = _params_for(strategy, blueprint)
    signal_params = tuple(
        (key, repr(stable_payload(params.get(key))))
        for key in BLUEPRINT_SIGNAL_PARAM_KEYS.get(blueprint_id, ())
    )
    return (
        "sandbox_blueprint_signal",
        BLUEPRINT_VERSION,
        blueprint_id,
        blueprint.signal_kind,
        strategy.side,
        signal_params,
    )


def blueprint_materialized_signal_column(strategy: StrategyCatalogRow) -> str | None:
    signal_key = blueprint_signal_cache_key(strategy)
    if signal_key is None:
        return None
    blueprint_id = str(strategy.params.get(BLUEPRINT_PARAM_KEY, ""))
    digest = _short_hash(signal_key, length=10)
    return f"sandbox_signal_{_slug(blueprint_id)}_{_slug(strategy.side)}_{digest}"


def resolve_materialized_signal_column(market: pd.DataFrame, signal_column: str) -> str:
    aliases = market.attrs.get(SIGNAL_ALIAS_ATTR)
    if isinstance(aliases, dict):
        resolved = aliases.get(str(signal_column))
        if resolved is not None and str(resolved) in market.columns:
            return str(resolved)
    return str(signal_column)


def materialize_strategy_signals(
    market: pd.DataFrame,
    strategies: list[StrategyCatalogRow],
    *,
    dedupe_blueprint_signals: bool = False,
) -> pd.DataFrame:
    if not strategies:
        return market
    output = market.copy()
    signal_aliases = dict(output.attrs.get(SIGNAL_ALIAS_ATTR) or {})
    columns_by_signal_key: dict[tuple[Any, ...], str] = {}
    for strategy in strategies:
        blueprint_id = str(strategy.params.get(BLUEPRINT_PARAM_KEY, ""))
        if not blueprint_id or strategy.signal_column in output.columns:
            continue
        blueprint = BUILTIN_BLUEPRINTS.get(blueprint_id)
        if blueprint is None or any(column not in output.columns for column in blueprint.required_columns):
            continue
        target_column = strategy.signal_column
        signal_key = blueprint_signal_cache_key(strategy) if dedupe_blueprint_signals else None
        if signal_key is not None:
            target_column = columns_by_signal_key.get(signal_key) or blueprint_materialized_signal_column(strategy) or target_column
            columns_by_signal_key[signal_key] = target_column
            signal_aliases[strategy.signal_column] = target_column
        if target_column in output.columns:
            continue
        output[target_column] = _build_signal(output, strategy=strategy, blueprint=blueprint).astype(float)
    if signal_aliases:
        output.attrs[SIGNAL_ALIAS_ATTR] = {str(key): str(value) for key, value in signal_aliases.items()}
    return output


def _params_for(strategy: StrategyCatalogRow, blueprint: SandboxStrategyBlueprint) -> dict[str, Any]:
    return {**blueprint.default_params, **strategy.params}


def _int_param(params: dict[str, Any], name: str, default: int) -> int:
    try:
        value = int(params.get(name, default))
    except (TypeError, ValueError):
        return default
    return max(1, value)


def _float_param(params: dict[str, Any], name: str, default: float) -> float:
    try:
        return float(params.get(name, default))
    except (TypeError, ValueError):
        return default


def _build_signal(
    market: pd.DataFrame,
    *,
    strategy: StrategyCatalogRow,
    blueprint: SandboxStrategyBlueprint,
) -> pd.Series:
    params = _params_for(strategy, blueprint)
    if blueprint.blueprint_id == "close_momentum_proxy":
        return _close_momentum_signal(market, strategy=strategy, params=params)
    if blueprint.blueprint_id == "range_reversion_proxy":
        return _range_reversion_signal(market, strategy=strategy, params=params)
    if blueprint.blueprint_id == "volatility_breakout_proxy":
        return _volatility_breakout_signal(market, strategy=strategy, params=params)
    if blueprint.blueprint_id == "no_trade_proxy":
        return pd.Series(np.zeros(len(market), dtype=float), index=market.index)
    return pd.Series(np.zeros(len(market), dtype=float), index=market.index)


def _close_momentum_signal(market: pd.DataFrame, *, strategy: StrategyCatalogRow, params: dict[str, Any]) -> pd.Series:
    close = pd.to_numeric(market["close"], errors="coerce")
    lookback = _int_param(params, "lookback_bars", 2)
    threshold = _float_param(params, "return_threshold", 0.0)
    returns = close / close.shift(lookback) - 1.0
    signal = returns < -abs(threshold) if strategy.side == "short" else returns > abs(threshold)
    return signal.fillna(False).astype(float)


def _range_reversion_signal(market: pd.DataFrame, *, strategy: StrategyCatalogRow, params: dict[str, Any]) -> pd.Series:
    close = pd.to_numeric(market["close"], errors="coerce")
    lookback = _int_param(params, "lookback_bars", 5)
    threshold = abs(_float_param(params, "zscore_threshold", 0.75))
    mean = close.rolling(lookback, min_periods=lookback).mean()
    std = close.rolling(lookback, min_periods=lookback).std(ddof=0)
    zscore = (close - mean) / std.replace(0.0, np.nan)
    signal = zscore > threshold if strategy.side == "short" else zscore < -threshold
    return signal.fillna(False).astype(float)


def _volatility_breakout_signal(market: pd.DataFrame, *, strategy: StrategyCatalogRow, params: dict[str, Any]) -> pd.Series:
    close = pd.to_numeric(market["close"], errors="coerce")
    high = pd.to_numeric(market["high"], errors="coerce")
    low = pd.to_numeric(market["low"], errors="coerce")
    lookback = _int_param(params, "lookback_bars", 4)
    prior_high = high.shift(1).rolling(lookback, min_periods=lookback).max()
    prior_low = low.shift(1).rolling(lookback, min_periods=lookback).min()
    signal = close < prior_low if strategy.side == "short" else close > prior_high
    return signal.fillna(False).astype(float)
