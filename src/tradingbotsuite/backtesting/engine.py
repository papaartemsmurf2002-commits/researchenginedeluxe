from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from tradingbotsuite.backtesting.costs import CostModel
from tradingbotsuite.backtesting.execution_sim import ExecutionAssumptions, ExecutionSimulator
from tradingbotsuite.backtesting.metrics import REQUIRED_BACKTEST_METRICS, calculate_backtest_metrics
from tradingbotsuite.strategies import get_strategy_plugin, validate_signal_frame

BACKTEST_ENGINE_VERSION = "research-backtest-engine-v1"
BACKTEST_MANIFEST_VERSION = "backtest-manifest-v1"
BACKTEST_CACHE_POLICY = "identity_only_no_execution_cache"
SUPPORTED_HOLDING_WINDOWS_MS = {
    "1h": 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
    "12h": 12 * 60 * 60 * 1000,
    "24h": 24 * 60 * 60 * 1000,
    "72h": 72 * 60 * 60 * 1000,
    "7d": 7 * 24 * 60 * 60 * 1000,
}


@dataclass(frozen=True, slots=True)
class BacktestSpec:
    run_id: str
    symbol: str
    output_dir: Path
    dataset_path: Path | None = None
    strategy_id: str = "baseline_trend"
    holding_window: str = "24h"
    interval_ms: int = 900_000
    initial_equity: float = 10_000.0
    entry_latency_ms: int = 900_000
    entry_price_source: str = "next_bar_open"
    fee_bps: float = 5.0
    slippage_bps: float = 5.0
    spread_bps: float = 0.0
    funding_rate: float = 0.0
    exit_policy_id: str = "fixed_holding_window"
    target_return: float | None = None
    stop_return: float | None = None
    exit_policy_params: dict[str, Any] = field(default_factory=dict)
    exit_price_source: str = "primary_close"
    lower_timeframe_dataset_path: Path | None = None
    feature_set_id: str | None = None
    feature_manifest_sha256: str | None = None
    dataset_sha256: str | None = None
    strategy_config: dict[str, Any] = field(default_factory=dict)

    def resolved_config(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["output_dir"] = str(self.output_dir)
        payload["dataset_path"] = str(self.dataset_path) if self.dataset_path is not None else None
        payload["lower_timeframe_dataset_path"] = (
            str(self.lower_timeframe_dataset_path)
            if self.lower_timeframe_dataset_path is not None
            else None
        )
        payload["engine_version"] = BACKTEST_ENGINE_VERSION
        payload["research_only"] = True
        payload["observe_only"] = True
        payload["promotion_ready"] = False
        return payload

    def config_sha256(self) -> str:
        return _stable_hash(self.resolved_config())


@dataclass(frozen=True, slots=True)
class BacktestResult:
    output_dir: Path
    manifest_path: Path
    trades_path: Path
    signals_path: Path
    equity_curve_path: Path
    metrics_path: Path
    config_resolved_path: Path
    result_sha256: str


class BacktestEngine:
    def __init__(self, execution_simulator: ExecutionSimulator | None = None) -> None:
        self.execution_simulator = execution_simulator or ExecutionSimulator()

    def run(
        self,
        spec: BacktestSpec,
        *,
        market_data: pd.DataFrame | None = None,
        dataset: pd.DataFrame | None = None,
    ) -> BacktestResult:
        started = time.perf_counter()
        output_dir = spec.output_dir / spec.run_id
        output_dir.mkdir(parents=True, exist_ok=True)
        source_frame = self._load_source_frame(spec, dataset=dataset, market_data=market_data)
        lower_timeframe_market = _load_lower_timeframe_frame(spec)
        market = _market_frame(source_frame, symbol=spec.symbol)
        assumptions = _execution_assumptions(spec)
        signals, strategy_metadata = _signals_for_strategy(source_frame, spec)
        cost_model = CostModel(
            fee_bps=spec.fee_bps,
            slippage_bps=spec.slippage_bps,
            spread_bps=spec.spread_bps,
            funding_rate=spec.funding_rate,
        )
        trades, equity_curve = self.execution_simulator.simulate(
            signals,
            market,
            costs=cost_model,
            assumptions=assumptions,
            initial_equity=spec.initial_equity,
            lower_timeframe_market_data=lower_timeframe_market,
        )
        trades = _enrich_trades(trades, market)
        metrics = calculate_backtest_metrics(
            trades=trades,
            signals=signals,
            equity_curve=equity_curve,
            market_data=market,
            initial_equity=spec.initial_equity,
        )
        config_resolved = spec.resolved_config()
        source_hash = _source_hash(spec, source_frame)
        lower_timeframe_hash = _lower_timeframe_source_hash(spec, lower_timeframe_market)
        cache_key_components = _cache_key_components(
            dataset_sha256=source_hash,
            lower_timeframe_dataset_sha256=lower_timeframe_hash,
            feature_manifest_sha256=spec.feature_manifest_sha256,
            config_resolved=config_resolved,
            assumptions=assumptions,
            cost_model=cost_model,
        )
        cache_key = _stable_hash(cache_key_components)

        trades_path = output_dir / "trades.parquet"
        signals_path = output_dir / "signals.parquet"
        equity_curve_path = output_dir / "equity_curve.parquet"
        metrics_path = output_dir / "metrics.json"
        config_resolved_path = output_dir / "config_resolved.json"
        manifest_path = output_dir / "backtest_manifest.json"
        trades.to_parquet(trades_path, index=False)
        signals.to_parquet(signals_path, index=False)
        equity_curve.to_parquet(equity_curve_path, index=False)
        _write_json(metrics_path, metrics)
        _write_json(config_resolved_path, config_resolved)

        artifact_hashes = {
            "trades_sha256": _file_sha256(trades_path),
            "signals_sha256": _file_sha256(signals_path),
            "equity_curve_sha256": _file_sha256(equity_curve_path),
            "metrics_sha256": _file_sha256(metrics_path),
            "config_resolved_sha256": _file_sha256(config_resolved_path),
        }
        result_sha256 = _stable_hash(
            {
                "trades": _frame_hash(trades),
                "signals": _frame_hash(signals),
                "equity_curve": _frame_hash(equity_curve),
                "metrics": metrics,
                "config": _reproducible_config(config_resolved),
            }
        )
        manifest = {
            "backtest_manifest_version": BACKTEST_MANIFEST_VERSION,
            "engine_version": BACKTEST_ENGINE_VERSION,
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "symbol": spec.symbol,
            "strategy_id": spec.strategy_id,
            "strategy_metadata": strategy_metadata,
            "holding_window": spec.holding_window,
            "entry_price_source": spec.entry_price_source,
            "exit_policy_id": spec.exit_policy_id,
            "exit_price_source": spec.exit_price_source,
            "same_bar_entry_exit_allowed": False,
            "required_outputs": {
                "backtest_manifest": str(manifest_path),
                "trades": str(trades_path),
                "signals": str(signals_path),
                "equity_curve": str(equity_curve_path),
                "metrics": str(metrics_path),
                "config_resolved": str(config_resolved_path),
            },
            "required_metrics_present": all(key in metrics for key in REQUIRED_BACKTEST_METRICS),
            "row_count": int(len(market)),
            "signal_count": int(len(signals)),
            "trade_count": int(len(trades)),
            "dataset_path": str(spec.dataset_path) if spec.dataset_path is not None else None,
            "dataset_sha256": source_hash,
            "lower_timeframe_dataset_path": (
                str(spec.lower_timeframe_dataset_path)
                if spec.lower_timeframe_dataset_path is not None
                else None
            ),
            "lower_timeframe_dataset_sha256": lower_timeframe_hash,
            "feature_set_id": spec.feature_set_id,
            "feature_manifest_sha256": spec.feature_manifest_sha256,
            "config_sha256": spec.config_sha256(),
            "cache_key": cache_key,
            "cache_policy": BACKTEST_CACHE_POLICY,
            "cache_lookup_used": False,
            "cache_hit": False,
            "execution_cache_reuse_enabled": False,
            "cache_key_components": cache_key_components,
            "result_sha256": result_sha256,
            "artifact_hashes": artifact_hashes,
            "execution_assumptions": assumptions.to_payload(),
            "cost_model": cost_model.to_payload(),
            "runtime": {
                "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 6),
                "rows_per_second": round(len(market) / max(time.perf_counter() - started, 1e-9), 6),
            },
            "validity": {
                "future_features_used": False,
                "validation_rows_used_for_fit": False,
                "fees_slippage_funding_included": True,
                "in_sample_only": False,
                "wt3d_claim_requires_no_wt_baseline": False,
            },
        }
        _write_json(manifest_path, manifest)
        return BacktestResult(
            output_dir=output_dir,
            manifest_path=manifest_path,
            trades_path=trades_path,
            signals_path=signals_path,
            equity_curve_path=equity_curve_path,
            metrics_path=metrics_path,
            config_resolved_path=config_resolved_path,
            result_sha256=result_sha256,
        )

    def _load_source_frame(
        self,
        spec: BacktestSpec,
        *,
        dataset: pd.DataFrame | None,
        market_data: pd.DataFrame | None,
    ) -> pd.DataFrame:
        if dataset is not None:
            return dataset.copy()
        if market_data is not None:
            return market_data.copy()
        if spec.dataset_path is None:
            raise ValueError("BacktestSpec requires dataset_path or an in-memory frame")
        return pd.read_parquet(spec.dataset_path)


def _execution_assumptions(spec: BacktestSpec) -> ExecutionAssumptions:
    if spec.holding_window not in SUPPORTED_HOLDING_WINDOWS_MS:
        raise ValueError(f"holding_window must be one of {', '.join(SUPPORTED_HOLDING_WINDOWS_MS)}")
    holding_ms = SUPPORTED_HOLDING_WINDOWS_MS[spec.holding_window]
    return ExecutionAssumptions(
        interval_ms=int(spec.interval_ms),
        entry_latency_ms=int(spec.entry_latency_ms),
        entry_price_source=spec.entry_price_source,  # type: ignore[arg-type]
        min_holding_ms=SUPPORTED_HOLDING_WINDOWS_MS["1h"],
        max_holding_ms=SUPPORTED_HOLDING_WINDOWS_MS["7d"],
        holding_period_ms=holding_ms,
        allow_same_bar_exit=False,
        exit_policy_id=spec.exit_policy_id,
        target_return=spec.target_return,
        stop_return=spec.stop_return,
        exit_price_source=spec.exit_price_source,  # type: ignore[arg-type]
        exit_policy_params=dict(spec.exit_policy_params),
    )


def _load_lower_timeframe_frame(spec: BacktestSpec) -> pd.DataFrame | None:
    if spec.lower_timeframe_dataset_path is None:
        return None
    return pd.read_parquet(spec.lower_timeframe_dataset_path)


def _market_frame(source: pd.DataFrame, *, symbol: str) -> pd.DataFrame:
    if "symbol" in source.columns:
        source = source.loc[source["symbol"].astype(str).str.upper() == symbol.upper()].copy()
    columns = {
        "bar_time_ms": _first_existing(source, ("bar_time_ms", "signal_bar_time_ms", "time_ms")),
        "open": _first_existing(source, ("open", "signal_bar_open", "entry_price")),
        "high": _first_existing(source, ("high", "signal_bar_high", "entry_price")),
        "low": _first_existing(source, ("low", "signal_bar_low", "entry_price")),
        "close": _first_existing(source, ("close", "signal_bar_close", "entry_price")),
        "volume": _first_existing(source, ("volume", "signal_bar_volume")),
    }
    frame = pd.DataFrame({key: value for key, value in columns.items() if value is not None})
    if "volume" not in frame.columns:
        frame["volume"] = 0.0
    optional = [
        "funding_rate",
        "spread_bps",
        "top_regime_label",
        "regime",
        "realized_volatility",
        "atr_percentile",
        "atr",
        "directional_slope_atr",
        "funding_rate_change",
        "time_to_next_funding_ms",
        "hours_to_next_funding",
        "accept_probability",
        "base_probability",
        "primary_signed_imbalance_ratio",
        "primary_sqrt_signed_imbalance_ratio",
        "top_of_book_imbalance",
        "queue_imbalance_l5",
    ]
    for column in optional:
        if column in source.columns:
            frame[column] = source[column].to_numpy()
    frame["bar_time_ms"] = pd.to_numeric(frame["bar_time_ms"], errors="coerce").astype("int64")
    for column in ("open", "high", "low", "close", "volume"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.sort_values("bar_time_ms", kind="mergesort").drop_duplicates("bar_time_ms").reset_index(drop=True)


def _signals_for_strategy(source: pd.DataFrame, spec: BacktestSpec) -> tuple[pd.DataFrame, dict[str, Any]]:
    effective_feature_set = spec.feature_set_id or spec.strategy_config.get("feature_set_id", "features_full_context_no_wt")
    plugin_config = {
        **dict(spec.strategy_config),
        "symbol": spec.symbol.upper(),
        "feature_set_id": effective_feature_set,
        "holding_period": spec.holding_window,
        "entry_policy": spec.entry_price_source,
        "exit_policy_id": spec.exit_policy_id,
        "target_return": spec.target_return,
        "stop_return": spec.stop_return,
    }
    try:
        plugin = get_strategy_plugin(spec.strategy_id, config=plugin_config)
    except ValueError as exc:
        message = str(exc)
        if message.startswith("invalid_holding_period:"):
            raise ValueError(f"strategy_holding_window_unsupported:{spec.strategy_id}:{spec.holding_window}") from exc
        if message.startswith("invalid_feature_set:"):
            raise ValueError(f"strategy_feature_set_unsupported:{spec.strategy_id}:{effective_feature_set}") from exc
        raise
    if spec.holding_window not in getattr(plugin, "allowed_holding_periods", ()):
        raise ValueError(f"strategy_holding_window_unsupported:{spec.strategy_id}:{spec.holding_window}")
    if effective_feature_set not in getattr(plugin, "required_feature_sets", ()):
        raise ValueError(f"strategy_feature_set_unsupported:{spec.strategy_id}:{effective_feature_set}")
    plugin.prepare(None)
    predictions = plugin.predict(source.copy())
    validation = validate_signal_frame(predictions)
    if not validation.valid:
        raise ValueError("; ".join(validation.errors))
    if predictions.empty:
        signals = pd.DataFrame(columns=["signal_id", "symbol", "decision_time_ms", "side", "signal_bar_close", "strategy_id"])
    else:
        signals = predictions.loc[
            (predictions["side"].astype(str).str.lower() != "flat")
            & (predictions["skip_reason"].fillna("").astype(str) == "")
        ].copy()
        signals["decision_time_ms"] = pd.to_numeric(signals["signal_time_ms"], errors="coerce").astype("int64")
        signals["side"] = signals["side"].astype(str).str.lower()
    metadata = {
        "strategy_id": getattr(plugin, "strategy_id", spec.strategy_id),
        "strategy_version": getattr(plugin, "strategy_version", "unknown"),
        "allowed_holding_periods": list(getattr(plugin, "allowed_holding_periods", ())),
        "required_feature_sets": list(getattr(plugin, "required_feature_sets", ())),
        "signal_contract_valid": validation.valid,
        "signal_contract_errors": list(validation.errors),
    }
    return signals, metadata


def _enrich_trades(trades: pd.DataFrame, market: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return trades
    by_time = market.set_index("bar_time_ms")
    enriched = trades.copy()
    regimes: list[str] = []
    months: list[str] = []
    vol_buckets: list[str] = []
    spreads: list[float] = []
    for row in enriched.to_dict("records"):
        market_row = by_time.loc[int(row["entry_time_ms"])]
        regime = market_row.get("top_regime_label", market_row.get("regime", "unknown"))
        regimes.append("unknown" if pd.isna(regime) else str(regime))
        timestamp = pd.to_datetime(int(row["entry_time_ms"]), unit="ms", utc=True)
        months.append(timestamp.strftime("%Y-%m"))
        vol = market_row.get("realized_volatility", market_row.get("atr_percentile", np.nan))
        vol_buckets.append(_volatility_bucket(vol))
        spreads.append(float(market_row.get("spread_bps", 0.0) if not pd.isna(market_row.get("spread_bps", np.nan)) else 0.0))
    enriched["regime"] = regimes
    enriched["entry_month"] = months
    enriched["volatility_bucket"] = vol_buckets
    enriched["spread_bps"] = spreads
    return enriched


def _volatility_bucket(value: object) -> str:
    if value is None or pd.isna(value):
        return "missing"
    numeric = float(value)
    if numeric < 0.006:
        return "low"
    if numeric < 0.015:
        return "medium"
    return "high"


def _first_existing(frame: pd.DataFrame, columns: tuple[str, ...]) -> pd.Series | None:
    for column in columns:
        if column in frame.columns:
            return frame[column]
    return None


def _source_hash(spec: BacktestSpec, frame: pd.DataFrame) -> str:
    if spec.dataset_sha256:
        return spec.dataset_sha256
    if spec.dataset_path is not None and spec.dataset_path.exists():
        return _file_sha256(spec.dataset_path)
    return _frame_hash(frame)


def _lower_timeframe_source_hash(spec: BacktestSpec, frame: pd.DataFrame | None) -> str | None:
    if spec.lower_timeframe_dataset_path is not None and spec.lower_timeframe_dataset_path.exists():
        return _file_sha256(spec.lower_timeframe_dataset_path)
    if frame is not None:
        return _frame_hash(frame)
    return None


def _reproducible_config(config: dict[str, Any]) -> dict[str, Any]:
    payload = dict(config)
    payload.pop("run_id", None)
    payload.pop("output_dir", None)
    payload.pop("dataset_path", None)
    payload.pop("lower_timeframe_dataset_path", None)
    return payload


def _cache_key_components(
    *,
    dataset_sha256: str,
    lower_timeframe_dataset_sha256: str | None,
    feature_manifest_sha256: str | None,
    config_resolved: dict[str, Any],
    assumptions: ExecutionAssumptions,
    cost_model: CostModel,
) -> dict[str, Any]:
    return {
        "cache_policy": BACKTEST_CACHE_POLICY,
        "dataset_sha256": dataset_sha256,
        "lower_timeframe_dataset_sha256": lower_timeframe_dataset_sha256,
        "feature_manifest_sha256": feature_manifest_sha256,
        "backtest_spec_sha256": _stable_hash(_reproducible_config(config_resolved)),
        "execution_assumptions": assumptions.to_payload(),
        "cost_model": cost_model.to_payload(),
        "engine_version": BACKTEST_ENGINE_VERSION,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _stable_hash(payload: Any) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False).encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _frame_hash(frame: pd.DataFrame) -> str:
    if frame.empty:
        return _stable_hash({"columns": list(frame.columns), "rows": []})
    normalized = frame.copy()
    normalized = normalized.reindex(sorted(normalized.columns), axis=1)
    csv_payload = normalized.to_csv(index=False, lineterminator="\n", float_format="%.12g")
    return sha256(csv_payload.encode("utf-8")).hexdigest()
