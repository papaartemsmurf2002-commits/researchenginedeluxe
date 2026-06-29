# V2-AUDIT-ID: V2-AUD-PKG-001
# V2-CONTRACTS: docs/PRODUCT_SCOPE.md
# V2-BOUNDARY: research_only, no_live_imports, no_order_or_sizing
# V2-OWNER: v2_cli
"""Minimal v2 CLI entrypoint for Phase 1 smoke validation."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import date, datetime, timedelta
from pathlib import Path

import pyarrow.parquet as pq
from pydantic import ValidationError

from tradingbotsuite.v2.audit import (
    AutonomousReadinessStatus,
    run_autonomous_readiness_audit_from_file,
)
from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.archive.manifest_store import ArchiveManifestStore
from tradingbotsuite.v2.archive.rebuild import (
    bronze_asset_contexts_to_silver,
    bronze_candles_to_silver_bars,
    bronze_funding_to_silver,
    create_silver_market_data_snapshot,
    raw_asset_contexts_to_bronze,
    raw_candles_to_bronze,
    raw_funding_to_bronze,
)
from tradingbotsuite.v2.archive.schemas import ArchiveLayer
from tradingbotsuite.v2.archive.snapshots import create_archive_snapshot
from tradingbotsuite.v2.archive_inventory import (
    ArchiveInventoryService,
    ArtifactMode,
    CentralArchiveSnapshotBridgeConfig,
    CentralArchiveSnapshotBridgeError,
    DataGapRequest,
    StrategyDataRequirementRequest,
    build_central_archive_snapshot_bridge,
)
from tradingbotsuite.v2.autonomy import (
    AutopilotArchiveCycleConfig,
    AutopilotCyclePlanError,
    AutopilotCycleRunnerError,
    AutopilotFixtureCycleConfig,
    AutopilotPublicCandleCycleConfig,
    AutopilotSchedulerError,
    StrategyQueueScanConfig,
    agent_context_to_json,
    build_autonomous_research_agent_context,
    load_autopilot_cycle_spec,
    plan_autopilot_research_cycle,
    run_autopilot_cycle_plan,
    run_autopilot_scheduler_tick,
    AutonomyDryRunConfig,
    AutonomyLoopError,
    run_autonomy_dry_run,
    scan_strategy_queue,
    write_autonomous_research_agent_context,
    write_autopilot_archive_cycle_spec,
    write_autopilot_fixture_cycle_spec,
    write_autopilot_public_candle_cycle_spec,
)
from tradingbotsuite.v2.backtest_data import (
    BacktestDataError,
    BacktestDataRequest,
    BacktestDataService,
    BacktestEvidenceMode,
)
from tradingbotsuite.v2.backtest_engine import (
    BacktestBenchmarkConfig,
    BenchmarkTier,
    RunManifest,
    audit_fast_lane_parity,
    build_full_artifact_replay_plan,
    build_reference_rerun_plan,
    run_archive_backtest_benchmark,
    select_reference_audit_sample,
    verify_full_artifact_replay,
)
from tradingbotsuite.v2.config.schemas import (
    BOUNDED_CONTEXTS,
    RESEARCH_BOUNDARY,
    V2_SCHEMA_VERSION,
)
from tradingbotsuite.v2.costs.models import CostModelConfig
from tradingbotsuite.v2.collectors.historical_dataset import (
    DEFAULT_MAX_INSTRUMENTS,
    HistoricalPerpDatasetConfig,
    collect_historical_perp_dataset,
)
from tradingbotsuite.v2.collectors.templates import collector_template_from_gap_request
from tradingbotsuite.v2.data_quality.checks import build_quality_checks
from tradingbotsuite.v2.data_quality.coverage import coverage_report_for_bars
from tradingbotsuite.v2.data_quality.reports import CoverageManifestStore
from tradingbotsuite.v2.data_quality.schemas import DEFAULT_COVERAGE_MIN, EvidenceMode
from tradingbotsuite.v2.feature_store import FeatureStoreCatalogService
from tradingbotsuite.v2.ledger import (
    LedgerAppendRequest,
    LedgerError,
    append_run_to_ledger,
    compact_ledger_parts,
    export_ledger,
    leaderboard,
)
from tradingbotsuite.v2.lead_book import (
    LeadBookError,
    LeadBookScanConfig,
    LeadBookStore,
    LeadState,
    approve_after_human_inspection,
    complete_human_inspection,
    create_lead_from_source,
    request_human_inspection,
    scan_lead_book_queue,
)
from tradingbotsuite.v2.strategy_specs import (
    example_strategy_payloads,
    load_strategy_spec_file,
    registry_summary,
    validate_strategy_spec,
)
from tradingbotsuite.v2.security.path_policy import resolve_within_root
from tradingbotsuite.v2.ui import snapshot_from_json, write_visibility_html
from tradingbotsuite.v2.universe.hyperliquid import (
    diff_snapshots,
    explain_instrument,
    refresh_hyperliquid_universe,
    select_asof_universe,
)
from tradingbotsuite.v2.universe.models import UniverseMode
from tradingbotsuite.v2.venues.hyperliquid import HyperliquidInfoClient
from tradingbotsuite.v2.workers.job_store import WorkerJobStore
from tradingbotsuite.v2.workers.models import WorkerJobKind, WorkerJobStatus
from tradingbotsuite.v2.workers.runner import run_one_job

BOUNDARY_HELP = (
    "Research-only v2 command shell. Non-live, non-paper, no order placement, "
    "no sizing instructions, no runtime mode changes, and no promotion output."
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="redx",
        description=BOUNDARY_HELP,
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="print the v2 schema version and exit",
    )
    parser.add_argument(
        "--show-boundary",
        action="store_true",
        help="print the research-only boundary invariant and exit",
    )
    parser.add_argument(
        "--list-contexts",
        action="store_true",
        help="list planned bounded contexts without running any jobs",
    )
    subparsers = parser.add_subparsers(dest="command")
    archive = subparsers.add_parser(
        "archive",
        help="local archive commands; no venue fetches or live behavior",
        description=f"Archive command group. {BOUNDARY_HELP}",
    )
    archive_subparsers = archive.add_subparsers(dest="archive_command")
    archive_init = archive_subparsers.add_parser(
        "init",
        help="create the local archive directory tree safely",
    )
    archive_init.add_argument("--archive-root", required=True)
    archive_validate = archive_subparsers.add_parser(
        "validate",
        help="validate file_manifest rows against local files",
    )
    archive_validate.add_argument("--archive-root", required=True)
    archive_snapshot = archive_subparsers.add_parser(
        "snapshot",
        help="create a deterministic archive snapshot from manifest rows",
    )
    archive_snapshot.add_argument("--archive-root", required=True)
    archive_snapshot.add_argument("--layer", required=True, choices=["silver", "gold", "bronze"])
    archive_snapshot.add_argument("--venue-scope", required=True)
    archive_snapshot.add_argument("--start-ts", required=True)
    archive_snapshot.add_argument("--end-ts", required=True)
    archive_snapshot.add_argument("--lockbox-policy-id")
    archive_snapshot.add_argument("--notes")
    archive_bronze = archive_subparsers.add_parser(
        "build-bronze",
        help="parse a raw local archive file into a bronze market-data table",
    )
    archive_bronze.add_argument("--archive-root", required=True)
    archive_bronze.add_argument("--raw-file-id", required=True)
    archive_bronze.add_argument("--datatype", required=True, choices=["candles", "funding", "asset_contexts"])
    archive_bronze.add_argument("--job-id", required=True)
    archive_bronze.add_argument("--instrument-id")
    archive_bronze.add_argument("--timeframe")
    archive_silver = archive_subparsers.add_parser(
        "build-silver",
        help="normalize a bronze market-data file into silver market-data tables",
    )
    archive_silver.add_argument("--archive-root", required=True)
    archive_silver.add_argument("--bronze-file-id", required=True)
    archive_silver.add_argument("--datatype", required=True, choices=["candles", "funding", "asset_contexts"])
    archive_silver.add_argument("--job-id", required=True)
    archive_silver.add_argument("--derive-timeframes", default="5m,15m,1h")
    archive_silver.add_argument("--skip-coverage", action="store_true")
    archive_silver.add_argument("--snapshot", action="store_true")
    archive_market_snapshot = archive_subparsers.add_parser(
        "snapshot-silver-market-data",
        help="create a silver archive snapshot including coverage and quality manifests",
    )
    archive_market_snapshot.add_argument("--archive-root", required=True)
    archive_market_snapshot.add_argument("--venue-scope", required=True)
    archive_market_snapshot.add_argument("--start-ts", required=True)
    archive_market_snapshot.add_argument("--end-ts", required=True)
    archive_market_snapshot.add_argument("--notes")
    archive_inventory = subparsers.add_parser(
        "archive-inventory",
        help="read-only archive inventory and strategy data-gap resolver",
        description=f"Archive inventory command. {BOUNDARY_HELP}",
    )
    archive_inventory.add_argument("--repo-root", default=".")
    archive_inventory.add_argument("--archive-root", default="data/research/central_market_history")
    archive_inventory.add_argument("--summary", action="store_true")
    archive_inventory.add_argument("--symbol")
    archive_inventory.add_argument("--instrument-id", action="append", dest="instrument_ids", default=[])
    archive_inventory.add_argument("--venue")
    archive_inventory.add_argument("--family")
    archive_inventory.add_argument("--feature-catalog", action="store_true")
    archive_inventory.add_argument("--feature-family")
    archive_inventory.add_argument("--source-family")
    archive_inventory.add_argument("--evidence-scope")
    archive_inventory.add_argument("--coverage-report-id")
    archive_inventory.add_argument("--accepted-only", action="store_true")
    archive_inventory.add_argument("--timeframe")
    archive_inventory.add_argument("--start-ts")
    archive_inventory.add_argument("--end-ts")
    archive_inventory.add_argument(
        "--bridge-central-snapshot",
        action="store_true",
        help="build a read-only v2 snapshot bridge from existing central archive evidence",
    )
    archive_inventory.add_argument("--bridge-archive-root")
    archive_inventory.add_argument("--project-validation-report")
    archive_inventory.add_argument("--bridge-coverage-min", type=float, default=0.98)
    archive_inventory.add_argument("--replace-existing-bridge", action="store_true")
    archive_inventory.add_argument(
        "--missing-for-strategy",
        "--strategy-spec-file",
        dest="strategy_spec_file",
        help="strategy spec JSON/YAML to resolve against existing archive refs",
    )
    archive_inventory.add_argument(
        "--evidence-mode",
        choices=[mode.value for mode in BacktestEvidenceMode],
    )
    archive_inventory.add_argument(
        "--artifact-mode",
        default=ArtifactMode.FULL.value,
        choices=[mode.value for mode in ArtifactMode],
    )
    archive_inventory.add_argument("--prefer-fast-lane", action="store_true")
    archive_inventory.add_argument("--require-reference-audit", action="store_true")
    archive_inventory.add_argument("--asof-date")
    universe = subparsers.add_parser(
        "universe",
        help="local universe commands; fixture-backed by default for repeatability",
        description=f"Universe command group. {BOUNDARY_HELP}",
    )
    universe_subparsers = universe.add_subparsers(dest="universe_command")
    universe_refresh = universe_subparsers.add_parser(
        "refresh",
        help="write raw Hyperliquid metaAndAssetCtxs payload and create a universe snapshot",
    )
    universe_refresh.add_argument("--archive-root", required=True)
    universe_refresh.add_argument("--venue", default="hyperliquid", choices=["hyperliquid"])
    universe_refresh.add_argument("--min-day-notional-usd", type=int, default=5_000_000)
    universe_refresh.add_argument(
        "--source",
        choices=["payload_file", "public_api"],
        help="refresh source; omit only when --payload-file is supplied",
    )
    universe_refresh.add_argument("--payload-file")
    universe_refresh.add_argument("--public-info-url", default="https://api.hyperliquid.xyz/info")
    universe_refresh.add_argument("--public-info-timeout", type=float, default=20.0)
    universe_refresh.add_argument("--asof-date", required=True)
    universe_refresh.add_argument(
        "--mode",
        default=UniverseMode.AS_OF.value,
        choices=[mode.value for mode in UniverseMode],
    )
    universe_refresh.add_argument("--include-hip3-dexs", action="store_true")
    universe_list = universe_subparsers.add_parser(
        "list",
        help="list instruments from the latest as-of snapshot at or before a date",
    )
    universe_list.add_argument("--archive-root", required=True)
    universe_list.add_argument("--asof-date", required=True)
    universe_list.add_argument("--eligible-only", action="store_true")
    universe_list.add_argument(
        "--mode",
        default=UniverseMode.AS_OF.value,
        choices=[mode.value for mode in UniverseMode],
    )
    universe_explain = universe_subparsers.add_parser(
        "explain",
        help="show one instrument row from a universe snapshot",
    )
    universe_explain.add_argument("--archive-root", required=True)
    universe_explain.add_argument("--snapshot", required=True)
    universe_explain.add_argument("--instrument", required=True)
    universe_diff = universe_subparsers.add_parser(
        "diff",
        help="diff eligible instruments between two snapshot IDs",
    )
    universe_diff.add_argument("--archive-root", required=True)
    universe_diff.add_argument("--left", required=True)
    universe_diff.add_argument("--right", required=True)
    data = subparsers.add_parser(
        "data",
        help="local data-quality commands; no venue fetches or live behavior",
        description=f"Data quality command group. {BOUNDARY_HELP}",
    )
    data_subparsers = data.add_subparsers(dest="data_command")
    data_coverage = data_subparsers.add_parser(
        "coverage",
        help="calculate bar coverage for a local Parquet slice",
    )
    _add_data_quality_common_args(data_coverage)
    data_coverage.add_argument("--coverage-min", type=float, default=DEFAULT_COVERAGE_MIN)
    data_coverage.add_argument("--write-manifest", action="store_true")
    data_quality = data_subparsers.add_parser(
        "quality-report",
        help="run duplicate, stale, zero-volume, and outlier checks on a local Parquet slice",
    )
    _add_data_quality_common_args(data_quality)
    data_quality.add_argument("--write-manifest", action="store_true")
    collectors = subparsers.add_parser(
        "collectors",
        help="bounded research-only data collection commands",
        description=f"Collectors command group. {BOUNDARY_HELP}",
    )
    collectors_subparsers = collectors.add_subparsers(dest="collectors_command")
    gap_template = collectors_subparsers.add_parser(
        "gap-template",
        help="convert resolver DataGapRequest JSON into research-only collector templates",
    )
    gap_template.add_argument("--gap-request-file", required=True)
    gap_template.add_argument("--gap-request-id")
    gap_template.add_argument("--requested-family")
    gap_template.add_argument("--adapter-id")
    historical_perps = collectors_subparsers.add_parser(
        "historical-perps",
        help="collect historical Hyperliquid perp candles and validate coverage/Binance overlap",
    )
    historical_perps.add_argument("--output-root", required=True)
    historical_perps.add_argument("--archive-root")
    historical_perps.add_argument("--run-id", default="v2-historical-perp-dataset")
    historical_perps.add_argument("--start-ts", required=True)
    historical_perps.add_argument("--end-ts", required=True)
    historical_perps.add_argument("--timeframe", default="1d")
    historical_perps.add_argument("--asof-date", default=date.today().isoformat())
    historical_perps.add_argument("--min-day-notional-usd", type=int, default=5_000_000)
    historical_perps.add_argument(
        "--max-instruments",
        type=int,
        default=DEFAULT_MAX_INSTRUMENTS,
        help="top-liquidity current eligible instruments to collect; 0 means all selected instruments",
    )
    historical_perps.add_argument(
        "--coin",
        action="append",
        dest="coins",
        default=[],
        help="restrict to a Hyperliquid coin; repeat for multiple coins",
    )
    historical_perps.add_argument("--coverage-min", type=float, default=DEFAULT_COVERAGE_MIN)
    historical_perps.add_argument("--public-info-url", default="https://api.hyperliquid.xyz/info")
    historical_perps.add_argument("--public-info-timeout", type=float, default=20.0)
    historical_perps.add_argument("--max-public-info-pages", type=int, default=50)
    historical_perps.add_argument("--max-candles-per-public-page", type=int, default=5_000)
    historical_perps.add_argument(
        "--candle-source",
        choices=["public_api", "trusted_records"],
        default="public_api",
        help="candle source for historical-perps; trusted_records reads local Hyperliquid-native files",
    )
    historical_perps.add_argument("--trusted-candle-records-root")
    historical_perps.add_argument("--trusted-candle-records-template", default="{coin}_{timeframe}.jsonl")
    historical_perps.add_argument(
        "--trusted-candle-records-format",
        choices=["auto", "json", "jsonl", "ndjson"],
        default="auto",
    )
    historical_perps.add_argument("--max-candle-records-file-bytes", type=int, default=512 * 1024 * 1024)
    historical_perps.add_argument("--include-funding", action="store_true")
    historical_perps.add_argument("--max-funding-pages", type=int, default=100)
    historical_perps.add_argument("--include-hip3-dexs", action="store_true")
    historical_perps.add_argument("--no-binance-validation", action="store_true")
    historical_perps.add_argument("--binance-base-url", default="https://fapi.binance.com")
    historical_perps.add_argument("--binance-timeout", type=float, default=20.0)
    historical_perps.add_argument("--binance-close-diff-warn-bps", type=float, default=250.0)
    historical_perps.add_argument("--created-by-id", default="codex-manager-agent")
    backtest_data = subparsers.add_parser(
        "backtest-data",
        help="local archive-backed backtest data reads; no strategy execution",
        description=f"Backtest-data command group. {BOUNDARY_HELP}",
    )
    backtest_data_subparsers = backtest_data.add_subparsers(dest="backtest_data_command")
    backtest_load = backtest_data_subparsers.add_parser(
        "load-panel",
        help="load a gated local archive data panel and write a request manifest",
    )
    backtest_load.add_argument("--archive-root", required=True)
    backtest_load.add_argument("--archive-snapshot-id", required=True)
    backtest_load.add_argument("--universe-snapshot-id", required=True)
    backtest_load.add_argument("--venue", required=True)
    backtest_load.add_argument("--instrument-id", required=True)
    backtest_load.add_argument("--family", default="bars")
    backtest_load.add_argument("--timeframe", required=True)
    backtest_load.add_argument("--start-ts", required=True)
    backtest_load.add_argument("--end-ts", required=True)
    backtest_load.add_argument("--warmup-start-ts")
    backtest_load.add_argument(
        "--field",
        action="append",
        dest="fields",
        required=True,
        help="output field to load; repeat for multiple fields",
    )
    backtest_load.add_argument(
        "--evidence-mode",
        default=BacktestEvidenceMode.ACCEPTED_RESEARCH.value,
        choices=[mode.value for mode in BacktestEvidenceMode],
    )
    backtest_load.add_argument("--asof-date")
    backtest_load.add_argument("--include-lockbox", action="store_true")
    backtest_load.add_argument("--no-write-manifest", action="store_true")
    fast_lane = subparsers.add_parser(
        "fast-lane",
        help="fast-lane parity, sampled reference audit, and rerun planning tools",
        description=f"Fast-lane audit command group. {BOUNDARY_HELP}",
    )
    fast_lane_subparsers = fast_lane.add_subparsers(dest="fast_lane_command")
    fast_lane_parity = fast_lane_subparsers.add_parser(
        "parity-report",
        help="compare a reference manifest with a fast-vectorized manifest",
    )
    fast_lane_parity.add_argument("--reference-run", required=True, help="path to reference run_manifest.json")
    fast_lane_parity.add_argument("--fast-run", required=True, help="path to fast run_manifest.json")
    fast_lane_parity.add_argument("--tolerance-abs", type=float, default=1e-12)
    fast_lane_rerun = fast_lane_subparsers.add_parser(
        "reference-rerun-plan",
        help="build a full-artifact reference rerun plan for a fast result",
    )
    fast_lane_rerun.add_argument("--fast-run", required=True, help="path to fast run_manifest.json")
    fast_lane_rerun.add_argument("--reason", default="suspicious_fast_result_reference_audit")
    full_replay = fast_lane_subparsers.add_parser(
        "full-artifact-replay-plan",
        help="build a full-artifact replay plan for a summary or metrics-only run",
    )
    full_replay.add_argument("--run", required=True, help="path to summary/metrics-only run_manifest.json")
    full_replay.add_argument("--reason", default="artifact_light_full_replay")
    full_replay_verify = fast_lane_subparsers.add_parser(
        "verify-full-artifact-replay",
        help="verify a full replay run preserves a light run's spec/data/config identity",
    )
    full_replay_verify.add_argument("--source-run", required=True, help="path to summary/metrics-only run_manifest.json")
    full_replay_verify.add_argument("--full-run", required=True, help="path to full replay run_manifest.json")
    full_replay_verify.add_argument("--tolerance-abs", type=float, default=1e-12)
    fast_lane_sample = fast_lane_subparsers.add_parser(
        "sample-reference-audits",
        help="deterministically select fast run IDs for sampled reference audit",
    )
    fast_lane_sample.add_argument("--sample-rate", type=float, required=True)
    fast_lane_sample.add_argument("--seed", default="fast_lane_reference_authority_v1")
    fast_lane_sample.add_argument("--minimum-count", type=int, default=1)
    fast_lane_sample.add_argument("--run-id", action="append", dest="run_ids", default=[])
    fast_lane_benchmark = fast_lane_subparsers.add_parser(
        "benchmark-run",
        help="run an archive-backed reference/fast benchmark over the same strategy/data slice",
    )
    fast_lane_benchmark.add_argument("--benchmark-id", default="archive_fast_lane_benchmark")
    fast_lane_benchmark.add_argument(
        "--benchmark-tier",
        default=BenchmarkTier.SMOKE.value,
        choices=[tier.value for tier in BenchmarkTier],
    )
    fast_lane_benchmark.add_argument("--strategy-spec-file", required=True)
    fast_lane_benchmark.add_argument("--archive-root", required=True)
    fast_lane_benchmark.add_argument("--output-root", required=True)
    fast_lane_benchmark.add_argument("--report-path")
    fast_lane_benchmark.add_argument("--archive-snapshot-id", required=True)
    fast_lane_benchmark.add_argument("--universe-snapshot-id", required=True)
    fast_lane_benchmark.add_argument("--venue", required=True)
    fast_lane_benchmark.add_argument("--instrument-id", action="append", dest="benchmark_instrument_ids", required=True)
    fast_lane_benchmark.add_argument("--family", default="bars")
    fast_lane_benchmark.add_argument("--timeframe", required=True)
    fast_lane_benchmark.add_argument("--start-ts", required=True)
    fast_lane_benchmark.add_argument("--end-ts", required=True)
    fast_lane_benchmark.add_argument("--warmup-start-ts")
    fast_lane_benchmark.add_argument(
        "--field",
        action="append",
        dest="benchmark_fields",
        default=[],
        help="optional loaded field override; repeat for multiple fields",
    )
    fast_lane_benchmark.add_argument(
        "--evidence-mode",
        default=BacktestEvidenceMode.ACCEPTED_RESEARCH.value,
        choices=[mode.value for mode in BacktestEvidenceMode],
    )
    fast_lane_benchmark.add_argument(
        "--artifact-mode",
        default=ArtifactMode.METRICS_ONLY.value,
        choices=[mode.value for mode in ArtifactMode],
    )
    fast_lane_benchmark.add_argument("--asof-date")
    fast_lane_benchmark.add_argument("--include-lockbox", action="store_true")
    fast_lane_benchmark.add_argument("--tolerance-abs", type=float, default=1e-12)
    fast_lane_benchmark.add_argument("--claim-speedup", action="store_true")
    fast_lane_benchmark.add_argument(
        "--cost-model-file",
        help="optional CostModelConfig JSON; useful for archive slices without funding fields",
    )
    strategy_spec = subparsers.add_parser(
        "strategy-spec",
        help="declarative strategy spec validation and registry inspection",
        description=f"Strategy-spec command group. {BOUNDARY_HELP}",
    )
    strategy_spec_subparsers = strategy_spec.add_subparsers(dest="strategy_spec_command")
    strategy_validate = strategy_spec_subparsers.add_parser(
        "validate",
        help="validate a declarative JSON/YAML strategy spec without executing it",
    )
    strategy_validate.add_argument("--spec-file", required=True)
    strategy_examples = strategy_spec_subparsers.add_parser(
        "examples",
        help="print built-in declarative example strategy specs as JSON",
    )
    strategy_examples.add_argument("--strategy-id")
    strategy_registry = strategy_spec_subparsers.add_parser(
        "registry",
        help="print allowed declarative strategy fields and expressions",
    )
    ledger = subparsers.add_parser(
        "ledger",
        help="append-only experiment ledger commands; generated exports only",
        description=f"Ledger command group. {BOUNDARY_HELP}",
    )
    ledger_subparsers = ledger.add_subparsers(dest="ledger_command")
    ledger_append = ledger_subparsers.add_parser(
        "append",
        help="append one run_manifest.json to the canonical Parquet ledger",
    )
    ledger_append.add_argument("--run", required=True, help="path to run_manifest.json")
    ledger_append.add_argument("--ledger", required=True, help="canonical Parquet ledger path")
    ledger_append.add_argument(
        "--evidence-mode",
        default="sandbox_diagnostic",
        choices=["sandbox_diagnostic", "accepted_research"],
    )
    ledger_append.add_argument("--notes", default="")
    ledger_append.add_argument("--max-part-rows", type=int, default=128)
    ledger_export = ledger_subparsers.add_parser(
        "export",
        help="generate CSV/XLSX from canonical Parquet ledger",
    )
    ledger_export.add_argument("--ledger", required=True, help="canonical Parquet ledger path")
    ledger_export.add_argument("--format", required=True, choices=["csv", "xlsx"])
    ledger_export.add_argument("--output", required=True)
    ledger_compact = ledger_subparsers.add_parser(
        "compact",
        help="compact part-backed ledger storage into a current Parquet artifact",
    )
    ledger_compact.add_argument("--ledger", required=True, help="canonical Parquet ledger path")
    ledger_compact.add_argument("--output", help="optional compacted Parquet output path")
    ledger_leaderboard = ledger_subparsers.add_parser(
        "leaderboard",
        help="print a conservative research leaderboard from the canonical ledger",
    )
    ledger_leaderboard.add_argument("--ledger", required=True, help="canonical Parquet ledger path")
    ledger_leaderboard.add_argument("--require-validation-pass", action="store_true")
    ledger_leaderboard.add_argument("--exclude-sandbox", action="store_true")
    ledger_leaderboard.add_argument("--rank", default="composite_v1")
    lead = subparsers.add_parser(
        "lead",
        help="non-promotable Lead Book commands",
        description=f"Lead Book command group. {BOUNDARY_HELP}",
    )
    lead_subparsers = lead.add_subparsers(dest="lead_command")
    lead_create = lead_subparsers.add_parser("create", help="create a non-promotable lead row")
    lead_create.add_argument("--lead-book", required=True)
    lead_create.add_argument("--source-artifact", required=True)
    lead_create.add_argument("--source-type", required=True)
    lead_create.add_argument("--strategy-family", required=True)
    lead_create.add_argument("--economic-thesis", required=True)
    lead_create.add_argument("--created-by-id", required=True)
    lead_create.add_argument("--roi-observed", type=float, required=True)
    lead_create.add_argument("--roi-projected", type=float, required=True)
    lead_create.add_argument("--roi-projection-assumptions", required=True)
    lead_create.add_argument("--why-interesting", required=True)
    lead_create.add_argument("--avg-trades-per-month", type=float, required=True)
    lead_create.add_argument("--total-trades", type=int, default=0)
    lead_create.add_argument("--usable-months", type=int, required=True)
    lead_create.add_argument("--losing-months-12m", type=int, default=0)
    lead_create.add_argument("--positive-months-12m", type=int, default=0)
    lead_create.add_argument("--top-2-trades-profit-share", type=float, default=0.0)
    lead_create.add_argument("--best-month-profit-share", type=float, default=0.0)
    lead_create.add_argument("--data-window-start", required=True)
    lead_create.add_argument("--data-window-end", required=True)
    lead_create.add_argument("--instrument", action="append", dest="instruments", required=True)
    lead_create.add_argument("--non-promotable", action="store_true")
    lead_list = lead_subparsers.add_parser("list", help="list Lead Book rows")
    lead_list.add_argument("--lead-book", required=True)
    lead_list.add_argument("--state")
    _add_lead_scan_args(lead_subparsers)
    lead_inspect = lead_subparsers.add_parser("inspect-request", help="request human inspection")
    lead_inspect.add_argument("--lead-book", required=True)
    lead_inspect.add_argument("--lead-id", required=True)
    lead_approve = lead_subparsers.add_parser(
        "approve-after-human-inspection",
        help="record human inspection notes and approve a lead for deep-validation request",
    )
    lead_approve.add_argument("--lead-book", required=True)
    lead_approve.add_argument("--lead-id", required=True)
    lead_approve.add_argument("--inspection-note-file", required=True)
    lead_approve.add_argument("--approving-agent-id", required=True)
    leadbook = subparsers.add_parser(
        "leadbook",
        help="Lead Book queue scan alias",
        description=f"Lead Book command alias. {BOUNDARY_HELP}",
    )
    leadbook_subparsers = leadbook.add_subparsers(dest="lead_command")
    _add_lead_scan_args(leadbook_subparsers)
    audit = subparsers.add_parser(
        "audit",
        help="research-only audit and blocker-report commands",
        description=f"Audit command group. {BOUNDARY_HELP}",
    )
    audit_subparsers = audit.add_subparsers(dest="audit_command")
    autonomous_readiness = audit_subparsers.add_parser(
        "autonomous-readiness",
        help="evaluate autonomous research-readiness evidence and write a blocker report",
    )
    autonomous_readiness.add_argument("--evidence-file", required=True)
    autonomous_readiness.add_argument("--output-path", required=True)
    autopilot = subparsers.add_parser(
        "autopilot",
        help="bounded research-only cycle planning commands",
        description=f"Autopilot planning command group. {BOUNDARY_HELP}",
    )
    autopilot_subparsers = autopilot.add_subparsers(dest="autopilot_command")
    autopilot_fixture_cycle = autopilot_subparsers.add_parser(
        "fixture-cycle-spec",
        help="write a sandbox diagnostic bounded-cycle spec and fixture inputs without running jobs",
    )
    autopilot_fixture_cycle.add_argument("--output-root", required=True)
    autopilot_fixture_cycle.add_argument("--run-id", default="autopilot-fixture-cycle")
    autopilot_fixture_cycle.add_argument("--instrument-id", default="hyperliquid:perp:BTC")
    autopilot_fixture_cycle.add_argument("--coin", default="BTC")
    autopilot_fixture_cycle.add_argument("--start-ts", default="2024-01-01T00:00:00+00:00")
    autopilot_fixture_cycle.add_argument("--end-ts", default="2024-08-01T00:00:00+00:00")
    autopilot_fixture_cycle.add_argument("--asof-date", default="2024-01-01")
    autopilot_fixture_cycle.add_argument("--created-by-id", default="codex-manager-agent")
    autopilot_public_cycle = autopilot_subparsers.add_parser(
        "public-candle-cycle-spec",
        help="write a public-API diagnostic bounded-cycle spec without running jobs",
    )
    autopilot_public_cycle.add_argument("--output-root", required=True)
    autopilot_public_cycle.add_argument("--run-id", default="autopilot-public-candle-cycle")
    autopilot_public_cycle.add_argument("--instrument-id", default="hyperliquid:perp:BTC")
    autopilot_public_cycle.add_argument("--coin", default="BTC")
    autopilot_public_cycle.add_argument("--timeframe", default="1d")
    autopilot_public_cycle.add_argument("--start-ts", default="2024-01-01T00:00:00+00:00")
    autopilot_public_cycle.add_argument("--end-ts", default="2024-08-01T00:00:00+00:00")
    autopilot_public_cycle.add_argument("--asof-date")
    autopilot_public_cycle.add_argument("--created-by-id", default="codex-manager-agent")
    autopilot_public_cycle.add_argument("--public-info-url", default="https://api.hyperliquid.xyz/info")
    autopilot_public_cycle.add_argument("--public-info-timeout", type=float, default=20.0)
    autopilot_public_cycle.add_argument("--max-public-info-pages", type=int, default=50)
    autopilot_public_cycle.add_argument("--max-candles-per-public-page", type=int, default=5_000)
    autopilot_public_cycle.add_argument("--coverage-min", type=float, default=DEFAULT_COVERAGE_MIN)
    autopilot_archive_cycle = autopilot_subparsers.add_parser(
        "archive-cycle-spec",
        help="write an accepted archive-ref bounded-cycle spec without collecting data",
    )
    autopilot_archive_cycle.add_argument("--output-root", required=True)
    autopilot_archive_cycle.add_argument("--run-id", default="autopilot-archive-cycle")
    autopilot_archive_cycle.add_argument("--archive-root", required=True)
    autopilot_archive_cycle.add_argument("--strategy-root", required=True)
    autopilot_archive_cycle.add_argument("--archive-snapshot-id", required=True)
    autopilot_archive_cycle.add_argument("--universe-snapshot-id", required=True)
    autopilot_archive_cycle.add_argument("--venue", default="hyperliquid")
    autopilot_archive_cycle.add_argument("--instrument-id", default="hyperliquid:perp:BTC")
    autopilot_archive_cycle.add_argument("--family", default="bars")
    autopilot_archive_cycle.add_argument("--timeframe", default="1d")
    autopilot_archive_cycle.add_argument("--start-ts", default="2024-01-01T00:00:00+00:00")
    autopilot_archive_cycle.add_argument("--end-ts", default="2024-08-01T00:00:00+00:00")
    autopilot_archive_cycle.add_argument("--asof-date", default=date.today().isoformat())
    autopilot_archive_cycle.add_argument("--coverage-min", type=float, default=DEFAULT_COVERAGE_MIN)
    autopilot_archive_cycle.add_argument("--requested-field", dest="requested_fields", action="append")
    autopilot_archive_cycle.add_argument("--strategy-max-files", type=int, default=50)
    autopilot_archive_cycle.add_argument("--created-by-id", default="codex-manager-agent")
    autopilot_archive_cycle.add_argument("--strategy-family", default="uploaded_declarative_strategy")
    autopilot_archive_cycle.add_argument(
        "--economic-thesis",
        default=(
            "Local declarative strategy spec was tested by the bounded research loop "
            "against operator-supplied accepted archive refs."
        ),
    )
    autopilot_archive_cycle.add_argument("--lead-avg-trades-per-month", type=float, default=10.0)
    autopilot_archive_cycle.add_argument("--lead-total-trades", type=int, default=60)
    autopilot_archive_cycle.add_argument("--lead-usable-months", type=int, default=6)
    autopilot_archive_cycle.add_argument("--lead-losing-months-12m", type=int, default=0)
    autopilot_archive_cycle.add_argument("--lead-positive-months-12m", type=int, default=6)
    autopilot_archive_cycle.add_argument("--lead-top-2-trades-profit-share", type=float, default=0.0)
    autopilot_archive_cycle.add_argument("--lead-best-month-profit-share", type=float, default=0.0)
    autopilot_strategy_queue = autopilot_subparsers.add_parser(
        "strategy-queue-scan",
        help="scan local declarative strategy specs and write an input-hygiene manifest",
    )
    autopilot_strategy_queue.add_argument("--strategy-root", required=True)
    autopilot_strategy_queue.add_argument("--output-root", required=True)
    autopilot_strategy_queue.add_argument("--run-id", default="strategy-queue-scan")
    autopilot_strategy_queue.add_argument("--max-files", type=int, default=500)
    autopilot_cycle = autopilot_subparsers.add_parser(
        "research-cycle",
        help="plan or enqueue a bounded durable research cycle without running jobs",
    )
    autopilot_cycle.add_argument("--mode", default="bounded", choices=["bounded"])
    autopilot_cycle.add_argument("--cycle-spec-file", required=True)
    autopilot_cycle.add_argument("--output-root", required=True)
    autopilot_cycle.add_argument("--job-store", required=True)
    autopilot_cycle.add_argument("--enqueue", action="store_true")
    autopilot_cycle.add_argument("--max-jobs", type=int)
    autopilot_run_cycle = autopilot_subparsers.add_parser(
        "run-cycle-plan",
        help="run one bounded enqueued research-cycle plan through durable workers",
    )
    autopilot_run_cycle.add_argument("--plan-manifest", required=True)
    autopilot_run_cycle.add_argument("--job-store")
    autopilot_run_cycle.add_argument("--worker-id", default="autopilot-cycle-runner")
    autopilot_run_cycle.add_argument("--max-jobs", type=int)
    autopilot_run_cycle.add_argument("--no-audit-on-blocker", action="store_true")
    autopilot_scheduler_tick = autopilot_subparsers.add_parser(
        "scheduler-tick",
        help="run one bounded scheduler tick over already-enqueued cycle plans",
    )
    autopilot_scheduler_tick.add_argument(
        "--plan-manifest",
        action="append",
        required=True,
        help="enqueued bounded-cycle plan manifest; repeat to provide multiple plans",
    )
    autopilot_scheduler_tick.add_argument("--output-root", required=True)
    autopilot_scheduler_tick.add_argument("--job-store")
    autopilot_scheduler_tick.add_argument("--worker-id", default="autopilot-scheduler")
    autopilot_scheduler_tick.add_argument("--scheduler-id", default="autopilot-scheduler")
    autopilot_scheduler_tick.add_argument("--max-plans", type=int, default=1)
    autopilot_scheduler_tick.add_argument("--max-jobs-per-plan", type=int)
    autopilot_scheduler_tick.add_argument("--no-audit-on-blocker", action="store_true")
    autonomy = subparsers.add_parser(
        "autonomy",
        help="fixture-backed research-only autonomy dry-run commands",
        description=f"Autonomy dry-run command group. {BOUNDARY_HELP}",
    )
    autonomy_subparsers = autonomy.add_subparsers(dest="autonomy_command")
    autonomy_dry_run = autonomy_subparsers.add_parser(
        "dry-run",
        help="run the fixture-backed sandbox loop and write blocker evidence",
    )
    autonomy_dry_run.add_argument("--output-root", required=True)
    autonomy_dry_run.add_argument("--run-id", default="autonomy-dry-run")
    autonomy_dry_run.add_argument("--strategy-id", default="hl_funding_carry_v1")
    autonomy_dry_run.add_argument(
        "--data-mode",
        default="archive_fixture",
        choices=["archive_fixture", "manifest_fixture"],
    )
    autonomy_dry_run.add_argument("--created-by-id", default="codex-manager-agent")
    autonomy_agent_context = autonomy_subparsers.add_parser(
        "agent-context",
        help="print a read-only JSON handoff map for autonomous research agents",
    )
    autonomy_agent_context.add_argument("--repo-root", default=".")
    autonomy_agent_context.add_argument("--run-id", default="autonomous-research-agent-context")
    autonomy_agent_context.add_argument("--asof-date")
    autonomy_agent_context.add_argument("--output-path")
    worker = subparsers.add_parser(
        "worker",
        help="durable local worker/job-store commands; no ASGI in-process execution",
        description=f"Worker command group. {BOUNDARY_HELP}",
    )
    worker_subparsers = worker.add_subparsers(dest="worker_command")
    worker_init = worker_subparsers.add_parser("init", help="initialize the SQLite WAL job store")
    worker_init.add_argument("--job-store", required=True)
    worker_enqueue = worker_subparsers.add_parser("enqueue", help="enqueue a durable worker job")
    worker_enqueue.add_argument("--job-store", required=True)
    worker_enqueue.add_argument("--kind", required=True, choices=[kind.value for kind in WorkerJobKind])
    worker_enqueue.add_argument("--input-spec-json")
    worker_enqueue.add_argument("--input-spec-file")
    worker_enqueue.add_argument("--job-id")
    worker_enqueue.add_argument("--max-attempts", type=int, default=3)
    worker_run = worker_subparsers.add_parser("run", help="claim and run one queued job")
    worker_run.add_argument("--job-store", required=True)
    worker_run.add_argument("--kind", required=True, choices=[kind.value for kind in WorkerJobKind])
    worker_run.add_argument("--worker-id", required=True)
    worker_run.add_argument(
        "--forbid-asgi",
        action="store_true",
        help="fail if a caller attempts to run worker code from an ASGI/operator process",
    )
    worker_status = worker_subparsers.add_parser("status", help="list durable jobs")
    worker_status.add_argument("--job-store", required=True)
    worker_status.add_argument("--kind", choices=[kind.value for kind in WorkerJobKind])
    worker_status.add_argument("--status", choices=[status.value for status in WorkerJobStatus])
    worker_status.add_argument("--job-id")
    worker_retry = worker_subparsers.add_parser("retry", help="manually requeue a failed/stale/cancelled job")
    worker_retry.add_argument("--job-store", required=True)
    worker_retry.add_argument("--job-id", required=True)
    worker_retry.add_argument("--worker-id", default="manual-retry")
    worker_cancel = worker_subparsers.add_parser("cancel", help="cancel a queued/claimed/running job")
    worker_cancel.add_argument("--job-store", required=True)
    worker_cancel.add_argument("--job-id", required=True)
    worker_cancel.add_argument("--worker-id", default="manual-cancel")
    worker_heartbeat = worker_subparsers.add_parser("heartbeat", help="record a job heartbeat")
    worker_heartbeat.add_argument("--job-store", required=True)
    worker_heartbeat.add_argument("--job-id", required=True)
    worker_heartbeat.add_argument("--worker-id", required=True)
    worker_stale = worker_subparsers.add_parser("mark-stale", help="mark stale running jobs")
    worker_stale.add_argument("--job-store", required=True)
    worker_stale.add_argument("--stale-after-seconds", type=int, required=True)
    worker_stale.add_argument("--worker-id", default="stale-monitor")
    ui = subparsers.add_parser(
        "ui",
        help="render read-only v2 visibility snapshots",
        description=f"UI visibility command group. {BOUNDARY_HELP}",
    )
    ui_subparsers = ui.add_subparsers(dest="ui_command")
    ui_render = ui_subparsers.add_parser(
        "render",
        help="render a supplied v2 visibility snapshot JSON as static HTML",
    )
    ui_render.add_argument("--input-root", required=True)
    ui_render.add_argument("--snapshot-json", required=True)
    ui_render.add_argument("--output-root", required=True)
    ui_render.add_argument("--output-html", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(V2_SCHEMA_VERSION)
        return 0
    if args.show_boundary:
        for key in sorted(RESEARCH_BOUNDARY):
            print(f"{key}={RESEARCH_BOUNDARY[key]}")
        return 0
    if args.list_contexts:
        for context in BOUNDED_CONTEXTS:
            print(context)
        return 0
    if args.command == "archive":
        return _handle_archive(args, parser)
    if args.command == "archive-inventory":
        return _handle_archive_inventory(args, parser)
    if args.command == "universe":
        return _handle_universe(args, parser)
    if args.command == "collectors":
        return _handle_collectors(args, parser)
    if args.command == "data":
        return _handle_data(args, parser)
    if args.command == "backtest-data":
        return _handle_backtest_data(args, parser)
    if args.command == "fast-lane":
        return _handle_fast_lane(args, parser)
    if args.command == "strategy-spec":
        return _handle_strategy_spec(args, parser)
    if args.command == "ledger":
        return _handle_ledger(args, parser)
    if args.command in {"lead", "leadbook"}:
        return _handle_lead(args, parser)
    if args.command == "audit":
        return _handle_audit(args, parser)
    if args.command == "autopilot":
        return _handle_autopilot(args, parser)
    if args.command == "autonomy":
        return _handle_autonomy(args, parser)
    if args.command == "worker":
        return _handle_worker(args, parser)
    if args.command == "ui":
        return _handle_ui(args, parser)
    parser.print_help()
    return 0


def _handle_archive_inventory(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    service = ArchiveInventoryService(repo_root=args.repo_root, archive_root=args.archive_root)
    start_ts = _parse_datetime(args.start_ts) if args.start_ts else None
    end_ts = _parse_datetime(args.end_ts) if args.end_ts else None
    if args.bridge_central_snapshot:
        if args.bridge_archive_root is None:
            print("central_archive_snapshot_bridge_rejected=bridge_archive_root_required")
            return 1
        if start_ts is None or end_ts is None:
            print("central_archive_snapshot_bridge_rejected=start_ts_and_end_ts_required")
            return 1
        try:
            result = build_central_archive_snapshot_bridge(
                CentralArchiveSnapshotBridgeConfig(
                    central_archive_root=args.archive_root,
                    bridge_archive_root=args.bridge_archive_root,
                    project_validation_report_path=args.project_validation_report,
                    instrument_ids=tuple(args.instrument_ids),
                    venue=args.venue or "binance_usdm",
                    family=args.family or "bars",
                    timeframe=args.timeframe or "1m",
                    start_ts=start_ts,
                    end_ts=end_ts,
                    asof_date=_parse_date(args.asof_date) if args.asof_date else None,
                    coverage_min=args.bridge_coverage_min,
                    replace_existing=args.replace_existing_bridge,
                )
            )
        except (OSError, CentralArchiveSnapshotBridgeError, ValueError, ValidationError) as exc:
            print(f"central_archive_snapshot_bridge_rejected={exc}")
            return 1
        print(json.dumps(result.model_dump(mode="json"), sort_keys=True, indent=2))
        return 0
    if args.feature_catalog:
        feature_service = FeatureStoreCatalogService(repo_root=args.repo_root, archive_root=args.archive_root)
        if args.summary:
            catalog = feature_service.build_catalog()
            print(json.dumps(catalog.model_dump(mode="json", exclude={"entries"}), sort_keys=True, indent=2))
            return 0
        entries = feature_service.query(
            feature_family=args.feature_family,
            source_family=args.source_family,
            venue=args.venue,
            symbol=args.symbol,
            instrument_ids=tuple(args.instrument_ids),
            timeframe=args.timeframe,
            evidence_scope=args.evidence_scope,
            accepted_only=args.accepted_only,
            start_ts=start_ts,
            end_ts=end_ts,
        )
        print(json.dumps([entry.model_dump(mode="json") for entry in entries], sort_keys=True, indent=2))
        return 0
    if args.strategy_spec_file:
        if start_ts is None or end_ts is None:
            print("archive_inventory_rejected=start_ts_and_end_ts_required_for_strategy_resolution")
            return 1
        try:
            report = service.resolve_strategy_data_requirements(
                StrategyDataRequirementRequest(
                    strategy_spec=load_strategy_spec_file(args.strategy_spec_file),
                    archive_root=args.archive_root,
                    repo_root=args.repo_root,
                    instrument_ids=tuple(args.instrument_ids),
                    venue=args.venue,
                    start_ts=start_ts,
                    end_ts=end_ts,
                    evidence_mode=args.evidence_mode,
                    artifact_mode=ArtifactMode(args.artifact_mode),
                    prefer_fast_lane=args.prefer_fast_lane,
                    require_reference_audit=args.require_reference_audit,
                ),
                asof_date=_parse_date(args.asof_date) if args.asof_date else None,
            )
        except (ValueError, ValidationError) as exc:
            print(f"archive_inventory_rejected={exc}")
            return 1
        print(json.dumps(report.model_dump(mode="json"), sort_keys=True, indent=2))
        return 0 if report.ready else 1
    if args.summary:
        inventory = service.build_inventory()
        print(json.dumps(inventory.summary.model_dump(mode="json"), sort_keys=True, indent=2))
        return 0
    records = service.query(
        symbol=args.symbol,
        instrument_ids=tuple(args.instrument_ids),
        venue=args.venue,
        family=args.family,
        timeframe=args.timeframe,
        evidence_scope=args.evidence_scope,
        coverage_report_id=args.coverage_report_id,
        accepted_only=args.accepted_only,
        start_ts=start_ts,
        end_ts=end_ts,
    )
    print(json.dumps([record.model_dump(mode="json") for record in records], sort_keys=True, indent=2))
    return 0


def _handle_archive(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.archive_command is None:
        parser.parse_args(["archive", "--help"])
        return 0
    layout = ArchiveLayout(Path(args.archive_root))
    store = ArchiveManifestStore(layout)
    if args.archive_command == "init":
        created = layout.initialize()
        print(f"archive_initialized={layout.root}")
        for path in created:
            print(path)
        return 0
    if args.archive_command == "validate":
        issues = store.validate_files()
        if not issues:
            print("archive_valid=true")
            return 0
        print("archive_valid=false")
        for issue in issues:
            print(f"{issue.code}: {issue.path}: {issue.message}")
        return 1
    if args.archive_command == "snapshot":
        snapshot = create_archive_snapshot(
            store=store,
            layer=ArchiveLayer(args.layer),
            venue_scope=args.venue_scope,
            start_ts=_parse_datetime(args.start_ts),
            end_ts=_parse_datetime(args.end_ts),
            lockbox_policy_id=args.lockbox_policy_id,
            notes=args.notes,
        )
        print(f"archive_snapshot_id={snapshot.archive_snapshot_id}")
        return 0
    if args.archive_command == "build-bronze":
        if args.datatype == "candles":
            result = raw_candles_to_bronze(
                archive_root=args.archive_root,
                raw_file_id=args.raw_file_id,
                job_id=args.job_id,
                instrument_id=args.instrument_id,
                timeframe=args.timeframe,
            )
        elif args.datatype == "funding":
            result = raw_funding_to_bronze(
                archive_root=args.archive_root,
                raw_file_id=args.raw_file_id,
                job_id=args.job_id,
                instrument_id=args.instrument_id,
            )
        else:
            result = raw_asset_contexts_to_bronze(
                archive_root=args.archive_root,
                raw_file_id=args.raw_file_id,
                job_id=args.job_id,
                instrument_id=args.instrument_id,
            )
        _print_rebuild_result(result)
        return 0
    if args.archive_command == "build-silver":
        if args.datatype == "candles":
            result = bronze_candles_to_silver_bars(
                archive_root=args.archive_root,
                bronze_file_id=args.bronze_file_id,
                job_id=args.job_id,
                derive_timeframes=tuple(
                    value.strip() for value in args.derive_timeframes.split(",") if value.strip()
                ),
                write_coverage=not args.skip_coverage,
                create_snapshot=args.snapshot,
            )
        elif args.datatype == "funding":
            result = bronze_funding_to_silver(
                archive_root=args.archive_root,
                bronze_file_id=args.bronze_file_id,
                job_id=args.job_id,
            )
        else:
            result = bronze_asset_contexts_to_silver(
                archive_root=args.archive_root,
                bronze_file_id=args.bronze_file_id,
                job_id=args.job_id,
            )
        _print_rebuild_result(result)
        return 0
    if args.archive_command == "snapshot-silver-market-data":
        snapshot = create_silver_market_data_snapshot(
            archive_root=args.archive_root,
            venue_scope=args.venue_scope,
            start_ts=_parse_datetime(args.start_ts),
            end_ts=_parse_datetime(args.end_ts),
            notes=args.notes,
        )
        print(f"archive_snapshot_id={snapshot.archive_snapshot_id}")
        return 0
    parser.error(f"unsupported archive command: {args.archive_command}")
    return 2


def _parse_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("timestamps must include timezone")
    return parsed


def _print_rebuild_result(result) -> None:
    print(f"output_file_ids={','.join(row.file_id for row in result.output_files)}")
    print(
        "normalization_manifest_ids="
        + ",".join(row.normalization_manifest_id for row in result.normalization_manifests)
    )
    print(f"coverage_report_ids={','.join(result.coverage_report_ids)}")
    if result.archive_snapshot_id:
        print(f"archive_snapshot_id={result.archive_snapshot_id}")


def _handle_universe(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.universe_command is None:
        parser.parse_args(["universe", "--help"])
        return 0
    if args.universe_command == "refresh":
        source = _universe_refresh_source(args, parser)
        client = (
            HyperliquidInfoClient(
                base_url=args.public_info_url,
                timeout=args.public_info_timeout,
            )
            if source == "public_api"
            else None
        )
        result = refresh_hyperliquid_universe(
            archive_root=args.archive_root,
            payload_file=args.payload_file if source == "payload_file" else None,
            asof_date=_parse_date(args.asof_date),
            min_day_notional_usd=args.min_day_notional_usd,
            mode=UniverseMode(args.mode),
            include_hip3_dexs=args.include_hip3_dexs,
            client=client,
        )
        print(f"universe_snapshot_id={result.snapshot_id}")
        print(f"raw_file_id={result.raw_file_id}")
        print(f"source_mode={result.payload_source}")
        print(f"raw_payload_sha256={result.raw_payload_sha256}")
        print(f"venue_adapter_id={result.venue_adapter_id}")
        print(f"source_endpoint_or_subscription={result.source_endpoint_or_subscription}")
        if result.raw_request_id:
            print(f"raw_request_id={result.raw_request_id}")
        if result.raw_response_id:
            print(f"raw_response_id={result.raw_response_id}")
        print(f"instrument_count={result.instrument_count}")
        print(f"eligible_count={result.eligible_count}")
        print(f"universe_mode={result.universe_mode.value}")
        return 0
    if args.universe_command == "list":
        rows = select_asof_universe(
            archive_root=args.archive_root,
            asof_date=_parse_date(args.asof_date),
            eligible_only=args.eligible_only,
            mode=UniverseMode(args.mode),
        )
        for row in rows:
            print(
                "\t".join(
                    [
                        row.snapshot_id,
                        row.instrument_id,
                        str(row.day_ntl_vlm_usd),
                        str(row.eligible),
                        row.exclusion_reason or "",
                        row.evidence_scope,
                    ]
                )
            )
        return 0
    if args.universe_command == "explain":
        row = explain_instrument(
            archive_root=args.archive_root,
            snapshot_id=args.snapshot,
            instrument_id=args.instrument,
        )
        if row is None:
            print("instrument_found=false")
            return 1
        print(row.model_dump_json())
        return 0
    if args.universe_command == "diff":
        diff = diff_snapshots(
            archive_root=args.archive_root,
            left_snapshot_id=args.left,
            right_snapshot_id=args.right,
        )
        for key in ("added", "removed", "unchanged"):
            print(f"{key}={','.join(diff[key])}")
        return 0
    parser.error(f"unsupported universe command: {args.universe_command}")
    return 2


def _parse_date(value: str):
    return datetime.fromisoformat(value).date()


def _handle_collectors(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.collectors_command is None:
        parser.parse_args(["collectors", "--help"])
        return 0
    if args.collectors_command == "gap-template":
        try:
            gap_requests = _load_data_gap_requests(args.gap_request_file)
        except (OSError, json.JSONDecodeError, ValueError, ValidationError) as exc:
            print(f"collector_gap_template_rejected={exc}")
            return 1
        selected = []
        for gap in gap_requests:
            if args.gap_request_id and gap.data_gap_request_id != args.gap_request_id:
                continue
            if args.requested_family and gap.requested_family != args.requested_family:
                continue
            selected.append(gap)
        templates = []
        skipped = []
        for gap in selected:
            try:
                template = collector_template_from_gap_request(gap, adapter_id=args.adapter_id)
            except ValueError as exc:
                skipped.append(
                    {
                        "data_gap_request_id": gap.data_gap_request_id,
                        "requested_family": gap.requested_family,
                        "reason": str(exc),
                    }
                )
                continue
            templates.append(template.model_dump(mode="json"))
        payload = {
            "schema_version": V2_SCHEMA_VERSION,
            "template_count": len(templates),
            "skipped_gap_count": len(skipped),
            "templates": templates,
            "skipped_gap_requests": skipped,
            **dict(RESEARCH_BOUNDARY),
        }
        print(json.dumps(payload, sort_keys=True, indent=2))
        return 0 if templates or not selected else 1
    if args.collectors_command == "historical-perps":
        output_root = (Path(args.output_root).resolve(strict=False) / args.run_id).resolve(strict=False)
        archive_root = (
            Path(args.archive_root).resolve(strict=False)
            if args.archive_root
            else (output_root / "archive").resolve(strict=False)
        )
        result = collect_historical_perp_dataset(
            HistoricalPerpDatasetConfig(
                output_root=str(output_root),
                archive_root=str(archive_root),
                run_id=args.run_id,
                start_ts=_parse_datetime(args.start_ts),
                end_ts=_parse_datetime(args.end_ts),
                timeframe=args.timeframe,
                asof_date=_parse_date(args.asof_date),
                min_day_notional_usd=args.min_day_notional_usd,
                max_instruments=args.max_instruments,
                coins=tuple(args.coins or ()),
                coverage_min=args.coverage_min,
                public_info_url=args.public_info_url,
                public_info_timeout=args.public_info_timeout,
                max_public_info_pages=args.max_public_info_pages,
                max_candles_per_public_page=args.max_candles_per_public_page,
                candle_source=args.candle_source,
                trusted_candle_records_root=args.trusted_candle_records_root,
                trusted_candle_records_template=args.trusted_candle_records_template,
                trusted_candle_records_format=args.trusted_candle_records_format,
                max_candle_records_file_bytes=args.max_candle_records_file_bytes,
                include_funding=args.include_funding,
                max_funding_pages=args.max_funding_pages,
                include_hip3_dexs=args.include_hip3_dexs,
                validate_binance=not args.no_binance_validation,
                binance_base_url=args.binance_base_url,
                binance_timeout=args.binance_timeout,
                binance_close_diff_warn_bps=args.binance_close_diff_warn_bps,
                created_by_id=args.created_by_id,
            )
        )
        print(f"report_path={result.report_path}")
        print(f"archive_root={result.archive_root}")
        print(f"universe_snapshot_id={result.universe_snapshot_id}")
        print(f"archive_snapshot_id={result.archive_snapshot_id}")
        print(f"candle_source={result.candle_source}")
        print(f"universe_eligible_count={result.universe_eligible_count}")
        print(f"selected_instrument_count={result.selected_instrument_count}")
        print(f"collected_instrument_count={result.collected_instrument_count}")
        print(f"technical_coverage_pass_count={result.technical_coverage_pass_count}")
        if result.min_coverage_ratio is not None:
            print(f"min_coverage_ratio={result.min_coverage_ratio:.12f}")
        print(f"binance_checked_count={result.binance_checked_count}")
        print(f"binance_pass_count={result.binance_pass_count}")
        print(f"binance_warning_count={result.binance_warning_count}")
        print(f"binance_skipped_count={result.binance_skipped_count}")
        print(f"funding_collected_count={result.funding_collected_count}")
        print(f"funding_skipped_count={result.funding_skipped_count}")
        print("accepted_research_ready=false")
        print(f"current_universe_caveat={result.current_universe_caveat}")
        return 0
    parser.error(f"unsupported collectors command: {args.collectors_command}")
    return 2


def _load_data_gap_requests(path: str) -> tuple[DataGapRequest, ...]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("data_gap_requests"), list):
        rows = payload["data_gap_requests"]
    elif isinstance(payload, dict):
        rows = [payload]
    else:
        raise ValueError("gap request file must contain a DataGapRequest, list, or resolver report")
    return tuple(DataGapRequest.model_validate(row) for row in rows)


def _universe_refresh_source(args: argparse.Namespace, parser: argparse.ArgumentParser) -> str:
    if args.source == "public_api":
        if args.payload_file:
            parser.error("universe refresh --source public_api cannot include --payload-file")
        return "public_api"
    if args.source == "payload_file":
        if not args.payload_file:
            parser.error("universe refresh --source payload_file requires --payload-file")
        return "payload_file"
    if args.payload_file:
        return "payload_file"
    parser.error("universe refresh requires --payload-file or --source public_api")
    return "payload_file"


def _add_data_quality_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--archive-root", required=True)
    parser.add_argument("--input-parquet", required=True)
    parser.add_argument("--venue", required=True)
    parser.add_argument("--instrument-id", required=True)
    parser.add_argument("--family", default="bars")
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--start-ts", required=True)
    parser.add_argument("--end-ts", required=True)
    parser.add_argument("--timestamp-field", default="ts")
    parser.add_argument("--volume-field", default="volume")
    parser.add_argument("--price-field", default="close")
    parser.add_argument("--spread-field", default="spread")
    parser.add_argument("--funding-field", default="funding")
    parser.add_argument(
        "--evidence-mode",
        default=EvidenceMode.ACCEPTED_RESEARCH.value,
        choices=[mode.value for mode in EvidenceMode],
    )


def _add_lead_scan_args(subparsers: argparse._SubParsersAction) -> None:
    lead_scan = subparsers.add_parser(
        "scan",
        help="write a read-only Lead Book queue scan manifest",
    )
    lead_scan.add_argument("--lead-book", required=True)
    lead_scan.add_argument(
        "--status",
        action="append",
        required=True,
        help="lead state to include; accepts comma-separated values and may be repeated",
    )
    lead_scan.add_argument("--output-path", required=True)
    lead_scan.add_argument("--max-rows", type=int, default=500)


def _parse_lead_scan_states(values: Sequence[str]) -> tuple[LeadState, ...]:
    states: list[LeadState] = []
    for value in values:
        for raw_part in value.split(","):
            part = raw_part.strip()
            if not part:
                continue
            states.append(LeadState(part))
    if not states:
        raise LeadBookError("lead_book_scan_requires_status")
    return tuple(dict.fromkeys(states))


def _handle_data(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.data_command is None:
        parser.parse_args(["data", "--help"])
        return 0
    rows = pq.read_table(Path(args.input_parquet)).to_pylist()
    start_ts = _parse_datetime(args.start_ts)
    end_ts = _parse_datetime(args.end_ts)
    mode = EvidenceMode(args.evidence_mode)
    if args.data_command == "coverage":
        report = coverage_report_for_bars(
            rows,
            venue=args.venue,
            instrument_id=args.instrument_id,
            family=args.family,
            timeframe=args.timeframe,
            start_ts=start_ts,
            end_ts=end_ts,
            ts_field=args.timestamp_field,
            volume_field=args.volume_field,
            price_field=args.price_field,
            spread_field=args.spread_field,
            funding_field=args.funding_field,
            coverage_min=args.coverage_min,
            evidence_mode=mode,
        )
        if args.write_manifest:
            CoverageManifestStore(ArchiveLayout(Path(args.archive_root))).append_coverage_report(report)
        print(f"coverage_report_id={report.coverage_report_id}")
        print(f"coverage_ratio={report.coverage_ratio:.12f}")
        print(f"expected_rows={report.expected_rows}")
        print(f"observed_rows={report.observed_rows}")
        print(f"missing_days={','.join(report.missing_days)}")
        print(f"quality_status={report.quality_status.value}")
        print(f"evidence_eligible={str(report.evidence_eligible).lower()}")
        print(f"blocker_reasons={','.join(report.blocker_reasons)}")
        return 1 if mode != EvidenceMode.SANDBOX_DIAGNOSTIC and not report.evidence_eligible else 0
    if args.data_command == "quality-report":
        checks = build_quality_checks(
            rows,
            venue=args.venue,
            instrument_id=args.instrument_id,
            family=args.family,
            timeframe=args.timeframe,
            start_ts=start_ts,
            end_ts=end_ts,
            ts_field=args.timestamp_field,
            volume_field=args.volume_field,
            price_field=args.price_field,
            spread_field=args.spread_field,
            funding_field=args.funding_field,
            evidence_mode=mode,
        )
        if args.write_manifest:
            CoverageManifestStore(ArchiveLayout(Path(args.archive_root))).append_quality_checks(checks)
        for check in checks:
            print(
                "\t".join(
                    [
                        check.check_type,
                        check.status.value,
                        str(check.affected_count),
                        ",".join(check.affected_timestamps_sample),
                    ]
                )
            )
        failed = any(check.status.value == "fail" for check in checks)
        return 1 if failed and mode != EvidenceMode.SANDBOX_DIAGNOSTIC else 0
    parser.error(f"unsupported data command: {args.data_command}")
    return 2


def _handle_backtest_data(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.backtest_data_command is None:
        parser.parse_args(["backtest-data", "--help"])
        return 0
    if args.backtest_data_command == "load-panel":
        request = BacktestDataRequest(
            archive_root=args.archive_root,
            archive_snapshot_id=args.archive_snapshot_id,
            universe_snapshot_id=args.universe_snapshot_id,
            venue=args.venue,
            instrument_id=args.instrument_id,
            family=args.family,
            timeframe=args.timeframe,
            start_ts=_parse_datetime(args.start_ts),
            end_ts=_parse_datetime(args.end_ts),
            warmup_start_ts=_parse_datetime(args.warmup_start_ts)
            if args.warmup_start_ts
            else None,
            requested_fields=tuple(args.fields),
            evidence_mode=BacktestEvidenceMode(args.evidence_mode),
            exclude_lockbox=not args.include_lockbox,
        )
        try:
            result = BacktestDataService(args.archive_root).load_panel(
                request,
                asof_date=_parse_date(args.asof_date) if args.asof_date else None,
                write_manifest=not args.no_write_manifest,
            )
        except BacktestDataError as exc:
            print(f"backtest_data_load_rejected={exc}")
            return 1
        print(f"data_manifest_id={result.data_manifest.data_manifest_id}")
        print(f"archive_snapshot_id={result.archive_snapshot_id}")
        print(f"universe_snapshot_id={result.universe_snapshot_id}")
        print(f"coverage_report_id={result.coverage_report_id}")
        print(f"loaded_fields={','.join(result.loaded_fields)}")
        print(f"row_count={len(result.rows)}")
        print(f"warmup_row_count={result.warmup_row_count}")
        print(f"reported_row_count={result.reported_row_count}")
        return 0
    parser.error(f"unsupported backtest-data command: {args.backtest_data_command}")
    return 2


def _handle_fast_lane(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.fast_lane_command is None:
        parser.parse_args(["fast-lane", "--help"])
        return 0
    if args.fast_lane_command == "parity-report":
        try:
            report = audit_fast_lane_parity(
                reference_manifest=_load_run_manifest(args.reference_run),
                fast_manifest=_load_run_manifest(args.fast_run),
                tolerance_abs=args.tolerance_abs,
            )
        except (OSError, ValueError, ValidationError) as exc:
            print(f"fast_lane_parity_report_rejected={exc}")
            return 1
        print(json.dumps(report.model_dump(mode="json"), sort_keys=True, indent=2))
        return 0 if report.status.value == "pass" else 1
    if args.fast_lane_command == "reference-rerun-plan":
        try:
            plan = build_reference_rerun_plan(
                _load_run_manifest(args.fast_run),
                run_manifest_ref=args.fast_run,
                reason=args.reason,
            )
        except (OSError, ValueError, ValidationError) as exc:
            print(f"fast_lane_reference_rerun_plan_rejected={exc}")
            return 1
        print(json.dumps(plan.model_dump(mode="json"), sort_keys=True, indent=2))
        return 0
    if args.fast_lane_command == "full-artifact-replay-plan":
        try:
            plan = build_full_artifact_replay_plan(
                _load_run_manifest(args.run),
                run_manifest_ref=args.run,
                reason=args.reason,
            )
        except (OSError, ValueError, ValidationError) as exc:
            print(f"full_artifact_replay_plan_rejected={exc}")
            return 1
        print(json.dumps(plan.model_dump(mode="json"), sort_keys=True, indent=2))
        return 0
    if args.fast_lane_command == "verify-full-artifact-replay":
        try:
            source = _load_run_manifest(args.source_run)
            full = _load_run_manifest(args.full_run)
            report = verify_full_artifact_replay(
                source_manifest=source,
                replay_manifest=full,
                source_replay_manifest=_load_replay_manifest_for_run(
                    source,
                    run_manifest_path=Path(args.source_run),
                ),
                full_replay_manifest=_load_replay_manifest_for_run(
                    full,
                    run_manifest_path=Path(args.full_run),
                ),
                tolerance_abs=args.tolerance_abs,
            )
        except (OSError, ValueError, ValidationError) as exc:
            print(f"full_artifact_replay_verification_rejected={exc}")
            return 1
        print(json.dumps(report.model_dump(mode="json"), sort_keys=True, indent=2))
        return 0 if report.status.value == "pass" else 1
    if args.fast_lane_command == "sample-reference-audits":
        try:
            selected = select_reference_audit_sample(
                tuple(args.run_ids),
                sample_rate=args.sample_rate,
                seed=args.seed,
                minimum_count=args.minimum_count,
            )
        except ValueError as exc:
            print(f"fast_lane_reference_audit_sample_rejected={exc}")
            return 1
        print(json.dumps({"selected_run_ids": selected}, sort_keys=True, indent=2))
        return 0
    if args.fast_lane_command == "benchmark-run":
        try:
            report = run_archive_backtest_benchmark(
                BacktestBenchmarkConfig(
                    benchmark_id=args.benchmark_id,
                    benchmark_tier=BenchmarkTier(args.benchmark_tier),
                    strategy_spec=load_strategy_spec_file(args.strategy_spec_file),
                    archive_root=args.archive_root,
                    output_root=args.output_root,
                    report_path=args.report_path,
                    archive_snapshot_id=args.archive_snapshot_id,
                    universe_snapshot_id=args.universe_snapshot_id,
                    venue=args.venue,
                    instrument_id=args.benchmark_instrument_ids[0],
                    instrument_ids=tuple(args.benchmark_instrument_ids),
                    family=args.family,
                    timeframe=args.timeframe,
                    start_ts=_parse_datetime(args.start_ts),
                    end_ts=_parse_datetime(args.end_ts),
                    warmup_start_ts=_parse_datetime(args.warmup_start_ts)
                    if args.warmup_start_ts
                    else None,
                    requested_fields=tuple(args.benchmark_fields),
                    evidence_mode=BacktestEvidenceMode(args.evidence_mode),
                    asof_date=_parse_date(args.asof_date) if args.asof_date else None,
                    include_lockbox=args.include_lockbox,
                    artifact_mode=ArtifactMode(args.artifact_mode),
                    cost_model=_load_cost_model(args.cost_model_file),
                    tolerance_abs=args.tolerance_abs,
                    claim_speedup=args.claim_speedup,
                )
            )
        except (OSError, ValueError, ValidationError) as exc:
            print(f"fast_lane_benchmark_run_rejected={exc}")
            return 1
        print(json.dumps(report.model_dump(mode="json"), sort_keys=True, indent=2))
        return 0 if report.parity_report.status.value == "pass" else 1
    parser.error(f"unsupported fast-lane command: {args.fast_lane_command}")
    return 2


def _load_run_manifest(path: str) -> RunManifest:
    return RunManifest.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def _load_cost_model(path: str | None) -> CostModelConfig:
    if path is None:
        return CostModelConfig()
    return CostModelConfig.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def _load_replay_manifest_for_run(
    manifest: RunManifest,
    *,
    run_manifest_path: Path,
) -> dict[str, object]:
    replay_artifact = manifest.artifacts.get("replay_manifest")
    if replay_artifact is None:
        raise ValueError(f"run manifest is missing replay_manifest artifact: {run_manifest_path}")
    replay_path = (run_manifest_path.parent / replay_artifact.path).resolve()
    return json.loads(replay_path.read_text(encoding="utf-8"))


def _handle_strategy_spec(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.strategy_spec_command is None:
        parser.parse_args(["strategy-spec", "--help"])
        return 0
    if args.strategy_spec_command == "validate":
        payload = load_strategy_spec_file(args.spec_file)
        result = validate_strategy_spec(payload)
        print(f"strategy_spec_valid={str(result.ok).lower()}")
        if result.strategy_id:
            print(f"strategy_id={result.strategy_id}")
        if result.spec_hash:
            print(f"spec_hash={result.spec_hash}")
        for error in result.errors:
            print(f"error={error}")
        for warning in result.warnings:
            print(f"warning={warning}")
        return 0 if result.ok else 1
    if args.strategy_spec_command == "examples":
        examples = example_strategy_payloads()
        if args.strategy_id:
            if args.strategy_id not in examples:
                print("strategy_example_found=false")
                return 1
            print(json.dumps(examples[args.strategy_id], sort_keys=True, indent=2))
            return 0
        print(json.dumps(examples, sort_keys=True, indent=2))
        return 0
    if args.strategy_spec_command == "registry":
        print(json.dumps(registry_summary(), sort_keys=True, indent=2))
        return 0
    parser.error(f"unsupported strategy-spec command: {args.strategy_spec_command}")
    return 2


def _handle_ledger(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.ledger_command is None:
        parser.parse_args(["ledger", "--help"])
        return 0
    try:
        if args.ledger_command == "append":
            row = append_run_to_ledger(
                LedgerAppendRequest(
                    run_manifest_path=args.run,
                    ledger_path=args.ledger,
                    evidence_mode=args.evidence_mode,
                    notes=args.notes,
                    max_part_rows=args.max_part_rows,
                )
            )
            print(f"ledger_row_appended={row.run_id}")
            print(f"ledger_index={row.ledger_index}")
            print(f"row_status={row.row_status}")
            print(f"validation_status={row.validation_status}")
            return 0
        if args.ledger_command == "export":
            path = export_ledger(
                ledger_path=args.ledger,
                output_path=args.output,
                export_format=args.format,
            )
            print(f"ledger_export={path}")
            print(f"source_ledger={args.ledger}")
            print("generated_from_canonical=true")
            return 0
        if args.ledger_command == "compact":
            path = compact_ledger_parts(
                ledger_path=args.ledger,
                output_path=args.output,
            )
            print(f"ledger_compacted={path}")
            print(f"source_ledger={args.ledger}")
            print("generated_from_canonical=true")
            return 0
        if args.ledger_command == "leaderboard":
            rows = leaderboard(
                ledger_path=args.ledger,
                require_validation_pass=args.require_validation_pass,
                exclude_sandbox=args.exclude_sandbox,
                rank=args.rank,
            )
            for row in rows:
                print(
                    "\t".join(
                        [
                            str(row.rank),
                            row.run_id,
                            row.experiment_id,
                            row.strategy_id,
                            f"{row.net_return:.12f}",
                            f"{row.composite_score:.12f}",
                            row.validation_status,
                            row.evidence_mode,
                            str(row.trial_count),
                            str(row.fold_count),
                            "" if row.fold_stability_score is None else f"{row.fold_stability_score:.12f}",
                            str(row.overfit_warning).lower(),
                        ]
                    )
                )
            return 0
    except LedgerError as exc:
        print(f"ledger_rejected={exc}")
        return 1
    parser.error(f"unsupported ledger command: {args.ledger_command}")
    return 2


def _handle_lead(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.lead_command is None:
        parser.parse_args(["lead", "--help"])
        return 0
    store = LeadBookStore(args.lead_book)
    try:
        if args.lead_command == "create":
            lead = create_lead_from_source(
                source_artifact_path=args.source_artifact,
                source_type=args.source_type,
                strategy_family=args.strategy_family,
                economic_thesis=args.economic_thesis,
                created_by_id=args.created_by_id,
                instrument_scope=tuple(args.instruments),
                data_window_start=_parse_datetime(args.data_window_start),
                data_window_end=_parse_datetime(args.data_window_end),
                roi_observed=args.roi_observed,
                roi_projected=args.roi_projected,
                roi_projection_assumptions=args.roi_projection_assumptions,
                why_interesting=args.why_interesting,
                trade_count_summary={
                    "avg_trades_per_month": args.avg_trades_per_month,
                    "total_trades": args.total_trades,
                },
                monthly_stability_summary={
                    "usable_months": args.usable_months,
                    "losing_months_12m": args.losing_months_12m,
                    "positive_months_12m": args.positive_months_12m,
                },
                pnl_concentration_summary={
                    "top_2_trades_profit_share": args.top_2_trades_profit_share,
                    "best_month_profit_share": args.best_month_profit_share,
                },
            )
            store.upsert(lead)
            print(f"lead_id={lead.lead_id}")
            print(f"state={lead.state.value}")
            print(f"source_artifact_sha256={lead.source_artifact_sha256}")
            print("promotion_ready=false")
            return 0
        if args.lead_command == "list":
            for lead in store.list(state=args.state):
                print(
                    "\t".join(
                        [
                            lead.lead_id,
                            lead.state.value,
                            lead.strategy_family,
                            lead.human_inspection_status.value,
                            lead.agent_approval_status.value,
                            str(lead.promotion_ready).lower(),
                        ]
                    )
                )
            return 0
        if args.lead_command == "scan":
            result = scan_lead_book_queue(
                LeadBookScanConfig(
                    lead_book_path=args.lead_book,
                    output_path=args.output_path,
                    states=_parse_lead_scan_states(args.status),
                    max_rows=args.max_rows,
                )
            )
            print(f"lead_book_scan_manifest={result.scan_manifest_path}")
            print(f"scan_id={result.scan_id}")
            print(f"states={','.join(state.value for state in result.states)}")
            print(f"total_lead_count={result.total_lead_count}")
            print(f"matched_count={result.matched_count}")
            print(f"returned_count={result.returned_count}")
            print(f"blocker_count={len(result.blocker_reasons)}")
            for blocker in result.blocker_reasons:
                print(f"blocker={blocker}")
            print("accepted_research_ready=false")
            print("promotion_ready=false")
            return 0
        if args.lead_command == "inspect-request":
            lead = request_human_inspection(store.get(args.lead_id))
            store.upsert(lead)
            print(f"lead_id={lead.lead_id}")
            print(f"human_inspection_status={lead.human_inspection_status.value}")
            print(f"state={lead.state.value}")
            return 0
        if args.lead_command == "approve-after-human-inspection":
            notes = Path(args.inspection_note_file).read_text(encoding="utf-8")
            lead = complete_human_inspection(
                store.get(args.lead_id),
                inspected_by=args.approving_agent_id,
                notes=notes,
            )
            lead = approve_after_human_inspection(
                lead,
                approving_agent_id=args.approving_agent_id,
            )
            store.upsert(lead)
            print(f"lead_id={lead.lead_id}")
            print(f"human_inspection_status={lead.human_inspection_status.value}")
            print(f"agent_approval_status={lead.agent_approval_status.value}")
            print(f"state={lead.state.value}")
            return 0
    except (LeadBookError, ValueError, ValidationError) as exc:
        print(f"lead_rejected={exc}")
        return 1
    parser.error(f"unsupported lead command: {args.lead_command}")
    return 2


def _handle_audit(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.audit_command is None:
        parser.parse_args(["audit", "--help"])
        return 0
    if args.audit_command == "autonomous-readiness":
        try:
            report = run_autonomous_readiness_audit_from_file(
                args.evidence_file,
                output_path=args.output_path,
            )
        except (ValueError, ValidationError) as exc:
            print(f"autonomous_readiness_audit_rejected={exc}")
            return 1
        print(f"readiness_report={Path(args.output_path).resolve(strict=False)}")
        print(f"report_id={report.report_id}")
        print(f"status={report.status.value}")
        print(f"autonomous_research_ready={str(report.autonomous_research_ready).lower()}")
        print(f"blocker_count={report.blocker_count}")
        for blocker in report.blocker_reasons:
            print(f"blocker={blocker}")
        print("promotion_ready=false")
        if report.status == AutonomousReadinessStatus.AUTONOMOUS_RESEARCH_READY:
            return 0
        return 1
    parser.error(f"unsupported audit command: {args.audit_command}")
    return 2


def _handle_autopilot(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.autopilot_command is None:
        parser.parse_args(["autopilot", "--help"])
        return 0
    if args.autopilot_command == "fixture-cycle-spec":
        try:
            result = write_autopilot_fixture_cycle_spec(
                AutopilotFixtureCycleConfig(
                    output_root=args.output_root,
                    run_id=args.run_id,
                    instrument_id=args.instrument_id,
                    coin=args.coin,
                    start_ts=_parse_datetime(args.start_ts),
                    end_ts=_parse_datetime(args.end_ts),
                    asof_date=date.fromisoformat(args.asof_date),
                    created_by_id=args.created_by_id,
                )
            )
        except (argparse.ArgumentTypeError, ValueError, ValidationError) as exc:
            print(f"autopilot_fixture_cycle_spec_rejected={exc}")
            return 1
        print(f"cycle_spec={result.cycle_spec_path}")
        print(f"fixture_root={result.fixture_root}")
        print(f"universe_payload_file={result.universe_payload_file}")
        print(f"candle_records_file={result.candle_records_file}")
        print(f"archive_root={result.archive_root}")
        print(f"backtest_output_root={result.backtest_output_root}")
        print(f"ledger_path={result.ledger_path}")
        print(f"lead_book_path={result.lead_book_path}")
        print(f"suggested_plan_output_root={result.suggested_plan_output_root}")
        print(f"suggested_job_store={result.suggested_job_store_path}")
        print(f"declared_job_count={result.declared_job_count}")
        print(f"declared_binding_count={result.declared_binding_count}")
        for blocker in result.expected_audit_blockers:
            print(f"expected_audit_blocker={blocker}")
        print("evidence_mode=sandbox_diagnostic")
        print("accepted_research_ready=false")
        print("promotion_ready=false")
        return 0
    if args.autopilot_command == "public-candle-cycle-spec":
        try:
            config_payload = {
                "output_root": args.output_root,
                "run_id": args.run_id,
                "instrument_id": args.instrument_id,
                "coin": args.coin,
                "timeframe": args.timeframe,
                "start_ts": _parse_datetime(args.start_ts),
                "end_ts": _parse_datetime(args.end_ts),
                "created_by_id": args.created_by_id,
                "public_info_url": args.public_info_url,
                "public_info_timeout": args.public_info_timeout,
                "max_public_info_pages": args.max_public_info_pages,
                "max_candles_per_public_page": args.max_candles_per_public_page,
                "coverage_min": args.coverage_min,
            }
            if args.asof_date:
                config_payload["asof_date"] = date.fromisoformat(args.asof_date)
            result = write_autopilot_public_candle_cycle_spec(
                AutopilotPublicCandleCycleConfig(**config_payload)
            )
        except (argparse.ArgumentTypeError, ValueError, ValidationError) as exc:
            print(f"autopilot_public_candle_cycle_spec_rejected={exc}")
            return 1
        print(f"cycle_spec={result.cycle_spec_path}")
        print(f"archive_root={result.archive_root}")
        print(f"backtest_output_root={result.backtest_output_root}")
        print(f"ledger_path={result.ledger_path}")
        print(f"lead_book_path={result.lead_book_path}")
        print(f"suggested_plan_output_root={result.suggested_plan_output_root}")
        print(f"suggested_job_store={result.suggested_job_store_path}")
        print(f"public_info_url={result.public_info_url}")
        print(f"declared_job_count={result.declared_job_count}")
        print(f"declared_binding_count={result.declared_binding_count}")
        for blocker in result.expected_audit_blockers:
            print(f"expected_audit_blocker={blocker}")
        print("source_mode=public_api")
        print("evidence_mode=sandbox_diagnostic")
        print("accepted_research_ready=false")
        print("promotion_ready=false")
        return 0
    if args.autopilot_command == "archive-cycle-spec":
        try:
            config_payload = {
                "output_root": args.output_root,
                "run_id": args.run_id,
                "archive_root": args.archive_root,
                "strategy_root": args.strategy_root,
                "archive_snapshot_id": args.archive_snapshot_id,
                "universe_snapshot_id": args.universe_snapshot_id,
                "venue": args.venue,
                "instrument_id": args.instrument_id,
                "family": args.family,
                "timeframe": args.timeframe,
                "start_ts": _parse_datetime(args.start_ts),
                "end_ts": _parse_datetime(args.end_ts),
                "asof_date": date.fromisoformat(args.asof_date),
                "coverage_min": args.coverage_min,
                "strategy_max_files": args.strategy_max_files,
                "created_by_id": args.created_by_id,
                "strategy_family": args.strategy_family,
                "economic_thesis": args.economic_thesis,
                "lead_avg_trades_per_month": args.lead_avg_trades_per_month,
                "lead_total_trades": args.lead_total_trades,
                "lead_usable_months": args.lead_usable_months,
                "lead_losing_months_12m": args.lead_losing_months_12m,
                "lead_positive_months_12m": args.lead_positive_months_12m,
                "lead_top_2_trades_profit_share": args.lead_top_2_trades_profit_share,
                "lead_best_month_profit_share": args.lead_best_month_profit_share,
            }
            if args.requested_fields:
                config_payload["requested_fields"] = tuple(args.requested_fields)
            result = write_autopilot_archive_cycle_spec(
                AutopilotArchiveCycleConfig(**config_payload)
            )
        except (argparse.ArgumentTypeError, ValueError, ValidationError) as exc:
            print(f"autopilot_archive_cycle_spec_rejected={exc}")
            return 1
        print(f"cycle_spec={result.cycle_spec_path}")
        print(f"archive_root={result.archive_root}")
        print(f"strategy_root={result.strategy_root}")
        print(f"archive_snapshot_id={result.archive_snapshot_id}")
        print(f"universe_snapshot_id={result.universe_snapshot_id}")
        print(f"backtest_output_root={result.backtest_output_root}")
        print(f"ledger_path={result.ledger_path}")
        print(f"lead_book_path={result.lead_book_path}")
        print(f"suggested_plan_output_root={result.suggested_plan_output_root}")
        print(f"suggested_job_store={result.suggested_job_store_path}")
        print(f"declared_job_count={result.declared_job_count}")
        print(f"declared_binding_count={result.declared_binding_count}")
        for blocker in result.expected_audit_blockers:
            print(f"expected_audit_blocker={blocker}")
        print("source_mode=existing_ref")
        print("evidence_mode=accepted_research")
        print("accepted_research_ready=false")
        print("promotion_ready=false")
        return 0
    if args.autopilot_command == "strategy-queue-scan":
        try:
            result = scan_strategy_queue(
                StrategyQueueScanConfig(
                    strategy_root=args.strategy_root,
                    output_root=args.output_root,
                    run_id=args.run_id,
                    max_files=args.max_files,
                )
            )
        except (ValueError, ValidationError) as exc:
            print(f"autopilot_strategy_queue_scan_rejected={exc}")
            return 1
        print(f"strategy_queue_manifest={result.manifest_path}")
        print(f"manifest_id={result.manifest_id}")
        print(f"run_id={result.run_id}")
        print(f"item_count={result.item_count}")
        print(f"accepted_count={result.accepted_count}")
        print(f"rejected_count={result.rejected_count}")
        print(f"blocker_count={len(result.blocker_reasons)}")
        for blocker in result.blocker_reasons:
            print(f"blocker={blocker}")
        print(f"evidence_mode={result.evidence_mode}")
        print("accepted_research_ready=false")
        print("promotion_ready=false")
        return 0
    if args.autopilot_command == "research-cycle":
        try:
            config = load_autopilot_cycle_spec(args.cycle_spec_file)
            if args.max_jobs is not None:
                if args.max_jobs < 1:
                    raise AutopilotCyclePlanError("max_jobs must be positive")
                config = config.model_copy(update={"max_jobs": args.max_jobs})
            result = plan_autopilot_research_cycle(
                config,
                output_root=args.output_root,
                job_store_path=args.job_store,
                enqueue=args.enqueue,
            )
        except (AutopilotCyclePlanError, ValidationError) as exc:
            print(f"autopilot_research_cycle_rejected={exc}")
            return 1
        print(f"plan_manifest={result.plan_manifest_path}")
        print(f"plan_id={result.plan_id}")
        print(f"status={result.status.value}")
        print(f"planned_job_count={result.planned_job_count}")
        print(f"enqueued_job_count={result.enqueued_job_count}")
        print(f"audit_job_id={result.audit_job_id}")
        print(f"audit_report_path={result.audit_report_path}")
        print("accepted_research_ready=false")
        print("promotion_ready=false")
        return 0
    if args.autopilot_command == "run-cycle-plan":
        try:
            result = run_autopilot_cycle_plan(
                args.plan_manifest,
                job_store_path=args.job_store,
                worker_id=args.worker_id,
                max_jobs=args.max_jobs,
                run_audit_on_blocker=not args.no_audit_on_blocker,
            )
        except (AutopilotCycleRunnerError, ValidationError) as exc:
            print(f"autopilot_cycle_run_rejected={exc}")
            return 1
        print(f"execution_manifest={result.execution_manifest_path}")
        print(f"execution_id={result.execution_id}")
        print(f"status={result.status.value}")
        print(f"executed_job_count={result.executed_job_count}")
        print(f"skipped_job_count={result.skipped_job_count}")
        print(f"audit_attempted={str(result.audit_attempted).lower()}")
        print(f"audit_report_path={result.audit_report_path}")
        print(f"blocker_count={len(result.blocker_reasons)}")
        for blocker in result.blocker_reasons:
            print(f"blocker={blocker}")
        print("accepted_research_ready=false")
        print("promotion_ready=false")
        return 0
    if args.autopilot_command == "scheduler-tick":
        try:
            result = run_autopilot_scheduler_tick(
                plan_manifest_paths=tuple(args.plan_manifest),
                output_root=args.output_root,
                job_store_path=args.job_store,
                worker_id=args.worker_id,
                scheduler_id=args.scheduler_id,
                max_plans=args.max_plans,
                max_jobs_per_plan=args.max_jobs_per_plan,
                run_audit_on_blocker=not args.no_audit_on_blocker,
            )
        except (AutopilotSchedulerError, ValidationError) as exc:
            print(f"autopilot_scheduler_tick_rejected={exc}")
            return 1
        print(f"scheduler_manifest={result.scheduler_manifest_path}")
        print(f"session_id={result.session_id}")
        print(f"status={result.status.value}")
        print(f"executed_plan_count={result.executed_plan_count}")
        print(f"blocker_count={len(result.blocker_reasons)}")
        for blocker in result.blocker_reasons:
            print(f"blocker={blocker}")
        print("accepted_research_ready=false")
        print("promotion_ready=false")
        return 0
    parser.error(f"unsupported autopilot command: {args.autopilot_command}")
    return 2


def _handle_autonomy(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.autonomy_command is None:
        parser.parse_args(["autonomy", "--help"])
        return 0
    if args.autonomy_command == "dry-run":
        try:
            result = run_autonomy_dry_run(
                AutonomyDryRunConfig(
                    output_root=args.output_root,
                    run_id=args.run_id,
                    strategy_id=args.strategy_id,
                    data_mode=args.data_mode,
                    created_by_id=args.created_by_id,
                )
            )
        except (AutonomyLoopError, ValidationError) as exc:
            print(f"autonomy_dry_run_rejected={exc}")
            return 1
        print(f"autonomy_manifest={result.manifest_path}")
        print(f"blocker_report={result.blocker_report_path}")
        print(f"ledger_path={result.ledger_path}")
        print(f"lead_book_path={result.lead_book_path}")
        print(f"backtest_run_dir={result.backtest_run_dir}")
        print(f"status={result.status.value}")
        print("evidence_mode=sandbox_diagnostic")
        print("promotion_ready=false")
        return 0
    if args.autonomy_command == "agent-context":
        try:
            context = build_autonomous_research_agent_context(
                repo_root=args.repo_root,
                run_id=args.run_id,
                asof_date=date.fromisoformat(args.asof_date) if args.asof_date else None,
            )
            if args.output_path:
                write_autonomous_research_agent_context(context, args.output_path)
        except (ValueError, ValidationError) as exc:
            print(f"autonomy_agent_context_rejected={exc}")
            return 1
        print(agent_context_to_json(context), end="")
        return 0
    parser.error(f"unsupported autonomy command: {args.autonomy_command}")
    return 2


def _handle_ui(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.ui_command is None:
        parser.parse_args(["ui", "--help"])
        return 0
    if args.ui_command == "render":
        try:
            snapshot_path = resolve_within_root(args.input_root, args.snapshot_json)
            snapshot = snapshot_from_json(snapshot_path.read_text(encoding="utf-8"))
            output_path = write_visibility_html(
                snapshot,
                output_root=args.output_root,
                output_path=args.output_html,
            )
        except (OSError, ValueError) as exc:
            print(f"ui_render_rejected={exc}")
            return 1
        print(f"ui_html={output_path}")
        print(f"snapshot_id={snapshot.snapshot_id}")
        print("read_only=true")
        print("promotion_ready=false")
        return 0
    parser.error(f"unsupported ui command: {args.ui_command}")
    return 2


def _handle_worker(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.worker_command is None:
        parser.parse_args(["worker", "--help"])
        return 0
    store = WorkerJobStore(Path(args.job_store))
    if args.worker_command == "init":
        store.initialize()
        print(f"job_store_initialized={Path(args.job_store)}")
        return 0
    if args.worker_command == "enqueue":
        spec = _load_worker_input_spec(args)
        record = store.enqueue(
            kind=WorkerJobKind(args.kind),
            input_spec=spec,
            job_id=args.job_id,
            max_attempts=args.max_attempts,
        )
        print(f"job_id={record.job_id}")
        print(f"kind={record.kind.value}")
        print(f"status={record.status.value}")
        print(f"input_spec_hash={record.input_spec_hash}")
        return 0
    if args.worker_command == "run":
        try:
            result = run_one_job(
                store=store,
                kind=WorkerJobKind(args.kind),
                worker_id=args.worker_id,
                forbid_asgi=args.forbid_asgi,
            )
        except RuntimeError as exc:
            print(f"worker_run_rejected={exc}")
            return 1
        if result is None:
            print("job_found=false")
            return 0
        print(f"job_id={result.job_id}")
        print(f"status={result.status.value}")
        print(f"output_refs={','.join(result.output_refs)}")
        print(f"archive_manifest_refs={','.join(result.archive_manifest_refs)}")
        print(f"gap_record_ids={','.join(result.gap_record_ids)}")
        if result.failure_reason:
            print(f"failure_reason={result.failure_reason}")
        return 0 if result.status == WorkerJobStatus.SUCCEEDED else 1
    if args.worker_command == "status":
        if args.job_id:
            record = store.load_job(args.job_id)
            if record is None:
                print("job_found=false")
                return 1
            _print_worker_job(record)
            return 0
        for record in store.list_jobs(kind=args.kind, status=args.status):
            _print_worker_job(record)
        return 0
    if args.worker_command == "retry":
        record = store.retry_job(args.job_id, worker_id=args.worker_id)
        _print_worker_job(record)
        return 0
    if args.worker_command == "cancel":
        record = store.cancel_job(args.job_id, worker_id=args.worker_id)
        _print_worker_job(record)
        return 0
    if args.worker_command == "heartbeat":
        heartbeat = store.heartbeat(args.job_id, worker_id=args.worker_id)
        print(f"heartbeat_id={heartbeat.heartbeat_id}")
        print(f"job_id={heartbeat.job_id}")
        print(f"status={heartbeat.status.value}")
        return 0
    if args.worker_command == "mark-stale":
        stale = store.mark_stale_jobs(
            stale_after=timedelta(seconds=args.stale_after_seconds),
            worker_id=args.worker_id,
        )
        print(f"stale_count={len(stale)}")
        for record in stale:
            _print_worker_job(record)
        return 0
    parser.error(f"unsupported worker command: {args.worker_command}")
    return 2


def _load_worker_input_spec(args: argparse.Namespace) -> dict:
    if args.input_spec_file:
        return json.loads(Path(args.input_spec_file).read_text(encoding="utf-8"))
    if args.input_spec_json:
        return json.loads(args.input_spec_json)
    return {}


def _print_worker_job(record) -> None:
    print(
        "\t".join(
            [
                record.job_id,
                record.kind.value,
                record.status.value,
                str(record.attempts),
                str(record.terminal_state).lower(),
                record.failure_reason or "",
                ",".join(record.archive_manifest_refs),
            ]
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
