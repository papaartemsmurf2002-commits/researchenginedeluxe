# Stage R94 Discovery Compute Telemetry Cached KNN Sweeps Report

Date: 2026-05-12
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR94-10-discovery-compute-telemetry-cached-knn-sweeps.md`

## Scope

WPR94-10 added run-level compute telemetry and an exact deterministic
neighbor-cache layer for discovery KNN sweeps. It did not change discovery score
semantics, candidate-pack eligibility, live behavior, promotion readiness, or
sizing.

## Completed

- Added `research_discovery.telemetry` for run-manifest compute telemetry:
  wall/process timing, stage timing, memory peak, active workers,
  trials/minute, cache rates/counts, artifact bytes, and file counts.
- Added `research_discovery.neighbor_cache` with exact-neighbor cache identity
  and thread-safe in-memory stats.
- Refactored KNN prediction materialization so selected exact neighbor prefixes
  can be replayed across `k` and threshold variants.
- Kept deterministic top-k ordering unchanged.
- Added runner payload fields for neighbor-cache hits/lookups.
- Normalized HMM identity so cache-hit metadata does not prevent valid neighbor
  reuse.
- Added focused parity and manifest telemetry tests.

## Boundary Notes

- No ANN/GPU/randomized KNN was added.
- Threshold fields are excluded from neighbor-cache identity; source, feature,
  split, horizon, regime, distance, and max-k identity remain included.
- Cache reuse remains research-only and observe-only.
- No candidate packs are written, and no promotion/live/sizing paths changed.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_knn_study.py tests\research_discovery\test_discovery_runner.py tests\research_discovery\test_discovery_spec.py -q
# 37 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 382 passed

$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
# 142 passed

python -m compileall -q src\tradingbotsuite
# passed

git diff --check
# passed with existing CRLF conversion warnings only
```

## Decision

WPR94-10 is complete. The next roadmap step is the exit model upgrade and
remaining-edge lab.
