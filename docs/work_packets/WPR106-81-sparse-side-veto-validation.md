# WPR106-81 - Sparse Side Veto Validation

## Purpose

Turn the WPR106-80 offline BTC sparse long-only side decomposition into a real
strategy-contract validation. The packet adds an explicit research-only side
veto to `sparse_event_filter_v1`, tests both pre-selection and post-selection
side-veto semantics, reruns the two BTC sparse long-only theories as actual
historical-cycle candidates, and includes short-only controls before any larger
optimizer work is considered.

## Scope

Allowed edit paths:

- `docs/work_packets/WPR106-81-sparse-side-veto-validation.md`
- `docs/stage_reports/STAGE_R106_SPARSE_SIDE_VETO_VALIDATION_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `configs/research/sparse_side_veto_btcusdt_r106_v1.json`
- `src/tradingbotsuite/strategies/sparse_event_filter.py`
- `src/tradingbotsuite/strategies/parameters.py`
- `tests/contracts/test_strategy_contracts.py`

Allowed generated research-output paths:

- `data/research/historical_cycles/sparse_side_veto_btcusdt_r106_v1/**`
- `data/research/monte_carlo_exit_sizing/wpr106_81/**`

Read-only evidence and reference paths:

- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- `docs/KNOWN_ISSUES.md`
- `docs/stage_reports/STAGE_R106_MONTE_CARLO_EXIT_SIZING_SIEVE_REPORT.md`
- `docs/stage_reports/STAGE_R106_SPARSE_ENTRY_FILTER_LAYER_REPORT.md`
- `configs/research/sparse_entry_filter_btcusdt_r106_v1.json`
- `data/research/historical_cycles/sparse_entry_filter_btcusdt_r106_v1/**`
- `data/research/monte_carlo_exit_sizing/wpr106_80/**`

Out of scope:

- Candidate-pack creation, paper/live artifacts, or promotion artifacts.
- Live, paper, order-placement, runtime-mode, live-configuration, or actual
  position-sizing behavior.
- Provider downloads, fixture rewrites, catalog rebuilds, or new venue intake.
- Broad KNN/exact-discovery sweeps or expensive optimizer runs before the true
  side-veto rows pass split and cost-stress evidence.
- Treating side-veto validation as candidate-ready or promotion-ready evidence.

## Plan

1. Add an `allowed_sides` parameter to `sparse_event_filter_v1` with accepted
   values `both`, `long`, and `short`.
2. Add a `side_filter_stage` parameter with `pre_selection` and
   `post_selection` options:
   - `pre_selection` evaluates a true one-sided candidate population;
   - `post_selection` preserves the original top-score/side-balance selection
     and then vetoes the disallowed side, matching the WPR106-80 offline
     decomposition hypothesis.
3. Add contract tests for metadata coverage, long-only/short-only behavior, and
   pre-selection versus post-selection semantics.
4. Add a BTCUSDT side-veto historical-cycle spec with:
   - no-trade and transparent volatility controls;
   - pre-selection and post-selection price sparse and aggTrade-contrarian
     rows;
   - matching short-only controls;
   - fixed-hold exits only.
5. Run focused validation, the historical cycle, and baseline compile/contracts
   if runtime permits.
6. Document whether the true long-only rows justify an expensive optimizer
   packet, or fail closed.

## Research Boundary

All outputs remain `research_only: true`, `observe_only: true`, and
`promotion_ready: false`. This packet may identify or reject a follow-up
optimizer direction, but it cannot size positions, place orders, alter runtime
mode, write live configuration, create candidate packs, or claim promotion
readiness.
