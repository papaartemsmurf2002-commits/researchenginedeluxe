# Stage R106 Sandbox Suite Batch Runner Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-234-sandbox-suite-batch-runner.md`
Status: closed

## Summary

WPR106-234 adds a suite-level batch runner for the Rapid Strategy Iteration
Sandbox. Agents can now execute several sandbox specs/catalogs/venue manifests
from one portable JSON suite file and receive suite-level JSON/Parquet indexes
plus aggregated evidence-request descriptors.

## Implementation

- Added `src/tradingbotsuite/research_sandbox/suite.py`.
- Added `SandboxSuiteSpec`, `SandboxSuiteCase`, suite artifact/result
  dataclasses, `load_sandbox_suite_spec`, and `run_sandbox_suite`.
- Suite case paths resolve relative to the suite spec file unless absolute.
- Each suite case reuses the archive-routed sandbox runner, then summarizes the
  run with the existing sandbox analysis layer.
- Suite output writes:
  - `suite_manifest.json`;
  - `suite_index.json`;
  - `suite_index.parquet`;
  - `suite_evidence_requests.json`;
  - `suite_evidence_requests.parquet`.
- Aggregated evidence-request descriptors retain the original request payload
  and add suite/case/source artifact context.
- Added `run-rapid-strategy-sandbox-suite` as a research CLI command with
  research-root `--output-dir` enforcement.
- Registered the command in the research command registry and boundary
  contract.
- Extended the sandbox research contract with suite rules.

## Boundary

Suite artifacts are still sandbox artifacts. They carry:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- `sandbox_only: true`
- `candidate_evidence: false`
- `candidate_pack_eligible: false`

The suite runner does not execute strict validation, write candidate packs,
create paper/live signals, define sizing, place orders, mutate runtime mode,
write live configuration, or claim promotion readiness.

## Validation

Final validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
# 37 passed

$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
# 10 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# first attempt: 460 passed, 1 Windows asyncio setup error, 1 warning
# rerun: 461 passed
```

The first full contract attempt failed before the affected test body ran while
Windows was creating an asyncio event-loop socketpair (`WinError 10055`). The
same contract baseline reran cleanly with 461 passed tests.

## Remaining Work

This packet does not add strict-cycle auto-execution from evidence requests,
interactive query/UI workflows, or provider network download orchestration.
Those remain separate follow-up work under the active sandbox objective.
