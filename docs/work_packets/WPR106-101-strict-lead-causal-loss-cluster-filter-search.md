# WPR106-101 Strict Lead Causal Loss-Cluster Filter Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Test whether the WPR106-100 strict pre-May cluster-aware portfolio can be
improved by causal pre-entry filters that target loss-cluster behavior without
using calendar-month exclusions or May 2026 feedback.

## Scope

- Use 2024-01-01 through 2026-04-30 as the only optimization and diagnostic
  window.
- Keep May 2026 fully out of filter selection, scoring, parameter choice, and
  ranking.
- Start from the fixed WPR106-100 strict lead
  `combo100-8e6136c0927425b1`.
- Test deterministic causal pre-entry filters over existing trade artifacts:
  - side;
  - regime;
  - volatility bucket;
  - UTC hour groups;
  - UTC weekday groups;
  - bounded pairwise combinations of those filter dimensions.
- Require active 1 to 5 trades per active day, active-month coverage, annual
  loss stability, overlap controls, positive-month concentration controls, and
  positive pre-May return before a filtered row can be a promising lead.
- Join May 2026 only after fixed pre-May filter rows are selected.
- Keep all outputs research-only, observe-only, and promotion-ready false.

## Allowed paths

- `docs/work_packets/WPR106-101-strict-lead-causal-loss-cluster-filter-search.md`
- `docs/stage_reports/STAGE_R106_STRICT_LEAD_CAUSAL_LOSS_CLUSTER_FILTER_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_101*/**`

## Out of scope

- No May 2026 tuning, selection feedback, feature choice, filter choice,
  threshold choice, parameter change, or optimizer feedback.
- No calendar-month exclusion filter as a selected lead.
- No strategy, feature, exit-policy, research-cycle, live-boundary, or operator
  UI source changes.
- No candidate pack, promotion artifact, paper/live artifact, order placement,
  position sizing, runtime-mode change, live-configuration write, or CUDA
  speedup claim.
- No synthetic fallback data.

## Exit evidence

- A deterministic WPR106-101 runner and pre-May causal-filter ranking artifacts
  are written under `data/research/wpr106_101*/`.
- Any May benchmark artifacts are marked benchmark-only and joined only after
  fixed pre-May filter selection.
- Stage report records whether causal filters improve the strict lead without
  breaking active-rate and month-stability targets, and whether May confirms or
  rejects the fixed rows.
- Validation baseline is run or explicitly reported if blocked:
  `python -m compileall -q src/tradingbotsuite` and
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`.
