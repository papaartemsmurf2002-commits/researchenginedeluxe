# Stage R91 Discovery Batched State Checkpoints Report

Date: 2026-05-10
Packet: `docs/work_packets/WPR91-01-discovery-batched-state-checkpoints.md`

## Scope

WPR91 reduces discovery-run IO overhead by avoiding `run_state.json` rewrites
after every individual trial. Trial records remain the durable source of trial
completion truth, and state is still checkpointed at setup, resume merge,
snapshot, pause, completion, and final manifest boundaries.

## Changes

- Removed per-trial `run_state.json` writes after each trial record.
- Kept per-trial atomic trial record writes unchanged.
- Added manifest telemetry:
  `state_checkpoint_policy.policy_version:
  discovery-run-state-checkpoint-policy-v1`.
- Added a resume regression that deliberately makes `run_state.json` stale
  while keeping trial records intact; resume rebuilds completed state and
  finishes the run.

## Probe Evidence

A 10-trial deep-harvest-shaped local probe completed successfully:

- Completed trials: `10`
- Elapsed seconds: `10.967`
- Projected 5,000-trial runtime from this sample: `1.523` hours
- HMM cache hits in this random 10-trial sample: `0`
- Label/split cache hits in this random 10-trial sample: `0`
- State checkpoint policy: `discovery-run-state-checkpoint-policy-v1`

Recent same-shape probe progression:

- R88 probe: `22.439` seconds, projected `3.117` hours
- R89 probe: `22.725` seconds, projected `3.156` hours
- R90 probe: `13.245` seconds, projected `1.840` hours
- R91 probe: `10.967` seconds, projected `1.523` hours

## Validation

- `python -m compileall -q src\tradingbotsuite\research_discovery`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_discovery_runner.py -q`
  - `11 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q`
  - `80 passed`
- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - `372 passed`

## Exit Decision

Stage R91 is complete. Discovery run-state checkpointing now avoids per-trial
write amplification while preserving resume recovery from durable trial records.
