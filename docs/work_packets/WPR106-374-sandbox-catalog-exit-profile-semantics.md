# WPR106-374 - Sandbox Catalog Exit-Profile Semantics

## Status

closed

## Objective

Close the post-audit ambiguity where direct strategy catalog rows can declare
`exit_profile` values that are silently ignored by sweep execution and
compatibility preflight.

## Dependencies

- `RAPID_STRATEGY_SANDBOX_AUDIT.md`
- `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md`
- `docs/work_packets/WPR106-362-post-audit-sandbox-safety-coherence.md`
- `docs/work_packets/WPR106-373-backtest-fill-semantics-compatibility.md`

## Allowed paths

- `src/tradingbotsuite/research_sandbox/fast_backtest.py`
- `src/tradingbotsuite/research_sandbox/preflight.py`
- `tests/research_sandbox/test_post_audit_safety.py`
- `docs/contracts/sandbox_research_contract.md`
- `docs/work_packets/WPR106-374-sandbox-catalog-exit-profile-semantics.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_CATALOG_EXIT_PROFILE_SEMANTICS_REPORT.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Boundary constraints

- Preserve sandbox-only, research-only, observe-only, non-promotable,
  non-candidate-evidence, and candidate-pack-ineligible artifact semantics.
- Do not add strict-validation execution, candidate-pack writes, paper/live
  behavior, sizing, order placement, runtime mode changes, live config writes,
  provider downloads, or promotion claims.
- Do not invent target/stop parameters from vague catalog text.

## Acceptance criteria

- A non-default catalog row `exit_profile` is not silently ignored.
- If a row declares a non-default `exit_profile`, execution only runs matching
  run-spec exit variants.
- If no matching run-spec variant exists, execution and preflight fail closed
  with a clear blocker.
- Existing default `fixed_hold` rows still participate in normal run-spec exit
  sweeps.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_post_audit_safety.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
python -m compileall -q src\tradingbotsuite
git diff --check
```

Exit evidence:

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_post_audit_safety.py -q`
  - `17 passed`
- `python -m compileall -q src\tradingbotsuite`
  - passed
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  - `208 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`
  - `26 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - `462 passed`
- `git diff --check`
  - passed with existing LF-to-CRLF warnings only

## Stop conditions

- Row-level exit profiles are still silently ignored.
- The fix weakens blocker reporting, boundary metadata, descriptor windows,
  trial identity, strict-validation handoff, or candidate-pack protections.
