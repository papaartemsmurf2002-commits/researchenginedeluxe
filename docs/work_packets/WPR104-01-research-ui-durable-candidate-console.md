# WPR104-01 Research UI Durable Candidate Console

Owner: Codex Research Agent
Stage: R104 candidate validation on durable evidence
Status: closed
Created: 2026-05-14

## Goal

Bring the operator Research console up to the R104 purpose: run durable
BTC/ETH candidate-validation research from the UI, make the right settings and
recommendations visible, and remove or de-emphasize stale/latest-window-first
paths that distract from durable evidence.

## Allowed paths

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/work_packets/**`
- `docs/stage_reports/**`
- `docs/OPERATOR_GUIDE.md`
- `docs/OPERATOR_QUICKSTART.md`
- `docs/runbooks/research_ui_runbook.md`
- `configs/research/**`
- `configs/discovery/**`
- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/web/operator.py`
- `src/tradingbotsuite/web/templates/base.html`
- `src/tradingbotsuite/web/templates/research.html`
- `src/tradingbotsuite/ui/**`
- `tests/contracts/**`
- `tests/historical/**`
- `tests/integration/test_research_ui.py`
- `tests/tradingbotsuite/test_operator_ui.py`
- `tests/research_discovery/**`

## Constraints

- Keep outputs `research_only`, `observe_only`, and `promotion_ready: false`.
- Do not add live execution, live config writes, runtime-mode changes, sizing
  changes, order-placement behavior, or promotion authorization.
- UI actions must remain backed by service-layer validation, path allowlists,
  isolated output directories, CSRF/session checks, and live-mode rejection.
- Do not claim candidate-ready performance just because durable fixture packs
  exist; R104 can still end with blocked candidate packs.

## Planned implementation

1. Add or update durable BTC/ETH candidate-validation configs that consume the
   R103 public-archive fixture packs.
2. Add durable discovery presets where the existing engine can run them safely,
   keeping smoke/latest-window paths clearly secondary.
3. Wire the Research tab to durable R104 defaults, visible settings,
   recommendations, and first-look status instead of V2/latest-window defaults.
4. Keep older signal-history model tools in an advanced diagnostics area only.
5. Update tests to cover durable presets, UI copy, route allowlists, and
   research/live boundary behavior.

## Validation target

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py tests\integration\test_research_ui.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts tests\historical tests\research_discovery -q
git diff --check
```

## Exit evidence

- Added durable BTC/ETH R104 cycle specs and updated discovery defaults to use
  the checked R103 public-archive fixture packs.
- Added operator R104 readiness diagnostics and a UI-backed
  `evaluate-discovery-candidate-pack-eligibility` job with research-root path
  validation and isolated output directories.
- Reworked the Research tab around durable readiness, recommended run order,
  BTC/ETH durable cycle/discovery controls, candidate eligibility review, and
  fail-soft artifact cards for exit-lab, multiple-testing, validation-floor,
  bridge, and malformed artifacts.
- Kept provider pipeline and signal-history controls as secondary diagnostics;
  removed raw CLI copy guidance from the active historical-cycle path.
- Validation:
  - `python -m compileall -q src/tradingbotsuite`
  - Research page JavaScript parsed with Node `new Function(...)`
  - `$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_operator_ui.py -q`
  - `$env:PYTHONPATH='src'; python -m pytest tests/research_discovery/test_discovery_spec.py tests/research_discovery/test_discovery_feature_sets.py -q`
  - `$env:PYTHONPATH='src'; python -m pytest tests/integration/test_research_ui.py -q`
  - `$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_strategy_contracts.py tests/contracts/test_import_boundaries.py -q`
  - `$env:PYTHONPATH='src'; python -m pytest tests/contracts tests/historical tests/research_discovery -q`
