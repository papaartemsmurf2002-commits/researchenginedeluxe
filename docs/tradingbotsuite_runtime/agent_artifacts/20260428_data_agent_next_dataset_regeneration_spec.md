# Data Agent Artifact: Next BTC Dataset Regeneration Spec

## Agent Name
Data Agent

## Task Received
Design the next real BTC dataset regeneration pass. Review the real BTC lineage quality artifact, identify which missing fields most likely hurt the HMM-routed KNN architecture, and draft exact regeneration requirements for raw fields, missingness thresholds, minimum row count, time span, and manifest fields. Do not fetch live data unless explicitly authorized.

## Files Read
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_real_btc_lineage_quality.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_INPUT_LOOKUP.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_REALIZATION_PLAN.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_RUNBOOK.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_SOURCE_LOG.md`
- `configs/v2_btc_hmm_multi_knn_research.json`
- `data/research/v2-btc-research-1/dataset_manifest.json`

## Files Changed
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_next_dataset_regeneration_spec.md`

## Commands Run
- `rg -n "missing_open_interest|missing_basis_bps|missing_spread_bps|missing_top_of_book|missing_queue|missing_primary" docs\tradingbotsuite_runtime`

## Current Dataset Baseline
The reviewed real BTC dataset is:

- Dataset path: `data/research/v2-btc-research-1/btcusdt_dataset.parquet`
- Rows: `1173`
- Columns: `105`
- Symbol scope: `BTCUSDT`
- Dataset feature version: `v2-btc-acceptance-2`
- HMM/KNN plan version: `v2-btc-hmm-multi-knn-1`
- HMM/KNN evaluation rows reported by lineage review: `446`

The dataset is useful for local diagnostics, but not strong enough for production-quality research claims. Funding context is present, but OI, basis, premium basis, spread, signed flow, top-of-book imbalance, and queue imbalance are either mostly missing or fully placeholder-level.

## Architecture Impact Ranking
The missing fields most likely to hurt the HMM-routed KNN architecture are ranked below by direct model contract impact and by whether they represent a distinct edge family.

1. Signed flow / taker imbalance
   - Fields: `primary_signed_imbalance_ratio`, `primary_sqrt_signed_imbalance_ratio`, `primary_trade_sign_acf_lag1`, `primary_flow_price_alignment_bps`, `primary_impact_efficiency_bps_per_sqrt_notional`
   - Current state: fully missing in the real BTC lineage review.
   - Impact: critical. These fields are core order-flow analogs for confirming whether a TradingView entry has real aggressor support. They affect KNN neighborhood quality, meta-filter acceptance, and the distinction between continuation and mean-reversion setups.

2. Top-of-book and queue imbalance
   - Fields: `top_of_book_imbalance`, `queue_imbalance_l1`, `queue_imbalance_l5`, `queue_imbalance_l10`
   - Current state: fully missing.
   - Impact: critical. HMM emissions and KNN features expect liquidity pressure information. Without these fields, the model cannot distinguish a clean signal from one crossing into depleted or adverse book conditions.

3. Spread
   - Field: `spread_bps`
   - Current state: fully missing.
   - Impact: critical. Spread is required for cost-aware filtering, slippage realism, and no-trade rules. A signal that only works when spread is ignored is not acceptable for research promotion.

4. Open interest and OI change
   - Fields: `open_interest`, `open_interest_change`, `open_interest_change_pct`, `open_interest_value`
   - Current state: about `87.47%` missing in the real BTC manifest.
   - Impact: high. OI change is part of the HMM emission set and KNN perp-structure feature set. Missing OI weakens regime routing and hides whether moves are spot-led, perp-led, or short-covering/liquidation-like.

5. Basis and premium basis
   - Fields: `basis_bps`, `premium_basis_rate`, `premium_basis_abs`, mark/index context
   - Current state: `basis_bps`, `premium_basis_rate`, and `premium_basis_abs` are fully missing or placeholder-level; premium close exists but is not enough by itself.
   - Impact: high. Basis/premium context is required to separate healthy continuation from crowded perp positioning and funding/premium stress.

6. Funding
   - Fields: `funding_rate`, `funding_rate_change`, funding timing and funding paid/received label context
   - Current state: present in the reviewed dataset.
   - Impact: still required. Funding should remain a mandatory context family because the model spec treats perp edge as first-class, but it is not the largest current gap.

## Regeneration Requirements

### Scope
- Asset scope must be BTC-only: `BTCUSDT`.
- `research_only` must remain `true`.
- Do not fetch or generate ETH rows in this pass.
- Source decision rows must remain TradingView-origin BTCUSDT research signals from local SQLite/imported research sources.
- No live gate, execution adapter, Hyperliquid behavior, sizing, or operator control changes are in scope.

### Source Authorization
- This spec does not authorize live data fetches.
- If a future run is explicitly authorized to fetch data, use only repo-supported BTC Binance extraction instruments for historical klines, funding, premium/index/mark, and open interest where available.
- Binance Vision and Crypto Lake style order-flow extraction are not currently instrumented in this repo. Do not silently add those external sources under this pass.
- Current-only websocket state must not be used to reconstruct old rows. Historical microstructure may only come from captured decision packets or explicitly historical local/source archives.

### Minimum Row Count
- Hard minimum labeled dataset rows: `>= 1000`, so the next pass does not regress below the current `1173` rows.
- Target labeled dataset rows: `>= 3000` if local signal/source history supports it.
- Hard minimum HMM/KNN evaluation rows after split/purge/warmup: `>= 400`.
- Target HMM/KNN evaluation rows after split/purge/warmup: `>= 750`.
- If source history cannot meet the target, write the dataset anyway only if the hard minimum is met, and record `insufficient_signal_history: true` in the manifest.

### Time Span
- Hard minimum signal span: `>= 90` calendar days.
- Target signal span: `>= 180` calendar days.
- Hard minimum OHLCV context coverage: at least `8640` 15-minute bars, equivalent to about 90 days.
- Target OHLCV context coverage: full available local BTCUSDT history needed to cover the signal span plus feature warmup and label horizons.
- Feature timestamps must be point-in-time aligned to the signal bar close.
- Future bars may be used only for labels and only after the feature cutoff.
- Label horizons must remain compatible with the configured research horizons: `6h`, `24h`, `72h`, and `7d`.

## Required Raw Fields

### Signal And OHLCV Audit Fields
Every row must carry auditable signal-bar and feature-cutoff fields:

- `symbol`
- `signal_time_ms`
- `signal_bar_open_time_ms`
- `signal_bar_close_time_ms`
- `signal_bar_open`
- `signal_bar_high`
- `signal_bar_low`
- `signal_bar_close`
- `signal_bar_volume`
- `historical_feature_end_time_ms`
- `label_future_start_time_ms`
- `label_future_end_time_ms`
- `label_future_bar_count`

### TradingView Provenance Fields
Every row must preserve the TradingView/research signal lineage:

- `source`
- `source_mode`
- `strategy_version`
- `import_batch_id`
- `source_row_number`
- `raw_signal_payload_json`
- `feature_snapshot_json`
- `decision_context_present`

### Funding Fields
Required raw and normalized funding context:

- `raw_funding_rate`
- `raw_funding_rate_change`
- `raw_time_to_next_funding_ms`
- `funding_rate`
- `funding_rate_change`
- `time_to_next_funding_ms`
- `missing_funding_rate`
- `missing_funding_rate_change`
- `funding_context_json`
- funding source, error, and backoff summary fields in the manifest

### Open Interest Fields
Required raw and normalized OI context:

- `raw_open_interest`
- `raw_open_interest_change`
- `raw_open_interest_change_pct`
- `raw_open_interest_value`
- `open_interest`
- `open_interest_change`
- `open_interest_change_pct`
- `open_interest_value`
- `missing_open_interest`
- `missing_open_interest_change`
- `missing_open_interest_change_pct`
- `missing_open_interest_value`
- `open_interest_context_json`
- OI source, error, and backoff summary fields in the manifest

### Basis And Premium Fields
Required raw and normalized basis/premium context:

- `raw_mark_price`
- `raw_index_price`
- `raw_basis_bps`
- `raw_premium_close`
- `raw_premium_basis_rate`
- `raw_premium_basis_abs`
- `basis_bps`
- `premium_close`
- `premium_basis_rate`
- `premium_basis_abs`
- `missing_mark_price`
- `missing_index_price`
- `missing_basis_bps`
- `missing_premium_close`
- `missing_premium_basis_rate`
- `missing_premium_basis_abs`
- `basis_context_json`
- `premium_context_json`
- premium/basis source, error, and backoff summary fields in the manifest

### Microstructure And Signed Flow Fields
Required raw and normalized microstructure fields:

- `raw_primary_signed_imbalance_ratio`
- `raw_primary_sqrt_signed_imbalance_ratio`
- `raw_primary_trade_sign_acf_lag1`
- `raw_primary_flow_price_alignment_bps`
- `raw_primary_impact_efficiency_bps_per_sqrt_notional`
- `raw_top_of_book_imbalance`
- `raw_queue_imbalance_l1`
- `raw_queue_imbalance_l5`
- `raw_queue_imbalance_l10`
- `raw_spread_bps`
- `primary_signed_imbalance_ratio`
- `primary_sqrt_signed_imbalance_ratio`
- `primary_trade_sign_acf_lag1`
- `primary_flow_price_alignment_bps`
- `primary_impact_efficiency_bps_per_sqrt_notional`
- `top_of_book_imbalance`
- `queue_imbalance_l1`
- `queue_imbalance_l5`
- `queue_imbalance_l10`
- `spread_bps`
- matching `missing_*` flags for every normalized field above
- `microstructure_context_json`
- microstructure source, error, and backoff summary fields in the manifest

### Label Contract Fields
The regenerated dataset must keep label fields auditable and excluded from feature inputs:

- `label_accept`
- `label_pnl_multiple`
- `label_exit_reason`
- `label_exit_price`
- `label_exit_time_ms`
- `gross_return`
- `fees_bps`
- `slippage_bps`
- `funding_paid_or_received`
- `time_in_trade`
- `time_in_trade_bars`
- `max_adverse_excursion`
- `max_favorable_excursion`
- `barrier_hit_type`

No label outcome column may appear in HMM emission features, KNN feature columns, scaler inputs, or meta-filter feature inputs.

## Missingness Thresholds
Missing raw exchange context must remain `null` in raw fields. Normalized numeric model fields may be zero-filled only when paired with matching `missing_*` flags.

| Context family | Target missing rate | Maximum acceptable | Fail threshold |
| --- | ---: | ---: | ---: |
| Funding | `<= 2%` | `<= 5%` | `> 5%` |
| Open interest / OI change | `<= 20%` | `<= 35%` | `> 50%` |
| Basis / premium basis | `<= 10%` | `<= 20%` | `> 35%` |
| Spread | `<= 15%` | `<= 25%` | `> 40%` |
| Top-of-book / queue imbalance | `<= 15%` | `<= 25%` | `> 40%` |
| Signed flow / taker imbalance | `<= 15%` | `<= 25%` | `> 40%` |

If a family fails its threshold, the dataset may still be written for diagnostics, but the manifest must mark it as research-diagnostic quality rather than model-promotion quality.

## Manifest Requirements
The next manifest must include or preserve:

- `research_only: true`
- `asset_scope`
- `symbol`
- `dataset_manifest_version`
- `plan_version`
- `plan_sha256`
- `dataset_sha256`
- `dataset_path`
- `row_count`
- `column_count`
- `feature_version`
- `label_version`
- `label_outcome_fields`
- `feature_input_columns`
- `hmm_emission_features`
- `knn_feature_columns`
- `meta_feature_columns`
- `source_counts`
- `source_mode_counts`
- `strategy_version_counts`
- `class_balance`
- `missing_feature_rates`
- `raw_context_available_counts`
- `exchange_context_summary`
- `context_source_coverage`
- `planned_split_summary`
- `time_span`
- `quality_gates`
- `dataset_quality_summary`

### Required Manifest Summaries
`raw_context_available_counts` must report available and missing counts for at least:

- funding
- open interest
- open interest change
- mark/index basis
- premium basis
- spread
- top-of-book imbalance
- queue imbalance
- signed flow

`exchange_context_summary` must report, per context family:

- source name
- source mode: local cache, historical endpoint, captured decision packet, or unavailable
- attempted count
- successful count
- unavailable count
- error count
- backoff count
- earliest context timestamp
- latest context timestamp
- point-in-time cap field, such as `as_of_ms`
- current-only fallback count, which must be `0` for old historical rows

`quality_gates` must include pass/warn/fail status for:

- row count
- time span
- BTC-only scope
- label contract
- no label leakage into features
- funding missingness
- OI missingness
- basis/premium missingness
- spread missingness
- top-of-book/queue missingness
- signed-flow missingness
- point-in-time alignment

## Point-In-Time Safety Checks
The regeneration pass must prove:

- Feature OHLCV windows end at or before `signal_bar_close_time_ms`.
- Funding, OI, premium, basis, and microstructure context are selected with `as_of_ms <= signal_bar_close_time_ms`.
- No feature value is derived from future bars used for labels.
- `label_exit_time_ms` is greater than the feature cutoff and less than or equal to `label_future_end_time_ms`.
- Historical rows do not use current-only Binance endpoint snapshots.
- Captured decision-packet microstructure is allowed only when the packet existed at or before signal time.

## Decisions Made
- The next regeneration pass should prioritize signed flow, queue/top-of-book imbalance, spread, OI, and basis/premium coverage before treating model metrics as meaningful.
- Funding coverage is acceptable in the current dataset but remains mandatory in the raw and manifest contracts.
- Missing raw context must remain `null`; normalized zero-fill is acceptable only with explicit `missing_*` flags.
- The next dataset can be emitted as diagnostic even if quality gates fail, but the manifest must make that failure explicit.
- No live data fetch is authorized by this task.

## Assumptions
- BTCUSDT remains the only Phase 1 asset.
- Existing repo Binance instruments may be used in a later explicitly authorized regeneration pass for BTC historical context where they support historical extraction.
- Binance Vision and Crypto Lake style order-flow archives are not available through current repo instruments.
- Local TradingView-origin source rows remain the canonical signal source.

## Open Issues Or Blockers
No new open issue was added. The main limitation is procedural rather than ambiguous: a real regeneration pass that improves OI, basis, premium, spread, queue, top-of-book, or signed-flow coverage requires explicit authorization to use historical extraction beyond existing local files.

## Handoff Notes For Other Agents
- Model Agent: do not interpret current HMM/KNN metrics as edge evidence while signed flow, queue/top-of-book, spread, basis, and OI coverage fail the thresholds above.
- Data Agent: implement manifest `quality_gates`, `raw_context_available_counts`, and per-family `exchange_context_summary` before running a promotion candidate.
- Testing Agent: add assertions that every raw unavailable field remains null and every normalized substitute has a matching `missing_*` flag.
- Ops/Live Agent: no live routing, execution, sizing, or operator behavior should depend on this research dataset until the manifest reports promotion-quality coverage.
