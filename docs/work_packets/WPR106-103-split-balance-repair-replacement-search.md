# WPR106-103 Split-Balance Repair Replacement Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Repair or falsify the WPR106-102 rank 2/3 diagnostic direction by searching
for split-clean replacement portfolios that keep the improved month-stability
profile without relying on member sleeves whose split proxy is maximally
concentrated.

## Scope

- Use 2024-01-01 through 2026-04-30 as the only optimization, ranking,
  filtering, replacement, and selection window.
- Keep May 2026 fully out of tuning and use it only as a benchmark holdout
  after fixed pre-May rows are selected.
- Start from existing WPR106-95/WPR106-102 sleeve evidence and May replay
  artifacts.
- Search both:
  - exact split-clean portfolios from all WPR106-95 positive sleeves where
    member split proxies are acceptable;
  - targeted replacements around WPR106-102 rank 2/3/4 families that remove
    `max_single_split_pnl_share=1.0` members.
- Preserve active 1 to 5 trades per active day as acceptable when overlap,
  cost, split, and month-stability controls are handled.
- Rank month-to-month and year-to-year stability ahead of one large profitable
  window.
- Keep all outputs research-only, observe-only, and promotion-ready false.

## Allowed paths

- `docs/work_packets/WPR106-103-split-balance-repair-replacement-search.md`
- `docs/stage_reports/STAGE_R106_SPLIT_BALANCE_REPAIR_REPLACEMENT_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_103*/**`

## Out of scope

- No May 2026 tuning, selection feedback, feature choice, filter choice,
  threshold choice, parameter change, or optimizer feedback.
- No source changes unless a small, scoped, testable bug blocks this packet.
- No calendar-month exclusion as a selected lead.
- No candidate pack, promotion artifact, paper/live artifact, order placement,
  position sizing, runtime-mode change, live-configuration write, or CUDA
  speedup claim.
- No synthetic fallback data.

## Exit evidence

- A deterministic WPR106-103 runner and pre-May split-balance search artifacts
  are written under `data/research/wpr106_103*/`.
- Any May benchmark artifacts are marked benchmark-only and joined only after
  fixed pre-May selection.
- The stage report records whether split-clean replacements preserve the
  4-losing-month profile and whether May confirms or rejects those rows.
- Validation baseline is run or explicitly reported if blocked:
  `python -m compileall -q src/tradingbotsuite` and
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`.

## Closeout

WPR106-103 is closed as a falsification/diagnostic packet. The exact
split-clean sleeve pool contains only 12 of the 120 positive WPR106-95/WPR106-102
sleeves. Exhaustive 2-to-6 sleeve recombination over that pool evaluated 2,497
pre-May portfolios and found only one strict split-clean row that satisfies the
annual and partial-2026 loss controls: `combo103-8e6136c0927425b1`, the same
five-sleeve strict lead already rejected by May. Its May 2026 benchmark remains
-0.007165.

May was joined only after fixed pre-May selection. All 40 selected rows have May
benchmarks; 9 are May-positive and 31 are May-negative. The May-positive rows do
not satisfy the strict pre-May stability target, so no candidate pack,
promotion-ready artifact, paper/live artifact, order/sizing/runtime change, live
configuration write, CUDA speedup claim, or promotion claim was made.
