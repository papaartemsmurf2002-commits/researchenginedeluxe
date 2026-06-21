# ResearchEngineDeluxe v2 — Agenting Development Execution Brief

**Date:** 2026-06-21
**Document type:** implementation-ready agent development brief
**Status:** curated CEO direction + audit resolution + v2 roadmap synthesis
**Primary goal:** finish ResearchEngineDeluxe v2 into an autonomous, research-only strategy checking and backtesting platform.
**Audience:** coding agents, manager agents, specialist subagents, independent auditors, and human reviewers.

---

## 0. One-sentence mission

Build ResearchEngineDeluxe v2 into a **research-only, autonomous perpetual-futures research platform** that can discover the eligible Hyperliquid universe, collect and archive market data, verify coverage, run leakage-safe backtests from 2024 onward, log every pass/fail trial, update the Lead Book and ledger, and report blockers — **without ever producing paper/live/order/sizing/runtime/promotion outputs**.

---

## 1. Executive end goal

The repository is complete when this loop can run safely and repeatedly:

```text
scheduler / manager agent
  -> universe refresh
  -> archive collection and backfill
  -> coverage and quality audit
  -> Lead Book / strategy-spec queue scan
  -> strategy spec validation
  -> backtest data-service preflight
  -> vectorized or event-driven backtest
  -> validation and anti-overfit gates
  -> gross/net/cost-stress metrics
  -> append-only ledger write
  -> Lead Book status update
  -> audit/blocker report
```

This repo does **not** become a trading system. Completion means the platform is ready for autonomous **research and backtesting**, not candidate approval, paper trading, live trading, position sizing, runtime config changes, or promotion.

---

## 2. Binding product identity

ResearchEngineDeluxe v2 is a **multi-instrument, data-first, agent-friendly perpetual-futures research operating system**.

The default research universe is:

```text
all Hyperliquid perpetual futures
where as-of daily notional volume >= USD 5,000,000
and instrument is active / not delisted / not disabled
and data coverage passes v2 gates
```

BTC and ETH remain useful fixtures, smoke-test symbols, and historical evidence symbols. They are **not** the product boundary.

HIP-3, RWA, equity, index, and commodity-style perps are in scope if they pass the same threshold, metadata, coverage, oracle/reference, and validation rules.

---

## 3. Non-negotiable branch invariant

Every v2 artifact, command, output, report, ledger row, Lead Book row, and UI surface must preserve this invariant:

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

This invariant must be enforced in code through a central artifact/boundary policy, not copied manually in every command.

### 3.1 Explicitly forbidden in this repo

Do not implement, enable, or imply:

- paper trading;
- live trading;
- order placement;
- position sizing instructions;
- runtime-mode changes;
- exchange account mutation;
- candidate-pack eligibility;
- promotion readiness;
- “strategy is ready to trade” language.

Paper/live layers already belong to a different repo or legacy context. In this repo they are **no-touch boundary concerns**, not roadmap options.

---

## 4. CEO decisions already fixed

Treat these as facts. Do not reopen them unless the human explicitly changes direction.

| Decision area | Fixed decision |
|---|---|
| Product identity | Full v2 identity: liquid Hyperliquid-perp research platform. |
| Repo purpose | Strict research-only. No paper/live path in v2. |
| Migration style | Strangler migration; do not big-bang rewrite. |
| Work planning stage | Current task is full implementation direction and execution brief, not packet debate. |
| Legacy subsystems | Inspect, audit, fix, wrap, and migrate useful pieces into v2. Do not blindly delete. |
| Legacy GUI | Drawer/frozen; do not touch for now. A new v2 UI may be written later and is low priority. |
| Legacy results | Preserve as Lead Book inputs, not candidates. |
| Lead Book | Canonical queue for serious strategy investigation. |
| Lead creation | Agents may create leads. Human inspection required before serious/deep validation approval. |
| Lead evidence | Must show stability, trade frequency, non-concentrated profit, and unseen-period performance. |
| Old rejected rows | Allowed as leads if they reveal useful failure modes or strategy ideas. |
| External papers/reports | Allowed as Lead Book hypotheses, never as evidence by themselves. |
| ROI fields | Add ROI / ROI projection fields, clearly marked projected/untrusted until validated. |
| Data archive | Repo owns canonical market archive. |
| Data collection | Aggressive collection: all available relevant data where feasible. |
| Universe threshold | Hyperliquid perps with day notional >= USD 5M. No lower threshold for evidence. |
| Universe bias | As-of universe required for evidence; current universe allowed only when labeled sandbox/current-universe research. |
| HIP-3/RWA | Included if they pass rules and coverage requirements. |
| Validation | 2024+ start, 6+ usable months, 12-month preference, lockbox exclusion, every trial logged. |
| Lockbox | Dynamic: normally 2 full months, may fall to 1 only under explicit policy for short data history. |
| Coverage | Default 0.98 minimum. |
| Strategy lanes | Declarative specs first; Python plugins later through strict protocol. |
| Backtest lanes | Both vectorized and event-driven are first-class architecture lanes. |
| Cost model | Gross and net, with base/conservative/severe cost assumptions. |
| Ledger | Append-only ledger is canonical. Spreadsheet is generated view only. |
| Failed trials | Must be logged. |
| Deep validation | One serious lead at a time by default. |
| Final hard test | Top 3 surviving leads only. |
| Final survivor meaning | Survived strict research tests; not guaranteed profitable and not trade-ready. |
| UI | New v2 UI later. Not an early blocker. |
| Workers | Dedicated workers/subprocesses, not ASGI/operator loop. |
| Job durability | SQLite WAL job store + append-only job event log first. |
| Hardening | Parallel hardening, not a reason to derail archive/backtester unless same files or active risk. |
| Diminishing returns | Lead warning if performance decays from strong early window to weak recent window. |

---

## 5. Current audit concerns to resolve

The v2 audit found a strong foundation but not an operationally complete autonomous system. Treat the audit as a blocker register, not as a reason to restart.

### 5.1 Open blockers / holes

| Issue | Decision | Required resolution |
|---|---|---|
| Self-checked only | Self-check is local evidence, not acceptance. | High-risk chunks require independent agent audit. |
| Local/uncommitted work | P0 process blocker. | Classify, stage, commit, push, and record baseline SHA before new major work. |
| Full-suite not certified in one process | Required before autonomous-ready. | Run authoritative full suite in clean pinned environment. |
| `ISSUE-R106-026` Windows socket exhaustion | Test-infrastructure blocker for Windows certification. | Fresh session, Python 3.11 env, Linux CI authoritative lane if needed, async resource hygiene. |
| Python 3.14 local default | Not authoritative. | Pin final validation to Python 3.11.x. |
| Static scans not full proof | Smoke checks only. | Add formal import/no-touch/artifact/path/secret tests. |
| Boundary flags rely on convention | Not acceptable long-term. | Central boundary builder/policy. |
| Old docs with readiness language | Can mislead agents. | Classify docs as current/historical/obsolete and lint readiness language. |
| v2 foundation not populated operation | Structural readiness only. | Build real archive/collector/coverage operation. |
| Strategy/exit semantics debt `ISSUE-R106-020` | Pre-autonomy blocker. | Contracts and regression tests for every semantics item. |

---

## 6. Required completion definition

The repo may be called **v2 autonomous research-ready** only when all of this is true:

```yaml
V2_AUTONOMOUS_RESEARCH_READY:
  repo_state:
    clean_git_tree: true
    baseline_committed_and_pushed: true
    current_control_docs_authoritative: true

  validation:
    python_3_11_pinned: true
    compile_passed: true
    contracts_passed: true
    v2_tests_passed: true
    full_suite_passed_in_authoritative_env: true

  audit:
    high_risk_chunks_independently_audited: true
    p0_blockers_open: false
    p1_blockers_open: false

  known_issues:
    ISSUE_R106_026:
      resolved_or_ci_authority_documented: true
    ISSUE_R106_020:
      closed_with_regression_tests: true

  data:
    hyperliquid_universe_snapshots_operational: true
    archive_collectors_operational: true
    coverage_reports_operational: true
    archive_snapshot_ids_required: true
    universe_snapshot_ids_required: true

  backtest_data:
    rejects_pre_2024: true
    rejects_under_6_months_for_accepted_results: true
    rejects_lockbox_overlap: true
    enforces_coverage_0_98: true
    supports_asof_universe: true

  strategy_engine:
    declarative_specs_supported: true
    python_plugins_protocol_guarded: true
    vectorized_engine_available: true
    event_driven_engine_available: true
    strategy_exit_semantics_locked: true

  ledger:
    append_only: true
    failed_trials_logged: true
    manual_spreadsheet_editing_forbidden: true
    gross_and_net_metrics_required: true
    base_conservative_severe_costs_required: true

  leadbook:
    agents_can_create_rows: true
    human_inspection_required_for_deep_validation: true
    diminishing_returns_warning: true
    profit_concentration_check: true
    minimum_trade_frequency_check: true
    monthly_stability_check: true

  workers:
    dedicated_workers: true
    durable_job_store: true
    collector_gaps_logged: true
    asgi_not_blocked_by_jobs: true

  boundaries:
    research_only: true
    paper_live_order_sizing_runtime_forbidden: true
    no_touch_paths_enforced: true
    artifact_boundary_invariant_centralized: true
```

---

## 7. Recommended architecture

```text
Agent / human researcher
  -> agent lab
  -> strategy spec validator
  -> Lead Book queue
  -> worker scheduler
  -> backtest data service
  -> vectorized engine / event-driven engine
  -> validation gate
  -> ledger append
  -> reports and audit notes

Venue collectors
  -> raw archive
  -> bronze normalized records
  -> silver cleaned market data
  -> gold strategy-ready panels/features
  -> manifests, coverage, quality, snapshots
```

### 7.1 Bounded contexts

| Context | Owns | Must not do |
|---|---|---|
| `venues` | Exchange/API/S3/WebSocket adapters, raw fetches, rate limits. | Strategy logic, scoring, ledger writes. |
| `universe` | Instrument catalog, as-of snapshots, USD 5M eligibility. | Hindsight cherry-picking. |
| `archive` | File layout, raw/bronze/silver/gold, manifests, hashes, snapshot IDs. | Direct strategy evaluation. |
| `data_quality` | Gaps, stale data, duplicates, coverage, quality reports. | Silent repair without provenance. |
| `backtest_data` | Safe historical reads, lockbox/date/coverage enforcement. | Archive mutation or network calls. |
| `strategy_specs` | Declarative strategy schema, validation, parameter bounds. | Arbitrary code execution. |
| `backtest_engine` | Simulation, exits, fills, funding, costs, metrics. | Credential access, network calls, live imports. |
| `validation` | 2024+, 6 months, lockbox, walk-forward, PBO/CSCV where used. | Strategy mutation after seeing validation. |
| `ledger` | Append-only result log and generated views. | Manual edits or hidden failed trials. |
| `leadbook` | Lead queue and serious validation state. | Candidate/trading claims. |
| `workers` | Durable jobs, collector jobs, backtest jobs, heartbeats. | ASGI/operator blocking. |
| `ui` | Read-only status later: universe, coverage, leads, blockers. | Early priority; live control surface. |
| `security_boundary` | No-touch paths, import guards, artifact flags, path policy. | Broad unscoped cleanup. |

---

## 8. Data architecture decisions

### 8.1 Archive layers

| Layer | Meaning | Rule |
|---|---|---|
| Raw | Exact venue payloads and downloaded files. | Append-only, hashed, never edited. |
| Bronze | Parsed source-equivalent rows. | Rebuildable from raw. |
| Silver | Clean research-ready market data. | Rebuildable with manifest and quality report. |
| Gold | Strategy-ready panels/features. | Versioned snapshots only. |

Agents and strategy code should never directly edit archive files. All reads must go through `backtest_data` or approved archive/data-quality tools.

### 8.2 Default archive layout

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
    bars/timeframe=1h/venue=hyperliquid/date=YYYY-MM-DD/*.parquet
    funding/venue=hyperliquid/date=YYYY-MM-DD/*.parquet
    liquidity/venue=hyperliquid/date=YYYY-MM-DD/*.parquet
    asset_context/venue=hyperliquid/date=YYYY-MM-DD/*.parquet

  gold/
    panels/timeframe=1m/universe_rule=hl_5m_v1/snapshot_id=.../*.parquet
    features/feature_set=.../snapshot_id=.../*.parquet

  manifests/
    ingestion_runs.parquet
    file_manifest.parquet
    data_coverage.parquet
    data_quality.parquet
    archive_snapshots.parquet
    universe_snapshots.parquet
    feature_snapshots.parquet

  performance/
    experiment_ledger.parquet
    experiment_ledger.csv
    experiment_ledger.xlsx

  leadbook/
    lead_book.parquet
    lead_book.csv
    lead_book.xlsx
```

### 8.3 Technology defaults

Use these defaults unless existing repo constraints force a different local implementation:

| Area | Default |
|---|---|
| Python | 3.11.x authoritative validation. |
| Storage | Parquet for canonical analytical data; JSONL/Zstd for raw payloads; generated CSV/XLSX for human views. |
| Query engine | DuckDB for SQL over Parquet; Polars lazy operations allowed where beneficial. |
| Job store | SQLite WAL first. |
| Job events | Append-only JSONL or SQLite table, mirrored to artifact manifests where useful. |
| Strategy specs | YAML/JSON declarative lane first. |
| Python strategy plugins | Later only through narrow protocol and sandbox restrictions. |
| Testing | pytest, compileall, contract tests, v2 tests, full suite in pinned env. |
| Agent orchestration | One manager agent with specialist subagents as bounded tools by default. |

Do not add heavy infrastructure such as distributed queues, MLflow, Optuna, or full production dashboards before the core v2 loop is operational unless the existing repo already has a supported path and tests.

---

## 9. Universe manager requirements

### 9.1 Eligibility rule

```text
eligible = venue == hyperliquid
           AND market_type == perp
           AND day_ntl_vlm_usd >= 5_000_000
           AND status in [active]
           AND not delisted
           AND not disabled
           AND data coverage passes evidence gate when used for evidence
```

### 9.2 Universe modes

| Mode | Allowed use | Rules |
|---|---|---|
| As-of universe | Evidence and serious validation. | Must use only snapshots available at or before the test/rebalance date. |
| Current universe | Sandbox/current tradable research only. | Must be labeled as current-universe; cannot support historical evidence claims. |
| Watchlist/excluded instruments | Archive/coverage tracking. | Can be stored and monitored, not evidence-eligible below threshold. |

### 9.3 Required tables

#### `instrument_catalog`

| Column | Required | Notes |
|---|---:|---|
| `instrument_id` | yes | Stable internal ID, e.g. `hyperliquid:perp:BTC`. |
| `venue` | yes | `hyperliquid`, `binance`, etc. |
| `venue_symbol` | yes | Exact venue symbol, including HIP-3 prefixes. |
| `canonical_symbol` | yes | Normalized symbol for specs. |
| `market_type` | yes | `perp`, `spot`, `future`, etc. |
| `base_asset` | yes | Base asset. |
| `quote_asset` | yes | Quote asset. |
| `settle_asset` | yes | Settle asset. |
| `first_seen_ts` | yes | First archive observation. |
| `last_seen_ts` | yes | Last archive observation. |
| `status` | yes | active, delisted, disabled, quarantine. |
| `sz_decimals` | if available | Hyperliquid precision. |
| `max_leverage` | if available | Metadata only; no sizing implication. |
| `only_isolated` | if available | Metadata only. |
| `source_snapshot_id` | yes | Raw provenance. |

#### `universe_snapshot`

| Column | Required | Notes |
|---|---:|---|
| `snapshot_id` | yes | Content hash or UUID. |
| `asof_date` | yes | UTC date. |
| `venue` | yes | Hyperliquid first. |
| `universe_rule_id` | yes | Example: `hl_perps_day_ntl_vlm_gte_5m_v1`. |
| `instrument_id` | yes | Internal ID. |
| `day_ntl_vlm_usd` | yes | From asset context. |
| `open_interest` | if available | From asset context. |
| `mark_px` | if available | From asset context. |
| `oracle_px` | if available | From asset context. |
| `funding` | if available | Current/context funding. |
| `eligible` | yes | Final inclusion under rule. |
| `exclusion_reason` | yes if excluded | volume below threshold, missing context, insufficient coverage, etc. |
| `raw_payload_sha256` | yes | Source hash. |

---

## 10. Data collection requirements

The system should collect aggressively, but still record capabilities and gaps honestly.

### 10.1 Required collection jobs

| Job | Cadence | Output | Notes |
|---|---:|---|---|
| `universe_refresh` | daily | raw context + universe snapshot | Include eligible and excluded instruments. |
| `recent_candle_bootstrap` | hourly/daily | recent bars | Endpoint history is limited; use for bootstrap/gap repair. |
| `websocket_candle_capture` | continuous | raw + bronze + silver bars | Core archive builder. |
| `websocket_trade_capture` | continuous | raw + bronze trades | Needed for slippage/volume/microstructure. |
| `websocket_l2_bbo_capture` | configurable continuous/sampled | raw + bronze L2/BBO | Storage-heavy but in scope. |
| `funding_backfill` | daily | funding table | Required for net perp returns. |
| `official_s3_backfill` | monthly/manual/scheduled | raw/bronze L2 and contexts | Useful but not assumed complete. |
| `coverage_audit` | daily | coverage/quality manifests | Blocks unreliable tests. |

### 10.2 Required collector behavior

Collectors must:

- write raw payloads before normalization;
- never overwrite raw data;
- attach source timestamps, local receive timestamps, and payload hashes;
- record reconnects, duplicates, gaps, and downtime;
- write gap records instead of silently hiding missing data;
- support idempotent reruns/backfills;
- avoid blocking the operator/API process;
- be stoppable/resumable through durable job state.

---

## 11. Backtest data-service requirements

All strategy runs must request data through the backtest data service.

### 11.1 Mandatory rejects

The data service must reject reported/accepted backtest requests that:

- start before `2024-01-01`;
- have fewer than 6 usable months;
- overlap the current lockbox;
- do not identify `archive_snapshot_id`;
- do not identify `universe_snapshot_id`;
- have coverage below 0.98;
- use current universe for historical evidence without explicit sandbox/current-universe label;
- request fields not declared by the strategy spec;
- attempt to load lockbox rows for ordinary backtest/optimization/leaderboard mode.

### 11.2 Lockbox policy

Default lockbox is dynamic:

```yaml
lockbox:
  default_months: 2
  minimum_months: 1
  align_to_full_calendar_months: true
  ordinary_backtests_can_access: false
  optimization_can_access: false
  leaderboard_can_access: false
  final_test_access_requires_human_approval: true
```

Use full UTC calendar months. The ordinary data-service end date must be before `lockbox_start`.

---

## 12. Strategy and backtest engine requirements

### 12.1 Meaning of “any strategy”

In this repo, “any strategy” means:

> Any deterministic strategy idea that can be expressed through a supported declarative spec or guarded Python plugin, reads only approved historical datasets, declares all parameters and required inputs, emits standardized positions/signals/orders-for-simulation, and is evaluated through common cost, funding, slippage, liquidity, and validation rules.

It does not mean arbitrary Python scripts with network/file/credential access.

### 12.2 Strategy lanes

| Lane | Status | Rules |
|---|---|---|
| Declarative YAML/JSON specs | First priority | Agents should use this by default. |
| Python strategy plugins | Later / guarded | Narrow protocol, no network/secrets/random file reads. |
| Arbitrary dynamic Python | Forbidden | No `exec`, no dynamic unreviewed code import, no hidden tools. |

### 12.3 Engine lanes

| Engine | Required | Use case |
|---|---:|---|
| Vectorized bar engine | yes | Broad agent sweeps, 1m/5m/1h strategies, fast screening. |
| Event-driven engine | yes | Fills/order-book/trades/L2/slippage-sensitive ideas. |
| Microstructure-specialized lab | later refinement | Deeper L2/TWAP/OFI research once data quality is sufficient. |

### 12.4 Required simulation layers

Every accepted/reported result must specify:

- price basis: next bar open, close, VWAP, mark, oracle, or event-driven fill;
- fee model;
- spread model;
- slippage model;
- funding model;
- liquidity/participation cap;
- missing-data policy;
- position model;
- warmup policy;
- gross and net metrics;
- cost-stress model IDs.

---

## 13. `ISSUE-R106-020` strategy/exit semantics contract

Autonomous strategy runs cannot be trusted until these semantics are explicit and tested.

| Sub-issue | Required contract | Required regression test |
|---|---|---|
| Latest-window context gating | Recent/lockbox context blocked before strategy execution. | Request using lockbox context fails pre-strategy. |
| GMM detector metadata | Fitted detectors include train window, inference window, feature version, params, artifact hash. | Missing metadata rejects manifest. |
| Fixed-holding alias identity | Aliases resolve to canonical hold rule ID or fail. | Alias and canonical ID match or reject. |
| Lower-timeframe no-hit exit pricing | If TP/SL not hit, exit at scheduled horizon using last completed lower-timeframe bar at/before horizon; missing data rejects evidence. | Synthetic no-hit fixture proves price/proof path. |
| Fit-aware train-context wiring | Any fitted feature/model trains only on prior fold data. | Fold test fails on leakage. |
| Cost-stress semantics | Base/conservative/severe costs required. | Ledger rejects base-only/gross-only metrics. |
| Static volatility-scaled barrier naming | Barrier ID encodes estimator/window/scale/timeframe/clipping/as-of rule. | Stable ID test and changed-param test. |
| Path-dynamic funding costs | Funding applied along actual position path by timestamp. | Fixture proves funding PnL changes with path. |

Close this issue only after contracts and tests exist for every row.

---

## 14. Cost model requirements

Every reportable backtest must include:

```yaml
cost_model:
  fee_model:
    base: configured_hyperliquid_fee_or_default
    conservative: base_plus_buffer
    severe: high_fee_or_taker_only
  spread_model:
    source: bbo_or_bar_proxy
  slippage_model:
    method: volume_participation_or_l2
    participation_cap: required
  funding_model:
    path_dynamic: true
  liquidity_model:
    min_volume: required
    max_participation: required
  reporting:
    gross_metrics: required
    net_base_metrics: required
    net_conservative_metrics: required
    net_severe_metrics: required
```

A strategy that only works before costs remains a failed or weak lead record, not an accepted result.

---

## 15. Ledger requirements

The append-only ledger is the canonical performance source. CSV/XLSX are generated views only.

### 15.1 Required ledger fields

| Field | Required | Notes |
|---|---:|---|
| `run_id` | yes | Immutable unique ID. |
| `experiment_id` | yes | Groups related trials. |
| `trial_index` | yes | Multiple-testing accounting. |
| `agent_or_user` | yes | Initiator. |
| `git_sha` | yes | Code provenance. |
| `strategy_id` | yes | Stable strategy ID. |
| `strategy_version` | yes | Strategy/spec version. |
| `strategy_hash` | yes | Hash of strategy spec/code. |
| `params_hash` | yes | Hash of full parameters. |
| `archive_snapshot_id` | yes | Data provenance. |
| `universe_snapshot_id` | yes | Universe provenance. |
| `feature_snapshot_id` | if used | Feature provenance. |
| `engine_id` | yes | Vectorized/event-driven engine version. |
| `cost_model_id` | yes | Base/conservative/severe assumptions. |
| `venue_scope` | yes | Hyperliquid, cross-venue, etc. |
| `instrument_count` | yes | Evaluated/traded instruments. |
| `timeframe` | yes | 1m, 5m, 1h, etc. |
| `backtest_start` | yes | Must be >= 2024-01-01 for reported runs. |
| `backtest_end` | yes | Before lockbox for ordinary runs. |
| `usable_months` | yes | Must be >= 6 for accepted/reported. |
| `lockbox_policy_id` | yes | Shows excluded months. |
| `lockbox_start` | yes | First excluded timestamp. |
| `data_coverage_min` | yes | Worst coverage. |
| `gross_return` | yes | Before costs. |
| `net_return_base` | yes | Net base costs. |
| `net_return_conservative` | yes | Net conservative costs. |
| `net_return_severe` | yes | Net severe costs. |
| `annualized_return` | yes | Net. |
| `annualized_vol` | yes | Net. |
| `sharpe` | yes | Net. |
| `sortino` | should | Useful. |
| `max_drawdown` | yes | Net. |
| `calmar` | should | Useful. |
| `turnover` | yes | Cost/capacity proxy. |
| `avg_daily_trades` | yes | Must support 5/month rule. |
| `monthly_win_loss_profile` | yes | Stability. |
| `fee_paid` | yes | Simulated fees. |
| `funding_pnl` | yes | Perp funding contribution. |
| `slippage_cost` | yes | Simulated slippage. |
| `profit_concentration_top_trades` | yes | Concentration warning/blocker. |
| `diminishing_returns_flag` | yes | Early strong / recent weak warning. |
| `pbo_score` | if computed | Overfitting diagnostic. |
| `walk_forward_pass` | yes | Boolean/status. |
| `validation_status` | yes | pass/fail/quarantine. |
| `failure_reason` | if failed | Required for failed trials. |
| `artifact_path` | yes | Run directory. |
| `artifact_sha256` | yes | Integrity. |
| `notes` | optional | Not used for ranking. |

### 15.2 Ledger rejects

Reject ledger append if:

- missing run manifest;
- missing metrics;
- missing validation status;
- missing failed-trial reason on failed run;
- missing data/universe snapshot IDs;
- missing strategy/param hashes;
- duplicate `run_id`;
- gross-only metrics;
- lockbox overlap;
- insufficient coverage;
- hand-edited spreadsheet row with no canonical artifact.

---

## 16. Lead Book requirements

The Lead Book is the official queue for serious investigation.

### 16.1 Lead states

```text
idea_only
sandbox_screened
deep_validation_requested
deep_validation_approved_by_human
deep_validation_running
deep_validation_rejected
final_test_candidate
final_test_rejected
final_test_survivor
archived_reference
```

### 16.2 Lead creation and approval

- Agents may create leads.
- Agents may recommend deep validation.
- Human inspection is required before deep validation begins.
- A lead is never a candidate by default.
- A final-test survivor is still not trade-ready.

### 16.3 Required lead fields

| Field | Required | Notes |
|---|---:|---|
| `lead_id` | yes | Stable ID. |
| `source_type` | yes | legacy run, sandbox run, external paper, manual hypothesis, rejected row, etc. |
| `source_artifact_ref` | yes | Artifact/path/doc reference. |
| `strategy_family` | yes | Momentum, funding, OI, liquidation, etc. |
| `economic_thesis` | yes | Why this could work structurally. |
| `venue_scope` | yes | Hyperliquid/default/cross-venue. |
| `universe_scope` | yes | As-of/current/sandbox/watchlist. |
| `data_window` | yes | Window used so far. |
| `data_source` | yes | Archive/source details. |
| `cost_assumptions` | yes | Fees/slippage/funding/fill. |
| `headline_metrics` | if screened | Clearly preliminary. |
| `roi` | optional | Actual measured ROI if validated. |
| `roi_projection` | optional | Mark as projection/untrusted until validated. |
| `why_interesting` | yes | Concise reason. |
| `known_blockers` | yes | Missing data, cost fragility, etc. |
| `missing_evidence` | yes | What must be proven next. |
| `required_next_validation` | yes | Next concrete test. |
| `state` | yes | Lead state. |
| `boundary_flags` | yes | Research-only invariant. |
| `diminishing_returns_flag` | yes | Warning if performance decays over time. |

### 16.4 Serious lead minimum rules

A lead should not enter serious deep validation unless it satisfies or explicitly addresses:

- no 6 losing months out of a 12-month window;
- at least 5 trades per month on average, unless strategy type justifies lower frequency and human approves;
- profit not concentrated in only a few trades;
- performance on months never seen during fitting/tuning;
- modern unseen-data failure normally fails the lead;
- if modern unseen data fails, one diagnostic fallback on pre-2024 data is allowed only if such data exists and is clearly labeled diagnostic, not evidence;
- diminishing returns from early to later test windows must be flagged as warning.

---

## 17. Worker and job-store requirements

Use dedicated workers with durable local state first.

### 17.1 Required worker model

```text
control plane / CLI / optional UI
  -> submit job
  -> SQLite WAL job store
  -> worker process claims job
  -> job writes event log and artifacts
  -> validator checks artifacts
  -> ledger/leadbook update through validated writer
```

Collectors and backtests must not run inside ASGI/operator event loop.

### 17.2 Required job tables

```text
jobs
job_events
worker_heartbeats
collector_offsets
archive_ingestion_runs
backtest_runs
ledger_append_attempts
leadbook_update_attempts
```

### 17.3 Job behavior

Every job must have:

- job ID;
- idempotency key;
- input manifest hash;
- output artifact hash;
- owner/agent ID;
- created/claimed/started/finished timestamps;
- status;
- retry count;
- failure reason;
- audit ID if part of migration;
- no-touch path compliance result.

Failed jobs are retained. Retries are explicit. Worker crashes leave resumable or safely failed state. Collector gaps become visible gap records.

---

## 18. Agent orchestration model

Use one manager/owner agent by default. Add subagents only when they materially improve capability isolation, policy isolation, prompt clarity, tool isolation, or audit trace legibility.

### 18.1 Manager agent responsibilities

The manager agent owns:

- final implementation plan for the current chunk;
- allowed/no-touch path enforcement;
- subagent routing;
- synthesis of subagent results;
- decision log updates;
- tests and acceptance proof;
- final audit note for the chunk.

The manager may delegate bounded tasks to subagents but remains accountable for the merge decision.

### 18.2 When to use subagents

Use subagents as tools when the manager should stay in control and the specialist is doing bounded work such as:

- repo cartography;
- data schema review;
- backtest semantics review;
- test generation;
- security boundary review;
- independent code audit;
- docs/control-doc consistency review;
- performance benchmark review.

Use handoff-style ownership only if a specialist must own a whole branch with different instructions, tools, or approval policy.

### 18.3 Recommended subagent roster

| Subagent | Use for | Output contract |
|---|---|---|
| Repo Cartographer | Map existing files, no-touch paths, dependency seams. | File map, risk map, recommended allowed paths. |
| Architecture Integrator | Align new v2 modules with existing repo structure. | Design diff, bounded-context placement, no rewrite warnings. |
| Data Archive Engineer | Raw/bronze/silver/gold, manifests, coverage. | Schemas, writer/reader design, tests. |
| Market Data Collector Engineer | Hyperliquid REST/WebSocket/S3, reconnects, gaps. | Collector design, failure modes, fixtures. |
| Quant Backtest Engineer | Engine logic, exits, costs, funding, fills. | Semantics, regression fixtures, metrics contract. |
| Validation Auditor | Lockbox, walk-forward, anti-overfit, trial logging. | Gate matrix, reject tests, leakage risks. |
| Security Boundary Auditor | Live/paper/runtime imports, path policy, secrets, artifact flags. | P0/P1 blockers, import tests, no-touch results. |
| Test Infrastructure Engineer | Python 3.11 env, full suite, Windows socket issue. | Validation matrix, CI commands, infra fixes. |
| Ledger/LeadBook Engineer | Append-only ledger and Lead Book state machine. | Schema, append rules, invalid row rejects. |
| Independent Chunk Auditor | Review one implemented chunk. | Pass/fail, P0/P1/P2 findings, acceptance recommendation. |

### 18.4 Subagent invocation template

```text
You are acting as subagent: <ROLE>.

Scope:
- Audit / design / implement exactly this bounded context: <CONTEXT>.
- Allowed read paths: <PATHS>.
- Allowed write paths: <PATHS>.
- No-touch paths: <PATHS>.
- Relevant contracts: <DOCS>.

Return:
1. Summary of what you inspected or changed.
2. Files touched or recommended.
3. Risks found.
4. Decisions made, with rationale.
5. Tests required or run.
6. Blockers P0/P1/P2.
7. Whether the chunk is safe to proceed.

Do not audit the entire repo. Do not propose broad rewrites. Do not touch live/paper/order/sizing/runtime paths.
```

---

## 19. Creative decision policy for agents

Agents may make creative implementation decisions when the decision is local, reversible, documented, and does not affect research integrity or safety boundaries.

### 19.1 Agents may decide without asking human

Agents may choose:

- internal class/function names;
- module organization inside an approved bounded context;
- exact fixture content;
- test helper structure;
- schema implementation details if required fields are preserved;
- local retry/backoff defaults for collectors;
- implementation details for deterministic hashing;
- performance optimizations that preserve contracts;
- whether to use DuckDB or Polars for a local read path if output parity is tested;
- whether to split a too-large chunk into smaller audit IDs.

All such decisions must be recorded in a decision log or chunk audit note.

### 19.2 Agents must escalate / require human review

Agents must not decide alone when the change:

- weakens the research-only invariant;
- touches paper/live/order/sizing/runtime paths;
- deletes or rewrites legacy evidence;
- changes lockbox length/policy;
- changes 2024+ or 6-month validation floors;
- lowers coverage below 0.98 for evidence;
- allows manual ledger edits;
- changes final-test access;
- changes no-touch registry;
- changes external data licensing or paid vendor dependency;
- adds credential handling or secrets;
- changes candidate/promotion language;
- makes a broad refactor across multiple bounded contexts.

### 19.3 Creative design rule

When blocked by an ambiguity, prefer the smallest deterministic implementation that preserves:

```text
research-only boundary
+ reproducible artifacts
+ no lockbox leakage
+ no hidden failed trials
+ as-of universe discipline
+ central ledger/Lead Book discipline
+ auditability one chunk at a time
```

If a feature can be implemented in a simple fixture-backed form first, do that before adding full provider/live-data complexity.

---

## 20. Audit marker system

Every migration/development chunk must have an audit ID:

```text
V2-AUD-<AREA>-<NUMBER>
```

Recommended areas:

| Area | Meaning |
|---|---|
| `SCOPE` | Product identity, docs, branch purpose. |
| `LEGACY` | Legacy classification, wrappers, drawer/frozen paths. |
| `LEAD` | Lead Book. |
| `ARCH` | Archive/manifests/hash/provenance. |
| `UNIV` | Universe snapshots. |
| `QUAL` | Data quality and coverage. |
| `BTDATA` | Backtest data service. |
| `BTENG` | Backtest engine. |
| `STRAT` | Strategy specs and plugin protocol. |
| `EXIT` | Exit semantics and `ISSUE-R106-020`. |
| `COST` | Fees, funding, slippage, liquidity. |
| `LEDGER` | Append-only experiment ledger. |
| `VAL` | Validation, lockbox, anti-overfit. |
| `WORKER` | Jobs, collectors, worker state. |
| `SEC` | Boundary, secrets, no-touch tests. |
| `UI` | Read-only status UI later. |
| `XVENUE` | Cross-venue adapters. |
| `FINAL` | Top-3 final hard-test workflow. |

### 20.1 Code-level marker

At package/module level for new v2 code:

```python
# V2-AUDIT-ID: V2-AUD-BTDATA-001
# V2-CONTRACTS: docs/contracts/backtest_data_service_contract.md
# V2-BOUNDARY: research_only, no_live_imports, no_lockbox_access
# V2-OWNER: backtest_data
```

Do not spam every function. Use package or module headers.

### 20.2 Chunk size limits

A single audit chunk should touch no more than:

```text
- one bounded context, or
- one contract plus its tests, or
- about 15 source files, or
- about 1,500 changed LOC,
whichever limit is reached first.
```

Split larger work.

### 20.3 Audit states

```text
planned
  -> implemented
  -> self_checked
  -> independent_agent_audited
  -> fixed_after_audit
  -> accepted
  -> operationally_verified
```

High-risk chunks cannot stop at `self_checked`.

---

## 21. Required validation tiers

| Tier | Command / evidence | Required before |
|---|---|---|
| T0 compile | `python -m compileall -q src/tradingbotsuite` | Every implementation chunk. |
| T1 contracts | `PYTHONPATH=src python -m pytest tests/contracts -q` | Contract chunks. |
| T2 v2 | `PYTHONPATH=src python -m pytest tests/v2 -q` | v2 chunks. |
| T3 targeted legacy | Relevant existing tests around touched seams. | Any wrapper/reuse change. |
| T4 full suite | `PYTHONPATH=src python -m pytest tests -q` | Before autonomous-ready. |
| T5 soak/stress | Worker/collector/backtest repeated runs. | Before long autonomous runs. |

Final validation must record:

- OS;
- Python version;
- dependency lock hash;
- git SHA;
- exact commands;
- pass/fail counts;
- skipped tests and reasons;
- open known issues.

---

## 22. Implementation roadmap to complete state

### Phase C0 — repo stabilization and baseline

**Goal:** prevent loss/drift before more work.

Tasks:

- inspect `git status`;
- classify modified/untracked files as v2 foundation, generated artifact, temporary, or delete;
- stage intentional files only;
- run T0/T1/T2;
- commit and push baseline;
- tag baseline, for example `v2-foundation-selfchecked-2026-06-21`;
- record baseline SHA in current control docs and audit index.

Exit gate:

```text
clean working tree
baseline commit pushed
v2 control docs and tests are in version control
```

### Phase C1 — validation environment and full-suite certification

**Goal:** make test evidence authoritative.

Tasks:

- pin Python 3.11.x;
- add/update `.python-version`, lockfile/constraints, validation environment docs;
- run full suite in clean environment;
- address or scope `ISSUE-R106-026`;
- make Linux CI authoritative if Windows socket issue persists;
- add async/operator resource hygiene tests where needed.

Exit gate:

```text
T4 full suite passes in authoritative clean environment
or Windows issue is formally scoped while Linux CI passes
```

### Phase C2 — control docs and no-touch authority

**Goal:** make agent navigation safe.

Tasks:

- ensure `START_HERE.md` routes to v2 control docs;
- mark old docs current/historical/obsolete;
- create/update `docs/V2_DECISION_REGISTER.md`;
- create/update `docs/V2_NO_TOUCH_PATHS.md`;
- create/update `docs/audit/V2_AUDIT_INDEX.md`;
- create docs linter for readiness language where feasible.

Exit gate:

```text
new agent can identify current authority and no-touch paths quickly
```

### Phase C3 — independent audit of current foundation

**Goal:** move beyond self-check.

Tasks:

- independent audits for archive, universe, backtest data, ledger, validation, worker, security, strategy/exit semantics;
- fix P0/P1 findings;
- record audit states.

Exit gate:

```text
no high-risk v2 foundation chunk remains self_checked only
```

### Phase C4 — close strategy/exit semantics issue

**Goal:** eliminate misleading strategy evidence paths.

Tasks:

- implement contracts and tests for `ISSUE-R106-020` rows;
- quarantine old outputs affected by ambiguous semantics;
- make ledger reject incomplete semantics.

Exit gate:

```text
ISSUE-R106-020 closed with regression tests
```

### Phase C5 — universe manager

**Goal:** dynamic Hyperliquid eligible universe.

Tasks:

- native Hyperliquid info client for `metaAndAssetCtxs` and related metadata;
- raw payload storage;
- instrument catalog;
- universe snapshot table;
- USD 5M threshold;
- HIP-3/RWA symbol support;
- as-of universe selection;
- fixture tests for non-BTC/ETH inclusion, low-volume exclusion, HIP-3 prefix handling, missing context.

Exit gate:

```text
redx universe refresh --venue hyperliquid --min-day-notional-usd 5000000
creates a snapshot and tests prove as-of behavior
```

### Phase C6 — central archive and coverage foundation

**Goal:** reliable storage before backtests.

Tasks:

- archive layout;
- raw JSONL/Zstd writer;
- Parquet writers;
- file manifest;
- ingestion run manifest;
- coverage report;
- data quality report;
- immutable archive snapshot IDs;
- CLI commands: `archive init`, `archive validate`, `archive snapshot`, `data coverage`.

Exit gate:

```text
fixture raw payload -> bronze/silver parquet -> coverage -> deterministic archive snapshot
```

### Phase C7 — collectors and backfill

**Goal:** real operational archive.

Tasks:

- recent candle bootstrap;
- WebSocket candle/trade/context/L2/BBO capture;
- funding backfill;
- official S3 loader where useful;
- reconnect/gap/downtime handling;
- worker jobs and offsets;
- storage controls and collector health reports.

Exit gate:

```text
DR3 achieved: real archive data exists, coverage is measured, gaps are visible
```

### Phase C8 — backtest data service

**Goal:** safe deterministic panels.

Tasks:

- DuckDB/Polars-backed panel loader;
- lockbox/date/coverage/as-of enforcement;
- multi-timeframe reads;
- snapshot IDs in every response manifest;
- benchmark tests;
- reject tests.

Exit gate:

```text
bad requests fail before strategy execution
valid 6+ month non-lockbox request returns deterministic panel
```

### Phase C9 — strategy specs and engines

**Goal:** comparable strategy runs.

Tasks:

- declarative spec schema;
- example strategy templates;
- vectorized engine;
- event-driven engine skeleton/first implementation;
- guarded Python plugin protocol;
- standardized run artifacts;
- no network/secret/random file access from strategies;
- fixed seeds/hashes.

Exit gate:

```text
multiple strategy specs run on same snapshot and produce comparable manifests/metrics
```

### Phase C10 — costs, metrics, validation

**Goal:** prevent false winners.

Tasks:

- gross/net metrics;
- base/conservative/severe cost stress;
- path-dynamic funding;
- slippage/participation caps;
- monthly stability;
- profit concentration;
- diminishing returns flag;
- walk-forward;
- purged/embargoed folds where relevant;
- PBO/CSCV diagnostics for broad sweeps when feasible.

Exit gate:

```text
strategies can fail due to costs, instability, concentration, or overfit warnings even with good headline returns
```

### Phase C11 — ledger and Lead Book integration

**Goal:** make autonomous output useful.

Tasks:

- append-only ledger;
- generated CSV/XLSX;
- ledger append validator;
- failed-trial logging;
- Lead Book table/state machine;
- agent lead creation;
- human review gate for deep validation;
- ROI/ROI projection fields with trust labeling.

Exit gate:

```text
backtest result updates ledger and Lead Book without implying candidate/trading readiness
```

### Phase C12 — bounded autopilot research cycle

**Goal:** autonomous checking/backtesting.

Tasks:

- scheduler;
- durable job store;
- worker pool;
- strategy/lead queue scanner;
- budget controls;
- coverage preflight;
- backtest execution;
- validation;
- ledger append;
- Lead Book update;
- blocker report;
- dry-run mode.

Exit gate:

```text
redx autopilot research-cycle --mode bounded
runs safely on eligible leads/specs and logs every result
```

### Phase C13 — operational complete release

**Goal:** declare v2 autonomous research-ready.

Tasks:

- clean branch;
- pinned validation env;
- full suite pass;
- high-risk independent audits accepted;
- known issues resolved/scoped;
- archive operational;
- coverage operational;
- lockbox enforced;
- ledger append-only;
- failed trials logged;
- bounded autopilot succeeds;
- no boundary leaks.

Exit gate:

```text
ResearchEngineDeluxe v2 is operational research-ready.
```

Forbidden release language:

```text
candidate-ready
paper-ready
live-ready
trade-ready
sizing-ready
promotion-ready
```

---

## 23. Required CLI surface

The exact CLI framework can follow the repo’s current conventions, but the final platform should expose equivalent commands:

```bash
redx v2 doctor

redx universe refresh \
  --venue hyperliquid \
  --min-day-notional-usd 5000000

redx archive init
redx archive validate
redx archive snapshot

redx archive collect \
  --venue hyperliquid \
  --datasets candles,trades,funding,asset_ctx,l2,bbo \
  --mode continuous

redx data coverage \
  --universe latest \
  --since 2024-01-01

redx leadbook scan \
  --status sandbox_screened,deep_validation_requested

redx strategy validate \
  specs/strategies/example.yaml

redx backtest run \
  --spec specs/strategies/example.yaml \
  --universe asof \
  --start 2024-01-01 \
  --end auto_non_lockbox_end \
  --exclude-lockbox

redx backtest walk-forward \
  --spec specs/strategies/example.yaml \
  --exclude-lockbox

redx ledger append \
  --run runs/<run_id>/run_manifest.json

redx autopilot research-cycle \
  --mode bounded \
  --max-jobs 10 \
  --exclude-lockbox
```

---

## 24. Required run artifact layout

Every backtest run should produce:

```text
runs/<run_id>/
  run_manifest.json
  strategy_spec.yaml
  params.json
  data_manifest.json
  validation_manifest.json
  cost_model_manifest.json
  metrics.json
  equity_curve.parquet
  daily_returns.parquet
  trades.parquet
  positions.parquet
  per_instrument_metrics.parquet
  fold_metrics.parquet
  blocker_report.md
  log.txt
```

`run_manifest.json` must include:

- git SHA;
- environment hash / lockfile ID;
- strategy ID and version;
- full parameter set;
- strategy hash;
- params hash;
- archive snapshot ID;
- universe snapshot ID;
- feature snapshot ID if used;
- date windows;
- lockbox policy;
- data coverage summary;
- cost model IDs;
- engine ID/version;
- trial group ID;
- experiment ID;
- agent/user ID;
- pass/fail status for every validation gate;
- research-only invariant.

---

## 25. Test suite additions

### 25.1 Universe

- `test_hyperliquid_universe_includes_non_btc_eth_above_5m`
- `test_hyperliquid_universe_excludes_below_5m_day_ntl_volume`
- `test_hyperliquid_universe_archives_excluded_instruments`
- `test_hyperliquid_universe_handles_hip3_prefixed_symbols`
- `test_asof_universe_does_not_use_future_volume_snapshot`

### 25.2 Archive

- `test_raw_payload_written_before_normalization`
- `test_file_manifest_has_sha256_size_rows_schema_version`
- `test_bronze_to_silver_rebuild_is_deterministic`
- `test_data_coverage_reports_missing_days`
- `test_archive_snapshot_id_changes_when_input_changes`

### 25.3 Backtest data service

- `test_reported_backtest_rejects_start_before_2024`
- `test_reported_backtest_rejects_less_than_6_months`
- `test_backtest_rejects_lockbox_overlap`
- `test_backtest_loads_only_declared_fields`
- `test_backtest_uses_asof_universe_snapshot`
- `test_warmup_bars_do_not_enter_reported_pnl`

### 25.4 Strategy / engine

- `test_declarative_strategy_validates_schema`
- `test_strategy_cannot_access_network_or_credentials`
- `test_same_run_manifest_reproduces_metrics_on_fixture_data`
- `test_funding_and_fees_affect_net_results`
- `test_missing_data_policy_is_explicit`
- `test_lower_timeframe_no_hit_exit_uses_horizon_price_or_rejects`
- `test_path_dynamic_funding_applies_to_actual_position_path`

### 25.5 Ledger

- `test_ledger_append_rejects_missing_run_manifest`
- `test_ledger_append_rejects_missing_validation_status`
- `test_ledger_records_failed_trials`
- `test_ledger_rejects_duplicate_run_id`
- `test_xlsx_export_is_generated_from_canonical_ledger`
- `test_ledger_rejects_gross_only_metrics`

### 25.6 Overfitting / validation

- `test_experiment_sweep_records_all_trials`
- `test_walk_forward_folds_are_time_ordered`
- `test_embargo_gap_excludes_boundary_rows`
- `test_leaderboard_warns_when_best_result_is_from_many_trials`
- `test_profit_concentration_warns_or_blocks`
- `test_diminishing_returns_flag_detects_recent_decay`

### 25.7 Boundary / safety

- `test_v2_has_no_live_runtime_imports`
- `test_v2_artifact_flags_use_central_boundary_policy`
- `test_no_touch_paths_are_not_modified_by_chunk`
- `test_root_contained_path_policy`
- `test_secret_redaction`
- `test_unsafe_artifact_rejection`
- `test_read_only_ui_visibility`

---

## 26. Agent manager prompt — ready to use

Use this as the main development-agent instruction.

```text
You are the manager development agent for ResearchEngineDeluxe v2.

Your goal is to finish the repository into an autonomous, research-only strategy
checking and backtesting platform. Completion means the repo can discover the
eligible Hyperliquid perp universe, collect/archive data, verify coverage, run
leakage-safe backtests from 2024 onward, log every pass/fail trial, update the
Lead Book and ledger, and report blockers.

This repo must never produce paper/live/order/sizing/runtime/promotion outputs.
Paper/live belongs outside this repo or in frozen legacy context. Do not touch
paper/live/order/sizing/runtime paths unless a human explicitly scopes a boundary
audit. Do not claim candidate-ready, trade-ready, paper-ready, live-ready,
sizing-ready, or promotion-ready status.

Follow REDX_V2_AGENTING_DEVELOPMENT_EXECUTION_BRIEF_2026_06_21.md as the current
control document. Treat CEO decisions in that document as fixed. When existing
repo docs conflict with this brief, inspect whether the older doc is current,
historical, or obsolete. Do not silently override current control docs; update
control docs intentionally and test the result.

Use a strangler migration. Preserve useful legacy subsystems. Inspect, audit,
fix, wrap, or migrate them into v2 when useful. Do not blindly delete old
strategy outputs or evidence. Legacy GUI is drawer/frozen and not an early task.

Work in bounded audit chunks. Every chunk needs an audit ID, allowed paths,
no-touch paths, expected tests, and an acceptance note. If a chunk grows beyond
one bounded context, about 15 files, or about 1,500 changed LOC, split it.

Use subagents as bounded specialists when useful, but you remain responsible for
the final implementation decision. Prefer subagents-as-tools for repo mapping,
archive design, quant semantics, validation audit, security boundary audit, and
independent chunk review. Use handoff-style ownership only if a specialist truly
needs separate tools, instructions, or approval policy.

You may make creative local decisions when they are reversible, documented, and
preserve research integrity. Escalate or stop when a decision weakens research
boundaries, touches no-touch paths, changes lockbox/coverage/date floors, deletes
legacy evidence, changes credentials, changes external data licensing, or alters
candidate/promotion language.

Development order:
1. Stabilize and commit the current v2 foundation.
2. Pin validation environment to Python 3.11.x.
3. Certify tests in an authoritative clean environment.
4. Resolve or scope ISSUE-R106-026.
5. Close ISSUE-R106-020 with contracts and regression tests.
6. Independently audit high-risk chunks.
7. Build operational universe/archive/collector/coverage flows.
8. Build backtest data service enforcing 2024+, 6 months, coverage, lockbox, and as-of universe.
9. Build declarative specs, guarded Python plugin protocol, vectorized and event-driven engines.
10. Build cost/metrics/validation gates.
11. Build append-only ledger and Lead Book integration.
12. Build bounded autopilot research cycle.
13. Declare operational research-ready only when the full checklist passes.

At the end of every chunk, report:
- audit ID;
- files changed;
- no-touch paths checked;
- decisions made;
- tests run with exact commands;
- open blockers;
- whether the chunk is implemented, self_checked, independent_agent_audited, or accepted.
```

---

## 27. Independent auditor prompt — ready to use

```text
You are independently auditing exactly one ResearchEngineDeluxe v2 migration chunk.

Audit ID:
Packet/chunk ID:
Changed files:
Declared contracts:
Declared no-touch paths:
Expected tests:
Expected artifacts:

Your job:
1. Verify the implementation matches the chunk objective.
2. Verify the research-only invariant is preserved.
3. Verify no paper/live/order/sizing/runtime path was touched or imported.
4. Verify no hidden evidence drift or legacy artifact mutation occurred.
5. Verify deterministic IDs, manifests, hashes, and snapshot references where relevant.
6. Verify lockbox/date/coverage/as-of universe gates where relevant.
7. Verify failed trials are recorded where relevant.
8. Verify tests cover acceptance criteria.
9. Identify missing tests.
10. List blockers as P0/P1/P2.
11. Produce pass/fail and acceptance recommendation.

Do not audit the whole repo. Do not propose broad rewrites. Stay inside the chunk.
```

---

## 28. Autopilot policy

Autopilot may:

- create strategy specs;
- validate specs;
- run sandbox/screening backtests;
- run walk-forward validation;
- append failed and passed trials;
- update Lead Book status;
- write blocker reports;
- ask for human review before serious/deep validation.

Autopilot may not:

- touch paper/live repos;
- write runtime config;
- place orders;
- produce sizing instructions;
- mark anything candidate-pack eligible;
- access final lockbox outside final-test approval;
- edit ledger manually;
- edit historical archive files;
- modify no-touch legacy paths;
- suppress failed trials;
- hide data gaps.

---

## 29. First autonomous-ready milestone

### M1 — Dynamic Hyperliquid 1m-bar research loop

Scope:

- Hyperliquid perps only;
- USD 5M daily notional universe rule;
- 1m candles, funding, daily asset context;
- raw + silver Parquet + manifests;
- backtest data service enforcing 2024+, 6 months, 0.98 coverage, lockbox;
- vectorized bar engine;
- 3 declarative example strategies;
- append-only ledger;
- failed trials recorded;
- no paper/live/promotion.

Acceptance:

```text
1. redx universe refresh creates a universe snapshot.
2. redx data coverage shows eligible instrument coverage.
3. redx backtest run rejects pre-2024 windows.
4. redx backtest run rejects <6 usable months.
5. redx backtest run rejects lockbox overlap.
6. redx backtest run rejects coverage below 0.98.
7. redx backtest run accepts valid 6+ month non-lockbox fixture/archive window.
8. redx ledger append writes standardized metrics.
9. failed strategy trial is logged.
10. boundary scan shows no paper/live/order/sizing/runtime/promotion artifact.
```

M1 is useful even before full L2, cross-venue adapters, or final-test workflow.

---

## 30. Final instruction to future agents

Do not redesign v2 from scratch.

Finish the platform by closing audit holes and building the operational autonomous research loop. Use this document as the controlling execution brief, current v2 roadmap as product context, and the completion audit as the blocker register.

The successful final state is not a profitable strategy. The successful final state is a clean, audited, research-only machine that can autonomously discover data, backtest ideas, reject weak strategies, preserve failed trials, and show exactly why any lead is or is not worth deeper validation.
