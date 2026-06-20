# WPR106-115 Regime-Switch Intraday Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Test a fresh artifact-only intraday regime-switch family over the verified
WPR106-96 BTCUSDT/ETHUSDT 15m feature context. This packet should revisit
discarded transparent trend, range, volatility, session, flow, and perp-context
ideas with new causal feature combinations, filters, daily caps, overlap
handling, and primary-bar path exits. The purpose is not to defend the rejected
WPR106-113 ETH-heavy portfolio cluster, but to test whether direct entry logic
can produce month-to-month stable 2024-forward leads before May 2026 is
inspected.

## Scope

- Use WPR106-96 verified feature frames that cover 2024-01 through 2026-05:
  BTCUSDT price/trend/vol context and ETHUSDT price/perp/aggTrade-flow context.
- Use 2024-01-01 through 2026-04-30 for every feature, family, score, filter,
  threshold, side, exit, daily cap, rank, and selection decision.
- Keep May 2026 fully out of tuning and use it only as a benchmark holdout
  after fixed pre-May rows are selected.
- Evaluate causal regime-switch score families with completed 15m bars and
  next-bar entries:
  - trend continuation;
  - trend pullback;
  - range reversion;
  - volatility breakout and volatility fade;
  - flow absorption and flow follow using available aggTrade proxies;
  - ETH-only perp/funding/premium/flow pressure rows where provider-backed
    context exists.
- Test active entry rates up to roughly 1 to 5 trades per active day when
  costs, one-position overlap, max trades/day, and drawdown are measured.
- Test fixed-hold and primary-barrier exits using completed 15m OHLC paths,
  with conservative same-bar stop-first behavior when TP and SL are both hit.
- Rank by post-cost return, annual/month stability, rolling block stability,
  active-month/trade-count adequacy, drawdown, downside risk, cost stress, and
  best-month concentration rather than one large profitable window.
- Keep all outputs research-only, observe-only, and promotion-ready false.

## Allowed paths

- `docs/work_packets/WPR106-115-regime-switch-intraday-search.md`
- `docs/stage_reports/STAGE_R106_REGIME_SWITCH_INTRADAY_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_115*/**`

## Out of scope

- No May 2026 tuning, threshold feedback, filter feedback, exit feedback,
  rank feedback, source feedback, or cost feedback.
- No shared package, strategy registry, feature registry, backtest engine,
  optimizer, research-cycle, candidate-pack, live, runtime, or config changes
  unless a later packet explicitly scopes them.
- No candidate pack, paper/live artifact, live order placement, live runtime
  mode change, position sizing change, live configuration write, CUDA speedup
  claim, or promotion claim.
- No synthetic fallback data.
- No use of WPR106-113 selected portfolios, member sets, May labels, or May
  distributions to choose rows.

## Exit evidence

- A deterministic WPR106-115 runner and summary artifacts are written under
  `data/research/wpr106_115*/`.
- Pre-May rankings, monthly returns, daily returns, selected rows, selected
  trades, rolling block metrics, and cost-stress diagnostics are written
  separately from May benchmark artifacts.
- If any promising pre-May rows exist, May 2026 benchmark artifacts are written
  only for the fixed selected rows.
- The stage report records whether any row satisfies the target profile of
  roughly zero to two losing months per full pre-May year, whether selected
  rows remain stable across rolling blocks, and whether May confirms or rejects
  fixed pre-May selection.
- Validation baseline is run or explicitly reported if blocked:
  `python -m compileall -q src/tradingbotsuite` and
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`.

## Closeout

Closed 2026-06-11. The deterministic artifact-only runner was written under
`data/research/wpr106_115_regime_switch_intraday_search/scripts/` and generated
pre-May and May benchmark artifacts under
`data/research/wpr106_115_regime_switch_intraday_search/`.

The sweep evaluated 45,360 causal score/filter/side/exit rows over the
WPR106-96 2024-01 through 2026-05 BTCUSDT and ETHUSDT feature frames. Every
ranking and selection decision used only 2024-01-01 through 2026-04-30. The
runner skipped ETH-only perp/funding/OI pressure rows because those context
z-score columns were fully missing in the available feature frame, and used
provider-backed price, trend, volatility, session, and aggTrade-flow proxy
features instead.

Results:

- Strict pre-May rows: 0.
- Loose pre-May rows: 31.
- Positive pre-May rows: 2,512.
- Positive annual-target rows with no more than 2/2/1 losing months in
  2024/2025/2026 Jan-Apr: 291, but all are too sparse for the active strategy
  target, with maximum 18 trades and maximum 14 active months.
- Selected rows: 25 loose rows across 8 unique symbol/family/template groups.
- May 2026 benchmark after fixed pre-May selection: 11 May-positive rows,
  14 May-negative rows, and 0 flat rows.

The top selected pre-May row is `rswitch-0a860a40b30d0c4f`, an ETHUSDT US
trend-regime volatility-breakout-follow row with a 32-bar fixed exit. It
returns +0.862332 pre-May after costs with 213 trades, 212 active days,
1.005 trades per active day, 28 active months, 8 losing months, annual losses
of 2024: 3, 2025: 3, and 2026 Jan-Apr: 2, max drawdown -0.159763, full
cost-stress survival, and one losing rolling block. It benchmarks -0.030540 in
May.

The best selected May row is `rswitch-a87c7ee557c3c55c`, an ETHUSDT choppy
volatility-breakout-fade long row with a 32-bar fixed exit. It benchmarks
+0.047973 in May, but was already rejected by pre-May annual stability with
7 losing months and 2025: 4 losing months.

Conclusion: the tested regime-switch intraday family finds active, costed,
post-cost positive diagnostics, including some May-positive selected rows, but
no strict month-stable lead. Rows that meet the annual losing-month target are
too sparse to satisfy the active strategy profile, and active loose rows fail
the target with 7 to 10 losing months. No candidate pack, paper/live artifact,
order/sizing/runtime change, live config write, CUDA speedup claim, or
promotion claim exists.

The full runner wrote complete artifacts and summary files. The PowerShell
wrapper command used for the full sweep exceeded the 30-minute tool timeout
while flushing output after artifact files were present; subsequent artifact
audits verified the summary, rankings, selections, and May benchmark files.

Validation passed:

```powershell
python -m compileall -q data/research/wpr106_115_regime_switch_intraday_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Contracts reported 460 passed.
