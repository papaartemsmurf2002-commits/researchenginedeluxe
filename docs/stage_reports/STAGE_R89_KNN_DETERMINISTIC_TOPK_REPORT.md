# Stage R89 KNN Deterministic Top-K Report

Date: 2026-05-09
Packet: `docs/work_packets/WPR89-01-knn-deterministic-topk.md`

## Scope

WPR89 reduces KNN neighbor-selection work by avoiding full candidate distance
sorts when only the nearest `k` neighbors are needed.

## Changes

- Added `_stable_topk_distance_order`, which uses `np.partition` to identify
  the kth distance and stable-sorts only candidates at or below that distance.
- Preserved prior full `np.argsort(..., kind="mergesort")` behavior for ties,
  including ties exactly at the kth-distance boundary.
- Added `neighbor_selection_engine: deterministic_partition_topk_v1` to KNN
  manifests.
- Added focused top-k regression tests for boundary ties and random distances.

## Probe Evidence

A 10-trial deep-harvest-shaped local probe completed successfully:

- Completed trials: `10`
- Elapsed seconds: `22.725`
- Projected 5,000-trial runtime from this sample: `3.156` hours
- HMM cache hits in this random 10-trial sample: `0`
- Label/split cache hits in this random 10-trial sample: `0`

This small sample did not show a visible end-to-end improvement because the
fixture row count and candidate pools are modest; the change primarily reduces
sort cost on larger pools and longer provider-backed frames.

## Validation

- `python -m compileall -q src\tradingbotsuite\research_discovery`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_knn_study.py -q`
  - `12 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q`
  - `78 passed`
- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - `372 passed`

## Exit Decision

Stage R89 is complete. KNN neighbor selection now avoids full candidate sorts
while keeping deterministic output equivalence.
