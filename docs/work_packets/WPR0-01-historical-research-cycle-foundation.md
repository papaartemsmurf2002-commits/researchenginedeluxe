# Work Packet WPR0-01 - Historical Research Cycle Foundation

Stage: Stage R0/R1/R4/R5 historical research computation foundation
Substages: R0 stop misleading empirical outputs, R1 full-cycle skeleton, focused holding-window alignment, optimizer/stability foundation
Owner: Codex Research Agent
Status: closed
Date: 2026-05-04

## Objective

Convert the next research wave from planning-only outputs toward reproducible historical computation without touching live execution. The immediate target is to prevent placeholder experiment metrics from being interpreted as evidence and to add a research-only historical cycle command that writes auditable artifacts from synthetic historical inputs.

## Allowed Paths

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/work_packets/WPR0-01-historical-research-cycle-foundation.md`
- `docs/stage_reports/STAGE_R0_R1_HISTORICAL_RESEARCH_FOUNDATION_REPORT.md`
- `src/tradingbotsuite/research/experiment_runner.py`
- `src/tradingbotsuite/research/command_registry.py`
- `src/tradingbotsuite/research_cycle/**`
- `src/tradingbotsuite/backtesting/engine.py`
- `src/tradingbotsuite/backtesting/splits.py`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/optimization/**`
- `configs/research/**`
- `tests/tradingbotsuite/test_experiment_runner.py`
- `tests/contracts/test_backtest_contracts.py`
- `tests/contracts/test_research_cycle_contract.py`
- `tests/historical/**`
- `tests/optimization/**`
- `tests/live/test_preflight.py`

## Scope

- Mark generic experiment-runner summary outputs as `contract_only` when they are not backed by real backtest manifests.
- Add tests that reject contract-only rows as candidate evidence.
- Align backtest holding-window support with the strategy contract for `1h`, `4h`, `12h`, `24h`, `72h`, and `7d`.
- Add a `research_cycle` package with a spec parser and runner that writes the required full-cycle manifest set.
- Add `run-historical-research-cycle --spec ...` as a research command.
- Keep all cycle outputs `research_only`, `observe_only`, and `promotion_ready: false`.
- Add synthetic full-cycle tests that prove the command writes real backtest-derived rankings and remains research-only.
- Add a dependency-light optimizer/stability foundation with deterministic cache keys, search-space expansion, serial/parallel equivalence, and spike rejection tests.

## Non-Scope

- No paper, shadow, testnet, or live execution.
- No order placement, live runtime mode changes, capital allocation, or live configuration writes.
- No promotion acceptance or `promotion_ready: true` output.
- No real-world performance claim from synthetic data.
- No full optimizer, feature DAG, or candidate-pack acceptance unless backed by focused follow-up packets.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_experiment_runner.py tests/contracts/test_backtest_contracts.py tests/contracts/test_research_cycle_contract.py tests/historical/test_full_cycle_synthetic.py tests/live/test_preflight.py tests/optimization -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m tradingbotsuite.main run-historical-research-cycle --help
```

## Exit Criteria

The packet exits when generic placeholder metrics cannot be accepted as empirical evidence, the historical research cycle command writes the required research-only artifacts from synthetic data, holding windows match strategy contracts, optimizer/stability foundations reject parameter spikes, and focused validation passes.

## Exit Evidence

- Focused packet validation: `39 passed` for experiment runner, backtest contract, research-cycle contract, synthetic full-cycle, and live preflight tests before optimizer additions.
- Contract baseline: `34 passed`.
- Optimizer focused validation: `6 passed`.
- Compile check: `python -m compileall -q src/tradingbotsuite` passed.
- CLI help check: `python -m tradingbotsuite.main run-historical-research-cycle --help` passed.
