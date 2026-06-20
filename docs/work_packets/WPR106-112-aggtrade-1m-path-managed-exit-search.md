# WPR106-112 AggTrade 1m Path-Managed Exit Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Test whether path-managed exits can improve the WPR106-111 1m aggTrade flow
signals without using May 2026 for tuning. WPR106-111 found active,
cost-positive 1m flow entries, but annual month stability remained weak. This
packet should determine whether fixed pre-May TP/SL/time-stop variants over
those same causal 1m signal families can produce a more stable research-only
lead before May 2026 is used as a benchmark holdout.

## Scope

- Use WPR106-96 verified BTCUSDT/ETHUSDT 2024-01 through 2026-05 local public
  archive 1m aggTrade context and the WPR106-111 pre-May 1m flow signal rows.
- Optimize source-row pool, TP, SL, max-hold, ranking, and selection only on
  2024-01-01 through 2026-04-30.
- Keep May 2026 fully out of source-pool choice, TP/SL choice, max-hold choice,
  ranking, and selection.
- Apply fixed pre-May source row and exit settings unchanged to May 2026 only
  after a row is selected as a promising pre-May lead.
- Use completed 1m aggTrade aggregate rows only; enter on the next 1m aggregate
  price; require pre-May selected trades to exit before 2026-05-01.
- Treat the 1m aggregate trade price path as a diagnostic price path, not as
  complete 1m OHLC. Do not claim intraminute high/low barrier precision.
- Preserve one-position overlap handling under the path-managed exit time.
- Allow active 1 to 5 trades per active day after overlap handling.
- Measure explicit taker commission 0.0432% per side plus conservative
  slippage/spread allowance, monthly returns, annual losing-month counts,
  drawdown, overlap skips, active-rate density, and cost-stress survival.
- Keep every artifact research-only, observe-only, and promotion-ready false.

## Allowed paths

- `docs/work_packets/WPR106-112-aggtrade-1m-path-managed-exit-search.md`
- `docs/stage_reports/STAGE_R106_AGGTRADE_1M_PATH_MANAGED_EXIT_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_112*/**`

## Out of scope

- No May 2026 tuning, feature/filter feedback, threshold feedback, exit/hold
  feedback, optimizer feedback, or cost tuning.
- No source package changes unless a small, scoped, testable blocker prevents
  artifact-only research.
- No candidate pack, paper/live artifact, order placement, position sizing,
  runtime-mode change, live configuration write, CUDA speedup claim, or
  promotion claim.
- No synthetic fallback data.
- No fitted score, threshold, TP, SL, max-hold, or filter that uses May labels,
  May returns, May quantiles, or May distributions.
- No claim that aggTrade aggregate price paths are equivalent to exchange
  intraminute OHLC/high-low barrier paths.

## Exit evidence

- A deterministic WPR106-112 runner and pre-May exit-search artifacts are
  written under `data/research/wpr106_112*/`.
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

Closed on 2026-06-11. The deterministic artifact runner is written at
`data/research/wpr106_112_aggtrade_1m_path_managed_exit_search/scripts/run_wpr106_112_aggtrade_1m_path_managed_exit_search.py`.

The pre-May source pool used only WPR106-111 positive rows and filtered before
May for trade count, active months, 1 to 5 trades per active day, and
cost-stress survival. It contained 271 source rows, split across 63 BTCUSDT
rows and 208 ETHUSDT rows. The exit grid evaluated 17,344 TP/SL/time-stop
overlays and found 2,316 positive pre-May rows, 89 loose pre-May rows, and 0
strict month-stability rows.

All 89 loose rows were benchmarked in May only after fixed pre-May selection:
58 were May-positive, 31 were May-negative, and 0 were flat. The best selected
pre-May row was `exit1m-d17af0cdc1689d55`, an ETHUSDT short flow-price
divergence row with +0.193259 pre-May return, 152 trades, 28 active months,
annual losing-month counts of 2024: 4, 2025: 5, and 2026 Jan-Apr: 0, and a May
benchmark return of -0.009363. The strongest May-positive selected cluster was
ETHUSDT short price-leads-flow-follow with +0.015629 May return, but those rows
failed pre-May annual stability before May was inspected.

The result improves the WPR106-111 diagnostic family on May survival but still
does not produce a candidate-quality lead. Zero positive pre-May rows met the
full-year target of no more than two losing active months in both 2024 and
2025. The closest stability diagnostics were low-return and cost-stress fragile.
No candidate pack, paper/live artifact, order placement, sizing change,
runtime-mode change, live configuration write, CUDA speedup claim, or promotion
claim was made.

Validation passed:

- `python -m compileall -q data/research/wpr106_112_aggtrade_1m_path_managed_exit_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` with 460 passed
