# Stage R106 WPR146 Source-Level Stability Ablation Report

Date: 2026-06-12
Work packet: WPR106-166-wpr146-source-level-stability-ablation
Status: rejected as candidate-ready, portfolio-ready, and promotion-ready
evidence; WPR106-146 consensus threshold 5 retained as a research-only fresh
retest descriptor

## Scope

WPR106-166 ran a source-level stability and ablation audit around the WPR106-146
cross-symbol relative-strength trade-veto clue. WPR106-165 preserved this
pocket as the strongest research-only follow-up, but the evidence remains
post-hoc because WPR106-146 was already noticed through prior May 2026 benchmark
summaries.

All behavior-deduped row selection, raw-source comparisons, consensus-filter
thresholds, rolling diagnostics, side controls, and opposite-side controls used
only 2024-01-01 through 2026-04-30. May 2026 was benchmark-only after fixed
rows, controls, and consensus thresholds were selected.

The packet is research-only and observe-only. It writes no candidate pack, no
paper/live artifact, no live configuration, no sizing change, no order path,
and no promotion claim.

## Inputs

Read-only WPR106-146 artifacts:

- selected metrics: 48 rows;
- selected behavior diagnostics: 17 unique pre-May behavior hashes;
- selected pre-May trades: 9,148 rows;
- selected May benchmark trades: 572 rows;
- raw-source/no-KNN and side-control metrics/trades;
- WPR106-146/WPR106-136 accounting helpers for consistent metrics.

## Method

The runner performed five checks:

- behavior-deduped selection: one representative per pre-May behavior hash,
  ranked by pre-May strict/profile status, WPR106-136 strict status,
  pre-May score, return, losing months, concentration, and deterministic
  tie-breaks;
- raw-source path ablation: compare each behavior representative against the
  raw no-KNN source at the same daily cap by selected, common, excluded, and
  raw-only trades;
- rolling diagnostics: calendar-year and anchored future-window pre-May returns
  for fixed selected rows;
- opposite-side counterfactual: flip selected trade direction while preserving
  costs;
- behavior-consensus filters: count how many fixed behavior representatives
  accept each raw-source trade, select fixed vote thresholds from pre-May
  profile/strict metrics, then benchmark those thresholds on May.

## Behavior-Deduped Rows

The 48 WPR106-146 selected rows collapse to 17 pre-May behavior representatives.
All 17 representatives remain May-positive:

| Rows | Positive | Negative | Best | Worst | Median | Mean |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 17 | 17 | 0 | +0.067949 | +0.015398 | +0.030569 | +0.037985 |

The strongest representative is a `regime_reversal`, Lorentzian, same-side KNN
row with 64-trade lookback, 31 neighbors, threshold -0.00025, win-rate floor
0.46, and cap 5. It has 242 pre-May trades, 25 active months, four losing
months with annual losses 2/2/0, +1.140510 pre-May net, -0.145973 max drawdown,
best-month share 0.170868, and +0.067949 May.

## Raw-Source Path Coupling

Raw no-KNN source baselines are already May-positive:

| Raw baseline | Pre-May trades | Pre-May losing months | Annual losses | Pre-May net | May trades | May net |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| Cap 1 | 401 | 9 | 5/4/0 | +1.007245 | 16 | +0.048701 |
| Cap 3 | 451 | 7 | 4/3/0 | +1.209539 | 17 | +0.065272 |
| Cap 5 | 451 | 7 | 4/3/0 | +1.209539 | 17 | +0.065272 |

The behavior representatives improve the stability profile versus raw, but they
do not generally improve total raw-source return:

- Pre-May selected-minus-raw return is negative for 16 of 17 representatives,
  with median -0.112692 and mean -0.127724.
- May selected-minus-raw return is negative for 12 of 17 representatives, with
  median -0.029644 and mean -0.017540.

This confirms the positive May benchmark is tightly coupled to the same raw
WPR106-133 source path. The KNN variants are better described as stability
filters over a profitable raw source than as independent alpha.

## Side And Opposite Controls

Standalone side controls do not explain the stable behavior:

- Raw long controls are pre-May unstable and May-negative: cap 3 has 210
  pre-May trades, nine losing months, annual losses 3/6/0, +0.533107 pre-May,
  and -0.001938 May.
- Raw short controls are May-positive but pre-May unstable: cap 3 has 241
  pre-May trades, eleven losing months, annual losses 5/5/1, +0.676432
  pre-May, and +0.067211 May.
- Exact KNN long/short controls also fail pre-May profile checks.

Opposite-side counterfactuals are uniformly negative:

- Pre-May opposite-side rows: 17 negative, 0 positive, median -1.317360, mean
  -1.352005.
- May opposite-side rows: 17 negative, 0 positive, median -0.060833, mean
  -0.060580.

This supports direction-specific behavior and argues against a direction-
agnostic accounting artifact.

## Rolling Stability

The behavior representatives stay positive across the fixed pre-May rolling
checks:

| Window | Median negative months | Max negative months | Median return | Median worst month |
| --- | ---: | ---: | ---: | ---: |
| 2024 | 2 | 2 | +0.474211 | -0.060060 |
| 2025 | 2 | 4 | +0.348945 | -0.050464 |
| 2026 Jan-Apr | 1 | 1 | +0.121175 | -0.003438 |
| After 2024-12 | 3 | 5 | +0.462169 | -0.050464 |
| After 2025-06 | 2 | 2 | +0.349212 | -0.022296 |
| After 2025-12 | 1 | 1 | +0.121175 | -0.003438 |

These diagnostics support the stability clue, but they remain retrospective
because the WPR106-146 row family had already been discovered.

## Consensus Filters

Consensus filters were selected from pre-May evidence by requiring at least N
behavior representatives to accept a raw source trade. Eight of nine thresholds
were pre-May profile-ok; three were strict-like.

| Vote threshold | Strict-like | Pre-May trades | Active months | Losing months | Annual losses | Pre-May net | May trades | May net |
| ---: | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| 1 | No | 354 | 26 | 8 | 4/4/0 | +1.531862 | 17 | +0.065272 |
| 3 | No | 318 | 26 | 7 | 3/4/0 | +1.289746 | 17 | +0.065272 |
| 5 | Yes | 254 | 26 | 2 | 1/1/0 | +1.155278 | 17 | +0.065272 |
| 8 | No | 157 | 26 | 5 | 3/2/0 | +1.024284 | 9 | +0.036621 |
| 10 | Yes | 104 | 25 | 4 | 2/1/1 | +0.872218 | 7 | +0.033639 |
| 12 | Yes | 87 | 24 | 4 | 2/1/1 | +0.797090 | 4 | +0.015398 |
| 15 | No | 52 | 22 | 5 | 2/0/3 | +0.565925 | 4 | +0.015398 |

The threshold-5 consensus filter is the clearest descriptor for fresh retesting:
it has 254 pre-May trades, 26 active months, only two losing months total
across 2024 through 2026 Apr, annual losses 1/1/0, +1.155278 pre-May net,
-0.141007 max drawdown, best-month share 0.146280, full cost-stress survival,
and +0.065272 May.

The threshold-5 May result matches the raw cap 3/5 May return, so it is not
independent May evidence. It is a cleaner pre-May stability filter over the raw
source path, not a candidate-ready strategy.

## Decision

WPR106-166 rejects the WPR106-146 source-level ablation as candidate-ready,
portfolio-ready, or promotion-ready evidence.

The packet strengthens the research-only clue:

- the behavior-deduped WPR106-146 representatives are all May-positive;
- the opposite-side controls are uniformly negative;
- side-only controls are unstable;
- the threshold-5 consensus filter reaches the requested month-to-month
  stability profile on pre-May evidence.

The packet also confirms the main weakness:

- raw WPR106-133 cap 3/5 is already May-positive at +0.065272;
- selected KNN representatives usually underperform raw total return;
- the best consensus May benchmark is the same raw-source May path;
- May is not a fresh independent discovery holdout.

The next useful step is a fresh non-May retest of the threshold-5 consensus
descriptor, preferably by rebuilding the direct strategy/feature path outside
the WPR106-146 artifact selection loop and using any available post-May data
other than May 2026 as a new holdout. If no later data is locally available,
the descriptor should remain a research-only clue until additional archive data
is added.

No candidate pack, paper/live artifact, order path, sizing change, runtime-mode
change, live config write, CUDA speedup claim, or promotion claim exists.

## Artifacts

- Runner:
  `data/research/wpr106_166_wpr146_source_level_stability_ablation/scripts/run_wpr106_166_wpr146_source_level_stability_ablation.py`
- Summary:
  `data/research/wpr106_166_wpr146_source_level_stability_ablation/wpr106_166_wpr146_source_level_stability_ablation_summary.json`
- Behavior-deduped rows:
  `data/research/wpr106_166_wpr146_source_level_stability_ablation/pre_may/behavior_deduped_selected_rows.parquet`
- Source-path ablations:
  `data/research/wpr106_166_wpr146_source_level_stability_ablation/pre_may/source_path_ablation_pre_may.parquet`
  and
  `data/research/wpr106_166_wpr146_source_level_stability_ablation/may_benchmark/source_path_ablation_may.parquet`
- Rolling stability diagnostics:
  `data/research/wpr106_166_wpr146_source_level_stability_ablation/pre_may/rolling_stability_diagnostics.parquet`
- Opposite-side controls:
  `data/research/wpr106_166_wpr146_source_level_stability_ablation/pre_may/opposite_side_counterfactual_pre_may.parquet`
  and
  `data/research/wpr106_166_wpr146_source_level_stability_ablation/may_benchmark/opposite_side_counterfactual_may.parquet`
- Consensus metrics:
  `data/research/wpr106_166_wpr146_source_level_stability_ablation/pre_may/consensus_filter_pre_may_and_may_metrics.parquet`

## Validation

Passed:

- `python -m compileall -q data/research/wpr106_166_wpr146_source_level_stability_ablation/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`

Contract result: 460 passed.
