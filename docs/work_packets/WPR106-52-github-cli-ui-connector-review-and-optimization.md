# Work Packet: WPR106-52 GitHub CLI, UI Connector Review, and Optimization

## Goal

Install and verify GitHub CLI support, check repository/UI connector health,
perform a deep code review and optimization pass, and validate the repository
with broad tests.

This packet is a maintenance, connector, review, and validation packet. It does
not attempt to advance the stage, create candidate-ready claims, emit candidate
packs, or change live/paper execution behavior.

## Current Repo Facts

- Current implementation branch:
  `codex/wpr106-47-full-replay-exit-lab-controls`.
- WPR106-51 has already been committed and pushed to GitHub on the current
  branch.
- `.pytest_cache` files are dirty from local validation and are not source
  artifacts for this packet.
- Root-level handoff prompt files under `docs/NEXT_AGENT_HANDOFF_WPR106_*.md`
  remain unrelated to this packet and should stay unstaged.
- `ISSUE-R104-001` remains the only open P1 issue in
  `docs/KNOWN_ISSUES.md`; no P0 issues are open.

## Allowed Edit Paths

This is a broad audit packet. Edits are allowed only when review or validation
finds a concrete issue:

- `docs/ACTIVE_INDEX.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/STAGE_R106_*.md`
- `docs/work_packets/WPR106-*.md`
- `docs/work_packets/WPR106-*-progress.jsonl`
- `src/tradingbot/**`
- `src/tradingbotsuite/**`
- `tests/**`
- `.github/workflows/**`
- `configs/**`
- `README.md`
- `pyproject.toml`

Generated empirical and performance artifacts under
`data/research/operator_runs/` remain local research evidence outputs and
should stay out of git unless a specific later packet approves them.

## Research Boundary

- Research outputs are not live signals.
- Artifacts must remain `research_only: true`, `observe_only: true`, and
  `promotion_ready: false`.
- This packet must not add live signals, paper signals, order placement, sizing
  behavior, runtime-mode changes, live configuration writes, promotion-ready
  claims, candidate-ready claims, or candidate-pack writes.
- Performance measurements are diagnostic unless a later scoped packet
  explicitly approves a speed claim with parity evidence.

## Review Plan

1. Install and verify `gh`; check authentication and PR publication options.
2. Check desktop/GitHub connector health and record any external connector
   limitation separately from repository validation.
3. Inventory dirty changes and avoid staging unrelated validation cache or
   handoff prompt files.
4. Run static scans for TODO/FIXME markers, skipped tests, unsafe boundary
   terms, live/paper/runtime writes, and common Python failure patterns.
5. Review operator UI and connector-related code paths, then run focused UI and
   connector tests.
6. Run compile, contract, focused high-risk, and full-suite validation.
7. Fix concrete defects or consistency issues found by review or validation and
   add focused tests.
8. Update packet progress and stage-report documentation with validation
   evidence.
9. Stage only intended source/docs/test changes, commit, push, and create a
   draft PR if authenticated tooling is available.

## Acceptance Criteria

- `gh` is installed and version-checked.
- GitHub authentication and desktop connector status are explicitly recorded.
- No open P0 issues are introduced.
- The open P1 count remains below the stage stop threshold unless a blocking
  issue is discovered and documented.
- Compile and contract validation pass.
- Focused UI/connector validation passes or any environment limitation is
  recorded.
- Full-suite or materially equivalent broad validation passes, or any
  environment limitation is recorded.
- `git diff --check` passes, ignoring expected line-ending notices.
- If changes are committed, the pushed branch contains only intended
  source/docs/test changes.

## Implementation Summary

- Installed GitHub CLI with `winget`; `gh version 2.93.0 (2026-05-27)` is
  available in refreshed shells.
- Verified `gh` is not authenticated in this environment; `gh auth status`
  reports no logged-in GitHub hosts.
- Retried the desktop GitHub connector; it still fails during MCP startup
  handshake. This is recorded as an external connector limitation, separate
  from repository validation.
- Hardened the standalone research UI write API:
  - mutating job POSTs now require a configured operator secret token;
  - cross-origin mutating requests are rejected;
  - generic research-only manifests are labeled as boundary review items
    instead of promotion candidates.
- Reduced operator artifact-index overhead by skipping high-volume `trials/`
  directories during recursive manifest scans.
- Hardened research output boundaries:
  - provider pipeline, research experiment, and historical-cycle output dirs
    must stay inside the configured research output root before directories
    are created;
  - data-pipeline stage paths resolve relative to their spec before any
    explicit repo-root fallback, avoiding launch-CWD stale-file capture.
- Tightened negative-control availability checks:
  - shuffled-label controls now block no-effect one-label inputs and unchanged
    shuffled hashes;
  - shifted-context controls now require unique monotonic timestamps and real
    context columns rather than identifier-only fallbacks.
- Added focused regression tests for each hardening change.
- No candidate pack, live, paper, order-placement, sizing, runtime-mode,
  live-config, or promotion behavior was introduced.

## Validation Completed

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
  Warnings were one XGBoost device fallback warning and one non-reproducible
  aiosqlite thread warning; the targeted warning-as-error rerun passed.
- `git diff --check`: passed with line-ending warnings only.

## Staging Notes

- Do not stage `.pytest_cache/v/cache/lastfailed` or
  `.pytest_cache/v/cache/nodeids`; they are tracked local validation cache
  files but are not source artifacts for this packet.
- Do not stage `docs/NEXT_AGENT_HANDOFF_WPR106_47_LONG_RUN_PROMPT.md` or
  `docs/NEXT_AGENT_HANDOFF_WPR106_48_LONG_RUN_PROMPT.md`; they are root-level
  handoff prompts outside this packet's allowed paths.
