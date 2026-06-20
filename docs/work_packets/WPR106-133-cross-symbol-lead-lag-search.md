# WPR106-133 Cross-Symbol Lead-Lag Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Objective

Test a fresh artifact-only BTCUSDT/ETHUSDT cross-symbol lead-lag family. The
family uses completed 15m bars from both symbols to build lagged leader returns,
target returns, rolling correlation, rolling beta/residuals, relative strength,
range, volume, volatility, and aggTrade-flow features, then tests leader
momentum spillover, lagged convergence, relative-strength continuation,
beta-residual reversion, flow-led momentum, and correlation-break follow
behavior.

Optimization, thresholds, filters, holds, ranking, and selection use only
2024-01-01 through 2026-04-30. May 2026 remains fully out of tuning and is
replayed only as a benchmark holdout after fixed pre-May strict rows, or fixed
loose rows if strict rows are absent.

## Allowed Paths

- `docs/work_packets/WPR106-133-cross-symbol-lead-lag-search.md`
- `docs/stage_reports/STAGE_R106_CROSS_SYMBOL_LEAD_LAG_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_133_cross_symbol_lead_lag_search/**`

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

1. Load aligned completed-bar BTCUSDT and ETHUSDT WPR106-96 contexts.
2. Build pairwise lagged leader-return, target-return, relative-strength,
   rolling-correlation, beta-residual, range, volume, volatility, and flow
   features for BTC->ETH and ETH->BTC directions.
3. Generate candidate signals from lead momentum, lagged convergence,
   relative-strength continuation, beta-residual reversion, flow-led momentum,
   and correlation-break follow templates.
4. Use only pre-May rows to calibrate score thresholds and select fixed
   parameters.
5. Evaluate fixed-hold trades with next-bar entry on the target symbol, no
   overlapping position per candidate, taker/slippage costs, monthly stability,
   drawdown, Sortino, best-month concentration, and cost stress.
6. Select strict rows first; select loose rows only if strict is empty. If
   neither exists, do not benchmark May.
7. Replay May 2026 only for fixed selected rows and report it separately.

## Validation

Run focused script compile, then the branch baseline:

```powershell
python -m compileall -q data/research/wpr106_133_cross_symbol_lead_lag_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Completed:

- `python -m compileall -q data/research/wpr106_133_cross_symbol_lead_lag_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

## Closeout

The search evaluated 41,472 pre-May rows. It found 4,103 positive pre-May rows,
0 positive annual-target rows, 59 loose rows, and 0 strict rows. The fixed
loose selection was benchmarked on May 2026 only after pre-May selection was
locked. May rejected the family with 6 positive, 53 negative, and 0 flat
selected rows; the median selected May return was -0.034385.

Decision: reject the cross-symbol lead-lag family as currently configured. All
outputs remain research-only, observe-only, and promotion-ready false.
