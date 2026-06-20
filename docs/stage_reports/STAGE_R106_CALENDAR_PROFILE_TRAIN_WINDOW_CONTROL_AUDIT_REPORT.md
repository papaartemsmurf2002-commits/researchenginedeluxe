# Stage R106 WPR106-208 Calendar Profile Train-Window Control Audit Report

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Scope

WPR106-208 tests whether the WPR106-139 strict calendar/session rows remain
plausible when their calendar profiles are refit on alternate pre-May
subwindows. WPR106-139 fitted full pre-May bucket profiles and found active,
strict-looking rows, but all selected rows lost in May 2026. WPR106-140 and
WPR106-185 already rejected causal rolling and prior-month calendar variants.
This packet adds source-level train-window sensitivity controls over the fixed
WPR106-139 strict candidates.

Candidate templates, thresholds, session filters, volatility filters, flow
filters, bucket modes, and holds are fixed from WPR106-139. Only the profile
training window changes. Selection uses pre-May pseudo-OOS controls only; May
2026 is loaded after the fixed control set is selected.

## Implementation

The packet-local runner is:

- `data/research/wpr106_208_calendar_profile_train_window_control_audit/scripts/run_wpr106_208_calendar_profile_train_window_control_audit.py`

The runner imports the WPR106-139 source runner, rebuilds BTCUSDT and ETHUSDT
archive contexts, and reuses WPR106-139 completed-bar feature and accepted
trade accounting. It evaluates 17 fixed WPR106-139 strict rows under five
profile-fit policies:

- full pre-May fit, matching WPR106-139.
- 2024-only fit.
- 2025-only fit.
- 2024-through-2025 fit.
- recent 2025-H2 through 2026-April fit.

Primary pseudo-OOS selection windows are:

- 2025 through 2026-April for 2024-only fits.
- 2026 Jan-April for 2025-only and 2024-through-2025 fits.

Runtime was 20.70 seconds. The runner rebuilt 25 cached feature sets. CUDA was
not used and no speedup claim was made.

## Pre-May Results

The audit evaluates 510 non-May control-window rows across the fixed strict
candidate set. Among 51 primary pseudo-OOS rows:

- 36 are positive.
- 4 pass strict pseudo-OOS controls.
- 22 pass loose pseudo-OOS controls.

Selected fixed control set:

- 22 controls selected from pseudo-OOS pre-May behavior.
- 4 strict pseudo-OOS controls.
- 22 loose controls, including the strict rows because strict rows also satisfy
  loose criteria.
- Median selected pseudo-OOS return: +0.173659.
- Median selected pseudo-OOS losing months: 1.

Primary pseudo-OOS summary by train policy:

- `train_2024_2025_fit`: 17 rows, 14 positive, 2 strict, 14 loose, median
  return +0.206825.
- `train_2024_fit`: 17 rows, 11 positive, 1 strict, 2 loose, median return
  +0.187711.
- `train_2025_fit`: 17 rows, 11 positive, 1 strict, 6 loose, median return
  +0.022487.

The best pseudo-OOS selected row is `calendar-e4c182b11aad732f`, an ETHUSDT
`calendar_session_momentum` row fit on 2024 and evaluated over 2025 through
2026-April. It records +1.105674, 207 trades, 16 active months, 3 losing
months, annual losses 0/2/1 for 2024/2025/2026 Jan-Apr, max drawdown
-0.158025, 1.277778 trades per active day, and 4/4 cost-stress survival.

## May Benchmark

The fixed selected controls fail May:

- 1 positive selected control.
- 19 negative selected controls.
- 2 flat selected controls.
- Median selected May return: -0.064568.
- Best selected May return: +0.010172.
- Worst selected May return: -0.134535.

The only positive selected May control is BTCUSDT
`calendar-82239f45d0613096` with a 2024-only profile fit. It had only
+0.140099 over the 2025-through-2026-April pseudo-OOS window, six losing
months in 2025, and was selected as loose rather than strict. Its May result
is +0.010172 over four trades, too sparse to rescue the family.

The four strict pseudo-OOS controls all lose in May:

- `calendar-e4c182b11aad732f`, 2024-only fit: -0.047876.
- `calendar-4e3aa2d223cc912c`, 2024-2025 fit: -0.103482.
- `calendar-66bd6152873fc2b8`, 2024-2025 fit: -0.103482.
- `calendar-e4c182b11aad732f`, 2025-only fit: -0.122801.

Across all May train-window controls, full pre-May fit reproduces WPR106-139's
failure at 0 positive and 17 negative rows. Train-window changes improve the
positive count only slightly and do not create a stable benchmark pocket:

- `train_2024_fit`: 6 positive, 11 negative, median -0.014564.
- `train_2024_2025_fit`: 1 positive, 14 negative, 2 flat, median -0.047780.
- `train_2025_fit`: 2 positive, 15 negative, median -0.078083.
- `recent_2025h2_2026apr_fit`: 1 positive, 16 negative, median -0.050918.

## Interpretation

WPR106-208 rejects the WPR106-139 strict calendar/session pocket as
candidate-ready, portfolio-ready, paper/live-ready, or promotion-ready.

The source-level train-window controls show that the calendar rows are not
only a full-pre-May profile-fit artifact: several earlier-window profiles can
produce positive pseudo-OOS pre-May behavior. But that apparent repair still
does not transfer to May. The selected set's May distribution is decisively
negative, and the only selected positive May row is sparse and loose.

The evidence now strongly demotes the calendar/session strict pocket to a
time-bucket overfit diagnostic. Future calendar work should not defend fixed
weekday/hour profile rows. A future packet would need a different economic
driver, such as independently causal event context or non-calendar order-flow
state, before spending more compute on this family.

## Artifacts

- `data/research/wpr106_208_calendar_profile_train_window_control_audit/controls/source_artifact_index.parquet`
- `data/research/wpr106_208_calendar_profile_train_window_control_audit/controls/profile_train_policies.parquet`
- `data/research/wpr106_208_calendar_profile_train_window_control_audit/pre_may/profile_train_window_diagnostics.parquet`
- `data/research/wpr106_208_calendar_profile_train_window_control_audit/pre_may/calendar_train_window_control_metrics.parquet`
- `data/research/wpr106_208_calendar_profile_train_window_control_audit/pre_may/calendar_train_window_monthly_returns.parquet`
- `data/research/wpr106_208_calendar_profile_train_window_control_audit/pre_may/calendar_train_window_daily_returns.parquet`
- `data/research/wpr106_208_calendar_profile_train_window_control_audit/pre_may/selected_pre_may_train_window_controls.parquet`
- `data/research/wpr106_208_calendar_profile_train_window_control_audit/may_benchmark/calendar_train_window_may_benchmark_metrics.parquet`
- `data/research/wpr106_208_calendar_profile_train_window_control_audit/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_208_calendar_profile_train_window_control_audit/may_benchmark/calendar_train_window_may_monthly_returns.parquet`
- `data/research/wpr106_208_calendar_profile_train_window_control_audit/may_benchmark/calendar_train_window_may_daily_returns.parquet`
- `data/research/wpr106_208_calendar_profile_train_window_control_audit/selected_pre_may_may_control_comparison.parquet`
- `data/research/wpr106_208_calendar_profile_train_window_control_audit/calendar_train_window_control_trades.parquet`
- `data/research/wpr106_208_calendar_profile_train_window_control_audit/wpr106_208_calendar_profile_train_window_control_audit_summary.json`

## Research Boundary

All outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. No candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim was created.

## Validation

Passed final close validation:

```powershell
python -m compileall -q data\research\wpr106_208_calendar_profile_train_window_control_audit\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
