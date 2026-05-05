# Stage R47 Crypto Lake Free Data Fallback Report

## Scope

WPR47 made Crypto Lake free sample data an explicit local fallback when Binance
Vision is insufficient. No provider credentials were added, documented, or
required, and no large provider fetch was run.

## Changes

- Added `docs/runbooks/crypto_lake_free_data_runbook.md` with install, free-sample, smoke-test, local-export, pipeline, and agent-use instructions.
- Added the optional `crypto-lake` package extra with `lakeapi>=0.22.3`.
- Added `.lake_cache/` to `.gitignore`.
- Updated README provider-intake notes to point to the Crypto Lake runbook.
- Added `CryptoLakeAccessError` so direct free-data fetches without `lakeapi` fail with setup guidance instead of a raw import error.
- Updated direct Crypto Lake fetches to call `lakeapi.use_sample_data(anonymous_access=True)` before loading data.
- Recorded free sample provenance in Crypto Lake fetch manifests with `source_access_mode: free_sample`.
- Added focused tests for the optional free-sample `lakeapi` fetch path and missing-dependency guidance.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite\research\market_data.py src\tradingbotsuite\research\data_pipeline.py src\tradingbotsuite\main.py
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_market_data_collection.py -q
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_data_pipeline.py tests\contracts\test_data_contracts.py -q
$env:PYTHONPATH='src'; python -m tradingbotsuite.main fetch-crypto-lake --help
$env:PYTHONPATH='src'; python -m tradingbotsuite.main fetch-crypto-lake --symbol BTCUSDT --provider-symbol BTC-USDT-PERP --data-family kline --start-time "2025-04-06" --end-time "2025-04-07" --exchange BINANCE_FUTURES --table candles --interval 1m --output-dir data/research/market_data/crypto_lake/free_sample_smoke --strict
```

Results:

- `tests/tradingbotsuite/test_market_data_collection.py`: 18 passed.
- `tests/tradingbotsuite/test_data_pipeline.py tests/contracts/test_data_contracts.py`: 19 passed.
- `fetch-crypto-lake --help`: passed.
- Crypto Lake free sample smoke: passed with 1,440 rows, `gap_count: 0`, `duplicate_count: 0`, `source_access_mode: free_sample`, and `free_sample_data: true`.

## Boundary

Outputs remain research-only. The supported direct Crypto Lake fetch path uses
free sample data and does not require provider accounts, AWS profiles, or secret
credentials. If any credentials happen to exist locally, they must not be written
to repo files, manifests, logs, or agent messages.
