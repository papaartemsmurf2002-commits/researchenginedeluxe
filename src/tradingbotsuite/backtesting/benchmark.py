from __future__ import annotations

import json
import time
from hashlib import sha256
from pathlib import Path
from typing import Any

from tradingbotsuite.backtesting.engine import BacktestEngine, BacktestSpec
from tradingbotsuite.research.deterministic_datasets import write_hmm_knn_sweep_dataset

BACKTEST_BENCHMARK_VERSION = "research-backtest-benchmark-v1"


def write_backtest_benchmark_report(
    *,
    output_dir: Path = Path("data/research/benchmarks"),
    row_count: int = 240,
    repeat: int = 2,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset = write_hmm_knn_sweep_dataset(output_dir=output_dir / "fixtures", row_count=row_count, variant="balanced")
    engine = BacktestEngine()
    runs: list[dict[str, Any]] = []
    result_hashes: list[str] = []
    for index in range(max(int(repeat), 1)):
        started = time.perf_counter()
        result = engine.run(
            BacktestSpec(
                run_id=f"benchmark-trend-{index}",
                symbol="BTCUSDT",
                output_dir=output_dir / "runs",
                dataset_path=dataset.parquet_path,
                strategy_id="baseline_trend",
                holding_window="24h",
                dataset_sha256=dataset.parquet_sha256,
                feature_set_id="features_price_trend_vol",
                feature_manifest_sha256="benchmark-fixture",
                strategy_config={"slope_threshold": 0.1, "spacing_bars": 12},
            )
        )
        elapsed = max(time.perf_counter() - started, 1e-9)
        result_hashes.append(result.result_sha256)
        runs.append(
            {
                "run_id": f"benchmark-trend-{index}",
                "manifest_path": str(result.manifest_path),
                "result_sha256": result.result_sha256,
                "elapsed_ms": round(elapsed * 1000.0, 6),
                "rows_processed_per_second": round(row_count / elapsed, 6),
                "strategies_per_minute": round(60.0 / elapsed, 6),
            }
        )
    report = {
        "benchmark_report_version": BACKTEST_BENCHMARK_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "engine": "tradingbotsuite.backtesting.BacktestEngine",
        "dataset_path": str(dataset.parquet_path),
        "dataset_sha256": dataset.parquet_sha256,
        "dimensions": {
            "rows_processed_per_second": [run["rows_processed_per_second"] for run in runs],
            "strategies_per_minute": [run["strategies_per_minute"] for run in runs],
            "memory_peak": "not_measured_stage5_baseline",
            "cache_hit_speedup": 1.0,
            "process_scaling": {"workers_1": 1.0, "workers_n": "not_measured_stage5_baseline"},
            "deterministic_repeat_hash": _repeat_hash(result_hashes),
        },
        "runs": runs,
    }
    backtest_report_path = output_dir / "backtest_engine_baseline.json"
    optimizer_report_path = output_dir / "optimizer_baseline.json"
    _write_json(backtest_report_path, report)
    _write_json(
        optimizer_report_path,
        {
            "benchmark_report_version": "research-optimizer-benchmark-v1",
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "status": "registered_baseline",
            "reason": "Stage 5 creates the engine baseline; optimizer implementation begins after engine correctness is stable.",
            "backtest_engine_baseline_path": str(backtest_report_path),
            "deterministic_repeat_hash": report["dimensions"]["deterministic_repeat_hash"],
        },
    )
    return backtest_report_path, optimizer_report_path


def _repeat_hash(values: list[str]) -> str:
    return sha256(json.dumps(values, sort_keys=True).encode("utf-8")).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
