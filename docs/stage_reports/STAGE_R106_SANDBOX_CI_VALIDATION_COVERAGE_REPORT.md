# Stage R106 Sandbox CI Validation Coverage Report

Date: 2026-06-20
Packet: `WPR106-380-sandbox-ci-validation-coverage`

## Summary

WPR106-380 closes the post-audit H10 CI coverage gap for the rapid strategy
iteration sandbox. The `research-validation` workflow now runs the
`tests/research_sandbox` suite and includes `tests/live/test_cli_boundary.py`
in the existing live/artifact boundary test slice.

This packet does not change sandbox runtime behavior. It makes the staged
sandbox source, artifact boundary checks, and live-mode command rejection part
of the required validation surface so future sandbox regressions are less
likely to land with a green research-validation job.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  - `219 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py tests\live\test_cli_boundary.py tests\live\test_reject_research_artifacts.py tests\live\test_shadow_loader.py tests\live\test_promotion_candidate_validator.py -q`
  - `103 passed`
- `python -m compileall -q src\tradingbotsuite`
  - passed

## Boundary Statement

This packet changes only CI validation coverage. It does not execute strict
validation, write candidate packs, create paper/live signals, define sizing,
place orders, change runtime mode, write live configuration, claim candidate
evidence, or authorize promotion.
