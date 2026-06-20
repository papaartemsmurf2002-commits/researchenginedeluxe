# WPR106-249 Sandbox Shared-Market Metric Cache

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Improve Rapid Strategy Iteration Sandbox throughput for shared-market
multi-venue smoke sweeps by computing strategy/filter/exit/holding trial
metrics once per prepared 2024+ market frame and reusing those metrics across
venue descriptors. Preserve existing result ordering, deterministic trial IDs,
ranking behavior, blocker reasons, and sandbox boundary metadata.

## Scope

- Refactor `src/tradingbotsuite/research_sandbox/fast_backtest.py` so
  `_run_prepared_market_sweep()` caches per-strategy/filter/exit/holding trial
  outcomes within the prepared market frame.
- Reuse cached trial metrics only for additional venue descriptors that share
  the same prepared market frame.
- Recompute venue-specific trial IDs and venue fields for each result row.
- Preserve descriptor-routed archive behavior where each venue descriptor has
  its own market frame and therefore its own metric computation.
- Preserve fixed-hold and target/stop exit semantics, including existing
  missing-column blockers and stop-first conservative target/stop behavior.
- Add focused tests proving shared-market multi-venue sweeps reduce gross
  return/barrier work while keeping all venue rows and unique trial IDs.
- Update sandbox contract and stage closeout docs.

## Allowed Paths

- `docs/work_packets/WPR106-249-sandbox-shared-market-metric-cache.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_SHARED_MARKET_METRIC_CACHE_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/fast_backtest.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- A shared-market sweep with multiple venues, filter variants, exit variants,
  and holding periods emits the same number of rows, unique venue-specific
  trial IDs, statuses, rankings, and blocker semantics.
- Gross-return and target/stop work is performed once per
  strategy/filter/exit/holding combination for the prepared market frame, not
  once per venue descriptor.
- Descriptor-routed archive sweeps remain venue-frame-specific and do not
  collapse distinct venue market data.
- Generated artifacts and result rows remain sandbox-only, research-only,
  non-promotable, and ineligible for candidate packs.
- Validation includes focused sandbox tests, import-boundary tests, package
  compile, and the contract baseline when the local validation environment
  allows pytest-asyncio socket setup.

## Boundary

This packet changes local sandbox sweep implementation efficiency only. It does
not alter strategy math, scoring formulas, strict validation, candidate-pack
gates, live/paper signals, sizing, order placement, runtime mode, live
configuration, provider downloads, descriptor archive loading, or promotion
readiness.

## Completion Notes

Implemented and closed on 2026-06-18. The prepared-market sweep path now caches
the first computed trial outcome for each strategy/filter/exit/holding cell
inside a prepared market frame and reuses that outcome for later venue
descriptors sharing the same market frame. Each copied row receives a fresh
deterministic venue-specific trial ID, venue, symbol, data-family fields, and
metadata.

Descriptor-routed archive sweeps still call the prepared-market sweep once per
venue descriptor and therefore keep distinct OKX, Bybit, Hyperliquid, Binance,
or local manifest market frames separate.

Focused coverage proves a two-filter, two-exit, three-holding, two-venue shared
market grid emits all 24 venue rows while running gross-return work 12 times,
once per strategy/filter/exit/holding cell instead of once per venue row. A
separate descriptor-routed test proves different venue frames keep different
returns and still compute once per descriptor frame.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 73 sandbox tests passed, 11 import-boundary tests passed,
package compileall passed, and the full contract baseline passed with 461
tests.
