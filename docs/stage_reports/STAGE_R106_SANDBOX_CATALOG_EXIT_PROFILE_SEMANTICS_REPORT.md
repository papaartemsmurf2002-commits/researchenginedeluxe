# Stage R106 Sandbox Catalog Exit-Profile Semantics Report

Date: 2026-06-20
Packet: `WPR106-374-sandbox-catalog-exit-profile-semantics`

## Summary

WPR106-374 closes a post-audit sandbox semantics gap where direct strategy
catalog rows could declare a non-default `exit_profile` that execution and
compatibility preflight silently ignored.

Non-default row-level exit profiles now restrict sandbox execution to matching
run-spec exit variants. If no matching variant exists, preflight and execution
fail closed with `strategy_exit_profile_not_in_run_spec:<profile>` or
`unsupported_strategy_exit_profile:<profile>` blockers. Default `fixed_hold`
rows keep the existing normal run-spec exit-sweep behavior.

## Validation

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

## Boundary Statement

This packet changes sandbox preflight/execution semantics only for row-level
catalog exit-profile compatibility. It does not add strategy logic, invent
target/stop parameters, execute strict validation, write candidate packs,
create paper/live signals, define sizing, place orders, change runtime mode,
write live configuration, claim candidate evidence, or authorize promotion.
