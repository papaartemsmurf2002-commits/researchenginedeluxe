# WPR61-01 Split-Safe KNN Local Analog Filter

Owner: Codex Research Agent
Status: closed
Stage: R61 split-safe KNN local analog filter
Date opened: 2026-05-05

## Goal

Add `hmm_knn_local_analog_filter_v2` as a research-only strategy/filter that consumes already materialized split-safe HMM/KNN artifact columns. It must use local-analog probabilities, expected value, neighbor quality, and split-safety markers without fitting KNN, recomputing neighbors, or reading future rows inside the strategy.

## Allowed Paths

```text
src/tradingbotsuite/strategies/hmm_knn_local_analog_filter.py
src/tradingbotsuite/strategies/registry.py
src/tradingbotsuite/strategies/parameters.py
configs/strategies/hmm_knn_local_analog_filter_v2.json
tests/contracts/test_strategy_contracts.py
tests/contracts/test_research_cycle_contract.py
tests/tradingbotsuite/test_hmm_knn.py
docs/work_packets/WPR61-01-split-safe-knn-local-analog-filter.md
docs/stage_reports/STAGE_R61_SPLIT_SAFE_KNN_LOCAL_ANALOG_FILTER_REPORT.md
docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- Keep all outputs research-only, observe-only, and promotion-ready false.
- Do not import live adapters, place orders, write runtime controls, or create promotion evidence.
- Do not fit KNNs, fit scalers, read neighbor pools, or recompute local analogs inside the strategy.
- Do not add live, paper, shadow, testnet, canary, or promotion workflow behavior.
- Do not wire the strategy into checked BTC/ETH provider-cycle configs until split-safe KNN prediction columns are materialized into those cycle frames.
- Fail closed when KNN output, HMM posterior, or neighbor source-boundary columns are missing, non-finite, low-quality, or not prior-row safe.

## Required Behavior

- Register `hmm_knn_local_analog_filter_v2` as a normal research strategy candidate, not as a comparator baseline.
- Require `features_perp_context_v2` plus existing KNN/HMM artifact columns:
  - `p_up_barrier`
  - `p_down_barrier`
  - `expected_net_return_after_costs`
  - `neighbor_agreement`
  - `neighbor_distance_quality`
  - `neighbor_count`
  - `neighbor_min_source_index`
  - `neighbor_max_source_index`
  - `knn_vote_margin`
  - `accepted_by_knn`
  - `knn_skip_reason`
  - `top_regime_label`
  - `max_regime_probability`
  - `posterior_entropy`
  - `recent_regime_flip`
  - `regime_no_trade`
  - `hmm_fit_end_row`
  - `source_row_index`
- Require `hmm_fit_end_row < source_row_index`.
- Require `neighbor_max_source_index < source_row_index` and non-negative integer source markers.
- Emit standard `RuleSignal` rows only when local analog probability, EV, neighbor count, agreement, and distance-quality floors pass.

## Validation Plan

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_strategy_contracts.py tests\contracts\test_research_cycle_contract.py::test_perp_context_v2_candidate_space_includes_transparent_perp_strategies_with_baseline_coverage tests\tradingbotsuite\test_hmm_knn.py::test_hmm_knn_research_writes_expected_research_only_artifacts -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Close Evidence

Record strategy semantics, split-safety checks, focused validation, unchanged cycle wiring, and residual risks in `docs/stage_reports/STAGE_R61_SPLIT_SAFE_KNN_LOCAL_ANALOG_FILTER_REPORT.md`, then close this packet and the ledger row if validation is clean.

Closed 2026-05-05 with validation and boundary evidence recorded in `docs/stage_reports/STAGE_R61_SPLIT_SAFE_KNN_LOCAL_ANALOG_FILTER_REPORT.md`.
