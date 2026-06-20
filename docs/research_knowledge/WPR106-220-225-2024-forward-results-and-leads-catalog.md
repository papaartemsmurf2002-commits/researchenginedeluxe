# WPR106-220 Through WPR106-225 2024-Forward Results And Leads Catalog

Status: research-only, observe-only, promotion-ready false.
Catalog date: 2026-06-18.
Catalog packet: WPR106-226.

## Purpose

This catalog consolidates the recent 2024-forward strategy research sequence
from WPR106-220 through WPR106-225. It records what was tested, where the
artifacts live, what validation passed, which results are rejected, and which
research leads remain worth pursuing.

This is not candidate-ready, paper-ready, live-ready, or promotion-ready
evidence. No candidate pack was created by these packets.

## Evidence Boundary

- Default optimization and selection window: 2024-01-01 through 2026-04-30.
- May 2026 is benchmark-only and must not be used for tuning.
- High activity is allowed when costs, overlap, daily caps, and monthly
  stability are reported.
- All listed outputs remain `research_only`, `observe_only`, and
  `promotion_ready: false`.
- CUDA was not used in these packets and no CUDA speedup claim exists.

## Documentation Integrity Note

During WPR106-226, the WPR106-220 through WPR106-225 work packet and stage
report markdown files were found to be NUL-filled. WPR106-226 reconstructed
those markdown anchors from the preserved summary JSON files, Parquet
artifacts, and orchestrator ledger entries. The authoritative numeric evidence
remains the summary JSON and Parquet outputs under each `data/research`
packet directory.

## Packet Catalog

| Packet | Family | Work Packet | Stage Report | Summary JSON | Final Decision |
| --- | --- | --- | --- | --- | --- |
| WPR106-220 | WPR199 source-control expansion | `docs/work_packets/WPR106-220-wpr199-source-control-stability-expansion.md` | `docs/stage_reports/STAGE_R106_WPR199_SOURCE_CONTROL_STABILITY_EXPANSION_REPORT.md` | `data/research/wpr106_220_wpr199_source_control_stability_expansion/wpr106_220_wpr199_source_control_stability_expansion_summary.json` | Rejected: strong pre-May, May failed |
| WPR106-221 | Transparent motif active fallback | `docs/work_packets/WPR106-221-transparent-motif-active-fallback-repair.md` | `docs/stage_reports/STAGE_R106_TRANSPARENT_MOTIF_ACTIVE_FALLBACK_REPAIR_REPORT.md` | `data/research/wpr106_221_transparent_motif_active_fallback_repair/wpr106_221_transparent_motif_active_fallback_repair_summary.json` | Rejected: May positive, annual loss profile misses |
| WPR106-222 | Directional KNN source stability | `docs/work_packets/WPR106-222-directional-knn-source-stability-repair.md` | `docs/stage_reports/STAGE_R106_DIRECTIONAL_KNN_SOURCE_STABILITY_REPAIR_REPORT.md` | `data/research/wpr106_222_directional_knn_source_stability_repair/wpr106_222_directional_knn_source_stability_repair_summary.json` | Rejected: May nonnegative but too sparse |
| WPR106-223 | Dense KNN source generation | `docs/work_packets/WPR106-223-dense-knn-source-generation-search.md` | `docs/stage_reports/STAGE_R106_DENSE_KNN_SOURCE_GENERATION_SEARCH_REPORT.md` | `data/research/wpr106_223_dense_knn_source_generation_search/wpr106_223_dense_knn_source_generation_search_summary.json` | Rejected: denser May, worse loss-month stability |
| WPR106-224 | Dense KNN path-managed exits | `docs/work_packets/WPR106-224-dense-knn-path-managed-exit-repair.md` | `docs/stage_reports/STAGE_R106_DENSE_KNN_PATH_MANAGED_EXIT_REPAIR_REPORT.md` | `data/research/wpr106_224_dense_knn_path_managed_exit_repair/wpr106_224_dense_knn_path_managed_exit_repair_summary.json` | Rejected: exits help, but no strict rows |
| WPR106-225 | Cross-family loss-cluster complement | `docs/work_packets/WPR106-225-cross-family-loss-cluster-complement-search.md` | `docs/stage_reports/STAGE_R106_CROSS_FAMILY_LOSS_CLUSTER_COMPLEMENT_SEARCH_REPORT.md` | `data/research/wpr106_225_cross_family_loss_cluster_complement_search/wpr106_225_cross_family_loss_cluster_complement_search_summary.json` | Rejected: pre-May strict rows failed May |

## Result Summary

| Packet | Pre-May Search Rows | Selected Rows | Selected Pre-May Median | Median Active Months | Median Losing Months | Strict Selected Rows | May Positive/Negative/Flat | May Median | May Active Mean | Verdict |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- |
| WPR106-220 | 24,632 | 120 | +0.637255 | 26 | 4 | 59 | 29 / 86 / 5 | -0.005859 | -0.007629 | Reject May transfer |
| WPR106-221 | 13,824 | 140 | +0.446878 | 27 | 6 | 0 | 113 / 27 / 0 | +0.011323 | +0.010638 | Lead, but annual loss count fails |
| WPR106-222 | 17,024 | 160 | +0.464644 | 24 | 5 | 68 | 137 / 0 / 23 | +0.001407 | +0.001413 | Lead, but too sparse |
| WPR106-223 | 139,968 base plus 220 gated | 71 | +0.200877 | 24 | 8 | 0 | 43 / 0 / 28 | +0.001341 | +0.004476 | Reject loss-month stability |
| WPR106-224 | 2,556 exit-policy rows | 140 | +0.314421 | 21 | 7 | 0 | 73 / 0 / 67 | +0.000994 | +0.006685 | Lead clue only |
| WPR106-225 | 14,040 portfolio specs | 180 | +0.612399 | 27 | 4 | 80 | 2 / 178 / 0 | -0.005795 | -0.006737 | Reject selector overfit |

## Validation Catalog

Each packet preserved the branch validation baseline for its scoped work:

```powershell
python -m compileall -q data\research\<packet>\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

| Packet | Packet Script Compile | Package Compile | Contracts | Notes |
| --- | --- | --- | --- | --- |
| WPR106-220 | Passed per ledger | Passed per ledger | Passed per ledger | Older report reconstructed from JSON/ledger |
| WPR106-221 | Passed per ledger | Passed per ledger | Passed per ledger | Older report reconstructed from JSON/ledger |
| WPR106-222 | Passed per ledger | Passed per ledger | Passed per ledger | Older report reconstructed from JSON/ledger |
| WPR106-223 | Passed per ledger | Passed per ledger | Passed per ledger | Dense KNN used NumPy prediction caches, not CUDA |
| WPR106-224 | Passed | Passed | 460 passed | Exit-only artifact replay |
| WPR106-225 | Passed | Passed | 460 passed | Cross-family artifact replay |
| WPR106-226 | Not applicable, docs only | Passed | 460 passed | Catalog and markdown reconstruction |

## Artifact Checklist

For each packet, the key artifact groups are:

- `wpr106_*_summary.json`: top-level run metadata, boundary flags, and result summaries.
- `pre_may/*ranking*.parquet` or `pre_may/*rows.parquet`: pre-May selection and ranking evidence.
- `pre_may/selected_pre_may_*metrics.parquet`: fixed selected-row pre-May replay metrics.
- `pre_may/selected_pre_may_*monthly_returns.parquet`: monthly stability evidence.
- `pre_may/selected_pre_may_*trades.parquet`: costed selected pre-May trades.
- `may_benchmark/selected_may_benchmark_metrics.parquet`: fixed-row May benchmark metrics.
- `may_benchmark/selected_may_benchmark_monthly_returns.parquet`: May benchmark monthly return evidence.
- `may_benchmark/selected_may_benchmark_trades.parquet`: costed selected May trades.
- `selected_pre_may_may_comparison.parquet`: pre-May versus May comparison where emitted.

## Leads Worth Continuing

### Transparent Motif Fallback

Source packet: WPR106-221.

Why it remains interesting:

- May benchmark was positive for 113 of 140 selected rows.
- Median May return was +0.011323 with all selected rows active.
- Pre-May activity was broad: median 27 active months and median 651 trades.

Why it is not ready:

- Zero selected strict rows and zero selected annual-target rows.
- Median losing months remained six.
- The best active rows still missed the annual loss-month target because 2024
  had too many losing months.

Useful next work:

- Keep the opening fallback idea, but split or gate the 2024 loss months.
- Test fallback sleeve diversity without relying on the old canonical motif.
- Add pseudo-holdout inside pre-May before May is benchmarked.

### Directional KNN Source-Level Gating

Source packet: WPR106-222.

Why it remains interesting:

- All 17,024 pre-May portfolio rows were positive.
- Selected rows had 68 strict rows and 111 annual-target rows.
- May was nonnegative: 137 positive, zero negative, 23 flat.

Why it is not ready:

- May activity was sparse, with median May trade count one.
- Median selected rows still had four inactive pre-May months.
- No selected row combined all 28 active pre-May months with five or fewer
  losing months.

Useful next work:

- Generate denser source paths before portfolio composition.
- Preserve source-before-portfolio gates and mixed WPR106-190/WPR106-213 pairs.
- Add source-family pseudo-holdouts so pre-May strength is not selected from a
  single favorable regime.

### Dense KNN Flow-Wick Feature Path

Source packets: WPR106-223 and WPR106-224.

Why it remains interesting:

- `flow_wick_density` transferred best among dense KNN feature packs.
- WPR106-224 target-only exits improved WPR106-223 median pre-May return from
  +0.200877 to +0.314421 and reduced median losing months from eight to seven.
- May stayed nonnegative in WPR106-224: 73 positive, zero negative, 67 flat.

Why it is not ready:

- WPR106-223 had zero strict rows and median eight losing months.
- WPR106-224 still had zero strict rows, median 21 active months, and median
  seven losing months.
- Best near-misses still failed because 2025 loss clusters remained.

Useful next work:

- Change KNN feature/label construction before exit overlays.
- Focus on reducing 2025 loss clusters before monthly gates.
- Keep target-only exits as a diagnostic, but do not expect exits alone to
  repair the family.

## Falsified Or Control Paths

### WPR106-220 WPR199 Source Control

WPR106-220 was strong pre-May but failed May with 29 positive, 86 negative,
and five flat rows. WPR106-225 then showed that selectors can overfit to
WPR106-220: every selected cross-family portfolio included WPR106-220 and
every selected cross-family complement was May-negative.

Use WPR106-220 as a control or ablation source, not as a dominant selector
source.

### Cross-Family Complement Selector

WPR106-225 looked excellent pre-May with 80 strict selected rows and 140
annual-target selected rows, but May rejected it with two positive and 178
negative selected rows. The conclusion is not that portfolio complements are
impossible; the conclusion is that this selector needs source-family caps,
family pseudo-holdouts, and transfer-risk penalties before May is benchmarked.

## Current Best Next Packet Direction

The next research packet should not tune on May. A practical next direction is
a pre-May source-family pseudo-holdout selector:

- Split the 2024-01-01 through 2026-04-30 window into family-selection and
  pseudo-holdout folds.
- Keep WPR106-220 as a control/ablation source rather than a selectable
  dominant source.
- Prioritize WPR106-221 fallback rows and WPR106-222/WPR106-224 KNN rows that
  survive pseudo-holdouts.
- Score for annual loss distribution, active coverage, cost-stress survival,
  and loss-cluster reduction before fixed May benchmarking.
- Use May 2026 only after selected rows are fixed.

## Final Status

No candidate-ready, portfolio-ready, paper/live-ready, or promotion-ready
strategy exists from WPR106-220 through WPR106-225. The useful leads are
research leads only:

- transparent motif active fallback repair;
- source-before-portfolio directional KNN gates;
- `flow_wick_density` dense KNN with target-only exit diagnostics;
- pre-May pseudo-holdout source-family selection as the next selector repair.
