# Stage R106 WPR106-182 Multi-Horizon Lorentzian KNN Consensus Search Report

Status: closed
Date: 2026-06-12
Owner: Codex Research Agent

## Scope

WPR106-182 continued the 2024-forward broad research search with a
packet-local Lorentzian/KNN variant. The runner tested multi-horizon analog
consensus labels, where neighbors are labeled by agreement between shorter and
longer future paths rather than a single fixed-horizon direction or a prior
event veto.

Selection and ranking used only 2024-01-01 through 2026-04-30 UTC. May 2026
was benchmark-only after fixed pre-May selection.

## Implementation

The artifact-only runner is:

- `data/research/wpr106_182_multi_horizon_lorentzian_knn_consensus_search/scripts/run_wpr106_182_multi_horizon_lorentzian_knn_consensus_search.py`

The runner reused WPR106-126 source-context loading, completed-bar alignment,
round-trip cost accounting, overlap handling, daily-cap handling, and metrics.
It evaluated BTCUSDT and ETHUSDT with two completed-bar feature packs,
8/32-bar and 16/32-bar label pairs, Lorentzian and Euclidean distance,
960/2880-bar lookbacks, 15/31 neighbors, all/Asia/EU/US sessions, loose and
strict consensus filters, both/long/short side modes, target signal rates of
1/3/5 per day, and accepted-trade daily caps of 1/3/5.

Feature normalization was fit on pre-May rows only. For May query rows,
neighbor labels were restricted to labels whose exits completed before
2026-05-01.

Runtime was 315.57 seconds. CUDA was not used and no speedup claim was made.

## Results

The screen evaluated 13,824 candidate rows:

- 1,557 positive pre-May rows.
- 0 annual-target rows.
- 5 loose rows.
- 0 strict rows.
- 5 selected rows, all loose.

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

The selected rows were all ETHUSDT `regime_gap_session` rows with
`strict_consensus` quality. The Euclidean long rows traded seven times in May
and lost. The Lorentzian long rows did not trade in May.

## Interpretation

The multi-horizon KNN consensus label geometry found a small ETHUSDT
pre-May diagnostic pocket, but it did not produce annual-target or strict
month-stability rows and did not transfer to May. High-return pre-May rows
were rejected by the stability filters, while the only loose rows either lost
or went inactive in the benchmark holdout.

WPR106-182 therefore rejects this KNN variant as candidate-ready,
portfolio-ready, or promotion-ready. The ETHUSDT `regime_gap_session`
Euclidean-long pocket remains only a research clue.

## Artifacts

- `data/research/wpr106_182_multi_horizon_lorentzian_knn_consensus_search/pre_may/multi_horizon_knn_consensus_ranking.parquet`
- `data/research/wpr106_182_multi_horizon_lorentzian_knn_consensus_search/pre_may/multi_horizon_knn_consensus_top3000.csv`
- `data/research/wpr106_182_multi_horizon_lorentzian_knn_consensus_search/pre_may/multi_horizon_knn_consensus_monthly_returns.parquet`
- `data/research/wpr106_182_multi_horizon_lorentzian_knn_consensus_search/pre_may/family_feature_summary.parquet`
- `data/research/wpr106_182_multi_horizon_lorentzian_knn_consensus_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_182_multi_horizon_lorentzian_knn_consensus_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_182_multi_horizon_lorentzian_knn_consensus_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_182_multi_horizon_lorentzian_knn_consensus_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_182_multi_horizon_lorentzian_knn_consensus_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_182_multi_horizon_lorentzian_knn_consensus_search/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_182_multi_horizon_lorentzian_knn_consensus_search/selected_pre_may_may_comparison.parquet`
- `data/research/wpr106_182_multi_horizon_lorentzian_knn_consensus_search/wpr106_182_multi_horizon_lorentzian_knn_consensus_search_summary.json`

## Research Boundary

All outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. No candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim was created.

## Validation

Passed:

```powershell
python -m compileall -q data\research\wpr106_182_multi_horizon_lorentzian_knn_consensus_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
