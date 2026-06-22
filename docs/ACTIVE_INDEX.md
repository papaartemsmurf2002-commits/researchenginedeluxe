# Active Index

Last updated: 2026-06-22

This is the first file to read after `AGENTS.md`.

## Immediate Next-Agent Handoff

- Read `docs/audit/V2_COMPLETION_AUDIT_ISSUES_AND_HOLES_2026_06_21.md`,
  `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`,
  `docs/V2_FUTURE_UI_DEFERRAL.md`, `docs/PRODUCT_SCOPE.md`,
  `docs/V2_DECISION_REGISTER.md`, `docs/V2_NO_TOUCH_PATHS.md`,
  `docs/audit/V2_AUDIT_INDEX.md`, and
  `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md` before v2 implementation
  work. WPR106-391 through WPR106-416 implement the v2 roadmap phases, map M0
  through M5, and add Phase 22 as a read-only static visibility UI rather than
  a legacy GUI rewrite or job-running UI process. WPR106-417 records the
  follow-up completion-audit issues, holes, validation limitations, and
  concerns; it does not change the research-only boundary or stage-gate status.
  WPR106-418 stabilizes the v2 foundation baseline at
  `9bea1b87025fb8b17df54362101b6d3ffb0213d6` after WPR106-419 closes two P1
  boundary findings in official-file source handling and signal-bearing
  artifact invariants. The foundation is committed but is not autonomous-ready:
  WPR106-420 installs local Python 3.11 dev dependencies, proves 3.11 v2 and
  contract suites pass, and fixes deterministic v2 worker transition ordering,
  but monolithic full-suite authoritative validation remains blocked by
  `ISSUE-R106-026` on this Windows/Python 3.11.0 host. WPR106-421 resolves
  `ISSUE-R106-020` by tightening latest-window strategy gates, GMM detector
  metadata, lower-frame no-hit proof, exit-policy alias artifacts, static
  barrier canonical identity, and timestamped funding-path costs. WPR106-422
  adds `redx autonomy dry-run`, a fixture-backed sandbox loop that writes an
  autonomy manifest, blocker report, ledger row, and non-promotable Lead Book
  row while proving the wiring remains research-only. It is not accepted
  research evidence and it explicitly reports real Hyperliquid archive
  operation as a blocker. WPR106-423 upgrades that dry-run so the default path
  creates a local archive root, silver bars, coverage report, archive snapshot,
  fixture as-of universe, and `BacktestDataService` manifest before the
  backtest, while still staying `sandbox_diagnostic`. WPR106-424 adds a
  central v2 research-boundary policy and migrates autonomy, backtest,
  backtest-data, ledger, Lead Book, and strategy/signal artifacts to use it.
  WPR106-425 makes durable recent-candle and funding collector jobs write
  local source records into raw, bronze, and silver archive artifacts, with
  candle coverage/snapshot refs and funding interval evidence, while keeping
  no-record API-cap diagnostics explicit. WPR106-426 adds trusted local
  `records_file` intake for those collector jobs, bounded to a declared source
  root with JSON/JSONL parsing, unsafe-file rejection, source SHA-256 refs, and
  fail-before-archive behavior for rejected files. WPR106-427 wires the
  existing `coverage_audit` worker kind to durable archive-backed coverage and
  quality manifest writes for silver bars, with blocker evidence surfaced
  through worker output refs. WPR106-428 wires durable
  `vectorized_backtest` jobs through the worker runner using inline
  declarative strategy specs and archive-backed `BacktestDataService` panels,
  returning run-manifest, data-manifest, coverage, archive-snapshot, and
  universe-snapshot refs without adding paper/live/order/sizing/runtime or
  promotion behavior. WPR106-429 wires durable `ledger_append_export` jobs
  through the worker runner so backtest run manifests append through the
  canonical Parquet ledger and optionally produce generated CSV/XLSX views,
  with secret-like output paths rejected before writes. WPR106-430 wires
  durable `lead_book_upsert` jobs through the worker runner so ledger-backed
  source artifacts can create or replace non-promotable Lead Book rows through
  the canonical Lead Book service, optionally emitting generated CSV views,
  with secret-like output paths and boundary override attempts rejected before
  writes. WPR106-431 wires the existing durable `audit_check` worker kind so
  job-store evidence can produce research-only JSON blocker reports with failed,
  incomplete, gap, blocker, known-blocker, and missing-evidence refs surfaced
  explicitly while keeping `accepted_research_ready=false`. WPR106-432 makes
  Hyperliquid universe refresh support an explicit unsigned public
  `source=public_api` mode with venue raw-request/raw-response provenance,
  requires durable worker/CLI callers to declare either `payload_file` or
  `public_api`, and records an optional successful live public-info smoke into
  a temporary archive. WPR106-433 adds explicit public Hyperliquid
  `candleSnapshot` intake for durable `recent_candle_bootstrap` jobs, writing
  raw, bronze, silver, coverage, and optional snapshot refs with raw
  request/response provenance while recording the documented recent-window cap.
  WPR106-434 adds paginated public Hyperliquid `fundingHistory` intake for
  durable `funding_backfill` jobs, writing raw, bronze, and silver funding refs
  with per-page request/response provenance. WPR106-435 adds public Hyperliquid
  `l2Book` snapshot intake for durable BBO/L2 microstructure capture jobs,
  writing raw-capture, quality, and storage refs while labeling the path as
  one-shot snapshot intake only. WPR106-436 adds bounded public Hyperliquid
  WebSocket `trades` snapshot intake for durable trade microstructure capture
  jobs, writing raw-capture, quality, and storage refs with message/row/time
  caps. WPR106-437 resolves `ISSUE-R106-029` by replacing eager data-quality
  and archive package exports with lazy export shims and proving direct
  `WorkerJobStore` imports work in a fresh interpreter. WPR106-438 extends the
  durable `coverage_audit` worker so a silver archive snapshot can be audited
  against a universe snapshot, writing one report per eligible instrument and
  surfacing missing silver bars as blocker evidence. WPR106-439 adds bounded
  public `candleSnapshot` pagination for recent-window candle archive intake
  with page-cap failure and per-page provenance. WPR106-440 makes
  Hyperliquid `official_s3_backfill` jobs classify trusted local official
  historical files, allow documented raw L2/asset-context/node-fill scopes, and
  reject unsupported official candle/OHLCV claims before archive writes.
  WPR106-441 adds trusted local decompressed official `l2Book` JSON/JSONL
  replay into BBO/L2 microstructure archive rows, with source hash, dataset
  scope, and non-continuous-coverage caveats. WPR106-442 adds trusted local
  decompressed official `asset_ctxs` JSON/JSONL replay into raw, bronze, and
  silver `asset_contexts` archive rows, with source hash, dataset scope,
  normalization refs, and non-continuous-coverage caveats. WPR106-443 adds
  trusted local decompressed official `node_fills_by_block`, `node_fills`, and
  legacy `node_trades` JSON/JSONL replay into raw trade microstructure rows,
  with instrument filtering, source hash, dataset scope, quality/storage refs,
  and coverage-certification caveats. WPR106-444 adds timestamp-bucket
  coverage audits for raw `trades`, raw `bbo`, raw `l2`, and silver
  `asset_contexts` files, including archive-snapshot plus universe-snapshot
  missing-file blocker evidence, while keeping raw microstructure coverage
  non-evidence by default. WPR106-445 adds bounded local WebSocket candle batch
  archive writes for durable `websocket_capture` jobs with explicit candle
  datatype plus `records` or trusted `records_file`, returning raw/bronze/
  silver/coverage/snapshot refs and bounded-batch caveats while preserving
  generic WebSocket gap-record behavior. WPR106-446 extends durable
  `audit_check` blocker reports with required successful job-kind and required
  artifact-ref-prefix checks, so absent universe/archive/coverage/backtest/
  ledger/Lead Book evidence becomes explicit `missing_evidence:*` blocker
  output. WPR106-447 adds optional required job-kind ordering to those reports,
  so selected successful loop stages must also form a nondecreasing
  `finished_at` chain when the manager declares `required_job_kind_order`;
  missing timestamps and out-of-order stages remain blocker evidence, not
  worker-system failures or readiness claims. WPR106-448 adds bounded public
  Hyperliquid WebSocket `candle` snapshot intake for durable
  `websocket_capture` candle jobs, writing raw/bronze/silver/coverage and
  optional snapshot refs with public WebSocket request/response provenance,
  while explicitly keeping `continuous_capture=false` and
  `accepted_historical_coverage_proof=false`. WPR106-449 adds bounded public
  Hyperliquid WebSocket `bbo` and `l2Book` snapshot intake for durable
  `websocket_l2_bbo_capture` BBO/L2 jobs, writing raw microstructure capture,
  quality, and storage refs with public WebSocket request/response provenance,
  while explicitly keeping `continuous_capture=false` and
  `accepted_historical_coverage_proof=false`. WPR106-450 adds opt-in
  `capture_mode=unattended_session` evidence for bounded public WebSocket
  candle, trade, BBO, and L2 capture segments, including session heartbeats and
  JSON capture-session reports under archive manifests, while still keeping
  accepted historical coverage proof false. WPR106-451 adds a bounded
  `redx autopilot research-cycle --mode bounded` plan/enqueue surface that
  validates an ordered durable loop spec, optionally enqueues declared worker
  jobs, and appends a generated final `audit_check` job with required
  successful job-kind, artifact-prefix, and ordering checks. It does not run
  jobs, call venues, stream WebSockets, certify coverage, or claim
  autonomous-ready status. WPR106-452 adds
  `redx autopilot run-cycle-plan`, a bounded operator-invoked executor for an
  already enqueued plan. It skips already successful planned jobs, runs planned
  queued jobs only when they are next for their worker kind, records execution
  blockers, and attempts the generated final `audit_check` job so the cycle
  writes a blocker report. It does not add a daemon scheduler, direct venue
  calls, direct WebSocket control, coverage certification, accepted evidence,
  autonomous-ready status, or paper/live/order/sizing/runtime/promotion
  behavior. WPR106-453 adds planner-declared output-ref bindings so an
  enqueued bounded cycle can pass earlier successful worker refs into later
  still-queued planned job input specs before execution. Bindings are
  validated as source-before-target, reject research-boundary targets, update
  only queued jobs with worker transition evidence, and turn missing or
  ambiguous refs into blockers. This does not infer readiness, mutate terminal
  evidence, or add paper/live/order/sizing/runtime/promotion behavior.
  WPR106-454 adds `redx autopilot fixture-cycle-spec`, a generated
  sandbox-diagnostic bounded-cycle fixture that can be planned, enqueued, and
  run through the real durable worker chain from universe refresh through
  archive, coverage, backtest, ledger, Lead Book, and generated audit report.
  The fixture intentionally ends with sandbox/missing-real-evidence blockers
  and remains operational wiring evidence only, not accepted research evidence
  or autonomous-ready proof. Full historical candle coverage beyond the public
  recent-window limit, long-running scheduler/daemon capture, accepted
  continuous historical trade/L2 coverage proof, independent audits,
  real-archive loop acceptance,
  and authoritative full-suite proof remain follow-up work.
  WPR106-455 adds `redx audit autonomous-readiness`, a deterministic
  manager-gate report that consumes checklist evidence plus cycle, final audit,
  ledger, and Lead Book artifacts. Missing or failed evidence becomes an
  explicit blocker report; the command does not collect data, certify strategy
  quality, create accepted evidence, or add candidate/paper/live/order/sizing/
  runtime/promotion behavior.
  WPR106-456 adds `redx autopilot public-candle-cycle-spec`, a public API
  diagnostic bounded-cycle spec writer for current Hyperliquid universe and
  candle intake through the durable worker loop. The command writes a spec
  only; it does not run network calls, enqueue jobs, certify historical
  coverage, or claim readiness, and the generated Lead Book step carries
  public-current-universe/recent-window/coverage/audit/validation blockers.
  WPR106-457 adds `redx autopilot strategy-queue-scan`, a bounded local
  declarative-spec scanner that validates JSON/YAML strategy specs, writes
  normalized accepted copies, and records invalid/unsupported/secret-like
  blockers in a queue manifest. The manifest is input hygiene only and is not
  job execution, strategy performance, accepted research evidence, or
  autonomous-ready proof. WPR106-458 adds a durable
  `validation_gate` worker that reads completed run manifests plus fold and
  cost-stress artifacts, writes `validation_gate_manifest.json`, and reports
  validation blockers before ledger/Lead Book interpretation. It is a
  validation-stage worker output only, not accepted evidence or readiness
  certification. WPR106-459 wires that worker into bounded autopilot cycle
  planning and generated fixture/public cycle specs as a required stage after
  vectorized backtest and before ledger/Lead Book interpretation. The generated
  audit job now requires validation manifest refs and loop order evidence, but
  cycle plans/executions still remain operational evidence only, not accepted
  research evidence or autonomous-ready proof. WPR106-460 adds durable
  `strategy_queue_scan` worker routing and SHA-checked `strategy_spec_file`
  intake for durable vectorized backtests. Queue workers expose normalized
  accepted spec path/SHA refs only when exactly one spec is accepted; backtest
  workers reject missing/mismatched/secret-like/unsupported file intake before
  panel loads and still validate loaded declarative specs before run artifacts.
  This is trusted input plumbing only, not strategy performance, accepted
  research evidence, or autonomous-ready proof. WPR106-461 wires that queue
  worker into bounded autopilot plans and generated fixture/public cycle specs:
  `strategy_queue_scan` is required after coverage and before backtest, the
  generated audit job requires queue manifest/spec refs, and generated cycles
  bind accepted spec path/SHA refs into backtests instead of using inline specs.
  Cycle plans/executions remain operational evidence only, not accepted research
  evidence or autonomous-ready proof. WPR106-462 tightens the autonomous
  readiness manager gate so it now blocks stale cycle/final-audit evidence that
  omits the `strategy_queue_scan` or `validation_gate` stages, or that lacks
  queue manifest, accepted-spec path/SHA, strategy hash, validation manifest,
  ledger, and Lead Book artifact-ref requirements. This is still a blocker
  gate only, not accepted research evidence or autonomous-ready proof.
  WPR106-463 adds `redx autopilot scheduler-tick`, a run-once bounded manager
  surface that selects explicit already-enqueued cycle plan manifests under
  max-plan and max-job budgets, delegates selected plans to the existing
  durable cycle runner, defers excess plans as blocker evidence, and writes a
  research-only scheduler session manifest. It is not a daemon, venue fetch
  bypass, ASGI/operator in-process job loop, accepted research evidence, or
  autonomous-ready proof. Independent WPR106-463 audit found no P0/P1 findings,
  and WPR106-465 closes the P2 follow-up with focused missing-manifest and
  max-jobs-per-plan scheduler blocker regressions. WPR106-464 adds `redx
  leadbook scan --status ...`, a read-only multi-state Lead Book queue scan
  that writes a research-only JSON manifest from the canonical Lead Book,
  reports missing or empty queues as blocker evidence, and does not mutate lead
  states, enqueue jobs, run backtests, or imply accepted/autonomous/candidate/
  paper/live/sizing/runtime/promotion readiness.
- Read `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md` before planning
  more legacy sandbox feature work. It remains useful historical transition
  guidance and makes repo-state stabilization mandatory before the
  materializer, dashboard, strict-validation bridge, or performance work.
- Read `docs/RESEARCH_ROADMAP_DIRECTION_COMPARISON_2026_06_20.md` when
  evaluating the imported v2 multi-venue Hyperliquid-perp roadmap in
  `docs/RESEARCH_ENGINE_DELUXE_V2_MULTI_VENUE_PERP_RESEARCH_ROADMAP.md`.
  WPR106-388 and WPR106-389 are source/reference packages. WPR106-391 is the
  later packet that changes the active canonical identity and Phase 0 docs,
  without claiming implementation evidence.
- Read `docs/SANDBOX_FIRST_LOOK_RECOMMENDATIONS.md` before resuming sandbox
  development. It is a first-look recommendation memo, not an implementation
  guideline. It recommends audit-first posture before continuing the
  materializer or other new feature work.
- Read `docs/NEXT_AGENT_HANDOFF_WPR106_358_SANDBOX_SELF_AUDIT.md` before
  opening the next sandbox development packet. It is the self-audit that
  shaped WPR106-359 through WPR106-371; the materializer, venue candidate
  manifest, fixture smoke, strict-validation descriptor preflight, and
  next-action dashboard packets are now closed. WPR106-372 also adds
  measurement-only throughput telemetry and reports. WPR106-373 closes the
  explicitly scoped `signal_bar_close_plus_latency` backtest compatibility
  drift by restoring signal-close pricing and adding
  `primary_bar_open_plus_latency` for primary-open latency fills. WPR106-374
  closes the sandbox catalog `exit_profile` drift by requiring non-default
  row-level exit profiles to match declared run-spec exit variants or fail
  closed in preflight/execution. WPR106-375 adds bounded ZIP/TAR container
  loader guards for selected member count, raw member bytes, total selected
  bytes, and gzip decompression bytes; it is a blocker-surfacing guardrail, not
  a full streaming throughput claim. WPR106-376 repairs deterministic test
  fixture ZIP payload generation so archive checksum tests reach their intended
  quality gates. WPR106-377 stages the classified sandbox package, sandbox
  tests, smoke config, and sandbox contract so tracked CLI imports no longer
  depend on an untracked sandbox package, and removes tracked `.pytest_cache`
  entries from the index only. WPR106-378 closes the remaining workbook intake
  M2/M9 gap by making legacy `.xls` catalogs explicitly unsupported and bounding
  the standard-library `.xlsx` fallback parser. WPR106-379 closes the M5
  source-discovery cost gap for strategy catalog materialization, archive
  manifest building, and global leaderboard run discovery by replacing
  full-tree recursive sorting with deterministic bounded traversal. WPR106-380
  closes the H10 CI coverage gap by adding `tests/research_sandbox` and
  `tests/live/test_cli_boundary.py` to the research-validation workflow.
  WPR106-381 improves the next-action dashboard's first-read behavior by
  recommending iteration indexing and listing exact
  `sandbox_iteration_manifest.json` files when an iteration exists but no
  artifact catalog or iteration index has been built yet. WPR106-382 closes the
  sandbox CLI publication-coherence gap by staging sandbox-only canonical CLI
  parser/dispatch additions, research-command registry entries, and live CLI
  boundary tests while leaving unrelated four-bar KNN command work unstaged.
  WPR106-383 resolves the broad-suite timeout by bounding historical fixture
  cycle smoke tests that were executing production-sized checked-in specs; the
  full suite now passes locally with 1890 passed, 1 skipped, and 1 XGBoost
  device warning. WPR106-384 closes the sandbox package-root import coupling
  gap by preserving package-root exports through lazy module resolution instead
  of importing the full sandbox graph at root import time. WPR106-385 reduces
  the H9 descriptor-routed archive-sweep memory pressure by loading descriptor
  market frames sequentially and applying global ranking after collection.
  WPR106-386 reduces the H9 dense barrier-exit memory pressure by batching
  primary-bar target/stop window matrices while preserving existing
  target-only, stop-only, and conservative target/stop semantics. WPR106-387
  reduces the H9 proxy-signal memory pressure by materializing identical
  blueprint proxy signals into shared canonical market-frame columns for
  execution/preflight while preserving original strategy descriptors and trial
  identity inputs.
  Treat remaining roadmap work as newly discovered blocker repairs, broader
  inherited publication cleanup, and performance proof rather than as a request
  to rerun the completed materializer sequence.

## Canonical Identity

ResearchEngineDeluxe v2 is a research-only, data-first, multi-instrument
perpetual-futures research platform. The active default direction is
Hyperliquid-first: instruments above USD 5,000,000 daily notional volume,
owned archives, as-of universe snapshots, 2024+ evidence, 6+ usable months,
12-month preference, 0.98 coverage, dynamic lockbox exclusion, declarative
strategy evaluation, append-only experiment ledger, Lead Book, and
audit-by-chunk migration.

BTC and ETH remain fixture, smoke-test, reference, and legacy evidence symbols.
They are not the full v2 product scope.

The product surface is research evidence, not live execution. It produces
manifests, metrics, rejections, ablations, multiple-testing evidence,
validation-floor evidence, lead diagnostics, audit records, and operator
visibility. It does not produce live signals, paper signals, order-placement
instructions, sizing instructions, runtime-mode changes, candidate-pack
promotion, or promotion authorization.

The Python package name remains `tradingbotsuite` for compatibility. Treat that
as an implementation detail unless a future package-rename packet scopes a
rename.

## Current Checkout

- Local checkout: `main`.
- Stage role: migrated mirror of `research/v3-experimental-engine`.
- Live runtime branch referenced by older docs: `live/v1-runtime-hardening`.
- WPR106-46 through WPR106-54 were merged through PR #2, and the merged
  `codex/wpr106-46-exact-replay-overlay` and
  `codex/wpr106-47-full-replay-exit-lab-controls` branch refs were deleted
  locally and on `origin`.
- Current git state after local WPR106-57 through WPR106-66 follow-up work:
  uncommitted operator/research UI, autopilot, documentation, and test changes
  are present. Preserve unrelated local edits.
- Current git state after local WPR106-220 through WPR106-226 follow-up work:
  2024-forward research artifacts remain research-only and no candidate pack
  exists. WPR106-226 reconstructed NUL-filled WPR106-220 through WPR106-225
  packet/report markdown from preserved JSON, Parquet, and ledger evidence and
  added the current results/leads catalog.
- Current git state after local WPR106-228 follow-up work: the first isolated
  Rapid Strategy Iteration Sandbox foundation exists under
  `src/tradingbotsuite/research_sandbox/`. It is an idea-triage layer only:
  sandbox outputs and evidence requests are research-only, observe-only,
  `promotion_ready: false`, `candidate_evidence: false`, and
  `candidate_pack_eligible: false`.
- Current git state after local WPR106-229 follow-up work:
  `run-rapid-strategy-sandbox` is available as a research CLI command for
  local 2024+ sandbox sweeps from strategy catalogs, venue archive descriptors,
  and local CSV/TSV/JSON/JSONL/Parquet or Binance Vision kline CSV/ZIP market
  data. It writes only sandbox manifests, Parquet summaries/rankings, and
  evidence-request descriptors under the configured research output root.
- Current git state after local WPR106-230 follow-up work: sandbox strategy
  intake can compile existing repo strategy JSON configs and spreadsheet-like
  lead catalogs into deterministic static blueprint proxy rows. Blueprint
  signals are materialized only after the 2024+ sandbox market window is
  applied, and outputs remain sandbox-only, research-only, non-promotable, and
  ineligible for candidate packs.
- Current git state after local WPR106-231 follow-up work: sandbox sweeps now
  include bounded exit/filter grids. Run specs can declare fixed-hold,
  target-only, stop-only, and conservative target/stop exit variants plus
  completed-row filter variants; exit/filter payloads are included in trial
  identity and remain sandbox-only evidence-request material.
- Current git state after local WPR106-232 follow-up work: sandbox archive
  sweeps can route multiple venue descriptors to distinct local `data_path`
  market frames in one run, rank the combined results globally, and record
  market-source metadata for OKX/Bybit/Hyperliquid/Binance/local descriptor
  inputs. Shared `--market-data` remains available for smoke runs only.
- Current git state after local WPR106-233 follow-up work:
  `summarize-rapid-strategy-sandbox` summarizes existing sandbox run
  artifacts under the research output root, writes `analysis_summary.json`, and
  reports status, venue, family, exit/filter, rejection, top-row, and
  evidence-request summaries while preserving sandbox-only non-promotable
  boundary flags.
- Current git state after local WPR106-234 follow-up work:
  `run-rapid-strategy-sandbox-suite` runs multiple sandbox cases from one suite
  spec, resolves case paths relative to the suite file, writes suite-level
  JSON/Parquet indexes and aggregated evidence-request descriptors under the
  research output root, and preserves sandbox-only non-promotable boundary
  flags.
- Current git state after local WPR106-235 follow-up work:
  `summarize-rapid-strategy-sandbox-hypotheses` writes run-level or suite-level
  hypothesis falsification JSON/Parquet indexes. The indexes group sandbox rows
  by hypothesis, record best trial metrics and tested venues/exits/filters,
  distinguish blocked, falsified, mixed, screened-positive, and
  strict-validation-requested outcomes, and remain sandbox-only non-promotable
  analysis artifacts.
- Current git state after local WPR106-236 follow-up work:
  `export-rapid-strategy-sandbox-validation-requests` writes descriptor-only
  strict-validation request bundles from sandbox run or suite evidence requests.
  Bundles dedupe requests, name `run-historical-research-cycle` as the later
  strict validation entrypoint, preserve source metrics/provenance, and do not
  execute validation or write candidate artifacts.
- Current git state after local WPR106-237 follow-up work:
  `index-rapid-strategy-sandbox-artifacts` scans known sandbox JSON artifacts
  under the research output root, validates sandbox boundary flags, and writes
  compact JSON/Parquet catalogs covering runs, suites, analysis reports,
  hypothesis falsification indexes, and strict-validation request bundles.
- Current git state after local WPR106-238 follow-up work:
  `audit-rapid-strategy-sandbox-archives` audits venue archive descriptors and
  local market data paths before sweeps, reporting 2024+ normalized/window row
  coverage, OHLC availability, routing mode, and blocker/warning reasons while
  preserving sandbox-only non-promotable flags.
- Current git state after local WPR106-239 follow-up work:
  `build-rapid-strategy-sandbox-archive-manifest` builds loadable
  `venue_archives.json` files from local 2024+ archive roots, infers or
  overrides descriptor identity, reports skipped files with reasons, and writes
  deterministic sandbox-only manifest/build-report artifacts for agent
  preflight loops.
- Current git state after local WPR106-240 follow-up work:
  `rank-rapid-strategy-sandbox-artifacts` scans existing sandbox run artifacts
  under the research output root and writes global hypothesis/family
  leaderboard JSON/Parquet reports across runs, venues, exits, and filters
  while preserving sandbox-only non-promotable flags.
- Current git state after local WPR106-241 follow-up work:
  `build-rapid-strategy-sandbox-strategy-catalog` materializes local strategy
  spreadsheets, lead catalogs, repo strategy configs, and directories into
  deterministic loadable sandbox `strategy_catalog.json` plus JSON/Parquet
  build reports with skipped-source reasons for agent preflight loops.
- Current git state after local WPR106-242 follow-up work:
  `run-rapid-strategy-sandbox-iteration` runs a one-command research-only
  sandbox iteration: materialize or reuse strategy/archive inputs, run the
  archive-backed sweep, summarize/falsify hypotheses, export descriptor-only
  strict-validation requests, refresh a global leaderboard, and write a compact
  iteration manifest.
- Current git state after local WPR106-243 follow-up work:
  sandbox market-frame loading normalizes common OKX, Bybit, and Hyperliquid
  local export aliases into canonical timestamp/OHLCV/price columns, records
  alias metadata in archive build/audit rows, and still filters out all
  pre-2024 rows.
- Current git state after local WPR106-244 follow-up work:
  `preflight-rapid-strategy-sandbox` checks a sandbox spec, strategy catalog,
  and venue archive manifest before a sweep, materializes blueprint signals
  inside the 2024+ window, and writes deterministic JSON/Parquet compatibility
  reports with runnable/blocked trial estimates and explicit blocker reasons.
- Current git state after local WPR106-245 follow-up work:
  `run-rapid-strategy-sandbox-iteration` now runs compatibility preflight as a
  first-class step before the archive sweep, records preflight paths/counts in
  the iteration manifest, and writes a `blocked_by_preflight` manifest with
  skipped downstream steps when no trials are runnable.
- Current git state after local WPR106-246 follow-up work:
  `run-rapid-strategy-sandbox-suite` now preflights every suite case before
  running a sweep, records per-case and suite-level preflight counts, and
  indexes zero-runnable cases as `blocked_by_preflight` without writing run or
  evidence-request artifacts for those cases.
- Current git state after local WPR106-247 follow-up work:
  sandbox fixed-hold sweep execution caches prepared strategy/filter signal
  masks per market frame and reuses them across venues, exit variants, and
  holding periods without changing trial IDs, metrics, rankings, or blocked
  reason semantics.
- Current git state after local WPR106-248 follow-up work:
  sandbox fixed-hold sweep execution prepares close, optional high/low, and
  entry-date arrays once per prepared 2024+ market frame and reuses them across
  venue, filter, exit, and holding-period trials without changing trial IDs,
  metrics, rankings, or blocked reason semantics.
- Current git state after local WPR106-249 follow-up work:
  sandbox shared-market multi-venue sweeps cache trial metrics per
  strategy/filter/exit/holding cell and reuse them across venue descriptors
  sharing that market frame, while descriptor-routed archive sweeps keep each
  venue's own market frame and metrics separate.
- Current git state after local WPR106-250 follow-up work:
  sandbox target/stop exit pricing uses vectorized primary-bar windows instead
  of nested per-trade/per-bar scans, while preserving long/short semantics,
  no-hit fixed-hold fallback, and conservative stop-first same-bar behavior.
- Current git state after local WPR106-251 follow-up work:
  sandbox suites can run independent cases concurrently with explicit
  `max_workers`, while final JSON/Parquet suite indexes, returned case results,
  and aggregated evidence-request descriptors remain ordered by the suite spec.
- Current git state after local WPR106-252 follow-up work:
  sandbox run and suite manifests record SHA-256 and byte-size integrity
  metadata for compact child Parquet/JSON artifacts without hashing the
  manifest itself.
- Current git state after local WPR106-253 follow-up work:
  `verify-rapid-strategy-sandbox-artifacts` verifies existing sandbox run or
  suite child artifact SHA-256 and byte-size metadata from a directory or
  manifest path, writes optional sandbox-only JSON/Parquet verification
  reports, and fails closed on missing metadata, missing files, or hash/size
  drift without executing validation or modifying source artifacts.
- Current git state after local WPR106-254 follow-up work:
  `index-rapid-strategy-sandbox-artifacts` now surfaces read-only integrity
  status for indexed run and suite manifests, including checked/verified/failed
  child artifact counts and failed artifact keys/reasons, while leaving
  non-run/suite artifacts as `not_applicable` and avoiding verifier report
  writes during catalog scans.
- Current git state after local WPR106-255 follow-up work:
  direct sandbox artifact consumers now verify run/suite child artifact
  integrity before reading manifest child files. Run analysis, run/suite
  hypothesis falsification, global leaderboard aggregation, and run/suite
  validation-request bundle export fail closed on missing metadata, missing
  files, or hash/size drift before writing derived artifacts.
- Current git state after local WPR106-256 follow-up work:
  cached `run-rapid-strategy-sandbox-iteration` reuse now validates referenced
  JSON/Parquet artifacts before returning `reused_existing: true`. Cached JSON
  artifacts must retain sandbox boundary flags, cached Parquet files must
  exist, and completed cached iterations verify the referenced run manifest's
  child-artifact integrity.
- Current git state after local WPR106-257 follow-up work:
  sandbox archive manifest builders now record local source file SHA-256 and
  byte-size metadata in build rows and generated venue descriptors. Archive
  manifest identity now changes when a source archive file is edited in place,
  while unchanged archive inputs remain idempotent.
- Current git state after local WPR106-258 follow-up work:
  descriptor-routed archive consumers now verify descriptor `source_integrity`
  before reading local archive files. Archive audit and compatibility preflight
  surface source-integrity mismatches as blockers, and archive-backed sweeps
  fail closed before reading changed source files; shared-market-data smoke
  mode remains explicitly available.
- Current git state after local WPR106-259 follow-up work:
  sandbox evidence-request descriptors now carry compact `source_trial_context`
  for strict-validation handoffs, including source trial/run identity,
  venue/source routing metadata, market timestamp bounds, exit/filter
  assumptions, and execution assumptions. Strict-validation request bundle rows
  preserve that context and expose searchable source market fields while
  remaining descriptor-only.
- Current git state after local WPR106-260 follow-up work:
  sandbox archive coverage matrices now aggregate archive descriptor audit rows
  into venue/symbol/data-family/interval buckets with ready/blocked descriptor
  counts, row counts, market/window bounds, source paths, and blocker/warning
  counts. The report reuses the audit path for 2024+ filtering and
  source-integrity blockers, and the sandbox artifact catalog discovers
  `archive_coverage_matrix.json`.
- Current git state after local WPR106-261 follow-up work:
  `summarize-rapid-strategy-sandbox-archive-coverage` is now a guarded
  research CLI command for generating archive coverage matrices under the
  configured research output root. It supports the same optional shared
  market-data smoke mode as archive audit and is registered for live-mode
  rejection.
- Current git state after local WPR106-262 follow-up work:
  `run-rapid-strategy-sandbox-iteration` now writes an archive coverage matrix
  before compatibility preflight, records coverage and source-audit paths/counts
  in completed and preflight-blocked iteration manifests, and validates cached
  coverage artifacts before returning `reused_existing: true`.
- Current git state after local WPR106-263 follow-up work:
  sandbox agent iterations now write `sandbox_iteration_agent_brief.json` and a
  one-row Parquet brief with next-action labels, reason codes, compact counts,
  top blockers, top descriptor-only validation requests, and artifact pointers.
  Cached iteration reuse validates brief artifacts, and the sandbox artifact
  catalog discovers `agent_iteration_brief` rows.
- Current git state after local WPR106-264 follow-up work:
  sandbox iteration indexes now scan iteration manifests and agent briefs across
  an output root, writing `sandbox_iteration_index.json` and Parquet rows with
  iteration status, next action, blocker/request counts, brief availability,
  and artifact pointers for fast agent navigation.
- Current git state after local WPR106-265 follow-up work:
  `index-rapid-strategy-sandbox-iterations` is now a guarded research CLI
  command for writing sandbox iteration indexes under the configured research
  output root. The command is registered for live-mode rejection and preserves
  the existing read-only iteration-index boundary.
- Current git state after local WPR106-266 follow-up work:
  sandbox iteration indexes now include deterministic action queues for
  request-bearing, preflight-repair, missing-brief, and rejection-review
  iterations. Queue entries are compact sandbox-boundary summaries derived from
  existing index rows and do not execute validation or create candidate
  evidence.
- Current git state after local WPR106-267 follow-up work:
  sandbox archive manifest builders can infer venue, symbol, data family, and
  interval from common OKX/Bybit/Hyperliquid content columns when local archive
  filenames are generic. Build reports expose inference-source fields while
  preserving source integrity, 2024+ filtering, and sandbox-only boundaries.
- Current git state after local WPR106-268 follow-up work:
  sandbox direct strategy catalog loading now normalizes common human
  spreadsheet headers such as `Hypothesis`, `Strategy Family`, `Signal`, and
  `Direction` before lead/proxy fallback. Alias-heavy direct catalogs stay
  direct precomputed-signal descriptors with optional filters, params, tags,
  and notes preserved.
- Current git state after local WPR106-269 follow-up work:
  sandbox venue descriptor intake now canonicalizes common local/export venue
  aliases such as `binance_futures`, `okex`, `bybit_usdt_linear`, and
  `hl_perp` into canonical sandbox venues before validation. Archive manifest
  builder overrides use the same alias path, preserving research-only
  descriptor boundaries and source-integrity metadata.
- Current git state after local WPR106-270 follow-up work:
  generated one-command sandbox iterations now support recent-window presets
  such as `recent_365d`, clipped to the `2024-01-01` sandbox floor. Iteration
  manifests and agent briefs record the preset/as-of/lookback/resolved-window
  metadata, and spec-file runs reject preset overrides instead of silently
  rewriting explicit specs.
- Current git state after local WPR106-271 follow-up work:
  archive-root materialization for one-command sandbox iterations now receives
  the resolved sandbox data window. The archive manifest builder includes only
  local files whose normalized 2024+ bounds overlap that window and records
  non-overlapping files as `outside_requested_window` skipped rows.
- Current git state after local WPR106-272 follow-up work:
  sandbox archive audits and coverage matrices can receive the resolved
  sandbox data window. They report requested-window row counts separately from
  descriptor-window counts and block otherwise loadable descriptors with
  `no_rows_in_requested_window` when an existing venue archive manifest has no
  rows in the active requested window.
- Current git state after local WPR106-273 follow-up work:
  sandbox iteration indexes expose archive requested-window row counts and add
  an `archive_window_repair_queue` for iterations whose archive blockers
  include `no_rows_in_requested_window`, so agents can find manifest/window
  repair work without reopening each coverage artifact.
- Current git state after local WPR106-274 follow-up work:
  one-command sandbox iteration manifests and agent briefs now carry full
  archive coverage blocker reason counts. Iteration indexes preserve those
  counts and use them for `archive_window_repair_queue` membership, falling
  back to bounded top blockers only for older artifacts.
- Current git state after local WPR106-275 follow-up work:
  one-command sandbox agent briefs and iteration indexes now carry full
  preflight blocker reason counts, while keeping bounded top preflight blockers
  for display. Iteration index rows and queues prefer full counts and fall back
  to top blockers for older artifacts.
- Current git state after local WPR106-276 follow-up work:
  sandbox iteration indexes now include queue-level `action_queue_summaries`
  that aggregate every matched action-queue row, including rows beyond the
  visible queue cap. Queue items also carry coverage and preflight status
  counts, giving agents one-manifest triage for repair and request backlogs.
- Current git state after local WPR106-277 follow-up work:
  sandbox iteration index rows and queue items now expose materialized
  strategy-catalog and venue-archive source context: catalog/archive manifest
  paths, build-report paths, included/skipped strategy source counts, archive
  file counts, and archive skipped-file counts. Queue summaries aggregate those
  source counts so requested-window archive materialization skips are visible
  from one index manifest.
- Current git state after local WPR106-278 follow-up work:
  sandbox iteration indexes now report read-only artifact availability for
  referenced iteration/source/handoff artifact paths. Rows, queue items, and
  queue summaries expose referenced/present/missing artifact counts and missing
  keys, and a new `artifact_repair_queue` points agents at iterations whose
  referenced artifacts have gone missing.
- Current git state after local WPR106-279 follow-up work:
  sandbox iteration indexes now include deterministic recommended action hints
  on rows and action queue items, plus recommended-action rollups in queue
  summaries and top-level payloads. The hints are derived only from existing
  index metadata so agents can choose repair/review work faster without
  executing validation or mutating artifacts from the index.
- Current git state after local WPR106-280 follow-up work:
  sandbox iteration indexes now include a global `agent_action_plan` derived
  from row recommended actions. The plan gives agents one prioritized worklist
  with action priorities, source queue labels, blocker/request context,
  relevant paths, and dependent-action markers while remaining a read-only
  navigation artifact.
- Current git state after local WPR106-281 follow-up work:
  sandbox iteration indexes now write the visible `agent_action_plan` as
  `sandbox_iteration_agent_action_plan.parquet` and expose
  `agent_action_plan_parquet_path` in the index payload, giving agents a
  queryable repair/request worklist without parsing nested index JSON.
- Current git state after local WPR106-282 follow-up work:
  descriptor-routed sandbox sweeps now reuse trial metric work across venue
  descriptors that share the same explicit market source, including shared
  market-data paths, identical descriptor `data_path` values, or the same
  in-memory market frame object. Distinct descriptor sources still compute
  separately, and venue-specific trial IDs/source metadata remain distinct.
- Current git state after local WPR106-283 follow-up work:
  descriptor-routed sandbox batch loading now caches loaded and normalized
  market frames for identical resolved descriptor `data_path` values. Source
  integrity is still checked per descriptor before any cached frame is returned,
  distinct paths remain separate frames, and pre-2024 rows remain filtered out.
- Current git state after local WPR106-284 follow-up work:
  sandbox archive audit/coverage and compatibility preflight now cache
  identical resolved market sources inside each readiness run. Audit avoids
  rereading and renormalizing repeated descriptor paths, preflight reuses
  loaded/windowed/materialized frames, and both paths still evaluate source
  integrity per descriptor before cached market data is used.
- Current git state after local WPR106-285 follow-up work:
  one-command sandbox iterations now pass one process-local market-data cache
  through archive coverage, compatibility preflight, and the archive sweep, so
  a repeated local source is read and normalized once across the active
  iteration while trial IDs, rankings, market-source metadata, blocker
  semantics, and artifacts remain unchanged.
- Current git state after local WPR106-286 follow-up work:
  sequential sandbox suites now reuse one process-local market-data cache across
  case preflight and archive sweep execution, so repeated shared local market
  sources are read and normalized once across the suite. Parallel suites keep
  case-local caches, and suite artifacts record only cache-scope metadata.
- Current git state after local WPR106-287 follow-up work:
  sequential sandbox suites now reuse parsed sandbox run specs, strategy
  catalogs, and venue archive descriptor manifests by resolved local path.
  Parallel suites keep parsed-input caches case-local, and suite artifacts
  record only input-cache-scope metadata.
- Current git state after local WPR106-288 follow-up work:
  sandbox local archive intake now supports gzip-compressed CSV, TSV, JSON, and
  JSONL market-data exports. Archive manifest building recognizes compound
  suffixes such as `.csv.gz`, includes loadable compressed OKX/Bybit/
  Hyperliquid-style local drops, and preserves source integrity against the
  compressed file itself.
- Current git state after local WPR106-289 follow-up work:
  sandbox ZIP CSV loading now preserves headered local venue-export columns for
  normalization and archive-manifest content inference while keeping Binance
  Vision headerless kline ZIP support. Archive data-family path inference no
  longer treats `market` as `mark_index`.
- Current git state after local WPR106-290 follow-up work:
  sandbox timestamp normalization now infers seconds, milliseconds,
  microseconds, and nanoseconds for numeric timestamp aliases before applying
  the 2024+ filter. Compact `YYYYMMDD` timestamp values remain calendar dates.
- Current git state after local WPR106-291 follow-up work:
  sandbox local archive intake now treats `.ndjson` and `.ndjson.gz` as
  newline-delimited JSON exports, sharing the existing JSONL normalization,
  2024+ filtering, archive-manifest inclusion, and compressed-file source
  integrity behavior.
- Current git state after local WPR106-292 follow-up work:
  sandbox ZIP archive loading now accepts ZIP members containing TSV, JSON,
  JSONL, or NDJSON market-data exports when no CSV member is present. ZIPs with
  CSV members still prefer CSV first, preserving Binance Vision and headered
  CSV venue-export behavior.
- Current git state after local WPR106-293 follow-up work:
  sandbox market-frame normalization now accepts common mark/index/mid price
  aliases such as `markPx`, `idxPx`, and `midPx`, and can derive canonical
  `close` from bid/ask midpoint for L2/book snapshots when no explicit
  close-like price column exists. Archive build rows expose derived-column
  metadata for agent triage.
- Current git state after local WPR106-294 follow-up work:
  sandbox JSON and ZIP-JSON loading can flatten local Hyperliquid-style nested
  `l2Book` payloads with `levels` arrays into best bid/ask rows, reuse the
  midpoint `close` derivation path, record source-transformation metadata, and
  infer `l2_book` descriptor family from generic snapshot exports.
- Current git state after local WPR106-295 follow-up work:
  sandbox local archive loading now supports `.tar`, `.tar.gz`, and `.tgz`
  files containing CSV/TSV/JSON/JSONL/NDJSON market-data members, reading
  members in memory without extraction and preserving archive manifest source
  integrity, 2024+ filtering, venue alias normalization, and sandbox-only
  boundaries.
- Current git state after local WPR106-296 follow-up work:
  sandbox ZIP and TAR/TGZ readers now detect gzip-compressed market-data
  members such as `.csv.gz` and `.jsonl.gz` by compound suffix, decompress
  member payloads in memory, and send them through the same local 2024+
  normalization path without source archive mutation or member extraction.
- Current git state after local WPR106-297 follow-up work:
  sandbox ZIP and TAR/TGZ readers now concatenate every member of the selected
  highest-priority market-data suffix in deterministic member-name order before
  2024+ normalization, so chunked local venue drops no longer silently load only
  the first matching member.
- Current git state after local WPR106-298 follow-up work:
  sandbox ZIP and TAR/TGZ readers now preserve bounded container member
  selection metadata through normalization and archive manifest build rows,
  including container kind, selected suffix/count, selected member-name sample,
  available suffix counts, and loadable member count for agent audit loops.
- Current git state after local WPR106-299 follow-up work:
  sandbox archive descriptor audits and archive coverage matrices now propagate
  and aggregate bounded container member-selection diagnostics, so agent
  preflight loops can inspect ZIP/TAR selected suffixes, member counts, suffix
  counts, and bounded member-name samples without reopening build reports.
- Current git state after local WPR106-300 follow-up work:
  sandbox compatibility preflight rows now expose bounded container
  member-selection diagnostics as searchable JSON/Parquet fields, so agents can
  triage archive-backed runnable/blocked trial estimates without parsing nested
  normalization metadata.
- Current git state after local WPR106-301 follow-up work:
  sandbox archive sweeps now preserve bounded ZIP/TAR container
  member-selection diagnostics in result `market_source` metadata, run
  manifests, ranking metadata, evidence-request source context, and
  descriptor-only strict-validation request bundle rows for faster agent
  provenance review.
- Current git state after local WPR106-302 follow-up work:
  one-command sandbox iteration briefs, iteration index rows, strict-validation
  action queues, and agent action-plan items now preserve compact source
  summaries for top descriptor-only validation requests, including routing,
  source path, market bounds, and bounded ZIP/TAR member diagnostics.
- Current git state after local WPR106-303 follow-up work:
  sandbox strategy catalog intake now loads every usable sheet from local
  `.xlsx/.xls` workbooks, including direct strategy sheets and
  spreadsheet-like lead sheets, while strategy-catalog materializer build
  reports expose compact included/skipped sheet diagnostics for agent preflight
  loops.
- Current git state after local WPR106-304 follow-up work:
  one-command sandbox iteration manifests, agent briefs, and iteration index
  rows now expose compact materialized strategy-source summaries, including
  source status/suffix counts, skipped-source reason counts, family/side/
  blueprint counts, and bounded workbook sheet diagnostics.
- Current git state after local WPR106-305 follow-up work:
  direct strategy rows loaded from local workbook catalogs now default missing
  source IDs to `workbook_path#sheet_name`, while explicit source IDs remain
  authoritative; materialized catalogs and build reports preserve that
  descriptor provenance.
- Current git state after local WPR106-306 follow-up work:
  sandbox iteration indexes now surface skipped materialized strategy catalog
  sources in a dedicated `strategy_source_repair_queue`, recommended action
  hints, queue summaries, and agent action-plan items with source skip reason
  counts for faster repair loops.
- Current git state after local WPR106-307 follow-up work:
  one-command sandbox iteration strategy-source summaries, iteration indexes,
  strategy-source repair queues, and agent action-plan items now carry bounded
  skipped source samples with source paths, suffixes, and skip reasons so
  agents can identify bad catalog files without reopening build reports.
- Current git state after local WPR106-308 follow-up work:
  one-command sandbox iteration archive-source summaries, iteration indexes,
  archive/preflight action queues, recommended action details, and agent
  action-plan items now carry bounded skipped archive-file samples with source
  paths, integrity metadata, requested-window bounds, and skip reasons so
  agents can identify bad or out-of-window archive files without reopening
  build reports.
- Current git state after local WPR106-309 follow-up work:
  one-command sandbox iteration manifests, agent briefs, iteration indexes,
  archive-window/preflight queues, recommended action details, and agent
  action-plan items now carry bounded archive-coverage blocker samples with
  blocked descriptor IDs, source paths, blocker reason counts, and window
  evidence so agents can repair archive coverage blockers without reopening
  coverage matrices or source audits.
- Current git state after local WPR106-310 follow-up work:
  one-command sandbox iteration manifests, agent briefs, iteration indexes,
  preflight repair queues, recommended action details, and agent action-plan
  items now carry bounded compatibility-preflight blocker samples with
  descriptor IDs, hypothesis IDs, signal/filter columns, source paths, blocker
  reason counts, trial estimates, and market-column context so agents can
  repair blocked strategy/archive combinations without reopening preflight
  Parquet or JSON rows.
- Current git state after local WPR106-311 follow-up work:
  completed one-command sandbox iteration manifests, agent briefs, iteration
  indexes, rejection-review queues, recommended action details, queue
  summaries, and agent action-plan items now carry bounded
  rejection/falsification samples with failed hypothesis IDs, decisions,
  representative rejected or blocked trial IDs, compact metrics, tested
  exit/filter variants, and reason counts so agents can review falsified
  hypotheses without reopening rankings or falsification Parquet rows.
- Current git state after local WPR106-312 follow-up work:
  one-command sandbox iteration manifests, agent briefs, iteration-index rows,
  action queue items, recommended action details, and agent action-plan items
  now carry inert input replay context with a deterministic replay context ID,
  command name, non-executing argv list, strategy/venue input modes, resolved
  paths or roots, data windows, and bounded run/build options so agents can
  reproduce or refresh archive-backed iterations from handoff artifacts.
- Current git state after local WPR106-313 follow-up work:
  sandbox iteration indexes now materialize a dedicated descriptor-only input
  replay worklist as JSON and Parquet. The worklist flattens replay context
  IDs, argv-list command descriptors, input modes, resolved paths or roots,
  data windows, recommended action context, artifact availability, and compact
  counts so agents can query replay/refresh metadata without parsing nested
  index rows, queues, or action-plan items.
- Current git state after local WPR106-314 follow-up work:
  sandbox iteration input replay worklists now include replay input path
  readiness diagnostics. Worklist rows check only filesystem existence and
  expected file-vs-directory type for output/spec/catalog/archive references,
  expose present/missing/wrong-type counts, missing keys, bounded reference
  rows, and fail `input_replay_ready` closed when replay inputs are missing.
- Current git state after local WPR106-315 follow-up work:
  sandbox iteration input replay worklist summaries now roll up replay rows by
  archive venue, symbol, data family, interval, venue/symbol/family/interval
  bucket, requested window, readiness, and path availability so agents can find
  ready or blocked OKX/Bybit/Hyperliquid archive-backed replay coverage without
  scanning every worklist row.
- Current git state after local WPR106-316 follow-up work:
  sandbox iteration input replay worklist rows and summaries now expose
  duplicate replay-context groups, per-row duplicate counts, duplicate flags,
  duplicate group-key counts, and archive/window unique replay-context rollups
  so agents can avoid planning redundant refreshes for identical sandbox inputs.
- Current git state after local WPR106-317 follow-up work:
  sandbox iteration indexes now emit a descriptor-only input replay batch plan
  as JSON and Parquet. The plan selects one ready representative argv-list
  descriptor per unique replay context, summarizes suppressed duplicates and
  blocked replay rows, and is registered in the sandbox artifact catalog for
  agent discovery.
- Current git state after local WPR106-318 follow-up work:
  sandbox artifact catalog rows now expose input replay batch-plan source,
  ready, blocked, descriptor, unique-ready-context, and suppressed-duplicate
  counts so agents can rank replay batch-plan artifacts without opening every
  batch-plan JSON.
- Current git state after local WPR106-319 follow-up work:
  sandbox artifact catalogs now include a top-level replay batch-plan summary
  and bounded replay batch-plan queue, derived from already-indexed catalog
  rows, so agents can select useful replay batch plans without scanning all
  artifacts.
- Current git state after local WPR106-320 follow-up work:
  sandbox artifact catalogs now project descriptor-only input replay batch-plan
  ready/planned archive bucket and archive-window bucket count maps into catalog
  rows, top-level replay batch-plan summaries, and bounded queue items so agents
  can triage OKX/Bybit/Hyperliquid coverage without opening every batch-plan
  JSON.
- Current git state after local WPR106-321 follow-up work:
  sandbox artifact catalogs now include bounded archive bucket and
  archive-window bucket representative queues derived from replay batch-plan
  catalog rows. Agents can jump from a venue/window bucket to representative
  descriptor-only batch-plan artifacts without scanning every queue item or
  opening every batch-plan JSON.
- Current git state after local WPR106-322 follow-up work:
  sandbox artifact catalogs now write compact replay bucket queue and bucket
  representative Parquet sidecars derived from bounded catalog queues. Agents
  can query venue/window-to-plan routing from flat Parquet rows while empty
  bucket coverage still writes empty-schema sidecars for stable automation.
- Current git state after local WPR106-323 follow-up work:
  sandbox artifact catalogs now project descriptor-only strict-validation
  request bundle counts into catalog rows, add a top-level strict-validation
  bundle summary, and expose a bounded bundle queue so agents can find ready
  strict-validation handoff artifacts without opening every bundle JSON.
- Current git state after local WPR106-324 follow-up work:
  sandbox artifact catalogs now write a compact strict-validation bundle queue
  Parquet sidecar derived from the bounded catalog queue. Agents can query
  descriptor-only validation handoff bundles from flat rows while catalogs with
  no bundle queue still write an empty-schema sidecar for stable automation.
- Current git state after local WPR106-325 follow-up work:
  sandbox artifact catalogs now write a cross-bundle strict-validation
  descriptor Parquet sidecar from already-loaded bundle JSON payloads. Agents
  can query individual descriptor-only validation requests, source trials,
  venues, symbols, market windows, and source metrics from one flat sidecar
  without opening each bundle JSON or bundle Parquet.
- Current git state after local WPR106-326 follow-up work:
  sandbox artifact catalogs now add a bounded strict-validation descriptor
  bucket queue and Parquet sidecar grouped by venue/symbol and
  venue/symbol/requested-validation. Agents can see multi-venue validation
  request clusters and representative descriptor IDs without scanning every
  descriptor row.
- Current git state after local WPR106-327 follow-up work:
  sandbox artifact catalogs now write a companion strict-validation descriptor
  bucket representative Parquet sidecar. Agents can jump from venue/symbol
  validation buckets to representative descriptor metadata, source trials,
  market windows, metrics, and routing fields without joining the full
  descriptor table first.
- Current git state after local WPR106-328 follow-up work:
  sandbox artifact catalogs now expose a bounded strict-validation descriptor
  priority queue and Parquet sidecar. Agents can start from the highest-priority
  descriptor-only evidence requests across bundles without scanning the full
  descriptor table first.
- Current git state after local WPR106-329 follow-up work:
  sandbox artifact catalogs now write a compact sidecar index Parquet file that
  inventories catalog, replay batch-plan, and strict-validation sidecar names,
  categories, paths, row counts, and empty status for faster agent navigation.
- Current git state after local WPR106-330 follow-up work:
  sandbox artifact catalog sidecar index rows now include file existence,
  byte-size, and SHA-256 metadata for catalog-written companion sidecars so
  agents can verify sidecar identity without opening the catalog JSON first.
- Current git state after local WPR106-331 follow-up work:
  sandbox artifact catalogs now project existing iteration-index agent action
  plans into compact catalog rows and a Parquet sidecar. Agents can find
  cross-iteration repair, replay, rejection-review, and descriptor-only
  strict-validation work from the artifact catalog without opening each
  iteration index JSON first.
- Current git state after local WPR106-332 follow-up work:
  sandbox artifact catalogs now add a bounded iteration action-plan bucket
  sidecar grouped by action and source queue. Agents can see which
  cross-iteration workflow buckets exist, with representative iteration IDs,
  before scanning every action-plan row.
- Current git state after local WPR106-333 follow-up work:
  sandbox artifact catalogs now write a companion iteration action-plan bucket
  representative sidecar. Agents can jump from action/source-queue workflow
  buckets to representative iteration/action rows without joining the full
  action-plan sidecar first.
- Current git state after local WPR106-334 follow-up work:
  sandbox run analysis reports now include bounded venue, family, exit, filter,
  and venue/family bucket rollups with counts, best representative trials, and
  non-authorizing boundary flags so agents can triage promising or failing run
  clusters without scanning every ranking row.
- Current git state after local WPR106-335 follow-up work:
  sandbox artifact catalogs now flatten run analysis bucket rollups into
  `sandbox_artifact_catalog_analysis_bucket_rollups.parquet` and register that
  sidecar in the sidecar index with post-write file identity. Agents can query
  venue, family, exit, filter, and venue/family buckets across many runs without
  opening each `analysis_summary.json`.
- Current git state after local WPR106-336 follow-up work:
  sandbox global leaderboards now write
  `sandbox_global_bucket_leaderboard.parquet` and expose bounded `top_buckets`
  in `sandbox_global_leaderboard.json`. Agents can rank venue, symbol,
  venue/symbol, family, exit, filter, and venue/family clusters directly from
  integrity-checked run rankings, even when per-run analysis reports are absent.
- Current git state after local WPR106-337 follow-up work:
  sandbox artifact catalog rows for global leaderboards now expose the
  companion global bucket leaderboard Parquet path, bucket count, bounded
  top-bucket count/types, and bucket decision-count map from the loaded
  `sandbox_global_leaderboard.json` payload. Agents can route from catalog to
  cross-run bucket evidence without reopening each leaderboard JSON first.
- Current git state after local WPR106-338 follow-up work:
  sandbox artifact catalogs now flatten bounded global leaderboard `top_buckets`
  into `sandbox_artifact_catalog_global_bucket_top_buckets.parquet` and register
  the sidecar in the sidecar index with file identity. Agents can query
  cross-run venue, symbol, family, exit, filter, and venue/family bucket leaders
  from catalog output without opening each leaderboard JSON or bucket Parquet
  first.
- Current git state after local WPR106-339 follow-up work:
  sandbox artifact catalogs now flatten bounded global leaderboard
  `top_hypotheses` into
  `sandbox_artifact_catalog_global_top_hypotheses.parquet` and register the
  sidecar in the sidecar index with file identity. Agents can query cross-run
  hypothesis ranking, falsification state, representative trial metadata, and
  descriptor-only evidence-request IDs from catalog output without opening each
  leaderboard JSON or leaderboard Parquet first.
- Current git state after local WPR106-340 follow-up work:
  sandbox artifact catalogs now flatten bounded global leaderboard
  `top_hypotheses[*].evidence_request_trial_ids` into
  `sandbox_artifact_catalog_global_evidence_requests.parquet` and register the
  sidecar in the sidecar index with file identity. Agents can route
  descriptor-only strict-validation request trial IDs from catalog output
  without opening each leaderboard JSON, leaderboard Parquet, or parsing
  list-valued top-hypothesis cells first.
- Current git state after local WPR106-341 follow-up work:
  sandbox artifact catalogs now derive a bounded
  `sandbox_artifact_catalog_global_evidence_request_bucket_queue.parquet`
  sidecar from global evidence-request rows and register it in the sidecar
  index with file identity. Agents can route descriptor-only global
  strict-validation requests by requested validation, hypothesis, family,
  tested venue, tested symbol, tested venue/family, tested venue/symbol, and
  leaderboard decision without scanning the full flat request table first.
- Current git state after local WPR106-342 follow-up work:
  sandbox artifact catalogs now derive
  `sandbox_artifact_catalog_global_evidence_request_bucket_representatives.parquet`
  from global evidence-request bucket queues and in-memory global request rows.
  Agents can jump from a global request bucket to concrete descriptor-only
  evidence-request trial IDs, hypothesis context, tested venues/symbols, and
  source leaderboard paths without joining the full flat request sidecar first.
- Current git state after local WPR106-343 follow-up work:
  sandbox artifact catalog global leaderboard rows now expose compact
  global evidence-request metadata, including request counts, unique trial
  counts, requesting-hypothesis counts, requested-validation and leaderboard
  decision maps, family maps, and tested venue/symbol maps. The catalog
  manifest also exposes a global evidence-request summary with request, bucket,
  and representative counts so agents can identify requestable leaderboard
  artifacts before opening evidence-request sidecars.
- Current git state after local WPR106-344 follow-up work:
  sandbox artifact catalogs now write
  `sandbox_artifact_catalog_global_evidence_request_priority_queue.parquet`,
  a bounded descriptor-only queue of top global leaderboard evidence requests
  derived from in-memory global request rows. Agents can start from concrete
  strict-validation request trial IDs, source leaderboard paths, hypothesis
  context, tested venues/symbols, and compact metrics without scanning the full
  flat global evidence-request sidecar first.
- Current git state after local WPR106-345 follow-up work:
  sandbox global leaderboard top hypotheses now carry a bounded
  `evidence_request_source_contexts` preview derived from already-loaded
  evidence-request descriptors. Artifact catalog global request rows and the
  priority queue flatten compact source request IDs, source run paths, market
  windows, routing/data-path/container fields, and source metrics so agents can
  route descriptor-only strict-validation work without reopening per-run
  evidence request files.
- Current git state after local WPR106-346 follow-up work:
  sandbox artifact catalog global evidence-request bucket queues and bucket
  representatives now carry source-context routing fields and source-context
  bucket keys. Agents can route descriptor-only strict-validation requests by
  source venue, symbol, venue/symbol, data family, interval, venue descriptor,
  routing mode, and data path without scanning the full flat request table or
  reopening per-run evidence request files.
- Current git state after local WPR106-347 follow-up work:
  sandbox artifact catalog global evidence-request summaries and top-level
  manifest fields now expose source venue, source symbol, source data family,
  source interval, source routing mode, source venue descriptor, and source
  data-path count maps. Agents can decide which source-context queues are worth
  opening before scanning bucket or flat request sidecars.
- Current git state after local WPR106-348 follow-up work:
  sandbox artifact catalogs now write
  `sandbox_artifact_catalog_global_evidence_request_source_summary.parquet`
  and register it in the sidecar index with file identity. Agents can query
  global evidence-request source venue, symbol, data family, interval, routing
  mode, venue descriptor, and data-path availability from flat Parquet rows
  without opening the catalog JSON or full request sidecar.
- Current git state after local WPR106-349 follow-up work:
  the global evidence-request source-summary sidecar now includes unique
  request-trial counts, source leaderboard counts, and source market start/end
  min/max bounds per source field/value row. Agents can verify 2024+ source
  windows for source venues, symbols, routing modes, venue descriptors, and
  data paths without scanning the full flat request sidecar.
- Current git state after local WPR106-350 follow-up work:
  the global evidence-request source-summary sidecar now includes bounded
  representative evidence-request trial IDs, source trial IDs, source request
  IDs, source artifact paths, and source leaderboard JSON paths per source
  field/value row. Agents can jump from source coverage and 2024+ window
  summaries to concrete descriptor-only request rows without opening bucket
  representative sidecars or scanning the full flat request sidecar first.
- Current git state after local WPR106-351 follow-up work:
  the global evidence-request source-summary sidecar now includes compact
  best-context fields per source field/value row: best leaderboard rank, best
  global score, best source metric rank/score/net return/trade count, best
  evidence-request trial ID, best source trial ID, best hypothesis ID, and best
  family. Agents can prioritize source coverage queues before opening the full
  flat global request sidecar.
- Current git state after local WPR106-352 follow-up work:
  sandbox artifact catalogs now write
  `sandbox_artifact_catalog_global_evidence_request_source_priority_queue.parquet`,
  a bounded cross-source priority queue derived from source-summary rows.
  Agents can inspect the best source venue, symbol, family, interval, routing,
  descriptor, and data-path coverage rows first without scanning the full flat
  global request sidecar or hand-sorting the source-summary sidecar.
- Current git state after local WPR106-353 follow-up work:
  sandbox artifact catalog sidecar-index rows now include deterministic
  `agent_read_order`, `agent_read_group`, `agent_first_read`, and
  `agent_navigation_hint` metadata. Agents can discover the first catalog,
  source-priority, strict-validation, iteration-action, and replay-planning
  sidecars from the sidecar index itself without relying on packet history or
  hard-coded filename order.
- Current git state after local WPR106-354 follow-up work:
  sandbox archive coverage now writes
  `archive_coverage_venue_expansion_gaps.parquet`, a compact diagnostic
  sidecar that compares OKX, Bybit, and Hyperliquid readiness for each observed
  market-symbol/data-family/interval group. Agents can see ready, blocked,
  mixed, and missing venue targets plus descriptor-only repair/add actions
  before launching archive-backed iterations.
- Current git state after local WPR106-355 follow-up work:
  one-command sandbox iteration manifests, agent briefs, iteration indexes,
  action queues, and agent action plans now surface the venue-expansion gap
  sidecar path, counts, descriptor-only target actions, and bounded actionable
  samples. Agents can prioritize OKX/Bybit/Hyperliquid archive descriptor
  repair or addition from the iteration handoff without opening the full
  archive coverage JSON first.
- Current git state after local WPR106-356 follow-up work:
  the sandbox artifact catalog now writes
  `sandbox_artifact_catalog_iteration_venue_expansion_gap_worklist.parquet`,
  a compact first-read sidecar flattened from already-loaded iteration
  action-plan venue-expansion samples. Agents can query concrete OKX, Bybit,
  and Hyperliquid archive descriptor repair/add targets across iteration
  indexes from the catalog sidecar index without opening each iteration index
  JSON or archive coverage sidecar.
- Current git state after local WPR106-357 follow-up work:
  `export-rapid-strategy-sandbox-venue-expansion-requests` writes
  descriptor-only `sandbox_venue_expansion_request_bundle.json` and
  `.parquet` artifacts from an existing sandbox artifact catalog and its venue
  expansion gap worklist sidecar. The bundle dedupes OKX, Bybit, and
  Hyperliquid archive descriptor repair/add requests by target venue, compact
  market-symbol key, data family, interval, target action, and target bucket,
  preserves bounded source iteration/queue/path references, registers in the
  catalog as `venue_expansion_request_bundle`, refuses pre-2024 windows, and
  never downloads data, mutates archive manifests or source files, executes
  replay/validation, writes candidate packs, or changes promotion state.
- Current git state after local WPR106-358 follow-up work:
  `docs/NEXT_AGENT_HANDOFF_WPR106_358_SANDBOX_SELF_AUDIT.md` is the visible
  next-agent self-audit for the sandbox rewrite. It records what is solid,
  what remains incomplete, current worktree friction, validation evidence, and
  the recommended next packet for a descriptor-only local materializer that can
  consume venue-expansion request bundles and scan only user-provided local
  archive roots.
- Current git state after local WPR106-359 follow-up work:
  `docs/SANDBOX_FIRST_LOOK_RECOMMENDATIONS.md` records audit-first posture
  before more sandbox feature work and warns that the current dirty/untracked
  state must be classified before continuing.
- Current git state after local WPR106-360 follow-up work:
  `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md` is the master
  research-only completion roadmap. It starts with mandatory repo-state and
  test stabilization, then sequences safety/provenance repair, local
  venue-expansion materialization, closed-loop smoke evidence,
  strict-validation descriptor preflight, performance proof, and reviewable
  delivery. It does not authorize live, paper, sizing, order, runtime,
  candidate-pack, or promotion work.
- Current git state after local WPR106-361 follow-up work:
  `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md` is expanded into a
  detailed autonomous-development guide with product definition, target
  architecture, subsystem touchpoints, Phase 0 stabilization checklist,
  safety/provenance repair specs, closed-loop sandbox guidance,
  strict-validation preflight guidance, performance proof requirements,
  suggested packet backlog, artifact rules, testing matrix, stop conditions,
  agent operating rules, and definition of done.
- Current git state after local WPR106-362 follow-up work:
  post-audit sandbox safety/coherence blockers are repaired. Sandbox run IDs
  are path-safe, run/suite output directories are contained under configured
  roots, nested free-form live/paper/order/sizing/promotion/candidate-pack
  fields fail boundary validation, descriptor-window intersections are enforced
  in preflight and execution, manifest child artifact paths cannot escape their
  run/suite directory during integrity verification, trial IDs include
  decision-affecting thresholds without depending on local archive paths, and
  proxy blueprint outputs are explicitly proxy-only. `baseline_no_trade`
  compiles to a non-active `no_trade_proxy`.
- Current git state after local WPR106-363 follow-up work:
  the two audit-reported full-suite blockers are fixed. 4h
  `trend_following_v1` and 12h `range_reversion_v1` spacing metadata match the
  existing optimization contract, and large discovery resume manifests count
  recovered completed trial IDs without forcing full trial hydration.
- Current git state after local WPR106-364 follow-up work:
  `.github/workflows/research-validation.yml` now runs
  `tests/research_sandbox` and includes `tests/live/test_cli_boundary.py` in
  the live/artifact boundary step, so sandbox and CLI boundary regressions are
  part of the checked-in baseline.
- Current git state after local WPR106-365 follow-up work:
  the intended sandbox publication surface is classified as the complete
  `configs/sandbox`, `src/tradingbotsuite/research_sandbox`, and
  `tests/research_sandbox` source/config/test set plus related WPR106-362
  through WPR106-365 packet/report documentation. `outputs/` remains ignored
  and clean; broader inherited dirty-tree work remains out of scope and must
  not be swept into sandbox publication without its own packet/review.
- Current git state after local WPR106-366 follow-up work:
  `materialize-rapid-strategy-sandbox-venue-expansion-requests` consumes
  descriptor-only venue-expansion request bundles, scans only explicitly
  supplied local archive roots, and writes descriptor-candidate plus
  manifest-patch dry-run artifacts for requested venue coverage. Unmatched
  requests become blocker rows, pre-2024 request windows are rejected, and no
  provider download, archive/source mutation, manifest write, replay, strict
  validation, candidate-pack, paper/live, sizing, order, runtime, live-config,
  candidate-evidence, or promotion behavior is authorized.
- Current git state after local WPR106-367 follow-up work:
  sandbox artifact catalogs now discover WPR106-366 materializer outputs:
  `sandbox_venue_expansion_descriptor_candidates.json` as
  `venue_expansion_descriptor_candidates` and
  `sandbox_venue_expansion_manifest_patch_dry_run.json` as
  `venue_expansion_manifest_patch_dry_run`. Catalog rows expose materializer
  request, candidate, ready/blocked, scan, output-path, and false
  provider/archive mutation authorization fields without rerunning
  materialization or changing dry-run semantics.
- Current git state after local WPR106-368 follow-up work:
  `export-rapid-strategy-sandbox-venue-expansion-candidate-manifest` converts
  validated WPR106-366 descriptor candidates into a new standalone sandbox
  `venue_archives.json` manifest plus JSON/Parquet report under the configured
  research output root. The manifest is loadable by existing archive coverage
  and compatibility preflight paths, while source archives and existing
  manifests remain untouched.
- Current git state after local WPR106-369 follow-up work:
  the sandbox test suite now includes a fixture-level closed-loop regression
  for venue-expansion workflow composition: request bundle -> materializer ->
  candidate manifest -> coverage -> preflight -> bounded archive sweep ->
  analysis/falsification -> descriptor-only strict-validation request bundle ->
  artifact catalog. This is workflow regression evidence only, not real-market
  archive evidence, candidate evidence, or promotion evidence.
- Current git state after local WPR106-370 follow-up work:
  `preflight-rapid-strategy-sandbox-validation-requests` imports existing
  descriptor-only strict-validation request bundles and writes
  strict-validation descriptor preflight JSON/Parquet reports for planning
  only. Accepted rows mean `accepted_for_strict_validation_planning`; proxy-only
  descriptors, pre-2024 windows, missing source context, missing archive
  identity, missing validation requirements, and candidate-pack/promotion flags
  become blocked rows or fail closed before output.

If older documents say the current branch is `research/v3-experimental-engine`,
prefer this index plus WPR106-21 and later R106 reports for local checkout
facts.

## Active Stage

- Current stage: Stage R106 centralized historical data catalog complete,
  fail-closed no-candidate decision.
- Current stage owner: Codex Research Agent.
- Latest local v2 roadmap status packet:
  `docs/work_packets/WPR106-414-v2-roadmap-milestone-status-closeout.md`.
- Latest local v2 control-doc sync packet:
  `docs/work_packets/WPR106-415-v2-control-doc-sync-and-completion-audit.md`.
- V2 roadmap status:
  `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md` records Phases 0 through 22 and
  M0 through M5. This is a research-only platform foundation status, not a
  candidate-ready, paper/live, order, sizing, runtime-mode, or promotion claim.
- Latest local completion roadmap packet:
  `docs/work_packets/WPR106-360-research-engine-completion-roadmap.md`.
- Latest local completion roadmap expansion packet:
  `docs/work_packets/WPR106-361-research-engine-completion-roadmap-expansion.md`.
- Latest local post-audit sandbox safety packet:
  `docs/work_packets/WPR106-362-post-audit-sandbox-safety-coherence.md`.
- Latest local post-audit red-test repair packet:
  `docs/work_packets/WPR106-363-red-test-repair-strategy-discovery-resume.md`.
- Latest local sandbox CI coverage packet:
  `docs/work_packets/WPR106-364-sandbox-ci-boundary-coverage.md`.
- Latest local sandbox commit-coherence classification packet:
  `docs/work_packets/WPR106-365-sandbox-commit-coherence-classification.md`.
- Latest local sandbox venue-expansion local materializer packet:
  `docs/work_packets/WPR106-366-sandbox-venue-expansion-local-materializer.md`.
- Latest local sandbox materializer catalog-discovery packet:
  `docs/work_packets/WPR106-367-sandbox-venue-expansion-materializer-catalog-discovery.md`.
- Latest local sandbox venue-expansion candidate-manifest export packet:
  `docs/work_packets/WPR106-368-sandbox-venue-expansion-candidate-manifest-export.md`.
- Latest local sandbox end-to-end venue-expansion fixture smoke packet:
  `docs/work_packets/WPR106-369-sandbox-end-to-end-venue-expansion-fixture-smoke.md`.
- Latest local sandbox strict-validation descriptor preflight packet:
  `docs/work_packets/WPR106-370-sandbox-strict-validation-descriptor-preflight.md`.
- Latest local completion roadmap:
  `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md`.
- Latest local sandbox foundation packet:
  `docs/work_packets/WPR106-228-rapid-strategy-iteration-sandbox-foundation.md`.
- Latest local sandbox foundation report:
  `docs/stage_reports/STAGE_R106_RAPID_STRATEGY_ITERATION_SANDBOX_FOUNDATION_REPORT.md`.
- Latest local sandbox CLI/archive-loader packet:
  `docs/work_packets/WPR106-229-rapid-strategy-sandbox-cli-and-archive-loader.md`.
- Latest local sandbox CLI/archive-loader report:
  `docs/stage_reports/STAGE_R106_RAPID_STRATEGY_SANDBOX_CLI_AND_ARCHIVE_LOADER_REPORT.md`.
- Latest local sandbox strategy-blueprint compiler packet:
  `docs/work_packets/WPR106-230-sandbox-strategy-blueprint-catalog-compiler.md`.
- Latest local sandbox strategy-blueprint compiler report:
  `docs/stage_reports/STAGE_R106_SANDBOX_STRATEGY_BLUEPRINT_CATALOG_COMPILER_REPORT.md`.
- Latest local sandbox exit/filter sweep-grid packet:
  `docs/work_packets/WPR106-231-sandbox-exit-filter-sweep-grid.md`.
- Latest local sandbox exit/filter sweep-grid report:
  `docs/stage_reports/STAGE_R106_SANDBOX_EXIT_FILTER_SWEEP_GRID_REPORT.md`.
- Latest local sandbox multi-venue archive-routing packet:
  `docs/work_packets/WPR106-232-sandbox-multi-venue-archive-routing.md`.
- Latest local sandbox multi-venue archive-routing report:
  `docs/stage_reports/STAGE_R106_SANDBOX_MULTI_VENUE_ARCHIVE_ROUTING_REPORT.md`.
- Latest local sandbox artifact-analytics CLI packet:
  `docs/work_packets/WPR106-233-sandbox-artifact-analytics-cli.md`.
- Latest local sandbox artifact-analytics CLI report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_ANALYTICS_CLI_REPORT.md`.
- Latest local sandbox suite batch-runner packet:
  `docs/work_packets/WPR106-234-sandbox-suite-batch-runner.md`.
- Latest local sandbox suite batch-runner report:
  `docs/stage_reports/STAGE_R106_SANDBOX_SUITE_BATCH_RUNNER_REPORT.md`.
- Latest local sandbox hypothesis-falsification packet:
  `docs/work_packets/WPR106-235-sandbox-hypothesis-falsification-index.md`.
- Latest local sandbox hypothesis-falsification report:
  `docs/stage_reports/STAGE_R106_SANDBOX_HYPOTHESIS_FALSIFICATION_INDEX_REPORT.md`.
- Latest local sandbox strict-validation request bundle packet:
  `docs/work_packets/WPR106-236-sandbox-strict-validation-request-bundle.md`.
- Latest local sandbox strict-validation request bundle report:
  `docs/stage_reports/STAGE_R106_SANDBOX_STRICT_VALIDATION_REQUEST_BUNDLE_REPORT.md`.
- Latest local sandbox artifact-catalog packet:
  `docs/work_packets/WPR106-237-sandbox-artifact-catalog.md`.
- Latest local sandbox artifact-catalog report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_REPORT.md`.
- Latest local sandbox archive-descriptor audit packet:
  `docs/work_packets/WPR106-238-sandbox-archive-descriptor-audit.md`.
- Latest local sandbox archive-descriptor audit report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARCHIVE_DESCRIPTOR_AUDIT_REPORT.md`.
- Latest local sandbox archive-manifest builder packet:
  `docs/work_packets/WPR106-239-sandbox-archive-manifest-builder.md`.
- Latest local sandbox archive-manifest builder report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARCHIVE_MANIFEST_BUILDER_REPORT.md`.
- Latest local sandbox global-leaderboard packet:
  `docs/work_packets/WPR106-240-sandbox-global-leaderboard.md`.
- Latest local sandbox global-leaderboard report:
  `docs/stage_reports/STAGE_R106_SANDBOX_GLOBAL_LEADERBOARD_REPORT.md`.
- Latest local sandbox strategy-catalog materializer packet:
  `docs/work_packets/WPR106-241-sandbox-strategy-catalog-materializer.md`.
- Latest local sandbox strategy-catalog materializer report:
  `docs/stage_reports/STAGE_R106_SANDBOX_STRATEGY_CATALOG_MATERIALIZER_REPORT.md`.
- Latest local sandbox agent iteration runner packet:
  `docs/work_packets/WPR106-242-sandbox-agent-iteration-runner.md`.
- Latest local sandbox agent iteration runner report:
  `docs/stage_reports/STAGE_R106_SANDBOX_AGENT_ITERATION_RUNNER_REPORT.md`.
- Latest local sandbox venue-export normalizer packet:
  `docs/work_packets/WPR106-243-sandbox-venue-export-normalizer.md`.
- Latest local sandbox venue-export normalizer report:
  `docs/stage_reports/STAGE_R106_SANDBOX_VENUE_EXPORT_NORMALIZER_REPORT.md`.
- Latest local sandbox compatibility preflight packet:
  `docs/work_packets/WPR106-244-sandbox-compatibility-preflight.md`.
- Latest local sandbox compatibility preflight report:
  `docs/stage_reports/STAGE_R106_SANDBOX_COMPATIBILITY_PREFLIGHT_REPORT.md`.
- Latest local sandbox iteration preflight-gate packet:
  `docs/work_packets/WPR106-245-sandbox-iteration-preflight-gate.md`.
- Latest local sandbox iteration preflight-gate report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_PREFLIGHT_GATE_REPORT.md`.
- Latest local sandbox suite preflight-gate packet:
  `docs/work_packets/WPR106-246-sandbox-suite-preflight-gate.md`.
- Latest local sandbox suite preflight-gate report:
  `docs/stage_reports/STAGE_R106_SANDBOX_SUITE_PREFLIGHT_GATE_REPORT.md`.
- Latest local sandbox sweep mask-cache packet:
  `docs/work_packets/WPR106-247-sandbox-sweep-mask-cache.md`.
- Latest local sandbox sweep mask-cache report:
  `docs/stage_reports/STAGE_R106_SANDBOX_SWEEP_MASK_CACHE_REPORT.md`.
- Latest local sandbox sweep market-array cache packet:
  `docs/work_packets/WPR106-248-sandbox-sweep-market-array-cache.md`.
- Latest local sandbox sweep market-array cache report:
  `docs/stage_reports/STAGE_R106_SANDBOX_SWEEP_MARKET_ARRAY_CACHE_REPORT.md`.
- Latest local sandbox shared-market metric-cache packet:
  `docs/work_packets/WPR106-249-sandbox-shared-market-metric-cache.md`.
- Latest local sandbox shared-market metric-cache report:
  `docs/stage_reports/STAGE_R106_SANDBOX_SHARED_MARKET_METRIC_CACHE_REPORT.md`.
- Latest local sandbox vectorized barrier-exits packet:
  `docs/work_packets/WPR106-250-sandbox-vectorized-barrier-exits.md`.
- Latest local sandbox vectorized barrier-exits report:
  `docs/stage_reports/STAGE_R106_SANDBOX_VECTORIZED_BARRIER_EXITS_REPORT.md`.
- Latest local sandbox parallel suite-runner packet:
  `docs/work_packets/WPR106-251-sandbox-parallel-suite-runner.md`.
- Latest local sandbox parallel suite-runner report:
  `docs/stage_reports/STAGE_R106_SANDBOX_PARALLEL_SUITE_RUNNER_REPORT.md`.
- Latest local sandbox artifact-integrity packet:
  `docs/work_packets/WPR106-252-sandbox-artifact-integrity-hashes.md`.
- Latest local sandbox artifact-integrity report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_INTEGRITY_HASHES_REPORT.md`.
- Latest local sandbox artifact-integrity verifier packet:
  `docs/work_packets/WPR106-253-sandbox-artifact-integrity-verifier.md`.
- Latest local sandbox artifact-integrity verifier report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_INTEGRITY_VERIFIER_REPORT.md`.
- Latest local sandbox artifact-catalog integrity-status packet:
  `docs/work_packets/WPR106-254-sandbox-artifact-catalog-integrity-status.md`.
- Latest local sandbox artifact-catalog integrity-status report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_INTEGRITY_STATUS_REPORT.md`.
- Latest local sandbox integrity-guarded consumers packet:
  `docs/work_packets/WPR106-255-sandbox-integrity-guarded-artifact-consumers.md`.
- Latest local sandbox integrity-guarded consumers report:
  `docs/stage_reports/STAGE_R106_SANDBOX_INTEGRITY_GUARDED_ARTIFACT_CONSUMERS_REPORT.md`.
- Latest local sandbox iteration-cache integrity-reuse packet:
  `docs/work_packets/WPR106-256-sandbox-iteration-cache-integrity-reuse.md`.
- Latest local sandbox iteration-cache integrity-reuse report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_CACHE_INTEGRITY_REUSE_REPORT.md`.
- Latest local sandbox archive-source integrity-metadata packet:
  `docs/work_packets/WPR106-257-sandbox-archive-source-integrity-metadata.md`.
- Latest local sandbox archive-source integrity-metadata report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARCHIVE_SOURCE_INTEGRITY_METADATA_REPORT.md`.
- Latest local sandbox archive-source integrity-guard packet:
  `docs/work_packets/WPR106-258-sandbox-archive-source-integrity-guard.md`.
- Latest local sandbox archive-source integrity-guard report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARCHIVE_SOURCE_INTEGRITY_GUARD_REPORT.md`.
- Latest local sandbox strict-request source-context packet:
  `docs/work_packets/WPR106-259-sandbox-strict-request-source-context.md`.
- Latest local sandbox strict-request source-context report:
  `docs/stage_reports/STAGE_R106_SANDBOX_STRICT_REQUEST_SOURCE_CONTEXT_REPORT.md`.
- Latest local sandbox archive-coverage matrix packet:
  `docs/work_packets/WPR106-260-sandbox-archive-coverage-matrix.md`.
- Latest local sandbox archive-coverage matrix report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARCHIVE_COVERAGE_MATRIX_REPORT.md`.
- Latest local sandbox archive-coverage CLI packet:
  `docs/work_packets/WPR106-261-sandbox-archive-coverage-cli.md`.
- Latest local sandbox archive-coverage CLI report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARCHIVE_COVERAGE_CLI_REPORT.md`.
- Latest local sandbox iteration archive-coverage step packet:
  `docs/work_packets/WPR106-262-sandbox-iteration-archive-coverage-step.md`.
- Latest local sandbox iteration archive-coverage step report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_ARCHIVE_COVERAGE_STEP_REPORT.md`.
- Latest local sandbox iteration agent-brief packet:
  `docs/work_packets/WPR106-263-sandbox-iteration-agent-brief.md`.
- Latest local sandbox iteration agent-brief report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_AGENT_BRIEF_REPORT.md`.
- Latest local sandbox iteration-index packet:
  `docs/work_packets/WPR106-264-sandbox-iteration-index.md`.
- Latest local sandbox iteration-index report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_INDEX_REPORT.md`.
- Latest local sandbox iteration-index CLI packet:
  `docs/work_packets/WPR106-265-sandbox-iteration-index-cli.md`.
- Latest local sandbox iteration-index CLI report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_INDEX_CLI_REPORT.md`.
- Latest local sandbox iteration action-queues packet:
  `docs/work_packets/WPR106-266-sandbox-iteration-action-queues.md`.
- Latest local sandbox iteration action-queues report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_ACTION_QUEUES_REPORT.md`.
- Latest local sandbox archive content-identity inference packet:
  `docs/work_packets/WPR106-267-sandbox-archive-content-identity-inference.md`.
- Latest local sandbox archive content-identity inference report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARCHIVE_CONTENT_IDENTITY_INFERENCE_REPORT.md`.
- Latest local sandbox strategy catalog header-alias packet:
  `docs/work_packets/WPR106-268-sandbox-strategy-catalog-header-aliases.md`.
- Latest local sandbox strategy catalog header-alias report:
  `docs/stage_reports/STAGE_R106_SANDBOX_STRATEGY_CATALOG_HEADER_ALIASES_REPORT.md`.
- Latest local sandbox venue identity-alias packet:
  `docs/work_packets/WPR106-269-sandbox-venue-identity-aliases.md`.
- Latest local sandbox venue identity-alias report:
  `docs/stage_reports/STAGE_R106_SANDBOX_VENUE_IDENTITY_ALIASES_REPORT.md`.
- Latest local sandbox iteration recent-window preset packet:
  `docs/work_packets/WPR106-270-sandbox-iteration-recent-window-presets.md`.
- Latest local sandbox iteration recent-window preset report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_RECENT_WINDOW_PRESETS_REPORT.md`.
- Latest local sandbox archive manifest window-filter packet:
  `docs/work_packets/WPR106-271-sandbox-archive-manifest-window-filter.md`.
- Latest local sandbox archive manifest window-filter report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARCHIVE_MANIFEST_WINDOW_FILTER_REPORT.md`.
- Latest local sandbox archive coverage requested-window packet:
  `docs/work_packets/WPR106-272-sandbox-archive-coverage-requested-window.md`.
- Latest local sandbox archive coverage requested-window report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARCHIVE_COVERAGE_REQUESTED_WINDOW_REPORT.md`.
- Latest local sandbox iteration index archive-window queue packet:
  `docs/work_packets/WPR106-273-sandbox-iteration-index-archive-window-queue.md`.
- Latest local sandbox iteration index archive-window queue report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_INDEX_ARCHIVE_WINDOW_QUEUE_REPORT.md`.
- Latest local sandbox full archive blocker-count packet:
  `docs/work_packets/WPR106-274-sandbox-full-archive-blocker-counts.md`.
- Latest local sandbox full archive blocker-count report:
  `docs/stage_reports/STAGE_R106_SANDBOX_FULL_ARCHIVE_BLOCKER_COUNTS_REPORT.md`.
- Latest local sandbox full preflight blocker-count packet:
  `docs/work_packets/WPR106-275-sandbox-full-preflight-blocker-counts.md`.
- Latest local sandbox full preflight blocker-count report:
  `docs/stage_reports/STAGE_R106_SANDBOX_FULL_PREFLIGHT_BLOCKER_COUNTS_REPORT.md`.
- Latest local sandbox action-queue rollup packet:
  `docs/work_packets/WPR106-276-sandbox-action-queue-rollups.md`.
- Latest local sandbox action-queue rollup report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ACTION_QUEUE_ROLLUPS_REPORT.md`.
- Latest local sandbox iteration source-context index packet:
  `docs/work_packets/WPR106-277-sandbox-iteration-source-context-index.md`.
- Latest local sandbox iteration source-context index report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_SOURCE_CONTEXT_INDEX_REPORT.md`.
- Latest local sandbox iteration artifact-availability index packet:
  `docs/work_packets/WPR106-278-sandbox-iteration-artifact-availability-index.md`.
- Latest local sandbox iteration artifact-availability index report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_ARTIFACT_AVAILABILITY_INDEX_REPORT.md`.
- Latest local sandbox iteration recommended-actions packet:
  `docs/work_packets/WPR106-279-sandbox-iteration-recommended-actions.md`.
- Latest local sandbox iteration recommended-actions report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_RECOMMENDED_ACTIONS_REPORT.md`.
- Latest local sandbox iteration agent action-plan packet:
  `docs/work_packets/WPR106-280-sandbox-iteration-agent-action-plan.md`.
- Latest local sandbox iteration agent action-plan report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_AGENT_ACTION_PLAN_REPORT.md`.
- Latest local sandbox iteration agent action-plan Parquet packet:
  `docs/work_packets/WPR106-281-sandbox-iteration-agent-action-plan-parquet.md`.
- Latest local sandbox iteration agent action-plan Parquet report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_AGENT_ACTION_PLAN_PARQUET_REPORT.md`.
- Latest local sandbox descriptor-source metric reuse packet:
  `docs/work_packets/WPR106-282-sandbox-descriptor-source-metric-reuse.md`.
- Latest local sandbox descriptor-source metric reuse report:
  `docs/stage_reports/STAGE_R106_SANDBOX_DESCRIPTOR_SOURCE_METRIC_REUSE_REPORT.md`.
- Latest local sandbox descriptor market-frame load-cache packet:
  `docs/work_packets/WPR106-283-sandbox-descriptor-market-frame-load-cache.md`.
- Latest local sandbox descriptor market-frame load-cache report:
  `docs/stage_reports/STAGE_R106_SANDBOX_DESCRIPTOR_MARKET_FRAME_LOAD_CACHE_REPORT.md`.
- Latest local sandbox readiness source-cache packet:
  `docs/work_packets/WPR106-284-sandbox-readiness-source-cache.md`.
- Latest local sandbox readiness source-cache report:
  `docs/stage_reports/STAGE_R106_SANDBOX_READINESS_SOURCE_CACHE_REPORT.md`.
- Latest local sandbox iteration market-data cache packet:
  `docs/work_packets/WPR106-285-sandbox-iteration-market-data-cache.md`.
- Latest local sandbox iteration market-data cache report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_MARKET_DATA_CACHE_REPORT.md`.
- Latest local sandbox suite market-data cache packet:
  `docs/work_packets/WPR106-286-sandbox-suite-market-data-cache.md`.
- Latest local sandbox suite market-data cache report:
  `docs/stage_reports/STAGE_R106_SANDBOX_SUITE_MARKET_DATA_CACHE_REPORT.md`.
- Latest local sandbox suite input-cache packet:
  `docs/work_packets/WPR106-287-sandbox-suite-input-cache.md`.
- Latest local sandbox suite input-cache report:
  `docs/stage_reports/STAGE_R106_SANDBOX_SUITE_INPUT_CACHE_REPORT.md`.
- Latest local sandbox gzip archive-loader packet:
  `docs/work_packets/WPR106-288-sandbox-gzip-archive-loader.md`.
- Latest local sandbox gzip archive-loader report:
  `docs/stage_reports/STAGE_R106_SANDBOX_GZIP_ARCHIVE_LOADER_REPORT.md`.
- Latest local sandbox header-aware ZIP loader packet:
  `docs/work_packets/WPR106-289-sandbox-header-aware-zip-loader.md`.
- Latest local sandbox header-aware ZIP loader report:
  `docs/stage_reports/STAGE_R106_SANDBOX_HEADER_AWARE_ZIP_LOADER_REPORT.md`.
- Latest local sandbox numeric timestamp unit normalizer packet:
  `docs/work_packets/WPR106-290-sandbox-numeric-timestamp-unit-normalizer.md`.
- Latest local sandbox numeric timestamp unit normalizer report:
  `docs/stage_reports/STAGE_R106_SANDBOX_NUMERIC_TIMESTAMP_UNIT_NORMALIZER_REPORT.md`.
- Latest local sandbox NDJSON archive-loader packet:
  `docs/work_packets/WPR106-291-sandbox-ndjson-archive-loader.md`.
- Latest local sandbox NDJSON archive-loader report:
  `docs/stage_reports/STAGE_R106_SANDBOX_NDJSON_ARCHIVE_LOADER_REPORT.md`.
- Latest local sandbox ZIP JSON member-loader packet:
  `docs/work_packets/WPR106-292-sandbox-zip-json-member-loader.md`.
- Latest local sandbox ZIP JSON member-loader report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ZIP_JSON_MEMBER_LOADER_REPORT.md`.
- Latest local sandbox venue price-alias packet:
  `docs/work_packets/WPR106-293-sandbox-venue-price-aliases.md`.
- Latest local sandbox venue price-alias report:
  `docs/stage_reports/STAGE_R106_SANDBOX_VENUE_PRICE_ALIASES_REPORT.md`.
- Latest local sandbox Hyperliquid L2 JSON loader packet:
  `docs/work_packets/WPR106-294-sandbox-hyperliquid-l2-json-loader.md`.
- Latest local sandbox Hyperliquid L2 JSON loader report:
  `docs/stage_reports/STAGE_R106_SANDBOX_HYPERLIQUID_L2_JSON_LOADER_REPORT.md`.
- Latest local sandbox TAR archive-loader packet:
  `docs/work_packets/WPR106-295-sandbox-tar-archive-loader.md`.
- Latest local sandbox TAR archive-loader report:
  `docs/stage_reports/STAGE_R106_SANDBOX_TAR_ARCHIVE_LOADER_REPORT.md`.
- Latest local sandbox compressed container-member packet:
  `docs/work_packets/WPR106-296-sandbox-compressed-container-members.md`.
- Latest local sandbox compressed container-member report:
  `docs/stage_reports/STAGE_R106_SANDBOX_COMPRESSED_CONTAINER_MEMBERS_REPORT.md`.
- Latest local sandbox container multimember-loader packet:
  `docs/work_packets/WPR106-297-sandbox-container-multimember-loader.md`.
- Latest local sandbox container multimember-loader report:
  `docs/stage_reports/STAGE_R106_SANDBOX_CONTAINER_MULTIMEMBER_LOADER_REPORT.md`.
- Latest local sandbox container member-metadata packet:
  `docs/work_packets/WPR106-298-sandbox-container-member-metadata.md`.
- Latest local sandbox container member-metadata report:
  `docs/stage_reports/STAGE_R106_SANDBOX_CONTAINER_MEMBER_METADATA_REPORT.md`.
- Latest local sandbox archive container audit/coverage packet:
  `docs/work_packets/WPR106-299-sandbox-archive-container-audit-coverage.md`.
- Latest local sandbox archive container audit/coverage report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARCHIVE_CONTAINER_AUDIT_COVERAGE_REPORT.md`.
- Latest local sandbox preflight container-metadata packet:
  `docs/work_packets/WPR106-300-sandbox-preflight-container-metadata.md`.
- Latest local sandbox preflight container-metadata report:
  `docs/stage_reports/STAGE_R106_SANDBOX_PREFLIGHT_CONTAINER_METADATA_REPORT.md`.
- Latest local sandbox run source container-metadata packet:
  `docs/work_packets/WPR106-301-sandbox-run-source-container-metadata.md`.
- Latest local sandbox run source container-metadata report:
  `docs/stage_reports/STAGE_R106_SANDBOX_RUN_SOURCE_CONTAINER_METADATA_REPORT.md`.
- Latest local sandbox iteration brief source-summary packet:
  `docs/work_packets/WPR106-302-sandbox-iteration-brief-source-summaries.md`.
- Latest local sandbox iteration brief source-summary report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_BRIEF_SOURCE_SUMMARIES_REPORT.md`.
- Latest local sandbox workbook strategy-catalog sheet packet:
  `docs/work_packets/WPR106-303-sandbox-workbook-strategy-catalog-sheets.md`.
- Latest local sandbox workbook strategy-catalog sheet report:
  `docs/stage_reports/STAGE_R106_SANDBOX_WORKBOOK_STRATEGY_CATALOG_SHEETS_REPORT.md`.
- Latest local sandbox iteration strategy-source summary packet:
  `docs/work_packets/WPR106-304-sandbox-iteration-strategy-source-summaries.md`.
- Latest local sandbox iteration strategy-source summary report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_STRATEGY_SOURCE_SUMMARIES_REPORT.md`.
- Latest local sandbox direct workbook sheet-provenance packet:
  `docs/work_packets/WPR106-305-sandbox-direct-workbook-sheet-provenance.md`.
- Latest local sandbox direct workbook sheet-provenance report:
  `docs/stage_reports/STAGE_R106_SANDBOX_DIRECT_WORKBOOK_SHEET_PROVENANCE_REPORT.md`.
- Latest local sandbox strategy source repair-queue packet:
  `docs/work_packets/WPR106-306-sandbox-strategy-source-repair-queue.md`.
- Latest local sandbox strategy source repair-queue report:
  `docs/stage_reports/STAGE_R106_SANDBOX_STRATEGY_SOURCE_REPAIR_QUEUE_REPORT.md`.
- Latest local sandbox strategy skipped-source sample packet:
  `docs/work_packets/WPR106-307-sandbox-strategy-skipped-source-samples.md`.
- Latest local sandbox strategy skipped-source sample report:
  `docs/stage_reports/STAGE_R106_SANDBOX_STRATEGY_SKIPPED_SOURCE_SAMPLES_REPORT.md`.
- Latest local sandbox archive skipped-file sample packet:
  `docs/work_packets/WPR106-308-sandbox-archive-skipped-file-samples.md`.
- Latest local sandbox archive skipped-file sample report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARCHIVE_SKIPPED_FILE_SAMPLES_REPORT.md`.
- Latest local sandbox archive coverage blocker sample packet:
  `docs/work_packets/WPR106-309-sandbox-archive-coverage-blocker-samples.md`.
- Latest local sandbox archive coverage blocker sample report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARCHIVE_COVERAGE_BLOCKER_SAMPLES_REPORT.md`.
- Latest local sandbox preflight blocker sample packet:
  `docs/work_packets/WPR106-310-sandbox-preflight-blocker-samples.md`.
- Latest local sandbox preflight blocker sample report:
  `docs/stage_reports/STAGE_R106_SANDBOX_PREFLIGHT_BLOCKER_SAMPLES_REPORT.md`.
- Latest local sandbox rejection/falsification sample packet:
  `docs/work_packets/WPR106-311-sandbox-rejection-falsification-samples.md`.
- Latest local sandbox rejection/falsification sample report:
  `docs/stage_reports/STAGE_R106_SANDBOX_REJECTION_FALSIFICATION_SAMPLES_REPORT.md`.
- Latest local sandbox iteration input replay context packet:
  `docs/work_packets/WPR106-312-sandbox-iteration-input-replay-context.md`.
- Latest local sandbox iteration input replay context report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_INPUT_REPLAY_CONTEXT_REPORT.md`.
- Latest local sandbox iteration input replay worklist packet:
  `docs/work_packets/WPR106-313-sandbox-iteration-input-replay-worklist.md`.
- Latest local sandbox iteration input replay worklist report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_INPUT_REPLAY_WORKLIST_REPORT.md`.
- Latest local sandbox iteration input replay path-readiness packet:
  `docs/work_packets/WPR106-314-sandbox-iteration-input-replay-path-readiness.md`.
- Latest local sandbox iteration input replay path-readiness report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_INPUT_REPLAY_PATH_READINESS_REPORT.md`.
- Latest local sandbox iteration input replay venue/window rollup packet:
  `docs/work_packets/WPR106-315-sandbox-iteration-input-replay-venue-window-rollups.md`.
- Latest local sandbox iteration input replay venue/window rollup report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_INPUT_REPLAY_VENUE_WINDOW_ROLLUPS_REPORT.md`.
- Latest local sandbox iteration input replay dedupe packet:
  `docs/work_packets/WPR106-316-sandbox-iteration-input-replay-dedupe-groups.md`.
- Latest local sandbox iteration input replay dedupe report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_INPUT_REPLAY_DEDUPE_GROUPS_REPORT.md`.
- Latest local sandbox iteration input replay batch-plan packet:
  `docs/work_packets/WPR106-317-sandbox-iteration-input-replay-batch-plan.md`.
- Latest local sandbox iteration input replay batch-plan report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_INPUT_REPLAY_BATCH_PLAN_REPORT.md`.
- Latest local sandbox artifact catalog replay batch-plan count packet:
  `docs/work_packets/WPR106-318-sandbox-artifact-catalog-replay-batch-plan-counts.md`.
- Latest local sandbox artifact catalog replay batch-plan count report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_REPLAY_BATCH_PLAN_COUNTS_REPORT.md`.
- Latest local sandbox artifact catalog replay batch-plan rollup packet:
  `docs/work_packets/WPR106-319-sandbox-artifact-catalog-replay-batch-plan-rollups.md`.
- Latest local sandbox artifact catalog replay batch-plan rollup report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_REPLAY_BATCH_PLAN_ROLLUPS_REPORT.md`.
- Latest local sandbox artifact catalog replay batch-plan archive-bucket packet:
  `docs/work_packets/WPR106-320-sandbox-artifact-catalog-replay-batch-plan-archive-buckets.md`.
- Latest local sandbox artifact catalog replay batch-plan archive-bucket report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_REPLAY_BATCH_PLAN_ARCHIVE_BUCKETS_REPORT.md`.
- Latest local sandbox artifact catalog replay bucket representative packet:
  `docs/work_packets/WPR106-321-sandbox-artifact-catalog-replay-bucket-representatives.md`.
- Latest local sandbox artifact catalog replay bucket representative report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_REPLAY_BUCKET_REPRESENTATIVES_REPORT.md`.
- Latest local sandbox artifact catalog replay bucket Parquet sidecars packet:
  `docs/work_packets/WPR106-322-sandbox-artifact-catalog-replay-bucket-parquet-sidecars.md`.
- Latest local sandbox artifact catalog replay bucket Parquet sidecars report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_REPLAY_BUCKET_PARQUET_SIDECARS_REPORT.md`.
- Latest local sandbox artifact catalog strict-validation bundle queue packet:
  `docs/work_packets/WPR106-323-sandbox-artifact-catalog-strict-validation-bundle-queue.md`.
- Latest local sandbox artifact catalog strict-validation bundle queue report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_STRICT_VALIDATION_BUNDLE_QUEUE_REPORT.md`.
- Latest local sandbox strict-validation bundle Parquet sidecar packet:
  `docs/work_packets/WPR106-324-sandbox-strict-validation-bundle-parquet-sidecar.md`.
- Latest local sandbox strict-validation bundle Parquet sidecar report:
  `docs/stage_reports/STAGE_R106_SANDBOX_STRICT_VALIDATION_BUNDLE_PARQUET_SIDECAR_REPORT.md`.
- Latest local sandbox strict-validation descriptor catalog sidecar packet:
  `docs/work_packets/WPR106-325-sandbox-strict-validation-descriptor-catalog-sidecar.md`.
- Latest local sandbox strict-validation descriptor catalog sidecar report:
  `docs/stage_reports/STAGE_R106_SANDBOX_STRICT_VALIDATION_DESCRIPTOR_CATALOG_SIDECAR_REPORT.md`.
- Latest local sandbox strict-validation descriptor bucket queue packet:
  `docs/work_packets/WPR106-326-sandbox-strict-validation-descriptor-bucket-queue.md`.
- Latest local sandbox strict-validation descriptor bucket queue report:
  `docs/stage_reports/STAGE_R106_SANDBOX_STRICT_VALIDATION_DESCRIPTOR_BUCKET_QUEUE_REPORT.md`.
- Latest local sandbox strict-validation descriptor bucket representative packet:
  `docs/work_packets/WPR106-327-sandbox-strict-validation-descriptor-bucket-representatives.md`.
- Latest local sandbox strict-validation descriptor bucket representative report:
  `docs/stage_reports/STAGE_R106_SANDBOX_STRICT_VALIDATION_DESCRIPTOR_BUCKET_REPRESENTATIVES_REPORT.md`.
- Latest local sandbox strict-validation descriptor priority queue packet:
  `docs/work_packets/WPR106-328-sandbox-strict-validation-descriptor-priority-queue.md`.
- Latest local sandbox strict-validation descriptor priority queue report:
  `docs/stage_reports/STAGE_R106_SANDBOX_STRICT_VALIDATION_DESCRIPTOR_PRIORITY_QUEUE_REPORT.md`.
- Latest local sandbox artifact catalog sidecar index packet:
  `docs/work_packets/WPR106-329-sandbox-artifact-catalog-sidecar-index.md`.
- Latest local sandbox artifact catalog sidecar index report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_SIDECAR_INDEX_REPORT.md`.
- Latest local sandbox artifact catalog sidecar file identity packet:
  `docs/work_packets/WPR106-330-sandbox-artifact-catalog-sidecar-file-identity.md`.
- Latest local sandbox artifact catalog sidecar file identity report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_SIDECAR_FILE_IDENTITY_REPORT.md`.
- Latest local sandbox artifact catalog iteration action-plan sidecar packet:
  `docs/work_packets/WPR106-331-sandbox-artifact-catalog-iteration-action-plan-sidecar.md`.
- Latest local sandbox artifact catalog iteration action-plan sidecar report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_ITERATION_ACTION_PLAN_SIDECAR_REPORT.md`.
- Latest local sandbox artifact catalog iteration action bucket sidecar packet:
  `docs/work_packets/WPR106-332-sandbox-artifact-catalog-iteration-action-bucket-sidecar.md`.
- Latest local sandbox artifact catalog iteration action bucket sidecar report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_ITERATION_ACTION_BUCKET_SIDECAR_REPORT.md`.
- Latest local sandbox artifact catalog iteration action bucket representative packet:
  `docs/work_packets/WPR106-333-sandbox-artifact-catalog-iteration-action-bucket-representatives.md`.
- Latest local sandbox artifact catalog iteration action bucket representative report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_ITERATION_ACTION_BUCKET_REPRESENTATIVES_REPORT.md`.
- Latest local sandbox analysis bucket rollups packet:
  `docs/work_packets/WPR106-334-sandbox-analysis-bucket-rollups.md`.
- Latest local sandbox analysis bucket rollups report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ANALYSIS_BUCKET_ROLLUPS_REPORT.md`.
- Latest local sandbox artifact catalog analysis bucket sidecar packet:
  `docs/work_packets/WPR106-335-sandbox-artifact-catalog-analysis-bucket-sidecar.md`.
- Latest local sandbox artifact catalog analysis bucket sidecar report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_ANALYSIS_BUCKET_SIDECAR_REPORT.md`.
- Latest local sandbox global bucket leaderboard packet:
  `docs/work_packets/WPR106-336-sandbox-global-bucket-leaderboard.md`.
- Latest local sandbox global bucket leaderboard report:
  `docs/stage_reports/STAGE_R106_SANDBOX_GLOBAL_BUCKET_LEADERBOARD_REPORT.md`.
- Latest local sandbox artifact catalog global bucket leaderboard metadata packet:
  `docs/work_packets/WPR106-337-sandbox-artifact-catalog-global-bucket-leaderboard-metadata.md`.
- Latest local sandbox artifact catalog global bucket leaderboard metadata report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_GLOBAL_BUCKET_LEADERBOARD_METADATA_REPORT.md`.
- Latest local sandbox artifact catalog global bucket top-buckets sidecar packet:
  `docs/work_packets/WPR106-338-sandbox-artifact-catalog-global-bucket-top-buckets-sidecar.md`.
- Latest local sandbox artifact catalog global bucket top-buckets sidecar report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_GLOBAL_BUCKET_TOP_BUCKETS_SIDECAR_REPORT.md`.
- Latest local sandbox artifact catalog global top-hypotheses sidecar packet:
  `docs/work_packets/WPR106-339-sandbox-artifact-catalog-global-top-hypotheses-sidecar.md`.
- Latest local sandbox artifact catalog global top-hypotheses sidecar report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_GLOBAL_TOP_HYPOTHESES_SIDECAR_REPORT.md`.
- Latest local sandbox artifact catalog global evidence-request sidecar packet:
  `docs/work_packets/WPR106-340-sandbox-artifact-catalog-global-evidence-request-sidecar.md`.
- Latest local sandbox artifact catalog global evidence-request sidecar report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_SIDECAR_REPORT.md`.
- Latest local sandbox artifact catalog global evidence-request bucket queue packet:
  `docs/work_packets/WPR106-341-sandbox-artifact-catalog-global-evidence-request-bucket-queue.md`.
- Latest local sandbox artifact catalog global evidence-request bucket queue report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_BUCKET_QUEUE_REPORT.md`.
- Latest local sandbox artifact catalog global evidence-request bucket representatives packet:
  `docs/work_packets/WPR106-342-sandbox-artifact-catalog-global-evidence-request-bucket-representatives.md`.
- Latest local sandbox artifact catalog global evidence-request bucket representatives report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_BUCKET_REPRESENTATIVES_REPORT.md`.
- Latest local sandbox artifact catalog global evidence-request metadata packet:
  `docs/work_packets/WPR106-343-sandbox-artifact-catalog-global-evidence-request-metadata.md`.
- Latest local sandbox artifact catalog global evidence-request metadata report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_METADATA_REPORT.md`.
- Latest local sandbox artifact catalog global evidence-request priority queue packet:
  `docs/work_packets/WPR106-344-sandbox-artifact-catalog-global-evidence-request-priority-queue.md`.
- Latest local sandbox artifact catalog global evidence-request priority queue report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_PRIORITY_QUEUE_REPORT.md`.
- Latest local sandbox global leaderboard evidence-request source-context packet:
  `docs/work_packets/WPR106-345-sandbox-global-leaderboard-evidence-request-source-context.md`.
- Latest local sandbox global leaderboard evidence-request source-context report:
  `docs/stage_reports/STAGE_R106_SANDBOX_GLOBAL_LEADERBOARD_EVIDENCE_REQUEST_SOURCE_CONTEXT_REPORT.md`.
- Latest local sandbox global evidence-request source buckets packet:
  `docs/work_packets/WPR106-346-sandbox-global-evidence-request-source-buckets.md`.
- Latest local sandbox global evidence-request source buckets report:
  `docs/stage_reports/STAGE_R106_SANDBOX_GLOBAL_EVIDENCE_REQUEST_SOURCE_BUCKETS_REPORT.md`.
- Latest local sandbox global evidence-request source summary packet:
  `docs/work_packets/WPR106-347-sandbox-global-evidence-request-source-summary.md`.
- Latest local sandbox global evidence-request source summary report:
  `docs/stage_reports/STAGE_R106_SANDBOX_GLOBAL_EVIDENCE_REQUEST_SOURCE_SUMMARY_REPORT.md`.
- Latest local sandbox global evidence-request source summary sidecar packet:
  `docs/work_packets/WPR106-348-sandbox-global-evidence-request-source-summary-sidecar.md`.
- Latest local sandbox global evidence-request source summary sidecar report:
  `docs/stage_reports/STAGE_R106_SANDBOX_GLOBAL_EVIDENCE_REQUEST_SOURCE_SUMMARY_SIDECAR_REPORT.md`.
- Latest local sandbox global evidence-request source window summary packet:
  `docs/work_packets/WPR106-349-sandbox-global-evidence-request-source-window-summary.md`.
- Latest local sandbox global evidence-request source window summary report:
  `docs/stage_reports/STAGE_R106_SANDBOX_GLOBAL_EVIDENCE_REQUEST_SOURCE_WINDOW_SUMMARY_REPORT.md`.
- Latest local sandbox global evidence-request source summary representatives
  packet:
  `docs/work_packets/WPR106-350-sandbox-global-evidence-request-source-summary-representatives.md`.
- Latest local sandbox global evidence-request source summary representatives
  report:
  `docs/stage_reports/STAGE_R106_SANDBOX_GLOBAL_EVIDENCE_REQUEST_SOURCE_SUMMARY_REPRESENTATIVES_REPORT.md`.
- Latest local sandbox global evidence-request source summary best-context
  packet:
  `docs/work_packets/WPR106-351-sandbox-global-evidence-request-source-summary-best-context.md`.
- Latest local sandbox global evidence-request source summary best-context
  report:
  `docs/stage_reports/STAGE_R106_SANDBOX_GLOBAL_EVIDENCE_REQUEST_SOURCE_SUMMARY_BEST_CONTEXT_REPORT.md`.
- Latest local sandbox global evidence-request source priority queue packet:
  `docs/work_packets/WPR106-352-sandbox-global-evidence-request-source-priority-queue.md`.
- Latest local sandbox global evidence-request source priority queue report:
  `docs/stage_reports/STAGE_R106_SANDBOX_GLOBAL_EVIDENCE_REQUEST_SOURCE_PRIORITY_QUEUE_REPORT.md`.
- Latest local sandbox artifact catalog agent navigation index packet:
  `docs/work_packets/WPR106-353-sandbox-artifact-catalog-agent-navigation-index.md`.
- Latest local sandbox artifact catalog agent navigation index report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_AGENT_NAVIGATION_INDEX_REPORT.md`.
- Latest local sandbox archive coverage venue expansion gaps packet:
  `docs/work_packets/WPR106-354-sandbox-archive-coverage-venue-expansion-gaps.md`.
- Latest local sandbox archive coverage venue expansion gaps report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARCHIVE_COVERAGE_VENUE_EXPANSION_GAPS_REPORT.md`.
- Latest local sandbox iteration venue expansion gap handoff packet:
  `docs/work_packets/WPR106-355-sandbox-iteration-venue-expansion-gap-handoff.md`.
- Latest local sandbox iteration venue expansion gap handoff report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_VENUE_EXPANSION_GAP_HANDOFF_REPORT.md`.
- Latest local sandbox venue expansion request bundle packet:
  `docs/work_packets/WPR106-357-sandbox-venue-expansion-request-bundle.md`.
- Latest local sandbox venue expansion request bundle report:
  `docs/stage_reports/STAGE_R106_SANDBOX_VENUE_EXPANSION_REQUEST_BUNDLE_REPORT.md`.
- Latest local sandbox self-audit next-agent handoff:
  `docs/NEXT_AGENT_HANDOFF_WPR106_358_SANDBOX_SELF_AUDIT.md`.
- Latest local sandbox self-audit next-agent handoff packet:
  `docs/work_packets/WPR106-358-sandbox-self-audit-next-agent-handoff.md`.
- Latest local sandbox self-audit next-agent handoff report:
  `docs/stage_reports/STAGE_R106_SANDBOX_SELF_AUDIT_NEXT_AGENT_HANDOFF_REPORT.md`.
- Latest local sandbox next-action dashboard packet:
  `docs/work_packets/WPR106-371-sandbox-next-action-dashboard.md`.
- Latest local sandbox next-action dashboard report:
  `docs/stage_reports/STAGE_R106_SANDBOX_NEXT_ACTION_DASHBOARD_REPORT.md`.
- Latest local sandbox throughput telemetry packet:
  `docs/work_packets/WPR106-372-sandbox-throughput-telemetry-report.md`.
- Latest local sandbox throughput telemetry report:
  `docs/stage_reports/STAGE_R106_SANDBOX_THROUGHPUT_TELEMETRY_REPORT.md`.
- Latest local backtest fill-semantics compatibility packet:
  `docs/work_packets/WPR106-373-backtest-fill-semantics-compatibility.md`.
- Latest local backtest fill-semantics compatibility report:
  `docs/stage_reports/STAGE_R106_BACKTEST_FILL_SEMANTICS_COMPATIBILITY_REPORT.md`.
- Latest local sandbox catalog exit-profile semantics packet:
  `docs/work_packets/WPR106-374-sandbox-catalog-exit-profile-semantics.md`.
- Latest local sandbox catalog exit-profile semantics report:
  `docs/stage_reports/STAGE_R106_SANDBOX_CATALOG_EXIT_PROFILE_SEMANTICS_REPORT.md`.
- Latest local sandbox container loader bounds packet:
  `docs/work_packets/WPR106-375-sandbox-container-loader-bounds.md`.
- Latest local sandbox container loader bounds report:
  `docs/stage_reports/STAGE_R106_SANDBOX_CONTAINER_LOADER_BOUNDS_REPORT.md`.
- Latest local deterministic archive fixture checksum packet:
  `docs/work_packets/WPR106-376-deterministic-archive-fixture-checksums.md`.
- Latest local deterministic archive fixture checksum report:
  `docs/stage_reports/STAGE_R106_DETERMINISTIC_ARCHIVE_FIXTURE_CHECKSUMS_REPORT.md`.
- Latest local sandbox publication coherence packet:
  `docs/work_packets/WPR106-377-sandbox-publication-coherence.md`.
- Latest local sandbox publication coherence report:
  `docs/stage_reports/STAGE_R106_SANDBOX_PUBLICATION_COHERENCE_REPORT.md`.
- Latest local sandbox workbook intake bounds and xls policy packet:
  `docs/work_packets/WPR106-378-sandbox-workbook-intake-bounds-and-xls-policy.md`.
- Latest local sandbox workbook intake bounds and xls policy report:
  `docs/stage_reports/STAGE_R106_SANDBOX_WORKBOOK_INTAKE_BOUNDS_AND_XLS_POLICY_REPORT.md`.
- Latest local sandbox source discovery bounds packet:
  `docs/work_packets/WPR106-379-sandbox-source-discovery-bounds.md`.
- Latest local sandbox source discovery bounds report:
  `docs/stage_reports/STAGE_R106_SANDBOX_SOURCE_DISCOVERY_BOUNDS_REPORT.md`.
- Latest local sandbox CI validation coverage packet:
  `docs/work_packets/WPR106-380-sandbox-ci-validation-coverage.md`.
- Latest local sandbox CI validation coverage report:
  `docs/stage_reports/STAGE_R106_SANDBOX_CI_VALIDATION_COVERAGE_REPORT.md`.
- Latest local sandbox next-action unindexed iteration manifests packet:
  `docs/work_packets/WPR106-381-sandbox-next-action-unindexed-iteration-manifests.md`.
- Latest local sandbox next-action unindexed iteration manifests report:
  `docs/stage_reports/STAGE_R106_SANDBOX_NEXT_ACTION_UNINDEXED_ITERATION_MANIFESTS_REPORT.md`.
- Latest local sandbox CLI publication coherence packet:
  `docs/work_packets/WPR106-382-sandbox-cli-publication-coherence.md`.
- Latest local sandbox CLI publication coherence report:
  `docs/stage_reports/STAGE_R106_SANDBOX_CLI_PUBLICATION_COHERENCE_REPORT.md`.
- Latest local historical fixture cycle runtime bound packet:
  `docs/work_packets/WPR106-383-historical-fixture-cycle-runtime-bound.md`.
- Latest local historical fixture cycle runtime bound report:
  `docs/stage_reports/STAGE_R106_HISTORICAL_FIXTURE_CYCLE_RUNTIME_BOUND_REPORT.md`.
- Latest local sandbox package root lazy exports packet:
  `docs/work_packets/WPR106-384-sandbox-package-root-lazy-exports.md`.
- Latest local sandbox package root lazy exports report:
  `docs/stage_reports/STAGE_R106_SANDBOX_PACKAGE_ROOT_LAZY_EXPORTS_REPORT.md`.
- Latest local sandbox archive sweep sequential descriptor loading packet:
  `docs/work_packets/WPR106-385-sandbox-archive-sweep-sequential-descriptor-loading.md`.
- Latest local sandbox archive sweep sequential descriptor loading report:
  `docs/stage_reports/STAGE_R106_SANDBOX_ARCHIVE_SWEEP_SEQUENTIAL_DESCRIPTOR_LOADING_REPORT.md`.
- Sandbox research contract:
  `docs/contracts/sandbox_research_contract.md`.
- Latest WPR106-56 complete empirical development/stage decision packet:
  `docs/work_packets/WPR106-56-complete-empirical-development-and-stage-decision.md`.
- Latest local final autopilot hardening packet:
  `docs/work_packets/WPR106-66-autopilot-forced-cycle-schema-handoff.md`.
- Prior local final autopilot hardening packet:
  `docs/work_packets/WPR106-65-autopilot-new-compute-action.md`.
- Prior local final autopilot hardening packet:
  `docs/work_packets/WPR106-64-final-autopilot-hardening-and-docs.md`.
- Latest local autopilot compute-semantics packet:
  `docs/work_packets/WPR106-63-autopilot-new-iteration-compute-semantics.md`.
- Latest 2024-forward research documentation packet:
  `docs/work_packets/WPR106-226-2024-forward-results-catalog-and-lead-docs.md`.
- Latest 2024-forward results and leads catalog:
  `docs/research_knowledge/WPR106-220-225-2024-forward-results-and-leads-catalog.md`.
- Latest 2024-forward documentation report:
  `docs/stage_reports/STAGE_R106_2024_FORWARD_RESULTS_CATALOG_AND_LEAD_DOCS_REPORT.md`.
- Latest WPR106-56 complete empirical development/stage decision report:
  `docs/stage_reports/STAGE_R106_COMPLETE_EMPIRICAL_DEVELOPMENT_AND_STAGE_DECISION_REPORT.md`.
- Latest WPR106-55 next-agent complete-development handoff packet:
  `docs/work_packets/WPR106-55-next-agent-complete-development-handoff.md`.
- Latest WPR106-55 next-agent handoff prompt:
  `docs/NEXT_AGENT_HANDOFF_WPR106_55_COMPLETE_DEVELOPMENT_PROMPT.md`.
- Latest WPR106-54 finish-development closeout packet:
  `docs/work_packets/WPR106-54-finish-development-and-stage-closeout.md`.
- Latest WPR106-54 finish-development closeout report:
  `docs/stage_reports/STAGE_R106_FINISH_DEVELOPMENT_AND_STAGE_CLOSEOUT_REPORT.md`.
- Latest WPR106-53 operator UI logic reliability audit packet:
  `docs/work_packets/WPR106-53-operator-ui-logic-reliability-audit.md`.
- Latest WPR106-53 operator UI logic reliability audit report:
  `docs/stage_reports/STAGE_R106_OPERATOR_UI_LOGIC_RELIABILITY_AUDIT_REPORT.md`.
- Previous WPR106-52 GitHub CLI/UI connector review and optimization packet:
  `docs/work_packets/WPR106-52-github-cli-ui-connector-review-and-optimization.md`.
- Previous WPR106-52 connector review report:
  `docs/stage_reports/STAGE_R106_GITHUB_CLI_UI_CONNECTOR_REVIEW_AND_OPTIMIZATION_REPORT.md`.
- Latest WPR106-51 complete review hardening and publish packet:
  `docs/work_packets/WPR106-51-complete-review-hardening-and-publish.md`.
- Latest WPR106-50 full-codebase validation/performance audit packet:
  `docs/work_packets/WPR106-50-full-codebase-validation-and-performance-audit.md`.
- Latest WPR106-49 replay-scope validation manifest refresh packet:
  `docs/work_packets/WPR106-49-replay-scope-validation-manifests-and-eligibility-refresh.md`.
- Latest WPR106-48 first-class negative-control hardening packet:
  `docs/work_packets/WPR106-48-first-class-negative-controls-modern-window-and-hardening.md`.
- Latest WPR106-47 replay exit-lab/control audit packet:
  `docs/work_packets/WPR106-47-full-replay-exit-lab-and-negative-controls.md`.
- Latest closed exact replay overlay domain/cycle implementation packet:
  `docs/work_packets/WPR106-46-exact-replay-overlay-domain-and-cycle.md`.
- Latest closed reusable replay preflight contract packet:
  `docs/work_packets/WPR106-45-replay-overlay-preflight-contract.md`.
- Latest closed empirical preflight packet:
  `docs/work_packets/WPR106-44-replay-overlay-cycle-spec-preflight.md`.
- Latest closed compatibility packet:
  `docs/work_packets/WPR106-43-discovery-replay-spec-schema-compatibility.md`.
- Latest closed overlay infrastructure packet:
  `docs/work_packets/WPR106-42-candidate-scoped-replay-overlay-cycle-gates.md`.
- Latest closed empirical replay packet:
  `docs/work_packets/WPR106-31-discovery-lead-replay-entry-evidence.md`.
- Latest replay evidence report:
  `docs/stage_reports/STAGE_R106_DISCOVERY_LEAD_REPLAY_ENTRY_EVIDENCE_REPORT.md`.

WPR106-31 produced real replayed KNN/strategy-accounting artifacts and
annotated entry-signal evidence for 24 BTC and 24 ETH materialized discovery
leads. It also recorded bounded top-3 frozen-entry exit-lab slices blocked by
no improvement over fixed holding. This is evidence, not candidate readiness.
WPR106-47 verified the local full 24-lead-per-symbol frozen-entry exit-lab
artifacts and added a separate audit manifest for full-window, modern-window,
negative-control, and eligibility status without candidate-ready claims.
WPR106-48 adds first-class negative-control artifacts for shuffled labels,
shifted context, no-KNN overlay, and no-regime backend controls. All 192
control rows remain blocked because replay profile provenance, validation
manifest evidence, and modern-window evidence are missing, but the controls are
now structurally labeled `artifact_family: negative_control`,
`control_only: true`, and `candidate_evidence: false`.
WPR106-49 materializes replay-scope multiple-testing and validation-floor
manifests for all 48 WPR106-31 replay leads and refreshes BTC/ETH eligibility
audits. Missing-manifest blockers are removed for this evidence scope, but all
48 rows remain blocked and no candidate pack is written.
WPR106-50 runs broad compile, full-suite, grouped, benchmark-focused, and CLI
performance validation. It fixes a checked-config relative path bug in the
research-experiment benchmark command and removes repeated legacy pandas
FutureWarnings without changing candidate gates or runtime behavior.
WPR106-51 performs the final broad review, validation, and publish hardening
pass over the inherited WPR106-48 through WPR106-50 worktree. It confirms
compile, contracts, full-suite, focused touched-path validation, and diff
hygiene; hardens replay provenance, negative-control row validation,
candidate-pack runtime-mode-change rejection, benchmark nested path
resolution, and Lorentzian warning cleanup; tightens the known-issue template
so naive counters do not report a fake open template issue; and preserves zero
eligible candidates with no candidate pack, live, paper, order-placement,
sizing, runtime, or promotion claim.
WPR106-52 installs GitHub CLI 2.93.0, confirms local `gh` is available but not
authenticated, records the desktop GitHub connector MCP startup timeout as an
external connector limitation, and hardens UI/research connector paths. The
standalone research UI mutating API now requires a configured operator secret
token and rejects cross-origin writes; generic non-promotable manifests are
shown as research boundary review rather than promotion candidates; operator
artifact indexing skips `trials/`; provider pipeline, research experiment, and
historical-cycle output dirs fail closed outside the configured research output
root; data-pipeline stage paths prefer the owning spec directory over launch
CWD; and negative-control availability blocks no-effect shuffled-label and
weak shifted-context evidence. Final validation reports 1552 passed, 1 skipped,
and 2 warnings. No candidate pack, live/paper/order/sizing/runtime/promotion
behavior is introduced.
WPR106-53 performs the follow-up operator UI logic reliability audit. It
hardens logout CSRF handling, mutating JSON-route validation, worker-time
research/live-boundary checks, public health redaction, artifact scan
offloading, command debouncing, visible browser error states, symbol-scoped
research evidence selection, backend-owned BTC/ETH evidence bundle sequencing,
and standalone boundary-review links/scan bounds. Final validation reports
1561 passed, 1 skipped, and 1 XGBoost environment warning. No candidate pack,
live/paper/order/sizing/runtime authorization, or promotion behavior is
introduced.
WPR106-54 performs the finish-development closeout pass. It verifies the
pre-closeout PR #2 head was open, draft, mergeable, and green at `3681fc9`;
verifies PR #1 is superseded by PR #2 because PR #2 contains PR #1's head plus
four additional commits; records that remote draft PR state was not mutated
without explicit merge/close authorization; and refreshes closeout
documentation. Baseline validation passes with
`python -m compileall -q src/tradingbotsuite` and
`PYTHONPATH=src python -m pytest tests/contracts -q` reporting 441 passed. No
candidate pack, live/paper/order/sizing/runtime authorization, or promotion
behavior is introduced.
WPR106-56 completes the empirical development decision from cleaned merged
`main`. The R106 Historical Data Catalog is candidate-depth ready for BTCUSDT
and ETHUSDT, active exact discovery completed 570,240 trials per symbol, active
historical cycles ranked 63 rejected candidates per symbol, WPR106-29
materialized active multiple-testing/validation-floor/capped eligibility
evidence with 22,560 BTC and 23,040 ETH blocked rows, WPR106-49 confirms all 48
replay rows remain blocked, and no candidate pack exists. `ISSUE-R104-001` is
resolved as a fail-closed no-candidate outcome, not as candidate readiness or
promotion readiness.
Local WPR106-63 through WPR106-66 harden Research Autopilot after the stage
decision. Autopilot now reports `reused_existing_evidence`,
`refreshed_downstream_evidence`, `executed_upstream_compute`, `blocked`, or
`failed` explicitly. `Run New Compute Iteration` is the deliberate operator path
for isolated cycle/discovery/downstream recompute when current artifacts already
exist. `Review Existing Evidence` is the fast cache/reuse audit. Downstream-only
eligibility refresh is not a new upstream iteration. Forced cycle handoff keeps
strict `historical_research_cycle` specs free of operator-only metadata.

## Legacy R106 Gate State

The inherited R106 strategy implementation surface is structurally complete for
its BTC/ETH evidence scope: active plugins, checked strategy configs, BTC/ETH
candidate blueprints, durable cycle configs, replay-overlay support, exit-lab,
multiple-testing, validation-floor, and candidate-eligibility surfaces all
exist and are contract-tested. Under v2, treat this as legacy/reference
research infrastructure and evidence, not as the full product scope.

No candidate-ready trading claim exists. No candidate pack should be written
from current evidence. Zero eligible candidates remains a valid research
outcome and a useful signal for refining the next strategy hypotheses.

Open P0 blockers stop stage advancement and empirical expansion until
resolved. Current open P0 count: 0.

Resolved P0 blockers in the active-index wave:

- `ISSUE-R106-008`: active index and ResearchEngineDeluxe identity were
  missing.
- `ISSUE-R106-009`: CI/reproducible install checks were missing.
- `ISSUE-R106-010`: synthetic fallback and source selection were not explicit
  enough.
- `ISSUE-R106-011`: generic purge was fixed-bar based rather than
  label/event-end aware.
- `ISSUE-R106-012`: lower-timeframe entry pricing was labeled but not used.
- `ISSUE-R106-013`: local credential files could imply Hyperliquid
  live/testnet enablement without an explicit env flag.
- `ISSUE-R106-014`: live artifact validation was not fail-closed for unknown
  or mode-ambiguous manifests.

Open P1 blockers: none.

Resolved P1 blockers:

- `ISSUE-R104-001`: resolved by WPR106-56 as a fail-closed no-candidate
  empirical outcome after expanded catalog readiness, active deep cycles,
  exact sweeps, active/replay gate materialization, and eligibility review.
  Resolution does not create a candidate-ready, paper-ready, live-ready, or
  promotion-ready claim.
- `ISSUE-R106-015`: resolved by WPR106-62 as stable exact-discovery overwrite
  fallback/reuse hardening.
- `ISSUE-R106-016`: resolved by WPR106-63 and hardened by WPR106-64 so
  downstream-only autopilot refresh, blocked runs, and failed runs are not
  mislabeled as new upstream compute.
- `ISSUE-R106-017`: resolved by WPR106-65 so the primary new-compute action
  sends `force_upstream_recompute: true`, while fast reused-evidence review is
  visibly separate.
- `ISSUE-R106-018`: resolved by WPR106-66 so forced autopilot writes
  historical-cycle operator metadata to a sidecar file instead of injecting
  unknown keys into strict cycle specs.

See `docs/KNOWN_ISSUES.md` for the blocking source of truth.

## Required Read Order

1. `AGENTS.md`
2. `docs/ACTIVE_INDEX.md`
3. `docs/PRODUCT_SCOPE.md`
4. `docs/V2_DECISION_REGISTER.md`
5. `docs/V2_NO_TOUCH_PATHS.md`
6. `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
7. `docs/V2_FUTURE_UI_DEFERRAL.md`
8. `docs/audit/V2_AUDIT_INDEX.md`
9. `docs/ORCHESTRATOR_STAGE_LEDGER.md`
10. `docs/KNOWN_ISSUES.md`
11. `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
12. Latest relevant `docs/stage_reports/STAGE_R106_*.md`
13. Relevant source and tests for the scoped packet

## Near-Term Work Order

Active v2 work should follow `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md`
and `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`. WPR106-391 through WPR106-416
implement the roadmap foundation through Phase 22 as a research-only v2
platform. Do not rerun early v2 foundation phases unless a new audit finds a
concrete gap. Future v2 work should be one of:

- an explicitly scoped independent audit/fix packet for existing v2 behavior;
- a later UI extension packet that preserves the `V2-AUD-UI-001` read-only
  boundary or explicitly scopes any new command delegation through workers;
- a new roadmap extension packet with contracts, tests, and research-only
  boundary proof.

Do not start paper/live features, order placement, sizing, runtime-mode
mutation, arbitrary Python strategy execution, or promotion behavior from the
v2 roadmap foundation.

Inherited R106 strategy and sandbox work remains useful as legacy/reference
research, but it is no longer the active product scope by itself.

New strategies, filters, models, and refinements should be added through
scoped research packets only when they advance the v2 roadmap or explicitly
classified legacy migration. Keep them research-only, comparator-backed, and
manifested so failures produce analyzable rejection data instead of vague
closed status.

With the active P0 blockers closed and candidate-scoped overlay routing in
place, WPR106-44 proved exact
WPR106-31 replay leads are not representable by the then-current
historical-cycle candidate contract. WPR106-45 turns that preflight into a
reusable research-only contract and reruns it against WPR106-31 artifacts,
again finding 48/48 replay leads unrepresentable with no overlay specs or
candidate packs emitted. WPR106-46 implements the Option A lane: exact replay
lead domains and `1h` KNN overlay horizons now have explicit tested support,
generated singleton overlay specs exist for all 48 WPR106-31 replay leads, and
bounded BTC/ETH smoke cycles prove candidate-scoped overlay provenance reaches
rankings, backtest index, and gate reports. Candidate packs remain blocked
because existing gates do not pass. Do not silently substitute current defaults
for replayed values. WPR106-47 then audits the existing full frozen-entry
exit-lab evidence for all 48 replay leads, records full-window evidence
separately from missing modern-window profiles, emits fail-closed
negative-control rows for missing shuffled-label/shifted-context/no-KNN/no-
regime artifacts, and runs eligibility review with zero eligible rows.
WPR106-48 turns those control rows into first-class fail-closed artifacts,
hardens candidate-pack bridge and pack validation against negative-control
inputs, and normalizes old replay-ledger compatibility columns at read time
without rewriting generated WPR106-31 evidence. WPR106-49 then materializes
the replay-scope multiple-testing and validation-floor manifests that WPR106-48
left missing, refreshes eligibility, removes the missing-manifest blockers, and
still confirms zero eligible rows and no candidate packs.

Broader research queue:

- Generate first-class modern-window replay artifacts instead of relabeling
  full-window evidence.
- Replace the WPR106-48 fail-closed first-class control blockers with real
  replay profile provenance, validation manifests, modern-window evidence, and
  source label/timestamp inputs before treating controls as available.
- Add passing replay validation evidence only through real evidence: current
  WPR106-49 multiple-testing and validation-floor manifests are materialized
  but blocked, so later expansion still needs split/window concentration,
  source capability, baseline, ablation, exit-lab, and full cycle-ranking
  evidence.
- Treat `ISSUE-R104-001` as resolved by WPR106-56's fail-closed no-candidate
  decision. New empirical expansion should open a new issue or packet instead
  of reusing that blocker.
- Use the WPR106-59/WPR106-64 testing-readiness and autopilot payloads before
  kicking off a new compute iteration: catalog reuse/check should be ready, no
  catalog rebuild should be active, autopilot status should distinguish reused
  evidence, downstream refresh, upstream compute, blocked, and failed states,
  and candidate eligibility should reflect latest same-symbol gate manifests
  when available.
- Keep approximate-current-domain overlays separate and explicitly labeled; they
  cannot claim exact WPR106-31 replay evidence.
- Keep live/paper runtime behavior, order placement, sizing, venue execution
  proof, and promotion handoff out of research packets unless a later ledger
  explicitly scopes them.

WPR106-39 also normalizes active discovery regime backend evidence:
GMM-backed regime/KNN outputs now carry explicit
`regime_model_backend: sklearn.mixture.GaussianMixture`, no-regime outputs
carry `regime_model_backend: none`, and `true_hmm_backend_used` remains false.
Legacy `hmm_*` field names remain compatibility fields only.

WPR106-40 adds venue-aware cost/fill profile metadata to research backtests and
historical-cycle cost-stress rows. The required cost-stress scenario set remains
intact, and Binance USDM historical cost evidence is explicitly
`historical_research_only_not_live_execution_proof`, not Hyperliquid execution
proof.

WPR106-41 adds parser-level schema guards and roundtrip validation for active
historical-cycle and discovery-run specs. Wrong `spec_version` values and
unknown active nested fields now fail closed, while known documentary metadata
in historical-cycle configs remains accepted.

WPR106-42 adds candidate-scoped materialized prediction overlay routing to the
historical-cycle runner. WPR106-31 replayed KNN prediction artifacts can now be
mapped to generated historical-cycle candidate IDs without applying one
candidate's prediction frame globally to every candidate in the feature set.
Overlay provenance is recorded in rankings, backtest index, and gate reports.
This is infrastructure only; no replay-overlay cycle outputs or candidate packs
were generated by WPR106-42.

WPR106-43 restores discovery lead replay spec compatibility after the schema
guard hardening. `discovery-lead-replay-spec-v1` is an accepted discovery-run
specialization again, `replay_metadata` is recognized, and arbitrary wrong
discovery `spec_version` values still fail closed.

WPR106-44 preflighted all 48 WPR106-31 replay leads for exact
candidate-scoped historical-cycle overlay execution. All prediction artifacts
and KNN manifests exist, but zero leads are exactly representable by the current
historical-cycle `hmm_knn_local_analog_filter_v2` candidate contract because
the replay leads use `1h` label horizons, `event_spacing_bars: 4`, and multiple
threshold values outside the current strategy metadata domain. No overlay cycle
specs or candidate packs were emitted; zero representable exact replay
candidates is valid evidence.

WPR106-45 codifies that exact replay-overlay preflight as reusable source and
tests. The reusable preflight checks strategy plugin holding-window support,
current strategy parameter domains, KNN prediction/manifest existence, manifest
research-boundary flags, split-safety status, prediction path match, and
prediction SHA match before any overlay spec can be trusted. A fresh BTC/ETH
rerun from the reusable utility again checked 48 replay leads, found all 48
prediction artifacts and KNN manifests, found 0 exact representable candidates,
and emitted no overlay specs or candidate packs.

WPR106-46 implements the Option A exact replay-overlay domain and cycle lane.
All 48 WPR106-31 replay leads are now representable by explicit `1h`
historical-cycle strategy-domain support, 48 singleton overlay specs were
generated locally, and bounded BTC/ETH smoke cycles produced rankings,
backtest-index rows, gate reports, and rejection reports with candidate-scoped
overlay provenance. No candidate pack was emitted, and `ISSUE-R104-001`
remained open at that point.

WPR106-47 adds the full replay exit-lab and negative-control audit packet. The
packet verifies 48 existing full frozen-entry exit-lab rows, all blocked by no
simple-runner improvement over fixed holding; records two full-window scope rows
available and two modern-window scope rows blocked by missing local modern
profiles; records 192 blocked control rows for missing shuffled-label,
shifted-context, no-KNN, and no-regime control artifacts; and runs BTC/ETH
eligibility bridge audits with 48 blocked rows, zero eligible candidates, and
no candidate packs.

WPR106-49 materializes replay-scope multiple-testing and validation-floor gate
artifacts for the 24 BTC and 24 ETH WPR106-31 replay leads, then refreshes
eligibility with those manifests wired in. Both symbols have 24 blocked
multiple-testing rows, 24 diagnostic validation-floor rows, 24 blocked
eligibility rows, zero eligible rows, and zero missing-manifest blockers. No
candidate pack was emitted.

WPR106-50 performs the full-codebase validation and diagnostic performance
audit. Final validation after fixes reports 1539 passed, 1 skipped, 1 warning;
`pip check` passes; grouped high-risk, benchmark/vector/GPU, integration,
top-level legacy, experiment-runner, and strategy-flow suites pass. CLI
benchmarks pass for historical medium repeat 2, discovery deep repeat 2,
hardware utilization, and the Phase 1 research-experiment benchmark. The
provider latest-month benchmark completes as report-only evidence because
repeat 1 lacks determinism/cache-reuse evidence.

WPR106-51 performs a final complete-review hardening and publish pass. Broad
validation remains green at 1544 passed, 1 skipped, and 1 XGBoost environment
warning; focused touched-path validation passes; retry-agent findings in
replay provenance, negative-control row trust, runtime-mode-change filtering,
benchmark nested path resolution, and Lorentzian warning cleanup are fixed;
the known-issue template no longer resembles a real open issue to naive
counters; `.pytest_cache` and root-level handoff prompts remain unstaged; no
candidate pack or live/paper/promotion behavior is introduced.
WPR106-52 follows with a connector/review/optimization hardening pass. GitHub
CLI is installed but unauthenticated, the desktop GitHub connector still times
out externally, UI/research write surfaces and output-root boundaries are
hardened, negative controls reject no-effect evidence, and the final full suite
passes at 1552 passed, 1 skipped, 2 warnings.
WPR106-53 follows with an operator UI logic reliability audit. It fixes
CSRF/JSON validation, redacts unauthenticated health details, rechecks
research-job live boundaries at worker time, makes command and refresh failure
states visible, symbol-scopes research evidence actions, routes the evidence
bundle through backend autopilot, and keeps standalone research UI scans and
boundary-review labels bounded and current. The final full suite passes at
1561 passed, 1 skipped, 1 warning.

## Non-Negotiable Research Boundary

- Research outputs are not live signals.
- Candidate gates must not be weakened.
- Zero eligible candidates is valid evidence.
- Synthetic data must be explicit and demo/test-only.
- Binance historical evidence is not Hyperliquid execution proof.
- Cost/fill profile metadata is research evidence only unless a later approved
  packet adds separate venue execution proof.
- Research/discovery config schemas must fail closed on misspelled active
  parser fields.
- GMM-backed regime logic must carry the true backend
  (`sklearn.mixture.GaussianMixture`) and must not be treated as true HMM
  evidence.
- Runtime, paper, live, order placement, live configuration, and promotion logic
  are out of scope for research packets unless a later ledger explicitly scopes
  them.

## Validation Baseline

Use focused validation for scoped work and broaden when shared contracts change:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

The checked-in CI baseline is `.github/workflows/research-validation.yml`. It
installs `.[dev]`, runs `pip check`, compiles `src/tradingbotsuite`, runs
contract tests, and runs focused live/artifact boundary tests. Optional
research, Crypto Lake, and GPU extras remain outside the baseline.
