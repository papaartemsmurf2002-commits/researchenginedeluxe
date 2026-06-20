# WPR106-105 Causal Bar-Path Flow Exit Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Test a fresh 2024-forward strategy family that is not another defense or
reweighting of the rejected WPR106-100 through WPR106-104 sleeve leads:
causal 15m bar-path, session, volatility, and aggTrade-flow entries with
fixed-hold and intrahold barrier-style exits. The packet should determine
whether simple economically interpretable price/flow variants can produce
month-stable pre-May leads before May 2026 is used as a benchmark.

## Scope

- Use WPR106-96 verified BTCUSDT/ETHUSDT 2024-01 through 2026-05 local public
  archive context.
- Optimize, score, filter, and select only on 2024-01-01 through
  2026-04-30.
- Keep May 2026 fully out of feature choice, strategy choice, threshold choice,
  exit choice, ranking, filtering, and selection.
- Use May 2026 only as a benchmark holdout after fixed pre-May rows are
  selected.
- Test interpretable families:
  - channel breakout with same-direction or opposite-flow confirmation;
  - flush/fade reversal using wick, return shock, volatility, and flow;
  - range mean-reversion using channel location, choppiness, and flow reversal;
  - continuation-after-compression variants.
- Allow active 1 to 5 trades per active day when costs, overlap, drawdown,
  trade clustering, and monthly stability are measured.
- Use realistic explicit costs consistent with the current R106 research
  family by default: taker commission 0.0432% per side plus a conservative
  slippage/spread allowance.
- Keep every artifact research-only, observe-only, and promotion-ready false.

## Allowed paths

- `docs/work_packets/WPR106-105-causal-barpath-flow-exit-search.md`
- `docs/stage_reports/STAGE_R106_CAUSAL_BARPATH_FLOW_EXIT_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_105*/**`

## Out of scope

- No May 2026 tuning, selection feedback, feature choice, threshold choice,
  filter choice, exit choice, optimizer feedback, or cost tuning.
- No source package changes unless a small, scoped, testable blocker prevents
  artifact-only research.
- No candidate pack, paper/live artifact, order placement, position sizing,
  runtime-mode change, live configuration write, CUDA speedup claim, or
  promotion claim.
- No synthetic fallback data.
- No unconstrained optimizer that fits monthly weights or thresholds to May.

## Exit evidence

- A deterministic WPR106-105 runner and pre-May search artifacts are written
  under `data/research/wpr106_105*/`.
- Pre-May selected rows, monthly returns, trades, and benchmark-only May rows
  are written separately.
- The stage report records whether any row satisfies the target profile of
  roughly zero to two losing months per full pre-May year, whether active-rate
  behavior is acceptable, and whether May confirms or rejects fixed promising
  rows.
- Validation baseline is run or explicitly reported if blocked:
  `python -m compileall -q src/tradingbotsuite` and
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`.

## Closeout

Closed on 2026-06-11. The artifact-only runner evaluated 5,832 causal
bar-path/flow candidates over the WPR106-96 verified 2024-01 through 2026-05
BTCUSDT/ETHUSDT public-archive context. Optimization and selection used only
2024-01-01 through 2026-04-30, and pre-May trades were required to exit before
2026-05-01. May was joined only after fixed pre-May selection.

The screen found 270 positive pre-May rows, 3 loose pre-May holdout rows, and
0 strict month-stability rows. All 3 selected loose rows were ETHUSDT variants
and all were negative in May:

- `barflow-4af57c2235dc425e`: +0.093710 pre-May, 54 trades, 10 losing months,
  May -0.010393.
- `barflow-5adcceacbae60ef7`: +0.063250 pre-May, 56 trades, 10 losing months,
  May -0.036940.
- `barflow-1f575771dfa9ff18`: +0.015509 pre-May, 54 trades, 10 losing months,
  May -0.002629.

The family is rejected as currently configured. Profitable rows either fail the
annual month-stability target, are too sparse/inactive, or fail the May
benchmark. No candidate pack, paper/live artifact, order/sizing/runtime change,
live configuration write, CUDA speedup claim, or promotion claim exists.

Validation passed:

- `python -m compileall -q data/research/wpr106_105_causal_barpath_flow_exit_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` with 460 passed.
