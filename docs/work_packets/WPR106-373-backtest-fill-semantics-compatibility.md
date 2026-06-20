# WPR106-373 - Backtest Fill-Semantics Compatibility

## Status

closed

## Objective

Resolve the post-audit `signal_bar_close_plus_latency` compatibility drift by
restoring the public source name to signal-close pricing and moving primary
bar open latency behavior behind an explicit source name.

## Dependencies

- `RAPID_STRATEGY_SANDBOX_AUDIT.md`
- `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md`
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- `docs/work_packets/WPR106-362-post-audit-sandbox-safety-coherence.md`
- `docs/work_packets/WPR106-372-sandbox-throughput-telemetry-report.md`

## Allowed paths

- `src/tradingbotsuite/backtesting/engine.py`
- `src/tradingbotsuite/backtesting/execution_sim.py`
- `src/tradingbotsuite/backtesting/vector_engine.py`
- `src/tradingbotsuite/backtesting/cuda_engine.py`
- `src/tradingbotsuite/backtesting/cuda_batched_engine.py`
- `tests/unit/test_execution_simulator.py`
- `tests/backtesting/**`
- `tests/contracts/test_backtest_contracts.py`
- `tests/historical/test_full_cycle_synthetic.py`
- `docs/contracts/boundary_contract.md`
- `docs/work_packets/WPR106-373-backtest-fill-semantics-compatibility.md`
- `docs/stage_reports/STAGE_R106_BACKTEST_FILL_SEMANTICS_COMPATIBILITY_REPORT.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Boundary constraints

- Compatibility and naming only.
- Do not change sandbox trial identity, sandbox ranking, archive routing,
  strict-validation behavior, candidate-pack gates, paper/live behavior,
  sizing, order placement, runtime mode, or live configuration.
- Preserve research-only backtest semantics and historical cost/fill proof
  metadata.

## Acceptance criteria

- `signal_bar_close_plus_latency` again uses the signal row close as its entry
  price after applying the configured latency to select the eligible entry bar.
- A new explicit primary-open latency source remains available for configs that
  intentionally want latency-bar open fills.
- Reference, vector, CUDA fallback, and CUDA batched policy code agree or fail
  closed for unsupported paths.
- Backtest manifests map the old source to `signal_close_latency_fill` and the
  explicit open-latency source to `primary_bar_latency_fill`.
- Focused tests cover the compatibility source, explicit open-latency source,
  manifest fill-profile mapping, and vector/reference parity.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\unit\test_execution_simulator.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_backtest_contracts.py -q
$env:PYTHONPATH='src'; python -m pytest tests\backtesting -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

## Stop conditions

- Any compatibility repair changes sandbox authority or candidate-pack
  behavior.
- Any old source silently keeps primary-open fill semantics.
- Any new source weakens research-only, observe-only, or non-promotion flags.

## Exit evidence

- Restored `signal_bar_close_plus_latency` to signal-close entry pricing after
  latency-based entry-bar selection.
- Added explicit `primary_bar_open_plus_latency` as the named primary-open
  latency source.
- Backtest manifest fill-profile mapping now distinguishes
  `signal_close_latency_fill` from `primary_bar_latency_fill`.
- Reference, vector, fake-CUDA R96, and fake-CUDA batched parity coverage now
  includes the restored old source and the explicit open-latency source.
- Focused validation passed:
  `$env:PYTHONPATH='src'; python -m pytest tests\unit\test_execution_simulator.py -q`
  reported 22 passed;
  `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_backtest_contracts.py -q -k "fill_profile or signal_close or unknown_cost"`
  reported 3 passed / 18 deselected;
  `$env:PYTHONPATH='src'; python -m pytest tests\backtesting\test_vector_engine_matches_reference.py -q -k "latency_entry_sources or fake_cupy"`
  reported 9 passed / 26 deselected;
  `$env:PYTHONPATH='src'; python -m pytest tests\backtesting\test_cuda_batched_fixed_holding.py -q -k "fake_cupy"`
  reported 6 passed / 3 deselected.
- Broader validation passed:
  `python -m compileall -q src\tradingbotsuite`;
  `$env:PYTHONPATH='src'; python -m pytest tests\backtesting -q`
  reported 109 passed / 1 skipped;
  `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  reported 462 passed;
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  reported 205 passed;
  `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`
  reported 26 passed;
  `git diff --check` passed with existing LF-to-CRLF warnings only.
- This packet does not change sandbox trial identity, sandbox ranking, archive
  routing, strict-validation behavior, candidate-pack gates, paper/live
  behavior, sizing, order placement, runtime mode, live configuration,
  candidate-evidence semantics, or promotion state.
