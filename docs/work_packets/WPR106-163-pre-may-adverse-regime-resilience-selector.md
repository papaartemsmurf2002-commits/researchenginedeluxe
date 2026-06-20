# WPR106-163 Pre-May Adverse-Regime Resilience Selector

Status: closed
Date: 2026-06-12
Stage: R106 strategy research

## Objective

Run a May-blind broad follow-up after WPR106-162 rejected component-pocket
portfolio construction. This packet tests whether broad WPR106 source rows can
be selected by pre-May adverse-regime resilience rather than by aggregate PnL,
component-pocket membership, or fixed equal-sleeve portfolio construction.

The goal is to identify whether any old, discarded, or mixed strategy family
has stable 2024-forward behavior in months and day clusters that are difficult
for the rest of the source universe. Active entry rates around 1 to 5 trades
per day are acceptable when costs and overlap diagnostics are explicit.

All scoring, stress-month discovery, stress-day discovery, ranking, exposure
caps, and selection use 2024-01-01 through 2026-04-30 only. May 2026 is fully
excluded from tuning and is used only as a fixed benchmark holdout after
selection is frozen.

## Allowed Paths

- `docs/work_packets/WPR106-163-pre-may-adverse-regime-resilience-selector.md`
- `docs/stage_reports/STAGE_R106_PRE_MAY_ADVERSE_REGIME_RESILIENCE_SELECTOR_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_163_pre_may_adverse_regime_resilience_selector/**`

## Inputs

- Read-only broad artifact universe from
  `data/research/wpr106_157_broad_artifact_component_exposure_selector/**`.
- Read-only later selector artifacts may be used only for comparison and not
  as a substitute for this packet's own pre-May ranking.

## Method

- Load the WPR106-157 broad source universe, selected pre-May trade details,
  and May benchmark trade details.
- Build pre-May row daily and monthly net-return matrices from trade details.
- Discover adverse pre-May months from the cross-sectional median source
  return and broad source drawdown behavior, without using May.
- Discover adverse pre-May day clusters from cross-sectional daily median
  return and source participation, without using May.
- Score source rows by:
  - total 2024-2026 Apr return;
  - 2024-2025 search return and 2026 Jan-Apr validation return;
  - annual losing-month counts;
  - adverse-month and adverse-day returns;
  - drop-best-month robustness;
  - best-month concentration;
  - max drawdown;
  - active-month and active-trade-rate diagnostics;
  - cost stress where enough cost detail exists.
- Select fixed source rows with packet/family/symbol/template exposure caps.
- Build a small set of equal-sleeve portfolios from selected source rows using
  pre-May-only resilience rank, packet/family diversity, low correlation, and
  low same-day-overlap construction.
- Benchmark the fixed selected rows and portfolios on May 2026 only after
  selection is frozen.
- Keep outputs research-only, observe-only, and `promotion_ready: false`.

## Validation

- `python -m compileall -q data/research/wpr106_163_pre_may_adverse_regime_resilience_selector/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`

## Exit Criteria

- Write adverse-regime source rankings, fixed selected rows, selected
  portfolio artifacts, May benchmark artifacts, summary, and stage report.
- Update the stage ledger with the packet decision.
- Do not write a candidate pack or make paper/live/promotion claims.

## Result

WPR106-163 rebuilt the WPR106-157 broad artifact universe, discovered eight
pre-May adverse months and 80 pre-May adverse day clusters without using May,
selected 100 fixed source rows, generated 375 equal-sleeve portfolio
candidates, and selected 38 fixed pre-May portfolios.

May rejected the fixed selected rows and portfolios as broad evidence. Selected
source rows had 30 positive, 68 negative, and 2 flat May rows, with best
+0.065272, worst -0.133646, median -0.006947, and mean -0.013354. Selected
portfolios had 3 positive, 35 negative, and 0 flat May rows, with best
+0.011174, worst -0.045880, median -0.009557, and mean -0.014304.

The packet preserves research-only follow-up clues in WPR106-146
cross-symbol relative-strength trade-veto rows and WPR106-128 anchored VWAP
flow-impulse rows, but rejects the adverse-regime selector as candidate-ready,
portfolio-ready, or promotion-ready. It did not write a candidate pack,
paper/live artifact, live config, order path, sizing change, CUDA speedup
claim, or promotion claim. Focused script compile, package compile, and
contracts passed; contracts reported 460 passed.
