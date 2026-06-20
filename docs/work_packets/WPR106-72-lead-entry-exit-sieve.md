# WPR106-72 - Lead Entry Exit Sieve

## Purpose

Continue the research-only search after WPR106-71 by running a smaller,
lead-focused entry/exit sieve. The goal is to compare the best observed entry
models against a compact exit set and adjacent horizon choices before deciding
whether any lead deserves larger durable validation or optimization.

## Scope

Allowed edit paths:

- `docs/work_packets/WPR106-72-lead-entry-exit-sieve.md`
- `docs/stage_reports/STAGE_R106_LEAD_ENTRY_EXIT_SIEVE_REPORT.md`
- `docs/KNOWN_ISSUES.md`
- `configs/research/fast_lead_exit_sieve_btcusdt_r106_v1.json`
- `configs/research/fast_lead_exit_sieve_ethusdt_r106_v1.json`

Allowed generated research-output paths:

- `data/research/historical_cycles/fast_lead_exit_sieve_btcusdt_r106_v1/**`
- `data/research/historical_cycles/fast_lead_exit_sieve_ethusdt_r106_v1/**`

Read-only evidence and reference paths:

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- `docs/stage_reports/STAGE_R106_FAST_ENTRY_FILTER_EXIT_RESEARCH_REPORT.md`
- `docs/work_packets/WPR106-71-fast-entry-filter-exit-research.md`
- `configs/research/fast_filter_probe_btcusdt_r106_v1.json`
- `configs/research/fast_filter_probe_ethusdt_r106_v1.json`
- `data/research/fixtures/*_context_provider_latest_month_v1/**`
- `data/research/historical_cycles/fast_filter_probe_*_r106_v1/**`
- `src/tradingbotsuite/backtesting/**`
- `src/tradingbotsuite/research_cycle/**`
- `src/tradingbotsuite/strategies/**`

Out of scope:

- Candidate-pack creation.
- Live, paper, order-placement, sizing, runtime-mode, or promotion behavior.
- Historical-data catalog rebuilds.
- Broad feature-provider, strategy, or backtest rewrites.
- Treating latest-window fast-screen outputs as candidate-ready evidence.

## Plan

1. Reuse subagents for strategy-side and exit-side logic checks.
2. Pin the WPR106-71 leading entry settings in explicit optimizer search
   spaces to avoid a broad default grid.
3. Compare fixed holding, simple runner variants, trailing after profit,
   volatility barriers, max-MAE stop, and funding-aware exits where context
   exists.
4. Run BTC and ETH latest-window diagnostic cycles under a bounded fast-loop
   budget.
5. Summarize entry model, exit model, horizon, and symbol trends, including
   whether anything merits larger durable validation.

## Research Boundary

All outputs are research-only, observe-only, and promotion-disabled. Latest
window context data is useful for fast discovery but cannot support candidate,
paper, live, sizing, runtime, or promotion claims.

## Outcome

Completed 2026-06-07.

Added BTC/ETH lead-sieve configs with explicit optimizer search spaces instead
of a broad metadata grid. BTC expanded to 40 ranked rows and completed in 26.1
seconds; ETH expanded to 28 ranked rows and completed in 21.1 seconds.

BTC strengthened the `volatility_breakout_v1` 72h latest-window lead. The best
row used `simple_runner_v1` with `activation_pct: 0.008` and
`runner_gap_pct: 0.004`, producing 24 trades, net 0.177178, expectancy
0.006868, and profit factor 6.398171. The same entry under fixed hold was
0.052648, base `0.005/0.004` simple runner was 0.140613, and trailing was
0.101481.

ETH confirmed the `trend_following_v1` 24h/72h latest-window lead. The best
row remained the 24h base `0.005/0.004` simple runner with 57 trades, net
0.313310, expectancy 0.004892, and profit factor 2.703250. ETH did not improve
with tighter or slower simple-runner variants.

Subagent audits found no P0/P1 math issue in the winning simple-runner paths.
They did identify P2 interpretation caveats for the existing audit follow-up:
`volatility_scaled_barrier` is static in the current primary-bar path, and
funding-aware exits use path funding context while realized funding cost remains
entry-rate based. These were recorded in `ISSUE-R106-020`.

Validation passed:

- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` with 443 passed
- `git diff --check` with no whitespace errors, only inherited CRLF warnings

Stage report:
`docs/stage_reports/STAGE_R106_LEAD_ENTRY_EXIT_SIEVE_REPORT.md`
