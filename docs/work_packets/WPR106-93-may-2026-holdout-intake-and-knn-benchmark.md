# WPR106-93 May 2026 Holdout Intake And KNN Benchmark

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Resolve the immediate May 2026 benchmark blocker for the WPR106-92 pre-May
ETHUSDT KNN/meta loose-stability row, without using May 2026 for tuning,
ranking, feature selection, threshold selection, or parameter changes.

The pre-selected benchmark target is:

- Symbol: `ETHUSDT`
- Row: `eth-1h-4h-wick-flow-lorentzian-compatible-lower-meta`
- Source packet: WPR106-92
- Pre-May summary: 564 meta trades, +0.069117 net after costs, +0.000123
  expectancy, 2.452 trades per active day, 10 active months, 5 positive
  months, 5 losing months, max positive-month profit share 0.335295, and max
  split PnL share 0.366382.

## Scope

- Intake only the May 2026 Binance Vision public-archive data required to
  build a truthful benchmark dataset for the pre-selected ETHUSDT 1h-to-4h
  HMM/KNN row. BTCUSDT May archive inspection/intake may be included only if it
  is cheap and helps close the shared `ISSUE-R106-025` archive dependency.
- Preserve hash, row-count, gap/duplicate, completed-bar, event-end, purge, and
  research-only metadata.
- Build a May-only benchmark dataset/artifact for ETHUSDT with no optimizer
  feedback into the WPR106-92 choice.
- Reuse the exact WPR106-92 candidate settings/config payload for the selected
  ETHUSDT row where the current code supports it. Any unavoidable benchmark
  implementation limitation must be explicit and fail closed.
- Report May 2026 benchmark trades, net return after costs, expectancy, active
  days, trades per active day, drawdown/downside evidence if available,
  day/month behavior, and whether May contradicts the pre-May story.
- Keep all outputs `research_only`, `observe_only`, and `promotion_ready:
  false`.

## Allowed paths

- `docs/work_packets/WPR106-93-may-2026-holdout-intake-and-knn-benchmark.md`
- `docs/stage_reports/STAGE_R106_MAY_2026_HOLDOUT_INTAKE_AND_KNN_BENCHMARK_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `configs/research/wpr106_93_*.json`
- `data/research/wpr106_93*/**`
- `data/research/historical_data_cache/binance_vision_public_archive/downloads/futures_um/monthly/klines/ETHUSDT/15m/*2026-05*`
- `data/research/historical_data_cache/binance_vision_public_archive/downloads/futures_um/monthly/klines/ETHUSDT/1m/*2026-05*`
- `data/research/historical_data_cache/binance_vision_public_archive/downloads/futures_um/monthly/aggTrades/ETHUSDT/*2026-05*`
- `data/research/historical_data_cache/binance_vision_public_archive/downloads/futures_um/monthly/klines/BTCUSDT/15m/*2026-05*`
- `data/research/historical_data_cache/binance_vision_public_archive/downloads/futures_um/monthly/klines/BTCUSDT/1m/*2026-05*`
- `data/research/historical_data_cache/binance_vision_public_archive/downloads/futures_um/monthly/aggTrades/BTCUSDT/*2026-05*`

## Out of scope

- No strategy, feature, filter, threshold, model, cost, or exit tuning from May
  2026 data.
- No candidate pack, promotion artifact, paper/live artifact, order placement,
  sizing change, runtime-mode change, or live-configuration write.
- No new venue/source family beyond the scoped Binance Vision public-archive
  holdout intake.
- No synthetic fallback if May 2026 public archive data is unavailable.
- No CUDA speedup claim.

## Exit evidence

- ETHUSDT May archive intake manifest with source URLs, archive hashes, and
  checksum verification:
  `data/research/wpr106_93_may_2026_holdout_intake_and_knn_benchmark/intake/wpr106_93_ethusdt_may_2026_intake_manifest.json`
- April+May context map, used only to compute May rows with rolling April
  history:
  `data/research/wpr106_93_may_2026_holdout_intake_and_knn_benchmark/archive_map/`
- Benchmark dataset manifest:
  `data/research/wpr106_93_may_2026_holdout_intake_and_knn_benchmark/benchmark_dataset/ethusdt_wpr106_92_candidate_pre_may_train_plus_may_2026_holdout_dataset_manifest.json`
- One-row benchmark spec:
  `configs/research/wpr106_93_ethusdt_may_holdout_wpr106_92_candidate_v1.json`
- Benchmark matrix:
  `data/research/wpr106_93_may_2026_holdout_intake_and_knn_benchmark/ethusdt_may_holdout_matrix/experiment_manifest.json`
- Benchmark summary:
  `data/research/wpr106_93_may_2026_holdout_intake_and_knn_benchmark/summary/wpr106_93_may_holdout_benchmark_summary.json`
- Daily returns:
  `data/research/wpr106_93_may_2026_holdout_intake_and_knn_benchmark/summary/wpr106_93_may_holdout_daily_returns.csv`
- Stage report:
  `docs/stage_reports/STAGE_R106_MAY_2026_HOLDOUT_INTAKE_AND_KNN_BENCHMARK_REPORT.md`
- Ledger and known-issue update.
- Validation baseline passed:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Results:

- Compileall: passed.
- Contracts: 454 passed.
