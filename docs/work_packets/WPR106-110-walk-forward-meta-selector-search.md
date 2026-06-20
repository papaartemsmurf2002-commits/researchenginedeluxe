# WPR106-110 Walk-Forward Meta-Selector Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Test whether a pre-May-only walk-forward meta-selector can improve
month-to-month stability by adaptively selecting among previously generated
research rows instead of defending any single rejected family. The packet should
determine whether discarded/fresh rows from recent broad-search packets can be
combined by a causal monthly policy into a more stable research-only lead before
May 2026 is used as a benchmark holdout.

## Scope

- Use existing research-only artifact rows from recent 2024-forward packets as
  a candidate pool, prioritizing WPR106-105 through WPR106-109 fresh family
  searches.
- Use only pre-May evidence from 2024-01-01 through 2026-04-30 for candidate
  pool filtering, policy definition, score weights, lookback windows, selection,
  and ranking.
- Keep May 2026 fully out of pool filtering, policy choice, score choice,
  lookback choice, ranking, and selection.
- Apply fixed pre-May-selected meta policies unchanged to May 2026 only after a
  policy qualifies as a promising pre-May lead.
- Treat each selected source row as research-only, observe-only, and
  promotion-ready false; any meta-policy artifact inherits those flags.
- Use monthly walk-forward selection that only sees completed prior months when
  choosing rows for the next month.
- Evaluate equal-weight and risk-adjusted monthly allocation variants, bounded
  top-k row counts, family/symbol diversity caps, and turnover/overlap
  diagnostics.
- Allow active 1 to 5 trades per active day where source trade artifacts allow
  density accounting; otherwise record the missing trade-density evidence as a
  limitation and keep the result diagnostic.
- Measure monthly returns, annual losing-month counts, pre-May trade/activity
  coverage where available, drawdown on monthly equity, cost-stress proxy
  survival from source rows, and May benchmark behavior.

## Allowed paths

- `docs/work_packets/WPR106-110-walk-forward-meta-selector-search.md`
- `docs/stage_reports/STAGE_R106_WALK_FORWARD_META_SELECTOR_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_110*/**`

## Out of scope

- No May 2026 tuning, score feedback, pool feedback, weighting feedback,
  lookback feedback, or policy selection feedback.
- No source package changes unless a small, scoped, testable blocker prevents
  artifact-only research.
- No candidate pack, paper/live artifact, order placement, position sizing,
  runtime-mode change, live configuration write, CUDA speedup claim, or
  promotion claim.
- No synthetic fallback data.
- No policy that uses future monthly returns when selecting the current month.
- No claim that monthly artifact recombination is sufficient candidate-pack
  evidence without later trade-level overlap, split, ablation, and baseline
  checks.

## Exit evidence

- A deterministic WPR106-110 runner and pre-May meta-selector artifacts are
  written under `data/research/wpr106_110*/`.
- The candidate pool manifest records source packets, row counts, and evidence
  limitations.
- Selected pre-May meta policies, monthly returns, source membership history,
  and benchmark-only May rows are written separately when any promising pre-May
  policy qualifies.
- The stage report records whether any policy satisfies the target profile of
  roughly zero to two losing months per full pre-May year, whether active-rate
  evidence is complete or limited, and whether May confirms or rejects fixed
  promising policies.
- Validation baseline is run or explicitly reported if blocked:
  `python -m compileall -q src/tradingbotsuite` and
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`.

## Closeout

Closed on 2026-06-11. The artifact runner
`data/research/wpr106_110_walk_forward_meta_selector_search/scripts/run_wpr106_110_walk_forward_meta_selector_search.py`
loaded recent pre-May-selected source rows from WPR106-105 through WPR106-109,
removed duplicate monthly behavior fingerprints, and evaluated causal
walk-forward monthly meta-policies. Candidate pool filtering, policy settings,
lookback windows, score modes, weighting, ranking, and selection used only
2024-01-01 through 2026-04-30. May 2026 source returns were loaded only after
the selected pre-May policies were fixed.

The run loaded 630 source rows and removed 81 duplicate behavior rows, leaving
549 candidate rows. It evaluated 28,800 policies, found 28,728 positive
pre-May policy rows, 10,051 loose pre-May rows, and 985 strict monthly-artifact
rows. The top pre-May policy, `wfmeta-230ed7fe71bc2ed0`, returned +1.140045
with 3 losing pre-May months and annual losses of 2024: 1, 2025: 1, and 2026
Jan-Apr: 1, but had very high month-to-month membership turnover and benchmarked
-0.044406 in May.

All 100 selected pre-May policies benchmarked negative in May: 0 May-positive,
100 May-negative, and 0 flat. The best selected May return was -0.008727 and
the mean selected May return was -0.039973. This rejects the monthly
meta-selector idea as currently configured. The strict pre-May rows are
diagnostic only because the packet recombines already-costed source rows at
monthly resolution and does not replay cross-source intramonth trade overlap.

Main artifacts:

- `docs/stage_reports/STAGE_R106_WALK_FORWARD_META_SELECTOR_SEARCH_REPORT.md`
- `data/research/wpr106_110_walk_forward_meta_selector_search/wpr106_110_walk_forward_meta_selector_summary.json`
- `data/research/wpr106_110_walk_forward_meta_selector_search/pre_may/candidate_pool.parquet`
- `data/research/wpr106_110_walk_forward_meta_selector_search/pre_may/policy_ranking.parquet`
- `data/research/wpr106_110_walk_forward_meta_selector_search/pre_may/selected_pre_may_policies.parquet`
- `data/research/wpr106_110_walk_forward_meta_selector_search/may_benchmark/selected_may_benchmark_metrics.parquet`

Validation passed:

- `python -m compileall -q data/research/wpr106_110_walk_forward_meta_selector_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` reported 460 passed.

No candidate pack, paper/live artifact, order/sizing/runtime change, live
configuration write, CUDA speedup claim, or promotion claim exists.
