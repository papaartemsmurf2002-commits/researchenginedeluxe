# WPR106-369 - Sandbox End-To-End Venue Expansion Fixture Smoke

## Status

closed

## Objective

Add a focused fixture-level regression for the closed venue-expansion sandbox
loop: request bundle -> local materializer -> candidate archive manifest ->
coverage -> preflight -> bounded sandbox run -> analysis/falsification ->
descriptor-only strict-validation request bundle -> artifact catalog.

## Dependencies

- `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md`
- `docs/work_packets/WPR106-366-sandbox-venue-expansion-local-materializer.md`
- `docs/work_packets/WPR106-367-sandbox-venue-expansion-materializer-catalog-discovery.md`
- `docs/work_packets/WPR106-368-sandbox-venue-expansion-candidate-manifest-export.md`

## Allowed paths

- `tests/research_sandbox/**`
- `docs/work_packets/WPR106-369-sandbox-end-to-end-venue-expansion-fixture-smoke.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_END_TO_END_VENUE_EXPANSION_FIXTURE_SMOKE_REPORT.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Boundary constraints

- Fixture/regression validation only, not real-market evidence.
- No source behavior changes.
- No provider downloads, archive source mutation, existing manifest mutation,
  strict-validation execution, candidate-pack writes, paper/live artifacts,
  sizing, order placement, runtime-mode changes, live config writes, candidate
  evidence claims, or promotion claims.

## Acceptance criteria

- The fixture closed loop completes without manual edits between steps.
- Every produced payload keeps sandbox boundary flags.
- The strict-validation bundle remains descriptor-only and non-executing.
- The artifact catalog discovers the candidate manifest and resulting run
  artifacts.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "end_to_end_venue_expansion_fixture"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
git diff --check
```

## Exit evidence

- Added a fixture-level end-to-end regression covering:
  request bundle -> local materializer -> candidate archive manifest ->
  archive coverage -> compatibility preflight -> bounded sandbox run ->
  analysis/falsification -> descriptor-only strict-validation request bundle ->
  artifact catalog.
- The regression asserts all top-level payloads remain research-only,
  observe-only, sandbox-only, non-promotable, non-candidate-evidence, and
  candidate-pack-ineligible, with no live/paper/sizing/order/runtime behavior.
- Validation passed:
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "end_to_end_venue_expansion_fixture"`
  reported 1 passed / 181 deselected;
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  reported 196 passed;
  `git diff --check` passed with existing LF-to-CRLF warnings only.
- This is fixture workflow regression evidence only. It is not real-market
  archive evidence, candidate evidence, or promotion evidence.
