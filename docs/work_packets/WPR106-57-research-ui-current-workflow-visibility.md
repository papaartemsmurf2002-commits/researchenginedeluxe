# Work Packet: WPR106-57 Research UI Current Workflow Visibility

## Goal

Make the operator Research tab visibly reflect the current ResearchEngineDeluxe
R106 catalog/autopilot workflow and prevent old browser-saved manual presets
from making the page appear stale after the repo/project migration.

## Current Repo Facts

- Current branch: `main`.
- Stage R106 is complete with a fail-closed no-candidate decision.
- The operator backend already exposes Historical Data Catalog diagnostics,
  catalog refresh, active-catalog default specs, and research autopilot routes.
- The Research tab still opens with a generic `Research Operations` hero, and
  browser `localStorage` keeps manual preset settings under
  `tbs.research.settings.v1`.

## Allowed Edit Paths

- `docs/work_packets/WPR106-57-*.md`
- `src/tradingbotsuite/web/templates/research.html`
- `tests/tradingbotsuite/test_operator_ui.py`

## Research Boundary

- This packet is UI/default-state visibility only.
- Do not change candidate gates, research algorithms, generated artifacts,
  paper/live runtime behavior, order placement, sizing, promotion validation,
  or runtime mode authorization.
- Research outputs remain `research_only`, `observe_only`, and
  `promotion_ready: false`.

## Plan

1. Update the Research tab first viewport so the current R106 catalog/autopilot
   workflow is unmistakable.
2. Rotate the browser research settings storage key to avoid stale pre-migration
   manual preset selections controlling the page.
3. Update focused operator UI assertions.
4. Run focused template/UI validation and the baseline compile/contracts if
   needed.

## Acceptance Criteria

- `/ui/research` HTML includes explicit ResearchEngineDeluxe/R106 catalog
  workflow copy in the first viewport.
- Fresh page state defaults to the active catalog workflow instead of old
  browser `v1` settings.
- Focused operator UI tests pass.

## Outcome

Updated the Research tab hero to identify the current
`ResearchEngineDeluxe R106 Console`, surface the R106 Historical Data Catalog
plus Research Autopilot path in the first viewport, and expose the two primary
operator actions immediately. Rotated the browser manual-preset storage key to
`researchenginedeluxe.research.settings.r106.v1` so old pre-migration
`tbs.research.settings.v1` selections do not make the page look or behave
stale.

Validation passed:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -k "research_page or research_artifacts or progress" -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- Compile passed.
- Focused operator UI slice: 15 passed, 68 deselected.
- Contracts: 441 passed.
