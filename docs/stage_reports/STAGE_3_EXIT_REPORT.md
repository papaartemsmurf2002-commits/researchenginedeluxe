# Stage 3 Exit Report

Stage: Stage 3 - Data architecture and normalized research store
Branch: `research/v3-experimental-engine`
Decision: complete
Date: 2026-05-01
Orchestrator: Codex

## Completed work packets

- WP3-01-data-manifest-consolidation

## Validation commands run

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.main collect-binance-bars --help
$env:PYTHONPATH='src'; python -m tradingbotsuite.main fetch-binance-vision --help
$env:PYTHONPATH='src'; python -m tradingbotsuite.main fetch-crypto-lake --help
$env:PYTHONPATH='src'; python -m tradingbotsuite.main prepare-hmm-knn-research-data --help
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_data_contracts.py tests/integration/test_provider_intake_smoke.py tests/contracts/test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_archive_sources.py tests/tradingbotsuite/test_data_quality.py tests/tradingbotsuite/test_data_pipeline.py tests/tradingbotsuite/test_market_data_collection.py tests/tradingbotsuite/test_research.py -q
```

## Results

- CLI help checks passed for `collect-binance-bars`, `fetch-binance-vision`, `fetch-crypto-lake`, and `prepare-hmm-knn-research-data`.
- `python -m compileall -q src/tradingbotsuite`: passed.
- New data contract, provider smoke, and import-boundary tests passed, 12 tests.
- Existing archive/data pipeline/research tests passed, 58 tests.

## Artifacts produced

- `src/tradingbotsuite/data/__init__.py`
- `src/tradingbotsuite/data/contracts.py`
- `src/tradingbotsuite/data/quality.py`
- `src/tradingbotsuite/data/providers/binance_rest.py`
- `src/tradingbotsuite/data/providers/binance_vision.py`
- `src/tradingbotsuite/data/providers/crypto_lake.py`
- `src/tradingbotsuite/data/providers/hyperliquid_archive.py`
- `src/tradingbotsuite/data/storage/parquet_store.py`
- `tests/contracts/test_data_contracts.py`
- `tests/integration/test_provider_intake_smoke.py`

## Known issues

- ISSUE-R1-001 remains open for later live-boundary enforcement.
- ISSUE-R1-002 remains open for Stage 10 live-mode research job rejection.

## Carry-forward debt

- Stage 4 must build point-in-time feature manifests on top of the normalized data manifest contract.
- `collect-binance-bars` still writes the historical research JSONL manifest for backward compatibility; the new normalized Parquet intake path is under `tradingbotsuite.data.providers.binance_rest`.
- Hyperliquid archive ingestion is registered-only and diagnostic in Stage 3.

## Decision rationale

Stage 3 is complete because at least one deterministic fixture dataset passes the full data contract, Binance kline intake writes partitioned Parquet plus manifest and data-quality report, Binance Vision and Crypto Lake local ingestion remain tested, Hyperliquid archive is explicitly registered-only, and no strategy optimization depends on unvalidated data.
