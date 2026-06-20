# WPR106-147 WPR133 Behavior-Dedup Stability Controls

Date: 2026-06-12
Owner: Codex Research Agent
Status: closed

## Objective

Stress-test the WPR106-146 ETHUSDT `cross_symbol_relative_strength` follow-up
lead before treating it as more than a narrow research-only lead.

The packet starts from the WPR106-146 target source
`wpr133_leadlag:leadlag-18708dffa1413dce` and its strongest nearby
`regime_reversal` + Lorentzian + same-side KNN variants. It must reduce
parameter-duplicate evidence with behavior hashes, test whether pre-May-only
rolling selection remains stable, check whether the same KNN settings work on
neighboring WPR106-133 relative-strength source rows, and run simple BTC hedge
diagnostics. May 2026 remains fully out of tuning and is used only as a
benchmark for fixed rows.

## Allowed Paths

- `docs/work_packets/WPR106-147-wpr133-behavior-dedup-stability-controls.md`
- `docs/stage_reports/STAGE_R106_WPR133_BEHAVIOR_DEDUP_STABILITY_CONTROLS_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_147_wpr133_behavior_dedup_stability_controls/**`

## Inputs

- `data/research/wpr106_133_cross_symbol_lead_lag_search/**`
- `data/research/wpr106_136_cross_family_knn_trade_veto_search/**`
- `data/research/wpr106_146_wpr133_relative_strength_overlay_causal_audit/**`

## Boundaries

- Research-only, observe-only, promotion-ready false.
- No candidate pack, paper/live artifact, order placement, sizing change,
  runtime-mode change, live configuration write, or promotion claim.
- May 2026 must not affect parameter grids, behavior-dedup selection,
  rolling-selection rules, sibling-source controls, hedge settings, ranking, or
  control definitions.
- Side, sibling-source, and hedge outputs are diagnostic controls, not
  candidate claims.
- Active rates of 1, 3, and 5 accepted trades/day are allowed when costs and
  overlap are accounted for.
- CUDA is not expected. CPU/vectorized pandas/accounting is sufficient and no
  speedup claim is allowed unless a real CUDA path is used and verified.
- If a blocking correctness risk is found, update `docs/KNOWN_ISSUES.md`.

## Evidence Plan

1. Re-evaluate the WPR106-146 KNN parameter grid for the target source and add
   accepted-trade behavior hashes.
2. Deduplicate by pre-May behavior hash, keeping the best pre-May representative
   per behavior using only pre-May metrics.
3. Run rolling pre-May train/holdout selections over anchored pre-May windows
   to test whether the deduped lead survives without using later months for
   selection.
4. Fix top behavior-deduped rows from pre-May only and replay May 2026 as a
   benchmark.
5. Apply the top pre-May KNN parameter settings to sibling WPR106-133 ETHUSDT
   relative-strength continuation source rows and benchmark May only after
   fixed source/parameter controls.
6. Run BTC hedge diagnostics for fixed top rows with hedge weights selected
   from a predeclared grid, using embedded ETH costs plus BTC hedge costs.
7. Decide whether the WPR106-146 lead survives as a broader source-level lead
   or remains a path-coupled research-only diagnostic.

## Validation

Run focused script compile, then the branch baseline:

```powershell
python -m compileall -q data/research/wpr106_147_wpr133_behavior_dedup_stability_controls/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Completed:

- `python -m compileall -q data/research/wpr106_147_wpr133_behavior_dedup_stability_controls/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed.

## Closeout

WPR106-147 rejects the WPR106-146 target as a broader source-level strategy.
The 12,000-row target grid collapsed to 2,340 unique pre-May behavior hashes;
only 15 behavior-deduped representatives remained strict-like. The top 30
behavior-deduped rows were all May-positive after fixed pre-May selection, but
rolling pre-May selection was holdout-positive in only 3/6 top-1 splits and
3/6 top-3 equal-average splits.

Sibling-source transfer failed: across five top parameter settings and 14
ETHUSDT relative-strength continuation source rows, the target passed in 5/5
controls but non-target siblings had 0 strict-like rows and 0 rows passing both
pre-May profile and May benchmark. BTC hedge diagnostics also failed to improve
the lead: no hedge row was strict-like, and 1.00 hedge variants turned May
negative.

The target remains a path-specific research pocket, not a candidate-ready or
source-family-ready lead. No candidate pack, paper/live artifact,
order/sizing/runtime change, live configuration write, CUDA speedup claim, or
promotion claim was created.
