# Stage R106 Sandbox Run Source Container Metadata Report

Date: 2026-06-19
Packet: `WPR106-301-sandbox-run-source-container-metadata`
Owner: Codex Research Agent
Status: closed

## Summary

WPR106-301 propagates bounded ZIP/TAR container member-selection diagnostics
from loaded archive-backed market frames into actual sandbox sweep provenance.
Agents can now inspect selected container suffixes, selected/loadable member
counts, bounded member-name samples, and available suffix counts directly from
run manifests, result/ranking metadata, evidence-request source context, and
strict-validation request bundle rows.

## Implementation

- Archive sweep `market_source` payloads now copy bounded
  `container_member_metadata` from loaded market-frame normalization metadata.
- Result metadata, run `market_sources`, ranking Parquet `metadata`,
  evidence-request `source_trial_context.market_source`, and validation bundle
  `source_market_source` preserve that payload.
- Strict-validation request bundle descriptor rows now expose searchable
  convenience fields: `source_container_member_metadata`,
  `source_container_kind`, `source_selected_member_suffix`,
  `source_selected_member_count`, `source_selected_member_name_sample`,
  `source_selected_member_names_truncated`,
  `source_available_member_suffix_counts`,
  `source_available_member_suffix_count`, and
  `source_loadable_member_count`.
- Non-container sources keep empty/default bundle convenience fields, and
  archive sweep market sources omit empty container fields.
- Added a focused ZIP-backed archive sweep test that checks run manifest,
  ranking metadata, evidence-request context, bundle JSON, and bundle Parquet
  propagation.

## Boundary

This packet only changes provenance diagnostics. It does not change archive
loading, market routing, trial IDs, sweep metrics, ranking math, blocker
semantics, eligibility flags, evidence-request selection, strict validation, or
candidate-pack behavior. Archive members remain read in memory by the existing
loader and are not extracted to disk. No provider download, strict validation
execution, candidate-pack write, paper/live signal, sizing, order placement,
runtime-mode change, live configuration write, source archive mutation, member
extraction, or promotion claim exists.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "archive_sweep_preserves_container_metadata"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- 1 focused archive-sweep container provenance test passed.
- 164 sandbox tests passed.
- Package compileall passed.
- 11 import-boundary tests passed.
- 461 contract tests passed.
