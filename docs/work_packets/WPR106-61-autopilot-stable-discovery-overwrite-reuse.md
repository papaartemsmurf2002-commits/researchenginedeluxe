# Work Packet: WPR106-61 Autopilot Stable Discovery Overwrite Reuse

## Goal

Fix the autopilot failure mode where exact discovery can reach the discovery
runner and fail with `completed discovery runs refuse overwrite` even though a
stable completed discovery output directory already exists.

## Current Repo Facts

- WPR106-57 through WPR106-60 are uncommitted local work and must be preserved.
- The active BTC/ETH candidate-depth discovery manifests under
  `data/research/operator_runs/discovery_runs/*candidate-depth-v1` are complete
  locally.
- The discovery runner correctly refuses to overwrite a completed stable
  output directory.
- Autopilot should treat complete stable discovery evidence as reusable, and
  should fail closed with explicit blockers if a completed stable output exists
  but does not satisfy current artifact completeness rules.
- Stable discovery reuse must not become a stale-evidence trap. A completed
  stable output is reusable only when its resolved discovery spec matches the
  active discovery spec after migration-aware operator path normalization and
  after ignoring non-behavioral operator metadata.

## Allowed Edit Paths

- `docs/work_packets/WPR106-61-*.md`
- `src/tradingbotsuite/operator_console.py`
- `tests/tradingbotsuite/test_operator_ui.py`

## Research Boundary

- Do not start catalog rebuilds, historical cycles, discovery runs, or other
  long compute.
- Do not change strategy math, candidate gates, generated artifacts, live/paper
  runtime behavior, order placement, sizing, or promotion behavior.
- Research outputs remain `research_only`, `observe_only`, and
  `promotion_ready: false`.

## Plan

1. Add a direct stable-discovery manifest lookup by discovery spec/run ID.
2. Before executing exact discovery in autopilot, reuse that stable manifest if
   it is structurally complete for the expected symbol/run and its resolved
   discovery spec still matches the active spec.
3. If a completed stable run exists but is not structurally complete, block with
   explicit artifact blockers instead of calling the discovery runner.
4. If a completed stable run exists but its resolved spec is stale, block with a
   stale-evidence reason instead of treating the iteration as finished.
5. Add operator autopilot regression tests for reusable stable evidence,
   migrated output paths, metadata-only spec differences, and stale stable specs.
6. Run focused operator validation and baseline compile/contracts.

## Acceptance Criteria

- Autopilot does not call `_run_isolated_discovery` when a complete stable
  discovery manifest exists for the current spec/run ID.
- Autopilot no longer surfaces `completed discovery runs refuse overwrite` for
  reusable completed stable discovery evidence.
- Incomplete completed stable discovery evidence blocks with explicit reasons.
- Stale completed stable discovery evidence blocks with
  `completed_stable_discovery_artifact_stale`, preventing hidden no-progress
  iterations.
- Migrated old-checkout paths inside stable discovery manifests/specs are
  normalized before reuse comparison.
- Focused tests and baseline validation pass.
