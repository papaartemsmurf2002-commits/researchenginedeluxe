# Stage R106 Pre-May Component Pocket Control Audit Report

Date: 2026-06-12
Packet: WPR106-161
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of component scoring, row scoring, control matching,
exposure caps, ranking, and selection. May was replayed only after selected
components, selected pocket rows, and matched control rows were fixed from
pre-May evidence.

## Method

The runner
`data/research/wpr106_161_pre_may_component_pocket_control_audit/scripts/run_wpr106_161_pre_may_component_pocket_control_audit.py`
reuses the WPR106-157 artifact-universe builder, which normalizes local WPR106
selected artifacts, behavior-de-duplicates accepted pre-May trade paths, and
recomputes common metrics from trade details.

Selection uses only 2024-01-01 through 2026-04-30:

- row-level 2024-2025 search return and dropout robustness;
- row-level 2026 Jan-Apr validation return, active months, and losing months;
- annual losing-month counts for 2024 and 2025;
- rolling six-month search stability and active trade-rate caps;
- component aggregation by packet, family, and template;
- component selection by row count, eligible-row count, validation-positive
  rate, median 2026 Jan-Apr validation return, median 2024-2025 search return,
  median dropout return, and packet/symbol caps;
- matched controls from non-selected components with similar pre-May scores,
  symbols, packets where possible, and trade-count scale.

Compute used vectorized pandas artifact loading and grouped metric replay from
the WPR106-157 builder. No CUDA path was used because this packet is an
artifact-level control audit, not a new model/backtest grid, and no speedup was
claimed.

## Results

Broad source universe:

- Included packet directories: 43.
- Loaded metric rows: 2,925.
- Loaded pre-May trade rows: 591,571.
- Loaded May benchmark trade rows: 21,216.
- Behavior-deduplicated source rows: 1,915.
- Component rows: 249.
- Pre-May selected components: 24.
- Selected component-pocket rows: 81.
- Matched control rows: 81.

Pre-May selected component exposure:

- WPR106-137: 4 components, 55 source rows, 54 eligible rows.
- WPR106-119: 4 components, 21 source rows, 21 eligible rows.
- WPR106-135: 4 components, 8 source rows, 8 eligible rows.
- WPR106-139: 3 components, 15 source rows, 15 eligible rows.
- WPR106-144: 2 components, 6 source rows, 6 eligible rows.
- WPR106-121, WPR106-146, WPR106-120, WPR106-108, WPR106-150,
  WPR106-125, and WPR106-134: 1 component each.

Selected pocket rows versus matched controls before May:

- Component-pocket rows: 81 rows, 12 packets, 24 components.
- Matched controls: 81 rows, 20 packets, 55 components.
- Component-pocket median trade count: 333 versus matched-control median 323.
- Component-pocket median 2024-2025 search return: +0.662945 versus matched
  control +0.579820.
- Component-pocket median 2026 Jan-Apr validation return: +0.087639 versus
  matched control +0.078741.
- Component-pocket median search drop-best-three return: +0.384807 versus
  matched control +0.328117.
- Component-pocket median pre-May total net return: +0.745853 versus matched
  control +0.687570.
- Component-pocket median pre-May row score: +1.263440 versus matched control
  +1.185108.

May 2026 benchmark after fixed pre-May selection:

- Component-pocket group: 81 rows, 19 positive, 60 negative, 2 flat, best
  +0.067949, worst -0.133646, median -0.015958, mean -0.015143.
- Matched-control group: 81 rows, 10 positive, 68 negative, 3 flat, best
  +0.027293, worst -0.132690, median -0.015520, mean -0.020810.

May-positive component pockets:

- WPR106-146 cross-symbol relative-strength trade-veto variants: 4/4 positive
  in May, median +0.063858, mean +0.060721, best +0.067949, worst +0.047219.
- WPR106-119 wick-fade variants: 4/4 positive, median +0.003795.
- WPR106-120 wick-fade variants: 4/4 positive, median +0.003784.
- One WPR106-135 microstructure component was 2/2 positive with median
  +0.001298.

May-negative concentration:

- WPR106-139 calendar-session momentum: 0/4 positive, median -0.062302,
  mean -0.074903, worst -0.133646.
- WPR106-134 microstructure flow agreement: 0/4 positive, median -0.061718.
- WPR106-121 flow-confirmed squeeze: 0/2 positive, both -0.051256.
- WPR106-119 rolling KNN: 0/4 positive, median -0.041900.
- WPR106-137 selected components were collectively 0/15 positive in May.

## Decision

The pre-May component pocket control audit is rejected as candidate-ready,
portfolio-ready, or promotion-ready evidence. Component-level selection did
improve the May positive count and mean relative to matched controls, but the
fixed component-pocket group still had 60/81 losing rows and a negative median.
That is not the requested stable month-to-month profile.

The packet gives stronger research-only evidence that some small components
deserve targeted May-blind follow-up, especially WPR106-146 cross-symbol
relative-strength trade-veto and the small WPR106-119/WPR106-120 wick-fade
pockets. It also strengthens the rejection of WPR106-139 calendar/session
families and WPR106-137 selected components for current May transfer.

Future work must define any targeted follow-up only from pre-May structure and
controls, then replay May after the target is fixed. The observed May-positive
pockets are not sufficient by themselves to choose parameters or claim
candidate readiness.

## Artifacts

- `data/research/wpr106_161_pre_may_component_pocket_control_audit/wpr106_161_pre_may_component_pocket_control_audit_summary.json`
- `data/research/wpr106_161_pre_may_component_pocket_control_audit/pre_may/artifact_inventory.parquet`
- `data/research/wpr106_161_pre_may_component_pocket_control_audit/pre_may/row_pre_may_ranking.parquet`
- `data/research/wpr106_161_pre_may_component_pocket_control_audit/pre_may/row_pre_may_top2500.csv`
- `data/research/wpr106_161_pre_may_component_pocket_control_audit/pre_may/component_diagnostics.parquet`
- `data/research/wpr106_161_pre_may_component_pocket_control_audit/pre_may/component_diagnostics.csv`
- `data/research/wpr106_161_pre_may_component_pocket_control_audit/pre_may/selected_components.parquet`
- `data/research/wpr106_161_pre_may_component_pocket_control_audit/pre_may/selected_components.csv`
- `data/research/wpr106_161_pre_may_component_pocket_control_audit/pre_may/selected_component_pocket_rows.parquet`
- `data/research/wpr106_161_pre_may_component_pocket_control_audit/pre_may/selected_component_pocket_rows.csv`
- `data/research/wpr106_161_pre_may_component_pocket_control_audit/pre_may/matched_control_rows.parquet`
- `data/research/wpr106_161_pre_may_component_pocket_control_audit/pre_may/matched_control_rows.csv`
- `data/research/wpr106_161_pre_may_component_pocket_control_audit/pre_may/selected_and_control_rows.parquet`
- `data/research/wpr106_161_pre_may_component_pocket_control_audit/pre_may/selected_and_control_rows.csv`
- `data/research/wpr106_161_pre_may_component_pocket_control_audit/pre_may/selected_and_control_pre_may_trades.parquet`
- `data/research/wpr106_161_pre_may_component_pocket_control_audit/may_benchmark/selected_and_control_may_metrics.parquet`
- `data/research/wpr106_161_pre_may_component_pocket_control_audit/may_benchmark/selected_and_control_may_metrics.csv`
- `data/research/wpr106_161_pre_may_component_pocket_control_audit/may_benchmark/selected_and_control_may_monthly_returns.parquet`
- `data/research/wpr106_161_pre_may_component_pocket_control_audit/may_benchmark/selected_and_control_may_daily_returns.parquet`
- `data/research/wpr106_161_pre_may_component_pocket_control_audit/may_benchmark/selected_and_control_may_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_161_pre_may_component_pocket_control_audit/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
