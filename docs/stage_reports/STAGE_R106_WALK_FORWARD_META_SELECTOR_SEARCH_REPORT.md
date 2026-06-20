# Stage R106 Walk-Forward Meta-Selector Search Report

Date: 2026-06-11
Work packet: `docs/work_packets/WPR106-110-walk-forward-meta-selector-search.md`
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It uses
only 2024-01-01 through 2026-04-30 evidence for candidate pool filtering,
policy definition, score weights, lookback windows, ranking, and selection.
May 2026 is excluded from all tuning and selection. May is loaded only after
pre-May policies are selected, and only as a benchmark holdout. No candidate
pack, paper/live artifact, order placement, sizing change, runtime-mode change,
live configuration write, CUDA speedup claim, or promotion claim is made.

## Method

The artifact runner tests a causal monthly meta-selector over recent
pre-May-selected research rows from WPR106-105 through WPR106-109. The source
rows already include post-cost monthly returns. The meta-policy chooses source
rows for each month using only completed prior months, then records the next
month's already-costed source returns as an equal-weight or positive-score
weighted monthly portfolio.

Source pool:

| Source | Selected Rows Loaded | Monthly Rows Loaded |
| --- | ---: | ---: |
| WPR106-105 bar-path/flow | 3 | 84 |
| WPR106-106 dense causal score | 369 | 10,332 |
| WPR106-107 rolling Lorentzian/KNN | 27 | 756 |
| WPR106-108 cross-asset relative value | 81 | 2,268 |
| WPR106-109 session anchor | 150 | 4,200 |

The runner loaded 630 source rows and removed 81 duplicate monthly behavior
fingerprints, leaving 549 unique candidate rows. The duplicate removal mainly
prevents identical source behavior, such as equivalent WPR106-108 beta variants,
from being counted twice by a meta-policy.

Policy grid:

- lookback windows: 1, 2, 3, 6, and 12 completed months;
- top-k source rows: 1, 2, 3, 5, and 8;
- score modes: trailing mean, downside-adjusted, hit-stability, and
  persistence;
- weights: equal and positive-score proportional;
- source filters: cost-stress survival floors, source losing-month caps,
  source return floors, and source group caps.

Important limitation: this packet recombines source rows at monthly resolution.
The source rows are costed and have source-level active-rate evidence, but
cross-source intramonth trade overlap, correlated execution, and trade-level
drawdown are not replayed here. Any positive result from this packet would
require a later trade-level replay before candidate-pack use.

## Results

The screen evaluated 28,800 monthly meta-policies. It found 28,728 positive
pre-May policies, 10,051 loose pre-May policies, and 985 strict monthly-artifact
policies.

| Scope | Rows |
| --- | ---: |
| Candidate pool rows after duplicate removal | 549 |
| Evaluated policy rows | 28,800 |
| Positive pre-May policy rows | 28,728 |
| Loose pre-May policy rows | 10,051 |
| Strict pre-May policy rows | 985 |
| Selected May benchmark policies | 100 |
| May-positive selected policies | 0 |
| May-negative selected policies | 100 |
| May-flat selected policies | 0 |

The rank-1 pre-May policy looked strong inside the pre-May monthly artifacts:

| Policy | Lookback | Top-K | Score | Weight | Pre-May Return | Active Months | Losing Months | Annual Losses | Max DD | May Return | May Trades |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| `wfmeta-230ed7fe71bc2ed0` | 1 | 8 | trailing mean | equal | +1.140045 | 27 | 3 | 2024: 1, 2025: 1, 2026 Jan-Apr: 1 | -0.083523 | -0.044406 | 77 |

The policy's pre-May stability is not enough evidence. It has very high monthly
membership turnover, with average Jaccard turnover of 0.963234. Its May
selection used the final completed pre-May month as the one-month lookback and
chose eight rows; all eight contributed negatively or weakly in May:

| Source | Candidate | Family | May Return |
| --- | --- | --- | ---: |
| WPR106-108 | `xasset-2716268f5bfa48d8` | ETH single-leg lead-lag | -0.039128 |
| WPR106-108 | `xasset-12e3309b6afdacb8` | ETH single-leg lead-lag | -0.011490 |
| WPR106-106 | `dense-3fa4b0fb54abcd55` | BTC balanced | -0.047988 |
| WPR106-106 | `dense-18b7cfbfc1150afb` | BTC balanced | -0.025427 |
| WPR106-106 | `dense-53a705d92efbb3ac` | ETH momentum | -0.068148 |
| WPR106-106 | `dense-5c4fd628807044e3` | ETH calendar-flow | -0.004124 |
| WPR106-106 | `dense-c97cbc47d75d2c94` | ETH session-drift | -0.061804 |
| WPR106-106 | `dense-dfbc11113b4b0493` | ETH momentum | -0.097138 |

All selected policies were May-negative. The best selected May result was still
-0.008727. Across the 100 selected policies, May return distribution was:

| Metric | May Return |
| --- | ---: |
| Mean | -0.039973 |
| Median | -0.043546 |
| Best | -0.008727 |
| Worst | -0.069622 |

The source rows selected for May across the selected policies were concentrated
in families that previous packets already found May-fragile:

| Source / Family | May Member Rows | Unique Source Rows | Average Member May Return |
| --- | ---: | ---: | ---: |
| WPR106-108 ETH single-leg lead-lag | 141 | 4 | -0.034579 |
| WPR106-106 ETH momentum | 116 | 7 | -0.060641 |
| WPR106-106 BTC balanced | 74 | 2 | -0.040366 |
| WPR106-106 ETH session-drift | 69 | 2 | -0.074583 |
| WPR106-106 ETH calendar-flow | 53 | 1 | -0.004124 |

## Interpretation

The walk-forward selector can make the pre-May monthly table look stable, but
May rejects the selected policies decisively. The result is useful because it
tests a broader adaptive idea over many previously rejected/fresh rows without
May leakage: if recent-month winner rotation were enough to repair month
stability, at least some selected policies should have survived the fixed May
benchmark. None did.

The strict pre-May count is therefore not a candidate-ready finding. It is a
monthly-artifact diagnostic. The policies have high turnover, rely on source
rows already known to be May-fragile, and lack trade-level overlap replay. The
proper decision is fail-closed: no meta-selector lead is eligible for a
candidate pack or promotion.

## Artifacts

- `data/research/wpr106_110_walk_forward_meta_selector_search/scripts/run_wpr106_110_walk_forward_meta_selector_search.py`
- `data/research/wpr106_110_walk_forward_meta_selector_search/wpr106_110_walk_forward_meta_selector_summary.json`
- `data/research/wpr106_110_walk_forward_meta_selector_search/wpr106_110_runner.log`
- `data/research/wpr106_110_walk_forward_meta_selector_search/pre_may/candidate_pool.parquet`
- `data/research/wpr106_110_walk_forward_meta_selector_search/pre_may/candidate_monthly_returns.parquet`
- `data/research/wpr106_110_walk_forward_meta_selector_search/pre_may/policy_ranking.parquet`
- `data/research/wpr106_110_walk_forward_meta_selector_search/pre_may/selected_pre_may_policies.parquet`
- `data/research/wpr106_110_walk_forward_meta_selector_search/pre_may/selected_policy_monthly_returns.parquet`
- `data/research/wpr106_110_walk_forward_meta_selector_search/pre_may/selected_policy_membership.parquet`
- `data/research/wpr106_110_walk_forward_meta_selector_search/may_benchmark/source_candidate_may_returns.parquet`
- `data/research/wpr106_110_walk_forward_meta_selector_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_110_walk_forward_meta_selector_search/may_benchmark/selected_may_membership.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_110_walk_forward_meta_selector_search/scripts`: passed.
- `python -m compileall -q src/tradingbotsuite`: passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`: 460 passed.
