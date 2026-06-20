# WPR106-243 Sandbox Venue Export Normalizer

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Make the Rapid Strategy Iteration Sandbox more useful for OKX, Bybit, and
Hyperliquid archive-backed research by accepting common local venue export
column names without manual CSV rewrites.

## Scope

- Add sandbox market-frame normalization for common timestamp, OHLCV, trade,
  and signal/feature column aliases seen in local venue exports.
- Keep normalized output canonical for the existing sandbox runner:
  `timestamp`, `open`, `high`, `low`, `close`, `volume`, plus preserved extra
  columns when safe.
- Preserve the existing 2024+ data-window filter and fail-closed missing
  `timestamp` or `close` behavior.
- Keep archive manifest building, archive audits, one-command iterations, and
  direct market-frame loads using the same normalization path.
- Record alias normalization metadata in audit/build rows where useful for
  agent troubleshooting.
- Add focused tests for OKX/Bybit/Hyperliquid-style local exports.
- Update sandbox docs and stage closeout docs.

## Allowed Paths

- `docs/work_packets/WPR106-243-sandbox-venue-export-normalizer.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_VENUE_EXPORT_NORMALIZER_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/**`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Local CSV/TSV/JSON/JSONL/Parquet loads with common venue aliases are
  normalized into canonical sandbox market frames.
- OKX-style millisecond timestamp/OHLC columns can be built into archive
  manifests and run through an archive-backed sandbox sweep.
- Bybit-style `startTime` / `openPrice` / `closePrice` exports can be loaded
  and audited with high/low support.
- Hyperliquid-style time and price columns can be loaded without treating
  pre-2024 rows as usable evidence.
- Missing timestamp or close data still fails closed.
- Validation includes focused sandbox tests, package compile, and the contract
  baseline when the local validation environment allows pytest-asyncio socket
  setup.

## Boundary

This packet only normalizes local sandbox market-frame inputs for research
iteration. It does not download data, execute strict validation, write
candidate packs, create paper/live signals, define sizing, place orders, mutate
runtime mode, write live configuration, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. The packet added common local venue
export alias normalization for sandbox market frames. Canonical columns remain
`timestamp`, `open`, `high`, `low`, `close`, and `volume`, while original
columns are preserved when safe for strategy features. The loader now accepts
OKX-style short OHLCV columns, Bybit-style `startTime` and `openPrice` /
`closePrice` columns, and Hyperliquid-style `time`, `px`, and `sz` trade rows.
Archive manifest build rows and archive descriptor audit rows record alias
metadata for agent troubleshooting. Pre-2024 rows are still filtered out, and
missing timestamp or close data still fails closed.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final focused results were 65 sandbox tests passed, 11 import-boundary tests
passed, and package compileall passed. The full contract baseline was attempted
and reached 460 passed tests before failing during pytest-asyncio event-loop
socketpair setup for one async contract test with Windows `WinError 10055`,
before the test body ran. `ISSUE-R106-026` tracks this local
validation-environment blocker.
