# Agent name

Meta-Model Agent

# Task received

Objective: explain zero accepted meta trades and define the next meta experiments.

Tasks:

- Review `20260428_meta_model_agent_architecture_gap_review.md`.
- Identify whether zero trades are caused by thresholding, upstream KNN sparsity, fallback backend, class imbalance, or feature distribution.
- Define next experiments:
  - lower meta threshold diagnostic run
  - XGBoost research-extra run
  - pure KNN-only baseline comparison
  - meta trained only after KNN trade candidate expansion
- Write artifact: `docs/tradingbotsuite_runtime/agent_artifacts/20260428_meta_model_agent_next_experiment_spec.md`.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_meta_model_agent_architecture_gap_review.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_meta_model_agent_real_btc_meta_review.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_real_btc_contract_run.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_real_btc_acceptance_triage.md`
- `configs/v2_btc_hmm_multi_knn_research.json`
- `src/tradingbotsuite/research/hmm_knn.py`
- `data/research/v2-btc-hmm-multi-knn-1/meta_predictions.parquet`
- `data/research/v2-btc-hmm-multi-knn-1/walk_forward_metrics.json`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_meta_model_agent_next_experiment_spec.md`

# Commands/tests run

The command from the task appeared truncated at `c`. I ran the literal command first and then the corrected repo-root search.

```powershell
rg -n "meta_model|meta_threshold|accepted_by_meta|meta_probability|random_forest_fallback|XGBClassifier|comparison" c
```

Result: failed because `c` is not a repo path:

```text
rg: c: IO error for operation on c: The system cannot find the file specified. (os error 2)
```

Corrected search:

```powershell
rg -n "meta_model|meta_threshold|accepted_by_meta|meta_probability|random_forest_fallback|XGBClassifier|comparison" src tests docs configs
```

Relevant hits:

- `configs/v2_btc_hmm_multi_knn_research.json:94` defines `meta_model`.
- `src/tradingbotsuite/research/hmm_knn.py:25` imports `XGBClassifier` when available.
- `src/tradingbotsuite/research/hmm_knn.py:667` starts `_fit_meta_model`.
- `src/tradingbotsuite/research/hmm_knn.py:670` selects XGBoost only when `XGBClassifier` is importable.
- `src/tradingbotsuite/research/hmm_knn.py:686` records `random_forest_fallback`.
- `src/tradingbotsuite/research/hmm_knn.py:892` writes `meta_probability`.
- `src/tradingbotsuite/research/hmm_knn.py:894` writes `accepted_by_meta`.
- `src/tradingbotsuite/research/hmm_knn.py:1229` writes the pure-KNN versus meta `comparison`.

Artifact inspection command:

```powershell
$env:PYTHONPATH='src'; python <pandas/json inspection script for meta_predictions.parquet and walk_forward_metrics.json>
```

Key observed values:

```json
{
  "configured_meta_probability_threshold": 0.55,
  "meta_probability_min": 0.36855263232911384,
  "meta_probability_p50": 0.5027877583532323,
  "meta_probability_p95": 0.5523742626267958,
  "meta_probability_max": 0.6344858552846621,
  "accepted_by_knn_count": 5,
  "accepted_by_meta_count": 0,
  "meta_backend": "random_forest_fallback",
  "xgboost_available": false
}
```

KNN candidate meta probabilities:

```text
0.49135565369348455
0.423763204910028
0.505576259773435
0.499486759989372
0.47859321065449023
```

All five KNN candidates had `regime_no_trade: true` and `label_accept: 0`.

No pytest command was run. This task is a read-only diagnosis and experiment specification.

# Decisions made

## Cause of zero accepted meta trades

Zero accepted meta trades are caused by the intersection of three gates, not by a single meta-model failure.

Current code defines `accepted_by_meta` as:

```text
meta_probability >= 0.55
AND accepted_by_knn
AND NOT regime_no_trade
```

Observed causes:

| Candidate cause | Diagnosis | Evidence |
| --- | --- | --- |
| Thresholding | Contributing cause, but not sufficient alone. | The configured meta threshold is `0.55`. None of the five KNN candidates reached it; their max meta probability was `0.505576259773435`. |
| Upstream KNN sparsity | Primary structural cause. | Pure KNN accepted only `5` of `446` rows. Those five were all negative realized outcomes. The acceptance triage already fails KNN for insufficient trade count and negative post-cost expectancy. |
| Regime no-trade veto | Primary mechanical cause. | All five KNN candidates had `regime_no_trade: true`, so even a very low meta threshold still produces zero final meta trades unless the diagnostic explicitly bypasses the regime veto. |
| Fallback backend | Possible calibration contributor, not proven root cause. | The run used `random_forest_fallback` because `xgboost_available` was `false`. The fallback produced a compressed probability band around 0.50, but the KNN/regime gates would still block trades. |
| Class imbalance | Not the cause. | Output labels were two-class, and training summaries had two classes in all splits. Training positives were about 30-32% of rows, not one-class or too thin by current validation. |
| Feature distribution | Likely weak separation, not a standalone blocker. | Meta probabilities barely separate labels: negative-label mean was about `0.49795`, positive-label mean about `0.49738`. KNN candidates had lower average meta probability than non-candidates, which is consistent with the meta-filter rejecting poor KNN candidates. |

Conclusion: the zero-trade meta result is mostly an upstream candidate-generation and regime-veto problem. Thresholding explains why KNN candidates did not pass the probability gate, but lowering only `meta_model.probability_threshold` will not create final accepted trades while all KNN candidates remain `regime_no_trade: true`.

# Next experiments

## 1. Lower Meta Threshold Diagnostic Run

Purpose: determine whether meta probability calibration is too conservative, while keeping the result research-only and non-promotional.

Design:

- Run a diagnostic threshold ladder at `0.55`, `0.525`, `0.50`, `0.49`, `0.475`, `0.45`, and `0.40`.
- Report three separate counters for each threshold:
  - `meta_prob_only_count`
  - `meta_prob_and_knn_count`
  - `meta_prob_and_knn_and_regime_allowed_count`
- Include realized post-cost expectancy for each counter where trades exist.
- Keep the official `accepted_by_meta` formula unchanged unless the experiment writes to a separate diagnostic artifact.

Current-data expectation:

- With the full current formula, every tested lower threshold still yields zero trades because all KNN candidates are `regime_no_trade: true`.
- If the regime veto is ignored for diagnosis only:
  - threshold `0.50` would include one KNN candidate
  - threshold around `0.49` would include three KNN candidates
  - threshold below `0.424` would include all five KNN candidates
- All five existing KNN candidates are `label_accept: 0`, so lowering the threshold on the current artifact would add losing candidates, not reveal edge.

Suggested command shape:

```powershell
$env:PYTHONPATH='src'
python -m tradingbotsuite.main research-hmm-knn `
  --config configs/v2_btc_hmm_multi_knn_research_meta_threshold_diag.json `
  --dataset data/research/v2-btc-research-1/btcusdt_dataset.parquet `
  --output-dir data/research/meta_threshold_diag
```

Required output fields for the diagnostic artifact:

- threshold ladder counts
- KNN-intersection counts
- regime-vetoed counts
- realized net return after fees, slippage, and funding
- `research_only: true`
- `promotion_ready: false`

## 2. XGBoost Research-Extra Run

Purpose: test whether the intended backend materially improves probability separation or KNN-candidate ranking.

Design:

- Install/use the research environment where `xgboost` is importable.
- Run the same dataset and config without changing KNN or regime settings.
- Confirm:
  - `artifact_manifest.json.dependencies.xgboost_available: true`
  - `artifact_manifest.json.dependencies.meta_backend: ["xgboost"]`
  - `meta_predictions.parquet.meta_model_backend` is `xgboost`
- Compare XGBoost against the fallback on:
  - probability distribution by `label_accept`
  - probability distribution on KNN candidates only
  - threshold ladder counts
  - realized comparison metrics

Suggested command shape:

```powershell
$env:PYTHONPATH='src'
python -c "import xgboost; print(xgboost.__version__)"
python -m tradingbotsuite.main research-hmm-knn `
  --config configs/v2_btc_hmm_multi_knn_research.json `
  --dataset data/research/v2-btc-research-1/btcusdt_dataset.parquet `
  --output-dir data/research/xgboost_meta_check
```

Decision rule:

- If XGBoost improves label separation but still yields zero final meta trades, the blocker remains upstream KNN/regime gating.
- If XGBoost improves KNN-candidate ranking and candidate probabilities exceed threshold, then backend/calibration becomes a meaningful next tuning surface.
- If XGBoost looks like fallback, stop tuning the meta backend until upstream KNN candidate quality improves.

## 3. Pure KNN-Only Baseline Comparison

Purpose: avoid attributing KNN weakness to the meta-filter.

Design:

- Treat pure KNN as its own baseline before any meta filtering.
- Use the existing `comparison.hmm_regime_lorentzian_knn` as the starting baseline.
- Add a KNN-only candidate expansion matrix before meta work:
  - `vote_probability_threshold`: `0.55`, `0.52`, `0.50`
  - `expected_value_threshold`: `0.0`, `-0.05`, `-0.10`
  - `k`: primary `32`, plus best observed K sweep candidates from KNN Agent follow-up
  - keep `same_regime_only: true` for the first pass
  - report regime-vetoed and regime-allowed rows separately

Current baseline:

- Pure KNN accepted `5` trades.
- Pure KNN realized post-cost expectancy was `-1.0008811453163364`.
- Pure KNN had `3` long and `2` short trades, but trade count was far below the required `25`.
- All five accepted KNN candidates were bad labels and regime-vetoed.

Decision rule:

- Do not train or tune meta as a performance filter until a KNN-only baseline can produce enough non-vetoed candidates to evaluate.
- Minimum candidate target for the next meta pass: at least `25` realized candidate trades overall and enough split coverage that one split cannot dominate.

## 4. Meta Trained Only After KNN Trade Candidate Expansion

Purpose: train the meta-filter on the population it is meant to filter, not mostly on rows that are never plausible KNN candidates.

Design:

- First expand KNN candidate generation in a separate research config.
- Define an `expanded_knn_candidate` mask using relaxed KNN thresholds, before meta fitting.
- Train the meta-model only on prior/train rows that are `expanded_knn_candidate`, while preserving leakage rules:
  - meta KNN features remain prior-only/out-of-fold
  - no same-row/self-neighbor contamination
  - purge/embargo still applies
  - scalers and model fits remain train-only
- Score only expanded KNN candidates in test folds.
- Compare:
  - expanded pure KNN baseline
  - expanded KNN plus fallback meta
  - expanded KNN plus XGBoost meta
- Keep regime-veto reporting decomposed:
  - candidate before regime veto
  - candidate after regime veto
  - meta accepted before regime veto
  - final meta accepted after regime veto

Why this comes after candidate expansion:

- The current meta model was trained on enough two-class labels, but the final decision surface has almost no KNN candidate support.
- Training meta on all rows can produce a globally valid probability, but it does not solve the operational question of ranking scarce KNN candidates.
- Candidate-conditioned training makes the meta target match the decision point.

Decision rule:

- Continue only if expanded KNN produces sufficient candidate support and the meta-filter improves realized post-cost expectancy without collapsing trade count or one-sided long/short coverage.
- Any result remains research-only with `promotion_ready: false` until full acceptance gates are met on a current point-in-time dataset.

# Assumptions

- The current real BTC artifact under `data/research/v2-btc-hmm-multi-knn-1` is the right baseline for this experiment spec.
- Lower-threshold and regime-bypass calculations are diagnostics only. They do not imply live gates, sizing, Hyperliquid execution, operator controls, or promotion.
- The user wants experiment definitions, not code changes or new runs, in this task.

# Open issues or blockers

None.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` reported no open issues. No new issue was appended.

# Handoff notes for other agents

- KNN Agent should own candidate expansion first; the current meta-filter has too few valid KNN candidates to evaluate.
- Regime Agent should review why every KNN candidate is `regime_no_trade: true` before any meta threshold result is interpreted.
- Backtest Agent should require all next experiment outputs to report decomposed counts: KNN candidate, regime-vetoed candidate, meta-probability pass, and final accepted-by-meta.
- Meta Agent should run XGBoost only as a backend comparison after preserving the same dataset, splits, KNN settings, and no-leakage feature construction.
