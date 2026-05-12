# Stage R94 Multiple-Testing And Stability Gate Report

Date: 2026-05-12
Branch: `research/v3-experimental-engine`
Work packet: `docs/work_packets/WPR94-05-multiple-testing-stability-gate.md`

## Summary

WPR94-05 added a discovery-side multiple-testing and stability gate so sparse
large-grid winners remain screen leads until concentration and stability
evidence is explicit.

Implemented:

- Added `tradingbotsuite.research_discovery.multiple_testing`.
- Added research-only artifact writer for:
  - `discovery_multiple_testing_manifest.json`
  - `discovery_multiple_testing_candidate_gates.parquet`
- Added candidate gate metrics:
  `declared_search_space`, `sampled_fraction`, `effective_trial_count`,
  `best_candidate_concentration`, `stability_neighborhood_size`,
  `split_window_concentration`, `side_concentration`, and
  `latest_window_only_penalty`.
- Added manifest-derived report construction from discovery manifests, resolved
  specs, ledgers, and trial records.
- Tied gate rows to `record_sha256` and source discovery manifest SHA.
- Extended the discovery candidate-pack bridge and CLI with a mandatory
  multiple-testing manifest input.
- Added bridge blockers for missing/corrupt evidence, source manifest mismatch,
  candidate record hash mismatch, isolated large-grid winners, concentrated
  top scores, low stability-neighborhood size, split/window concentration,
  side concentration, and latest-window-only evidence.

## Boundary Notes

- Research outputs remain `research_only: true`, `observe_only: true`, and
  `promotion_ready: false`.
- Candidate-pack writing remains disabled in the bridge.
- No live order placement, live config writes, runtime mode changes, or sizing
  behavior was added.
- The existing historical-cycle candidate-pack gate remains mandatory and was
  not weakened or replaced.

## Validation

Passed:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_multiple_testing.py tests\research_discovery\test_candidate_pack_bridge.py -q
# 27 passed

$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
# 131 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 372 passed

python -m compileall -q src\tradingbotsuite
# passed

git diff --check
# passed with line-ending warnings only
```

## Next Packet

Continue the explicit R94 priority list with validation floors and blocker
registry work.
