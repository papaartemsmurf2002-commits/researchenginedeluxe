# WPR106-549 v2 Project OF-Style Data Expansion

Status: validated
Owner: Codex Research Agent
Branch role: research/v3-experimental-engine, v2 research-only data-first archive

## Objective

Obtain and validate additional official no-paid OF-style data for the 29
project symbols that were validated as Hyperliquid-tradable and already
complete for project-needed 1m bars. Prefer the highest-gain, lowest-risk
collector changes first: reuse the central market-history bounded downloader,
add missing Binance Vision USD-M source-family support where needed, and write
large event/order-book batches through a faster append-only path.

## Scope

Symbols:

`AAVE`, `ADA`, `AERO`, `AVAX`, `BNB`, `BTC`, `DOGE`, `ENA`, `ETH`,
`FARTCOIN`, `HYPE`, `IP`, `JTO`, `JUP`, `KPEPE`, `LINK`, `LIT`, `NEAR`,
`PUMP`, `SOL`, `SUI`, `TAO`, `UNI`, `VVV`, `WLD`, `XMR`, `XPL`, `XRP`, `ZEC`.

Source families:

- Binance Vision USD-M `aggTrades`: trade-flow/orderflow proxy already modeled;
  collect or re-normalize uncapped rows where budget-safe.
- Binance Vision USD-M `trades`: raw trade prints; add central support before
  collection.
- Binance Vision USD-M `bookDepth`: daily depth snapshots; add central support
  before collection.
- Binance Vision USD-M `bookTicker`: official BBO stream archive; discover and
  size, but collect only when the 300 GiB central-store cap can be preserved.
- Binance Vision USD-M daily `klines`, `indexPriceKlines`,
  `markPriceKlines`, `premiumIndexKlines`, and `metrics`: collect as
  raw-heavy comparison/context archives in the operator-specified external
  archive, not in the capped central store unless a later packet adds a compact
  normalized representation.
- Existing Bybit public trade rows may remain comparable trade evidence where
  already collected; this packet does not prioritize new Bybit expansion unless
  Binance source discovery blocks.

Out of scope:

- Hyperliquid official S3 network downloads requiring requester-pays/operator
  gates.
- Paid, authenticated, synthetic, fixture-only, or sandbox data.
- Live, paper, order-placement, sizing, runtime-mode, candidate-pack, or
  promotion behavior.
- Rewriting old evidence artifacts. New central market-history artifacts are
  append-only.

## Allowed Paths

- `docs/work_packets/WPR106-549-v2-project-of-style-data-expansion.md`
- `docs/NEXT_AGENT_HANDOFF_WPR106_549_OF_STYLE_DATA_EXPANSION.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/v2/data_sources/central_market_history.py`
- `src/tradingbotsuite/v2/data_sources/central_market_history_collection.py`
- `tests/v2/test_central_market_history*.py`
- `data/research/central_market_history/**` append-only artifacts for this
  packet, including raw source files, normalized Parquet, manifests, source
  discovery reports, quality reports, telemetry, and validation reports.
- `M:\additional_archive\researchenginedeluxe\wpr106_549_of_style_raw\**`
  operator-specified external raw-heavy archive for OF-style downloads that do
  not fit the central store cap.

## No-Touch Review

This packet does not touch live runtime, order placement, sizing/runtime
configuration, promotion/shadow paths, candidate-pack truth layers, old checked
fixture evidence, legacy high-return outputs, legacy GUI paths, or secrets.
Generated central market-history artifacts are append-only and preserve existing
manifests.

## Implementation Plan

1. Inventory existing OF-style coverage for the 29 symbols from append
   manifests, quality reports, raw refs, checksums, and partial-file state.
2. Add central source plans/parsers for Binance USD-M `trades`, `bookDepth`,
   and optionally `bookTicker` if needed for bounded collection.
3. Add or reuse a faster event/book writer with atomic `.part` Parquet writes,
   manifest hashes, quality reports, source metadata, and research-only flags.
4. Build source-discovery reports with official URL, HTTP status, bytes,
   checksum availability, source family, symbol, date/month, existing-cache
   status, and budget impact.
5. Run bounded parallel collection in budget-safe batches with controlled
   download concurrency and per-batch append boundaries.
6. Validate no `.part` files, checksum/hash integrity, schema/readiness flags,
   source coverage, row counts, and 300 GiB storage cap.

## Implementation Evidence

- Added bounded external raw-heavy archive collection support in
  `data/research/central_market_history/manifests/wpr106-549-heavy-raw-downloader.py`
  for Binance Vision USD-M daily `bookDepth`, `aggTrades`, `bookTicker`,
  `trades`, `metrics`, `klines`, `markPriceKlines`, `indexPriceKlines`, and
  `premiumIndexKlines`.
- The downloader writes to
  `M:\additional_archive\researchenginedeluxe\wpr106_549_of_style_raw` by
  default, keeps the central 300 GiB cap out of scope for that operator
  archive, uses atomic `.part` downloads, ZIP/size/checksum checks, SHA-256
  sidecars, source metadata sidecars, progress JSONL, per-batch reports, and
  canonical research-only boundary flags.
- Added repeat-until-done batches and run labels for resumable collection.
  Added `WPR106549_HEAVY_SYMBOLS` / `WPR106549_HEAVY_EXCLUDE_SYMBOLS` filters
  so large trade-family collection can be split into disjoint symbol shards
  without overlapping `.part` writers.
- Source discovery for the external heavy families produced 1,091,050 official
  no-paid Binance Vision USD-M source rows across `metrics`, `klines`,
  `markPriceKlines`, `indexPriceKlines`, and `premiumIndexKlines`. Legacy
  packet discovery reports cover `bookDepth`, `aggTrades`, `bookTicker`, and
  `trades`.
- Final consolidated external archive validation report:
  `M:\additional_archive\researchenginedeluxe\wpr106_549_of_style_raw\manifests\wpr106-549-heavy-raw-archive-validation-report.json`.
  It reports 1,159,478/1,159,478 complete sources, 0 missing, 0 invalid, and
  0 `.part` files.
- Fresh validation rerun on 2026-06-27 wrote the same report with
  `created_at=2026-06-27T09:25:28.927445+00:00`, 0 missing sources, 0 invalid
  sources, 0 missing metadata sidecars, 0 missing SHA-256 sidecars, and
  0 `.part` files.

Validated complete sources by family:

| Family | Complete sources |
| --- | ---: |
| `aggTrades` | 22,256 |
| `bookDepth` | 22,236 |
| `bookTicker` | 1,680 |
| `indexPriceKlines` | 266,652 |
| `klines` | 267,384 |
| `markPriceKlines` | 267,384 |
| `metrics` | 22,282 |
| `premiumIndexKlines` | 267,348 |
| `trades` | 22,256 |

## Validation

Focused validation:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_central_market_history*.py -q
```

Collection validation:

- Packet source-discovery report exists and has checksum/hash sidecar.
- Packet collection/quality report has `research_only: true`,
  `observe_only: true`, `promotion_ready: false`,
  `candidate_pack_eligible: false`, `live_signal: false`,
  `paper_signal: false`, `sizing_instruction: false`,
  `order_placement_instruction: false`, and `runtime_mode_change: false`.
- No successful source uses paid or requester-pays access.
- No `.part` files remain under `data/research/central_market_history/**`.
- No `.part` files remain under
  `M:\additional_archive\researchenginedeluxe\wpr106_549_of_style_raw\**`.
- Central market-history budget remains within 300 GiB.

## Risk Notes

- Full `bookTicker`, raw `trades`, and all nested interval kline archive
  families can exceed local central-store budget quickly, especially for
  BTC/ETH. They must remain budget-gated before central-store collection.
- As of the operator update, raw-heavy OF-style data may be downloaded to
  `M:\additional_archive` without applying the central market-history 300 GiB
  cap. Central normalized append artifacts still keep their own budget and
  quality constraints.
- Binance `aggTrades` and `bookDepth` are likely the best first expansion path:
  high research value and much smaller storage impact than full BBO ticks.
- Hyperliquid-native historical L2/trade archives remain unavailable in
  strict-zero-dollar mode without operator-gated requester-pays S3 access.
