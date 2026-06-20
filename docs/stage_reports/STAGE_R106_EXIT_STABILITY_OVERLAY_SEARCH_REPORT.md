# Stage R106 Exit Stability Overlay Search Report

Date: 2026-06-11
Work packet: `docs/work_packets/WPR106-88-exit-stability-overlay-search.md`
Owner: Codex Research Agent

## Decision

WPR106-88 is closed as another fail-closed 2024-forward pre-May research
screen. Exit overlays improved some sparse/event rows, but no BTCUSDT or
ETHUSDT row met the month-to-month stability target. No May 2026 holdout was
run because there is no promising pre-May lead, and local May 2026 archive data
remains unavailable under `ISSUE-R106-025`.

No candidate pack, paper/live artifact, order placement, sizing change, runtime
mode change, live configuration write, CUDA speedup claim, or promotion-ready
claim exists.

## Scope

- Tuning window: 2024-01-01 through 2026-04-30.
- May 2026 usage: excluded from tuning, ranking, optimizer feedback, and
  selection.
- Symbols: BTCUSDT and ETHUSDT.
- Evidence source: WPR106-85 exact-window archive-backed durable fixture packs.
- Search surface: all non-no-trade strategy rows, including sparse/event
  research candidates and transparent trend, range, and volatility controls.
- Exit policies: fixed holding, simple runner, trailing after profit,
  max-MAE stop, primary-bar volatility-scaled barrier, and lower-timeframe
  ATR triple barrier.

## Artifacts

- BTCUSDT cycle:
  `data/research/historical_cycles/wpr106_88_exit_stability_overlay_btcusdt_v1/`
- ETHUSDT cycle:
  `data/research/historical_cycles/wpr106_88_exit_stability_overlay_ethusdt_v2/`
- Aborted ETHUSDT audit run:
  `data/research/historical_cycles/wpr106_88_exit_stability_overlay_ethusdt_v1/`
- Combined summary:
  `data/research/wpr106_88_exit_stability_overlay/summary/wpr106_88_exit_stability_overlay_summary.json`
- Candidate stability CSV:
  `data/research/wpr106_88_exit_stability_overlay/summary/wpr106_88_candidate_stability_summary.csv`
- Candidate monthly returns CSV:
  `data/research/wpr106_88_exit_stability_overlay/summary/wpr106_88_candidate_monthly_returns.csv`

ETHUSDT v1 aborted before candidate generation because the background process
imported `C:/Users/papaa/Music/tradingbotsuite` instead of this checkout. The
valid ETHUSDT rerun is v2, launched with `PYTHONPATH=src`.

## Results

- Searched strategy rows: 140 non-no-trade rows across both symbols.
- Strict sparse research-candidate rows: 28.
- All rows including no-trade baselines: 182.
- Positive net and positive expectancy rows: 18.
- Month-stable candidates: 0.
- Gate-accepted rows: 0.

The stability rule used in the summary requires positive pre-May net and
expectancy, at least 24 active months, no more than 4 losing active months, no
more than 4 inactive months, cost-stress survival at or above 0.70,
max-single-split PnL share at or below 0.75, and no single month contributing
more than 35% of absolute monthly PnL.

Top pre-May rows:

| Symbol | Candidate | Strategy | Exit | Net | Expectancy | Trades | Active months | Losing active months | Cost stress |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BTCUSDT | `fbbe4e1c2840` | `volatility_breakout_v1` | fixed holding | 0.777618 | 0.002843 | 271 | 28 | 13 | 0.636364 |
| BTCUSDT | `4239f08ef337` | `sparse_event_filter_v1` | simple runner | 0.637987 | 0.003852 | 134 | 28 | 8 | 0.636364 |
| BTCUSDT | `5efdd7874a40` | `sparse_event_filter_v1` | fixed holding | 0.526414 | 0.004697 | 106 | 28 | 12 | 0.636364 |
| ETHUSDT | `c3b24044c284` | `volatility_breakout_v1` | fixed holding | 0.386979 | 0.003333 | 236 | 28 | 13 | 0.000000 |
| ETHUSDT | `0fbdfa969ab8` | `sparse_event_filter_v1` | fixed holding | 0.295467 | 0.010381 | 33 | 20 | 10 | 0.909091 |
| ETHUSDT | `56790eb061f2` | `volatility_breakout_v1` | simple runner | 0.274303 | 0.000852 | 558 | 28 | 10 | 0.000000 |

## Interpretation

The BTC sparse simple-runner overlay improved the prior sparse fixed-hold lead
from +0.526414 to +0.637987 net and reduced losing active months from 12 to 8,
but still missed the requested month-to-month target and remained below the
0.70 cost-stress survival floor. The ETH sparse fixed-hold row remains the only
positive row in this packet with cost-stress survival above 0.70, but it is too
sparse and unstable: 20 active months, 10 losing active months, and 8 inactive
months.

Transparent volatility breakout fixed-holding rows can be profitable over the
full pre-May span, but they are not durable month-to-month candidates. BTC has
13 losing active months and sub-floor cost stress; ETH has 13 losing active
months and no cost-stress survival evidence in the shortlist gate output.

The lower-timeframe triple-barrier rows completed, but they were the slow tail
of both cycles and did not produce a stable lead. WPR106-88 therefore does not
justify using May 2026 as a benchmark holdout.

## Compute

The cycles used the historical-cycle backend policy with `backtest_backend:
auto`. Ranking artifacts report 13 fixed-holding rows per symbol using
`vector_fixed_holding`; the remaining 78 richer-exit rows per symbol used the
reference backend. No row records CUDA execution, and no GPU speedup claim is
made. The repeated pandas fragmentation warning in `features/packs.py` remains
covered by `ISSUE-R106-022`.

## Validation

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Result: compileall passed; contracts passed with 451 passed.
