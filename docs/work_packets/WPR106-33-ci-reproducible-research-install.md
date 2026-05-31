# WPR106-33 CI Reproducible Research Install

## Goal

Close `ISSUE-R106-009` by adding a checked-in CI workflow that proves the
research package can be installed and validated from a clean Python 3.11
environment.

This packet does not change source behavior, research execution, candidate
gates, fixture data, generated artifacts, live/paper/runtime behavior,
promotion logic, sizing, or order placement.

## Current Repo Facts

- Current checkout: `main`, treated as the migrated R106 research checkout
  mirror.
- `.github` is missing before this packet.
- `pyproject.toml` declares Python `>=3.11` and a `dev` extra containing pytest
  dependencies.
- WPR106-32 registered `ISSUE-R106-009` as an open P0 because no checked-in CI
  or reproducible install gate existed.
- Open P0 issues block stage advancement and empirical expansion.

## Conflicts And Stale Docs Found

- Local README validation commands exist, but they are not equivalent to a clean
  environment CI gate.
- Optional `research`, `crypto-lake`, and `research-gpu` extras are not required
  for baseline contracts and should not be pulled into the default CI gate.

## Allowed Edit Paths

- `docs/work_packets/WPR106-33-ci-reproducible-research-install.md`
- `.github/workflows/research-validation.yml`
- `README.md`
- `docs/ACTIVE_INDEX.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/STAGE_R106_CI_REPRODUCIBLE_RESEARCH_INSTALL_REPORT.md`

## Forbidden Edit Paths

- `src/**`
- `tests/**`
- `configs/**`
- `data/research/**`
- fixture packs
- generated operator-run artifacts
- live/runtime/promotion/sizing/order-placement behavior
- dependency version changes
- `.pytest_cache/**`

## Subagents Used

No new subagent was needed for this narrow implementation. WPR106-32 repo
cartography already confirmed `.github` was missing and the safety subagent
identified the focused live/artifact safety baseline.

## Tests To Run

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py tests\live\test_reject_research_artifacts.py tests\live\test_shadow_loader.py tests\live\test_promotion_candidate_validator.py -q
git diff --check
```

## Artifacts Expected

- One GitHub Actions workflow under `.github/workflows/`.
- Updated active docs and issue registry marking `ISSUE-R106-009` resolved if
  validation passes.
- Stage report recording commands and results.

No generated research data artifacts or candidate packs are expected.

## Definition Of Done

- CI installs `.[dev]` in a clean Python 3.11 environment.
- CI runs `pip check`, compile, contract tests, and focused live/artifact
  boundary tests.
- Optional research/GPU/vendor extras are explicitly outside this baseline.
- `ISSUE-R106-009` is resolved in `docs/KNOWN_ISSUES.md`.
- Open P0 count is reduced without weakening any gate.

## Rollback Plan

Remove `.github/workflows/research-validation.yml` and revert only this packet's
documentation updates. Do not touch unrelated local cache state, source code,
or generated evidence.
