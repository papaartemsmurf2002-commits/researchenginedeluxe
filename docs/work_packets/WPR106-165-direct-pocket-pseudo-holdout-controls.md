# WPR106-165 Direct Pocket Pseudo-Holdout Controls

Status: closed
Date: 2026-06-12
Stage: R106 strategy research

## Objective

Run a direct, May-blind control audit on the narrow research-only pockets that
survived repeated broad selector reports: WPR106-146 cross-symbol
relative-strength trade-veto and WPR106-128 anchored VWAP flow-impulse.

These pockets have already been noticed through prior May benchmark summaries,
so this packet cannot treat May 2026 as a fresh discovery holdout. The purpose
is narrower and fail-closed: test whether the pockets were already stable under
pre-May month-by-month pseudo-holdouts, matched controls, concentration checks,
and simple pre-May-only portfolio construction before comparing the fixed rows
to May 2026 as a benchmark.

All row scoring, pseudo-holdout checks, control matching, portfolio
construction, and ranking use 2024-01-01 through 2026-04-30 only. May 2026 is
used only after fixed rows, controls, and portfolios are frozen.

## Allowed Paths

- `docs/work_packets/WPR106-165-direct-pocket-pseudo-holdout-controls.md`
- `docs/stage_reports/STAGE_R106_DIRECT_POCKET_PSEUDO_HOLDOUT_CONTROLS_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_165_direct_pocket_pseudo_holdout_controls/**`

## Inputs

- Read-only WPR106-157 broad artifact normalizer and artifacts under
  `data/research/wpr106_157_broad_artifact_component_exposure_selector/**`.
- Read-only WPR106-163 helper logic may be reused for pre-May daily/monthly
  matrices and adverse-regime diagnostics.
- WPR106-164 prototype evidence may be referenced for context, but selection
  and controls in this packet must be recomputed from pre-May data.

## Method

- Rebuild the broad WPR106 artifact universe from selected trade details.
- Identify the target pockets by packet/family/template names:
  - WPR106-146 cross-symbol relative-strength continuation;
  - WPR106-128 anchored VWAP flow-impulse.
- Compute pre-May source metrics, monthly returns, daily returns, adverse
  month/day diagnostics, annual losing-month counts, active rates, drawdown,
  best-month concentration, and drop-best-month robustness.
- Run pre-May pseudo-holdout diagnostics for each target row by treating every
  pre-May month as a withheld month and measuring:
  - number of positive withheld months;
  - number of losing withheld months per year;
  - worst withheld month;
  - median withheld month;
  - fraction of total PnL explained by the best month.
- Select fixed target rows using only pre-May diagnostics.
- Match non-target controls by symbol, trade-count scale, validation return,
  adverse-month/day profile, total return, and pseudo-holdout profile.
- Build simple equal-sleeve target and control portfolios using pre-May-only
  rank, diversity, low correlation, and low overlap diagnostics.
- Benchmark fixed target rows, matched controls, target portfolios, and control
  portfolios on May 2026 only after all selections are frozen.
- Keep outputs research-only, observe-only, and `promotion_ready: false`.

## Validation

- `python -m compileall -q data/research/wpr106_165_direct_pocket_pseudo_holdout_controls/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`

## Exit Criteria

- Write target-pocket rankings, fixed selected target rows, matched controls,
  pseudo-holdout diagnostics, selected/control portfolio artifacts, May
  benchmark artifacts, summary, and stage report.
- Update the stage ledger with the packet decision.
- Do not write a candidate pack or make paper/live/promotion claims.

## Result

WPR106-165 rebuilt the WPR106-157 broad artifact universe, identified 47 fixed
target rows across WPR106-146 cross-symbol relative-strength trade-veto and
WPR106-128 anchored VWAP flow-impulse, matched 47 non-target controls, generated
872 pre-May portfolio candidates, and selected 52 fixed target/control
portfolios. All row scoring, pseudo-holdout diagnostics, control matching,
portfolio construction, and portfolio ranking used only 2024-01-01 through
2026-04-30; May 2026 remained benchmark-only after fixed selection.

May split the target pockets. WPR106-146 had 17 positive, 0 negative, and 0
flat May rows, with best +0.067949, worst +0.015398, median +0.030569, and
mean +0.037985. WPR106-128 had 13 positive, 16 negative, and 1 flat May rows,
with best +0.027293, worst -0.107429, median -0.002686, and mean -0.009161.
Matched controls had 7 positive, 40 negative, and 0 flat May rows, with median
-0.022573 and mean -0.023592.

Target-pocket portfolios were 28 positive and 0 negative in May, with median
+0.023694 and mean +0.024733, while matched-control portfolios were 0 positive
and 24 negative with median -0.030822 and mean -0.026689. This is a useful
control finding, but not candidate-ready evidence because the target pockets
were motivated by prior May benchmark summaries and therefore May is not a
fresh independent discovery holdout.

The packet rejects WPR106-165 as candidate-ready, portfolio-ready, or
promotion-ready evidence. It preserves WPR106-146 relative-strength trade-veto
as the strongest research-only follow-up clue from the broad 2024-forward
search so far, rejects WPR106-128 as a direct May benchmark lead, and requires
fresh non-May retest, direct strategy rerun, causal ablations, side/opposite
controls, cost/overlap stress, and candidate-gate evidence before any stronger
claim. The run did not write a candidate pack, paper/live artifact, live config,
order path, sizing change, CUDA speedup claim, or promotion claim. Focused
script compile, package compile, and contracts passed; contracts reported 460
passed.
