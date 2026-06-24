# WPR106-525 - Windows Async Contract Validation Mitigation

Status: self_checked
Owner: Codex Research Agent
Date: 2026-06-24

## Objective

Reduce recurring local Windows `WinError 10055` failures in the contract
validation lane without weakening source assertions. The known failure occurs
while pytest-asyncio creates an event-loop self-pipe before the lone async
contract test body runs.

This packet must not change research logic, strategy logic, archive behavior,
candidate-pack behavior, live/paper/order/sizing/runtime behavior, or
promotion state.

## Allowed Paths

- `docs/work_packets/WPR106-525-windows-async-contract-validation-mitigation.md`
- `tests/conftest.py`
- `AGENTS.md`

## No-Touch Paths

- Live runtime, order-placement, sizing, runtime config, promotion, shadow, and
  candidate-pack truth-layer paths.
- Checked research evidence under `data/research/**`.
- Provider/archive/data-source implementation code.

## Implementation Plan

- Keep the existing Windows selector event-loop policy.
- On Windows, prioritize async tests under `tests/contracts` during collection
  so pytest-asyncio creates its event-loop socket before the contract suite has
  churned through many sync tests.
- Document why `WinError 10055` can still happen and how agents should
  mitigate it without treating it as a source assertion failure.

## Expected Validation

```powershell
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/contracts -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/contracts/test_historical_fixture_pack_contract.py::test_provider_kline_fixture_pack_builder_accepts_collected_binance_context_manifest -q
git diff --check
```

## Validation Evidence

```text
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/contracts -q:
  463 passed, 1 warning
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/contracts --collect-only -q:
  first collected item is tests/contracts/test_historical_fixture_pack_contract.py::test_provider_kline_fixture_pack_builder_accepts_collected_binance_context_manifest
python -m compileall -q src/tradingbotsuite:
  passed
git diff --check:
  passed with expected LF-to-CRLF warnings only
```

An immediate isolated rerun of the async contract after the full contract sweep
still hit `WinError 10055` in pytest-asyncio event-loop setup while the host
session was degraded. Direct `socket.socketpair()` still succeeded. The
mitigation therefore reduces the common full-contract failure mode by running
the lone async contract first; it does not claim to repair Windows socket-stack
resource exhaustion after repeated async test runs.
