# Stage R106 Completed Catalog Wiring Validation Report

Date: 2026-05-22
Work packet: `docs/work_packets/WPR106-05-completed-catalog-wiring-validation.md`

## Summary

Validated the completed R106 historical-data catalog:

`data/research/operator_runs/historical_data/refresh-historical-data-catalog-4dfa2700192f4b6fa1fa8fe833668cfb/historical_data_catalog.json`

The catalog is complete and candidate-depth ready for BTCUSDT and ETHUSDT:

- Period coverage: `2020-01` through `2026-04` inclusive.
- Archive progress: `456/456` steps, `100.0%`.
- BTCUSDT: `221,952` 15m bars, `3,329,280` 1m bars, `3,291,128`
  agg-trade proxy rows, `55,488` effective hours.
- ETHUSDT: `221,952` 15m bars, `3,329,280` 1m bars, `3,317,494`
  agg-trade proxy rows, `55,488` effective hours.
- Each symbol has 228 checksum-verified Binance Vision monthly archive inputs:
  76 `15m` kline ZIPs, 76 `1m` kline ZIPs, and 76 `aggTrades` ZIPs.
- Generated active readiness, cycle, and exact-discovery specs exist under the
  completed catalog output tree.

## Fixes

Final validation found stale R104-only wiring after catalog completion. The
operator could correctly read the catalog, but progress and artifact filters
still treated only R104 hard-coded cycle/discovery IDs as required evidence.
That would have made the generated candidate-depth active specs look stale after
running them.

The operator now:

- Derives required cycle and exact-discovery IDs from active catalog readiness.
- Accepts generated `exact_entry_sweep_*_candidate_depth_v1` specs as stable,
  resumable exact-discovery runs.
- Shows generated candidate-depth cycle/discovery artifacts as required current
  evidence in the Research UI.
- Primes BTC controls from the active catalog when no local UI override exists.
- Recovers interrupted DB jobs left in `running` state at operator startup.

The current local DB was also cleaned: stale `run-discovery` and
`optimize-entry-gates` jobs from prior sessions were marked failed with
`stale_running_job_recovered_after_operator_restart`; no jobs remain in
`running` state.

## Provider Quality Review

Binance Vision remains the correct implemented active source for this branch's
current required BTC/ETH candidate-depth fixture path. The official Binance
public-data repository documents daily/monthly downloadable public market data,
USD-M futures kline and aggTrade schemas aligned with `/fapi` endpoints, and
per-ZIP `.CHECKSUM` sidecars for SHA-256 verification. It also notes archive
files may be corrected later, so retaining checksums/manifests is required.

Crypto Lake is a stronger future microstructure source where licensed access is
available: it offers trades, high-frequency order book snapshots, 1m candles,
funding, open interest, liquidations, and received-time columns. The current
catalog correctly keeps it as local-export/credential dependent rather than
silently substituting sample data.

Bybit has official recent-trade and kline APIs plus an official historical-data
download page, and Tardis documents broader Bybit derivative history from
2019/2020 with trades, quotes, L2, and liquidation samples. It remains an
expansion source until a normalized downloader/parser and validation contract
are implemented.

Hyperliquid official archive data is useful but not a direct replacement for the
current BTC/ETH Binance fixture path: its docs say requester-pays S3 archive
data may be missing or not timely, L2 snapshots and asset contexts are the
market-data S3 products, and fills/node data use multiple formats. The current
catalog correctly keeps Hyperliquid as a registered requester-pays expansion
surface until parser and reconciliation work exists.

## Boundaries

All catalog and fixture outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. This work validates data readiness and UI/API wiring;
it does not claim profitable candidates, write candidate packs, place orders,
change live runtime configuration, or change sizing.

## Validation

- Completed-catalog validation script: `VALIDATION_OK`
- Central cache count check: BTCUSDT and ETHUSDT each have 76 `15m`, 76 `1m`,
  and 76 `aggTrades` ZIP/checksum/manifest triplets.
- Current operator DB status check: `35 succeeded`, `9 failed`, `0 running`.
- `python -m compileall -q src\tradingbotsuite`
- `PYTHONPATH=src python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`
- `PYTHONPATH=src python -m pytest tests\tradingbotsuite\test_market_data_collection.py -q`
- `PYTHONPATH=src python -m pytest tests\contracts -q`
- `PYTHONPATH=src python -m pytest -q`
