# WPR106-232 Sandbox Multi Venue Archive Routing

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Make the Rapid Strategy Iteration Sandbox route local market data by venue
archive descriptor instead of forcing every descriptor through one shared
market frame. This moves the sandbox closer to archive-backed multi-venue
iteration across Binance, OKX, Bybit, Hyperliquid, and local manifests while
remaining research-only and non-promotable.

## Scope

- Add descriptor-keyed market-frame loading from `VenueArchiveDescriptor`
  `data_path` values.
- Add a sandbox runner path that loads and sweeps each descriptor against its
  own normalized 2024+ market frame, then ranks all trial rows globally.
- Preserve the existing single-frame runner for tests and callers that already
  provide one prepared frame.
- Update `run-rapid-strategy-sandbox` so multiple venue descriptors can run
  without `--market-data` when every descriptor has `data_path`.
- Keep `--market-data` as an explicit shared-frame fallback for quick smoke
  runs.
- Record descriptor-specific market source metadata in manifests/results.
- Add focused tests for multi-venue descriptor routing, per-venue market
  differences, missing descriptor data-path failure, and CLI execution with
  multiple local archive descriptors.
- Update sandbox contract, active index, ledger, and stage report.

## Allowed Paths

- `docs/work_packets/WPR106-232-sandbox-multi-venue-archive-routing.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_MULTI_VENUE_ARCHIVE_ROUTING_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/research_sandbox/**`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Multiple venue descriptors with distinct `data_path` files run in one sandbox
  sweep and produce venue-specific results.
- Result ranking is global across all descriptor-specific market frames.
- A missing `data_path` fails closed when no shared `--market-data` fallback is
  supplied.
- Existing single-frame sandbox sweep behavior remains available.
- CLI multi-descriptor execution writes the same sandbox manifest, Parquet, and
  evidence-request artifacts under the research output root.
- All outputs remain `research_only`, `observe_only`, `promotion_ready: false`,
  `sandbox_only`, `candidate_evidence: false`, and
  `candidate_pack_eligible: false`.
- Validation includes focused sandbox tests, import-boundary tests, package
  compile, and contract baseline where the local Windows socket environment
  allows it.

## Boundary

This packet only routes local sandbox archive files. It does not download venue
data, use venue account APIs, place orders, write live configuration, create
candidate packs, produce paper/live signals, change sizing, alter runtime mode,
or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. The packet added descriptor-keyed market
frame loading, relative `data_path` resolution from venue descriptor manifests,
descriptor-routed archive sweeps with global ranking, CLI support for multiple
descriptor `data_path` files without shared `--market-data`, shared-frame smoke
fallback preservation, result `market_source` metadata, and manifest
`market_sources` summaries.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results were 30 sandbox tests passed, 11 import-boundary tests passed,
package compileall passed, and 461 contract tests passed.
