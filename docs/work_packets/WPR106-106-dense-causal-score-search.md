# WPR106-106 Dense Causal Score Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Test a fresh 2024-forward dense-entry strategy family after WPR106-105 rejected
the causal bar-path/flow variants. This packet searches causal score and
quantile-threshold entries that deliberately target active rates around 1 to 5
trades per active day after one-position overlap handling, while selecting only
on month-to-month pre-May stability.

## Scope

- Use WPR106-96 verified BTCUSDT/ETHUSDT 2024-01 through 2026-05 local public
  archive context.
- Optimize, calibrate score thresholds, rank, filter, and select only on
  2024-01-01 through 2026-04-30.
- Keep May 2026 fully out of feature choice, score-weight choice, threshold
  calibration, hold selection, ranking, filtering, and selection.
- Apply fixed pre-May score thresholds unchanged to May 2026 only after a row is
  selected as a promising pre-May lead.
- Test transparent causal score families built from completed 15m bar features:
  return momentum, return reversal, wick rejection, channel location,
  volatility/range expansion or compression, session/day effects, and
  aggTrade-flow imbalance or divergence.
- Include long-only, short-only, and symmetric two-sided variants with fixed
  holds that enforce one open position per symbol/candidate.
- Measure explicit taker commission 0.0432% per side plus a conservative
  slippage/spread allowance, active-rate density, overlap skips, monthly
  returns, full-year losing-month counts, drawdown, and cost-stress survival.
- Keep every artifact research-only, observe-only, and promotion-ready false.

## Allowed paths

- `docs/work_packets/WPR106-106-dense-causal-score-search.md`
- `docs/stage_reports/STAGE_R106_DENSE_CAUSAL_SCORE_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_106*/**`

## Out of scope

- No May 2026 tuning, score/threshold/feature/filter feedback, exit choice
  feedback, optimizer feedback, or cost tuning.
- No source package changes unless a small, scoped, testable blocker prevents
  artifact-only research.
- No candidate pack, paper/live artifact, order placement, position sizing,
  runtime-mode change, live configuration write, CUDA speedup claim, or
  promotion claim.
- No synthetic fallback data.
- No fitted model that uses May labels, May scores, May quantiles, or May
  distributions.

## Exit evidence

- A deterministic WPR106-106 runner and pre-May search artifacts are written
  under `data/research/wpr106_106*/`.
- Pre-May selected rows, monthly returns, trades, and benchmark-only May rows
  are written separately when any promising pre-May row qualifies.
- The stage report records whether any row satisfies the target profile of
  roughly zero to two losing months per full pre-May year, whether the intended
  1 to 5 trades/day behavior survives overlap handling and costs, and whether
  May confirms or rejects fixed promising rows.
- Validation baseline is run or explicitly reported if blocked:
  `python -m compileall -q src/tradingbotsuite` and
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`.

## Closeout

Closed on 2026-06-11. The artifact-only runner evaluated 129,600 dense causal
score rows over the WPR106-96 verified 2024-01 through 2026-05 BTCUSDT/ETHUSDT
public-archive context, with BTCUSDT and ETHUSDT processed in separate worker
processes. Optimization, score-threshold calibration, ranking, filtering, and
selection used only 2024-01-01 through 2026-04-30, and pre-May trades were
required to exit before 2026-05-01. May was joined only after fixed pre-May
loose/strict rows were selected.

The search found 6,656 positive pre-May rows and 369 loose pre-May rows, but
0 strict month-stability rows. All positive rows landed inside the intended
1-to-5 trades per active day band after overlap handling, 6,619 positive rows
were active in at least 24 months, and 2,947 positive rows had cost-stress
survival of at least 0.75. The blocker was annual month stability: zero
positive rows met the full-year constraint of two or fewer losing active months
in both 2024 and 2025.

All 369 loose rows were benchmarked in May after pre-May selection. May results
were 107 positive, 261 negative, and 1 flat. The highest pre-May rows all
failed the annual loss target and were May-negative; the best May-positive rows
were already rejected by pre-May annual stability.

The dense causal score family is rejected as currently configured. It is useful
diagnostic evidence that active 1-to-5 trades/day behavior can survive costs
and overlap in parts of the search space, but it does not produce a stable
pre-May lead or candidate-ready artifact. No May tuning, candidate pack,
paper/live artifact, order/sizing/runtime change, live configuration write,
CUDA speedup claim, or promotion claim exists.

Validation passed:

- `python -m compileall -q data/research/wpr106_106_dense_causal_score_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` with 460 passed.
