# Stage R106 Final Crosscheck Robustness Report

Date: 2026-05-26
Work packet: `docs/work_packets/WPR106-17-final-crosscheck-robustness.md`

## Scope

Final robustness crosscheck after WPR106-16. The work stayed research-only and
did not add live execution, live configuration, runtime-mode changes, order
placement, candidate-pack writes, or promotion claims.

## Changes

- Frozen-entry exit-lab now fails closed for malformed or unsupported research
  inputs:
  - sub-hour label horizons clamp to the simulator-supported one-hour floor;
  - over-week horizons block the lead;
  - invalid sides, bad timestamps, bad `signal_bar_close`, malformed Parquet,
    and non-positive market OHLC produce blocked artifacts rather than job
    crashes.
- Candidate eligibility now enforces service-layer artifact boundaries:
  - all supplied manifest paths must stay inside `research.output_dir`;
  - nested `required_outputs` in supplied manifests must also stay inside the
    research root;
  - mixed-symbol discovery/exit-lab/testing/floor inputs are rejected before
    evaluation.
- Candidate eligibility completion checks now require the bridge and eligibility
  versions, canonical scope, required outputs, eligibility hash, and discovery
  and cycle source hashes before marking the required milestone complete.
- Research autopilot now runs all requested symbol cycle/discovery prerequisites
  before later analysis, delta, frozen-entry exit-lab, and eligibility steps.
- `docs/contracts/boundary_contract.md` now lists the R106 operator research
  workflow command names.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_frozen_entry_exit_lab.py -q`
  - `10 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`
  - `67 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py::test_boundary_contract_lists_research_command_registry -q`
  - `1 passed`
- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - `427 passed`
- `$env:PYTHONPATH='src'; python -m pytest -q`
  - `1452 passed, 1 skipped`

## Residual State

No candidate-ready trading claim exists. Remaining work is empirical: ETH cycle,
ETH exact discovery, current-output analysis/delta/exit-lab/eligibility review,
and candidate gate evidence.
