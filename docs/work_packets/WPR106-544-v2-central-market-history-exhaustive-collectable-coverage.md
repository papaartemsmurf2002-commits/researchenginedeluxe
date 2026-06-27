# WPR106-544 - V2 Central Market History Exhaustive Collectable Coverage

Status: complete
Owner: Codex Research Agent
Date: 2026-06-26

## Objective

Collect every currently collectable no-paid 2024+ central market-history input
that is practical under the active 300 GiB central-store cap, using bounded
parallelism and manifest-safe writes. Any missing, unsupported, unavailable,
operator-gated, or budget-blocked data must be explicitly recorded so backtest
and strategy callers can determine whether partial-data testing is allowed or a
strategy path must be called off for insufficient data.

This packet remains research-only central data readiness. It does not create
candidate-pack, paper/live, order, sizing, runtime-mode, promotion, autonomous
strategy, or production trading readiness.

## Starting State

WPR106-543 left the central store at 4,152 files, 39,925,814,513 bytes
approximately 37.184 GiB, 174 append-manifest rows, 9,193,343 normalized rows,
and no `.part` files. The active budget cap is 300 GiB.

The local central store has broad 2024-01 through 2026-05 1h/1d Binance/Bybit
bars for many symbols, but it does not yet have a normalized 1m bar backbone.
Dense trade/orderflow collection is currently strongest for January through
March 2024, and previous daily trade/orderflow batches used bounded normalized
row limits while preserving raw source archives.

Current Hyperliquid public metadata is useful for current-universe discovery,
but historical as-of universe coverage is still incomplete unless a later
source provides historical membership snapshots. Hyperliquid official S3
history remains requester-pays/operator-gated and is not collectable under this
packet without a separate explicit operator gate.

## Allowed Paths

- `docs/work_packets/WPR106-544-v2-central-market-history-exhaustive-collectable-coverage.md`
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

## Collection Scope

Collectable in this packet:

- Binance USD-M official public archive klines, especially 1m bars from
  2024-01-01 onward or symbol listing date onward.
- Binance USD-M official public archive aggregate trades from 2024-01-01 onward
  or symbol listing date onward, subject to the 300 GiB cap and local runtime.
- Bybit public archive trade files where available, with explicit budget and
  availability gaps because dense Bybit trade archives can exceed the local
  cap.
- Current Hyperliquid public metadata/universe snapshots and recent public
  candle windows where API limits permit.

Not collectable under this packet without explicit later operator action:

- Hyperliquid official S3 requester-pays files, including full historical L2,
  asset contexts, node fills, and node trades.
- Paid, authenticated, requester-pays, secret-backed, or local-private sources.
- Historical as-of Hyperliquid universe membership before the current public
  snapshot unless a no-paid public historical membership source is identified.

## Plan

- Build a fresh current-universe and existing-central-symbol source inventory.
- Collect missing Binance USD-M 1m kline monthly archives first because they are
  compact and provide the canonical bar backbone for research panels.
- Continue with Binance USD-M aggregate-trade archives using bounded
  concurrency and deterministic per-symbol/month append boundaries while
  respecting the 300 GiB cap.
- Probe or collect Bybit public trade archives only where budget allows; record
  the rest as explicitly budget-blocked or unavailable.
- Write a consolidated collection instrument/gap ledger that records collected,
  unavailable, unsupported, operator-gated, budget-blocked, and partial parse
  states for each provider/family/symbol/window.
- Update control docs so strategy/backtest callers must read the ledger before
  running on partial data; insufficient required data must call off the test
  rather than silently substituting incomplete evidence.

## Expected Validation

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2/test_central_market_history_store_phase76.py tests/v2/test_central_market_history_collection_phase77.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/contracts -q
git diff --check
rg boundary scans for forbidden live/order/sizing/runtime/promotion/candidate-pack drift
```

## Completed Artifacts

- Authoritative collection ledger:
  `data/research/central_market_history/manifests/wpr106-544-central-market-history-exhaustive-coverage-v2-collection_ledger-ef0cfdcda209.json`
- Binance USD-M 1m source-discovery report:
  `data/research/central_market_history/manifests/wpr106-544-central-market-history-exhaustive-coverage-v2-binance-usdm-1m-bars-source_discovery_report-564552e6a9dc.json`
- Parallel download telemetry:
  `data/research/central_market_history/manifests/wpr106-544-binance-usdm-1m-bars-progress.jsonl`
- Fast normalization telemetry:
  `data/research/central_market_history/manifests/wpr106-544-fast-normalize-binance-usdm-1m-bars-progress.jsonl`

## Result

WPR106-544 collected every currently reachable official no-paid Binance USD-M
monthly 1m kline ZIP in the discovered 230-symbol central universe for
2024-01 through 2026-05, under the 300 GiB cap. The bounded downloader
processed 6,670 source probes, collected 4,799 raw ZIPs, recorded 1,871
official unavailable sources after retrying the three initial worker anomalies
as 404s, and left zero `.part` files.

The packet adds a fast manifest-compatible OHLCV payload writer and fixes the
central Parquet helper hot path. BTC, ETH, SOL, and DOGE now each have 29
monthly normalized 1m bar manifests covering 2024-01 through 2026-05, with
1,270,080 rows per symbol and `backtest_usable=true` in the ledger. The
central store now has 296 append-manifest rows, 14,510,318 normalized rows,
and uses approximately 44.4 GiB of the 300 GiB cap.

Broad non-priority symbols are mostly raw-collected but not fully normalized.
The ledger records which symbols/windows are raw-only, partial, unavailable,
or backtest-usable. Future agents can normalize raw-complete symbols without
additional provider downloads, but backtest callers must not infer readiness
from raw ZIP presence alone.

Dense 2024+ orderflow beyond the existing January-March row-limited evidence
is budget-blocked unless narrowed by symbol/window. Hyperliquid official
historical S3 orderflow/book/history remains requester-pays/operator-gated and
was not collected in this no-paid packet.

## Backtest/Strategy Rule

Backtest and strategy callers must consult the WPR106-544 collection ledger
before running on central market-history data. Entries with
`backtest_usable=true` may be used for the declared family/symbol/window.
Entries marked `partial` may only be used when the requested test window is
covered by the listed manifest refs and the strategy explicitly allows partial
data. Entries marked `unavailable`, `budget_blocked`, `unsupported`, or
`operator_gated` must call off a strategy path that requires that family rather
than silently substituting bar-only or incomplete evidence.

## Validation Evidence

Passed:

```powershell
python -m compileall -q src\tradingbotsuite\v2\data_sources
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_central_market_history_store_phase76.py tests\v2\test_central_market_history_collection_phase77.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
git diff --check
rg boundary scan for true live/paper/order/sizing/runtime/candidate/promotion flags over changed source/docs and WPR106-544 manifests
```

Focused result: 18 passed, 1 warning.
Contracts result: 463 passed, 1 warning.
`git diff --check` returned only pre-existing LF-to-CRLF working-copy warnings.
The boundary scan found no true live/paper/order/sizing/runtime/candidate or
promotion flags in the WPR106-544 artifacts or changed source/docs.
