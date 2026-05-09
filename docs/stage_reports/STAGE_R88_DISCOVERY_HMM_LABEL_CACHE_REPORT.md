# Stage R88 Discovery HMM Label Cache Report

Date: 2026-05-09
Packet: `docs/work_packets/WPR88-01-discovery-hmm-label-cache.md`

## Scope

WPR88 reduces repeated work in real discovery runs by caching label/split
preparation and reusing split-safe HMM materializations across label horizons.
It does not change research gates, live behavior, promotion readiness, or
strategy semantics.

## Changes

- Added an in-run label/split cache keyed by feature-column set, horizon,
  interval, row window, and split settings.
- Removed label horizon from the HMM cache key because HMM regime fitting uses
  feature columns, HMM settings, and split settings, not future-return labels.
- Reused HMM cache entries are grafted onto the current horizon-labeled frame,
  preserving `label_up` and `label_return` for the KNN trial being evaluated.
- Trial payloads now expose `label_split_cache_hit` and `hmm_cache_hit`
  telemetry for post-run profiling.
- Added regression coverage proving one HMM fit can serve multiple horizons
  without leaking labels between KNN trials.

## Probe Evidence

A 10-trial deep-harvest-shaped local probe completed successfully:

- Completed trials: `10`
- Elapsed seconds: `22.439`
- Projected 5,000-trial runtime from this sample: `3.117` hours
- HMM cache hits in this random 10-trial sample: `0`
- Label/split cache hits in this random 10-trial sample: `0`

The zero-hit result means the sampled first 10 trials had unique HMM and label
combinations. The cache remains useful for longer runs and threshold-only
variants that revisit the same feature/HMM/split basis.

## Validation

- `python -m compileall -q src\tradingbotsuite\research_discovery`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_discovery_runner.py -q`
  - `10 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q`
  - `76 passed`
- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - `372 passed`

## Exit Decision

Stage R88 is complete. Discovery now has safe label/split and HMM-basis reuse
with explicit telemetry. The next bottleneck target is grouped/batched KNN
top-k neighbor selection.
