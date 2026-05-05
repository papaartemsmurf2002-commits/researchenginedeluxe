# WPR29-01 Benchmark CLI Gate Completeness

Status: closed
Owner: Codex Research Agent
Stage: Stage R29 benchmark CLI gate completeness
Opened: 2026-05-04
Closed: 2026-05-04

## Objective

Historical research-cycle benchmark reports already compute a strict `benchmark_gate`, but the CLI helper can still return a successful payload when that gate is failed or evidence-incomplete. This packet makes benchmark CLI behavior fail closed by default and records gate details in the command payload.

## Allowed paths

- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR29-01-benchmark-cli-gate-completeness.md`
- `docs/stage_reports/STAGE_R29_BENCHMARK_CLI_GATE_COMPLETENESS_REPORT.md`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/research_cycle/benchmark.py`
- `tests/historical/test_research_cycle_benchmark.py`
- `tests/live/test_preflight.py`

## Non-goals

- No live, paper, shadow, testnet, canary, promotion, order-placement, or capital allocation work.
- No new benchmark engine architecture.
- No large/manual benchmark execution in this packet.
- No performance claims beyond local benchmark report evidence.

## Implementation plan

1. Derive benchmark CLI tier choices from the benchmark tier registry.
2. Make benchmark CLI payload include `benchmark_gate_passed`, `evidence_complete`, failure reasons, and skipped reasons.
3. Make benchmark CLI fail closed when the gate fails, unless a deliberate report-only override is supplied.
4. Adjust default repeat or explicit override behavior so default CLI usage can satisfy repeat evidence.
5. Add tests for gate-failed CLI behavior, override/report-only behavior, payload evidence, and medium tier registry coverage.
6. Record validation evidence and close the packet.

## Exit criteria

- Benchmark CLI does not silently succeed on a failed or evidence-incomplete gate.
- CLI payload exposes gate pass/fail and evidence completeness details.
- Medium benchmark tier remains covered by tests without requiring a large runtime in normal focused validation.
- Live preflight still rejects benchmark commands in live mode.
- Focused benchmark/live tests, compile, contracts, and diff check pass.

## Completion evidence

- CLI tier choices are derived from `BENCHMARK_TIERS`.
- CLI default repeat is now `2`, matching the repeat evidence needed by the strict benchmark gate.
- CLI payload includes `benchmark_gate_passed`, `evidence_complete`, `failure_reasons`, and `skipped_reasons`.
- CLI raises on failed/evidence-incomplete gates unless `--allow-failed-gate` is explicitly supplied for report-only output.
- Tests cover failed-gate default behavior, report-only override behavior, passed-gate payloads, and medium tier registry coverage.
- Validation:
  - `python -m compileall -q src/tradingbotsuite`
  - `$env:PYTHONPATH='src'; python -m pytest tests\historical\test_research_cycle_benchmark.py tests\live\test_preflight.py -q`
  - `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - `git diff --check` completed with line-ending warnings only.
