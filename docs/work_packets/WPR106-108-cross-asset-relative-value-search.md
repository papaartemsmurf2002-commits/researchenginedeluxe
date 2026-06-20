# WPR106-108 Cross-Asset Relative Value Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Test a fresh 2024-forward family that is structurally different from the
single-symbol sparse, dense-score, and KNN passes: BTC/ETH relative-value,
spread, and lead-lag strategies. The packet should determine whether
cross-asset signals can produce active, cost-positive, month-stable pre-May
leads before May 2026 is used as a benchmark holdout.

## Scope

- Use WPR106-96 verified BTCUSDT/ETHUSDT 2024-01 through 2026-05 local public
  archive context.
- Optimize family, spread window, beta model, z-score threshold, lead-lag
  threshold, side mode, hold, session, volatility/filter settings, and ranking
  only on 2024-01-01 through 2026-04-30.
- Keep May 2026 fully out of feature choice, threshold choice, family choice,
  exit/hold choice, ranking, filtering, and selection.
- Apply fixed pre-May settings unchanged to May 2026 only after a row is
  selected as a promising pre-May lead.
- Test pair-return variants with both-leg costs and one open pair position at a
  time:
  - ETH/BTC spread mean reversion;
  - ETH/BTC spread momentum;
  - BTC-leading-ETH and ETH-leading-BTC follow-through;
  - flow-divergence relative-value variants;
  - vol-adjusted spread variants.
- Include single-leg diagnostic variants when the signal explicitly chooses
  only BTCUSDT or ETHUSDT, but keep them clearly labeled separately from
  pair-return rows.
- Allow active 1 to 5 trades per active day after overlap handling.
- Measure explicit taker commission 0.0432% per side plus conservative
  slippage/spread allowance per leg, active-rate density, monthly returns,
  annual losing-month counts, drawdown, overlap skips, and cost-stress survival.
- Keep every artifact research-only, observe-only, and promotion-ready false.

## Allowed paths

- `docs/work_packets/WPR106-108-cross-asset-relative-value-search.md`
- `docs/stage_reports/STAGE_R106_CROSS_ASSET_RELATIVE_VALUE_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_108*/**`

## Out of scope

- No May 2026 tuning, feature/filter feedback, threshold feedback, exit/hold
  feedback, optimizer feedback, or cost tuning.
- No source package changes unless a small, scoped, testable blocker prevents
  artifact-only research.
- No candidate pack, paper/live artifact, order placement, position sizing,
  runtime-mode change, live configuration write, CUDA speedup claim, or
  promotion claim.
- No synthetic fallback data.
- No fitted beta, scaler, threshold, or score that uses May labels, May returns,
  May quantiles, or May distributions.

## Exit evidence

- A deterministic WPR106-108 runner and pre-May search artifacts are written
  under `data/research/wpr106_108*/`.
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

Closed on 2026-06-11. The artifact-only runner evaluated 19,200 BTC/ETH
cross-asset rows over the WPR106-96 verified 2024-01 through 2026-05 public
archive context. Optimization, beta/window/hold/session/filter choice,
score-threshold calibration, ranking, filtering, and selection used only
2024-01-01 through 2026-04-30. May was joined only after fixed pre-May
loose/strict rows were selected.

The search found 986 positive pre-May rows and 81 loose pre-May rows, but
0 strict month-stability rows. All 986 positive rows landed inside the intended
1-to-5 trades per active day band after overlap handling, 953 positive rows
were active in at least 24 months, and 475 positive rows had cost-stress
survival of at least 0.75. The blocker was annual month stability: zero
positive rows met the full-year constraint of two or fewer losing active months
in both 2024 and 2025.

The selected loose rows were dominated by single-leg ETH follow-BTC diagnostics:
71 single ETH rows, 7 pair rows, and 3 single BTC rows. All 81 loose rows were
benchmarked in May after pre-May selection. May results were 11 positive,
69 negative, and 1 flat. The highest pre-May row `xasset-de4ac045c28d3b9c`
was +1.652138 pre-May with 299 trades and 9 losing months, then benchmarked
-0.038135 in May. The closest stability row `xasset-264398ad33c1ce89` had
5 pre-May losing months with annual losses of 2024: 2, 2025: 3, and
2026 Jan-Apr: 0, but still missed the full-year target and lost -0.016162 in
May. Every selected pair row that traded in May was May-negative.

The cross-asset family is rejected as currently configured. It is useful
diagnostic evidence that lead-lag effects can produce active, cost-positive
single-leg ETH rows, but it does not produce stable BTC/ETH pair evidence or a
candidate-ready lead. No May tuning, candidate pack, paper/live artifact,
order/sizing/runtime change, live configuration write, CUDA speedup claim, or
promotion claim exists.

Validation passed:

- `python -m compileall -q data/research/wpr106_108_cross_asset_relative_value_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` with 460 passed.
