# Stage R106 Monthly Rotation Lead Controls Report

Date: 2026-06-12
Packet: WPR106-142
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

The tested rule was fixed from WPR106-141 pre-May evidence:
`monthrot-ed7358029b345be5`, with 6-month lookback, 5 members, max 1 accepted
trade/day, stable-mean scoring, no diversity limit, and max pair correlation
0.85. Control definitions used only pre-May artifacts and WPR106-141 selected
evidence. May 2026 was replayed only after each fixed control definition was
applied.

## Method

The runner
`data/research/wpr106_142_monthly_rotation_lead_controls/scripts/run_wpr106_142_monthly_rotation_lead_controls.py`
reuses the WPR106-141 artifact-local replay helpers without changing shared
package code. It rebuilds the WPR106-141 source universe, monthly source-return
matrix, pre-May trades, and May trades, then reruns the fixed lead rule under
38 controls:

- baseline replay;
- exact source-trade behavior deduplication;
- calendar-only and no-calendar concentration controls;
- removal of each May-selected source;
- removal of each packet used by the lead across pre-May member choices;
- removal of each family used by the lead across pre-May member choices;
- five diagnostic-only negative controls using permuted source histories,
  shuffled source-month histories, or reversed month order.

Negative controls are not valid strategies. They are used only to see whether
distorted monthly evidence can mimic the lead.

## Results

Deduplication:

- Source rows before dedup: 659.
- Exact behavior hashes: 518.
- Duplicate behavior groups: 132.
- Rows removed by exact behavior dedup: 141.
- Lead unique pre-May members: 54.
- Lead unique May members: 5.
- Exact behavior dedup did not change the lead's pre-May or May result:
  pre-May +0.359543, 3 losing months, May +0.008070.

Control summary:

- Evaluated controls: 38.
- Non-diagnostic controls: 33.
- Diagnostic negative controls: 5.
- Non-diagnostic controls that remained pre-May strict: 20.
- Non-diagnostic controls with positive May: 29.
- Non-diagnostic controls that were both pre-May strict and May-positive: 16.
- Median non-diagnostic May return: +0.008070.
- Best non-diagnostic May return: +0.017640.
- Worst non-diagnostic May return: -0.007396.
- Diagnostic negative controls with positive May: 1 of 5.
- Best diagnostic negative-control May return: +0.001073.

The original baseline remained:

- Pre-May trades: 573.
- Active months: 25.
- Losing months: 3.
- Annual losses: 2024: 1, 2025: 2, 2026 Jan-Apr: 0.
- Pre-May net return: +0.359543.
- Max drawdown: -0.046434.
- Cost-stress survival: 4/4.
- May trades: 26.
- May net return: +0.008070.
- May max drawdown: -0.006925.

Important non-diagnostic failures:

- Dropping May-selected WPR106-133 `leadlag-18708dffa1413dce` kept pre-May
  strictness but made May negative at -0.007396.
- Dropping packet WPR106-133 kept pre-May strictness but made May negative at
  -0.007396.
- Dropping family `cross_symbol_relative_strength` kept pre-May strictness but
  made May negative at -0.007396.
- Dropping WPR106-139 made May slightly positive at +0.000413 but broke
  pre-May strictness with 7 losing months.
- `no_calendar_like` made May positive at +0.001703 but failed pre-May
  strictness with 10 losing months.

Important non-diagnostic survivors:

- Exact behavior dedup remained strict and May-positive.
- Dropping WPR106-140 remained strict and May-positive at +0.007719.
- Dropping WPR106-131 remained strict and May-positive at +0.008070.
- Dropping May-selected WPR106-134 `microstate-3f8caf061556b8a2` improved May
  to +0.017640 while remaining strict.
- Dropping family `microstructure_return_streak` also improved May to
  +0.017640 while remaining strict.

Negative controls:

- `negative_permute_source_history_seed7` was not pre-May strict, but it was
  May-positive at +0.001073.
- The other four negative controls were May-negative, ranging from -0.001555
  to -0.015332.

## Decision

`monthrot-ed7358029b345be5` remains a research-only lead but is not
candidate-ready. The exact behavior dedup result and many surviving ablations
show that the lead is not just a duplicate-row artifact. The control failures
show that it is still fragile: May depends materially on WPR106-133
cross-symbol relative-strength evidence, WPR106-139 calendar/session evidence
helps keep pre-May strictness, and one permuted-history negative control can
still produce a positive May.

The next useful follow-up is not a candidate-pack attempt. It should either:

- build a stricter version of the monthly rotation that requires packet/family
  diversity and cross-symbol-relative-strength robustness at selection time; or
- reject the family if shifted/shuffled controls and additional holdout months
  can keep producing comparable May-positive behavior.

## Artifacts

- `data/research/wpr106_142_monthly_rotation_lead_controls/wpr106_142_monthly_rotation_lead_controls_summary.json`
- `data/research/wpr106_142_monthly_rotation_lead_controls/control_metrics.parquet`
- `data/research/wpr106_142_monthly_rotation_lead_controls/control_metrics.csv`
- `data/research/wpr106_142_monthly_rotation_lead_controls/dedup_summary.json`
- `data/research/wpr106_142_monthly_rotation_lead_controls/source_load_metadata.json`
- `data/research/wpr106_142_monthly_rotation_lead_controls/pre_may/control_monthly_returns.parquet`
- `data/research/wpr106_142_monthly_rotation_lead_controls/pre_may/control_member_choices.parquet`
- `data/research/wpr106_142_monthly_rotation_lead_controls/pre_may/control_trades.parquet`
- `data/research/wpr106_142_monthly_rotation_lead_controls/may_benchmark/control_monthly_returns.parquet`
- `data/research/wpr106_142_monthly_rotation_lead_controls/may_benchmark/control_member_choices.parquet`
- `data/research/wpr106_142_monthly_rotation_lead_controls/may_benchmark/control_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_142_monthly_rotation_lead_controls/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
