# WPR106-114 Pre-May Rolling OOS Cluster-Veto Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Test whether the WPR106-113 cross-family portfolio universe can be filtered by
pre-May-only rolling pseudo-OOS evidence before May 2026 is inspected. WPR106-113
showed that daily-throttled portfolios can look strict and month-stable
over the full pre-May window while remaining dominated by an ETH-heavy
WPR106-106/108/109 cluster that all loses in May. This packet should determine
whether a stricter pre-May rolling validation and source-cluster veto can avoid
that failure mode without using May feedback.

## Scope

- Use WPR106-113 pre-May candidate universe, monthly returns, selected source
  pool, and trade-stream replay metadata.
- Use only 2024-01-01 through 2026-04-30 for rolling validation, source-cluster
  vetoes, member concentration limits, ranking, and selection.
- Keep May 2026 fully out of all source, cluster, fold, ranking, veto, and
  selection decisions.
- Apply fixed pre-May-selected portfolio rows unchanged to WPR106-113 May trade
  streams only after rolling-OOS selection is complete.
- Treat WPR106-113's full pre-May candidate universe as diagnostic candidate
  generation evidence, then require rolling validation blocks to pass before a
  row can be selected.
- Penalize or veto portfolios dominated by the same ETH-heavy prior-day /
  ETH-follow-BTC / dense wick-vol cluster that failed WPR106-113, but only
  using pre-May source identity and pre-May validation behavior.
- Preserve active 1 to 5 trades/day as acceptable when costs and overlap were
  already handled by WPR106-113 replay.
- Measure rolling validation return, losing validation blocks, late-pre-May
  robustness, selected source diversity, ETH concentration, monthly returns,
  annual losing-month counts, drawdown, active rate, and cost-stress survival.
- Keep every artifact research-only, observe-only, and promotion-ready false.

## Allowed paths

- `docs/work_packets/WPR106-114-pre-may-rolling-oos-cluster-veto-search.md`
- `docs/stage_reports/STAGE_R106_PRE_MAY_ROLLING_OOS_CLUSTER_VETO_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_114*/**`

## Out of scope

- No May 2026 tuning, fold feedback, source feedback, cluster feedback,
  ranking feedback, veto feedback, risk-policy feedback, or cost tuning.
- No source package changes unless a small, scoped, testable blocker prevents
  artifact-only research.
- No candidate pack, paper/live artifact, order placement, position sizing,
  runtime-mode change, live configuration write, CUDA speedup claim, or
  promotion claim.
- No synthetic fallback data.
- No source row, portfolio row, veto rule, threshold, or scoring function that
  uses May labels, May returns, May quantiles, May distributions, or May trade
  timing.
- No claim that this proves a fully independent OOS validation, because the
  WPR106-113 candidate universe was generated from pre-May evidence. This
  packet is a stronger pre-May robustness filter, not a replacement for the
  May holdout.

## Exit evidence

- A deterministic WPR106-114 runner and rolling-OOS selection artifacts are
  written under `data/research/wpr106_114*/`.
- Pre-May rolling fold metrics, cluster-veto diagnostics, selected rows,
  monthly returns, and benchmark-only May rows are written separately.
- The stage report records whether any row satisfies the target profile of
  roughly zero to two losing months per full pre-May year, whether rolling
  validation stays stable, whether source concentration is reduced, and whether
  May confirms or rejects fixed pre-May rows.
- Validation baseline is run or explicitly reported if blocked:
  `python -m compileall -q src/tradingbotsuite` and
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`.

## Closeout

Closed 2026-06-11. The deterministic runner was written under
`data/research/wpr106_114_pre_may_rolling_oos_cluster_veto_search/scripts/`
and generated separate pre-May and May benchmark artifacts under
`data/research/wpr106_114_pre_may_rolling_oos_cluster_veto_search/`.

The run evaluated the 40,320-row WPR106-113 candidate universe with
pre-May-only rolling validation blocks and source-cluster diagnostics. It found
0 rolling-strict rows and 942 rolling-loose rows. The selected set contains
68 rolling-loose rows across 17 unique member sets; all are research-only,
observe-only, and promotion-ready false.

May 2026 was not used for source, fold, cluster, ranking, threshold, veto, or
selection decisions. After fixed pre-May selection, the May benchmark rejected
the selected set: 0 May-positive rows, 68 May-negative rows, and 0 flat rows.
The best selected May return is -0.010799 and the worst is -0.025147.

Conclusion: the pre-May rolling cluster-veto filter does not salvage the
WPR106-113 universe. Rolling strict selection is empty, loose survivors remain
ETH-heavy and failed-cluster concentrated, and every fixed selected row loses
in May. No candidate pack, paper/live artifact, order/sizing/runtime change,
live config write, CUDA speedup claim, or promotion claim exists.

Validation passed:

```powershell
python -m compileall -q data/research/wpr106_114_pre_may_rolling_oos_cluster_veto_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Contracts reported 460 passed.
