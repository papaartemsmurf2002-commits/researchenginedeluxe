# Stage R2/R3/R6/R7 Research Computation Report

Date: 2026-05-04
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR2-01-real-backtests-splits-features-exits.md`
Status: closed - research computation foundations complete

## Scope Completed

- Generic experiment-runner outputs now use real `BacktestEngine` runs when a local parquet dataset can be resolved from evidence manifests, dataset manifests, pipeline specs, or experiment specs.
- Candidate summaries now link to real backtest manifests and metrics, write `candidate_rankings.parquet`, and keep contract-only fallback rows explicitly non-empirical.
- Historical cycle optimizer input now accepts explicit search spaces, expands them through `SearchSpace`, uses deterministic `CandidateConfig` cache keys, and merges searched parameters into strategy configs.
- Stability regions are now generated from actual `CandidateResult` objects derived from aggregate, split, and cost-stress metrics instead of placeholder rows.
- Backtest cache identity now includes reproducible spec, execution assumptions, and cost model inputs; split backtests use the actual split-frame hash.
- Dataset manifests now resolve relative parquet/data paths from the manifest directory, and specs reject empty candidate dimensions before execution.
- Split/OOS helpers now support anchored and rolling purged walk-forward metadata plus month, regime, and stress-period holdouts.
- Exit metadata now records entry/exit bar indexes, target holding time, fallback exits, and fixed-window policy details without permitting same-bar optimism.
- Feature foundations now expose registered feature builds, deterministic cache identity manifests, and train-only split transforms.

## Boundaries

- No paper, shadow, testnet, or live execution was added or run.
- No research module imports live order-placement adapters.
- No live runtime mode, live config, capital allocation, or order path is modified.
- Research artifacts remain `research_only`, `observe_only`, and `promotion_ready: false`.
- Candidate acceptance and promotion packs remain blocked even when real local backtest artifacts are generated.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_experiment_runner.py tests/backtesting tests/features tests/historical tests/optimization -q
# 26 passed

$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
# 37 passed

python -m compileall -q src/tradingbotsuite
# passed
```

## Remaining Blockers

- Empirical acceptance remains blocked until real OOS/stress/stability evidence is produced from approved historical datasets with reproducible manifests and documented validation evidence.
- Stage 13 execution remains blocked until real OOS/stress evidence, paper/shadow/testnet archives, rollback evidence, and explicit human approval artifacts exist.
