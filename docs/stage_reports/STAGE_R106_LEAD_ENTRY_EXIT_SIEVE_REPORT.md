# Stage R106 Lead Entry Exit Sieve Report

Date: 2026-06-07

Work packet: `docs/work_packets/WPR106-72-lead-entry-exit-sieve.md`

## Boundary

This packet stayed research-only, observe-only, and promotion-disabled. No
candidate pack, live or paper runtime setting, order adapter, sizing policy, or
promotion artifact was changed. The latest-window context fixtures used here
are diagnostic screens only and are not candidate-ready evidence.

## External And Sidecar Checks

External checks were refreshed against official documentation:

- Binance USD-M klines and premium-index klines are keyed by open time:
  https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Kline-Candlestick-Data
  and
  https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Premium-Index-Kline-Data
- Binance funding history is ordered historical funding data, and mark-price
  payloads expose `lastFundingRate`:
  https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History
  and
  https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Mark-Price
- Binance open-interest statistics are limited to latest-month access, matching
  the diagnostic-only scope of these context fixtures:
  https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Open-Interest-Statistics
- scikit-learn documents ordered time-series splitting and a `gap` parameter,
  supporting the branch purge/embargo validation posture:
  https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html
- scikit-learn nearest-neighbor docs reinforce that KNN cost grows with
  neighbor count, dimensionality, metric, and backend, supporting the decision
  not to spend large compute on dense KNN replay yet:
  https://scikit-learn.org/stable/modules/neighbors.html

Sidecar audits found no P0/P1 math issue in the tested winning paths. Strategy
sign conventions are coherent for trend following, volatility breakout,
funding-crowding fade, perp-basis convergence, and OI-flow breakout. Exit
long/short signs are coherent for fixed, runner, trailing, max-MAE, and
funding-aware exits. Two P2 interpretation caveats were added to
`ISSUE-R106-020`: `volatility_scaled_barrier` is currently a static close
barrier in this primary-bar path, and funding-aware exits trigger from path
funding context while realized funding-cost accounting remains entry-rate
based.

## Configs And Runtime

Configs:

- `configs/research/fast_lead_exit_sieve_btcusdt_r106_v1.json`
- `configs/research/fast_lead_exit_sieve_ethusdt_r106_v1.json`

Outputs:

- `data/research/historical_cycles/fast_lead_exit_sieve_btcusdt_r106_v1`
- `data/research/historical_cycles/fast_lead_exit_sieve_ethusdt_r106_v1`

The configs use explicit optimizer search spaces to pin the strongest
WPR106-71 entry settings and compare a compact exit set. BTC expanded to 40
ranked rows with injected baselines and finished in 26.1 seconds. ETH expanded
to 28 ranked rows with injected baselines and finished in 21.1 seconds.

## Results

BTC summary:

- 40 ranked rows, 10 positive rows, 727 total trades, 0 blocked rows.
- Best row: `volatility_breakout_v1`, `features_price_trend_vol`, 72h,
  `simple_runner_v1` with `activation_pct: 0.008`, `runner_gap_pct: 0.004`,
  entry params `atr_percentile_threshold: 0.25`, `shock_threshold: 0.7`,
  `spacing_bars: 8`.
- Best BTC row metrics: 24 trades, net 0.177178, expectancy 0.006868, profit
  factor 6.398171.
- Same entry comparison: fixed hold net 0.052648; base simple runner
  0.140613; slower-activation simple runner 0.177178; trailing 0.101481;
  tight simple runner -0.037362; hard stop -0.021346; static barrier
  -0.089079.
- Best horizon remained 72h. The 24h volatility-breakout simple-runner retest
  was only 0.018494 net.
- Strict 72h volatility breakout
  `atr_percentile_threshold: 0.45`, `shock_threshold: 1.3`,
  `spacing_bars: 18` stayed better under fixed hold (0.070124) than runner
  variants.

ETH summary:

- 28 ranked rows, 13 positive rows, 604 total trades, 0 blocked rows.
- Best row: `trend_following_v1`, `features_price_trend_vol`, 24h,
  `simple_runner_v1` with `activation_pct: 0.005`, `runner_gap_pct: 0.004`,
  entry params `slope_threshold: 0.12`, `max_choppiness: 58.0`,
  `funding_penalty_threshold: 0.00025`, `spacing_bars: 12`.
- Best ETH row metrics: 57 trades, net 0.313310, expectancy 0.004892, profit
  factor 2.703250.
- Same 24h trend entry comparison: fixed hold -0.167727; base simple runner
  0.313310; trailing 0.167868; slower simple runner 0.044040; tight simple
  runner 0.012458; static barrier -0.263005.
- 72h trend remained strong: simple runner 0.216966 and trailing 0.191979
  versus fixed hold -0.039747.
- ETH funding-crowding fade remained useful but secondary: 72h fixed hold
  0.110259, funding-aware exit 0.104650; 24h fixed hold 0.081534.

## Decisions

- BTC lead for larger durable validation: `volatility_breakout_v1`, 72h,
  loose entry params, compare fixed hold, base simple runner, and slower
  `0.008/0.004` simple runner. The slower runner is the best latest-window BTC
  exit result so far, but it still needs durable multi-window evidence.
- ETH lead for larger durable validation: `trend_following_v1`, 24h and 72h,
  base `0.005/0.004` simple runner and trailing-after-profit. ETH did not
  benefit from the tighter or slower simple-runner variants.
- Context strategies should stay secondary until durable perp-context evidence
  exists. ETH funding-crowding is positive, but funding-aware exits did not
  beat fixed hold on the same entry and carry the path-funding accounting P2
  caveat.
- Do not use `volatility_scaled_barrier` as evidence of a true volatility-aware
  exit until the P2 naming/semantics follow-up is resolved.
- Do not spend large compute on KNN yet. The useful next KNN work is a sparse
  event selector or cooldown/event-spacing layer, not another dense replay.

## Validation

- JSON parse passed for both new configs.
- `HistoricalResearchCycleSpec.from_path` passed for both configs.
- Candidate expansion check passed: BTC 40 rows with baselines, ETH 28 rows
  with baselines.
- Both cycles completed under the 1h fast-loop limit: BTC 26.1 seconds, ETH
  21.1 seconds.
- Candidate gate reports wrote 0 pack-eligible and 0 promotion-ready rows for
  both symbols, as expected for latest-window diagnostic evidence.
- `python -m compileall -q src/tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed with
  443 tests.
- `git diff --check` returned no whitespace errors; PowerShell reported only
  inherited CRLF warnings from the dirty worktree.

## Next Phase

Run a durable validation-focused packet for the two leads above. Keep trial
count small by using explicit search spaces first; only expand around a lead if
durable multi-window evidence keeps positive expectancy and beats fixed-hold
and transparent baseline comparators.
