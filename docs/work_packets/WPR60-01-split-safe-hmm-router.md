# WPR60-01 Split-Safe HMM Router

Owner: Codex Research Agent
Status: closed
Stage: R60 split-safe HMM router
Date opened: 2026-05-05

## Goal

Add `hmm_routed_alpha_sleeves_v2` as a research-only transparent router strategy that consumes already materialized split-safe HMM posterior columns and routes to simple alpha-sleeve rules without fitting HMMs inside the strategy.

## Allowed Paths

```text
src/tradingbotsuite/strategies/hmm_routed_alpha_sleeves.py
src/tradingbotsuite/strategies/registry.py
src/tradingbotsuite/strategies/parameters.py
src/tradingbotsuite/strategies/__init__.py
configs/strategies/hmm_routed_alpha_sleeves_v2.json
tests/contracts/test_strategy_contracts.py
tests/contracts/test_research_cycle_contract.py
tests/tradingbotsuite/test_hmm_knn.py
docs/work_packets/WPR60-01-split-safe-hmm-router.md
docs/stage_reports/STAGE_R60_SPLIT_SAFE_HMM_ROUTER_REPORT.md
docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- Keep all outputs research-only, observe-only, and promotion-ready false.
- Do not import live adapters, place orders, write runtime controls, or create promotion evidence.
- Do not fit HMMs inside the strategy plugin.
- Do not recompute full-dataset HMM posteriors.
- Do not add KNN routing or local-analog filtering in this packet.
- Do not wire the router into checked BTC/ETH provider-cycle configs until split-safe posterior columns are materialized into those cycle frames.
- Fail closed when HMM posterior columns are missing, non-finite, low-confidence, high-entropy, recent-flip, no-trade, or not prior-fit safe.

## Required Behavior

- Register `hmm_routed_alpha_sleeves_v2` as a normal research strategy candidate, not as a comparator baseline.
- Require `features_perp_context_v2` plus split-safe HMM posterior columns:
  - `top_regime_label`
  - `max_regime_probability`
  - `posterior_entropy`
  - `recent_regime_flip`
  - `regime_no_trade`
  - `hmm_fit_end_row`
  - `source_row_index`
- Require `hmm_fit_end_row < source_row_index` before any signal can be emitted.
- Route `bull_trend` and `bear_trend` regimes to directional OI/premium-flow sleeves.
- Route `range_chop` regimes to basis/funding fade sleeves.
- Treat `shock_transition` and unknown regimes as no-trade unless a later packet explicitly changes that behavior.
- Emit only standard `RuleSignal` rows through the existing strategy contract.

## Validation Plan

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_strategy_contracts.py tests\tradingbotsuite\test_hmm_knn.py::test_hmm_knn_research_writes_expected_research_only_artifacts -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Close Evidence

Record strategy semantics, split-safety checks, focused validation, unchanged cycle wiring, and residual risks in `docs/stage_reports/STAGE_R60_SPLIT_SAFE_HMM_ROUTER_REPORT.md`, then close this packet and the ledger row if validation is clean.

Closed 2026-05-05 with validation and boundary evidence recorded in `docs/stage_reports/STAGE_R60_SPLIT_SAFE_HMM_ROUTER_REPORT.md`.
