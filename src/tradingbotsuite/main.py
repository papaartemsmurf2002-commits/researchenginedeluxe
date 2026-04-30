import argparse
import asyncio
from dataclasses import replace
from pathlib import Path

from tradingbotsuite.config import AppConfig
from tradingbotsuite.core.models import RuntimeMode
from tradingbotsuite.live_smoke import run_live_smoke
from tradingbotsuite.manual_cli import run_manual_shell
from tradingbotsuite.research.deterministic_datasets import (
    DETERMINISTIC_SWEEP_VARIANTS,
    write_hmm_knn_sweep_datasets,
)
from tradingbotsuite.research.data_pipeline import DATA_PIPELINE_STAGES, prepare_hmm_knn_research_data
from tradingbotsuite.research.hmm_knn import replay_hmm_knn_artifact, run_hmm_knn_research
from tradingbotsuite.research.hmm_knn_experiments import run_hmm_knn_experiment_matrix
from tradingbotsuite.research.hmm_knn_monitoring import monitor_hmm_knn_artifact
from tradingbotsuite.research.experiment_runner import (
    run_research_experiment,
    write_research_experiment_benchmark_report,
)
from tradingbotsuite.research.market_data import (
    collect_binance_usdm_bars,
    download_and_ingest_binance_vision_archive,
    download_binance_vision_archive,
    fetch_crypto_lake_archive,
    ingest_crypto_lake_archive,
)
from tradingbotsuite.research.workflow import build_dataset, calibrate_model_artifact, replay_eval_artifact, train_model
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

    train = subparsers.add_parser("train-model", help="Train the BTC acceptance baseline")
    train.add_argument("--dataset", required=True)
    train.add_argument("--config", dest="research_config", default=None)

    calibrate = subparsers.add_parser("calibrate-model", help="Calibrate the trained BTC acceptance model")
    calibrate.add_argument("--train-manifest", required=True)
    calibrate.add_argument("--config", dest="research_config", default=None)

    replay = subparsers.add_parser("replay-eval", help="Run replay evaluation for the BTC acceptance model")
    replay.add_argument("--artifact-manifest", required=True)
    replay.add_argument("--config", dest="research_config", default=None)

    hmm_knn = subparsers.add_parser("research-hmm-knn", help="Run BTC HMM-routed Lorentzian KNN research")
    hmm_knn.add_argument("--config", required=True)
    hmm_knn.add_argument("--dataset", default=None)
    hmm_knn.add_argument("--output-dir", default=None)

    hmm_knn_replay = subparsers.add_parser("replay-hmm-knn", help="Summarize an HMM/KNN research artifact")
    hmm_knn_replay.add_argument("--manifest", required=True)

    hmm_knn_monitor = subparsers.add_parser("monitor-hmm-knn", help="Write an observe-only HMM/KNN monitoring report")
    hmm_knn_monitor.add_argument("--manifest", required=True)

    hmm_knn_experiments = subparsers.add_parser("run-hmm-knn-experiments", help="Run a cached HMM/KNN research experiment matrix")
    hmm_knn_experiments.add_argument("--spec", required=True)
    hmm_knn_experiments.add_argument("--dataset", default=None, help="Override the dataset path in the experiment spec")
    hmm_knn_experiments.add_argument("--output-dir", default=None)
    hmm_knn_experiments.add_argument("--cache-dir", default=None)
    hmm_knn_experiments.add_argument("--force", action="store_true", help="Refresh cached experiment artifacts")
    hmm_knn_experiments.add_argument("--skip-monitor", action="store_true", help="Do not write monitor-hmm-knn reports for experiment artifacts")
    hmm_knn_experiments.add_argument("--fail-fast", action="store_true", help="Stop on the first failed experiment")
    hmm_knn_experiments.add_argument("--workers", type=int, default=1, help="Bounded worker count for independent experiment specs")

    hmm_knn_dataset = subparsers.add_parser(
        "write-hmm-knn-sweep-datasets",
        help="Write deterministic offline BTC datasets for repeatable HMM/KNN sweeps",
    )
    hmm_knn_dataset.add_argument("--output-dir", default="data/research/deterministic_sweeps")
    hmm_knn_dataset.add_argument("--row-count", type=int, default=240)
    hmm_knn_dataset.add_argument(
        "--variant",
        choices=[*DETERMINISTIC_SWEEP_VARIANTS, "all"],
        default="all",
        help="Dataset variant to write",
    )

    collect_bars = subparsers.add_parser("collect-binance-bars", help="Collect research-only Binance USD-M historical chart bars")
    collect_bars.add_argument("--symbol", required=True, choices=["BTCUSDT", "ETHUSDT"])
    collect_bars.add_argument("--interval", required=True)
    collect_bars.add_argument("--start-time-ms", required=True, type=int)
    collect_bars.add_argument("--end-time-ms", required=True, type=int)
    collect_bars.add_argument("--output-dir", default=None)
    collect_bars.add_argument("--strict", action="store_true")

    binance_vision = subparsers.add_parser("fetch-binance-vision", help="Download and optionally ingest a Binance Vision research archive")
    binance_vision.add_argument("--symbol", required=True, choices=["BTCUSDT", "ETHUSDT"])
    binance_vision.add_argument("--data-family", required=True, choices=["kline", "trade", "agg_trade"])
    binance_vision.add_argument("--period", required=True, help="Daily YYYY-MM-DD or monthly YYYY-MM period")
    binance_vision.add_argument("--interval", default=None)
    binance_vision.add_argument("--cadence", choices=["daily", "monthly"], default="daily")
    binance_vision.add_argument("--market", choices=["futures/um", "futures/cm", "spot"], default="futures/um")
    binance_vision.add_argument("--output-dir", default=None)
    binance_vision.add_argument("--no-checksum", action="store_true")
    binance_vision.add_argument("--download-only", action="store_true")
    binance_vision.add_argument("--strict", action="store_true")

    crypto_lake = subparsers.add_parser("fetch-crypto-lake", help="Fetch or ingest Crypto Lake research archive data")
    crypto_lake.add_argument("--symbol", required=True, choices=["BTCUSDT", "ETHUSDT"])
    crypto_lake.add_argument("--data-family", required=True, choices=["kline", "trade", "funding_rate", "open_interest"])
    crypto_lake.add_argument("--path", default=None, help="Local Crypto Lake export path: csv/json/jsonl/parquet")
    crypto_lake.add_argument("--start-time", default=None)
    crypto_lake.add_argument("--end-time", default=None)
    crypto_lake.add_argument("--exchange", default="BINANCE")
    crypto_lake.add_argument("--table", default=None)
    crypto_lake.add_argument("--provider-symbol", default=None)
    crypto_lake.add_argument("--interval", default=None)
    crypto_lake.add_argument("--output-dir", default=None)
    crypto_lake.add_argument("--strict", action="store_true")

    prepare_hmm_knn_data = subparsers.add_parser(
        "prepare-hmm-knn-research-data",
        help="Prepare provider-aware research-only HMM/KNN data intake artifacts",
    )
    prepare_hmm_knn_data.add_argument("--spec", required=True)
    prepare_hmm_knn_data.add_argument("--stage", choices=list(DATA_PIPELINE_STAGES), default="intake")

    research_experiment = subparsers.add_parser("run-research-experiment", help="Run a bundled BTC Phase 1 research experiment")
    research_experiment.add_argument("--spec", required=True)

    benchmark_experiment = subparsers.add_parser("benchmark-research-experiment", help="Run repeated research experiment timing reports")
    benchmark_experiment.add_argument("--spec", required=True)
    benchmark_experiment.add_argument("--output-dir", default=None)
    benchmark_experiment.add_argument("--repeat", type=int, default=1)

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


def _archive_payload(result: object) -> dict[str, object]:
    return {
        "output_dir": str(result.output_dir),
        "data_path": str(result.data_path),
        "manifest_path": str(result.manifest_path),
        "row_count": result.row_count,
        "gap_count": result.gap_count,
        "duplicate_count": result.duplicate_count,
        "content_hash": result.content_hash,
        "source_hash": result.source_hash,
    }


def _run_fetch_binance_vision_command(args: argparse.Namespace) -> dict[str, object]:
    output_dir = Path(args.output_dir) if args.output_dir is not None else None
    if args.download_only:
        result = download_binance_vision_archive(
            symbol=args.symbol,
            data_family=args.data_family,
            period=args.period,
            output_dir=output_dir,
            interval=args.interval,
            cadence=args.cadence,
            market=args.market,
            verify_checksum=not args.no_checksum,
        )
        return {
            "url": result.url,
            "output_path": str(result.output_path),
            "checksum_url": result.checksum_url,
            "checksum_path": str(result.checksum_path) if result.checksum_path is not None else None,
            "sha256": result.sha256,
            "verified": result.verified,
        }
    result = download_and_ingest_binance_vision_archive(
        symbol=args.symbol,
        data_family=args.data_family,
        period=args.period,
        output_dir=output_dir,
        interval=args.interval,
        cadence=args.cadence,
        market=args.market,
        strict=args.strict,
        verify_checksum=not args.no_checksum,
    )
    return _archive_payload(result)


def _run_fetch_crypto_lake_command(args: argparse.Namespace) -> dict[str, object]:
    if args.path is not None:
        result = ingest_crypto_lake_archive(
            Path(args.path),
            symbol=args.symbol,
            data_family=args.data_family,
            output_dir=Path(args.output_dir) if args.output_dir is not None else None,
            interval=args.interval,
            provider_symbol=args.provider_symbol,
            strict=args.strict,
        )
    else:
        if args.start_time is None or args.end_time is None:
            raise ValueError("fetch-crypto-lake requires --path or both --start-time and --end-time")
        result = fetch_crypto_lake_archive(
            symbol=args.symbol,
            data_family=args.data_family,
            start_time=args.start_time,
            end_time=args.end_time,
            output_dir=Path(args.output_dir) if args.output_dir is not None else None,
            interval=args.interval,
            exchange=args.exchange,
            table=args.table,
            provider_symbol=args.provider_symbol,
        )
    return _archive_payload(result)


def _run_prepare_hmm_knn_research_data_command(args: argparse.Namespace) -> dict[str, object]:
    result = prepare_hmm_knn_research_data(
        spec_path=Path(args.spec),
        stage=args.stage,
        app_config=AppConfig.from_env(),
    )
    return {
        "output_dir": str(result.output_dir),
        "data_intake_manifest_path": str(result.intake_manifest_path),
        "data_quality_report_path": str(result.data_quality_report_path),
        "market_journal_manifest_path": str(result.market_journal_manifest_path),
        "pipeline_summary_path": str(result.pipeline_summary_path),
        "dataset_manifest_path": str(result.dataset_manifest_path) if result.dataset_manifest_path is not None else None,
        "evidence_manifest_path": str(result.evidence_manifest_path) if result.evidence_manifest_path is not None else None,
    }


def _run_research_experiment_command(args: argparse.Namespace) -> dict[str, object]:
    result = run_research_experiment(
        spec_path=Path(args.spec),
        app_config=AppConfig.from_env(),
    )
    return {
        "output_dir": str(result.output_dir),
        "experiment_run_manifest_path": str(result.manifest_path),
        "conclusion_path": str(result.conclusion_path),
        "pipeline_summary_path": str(result.pipeline_summary_path),
    }


def _run_benchmark_research_experiment_command(args: argparse.Namespace) -> dict[str, object]:
    report_path = write_research_experiment_benchmark_report(
        spec_path=Path(args.spec),
        output_dir=Path(args.output_dir) if args.output_dir is not None else None,
        repeat=args.repeat,
        app_config=AppConfig.from_env(),
    )
    return {"benchmark_report_path": str(report_path)}


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
    elif args.command == "run-hmm-knn-experiments":
        import json

        config = AppConfig.from_env()
        result = run_hmm_knn_experiment_matrix(
            spec_path=Path(args.spec),
            dataset_path=Path(args.dataset) if args.dataset is not None else None,
            output_dir=Path(args.output_dir) if args.output_dir is not None else config.research.output_dir / "hmm_knn_experiments",
            cache_dir=Path(args.cache_dir) if args.cache_dir is not None else None,
            force=args.force,
            write_monitoring=not args.skip_monitor,
            fail_fast=args.fail_fast,
            max_workers=args.workers,
        )
        print(
            json.dumps(
                {
                    "output_dir": str(result.output_dir),
                    "experiment_manifest_path": str(result.manifest_path),
                    "summary_path": str(result.summary_path),
                },
                indent=2,
            )
        )
    elif args.command == "write-hmm-knn-sweep-datasets":
        import json

        variants = DETERMINISTIC_SWEEP_VARIANTS if args.variant == "all" else (args.variant,)
        results = write_hmm_knn_sweep_datasets(
            output_dir=Path(args.output_dir),
            row_count=args.row_count,
            variants=variants,
        )
        print(
            json.dumps(
                {
                    "research_only": True,
                    "observe_only": True,
                    "promotion_ready": False,
                    "datasets": [
                        {
                            "variant": result.variant,
                            "parquet_path": str(result.parquet_path),
                            "csv_path": str(result.csv_path),
                            "manifest_path": str(result.manifest_path),
                            "row_count": result.row_count,
                            "parquet_sha256": result.parquet_sha256,
                            "csv_sha256": result.csv_sha256,
                            "logical_sha256": result.logical_sha256,
                        }
                        for result in results
                    ],
                },
                indent=2,
            )
        )
    elif args.command == "collect-binance-bars":
        import json

        print(json.dumps(_run_collect_binance_bars_command(args), indent=2))
    elif args.command == "fetch-binance-vision":
        import json

        print(json.dumps(_run_fetch_binance_vision_command(args), indent=2))
    elif args.command == "fetch-crypto-lake":
        import json

        print(json.dumps(_run_fetch_crypto_lake_command(args), indent=2))
    elif args.command == "prepare-hmm-knn-research-data":
        import json

        print(json.dumps(_run_prepare_hmm_knn_research_data_command(args), indent=2))
    elif args.command == "run-research-experiment":
        import json

        print(json.dumps(_run_research_experiment_command(args), indent=2))
    elif args.command == "benchmark-research-experiment":
        import json

        print(json.dumps(_run_benchmark_research_experiment_command(args), indent=2))
    else:
        host = getattr(args, "host", "127.0.0.1")
        port = getattr(args, "port", 8000)
        uvicorn.run("tradingbotsuite.main:app", host=host, port=port, reload=False)
