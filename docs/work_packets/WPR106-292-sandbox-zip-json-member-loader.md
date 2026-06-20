# WPR106-292 Sandbox ZIP JSON Member Loader

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Expand sandbox ZIP archive intake beyond CSV-only members so local venue ZIPs
that contain JSON, JSONL, or NDJSON market-data exports can be loaded by the
same 2024+ sandbox path. Preserve current CSV-first behavior for Binance Vision
kline ZIPs and headered venue-export CSV ZIPs.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-292-sandbox-zip-json-member-loader.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ZIP_JSON_MEMBER_LOADER_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/market_data.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, and
  promotion-ready false.
- Do not execute strict validation, write candidate packs, create paper/live
  signals, define sizing, place orders, change runtime mode, write live
  configuration, download provider data, mutate source files, or claim
  promotion readiness.
- Preserve the 2024+ sandbox date floor and completed-row normalization.
- Preserve deterministic archive descriptor IDs, trial IDs, rankings,
  evidence-request descriptors, blocker semantics, and sandbox boundary flags.
- Preserve existing CSV member selection behavior for ZIP files that contain
  CSV members.
- Keep parsing deterministic from local data only.

## Plan

1. Replace the CSV-only ZIP reader with a ZIP table reader that prefers the
   first CSV member, then TSV, JSON, JSONL, or NDJSON members.
2. Reuse the existing CSV/TSV header detection and JSON/JSONL/NDJSON parsing
   paths.
3. Add focused tests for ZIP NDJSON loading and archive manifest inclusion.
4. Update sandbox contract, active index, stage ledger, and stage report.
5. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Completion Notes

Implemented and closed on 2026-06-19. ZIP archive loading now supports TSV,
JSON, JSONL, and NDJSON members when a ZIP has no CSV member. ZIPs with one or
more CSV members still select CSV first, preserving Binance Vision kline ZIP
behavior and headered local venue-export CSV behavior.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "zip_ndjson or prefers_csv_zip or headered_zip or binance_vision_kline_zip"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 8 focused ZIP tests passed, 140 sandbox tests passed, package
compileall passed, 11 import-boundary tests passed, and 461 contract tests
passed.
