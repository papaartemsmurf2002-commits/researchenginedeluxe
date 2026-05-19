# Stage R104 Exit Entry Orderflow Research Handoff

Date: 2026-05-19
Owner: Codex Research Agent
Stage: R104 candidate validation on durable evidence
Status: research-only handoff; no candidate-ready claim

## Research Boundary

This document is a research and evaluation handoff. It does not promote a
candidate, write live configuration, place orders, change runtime mode, or make
a profitability claim. Every recommendation below stays `research_only`,
`observe_only`, and `promotion_ready: false` until a later promotion process
with reproducible evidence changes that state.

The branch is not empirically finished. The completed exact BTCUSDT durable
sweep proved the engine can run a large bounded search to completion, but it
did not produce a screen-worthy lead. The next useful phase is not another
coupled brute-force sweep. It is a falsification pass that isolates entries,
exits, orderflow, KNN/regime filters, and feature families so weak components
are removed early and useful components are measured independently.

## Latest Completed Run

Run path:

```text
data/research/operator_runs/discovery_runs/exact-entry-sweep-btcusdt-durable-r104-v1/run-discovery-142f3b61b761470b8aeb105967dd9c47
```

Core run evidence:

| Field | Value |
| --- | --- |
| Run id | `exact_entry_sweep_btcusdt_durable_r104_v1` |
| Symbol/timeframe | `BTCUSDT` / `15m` |
| Discovery mode | `deep_candidate_harvest` |
| State | `completed` |
| Completion time | `2026-05-19T02:49:18.756830Z` |
| Completed trials | `570240 / 570240` |
| Failed trials | `0` |
| Interesting candidates | `0` |
| Blocked candidates | `570240` |
| Filter blockers | `0` |
| Candidate pack written | `false` |
| Manifest scope | `real_discovery_ledgers_no_pack_gate` |
| Research boundary | `research_only: true`, `observe_only: true`, `promotion_ready: false` |

Search-space evidence:

| Dimension | Value |
| --- | --- |
| Coverage | Exhaustive, sampled fraction `1.0` |
| Total combinations | `570240` |
| Feature column sets | `price_trend_vol`, `compact_wt3d_base` |
| Label horizons | `1h`, `2h`, `4h` |
| Distance metrics | `euclidean`, `manhattan`, `cosine` |
| K values | `3`, `5`, `8`, `13`, `21`, `34` |
| Min neighbor counts | `2`, `3`, `4`, `5` |
| Probability thresholds | `0.48`, `0.50`, `0.52`, `0.55`, `0.58`, `0.62` |
| Vote margin thresholds | `0.00`, `0.02`, `0.03`, `0.05` |
| Min neighbor agreement | `0.48`, `0.50`, `0.52`, `0.55`, `0.60` |
| Expected value thresholds | `-0.0004`, `-0.0002`, `0.0`, `0.0002` |
| Regime mode | `none` |
| True HMM backend | Not used |

Data evidence:

| Field | Value |
| --- | --- |
| Fixture | `btcusdt-public-archive-multi-window-v1` |
| Primary rows | `32` |
| Lower-timeframe rows | `480` |
| Source type | `historical_fixture_pack` |
| Manifest sha256 | `c58a44a0a40a942a70f0202b5dc5e3c094139651c148a8b14f00475a1cd54983` |

The compact fixture is valid for screening and path verification. It is still
too small for candidate-ready claims. `ISSUE-R104-001` remains the active
blocker for expanded durable primary-bar evidence.

Blocker distribution:

| Blocker | Rows | Share |
| --- | ---: | ---: |
| `overlap_ratio_above_ceiling` | `222720` | `39.1%` |
| `independent_event_count_below_floor` | `194976` | `34.2%` |
| `signal_rate_near_ceiling` | `86304` | `15.1%` |
| `signal_rate_above_discovery_ceiling` | `60480` | `10.6%` |
| `realized_expectancy_below_discovery_floor` | `5760` | `1.0%` |

Score and event statistics from `blocked_candidates.parquet`:

| Metric | Min | Median | P95 | Max |
| --- | ---: | ---: | ---: | ---: |
| Score | `-0.240216` | `-0.047465` | `0.0` | `0.038431` |
| Realized expectancy | `-0.153586` | `-0.017128` | `0.0` | `0.012025` |
| Trade count | `0` | `1` | `5` | `5` |
| Independent event count | `0` | `1` | `5` | `5` |
| Accepted prediction count | `0` | `10` | `20` | `20` |
| Overlap ratio | `0.0` | `0.7` | `0.857143` | `0.857143` |
| Side-collapse ratio | `0.0` | `1.0` | `1.0` | `1.0` |
| Signal rate | `0.0` | `0.125` | `0.5` | `0.5625` |

The top blocked records were all `compact_wt3d_base`, `1h`, `cosine`, `k=3`,
with a score of `0.038431`, realized expectancy `0.012025`, four trades,
four independent events, overlap `0.666667`, side collapse `0.75`, and signal
rate `0.375`. They were blocked by overlap. This is not enough evidence to
promote. It is useful as a postmortem seed for entry-only and exit-only tests.

Runtime evidence:

| Field | Value |
| --- | ---: |
| Wall time | `112216.39s` |
| Trials/minute | `304.90` |
| Active workers | `48` |
| Artifact files | `570374` |
| Artifact bytes | `2195792196` |
| Neighbor cache hit rate | `0.999956` |
| Label/split cache hit rate | `0.999989` |
| GMM regime cache hits | `0`, because regime mode was `none` |

The run consumed about 31.2 hours and wrote many small files. Improving CPU
utilization alone is not the next best lever. The larger win is to reduce
effective-equivalent trial work, cache entry signals, and run exit/orderflow
ablations only after an entry family shows raw edge.

## Interpretation

The run did not fail operationally. It completed, had no failed trials, and
preserved run state, manifest, ledgers, and search-space coverage. The no-lead
result is therefore a research result:

- The current compact BTC exact sweep did not find a candidate under current
  KNN entry thresholds.
- The dominant blockers are overlapping signals, too few independent events,
  excessive signal density, and weak realized expectancy.
- The search is still too coupled. A bad exit, noisy feature family, no-op
  filter, or weak entry can mask the others.
- The exact sweep included nominal dimensions that are likely inert under
  `regime_mode: none` or collapse to the same effective behavior for many
  trials. Future brute-force runs should calculate an effective trial key and
  deduplicate before execution.
- `interesting_only` persistence reduced disk waste, but postmortem analysis
  would be stronger if the next deep run also writes a compact top-k blocked
  sample per blocker and per effective feature family.

## Existing Surfaces To Use

The branch already has most pieces required for the next phase:

- Entry discovery: `src/tradingbotsuite/research_discovery/` runs bounded
  real KNN discovery, blocker ledgers, candidate ledgers, manifests, snapshots,
  and candidate eligibility bridge evidence.
- Feature sets: `configs/discovery/feature_column_sets_v4.json` includes
  `price_trend_vol` as the no-WT baseline and `compact_wt3d_base` as the WT3D
  comparator. Other registered feature packs include perp and aggTrade flow
  contexts.
- Exit lab: `configs/discovery/discovery_exit_lab_v4.json` already compares
  fixed holding with barrier, funding/OI, GMM transition, KNN remaining-edge,
  KNN dynamic barrier, trailing risk, true-HMM deferred, and liquidity
  adverse-selection families.
- Filter ablation: `configs/discovery/filter_ablation_matrix_v5.json` already
  defines matched filter-on/filter-off comparisons for volatility, ATR,
  ER/chop, volatility shock, funding, basis/premium, and related context.
- Orderflow features: `features_aggtrade_orderflow_v1` and
  `features_price_perp_aggflow_no_wt` exist, but their metadata correctly marks
  aggTrade fields as trade-flow proxies, not true order-book imbalance or OFI.
- Fast screening: `src/tradingbotsuite/backtesting/vector_engine.py` supports
  fixed-holding primary-bar screening. Richer exits should stay reference-path
  or specialized vectorized only after parity is proven.

## Weak Points To Address

1. Coupled evaluation hides which component failed. The previous sweep tested
   KNN entry configuration on compact data, but it did not isolate whether the
   entry signal, exit logic, orderflow features, regime labels, or filters carry
   independent value.
2. Exit value-add is not yet proven. Candidate-pack gates already reject
   fixed-holding-only evidence, but there are no durable R104 leads where the
   exit lab can show a real improvement over fixed holding.
3. Entry quality is not yet separated from exit complexity. An entry family
   should first beat fixed-hold and a simple runner baseline before expensive
   context-dependent exits are tested.
4. Orderflow is not yet proven as a standalone signal, a feature addition, a
   filter, or an exit trigger. It may add signal, but it may also add noisy
   dimensions and missingness.
5. Current discovery regime evidence is no-regime or split-safe GMM-style
   context, not true HMM transition evidence. Any "HMM helped" claim must be
   blocked unless a true HMM backend is used and beats no-regime and GMM
   comparators.
6. Compact fixture size creates low independent-event ceilings. A 32-primary-bar
   fixture can find plumbing and obvious logic errors, but cannot settle a
   strategy-quality question.
7. Effective-equivalent trials are likely wasting time. A future exact search
   should collapse inactive dimensions and record `effective_trial_key` before
   scheduling work.
8. Exit grids can explode the search. Exit tests must reuse frozen entry events
   and lower-timeframe path caches instead of rerunning KNN for every exit
   setting.
9. The score gate accepts very low nominal trade-count settings in the search
   space, but event-accounting blocks most results afterward. The next pass
   should screen entries directly on independent event density before exit labs.

## Next Phase Objective

Build a component falsification matrix that answers five questions:

1. Does any entry family have raw edge under fixed holding or a simple runner?
2. Does any exit policy improve that same frozen entry set after costs?
3. Does orderflow work alone, as an additive feature, as a filter, or as an exit
   context?
4. Does KNN improve a transparent baseline, or does it mostly create sparse,
   overlapping, side-collapsed signals?
5. Does regime filtering improve out-of-sample results versus no-regime under
   the same entry, exit, cost, split, and feature setup?

If a component does not improve the matched baseline, remove it from default
research paths and keep it diagnostic only.

## Experiment Architecture

Use a staged evaluation pipeline:

1. Data gate: expanded durable BTC/ETH fixtures first where possible; compact
   fixtures only for smoke and preliminary falsification.
2. Entry lab: run cheap fixed-hold and simple-runner tests for each entry
   family. Persist frozen entry events and entry hashes.
3. Exit lab: reuse frozen entries and vary only exit policy and exit parameters.
4. Feature-family lab: compare bar-only, WT3D, orderflow-only, bar+orderflow,
   perp-only, bar+perp, and combined contexts under the same entry and exit.
5. Filter lab: compare each filter to its exact no-filter match.
6. Interaction lab: only test combined KNN/regime/orderflow/exits after each
   component has positive independent evidence.
7. Multiple-testing control: report trial count, effective trial count,
   correlation clusters, false-discovery controls, and deflated performance.

This flow saves time because exit and filter grids run on reusable entry events
instead of rerunning KNN for every parameter combination.

## Entry-Only Lab

Purpose: decide whether entries have raw predictive value before advanced exits
or filters are allowed to matter.

Entry families to evaluate:

| Family | Treatment | Comparator |
| --- | --- | --- |
| Price/trend/vol | `price_trend_vol` entry signals | no-trade, random-side density match, fixed-hold baseline |
| WT3D comparator | `compact_wt3d_base` | exact `price_trend_vol` match |
| KNN overlay | KNN thresholds and distances | transparent same feature family without KNN |
| Regime gate | GMM gate only, same-regime neighbors, all-regime with gate | no-regime |
| Orderflow-only | aggTrade/orderflow columns only | no-trade and bar-only |
| Perp-only | funding/OI/basis context only | no-trade and bar-only |

Entry exits for this phase should be deliberately simple:

- `fixed_holding_window`: 1h, 2h, 4h.
- `static_stop_time_exit`: fixed initial stop plus time exit.
- `simple_runner_v1`: deterministic runner described below.

Do not test KNN remaining-edge exits, dynamic barriers, GMM transition exits,
funding-aware exits, or adverse-selection exits until the entry family survives
this lab.

Minimum output table:

| Column | Meaning |
| --- | --- |
| `entry_family` | Transparent label for the entry rule |
| `feature_column_set_id` | Feature columns used by the entry |
| `entry_event_hash` | Hash of frozen entry timestamps, side, and symbol |
| `exit_policy_id` | Fixed-hold or simple runner only |
| `independent_event_count` | Event count after purge/embargo |
| `overlap_ratio` | Overlap after accounting |
| `side_collapse_ratio` | Max side share |
| `net_expectancy` | Costed expectancy |
| `hit_rate` | Costed hit rate |
| `mfe_quantiles` | MFE distribution, if lower-timeframe data exists |
| `mae_quantiles` | MAE distribution, if lower-timeframe data exists |
| `split_consistency` | Direction and magnitude consistency by split |
| `decision` | `keep`, `diagnostic_only`, or `drop` |

Entry keep rule:

- Keep only entries with positive costed expectancy, enough independent events,
  tolerable overlap, non-collapsed side distribution, and split stability.
- If fixed holding fails but simple runner passes, keep the entry only for
  exit-lab confirmation. Do not mark it candidate-ready.
- If simple runner creates all improvement while fixed holding is negative,
  treat the entry as exit-dependent and stress it harder.

## Simple Runner Baseline

The simple runner is a cheap exit baseline that should be tested before rich
exit families. It must be symmetric for longs and shorts and must use
lower-timeframe sequencing when available.

Use explicit return units in every config. Suggested first grid:

| Parameter | Values |
| --- | --- |
| `initial_stop_pct` | `0.30`, `0.50`, `0.70` |
| `activation_pct` | `0.30`, `0.40`, `0.50`, `0.70` |
| `runner_gap_pct` | `0.20`, `0.30`, `0.40` |
| `runner_step_pct` | `0.20`, `0.30`, `0.40` |
| `max_holding` | `1h`, `2h`, `4h` |

Example requested by operator:

- Initial stop: `-0.50%`.
- Runner activation: `+0.40%`.
- Runner gap: `0.30%`.
- When unrealized reaches `+0.40%`, protective stop becomes `+0.10%`
  (`0.40 - 0.30`).
- When unrealized reaches `+0.70%`, protective stop becomes `+0.40%`.
- Continue stepping by the runner step until target, timeout, or stop.
- For shorts, invert signs and use favorable move from entry.

Implementation requirements for the next coding pass:

- The runner must not use bar-close hindsight to decide whether target or stop
  happened first. Use lower-timeframe high/low ordering when available and a
  conservative ambiguous-hit rule otherwise.
- The runner should return MFE, MAE, exit reason, stop path, and whether the
  event used approximate sequencing.
- Runner sweeps should reuse frozen entry events and preloaded lower-timeframe
  paths.

## Exit-Only Lab

Purpose: prove whether exits improve results or hurt them.

Freeze the entry event set first. Then compare exits under identical symbol,
side, entry timestamp, split, cost model, feature family, and entry hash.

Exit families to compare:

| Exit family | First use | Baseline |
| --- | --- | --- |
| Fixed hold | Reference and entry quality | no-trade and simple runner |
| Static stop/target | Cheap risk boundary | fixed hold |
| Simple runner | Cheap trailing baseline | fixed hold |
| Triple barrier | Candidate risk shaping | simple runner and fixed hold |
| Volatility scaled barrier | Vol-aware risk shaping | fixed hold and simple runner |
| Max-MAE stop | Loss truncation | fixed hold |
| Funding/OI exits | Perp-context exit value | fixed hold with same entries |
| GMM transition exits | Regime exit value | no-regime fixed hold |
| KNN remaining-edge exits | KNN exit value | KNN entry with fixed hold |
| KNN dynamic barriers | KNN barrier value | simple runner and fixed hold |
| Adverse-selection exits | Microstructure exit value | simple runner and fixed hold |

Exit keep rule:

- Keep an exit only if it improves the same frozen entries after costs and
  survives split, side, symbol, and stress checks.
- Require a practical effect size, not just `min_score_delta: 0.0`. The next
  config should introduce a nonzero minimum delta for promotion-quality
  research, while keeping zero-delta rows available for diagnostics.
- If an exit reduces drawdown but destroys expectancy or event count, mark it
  risk-control-only, not alpha-improving.
- If an exit only wins on compact data or one side, keep diagnostic only.

Required exit report columns:

| Column | Meaning |
| --- | --- |
| `entry_event_hash` | Frozen entry set |
| `exit_policy_id` | Exit being tested |
| `exit_policy_params_json` | Full parameter payload |
| `matched_baseline_exit_policy_id` | Baseline exit |
| `final_score_delta` | Treatment minus matched baseline |
| `net_expectancy_delta` | Costed expectancy delta |
| `drawdown_delta` | Risk impact |
| `turnover_delta` | Trading cost pressure |
| `exit_reason_distribution` | Why exits happened |
| `ambiguous_hit_rate` | Conservative sequencing count |
| `decision` | `keep`, `risk_control_only`, `diagnostic_only`, or `drop` |

## Orderflow Lab

Purpose: decide whether aggTrade/orderflow fields contain useful information or
mostly add noise.

Orderflow in this branch is currently an aggTrade trade-flow proxy. It is not
true order-book imbalance and not true OFI. That distinction must stay visible
in manifests and reports.

Run these matched comparisons:

| Comparison | Treatment | Comparator | Question |
| --- | --- | --- | --- |
| Flow-only vs no-trade | `features_aggtrade_orderflow_v1` entry only | no-trade/random density | Does flow alone predict anything? |
| Flow-only vs bar-only | flow entry only | `price_trend_vol` | Is flow stronger than bars? |
| Bar+flow vs bar-only | `features_price_perp_aggflow_no_wt` or flow-added set | exact bar-only match | Does flow add incremental value? |
| Flow filter vs no filter | same bar entry with flow gate | same bar entry without flow gate | Does flow reject bad trades? |
| Flow exit vs simple runner | adverse-selection/orderflow exit | same entries with simple runner | Does flow improve exits? |

Orderflow keep rule:

- Keep as standalone only if flow-only beats no-trade and random density after
  costs with enough independent events.
- Keep as additive only if bar+flow beats exact bar-only after costs and
  survives split/symbol stress.
- Keep as a filter only if it rejects more bad trades than good trades and
  preserves enough sample retention.
- Drop from default if it only improves in one compact window, increases
  missingness, creates side collapse, or requires a story after the fact.

Required orderflow diagnostics:

- Source family, provider capability, archive hashes, and context coverage.
- Missingness by feature and split.
- `quality_aggtrade_source_present`.
- `quality_aggtrade_latest_window_diagnostic`.
- `quality_aggtrade_flow_proxy_not_ofi`.
- Incremental delta over bar-only after exact matching.
- Event-retention and false-rejection analysis for filter usage.

## KNN And Regime Lab

Purpose: determine if KNN and regime labels help, or if they only create sparse
and overlapping signals.

Regime comparisons:

| Treatment | Comparator | Claim allowed |
| --- | --- | --- |
| No-regime KNN | Transparent no-KNN entry | KNN value without regime |
| GMM gate only | No-regime same entry | Current-regime gate value |
| GMM same-regime neighbors | No-regime KNN | Regime-local neighbor value |
| GMM all-regime neighbors with gate | No-regime KNN | Gate value without neighbor restriction |
| True HMM backend | GMM and no-regime | True HMM transition value only if a true HMM backend is used |

KNN parameter axes:

- Distance: `euclidean`, `manhattan`, `cosine`.
- K: `3`, `5`, `8`, `13`, `21`, `34`.
- Min neighbor count: `2`, `3`, `4`, `5`.
- Probability threshold: `0.48` to `0.62`.
- Vote margin: `0.00` to `0.05`.
- Expected value threshold: `-0.0004` to `0.0002`.
- Distance quality: `0.0`, `0.005`, `0.01`.

KNN keep rule:

- Keep only if it improves the matched non-KNN baseline after costs and
  multiple-testing controls.
- Penalize high overlap, low independent events, and side collapse.
- Report effective trial counts, not just scheduled trial counts.
- If many nominal configurations collapse to the same predictions, deduplicate
  by prediction hash and entry event hash before exit testing.

## Filter Lab

Purpose: test filters independently from entry and exit.

Filter comparisons should reuse `filter_ablation_matrix_v5` patterns:

| Filter family | Required comparison |
| --- | --- |
| HVP / realized-vol percentile | exact filter-on vs no-filter |
| ATR percentile | exact filter-on vs no-filter |
| ER/chop | exact filter-on vs no-filter |
| Volatility shock | exact filter-on vs no-filter |
| Funding | exact filter-on vs no-filter |
| Basis/premium | exact filter-on vs no-filter |
| Orderflow | exact filter-on vs no-filter |
| Liquidation context | exact filter-on vs no-filter, only if provider-backed |

Filter keep rule:

- Keep a filter only if treatment beats the exact no-filter row, after costs,
  with acceptable sample retention.
- Report rejected-good-trade rate and rejected-bad-trade rate.
- Do not enable a filter as a default because it sounds sensible. It must win
  the matched ablation.

## Feature Family Lab

Feature families should be tested as isolated treatments:

| Feature family | Comparator | Decision question |
| --- | --- | --- |
| Bar-only price/trend/vol | no-trade and random density | Is there baseline edge? |
| WT3D | exact bar-only | Does WT3D add value? |
| AggTrade flow only | no-trade and bar-only | Does flow stand alone? |
| Bar + aggTrade flow | exact bar-only | Does flow add incremental value? |
| Perp context only | no-trade and bar-only | Does perp context stand alone? |
| Bar + perp context | exact bar-only | Does perp context add value? |
| Liquidation context | exact bar-only | Does liquidation context add value? |
| Full context | best simple family | Does complexity beat simpler evidence? |

Feature keep rule:

- Prefer the simplest family that survives. A complex feature set must win by a
  practical margin over its simpler comparator.
- Do not combine WT3D, KNN, orderflow, perp context, and advanced exits until
  each component has a positive matched result.

## Statistical Controls

The next research model should make the search ledger more honest about
multiple testing and overfit risk:

- Record scheduled trial count and effective trial count.
- Cluster trials by prediction hash, entry event hash, feature hash, and exit
  result hash.
- Report deflated performance metrics when many trials are searched.
- Apply false-discovery controls across component families.
- Use purged/embargoed split handling for overlapping labels and time-series
  leakage.
- Keep a final untouched holdout until component families are selected.

References for methodology:

- Halbert White, "A Reality Check for Data Snooping", Econometrica 68(5),
  2000: https://www.econometricsociety.org/publications/econometrica/issue/2000/09/5
- David H. Bailey and Marcos Lopez de Prado, "The Deflated Sharpe Ratio:
  Correcting for Selection Bias, Backtest Overfitting and Non-Normality",
  2014: https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf
- Yoav Benjamini and Yosef Hochberg, "Controlling the False Discovery Rate: A
  Practical and Powerful Approach to Multiple Testing", 1995:
  https://www.math.tau.ac.il/~ybenja/MyPapers/benjamini_hochberg1995.pdf
- Robert D. Arnott, Campbell R. Harvey, and Harry Markowitz, "A Backtesting
  Protocol in the Era of Machine Learning", 2018:
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3275654

## Immediate Work Packets For Next Phase

### WPR105-01 Latest Sweep Postmortem

Goal: Extract top blocked clusters from the completed BTC exact sweep and
measure effective-equivalent trial duplication.

Outputs:

- Top-k blocked candidates per blocker, feature family, horizon, and distance.
- Prediction hash and entry event hash clustering.
- Effective trial count versus scheduled trial count.
- Recommendation for pruning no-op dimensions under `regime_mode: none`.

### WPR105-02 Entry-Only Baseline Lab

Goal: Run frozen-entry tests with fixed holding and simple runner only.

Outputs:

- Entry event ledgers for bar-only, WT3D, KNN, no-regime, GMM-gated, flow-only,
  and perp-only families.
- Fixed-hold and simple-runner baseline tables.
- Keep/drop decisions before advanced exits.

### WPR105-03 Simple Runner And Exit Lab

Goal: Implement or formalize the simple runner baseline and run exit-only
ablations on frozen entries.

Outputs:

- Lower-timeframe sequencing checks.
- Static stop, static target, simple runner, triple barrier, volatility
  barrier, max-MAE, funding/OI, GMM, KNN, and adverse-selection comparisons.
- Exit decision matrix against fixed hold and simple runner.

### WPR105-04 Orderflow Independent Ablation

Goal: Determine if aggTrade flow helps by itself, as an additive feature, as a
filter, or as an exit signal.

Outputs:

- Flow-only versus no-trade.
- Flow-only versus bar-only.
- Bar+flow versus bar-only.
- Flow-filter versus no-filter.
- Flow-exit versus simple runner.
- Source quality and missingness diagnostics.

### WPR105-05 KNN Regime Filter Falsification

Goal: Test no-regime, GMM, and optional true-HMM treatments against exact
comparators.

Outputs:

- No-regime KNN versus transparent no-KNN.
- GMM gate-only versus no-regime.
- Same-regime KNN versus all-regime KNN.
- True-HMM only if a true backend is present.
- Multiple-testing and effective-trial reports.

### WPR105-06 Expanded Durable Evidence

Goal: Move beyond compact fixtures for any component that survives screening.

Outputs:

- Expanded BTC/ETH primary-bar fixtures with lower-timeframe and context
  coverage.
- Reproducible manifests and source hashes.
- Candidate-ready evidence only if gates pass; otherwise a documented reject.

## Handoff Prompt For Research Evaluation Model

Use this prompt when handing the work to a separate research/evaluation model:

```text
You are evaluating the research/v3-experimental-engine branch. Treat all
outputs as research-only, observe-only, and promotion_ready=false. Do not make
live trading or profitability claims.

Start from:
docs/stage_reports/STAGE_R104_EXIT_ENTRY_ORDERFLOW_RESEARCH_HANDOFF.md

Latest completed run:
data/research/operator_runs/discovery_runs/exact-entry-sweep-btcusdt-durable-r104-v1/run-discovery-142f3b61b761470b8aeb105967dd9c47

Primary task:
Decouple entry quality, exit value-add, orderflow value-add, KNN/regime value,
and filter value. Do not run another coupled brute-force sweep until you have
measured the components independently.

Required analysis:
1. Postmortem the latest exact sweep and cluster effective-equivalent trials.
2. Build entry-only fixed-hold and simple-runner baselines.
3. Freeze entry event hashes before exit sweeps.
4. Test whether exits improve or hurt matched frozen entries.
5. Test orderflow independently as standalone signal, additive feature, filter,
   and exit context.
6. Test KNN and GMM/no-regime comparisons with exact matched baselines.
7. Report effective trial count, multiple-testing controls, split stability,
   cost stress, side balance, overlap, and independent-event counts.

Decision rule:
Keep only components that beat their exact simple comparator after costs and
survive split/symbol/stress checks. Mark everything else diagnostic-only or
drop from default research paths.
```

## Completion State

Development is not finished from an empirical strategy standpoint. The branch
now has a functioning research engine, durable screening fixtures, fail-closed
candidate boundaries, UI/operator controls, exact search hardening, and a
completed long BTC sweep. The missing piece is empirical proof that any entry,
exit, orderflow, KNN/regime, or filter component improves a simple baseline on
durable evidence.

The next operation should therefore be Stage R105 component falsification, not
promotion planning.
