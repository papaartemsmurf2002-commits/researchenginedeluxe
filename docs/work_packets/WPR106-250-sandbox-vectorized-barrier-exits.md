# WPR106-250 Sandbox Vectorized Barrier Exits

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Improve Rapid Strategy Iteration Sandbox throughput for target-only, stop-only,
and conservative target/stop exit sweeps by replacing the per-trade/per-bar
barrier scan with a vectorized primary-bar window calculation. Preserve
existing fixed-hold behavior, target/stop semantics, deterministic trial IDs,
ranking behavior, blocker reasons, and sandbox boundary metadata.

## Scope

- Refactor `src/tradingbotsuite/research_sandbox/fast_backtest.py` so
  `_barrier_exit_prices()` computes barrier hit windows with NumPy arrays
  instead of nested Python loops.
- Preserve long and short side semantics for target-only, stop-only, and
  conservative target/stop exits.
- Preserve conservative target/stop same-bar ambiguity as stop-first.
- Preserve fallback to fixed hold close when no target/stop barrier is hit.
- Preserve explicit blocked rows when target/stop exits lack high/low columns.
- Add focused tests covering vectorized parity for long and short exits,
  same-bar stop-first behavior, and fallback/no-hit behavior.
- Update sandbox contract and stage closeout docs.

## Allowed Paths

- `docs/work_packets/WPR106-250-sandbox-vectorized-barrier-exits.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_VECTORIZED_BARRIER_EXITS_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/fast_backtest.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Target-only, stop-only, and conservative target/stop exits produce the same
  prices and trial metrics as the prior loop semantics for long and short
  trades.
- Conservative target/stop still resolves same-bar target/stop ambiguity as
  stop-first.
- No-hit target/stop exits still fall back to the fixed-hold close.
- Missing high/low columns still produce explicit blocked rows.
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

Implemented and closed on 2026-06-18. The sandbox target/stop exit path now
builds a NumPy primary-bar window for each trial and resolves barrier hits with
vectorized array operations. Target-only, stop-only, and conservative
target/stop exits no longer scan every trade and bar through nested Python
loops.

The vectorized path preserves long/short target and stop math, no-hit fallback
to the fixed-hold close, and conservative target/stop stop-first behavior when
both barriers touch on the same bar.

Focused coverage compares vectorized barrier prices against a local reference
loop for long and short target-only, stop-only, and target/stop profiles. A
separate test locks same-bar stop-first behavior and no-hit fallback. Existing
sweep-level tests continue to cover blocked OHLC behavior, deterministic trial
IDs, ranking, and sandbox boundaries.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 75 sandbox tests passed, 11 import-boundary tests passed,
package compileall passed, and the full contract baseline passed with 461
tests.
