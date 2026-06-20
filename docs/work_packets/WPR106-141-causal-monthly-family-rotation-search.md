# WPR106-141 Causal Monthly Family Rotation Search

Date: 2026-06-12
Owner: Codex Research Agent
Status: closed

## Objective

Test whether previously rejected 2024-forward families contain useful
month-stable information when combined by a causal month-by-month
family-rotation portfolio, rather than defended as static standalone rows. The
packet uses only prior completed research artifacts as inputs, selects source
rows for each month using only earlier pre-May monthly evidence, and keeps May
2026 fully out of tuning until fixed pre-May rotation rules are selected.

## Allowed Paths

- `docs/work_packets/WPR106-141-causal-monthly-family-rotation-search.md`
- `docs/stage_reports/STAGE_R106_CAUSAL_MONTHLY_FAMILY_ROTATION_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_141_causal_monthly_family_rotation_search/**`

## Inputs

- `data/research/wpr106_130_prior_day_level_gap_search/**`
- `data/research/wpr106_131_volatility_term_structure_search/**`
- `data/research/wpr106_132_multi_horizon_trend_state_search/**`
- `data/research/wpr106_133_cross_symbol_lead_lag_search/**`
- `data/research/wpr106_134_microstructure_state_transition_search/**`
- `data/research/wpr106_135_microstructure_annual_target_portfolio_search/**`
- `data/research/wpr106_136_cross_family_knn_trade_veto_search/**`
- `data/research/wpr106_137_diversity_constrained_knn_veto_ensemble/**`
- `data/research/wpr106_138_pre_may_robust_meta_selector/**`
- `data/research/wpr106_139_calendar_session_interaction_search/**`
- `data/research/wpr106_140_causal_rolling_calendar_profile_search/**`

## Boundaries

- Research-only, observe-only, promotion-ready false.
- No candidate pack, paper/live artifact, order placement, sizing change,
  runtime-mode change, live configuration write, or promotion claim.
- Source-row universe construction, monthly scoring rules, member counts,
  diversity rules, daily caps, threshold choices, ranking, and selection must
  use only 2024-01-01 through 2026-04-30.
- May 2026 may be replayed only after fixed pre-May rotation rows are written.
- For pre-May portfolio months, selected members must be chosen only from
  source-row monthly results completed before the evaluated month.
- For May 2026, member choice must be frozen from evidence completed through
  2026-04-30; no May source-row performance may influence May selection.
- Portfolio replay must account for costs already embedded in source trades,
  same-symbol overlap, and daily accepted-trade caps.
- CUDA is not expected. CPU/vectorized pandas/accounting is sufficient and no
  speedup claim is allowed unless a real CUDA path is used and verified.
- If a blocking correctness risk is found, update `docs/KNOWN_ISSUES.md`.

## Evidence Plan

1. Load selected pre-May source rows, monthly returns, and trade artifacts from
   WPR106-130 through WPR106-140 where present.
2. Build source-row identities that preserve source packet, symbol, family,
   template, candidate ID, and selection tier.
3. Search causal monthly rotation rules over trailing monthly lookbacks,
   scoring modes, family/source diversity settings, member counts, and daily
   accepted-trade caps targeting active 1-5 trades/day behavior.
4. Replay pre-May portfolios month by month using only earlier monthly evidence
   for member selection, equal member sleeves, same-symbol overlap handling,
   costs embedded in source trades, and additional cost-stress accounting.
5. Select strict rows first; if none exist, select loose rows. Then benchmark
   May 2026 separately with the fixed rule and member choice frozen from
   pre-May evidence through 2026-04-30.
6. Report whether causal rotation/complementarity rescues any old/discarded
   family evidence or confirms that the combined family set remains unstable.

## Validation

Run focused script compile, then the branch baseline:

```powershell
python -m compileall -q data/research/wpr106_141_causal_monthly_family_rotation_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Completed:

- `python -m compileall -q data/research/wpr106_141_causal_monthly_family_rotation_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed.

## Closeout

WPR106-141 found that causal monthly rotation can create strict-looking
pre-May portfolio rows from previously rejected or loose families, but the
fixed strict set does not survive May as a broad family. The run loaded 659
trade-level source rows from WPR106-130 through WPR106-137 and WPR106-139
through WPR106-140, explicitly skipped WPR106-138 because it has no trade-level
selected-row artifacts, and evaluated 864 rotation rules. All 864 rows were
positive pre-May; 668 were loose and 60 were strict. The fixed top-60 strict
May benchmark produced 3 May-positive rows, 57 May-negative rows, and 0 flat
rows, with median May net return -0.021032.

The rank-1 strict rule remains a research-only follow-up lead, not a candidate:
`monthrot-ed7358029b345be5` had 573 pre-May trades, 25 active months, 3 losing
months, +0.359543 pre-May net return, -0.046434 max drawdown, 0.190664
best-month share, full cost-stress survival, and +0.008070 May return after the
fixed May replay. It requires dedicated deduplication, source ablation, filter
ablation, negative controls, and gate checks before it can be trusted. No
candidate pack, paper/live artifact, order/sizing/runtime change, live
configuration write, CUDA speedup claim, or promotion claim was created.
