# WPR106-248 Sandbox Sweep Market Array Cache

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Improve Rapid Strategy Iteration Sandbox sweep throughput by preparing market
numeric arrays once per already-filtered market frame and reusing them across
venue, holding-period, exit-variant, and filter-variant trials. Preserve
existing trial identity, metrics, ranking behavior, blocker reasons, and
sandbox boundary metadata.

## Scope

- Refactor `src/tradingbotsuite/research_sandbox/fast_backtest.py` so close,
  optional high/low, and entry-date arrays are prepared once per prepared
  market frame after the 2024+ window filter and blueprint signal
  materialization.
- Pass the prepared arrays into trial execution and target/stop exit
  calculations instead of converting market columns inside every trial.
- Preserve fixed-hold, target-only, stop-only, and conservative target/stop
  semantics, including stop-first same-bar ambiguity.
- Preserve explicit blocked rows for empty market windows and missing
  signal/filter/OHLC columns.
- Add focused tests proving prepared arrays are reused across a broad
  holding/exit/filter/venue grid while outputs remain unchanged.
- Update sandbox contract and stage closeout docs.

## Allowed Paths

- `docs/work_packets/WPR106-248-sandbox-sweep-market-array-cache.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_SWEEP_MARKET_ARRAY_CACHE_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/fast_backtest.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Sweeps with multiple venues, holding periods, exit variants, and filter
  variants produce the same trial IDs, statuses, trade counts, scores, rankings,
  active-day counts, and blocker reasons as the prior behavior.
- Market close/high/low/date arrays are prepared once per prepared market frame,
  not once per individual trial.
- Target/stop exits continue to require high/low columns and fail closed with
  explicit blockers when those columns are absent.
- Generated artifacts and result rows remain sandbox-only, research-only,
  non-promotable, and ineligible for candidate packs.
- Validation includes focused sandbox tests, import-boundary tests, package
  compile, and the contract baseline when the local validation environment
  allows pytest-asyncio socket setup.

## Boundary

This packet changes local sandbox sweep implementation efficiency only. It does
not alter strategy math, scoring formulas, strict validation, candidate-pack
gates, live/paper signals, sizing, order placement, runtime mode, live
configuration, provider downloads, or promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. The prepared-market sweep path now builds
close, optional high/low, and entry-date arrays once per prepared 2024+ market
frame and reuses them across venue, filter, exit, and holding-period trials.
Fixed-hold trials use the cached close array; target/stop trials use cached
high/low arrays when those columns exist and still block with explicit OHLC
reasons when they do not.

Focused coverage proves a two-filter, two-exit, three-holding, two-venue grid
produces all 24 trial rows while calling `_prepared_market_arrays()` only once
for the prepared market frame. Existing sandbox tests continue to cover trial
IDs, active-day counts, statuses, rankings, blocked reasons, target/stop
semantics, and artifact boundaries.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 71 sandbox tests passed, 11 import-boundary tests passed,
package compileall passed, and the full contract baseline passed with 461
tests. The first full-contract attempt reached 460 passed tests before the
known local Windows pytest-asyncio `WinError 10055` socket setup failure; an
immediate rerun passed cleanly.
