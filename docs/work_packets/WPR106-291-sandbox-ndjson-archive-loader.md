# WPR106-291 Sandbox NDJSON Archive Loader

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Expand sandbox local archive intake to accept `.ndjson` and `.ndjson.gz`
newline-delimited JSON exports as deterministic aliases of the existing JSONL
loader. This closes a common local-stream export gap for Hyperliquid, Bybit,
OKX, and local manifest workflows without changing sandbox execution,
ranking, evidence-request, or validation behavior.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-291-sandbox-ndjson-archive-loader.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_NDJSON_ARCHIVE_LOADER_REPORT.md`
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
- Preserve deterministic archive descriptor IDs, trial IDs, rankings,
  evidence-request descriptors, blocker semantics, and sandbox boundary flags.
- Keep parsing deterministic from local data only.

## Plan

1. Add `.ndjson` and `.ndjson.gz` suffix handling to the existing JSONL
   market-data loader path.
2. Add those suffixes to archive manifest builder support and compound suffix
   reporting.
3. Add focused tests for direct `.ndjson`, gzip `.ndjson.gz`, and archive
   manifest inclusion/source suffix reporting.
4. Update sandbox contract, active index, stage ledger, and stage report.
5. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Completion Notes

Implemented and closed on 2026-06-19. `.ndjson` and `.ndjson.gz` files now
use the same deterministic newline-delimited JSON loader as `.jsonl` and
`.jsonl.gz`. Archive manifest building recognizes both suffixes, records
`.ndjson.gz` as the compound source suffix, and preserves compressed-file
source integrity metadata.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "ndjson"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 3 focused NDJSON tests passed, 137 sandbox tests passed,
package compileall passed, 11 import-boundary tests passed, and 461 contract
tests passed.
