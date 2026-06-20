# WPR106-294 Sandbox Hyperliquid L2 JSON Loader

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Expand sandbox local venue-export normalization so Hyperliquid-style nested
`l2Book` JSON payloads with `levels` arrays can be flattened into deterministic
best bid/ask rows, derive canonical midpoint `close`, and enter archive
manifest/audit/preflight/sweep loops without hand-normalizing the files first.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-294-sandbox-hyperliquid-l2-json-loader.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_HYPERLIQUID_L2_JSON_LOADER_REPORT.md`
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
  configuration, download provider data, mutate source archive files, or claim
  promotion readiness.
- Preserve the 2024+ sandbox date floor and completed-row normalization.
- Preserve deterministic archive descriptor IDs, trial IDs, rankings,
  evidence-request descriptors, blocker semantics, and sandbox boundary flags.
- Flatten only already-local JSON/ZIP JSON payloads; do not add provider
  network access or Hyperliquid account access.
- Treat nested book snapshots as diagnostic archive inputs, not venue execution
  proof or strict L2 fill evidence.

## Plan

1. Add deterministic flattening for Hyperliquid `l2Book` payloads whose
   `data` item or rows contain `levels` arrays.
2. Emit flat best bid/ask price and size columns that reuse the existing
   bid/ask midpoint close derivation path and normalization metadata.
3. Improve archive manifest data-family inference for flattened book snapshots
   when paths are generic.
4. Add focused tests for plain JSON, ZIP JSON, and archive-manifest inclusion
   of nested Hyperliquid L2 book exports.
5. Update sandbox contract, active index, stage ledger, and stage report.
6. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Completion Notes

Implemented and closed on 2026-06-19. Sandbox JSON and JSONL parsing now
flattens local Hyperliquid-style nested `l2Book` payloads with `levels` arrays
into deterministic best bid/ask price and size columns. ZIP JSON members reuse
the same path. The existing bid/ask midpoint derivation then provides canonical
`close` values for 2024+ sandbox audits, archive manifests, preflights, and
sweeps. Archive manifest build rows now expose source-transformation metadata,
and data-family inference recognizes `l2Book` content hints and flattened book
columns as `l2_book`.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "l2_book_json or l2_book_zip_json or l2_book_jsonl_messages or hyperliquid_l2_book_json_export"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 4 focused Hyperliquid L2 JSON tests passed, 147 sandbox tests
passed, package compileall passed, 11 import-boundary tests passed, and 461
contract tests passed.
