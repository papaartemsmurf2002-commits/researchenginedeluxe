# Stage R106 Discovery Lead Replay Entry Evidence Report

Work packet:
`docs/work_packets/WPR106-31-discovery-lead-replay-entry-evidence.md`

Date: 2026-05-30

## Summary

WPR106-31 replayed the WPR106-30 materialized BTCUSDT and ETHUSDT discovery
lead descriptors through the real discovery artifact path. The packet adds a
bounded replay-spec builder, a prediction-only discovery artifact policy, and
an annotated entry-signal aggregation artifact for downstream exit-lab and
cycle-overlay work.

This is still not candidate-pack evidence. It produces real replayed
KNN/strategy-signal artifacts and a bounded frozen-entry exit-lab slice, but it
does not write historical-cycle rankings, research gate pass rows, candidate
packs, live behavior, sizing, runtime-mode changes, or promotion claims.

## Code Changes

Added:

- `src/tradingbotsuite/research_discovery/discovery_lead_replay.py`
- `tests/research_discovery/test_discovery_lead_replay.py`

Updated:

- `src/tradingbotsuite/research_discovery/spec.py`
- `src/tradingbotsuite/research_discovery/runner.py`
- `src/tradingbotsuite/research_discovery/__init__.py`
- `tests/research_discovery/test_discovery_spec.py`
- `tests/research_discovery/test_discovery_runner.py`

The new replay module provides:

- `build_discovery_lead_replay_spec()`
- `write_discovery_lead_replay_spec()`
- `aggregate_discovery_replay_entry_signals()`
- `write_discovery_replay_entry_signal_artifacts()`
- `validate_discovery_replay_entry_signal_manifest()`

The discovery execution policy now accepts `predictions_only`. That policy
persists KNN prediction artifacts and strategy-accounting artifacts without
writing heavy per-trial neighbor diagnostics or HMM posterior artifacts.

## Replay Specs

Replay specs were generated under:

- `data/research/operator_runs/wpr106_31_discovery_lead_replay/btcusdt/replay_spec/discovery_replay_spec.json`
- `data/research/operator_runs/wpr106_31_discovery_lead_replay/ethusdt/replay_spec/discovery_replay_spec.json`

Each replay spec contains 24 explicit `trial_templates` sourced from
WPR106-30 materialized leads. Each template preserves:

- source discovery candidate ID;
- source trial ID;
- source record hash;
- materialized `mat-*` candidate ID;
- prediction signature hash;
- entry-event signature hash;
- effective trial key;
- original KNN/HMM threshold payload.

## BTCUSDT Evidence

Replay output:

- `data/research/operator_runs/wpr106_31_discovery_lead_replay/btcusdt/discovery_run/discovery_run_manifest.json`
- manifest SHA-256:
  `e06af984a5a32fc5d2903728e260cd96e7ea9b75af16c1ef628e5ccb47529134`

Replay counts:

- completed trials: 24
- interesting candidates: 24
- blocked candidates: 0
- filter blockers: 0
- runtime: 9,995.955365 seconds
- artifact policy: `predictions_only`

Entry-signal evidence:

- `data/research/operator_runs/wpr106_31_discovery_lead_replay/btcusdt/entry_signals/discovery_replay_entry_signal_manifest.json`
- `data/research/operator_runs/wpr106_31_discovery_lead_replay/btcusdt/entry_signals/discovery_replay_entry_signals.parquet`
- entry signal rows: 969,870
- candidates with signals: 24
- signal artifact SHA-256:
  `c90759d8162fd04456d3f154b673c1dc6f2eb9a0d594b7ed2a8e972ba1f214ed`

Frozen-entry exit-lab slice:

- `data/research/operator_runs/wpr106_31_discovery_lead_replay/btcusdt/frozen_entry_exit_lab_top3/discovery_exit_lab_manifest.json`
- selected leads: 3
- comparisons: 6
- decisions: `blocked: 3`
- blocker reason for all 3:
  `simple_runner_did_not_beat_fixed_holding|exit_lab_no_improving_exit_over_fixed_holding`

## ETHUSDT Evidence

Replay output:

- `data/research/operator_runs/wpr106_31_discovery_lead_replay/ethusdt/discovery_run/discovery_run_manifest.json`
- manifest SHA-256:
  `08007966dd5b27adae3d38bd8f9142cba3b21f1a7c3c041aca15d03fb2561f77`

Replay counts:

- completed trials: 24
- interesting candidates: 24
- blocked candidates: 0
- filter blockers: 0
- runtime: 10,239.432062 seconds
- artifact policy: `predictions_only`

Entry-signal evidence:

- `data/research/operator_runs/wpr106_31_discovery_lead_replay/ethusdt/entry_signals/discovery_replay_entry_signal_manifest.json`
- `data/research/operator_runs/wpr106_31_discovery_lead_replay/ethusdt/entry_signals/discovery_replay_entry_signals.parquet`
- entry signal rows: 957,643
- candidates with signals: 24
- signal artifact SHA-256:
  `1d5a3a9c89a2c8708968f409a8cf55f9cb68f9df66260a83ffd3d040b4f44114`

Frozen-entry exit-lab slice:

- `data/research/operator_runs/wpr106_31_discovery_lead_replay/ethusdt/frozen_entry_exit_lab_top3/discovery_exit_lab_manifest.json`
- selected leads: 3
- comparisons: 6
- decisions: `blocked: 3`
- blocker reason for all 3:
  `simple_runner_did_not_beat_fixed_holding|exit_lab_no_improving_exit_over_fixed_holding`

## Interpretation

WPR106-31 closes the gap between descriptor-only discovery leads and replayed
entry-signal evidence. BTC and ETH now both have:

- bounded replay specs;
- real replay discovery manifests;
- per-trial KNN prediction artifacts;
- per-trial strategy-accounting artifacts;
- 24 candidate IDs with annotated entry signals;
- a bounded frozen-entry exit-lab slice.

The top-3 exit-lab slices did not pass. That is a research rejection signal,
not a code failure.

The full 24-candidate exit-lab simulation was attempted first and exceeded the
20-minute shell command timeout before writing output. The packet therefore
records the complete replay/entry-signal evidence and a bounded top-3 exit-lab
slice. Full 24-candidate exit-lab, historical-cycle overlay ranking, multiple
testing, validation floors, and candidate-pack eligibility remain empirical
follow-up work.

## Remaining Gates

Still missing before any candidate-ready claim:

- historical-cycle overlay run from replayed KNN predictions;
- `candidate_rankings.parquet` from the cycle runner;
- `backtest_index.parquet` from the cycle runner;
- research candidate gate pass evidence;
- full exit-lab pass evidence;
- multiple-testing pass evidence;
- validation-floor pass evidence;
- candidate-pack eligibility pass evidence.

No P0/P1 issue was opened. The exit-lab runtime is a performance concern, but
the core evidence path is now reproducible and bounded.

## Validation

Passed:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_artifacts\test_candidate_pack.py -q
git diff --check
```

Observed:

- research-discovery tests: 221 passed;
- contracts: 427 passed;
- candidate-pack tests: 37 passed;
- `git diff --check` passed with CRLF warnings only.
