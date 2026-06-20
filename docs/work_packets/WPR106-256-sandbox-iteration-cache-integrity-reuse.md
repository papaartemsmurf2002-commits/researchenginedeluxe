# WPR106-256 Sandbox Iteration Cache Integrity Reuse

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Make cached one-command sandbox iteration reuse safe for agent workflows. If
`run_sandbox_agent_iteration()` finds an existing iteration manifest, it must
verify the cached artifact references before returning the manifest as reused.

## Scope

- Validate cached iteration JSON/Parquet artifact paths before reuse.
- Validate sandbox boundary flags on cached JSON artifacts before reuse.
- Validate the referenced completed run's manifest child-artifact integrity
  before returning a cached completed iteration.
- Preserve fast idempotent reuse for untampered iteration directories.
- Add focused tests for successful reuse, tampered run-child rejection, and
  missing cached artifact rejection.
- Update sandbox contract and stage docs.

## Allowed Paths

- `docs/work_packets/WPR106-256-sandbox-iteration-cache-integrity-reuse.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_CACHE_INTEGRITY_REUSE_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/iteration.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Untampered completed sandbox iterations still return `reused_existing: true`
  on a repeated call.
- Cached completed iteration reuse fails closed when the referenced run child
  artifacts no longer match manifest integrity metadata.
- Cached iteration reuse fails closed when a referenced derived JSON/Parquet
  artifact is missing.
- Cached JSON artifacts must retain sandbox boundary flags before reuse.
- No sandbox sweeps or strict validation are executed by the cache validation
  path.
- All returned cached iteration payloads remain sandbox-only, research-only,
  non-promotable, and ineligible for candidate packs.
- Validation includes focused sandbox tests, import-boundary tests, package
  compile, and the contract baseline when the local validation environment
  allows pytest-asyncio socket setup.

## Boundary

This packet changes only cached iteration manifest reuse validation. It does
not change strategy math, trial IDs, sweep execution, archive normalization,
strict validation, candidate-pack writing, paper/live signals, sizing, order
placement, runtime mode, live configuration, provider downloads, or promotion
readiness.

## Completion Notes

Implemented and closed on 2026-06-18. Cached iteration manifest reuse now
validates referenced cached JSON/Parquet artifacts before returning
`reused_existing: true`. Cached JSON artifacts must exist and retain sandbox
boundary flags, cached Parquet artifacts must exist, and completed cached
iterations must verify the referenced run manifest's child-artifact integrity
before reuse.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "agent_iteration"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 7 iteration-focused sandbox tests passed, 84 sandbox tests
passed, 11 import-boundary tests passed, package compileall passed, and the
full contract baseline passed with 461 tests.
