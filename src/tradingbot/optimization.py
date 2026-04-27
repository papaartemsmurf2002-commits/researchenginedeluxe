from __future__ import annotations

import heapq
import math
import os
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from dataclasses import asdict, replace
from dataclasses import dataclass
from itertools import product
from typing import Any
from typing import Iterable

import pandas as pd

from tradingbot.backtest import BacktestReport, Backtester
from tradingbot.models import AppConfig


FEATURE_KEY_RE = re.compile(r"^feature_(\d+)(?:[._](name|param_a|param_b))$")
_WORKER_BASE_DF: pd.DataFrame | None = None
_WORKER_EXECUTION_DF: pd.DataFrame | None = None
_WORKER_FALLBACK_EXECUTION_DF: pd.DataFrame | None = None


@dataclass
class OptimizationResult:
    symbol: str
    best_config: AppConfig
    best_report: BacktestReport
    baseline_report: BacktestReport
    comparison_to_baseline: dict[str, float]
    selection_mode: str
    changed_fields: list[dict[str, Any]]
    baseline_config_snapshot: dict[str, Any]
    best_config_snapshot: dict[str, Any]
    candidate_count: int
    search_space: dict[str, list[Any]]
    best_candidate_summary: dict[str, Any]
    prescreen_bars: int
    shortlist_size: int
    shortlisted_candidate_count: int
    prescreen_top_candidates: list[dict[str, Any]]


class WalkForwardOptimizer:
    def __init__(self) -> None:
        self.backtester = Backtester()
        self._progress_last_print: dict[str, float] = {}

    def optimize(
        self,
        base_df: pd.DataFrame,
        execution_df: pd.DataFrame | None,
        app_config: AppConfig,
        symbol: str,
        fallback_execution_df: pd.DataFrame | None = None,
    ) -> OptimizationResult:
        base = base_df.copy()
        execution = execution_df.copy() if execution_df is not None else None
        fallback_execution = fallback_execution_df.copy() if fallback_execution_df is not None else None
        search_space = self._search_space(app_config, symbol)
        candidate_count = self._candidate_count(search_space)
        baseline_report = self.backtester.run(base, execution, app_config, symbol, fallback_execution)
        prescreen_bars = min(max(int(app_config.optimization.prescreen_bars), 1), len(base))
        shortlist_size = max(int(app_config.optimization.shortlist_size), 1)
        prescreen_base = self._slice_base_window(base, prescreen_bars)
        prescreen_execution = self._slice_execution_window(execution, prescreen_base, app_config.strategies[symbol].base_timeframe)
        prescreen_fallback = self._slice_execution_window(fallback_execution, prescreen_base, app_config.strategies[symbol].base_timeframe)
        shortlisted_candidates, prescreen_top_candidates = self._prescreen_candidates(
            prescreen_base,
            prescreen_execution,
            prescreen_fallback,
            app_config,
            symbol,
            search_space,
            shortlist_size,
        )

        best_score = float("-inf")
        best_raw_score = float("-inf")
        best_bundle = deepcopy(app_config)
        best_raw_bundle = deepcopy(app_config)
        best_report = baseline_report
        best_raw_report = baseline_report
        best_summary: dict[str, Any] | None = None
        best_raw_summary: dict[str, Any] | None = None

        evaluations = self._evaluate_candidate_configs(base, execution, fallback_execution, shortlisted_candidates, app_config, symbol, len(shortlisted_candidates))
        for candidate, report in evaluations:
            metrics = report.metrics
            raw_score = float(metrics["net_profit"])
            filter_failures: list[str] = []
            if metrics["trade_count"] < app_config.optimization.minimum_trades:
                filter_failures.append("minimum_trades")
            if metrics["max_drawdown_pct"] > app_config.optimization.max_drawdown_pct:
                filter_failures.append("max_drawdown_pct")
            if metrics["max_consecutive_losses"] > app_config.optimization.max_consecutive_losses:
                filter_failures.append("max_consecutive_losses")

            passes_filters = not filter_failures
            candidate_summary = {
                "score": raw_score,
                "raw_score": raw_score,
                "passes_filters": passes_filters,
                "filter_failures": sorted(filter_failures),
                "changed_fields": self._diff_configs(app_config, candidate, symbol),
            }

            if raw_score > best_raw_score:
                best_raw_score = raw_score
                best_raw_bundle = candidate
                best_raw_report = report
                best_raw_summary = candidate_summary

            if passes_filters and raw_score > best_score:
                best_score = raw_score
                best_bundle = candidate
                best_report = report
                best_summary = candidate_summary

        selection_mode = "filtered_best"
        if best_summary is None:
            selection_mode = "raw_fallback_no_candidate_passed_filters"
            best_bundle = best_raw_bundle
            best_report = best_raw_report
            best_summary = best_raw_summary or {
                "score": float(best_raw_report.metrics["net_profit"]),
                "raw_score": float(best_raw_report.metrics["net_profit"]),
                "passes_filters": False,
                "filter_failures": ["no_candidate_passed_filters"],
                "changed_fields": self._diff_configs(app_config, best_raw_bundle, symbol),
            }

        return OptimizationResult(
            symbol=symbol,
            best_config=best_bundle,
            best_report=best_report,
            baseline_report=baseline_report,
            comparison_to_baseline=self._compare_reports(baseline_report, best_report),
            selection_mode=selection_mode,
            changed_fields=self._diff_configs(app_config, best_bundle, symbol),
            baseline_config_snapshot=self._config_snapshot(app_config, symbol),
            best_config_snapshot=self._config_snapshot(best_bundle, symbol),
            candidate_count=candidate_count,
            search_space=search_space,
            best_candidate_summary=best_summary,
            prescreen_bars=prescreen_bars,
            shortlist_size=shortlist_size,
            shortlisted_candidate_count=len(shortlisted_candidates),
            prescreen_top_candidates=prescreen_top_candidates,
        )

    def _evaluate_candidates(
        self,
        base_df: pd.DataFrame,
        execution_df: pd.DataFrame | None,
        fallback_execution_df: pd.DataFrame | None,
        app_config: AppConfig,
        symbol: str,
        search_space: dict[str, list[Any]],
    ) -> Iterable[tuple[AppConfig, BacktestReport]]:
        candidate_iter = self._candidate_configs(app_config, symbol, search_space)
        return self._evaluate_candidate_configs(
            base_df,
            execution_df,
            fallback_execution_df,
            candidate_iter,
            app_config,
            symbol,
            self._candidate_count(search_space),
            stage_name="prescreen",
        )

    def _evaluate_candidate_configs(
        self,
        base_df: pd.DataFrame,
        execution_df: pd.DataFrame | None,
        fallback_execution_df: pd.DataFrame | None,
        candidate_iter: Iterable[AppConfig],
        app_config: AppConfig,
        symbol: str,
        candidate_count: int,
        stage_name: str = "optimize",
    ) -> Iterable[tuple[AppConfig, BacktestReport]]:
        worker_count = min(self._worker_count(app_config), max(candidate_count, 1))
        start_time = time.perf_counter()
        completed = 0
        if worker_count <= 1:
            for candidate in candidate_iter:
                report = self.backtester.run(base_df, execution_df, candidate, symbol, fallback_execution_df)
                completed += 1
                self._render_progress(stage_name, completed, candidate_count, start_time)
                yield candidate, report
            return

        tasks = ((candidate, symbol) for candidate in candidate_iter)
        chunksize = max(candidate_count // max(worker_count * 4, 1), 1)
        with ProcessPoolExecutor(
            max_workers=worker_count,
            initializer=_init_worker,
            initargs=(base_df, execution_df, fallback_execution_df),
        ) as executor:
            for candidate, report in executor.map(_evaluate_candidate, tasks, chunksize=chunksize):
                completed += 1
                self._render_progress(stage_name, completed, candidate_count, start_time)
                yield candidate, report

    def _candidate_configs(self, app_config: AppConfig, symbol: str, search_space: dict[str, list[Any]]) -> Iterable[AppConfig]:
        ordered_keys = list(search_space.keys())
        value_sets = [search_space[key] for key in ordered_keys]
        for combination in product(*value_sets):
            bundle = self._clone_bundle(app_config, symbol)
            for key, value in zip(ordered_keys, combination):
                self._apply_search_value(bundle, symbol, key, value)
            yield bundle

    def _clone_bundle(self, app_config: AppConfig, symbol: str) -> AppConfig:
        strategy_map = dict(app_config.strategies)
        strategy_map[symbol] = replace(app_config.strategies[symbol], feature_definitions=list(app_config.strategies[symbol].feature_definitions))
        return replace(
            app_config,
            strategies=strategy_map,
            risk=replace(app_config.risk),
            backtest=replace(app_config.backtest),
        )

    def _candidate_count(self, search_space: dict[str, list[Any]]) -> int:
        if not search_space:
            return 1
        return math.prod(len(values) for values in search_space.values())

    def _compare_reports(self, baseline: BacktestReport, candidate: BacktestReport) -> dict[str, float]:
        baseline_metrics = baseline.metrics
        candidate_metrics = candidate.metrics
        return {
            "baseline_net_profit": baseline_metrics["net_profit"],
            "optimized_net_profit": candidate_metrics["net_profit"],
            "net_profit_delta": candidate_metrics["net_profit"] - baseline_metrics["net_profit"],
            "baseline_win_rate": baseline_metrics["win_rate"],
            "optimized_win_rate": candidate_metrics["win_rate"],
            "win_rate_delta": candidate_metrics["win_rate"] - baseline_metrics["win_rate"],
            "baseline_max_drawdown_pct": baseline_metrics["max_drawdown_pct"],
            "optimized_max_drawdown_pct": candidate_metrics["max_drawdown_pct"],
            "drawdown_delta_pct": candidate_metrics["max_drawdown_pct"] - baseline_metrics["max_drawdown_pct"],
            "baseline_trade_count": baseline_metrics["trade_count"],
            "optimized_trade_count": candidate_metrics["trade_count"],
        }

    def _diff_configs(self, baseline: AppConfig, candidate: AppConfig, symbol: str) -> list[dict[str, Any]]:
        changes: list[dict[str, Any]] = []
        baseline_strategy = baseline.strategies[symbol]
        candidate_strategy = candidate.strategies[symbol]

        for field, old in asdict(baseline_strategy).items():
            if field == "feature_definitions":
                continue
            new = getattr(candidate_strategy, field)
            if old != new:
                changes.append({"field": field, "old": old, "new": new, "display": f"{field}: {old} -> {new}"})

        for idx, (base_def, cand_def) in enumerate(zip(baseline_strategy.feature_definitions, candidate_strategy.feature_definitions), start=1):
            base_name, base_a, base_b = base_def
            cand_name, cand_a, cand_b = cand_def
            if base_name != cand_name:
                changes.append(
                    {
                        "field": f"feature_{idx}.name",
                        "old": base_name,
                        "new": cand_name,
                        "display": f"feature_{idx}.name: {base_name} -> {cand_name}",
                    }
                )
            if base_a != cand_a:
                changes.append(
                    {
                        "field": f"feature_{idx}.param_a",
                        "old": base_a,
                        "new": cand_a,
                        "display": f"feature_{idx}.param_a: {base_a} -> {cand_a}",
                    }
                )
            if base_b != cand_b:
                changes.append(
                    {
                        "field": f"feature_{idx}.param_b",
                        "old": base_b,
                        "new": cand_b,
                        "display": f"feature_{idx}.param_b: {base_b} -> {cand_b}",
                    }
                )

        for group_name in ("risk", "backtest"):
            baseline_group = getattr(baseline, group_name)
            candidate_group = getattr(candidate, group_name)
            for field, old in asdict(baseline_group).items():
                new = getattr(candidate_group, field)
                if old != new:
                    label = f"{group_name}.{field}"
                    changes.append({"field": label, "old": old, "new": new, "display": f"{label}: {old} -> {new}"})

        return changes

    def _config_snapshot(self, app_config: AppConfig, symbol: str) -> dict[str, Any]:
        strategy = app_config.strategies[symbol]
        return {
            "symbol": symbol,
            "feature_definitions": [list(item) for item in strategy.feature_definitions[: strategy.feature_count]],
            "strategy": asdict(strategy),
            "risk": asdict(app_config.risk),
            "backtest": asdict(app_config.backtest),
        }

    def _worker_count(self, app_config: AppConfig) -> int:
        configured = int(app_config.optimization.parallel_workers)
        if configured > 0:
            return configured
        cpu_count = os.cpu_count() or 1
        return max(cpu_count - 1, 1)

    def _search_space(self, app_config: AppConfig, symbol: str) -> dict[str, list[Any]]:
        raw_space = app_config.optimization.search_space or self._default_search_space(app_config, symbol)
        normalized: dict[str, list[Any]] = {}
        for raw_key, raw_values in raw_space.items():
            key = self._canonical_key(raw_key)
            if not isinstance(raw_values, list) or not raw_values:
                raise ValueError(f"Optimization search space for '{raw_key}' must be a non-empty list.")
            values = list(dict.fromkeys(raw_values))
            baseline_value = self._read_search_value(app_config, symbol, key)
            if baseline_value not in values:
                values.append(baseline_value)
            normalized[key] = values
        return normalized

    def _default_search_space(self, app_config: AppConfig, symbol: str) -> dict[str, list[Any]]:
        strategy = app_config.strategies[symbol]
        defaults: dict[str, list[Any]] = {}
        for idx, (_name, param_a, param_b) in enumerate(strategy.feature_definitions[: strategy.feature_count], start=1):
            defaults[f"feature_{idx}.param_a"] = [max(param_a - 2, 1), max(param_a - 1, 1), param_a, param_a + 1, param_a + 2]
            defaults[f"feature_{idx}.param_b"] = [max(param_b - 1, 1), param_b, param_b + 1]
        return defaults

    def _slice_base_window(self, base_df: pd.DataFrame, prescreen_bars: int) -> pd.DataFrame:
        return base_df.tail(prescreen_bars).reset_index(drop=True)

    def _slice_execution_window(
        self,
        execution_df: pd.DataFrame | None,
        base_slice: pd.DataFrame,
        base_timeframe: str,
    ) -> pd.DataFrame | None:
        if execution_df is None or execution_df.empty or base_slice.empty:
            return execution_df
        start = base_slice.iloc[0]["timestamp"]
        end = base_slice.iloc[-1]["timestamp"] + self.backtester._timeframe_delta(base_timeframe)
        return execution_df[(execution_df["timestamp"] >= start) & (execution_df["timestamp"] < end)].reset_index(drop=True)

    def _prescreen_candidates(
        self,
        base_df: pd.DataFrame,
        execution_df: pd.DataFrame | None,
        fallback_execution_df: pd.DataFrame | None,
        app_config: AppConfig,
        symbol: str,
        search_space: dict[str, list[Any]],
        shortlist_size: int,
    ) -> tuple[list[AppConfig], list[dict[str, Any]]]:
        heap: list[tuple[float, int, AppConfig, dict[str, Any]]] = []
        sequence = 0
        for candidate, report in self._evaluate_candidates(base_df, execution_df, fallback_execution_df, app_config, symbol, search_space):
            metrics = report.metrics
            score = float(metrics.get(app_config.optimization.objective, metrics["net_profit"]))
            summary = {
                "score": score,
                "net_profit": float(metrics["net_profit"]),
                "win_rate": float(metrics["win_rate"]),
                "trade_count": float(metrics["trade_count"]),
                "max_drawdown_pct": float(metrics["max_drawdown_pct"]),
                "changed_fields": self._diff_configs(app_config, candidate, symbol),
            }
            item = (score, sequence, candidate, summary)
            sequence += 1
            if len(heap) < shortlist_size:
                heapq.heappush(heap, item)
            else:
                heapq.heappushpop(heap, item)
        shortlisted = sorted(heap, key=lambda item: (item[0], -item[1]), reverse=True)
        candidates = [item[2] for item in shortlisted]
        summaries = [item[3] for item in shortlisted]
        return candidates, summaries

    def _render_progress(
        self,
        stage_name: str,
        completed: int,
        total: int,
        start_time: float,
        *,
        force: bool = False,
    ) -> None:
        if total <= 0:
            return
        now = time.perf_counter()
        if not force:
            last_print = self._progress_last_print.get(stage_name, 0.0)
            if completed not in {1, total} and (now - last_print) < 0.25:
                return
        self._progress_last_print[stage_name] = now
        fraction = min(max(completed / total, 0.0), 1.0)
        width = 24
        filled = int(width * fraction)
        bar = "#" * filled + "-" * (width - filled)
        elapsed = now - start_time
        rate = completed / elapsed if elapsed > 0 else 0.0
        remaining = (total - completed) / rate if rate > 0 else 0.0
        message = (
            f"\r[{stage_name}] [{bar}] {completed}/{total} "
            f"({fraction * 100:5.1f}%) elapsed {elapsed:6.1f}s eta {remaining:6.1f}s"
        )
        end = "\n" if force or completed >= total else ""
        sys.stderr.write(message + end)
        sys.stderr.flush()

    def _canonical_key(self, key: str) -> str:
        match = FEATURE_KEY_RE.match(key)
        if match:
            idx, field = match.groups()
            return f"feature_{idx}.{field}"
        return key

    def _read_search_value(self, bundle: AppConfig, symbol: str, key: str) -> Any:
        if "." not in key:
            strategy = bundle.strategies[symbol]
            if hasattr(strategy, key):
                return getattr(strategy, key)
            raise ValueError(f"Unsupported optimization field '{key}'.")

        head, tail = key.split(".", 1)
        feature_match = FEATURE_KEY_RE.match(f"{head}.{tail}")
        if feature_match:
            feature_idx = int(feature_match.group(1)) - 1
            feature_field = feature_match.group(2)
            feature_name, param_a, param_b = bundle.strategies[symbol].feature_definitions[feature_idx]
            if feature_field == "name":
                return feature_name
            if feature_field == "param_a":
                return param_a
            return param_b

        if head in {"risk", "backtest"}:
            target = getattr(bundle, head)
            if hasattr(target, tail):
                return getattr(target, tail)
        raise ValueError(f"Unsupported optimization field '{key}'.")

    def _apply_search_value(self, bundle: AppConfig, symbol: str, key: str, value: Any) -> None:
        if "." not in key:
            strategy = bundle.strategies[symbol]
            if hasattr(strategy, key):
                setattr(strategy, key, value)
                return
            raise ValueError(f"Unsupported optimization field '{key}'.")

        head, tail = key.split(".", 1)
        feature_match = FEATURE_KEY_RE.match(f"{head}.{tail}")
        if feature_match:
            feature_idx = int(feature_match.group(1)) - 1
            feature_field = feature_match.group(2)
            feature_name, param_a, param_b = bundle.strategies[symbol].feature_definitions[feature_idx]
            if feature_field == "name":
                bundle.strategies[symbol].feature_definitions[feature_idx] = (str(value), param_a, param_b)
            elif feature_field == "param_a":
                bundle.strategies[symbol].feature_definitions[feature_idx] = (feature_name, int(value), param_b)
            else:
                bundle.strategies[symbol].feature_definitions[feature_idx] = (feature_name, param_a, int(value))
            return

        if head in {"risk", "backtest"}:
            target = getattr(bundle, head)
            if hasattr(target, tail):
                setattr(target, tail, value)
                return
        raise ValueError(f"Unsupported optimization field '{key}'.")


def _init_worker(base_df: pd.DataFrame, execution_df: pd.DataFrame | None, fallback_execution_df: pd.DataFrame | None) -> None:
    global _WORKER_BASE_DF, _WORKER_EXECUTION_DF, _WORKER_FALLBACK_EXECUTION_DF
    _WORKER_BASE_DF = base_df
    _WORKER_EXECUTION_DF = execution_df
    _WORKER_FALLBACK_EXECUTION_DF = fallback_execution_df


def _evaluate_candidate(task: tuple[AppConfig, str]) -> tuple[AppConfig, BacktestReport]:
    candidate, symbol = task
    base_df = _WORKER_BASE_DF
    execution_df = _WORKER_EXECUTION_DF
    fallback_execution_df = _WORKER_FALLBACK_EXECUTION_DF
    if base_df is None:
        raise RuntimeError("Optimizer worker was not initialized with base market data.")
    report = Backtester().run(base_df, execution_df, candidate, symbol, fallback_execution_df)
    return candidate, report
