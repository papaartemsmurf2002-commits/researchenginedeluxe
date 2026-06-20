# WPR106-130 Prior-Day Level Gap Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Objective

Test a fresh artifact-only prior-day level and gap family on BTCUSDT and
ETHUSDT. The family uses completed 15m bars plus prior-day high, low, close,
mid, VWAP, range, and current-day opening gap to test breakout-follow,
failed-breakout fade, range-fade, gap-reversion, gap-continuation, and prior
VWAP reversion behavior with session, volatility, volume, and aggTrade-flow
filters.

Optimization, thresholds, filters, holds, ranking, and selection use only
2024-01-01 through 2026-04-30. May 2026 remains fully out of tuning and is
replayed only as a benchmark holdout after fixed pre-May strict or loose rows
exist.

## Allowed Paths

- `docs/work_packets/WPR106-130-prior-day-level-gap-search.md`
- `docs/stage_reports/STAGE_R106_PRIOR_DAY_LEVEL_GAP_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_130_prior_day_level_gap_search/**`

## Inputs

- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/source_context/*_2024_01_to_2026_05_cycle_dataset.parquet`
- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/source_context/*_2024_01_to_2026_05_agg_trade_1m.parquet`
- WPR106-126 source-context loader for completed 15m bars plus 15m aggTrade-flow aggregation.

## Boundaries

- Research-only, observe-only, promotion-ready false.
- No candidate pack, paper/live artifact, order placement, sizing change,
  runtime-mode change, or live configuration write.
- May 2026 must not influence feature choice, threshold choice, filter choice,
  hold choice, ranking, selection, or costs.
- CUDA may be used only if a real path is executed and represented truthfully.
  The expected path is CPU vectorized screening with no speedup claim.
- If a blocking correctness risk is found, update `docs/KNOWN_ISSUES.md`.

## Evidence Plan

1. Build completed-bar prior-day level and gap features from WPR106-96 BTCUSDT
   and ETHUSDT 15m bars plus 15m aggTrade-flow context.
2. Generate candidate signals from prior-day breakout follow, failed-breakout
   fade, prior-range fade, gap reversion, gap continuation, and prior-day VWAP
   reversion templates.
3. Use only pre-May rows to calibrate score thresholds and select fixed
   parameters.
4. Evaluate fixed-hold trades with next-bar entry, no overlapping position per
   candidate, taker/slippage costs, monthly stability, drawdown, Sortino,
   best-month concentration, and cost stress.
5. Select strict rows first, loose rows only if strict is empty. If neither
   exists, do not benchmark May.
6. Replay May 2026 only for fixed selected rows and report it separately.

## Validation

Run focused script compile, then the branch baseline:

```powershell
python -m compileall -q data/research/wpr106_130_prior_day_level_gap_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Completed validation:

- `python -m compileall -q data/research/wpr106_130_prior_day_level_gap_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

## Closeout

The packet is rejected as candidate-ready evidence after the May benchmark.
The run evaluated 17,664 pre-May rows across BTCUSDT and ETHUSDT prior-day
breakout, failed-breakout fade, prior-range fade, gap-reversion,
gap-continuation, and prior-day VWAP reversion templates. It found 2,061
positive pre-May rows, 1 positive annual-target row, 105 loose rows, and 1
strict row.

The strict pre-May row is ETHUSDT prior-day breakout follow with a 384-bar
normalization window, 32-bar hold, all-session high-range filter, and
flow-neutral filter. It records +1.088169 pre-May net return, 261 trades, 28
active months, 5 losing months, annual losses of 2024: 2, 2025: 2, 2026
Jan-Apr: 1, max drawdown -0.126504, best-month share 0.163108, and full cost
stress survival.

May 2026 was benchmark-only after strict pre-May selection. The single strict
row recorded 3 May trades, all net negative in aggregate, with -0.029037 May
net return and -0.029037 max drawdown. The row is rejected by holdout despite
being the strongest pre-May row found in this packet.

No candidate pack, paper/live artifact, order/sizing/runtime change, live
configuration write, CUDA speedup claim, or promotion claim was made.
