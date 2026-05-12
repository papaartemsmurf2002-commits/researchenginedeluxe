# WPR97-07 Fastest Worker Scaling Default

Status: closed
Owner: Codex Research Agent
Stage: R97 aggressive CUDA/TensorCore stability search

## Goal

Test whether higher aggregate workers can be assigned reliably and improve the
default `fastest_exact` research-cycle route. If a higher setting is reliably
faster, update the default and benchmark evidence naming.

## Allowed Paths

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/**`
- `docs/work_packets/**`
- `src/tradingbotsuite/research_cycle/**`
- `tests/contracts/**`
- `tests/historical/**`

## Non-Goals

- Do not change live trading behavior, live config, order placement, promotion
  readiness, or sizing logic.
- Do not change backtest math, strategy signals, or candidate gates.
- Do not switch to a higher worker count unless it is assigned correctly and
  faster in local full-cycle testing.

## Worker Test Evidence

Synthetic 720-row full-cycle benchmark, three repeats per worker count:

| Workers | Median s | Min s | Max s | Assigned | Aggregate backend | Validation backend |
| ---: | ---: | ---: | ---: | --- | --- | --- |
| 15 | 8.560 | 8.541 | 8.672 | yes | `vector_fixed_holding` | `reference` |
| 24 | 8.518 | 8.421 | 8.686 | yes | `vector_fixed_holding` | `reference` |
| 32 | 8.490 | 8.466 | 8.620 | yes | `vector_fixed_holding` | `reference` |
| 48 | 8.474 | 8.453 | 8.512 | yes | `vector_fixed_holding` | `reference` |
| 64 | 8.605 | 8.570 | 8.647 | yes | `vector_fixed_holding` | `reference` |

Result: 48 workers was the fastest reliable median. 64 workers assigned
correctly but was slower, so it is not the default.

## Plan

1. Change default `fastest_exact` CPU worker count from 15 to 48.
2. Update benchmark labels/evidence from CPU15 to CPU48.
3. Update focused contract and historical tests.
4. Close with validation and a default smoke.

## Exit Evidence

- Changed default `fastest_exact` CPU worker count from 15 to 48.
- Updated historical benchmark backend comparison labels/evidence from CPU15 to
  CPU48.
- Focused compile and contract/historical/operator validation passed:
  `79 passed`.
- Stage evidence recorded in
  `docs/stage_reports/STAGE_R97_FASTEST_WORKER_SCALING_DEFAULT_REPORT.md`.
