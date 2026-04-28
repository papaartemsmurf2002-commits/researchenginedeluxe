import argparse
import asyncio
from dataclasses import replace
from pathlib import Path

from tradingbotsuite.config import AppConfig
from tradingbotsuite.core.models import RuntimeMode
from tradingbotsuite.live_smoke import run_live_smoke
from tradingbotsuite.manual_cli import run_manual_shell
from tradingbotsuite.research.entry_gate import (
    DEFAULT_GATE_CANDIDATE_CAP,
    GATE_FAMILIES,
    SimulationSettings,
    run_entry_gate_optimizer,
    run_entry_gate_preflight,
    run_entry_gate_research,
)
from tradingbotsuite.research.hmm_knn import replay_hmm_knn_artifact, run_hmm_knn_research
from tradingbotsuite.research.hmm_knn_monitoring import monitor_hmm_knn_artifact
from tradingbotsuite.research.market_data import collect_binance_usdm_bars
from tradingbotsuite.research.workflow import build_dataset, calibrate_model_artifact, replay_eval_artifact, train_model
from tradingbotsuite.research.tradingview_import import import_tradingview_chart_export
from tradingbotsuite.web.app import create_app

app = create_app()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Trading Bot Suite")
    subparsers = parser.add_subparsers(dest="command")

    serve = subparsers.add_parser("serve", help="Run the FastAPI webhook server")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)

    manual = subparsers.add_parser("manual", help="Run the interactive manual signal shell")
    manual.add_argument("--mode", choices=["shadow", "paper", "live"], default=None)

    smoke = subparsers.add_parser("smoke-live", help="Run the Hyperliquid live smoke check")
    smoke.add_argument("--size", type=str, default=None)

    build = subparsers.add_parser("build-dataset", help="Build the BTC research dataset")
    build.add_argument("--config", dest="research_config", default=None)

    tv_import = subparsers.add_parser("import-tv-chart-export", help="Import BTC TradingView chart-export Buy/Sell markers")
    tv_import.add_argument("--path", required=True)
    tv_import.add_argument("--symbol", default="BTCUSDT")
    tv_import.add_argument("--strategy-version", required=True)
    tv_import.add_argument("--timeframe", default="15m")
    tv_import.add_argument("--mode", choices=["replace-batch", "append-only"], default="replace-batch")
    tv_import.add_argument("--notes", default=None)
    tv_import.add_argument("--manifest-dir", default="data/imports")

    train = subparsers.add_parser("train-model", help="Train the BTC acceptance baseline")
    train.add_argument("--dataset", required=True)
    train.add_argument("--config", dest="research_config", default=None)

    calibrate = subparsers.add_parser("calibrate-model", help="Calibrate the trained BTC acceptance model")
    calibrate.add_argument("--train-manifest", required=True)
    calibrate.add_argument("--config", dest="research_config", default=None)

    replay = subparsers.add_parser("replay-eval", help="Run replay evaluation for the BTC acceptance model")
    replay.add_argument("--artifact-manifest", required=True)
    replay.add_argument("--config", dest="research_config", default=None)

    gate = subparsers.add_parser("research-entry-gates", help="Run BTC chart-export trend/chop entry-gate research")
    gate.add_argument("--path", required=True)
    gate.add_argument("--symbol", default="BTCUSDT")
    gate.add_argument("--strategy-version", required=True)
    gate.add_argument("--output-dir", default=None)
    gate.add_argument("--exit-mode", choices=["fixed", "runner"], default="fixed")
    gate.add_argument("--take-profit-pct", type=float, default=0.005)
    gate.add_argument("--stop-loss-pct", type=float, default=0.005)
    gate.add_argument("--runner-activation-pct", type=float, default=0.005)
    gate.add_argument("--runner-trailing-stop-pct", type=float, default=0.003)
    gate.add_argument("--runner-profit-floor-pct", type=float, default=0.001)
    gate.add_argument("--position-size-btc", type=float, default=0.01)
    gate.add_argument("--capital-quote", type=float, default=1000.0)
    gate.add_argument("--entry-slippage-bps", type=float, default=5.0)
    gate.add_argument("--exit-slippage-bps", type=float, default=5.0)
    gate.add_argument("--fee-bps", type=float, default=5.0)
    gate.add_argument("--max-candidates", type=int, default=DEFAULT_GATE_CANDIDATE_CAP)
    gate.add_argument("--gate-family", choices=list(GATE_FAMILIES), default="acf_hvr_dsp")
    gate.add_argument("--allowed-components", default=None, help="Comma-separated component list for the selected gate family")
    gate.add_argument("--ohlcv-cache-policy", choices=["use-or-fetch", "cache-only", "off"], default=None)

    gate_opt = subparsers.add_parser("optimize-entry-gates", help="Run heavy BTC entry-gate and component optimizer")
    gate_opt.add_argument("--path", required=True)
    gate_opt.add_argument("--symbol", default="BTCUSDT")
    gate_opt.add_argument("--strategy-version", required=True)
    gate_opt.add_argument("--output-dir", default=None)
    gate_opt.add_argument("--max-gate-candidates", type=int, default=DEFAULT_GATE_CANDIDATE_CAP)
    gate_opt.add_argument("--exit-profile", choices=["runner", "fixed"], default="runner")
    gate_opt.add_argument("--top-n", type=int, default=5)
    gate_opt.add_argument("--workers", type=int, default=1)
    gate_opt.add_argument("--uncapped", action="store_true", help="Run the full theoretical grid; this can take impractically long.")
    gate_opt.add_argument("--gate-family", choices=list(GATE_FAMILIES), default="acf_hvr_dsp")
    gate_opt.add_argument("--allowed-components", default=None, help="Comma-separated component list for the selected gate family")
    gate_opt.add_argument("--ohlcv-cache-policy", choices=["use-or-fetch", "cache-only", "off"], default=None)

    gate_preflight = subparsers.add_parser("preflight-entry-gates", help="Test each BTC entry-gate component alone before heavy search")
    gate_preflight.add_argument("--path", required=True)
    gate_preflight.add_argument("--symbol", default="BTCUSDT")
    gate_preflight.add_argument("--strategy-version", required=True)
    gate_preflight.add_argument("--output-dir", default=None)
    gate_preflight.add_argument("--gate-family", choices=list(GATE_FAMILIES), default="acf_hvr_dsp")
    gate_preflight.add_argument("--ohlcv-cache-policy", choices=["use-or-fetch", "cache-only", "off"], default=None)

    hmm_knn = subparsers.add_parser("research-hmm-knn", help="Run BTC HMM-routed Lorentzian KNN research")
    hmm_knn.add_argument("--config", required=True)
    hmm_knn.add_argument("--dataset", default=None)
    hmm_knn.add_argument("--output-dir", default=None)

    hmm_knn_replay = subparsers.add_parser("replay-hmm-knn", help="Summarize an HMM/KNN research artifact")
    hmm_knn_replay.add_argument("--manifest", required=True)

    hmm_knn_monitor = subparsers.add_parser("monitor-hmm-knn", help="Write an observe-only HMM/KNN monitoring report")
    hmm_knn_monitor.add_argument("--manifest", required=True)

    collect_bars = subparsers.add_parser("collect-binance-bars", help="Collect research-only Binance USD-M historical chart bars")
    collect_bars.add_argument("--symbol", required=True, choices=["BTCUSDT", "ETHUSDT"])
    collect_bars.add_argument("--interval", required=True)
    collect_bars.add_argument("--start-time-ms", required=True, type=int)
    collect_bars.add_argument("--end-time-ms", required=True, type=int)
    collect_bars.add_argument("--output-dir", default=None)
    collect_bars.add_argument("--strict", action="store_true")

    return parser.parse_args()


def _parse_component_list(value: str | None) -> tuple[str, ...] | None:
    if value is None:
        return None
    components = tuple(component.strip() for component in value.split(",") if component.strip())
    return components or None


def _config_with_runtime_mode(config: AppConfig, mode: str) -> AppConfig:
    return replace(config, runtime_mode=RuntimeMode(mode))


def _config_with_research_config_path(config: AppConfig, config_path: str) -> AppConfig:
    return replace(config, research=replace(config.research, config_path=Path(config_path)))


def _run_collect_binance_bars_command(args: argparse.Namespace) -> dict[str, object]:
    result = asyncio.run(
        collect_binance_usdm_bars(
            symbol=args.symbol,
            interval=args.interval,
            start_time_ms=args.start_time_ms,
            end_time_ms=args.end_time_ms,
            output_dir=Path(args.output_dir) if args.output_dir is not None else None,
            strict=args.strict,
        )
    )
    return {
        "output_dir": str(result.output_dir),
        "data_path": str(result.data_path),
        "manifest_path": str(result.manifest_path),
        "row_count": result.row_count,
        "gap_count": result.gap_count,
        "duplicate_count": result.duplicate_count,
    }


if __name__ == "__main__":
    import uvicorn

    args = parse_args()
    if args.command == "manual":
        config = AppConfig.from_env()
        if args.mode is not None:
            config = _config_with_runtime_mode(config, args.mode)
        asyncio.run(run_manual_shell(config))
    elif args.command == "smoke-live":
        from decimal import Decimal
        import json

        config = AppConfig.from_env()
        result = asyncio.run(run_live_smoke(config, size=Decimal(args.size) if args.size is not None else None))
        print(json.dumps(result, indent=2, default=str))
    elif args.command == "build-dataset":
        import json

        config = AppConfig.from_env()
        if args.research_config is not None:
            config = _config_with_research_config_path(config, args.research_config)
        result = asyncio.run(build_dataset(config))
        print(json.dumps({"dataset_path": str(result.dataset_path), "manifest_path": str(result.manifest_path), "row_count": result.row_count}, indent=2))
    elif args.command == "import-tv-chart-export":
        import json

        config = AppConfig.from_env()
        result = asyncio.run(
            import_tradingview_chart_export(
                config,
                path=Path(args.path),
                symbol=args.symbol,
                strategy_version=args.strategy_version,
                timeframe=args.timeframe,
                mode=args.mode,
                notes=args.notes,
                manifest_dir=Path(args.manifest_dir),
            )
        )
        print(
            json.dumps(
                {
                    "batch_id": result.batch_id,
                    "manifest_path": str(result.manifest_path),
                    "imported_count": result.imported_count,
                    "skipped_count": result.skipped_count,
                    "duplicate_count": result.duplicate_count,
                    "candidate_count": result.candidate_count,
                    "buy_count": result.buy_count,
                    "sell_count": result.sell_count,
                },
                indent=2,
            )
        )
    elif args.command == "train-model":
        import json

        config = AppConfig.from_env()
        if args.research_config is not None:
            config = _config_with_research_config_path(config, args.research_config)
        manifest_path = train_model(config, dataset_path=Path(args.dataset))
        print(json.dumps({"train_manifest_path": str(manifest_path)}, indent=2))
    elif args.command == "calibrate-model":
        import json

        config = AppConfig.from_env()
        if args.research_config is not None:
            config = _config_with_research_config_path(config, args.research_config)
        artifact_manifest_path = calibrate_model_artifact(config, train_manifest_path=Path(args.train_manifest))
        print(json.dumps({"artifact_manifest_path": str(artifact_manifest_path)}, indent=2))
    elif args.command == "replay-eval":
        import json

        config = AppConfig.from_env()
        if args.research_config is not None:
            config = _config_with_research_config_path(config, args.research_config)
        metrics_path = replay_eval_artifact(config, artifact_manifest_path=Path(args.artifact_manifest))
        print(json.dumps({"metrics_path": str(metrics_path)}, indent=2))
    elif args.command == "research-entry-gates":
        import json

        config = AppConfig.from_env()
        result = run_entry_gate_research(
            path=Path(args.path),
            symbol=args.symbol,
            strategy_version=args.strategy_version,
            output_dir=Path(args.output_dir) if args.output_dir is not None else config.research.output_dir,
            settings=SimulationSettings(
                exit_mode=args.exit_mode,
                take_profit_pct=args.take_profit_pct,
                stop_loss_pct=args.stop_loss_pct,
                runner_activation_pct=args.runner_activation_pct,
                runner_trailing_stop_pct=args.runner_trailing_stop_pct,
                runner_profit_floor_pct=args.runner_profit_floor_pct,
                position_size_btc=args.position_size_btc,
                capital_quote=args.capital_quote,
                entry_slippage_bps=args.entry_slippage_bps,
                exit_slippage_bps=args.exit_slippage_bps,
                fee_bps=args.fee_bps,
            ),
            max_candidates=args.max_candidates,
            gate_family=args.gate_family,
            allowed_components=_parse_component_list(args.allowed_components),
            ohlcv_cache_policy=args.ohlcv_cache_policy,
        )
        print(
            json.dumps(
                {
                    "output_dir": str(result.output_dir),
                    "metrics_path": str(result.metrics_path),
                    "grid_results_path": str(result.grid_results_path),
                    "best_gate_manifest_path": str(result.best_gate_manifest_path),
                    "equity_curve_path": str(result.equity_curve_path),
                    "rejected_vs_accepted_path": str(result.rejected_vs_accepted_path),
                },
                indent=2,
            )
        )
    elif args.command == "optimize-entry-gates":
        import json

        config = AppConfig.from_env()
        result = run_entry_gate_optimizer(
            path=Path(args.path),
            symbol=args.symbol,
            strategy_version=args.strategy_version,
            output_dir=Path(args.output_dir) if args.output_dir is not None else config.research.output_dir,
            max_gate_candidates=None if args.uncapped else args.max_gate_candidates,
            exit_profile=args.exit_profile,
            top_n=args.top_n,
            workers=args.workers,
            allowed_components=_parse_component_list(args.allowed_components),
            gate_family=args.gate_family,
            ohlcv_cache_policy=args.ohlcv_cache_policy,
        )
        print(
            json.dumps(
                {
                    "output_dir": str(result.output_dir),
                    "metrics_path": str(result.metrics_path),
                    "top_results_path": str(result.top_results_path),
                    "best_gate_manifest_path": str(result.best_gate_manifest_path),
                    "equity_curve_path": str(result.equity_curve_path),
                    "rejected_vs_accepted_path": str(result.rejected_vs_accepted_path),
                },
                indent=2,
            )
        )
    elif args.command == "preflight-entry-gates":
        import json

        config = AppConfig.from_env()
        result = run_entry_gate_preflight(
            path=Path(args.path),
            symbol=args.symbol,
            strategy_version=args.strategy_version,
            output_dir=Path(args.output_dir) if args.output_dir is not None else config.research.output_dir,
            gate_family=args.gate_family,
            ohlcv_cache_policy=args.ohlcv_cache_policy,
        )
        print(
            json.dumps(
                {
                    "output_dir": str(result.output_dir),
                    "metrics_path": str(result.metrics_path),
                    "preflight_results_path": str(result.preflight_results_path),
                },
                indent=2,
            )
        )
    elif args.command == "research-hmm-knn":
        import json

        config = AppConfig.from_env()
        result = run_hmm_knn_research(
            config_path=Path(args.config),
            dataset_path=Path(args.dataset) if args.dataset is not None else None,
            output_dir=Path(args.output_dir) if args.output_dir is not None else config.research.output_dir,
        )
        print(
            json.dumps(
                {
                    "output_dir": str(result.output_dir),
                    "artifact_manifest_path": str(result.artifact_manifest_path),
                    "metrics_path": str(result.metrics_path),
                    "regime_posteriors_path": str(result.regime_posteriors_path),
                    "knn_predictions_path": str(result.knn_predictions_path),
                    "meta_predictions_path": str(result.meta_predictions_path),
                    "neighbor_diagnostics_path": str(result.neighbor_diagnostics_path),
                },
                indent=2,
            )
        )
    elif args.command == "replay-hmm-knn":
        import json

        metrics_path = replay_hmm_knn_artifact(Path(args.manifest))
        print(json.dumps({"metrics_path": str(metrics_path)}, indent=2))
    elif args.command == "monitor-hmm-knn":
        import json

        report_path = monitor_hmm_knn_artifact(Path(args.manifest))
        print(json.dumps({"monitoring_report_path": str(report_path)}, indent=2))
    elif args.command == "collect-binance-bars":
        import json

        print(json.dumps(_run_collect_binance_bars_command(args), indent=2))
    else:
        host = getattr(args, "host", "127.0.0.1")
        port = getattr(args, "port", 8000)
        uvicorn.run("tradingbotsuite.main:app", host=host, port=port, reload=False)
