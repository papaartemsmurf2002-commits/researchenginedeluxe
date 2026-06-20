# WPR106-126 Liquidity Sweep Wick-Failure Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Objective

Test a fresh artifact-only liquidity-sweep and wick-failure strategy family on
BTCUSDT and ETHUSDT, focusing on 2024-01-01 through 2026-04-30 for all
thresholds, filters, exits, ranking, and selection. May 2026 remains a
benchmark-only holdout, replayed only after fixed pre-May strict or loose rows
exist.

The family targets completed-bar stop-run behavior:

- sweep prior high/low ranges and close back inside the range;
- wick rejection and failed breakout continuation/fade variants;
- session, volatility, trend, and aggTrade-flow confirmation filters;
- fixed 15m-bar exits with one-position overlap handling;
- realistic taker/slippage costs and cost stress;
- active rates around 1 to 5 trades per active day when the evidence supports
  that cadence.

## Allowed Paths

- `docs/work_packets/WPR106-126-liquidity-sweep-wick-failure-search.md`
- `docs/stage_reports/STAGE_R106_LIQUIDITY_SWEEP_WICK_FAILURE_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_126_liquidity_sweep_wick_failure_search/**`

## Inputs

- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/source_context/*_2024_01_to_2026_05_cycle_dataset.parquet`
- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/source_context/*_2024_01_to_2026_05_agg_trade_1m.parquet`

## Boundaries

- Research-only, observe-only, promotion-ready false.
- No candidate pack, paper/live artifact, order placement, sizing change,
  runtime-mode change, or live configuration write.
- May 2026 must not influence feature choice, sweep-window choice, threshold
  choice, side/filter choice, exit choice, ranking, selection, or costs.
- CUDA may be used only if a real path is executed and represented truthfully.
  The expected path is CPU vectorized screening with no speedup claim.
- If a blocking correctness risk is found, update `docs/KNOWN_ISSUES.md`.

## Evidence Plan

1. Build completed 15m bar and aggTrade-flow features from the WPR106-96
   context for BTCUSDT and ETHUSDT.
2. Generate candidate signals from prior-range sweeps, wick rejection ratios,
   close-back-inside behavior, trend context, volatility context, and
   flow-confirmation or flow-contrarian filters.
3. Use only pre-May rows to calibrate score thresholds and select fixed
   parameters.
4. Evaluate pre-May fixed-hold trades with next-bar entry, no overlapping
   position per candidate, taker/slippage costs, monthly stability, drawdown,
   Sortino, best-month concentration, and cost stress.
5. Select strict rows first, loose rows only if strict is empty. If neither
   exists, do not benchmark May.
6. Replay May 2026 only for fixed selected rows and report it separately.

## Validation

Run focused script compile, then the branch baseline:

```powershell
python -m compileall -q data/research/wpr106_126_liquidity_sweep_wick_failure_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Completed validation:

- `python -m compileall -q data/research/wpr106_126_liquidity_sweep_wick_failure_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

## Closeout

The packet is rejected as candidate-ready evidence. The run evaluated 6,480
pre-May rows across BTCUSDT and ETHUSDT liquidity-sweep reversal,
wick-rejection, failed-breakout-reclaim, sweep-continuation, and flow-absorbed
sweep templates. It found 486 positive pre-May rows, 42 positive
annual-target rows, 10 loose rows, and 0 strict rows.

Selected loose rows had 60 to 330 trades, 21 to 28 active months, and 6 to 8
losing months, but all missed at least one annual cap. The annual-target rows
were too sparse, generally 1 to 37 trades and at most 14 active months in the
top diagnostics. May 2026 was benchmark-only after fixed pre-May selection:
1 selected row was May-positive, 9 were May-negative, best May return was
+0.008896, worst was -0.072570, and median was -0.012010. The only
May-positive selected row was already rejected by pre-May annual stability.

No candidate pack, paper/live artifact, order/sizing/runtime change, live
configuration write, CUDA speedup claim, or promotion claim was made.
