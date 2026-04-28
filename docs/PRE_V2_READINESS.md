# Pre-V2 Readiness

Date: April 10, 2026

## Summary

The current codebase is in a good handoff state for v2 work.

V2 should be understood as the BTC-first TradingView-to-acceptance phase, not as a TradingView-free phase.

What is solid:

- BTC-first v1 execution path is live-capable and tested
- webhook, manual, paper, shadow, and live smoke paths are all present
- Binance bar, trade, top-of-book, and diff-depth infrastructure are in place
- Hyperliquid live stack has working entry, stream, reconcile, and close verification
- persistence and replay primitives exist for decisions, tickets, trade state, and events
- the code now has a canonical system snapshot used by both manual mode and the API

## Last-Pass Code Analysis

No stop-the-line v1 bugs were found in this pass.

The main remaining gaps are strategic or research-facing, not foundational:

- acceptance logic is still a simple hard-veto baseline rather than a calibrated meta-label model
- funding, premium, open-interest, and realized-volatility context are not yet in the feature packet
- diff-depth infrastructure exists, but true multi-level OFI is still a v2 research task
- adverse-selection and alpha-decay exits are not yet implemented
- health and monitoring surfaces exist, but long-run metrics storage is still lightweight
- TradingView-origin BTC signal provenance, history quality, and research integration still need to be carried through the V2 acceptance workflow

## V2 Should Build On These Interfaces

Most stable extension points:

- [engine.py](c:/Users/papaa/Music/tradingbotsuite/src/tradingbotsuite/core/engine.py)
  The decision packet and system snapshot surfaces are the best place to grow feature and model inputs.
- [binance.py](c:/Users/papaa/Music/tradingbotsuite/src/tradingbotsuite/adapters/binance.py)
  This is the correct place to add funding, premium, OI, richer queue analytics, and true OFI research.
- [execution.py](c:/Users/papaa/Music/tradingbotsuite/src/tradingbotsuite/adapters/execution.py)
  This is the correct place for execution-quality attribution and richer live reconcile telemetry.
- [sqlite_store.py](c:/Users/papaa/Music/tradingbotsuite/src/tradingbotsuite/persistence/sqlite_store.py)
  This is the correct place to add v2 metrics/event tables if the replay model expands.

## Recommended V2 Priority Order

1. Add feature-packet enrichment:
   funding, premium, open interest, realized volatility, and time-to-funding.
2. Keep the BTC TradingView signal path first-class inside research:
   provenance handling, signal-history bootstrapping, and dataset integration around TradingView-origin BTC signals.
3. Add research-grade acceptance modeling:
   calibrated meta-label baseline with stored model/calibration versions.
4. Add sophisticated exit supervision:
   adverse-selection and alpha-decay exits on top of the existing triple barrier.
5. Add richer monitoring:
   slippage attribution, latency buckets, rejection distributions, calibration drift, and basis history.
6. Only then expand into V3 work:
   ETH-specific modeling, cross-asset ETH context, cleaner GUI/operator tweaking, and broader tuning instrumentation.

## Guardrails For V2

- Keep the exact same feature code usable in replay, paper, and live modes.
- Add new model outputs as features and packet fields before making them hard gates.
- Preserve fail-closed behavior on stale data, reconcile uncertainty, and live ambiguity.
- Prefer additive tables and packet fields over mutating existing persistence semantics.
- Keep BTC as the primary optimization target until the acceptance model and exit stack are stable.
- Treat ETH, GUI-heavy tuning workflows, and broad operator-surface expansion as V3 objectives rather than V2 blockers.
