# V2 Discussed Changes Final Audit And Remaining Roadmap

Date: 2026-06-29
Packet: `docs/work_packets/WPR106-568-discussed-systems-final-audit-roadmap.md`
Audited work: PR5 follow-up, PR6, and WPR106-567 autonomous research systems layer

## Boundary

This is a docs-only final audit. It does not change source behavior, tests,
generated evidence, ledgers, Lead Book rows, archive data, live/runtime files,
or research outputs.

The trade-frequency and losing-month section from the post-PR6 recommendation
report remains ignored per owner instruction.

## Final Audit Verdict

Most discussed changes have been implemented successfully.

The repo now has the required first-pass systems for:

- PR5 math fixes and policy corrections;
- PR6 fast lane, columnar data path, strict spread mode, part-backed ledgers,
  OF Parquet parts, and bounded Bybit/OKX pagination helpers;
- WPR106-567 archive inventory, data-requirement resolver, `DataGapRequest`,
  archive-first agent rules, feature-store catalog, collector templates,
  artifact-light modes, fast-lane audit/replay tooling, benchmark scaffolding,
  ledger part batching, and streaming OF improvements.

No source-level blocker was found in this audit. Focused validation passed.

The work is not fully finished as a platform, because the remaining needs are
evidence and hardening:

- real large-panel benchmark evidence before any broad speedup claim;
- broader fast/reference parity coverage as new strategy families are added;
- end-to-end archive-first workflow smoke across resolver, fast run, reference
  audit, full replay, and ledger/feature discovery;
- stronger handling for very large non-monotonic OF sources, where correctness
  is preserved by fallback but memory scaling can still be improved;
- final review/commit/PR hygiene for the uncommitted WPR106-567 work.

## What Is Complete

| System | Audit Result |
| --- | --- |
| Account-notional capacity math | Implemented and covered. |
| 5 bps spread fallback and strict spread policy | Implemented and covered. |
| Monthly validation folds | Implemented and covered. |
| Funding zero handling and `next_bar_open` causality | Implemented and covered. |
| Fast vectorized engine lane | Implemented with fixture parity coverage. |
| Columnar backtest data loading | Implemented. |
| Cost stress reuse | Implemented. |
| Worker stale claim / atomic claim | Already implemented in prior work. |
| Part-backed ledger storage | Implemented. |
| Ledger part batching | Implemented in WPR106-567. |
| OF Parquet part output | Implemented. |
| Streaming OF improvements | Implemented for monotonic sorted-bucket paths, with fallback remaining for non-monotonic inputs. |
| Bybit/OKX bounded pagination helpers | Implemented without live fetches in tests. |
| Archive inventory | Implemented with CLI and real summary smoke. |
| Strategy data-requirement resolver | Implemented with `DataGapRequest` output. |
| Archive-first agent docs | Implemented in `AGENTS.md` and `docs/RESEARCH_AGENT_QUICKSTART.md`. |
| Feature-store catalog | Implemented. |
| Collector gap templates | Implemented and fail closed without resolver proof. |
| Artifact modes | Implemented: `full`, `summary`, `metrics_only`. |
| Fast-lane audit and replay tooling | Implemented. |
| Benchmark scaffolding | Implemented; broad real benchmark evidence still remains. |

## Validation Re-run By This Audit

```powershell
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_archive_inventory_phase80.py tests\v2\test_data_requirement_resolver_phase80.py tests\v2\test_feature_store_catalog_phase80.py tests\v2\test_collector_gap_template_phase80.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_fast_lane_audit_phase80.py tests\v2\test_backtest_benchmark_phase80.py tests\v2\test_backtest_engine_phase11.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_ledger_phase13.py tests\v2\test_of_style_materialization_phase78.py tests\v2\test_autonomy_agent_context_phase79.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
$env:PYTHONPATH='src'; py -3.11 -m tradingbotsuite.v2.cli.main archive-inventory --summary
git diff --check
```

Results:

- compileall passed;
- archive/resolver/feature-store/collector tests passed: `21`;
- fast-lane/benchmark/backtest tests passed: `27`;
- ledger/OF/autonomy tests passed: `26`;
- contracts passed: `463`;
- archive-inventory summary returned `492` records, `8,633,194` rows, two
  venues, accepted-research records, and research-only boundary flags;
- `git diff --check` passed with existing LF-to-CRLF warnings only.

Additional resolver CLI smoke:

```powershell
$env:PYTHONPATH='src'; py -3.11 -m tradingbotsuite.v2.cli.main archive-inventory --missing-for-strategy configs\strategies\wpr106_556\accepted\first_passing_atlas_strategy.json --instrument-id binance:perp:BTCUSDT --start-ts 2024-01-01T00:00:00Z --end-ts 2024-02-01T00:00:00Z --artifact-mode metrics_only --prefer-fast-lane --require-reference-audit
```

Result: exited nonzero because `ready=false`, which is expected for this
insufficient accepted-research window. The command emitted bounded
`DataGapRequest` objects and preserved research-only boundary flags.

## Remaining Roadmap

### 1. End-To-End Archive-First Workflow Smoke

Goal:

Prove the full post-PR6/WPR106-567 workflow works as one system, not just as
individual modules.

Required flow:

```text
strategy spec
-> archive inventory
-> data-requirement resolver
-> existing archive refs or bounded DataGapRequest
-> columnar data load
-> fast metrics_only run
-> sampled reference audit
-> full-artifact replay plan
-> full replay verification
-> ledger append/read/export on batched parts
-> feature-store discovery
```

Acceptance:

- one fixture-only flow;
- one real local archive flow using already available data;
- no data collection;
- no generated evidence rewrite outside the packet output root;
- final report states whether speedup is unclaimed or supported.

### 2. Real Benchmark Evidence

Goal:

Use the new benchmark scaffolding on realistic local panels before any broad
speed claim.

Benchmark tiers:

- smoke: tiny fixture;
- single-symbol 1m multi-month panel;
- multi-symbol 1m panel;
- parameter-sweep style repeated run;
- OF-derived feature panel when available.

Report:

- reference runtime;
- fast runtime;
- speedup ratio;
- data load time;
- artifact write time;
- memory peak;
- parity status;
- benchmark tier and scope.

Acceptance:

- speedup claims remain false unless complete measured evidence exists;
- any speedup statement includes panel size, instrument count, timeframe,
  artifact mode, and hardware/runtime context.

### 3. Fast-Lane Parity Expansion

Goal:

Broaden parity beyond current fixtures as strategy families expand.

Cover:

- cross-sectional rank strategies;
- funding carry;
- momentum/reversion;
- volatility filters;
- multi-instrument panels;
- `close`, `mark`, `oracle`, and `next_bar_open` price bases;
- strict and lenient spread policies;
- `full`, `summary`, and `metrics_only` artifact modes.

Acceptance:

- new strategy family templates require reference+fast parity before routine
  fast sweeps;
- parity failures block leaderboard acceptance until investigated.

### 4. OF Streaming Hardening

Goal:

Remove the remaining memory-heavy fallback for very large non-monotonic
trade/book sources.

Options:

- bounded spill-to-disk bucket sort;
- chunked merge-sort by bucket;
- partitioned source-file processing;
- process-pool by source file with stable output ordering.

Acceptance:

- large non-monotonic source can materialize without holding all feature rows
  or all buckets in memory;
- output hashes remain deterministic;
- feature-store catalog discovers the output.

### 5. Final Review, Commit, And PR Hygiene

Goal:

Turn the uncommitted WPR106-567 systems layer and this audit into a clean,
reviewable change set.

Required:

- inspect current dirty worktree;
- ensure no generated evidence or archive data is accidentally included;
- run final focused validation;
- optionally run full `tests\v2 -q` if time allows;
- stage only intended source/docs/tests;
- commit and open PR if requested by the owner.

## Single Goal For The Implementation Agent

```text
Finish the post-PR6 autonomous research systems closure layer.

Most core systems are implemented. Do not redo PR5, PR6, or WPR106-567. Your
task is to prove and harden the whole workflow end to end: archive-first
strategy resolution, existing-data use, fast metrics-only execution, sampled
reference audit, full replay verification, batched ledger handling, feature
catalog discovery, and realistic benchmark evidence.

Do not collect data, add venues by default, rewrite generated evidence, weaken
math fixes, remove the reference engine, or touch live/paper/order/sizing/
promotion/candidate/runtime/secret/local-state paths.

If a strategy cannot be tested, emit bounded DataGapRequest objects. If it can
be tested, use existing archive refs. If a result is promising or suspicious,
produce a full replay plan and verify the replay before treating it as audit
evidence. Do not claim speedup without complete benchmark observations.
```

## Suggested Next Packet

```text
docs/work_packets/WPR106-569-v2-autonomous-research-end-to-end-systems-closure.md
```

Recommended scope:

- end-to-end archive-first workflow smoke;
- real local archive benchmark report;
- parity expansion matrix for current strategy families;
- OF non-monotonic streaming hardening if benchmark/workflow evidence shows it
  is now the bottleneck;
- final WPR106-567 review/commit readiness.
