# Stage R106 Sandbox Artifact Integrity Hashes Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-252-sandbox-artifact-integrity-hashes.md`
Status: closed

## Summary

WPR106-252 improves sandbox reproducibility and agent handoff quality by adding
SHA-256 and byte-size metadata for compact run and suite child artifacts.
Agents can now verify that Parquet/JSON summaries, rankings, and
evidence-request descriptors match the manifest without executing strict
validation.

## Implementation

- Added child artifact integrity metadata to
  `src/tradingbotsuite/research_sandbox/store.py`.
- Run manifests now record hashes and byte sizes for `summary.parquet`,
  `rankings.parquet`, `evidence_requests.json`, and
  `evidence_requests.parquet`.
- Added the same metadata to suite manifests in
  `src/tradingbotsuite/research_sandbox/suite.py`.
- Suite manifests now record hashes and byte sizes for `suite_index.json`,
  `suite_index.parquet`, `suite_evidence_requests.json`, and
  `suite_evidence_requests.parquet`.
- The manifest file is not hashed inside itself, avoiding circular digest
  semantics.
- The change does not alter artifact paths, schemas, deterministic trial IDs,
  scores, ranks, evidence-request descriptors, or sandbox boundary payloads.

## Boundary

This packet changes sandbox artifact metadata only. It does not execute strict
validation, write candidate packs, create live/paper signals, define sizing,
place orders, change runtime mode, write live configuration, download provider
data, or claim promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 76 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 461 passed
```

## Remaining Work

Run and suite child artifacts are now directly verifiable from manifests. Later
work can add a read-only verification CLI if repeated manual integrity checks
become a workflow bottleneck.
