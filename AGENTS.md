# Agent Guide

This branch is controlled by the orchestrator stage ledger.

## Branch role

`research/v3-experimental-engine` is the research and experimentation branch.
Its active v2 direction is a research-only, data-first, multi-instrument
Hyperliquid-perpetual research platform with compatible multi-venue comparison
support. It owns provider/archive intake, manifests, feature construction,
strategy research, backtesting, HMM/KNN experiments, optimizer work, rapid
sandbox work, Lead Book preparation, audit-by-chunk migration, and research UI
work.

## Active stage rules

- Check `docs/ORCHESTRATOR_STAGE_LEDGER.md` before starting work.
- Read `docs/PRODUCT_SCOPE.md`, `docs/V2_DECISION_REGISTER.md`,
  `docs/V2_NO_TOUCH_PATHS.md`, and `docs/audit/V2_AUDIT_INDEX.md` before v2
  implementation work.
- Read `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md` before broad package,
  dependency, data, feature, backtest, research-cycle, artifact, or live-boundary
  changes.
- Write a work packet before coding.
- Keep changes inside the allowed paths listed by the work packet.
- Update `docs/KNOWN_ISSUES.md` when a blocking risk is discovered.
- Do not advance a stage while any P0 issue is open or four or more P1 issues are unresolved.
- BTC and ETH are fixture, smoke-test, reference, and legacy evidence symbols;
  they are not the full v2 product scope.

## Research boundary

- Research outputs are not live signals.
- Research artifacts must stay `research_only`, `observe_only`, and `promotion_ready: false` unless a later promotion process changes them.
- Research modules must not import live order-placement adapters.
- Research jobs must not place orders, change live runtime mode, or write live configuration.
- V2 research commands and artifacts must not imply paper-ready, live-ready,
  trade-ready, order-ready, sizing-ready, signal-ready, candidate-pack-ready,
  or promotion-ready status.
- Performance claims require reproducible manifests and validation evidence.

## Validation baseline

Use focused validation for scoped work and broaden tests when shared contracts change:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```
