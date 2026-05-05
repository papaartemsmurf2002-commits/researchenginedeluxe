# WPR47-01 Crypto Lake free-data fallback setup

## Objective

Make Crypto Lake free sample data an explicit research fallback when Binance Vision is insufficient.

## Scope

- Document local installation, free anonymous sample-data mode, smoke tests, and agent usage for Crypto Lake.
- Keep generated lakeapi cache/data ignored.
- Keep Crypto Lake as an optional dependency for local fallback collection.
- Make direct Crypto Lake fetches use free `lakeapi.use_sample_data(anonymous_access=True)` mode.
- Improve missing optional dependency failures with actionable setup guidance.

## Allowed paths

- `.gitignore`
- `README.md`
- `pyproject.toml`
- `configs/data/v2_btc_hmm_knn_provider_pipeline.json`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/research/data_pipeline.py`
- `src/tradingbotsuite/research/market_data.py`
- `tests/tradingbotsuite/test_market_data_collection.py`
- `docs/runbooks/crypto_lake_free_data_runbook.md`
- `docs/work_packets/WPR47-01-crypto-lake-access-setup.md`
- `docs/stage_reports/STAGE_R47_CRYPTO_LAKE_FREE_DATA_FALLBACK_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Non-goals

- Do not document or require provider accounts, AWS profiles, or secret credentials.
- Do not fetch large Crypto Lake datasets as part of this packet.
- Do not promote research artifacts or change live runtime behavior.
- Do not add Crypto Lake as a mandatory install dependency.

## Validation plan

```powershell
python -m compileall -q src/tradingbotsuite/research/market_data.py
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_market_data_collection.py -q
```
