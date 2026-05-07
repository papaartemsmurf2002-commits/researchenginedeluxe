# Research V4 Implementation Agent Handoff

Date: 2026-05-07
Branch: `research/v3-experimental-engine`
Next stage: WPR73 Discovery Run Manager

## Read First

Before coding, read these files in this order:

1. `AGENTS.md`
2. `docs/ORCHESTRATOR_STAGE_LEDGER.md`
3. `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
4. `docs/RESEARCH_V4_DISCOVERY_ENGINE_AGENT_PLAN.md`
5. `docs/work_packets/WPR72-01-discovery-engine-agent-plan.md`
6. `docs/work_packets/WPR72-02-discovery-feature-set-flexibility-addendum.md`

The next implementation must start with WPR73. Do not jump directly into HMM/KNN math, feature packs, UI, or candidate-pack bridge before the discovery run manager exists.

## Current Decision

The branch has a historical research framework, but the latest runs were constrained smoke-style cycles. They are not real discovery. V4 changes the direction toward a durable research-only discovery engine that can run for hours or days, checkpoint progress, and produce a complete ledger of tested ideas, blockers, and interesting candidates.

Important design decisions:

- HMM is a split-safe regime detector, not the alpha engine.
- KNN must be tuned per HMM regime.
- WT and WT3D are optional feature-column candidates, not privileged defaults.
- Non-WT alternatives are first-class.
- Perp context and microstructure are ablation tracks until proven useful.
- Feature combinations must be predeclared and bounded; do not brute-force arbitrary millions of combinations.
- Current region-of-stability logic must not be reused to claim stability across feature sets. Use a separate `feature_combination_stability` diagnostic later.
- Long runs must snapshot every 30 minutes and resume safely.
- Research outputs remain `research_only`, `observe_only`, and `promotion_ready: false`.

## Immediate Implementation Target: WPR73

Build the discovery run manager foundation.

Expected package shape:

```text
src/tradingbotsuite/research_discovery/
  __init__.py
  spec.py
  runner.py
  state.py
  snapshots.py
  manifests.py
```

Expected tests:

```text
tests/research_discovery/
  test_discovery_spec.py
  test_discovery_state.py
  test_discovery_snapshots.py
  test_discovery_runner.py
```

Expected docs/configs:

```text
configs/discovery/
  quick_smoke_btcusdt_v4.json
```

Only add files where needed. Keep the structure small and explicit.

## WPR73 Required Behavior

Implement:

- Discovery spec parsing and validation.
- Repo-root-safe path resolution.
- Isolated output directory creation under configured research output.
- `discovery_run_manifest.json`.
- `discovery_spec_resolved.json`.
- `run_state.json`.
- `candidate_ledgers/interesting_candidates.parquet`.
- `candidate_ledgers/blocked_candidates.parquet`.
- `candidate_ledgers/filter_blockers.parquet`.
- `snapshots/*.json`.
- Atomic snapshot writes using temp file then rename.
- Resume-safe immutable completed-trial records.
- Clear refusal to overwrite existing completed runs.

Do not implement full KNN search yet. WPR73 can use placeholder trial records as long as manifests and state behavior are real, deterministic, and tested.

## Validation Minimum

Run:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
git diff --check
```

If contracts are too slow for an intermediate check, run the focused discovery tests first, but do not close WPR73 without the baseline validation.

## Agent Workflow

Use subagents deliberately:

- Explorer: inspect path/config/test contracts before implementation.
- Worker: implement `research_discovery` package and tests.
- Reviewer: audit state transitions, atomic writes, resume behavior, and research/live boundaries.

Keep file ownership disjoint if multiple workers are used. Do not let agents edit the same files in parallel.

## Calculation And State Safety Rules

- No full-dataset fitting.
- No live adapter imports.
- No order placement, runtime mode changes, sizing, or promotion artifacts.
- Every generated artifact must be reproducible from spec, run ID, code version, and input hashes.
- Interrupted and uninterrupted runs must produce the same completed-trial ledger.
- Snapshot files must be readable even if a run is interrupted after the previous snapshot.
- All paths in manifests should be absolute or repo-root-resolved where appropriate.
- Do not hide failure: failed trial attempts need an error payload and retry identity.

## Ready Prompt For Next Agent

```text
You are continuing on branch `research/v3-experimental-engine` in `C:\Users\papaa\Music\tradingbotsuite`.

Read `AGENTS.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`, `docs/RESEARCH_V4_DISCOVERY_ENGINE_AGENT_PLAN.md`, and this handoff before coding.

Open WPR73: implement the V4 Discovery Run Manager foundation only. Do not start feature math, HMM materialization, KNN tuning, UI redesign, or candidate-pack bridge yet.

Create a small `src/tradingbotsuite/research_discovery/` package with spec parsing, output directory handling, run manifests, run state, immutable trial records, atomic 30-minute snapshot support, and resume-safe behavior. Add a quick smoke discovery config under `configs/discovery/` and focused tests under `tests/research_discovery/`.

Keep all outputs research-only, observe-only, and promotion-ready false. Do not import live execution adapters. Preserve the existing branch structure and contracts.

Use subagents for independent exploration/review where useful. Crosscheck state transitions, path safety, atomic writes, resume determinism, and no-overwrite behavior. Add focused tests and run:

python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
git diff --check

Stop and report if a blocker appears that would require changing existing research-cycle semantics, live/promotion boundaries, or candidate-pack gates.
```
