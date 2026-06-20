# Stage R106 Active-Rate Density Search And Feature Defrag Report

Date: 2026-06-11
Work packet: `docs/work_packets/WPR106-91-active-rate-density-search-and-feature-defrag.md`
Owner: Codex Research Agent

## Decision

WPR106-91 is closed as a pre-May active-rate density search plus a scoped
wide-feature defragmentation fix. The packet deliberately allowed higher
active entry rates, revisited transparent and sparse/event families, recorded
overlap evidence, and found no strict month-stable lead.

May 2026 was not used. No row is eligible for the requested May 2026 benchmark
holdout from this packet.

No candidate pack, paper/live artifact, order placement, sizing change,
runtime-mode change, live configuration write, CUDA speedup claim, or
promotion-ready claim exists.

## Scope

- Window: 2024-01-01 through 2026-04-30 only.
- May 2026 usage: none.
- Feature change: `build_feature_frame` now batches missing manifest feature
  columns and missingness indicators with `pd.concat`, then copies once to
  defragment the result.
- Search scope: BTCUSDT and ETHUSDT transparent volatility, trend, range, and
  sparse/event rows across 24h and 72h holding windows, with fixed-hold
  screens plus small simple-runner/trailing probes.
- Active-rate policy: retain and score rows in the 1 to 5 trades-per-active-day
  band when cost, overlap, split, and monthly evidence are recorded.
- Compute: CPU historical-cycle execution with `gpu_acceleration: disabled`.
  No CUDA path was requested or claimed.

## Artifacts

- BTCUSDT config:
  `configs/research/wpr106_91_active_rate_density_search_btcusdt_v1.json`
- ETHUSDT config:
  `configs/research/wpr106_91_active_rate_density_search_ethusdt_v1.json`
- BTCUSDT cycle:
  `data/research/historical_cycles/wpr106_91_active_rate_density_search_btcusdt_v1/`
- ETHUSDT cycle:
  `data/research/historical_cycles/wpr106_91_active_rate_density_search_ethusdt_v1/`
- Combined summary:
  `data/research/wpr106_91_active_rate_density_search/wpr106_91_active_rate_density_search_summary.json`
- Candidate summary:
  `data/research/wpr106_91_active_rate_density_search/wpr106_91_candidate_summary.csv`
  and
  `data/research/wpr106_91_active_rate_density_search/wpr106_91_candidate_summary.parquet`
- Monthly returns:
  `data/research/wpr106_91_active_rate_density_search/wpr106_91_candidate_monthly_returns.csv`

## Results

- Candidate rows summarized: 268.
- Positive net/expectancy rows: 14.
- Rows inside 1 to 5 trades per active day: 254.
- Positive rows above 1 trade per active day: 0.
- Loose monthly-stability rows: 1.
- Strict monthly-stability rows: 0.
- May-holdout eligible rows: 0.
- Gate status: 268 blocked, 0 passed.
- Ranking decision: 268 rejected, 0 accepted.

By symbol:

| Symbol | Candidate rows | Positive rows | Loose hits | Strict hits | Best net |
| --- | ---: | ---: | ---: | ---: | ---: |
| BTCUSDT | 134 | 10 | 1 | 0 | 1.299355 |
| ETHUSDT | 134 | 4 | 0 | 0 | 0.751568 |

Active-rate distribution:

| Trades per active day | Rows |
| --- | ---: |
| 0 | 14 |
| 0 to 1 | 234 |
| 1 to 2 | 19 |
| 2 to 3 | 1 |
| 3 to 5 | 0 |
| >5 | 0 |

Positive rows by family:

| Symbol | Family | Positive rows |
| --- | --- | ---: |
| BTCUSDT | `volatility_breakout_v1` | 5 |
| BTCUSDT | `sparse_event_filter_v1` | 5 |
| ETHUSDT | `volatility_breakout_v1` | 3 |
| ETHUSDT | `sparse_event_filter_v1` | 1 |

Loose row:

| Symbol | Candidate | Strategy | Exit | Net | Expectancy | Trades/day | Active months | Losing months | Cost-stress survival | Max concurrent |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BTCUSDT | `volatility_breakout_v1__features_price_trend_vol__72h__ea9b0ade9515` | `volatility_breakout_v1` | `fixed_holding_window` | 1.299355 | 0.004028 | 1.0 | 28 | 11 | 0.545455 | 1 |

This row has low monthly concentration (`0.101961`) and no overlap, but it
fails cost-stress survival and strict yearly losing-month caps. It remains
blocked and is not May-holdout eligible.

## Interpretation

The active-rate hypothesis did not produce a robust high-density lead. The
search did exercise rows above 1 trade per active day, including rows up to
about 2 trades per active day, but every positive net/expectancy row settled at
exactly 1 trade per active day. Higher-density rows did not survive costs and
monthly stability checks.

The best result is a transparent volatility-breakout comparator rather than a
novel sparse aggTrade lead. Sparse rows still produced positive examples, but
they failed strict month-to-month stability and cost-stress requirements.

The feature defragmentation is still useful: the focused wide-feature test
confirms the `features_price_perp_aggflow_no_wt` missingness path no longer
emits pandas `PerformanceWarning`, and both wide-feature BTCUSDT/ETHUSDT
cycles completed with split and cost-stress evidence.

The next useful research direction is not to spend May 2026 holdout intake on
WPR106-91 rows. Continue broader entry/exit/model-family exploration, or add
new causal information, while keeping May 2026 reserved for a later strict
pre-May lead.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\features\test_feature_builders.py -q -k "price_perp_aggflow_no_wt or aggtrade_orderflow_v1_derives"
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- Focused feature-builder slice: 2 passed, 29 deselected.
- Compileall: passed.
- Contracts: 454 passed.
