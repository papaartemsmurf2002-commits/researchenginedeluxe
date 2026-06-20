# Stage R106 Pre-May Family Prototype Transfer Controls Report

Date: 2026-06-12
Work packet: WPR106-164-pre-may-family-prototype-transfer-controls
Status: rejected as candidate-ready, portfolio-ready, and promotion-ready evidence

## Scope

WPR106-164 tested whether broad family/template prototypes can be selected from
pre-May group-level evidence alone and transfer to May better than matched
non-selected controls.

All prototype scoring, prototype selection, representative-row selection,
control matching, and portfolio construction used only 2024-01-01 through
2026-04-30. May 2026 was excluded from tuning and used only after selected
prototypes, rows, controls, and portfolios were fixed.

The packet is research-only and observe-only. It writes no candidate pack, no
paper/live artifact, no live configuration, no sizing change, no order path,
and no promotion claim.

## Inputs

The runner rebuilt the WPR106-157 broad artifact universe and reused WPR106-163
pre-May adverse-regime diagnostics:

- Included packet directories: 43.
- Loaded metric rows: 2,925.
- Loaded pre-May trade rows: 591,571.
- Loaded May benchmark trade rows: 21,216.
- Behavior-deduplicated source rows: 1,915.
- Prototype groups: 305.

Prototype keys were packet, symbol, family, and template combinations.

## Method

Prototype scoring used only pre-May row evidence:

- row support and non-duplicate row count;
- median total return;
- median 2024-2025 search return;
- median 2026 Jan-Apr validation return;
- median adverse-month return;
- median adverse-day return;
- median drop-best-three-month return;
- median losing-month counts;
- median cost-stress survival;
- median drawdown, best-month concentration, active months, and trades per
  active day.

The runner selected prototypes under packet, family, and symbol caps. It then
selected up to four representative rows per selected prototype, matched one
control for each selected row from non-selected prototypes, and generated
equal-sleeve selected/control portfolios from the fixed row sets.

## Pre-May Results

Prototype universe:

- Strict prototypes: 25.
- Robust prototypes: 33.
- Watch prototypes: 105.
- Positive-only prototypes: 142.

Fixed selections:

- Selected prototypes: 32.
- Selected representative rows: 100.
- Matched controls: 100.

Selected prototype packets were concentrated in:

- WPR106-135: 6 prototypes.
- WPR106-119: 5 prototypes.
- WPR106-113: 4 prototypes.
- WPR106-120: 4 prototypes.
- WPR106-139: 3 prototypes.
- WPR106-137: 3 prototypes.

The pre-May prototype ranking selected WPR106-146 as a strict prototype:
ETHUSDT cross-symbol relative-strength continuation ranked 8th, with 17 rows,
median total net +0.944238, median validation +0.121175, median adverse-month
return +0.015880, median adverse-day return -0.281538, median
drop-best-three-month return +0.515259, and median five losing months.

WPR106-128 was not selected by the prototype rule. Its strongest ETHUSDT
anchored-VWAP flow-impulse prototype ranked 62nd as a watch prototype, with
27 rows, median total net +0.880556, median validation +0.148335, median
adverse-month return +0.026815, median adverse-day return -0.353450, median
drop-best-three-month return +0.443309, and median eight losing months.

## May 2026 Row Benchmark

May rejected selected prototypes and they underperformed matched controls:

| Group | Rows | Positive | Negative | Flat | Best | Worst | Median | Mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Selected prototype rows | 100 | 16 | 84 | 0 | +0.047219 | -0.133646 | -0.017170 | -0.019284 |
| Matched controls | 100 | 16 | 79 | 5 | +0.065272 | -0.132690 | -0.015630 | -0.015713 |

Selected prototype row packet details:

- WPR106-146 was 4/4 positive, median +0.031309, mean +0.031309.
- WPR106-144 was 3/6 positive, but near flat with mean -0.000019.
- WPR106-135 was 2/12 positive, median -0.001306.
- WPR106-119 was 4/19 positive, median -0.031609.
- WPR106-139 was 0/10 positive, median -0.018909, mean -0.035769.
- WPR106-136 was 0/4 positive, all at -0.070820.

Matched controls included WPR106-128 rows and those controls were 3/4 positive
but still slightly negative on mean because one control row lost -0.029740.

## May 2026 Portfolio Benchmark

May rejected the fixed selected-prototype portfolios:

| Group | Rows | Positive | Negative | Flat | Best | Worst | Median | Mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Selected prototype portfolios | 39 | 0 | 39 | 0 | -0.000192 | -0.047466 | -0.018105 | -0.020730 |
| Matched-control portfolios | 33 | 3 | 30 | 0 | +0.002249 | -0.096210 | -0.002445 | -0.016344 |

Selected-prototype portfolios looked strong pre-May but failed May completely:
0 of 39 selected-prototype portfolios were May-positive. Matched-control
portfolios were also rejected, but their median was less negative.

## Decision

WPR106-164 rejects pre-May family/template prototype selection as
candidate-ready, portfolio-ready, or promotion-ready evidence. The selected
prototype rows underperformed matched controls in May, and selected-prototype
portfolios were uniformly negative.

The result narrows the research picture:

- WPR106-146 relative-strength trade-veto remains a narrow research-only
  pocket, not a broad family prototype. It needs direct controls and fresh
  pre-May-only construction before it can be trusted.
- WPR106-128 anchored VWAP remains a research-only clue, but its best
  prototype did not meet the stricter pre-May prototype selection path and
  appeared only through controls.
- WPR106-139 calendar/session, WPR106-136 KNN trade-veto, and WPR106-156
  complement exposure are further discouraged by this audit.

## Artifacts

- Runner:
  `data/research/wpr106_164_pre_may_family_prototype_transfer_controls/scripts/run_wpr106_164_pre_may_family_prototype_transfer_controls.py`
- Summary:
  `data/research/wpr106_164_pre_may_family_prototype_transfer_controls/wpr106_164_pre_may_family_prototype_transfer_controls_summary.json`
- Prototype ranking:
  `data/research/wpr106_164_pre_may_family_prototype_transfer_controls/pre_may/prototype_pre_may_ranking.parquet`
- Selected prototypes:
  `data/research/wpr106_164_pre_may_family_prototype_transfer_controls/pre_may/selected_pre_may_prototypes.parquet`
- Selected prototype rows:
  `data/research/wpr106_164_pre_may_family_prototype_transfer_controls/pre_may/selected_pre_may_prototype_rows.parquet`
- Matched controls:
  `data/research/wpr106_164_pre_may_family_prototype_transfer_controls/pre_may/matched_control_rows.parquet`
- May row benchmark:
  `data/research/wpr106_164_pre_may_family_prototype_transfer_controls/may_benchmark/selected_and_control_may_metrics.parquet`
- May portfolio benchmark:
  `data/research/wpr106_164_pre_may_family_prototype_transfer_controls/may_benchmark/selected_and_control_may_portfolio_metrics.parquet`

## Validation

Passed:

- `python -m compileall -q data/research/wpr106_164_pre_may_family_prototype_transfer_controls/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`

Contract result: 460 passed.
