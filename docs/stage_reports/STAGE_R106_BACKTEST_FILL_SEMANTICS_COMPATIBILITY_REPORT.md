# Stage R106 Backtest Fill-Semantics Compatibility Report

Date: 2026-06-20
Packet: `WPR106-373-backtest-fill-semantics-compatibility`

## Summary

WPR106-373 closes the post-audit `signal_bar_close_plus_latency`
compatibility risk. The public source name again uses `signal_bar_close` for
entry price after applying configured latency to select the eligible entry bar.
Primary bar open latency behavior remains available under the explicit
`primary_bar_open_plus_latency` source name.

Backtest manifests now map `signal_bar_close_plus_latency` to
`signal_close_latency_fill` and `primary_bar_open_plus_latency` to
`primary_bar_latency_fill`. Reference, vector, fake-CUDA R96, and fake-CUDA
batched paths have focused parity coverage for both source names.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\unit\test_execution_simulator.py -q`
  - `22 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_backtest_contracts.py -q -k "fill_profile or signal_close or unknown_cost"`
  - `3 passed, 18 deselected`
- `$env:PYTHONPATH='src'; python -m pytest tests\backtesting\test_vector_engine_matches_reference.py -q -k "latency_entry_sources or fake_cupy"`
  - `9 passed, 26 deselected`
- `$env:PYTHONPATH='src'; python -m pytest tests\backtesting\test_cuda_batched_fixed_holding.py -q -k "fake_cupy"`
  - `6 passed, 3 deselected`
- `python -m compileall -q src\tradingbotsuite`
  - passed
- `$env:PYTHONPATH='src'; python -m pytest tests\backtesting -q`
  - `109 passed, 1 skipped`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - `462 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  - `205 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`
  - `26 passed`
- `git diff --check`
  - passed with existing LF-to-CRLF warnings only

## Boundary Statement

This packet changes shared research backtest fill-source compatibility only.
It does not change sandbox trial identity, sandbox ranking, archive routing,
strict-validation behavior, candidate-pack gates, paper/live behavior, sizing,
order placement, runtime mode, live configuration, candidate-evidence
semantics, or promotion state.
