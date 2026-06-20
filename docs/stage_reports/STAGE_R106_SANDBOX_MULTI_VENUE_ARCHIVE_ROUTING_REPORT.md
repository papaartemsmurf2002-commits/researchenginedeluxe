# Stage R106 Sandbox Multi Venue Archive Routing Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-232-sandbox-multi-venue-archive-routing.md`
Status: closed

## Summary

WPR106-232 makes the Rapid Strategy Iteration Sandbox route market data by
venue archive descriptor. A single run can now compare descriptor-backed local
archive frames for OKX, Bybit, Hyperliquid, Binance, and local manifests
without forcing every descriptor through one shared market frame.

## Implementation

- Added `load_market_frames_for_descriptors`.
- Resolved relative descriptor `data_path` values relative to the descriptor
  manifest file.
- Added `run_fixed_hold_sweep_for_venue_frames` for descriptor-keyed market
  frames with global ranking after all venue rows are generated.
- Added `run_sandbox_archive_sweep`, which loads descriptor market frames,
  runs the venue-routed sweep, builds evidence-request descriptors, and writes
  the existing compact sandbox artifacts.
- Updated `run-rapid-strategy-sandbox` so multiple descriptors can run without
  `--market-data` when each descriptor has `data_path`.
- Preserved explicit `--market-data` as a shared-frame smoke fallback.
- Added `market_source` metadata to result rows and compact `market_sources`
  in sandbox manifests.

## Boundary

This packet only routes local archive files already present on disk. It does
not download venue data, call venue account APIs, place orders, write live
configuration, create candidate packs, produce paper/live signals, change
sizing, alter runtime mode, or claim promotion readiness.

All outputs remain:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- `sandbox_only: true`
- `candidate_evidence: false`
- `candidate_pack_eligible: false`

## Validation

Final validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
# 30 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 461 passed
```

## Remaining Work

This packet does not add network collection, strict fixture-pack conversion,
venue checksum enforcement, Parquet query tooling, or automatic strict-cycle
execution from evidence requests. Those remain separate follow-up work under
the active sandbox objective.
