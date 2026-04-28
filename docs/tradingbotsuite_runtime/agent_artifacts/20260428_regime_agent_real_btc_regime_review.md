# Agent name

Regime Agent

# Task received

Objective: evaluate real-data regime behavior.

Tasks:

- Inspect `regime_posteriors.parquet`.
- Report regime distribution, entropy distribution, no-trade rate, flip rate, and whether all 4 regimes appear.
- Identify if shock/range regimes are absent or underrepresented.
- Write this artifact.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `configs/v2_btc_hmm_multi_knn_research.json`
- `data/research/v2-btc-research-1/btcusdt_dataset.parquet`
- Generated real-BTC artifact: `C:\Users\papaa\AppData\Local\Temp\hmm_knn_real_btc_regime_a83076aff7fb49dcbfd4e12495920f86\v2-btc-hmm-multi-knn-1\regime_posteriors.parquet`
- Generated real-BTC manifest: `C:\Users\papaa\AppData\Local\Temp\hmm_knn_real_btc_regime_a83076aff7fb49dcbfd4e12495920f86\v2-btc-hmm-multi-knn-1\artifact_manifest.json`
- Generated real-BTC metrics: `C:\Users\papaa\AppData\Local\Temp\hmm_knn_real_btc_regime_a83076aff7fb49dcbfd4e12495920f86\v2-btc-hmm-multi-knn-1\walk_forward_metrics.json`
- Existing repo dataset manifest/artifact inventory under `data/research/`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_regime_agent_real_btc_regime_review.md`

# Commands/tests run

Protocol and artifact discovery:

```powershell
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_PROMPTS.md
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_ISSUES.md
Get-ChildItem -Recurse -Force -File -Filter regime_posteriors.parquet
Get-ChildItem -Recurse -Force -File -Filter artifact_manifest.json
Get-ChildItem -Recurse -Force data\research
Get-Content data\research\v2-btc-research-1-btcusdt-artifacts\artifact_manifest.json
```

Finding from discovery:

- No repo-local HMM/KNN `regime_posteriors.parquet` existed before this review.
- The repo did contain the real BTC research dataset at `data/research/v2-btc-research-1/btcusdt_dataset.parquet`.
- The repo-local `data/research/v2-btc-research-1-btcusdt-artifacts/artifact_manifest.json` is an older V2 model artifact, not an HMM/KNN regime artifact.

Generated a fresh real-BTC HMM/KNN artifact into a temp output directory:

```powershell
$root = Join-Path $env:TEMP ("hmm_knn_real_btc_regime_" + [System.Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $root | Out-Null
$env:PYTHONPATH='src'
python -m tradingbotsuite.main research-hmm-knn --config configs/v2_btc_hmm_multi_knn_research.json --dataset data/research/v2-btc-research-1/btcusdt_dataset.parquet --output-dir $root
```

CLI result:

```json
{
  "output_dir": "C:\\Users\\papaa\\AppData\\Local\\Temp\\hmm_knn_real_btc_regime_a83076aff7fb49dcbfd4e12495920f86\\v2-btc-hmm-multi-knn-1",
  "artifact_manifest_path": "C:\\Users\\papaa\\AppData\\Local\\Temp\\hmm_knn_real_btc_regime_a83076aff7fb49dcbfd4e12495920f86\\v2-btc-hmm-multi-knn-1\\artifact_manifest.json",
  "metrics_path": "C:\\Users\\papaa\\AppData\\Local\\Temp\\hmm_knn_real_btc_regime_a83076aff7fb49dcbfd4e12495920f86\\v2-btc-hmm-multi-knn-1\\walk_forward_metrics.json",
  "regime_posteriors_path": "C:\\Users\\papaa\\AppData\\Local\\Temp\\hmm_knn_real_btc_regime_a83076aff7fb49dcbfd4e12495920f86\\v2-btc-hmm-multi-knn-1\\regime_posteriors.parquet",
  "knn_predictions_path": "C:\\Users\\papaa\\AppData\\Local\\Temp\\hmm_knn_real_btc_regime_a83076aff7fb49dcbfd4e12495920f86\\v2-btc-hmm-multi-knn-1\\knn_predictions.parquet",
  "meta_predictions_path": "C:\\Users\\papaa\\AppData\\Local\\Temp\\hmm_knn_real_btc_regime_a83076aff7fb49dcbfd4e12495920f86\\v2-btc-hmm-multi-knn-1\\meta_predictions.parquet",
  "neighbor_diagnostics_path": "C:\\Users\\papaa\\AppData\\Local\\Temp\\hmm_knn_real_btc_regime_a83076aff7fb49dcbfd4e12495920f86\\v2-btc-hmm-multi-knn-1\\neighbor_diagnostics.csv"
}
```

Inspected `regime_posteriors.parquet`, `artifact_manifest.json`, and `walk_forward_metrics.json` with pandas/json.

# Decisions made

- Used the real BTC dataset from `data/research/v2-btc-research-1/btcusdt_dataset.parquet` because no existing HMM/KNN `regime_posteriors.parquet` was present in the repo.
- Wrote generated HMM/KNN outputs to a temp directory to avoid adding generated research artifacts under repo `data/research/`.
- Treated the resulting artifact as a real-data regime behavior review, not a promotion assessment.
- Did not change code, config, live execution, sizing, gates, Hyperliquid behavior, safety behavior, or operator live controls.

# Real BTC artifact identity

- Output directory: `C:\Users\papaa\AppData\Local\Temp\hmm_knn_real_btc_regime_a83076aff7fb49dcbfd4e12495920f86\v2-btc-hmm-multi-knn-1`
- Dataset path in manifest: `data\research\v2-btc-research-1\btcusdt_dataset.parquet`
- Manifest `research_only`: `true`
- Manifest `symbol`: `BTCUSDT`
- Manifest `asset_scope`: `["BTCUSDT"]`
- Manifest `plan_version`: `v2-btc-hmm-multi-knn-1`
- Manifest `row_count`: `446`
- HMM backend: `["gaussian_mixture_fallback"]`
- `hmmlearn_available`: `false`

# Regime artifact validity

`regime_posteriors.parquet` shape:

- `446` rows
- `18` columns

Posterior columns:

- `regime_p_0`
- `regime_p_1`
- `regime_p_2`
- `regime_p_3`

Contract checks:

- No required regime fields were missing.
- Posterior row sums are valid: min `0.9999999999999998`, max `1.0000000000000002`.
- Posterior row sums are all close to `1.0`.
- Train-fit boundary is valid for all rows: `hmm_fit_end_row < source_row_index`.
- `regime_model_backend` values: `["gaussian_mixture_fallback"]`.
- Walk-forward splits present: `0`, `1`, `2`.

# Regime distribution

By top regime label:

| Regime label | Rows | Percent |
| --- | ---: | ---: |
| `bear_trend` | 170 | 38.1166% |
| `range_chop` | 130 | 29.1480% |
| `shock_transition` | 77 | 17.2646% |
| `bull_trend` | 69 | 15.4709% |

By numeric top regime:

| Top regime | Rows | Percent |
| --- | ---: | ---: |
| `0` | 89 | 19.9552% |
| `1` | 106 | 23.7668% |
| `2` | 140 | 31.3901% |
| `3` | 111 | 24.8879% |

All four semantic regime labels appear:

- `range_chop`
- `bull_trend`
- `bear_trend`
- `shock_transition`

# Entropy distribution

`posterior_entropy` summary:

| Statistic | Value |
| --- | ---: |
| min | `0.0000000028481961611462465` |
| p05 | `0.007651921193898591` |
| p25 | `0.07482732142290924` |
| median | `0.1822276593873849` |
| mean | `0.23115281296041446` |
| p75 | `0.3768192591114443` |
| p95 | `0.5350898796165469` |
| max | `0.7830931786805785` |

`max_regime_probability` summary:

| Statistic | Value |
| --- | ---: |
| min | `0.4085024901092016` |
| p05 | `0.5575320439530776` |
| median | `0.9335742964827483` |
| mean | `0.8713859425147195` |
| p95 | `0.9985961303535349` |
| max | `0.9999999998343305` |

# No-trade and flip behavior

Overall:

- `regime_no_trade` count: `406`
- `regime_no_trade` rate: `91.0314%`
- `recent_regime_flip` count: `399`
- `recent_regime_flip` rate: `89.4619%`
- Tradeable rows: `40`
- Tradeable rate: `8.9686%`

No-trade reason breakdown:

| Reason | Count | Rate |
| --- | ---: | ---: |
| `max_regime_probability < 0.60` | 36 | 8.0717% |
| `posterior_entropy > 0.78` | 1 | 0.2242% |
| `recent_regime_flip` | 399 | 89.4619% |
| no-trade due only to recent flip | 370 | n/a |
| no-trade due low probability without flip | 7 | n/a |
| no-trade due high entropy without flip | 0 | n/a |

By split:

| Split | Rows | No-trade rate | Recent flip rate | Entropy mean | Entropy p95 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `0` | 156 | 94.2308% | 91.0256% | 0.20181823938075935 | 0.4918996504112814 |
| `1` | 156 | 87.1795% | 85.8974% | 0.21719003740230944 | 0.5708019930055461 |
| `2` | 134 | 91.7910% | 91.7910% | 0.28155868210586643 | 0.5641420900020263 |

By regime label:

| Regime label | Rows | Percent | No-trade rate | Recent flip rate | Low-prob rate | High-entropy rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `bear_trend` | 170 | 38.1166% | 90.0000% | 86.4706% | 12.3529% | 0.5882% |
| `bull_trend` | 69 | 15.4709% | 94.2029% | 94.2029% | 7.2464% | 0.0000% |
| `range_chop` | 130 | 29.1480% | 88.4615% | 88.4615% | 3.0769% | 0.0000% |
| `shock_transition` | 77 | 17.2646% | 94.8052% | 93.5065% | 7.7922% | 0.0000% |

# Shock/range representation

Shock and range regimes are not absent.

- `range_chop`: `130` rows, `29.1480%`.
- `shock_transition`: `77` rows, `17.2646%`.

Using a simple underrepresentation threshold of less than `5%`, neither shock nor range is underrepresented. Both are materially represented in the real BTC artifact.

# Assessment

All four regimes appear in the real BTC artifact. The distribution is not collapsed into only trend states, and both `range_chop` and `shock_transition` are present at meaningful shares.

The main issue is regime stability: `recent_regime_flip` is extremely high at `89.4619%`, which drives the overall `regime_no_trade` rate to `91.0314%`. Entropy itself is usually moderate or low: p95 is `0.5351`, and only one row crosses the configured entropy threshold of `0.78`.

Practical interpretation:

- The artifact demonstrates regime coverage across all four semantic labels.
- It does not demonstrate stable regime persistence.
- Most no-trade behavior comes from flip cooldown, not entropy or low posterior confidence.
- Before using these regime outputs to judge KNN/meta performance, the Regime layer likely needs review of transition smoothness, state persistence, and/or flip cooldown sensitivity.

# Assumptions

- "Real-data" refers to the repo-local BTC research dataset at `data/research/v2-btc-research-1/btcusdt_dataset.parquet`.
- A fresh temp HMM/KNN run from that dataset is acceptable because no existing repo-local HMM/KNN `regime_posteriors.parquet` was present.
- The active environment does not have `hmmlearn`, so this review reflects the deterministic Gaussian mixture fallback backend rather than the optional HMM backend.

# Open issues or blockers

None.

No issue was appended to `HMM_MULTI_KNN_AGENT_ISSUES.md` because all four regimes appear and the review is complete. The high flip/no-trade rate is a model-quality concern documented here for follow-up, not a blocker to artifact inspection.

# Handoff notes for other agents

- Do not treat the real BTC Regime layer as stable based on this artifact. It covers all four regimes, but it flips too often.
- KNN and Meta agents should account for the fact that only about `8.97%` of rows are regime-tradeable after current no-trade logic.
- If a follow-up task is assigned, focus on regime persistence diagnostics and whether the fallback Gaussian mixture backend is too jumpy compared with an installed `hmmlearn` backend.
