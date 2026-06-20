# WPR106-301 Sandbox Run Source Container Metadata

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Propagate bounded ZIP/TAR container member-selection diagnostics from loaded
archive-backed market frames into sandbox sweep `market_source` metadata,
evidence-request source context, and strict-validation request bundle
convenience fields.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-301-sandbox-run-source-container-metadata.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_RUN_SOURCE_CONTAINER_METADATA_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/runner.py`
- `src/tradingbotsuite/research_sandbox/validation_bundle.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, and
  promotion-ready false.
- Do not execute strict validation, write candidate packs, create paper/live
  signals, define sizing, place orders, change runtime mode, write live
  configuration, download provider data, mutate source archive files, extract
  archive members to disk, or claim promotion readiness.
- Preserve the 2024+ sandbox date floor, source-integrity checks, archive
  routing, trial identity, ranking math, blocker semantics, and evidence
  request selection.
- Treat container metadata as diagnostics only; it must not alter trial
  estimates, sweep metrics, rankings, eligibility, or request counts.
- Keep projected metadata bounded and deterministic for compact agent handoff
  artifacts.

## Plan

1. Add a runner helper that extracts bounded container diagnostics from loaded
   market-frame normalization metadata.
2. Attach those diagnostics to descriptor-routed archive sweep `market_source`
   payloads before fixed-hold sweep execution.
3. Project the same source container diagnostics as stable convenience fields
   in strict-validation request bundle descriptor rows.
4. Add focused tests proving run manifests, ranking metadata, evidence-request
   source context, bundle JSON, and bundle Parquet rows preserve the fields.
5. Update sandbox contract, active index, stage ledger, and stage report.
6. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Completion Notes

Implemented and closed on 2026-06-19. Archive-backed sandbox sweeps now attach
bounded ZIP/TAR member-selection diagnostics from loaded market-frame
normalization metadata to each descriptor `market_source` payload. The payload
is preserved through result metadata, run manifests, ranking Parquet metadata,
evidence-request `source_trial_context`, and descriptor-only strict-validation
request bundle JSON/Parquet rows.

This is provenance-only. Trial IDs, market routing, ranking math, blocker
semantics, eligibility flags, evidence-request selection, source archive files,
and strict-validation behavior are unchanged.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "archive_sweep_preserves_container_metadata"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 1 focused archive-sweep container provenance test passed, 164
sandbox tests passed, package compileall passed, 11 import-boundary tests
passed, and 461 contract tests passed.
