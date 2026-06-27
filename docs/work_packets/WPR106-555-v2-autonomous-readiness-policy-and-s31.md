# WPR106-555 - V2 autonomous readiness policy update and S31 trend test

## Status

Blocked for `autonomous_research_ready` claim.

## Objective

Update the uploaded-strategy autonomous-readiness pass with the corrected
operator policy:

- Strategies that cannot be tested because required data cannot be collected,
  deduced, or simulated truthfully should be skipped with explicit evidence
  rather than blocking the whole autonomous-readiness set.
- Order-flow-style strategies should use collected, deduced, or simulated
  OF-style features when the transformation is documented and reproducible.
- Base-case slippage should use a median research estimate of `8` bps.
- Worst-case slippage should remain `20` bps for stress evidence.
- Add S31 volatility-adjusted trend following as a bar-based example strategy
  for the autonomous-readiness attempt.

## Scope

Allowed paths for this packet:

- `docs/work_packets/WPR106-555-v2-autonomous-readiness-policy-and-s31.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/ACTIVE_INDEX.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/contracts/**`
- `configs/strategies/wpr106_554/**`
- `configs/strategies/wpr106_555/**`
- `data/research/wpr106_554_autonomous_readiness/**`
- `data/research/wpr106_555_autonomous_readiness/**`
- `src/tradingbotsuite/v2/autonomy/**`
- `src/tradingbotsuite/v2/backtest_data/**`
- `src/tradingbotsuite/v2/backtest_engine/**`
- `src/tradingbotsuite/v2/collectors/**`
- `src/tradingbotsuite/v2/strategy_specs/**`
- `src/tradingbotsuite/v2/validation/**`
- `tests/v2/**`
- `tests/contracts/**`

No live, paper, order placement, sizing, runtime-mode, candidate-pack, or
promotion paths are in scope.

## Plan

1. Encode the corrected cost assumption as base `8` bps slippage with `20` bps
   stress evidence.
2. Add S31 as a research-only declarative strategy spec if the current bar
   archive can provide or derive its required data.
3. Implement only narrow, local declarative/compiler support needed for S31.
4. Rerun bounded evidence for accepted testable strategies.
5. Keep S59 skipped/deferred unless trade/L2 sweep features can be reproduced
   from collected or materialized data without pretending a weaker proxy is the
   same strategy.
6. Update the readiness verdict and known issues truthfully.

## Research boundary

All artifacts remain `research_only`, `observe_only`, and
`promotion_ready: false`. This packet must not create paper/live/order/sizing,
candidate-pack, promotion, production trading, or strategy-performance claims.

## Outcome

Implemented the corrected policy and S31 test surface:

- Archive-ref cycle base slippage is now `8` bps with a `20` bps worst-case
  reference; the existing 3x stress lane is stricter at `24` bps.
- Added declarative `vol_adjusted_trend` support for S31. It derives trend
  score from returns divided by realized volatility, uses candle-derived
  volatility/ATR inputs, caps per-instrument research weights, and scales total
  gross exposure to the strategy risk cap.
- Added accepted WPR106-555 specs for S31 and S54 under
  `configs/strategies/wpr106_555/accepted/**`.
- Marked S59 skipped for this readiness set because the current bounded
  vectorized cycle cannot yet consume event-level trades/L2 sweep and
  replenishment features. WPR106-552 proves OF-style features can be
  materialized, so S59 should be handled by a future event-driven replay packet
  rather than by a bar proxy.

Generated evidence:

- Materialization/reuse report:
  `data/research/wpr106_555_autonomous_readiness/materialization_report_2024_01_08.json`
- S54 base-8 bounded cycle:
  `data/research/wpr106_555_autonomous_readiness/cycle_s54_cross_reversion_base8_summary.json`
- Initial S31 base-8 bounded cycle:
  `data/research/wpr106_555_autonomous_readiness/cycle_s31_vol_adjusted_trend_base8_summary.json`
- S31 bounded parameter probes:
  `data/research/wpr106_555_autonomous_readiness/parameter_probe/s31_vol_adjusted_trend_base8/s31_parameter_probe_partial_summary.json`
  and
  `data/research/wpr106_555_autonomous_readiness/parameter_probe/s31_vol_adjusted_trend_base8_micro/s31_micro_probe_summary.json`
- Tuned S31 base-8 bounded cycle:
  `data/research/wpr106_555_autonomous_readiness/cycle_s31_vol_adjusted_trend_base8_tuned_summary.json`

The tuned S31 cycle is technically successful and base-case positive:

```text
net_return=0.0022629838731449414
gross_return=0.08585296976945722
total_turnover=64.99999999999866
trade_count=1228
fold_stability_score=1.0
```

It still finishes `completed_with_blockers` because cost stress fails:

```text
validation_status=fail
blocker_reasons=["cost_dependent_failure"]
base_cost_net_return=0.0022629838731449414
stress_2x_net_return=-0.07489973176516174
stress_3x_net_return=-0.14612879144902113
```

S54 remains negative at the 8 bps base case:

```text
net_return=-0.3254955638131598
blocker_reasons=["fold_stability_below_min_share"]
```

Therefore the repository still cannot be marked
`autonomous_research_ready`. The remaining issue is no longer unavailable data
for S59; it is that the currently tested S31/S54 accepted specs do not produce
a blocker-free accepted-research cycle under the required validation gates.

## Validation

Python 3.11 validation on 2026-06-27:

```text
py -3.11 -m compileall -q src\tradingbotsuite: passed
PYTHONPATH=src; py -3.11 -m pytest tests\v2\test_strategy_specs_phase10.py tests\v2\test_backtest_data_phase9.py tests\v2\test_autopilot_archive_cycle_phase75.py -q: 27 passed, 1 warning
PYTHONPATH=src; py -3.11 -m pytest tests\contracts -q: 463 passed, 1 warning
PYTHONPATH=src; py -3.11 -m pytest tests\v2 -q: 579 passed, 1 warning
PYTHONPATH=src; py -3.11 -m pytest tests -q: 2486 passed, 2 skipped, 6 warnings
git diff --check: passed; Git reported line-ending normalization warnings only
```

Warnings were existing deprecation warnings; no assertion failures or Windows
socket setup failures were observed.
