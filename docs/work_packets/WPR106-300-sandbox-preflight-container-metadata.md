# WPR106-300 Sandbox Preflight Container Metadata

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Expose bounded ZIP/TAR container member-selection diagnostics as first-class
compatibility preflight row fields so agents can triage archive-backed sandbox
runnability without parsing nested normalization JSON.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-300-sandbox-preflight-container-metadata.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_PREFLIGHT_CONTAINER_METADATA_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/preflight.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, and
  promotion-ready false.
- Do not execute strict validation, write candidate packs, create paper/live
  signals, define sizing, place orders, change runtime mode, write live
  configuration, download provider data, mutate source archive files, extract
  archive members to disk, or claim promotion readiness.
- Preserve the 2024+ sandbox date floor, completed-row normalization,
  descriptor readiness blockers, source-integrity checks, trial identity, and
  preflight runnable/blocked semantics.
- Treat container metadata as diagnostics only; it must not alter trial
  estimates, blocker reasons, rankings, sweep metrics, or evidence requests.
- Keep metadata bounded and deterministic for compact agent reports.

## Plan

1. Add a preflight row helper that extracts bounded container member metadata
   from `venue_metadata["normalization"]`.
2. Project container summary fields into each compatibility preflight row.
3. Add focused tests for preflight JSON and Parquet rows over local ZIP member
   containers.
4. Update sandbox contract, active index, stage ledger, and stage report.
5. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Completion Notes

Implemented and closed on 2026-06-19. Compatibility preflight rows now expose
bounded container member-selection diagnostics as first-class JSON/Parquet
fields while keeping trial estimates, blocker reasons, ranking inputs, sweep
metrics, and evidence requests unchanged.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "preflight_records_container_member_metadata"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 1 focused preflight container-metadata test passed, 163 sandbox
tests passed, package compileall passed, 11 import-boundary tests passed, and
461 contract tests passed.
