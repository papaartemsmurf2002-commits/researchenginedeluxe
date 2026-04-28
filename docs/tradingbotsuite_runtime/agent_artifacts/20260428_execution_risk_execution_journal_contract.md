# Execution Risk Execution Journal Contract

## Agent name

Execution and Risk Agent

## Task received

Implement schema/tests for Hyperliquid execution/account journal contracts, not live adapter behavior.

Required scope:

- Add a research/runtime-neutral execution journal contract module.
- Add focused tests.
- Add this handoff artifact.
- Do not change `src/tradingbotsuite/adapters/execution.py`, `src/tradingbotsuite/core/engine.py`, live order behavior, sizing, or the Control page.

## Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_EXECUTION_RISK_REVIEW.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `src/tradingbotsuite/adapters/execution.py`
- `src/tradingbotsuite/core/engine.py`
- `src/tradingbotsuite/research/market_data.py`
- `src/tradingbotsuite/research/archive_sources.py`
- `tests/tradingbotsuite/test_market_data_collection.py`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_execution_risk_commit_scope_inventory.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_execution_risk_final_live_boundary_check.md`

## Files changed

- `src/tradingbotsuite/research/execution_journal.py`
- `tests/tradingbotsuite/test_execution_journal.py`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_execution_risk_execution_journal_contract.md`

## Commands/tests run

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_execution_journal.py
```

Result:

```text
4 passed
```

Boundary commands:

```powershell
git status --short
git diff --name-only
git diff -- src/tradingbotsuite/adapters/execution.py src/tradingbotsuite/core/engine.py src/tradingbotsuite/config.py src/tradingbotsuite/runtime.py src/tradingbotsuite/web/operator.py src/tradingbotsuite/web/templates/control.html src/tradingbotsuite/operator_commands.py
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite/research/execution_journal.py
```

Explicit live-boundary diff result:

```text
<no diff output>
```

Current status includes other agents' existing/unrelated research and labeling edits in addition to this task's new files:

```text
 M docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md
 M src/tradingbotsuite/research/archive_sources.py
 M src/tradingbotsuite/research/dataset.py
 M src/tradingbotsuite/research/market_data.py
 M tests/tradingbotsuite/test_archive_sources.py
 M tests/tradingbotsuite/test_market_data_collection.py
 M tests/tradingbotsuite/test_research.py
?? docs/tradingbotsuite_runtime/agent_artifacts/20260428_execution_risk_execution_journal_contract.md
?? docs/tradingbotsuite_runtime/agent_artifacts/20260428_feature_agent_provider_normalization_contract.md
?? docs/tradingbotsuite_runtime/agent_artifacts/20260428_labeling_agent_executable_fill_purge_helpers.md
?? docs/tradingbotsuite_runtime/agent_artifacts/20260428_monitoring_agent_data_quality_reports.md
?? src/tradingbotsuite/research/data_quality.py
?? src/tradingbotsuite/research/execution_journal.py
?? tests/tradingbotsuite/test_data_quality.py
?? tests/tradingbotsuite/test_execution_journal.py
```

## Decisions made

- Added `src/tradingbotsuite/research/execution_journal.py` as a dependency-light research/runtime-neutral module.
- Defined the required event types:
  - `order_intent`
  - `order_submitted`
  - `order_acknowledged`
  - `order_rejected`
  - `order_partially_filled`
  - `order_filled`
  - `order_cancel_requested`
  - `order_cancel_acknowledged`
  - `position_snapshot`
  - `funding_payment`
  - `reconciliation`
  - `schedule_cancel_set`
  - `schedule_cancel_triggered`
- Added validation that requires:
  - exact `schema_version`
  - supported `event_type`
  - `source_event_time_ms`
  - `receive_time_ms` or `receive_time_unavailable_reason`
  - `symbol` for order, position, funding, and symbol-scoped reconciliation events
  - deterministic `cloid` evidence for order events, except `order_rejected` with `pre_submit_reject=true`
  - `reduce_only=true` when `exit_intent=true`
  - `payload_hash`, `raw_payload`, `payload`, or enough non-envelope fields to compute a canonical hash
- Added deterministic cloid helper using SHA-256 over canonical input parts and returning `0x` plus 32 hex characters.
- Added append-only JSONL writer, reader, manifest builder, and deterministic replay ordering by:
  - `receive_time_ms`
  - `source_event_time_ms`
  - `source_row_index`
- Kept all implementation outside live execution paths.

## Assumptions

- "Order-related non-snapshot events" means the `order_*` event family. `schedule_cancel_set` and `schedule_cancel_triggered` are account/dead-man-cancel contract events and do not require a per-order `cloid`.
- Reconciliation is symbol-scoped unless an event explicitly sets `scope="account"`.
- The contract is an offline journal schema for future Hyperliquid execution/account replay and auditability, not an instruction to place, size, cancel, or supervise live orders.

## Open issues or blockers

No open issues or blockers.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` reports no open issues.

## Handoff notes for other agents

- Import path: `tradingbotsuite.research.execution_journal`.
- Focused test path: `tests/tradingbotsuite/test_execution_journal.py`.
- This task intentionally did not modify:
  - `src/tradingbotsuite/adapters/execution.py`
  - `src/tradingbotsuite/core/engine.py`
  - live order behavior
  - position sizing
  - live gates
  - Hyperliquid adapter behavior
  - Control page/operator live controls
- Future adapter work can map live Hyperliquid order/account messages into this schema, but that is a separate task requiring explicit live-boundary approval.
