# WPR106-472 - V2 Readiness Doc, CI, And Full-Suite Closeout

Status: self_checked
Audit IDs: `V2-AUD-COMPLETE-004`, `V2-AUD-TESTINFRA-001`

## Objective

Close the fixable readiness gaps found during the repository audit: stale
top-level v2 readiness documentation, missing v2 tests in the checked-in CI
baseline, and the open local Python 3.11 full-suite validation blocker.

This packet must not create accepted research evidence, autonomous-ready
status, candidate-ready status, paper/live/order/sizing/runtime behavior, a
candidate pack, or promotion readiness.

## Allowed Paths

- `docs/work_packets/WPR106-472-v2-readiness-doc-ci-full-suite-closeout.md`
- `README.md`
- `.github/workflows/research-validation.yml`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `docs/KNOWN_ISSUES.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## No-Touch Paths

- `src/**/live/**`
- `src/**/runtime.py`
- `run_live_smoke.py`
- `run_manual.py`
- order-placement, broker, exchange-submit, sizing, runtime-config, promotion,
  shadow, and candidate-pack truth-layer paths
- committed `data/research/fixtures/**`
- committed `data/research/historical_cycles/**`
- legacy GUI/operator UI paths
- `src/tradingbot/**`
- `.env`, credential files, local SQLite operator DBs, private caches, and
  generated `outputs/**`

## Changed Files

- `README.md`
- `.github/workflows/research-validation.yml`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `docs/KNOWN_ISSUES.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR106-472-v2-readiness-doc-ci-full-suite-closeout.md`

## Decisions Made

- The checked-in CI baseline now runs `tests/v2 -q` because v2 is the active
  manager-loop and readiness surface.
- `ISSUE-R106-026` is resolved by fresh Python 3.11 local evidence from this
  packet. The previous failure was a local environment/resource condition, not
  a source assertion failure.
- Top-level docs now describe the current state as a self-checked
  research-only v2 foundation with a completed public diagnostic worker-chain
  smoke, while still clearly blocking autonomous/candidate/paper/live/order/
  sizing/runtime/promotion interpretation until accepted archive and readiness
  evidence exists.

## Acceptance Evidence

- Python 3.11 dependency check passed:
  `py -3.11 -m pip check`.
- Python 3.11 focused v2 validation passed:
  `$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2 -q`
  (328 passed, 1 warning).
- Python 3.11 contracts passed:
  `$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q`
  (463 passed, 1 warning).
- Python 3.11 rapid sandbox CI lane passed:
  `$env:PYTHONPATH='src'; py -3.11 -m pytest tests\research_sandbox -q`
  (226 passed, 1 warning).
- Python 3.11 live/artifact boundary CI lane passed:
  `$env:PYTHONPATH='src'; py -3.11 -m pytest tests\live\test_preflight.py tests\live\test_cli_boundary.py tests\live\test_reject_research_artifacts.py tests\live\test_shadow_loader.py tests\live\test_promotion_candidate_validator.py -q`
  (103 passed, 1 warning).
- Python 3.11 monolithic full suite passed:
  `$env:PYTHONPATH='src'; py -3.11 -m pytest tests -q`
  (2235 passed, 2 skipped, 6 warnings, 12:44).
- Default-Python contract lane passed after the doc/CI updates:
  `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  (463 passed).
- Diff hygiene passed:
  `git diff --check`
  (passed with expected LF-to-CRLF warnings only).
