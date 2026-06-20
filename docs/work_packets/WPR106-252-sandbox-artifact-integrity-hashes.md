# WPR106-252 Sandbox Artifact Integrity Hashes

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Improve Rapid Strategy Iteration Sandbox reproducibility and agent handoff
quality by recording deterministic integrity metadata for compact run and suite
artifacts. Agents should be able to verify that Parquet/JSON summaries,
rankings, and evidence-request descriptors have not drifted without executing
strict validation or reading live-adjacent state.

## Scope

- Add SHA-256 and byte-size metadata for sandbox run child artifacts written by
  `ResultStore.write_run()`.
- Add SHA-256 and byte-size metadata for sandbox suite child artifacts written
  by `run_sandbox_suite()`.
- Avoid circular hashing of the manifest file itself.
- Preserve all existing artifact paths, schemas, trial IDs, rankings, evidence
  requests, and sandbox boundary fields.
- Add focused tests proving manifest hash metadata matches written files.
- Update sandbox contract and stage closeout docs.

## Allowed Paths

- `docs/work_packets/WPR106-252-sandbox-artifact-integrity-hashes.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_INTEGRITY_HASHES_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/store.py`
- `src/tradingbotsuite/research_sandbox/suite.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Run manifests include SHA-256 and byte-size metadata for `summary.parquet`,
  `rankings.parquet`, `evidence_requests.json`, and
  `evidence_requests.parquet`.
- Suite manifests include SHA-256 and byte-size metadata for
  `suite_index.json`, `suite_index.parquet`, `suite_evidence_requests.json`,
  and `suite_evidence_requests.parquet`.
- Hash metadata matches the actual written files.
- Manifest hashing avoids self-referential manifest hashes.
- Generated artifacts and result rows remain sandbox-only, research-only,
  non-promotable, and ineligible for candidate packs.
- Validation includes focused sandbox tests, import-boundary tests, package
  compile, and the contract baseline when the local validation environment
  allows pytest-asyncio socket setup.

## Boundary

This packet changes local sandbox artifact metadata only. It does not alter
strategy math, scoring formulas, strict validation, candidate-pack gates,
live/paper signals, sizing, order placement, runtime mode, live configuration,
provider downloads, descriptor archive loading, or promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. Sandbox run manifests now include
`artifact_integrity` metadata for `summary.parquet`, `rankings.parquet`,
`evidence_requests.json`, and `evidence_requests.parquet`. Sandbox suite
manifests now include the same SHA-256 and byte-size metadata for
`suite_index.json`, `suite_index.parquet`, `suite_evidence_requests.json`, and
`suite_evidence_requests.parquet`.

The manifest itself is intentionally not hashed inside the manifest to avoid a
self-referential digest. Artifact paths, schemas, trial IDs, rankings, evidence
requests, and sandbox boundary fields are unchanged.

Focused coverage independently recomputes SHA-256 and byte sizes from the
written files and verifies manifest metadata for both run and suite artifacts.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 76 sandbox tests passed, 11 import-boundary tests passed,
package compileall passed, and the full contract baseline passed with 461
tests.
