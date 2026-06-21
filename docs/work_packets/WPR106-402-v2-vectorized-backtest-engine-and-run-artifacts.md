# WPR106-402 V2 Vectorized Backtest Engine And Run Artifacts

Status: closed
Owner: Codex Research Agent
Created: 2026-06-21

## Objective

Implement Phase 11 of `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md`: add
the first v2 vectorized backtest engine and shared run artifact contract so
validated Phase 9 data panels and Phase 10 declarative strategy specs can
produce reproducible research-only run directories.

This packet includes a minimal event-driven lane placeholder that writes the
same blocked/failure artifact contract. It does not implement event-driven
fills, Phase 12 detailed cost/funding/slippage/impact models, ledgers, Lead
Book workflow, UI, paper/live behavior, order placement, sizing,
runtime-mode changes, candidate packs, or promotion behavior.

## Audit IDs

- `V2-AUD-BTENG-001`

## Dependencies

- `docs/contracts/backtest_engine_contract.md`
- `docs/contracts/run_artifact_contract.md`
- `src/tradingbotsuite/v2/backtest_data/**`
- `src/tradingbotsuite/v2/strategy_specs/**`
- `src/tradingbotsuite/v2/costs/**`

## Allowed Paths

- `docs/contracts/backtest_engine_contract.md`
- `docs/contracts/run_artifact_contract.md`
- `src/tradingbotsuite/v2/backtest_engine/**`
- `src/tradingbotsuite/v2/cli/main.py`
- `tests/v2/**`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/work_packets/WPR106-402-v2-vectorized-backtest-engine-and-run-artifacts.md`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Constraints

- Preserve research-only, observe-only, non-promotable semantics.
- Engine inputs must be in-memory/local artifacts supplied by the caller; the
  engine must not call venue APIs.
- Do not place orders, create paper/live artifacts, change runtime mode, write
  live configuration, or add sizing/order-placement behavior.
- Gross-only runs must fail in reported/accepted modes.
- Missing data policy must be explicit; no silent forward-fill of
  PnL-critical prices.
- Same-bar execution optimism is not allowed unless explicitly labeled. The
  initial vectorized engine uses next-bar price basis for fills.
- Event-driven behavior remains a blocked placeholder with failure artifacts,
  not an execution implementation.

## Acceptance Criteria

- At least three declarative strategy templates run over the same data snapshot.
- Runs produce the required artifact directory:
  - `run_manifest.json`
  - `strategy_spec.json`
  - `params.json`
  - `data_manifest.json`
  - `validation_manifest.json`
  - `cost_manifest.json`
  - `metrics.json`
  - `equity_curve.parquet`
  - `daily_returns.parquet`
  - `trades.parquet`
  - `positions.parquet`
  - `per_instrument_metrics.parquet`
  - `fold_metrics.parquet`
  - `logs/log.txt`
- Runs are reproducible from `run_manifest.json` plus the artifact directory.
- Failed runs record failure artifacts.
- Funding/fees are represented in gross/net metrics even though deeper cost
  stress modeling remains Phase 12.
- Event-driven placeholder outputs the same artifact contract with blocked
  status.

## Validation

```powershell
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
- Detailed Phase 12 cost/funding/slippage/impact/capacity modeling, ledger
  append workflow, Lead Book workflow, candidate-pack, paper/live, order,
  sizing, runtime, or promotion behavior becomes necessary.
- The artifact contract cannot be emitted deterministically for both completed
  and failed runs.

## Completion Notes

Closed on 2026-06-21.

- Added Phase 11 backtest-engine schemas:
  - `BacktestRunConfig`
  - `StrategyContext`
  - `RunManifest`
  - `RunArtifactRef`
  - `BacktestMetrics`
  - `BacktestRunResult`
  - `EngineLane`
  - `RunStatus`
  - `MissingDataPolicy`
  - `ValidationStatus`
- Added `run_vectorized_backtest`, which:
  - compiles Phase 10 declarative specs to signal frames;
  - applies previous signals to explicit price-basis returns;
  - supports `next_bar_open`, `close`, `mark`, and `oracle` price bases;
  - enforces common-clock fail-closed missing data;
  - applies basic target-weight risk constraints from signal frames;
  - records gross and net returns separately;
  - includes initial fee, slippage, and funding PnL representation;
  - rejects gross-only runs;
  - writes deterministic research-only run artifacts.
- Added `run_event_driven_placeholder`, which writes the same failure artifact
  contract without claiming event-driven fill simulation.
- Added manifest-based metric recomputation for reproducibility checks.
- Required artifact directory is written with:
  - `run_manifest.json`
  - `strategy_spec.json`
  - `params.json`
  - `data_manifest.json`
  - `validation_manifest.json`
  - `cost_manifest.json`
  - `metrics.json`
  - `equity_curve.parquet`
  - `daily_returns.parquet`
  - `trades.parquet`
  - `positions.parquet`
  - `per_instrument_metrics.parquet`
  - `fold_metrics.parquet`
  - `logs/log.txt`
- Updated backtest-engine and run-artifact contracts.
- Marked `V2-AUD-BTENG-001` as `self_checked`.
- No detailed Phase 12 cost/funding/slippage/impact/capacity model, ledger
  append workflow, Lead Book workflow, UI, paper/live behavior, order
  placement, sizing, runtime-mode change, candidate-pack writing, or promotion
  behavior was implemented.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_backtest_engine_phase11.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_contract_docs.py -q
git diff --check
```

Result:

- Focused Phase 11 tests passed: 7 passed.
- Focused v2 tests passed: 81 passed.
- `compileall` for `src\tradingbotsuite\v2` passed.
- Full `compileall` for `src\tradingbotsuite` passed.
- Contract tests passed: 462 passed.
- Contract-doc smoke passed: 2 passed.
- `git diff --check` passed with LF-to-CRLF warnings only for existing
  text-file line-ending behavior.
