# WPR106-80 - Monte Carlo Exit And Sizing Sieve

## Purpose

Revisit the latest R106 research evidence with offline Monte Carlo and exit
math before spending more optimizer compute. This packet checks whether any
current entry/exit row has enough after-cost robustness to justify expensive
optimization, and whether a fixed TP/SL plus 1.5x Martingale overlay is
mathematically acceptable under a taker commission of 0.0432% per side with
funding ignored.

## Scope

Allowed edit paths:

- `docs/work_packets/WPR106-80-monte-carlo-exit-sizing-sieve.md`
- `docs/stage_reports/STAGE_R106_MONTE_CARLO_EXIT_SIZING_SIEVE_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research/monte_carlo_exit_sizing.py`
- `tests/tradingbotsuite/test_monte_carlo_exit_sizing.py`

Allowed generated research-output paths:

- `data/research/monte_carlo_exit_sizing/wpr106_80/**`

Read-only evidence and reference paths:

- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- `docs/KNOWN_ISSUES.md`
- `docs/stage_reports/STAGE_R106_SPARSE_ENTRY_FILTER_LAYER_REPORT.md`
- `docs/stage_reports/STAGE_R106_LOCAL_BINANCE_ARCHIVE_FOUR_BAR_MAPPER_REPORT.md`
- `docs/stage_reports/STAGE_R106_FOUR_BAR_LEAD_DISCOVERY_BRIDGE_REPORT.md`
- `data/research/historical_cycles/sparse_entry_filter_btcusdt_r106_v1/**`
- `data/research/hmm_knn_four_bar_archive_mapping/wpr106_79_full_local_archive_map/**`
- `src/tradingbotsuite/backtesting/**`

Out of scope:

- Candidate-pack creation, paper/live artifacts, or promotion artifacts.
- Live, paper, order-placement, runtime-mode, live-configuration, or actual
  position-sizing behavior.
- Provider downloads, fixture rewrites, catalog rebuilds, or new venue intake.
- Large historical-cycle reruns or broad KNN/exact-discovery sweeps.
- Treating offline Monte Carlo or Martingale diagnostics as candidate-ready
  evidence.

## Plan

1. Translate current exit-strategy literature into testable offline candidates:
   fixed TP/SL with vertical timeout, volatility-aware barriers, trailing stops,
   and optimal-stopping/RL exits as deferred model families.
2. Add an offline analyzer over existing trade artifacts that:
   - recalculates returns using taker-only commission of 0.0432% per side and
     funding ignored;
   - runs bootstrap Monte Carlo over fixed-size and 1.5x Martingale overlays;
   - reports loss-streak and drawdown distributions;
   - audits conservative 1:2 fixed TP/SL feasibility from MAE/MFE evidence.
3. Run the analyzer on current BTC sparse positive rows and include WPR106-79
   KNN larger-validation summary rows as rejected non-candidates.
4. Write research-only JSON/CSV/Markdown reports.
5. Run focused tests plus baseline compile/contracts if time permits.

## Research Boundary

All outputs remain `research_only: true`, `observe_only: true`, and
`promotion_ready: false`. The packet may reject or identify follow-up research
directions, but it cannot size positions, place orders, alter runtime mode,
write live configuration, create candidate packs, or claim promotion readiness.
