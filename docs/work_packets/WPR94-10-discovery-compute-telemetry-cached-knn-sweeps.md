# WPR94-10 Discovery Compute Telemetry And Cached KNN Sweeps

Status: closed
Owner: Codex Research Agent
Date: 2026-05-12

## Purpose

Make real discovery runtime understandable and add an exact neighbor-cache layer
so repeated `k`/threshold variants can reuse deterministic KNN neighbor data.

## Allowed Paths

- `docs/work_packets/WPR94-10-discovery-compute-telemetry-cached-knn-sweeps.md`
- `docs/stage_reports/STAGE_R94_DISCOVERY_COMPUTE_TELEMETRY_CACHED_KNN_SWEEPS_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/research_discovery/telemetry.py`
- `src/tradingbotsuite/research_discovery/neighbor_cache.py`
- `src/tradingbotsuite/research_discovery/runner.py`
- `src/tradingbotsuite/research_discovery/knn_study.py`
- `src/tradingbotsuite/research_discovery/spec.py`
- `src/tradingbotsuite/research_discovery/manifests.py`
- `src/tradingbotsuite/research_discovery/__init__.py`
- `configs/discovery/deep_candidate_harvest_btcusdt_v4.json`
- `tests/research_discovery/test_discovery_runner.py`
- `tests/research_discovery/test_knn_study.py`
- `tests/research_discovery/test_discovery_spec.py`

## Scope

- Add stage-level discovery compute telemetry:
  - wall time by stage
  - process CPU time/percent where available
  - memory peak where available
  - active workers
  - trials per minute
  - cache hit rates for feature/label/split/regime/neighbor evidence
  - artifact write time
  - bytes written
- Add exact deterministic neighbor cache identity for feature set, split,
  horizon, regime mode, distance metric, feature columns, and source hashes.
- Reuse cached exact neighbor arrays for repeated `k`/threshold variants while
  preserving exact-KNN parity.

## Non-Goals

- No approximate nearest-neighbor, GPU, ANN, or randomized KNN behavior.
- No live trading behavior, live config writes, order placement, runtime mode
  changes, promotion readiness, candidate-pack writing, or sizing logic changes.
- No strategy scoring or candidate eligibility semantics changes.

## Validation Plan

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_knn_study.py tests\research_discovery\test_discovery_runner.py tests\research_discovery\test_discovery_spec.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
python -m compileall -q src\tradingbotsuite
git diff --check
```

## Validation Result

- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_knn_study.py tests\research_discovery\test_discovery_runner.py tests\research_discovery\test_discovery_spec.py -q` - 37 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` - 382 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q` - 142 passed.
- `python -m compileall -q src\tradingbotsuite` - passed.
- `git diff --check` - passed with existing CRLF conversion warnings only.

## Exit Evidence

- Added `telemetry.py` and run-manifest `compute_telemetry` with wall/process
  timing, stage timing, memory peak, active workers, trials/minute, cache hit
  rates/counts, artifact bytes, and file counts.
- Added `neighbor_cache.py` and exact deterministic in-memory neighbor-cache
  identity.
- KNN prediction materialization can now reuse cached exact neighbor prefixes
  for repeated `k` and threshold sweeps while preserving uncached parity.
- Runner trial payloads now expose `neighbor_cache_hit`,
  `neighbor_cache_lookup_count`, and `neighbor_cache_hit_count`.
- Tests prove cached/uncached prediction parity, deterministic cache identity,
  manifest telemetry shape, and reuse across repeated horizon/KNN sweeps.
- ANN/GPU/randomized KNN, score semantics, candidate-pack writing, live
  behavior, promotion readiness, and sizing were not changed.
