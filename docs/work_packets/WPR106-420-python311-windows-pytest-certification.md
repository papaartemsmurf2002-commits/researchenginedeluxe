# WPR106-420 Python 3.11 Windows Pytest Certification

Status: closed
Owner: Codex Manager Development Agent
Created: 2026-06-21

## Objective

Resolve or sharply narrow `ISSUE-R106-026` so the repository has an
authoritative Python 3.11 Windows validation lane for v2 and full-suite
certification work. The immediate failure is Windows Proactor event-loop
socket exhaustion during `pytest-asyncio` fixture setup in the monolithic
Python 3.11 test suite. If the pinned lane exposes deterministic v2
test-contract defects, fix them only inside the smallest relevant v2 module.

This packet is test-infrastructure only. It does not implement strategy
behavior, run collectors, run backtests, write generated research evidence,
create candidate packs, place orders, produce paper/live signals, emit sizing
instructions, change runtime mode, or create promotion-ready artifacts.

## Audit IDs

- `V2-AUD-TESTINFRA-001`
- `V2-AUD-WORKER-002`

## Allowed Paths

- `docs/work_packets/WPR106-420-python311-windows-pytest-certification.md`
- `docs/KNOWN_ISSUES.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/workers/job_store.py`
- `tests/conftest.py`
- `tests/v2/test_workers_phase7.py`

## No-Touch Paths

- `src/**/live/**`
- `src/**/runtime.py`
- `run_live_smoke.py`
- `run_manual.py`
- order-placement adapters, broker helpers, exchange submit helpers
- sizing/runtime configuration paths
- `src/tradingbotsuite/research_artifacts/candidate_pack.py`
- `src/tradingbotsuite/promotion/**`
- `src/tradingbotsuite/live/shadow_loader.py`
- committed generated research evidence under `data/research/**`
- legacy GUI/web/operator source paths
- `src/tradingbot/**`
- `.env`, credential files, local SQLite operator DBs, private caches

## Boundary Constraints

- The fix may only change pytest/test-process behavior.
- Runtime asyncio policy and application behavior must remain untouched.
- Worker-store changes may only improve deterministic audit ordering for
  already-recorded transitions; worker execution semantics are out of scope.
- The packet may install local Python 3.11 dev dependencies for validation
  evidence, but repository dependency policy changes are out of scope unless a
  new failure proves they are required.
- If the full suite still fails, record exact blockers and keep the goal
  active.

## Expected Validation

```powershell
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts\test_historical_fixture_pack_contract.py::test_provider_kline_fixture_pack_builder_accepts_collected_binance_context_manifest -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_workers_phase7.py::test_claim_heartbeat_failure_retry_and_terminal_transitions_are_recorded -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2 -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests -q
git diff --check
```

## Acceptance Criteria

- Python 3.11 has the repo runtime/dev dependencies installed locally.
- The known Proactor socket-exhaustion reproduction no longer fails.
- Python 3.11 v2 and contract suites pass.
- The Python 3.11 full suite either passes or produces a new, concrete blocker
  recorded in `docs/KNOWN_ISSUES.md`.
- Control docs record the validation evidence without claiming autonomous-ready
  status unless every completion-checklist item is satisfied.

## Completion Notes

Closed on 2026-06-21 with `ISSUE-R106-026` still open as a local
Windows/Python 3.11.0 full-suite certification blocker.

Changed files:

- `tests/conftest.py`
- `src/tradingbotsuite/v2/workers/job_store.py`
- `docs/work_packets/WPR106-420-python311-windows-pytest-certification.md`
- `docs/KNOWN_ISSUES.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

Decisions made:

- Installed the project with `.[dev]` into the local Python 3.11.0
  interpreter so Python 3.11 validation can run locally.
- Set the Windows pytest process to `WindowsSelectorEventLoopPolicy` to reduce
  Proactor-specific event-loop cleanup noise without changing application
  runtime behavior.
- Fixed v2 worker transition listing to use SQLite insertion order as the
  tie-breaker after timestamp, because hash-based `transition_id` order can
  reorder transitions written in the same clock tick.
- Kept `ISSUE-R106-026` open because the monolithic Python 3.11 full suite
  still fails on the local Windows socket stack before an async test body runs.

Validation:

```powershell
py -3.11 -m pip install -e ".[dev]"
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts\test_historical_fixture_pack_contract.py::test_provider_kline_fixture_pack_builder_accepts_collected_binance_context_manifest -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_workers_phase7.py::test_claim_heartbeat_failure_retry_and_terminal_transitions_are_recorded -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2 -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests -q
```

Result:

- Python 3.11 local dependency install succeeded.
- Exact async contract reproduction passed: 1 passed.
- Exact worker transition-order reproduction passed: 1 passed.
- Python 3.11 contracts passed: 462 passed, 1 warning.
- Python 3.11 v2 passed: 173 passed, 1 warning.
- Python 3.11 monolithic full suite did not certify: latest run reported
  1 failed, 668 passed, 2 skipped, 3 warnings, and 1 error before pytest hit
  an internal traceback formatting error. The first isolated concrete error is
  still `WinError 10055` during `socket.socketpair()` setup for
  `test_provider_kline_fixture_pack_builder_accepts_collected_binance_context_manifest`.

Open blockers:

- `ISSUE-R106-026` remains open. Use a fresh Windows socket stack, a newer
  Python 3.11 patch interpreter, or Linux CI as authoritative full-suite
  evidence.
- `ISSUE-R106-020` remains open as strategy/exit semantics debt and a
  pre-autonomy blocker under the execution brief.
- Final autonomous-ready status is not claimed.
