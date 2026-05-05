# Research V3 Perpetual Agent Development Plan

Date: 2026-05-05
Branch: `research/v3-experimental-engine`
Source input: `C:/Users/papaa/Downloads/TBS_RESEARCH_V3_PERP_STRATEGY_IMPLEMENTATION_PLAN.md`
Status: curated implementation instructions, refreshed after WPR47 Crypto Lake free-sample fallback

## Purpose

This document converts the downloaded BTC/ETH perpetual strategy expansion plan into repo-native instructions for the current TradingBotSuite research branch.

The branch already has a historical research framework. Future work must extend it, not replace it:

```text
provider manifests and fixture packs
  -> point-in-time feature frames
  -> validation splits
  -> strategy candidates
  -> reference/vector backtests
  -> cost stress, stability, and ablation evidence
  -> ranked research candidates
  -> fail-closed candidate pack only if gates pass
```

All new outputs must remain:

```yaml
research_only: true
observe_only: true
promotion_ready: false
```

No stage in this document creates live signals, paper/shadow/testnet/canary execution, promotion acceptance, order placement, runtime-control writes, or capital-allocation behavior.

## Current Branch Contracts To Preserve

Use the current branch as the source of truth:

- Ledger and governance: `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- Branch summary: `docs/RESEARCH_BRANCH_DISTILLATION.md`
- Cycle spec: `src/tradingbotsuite/research_cycle/spec.py`
- Cycle runner: `src/tradingbotsuite/research_cycle/runner.py`
- Feature registry/builders/cache: `src/tradingbotsuite/features/`
- Data contracts and fixture packs: `src/tradingbotsuite/data/`
- Provider collection: `src/tradingbotsuite/research/market_data.py`
- Strategy contract/registry/metadata: `src/tradingbotsuite/strategies/`
- Backtest engines and exits: `src/tradingbotsuite/backtesting/`
- Candidate pack gates: `src/tradingbotsuite/research_artifacts/candidate_pack.py`
- Crypto Lake free-sample fallback runbook: `docs/runbooks/crypto_lake_free_data_runbook.md`

The primary active package is `src/tradingbotsuite/`. The older `src/tradingbot/` package remains legacy/reference material unless a later work packet explicitly scopes it.

## Conflict Resolution Summary

| Downloaded plan item | Current branch conflict | Curated resolution |
| --- | --- | --- |
| First implementation stage named `R45` | R45 is already closed for branch distillation. WPR47 is closed for Crypto Lake free-data fallback and WPR48 is this plan refresh. | Perp implementation starts at WPR49. |
| Multi-symbol top-level config with `symbols` | `HistoricalResearchCycleSpec` is single-symbol. | Run BTCUSDT and ETHUSDT as separate cycle specs first. Multi-symbol/cross-asset cycle support is a later dedicated packet. |
| Holding window `8h` | Current supported windows are `1h`, `4h`, `12h`, `24h`, `72h`, `7d`. | Remove `8h` until `REQUIRED_HOLDING_WINDOWS`, strategy helper, tests, and artifacts explicitly support it. |
| Config keys `name`, `feature_sets`, `validation_modes`, `candidate_gates` | Current spec uses `cycle_id`, `features.feature_sets`, `validation.split_modes`, and candidate gates derived from runner/pack contracts. | Use current spec shape. New gate concepts become reports or validation fields in later packets. |
| Exit IDs `fixed_holding`, `volatility_triple_barrier`, `funding_aware_exit_v1`, `knn_remaining_edge_exit_v1`, `hmm_transition_exit_v1`, `oi_contraction_exit_v1`, `liquidity_adverse_selection_exit_v1` | Current cycle supports `fixed_holding_window`, `triple_barrier`, `triple_barrier_atr`, `volatility_scaled_barrier`, `regime_flip_exit`, `funding_adverse_exit`, `alpha_decay_exit`, `adverse_selection_exit`, `trailing_atr_after_profit`, `max_mae_stop`. | Map to existing exits first. Add new exit IDs only in a dedicated exit-policy packet. |
| Strategy skeleton returns `timestamp`, `signal_side`, `signal_reason` | Current strategy contract requires `signal_time_ms`, `side`, `strength`, `confidence`, holding bounds, entry/exit policy, feature set, model version, `research_only`, etc. | Implement strategies by extending existing `RuleBasedStrategy` patterns and emitting `RuleSignal` rows. |
| Required liquidation/L2/cross-exchange data | Current durable provider fixture supports bars plus funding, premium, open interest; `agg_trade` is supported through archive ingestion. | Treat liquidation, L2 order book, and cross-exchange context as optional future packets gated by durable fixture availability. |
| Crypto Lake as a provider dependency | WPR47 established anonymous free-sample access only. Paid access, provider accounts, AWS profiles, and secret setup are intentionally out of scope. | Use Crypto Lake free sample only as an optional diagnostic fallback when Binance Vision/public Binance data is insufficient. Label outputs with `source_access_mode: free_sample`; do not use free samples as broad OOS/stress evidence by themselves. |
| External source-backed claims | Some API and literature claims may change or need verification. | Treat them as research context only. Empirical acceptance must come from repo artifacts and gates. |

## Provider Source Priority

Use this priority before adding new provider assumptions:

1. Existing durable fixture packs and checked manifests already in the repo.
2. Binance Vision public archives for broad historical bars, trades, and aggregate trades.
3. Binance USD-M public REST collectors for latest-window funding, premium, and open-interest context.
4. Crypto Lake anonymous free sample only as a diagnostic fallback when Binance Vision/public Binance sources are not enough for a specific local check.

Crypto Lake direct fetches must remain optional and credential-free. WPR47 verified local free-sample access for `BINANCE_FUTURES` `BTC-USDT-PERP` candles from 2025-04-06 to 2025-04-07: 1,440 rows, no gaps, no duplicates, and manifests labelled `source_access_mode: free_sample`.

Free-sample output is useful for collector compatibility, schema checks, and local fallback experiments. It cannot by itself satisfy broad provider coverage, multi-year OOS/stress validation, candidate-pack acceptance, or promotion gates.

## Data Family Alignment

Prefer existing family names unless there is a hard reason to add a new one.

| Curated family | Current or future status | Notes |
| --- | --- | --- |
| `primary_perp_bars` | Existing fixture primary bars, not a new context family. | Represented by fixture `bars_15m.parquet` and `cycle_dataset.parquet` today. Future 1h fixtures should still write the existing fixture contract. |
| `premium_index` | Existing supported context family. | Use for mark/index/premium features. It already supports `mark_price`, `index_price`, and premium aliases when present. |
| `funding_rate` | Existing supported context family. | Use for realized funding as-of features. Future funding cap/floor/interval rows can extend this or add `funding_info` after a contract packet. |
| `open_interest` | Existing supported context family. | Use for OI level/change features. |
| `agg_trade` | Existing supported context family from archive ingestion. | Use as first source for taker-flow features when durable archive rows exist. Do not require REST taker long/short endpoint initially. |
| `funding_info` | Future addition. | Add only after manifest and collector semantics are clear. Missing rows must not silently imply default cap/floor/interval values. |
| `long_short_ratios` | Future addition. | Useful for crowding, but retention-limited direct endpoints must be flagged. |
| `spot_context` | Future addition. | Needed for true spot/perp basis work and ETH/BTC residuals. Keep single-leg perp strategies named directional convergence proxies. |
| `liquidations` | Future addition. | Requires stream/vendor archive and stream-health evidence. Crypto Lake free sample may help diagnose schema support, but unknown windows are missing, not zero. |
| `l2_orderbook_optional` | Future addition. | Requires durable snapshots/events, depth aggregation, and stream-health evidence. |
| `cross_exchange_perp_context_optional` | Future addition. | Later cross-exchange context only; not part of the first BTC/ETH provider-backed pass. |

## Feature Set Naming

Use repo-style feature set IDs:

- Existing: `features_price_trend_vol`
- Existing: `features_full_context_no_wt`
- Existing: `features_full_context_wt3d`
- Existing: `features_perp_context_only`
- New curated target: `features_perp_context_v2`
- New optional variants after v2 exists:
  - `features_perp_context_v2_no_microstructure`
  - `features_perp_context_v2_no_wt`
  - `features_perp_context_v2_full_context`

Do not use unprefixed names such as `perp_context_v2` in cycle specs. The registry and configs should use `features_*` IDs.

Initial `features_perp_context_v2` should focus on features derivable from current durable families:

- Price and volatility columns from primary bars.
- Funding features from `funding_rate`.
- Premium/mark/index features from `premium_index`.
- Open-interest features from `open_interest`.
- Taker-flow features only when `agg_trade` context is present.
- Quality and missingness flags for each required and optional family.

Liquidation, order-book, and cross-exchange features stay omitted or explicitly missing/optional until durable fixtures exist.

## Strategy Naming And Contract Rules

New strategy IDs should follow existing `*_vN` style and be registered in:

- `src/tradingbotsuite/strategies/registry.py`
- `src/tradingbotsuite/strategies/parameters.py`
- `configs/strategies/<strategy_id>.json`

Initial implementation order:

1. `perp_basis_convergence_v2`
2. `funding_crowding_fade_v2`
3. `oi_flow_breakout_v2`
4. `funding_window_timing_v1`
5. `eth_btc_beta_residual_v1`, after ETH fixtures and cross-asset features exist
6. `hmm_routed_alpha_sleeves_v2`, after transparent sleeves have evidence
7. `hmm_knn_local_analog_filter_v2`, after HMM/router artifacts are stable
8. `liquidation_absorption_classifier_v1`, after liquidation fixtures are durable
9. `liquidity_adverse_selection_filter_v1`, after L2/order-book fixtures are durable
10. `cross_sectional_perp_crowding_v1`, after BTC/ETH-only research is stable

Every strategy must:

- Extend the existing strategy contract.
- Emit valid signal frames with current required columns.
- Allow only `long`, `short`, `flat`.
- Respect the 1h minimum and 7d maximum holding rules.
- Use only registered feature set IDs.
- Fail closed when required context is missing.
- Expose bounded parameter metadata.
- Preserve comparator coverage against `baseline_no_trade` and existing transparent baselines.

## Exit Policy Alignment

Use existing exit IDs first:

| Desired behavior | Current exit ID to use first | Later optional new ID |
| --- | --- | --- |
| Fixed time exit | `fixed_holding_window` | None needed. |
| Volatility/triple barrier | `triple_barrier_atr` or `volatility_scaled_barrier` | Only add if current policies cannot express the behavior. |
| Avoid adverse funding | `funding_adverse_exit` | `funding_aware_exit_v1` can be added later if it needs expected-alpha/funding tradeoff logic. |
| Regime transition exit | `regime_flip_exit` | `hmm_transition_exit_v1` later, after filtered HMM posterior is split-safe. |
| Momentum decay exit | `alpha_decay_exit` | `oi_contraction_exit_v1` complete in WPR58 for OI-specific contraction evidence. |
| Liquidity/adverse selection | `adverse_selection_exit` | `liquidity_adverse_selection_exit_v1` later, after L2 fixtures exist. |
| Trailing after profit | `trailing_atr_after_profit` | None initially. |
| MAE stop | `max_mae_stop` | Dynamic KNN barrier only after KNN evidence exists. |

Vector backtesting remains fixed-holding only unless a later vector engine packet explicitly expands supported exit scopes.

## Current Cycle Spec Template

Use this shape for first BTCUSDT cycles. Create a separate ETHUSDT spec with `symbol: "ETHUSDT"` after ETH fixtures exist.

```json
{
  "cycle_id": "btcusdt-perp-context-v2-foundation",
  "symbol": "BTCUSDT",
  "holding_windows": ["1h", "4h", "12h", "24h", "72h", "7d"],
  "data": {
    "dataset_manifest_paths": [
      "../../data/research/fixtures/btcusdt_context_provider_latest_month_v1/fixture_pack_manifest.json"
    ],
    "local_fixture_dir": null,
    "synthetic_fixture": false
  },
  "features": {
    "feature_sets": [
      "features_price_trend_vol",
      "features_full_context_no_wt",
      "features_perp_context_v2"
    ]
  },
  "strategies": [
    "baseline_no_trade",
    "trend_following_v1",
    "funding_basis_v1",
    "perp_basis_convergence_v2"
  ],
  "validation": {
    "walk_forward": "rolling_and_anchored",
    "purge_embargo_bars": 8,
    "stress_periods_required": true,
    "min_splits": 2,
    "trade_count_floor": 1,
    "max_single_split_pnl_share": 0.5,
    "min_cost_stress_survival_rate": 1.0,
    "split_modes": [
      "purged_embargoed_walk_forward",
      "anchored_walk_forward",
      "shifted_purged_walk_forward",
      "month_holdout",
      "stress_period_holdout",
      "regime_holdout"
    ]
  },
  "optimizer": {
    "method_sequence": ["coarse_lhs", "adaptive_grid", "stability_region_refine"],
    "max_candidates_per_strategy": 64,
    "top_regions_to_refine": 2
  },
  "exits": {
    "exit_policies": [
      {
        "exit_policy_id": "fixed_holding_window",
        "exit_policy_params": {},
        "exit_policy_source": "default_fixed_holding"
      },
      {
        "exit_policy_id": "funding_adverse_exit",
        "exit_policy_params": {
          "funding_threshold": 0.00005
        },
        "exit_policy_source": "configured_research_exit"
      },
      {
        "exit_policy_id": "volatility_scaled_barrier",
        "exit_policy_params": {
          "target_return": 0.015,
          "stop_return": 0.01
        },
        "target_return": 0.015,
        "stop_return": 0.01,
        "exit_policy_source": "configured_research_exit"
      }
    ]
  },
  "backtest_backend": "auto",
  "output_dir": "../../data/research/historical_cycles/btcusdt_perp_context_v2_foundation/run"
}
```

For normal tests, keep `min_splits` and `trade_count_floor` small enough to run locally. Do not interpret those local floors as candidate acceptance floors.

## Curated Implementation Roadmap

### WPR49-01 Perp Context Manifest Foundation

Goal: extend current context-family validation without altering historical-cycle behavior.

Allowed path families:

```text
src/tradingbotsuite/data/contracts.py
src/tradingbotsuite/data/historical_fixture_pack.py
src/tradingbotsuite/research/market_data.py
tests/contracts/
tests/tradingbotsuite/test_market_data_collection.py
tests/contracts/test_historical_fixture_pack_contract.py
docs/work_packets/
docs/stage_reports/
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

Required behavior:

- Preserve existing families: `funding_rate`, `premium_index`, `open_interest`, `agg_trade`.
- Preserve WPR47 Crypto Lake free-sample fallback semantics: no provider credentials, no AWS profile setup, and no paid-access assumptions.
- Add manifest metadata fields for retention and quality where non-breaking:
  - `retention_policy`
  - `coverage_scope`
  - `latest_window_only`
  - `context_family_role`
  - `stream_health` for future stream families
- Ensure direct latest-window context cannot support multi-year claims.
- Ensure `source_access_mode: free_sample` evidence remains diagnostic fallback evidence, not broad OOS/stress or promotion evidence.
- Keep synthetic context disallowed for provider-backed candidate evidence.
- Do not require liquidation/L2/cross-exchange context yet.

Exit validation:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_historical_fixture_pack_contract.py tests\contracts\test_data_contracts.py tests\tradingbotsuite\test_market_data_collection.py -q
```

### WPR50-01 Perp Context V2 Feature Pack

Goal: add `features_perp_context_v2` as a registered feature set built from current durable context families.

Allowed path families:

```text
src/tradingbotsuite/features/registry.py
src/tradingbotsuite/features/builders.py
src/tradingbotsuite/features/cache.py
configs/features/features_perp_context_v2.json
tests/features/
tests/contracts/test_feature_contracts.py
docs/work_packets/
docs/stage_reports/
docs/ORCHESTRATOR_STAGE_LEDGER.md
```

Initial feature columns:

```text
perp_mark_index_basis
perp_premium
perp_premium_z_7d
perp_premium_slope_8h
perp_last_funding_rate
perp_funding_z_7d
perp_funding_momentum
cal_time_since_last_funding_h
cal_time_to_next_funding_h
oi_notional
oi_delta_1h
oi_delta_z_7d
oi_volume_ratio
flow_buy_sell_ratio
flow_signed_taker_notional
flow_signed_taker_z_7d
quality_context_missing_count
quality_has_funding_gap
quality_has_oi_gap
quality_has_premium_gap
quality_provider_backed_all_required
quality_latest_window_context_only
```

Rules:

- Every feature must be completed-bar aligned.
- Every context join must be backward-as-of.
- Funding settled after a bar close cannot appear in that row.
- Missing optional context is represented as `NaN` plus quality flags, not silent zero.
- Feature-cache identity must include context-family hashes.

Exit validation:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_feature_contracts.py tests\features -q
```

### WPR51-01 Perp Basis Convergence Strategy

Goal: add the first transparent perp strategy, `perp_basis_convergence_v2`.

Allowed path families:

```text
src/tradingbotsuite/strategies/perp_basis_convergence.py
src/tradingbotsuite/strategies/registry.py
src/tradingbotsuite/strategies/parameters.py
src/tradingbotsuite/strategies/__init__.py
configs/strategies/perp_basis_convergence_v2.json
tests/contracts/test_strategy_contracts.py
tests/integration/test_backtest_engine_fixture.py
tests/historical/
docs/work_packets/
docs/stage_reports/
docs/ORCHESTRATOR_STAGE_LEDGER.md
```

Contract requirements:

- Extend `RuleBasedStrategy`.
- `strategy_id = "perp_basis_convergence_v2"`.
- `allowed_holding_periods = ("4h", "12h", "24h", "72h")` initially.
- `required_feature_sets = ("features_perp_context_v2",)`.
- Use `RuleSignal` outputs through the existing helper.
- Fail closed when required feature columns or quality flags are missing.
- Add bounded metadata for:
  - `basis_vol_threshold`
  - `premium_z_threshold`
  - `min_edge_bps`
  - `funding_policy`
  - `spacing_bars`
  - optional `spread_z_max` only after book features exist

Entry concept:

```text
Long directional convergence proxy:
  basis is sufficiently negative, premium z-score is sufficiently negative,
  absolute carry-adjusted basis exceeds estimated costs plus min edge,
  required context quality is valid.

Short directional convergence proxy:
  basis is sufficiently positive, premium z-score is sufficiently positive,
  absolute carry-adjusted basis exceeds estimated costs plus min edge,
  required context quality is valid.
```

Do not call this arbitrage. Single-leg perp trades are directional convergence proxies.

Exit validation:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_strategy_contracts.py tests\integration\test_backtest_engine_fixture.py -q
```

### WPR52-01 Provider Perp Context Cycle Evidence

Goal: run BTCUSDT provider-backed historical cycles with `features_perp_context_v2` and `perp_basis_convergence_v2`.

Allowed path families:

```text
configs/research/full_cycle_btcusdt_perp_context_v2.json
data/research/historical_cycles/btcusdt_perp_context_v2_foundation/**
tests/historical/
tests/contracts/test_research_cycle_contract.py
docs/work_packets/
docs/stage_reports/
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

Rules:

- Use non-synthetic provider fixture evidence.
- Prefer durable repo fixtures and Binance public sources. Use Crypto Lake free sample only for fallback diagnostics unless a later packet explicitly turns expanded free-sample coverage into durable fixture evidence.
- Candidate gates remain fail-closed.
- No candidate pack is expected unless all existing gates pass.
- Record if candidates are blocked; blocked is acceptable and truthful.
- Do not claim OOS acceptance or promotion readiness.

Exit validation:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py tests\historical -q
```

### WPR53 And Later

Add only after WPR49-WPR52 are stable:

1. `funding_crowding_fade_v2`
2. `oi_flow_breakout_v2`
3. ETHUSDT fixture and mirror cycle - complete in WPR56 with a 2,810-row latest-window ETHUSDT provider fixture and checked mirror cycle
4. `funding_adverse_exit` improvements or new `funding_aware_exit_v1` - complete in WPR57 with `funding_aware_exit_v1` checked in BTCUSDT and ETHUSDT cycles
5. `oi_contraction_exit_v1` - complete in WPR58 with `oi_contraction_exit_v1` checked in BTCUSDT and ETHUSDT cycles
6. Trial-budget and overfit-adjustment reports - complete in WPR59 as diagnostic-only required research-cycle outputs without changing candidate-pack metric gates
7. Split-safe HMM router - complete in WPR60 as `hmm_routed_alpha_sleeves_v2`, a research-only strategy that consumes split-safe posterior columns and is not wired into checked provider cycles until posterior materialization exists
8. Split-safe KNN local analog filter - complete in WPR61 as `hmm_knn_local_analog_filter_v2`, a research-only strategy that consumes split-safe KNN/HMM artifact columns and is not wired into checked provider cycles until KNN prediction materialization exists
9. Liquidation fixture intake foundation - complete in WPR62 for Crypto Lake/local archive normalization and optional fixture-pack materialization; `liquidation_absorption_classifier_v1` remains gated on liquidation features or checked fixture evidence
10. L2 liquidity filter after durable order-book fixtures
11. Cross-exchange/cross-sectional context after BTC/ETH cycles are stable

## Future Data Guardrails

These guardrails apply before any future family can support empirical claims:

- Direct latest-window endpoints must be flagged and cannot support multi-year claims.
- Stream data must include stream-health evidence.
- Unknown stream windows are missing, not zero.
- Lower-timeframe data can support context or exit sequencing but does not relax the 1h minimum hold.
- External/vended data must still write normalized manifests, hashes, row counts, coverage, and research-only flags.
- Crypto Lake free-sample evidence must be labelled with `source_access_mode: free_sample` and treated as diagnostic fallback unless a later packet proves durable coverage.
- A source paper or API page is not branch evidence; only generated provider-backed artifacts and gates are evidence.

## Future Validation And Gate Enhancements

The downloaded plan's trial-budget and overfit-control ideas are useful, but they should be additive:

- Add `trial_budget_report.json` as a new required report only after the report writer and candidate-pack validator support it.
- Add `overfit_adjustment_report.json` after metrics and trial accounting are stable.
- Deflated Sharpe, PBO, and CPCV should be reported as research diagnostics first, not hard pack gates on the first implementation.
- If added to candidate-pack gates, keep fail-closed behavior and add focused tests before running provider cycles.

## First Agent Prompt

Use this prompt after opening WPR49:

```text
You are implementing research-only extensions for TradingBotSuite branch research/v3-experimental-engine.

Read first:
- AGENTS.md
- docs/ORCHESTRATOR_STAGE_LEDGER.md
- docs/RESEARCH_BRANCH_DISTILLATION.md
- docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md
- docs/runbooks/crypto_lake_free_data_runbook.md

Task:
Implement WPR49-01 Perp Context Manifest Foundation.

Constraints:
- Preserve research_only=true, observe_only=true, promotion_ready=false.
- Do not touch live execution or promotion paths except to preserve rejection boundaries.
- Do not introduce a new cycle spec shape.
- Do not add liquidation, L2, cross-exchange, or multi-symbol cycle behavior in this packet.
- Do not add Crypto Lake paid access, provider-account setup, AWS profile setup, or secret material.
- Keep changes inside the work packet allowed paths.

Required behavior:
- Preserve existing context families: funding_rate, premium_index, open_interest, agg_trade.
- Preserve WPR47 Crypto Lake free-sample fallback semantics and `source_access_mode: free_sample` labelling.
- Add non-breaking manifest metadata for retention/coverage/quality where appropriate.
- Ensure latest-window context cannot masquerade as multi-year provider-backed evidence.
- Ensure synthetic context cannot support provider-backed empirical claims.
- Add tests for manifest retention flags and fail-closed fixture validation.

Validation:
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_historical_fixture_pack_contract.py tests\contracts\test_data_contracts.py tests\tradingbotsuite\test_market_data_collection.py -q
```

## Non-Trivial Changes Requiring Dedicated Approval

These are intentionally not part of the first stages:

- Multi-symbol `HistoricalResearchCycleSpec`.
- Adding `8h` as a supported holding window.
- Making vector backtesting support non-fixed-holding exits.
- Making new overfit reports mandatory candidate-pack gates.
- Treating liquidation, L2, or cross-exchange data as required context.
- Adding production speed or profitability claims.
- Adding provider-account, AWS-profile, or secret-backed Crypto Lake collection.
- Any promotion, paper, shadow, testnet, canary, live, or order-placement workflow.

## Minimum Close Evidence Per Packet

Every future packet must close with:

- Work packet document.
- Code changes only inside allowed paths.
- Tests or explicit reason tests are not applicable.
- Validation commands and results.
- Artifact schema updates if needed.
- Stage report and close evidence.
- Ledger update.
- Rejection/fail-closed behavior verified.
