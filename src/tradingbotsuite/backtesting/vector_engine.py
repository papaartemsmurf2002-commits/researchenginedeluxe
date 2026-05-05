from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from tradingbotsuite.backtesting.costs import CostModel
from tradingbotsuite.backtesting.engine import (
    BACKTEST_CACHE_POLICY,
    BACKTEST_ENGINE_VERSION,
    BACKTEST_MANIFEST_VERSION,
    BacktestEngine,
    BacktestResult,
    BacktestSpec,
    _cache_key_components,
    _enrich_trades,
    _execution_assumptions,
    _file_sha256,
    _frame_hash,
    _market_frame,
    _reproducible_config,
    _signals_for_strategy,
    _source_hash,
    _stable_hash,
    _write_json,
)
from tradingbotsuite.backtesting.execution_sim import _equity_curve
from tradingbotsuite.backtesting.exits import fixed_holding_window_exit
from tradingbotsuite.backtesting.metrics import REQUIRED_BACKTEST_METRICS, calculate_backtest_metrics


VECTOR_BACKTEST_ENGINE_VERSION = "research-vector-backtest-engine-v1"


class VectorBacktestEngine:
    """Vector-oriented fixed-holding research backtest path.

    This foundation intentionally supports only primary-bar fixed holding windows.
    Unsupported richer exits remain on the reference `BacktestEngine`.
    """

    def run(
        self,
        spec: BacktestSpec,
        *,
        market_data: pd.DataFrame | None = None,
        dataset: pd.DataFrame | None = None,
    ) -> BacktestResult:
        started = time.perf_counter()
        _validate_vector_spec(spec)
        output_dir = spec.output_dir / spec.run_id
        output_dir.mkdir(parents=True, exist_ok=True)
        reference_engine = BacktestEngine()
        source_frame = reference_engine._load_source_frame(spec, dataset=dataset, market_data=market_data)
        market = _market_frame(source_frame, symbol=spec.symbol)
        assumptions = _execution_assumptions(spec)
        reference_engine.execution_simulator._validate_assumptions(assumptions, None)
        signals, strategy_metadata = _signals_for_strategy(source_frame, spec)
        cost_model = CostModel(
            fee_bps=spec.fee_bps,
            slippage_bps=spec.slippage_bps,
            spread_bps=spec.spread_bps,
            funding_rate=spec.funding_rate,
        )
        trades = _vector_fixed_holding_trades(
            signals,
            market,
            costs=cost_model,
            assumptions=assumptions,
            symbol=spec.symbol,
        )
        trades = _enrich_trades(trades, market)
        equity_curve = _equity_curve(spec.initial_equity, market, trades)
        metrics = calculate_backtest_metrics(
            trades=trades,
            signals=signals,
            equity_curve=equity_curve,
            market_data=market,
            initial_equity=spec.initial_equity,
        )
        config_resolved = spec.resolved_config()
        config_resolved["engine_version"] = VECTOR_BACKTEST_ENGINE_VERSION
        source_hash = _source_hash(spec, source_frame)
        cache_key_components = _cache_key_components(
            dataset_sha256=source_hash,
            lower_timeframe_dataset_sha256=None,
            feature_manifest_sha256=spec.feature_manifest_sha256,
            config_resolved=config_resolved,
            assumptions=assumptions,
            cost_model=cost_model,
        )
        cache_key_components["engine_version"] = VECTOR_BACKTEST_ENGINE_VERSION
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
            "engine_version": VECTOR_BACKTEST_ENGINE_VERSION,
            "reference_engine_version": BACKTEST_ENGINE_VERSION,
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
            "vector_execution_scope": "fixed_holding_primary_bar",
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
            "lower_timeframe_dataset_path": None,
            "lower_timeframe_dataset_sha256": None,
            "feature_set_id": spec.feature_set_id,
            "feature_manifest_sha256": spec.feature_manifest_sha256,
            "config_sha256": _stable_hash(config_resolved),
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


def _validate_vector_spec(spec: BacktestSpec) -> None:
    reason = vector_backtest_support_reason(spec)
    if reason is not None:
        raise ValueError(reason)


def vector_backtest_support_reason(spec: BacktestSpec) -> str | None:
    if spec.lower_timeframe_dataset_path is not None:
        return "vector_engine_lower_timeframe_not_supported"
    if not _is_vector_fixed_holding_policy(spec.exit_policy_id):
        return "vector_engine_supports_fixed_holding_only"
    if str(spec.exit_price_source) != "primary_close":
        return "vector_engine_supports_primary_close_exit_only"
    if str(spec.entry_price_source) not in {"next_bar_open", "signal_bar_close_plus_latency", "vwap_approximation"}:
        return "vector_engine_entry_price_source_not_supported"
    return None


def _is_vector_fixed_holding_policy(exit_policy_id: str) -> bool:
    value = str(exit_policy_id).lower()
    return value == "fixed_holding_window" or value.endswith("_time_exit")


def _vector_fixed_holding_trades(
    signals: pd.DataFrame,
    market: pd.DataFrame,
    *,
    costs: CostModel,
    assumptions: Any,
    symbol: str,
) -> pd.DataFrame:
    if signals.empty:
        return _empty_trades()
    ordered_market = market.sort_values("bar_time_ms", kind="mergesort").reset_index(drop=True)
    times = ordered_market["bar_time_ms"].astype("int64").to_numpy()
    rows: list[dict[str, Any]] = []
    next_available_entry_time = -1
    for signal in signals.sort_values("decision_time_ms", kind="mergesort").to_dict("records"):
        decision_time = int(signal["decision_time_ms"])
        entry_index = int(np.searchsorted(times, decision_time + int(assumptions.entry_latency_ms), side="left"))
        if entry_index >= len(ordered_market):
            continue
        entry_row = ordered_market.iloc[entry_index]
        entry_time = int(entry_row["bar_time_ms"])
        if entry_time < next_available_entry_time:
            continue
        side = str(signal["side"]).lower()
        entry_price = _entry_price(signal, entry_row, assumptions)
        target_exit_time = entry_time + int(assumptions.holding_period_ms)
        exit_index = int(np.searchsorted(times, target_exit_time, side="left"))
        exit_reason = "holding_window"
        used_fallback = False
        if exit_index >= len(ordered_market):
            exit_index = len(ordered_market) - 1
            exit_time = int(ordered_market.iloc[exit_index]["bar_time_ms"])
            if exit_time - entry_time < int(assumptions.min_holding_ms):
                continue
            exit_reason = "end_of_data_min_holding"
            used_fallback = True
        exit_row = ordered_market.iloc[exit_index]
        exit_time = int(exit_row["bar_time_ms"])
        path = ordered_market.iloc[entry_index : exit_index + 1]
        exit_result = fixed_holding_window_exit(
            entry_time_ms=entry_time,
            exit_time_ms=exit_time,
            exit_price=float(exit_row["close"]),
            side=side,
            path_high=float(path["high"].max()),
            path_low=float(path["low"].min()),
            entry_price=entry_price,
            costs_applied=True,
            exit_reason=exit_reason,
        )
        holding_ms = int(exit_result.time_in_trade_ms)
        funding_rate = _optional_float(entry_row.get("funding_rate"))
        spread_bps = _optional_float(entry_row.get("spread_bps"))
        cost = costs.estimate(
            entry_price=entry_price,
            exit_price=float(exit_result.exit_price),
            side=side,
            holding_ms=holding_ms,
            funding_rate=funding_rate,
            spread_bps=spread_bps,
        )
        rows.append(
            {
                "trade_id": f"trade-{len(rows):06d}",
                "signal_id": str(signal.get("signal_id", f"signal-{len(rows):06d}")),
                "symbol": str(signal.get("symbol", symbol)),
                "side": side,
                "entry_time_ms": entry_time,
                "exit_time_ms": int(exit_result.exit_time_ms),
                "entry_bar_index": entry_index,
                "exit_bar_index": exit_index,
                "entry_price": float(entry_price),
                "exit_price": float(exit_result.exit_price),
                "holding_ms": holding_ms,
                "exit_target_time_ms": target_exit_time,
                "exit_target_holding_ms": int(assumptions.holding_period_ms),
                "exit_used_fallback": bool(used_fallback),
                "exit_policy": exit_result.exit_policy_id,
                "barrier_hit_type": exit_result.barrier_hit_type,
                "max_adverse_excursion": exit_result.max_adverse_excursion,
                "max_favorable_excursion": exit_result.max_favorable_excursion,
                "exit_approximate": exit_result.approximate,
                "exit_sequence_proof": "primary_bar_time",
                "exit_price_source": assumptions.exit_price_source,
                "gross_return": cost.gross_return,
                "fee_return": cost.fee_return,
                "slippage_return": cost.slippage_return,
                "spread_return": cost.spread_return,
                "funding_return": cost.funding_return,
                "net_return": cost.net_return,
                "entry_price_source": assumptions.entry_price_source,
                "exit_reason": exit_result.exit_reason,
            }
        )
        next_available_entry_time = int(exit_result.exit_time_ms)
    return pd.DataFrame(rows, columns=list(_empty_trades().columns)) if rows else _empty_trades()


def _entry_price(signal: dict[str, Any], entry_row: pd.Series, assumptions: Any) -> float:
    if assumptions.entry_price_source == "signal_bar_close_plus_latency":
        value = signal.get("signal_bar_close")
        return float(entry_row["open"] if value is None else value)
    if assumptions.entry_price_source == "vwap_approximation":
        return float((float(entry_row["high"]) + float(entry_row["low"]) + float(entry_row["close"])) / 3.0)
    return float(entry_row["open"])


def _empty_trades() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "trade_id",
            "signal_id",
            "symbol",
            "side",
            "entry_time_ms",
            "exit_time_ms",
            "entry_bar_index",
            "exit_bar_index",
            "entry_price",
            "exit_price",
            "holding_ms",
            "exit_target_time_ms",
            "exit_target_holding_ms",
            "exit_used_fallback",
            "exit_policy",
            "barrier_hit_type",
            "max_adverse_excursion",
            "max_favorable_excursion",
            "exit_approximate",
            "exit_sequence_proof",
            "exit_price_source",
            "gross_return",
            "fee_return",
            "slippage_return",
            "spread_return",
            "funding_return",
            "net_return",
            "entry_price_source",
            "exit_reason",
        ]
    )


def _optional_float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)
