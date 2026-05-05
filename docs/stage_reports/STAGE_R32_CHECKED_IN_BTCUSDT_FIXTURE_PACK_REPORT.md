# Stage R32 Checked-In BTCUSDT Fixture Pack Report

Date: 2026-05-04
Packet: `docs/work_packets/WPR32-01-checked-in-btcusdt-fixture-pack.md`
Status: complete

## Summary

Stage R32 adds a small checked-in BTCUSDT historical fixture pack and wires `configs/research/full_cycle_btc_v1.json` to consume it through the validated `historical_fixture_pack` manifest path with synthetic fallback disabled.

The fixture is intentionally narrow. It is a compact contract and full-cycle execution fixture, not OOS acceptance, stress, profitability, promotion, or performance evidence.

## Implementation

- Added `data/research/fixtures/btcusdt_v1/fixture_pack_manifest.json`.
- Added `data/research/fixtures/btcusdt_v1/cycle_dataset.parquet`.
- Added `data/research/fixtures/btcusdt_v1/bars_15m.parquet`.
- Added `.gitignore` exceptions so the BTCUSDT fixture pack can be tracked under the otherwise ignored `data/` tree.
- Updated `configs/research/full_cycle_btc_v1.json` to resolve the checked-in fixture pack manifest through `dataset_manifest_paths`, with `local_fixture_dir: null` and `synthetic_fixture: false`.
- Added contract coverage for the checked-in manifest, embedded Parquet provider provenance, and truthful absence of optional lower-timeframe/context families.
- Added full-cycle coverage proving the checked-in config consumes `source_type: historical_fixture_pack`, avoids synthetic fallback, and fails closed when the manifest is missing.

## Provenance

The checked-in fixture is derived from the local BTCUSDT Binance USD-M kline provider cache:

- Source manifest: `data/research/chart_ohlcv_cache/BTCUSDT_15m_1760450400000_1776178800000.manifest.json`
- Source mapping: `binance_usdm_klines` maps to registered `binance_rest` kline source through the data contract.
- Source row count: 17,477
- Source SHA256: `ff86ed71921ddaead3a58a6205e4d4b04917960f1a1bd1a9d4c2ef6dbb97ec2e`
- Fixture derivation: contiguous tail slice, 144 rows

The fixture manifest records `tradingview_source_used: false` and `synthetic_source_used: false`. TradingView exports and deterministic synthetic datasets were not used for the final checked-in pack.

## Limitations

- The fixture is OHLCV-only. Lower-timeframe bars, funding, premium, open-interest, and aggregate-trade families are omitted because the local provider cache used for this packet does not contain those families.
- The fixture is not statistically sufficient for candidate acceptance.
- The fixture is not promotion-ready and cannot be used as a live, paper, shadow, testnet, canary, order-placement, or position-sizing input.
- No provider download or network intake was performed in this packet.

## Validation

- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_historical_fixture_pack_contract.py tests\historical\test_full_cycle_local_fixture_pack.py -q` passed: 14 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q` passed: 24 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 77 tests.
- `git check-ignore -q data\research\fixtures\btcusdt_v1\fixture_pack_manifest.json` returned exit code 1, confirming the fixture pack is trackable.
- Review agent found no blockers after fixture replacement and test hardening.

## Decision

Stage R32 is complete. Continue holding before empirical acceptance and Stage 13 execution. The checked-in fixture improves reproducibility and full-cycle test coverage, but does not change the research-only boundary or promotion readiness.
