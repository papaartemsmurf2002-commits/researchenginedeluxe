from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from tradingbot.backtest import Backtester
from tradingbot.config import default_app_config, load_app_config, save_app_config
from tradingbot.data import DataManager
from tradingbot.live import LiveTrader
from tradingbot.lc_marker_research import report_to_dict, run_marker_research, write_gpt55_casefile
from tradingbot.optimization import WalkForwardOptimizer
from tradingbot.parity import format_parity_dump_for_csv, generate_parity_dump, merge_tv_exports, run_advanced_ta_compare, run_entry_parity_check, run_parity_check
from tradingbot.ui import serve_diagnostics_ui


def _load_config(path: str | None):
    if path is None:
        return default_app_config()
    return load_app_config(path)


def _is_placeholder_path(path: str) -> bool:
    normalized = path.replace("/", "\\").lower()
    return normalized.startswith("path\\to\\") or normalized == "path\\to\\file.csv"


def _load_csv(path: str, *, symbol: str, timeframe: str, output_dir: str = "data/cache") -> pd.DataFrame:
    if _is_placeholder_path(path):
        raise SystemExit(
            "The CSV path you passed is still the README placeholder. "
            f"Use a real file path or fetch data first with: tradingbot fetch-data --symbol {symbol} --days 60 --base-timeframe 15m --confirm-timeframe 5m. "
            f"Default cache location: {Path(output_dir).resolve()}"
        )
    file_path = Path(path)
    if not file_path.exists():
        raise SystemExit(
            f"CSV file not found: {file_path.resolve() if file_path.is_absolute() else file_path}. "
            f"Fetch data first with: tradingbot fetch-data --symbol {symbol} --days 60 --base-timeframe 15m --confirm-timeframe 5m "
            f"or place a valid {timeframe} CSV in {Path(output_dir).resolve()}."
        )
    frame = pd.read_csv(file_path, low_memory=False)
    if "timestamp" in frame.columns:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    return frame


def _add_dataset_args(command: argparse.ArgumentParser) -> None:
    command.add_argument("--base-csv", required=False)
    command.add_argument("--confirm-csv", required=False)
    command.add_argument("--fallback-csv", required=False)
    command.add_argument("--days", type=int, default=60)
    command.add_argument("--base-timeframe", required=False)
    command.add_argument("--confirm-timeframe", required=False)
    command.add_argument("--fallback-timeframe", required=False)
    command.add_argument("--provider-policy", choices=["hyperliquid_only", "hyperliquid_fallback"], default="hyperliquid_fallback")
    command.add_argument("--output-dir", default="data/cache")
    command.add_argument("--force-refresh", action="store_true")
    command.add_argument("--allow-partial", action="store_true")


def _resolve_frames(args, app_config, *, base_only: bool = False):
    if args.symbol not in app_config.strategies:
        raise SystemExit(f"Unknown symbol '{args.symbol}'. Available config profiles: {', '.join(sorted(app_config.strategies))}")
    strategy = app_config.strategies[args.symbol]
    base_timeframe = args.base_timeframe or strategy.base_timeframe
    confirm_timeframe = args.confirm_timeframe or app_config.backtest.execution_timeframe_primary
    fallback_timeframe = args.fallback_timeframe or app_config.backtest.execution_timeframe_fallback

    confirm_required = False if base_only else (strategy.use_order_block_exits or app_config.backtest.use_subcandle_execution)

    if confirm_required and bool(args.base_csv) != bool(args.confirm_csv):
        raise SystemExit("Provide both --base-csv and --confirm-csv together when lower-timeframe execution is enabled, or omit both and let the tool fetch/cache the datasets.")
    if not confirm_required and args.confirm_csv and not args.base_csv:
        raise SystemExit("If you pass --confirm-csv, you must also pass --base-csv.")

    if args.base_csv:
        base_df = _load_csv(args.base_csv, symbol=args.symbol, timeframe=base_timeframe, output_dir=args.output_dir)
        execution_df = None
        fallback_df = None
        resolved = {"base_csv": args.base_csv}
        if args.confirm_csv:
            execution_df = _load_csv(args.confirm_csv, symbol=args.symbol, timeframe=confirm_timeframe, output_dir=args.output_dir)
            resolved["confirm_csv"] = args.confirm_csv
            if args.fallback_csv:
                fallback_df = _load_csv(args.fallback_csv, symbol=args.symbol, timeframe=fallback_timeframe, output_dir=args.output_dir)
                resolved["fallback_csv"] = args.fallback_csv
            else:
                resolved["fallback_csv"] = None
        else:
            resolved["confirm_csv"] = None
            resolved["fallback_csv"] = None
            resolved["confirm_disabled"] = not confirm_required
        return base_df, execution_df, fallback_df, resolved

    manager = DataManager(app_config=app_config, output_dir=args.output_dir)
    try:
        try:
            base_start, base_end = manager.resolve_window(args.days, base_timeframe)
            base_resolution = manager.resolve_dataset(
                symbol=args.symbol,
                timeframe=base_timeframe,
                start=base_start,
                end=base_end,
                provider_policy=args.provider_policy,
                force_refresh=args.force_refresh,
                allow_partial=args.allow_partial,
            )
            confirm_resolution = None
            fallback_resolution = None
            if confirm_required:
                confirm_start, confirm_end = manager.resolve_window(args.days, confirm_timeframe)
                confirm_resolution = manager.resolve_dataset(
                    symbol=args.symbol,
                    timeframe=confirm_timeframe,
                    start=confirm_start,
                    end=confirm_end,
                    provider_policy=args.provider_policy,
                    force_refresh=args.force_refresh,
                    allow_partial=args.allow_partial,
                )
                if fallback_timeframe and fallback_timeframe != confirm_timeframe:
                    fallback_start, fallback_end = manager.resolve_window(args.days, fallback_timeframe)
                    fallback_resolution = manager.resolve_dataset(
                        symbol=args.symbol,
                        timeframe=fallback_timeframe,
                        start=fallback_start,
                        end=fallback_end,
                        provider_policy=args.provider_policy,
                        force_refresh=args.force_refresh,
                        allow_partial=args.allow_partial,
                    )
        except Exception as exc:
            raise SystemExit(
                f"Unable to prepare datasets for {args.symbol}. "
                f"Try 'tradingbot fetch-data --symbol {args.symbol} --days {args.days} --base-timeframe {base_timeframe} --confirm-timeframe {confirm_timeframe}' "
                f"or use --allow-partial if you intentionally want a best-effort dataset. Details: {exc}"
            ) from exc
    finally:
        manager.close()

    base_df = _load_csv(str(base_resolution.csv_path), symbol=args.symbol, timeframe=base_timeframe, output_dir=args.output_dir)
    execution_df = _load_csv(str(confirm_resolution.csv_path), symbol=args.symbol, timeframe=confirm_timeframe, output_dir=args.output_dir) if confirm_resolution is not None else None
    fallback_df = _load_csv(str(fallback_resolution.csv_path), symbol=args.symbol, timeframe=fallback_timeframe, output_dir=args.output_dir) if fallback_resolution is not None else None
    resolved = {
        "base_csv": str(base_resolution.csv_path),
        "confirm_csv": str(confirm_resolution.csv_path) if confirm_resolution is not None else None,
        "fallback_csv": str(fallback_resolution.csv_path) if fallback_resolution is not None else None,
        "base_validation": base_resolution.validation,
        "confirm_validation": confirm_resolution.validation if confirm_resolution is not None else None,
        "fallback_validation": fallback_resolution.validation if fallback_resolution is not None else None,
        "confirm_disabled": not confirm_required,
    }
    return base_df, execution_df, fallback_df, resolved


def main() -> None:
    parser = argparse.ArgumentParser(description="Trading bot framework")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_cmd = subparsers.add_parser("init-config", help="Write a default config file")
    init_cmd.add_argument("--output", default="examples/default.yaml")

    fetch_cmd = subparsers.add_parser("fetch-data", help="Fetch, normalize, validate, and cache backtest datasets")
    fetch_cmd.add_argument("--config", required=False)
    fetch_cmd.add_argument("--symbol", default="BTC")
    fetch_cmd.add_argument("--days", type=int, default=60)
    fetch_cmd.add_argument("--base-timeframe", default="15m")
    fetch_cmd.add_argument("--confirm-timeframe", default="5m")
    fetch_cmd.add_argument("--fallback-timeframe", default="5m")
    fetch_cmd.add_argument("--provider-policy", choices=["hyperliquid_only", "hyperliquid_fallback"], default="hyperliquid_fallback")
    fetch_cmd.add_argument("--output-dir", default="data/cache")
    fetch_cmd.add_argument("--force-refresh", action="store_true")
    fetch_cmd.add_argument("--allow-partial", action="store_true")

    bt_cmd = subparsers.add_parser("backtest", help="Run a backtest")
    bt_cmd.add_argument("--config", required=False)
    bt_cmd.add_argument("--symbol", default="BTC")
    _add_dataset_args(bt_cmd)

    opt_cmd = subparsers.add_parser("optimize", help="Run walk-forward optimization")
    opt_cmd.add_argument("--config", required=False)
    opt_cmd.add_argument("--symbol", default="BTC")
    opt_cmd.add_argument("--output", required=False)
    _add_dataset_args(opt_cmd)

    parity_cmd = subparsers.add_parser("parity-check", help="Compare Python Lorentz output against a TradingView export")
    parity_cmd.add_argument("--config", required=False)
    parity_cmd.add_argument("--symbol", default="BTC")
    parity_cmd.add_argument("--tv-export", required=True)
    parity_cmd.add_argument("--tolerance", type=float, default=1e-6)
    parity_cmd.add_argument("--columns", choices=["all", "features", "kernel", "ann", "signals", "stats"], default="all")
    parity_cmd.add_argument("--report-dir", required=False)
    parity_cmd.add_argument("--skip-rows", type=int, default=0)
    parity_cmd.add_argument("--kernel-preflight", action="store_true", help="Detect kernel config/export mismatches before column comparisons")
    parity_cmd.add_argument("--exclude-last-bar", action="store_true", help="Ignore the final export row, useful when split TradingView exports include a live partial bar")
    _add_dataset_args(parity_cmd)

    merge_exports_cmd = subparsers.add_parser("merge-tv-exports", help="Merge multiple TradingView diagnostic exports by timestamp")
    merge_exports_cmd.add_argument("--config", required=False)
    merge_exports_cmd.add_argument("--input", action="append", required=True, help="TradingView export CSV. Pass once per export.")
    merge_exports_cmd.add_argument("--output", required=True)
    merge_exports_cmd.add_argument("--symbol", default="BTC")

    entry_parity_cmd = subparsers.add_parser("entry-parity", help="Marker-only LC entry parity against a TradingView export")
    entry_parity_cmd.add_argument("--config", required=False)
    entry_parity_cmd.add_argument("--symbol", default="BTC")
    entry_parity_cmd.add_argument("--tv-export", required=True)
    entry_parity_cmd.add_argument("--mode", choices=["sample", "full", "latest"], default="sample")
    entry_parity_cmd.add_argument("--sample-size", type=int, default=100)
    entry_parity_cmd.add_argument("--sample-offset", type=int, default=0)
    entry_parity_cmd.add_argument("--tolerance-bars", type=int, default=1)
    entry_parity_cmd.add_argument("--include-last-bar", action="store_true")
    entry_parity_cmd.add_argument("--no-hypotheses", action="store_true")
    entry_parity_cmd.add_argument("--feature-probes", action="store_true")
    entry_parity_cmd.add_argument("--feature-probe-radius", type=int, default=1)
    entry_parity_cmd.add_argument("--report-dir", required=False)
    _add_dataset_args(entry_parity_cmd)

    parity_dump_cmd = subparsers.add_parser("parity-dump", help="Write Python Lorentz parity diagnostics to CSV")
    parity_dump_cmd.add_argument("--config", required=False)
    parity_dump_cmd.add_argument("--symbol", default="BTC")
    parity_dump_cmd.add_argument("--output", required=True)
    _add_dataset_args(parity_dump_cmd)

    advanced_compare_cmd = subparsers.add_parser("advanced-ta-compare", help="Research-only comparison against the published advanced-ta package")
    advanced_compare_cmd.add_argument("--config", required=False)
    advanced_compare_cmd.add_argument("--symbol", default="BTC")
    _add_dataset_args(advanced_compare_cmd)

    marker_research_cmd = subparsers.add_parser("marker-research", help="Run marker-only LC parity research candidates")
    marker_research_cmd.add_argument("--config", required=True)
    marker_research_cmd.add_argument("--symbol", default="BTC")
    marker_research_cmd.add_argument("--tv-export", required=True)
    marker_research_cmd.add_argument("--report-output", required=False)
    marker_research_cmd.add_argument("--casefile-output", required=False)
    marker_research_cmd.add_argument("--max-candidates", type=int, required=False)
    _add_dataset_args(marker_research_cmd)

    ui_cmd = subparsers.add_parser("serve-ui", help="Start the local LC diagnostics chart UI")
    ui_cmd.add_argument("--config", default="examples/btc_lc_close_10_6000.yaml")
    ui_cmd.add_argument("--symbol", default="BTC")
    ui_cmd.add_argument("--csv", default="btcusdt")
    ui_cmd.add_argument("--host", default="127.0.0.1")
    ui_cmd.add_argument("--port", type=int, default=8765)
    ui_cmd.add_argument("--no-browser", action="store_true")

    bot_cmd = subparsers.add_parser("run-bot", help="Start the live bot shell")
    bot_cmd.add_argument("--config", required=False)
    bot_cmd.add_argument("--symbol", default="BTC")

    args = parser.parse_args()
    if hasattr(args, "symbol"):
        args.symbol = args.symbol.upper()

    if args.command == "init-config":
        config = default_app_config()
        save_app_config(config, args.output)
        print(f"Saved default config to {Path(args.output).resolve()}")
        return

    app_config = _load_config(args.config)

    if args.command == "fetch-data":
        manager = DataManager(app_config=app_config, output_dir=args.output_dir)
        strategy = app_config.strategies[args.symbol]
        fallback_resolution = None
        try:
            try:
                base_start, base_end = manager.resolve_window(args.days, args.base_timeframe)
                base_resolution = manager.resolve_dataset(
                    symbol=args.symbol,
                    timeframe=args.base_timeframe,
                    start=base_start,
                    end=base_end,
                    provider_policy=args.provider_policy,
                    force_refresh=args.force_refresh,
                    allow_partial=args.allow_partial,
                )
                confirm_resolution = None
                if strategy.use_order_block_exits or app_config.backtest.use_subcandle_execution:
                    confirm_start, confirm_end = manager.resolve_window(args.days, args.confirm_timeframe)
                    confirm_resolution = manager.resolve_dataset(
                        symbol=args.symbol,
                        timeframe=args.confirm_timeframe,
                        start=confirm_start,
                        end=confirm_end,
                        provider_policy=args.provider_policy,
                        force_refresh=args.force_refresh,
                        allow_partial=args.allow_partial,
                    )
                    fallback_resolution = None
                    if args.fallback_timeframe != args.confirm_timeframe:
                        fallback_start, fallback_end = manager.resolve_window(args.days, args.fallback_timeframe)
                        fallback_resolution = manager.resolve_dataset(
                            symbol=args.symbol,
                            timeframe=args.fallback_timeframe,
                            start=fallback_start,
                            end=fallback_end,
                            provider_policy=args.provider_policy,
                            force_refresh=args.force_refresh,
                            allow_partial=args.allow_partial,
                        )
            except Exception as exc:
                raise SystemExit(
                    f"Failed to fetch and prepare datasets for {args.symbol}. "
                    f"Requested window: {args.days} days, base timeframe {args.base_timeframe}, confirm timeframe {args.confirm_timeframe}. "
                    f"Details: {exc}"
                ) from exc
        finally:
            manager.close()
        print(
            json.dumps(
                {
                    "symbol": args.symbol,
                    "base_csv": str(base_resolution.csv_path),
                    "confirm_csv": str(confirm_resolution.csv_path) if confirm_resolution is not None else None,
                    "fallback_csv": str(fallback_resolution.csv_path) if fallback_resolution is not None else None,
                    "base_metadata": str(base_resolution.metadata_path),
                    "confirm_metadata": str(confirm_resolution.metadata_path) if confirm_resolution is not None else None,
                    "fallback_metadata": str(fallback_resolution.metadata_path) if fallback_resolution is not None else None,
                    "base_rows": base_resolution.row_count,
                    "confirm_rows": confirm_resolution.row_count if confirm_resolution is not None else 0,
                    "fallback_rows": fallback_resolution.row_count if fallback_resolution is not None else 0,
                    "base_providers": base_resolution.providers,
                    "confirm_providers": confirm_resolution.providers if confirm_resolution is not None else [],
                    "fallback_providers": fallback_resolution.providers if fallback_resolution is not None else [],
                    "base_gaps": base_resolution.gaps,
                    "confirm_gaps": confirm_resolution.gaps if confirm_resolution is not None else [],
                    "fallback_gaps": fallback_resolution.gaps if fallback_resolution is not None else [],
                    "base_validation": base_resolution.validation,
                    "confirm_validation": confirm_resolution.validation if confirm_resolution is not None else None,
                    "fallback_validation": fallback_resolution.validation if fallback_resolution is not None else None,
                    "confirm_disabled": not (strategy.use_order_block_exits or app_config.backtest.use_subcandle_execution),
                },
                indent=2,
                default=str,
            )
        )
        return

    if args.command == "merge-tv-exports":
        if len(args.input) < 2:
            raise SystemExit("Pass at least two --input CSV files to merge.")
        frames = [_load_csv(path, symbol=args.symbol, timeframe="15m") for path in args.input]
        merged = merge_tv_exports(*frames)
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        merged.to_csv(output_path, index=False)
        print(json.dumps({"inputs": args.input, "output": str(output_path), "rows": int(len(merged)), "columns": list(merged.columns)}, indent=2, default=str))
        return

    if args.command == "backtest":
        base_df, execution_df, fallback_df, resolved = _resolve_frames(args, app_config)
        report = Backtester().run(base_df, execution_df, app_config, args.symbol, fallback_df)
        payload = {"inputs": resolved, "metrics": report.metrics, "execution_summary": report.execution_summary}
        print(json.dumps(payload, indent=2, default=str))
        return

    if args.command == "optimize":
        base_df, execution_df, fallback_df, resolved = _resolve_frames(args, app_config)
        result = WalkForwardOptimizer().optimize(base_df, execution_df, app_config, args.symbol, fallback_df)
        change_lines = [item["display"] for item in result.changed_fields] if result.changed_fields else ["No feature parameters changed from baseline."]
        payload = {
            "inputs": resolved,
            "symbol": result.symbol,
            "selection_mode": result.selection_mode,
            "candidate_count": result.candidate_count,
            "prescreen_bars": result.prescreen_bars,
            "shortlist_size": result.shortlist_size,
            "shortlisted_candidate_count": result.shortlisted_candidate_count,
            "search_space": result.search_space,
            "prescreen_top_candidates": result.prescreen_top_candidates,
            "baseline_metrics": result.baseline_report.metrics,
            "baseline_execution_summary": result.baseline_report.execution_summary,
            "metrics": result.best_report.metrics,
            "execution_summary": result.best_report.execution_summary,
            "comparison_to_baseline": result.comparison_to_baseline,
            "changed_fields": result.changed_fields,
            "change_summary": change_lines,
            "best_candidate_summary": result.best_candidate_summary,
            "baseline_config_snapshot": result.baseline_config_snapshot,
            "best_config_snapshot": result.best_config_snapshot,
        }
        if args.output:
            save_app_config(result.best_config, args.output)
        print(json.dumps(payload, indent=2, default=str))
        return

    if args.command == "parity-check":
        base_df, _execution_df, _fallback_df, resolved = _resolve_frames(args, app_config, base_only=True)
        tv_export = _load_csv(args.tv_export, symbol=args.symbol, timeframe="15m", output_dir=args.output_dir)
        result = run_parity_check(
            base_df,
            tv_export,
            app_config,
            args.symbol,
            tolerance=args.tolerance,
            column_group=args.columns,
            report_dir=args.report_dir,
            skip_rows=args.skip_rows,
            kernel_preflight=args.kernel_preflight,
            include_last_bar=not args.exclude_last_bar,
        )
        payload = {
            "inputs": resolved,
            "symbol": args.symbol,
            "matched": result.matched,
            "compared_rows": result.compared_rows,
            "skip_rows": args.skip_rows,
            "included_last_bar": result.included_last_bar,
            "compared_columns": result.compared_columns,
            "missing_columns": result.missing_columns,
            "first_divergence": result.first_divergence,
            "tv_stats": result.tv_stats,
            "preflight": result.preflight,
            "report_files": result.report_files,
        }
        print(json.dumps(payload, indent=2, default=str))
        return

    if args.command == "entry-parity":
        base_df, _execution_df, _fallback_df, resolved = _resolve_frames(args, app_config, base_only=True)
        tv_export = _load_csv(args.tv_export, symbol=args.symbol, timeframe="15m", output_dir=args.output_dir)
        result = run_entry_parity_check(
            base_df,
            tv_export,
            app_config,
            args.symbol,
            mode=args.mode,
            sample_size=args.sample_size,
            sample_offset=args.sample_offset,
            tolerance_bars=args.tolerance_bars,
            include_last_bar=args.include_last_bar,
            run_hypotheses=not args.no_hypotheses,
            run_feature_probes=args.feature_probes,
            feature_probe_radius=args.feature_probe_radius,
            report_dir=args.report_dir,
        )
        payload = {
            "inputs": resolved,
            "symbol": result.symbol,
            "matched": result.matched,
            "mode": result.mode,
            "compared_rows": result.compared_rows,
            "comparison_start": result.comparison_start,
            "comparison_end": result.comparison_end,
            "included_last_bar": result.included_last_bar,
            "tolerance_bars": result.tolerance_bars,
            "sample_size": result.sample_size,
            "sample_offset": result.sample_offset,
            "sample_entry_count": result.sample_entry_count,
            "tv_entry_count": result.tv_entry_count,
            "python_entry_count": result.python_entry_count,
            "matched_entry_count": result.matched_entry_count,
            "missing_entry_count": result.missing_entry_count,
            "extra_entry_count": result.extra_entry_count,
            "entry_match_rate": result.entry_match_rate,
            "ignored_exit_mismatch_count": result.ignored_exit_mismatch_count,
            "first_mismatch": result.first_mismatch,
            "mismatches": result.mismatches[:25],
            "hypothesis_rankings": result.hypothesis_rankings,
            "feature_probe_rankings": result.feature_probe_rankings[:25],
            "report_files": result.report_files,
        }
        print(json.dumps(payload, indent=2, default=str))
        return

    if args.command == "parity-dump":
        base_df, _execution_df, _fallback_df, resolved = _resolve_frames(args, app_config, base_only=True)
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        dump = generate_parity_dump(base_df, app_config, args.symbol)
        format_parity_dump_for_csv(dump).to_csv(output_path, index=False)
        print(json.dumps({"inputs": resolved, "symbol": args.symbol, "output": str(output_path), "rows": int(len(dump))}, indent=2, default=str))
        return

    if args.command == "advanced-ta-compare":
        base_df, _execution_df, _fallback_df, resolved = _resolve_frames(args, app_config, base_only=True)
        result = run_advanced_ta_compare(base_df, app_config, args.symbol)
        print(json.dumps({"inputs": resolved, "symbol": args.symbol, "advanced_ta": result}, indent=2, default=str))
        return

    if args.command == "marker-research":
        base_df, _execution_df, _fallback_df, resolved = _resolve_frames(args, app_config, base_only=True)
        tv_export = _load_csv(args.tv_export, symbol=args.symbol, timeframe="15m", output_dir=args.output_dir)
        report = run_marker_research(
            base_df,
            tv_export,
            app_config,
            args.symbol,
            max_candidates=args.max_candidates,
        )
        payload = {"inputs": resolved, **report_to_dict(report)}
        if args.report_output:
            report_path = Path(args.report_output)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
            payload["report_output"] = str(report_path)
        if args.casefile_output and not (report.matched_exact or report.matched_one_bar):
            kernel_command = (
                f"python -m tradingbot.cli parity-check --config {args.config} --symbol {args.symbol} "
                f"--base-csv {args.base_csv} --tv-export \"{args.tv_export}\" "
                "--columns kernel --skip-rows 26 --tolerance 0.01 --kernel-preflight"
            )
            entry_exact_command = (
                f"python -m tradingbot.cli entry-parity --config {args.config} --symbol {args.symbol} "
                f"--base-csv {args.base_csv} --tv-export \"{args.tv_export}\" "
                "--mode full --tolerance-bars 0 --include-last-bar --no-hypotheses"
            )
            entry_one_bar_command = (
                f"python -m tradingbot.cli entry-parity --config {args.config} --symbol {args.symbol} "
                f"--base-csv {args.base_csv} --tv-export \"{args.tv_export}\" "
                "--mode full --tolerance-bars 1 --include-last-bar --no-hypotheses"
            )
            casefile_path = write_gpt55_casefile(
                args.casefile_output,
                report=report,
                base_path=args.base_csv,
                tv_export_path=args.tv_export,
                config_path=args.config,
                kernel_command=kernel_command,
                entry_exact_command=entry_exact_command,
                entry_one_bar_command=entry_one_bar_command,
            )
            payload["casefile_output"] = str(casefile_path)
        print(json.dumps(payload, indent=2, default=str))
        return

    if args.command == "serve-ui":
        serve_diagnostics_ui(
            config_path=args.config,
            symbol=args.symbol,
            csv_path=args.csv,
            host=args.host,
            port=args.port,
            open_browser=not args.no_browser,
        )
        return

    if args.command == "run-bot":
        trader = LiveTrader(app_config, args.symbol)
        print(json.dumps({"symbol": args.symbol, "state_path": app_config.execution.state_path, "live_enabled": app_config.execution.enable_live_trading}, indent=2))
        trader.save_state({"status": "initialized"})
        return


if __name__ == "__main__":
    main()
