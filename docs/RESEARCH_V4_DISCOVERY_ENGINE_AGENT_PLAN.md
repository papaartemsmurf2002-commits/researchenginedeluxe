# Research V4 Discovery Engine Agent Plan

Status: ready for next agentic implementation stage
Date: 2026-05-07
Branch role: research-only discovery, no live execution

This plan replaces the current "small constrained cycle" mindset with a durable discovery engine that can run for hours or days, checkpoint progress, and surface possible candidates without pretending that any candidate is promotion-ready.

The current branch already has useful infrastructure: provider fixtures, feature materialization, strategy plugins, backtests, split/cost-stress evidence, candidate gates, research UI, HMM/KNN diagnostics, and fail-closed candidate packs. The missing part is real discovery breadth: regime-local KNN tuning, proper trial budgeting, snapshots, filter ablations, and operator-visible blocker diagnostics.

## Interpretation Of The New Direction

### Accepted Ideas

- HMM is a regime detector, not the alpha engine.
- KNN should be tuned separately per HMM regime, because one global KNN blends incompatible market states.
- Perp context and microstructure should be tested semi-separately before becoming filters or entry strategies.
- KNN-style entries should become a high-signal discovery family because they can produce enough trades for exits and gates to matter.
- KNN feature sets are open research variables. WT and WT3D can be tested, but the system must also be able to ditch WT entirely and research alternative non-WT column sets.
- Feature/filter candidates such as ER, VWAP, HVP, autocorrelation, Hurst, NTRI, entropy, and KNN internal confidence should be tested as ablations, not hard-coded as truth.
- Feature combinations should be predeclared and stability-tested. Do not brute-force millions of arbitrary combinations.
- Long discovery runs need durable snapshots at least every 30 minutes and after every completed trial batch.
- The system should produce "interesting candidates" and "blocked candidate reasons" even when strict research gates reject all packs.

### Conditional Ideas

- Perp funding/OI/premium context may help as a feature, entry family, filter, or exit trigger, but must be compared against a no-perp baseline.
- Microstructure/order-book data is likely too fast-decaying for 15m directional entries, but liquidation/wick/absorption proxies can be tested at candle scale.
- HMM regime labels can improve KNN if they are split-safe and stable; they can also hurt by over-fragmenting data.
- Feature stacks above 6-8 dimensions can help only if distance quality remains strong; otherwise KNN suffers from sparse neighborhoods.
- KNN kernels/weighting/distance metrics should be optimized, but under strict trial budgeting and leakage-safe validation.
- WT is optional. Do not make WT or WT3D a privileged assumption in architecture, UI, gates, or candidate-pack language.

### Rejected For Default Wiring

- Hard-blocking all entries with perp/microstructure filters before ablation evidence.
- Treating one latest-month cycle as discovery evidence.
- Running global KNN over all regimes and calling that regime-aware.
- Full-dataset HMM posteriors or scalers that see future rows.
- One giant Cartesian grid over every feature/filter/KNN/exit parameter.
- Candidate acceptance from a single profitable aggregate backtest.

## Target Architecture

```text
provider data
  -> point-in-time feature frames
  -> split-safe HMM regime materialization
  -> regime-local KNN discovery studies
  -> filter/context ablation studies
  -> candidate signal frame materialization
  -> execution and exit simulation
  -> split/stress/ablation/stability evidence
  -> interesting-candidate ledger
  -> strict research gate
  -> research-only candidate pack only if all gates pass
```

## Layer 0: Data Universe

Minimum real discovery data should be 6-12 months. A one-month fixture is only a smoke test.

Required data families:

- Primary OHLCV bars, initially 15m.
- Optional lower-timeframe bars for better entry/exit sequencing.
- Funding rate, premium/mark-index basis, and open interest.
- Optional liquidation and candle-scale absorption evidence.
- Optional spot/perp or cross-exchange context later.

Data rules:

- All joins must be point-in-time and event-time bounded.
- Provider/latest-window evidence must be labeled as such.
- No legacy TradingView exports.
- No synthetic evidence for candidate-pack eligibility.
- Crypto Lake free samples can test plumbing but cannot satisfy broad OOS evidence.

## Layer 1: Feature Families

Feature families must be ablation-friendly. Every feature pack needs identity, provenance, missingness, and split-safe scaler state.

Important naming rule:

- Registered feature-set manifests use repo IDs such as `features_price_trend_vol`, `features_price_trend_vol_wt3d`, `features_full_context_wt3d`, `features_full_context_no_wt`, `features_price_perp_micro_no_wt`, and `features_perp_context_v2`.
- HMM/KNN `feature_pack` keys such as `price_trend_vol`, `full_context_wt3d`, and `full_context_no_wt3d` are KNN column-set keys, not registered `features_*` manifests.
- Future agents should use "KNN feature-column set", "KNN study feature matrix", or "KNN feature-pack variant" when discussing flexible KNN inputs.
- New persistent feature-set names require registry/config/test work. Do not introduce names only in docs or specs.

### Core OHLCV / KNN Features

Start with compact, distance-friendly features:

- Price path and return-shape features.
- Trend/chop and displacement features.
- Volatility state features.
- Optional WT or WT3D components.
- CCI or comparable momentum deviation.
- NATR or volatility percent feature.
- CMF or volume-flow proxy.
- Fisher transform or pivot-shape feature.
- VWAP deviation.
- Efficiency Ratio.
- Historical Volatility Percentile.

### KNN Feature-Column Set Families

The KNN study engine must let feature sets vary by configuration, not by hardcoded strategy logic.

Predeclared first-wave families:

| Family | Repo status | Purpose |
| --- | --- | --- |
| `price_trend_vol` | existing HMM/KNN column-set key | Price path, trend/chop, and volatility baseline. |
| `full_context_no_wt3d` | existing HMM/KNN column-set key | Broad context without WT3D, used as no-WT comparator. |
| `full_context_wt3d` | existing HMM/KNN column-set key | Broad context with WT3D columns. |
| `features_price_trend_vol` | registered feature-set ID | Manifest-backed OHLCV/trend/vol baseline. |
| `features_price_trend_vol_wt3d` | registered feature-set ID | Manifest-backed WT3D comparator. |
| `features_full_context_no_wt` | registered feature-set ID | Full context no-WT baseline. |
| `features_full_context_wt3d` | registered feature-set ID | Full context with WT3D. |
| alternative non-WT price-state set | proposed, not registered | Non-WT columns such as `direction_long`, `directional_slope_atr`, `directional_di_spread`, `choppiness`, `range_width`, ER, HVR, HVP, VWAP deviation, autocorrelation, and similar price-state features. |
| compact WT base | proposed KNN column subset | Minimal WT or WT-like oscillator plus price-state features. |
| compact WT3D base | existing/proposed hybrid | Minimal WT3D columns plus price-state features, excluding perp/microstructure unless ablation adds them. |

The plan intentionally keeps WT optional. Alternative non-WT sets must be first-class candidates, not fallback afterthoughts.

### Bounded Feature-Combination Matrix

The first implementation must not search arbitrary feature subsets. It should use a predeclared matrix:

1. Baseline: price/trend/vol only.
2. WT base: baseline plus compact WT or WT-like oscillator columns.
3. WT3D base: baseline plus compact WT3D columns.
4. Alternative non-WT price-state: baseline plus ER/HVR/HVP/VWAP/autocorrelation or similar columns.
5. WT3D plus one experimental filter feature.
6. Alternative non-WT plus one experimental filter feature.
7. Perp as feature addition.
8. Microstructure/liquidation proxy as feature addition.
9. Selected combinations only after single-addition ablations improve split stability and distance quality.

Predeclared ranges should be explicit in config:

- `feature_column_set_id`
- ordered column list
- scaler policy
- clamp policy
- maximum dimensions
- required comparator set
- allowed experimental additions
- disabled reason when not eligible

The starting maximum dimensionality should be conservative, for example 6-8 active KNN dimensions for first-wave discovery. Any larger set must show distance-quality, neighbor-count, and split-stability evidence before it is allowed into deep discovery.

### Experimental Candle-Scale Context

Test one addition at a time:

- NTRI / wick rejection.
- Rolling Shannon entropy.
- Hurst exponent.
- Lag-1 autocorrelation.
- HVR short-vol over long-vol ratio.

### Perp Context

Treat as four separate roles:

- `perp_features_only`: funding/OI/premium included as KNN dimensions.
- `perp_filter_only`: KNN entry generated first, perp context can allow/block.
- `perp_strategy_only`: existing transparent perp rules run separately.
- `perp_exit_only`: funding/OI context can exit but not enter.

No global claim is valid until these roles are compared against `no_perp_context`.

## Layer 2: HMM Regime Detector

HMM should materialize columns into the historical cycle frame before KNN strategy candidates use them.

Required outputs per row:

- `top_regime_label`
- `max_regime_probability`
- `posterior_entropy`
- `recent_regime_flip`
- `regime_no_trade`
- `hmm_fit_end_row`
- `source_row_index`
- `hmm_model_id`
- `hmm_feature_pack_id`
- `hmm_split_id`

Split-safety rule:

```text
hmm_fit_end_row < source_row_index
```

Regime labels should be stable semantic labels such as:

- range/chop
- bull trend
- bear trend
- shock/transition
- uncertain/no-trade

HMM is allowed to say "no-trade/unknown." It must not force every bar into an actionable alpha sleeve.

## Layer 3: Regime-Local KNN Discovery

Each regime gets its own KNN study. A KNN candidate is not just `k`; it is a full local analog configuration.

Candidate identity:

```text
symbol
+ timeframe
+ feature_pack
+ regime_label
+ label_horizon
+ side_policy
+ distance_metric
+ k
+ neighbor_weighting
+ scaler
+ probability_threshold
+ expected_value_threshold
+ min_neighbor_count
+ agreement_threshold
+ distance_quality_threshold
+ filter_pack
+ entry_spacing
+ exit_policy
```

Feature-column-set identity is part of the candidate identity. A candidate that differs only by WT base versus WT3D base versus non-WT price-state columns is a different candidate family and needs its own comparator evidence.

Initial KNN search dimensions:

- `k`: for example 8, 12, 16, 24, 32, 48, 64.
- distance: Lorentzian, Manhattan, Euclidean, cosine where supported.
- weighting: uniform, inverse distance, softmax.
- feature-column sets: no-WT baseline, WT base, WT3D base, alternative non-WT price-state sets, core 6, core + one experimental feature, selected combinations.
- label horizon: 4h, 12h, 24h, 72h.
- thresholds: probability, vote margin, expected value, agreement, distance quality.
- filters: none, ER, HVP, VWAP, autocorrelation, HVR, Hurst, combinations.

Search must be hierarchical:

1. Cheap per-regime screening on a limited candidate budget.
2. Promote top regions into deeper validation.
3. Run exit-policy labs only for entries with enough trades.
4. Run strict split/stress/stability only for shortlisted candidates.

This avoids a two-year computation while still doing real search.

### Feature-Combination Stability

The existing optimizer region-of-stability gate groups candidates only inside the same strategy, feature set, holding window, exit policy, and exit params. Do not overload that gate to claim stability across feature combinations.

Add a separate discovery diagnostic named `feature_combination_stability` before any future pack gate uses it.

Required behavior:

- Build graph edges only between predeclared neighboring feature-column sets, such as baseline -> WT3D base or baseline -> alternative non-WT price-state.
- Do not connect arbitrary feature sets after the fact.
- Compare each added feature or feature group against its required no-addition comparator.
- Require stable improvement in split consistency, distance quality, and trade density, not just aggregate return.
- Require degradation reasons when a feature set loses: lower neighbor quality, lower trade count, worse drawdown, higher missingness, or unstable split performance.
- Keep feature-combination stability diagnostic-only until a later packet adds candidate-pack gate support.

First pass acceptance for a feature-column set into deeper search:

```text
beats comparator on median split score
+ does not reduce trade count below floor
+ improves or preserves neighbor_distance_quality
+ does not increase missingness beyond allowed bound
+ survives at least one cost/stress screen
+ has a connected local parameter region, not one spike
```

## Layer 4: Entry And Filter Semantics

Do not mix entry and filter roles in one opaque result.

Entry generators:

- WT/KNN local analog.
- HMM-routed KNN local analog.
- Existing perp transparent strategies.
- Future liquidation/absorption classifier.

Filter families:

- KNN internal filters: distance quality, neighbor agreement, vote margin, sparse-cluster rejection.
- Price-state filters: ER, HVP, VWAP deviation, autocorrelation, HVR, Hurst.
- Perp filters: funding, OI, premium, basis, liquidation context.
- HMM filters: posterior confidence, entropy, recent flip, no-trade regime.

Every run must report:

- raw signals generated;
- signals blocked by each filter;
- signals skipped by one-position/no-overlap assumption;
- signals converted to trades;
- trades closed by each exit reason.

## Layer 5: Execution And Exit Labs

Exit strategies are meaningless when entries produce only a few trades. Exit optimization starts only after a candidate family clears signal/trade density floors.

Execution modes:

- `single_position_serial`: current conservative mode.
- `overlap_allowed_research`: permits overlapping independent signals for discovery diagnostics.
- `cooldown_limited`: allows a new entry after configurable bars.
- `side_aware_serial`: separate long and short channels.

Exit labs:

- fixed holding windows.
- triple barrier when lower-timeframe coverage exists.
- volatility-scaled barrier.
- funding-aware exit.
- OI contraction exit.
- alpha decay / KNN remaining-edge exit.
- HMM transition exit.
- trailing after profit.
- max-MAE stop.

Exit lab rule:

```text
entry search first, exit search second, strict gate last
```

## Layer 6: Discovery Run Manager

Long runs need a first-class run manager, not ad hoc CLI loops.

Proposed artifact layout:

```text
data/research/discovery_runs/{run_id}/
  discovery_run_manifest.json
  discovery_spec_resolved.json
  study.sqlite3
  run_state.json
  trials/
    trial-000001.json
    trial-000001_metrics.parquet
  snapshots/
    20260507T120000Z_snapshot.json
    20260507T123000Z_snapshot.json
  candidate_ledgers/
    interesting_candidates.parquet
    blocked_candidates.parquet
    filter_blockers.parquet
  feature_cache/
  hmm_cache/
  knn_cache/
  backtests/
  reports/
    operator_progress.md
    discovery_summary.md
```

Snapshot policy:

- Write after every completed trial batch.
- Write every 30 minutes even if the batch is still running.
- Use atomic temp-file then rename writes.
- Store enough state to resume without recomputing completed trials.
- Store RNG seeds, data hashes, feature hashes, candidate hashes, and code version.

Resume policy:

- Same spec and same run ID resumes.
- Changed spec creates a new run unless explicitly marked `resume_with_compatible_extension`.
- Completed trials are immutable.
- Failed trials keep error payload and can be retried with a new attempt ID.

## Layer 7: Optimizer Strategy

Use deterministic grids only for smoke tests. Real discovery should use budgeted search.

Recommended search engines:

- Existing repo search-space tools for deterministic and contract-safe expansion.
- Optuna-style persistent studies for long searches, because RDB storage can save and resume studies and pruning can terminate weak trials early.
- Random or Sobol first-stage screens to reduce grid bias.
- TPE/Bayesian sampling for conditional spaces after the first screen.

Budget examples:

- quick: 50-200 trials.
- standard: 2,000-10,000 trials.
- deep/day-two: 25,000+ trials with resume and pruning.

Budgets are allocated hierarchically:

- feature-column-set screen first;
- regime-local KNN threshold and `k` tuning second;
- filter additions third;
- exit lab fourth;
- strict validation last.

Do not allow a single run spec to expand into millions of combinations unless it is explicitly marked as a deep run, has resume enabled, has max wall-clock and max trial counts, and writes snapshots.

Objective should be multi-component:

```text
score =
  costed expectancy
  + split consistency
  + trade density score
  + drawdown penalty
  + overfit penalty
  + distance-quality penalty
  + data-quality penalty
```

Do not optimize only final return.

## Layer 7.5: Calculation Correctness Standards

Future implementation must assume tiny mathematical errors are dangerous because they can hide in a large research run.

Required safeguards:

- Every feature formula gets a tiny hand-computed fixture test.
- Every rolling feature proves no future fill, no `bfill`, no full-dataset scaler, and no validation-row fitting.
- Every KNN distance metric has deterministic toy-matrix tests with expected neighbor order.
- Every scaler/clamp/min-max transform stores train-only fit state and has NaN/inf tests.
- HMM posteriors prove `hmm_fit_end_row < source_row_index`.
- KNN neighbors prove `neighbor_max_source_index <= hmm_fit_end_row < source_row_index`.
- Signal accounting must reconcile exactly: raw signals = executed trades + overlap skips + filter blocks + end-of-data skips.
- Resume tests must prove that interrupted and uninterrupted runs produce identical completed-trial ledgers.
- Snapshot tests must prove atomic write behavior and readable partial-progress summaries.
- Parallel execution tests must prove result equivalence to serial execution for the same seed and trial budget.
- Any vectorized implementation must be crosschecked against a simple reference implementation on small fixtures.
- Any GPU or approximate-neighbor backend must remain opt-in until parity is proven against CPU/brute-force reference.

Testing minimum for implementation packets:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Each packet must also add focused tests for the specific formulas, identities, caches, snapshots, or UI behavior it changes.

## Layer 8: Validation And Gates

Validation must remain stricter than discovery ranking.

Discovery can produce interesting candidates when gates fail. Candidate packs require gates to pass.

Required evidence for a pack:

- provider-backed non-synthetic fixture provenance;
- enough trades by candidate and split;
- purged/embargoed validation;
- side and regime evidence;
- no single split dominating PnL;
- cost stress survival;
- feature/filter ablation evidence;
- stability region evidence;
- no unresolved data-quality blockers;
- no live/promotion flags.

Recommended validation flow:

1. In-sample research screen.
2. Purged rolling split.
3. Anchored split.
4. Regime holdout.
5. Time holdout.
6. Cost/funding/spread stress.
7. Feature/filter ablation.
8. Exit sensitivity.
9. Candidate-pack gate.

## Layer 9: Operator UI Requirements

The operator needs a discovery control room, not a blank artifact viewer.

Required UI panels:

- active discovery run status;
- trial throughput;
- next snapshot ETA;
- last successful snapshot path;
- current best interesting candidates;
- strict-gate accepted count;
- top blockers by count;
- raw signals vs executed trades;
- filter ablation matrix;
- per-regime KNN summary;
- perp context contribution summary;
- resume/stop-safe instructions.

UI must clearly separate:

- interesting candidate;
- rejected candidate;
- strict gate candidate;
- research candidate pack;
- promotion candidate, which should remain absent on this branch.

## Cycle Variants

### `quick_smoke`

Purpose: plumbing only.
Runtime: minutes.
Data: latest fixture or small sampled period.
Acceptance: never promotion evidence.

### `entry_discovery_standard`

Purpose: find signal-rich WT/KNN candidates.
Runtime: hours.
Data: 6-12 months.
Exits: fixed/simple first.
Output: interesting candidates and blockers.

### `hmm_regime_knn_lab`

Purpose: fit HMM split-safely and tune KNN per regime.
Runtime: hours to day.
Output: per-regime KNN studies and posterior materialization.

### `perp_context_ablation`

Purpose: prove whether perp context helps.
Variants:

- no perp context;
- perp as KNN features;
- perp as filter;
- perp as transparent strategy;
- perp as exit trigger.

### `filter_ablation_lab`

Purpose: test ER/VWAP/HVP/autocorrelation/HVR/Hurst/NTRI/entropy as filters or features.
Rule: add one filter at a time before testing combinations.

### `exit_lab`

Purpose: optimize exits after entries produce enough trades.
Input: shortlisted entry candidates only.

### `deep_candidate_harvest`

Purpose: day-or-two run to one-shot possible candidates.
Runtime: 24-48 hours.
Requirements: persistent study, snapshots, resume, cache, operator progress.

### `promotion_gate_research_only`

Purpose: strict final candidate-pack gate.
Runtime: as needed.
Output: research-only candidate pack only if all gates pass.

## Implementation Work Packets

Each implementation packet should use subagents for independent review where useful:

- one code worker for the bounded implementation scope;
- one explorer for contract and dependency checks;
- one reviewer or verification pass for calculation correctness, leakage, and artifact identity.

Agents must not edit overlapping files in parallel unless write ownership is explicitly disjoint.

### WPR73 Discovery Run Manager

Add discovery specs, run manifests, state store, snapshots, resume semantics, and operator-safe output directories.

Allowed areas:

- `src/tradingbotsuite/research_discovery/**`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/operator_console.py`
- `tests/research_discovery/**`
- docs and configs for discovery specs

### WPR74 Core Discovery Feature Packs

Add compact WT/KNN feature-column set support and ablation feature packs: ER, HVP, VWAP deviation, autocorrelation, HVR, Hurst, NTRI, entropy.

Required planning constraints:

- Reuse existing registered feature-set IDs where possible.
- Keep flexible KNN column sets separate from persistent `features_*` manifest names.
- Define no-WT baseline, WT base, WT3D base, and alternative non-WT candidate sets in config with explicit column lists.
- WT and WT3D must have no-WT comparators and must not become default unless evidence beats non-WT alternatives.
- Add feature math reference tests before any feature is used in discovery.

Keep perp context separate.

### WPR75 Split-Safe HMM Materialization

Materialize HMM posteriors into historical-cycle frames using train-only fits per split/window.

No full-dataset posterior leakage.

### WPR76 Regime-Local KNN Study Engine

Implement per-regime KNN study generation, feature scaling, distance/weighting thresholds, neighbor diagnostics, and prediction materialization.

Use cached feature matrices and persistent trials.

Must include bounded feature-column-set candidate generation, predefined search ranges, and distance-quality diagnostics.

### WPR77 WT/KNN Strategy Candidate Integration

Wire materialized KNN predictions into standard strategy plugins and historical-cycle candidate generation.

Expose raw signal, filter block, and executed trade counts.

### WPR78 Perp Context And Filter Ablation Matrix

Run no-perp/perp-feature/perp-filter/perp-strategy/perp-exit comparisons.

No filter can become default without winning ablation evidence.

Also include feature-combination stability diagnostics for no-WT baseline, WT base, WT3D base, alternative non-WT sets, and selected experimental additions.

### WPR79 Exit Lab

Run exit studies only on entry candidates with enough trade density.

Compare fixed holding, barriers, funding/OI/HMM/KNN exits, and trailing policies.

### WPR80 Operator Discovery UI

Add discovery run launch/resume/stop-safe UX, snapshots, candidate ledger, blocker tables, and per-regime charts.

### WPR81 Deep Discovery Benchmarks

Add benchmark tiers for quick, standard, and deep discovery. Validate resume behavior and snapshot integrity.

### WPR82 Candidate Pack Bridge

Allow strict-gate winners from discovery runs to enter the existing research-only candidate-pack validator without bypassing current evidence requirements.

## Critical Guardrails

- No live order adapters in research discovery modules.
- No promotion-ready flags.
- No full-dataset fitting for HMM, scalers, labels, or KNN thresholds.
- No hidden filters: every block reason must be counted.
- No accepting latest-month-only evidence.
- No hard-coded perp/microstructure benefit assumption.
- No giant unbounded grid.
- No overwriting prior run artifacts.
- No losing progress on interruption.

## References Used For Design

- `hmmlearn` provides Gaussian HMM implementations and is already an optional repo dependency: https://hmmlearn.readthedocs.io/en/0.3.3/tutorial.html
- scikit-learn's nearest-neighbor API documents tree/brute search options and distance-metric interfaces useful for KNN backend planning: https://scikit-learn.org/stable/modules/neighbors.html
- Optuna's paper and docs support define-by-run, pruning, and persistent/resumable studies: https://arxiv.org/abs/1907.10902 and https://optuna.readthedocs.io/en/v3.0.3/tutorial/20_recipes/001_rdb.html
- Financial ML validation needs purging/embargoing when labels overlap future horizons; this repo already has purged/embargoed concepts and should keep them central. See Lopez de Prado references summarized at https://www.quantresearch.org/Innovations.htm
- KNN high-dimensional behavior requires feature discipline and distance-quality diagnostics. See nearest-neighbor curse-of-dimensionality discussion in https://arxiv.org/abs/1110.4347

## End State

After this plan is implemented, an operator should be able to start a 24-48 hour research-only discovery run, leave it running, and inspect snapshots every 30 minutes. The system should show what it tested, what it skipped, why entries were blocked, which regimes produced useful KNN candidates, whether perp context helped or hurt, and which candidates deserve strict validation.

The expected normal outcome is still zero candidate packs until evidence is strong. The difference is that zero packs will no longer look like a nothing burger: the branch will produce a complete discovery ledger explaining what was searched and why each promising idea did or did not survive.
