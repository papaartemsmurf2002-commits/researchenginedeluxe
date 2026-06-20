# WPR106-143 Diversity Robust Monthly Rotation Search

Date: 2026-06-12
Owner: Codex Research Agent
Status: closed

## Objective

Test whether the WPR106-141 monthly family-rotation idea can survive when
diversity and leave-one-source robustness are required at pre-May selection
time, rather than added as after-the-fact controls. The packet should broaden
from the single WPR106-141 lead by reranking and replaying many causal rotation
rules over the existing WPR106-130 through WPR106-140 trade-level source
universe, with exact behavior deduplication, packet/family diversity,
cross-symbol relative-strength robustness tests, and shuffled/shifted
diagnostic controls. May 2026 remains benchmark-only for fixed pre-May
selections.

## Allowed Paths

- `docs/work_packets/WPR106-143-diversity-robust-monthly-rotation-search.md`
- `docs/stage_reports/STAGE_R106_DIVERSITY_ROBUST_MONTHLY_ROTATION_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_143_diversity_robust_monthly_rotation_search/**`

## Inputs

- `data/research/wpr106_141_causal_monthly_family_rotation_search/**`
- `data/research/wpr106_142_monthly_rotation_lead_controls/**`
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
- All source universe construction, deduplication, rule selection, parameter
  choice, diversity/robustness thresholds, scoring, reranking, and selected
  row fixation must use only 2024-01-01 through 2026-04-30 artifacts.
- May 2026 may be replayed only after fixed pre-May selections are written.
- Diagnostic shuffled/shifted controls are not valid strategies and must not
  be used as candidate evidence.
- Portfolio replay must keep embedded source costs, same-symbol overlap
  skipping, and accepted-trade daily caps.
- CUDA is not expected. CPU/vectorized pandas/accounting is sufficient and no
  speedup claim is allowed unless a real CUDA path is used and verified.
- If a blocking correctness risk is found, update `docs/KNOWN_ISSUES.md`.

## Evidence Plan

1. Rebuild the WPR106-141 source universe using artifact-local helpers and
   remove exact duplicate pre-May trade behavior.
2. Re-evaluate causal monthly rotation rules with packet/family diversity
   constraints, daily accepted-trade caps of 1, 3, and 5, and scoring that
   rewards monthly stability, low drawdown, and low best-month concentration.
3. For pre-May promising rows, compute leave-one-source, leave-one-packet,
   leave-one-family, and no-cross-symbol-relative-strength robustness using
   pre-May data only.
4. Fix selected rows before May by requiring pre-May strictness, deduped source
   membership, diversity, and robustness floors.
5. Replay fixed selected rows on May 2026 as a benchmark holdout.
6. Run shifted/shuffled diagnostic selection controls to see whether distorted
   monthly evidence can produce similar pre-May strictness or May positivity.
7. Report whether stricter selection rescues the rotation family or strengthens
   the rejection.

## Validation

Run focused script compile, then the branch baseline:

```powershell
python -m compileall -q data/research/wpr106_143_diversity_robust_monthly_rotation_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Completed:

- `python -m compileall -q data/research/wpr106_143_diversity_robust_monthly_rotation_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed.

## Closeout

WPR106-143 rejects the monthly rotation family as a candidate path after a
stricter selection-time robustness search. Exact behavior deduplication
reduced the WPR106-141 universe from 659 to 518 source rows, and the stricter
grid found 18 strict/diverse pre-May rows. The top 60 diverse pre-May rows
produced 12 core-strict rows after leave-one-source, leave-one-packet,
leave-one-family, no-WPR106-133, and no-cross-symbol-relative-strength checks,
but no full robust-strict rows existed because calendar-like removal failed the
loose floor.

The fixed 12 core-strict rows all lost in May 2026: 0 positive, 12 negative,
best -0.019916, worst -0.021032, median -0.021032. Diagnostic shifted/shuffled
controls produced 88 selected rows and 8 May-positive rows, so pre-May
strict/diverse rotation evidence is not enough to trust the family. No
candidate pack, paper/live artifact, order/sizing/runtime change, live
configuration write, CUDA speedup claim, or promotion claim was created.
