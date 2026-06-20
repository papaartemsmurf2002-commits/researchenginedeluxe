# WPR106-107 Rolling Lorentzian KNN Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Revisit the Lorentzian/KNN family with a different, scoped implementation path
instead of rerunning prior rejected no-RSI matrix settings. This packet tests a
rolling causal nearest-neighbor classifier over 2024-forward BTCUSDT/ETHUSDT
public-archive context, using logically motivated price-path, wick, range,
session, and aggTrade-flow features. The search should determine whether
Lorentzian-space analog signals can produce active, cost-positive, month-stable
pre-May leads before May 2026 is used as a holdout benchmark.

## Scope

- Use WPR106-96 verified BTCUSDT/ETHUSDT 2024-01 through 2026-05 local public
  archive context.
- Optimize feature pack, distance metric, lookback, neighbor count, horizon,
  confidence threshold, side mode, session, and volatility/filter settings only
  on 2024-01-01 through 2026-04-30.
- Keep May 2026 fully out of feature choice, neighbor-logic choice, threshold
  calibration, ranking, filtering, and selection.
- Apply fixed pre-May KNN settings and thresholds unchanged to May 2026 only
  after a row is selected as a promising pre-May lead.
- Use rolling causal neighbor pools: for each signal row, neighbors must be
  older than the signal by at least the label horizon plus purge gap.
- Compare Lorentzian distance against Euclidean controls and no-KNN/simple
  score controls when practical inside the artifact runner.
- Allow active 1 to 5 trades per active day after one-position overlap handling.
- Measure explicit taker commission 0.0432% per side plus conservative
  slippage/spread allowance, monthly returns, annual losing-month counts,
  drawdown, active-rate density, overlap skips, and cost-stress survival.
- Keep every artifact research-only, observe-only, and promotion-ready false.

## Allowed paths

- `docs/work_packets/WPR106-107-rolling-lorentzian-knn-search.md`
- `docs/stage_reports/STAGE_R106_ROLLING_LORENTZIAN_KNN_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_107*/**`

## Out of scope

- No May 2026 tuning, score/threshold/feature/filter feedback, KNN parameter
  feedback, exit choice feedback, optimizer feedback, or cost tuning.
- No source package changes unless a small, scoped, testable blocker prevents
  artifact-only research.
- No candidate pack, paper/live artifact, order placement, position sizing,
  runtime-mode change, live configuration write, CUDA speedup claim, or
  promotion claim.
- No synthetic fallback data.
- No model fit, scaler, threshold, or neighbor pool that uses May labels, May
  scores, May quantiles, or May feature distributions.

## Exit evidence

- A deterministic WPR106-107 runner and pre-May search artifacts are written
  under `data/research/wpr106_107*/`.
- Pre-May selected rows, monthly returns, trades, and benchmark-only May rows
  are written separately when any promising pre-May row qualifies.
- The stage report records whether any row satisfies the target profile of
  roughly zero to two losing months per full pre-May year, whether active-rate
  behavior is acceptable, and whether May confirms or rejects fixed promising
  rows.
- Validation baseline is run or explicitly reported if blocked:
  `python -m compileall -q src/tradingbotsuite` and
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`.

## Closeout

Closed on 2026-06-11. The artifact-only runner evaluated 73,728 rolling KNN
rows over the WPR106-96 verified 2024-01 through 2026-05 BTCUSDT/ETHUSDT
public-archive context. Optimization, KNN parameter selection, feature-pack
choice, score-threshold calibration, ranking, filtering, and selection used
only 2024-01-01 through 2026-04-30. May was joined only after fixed pre-May
loose/strict rows were selected, and May KNN neighbor labels were frozen to
labels that completed before 2026-05-01.

The search found 1,270 positive pre-May rows and 27 loose pre-May rows, but
0 strict month-stability rows. All 1,270 positive rows landed inside the
intended 1-to-5 trades per active day band after overlap handling, and 1,269
positive rows were active in at least 24 months. The blocker was annual month
stability: zero positive rows met the full-year constraint of two or fewer
losing active months in both 2024 and 2025.

All 27 loose rows were ETHUSDT rows and were benchmarked in May after pre-May
selection. May results were 4 positive, 21 negative, and 2 flat. The top
pre-May row `rknn-59968119d9c264fb` was +0.829823 pre-May with 461 trades,
1.000 trades per active day, 8 losing months, annual losses of 2024: 2,
2025: 4, and 2026 Jan-Apr: 2, then benchmarked -0.026627 in May. May-positive
diagnostics were already rejected by pre-May annual stability.

The rolling Lorentzian/KNN family is rejected as currently configured. It is
useful diagnostic evidence that causal KNN analog rows can produce active,
cost-positive ETHUSDT pockets, but not the requested full-year month stability
or a candidate-ready lead. No May tuning, candidate pack, paper/live artifact,
order/sizing/runtime change, live configuration write, CUDA speedup claim, or
promotion claim exists.

Validation passed:

- `python -m compileall -q data/research/wpr106_107_rolling_lorentzian_knn_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` with 460 passed.
