# WPR106-129 Opening Range Breakout Fade Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Objective

Test a fresh artifact-only opening-range family on BTCUSDT and ETHUSDT. The
family uses completed 15m bars to define Asia, EU, and US session opening
ranges, then tests breakout-follow, failed-breakout fade, retest-continuation,
and range-fade behavior with volatility and aggTrade-flow filters.

Optimization, thresholds, opening-range length, filters, holds, ranking, and
selection use only 2024-01-01 through 2026-04-30. May 2026 remains fully out of
tuning and is replayed only as a benchmark holdout after fixed pre-May strict
or loose rows exist.

## Allowed Paths

- `docs/work_packets/WPR106-129-opening-range-breakout-fade-search.md`
- `docs/stage_reports/STAGE_R106_OPENING_RANGE_BREAKOUT_FADE_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_129_opening_range_breakout_fade_search/**`

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

1. Build completed-bar session opening-range features from WPR106-96 BTCUSDT
   and ETHUSDT 15m bars and 15m aggTrade-flow context.
2. Generate candidate signals from opening-range breakout follow, failed
   breakout fade, retest continuation, and range-fade templates.
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
python -m compileall -q data/research/wpr106_129_opening_range_breakout_fade_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Completed validation:

- `python -m compileall -q data/research/wpr106_129_opening_range_breakout_fade_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

## Closeout

The packet is rejected as candidate-ready evidence. The run evaluated 17,280
pre-May rows across BTCUSDT and ETHUSDT opening-range breakout,
failed-breakout fade, retest-continuation, range-fade, and volume-flow impulse
templates. It found 2,078 positive pre-May rows, 96 positive annual-target
rows, 20 loose rows, and 0 strict rows.

The loose rows were active and broad enough to be diagnostic, but they failed
annual stability. They were mostly ETHUSDT US 4-bar opening-range
volume-flow/breakout rows and ETHUSDT EU retest-continuation rows. The top
pre-May row recorded +1.038698 with 366 trades and 28 active months, but had 7
losing months, including 3 in 2024 and 4 in 2025. The annual-target rows were
too sparse, maxing at 29 trades and 15 active months.

May 2026 was benchmark-only after fixed pre-May selection. It rejected all
selected rows: 0 May-positive, 20 May-negative, 0 flat, best May return
-0.004720, worst -0.044803, and median -0.024827. No candidate pack,
paper/live artifact, order/sizing/runtime change, live configuration write,
CUDA speedup claim, or promotion claim was made.
