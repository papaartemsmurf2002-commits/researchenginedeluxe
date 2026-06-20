# WPR106-156 Recent Cross-Family Complement Portfolio Search

Status: closed
Date: 2026-06-12
Stage: R106 strategy research

## Objective

Test whether recent rejected or near-miss 2024-forward strategy families are
individually unstable but complementary enough to form a stable research-only
portfolio. The packet combines fixed selected rows from WPR106-151 through
WPR106-155, behavior-de-duplicates source rows using pre-May accepted trades,
then searches equal-sleeve portfolios with same-symbol overlap handling and
daily trade caps.

Optimization and selection use 2024-01-01 through 2026-04-30 only. May 2026 is
fully excluded from source scoring, behavior de-duplication decisions,
portfolio construction, diversity filters, ranking, and selection. May 2026 is
used only as a fixed benchmark holdout for selected pre-May portfolios.

## Allowed Paths

- `docs/work_packets/WPR106-156-recent-cross-family-complement-portfolio-search.md`
- `docs/stage_reports/STAGE_R106_RECENT_CROSS_FAMILY_COMPLEMENT_PORTFOLIO_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_156_recent_cross_family_complement_portfolio_search/**`

## Inputs

- `data/research/wpr106_151_causal_multiday_level_retest_search/**`
- `data/research/wpr106_152_level_knn_trade_filter_search/**`
- `data/research/wpr106_153_intrabar_order_flow_event_search/**`
- `data/research/wpr106_154_cross_symbol_intrabar_flow_transfer_search/**`
- `data/research/wpr106_155_causal_lorentzian_regime_knn_search/**`

## Method

- Load fixed selected pre-May and May benchmark trade artifacts from
  WPR106-151 through WPR106-155.
- Behavior-de-duplicate source rows by pre-May symbol/entry/exit/side behavior
  and retain the best pre-May representative per behavior hash.
- Construct diversified source portfolios using only pre-May evidence:
  high-quality seed rows, low monthly-return correlation, loss-complement
  scores, packet/family diversity, and equal-sleeve accounting.
- Replay portfolio trades with embedded source costs, same-symbol overlap
  skipping, active daily caps of 1, 3, and 5, and cost stress.
- Select strict or loose pre-May rows without May feedback, then benchmark May
  for those fixed rows only.
- Keep outputs research-only, observe-only, and `promotion_ready: false`.

## Validation

- `python -m compileall -q data/research/wpr106_156_recent_cross_family_complement_portfolio_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`

## Exit Criteria

- Write source-pool, ranking, selected pre-May replay, May benchmark, summary,
  and stage report artifacts.
- Update the stage ledger with the packet decision.
- Do not write a candidate pack or make paper/live/promotion claims.

## Result

Closed as rejected candidate-ready evidence. The run loaded 401 recent selected
source rows from WPR106-151 through WPR106-155, behavior-de-duplicated them to
153 source rows, generated 2,154 raw equal-sleeve portfolios, and
pre-May-portfolio-behavior de-duplicated those to 1,852 rows. It found 273
strict pre-May rows and selected 100 strict rows without May feedback, but May
2026 rejected the selected set with 0 positive, 100 negative, and 0 flat rows.
No candidate pack, paper/live artifact, order/sizing/runtime change, live
configuration write, CUDA speedup claim, or promotion claim was made.
