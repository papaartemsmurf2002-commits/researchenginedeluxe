# WPR106-387 - Sandbox Proxy Signal Column Deduping

## Status

closed

## Objective

Reduce the audit H9 proxy-signal memory pressure by letting high-throughput
sandbox execution and preflight materialize identical blueprint proxy signals
once per signal definition instead of adding one generated DataFrame column per
strategy row.

## Dependencies

- `RAPID_STRATEGY_SANDBOX_AUDIT.md`
- `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md`
- `docs/work_packets/WPR106-362-post-audit-sandbox-safety-coherence.md`
- `docs/work_packets/WPR106-386-sandbox-barrier-exit-batched-windows.md`

## Allowed paths

- `src/tradingbotsuite/research_sandbox/strategy_blueprints.py`
- `src/tradingbotsuite/research_sandbox/fast_backtest.py`
- `src/tradingbotsuite/research_sandbox/preflight.py`
- `tests/research_sandbox/test_sandbox_foundation.py`
- `docs/work_packets/WPR106-387-sandbox-proxy-signal-column-deduping.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_PROXY_SIGNAL_COLUMN_DEDUPING_REPORT.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Boundary constraints

- Preserve strategy descriptors, original `signal_column` values, trial IDs,
  ranking semantics, artifact schemas, and sandbox boundary flags.
- Dedupe only blueprint proxy signal materialization for identical
  decision-affecting signal definitions. Direct/manual precomputed signal
  columns must keep existing behavior.
- Do not relabel proxy results as real strategy evidence.
- This packet must not execute strict validation, write candidate packs, create
  live/paper signals, define sizing, place orders, change runtime mode, write
  live config, claim candidate evidence, or promote artifacts.

## Acceptance criteria

- High-throughput sandbox sweeps and compatibility preflight can run strategies
  whose blueprint proxy columns have been deduped through DataFrame alias
  metadata.
- Identical blueprint/side/signal-parameter strategies share one materialized
  signal column and one mask-cache key.
- Focused tests prove duplicate proxy rows remain runnable and original
  strategy descriptors/trial identities are preserved.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -k "blueprint or signal_mask or preflight" -q
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
python -m compileall -q src\tradingbotsuite
git diff --cached --check
```

Exit evidence:

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -k "blueprint or signal_mask or preflight" -q`
  passed with 18 tests and 186 deselected.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  passed with 226 tests.
- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  passed with 462 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`
  passed with 26 tests.
- `$env:PYTHONPATH='src'; python -m pytest -q` passed with 1896 tests,
  1 skipped test, and 1 XGBoost device warning.

## Stop conditions

- Dedupe changes trial IDs, strategy payload identity, ranking semantics, or
  direct/manual signal-column behavior.
- The fix requires weakening proxy-only labeling, strict-validation boundaries,
  candidate-pack gates, or live/paper safety boundaries.
