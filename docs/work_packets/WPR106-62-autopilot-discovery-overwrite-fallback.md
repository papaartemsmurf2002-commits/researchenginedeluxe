# Work Packet: WPR106-62 Autopilot Discovery Overwrite Fallback

## Goal

Make `run-research-autopilot` operational when the stable exact-discovery
output directory already contains a completed run and the discovery runner
raises `completed discovery runs refuse overwrite`.

## Current Repo Facts

- WPR106-57 through WPR106-61 are uncommitted local work and must be preserved.
- The operator can still reach `_run_isolated_discovery(... stable_run_id=True)`
  and fail with `completed discovery runs refuse overwrite`.
- Completed stable discovery evidence should be reused when it is current and
  structurally complete, but a fresh requested iteration must not get trapped by
  stable-run overwrite protection.

## Allowed Edit Paths

- `docs/work_packets/WPR106-62-*.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/operator_console.py`
- `tests/tradingbotsuite/test_operator_ui.py`

## Research Boundary

- Do not trigger catalog rebuilds, historical cycles, exact discovery, or other
  long compute during this fix.
- Do not rewrite generated research artifacts.
- Do not change strategy math, candidate gates, order placement, sizing, live
  mode, or promotion behavior.
- Research outputs remain `research_only`, `observe_only`, and
  `promotion_ready: false`.

## Plan

1. Register the overwrite fallback risk in `docs/KNOWN_ISSUES.md` as a P1.
2. Add a bounded operator fallback so exact discovery can retry in an isolated
   per-job output directory when the stable output is completed and refuses
   overwrite.
3. Preserve the current stable-evidence reuse path and stale-spec blockers.
4. Add an operator regression proving the fallback retries without changing the
   stable output directory.
5. Run focused operator validation and baseline compile/contracts.

## Acceptance Criteria

- `completed discovery runs refuse overwrite` no longer causes an autopilot job
  failure when a fresh isolated discovery attempt is allowed.
- Stable evidence reuse still skips execution when current complete evidence is
  available.
- Stale completed stable evidence still blocks instead of silently reusing.
- Tests and baseline validation pass.

## Outcome

- Added a stable-overwrite fallback wrapper for discovery jobs.
- Autopilot exact discovery and the direct `run-discovery` operator job now use
  the wrapper.
- The fallback retries internally with isolated-output routing,
  `resume=False`, and a `-isolated-fallback` job id when the stable output
  refuses overwrite.
- The fallback reports `overwrite_fallback_used`,
  `stable_overwrite_error_text`, `stable_attempt_job_id`, and
  `fallback_job_id` in the step result for UI/job-log visibility.
- `ISSUE-R106-015` was registered and resolved in `docs/KNOWN_ISSUES.md`.

## Validation

- Focused fallback/reuse/stale tests: 3 passed.
- Affected direct discovery tests plus fallback regression: 3 passed.
- `python -m compileall -q src\tradingbotsuite`: passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`: 441 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`: 87 passed.
