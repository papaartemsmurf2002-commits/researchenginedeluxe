import argparse
import asyncio
from dataclasses import replace
from pathlib import Path

from tradingbotsuite.config import AppConfig
from tradingbotsuite.core.models import RuntimeMode
from tradingbotsuite.live.preflight import assert_live_preflight, assert_research_command_not_live
from tradingbotsuite.live_smoke import run_live_smoke
from tradingbotsuite.manual_cli import run_manual_shell
from tradingbotsuite.data.historical_fixture_pack import build_provider_kline_fixture_pack
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
from tradingbotsuite.research.feature_ablation import write_feature_ablation_plan
from tradingbotsuite.research.stage12_research import write_stage12_research_plan
from tradingbotsuite.research_cycle import run_historical_research_cycle, write_research_cycle_benchmark_report
from tradingbotsuite.research_cycle.benchmark import BENCHMARK_TIERS
from tradingbotsuite.promotion.stage13_readiness import write_stage13_readiness_plan
from tradingbotsuite.research.market_data import (
    collect_binance_usdm_bars,
    collect_binance_usdm_context,
    download_and_ingest_binance_vision_archive,
    download_binance_vision_archive,
    fetch_crypto_lake_archive,
    ingest_crypto_lake_archive,
)
from tradingbotsuite.research.workflow import build_dataset, calibrate_model_artifact, replay_eval_artifact, train_model
from tradingbotsuite.web.app import create_app

app = create_app() if __name__ != "__main__" else None


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

    collect_context = subparsers.add_parser(
        "collect-binance-context",
        help="Collect research-only Binance USD-M historical context rows",
    )
    collect_context.add_argument("--symbol", required=True, choices=["BTCUSDT", "ETHUSDT"])
    collect_context.add_argument("--data-family", required=True, choices=["funding_rate", "premium_index", "open_interest"])
    collect_context.add_argument("--start-time-ms", required=True, type=int)
    collect_context.add_argument("--end-time-ms", required=True, type=int)
    collect_context.add_argument("--interval", default="5m")
    collect_context.add_argument("--output-dir", default=None)
    collect_context.add_argument("--strict", action="store_true")

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

    crypto_lake = subparsers.add_parser(
        "fetch-crypto-lake",
        help="Fetch Crypto Lake free sample fallback data or ingest a local Crypto Lake export",
    )
    crypto_lake.add_argument("--symbol", required=True, choices=["BTCUSDT", "ETHUSDT"])
    crypto_lake.add_argument("--data-family", required=True, choices=["kline", "trade", "funding_rate", "open_interest"])
    crypto_lake.add_argument("--path", default=None, help="Local Crypto Lake export path: csv/json/jsonl/parquet")
    crypto_lake.add_argument("--start-time", default=None)
    crypto_lake.add_argument("--end-time", default=None)
    crypto_lake.add_argument("--exchange", default=None)
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

    build_fixture_pack = subparsers.add_parser(
        "build-historical-fixture-pack",
        help="Build a research-only historical fixture pack from a local provider kline manifest",
    )
    build_fixture_pack.add_argument("--source-manifest", required=True)
    build_fixture_pack.add_argument("--output-dir", required=True)
    build_fixture_pack.add_argument("--fixture-id", default=None)
    build_fixture_pack.add_argument("--row-limit", type=int, default=144)
    build_fixture_pack.add_argument("--slice-mode", choices=["tail"], default="tail")
    build_fixture_pack.add_argument(
        "--context-manifest",
        action="append",
        default=[],
        help="Repeatable local provider context manifest for funding, premium, open interest, or aggregate trades",
    )

    research_experiment = subparsers.add_parser("run-research-experiment", help="Run a bundled BTC Phase 1 research experiment")
    research_experiment.add_argument("--spec", required=True)

    benchmark_experiment = subparsers.add_parser("benchmark-research-experiment", help="Run repeated research experiment timing reports")
    benchmark_experiment.add_argument("--spec", required=True)
    benchmark_experiment.add_argument("--output-dir", default=None)
    benchmark_experiment.add_argument("--repeat", type=int, default=1)

    historical_cycle = subparsers.add_parser("run-historical-research-cycle", help="Run a research-only historical strategy cycle")
    historical_cycle.add_argument("--spec", required=True)

    historical_cycle_benchmark = subparsers.add_parser(
        "benchmark-historical-research-cycle",
        help="Run a research-only historical cycle benchmark gate",
    )
    historical_cycle_benchmark.add_argument("--tier", choices=sorted(BENCHMARK_TIERS), default="small")
    historical_cycle_benchmark.add_argument("--output-dir", default=None)
    historical_cycle_benchmark.add_argument("--repeat", type=int, default=2)
    historical_cycle_benchmark.add_argument(
        "--allow-failed-gate",
        action="store_true",
        help="Write a report-only benchmark payload even when the benchmark gate fails",
    )

    feature_ablation = subparsers.add_parser("plan-feature-ablation", help="Write Stage 12.1 feature ablation manifests")
    feature_ablation.add_argument("--output-dir", default=None)
    feature_ablation.add_argument("--dataset-manifest-hash", default="dataset_manifest_unavailable")

    stage12 = subparsers.add_parser("plan-stage12-research", help="Write Stage 12 research manifests for substages 12.1 through 12.7")
    stage12.add_argument("--output-dir", default=None)
    stage12.add_argument("--dataset-manifest-hash", default="dataset_manifest_unavailable")

    stage13 = subparsers.add_parser("plan-stage13-readiness", help="Write Stage 13 readiness templates without running paper, shadow, testnet, or live")
    stage13.add_argument("--output-dir", default=None)

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


def _config_for_command(command: str | None) -> AppConfig:
    config = AppConfig.from_env()
    if command is not None:
        assert_research_command_not_live(config, command)
    return config


def _run_collect_binance_bars_command(args: argparse.Namespace) -> dict[str, object]:
    assert_research_command_not_live(AppConfig.from_env(), "collect-binance-bars")
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


def _run_collect_binance_context_command(args: argparse.Namespace) -> dict[str, object]:
    assert_research_command_not_live(AppConfig.from_env(), "collect-binance-context")
    result = asyncio.run(
        collect_binance_usdm_context(
            symbol=args.symbol,
            data_family=args.data_family,
            start_time_ms=args.start_time_ms,
            end_time_ms=args.end_time_ms,
            interval=args.interval,
            output_dir=Path(args.output_dir) if args.output_dir is not None else None,
            strict=args.strict,
        )
    )
    return _archive_payload(result)


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
    assert_research_command_not_live(AppConfig.from_env(), "fetch-binance-vision")
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
    assert_research_command_not_live(AppConfig.from_env(), "fetch-crypto-lake")
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
    config = _config_for_command("prepare-hmm-knn-research-data")
    result = prepare_hmm_knn_research_data(
        spec_path=Path(args.spec),
        stage=args.stage,
        app_config=config,
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


def _run_build_historical_fixture_pack_command(args: argparse.Namespace) -> dict[str, object]:
    assert_research_command_not_live(AppConfig.from_env(), "build-historical-fixture-pack")
    result = build_provider_kline_fixture_pack(
        source_manifest_path=Path(args.source_manifest),
        output_dir=Path(args.output_dir),
        fixture_id=args.fixture_id,
        row_limit=args.row_limit,
        slice_mode=args.slice_mode,
        context_manifest_paths=[Path(path) for path in getattr(args, "context_manifest", [])],
    )
    return result.to_payload()


def _run_research_experiment_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("run-research-experiment")
    result = run_research_experiment(
        spec_path=Path(args.spec),
        app_config=config,
    )
    return {
        "output_dir": str(result.output_dir),
        "experiment_run_manifest_path": str(result.manifest_path),
        "conclusion_path": str(result.conclusion_path),
        "pipeline_summary_path": str(result.pipeline_summary_path),
    }


def _run_benchmark_research_experiment_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("benchmark-research-experiment")
    report_path = write_research_experiment_benchmark_report(
        spec_path=Path(args.spec),
        output_dir=Path(args.output_dir) if args.output_dir is not None else None,
        repeat=args.repeat,
        app_config=config,
    )
    return {"benchmark_report_path": str(report_path)}


def _run_historical_research_cycle_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("run-historical-research-cycle")
    result = run_historical_research_cycle(
        spec_path=Path(args.spec),
        app_config=config,
    )
    return {
        "output_dir": str(result.output_dir),
        "research_cycle_manifest_path": str(result.manifest_path),
        "candidate_rankings_path": str(result.candidate_rankings_path),
        "backtest_index_path": str(result.backtest_index_path),
        "rejection_report_path": str(result.rejection_report_path),
    }


def _run_benchmark_historical_research_cycle_command(args: argparse.Namespace) -> dict[str, object]:
    import json

    config = _config_for_command("benchmark-historical-research-cycle")
    result = write_research_cycle_benchmark_report(
        output_dir=Path(args.output_dir) if args.output_dir is not None else None,
        tier=args.tier,
        repeat=args.repeat,
        app_config=config,
    )
    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    gate = dict(report.get("benchmark_gate") or {})
    payload = {
        "output_dir": str(result.output_dir),
        "benchmark_report_path": str(result.report_path),
        "tier": str(report.get("tier") or args.tier),
        "repeat": int(report.get("repeat") or args.repeat),
        "benchmark_gate_passed": bool(gate.get("passed", False)),
        "evidence_complete": bool(gate.get("evidence_complete", False)),
        "failure_reasons": list(gate.get("failure_reasons") or []),
        "skipped_reasons": list(gate.get("skipped_reasons") or []),
        "incomplete_evidence_reasons": list(gate.get("incomplete_evidence_reasons") or []),
        "allow_failed_gate": bool(getattr(args, "allow_failed_gate", False)),
    }
    if not payload["benchmark_gate_passed"] and not payload["allow_failed_gate"]:
        reasons = []
        for reason in [
            *payload["failure_reasons"],
            *payload["skipped_reasons"],
            *payload["incomplete_evidence_reasons"],
        ]:
            if reason not in reasons:
                reasons.append(reason)
        detail = ",".join(str(reason) for reason in reasons) or "benchmark_gate_failed"
        raise ValueError(f"benchmark_historical_research_cycle_gate_failed:{detail}")
    return payload


def _run_plan_feature_ablation_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("plan-feature-ablation")
    result = write_feature_ablation_plan(
        output_dir=Path(args.output_dir) if args.output_dir is not None else config.research.output_dir / "stage12" / "feature_ablation",
        dataset_manifest_hash=args.dataset_manifest_hash,
    )
    return {
        "output_dir": str(result.output_dir),
        "feature_ablation_manifest_path": str(result.manifest_path),
        "summary_path": str(result.summary_path),
        "rejected_hypotheses_path": str(result.rejected_hypotheses_path),
        "experiment_spec_dir": str(result.experiment_spec_dir),
    }


def _run_plan_stage12_research_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("plan-stage12-research")
    result = write_stage12_research_plan(
        output_dir=Path(args.output_dir) if args.output_dir is not None else config.research.output_dir / "stage12",
        dataset_manifest_hash=args.dataset_manifest_hash,
    )
    return {
        "output_dir": str(result.output_dir),
        "stage12_research_manifest_path": str(result.manifest_path),
        "summary_path": str(result.summary_path),
        "rejected_hypotheses_path": str(result.rejected_hypotheses_path),
        "limitations_path": str(result.limitations_path),
        "experiment_spec_dir": str(result.experiment_spec_dir),
        "feature_ablation_manifest_path": str(result.feature_ablation_manifest_path),
    }


def _run_plan_stage13_readiness_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("plan-stage13-readiness")
    result = write_stage13_readiness_plan(
        output_dir=Path(args.output_dir) if args.output_dir is not None else config.research.output_dir / "stage13" / "readiness",
    )
    return {
        "output_dir": str(result.output_dir),
        "paper_manifest_template_path": str(result.paper_manifest_template_path),
        "shadow_archive_manifest_template_path": str(result.shadow_archive_manifest_template_path),
        "testnet_validation_manifest_template_path": str(result.testnet_validation_manifest_template_path),
        "readiness_report_path": str(result.readiness_report_path),
        "rollback_runbook_checklist_path": str(result.rollback_runbook_checklist_path),
        "operator_readiness_checklist_path": str(result.operator_readiness_checklist_path),
    }


if __name__ == "__main__":
    import uvicorn

    args = parse_args()
    if args.command == "manual":
        config = _config_for_command(args.command)
        if args.mode is not None:
            config = _config_with_runtime_mode(config, args.mode)
        assert_live_preflight(config, command="manual")
        asyncio.run(run_manual_shell(config))
    elif args.command == "smoke-live":
        from decimal import Decimal
        import json

        config = _config_for_command(args.command)
        assert_live_preflight(config, command="smoke-live")
        result = asyncio.run(run_live_smoke(config, size=Decimal(args.size) if args.size is not None else None))
        print(json.dumps(result, indent=2, default=str))
    elif args.command == "build-dataset":
        import json

        config = _config_for_command(args.command)
        if args.research_config is not None:
            config = _config_with_research_config_path(config, args.research_config)
        result = asyncio.run(build_dataset(config))
        print(json.dumps({"dataset_path": str(result.dataset_path), "manifest_path": str(result.manifest_path), "row_count": result.row_count}, indent=2))
    elif args.command == "train-model":
        import json

        config = _config_for_command(args.command)
        if args.research_config is not None:
            config = _config_with_research_config_path(config, args.research_config)
        manifest_path = train_model(config, dataset_path=Path(args.dataset))
        print(json.dumps({"train_manifest_path": str(manifest_path)}, indent=2))
    elif args.command == "calibrate-model":
        import json

        config = _config_for_command(args.command)
        if args.research_config is not None:
            config = _config_with_research_config_path(config, args.research_config)
        artifact_manifest_path = calibrate_model_artifact(config, train_manifest_path=Path(args.train_manifest))
        print(json.dumps({"artifact_manifest_path": str(artifact_manifest_path)}, indent=2))
    elif args.command == "replay-eval":
        import json

        config = _config_for_command(args.command)
        if args.research_config is not None:
            config = _config_with_research_config_path(config, args.research_config)
        metrics_path = replay_eval_artifact(config, artifact_manifest_path=Path(args.artifact_manifest))
        print(json.dumps({"metrics_path": str(metrics_path)}, indent=2))
    elif args.command == "research-hmm-knn":
        import json

        config = _config_for_command(args.command)
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

        assert_research_command_not_live(AppConfig.from_env(), args.command)
        metrics_path = replay_hmm_knn_artifact(Path(args.manifest))
        print(json.dumps({"metrics_path": str(metrics_path)}, indent=2))
    elif args.command == "monitor-hmm-knn":
        import json

        assert_research_command_not_live(AppConfig.from_env(), args.command)
        report_path = monitor_hmm_knn_artifact(Path(args.manifest))
        print(json.dumps({"monitoring_report_path": str(report_path)}, indent=2))
    elif args.command == "run-hmm-knn-experiments":
        import json

        config = _config_for_command(args.command)
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

        assert_research_command_not_live(AppConfig.from_env(), args.command)
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
    elif args.command == "collect-binance-context":
        import json

        print(json.dumps(_run_collect_binance_context_command(args), indent=2))
    elif args.command == "fetch-binance-vision":
        import json

        print(json.dumps(_run_fetch_binance_vision_command(args), indent=2))
    elif args.command == "fetch-crypto-lake":
        import json

        print(json.dumps(_run_fetch_crypto_lake_command(args), indent=2))
    elif args.command == "prepare-hmm-knn-research-data":
        import json

        print(json.dumps(_run_prepare_hmm_knn_research_data_command(args), indent=2))
    elif args.command == "build-historical-fixture-pack":
        import json

        print(json.dumps(_run_build_historical_fixture_pack_command(args), indent=2))
    elif args.command == "run-research-experiment":
        import json

        print(json.dumps(_run_research_experiment_command(args), indent=2))
    elif args.command == "benchmark-research-experiment":
        import json

        print(json.dumps(_run_benchmark_research_experiment_command(args), indent=2))
    elif args.command == "run-historical-research-cycle":
        import json

        print(json.dumps(_run_historical_research_cycle_command(args), indent=2))
    elif args.command == "benchmark-historical-research-cycle":
        import json

        print(json.dumps(_run_benchmark_historical_research_cycle_command(args), indent=2))
    elif args.command == "plan-feature-ablation":
        import json

        print(json.dumps(_run_plan_feature_ablation_command(args), indent=2))
    elif args.command == "plan-stage12-research":
        import json

        print(json.dumps(_run_plan_stage12_research_command(args), indent=2))
    elif args.command == "plan-stage13-readiness":
        import json

        print(json.dumps(_run_plan_stage13_readiness_command(args), indent=2))
    else:
        host = getattr(args, "host", "127.0.0.1")
        port = getattr(args, "port", 8000)
        assert_live_preflight(AppConfig.from_env(), command="serve")
        uvicorn.run("tradingbotsuite.main:app", host=host, port=port, reload=False)
