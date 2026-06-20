# Stage R106 WPR106-148 Broad Behavior-Dedup Rolling Source Selector Report

Date: 2026-06-12
Owner: Codex Research Agent
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It does
not create a candidate pack, paper/live artifact, order-placement path, sizing
change, runtime-mode change, live configuration write, or promotion claim.

All selection, behavior de-duplication, rolling diagnostics, rankings, and
thresholds use only 2024-01-01 through 2026-04-30. May 2026 is benchmark-only
after the selected pre-May rows are fixed. CUDA was not used and no CUDA
speedup claim is made.

## Method

WPR106-148 starts from the WPR106-144 direct source and fixed-family benchmark
universe, then recomputes accepted-trade behavior hashes for every candidate
row over the pre-May window. Rows are de-duplicated by exact accepted pre-May
behavior before rolling diagnostics are attached.

The selector evaluates six anchored pre-May holdout windows:

- Train through 2024-09, hold out 2024 Q4.
- Train through 2024-12, hold out 2025 Q1.
- Train through 2025-03, hold out 2025 Q2.
- Train through 2025-06, hold out 2025 Q3.
- Train through 2025-09, hold out 2025 Q4.
- Train through 2025-12, hold out 2026 Jan-Apr.

The fixed May benchmark set is the top 80 robust pre-May rows after behavior
de-duplication and rolling holdout scoring.

## Results

- Input rows: 2,181 WPR106-144 source/family candidate rows.
- Exact source behavior de-duplication snapshot: 659 source rows to 518 source
  rows.
- Candidate accepted-trade behavior de-duplication: 1,219 unique pre-May
  behavior hashes.
- Pre-May screen after behavior de-duplication: 258 strict rows, 741 loose rows,
  444 rolling-candidate rows, and 134 robust rows.
- Fixed May benchmark set: 80 behavior-unique robust rows.
- Selected pre-May profile: median total net return +0.724021, median losing
  months 4, median rolling worst holdout +0.034321, median 1.239579 trades per
  active day.
- May 2026 benchmark: 7/80 positive rows, positive rate 8.75%, median
  -0.012930, mean -0.015425, return sum -1.233990, best +0.019375, worst
  -0.133646.
- May by entity: 7/69 individual-source rows positive; 0/11 fixed source-family
  portfolios positive.
- May by packet: WPR106-137 rows contain the only positive May rows; WPR106-139
  calendar/session rows are materially negative in May.

The strongest May-positive research pockets are still narrow and all remain
research-only:

- WPR106-137 `cross_symbol_relative_strength|multi_horizon_transition_breakout|microstructure_flow_agreement`
  on `ETHUSDT|ETHUSDT|BTCUSDT`: +0.019375 May.
- WPR106-137 `cross_symbol_relative_strength|volatility_quiet_trend_pullback|cross_symbol_flow_led_momentum`
  on `ETHUSDT|ETHUSDT|ETHUSDT`: +0.015157 May.
- WPR106-137 `cross_symbol_relative_strength|multi_horizon_trend_follow|volatility_quiet_trend_pullback`
  on `ETHUSDT|ETHUSDT|ETHUSDT`: +0.011182 May.
- WPR106-137 `cross_symbol_relative_strength|multi_horizon_trend_follow|microstructure_flow_agreement`
  on `ETHUSDT|ETHUSDT|BTCUSDT`: two selected rows positive in May, best
  +0.010928.

## Decision

WPR106-148 rejects the broad behavior-deduped rolling source selector as a
candidate-ready or portfolio-ready direction. The pre-May robustness controls
are stronger than WPR106-147, but the fixed May benchmark rejects the selected
set as a broad family: only 7 of 80 selected rows are positive, fixed
source-family portfolios are 0 of 11 positive, and the selected set has a
negative May median and negative aggregate.

The May-positive WPR106-137 pockets can seed future research-only probes, but
they should be treated as narrow variants requiring new controls rather than
as a validated broad source-selector lead. Useful next work should either
construct materially new feature/source families or add stronger pre-May
transfer controls before any May benchmark.

## Artifacts

- `data/research/wpr106_148_broad_behavior_dedup_rolling_source_selector/wpr106_148_broad_behavior_dedup_rolling_source_selector_summary.json`
- `data/research/wpr106_148_broad_behavior_dedup_rolling_source_selector/pre_may/scored_behavior_deduped_candidates.parquet`
- `data/research/wpr106_148_broad_behavior_dedup_rolling_source_selector/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_148_broad_behavior_dedup_rolling_source_selector/pre_may/rolling_pre_may_holdout_diagnostics.parquet`
- `data/research/wpr106_148_broad_behavior_dedup_rolling_source_selector/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_148_broad_behavior_dedup_rolling_source_selector/family_selector_summary.parquet`
- `data/research/wpr106_148_broad_behavior_dedup_rolling_source_selector/scripts/run_wpr106_148_broad_behavior_dedup_rolling_source_selector.py`

## Validation

Passed:

```powershell
python -m compileall -q data/research/wpr106_148_broad_behavior_dedup_rolling_source_selector/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Contracts result: 460 passed.
