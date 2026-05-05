# WPR67-01 Repo Structure Dependency Fuse

Stage: R67 final structure crosscheck and dependency fuse
Owner: Codex Research Agent
Status: closed
Created: 2026-05-06

## Goal

Perform a final review pass after R66 and add a visible repo-structure and
dependency-safety document that future agents must read before modifying core
research infrastructure. The document should explain what the branch contains,
how the research system works, what goals are complete apart from live/promotion
execution, and which areas are unsafe to rewrite casually because of cross-module
contracts.

## Allowed paths

```text
AGENTS.md
START_HERE.md
README.md
src/tradingbotsuite/__init__.py
src/tradingbotsuite/backtesting/__init__.py
src/tradingbotsuite/data/__init__.py
src/tradingbotsuite/features/__init__.py
src/tradingbotsuite/live/__init__.py
src/tradingbotsuite/research_artifacts/__init__.py
src/tradingbotsuite/research_cycle/__init__.py
src/tradingbotsuite/strategies/__init__.py
src/tradingbotsuite/ui/research_app.py
tests/integration/test_research_ui.py
docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md
docs/work_packets/WPR67-01-repo-structure-dependency-fuse.md
docs/stage_reports/STAGE_R67_REPO_STRUCTURE_DEPENDENCY_FUSE_REPORT.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- Documentation and lightweight pointers only except the reviewed standalone
  research UI boundary gap.
- Do not change live execution behavior, promotion behavior, research-cycle
  semantics, feature calculation, strategy behavior, or generated artifacts.
- Do not claim live readiness or promotion readiness.
- Preserve branch rules: research outputs remain `research_only`,
  `observe_only`, and `promotion_ready: false`.

## Review checklist

- Confirm current ledger has no open P0 and fewer than four open P1 issues.
- Crosscheck research objectives reached outside live/promotion execution.
- Verify branch boundaries: research/data/features/backtesting/strategies do not
  import order-placement paths.
- Guard the standalone research UI against unallowlisted spec paths, external
  output directories, and live-mode execution.
- Verify validation is green after pointer/document changes.
- Add visible pointers to the fuse document in root onboarding docs and critical
  package roots.

## Exit validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Close evidence

- Final review found no remaining P0/P1 blockers and no open blocking issues in
  `docs/KNOWN_ISSUES.md`.
- Added `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md` as the visible branch
  architecture, dependency, workflow, and unsafe-to-rewrite fuse for future
  agents.
- Added pointers to the fuse document in root onboarding docs and critical
  package roots.
- Hardened the standalone research UI so experiment job specs must be inside
  `configs/experiments` or the configured research output directory, pipeline
  specs must be inside `configs/data` or the research output directory, output
  directories must stay inside the research output directory, and direct
  execution is rejected in live runtime.
- Added research UI integration coverage for explicit queued jobs, unallowlisted
  specs, external output directories, live-mode execution rejection, and live
  adapter import boundaries.
- Validation passed:
  - `python -m compileall -q src\tradingbotsuite`
  - `$env:PYTHONPATH='src'; python -m pytest tests\integration\test_research_ui.py -q`
    - 6 passed
  - `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
    - 367 passed
  - `$env:PYTHONPATH='src'; python -m pytest tests\live -q`
    - 40 passed
  - `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py tests\integration\test_research_ui.py -q`
    - 12 passed
  - `$env:PYTHONPATH='src'; python -m pytest -q`
    - 1041 passed, 91 warnings from legacy `tradingbot` FutureWarnings
