# WPR4-08 Metadata-Backed Default Search

Status: closed
Owner: Codex Research Agent
Stage: Stage R4/R8 metadata-backed default search
Opened: 2026-05-04
Closed: 2026-05-04

## Objective

Make default historical research cycles use strategy parameter metadata for deterministic candidate expansion instead of evaluating only one resolved-default candidate per strategy/feature/holding-window combination. The default path must include the resolved default seed, add a small deterministic metadata sample capped by `optimizer.max_candidates_per_strategy`, remain auditable in manifests, stay compatible with baseline comparator policy, and stay research-only.

## Allowed paths

- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR4-08-metadata-backed-default-search.md`
- `docs/stage_reports/STAGE_R4_R8_METADATA_BACKED_DEFAULT_SEARCH_REPORT.md`
- `src/tradingbotsuite/research_cycle/runner.py`
- `src/tradingbotsuite/optimization/search_space.py`
- `src/tradingbotsuite/strategies/parameters.py`
- `tests/contracts/test_research_cycle_contract.py`
- `tests/historical/test_full_cycle_synthetic.py`
- `tests/historical/test_full_cycle_local_fixture_pack.py`
- `tests/optimization/test_search_space_expansion.py`

## Non-goals

- No live, paper, shadow, testnet, canary, promotion, order-placement, or capital allocation work.
- No new strategy alpha implementation.
- No candidate acceptance or promotion-ready artifact path.
- No parallel execution or vectorized backtest implementation.
- No broad optimizer rewrite beyond deterministic metadata-backed candidate expansion.

## Implementation plan

1. Build default strategy/feature/window search spaces from `StrategyParameterMetadata.parameter_space`.
2. Ensure per-holding-window default overrides are included in each default search domain so resolved-default candidates are present.
3. Expand default search spaces with a deterministic capped grid sample so routine cycles do not explode.
4. Preserve comparator injection and candidate resolved-parameter identity from the prior R8 packet.
5. Add manifest fields that distinguish metadata-backed default search from explicit optimizer search.
6. Add tests for default metadata expansion, default candidate inclusion, comparator coverage, and full-cycle candidate counts.

## Exit criteria

- Default historical cycles expand strategy candidates from metadata parameter spaces.
- Candidate-space manifests record `search_mode: metadata_default_search` and default-search coverage fields.
- Resolved defaults remain present in each generated strategy/feature/window search set.
- Candidate counts are deterministic and bounded by a small default metadata cap and `max_candidates_per_strategy`.
- Comparator coverage remains complete after metadata-backed expansion.
- Focused tests, contracts, historical tests, compileall, and diff checks pass.

## Risk controls

- Keep synthetic and fixture-cycle outputs research-only, observe-only, and not promotion-ready.
- Avoid unbounded Cartesian explosion by applying a small default metadata sample cap to each supported strategy/feature/window search space.
- Do not modify live, promotion, or order-placement modules.
- Treat earlier uncommitted WPR files in the dirty tree as out of scope for this packet.

## Exit evidence

- Default historical cycles now route through metadata-backed default search when `optimizer.search_spaces` is absent.
- Each supported strategy/feature/holding-window tuple emits a resolved-default seed candidate, then up to four unique metadata grid candidates capped by `optimizer.max_candidates_per_strategy`.
- `baseline_no_trade` remains a single comparator seed and does not expand through metadata parameters.
- Explicit optimizer search spaces keep the prior `explicit_search_spaces` path and do not emit metadata-default candidate sources.
- Candidate-space manifests now record `search_mode: metadata_default_search`, `search_method: metadata_capped_grid`, and a research-only `default_search_policy` with source counts and effective caps.
- Holding-window default overrides are included in search domains so resolved defaults remain auditable even when not present in the base metadata parameter space.
- Grid expansion is lazy and capped before materializing Cartesian products.
- Metadata-default sampling keeps walking the grid until the requested number of unique metadata candidates is emitted or the domain is exhausted.
- Comparator coverage remains complete after metadata-backed expansion.
- Reviewer-identified boundedness and dedupe issues were fixed before closure.

## Validation

- `python -m compileall -q src/tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_research_cycle_contract.py tests/optimization/test_search_space_expansion.py tests/historical/test_full_cycle_synthetic.py tests/historical/test_full_cycle_local_fixture_pack.py -q` passed: 18 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed: 59 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/historical -q` passed: 8 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/optimization -q` passed: 14 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/live/test_preflight.py -q` passed: 24 passed.
- `git diff --check` passed with only existing LF-to-CRLF warnings.
