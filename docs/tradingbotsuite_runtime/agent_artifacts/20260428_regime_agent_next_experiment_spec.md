# Agent name

Regime Agent

# Task received

Objective: diagnose high regime flip/no-trade behavior.

Tasks:

- Review `20260428_regime_agent_architecture_gap_review.md`.
- Propose concrete research experiments for high flip rate and high no-trade rate:
  - flip-cooldown sensitivity
  - entropy threshold sensitivity
  - posterior threshold sensitivity
  - HMM feature subset ablation
  - longer training history
- For each experiment, define config fields to change and expected diagnostic metric.
- Write this artifact.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_regime_agent_architecture_gap_review.md`
- `configs/v2_btc_hmm_multi_knn_research.json`
- `src/tradingbotsuite/research/hmm_knn.py`
- `tests/tradingbotsuite/test_hmm_knn.py`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_regime_agent_next_experiment_spec.md`

# Commands/tests run

Requested command:

```powershell
rg -n "posterior_threshold|entropy_threshold|flip_cooldown|emission_features|regime_no_trade|recent_regime_flip" config
```

Result:

```text
rg: config: IO error for operation on config: Не удается найти указанный файл. (os error 2)
```

Follow-up using the actual repo config directory:

```powershell
rg -n "posterior_threshold|entropy_threshold|flip_cooldown|emission_features|regime_no_trade|recent_regime_flip" configs
```

Result:

```text
configs\v2_btc_hmm_multi_knn_research.json:14:    "posterior_threshold": 0.6,
configs\v2_btc_hmm_multi_knn_research.json:15:    "entropy_threshold": 0.78,
configs\v2_btc_hmm_multi_knn_research.json:16:    "flip_cooldown_bars": 3,
configs\v2_btc_hmm_multi_knn_research.json:21:    "emission_features": [
```

Additional implementation/config lookup:

```powershell
rg -n "min_training_rows|train_fraction|walk_forward_splits|_walk_forward_frames|flip_cooldown_bars|posterior_threshold|entropy_threshold|emission_features" src\tradingbotsuite\research\hmm_knn.py tests\tradingbotsuite\test_hmm_knn.py configs\v2_btc_hmm_multi_knn_research.json
```

# Baseline problem from architecture review

`20260428_regime_agent_architecture_gap_review.md` reports:

| Measure | Value |
| --- | ---: |
| Regime rows | `446` |
| Bear trend labels | `170` |
| Range/chop labels | `130` |
| Shock/transition labels | `77` |
| Bull trend labels | `69` |
| Mean posterior entropy | `0.23115281296041446` |
| P95 posterior entropy | `0.5350898796165469` |
| Mean max regime probability | `0.8713859425147195` |
| Regime no-trade rate | `0.9103139013452914` |
| Recent flip rate | `0.8946188340807175` |

Interpretation:

- All four intended labels appear.
- The taxonomy did not collapse.
- The main failure mode is instability: recent-flip rate is very high and drives no-trade behavior.
- Entropy is not the main observed driver because p95 entropy is below the configured `hmm.entropy_threshold` of `0.78`.

# Common evaluation protocol

Every experiment should:

- Use the same real BTC dataset: `data/research/v2-btc-research-1/btcusdt_dataset.parquet`.
- Write outputs to a temp directory or an explicitly named research experiment directory, not to live runtime paths.
- Keep `acceptance.research_only: true`.
- Keep `asset_scope: ["BTCUSDT"]`.
- Keep live execution, sizing, live gates, Hyperliquid behavior, safety behavior, and operator live controls unchanged.
- Record the full config mutation and resulting artifact manifest path.
- Compare against the baseline run from `20260428_regime_agent_architecture_gap_review.md`.

Primary diagnostics for every run:

- `recent_regime_flip_rate = mean(recent_regime_flip)`
- `regime_no_trade_rate = mean(regime_no_trade)`
- `tradeable_rate = 1 - regime_no_trade_rate`
- `low_probability_rate = mean(max_regime_probability < hmm.posterior_threshold)`
- `high_entropy_rate = mean(posterior_entropy > hmm.entropy_threshold)`
- `posterior_entropy_mean`, `posterior_entropy_p95`
- `max_regime_probability_mean`, `max_regime_probability_p05`
- regime distribution by `top_regime_label`
- mean run length by `top_regime_label`
- median run length by `top_regime_label`
- number of label switches per 100 rows
- KNN/meta trade counts and promotion failures, treated as secondary effects

Recommended acceptance target for regime stability experiments:

- reduce `recent_regime_flip_rate` materially from `0.8946`
- reduce `regime_no_trade_rate` materially from `0.9103`
- preserve all four semantic regimes
- avoid collapsing `shock_transition` or `range_chop` below `5%`
- avoid a large increase in high-entropy rows

# Experiment 1: flip-cooldown sensitivity

Purpose:

Separate actual regime switching from the current no-trade penalty caused by the cooldown rule.

Config fields to change:

- `hmm.flip_cooldown_bars`

Grid:

| Variant | `hmm.flip_cooldown_bars` |
| --- | ---: |
| baseline | `3` |
| no cooldown | `0` |
| short cooldown | `1` |
| medium cooldown | `2` |
| conservative cooldown | `4` |
| very conservative cooldown | `6` |

Expected diagnostic metric:

- Primary: `regime_no_trade_rate`
- Secondary: `recent_regime_flip_rate`, `tradeable_rate`, accepted KNN/meta counts

Expected interpretation:

- `recent_regime_flip_rate` should not change if the underlying top-regime sequence is unchanged.
- If `regime_no_trade_rate` falls sharply as cooldown decreases, then the no-trade problem is mostly policy-induced rather than posterior uncertainty-induced.
- If accepted KNN/meta counts increase while posterior confidence remains similar, downstream agents can evaluate whether cooldown is too strict.

Decision rule:

- If `flip_cooldown_bars = 0` lowers no-trade from about `91%` to near the low-probability/entropy-only rate without increasing bad metrics elsewhere, add a follow-up to tune cooldown separately from regime detection.
- If cooldown variants still have high no-trade, focus on posterior threshold or model instability.

# Experiment 2: entropy threshold sensitivity

Purpose:

Test whether the entropy threshold meaningfully contributes to no-trade behavior and whether it can catch unstable rows better than flip cooldown.

Config fields to change:

- `hmm.entropy_threshold`

Grid:

| Variant | `hmm.entropy_threshold` |
| --- | ---: |
| strict | `0.45` |
| medium strict | `0.60` |
| baseline | `0.78` |
| loose | `0.90` |
| disabled proxy | `1.01` |

Expected diagnostic metric:

- Primary: `high_entropy_rate`
- Secondary: `regime_no_trade_rate`, `posterior_entropy_p95`, tradeable rows by regime label

Expected interpretation:

- Baseline p95 entropy was about `0.5351`, so lowering threshold to `0.45` or `0.60` should reveal whether entropy can be a useful uncertainty gate.
- Raising threshold to `0.90` or `1.01` should have almost no effect if entropy is already not the driver.

Decision rule:

- If strict entropy catches unstable/high-flip rows with fewer false blocks than cooldown, consider replacing some cooldown strictness with entropy gating.
- If entropy changes barely affect no-trade or downstream quality, deprioritize entropy threshold tuning.

# Experiment 3: posterior threshold sensitivity

Purpose:

Quantify how much no-trade is caused by low top-regime probability and whether the `0.60` threshold is too strict or too loose.

Config fields to change:

- `hmm.posterior_threshold`

Grid:

| Variant | `hmm.posterior_threshold` |
| --- | ---: |
| loose | `0.45` |
| moderate | `0.50` |
| baseline | `0.60` |
| strict | `0.70` |
| very strict | `0.80` |

Expected diagnostic metric:

- Primary: `low_probability_rate`
- Secondary: `regime_no_trade_rate`, `max_regime_probability_p05`, `max_regime_probability_mean`, accepted KNN/meta counts

Expected interpretation:

- Baseline low-probability rate was about `8.07%`, much lower than no-trade rate, so threshold changes alone should not solve the `91%` no-trade rate.
- If lowering the threshold has little impact, it confirms flip cooldown dominates.

Decision rule:

- Keep `0.60` if changes do not materially improve tradeable rows or downstream quality.
- Consider `0.50` only if it materially improves tradeable rows without increasing poor neighbor quality or bad meta outcomes.

# Experiment 4: HMM emission feature subset ablation

Purpose:

Determine whether noisy or unstable emission features are causing rapid regime switching.

Config fields to change:

- `hmm.emission_features`

Baseline features:

```json
[
  "directional_slope_atr",
  "choppiness",
  "realized_volatility",
  "atr_percentile",
  "volatility_shock_zscore",
  "funding_rate",
  "open_interest_change_pct",
  "primary_signed_imbalance_ratio",
  "top_of_book_imbalance"
]
```

Feature subset variants:

| Variant | `hmm.emission_features` | Hypothesis |
| --- | --- | --- |
| price-vol-core | `["directional_slope_atr", "choppiness", "realized_volatility", "atr_percentile", "volatility_shock_zscore"]` | Removes perp/microstructure noise; should reduce flips if exchange-context fields are unstable. |
| trend-chop-vol-minimal | `["directional_slope_atr", "choppiness", "realized_volatility", "volatility_shock_zscore"]` | Tests whether a smaller state model is more persistent. |
| no-orderbook | baseline minus `["primary_signed_imbalance_ratio", "top_of_book_imbalance"]` | Tests whether microstructure inputs drive short-horizon state churn. |
| no-perp | baseline minus `["funding_rate", "open_interest_change_pct"]` | Tests whether perp structure fields add instability. |
| vol-shock-only | `["realized_volatility", "atr_percentile", "volatility_shock_zscore"]` | Tests whether shock/range/trend labels are being overfit by directional features. |
| trend-chop-only | `["directional_slope_atr", "choppiness"]` | Tests a highly stable low-dimensional router; likely less expressive. |

Expected diagnostic metric:

- Primary: `recent_regime_flip_rate`, switches per 100 rows, mean/median run length
- Secondary: regime distribution, `shock_transition` share, `range_chop` share, entropy p95, no-trade rate

Expected interpretation:

- A good subset reduces flips while preserving all four regimes and keeping `range_chop`/`shock_transition` above `5%`.
- A bad subset collapses states, eliminates shock/range, or increases entropy sharply.

Decision rule:

- Prefer the smallest feature set that preserves all four regimes and reduces flip rate.
- If removing order book or perp fields reduces flips materially, move those features downstream to KNN/meta rather than HMM emissions.

# Experiment 5: longer training history / walk-forward split sensitivity

Purpose:

Test whether unstable regimes are caused by insufficient training history or too frequent refits.

Config fields to change:

- `evaluation.train_fraction`
- `evaluation.min_training_rows`
- `evaluation.walk_forward_splits`

Grid:

| Variant | `evaluation.train_fraction` | `evaluation.min_training_rows` | `evaluation.walk_forward_splits` | Hypothesis |
| --- | ---: | ---: | ---: | --- |
| baseline | `0.60` | `50` | `3` | Current behavior. |
| more train | `0.70` | `50` | `3` | More historical context stabilizes state statistics. |
| much more train | `0.80` | `50` | `3` | Stronger stability test with fewer scored rows. |
| higher min rows | `0.60` | `200` | `3` | Prevents small early train windows from dominating. |
| fewer refits | `0.70` | `200` | `2` | Tests whether refit boundaries create churn. |
| single late test | `0.80` | `300` | `1` | Maximum stability smoke; fewer validation rows. |

Expected diagnostic metric:

- Primary: `recent_regime_flip_rate`, split-level flip rate, run length by split
- Secondary: regime distribution by split, no-trade rate, backend, row count, KNN/meta trade counts

Expected interpretation:

- If longer training history reduces flips, the HMM/fallback model needs more stable train windows or fewer refits.
- If flips remain high across longer histories, instability likely comes from emissions or posterior labeling/scoring behavior.

Decision rule:

- Prefer a setting that lowers flip rate without eliminating shock/range or starving validation rows.
- Do not accept a setting that only appears stable because it produces too few scored rows.

# Recommended run order

Run these in order:

1. Flip-cooldown sensitivity.
2. Posterior threshold sensitivity.
3. Entropy threshold sensitivity.
4. Feature subset ablation.
5. Longer training history / split sensitivity.

Reasoning:

- Cooldown sensitivity is the fastest way to separate policy-caused no-trade from model-caused instability.
- Posterior and entropy thresholds quantify whether uncertainty gates matter.
- Feature subset and train-history experiments are heavier and should be interpreted after the policy gates are understood.

# Suggested output table for each experiment

Each run should write a small summary row like:

| experiment_id | changed_fields | rows | regimes_present | range_pct | shock_pct | flip_rate | no_trade_rate | low_prob_rate | high_entropy_rate | entropy_p95 | max_prob_p05 | tradeable_rate | notes |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |

# Assumptions

- The high no-trade behavior reported by the architecture review used the real BTC artifact, not the synthetic CLI smoke artifact.
- `config` in the requested command refers to repo configuration files; this repo uses `configs/`.
- These are experiment specifications only. No config files or model code were changed in this task.
- Current active environment lacks optional `hmmlearn`, so early experiment results may reflect `gaussian_mixture_fallback`; install the research extra before comparing final HMM behavior.

# Open issues or blockers

None.

No issue was appended because this task is a planning/specification task and the requested config typo was resolved by searching `configs/`.

# Handoff notes for other agents

- The fastest likely win is to measure cooldown sensitivity first. Baseline evidence says recent flips, not entropy, dominate no-trade behavior.
- Feature ablation should specifically test whether microstructure and perp fields destabilize the router.
- A future Backtest/Regime task should implement a small experiment runner that clones the base config, mutates these fields, runs `research-hmm-knn`, and writes a CSV summary using the output table above.
