# Stage R106 Pre-May Cluster-Aware Portfolio Search Report

Date: 2026-06-11
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR106-100-pre-may-cluster-aware-portfolio-search.md`

## Scope

WPR106-100 turns the WPR106-99 component diagnosis into a pre-May-only
cluster-aware portfolio search. The optimization window is 2024-01-01 through
2026-04-30. May 2026 is held out completely until after fixed pre-May lead
selection.

The recombination universe is the 36 packet-qualified WPR106-95 positive
sleeves already replayed through May by WPR106-97. This keeps the search
bounded and ensures every selected lead can receive a benchmark-only May view
without a new data dependency.

No May 2026 row was used for strategy choice, feature choice, filter choice,
threshold choice, parameter changes, optimizer feedback, ranking, filtering,
or portfolio selection.

## Method

The runner reloads original WPR106-95 pre-May sleeve trades, builds monthly
return vectors and daily trade-count matrices, then vectorizes chunked
enumeration of all 2-to-6 sleeve combinations from the 36-sleeve May-ready
pool.

Pre-May ranking terms include:

- full-year losing-month caps for 2024 and 2025;
- partial 2026 Jan-Apr losing-month cap;
- total losing-month cap;
- active-month coverage;
- 1 to 5 trades per active day;
- overlap-day share;
- positive-month concentration;
- cost-stress survival and split concentration;
- unique candidate, core-parameter, and monthly-behavior fingerprints;
- symbol/family diversity.

May benchmark rows are joined only after the selected pre-May lead list is
fixed, using WPR106-97 May member trades and equal-sleeve accounting.

Primary artifacts:

- Summary:
  `data/research/wpr106_100_pre_may_cluster_aware_portfolio_search/wpr106_100_cluster_search_summary.json`
- Runner:
  `data/research/wpr106_100_pre_may_cluster_aware_portfolio_search/scripts/run_wpr106_100_cluster_search.py`
- May-ready sleeve universe:
  `data/research/wpr106_100_pre_may_cluster_aware_portfolio_search/pre_may/wpr106_100_may_ready_sleeve_universe.csv`
- Ranked top parquet and compact CSV:
  `data/research/wpr106_100_pre_may_cluster_aware_portfolio_search/pre_may/wpr106_100_cluster_aware_ranked_top.parquet`
  and
  `data/research/wpr106_100_pre_may_cluster_aware_portfolio_search/pre_may/wpr106_100_cluster_aware_ranked_top500.csv`
- Selected pre-May leads:
  `data/research/wpr106_100_pre_may_cluster_aware_portfolio_search/pre_may/wpr106_100_cluster_aware_selected_leads.csv`
- May benchmark:
  `data/research/wpr106_100_pre_may_cluster_aware_portfolio_search/may_benchmark/wpr106_100_selected_lead_may_benchmark.csv`

## Results

Search counts:

- May-ready sleeves: 36
- Combination sizes: 2 through 6 sleeves
- Evaluated combinations: 2,391,459
- Combinations inside 1 to 5 trades per active day: 2,391,458
- Full-year target hits with no more than 2 losing months in both 2024 and
  2025: 7,929
- Strict cluster-filter hits after all controls: 1
- Selected pre-May leads benchmarked on May: 40

Strict pre-May cluster-aware lead:

| Selected rank | Combo | Sleeves | Pre-May return | Trades/active day | Overlap-day share | Losing months | 2024 losing | 2025 losing | 2026 Jan-Apr losing | May return |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `combo100-8e6136c0927425b1` | 5 | +0.969026 | 1.758 | 0.507 | 5 | 2 | 2 | 1 | -0.007165 |

The strict lead improves the pre-May annual profile relative to WPR106-98:
both full pre-May years meet the 0-to-2 losing-month target, and the partial
2026 window has one losing month. Its losing months are 2024-09, 2024-12,
2025-06, 2025-12, and 2026-04.

The May benchmark rejects it as a clean lead:

- May return: -0.007165
- May trades: 35
- May active days: 26
- May trades per active day: 1.346
- May overlap-day share: 0.346
- May positive days: 8
- May losing days: 18

The May drag is component-level and consistent with earlier evidence. The
strict lead includes the WPR106-88 BTCUSDT `fbbe` volatility sleeve, which
contributes -0.020880 weighted in May, plus two ETHUSDT sparse-event sleeves
with negative May contribution. Its BTCUSDT WPR106-91 and WPR106-94 volatility
sleeves are positive in May but do not fully offset those losses.

Selected-lead May benchmark:

- 16 of 40 selected pre-May leads are positive in May.
- 24 of 40 selected pre-May leads are negative in May.
- The best May row is selected rank 10, `combo100-413f32790600ecca`, with
  +0.036318 May return, but it has 4 losing months in 2024 and therefore does
  not meet the full-year stability target.
- The WPR106-98 rank-1 portfolio reappears as selected rank 7 with +0.031402
  May return, but it still has 4 losing months in 2024.

## Interpretation

WPR106-100 finds one true pre-May cluster-aware improvement: a five-sleeve
portfolio that satisfies the requested full-year losing-month cap in both 2024
and 2025 while keeping active frequency in the accepted 1-to-5 trades/day
range. That is useful research progress because WPR106-98 and WPR106-99 did
not find a selected lead with both full years inside the target.

The May holdout does not confirm it. The strict lead is slightly negative in
May, with more losing than positive active days. Positive May rows exist in the
selected set, but they are less stable pre-May and fail the annual
losing-month objective. The result is therefore a research-only rejection, not
a candidate-ready outcome.

The next useful research direction is not to defend this exact five-sleeve
lead. It is to use the stricter pre-May objective as a scoring primitive in a
new family-level search: build strategies or filters that avoid the 2024-09 /
2024-12 / 2025-06 / 2025-12 loss clusters without needing the May-weak `fbbe`
sleeve for pre-May annual stability.

## Boundary

All outputs are research-only, observe-only, and promotion-ready false. No
candidate pack, paper/live artifact, order placement, position sizing,
runtime-mode change, live-configuration write, CUDA speedup claim, or
promotion claim was created.

## Validation

Passed:

- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` with 460 passed
