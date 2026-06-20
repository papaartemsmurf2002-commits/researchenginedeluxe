# WPR106-125 True Pair Relative-Value Hedged Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Objective

Test a fresh artifact-only BTCUSDT/ETHUSDT true pair relative-value family
instead of defending prior single-leg lead-lag, KNN, flow, or portfolio
families. The packet focuses on 2024-01-01 through 2026-04-30 for all
thresholds, hedge ratios, filters, exit choices, ranking, and selection. May
2026 is a benchmark-only holdout, loaded only if fixed pre-May strict or loose
rows exist.

The family should explicitly model two-leg hedged trades:

- rolling or fixed pre-May hedge ratios;
- spread z-score mean-reversion and momentum variants;
- beta-residual and ratio-return variants;
- volatility, correlation, session, and flow-confirmation filters;
- realistic two-leg fees and one-position-at-a-time overlap handling;
- active entry rates around 1 to 5 trades per active day when costs and
  overlap remain controlled.

## Allowed Paths

- `docs/work_packets/WPR106-125-true-pair-relative-value-hedged-search.md`
- `docs/stage_reports/STAGE_R106_TRUE_PAIR_RELATIVE_VALUE_HEDGED_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_125_true_pair_relative_value_hedged_search/**`

## Inputs

- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/source_context/*_2024_01_to_2026_05_cycle_dataset.parquet`
- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/source_context/*_2024_01_to_2026_05_agg_trade_1m.parquet`
- Existing WPR106-108 relative-value evidence as prior negative context only;
  do not tune from WPR106-108 May outcomes.

## Boundaries

- Research-only, observe-only, promotion-ready false.
- No candidate pack, paper/live artifact, order placement, sizing change,
  runtime-mode change, or live configuration write.
- No May 2026 row may influence feature choice, threshold choice, hedge-ratio
  choice, ranking, selection, filters, or cost assumptions.
- CUDA may be used only if the executed path is real and truthfully reported.
  This packet is expected to use CPU vectorization/multiprocessing unless a
  real GPU path is implemented and parity-checked.
- If a blocking correctness risk is found, update `docs/KNOWN_ISSUES.md`.

## Evidence Plan

1. Build aligned 15m BTCUSDT/ETHUSDT completed-bar pair features from the
   existing WPR106-96 public-archive context.
2. Generate two-leg pair trades using only completed pre-entry bars, next-bar
   entries, fixed horizons, and optional spread take-profit/stop-style exits
   that do not inspect May during tuning.
3. Apply two-leg costs for both BTC and ETH legs and block overlapping pair
   positions per candidate.
4. Rank pre-May candidates by post-cost return, annual losing-month caps,
   active-month coverage, drawdown, Sortino, best-month concentration, cost
   stress, and trade-rate sanity.
5. Select strict rows first, loose rows only if strict is empty. If neither
   exists, do not benchmark May.
6. If selected rows exist, replay May 2026 with fixed pre-May parameters and
   report benchmark-only return, trades, daily/monthly behavior, drawdown, and
   whether the holdout contradicts the pre-May story.

## Validation

Run focused script compile, then the branch baseline:

```powershell
python -m compileall -q data/research/wpr106_125_true_pair_relative_value_hedged_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Completed validation:

- `python -m compileall -q data/research/wpr106_125_true_pair_relative_value_hedged_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

## Closeout

The packet is rejected as candidate-ready evidence. The final narrowed grid
evaluated 17,280 true-pair rows after an initial broader attempt was stopped
without artifacts for poor first-pass throughput. It found 1,974 positive
pre-May rows, 10 positive annual-target rows, 8 loose rows, and 0 strict rows.
All selected loose rows were US-session unit-beta spread-acceleration momentum
rows with 101 to 158 pre-May trades and 27 active months, but they still had
8 losing pre-May months and missed the annual caps. The annual-target positives
were too sparse, with only 21 to 22 trades and 12 active months.

May 2026 was benchmark-only after fixed pre-May selection. All 8 selected
loose rows were May-negative, with best May return -0.005138, worst
-0.023808, and median -0.020340. No candidate pack, paper/live artifact,
order/sizing/runtime change, live configuration write, CUDA speedup claim, or
promotion claim was made.
