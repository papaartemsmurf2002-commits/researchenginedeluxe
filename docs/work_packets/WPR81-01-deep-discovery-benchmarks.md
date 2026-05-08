# WPR81-01 Deep Discovery Benchmarks

Status: in_progress
Owner: Codex Research Agent
Stage: R81 deep discovery benchmarks

## Objective

Add research-only discovery benchmark tiers for quick, standard, and deep discovery runs. Benchmarks must validate stop/resume behavior, snapshot readability, immutable ledger consistency, and artifact overhead without changing discovery math, historical-cycle semantics, candidate-pack gates, promotion behavior, or live execution.

## Allowed paths

- `src/tradingbotsuite/research_discovery/**`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/research/command_registry.py`
- `configs/discovery/**`
- `tests/research_discovery/**`
- `tests/live/test_preflight.py`
- `docs/work_packets/WPR81-01-deep-discovery-benchmarks.md`
- `docs/stage_reports/STAGE_R81_DEEP_DISCOVERY_BENCHMARKS_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`

## Non-goals

- Do not add new signal math, HMM fitting, KNN distance behavior, exit policies, strategy plugins, optimizer gates, candidate-pack validation rules, or checked BTCUSDT/ETHUSDT historical-cycle config changes.
- Do not claim live readiness, production speedup, profitability, or promotion readiness.
- Do not write checked benchmark output artifacts under `data/research`.

## Implementation plan

1. Add `research_discovery.benchmark` with quick, standard, and deep tier specs and thresholds.
2. Generate isolated benchmark specs under a caller-provided output directory or `research.output_dir/benchmarks/research_discovery/<tier>`.
3. Run each tier both uninterrupted and interrupted/resumed, then compare completed ledger hashes.
4. Read every snapshot and report snapshot count, latest snapshot, and readability/integrity evidence.
5. Write `discovery_benchmark_report.json` with research-only gate semantics.
6. Add CLI command `benchmark-discovery-run` and register it as a research command for live preflight rejection.
7. Add focused tests for report contents, resume equality, failed gate behavior, CLI payload, and live-command registry coverage.

## Validation target

- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/research_discovery -q`
- `$env:PYTHONPATH='src'; python -m pytest tests/live/test_preflight.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
