# Stage R90 HMM Vectorized Assignment Report

Date: 2026-05-09
Packet: `docs/work_packets/WPR90-01-hmm-vectorized-assignment.md`

## Scope

WPR90 reduces HMM materialization overhead by vectorizing posterior/router
assignment into the output frame. It does not change model fitting, feature
math, split construction, strategy behavior, candidate gates, promotion
readiness, or live behavior.

## Changes

- Replaced nested per-row/per-state `.loc` assignment in `_assign_posterior_rows`
  with vectorized column assignment.
- Added `assignment_engine: vectorized_posterior_assignment_v1` to HMM
  materialization manifests.
- Added scalar-reference regression coverage for posterior probabilities,
  top-regime labels, confidence, entropy, flip flags, no-trade flags, source
  rows, model ids, feature-pack ids, and split ids.

## Probe Evidence

A 10-trial deep-harvest-shaped local probe completed successfully:

- Completed trials: `10`
- Elapsed seconds: `13.245`
- Projected 5,000-trial runtime from this sample: `1.840` hours
- HMM cache hits in this random 10-trial sample: `0`
- Label/split cache hits in this random 10-trial sample: `0`

This is a meaningful improvement versus the prior same-shape probes in this
work session:

- R88 probe: `22.439` seconds, projected `3.117` hours
- R89 probe: `22.725` seconds, projected `3.156` hours
- R90 probe: `13.245` seconds, projected `1.840` hours

## Validation

- `python -m compileall -q src\tradingbotsuite\research_discovery`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_hmm_materialization.py -q`
  - `9 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q`
  - `79 passed`
- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - `372 passed`

## Exit Decision

Stage R90 is complete. HMM assignment is vectorized and the deep discovery
runtime estimate for the local latest-month fixture probe improved to about
`1.84` hours for 5,000 trials.
