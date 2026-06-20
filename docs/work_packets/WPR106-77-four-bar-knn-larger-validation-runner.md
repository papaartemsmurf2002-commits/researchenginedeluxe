# WPR106-77 - Four-Bar KNN Larger Validation Runner

## Purpose

Turn the WPR106-76 larger-validation decision into a reproducible
research-only runner that can be launched from the CLI or queued from the
operator Research UI without blocking this agent on long local compute.

## Scope

Allowed edit paths:

- `docs/work_packets/WPR106-77-four-bar-knn-larger-validation-runner.md`
- `docs/stage_reports/STAGE_R106_FOUR_BAR_KNN_LARGER_VALIDATION_RUNNER_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/contracts/boundary_contract.md`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/research/command_registry.py`
- `src/tradingbotsuite/research/knn_four_bar.py`
- `src/tradingbotsuite/research/knn_four_bar_validation.py`
- `src/tradingbotsuite/web/operator.py`
- `src/tradingbotsuite/web/templates/research.html`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `tests/tradingbotsuite/test_operator_ui.py`

Allowed generated research-output paths:

- `data/research/hmm_knn_four_bar_validation/**`

Read-only reference paths:

- `AGENTS.md`
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- `docs/work_packets/WPR106-76-four-bar-lead-discovery-bridge.md`
- `docs/stage_reports/STAGE_R106_FOUR_BAR_LEAD_DISCOVERY_BRIDGE_REPORT.md`
- `configs/research/no_rsi_knn_four_bar_btcusdt_r106_v1.json`
- `configs/research/no_rsi_knn_four_bar_ethusdt_r106_v1.json`
- `data/research/hmm_knn_four_bar/**`
- `data/research/fixtures/btcusdt_public_archive_multi_window_v1/**`
- `data/research/fixtures/ethusdt_public_archive_multi_window_v1/**`
- `src/tradingbotsuite/research/hmm_knn.py`
- `src/tradingbotsuite/research/hmm_knn_experiments.py`
- `src/tradingbotsuite/strategies/hmm_knn/**`

Out of scope:

- Candidate-pack creation, paper/live artifacts, promotion artifacts, or
  promotion-ready claims.
- Live, paper, order-placement, sizing, runtime-mode, or live-configuration
  behavior.
- New provider or OKX/Bybit intake implementation.
- Broad KNN grid expansion beyond the WPR106-76 selected validation rows.
- RSI core features or RSI-driven lead claims.

## Plan

1. Add a durable larger-validation runner that builds deterministic BTC/ETH
   validation datasets from existing fixture packs, generates narrow no-RSI
   experiment specs, runs them through the existing HMM/KNN experiment runner,
   and writes a consolidated research-only manifest.
2. Limit validation rows to the WPR106-76 decision set: BTC primary
   `1h -> 4h` price/vol/flow KNN, BTC `15m -> 1h` price/vol/flow top-score
   source, and ETH comparator/top-score source rows.
3. Add a CLI command that can run the long validation with bounded worker count,
   sample size, cache reuse, and optional matrix skipping for command/script
   generation.
4. Wire one operator Research UI button to queue the same research-only job if
   it fits the existing guarded job service.
5. Add focused tests for command registration, spec generation, manifest
   boundaries, queue wiring, and help output.

## Research Boundary

All outputs remain `research_only: true`, `observe_only: true`, and
`promotion_ready: false`. Larger validation evidence is still research evidence
only; it cannot place orders, write live config, change runtime mode, size
positions, create candidates, or claim promotion readiness.
