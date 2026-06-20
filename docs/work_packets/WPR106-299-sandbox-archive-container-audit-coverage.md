# WPR106-299 Sandbox Archive Container Audit Coverage

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Propagate sandbox container member-selection metadata from normalized market
frames into archive descriptor audit rows and archive coverage buckets so agent
preflight loops can inspect chunked ZIP/TAR intake without reopening manifest
build reports.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-299-sandbox-archive-container-audit-coverage.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARCHIVE_CONTAINER_AUDIT_COVERAGE_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/archive_audit.py`
- `src/tradingbotsuite/research_sandbox/archive_coverage.py`
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
  descriptor readiness blockers, source-integrity checks, and coverage bucket
  identity.
- Treat container metadata as diagnostics only; it must not alter descriptor
  readiness, trial identity, metrics, rankings, or evidence requests.
- Keep metadata bounded and deterministic for compact agent reports.

## Plan

1. Copy bounded container member metadata from normalization metadata into
   archive descriptor audit rows.
2. Aggregate audit-level container fields into archive coverage rows with
   deterministic suffix/count/sample summaries.
3. Add focused tests for audit JSON/Parquet rows and coverage bucket
   aggregation.
4. Update sandbox contract, active index, stage ledger, and stage report.
5. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Completion Notes

Implemented and closed on 2026-06-19. Archive descriptor audit rows now carry
bounded container member-selection metadata from normalized market frames, and
archive coverage rows aggregate those diagnostics into bucket-level summaries.
The metadata is diagnostic only and does not change archive loading,
descriptor readiness, coverage bucket identity, trial identity, sweep metrics,
or evidence-request behavior.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "archive_descriptor_audit_records_container_member_metadata or archive_coverage_matrix_aggregates_container_member_metadata"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 2 focused archive container audit/coverage tests passed, 162
sandbox tests passed, package compileall passed, 11 import-boundary tests
passed, and 461 contract tests passed.
