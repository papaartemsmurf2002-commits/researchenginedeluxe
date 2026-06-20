# WPR106-227 Repo State Research Performance Correlation Audit

Status: research-only, observe-only, promotion-ready false.
Audit date: 2026-06-18.
Packet: WPR106-227.

## Purpose

This report records the current local checkout state, the observable
local-versus-GitHub difference, the local WPR106 research artifact inventory,
the strongest performance rows discovered, and the main pre-May versus May
correlation diagnostics. It is written for the next agent so they can continue
research from evidence instead of re-reading every packet.

This is not candidate-ready, paper-ready, live-ready, sizing, runtime, or
promotion evidence. No candidate pack was created.

## Deliverables

- Workbook:
  `outputs/019ed9da-c03f-7a01-ba1a-8a28806bc270/repo_research_performance_correlation_audit.xlsx`
- Extracted audit data:
  `outputs/019ed9da-c03f-7a01-ba1a-8a28806bc270/research_audit_data.json`
- Normalized CSV extracts:
  `research_summary_rows.csv`, `research_detail_rows.csv`,
  `research_correlation_rows.csv`, and `stage_report_inventory.csv`
- Workbook previews:
  `outputs/019ed9da-c03f-7a01-ba1a-8a28806bc270/workbook_previews/`

The workbook has seven sheets:

1. `Dashboard`
2. `Curated Leads`
3. `Packet Summary`
4. `Correlations`
5. `Top Detail Rows`
6. `Repo State`
7. `Report Inventory`

## Repo State

Local branch state at audit time:

- Current branch: `main`
- Local `HEAD`: `0be5e0d5892443df1e34804f3a819c26f9c5ed03`
- Fetched `origin/main`: `3f4b45ce3f8ecca3e21def076d99ddca5db4ecf0`
- Fresh `git ls-remote origin refs/heads/main`: `3f4b45ce3f8ecca3e21def076d99ddca5db4ecf0`
- Ahead/behind versus fetched `origin/main`: `0 1`
- Remote-only commit:
  `3f4b45c docs: add Harvard Algorithmic Trading repomix transfer report`
- Remote-only file:
  `docs/external_repo_analysis/harvard_algorithmic_trading_ai_repomix_transfer.md`
  with 1,029 insertions.

Initial fetch/API attempts failed with local DNS/socket resource errors, but a
later `git fetch --prune origin` succeeded and made the exact GitHub diff
visible.

Working tree relative to fetched `origin/main`:

- Tracked changed files: 57
- Untracked files at extraction time: 388
- Diff shortstat against fetched `origin/main`: 58 files changed, 10,927
  insertions, 1,555 deletions. The extra deletion count includes the
  remote-only Harvard repomix report that is present on `origin/main` but not in
  local `HEAD`.
- Major local areas: WPR106 research reports/work packets/configs, research
  runner/operator/UI/source changes, generated local research artifact
  directories, and the new WPR106-227 audit outputs.

Do not treat the local tree as a clean GitHub mirror. The local research state
has a large uncommitted/untracked WPR106 research wave, while GitHub has one
additional documentation commit not present in local `HEAD`.

## Artifact Inventory

The extractor scanned packet-shaped local research artifacts rather than
recursing blindly through all cache trees.

| Item | Count |
| --- | ---: |
| WPR106 data directories under `data/research` | 144 |
| Root-level WPR106 summary JSON files | 142 |
| Parquet result files read for packet/comparison diagnostics | 213 |
| Normalized top/detail rows written to workbook | 3,698 |
| Correlation/summary diagnostics written to workbook | 218 |
| Stage R106 reports inventoried | 212 |
| WPR106 work packets present | 227 |

Several WPR106-220 through WPR106-225 markdown anchors were previously found
NUL-filled and reconstructed by WPR106-226. Numeric authority for those packets
is the summary JSON and Parquet evidence under `data/research`.

## Best Leads If Hard Gates And Month Stability Are Ignored

The following ranking intentionally ignores hard promotion gates and broad
month-stability requirements, as requested. It does not ignore data leakage,
research/live boundaries, or whether May/post-selection transfer evidence is
weak. "Promising" means worth a further research packet, not candidate-ready.

| Rank | Packet | Lead | Evidence | Read |
| ---: | --- | --- | --- | --- |
| 1 | WPR106-146 | ETH relative-strength KNN trade-veto overlay | 48/48 selected rows May-positive; top row +1.140510 pre-May, +0.067949 May, 242 pre-May trades, 25 active months, 4 losing months. | Strongest narrow lead. Mechanism is plausible and May transfer is unusually clean, but behavior is clustered and path-coupled to WPR106-133 raw source. |
| 2 | WPR106-214 | Transparent motif replacement portfolio | 120/120 selected rows positive pre-May; median +0.595252 pre-May; May 94 positive / 26 negative with median +0.026679. | Strong broad transfer if hard gates/month stability are ignored. More robust than the original motif cluster. |
| 3 | WPR106-221 | Transparent motif active fallback repair | 13,534 positive pre-May rows; selected median +0.446878 pre-May; May 113 positive / 27 negative; median May +0.011323. | Good follow-up lead: broad activity, positive May median, no single-row-only dependence. |
| 4 | WPR106-222 | Directional KNN source-level gating | 17,024/17,024 positive pre-May portfolio rows; 68 selected strict rows; May 137 positive / 0 negative / 23 flat. | Promising model/source-selection clue. May behavior is clean but sparse, with median May trade count one. |
| 5 | WPR106-180 | ETH volatility-expansion fixed-hold diagnostic | Best May row: +1.079938 pre-May over 354 trades, +0.077562 May over 14 trades. | Worth preserving as a volatility-term behavior clue only; packet-level May result was weak. |
| 6 | WPR106-209 | BTC-led ETH relative-flow absorption reversion | Top row +0.672164 pre-May over 394 trades, +0.062942 May over 24 trades; full cost-stress survival. | Plausible order-flow transfer mechanism, but selected packet result was mixed. |
| 7 | WPR106-186 | BTC state-transition short profile | Strongest row +0.255860 pre-May and +0.055395 May; BTC subset had 12 positive / 3 negative May rows. | BTC-only clue is useful; mixed BTC/ETH family failed due ETH losses. |
| 8 | WPR106-139 / WPR106-157 | ETH calendar flow impulse | Top raw pre-May row +2.796355; broad selector top row +2.480657 with 678 trades, 28 active months, 4 losing months. | Highest raw pre-May performance, but less promising because May transfer rejected the pocket. Use as a control or split-by-regime diagnostic. |
| 9 | WPR106-225 / WPR106-220 | Cross-family loss-cluster complement and WPR199 source-control | WPR106-225 median +0.612399 pre-May with 80 strict rows; WPR106-220 median +0.637255 pre-May. | Not promising as a selector: WPR106-225 was 2 positive / 178 negative in May and every selected complement included WPR106-220. |

## Correlation Evidence

The strongest useful positive selected-row pre-May versus May correlations
found in comparison Parquets were:

| Packet | Rows | May result | Correlation |
| --- | ---: | --- | ---: |
| WPR106-222 | 160 | 137 positive / 0 negative / 23 flat, May median +0.001407 | +0.337 |
| WPR106-221 | 140 | 113 positive / 27 negative, May median +0.011323 | +0.305 |
| WPR106-214 | 120 | 94 positive / 26 negative, May median +0.026679 | +0.234 |

Important negative transfer diagnostics:

| Packet | Rows | May result | Correlation |
| --- | ---: | --- | ---: |
| WPR106-219 | 14 | 6 positive / 6 negative / 2 flat, May median 0.000000 | -0.712 |
| WPR106-218 | 160 | 33 positive / 127 negative, May median -0.001138 | -0.592 |
| WPR106-225 | 180 | 2 positive / 178 negative, May median -0.005795 | -0.582 |
| WPR106-216 | 160 | 5 positive / 155 negative, May median -0.014582 | -0.556 |
| WPR106-215 | 160 | 25 positive / 135 negative, May median -0.014480 | -0.439 |
| WPR106-220 | 120 | 29 positive / 86 negative / 5 flat, May median -0.005859 | -0.408 |

Interpretation: the best broad-selected follow-up families are WPR106-214,
WPR106-221, and WPR106-222. WPR106-146 is the strongest narrow direct lead even
though it is not represented as a broad packet-level comparison correlation in
the same way. WPR106-220/WPR106-225 are useful falsification sources, not
selector anchors.

## Falsified Or Weak Paths

- WPR106-139 calendar/session rows dominate raw pre-May returns but fail May in
  broad selected exposure tests.
- WPR106-157 broad artifact selector included 43 local packet directories and
  still had a negative selected May median and mean.
- WPR106-225 cross-family complement looked excellent pre-May but failed May
  badly, with every selected complement including WPR106-220.
- WPR106-180, WPR106-186, and WPR106-209 contain good single-row diagnostics
  but do not yet support family-level confidence.

## Next Research Direction

1. Start with WPR106-146 as the most direct narrow lead. Run behavior-deduped,
   source-level causal stability around the ETH relative-strength KNN overlay,
   with raw-source controls and additional pre-May pseudo-holdouts.
2. In parallel, use WPR106-214 and WPR106-221 as the broad transparent-motif
   replacement/fallback track. Keep selection May-blind and cap duplicated
   source behavior.
3. Treat WPR106-222 as a KNN source-generation problem: the sign of May
   transfer is clean, but trade density is too sparse.
4. Preserve WPR106-180, WPR106-186, and WPR106-209 as mechanism clues for
   narrow packets only.
5. Use WPR106-139, WPR106-220, and WPR106-225 as controls and overfit
   warnings.

## Validation

Extraction and workbook creation:

```powershell
python outputs/019ed9da-c03f-7a01-ba1a-8a28806bc270/extract_research_audit.py
& 'C:\Users\papaa\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' outputs/019ed9da-c03f-7a01-ba1a-8a28806bc270/build_research_audit_workbook.mjs
```

Validation evidence:

- Extractor completed with 142 summary JSON files, 213 Parquet files read, and
  218 correlation diagnostics.
- Workbook exported successfully to the output path above.
- Workbook preview PNGs were rendered for the primary sheets.
- Formula/error scan returned: `Cell search matched 0 entries.`

## Final Boundary

All conclusions are research-only and observe-only. The audit does not create
a candidate pack, paper/live artifact, order path, sizing change, runtime-mode
change, live configuration write, CUDA speedup claim, or promotion claim.
