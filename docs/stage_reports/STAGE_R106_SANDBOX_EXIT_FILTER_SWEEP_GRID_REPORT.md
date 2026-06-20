# Stage R106 Sandbox Exit Filter Sweep Grid Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-231-sandbox-exit-filter-sweep-grid.md`
Status: closed

## Summary

WPR106-231 extends the Rapid Strategy Iteration Sandbox from fixed-hold-only
triage into a bounded strategy/exit/filter sweep grid. The new grid remains
sandbox-only and non-promotable, but it lets agents falsify more variants per
run before asking the strict historical research cycle for expensive evidence.

## Implementation

- Added `ExitVariant` and `FilterVariant` to the sandbox run spec.
- Preserved default behavior with one `fixed_hold` exit and one `base` filter.
- Added target-only, stop-only, and conservative target/stop primary-bar exit
  proxies.
- Added completed-row filter variants that layer beside a strategy's base
  filter.
- Included exit/filter variant payloads in deterministic trial IDs.
- Added `exit_profile`, `exit_variant_id`, and `filter_variant_id` to result
  payloads and Parquet summaries.
- Recorded exit/fill assumptions in result metadata, including stop-first
  handling for same-bar target/stop ambiguity.
- Updated JSON run-spec loading for `exit_variants` and `filter_variants`.
- Updated the sandbox research contract and active index.

## Boundary

The target/stop variants are primary-bar sandbox proxies. They are useful for
fast falsification, not strict lower-timeframe execution evidence. Target/stop
variants require `high` and `low` columns and block clearly when those columns
are unavailable.

All outputs remain:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- `sandbox_only: true`
- `candidate_evidence: false`
- `candidate_pack_eligible: false`

No candidate pack, paper/live signal, sizing instruction, order instruction,
runtime-mode change, live configuration write, or promotion claim is produced.

## Validation

Final validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
# 25 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 461 passed
```

## Remaining Work

This packet does not add lower-timeframe path reconstruction, richer venue
manifest normalization, query tools over sandbox Parquet, or automatic strict
cycle execution from evidence requests. Those remain follow-up work under the
active sandbox objective.
