# WPR97-02 Default Accelerated Runtime Polish

Status: closed
Owner: Codex Research Agent
Date: 2026-05-12

## Purpose

Make the research-cycle runtime prefer the accelerated path by default while
preserving fail-closed research boundaries and CPU/reference fallback evidence.

Default acceleration means historical research cycles resolve to `auto` with the
R97 exact batched CUDA profile. When CUDA is unavailable or unsupported, the
existing vector/reference paths remain the fallback and must record why.

## Allowed Paths

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/**`
- `docs/work_packets/**`
- `src/tradingbotsuite/backtesting/**`
- `src/tradingbotsuite/optimization/**`
- `src/tradingbotsuite/research_cycle/**`
- `tests/backtesting/**`
- `tests/contracts/**`
- `tests/historical/**`
- `tests/optimization/**`

## Scope

- Change research-cycle defaults to accelerated `auto` routing with
  `gpu_execution_profile: cuda_exact_batched`.
- Keep CPU vector/reference as the deterministic fallback path.
- Add and update tests for default routing, parity/error checks, fallback
  evidence, and benchmark stability.
- Run longer combined validation and local CUDA parity checks before push.

## Non-Goals

- No live trading behavior, live configuration, promotion readiness, order
  placement, or sizing logic changes.
- No speedup claim unless benchmark and parity evidence explicitly support it.
- No Tensor Core use for final accounting or candidate acceptance.

## Validation Result

Passed on 2026-05-12:

- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - `413 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\backtesting tests\optimization tests\historical\test_research_cycle_benchmark.py tests\historical\test_full_cycle_synthetic.py tests\historical\test_full_cycle_local_fixture_pack.py -q`
  - `167 passed, 1 skipped`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q`
  - `152 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q`
  - `32 passed`
- Longer local CUDA parity script on RTX 5070 Ti
  - 5 deterministic 720-row cases passed with max metric diff `0.0`
- `git diff --check`

Stage report:
`docs/stage_reports/STAGE_R97_DEFAULT_ACCELERATED_RUNTIME_POLISH_REPORT.md`
