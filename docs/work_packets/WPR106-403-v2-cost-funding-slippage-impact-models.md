# WPR106-403 V2 Cost Funding Slippage Impact Models

Status: closed
Owner: Codex Research Agent
Created: 2026-06-21

## Objective

Implement Phase 12 of `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md`: add
first-class v2 cost, funding, spread, slippage, impact, capacity, cost-manifest,
and stress-matrix behavior to the research-only backtest engine.

This packet extends the Phase 11 vectorized engine artifacts. It does not add
ledger append workflow, Lead Book workflow, UI, paper/live behavior, order
placement, sizing, runtime-mode changes, candidate packs, or promotion
behavior.

## Audit IDs

- `V2-AUD-COST-001`

## Dependencies

- Phase 11 backtest engine and run artifact contract.
- `docs/contracts/backtest_engine_contract.md`
- `docs/contracts/run_artifact_contract.md`
- `docs/contracts/cost_model_contract.md`
- `src/tradingbotsuite/v2/backtest_engine/**`
- `src/tradingbotsuite/v2/costs/**`

## Allowed Paths

- `docs/contracts/backtest_engine_contract.md`
- `docs/contracts/run_artifact_contract.md`
- `docs/contracts/cost_model_contract.md`
- `src/tradingbotsuite/v2/costs/**`
- `src/tradingbotsuite/v2/backtest_engine/**`
- `tests/v2/**`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/work_packets/WPR106-403-v2-cost-funding-slippage-impact-models.md`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Constraints

- Preserve research-only, observe-only, non-promotable semantics.
- Cost outputs are research assumptions, not venue execution proof.
- No live venue/API reads, live order-placement imports, live configuration
  writes, runtime-mode changes, paper/live artifacts, sizing, or order
  placement.
- Gross-only reported or accepted results must fail closed.
- Missing cost evidence must not produce accepted metrics.
- Stress scenarios must be recorded separately from base assumptions.

## Acceptance Criteria

- Metrics include gross and net returns.
- Fees apply to turnover.
- Funding changes net results.
- Spread, slippage, and impact reduce net results.
- Oversized trades fail closed through a liquidity participation cap.
- `base`, `stress_2x`, and `stress_3x` cost sensitivity rows are produced.
- `cost_manifest.json` records cost model, hash, dimensions, stress matrix,
  and research-only boundary metadata.
- Gross-only results cannot enter ranked/promotable paths.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_cost_models_phase12.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

No broader non-v2 tests are required unless shared implementation files outside
the v2 shell are changed.

## Stop Conditions

- A no-touch live/runtime/order/sizing path must be modified.
- Maker fill assumptions require queue modeling or L2/event-driven evidence.
- Phase 13 ledger, Lead Book, UI, candidate-pack, paper/live, order, sizing,
  runtime, or promotion behavior becomes necessary.
- Cost and stress artifacts cannot be emitted deterministically for both
  completed and failed runs.

## Completion Notes

Closed on 2026-06-21.

- Added Phase 12 cost schemas and helpers:
  - `CostModelConfig`
  - `CostStressScenario`
  - `CostBreakdown`
  - deterministic cost model hashing
  - fee, funding, spread, slippage, impact, and capacity calculations
  - `cost_manifest_v1` manifest construction
- Extended `BacktestRunConfig`, `BacktestMetrics`, and `RunManifest` with cost
  model hash, spread/impact/transaction metrics, capacity counts, and the
  required `cost_stress` artifact.
- Replaced inline Phase 11 fee/slippage math with the Phase 12 cost model.
- Added base, `stress_2x`, and `stress_3x` vectorized cost replays and writes
  `cost_stress.parquet`.
- Extended `cost_manifest.json` with cost model config/hash, fee/funding,
  spread/slippage, impact, capacity, stress matrix, and cost sensitivity.
- Added fail-closed liquidity participation-cap rejection.
- Kept failed/event-driven-placeholder runs on the same artifact contract with
  empty required cost-stress artifacts.
- Updated cost, backtest-engine, and run-artifact contracts.
- Marked `V2-AUD-COST-001` as `self_checked`.
- No ledger, Lead Book, UI, paper/live behavior, order placement, sizing,
  runtime-mode change, candidate-pack writing, or promotion behavior was
  implemented.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_cost_models_phase12.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Result:

- Focused Phase 12 tests passed: 8 passed.
- Full v2 tests passed: 89 passed.
- `compileall` for `src\tradingbotsuite\v2` passed.
- Full `compileall` for `src\tradingbotsuite` passed.
- Contract tests passed: 462 passed.
- `git diff --check` passed with LF-to-CRLF warnings only for existing
  text-file line-ending behavior.
