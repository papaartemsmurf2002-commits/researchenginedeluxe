# Stage R106 Sandbox Container Multimember Loader Report

Date: 2026-06-19
Packet: `WPR106-297-sandbox-container-multimember-loader`
Owner: Codex Research Agent
Status: closed

## Summary

WPR106-297 changes ZIP and TAR/TGZ sandbox loading from first-member-only to
deterministic multimember loading. When a local container has several members
of the selected highest-priority loadable type, the sandbox now reads all of
those members, concatenates the raw frames, and then applies the existing 2024+
market-frame normalization path.

This removes a quiet agent-workflow trap where chunked venue drops inside one
container could appear loadable while only the first chunk contributed rows.

## Implementation

- ZIP member names are evaluated in deterministic sorted order.
- TAR/TGZ members are evaluated in deterministic member-name order.
- The loader selects one highest-priority suffix class, then concatenates all
  members of that class.
- Lower-priority member types are not mixed into the same loaded frame.
- Existing plain and gzip-compressed CSV/TSV/JSON/JSONL/NDJSON parsing paths
  are reused.
- Hyperliquid L2 source-transformation metadata is merged across member frames
  so flattened row counts remain visible after concatenation.
- Added focused tests for ZIP JSONL member concatenation, TAR CSV member
  concatenation, archive manifest normalized row counts, and multimember L2
  source-transformation count merging.

## Boundary

This packet only changes already-local sandbox archive member loading and
manifest diagnostics. Members are read in memory and are not extracted to disk.
No provider download, strict validation execution, candidate-pack write,
paper/live signal, sizing, order placement, runtime-mode change, live
configuration write, source archive mutation, or promotion claim exists.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "multimember or concatenates_zip or concatenates_tar"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- 4 focused container multimember tests passed.
- 157 sandbox tests passed.
- Package compileall passed.
- 11 import-boundary tests passed.
- 461 contract tests passed.
