# Stage R22 Exit Policy Candidate Cycle Evidence Report

Date: 2026-05-04
Owner: Codex Research Agent
Status: closed

## Scope

WPR22 made configured research exit policies part of historical-cycle candidate identity and evidence. Defaults remain fixed-holding only.

## Completed

- Added cycle spec `exit_policies` support.
- Added exit policy id and parameters to:
  - `CandidateConfig`;
  - `SearchSpace`;
  - candidate-space manifests;
  - candidate rankings;
  - backtest index rows;
  - aggregate, split, and cost-stress `BacktestSpec` construction.
- Preserved candidate count and behavior for default fixed-holding cycles.
- Added explicit exit-policy candidate expansion tests.
- Added optimizer identity tests proving candidate keys change with exit policy and exit parameters.

## Validation

- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_research_cycle_contract.py tests/historical/test_full_cycle_synthetic.py tests/historical/test_research_cycle_benchmark.py tests/optimization/test_candidate_cache_keys.py tests/optimization/test_search_space_expansion.py tests/live/test_preflight.py -q` (`59 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` (`67 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests/optimization -q` (`18 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests/historical -q` (`13 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests/backtesting -q` (`43 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests/research_artifacts -q` (`23 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite -q` (`273 passed`)
- `git diff --check` passed with line-ending warnings only.

## Boundary Notes

- No live, paper, shadow, testnet, canary, promotion, order-placement, or capital-allocation behavior was added.
- Fixed-holding remains the default exit policy.
- Non-fixed exit policies remain research-only candidate dimensions.
- Candidate acceptance and Stage 13 execution remain blocked.
