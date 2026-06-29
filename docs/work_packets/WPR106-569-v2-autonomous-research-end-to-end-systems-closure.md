# WPR106-569 - V2 Autonomous Research End-To-End Systems Closure

Status: self_checked
Owner: Codex Research Agent
Date opened: 2026-06-29

## Scope

Finish the post-PR6 autonomous research systems closure layer without
rebuilding PR5, PR6, or WPR106-567. This packet proves the newly added archive
inventory, resolver, fast-lane, replay, benchmark, ledger batching, and
feature-store catalog surfaces as an integrated archive-first workflow.

The packet may add small orchestration/reporting helpers, focused tests, and a
packet-scoped systems-closure report. It may harden OF-style non-monotonic
streaming only if the change stays local to the existing materializer and keeps
deterministic output hashes.

This packet must not collect data, add venues proactively, rewrite existing
generated evidence, compact existing ledgers, update Lead Book rows, alter
candidate-pack/promotion/live/runtime behavior, weaken the reference-engine
authority, or make a broad speedup claim without complete measured benchmark
evidence.

## Allowed paths

- `docs/work_packets/WPR106-569-v2-autonomous-research-end-to-end-systems-closure.md`
- `docs/stage_reports/STAGE_R106_WPR106_569_SYSTEMS_CLOSURE_REPORT.md`
- `docs/hand_offs/WPR106-569-systems-closure-handoff.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/v2/archive_inventory/**`
- `src/tradingbotsuite/v2/backtest_engine/**`
- `src/tradingbotsuite/v2/data_sources/of_style_materialization.py`
- `src/tradingbotsuite/v2/feature_store/**`
- `src/tradingbotsuite/v2/ledger/**`
- `src/tradingbotsuite/v2/cli/main.py`
- `tests/v2/test_archive_inventory_phase80.py`
- `tests/v2/test_backtest_benchmark_phase80.py`
- `tests/v2/test_fast_lane_audit_phase80.py`
- `tests/v2/test_of_style_materialization_phase78.py`
- `tests/v2/test_ledger_phase13.py`
- `tests/v2/test_systems_closure_phase81.py`
- `data/research/wpr106_569_systems_closure/**`

## No-touch review

- No live, paper, order-placement, sizing, promotion, candidate-pack,
  runtime-mode, secret, or local-state paths are in scope.
- Existing generated evidence, archive data, central collection ledgers, and
  Lead Book data must not be rewritten. Packet-scoped generated proof, if
  needed, must stay under `data/research/wpr106_569_systems_closure/**`.
- Archive-first workflow smokes must use existing archive refs or emit bounded
  `DataGapRequest` objects. They must not fetch venue data or materialize wider
  source archives.
- Benchmark output remains evidence, not a speedup claim. `speedup_claimed`
  must stay false unless reports include complete reference runtime, fast
  runtime, data-load time, artifact-write time, memory peak, parity status,
  artifact mode, panel size, instrument count, timeframe, and runtime context.
- Fast-lane output is triage until sampled reference audit and full replay
  verification pass.

## Implementation plan

1. Inspect the WPR106-567 dirty worktree and current CLI/API shape without
   reverting existing uncommitted work.
2. Add a focused end-to-end workflow smoke that exercises strategy spec,
   archive inventory/resolver, existing refs or gap requests, columnar data
   load, fast metrics-only run, sampled reference audit, full replay plan,
   full replay verification, batched ledger read/write/export, and
   feature-store discovery.
3. Run real local benchmark commands over fixture/smoke and larger local
   archive panels, recording measured observations under the packet output
   root and avoiding speedup claims unless the evidence is complete.
4. Expand fast/reference parity tests across current strategy-family and
   artifact-mode surfaces where the existing engine supports them.
5. Harden very large non-monotonic OF streaming if a small, deterministic local
   implementation can remove the memory-heavy fallback without changing
   feature semantics.
6. Publish a concise systems-closure report and handoff that records evidence,
   remaining caveats, validation, and commit/PR hygiene status.

## Validation target

```powershell
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_systems_closure_phase81.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_archive_inventory_phase80.py tests\v2\test_fast_lane_audit_phase80.py tests\v2\test_backtest_benchmark_phase80.py tests\v2\test_ledger_phase13.py tests\v2\test_of_style_materialization_phase78.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
git diff --check
```

Broaden to `tests\v2 -q` if source changes cross shared contracts more than
expected.

## Completion notes

Implemented as a systems-closure packet, not a rebuild. The packet adds a
focused archive-first workflow smoke, a current-family fast/reference parity
matrix, and deterministic bounded spill/merge aggregation for non-monotonic
OF-style bucket materialization.

Local inventory and feature-catalog probes succeeded against the existing
central archive, but direct larger-panel benchmark execution remains blocked:
the benchmark runner requires v2 file-manifest and archive-snapshot records,
and `data/research/central_market_history` currently has zero such snapshot
records. `docs/KNOWN_ISSUES.md` records this as ISSUE-R106-035. No speedup
claim was made.

Validation completed:

```powershell
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_of_style_materialization_phase78.py tests\v2\test_systems_closure_phase81.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
$env:PYTHONPATH='src'; py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_archive_inventory_phase80.py tests\v2\test_data_requirement_resolver_phase80.py tests\v2\test_feature_store_catalog_phase80.py tests\v2\test_collector_gap_template_phase80.py tests\v2\test_fast_lane_audit_phase80.py tests\v2\test_backtest_benchmark_phase80.py tests\v2\test_backtest_engine_phase11.py tests\v2\test_ledger_phase13.py tests\v2\test_of_style_materialization_phase78.py tests\v2\test_systems_closure_phase81.py tests\v2\test_autonomy_agent_context_phase79.py tests\v2\archive\test_archive_phase4.py tests\v2\test_data_quality_phase6.py -q
git diff --check
```
