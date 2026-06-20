# WPR106-102 Broad Family-Level Portfolio Refresh

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Move past defending the WPR106-100 strict portfolio by refreshing the broader
2024-forward family-level sleeve search. Revisit older and discarded WPR106-85
through WPR106-95 families using only pre-May evidence, then benchmark May 2026
only for fixed promising leads.

## Scope

- Use 2024-01-01 through 2026-04-30 as the only optimization, ranking,
  filtering, and selection window.
- Keep May 2026 fully out of tuning and use it only as a benchmark holdout
  after fixed pre-May leads are selected.
- Reuse existing research-only artifacts before changing shared source:
  - WPR106-95 positive sleeve universe;
  - WPR106-100 May-ready sleeve pre-May trades;
  - WPR106-97 May-only sleeve trades where a fixed pre-May lead uses those
    sleeves.
- Search family-level portfolio variants rather than further single-filter
  defense of `combo100-8e6136c0927425b1`.
- Allow active 1 to 5 trades per active day when overlap, costs, and month
  stability are controlled.
- Rank month-to-month and year-to-year stability ahead of one large profitable
  window.
- Keep all outputs research-only, observe-only, and promotion-ready false.

## Allowed paths

- `docs/work_packets/WPR106-102-broad-family-level-portfolio-refresh.md`
- `docs/stage_reports/STAGE_R106_BROAD_FAMILY_LEVEL_PORTFOLIO_REFRESH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_102*/**`

## Out of scope

- No May 2026 tuning, selection feedback, feature choice, filter choice,
  threshold choice, parameter change, or optimizer feedback.
- No source changes unless the artifact-level search exposes a small, scoped,
  testable bug that blocks the packet.
- No calendar-month exclusion as a selected lead.
- No candidate pack, promotion artifact, paper/live artifact, order placement,
  position sizing, runtime-mode change, live-configuration write, or CUDA
  speedup claim.
- No synthetic fallback data.

## Exit evidence

- A deterministic WPR106-102 runner and pre-May selection artifacts are written
  under `data/research/wpr106_102*/`.
- Any May benchmark artifacts are marked benchmark-only and joined only after
  fixed pre-May selection.
- The stage report records whether the broader family-level refresh finds any
  better month-stable leads than WPR106-100/WPR106-101, and whether May
  confirms or rejects those fixed rows.
- Validation baseline is run or explicitly reported if blocked:
  `python -m compileall -q src/tradingbotsuite` and
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`.
