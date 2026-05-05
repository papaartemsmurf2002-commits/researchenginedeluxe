# Work Packet WPR6-08-11 - Exit Sequencing, Strategy Hardening, And Candidate Pack Foundation

Stage: Stage R6/R8/R11 research hardening wave
Substages: R6 exit sequencing, R8 strategy library hardening, R11 research candidate pack foundation
Owner: Codex Research Agent
Status: closed
Date: 2026-05-04

## Objective

Continue converting the research branch into a trusted historical research machine by extending exit-policy correctness, adding explicit strategy parameter metadata, and creating a research-only candidate pack foundation. The packet must preserve all existing research/live boundaries and leave empirical acceptance blocked unless evidence gates are explicitly satisfied by reproducible artifacts.

## Allowed Paths

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/work_packets/WPR6-08-11-exit-strategy-candidate-pack-hardening.md`
- `docs/stage_reports/STAGE_R6_R8_R11_RESEARCH_HARDENING_REPORT.md`
- `src/tradingbotsuite/backtesting/exits.py`
- `src/tradingbotsuite/backtesting/execution_sim.py`
- `src/tradingbotsuite/backtesting/engine.py`
- `src/tradingbotsuite/backtesting/__init__.py`
- `src/tradingbotsuite/strategies/_helpers.py`
- `src/tradingbotsuite/strategies/parameters.py`
- `src/tradingbotsuite/strategies/__init__.py`
- `src/tradingbotsuite/research_cycle/runner.py`
- `src/tradingbotsuite/research_artifacts/**`
- `tests/backtesting/**`
- `tests/contracts/test_strategy_contracts.py`
- `tests/contracts/test_backtest_contracts.py`
- `tests/historical/**`
- `tests/research_artifacts/**`
- `tests/unit/test_execution_simulator.py`

## Scope

- Add deterministic triple-barrier exit-policy primitives with MAE/MFE and lower-timeframe ordering proof.
- Ensure optimistic same-bar or same-lower-bar stop/target ambiguity is rejected instead of guessed.
- Add signal-level exit barrier fields while preserving existing signal contracts.
- Add strategy parameter metadata with parameter spaces, per-holding defaults, signal-density controls, and documented failure modes.
- Surface strategy parameter metadata in research-cycle candidate manifests.
- Add a research-only candidate pack writer that packages evidence only when gates pass and keeps outputs non-promotable.
- Add focused tests for exit ordering, strategy metadata, and candidate-pack boundaries.

## Non-Scope

- No paper, shadow, testnet, or live execution.
- No promotion-ready candidate manifests or live input artifacts.
- No order placement, live runtime mode changes, or live configuration writes.
- No dependency-heavy vector engine or benchmark gate in this packet.
- No claim that synthetic or single-fixture results are sufficient for empirical acceptance.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/backtesting tests/contracts/test_strategy_contracts.py tests/contracts/test_backtest_contracts.py tests/historical tests/research_artifacts -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
python -m compileall -q src/tradingbotsuite
```

## Exit Criteria

The packet exits when lower-timeframe barrier ordering is deterministic and guarded, strategy parameter metadata is available to research-cycle artifacts, research candidate packs are explicitly research-only/non-promotable, and validation passes.

## Exit Evidence

- Added lower-timeframe triple-barrier exit sequencing with ordered target/stop handling, conservative same-child-bar stop behavior, symbol isolation, and fail-closed coverage checks.
- Backtest manifests and cache identity now include lower-timeframe dataset hashes when lower-timeframe inputs are used.
- Unknown exit policies fail closed; fixed holding-window behavior remains the default.
- Added strategy-owned parameter metadata with parameter spaces, holding-window defaults, signal-density controls, and failure modes.
- Research-cycle candidate-space manifests now include strategy parameter metadata, default candidates use strategy-owned per-window defaults, and unsupported strategy/feature/window combinations are filtered or rejected before backtests.
- Added research-only candidate pack artifacts under `src/tradingbotsuite/research_artifacts`; packs require explicit research-pack eligibility, reject synthetic/live-adjacent evidence, and remain `research_only`, `observe_only`, and `promotion_ready: false`.
- Synthetic full-cycle runs still write no candidate packs.

Validation completed:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/backtesting tests/contracts/test_strategy_contracts.py tests/contracts/test_backtest_contracts.py tests/historical tests/research_artifacts tests/unit/test_execution_simulator.py -q
# 44 passed

$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
# 40 passed

$env:PYTHONPATH='src'; python -m pytest tests/live/test_preflight.py -q
# 23 passed

python -m compileall -q src/tradingbotsuite
# passed
```
