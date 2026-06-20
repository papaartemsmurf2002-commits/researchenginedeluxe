# Stage R106 May 2026 Holdout Intake And KNN Benchmark Report

Date: 2026-06-11
Work packet: `docs/work_packets/WPR106-93-may-2026-holdout-intake-and-knn-benchmark.md`
Owner: Codex Research Agent

## Decision

WPR106-93 is closed as a benchmark rejection for the WPR106-92 ETHUSDT
Lorentzian/KNN loose-stability lead.

The packet downloaded and verified the ETHUSDT May 2026 Binance Vision public
archive files required by the existing four-bar mapper, built a benchmark-only
dataset, and ran the pre-selected WPR106-92 KNN/meta row with May isolated as
out-of-sample evidence. The May result contradicts the pre-May story: the
meta-model loses after costs, pure KNN also loses after costs, and no-trade
beats both.

No May 2026 data was used for tuning, ranking, feature selection, threshold
selection, candidate selection, or parameter search. No candidate pack,
paper/live artifact, order placement, sizing change, runtime-mode change, live
configuration write, CUDA speedup claim, or promotion-ready claim exists.

## Intake

Downloaded ETHUSDT May 2026 Binance Vision public-archive files:

| File | Size bytes | Checksum verified |
| --- | ---: | --- |
| `ETHUSDT-15m-2026-05.zip` | 145132 | true |
| `ETHUSDT-1m-2026-05.zip` | 1893623 | true |
| `ETHUSDT-aggTrades-2026-05.zip` | 382806175 | true |

Intake manifest:
`data/research/wpr106_93_may_2026_holdout_intake_and_knn_benchmark/intake/wpr106_93_ethusdt_may_2026_intake_manifest.json`

The April+May context mapper output uses existing April local archives plus the
new May files so May features have rolling April history. The mapper records
all archive hashes and checksum verification. It reports no 15m/1m duplicate
or gap count over April+May and aggregates 65,769,258 aggTrade rows to the
existing 1m trade-flow proxy.

Archive map:
`data/research/wpr106_93_may_2026_holdout_intake_and_knn_benchmark/archive_map/`

## Benchmark Setup

Pre-selected row:

- Source packet: WPR106-92
- Symbol: ETHUSDT
- Slug: `eth-1h-4h-wick-flow-lorentzian-compatible-lower-meta`
- Strategy: meta-model on KNN decisions
- Pre-May result: 564 trades, +0.069117 net after costs, +0.000123
  expectancy, 2.452 trades per active day, 10 active months, 5 positive
  months, 5 losing months, max positive-month profit share 0.335295, max split
  PnL share 0.366382.

Benchmark dataset:
`data/research/wpr106_93_may_2026_holdout_intake_and_knn_benchmark/benchmark_dataset/ethusdt_wpr106_92_candidate_pre_may_train_plus_may_2026_holdout_dataset.parquet`

The benchmark dataset appends only May 2026 signal rows to the frozen WPR106-92
pre-May selected dataset. Row counts:

| Row set | Rows |
| --- | ---: |
| Pre-May all horizons | 16000 |
| May holdout all horizons | 7424 |
| Combined all horizons | 23424 |
| Pre-May 4h rows | 8000 |
| May holdout 4h rows | 1480 |
| Combined 4h rows | 9480 |

The benchmark spec keeps the WPR106-92 candidate's feature, distance, KNN, and
meta thresholds. The only evaluation change is split isolation:
`evaluation.walk_forward_splits=1` and `evaluation.min_training_rows=8000`, so
training ends before May 2026. The runner's existing purge behavior starts
scored holdout rows at 2026-05-01 04:00:00 UTC and labels end at
2026-05-31 23:00:00 UTC.

Spec:
`configs/research/wpr106_93_ethusdt_may_holdout_wpr106_92_candidate_v1.json`

Matrix:
`data/research/wpr106_93_may_2026_holdout_intake_and_knn_benchmark/ethusdt_may_holdout_matrix/experiment_manifest.json`

## Results

May 2026 holdout summary:

| Strategy | Prediction rows | Trades | Net after costs | Expectancy | Profit factor | Active days | Trades/active day | Positive days | Losing days | Max trade-sequence drawdown |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Meta | 1472 | 268 | -0.353937 | -0.001321 | 0.631910 | 31 | 8.645 | 10 | 21 | -0.365293 |
| KNN | 1472 | 367 | -0.406169 | -0.001107 | 0.677453 | 31 | 11.839 | 6 | 25 | -0.417525 |
| No-trade | 1472 | 0 | 0.000000 | 0.000000 | n/a | 0 | 0.000 | 0 | 0 | 0.000000 |

Daily returns:
`data/research/wpr106_93_may_2026_holdout_intake_and_knn_benchmark/summary/wpr106_93_may_holdout_daily_returns.csv`

Summary JSON:
`data/research/wpr106_93_may_2026_holdout_intake_and_knn_benchmark/summary/wpr106_93_may_holdout_benchmark_summary.json`

The candidate is rejected after holdout. May 2026 is negative after costs,
has too many losing days, and trades above the desired 1 to 5 trades per active
day band in holdout. The result is worse than no-trade and does not support
candidate-pack, paper, live, sizing, runtime, or promotion work.

## Known Issue Status

`ISSUE-R106-025` remains open, but narrowed. ETHUSDT May 2026 benchmark data
for this KNN lead is now locally available and verified. BTCUSDT May 2026
archive completeness was not part of this benchmark and remains unverified for
future BTC holdout work.

## Validation

Passed:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- Compileall: passed.
- Contracts: 454 passed.
