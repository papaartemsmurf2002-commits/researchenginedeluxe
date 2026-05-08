# WPR79-01 Discovery Exit Lab

Stage: R79 discovery exit lab
Owner: Codex Research Agent
Status: closed
Created: 2026-05-08

## Goal

Add a discovery-side exit lab that compares fixed holding, barriers,
funding/OI-aware exits, HMM/KNN exit candidates, and trailing/risk-control
policies only for entry candidates with enough trade density.

## Allowed Paths

```text
src/tradingbotsuite/research_discovery/**
configs/discovery/**
tests/research_discovery/**
docs/work_packets/WPR79-01-discovery-exit-lab.md
docs/stage_reports/STAGE_R79_DISCOVERY_EXIT_LAB_REPORT.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- Do not add or modify backtest execution policies in this packet.
- Do not alter checked BTCUSDT/ETHUSDT historical-cycle configs or checked
  historical-cycle artifacts.
- Run exit comparisons only when entry candidates meet configured trade-density
  floors.
- Keep all outputs `research_only`, `observe_only`, and `promotion_ready:
  false`.
- Do not add live execution, promotion behavior, candidate-pack bridging,
  operator UI behavior, sizing, or order placement.

## Required Output

- Discovery-side exit lab dataclasses and functions.
- Config under `configs/discovery/`.
- Artifact writer for exit lab rows, family summaries, and manifest evidence.
- Focused tests for trade-density gating, fixed/barrier/funding/OI/trailing
  comparisons, pending HMM/KNN exit evidence, guardrail flags, and artifact
  boundary flags.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
```

Run contracts before closing if shared contracts change.

## Close Evidence

- Added `tradingbotsuite.research_discovery.exit_lab` with a research-only exit
  lab evaluator.
- Added checked discovery config `configs/discovery/discovery_exit_lab_v4.json`.
- Exit comparisons now require fixed-holding entry candidates to pass
  trade-density floors before testing barrier, funding/OI, HMM/KNN, or
  trailing/risk-control exit families.
- Added artifact writer for `discovery_exit_lab_manifest.json`,
  `discovery_exit_lab_matrix.parquet`, and
  `discovery_exit_family_summary.parquet`.
- Added focused tests for trade-density gating, exit-family comparisons,
  pending HMM/KNN exit evidence, family summaries, boundary flags, and config
  validation.
- Validation passed on 2026-05-08 with compile and discovery tests.
