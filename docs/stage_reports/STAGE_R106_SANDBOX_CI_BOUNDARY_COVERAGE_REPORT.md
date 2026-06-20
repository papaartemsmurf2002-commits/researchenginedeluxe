# Stage R106 Sandbox CI Boundary Coverage Report

Date: 2026-06-20
Packet: `WPR106-364-sandbox-ci-boundary-coverage`

## Summary

WPR106-364 adds the Rapid Strategy Iteration Sandbox tests and live CLI
boundary tests to `.github/workflows/research-validation.yml`. This closes the
post-audit CI coverage gap where sandbox regressions could land without the
workflow running `tests/research_sandbox` or
`tests/live/test_cli_boundary.py`.

## Changes

- Added a dedicated workflow step:
  `python -m pytest tests/research_sandbox -q`.
- Added `tests/live/test_cli_boundary.py` to the existing live/artifact
  boundary workflow step.
- Left contract tests and the prior live/artifact boundary tests in place.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  - `189 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`
  - `23 passed`
- `python -c "import yaml, pathlib; yaml.safe_load(pathlib.Path('.github/workflows/research-validation.yml').read_text())"`
  - passed
- Earlier WPR106-362/WPR106-363 full-suite validation:
  `$env:PYTHONPATH='src'; python -m pytest -q -p no:cacheprovider`
  - `1844 passed, 1 skipped, 1 warning`

## Boundary Statement

This packet changes CI coverage only. It does not change source behavior,
generated artifacts, archive manifests, archive sources, provider downloads,
replay execution, strict-validation execution, candidate packs, paper/live
artifacts, sizing, order behavior, runtime mode, live configuration, or
promotion state.

