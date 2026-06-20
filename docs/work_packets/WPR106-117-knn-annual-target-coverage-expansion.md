# WPR106-117 KNN Annual-Target Coverage Expansion

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Test whether the closest WPR106-116 pre-May annual-target Lorentzian/KNN rows
can be expanded into active, month-stable leads without using May 2026
feedback. WPR106-116 found annual-stability diagnostics, but they were too
inactive or concentrated. This packet should test nearby coverage-expansion
variants before rejecting that KNN sub-family.

## Scope

- Use WPR106-116 pre-May ranking artifacts only to choose source
  neighborhoods:
  - positive pre-May rows;
  - annual losing-month target of at most 2/2/1 losing months in
    2024/2025/2026 Jan-Apr;
  - pre-May trade and active-month diagnostics.
- Recompute KNN scores from WPR106-96 BTCUSDT/ETHUSDT 2024-01 through
  2026-05 feature frames, but use only 2024-01-01 through 2026-04-30 for all
  source selection, threshold multipliers, query spacing, session/regime
  expansion, ranking, and fixed selection.
- Keep May 2026 fully out of tuning and use it only as a benchmark holdout for
  fixed pre-May-selected rows.
- Test coverage expansion around WPR106-116 annual-target rows:
  - lower and slightly higher score thresholds;
  - query spacing of 4 and 8 primary bars;
  - original and expanded sessions;
  - original and expanded regimes;
  - max trades/day caps of 1, 2, and 4.
- Preserve causal KNN semantics: every neighbor label must be completed before
  the query signal time.
- Keep the target active profile explicit: prefer at least 80 trades, at least
  20 active months, roughly 1 to 5 trades/day, realistic costs, overlap
  handling, cost stress, drawdown control, and zero to two losing months per
  full pre-May year.
- Keep all artifacts research-only, observe-only, and promotion-ready false.

## Allowed paths

- `docs/work_packets/WPR106-117-knn-annual-target-coverage-expansion.md`
- `docs/stage_reports/STAGE_R106_KNN_ANNUAL_TARGET_COVERAGE_EXPANSION_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_117*/**`

## Out of scope

- No May 2026 tuning, threshold feedback, source feedback, session/regime
  feedback, rank feedback, active-rate feedback, or cost feedback.
- No shared `src/tradingbotsuite` code, package registry, feature registry,
  strategy registry, backtest engine, optimizer, research-cycle, candidate-pack,
  live, runtime, config, or test changes.
- No candidate pack, paper/live artifact, order placement, position sizing,
  live runtime change, live configuration write, CUDA speedup claim, or
  promotion claim.
- No synthetic fallback data.

## Exit evidence

- A deterministic WPR106-117 runner and artifacts are written under
  `data/research/wpr106_117*/`.
- The report records the exact WPR106-116 source-neighborhood selection rule,
  number of source rows, number of expanded variants, strict/loose counts,
  annual-target counts, and May benchmark result for fixed selected rows.
- May benchmark artifacts are written separately and only after fixed pre-May
  selection.
- Validation baseline is run or explicitly reported if blocked:
  `python -m compileall -q src/tradingbotsuite` and
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`.

## Outcome

WPR106-117 closed on 2026-06-11. The runner selected 20 WPR106-116
annual-target source rows without May feedback, expanded them into 4,320
pre-May variants, and found 1,804 positive rows, 210 annual-target rows, 36
coverage-loose rows, and 0 coverage-strict rows. The fixed pre-May selection
contains 27 coverage-loose rows across 9 parameter clusters, mainly BTCUSDT
trend-pullback high-vol long rows, ETHUSDT trend-pullback Asia long rows, and
ETHUSDT price-path-vol US trend short rows.

May 2026 was benchmark-only after fixed selection. The 27 selected rows
recorded 9 May-positive, 0 May-negative, and 18 flat rows; the best May result
was +0.000777 from one ETHUSDT price-path-vol short trade. The KNN source
neighborhood remains research-only and not candidate-ready because no row
reached the strict 20-active-month floor, the selected rows are concentrated in
a small number of source neighborhoods, and May had too little activity to
confirm robustness.

Validation passed:

```powershell
python -m compileall -q data/research/wpr106_117_knn_annual_target_coverage_expansion/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Contracts reported 460 passed.
