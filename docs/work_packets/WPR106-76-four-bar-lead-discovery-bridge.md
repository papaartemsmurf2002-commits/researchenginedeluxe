# WPR106-76 - Four-Bar Lead-Discovery Bridge

## Purpose

Build the smallest durable BTCUSDT/ETHUSDT four-bar event-label dataset layer
needed to run the WPR106-75 no-RSI KNN compact matrices, then use those outputs
to decide whether KNN has an entry-quality lead, needs sparse/cost-aware
filters, or should stop until OKX/Bybit venue-derived feature intake exists.

## Scope

Allowed edit paths:

- `docs/work_packets/WPR106-76-four-bar-lead-discovery-bridge.md`
- `docs/stage_reports/STAGE_R106_FOUR_BAR_LEAD_DISCOVERY_BRIDGE_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/contracts/boundary_contract.md`
- `configs/research/no_rsi_knn_four_bar_matrix_btcusdt_r106_v1.json`
- `configs/research/no_rsi_knn_four_bar_matrix_ethusdt_r106_v1.json`
- `src/tradingbotsuite/research/knn_four_bar.py`
- `src/tradingbotsuite/research/command_registry.py`
- `src/tradingbotsuite/research/hmm_knn.py`
- `src/tradingbotsuite/research/hmm_knn_experiments.py`
- `src/tradingbotsuite/main.py`
- `tests/tradingbotsuite/test_hmm_knn.py`

Allowed generated research-output paths:

- `data/research/hmm_knn_four_bar/**`

Read-only reference paths:

- `AGENTS.md`
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- `docs/stage_reports/STAGE_R106_VENUE_FIRST_NO_RSI_KNN_FOUR_BAR_REPORT.md`
- `docs/stage_reports/STAGE_R106_SPARSE_ENTRY_FILTER_LAYER_REPORT.md`
- `docs/research_knowledge/WPR106-75-venue-scorecard.md`
- `configs/research/no_rsi_knn_four_bar_btcusdt_r106_v1.json`
- `configs/research/no_rsi_knn_four_bar_ethusdt_r106_v1.json`
- `configs/research/sparse_entry_filter_btcusdt_r106_v1.json`
- `data/research/fixtures/btcusdt_public_archive_multi_window_v1/**`
- `data/research/fixtures/ethusdt_public_archive_multi_window_v1/**`
- `data/research/historical_cycles/sparse_entry_filter_btcusdt_r106_v1/**`
- `src/tradingbotsuite/features/**`
- `src/tradingbotsuite/strategies/hmm_knn/**`
- `src/tradingbotsuite/backtesting/**`

Out of scope:

- Candidate-pack creation, paper/live artifacts, promotion artifacts, or
  promotion-ready claims.
- Live, paper, order-placement, sizing, runtime-mode, or live-configuration
  behavior.
- Broad venue downloads or provider ingestion implementation.
- Broad KNN grids or long sweeps beyond the WPR106-75 compact matrices and
  bounded follow-up rows.
- RSI core features. RSI may only appear as an explicit negative control.

## Plan

1. Verify durable BTCUSDT/ETHUSDT fixture coverage and source schemas for 15m
   bars, 1m lower bars, and aggTrade flow proxy context.
2. Add a durable dataset builder that emits dense research events from signal
   close, attaches four completed-bar labels, event-end/purge metadata,
   no-RSI close-path features, compact volatility/range/wick/flow features,
   and explicit missingness for unavailable perp context.
3. Write BTCUSDT and ETHUSDT Parquet datasets and sidecar manifests under
   `data/research/hmm_knn_four_bar/` with `research_only: true`,
   `observe_only: true`, and `promotion_ready: false`.
4. Run the WPR106-75 compact matrix specs on those datasets and summarize
   fixed four-bar entry quality separately from exit quality.
5. Try bounded creative extensions only after the base matrix runs: top-score
   sparse event selection, cooldown/side-balance controls, aggTrade flow gates,
   and missing perp-crowding/funding/OI diagnostics.
6. Choose exactly one next phase: larger validation, sparse-entry/filter
   packet, or venue-intake feature packet.

## Decision Gates

Scale larger validation only if a row has positive costed expectancy and net
return, profit factor above 1.05, at least 150 aggregate trades, at least 40
trades per split, 3 of 4 positive split checks, cost-stress survival at least
70%, no split above 60% of PnL, and no RSI or unimplemented venue dependency.

If KNN improves entry quality but fails costs, the next packet is sparse event
selection and cost-aware filters. If KNN remains negative after durable
four-bar datasets exist, stop KNN tuning and move to OKX/Bybit venue-derived
feature intake.

## Research Boundary

All outputs are research-only, observe-only, and promotion-disabled. This packet
may select the next research direction, but it cannot create candidates,
paper/live readiness, sizing changes, runtime changes, order placement, or
promotion claims.
