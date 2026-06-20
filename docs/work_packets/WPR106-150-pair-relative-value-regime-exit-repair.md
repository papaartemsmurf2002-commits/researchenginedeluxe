# WPR106-150 Pair Relative-Value Regime/Exit Repair

Date: 2026-06-12
Owner: Codex Research Agent
Status: closed

## Objective

Revisit the WPR106-125 true-pair relative-value family without rerunning the
same rejected grid. The prior packet found an active true-pair pocket in
US-session unit-beta spread-acceleration momentum, but it missed annual
loss-month caps and all selected loose rows lost in May.

This packet tests whether pre-May-only causal regime gates, downside throttles,
and exit repairs can make the pair-spread family month-stable enough to
qualify for a May 2026 benchmark.

## Allowed Paths

- `docs/work_packets/WPR106-150-pair-relative-value-regime-exit-repair.md`
- `docs/stage_reports/STAGE_R106_PAIR_RELATIVE_VALUE_REGIME_EXIT_REPAIR_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_150_pair_relative_value_regime_exit_repair/**`

## Inputs

- `data/research/wpr106_125_true_pair_relative_value_hedged_search/**`
- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/source_context/**`

WPR106-125 May outcomes may be read as rejection context only. No May data may
influence WPR106-150 feature choice, filter choice, threshold, exit rule,
ranking, or selection.

## Boundaries

- Research-only, observe-only, promotion-ready false.
- No candidate pack, paper/live artifact, order placement, sizing change,
  runtime-mode change, live configuration write, or promotion claim.
- Use 2024-01-01 through 2026-04-30 for every tuning and selection decision.
- Use May 2026 only as benchmark holdout if fixed pre-May survivors exist.
- Pair trades remain true two-leg BTCUSDT/ETHUSDT normalized returns with
  two-leg costs, one pair position at a time, and explicit daily caps.
- Active rates around 1 to 5 trades per active day are allowed when costs,
  overlap, drawdown, and monthly stability are handled.
- This packet is artifact-only and does not change shared strategy, feature,
  KNN, backtest, live, or candidate-pack code.
- CUDA is not expected; report CPU/vectorized execution truthfully.
- If a blocking correctness risk is found, update `docs/KNOWN_ISSUES.md`.

## Evidence Plan

1. Import/reuse WPR106-125 pair feature and accounting helpers.
2. Build aligned BTCUSDT/ETHUSDT pair context from WPR106-96.
3. Test a narrowed but novel pre-May grid around pair spread acceleration,
   spread momentum, and relative-return momentum with:
   - unit and rolling hedge ratios;
   - correlation/volatility/spread-state gates;
   - causal rolling loss-throttle gates using only prior completed monthly
     evidence;
   - fixed, score-flip, reversion, and time-stop exits;
   - target active rates of 1, 3, and 5 signals/day.
4. Require strict or loose pre-May monthly stability before any May replay.
5. Replay May 2026 only for fixed pre-May survivors.
6. Record whether the pair family is still rejected or whether a narrow
   research-only repair lead deserves deeper controls.

## Validation

Run focused script compile, then the branch baseline:

```powershell
python -m compileall -q data/research/wpr106_150_pair_relative_value_regime_exit_repair/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

## Evidence Results

- Evaluated rows: 5,184.
- Positive pre-May rows: 986.
- Annual-target rows: 4.
- Loose pre-May rows: 8.
- Strict pre-May rows: 0.
- Selected rows: 8 loose rows.
- May benchmark: 0 positive rows, 4 negative rows, 4 flat rows.
- Best May return: 0.000000.
- Worst May return: -0.010919.
- Median May return: -0.005459.

## Closeout

WPR106-150 rejects the pair relative-value regime/exit repair as
candidate-ready or as a new promising lead. The pre-May repair produced eight
loose spread-acceleration momentum rows with lower drawdown than WPR106-125,
but no strict rows. The rows still miss the ideal annual stability target, and
May either goes flat because April's loss-throttle state blocks all entries or
loses on the rolling-beta score-flip variants.

The four annual-target rows are too sparse and weak to benchmark seriously:
30 trades, 11 active months, +0.003453 pre-May return, best-month share
0.799766, and 1/4 cost-stress survival.

Validation passed:

```powershell
python -m compileall -q data/research/wpr106_150_pair_relative_value_regime_exit_repair/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Contracts result: 460 passed.
