# Stage R46 Perp Strategy Plan Alignment Report

Date: 2026-05-05
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR46-01-perp-strategy-plan-alignment.md`
Status: closed

## Scope

WPR46 curated the downloaded BTC/ETH perpetual strategy expansion plan into a repo-native agent development document. This was documentation-only and did not change runtime behavior, provider collection code, feature builders, strategies, exits, candidate gates, promotion logic, live preflight, or order-placement behavior.

## Output

- Curated plan: `docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md`

The curated plan aligns the downloaded document with the current branch by:

- Moving implementation start from the already-closed R45 to WPR47.
- Preserving the current `HistoricalResearchCycleSpec` shape.
- Removing `8h` from initial supported holding windows.
- Mapping proposed exit names to existing supported exit IDs.
- Requiring new strategies to follow current `RuleBasedStrategy` and signal-frame contracts.
- Keeping BTCUSDT and ETHUSDT as separate cycles until multi-symbol cycle support is explicitly implemented.
- Deferring liquidation, L2/order-book, cross-exchange context, HMM/KNN filters, and ML meta-labeling until required foundations exist.
- Treating overfit diagnostics and trial-budget reports as additive future reports, not immediate hard gates.

## Boundary Notes

- The plan remains research-only and observe-only.
- The plan does not claim OOS acceptance, profitability, production speed, live readiness, or promotion readiness.
- The plan does not require deleting or replacing core repo structure.
- Non-trivial infrastructure changes are isolated into dedicated future work packets.
- External research/API references from the source document remain research context only; empirical acceptance must come from branch artifacts and gates.

## Validation

Documentation cross-checks:

- Reviewed `docs/ORCHESTRATOR_STAGE_LEDGER.md`.
- Reviewed `docs/KNOWN_ISSUES.md`.
- Reviewed `docs/RESEARCH_BRANCH_DISTILLATION.md`.
- Compared the downloaded plan against current names in:
  - `src/tradingbotsuite/research_cycle/spec.py`
  - `src/tradingbotsuite/features/registry.py`
  - `src/tradingbotsuite/data/historical_fixture_pack.py`
  - `src/tradingbotsuite/research/market_data.py`
  - `src/tradingbotsuite/strategies/contracts.py`
  - `src/tradingbotsuite/strategies/_helpers.py`
  - `src/tradingbotsuite/strategies/registry.py`
  - `src/tradingbotsuite/backtesting/exits.py`
  - `src/tradingbotsuite/research_artifacts/candidate_pack.py`

Focused repository validation passed:

- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 97 tests.
- `git diff --check` passed.

## Close Decision

Stage R46 is closed. The branch now has a ready-to-agent perpetual strategy development plan aligned to the current research architecture and naming contracts. Implementation should begin with WPR47 only after a scoped work packet is opened.
