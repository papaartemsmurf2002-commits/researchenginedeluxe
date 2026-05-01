from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def benchmark_against_stage6_baselines(
    *,
    dataset_path: Path,
    output_dir: Path,
    symbol: str,
    dataset_sha256: str | None = None,
) -> dict[str, Any]:
    from tradingbotsuite.backtesting import BacktestEngine, BacktestSpec

    output_dir.mkdir(parents=True, exist_ok=True)
    engine = BacktestEngine()
    strategies = {
        "trend_following_v1": {"slope_threshold": 0.1, "spacing_bars": 10},
        "baseline_no_trade": {},
    }
    results: dict[str, Any] = {}
    for strategy_id, strategy_config in strategies.items():
        result = engine.run(
            BacktestSpec(
                run_id=strategy_id,
                symbol=symbol,
                output_dir=output_dir,
                dataset_path=dataset_path,
                dataset_sha256=dataset_sha256,
                strategy_id=strategy_id,
                holding_window="24h",
                feature_set_id="features_full_context_no_wt",
                strategy_config=strategy_config,
            )
        )
        metrics = json.loads(result.metrics_path.read_text(encoding="utf-8"))
        results[strategy_id] = {
            "manifest_path": str(result.manifest_path),
            "metrics_path": str(result.metrics_path),
            "result_sha256": result.result_sha256,
            "trade_count": int(metrics["trade_count"]),
            "net_return_after_fees_slippage_funding": float(metrics["net_return_after_fees_slippage_funding"]),
        }
    return {
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "benchmark_scope": "stage6_baseline_strategies",
        "strategies": results,
    }
