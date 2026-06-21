# V2 Backtest Engine Contract

Status: v2 Phase 16 vectorized and event-driven engine contract
Audit IDs: `V2-AUD-BTENG-001`, `V2-AUD-BTENG-002`, `V2-AUD-COST-001`, `V2-AUD-BTENG-006`

## Purpose

Backtest engines turn validated data-service panels and strategy specs into
research-only run artifacts.

## Schema Names

- `BacktestRunConfig`
- `RunManifest`
- `StrategyContext`
- `BacktestMetrics`
- `BacktestRunResult`
- `EngineLane`
- `MissingDataPolicy`
- `ValidationStatus`
- `CostModelConfig`
- `CostStressScenario`

## Required Rules

- Vectorized and event-driven lanes share run artifact contracts.
- Engines record fill assumptions, latency, fees, funding, spread, slippage,
  impact, capacity assumptions, and rejected/blocked reasons.
- Same-bar optimism is forbidden unless explicitly modeled and labeled.
- Run outputs are research-only and non-promotable.
- The initial Phase 11 vectorized engine runs validated declarative strategy
  specs over caller-supplied local/in-memory panels.
- Durable `vectorized_backtest` worker jobs must use `BacktestDataService` as
  the archive-backed panel source and must not bypass 2024+, six-month,
  coverage, as-of universe, or lockbox preflight gates.
- `StrategyContext` records archive snapshot, universe snapshot, data
  manifest, validation policy, cost model, timeframe, universe mode, venue
  scope, backtest window, lockbox policy, and coverage floor.
- The initial explicit price bases are:
  - `next_bar_open`: previous signal is applied to the current bar open-to-close
    return;
  - `close`: previous signal is applied to close-to-close returns;
  - `mark` and `oracle`: previous signal is applied to corresponding
    mark/oracle price returns.
- Missing data policy is explicit and fail-closed. Multi-instrument runs must
  share a common timestamp clock; missing instrument rows produce failed run
  artifacts.
- Metrics must include gross and net returns, final gross/net equity, fee cost,
  spread cost, slippage cost, impact cost, total transaction cost, funding PnL,
  turnover, trade count, capacity-blocked count, and position row count.
- Base vectorized runs write `cost_stress.parquet` with `base`, `stress_2x`,
  and `stress_3x` rows. Stress rows reuse the same panel/signals and multiply
  transaction-cost assumptions while leaving funding PnL explicit.
- Cost manifests record cost model ID/hash, fee/funding/slippage/spread/impact
  assumptions, capacity cap, stress matrix, and cost sensitivity.
- Trade artifacts record the requested exit-policy ID and a canonical
  exit-policy ID. Fixed-holding aliases canonicalize to
  `fixed_holding_window`; the legacy `volatility_scaled_barrier` request
  canonicalizes to `static_primary_close_barrier` until a true as-of
  volatility-scaled barrier encodes estimator/window/scale/timeframe/clipping
  metadata.
- Lower-timeframe triple-barrier exits use lower-frame OHLC rows for both
  barrier hits and no-hit time exits. No-hit exits use the last completed
  lower-frame close at or before the scheduled horizon and fail closed when
  lower-frame horizon coverage is stale or missing.
- GMM transition exits require detector metadata for train window, inference
  window, feature version, parameter hash, and artifact hash before they can
  be accepted as regime-context evidence.
- Funding costs are applied from the timestamped in-trade funding path when
  funding rows are available, not from a single entry-row estimate.
- Volume participation cap breaches fail closed with required failure
  artifacts.
- Gross-only reported/accepted metrics are rejected.
- Event-driven Phase 16 behavior is a fixture-only skeleton lane. It validates
  local trade/BBO/L2 event rows, sorts the event queue deterministically, writes
  the same required artifacts as vectorized runs, and remains research-only.
- The event-driven skeleton does not place orders, claim live/paper readiness,
  or provide realistic queue/fill proof.
- Maker or mixed maker/taker assumptions are blocked unless queue-model
  metadata is explicitly documented.
- The older event-driven placeholder remains available for explicit blocked
  artifact-contract tests.
- Runs must be reproducible from `run_manifest.json`, `strategy_spec.json`,
  `params.json`, and the same input panel.

## Forbidden

- Direct venue/API reads.
- Order placement or runtime execution.
- Gross-only advancement.
- Silent forward-fill of PnL-critical prices.
- Event-driven fill realism or order-readiness claims from the Phase 16
  skeleton lane.
