# WPR106-75 - Venue-First No-RSI KNN Four-Bar Lead Research

## Purpose

Broaden the WPR106-74 sparse-filter follow-up into a data-first venue and KNN
lead-discovery packet. The packet tests whether no-RSI KNN feature packs and a
four-bar-after-signal-close horizon can produce a durable research lead for
BTCUSDT or ETHUSDT, while documenting which new venue source should be pursued
for future intake.

## Scope

Allowed edit paths:

- `docs/work_packets/WPR106-75-venue-first-no-rsi-knn-four-bar.md`
- `docs/stage_reports/STAGE_R106_VENUE_FIRST_NO_RSI_KNN_FOUR_BAR_REPORT.md`
- `docs/research_knowledge/WPR106-75-venue-scorecard.md`
- `configs/research/no_rsi_knn_four_bar_btcusdt_r106_v1.json`
- `configs/research/no_rsi_knn_four_bar_ethusdt_r106_v1.json`
- `configs/research/no_rsi_knn_four_bar_matrix_btcusdt_r106_v1.json`
- `configs/research/no_rsi_knn_four_bar_matrix_ethusdt_r106_v1.json`
- `src/tradingbotsuite/data/contracts.py`
- `src/tradingbotsuite/research/archive_sources.py`
- `src/tradingbotsuite/research/hmm_knn.py`
- `src/tradingbotsuite/research/hmm_knn_experiments.py`
- `src/tradingbotsuite/strategies/hmm_knn/config.py`
- `src/tradingbotsuite/research/knn_four_bar.py`
- `tests/contracts/test_data_contracts.py`
- `tests/tradingbotsuite/test_archive_sources.py`
- `tests/tradingbotsuite/test_data_pipeline.py`
- `tests/tradingbotsuite/test_hmm_knn.py`

Allowed generated research-output paths:

- `data/research/hmm_knn_four_bar/**`

Read-only reference paths:

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- `docs/stage_reports/STAGE_R106_SPARSE_ENTRY_FILTER_LAYER_REPORT.md`
- `configs/research/sparse_entry_filter_btcusdt_r106_v1.json`
- `data/research/historical_cycles/sparse_entry_filter_btcusdt_r106_v1/**`
- `configs/v2_btc_hmm_multi_knn_research.json`
- `src/tradingbotsuite/research/deterministic_datasets.py`
- `src/tradingbotsuite/strategies/hmm_knn/**`

Out of scope:

- Broad venue downloads or provider ingestion implementation.
- Candidate-pack creation or promotion artifacts.
- Live, paper, order-placement, sizing, runtime-mode, or live-config behavior.
- Treating registered-only venue data as candidate-ready.
- RSI-driven core model search.
- Broad KNN grids or 50-hour sweeps.

## Plan

1. Register `okx_archive` as a diagnostic-only, registered-only source surface
   with provider capability metadata.
2. Write a venue scorecard ranking OKX first, Bybit second, Hyperliquid as
   diagnostic context, and Deribit/options as a later volatility-context lane.
3. Add no-RSI KNN feature packs for price close path, price/vol/flow, and perp
   context.
4. Add `uniform` KNN neighbor weighting and keep distance modes to the current
   Lorentzian, Euclidean robust-z, and cosine implementations.
5. Add reusable four-bar horizon helpers that map 15m to 1h, 1h to 4h, and
   mark 4h to 16h as diagnostic-only unless later holding-window support is
   explicitly added.
6. Add compact BTCUSDT/ETHUSDT KNN matrix specs with no-RSI features,
   explicit neighbor counts, regime modes, and four-bar horizon metadata.
7. Run JSON/spec checks and focused KNN/data contract validation. Run compact
   matrix commands only when a compatible local dataset is available; otherwise
   record the blocker in the report.

## Research Boundary

All outputs are research-only, observe-only, and promotion-disabled. This
packet may select the next validation or data-intake direction, but it cannot
create candidate packs, live/paper readiness, sizing changes, runtime changes,
order placement, or promotion claims.
