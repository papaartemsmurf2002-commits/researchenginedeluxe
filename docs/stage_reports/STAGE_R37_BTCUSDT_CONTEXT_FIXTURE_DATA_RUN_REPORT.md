# Stage R37 BTCUSDT Context Fixture Data Run Report

Date: 2026-05-04
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR37-01-btcusdt-context-fixture-data-run.md`
Status: closed

## Scope

WPR37 used the research-only provider tools to collect a small BTCUSDT Binance USD-M context dataset and build a generated context-aware fixture pack.

The packet did not use TradingView exports, Pine files, legacy parity files, live execution, paper/shadow/testnet/canary flows, order placement, promotion, or candidate acceptance.

## Inputs

- Kline source manifest: `data/research/chart_ohlcv_cache/BTCUSDT_15m_1760450400000_1776178800000.manifest.json`
- Kline source hash: `ff86ed71921ddaead3a58a6205e4d4b04917960f1a1bd1a9d4c2ef6dbb97ec2e`
- Fixture tail window:
  - first primary bar: `1776050100000`
  - last primary bar: `1776178800000`
  - row count: 144

## Collected Context

Funding-rate collection:

- Path: `data/research/market_data/binance_usdm/wpr37_btcusdt_context_provider_v1/BTCUSDT/funding_rate/BTCUSDT_funding_rate_1776021300000_1776178800000.manifest.json`
- Rows: 5
- Content hash: `sha256:ecfb31b294d3c5b5c7a6641612a67055723b10eab78ea62936c4eb7a4a3876c0`
- Source: `binance_usdm_rest`

Premium-index collection:

- Path: `data/research/market_data/binance_usdm/wpr37_btcusdt_context_provider_v1/BTCUSDT/premium_index/15m/BTCUSDT_premium_index_15m_1776049200000_1776178800000.manifest.json`
- Rows: 145
- Content hash: `sha256:aeaef988d402b70725cef8f5f1cdf60317b87216cdfdd159f73bcd2ecb7dba7e`
- Source: `binance_usdm_rest`

Open-interest collection:

- Path: `data/research/market_data/binance_usdm/wpr37_btcusdt_context_provider_v1/BTCUSDT/open_interest/15m/BTCUSDT_open_interest_15m_1776049200000_1776178800000.manifest.json`
- Rows: 145
- Content hash: `sha256:65d7655303580df1106c57af4cef9a6129cca60238037ca1ae0c01fdf47f8818`
- Source: `binance_usdm_rest`

## Generated Fixture Pack

- Manifest: `data/research/fixtures/btcusdt_context_provider_v1/fixture_pack_manifest.json`
- Fixture ID: `btcusdt-context-provider-v1`
- Row count: 144
- Manifest SHA-256: `7c97dfb0abfd8459e72998815b8fee25af42aac78fd0e9bd1cf9ef3523e26464`
- Cycle dataset SHA-256: `2cc685578d8bda525dab72659e2bf95151e02ec9a46bcb5322484c174f3b47fa`
- Bars SHA-256: `a0f4bdba21b40511f1b0c097f4fa1d9835ea112e61229c935d0a480efc961823`
- Funding family SHA-256: `a64a08617feaa9cbe7af22b9a60f9016815b2e7d3d05221702fabe1073bebf12`
- Premium family SHA-256: `030cf2bd62a89eb5283dd11ca42681957b61265300d14c33534d75ee7ac242b2`
- Open-interest family SHA-256: `7f589b5d35f6d9ebe3b9516645789941ee47e2ad78f7985dc641b596d13a79b3`

Included optional context families:

- `funding_rate`
- `premium_index`
- `open_interest`

Omitted optional families:

- `agg_trade`
- `lower_timeframe_bars`

## Boundary Notes

- The generated fixture pack is `research_only`, `observe_only`, and `promotion_ready: false`.
- The generated fixture pack is not OOS acceptance evidence and is not sufficient for performance claims.
- The generated fixture pack uses provider REST context and local provider kline cache data.
- Artifact audit confirmed `tradingview_source_used: false`, `synthetic_source_used: false`, and no deprecated chart-export source text in artifact string values.
- Generated data paths remain under ignored research data directories and do not replace the checked-in `btcusdt_v1` fixture.

## Validation

- `collect-binance-context` succeeded for funding-rate, premium-index, and open-interest context manifests.
- `build-historical-fixture-pack` succeeded with the collected context manifests.
- Explicit fixture manifest validation through `assert_valid_historical_fixture_pack_manifest` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_historical_fixture_pack_contract.py -q` passed: 27 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 97 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q` passed: 26 tests.
- `git diff --check` reported only CRLF normalization warnings.

## Close Decision

Stage R37 is closed. The branch now has a generated BTCUSDT context-aware fixture pack built from local provider bars plus fresh Binance USD-M REST context manifests.
