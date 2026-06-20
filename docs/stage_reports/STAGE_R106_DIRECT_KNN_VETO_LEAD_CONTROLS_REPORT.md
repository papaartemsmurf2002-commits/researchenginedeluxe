# Stage R106 Direct KNN Veto Lead Controls Report

Date: 2026-06-12
Packet: WPR106-145
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

The controlled leads were fixed from WPR106-144 and WPR106-137 pre-May
evidence. Control definitions used only 2024-01-01 through 2026-04-30 and the
pre-May selected lead metadata. May 2026 was replayed only after each fixed
control definition. No-KNN rows are diagnostic baselines only.

## Method

The runner
`data/research/wpr106_145_direct_knn_veto_lead_controls/scripts/run_wpr106_145_direct_knn_veto_lead_controls.py`
imports the WPR106-137 artifact runner and replays the needed WPR106-136 and
WPR106-137 overlay members with the same feature and accounting helpers.

Tested lead variants:

- WPR106-137 `vetoensemble-0984617d185c319b` at daily caps 1, 3, and 5.
- WPR106-137 `vetoensemble-2b025e21f7235d09` at daily caps 1, 3, and 5.

The daily-cap 1 variant of `vetoensemble-0984617d185c319b` and daily-cap 3/5
variants of `vetoensemble-2b025e21f7235d09` were the WPR106-144 follow-up
leads. Daily-cap variants were included to test active-rate sensitivity within
the user-allowed 1-5 trades/day range.

Controls:

- baseline replay from raw overlay member trades;
- drop each overlay member;
- isolate each overlay member as diagnostic-only;
- remove all WPR106-133 lead-lag members;
- remove all `cross_symbol_relative_strength` members;
- keep ETHUSDT-only or BTCUSDT-only subsets where applicable;
- diagnostic no-KNN baseline using the same underlying source trades before
  KNN veto filtering;
- diagnostic month sensitivity removing the best pre-May month, worst pre-May
  month, and most active pre-May month.

## Results

Overall:

- Lead variants: 6.
- Unique overlay members replayed: 5.
- Control rows: 84.
- Non-diagnostic controls: 39.
- Diagnostic controls: 45.
- Baseline rows: 6.
- Baseline rows with pre-May profile ok: 6.
- Baseline rows May-positive: 6.
- Non-diagnostic survivors: 26.
- Non-diagnostic May-positive controls: 27.
- Diagnostic May-positive controls: 27.
- No-KNN diagnostic rows: 6.
- No-KNN May-positive rows: 3.
- Best non-diagnostic May: +0.027784.
- Worst non-diagnostic May: -0.016893.
- Median non-diagnostic May: +0.009265.

Baseline replays:

- `veto098_cap1`: 345 pre-May trades, 26 active months, 2 losing months,
  +0.706472 pre-May, -0.045469 max drawdown, +0.015157 May.
- `veto098_cap3`: 385 pre-May trades, 26 active months, 4 losing months,
  +0.708908 pre-May, -0.045469 max drawdown, +0.012709 May.
- `veto098_cap5`: same as cap 3.
- `veto2b025_cap1`: 320 pre-May trades, 26 active months, 5 losing months,
  +0.517565 pre-May, -0.057025 max drawdown, +0.012573 May.
- `veto2b025_cap3`: 404 pre-May trades, 26 active months, 2 losing months,
  +0.728679 pre-May, -0.053935 max drawdown, +0.009265 May.
- `veto2b025_cap5`: same as cap 3.

Important concentration evidence:

- The single WPR106-133 `cross_symbol_relative_strength` overlay member
  `tradeveto-3a585c9bd5b09303` was the strongest May contributor. Isolating it
  produced +0.059766 May across all relevant daily caps, while the other
  isolated members were May-negative.
- For `veto2b025`, removing the WPR106-133/cross-symbol-relative-strength
  member kept the pre-May profile plausible but made May negative at all caps:
  -0.016893 at cap 1 and -0.016095 at caps 3/5.
- For `veto098`, removing all WPR106-133 lead-lag members left only the
  WPR106-131 volatility-term member and made May negative at -0.000680.
- For `veto098`, removing only the `cross_symbol_relative_strength` member
  kept May positive, but the cap 3/5 variants survived only 1/4 May cost-stress
  scenarios.
- For `veto2b025`, the ETHUSDT-only subset survived and improved May to
  +0.021757, while the BTCUSDT-only diagnostic subset was May-negative.

No-KNN diagnostic baselines:

- `veto098` no-KNN source baselines were May-positive (+0.007792 at cap 1 and
  +0.012485 at caps 3/5), but failed pre-May profile checks because they had
  9 losing months.
- `veto2b025` no-KNN source baselines were May-negative (-0.002224 at cap 1 and
  -0.007473 at caps 3/5). The cap 3/5 no-KNN baselines had a plausible pre-May
  profile but failed the May benchmark.

Month sensitivity:

- Removing the best pre-May month, worst pre-May month, or most active pre-May
  month did not break the baseline pre-May profile for the tested leads.
- This is useful stability evidence, but it does not resolve the member
  concentration and WPR106-133 dependence.

## Decision

The WPR106-144 KNN-veto ensemble leads remain research-only and fail-closed.
They are not duplicate or single-month artifacts, but they are not clean
candidate leads either. The May-positive behavior is materially concentrated in
the same WPR106-133 cross-symbol-relative-strength overlay member, and removing
that member breaks the `veto2b025` May benchmark entirely. The `veto098`
variant has better ablation survival, but WPR106-133 removal still turns May
negative and no-KNN diagnostics show that part of the May behavior can exist
without the KNN veto.

The next useful work should not try to candidate-pack these ensembles. A better
follow-up is a direct causal audit of the WPR106-133 relative-strength overlay
member itself, including alternative distance parameters, no-KNN/no-veto
baselines, source-side controls, and additional holdout/cluster tests.

## Artifacts

- `data/research/wpr106_145_direct_knn_veto_lead_controls/wpr106_145_direct_knn_veto_lead_controls_summary.json`
- `data/research/wpr106_145_direct_knn_veto_lead_controls/control_metrics.parquet`
- `data/research/wpr106_145_direct_knn_veto_lead_controls/control_metrics.csv`
- `data/research/wpr106_145_direct_knn_veto_lead_controls/pre_may/lead_overlay_universe.parquet`
- `data/research/wpr106_145_direct_knn_veto_lead_controls/pre_may/wpr136_source_pool_snapshot.parquet`
- `data/research/wpr106_145_direct_knn_veto_lead_controls/pre_may/control_monthly_returns.parquet`
- `data/research/wpr106_145_direct_knn_veto_lead_controls/pre_may/control_trades.parquet`
- `data/research/wpr106_145_direct_knn_veto_lead_controls/may_benchmark/control_monthly_returns.parquet`
- `data/research/wpr106_145_direct_knn_veto_lead_controls/may_benchmark/control_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_145_direct_knn_veto_lead_controls/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
