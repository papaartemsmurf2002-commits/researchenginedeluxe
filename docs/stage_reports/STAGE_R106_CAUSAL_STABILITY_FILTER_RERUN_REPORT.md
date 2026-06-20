# Stage R106 Causal Stability Filter Rerun Report

Date: 2026-06-11
Work packet: `docs/work_packets/WPR106-90-causal-stability-filter-rerun.md`
Owner: Codex Research Agent

## Decision

WPR106-90 is closed as a causal pre-entry rerun of the WPR106-89
regime/volatility diagnostic evidence. The packet adds default-off sparse
regime and volatility-bucket filters, reruns BTCUSDT and ETHUSDT pre-May
cycles, and finds no strict month-stable lead.

May 2026 was not used. No row is eligible for the requested May 2026 benchmark
holdout from this packet.

No candidate pack, paper/live artifact, order placement, sizing change,
runtime-mode change, live configuration write, CUDA speedup claim, or
promotion-ready claim exists.

## Scope

- Window: 2024-01-01 through 2026-04-30 only.
- May 2026 usage: none.
- Strategy change: `sparse_event_filter_v1` now supports default-off
  `allowed_regimes` and `allowed_volatility_buckets` pre-entry filters.
- Filter inputs: completed-bar regime labels when present, otherwise the same
  causal `volatility_shock_zscore` and `directional_slope_atr` derivation used
  by research-cycle validation labels; volatility buckets use
  `realized_volatility` with `atr_percentile` fallback, matching backtest
  enrichment.
- Compute: CPU historical-cycle execution with `gpu_acceleration: disabled`.
  No CUDA path was requested or claimed.

## Artifacts

- BTCUSDT config:
  `configs/research/wpr106_90_causal_stability_filter_btcusdt_v1.json`
- ETHUSDT config:
  `configs/research/wpr106_90_causal_stability_filter_ethusdt_v1.json`
- BTCUSDT cycle:
  `data/research/historical_cycles/wpr106_90_causal_stability_filter_btcusdt_v1/`
- ETHUSDT cycle:
  `data/research/historical_cycles/wpr106_90_causal_stability_filter_ethusdt_v1/`
- Combined summary:
  `data/research/wpr106_90_causal_stability_filter/wpr106_90_causal_stability_filter_summary.json`
- Candidate summary:
  `data/research/wpr106_90_causal_stability_filter/wpr106_90_candidate_summary.csv`
  and
  `data/research/wpr106_90_causal_stability_filter/wpr106_90_candidate_summary.parquet`
- Monthly returns:
  `data/research/wpr106_90_causal_stability_filter/wpr106_90_candidate_monthly_returns.csv`

## Results

- Candidate rows summarized: 150.
- Positive net/expectancy rows: 58.
- Loose monthly-stability rows: 4.
- Strict monthly-stability rows: 0.
- May-holdout eligible rows: 0.

By symbol:

| Symbol | Candidate rows | Positive rows | Loose hits | Strict hits | Best net |
| --- | ---: | ---: | ---: | ---: | ---: |
| BTCUSDT | 75 | 34 | 1 | 0 | 0.777618 |
| ETHUSDT | 75 | 24 | 3 | 0 | 0.688739 |

By filter family:

| Filter family | Rows | Positive rows | Loose hits | Strict hits | Best net |
| --- | ---: | ---: | ---: | ---: | ---: |
| none | 78 | 13 | 0 | 0 | 0.777618 |
| regime | 36 | 19 | 2 | 0 | 0.533206 |
| volatility bucket | 24 | 19 | 2 | 0 | 0.688739 |
| regime + volatility bucket | 12 | 7 | 0 | 0 | 0.303326 |

Loose rows:

| Symbol | Candidate | Strategy | Exit | Filter | Net | Trades | Active months | Losing active months | Inactive months |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| BTCUSDT | `4238b1bea4e` | `sparse_event_filter_v1` | `simple_runner_v1` | regime `range` | 0.332366 | 91 | 28 | 5 | 0 |
| ETHUSDT | `97c79272fc6e` | `sparse_event_filter_v1` | `simple_runner_v1` | regime `shock` | 0.238956 | 110 | 28 | 5 | 0 |
| ETHUSDT | `deaaa9048d86` | `sparse_event_filter_v1` | `simple_runner_v1` | volatility `medium` | 0.232763 | 50 | 21 | 5 | 7 |
| ETHUSDT | `b24d172d27aa` | `sparse_event_filter_v1` | `trailing_atr_after_profit` | volatility `medium` | 0.225425 | 50 | 21 | 5 | 7 |

Strict stability rule reused from WPR106-89:

- positive net return, positive costed expectancy, and positive expectancy
  versus no-trade,
- at least 24 active months,
- no more than 4 inactive months,
- no more than 4 total losing active months,
- no more than 2 losing active months in each full year,
- no more than 1 losing active month in 2026 Jan-Apr.

All four loose rows failed strict stability on losing-month or inactive-month
criteria. The strongest BTC causal row had 5 losing active months, including
3 in 2025. The ETH medium-volatility rows had only 21 active months and
7 inactive months.

## Interpretation

Causal pre-entry regime and volatility-bucket filters improved some monthly
stability signatures, but not enough to produce a May-holdout trigger. The
best net-return rows remain unstable: BTC transparent volatility breakout
fixed-hold reached +0.777618 but had 13 losing active months; BTC sparse
no-filter simple-runner reached +0.637987 but had 8 losing active months; ETH
medium-volatility fixed-hold reached +0.688739 but had 8 losing active months
and only 21 active months.

The result supports continuing the broad search, but not spending May 2026
holdout intake on these WPR106-90 rows yet. Useful next directions are new
causal entry/exit logic or broader model-family changes rather than defending
the rejected sparse side-veto lead or the May/June seasonal overlay.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_strategy_contracts.py -k "sparse_event_filter" -q
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_sparse_event_filter.py -q
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Results:

- Sparse contract slice: 10 passed, 279 deselected.
- Focused sparse implementation test: 1 passed.
- Compileall: passed.
- Contracts: 454 passed.
