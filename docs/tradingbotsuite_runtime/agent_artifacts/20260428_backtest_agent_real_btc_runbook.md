# Agent name

Backtest Agent

# Task received

Prepare the real-data validation command path.

Requested commands:

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.main research-hmm-knn --help
$env:PYTHONPATH='src'; python -m tradingbotsuite.main monitor-hmm-knn --help
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_hmm_knn.py -q
```

Tasks:

- Define the exact command template for running `research-hmm-knn` on a real local BTC dataset once Data Agent identifies it.
- Define expected output directory under `data/research/<plan_version>/`.
- Do not run on live exchange data.

# Files read

- `src/tradingbotsuite/main.py`
- `configs/v2_btc_hmm_multi_knn_research.json`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_real_btc_runbook.md`

# Commands/tests run

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.main research-hmm-knn --help
```

Exit code: `0`

Exact output:

```text
usage: python.exe -m tradingbotsuite.main research-hmm-knn [-h]
                                                           --config CONFIG
                                                           [--dataset DATASET]
                                                           [--output-dir OUTPUT_DIR]

options:
  -h, --help            show this help message and exit
  --config CONFIG
  --dataset DATASET
  --output-dir OUTPUT_DIR
```

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.main monitor-hmm-knn --help
```

Exit code: `0`

Exact output:

```text
usage: python.exe -m tradingbotsuite.main monitor-hmm-knn [-h]
                                                          --manifest MANIFEST

options:
  -h, --help           show this help message and exit
  --manifest MANIFEST
```

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_hmm_knn.py -q
```

Exit code: `0`

Exact result:

```text
.......................                                                  [100%]
23 passed in 12.84s
```

# Real BTC local dataset command template

Use this only after the Data Agent identifies a real local point-in-time BTC dataset parquet file. Do not use this template to fetch live exchange data.

```powershell
$env:PYTHONPATH='src'
$REAL_BTC_DATASET='C:\absolute\path\to\real_btcusdt_dataset.parquet'
python -m tradingbotsuite.main research-hmm-knn `
  --config configs/v2_btc_hmm_multi_knn_research.json `
  --dataset $REAL_BTC_DATASET `
  --output-dir data/research
```

Expected plan version from `configs/v2_btc_hmm_multi_knn_research.json`:

```text
v2-btc-hmm-multi-knn-1
```

Expected output directory:

```text
data/research/v2-btc-hmm-multi-knn-1/
```

Expected files:

- `data/research/v2-btc-hmm-multi-knn-1/artifact_manifest.json`
- `data/research/v2-btc-hmm-multi-knn-1/walk_forward_metrics.json`
- `data/research/v2-btc-hmm-multi-knn-1/regime_posteriors.parquet`
- `data/research/v2-btc-hmm-multi-knn-1/knn_predictions.parquet`
- `data/research/v2-btc-hmm-multi-knn-1/meta_predictions.parquet`
- `data/research/v2-btc-hmm-multi-knn-1/neighbor_diagnostics.csv`

# Monitoring command template

After the research command writes `artifact_manifest.json`, run:

```powershell
$env:PYTHONPATH='src'
python -m tradingbotsuite.main monitor-hmm-knn `
  --manifest data/research/v2-btc-hmm-multi-knn-1/artifact_manifest.json
```

Expected monitoring output:

```text
data/research/v2-btc-hmm-multi-knn-1/monitoring_report.json
```

The report must remain:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`

# Decisions made

- Verified CLI help instead of running a real-data research job.
- Defined `--output-dir data/research` so the implementation writes under `data/research/<plan_version>/`.
- Kept the dataset path as an explicit local file placeholder owned by the Data Agent handoff.
- Did not run live exchange data, live data fetching, live execution, sizing, gates, Hyperliquid behavior, safety behavior, or operator live controls.

# Assumptions

- Data Agent will provide an absolute local parquet path containing BTCUSDT rows compatible with the HMM/KNN config and required label/feature fields.
- The real local dataset is already point-in-time aligned and does not require network calls at Backtest Agent runtime.

# Open issues or blockers

- Waiting on Data Agent to identify or produce the real local BTC dataset path.
- No blocker for the command path itself; help and focused tests passed.

# Handoff notes for other agents

- Backtest Agent should not run the real-data command until the Data Agent provides a local dataset path and confirms its point-in-time contract.
- A successful run is still research-only. It does not imply positive expectancy or live readiness.
- After the run, evaluate `walk_forward_metrics.json` for trade count, expectancy after fees/slippage/funding, long/short breakout, split concentration, positive split ratio, and explicit promotion failures.
