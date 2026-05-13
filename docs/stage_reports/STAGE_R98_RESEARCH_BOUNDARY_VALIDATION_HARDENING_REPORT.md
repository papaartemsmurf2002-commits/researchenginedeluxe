# Stage R98 Research Boundary Validation Hardening Report

Date: 2026-05-13
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR98-01-research-boundary-validation-hardening.md`

## Summary

WPR98-01 implemented the highest-fit findings from the orchestration master
brief and subagent crosscheck without reopening broad strategy research. The
stage hardens legacy research artifact metadata, validation-floor evidence, and
CLI/package documentation while keeping all outputs research-only.

## Changes

- Added shared research artifact boundary metadata in
  `src/tradingbotsuite/research/live_readiness.py`.
- Applied fail-closed boundary metadata to dataset, model-training,
  calibrated-artifact, and replay-evaluation outputs.
- Prevented replay evaluation from reporting promotion readiness from local
  research metrics.
- Required explicit `exit_lab_gate_status: passed` for validation-floor
  candidate-ready evidence.
- Preserved both `exit_lab_status` and `exit_lab_gate_status` in validation
  gate artifacts.
- Added candidate-pack bridge checks for blocker-registry hash integrity and
  current blocker-registry payload matching.
- Added the canonical `tradingbotsuite` console script and kept legacy
  `tradingbot` compatibility entrypoint.
- Updated README and boundary documentation to describe the current command
  surface.

## Boundary

All changed research outputs remain:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- not live signal inputs
- not position sizing inputs
- not operator, execution, or runtime-control inputs

No live trading behavior, live configuration, order placement, runtime mode,
candidate-pack writing, promotion authorization, or sizing logic changed.

## Deferred Items

- The package distribution name remains `tradingbot-framework`. Renaming it is
  deferred because it can affect installed-environment compatibility outside
  this boundary-validation fix.
- Broad CLI output-directory allowlist hardening was not included; it should be
  isolated in a future packet because it touches many command handlers.
- A production no-regime-baseline ladder report remains useful future
  discovery work, but was outside the WPR98 boundary.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_research.py tests\research_discovery\test_validation_floors.py tests\research_discovery\test_candidate_pack_bridge.py tests\live -q
# 58 passed, 2 warnings

$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_validation_floors.py tests\research_discovery\test_candidate_pack_bridge.py -q
# 38 passed

$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_research.py tests\live\test_cli_boundary.py -q
# 22 passed, 2 warnings

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 414 passed

$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
# 156 passed

$env:PYTHONPATH='src'; python -m pytest tests\live -q
# 49 passed

$env:PYTHONPATH='src'; python -m pytest -q
# 1320 passed, 1 skipped, 92 warnings

git diff --check
# passed with line-ending warnings only
```

The remaining warnings are existing pandas FutureWarnings and local
XGBoost/CuPy fallback warnings; no new failure remains open from this stage.

## Decision

WPR98-01 is closed. The branch remains research-only and is ready for the next
orchestrated research packet.
