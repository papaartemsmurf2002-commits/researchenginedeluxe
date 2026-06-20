# Stage R106 May 2026 Portfolio Holdout Benchmark Report

Date: 2026-06-11
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR106-96-may-2026-portfolio-holdout-benchmark.md`

## Scope

WPR106-96 resolved the BTCUSDT May 2026 archive dependency for the WPR106-95
pre-May portfolio-combination leads and benchmarked the preselected rank-1
combination, `combo-d9edcc252c323b03`, on May 2026 without May tuning or
selection feedback.

## Intake

BTCUSDT May 2026 Binance Vision monthly archives were added under the local
public-archive cache for 15m klines, 1m klines, and aggTrades, with checksum
sidecars and verified SHA-256 hashes:

- 15m kline: `sha256:1c0a865f62ddca9890f5d7bbe901b7261a3818785594d960f5fce36ee7ce81f5`
- 1m kline: `sha256:d91548e94220d5211bb32447cc4b604ee266d145f2092edc5ec613328cbbc20a`
- aggTrades: `sha256:c9c9db1a85d5ec2761b223d71aa6090d2093d4fe3237ec3f9afda02361aa9153`

ETHUSDT May 2026 files from WPR106-93 were reused and re-verified. Both
symbols have 2,976 May 15m bars, 44,640 May 1m bars, no kline gaps, no kline
duplicates, completed-bar close-time checks passing, and 44,640 aggregated
1-minute aggTrade rows. Raw aggTrade rows were 33,660,928 for BTCUSDT and
27,537,845 for ETHUSDT.

Primary manifest:
`data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/intake/wpr106_96_may_archive_intake_manifest.json`.

## Method

The benchmark used the WPR106-95 rank-1 sleeve membership and exact frozen
strategy parameters. May 2026 was not used for parameter search, feature
choice, threshold choice, selection, ranking, or optimizer feedback.

For each sleeve, the runner built feature context over 2024-01-01 through
2026-05-31 by appending May archive rows to the WPR106-85 pre-May fixture
packs. It then ran each sleeve over the full context and filtered trades by
May entry time. This preserves single-sleeve spacing, cooldown, and no-overlap
state across the April-to-May boundary while keeping portfolio accounting
matched to WPR106-95: sum member trade `net_return / sleeve_count` by entry
month.

## Results

Rank-1 `combo-d9edcc252c323b03` May 2026 benchmark:

- Portfolio return: +0.026603 equal-sleeve net return
- Member raw net-return sum: +0.106414
- Trades: 25
- Signals: 120
- Active days: 20
- Trades per active day: 1.250
- Overlap-day share: 0.250
- Positive days: 8
- Losing days: 12
- Max positive-day profit share: 0.262308

Sleeve details:

| Sleeve | May trades | May net return | Expectancy | Hit rate |
| --- | ---: | ---: | ---: | ---: |
| WPR106-94 BTC `c66b21e80bf2` | 9 | +0.057419 | +0.006380 | 0.555556 |
| WPR106-91 BTC `ea9b0ade9515` | 10 | +0.057029 | +0.005703 | 0.400000 |
| WPR106-90 ETH `335840e95fb1` | 1 | -0.020243 | -0.020243 | 0.000000 |
| WPR106-94 BTC `2ad619dad064` | 5 | +0.012209 | +0.002442 | 0.200000 |

Daily evidence:
`data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/may_only/combo-d9edcc252c323b03_may_2026_daily_returns.csv`.

## Interpretation

May did not reject the rank-1 WPR106-95 diagnostic portfolio lead, but it also
does not make it candidate-ready. The result is modest and uneven: the month is
positive overall, but daily stability is weak with 12 losing days out of 20
active days, and the ETH sparse sleeve lost on its single May trade. The lead
remains research-only, observe-only, and promotion-ready false.

## Boundary

No strategy, feature, research-cycle, live-boundary, operator UI, candidate
pack, paper/live artifact, order placement, position sizing, runtime mode, live
configuration, CUDA speedup claim, or promotion claim was changed or created.

## Validation

Passed:

- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` with 460 passed
