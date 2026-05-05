# Stage R0/R1 Historical Research Foundation Report

Date: 2026-05-04
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR0-01-historical-research-cycle-foundation.md`
Status: closed - research-only foundations complete

## Scope Completed

- Generic experiment-runner placeholder rows are now explicitly `contract_only`, non-empirical, and not acceptable as candidate evidence.
- Backtest holding-window support now matches the research target set: `1h`, `4h`, `12h`, `24h`, `72h`, and `7d`.
- Added a research-only historical cycle package and CLI command:
  - `python -m tradingbotsuite.main run-historical-research-cycle --spec configs/research/full_cycle_btc_v1.json`
- The cycle runner writes the required R1 artifact set, including rankings, split metrics, cost-stress metrics, stability placeholders, ablation report, rejection report, and a cycle manifest.
- Added a dependency-light optimizer foundation with deterministic candidate cache keys, search-space expansion, serial/parallel equivalence, and region-of-stability spike rejection.
- Registered the historical cycle command in the central research command registry so live preflight rejects it in live mode.

## Boundaries

- No paper, shadow, testnet, or live execution was added or run.
- No live order-placement adapter was imported by new research modules.
- All produced research artifacts remain `research_only`, `observe_only`, and `promotion_ready: false`.
- Synthetic fixture results are explicitly rejected as candidate acceptance evidence.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_experiment_runner.py tests/contracts/test_backtest_contracts.py tests/contracts/test_research_cycle_contract.py tests/historical/test_full_cycle_synthetic.py tests/live/test_preflight.py -q
# 39 passed

$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
# 34 passed

$env:PYTHONPATH='src'; python -m pytest tests/optimization -q
# 6 passed

python -m compileall -q src/tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m tradingbotsuite.main run-historical-research-cycle --help
# passed
```

## Remaining Blockers

- Full empirical completion remains blocked until real historical fixture data, real OOS/stress metrics, feature DAG output, split-aware transforms, richer exits, and stability-region refinement are implemented and validated.
- Stage 13 execution remains blocked until real OOS/stress evidence, paper/shadow/testnet archives, rollback evidence, and explicit human approval artifacts exist.
