# Next Agent Handoff - WPR106-542 Central Market-History Speedup

Date: 2026-06-26
Owner: Codex Research Agent
Status: superseded by WPR106-543

## Operator Direction

Superseded update: WPR106-543 implemented the requested speedup, changed the
active central market-history cap to 300 GiB, and completed the remaining ETH
March 18-31, BTC March 5-31, and full SOL/DOGE March 2024 collection targets.
This file is retained as historical handoff context for why WPR106-543 was
opened.

The operator changed the local market-history storage cap from 150 GiB to
300 GiB and stopped the current serial collection run because throughput is far
too slow. Do not continue broad bulk collection with the current serial
approach. The next packet should first make collection dramatically faster and
then resume data acquisition under a correctly enforced 300 GiB cap.

The central market-history data-readiness lane remains research-only and
multi-provider. Hyperliquid is preferred when usable, but strict
Hyperliquid-only readiness is out of this central market-history lane and must
not conflict with valid no-paid Binance/Bybit/Hyperliquid data readiness.

## Current Store State

Path: `data/research/central_market_history/**`

Measured at handoff:

- Files: 3218
- Bytes: 28316202467
- Size: approximately 26.372 GiB
- Append-manifest rows: 71
- Normalized rows: 8,163,343
- Handoff-time code cap: 150 GiB via `CENTRAL_MARKET_HISTORY_MAX_BYTES`
- Superseding WPR106-543 cap: 300 GiB, wired into code/tests/docs

Current row distribution:

- Providers: `binance_usdm=5465980`, `bybit_linear=2011913`,
  `binance_spot=352384`, `bybit_inverse=178560`, `hyperliquid=144506`,
  `bybit_spot=10000`.
- Families: `orderflow=5220999`, `ohlcv=1412324`, `trade=1351000`,
  `metadata=179020`.
- Timeframes: event/metadata rows without row timeframe at `6751019`,
  `1h=1251630`, `15m=116927`, `1d=43767`.
- Top symbols: `ETH=1001581`, `BTC=866521`, `BNB=814091`, `XRP=814090`,
  `DOGE=504091`, `SOL=504091`.

No `.part` files were present at handoff. No WPR106-542 collector process was
active. Only unrelated local Python HTTP server processes were present.

## Work Completed Before Handoff

WPR106-541 was completed before this packet:

- Added 660,000 normalized rows from 132 official no-paid Binance USD-M and
  Bybit public March 2024 archives.
- Accepted BTC March 1-4, full BNB March, and full XRP March.
- Recorded exact `deferred_next_packet` source URLs for BTC March 5-31 plus
  full ETH, SOL, and DOGE March.
- Final WPR106-541 store state was 25.014 GiB, 54 append-manifest rows, and
  7,993,343 normalized rows.

WPR106-542 partial work accepted:

- ETH March 1-17, 2024.
- 17 daily append-only batches.
- Each day used one Binance USD-M aggregate-trade ZIP and one Bybit public
  trading GZIP.
- 170,000 normalized rows added.
- Zero blockers and zero duplicates in accepted WPR106-542 batches.

WPR106-542 accepted run IDs:

- `wpr106-542-eth-mar2024-01-trade-orderflow`
- `wpr106-542-eth-mar2024-02-trade-orderflow`
- `wpr106-542-eth-mar2024-03-trade-orderflow`
- `wpr106-542-eth-mar2024-04-trade-orderflow`
- `wpr106-542-eth-mar2024-05-trade-orderflow`
- `wpr106-542-eth-mar2024-06-trade-orderflow`
- `wpr106-542-eth-mar2024-07-trade-orderflow`
- `wpr106-542-eth-mar2024-08-trade-orderflow`
- `wpr106-542-eth-mar2024-09-trade-orderflow`
- `wpr106-542-eth-mar2024-10-trade-orderflow`
- `wpr106-542-eth-mar2024-11-trade-orderflow`
- `wpr106-542-eth-mar2024-12-trade-orderflow`
- `wpr106-542-eth-mar2024-13-trade-orderflow`
- `wpr106-542-eth-mar2024-14-trade-orderflow`
- `wpr106-542-eth-mar2024-15-trade-orderflow`
- `wpr106-542-eth-mar2024-16-trade-orderflow`
- `wpr106-542-eth-mar2024-17-trade-orderflow`

## Mid-Work Results And Failure Mode

The first WPR106-542 attempt tried ETH March 1-7 as a weekly batch. It hit the
two-hour shell timeout and then remained CPU-bound for roughly another ten
minutes without producing a manifest. It created an unmanifested raw JSONL at:

`data/research/central_market_history/raw/wpr106-542-eth-mar2024-week1-trade-orderflow-fc9d62af66558183.jsonl`

That file was removed because it had no normalized Parquet, quality report, or
batch manifest. The already-downloaded source archives were validated as
proper ZIP/GZIP files and then written as daily batches.

Daily batches are safer but still too slow. ETH March 8-14 took about 1 hour
42 minutes for only 70,000 normalized rows. At that rate, continuing all
remaining source families and symbols would take far too long.

## Likely Bottlenecks

- Downloads are serial: one HEAD/GET/source at a time.
- Parsing/writing is serial and Pydantic-heavy for every normalized row.
- Large weekly batches can spend a long time in row validation, hashing, raw
  JSONL writing, and Parquet writing without a manifest boundary.
- No job-level progress telemetry is written during long local scripts.
- No atomic `.part` convention is currently used by `download_source_plan`;
  interrupted files were manually detected and removed in WPR106-541.
- At handoff, the cap was a module-level default of 150 GiB rather than a
  300 GiB operator policy; WPR106-543 supersedes this with a 300 GiB default.

## Next-Agent Goal

Goal for the next agent:

Build a dramatically faster, manifest-safe central market-history collection
path before resuming bulk data collection. Update the storage cap to 300 GiB
consistently, then implement and validate a bounded parallel collector that can
download, verify, parse, and append official no-paid provider archives with
atomic writes, provenance, checksums, source-discovery reports, quality
reports, and research-only boundary flags intact.

Concrete success criteria:

- Replace or supplement ad hoc serial inline scripts with a reusable
  `central_market_history_collection` orchestration helper.
- Support controlled parallel downloads with a configurable concurrency limit
  such as 4-8 simultaneous files.
- Use atomic raw downloads: write to a temporary `.part` file, validate ZIP/GZIP
  integrity, then rename into final `raw_sources/**` only after success.
- Prevent partial files from being treated as cache hits.
- Reserve or recheck storage budget safely against the 300 GiB cap before and
  during concurrent downloads.
- Keep append-only batch manifests deterministic and idempotent.
- Prefer smaller append boundaries, such as per-day or small day-group
  manifests, unless a tested writer can batch larger groups without long CPU
  stalls.
- Emit progress telemetry or a machine-readable collection summary while a
  long run is active.
- Add focused tests for atomic partial cleanup, cache-hit behavior, budget
  enforcement, parallel plan execution, and unchanged research-only flags.
- Run central tests, focused provider/storage tests, contracts, `tests/v2`,
  `git diff --check`, and boundary scans before resuming large collection.

After the speed packet passes, resume remaining WPR106-541/WPR106-542 March
targets:

- ETH March 18-31 Binance USD-M aggTrade and Bybit public trading archives.
- BTC March 5-31 Binance USD-M aggTrade and Bybit public trading archives.
- SOL March 1-31 Binance USD-M aggTrade and Bybit public trading archives.
- DOGE March 1-31 Binance USD-M aggTrade and Bybit public trading archives.

## Required Boundary

Every new artifact and helper must preserve:

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

No candidate-pack, paper/live, order, sizing, runtime-mode, promotion,
autonomous strategy, or production trading readiness should be introduced.

## Suggested Packet Shape

Open `WPR106-543-v2-central-market-history-speedup-300gb.md` or equivalent.
Allowed paths should include:

- New work packet.
- This handoff, if updating it.
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/v2/data_sources/central_market_history.py`
- `src/tradingbotsuite/v2/data_sources/central_market_history_collection.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `tests/v2/test_central_market_history_store_phase76.py`
- `tests/v2/test_central_market_history_collection_phase77.py`
- Generated central-market-history artifacts only if the packet resumes
  collection after speed validation.

Keep all live/order/sizing/runtime/promotion/candidate-pack paths out of scope.
