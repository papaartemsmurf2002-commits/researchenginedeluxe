# Stage R106 Sandbox Next-Action Unindexed Iteration Manifests Report

Date: 2026-06-20
Packet: `WPR106-381-sandbox-next-action-unindexed-iteration-manifests`

## Summary

WPR106-381 improves the first-read dashboard path after a sandbox iteration has
run but before an agent has built an artifact catalog or iteration index. The
next-action report now performs bounded, read-only discovery of
`sandbox_iteration_manifest.json` files under the requested output root. When
such manifests exist and no index/catalog is available, the dashboard
recommends `index_rapid_strategy_sandbox_iterations` and lists exact manifest
paths to inspect next.

This keeps the dashboard in its intended role: it summarizes and points to
existing artifacts only. It does not index, recompute, validate, or promote
anything.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -k "next_action" -q`
  - `3 passed, 196 deselected`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  - `220 passed`
- `python -m compileall -q src\tradingbotsuite`
  - passed
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`
  - `26 passed`
- Ignored local CLI smoke with `TBS_RESEARCH_OUTPUT_DIR` set to
  `outputs\sandbox_smoke_wpr106_379\research_outputs`:
  `python -m tradingbotsuite.main show-rapid-strategy-sandbox-next-action --output-root <smoke-root> --output-dir next_action_smoke_wpr106_381 --limit 5`
  - returned `recommended_action: index_rapid_strategy_sandbox_iterations`
  - returned `unindexed_iteration_manifest_count: 1`
  - returned `strict_validation_executed: false` and `candidate_pack_written: false`

## Boundary Statement

This packet changes only read-only next-action dashboard guidance. It does not
execute sandbox sweeps, recompute evidence, index artifacts, execute strict
validation, write candidate packs, create paper/live signals, define sizing,
place orders, change runtime mode, write live configuration, claim candidate
evidence, or authorize promotion.
