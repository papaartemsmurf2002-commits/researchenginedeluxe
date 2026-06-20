# Stage R106 Sandbox Artifact Catalog Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-237-sandbox-artifact-catalog.md`
Status: closed

## Summary

WPR106-237 adds a bounded artifact catalog for Rapid Strategy Iteration Sandbox
outputs. Agents can now scan the configured research output root for known
sandbox JSON artifacts and get a compact JSON/Parquet navigation index.

## Implementation

- Added `src/tradingbotsuite/research_sandbox/catalog.py`.
- Added `index_sandbox_artifacts`.
- The scanner only considers known sandbox JSON artifact names:
  - `manifest.json`;
  - `suite_manifest.json`;
  - `analysis_summary.json`;
  - `hypothesis_falsification.json`;
  - `suite_hypothesis_falsification.json`;
  - `strict_validation_request_bundle.json`;
  - `suite_strict_validation_request_bundle.json`.
- Discovered JSON objects must carry valid sandbox boundary flags before being
  indexed.
- Catalog rows include artifact kind, source artifact family, absolute and
  relative path, run/suite IDs, scope, result/case/hypothesis/request counts,
  strict-validation request bundle fields, and modified timestamp.
- Catalog output writes `sandbox_artifact_catalog.json` and
  `sandbox_artifact_catalog.parquet`.
- Added `index-rapid-strategy-sandbox-artifacts` as a research CLI command with
  research-root `--root-dir` and `--output-dir` enforcement.
- Registered the command in the research command registry and boundary
  contract.
- Extended the sandbox research contract with artifact catalog rules.

## Boundary

Artifact catalogs are sandbox analysis indexes. They carry:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- `sandbox_only: true`
- `candidate_evidence: false`
- `candidate_pack_eligible: false`

They do not execute sandbox runs, execute strict validation, write candidate
packs, create paper/live signals, define sizing, place orders, mutate runtime
mode, write live configuration, or claim promotion readiness.

## Validation

Final validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
# 45 passed

$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
# 13 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 461 passed
```

## Remaining Work

This packet does not add a UI explorer, strict validation execution, or
provider data download orchestration. Those remain separate follow-up work
under the active sandbox objective.
