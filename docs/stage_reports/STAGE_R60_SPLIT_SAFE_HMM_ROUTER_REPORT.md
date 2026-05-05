# Stage R60 Split-Safe HMM Router Report

Date: 2026-05-05
Branch: `research/v3-experimental-engine`
Work packet: `docs/work_packets/WPR60-01-split-safe-hmm-router.md`
Status: closed

## Scope

R60 added `hmm_routed_alpha_sleeves_v2` as a research-only strategy plugin. The strategy consumes already materialized split-safe HMM posterior columns and routes to transparent alpha-sleeve rules. It does not fit HMMs, recompute full-dataset posteriors, use KNN local analog filters, import live adapters, or alter promotion/live behavior.

## Strategy Semantics

- Required feature set: `features_perp_context_v2`.
- Required posterior columns: `top_regime_label`, `max_regime_probability`, `posterior_entropy`, `recent_regime_flip`, `regime_no_trade`, `hmm_fit_end_row`, and `source_row_index`.
- Split-safety rule: signals are allowed only when `hmm_fit_end_row < source_row_index`.
- `bull_trend` and `bear_trend` route to directional OI/premium-flow sleeves.
- `range_chop` routes to basis/funding fade sleeves.
- `shock_transition`, unknown regimes, low posterior confidence, high entropy, recent flips, no-trade flags, invalid context, and malformed parameters fail closed.

## Candidate-Space Boundary

The router is registered as a normal research candidate, not a comparator baseline. It is not wired into the checked BTCUSDT/ETHUSDT provider-cycle configs in this packet because those cycle frames do not yet materialize split-safe HMM posterior columns. A later packet can add posterior materialization or artifact joins before adding checked cycle evidence.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_strategy_contracts.py tests\contracts\test_research_cycle_contract.py::test_perp_context_v2_candidate_space_includes_transparent_perp_strategies_with_baseline_coverage tests\tradingbotsuite\test_hmm_knn.py::test_hmm_knn_research_writes_expected_research_only_artifacts -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- Full compile passed.
- WPR60 focused suite: 191 passed.
- Full contract suite: 283 passed.

## Research Boundary

This stage does not add live signals, promotion readiness, paper/shadow/testnet/canary behavior, live configuration writes, order placement, position sizing, or performance claims.

## Next Stage

WPR61 should be opened as a new packet before coding. The next planned roadmap item is the split-safe KNN local analog filter, but it should not start until router posterior materialization assumptions are explicitly scoped.
