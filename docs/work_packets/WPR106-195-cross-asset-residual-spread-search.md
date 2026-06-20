# WPR106-195 Cross-Asset Residual Spread Search

Status: closed
Owner: Codex Research Agent
Date: 2026-06-13

## Objective

Continue the 2024-forward broad search after WPR106-194 rejected intrabar
flow-burst single-leg entries. This packet tests a different source family:
BTC/ETH dollar-neutral relative-value spread entries using causal rolling
price residuals, cross-symbol flow divergence, volatility state, and session
filters.

The purpose is to test whether pair-style relative-value behavior can improve
month-to-month stability versus the recent single-leg families while still
allowing normal active rates such as 1 to 5 entries per day.

This is an artifact-only research packet, not a candidate-promotion packet.

## Scope

Selection/tuning window:

- 2024-01-01 through 2026-04-30 UTC.

Benchmark-only window:

- May 2026, replayed only after fixed pre-May row selection.

Inputs:

- WPR106-96 BTCUSDT/ETHUSDT 15m OHLCV and aggTrade-flow context.
- WPR106-170 helper cost model, period masks, and metric accounting.

Search family:

- equal-notional two-leg BTC/ETH pair trades;
- causal completed-bar rolling log-price residuals and residual z-scores;
- residual reversion, residual breakout/trend, flow-divergence reversion, and
  volatility-adjusted spread templates;
- target symbol, side mode, session, hold, threshold, and daily-cap variants;
- overlap blocking across the pair using a single active pair position;
- WPR106 embedded round-trip cost for the pair notional;
- pre-May-only ranking by annual losing-month limits, drawdown, downside risk,
  best-month concentration, cost-stress survival, active-rate behavior, and
  recent activity;
- May replay of fixed selected rows only.

May must not be used for feature choice, threshold choice, side choice, session
choice, hold choice, cap choice, row ranking, or tie-breaking. May is
benchmark-only after fixed pre-May selection.

## Allowed Paths

- `docs/work_packets/WPR106-195-cross-asset-residual-spread-search.md`
- `docs/stage_reports/STAGE_R106_CROSS_ASSET_RESIDUAL_SPREAD_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_195_cross_asset_residual_spread_search/**`

## Plan

1. Load aligned WPR106-96 BTCUSDT/ETHUSDT contexts through WPR106-170 helpers.
2. Build causal completed-bar residual, spread, flow-divergence, volatility,
   and session features.
3. Generate equal-notional pair trade labels for fixed holding windows.
4. Calibrate score thresholds on pre-May only for target active rates.
5. Evaluate pair entries with overlap blocking and embedded costs.
6. Select fixed rows from pre-May diagnostics only.
7. Replay selected rows on May 2026.
8. Write ranking, monthly/daily/trade artifacts, summary, report, ledger
   update, and validation notes.

## Research Boundary

All outputs remain:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`

This packet must not create a candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim.

## Validation

Passed at close:

```powershell
python -m compileall -q data\research\wpr106_195_cross_asset_residual_spread_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.

## Exit Evidence

WPR106-195 evaluated 8,640 equal-notional BTC/ETH pair-spread rows. All
thresholds and selection used 2024-01-01 through 2026-04-30; May 2026 was
benchmark-only after fixed pre-May selection.

The pre-May screen found 564 positive rows, 52 annual-target rows, zero loose
rows, and zero strict rows. The annual-target rows were sparse and stale:
median trade counts were 10 to 15 trades depending on template, and none
passed latest-four-month floors of at least three active months and at least
20 trades.

The fixed selected set contained 15 fallback `positive_recent_stability` rows:
8 BTCUSDT-target rows and 7 ETHUSDT-target rows. Selected pre-May replay was
15 positive rows, zero negative rows, median +0.104935, active mean +0.122760,
best +0.192660, and worst +0.058794. Drawdowns were lower than recent
single-leg pockets, but May rejected every selected row: 0 positive rows,
15 negative rows, median -0.012385, active mean -0.016748, best -0.002851,
and worst -0.030679.

WPR106-195 therefore rejects the cross-asset residual spread search as
candidate-ready, portfolio-ready, or promotion-ready. It preserves the
diagnostic that dollar-neutral residual spreads reduce drawdown and can create
annual-target sparse pockets, but the active selected rows did not transfer to
May and the annual-target pockets were too sparse/recently inactive.
