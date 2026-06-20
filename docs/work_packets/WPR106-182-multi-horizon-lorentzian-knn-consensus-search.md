# WPR106-182 Multi-Horizon Lorentzian KNN Consensus Search

Status: closed
Owner: Codex Research Agent
Date: 2026-06-12

## Objective

Continue the 2024-forward broad research search with a materially different
Lorentzian/KNN variant. Prior KNN packets tested rolling fixed-horizon analogs,
walk-forward feature packs, causal regime KNN, and path-quality event vetoes.
This packet tests a KNN entry generator based on multi-horizon analog
consensus: neighbors are labeled by agreement between shorter and longer
future paths rather than only a single fixed-horizon direction or a transparent
event veto.

The goal is to give the Lorentzian/KNN family another fair, May-blind test
with different feature geometry, label construction, filter logic, and active
1-5 trades/day support.

## Scope

Selection/tuning window:

- 2024-01-01 through 2026-04-30 UTC.

Benchmark-only window:

- May 2026, replayed only after fixed pre-May selection.

Inputs:

- WPR106-96 BTCUSDT/ETHUSDT 15m bar context through May 2026 and 15m
  aggTrade-flow aggregation loaded through the WPR106-126 helper.

KNN variant dimensions:

- feature packs with completed-bar path, flow, wick/range, volatility,
  session, and prior-day gap state;
- multi-horizon labels such as 8/32 and 16/32 bars;
- Lorentzian distance plus Euclidean controls;
- causal neighbor pools whose labels complete before the query row;
- query/train spacing, lookback, neighbor count, consensus-quality filters,
  side modes, sessions, active signal rates, and daily caps.

May must not be used for feature normalization, label construction for neighbor
pools, threshold choice, filter choice, side-mode choice, row inclusion,
ranking, or selection.

The packet is artifact-only unless a blocking correctness issue is discovered.

## Allowed Paths

- `docs/work_packets/WPR106-182-multi-horizon-lorentzian-knn-consensus-search.md`
- `docs/stage_reports/STAGE_R106_MULTI_HORIZON_LORENTZIAN_KNN_CONSENSUS_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_182_multi_horizon_lorentzian_knn_consensus_search/**`

## Plan

1. Reuse WPR106-126 source-context loading, completed-bar alignment, cost, and
   metrics helpers.
2. Build packet-local completed-bar feature packs and normalize them from
   pre-May rows only.
3. Build causal multi-horizon labels where neighbor labels must complete
   before the query signal row; May query neighbor pools stay frozen to
   pre-May-completed labels.
4. Evaluate Lorentzian and Euclidean KNN score caches over pre-May only.
5. Select fixed rows by annual loss caps, active-month coverage, 1-5
   trades/day behavior, cost stress, drawdown, best-month concentration,
   consensus quality, and dropout robustness.
6. Replay selected fixed rows on May 2026 only.
7. Write ranking, monthly/daily/trade artifacts, summary, report, ledger
   update, and validation notes.

## Research Boundary

All outputs remain:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`

This packet must not create a candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim.

## Validation

At close, run:

```powershell
python -m compileall -q data\research\wpr106_182_multi_horizon_lorentzian_knn_consensus_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Result

Closed on 2026-06-12 as a negative research result.

The packet-local runner
`data/research/wpr106_182_multi_horizon_lorentzian_knn_consensus_search/scripts/run_wpr106_182_multi_horizon_lorentzian_knn_consensus_search.py`
evaluated 13,824 BTCUSDT/ETHUSDT multi-horizon KNN rows. Selection used only
2024-01-01 through 2026-04-30. May 2026 was held out until after fixed
pre-May row selection.

Pre-May screen:

- 1,557 rows were positive after costs.
- 0 rows met annual-target criteria.
- 5 rows met loose criteria.
- 0 rows met strict criteria.
- The fixed selected set contained 5 loose rows.

Selected pre-May replay:

- 5 positive rows, 0 negative rows, 0 flat rows.
- Median net return: +0.366823.
- Active mean net return: +0.253427.
- Best/worst selected rows: +0.366823 / +0.083334.

May 2026 benchmark replay:

- 0 positive rows, 3 negative rows, 2 flat/inactive rows.
- Median net return: -0.018024.
- Active mean net return: -0.018024.
- Best/worst selected rows: 0.000000 / -0.018024.

The only selected pocket was ETHUSDT `regime_gap_session` with
`strict_consensus` quality. Euclidean long rows traded seven times in May and
lost; Lorentzian long rows were inactive in May. The multi-horizon KNN
consensus variant is rejected as candidate-ready, portfolio-ready, or
promotion-ready. No candidate pack, paper/live artifact, order path, sizing
change, runtime-mode change, live configuration write, CUDA speedup claim, or
promotion claim was created.

Artifacts:

- `data/research/wpr106_182_multi_horizon_lorentzian_knn_consensus_search/pre_may/multi_horizon_knn_consensus_ranking.parquet`
- `data/research/wpr106_182_multi_horizon_lorentzian_knn_consensus_search/pre_may/multi_horizon_knn_consensus_top3000.csv`
- `data/research/wpr106_182_multi_horizon_lorentzian_knn_consensus_search/pre_may/family_feature_summary.parquet`
- `data/research/wpr106_182_multi_horizon_lorentzian_knn_consensus_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_182_multi_horizon_lorentzian_knn_consensus_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_182_multi_horizon_lorentzian_knn_consensus_search/selected_pre_may_may_comparison.parquet`
- `data/research/wpr106_182_multi_horizon_lorentzian_knn_consensus_search/wpr106_182_multi_horizon_lorentzian_knn_consensus_search_summary.json`

Validation passed:

```powershell
python -m compileall -q data\research\wpr106_182_multi_horizon_lorentzian_knn_consensus_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
