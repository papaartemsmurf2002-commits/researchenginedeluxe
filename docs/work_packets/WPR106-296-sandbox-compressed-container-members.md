# WPR106-296 Sandbox Compressed Container Members

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Expand sandbox ZIP and TAR/TGZ local archive loading so container members named
`.csv.gz`, `.tsv.gz`, `.json.gz`, `.jsonl.gz`, or `.ndjson.gz` are detected by
compound suffix and parsed through the existing 2024+ market-data
normalization path without manual extraction or decompression.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-296-sandbox-compressed-container-members.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_COMPRESSED_CONTAINER_MEMBERS_REPORT.md`
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
- Preserve CSV-first member priority semantics across plain and gzip-compressed
  member forms.
- Keep parsing deterministic from local data only.

## Plan

1. Replace simple ZIP/TAR member suffix checks with compound suffix detection
   for gzip-compressed market-data members.
2. Reuse the existing CSV/TSV/JSON/JSONL/NDJSON parser paths after in-memory
   gzip decompression.
3. Add focused tests for ZIP `.jsonl.gz`, TAR `.csv.gz` priority, and archive
   manifest inclusion of compressed container members.
4. Update sandbox contract, active index, stage ledger, and stage report.
5. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Completion Notes

Implemented and closed on 2026-06-19. ZIP and TAR/TGZ sandbox member loading
now detects compound gzip market-data member suffixes such as `.csv.gz`,
`.json.gz`, `.jsonl.gz`, and `.ndjson.gz`. Member payloads are decompressed in
memory and then parsed through the same CSV/TSV/JSON/JSONL/NDJSON normalization
path used by plain files, preserving 2024+ filtering, venue alias handling,
Hyperliquid L2 flattening, midpoint derivation, and sandbox boundary flags.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "gzip_jsonl_member or csv_gzip_tar_member"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 3 focused compressed-container member tests passed, 153 sandbox
tests passed, package compileall passed, 11 import-boundary tests passed, and
461 contract tests passed.
