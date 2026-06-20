from __future__ import annotations

import argparse
import csv
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

from tradingbotsuite.research.live_readiness import research_boundary_metadata


MONTE_CARLO_EXIT_SIZING_VERSION = "wpr106-80-monte-carlo-exit-sizing-sieve-v1"
DEFAULT_TAKER_FEE_RATE = 0.000432
DEFAULT_MONTE_CARLO_PATHS = 10_000
DEFAULT_MONTE_CARLO_SEED = 10680
DEFAULT_STOP_RETURNS = (0.003, 0.005, 0.0075, 0.01, 0.015, 0.02)
SPARSE_BTC_CYCLE_ROOT = Path("data/research/historical_cycles/sparse_entry_filter_btcusdt_r106_v1")
KNN_ARCHIVE_ROOT = Path("data/research/hmm_knn_four_bar_archive_mapping/wpr106_79_full_local_archive_map")


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    output_dir: Path
    summary_path: Path
    strategy_csv_path: Path
    barrier_csv_path: Path
    report_path: Path

    def to_payload(self) -> dict[str, str]:
        return {
            "output_dir": str(self.output_dir),
            "summary_path": str(self.summary_path),
            "strategy_csv_path": str(self.strategy_csv_path),
            "barrier_csv_path": str(self.barrier_csv_path),
            "report_path": str(self.report_path),
        }


def round_trip_fee_return(taker_fee_rate: float = DEFAULT_TAKER_FEE_RATE) -> float:
    return 2.0 * float(taker_fee_rate)


def reprice_gross_returns(
    trades: pd.DataFrame,
    *,
    taker_fee_rate: float = DEFAULT_TAKER_FEE_RATE,
    side: str | None = None,
) -> np.ndarray:
    frame = trades
    if side is not None:
        frame = frame.loc[frame["side"].astype(str).str.lower() == str(side).lower()]
    if frame.empty:
        return np.array([], dtype=float)
    gross = pd.to_numeric(frame["gross_return"], errors="coerce").to_numpy(dtype=float)
    return gross[np.isfinite(gross)] - round_trip_fee_return(taker_fee_rate)


def conservative_one_to_two_barrier_returns(
    trades: pd.DataFrame,
    *,
    stop_return: float,
    taker_fee_rate: float = DEFAULT_TAKER_FEE_RATE,
    side: str | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    if stop_return <= 0.0:
        raise ValueError("stop_return must be positive")
    frame = trades
    if side is not None:
        frame = frame.loc[frame["side"].astype(str).str.lower() == str(side).lower()]
    if frame.empty:
        return np.array([], dtype=float), _empty_barrier_audit(stop_return=stop_return, side=side)

    fee = round_trip_fee_return(taker_fee_rate)
    gross_time = pd.to_numeric(frame["gross_return"], errors="coerce").to_numpy(dtype=float)
    mae = pd.to_numeric(frame["max_adverse_excursion"], errors="coerce").to_numpy(dtype=float)
    mfe = pd.to_numeric(frame["max_favorable_excursion"], errors="coerce").to_numpy(dtype=float)
    finite = np.isfinite(gross_time) & np.isfinite(mae) & np.isfinite(mfe)
    gross_time = gross_time[finite]
    mae = mae[finite]
    mfe = mfe[finite]

    stop_hit = mae >= float(stop_return)
    target = 2.0 * float(stop_return)
    target_hit = mfe >= target
    ambiguous = stop_hit & target_hit
    target_only = target_hit & ~stop_hit
    stop_only = stop_hit & ~target_hit
    neither = ~(target_hit | stop_hit)

    returns = gross_time - fee
    returns[target_only] = target - fee
    returns[stop_only | ambiguous] = -float(stop_return) - fee

    audit = {
        "stop_return": float(stop_return),
        "target_return": float(target),
        "side": side or "all",
        "trade_count": int(returns.size),
        "target_only_count": int(target_only.sum()),
        "stop_only_count": int(stop_only.sum()),
        "ambiguous_stop_first_count": int(ambiguous.sum()),
        "time_exit_count": int(neither.sum()),
        "target_only_rate": _safe_ratio(int(target_only.sum()), int(returns.size)),
        "stop_or_ambiguous_rate": _safe_ratio(int((stop_only | ambiguous).sum()), int(returns.size)),
        "ambiguous_rate": _safe_ratio(int(ambiguous.sum()), int(returns.size)),
        "sequence_note": "mae_mfe_only_conservative_stop_first_for_ambiguous_paths",
    }
    return returns, audit


def max_loss_streak(returns: Sequence[float]) -> int:
    longest = 0
    current = 0
    for value in returns:
        if float(value) <= 0.0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def martingale_fee_positive_recovery_streak(
    *,
    stop_return: float,
    taker_fee_rate: float = DEFAULT_TAKER_FEE_RATE,
    multiplier: float = 1.5,
) -> int:
    fee = round_trip_fee_return(taker_fee_rate)
    threshold = (2.0 * (float(stop_return) + fee)) / (3.0 * fee)
    if threshold <= 1.0:
        return 0
    return max(int(math.floor(math.log(threshold, float(multiplier)) - 1e-12)), 0)


def monte_carlo_summary(
    returns: Sequence[float],
    *,
    paths: int = DEFAULT_MONTE_CARLO_PATHS,
    seed: int = DEFAULT_MONTE_CARLO_SEED,
    martingale: bool = False,
    martingale_multiplier: float = 1.5,
) -> dict[str, Any]:
    values = np.asarray(returns, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return {
            "path_count": int(paths),
            "horizon_trades": 0,
            "available": False,
        }
    rng = np.random.default_rng(seed)
    horizon = int(values.size)
    sampled = values[rng.integers(0, values.size, size=(int(paths), horizon))]
    if martingale:
        terminal, drawdowns, streaks, max_multipliers, ruin = _simulate_martingale_paths(
            sampled,
            multiplier=martingale_multiplier,
        )
    else:
        equity = np.cumprod(1.0 + sampled, axis=1)
        terminal = equity[:, -1] - 1.0
        running_peak = np.maximum.accumulate(equity, axis=1)
        drawdowns = np.min((equity / running_peak) - 1.0, axis=1)
        streaks = np.fromiter((max_loss_streak(row) for row in sampled), dtype=int, count=sampled.shape[0])
        max_multipliers = np.ones(sampled.shape[0], dtype=float)
        ruin = np.zeros(sampled.shape[0], dtype=bool)

    return {
        "path_count": int(paths),
        "horizon_trades": horizon,
        "available": True,
        "terminal_return_mean": _float(np.mean(terminal)),
        "terminal_return_median": _float(np.median(terminal)),
        "terminal_return_p05": _float(np.quantile(terminal, 0.05)),
        "terminal_return_p95": _float(np.quantile(terminal, 0.95)),
        "probability_terminal_negative": _float(np.mean(terminal < 0.0)),
        "max_drawdown_median": _float(np.median(drawdowns)),
        "max_drawdown_p05": _float(np.quantile(drawdowns, 0.05)),
        "max_loss_streak_median": _float(np.median(streaks)),
        "max_loss_streak_p95": _float(np.quantile(streaks, 0.95)),
        "probability_loss_streak_ge_5": _float(np.mean(streaks >= 5)),
        "probability_loss_streak_ge_8": _float(np.mean(streaks >= 8)),
        "probability_loss_streak_ge_10": _float(np.mean(streaks >= 10)),
        "martingale_multiplier_max_p95": _float(np.quantile(max_multipliers, 0.95)),
        "ruin_probability": _float(np.mean(ruin)),
    }


def run_wpr10680_analysis(
    *,
    output_dir: Path,
    repo_root: Path | None = None,
    paths: int = DEFAULT_MONTE_CARLO_PATHS,
    seed: int = DEFAULT_MONTE_CARLO_SEED,
    taker_fee_rate: float = DEFAULT_TAKER_FEE_RATE,
) -> AnalysisResult:
    repo_root = (repo_root or _repo_root()).resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    started_at_ms = int(time.time() * 1000)

    sparse_cases, barrier_rows = _build_sparse_strategy_cases(
        repo_root=repo_root,
        taker_fee_rate=taker_fee_rate,
        paths=paths,
        seed=seed,
    )
    knn_rejections = _load_knn_archive_rejections(repo_root=repo_root)
    strategy_rows = sparse_cases + knn_rejections

    strategy_csv_path = output_dir / "wpr106_80_strategy_monte_carlo.csv"
    barrier_csv_path = output_dir / "wpr106_80_fixed_barrier_audit.csv"
    _write_csv(strategy_csv_path, strategy_rows)
    _write_csv(barrier_csv_path, barrier_rows)

    top_rows = [
        row
        for row in strategy_rows
        if row.get("evidence_status") == "monte_carlo_evaluated"
        and float(row.get("fixed_terminal_return_p05") or -1.0) > 0.0
        and float(row.get("fixed_probability_terminal_negative") or 1.0) <= 0.05
    ]
    martingale_allowed = [
        row
        for row in strategy_rows
        if row.get("martingale_status") == "allowed_for_followup"
    ]
    next_decision = _next_decision(strategy_rows=top_rows, martingale_allowed=martingale_allowed)
    summary = {
        "summary_version": MONTE_CARLO_EXIT_SIZING_VERSION,
        "generated_at_ms": int(time.time() * 1000),
        "started_at_ms": started_at_ms,
        "runtime_seconds": round((int(time.time() * 1000) - started_at_ms) / 1000.0, 6),
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "candidate_pack_written": False,
        "paper_artifact_written": False,
        "live_artifact_written": False,
        "order_placement_used": False,
        "position_sizing_used": False,
        "runtime_mode_changed": False,
        "taker_fee_rate": float(taker_fee_rate),
        "round_trip_fee_return": round_trip_fee_return(taker_fee_rate),
        "funding_included": False,
        "monte_carlo_paths": int(paths),
        "monte_carlo_seed": int(seed),
        "strategy_row_count": len(strategy_rows),
        "barrier_row_count": len(barrier_rows),
        "top_candidate_count": len(top_rows),
        "martingale_allowed_count": len(martingale_allowed),
        "next_decision": next_decision,
        "external_research_sources": _external_sources(),
        "strategy_csv_path": str(strategy_csv_path),
        "barrier_csv_path": str(barrier_csv_path),
    }
    summary_path = output_dir / "wpr106_80_monte_carlo_exit_sizing_summary.json"
    summary_path.write_text(_canonical_json(summary) + "\n", encoding="utf-8")
    report_path = output_dir / "wpr106_80_monte_carlo_exit_sizing_report.md"
    report_path.write_text(_render_markdown_report(summary, strategy_rows, barrier_rows), encoding="utf-8")
    return AnalysisResult(
        output_dir=output_dir,
        summary_path=summary_path,
        strategy_csv_path=strategy_csv_path,
        barrier_csv_path=barrier_csv_path,
        report_path=report_path,
    )


def _build_sparse_strategy_cases(
    *,
    repo_root: Path,
    taker_fee_rate: float,
    paths: int,
    seed: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cycle_root = repo_root / SPARSE_BTC_CYCLE_ROOT
    definitions = (
        {
            "strategy_key": "btc_sparse_price_only_72h_fixed",
            "candidate_prefix": "34a6f2ca8856",
            "trades_path": cycle_root / "backtests" / "agg-34a6f2ca8856" / "trades.parquet",
            "source_note": "WPR106-74 BTC price-only sparse volatility-breakout positive row",
        },
        {
            "strategy_key": "btc_sparse_aggflow_contrarian_72h_fixed",
            "candidate_prefix": "fd3c0f361ba7",
            "trades_path": cycle_root / "backtests" / "agg-fd3c0f361ba7" / "trades.parquet",
            "source_note": "WPR106-74 BTC aggTrade contrarian sparse volatility-breakout positive row",
        },
    )
    rows: list[dict[str, Any]] = []
    barrier_rows: list[dict[str, Any]] = []
    for definition in definitions:
        trades = pd.read_parquet(definition["trades_path"])
        for side in (None, "long", "short"):
            case_key = definition["strategy_key"] + ("_all" if side is None else f"_{side}_only")
            returns = reprice_gross_returns(trades, taker_fee_rate=taker_fee_rate, side=side)
            rows.append(
                _strategy_row(
                    strategy_key=case_key,
                    strategy_family="observed_fixed_holding",
                    candidate_prefix=definition["candidate_prefix"],
                    source_note=definition["source_note"],
                    side=side or "all",
                    returns=returns,
                    paths=paths,
                    seed=seed,
                    taker_fee_rate=taker_fee_rate,
                    martingale_stop_return=None,
                )
            )
        for stop_return in DEFAULT_STOP_RETURNS:
            for side in (None, "long"):
                returns, audit = conservative_one_to_two_barrier_returns(
                    trades,
                    stop_return=stop_return,
                    taker_fee_rate=taker_fee_rate,
                    side=side,
                )
                case_key = (
                    f"{definition['strategy_key']}_one_to_two_stop_{_bps_label(stop_return)}"
                    + ("_all" if side is None else f"_{side}_only")
                )
                row = _strategy_row(
                    strategy_key=case_key,
                    strategy_family="conservative_one_to_two_fixed_tp_sl",
                    candidate_prefix=definition["candidate_prefix"],
                    source_note=definition["source_note"],
                    side=side or "all",
                    returns=returns,
                    paths=paths,
                    seed=seed + int(stop_return * 1_000_000),
                    taker_fee_rate=taker_fee_rate,
                    martingale_stop_return=stop_return,
                )
                rows.append(row)
                barrier_rows.append(
                    {
                        "strategy_key": case_key,
                        "candidate_prefix": definition["candidate_prefix"],
                        **audit,
                        "research_only": True,
                        "observe_only": True,
                        "promotion_ready": False,
                    }
                )
    return rows, barrier_rows


def _strategy_row(
    *,
    strategy_key: str,
    strategy_family: str,
    candidate_prefix: str,
    source_note: str,
    side: str,
    returns: np.ndarray,
    paths: int,
    seed: int,
    taker_fee_rate: float,
    martingale_stop_return: float | None,
) -> dict[str, Any]:
    fixed = monte_carlo_summary(returns, paths=paths, seed=seed, martingale=False)
    martingale = monte_carlo_summary(returns, paths=paths, seed=seed, martingale=True)
    observed = _observed_summary(returns)
    recovery_streak = (
        martingale_fee_positive_recovery_streak(stop_return=martingale_stop_return, taker_fee_rate=taker_fee_rate)
        if martingale_stop_return is not None
        else None
    )
    martingale_status = _martingale_status(martingale, recovery_streak)
    return {
        "strategy_key": strategy_key,
        "strategy_family": strategy_family,
        "candidate_prefix": candidate_prefix,
        "source_note": source_note,
        "side": side,
        "trade_count": int(returns.size),
        "mean_return": observed["mean_return"],
        "median_return": observed["median_return"],
        "win_rate": observed["win_rate"],
        "observed_compound_return": observed["compound_return"],
        "observed_max_loss_streak": observed["max_loss_streak"],
        "fixed_terminal_return_p05": fixed.get("terminal_return_p05"),
        "fixed_terminal_return_median": fixed.get("terminal_return_median"),
        "fixed_terminal_return_mean": fixed.get("terminal_return_mean"),
        "fixed_probability_terminal_negative": fixed.get("probability_terminal_negative"),
        "fixed_max_drawdown_p05": fixed.get("max_drawdown_p05"),
        "fixed_max_loss_streak_p95": fixed.get("max_loss_streak_p95"),
        "martingale_terminal_return_p05": martingale.get("terminal_return_p05"),
        "martingale_terminal_return_median": martingale.get("terminal_return_median"),
        "martingale_probability_terminal_negative": martingale.get("probability_terminal_negative"),
        "martingale_ruin_probability": martingale.get("ruin_probability"),
        "martingale_max_multiplier_p95": martingale.get("martingale_multiplier_max_p95"),
        "martingale_max_loss_streak_p95": martingale.get("max_loss_streak_p95"),
        "martingale_fee_positive_recovery_streak": recovery_streak,
        "martingale_status": martingale_status,
        "evidence_status": "monte_carlo_evaluated" if returns.size else "no_trade_returns",
        "taker_fee_rate": float(taker_fee_rate),
        "round_trip_fee_return": round_trip_fee_return(taker_fee_rate),
        "funding_included": False,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
    }


def _load_knn_archive_rejections(*, repo_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for symbol in ("btcusdt", "ethusdt"):
        path = repo_root / KNN_ARCHIVE_ROOT / "matrices" / symbol / "experiment_summary.csv"
        if not path.exists():
            continue
        frame = pd.read_csv(path)
        for record in frame.to_dict(orient="records"):
            rows.append(
                {
                    "strategy_key": str(record.get("slug") or ""),
                    "strategy_family": "wpr106_79_knn_archive_summary_rejected",
                    "candidate_prefix": "",
                    "source_note": "WPR106-79 2024 archive-backed no-RSI KNN matrix summary",
                    "side": "matrix_summary",
                    "trade_count": int(float(record.get("knn_trade_count") or 0)),
                    "mean_return": _float(record.get("knn_expectancy_after_cost")),
                    "median_return": "",
                    "win_rate": "",
                    "observed_compound_return": "",
                    "observed_max_loss_streak": "",
                    "fixed_terminal_return_p05": "",
                    "fixed_terminal_return_median": "",
                    "fixed_terminal_return_mean": "",
                    "fixed_probability_terminal_negative": "",
                    "fixed_max_drawdown_p05": "",
                    "fixed_max_loss_streak_p95": "",
                    "martingale_terminal_return_p05": "",
                    "martingale_terminal_return_median": "",
                    "martingale_probability_terminal_negative": "",
                    "martingale_ruin_probability": "",
                    "martingale_max_multiplier_p95": "",
                    "martingale_max_loss_streak_p95": "",
                    "martingale_fee_positive_recovery_streak": "",
                    "martingale_status": "not_evaluated_negative_archive_matrix",
                    "evidence_status": "rejected_by_archive_matrix_negative_after_cost_expectancy",
                    "taker_fee_rate": "",
                    "round_trip_fee_return": "",
                    "funding_included": False,
                    "research_only": True,
                    "observe_only": True,
                    "promotion_ready": False,
                }
            )
    return rows


def _simulate_martingale_paths(sampled: np.ndarray, *, multiplier: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    terminal = np.empty(sampled.shape[0], dtype=float)
    drawdowns = np.empty(sampled.shape[0], dtype=float)
    streaks = np.empty(sampled.shape[0], dtype=int)
    max_multipliers = np.empty(sampled.shape[0], dtype=float)
    ruin = np.zeros(sampled.shape[0], dtype=bool)
    for idx, row in enumerate(sampled):
        equity = 1.0
        peak = 1.0
        worst_dd = 0.0
        size = 1.0
        max_size = 1.0
        current_streak = 0
        longest_streak = 0
        for value in row:
            equity *= 1.0 + (size * float(value))
            if equity <= 0.0 or not math.isfinite(equity):
                ruin[idx] = True
                equity = 0.0
                worst_dd = -1.0
                break
            peak = max(peak, equity)
            worst_dd = min(worst_dd, (equity / peak) - 1.0)
            if float(value) <= 0.0:
                current_streak += 1
                longest_streak = max(longest_streak, current_streak)
                size *= float(multiplier)
                max_size = max(max_size, size)
            else:
                current_streak = 0
                size = 1.0
        terminal[idx] = equity - 1.0
        drawdowns[idx] = worst_dd
        streaks[idx] = longest_streak
        max_multipliers[idx] = max_size
    return terminal, drawdowns, streaks, max_multipliers, ruin


def _observed_summary(returns: np.ndarray) -> dict[str, Any]:
    values = np.asarray(returns, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return {"mean_return": "", "median_return": "", "win_rate": "", "compound_return": "", "max_loss_streak": ""}
    return {
        "mean_return": _float(np.mean(values)),
        "median_return": _float(np.median(values)),
        "win_rate": _float(np.mean(values > 0.0)),
        "compound_return": _float(np.prod(1.0 + values) - 1.0),
        "max_loss_streak": int(max_loss_streak(values)),
    }


def _martingale_status(summary: Mapping[str, Any], recovery_streak: int | None) -> str:
    if not summary.get("available"):
        return "not_evaluated_no_returns"
    if recovery_streak is None:
        return "blocked_not_fixed_rr_payload"
    p95_streak = float(summary.get("max_loss_streak_p95") or 0.0)
    ruin_probability = float(summary.get("ruin_probability") or 0.0)
    p05 = float(summary.get("terminal_return_p05") or -1.0)
    if ruin_probability > 0.0:
        return "blocked_ruin_probability_positive"
    if p95_streak > float(recovery_streak):
        return "blocked_loss_streak_exceeds_fee_positive_recovery"
    if p05 <= 0.0:
        return "blocked_p05_terminal_return_not_positive"
    return "allowed_for_followup"


def _next_decision(*, strategy_rows: list[dict[str, Any]], martingale_allowed: list[dict[str, Any]]) -> dict[str, Any]:
    if not strategy_rows:
        return {
            "decision": "do_not_run_expensive_optimizer",
            "reason": "no_strategy_has_positive_5pct_monte_carlo_terminal_return_with_low_negative_terminal_probability",
            "next_goal": "invent_and_test_btc_long_only_sparse_or_sequence-proven_barrier_exits_before_large_optimization",
        }
    return {
        "decision": "candidate_for_focused_followup_only",
        "reason": "one_or_more_rows_passed_the_offline_monte_carlo_prefilter_but_still_need_split_cost_gate_evidence",
        "martingale_allowed_count": len(martingale_allowed),
    }


def _render_markdown_report(summary: Mapping[str, Any], strategy_rows: list[dict[str, Any]], barrier_rows: list[dict[str, Any]]) -> str:
    evaluated = [row for row in strategy_rows if row.get("evidence_status") == "monte_carlo_evaluated"]
    best = sorted(
        evaluated,
        key=lambda row: float(row.get("fixed_terminal_return_p05") or -1.0),
        reverse=True,
    )[:8]
    lines = [
        "# WPR106-80 Monte Carlo Exit And Sizing Sieve",
        "",
        "## Boundary",
        "",
        "Research-only, observe-only, promotion-disabled. No candidate pack, live/paper artifact, order placement, runtime-mode change, or position-sizing change was made.",
        "",
        "## Cost Assumption",
        "",
        f"- Taker commission per side: {float(summary['taker_fee_rate']):.6f}.",
        f"- Round-trip commission: {float(summary['round_trip_fee_return']):.6f}.",
        "- Funding and slippage ignored for this user-requested offline sieve.",
        "",
        "## Best Offline Rows By 5% Monte Carlo Terminal Return",
        "",
        "| Strategy | Trades | Mean Return | Win Rate | Fixed MC p05 | Fixed MC P(negative) | Loss Streak p95 | Martingale Status |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in best:
        lines.append(
            "| {strategy_key} | {trade_count} | {mean_return:.6f} | {win_rate:.3f} | {fixed_terminal_return_p05:.6f} | {fixed_probability_terminal_negative:.3f} | {fixed_max_loss_streak_p95:.1f} | {martingale_status} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"- `{summary['next_decision']['decision']}`: {summary['next_decision']['reason']}.",
            f"- Martingale allowed rows: {summary['martingale_allowed_count']}.",
            "- KNN archive rows are not expensive-optimizer candidates because WPR106-79 larger validation was negative after costs.",
            "- 1:2 fixed TP/SL rows remain offline MAE/MFE diagnostics; ambiguous paths are counted as stop-first and need lower-timeframe sequence proof before any upgrade.",
            "",
            "## External Research Sources",
            "",
        ]
    )
    for source in summary["external_research_sources"]:
        lines.append(f"- [{source['label']}]({source['url']}): {source['use']}")
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            f"- Strategy Monte Carlo CSV: `{summary['strategy_csv_path']}`",
            f"- Fixed-barrier audit CSV: `{summary['barrier_csv_path']}`",
            "",
        ]
    )
    high_ambiguity = [
        row
        for row in barrier_rows
        if float(row.get("ambiguous_rate") or 0.0) > 0.25
    ]
    if high_ambiguity:
        lines.extend(
            [
                "## Barrier Caveat",
                "",
                f"{len(high_ambiguity)} fixed TP/SL audits had more than 25% ambiguous MAE/MFE paths. Treat them as lower-bound diagnostics until a lower-timeframe triple-barrier rerun proves hit order.",
                "",
            ]
        )
    return "\n".join(lines)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def _external_sources() -> list[dict[str, str]]:
    return [
        {
            "label": "Vezeris et al. 2018 TP/SL comparison",
            "url": "https://www.mdpi.com/1911-8074/11/3/56",
            "use": "supports testing simple fixed and ATR-style TP/SL exits against baselines rather than assuming they improve entries",
        },
        {
            "label": "Financial Innovation 2025 crypto triple-barrier study",
            "url": "https://link.springer.com/article/10.1186/s40854-025-00866-w",
            "use": "supports triple-barrier labels with profit, stop, and time barriers, and sensitivity testing of barrier parameters",
        },
        {
            "label": "Leung and Zhang trailing-stop optimal stopping paper",
            "url": "https://ideas.repec.org/p/arx/papers/1701.03960.html",
            "use": "supports treating trailing stops as path-dependent exits requiring explicit path/order evidence",
        },
        {
            "label": "Moallemi and Wang 2022 RL optimal execution",
            "url": "https://moallemi.com/ciamac/papers/rl-exec-2021.pdf",
            "use": "keeps RL/optimal-stopping exits as a later model family that needs execution-timing data, not a quick optimizer tweak",
        },
    ]


def _empty_barrier_audit(*, stop_return: float, side: str | None) -> dict[str, Any]:
    return {
        "stop_return": float(stop_return),
        "target_return": float(stop_return) * 2.0,
        "side": side or "all",
        "trade_count": 0,
        "target_only_count": 0,
        "stop_only_count": 0,
        "ambiguous_stop_first_count": 0,
        "time_exit_count": 0,
        "target_only_rate": 0.0,
        "stop_or_ambiguous_rate": 0.0,
        "ambiguous_rate": 0.0,
        "sequence_note": "no_trade_returns",
    }


def _safe_ratio(numerator: int, denominator: int) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def _float(value: object) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return parsed if math.isfinite(parsed) else float("nan")


def _bps_label(value: float) -> str:
    return f"{int(round(float(value) * 10_000))}bps"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run WPR106-80 research-only Monte Carlo exit/sizing sieve.")
    parser.add_argument(
        "--output-dir",
        default="data/research/monte_carlo_exit_sizing/wpr106_80",
        help="Output directory for research-only reports.",
    )
    parser.add_argument("--paths", type=int, default=DEFAULT_MONTE_CARLO_PATHS)
    parser.add_argument("--seed", type=int, default=DEFAULT_MONTE_CARLO_SEED)
    parser.add_argument("--taker-fee-rate", type=float, default=DEFAULT_TAKER_FEE_RATE)
    args = parser.parse_args(argv)
    result = run_wpr10680_analysis(
        output_dir=Path(args.output_dir),
        paths=args.paths,
        seed=args.seed,
        taker_fee_rate=args.taker_fee_rate,
    )
    print(_canonical_json(result.to_payload()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
