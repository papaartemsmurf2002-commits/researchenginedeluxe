# WPR8-01 Strategy Comparator Contract Hardening

Status: closed
Owner: Codex Research Agent
Stage: Stage R8 strategy comparator contract hardening
Opened: 2026-05-04
Closed: 2026-05-04

## Objective

Close the remaining Stage R8 audit gaps by making baseline comparator coverage explicit in historical research cycles and making strategy plugin/config/signal contracts fail closed before invalid research evidence can be emitted.

## Allowed paths

- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR8-01-strategy-comparator-contract-hardening.md`
- `docs/stage_reports/STAGE_R8_STRATEGY_COMPARATOR_CONTRACT_HARDENING_REPORT.md`
- `src/tradingbotsuite/backtesting/engine.py`
- `src/tradingbotsuite/research_cycle/runner.py`
- `src/tradingbotsuite/research_cycle/spec.py`
- `src/tradingbotsuite/strategies/contracts.py`
- `src/tradingbotsuite/strategies/registry.py`
- `src/tradingbotsuite/strategies/_helpers.py`
- `src/tradingbotsuite/strategies/no_trade.py`
- `src/tradingbotsuite/strategies/parameters.py`
- `tests/contracts/test_strategy_contracts.py`
- `tests/contracts/test_research_cycle_contract.py`
- `tests/historical/test_full_cycle_synthetic.py`
- `tests/integration/test_backtest_engine_fixture.py`

## Non-goals

- No live, paper, shadow, testnet, canary, promotion, order-placement, or capital allocation work.
- No new strategy alpha family.
- No candidate acceptance or promotion-ready artifact path.
- No broad rewrite of strategy implementations unless required for contract safety.
- No persistent backtest execution-cache behavior.

## Implementation plan

1. Add explicit comparator roles and metadata hashes to generated candidates, rankings, and backtest index rows.
2. Add historical-cycle comparator coverage evidence so explicit optimizer search spaces cannot silently omit no-trade/default transparent baselines.
3. Build strategy parameter metadata from generated candidate strategies rather than only declared spec strategies.
4. Make strategy plugin construction reject unsupported holding periods and feature sets with explicit errors.
5. Merge per-holding-window strategy metadata defaults before user-supplied runtime config.
6. Strengthen signal-frame validation for finite times, non-empty fields, numeric holding windows, strength/confidence bounds, and strict boolean research-only values.
7. Add focused contract and historical-cycle tests for comparator policy and fail-closed strategy behavior.

## Exit criteria

- Historical-cycle candidate-space manifests expose comparator policy and coverage.
- Explicit optimizer search-space cycles still carry baseline comparator evidence.
- Candidate rankings and backtest index rows include comparator role and strategy metadata audit fields.
- Strategy parameter metadata covers generated candidate strategies.
- Unsupported strategy feature/window configs fail closed at plugin construction.
- Malformed signal frames are rejected by strategy contract validation.
- Focused tests, contracts, compileall, and diff checks pass.

## Risk controls

- Comparator evidence is research-only and does not affect live behavior.
- Comparator fields must not mark any candidate `promotion_ready`.
- Defaults merge must preserve user-supplied parameter overrides.
- Tests must include explicit search-space mode because that is where comparator omission was found.

## Exit evidence

- Candidate IDs now hash resolved parameter configs after per-holding-window defaults are applied.
- Candidate-space manifests now record candidate-derived strategy metadata, comparator policy, and per-group comparator coverage.
- Explicit optimizer search-space cycles inject no-trade and compatible transparent default comparators.
- Candidate rankings and backtest index rows now carry comparator role, baseline group, strategy metadata hash, and resolved/specified parameter JSON.
- Rankings include comparator candidate IDs, metrics paths, and expectancy deltas against no-trade and transparent default baselines.
- Strategy plugin construction rejects unsupported feature/window combinations.
- Strategy config loading rejects unknown strategies, unknown parameters, non-finite numeric values, and unsupported feature/window combinations.
- Signal-frame validation requires strict research-only booleans, finite timestamps/holding windows, bounded strength/confidence, non-empty policy fields, and exit metadata fields.
- Backtest signal artifacts now mirror `BacktestSpec` exit policy, target, and stop fields.
- Reviewer rechecks reported no blocking findings after fixes.

## Validation

- `python -m compileall -q src/tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_strategy_contracts.py tests/contracts/test_research_cycle_contract.py tests/historical/test_full_cycle_synthetic.py tests/integration/test_backtest_engine_fixture.py tests/contracts/test_backtest_contracts.py -q` passed: 41 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed: 57 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/historical -q` passed: 8 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/backtesting tests/unit/test_execution_simulator.py tests/integration/test_backtest_engine_fixture.py tests/live/test_preflight.py -q` passed: 51 passed.
- `git diff --check` passed with only existing LF-to-CRLF warnings.
