# WPR106-385 - Sandbox Archive Sweep Sequential Descriptor Loading

## Status

closed

## Objective

Reduce the audit H9 full-memory pressure in descriptor-routed sandbox archive
sweeps by loading and executing descriptor market frames sequentially instead
of materializing every descriptor frame into one in-memory dictionary before
execution.

## Dependencies

- `RAPID_STRATEGY_SANDBOX_AUDIT.md`
- `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md`
- `docs/work_packets/WPR106-362-post-audit-sandbox-safety-coherence.md`
- `docs/work_packets/WPR106-384-sandbox-package-root-lazy-exports.md`

## Allowed paths

- `src/tradingbotsuite/research_sandbox/runner.py`
- `src/tradingbotsuite/research_sandbox/fast_backtest.py`
- `tests/research_sandbox/test_sandbox_foundation.py`
- `docs/work_packets/WPR106-385-sandbox-archive-sweep-sequential-descriptor-loading.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARCHIVE_SWEEP_SEQUENTIAL_DESCRIPTOR_LOADING_REPORT.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Boundary constraints

- Preserve trial IDs, ranking semantics, descriptor-window enforcement, artifact
  schemas, and boundary flags.
- Shared `--market-data` sweeps may still use one shared loaded frame for all
  descriptors.
- Descriptor-routed sweeps must not execute strict validation, write candidate
  packs, create live/paper signals, define sizing, place orders, change runtime
  mode, write live config, claim candidate evidence, or promote artifacts.
- Provider downloads and archive mutation remain out of scope.

## Acceptance criteria

- Descriptor-routed `run_sandbox_archive_sweep` loads descriptor frames one
  descriptor at a time by default.
- Global ranking/truncation is applied once after all descriptor results are
  collected.
- Existing preloaded market-data cache behavior still avoids rereading cached
  frames.
- A regression test proves descriptor-routed archive sweep uses per-descriptor
  loading and matches direct multi-frame sweep results.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -k "archive_sweep" -q
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
python -m compileall -q src\tradingbotsuite
git diff --cached --check
```

Exit evidence:

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -k "archive_sweep" -q`
  passed with 4 tests and 196 deselected.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  passed with 222 tests.
- `python -m compileall -q src\tradingbotsuite` passed.

## Stop conditions

- Sequential loading changes trial identities or ranking order.
- Cache reuse regressions require rereading preloaded frames.
- The fix requires changing artifact authority, strict-validation behavior, or
  candidate-pack gates.
