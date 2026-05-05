# WPR22-01 Exit Policy Candidate Cycle Evidence

Status: closed
Owner: Codex Research Agent
Stage: Stage R22 exit policy candidate cycle evidence
Opened: 2026-05-04
Closed: 2026-05-04

## Objective

Make research exit policies first-class historical-cycle candidate dimensions with explicit manifest, ranking, and backtest-index evidence.

WPR21 added policy execution foundations. This packet lets research cycles evaluate configured exit policies without changing default behavior or making promotion claims.

## Allowed paths

- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR22-01-exit-policy-candidate-cycle-evidence.md`
- `docs/stage_reports/STAGE_R22_EXIT_POLICY_CANDIDATE_CYCLE_EVIDENCE_REPORT.md`
- `src/tradingbotsuite/research_cycle/spec.py`
- `src/tradingbotsuite/research_cycle/runner.py`
- `src/tradingbotsuite/research_cycle/benchmark.py`
- `src/tradingbotsuite/optimization/candidate.py`
- `src/tradingbotsuite/optimization/search_space.py`
- `src/tradingbotsuite/backtesting/engine.py`
- `tests/contracts/test_research_cycle_contract.py`
- `tests/historical/test_full_cycle_synthetic.py`
- `tests/historical/test_research_cycle_benchmark.py`
- `tests/optimization/test_candidate_cache_keys.py`
- `tests/optimization/test_search_space_expansion.py`
- `tests/live/test_preflight.py`

## Non-goals

- No live, paper, shadow, testnet, canary, promotion, order-placement, or capital allocation work.
- No default switch away from `fixed_holding_window`.
- No vector support for non-fixed-holding policies.
- No acceptance or promotion-ready claims.

## Implementation plan

1. Add cycle spec support for configured exit policies, defaulting to `fixed_holding_window`.
2. Include exit policy id and policy parameters in candidate identity and candidate-space manifests.
3. Pass candidate exit policy fields into every aggregate, split, and cost-stress `BacktestSpec`.
4. Record exit-policy evidence in rankings and backtest indexes.
5. Keep default benchmark dimensions fixed-holding unless a benchmark explicitly asks for exit-policy candidates.
6. Add tests for default preservation, explicit exit-policy candidate expansion, candidate identity/cache changes, and live preflight preservation.

## Exit criteria

- Historical-cycle defaults remain fixed-holding only.
- Configured exit policies expand candidate rows with deterministic identity.
- Backtest indexes and rankings record exit policy id, source, and parameters.
- Candidate cache keys change when exit policy or exit params change.
- Existing contracts, historical tests, benchmark tests, optimization tests, and live preflight pass.

## Closure evidence

- Added historical-cycle `exit_policies` parsing with default `fixed_holding_window`.
- Added exit policy id and parameter identity to `CandidateConfig`, `SearchSpace`, candidate manifests, ranking rows, and backtest index rows.
- Passed candidate exit policy fields into aggregate, split, and cost-stress backtests.
- Preserved fixed-holding defaults and default benchmark dimensions.
- Validation:
  - `python -m compileall -q src/tradingbotsuite`
  - `$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_research_cycle_contract.py tests/historical/test_full_cycle_synthetic.py tests/historical/test_research_cycle_benchmark.py tests/optimization/test_candidate_cache_keys.py tests/optimization/test_search_space_expansion.py tests/live/test_preflight.py -q` (`59 passed`)
  - `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` (`67 passed`)
  - `$env:PYTHONPATH='src'; python -m pytest tests/optimization -q` (`18 passed`)
  - `$env:PYTHONPATH='src'; python -m pytest tests/historical -q` (`13 passed`)
  - `$env:PYTHONPATH='src'; python -m pytest tests/backtesting -q` (`43 passed`)
  - `$env:PYTHONPATH='src'; python -m pytest tests/research_artifacts -q` (`23 passed`)
  - `$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite -q` (`273 passed`)
  - `git diff --check` passed with line-ending warnings only.
