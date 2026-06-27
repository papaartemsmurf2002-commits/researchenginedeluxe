# WPR106-551 V2 Free-Venue Data Authority Resolution

Status: complete
Owner: Codex Research Agent
Date opened: 2026-06-27

## Goal

Resolve the remaining data-source conflict after the WPR106-550 catalog pass:
for the current v2 research scope, strict-free/no-paid venue data is the
authoritative data baseline. If all available OF-style source families have
been collected and validated under that constraint, data collection is
complete for final audit handoff. Uncollectable or requester-pays native
Hyperliquid historical sources are provenance caveats only; they must not
remain readiness blockers or next-agent instructions.

## Allowed paths

- `docs/work_packets/WPR106-551-v2-free-venue-data-authority-resolution.md`
- `docs/V2_DATA_CATALOG_AND_AGENTIC_RESEARCH_POINTERS.md`
- `docs/v2_visibility_snapshot_wpr106_551.json`
- `docs/index.html`
- `README.md`
- `START_HERE.md`
- `docs/ACTIVE_INDEX.md`
- `docs/PRODUCT_SCOPE.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/contracts/autonomous_readiness_contract.md`
- `docs/contracts/autonomy_loop_contract.md`
- `src/tradingbotsuite/v2/audit/readiness.py`
- `tests/v2/test_autonomous_readiness_audit_phase29.py`

## Out of scope

- No provider downloads, archive mutation, normalization backfill, strategy
  execution, candidate-pack writes, paper/live/order/sizing/runtime behavior,
  or promotion claims.
- Do not rewrite historical generated evidence. This packet changes the
  controlling interpretation of already-collected free-venue data and the
  readiness pointers that agents use.

## Plan

1. Identify docs and readiness code that still treats missing native
   Hyperliquid historical data as a blocker.
2. Update the scope, issue register, audit contract, and handoff docs so the
   free-venue OF-style archive is the authoritative complete data baseline.
3. Update the autonomous readiness manager's data next-action language so it
   asks for authoritative free-venue data evidence, not uncollectable
   Hyperliquid-native archive evidence.
4. Refresh the static GitHub Pages HTML from the updated visibility snapshot.
5. Run focused validation and record results.

## Validation

Passed:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_autonomous_readiness_audit_phase29.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_ui_visibility_phase22.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_central_market_history_store_phase76.py tests\v2\test_central_market_history_collection_phase77.py -q
$env:PYTHONPATH='src'; python -m tradingbotsuite.v2.cli.main ui render --input-root docs --snapshot-json v2_visibility_snapshot_wpr106_551.json --output-root docs --output-html index.html
git diff --check
```

Results:

- compile passed;
- autonomous readiness tests: 8 passed;
- UI visibility tests: 13 passed;
- contracts baseline: 463 passed;
- central market-history focused tests: 21 passed;
- snapshot-to-HTML consistency check passed;
- `git diff --check` passed with only the existing LF-to-CRLF warnings.

Note: the initial Windows command
`python -m pytest tests\v2\test_central_market_history*.py -q` did not expand
the glob and ran no tests. The explicit file-list command above is the valid
local invocation.

## Completion summary

- `ISSUE-R106-032` is resolved as a data-source/readiness-policy conflict.
- `docs/KNOWN_ISSUES.md` now reports zero open P0/P1 issues.
- Strict-free/no-paid venue data is the authoritative data baseline for final
  audit and agentic research handoff.
- Unavailable requester-pays/native Hyperliquid official history is out of
  scope for data readiness and must not be treated as a blocker.
- The readiness manager now asks for
  `provide_authoritative_free_venue_data_evidence` instead of native
  Hyperliquid archive evidence when data keys are missing.
- `docs/index.html` is rendered from
  `docs/v2_visibility_snapshot_wpr106_551.json`, matching the GitHub Pages
  docs entrypoint.

## Notes

- WPR106-546 already proves lifecycle-scoped official Binance USD-M 1m bars are
  complete and backtest-usable for all 29 project symbols through 2026-05.
- WPR106-549/WPR106-550 already prove the external raw-heavy archive contains
  1,159,478 complete official Binance USD-M source files across the requested
  OF-style families with zero missing, invalid, or partial files in the latest
  validation report.
- This packet resolves data-source blockers only. It does not claim that
  normalized OF-style feature panels, strategy results, autonomous loop
  artifacts, candidate packs, paper/live signals, order placement, sizing, or
  runtime promotion are ready.
