# Work Packet WPR2-01 - Real Backtests, Splits, Features, And Exits

Stage: Stage R2/R3/R6/R7 research computation foundation
Substages: R2 real experiment-runner integration, R3 split/OOS expansion, R6 exit metadata foundation, R7 feature DAG foundation
Owner: Codex Research Agent
Status: closed
Date: 2026-05-04

## Objective

Continue converting the research branch from contract-only scaffolding into reproducible historical computation while preserving branch boundaries and the existing repo structure. The immediate goal is to make experiment-runner generic outputs use real `BacktestEngine` artifacts when a dataset is available, expand split/stress outputs from actual runs, and add minimal feature/exit foundations that later stages can extend.

## Allowed Paths

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/work_packets/WPR2-01-real-backtests-splits-features-exits.md`
- `docs/stage_reports/STAGE_R2_R3_R6_R7_RESEARCH_COMPUTATION_REPORT.md`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/research/experiment_runner.py`
- `src/tradingbotsuite/research/command_registry.py`
- `src/tradingbotsuite/research_cycle/**`
- `src/tradingbotsuite/backtesting/engine.py`
- `src/tradingbotsuite/backtesting/execution_sim.py`
- `src/tradingbotsuite/backtesting/exits.py`
- `src/tradingbotsuite/backtesting/splits.py`
- `src/tradingbotsuite/backtesting/metrics.py`
- `src/tradingbotsuite/features/builders.py`
- `src/tradingbotsuite/features/cache.py`
- `src/tradingbotsuite/features/split_transforms.py`
- `src/tradingbotsuite/features/__init__.py`
- `src/tradingbotsuite/optimization/**`
- `tests/tradingbotsuite/test_experiment_runner.py`
- `tests/contracts/test_research_cycle_contract.py`
- `tests/contracts/test_backtest_contracts.py`
- `tests/contracts/test_feature_contracts.py`
- `tests/backtesting/**`
- `tests/features/**`
- `tests/historical/**`
- `tests/optimization/**`

## Scope

- Resolve real parquet dataset paths for experiment-runner generic outputs.
- Run `BacktestEngine` candidates for generic experiment rows when a real local dataset is available.
- Write candidate rankings and real backtest manifest links for those rows.
- Preserve contract-only fallback when no real dataset can be resolved.
- Expand split helpers toward anchored, rolling, purged/embargoed, month, stress-period, and regime holdout metadata.
- Add exit-policy result metadata for fixed-window exits and close-only barrier foundations without optimistic same-bar assumptions.
- Add a small feature DAG foundation for price/trend/vol features, cache keys, and train-only split transforms.
- Keep all generated outputs research-only, observe-only, and not promotion-ready.

## Non-Scope

- No paper, shadow, testnet, or live execution.
- No order placement, live runtime mode changes, live configuration writes, or capital allocation.
- No promotion-ready candidate packs.
- No claim that synthetic or single-fixture results satisfy empirical acceptance floors.
- No dependency-heavy acceleration path.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_experiment_runner.py tests/backtesting tests/features tests/historical tests/optimization -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
python -m compileall -q src/tradingbotsuite
```

## Exit Criteria

The packet exits when generic experiment outputs use real backtest artifacts when possible, no placeholder metrics are accepted as evidence, split/exit/feature foundations have focused tests, live/order boundaries remain untouched, and validation passes.

## Exit Evidence

- Generic experiment-runner output now resolves local parquet datasets and writes real `BacktestEngine` manifests, metrics, split, regime, side, cost-stress, and candidate-ranking artifacts when data is available.
- Contract-only fallback remains explicit when no dataset can be resolved, with `empirical_evidence: false` and no candidate acceptance.
- Historical cycle candidate generation can expand optimizer search spaces, keeps deterministic `CandidateConfig` cache-key candidate IDs, and writes stability regions from `CandidateResult` objects built from aggregate, split, and cost-stress metrics.
- Backtest cache identity includes reproducible backtest spec, execution assumptions, and cost model inputs; split runs hash their actual split frame.
- Dataset manifests resolve relative parquet/data paths against the manifest directory.
- Empty candidate dimensions are rejected at spec-load time.
- Split helpers now cover anchored/rolling walk-forward metadata plus month, regime, and stress holdouts.
- Execution simulation records fixed-window exit metadata, including fallback exits and same-bar safeguards.
- Feature DAG foundation adds registered feature builds, deterministic cache manifests, and train-only split transforms.
- All produced artifacts remain research-only, observe-only, and `promotion_ready: false`.

Validation completed:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_experiment_runner.py tests/backtesting tests/features tests/historical tests/optimization -q
# 26 passed

$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
# 37 passed

python -m compileall -q src/tradingbotsuite
# passed
```
