# WPR106-282 Sandbox Descriptor Source Metric Reuse

Status: closed
Owner: Codex Research Agent
Created: 2026-06-19

## Objective

Speed up archive-backed sandbox sweeps by reusing trial metric work across
venue descriptors that point to the same normalized market source, while still
keeping distinct descriptor sources and venue-specific trial IDs separate.

## Scope

- Group descriptor-routed sandbox sweeps by reusable market source when
  descriptors share a `shared_market_data_path`, identical `data_path`, or the
  same in-memory market frame object.
- Run one prepared market sweep per reusable source group and reuse the existing
  per-market trial metric cache across the grouped venues.
- Preserve venue-specific trial IDs, venue fields, market-source metadata, and
  global ranking semantics.
- Preserve separate metric computation for descriptors with different source
  paths or different market frame objects.
- Add focused tests proving same-source descriptors reuse gross-return work and
  distinct descriptor sources remain separate.
- Update the sandbox research contract, active index, stage ledger, and stage
  report.

## Allowed Paths

- `docs/work_packets/WPR106-282-sandbox-descriptor-source-metric-reuse.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_DESCRIPTOR_SOURCE_METRIC_REUSE_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/fast_backtest.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Descriptor-routed sweeps reuse metric work when multiple descriptors share
  the same source path or shared market-data path.
- Venue-specific trial IDs and market-source descriptor metadata remain
  distinct for reused results.
- Descriptors with distinct market sources still compute separate metrics.
- Existing shared-market sweep behavior, descriptor-routed ranking, and result
  contracts remain stable.
- No candidate packs, paper/live signals, sizing, order placement, strict
  validation execution, provider downloads, source artifact mutation, runtime
  mode changes, or live configuration writes are introduced.
- Validation includes focused sandbox tests, full sandbox tests, package
  compile, import-boundary tests, and the contract baseline when the local
  environment allows it.

## Boundary

This packet only changes research-sandbox metric reuse inside existing
archive-backed sweeps. It does not change backtest assumptions, execute strict
validation, write candidate artifacts, create paper/live signals, define
sizing, place orders, mutate runtime mode, write live configuration, mutate
source archive files, download provider data, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-19. Descriptor-routed sweeps now group venue
descriptors by shared market-data path, identical descriptor `data_path`, or
the same in-memory market frame object. The existing per-market metric cache is
reused inside each source group while venue-specific trial IDs and
market-source metadata remain distinct.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "shared_market_sweep_reuses_trial_metrics or descriptor_routed_sweep"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 3 focused cache tests passed, 116 sandbox tests passed, package
compileall passed, 11 import-boundary tests passed, and 461 contract tests
passed.
