# WPR106-542 - V2 Central Market History March Continuation

Status: paused_for_speedup_handoff
Owner: Codex Research Agent
Date: 2026-06-26

## Objective

Continue the centralized market-history collection toward the active
research-only, data-first, multi-instrument v2 scope by consuming the March
2024 continuation targets recorded by WPR106-541 and adding official no-paid
trade/orderflow-style archives into `data/research/central_market_history/**`
without exceeding the configured local cap.

Hyperliquid remains preferred where usable, but the central market-history
data-readiness lane must not fail solely because Hyperliquid historical
coverage is absent for a symbol/window when eligible no-paid Binance, Bybit, or
other repo-supported provider data is present, valid, and manifested. This
packet does not alter stricter Hyperliquid-native autonomous readiness gates.

This packet does not create candidate-pack, paper/live, order, sizing,
runtime-mode, promotion, autonomous strategy, or production trading readiness.

## Starting State

At packet start the central store contains 3065 files and 26858531485 bytes
(approximately 25.014 GiB), leaving approximately 124.986 GiB under the 150 GiB
cap. The append manifest has 54 prior rows from WPR106-534 through WPR106-541.

After partial WPR106-542 collection, the operator changed the intended cap to
300 GiB and directed the next agent to solve collection performance before
continuing broad bulk ingest. Current code still carries a 150 GiB default in
`CENTRAL_MARKET_HISTORY_MAX_BYTES`; the next speed packet must update code,
docs, and tests so the 300 GiB cap is enforced consistently rather than only
documented here.

WPR106-541 recorded exact `deferred_next_packet` source URLs for BTC March 5-31
and full ETH, SOL, and DOGE March 2024 Binance USD-M aggregate-trade and Bybit
public trading archives. This packet starts with bounded ETH chunks because the
larger BTC/SOL/DOGE Bybit archives need smaller runtime-safe slices.

The current worktree also contains prior uncommitted WPR106-527 through
WPR106-541 changes. They are treated as authoritative and must not be reverted
or rewritten outside this packet's scope.

## Allowed Paths

- `docs/work_packets/WPR106-542-v2-central-market-history-march-continuation.md`
- `docs/NEXT_AGENT_HANDOFF_WPR106_542_CENTRAL_MARKET_HISTORY_SPEEDUP.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/v2/data_sources/central_market_history.py`
- `src/tradingbotsuite/v2/data_sources/central_market_history_collection.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `tests/v2/test_central_market_history_store_phase76.py`
- `tests/v2/test_central_market_history_collection_phase77.py`
- New generated central market-history artifacts under
  `data/research/central_market_history/**`

## No-Touch Paths

- Live runtime, order-placement, broker/execution, sizing, runtime config,
  promotion, shadow, and candidate-pack truth-layer paths.
- Existing generated research evidence under `data/research/**`, except the
  append-only `data/research/central_market_history/**` output root.
- Secrets, `.env`, credential files, private caches, local SQLite operator
  databases, requester-pays data, paid sources, fixture-only/synthetic data as
  accepted evidence, sandbox-only evidence as accepted evidence, supplied-ref
  evidence without verifiable provenance, and generated `outputs/**`.

## Boundary

All new artifacts and models preserve:

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

- Reuse the central collection helpers and budget checks from WPR106-535
  through WPR106-541.
- Collect public official Binance USD-M aggregate-trade ZIPs and Bybit public
  linear trading GZIPs for March 2024 ETH in bounded chunks, then continue to
  BTC/SOL/DOGE slices if runtime and budget remain favorable.
- Preserve raw compressed source files where practical, normalize bounded
  sample rows per file into append-only Parquet/manifest batches, and record
  source discovery reports, checksums, coverage, quality, and exact blockers.
- Treat trade/orderflow families with relaxed cross-provider equality:
  provenance, schema validity, timestamp sanity, monotonicity, nonempty rows,
  and coverage metrics are required; strict row equality is not.
- Stop or downshift collection before any pass risks the 150 GiB cap or
  unreliable local runtime behavior.
- Update control docs only if this packet discovers a new blocker or changes
  the central data-readiness contract.

## Expected Validation

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2/test_central_market_history_store_phase76.py tests/v2/test_central_market_history_collection_phase77.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest focused data/provider/storage/manifest tests -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/contracts -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2 -q
git diff --check
rg boundary scans for forbidden live/order/sizing/runtime/promotion/candidate-pack drift
```

## Results

Paused for speed-focused handoff at operator request. Do not continue broad
bulk collection at the current serial speed before a performance packet lands.

Accepted WPR106-542 partial results:

- Added 17 append-only daily batches for ETH March 1-17, 2024.
- Each day accepted two official no-paid archives: one Binance USD-M
  aggregate-trade ZIP and one Bybit public trading GZIP.
- Added 170,000 normalized rows total: 85,000 `binance_usdm` orderflow rows
  and 85,000 `bybit_linear` trade rows.
- All accepted WPR106-542 batches reported zero duplicate rows and zero source
  blockers.
- The oversized first ETH week-one attempt produced an unmanifested raw JSONL
  and no normalized Parquet or batch manifest. That orphan raw output was
  removed after stopping the process. The raw source archives remained valid
  and were then written as daily manifests.

Current central-store state at pause:

- 3218 files.
- 28316202467 bytes, approximately 26.372 GiB.
- 71 append-manifest rows.
- 8,163,343 normalized rows.
- Provider rows: `binance_usdm=5465980`, `bybit_linear=2011913`,
  `binance_spot=352384`, `bybit_inverse=178560`, `hyperliquid=144506`,
  `bybit_spot=10000`.
- Family rows: `orderflow=5220999`, `ohlcv=1412324`, `trade=1351000`,
  `metadata=179020`.

Remaining WPR106-541/WPR106-542 March continuation targets include ETH
March 18-31, BTC March 5-31, and full SOL/DOGE March 2024 Binance USD-M
aggregate-trade and Bybit public trading archives. Continue them only after
the next packet addresses collection throughput and cap wiring.

Updated direction:

- The local market-history storage cap is now intended to be 300 GiB.
- The current implementation still defaults to 150 GiB and must be updated
  before claiming 300 GiB enforcement.
- The next work should prioritize a parallel, atomic, manifest-safe downloader
  and batch writer before more long serial collection runs.
- The central market-history lane remains multi-provider and research-only.
  Strict Hyperliquid-only readiness remains out of this central data-readiness
  path and separate from Hyperliquid-native autonomous strategy readiness.

Validation was not rerun after this pause-only documentation handoff. Previous
WPR106-542 accepted batches were produced through existing central-store write
contracts. No `.part` files or active WPR106-542 collector process were present
at handoff inspection time; only unrelated local HTTP server Python processes
were present.
