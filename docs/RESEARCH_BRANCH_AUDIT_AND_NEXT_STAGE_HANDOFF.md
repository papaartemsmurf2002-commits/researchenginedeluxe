# Research Branch Audit And Next Stage Handoff

Date: 2026-05-10
Branch: `research/v3-experimental-engine`
Audience: next high-capability research/development agent

This document condenses the current branch structure, completed work, latest
discovery-run findings, and the recommended next research stage. It should be
read after `AGENTS.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, and
`docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`.

For the expanded real-strategy/filter/feature implementation roadmap, also read
`docs/RESEARCH_NEXT_PHASE_REAL_STRATEGIES_FILTERS_FEATURES_PLAN.md`.

## Current Branch Role

This is a research and experimentation branch. It owns provider intake,
historical fixtures, feature construction, strategy research, backtesting,
optimizer/stability gates, HMM/KNN discovery experiments, discovery UI, and
research artifact handling.

It is not a live trading branch. Research outputs must remain:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`

Do not import live order-placement adapters into research modules. Do not make
research jobs place orders, alter runtime mode, write live config, or claim live
readiness.

## Repo Structure Summary

```text
AGENTS.md
START_HERE.md
README.md
docs/
  ORCHESTRATOR_STAGE_LEDGER.md
  KNOWN_ISSUES.md
  REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md
  OPERATOR_QUICKSTART.md
  OPERATOR_GUIDE.md
  RESEARCH_BRANCH_AUDIT_AND_NEXT_STAGE_HANDOFF.md
  contracts/
  runbooks/
  stage_reports/
  work_packets/
configs/
  discovery/
  features/
  research/
  strategies/
data/
  research/
    fixtures/
    historical_cycles/
    operator_runs/
src/
  tradingbotsuite/
    data/
    features/
    strategies/
    backtesting/
    optimization/
    research_cycle/
    research_discovery/
    research_artifacts/
    research/
    web/
    ui/
    operator_console.py
    main.py
    live/
    promotion/
  tradingbot/
tests/
  contracts/
  research_discovery/
  historical/
  backtesting/
  features/
  optimization/
  live/
```

## Package Responsibilities

| Package | Responsibility | Rewrite caution |
| --- | --- | --- |
| `tradingbotsuite.data` | Provider manifests, fixture-pack validation, provenance, storage. | Do not weaken hashes, source metadata, row counts, gap checks, or research-only flags. |
| `tradingbotsuite.features` | Feature registry, completed-bar alignment, context joins, feature cache identity. | Preserve point-in-time behavior, interval-aware rolling windows, and cache identity fields. |
| `tradingbotsuite.strategies` | Strategy plugin contract, registry, signal validation, metadata. | Keep strategy configs bounded and signal frames contract-valid. |
| `tradingbotsuite.backtesting` | Reference/vector engines, splits, exits, execution simulation, metrics. | Preserve split evidence, cost/funding semantics, and lower-timeframe exit identity. |
| `tradingbotsuite.optimization` | Candidate search, cache, region-of-stability, overfit/stability diagnostics. | Do not turn spike candidates into accepted candidates by weakening gates. |
| `tradingbotsuite.research_cycle` | Main historical-cycle orchestration. | High-risk shared layer; connects data, features, strategies, backtests, rankings, gates. |
| `tradingbotsuite.research_discovery` | V4 discovery manager, split-safe regime materialization, KNN study, ledgers, snapshots, candidate bridge. | Current next work should focus here, but preserve artifact contracts and resume behavior. |
| `tradingbotsuite.research_artifacts` | Candidate-pack validation/writing and promotion boundaries. | Do not allow incomplete discovery artifacts into candidate packs. |
| `tradingbotsuite.web`, `tradingbotsuite.ui`, `operator_console.py` | Operator UI and research controls. | UI must remain a guarded control/visibility surface, not a source of research truth. |
| `tradingbotsuite.live`, `tradingbotsuite.promotion` | Live preflight and shadow/promotion guards. | Research outputs must remain rejected by live paths unless a later approved process changes that. |

## Work Completed On This Branch

The branch now has:

- Binance REST/Binance Vision/local manifest/Crypto Lake free-sample fallback
  provider surfaces.
- Historical fixture packs with provenance, hashes, optional context families,
  interval metadata, and research-only flags.
- Feature registry and feature cache with completed-bar alignment and
  interval-aware construction.
- Historical research cycle that loads fixtures, builds features, creates
  validation splits, expands strategy candidates, backtests them, ranks them,
  writes gate evidence, and refuses weak candidates.
- Strategy plugins for baselines, perp context, funding/OI/timing,
  HMM/KNN local analog filtering, liquidation absorption, and no-trade
  comparators.
- Backtesting support for reference execution, vector fixed-holding execution,
  fixed holds, lower-timeframe triple-barrier, primary-bar exits, funding/cost
  stress evidence, and artifact manifests.
- Optimizer/stability tooling, candidate identity, region-of-stability gates,
  feature ablation, benchmark evidence, and candidate-pack validation.
- V4 discovery engine:
  - resume-safe run manager
  - atomic snapshots
  - immutable trial records
  - interesting/blocked/filter-blocker ledgers
  - split-safe regime materialization
  - regime-local KNN prediction overlays
  - feature-column set manifests
  - perp/filter ablation helpers
  - discovery exit-lab helpers
  - discovery candidate-pack bridge
  - standard/deep discovery configs
  - operator UI launch/resume/summary controls
- Operator documentation and UI quickstart.
- Full branch validation at Stage R92:
  - `python -m compileall -q src\tradingbotsuite`
  - contracts passed
  - focused discovery/operator tests passed
  - full suite passed: 1144 tests

## Latest Deep Discovery Run

Artifact audited:

```text
data/research/operator_runs/discovery_runs/deep-candidate-harvest-btcusdt-v4/
  run-discovery-ba58bbf8c49c42b1971beb0dbc6d5fd0/
```

The run completed mechanically:

- Trials: `5000/5000`
- Runtime: about 2h 26m
- Fixture: latest-month BTCUSDT context fixture
- Rows: `2873`
- Interesting candidates: `2714`
- Blocked candidates: `2286`
- Filter blockers: `0`
- Candidate pack written: `false`
- Live/order placement flags: false
- Promotion ready: false

Important aggregate results:

- Search space total: `887,040,000` combinations
- Sampled fraction: about `0.00056%`
- Top score candidate was near the signal-rate ceiling:
  - candidate: `deep_candidate_harvest_btcusdt_v4-hmm-knn-319db9eb017c8f43`
  - feature set: `price_trend_vol`
  - horizon: `72h`
  - distance/k: `cosine`, `k=5`
  - same-regime only: `false`
  - signal rate: `0.4479638009`
  - trade count: `1287`
  - realized expectancy: `0.0131831229`
  - side counts in accounting: `1339` long, `54` short
- Top expectancy candidates were mostly `alternative_non_wt_price_state`,
  `72h`, and all-regime KNN, but they scored below denser candidates because
  the score rewards trade count.
- `liquidation_feature_addition_smoke` was not tested meaningfully. It was
  blocked by `feature_set_preflight_insufficient_finite_variant_columns`.

## Critical Interpretation

The latest run proves the discovery machinery can run, checkpoint, persist
ledgers, and produce candidates. It does not yet prove that KNN/HMM/perp
context/orderflow/exits produce a robust strategy.

Current limitations:

1. The current "HMM" implementation in discovery is actually a split-safe
   `sklearn.mixture.GaussianMixture` regime clusterer. It does not model a
   hidden-state transition matrix. Treat it as GMM regime detection unless a
   true HMM backend is added.
2. A clean no-regime baseline is missing. Even `same_regime_only=false` still
   uses the regime `no_trade` gate, so it is not a no-HMM/no-GMM comparison.
3. The search is random sampled, not adaptive optimization. It tests 5000
   unique parameter combinations from a very large grid but does not establish
   region-of-stability across nearby feature/filter/parameter variants.
4. The current score over-rewards trade density:

   ```text
   final_score =
     realized_expectancy
     + 0.05 * log1p(trade_count)
     + 0.01 * avg_neighbor_quality
     + 0.01 * avg_vote_margin
   ```

   This can rank broad exposure filters above selective edges.
5. High signal-rate, long-horizon labels create overlapping events. A `72h`
   horizon on 15m bars means many accepted rows are not independent executable
   trades.
6. The latest fixture is latest-window only. It is useful for machinery and
   initial discovery, not durable multi-market/multi-regime evidence.
7. Entry filters such as HVP, ATR percentile, ER/chop, volatility shock,
   funding/OI, basis, liquidation, and orderflow are not yet tested as clean
   filter-on/filter-off ablations under the same entry settings.
8. Orderflow is not meaningfully represented yet. Binance public archives cover
   klines/trades/aggTrades; real order book imbalance requires depth snapshots
   plus diff-depth stream handling or an archived depth provider.
9. Exit strategy selection is not mandatory in the deep discovery loop. The run
   uses directional future-close labels and strategy accounting, but candidates
   still need mandatory fixed-hold vs triple-barrier vs ATR/trailing/regime/funding
   exit comparisons.
10. Machine resources are underused for deep research. Current discovery uses
    `ThreadPoolExecutor`, `max_workers=8`, per-trial KNN work, caches, and
    serial artifact writes. It is not using 15 threads, process parallelism,
    vectorized threshold sweeps, or GPU/ANN acceleration.

## Repo-Free Context Pack

Use this section when handing context to a research model that cannot inspect
files directly. It deliberately repeats the most important branch facts in a
standalone form.

### Product Goal

TradingBotSuite research is intended to discover and validate crypto perpetual
strategy candidates, not to produce live orders. Its job is to answer:

- Which entry families have evidence across market regimes?
- Which feature sets add signal rather than noise?
- Which filters improve entries instead of randomly blocking trades?
- Which exit policies improve risk-adjusted results for the same entries?
- Which candidates remain stable across symbols, windows, costs, and splits?
- Which candidates are false positives created by oversearching?

The branch currently has enough infrastructure to run long discovery jobs, but
the latest results should be read as a discovery-screen artifact, not as proof
of a deployable strategy.

### Development Layer Map

| Layer | What exists | Main remaining issue |
| --- | --- | --- |
| Data intake | Binance REST, Binance Vision/public archive support, local manifests, Crypto Lake free-sample fallback, fixture builders. | Need broader multi-window/multi-symbol fixture coverage and stronger orderflow/depth ingestion. |
| Provenance | Fixture manifests with hashes, source metadata, optional-family evidence, research-only flags. | Latest-window diagnostic data must not be treated as durable validation. |
| Features | Completed-bar feature builder, registered feature sets, context joins, interval-aware rolling windows, feature cache identity. | Need broader feature families and explicit feature-set stability testing. |
| Regimes | Split-safe Gaussian mixture regime materialization with posterior/no-trade columns. | Current naming says HMM in places, but implementation is GMM-style clustering, not true temporal HMM. |
| KNN discovery | Regime-local KNN predictions, distance metrics, k/min-neighbor/threshold sweeps, side-adjusted expectancy. | Needs true no-regime baseline, independent-event scoring, and cached neighbor-matrix sweeps. |
| Entry filters | Perp/filter ablation helper exists. | Need matched filter-on/filter-off experiments for HVP, volatility, ATR, ER/chop, funding/OI, basis, orderflow, and liquidation. |
| Exits | Exit policies and discovery exit lab helper exist. | Exit lab is not mandatory in deep discovery acceptance. |
| Backtesting | Reference and vector fixed-hold engines, costs/funding/stress evidence, lower-timeframe triple-barrier support. | Discovery candidates still need mandatory downstream backtest/exit validation before candidate-pack eligibility. |
| Optimization | Search space, cache, stability, candidate gates, overfit diagnostics. | Latest discovery search is still random sparse sampling from a huge grid. |
| Artifacts | Manifests, ledgers, snapshots, run state, candidate-pack bridge, tamper checks. | Need stronger discovery acceptance semantics before bridge eligibility. |
| UI | Operator Research tab can launch/resume/summarize discovery and historical jobs. | UI should make "screen result vs validated candidate" visibly clear. |
| Live boundary | Research commands and artifacts are rejected by live paths. | Preserve this boundary; do not weaken it for convenience. |

### Current Discovery Engine Semantics

The deep discovery job creates a trial from a sampled parameter combination:

1. Select a feature-column set.
2. Build directional future-close labels for a horizon such as `1h`, `4h`, or
   `72h`.
3. Build purged/embargoed walk-forward splits.
4. Materialize split-safe regimes using a Gaussian mixture model fitted only on
   training rows.
5. Run KNN over training rows that are safe relative to validation source rows
   and label horizon.
6. Accept rows if probability, expected value, neighbor agreement, distance
   quality, vote margin, and minimum neighbor count pass thresholds.
7. Score the candidate from accepted-row realized expectancy, trade count,
   neighbor quality, and vote margin.
8. Persist interesting or blocked trial records, ledgers, optional artifacts,
   and snapshots.

Strong parts:

- Training/validation split safety is explicitly guarded.
- Label leakage from train labels into validation rows has a safety rule.
- Completed trials are immutable and resume-safe.
- Long runs snapshot and can resume.
- Artifacts preserve research-only/live-boundary metadata.
- Short-side expectancy was fixed in R92.

Weak parts:

- Signal acceptance is still bar-level, not independent-position-level.
- The run can overcount many overlapping `72h` events.
- Dense signal rate is rewarded rather than penalized.
- GMM gating is not compared to true no-regime behavior.
- Exit family performance is not a hard part of discovery acceptance.
- Orderflow and liquidation evidence are not mature.

### Latest Run Interpretation For Researchers

The latest deep run should be summarized as:

```text
The V4 discovery engine completed a 5000-trial sparse random search on a
latest-month BTCUSDT 15m context fixture. It produced many interesting rows, but
top candidates were high-density, mostly-long 72h KNN filters near the allowed
signal-rate ceiling. This is useful evidence that the discovery pipeline works
and can find candidate-like patterns, but it is not yet strong evidence of a
robust alpha. The next research stage must determine whether these candidates
survive no-regime baselines, independent event accounting, filter ablation,
exit-family comparison, multi-window validation, and stronger multiple-testing
controls.
```

### Candidate Interpretation Rules

When reading discovery rows:

- `interesting` means the row passed current discovery floors. It does not mean
  profitable after realistic exits and validation.
- `blocked` means a trial ran or preflighted and failed one of the current
  discovery floors.
- `filter_blockers` being zero does not mean filters are good. It means no row
  was classified into that specific ledger.
- High `trade_count` with high `signal_rate` is suspicious unless converted to
  independent executable events.
- High expectancy on a short latest-month window can be a market-regime artifact.
- A mostly-long candidate on a rising BTC window is not proof of predictive KNN
  skill.
- A feature set blocked for insufficient finite columns was not tested.

### Current Search Axes

The current deep config samples across:

- Feature column sets:
  - price/trend/vol baseline
  - compact WT3D comparator
  - alternative non-WT price-state features
  - perp context smoke features
  - liquidation context smoke features
- Regime state counts: 3, 4, 5, 6
- Regime posterior thresholds
- Regime entropy thresholds
- Label horizons: 1h, 2h, 4h, 8h, 12h, 24h, 72h
- K values: 3, 5, 8, 13, 21, 34
- Minimum neighbor counts
- Distance metrics: Euclidean, Manhattan, cosine
- Probability thresholds
- Expected value thresholds
- Neighbor agreement thresholds
- Distance-quality thresholds
- Vote-margin thresholds
- Same-regime-only flag

Missing or incomplete axes:

- True no-regime/no-gate baseline.
- True HMM backend.
- Feature lookback/window-length optimization.
- WT/WT3D parameter variants.
- HVP/ATR/ER/chop filter toggles.
- AggTrade orderflow feature toggles.
- Real order book depth imbalance.
- Exit family as a mandatory acceptance axis.
- Multi-symbol and multi-window validation.
- Explicit multiple-comparison-adjusted acceptance.

## Research Questions To Answer Next

The next stage should be organized around questions, not just implementation.

### Regime Questions

- Does any regime layer improve results compared with no regime at all?
- Does GMM no-trade gating help or just block valid trades?
- Does same-regime neighbor restriction improve expectancy after independent
  event accounting?
- Are regime labels stable across adjacent windows and different symbols?
- Would a true temporal HMM add value beyond GMM clustering, or would it add
  complexity without evidence?

Required comparison:

```text
same feature set
same label horizon
same KNN thresholds
same exit policy
same validation windows

compare:
  no_regime
  gmm_no_trade_gate_only
  gmm_same_regime_neighbors
  true_hmm_gate_only, if implemented
  true_hmm_same_regime_neighbors, if implemented
```

### KNN Questions

- Does KNN add predictive value after transaction costs, funding, and realistic
  exit behavior?
- Are best settings stable around nearby `k`, threshold, distance, and feature
  variants?
- Is performance coming from neighbor agreement or simply from trend exposure?
- Does KNN improve against transparent comparator strategies and no-trade?
- Does the result survive side-separated long/short evidence?

Do not accept KNN because one sparse random trial had a high score. Require
stability clusters and independent validation.

### Feature Questions

- Which compact feature families work without WT/WT3D?
- Do WT/WT3D features improve over price/trend/vol comparators after matched
  controls?
- Are perp context features signal, filters, or noise?
- Are volatility and efficiency features better as KNN dimensions or as hard
  filters?
- Which feature sets remain stable over multiple market windows?

Suggested feature families:

- Price/trend/vol:
  - returns
  - slope
  - efficiency ratio
  - realized volatility
  - ATR percentile
  - choppiness/range width
- WT/WT3D optional:
  - WT normalized value
  - WT slope
  - WT3D normal/slope/spread
  - MTF agreement only after bounded predeclared ranges
- Non-WT alternatives:
  - path z-score
  - directional DI spread
  - Hurst proxy
  - volatility shock
  - autocorrelation
  - entropy
- Perp:
  - funding rate
  - funding change
  - basis/premium
  - open-interest change
  - OI z-score
- Orderflow:
  - taker buy/sell imbalance
  - CVD slope
  - trade intensity
  - large trade burst
  - sweep proxy
  - realized spread proxy if data supports it
- Liquidation:
  - event count
  - notional z-score
  - side imbalance
  - reclaim/absorption only if provider-backed and finite

### Filter Questions

- Does a filter reduce bad trades or merely reduce sample size?
- Does a filter improve expectancy after cost without pushing trade count below
  evidence floors?
- Does the same filter work for long and short sides?
- Is a filter stable across regimes, horizons, and symbols?
- Is a filter better as a KNN feature or as a separate entry gate?

### Exit Questions

- Does the edge need a time hold, volatility barrier, trailing stop, funding/OI
  exit, or regime/alpha decay exit?
- Do exits improve risk-adjusted results without cherry-picking per candidate?
- Are exits robust across cost and funding stress?
- Does a candidate only look good because `72h` future-close labels are favorable?

## Proposed Experiment Matrices

### Regime Matrix

| Axis | Values |
| --- | --- |
| Regime mode | `none`, `gmm_gate_only`, `gmm_same_regime_neighbors`, future `true_hmm_gate_only`, future `true_hmm_same_regime_neighbors` |
| State count | 3, 4, 5, 6, optionally 2 for baseline simplicity |
| Posterior threshold | conservative bounded set, not too many values |
| Entropy threshold | conservative bounded set |
| Recent flip cooldown | off, short, medium |
| Validation | identical splits and feature sets for every mode |

Output required:

- Candidate score by regime mode.
- Trade count and independent trade count by regime mode.
- Side-separated expectancy.
- Regime occupancy and no-trade rate.
- Regime transition/flip diagnostics.
- Failure reason if regime mode suppresses too much sample.

### KNN Matrix

| Axis | Values |
| --- | --- |
| k | 3, 5, 8, 13, 21, 34 |
| Distance | Manhattan, Euclidean, cosine |
| Weighting | uniform first, optional distance-weighted later |
| Neighbor pool | all-safe, same-regime, same-side analog diagnostics |
| Probability threshold | bounded coarse grid |
| Expected value threshold | bounded around zero and realistic cost floor |
| Vote margin | coarse grid |
| Minimum distance quality | off, weak, moderate |

Output required:

- Stability around nearby `k`.
- Stability around thresholds.
- Neighbor distance diagnostics.
- Neighbor label distribution.
- Feature-space missingness and scaler evidence.
- Side-separated behavior.

### Feature Matrix

| Family | Purpose | Comparator |
| --- | --- | --- |
| price_trend_vol | no-WT baseline | no-trade, transparent trend/vol |
| compact_wt3d | optional WT comparator | price_trend_vol |
| alternative_non_wt_price_state | non-WT alternative | price_trend_vol |
| perp_context | funding/OI/basis addition | same price features without perp |
| aggtrade_orderflow | public archive orderflow proxy | same price/perp features without orderflow |
| liquidation_context | liquidation proxy | same features without liquidation |

Output required:

- Matched score delta vs comparator.
- Missingness and finite-column preflight.
- Stability by symbol/window.
- Whether feature works as KNN dimension, hard filter, or separate strategy.

### Filter Matrix

| Filter | Values | Required comparator |
| --- | --- | --- |
| HVP / realized volatility percentile | off, low-vol only, high-vol only, mid-vol only | identical entry with no filter |
| ATR percentile | off, low/mid/high bucket | identical entry with no filter |
| Efficiency/chop | trend-only, chop-only, off | identical entry with no filter |
| Funding | avoid adverse funding, fade crowding, off | no funding filter |
| OI | require OI expansion, avoid OI contraction, off | no OI filter |
| Basis/premium | convergence/fade buckets, off | no basis filter |
| AggTrade imbalance | buy/sell pressure buckets, off | no orderflow filter |
| Liquidation | absorption/reclaim buckets, off | no liquidation filter |

Output required:

- Matched delta after costs.
- Sample retained percentage.
- Independent trade count.
- Side/regime/horizon breakdown.
- Failure reason when filter only reduces trades.

### Exit Matrix

| Exit family | Examples | Notes |
| --- | --- | --- |
| Fixed hold | 1h, 4h, 12h, 24h, 72h | Baseline, not proof of optimality. |
| Triple barrier | fixed TP/SL plus vertical barrier | Needs lower-timeframe sequence proof when available. |
| ATR barrier | ATR-scaled TP/SL | Compare by volatility regime. |
| Volatility-scaled barrier | realized-vol scaled thresholds | Avoid overfitting too many barrier values. |
| Trailing/risk | trailing ATR after profit, max MAE stop | Useful only after enough trade density. |
| Funding/OI | funding adverse exit, OI contraction exit | Requires finite context. |
| Regime/alpha | regime flip exit, alpha decay exit | Requires trustworthy regime/KNN diagnostics. |

Output required:

- Exit-family winner per entry group.
- Trade count retained.
- Profit factor, expectancy, drawdown, win/loss distribution.
- Cost/funding stress survival.
- Side-separated and split-separated metrics.

### Validation Matrix

| Axis | Recommendation |
| --- | --- |
| Symbol | BTCUSDT and ETHUSDT first; add more only after infrastructure is stable. |
| Time windows | latest month for smoke only; add multiple non-overlapping historical windows. |
| Market regimes | bull trend, bear trend, chop, volatility shock, funding extremes. |
| Splits | anchored and rolling walk-forward; purged/embargoed when labels overlap. |
| Costs | baseline, higher taker/slippage, funding stress. |
| Survivorship | candidate must survive at least one strict OOS validation not used for search. |

## Metrics And Gates

The next stage should separate discovery scoring from validation acceptance.

### Discovery Metrics

- accepted bar count
- independent event count
- signal rate
- side counts and side balance
- neighbor agreement
- vote margin
- distance quality
- expected value before and after estimated costs
- realized label expectancy
- no-trade/filter block rates
- feature missingness
- regime occupancy
- split coverage

### Validation Metrics

- net expectancy after fees/slippage/funding
- profit factor
- max drawdown
- drawdown duration
- Sharpe/Sortino with caution due non-normal returns
- hit rate and payoff ratio
- average win/loss
- tail loss / CVaR proxy
- turnover
- exposure time
- side-separated PnL
- split-separated PnL
- cost-stress survival
- funding-stress survival
- feature/regime/filter/exit ablation deltas

### Suggested Acceptance Gates

A discovery candidate may move to deeper historical-cycle validation only if:

- It has enough independent executable events per split.
- Signal rate is not near the ceiling unless explicitly justified.
- Long and short sides are reported separately.
- It beats no-trade and transparent baseline comparators.
- Its feature set beats required no-WT/no-perp/no-filter comparators where
  relevant.
- Its regime mode beats true no-regime or is clearly marked as non-beneficial.
- Its exit family beats fixed hold or remains explicitly pending, not assumed.
- It survives cost/funding stress.
- It has stable neighboring parameter settings.
- It has multi-window evidence, or is marked latest-window-only/diagnostic.
- It has complete artifact provenance and no live/promotion flags.

A candidate must not move to candidate-pack eligibility if:

- It relies only on latest-month fixture evidence.
- It is mostly a one-side market drift capture without comparator dominance.
- It has high overlapping signal density and low independent trade count.
- It lacks exit-family evidence.
- It depends on missing or non-finite feature columns.
- It is selected from a large search without overfit/multiple-testing controls.

## Compute And Runtime Plan

The current run shape is correct enough for safety, but not efficient enough for
large research.

### Current Bottlenecks

- Per-trial KNN distance work repeats similar computations.
- `ThreadPoolExecutor` helps only partly because many operations are Python or
  pandas-heavy.
- Artifact writes are serial at batch/snapshot boundaries.
- HMM/GMM and label caches help, but threshold/k sweeps still recompute too
  much.
- No durable CPU/memory/IO telemetry exists for a run.

### Near-Term Compute Improvements

1. Precompute split-safe feature matrices once per feature set and split.
2. Precompute neighbor order/stat arrays once per:
   - feature set
   - label horizon
   - split
   - regime mode
   - distance metric
3. Sweep `k`, probability thresholds, expected value thresholds, vote margins,
   and distance-quality thresholds over cached arrays.
4. Persist compact candidate summaries first; persist full KNN artifacts only
   for shortlisted candidates.
5. Add telemetry:
   - wall time by stage
   - CPU percent
   - memory peak
   - worker count
   - trials/minute
   - cache hit rate
   - artifact write time
   - bytes written
6. Use process pools for CPU-bound blocks after deterministic parity tests.
7. Control BLAS/threadpool oversubscription before raising worker count.

### Later Compute Options

- Approximate nearest neighbors for very large windows, only with exact-KNN
  parity and recall diagnostics.
- GPU acceleration for batched distances if data grows enough to justify it.
- Columnar/NumPy-first trial sweeps instead of pandas-heavy inner loops.
- Incremental artifact compaction to reduce many small files.

## Statistical Safeguards

The next stage must treat the search as multiple testing.

Required safeguards:

- Declare the tested search space in artifacts.
- Report sampled fraction and effective trial count.
- Keep all attempted trials, not just winners.
- Use out-of-sample windows not used for tuning.
- Use purging/embargo where labels overlap.
- Prefer stability plateaus over isolated peaks.
- Report deflated/adjusted performance where feasible.
- Reject candidates that only work in one narrow window or one side.
- Require economic rationale for features and filters.

Practical rule: if a candidate is found from a huge search and only survives one
short latest-window dataset, it is a lead, not evidence.

## Documentation And UI Requirements

The operator UI and docs should consistently distinguish:

- smoke run
- discovery screen
- historical-cycle validation
- candidate-pack eligible artifact
- paper/shadow/testnet/live, which are outside this branch's current approval
  scope

Recommended UI additions:

- "Screen result, not validated" badge for discovery candidates.
- Signal density warning when signal rate is near ceiling.
- Latest-window-only warning for diagnostic fixtures.
- Side imbalance warning for mostly-long/mostly-short candidates.
- Exit evidence missing warning.
- Regime baseline missing warning.
- Orderflow/liquidation not tested warning when feature preflight blocks data.

## Recommended Next Stage

Open a new stage after R92 focused on truthfulness and compute efficiency:

```text
Stage R93: Discovery Truthfulness And Compute Upgrade
```

Recommended packets:

1. `WPR93-01-discovery-audit-docs`
   - Preserve this handoff.
   - Add explicit UI/docs language that latest discovery candidates are screen
     results, not strategy validation.

2. `WPR93-02-regime-baseline-ablation`
   - Add explicit regime mode axis:
     - `none`
     - `gmm_gate_only`
     - `gmm_same_regime_neighbors`
     - optional future `true_hmm_gate_only`
     - optional future `true_hmm_same_regime_neighbors`
   - Rename artifact fields or add metadata so current GMM is not overstated
     as true HMM.
   - Compare no-regime vs GMM/no-trade vs same-regime on identical feature,
     horizon, threshold, and exit settings.

3. `WPR93-03-independent-event-and-score-hardening`
   - Add non-overlap spacing for accepted entries.
   - Penalize signal rates near the ceiling.
   - Add side balance, turnover, drawdown, cost survival, and independent-event
     count to score.
   - Separate discovery score from validation score.

4. `WPR93-04-filter-ablation-matrix-v2`
   - Implement proper filter treatments:
     - no filter
     - HVP/realized-volatility percentile
     - ATR percentile
     - ER/choppiness
     - funding/OI/basis
     - aggregate-trade imbalance
     - liquidation if finite provider-backed data exists
   - Compare filters only inside matched entry/exit groups.

5. `WPR93-05-orderflow-feature-foundation`
   - Start with Binance Vision/public `aggTrades` features:
     - taker buy/sell imbalance
     - CVD slope
     - trade intensity
     - large trade burst proxy
     - sweep proxy
     - volume shock vs rolling baseline
   - Keep real order book imbalance as a separate provider-stage task requiring
     snapshots plus depth updates or an archived depth provider.

6. `WPR93-06-exit-lab-mandatory-gate`
   - Require candidate discovery rows to pass exit-family comparison before
     candidate-pack bridge eligibility.
   - Compare fixed hold, triple barrier, ATR barrier, volatility-scaled barrier,
     trailing ATR after profit, regime-flip exit, alpha-decay exit, funding/OI
     exits, and time stops.

7. `WPR93-07-compute-engine-upgrade`
   - Precompute train-only neighbor matrices per feature set, split, regime mode,
     distance metric, and horizon.
   - Sweep thresholds/k values over cached neighbor stats instead of recomputing
     distances per trial.
   - Use process parallelism for CPU-bound Python sections.
   - Tune BLAS/threadpool limits to avoid oversubscription.
   - Add runtime telemetry: workers active, CPU percent, memory, trials/minute,
     cache hits, artifact write time, and per-stage timing.
   - Consider approximate nearest neighbor indexing only after deterministic
     exact-KNN parity tests exist.

8. `WPR93-08-multi-window-validation-fixtures`
   - Move beyond latest-month BTCUSDT.
   - Add BTCUSDT and ETHUSDT multi-month/multi-regime fixtures.
   - Keep source provenance explicit and fail closed when data is diagnostic or
     latest-window only.

## Practical Research Priorities

Highest value first:

1. Fix the regime/no-regime comparison.
2. Fix dense-signal scoring and overlapping event inflation.
3. Make exit lab mandatory.
4. Add clean filter ablations.
5. Add aggTrade-based orderflow features.
6. Improve compute by reusing neighbor matrices and adding telemetry.
7. Only then expand to true HMM, GPU, or approximate nearest neighbors.

## Unsafe To Rewrite Casually

Do not casually rewrite:

- `src/tradingbotsuite/research_cycle/runner.py`
- `src/tradingbotsuite/backtesting/engine.py`
- `src/tradingbotsuite/backtesting/splits.py`
- `src/tradingbotsuite/backtesting/exits.py`
- `src/tradingbotsuite/features/builders.py`
- `src/tradingbotsuite/features/cache.py`
- `src/tradingbotsuite/data/historical_fixture_pack.py`
- `src/tradingbotsuite/research_artifacts/candidate_pack.py`
- `src/tradingbotsuite/research_discovery/runner.py`
- `src/tradingbotsuite/research_discovery/knn_study.py`
- `src/tradingbotsuite/research_discovery/hmm_materialization.py`
- live/promotion guard files

If one of these must change, write a work packet, add focused regression tests,
and run the contract baseline.

## Validation Baseline

Minimum focused checks for next code work:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
git diff --check
```

Broaden to historical/backtesting/optimization tests when touching shared
research-cycle, feature, exit, or optimizer contracts.

## External References To Recheck

- scikit-learn Nearest Neighbors:
  `https://scikit-learn.org/stable/modules/neighbors.html`
- scikit-learn GaussianMixture:
  `https://scikit-learn.org/stable/modules/generated/sklearn.mixture.GaussianMixture.html`
- hmmlearn HMM tutorial:
  `https://hmmlearn.readthedocs.io/en/0.3.3/tutorial.html`
- Cont, Kukanov, Stoikov order-flow imbalance paper:
  `https://ideas.repec.org/p/arx/papers/1011.6402.html`
- Bailey and Lopez de Prado on backtest overfitting:
  `https://academic.oup.com/jrssig/article/18/6/22/7038278`
- Binance public data:
  `https://github.com/binance/binance-public-data`
- Binance local order book tutorials:
  `https://academy.binance.com/ka-GE/articles/local-order-book-tutorial-part-1-depth-stream-and-event-buffering`

## Ready Prompt For External Research Model Without Repo Access

Use this prompt for a stronger research model that cannot read this repository
directly. Its output should be a research plan or critique that an implementation
agent can later translate into code.

```text
You are a senior quantitative research, market microstructure, and ML systems
reviewer. You do not have direct access to the repository or artifacts, so work
only from the structured context below. Your job is to produce a rigorous,
practical next-stage research plan for a crypto perpetual strategy discovery
system. Do not assume live trading. Do not produce code. Produce a research and
implementation design that can be handed to engineering agents.

System identity:
- Project: TradingBotSuite research branch.
- Market: crypto perpetual futures, primarily BTCUSDT and ETHUSDT.
- Current branch role: research and experimentation only.
- Live trading status: not live, not promotion-ready.
- Required artifact flags: research_only=true, observe_only=true,
  promotion_ready=false.
- Research target: discover, falsify, and validate candidate entry/filter/exit
  combinations before any later paper/shadow/testnet process.

Current architecture:
- Data intake:
  - Binance REST collectors.
  - Binance Vision/public archive support.
  - Local manifests.
  - Crypto Lake free-sample fallback for diagnostic/latest-window data.
  - Hyperliquid/archive surfaces exist but research outputs remain separate
    from live execution.
- Fixture layer:
  - Historical fixture packs validate source provenance, hashes, row counts,
    interval metadata, optional context families, missingness, research-only
    flags, and source limitations.
  - Latest-window data must be treated as diagnostic unless broader coverage is
    added.
- Feature layer:
  - Completed-bar point-in-time feature construction.
  - Feature registry and preset manifests.
  - Optional context joins for funding, premium/basis, open interest, aggregate
    trades, liquidation context where available.
  - Feature cache identity includes data/source/context/interval/build identity.
- Strategy layer:
  - Baselines and transparent comparators.
  - Perp context strategies.
  - Funding/OI/timing strategies.
  - HMM/KNN local analog filter strategy.
  - Liquidation absorption strategy.
  - No-trade comparator.
- Backtest layer:
  - Reference execution engine.
  - Vector fixed-holding backend.
  - Fixed holding windows.
  - Lower-timeframe triple-barrier support.
  - ATR/volatility/trailing/regime/funding exits exist or are represented.
  - Cost, funding, and stress evidence.
- Optimizer/gate layer:
  - Candidate identity.
  - Search spaces.
  - Caching.
  - Region-of-stability diagnostics.
  - Overfit/stability checks.
  - Candidate-pack gates.
- Discovery V4:
  - Resume-safe long-run manager.
  - Atomic snapshots.
  - Immutable trial records.
  - Interesting/blocked/filter-blocker ledgers.
  - Split-safe regime materialization.
  - KNN study engine.
  - Feature-column-set manifest.
  - Perp/filter ablation helper.
  - Discovery exit-lab helper.
  - Candidate-pack bridge.
  - Operator UI can launch/resume/summarize discovery runs.

Latest audited deep discovery run:
- Symbol/timeframe: BTCUSDT 15m.
- Dataset: latest-month context fixture.
- Rows: 2873.
- Run completed: 5000/5000 trials.
- Runtime: about 2h 26m.
- Interesting candidates: 2714.
- Blocked candidates: 2286.
- Filter blockers: 0.
- Candidate pack written: false.
- Live/order placement flags: false.
- Search space total combinations: 887,040,000.
- Sampled fraction: about 0.00056%.
- Top score candidate:
  - candidate id: deep_candidate_harvest_btcusdt_v4-hmm-knn-319db9eb017c8f43
  - feature set: price_trend_vol
  - horizon: 72h
  - distance metric: cosine
  - k: 5
  - min_neighbor_count: 5
  - same_regime_only: false
  - signal_rate: 0.4479638009, very close to max ceiling 0.45
  - trade_count: 1287
  - realized_expectancy: 0.0131831229
  - side counts in strategy accounting: 1339 long, 54 short
- Top expectancy candidates:
  - mostly alternative_non_wt_price_state
  - mostly 72h horizon
  - mostly all-regime KNN
  - scored lower than dense candidates because final_score rewards trade count.
- Liquidation feature set:
  - did not meaningfully run.
  - blocked by insufficient finite variant columns.

Current discovery trial semantics:
1. Select feature-column set.
2. Create directional future-close labels for horizons such as 1h, 4h, 72h.
3. Build purged/embargoed walk-forward splits.
4. Materialize regimes split-safely using sklearn GaussianMixture fitted only on
   training rows.
5. Run KNN over label-safe training rows for validation rows.
6. Accept rows based on probability, expected value, neighbor agreement,
   distance quality, vote margin, and minimum neighbor count.
7. Score candidate:
   final_score =
     realized_expectancy
     + 0.05 * log1p(trade_count)
     + 0.01 * avg_neighbor_quality
     + 0.01 * avg_vote_margin
8. Persist trial record, ledgers, optional HMM/KNN/accounting artifacts, and
   snapshots.

Critical concerns:
1. Current "HMM" is actually GaussianMixture regime clustering, not a true
   temporal Hidden Markov Model with transition probabilities.
2. same_regime_only=false is not a clean no-regime/no-HMM baseline, because
   regime_no_trade still gates rows.
3. Top candidates are close to the signal-rate ceiling and mostly long, so they
   may be broad market exposure rather than KNN edge.
4. The score heavily rewards trade density via log1p(trade_count), so dense
   candidates can outrank more selective higher-expectancy candidates.
5. 72h labels on 15m bars create overlapping events; bar-level trade_count may
   overstate independent executable trades.
6. Latest-month BTCUSDT evidence is not enough for robust strategy claims.
7. Filter ideas such as HVP, realized volatility, ATR percentile, efficiency
   ratio, choppiness, funding, OI, basis, liquidation, and orderflow have not
   been tested as matched filter-on/filter-off ablations.
8. Orderflow is not yet meaningfully represented. Binance public archives can
   support aggregate-trade-derived features first. True order book imbalance
   needs depth snapshots plus diff-depth streams or an archived depth provider.
9. Exit policies exist, but exit-family comparison is not yet mandatory before
   candidate acceptance.
10. Compute is underused:
   - max_workers=8 ThreadPoolExecutor
   - repeated per-trial distance work
   - serial artifact writes
   - no CPU/memory/cache/runtime telemetry
   - no vectorized threshold sweeps
   - no process/GPU/ANN acceleration yet

Your task:
Produce a rigorous next-stage research plan. Make it concrete enough for an
engineering agent to implement, but do not write code. Be critical. Assume that
many apparent candidates may be false positives until proven otherwise.

Address these research questions:
1. Regime detection:
   - How should no-regime, GMM gate, GMM same-regime neighbors, and true HMM
     variants be compared?
   - What would prove that regime detection helps rather than randomly blocks
     entries?
   - Should a true HMM be implemented now, later, or only after GMM/no-regime
     evidence is clear?
2. KNN faithfulness:
   - Is current KNN testing enough to evaluate neighbor count, k, distance,
     thresholds, and feature sets?
   - How should neighbor matrices and threshold sweeps be structured?
   - How should KNN be compared against simple transparent baselines?
3. Feature-set search:
   - How should WT/WT3D, non-WT, price/trend/vol, perp context, orderflow, and
     liquidation feature families be tested?
   - How should feature-set stability be measured?
   - What feature combinations should be excluded to avoid blind brute force?
4. Filters:
   - Design matched ablations for HVP/realized volatility, ATR percentile,
     efficiency/chop, funding/OI, basis/premium, aggregate-trade orderflow, and
     liquidation.
   - Define how to tell whether a filter improves edge or merely reduces sample
     size.
5. Exits:
   - Design mandatory exit-family testing:
     fixed hold, triple barrier, ATR barrier, volatility-scaled barrier,
     trailing/risk exits, funding/OI exits, regime flip, alpha decay.
   - Define when an entry candidate is allowed to proceed without a winning exit
     family.
6. Event independence:
   - Redesign scoring for overlapping long-horizon labels.
   - Define independent event counting and non-overlap spacing.
   - Explain how to avoid counting many correlated 72h labels as separate
     trades.
7. Metrics and gates:
   - Propose discovery metrics, validation metrics, and acceptance gates.
   - Include side-separated, split-separated, regime-separated, cost/funding
     stress, drawdown, turnover, and sample-size requirements.
8. Data:
   - Propose multi-window BTCUSDT/ETHUSDT validation.
   - Explain latest-window vs durable evidence.
   - Propose an orderflow roadmap starting with Binance aggTrades and later
     order book depth.
9. Compute:
   - Propose how to use precomputed neighbor matrices, vectorized threshold
     sweeps, multiprocessing, telemetry, and later ANN/GPU options.
   - Explain what telemetry should be added to understand resource utilization.
10. Statistical safeguards:
   - Address multiple testing, backtest overfitting, false discoveries,
     stability plateaus, purging/embargo, and true out-of-sample validation.

Required output format:
1. Executive diagnosis.
2. Prioritized stage plan with work packets.
3. Experiment matrices for regimes, KNN, features, filters, exits, validation.
4. Metrics and acceptance gates.
5. Compute optimization plan.
6. Data roadmap.
7. Risks and likely false-positive modes.
8. "Do not do" list.
9. Minimal implementation order for the next engineering agent.

Constraints:
- Do not recommend live trading.
- Do not recommend candidate promotion from latest-month evidence.
- Do not overstate GaussianMixture as HMM.
- Do not accept high signal-rate candidates without independent-event analysis.
- Do not treat missing liquidation/orderflow data as tested.
- Do not propose brute-forcing the full 887M search grid.
- Prefer bounded, interpretable, staged experiments with clear falsification
  criteria.
```

## Ready Prompt For Repo-Access Implementation Agent

Use this prompt only for an implementation agent that can inspect and edit the
repository.

```text
You are continuing work in C:\Users\papaa\Music\tradingbotsuite on branch
research/v3-experimental-engine.

Read first:
1. AGENTS.md
2. docs/ORCHESTRATOR_STAGE_LEDGER.md
3. docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md
4. docs/RESEARCH_BRANCH_AUDIT_AND_NEXT_STAGE_HANDOFF.md
5. docs/stage_reports/STAGE_R92_FINAL_BRANCH_CROSSCHECK_REPORT.md

Task:
Implement the next post-R92 research stage. Preserve branch governance and
research-only boundaries. The target is discovery truthfulness and compute
efficiency, not live strategy deployment.

Start with work packets. Do not change broad shared packages without a packet
and focused tests. Prioritize:
1. Explicit regime baseline modes:
   - no_regime
   - gmm_gate_only
   - gmm_same_regime_neighbors
   - future true_hmm variants only if scoped and justified
2. Independent-event scoring and signal-rate penalty.
3. Mandatory exit-lab gate before candidate-pack bridge eligibility.
4. Matched filter ablation v2.
5. AggTrade orderflow feature foundation.
6. Cached neighbor-matrix/threshold-sweep compute upgrade.
7. Runtime telemetry.
8. Multi-window BTCUSDT/ETHUSDT fixtures.

Keep current guardrails:
- research_only=true
- observe_only=true
- promotion_ready=false
- no live adapter imports in research modules
- no order placement
- no live config writes
- no candidate promotion from latest-window evidence

Minimum validation:
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
git diff --check

Broaden validation when touching backtesting, exits, feature cache, fixture
provenance, optimization, candidate-pack gates, or operator UI.
```
