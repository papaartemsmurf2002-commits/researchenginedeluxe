# Stage R106 Fail-Closed Synthetic Source Selection Report

Work packet:
`docs/work_packets/WPR106-34-fail-closed-synthetic-source-selection.md`

Date: 2026-05-31

## Summary

WPR106-34 closes `ISSUE-R106-010`. Historical research-cycle data loading no
longer silently synthesizes data when a spec declares no source. Synthetic data
remains available only when `synthetic_fixture: true` is explicit, and synthetic
fixtures are labeled as test/demo/benchmark evidence rather than real
candidate-ready evidence.

This packet does not add strategies, filters, models, candidate gates, live or
paper behavior, runtime artifact loading, promotion logic, sizing, order
placement, fixture data, or generated research artifacts.

## Code Changes

Updated:

- `src/tradingbotsuite/research_cycle/spec.py`
- `src/tradingbotsuite/research_cycle/runner.py`
- `tests/contracts/test_research_cycle_contract.py`
- `tests/historical/test_full_cycle_synthetic.py`
- `tests/historical/test_full_cycle_local_fixture_pack.py`

Added:

- `docs/work_packets/WPR106-34-fail-closed-synthetic-source-selection.md`
- `docs/stage_reports/STAGE_R106_FAIL_CLOSED_SYNTHETIC_SOURCE_SELECTION_REPORT.md`

Documentation updates:

- `docs/ACTIVE_INDEX.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Behavior

`CycleDataSpec` now parses and round-trips:

- `synthetic_fallback_allowed`
- `synthetic_use_case`

Allowed synthetic use cases are:

- `test_only`
- `demo_only`
- `benchmark_only`

Fail-closed behavior added:

- no declared source plus `synthetic_fixture: false` now raises
  `cycle_data_source_required`;
- `synthetic_fixture: true` cannot be combined with declared real data sources;
- `synthetic_fallback_allowed: true` requires `synthetic_fixture: true`;
- ambiguous `local_fixture_dir` directories with multiple Parquet files raise
  `local_fixture_dir_ambiguous_multiple_parquet_files`;
- unusable declared sources still fail closed instead of falling back to
  synthetic data.

Successful historical-cycle runs now write
`source_selection_manifest.json` and include it in `required_outputs`.

The source-selection manifest records:

- selected source type;
- declared source count;
- synthetic fixture request state;
- synthetic fallback policy;
- synthetic use case when applicable;
- selected, skipped, and rejected source records.

## Evidence Contract

Explicit synthetic fixtures remain research-only, observe-only, and
promotion-ready false. Candidate-pack gates continue to reject synthetic
evidence as candidate-ready evidence through existing source-gate reasons such
as `non_synthetic_fixture_evidence_required`.

Generic `dataset_path`, generic `dataset_manifest`, and `local_fixture_dir`
sources remain weaker than validated `historical_fixture_pack` source evidence.
This packet records how they were selected, but it does not promote them to
candidate-ready evidence.

## Issue Registry Update

`ISSUE-R106-010` is resolved.

Current open P0 blockers after this packet:

- `ISSUE-R106-011`: generic purge is fixed-bar based instead of
  label/event-end aware.
- `ISSUE-R106-012`: lower-timeframe entry pricing is labeled but not used.
- `ISSUE-R106-013`: local credential files can imply Hyperliquid live/testnet
  enablement.
- `ISSUE-R106-014`: runtime artifact validation is not mode-aware and not
  fail-closed for unknown manifests.

Open P0 issues still block stage advancement and empirical expansion.

## Validation

Passed:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py tests\historical\test_full_cycle_synthetic.py tests\historical\test_full_cycle_local_fixture_pack.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Observed:

- compileall passed.
- focused research-cycle/history tests: 83 passed in 293.54 seconds.
- contracts: 430 passed in 5.54 seconds.
- `git diff --check` passed with line-ending warnings only.

## Boundary

No candidate pack was written. No generated data artifact was committed. No live
or paper runtime behavior was introduced. No candidate gate was weakened.

The next recommended packet is P0-D: add LabelSpec/event-end-aware purge
evidence and replace fixed-bar purge where long or overlapping labels can leak.
