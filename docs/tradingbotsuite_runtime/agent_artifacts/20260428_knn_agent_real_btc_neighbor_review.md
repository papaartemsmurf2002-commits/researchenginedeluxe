# Agent name

KNN Agent

# Task received

Objective: evaluate real-data KNN diagnostics.

Requested tasks:

- Inspect `knn_predictions.parquet` and `neighbor_diagnostics.csv`.
- Report neighbor counts, distance quality, same-regime compliance, K sweep coverage, and skip reasons.
- Identify if KNN is mostly skipping or using poor-quality neighbors.
- Write this artifact.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_knn_agent_diagnostics_contract_hardening.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_knn_agent_cli_artifact_diagnostics_readiness.md`
- `configs/v2_btc_hmm_multi_knn_research.json`
- `data/research/v2-btc-research-1/dataset_manifest.json`
- `data/research/v2-btc-hmm-multi-knn-1/artifact_manifest.json`
- `data/research/v2-btc-hmm-multi-knn-1/walk_forward_metrics.json`
- `data/research/v2-btc-hmm-multi-knn-1/knn_predictions.parquet`
- `data/research/v2-btc-hmm-multi-knn-1/neighbor_diagnostics.csv`
- `src/tradingbotsuite/research/hmm_knn.py`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_knn_agent_real_btc_neighbor_review.md`

# Commands/tests run

Prompt and issue protocol check:

```powershell
Get-Content -Path docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_PROMPTS.md -TotalCount 220
Get-Content -Path docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_ISSUES.md -TotalCount 120
```

Result:

```text
HMM_MULTI_KNN_AGENT_ISSUES.md reported no open issues.
```

Artifact discovery:

```powershell
Get-ChildItem -Path data\research\v2-btc-hmm-multi-knn-1 -Recurse -Force | Select-Object FullName,Length,LastWriteTime | Format-Table -AutoSize
Get-Content -Path data\research\v2-btc-research-1\dataset_manifest.json
```

Result:

```text
Found real BTC artifact set in data\research\v2-btc-hmm-multi-knn-1.
The artifact set includes knn_predictions.parquet, neighbor_diagnostics.csv, walk_forward_metrics.json, artifact_manifest.json, regime_posteriors.parquet, meta_predictions.parquet, and monitoring_report.json.
The source dataset manifest reports BTCUSDT, 1,173 rows, and dataset path data\research\v2-btc-research-1\btcusdt_dataset.parquet.
```

Schema and metric inspection:

```powershell
$env:PYTHONPATH='src'; python <inspection script reading knn_predictions.parquet, neighbor_diagnostics.csv, walk_forward_metrics.json, artifact_manifest.json>
```

Key result:

```text
knn_predictions rows: 446
neighbor_diagnostics rows: 44,600
populated diagnostic rows: 44,600
diagnostic skip rows: 0
prediction skip reasons: {"none": 446}
diagnostic skip reasons: {"none": 44600}
accepted_by_knn: {"False": 441, "True": 5}
accepted_rate: 0.011210762331838564
```

No test command was run for this read-only artifact review; the task was artifact inspection, not a code change.

# Decisions made

- Treated `data/research/v2-btc-hmm-multi-knn-1` as the real BTC artifact set because it contains the requested KNN outputs and its manifest is `research_only: true`, `symbol: BTCUSDT`, with row count 446.
- Did not regenerate artifacts because the requested real-data files already existed and were readable.
- Interpreted "skipping" as a non-null KNN skip reason or missing neighbor diagnostics. Under that definition, the real run is not mostly skipping.
- Interpreted "poor-quality neighbors" through the emitted `neighbor_distance_quality` score, where higher is better because source code computes it as `1 / (1 + weighted_average_distance)`. The current contract does not define a formal pass/fail threshold, so the quality judgment below is an audit assessment, not a promotion rule.

# Real-data KNN diagnostics

Primary `knn_predictions.parquet`:

```text
rows: 446
neighbor_count min/median/mean/max: 32 / 32 / 32 / 32
neighbor_count value counts: {32: 446}
accepted_by_knn true: 5
accepted_by_knn false: 441
accepted rate: 1.12%
skip reasons: none for all 446 rows
walk-forward split rows: split 0 = 156, split 1 = 156, split 2 = 134
```

The primary output is not missing neighbors. Every primary row used the configured primary K of 32 with `primary_weighting: inverse_distance`.

Primary distance quality:

```text
count: 446
min: 0.077318
p05: 0.109722
p10: 0.117532
p25: 0.138364
median: 0.157596
mean: 0.155536
p75: 0.175122
p90: 0.186557
p95: 0.195176
p99: 0.210675
max: 0.219907
```

Primary distance-quality threshold counts:

```text
quality < 0.10: 11 / 446
quality < 0.15: 171 / 446
quality < 0.20: 432 / 446
quality < 0.30: 446 / 446
quality >= 0.50: 0 / 446
```

This indicates weak neighbor proximity in the real BTC run. KNN is mostly not skipping; it is mostly using low-quality same-regime neighbors and then rejecting almost every row at the KNN acceptance stage.

# Same-regime compliance

Diagnostics:

```text
same_regime_only values: {"True": 44600}
fallback_used values: {"False": 44600}
populated neighbor rows: 44,600
cross-regime diagnostic rows: 0
future neighbor source references: 0
source_row_index min/max: 711 / 1172
neighbor_source_index min/max: 0 / 1030
```

Populated query and neighbor regime counts matched exactly:

```text
regime 0: query rows 8,900, neighbor rows 8,900
regime 1: query rows 10,600, neighbor rows 10,600
regime 2: query rows 14,000, neighbor rows 14,000
regime 3: query rows 11,100, neighbor rows 11,100
```

The real artifact satisfies the same-regime guarantee. No fallback was used and no populated diagnostic row crossed regimes.

# K sweep coverage

Manifest and metrics report:

```text
distance: lorentzian
same_regime_only: true
allow_cross_regime_fallback: false
configured_k_values: [16, 24, 32, 48, 64]
configured_weighting: ["inverse_distance", "softmax"]
primary_k: 32
primary_weighting: inverse_distance
knn_sweep result count: 10
```

Diagnostics contain all configured K and weighting combinations:

```text
16|inverse_distance: 4,460 rows
16|softmax: 4,460 rows
24|inverse_distance: 4,460 rows
24|softmax: 4,460 rows
32|inverse_distance: 4,460 rows
32|softmax: 4,460 rows
48|inverse_distance: 4,460 rows
48|softmax: 4,460 rows
64|inverse_distance: 4,460 rows
64|softmax: 4,460 rows
```

The diagnostics emit the top 10 neighbor ranks per signal and K/weighting combination. This is enough to audit same-regime compliance, distance quality, weighting mode, source references, and K sweep coverage, but it is not a full dump of all selected neighbors for K values above 10.

K sweep metrics from `walk_forward_metrics.json`:

```text
k=16 inverse_distance: accepted_rate 3.81%, trade_count 17, expectancy_after_cost -0.5596, fallback_rate 0.0, skip none
k=16 softmax: accepted_rate 9.19%, trade_count 41, expectancy_after_cost -0.0862, fallback_rate 0.0, skip none
k=24 inverse_distance: accepted_rate 1.57%, trade_count 7, expectancy_after_cost -1.0009, fallback_rate 0.0, skip none
k=24 softmax: accepted_rate 5.38%, trade_count 24, expectancy_after_cost -0.0634, fallback_rate 0.0, skip none
k=32 inverse_distance primary: accepted_rate 1.12%, trade_count 5, expectancy_after_cost -1.0009, fallback_rate 0.0, skip none
k=32 softmax: accepted_rate 4.04%, trade_count 18, expectancy_after_cost -0.1675, fallback_rate 0.0, skip none
k=48 inverse_distance: accepted_rate 0.00%, trade_count 0, expectancy_after_cost 0.0000, fallback_rate 0.0, skip none
k=48 softmax: accepted_rate 2.69%, trade_count 12, expectancy_after_cost -0.7924, fallback_rate 0.0, skip none
k=64 inverse_distance: accepted_rate 0.00%, trade_count 0, expectancy_after_cost 0.0000, fallback_rate 0.0, skip none
k=64 softmax: accepted_rate 2.24%, trade_count 10, expectancy_after_cost -0.7508, fallback_rate 0.0, skip none
```

All sweep combinations are evaluated. None show positive expectancy after cost in this artifact.

# Distance quality by sweep combination

Diagnostic `neighbor_distance_quality` distribution by K/weighting:

```text
k=16 inverse_distance: mean 0.1680, median 0.1701, max 0.2417
k=16 softmax: mean 0.1774, median 0.1785, max 0.2464
k=24 inverse_distance: mean 0.1607, median 0.1628, max 0.2300
k=24 softmax: mean 0.1720, median 0.1731, max 0.2370
k=32 inverse_distance: mean 0.1555, median 0.1576, max 0.2199
k=32 softmax: mean 0.1684, median 0.1695, max 0.2295
k=48 inverse_distance: mean 0.1480, median 0.1498, max 0.2101
k=48 softmax: mean 0.1633, median 0.1643, max 0.2218
k=64 inverse_distance: mean 0.1427, median 0.1440, max 0.2022
k=64 softmax: mean 0.1600, median 0.1608, max 0.2149
```

Quality declines as K grows, which is expected because larger K includes farther neighbors. Softmax weighting produces slightly higher quality scores than inverse-distance in this run, but its sweep expectancy is still negative after costs.

# Assumptions

- The real BTC artifact set under `data/research/v2-btc-hmm-multi-knn-1` is the correct artifact to audit.
- `neighbor_distance_quality` is bounded in `[0, 1]`, with higher scores meaning closer weighted neighbor sets.
- "Mostly skipping" refers to KNN skip reasons and missing diagnostics, not to trade rejection by the final `accepted_by_knn` boolean.
- Top-10 neighbor diagnostics are sufficient for this requested audit because same-regime, source-row, K, weighting, distance, distance-quality, and label evidence are present.

# Open issues or blockers

None.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` reported no open issues before this task, and no new blocker was found.

# Handoff notes for other agents

- Real BTC KNN diagnostics are contract-complete and same-regime compliant.
- KNN is not mostly skipping: skip reasons are `none` for all 446 prediction rows and all 44,600 diagnostic rows.
- KNN is mostly no-trade/rejected: primary accepted rate is only 5 of 446 rows, or 1.12%.
- Neighbor quality is weak in this real artifact: every primary row has `neighbor_distance_quality < 0.30`, 432 of 446 are below 0.20, and none are at or above 0.50.
- K sweep coverage is complete in metrics and diagnostics for `[16, 24, 32, 48, 64] x ["inverse_distance", "softmax"]`; `(32, "inverse_distance")` remains the primary output path.
- Diagnostics currently emit only the first 10 neighbor ranks per K/weighting combination. If another agent needs to audit all selected neighbors for K values 16 through 64, the diagnostics contract should be extended to emit all selected ranks or add an explicit aggregate selected-neighbor-count field per K/weighting row.
