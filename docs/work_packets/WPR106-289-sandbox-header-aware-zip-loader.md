# WPR106-289 Sandbox Header-Aware ZIP Loader

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Improve multi-venue local archive intake by making ZIP CSV loading
header-aware. Local OKX, Bybit, Hyperliquid, and generic venue exports inside
ZIP files may contain useful header columns such as `venue`, `symbol`,
`interval`, `timestamp`, `close`, or venue-specific aliases. The sandbox should
preserve those headers for normalization and archive-manifest content
inference while keeping existing Binance Vision headerless kline ZIP support.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-289-sandbox-header-aware-zip-loader.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_HEADER_AWARE_ZIP_LOADER_REPORT.md`
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
  configuration, download provider data, mutate source files, or claim
  promotion readiness.
- Preserve the 2024+ sandbox date floor and completed-row normalization.
- Preserve descriptor source-integrity checks against the ZIP file itself.
- Preserve Binance Vision headerless ZIP behavior.
- Preserve deterministic archive descriptor IDs, trial IDs, rankings,
  evidence-request descriptors, blocker semantics, and sandbox boundary flags.

## Plan

1. Reuse the normal text-table header detection for ZIP CSV members.
2. Ensure file-like rereads reset before fallback headerless reads.
3. Add focused tests for headerless Binance Vision ZIP compatibility and
   headered venue-export ZIP content inference.
4. Update sandbox contract, active index, stage ledger, and stage report.
5. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Completion Notes

Implemented and closed on 2026-06-19. ZIP CSV members now use the same
header-detection path as plain CSV files, with file-like stream rewinds before
fallback headerless reads. Headered local venue-export ZIPs preserve columns
for alias normalization and content-derived manifest identity inference, while
Binance Vision headerless kline ZIP support remains intact. Archive data-family
path inference now uses token matches instead of raw substring matches, so
generic names such as `market_export.zip` no longer infer `mark_index`.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "zip and (market_frame_loader or archive_manifest_builder)"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 7 focused ZIP/archive-loader tests passed, 130 sandbox tests
passed, package compileall passed, 11 import-boundary tests passed, and 461
contract tests passed.
