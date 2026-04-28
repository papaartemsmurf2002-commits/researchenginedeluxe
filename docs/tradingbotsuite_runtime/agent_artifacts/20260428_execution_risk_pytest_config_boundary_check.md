# Execution Risk Pytest Config Boundary Check

## Agent name

Execution and Risk Agent

## Task received

Review the `pyproject.toml` pytest/config change as non-runtime and non-live. Run `git diff -- pyproject.toml` and confirm it only affects test collection and research optional dependencies, not execution or runtime behavior. Write this artifact.

## Files read

- `pyproject.toml` diff from `git diff -- pyproject.toml`.

## Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_execution_risk_pytest_config_boundary_check.md`

## Commands/tests run

```powershell
git diff -- pyproject.toml
```

Observed diff:

- Adds optional dependency group:
  - `research = ["hmmlearn==0.3.3", "xgboost>=3.2.0,<4"]`
- Adds pytest option:
  - `addopts = "--import-mode=importlib"`

## Decisions made

- Classified the `research` dependency group as optional research tooling. It does not alter default install dependencies, project scripts, runtime mode, execution adapter behavior, Hyperliquid configuration, or operator live controls.
- Classified `addopts = "--import-mode=importlib"` as pytest collection/import behavior only. It affects test execution, not application runtime behavior.
- Confirmed the diff does not change `[project.scripts]`, runtime entrypoints, live execution settings, position sizing, live gates, or Hyperliquid behavior.

## Assumptions

- Optional extras are only installed when explicitly requested and are not part of default runtime execution.
- Pytest configuration is used by test runs and is not consumed by production runtime code.

## Open issues or blockers

No open issues or blockers.

## Handoff notes for other agents

This `pyproject.toml` diff is non-runtime and non-live. It is limited to optional research dependencies and pytest import-mode configuration. No live execution, sizing, gates, Hyperliquid behavior, or operator live controls were changed by this diff.
