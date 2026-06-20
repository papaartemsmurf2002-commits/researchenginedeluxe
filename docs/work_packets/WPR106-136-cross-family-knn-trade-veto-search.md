# WPR106-136 Cross-Family KNN Trade-Veto Search

Date: 2026-06-12
Owner: Codex Research Agent
Status: closed

## Objective

Test whether a causal trade-outcome analog veto can improve the pre-May
selected rows from recently rejected 2024-forward families. The packet revisits
discarded WPR106-130 through WPR106-134 sources and overlays a scoped
Lorentzian/Euclidean KNN trade filter that learns only from earlier completed
source trades. The intent is to repair month-to-month stability, not to defend
one family.

## Allowed Paths

- `docs/work_packets/WPR106-136-cross-family-knn-trade-veto-search.md`
- `docs/stage_reports/STAGE_R106_CROSS_FAMILY_KNN_TRADE_VETO_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_136_cross_family_knn_trade_veto_search/**`

## Inputs

- `data/research/wpr106_130_prior_day_level_gap_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_130_prior_day_level_gap_search/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_131_volatility_term_structure_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_131_volatility_term_structure_search/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_132_multi_horizon_trend_state_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_132_multi_horizon_trend_state_search/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_133_cross_symbol_lead_lag_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_133_cross_symbol_lead_lag_search/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_134_microstructure_state_transition_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_134_microstructure_state_transition_search/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/source_context/*_2024_01_to_2026_05_cycle_dataset.parquet`
- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/source_context/*_2024_01_to_2026_05_agg_trade_1m.parquet`

## Boundaries

- Research-only, observe-only, promotion-ready false.
- No candidate pack, paper/live artifact, order placement, sizing change,
  runtime-mode change, live configuration write, or promotion claim.
- May 2026 must not influence source selection, feature normalization,
  KNN parameters, thresholds, ranking, or selection.
- May 2026 may be replayed only after fixed strict pre-May overlays are
  selected, or fixed loose overlays if strict is empty.
- The trade-veto KNN must be causal: pre-May source trades can only use earlier
  source trades whose exits are complete before the current signal; May source
  trades can use only the frozen pre-May history.
- CUDA may be used only if a real path is executed and represented truthfully.
  The expected path is CPU/vectorized NumPy with no speedup claim.
- If a blocking correctness risk is found, update `docs/KNOWN_ISSUES.md`.

## Evidence Plan

1. Load selected source-trade artifacts from WPR106-130 through WPR106-134 and
   de-duplicate exact pre-May behavior.
2. Build completed-bar feature vectors from WPR106-96 15m bars plus 15m
   aggTrade-flow aggregation, using only the completed signal bar for each
   source trade.
3. Evaluate Lorentzian and Euclidean trade-outcome KNN veto variants over
   source candidates with enough pre-May history.
4. Enforce no-overlap and daily trade caps after the veto, then compute monthly
   stability, annual loss caps, drawdown, Sortino, cost stress, and active
   rate.
5. Select strict overlays first; select loose overlays only if strict is empty.
   If neither exists, do not benchmark May.
6. Apply the fixed selected overlays to the already-materialized May source
   trades using frozen pre-May neighbor history only.

## Validation

Run focused script compile, then the branch baseline:

```powershell
python -m compileall -q data/research/wpr106_136_cross_family_knn_trade_veto_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Completed:

- `python -m compileall -q data/research/wpr106_136_cross_family_knn_trade_veto_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

## Closeout

The runner loaded 346 selected source candidates from WPR106-130 through
WPR106-134 and de-duplicated exact pre-May trade behavior to a 292-source pool.
It evaluated 168,192 KNN trade-veto overlays. The pre-May screen found
132,125 positive overlays, 25,371 annual-target overlays, 14,903 loose rows,
and 12 strict rows.

The strict rows are not independent evidence. They come from two WPR106-133
ETHUSDT cross-symbol leader-momentum source candidates with very similar
behavior, and the selected May benchmark has identical accepted May trades for
both sources.

The top strict overlay uses `path_flow` features, Lorentzian distance,
64-trade lookback, 7 neighbors, all-side history, a -0.00010 minimum neighbor
mean, 0.48 minimum neighbor win rate, and a 1-trade/day cap. It records 147
pre-May trades, 26 active months, 5 losing months, annual losses of 2024: 2,
2025: 2, 2026 Jan-Apr: 1, +0.383212 pre-May net return, -0.058052 max
drawdown, 0.144292 best-month share, and full cost-stress survival.

May 2026 rejects the fixed strict selection. All 12 selected overlays are
negative in May; all record 8 May trades and -0.070820 net return after costs.

Decision: reject the cross-family KNN trade-veto overlay as a candidate lead.
It can manufacture strict pre-May rows by filtering WPR106-133 leader-momentum
trades, but the fixed behavior fails the May benchmark and is too concentrated
to support a robust cross-family conclusion. All outputs remain research-only,
observe-only, and promotion-ready false.
