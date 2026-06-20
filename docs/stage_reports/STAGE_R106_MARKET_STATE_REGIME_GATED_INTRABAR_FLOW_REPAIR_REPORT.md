# Stage R106 Market-State Regime-Gated Intrabar Flow Repair Report

Date: 2026-06-12
Work packet: WPR106-171-market-state-regime-gated-intrabar-flow-repair
Status: broad regime-gate repair completed, no candidate-ready lead

## Scope

WPR106-171 continues the 2024-forward broad search after WPR106-170 rejected
the path-quality KNN event-veto formulation. It revisits the prior WPR106-153
intrabar order-flow family and tests whether independent completed-bar market
state gates can repair monthly stability without changing source entries,
exits, costs, or source overlap handling.

All gate thresholds, ranking, filtering, daily-cap choices, and selection use
only 2024-01-01 through 2026-04-30. May 2026 is replayed only after fixed
pre-May rows are selected. Because the WPR106-153 May benchmark has already
been inspected in prior work, May is not treated as a fresh discovery holdout
here; it remains a benchmark-only replay and is not used for tuning.

This packet is research-only and observe-only. It writes no candidate pack,
paper/live artifact, live configuration, sizing change, order path, CUDA
speedup claim, or promotion claim.

## Method

Inputs:

- WPR106-153 selected pre-May and May intrabar order-flow trade ledgers;
- WPR106-96 verified BTCUSDT/ETHUSDT 15m bars through May 2026;
- WPR106-96 BTCUSDT/ETHUSDT 1m aggTrade rows aggregated into completed 15m
  flow-pressure features.

The source WPR106-153 trade ledgers already include accepted trades, paid
round-trip costs, and source overlap handling. WPR106-171 does not recompute
fills or exits. It only applies fixed entry-time gates and then optional
accepted-trade daily caps of 1, 3, or 5.

State features are known by the completed signal bar and include:

- own-symbol 1/4/16/96-bar returns, 16/96-bar volatility, range, volume z-score;
- 16/64-bar aggTrade flow pressure;
- own-minus-peer relative returns and flow;
- common BTC trend and BTC flow state;
- UTC hour/session gates.

All quantile thresholds are derived from pre-May completed bars only.

Grid dimensions:

- source rows: 100 WPR106-153 selected rows;
- state gates: 22 fixed gates, including no gate, volatility, shock,
  range-compression/expansion, volume, flow-aligned/contra/quiet,
  trend-aligned/contra/flat, cross-strength, BTC-trend, Asia, and US;
- daily caps: 1, 3, and 5 accepted source trades per day.

Cost stress uses the existing source gross returns and round-trip costs at
1.0x, 1.25x, 1.5x, and 2.0x cost multipliers.

## Results

Full pre-May grid:

| Metric | Value |
| --- | ---: |
| Evaluated rows | 6,600 |
| Positive pre-May rows | 5,115 |
| Annual-target rows | 219 |
| Loose rows | 1,615 |
| Strict rows | 0 |

The fixed selected set contains only loose rows:

| Selected metric | Value |
| --- | ---: |
| Selected rows | 100 |
| Strict rows | 0 |
| Loose rows | 100 |
| Best pre-May net return | +1.059577 |
| Median pre-May net return | +0.781872 |
| Worst pre-May net return | +0.233917 |

The selection is duplicate-heavy because several source rows differ only by
WPR106-153 source cap parameters, and daily caps often do not change the
already overlap-filtered trade set.

The top stability-scored selected row is:

- candidate: `mktgate-b2dab01af4de0eb8`;
- source candidate: `intrabarof-1676b8748ca1ce46`;
- symbol: ETHUSDT;
- template: late-delta-flip fade;
- gate: `shock_q80`;
- daily cap: 1;
- pre-May trades: 161;
- active months: 20;
- losing months: 5;
- annual losses: 2024: 2, 2025: 2, 2026 Jan-Apr: 1;
- pre-May net return: +0.614123;
- max drawdown: -0.138568;
- best-month share: 0.208531;
- cost-stress survival: 4/4.

It is not strict because active-month coverage is too low for the strict bar.

Gate summary:

| Gate | Loose rows | Annual-target rows | Median net | Best net |
| --- | ---: | ---: | ---: | ---: |
| all | 250 | 0 | +0.365931 | +0.955683 |
| us_hours | 206 | 0 | +0.291327 | +0.955683 |
| range_expansion | 153 | 6 | +0.346229 | +0.983619 |
| shock_q80 | 142 | 7 | +0.311851 | +1.059577 |
| volume_high_q70 | 122 | 3 | +0.243054 | +0.725580 |
| flow_contra_q60 | 86 | 33 | +0.104828 | +0.514207 |
| high_vol_q70 | 60 | 27 | +0.266529 | +0.672087 |

## May Benchmark

May 2026 was benchmark-only after fixed pre-May selection:

| Metric | Value |
| --- | ---: |
| Selected rows benchmarked | 100 |
| May-positive rows | 46 |
| May-negative rows | 51 |
| May-flat rows | 3 |
| Best May return | +0.069661 |
| Worst May return | -0.057689 |
| Median May return | -0.001737 |

The strongest May-positive diagnostic pocket is ETHUSDT late-delta-flip fade
with `shock_q80` or `volume_high_q70` gates:

- best May row: `mktgate-749d40d90ab1237c`;
- source candidate: `intrabarof-ac2a730ba7b3f4a6`;
- gate: `shock_q80`;
- daily cap: 3;
- pre-May net return: +0.532151;
- pre-May active months: 21;
- pre-May losing months: 5;
- pre-May max drawdown: -0.245258;
- May trades: 6;
- May net return: +0.069661;
- May cost-stress survival: 4/4.

This is not candidate-ready evidence because May support is only a handful of
trades, the selected set median is still negative, no strict pre-May row
exists, and the May result is duplicate-heavy rather than broad transfer.

## Decision

WPR106-171 rejects the market-state regime-gated intrabar-flow repair as
candidate-ready, portfolio-ready, or promotion-ready evidence. The repair
improves pre-May row counts and finds a useful ETH shock/high-volume diagnostic
pocket, but it does not meet the strict month-to-month stability bar and does
not transfer strongly enough to May 2026.

Useful follow-up evidence: ETHUSDT late-delta-flip fade under shock/high-volume
completed-bar states deserves a later fresh non-May retest or a source-level
control packet if more post-May data is available. It should not be defended as
a candidate without fresh evidence, duplicate reduction, side/source controls,
and a broader month-stability proof.

## Artifacts

- Runner:
  `data/research/wpr106_171_market_state_regime_gated_intrabar_flow_repair/scripts/run_wpr106_171_market_state_regime_gated_intrabar_flow_repair.py`
- Summary:
  `data/research/wpr106_171_market_state_regime_gated_intrabar_flow_repair/wpr106_171_market_state_regime_gated_intrabar_flow_summary.json`
- Pre-May thresholds:
  `data/research/wpr106_171_market_state_regime_gated_intrabar_flow_repair/pre_may_state_thresholds.json`
- Ranking:
  `data/research/wpr106_171_market_state_regime_gated_intrabar_flow_repair/pre_may/market_state_gate_ranking.parquet`
- Top 2000:
  `data/research/wpr106_171_market_state_regime_gated_intrabar_flow_repair/pre_may/market_state_gate_top2000.csv`
- Monthly returns:
  `data/research/wpr106_171_market_state_regime_gated_intrabar_flow_repair/pre_may/market_state_gate_monthly_returns.parquet`
- Selected rows and trades:
  `data/research/wpr106_171_market_state_regime_gated_intrabar_flow_repair/pre_may/selected_pre_may.parquet`
  and
  `data/research/wpr106_171_market_state_regime_gated_intrabar_flow_repair/pre_may/selected_pre_may_trades.parquet`
- May benchmark metrics and trades:
  `data/research/wpr106_171_market_state_regime_gated_intrabar_flow_repair/may_benchmark/selected_may_benchmark_metrics.parquet`
  and
  `data/research/wpr106_171_market_state_regime_gated_intrabar_flow_repair/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

Passed:

- `python -m compileall -q data\research\wpr106_171_market_state_regime_gated_intrabar_flow_repair\scripts`
- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`

Contract result: 460 passed.
