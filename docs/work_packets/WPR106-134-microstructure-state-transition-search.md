# WPR106-134 Microstructure State Transition Search

Date: 2026-06-12
Owner: Codex Research Agent
Status: closed

## Objective

Test a fresh artifact-only completed-bar microstructure/state-transition family
on BTCUSDT and ETHUSDT. The family uses 15m return signs, return streaks,
aggTrade-flow imbalance streaks, flow/price agreement and divergence,
alternation/chop, range, volume, realized-volatility, and burst features, then
tests return-streak continuation, return-streak exhaustion fade,
flow-price-agreement follow, flow-price-divergence fade, volatility-burst
follow, volatility-burst reversal, and alternating-chop reversion behavior.

Optimization, thresholds, filters, holds, ranking, and selection use only
2024-01-01 through 2026-04-30. May 2026 remains fully out of tuning and is
replayed only as a benchmark holdout after fixed pre-May strict rows, or fixed
loose rows if strict rows are absent.

## Allowed Paths

- `docs/work_packets/WPR106-134-microstructure-state-transition-search.md`
- `docs/stage_reports/STAGE_R106_MICROSTRUCTURE_STATE_TRANSITION_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_134_microstructure_state_transition_search/**`

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

1. Build completed-bar return-streak, flow-streak, flow/price divergence,
   alternation, choppiness, range, volume, volatility, and burst features from
   WPR106-96 BTCUSDT and ETHUSDT context.
2. Generate candidate signals from return-streak continuation, exhaustion
   fade, flow-price agreement follow, flow-price divergence fade,
   volatility-burst follow/reversal, and alternating-chop reversion templates.
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
python -m compileall -q data/research/wpr106_134_microstructure_state_transition_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Completed:

- `python -m compileall -q data/research/wpr106_134_microstructure_state_transition_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

## Closeout

The search evaluated 40,320 pre-May rows. It found 4,070 positive pre-May rows,
797 positive annual-target diagnostics, 55 loose rows, and 0 strict rows. The
fixed loose selection was benchmarked on May 2026 only after pre-May selection
was locked. May rejected the family with 16 positive, 39 negative, and 0 flat
selected rows; the median selected May return was -0.022664.

Decision: reject the microstructure state-transition family as currently
configured. All outputs remain research-only, observe-only, and
promotion-ready false.
