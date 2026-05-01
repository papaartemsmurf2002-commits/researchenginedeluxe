# Work Packet: WP5-01-backtesting-engine

Stage: Stage 5 - Fast modular backtesting engine
Owner agent: Backtest Agent
Reviewer agent: QA Agent
Branch: `research/v3-experimental-engine`
Allowed paths:

- `src/tradingbotsuite/backtesting/**`
- `tests/contracts/test_backtest_contracts.py`
- `tests/contracts/test_import_boundaries.py`
- `tests/unit/test_execution_simulator.py`
- `tests/integration/test_backtest_engine_fixture.py`
- `data/research/benchmarks/backtest_engine_baseline.json`
- `data/research/benchmarks/optimizer_baseline.json`
- `docs/contracts/backtest_contract.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WP5-01-backtesting-engine.md`
- `docs/stage_reports/STAGE_5_EXIT_REPORT.md`

Forbidden paths:

- live runtime execution behavior
- order placement adapters
- legacy `tradingbot.backtest` refactors outside compatibility work
- secrets, databases, logs, and local cache artifacts

## Objective

Create a research-only modular backtesting engine with deterministic artifacts, explicit execution assumptions, costed metrics, and benchmark baselines. The legacy `tradingbot.backtest` remains untouched and is no longer the research engine foundation for new Stage 5 work.

## Required source files read first

- `docs/contracts/backtest_contract.md`
- `docs/contracts/strategy_contract.md`
- `src/tradingbot/backtest.py`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/research/deterministic_datasets.py`
- `src/tradingbotsuite/features/alignment.py`
- `src/tradingbotsuite/features/registry.py`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `tests/tradingbotsuite/test_experiment_runner.py`

## Implementation tasks

- Add `src/tradingbotsuite/backtesting/engine.py`.
- Add `execution_sim.py`, `costs.py`, `portfolio.py`, `metrics.py`, and `benchmark.py`.
- Write deterministic backtest outputs with the exact required artifact names.
- Support baseline trend and baseline no-trade strategies through the same engine.
- Include fees, slippage, spread, and funding in net return.
- Support `1h`, `24h`, `72h`, and `7d` holding windows.
- Add reproducibility hashes and cache-key inputs.
- Add benchmark baseline JSON artifacts.
- Extend import-boundary tests to the new backtesting package.

## Tests and validation commands

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_backtest_contracts.py -q
$env:PYTHONPATH='src'; python -m pytest tests/unit/test_execution_simulator.py -q
$env:PYTHONPATH='src'; python -m pytest tests/integration/test_backtest_engine_fixture.py -q
$env:PYTHONPATH='src'; python -m tradingbotsuite.main benchmark-research-experiment --help
```

## Acceptance evidence

- `src/tradingbotsuite/backtesting/engine.py`
- `src/tradingbotsuite/backtesting/execution_sim.py`
- `src/tradingbotsuite/backtesting/costs.py`
- `src/tradingbotsuite/backtesting/portfolio.py`
- `src/tradingbotsuite/backtesting/metrics.py`
- `src/tradingbotsuite/backtesting/benchmark.py`
- `tests/contracts/test_backtest_contracts.py`
- `tests/unit/test_execution_simulator.py`
- `tests/integration/test_backtest_engine_fixture.py`
- `data/research/benchmarks/backtest_engine_baseline.json`
- `data/research/benchmarks/optimizer_baseline.json`
- `docs/stage_reports/STAGE_5_EXIT_REPORT.md`

## Handoff notes

Stage 6 can build strategy plugins on top of `BacktestSpec.strategy_id` and the shared execution/cost/metrics stack. Optimizer benchmarking is registered as a baseline placeholder until the strategy plugin system expands the search space.
