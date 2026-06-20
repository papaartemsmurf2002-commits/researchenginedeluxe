# WPR106-100 Pre-May Cluster-Aware Portfolio Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Convert the WPR106-99 component diagnosis into a broader pre-May-only
portfolio search that treats annual losing-month clusters, month-to-month
stability, overlap, duplicate behavior, and active-rate density as first-class
ranking terms before any May 2026 benchmark join.

## Scope

- Use 2024-01-01 through 2026-04-30 as the optimization and diagnostic window.
- Keep May 2026 fully out of tuning, selection, scoring, filtering, and
  parameter choice.
- Re-evaluate WPR106-95 packet-qualified positive sleeves and combinations
  with:
  - annual losing-month caps for full pre-May years;
  - total losing-month and month-cluster penalties;
  - duplicate monthly-behavior and duplicate core-parameter controls;
  - overlap-day and 1 to 5 trades-per-active-day controls;
  - cost-stress and split-concentration controls;
  - explicit ranking output for rejected near-misses.
- Benchmark only fixed pre-May-selected promising leads on May 2026, using
  frozen sleeve definitions and equal-sleeve accounting.
- Keep all outputs research-only, observe-only, and promotion-ready false.

## Allowed paths

- `docs/work_packets/WPR106-100-pre-may-cluster-aware-portfolio-search.md`
- `docs/stage_reports/STAGE_R106_PRE_MAY_CLUSTER_AWARE_PORTFOLIO_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_100*/**`

## Out of scope

- No May 2026 tuning, selection feedback, feature choice, filter choice,
  threshold choice, parameter change, or optimizer feedback.
- No strategy, feature, filter, exit-policy, research-cycle, live-boundary, or
  operator UI source changes.
- No candidate pack, promotion artifact, paper/live artifact, order placement,
  position sizing, runtime-mode change, live-configuration write, or CUDA
  speedup claim.
- No synthetic fallback data.

## Exit evidence

- A deterministic WPR106-100 runner and pre-May cluster-aware ranking artifacts
  are written under `data/research/wpr106_100*/`.
- Any May benchmark artifacts are marked benchmark-only and are joined only
  after fixed pre-May lead selection.
- Stage report records whether stricter month-cluster search finds a more
  stable lead, what May benchmark says for fixed promising rows, and which
  rejected near-misses should or should not guide later strategy research.
- Validation baseline is run or explicitly reported if blocked:
  `python -m compileall -q src/tradingbotsuite` and
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`.

Completed:

- Runner:
  `data/research/wpr106_100_pre_may_cluster_aware_portfolio_search/scripts/run_wpr106_100_cluster_search.py`
- Summary:
  `data/research/wpr106_100_pre_may_cluster_aware_portfolio_search/wpr106_100_cluster_search_summary.json`
- Pre-May ranking and selected leads:
  `data/research/wpr106_100_pre_may_cluster_aware_portfolio_search/pre_may/`
- May benchmark-only rows:
  `data/research/wpr106_100_pre_may_cluster_aware_portfolio_search/may_benchmark/`
- Stage report:
  `docs/stage_reports/STAGE_R106_PRE_MAY_CLUSTER_AWARE_PORTFOLIO_SEARCH_REPORT.md`
- Validation passed:
  `python -m compileall -q src/tradingbotsuite` and
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` with 460 passed.
