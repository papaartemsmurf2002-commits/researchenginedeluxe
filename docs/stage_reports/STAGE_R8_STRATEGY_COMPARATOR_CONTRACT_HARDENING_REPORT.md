# Stage R8 Strategy Comparator Contract Hardening Report

Status: closed - comparator policy and strategy contracts hardened
Owner: Codex Research Agent
Date: 2026-05-04

## Scope

This wave completed a bounded Stage R8 hardening slice:

- Historical-cycle candidates now carry comparator role, baseline group, strategy metadata hash, resolved parameters, and specified parameters.
- Candidate identity is based on resolved parameters after per-holding-window defaults are applied.
- Candidate-space manifests now build strategy metadata from generated candidate strategies and include baseline comparator policy plus coverage rows.
- Explicit optimizer search-space cycles now inject no-trade and compatible transparent default comparators.
- Candidate rankings now include no-trade and transparent comparator IDs, metrics paths, and expectancy deltas.
- Backtest index rows now include comparator and strategy metadata audit fields.
- Strategy plugin construction now fails closed for unsupported feature sets and holding windows.
- Strategy config loading rejects unknown strategies, unknown parameters, non-finite numeric parameters, and unsupported feature/window combinations.
- Signal-frame validation now rejects malformed signal time, empty required fields, out-of-range strength/confidence, non-finite holding windows, non-strict `research_only`, and missing exit metadata fields.
- Backtest signal artifacts now receive `exit_policy_id`, `target_return`, and `stop_return` from `BacktestSpec`.

## Path Audit

WPR8-specific edits were confined to the packet's allowed paths:

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR8-01-strategy-comparator-contract-hardening.md`
- `docs/stage_reports/STAGE_R8_STRATEGY_COMPARATOR_CONTRACT_HARDENING_REPORT.md`
- `src/tradingbotsuite/backtesting/engine.py`
- `src/tradingbotsuite/research_cycle/runner.py`
- `src/tradingbotsuite/strategies/__init__.py`
- `src/tradingbotsuite/strategies/_helpers.py`
- `src/tradingbotsuite/strategies/contracts.py`
- `src/tradingbotsuite/strategies/no_trade.py`
- `src/tradingbotsuite/strategies/parameters.py`
- `tests/contracts/test_research_cycle_contract.py`
- `tests/contracts/test_strategy_contracts.py`
- `tests/historical/test_full_cycle_synthetic.py`
- `tests/integration/test_backtest_engine_fixture.py`

The working tree still contains many earlier uncommitted WPR files and modifications already represented in the ledger. Those prior packet changes are not part of this WPR8 closure and were not reverted or normalized.

## Research Boundary

All new historical-cycle evidence remains:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`

No live, paper, shadow, testnet, canary, order-placement, live-mode mutation, or promotion-ready candidate path was added. The R8 comparator fields are evidence-only and do not alter candidate acceptance or promotion gates.

## Review Resolution

Read-only reviewers identified and rechecked these issues:

- Explicit search spaces could omit baseline comparators. Resolved by comparator injection and manifest coverage evidence.
- Non-transparent-only groups could miss a transparent baseline. Resolved by selecting a compatible transparent baseline per feature/window group.
- Candidate IDs omitted implicit defaults. Resolved by hashing resolved parameters and persisting both specified and resolved parameter JSON.
- Strategy metadata was spec-derived instead of candidate-derived. Resolved by manifesting metadata for generated candidate strategy IDs.
- Backtest exit metadata was not propagated to signal artifacts. Resolved and covered by an integration test.
- Strategy config loading did not fail closed for unknown strategy/feature/window combinations. Resolved by plugin construction during config validation.

Final reviewer rechecks reported no blocking findings.

## Validation

- `python -m compileall -q src/tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_strategy_contracts.py tests/contracts/test_research_cycle_contract.py tests/historical/test_full_cycle_synthetic.py tests/integration/test_backtest_engine_fixture.py tests/contracts/test_backtest_contracts.py -q` passed: 41 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed: 57 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/historical -q` passed: 8 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/backtesting tests/unit/test_execution_simulator.py tests/integration/test_backtest_engine_fixture.py tests/live/test_preflight.py -q` passed: 51 passed.
- `git diff --check` passed with only existing LF-to-CRLF warnings.

## Remaining Limitations

- Comparator evidence is aggregate historical research evidence only; it is not live readiness.
- Default cycles still use one resolved-default candidate per supported strategy/feature/window unless explicit optimizer search spaces are supplied.
- Failure-mode count diagnostics remain future work; failure modes are declared in metadata and used in gating/audit context, but per-row skipped-reason accounting was not added in this packet.
