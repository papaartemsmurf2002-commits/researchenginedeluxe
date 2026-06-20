# WPR106-73 - Durable Lead Exit Sieve

## Purpose

Continue the research-only strategy search by moving the strongest WPR106-72
latest-window entry/exit leads onto the R106 candidate-depth Binance Vision
public-archive catalog. The immediate question is whether exit design can
improve otherwise weak but promising entry models on durable 2020-2026 BTCUSDT
and ETHUSDT evidence before any larger compute experiment is scheduled.

## Scope

Allowed edit paths:

- `docs/work_packets/WPR106-73-durable-lead-exit-sieve.md`
- `docs/stage_reports/STAGE_R106_DURABLE_LEAD_EXIT_SIEVE_REPORT.md`
- `configs/research/durable_lead_exit_sieve_btcusdt_r106_v1.json`
- `configs/research/durable_lead_exit_sieve_ethusdt_r106_v1.json`
- `docs/KNOWN_ISSUES.md` only if a new blocking risk is found

Allowed generated research-output paths:

- `data/research/historical_cycles/durable_lead_exit_sieve_btcusdt_r106_v1/**`
- `data/research/historical_cycles/durable_lead_exit_sieve_ethusdt_r106_v1/**`
- `data/research/historical_cycles/durable_lead_exit_sieve_*_r106_v1_run_output.json`

Read-only evidence and reference paths:

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- `docs/KNOWN_ISSUES.md`
- `docs/stage_reports/STAGE_R106_LEAD_ENTRY_EXIT_SIEVE_REPORT.md`
- `docs/work_packets/WPR106-72-lead-entry-exit-sieve.md`
- `configs/research/fast_lead_exit_sieve_btcusdt_r106_v1.json`
- `configs/research/fast_lead_exit_sieve_ethusdt_r106_v1.json`
- `data/research/operator_runs/historical_data/refresh-historical-data-catalog-4dfa2700192f4b6fa1fa8fe833668cfb/**`
- `data/research/operator_runs/historical_cycles/r105-*-durable-public-archive-candidate-depth-v1/**`
- `src/tradingbotsuite/backtesting/**`
- `src/tradingbotsuite/research_cycle/**`
- `src/tradingbotsuite/strategies/**`

Out of scope:

- Candidate-pack creation or promotion artifacts.
- Live, paper, order-placement, sizing, runtime-mode, or live-config behavior.
- Historical-data catalog rebuilds or provider downloads.
- Strategy, feature, optimizer, or backtest source-code rewrites.
- Treating this fast durable sieve as candidate-ready acceptance evidence.
- Perp-context, funding-aware, premium, or OI exits on the candidate-depth pack,
  because durable funding/OI/premium context is absent in the active pack.

## Plan

1. Use the active R106 candidate-depth fixture manifests for BTCUSDT and
   ETHUSDT, with synthetic fallback disabled.
2. Keep the matrix compact with explicit optimizer search spaces rather than a
   broad metadata grid.
3. Compare entry models separately from exit models:
   - BTC: WPR106-72 `volatility_breakout_v1` loose 72h lead, strict adjacent
     entry, and 24h horizon cross-check.
   - ETH: WPR106-72 `trend_following_v1` 24h and 72h leads, plus the strongest
     R105 durable fixed-hold trend entry for contrast.
4. Compare fixed holding against the base `simple_runner_v1` 0.005/0.004 exit,
   slower/tighter runner variants where useful, trailing-after-profit,
   max-MAE stop, and the current static close-barrier implementation labelled
   as static barrier evidence only.
5. Keep `top_regions_to_refine` low so split and cost-stress validation is
   reserved for the top aggregate row, making this a sub-hour research node
   rather than a full candidate acceptance pass.
6. Record whether any exit/entry/horizon combination deserves a larger
   validation or optimization experiment.

## Research Boundary

All outputs are research-only, observe-only, and promotion-disabled. This packet
may identify large-compute candidates, but it cannot create candidate packs,
paper/live readiness, sizing changes, runtime changes, or promotion claims.

## Outcome

Completed on 2026-06-08 as a research-only durable sieve.

BTC and ETH configs were completed, JSON-validated, spec-loaded, and expanded
before running. BTC expanded to 28 total rows with 14 explicit target rows; ETH
expanded to 35 total rows with 21 explicit target rows. Durable candidate-depth
cycles completed for both symbols and wrote frozen-entry exit audit artifacts
so exit quality could be judged separately from entry quality.

No target row beat fixed holding and no-trade with coherent durable evidence.
BTC exits reduced losses on the same entries, especially `max_mae_stop`, but
all rows stayed negative. ETH 72h fixed-hold trend had PF above 1.0 and
positive per-trade expectancy on 754 fixed entries, but total net return stayed
negative, no-trade was not beaten, all alternate exits worsened the row, and
gate/cost/split evidence did not support scale.

Decision: stop optimizing runner exits for these dense leads. The next phase
should be a new sparse-entry/filter packet focused on cooldown/top-score event
selection, side-balance control, optional aggTrade flow gating, and sparse
KNN/event gating after transparent filters show evidence. No candidate pack,
paper/live readiness artifact, live config, runtime mode, sizing change, or
promotion claim was created.

Fresh validation passed:

- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed with
  443 tests.
