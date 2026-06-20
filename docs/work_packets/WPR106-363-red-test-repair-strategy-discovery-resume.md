# WPR106-363 - Red Test Repair For Strategy Metadata And Discovery Resume

## Status

closed

## Objective

Repair the two post-audit full-suite blockers that remain outside the sandbox
package:

- align `trend_following_v1` 4h `spacing_bars` metadata/search-space behavior
  with the intended contract;
- make discovery resume manifests report completed-trial counts from recovered
  durable state when full trial hydration is intentionally skipped for large
  resumes.

## Dependencies

- `RAPID_STRATEGY_SANDBOX_AUDIT.md`
- `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md`
- `docs/work_packets/WPR106-362-post-audit-sandbox-safety-coherence.md`

## Allowed paths

- `src/tradingbotsuite/strategies/parameters.py`
- `src/tradingbotsuite/research_discovery/runner.py`
- `tests/optimization/test_search_space_expansion.py`
- `tests/research_discovery/test_discovery_runner.py`
- `docs/work_packets/WPR106-363-red-test-repair-strategy-discovery-resume.md`
- `docs/stage_reports/STAGE_R106_RED_TEST_REPAIR_STRATEGY_DISCOVERY_RESUME_REPORT.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`

## Boundary constraints

- No live, paper, sizing, order-placement, runtime-mode, live-config,
  candidate-pack, strict-validation execution, or promotion behavior.
- Do not weaken candidate gates, discovery durability, or resume correctness.
- Do not hide failed or incomplete discovery work by changing tests only.
- Strategy metadata changes must preserve explicit domains and deterministic
  candidate/search-space behavior.

## Acceptance criteria

- The targeted strategy search-space test passes with intentional 4h spacing
  behavior.
- The targeted discovery resume test passes while still avoiding full trial
  hydration above the configured limit.
- Discovery manifest `counts.completed_trials` matches recovered completed
  trial IDs after large zero-stop resume.
- Focused validation for touched areas passes.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\optimization\test_search_space_expansion.py::test_holding_window_search_space_includes_metadata_and_window_defaults -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_discovery_runner.py::test_discovery_runner_large_zero_stop_resume_recovers_lag_without_full_hydration -q
```

Broaden to sandbox/live/compile validation from WPR106-362 after these pass.

## Stop conditions

- A fix would make discovery manifest counts diverge from durable recovered
  state.
- A fix would require full hydration for large resumes despite the configured
  limit.
- A fix would weaken research-only or candidate-pack boundaries.
