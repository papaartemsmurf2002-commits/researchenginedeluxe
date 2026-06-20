# WPR106-247 Sandbox Sweep Mask Cache

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Improve Rapid Strategy Iteration Sandbox sweep throughput by caching
strategy/filter signal masks across holding-period and exit-variant trials for
each prepared market frame. The change should preserve existing trial IDs,
metrics, ranking behavior, blocker reasons, and sandbox boundary metadata.

## Scope

- Refactor `src/tradingbotsuite/research_sandbox/fast_backtest.py` so
  `_signal_mask()` is computed once per strategy/filter variant per prepared
  market frame when required columns exist.
- Reuse the cached mask across all holding periods and exit variants for that
  strategy/filter pair.
- Preserve existing missing-column and empty-window blocked behavior.
- Keep target/stop high/low checks per exit variant.
- Add focused tests proving result parity and that signal masks are not
  recomputed per holding/exit combination.
- Update sandbox contract and stage closeout docs.

## Allowed Paths

- `docs/work_packets/WPR106-247-sandbox-sweep-mask-cache.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_SWEEP_MASK_CACHE_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/fast_backtest.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Sweeps with multiple holding periods and exit variants produce the same
  trial IDs, statuses, trade counts, scores, and rankings as the uncached
  behavior.
- `_signal_mask()` is invoked once per strategy/filter variant per prepared
  market frame, not once per holding/exit trial.
- Missing signal/filter columns and missing OHLC columns still produce blocked
  rows with explicit reasons.
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

Implemented and closed on 2026-06-18. The prepared-market sweep path now caches
each strategy/filter signal mask once per market frame and reuses it across all
venues, exit variants, and holding periods for that prepared frame. Missing
signal/filter inputs still skip cache construction and flow through the
existing blocked-result path; high/low requirements still remain per exit
variant.

Focused coverage proves a two-filter, two-exit, three-holding, two-venue grid
produces all 24 trial rows while calling `_signal_mask()` only twice, once per
filter variant. Existing sandbox parity tests continue to cover trial IDs,
statuses, ranking, blocked reasons, and artifact boundaries.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 70 sandbox tests passed, 11 import-boundary tests passed,
package compileall passed, and the full contract baseline passed with 461
tests. The first full-contract attempt reached 460 passed tests before the
known local Windows pytest-asyncio `WinError 10055` socket setup failure; an
immediate rerun passed cleanly.
