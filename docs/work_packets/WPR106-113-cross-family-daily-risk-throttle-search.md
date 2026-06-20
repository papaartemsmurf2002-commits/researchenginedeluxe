# WPR106-113 Cross-Family Daily Risk Throttle Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Test whether a cross-family portfolio built from recent May-isolated selected
trade streams can improve month-to-month stability when actual trade timing,
cross-source overlap, and daily risk throttles are handled before May 2026 is
ever inspected. This packet should not defend any single rejected family. It
should combine old and recent diagnostic families only when their pre-May trade
streams complement each other by month and day.

## Scope

- Use selected trade-level artifacts from WPR106-106, WPR106-107, WPR106-108,
  WPR106-109, WPR106-111, and WPR106-112.
- Use only 2024-01-01 through 2026-04-30 for source filtering, behavior
  deduplication, portfolio member choice, weight choice, risk-throttle choice,
  ranking, and selection.
- Keep May 2026 fully out of all tuning, source choice, portfolio choice,
  weighting, daily-throttle choice, ranking, and selection.
- Apply fixed pre-May portfolio members, weights, overlap policy, max
  concurrent positions, max trades/day, daily loss stop, and daily profit lock
  unchanged to May 2026 only after a pre-May row qualifies as promising.
- Replay actual selected trade artifacts with explicit net returns already
  costed by the source packets; preserve additional cost-stress diagnostics
  using each trade's recorded round-trip cost where available.
- Enforce cross-source overlap handling during portfolio replay, not just
  monthly-return recombination.
- Allow active 1 to 5 trades per active day after overlap and throttle
  handling.
- Measure monthly returns, annual losing-month counts, day-level behavior,
  best-month concentration, max drawdown, Sortino-style downside risk, active
  rate, source diversity, overlap skips, throttle skips, and cost-stress
  survival.
- Keep every artifact research-only, observe-only, and promotion-ready false.

## Allowed paths

- `docs/work_packets/WPR106-113-cross-family-daily-risk-throttle-search.md`
- `docs/stage_reports/STAGE_R106_CROSS_FAMILY_DAILY_RISK_THROTTLE_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_113*/**`

## Out of scope

- No May 2026 tuning, feature/filter feedback, source feedback, weight
  feedback, risk-throttle feedback, optimizer feedback, or cost tuning.
- No source package changes unless a small, scoped, testable blocker prevents
  artifact-only research.
- No candidate pack, paper/live artifact, order placement, position sizing,
  runtime-mode change, live configuration write, CUDA speedup claim, or
  promotion claim.
- No synthetic fallback data.
- No source row, portfolio row, threshold, throttle, or weighting rule that uses
  May labels, May returns, May quantiles, May distributions, or May trade
  timing.
- No claim that monthly-only recombination proves executable overlap behavior;
  selected rows must be replayed from trade streams.

## Exit evidence

- A deterministic WPR106-113 runner and pre-May portfolio replay artifacts are
  written under `data/research/wpr106_113*/`.
- Pre-May source pool, deduped source pool, portfolio rankings, monthly/daily
  returns, selected portfolio definitions, selected pre-May trades, and
  benchmark-only May rows are written separately.
- The stage report records whether any row satisfies the target profile of
  roughly zero to two losing months per full pre-May year, whether active-rate
  behavior remains inside 1 to 5 trades/day, and whether May confirms or
  rejects fixed pre-May rows.
- Validation baseline is run or explicitly reported if blocked:
  `python -m compileall -q src/tradingbotsuite` and
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`.

## Closeout

Closed on 2026-06-11. The deterministic runner is written at
`data/research/wpr106_113_cross_family_daily_risk_throttle_search/scripts/run_wpr106_113_cross_family_daily_risk_throttle_search.py`.

The runner loaded selected trade-level evidence from WPR106-106, WPR106-107,
WPR106-108, WPR106-109, WPR106-111, and WPR106-112. It started from 758 raw
source rows, kept 140 pre-May behavior-deduped source rows, produced 2,750
monthly screen combinations, and replayed 40,320 trade-level cross-family
portfolio rows with actual cross-source overlap and daily risk-throttle
handling.

Pre-May results were strong in-sample: 40,320 rows were positive, 16,896 were
loose, and 4,182 were strict. The selected set contains 100 strict rows across
44 unique member sets. Rank 1, `riskcombo-910a9cff55b9e469`, records +0.605807
pre-May return, 548 trades, 514 active days, 1.066 trades per active day, 28
active months, two losing months, annual losses of 2024: 0, 2025: 1, and 2026
Jan-Apr: 1, max drawdown -0.058369, and full cost-stress survival.

May 2026 rejects the fixed selected set. All 100 selected strict rows are
May-negative: 0 May-positive, 100 May-negative, and 0 flat. The best May row is
`riskcombo-3023847d256caca0` at -0.001124, while the rank 1 row benchmarks
-0.009206 in May. This is diagnostic evidence that daily risk-throttled
cross-family portfolio construction can fit pre-May month stability from the
existing sleeve pool but does not transfer to the May holdout.

No candidate pack, paper/live artifact, order placement, sizing change,
runtime-mode change, live configuration write, CUDA speedup claim, or promotion
claim was made.

Validation passed:

- `python -m compileall -q data/research/wpr106_113_cross_family_daily_risk_throttle_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` with 460 passed
