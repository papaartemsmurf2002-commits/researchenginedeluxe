# WPR32-01 Checked-In BTCUSDT Fixture Pack

Status: closed
Owner: Codex Research Agent
Stage: Stage R32 checked-in BTCUSDT fixture pack
Opened: 2026-05-04
Closed: 2026-05-04

## Objective

Add a durable checked-in BTCUSDT historical fixture pack and wire `configs/research/full_cycle_btc_v1.json` to consume it through the validated `historical_fixture_pack` manifest path, without synthetic fallback.

## Allowed paths

- `configs/research/full_cycle_btc_v1.json`
- `data/research/fixtures/btcusdt_v1/**`
- `.gitignore`
- `tests/contracts/test_historical_fixture_pack_contract.py`
- `tests/historical/test_full_cycle_local_fixture_pack.py`
- `tests/live/test_preflight.py`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR32-01-checked-in-btcusdt-fixture-pack.md`
- `docs/stage_reports/STAGE_R32_CHECKED_IN_BTCUSDT_FIXTURE_PACK_REPORT.md`

## Non-goals

- No live, paper, shadow, testnet, canary, promotion, order-placement, or capital allocation work.
- No provider download or network intake in this packet.
- No claim that the small fixture is statistically sufficient for candidate acceptance.
- No broad runner, feature builder, optimizer, or strategy refactor.

## Implementation plan

1. Create `data/research/fixtures/btcusdt_v1/fixture_pack_manifest.json` plus compact Parquet artifact families for cycle bars and required 15m bars.
2. Use deterministic checked-in fixture artifacts derived from local BTCUSDT Binance USD-M kline provider-cache data, with research-only, observe-only, promotion-ready-false metadata and sha256/row-count evidence.
3. Update `configs/research/full_cycle_btc_v1.json` to reference the fixture pack manifest through `dataset_manifest_paths` and set `synthetic_fixture: false`.
4. Add `.gitignore` exceptions so the checked-in fixture pack can actually be tracked under the ignored `data/` tree.
5. Add contract coverage validating the checked-in fixture pack manifest.
6. Add full-cycle config coverage proving the checked-in config consumes `source_type: historical_fixture_pack` and does not fall back to synthetic/local-dir evidence.
7. Add no-fallback coverage for missing checked-in manifest evidence.
8. Record validation evidence and close the packet.

## Exit criteria

- Checked-in fixture pack manifest validates with `assert_valid_historical_fixture_pack_manifest`.
- `configs/research/full_cycle_btc_v1.json` resolves to the checked-in manifest and has synthetic fallback disabled.
- A focused full-cycle test using the checked-in config reports `data_source.source_type == historical_fixture_pack`, `synthetic == false`, and fixture validation evidence.
- Focused fixture/full-cycle tests, live preflight, compile, contracts, and diff check pass.

## Completion evidence

- Added checked-in fixture artifacts under `data/research/fixtures/btcusdt_v1/`: `cycle_dataset.parquet`, `bars_15m.parquet`, and `fixture_pack_manifest.json`.
- Fixture provenance is Binance USD-M kline provider cache (`binance_rest` / `binance_usdm_klines`), with `tradingview_source_used: false` and `synthetic_source_used: false`.
- Optional lower-timeframe and context families are omitted truthfully because the provider OHLCV cache does not contain those families.
- `.gitignore` exceptions make the BTCUSDT fixture pack trackable under the otherwise ignored `data/` tree.
- `configs/research/full_cycle_btc_v1.json` consumes the checked-in manifest through `dataset_manifest_paths`, with `local_fixture_dir: null` and `synthetic_fixture: false`.
- Contract and historical tests validate the manifest, embedded Parquet provenance, full-cycle consumption, optional-family absence, and fail-closed missing-manifest behavior.

## Validation

- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_historical_fixture_pack_contract.py tests\historical\test_full_cycle_local_fixture_pack.py -q` passed: 14 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q` passed: 24 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 77 tests.
- `git check-ignore -q data\research\fixtures\btcusdt_v1\fixture_pack_manifest.json` returned exit code 1, confirming the fixture pack is not ignored.
