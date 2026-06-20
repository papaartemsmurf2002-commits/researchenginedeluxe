# WPR106-104 Pre-May Stability Weighted Ensemble Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Test whether constrained non-equal sleeve weighting can improve the 2024-forward
month-stability profile without relying on May 2026 feedback, after WPR106-102
and WPR106-103 showed that equal-weight split-clean repair does not produce a
clean holdout lead.

## Scope

- Use 2024-01-01 through 2026-04-30 as the only optimization, scoring,
  filtering, and selection window.
- Keep May 2026 fully out of tuning and use it only as a benchmark holdout
  after fixed pre-May weighted rows are selected.
- Start from existing WPR106-95/WPR106-102 sleeve evidence and fixed May replay
  artifacts where available.
- Search constrained, discrete, auditable weighting policies rather than
  unconstrained continuous optimization:
  - equal weight baseline;
  - inverse-loss and inverse-volatility style weights;
  - bounded positive-month complement weights;
  - deterministic small-grid integer weights such as 1/2/3, normalized after
    selection.
- Preserve active 1 to 5 trades per active day as acceptable when overlap,
  cost, concentration, and month-stability controls are handled.
- Rank month-to-month and year-to-year stability ahead of one large profitable
  window.
- Keep all outputs research-only, observe-only, and promotion-ready false.

## Allowed paths

- `docs/work_packets/WPR106-104-pre-may-stability-weighted-ensemble-search.md`
- `docs/stage_reports/STAGE_R106_PRE_MAY_STABILITY_WEIGHTED_ENSEMBLE_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_104*/**`

## Out of scope

- No May 2026 tuning, selection feedback, feature choice, filter choice,
  threshold choice, parameter change, or optimizer feedback.
- No source changes unless a small, scoped, testable bug blocks this packet.
- No calendar-month exclusion as a selected lead.
- No unconstrained continuous optimizer that can overfit monthly weights.
- No candidate pack, promotion artifact, paper/live artifact, order placement,
  position sizing, runtime-mode change, live-configuration write, or CUDA
  speedup claim.
- No synthetic fallback data.

## Exit evidence

- A deterministic WPR106-104 runner and pre-May weighted-ensemble artifacts are
  written under `data/research/wpr106_104*/`.
- Any May benchmark artifacts are marked benchmark-only and joined only after
  fixed pre-May selection.
- The stage report records whether bounded weighting improves the 4-to-5
  losing-month profile and whether May confirms or rejects those rows.
- Validation baseline is run or explicitly reported if blocked:
  `python -m compileall -q src/tradingbotsuite` and
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`.

## Closeout

Closed on 2026-06-11. The packet evaluated 347,110 bounded weighted rows from
1,000 WPR106-102 base combo proposals and 120 positive sleeves using only
2024-01-01 through 2026-04-30 for scoring and selection. It found 603 strict
weighted pre-May stability rows and selected 40 fixed rows before any May join.

The best pre-May row, `combo104-b91239b7624cf3dd`, improves the pre-May
stability profile to 3 losing months with +0.509107 return, 561 trades,
302 active days, 1.858 trades per active day, and 0.493 overlap-day share.
May rejects that row at -0.029783 with 22 trades, 11 active days, 4 positive
days, and 7 losing days. All 40 selected rows have May benchmark evidence;
4 are May-positive and 36 are May-negative. The best May-positive selected rows
are modest at +0.013958 and +0.004301, with mixed 14 positive / 12 losing May
day balance.

The result is a useful constrained-weighting diagnostic, not candidate-ready
evidence. No May tuning, calendar-month selected filter, candidate pack,
paper/live artifact, order/sizing/runtime change, live configuration write,
CUDA speedup claim, or promotion claim exists.

Validation passed:

- `python -m compileall -q data/research/wpr106_104_pre_may_stability_weighted_ensemble_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` with 460 passed.
