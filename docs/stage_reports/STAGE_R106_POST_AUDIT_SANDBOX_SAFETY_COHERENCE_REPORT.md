# Stage R106 Post-Audit Sandbox Safety And Coherence Report

Date: 2026-06-20
Packet: `WPR106-362-post-audit-sandbox-safety-coherence`

## Summary

WPR106-362 repairs the highest-risk sandbox safety and provenance blockers
identified by `RAPID_STRATEGY_SANDBOX_AUDIT.md` before adding new feature
surface. The packet keeps the sandbox as a research-only triage layer and does
not execute strict validation, write candidate packs, mutate archive sources,
download provider data, or create live/paper/sizing/order/runtime/promotion
behavior.

## Changes

- Added `/outputs/` to `.gitignore` so generated output/dependency trees are
  not surfaced as review material by default.
- Added shared sandbox path helpers for safe path components and output-root
  containment.
- Made `SandboxRunSpec.run_id` reject path traversal, separators, drive-like
  names, trailing whitespace/dots, control characters, and reserved Windows
  device names.
- Made run and suite artifact writers resolve output directories under their
  configured output roots.
- Made sandbox boundary metadata include `live_config_writes_allowed: false`
  and `candidate_pack_writes_allowed: false`.
- Added recursive boundary validation so nested free-form strategy/source
  payloads cannot carry live/paper/order/sizing/promotion/candidate-pack
  authorization fields.
- Moved run artifact boundary validation before run-directory creation and
  before Parquet/JSON writes.
- Made artifact integrity verification reject manifest child paths that escape
  the run or suite manifest directory before reading or hashing them.
- Enforced run/descriptor effective-window intersections in compatibility
  preflight, shared-market sweeps, and descriptor-routed archive sweeps.
- Added effective-window metadata to preflight rows and market-source metadata.
- Updated trial identity to include `min_trades` and `rank_top_n`, and to use
  logical venue/source identity instead of local `data_path`/`manifest_path`
  strings when source integrity is available.
- Made sandbox proxy strategy metadata explicit and non-authorizing.
- Changed `baseline_no_trade` sandbox config compilation to `no_trade_proxy`,
  preventing active proxy trades from being attributed to a no-trade baseline.
- Added focused post-audit regression tests in
  `tests/research_sandbox/test_post_audit_safety.py`.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_post_audit_safety.py -q`
  - `14 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  - `189 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`
  - `23 passed`
- `python -m compileall -q src\tradingbotsuite`
  - passed
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - `461 passed`
- `$env:PYTHONPATH='src'; python -m pytest -q -p no:cacheprovider`
  - `1844 passed, 1 skipped, 1 warning`

The full-suite warning is the existing XGBoost mismatched-device warning.

## Boundary Statement

Sandbox outputs remain research-only, observe-only, sandbox-only,
non-promotable, non-candidate-evidence, and candidate-pack-ineligible. This
packet created no live signal, paper signal, sizing instruction,
order-placement instruction, runtime-mode change, live configuration write,
candidate-pack write, strict-validation execution, provider download, archive
source mutation, or promotion claim.

