# WPR106-293 Sandbox Venue Price Aliases

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Expand sandbox local venue-export normalization so common OKX, Bybit,
Hyperliquid, and local archive price columns such as `markPx`, `idxPx`,
`midPx`, `midPrice`, and bid/ask book snapshots can provide the canonical
`close` series needed for 2024+ sandbox audit, preflight, and sweep loops.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-293-sandbox-venue-price-aliases.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_VENUE_PRICE_ALIASES_REPORT.md`
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
- Prefer explicit close/price/mark/index/mid aliases before any bid/ask
  midpoint fallback.
- Keep parsing deterministic from local data only.

## Plan

1. Add common mark/index/mid price aliases to the canonical close alias set.
2. Add deterministic bid/ask midpoint fallback only when no explicit close-like
   alias exists.
3. Record midpoint derivation in normalization metadata for audit/build-report
   visibility.
4. Add focused tests for OKX mark/index aliases, Hyperliquid/Bybit-style
   midpoint snapshots, and archive manifest inclusion for L2 book snapshots.
5. Update sandbox contract, active index, stage ledger, and stage report.
6. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Completion Notes

Implemented and closed on 2026-06-19. Sandbox market-frame normalization now
accepts common mark/index/mid price aliases such as `markPx`, `idxPx`, and
`midPx`. When no explicit close-like price alias exists, the loader can derive
canonical `close` from bid/ask midpoint for book-style exports and records that
derivation in normalization metadata. Archive manifest build rows expose
derived-column metadata for agent triage.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "mark_and_index or bid_ask_midpoint or l2_bid_ask"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 3 focused venue price-alias tests passed, 143 sandbox tests
passed, package compileall passed, 11 import-boundary tests passed, and 461
contract tests passed.
