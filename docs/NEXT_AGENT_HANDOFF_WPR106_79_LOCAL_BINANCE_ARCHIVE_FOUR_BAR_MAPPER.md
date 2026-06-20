# WPR106-79 Next Agent Handoff - Local Binance Archive Four-Bar Mapper

Date: 2026-06-09

## State

WPR106-78 proved the larger four-bar HMM/KNN validation run was blocked by
compact fixture coverage, not by a KNN profitability result.

WPR106-79 chose exactly one next phase: map the existing larger local BTC/ETH
Binance Vision archive cache into the WPR106-76 four-bar dataset contract.
It did not implement OKX/Bybit/new venue intake.

Follow-up execution completed the archive-backed mapping and generated matrix
replay on 2026-06-09.

## Implemented

- New archive-backed builder:
  `build_four_bar_knn_dataset_from_binance_archive(...)`.
- New CLI command:
  `map-binance-archive-four-bar-datasets`.
- New operator Research job:
  `/api/operator/research/jobs/map-binance-archive-four-bar-datasets`.
- New Research page control:
  `Four-Bar Archive Mapping`.
- New artifact type:
  `four_bar_archive_mapping`.

The mapper reads local Binance Vision monthly ZIPs from the default cache:

`data/research/historical_data_cache/binance_vision_public_archive/downloads`

It expects complete local periods containing:

- `futures_um/monthly/klines/<SYMBOL>/15m/<SYMBOL>-15m-YYYY-MM.zip`
- `futures_um/monthly/klines/<SYMBOL>/1m/<SYMBOL>-1m-YYYY-MM.zip`
- `futures_um/monthly/aggTrades/<SYMBOL>/<SYMBOL>-aggTrades-YYYY-MM.zip`

The mapper writes BTC/ETH datasets, selected validation specs, a mapping
manifest, and `run_archive_four_bar_knn_validation_matrix.ps1`.

The long local run wrote:

`data/research/hmm_knn_four_bar_archive_mapping/wpr106_79_full_local_archive_map/`

Key outputs:

- `four_bar_archive_mapping_manifest.json`
- `datasets/btcusdt_no_rsi_four_bar_binance_archive_2024-01_to_2024-12_8000_dataset.parquet`
- `datasets/ethusdt_no_rsi_four_bar_binance_archive_2024-01_to_2024-12_8000_dataset.parquet`
- `matrices/btcusdt/experiment_manifest.json`
- `matrices/ethusdt/experiment_manifest.json`

Both BTCUSDT and ETHUSDT datasets have 16,000 selected rows. Both matrix
manifests have 2/2 experiment rows passed and research-boundary checks passing.
All rows remain `promotion_ready: false`.

## Semantics Preserved

- Same-entry fixed four-bar long/short labels.
- `event_end_time_ms == label_future_end_time_ms`.
- `purge_after_time_ms == event_end_time_ms + four base bars`.
- Sampling happens after labeling, so selected rows still use real completed
  future base bars.
- Funding/open-interest/premium/basis context remains explicitly missing in
  mapper v1.

## Boundary

All outputs remain research-only/observe-only/promotion-false. No candidate
pack, paper/live artifact, order placement, position sizing, runtime-mode
change, venue intake, or promotion claim was made.

## Validation

Passed:

- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_hmm_knn.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`

Warnings observed were existing CUDA/XGBoost and aiosqlite event-loop warnings.

## Next Step

No immediate rerun is required for the 2024 local archive-backed path. The
completed commands were:

```powershell
$env:PYTHONPATH='src'
python -m tradingbotsuite.main map-binance-archive-four-bar-datasets --output-dir hmm_knn_four_bar_archive_mapping\wpr106_79_full_local_archive_map --start-month 2024-01 --end-month 2024-12 --sample-rows-per-interval 8000 --matrix-workers 1
```

```powershell
data\research\hmm_knn_four_bar_archive_mapping\wpr106_79_full_local_archive_map\run_archive_four_bar_knn_validation_matrix.ps1
```

Treat the completed matrix as entry-quality validation only. Exit quality
remains a separate question because the labels are same-entry fixed four-bar
labels. The tested rows were negative/insufficient after cost and remained
promotion-blocked; this clears `ISSUE-R106-023` as a data-coverage blocker but
does not prove KNN profitability or justify candidate, paper, live, sizing, or
runtime-mode changes.
