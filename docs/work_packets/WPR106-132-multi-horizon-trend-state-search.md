# WPR106-132 Multi-Horizon Trend State Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Objective

Test a fresh artifact-only multi-horizon trend, pullback, and state-transition
family on BTCUSDT and ETHUSDT. The family uses completed 15m bars to build
1h/4h/1d/multi-day return state, rolling trend alignment, pullback,
overextension, range, volume, volatility, choppiness, and aggTrade-flow
features, then tests trend-follow, trend-pullback, transition-breakout,
exhaustion-fade, choppy mean-reversion, range expansion, and flow-confirmed
momentum behavior.

Optimization, thresholds, filters, holds, ranking, and selection use only
2024-01-01 through 2026-04-30. May 2026 remains fully out of tuning and is
replayed only as a benchmark holdout after fixed pre-May strict rows, or fixed
loose rows if strict rows are absent.

## Allowed Paths

- `docs/work_packets/WPR106-132-multi-horizon-trend-state-search.md`
- `docs/stage_reports/STAGE_R106_MULTI_HORIZON_TREND_STATE_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_132_multi_horizon_trend_state_search/**`

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

1. Build completed-bar multi-horizon return, trend-alignment, pullback,
   overextension, choppiness, volatility, volume, and flow features from
   WPR106-96 BTCUSDT and ETHUSDT context.
2. Generate candidate signals from trend-follow, trend-pullback,
   transition-breakout, exhaustion-fade, choppy mean-reversion,
   range-expansion, and flow-momentum templates.
3. Use only pre-May rows to calibrate score thresholds and select fixed
   parameters.
4. Evaluate fixed-hold trades with next-bar entry, no overlapping position per
   candidate, taker/slippage costs, monthly stability, drawdown, Sortino,
   best-month concentration, and cost stress.
5. Select strict rows first; select loose rows only if strict is empty. If
   neither exists, do not benchmark May.
6. Replay May 2026 only for fixed selected rows and report it separately.

## Validation

Run focused script compile, then the branch baseline:

```powershell
python -m compileall -q data/research/wpr106_132_multi_horizon_trend_state_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Completed:

- `python -m compileall -q data/research/wpr106_132_multi_horizon_trend_state_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

## Closeout

The search evaluated 40,320 pre-May rows. It found 5,402 positive pre-May
rows, 50 positive annual-target diagnostics, 135 loose rows, and 0 strict rows.
The fixed loose selection was benchmarked on May 2026 only after pre-May
selection was locked. May rejected the family with 17 positive, 118 negative,
and 0 flat selected rows; the median selected May return was -0.021058.

Decision: reject the multi-horizon trend-state family as currently configured.
All outputs remain research-only, observe-only, and promotion-ready false.
