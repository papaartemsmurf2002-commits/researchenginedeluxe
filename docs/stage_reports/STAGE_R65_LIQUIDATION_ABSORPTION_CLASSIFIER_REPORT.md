# Stage R65 Liquidation Absorption Classifier Report

Date: 2026-05-05
Work packet: `docs/work_packets/WPR65-01-liquidation-absorption-classifier.md`

## Summary

R65 adds `liquidation_absorption_classifier_v1` as a research-only transparent
strategy. It consumes `features_liquidation_context_v1` and emits standard
strategy signals only when liquidation context is provider-backed, non-gap,
non-latest-window by default, abnormal by 7d notional z-score, directionally
imbalanced, recent, and followed by positive absorption reclaim.

This stage does not wire the strategy into checked BTCUSDT or ETHUSDT
provider-cycle configs, does not create candidate-pack eligibility, and does
not change promotion or live behavior.

## Implementation

- Strategy module:
  `src/tradingbotsuite/strategies/liquidation_absorption_classifier.py`.
- Strategy ID: `liquidation_absorption_classifier_v1`.
- Feature set: `features_liquidation_context_v1`.
- Holding periods: `1h`, `4h`, `12h`, `24h`.
- Config:
  `configs/strategies/liquidation_absorption_classifier_v1.json`.
- Metadata parameters:
  - `notional_z_threshold`
  - `imbalance_abs_threshold`
  - `reclaim_bps_threshold`
  - `min_event_count`
  - `max_event_age_h`
  - `allow_latest_window_context`
  - `spacing_bars`
- `baseline_no_trade` now supports `features_liquidation_context_v1` for later
  comparator coverage.

Accepted trade signals keep `skip_reason` empty so backtest engines do not
filter them as skipped rows.

## Evidence

Contract tests cover:

- registry and config loading,
- invalid holding-window and feature-set rejection,
- metadata coverage,
- research-only signal output,
- required-column fail-closed behavior,
- unsafe context and invalid-parameter fail-closed behavior,
- explicit latest-window opt-in behavior,
- WPR64 checked fixture materialization and classifier execution.

WPR64 fixture evidence remains Crypto Lake anonymous free-sample diagnostic
evidence. It supports local classifier development and tests only; it is not
broad OOS/stress evidence, candidate-pack eligibility, promotion evidence, live
signal evidence, or a performance claim.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
```

Passed.

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_strategy_contracts.py -q
```

Passed: 267 passed.

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Passed: 366 passed.

## Next Gate

The next practical packet should first address interval-aware research-cycle
feature building for 1m fixture packs or build a 15m liquidation fixture. Do not
force WPR64 through the current historical-cycle runner yet, because current
cycle feature building assumes the 15m default interval. Checked BTCUSDT/ETHUSDT
provider-cycle wiring should stay separate until local cycle behavior is
validated and evidence limitations remain explicit.
