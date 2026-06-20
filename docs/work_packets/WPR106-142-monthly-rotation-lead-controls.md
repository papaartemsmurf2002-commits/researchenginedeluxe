# WPR106-142 Monthly Rotation Lead Controls

Date: 2026-06-12
Owner: Codex Research Agent
Status: closed

## Objective

Stress-test the WPR106-141 rank-1 causal monthly rotation lead
`monthrot-ed7358029b345be5` before treating it as more than a narrow
research-only lead. The packet keeps the WPR106-141 rule fixed from pre-May
evidence, then tests source deduplication, source/family/packet ablations,
calendar concentration controls, and shifted/shuffled monthly-evidence negative
controls. May 2026 remains benchmark-only after each fixed pre-May control
definition.

## Allowed Paths

- `docs/work_packets/WPR106-142-monthly-rotation-lead-controls.md`
- `docs/stage_reports/STAGE_R106_MONTHLY_ROTATION_LEAD_CONTROLS_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_142_monthly_rotation_lead_controls/**`

## Inputs

- `data/research/wpr106_141_causal_monthly_family_rotation_search/**`
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
- The tested lead rule is fixed from WPR106-141 pre-May evidence:
  6-month lookback, 5 members, max 1 accepted trade/day, stable-mean scoring,
  no diversity limit, max pair correlation 0.85.
- Control definitions, source removals, dedup decisions, and negative-control
  transforms must use only pre-May artifacts and WPR106-141 selected evidence.
- May 2026 may be replayed only after each fixed control definition is applied.
- Negative controls are diagnostic only and must not be treated as valid
  strategies.
- Portfolio replay must keep same-symbol overlap and daily accepted-trade caps.
- CUDA is not expected. CPU/vectorized pandas/accounting is sufficient and no
  speedup claim is allowed unless a real CUDA path is used and verified.
- If a blocking correctness risk is found, update `docs/KNOWN_ISSUES.md`.

## Evidence Plan

1. Rebuild the WPR106-141 source universe and fixed lead replay using the
   WPR106-141 artifact runner helpers.
2. Compute exact source-trade behavior hashes and rerun the fixed lead on a
   deduplicated source universe.
3. Rerun the fixed lead after removing May-selected sources, lead-used packets,
   and lead-used families.
4. Rerun calendar concentration controls: calendar-only and no-calendar source
   universes.
5. Rerun shifted and shuffled monthly-evidence controls while replaying actual
   source trades.
6. Report whether the lead survives ablations and whether negative controls
   can mimic the May-positive result.

## Validation

Run focused script compile, then the branch baseline:

```powershell
python -m compileall -q data/research/wpr106_142_monthly_rotation_lead_controls/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Completed:

- `python -m compileall -q data/research/wpr106_142_monthly_rotation_lead_controls/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed.

## Closeout

WPR106-142 keeps `monthrot-ed7358029b345be5` research-only. The lead survived
exact behavior deduplication, which removed 141 duplicate-behavior source rows,
and 16 of 33 non-diagnostic controls remained both pre-May strict and
May-positive. This is useful robustness evidence, but the lead did not clear
controls: dropping WPR106-133, dropping cross-symbol relative strength, or
dropping the May-selected WPR106-133 source kept pre-May strictness but made
May negative; dropping WPR106-139 broke pre-May strictness; and one of five
diagnostic shifted/shuffled monthly-evidence controls was May-positive.

The result is a narrow, fragile research lead requiring more work, not a
candidate. No candidate pack, paper/live artifact, order/sizing/runtime change,
live configuration write, CUDA speedup claim, or promotion claim was created.
