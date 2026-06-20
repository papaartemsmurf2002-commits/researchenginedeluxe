# WPR106-298 Sandbox Container Member Metadata

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Expose deterministic ZIP and TAR/TGZ member-selection metadata in sandbox
market-frame normalization and archive-manifest build rows so agent preflight
loops can audit which archive members were actually loaded.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-298-sandbox-container-member-metadata.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_CONTAINER_MEMBER_METADATA_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/market_data.py`
- `src/tradingbotsuite/research_sandbox/archive_manifest.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, and
  promotion-ready false.
- Do not execute strict validation, write candidate packs, create paper/live
  signals, define sizing, place orders, change runtime mode, write live
  configuration, download provider data, mutate source archive files, extract
  archive members to disk, or claim promotion readiness.
- Preserve the 2024+ sandbox date floor and completed-row normalization.
- Preserve deterministic archive descriptor IDs, trial IDs, rankings,
  evidence-request descriptors, blocker semantics, source-integrity metadata,
  and sandbox boundary flags.
- Preserve member priority semantics: select the highest-priority available
  member type and load only members of that selected type.
- Keep metadata bounded and deterministic for compact agent reports.

## Plan

1. Attach bounded container member metadata to raw frames produced by ZIP and
   TAR/TGZ loaders.
2. Propagate that metadata through normalization as
   `container_member_metadata`.
3. Surface the metadata in archive-manifest build rows with searchable summary
   columns.
4. Add focused tests for ZIP/TAR loader metadata and manifest build rows.
5. Update sandbox contract, active index, stage ledger, and stage report.
6. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Completion Notes

Implemented and closed on 2026-06-19. ZIP and TAR/TGZ sandbox loaders now
attach bounded container member-selection metadata to raw loaded frames, and
normalization preserves it under `container_member_metadata` with
`container_member_count`. Archive manifest build rows expose the nested
metadata plus searchable summary fields for container kind, selected suffix,
selected member count, selected member-name sample, suffix counts, and loadable
member count.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "container_member_metadata"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 3 focused container member-metadata tests passed, 160 sandbox
tests passed, package compileall passed, 11 import-boundary tests passed, and
461 contract tests passed.
