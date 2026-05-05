# Crypto Lake Free Data Fallback Runbook

This runbook is for local research data collection on
`research/v3-experimental-engine`.

Crypto Lake is a fallback provider in this branch. Use Binance Vision first for
public archive coverage. Use Crypto Lake free sample data only when Binance
Vision is insufficient for a schema check, provider comparison, or small
diagnostic fallback.

## What Is Supported

- Local Crypto Lake-style export ingestion: `.csv`, `.json`, `.jsonl`, or `.parquet`.
- Direct free sample-data fetch through optional `lakeapi`.
- Supported normalized families: `kline`, `trade`, `funding_rate`, `open_interest`.
- Research-only output under ignored `data/` paths with manifests, hashes, gap checks, and duplicate checks.

Crypto Lake free sample output remains `research_only`, `observe_only`,
`promotion_ready: false`, and `diagnostic_only: true`. It is not live signal
evidence, fillability evidence, full provider coverage, or promotion evidence by
itself.

## Install

From a fresh clone:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,crypto-lake]"
```

The `crypto-lake` extra installs the optional `lakeapi` package only for local
fallback collection. It is not part of the base runtime install.

## Free Sample Mode

Direct Crypto Lake fetches in this repo use:

```python
lakeapi.use_sample_data(anonymous_access=True)
```

No Crypto Lake provider account, AWS profile, access key, or secret key is
required for the supported direct fetch path.

The repo ignores `.env`, `.env.*`, `data/`, and `.lake_cache/`. Agents must still
avoid printing environment values, local paths with tokens, or downloaded raw
data content.

## Access Smoke Test

First confirm the optional dependency is importable:

```powershell
@'
import importlib.util
print("lakeapi_available=", importlib.util.find_spec("lakeapi") is not None)
'@ | python -
```

Then run the verified free-sample fetch:

```powershell
$env:PYTHONPATH="src"

python -m tradingbotsuite.main fetch-crypto-lake `
  --symbol BTCUSDT `
  --provider-symbol BTC-USDT-PERP `
  --data-family kline `
  --start-time "2025-04-06" `
  --end-time "2025-04-07" `
  --exchange BINANCE_FUTURES `
  --table candles `
  --interval 1m `
  --output-dir data/research/market_data/crypto_lake/free_sample_smoke `
  --strict
```

Verified locally on 2026-05-05: this command wrote 1,440 one-minute rows with
`gap_count: 0`, `duplicate_count: 0`, `source_access_mode: free_sample`, and
`free_sample_data: true`.

If the result is empty, check Crypto Lake free-data coverage for the exact table,
symbol, and date. Free sample data is intentionally limited and may not contain
the same perpetual symbols or windows as full provider coverage.

## Local Export Ingestion

Use this path when you already have a non-secret local export. Avoid paths that
contain tokens, signed URLs, access keys, or customer identifiers because the
manifest records `source_path` for reproducibility.

```powershell
$env:PYTHONPATH="src"

python -m tradingbotsuite.main fetch-crypto-lake `
  --symbol BTCUSDT `
  --provider-symbol BTC-USDT `
  --data-family kline `
  --path C:\local\crypto_lake\btcusdt_1m.csv `
  --interval 1m `
  --output-dir data/research/market_data/crypto_lake/local_exports `
  --strict
```

## Pipeline Input Example

Add inputs to `configs/data/v2_btc_hmm_knn_provider_pipeline.json` only as a
fallback after Binance Vision coverage has been checked:

```json
{
  "source_name": "crypto_lake",
  "enabled": true,
  "inputs": [
    {
      "symbol": "BTCUSDT",
      "provider_symbol": "BTC-USDT-PERP",
      "data_family": "kline",
      "interval": "1m",
      "fetch": {
        "start_time": "2025-04-06",
        "end_time": "2025-04-07",
        "exchange": "BINANCE_FUTURES",
        "table": "candles"
      },
      "strict": true
    }
  ]
}
```

Then run:

```powershell
$env:PYTHONPATH="src"
python -m tradingbotsuite.main prepare-hmm-knn-research-data `
  --spec configs/data/v2_btc_hmm_knn_provider_pipeline.json `
  --stage intake
```

## Agent Rules

- Prefer Binance Vision for public archive data.
- Use Crypto Lake free sample data only as a fallback for schema checks, provider comparison, or missing Binance Vision coverage.
- Do not add provider-account, AWS, or secret-credential setup to this branch.
- Do not commit or print credentials if they happen to exist in the local environment.
- Start with one-day smoke ranges before larger windows.
- Use `--strict` for kline/fixed-interval quality checks.
- Keep generated data under ignored `data/` paths.
- Report manifest paths, row counts, gaps, duplicates, source hashes, and `source_access_mode`.
- Treat all outputs as research-only until a later promotion process changes that.

## References

- Crypto Lake free data: https://crypto-lake.com/free-data/
- Lake API installation: https://lake-api.readthedocs.io/en/latest/installation.html
- Lake API usage: https://lake-api.readthedocs.io/en/latest/usage.html
- Lake API package reference: https://lake-api.readthedocs.io/en/stable/lakeapi.html
