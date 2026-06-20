# WPR106-122 KNN Complement Coverage Ensemble Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Test whether the WPR106-117 annual-target Lorentzian/KNN neighborhoods can be
combined into active, month-stable trade-level ensembles without using May 2026
for tuning. WPR106-117 found individual KNN rows with annual losing-month
targets satisfied and non-negative selected May behavior, but they were too
sparse by active-month coverage. This packet tests the direct complementary
coverage question at trade level before moving away from the KNN family.

## Scope

- Use WPR106-117 selected/coverage KNN rows as source rows:
  - `data/research/wpr106_117_knn_annual_target_coverage_expansion/pre_may/selected_pre_may.csv`
  - `data/research/wpr106_117_knn_annual_target_coverage_expansion/pre_may/selected_pre_may_trades.parquet`
  - `data/research/wpr106_117_knn_annual_target_coverage_expansion/may_benchmark/selected_may_benchmark_trades.parquet`
- Deduplicate equivalent source behaviors using pre-May source metadata and
  trade/monthly fingerprints before combining.
- Build 2-to-5 member KNN complement portfolios with equal, inverse-drawdown,
  active-month-balanced, and return-tempered weights.
- Replay at trade level with same-symbol overlap blocking, portfolio-level
  concurrent caps, max-trades/day caps, and cost-stress recomputation.
- Use only 2024-01-01 through 2026-04-30 for source deduplication,
  member-choice policy, weighting policy, replay policy, ranking, and fixed
  selection.
- Keep May 2026 fully out of tuning. Use May only after fixed pre-May
  selections are written.
- Keep all artifacts `research_only: true`, `observe_only: true`, and
  `promotion_ready: false`.

## Allowed paths

- `docs/work_packets/WPR106-122-knn-complement-coverage-ensemble-search.md`
- `docs/stage_reports/STAGE_R106_KNN_COMPLEMENT_COVERAGE_ENSEMBLE_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_122*/**`

## Out of scope

- No May 2026 tuning, feedback, source choice, weighting choice, replay policy
  choice, ranking choice, or selection choice.
- No shared `src/tradingbotsuite` package, strategy registry, feature registry,
  backtest engine, optimizer, research-cycle, candidate-pack, live, runtime,
  config, or test changes.
- No candidate pack, paper/live artifact, order placement, position sizing,
  live runtime change, live configuration write, CUDA speedup claim, or
  promotion claim.
- No synthetic fallback data and no silent use of unavailable context as zero.

## Exit evidence

- A deterministic WPR106-122 runner and artifacts are written under
  `data/research/wpr106_122*/`.
- The report records source deduplication, evaluated portfolio count, strict
  and loose counts, selected rows, member/weighting composition, monthly and
  annual diagnostics, active-rate diagnostics, overlap/day-cap effects,
  cost-stress behavior, May benchmark result, and rejected/promising
  archetypes.
- May benchmark artifacts are written separately and only after fixed pre-May
  selection.
- Validation baseline is run or explicitly reported if blocked:
  `python -m compileall -q src/tradingbotsuite` and
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`.

## Outcome

Closed as negative research evidence. A first broader source-replay attempt
from WPR106-117 ranking rows timed out before final artifacts, so the final
deterministic run narrowed to the already fixed WPR106-117 selected KNN rows
and deduplicated them by actual pre-May trade/monthly behavior. The source pool
collapsed to 5 unique KNN behaviors and 420 pre-May source trades.

The final runner evaluated 936 KNN complement portfolios across 2-to-5 member
sets, equal/inverse-drawdown/active-month-balanced/return-tempered weights,
max-trades/day caps of 1/2/4, and concurrent caps of 1/2/3. All 936 portfolios
were positive pre-May and 72 preserved the annual losing-month target, but no
row passed the strict or loose combo coverage gates.

The failure mode is explicit:

- Annual-target rows stayed sparse at 17 to 18 active months.
- Active-coverage rows reached 23 to 26 active months, but failed annual
  stability with 4 losing months in 2024 and 2 to 4 losing months in 2025.
- The selected diagnostic set contains 8 annual-target sparse rows and
  16 active-coverage annual-fail rows.

May 2026 was not benchmarked because no strict or loose pre-May combo existed.
Empty May benchmark artifact tables were written, and May remains unused for
selection.

Artifacts:

- `data/research/wpr106_122_knn_complement_coverage_ensemble_search/wpr106_122_knn_complement_coverage_ensemble_summary.json`
- `data/research/wpr106_122_knn_complement_coverage_ensemble_search/pre_may/source_pool_deduped.csv`
- `data/research/wpr106_122_knn_complement_coverage_ensemble_search/pre_may/knn_combo_ranking.parquet`
- `data/research/wpr106_122_knn_complement_coverage_ensemble_search/pre_may/selected_pre_may.csv`
- `data/research/wpr106_122_knn_complement_coverage_ensemble_search/may_benchmark/selected_may_benchmark_metrics.csv`

Validation passed:

```powershell
python -m compileall -q data/research/wpr106_122_knn_complement_coverage_ensemble_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Contracts reported 460 passed.
