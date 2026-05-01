# Work Packet: WP6-01-strategy-plugin-library

Stage: Stage 6 - Strategy plugin system and baseline strategy library
Owner agent: Strategy Agent
Reviewer agent: QA Agent
Branch: `research/v3-experimental-engine`
Allowed paths:

- `src/tradingbotsuite/strategies/**`
- `src/tradingbotsuite/backtesting/engine.py`
- `configs/strategies/**`
- `tests/contracts/test_strategy_contracts.py`
- `tests/contracts/test_import_boundaries.py`
- `tests/integration/test_backtest_engine_fixture.py`
- `docs/contracts/strategy_contract.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WP6-01-strategy-plugin-library.md`
- `docs/stage_reports/STAGE_6_EXIT_REPORT.md`

Forbidden paths:

- live runtime execution behavior
- order placement adapters
- strategy code importing live execution modules
- generated data, secrets, databases, logs, and local cache artifacts

## Objective

Add a plugin-shaped strategy library so baseline institutional-style strategies, LC reference logic, and HMM/KNN diagnostics can all produce standardized research signals and run through the same Stage 5 backtest engine.

## Required source files read first

- `docs/contracts/strategy_contract.md`
- `docs/stage_reports/STAGE_5_EXIT_REPORT.md`
- `src/tradingbotsuite/backtesting/engine.py`
- `src/tradingbotsuite/features/registry.py`
- `src/tradingbotsuite/research/deterministic_datasets.py`
- `tests/integration/test_backtest_engine_fixture.py`
- `tests/contracts/test_import_boundaries.py`

## Implementation tasks

- Add strategy plugin contracts and signal-frame validation.
- Add strategy registry and config loader.
- Implement trend following, volatility breakout, range reversion, funding/basis, regime-adaptive, LC reference, HMM/KNN diagnostic, and no-trade plugins.
- Add strategy configs under `configs/strategies/`.
- Update the Stage 5 engine to consume strategy plugins instead of hardcoded strategy logic.
- Add strategy contract tests and same-engine integration tests for at least four baseline strategies.
- Extend import-boundary tests to strategy modules.

## Tests and validation commands

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_strategy_contracts.py -q
$env:PYTHONPATH='src'; python -m pytest tests/integration/test_backtest_engine_fixture.py -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_backtest_contracts.py tests/contracts/test_import_boundaries.py -q
```

## Acceptance evidence

- `src/tradingbotsuite/strategies/contracts.py`
- `src/tradingbotsuite/strategies/registry.py`
- `src/tradingbotsuite/strategies/trend.py`
- `src/tradingbotsuite/strategies/volatility_breakout.py`
- `src/tradingbotsuite/strategies/range_reversion.py`
- `src/tradingbotsuite/strategies/funding_basis.py`
- `src/tradingbotsuite/strategies/regime_adaptive.py`
- `src/tradingbotsuite/strategies/lc_reference.py`
- `src/tradingbotsuite/strategies/hmm_knn.py`
- `configs/strategies/*.json`
- `tests/contracts/test_strategy_contracts.py`
- `docs/stage_reports/STAGE_6_EXIT_REPORT.md`

## Handoff notes

Stage 7 can refactor HMM/KNN internals behind `hmm_knn_diagnostic_v1` without changing the backtest engine. Stage 8/optimization can sweep strategy configs through the same engine.
