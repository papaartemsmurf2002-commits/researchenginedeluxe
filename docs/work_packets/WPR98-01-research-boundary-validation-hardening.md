# WPR98-01 Research Boundary Validation Hardening

Status: closed
Owner: Codex Research Agent
Stage: R98 research boundary validation hardening

## Goal

Implement the highest-fit findings from the orchestration master brief and
subagent crosscheck without reopening broad discovery research. This packet
tightens fail-closed research boundary metadata, validation-floor evidence, and
CLI/package clarity.

## Allowed Paths

- `pyproject.toml`
- `README.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/contracts/boundary_contract.md`
- `docs/stage_reports/**`
- `docs/work_packets/**`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/cli.py`
- `src/tradingbotsuite/research/**`
- `src/tradingbotsuite/research_discovery/**`
- `tests/live/**`
- `tests/research_discovery/**`
- `tests/tradingbotsuite/**`

## Scope

1. Normalize legacy research dataset/model/evaluation artifacts so they carry
   `research_only: true`, `observe_only: true`, and
   `promotion_ready: false`; remove the old replay-evaluation path that could
   report promotion readiness from local research metrics.
2. Make discovery validation floors require explicit passing exit-lab gate
   status for candidate-ready evidence, not only a generic complete status.
3. Validate discovery validation-floor blocker-registry hash integrity in the
   candidate-pack bridge.
4. Add a canonical `tradingbotsuite` console script for the active CLI while
   keeping the legacy `tradingbot` script as compatibility-only.
5. Refresh boundary documentation and README CLI guidance for the current
   command surface.

## Non-Goals

- No live trading behavior, live config writes, order placement, runtime-mode
  changes, promotion authorization, candidate-pack writing, or sizing logic.
- No broad package distribution rename in this packet; changing
  `project.name` is deferred because it can affect installed-environment
  compatibility outside the research-boundary fix.
- No wholesale output-dir allowlist refactor; that should be a later dedicated
  packet because many CLI handlers and tests are involved.
- No generated research artifact mutation.

## Validation Plan

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_research.py tests\research_discovery\test_validation_floors.py tests\research_discovery\test_candidate_pack_bridge.py tests\live -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

## Exit Evidence

Completed on 2026-05-13.

Implemented:

- Legacy research dataset, model-training, calibrated-artifact, and replay
  evaluation manifests now carry fail-closed research boundary metadata:
  `research_only: true`, `observe_only: true`, `promotion_ready: false`, and
  explicit non-live/non-sizing/non-control usage fields.
- Replay evaluation metrics can no longer report promotion readiness from local
  research metrics; they always include the
  `research_only_not_live_promotable` failure.
- Validation-floor candidate-ready evidence now requires an explicit
  `exit_lab_gate_status: passed`; a generic `exit_lab_status: complete` is not
  enough.
- Candidate-pack bridge validation now fails closed on missing, mismatched, or
  stale blocker-registry hash evidence and on validation-floor gate artifacts
  that omit `exit_lab_gate_status`.
- Added the canonical `tradingbotsuite` console script while preserving the
  legacy `tradingbot` entrypoint for compatibility.
- Refreshed README, boundary contract, known issues, and closeout report.

Deferred or intentionally not implemented:

- The package distribution name was not renamed from `tradingbot-framework`;
  this is an installed-environment compatibility risk and belongs in a
  dedicated packaging packet.
- Broad CLI output-directory allowlist hardening was not folded into this
  packet because it touches many handlers and should be isolated.
- A production no-regime-baseline ladder report was identified as useful
  future research-discovery work, but was outside this boundary-validation
  packet.

Validation passed:

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

Warnings were pre-existing pandas FutureWarnings and XGBoost device fallback /
CuPy CUDA-path warnings in local test environments.
