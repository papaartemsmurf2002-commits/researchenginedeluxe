# WPR106-288 Sandbox Gzip Archive Loader

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Improve multi-venue local archive intake for agent workflows by allowing the
sandbox market-data loader and archive manifest builder to read common
gzip-compressed local exports such as `.csv.gz`, `.tsv.gz`, `.json.gz`, and
`.jsonl.gz`.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-288-sandbox-gzip-archive-loader.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_GZIP_ARCHIVE_LOADER_REPORT.md`
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
- Preserve descriptor source-integrity checks against the compressed file
  itself.
- Preserve deterministic archive descriptor IDs, trial IDs, rankings,
  evidence-request descriptors, blocker semantics, and sandbox boundary flags.

## Plan

1. Extend the market-data loader to dispatch `.csv.gz`, `.tsv.gz`, `.json.gz`,
   and `.jsonl.gz` based on the compound suffix.
2. Add those suffixes to archive manifest builder support so gzip files are
   included instead of skipped.
3. Add focused tests for gzip loader behavior, source integrity, and manifest
   materialization.
4. Update sandbox contract, active index, stage ledger, and stage report.
5. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Completion Notes

Implemented and closed on 2026-06-19. The sandbox market-data loader now
supports `.csv.gz`, `.tsv.gz`, `.json.gz`, and `.jsonl.gz` files. The archive
manifest builder recognizes those compound suffixes, records them in build
rows, and includes loadable compressed local exports in generated venue archive
manifests. Descriptor source integrity continues to hash and size-check the
compressed source file itself.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "gzip or binance_vision_kline_zip or archive_manifest_builder_includes_gzip"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 5 focused gzip/archive-loader tests passed, 128 sandbox tests
passed, package compileall passed, 11 import-boundary tests passed, and 461
contract tests passed.
