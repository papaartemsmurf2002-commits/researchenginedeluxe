# Stage R66 Interval-Aware Feature Building Report

Date: 2026-05-05
Work packet: `docs/work_packets/WPR66-01-interval-aware-feature-building.md`

## Summary

R66 makes historical research-cycle feature building interval-aware. The cycle
runner now resolves the primary bar interval from loaded fixture/source
metadata before building registered feature sets, so 1m fixture packs no longer
flow through the 15m default.

This stage does not wire liquidation features or strategies into checked
BTCUSDT/ETHUSDT provider-cycle configs, does not create candidate-pack
eligibility, and does not change promotion or live behavior.

## Implementation

- Added cycle-local interval evidence resolution in
  `src/tradingbotsuite/research_cycle/runner.py`.
- Resolution order:
  1. fixture/data-source `base_interval`,
  2. constant dataset `source_interval`,
  3. uniform bar-time diff,
  4. existing 15m default only when no interval evidence exists.
- Passed the resolved interval into:
  - `FeatureCacheIdentity.interval_ms`,
  - `materialize_registered_feature_set(..., interval_ms=...)`.
- Added manifest fields:
  - `primary_interval_ms`,
  - `primary_interval_source`,
  - `declared_base_interval`,
  - `dataset_source_interval`,
  - `inferred_bar_interval_ms`,
  - per-feature-set `interval_ms`.

Unsupported declared intervals and clear declared-vs-observed mismatches now
fail before feature-cache reuse or feature materialization.

## Evidence

Contract coverage now confirms the liquidation classifier candidate family has
complete no-trade baseline comparator coverage.

Historical cycle coverage now runs the WPR64 BTCUSDT Crypto Lake free-sample
liquidation fixture through a tmp-output research cycle with
`features_liquidation_context_v1` and `liquidation_absorption_classifier_v1`.
The regression verifies:

- fixture `base_interval: 1m`,
- feature-build `primary_interval_ms: 60000`,
- feature-cache `interval_ms: 60000`,
- materialized `feature_time_ms - bar_time_ms == 60000`,
- liquidation feature columns are present and populated,
- provenance remains `source_access_mode: free_sample`, diagnostic-only,
  research-only, observe-only, and not promotion-ready,
- no candidate pack is written.

Existing 15m fixture tests continue to assert `primary_interval_ms: 900000`.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
```

Passed.

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py -q
```

Passed: 26 passed.

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_local_fixture_pack.py -q
```

Passed: 11 passed.

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Passed: 367 passed.

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\features\test_feature_builders.py -q
```

Passed: 20 passed.

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\historical -q
```

Passed: 35 passed.

## Next Gate

The interval-aware blocker is resolved. Remaining work, if desired, is separate:
either add checked local liquidation cycle artifacts/configs or later wire
durable liquidation context into broader BTCUSDT/ETHUSDT provider cycles. That
future work must keep WPR64 free-sample evidence diagnostic-only and must not
claim OOS/stress acceptance, promotion readiness, or live readiness.
