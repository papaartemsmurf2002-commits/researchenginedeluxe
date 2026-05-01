# Branch Purpose: research/v3-experimental-engine

This branch is the research and experimentation branch for TradingBotSuite.

## Source

- Created from: `codex/hmm-knn-research-package`
- Created for: Stage 0 governance and later Stage 3 through Stage 9 research platform work.

## Purpose

This branch owns fast, reproducible research: provider/archive intake, normalized manifests, point-in-time feature construction, deterministic backtesting, baseline strategies, HMM/KNN as a configurable research plugin, experiment orchestration, optimization, and research UI.

## Boundaries

- Research outputs are not live signals.
- All research artifacts must remain `research_only` and `observe_only` unless a later promotion process explicitly changes their status.
- Research code must not import live order-placement adapters.
- Research jobs must not place orders, alter live runtime mode, or write live configuration.
- WT3D is a feature candidate, not a required alpha source.

## Next eligible work

Stage 1 repo cartography must run before Stage 2 contracts or any research implementation stages advance. Stage 3 through Stage 9 remain sequential after the Stage 2 gate.
