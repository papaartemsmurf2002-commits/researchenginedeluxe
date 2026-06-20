# WPR106-381 - Sandbox Next-Action Unindexed Iteration Manifests

## Status

closed

## Objective

Improve the agent workflow for a just-run sandbox iteration by making
`show-rapid-strategy-sandbox-next-action` detect existing
`sandbox_iteration_manifest.json` files when no artifact catalog or iteration
index exists yet, then recommend the indexing step with exact files to inspect.

## Dependencies

- `RAPID_STRATEGY_SANDBOX_AUDIT.md`
- `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md`
- `docs/work_packets/WPR106-379-sandbox-source-discovery-bounds.md`
- `docs/work_packets/WPR106-380-sandbox-ci-validation-coverage.md`

## Allowed paths

- `src/tradingbotsuite/research_sandbox/next_action.py`
- `tests/research_sandbox/test_sandbox_foundation.py`
- `docs/work_packets/WPR106-381-sandbox-next-action-unindexed-iteration-manifests.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_NEXT_ACTION_UNINDEXED_ITERATION_MANIFESTS_REPORT.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Boundary constraints

- The dashboard remains read-only and descriptor-only.
- Do not run sandbox sweeps, recompute evidence, index artifacts, execute
  strict validation, write candidate packs, create paper/live behavior, define
  sizing, place orders, change runtime mode, write live config, claim candidate
  evidence, or authorize promotion.
- Manifest discovery must be bounded by `max_files` and path-contained under
  the requested output root.

## Acceptance criteria

- A root containing an iteration manifest but no artifact catalog or iteration
  index produces `recommended_action:
  index_rapid_strategy_sandbox_iterations`.
- The next-action payload includes the unindexed manifest count and exact
  manifest path to open next.
- Existing catalog/index behavior is unchanged.
- The report preserves research-only sandbox boundary flags.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -k "next_action" -q
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
python -m compileall -q src\tradingbotsuite
git diff --cached --check
```

Exit evidence:

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -k "next_action" -q`
  - `3 passed, 196 deselected`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  - `220 passed`
- `python -m compileall -q src\tradingbotsuite`
  - passed
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`
  - `26 passed`
- Ignored local CLI smoke with `TBS_RESEARCH_OUTPUT_DIR` set to
  `outputs\sandbox_smoke_wpr106_379\research_outputs`:
  `python -m tradingbotsuite.main show-rapid-strategy-sandbox-next-action --output-root <smoke-root> --output-dir next_action_smoke_wpr106_381 --limit 5`
  - returned `recommended_action: index_rapid_strategy_sandbox_iterations`
  - returned `unindexed_iteration_manifest_count: 1`
  - returned `strict_validation_executed: false` and `candidate_pack_written: false`

## Stop conditions

- The dashboard needs to recompute rankings, rerun a sweep, or mutate source
  artifacts to provide the recommendation.
- The change weakens artifact catalog or iteration-index validation.
- The change allows output-root traversal or reads outside the requested root.
