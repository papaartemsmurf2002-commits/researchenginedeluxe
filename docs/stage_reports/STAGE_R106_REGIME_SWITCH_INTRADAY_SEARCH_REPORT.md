# Stage R106 WPR106-115 Regime-Switch Intraday Search Report

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Boundary

WPR106-115 is research-only, observe-only, and promotion-ready false. It is an
artifact-only runner under `data/research/wpr106_115_regime_switch_intraday_search/`
and does not change shared package code, strategy registries, feature
registries, backtest engines, candidate-pack logic, live configuration, runtime
mode, or sizing behavior.

Every feature, score, threshold, filter, side, exit, daily cap, rank, and
selection decision uses only 2024-01-01 through 2026-04-30. May 2026 is used
only as a benchmark holdout after fixed pre-May selection.

## Method

The runner is:

`data/research/wpr106_115_regime_switch_intraday_search/scripts/run_wpr106_115_regime_switch_intraday_search.py`

Inputs are the WPR106-96 verified feature frames:

- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/features/btcusdt_features_price_trend_vol_2024_01_to_2026_05.parquet`
- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/features/ethusdt_features_price_perp_aggflow_no_wt_2024_01_to_2026_05.parquet`

The runner evaluates causal score families over completed 15m bars with
next-bar entries:

- trend continuation;
- trend pullback;
- range reversion;
- volatility breakout follow;
- volatility breakout fade;
- flow follow;
- flow absorption.

ETH-only perp/funding/OI pressure rows were intentionally skipped because the
available ETH feature frame has fully missing `perp_premium_z_7d`,
`perp_funding_z_7d`, and `oi_delta_z_7d` columns. The run therefore uses
provider-backed price, trend, volatility, session, and aggTrade-flow proxy
features only.

The grid covers sessions, regimes, side modes, raw signal-rate targets, max
trades/day caps, fixed 15m-bar exits, and primary-barrier exits. Costs use the
same local convention as recent packets: 0.0432% taker fee plus 0.0150%
slippage/spread per side. One-position overlap and daily trade caps are
enforced before returns are counted. Barrier exits use completed primary-bar
OHLC and conservative same-bar stop-first behavior.

## Artifacts

Root:

`data/research/wpr106_115_regime_switch_intraday_search/`

Key pre-May artifacts:

- `pre_may/regime_switch_ranking.parquet`
- `pre_may/regime_switch_top2000.csv`
- `pre_may/regime_switch_monthly_returns.parquet`
- `pre_may/regime_switch_daily_returns.parquet`
- `pre_may/selected_pre_may.parquet`
- `pre_may/selected_pre_may_replay_metrics.parquet`
- `pre_may/selected_pre_may_trades.parquet`
- `pre_may/selected_pre_may_monthly_returns.parquet`
- `pre_may/selected_pre_may_daily_returns.parquet`

Key May benchmark artifacts:

- `may_benchmark/selected_may_benchmark_metrics.parquet`
- `may_benchmark/selected_may_benchmark_trades.parquet`
- `may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `may_benchmark/selected_may_benchmark_daily_returns.parquet`

Summary:

- `wpr106_115_regime_switch_intraday_summary.json`

## Results

Rows evaluated: 45,360.

Pre-May screen:

- Strict pre-May rows: 0.
- Loose pre-May rows: 31.
- Positive pre-May rows: 2,512.
- Positive annual-target rows with no more than 2/2/1 losing months in
  2024/2025/2026 Jan-Apr: 291.
- Positive annual-target rows with at least 40 trades and at least 10 active
  months: 0.
- Maximum trade count among positive annual-target rows: 18.
- Maximum active months among positive annual-target rows: 14.

Selected set:

- Selected rows: 25 loose rows.
- Unique selected symbol/family/template groups: 8.
- Selected pre-May losing months: min 7, median 9, max 10.
- Selected rows satisfying the annual target: 0.

Top selected pre-May row:

- Candidate: `rswitch-0a860a40b30d0c4f`.
- Symbol/family/template: ETHUSDT volatility `vol_breakout_follow`.
- Filters: US session, trend regime, both sides.
- Exit: 32-bar fixed hold.
- Pre-May return: +0.862332 after costs.
- Trades: 213.
- Active days: 212.
- Trades per active day: 1.005.
- Active months: 28.
- Losing months: 8.
- Annual losses: 2024: 3, 2025: 3, 2026 Jan-Apr: 2.
- Max drawdown: -0.159763.
- Cost-stress survival: 1.0.
- Rolling blocks: one losing block, minimum block -0.093171.

May benchmark after fixed pre-May selection:

- May-positive selected rows: 11.
- May-negative selected rows: 14.
- May-flat selected rows: 0.
- Best selected May return: +0.047973
  (`rswitch-a87c7ee557c3c55c`).
- Worst selected May return: -0.030540
  (`rswitch-0a860a40b30d0c4f` and equivalent daily-cap variants).

The best selected May row is an ETHUSDT choppy volatility-breakout-fade long
row with a 32-bar fixed exit. It was already rejected by pre-May annual
stability: 7 losing pre-May months and 2025: 4 losing months.

## Interpretation

This packet gives the regime-switch intraday family a fair active-rate search:
1 to 5 raw signals/day are allowed, overlap is handled, max trades/day is
explicit, costs and cost stress are applied, and both fixed and primary-barrier
exits are tested. The family produces many post-cost positive diagnostics and
some selected rows that are May-positive after fixed pre-May selection.

It still does not produce a candidate-ready lead. No row is strict. Active
loose rows fail the target month-to-month stability profile with 7 to 10 losing
months. Rows that satisfy the annual losing-month target are too sparse for the
requested active strategy profile, with no qualifying row reaching 40 trades or
10 active months.

The useful follow-up is not to promote these rows. A later packet could mine
the May-positive but pre-May-rejected volatility-fade and BTC range-reversion
diagnostics for new causal filters, but May outcomes from this packet must not
be used to tune those filters. Any such follow-up must define filters from
pre-May-only evidence or from a new pre-May-only hypothesis.

No candidate pack, paper/live artifact, order placement, sizing change,
runtime-mode change, live configuration write, CUDA speedup claim, or promotion
claim exists.

## Compute Note

The full runner wrote complete artifacts and the summary JSON. The PowerShell
wrapper command used for the full sweep exceeded the 30-minute tool timeout
while flushing output after artifact files were present; no Python process was
left running, and a subsequent artifact audit verified the rankings,
selections, and May benchmark files. No CUDA path was used or claimed.

## Validation

Passed:

```powershell
python -m compileall -q data/research/wpr106_115_regime_switch_intraday_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Contracts reported 460 passed.
