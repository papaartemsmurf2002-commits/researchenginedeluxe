# WPR106-255 Sandbox Integrity-Guarded Artifact Consumers

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Make direct sandbox artifact consumers fail closed before trusting run or suite
child artifacts. Analysis, hypothesis falsification, global leaderboard, and
strict-validation request bundle export must verify manifest-recorded SHA-256
and byte-size metadata before reading compact Parquet/JSON child files.

## Scope

- Add a shared no-report integrity guard around the existing sandbox artifact
  verifier.
- Guard run analysis before reading rankings or evidence requests.
- Guard run and suite hypothesis falsification before reading child artifacts
  or case run artifacts.
- Guard global leaderboard run aggregation before reading run rankings or
  evidence requests.
- Guard run and suite strict-validation request bundle export before reading
  evidence-request descriptor files.
- Add focused tamper regressions proving consumers reject modified run and
  suite child artifacts.
- Update sandbox contract and stage docs.

## Allowed Paths

- `docs/work_packets/WPR106-255-sandbox-integrity-guarded-artifact-consumers.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_INTEGRITY_GUARDED_ARTIFACT_CONSUMERS_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/integrity.py`
- `src/tradingbotsuite/research_sandbox/__init__.py`
- `src/tradingbotsuite/research_sandbox/analytics.py`
- `src/tradingbotsuite/research_sandbox/falsification.py`
- `src/tradingbotsuite/research_sandbox/leaderboard.py`
- `src/tradingbotsuite/research_sandbox/validation_bundle.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- A tampered run child artifact causes run analysis to raise before writing an
  analysis report.
- A tampered run child artifact causes run hypothesis falsification or global
  leaderboard aggregation to raise before writing derived reports.
- A tampered suite child artifact causes suite validation-request bundle export
  to raise before writing a bundle.
- The shared integrity guard reports concise failed artifact keys and reasons.
- Passing, untampered sandbox consumers keep their existing output behavior.
- All derived artifacts remain sandbox-only, research-only, non-promotable,
  and ineligible for candidate packs.
- Validation includes focused sandbox tests, import-boundary tests, package
  compile, and the contract baseline when the local validation environment
  allows pytest-asyncio socket setup.

## Boundary

This packet changes only read-time verification for existing sandbox artifacts.
It does not execute strict validation, change strategy math, change trial IDs,
download provider data, rewrite existing source artifacts, write candidate
packs, create live/paper signals, define sizing, place orders, change runtime
mode, write live configuration, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. Added
`require_sandbox_artifact_integrity()` as a no-report fail-closed guard around
the existing verifier, and wired it into run analysis, run/suite hypothesis
falsification, global leaderboard run aggregation, and run/suite
strict-validation request bundle export.

Tampered run child artifacts now stop analysis, falsification, validation
bundle export, and global leaderboard aggregation before derived artifacts are
written. Tampered suite child artifacts now stop suite falsification and suite
validation bundle export before derived artifacts are written.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 81 sandbox tests passed, 11 import-boundary tests passed,
package compileall passed, and the full contract baseline passed with 461
tests on rerun after one known local Windows pytest-asyncio `WinError 10055`
socket setup failure at 460 passed tests.
