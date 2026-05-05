# Stage R63 Liquidation Context Feature Pack Report

Date: 2026-05-05
Branch: `research/v3-experimental-engine`
Work packet: `docs/work_packets/WPR63-01-liquidation-context-feature-pack.md`
Status: closed

## Scope

R63 added `features_liquidation_context_v1` as a registered research-only feature set backed by `liquidation_context_v1`. The feature set consumes optional WPR62 liquidation fixture context and emits conservative, point-in-time liquidation features for later research.

It does not implement `liquidation_absorption_classifier_v1`, wire liquidation features into checked BTCUSDT/ETHUSDT cycles, add candidate-pack eligibility, change optimizer gates, import live adapters, or create promotion/live evidence.

## Feature Semantics

- Feature set ID: `features_liquidation_context_v1`.
- Feature pack ID: `liquidation_context_v1`.
- Input family: `liquidation`.
- Feature columns:
  - `liq_event_count_1h`
  - `liq_total_notional_1h`
  - `liq_buy_notional_1h`
  - `liq_sell_notional_1h`
  - `liq_net_notional_1h`
  - `liq_imbalance_ratio_1h`
  - `liq_total_notional_z_7d`
  - `liq_time_since_last_event_h`
  - `liq_absorption_reclaim_bps`
  - `quality_has_liquidation_gap`
  - `quality_liquidation_provider_backed`
  - `quality_liquidation_latest_window_context_only`

## Materialization Semantics

Liquidation context is materialized with event-window semantics rather than stateful backward-as-of carry-forward. For each cycle bar, the materializer aggregates liquidation events with event times inside the prior 1h window and at or before the bar time.

Rows without in-window liquidation evidence remain `NaN` with explicit missingness and `quality_has_liquidation_gap = 1.0`. The feature builder does not zero-fill unknown liquidation windows.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_feature_contracts.py tests\features -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- Full compile passed.
- WPR63 focused feature suite: 31 passed.
- Full contract suite: 336 passed.

## Research Boundary

This stage does not add live signals, promotion readiness, paper/shadow/testnet/canary behavior, live configuration writes, order placement, position sizing, runtime mode changes, or performance claims.

## Next Stage

Checked liquidation fixture evidence should come before checked cycle wiring, classifier work, backtest claims, candidate-pack eligibility, or any live/promotion interpretation.
