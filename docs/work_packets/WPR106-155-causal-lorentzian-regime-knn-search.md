# WPR106-155 Causal Lorentzian Regime KNN Search

Status: closed
Date: 2026-06-12
Stage: R106 strategy research

## Objective

Run a scoped 2024-forward Lorentzian/KNN strategy search that is not tied to
the rejected sparse side-veto lineage or the recent direct intrabar-flow
formula grids. The packet tests causal online nearest-neighbor analogs over
completed 15m price, volatility, session, target-flow, and cross-symbol
flow-regime features.

Optimization and selection use 2024-01-01 through 2026-04-30 only. May 2026 is
fully excluded from feature-pack choice, distance metric choice, lookback,
neighbor count, filters, side mode, thresholds, daily caps, throttles, ranking,
and selection. May 2026 is used only as a fixed benchmark holdout for selected
pre-May rows.

## Allowed Paths

- `docs/work_packets/WPR106-155-causal-lorentzian-regime-knn-search.md`
- `docs/stage_reports/STAGE_R106_CAUSAL_LORENTZIAN_REGIME_KNN_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_155_causal_lorentzian_regime_knn_search/**`

## Inputs

- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/source_context/**`
- Recent WPR106-151/WPR106-153 helper code for the shared 2024-forward split,
  cost model, overlap handling, daily caps, loss throttles, and monthly
  metrics.
- WPR106-152 and WPR106-154 reports for rejection context.

## Method

- Build completed-bar feature packs from 15m bars and 15m aggTrade flow:
  target price/volatility/flow regime and cross-symbol relative-flow regime.
- Fit no global model on May. For each signal row, use only prior rows whose
  fixed-hold labels have completed before the signal row.
- Use Lorentzian distance as the primary analog metric and Euclidean distance
  as a transparent control.
- Search feature pack, fixed hold, lookback, neighbor count, session, KNN
  confidence filter, side mode, target raw signal rate, accepted-trade daily
  cap, and prior-month loss throttle.
- Allow active 1, 3, and 5 raw signal targets per day, with explicit overlap,
  daily cap, costs, and monthly stability accounting.
- Store all outputs as research-only, observe-only, and `promotion_ready:
  false`.

## Validation

- `python -m compileall -q data/research/wpr106_155_causal_lorentzian_regime_knn_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`

## Exit Criteria

- Write ranking, selected pre-May replay, May benchmark, summary, and stage
  report artifacts.
- Update the stage ledger with the packet decision.
- Do not write a candidate pack or make paper/live/promotion claims.
