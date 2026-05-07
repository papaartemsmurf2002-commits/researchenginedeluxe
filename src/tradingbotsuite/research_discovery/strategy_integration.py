from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from tradingbotsuite.research.live_readiness import research_boundary_metadata
from tradingbotsuite.research_discovery.state import atomic_write_json
from tradingbotsuite.strategies import get_strategy_plugin, validate_signal_frame
from tradingbotsuite.strategies.hmm_knn_local_analog_filter import REQUIRED_HMM_KNN_LOCAL_ANALOG_COLUMNS


DISCOVERY_STRATEGY_ACCOUNTING_MANIFEST_VERSION = "discovery-strategy-accounting-manifest-v1"
DISCOVERY_STRATEGY_INTEGRATION_VERSION = "discovery-hmm-knn-strategy-integration-v1"


@dataclass(frozen=True, slots=True)
class DiscoveryStrategyAccountingResult:
    manifest: dict[str, Any]
    signals: pd.DataFrame


@dataclass(frozen=True, slots=True)
class DiscoveryStrategyAccountingArtifactResult:
    output_dir: Path
    manifest_path: Path
    signals_path: Path


def account_hmm_knn_local_analog_strategy(
    frame: pd.DataFrame,
    *,
    symbol: str = "BTCUSDT",
    holding_window: str = "24h",
    feature_set_id: str = "features_perp_context_v2",
    strategy_config: Mapping[str, Any] | None = None,
    executed_trade_count: int | None = None,
) -> DiscoveryStrategyAccountingResult:
    missing = [column for column in REQUIRED_HMM_KNN_LOCAL_ANALOG_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"discovery_strategy_accounting_missing_columns:{','.join(missing)}")
    config = {
        **dict(strategy_config or {}),
        "symbol": symbol.upper(),
        "holding_period": holding_window,
        "feature_set_id": feature_set_id,
    }
    plugin = get_strategy_plugin("hmm_knn_local_analog_filter_v2", config=config)
    signals = plugin.predict(frame.copy())
    validation = validate_signal_frame(signals)
    if not validation.valid:
        raise ValueError("; ".join(validation.errors))
    executable = _executable_signals(signals)
    manifest = {
        "strategy_accounting_manifest_version": DISCOVERY_STRATEGY_ACCOUNTING_MANIFEST_VERSION,
        "strategy_integration_version": DISCOVERY_STRATEGY_INTEGRATION_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "strategy_id": "hmm_knn_local_analog_filter_v2",
        "symbol": symbol.upper(),
        "holding_window": holding_window,
        "feature_set_id": feature_set_id,
        "strategy_config": config,
        "row_count": int(len(frame)),
        "raw_knn_accepted_row_count": int(_accepted_knn_rows(frame).sum()),
        "plugin_signal_count": int(len(signals)),
        "backtest_executable_signal_count": int(len(executable)),
        "filter_block_count": int(max(0, len(signals) - len(executable))),
        "executed_trade_count": int(executed_trade_count) if executed_trade_count is not None else None,
        "side_counts": signals["side"].astype(str).str.lower().value_counts().to_dict() if "side" in signals else {},
        "executable_side_counts": (
            executable["side"].astype(str).str.lower().value_counts().to_dict()
            if "side" in executable
            else {}
        ),
        "signal_contract_valid": validation.valid,
        "signal_contract_errors": list(validation.errors),
        "required_materialized_columns": list(REQUIRED_HMM_KNN_LOCAL_ANALOG_COLUMNS),
        "split_safety_rule": "neighbor_min_source_index <= neighbor_max_source_index <= hmm_fit_end_row < source_row_index",
        "live_fetch_used": False,
        "order_placement_used": False,
        "runtime_mode_changed": False,
    }
    manifest["accounting_sha256"] = _stable_hash(
        {
            "strategy_id": manifest["strategy_id"],
            "strategy_config": config,
            "row_count": manifest["row_count"],
            "raw_knn_accepted_row_count": manifest["raw_knn_accepted_row_count"],
            "plugin_signal_count": manifest["plugin_signal_count"],
            "backtest_executable_signal_count": manifest["backtest_executable_signal_count"],
            "filter_block_count": manifest["filter_block_count"],
            "executed_trade_count": manifest["executed_trade_count"],
        }
    )
    return DiscoveryStrategyAccountingResult(manifest=manifest, signals=signals)


def write_strategy_accounting_artifacts(
    output_dir: Path,
    result: DiscoveryStrategyAccountingResult,
) -> DiscoveryStrategyAccountingArtifactResult:
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "strategy_accounting_manifest.json"
    signals_path = output_dir / "strategy_signals.parquet"
    result.signals.to_parquet(signals_path, index=False)
    manifest = dict(result.manifest)
    manifest["required_outputs"] = {
        "strategy_accounting_manifest": str(manifest_path),
        "strategy_signals": str(signals_path),
    }
    manifest["strategy_signals_sha256"] = _file_sha256(signals_path)
    atomic_write_json(manifest_path, manifest)
    return DiscoveryStrategyAccountingArtifactResult(
        output_dir=output_dir,
        manifest_path=manifest_path,
        signals_path=signals_path,
    )


def _executable_signals(signals: pd.DataFrame) -> pd.DataFrame:
    if signals.empty:
        return signals.copy()
    return signals.loc[
        (signals["side"].astype(str).str.lower() != "flat")
        & signals["skip_reason"].map(_skip_reason_clear)
    ].copy()


def _accepted_knn_rows(frame: pd.DataFrame) -> pd.Series:
    return frame["accepted_by_knn"].map(_strict_bool_flag) & frame["knn_skip_reason"].map(_skip_reason_clear)


def _strict_bool_flag(value: Any) -> bool:
    if isinstance(value, bool):
        return bool(value)
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _skip_reason_clear(value: Any) -> bool:
    if value is None or pd.isna(value):
        return True
    return str(value).strip().lower() in {"", "none", "nan", "null"}


def _stable_hash(payload: Any) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False).encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
