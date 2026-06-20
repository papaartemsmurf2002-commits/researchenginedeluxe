# WPR106-372 - Sandbox Throughput Telemetry Report

## Status

closed

## Objective

Add measurement-only throughput telemetry for one-command rapid strategy
sandbox iterations and a report command that summarizes existing iteration
manifests into reproducible runtime, cache, memory, artifact-byte, and
bottleneck diagnostics.

## Dependencies

- `RAPID_STRATEGY_SANDBOX_AUDIT.md`
- `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md`
- `docs/work_packets/WPR106-362-post-audit-sandbox-safety-coherence.md`
- `docs/work_packets/WPR106-369-sandbox-end-to-end-venue-expansion-fixture-smoke.md`
- `docs/work_packets/WPR106-371-sandbox-next-action-dashboard.md`

## Allowed paths

- `src/tradingbotsuite/research_sandbox/market_data.py`
- `src/tradingbotsuite/research_sandbox/iteration.py`
- `src/tradingbotsuite/research_sandbox/throughput.py`
- `src/tradingbotsuite/research_sandbox/__init__.py`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/research/command_registry.py`
- `tests/research_sandbox/**`
- `tests/live/test_cli_boundary.py`
- `docs/contracts/sandbox_research_contract.md`
- `docs/contracts/boundary_contract.md`
- `docs/work_packets/WPR106-372-sandbox-throughput-telemetry-report.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_THROUGHPUT_TELEMETRY_REPORT.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Boundary constraints

- Measurement and reporting only.
- Do not change sandbox ranking, trial identity, strategy signals, exit/fill
  semantics, evidence-request selection, archive routing, preflight blockers,
  or validation behavior.
- Do not execute strict validation, write candidate packs, create paper/live
  artifacts, define sizing, place orders, change runtime mode, write live
  configuration, claim candidate evidence, or claim promotion readiness.
- Throughput reports must not claim speedup unless a later packet adds repeated
  benchmark baselines with identical output identity evidence.

## Acceptance criteria

- One-command sandbox iteration manifests record bounded throughput telemetry:
  total runtime, per-stage runtime, cache counters, rows loaded after 2024+
  filtering, source bytes read, workers requested/used, and peak memory when
  measurable.
- A report command summarizes existing iteration manifests under the configured
  research output root and writes compact JSON/Parquet throughput reports.
- Reports include missing-telemetry blockers for older iteration manifests and
  a bottleneck ranking from recorded stage timings.
- Cache counters distinguish frame and source-integrity cache hits/misses
  without serializing cached frames or integrity contents.
- CLI input/output paths remain contained under the configured research output
  root.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "throughput_telemetry"
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

## Stop conditions

- Any telemetry changes trial IDs, rankings, evidence requests, blocker
  reasons, validation behavior, or artifact authority.
- Any report reads or writes outside the configured research output root.
- Any report claims candidate evidence, promotion readiness, speedup,
  candidate-pack eligibility, paper/live behavior, sizing, order placement,
  runtime-mode changes, or live config writes.

## Exit evidence

- Added measurement-only throughput telemetry to one-command sandbox iteration
  manifests, including total runtime, per-stage runtime, market-data frame and
  source-integrity cache counters, 2024+ rows loaded, source bytes read,
  workers requested/used, and traced peak memory when measurable.
- Added `summarize-rapid-strategy-sandbox-throughput`, a research command that
  scans existing iteration manifests under the configured research output root
  and writes `sandbox_throughput_report.json`,
  `sandbox_throughput_iteration_summary.parquet`, and
  `sandbox_throughput_stage_summary.parquet`.
- Reports include missing-telemetry blockers for older manifests, cache
  summaries, artifact-byte estimates, stage runtime totals, and bottleneck
  ranking while setting `speedup_claimed: false`.
- Focused validation passed:
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "throughput_telemetry"`
  reported 3 passed / 188 deselected;
  `python -m compileall -q src\tradingbotsuite` passed;
  `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`
  reported 26 passed;
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  reported 205 passed;
  `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  reported 461 passed;
  `git diff --check` passed with existing LF-to-CRLF warnings only.
- The packet does not alter trial identity, ranking, strategy signals,
  archive routing, blocker semantics, evidence-request selection, strict
  validation, candidate packs, paper/live behavior, sizing, order placement,
  runtime mode, live configuration, candidate-evidence semantics, or promotion
  state.
