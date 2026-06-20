# WPR106-170 Path-Quality KNN Event-Veto Search

Status: closed
Owner: Codex Research Agent
Date: 2026-06-12

## Objective

Continue the 2024-forward broad research search after WPR106-169 rejected the
bar-state/flow interaction screen. Test a materially different Lorentzian/KNN
variant: a causal event-veto layer over transparent completed-bar entries,
where neighbors are labeled by future return and path quality rather than only
fixed-hold direction.

## Scope

Default tuning/search window:

- 2024-01-01 00:00:00 UTC through 2026-04-30 23:59:59 UTC.

Benchmark holdout:

- 2026-05-01 through 2026-05-31 UTC.

May 2026 must not be used for feature choice, event-family choice, label
definition, KNN parameter choice, threshold choice, ranking, filtering, or
selection. It may only be replayed after fixed pre-May rows are selected.

The packet is artifact-only unless a blocking correctness issue is discovered.

## Allowed Paths

- `docs/work_packets/WPR106-170-path-quality-knn-event-veto-search.md`
- `docs/stage_reports/STAGE_R106_PATH_QUALITY_KNN_EVENT_VETO_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_170_path_quality_knn_event_veto_search/**`

## Plan

1. Load WPR106-96 verified BTCUSDT/ETHUSDT 15m and 1m aggTrade source context.
2. Build completed-bar feature and path-label caches without May-driven tuning.
3. Generate transparent event candidates across momentum, pullback, breakout,
   wick absorption, range reversion, and cross-symbol families.
4. Evaluate causal Lorentzian and Euclidean event-veto variants using only
   prior completed neighbor labels; cap accepted trades at 1, 3, or 5 per day.
5. Rank on pre-May monthly stability, annual losing-month profile, drawdown,
   cost stress, trade count, overlap, and concentration.
6. Replay only fixed promising/loose pre-May rows on May 2026 as a benchmark.
7. Write research-only artifacts, report, ledger update, and validation notes.

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
python -m compileall -q data\research\wpr106_170_path_quality_knn_event_veto_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Result

Completed as an artifact-only research packet. The runner evaluated 93,312
pre-May rows across BTCUSDT/ETHUSDT, six transparent event families, two KNN
feature packs, three fixed-hold horizons, Lorentzian/Euclidean distances,
11/31 neighbors, all/Asia/US sessions, 1/3/5 target raw events per active day,
long/short/both side modes, path-good-rate and mean-neighbor-return filters,
and 1/3/5 accepted-trade daily caps.

Pre-May results found 21,314 positive rows, 2,928 annual-target rows, 79 loose
rows, and zero strict rows. The fixed selected set had 79 loose rows with
median +0.211822 pre-May return, six to eight losing months, and median 1.0678
trades per active day.

May 2026 was benchmark-only after fixed pre-May selection. It rejected the
selected set: zero selected rows were May-positive, 25 were May-negative, 54
were May-flat because no May trades passed the fixed filter, and no May row
survived positive cost stress.

Decision: reject this path-quality KNN event-veto formulation as
candidate-ready, portfolio-ready, or promotion-ready evidence. The result is
useful negative evidence for a materially different KNN label target, but it
does not produce a lead.

Validation passed: scoped script compile, `src/tradingbotsuite` compile, and
contracts. Contracts reported 460 passed.
