# Execution Risk Live Readiness Contract

## Agent name

Execution and Risk Agent

## Task received

Implement a research-side live-readiness validator for future production safety gate evidence. The validator must remain disconnected from live runtime and must not modify live execution, runtime, operator UI, Hyperliquid adapter behavior, or broad unrelated files.

## Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `src/tradingbotsuite/research/execution_journal.py`
- `tests/tradingbotsuite/test_execution_journal.py`
- `src/tradingbotsuite/research/data_quality.py`
- `tests/tradingbotsuite/test_data_quality.py`
- `src/tradingbotsuite/research/archive_sources.py`
- `tests/tradingbotsuite/test_archive_sources.py`

## Files changed

- `src/tradingbotsuite/research/live_readiness.py`
- `tests/tradingbotsuite/test_live_readiness.py`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_execution_risk_live_readiness_contract.md`

## Commands/tests run

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_live_readiness.py
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite/research/live_readiness.py
git diff -- src/tradingbotsuite/adapters/execution.py src/tradingbotsuite/core/engine.py src/tradingbotsuite/config.py src/tradingbotsuite/runtime.py src/tradingbotsuite/web/operator.py src/tradingbotsuite/web/templates/control.html src/tradingbotsuite/operator_commands.py
git status --short
```

Focused test result:

```text
4 passed
```

Explicit live-boundary diff result:

```text
<no diff output>
```

Current worktree includes other agents' existing unrelated changes in addition to this task:

```text
 M src/tradingbotsuite/research/dataset.py
?? docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_replay_determinism_contract.md
?? docs/tradingbotsuite_runtime/agent_artifacts/20260428_execution_risk_live_readiness_contract.md
?? src/tradingbotsuite/research/feature_alignment.py
?? src/tradingbotsuite/research/live_readiness.py
?? src/tradingbotsuite/research/replay.py
?? tests/tradingbotsuite/test_feature_alignment.py
?? tests/tradingbotsuite/test_live_readiness.py
?? tests/tradingbotsuite/test_replay_determinism.py
```

## Decisions made

- Added `src/tradingbotsuite/research/live_readiness.py` as a pure dictionary validator.
- Exposed `build_live_readiness_report(...)`, accepting explicit `config`, `artifacts`, and `execution_journal_evidence`, or a combined `payload`.
- Kept report output forced to:
  - `research_only: true`
  - `observe_only: true`
  - `promotion_ready: false`
- Added advisory `passed` status for whether the supplied future-style evidence satisfies the contract, while still keeping promotion disabled.
- Added required blocker checks:
  - LIVE rejects research jobs and research/observe-only artifacts.
  - `research_only: true` artifacts are rejected for live promotion.
- missing/default webhook secrets are rejected.
- missing Hyperliquid account/signing credential indicators are rejected.
  - missing, zero, or negative hard risk caps are rejected.
  - execution journal evidence is required for deterministic `cloid`, reduce-only exits, scheduleCancel/dead-man heartbeat, and reconciliation before any live automation discussion.
- Kept the module disconnected from env loading, adapters, runtime state, persistence, UI, and network access.

## Behavior

The validator returns a structured report with:

- `live_readiness_report_version`
- `research_only`
- `observe_only`
- `promotion_ready`
- `passed`
- per-check `passed` booleans and blocker reasons
- aggregate `blockers`
- a small `summary`
- notes emphasizing advisory-only behavior

Tests prove:

- LIVE research jobs and research-only artifacts are rejected.
- default webhook secret, missing Hyperliquid credential indicators, and non-positive risk caps are rejected.
- missing execution journal evidence is rejected.
- a fully populated future-style payload passes advisory checks while still returning `promotion_ready: false`.
- Orchestrator review expanded the accepted dictionary shapes to include the repo's current `webhook.secret`, `operator_ui.secret`, and `hyperliquid.private_key` fields, while retaining future-style indicator fields.

## Assumptions

- Hyperliquid credential checks may use indicators such as `private_key_configured` or the current config-style `private_key` presence. Reports should avoid logging real secret values.
- The minimum hard risk caps for this contract are `max_daily_loss_quote` and `max_open_risk_notional`, found under `risk`, `strategy`, or top-level config.
- scheduleCancel/dead-man evidence may be represented by explicit boolean evidence or by journal `event_types`.
- This validator is a research-side contract only; it is not a runtime preflight.

## Open issues or blockers

No open issues or blockers.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` reports no open issues.

## Handoff notes for other agents

- Import path: `tradingbotsuite.research.live_readiness`.
- Focused tests: `tests/tradingbotsuite/test_live_readiness.py`.
- Do not wire this module into live runtime without a separate live-boundary approval task.
- Live execution, position sizing, runtime gates, Hyperliquid adapter behavior, operator UI, and Control page remain untouched.
