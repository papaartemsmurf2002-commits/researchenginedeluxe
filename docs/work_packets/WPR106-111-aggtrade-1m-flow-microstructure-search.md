# WPR106-111 AggTrade 1m Flow Microstructure Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Test a fresh 2024-forward order-flow-style family using the WPR106-96 verified
1m aggTrade aggregates for BTCUSDT and ETHUSDT. The packet should determine
whether short-horizon 1m flow bursts, flow exhaustion, flow/price divergence,
and volume-shock variants can produce active, cost-positive, month-stable
pre-May leads before May 2026 is used as a benchmark holdout.

## Scope

- Use WPR106-96 verified BTCUSDT/ETHUSDT 2024-01 through 2026-05 local public
  archive 1m aggTrade context.
- Optimize family, side logic, score threshold, hold horizon, session, volume
  filter, and ranking only on 2024-01-01 through 2026-04-30.
- Keep May 2026 fully out of family choice, feature choice, threshold choice,
  hold choice, session/filter choice, ranking, and selection.
- Apply fixed pre-May settings unchanged to May 2026 only after a row is
  selected as a promising pre-May lead.
- Use completed 1m aggTrade aggregate rows only; enter on the next 1m aggregate
  price; require pre-May selected trades to exit before 2026-05-01.
- Test flow continuation, flow reversal/exhaustion, flow-price divergence,
  volume shock follow/fade, and taker-buy/sell imbalance persistence variants.
- Allow active 1 to 5 trades per active day after one-position overlap
  handling.
- Measure explicit taker commission 0.0432% per side plus conservative
  slippage/spread allowance, active-rate density, monthly returns, annual
  losing-month counts, drawdown, overlap skips, and cost-stress survival.
- Keep every artifact research-only, observe-only, and promotion-ready false.

## Allowed paths

- `docs/work_packets/WPR106-111-aggtrade-1m-flow-microstructure-search.md`
- `docs/stage_reports/STAGE_R106_AGGTRADE_1M_FLOW_MICROSTRUCTURE_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_111*/**`

## Out of scope

- No May 2026 tuning, feature/filter feedback, threshold feedback, exit/hold
  feedback, optimizer feedback, or cost tuning.
- No source package changes unless a small, scoped, testable blocker prevents
  artifact-only research.
- No candidate pack, paper/live artifact, order placement, position sizing,
  runtime-mode change, live configuration write, CUDA speedup claim, or
  promotion claim.
- No synthetic fallback data.
- No fitted score, threshold, or filter that uses May labels, May returns, May
  quantiles, or May distributions.
- No claim that 1m aggTrade VWAP-like price is equivalent to complete 1m OHLC;
  path/high-low exits are out of scope for this packet.

## Exit evidence

- A deterministic WPR106-111 runner and pre-May search artifacts are written
  under `data/research/wpr106_111*/`.
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

Closed on 2026-06-11. The artifact runner
`data/research/wpr106_111_aggtrade_1m_flow_microstructure_search/scripts/run_wpr106_111_aggtrade_1m_flow_microstructure_search.py`
evaluated a 1m aggTrade flow microstructure sweep over the WPR106-96 verified
BTCUSDT/ETHUSDT 2024-01 through 2026-05 public-archive context. Family, score,
threshold, hold, session/filter, ranking, and selection used only 2024-01-01
through 2026-04-30. May 2026 was joined only after pre-May selection as a
benchmark holdout.

The run evaluated 15,360 rows, found 442 positive pre-May rows, 42 loose
pre-May rows, and 0 strict month-stability rows. All positive rows were inside
the allowed 1 to 5 trades per active day after one-position overlap handling,
so active-rate density was not the blocker. The blocker was annual month
stability: only seven positive rows met the full-year plus partial-2026
losing-month target, and none had at least 60 trades or 24 active months. Those
rows were sparse flow-burst fade shorts with 5 to 15 trades.

The 42 fixed selected rows benchmarked in May with 18 positive, 24 negative,
and 0 flat rows. May-positive selected rows were already rejected by pre-May
annual stability. The top pre-May row `flow1m-58682c5dd5e1679d` returned
+0.700716 pre-May with 9 losing months and benchmarked -0.007368 in May.

Main artifacts:

- `docs/stage_reports/STAGE_R106_AGGTRADE_1M_FLOW_MICROSTRUCTURE_SEARCH_REPORT.md`
- `data/research/wpr106_111_aggtrade_1m_flow_microstructure_search/wpr106_111_aggtrade_1m_flow_summary.json`
- `data/research/wpr106_111_aggtrade_1m_flow_microstructure_search/pre_may/combined_ranking.parquet`
- `data/research/wpr106_111_aggtrade_1m_flow_microstructure_search/pre_may/combined_monthly_returns.parquet`
- `data/research/wpr106_111_aggtrade_1m_flow_microstructure_search/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_111_aggtrade_1m_flow_microstructure_search/may_benchmark/selected_may_benchmark_metrics.parquet`

Validation passed:

- `python -m compileall -q data/research/wpr106_111_aggtrade_1m_flow_microstructure_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` reported 460 passed.

No candidate pack, paper/live artifact, order/sizing/runtime change, live
configuration write, CUDA speedup claim, or promotion claim exists.
