# Agent Guide

This branch is controlled by the orchestrator stage ledger.

## Branch role

`research/v3-experimental-engine` is the research and experimentation branch. It owns provider intake, manifests, feature construction, strategy research, backtesting, HMM/KNN experiments, optimizer work, and research UI work.

## Active stage rules

- Check `docs/ORCHESTRATOR_STAGE_LEDGER.md` before starting work.
- Write a work packet before coding.
- Keep changes inside the allowed paths listed by the work packet.
- Update `docs/KNOWN_ISSUES.md` when a blocking risk is discovered.
- Do not advance a stage while any P0 issue is open or four or more P1 issues are unresolved.

## Research boundary

- Research outputs are not live signals.
- Research artifacts must stay `research_only`, `observe_only`, and `promotion_ready: false` unless a later promotion process changes them.
- Research modules must not import live order-placement adapters.
- Research jobs must not place orders, change live runtime mode, or write live configuration.
- Performance claims require reproducible manifests and validation evidence.

## Validation baseline

Use focused validation for scoped work and broaden tests when shared contracts change:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```
