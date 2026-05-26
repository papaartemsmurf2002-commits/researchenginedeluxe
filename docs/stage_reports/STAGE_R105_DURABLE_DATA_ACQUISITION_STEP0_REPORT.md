# Stage R105 Durable Data Acquisition Step 0 Report

Date: 2026-05-20
Work packet: `docs/work_packets/WPR105-106-durable-data-acquisition-step0.md`
Status: closed

## Summary

WPR105-106 adds the missing required data-acquisition step ahead of durable
readiness. The operator now has a real Step 0 that collects expanded BTCUSDT and
ETHUSDT Binance Vision public-archive data, verifies checksums, builds
research-only candidate-depth fixture packs, and writes active readiness,
historical-cycle, and exact-discovery specs for the rest of the required
checklist.

This does not remove other provider work. Binance Vision is the default
runnable public-archive path because it already has implemented archive
downloads, checksum sidecars, and fixture-pack contracts. Crypto Lake/local
vendor exports and registered Hyperliquid archive surfaces remain provider
surfaces through the provider pipeline; they must produce the same validated
fixture/spec contract before replacing or augmenting the required checklist.

The compact checked fixtures remain valid screening inputs and are not deleted
or overwritten. They no longer complete candidate-depth readiness when generated
expanded packs are absent.

## Implementation Notes

- Added `collect_candidate_depth_public_archive_fixtures()` for monthly Binance
  Vision 15m kline, 1m kline, and aggTrades archives with `.CHECKSUM`
  verification.
- Generated packs write `cycle_dataset.parquet`, 15m bars, 1m bars, a 1m
  aggTrade trade-flow proxy, `fixture_pack_manifest.json`, active readiness
  config, active historical-cycle spec, active exact-discovery spec, and
  `durable_fixture_collection_summary.json`.
- Readiness now prefers the latest validated generated candidate-depth pack per
  symbol and exposes active generated fixture/spec paths to the operator API.
- The required Research UI checklist starts with `0. Collect Durable Data`, and
  the BTC/ETH cycle and exact-discovery buttons use the generated active specs
  when present.
- The Research UI now states that Step 0 is the default public-archive route,
  not the only possible provider route; provider diagnostics remain available
  for Crypto Lake/local vendor exports and registered Hyperliquid archive
  surfaces.
- Source reliability checks reject checksum failures, source bar gaps,
  duplicate source bars, missing/gapped lower-timeframe bars, duplicate
  aggTrade IDs inside a partition, and insufficient candidate-depth row floors.

## Boundary

No live execution, order placement, runtime-mode mutation, live configuration
write, promotion behavior, candidate-pack write, or sizing behavior was added.
All generated outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_market_data_collection.py::test_collect_candidate_depth_public_archive_fixtures_writes_active_specs_with_checksum_evidence tests\tradingbotsuite\test_market_data_collection.py::test_collect_candidate_depth_public_archive_fixtures_rejects_duplicate_source_bars -q
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py::test_operator_research_page_keeps_hmm_knn_monitoring_observe_only tests\tradingbotsuite\test_operator_ui.py::test_operator_research_progress_api_reports_r104_milestones tests\tradingbotsuite\test_operator_ui.py::test_operator_research_job_routes_default_to_r104_deep_and_exact_specs tests\tradingbotsuite\test_operator_ui.py::test_operator_research_job_blocked_in_live_mode_without_position -q
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_market_data_collection.py tests\tradingbotsuite\test_operator_ui.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Result: compile passed; focused durable data-builder tests passed; focused
operator UI and route tests passed; full market-data/operator UI tests passed
with `69 passed`; contracts passed with `427 passed`; `git diff --check`
passed.

## Remaining Operator Action

`ISSUE-R104-001` remains open until Step 0 is run against the full target month
range, readiness accepts the generated packs, and the required BTC/ETH deep
cycles, exact sweeps, and candidate eligibility review complete.
