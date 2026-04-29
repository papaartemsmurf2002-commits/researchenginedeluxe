# Data Agent: Provider-Aware Pipeline Intake

Date: 2026-04-29

## Task

Implement the provider-aware HMM/KNN research data intake path from the continuation plan.

## Work Done

- Added a research-only data pipeline coordinator with provider descriptors, local Binance Vision ingestion, diagnostic unsupported-provider manifests, canonical market journal assembly, and data-quality reporting.
- Added `configs/data/v2_btc_hmm_knn_provider_pipeline.json` as the BTC Phase 1 pipeline spec.
- Added `prepare-hmm-knn-research-data --stage intake` CLI wiring.

## Provider Status

- `binance_vision`: local CSV/ZIP ingestion implemented for `kline`, `trade`, and `agg_trade`.
- `crypto_lake`: descriptor registered; ingestion emits `not_implemented_for_ingestion`.
- `hyperliquid_archive`: descriptor registered; ingestion emits `not_implemented_for_ingestion`.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_data_pipeline.py -q
```

Result: `6 passed`.

## Boundary

No network downloader, live runtime hook, Hyperliquid execution hook, operator live control, or sizing behavior was added.

## Issues

No unresolved issue was added.
