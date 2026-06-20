# WPR106-144 Direct Source Family Stability Benchmark

Date: 2026-06-12
Owner: Codex Research Agent
Status: closed

## Objective

Move away from defending the rejected monthly-rotation line by testing the
underlying strategy rows and source families directly. The packet evaluates
deduplicated individual source rows and fixed equal-sleeve source-family
portfolios using only 2024-01-01 through 2026-04-30 for selection, with active
1-5 trades/day behavior allowed when costs and overlap are handled. May 2026
is benchmark-only for fixed pre-May selections.

## Allowed Paths

- `docs/work_packets/WPR106-144-direct-source-family-stability-benchmark.md`
- `docs/stage_reports/STAGE_R106_DIRECT_SOURCE_FAMILY_STABILITY_BENCHMARK_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_144_direct_source_family_stability_benchmark/**`

## Inputs

- `data/research/wpr106_141_causal_monthly_family_rotation_search/**`
- `data/research/wpr106_143_diversity_robust_monthly_rotation_search/**`
- `data/research/wpr106_130_prior_day_level_gap_search/**`
- `data/research/wpr106_131_volatility_term_structure_search/**`
- `data/research/wpr106_132_multi_horizon_trend_state_search/**`
- `data/research/wpr106_133_cross_symbol_lead_lag_search/**`
- `data/research/wpr106_134_microstructure_state_transition_search/**`
- `data/research/wpr106_135_microstructure_annual_target_portfolio_search/**`
- `data/research/wpr106_136_cross_family_knn_trade_veto_search/**`
- `data/research/wpr106_137_diversity_constrained_knn_veto_ensemble/**`
- `data/research/wpr106_139_calendar_session_interaction_search/**`
- `data/research/wpr106_140_causal_rolling_calendar_profile_search/**`

## Boundaries

- Research-only, observe-only, promotion-ready false.
- No candidate pack, paper/live artifact, order placement, sizing change,
  runtime-mode change, live configuration write, or promotion claim.
- All source-row deduplication, source scoring, group construction, member
  selection, daily-cap choice, ranking, and selected-row fixation must use only
  2024-01-01 through 2026-04-30 artifacts.
- May 2026 may be replayed only after fixed pre-May selections are written.
- Fixed portfolios must use embedded source trade returns/costs, equal outer
  sleeves, same-symbol overlap skipping, and explicit daily accepted-trade caps
  of 1, 3, or 5.
- CUDA is not expected. CPU/vectorized pandas/accounting is sufficient and no
  speedup claim is allowed unless a real CUDA path is used and verified.
- If a blocking correctness risk is found, update `docs/KNOWN_ISSUES.md`.

## Evidence Plan

1. Rebuild the WPR106-141 trade-level source universe and remove exact
   duplicate pre-May trade behavior.
2. Recompute individual source-row pre-May and May metrics from normalized
   trade artifacts, including monthly returns, active days, active rate,
   drawdown, Sortino, best-month share, and cost-stress survival.
3. Build fixed source-family portfolios from pre-May evidence only: packet,
   family, packet-family, symbol, and packet-symbol groups with top stable
   members and accepted-trade caps of 1, 3, and 5.
4. Select strict or loose pre-May rows before loading May benchmark metrics.
5. Benchmark fixed selected rows on May 2026 and report whether direct rows or
   fixed families survive.
6. Preserve artifacts for row metrics, fixed portfolio metrics, selected rows,
   May benchmark rows, monthly tables, and trades.

## Validation

Run focused script compile, then the branch baseline:

```powershell
python -m compileall -q data/research/wpr106_144_direct_source_family_stability_benchmark/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Completed:

- `python -m compileall -q data/research/wpr106_144_direct_source_family_stability_benchmark/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed.

## Closeout

WPR106-144 rejects direct source-family selection as a broad rescue. Exact
behavior deduplication reduced the WPR106-141 universe from 659 to 518 source
rows. The packet evaluated 1,554 individual source rows and 627 fixed
source-family portfolios, found 422 strict pre-May rows, and fixed the top 120
strict rows before May. May 2026 rejected the broad selected set with 30
positive rows, 90 negative rows, best +0.015157, worst -0.118374, and median
-0.002191.

The packet surfaced narrow research-only follow-up leads from WPR106-137:
`vetoensemble-0984617d185c319b` and `vetoensemble-2b025e21f7235d09`. They
combine strong pre-May stability with positive May, but require source-member
ablation, cross-symbol-relative-strength controls, KNN-veto dependence tests,
shifted/no-KNN controls, and cluster sensitivity checks before trust. No
candidate pack, paper/live artifact, order/sizing/runtime change, live
configuration write, CUDA speedup claim, or promotion claim was created.
