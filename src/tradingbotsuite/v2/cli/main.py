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
from tradingbotsuite.v2.autonomy import (
    AutopilotCyclePlanError,
    AutopilotCycleRunnerError,
    AutopilotFixtureCycleConfig,
    load_autopilot_cycle_spec,
    plan_autopilot_research_cycle,
    run_autopilot_cycle_plan,
    AutonomyDryRunConfig,
    AutonomyLoopError,
    run_autonomy_dry_run,
    write_autopilot_fixture_cycle_spec,
)
from tradingbotsuite.v2.backtest_data import (
    BacktestDataError,
    BacktestDataRequest,
    BacktestDataService,
    BacktestEvidenceMode,
)
from tradingbotsuite.v2.config.schemas import (
    BOUNDED_CONTEXTS,
    RESEARCH_BOUNDARY,
    V2_SCHEMA_VERSION,
)
from tradingbotsuite.v2.data_quality.checks import build_quality_checks
from tradingbotsuite.v2.data_quality.coverage import coverage_report_for_bars
from tradingbotsuite.v2.data_quality.reports import CoverageManifestStore
from tradingbotsuite.v2.data_quality.schemas import DEFAULT_COVERAGE_MIN, EvidenceMode
from tradingbotsuite.v2.ledger import (
    LedgerAppendRequest,
    LedgerError,
    append_run_to_ledger,
    export_ledger,
    leaderboard,
)
from tradingbotsuite.v2.lead_book import (
    LeadBookError,
    LeadBookStore,
    approve_after_human_inspection,
    complete_human_inspection,
    create_lead_from_source,
    request_human_inspection,
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
    ledger_export = ledger_subparsers.add_parser(
        "export",
        help="generate CSV/XLSX from canonical Parquet ledger",
    )
    ledger_export.add_argument("--ledger", required=True, help="canonical Parquet ledger path")
    ledger_export.add_argument("--format", required=True, choices=["csv", "xlsx"])
    ledger_export.add_argument("--output", required=True)
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
    if args.command == "universe":
        return _handle_universe(args, parser)
    if args.command == "data":
        return _handle_data(args, parser)
    if args.command == "backtest-data":
        return _handle_backtest_data(args, parser)
    if args.command == "strategy-spec":
        return _handle_strategy_spec(args, parser)
    if args.command == "ledger":
        return _handle_ledger(args, parser)
    if args.command == "lead":
        return _handle_lead(args, parser)
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
    except LeadBookError as exc:
        print(f"lead_rejected={exc}")
        return 1
    parser.error(f"unsupported lead command: {args.lead_command}")
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
