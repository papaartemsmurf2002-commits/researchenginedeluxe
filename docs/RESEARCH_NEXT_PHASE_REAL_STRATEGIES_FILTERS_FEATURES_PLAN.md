# Research Next Phase Real Strategies Filters Features Plan

Date: 2026-05-11
Branch: `research/v3-experimental-engine`
Input documents:

- `C:/Users/papaa/Downloads/tradingbotsuite_real_strategies_filters_features_research_plan.md`
- `C:/Users/papaa/Downloads/BTC_ETH_PERP_RESEARCH_IMPLEMENTATION_HANDOFF.md`

This plan converts the external findings into repo-aligned development work.
It does not replace `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md` or
`docs/RESEARCH_BRANCH_AUDIT_AND_NEXT_STAGE_HANDOFF.md`; it is the next-phase
implementation roadmap derived from them.

All work remains research-only:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- no order placement
- no live config writes
- no candidate promotion from latest-window evidence

## Executive Decision

The external plan is directionally strong and should be used, but not as a
request to add many new strategy plugins immediately. The current repo already
has most transparent strategy families and research infrastructure. The next
phase should harden truthfulness first, then add missing orderflow/features, then
expand data coverage.

Core decision:

```text
Do not expand the discovery grid.
Do not chase more top-score candidates.
First make existing discovery candidates harder to fool.
```

The next phase should be named:

```text
Stage R94 - Real Strategy Truthfulness And Feature/Filter Expansion
```

## How The External Findings Map To This Repo

| External finding | Repo alignment | Decision |
| --- | --- | --- |
| Public Binance klines and aggTrades are useful durable sources. | `tradingbotsuite.data.providers.binance_vision`, fixture builder, agg_trade family already exist. | Accept. Prioritize durable BTC/ETH archive fixtures and aggTrade feature pack. |
| REST OI/basis/taker ratios are latest-window limited. | Current fixture provenance supports latest-window/diagnostic flags. | Accept. Keep REST context diagnostic unless durable source exists. |
| Funding is both cost and crowding signal. | Funding strategies and funding-aware exits already exist. | Accept. Strengthen matched ablations and cost accounting. |
| aggTrades are trade flow, not book imbalance. | Current `microstructure_context_v1` mixes aggTrade-like and depth-like names. | Accept with modification. Split public aggTrade flow from depth/order-book features. |
| True order-book features require depth reconstruction. | Data contracts mention `book_ticker` and `depth_snapshot`, but durable L2 is not ready. | Defer. Do not implement true OFI until snapshot/diff-depth integrity exists. |
| Liquidation streams are incomplete by design. | Liquidation feature pack exists, latest run blocked for insufficient finite columns. | Accept. Keep liquidation diagnostic until provider-backed finite data exists. |
| GMM is not HMM. | Discovery materialization uses `GaussianMixture`. | Accept. Add explicit GMM/no-regime modes before true HMM. |
| KNN must be local analog layer, not magic model. | KNN study engine exists with split safety and side-adjusted expectancy. | Accept. Add no-regime controls, cached neighbor matrices, and threshold sweeps. |
| Multiple testing is central risk. | Search space is huge and latest run sampled 0.00056%. | Accept. Add effective-trial, stability, and multiple-testing gates before deep validation. |
| Strategy families S1-S9 should be tested. | Many transparent strategy plugins already exist. | Accept selectively. Use existing plugins as baselines; add missing features/ablations first. |

## Selected Strategy Families

The external plan lists nine strategy families. They are useful, but they should
not all become new plugins immediately.

### Tier 1 - Implement Now

These align with existing plugins/features and are most useful for validating
the discovery engine.

| Family | Existing repo support | Next action |
| --- | --- | --- |
| S1 volatility-adaptive trend continuation | `trend_following_v1`, `volatility_breakout_v1`, `features_price_trend_vol`, `features_full_context_no_wt` | Use as transparent comparators and matched KNN overlays. Add stronger volatility/filter ablation. |
| S3 range/chop mean reversion | `range_reversion_v1`, `features_price_trend_vol` | Use as explicit opposite comparator to trend. Add ER/chop filter matrix. |
| S4 funding/basis crowding and carry-aware direction | `funding_basis_v1`, `funding_crowding_fade_v2`, `funding_window_timing_v1`, funding-aware exits | Strengthen funding as cost vs signal in ablation and exit lab. |
| S5 OI expansion/contraction context | `oi_flow_breakout_v2`, `oi_contraction_exit_v1`, OI features | Test OI as feature, hard filter, and exit condition. |
| S6 aggTrade trade-flow confirmation/exhaustion | agg_trade fixture family, partial flow columns in feature builder | Add dedicated `aggtrade_orderflow_v1` feature pack and filter ablation. |
| S9 KNN local analog overlay | `research_discovery.knn_study`, `hmm_knn_local_analog_filter_v2` | Add no-regime controls, independent event accounting, cached sweeps. |

### Tier 2 - Implement After Truthfulness Foundation

These are promising but should wait until Stage R94 core gates exist.

| Family | Reason to delay | Required precondition |
| --- | --- | --- |
| S2 shock breakout/post-shock continuation | Current shock features exist, but event independence and exits need hardening first. | Independent event accounting and exit-lab gate. |
| S7 liquidation absorption/continuation | Latest liquidation feature set was not finite enough. | Durable provider-backed liquidation fixture. |
| S8 regime-adaptive ensemble | Current regime layer is GMM, not HMM, and no-regime comparison is missing. | Explicit regime baseline matrix. |

### Deferred Or Rejected For Now

| Idea | Decision | Reason |
| --- | --- | --- |
| True L2 order-book imbalance / true OFI now | Defer | Requires snapshot/diff-depth reconstruction and continuity evidence. |
| True HMM first | Defer | Need no-regime vs GMM evidence before adding another regime backend. |
| ANN/GPU-first KNN | Defer | Exact cached KNN parity and telemetry should come first. |
| Brute-force full 887M search | Reject | Computationally wasteful and statistically unsafe. |
| WT/WT3D as default alpha | Reject | Keep WT/WT3D as optional comparator only. |
| Liquidation as default filter | Reject for now | Insufficient finite/provider-backed data in latest run. |
| Long/short ratio durable claims from REST | Reject | REST context is latest-window diagnostic unless durable source exists. |

## BTC/ETH Handoff Alignment

The BTC/ETH implementation handoff is compatible with this plan if it is
treated as a candidate-priority and validation-hardening input, not as a request
to bypass current research guards.

### Accepted Alignment Points

- Keep the execution sequence:
  truthfulness gates, durable BTC/ETH data, perp-native feature packs,
  regime/KNN overlays, strategy candidates, exit lab, multiple-testing
  hardening, then candidate-pack eligibility.
- Prioritize BTCUSDT first, then ETHUSDT once durable fixture readiness and
  cross-symbol alignment checks pass.
- Treat KNN as local analog evidence:
  entry filter, empirical outcome distribution, remaining-edge exit signal, and
  dynamic-barrier estimator. Do not treat KNN as a standalone alpha model.
- Treat the current regime backend as GMM until a true HMM backend is explicitly
  implemented and proven. HMM language must not be used for current GMM output.
- Keep liquidation and true L2/order-book features diagnostic-only until durable
  historical data, continuity, and finite-column health gates pass.
- Add feature/filter/exit ablations before interpreting any candidate as more
  than a discovery lead.

### Candidate Priority Imported From The Handoff

| Priority | Candidate | R94 decision |
| --- | --- | --- |
| P1 | `perp_basis_convergence_v3` | Implement as the first new BTC/ETH candidate blueprint after truthfulness, durable perp context, and exit-gate packets exist. |
| P1 | `oi_flow_breakout_v3` | Implement as the second candidate blueprint, using OI plus aggTrade flow, with GMM/no-regime comparisons and KNN local analog filters. |
| P2 | `funding_crowding_fade_v3` | Keep as an upgraded funding/basis sleeve; require ablations proving funding is not just cost drag or crowding overfit. |
| P2 | `eth_btc_beta_residual_v2` | Add after durable ETH fixtures and cross-symbol point-in-time joins exist. |
| P3 | `liquidation_absorption_classifier_v1` | Keep diagnostic-only until historical liquidation and/or depth fixtures pass health checks. |

### Non-Negotiable Guardrails From The Handoff

- Latest-window REST context can support diagnostics and preflight only. It
  cannot support candidate-ready claims, long-horizon backtest claims, or
  candidate-pack eligibility.
- Missing derivatives context is `unknown` with a quality flag. Do not zero-fill
  liquidation, depth, taker, OI, or ratio data.
- Joins must be backward-as-of by completed decision time. Future funding,
  smoothed regime states, and overlapping future KNN labels are blockers.
- Dense overlapping bar signals are not independent events. Candidate scoring
  must use independent-event accounting.
- Candidate-pack eligibility requires exit-lab evidence, transparent
  comparators, no-regime baseline evidence when regime is claimed, and
  multiple-testing/stability evidence.
- aggTrades are compressed trade-flow proxies, not order-book imbalance or true
  OFI.

## Current Infrastructure Fit

### Existing Assets To Reuse

| Need | Current file families |
| --- | --- |
| Feature registry and manifests | `src/tradingbotsuite/features/**`, `configs/features/**` |
| Provider and fixture provenance | `src/tradingbotsuite/data/**`, `data/research/fixtures/**` |
| Strategy plugins | `src/tradingbotsuite/strategies/**`, `configs/strategies/**` |
| Backtest and exits | `src/tradingbotsuite/backtesting/**` |
| Historical-cycle orchestration | `src/tradingbotsuite/research_cycle/**` |
| Discovery run manager | `src/tradingbotsuite/research_discovery/runner.py` |
| GMM regime materialization | `src/tradingbotsuite/research_discovery/hmm_materialization.py` |
| KNN prediction engine | `src/tradingbotsuite/research_discovery/knn_study.py` |
| Discovery filter ablation | `src/tradingbotsuite/research_discovery/ablation_matrix.py` |
| Discovery exit lab | `src/tradingbotsuite/research_discovery/exit_lab.py` |
| Candidate-pack bridge | `src/tradingbotsuite/research_discovery/candidate_pack_bridge.py` |
| Operator Research UI | `src/tradingbotsuite/web/templates/research.html`, `src/tradingbotsuite/web/operator.py`, `src/tradingbotsuite/operator_console.py` |

### Important Current Gaps

- No clean no-regime discovery mode.
- GMM materialization is still named as HMM in many discovery concepts.
- Bar-level signal counts are not independent executable events.
- Discovery scoring rewards dense signal counts.
- Exit lab is not mandatory before candidate-pack bridge eligibility.
- `microstructure_context_v1` mixes public aggTrade-style features and
  depth/order-book feature names.
- The latest liquidation feature set did not pass finite-column preflight.
- Durable BTC/ETH multi-window fixtures are not yet the standard discovery
  target.
- Runtime telemetry is too thin to explain resource utilization.

## Stage R94 Development Plan

### WPR94-01 Regime Baseline And Naming Truthfulness

Purpose:
Make regime usage explicit and stop treating GMM as true HMM.

Implementation shape:

- Add a discovery `regime_mode` axis:
  - `none`
  - `gmm_gate_only`
  - `gmm_same_regime_neighbors`
  - `gmm_all_regime_neighbors_with_gate`
- Keep existing GMM materialization but record it as GMM in manifests.
- Make `same_regime_only=false` with no regime gate possible.
- Add run-manifest and trial-payload fields:
  - `regime_detector_type`
  - `regime_mode`
  - `regime_gate_enabled`
  - `same_regime_neighbor_pool_enabled`
  - `true_hmm_backend_used: false`
- Update UI/docs labels from "HMM" to "GMM regime detector" where current
  discovery implementation is meant.

Likely touchpoints:

- `src/tradingbotsuite/research_discovery/spec.py`
- `src/tradingbotsuite/research_discovery/runner.py`
- `src/tradingbotsuite/research_discovery/hmm_materialization.py`
- `src/tradingbotsuite/research_discovery/knn_study.py`
- `configs/discovery/*.json`
- `tests/research_discovery/**`
- operator Research UI labels if surfaced

Exit criteria:

- Same feature/horizon/KNN settings can be run with no-regime, GMM gate only,
  and GMM same-regime variants.
- Tests prove no-regime mode does not read `regime_no_trade`.
- Manifests stop overstating current GMM as true HMM.

### WPR94-02 Independent Event Accounting And Score Redesign

Purpose:
Stop ranking overlapping high-density bar signals as if they were independent
trades.

Implementation shape:

- Add independent event accounting for discovery rows:
  - sort by decision time/source index
  - accept first event
  - suppress same-symbol events until exit horizon or configured spacing
  - record overlap ratio
  - record side-separated independent events
- Add metrics:
  - `accepted_bar_count`
  - `independent_event_count`
  - `overlap_ratio`
  - `event_signal_rate`
  - `side_collapse_ratio`
  - `near_signal_ceiling`
- Replace or version discovery score:
  - keep old score as `legacy_density_score`
  - add `discovery_screen_score_v2`
  - penalize signal rate near ceiling
  - penalize overlapping long-horizon labels
  - penalize one-side collapse unless comparator beats directional baseline

Likely touchpoints:

- new `src/tradingbotsuite/research_discovery/event_accounting.py`
- `src/tradingbotsuite/research_discovery/runner.py`
- `src/tradingbotsuite/research_discovery/state.py`
- `tests/research_discovery/**`

Exit criteria:

- Latest-run style `72h` dense candidates would be visibly flagged.
- Score ranking no longer rewards trade count alone.
- Trial payloads include independent-event metrics.

### WPR94-03 Mandatory Exit-Lab Gate

Purpose:
Convert discovery label leads into executable exit hypotheses before any bridge
eligibility.

Implementation shape:

- Add candidate bridge requirement:
  - `exit_lab_status == complete`
  - fixed-hold baseline exists
  - at least one exit family has enough trades or candidate is diagnostic-only
- Extend exit lab decisions:
  - `exit_improving`
  - `fixed_hold_only`
  - `insufficient_trade_density`
  - `missing_required_context`
  - `unstable_by_split`
- Ensure fixed-hold vs barrier/ATR/trailing/funding/OI/regime exits are grouped
  by the same entry family and feature setup.

Likely touchpoints:

- `src/tradingbotsuite/research_discovery/exit_lab.py`
- `src/tradingbotsuite/research_discovery/candidate_pack_bridge.py`
- `configs/discovery/discovery_exit_lab_v4.json`
- `configs/discovery/discovery_candidate_pack_bridge_v4.json`
- `tests/research_discovery/test_exit_lab.py`
- `tests/research_discovery/test_candidate_pack_bridge.py`

Exit criteria:

- Candidate-pack bridge rejects discovery rows without exit-lab completion.
- Tests cover incomplete, pending, passed, and diagnostic-only exit states.

### WPR94-04 AggTrade Orderflow Feature Pack

Purpose:
Add durable public-archive orderflow features without pretending they are order
book imbalance.

Implementation shape:

- Add `aggtrade_orderflow_v1` feature pack and manifest.
- Add columns such as:
  - `agg_taker_buy_quote_share`
  - `agg_signed_quote_imbalance`
  - `agg_sqrt_signed_quote_imbalance`
  - `agg_cvd_slope`
  - `agg_trade_count_zscore`
  - `agg_quote_volume_zscore`
  - `agg_large_trade_count`
  - `agg_large_trade_side_imbalance`
  - `agg_flow_burst_score`
  - `agg_sweep_proxy`
- Keep `top_of_book_imbalance`, `queue_imbalance_l5`, and true OFI in a later
  depth-specific pack.
- Add feature completeness and point-in-time tests.

Likely touchpoints:

- `src/tradingbotsuite/features/registry.py`
- `src/tradingbotsuite/features/packs.py`
- `src/tradingbotsuite/features/builders.py`
- `configs/features/features_aggtrade_orderflow_v1.json`
- `configs/features/features_price_perp_aggflow_no_wt.json`
- `tests/features/**`
- `tests/contracts/test_feature_contracts.py`

Exit criteria:

- AggTrade features can be built from fixture `agg_trade` family.
- Missing aggTrade data produces explicit missingness, not silent fake signal.
- No doc or manifest calls these features order-book imbalance.

### WPR94-05 Matched Filter Ablation V2

Purpose:
Determine whether filters improve edge or only reduce sample size.

Implementation shape:

- Extend ablation matrix to support filter families:
  - HVP / realized-vol percentile
  - ATR percentile
  - ER/chop
  - volatility shock
  - funding
  - basis/premium
  - OI
  - aggTrade flow
  - liquidation, only when finite/provider-backed
- Add decision labels:
  - `edge_improving`
  - `sample_reducing_only`
  - `unstable`
  - `side_specific`
  - `not_testable`
  - `harmful`
- Require matched grouping:
  - same entry family
  - same feature set
  - same horizon
  - same regime mode
  - same KNN settings if applicable
  - same exit policy
  - same splits and cost model

Likely touchpoints:

- `src/tradingbotsuite/research_discovery/ablation_matrix.py`
- `configs/discovery/perp_filter_ablation_matrix_v4.json`
- new `configs/discovery/filter_ablation_matrix_v5.json`
- `tests/research_discovery/test_ablation_matrix.py`

Exit criteria:

- Filters cannot be marked default unless they beat matched no-filter rows.
- Missing finite columns become `not_testable`, not failed or passed.

### WPR94-06 Strategy Family Matrix Using Existing Plugins

Purpose:
Run real economic strategy families without duplicating plugins already present.

Implementation shape:

- Define matrix entries that use existing plugins:
  - trend continuation: `trend_following_v1`, `volatility_breakout_v1`
  - range/chop reversion: `range_reversion_v1`
  - funding/basis: `funding_basis_v1`, `funding_crowding_fade_v2`,
    `funding_window_timing_v1`
  - OI: `oi_flow_breakout_v2`
  - liquidation: `liquidation_absorption_classifier_v1`, diagnostic only until
    finite provider-backed evidence exists
  - regime adaptive: `regime_adaptive_v1`, `hmm_routed_alpha_sleeves_v2`,
    after regime truthfulness work
  - KNN overlay: `hmm_knn_local_analog_filter_v2`
- Add configs that compare transparent plugin baseline vs KNN overlay vs
  filtered variants.

Likely touchpoints:

- `configs/research/**`
- `configs/strategies/**`
- `configs/discovery/**`
- `tests/historical/**`
- `tests/contracts/test_strategy_contracts.py`

Exit criteria:

- Each selected family has a transparent comparator and no-trade comparator.
- KNN overlay is never the only tested strategy for a family.

### WPR94-07 Durable BTC/ETH Public Archive Fixtures

Purpose:
Move discovery from latest-window proof-of-machinery toward durable validation
windows.

Implementation shape:

- Build or document fixture configs for:
  - BTCUSDT 15m bars
  - ETHUSDT 15m bars
  - lower-timeframe bars for exit sequencing
  - aggTrades for orderflow features
- Use Binance Vision/public archive checksums when available.
- Keep REST derivatives context explicitly latest-window/diagnostic unless a
  durable source exists.
- Select windows by regime:
  - trend/bull
  - drawdown/bear
  - range/chop
  - high-vol shock
  - funding/OI extremes when data allows

Likely touchpoints:

- `src/tradingbotsuite/data/providers/binance_vision.py`
- `src/tradingbotsuite/data/historical_fixture_pack.py`
- `configs/research/**`
- `data/research/fixtures/**` only if intentionally checked evidence is small
  and approved
- `tests/contracts/test_historical_fixture_pack_contract.py`
- `tests/historical/**`

Exit criteria:

- Latest-window-only candidates remain diagnostic.
- BTC and ETH fixtures have durable provenance and checksums.
- Fixture limitations are visible in manifests.

### WPR94-08 Discovery Compute Telemetry And Cached KNN Sweeps

Purpose:
Use machine resources better and make runtime understandable.

Implementation shape:

- Add telemetry:
  - wall time by stage
  - CPU percent if available
  - memory peak
  - active workers
  - trials per minute
  - feature cache hit rate
  - label/split cache hit rate
  - GMM/regime cache hit rate
  - neighbor cache hit rate
  - artifact write time
  - bytes written
- Add exact neighbor cache:
  - per feature set
  - split
  - horizon
  - regime mode
  - distance metric
- Sweep `k` and thresholds over cached neighbor arrays.
- Preserve deterministic exact-KNN parity before ANN/GPU work.

Likely touchpoints:

- new `src/tradingbotsuite/research_discovery/telemetry.py`
- new `src/tradingbotsuite/research_discovery/neighbor_cache.py`
- `src/tradingbotsuite/research_discovery/runner.py`
- `src/tradingbotsuite/research_discovery/knn_study.py`
- `tests/research_discovery/**`

Exit criteria:

- Repeated threshold/k variants reuse exact neighbor data.
- Run manifests explain resource utilization.
- Serial and cached modes produce equivalent results in focused tests.

### WPR94-09 Multiple-Testing And Stability Gate Upgrade

Purpose:
Keep sparse large-grid winners from being overinterpreted.

Implementation shape:

- Add discovery reports:
  - declared search space
  - sampled fraction
  - effective trial count
  - best-candidate concentration
  - stability-neighborhood size
  - split/window concentration
  - side concentration
  - latest-window-only penalty
- Require all candidate acceptance text to say "lead" unless validation gates
  are complete.
- Add optional PBO/CSCV-style diagnostics where feasible.

Likely touchpoints:

- `src/tradingbotsuite/research_discovery/runner.py`
- `src/tradingbotsuite/optimization/**`
- `src/tradingbotsuite/research_artifacts/candidate_pack.py`
- `tests/research_discovery/**`
- `tests/optimization/**`

Exit criteria:

- A single isolated top score from a huge grid cannot be treated as validated.
- Candidate bridge has explicit multiple-testing/stability blocker reasons.

### WPR94-10 Operator UI Truthfulness, Modernization, And Fluff Removal

Purpose:
Make the operator UI clear enough that a user does not confuse discovery leads
with validated candidates, and make the Research tab a compact, modern,
operator-ready product surface rather than a verbose diagnostic page.

Implementation shape:

- Remove or rewrite fluffy, legacy, and vague copy:
  - no unexplained "legacy" language in primary workflows
  - no marketing-style text blocks
  - no stage names without inline purpose and consequences
  - no UI text that suggests research outputs are live signals
- Modernize the layout around operator workflows:
  - run setup
  - data readiness
  - active run progress
  - latest snapshots
  - leads/candidates
  - blockers
  - charts
  - artifacts
- Add one-click controls for every routine command:
  - preflight data readiness
  - start quick/standard/deep discovery
  - pause/stop
  - resume
  - open latest snapshot
  - evaluate candidate-pack eligibility
  - open artifact folder
- Preserve compactness:
  - dense but readable tables
  - collapsed detail drawers for long explanations
  - short labels with tooltips for research concepts
  - no oversized cards for repeated status items
- Add dynamic operator feedback:
  - live progress and stage status
  - last snapshot age
  - trial throughput
  - active blockers
  - run health warnings
  - whether results are diagnostic, screen-worthy, or candidate-ready
- Add local run-history and overwrite protection:
  - visible output directory
  - collision warning before reusing run ids
  - resume vs new-run choice
  - local state summary for interrupted runs
- Add visible warnings:
  - screen result, not validated
  - latest-window only
  - high signal density
  - mostly one-side exposure
  - no-regime baseline missing
  - exit lab missing
  - filter ablation missing
  - orderflow/liquidation not testable
- Surface new independent-event and filter-ablation metrics.
- Keep charting useful and non-decorative:
  - profitability/equity-style chart when executable backtest evidence exists
  - blocker and ablation charts for discovery-only runs
  - no empty chart shells without clear missing-evidence reason

Likely touchpoints:

- `src/tradingbotsuite/web/templates/research.html`
- `src/tradingbotsuite/web/operator.py`
- `src/tradingbotsuite/operator_console.py`
- `tests/tradingbotsuite/test_operator_ui.py`

Exit criteria:

- UI communicates candidate maturity level.
- No generated discovery row looks promotion-ready.
- The first screen answers: what can I run, what data is ready, what is running,
  what changed, and what is blocked.
- Vague or legacy copy is removed from primary workflows.
- Routine research actions have buttons and do not require copying CLI commands.
- Interrupted or repeated runs are safe from accidental overwrite.

### WPR94-11 Perp Context Delta Audit And Source Truthfulness

Purpose:
Align the existing perp context implementation with the BTC/ETH handoff without
silently changing the meaning of the current `features_perp_context_v2` family.

Implementation shape:

- Audit current `features_perp_context_v2` columns against handoff-required
  context:
  - mark/index basis and premium
  - basis/premium z-scores and slopes
  - funding last value, z-score, surprise, interval, caps/floors
  - carry-adjusted basis
  - OI notional, z-score, delta z-score, OI over volume
  - volatility context
  - time to/from funding
  - quality flags and source eligibility flags
- If semantics differ, add a new versioned manifest such as
  `features_perp_context_v3`; do not redefine existing `v2` columns in place.
- Add source eligibility metadata:
  - `durable_provider_archive`
  - `self_archived`
  - `latest_window_diagnostic`
  - `missing_unknown`
- Enforce missingness policy:
  - no zero-fill for OI, funding, taker, ratio, depth, or liquidation context
  - explicit quality flags for unknown/missing windows
  - backward-as-of joins by completed decision time

Likely touchpoints:

- `src/tradingbotsuite/features/**`
- `configs/features/features_perp_context_v2.json`
- possible new `configs/features/features_perp_context_v3.json`
- `src/tradingbotsuite/data/**`
- `tests/features/**`
- `tests/contracts/test_feature_contracts.py`

Exit criteria:

- The plan can state exactly which perp context columns are durable, diagnostic,
  or missing.
- Existing feature-pack names remain honest.
- Latest-window derivatives context cannot enter non-diagnostic candidate claims.

### WPR94-12 Exit Model Upgrade And Remaining-Edge Lab

Purpose:
Expand exit testing so BTC/ETH candidates are judged by executable exit logic,
not only by triple-barrier or fixed-hold labels.

Implementation shape:

- Add or expose exit families in the discovery exit lab:
  - `basis_normalization_exit_v1`
  - `premium_normalization_exit_v1`
  - `gmm_transition_exit_v1` for the current regime backend
  - future `hmm_transition_exit_v1` only after a true HMM backend exists
  - `knn_remaining_edge_exit_v1`
  - `knn_dynamic_barriers_v1`
  - funding-aware and OI-contraction exits where already supported
- Defer `liquidity_adverse_selection_exit_v1` until durable book/depth evidence
  exists.
- Require exit comparisons to share identical entries, splits, costs, feature
  sets, regime mode, and KNN setup.
- Record exit-lab evidence by side, split, regime mode, holding window, and cost
  stress.

Likely touchpoints:

- `src/tradingbotsuite/research_discovery/exit_lab.py`
- `src/tradingbotsuite/backtesting/**`
- `configs/discovery/discovery_exit_lab_v4.json`
- `configs/research/**`
- `tests/research_discovery/test_exit_lab.py`
- `tests/backtesting/**`

Exit criteria:

- `perp_basis_convergence_v3` can prove whether basis/premium normalization
  exits beat fixed-hold references.
- `oi_flow_breakout_v3` can prove whether OI contraction and KNN remaining-edge
  exits add value.
- No candidate can pass the bridge on entry labels alone.

### WPR94-13 BTC/ETH Candidate Blueprint Configs

Purpose:
Convert the handoff's strongest BTC/ETH ideas into explicit research configs
after truthfulness, data, and exit prerequisites exist.

Implementation shape:

- Add blueprint configs, not promotion artifacts, for:
  - `perp_basis_convergence_v3`
  - `oi_flow_breakout_v3`
  - upgraded `funding_crowding_fade_v3`
- Required `perp_basis_convergence_v3` ablations:
  - no basis/premium
  - no funding
  - no OI
  - no regime
  - no KNN
  - fixed-hold only
  - basis/premium normalization exit variants
- Required `oi_flow_breakout_v3` ablations:
  - no OI
  - no aggTrade flow
  - no funding context
  - no regime
  - no KNN
  - no OI-contraction exit
- All blueprints must include transparent strategy comparators, no-trade
  comparators, no-regime baselines, and candidate blocker reporting.

Likely touchpoints:

- `configs/research/**`
- `configs/discovery/**`
- `configs/strategies/**`
- `tests/historical/**`
- `tests/research_discovery/**`

Exit criteria:

- BTCUSDT blueprints can run as research-only discovery/deep-validation jobs.
- ETHUSDT blueprints are blocked until durable ETH fixture readiness is recorded.
- All outputs remain `research_only`, `observe_only`, and
  `promotion_ready: false`.

### WPR94-14 Cross-Asset BTC/ETH Residual Research

Purpose:
Add ETH/BTC relative-value research only after single-symbol BTC/ETH data
contracts are stable.

Implementation shape:

- Add or validate `cross_asset_btc_eth_v2` features:
  - BTC and ETH returns at matched intervals
  - ETH beta to BTC
  - residual return and residual z-score
  - ETHBTC trend/state
  - rolling correlation
  - funding spread z-score
  - OI delta spread
- Enforce cross-symbol point-in-time joins and explicit blocker reasons for:
  - missing durable ETH fixture
  - future alignment risk
  - weak BTC/ETH correlation window
  - missing transparent comparator
- Keep this as a later P2 candidate family; do not let it block P1 BTCUSDT
  basis/OI work.

Likely touchpoints:

- `src/tradingbotsuite/features/**`
- `configs/features/**`
- `configs/research/**`
- `tests/features/**`
- `tests/historical/**`

Exit criteria:

- Cross-asset features cannot leak future BTC/ETH bars.
- `eth_btc_beta_residual_v2` remains blocked unless the cross-symbol contract is
  proven in tests and manifests.

### WPR94-15 Validation Floors And Blocker Registry

Purpose:
Make the handoff's acceptance criteria executable and visible in every research
artifact.

Implementation shape:

- Add deep-validation defaults:
  - `independent_event_count_min: 120` for screen-to-deep validation
  - `independent_event_count_min: 250` for candidate-ready evidence
  - `overlap_ratio_max: 0.35` for screen-to-deep validation
  - `overlap_ratio_max: 0.25` for candidate-ready evidence
  - `split_pass_ratio_min: 0.60` for screen-to-deep validation
  - `split_pass_ratio_min: 0.70` for candidate-ready evidence
  - side concentration ceilings
  - cost-stress survival floors
  - stability-neighborhood floors
  - no-trade and transparent comparator requirements
  - no-regime baseline requirement when regime is claimed
  - exit/filter/feature ablation requirements
- Add standard blocker strings:
  - `funding_feature_future_leakage`
  - `regime_smoothed_state_used_in_validation`
  - `knn_future_or_overlapping_neighbor`
  - `latest_window_context_non_diagnostic_claim`
  - `liquidation_false_zero_window`
  - `depth_sequence_integrity_missing`
  - `barrier_ordering_without_lower_tf_proof`
  - `funding_only_crowding_overfit`
  - `cross_symbol_future_alignment`
  - `isolated_top_score_large_grid`
  - `knn_sample_reduction_only`
  - `baseline_comparator_missing`
- Add an experiment-budget ledger with:
  - strategy family
  - feature-set variants
  - parameter combinations
  - exit variants
  - regime modes
  - KNN `k` values
  - distance metrics
  - validation modes
  - effective trial count
  - sampled fraction
  - best-candidate concentration
  - stability-neighborhood size

Likely touchpoints:

- `src/tradingbotsuite/research_discovery/**`
- `src/tradingbotsuite/research_artifacts/candidate_pack.py`
- `configs/discovery/**`
- `tests/research_discovery/**`
- `tests/research_artifacts/**`

Exit criteria:

- Research reports show whether evidence is diagnostic, screen-worthy, or
  candidate-ready.
- Known failure modes become blocker codes rather than prose-only warnings.
- Candidate-pack bridge remains locked unless validation evidence is complete.

## Recommended Implementation Order

Do not start with new exotic strategies. Implement in this order:

1. WPR94-01 Regime Baseline And Naming Truthfulness
2. WPR94-02 Independent Event Accounting And Score Redesign
3. WPR94-03 Mandatory Exit-Lab Gate
4. WPR94-05 Matched Filter Ablation V2
5. WPR94-09 Multiple-Testing And Stability Gate Upgrade
6. WPR94-15 Validation Floors And Blocker Registry
7. WPR94-07 Durable BTC/ETH Public Archive Fixtures
8. WPR94-11 Perp Context Delta Audit And Source Truthfulness
9. WPR94-04 AggTrade Orderflow Feature Pack
10. WPR94-08 Discovery Compute Telemetry And Cached KNN Sweeps
11. WPR94-12 Exit Model Upgrade And Remaining-Edge Lab
12. WPR94-06 Strategy Family Matrix Using Existing Plugins
13. WPR94-13 BTC/ETH Candidate Blueprint Configs
14. WPR94-14 Cross-Asset BTC/ETH Residual Research
15. WPR94-10 Operator UI Truthfulness, Modernization, And Fluff Removal

The only reason to reorder is if data availability blocks a packet. In that
case, implement the truthfulness and scoring packets first anyway.

## Experiment Matrix For Stage R94

### Minimal Matrix

Use this for first validation after the truthfulness packets:

| Axis | Values |
| --- | --- |
| Symbols | BTCUSDT first; ETHUSDT after fixture readiness |
| Feature sets | `price_trend_vol`, `alternative_non_wt_price_state`, `full_context_no_wt`, future `aggtrade_orderflow_v1` |
| Strategies | trend, range, funding/basis, OI, KNN overlay |
| Regime modes | no regime, GMM gate, GMM same-regime |
| Horizons | 4h, 12h, 24h, 72h |
| K | 5, 13, 21 |
| Distance | cosine, Manhattan |
| Filters | none, vol bucket, ER/chop, funding, OI, aggTrade |
| Exits | fixed hold, ATR barrier, triple barrier when lower timeframe exists, trailing/risk, funding/OI exits |
| Validation | anchored and rolling walk-forward, purged/embargoed for overlapping labels |

Extended BTC/ETH matrix after WPR94-07, WPR94-11, WPR94-12, and WPR94-13:

| Axis | Values |
| --- | --- |
| Symbols | BTCUSDT; ETHUSDT only after durable fixture readiness |
| Feature sets | `perp_context_v2` or versioned successor, `aggtrade_orderflow_v1`, future `cross_asset_btc_eth_v2` |
| Candidates | `perp_basis_convergence_v3`, `oi_flow_breakout_v3`, `funding_crowding_fade_v3`, future `eth_btc_beta_residual_v2` |
| Regime modes | no regime, GMM gate, GMM same-regime, future true HMM only after backend proof |
| K | existing exact K grid first; larger 15/25/50/100-style sweeps only after cached neighbor parity |
| Distance | existing exact metrics first; `robust_euclidean`, `path_context`, and regime-posterior distances only after deterministic parity tests |
| Exits | fixed hold, ATR/triple barrier, basis/premium normalization, funding-aware, OI-contraction, KNN remaining-edge |
| Validation | purged/embargoed CV, rolling windows, cost stress, regime/no-regime holdout, feature/filter/exit ablations |

### Candidate Advancement Matrix

A candidate can move from discovery lead to deeper historical-cycle validation
only if these rows exist:

| Evidence | Required |
| --- | --- |
| no-trade comparator | yes |
| transparent strategy comparator | yes |
| no-regime baseline | yes |
| GMM mode comparison | yes if regime is claimed |
| independent event accounting | yes |
| exit lab | yes |
| filter ablation for claimed filter | yes |
| feature ablation for claimed feature family | yes |
| side-separated metrics | yes |
| split-separated metrics | yes |
| cost/funding stress | yes |
| latest-window limitation metadata | yes |
| multi-window evidence | required for non-diagnostic claim |

## Scoring And Gate Policy

The old density-driven discovery score should be retained only as legacy
evidence. The new score should rank leads by whether they are worth deeper
testing, not by how many overlapping bars they accepted.

Required new fields:

- `legacy_density_score`
- `discovery_screen_score_v2`
- `accepted_bar_count`
- `independent_event_count`
- `overlap_ratio`
- `event_signal_rate`
- `side_collapse_ratio`
- `signal_rate_ceiling_penalty`
- `latest_window_only_penalty`
- `exit_lab_status`
- `filter_ablation_status`
- `feature_ablation_status`
- `regime_baseline_status`

Minimum blocker reasons:

- `independent_event_count_below_floor`
- `overlap_ratio_above_ceiling`
- `signal_rate_near_ceiling`
- `directional_comparator_missing`
- `no_regime_baseline_missing`
- `exit_lab_missing`
- `filter_ablation_missing`
- `feature_ablation_missing`
- `latest_window_only_diagnostic`
- `orderflow_feature_not_testable`
- `liquidation_feature_not_testable`
- `multiple_testing_stability_incomplete`

## My Additional Recommendations

These extend the external plan with repo-specific priorities:

1. Separate public aggTrade flow from true depth microstructure in feature
   naming and manifests. This avoids a long-term semantic bug.
2. Keep strategy plugins boring and transparent. Most next value is in matched
   experiments and gates, not in more plugins.
3. Treat current high-density KNN candidates as test cases for the new blockers.
   A successful R94 may reject many current top candidates.
4. Do not add true HMM before GMM/no-regime comparison is complete. It may add
   model complexity without improving research truthfulness.
5. Do not add GPU/ANN before exact cached neighbor sweeps. Exact parity and
   telemetry are prerequisites.
6. Add UI maturity labels early enough that operators stop interpreting
   discovery ledgers as strategy results.
7. Treat UI modernization as product work, not styling polish: remove vague
   copy, expose routine actions as buttons, show dynamic run state, and protect
   local research outputs from accidental overwrite.
8. Make latest-window source limitations visible in every stage: ledgers,
   candidate bridge, UI, and docs.
9. Use ETH as a sanity check, not as a proof of broad generalization. BTC/ETH
   are correlated; true cross-market robustness needs later expansion.

## Validation Baseline For Implementation Packets

Every implementation packet should run:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
git diff --check
```

Broaden validation when touching:

| Touched area | Additional validation |
| --- | --- |
| Features/fixtures | `tests/features`, `tests/contracts/test_historical_fixture_pack_contract.py` |
| Strategies | `tests/contracts/test_strategy_contracts.py`, focused backtest tests |
| Exits/backtesting | `tests/backtesting`, `tests/historical` focused tests |
| Optimization/stability | `tests/optimization` |
| Candidate bridge | `tests/research_artifacts`, candidate bridge tests |
| Operator UI | `tests/tradingbotsuite/test_operator_ui.py` |

## Stop Conditions

Stop and report rather than pushing through if:

- no-regime mode requires weakening split safety;
- exit-lab gate conflicts with candidate-pack evidence contracts;
- aggTrade feature construction cannot be made point-in-time safe;
- durable BTC/ETH fixture construction would require committing huge generated
  data without explicit approval;
- a proposed shortcut weakens research-only/live-boundary flags;
- a change requires rewriting shared research-cycle/backtest contracts without
  focused tests.

## Final Recommendation

Use the external strategy plan as the economic hypothesis map, but implement the
repo phase as a truthfulness upgrade:

```text
regime truthfulness
-> independent events and score v2
-> mandatory exit lab
-> matched filter ablation
-> multiple-testing and validation blocker registry
-> durable BTC/ETH windows
-> perp context source audit
-> aggTrade orderflow features
-> cached compute and telemetry
-> exit model upgrade
-> existing strategy-family matrix
-> BTC/ETH candidate blueprints
-> cross-asset ETH/BTC residual research
-> modernized operator UI with fluff removed
```

This path complements the current architecture, avoids broad rewrites, and
turns the existing V4 discovery engine from a candidate screen into a stronger
research instrument.
