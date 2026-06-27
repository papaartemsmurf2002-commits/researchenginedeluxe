# WPR106-543 - V2 Central Market History Speedup And 300 GiB Cap

Status: self_checked
Owner: Codex Research Agent
Date: 2026-06-26

## Objective

Build a faster, manifest-safe central market-history collection path before
resuming broad March 2024 data collection. Update the central market-history
storage cap from 150 GiB to 300 GiB consistently, add bounded parallel
download and append orchestration for official no-paid provider archives, and
then resume the WPR106-541/WPR106-542 March continuation targets under the
research-only central data-readiness lane.

This packet does not create candidate-pack, paper/live, order, sizing,
runtime-mode, promotion, autonomous strategy, or production trading readiness.

## Starting State

WPR106-542 paused after collecting ETH March 1-17, 2024 through daily
append-only central batches. At handoff the central store measured 3218 files,
28316202467 bytes (approximately 26.372 GiB), 71 append-manifest rows, and
8,163,343 normalized rows. At WPR106-543 start, the code still defaulted to a
150 GiB central-store cap, while operator direction was now a 300 GiB local cap.

The remaining March targets are ETH March 18-31, BTC March 5-31, and full
SOL/DOGE March 2024 Binance USD-M aggregate-trade plus Bybit public trading
archives.

The current worktree contains prior uncommitted WPR106-527 through WPR106-542
changes. They are treated as existing operator/agent work and must not be
reverted.

## Allowed Paths

- `docs/work_packets/WPR106-543-v2-central-market-history-speedup-300gb.md`
- `docs/NEXT_AGENT_HANDOFF_WPR106_542_CENTRAL_MARKET_HISTORY_SPEEDUP.md`
- `docs/PRODUCT_SCOPE.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/contracts/autonomous_readiness_contract.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/v2/data_sources/central_market_history.py`
- `src/tradingbotsuite/v2/data_sources/central_market_history_collection.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `tests/v2/test_central_market_history_store_phase76.py`
- `tests/v2/test_central_market_history_collection_phase77.py`
- New append-only generated central market-history artifacts under
  `data/research/central_market_history/**`

## No-Touch Paths

- Live runtime, order-placement, broker/execution, sizing, runtime config,
  promotion, shadow, and candidate-pack truth-layer paths.
- Existing generated research evidence under `data/research/**`, except the
  append-only `data/research/central_market_history/**` output root.
- Secrets, `.env`, credential files, private caches, local SQLite operator
  databases, requester-pays data, paid sources, fixture-only/synthetic data as
  accepted evidence, sandbox-only evidence as accepted evidence, and generated
  `outputs/**`.

## Boundary

All new artifacts and helper models preserve:

```json
{
  "research_only": true,
  "observe_only": true,
  "promotion_ready": false,
  "candidate_evidence": false,
  "candidate_pack_eligible": false,
  "live_signal": false,
  "paper_signal": false,
  "sizing_instruction": false,
  "order_placement_instruction": false,
  "runtime_mode_change": false
}
```

## Plan

- Update the central-market-history default budget cap and associated docs/tests
  to 300 GiB.
- Make archive downloads atomic by writing `.part` files, verifying ZIP/GZIP or
  JSON source integrity, and renaming to final raw source paths only after
  successful validation.
- Reject lingering partial files as cache hits and remove failed partials.
- Add bounded parallel source-plan download orchestration with configurable
  concurrency, storage budget checks, deterministic result ordering, and
  progress telemetry JSONL.
- Add a reusable run helper that downloads, parses, writes one bounded central
  batch, emits source-discovery reports, source metadata, quality reports, and
  append manifests while preserving research-only boundary flags.
- Keep append boundaries small enough for predictable local runtime.
- Resume the remaining March 2024 ETH, BTC, SOL, and DOGE targets only after
  focused speed/cap validation passes.

## Expected Validation

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2/test_central_market_history_store_phase76.py tests/v2/test_central_market_history_collection_phase77.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/contracts -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2 -q
git diff --check
rg boundary scans for forbidden live/order/sizing/runtime/promotion/candidate-pack drift
```

## Results

Implemented and exercised the faster manifest-safe path:

- `CENTRAL_MARKET_HISTORY_MAX_BYTES` now defaults to `300 * 1024**3`
  (322,122,547,200 bytes).
- `download_source_plan()` writes source archives to `.part` files, validates
  ZIP/GZIP/JSON integrity, rejects `.part` refs and invalid cache hits, then
  atomically renames validated sources into `raw_sources/**`.
- `download_source_plans_parallel()` runs bounded concurrent downloads with a
  shared budget guard, deterministic input-order probe results, source-level
  worker-error blockers, and JSONL progress telemetry.
- `collect_central_market_history_batches()` downloads all batch source plans
  once, reuses cache hits, writes daily append batches, emits source-discovery
  reports, preserves source metadata/checksums/quality reports, and detects
  existing run IDs without duplicate append rows.

Collection resumed after focused validation:

- Targets completed: ETH March 18-31, BTC March 5-31, SOL March 1-31, and DOGE
  March 1-31 2024.
- Append boundary: 103 daily central batches.
- Source probes: 206 official no-paid Binance USD-M aggregate-trade ZIPs and
  Bybit public trading GZIPs.
- Source blockers: 0.
- Added rows: 1,030,000 normalized rows, split evenly between `binance_usdm`
  orderflow and `bybit_linear` trade rows.
- Telemetry: `data/research/central_market_history/manifests/wpr106-543-march-collection-progress-retry1.jsonl`.
- Summary: `data/research/central_market_history/manifests/wpr106-543-march-collection-summary.json`.

Final central-store state after WPR106-543:

- Files: 4,152.
- Bytes: 39,925,814,513, approximately 37.184 GiB.
- Remaining under 300 GiB cap: approximately 262.816 GiB.
- Append-manifest rows: 174.
- Normalized rows: 9,193,343.
- Provider rows: `binance_usdm=5,980,980`, `bybit_linear=2,526,913`,
  `binance_spot=352,384`, `bybit_inverse=178,560`, `hyperliquid=144,506`,
  `bybit_spot=10,000`.
- Family rows: `orderflow=5,735,999`, `trade=1,866,000`,
  `ohlcv=1,412,324`, `metadata=179,020`.
- No `.part` files remain under `data/research/central_market_history/**`.

Boundary result: all new collection results, source-discovery progress records,
batch manifests, quality reports, rows, and append-manifest rows preserve
`research_only=true`, `observe_only=true`, `promotion_ready=false`, and the
canonical false candidate/paper/live/order/sizing/runtime flags. This remains
central market-history data readiness only, not autonomous strategy readiness,
candidate evidence, paper/live/order/sizing/runtime behavior, promotion, or
production trading readiness.

Validation completed:

```powershell
python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_central_market_history_store_phase76.py tests\v2\test_central_market_history_collection_phase77.py -q
# 16 passed, 1 warning

$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
# 463 passed, 1 warning

$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2 -q
# 568 passed, 1 warning

git diff --check
# passed; only existing LF-to-CRLF warnings were printed

rg boundary scan over central source/tests
# no matches

rg boundary scan over WPR106-543 generated manifests
# no matches
```
