# WPR106-135 Microstructure Annual-Target Portfolio Search

Date: 2026-06-12
Owner: Codex Research Agent
Status: closed

## Objective

Test whether the sparse positive annual-target diagnostics found by
WPR106-134 can be converted into active, month-stable portfolios without using
May 2026 for tuning. The packet focuses on source de-duplication,
portfolio-level overlap handling, daily trade caps, equal-sleeve accounting,
cost stress, and fixed pre-May selection before any May benchmark replay.

## Allowed Paths

- `docs/work_packets/WPR106-135-microstructure-annual-target-portfolio-search.md`
- `docs/stage_reports/STAGE_R106_MICROSTRUCTURE_ANNUAL_TARGET_PORTFOLIO_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_135_microstructure_annual_target_portfolio_search/**`

## Inputs

- `data/research/wpr106_134_microstructure_state_transition_search/pre_may/microstructure_state_transition_ranking.parquet`
- `data/research/wpr106_134_microstructure_state_transition_search/scripts/run_wpr106_134_microstructure_state_transition_search.py`
- WPR106-134/WPR106-126 source-context loaders for completed 15m bars plus
  15m aggTrade-flow aggregation.

## Boundaries

- Research-only, observe-only, promotion-ready false.
- No candidate pack, paper/live artifact, order placement, sizing change,
  runtime-mode change, live configuration write, or promotion claim.
- May 2026 must not influence source-pool membership, source de-duplication,
  portfolio construction, daily caps, ranking, or selection.
- May 2026 may be replayed only after fixed strict pre-May portfolios are
  selected, or fixed loose portfolios if strict is empty.
- CUDA may be used only if a real path is executed and represented truthfully.
  The expected path is CPU/vectorized portfolio accounting with no speedup
  claim.
- If a blocking correctness risk is found, update `docs/KNOWN_ISSUES.md`.

## Evidence Plan

1. Load the WPR106-134 pre-May ranking and build the source pool only from
   positive annual-target diagnostics.
2. Replay source trades from the WPR106-134 runner with pre-May rows only, then
   de-duplicate by symbol/entry/exit/side behavior before portfolio search.
3. Construct fixed equal-sleeve portfolios across diversified source sleeves,
   applying no-overlap per symbol and a portfolio daily trade cap.
4. Evaluate portfolios with monthly stability, annual loss caps, drawdown,
   Sortino, best-month concentration, active trade rate, and cost stress.
5. Select strict portfolios first; select loose portfolios only if strict is
   empty. If neither exists, do not benchmark May.
6. Replay May 2026 only for the fixed selected portfolios and report it as a
   separate benchmark.

## Validation

Run focused script compile, then the branch baseline:

```powershell
python -m compileall -q data/research/wpr106_135_microstructure_annual_target_portfolio_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Completed:

- `python -m compileall -q data/research/wpr106_135_microstructure_annual_target_portfolio_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

## Closeout

The search replayed all 797 WPR106-134 positive annual-target source rows,
de-duplicated them to a 128-row source pool, generated 4,300 fixed portfolio
member sets, and evaluated 8,542 unique portfolio rows across daily caps of 3
and 5 trades/day. Pre-May portfolio construction found 8,542 positive rows,
3,538 annual-target rows, 4,635 loose rows, and 279 strict rows. The fixed
top-100 strict portfolios were selected before May replay.

The best selected strict pre-May portfolio used five equal-sleeve sources,
accepted 125 trades across 115 active days and 28 active months, averaged
1.087 trades per active day, had 4 losing months, annual losses of 2024: 2,
2025: 2, and 2026 Jan-Apr: 0, produced +0.133239 equal-sleeve net return,
recorded -0.011290 max drawdown, 0.173208 best-month share, and survived all
cost-stress multipliers.

May 2026 rejected the fixed strict selection: 43 selected portfolios were
positive, 55 were negative, and 2 were flat. The best May result was
+0.002333, the worst was -0.003529, and the median selected May return was
-0.000509. Selected portfolios also fired only 3 to 8 May trades, so May did
not confirm the pre-May stability.

Decision: reject this microstructure annual-target portfolio construction as a
candidate lead. The result is still useful because it shows pre-May source
combination can manufacture strict stability from sparse diagnostics, but the
fixed selection does not carry into May 2026. All outputs remain research-only,
observe-only, and promotion-ready false.
