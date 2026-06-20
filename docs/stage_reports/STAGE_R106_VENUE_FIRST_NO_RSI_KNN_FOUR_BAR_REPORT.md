# Stage R106 Venue-First No-RSI KNN Four-Bar Report

Status: research-only, observe-only, promotion-ready false.

## Scope Completed

- Created WPR106-75 work packet for venue-first no-RSI KNN four-bar research.
- Registered `okx_archive` as registered-only and diagnostic-only in the data and archive source contracts.
- Added the venue scorecard selecting OKX as the primary next data intake, Bybit as secondary, Hyperliquid as diagnostic context, and Deribit/options as a later volatility-context lane.
- Added no-RSI feature packs:
  - `price_close_path_4bar`
  - `price_vol_flow_no_rsi`
  - `perp_context_no_rsi`
- Added KNN `uniform` neighbor weighting alongside `inverse_distance` and `softmax`.
- Added four-bar horizon and label helpers:
  - 15m base interval maps to 1h.
  - 1h base interval maps to 4h.
  - 4h base interval maps to diagnostic-only 16h.
  - Labels are generated from signal close plus four completed bars and include event-end and purge metadata.
- Added compact BTCUSDT and ETHUSDT no-RSI KNN matrix specs with 18 rows per symbol.

## Compact Matrix Design

Each symbol matrix is bounded and avoids a broad grid:

- Feature packs: `price_close_path_4bar`, `price_vol_flow_no_rsi`, `perp_context_no_rsi`.
- Distances: `lorentzian`, `euclidean_robust_z`, `cosine`.
- Neighbor counts available to each config: `5, 8, 13, 21, 32, 48, 64, 96`.
- Primary weighting rows include `uniform`, `inverse_distance`, and `softmax`.
- Regime matching rows include `same`, `compatible`, and `all`.
- Base intervals represented: 15m -> 1h and 1h -> 4h.
- 4h -> 16h is supported by the helper only as diagnostic metadata, not a runnable holding-window claim.

Every matrix row is entry-first. Fixed four-bar holding is the first comparison target; runner exits are allowed only after entry quality is positive. Static barrier rows remain caveat rows.

## Run Status

The BTC and ETH compact matrix commands were attempted and both stopped before model execution because the required four-bar HMM/KNN event-label datasets do not exist locally:

- BTC required dataset: `data/research/hmm_knn_four_bar/btcusdt_no_rsi_four_bar_dataset.parquet`
- ETH required dataset: `data/research/hmm_knn_four_bar/ethusdt_no_rsi_four_bar_dataset.parquet`

The local BTC/ETH durable fixture parquet files are cycle/bar/context datasets. They do not contain the HMM/KNN event-label schema needed by the runner: `signal_id`, `direction`, `label_accept`, and `label_pnl_multiple`.

The deterministic HMM/KNN fixture is synthetic and BTC-only, so it remains valid for plumbing tests only. It is not durable market evidence.

## Result Interpretation

Exit design did not rescue any lead in WPR106-75 because no durable BTC/ETH four-bar KNN rows executed. No candidate, paper, live, promotion, or profitability claim is made.

Current evidence does not justify a larger validation packet. It also does not prove no-RSI KNN failure, because the durable event-label dataset is the blocker.

## Next Phase

Open WPR106-76 as a data/label enabling packet, not an exit-tuning packet:

1. Build BTCUSDT and ETHUSDT four-bar HMM/KNN event datasets from durable bar/context fixtures.
2. Populate no-RSI close-path columns and preserve missingness for flow/perp context columns.
3. Attach `label_accept`, `label_pnl_multiple`, event-end, future-end, and purge metadata using signal close plus four completed bars.
4. Run the WPR106-75 compact matrices unchanged.
5. If any row passes positive costed expectancy, net return, profit factor above 1.05, at least 150 aggregate trades, at least 40 trades per split, 3/4 positive split checks, cost-stress survival above 70%, and no split above 60% PnL share, define a larger validation packet for that symbol only.
6. If no-RSI KNN improves entry quality but fails costs, move to sparse event selection and cost-aware filters.
7. If no-RSI KNN stays negative after the label datasets exist, stop KNN tuning and move to novel venue-derived features after OKX/Bybit intake.

## Validation

- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 449 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_hmm_knn.py -q` passed: 42 passed, with existing XGBoost/CuPy environment warnings.
- Focused descriptor/KNN tests passed: 35 passed.
- JSON/spec expansion checks passed:
  - BTC matrix: 18 experiment rows, 18 unique loadable plan variants.
  - ETH matrix: 18 experiment rows, 18 unique loadable plan variants.

## Research Boundary

All WPR106-75 outputs remain research-only, observe-only, and `promotion_ready: false`. Registered-only venue surfaces cannot be used for candidate or promotion claims. No live configuration, runtime mode, sizing, order placement, candidate pack, or paper/live artifact was created.
