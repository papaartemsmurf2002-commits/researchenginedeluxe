from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from tradingbot.backtest import Backtester
from tradingbot.config import default_app_config, load_app_config, save_app_config
from tradingbot.data import DataManager
from tradingbot.live import LiveTrader
from tradingbot.optimization import WalkForwardOptimizer


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

    if args.command == "run-bot":
        trader = LiveTrader(app_config, args.symbol)
        print(json.dumps({"symbol": args.symbol, "state_path": app_config.execution.state_path, "live_enabled": app_config.execution.enable_live_trading}, indent=2))
        trader.save_state({"status": "initialized"})
        return


if __name__ == "__main__":
    main()
