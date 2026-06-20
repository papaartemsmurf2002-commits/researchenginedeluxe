# WPR106-138 Pre-May Robust Meta-Selector

Date: 2026-06-12
Owner: Codex Research Agent
Status: closed

## Objective

Test whether a pre-May-only robustness selector can identify month-stable leads
across prior 2024-forward selected families before the May 2026 benchmark. The
packet is intentionally cross-family: it revisits selected rows from
WPR106-130 through WPR106-137, including old discarded rows, portfolio rows,
KNN-veto overlays, and diversity-constrained ensembles, and ranks them by
monthly stability, late-window behavior, active-rate reasonableness, drawdown,
and best-month concentration without using May 2026.

## Allowed Paths

- `docs/work_packets/WPR106-138-pre-may-robust-meta-selector.md`
- `docs/stage_reports/STAGE_R106_PRE_MAY_ROBUST_META_SELECTOR_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_138_pre_may_robust_meta_selector/**`

## Inputs

- `data/research/wpr106_130_prior_day_level_gap_search/**`
- `data/research/wpr106_131_volatility_term_structure_search/**`
- `data/research/wpr106_132_multi_horizon_trend_state_search/**`
- `data/research/wpr106_133_cross_symbol_lead_lag_search/**`
- `data/research/wpr106_134_microstructure_state_transition_search/**`
- `data/research/wpr106_135_microstructure_annual_target_portfolio_search/**`
- `data/research/wpr106_136_cross_family_knn_trade_veto_search/**`
- `data/research/wpr106_137_diversity_constrained_knn_veto_ensemble/**`

## Boundaries

- Research-only, observe-only, promotion-ready false.
- No candidate pack, paper/live artifact, order placement, sizing change,
  runtime-mode change, live configuration write, or promotion claim.
- May 2026 must not influence source-packet inclusion, row inclusion,
  robustness-score construction, threshold choice, ranking, or fixed
  selection.
- May 2026 may be read only after a fixed pre-May selection is written.
- The selector may use prior generated May benchmark artifacts only for the
  fixed benchmark report, never for pre-May feature construction or ranking.
- CUDA is not expected. CPU/vectorized pandas accounting is sufficient and no
  speedup claim is allowed.
- If a blocking correctness risk is found, update `docs/KNOWN_ISSUES.md`.

## Evidence Plan

1. Load selected pre-May metrics and monthly returns from WPR106-130 through
   WPR106-137.
2. Normalize row identity across single strategies, portfolios, overlays, and
   ensembles without rewriting prior artifacts.
3. Score each row using only 2024-01-01 through 2026-04-30 monthly metrics:
   losing-month count by year, worst month, late-window return, rolling
   six-month loss count, active months, trades per active day, drawdown,
   best-month share, and cost-stress survival.
4. Select fixed strict rows first, then loose rows if strict is empty. The
   strict screen should prefer zero to two losing months per full calendar year
   and at most one losing month in 2026 Jan-Apr, while allowing active
   strategies around 1-5 trades per active day.
5. After fixed pre-May selection, attach May 2026 benchmark metrics from the
   existing packet artifacts and report the holdout distribution separately.
6. Reject or preserve the lead based on the May benchmark and evidence depth.

## Validation

Run focused script compile, then the branch baseline:

```powershell
python -m compileall -q data/research/wpr106_138_pre_may_robust_meta_selector/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Completed:

- `python -m compileall -q data/research/wpr106_138_pre_may_robust_meta_selector/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

## Closeout

Closed as a rejected research lead. The selector loaded 558 previously selected
rows from WPR106-130 through WPR106-137 and ranked them using only pre-May
monthly behavior from 2024-01-01 through 2026-04-30. It found all 558 rows
positive by construction, 168 selector-strict rows, and 277 selector-loose rows.
The fixed top-100 strict selection was dominated by WPR106-137 KNN-veto
ensembles and WPR106-135 equal-sleeve portfolios: 69 KNN-veto ensemble rows and
31 portfolio rows.

May 2026 was then attached only as a benchmark after fixed selection. May
rejected the selected set with 20 positive, 80 negative, and 0 flat rows; best
May was +0.012709, worst May was -0.035239, and median May was -0.009168. The
pre-May robustness score improved the WPR106-137 median holdout loss versus the
plain WPR106-137 top-100 selection, but not enough to create a viable lead. No
candidate pack, paper/live artifact, order/sizing/runtime change, live
configuration write, CUDA speedup claim, or promotion claim exists.
