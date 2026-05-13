# Stage R103 Durable Public Archive Fixtures Report

Date: 2026-05-13
Branch: `research/v3-experimental-engine`
Packet: `docs/work_packets/WPR103-01-durable-public-archive-fixtures.md`

## Scope

R103 created compact BTCUSDT and ETHUSDT public-archive fixture packs from
Binance Vision USD-M daily archives. This is data-foundation work only. It does
not claim candidate-ready strategy performance, does not write candidate packs,
and does not change live execution, live config, runtime mode, order placement,
promotion authorization, or sizing behavior.

## Source Evidence

Source: Binance Vision public data archives at
`https://data.binance.vision/data/futures/um/daily/`. Binance's public-data
README documents the daily/monthly archive layout and kline/aggTrades file
families: [binance-public-data](https://github.com/binance/binance-public-data).

For each symbol, the fixture uses four declared windows:

- `trend_bull`: `2024-01-10T12:00:00Z/2024-01-10T14:00:00Z`
- `drawdown_bear`: `2024-03-05T16:00:00Z/2024-03-05T18:00:00Z`
- `range_chop`: `2024-05-15T12:00:00Z/2024-05-15T14:00:00Z`
- `high_vol_shock`: `2024-08-05T00:00:00Z/2024-08-05T02:00:00Z`

For each window and symbol, the generator downloaded and checksum-verified:

- 15m kline archive
- 1m kline archive
- aggTrades archive

Raw downloaded archives remain ignored under `data/research/market_data/`.
Checked-in fixtures preserve archive URLs, archive hashes, checksum evidence,
selected raw row counts, provider capability metadata, and window-selection
metadata in each fixture manifest.

## Fixture Outputs

BTCUSDT:

- Manifest:
  `data/research/fixtures/btcusdt_public_archive_multi_window_v1/fixture_pack_manifest.json`
- Manifest sha256:
  `c58a44a0a40a942a70f0202b5dc5e3c094139651c148a8b14f00475a1cd54983`
- Rows: 32 bars, 480 lower-timeframe bars, 480 aggTrade proxy rows
- Source selected aggTrade rows before 1m aggregation: 2,728,724

ETHUSDT:

- Manifest:
  `data/research/fixtures/ethusdt_public_archive_multi_window_v1/fixture_pack_manifest.json`
- Manifest sha256:
  `c4c8831ab3a1498616ed9b494070cc95e29babb8a7d0605615968c288eadf2ae`
- Rows: 32 bars, 480 lower-timeframe bars, 480 aggTrade proxy rows
- Source selected aggTrade rows before 1m aggregation: 2,590,226

The aggTrade family is intentionally compacted to a 1-minute trade-flow proxy
with `feature_claim_scope:
trade_flow_proxy_not_order_book_imbalance_or_ofi`. It is not L2/order-book
evidence.

## Issue Outcome

`ISSUE-R101-003` is resolved as a durable data-foundation blocker. Candidate
validation remains R104 work: historical cycles and discovery should be rerun
against these durable fixtures, and candidate packs must remain absent or
blocked unless all research gates pass.

## Validation

Passed:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_historical_fixture_pack_contract.py tests\contracts\test_data_contracts.py -q
# 57 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest -q
# 1337 passed, 1 skipped, 92 warnings

git diff --check
# passed with line-ending warnings only
```

## Boundary Statement

These fixtures remain `research_only`, `observe_only`, and
`promotion_ready: false`. They are compact research fixtures for repeatable
cycle/discovery validation, not OOS acceptance evidence, not Hyperliquid
fillability evidence, not live signals, and not promotion artifacts.
