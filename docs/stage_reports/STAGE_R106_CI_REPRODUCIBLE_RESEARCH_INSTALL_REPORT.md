# Stage R106 CI Reproducible Research Install Report

Work packet:
`docs/work_packets/WPR106-33-ci-reproducible-research-install.md`

Date: 2026-05-31

## Summary

WPR106-33 closes `ISSUE-R106-009` by adding a checked-in GitHub Actions
workflow for the reproducible research baseline.

The new workflow installs ResearchEngineDeluxe's active package in a clean
Python 3.11 environment using the compatibility package name
`tradingbotsuite`, then runs dependency consistency, compile, contract, and
focused live/artifact boundary checks.

This packet does not change source behavior, tests, configs, fixture data,
generated research artifacts, candidate gates, candidate-pack eligibility, live
runtime behavior, paper behavior, promotion logic, sizing, or order placement.

## Code And Docs Changes

Added:

- `.github/workflows/research-validation.yml`
- `docs/work_packets/WPR106-33-ci-reproducible-research-install.md`
- `docs/stage_reports/STAGE_R106_CI_REPRODUCIBLE_RESEARCH_INSTALL_REPORT.md`

Updated:

- `README.md`
- `docs/ACTIVE_INDEX.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## CI Contract

The workflow runs on `push` to `main`, `research/**`, and `codex/**`, and on
pull requests.

The job:

- checks out the repository;
- sets up Python 3.11;
- installs `.[dev]` in editable mode;
- runs `python -m pip check`;
- runs `python -m compileall -q src/tradingbotsuite`;
- runs `python -m pytest tests/contracts -q`;
- runs focused live/artifact boundary tests:
  - `tests/live/test_preflight.py`
  - `tests/live/test_reject_research_artifacts.py`
  - `tests/live/test_shadow_loader.py`
  - `tests/live/test_promotion_candidate_validator.py`

Optional `research`, `crypto-lake`, and `research-gpu` extras remain outside
this baseline. Those extras require separate scoped packets if they become
required for a future gate.

## Issue Registry Update

`ISSUE-R106-009` is resolved.

Current open P0 blockers after this packet:

- `ISSUE-R106-010`: synthetic fallback and source selection are not explicit
  enough.
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
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py tests\live\test_reject_research_artifacts.py tests\live\test_shadow_loader.py tests\live\test_promotion_candidate_validator.py -q
```

Observed:

- compileall passed.
- contract tests: 427 passed in 6.09 seconds.
- focused live/artifact boundary tests: 46 passed in 0.49 seconds.
- workflow YAML parsed successfully with `PyYAML`.

## Boundary

This is a reproducibility gate only. It does not create candidate evidence,
write candidate packs, mark candidates eligible, enable live/testnet behavior,
load artifacts into runtime modes, or alter strategy/backtest behavior.

The next recommended packet is P0-C: fail closed on no-source/synthetic
fallback and record explicit source selection.
