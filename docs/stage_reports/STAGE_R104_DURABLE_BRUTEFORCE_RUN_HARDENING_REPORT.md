# Stage R104 Durable Brute-Force Run Hardening Report

Date: 2026-05-17
Work packet: `docs/work_packets/WPR104-04-durable-bruteforce-run-hardening.md`

## Summary

WPR104-04 investigated why the operator-visible durable runs produced no
candidate leads and hardened the R104 path around the branch objective:
long-running, brute-force-scale durable research.

The engine was not failing to run. It was running short or sparse profiles and
the UI/progress layer did not make that distinction clear enough. The latest
disk artifacts showed completed runs with explicit fail-closed blockers:

- Latest BTC deep discovery completed 5000 trials with zero current interesting
  candidates and 5000 blocked rows.
- Latest ETH standard discovery completed 360 trials with zero interesting
  candidates and 360 blocked rows.
- Latest BTC/ETH durable historical cycles produced 17 candidates each, with
  all candidates blocked by validation/gate evidence.
- The compact durable fixture packs have only 32 primary 15m bars per symbol,
  which is enough for checksum-verified screening but too small for
  candidate-ready brute-force evidence.

## Implemented

- Added discovery search-space summaries derived from the same dimensions that
  generate real trial templates:
  - `total_combinations`
  - `planned_trials`
  - `sampled_fraction`
  - `exhaustive`
  - `coverage_label`
- Added R104 exact bounded discovery configs:
  - `configs/discovery/exact_entry_sweep_btcusdt_durable_r104_v1.json`
  - `configs/discovery/exact_entry_sweep_ethusdt_durable_r104_v1.json`
  - each is 570240 planned combinations with exhaustive coverage over the
    compact viable feature-column scope.
- Added R104 standard blocker-screen config for BTC and tightened ETH standard
  to the compact feature sets that pass durable fixture preflight.
- Added deeper R104 historical-cycle configs:
  - `configs/research/full_cycle_btcusdt_durable_public_archive_r104_deep_v1.json`
  - `configs/research/full_cycle_ethusdt_durable_public_archive_r104_deep_v1.json`
  - each expands candidate search to 64 candidates per strategy and 16 refined
    regions while preserving observe-only, non-promotable boundaries.
- Changed operator defaults to durable R104 deep/exact specs instead of
  provider-context or smoke specs.
- Hardened `/api/operator/research/progress` so it uses a bounded R104 manifest
  scan for known cycle/discovery/eligibility outputs. Direct CLI or previous
  isolated operator artifacts now count even when the operator SQLite job table
  has no R104 rows.
- Updated the Research UI so the primary action path is visibly:
  1. BTC deep cycle
  2. BTC exact sweep
  3. eligibility review
  4. ETH deep cycle and exact sweep
- Kept standard screens and diagnostic smoke available, but no longer presents
  them as completion of the durable brute-force objective.
- Fixed mobile layout overflow found during browser verification.
- Registered `ISSUE-R104-001` for the remaining evidence blocker: the durable
  fixtures are currently too compact for candidate-ready brute-force evidence.

## Research Boundary

This wave did not write candidate packs, claim promotion readiness, add live
execution, alter live configuration, change runtime mode, place orders, or
touch sizing behavior. New configs and manifests remain research-only,
observe-only, and `promotion_ready: false`.

## Validation

- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q`
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
- JSON parse check for the new R104 discovery and research configs.
- Browser check on `http://127.0.0.1:8766/ui/research`:
  - desktop `1440x1000`: horizontal overflow `0`
  - mobile `390x900`: horizontal overflow `0`
  - exact-sweep controls and `570240` profile text visible.

## Next Operation

The next operational step is not another short run. Run the new R104 exact path
only after deciding whether the compact fixture is acceptable for screening:

1. Queue `BTC Deep Cycle`.
2. Queue `BTC Exact Sweep`.
3. Queue `Evaluate Eligibility`.
4. Repeat with `ETH Deep Cycle` and `ETH Exact Sweep`.
5. Inspect blocker histograms and eligibility output before making any
   candidate claim.

For candidate-ready evidence, resolve `ISSUE-R104-001` first by generating
expanded checksum-verified durable public-archive fixtures with materially more
primary 15m bars, then rerun the same deep/exact path.
