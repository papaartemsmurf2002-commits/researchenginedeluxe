# WPR106-386 - Sandbox Barrier Exit Batched Windows

## Status

closed

## Objective

Reduce the audit H9 dense-window memory pressure in sandbox target/stop exit
sweeps by batching primary-bar barrier window matrices instead of allocating a
single entry-by-hold matrix for every eligible entry at once.

## Dependencies

- `RAPID_STRATEGY_SANDBOX_AUDIT.md`
- `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md`
- `docs/work_packets/WPR106-250-sandbox-vectorized-barrier-exits.md`
- `docs/work_packets/WPR106-385-sandbox-archive-sweep-sequential-descriptor-loading.md`

## Allowed paths

- `src/tradingbotsuite/research_sandbox/fast_backtest.py`
- `tests/research_sandbox/test_sandbox_foundation.py`
- `docs/work_packets/WPR106-386-sandbox-barrier-exit-batched-windows.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_BARRIER_EXIT_BATCHED_WINDOWS_REPORT.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Boundary constraints

- Preserve target-only, stop-only, and conservative target/stop exit semantics,
  including stop-first same-bar behavior and fixed-hold fallback when no
  barrier touches.
- Preserve trial IDs, ranking semantics, artifact schemas, descriptor-window
  enforcement, and sandbox boundary flags.
- This packet must not execute strict validation, write candidate packs, create
  live/paper signals, define sizing, place orders, change runtime mode, write
  live config, claim candidate evidence, or promote artifacts.
- Provider downloads, archive mutation, strategy-signal semantics, and
  candidate-pack gates remain out of scope.

## Acceptance criteria

- `_barrier_exit_prices()` processes target/stop exits in bounded entry batches.
- A focused regression test forces a tiny batch size and proves the output
  matches the unbatched/reference path for long and short target/stop variants.
- Existing barrier semantics tests continue to pass.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -k "barrier" -q
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
python -m compileall -q src\tradingbotsuite
git diff --cached --check
```

Exit evidence:

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -k "barrier" -q`
  passed with 3 tests and 198 deselected.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  passed with 223 tests.
- `python -m compileall -q src\tradingbotsuite` passed.

## Stop conditions

- Batched output differs from current barrier-exit semantics.
- The fix requires changing trial identity, artifact authority,
  strict-validation behavior, candidate-pack gates, or live/paper boundaries.
