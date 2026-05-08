# Stage R81 Deep Discovery Benchmarks Report

Date: 2026-05-08
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR81-01-deep-discovery-benchmarks.md`

## Summary

WPR81 adds research-only discovery benchmark tiers for quick, standard, and deep discovery run-manager workloads. The benchmark writes a reproducible `discovery_benchmark_report.json` that checks stop/resume behavior, completed-ledger equality, snapshot readability, trial-record hash integrity, artifact overhead, and research-only boundary flags.

## Changes

- Added `tradingbotsuite.research_discovery.benchmark` with `quick`, `standard`, and `deep` benchmark tiers and gate thresholds.
- Added benchmark spec generation under isolated benchmark output directories.
- Added uninterrupted versus interrupted/resumed discovery runs and ledger hash equality checks.
- Added snapshot integrity checks for readable JSON, monotonic unique sequence numbers, no temp files, and final snapshot/state agreement.
- Added trial integrity checks that read completed trial files through the discovery state hash contract.
- Added `configs/discovery/discovery_benchmark_tiers_v4.json` as the checked tier reference.
- Added CLI command `benchmark-discovery-run` with report-only failed-gate override support.
- Registered the new command as a research command so live preflight rejects it.

## Research Boundary

- Benchmark artifacts are `research_only: true`, `observe_only: true`, and `promotion_ready: false`.
- No live fetch, order placement, runtime mode mutation, candidate-pack write, strategy math, HMM/KNN math, optimizer gate, promotion, or checked historical-cycle behavior was changed.
- The `deep` tier is a bounded local run-manager regression tier, not 24-48 hour evidence.

## Validation

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/research_discovery -q
$env:PYTHONPATH='src'; python -m pytest tests/live/test_preflight.py -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Results:

- `compileall`: passed
- `tests/research_discovery`: 53 passed
- `tests/live/test_preflight.py`: 28 passed
- `tests/contracts`: 372 passed

## Stage Decision

R81 is closed. The next V4 implementation stage is WPR82 candidate pack bridge.
