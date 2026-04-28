# Backtest Agent Replay Determinism Contract

## Agent name

Backtest Agent

## Task received

Implement a research-only replay determinism utility for market/execution journal artifacts.

Required scope:

- Add a small research module for replay ordering, hashing, and comparison.
- Keep it pure/research-only with no live runtime, exchange calls, or operator controls.
- Support source-time and receive-time replay ordering with stable tie-breakers.
- Add focused tests for order-insensitive hashing, ordering modes, missing timestamps, and mismatch reporting.
- Do not modify live execution, runtime, operator UI, Hyperliquid adapter, or broad unrelated files.

## Files changed

- `src/tradingbotsuite/research/replay.py`
- `tests/tradingbotsuite/test_replay_determinism.py`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_replay_determinism_contract.md`

## Commands/tests run

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_replay_determinism.py
```

Result:

```text
4 passed
```

Additional checks:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite/research/replay.py
git diff -- src/tradingbotsuite/adapters/execution.py src/tradingbotsuite/core/engine.py src/tradingbotsuite/runtime.py src/tradingbotsuite/web/operator.py src/tradingbotsuite/web/templates/control.html src/tradingbotsuite/operator_commands.py
```

Result:

```text
<no output>
```

## Behavior

- Added `tradingbotsuite.research.replay` as an offline/research-only helper.
- Public functions:
  - `order_replay_events(events, order_by="source_time" | "receive_time")`
  - `hash_replay_events(events, order_by="source_time" | "receive_time")`
  - `compare_replay_runs(left_events, right_events, order_by="source_time" | "receive_time")`
- Output contracts include:
  - `research_only: true`
  - `observe_only: true`
  - `promotion_ready: false`
  - `contract_version: research-replay-determinism-v1`
- Source-time mode accepts source timestamp aliases in this order:
  - `source_event_time_ms`
  - `event_time_ms`
  - `time_ms`
- Receive-time mode requires `receive_time_ms`.
- Stable tie-breakers include common market/execution journal fields such as `source_name`, `symbol`, `data_family`, `event_type`, `payload_hash`, `source_row_index`, trade ids, `cloid`, and `signal_id`, followed by the canonical event hash.
- Missing or invalid required timestamps raise `ReplayDeterminismError` with a mode-specific message.
- Replay comparison returns a mismatch report with `match: false`, hashes, event counts, first mismatch index, and first mismatching events. It does not throw for valid replay content mismatches.

## Boundary notes

- No live execution files were modified.
- No exchange clients, Hyperliquid adapter behavior, runtime wiring, operator commands, or operator UI controls were changed.
- The utility only operates on supplied in-memory event mappings; it performs no file I/O and no network I/O.

## Open issues or blockers

No open issues or blockers.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` reports no open issues.
