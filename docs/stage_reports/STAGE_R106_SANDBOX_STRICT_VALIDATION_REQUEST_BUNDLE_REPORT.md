# Stage R106 Sandbox Strict Validation Request Bundle Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-236-sandbox-strict-validation-request-bundle.md`
Status: closed

## Summary

WPR106-236 adds descriptor-only strict-validation request bundles for Rapid
Strategy Iteration Sandbox run and suite artifacts. Agents can now collect and
dedupe sandbox evidence requests into a compact handoff that names the existing
strict historical validation entrypoint without executing it.

## Implementation

- Added `src/tradingbotsuite/research_sandbox/validation_bundle.py`.
- Added run-level `export_sandbox_validation_request_bundle`.
- Added suite-level `export_sandbox_suite_validation_request_bundle`.
- Bundle writers validate source sandbox manifests and evidence-request
  descriptors before writing.
- Requests are deduped deterministically by requested validation, source run,
  source trial, hypothesis, venue, and symbol.
- Descriptor rows include:
  - source request/run/trial IDs;
  - hypothesis, family, venue, and symbol;
  - strict validation entrypoint and command;
  - descriptor-only execution mode;
  - required evidence;
  - source sandbox metrics;
  - run/suite/case provenance paths.
- Run-level output writes `strict_validation_request_bundle.json` and
  `strict_validation_request_bundle.parquet`.
- Suite-level output writes `suite_strict_validation_request_bundle.json` and
  `suite_strict_validation_request_bundle.parquet`.
- Added `export-rapid-strategy-sandbox-validation-requests` as a research CLI
  command with research-root `--run-dir`, `--suite-dir`, and `--output-dir`
  enforcement.
- Registered the command in the research command registry and boundary
  contract.
- Extended the sandbox research contract with descriptor bundle rules.

## Boundary

Strict-validation request bundles are sandbox handoff descriptors only. They
carry:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- `sandbox_only: true`
- `candidate_evidence: false`
- `candidate_pack_eligible: false`

They set `strict_validation_executed: false`, `candidate_pack_written: false`,
and `execution_mode: descriptor_only_no_execution`. They do not execute strict
validation, write candidate packs, create paper/live signals, define sizing,
place orders, mutate runtime mode, write live configuration, or claim promotion
readiness.

## Validation

Final validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
# 43 passed

$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
# 12 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 461 passed
```

## Remaining Work

This packet does not generate strict historical-cycle specs, execute strict
validation, or add an interactive UI. Those remain separate follow-up work
under the active sandbox objective.
