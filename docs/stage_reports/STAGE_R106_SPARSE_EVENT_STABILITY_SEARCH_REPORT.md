# Stage R106 Sparse Event Stability Search Report

Date: 2026-06-11
Work packet: `docs/work_packets/WPR106-87-sparse-event-stability-search.md`

## Scope

WPR106-87 revisited sparse/event filters on the WPR106-85 exact pre-May
archive-backed BTCUSDT and ETHUSDT fixture packs. The tuning window stayed
2024-01-01 through 2026-04-30. May 2026 was not used for tuning, ranking,
selection, optimizer feedback, or holdout evaluation.

The search used six explicit sparse search spaces per symbol, 66 sampled sparse
candidates per symbol, and injected no-trade/transparent comparators for 74
aggregate backtests per symbol. The spaces covered price-only trend sparse
filters, aggTrade-proxy volatility sparse filters, both-sided controls,
one-sided post-selection controls, aligned and contrarian flow confirmation,
and 24h plus 72h fixed holds.

## Implementation Note

The first BTCUSDT run exposed avoidable compute cost in
`sparse_event_filter_v1` when active aggTrade flow confirmation was paired with
`spacing_bars: 1`. The strategy was repeatedly constructing the same flow
Series per candidate. WPR106-87 made a behavior-preserving optimization that
materializes the flow-confirmation Series once per prediction frame and reuses
them for each sparse candidate.

Focused regression:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_sparse_event_filter.py -q
```

Result: `1 passed`.

The wider feature builder still emits the known pandas fragmentation warning
from `features/packs.py`; `ISSUE-R106-022` remains open for full wide-frame
defragmentation.

## Outputs

- BTC config:
  `configs/research/wpr106_87_sparse_event_stability_btcusdt_v1.json`
- ETH config:
  `configs/research/wpr106_87_sparse_event_stability_ethusdt_v1.json`
- BTC cycle:
  `data/research/historical_cycles/wpr106_87_sparse_event_stability_btcusdt_v1/`
- ETH cycle:
  `data/research/historical_cycles/wpr106_87_sparse_event_stability_ethusdt_v1/`
- Stability summary:
  `data/research/wpr106_87_sparse_event_stability/summary/wpr106_87_sparse_event_stability_summary.json`
- Candidate stability CSV:
  `data/research/wpr106_87_sparse_event_stability/summary/wpr106_87_candidate_stability_summary.csv`
- Candidate-month CSV:
  `data/research/wpr106_87_sparse_event_stability/summary/wpr106_87_candidate_monthly_returns.csv`

## Compute Evidence

Both cycles used `backtest_backend: auto` with optional CUDA preference and
`gpu_required: false`. The run selected CPU vector aggregate screening for the
74 aggregate candidates per symbol and CPU/reference validation for split and
cost-stress rows. CUDA was not selected and no GPU speedup claim is made.

BTCUSDT backend summary: 74 aggregate vector backtests, 60 validation reference
backtests.

ETHUSDT backend summary: 74 aggregate vector backtests, 60 validation reference
backtests.

## Results

Across BTCUSDT and ETHUSDT there were 132 research sparse candidates, 8 rows
with positive net return and positive expectancy after costs, and zero accepted
or month-stable leads.

BTCUSDT:

- Research rows: 66
- Positive net rows: 2
- Positive expectancy rows: 4
- Positive net and expectancy rows: 2
- Month-stable candidates: 0

Best BTCUSDT row:

- Candidate:
  `sparse_event_filter_v1__features_price_perp_aggflow_no_wt__72h__5efdd7874a40`
- Parameters: volatility breakout, long-only post-selection, contrarian
  flow, 72h hold, `spacing_bars: 1`, `top_n_per_window: 2`
- Trades: 106, all long
- Net after fees/slippage/funding: `+0.526414`
- Costed expectancy: `+0.004697`
- Active months: 28 of 28
- Losing active months: 12
- Average trades per active day: 1.0
- Cost-stress survival: `0.636364`, below the `0.70` floor
- Max single split PnL share: `0.354927`
- Decision: rejected

This row is not a May holdout lead because cost-stress survival fails and the
month-to-month profile is not stable: 2025 has 8 losing active months and a
negative yearly net return.

ETHUSDT:

- Research rows: 66
- Positive net rows: 6
- Positive expectancy rows: 9
- Positive net and expectancy rows: 6
- Month-stable candidates: 0

Best ETHUSDT row:

- Candidate:
  `sparse_event_filter_v1__features_price_perp_aggflow_no_wt__72h__0fbdfa969ab8`
- Parameters: volatility breakout, short-only post-selection, aligned flow,
  72h hold, `spacing_bars: 18`, `top_n_per_window: 1`
- Trades: 33, all short
- Net after fees/slippage/funding: `+0.295467`
- Costed expectancy: `+0.010381`
- Active months: 20 of 28
- Losing active months: 10
- Inactive months: 8
- Average trades per active day: 1.0
- Cost-stress survival: `0.909091`
- Max single split PnL share: `0.371121`
- Decision: rejected

This row passes the cost-stress floor but is too sparse and unstable for the
user's target: 10 of 20 active months lose money, and 8 of 28 months are
inactive.

## Decision

The sparse/event revisit produced several positive pre-May aggregate rows, but
none meet the month-to-month stability target. The search therefore does not
trigger the May 2026 benchmark holdout. May 2026 remains fully unused.

All outputs are `research_only`, `observe_only`, and `promotion_ready: false`.
No candidate pack, paper/live artifact, order-placement path, sizing change,
runtime-mode change, live configuration write, or promotion claim was produced.

## Validation

Completed:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_sparse_event_filter.py -q
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Results: sparse focused test `1 passed`; compileall passed; contracts
`451 passed`.
