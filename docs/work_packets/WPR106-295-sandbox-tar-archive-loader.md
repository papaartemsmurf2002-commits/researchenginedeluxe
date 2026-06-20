# WPR106-295 Sandbox TAR Archive Loader

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Expand sandbox local archive intake so `.tar`, `.tar.gz`, and `.tgz` venue
drops containing CSV, TSV, JSON, JSONL, or NDJSON market-data members can enter
the existing 2024+ archive manifest, audit, preflight, and sweep loops without
manual extraction.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-295-sandbox-tar-archive-loader.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_TAR_ARCHIVE_LOADER_REPORT.md`
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
- Preserve ZIP CSV-first member priority semantics for ZIP files; TAR member
  loading may use the same CSV/TSV/JSON/JSONL/NDJSON priority order.
- Keep parsing deterministic from local data only.

## Plan

1. Add TAR/TGZ market-data member loading using in-memory member reads only.
2. Reuse existing CSV/TSV header detection and JSON/JSONL/NDJSON parsing paths.
3. Register `.tar`, `.tar.gz`, and `.tgz` as archive manifest builder suffixes.
4. Add focused tests for TAR JSONL loading, TAR CSV priority, and archive
   manifest inclusion.
5. Update sandbox contract, active index, stage ledger, and stage report.
6. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Completion Notes

Implemented and closed on 2026-06-19. Sandbox market-data loading now supports
`.tar`, `.tar.gz`, and `.tgz` local archive files containing CSV, TSV, JSON,
JSONL, or NDJSON market-data members. TAR/TGZ members are read in memory and
reuse the existing CSV/TSV header detection plus JSON/JSONL/NDJSON parsing and
2024+ normalization paths. Archive manifest building now recognizes TAR/TGZ
source suffixes and preserves source integrity metadata on generated
descriptors.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "tar_jsonl or csv_tar_member"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 3 focused TAR archive-loader tests passed, 150 sandbox tests
passed, package compileall passed, 11 import-boundary tests passed, and 461
contract tests passed.
