# WPR106-128 Anchored VWAP Intraday Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Objective

Test a fresh artifact-only intraday anchored-VWAP family on BTCUSDT and
ETHUSDT. The family targets daily VWAP deviation, VWAP reclaim, pullback, and
range-position behavior with completed-bar volume, volatility, session, and
aggTrade-flow filters.

Optimization, thresholds, filters, holds, ranking, and selection use only
2024-01-01 through 2026-04-30. May 2026 remains fully out of tuning and is
replayed only as a benchmark holdout after fixed pre-May strict or loose rows
exist.

## Allowed Paths

- `docs/work_packets/WPR106-128-anchored-vwap-intraday-search.md`
- `docs/stage_reports/STAGE_R106_ANCHORED_VWAP_INTRADAY_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_128_anchored_vwap_intraday_search/**`

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

1. Build completed-bar daily anchored VWAP, deviation, reclaim, pullback,
   range-position, volume, volatility, and flow features from WPR106-96 context.
2. Generate candidate signals from VWAP reversion, reclaim continuation,
   trend-pullback, VWAP-range fade, and volume-flow impulse templates.
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
python -m compileall -q data/research/wpr106_128_anchored_vwap_intraday_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Completed validation:

- `python -m compileall -q data/research/wpr106_128_anchored_vwap_intraday_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

## Closeout

The packet is rejected as candidate-ready evidence. The run evaluated 15,360
pre-May rows across BTCUSDT and ETHUSDT anchored-VWAP reversion, momentum,
pullback, range-fade, and flow-impulse templates. It found 1,733 positive
pre-May rows, 2 positive annual-target rows, 52 loose rows, and 0 strict rows.

The loose rows were active enough, with 133 to 662 trades in the top set and
mostly full 28-month coverage, but they failed annual stability. The top
pre-May rows were ETHUSDT volume-flow impulse and VWAP displacement momentum
variants with large positive pre-May returns but 5 to 6 losing months in 2024.
The only positive annual-target rows were too sparse at 33 to 46 trades and 18
to 20 active months.

May 2026 was benchmark-only after fixed pre-May selection. It was mixed but not
stable enough to accept: 23 selected rows were May-positive, 28 were
May-negative, 1 was flat, best May return was +0.049556, worst was -0.127690,
and median was -0.002863. No candidate pack, paper/live artifact,
order/sizing/runtime change, live configuration write, CUDA speedup claim, or
promotion claim was made.
