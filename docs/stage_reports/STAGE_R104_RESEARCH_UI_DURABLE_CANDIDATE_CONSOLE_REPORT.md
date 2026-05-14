# Stage R104 Research UI Durable Candidate Console Report

Date: 2026-05-14
Work packet: `docs/work_packets/WPR104-01-research-ui-durable-candidate-console.md`
Stage status: control path complete; empirical candidate validation still pending

## Summary

WPR104-01 moved the active Research console from latest-window-first diagnostics
to the durable R104 candidate-validation path. The UI now starts from BTC/ETH
public-archive fixture readiness, durable historical cycles, durable discovery
runs, and a UI-backed discovery-to-candidate-pack eligibility review. The work
keeps all artifacts `research_only`, `observe_only`, and `promotion_ready:
false`; it does not create a candidate pack or claim candidate-ready
performance.

## Implemented

- Added durable R104 cycle specs:
  - `configs/research/full_cycle_btcusdt_durable_public_archive_r104_v1.json`
  - `configs/research/full_cycle_ethusdt_durable_public_archive_r104_v1.json`
- Updated BTC/ETH blueprint activation so durable R104 configs supersede the
  prior diagnostic/blocked blueprint cycles.
- Updated discovery presets to use durable BTC/ETH public-archive fixture
  packs, including a bounded `durable_aggtrade_orderflow_proxy` feature-column
  set and fixture-sized validation floors.
- Added `OperatorConsoleService.r104_readiness_diagnostics()` and
  `/api/operator/research/r104-readiness`.
- Added the operator job and route for
  `evaluate-discovery-candidate-pack-eligibility`, with CSRF/session checks,
  research-root manifest path validation, service-layer execution, and isolated
  output under the configured research root.
- Extended artifact indexing to fail soft on malformed JSON and to surface
  discovery exit lab, multiple-testing, validation-floor, and candidate-pack
  eligibility artifacts.
- Reworked `research.html` around durable readiness, visible settings,
  recommended run order, BTC/ETH durable cycle/discovery buttons, candidate
  eligibility review, better maturity/lead counting, and secondary diagnostics
  for provider pipeline and signal-history tools.

## Validation

- `python -m compileall -q src/tradingbotsuite`
- Research page JavaScript parsed with Node `new Function(...)`
- `$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_operator_ui.py -q`
  - `38 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests/research_discovery/test_discovery_spec.py tests/research_discovery/test_discovery_feature_sets.py -q`
  - `14 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests/integration/test_research_ui.py -q`
  - `6 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_strategy_contracts.py tests/contracts/test_import_boundaries.py -q`
  - `286 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts tests/historical tests/research_discovery -q`
  - `624 passed`

## Remaining R104 Work

The branch is not empirically finished. The next step is to run the durable
BTC/ETH cycles and discovery jobs through the UI, wait for completed manifests,
run candidate eligibility review, and inspect blockers. A research-only
candidate can only move forward if exit lab, multiple-testing, validation
floors, candidate-pack gates, source provenance, side/split/regime evidence,
and cost/funding stress all pass.
