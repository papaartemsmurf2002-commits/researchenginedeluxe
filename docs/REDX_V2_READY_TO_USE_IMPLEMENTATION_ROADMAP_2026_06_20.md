# ResearchEngineDeluxe v2 — Ready-to-Use Implementation Roadmap

**Repository target:** `papaartemsmurf2002-commits/researchenginedeluxe`
**Document status:** implementation-grade roadmap and execution contract
**Generated:** 2026-06-20
**Primary objective:** convert the repository into a research-only, data-first, multi-instrument Hyperliquid perpetual-futures research platform with owned data archives, strict validation, agent-safe strategy evaluation, append-only experiment records, Lead Book governance, and chunk-level migration audits.
**Output format:** Markdown
**Recommended repo path:** `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md`

---

## 0. Source basis, authority, and how implementers must use this document

This implementation roadmap is synthesized from the two provided source documents:

1. `REDX_V2_CEO_DIRECTION_AND_AUDIT_HELPER_2026_06_20.md`
   SHA-256: `11cba2581fbd290f8283ea4b6dabd5281513e28f792d214dbc707625cbbc4505`
2. `researchenginedeluxe_v2_multi_venue_perp_research_roadmap.md`
   SHA-256: `b0234fff1cbb07cedc4b5e744757c216c3f79f342beca9a4db99bf0f84290a67`

This document turns those direction documents into a concrete implementation plan. It is designed to be handed directly to implementation agents or engineers. It defines product boundaries, module boundaries, execution sequence, schemas, contracts, phase acceptance criteria, test names, audit gates, worker/job requirements, legacy migration workflow, and safe commands.

### 0.1 Authority order

When there is a conflict during implementation, resolve it in this order:

1. Explicit CEO decisions and clarifications captured in the CEO helper document.
2. Research-only and non-live boundary.
3. This implementation roadmap.
4. The uploaded practical v2 roadmap.
5. Older repo docs or historical handoffs.
6. Agent or developer preference.

No agent may silently override a CEO decision. If a conflict is found, the correct action is to record it in `docs/V2_DECISION_REGISTER.md` or `docs/audit/V2_AUDIT_INDEX.md` and block the specific chunk until resolved.

### 0.2 How to execute this roadmap

Implementation must proceed as a strangler migration, not a big-bang rewrite. Build v2 alongside legacy surfaces, inspect and classify legacy code before reuse, migrate useful pieces into v2 only through clear contracts, and freeze dangerous or obsolete surfaces in a no-touch registry.

Every substantial change must belong to a named audit chunk. Each audit chunk has:

- an audit ID;
- a bounded context;
- a small file scope;
- declared contracts;
- no-touch paths;
- tests;
- acceptance criteria;
- independent audit status.

No chunk is accepted merely because code runs locally. A chunk is accepted only when it passes its tests, preserves the research-only invariant, records artifacts/provenance where relevant, and is independently audited.

---

## 1. Final product doctrine

### 1.1 Canonical identity

ResearchEngineDeluxe v2 is:

```text
A research-only, data-first, multi-instrument perpetual-futures research platform
focused on Hyperliquid perpetuals above USD 5,000,000 daily notional volume,
with support for compatible multi-venue comparison data, strict validation,
owned data archives, agent-safe strategy evaluation, and audit-by-chunk migration.
```

### 1.2 What the system is for

The system must support this repeatable research loop:

```text
Discover liquid Hyperliquid perpetual universe
  -> collect raw venue data continuously and aggressively
  -> preserve raw payloads and official files immutably
  -> parse to source-equivalent bronze tables
  -> clean and validate silver market data
  -> produce strategy-ready gold panels/features
  -> expose deterministic historical slices through a lockbox-aware data service
  -> run strategy specs through controlled vectorized and event-driven engines
  -> apply fees, funding, spread, slippage, impact, and liquidity constraints
  -> write every trial, including failures, to an append-only ledger
  -> promote promising ideas only into a non-promotable Lead Book
  -> deep-validate one serious lead at a time
  -> allow only the top 3 survivors into final hard-test review
  -> never imply paper/live/trade readiness
```

### 1.3 What the system is not

This repository is not:

- a paper trading system;
- a live trading system;
- an execution system;
- a sizing system;
- an order-placement system;
- a deployment-ready trading bot;
- a candidate-pack production pipeline;
- a system allowed to imply live, paper, order, signal, or sizing readiness.

Any existing paper/live/runtime-adjacent code is legacy or boundary material unless separately scoped by a future explicit human decision outside this roadmap.

### 1.4 Non-negotiable invariant

Every artifact, command, run, dashboard, audit record, and result produced inside the repo must preserve the following invariant:

```json
{
  "research_only": true,
  "observe_only": true,
  "promotion_ready": false,
  "candidate_evidence": false,
  "candidate_pack_eligible": false,
  "live_signal": false,
  "paper_signal": false,
  "sizing_instruction": false,
  "order_placement_instruction": false,
  "runtime_mode_change": false
}
```

This invariant must appear in:

- `docs/PRODUCT_SCOPE.md`;
- `docs/V2_DECISION_REGISTER.md`;
- `docs/V2_NO_TOUCH_PATHS.md`;
- run manifests;
- validation manifests;
- Lead Book contract;
- ledger contract;
- audit prompts;
- CLI help for v2 commands where practical.

### 1.5 Allowed and disallowed language

Allowed language:

- research platform;
- research-only archive;
- non-promotable lead;
- sandbox lead;
- deep validation;
- final hard-test survivor;
- evidence readiness inside research context;
- historical robustness;
- blocker-free within backtest constraints.

Disallowed language unless explicitly negated:

- paper-ready;
- live-ready;
- trade-ready;
- deployment-ready;
- sizing-ready;
- order-ready;
- signal-ready;
- candidate-pack ready;
- guaranteed profitable;
- production trading strategy.

A final hard-test survivor means only that a lead survived the strictest available historical, out-of-sample, cost, liquidity, regime, robustness, data-integrity, and artifact-integrity checks without unresolved blockers. It does not mean the strategy should be traded.

---

## 2. CEO decisions converted into implementation facts

The following decisions are not optional implementation suggestions. They are development facts.

| Decision area | Final implementation fact | Required implementation consequence |
|---|---|---|
| Product identity | v2 canonical direction is approved. | Migrate current docs and defaults away from BTC/ETH-only framing. |
| Research-only boundary | Research-only is mandatory. Paper/live is not a future option for this repo. | Remove paper/live roadmap language; add boundary tests proving no paper/live/order/sizing behavior. |
| Migration style | Strangler migration. | Preserve, inspect, classify, fix, wrap, or migrate useful legacy code. No big-bang rewrite. |
| Legacy code | Legacy is not automatically obsolete. Useful pieces must be inspected and improved if needed before v2 migration. | Add legacy audit records and classification labels before reuse. |
| Legacy GUI | Frozen/drawer. | Do not prioritize UI early. Do not let old GUI define v2 behavior. |
| Old outputs | Old high-return and rejected outputs can become Lead Book sources or failure evidence. | Preserve old outputs; never silently delete evidence. |
| Lead Book | Canonical queue for serious ideas. Agents may create leads and approve only after manual human inspection. | Implement human inspection status and agent approval status. |
| Lead evidence | Stable, not 6 losing months/year, not profit from a few trades, at least 5 trades/month, unseen-month performance required. | Implement promotion gates in code. |
| ROI | Lead Book must include observed ROI and ROI projection fields. | Separate observed ROI from projection assumptions and projection confidence. |
| Archive | Repo must own its market data archive. | Backtests must use archive snapshots, not direct API pulls. |
| Archive layers | raw/bronze/silver/gold. | Implement the four-layer archive with clear contracts and provenance. |
| Collection posture | Aggressive collection of all available relevant data. | Design for candles, trades, funding, context, L2/BBO, official S3, and compatible venues. |
| Universe floor | USD 5M daily notional, no lower by default. | Evidence universe uses `dayNtlVlm >= 5_000_000`. Below-threshold data may be archived/sandboxed only. |
| Universe mode | Evidence requires as-of universe. Current universe is sandbox-only. | Every backtest manifest states universe mode and survivorship status. |
| HIP-3/RWA | Include if they pass threshold and metadata/coverage gates. | Universe manager supports HIP-3/RWA namespaces and reference-market metadata. |
| Validation | 2024+, 6 usable months minimum, 12 preferred, dynamic lockbox, full provenance. | Enforce in code, especially the backtest data service and ledger append validator. |
| Coverage | Default minimum coverage is 0.98. | Accepted evidence below 98% coverage fails. |
| Strategy interface | Declarative specs first, narrow Python plugins later. | No arbitrary Python execution by agents. |
| Backtest engines | Vectorized and event-driven are both first-class. | Design shared contracts early; vectorized handles broad sweeps; event-driven handles fill-sensitive research. |
| Costs | Conservative mandatory cost model. | Gross-only results cannot be promoted; fees/funding/spread/slippage/impact/liquidity stress required. |
| Ledger | Append-only ledger is canonical. | XLSX is generated view only; failed trials must be logged. |
| Deep validation | One serious lead at a time. | Broad sweeps are triage; expensive validation is serial. |
| Final hard test | Top 3 only. | Final hard-test workflow has max 3 active slots. |
| Workers | Dedicated workers required. | Collectors/backtests must not run inside ASGI/operator loop. |
| Jobs | Durable local job store first; queue abstraction later. | No ephemeral collectors or long backtests. |
| Security | Parallel hardening. | Track security/hygiene without derailing data/archive/backtest foundation unless same files or active risk. |
| Audit | Chunk-level audit required. | Add audit markers, audit index, no-touch registry, independent review workflow. |

---

## 3. Product scope, universe scope, and evidence scope

### 3.1 Default evidence universe

The default evidence universe is:

```yaml
default_evidence_universe:
  venue: hyperliquid
  market_type: perpetual
  min_day_notional_usd: 5000000
  selection_mode: as_of
  coverage_min: 0.98
  earliest_reported_backtest_start: "2024-01-01"
  minimum_usable_months: 6
  preferred_usable_months: 12
  lockbox_policy: dynamic_full_calendar_months
```

### 3.2 BTC and ETH role

BTC and ETH remain useful but must not define product scope. Use them as:

- fixture symbols;
- smoke tests;
- baseline sanity checks;
- high-liquidity reference instruments;
- legacy evidence symbols;
- comparator instruments.

Any doc, CLI default, test, fixture, or README sentence implying BTC/ETH are the entire research universe must be changed or marked historical.

### 3.3 Below-USD-5M instruments

Below-threshold instruments may be:

- archived;
- observed;
- used in diagnostic/sandbox-only tests;
- used as negative controls;
- stored in instrument catalog and universe snapshots with exclusion reason.

They may not be used as accepted evidence under the default v2 universe rule.

### 3.4 Current universe versus as-of universe

Use two universe modes:

```yaml
universe_modes:
  as_of:
    purpose: accepted historical research evidence
    accepted_research_evidence_allowed: true
    candidate_evidence_allowed: false
    survivorship_bias_status: pass_required
  current_labeled_sandbox:
    purpose: what looks interesting now
    candidate_evidence_allowed: false
    survivorship_bias_warning: true
  static_fixture:
    purpose: CI, examples, tiny deterministic tests
    candidate_evidence_allowed: false
```

Accepted evidence must use `as_of` universe snapshots. Current-universe backtests are allowed only if explicitly labeled sandbox/current research and blocked from evidence claims.

### 3.5 HIP-3/RWA inclusion

HIP-3/RWA/equity/commodity perps are included when they meet the same threshold and coverage gates. They require extra metadata:

```yaml
hip3_rwa_metadata_required:
  is_hip3_or_rwa: true
  dex_namespace: required
  reference_market: required
  oracle_source: required
  reference_session_calendar: required
  weekend_behavior_documented: required
  listing_age_days: required
  proxy_data_available: required
  market_hours_caveats: required
  special_event_calendar: optional_but_recommended
  special_caveats:
    - oracle_risk
    - session_gap_risk
    - short_history_risk
    - reference_market_holiday_risk
```

If this metadata is missing, the instrument may be archived but blocked from accepted evidence until resolved.

### 3.6 Cross-venue scope

Hyperliquid remains the default primary venue. Other venues are allowed as comparable data sources only if every row preserves venue provenance. Cross-venue data can support:

- proxy history;
- funding/OI comparison;
- reference markets;
- external validation;
- feature robustness;
- basis and lead-lag analysis;
- RWA reference context.

Cross-venue data must not dilute the default Hyperliquid-first identity.

---

## 4. Target architecture

### 4.1 Target dataflow

```text
Venue adapters
  -> aggressive data collectors and backfill jobs
  -> owned raw archive
  -> bronze source-equivalent tables
  -> silver cleaned market data
  -> gold strategy-ready panels/features
  -> instrument catalog and universe snapshots
  -> data quality and coverage service
  -> lockbox-aware backtest data service
  -> vectorized and event-driven backtest engines
  -> declarative strategy specs and later narrow Python plugins
  -> run artifacts and validation manifests
  -> append-only experiment ledger
  -> Lead Book
  -> deep validation runner
  -> final hard-test workflow
  -> eventual v2 UI after foundation is stable
```

### 4.2 Bounded contexts

| Context | Responsibility | Must not do |
|---|---|---|
| `venues` | API clients, WebSocket clients, S3/backfill clients, rate limits, raw fetches | score strategies, rank ledger, place orders |
| `collectors` | durable jobs for market-data collection | run inside UI/ASGI loop, mutate strategy results |
| `archive` | raw/bronze/silver/gold layout, manifests, hashes, snapshots | call venues directly except through adapter contracts |
| `universe` | instrument catalog, USD 5M eligibility, HIP-3/RWA namespace, as-of/current snapshots | cherry-pick winners |
| `data_quality` | gaps, duplicates, stale rows, coverage, abnormal values | silently repair without provenance |
| `backtest_data` | safe historical reads, lockbox enforcement, coverage enforcement, deterministic panels | mutate archive, bypass lockbox |
| `strategy_specs` | declarative strategy definitions and validation | execute arbitrary Python |
| `strategy_plugins` | later advanced Python protocol | use network, secrets, order paths, arbitrary file reads |
| `backtest_engine` | simulation, fills, costs, funding, metrics | network calls, secrets, direct data scraping |
| `costs` | fees, funding, spread, slippage, impact, liquidity participation, stress matrices | create signals or orders |
| `validation` | date gates, lockbox, walk-forward, overfit diagnostics, final hard-test rules | tune after seeing final/lockbox results |
| `agent_lab` | controlled strategy runs, manifests, result routing, command UX | direct spreadsheet editing, candidate claims |
| `ledger` | append-only experiment records and generated exports | manual row edits |
| `lead_book` | lead queue, human inspection state, agent approval, ROI projection fields | imply paper/live/trade readiness |
| `workers` | job store, worker entrypoints, heartbeats, retries | strategy logic or direct ledger mutation without validators |
| `audit` | chunk-level audits, markers, no-touch checks | broad unbounded rewrites |
| `ui` | eventual visibility surface | define core logic, run heavy jobs in-process |
| `security` | secrets, path policy, artifact safety, import boundaries, logging redaction | block foundation work unless same files or active risk |

### 4.3 Recommended package layout

Use the existing repository package convention if it already exists. The examples below use `src/tradingbotsuite/v2/` because the source documents reference `tradingbotsuite`. If the repo has standardized on another import root, keep the same bounded contexts and file names under that root.

```text
src/tradingbotsuite/v2/
  __init__.py
  cli/
    __init__.py
    main.py
    commands_archive.py
    commands_universe.py
    commands_collect.py
    commands_backtest.py
    commands_ledger.py
    commands_lead.py
    commands_audit.py
  config/
    __init__.py
    settings.py
    schemas.py
    defaults.py
  venues/
    __init__.py
    base.py
    hyperliquid/
      __init__.py
      client.py
      models.py
      info.py
      websocket.py
      s3_archive.py
      adapter.py
    ccxt_adapter.py
  archive/
    __init__.py
    layout.py
    paths.py
    schemas.py
    raw_writer.py
    parquet_writer.py
    manifest_store.py
    snapshots.py
    hashing.py
    rebuild.py
  universe/
    __init__.py
    models.py
    rules.py
    snapshots.py
    catalog.py
    hip3_rwa.py
  collectors/
    __init__.py
    jobs.py
    universe_refresh.py
    candle_bootstrap.py
    websocket_capture.py
    funding_backfill.py
    s3_backfill.py
  data_quality/
    __init__.py
    coverage.py
    gaps.py
    duplicates.py
    outliers.py
    reports.py
  backtest_data/
    __init__.py
    service.py
    policies.py
    panel_loader.py
    lockbox.py
    coverage_gate.py
    universe_gate.py
  strategy_specs/
    __init__.py
    schema.py
    validator.py
    declarative.py
    examples/
  strategy_plugins/
    __init__.py
    protocol.py
    sandbox.py
    registry.py
  backtest_engine/
    __init__.py
    vectorized.py
    event_driven.py
    portfolio.py
    fills.py
    metrics.py
    artifacts.py
    simulator_contracts.py
  costs/
    __init__.py
    fees.py
    funding.py
    slippage.py
    impact.py
    stress.py
    models.py
  validation/
    __init__.py
    date_rules.py
    walk_forward.py
    embargo.py
    pbo.py
    lead_gates.py
    final_hard_test.py
  ledger/
    __init__.py
    schemas.py
    append.py
    export.py
    leaderboard.py
  lead_book/
    __init__.py
    schemas.py
    store.py
    workflow.py
    approvals.py
  workers/
    __init__.py
    job_store.py
    runner.py
    heartbeat.py
    subprocess_worker.py
  audit/
    __init__.py
    markers.py
    registry.py
    checks.py
  security/
    __init__.py
    path_policy.py
    secrets.py
    artifact_safety.py
    import_boundaries.py
```

### 4.4 Recommended documentation layout

```text
docs/
  PRODUCT_SCOPE.md
  V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md
  V2_DECISION_REGISTER.md
  V2_NO_TOUCH_PATHS.md
  V2_LEGACY_CLASSIFICATION.md
  V2_TECHNOLOGY_DECISIONS.md
  V2_OPERATIONS_RUNBOOK.md
  DATA_ARCHIVE_CONTRACT.md
  BACKTEST_VALIDATION_CONTRACT.md
  contracts/
    archive_contract.md
    universe_contract.md
    venue_adapter_contract.md
    collector_job_contract.md
    data_quality_contract.md
    backtest_data_service_contract.md
    strategy_spec_contract.md
    strategy_plugin_contract.md
    backtest_engine_contract.md
    cost_model_contract.md
    run_artifact_contract.md
    ledger_contract.md
    lead_book_contract.md
    validation_contract.md
    worker_job_contract.md
    security_boundary_contract.md
  audit/
    V2_AUDIT_INDEX.md
    prompts/
      V2_CHUNK_AUDITOR_PROMPT.md
    records/
      V2-AUD-SCOPE-001.md
      V2-AUD-ARCH-001.md
      ...
```

---

## 5. Technology decisions

These are ready-to-implement defaults. If existing repo tooling differs, adapt only the integration layer and preserve the contracts.

### 5.1 Language and runtime

```yaml
runtime:
  language: python
  minimum_python: "3.11"
  recommended_python: "3.12 where repo support allows"
  timezone: UTC everywhere
  timestamps: timezone_aware_utc
  financial_raw_values: preserve raw strings when provided by venue
  normalized_numeric_values: Float64 or Decimal depending field criticality
```

### 5.2 Storage

```yaml
storage:
  raw_format: jsonl.zst_or_native_compressed
  primary_analytical_format: parquet
  manifest_format: parquet_with_json_exports_for_small_records
  archive_root_default: data/archive
  run_artifacts_root_default: runs
  hash_algorithm: sha256
  partitioning:
    bars: [venue, timeframe, date]
    trades: [venue, date, hour, instrument_id]
    l2book: [venue, date, hour, instrument_id]
    bbo: [venue, date, hour, instrument_id]
    funding: [venue, date]
    asset_context: [venue, date]
    universe: [venue, asof_date]
```

### 5.3 Query/dataframe engine

```yaml
analytics_engines:
  parquet_scan_sql: duckdb
  dataframe_lazy_pipeline: polars
  parquet_writer: pyarrow_or_polars
  csv_usage: fixtures_and_exports_only
  xlsx_usage: generated_view_only
```

### 5.4 Config and schemas

```yaml
config_and_schema:
  config_files: yaml
  config_validation: pydantic_models_or_existing_repo_schema_system
  strategy_specs: yaml_or_json_validated_before_execution
  manifests: json_for_run_artifacts_plus_parquet_for_central_manifest_tables
  schema_version_required: true
```

### 5.5 CLI

Use the existing CLI framework if present. If no framework exists, implement v2 CLI with `typer` or the repo-standard CLI mechanism. The command contract is more important than the library.

Required command groups:

```text
redx scope
redx audit
redx archive
redx universe
redx collect
redx data
redx strategy
redx backtest
redx ledger
redx lead
redx validate
redx worker
```

### 5.6 Job durability

```yaml
job_durability:
  first_target: local_sqlite_wal_job_store
  future_target: queue_adapter_possible
  ephemeral_jobs_allowed_for_collectors: false
  ephemeral_jobs_allowed_for_long_backtests: false
  worker_heartbeat_required: true
  retry_policy_required: true
```

SQLite is acceptable for the first durable local job store because job state is metadata, not the primary archive. Use WAL mode, clear state transitions, and schema migrations. Do not run heavy jobs inside the ASGI/operator process.

### 5.7 Security defaults

```yaml
security_defaults:
  secrets: fail_closed
  network_access_in_strategy_plugins: false
  arbitrary_file_reads_in_strategy_plugins: false
  direct_order_imports_in_v2: false
  unsafe_pickle_loading: blocked_unless_trusted_hash_and_trusted_root
  path_policy: required
  logging_redaction: required
  live_runtime_import_boundary_tests: required
```

---

## 6. Implementation invariants and cross-cutting rules

### 6.1 Research-only import boundary

New v2 modules must not import live trading, order placement, sizing runtime, exchange order adapters, or candidate-pack promotion modules except inside explicit no-touch boundary tests that assert they are not used.

Add tests similar to:

```python
def test_v2_core_has_no_live_order_imports():
    # Scan v2 source imports and fail on blocked modules.
    ...
```

Blocked concepts:

```yaml
blocked_import_concepts:
  - order_place
  - live_trade
  - paper_trade
  - sizing_runtime
  - execution_runtime
  - candidate_pack_promoter
  - broker_submit
```

### 6.2 No direct API pulls inside backtests

Backtests must not call venues or collectors. They read only through `backtest_data.service` using archive snapshot IDs. This prevents unmanifested data drift and hidden leakage.

### 6.3 No manual ledger/spreadsheet edits

The canonical ledger is append-only Parquet. CSV/XLSX are generated views. Agents and humans append only through `redx ledger append`, which validates manifests, hashes, lockbox status, coverage, schema version, and failure records.

### 6.4 No silent data repair

Missing data, duplicates, stale data, outliers, reconnect gaps, and parse errors must be recorded. A cleaning step may produce silver data, but it must record every material cleaning decision in a manifest.

### 6.5 Determinism

All accepted artifacts must be reproducible by manifest:

- code git SHA;
- environment hash or lockfile ID;
- strategy spec hash;
- params hash;
- archive snapshot ID;
- universe snapshot ID;
- feature snapshot ID if used;
- cost model ID;
- validation policy ID;
- run ID;
- artifact hash.

### 6.6 Every failure is evidence

Failed collector jobs, parse jobs, strategy trials, validation gates, ledger append attempts, and deep validation attempts are not noise. They must be logged, either as job failure records or ledger failure rows, depending on the layer.

---

## 7. Core contracts to create before implementation

The following contract files must be created early. Implementation can be incremental, but contracts must exist before code grows.

| Contract file | Purpose | Must include |
|---|---|---|
| `docs/PRODUCT_SCOPE.md` | Product identity and boundary | research-only invariant, USD 5M universe, no paper/live |
| `docs/V2_DECISION_REGISTER.md` | CEO decisions | D1-D29, status, owner, consequences |
| `docs/V2_NO_TOUCH_PATHS.md` | Prevent accidental mutation | live/runtime/order/sizing/old evidence/legacy GUI paths |
| `docs/V2_LEGACY_CLASSIFICATION.md` | Legacy reuse workflow | labels, inspection checklist, audit record schema |
| `docs/contracts/archive_contract.md` | Archive rules | raw/bronze/silver/gold, hashing, manifests, snapshots |
| `docs/contracts/universe_contract.md` | Universe rules | instrument catalog, `dayNtlVlm >= 5M`, as-of/current modes, HIP-3/RWA |
| `docs/contracts/venue_adapter_contract.md` | Venue adapters | capabilities, raw fetches, rate limits, provenance |
| `docs/contracts/collector_job_contract.md` | Durable collection | job schema, reconnect/gaps, retry/backfill |
| `docs/contracts/data_quality_contract.md` | Coverage and quality | coverage threshold, gaps, duplicates, stale/outlier checks |
| `docs/contracts/backtest_data_service_contract.md` | Safe reads | 2024+, 6 months, lockbox, coverage, snapshot enforcement |
| `docs/contracts/strategy_spec_contract.md` | Declarative strategies | schema, allowed expressions, validation, no arbitrary Python |
| `docs/contracts/strategy_plugin_contract.md` | Future plugins | narrow protocol, no network/secrets/order paths |
| `docs/contracts/backtest_engine_contract.md` | Engine outputs | vectorized/event-driven shared artifacts |
| `docs/contracts/cost_model_contract.md` | Costs | fees, funding, spread, slippage, impact, stress matrix |
| `docs/contracts/run_artifact_contract.md` | Run artifacts | manifest, metrics, equity, trades, positions, logs |
| `docs/contracts/ledger_contract.md` | Ledger | append-only Parquet, required columns, failed trial logging |
| `docs/contracts/lead_book_contract.md` | Leads | schema, statuses, ROI, human inspection, agent approval |
| `docs/contracts/validation_contract.md` | Validation | walk-forward, lockbox, PBO/CSCV, stability gates |
| `docs/contracts/worker_job_contract.md` | Workers | durable local job store, heartbeats, status transitions |
| `docs/contracts/security_boundary_contract.md` | Safety | no live imports, secrets, path policy, artifact safety |

---

## 8. Archive design and implementation contract

### 8.1 Archive principle

The archive is append-only at raw level, rebuildable at bronze/silver level, and snapshot-addressable at gold/research level.

Agents never edit archive files. Agents request data through the backtest data service. Every run records the archive snapshot used.

### 8.2 Archive layers in plain terms

| Layer | Plain-English meaning | Examples | Mutability |
|---|---|---|---|
| Raw | What the venue actually sent | WebSocket JSON, REST responses, S3 files | append-only, never edited |
| Bronze | Parsed source tables | trades table, candles table, asset context rows | rebuildable from raw |
| Silver | Clean research market data | deduped bars, normalized funding, aligned timestamps | rebuildable with cleaning manifests |
| Gold | Strategy-ready panels/features | multi-instrument panels, rolling features, fold matrices | versioned snapshots only |

### 8.3 Archive directory layout

```text
data/archive/
  raw/
    venue=hyperliquid/
      datatype=meta_and_asset_ctxs/date=YYYY-MM-DD/run_id=.../*.jsonl.zst
      datatype=all_dexs_asset_ctxs/date=YYYY-MM-DD/run_id=.../*.jsonl.zst
      datatype=candles/interval=1m/date=YYYY-MM-DD/instrument=.../*.jsonl.zst
      datatype=trades/date=YYYY-MM-DD/hour=HH/instrument=.../*.jsonl.zst
      datatype=l2book/date=YYYY-MM-DD/hour=HH/instrument=.../*.jsonl.zst
      datatype=bbo/date=YYYY-MM-DD/hour=HH/instrument=.../*.jsonl.zst
      datatype=funding_history/date=YYYY-MM-DD/instrument=.../*.jsonl.zst
      datatype=s3_l2book/date=YYYY-MM-DD/hour=HH/instrument=.../*.lz4
  bronze/
    venue=hyperliquid/datatype=trades/date=YYYY-MM-DD/hour=HH/*.parquet
    venue=hyperliquid/datatype=candles/interval=1m/date=YYYY-MM-DD/*.parquet
    venue=hyperliquid/datatype=funding/date=YYYY-MM-DD/*.parquet
    venue=hyperliquid/datatype=asset_ctx/date=YYYY-MM-DD/*.parquet
    venue=hyperliquid/datatype=l2book/date=YYYY-MM-DD/hour=HH/*.parquet
    venue=hyperliquid/datatype=bbo/date=YYYY-MM-DD/hour=HH/*.parquet
  silver/
    bars/timeframe=1m/venue=hyperliquid/date=YYYY-MM-DD/*.parquet
    bars/timeframe=5m/venue=hyperliquid/date=YYYY-MM-DD/*.parquet
    bars/timeframe=15m/venue=hyperliquid/date=YYYY-MM-DD/*.parquet
    bars/timeframe=1h/venue=hyperliquid/date=YYYY-MM-DD/*.parquet
    funding/venue=hyperliquid/date=YYYY-MM-DD/*.parquet
    liquidity/venue=hyperliquid/date=YYYY-MM-DD/*.parquet
    asset_context/venue=hyperliquid/date=YYYY-MM-DD/*.parquet
  gold/
    panels/timeframe=1m/universe_rule=hl_5m_v1/snapshot_id=.../*.parquet
    panels/timeframe=1h/universe_rule=hl_5m_v1/snapshot_id=.../*.parquet
    features/feature_set=.../snapshot_id=.../*.parquet
    folds/validation_policy=.../snapshot_id=.../*.parquet
  manifests/
    ingestion_runs.parquet
    file_manifest.parquet
    parse_manifest.parquet
    normalization_manifest.parquet
    data_coverage.parquet
    data_quality.parquet
    archive_snapshots.parquet
    universe_snapshots.parquet
    feature_snapshots.parquet
  performance/
    experiment_ledger.parquet
    experiment_ledger.csv
    experiment_ledger.xlsx
  lead_book/
    lead_book.parquet
    lead_book.csv
```

### 8.4 Archive manifest tables

#### `ingestion_runs`

| Column | Type | Required | Notes |
|---|---:|---:|---|
| `ingestion_run_id` | string | yes | Deterministic or UUID job/run ID. |
| `job_id` | string | yes | Durable worker job ID. |
| `adapter_id` | string | yes | Example: `hyperliquid_native_v1`. |
| `venue` | string | yes | `hyperliquid`, `binance`, `okx`, etc. |
| `datatype` | string | yes | `candles`, `trades`, `funding`, `l2book`, etc. |
| `source_endpoint_or_subscription` | string | yes | REST endpoint, WebSocket subscription, S3 path. |
| `symbols` | list/string | yes | Instruments requested. |
| `start_ts` | timestamp | yes | Source window start. |
| `end_ts` | timestamp | yes | Source window end. |
| `ingested_at` | timestamp | yes | UTC. |
| `status` | string | yes | success, partial, failed. |
| `row_count` | int | yes | Raw or parsed row count. |
| `byte_count` | int | yes | Bytes written. |
| `schema_version` | string | yes | Source schema/parser schema. |
| `error_summary` | string | if failed | Truncated summary, full logs linked. |
| `retry_count` | int | yes | Durable job retry count. |
| `gap_status` | string | yes | none, suspected, confirmed, backfilled, unresolved. |

#### `file_manifest`

| Column | Type | Required | Notes |
|---|---:|---:|---|
| `file_id` | string | yes | Content hash or generated ID. |
| `path` | string | yes | Relative archive path. |
| `layer` | string | yes | raw, bronze, silver, gold. |
| `venue` | string | yes | Venue provenance. |
| `datatype` | string | yes | Dataset type. |
| `instrument_id` | string | optional | Null allowed for multi-symbol files. |
| `timeframe` | string | optional | Bars/candles only. |
| `date` | date | optional | Partition date. |
| `hour` | int | optional | Hour partition where used. |
| `sha256` | string | yes | File hash. |
| `size_bytes` | int | yes | File size. |
| `row_count` | int | if tabular | Rows in file. |
| `schema_version` | string | yes | Writer/schema version. |
| `source_file_ids` | list/string | bronze+ | Parent raw/bronze files. |
| `created_at` | timestamp | yes | UTC. |
| `created_by_job_id` | string | yes | Worker job. |

#### `archive_snapshots`

| Column | Type | Required | Notes |
|---|---:|---:|---|
| `archive_snapshot_id` | string | yes | Deterministic content hash over included manifests/files. |
| `created_at` | timestamp | yes | UTC. |
| `layer` | string | yes | silver/gold usually. |
| `venue_scope` | string | yes | hyperliquid, multi_venue, etc. |
| `start_ts` | timestamp | yes | Earliest included data. |
| `end_ts` | timestamp | yes | Latest included data. |
| `file_manifest_hash` | string | yes | Hash of included file manifest subset. |
| `coverage_manifest_hash` | string | yes | Hash of relevant coverage rows. |
| `quality_manifest_hash` | string | yes | Hash of relevant quality rows. |
| `lockbox_policy_id` | string | optional | If snapshot is lockbox-aware. |
| `notes` | string | optional | Human-readable notes. |

### 8.5 Raw writer requirements

Raw writer must:

- write before parsing;
- preserve exact payload bytes or exact JSON serialization of received message;
- include source timestamp when available;
- include ingestion timestamp;
- include subscription/endpoint metadata;
- flush safely on rotation;
- hash every file;
- register every file in `file_manifest`;
- never overwrite existing raw files.

### 8.6 Bronze parser requirements

Bronze parser must:

- reference raw file IDs/hashes;
- preserve source-equivalent semantics;
- avoid filling gaps;
- avoid creating strategy features;
- record parse errors by source row/file;
- allow deterministic rebuild from raw.

### 8.7 Silver normalizer requirements

Silver normalizer must:

- deduplicate deterministically;
- label gaps instead of hiding them;
- align timestamps to UTC clocks;
- normalize symbol IDs through instrument catalog;
- reconcile raw-to-bronze-to-silver counts;
- produce quality and coverage reports;
- record every cleaning rule in `normalization_manifest`.

### 8.8 Gold feature requirements

Gold feature builder must:

- use only approved silver inputs;
- record feature definitions and parameters;
- record universe snapshot ID;
- record archive snapshot ID;
- exclude lockbox data in ordinary research mode;
- produce deterministic `feature_snapshot_id`;
- never be hand-edited.

---

## 9. Universe manager implementation contract

### 9.1 Universe rule

```python
eligible = (
    instrument.venue == "hyperliquid"
    and instrument.market_type == "perp"
    and asset_context.day_ntl_vlm_usd >= 5_000_000
    and instrument.status not in {"disabled", "delisted", "quarantine"}
    and coverage_ratio >= 0.98   # for accepted evidence, not necessarily for raw archiving
    and usable_months >= 6       # for accepted evidence, not necessarily for raw archiving
)
```

### 9.2 Instrument catalog schema

| Column | Type | Required | Notes |
|---|---:|---:|---|
| `instrument_id` | string | yes | Stable internal ID: `hyperliquid:perp:BTC`, `hyperliquid:hip3:<dex>:<symbol>`. |
| `venue` | string | yes | Primary venue. |
| `venue_symbol` | string | yes | Exact venue symbol. |
| `canonical_symbol` | string | yes | Normalized symbol used by strategy specs. |
| `market_type` | string | yes | perp, spot, future. |
| `base_asset` | string | yes | BTC, ETH, SOL, etc. |
| `quote_asset` | string | yes | USD/USDC/USDT depending venue. |
| `settle_asset` | string | optional | USDC/USDT etc. |
| `first_seen_ts` | timestamp | yes | First observed in archive. |
| `last_seen_ts` | timestamp | yes | Last observed in catalog refresh. |
| `status` | string | yes | active, delisted, disabled, quarantine. |
| `sz_decimals` | int | optional | Hyperliquid size precision. |
| `max_leverage` | decimal | optional | Venue value. |
| `only_isolated` | bool | optional | Hyperliquid field. |
| `is_hip3_or_rwa` | bool | yes | Special metadata flag. |
| `dex_namespace` | string | if HIP3 | HIP-3 namespace. |
| `reference_market` | string | if RWA | Reference market. |
| `oracle_source` | string | if RWA/HIP3 | Oracle/reference source. |
| `source_snapshot_id` | string | yes | Raw source provenance. |

### 9.3 Universe snapshot schema

| Column | Type | Required | Notes |
|---|---:|---:|---|
| `snapshot_id` | string | yes | Content hash or UUID. |
| `asof_date` | date | yes | UTC date. |
| `venue` | string | yes | Hyperliquid first. |
| `universe_rule_id` | string | yes | `hl_perps_day_ntl_vlm_gte_5m_v1`. |
| `instrument_id` | string | yes | Internal stable ID. |
| `day_ntl_vlm_usd` | decimal | yes | From asset context. |
| `open_interest` | decimal | optional | From asset context. |
| `mark_px` | decimal | optional | From asset context. |
| `oracle_px` | decimal | optional | From asset context. |
| `funding` | decimal | optional | Current/estimated funding. |
| `eligible_volume` | bool | yes | `dayNtlVlm >= 5M`. |
| `eligible_coverage` | bool | yes for evidence | Coverage gate status. |
| `eligible` | bool | yes | Final inclusion for rule. |
| `exclusion_reason` | string | if excluded | volume_below_threshold, insufficient_coverage, missing_context, missing_hip3_metadata, etc. |
| `raw_payload_sha256` | string | yes | Source payload hash. |
| `created_at` | timestamp | yes | UTC. |

### 9.4 Universe commands

```bash
redx universe refresh \
  --venue hyperliquid \
  --min-day-notional-usd 5000000 \
  --include-hip3-dexs \
  --write-raw \
  --write-snapshot

redx universe list \
  --snapshot latest \
  --eligible-only

redx universe explain \
  --snapshot latest \
  --instrument hyperliquid:perp:SOL

redx universe diff \
  --left 2026-06-01 \
  --right 2026-06-20 \
  --rule hl_perps_day_ntl_vlm_gte_5m_v1
```

### 9.5 Universe acceptance tests

Create tests:

- `test_hyperliquid_universe_includes_non_btc_eth_above_5m`
- `test_hyperliquid_universe_excludes_below_5m_day_ntl_volume`
- `test_hyperliquid_universe_archives_excluded_instruments`
- `test_hyperliquid_universe_handles_hip3_prefixed_symbols`
- `test_asof_universe_does_not_use_future_volume_snapshot`
- `test_current_universe_mode_is_sandbox_only`
- `test_missing_hip3_reference_metadata_blocks_evidence`

---

## 10. Venue adapters and collectors

### 10.1 Venue adapter protocol

```python
from typing import AsyncIterator, Protocol
from datetime import datetime

class VenueAdapter(Protocol):
    venue: str
    adapter_id: str

    def capabilities(self) -> "VenueCapabilities": ...
    async def discover_markets(self) -> list["MarketDefinition"]: ...
    async def fetch_asset_contexts(self, *, asof: datetime | None = None) -> list["AssetContext"]: ...
    async def fetch_candles(self, symbol: str, timeframe: str, start: datetime, end: datetime) -> list["Candle"]: ...
    async def fetch_funding(self, symbol: str, start: datetime, end: datetime) -> list["FundingRate"]: ...
    async def stream_trades(self, symbols: list[str]) -> AsyncIterator["Trade"]: ...
    async def stream_candles(self, symbols: list[str], timeframe: str) -> AsyncIterator["Candle"]: ...
    async def stream_l2(self, symbols: list[str]) -> AsyncIterator["OrderBookSnapshot"]: ...
    async def stream_bbo(self, symbols: list[str]) -> AsyncIterator["BBO"]: ...
```

### 10.2 Hyperliquid native adapter scope

The Hyperliquid adapter must support:

- `metaAndAssetCtxs` or equivalent metadata/context request;
- `perpDexs` or equivalent HIP-3/RWA namespace discovery where applicable;
- candle snapshot bootstrap with 5,000-candle cap awareness;
- funding history;
- WebSocket streams for candles, trades, L2 book, BBO, all mids, active asset contexts/all dex asset contexts where relevant;
- official S3 archive loader where available;
- raw payload capture before normalization;
- reconnect/backoff handling;
- gap records.

### 10.3 Collection posture

The CEO selected aggressive collection. Target state collects all relevant available data:

| Data type | Required | Priority | Notes |
|---|---:|---:|---|
| Instrument metadata | yes | P0 | Universe construction and precision. |
| Asset contexts | yes | P0 | `dayNtlVlm`, funding, OI, mark/oracle, eligibility. |
| 1m candles | yes | P0 | Baseline backtesting. |
| 5m/15m/1h bars | yes | P0/P1 | Derived from 1m where possible; efficient research. |
| Trades | yes | P1 | Slippage, volume validation, microstructure. |
| Funding history | yes | P0 | Net perp returns. |
| L2 book snapshots | yes | P1 | Liquidity, slippage, event-driven simulation. |
| BBO | yes | P1 | Spread and fill-cost estimation. |
| Official S3 archive | yes where available | P1 | Backfill and redundancy. |
| Cross-venue candles/funding/OI | yes where useful | P2 | Proxy/comparison/robustness. |
| RWA reference-market data | yes where relevant | P2 | Required context for non-crypto instruments. |
| Event calendars | later but important | P3 | Macro/RWA/event-sensitive strategies. |

Aggressive collection does not mean unmanifested collection. Build archive contracts and writers before running large collection jobs.

### 10.4 Collector jobs

| Job | Cadence | Data | Required behavior |
|---|---:|---|---|
| `universe_refresh` | daily | metadata + asset contexts | write raw first, update catalog/snapshot, no overwrite |
| `recent_candle_bootstrap` | hourly/daily | recent candles | record 5,000-candle cap and unresolved historical gaps |
| `websocket_candle_capture` | continuous | 1m candles and configured intervals | reconnect, rotate raw files, gap records |
| `websocket_trade_capture` | continuous | trades | dedupe, preserve raw, volume checks |
| `websocket_l2_bbo_capture` | continuous/configurable | L2/BBO | storage controls, sampled/configurable depth if needed |
| `funding_backfill` | daily | funding history | reconcile with funding fields in context |
| `official_s3_backfill` | monthly/manual | L2/context official files | preserve native compressed files if possible |
| `bronze_parse` | after ingestion | parsed tables | source-equivalent only |
| `silver_normalize` | scheduled | cleaned market data | coverage/quality reports |
| `coverage_audit` | daily | coverage manifest | fail/alert on data holes |

### 10.5 Job record schema

| Column | Type | Required | Notes |
|---|---:|---:|---|
| `job_id` | string | yes | Durable ID. |
| `job_type` | string | yes | universe_refresh, websocket_capture, etc. |
| `status` | string | yes | queued, running, succeeded, failed, cancelled, retrying. |
| `priority` | int | yes | Scheduling priority. |
| `inputs_json` | json | yes | Fully declared inputs. |
| `output_artifacts_json` | json | optional | Written outputs. |
| `created_at` | timestamp | yes | UTC. |
| `started_at` | timestamp | optional | UTC. |
| `ended_at` | timestamp | optional | UTC. |
| `heartbeat_at` | timestamp | if running | Worker heartbeat. |
| `retry_count` | int | yes | Retry count. |
| `max_retries` | int | yes | Policy. |
| `failure_reason` | string | if failed | Human-readable. |
| `audit_id` | string | yes | Chunk marker. |
| `archive_snapshot_id` | string | optional | For jobs producing snapshots. |
| `ledger_run_id` | string | optional | For backtest jobs. |

### 10.6 Collector acceptance tests

Create tests:

- `test_collector_writes_raw_before_bronze`
- `test_websocket_reconnect_records_gap_instead_of_silent_success`
- `test_candle_bootstrap_records_api_cap_warning`
- `test_funding_backfill_reconciles_duplicate_rows`
- `test_s3_loader_preserves_source_hash`
- `test_collector_job_state_survives_process_restart`
- `test_long_collector_not_run_inside_asgi_loop`

---

## 11. Data quality and coverage service

### 11.1 Required checks

Every archive snapshot must report:

- missing candle ratio by instrument/timeframe/day;
- duplicate timestamps;
- conflicting OHLCV rows;
- stale mark/oracle/funding records;
- abnormal zero-volume periods;
- time monotonicity violations;
- raw-to-bronze row count reconciliation;
- bronze-to-silver row count reconciliation;
- outlier returns;
- outlier spreads;
- outlier funding;
- listing/delisting status;
- coverage months by instrument;
- whether instrument qualifies for 6-month or 12-month testing;
- whether HIP-3/RWA metadata is complete.

### 11.2 Coverage schema

| Column | Type | Required | Notes |
|---|---:|---:|---|
| `coverage_id` | string | yes | Deterministic key. |
| `archive_snapshot_id` | string | yes | Data snapshot. |
| `instrument_id` | string | yes | Instrument. |
| `venue` | string | yes | Venue. |
| `datatype` | string | yes | bars, trades, funding, l2book, bbo. |
| `timeframe` | string | optional | Bars only. |
| `start_ts` | timestamp | yes | Window start. |
| `end_ts` | timestamp | yes | Window end. |
| `expected_rows` | int | yes | Expected rows. |
| `observed_rows` | int | yes | Observed rows. |
| `coverage_ratio` | float | yes | Observed/expected. |
| `missing_intervals_count` | int | yes | Gaps. |
| `duplicate_count` | int | yes | Duplicates. |
| `stale_count` | int | yes | Stale rows. |
| `quality_status` | string | yes | pass, warning, fail. |
| `evidence_eligible` | bool | yes | Whether coverage supports evidence. |
| `notes` | string | optional | Diagnostic notes. |

### 11.3 Coverage enforcement

Default accepted evidence requires:

```yaml
coverage_enforcement:
  min_coverage_ratio: 0.98
  failed_if_below_min: true
  sandbox_diagnostic_exception_allowed: true
  exception_requires_label: diagnostic_only
  exception_candidate_evidence: false
```

### 11.4 Data quality commands

```bash
redx data coverage \
  --universe latest \
  --timeframe 1m \
  --since 2024-01-01

redx data quality report \
  --archive-snapshot latest \
  --venue hyperliquid \
  --timeframe 1m

redx data gaps explain \
  --instrument hyperliquid:perp:SOL \
  --timeframe 1m \
  --start 2024-01-01 \
  --end auto_non_lockbox_end
```

---

## 12. Backtest data service implementation contract

### 12.1 Service role

The backtest data service is the enforcement point for:

- earliest reported start date;
- minimum usable months;
- dynamic lockbox;
- coverage threshold;
- universe mode;
- as-of universe validity;
- data snapshot identity;
- field declaration;
- no direct venue/API reads.

Backtest engines must call this service. Engines must not directly read archive files.

### 12.2 Public API shape

```python
panel = data_service.load_panel(
    universe_snapshot_id="...",
    instruments="eligible",
    timeframe="1m",
    start="2024-06-01",
    end="2025-05-31",
    fields=["open", "high", "low", "close", "volume", "funding", "open_interest"],
    exclude_lockbox=True,
    min_coverage=0.98,
    mode="reported_research",
)
```

### 12.3 Required policies

```yaml
backtest_data_policies:
  earliest_reported_backtest_start: "2024-01-01"
  minimum_usable_months: 6
  preferred_usable_months: 12
  coverage_minimum: 0.98
  require_archive_snapshot_id: true
  require_universe_snapshot_id: true
  require_universe_mode: true
  as_of_universe_required_for_evidence: true
  current_universe_allowed_only_as_sandbox: true
  warmup_allowed: true
  warmup_contributes_to_metrics: false
  ordinary_backtests_can_access_lockbox: false
```

### 12.4 Dynamic lockbox policy

Use full calendar months. Default is two full months; minimum is one full month only when documented by validation policy.

```yaml
lockbox_policy:
  id: dynamic_full_month_lockbox_v1
  default_months: 2
  minimum_months: 1
  maximum_months: 2
  align_to_full_calendar_months: true
  ordinary_backtests_can_access: false
  optimization_can_access: false
  leaderboard_can_access: false
  final_test_can_access: true_only_after_strategy_freeze
  dynamic_reduction_allowed_when:
    - instrument_history_is_short
    - coverage_would_otherwise_prevent_any_valid_6_month_non_lockbox_window
    - explicit_validation_manifest_records_reason
  dynamic_reduction_never_allowed_for:
    - ordinary_leaderboard_optimization
    - repeated_agent_sweeps
    - post_result_parameter_tuning
```

For a current date of 2026-06-20:

```text
2-month lockbox:
  lockbox_start = 2026-05-01 00:00:00 UTC
  ordinary_backtest_end <= 2026-04-30 23:59:59 UTC

1-month lockbox:
  lockbox_start = 2026-06-01 00:00:00 UTC
  ordinary_backtest_end <= 2026-05-31 23:59:59 UTC
```

### 12.5 Backtest data service tests

Create tests:

- `test_reported_backtest_rejects_start_before_2024`
- `test_reported_backtest_rejects_less_than_6_months`
- `test_backtest_rejects_lockbox_overlap`
- `test_backtest_loads_only_declared_fields`
- `test_backtest_uses_asof_universe_snapshot`
- `test_current_universe_claim_fails_evidence_mode`
- `test_warmup_bars_do_not_enter_reported_pnl`
- `test_coverage_below_098_fails_reported_mode`
- `test_engine_cannot_bypass_data_service_with_direct_path`

---

## 13. Strategy interface implementation contract

### 13.1 Declarative specs first

Declarative strategy specs are the first supported strategy interface. They must allow agents to express indicators, thresholds, ranks, filters, entries, exits, risk constraints, rebalance cadence, data requirements, and cost assumptions without arbitrary code execution.

### 13.2 Example declarative spec

```yaml
schema_version: strategy_spec_v1
strategy_id: hl_cross_sectional_momentum_v1
version: 0.1.0
owner: agent
research_only: true
market_scope:
  venue: hyperliquid
  market_type: perp
  universe_rule: hl_perps_day_ntl_vlm_gte_5m_v1
inputs:
  timeframe: 1h
  fields:
    - close
    - volume
    - funding
    - open_interest
logic:
  signal_type: cross_sectional_rank
  lookback_hours: 168
  rank_metric: return
  long_top_quantile: 0.10
  short_bottom_quantile: 0.10
  filters:
    min_coverage: 0.98
    max_funding_abs: 0.001
risk:
  max_gross_leverage: 1.0
  max_instrument_weight: 0.05
  rebalance: 1h
execution:
  price_basis: next_bar_open
  fee_model: conservative_hyperliquid_taker_v1
  slippage_model: volume_participation_v1
validation:
  min_backtest_months: 12
  earliest_start: 2024-01-01
  exclude_lockbox: true
  universe_mode: as_of
```

### 13.3 Declarative spec validator must reject

Reject specs that:

- omit schema version;
- omit research-only flag;
- reference live/paper/order/sizing behavior;
- reference arbitrary Python;
- request lockbox access;
- request current universe in evidence mode;
- omit cost model;
- omit data fields;
- use unsupported indicators or expressions;
- request unknown files or URLs;
- include hidden side effects.

### 13.4 Python plugins later

Python plugins are allowed later only through a narrow protocol:

```python
class Strategy(Protocol):
    strategy_id: str
    version: str

    def required_inputs(self) -> StrategyInputs: ...
    def default_params(self) -> dict[str, Any]: ...
    def generate_signals(
        self,
        data: MarketPanel,
        params: dict[str, Any],
        ctx: StrategyContext,
    ) -> SignalFrame: ...
```

Restrictions:

- no network;
- no secrets;
- no order paths;
- no runtime config writes;
- no arbitrary file reads;
- declared inputs only;
- full strategy hash;
- full params hash;
- deterministic outputs;
- manifest capture.

### 13.5 Strategy tests

Create tests:

- `test_declarative_strategy_validates_schema`
- `test_strategy_spec_rejects_live_or_order_language`
- `test_strategy_spec_rejects_unknown_data_fields`
- `test_strategy_spec_requires_cost_model`
- `test_strategy_cannot_access_network_or_credentials`
- `test_strategy_plugin_protocol_blocks_arbitrary_file_reads`
- `test_strategy_hash_changes_when_spec_changes`

---

## 14. Backtest engine implementation contract

### 14.1 Engine lanes

Both lanes are first-class:

| Engine | Role | Initial priority |
|---|---|---:|
| Vectorized engine | broad multi-instrument sweeps, declarative specs, OHLCV/funding/OI strategies, fast walk-forward | P0 |
| Event-driven engine | trade/L2/BBO strategies, fill-sensitive logic, impact modeling, order-flow/liquidity research, RWA session discontinuities | P1 skeleton, P2 expansion |

Design shared contracts from the beginning so event-driven requirements do not get bolted on incorrectly later.

### 14.2 Simulation requirements

| Layer | Required behavior |
|---|---|
| Price basis | Explicitly choose close, next-open, VWAP, mark, oracle, or event-driven fill basis. |
| Fees | Maker/taker and conservative defaults. |
| Funding | Apply perp funding to open positions. |
| Spread | Include spread cost or spread-derived slippage. |
| Slippage | At least volume-participation; L2-aware when data exists. |
| Impact | Market impact model for larger participation. |
| Liquidity | Participation caps; reject trades if volume/spread/OI insufficient. |
| Position model | Long/short/flat, max notional, max concentration, leverage constraints. |
| Missing data | Explicit policy; no silent forward-fill of PnL-critical prices. |
| Multi-instrument alignment | Common clock, listing dates, deterministic missing-bar handling. |
| Metrics | Gross and net separately; net is used for ranking. |

### 14.3 Required run artifacts

Every run must produce:

```text
runs/<run_id>/
  run_manifest.json
  strategy_spec.yaml or strategy_plugin_manifest.json
  params.json
  data_manifest.json
  validation_manifest.json
  cost_manifest.json
  metrics.json
  equity_curve.parquet
  daily_returns.parquet
  trades.parquet
  positions.parquet
  per_instrument_metrics.parquet
  fold_metrics.parquet
  logs/log.txt
```

### 14.4 Run manifest required fields

```yaml
run_manifest:
  schema_version: run_manifest_v1
  run_id: required
  experiment_id: required
  trial_index: required
  agent_or_user: required
  created_at: required
  research_only: true
  observe_only: true
  live_signal: false
  paper_signal: false
  sizing_instruction: false
  order_placement_instruction: false
  git_sha: required
  environment_hash: required
  strategy_id: required
  strategy_version: required
  strategy_hash: required
  params_hash: required
  strategy_lane: declarative_or_plugin
  archive_snapshot_id: required
  universe_snapshot_id: required
  feature_snapshot_id: optional
  universe_mode: required
  venue_scope: required
  instrument_count: required
  timeframe: required
  backtest_start: required
  backtest_end: required
  usable_months: required
  lockbox_policy_id: required
  lockbox_start: required
  lockbox_end: required
  data_coverage_min: required
  cost_model_id: required
  validation_status: pass_fail_quarantine
  failure_reason: optional
  artifacts:
    metrics: required
    equity_curve: required
    daily_returns: required
    trades: required
    positions: required
```

### 14.5 Engine tests

Create tests:

- `test_same_run_manifest_reproduces_metrics_on_fixture_data`
- `test_funding_and_fees_affect_net_results`
- `test_missing_data_policy_is_explicit`
- `test_vectorized_engine_outputs_required_artifacts`
- `test_event_driven_engine_skeleton_outputs_same_artifact_contract`
- `test_engine_records_failed_trial_artifacts`
- `test_engine_rejects_gross_only_metrics_for_reported_mode`

---

## 15. Cost, funding, slippage, impact, and capacity model

### 15.1 Cost doctrine

No result can be promoted even within research context without gross/net metrics and cost sensitivity. Gross-only ranking is forbidden.

### 15.2 Required cost dimensions

Every reported result must include:

- fees;
- funding;
- spread;
- slippage;
- market impact;
- liquidity participation cap;
- fill basis;
- turnover;
- gross return;
- net return;
- stress matrix.

### 15.3 Cost model IDs

```yaml
cost_models:
  conservative_hyperliquid_taker_v1:
    fee_side: taker
    spread_assumption: conservative
    slippage_model: volume_participation
    funding: applied
    impact: enabled
    ranking_allowed: true

  mixed_maker_taker_research_v1:
    allowed_only_with: event_driven_or_l2_data
    maker_assumption_requires_queue_model: true
    no_free_maker_fill: true
    ranking_allowed: only_if_queue_model_documented

  stress_2x_cost_v1:
    multiplier: 2.0
    purpose: robustness

  stress_3x_cost_v1:
    multiplier: 3.0
    purpose: severe_robustness
```

### 15.4 Cost manifest

```yaml
cost_manifest:
  schema_version: cost_manifest_v1
  cost_model_id: conservative_hyperliquid_taker_v1
  fee_model:
    side: taker
    rate_source: config_or_manifested_source
    rate_value: required
  funding_model:
    applied: true
    source: archive_funding_table
    missing_policy: fail_or_explicit
  slippage_model:
    id: volume_participation_v1
    participation_cap: required
    spread_component: required
    volume_component: required
  impact_model:
    enabled: true
    model_id: impact_v1
  stress_matrix:
    base: required
    stress_2x: required
    stress_3x: required
  cost_sensitivity:
    base_cost_net_return: required
    stress_2x_net_return: required
    stress_3x_net_return: required
    cost_fragile_warning: required
    cost_dependent_failure: required
```

### 15.5 Cost acceptance tests

Create tests:

- `test_cost_model_applies_fees_to_turnover`
- `test_funding_pnl_changes_net_return`
- `test_spread_slippage_reduces_net_return`
- `test_stress_2x_and_3x_costs_are_reported`
- `test_maker_assumption_requires_queue_model`
- `test_gross_only_result_cannot_enter_leaderboard`
- `test_liquidity_participation_cap_rejects_oversized_trade`

---

## 16. Experiment ledger implementation contract

### 16.1 Ledger doctrine

The ledger is the canonical append-only experiment record. It is not a spreadsheet. Spreadsheet files are generated views.

```yaml
ledger:
  canonical: data/archive/performance/experiment_ledger.parquet
  csv_export: data/archive/performance/experiment_ledger.csv
  xlsx_export: data/archive/performance/experiment_ledger.xlsx
  append_only: true
  manual_spreadsheet_editing_allowed: false
  failed_trials_required: true
  require_validation_status: true
  require_artifact_hash: true
```

### 16.2 Required ledger columns

| Group | Columns |
|---|---|
| Identity | `run_id`, `experiment_id`, `trial_index`, `agent_or_user`, `created_at`, `git_sha`, `environment_hash` |
| Strategy | `strategy_id`, `strategy_version`, `strategy_hash`, `params_hash`, `strategy_lane` |
| Data | `archive_snapshot_id`, `universe_snapshot_id`, `feature_snapshot_id`, `universe_mode`, `venue_scope`, `instrument_count`, `timeframe`, `backtest_start`, `backtest_end`, `usable_months`, `lockbox_policy_id`, `lockbox_start`, `lockbox_end`, `data_coverage_min` |
| Performance | `gross_return`, `net_return`, `roi_observed`, `annualized_return`, `annualized_vol`, `sharpe`, `sortino`, `max_drawdown`, `calmar`, `turnover`, `avg_daily_trades`, `fee_paid`, `funding_pnl`, `slippage_cost`, `impact_cost` |
| Validation | `walk_forward_pass`, `pbo_score`, `validation_status`, `failure_reason`, `diminishing_returns_warning`, `profit_concentration_warning`, `minimum_trade_frequency_pass`, `monthly_stability_pass`, `cost_fragile_warning`, `survivorship_bias_status` |
| Artifacts | `artifact_path`, `artifact_sha256`, `validation_manifest_path`, `metrics_path`, `notes` |
| Boundary | `research_only`, `live_signal`, `paper_signal`, `sizing_instruction`, `order_placement_instruction` |

### 16.3 Ledger append command

```bash
redx ledger append \
  --run runs/<run_id>/run_manifest.json \
  --ledger data/archive/performance/experiment_ledger.parquet

redx ledger export \
  --format xlsx \
  --output data/archive/performance/experiment_ledger.xlsx

redx ledger leaderboard \
  --require-validation-pass \
  --exclude-sandbox \
  --rank composite_v1
```

### 16.4 Ledger append validation

The append validator must reject rows when:

- run manifest missing;
- metrics missing;
- validation status missing;
- run overlaps lockbox in ordinary mode;
- start before 2024 in reported mode;
- usable months below 6 in accepted mode;
- archive/universe snapshot IDs missing;
- universe mode is current but evidence claim is attempted;
- gross-only metrics are present without net costs;
- duplicate `run_id` already exists;
- strategy hash or params hash missing;
- artifact hash missing;
- research-only invariant is missing or false.

### 16.5 Ranking doctrine

Do not rank by Sharpe alone. Ranking should consider:

- validation pass/fail first;
- net ROI and net return;
- max drawdown;
- Calmar, Sharpe, Sortino;
- monthly stability;
- unseen-period performance;
- trade frequency;
- profit concentration;
- diminishing returns;
- cost stress;
- fold stability;
- number of trials in the family;
- PBO/CSCV or similar overfit diagnostics;
- data coverage quality;
- capacity/liquidity constraints.

### 16.6 Ledger tests

Create tests:

- `test_ledger_append_rejects_missing_run_manifest`
- `test_ledger_append_rejects_missing_validation_status`
- `test_ledger_records_failed_trials`
- `test_ledger_rejects_duplicate_run_id`
- `test_xlsx_export_is_generated_from_canonical_ledger`
- `test_manual_spreadsheet_edit_is_not_canonical`
- `test_leaderboard_excludes_sandbox_current_universe_claims`
- `test_leaderboard_ranks_net_not_gross`

---

## 17. Lead Book implementation contract

### 17.1 Lead doctrine

The Lead Book is the official queue of non-promotable strategy ideas worth investigating. A lead is not a candidate. A lead is a hypothesis with enough evidence structure to deserve further validation.

Agents may create Lead Book rows. Agents may approve a lead for deep validation only after manual human inspection is completed and recorded.

### 17.2 Lead source types

Allowed sources:

- legacy run;
- sandbox run;
- strict-cycle rejected row;
- external research paper/report;
- manual hypothesis;
- old high-return strategy output;
- negative/failure-mode row worth studying;
- cross-venue observation;
- data anomaly investigation;
- microstructure hypothesis;
- HIP-3/RWA reference-market behavior.

External research creates hypotheses only. External claims are not evidence until reproduced under v2 archive and validation rules.

### 17.3 Lead schema

```yaml
lead_book_row:
  lead_id: required
  lead_version: required
  created_at: required
  created_by_type: agent_or_human
  created_by_id: required
  source_type: legacy_run_or_sandbox_run_or_external_source_or_other
  source_artifact_path: required
  source_artifact_sha256: required
  strategy_family: required
  economic_thesis: required
  venue_scope: required
  universe_scope: required
  instrument_scope: required
  hip3_or_rwa_flag: required
  data_window_start: required
  data_window_end: required
  data_source: required
  archive_snapshot_id: optional_but_required_after_v2_retest
  universe_snapshot_id: optional_but_required_after_v2_retest
  feature_snapshot_id: optional
  cost_assumptions: required
  funding_assumptions: required
  slippage_assumptions: required
  fill_assumptions: required
  headline_metrics: required
  roi_observed: required
  roi_projected: required
  roi_projection_assumptions: required
  roi_projection_confidence: low_medium_high_unknown
  roi_projection_is_not_claim: true
  why_interesting: required
  known_blockers: required
  missing_evidence: required
  required_next_validation: required
  trade_count_summary: required
  monthly_stability_summary: required
  pnl_concentration_summary: required
  diminishing_returns_warning: required
  human_inspection_status: not_requested_or_requested_or_completed_or_rejected
  human_inspected_by: optional
  human_inspected_at: optional
  human_inspection_notes: optional
  agent_approval_status: not_reviewed_or_approved_after_human_inspection_or_rejected_or_needs_more_info
  approving_agent_id: optional
  approved_at: optional
  current_state: idea_only_or_sandbox_screened_or_deep_validation_requested_or_deep_validation_approved_or_deep_validation_running_or_deep_validation_rejected_or_final_test_candidate_or_final_test_rejected_or_final_test_survivor
  non_promotable_flags: required
  notes: optional
```

### 17.4 Lead states

```text
idea_only
  -> sandbox_screened
  -> human_inspection_requested
  -> human_inspection_completed
  -> agent_approved_after_human_inspection
  -> deep_validation_requested
  -> deep_validation_running
  -> deep_validation_rejected OR final_test_candidate
  -> final_test_rejected OR final_test_survivor
```

No lead state may imply paper/live/trade readiness.

### 17.5 Lead promotion gates

```yaml
lead_promotion_gates:
  minimum_avg_trades_per_month: 5
  minimum_usable_months: 6
  preferred_usable_months: 12
  maximum_losing_months_in_12_month_window: 5
  six_losing_months_in_year: fail
  profit_concentration:
    top_2_trades_profit_share_warning: 0.35
    top_2_trades_profit_share_fail: 0.50
    best_month_profit_share_warning: 0.35
    best_month_profit_share_fail: 0.50
  unseen_modern_months_required: true
  modern_unseen_failure_policy:
    allow_pre_2024_fallback_once: true
    fallback_window_months: 6
    fallback_label: diagnostic_fallback_only
    fallback_absent_result: failed_lead
  diminishing_returns:
    compute: true
    flag_if_later_window_underperforms_early_window_materially: true
    status: warning_not_blocker
```

### 17.6 Lead commands

```bash
redx lead create \
  --source-artifact path/to/artifact \
  --source-type legacy_run \
  --strategy-family momentum \
  --economic-thesis "cross-sectional continuation after liquidity filter" \
  --non-promotable

redx lead inspect-request \
  --lead-id LEAD-...

redx lead approve-after-human-inspection \
  --lead-id LEAD-... \
  --inspection-note-file docs/lead_inspections/LEAD-....md

redx lead list \
  --state deep_validation_requested
```

### 17.7 Lead Book tests

Create tests:

- `test_agent_can_create_lead_with_source_hash`
- `test_lead_cannot_deep_validate_without_human_inspection_completed`
- `test_agent_approval_requires_human_inspection`
- `test_lead_schema_requires_roi_observed_and_projected`
- `test_roi_projection_marked_not_claim`
- `test_six_losing_months_fails_lead_gate`
- `test_profit_concentration_warning_and_fail_thresholds`
- `test_minimum_five_trades_per_month_gate`
- `test_diminishing_returns_warning_is_recorded`
- `test_pre_2024_fallback_absent_marks_failed_lead`

---

## 18. Deep validation and final hard-test workflow

### 18.1 Deep validation doctrine

Deep validation runs one serious lead at a time. Broad sweeps are triage only. Deep validation must be expensive, slow, and evidence-focused.

### 18.2 Deep validation checklist

Each deep validation must include:

- full valid 2024+ history where available;
- 6-month minimum and 12-month preference;
- dynamic lockbox exclusion;
- as-of universe snapshots;
- walk-forward validation;
- purged/embargoed splits where labels overlap;
- cost-stress matrix;
- fee/funding/slippage/liquidity sensitivity;
- monthly stability;
- loss-streak and drawdown analysis;
- PnL concentration checks;
- minimum trades/month;
- unseen-month performance;
- negative controls;
- side controls;
- no-trade baseline;
- simple comparator baseline;
- feature ablations;
- filter ablations;
- exit-lab and fixed-hold comparison;
- parameter-neighborhood stability;
- regime robustness;
- venue/symbol robustness where relevant;
- diminishing-returns warning;
- failure-mode report.

### 18.3 Pre-2024 fallback policy

Pre-2024 fallback is diagnostic only. It cannot replace mandatory 2024+ evidence.

```yaml
pre_2024_fallback:
  allowed_for: failed_modern_unseen_lead_diagnostic
  not_allowed_for: accepted_reported_strategy_result
  months: 6
  required_label: diagnostic_fallback_only
  if_unavailable: failed_lead
  if_passes: may_return_to_research_queue_with_warning
  if_fails: deep_validation_rejected
```

### 18.4 Final hard-test top 3

Only top 3 surviving leads may enter final hard-test review.

```yaml
final_hard_test:
  max_slots: 3
  requires_frozen_strategy_spec: true
  requires_frozen_params: true
  requires_frozen_data_snapshot: true
  requires_frozen_cost_model: true
  requires_frozen_universe_snapshot: true
  lockbox_access_allowed: only_in_final_phase
  parameter_edits_after_lockbox: forbidden
  final_result_to_leaderboard: separate_section_only
  paper_live_implication: false
```

### 18.5 Final hard-test tests

Create tests:

- `test_deep_validation_only_one_active_serious_lead`
- `test_final_hard_test_rejects_more_than_three_slots`
- `test_final_hard_test_requires_frozen_strategy_and_params`
- `test_final_lockbox_access_requires_final_phase_manifest`
- `test_parameter_edits_after_lockbox_access_are_forbidden`
- `test_final_survivor_report_contains_non_live_disclaimer`

---

## 19. Validation and overfitting prevention

### 19.1 Hard date rules

Enforce in code:

1. No reported strategy backtest may start before `2024-01-01`.
2. No accepted backtest may use less than 6 months of usable data.
3. Default accepted research window should be 12 months where coverage exists.
4. Most recent 1–2 full months are lockbox data.
5. Warmup bars may initialize indicators but do not contribute to reported PnL or metrics.

### 19.2 Walk-forward validation

Minimum pattern:

```text
For each strategy:
  split non-lockbox 2024+ history into sequential folds
  train/tune only on earlier fold(s)
  validate on next fold
  roll forward
  record fold-level metrics
  require stability across folds
```

Use gap/embargo around fold boundaries when features or labels use future horizons or rolling windows.

### 19.3 Overfit diagnostics

For sweeps and strategy families:

- log every trial;
- record parameter grid/search space before running;
- group related trials by `experiment_id`;
- show best-vs-median results;
- show number of trials;
- warn if best result comes from a large weak family;
- compute PBO/CSCV-style diagnostic when enough trials/folds exist;
- penalize performance concentrated in one instrument or short period;
- block leaderboard claims when trial logging is incomplete.

### 19.4 Disqualification rules

A run fails validation if any are true:

- backtest start before 2024-01-01 in reported mode;
- usable months < 6 in accepted mode;
- overlaps lockbox period;
- missing archive snapshot ID;
- missing universe snapshot ID;
- coverage below threshold;
- current universe used for historical evidence claim;
- metrics are gross-only;
- strategy/params not hashed;
- run not appended to ledger;
- external files/network/secrets used undeclared;
- research-only invariant missing or false;
- live/paper/order/sizing implication found.

### 19.5 Validation tests

Create tests:

- `test_experiment_sweep_records_all_trials`
- `test_walk_forward_folds_are_time_ordered`
- `test_embargo_gap_excludes_boundary_rows`
- `test_leaderboard_warns_when_best_result_is_from_many_trials`
- `test_validation_rejects_missing_experiment_id_for_sweep`
- `test_validation_rejects_post_lockbox_parameter_tuning`
- `test_pbo_diagnostic_runs_for_large_strategy_family`

---

## 20. Legacy migration and classification

### 20.1 Legacy doctrine

Legacy code is not blindly deleted and not blindly trusted. It must be inspected.

Flow:

```text
read subsystem
  -> identify purpose
  -> identify risks
  -> identify bugs or wrongdoings
  -> decide if useful for v2
  -> if useful, fix/improve and wrap/migrate into v2
  -> if obsolete, freeze/drawer or move to legacy
  -> if dangerous/live-adjacent, no-touch unless explicitly scoped
```

### 20.2 Classification labels

```yaml
legacy_classification_labels:
  reuse_as_is: safe and useful with no material change
  reuse_after_fix: useful but needs bug/security/contract fix
  wrap_into_v2: useful behavior behind new v2 interface
  migrate_into_v2: move responsibility into v2 bounded context
  freeze_drawer: keep but remove from default path
  move_to_legacy_area: explicitly mark as legacy
  no_touch_without_scope: live/runtime/evidence-sensitive
  remove_later: delete only after replacement and audit
```

### 20.3 Default classification tendencies

| Legacy surface | Classification tendency | Notes |
|---|---|---|
| Strict research cycle | inspect -> reuse/wrap | Truth layer; do not rewrite casually. |
| Candidate-pack gates | inspect -> reuse/harden | Keep guardrails, ensure no live implication. |
| Rapid research sandbox | inspect -> integrate as v2 agent lab/triage | Non-promotable by default. |
| Old high-return outputs | freeze as evidence -> Lead Book | Clues, not candidates. |
| Old rejected rows | preserve -> negative controls or leads | Useful failure evidence. |
| Strategy plugins | inspect -> wrap/migrate useful ones | Must conform to v2 protocol. |
| Feature builders | inspect -> wrap/migrate | Preserve point-in-time semantics. |
| Backtest engines | inspect -> adapter or replace gradually | Need vectorized and event-driven support. |
| Legacy GUI | freeze/drawer | Do not let it drive v2. |
| Live/runtime-adjacent code | no-touch without scope | Research repo must not drift into execution. |
| Old `tradingbot` package | legacy visible, not v2 core | Keep compatibility only if needed. |

### 20.4 Legacy audit record

```yaml
legacy_audit_record:
  subsystem: required
  files_reviewed:
    - required
  current_purpose: required
  v2_usefulness: high_medium_low_none
  risks_found:
    - optional
  bugs_found:
    - optional
  recommended_action: reuse_as_is_or_reuse_after_fix_or_wrap_into_v2_or_migrate_into_v2_or_freeze_drawer_or_no_touch_without_scope_or_remove_later
  required_fixes:
    - optional
  audit_id: V2-AUD-LEGACY-...
  final_status: pending_or_accepted_or_blocked
```

### 20.5 Legacy migration tests

Create tests:

- `test_legacy_live_paths_are_no_touch_by_default`
- `test_legacy_gui_not_imported_by_v2_core`
- `test_old_outputs_are_preserved_not_modified`
- `test_legacy_reuse_requires_audit_record`
- `test_migrated_legacy_strategy_conforms_to_v2_protocol`

---

## 21. Audit-by-chunk system

### 21.1 Audit principle

No large unbounded audit. Every change belongs to one audit chunk.

```text
Every audit chunk has an ID, scope, files, contracts, tests, and auditor note.
No chunk is accepted without independent review.
```

### 21.2 Audit ID format

```text
V2-AUD-<AREA>-<NUMBER>
```

Areas:

| Area | Meaning |
|---|---|
| `SCOPE` | product identity and direction docs |
| `LEGACY` | legacy inspection/classification/migration |
| `ARCH` | archive layout, manifests, hashes |
| `UNIV` | universe snapshots and instrument catalog |
| `QUAL` | data quality and coverage |
| `COLLECT` | collectors and backfill jobs |
| `BTDATA` | backtest data service |
| `BTENG` | vectorized/event-driven engines |
| `STRAT` | strategy specs/plugins |
| `COST` | fees/funding/slippage/impact models |
| `LEDGER` | experiment ledger and exports |
| `LEAD` | Lead Book |
| `VAL` | validation/lockbox/walk-forward/overfit |
| `FINAL` | final hard-test workflow |
| `WORKER` | jobs, queues, durability |
| `UI` | future v2 UI |
| `SEC` | security/hygiene |
| `XVENUE` | cross-venue adapters |
| `HIP3` | HIP-3/RWA specifics |

### 21.3 Audit chunk limits

```yaml
audit_chunk_limits:
  max_bounded_contexts: 1
  max_source_files: 15
  max_changed_loc: 1500
  max_contracts: 2
  max_major_behaviors: 1
```

Split any change exceeding these limits.

### 21.4 Audit states

```text
planned
  -> implemented
  -> self_checked
  -> independent_agent_audited
  -> fixed_after_audit
  -> accepted
```

Additional states:

```text
blocked
needs_ceo_decision
superseded
rolled_back
```

### 21.5 Audit index record

```yaml
audit_id: V2-AUD-BTDATA-001
area: backtest_data
status: planned
purpose: enforce 2024+, dynamic lockbox, coverage, as-of universe in data reads
files_owned:
  - src/tradingbotsuite/v2/backtest_data/service.py
  - src/tradingbotsuite/v2/backtest_data/policies.py
  - tests/v2/backtest_data/test_lockbox_policy.py
contracts:
  - docs/contracts/backtest_data_service_contract.md
  - docs/contracts/validation_contract.md
no_touch_paths:
  - src/tradingbotsuite/live/**
  - src/tradingbot/**
risk_flags:
  - lockbox_bypass
  - survivorship_bias
  - coverage_silent_failure
required_tests:
  - PYTHONPATH=src python -m pytest tests/v2/backtest_data -q
auditor: independent_agent_required
acceptance: ordinary backtest data request overlapping lockbox fails before strategy code runs
```

### 21.6 Code-level audit marker

Each new v2 module should include a module-level marker:

```python
# V2-AUDIT-ID: V2-AUD-BTDATA-001
# V2-CONTRACTS: docs/contracts/backtest_data_service_contract.md
# V2-BOUNDARY: research_only, no_live_imports, lockbox_enforced
# V2-OWNER: backtest_data
```

Do not spam every function. Place the marker at module/package level.

### 21.7 Auditor checklist

Each independent audit must answer:

1. What changed?
2. What contracts apply?
3. What files were touched?
4. Were no-touch paths modified?
5. Does the change preserve research-only boundaries?
6. Does it import live/order/runtime code?
7. Does it mutate old evidence?
8. Does it preserve deterministic IDs/hashes?
9. Does it enforce data snapshot identity where relevant?
10. Does it enforce 2024+, 6-month minimum, coverage, and lockbox where relevant?
11. Does it preserve as-of universe logic?
12. Does it log failed trials where relevant?
13. Are costs/funding/slippage net metrics included where relevant?
14. Are tests adequate?
15. Is rollback clear?
16. Are there hidden assumptions?
17. Does this chunk introduce UI/live/paper/candidate implications?
18. Pass/fail decision?

---

## 22. No-touch registry

Create `docs/V2_NO_TOUCH_PATHS.md` before touching code.

Initial registry:

```yaml
no_touch_categories:
  live_runtime:
    examples:
      - src/**/live/**
      - src/**/runtime/**
    reason: research repo must not mutate execution behavior
  order_placement:
    examples:
      - src/**/*order*place*/**
      - src/**/*broker*/**
    reason: out of scope and dangerous
  sizing_runtime_config:
    reason: no sizing/order instructions
  old_evidence_artifacts:
    examples:
      - data/**/candidate*/**
      - runs/legacy/**
    reason: preserve audit history
  candidate_pack_paths:
    reason: truth layer; only modify under explicit validation scope
  legacy_gui:
    reason: drawer/frozen until v2 UI is planned
  old_tradingbot_package:
    reason: legacy visible but not v2 core
```

No-touch does not mean never changes. It means cannot be touched accidentally.

---

## 23. Worker and operations implementation

### 23.1 Worker types

Required workers:

- universe refresh worker;
- WebSocket capture worker;
- REST/S3 backfill worker;
- bronze/silver normalization worker;
- coverage audit worker;
- vectorized backtest worker;
- event-driven simulation worker;
- ledger append/export worker;
- audit/check worker.

### 23.2 ASGI/operator separation

ASGI/operator UI may submit jobs and show status. It must not execute long collectors/backtests in-process.

Acceptance test:

```text
A long backtest or WebSocket capture does not block health/operator API responsiveness.
```

### 23.3 Job state transitions

```text
queued
  -> claimed
  -> running
  -> succeeded

queued
  -> claimed
  -> running
  -> failed
  -> retrying
  -> queued

queued/running
  -> cancelled
```

Every state transition must be recorded with timestamp, worker ID, and reason.

### 23.4 Worker CLI

```bash
redx worker run --kind universe_refresh --job-store data/jobs/redx_jobs.sqlite
redx worker run --kind websocket_capture --job-store data/jobs/redx_jobs.sqlite
redx worker run --kind backtest --job-store data/jobs/redx_jobs.sqlite
redx worker status --job-store data/jobs/redx_jobs.sqlite
redx worker retry --job-id JOB-...
```

### 23.5 Operations runbook minimums

Create `docs/V2_OPERATIONS_RUNBOOK.md` with:

- how to initialize archive;
- how to start collectors;
- how to inspect job health;
- how to backfill gaps;
- how to stop workers safely;
- how to rebuild bronze/silver;
- how to snapshot archive;
- how to run a safe backtest;
- how to append ledger;
- how to export XLSX;
- how to audit a chunk;
- how to recover from corrupted partial files.

---

## 24. CLI command contract

The final CLI can use the existing repo command name if not `redx`, but the command behaviors must exist.

### 24.1 Scope and audit commands

```bash
redx scope check
redx scope print-invariant
redx audit init
redx audit list
redx audit check --audit-id V2-AUD-ARCH-001
redx audit mark --audit-id V2-AUD-ARCH-001 --status self_checked
```

### 24.2 Archive commands

```bash
redx archive init --root data/archive
redx archive validate --root data/archive
redx archive snapshot --layer silver --venue hyperliquid
redx archive manifest list --layer raw --date 2026-06-20
redx archive rebuild --from raw --to bronze --datatype candles --date 2026-06-20
redx archive rebuild --from bronze --to silver --datatype bars --timeframe 1m --date 2026-06-20
```

### 24.3 Universe commands

```bash
redx universe refresh --venue hyperliquid --min-day-notional-usd 5000000 --include-hip3-dexs
redx universe list --snapshot latest --eligible-only
redx universe explain --snapshot latest --instrument hyperliquid:perp:BTC
redx universe diff --left 2026-06-01 --right 2026-06-20
```

### 24.4 Collector commands

```bash
redx collect candles-bootstrap --venue hyperliquid --universe latest --timeframe 1m
redx collect websocket --venue hyperliquid --streams candles,trades,bbo --universe latest
redx collect funding-backfill --venue hyperliquid --universe latest --since 2024-01-01
redx collect s3-backfill --venue hyperliquid --datatype l2book --month 2026-05
```

### 24.5 Data commands

```bash
redx data coverage --universe latest --timeframe 1m --since 2024-01-01
redx data quality report --archive-snapshot latest
redx data gaps explain --instrument hyperliquid:perp:SOL --timeframe 1m
```

### 24.6 Strategy and backtest commands

```bash
redx strategy validate specs/strategies/my_strategy.yaml

redx backtest run \
  --spec specs/strategies/my_strategy.yaml \
  --universe hl_5m_v1:2025-01-01 \
  --start 2024-06-01 \
  --end 2025-05-31 \
  --timeframe 1m \
  --exclude-lockbox

redx backtest walk-forward \
  --spec specs/strategies/my_strategy.yaml \
  --start 2024-01-01 \
  --end auto_non_lockbox_end \
  --min-window-months 6 \
  --exclude-lockbox
```

### 24.7 Ledger and lead commands

```bash
redx ledger append --run runs/<run_id>/run_manifest.json
redx ledger export --format xlsx
redx ledger leaderboard --rank composite_v1 --require-validation-pass

redx lead create --source-artifact runs/<run_id>/run_manifest.json --source-type sandbox_run
redx lead list --state sandbox_screened
redx lead approve-after-human-inspection --lead-id LEAD-...
```

---

## 25. Detailed phase-by-phase implementation roadmap

This section is the primary execution plan.

### Phase 0 — Repository intake, source lock, and safety rail setup

**Audit IDs:** `V2-AUD-SCOPE-001`, `V2-AUD-SEC-001`
**Goal:** Ensure the repo can be changed safely and current docs do not mislead future agents.
**Priority:** P0
**Dependencies:** none.

#### Implementation steps

1. Create `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md` from this file.
2. Create `docs/PRODUCT_SCOPE.md` with canonical identity and research-only invariant.
3. Create `docs/V2_DECISION_REGISTER.md` with the CEO decisions D1-D29 and extras.
4. Create `docs/V2_NO_TOUCH_PATHS.md` with initial no-touch registry.
5. Create `docs/audit/V2_AUDIT_INDEX.md` with planned chunks.
6. Create `docs/audit/prompts/V2_CHUNK_AUDITOR_PROMPT.md`.
7. Search README, START_HERE, AGENTS, docs, and CLI help for stale BTC/ETH-only product framing.
8. Mark stale docs historical or update them.
9. Add a minimal test or script that scans v2 modules for blocked live/order imports once v2 modules exist.
10. Record existing repo state: git SHA, branch, package roots, test command, and current known failures.

#### Files to create/update

```text
docs/PRODUCT_SCOPE.md
docs/V2_DECISION_REGISTER.md
docs/V2_NO_TOUCH_PATHS.md
docs/audit/V2_AUDIT_INDEX.md
docs/audit/prompts/V2_CHUNK_AUDITOR_PROMPT.md
README.md
START_HERE.md
AGENTS.md or equivalent agent guidance
```

#### Acceptance criteria

- Current docs no longer present BTC/ETH as full research scope.
- Docs state USD 5M daily notional universe rule.
- Docs state 2024+, 6-month minimum, 12-month preference, dynamic lockbox, and 0.98 coverage.
- Docs explicitly remove paper/live as future roadmap option.
- No-touch registry exists.
- Audit index exists.

#### Required tests/checks

```bash
python -m pytest tests -q  # or record current known baseline if existing tests fail
rg -i "btc/eth|BTC/ETH|live-ready|paper-ready|trade-ready|order-ready|sizing-ready" README.md docs/ START_HERE* AGENTS* || true
```

The grep command should not be interpreted as automatically failing on all hits; allowed hits are historical references or explicit negations.

---

### Phase 1 — v2 package skeleton, configuration, and audit markers

**Audit IDs:** `V2-AUD-ARCH-000`, `V2-AUD-SCOPE-002`
**Goal:** Create the v2 code shell without implementing business logic yet.
**Priority:** P0
**Dependencies:** Phase 0.

#### Implementation steps

1. Create v2 package root under the repo-standard source path.
2. Add empty bounded-context packages.
3. Add shared config loader and schema version constants.
4. Add audit marker helper or convention.
5. Add basic CLI entrypoints that print help and research-only boundary.
6. Add a smoke test that imports v2 packages without importing live/order modules.
7. Add `pyproject` optional dependencies if needed: pyarrow, polars, duckdb, zstandard, pydantic, typer, openpyxl for generated XLSX export if not already available.

#### Files

```text
src/tradingbotsuite/v2/__init__.py
src/tradingbotsuite/v2/cli/main.py
src/tradingbotsuite/v2/config/settings.py
src/tradingbotsuite/v2/config/schemas.py
src/tradingbotsuite/v2/audit/markers.py
tests/v2/test_import_boundaries.py
tests/v2/test_cli_smoke.py
```

#### Acceptance criteria

- `python -m tradingbotsuite.v2.cli.main --help` or equivalent command works.
- Importing v2 package does not import live/order/sizing runtime modules.
- All new modules contain module-level audit markers.
- CLI help says research-only and non-live.

---

### Phase 2 — Contract files and schema-first implementation foundation

**Audit IDs:** `V2-AUD-SCOPE-003`, `V2-AUD-ARCH-001`
**Goal:** Create enforceable schemas/contracts before implementing collectors/backtests.
**Priority:** P0
**Dependencies:** Phase 1.

#### Implementation steps

1. Create contract markdown files listed in Section 7.
2. Implement Python schema models for:
   - archive config;
   - universe config;
   - validation config;
   - lockbox policy;
   - cost model config;
   - run manifest skeleton;
   - ledger row skeleton;
   - Lead Book row skeleton.
3. Implement hash utilities:
   - file SHA-256;
   - canonical JSON hashing;
   - deterministic snapshot hashing over sorted manifest rows.
4. Implement UTC timestamp utilities.
5. Implement path policy root checks.

#### Acceptance criteria

- Config files validate.
- Hash utility returns stable hashes across runs.
- Path policy rejects path traversal outside archive/run roots.
- Contract docs exist and match schema names.

#### Tests

- `test_canonical_json_hash_is_stable`
- `test_file_sha256_matches_known_fixture`
- `test_archive_config_validates_defaults`
- `test_path_policy_rejects_parent_traversal`
- `test_run_manifest_requires_research_only_boundary`

---

### Phase 3 — Legacy subsystem inventory and classification

**Audit IDs:** `V2-AUD-LEGACY-001` through `V2-AUD-LEGACY-N`
**Goal:** Inspect legacy code before migration.
**Priority:** P0/P1
**Dependencies:** Phase 0; can run in parallel with Phase 2.

#### Implementation steps

1. Enumerate legacy subsystems:
   - strict research cycle;
   - candidate-pack gates;
   - rapid sandbox;
   - old high-return outputs;
   - rejected rows;
   - strategy plugins;
   - feature builders;
   - existing backtest engines;
   - legacy GUI;
   - live/runtime-adjacent code;
   - old `tradingbot` package.
2. Create one audit record per subsystem.
3. Classify each subsystem using labels from Section 20.
4. For useful code, identify required fixes before v2 wrapping.
5. For obsolete/dangerous code, add to no-touch registry or freeze drawer.
6. Preserve old outputs and rejected rows as future Lead Book or negative-control sources.

#### Acceptance criteria

- No legacy subsystem is reused without a legacy audit record.
- Legacy GUI is marked freeze/drawer.
- Live/runtime-adjacent code is no-touch without explicit scope.
- Old outputs are preserved, not rewritten.

---

### Phase 4 — Archive layout, raw writer, manifests, and snapshots

**Audit IDs:** `V2-AUD-ARCH-002`, `V2-AUD-ARCH-003`
**Goal:** Build storage foundation before large collection.
**Priority:** P0
**Dependencies:** Phase 2.

#### Implementation steps

1. Implement `ArchiveLayout` with deterministic paths.
2. Implement raw writer for JSONL.zst.
3. Implement Parquet writer for bronze/silver/gold tables.
4. Implement `file_manifest` append/update logic.
5. Implement `ingestion_runs` records.
6. Implement archive validation command.
7. Implement archive snapshot command for silver/gold subsets.
8. Implement deterministic snapshot hashing.
9. Add fixture raw payload and expected bronze/silver outputs.

#### Files

```text
src/tradingbotsuite/v2/archive/layout.py
src/tradingbotsuite/v2/archive/raw_writer.py
src/tradingbotsuite/v2/archive/parquet_writer.py
src/tradingbotsuite/v2/archive/manifest_store.py
src/tradingbotsuite/v2/archive/snapshots.py
src/tradingbotsuite/v2/archive/hashing.py
tests/v2/archive/
```

#### Acceptance criteria

- `redx archive init` creates directory tree safely.
- Raw file is written before normalization.
- Manifest records SHA-256, byte size, row count, layer, schema version, source parent IDs.
- Snapshot ID changes when included input changes.
- Bronze/silver rebuild is deterministic on fixture data.

#### Tests

- `test_raw_payload_written_before_normalization`
- `test_file_manifest_has_sha256_size_rows_schema_version`
- `test_bronze_to_silver_rebuild_is_deterministic`
- `test_archive_snapshot_id_changes_when_input_changes`
- `test_archive_validate_detects_missing_manifest_file`

---

### Phase 5 — Hyperliquid universe manager and instrument catalog

**Audit IDs:** `V2-AUD-UNIV-001`, `V2-AUD-HIP3-001`
**Goal:** Dynamic instrument universe with USD 5M rule and HIP-3/RWA support.
**Priority:** P0
**Dependencies:** Phase 4 raw writer; Phase 2 schemas.

#### Implementation steps

1. Implement Hyperliquid info client for metadata and asset contexts.
2. Write raw `metaAndAssetCtxs` payloads before parsing.
3. Parse instrument metadata into `instrument_catalog`.
4. Parse asset context into `asset_context_snapshot`.
5. Generate `universe_snapshot` rows.
6. Implement eligibility rule: active Hyperliquid perp and `dayNtlVlm >= 5_000_000`.
7. Include below-threshold instruments with `eligible=false` and exclusion reason.
8. Implement as-of universe selection.
9. Implement current universe sandbox labeling.
10. Implement HIP-3/RWA metadata fields and blocker status if missing.

#### Acceptance criteria

- `redx universe refresh --venue hyperliquid --min-day-notional-usd 5000000` creates a snapshot.
- Non-BTC/ETH symbols can pass eligibility in fixtures.
- Below-threshold instruments are archived but excluded.
- HIP-3/RWA prefixed symbols are represented with namespace metadata.
- As-of selection does not use future volume snapshots.

---

### Phase 6 — Data quality and coverage service

**Audit IDs:** `V2-AUD-QUAL-001`
**Goal:** Prevent hidden data gaps from inflating research results.
**Priority:** P0/P1
**Dependencies:** Phase 4 archive, Phase 5 universe.

#### Implementation steps

1. Implement expected-row calculators for bars by timeframe.
2. Implement coverage ratio by instrument/timeframe/date/window.
3. Implement duplicate timestamp detection.
4. Implement stale and zero-volume checks.
5. Implement outlier checks for returns/spreads/funding.
6. Implement coverage manifest writer.
7. Implement `redx data coverage` and `redx data quality report`.
8. Add coverage gate integration point for backtest data service.

#### Acceptance criteria

- Coverage reports are queryable by instrument/date/timeframe.
- Missing days are reported explicitly.
- Coverage below 0.98 fails reported/evidence mode.
- Sandbox diagnostic exceptions are labeled non-evidence.

---

### Phase 7 — Durable workers and collector jobs

**Audit IDs:** `V2-AUD-WORKER-001`, `V2-AUD-COLLECT-001`
**Goal:** Run collection/backtests as durable jobs outside ASGI/operator loop.
**Priority:** P0/P1
**Dependencies:** Phase 4 archive; Phase 5 universe.

#### Implementation steps

1. Implement SQLite WAL job store.
2. Implement job claim/heartbeat/state transition logic.
3. Implement worker CLI.
4. Implement `universe_refresh` job.
5. Implement recent candle bootstrap job with API-cap warning.
6. Implement funding backfill job.
7. Implement WebSocket capture skeleton for candles/trades/BBO/L2.
8. Implement reconnect/backoff/gap records.
9. Add operation runbook.

#### Acceptance criteria

- Collector jobs survive process restart.
- Reconnect produces gap records instead of silent success.
- Long job is not run inside ASGI/operator process.
- Job outputs are tied to archive manifests.

---

### Phase 8 — Bronze and silver pipelines for candles, funding, and contexts

**Audit IDs:** `V2-AUD-ARCH-004`, `V2-AUD-QUAL-002`
**Goal:** Produce backtest-ready bars and funding/context tables from collected data.
**Priority:** P0
**Dependencies:** Phase 4, Phase 5, Phase 7.

#### Implementation steps

1. Parse raw candle messages into bronze candles.
2. Parse funding history into bronze funding rows.
3. Parse asset contexts into bronze context rows.
4. Normalize bronze candles to silver bars.
5. Derive 5m/15m/1h bars from 1m where possible.
6. Normalize funding into UTC intervals.
7. Normalize mark/oracle/open-interest context fields.
8. Record gap and normalization manifests.
9. Generate initial archive snapshot.

#### Acceptance criteria

- Fixture raw payload can flow raw -> bronze -> silver.
- Silver bar schema is stable and documented.
- Funding rows are usable by cost/funding model.
- Coverage manifests update after silver build.

---

### Phase 9 — Backtest data service with date, lockbox, coverage, and universe enforcement

**Audit IDs:** `V2-AUD-BTDATA-001`
**Goal:** Safe deterministic historical reads.
**Priority:** P0
**Dependencies:** Phase 6, Phase 8.

#### Implementation steps

1. Implement lockbox policy calculator.
2. Implement data service `load_panel` over Parquet through DuckDB/Polars.
3. Enforce earliest start >= 2024-01-01 in reported mode.
4. Enforce 6 usable months minimum in accepted mode.
5. Enforce lockbox exclusion for ordinary requests.
6. Enforce coverage >= 0.98.
7. Enforce as-of universe for evidence mode.
8. Support current universe only as sandbox.
9. Record data manifest for each request.
10. Add benchmark tests for common queries.

#### Acceptance criteria

- Request overlapping lockbox fails before strategy code runs.
- Request before 2024 fails in reported mode.
- Request with <6 usable months fails in accepted mode.
- Valid request returns deterministic panel and data manifest.

---

### Phase 10 — Declarative strategy spec lane

**Audit IDs:** `V2-AUD-STRAT-001`
**Goal:** Allow agents to express strategy ideas safely.
**Priority:** P0
**Dependencies:** Phase 9.

#### Implementation steps

1. Implement declarative strategy schema.
2. Implement schema validator.
3. Implement allowed indicator/expression registry.
4. Implement compiler from declarative spec to signal frame.
5. Add example specs:
   - cross-sectional momentum;
   - mean reversion;
   - funding/carry;
   - volatility breakout;
   - liquidity-filtered variant.
6. Reject unsupported arbitrary Python or side effects.

#### Acceptance criteria

- At least three declarative example strategies validate.
- Invalid specs fail with clear errors.
- Specs cannot request network, secrets, arbitrary files, live/order paths, or lockbox access.

---

### Phase 11 — Vectorized backtest engine and run artifacts

**Audit IDs:** `V2-AUD-BTENG-001`
**Goal:** Fast comparable multi-instrument backtests.
**Priority:** P0
**Dependencies:** Phase 9, Phase 10.

#### Implementation steps

1. Implement `StrategyContext` and signal frame contract.
2. Implement vectorized position/portfolio simulator.
3. Implement price basis handling.
4. Implement basic position/risk constraints.
5. Implement missing data policy.
6. Emit required run artifacts.
7. Record run manifest and metrics.
8. Log failed runs as artifacts.

#### Acceptance criteria

- At least three strategy templates run over same data snapshot.
- Runs produce the required artifact directory.
- Runs are reproducible from `run_manifest.json`.
- Failed runs record failure artifacts.

---

### Phase 12 — Cost, funding, slippage, and impact models

**Audit IDs:** `V2-AUD-COST-001`
**Goal:** Net-of-cost realism and cost sensitivity.
**Priority:** P0
**Dependencies:** Phase 11.

#### Implementation steps

1. Implement fee model.
2. Implement funding PnL model.
3. Implement spread/slippage model.
4. Implement volume participation cap.
5. Implement impact model skeleton.
6. Implement stress_2x and stress_3x cost runs.
7. Add cost manifest.
8. Integrate cost metrics into engine and ledger rows.

#### Acceptance criteria

- Metrics include gross and net.
- Funding affects net results.
- Slippage/fees reduce net results.
- Cost stress matrix is produced.
- Gross-only result cannot be promoted or ranked.

---

### Phase 13 — Append-only ledger and generated spreadsheet

**Audit IDs:** `V2-AUD-LEDGER-001`
**Goal:** Central canonical experiment record.
**Priority:** P0
**Dependencies:** Phase 11, Phase 12.

#### Implementation steps

1. Implement ledger schema.
2. Implement append validator.
3. Implement append-only Parquet write path.
4. Implement CSV export.
5. Implement XLSX export.
6. Implement duplicate detection.
7. Implement failed trial rows.
8. Implement leaderboard composite report.

#### Acceptance criteria

- Every accepted run has one ledger row.
- Failed runs can be logged and counted.
- Invalid manifests cannot enter ledger.
- XLSX is generated from canonical ledger, not hand-edited.

---

### Phase 14 — Walk-forward validation and overfit controls

**Audit IDs:** `V2-AUD-VAL-001`
**Goal:** Make agent iteration less likely to fool itself.
**Priority:** P1 after M1, P0 before large sweeps.
**Dependencies:** Phase 13.

#### Implementation steps

1. Implement walk-forward splitter.
2. Implement purged/embargoed split support.
3. Implement fold metrics.
4. Implement trial family tracking.
5. Implement PBO/CSCV diagnostic spike.
6. Implement best-vs-median family report.
7. Integrate fold stability into leaderboard.

#### Acceptance criteria

- Sweeps record every trial.
- Leaderboard shows trial count and fold stability.
- Strategies can fail validation despite attractive headline Sharpe.

---

### Phase 15 — Lead Book and lead workflow

**Audit IDs:** `V2-AUD-LEAD-001`
**Goal:** Queue promising ideas without implying candidate/trading readiness.
**Priority:** P1
**Dependencies:** Phase 13; can create schema earlier.

#### Implementation steps

1. Implement Lead Book schema.
2. Implement lead store as Parquet with CSV export.
3. Implement `lead create` from run artifacts and external sources.
4. Implement human inspection statuses.
5. Implement agent approval after human inspection.
6. Implement ROI observed and projection fields.
7. Implement lead promotion gates.
8. Implement diminishing returns warning.
9. Implement pre-2024 fallback metadata for diagnostic-only cases.

#### Acceptance criteria

- Agents can create lead rows with source hash.
- Deep validation cannot start without human inspection completed.
- ROI projection is clearly labeled as assumption, not proof.
- Lead gates enforce stability/trade-frequency/profit-concentration rules.

---

### Phase 16 — Event-driven engine skeleton and microstructure path

**Audit IDs:** `V2-AUD-BTENG-002`
**Goal:** Ensure event-driven lane exists under shared contracts.
**Priority:** P1/P2
**Dependencies:** Phase 11, Phase 12, L2/trade data availability.

#### Implementation steps

1. Implement event-driven engine interface using same run artifact contract.
2. Implement event clock and event queue skeleton.
3. Implement order/fill simulation without real orders.
4. Implement BBO/L2 data ingestion into simulator inputs.
5. Implement queue-model placeholder that blocks maker assumptions unless configured.
6. Add tests proving event-driven artifacts match vectorized artifact contract.

#### Acceptance criteria

- Event-driven engine can run fixture data and output required artifacts.
- It does not place orders or imply order readiness.
- Maker assumptions require queue model.

---

### Phase 17 — Aggressive collection expansion: trades, L2/BBO, S3

**Audit IDs:** `V2-AUD-COLLECT-002`, `V2-AUD-ARCH-005`
**Goal:** Move from 1m/funding/context to fuller market-data archive.
**Priority:** P1/P2
**Dependencies:** Phase 7, Phase 8, storage budget.

#### Implementation steps

1. Enable trades capture for eligible universe.
2. Enable BBO capture for eligible universe.
3. Enable L2 snapshots for top liquidity instruments or full eligible universe if storage budget allows.
4. Add official S3 backfill where available.
5. Add storage budget monitor.
6. Add retention/backup policy.
7. Update coverage and quality reports for trades/L2/BBO.

#### Acceptance criteria

- Trades/BBO/L2 files are raw-preserved and manifest-recorded.
- Storage growth is visible.
- Gaps and reconnects are recorded.
- Event-driven engine can consume fixture microstructure data.

---

### Phase 18 — Useful legacy migration into v2 contracts

**Audit IDs:** `V2-AUD-LEGACY-010+`
**Goal:** Reuse useful legacy research value safely.
**Priority:** P1/P2 depending subsystem.
**Dependencies:** Phase 3, relevant v2 contract available.

#### Implementation steps

1. Select one audited legacy subsystem.
2. Confirm classification is `reuse_as_is`, `reuse_after_fix`, `wrap_into_v2`, or `migrate_into_v2`.
3. Implement required fixes first.
4. Wrap behavior behind v2 interface.
5. Add regression tests proving useful behavior preserved.
6. Add boundary tests proving no live/order/sizing behavior entered v2.
7. Preserve old artifacts and record source hash.

#### Acceptance criteria

- Migration is chunked and audited.
- Useful legacy value is preserved.
- Legacy behavior now emits v2 manifests/ledger rows where relevant.

---

### Phase 19 — Cross-venue adapter interface and first comparable venue

**Audit IDs:** `V2-AUD-XVENUE-001`
**Goal:** Add compatible data without corrupting Hyperliquid-first design.
**Priority:** P2
**Dependencies:** Phase 4, Phase 9, Phase 10.

#### Implementation steps

1. Finalize generic venue adapter protocol.
2. Implement CCXT adapter or first native external venue adapter.
3. Normalize symbols into instrument catalog.
4. Preserve venue provenance on every row.
5. Add cross-venue coverage reports.
6. Add feature flags/spec fields for cross-venue data usage.

#### Acceptance criteria

- Backtest data service can load comparable bars/funding for one non-Hyperliquid venue.
- Venue provenance is explicit in every row and manifest.
- Hyperliquid USD 5M universe remains default.

---

### Phase 20 — Deep validation runner and final hard-test workflow

**Audit IDs:** `V2-AUD-FINAL-001`, `V2-AUD-VAL-002`
**Goal:** Execute serious-lead validation safely.
**Priority:** P2 after Lead Book and validation base exist.
**Dependencies:** Phase 14, Phase 15.

#### Implementation steps

1. Implement one-active-serious-lead lock.
2. Implement deep validation run manifest.
3. Implement full scorecard with required checks.
4. Implement pre-2024 fallback diagnostic path.
5. Implement final hard-test slot manager with max 3 slots.
6. Implement frozen strategy/params/data/cost model enforcement.
7. Implement final survivor report template with non-live disclaimer.

#### Acceptance criteria

- Only one deep validation runs at a time.
- Only top 3 final hard-test slots exist.
- Final hard-test requires frozen strategy, params, data, universe, and cost model.
- Final reports never imply paper/live/trade readiness.

---

### Phase 21 — Security and hygiene hardening

**Audit IDs:** `V2-AUD-SEC-002+`
**Goal:** Preserve previous hardening work while keeping product focus.
**Priority:** Parallel P1/P2, P0 if same files or active risk.
**Dependencies:** can run throughout.

#### Implementation steps

1. Fail-closed webhook secret policy.
2. Secure operator cookies/admin posture.
3. Explicit credential loading policy.
4. Pickle/artifact hash and trusted-root validation.
5. Command classification metadata.
6. Path policy service.
7. Dependency constraints and lockfiles.
8. CI tiers and benchmarks.
9. Logging redaction.
10. Import-boundary tests for live/runtime code.

#### Acceptance criteria

- Secrets fail closed.
- Unsafe artifacts are blocked.
- Logs redact sensitive values.
- v2 research commands remain isolated from live/order paths.

---

### Phase 22 — Future v2 UI, delayed

**Audit IDs:** `V2-AUD-UI-001`
**Goal:** Eventually replace legacy GUI with v2 visibility surface.
**Priority:** last.
**Dependencies:** stable archive/data/backtest/ledger/lead foundation.

#### UI should show

- active universe;
- included/excluded instruments and reasons;
- HIP-3/RWA caveats;
- data collection status;
- archive coverage;
- gap reports;
- lockbox range;
- Lead Book;
- deep validation state;
- final hard-test candidates;
- audit chunk status;
- worker/job health.

#### Do not do early

- Do not rebuild UI before data foundation.
- Do not let legacy GUI define v2 behavior.
- Do not run collectors/backtests in UI process.

---

## 26. Milestones

### M0 — Product scope and safety foundation

M0 is complete when:

1. Product docs reflect v2 identity.
2. Research-only invariant is in docs and run schemas.
3. No-touch registry exists.
4. Audit index exists.
5. v2 package skeleton imports without live/order dependencies.

### M1 — Dynamic Hyperliquid 1m-bar research loop

M1 is the first practical value milestone.

Scope:

- Hyperliquid perps only.
- Universe from mocked or live metadata/context snapshot.
- Eligibility: `dayNtlVlm >= 5_000_000`.
- Data: 1m candles, funding, daily asset context.
- Storage: raw + silver Parquet + manifests.
- Backtest: vectorized bar engine.
- Strategies: at least 3 declarative examples.
- Validation: 2024+ start, minimum 6 months, lockbox exclusion.
- Ledger: append-only canonical file and generated XLSX export.

M1 acceptance:

```text
1. redx universe refresh creates a universe snapshot.
2. redx data coverage shows coverage by eligible instrument.
3. redx backtest run rejects pre-2024/short/lockbox-overlapping runs.
4. redx backtest run accepts a valid 6+ month non-lockbox window.
5. redx ledger append writes standardized run metrics.
6. A failed strategy trial is recorded rather than hidden.
```

### M2 — Validation and Lead Book readiness

M2 is complete when:

1. Walk-forward validation works.
2. Trial families and failed trials are logged.
3. Lead Book schema/store/commands exist.
4. Human inspection and agent approval gates work.
5. Lead promotion gates enforce trade frequency, monthly stability, profit concentration, and diminishing return warning.

### M3 — Aggressive market-data expansion

M3 is complete when:

1. Trades are collected and archived.
2. BBO is collected and archived.
3. L2 collection is available under storage controls.
4. Official S3 loader works where available.
5. Event-driven engine can consume fixture microstructure data.

### M4 — Deep validation and final hard-test governance

M4 is complete when:

1. One-serious-lead-at-a-time deep validation is enforced.
2. Final hard-test max 3 slots is enforced.
3. Frozen strategy/params/data/cost model requirements are enforced.
4. Final survivor report template includes non-live disclaimer.

### M5 — Cross-venue comparison

M5 is complete when:

1. First comparable venue adapter is implemented.
2. Cross-venue data has explicit provenance.
3. Hyperliquid-first default remains intact.
4. Cross-venue robustness tests can run without corrupting Hyperliquid evidence rules.

---

## 27. Acceptance test suite summary

### Universe

- `test_hyperliquid_universe_includes_non_btc_eth_above_5m`
- `test_hyperliquid_universe_excludes_below_5m_day_ntl_volume`
- `test_hyperliquid_universe_archives_excluded_instruments`
- `test_hyperliquid_universe_handles_hip3_prefixed_symbols`
- `test_asof_universe_does_not_use_future_volume_snapshot`
- `test_current_universe_mode_is_sandbox_only`

### Archive

- `test_raw_payload_written_before_normalization`
- `test_file_manifest_has_sha256_size_rows_schema_version`
- `test_bronze_to_silver_rebuild_is_deterministic`
- `test_data_coverage_reports_missing_days`
- `test_archive_snapshot_id_changes_when_input_changes`
- `test_archive_validate_detects_missing_manifest_file`

### Backtest data service

- `test_reported_backtest_rejects_start_before_2024`
- `test_reported_backtest_rejects_less_than_6_months`
- `test_backtest_rejects_lockbox_overlap`
- `test_backtest_loads_only_declared_fields`
- `test_backtest_uses_asof_universe_snapshot`
- `test_warmup_bars_do_not_enter_reported_pnl`
- `test_coverage_below_098_fails_reported_mode`

### Strategy and engine

- `test_declarative_strategy_validates_schema`
- `test_strategy_cannot_access_network_or_credentials`
- `test_same_run_manifest_reproduces_metrics_on_fixture_data`
- `test_funding_and_fees_affect_net_results`
- `test_missing_data_policy_is_explicit`
- `test_vectorized_engine_outputs_required_artifacts`
- `test_event_driven_engine_skeleton_outputs_same_artifact_contract`

### Ledger

- `test_ledger_append_rejects_missing_run_manifest`
- `test_ledger_append_rejects_missing_validation_status`
- `test_ledger_records_failed_trials`
- `test_ledger_rejects_duplicate_run_id`
- `test_xlsx_export_is_generated_from_canonical_ledger`
- `test_leaderboard_excludes_sandbox_current_universe_claims`

### Lead Book

- `test_agent_can_create_lead_with_source_hash`
- `test_lead_cannot_deep_validate_without_human_inspection_completed`
- `test_agent_approval_requires_human_inspection`
- `test_lead_schema_requires_roi_observed_and_projected`
- `test_six_losing_months_fails_lead_gate`
- `test_profit_concentration_warning_and_fail_thresholds`
- `test_minimum_five_trades_per_month_gate`
- `test_diminishing_returns_warning_is_recorded`

### Overfitting and validation

- `test_experiment_sweep_records_all_trials`
- `test_walk_forward_folds_are_time_ordered`
- `test_embargo_gap_excludes_boundary_rows`
- `test_leaderboard_warns_when_best_result_is_from_many_trials`
- `test_pbo_diagnostic_runs_for_large_strategy_family`

### Workers and security

- `test_collector_job_state_survives_process_restart`
- `test_long_collector_not_run_inside_asgi_loop`
- `test_v2_core_has_no_live_order_imports`
- `test_path_policy_rejects_parent_traversal`
- `test_secrets_fail_closed`
- `test_unsafe_pickle_requires_trusted_hash_and_root`

---

## 28. Risk register and mitigations

| Risk | Probability | Impact | Mitigation |
|---|---:|---:|---|
| Hyperliquid recent candle history insufficient for 6–12 month tests | High | Critical | Owned archive, WebSocket capture, S3/vendor backfill where allowed, coverage manifests. |
| Agents overfit by repeatedly testing recent months | High | Critical | Data-service lockbox enforcement, trial ledger, walk-forward, final hard-test freeze. |
| Survivor bias from current liquid universe | High | High | As-of universe snapshots; current universe sandbox label only. |
| Data gaps silently inflate performance | Medium-high | High | Coverage gates, gap manifests, no silent repair. |
| Spreadsheet drift | High | Medium-high | Append-only Parquet ledger; generated XLSX only. |
| L2/trade storage growth | Medium | Medium-high | Storage budget, tiered collection, retention/backup policy. |
| Backtester too slow for agents | Medium | High | Parquet, DuckDB/Polars, vectorized path, benchmark tests. |
| Cross-venue symbol mismatch | Medium | High | Instrument catalog, canonical IDs, adapter tests, venue provenance. |
| ASGI/operator blocked by long jobs | Medium-high | High | Dedicated workers, durable job store, health tests. |
| Old live/security issues leak into v2 | Medium | High | No-touch registry, import-boundary tests, security hardening. |
| Lead Book projections misread as claims | Medium | High | Projection fields marked assumptions/not proof; non-promotable flags. |
| Legacy useful code lost | Medium | Medium | Legacy inspection/classification before deletion or rewrite. |

---

## 29. Definition of done

### 29.1 Definition of done for a code chunk

A code chunk is done only when:

- it has an audit ID;
- it touches only declared files;
- it respects no-touch paths;
- it includes module-level audit marker;
- relevant contract docs exist;
- tests are added or updated;
- tests pass or current known failures are documented;
- no live/paper/order/sizing behavior is introduced;
- manifests/hashes/snapshots are recorded where relevant;
- failure modes are recorded;
- independent audit is completed or explicitly pending before merge.

### 29.2 Definition of done for a backtest result

A backtest result is accepted for research reporting only when:

- start date >= 2024-01-01;
- usable months >= 6;
- lockbox is excluded;
- coverage >= 0.98;
- as-of universe is used for evidence;
- strategy spec and params are hashed;
- archive/universe/feature snapshot IDs are present;
- gross and net metrics are present;
- cost/funding/slippage/impact are represented;
- validation status is present;
- failed or passed run is appended to ledger;
- research-only invariant is preserved.

### 29.3 Definition of done for M1

M1 is done when a new agent can run:

```bash
redx universe refresh --venue hyperliquid --min-day-notional-usd 5000000
redx data coverage --universe latest --timeframe 1m --since 2024-01-01
redx strategy validate specs/strategies/example_momentum.yaml
redx backtest run --spec specs/strategies/example_momentum.yaml --universe latest_asof --start 2024-06-01 --end auto_non_lockbox_end --timeframe 1m --exclude-lockbox
redx ledger append --run runs/<run_id>/run_manifest.json
redx ledger export --format xlsx
```

And the system correctly rejects:

- pre-2024 start;
- <6 months;
- lockbox overlap;
- current-universe evidence claim;
- missing cost model;
- missing run manifest;
- duplicate ledger run ID.

---

## 30. Open questions and safe defaults

These questions should be resolved when practical. They do not block starting implementation because safe defaults are provided.

| Question | Safe default now | When to revisit |
|---|---|---|
| Physical archive location | local `data/archive` with path policy and backup notes | before large L2/trade capture |
| Storage budget | configure warning thresholds; no silent deletion | before aggressive L2 full universe |
| Raw compression | JSONL.zst or native compressed official file | during archive implementation |
| Backup policy | hash manifests and raw files; document manual backup | before continuous collectors are relied upon |
| Alerting channel | log + local job status initially | before unattended continuous capture |
| RWA reference data sources | metadata fields required; evidence blocked if missing | before RWA strategies are accepted |
| Capital for ROI projection | mark projection confidence unknown unless specified | before serious Lead Book ranking uses ROI projection |
| Maker assumptions | blocked until queue model exists | event-driven expansion |
| Exact diminishing-return formula | early/middle/late window decay ratio warning | Lead Book gate implementation |
| Human inspector identity | freeform manual note initially | before production Lead Book workflow |
| Final top-3 selector | require explicit recorded selection note | before first final hard-test |

---

## 31. Agent execution template

Use this template for every implementation agent:

```text
You are implementing one ResearchEngineDeluxe v2 chunk.

Audit ID:
Bounded context:
Goal:
Contracts:
Files allowed:
No-touch paths:
Required tests:
Acceptance criteria:
Rollback plan:

Rules:
1. Preserve research-only invariant.
2. Do not introduce paper/live/order/sizing/runtime behavior.
3. Do not touch no-touch paths unless explicitly scoped.
4. Do not bypass archive/data-service/ledger contracts.
5. Add or update tests before claiming completion.
6. Record manifests/hashes/snapshots where relevant.
7. Keep chunk within audit size limits.
8. Produce self-check notes and mark audit status self_checked only after tests pass.
```

---

## 32. Immediate next implementation order

Start here:

1. Commit this roadmap as `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md`.
2. Create product scope, decision register, no-touch registry, audit index, and auditor prompt.
3. Create v2 package skeleton with research-only import boundary test.
4. Create archive/universe/backtest validation/ledger/Lead Book contract docs.
5. Implement archive layout, raw writer, manifest store, and hashing.
6. Implement Hyperliquid universe snapshot fixtures and eligibility tests.
7. Implement data coverage and lockbox policy tests.
8. Implement backtest data service skeleton that rejects invalid windows before any strategy code exists.
9. Implement declarative strategy validator.
10. Implement vectorized fixture backtest and artifact schema.
11. Implement cost model and ledger append.
12. Complete M1 dynamic Hyperliquid 1m-bar research loop.

Do not start UI replacement, live/paper features, arbitrary Python plugins, or broad cross-venue work before M1 is stable.

---

## 33. Final implementation summary

The implementation path is deliberately strict:

```text
scope and no-touch docs
  -> v2 skeleton and contracts
  -> legacy inventory
  -> archive foundation
  -> Hyperliquid universe snapshots
  -> quality/coverage reports
  -> durable collectors
  -> lockbox-aware data service
  -> declarative strategy specs
  -> vectorized engine
  -> cost/funding/slippage/impact
  -> append-only ledger
  -> validation and Lead Book
  -> event-driven and aggressive market-data expansion
  -> useful legacy migration
  -> cross-venue comparison
  -> deep validation and final hard-test
  -> UI last
```

The first real product milestone is not a UI, not a live trading path, and not a generic audit. It is the M1 dynamic Hyperliquid 1m-bar research loop with owned data, strict validation, and append-only results. Once M1 exists, agents can safely generate ideas, run comparable tests, record failures, and feed a controlled Lead Book without creating an untraceable pile of one-off scripts or cherry-picked spreadsheets.
