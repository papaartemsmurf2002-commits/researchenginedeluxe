import argparse
import asyncio
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from tradingbotsuite.config import AppConfig
from tradingbotsuite.core.models import RuntimeMode
from tradingbotsuite.live.preflight import assert_live_preflight, assert_research_command_not_live
from tradingbotsuite.live_smoke import run_live_smoke
from tradingbotsuite.manual_cli import run_manual_shell
from tradingbotsuite.data.durable_public_archive import collect_candidate_depth_public_archive_fixtures
from tradingbotsuite.data.historical_data_catalog import (
    DEFAULT_HISTORICAL_CATALOG_START_MONTH,
    default_historical_catalog_end_month,
    refresh_historical_data_catalog,
)
from tradingbotsuite.data.historical_fixture_pack import build_provider_kline_fixture_pack
from tradingbotsuite.research.deterministic_datasets import (
    DETERMINISTIC_SWEEP_VARIANTS,
    write_hmm_knn_sweep_datasets,
)
from tradingbotsuite.research.data_pipeline import DATA_PIPELINE_STAGES, prepare_hmm_knn_research_data
from tradingbotsuite.research.hmm_knn import replay_hmm_knn_artifact, run_hmm_knn_research
from tradingbotsuite.research.hmm_knn_experiments import run_hmm_knn_experiment_matrix
from tradingbotsuite.research.hmm_knn_monitoring import monitor_hmm_knn_artifact
from tradingbotsuite.research.knn_four_bar import build_four_bar_knn_dataset_from_fixture
from tradingbotsuite.research.knn_four_bar_validation import (
    FOUR_BAR_ARCHIVE_MAPPING_DEFAULT_END_MONTH,
    FOUR_BAR_ARCHIVE_MAPPING_DEFAULT_START_MONTH,
    FOUR_BAR_KNN_LARGER_VALIDATION_DEFAULT_SAMPLE_ROWS_PER_INTERVAL,
    map_local_binance_archive_four_bar_datasets,
    run_four_bar_knn_larger_validation,
)
from tradingbotsuite.research.experiment_runner import (
    run_research_experiment,
    write_research_experiment_benchmark_report,
)
from tradingbotsuite.research.feature_ablation import write_feature_ablation_plan
from tradingbotsuite.research.stage12_research import write_stage12_research_plan
from tradingbotsuite.research_sandbox import (
    DataWindow,
    audit_sandbox_archive_descriptors,
    build_sandbox_archive_manifest,
    build_sandbox_global_leaderboard,
    build_sandbox_iteration_index,
    export_sandbox_suite_validation_request_bundle,
    export_sandbox_validation_request_bundle,
    export_sandbox_venue_expansion_candidate_manifest,
    export_sandbox_venue_expansion_request_bundle,
    index_sandbox_artifacts,
    load_sandbox_run_spec,
    load_sandbox_suite_spec,
    load_strategy_catalog,
    load_venue_archive_descriptors,
    materialize_sandbox_strategy_catalog,
    materialize_sandbox_venue_expansion_requests,
    preflight_sandbox_compatibility,
    preflight_sandbox_strict_validation_descriptors,
    run_sandbox_agent_iteration,
    run_sandbox_archive_sweep,
    run_sandbox_suite,
    show_sandbox_next_action,
    summarize_sandbox_hypotheses,
    summarize_sandbox_archive_coverage,
    summarize_sandbox_run,
    summarize_sandbox_throughput,
    summarize_sandbox_suite_hypotheses,
    verify_sandbox_artifact_integrity,
)
from tradingbotsuite.research_cycle import (
    run_historical_research_cycle,
    write_hardware_utilization_report,
    write_research_cycle_benchmark_report,
)
from tradingbotsuite.research_cycle.benchmark import BENCHMARK_TIERS
from tradingbotsuite.research_discovery.benchmark import DISCOVERY_BENCHMARK_TIERS, write_discovery_benchmark_report
from tradingbotsuite.research_discovery.candidate_pack_bridge import (
    evaluate_discovery_candidate_pack_eligibility,
    write_discovery_candidate_pack_eligibility,
)
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

app = create_app() if __name__ not in {"__main__", "__mp_main__"} else None
REPO_ROOT = Path(__file__).resolve().parents[2]


def _resolve_cli_path(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    repo_candidate = REPO_ROOT / candidate
    if repo_candidate.exists():
        return repo_candidate.resolve()
    return candidate.resolve() if candidate.exists() else candidate


def _optional_sandbox_requested_window(start: str | None, end: str | None) -> DataWindow | None:
    if start is None and end is None:
        return None
    if start is None or end is None:
        raise ValueError("requested-window-start and requested-window-end must be supplied together")
    return DataWindow(start, end)


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

    four_bar_dataset = subparsers.add_parser(
        "build-four-bar-knn-dataset",
        help="Build research-only BTC/ETH four-bar HMM/KNN event-label datasets from durable fixtures",
    )
    four_bar_dataset.add_argument("--fixture-root", required=True)
    four_bar_dataset.add_argument("--symbol", required=True, choices=["BTCUSDT", "ETHUSDT"])
    four_bar_dataset.add_argument("--output-dir", default=None)
    four_bar_dataset.add_argument("--dataset-name", default=None)
    four_bar_dataset.add_argument("--base-interval", action="append", choices=["15m", "1h"], default=[])
    four_bar_dataset.add_argument("--max-rows-per-interval", type=int, default=None)

    four_bar_validation = subparsers.add_parser(
        "run-four-bar-knn-larger-validation",
        help="Run the research-only WPR106-77 no-RSI four-bar KNN larger validation packet",
    )
    four_bar_validation.add_argument("--output-dir", default=None)
    four_bar_validation.add_argument("--btc-fixture-root", default=None)
    four_bar_validation.add_argument("--eth-fixture-root", default=None)
    four_bar_validation.add_argument(
        "--sample-rows-per-interval",
        type=int,
        default=FOUR_BAR_KNN_LARGER_VALIDATION_DEFAULT_SAMPLE_ROWS_PER_INTERVAL,
    )
    four_bar_validation.add_argument("--workers", type=int, default=1)
    four_bar_validation.add_argument("--force", action="store_true", help="Rebuild validation datasets and refresh matrix cache")
    four_bar_validation.add_argument("--skip-monitor", action="store_true", help="Do not write monitor-hmm-knn reports for artifacts")
    four_bar_validation.add_argument("--skip-matrix", action="store_true", help="Only write datasets, specs, manifest, and replay command")

    archive_four_bar = subparsers.add_parser(
        "map-binance-archive-four-bar-datasets",
        help="Map existing local Binance Vision archives into research-only four-bar KNN datasets",
    )
    archive_four_bar.add_argument("--output-dir", default=None)
    archive_four_bar.add_argument("--archive-root", default=None)
    archive_four_bar.add_argument("--start-month", default=FOUR_BAR_ARCHIVE_MAPPING_DEFAULT_START_MONTH)
    archive_four_bar.add_argument("--end-month", default=FOUR_BAR_ARCHIVE_MAPPING_DEFAULT_END_MONTH)
    archive_four_bar.add_argument(
        "--sample-rows-per-interval",
        type=int,
        default=FOUR_BAR_KNN_LARGER_VALIDATION_DEFAULT_SAMPLE_ROWS_PER_INTERVAL,
    )
    archive_four_bar.add_argument("--matrix-workers", type=int, default=1)
    archive_four_bar.add_argument("--force", action="store_true", help="Rebuild mapped archive datasets")

    hmm_knn_dataset = subparsers.add_parser(
        "write-hmm-knn-sweep-datasets",
        help="Write deterministic offline BTC datasets for repeatable HMM/KNN sweeps",
    )
    hmm_knn_dataset.add_argument("--output-dir", default=None)
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
    crypto_lake.add_argument("--data-family", required=True, choices=["kline", "trade", "funding_rate", "open_interest", "liquidation"])
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

    collect_durable_data = subparsers.add_parser(
        "collect-durable-data",
        help="Collect expanded BTC/ETH Binance Vision public-archive fixture packs for required research evidence",
    )
    collect_durable_data.add_argument("--symbol", action="append", choices=["BTCUSDT", "ETHUSDT"], default=[])
    collect_durable_data.add_argument("--start-month", default="2024-01")
    collect_durable_data.add_argument("--end-month", default="2024-12")
    collect_durable_data.add_argument("--output-dir", default=None)

    refresh_catalog = subparsers.add_parser(
        "refresh-historical-data-catalog",
        help="Refresh the R106 central historical-data source-of-truth catalog",
    )
    refresh_catalog.add_argument("--symbol", action="append", choices=["BTCUSDT", "ETHUSDT"], default=[])
    refresh_catalog.add_argument("--start-month", default=DEFAULT_HISTORICAL_CATALOG_START_MONTH)
    refresh_catalog.add_argument("--end-month", default=None)
    refresh_catalog.add_argument("--output-dir", default=None)

    research_experiment = subparsers.add_parser("run-research-experiment", help="Run a bundled BTC Phase 1 research experiment")
    research_experiment.add_argument("--spec", required=True)

    rapid_sandbox = subparsers.add_parser(
        "run-rapid-strategy-sandbox",
        help="Run the 2024+ research-only rapid strategy iteration sandbox",
    )
    rapid_sandbox.add_argument("--spec", required=True, help="Sandbox run spec JSON")
    rapid_sandbox.add_argument("--strategy-catalog", required=True, help="CSV/TSV/JSON/Parquet/XLSX strategy catalog")
    rapid_sandbox.add_argument("--venue-archives", required=True, help="JSON venue archive descriptor manifest")
    rapid_sandbox.add_argument("--market-data", default=None, help="Local normalized market frame or Binance Vision kline CSV/ZIP")
    rapid_sandbox.add_argument("--output-dir", default=None)
    rapid_sandbox.add_argument("--min-request-score", type=float, default=0.0)

    summarize_sandbox = subparsers.add_parser(
        "summarize-rapid-strategy-sandbox",
        help="Summarize an existing research-only rapid strategy sandbox run",
    )
    summarize_sandbox.add_argument("--run-dir", required=True, help="Sandbox run directory under the research output root")
    summarize_sandbox.add_argument("--top-n", type=int, default=10)
    summarize_sandbox.add_argument("--no-write-report", action="store_true")

    rapid_sandbox_suite = subparsers.add_parser(
        "run-rapid-strategy-sandbox-suite",
        help="Run a 2024+ research-only rapid strategy sandbox suite",
    )
    rapid_sandbox_suite.add_argument("--suite", required=True, help="Sandbox suite spec JSON")
    rapid_sandbox_suite.add_argument("--output-dir", default=None)
    rapid_sandbox_suite.add_argument("--top-n", type=int, default=None)
    rapid_sandbox_suite.add_argument("--max-workers", type=int, default=1)

    verify_sandbox_artifacts_parser = subparsers.add_parser(
        "verify-rapid-strategy-sandbox-artifacts",
        help="Verify sandbox run or suite child artifact integrity hashes",
    )
    verify_sandbox_artifacts_parser.add_argument("--target", required=True, help="Sandbox run/suite directory or manifest path")
    verify_sandbox_artifacts_parser.add_argument("--output-dir", default=None)
    verify_sandbox_artifacts_parser.add_argument("--no-write-report", action="store_true")

    summarize_sandbox_hypotheses_parser = subparsers.add_parser(
        "summarize-rapid-strategy-sandbox-hypotheses",
        help="Summarize hypothesis-level falsification decisions for a sandbox run or suite",
    )
    hypothesis_scope = summarize_sandbox_hypotheses_parser.add_mutually_exclusive_group(required=True)
    hypothesis_scope.add_argument("--run-dir", default=None, help="Sandbox run directory under the research output root")
    hypothesis_scope.add_argument("--suite-dir", default=None, help="Sandbox suite directory under the research output root")
    summarize_sandbox_hypotheses_parser.add_argument("--no-write-report", action="store_true")

    export_sandbox_validation_requests = subparsers.add_parser(
        "export-rapid-strategy-sandbox-validation-requests",
        help="Export descriptor-only strict-validation requests from a sandbox run or suite",
    )
    validation_scope = export_sandbox_validation_requests.add_mutually_exclusive_group(required=True)
    validation_scope.add_argument("--run-dir", default=None, help="Sandbox run directory under the research output root")
    validation_scope.add_argument("--suite-dir", default=None, help="Sandbox suite directory under the research output root")
    export_sandbox_validation_requests.add_argument("--output-dir", default=None)

    preflight_sandbox_validation_requests = subparsers.add_parser(
        "preflight-rapid-strategy-sandbox-validation-requests",
        help="Preflight descriptor-only sandbox strict-validation request bundles without executing validation",
    )
    preflight_sandbox_validation_requests.add_argument(
        "--bundle",
        required=True,
        help="Sandbox strict-validation request bundle JSON under the research output root",
    )
    preflight_sandbox_validation_requests.add_argument("--output-dir", default=None)

    export_sandbox_venue_expansion_requests = subparsers.add_parser(
        "export-rapid-strategy-sandbox-venue-expansion-requests",
        help="Export descriptor-only venue archive intake requests from a sandbox artifact catalog",
    )
    export_sandbox_venue_expansion_requests.add_argument(
        "--catalog",
        required=True,
        help="Sandbox artifact catalog JSON under the research output root",
    )
    export_sandbox_venue_expansion_requests.add_argument(
        "--worklist",
        default=None,
        help="Optional venue-expansion worklist Parquet under the research output root",
    )
    export_sandbox_venue_expansion_requests.add_argument("--output-dir", default=None)

    materialize_sandbox_venue_expansion_requests_parser = subparsers.add_parser(
        "materialize-rapid-strategy-sandbox-venue-expansion-requests",
        help="Materialize dry-run descriptor candidates from sandbox venue-expansion requests and local roots",
    )
    materialize_sandbox_venue_expansion_requests_parser.add_argument(
        "--request-bundle",
        required=True,
        help="Sandbox venue-expansion request bundle JSON under the research output root",
    )
    materialize_sandbox_venue_expansion_requests_parser.add_argument(
        "--archive-root",
        action="append",
        required=True,
        help="Explicit local archive root or file to scan",
    )
    materialize_sandbox_venue_expansion_requests_parser.add_argument("--output-dir", default=None)
    materialize_sandbox_venue_expansion_requests_parser.add_argument("--venue", default=None)
    materialize_sandbox_venue_expansion_requests_parser.add_argument("--symbol", default=None)
    materialize_sandbox_venue_expansion_requests_parser.add_argument("--data-family", default=None)
    materialize_sandbox_venue_expansion_requests_parser.add_argument("--interval", default=None)
    materialize_sandbox_venue_expansion_requests_parser.add_argument("--max-files", type=int, default=5000)

    export_sandbox_venue_expansion_candidate_manifest_parser = subparsers.add_parser(
        "export-rapid-strategy-sandbox-venue-expansion-candidate-manifest",
        help="Export a new sandbox venue archive manifest from venue-expansion descriptor candidates",
    )
    export_sandbox_venue_expansion_candidate_manifest_parser.add_argument(
        "--descriptor-candidates",
        required=True,
        help="Sandbox venue-expansion descriptor candidates JSON under the research output root",
    )
    export_sandbox_venue_expansion_candidate_manifest_parser.add_argument("--output-dir", default=None)

    index_sandbox_artifacts_parser = subparsers.add_parser(
        "index-rapid-strategy-sandbox-artifacts",
        help="Index existing research-only rapid strategy sandbox artifacts under the research output root",
    )
    index_sandbox_artifacts_parser.add_argument("--root-dir", default=None)
    index_sandbox_artifacts_parser.add_argument("--output-dir", default=None)
    index_sandbox_artifacts_parser.add_argument("--max-files", type=int, default=5000)
    index_sandbox_artifacts_parser.add_argument("--no-write-report", action="store_true")

    index_sandbox_iterations_parser = subparsers.add_parser(
        "index-rapid-strategy-sandbox-iterations",
        help="Index one-command rapid strategy sandbox iterations under the research output root",
    )
    index_sandbox_iterations_parser.add_argument("--root-dir", default=None)
    index_sandbox_iterations_parser.add_argument("--output-dir", default=None)
    index_sandbox_iterations_parser.add_argument("--max-files", type=int, default=5000)
    index_sandbox_iterations_parser.add_argument("--no-write-report", action="store_true")

    sandbox_next_action_parser = subparsers.add_parser(
        "show-rapid-strategy-sandbox-next-action",
        help="Summarize existing sandbox artifact catalogs and iteration indexes into a next-action report",
    )
    sandbox_next_action_parser.add_argument("--output-root", default=None)
    sandbox_next_action_parser.add_argument(
        "--artifact-catalog",
        action="append",
        default=None,
        help="Existing sandbox_artifact_catalog.json under the research output root",
    )
    sandbox_next_action_parser.add_argument(
        "--iteration-index",
        action="append",
        default=None,
        help="Existing sandbox_iteration_index.json under the research output root",
    )
    sandbox_next_action_parser.add_argument("--output-dir", default=None)
    sandbox_next_action_parser.add_argument("--max-files", type=int, default=5000)
    sandbox_next_action_parser.add_argument("--limit", type=int, default=10)
    sandbox_next_action_parser.add_argument("--no-write-report", action="store_true")

    sandbox_throughput_parser = subparsers.add_parser(
        "summarize-rapid-strategy-sandbox-throughput",
        help="Summarize throughput telemetry from existing rapid strategy sandbox iteration manifests",
    )
    sandbox_throughput_parser.add_argument("--root-dir", default=None)
    sandbox_throughput_parser.add_argument("--output-dir", default=None)
    sandbox_throughput_parser.add_argument("--max-files", type=int, default=5000)
    sandbox_throughput_parser.add_argument("--limit", type=int, default=10)
    sandbox_throughput_parser.add_argument("--no-write-report", action="store_true")

    audit_sandbox_archives = subparsers.add_parser(
        "audit-rapid-strategy-sandbox-archives",
        help="Audit local venue archive descriptors for 2024+ sandbox readiness",
    )
    audit_sandbox_archives.add_argument("--venue-archives", required=True, help="JSON venue archive descriptor manifest")
    audit_sandbox_archives.add_argument("--market-data", default=None, help="Optional shared local market frame for smoke audits")
    audit_sandbox_archives.add_argument("--output-dir", default=None)
    audit_sandbox_archives.add_argument("--requested-window-start", default=None)
    audit_sandbox_archives.add_argument("--requested-window-end", default=None)

    archive_coverage_parser = subparsers.add_parser(
        "summarize-rapid-strategy-sandbox-archive-coverage",
        help="Summarize local venue archive coverage by venue, symbol, family, and interval",
    )
    archive_coverage_parser.add_argument("--venue-archives", required=True, help="JSON venue archive descriptor manifest")
    archive_coverage_parser.add_argument("--market-data", default=None, help="Optional shared local market frame for smoke coverage")
    archive_coverage_parser.add_argument("--output-dir", default=None)
    archive_coverage_parser.add_argument("--requested-window-start", default=None)
    archive_coverage_parser.add_argument("--requested-window-end", default=None)

    build_sandbox_archive_manifest_parser = subparsers.add_parser(
        "build-rapid-strategy-sandbox-archive-manifest",
        help="Build a 2024+ sandbox venue archive manifest from local archive files",
    )
    build_sandbox_archive_manifest_parser.add_argument("--archive-root", action="append", required=True)
    build_sandbox_archive_manifest_parser.add_argument("--output-dir", default=None)
    build_sandbox_archive_manifest_parser.add_argument("--venue", default=None)
    build_sandbox_archive_manifest_parser.add_argument("--symbol", default=None)
    build_sandbox_archive_manifest_parser.add_argument("--data-family", default=None)
    build_sandbox_archive_manifest_parser.add_argument("--interval", default=None)
    build_sandbox_archive_manifest_parser.add_argument("--max-files", type=int, default=5000)

    rank_sandbox_artifacts_parser = subparsers.add_parser(
        "rank-rapid-strategy-sandbox-artifacts",
        help="Build a global hypothesis leaderboard from existing rapid strategy sandbox runs",
    )
    rank_sandbox_artifacts_parser.add_argument("--root-dir", default=None)
    rank_sandbox_artifacts_parser.add_argument("--output-dir", default=None)
    rank_sandbox_artifacts_parser.add_argument("--max-runs", type=int, default=5000)
    rank_sandbox_artifacts_parser.add_argument("--top-n", type=int, default=100)
    rank_sandbox_artifacts_parser.add_argument("--no-write-report", action="store_true")

    build_sandbox_strategy_catalog_parser = subparsers.add_parser(
        "build-rapid-strategy-sandbox-strategy-catalog",
        help="Materialize a normalized sandbox strategy catalog from local strategy files",
    )
    build_sandbox_strategy_catalog_parser.add_argument("--catalog-root", action="append", required=True)
    build_sandbox_strategy_catalog_parser.add_argument("--output-dir", default=None)
    build_sandbox_strategy_catalog_parser.add_argument("--max-files", type=int, default=5000)

    sandbox_preflight_parser = subparsers.add_parser(
        "preflight-rapid-strategy-sandbox",
        help="Preflight strategy/catalog/archive compatibility before a sandbox sweep",
    )
    sandbox_preflight_parser.add_argument("--spec", required=True)
    sandbox_preflight_parser.add_argument("--strategy-catalog", required=True)
    sandbox_preflight_parser.add_argument("--venue-archives", required=True)
    sandbox_preflight_parser.add_argument("--market-data", default=None)
    sandbox_preflight_parser.add_argument("--output-dir", default=None)

    sandbox_iteration_parser = subparsers.add_parser(
        "run-rapid-strategy-sandbox-iteration",
        help="Run a one-command archive-backed rapid strategy sandbox iteration",
    )
    sandbox_iteration_parser.add_argument("--spec", default=None)
    strategy_input = sandbox_iteration_parser.add_mutually_exclusive_group(required=True)
    strategy_input.add_argument("--strategy-catalog", default=None)
    strategy_input.add_argument("--catalog-root", action="append", default=None)
    archive_input = sandbox_iteration_parser.add_mutually_exclusive_group(required=True)
    archive_input.add_argument("--venue-archives", default=None)
    archive_input.add_argument("--archive-root", action="append", default=None)
    sandbox_iteration_parser.add_argument("--output-dir", default=None)
    sandbox_iteration_parser.add_argument("--run-id", default=None)
    sandbox_iteration_parser.add_argument("--window-start", default="2024-01-01")
    sandbox_iteration_parser.add_argument("--window-end", default="2024-12-31")
    sandbox_iteration_parser.add_argument("--window-preset", default="explicit")
    sandbox_iteration_parser.add_argument("--window-as-of-date", default=None)
    sandbox_iteration_parser.add_argument("--window-lookback-days", type=int, default=365)
    sandbox_iteration_parser.add_argument("--holding-periods", default="1,2,4,8")
    sandbox_iteration_parser.add_argument("--round-trip-cost-bps", type=float, default=8.0)
    sandbox_iteration_parser.add_argument("--min-trades", type=int, default=5)
    sandbox_iteration_parser.add_argument("--max-evidence-requests", type=int, default=10)
    sandbox_iteration_parser.add_argument("--rank-top-n", type=int, default=100)
    sandbox_iteration_parser.add_argument("--min-request-score", type=float, default=0.0)
    sandbox_iteration_parser.add_argument("--catalog-max-files", type=int, default=5000)
    sandbox_iteration_parser.add_argument("--archive-max-files", type=int, default=5000)
    sandbox_iteration_parser.add_argument("--archive-venue", default=None)
    sandbox_iteration_parser.add_argument("--archive-symbol", default=None)
    sandbox_iteration_parser.add_argument("--archive-data-family", default=None)
    sandbox_iteration_parser.add_argument("--archive-interval", default=None)
    sandbox_iteration_parser.add_argument("--leaderboard-max-runs", type=int, default=5000)
    sandbox_iteration_parser.add_argument("--leaderboard-top-n", type=int, default=100)

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

    discovery_benchmark = subparsers.add_parser(
        "benchmark-discovery-run",
        help="Run a research-only discovery run-manager benchmark gate",
    )
    discovery_benchmark.add_argument("--tier", choices=sorted(DISCOVERY_BENCHMARK_TIERS), default="quick")
    discovery_benchmark.add_argument("--output-dir", default=None)
    discovery_benchmark.add_argument("--repeat", type=int, default=1)
    discovery_benchmark.add_argument(
        "--allow-failed-gate",
        action="store_true",
        help="Write a report-only benchmark payload even when the discovery benchmark gate fails",
    )

    hardware_benchmark = subparsers.add_parser(
        "benchmark-hardware-utilization",
        help="Run a research-only CPU/GPU hardware utilization benchmark",
    )
    hardware_benchmark.add_argument("--output-dir", default=None)
    hardware_benchmark.add_argument("--cpu-workers", type=int, default=None)
    hardware_benchmark.add_argument("--cpu-seconds", type=float, default=3.0)
    hardware_benchmark.add_argument("--gpu-seconds", type=float, default=3.0)
    hardware_benchmark.add_argument("--matrix-size", type=int, default=1024)

    discovery_pack_bridge = subparsers.add_parser(
        "evaluate-discovery-candidate-pack-eligibility",
        help="Write a research-only discovery-to-candidate-pack eligibility audit",
    )
    discovery_pack_bridge.add_argument("--discovery-manifest", required=True)
    discovery_pack_bridge.add_argument("--cycle-manifest", default=None)
    discovery_pack_bridge.add_argument("--exit-lab-manifest", default=None)
    discovery_pack_bridge.add_argument("--multiple-testing-manifest", default=None)
    discovery_pack_bridge.add_argument("--validation-floors-manifest", default=None)
    discovery_pack_bridge.add_argument("--output-dir", default=None)
    discovery_pack_bridge.add_argument(
        "--candidate-id-map-json",
        default=None,
        help="JSON object mapping discovery candidate ids to historical-cycle candidate ids",
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


def _research_output_root(config: AppConfig) -> Path:
    path = Path(config.research.output_dir).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (REPO_ROOT / path).resolve()


def _resolve_research_output_dir(raw_path: str | Path, *, config: AppConfig, field_name: str) -> Path:
    root = _research_output_root(config)
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{field_name} must stay inside the configured research output directory") from exc
    return resolved


def _resolve_optional_research_output_dir(
    raw_path: str | Path | None,
    *,
    config: AppConfig,
    field_name: str = "output_dir",
) -> Path | None:
    if raw_path is None:
        return None
    return _resolve_research_output_dir(raw_path, config=config, field_name=field_name)


def _default_research_output_dir(config: AppConfig, *relative_parts: str) -> Path:
    return _research_output_root(config).joinpath(*relative_parts)


def _default_discovery_bridge_output_dir(
    config: AppConfig,
    result: object,
) -> Path:
    manifest = dict(getattr(result, "manifest", {}) or {})
    discovery_path = Path(str(getattr(result, "discovery_manifest_path", "discovery")))
    run_part = _safe_cli_path_part(discovery_path.parent.name or discovery_path.stem or "discovery")
    source_hash = str(manifest.get("source_discovery_manifest_sha256") or "missing")[:12]
    cycle_hash = str(manifest.get("source_cycle_manifest_sha256") or "no-cycle")[:12]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return (
        _research_output_root(config)
        / "discovery_candidate_pack_bridge"
        / f"{run_part}_{timestamp}_{source_hash}_{cycle_hash}"
    )


def _safe_cli_path_part(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in str(value).strip())
    return (safe or "run")[:96]


def _run_research_hmm_knn_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("research-hmm-knn")
    output_dir = (
        _resolve_research_output_dir(args.output_dir, config=config, field_name="output_dir")
        if args.output_dir is not None
        else _research_output_root(config)
    )
    result = run_hmm_knn_research(
        config_path=Path(args.config),
        dataset_path=Path(args.dataset) if args.dataset is not None else None,
        output_dir=output_dir,
    )
    return {
        "output_dir": str(result.output_dir),
        "artifact_manifest_path": str(result.artifact_manifest_path),
        "metrics_path": str(result.metrics_path),
        "regime_posteriors_path": str(result.regime_posteriors_path),
        "knn_predictions_path": str(result.knn_predictions_path),
        "meta_predictions_path": str(result.meta_predictions_path),
        "neighbor_diagnostics_path": str(result.neighbor_diagnostics_path),
    }


def _run_hmm_knn_experiments_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("run-hmm-knn-experiments")
    output_dir = (
        _resolve_research_output_dir(args.output_dir, config=config, field_name="output_dir")
        if args.output_dir is not None
        else _default_research_output_dir(config, "hmm_knn_experiments")
    )
    result = run_hmm_knn_experiment_matrix(
        spec_path=Path(args.spec),
        dataset_path=Path(args.dataset) if args.dataset is not None else None,
        output_dir=output_dir,
        cache_dir=Path(args.cache_dir) if args.cache_dir is not None else None,
        force=args.force,
        write_monitoring=not args.skip_monitor,
        fail_fast=args.fail_fast,
        max_workers=args.workers,
    )
    return {
        "output_dir": str(result.output_dir),
        "experiment_manifest_path": str(result.manifest_path),
        "summary_path": str(result.summary_path),
    }


def _run_build_four_bar_knn_dataset_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("build-four-bar-knn-dataset")
    output_dir = (
        _resolve_research_output_dir(args.output_dir, config=config, field_name="output_dir")
        if args.output_dir is not None
        else _default_research_output_dir(config, "hmm_knn_four_bar")
    )
    result = build_four_bar_knn_dataset_from_fixture(
        fixture_root=_resolve_cli_path(args.fixture_root),
        output_dir=output_dir,
        symbol=args.symbol,
        base_intervals=tuple(args.base_interval or ["15m", "1h"]),
        dataset_name=args.dataset_name,
        max_rows_per_interval=args.max_rows_per_interval,
    )
    return result.to_payload()


def _run_four_bar_knn_larger_validation_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("run-four-bar-knn-larger-validation")
    output_dir = (
        _resolve_research_output_dir(args.output_dir, config=config, field_name="output_dir")
        if args.output_dir is not None
        else _default_research_output_dir(config, "hmm_knn_four_bar_validation", "wpr106_77_larger_validation_r106_v1")
    )
    result = run_four_bar_knn_larger_validation(
        output_dir=output_dir,
        btc_fixture_root=_resolve_cli_path(args.btc_fixture_root) if args.btc_fixture_root is not None else None,
        eth_fixture_root=_resolve_cli_path(args.eth_fixture_root) if args.eth_fixture_root is not None else None,
        sample_rows_per_interval=args.sample_rows_per_interval,
        workers=args.workers,
        force=args.force,
        write_monitoring=not args.skip_monitor,
        skip_matrix=args.skip_matrix,
    )
    return result.to_payload()


def _run_map_binance_archive_four_bar_datasets_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("map-binance-archive-four-bar-datasets")
    output_dir = (
        _resolve_research_output_dir(args.output_dir, config=config, field_name="output_dir")
        if args.output_dir is not None
        else _default_research_output_dir(config, "hmm_knn_four_bar_archive_mapping", "wpr106_79_local_archive_mapping")
    )
    result = map_local_binance_archive_four_bar_datasets(
        output_dir=output_dir,
        archive_root=_resolve_cli_path(args.archive_root) if args.archive_root is not None else None,
        start_month=args.start_month,
        end_month=args.end_month,
        sample_rows_per_interval=args.sample_rows_per_interval,
        matrix_workers=args.matrix_workers,
        force=args.force,
    )
    return result.to_payload()


def _run_write_hmm_knn_sweep_datasets_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("write-hmm-knn-sweep-datasets")
    output_dir = (
        _resolve_research_output_dir(args.output_dir, config=config, field_name="output_dir")
        if args.output_dir is not None
        else _default_research_output_dir(config, "deterministic_sweeps")
    )
    variants = DETERMINISTIC_SWEEP_VARIANTS if args.variant == "all" else (args.variant,)
    results = write_hmm_knn_sweep_datasets(
        output_dir=output_dir,
        row_count=args.row_count,
        variants=variants,
    )
    return {
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
    }


def _run_collect_binance_bars_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("collect-binance-bars")
    result = asyncio.run(
        collect_binance_usdm_bars(
            symbol=args.symbol,
            interval=args.interval,
            start_time_ms=args.start_time_ms,
            end_time_ms=args.end_time_ms,
            output_dir=_resolve_optional_research_output_dir(args.output_dir, config=config),
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
    config = _config_for_command("collect-binance-context")
    result = asyncio.run(
        collect_binance_usdm_context(
            symbol=args.symbol,
            data_family=args.data_family,
            start_time_ms=args.start_time_ms,
            end_time_ms=args.end_time_ms,
            interval=args.interval,
            output_dir=_resolve_optional_research_output_dir(args.output_dir, config=config),
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
    config = _config_for_command("fetch-binance-vision")
    output_dir = _resolve_optional_research_output_dir(args.output_dir, config=config)
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
    config = _config_for_command("fetch-crypto-lake")
    output_dir = _resolve_optional_research_output_dir(args.output_dir, config=config)
    if args.path is not None:
        result = ingest_crypto_lake_archive(
            Path(args.path),
            symbol=args.symbol,
            data_family=args.data_family,
            output_dir=output_dir,
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
            output_dir=output_dir,
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
    config = _config_for_command("build-historical-fixture-pack")
    result = build_provider_kline_fixture_pack(
        source_manifest_path=Path(args.source_manifest),
        output_dir=_resolve_research_output_dir(args.output_dir, config=config, field_name="output_dir"),
        fixture_id=args.fixture_id,
        row_limit=args.row_limit,
        slice_mode=args.slice_mode,
        context_manifest_paths=[Path(path) for path in getattr(args, "context_manifest", [])],
    )
    return result.to_payload()


def _run_collect_durable_data_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("collect-durable-data")
    default_output = _default_research_output_dir(
        config,
        "operator_runs",
        "durable_data",
        "cli-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"),
    )
    result = collect_candidate_depth_public_archive_fixtures(
        output_dir=_resolve_optional_research_output_dir(args.output_dir, config=config) or default_output,
        symbols=args.symbol or ["BTCUSDT", "ETHUSDT"],
        start_month=args.start_month,
        end_month=args.end_month,
        repo_root=Path(__file__).resolve().parents[2],
        download_cache_dir=_default_research_output_dir(config, "historical_data_cache", "binance_vision_public_archive", "downloads"),
    )
    return result.to_payload()


def _run_refresh_historical_data_catalog_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("refresh-historical-data-catalog")
    default_output = _default_research_output_dir(
        config,
        "operator_runs",
        "historical_data",
        "cli-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"),
    )
    result = refresh_historical_data_catalog(
        output_dir=_resolve_optional_research_output_dir(args.output_dir, config=config) or default_output,
        symbols=args.symbol or ["BTCUSDT", "ETHUSDT"],
        start_month=args.start_month,
        end_month=args.end_month or default_historical_catalog_end_month(),
        repo_root=Path(__file__).resolve().parents[2],
        download_cache_dir=_default_research_output_dir(config, "historical_data_cache", "binance_vision_public_archive", "downloads"),
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


def _run_rapid_strategy_sandbox_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("run-rapid-strategy-sandbox")
    output_dir = (
        _resolve_research_output_dir(args.output_dir, config=config, field_name="output_dir")
        if args.output_dir is not None
        else _default_research_output_dir(config, "rapid_strategy_sandbox")
    )
    spec = load_sandbox_run_spec(_resolve_cli_path(args.spec))
    strategies = load_strategy_catalog(_resolve_cli_path(args.strategy_catalog))
    venues = load_venue_archive_descriptors(_resolve_cli_path(args.venue_archives))

    result = run_sandbox_archive_sweep(
        spec=spec,
        strategies=strategies,
        venues=venues,
        output_root=output_dir,
        shared_market_data_path=_resolve_cli_path(args.market_data) if args.market_data is not None else None,
        min_request_score=args.min_request_score,
    )
    return {
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "sandbox_only": True,
        "candidate_evidence": False,
        "candidate_pack_eligible": False,
        "output_dir": str(result.artifacts.run_dir),
        "manifest_path": str(result.artifacts.manifest_path),
        "summary_parquet_path": str(result.artifacts.summary_parquet_path),
        "rankings_parquet_path": str(result.artifacts.rankings_parquet_path),
        "evidence_requests_json_path": str(result.artifacts.evidence_requests_json_path),
        "evidence_requests_parquet_path": str(result.artifacts.evidence_requests_parquet_path),
        "result_count": len(result.results),
        "screened_count": sum(1 for item in result.results if item.status == "screened"),
        "evidence_request_count": len(result.evidence_requests),
    }


def _run_summarize_rapid_strategy_sandbox_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("summarize-rapid-strategy-sandbox")
    run_dir = _resolve_research_output_dir(args.run_dir, config=config, field_name="run_dir")
    return summarize_sandbox_run(
        run_dir,
        top_n=args.top_n,
        write_report=not args.no_write_report,
    )


def _run_rapid_strategy_sandbox_suite_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("run-rapid-strategy-sandbox-suite")
    output_dir = (
        _resolve_research_output_dir(args.output_dir, config=config, field_name="output_dir")
        if args.output_dir is not None
        else _default_research_output_dir(config, "rapid_strategy_sandbox_suites")
    )
    suite = load_sandbox_suite_spec(_resolve_cli_path(args.suite))
    result = run_sandbox_suite(
        suite=suite,
        output_root=output_dir,
        top_n=args.top_n,
        max_workers=args.max_workers,
    )
    return {
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "sandbox_only": True,
        "candidate_evidence": False,
        "candidate_pack_eligible": False,
        "suite_id": suite.suite_id,
        "suite_dir": str(result.artifacts.suite_dir),
        "suite_manifest_path": str(result.artifacts.suite_manifest_path),
        "suite_index_json_path": str(result.artifacts.suite_index_json_path),
        "suite_index_parquet_path": str(result.artifacts.suite_index_parquet_path),
        "suite_evidence_requests_json_path": str(result.artifacts.suite_evidence_requests_json_path),
        "suite_evidence_requests_parquet_path": str(result.artifacts.suite_evidence_requests_parquet_path),
        "max_workers": args.max_workers,
        "case_count": len(result.case_results),
        "completed_case_count": sum(1 for row in result.index_rows if row.get("case_status") == "completed"),
        "skipped_case_count": sum(1 for row in result.index_rows if row.get("case_status") == "blocked_by_preflight"),
        "preflight_trial_estimate": sum(int(row.get("preflight_trial_estimate", 0) or 0) for row in result.index_rows),
        "preflight_runnable_trial_estimate": sum(
            int(row.get("preflight_runnable_trial_estimate", 0) or 0) for row in result.index_rows
        ),
        "preflight_blocked_trial_estimate": sum(
            int(row.get("preflight_blocked_trial_estimate", 0) or 0) for row in result.index_rows
        ),
        "result_count": sum(int(row.get("result_count", 0)) for row in result.index_rows),
        "screened_count": sum(int(row.get("screened_count", 0)) for row in result.index_rows),
        "evidence_request_count": len(result.evidence_requests),
    }


def _run_verify_rapid_strategy_sandbox_artifacts_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("verify-rapid-strategy-sandbox-artifacts")
    target = _resolve_research_output_dir(args.target, config=config, field_name="target")
    output_dir = (
        _resolve_research_output_dir(args.output_dir, config=config, field_name="output_dir")
        if args.output_dir is not None
        else None
    )
    return verify_sandbox_artifact_integrity(
        target,
        output_dir=output_dir,
        write_report=not args.no_write_report,
    )


def _run_summarize_rapid_strategy_sandbox_hypotheses_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("summarize-rapid-strategy-sandbox-hypotheses")
    if args.run_dir is not None:
        run_dir = _resolve_research_output_dir(args.run_dir, config=config, field_name="run_dir")
        return summarize_sandbox_hypotheses(
            run_dir,
            write_report=not args.no_write_report,
        )
    suite_dir = _resolve_research_output_dir(args.suite_dir, config=config, field_name="suite_dir")
    return summarize_sandbox_suite_hypotheses(
        suite_dir,
        write_report=not args.no_write_report,
    )


def _run_export_rapid_strategy_sandbox_validation_requests_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("export-rapid-strategy-sandbox-validation-requests")
    output_dir = (
        _resolve_research_output_dir(args.output_dir, config=config, field_name="output_dir")
        if args.output_dir is not None
        else None
    )
    if args.run_dir is not None:
        run_dir = _resolve_research_output_dir(args.run_dir, config=config, field_name="run_dir")
        return export_sandbox_validation_request_bundle(
            run_dir,
            output_dir=output_dir,
        )
    suite_dir = _resolve_research_output_dir(args.suite_dir, config=config, field_name="suite_dir")
    return export_sandbox_suite_validation_request_bundle(
        suite_dir,
        output_dir=output_dir,
    )


def _run_preflight_rapid_strategy_sandbox_validation_requests_command(
    args: argparse.Namespace,
) -> dict[str, object]:
    config = _config_for_command("preflight-rapid-strategy-sandbox-validation-requests")
    bundle_path = _resolve_research_output_dir(args.bundle, config=config, field_name="bundle")
    output_dir = (
        _resolve_research_output_dir(args.output_dir, config=config, field_name="output_dir")
        if args.output_dir is not None
        else _default_research_output_dir(
            config,
            "rapid_strategy_sandbox_strict_validation_preflights",
        )
    )
    return preflight_sandbox_strict_validation_descriptors(
        bundle_path,
        output_dir=output_dir,
    )


def _run_export_rapid_strategy_sandbox_venue_expansion_requests_command(
    args: argparse.Namespace,
) -> dict[str, object]:
    config = _config_for_command("export-rapid-strategy-sandbox-venue-expansion-requests")
    catalog_path = _resolve_research_output_dir(
        args.catalog,
        config=config,
        field_name="catalog",
    )
    worklist_path = (
        _resolve_research_output_dir(args.worklist, config=config, field_name="worklist")
        if args.worklist is not None
        else None
    )
    output_dir = (
        _resolve_research_output_dir(args.output_dir, config=config, field_name="output_dir")
        if args.output_dir is not None
        else None
    )
    return export_sandbox_venue_expansion_request_bundle(
        catalog_path,
        worklist_path=worklist_path,
        output_dir=output_dir,
    )


def _run_materialize_rapid_strategy_sandbox_venue_expansion_requests_command(
    args: argparse.Namespace,
) -> dict[str, object]:
    config = _config_for_command("materialize-rapid-strategy-sandbox-venue-expansion-requests")
    request_bundle_path = _resolve_research_output_dir(
        args.request_bundle,
        config=config,
        field_name="request_bundle",
    )
    output_dir = (
        _resolve_research_output_dir(args.output_dir, config=config, field_name="output_dir")
        if args.output_dir is not None
        else _default_research_output_dir(
            config,
            "rapid_strategy_sandbox_venue_expansion_materializer",
        )
    )
    return materialize_sandbox_venue_expansion_requests(
        request_bundle_path,
        [_resolve_cli_path(path) for path in args.archive_root],
        output_dir=output_dir,
        venue=args.venue,
        symbol=args.symbol,
        data_family=args.data_family,
        interval=args.interval,
        max_files=args.max_files,
    )


def _run_export_rapid_strategy_sandbox_venue_expansion_candidate_manifest_command(
    args: argparse.Namespace,
) -> dict[str, object]:
    config = _config_for_command("export-rapid-strategy-sandbox-venue-expansion-candidate-manifest")
    descriptor_candidates_path = _resolve_research_output_dir(
        args.descriptor_candidates,
        config=config,
        field_name="descriptor_candidates",
    )
    output_dir = (
        _resolve_research_output_dir(args.output_dir, config=config, field_name="output_dir")
        if args.output_dir is not None
        else _default_research_output_dir(
            config,
            "rapid_strategy_sandbox_venue_expansion_candidate_manifests",
        )
    )
    return export_sandbox_venue_expansion_candidate_manifest(
        descriptor_candidates_path,
        output_dir=output_dir,
    )


def _run_index_rapid_strategy_sandbox_artifacts_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("index-rapid-strategy-sandbox-artifacts")
    root_dir = (
        _resolve_research_output_dir(args.root_dir, config=config, field_name="root_dir")
        if args.root_dir is not None
        else _research_output_root(config)
    )
    output_dir = (
        _resolve_research_output_dir(args.output_dir, config=config, field_name="output_dir")
        if args.output_dir is not None
        else None
    )
    return index_sandbox_artifacts(
        root_dir,
        output_dir=output_dir,
        max_files=args.max_files,
        write_report=not args.no_write_report,
    )


def _run_index_rapid_strategy_sandbox_iterations_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("index-rapid-strategy-sandbox-iterations")
    root_dir = (
        _resolve_research_output_dir(args.root_dir, config=config, field_name="root_dir")
        if args.root_dir is not None
        else _research_output_root(config)
    )
    output_dir = (
        _resolve_research_output_dir(args.output_dir, config=config, field_name="output_dir")
        if args.output_dir is not None
        else None
    )
    return build_sandbox_iteration_index(
        root_dir,
        output_dir=output_dir,
        max_files=args.max_files,
        write_report=not args.no_write_report,
    )


def _run_show_rapid_strategy_sandbox_next_action_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("show-rapid-strategy-sandbox-next-action")
    output_root = (
        _resolve_research_output_dir(args.output_root, config=config, field_name="output_root")
        if args.output_root is not None
        else _research_output_root(config)
    )
    artifact_catalog_paths = [
        _resolve_research_output_dir(path, config=config, field_name="artifact_catalog")
        for path in (args.artifact_catalog or [])
    ] or None
    iteration_index_paths = [
        _resolve_research_output_dir(path, config=config, field_name="iteration_index")
        for path in (args.iteration_index or [])
    ] or None
    output_dir = (
        _resolve_research_output_dir(args.output_dir, config=config, field_name="output_dir")
        if args.output_dir is not None
        else None
    )
    return show_sandbox_next_action(
        output_root,
        artifact_catalog_paths=artifact_catalog_paths,
        iteration_index_paths=iteration_index_paths,
        output_dir=output_dir,
        max_files=args.max_files,
        limit=args.limit,
        write_report=not args.no_write_report,
    )


def _run_summarize_rapid_strategy_sandbox_throughput_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("summarize-rapid-strategy-sandbox-throughput")
    root_dir = (
        _resolve_research_output_dir(args.root_dir, config=config, field_name="root_dir")
        if args.root_dir is not None
        else _research_output_root(config)
    )
    output_dir = (
        _resolve_research_output_dir(args.output_dir, config=config, field_name="output_dir")
        if args.output_dir is not None
        else None
    )
    return summarize_sandbox_throughput(
        root_dir,
        output_dir=output_dir,
        containment_root=_research_output_root(config),
        max_files=args.max_files,
        limit=args.limit,
        write_report=not args.no_write_report,
    )


def _run_audit_rapid_strategy_sandbox_archives_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("audit-rapid-strategy-sandbox-archives")
    output_dir = (
        _resolve_research_output_dir(args.output_dir, config=config, field_name="output_dir")
        if args.output_dir is not None
        else _default_research_output_dir(config, "rapid_strategy_sandbox_archive_audits")
    )
    return audit_sandbox_archive_descriptors(
        _resolve_cli_path(args.venue_archives),
        output_dir=output_dir,
        shared_market_data_path=_resolve_cli_path(args.market_data) if args.market_data is not None else None,
        requested_window=_optional_sandbox_requested_window(
            getattr(args, "requested_window_start", None),
            getattr(args, "requested_window_end", None),
        ),
    )


def _run_summarize_rapid_strategy_sandbox_archive_coverage_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("summarize-rapid-strategy-sandbox-archive-coverage")
    output_dir = (
        _resolve_research_output_dir(args.output_dir, config=config, field_name="output_dir")
        if args.output_dir is not None
        else _default_research_output_dir(config, "rapid_strategy_sandbox_archive_coverage")
    )
    return summarize_sandbox_archive_coverage(
        _resolve_cli_path(args.venue_archives),
        output_dir=output_dir,
        shared_market_data_path=_resolve_cli_path(args.market_data) if args.market_data is not None else None,
        requested_window=_optional_sandbox_requested_window(
            getattr(args, "requested_window_start", None),
            getattr(args, "requested_window_end", None),
        ),
    )


def _run_build_rapid_strategy_sandbox_archive_manifest_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("build-rapid-strategy-sandbox-archive-manifest")
    output_dir = (
        _resolve_research_output_dir(args.output_dir, config=config, field_name="output_dir")
        if args.output_dir is not None
        else _default_research_output_dir(config, "rapid_strategy_sandbox_archive_manifests")
    )
    return build_sandbox_archive_manifest(
        [_resolve_cli_path(path) for path in args.archive_root],
        output_dir=output_dir,
        venue=args.venue,
        symbol=args.symbol,
        data_family=args.data_family,
        interval=args.interval,
        max_files=args.max_files,
    )


def _run_rank_rapid_strategy_sandbox_artifacts_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("rank-rapid-strategy-sandbox-artifacts")
    root_dir = (
        _resolve_research_output_dir(args.root_dir, config=config, field_name="root_dir")
        if args.root_dir is not None
        else _research_output_root(config)
    )
    output_dir = (
        _resolve_research_output_dir(args.output_dir, config=config, field_name="output_dir")
        if args.output_dir is not None
        else None
    )
    return build_sandbox_global_leaderboard(
        root_dir,
        output_dir=output_dir,
        max_runs=args.max_runs,
        top_n=args.top_n,
        write_report=not args.no_write_report,
    )


def _run_build_rapid_strategy_sandbox_strategy_catalog_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("build-rapid-strategy-sandbox-strategy-catalog")
    output_dir = (
        _resolve_research_output_dir(args.output_dir, config=config, field_name="output_dir")
        if args.output_dir is not None
        else _default_research_output_dir(config, "rapid_strategy_sandbox_strategy_catalogs")
    )
    return materialize_sandbox_strategy_catalog(
        [_resolve_cli_path(path) for path in args.catalog_root],
        output_dir=output_dir,
        max_files=args.max_files,
    )


def _run_preflight_rapid_strategy_sandbox_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("preflight-rapid-strategy-sandbox")
    output_dir = (
        _resolve_research_output_dir(args.output_dir, config=config, field_name="output_dir")
        if args.output_dir is not None
        else _default_research_output_dir(config, "rapid_strategy_sandbox_preflights")
    )
    return preflight_sandbox_compatibility(
        spec=load_sandbox_run_spec(_resolve_cli_path(args.spec)),
        strategies=load_strategy_catalog(_resolve_cli_path(args.strategy_catalog)),
        venues=load_venue_archive_descriptors(_resolve_cli_path(args.venue_archives)),
        output_dir=output_dir,
        shared_market_data_path=_resolve_cli_path(args.market_data) if args.market_data is not None else None,
    )


def _parse_holding_periods(value: str) -> tuple[int, ...]:
    periods = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    if not periods:
        raise ValueError("holding_periods must include at least one positive integer")
    if any(period <= 0 for period in periods):
        raise ValueError("holding_periods must include only positive integers")
    return periods


def _run_rapid_strategy_sandbox_iteration_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("run-rapid-strategy-sandbox-iteration")
    output_dir = (
        _resolve_research_output_dir(args.output_dir, config=config, field_name="output_dir")
        if args.output_dir is not None
        else _default_research_output_dir(config, "rapid_strategy_sandbox_iterations")
    )
    return run_sandbox_agent_iteration(
        output_dir=output_dir,
        spec_path=_resolve_cli_path(args.spec) if args.spec is not None else None,
        strategy_catalog_path=_resolve_cli_path(args.strategy_catalog) if args.strategy_catalog is not None else None,
        catalog_roots=[_resolve_cli_path(path) for path in args.catalog_root] if args.catalog_root else None,
        venue_archives_path=_resolve_cli_path(args.venue_archives) if args.venue_archives is not None else None,
        archive_roots=[_resolve_cli_path(path) for path in args.archive_root] if args.archive_root else None,
        run_id=args.run_id,
        window_start=args.window_start,
        window_end=args.window_end,
        window_preset=getattr(args, "window_preset", "explicit"),
        window_as_of_date=getattr(args, "window_as_of_date", None),
        window_lookback_days=getattr(args, "window_lookback_days", 365),
        holding_periods=_parse_holding_periods(args.holding_periods),
        round_trip_cost_bps=args.round_trip_cost_bps,
        min_trades=args.min_trades,
        max_evidence_requests=args.max_evidence_requests,
        rank_top_n=args.rank_top_n,
        min_request_score=args.min_request_score,
        catalog_max_files=args.catalog_max_files,
        archive_max_files=args.archive_max_files,
        archive_venue=args.archive_venue,
        archive_symbol=args.archive_symbol,
        archive_data_family=args.archive_data_family,
        archive_interval=args.archive_interval,
        leaderboard_max_runs=args.leaderboard_max_runs,
        leaderboard_top_n=args.leaderboard_top_n,
    )


def _run_benchmark_research_experiment_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("benchmark-research-experiment")
    report_path = write_research_experiment_benchmark_report(
        spec_path=Path(args.spec),
        output_dir=_resolve_optional_research_output_dir(args.output_dir, config=config),
        repeat=args.repeat,
        app_config=config,
    )
    return {"benchmark_report_path": str(report_path)}


def _run_historical_research_cycle_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("run-historical-research-cycle")
    result = run_historical_research_cycle(
        spec_path=_resolve_cli_path(args.spec),
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
        output_dir=_resolve_optional_research_output_dir(args.output_dir, config=config),
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


def _run_benchmark_discovery_command(args: argparse.Namespace) -> dict[str, object]:
    import json

    config = _config_for_command("benchmark-discovery-run")
    result = write_discovery_benchmark_report(
        output_dir=_resolve_optional_research_output_dir(args.output_dir, config=config),
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
        raise ValueError(f"benchmark_discovery_run_gate_failed:{detail}")
    return payload


def _run_benchmark_hardware_utilization_command(args: argparse.Namespace) -> dict[str, object]:
    import json

    config = _config_for_command("benchmark-hardware-utilization")
    result = write_hardware_utilization_report(
        output_dir=_resolve_optional_research_output_dir(args.output_dir, config=config),
        cpu_workers=getattr(args, "cpu_workers", None),
        cpu_seconds=float(getattr(args, "cpu_seconds", 3.0)),
        gpu_seconds=float(getattr(args, "gpu_seconds", 3.0)),
        matrix_size=int(getattr(args, "matrix_size", 1024)),
        app_config=config,
    )
    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    cpu_probe = dict(report.get("cpu_probe") or {})
    gpu_probe = dict(report.get("gpu_probe") or {})
    return {
        "output_dir": str(result.output_dir),
        "hardware_utilization_report_path": str(result.report_path),
        "cpu_probe_succeeded": bool(cpu_probe.get("probe_succeeded", False)),
        "gpu_probe_succeeded": bool(gpu_probe.get("probe_succeeded", False)),
        "cpu_worker_capacity_percent": cpu_probe.get("process_cpu_percent_of_worker_capacity"),
        "cpu_logical_capacity_percent": cpu_probe.get("process_cpu_percent_of_logical_capacity"),
        "gpu_execution_status": gpu_probe.get("gpu_execution_status"),
        "recommended_best_option": (report.get("recommendations") or {}).get("best_option"),
    }


def _run_discovery_candidate_pack_bridge_command(args: argparse.Namespace) -> dict[str, object]:
    import json

    config = _config_for_command("evaluate-discovery-candidate-pack-eligibility")
    candidate_id_map = json.loads(args.candidate_id_map_json) if args.candidate_id_map_json else {}
    if not isinstance(candidate_id_map, dict):
        raise ValueError("candidate-id-map-json must be a JSON object")
    result = evaluate_discovery_candidate_pack_eligibility(
        discovery_manifest_path=_resolve_cli_path(args.discovery_manifest),
        cycle_manifest_path=_resolve_cli_path(args.cycle_manifest) if args.cycle_manifest is not None else None,
        exit_lab_manifest_path=(
            _resolve_cli_path(getattr(args, "exit_lab_manifest", None))
            if getattr(args, "exit_lab_manifest", None) is not None
            else None
        ),
        multiple_testing_manifest_path=(
            _resolve_cli_path(getattr(args, "multiple_testing_manifest", None))
            if getattr(args, "multiple_testing_manifest", None) is not None
            else None
        ),
        validation_floors_manifest_path=(
            _resolve_cli_path(getattr(args, "validation_floors_manifest", None))
            if getattr(args, "validation_floors_manifest", None) is not None
            else None
        ),
        candidate_id_map={str(key): str(value) for key, value in candidate_id_map.items()},
    )
    output_dir = (
        _resolve_research_output_dir(args.output_dir, config=config, field_name="output_dir")
        if args.output_dir is not None
        else _default_discovery_bridge_output_dir(config, result)
    )
    artifact = write_discovery_candidate_pack_eligibility(output_dir=output_dir, result=result)
    manifest = json.loads(artifact.manifest_path.read_text(encoding="utf-8"))
    summary = dict(manifest.get("summary") or {})
    return {
        "output_dir": str(artifact.output_dir),
        "bridge_manifest_path": str(artifact.manifest_path),
        "eligibility_path": str(artifact.eligibility_path),
        "rejections_path": str(artifact.rejections_path),
        "candidate_count": int(summary.get("candidate_count") or 0),
        "eligible_count": int(summary.get("eligible_count") or 0),
        "blocked_count": int(summary.get("blocked_count") or 0),
        "global_reasons": list(manifest.get("global_reasons") or []),
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
        "promotion_ready": False,
    }


def _run_plan_feature_ablation_command(args: argparse.Namespace) -> dict[str, object]:
    config = _config_for_command("plan-feature-ablation")
    result = write_feature_ablation_plan(
        output_dir=(
            _resolve_research_output_dir(args.output_dir, config=config, field_name="output_dir")
            if args.output_dir is not None
            else _default_research_output_dir(config, "stage12", "feature_ablation")
        ),
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
        output_dir=(
            _resolve_research_output_dir(args.output_dir, config=config, field_name="output_dir")
            if args.output_dir is not None
            else _default_research_output_dir(config, "stage12")
        ),
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
        output_dir=(
            _resolve_research_output_dir(args.output_dir, config=config, field_name="output_dir")
            if args.output_dir is not None
            else _default_research_output_dir(config, "stage13", "readiness")
        ),
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

        print(json.dumps(_run_research_hmm_knn_command(args), indent=2))
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

        print(json.dumps(_run_hmm_knn_experiments_command(args), indent=2))
    elif args.command == "build-four-bar-knn-dataset":
        import json

        print(json.dumps(_run_build_four_bar_knn_dataset_command(args), indent=2))
    elif args.command == "run-four-bar-knn-larger-validation":
        import json

        print(json.dumps(_run_four_bar_knn_larger_validation_command(args), indent=2))
    elif args.command == "map-binance-archive-four-bar-datasets":
        import json

        print(json.dumps(_run_map_binance_archive_four_bar_datasets_command(args), indent=2))
    elif args.command == "write-hmm-knn-sweep-datasets":
        import json

        print(json.dumps(_run_write_hmm_knn_sweep_datasets_command(args), indent=2))
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
    elif args.command == "collect-durable-data":
        import json

        print(json.dumps(_run_collect_durable_data_command(args), indent=2))
    elif args.command == "refresh-historical-data-catalog":
        import json

        print(json.dumps(_run_refresh_historical_data_catalog_command(args), indent=2))
    elif args.command == "run-research-experiment":
        import json

        print(json.dumps(_run_research_experiment_command(args), indent=2))
    elif args.command == "run-rapid-strategy-sandbox":
        import json

        print(json.dumps(_run_rapid_strategy_sandbox_command(args), indent=2))
    elif args.command == "summarize-rapid-strategy-sandbox":
        import json

        print(json.dumps(_run_summarize_rapid_strategy_sandbox_command(args), indent=2))
    elif args.command == "run-rapid-strategy-sandbox-suite":
        import json

        print(json.dumps(_run_rapid_strategy_sandbox_suite_command(args), indent=2))
    elif args.command == "verify-rapid-strategy-sandbox-artifacts":
        import json

        print(json.dumps(_run_verify_rapid_strategy_sandbox_artifacts_command(args), indent=2))
    elif args.command == "summarize-rapid-strategy-sandbox-hypotheses":
        import json

        print(json.dumps(_run_summarize_rapid_strategy_sandbox_hypotheses_command(args), indent=2))
    elif args.command == "export-rapid-strategy-sandbox-validation-requests":
        import json

        print(json.dumps(_run_export_rapid_strategy_sandbox_validation_requests_command(args), indent=2))
    elif args.command == "preflight-rapid-strategy-sandbox-validation-requests":
        import json

        print(json.dumps(_run_preflight_rapid_strategy_sandbox_validation_requests_command(args), indent=2))
    elif args.command == "export-rapid-strategy-sandbox-venue-expansion-requests":
        import json

        print(json.dumps(_run_export_rapid_strategy_sandbox_venue_expansion_requests_command(args), indent=2))
    elif args.command == "materialize-rapid-strategy-sandbox-venue-expansion-requests":
        import json

        print(json.dumps(_run_materialize_rapid_strategy_sandbox_venue_expansion_requests_command(args), indent=2))
    elif args.command == "export-rapid-strategy-sandbox-venue-expansion-candidate-manifest":
        import json

        print(json.dumps(_run_export_rapid_strategy_sandbox_venue_expansion_candidate_manifest_command(args), indent=2))
    elif args.command == "index-rapid-strategy-sandbox-artifacts":
        import json

        print(json.dumps(_run_index_rapid_strategy_sandbox_artifacts_command(args), indent=2))
    elif args.command == "index-rapid-strategy-sandbox-iterations":
        import json

        print(json.dumps(_run_index_rapid_strategy_sandbox_iterations_command(args), indent=2))
    elif args.command == "show-rapid-strategy-sandbox-next-action":
        import json

        print(json.dumps(_run_show_rapid_strategy_sandbox_next_action_command(args), indent=2))
    elif args.command == "summarize-rapid-strategy-sandbox-throughput":
        import json

        print(json.dumps(_run_summarize_rapid_strategy_sandbox_throughput_command(args), indent=2))
    elif args.command == "audit-rapid-strategy-sandbox-archives":
        import json

        print(json.dumps(_run_audit_rapid_strategy_sandbox_archives_command(args), indent=2))
    elif args.command == "summarize-rapid-strategy-sandbox-archive-coverage":
        import json

        print(json.dumps(_run_summarize_rapid_strategy_sandbox_archive_coverage_command(args), indent=2))
    elif args.command == "build-rapid-strategy-sandbox-archive-manifest":
        import json

        print(json.dumps(_run_build_rapid_strategy_sandbox_archive_manifest_command(args), indent=2))
    elif args.command == "rank-rapid-strategy-sandbox-artifacts":
        import json

        print(json.dumps(_run_rank_rapid_strategy_sandbox_artifacts_command(args), indent=2))
    elif args.command == "build-rapid-strategy-sandbox-strategy-catalog":
        import json

        print(json.dumps(_run_build_rapid_strategy_sandbox_strategy_catalog_command(args), indent=2))
    elif args.command == "preflight-rapid-strategy-sandbox":
        import json

        print(json.dumps(_run_preflight_rapid_strategy_sandbox_command(args), indent=2))
    elif args.command == "run-rapid-strategy-sandbox-iteration":
        import json

        print(json.dumps(_run_rapid_strategy_sandbox_iteration_command(args), indent=2))
    elif args.command == "benchmark-research-experiment":
        import json

        print(json.dumps(_run_benchmark_research_experiment_command(args), indent=2))
    elif args.command == "run-historical-research-cycle":
        import json

        print(json.dumps(_run_historical_research_cycle_command(args), indent=2))
    elif args.command == "benchmark-historical-research-cycle":
        import json

        print(json.dumps(_run_benchmark_historical_research_cycle_command(args), indent=2))
    elif args.command == "benchmark-discovery-run":
        import json

        print(json.dumps(_run_benchmark_discovery_command(args), indent=2))
    elif args.command == "benchmark-hardware-utilization":
        import json

        print(json.dumps(_run_benchmark_hardware_utilization_command(args), indent=2))
    elif args.command == "evaluate-discovery-candidate-pack-eligibility":
        import json

        print(json.dumps(_run_discovery_candidate_pack_bridge_command(args), indent=2))
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
