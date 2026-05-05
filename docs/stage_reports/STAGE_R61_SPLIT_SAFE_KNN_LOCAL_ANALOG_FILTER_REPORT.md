# Stage R61 Split-Safe KNN Local Analog Filter Report

Date: 2026-05-05
Branch: `research/v3-experimental-engine`
Work packet: `docs/work_packets/WPR61-01-split-safe-knn-local-analog-filter.md`
Status: closed

## Scope

R61 added `hmm_knn_local_analog_filter_v2` as a research-only strategy plugin. The strategy consumes already materialized HMM/KNN local-analog columns and emits standard research-only signals only when KNN probabilities, expected value, neighbor quality, posterior confidence, and source-boundary checks all pass.

It does not fit HMMs, fit scalers, compute KNN distances, read neighbor pools, join artifacts from disk, import live adapters, or change promotion/live behavior.

## Strategy Semantics

- Required feature set: `features_perp_context_v2`.
- Required KNN columns: `p_up_barrier`, `p_down_barrier`, `expected_net_return_after_costs`, `neighbor_agreement`, `neighbor_distance_quality`, `neighbor_count`, `neighbor_min_source_index`, `neighbor_max_source_index`, `knn_vote_margin`, `accepted_by_knn`, and `knn_skip_reason`.
- Required HMM/split columns: `top_regime_label`, `max_regime_probability`, `posterior_entropy`, `recent_regime_flip`, `regime_no_trade`, `hmm_fit_end_row`, and `source_row_index`.
- Split-safety rule: signals require `neighbor_min_source_index <= neighbor_max_source_index <= hmm_fit_end_row < source_row_index`.
- The strategy fails closed on missing columns, malformed markers, non-empty skip reasons, `accepted_by_knn` false, low probability, low EV, low neighbor count, weak agreement, weak distance quality, low posterior confidence, high entropy, recent flips, or no-trade regimes.

## Candidate-Space Boundary

The filter is registered as a normal research candidate, not a comparator baseline. It is not wired into the checked BTCUSDT/ETHUSDT provider-cycle configs in this packet because those cycle frames do not yet materialize split-safe KNN prediction columns. The standalone HMM/KNN artifact regression confirms current `meta_predictions` remain fail-closed under the stricter `neighbor_max_source_index <= hmm_fit_end_row` requirement.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_strategy_contracts.py tests\contracts\test_research_cycle_contract.py::test_perp_context_v2_candidate_space_includes_transparent_perp_strategies_with_baseline_coverage tests\tradingbotsuite\test_hmm_knn.py::test_hmm_knn_research_writes_expected_research_only_artifacts -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- Full compile passed.
- WPR61 focused suite: 240 passed.
- Full contract suite: 332 passed.

## Research Boundary

This stage does not add live signals, promotion readiness, paper/shadow/testnet/canary behavior, live configuration writes, order placement, position sizing, or performance claims.

## Next Stage

The roadmap item after WPR61 is the liquidation classifier, but it should not start until durable liquidation fixtures or a scoped public-source liquidation data packet exists. Opening WPR62 should first decide whether to build durable liquidation data intake or explicitly defer the classifier.
