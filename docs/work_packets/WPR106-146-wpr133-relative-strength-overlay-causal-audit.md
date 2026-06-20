# WPR106-146 WPR133 Relative-Strength Overlay Causal Audit

Date: 2026-06-12
Owner: Codex Research Agent
Status: closed

## Objective

Audit the WPR106-133 cross-symbol relative-strength member that WPR106-145
identified as the strongest positive May 2026 contributor inside the rejected
WPR106-144/WPR106-137 KNN-veto leads:

- WPR106-137 overlay `tradeveto-3a585c9bd5b09303`;
- source row `wpr133_leadlag:leadlag-18708dffa1413dce`;
- family `cross_symbol_relative_strength`;
- template `relative_strength_continuation`;
- symbol `ETHUSDT`.

The packet must determine whether the May-positive behavior is a robust
research-only lead, a narrow KNN parameter artifact, or mostly explained by the
raw WPR106-133 source row. All parameter, filter, and selection decisions use
2024-01-01 through 2026-04-30 only. May 2026 remains fully out of tuning and is
used only as a benchmark after fixed pre-May selections and controls are
written.

## Allowed Paths

- `docs/work_packets/WPR106-146-wpr133-relative-strength-overlay-causal-audit.md`
- `docs/stage_reports/STAGE_R106_WPR133_RELATIVE_STRENGTH_OVERLAY_CAUSAL_AUDIT_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_146_wpr133_relative_strength_overlay_causal_audit/**`

## Inputs

- `data/research/wpr106_133_cross_symbol_lead_lag_search/**`
- `data/research/wpr106_136_cross_family_knn_trade_veto_search/**`
- `data/research/wpr106_137_diversity_constrained_knn_veto_ensemble/**`
- `data/research/wpr106_145_direct_knn_veto_lead_controls/**`

## Boundaries

- Research-only, observe-only, promotion-ready false.
- No candidate pack, paper/live artifact, order placement, sizing change,
  runtime-mode change, live configuration write, or promotion claim.
- May 2026 must not affect KNN parameter grids, selection thresholds, row
  ranking, or control definitions.
- No-KNN/no-veto source rows and side controls are diagnostic baselines, not
  valid candidate claims.
- Replays must preserve embedded source costs, overlap handling, explicit
  accepted-trade daily caps, and WPR106-136 frozen pre-May history for May.
- Active rates of 1, 3, and 5 accepted trades/day are allowed when overlap and
  costs are accounted for.
- CUDA is not expected. CPU/vectorized pandas/accounting is sufficient and no
  speedup claim is allowed unless a real CUDA path is used and verified.
- If a blocking correctness risk is found, update `docs/KNOWN_ISSUES.md`.

## Evidence Plan

1. Load the target WPR106-137 overlay row and underlying WPR106-136 source
   trades for pre-May and May.
2. Recompute the exact WPR106-137 overlay baseline for the target source using
   the existing WPR106-136 causal KNN helpers.
3. Run diagnostic no-KNN/no-veto source baselines for daily caps 1, 3, and 5.
4. Run target-source side controls for raw source trades and KNN overlays.
5. Run a nearby KNN parameter grid over `path_flow` and `regime_reversal`,
   Lorentzian and Euclidean distance, multiple lookbacks/neighbors, same-side
   history choices, neighbor mean/win thresholds, and daily caps 1, 3, and 5.
6. Rank and select promising rows using only pre-May monthly stability,
   annual loss counts, cost stress, drawdown, best-month concentration, and
   active-rate constraints.
7. Replay fixed pre-May selections and controls on May 2026 only as a benchmark.
8. Record whether any row has a stable pre-May profile and a May benchmark that
   survives raw-source, side, and parameter-neighborhood controls.

## Validation

Run focused script compile, then the branch baseline:

```powershell
python -m compileall -q data/research/wpr106_146_wpr133_relative_strength_overlay_causal_audit/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Completed:

- `python -m compileall -q data/research/wpr106_146_wpr133_relative_strength_overlay_causal_audit/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed.

## Closeout

WPR106-146 found a narrow research-only follow-up lead, not a candidate-ready
strategy. The exact WPR106-137 overlay remains profile-ok but not strict:
203 pre-May trades, 26 active months, 5 losing months, annual losses 1/3/1,
+1.130996 pre-May, -0.136225 max drawdown, full cost-stress survival, and
+0.059766 May.

The nearby `regime_reversal` + Lorentzian + same-side KNN variants improve
stability: the top row has 242 pre-May trades, 25 active months, 4 losing
months, annual losses 2/2/0, +1.140510 pre-May, -0.145973 max drawdown, full
cost-stress survival, and +0.067949 May. Across 12,000 parameter-grid rows,
4,377 were profile-ok, 45 were strict-like, 30 met WPR106-136 strict rules, and
all 48 fixed selected rows were May-positive.

The lead remains fail-closed because May behavior is tightly coupled to the raw
WPR106-133 source path: raw no-KNN source cap 3/5 is also May-positive at
+0.065272, selected rows collapse to 17 unique pre-May behavior hashes and 8
unique May behavior hashes, and the top row only excludes one negative May raw
source trade. The next useful packet should run source-level causal stability,
behavior-deduped parameter selection, additional rolling holdouts, and
portfolio/hedge controls. No candidate pack, paper/live artifact,
order/sizing/runtime change, live configuration write, CUDA speedup claim, or
promotion claim was created.
