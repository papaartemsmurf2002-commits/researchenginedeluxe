# Stage R4/R8 Metadata-Backed Default Search Report

Status: closed - metadata-backed default candidate expansion complete
Owner: Codex Research Agent
Date: 2026-05-04

## Scope

This wave completed a bounded Stage R4/R8 default-search slice:

- Historical cycles without explicit `optimizer.search_spaces` now generate candidates from strategy parameter metadata instead of only one defaults-only candidate per strategy/feature/window tuple.
- Each supported tuple includes a resolved-default seed candidate and a deterministic capped metadata grid sample.
- The metadata sample is capped at four unique metadata candidates per strategy/feature/holding-window tuple and also respects `optimizer.max_candidates_per_strategy`.
- Holding-window default overrides are included in metadata search domains, so default values remain auditable even when absent from base metadata parameter spaces.
- `baseline_no_trade` remains a single comparator seed and does not expand into synthetic parameter variants.
- Explicit optimizer search spaces continue to use the explicit-search path and do not emit metadata-default candidate sources.
- Candidate-space manifests now expose default-search policy, source counts, effective caps, and research-only boundary fields.
- Grid search expansion now slices lazily before materializing Cartesian products.
- Metadata-default sampling now fills the cap with unique candidate IDs when duplicate resolved configs appear early in the grid.

## Path Audit

WPR4-08-specific edits were confined to the packet's allowed paths:

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

The working tree still contains many earlier uncommitted WPR files and modifications already represented in the ledger. Those prior packet changes are out of scope for this WPR4-08 closure and were not reverted or normalized.

## Research Boundary

All new default-search evidence remains:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`

No live, paper, shadow, testnet, canary, order-placement, live-mode mutation, or promotion-ready candidate path was added. Metadata-backed default search only changes research candidate enumeration and manifest audit evidence.

## Review Resolution

Read-only reviewers identified and rechecked these issues:

- Grid expansion materialized the full Cartesian product before slicing. Resolved by adding lazy grid iteration and capping with `itertools.islice`.
- Default-seed dedupe could consume metadata search budget. Resolved by iterating until the configured number of unique metadata candidates is emitted or the metadata domain is exhausted.
- Manifest tests needed explicit-search policy assertions. Resolved by asserting explicit mode disables default search, excludes metadata-default sources, and keeps source counts equal to candidate count.
- Closure docs were missing. Resolved by this report and packet/ledger closure updates.

No P0 or unresolved P1 blocker remains for this wave.

## Validation

- `python -m compileall -q src/tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_research_cycle_contract.py tests/optimization/test_search_space_expansion.py tests/historical/test_full_cycle_synthetic.py tests/historical/test_full_cycle_local_fixture_pack.py -q` passed: 18 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed: 59 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/historical -q` passed: 8 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/optimization -q` passed: 14 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/live/test_preflight.py -q` passed: 24 passed.
- `git diff --check` passed with only existing LF-to-CRLF warnings.

## Remaining Limitations

- Metadata-backed candidates remain historical research evidence only; they are not live signals and do not imply promotion readiness.
- The default metadata sampler intentionally uses a small deterministic grid prefix, not a broad optimizer sweep.
- Candidate acceptance remains blocked until real OOS/stress/stability evidence, paper/shadow/testnet archives, rollback evidence, and explicit approval artifacts exist.
