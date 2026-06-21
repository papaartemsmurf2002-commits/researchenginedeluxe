# Branch Purpose: research/v3-experimental-engine

This branch is the research and experimentation branch for ResearchEngineDeluxe
and TradingBotSuite-compatible code.

## Source

- Created from: `codex/hmm-knn-research-package`
- Created for: Stage 0 governance and later Stage 3 through Stage 9 research platform work.

## Purpose

The active v2 purpose is a research-only, data-first, multi-instrument
perpetual-futures research platform. The default product direction is
Hyperliquid-first: instruments above USD 5,000,000 daily notional volume,
owned archives, as-of universe snapshots, 2024+ research evidence, 6+ usable
months, 12-month preference, 0.98 coverage, dynamic lockbox exclusion,
declarative strategy evaluation, append-only experiment ledger, Lead Book, and
audit-by-chunk migration.

The branch also owns useful legacy and transition research surfaces: provider
and archive intake, normalized manifests, point-in-time feature construction,
deterministic backtesting, baseline strategies, HMM/KNN research plugins,
experiment orchestration, optimization, rapid sandbox tooling, and research UI.

## Boundaries

- Research outputs are not live signals.
- All research artifacts must remain `research_only` and `observe_only` unless a later promotion process explicitly changes their status.
- Research code must not import live order-placement adapters.
- Research jobs must not place orders, alter live runtime mode, or write live configuration.
- BTC and ETH are fixture, smoke-test, reference, and legacy evidence symbols,
  not the full v2 product scope.
- Paper/live/order/sizing/promotion readiness is not a future option for this
  research branch without a separate explicit human-approved process outside
  the v2 roadmap.
- WT3D is a feature candidate, not a required alpha source.

## Next eligible work

Follow the active ledger and work-packet rules. For v2 work, read
`docs/PRODUCT_SCOPE.md`, `docs/V2_DECISION_REGISTER.md`,
`docs/V2_NO_TOUCH_PATHS.md`, and `docs/audit/V2_AUDIT_INDEX.md` before editing.
The next v2 implementation work after Phase 0 is package skeleton,
schema-first contracts, and import-boundary tests; do not start UI replacement,
paper/live features, arbitrary Python strategy plugins, or broad cross-venue
work before the Hyperliquid M1 research loop is stable.
