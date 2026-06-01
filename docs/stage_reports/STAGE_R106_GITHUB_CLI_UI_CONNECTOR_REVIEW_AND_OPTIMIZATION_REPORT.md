# Stage R106 GitHub CLI UI Connector Review And Optimization Report

Date: 2026-06-01

Packet: `WPR106-52-github-cli-ui-connector-review-and-optimization`

## Summary

WPR106-52 installed and verified GitHub CLI support, checked GitHub connector
health, ran a deep code review with subagent support, fixed concrete connector
and research-boundary issues, and reran broad validation.

This packet preserves the research-only boundary. It does not create
candidate-ready claims, emit candidate packs, add live or paper signals, place
orders, write live configuration, change sizing, or authorize promotion.

## Connector Status

- GitHub CLI installed successfully with `winget`.
- `gh version 2.93.0 (2026-05-27)` is available.
- `gh auth status` reports no logged-in GitHub hosts, so PR creation through
  `gh` remains blocked until authentication is completed.
- The desktop GitHub connector still fails during MCP startup handshake with a
  timeout. That is an external connector limitation, not a repository test
  failure.

## Fixes

- Standalone research UI mutating job APIs now require a configured operator
  secret token and reject cross-origin writes.
- The standalone research UI labels the review page as research boundary
  review instead of presenting generic non-promotable manifests as promotion
  candidates.
- Operator artifact indexing skips high-volume `trials/` directories.
- Provider pipeline, research experiment, and historical-cycle output dirs now
  fail closed when they are outside the configured research output root.
- Data-pipeline stage path resolution now prefers the owning spec directory
  before an explicit repo-root fallback, preventing stale launch-CWD files from
  being captured.
- Shuffled-label negative controls block no-effect single-label inputs and
  unchanged shuffled hashes.
- Shifted-context negative controls require unique monotonic timestamps and
  real context columns instead of identifier-only fallbacks.

## Validation

```powershell
python -m compileall -q src\tradingbot src\tradingbotsuite tests
python -m pip check
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q --durations=20
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py tests\test_operator_ui.py tests\integration\test_research_ui.py -q --durations=20
$env:PYTHONPATH='src'; python -m pytest tests\integration\test_research_ui.py tests\tradingbotsuite\test_operator_ui.py tests\tradingbotsuite\test_data_pipeline.py tests\tradingbotsuite\test_experiment_runner.py tests\historical\test_full_cycle_synthetic.py tests\research_discovery\test_replay_evidence_controls.py -q --durations=20
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_local_fixture_pack.py::test_full_cycle_materializes_fixture_context_families_and_cache_identity tests\historical\test_full_cycle_local_fixture_pack.py::test_full_cycle_consumes_provider_builder_context_fixture_pack tests\historical\test_research_cycle_benchmark.py::test_research_cycle_benchmark_report_contains_research_only_gate_metrics tests\historical\test_research_cycle_benchmark.py::test_research_cycle_benchmark_cleans_stale_repeat_artifacts tests\historical\test_research_cycle_benchmark.py::test_research_cycle_benchmark_resolves_relative_output_paths tests\historical\test_research_cycle_benchmark.py::test_research_cycle_benchmark_medium_tier_bounded_execution -q --durations=20
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py::test_operator_research_job_routes_default_to_active_catalog_specs -q -W error::pytest.PytestUnhandledThreadExceptionWarning --durations=10
$env:PYTHONPATH='src'; python -m pytest -q --durations=30
git diff --check
```

Results:

- Compile: passed.
- `python -m pip check`: no broken requirements found.
- Contracts: 441 passed.
- Focused operator/UI connector suite: 100 passed.
- Focused edited-path suite: 146 passed, 2 environment warnings.
- Exact full-suite failure rerun after test-root alignment: 6 passed.
- Operator aiosqlite warning reproduction with warning-as-error: 1 passed.
- Final full suite: 1552 passed, 1 skipped, 2 warnings in 790.63 seconds.
- `git diff --check`: passed with line-ending warnings only.

## Boundary Result

- Candidate eligible rows remain zero for current replay evidence.
- No candidate pack was written.
- `ISSUE-R104-001` remains open.
- No P0 issue was introduced.
- No candidate-ready, paper-ready, live-ready, or promotion-ready claim exists.
- No live/paper/order-placement/sizing/runtime-mode/live-config behavior was
  added.
