# WPR106-154 Cross-Symbol Intrabar Flow Transfer Search

Status: closed
Date: 2026-06-12
Stage: R106 strategy research

## Objective

Search for active 2024-forward BTCUSDT/ETHUSDT strategy leads using completed
15m bars plus 1m intrabar aggTrade order-flow shape from the opposite symbol.
The packet tests whether cross-symbol flow pressure, late-flow transfer,
absorption, synchronized flow, or relative dislocation can improve
month-to-month stability versus the rejected single-symbol intrabar flow
families.

Optimization and selection use 2024-01-01 through 2026-04-30 only. May 2026 is
fully excluded from tuning, thresholds, filters, ranking, and selection, then
used only as a fixed benchmark holdout for promising pre-May rows.

## Allowed Paths

- `docs/work_packets/WPR106-154-cross-symbol-intrabar-flow-transfer-search.md`
- `docs/stage_reports/STAGE_R106_CROSS_SYMBOL_INTRABAR_FLOW_TRANSFER_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_154_cross_symbol_intrabar_flow_transfer_search/**`

## Inputs

- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/source_context/**`
- `data/research/wpr106_153_intrabar_order_flow_event_search/scripts/run_wpr106_153_intrabar_order_flow_event_search.py`
- WPR106-151 and WPR106-153 reports for shared metric definitions and rejection
  context.

## Method

- Reuse the WPR106-153 local intrabar feature construction without changing
  shared packages.
- Build leader/target pairs for BTCUSDT -> ETHUSDT and ETHUSDT -> BTCUSDT.
- Evaluate cross-symbol templates covering leader-flow follow/fade, late-flow
  transfer, absorption transfer, relative flow dislocation follow/reversion,
  synchronized flow follow, and cross flow/price divergence fade.
- Allow active entry rates of 1, 3, and 5 raw signals per day, with accepted
  trade caps of 1, 3, and 5 per day.
- Preserve completed-bar causality: signals use completed 15m information and
  enter on the next 15m open; pre-May exits must complete before 2026-05-01.
- Apply the same cost model and stability reporting used in recent packets.
- Keep all outputs research-only, observe-only, and `promotion_ready: false`.

## Validation

- `python -m compileall -q data/research/wpr106_154_cross_symbol_intrabar_flow_transfer_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`

## Exit Criteria

- Write ranking, selected pre-May replay, May benchmark, summary, and stage
  report artifacts.
- Update the stage ledger with the packet decision.
- Do not write a candidate pack or make paper/live/promotion claims.
