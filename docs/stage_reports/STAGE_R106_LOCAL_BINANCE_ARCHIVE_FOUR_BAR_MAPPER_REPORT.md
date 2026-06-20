# Stage R106 Local Binance Archive Four-Bar Mapper Report

Work packet: `docs/work_packets/WPR106-79-local-binance-archive-four-bar-mapper.md`
Date: 2026-06-09

## Scope

WPR106-79 chooses the local archive mapping phase from the WPR106-78 handoff.
It does not implement a new OKX/Bybit/Binance venue-derived feature-intake
design.

## Result

The packet adds a research-only mapper from the existing local Binance Vision
archive cache into the WPR106-76 four-bar HMM/KNN dataset contract.

Implemented surfaces:

- `build_four_bar_knn_dataset_from_binance_archive(...)` reads existing local
  monthly Binance Vision ZIPs for 15m klines, 1m klines, and aggTrades.
- The mapper aggregates aggTrades to the existing 1m trade-flow proxy and
  audits 1m lower-timeframe coverage without using lower-timeframe bars for
  the fixed four-bar label.
- Sampling happens after labels are built, so `event_end_time_ms` remains the
  fourth real completed future base bar and `purge_after_time_ms` remains
  event-end plus four base bars.
- `map-binance-archive-four-bar-datasets` writes BTC/ETH archive-backed
  datasets, selected validation specs, a mapping manifest, a summary JSON, and
  a PowerShell replay command for the potentially long HMM/KNN matrix.
- The operator Research page now has a queued "Four-Bar Archive Mapping" job
  that writes under `operator_runs/hmm_knn_four_bar_archive_mapping/<job_id>/`.
- The new command is registered as research-only and included in the live
  boundary command list.

Follow-up execution completed the long local archive path:

- `data/research/hmm_knn_four_bar_archive_mapping/wpr106_79_full_local_archive_map/`
  contains BTCUSDT and ETHUSDT 2024 archive-backed datasets.
- Each symbol has 16,000 selected rows across the selected 15m and 1h
  four-bar configurations.
- The mapping manifest passes the research-boundary report after cached refresh.
- The generated matrix replay completed for BTCUSDT and ETHUSDT, writing
  `matrices/<symbol>/experiment_manifest.json` and `experiment_summary.csv`.
- Both symbols had 2/2 matrix rows complete with `status: passed`; all tested
  rows remain `promotion_ready: false`.

The first full archive parse exposed the pure-Python aggTrade row loop as too
slow for multi-GB monthly ZIPs. The mapper now uses chunked pandas parsing for
the aggTrade-to-1m proxy while preserving the same feature columns and label
contract.

## Boundary

All new outputs and job payloads remain:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`

No candidate pack, paper/live artifact, order placement, position sizing,
runtime-mode change, venue intake implementation, or promotion claim was made.

## Validation

Passed:

```powershell
python -m compileall -q src\tradingbotsuite\research\knn_four_bar.py src\tradingbotsuite\research\knn_four_bar_validation.py src\tradingbotsuite\main.py src\tradingbotsuite\operator_console.py src\tradingbotsuite\web\operator.py
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_hmm_knn.py::test_four_bar_binance_archive_mapper_preserves_real_four_bar_labels tests\tradingbotsuite\test_hmm_knn.py::test_four_bar_larger_validation_command_registered_as_research -q
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py::test_operator_four_bar_archive_mapping_job_queues_completes_and_lists_artifact -q
$env:PYTHONPATH='src'; python -m tradingbotsuite.main map-binance-archive-four-bar-datasets --help
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_hmm_knn.py -q
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q
```

Observed warnings:

- `tests/tradingbotsuite/test_hmm_knn.py`: existing XGBoost/CuPy CUDA device
  warnings.
- `tests/tradingbotsuite/test_operator_ui.py`: existing aiosqlite event-loop
  closed thread warning.
- Long matrix replay: repeated HMM `transmat_` zero-transition warnings,
  existing CuPy CUDA path warning, XGBoost CUDA/CPU fallback warning, and a
  pandas FutureWarning in neighbor diagnostics.

## Follow-Up

`ISSUE-R106-023` is resolved as a data-coverage blocker by the completed
archive-backed mapping and matrix replay. The matrix evidence is still
entry-quality evidence under a fixed four-bar exit label only. Exit quality,
funding/open-interest/premium/basis feature intake, and any broader
venue-derived context remain separate research questions. No promotion,
candidate pack, paper/live artifact, or live-boundary claim follows from these
negative after-cost rows.
