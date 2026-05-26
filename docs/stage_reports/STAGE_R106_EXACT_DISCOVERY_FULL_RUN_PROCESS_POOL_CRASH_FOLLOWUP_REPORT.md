# Stage R106 Exact Discovery Full Run Process Pool Crash Followup

Date: 2026-05-24
Work packet: `docs/work_packets/WPR106-09-exact-discovery-full-run-process-pool-crash-followup.md`

## Scope

Investigate the latest BTCUSDT candidate-depth exact-discovery run after it ran
for roughly 14 hours and stopped before completion. Preserve all durable
research artifacts, recover checkpoint lag, and harden the resume path before
the next operator restart.

## Findings

- Active output:
  `data/research/operator_runs/discovery_runs/exact-entry-sweep-btcusdt-candidate-depth-v1`
- Before recovery, `run_state.json` reported 407420 completed trials while
  407669 durable `trials/*.json` files existed. The manifest was stale at 512
  completed trials.
- No active Python discovery worker was alive when inspected, and the default
  operator SQLite job log did not contain a newer 14-hour job record for this
  run. The durable trial files are therefore the authoritative progress
  evidence.
- The stopped run left one partial cache-affinity group:
  `price_trend_vol / none / 2h / cosine / hmm_state=3 / posterior=0.55 /
  entropy=0.78 / k=8`, 4469 of 5760 complete.
- The observed failure shape matches another process-pool worker termination
  under concurrent exact KNN base memory pressure. It does not indicate that
  completed trial files were lost.

## Fix

- WPR106-09 initially lowered the default real-discovery process worker cap
  from 8 to 4 while preserving the explicit operator override
  `TBS_DISCOVERY_REAL_PROCESS_MAX_WORKERS`. WPR106-10 then restored the
  performance-first default to 8 after operator direction that throughput
  outweighs instability risk for the current study.
- Added a large-resume catalog path. When trial-file count exceeds
  `TBS_DISCOVERY_RESUME_FULL_RECORD_LOAD_LIMIT` (default 100000), resume uses
  `run_state.json` as the completed-ID checkpoint, validates that completed
  trial files exist, and reads only trial files that are ahead of state.
- Skipped real-discovery context preparation when `stop_after_trials=0`, so
  metadata-only recovery does not allocate the feature/KNN context.
- Prevented incomplete large resumes from overwriting candidate ledgers with
  a partial in-memory record subset. Full ledgers are rebuilt from trial JSON
  records only when the run completes.
- Manifest and snapshot counts now report accurate completed-trial count from
  state during partial large resumes and label the count scope.

## Recovery Evidence

After the zero-trial recovery resume:

- `run_state.json` status: `in_progress`
- Completed IDs: 407669
- Completed hashes: 407669
- Durable trial files: 407669
- Planned trials: 570240
- Remaining trials: 162571
- Recovered lagging files: 249
- Snapshot count: 86
- Manifest resume mode:
  `state_checkpoint_with_lagging_trial_file_recovery`

The run remains research-only, observe-only, and `promotion_ready: false`.

## Validation

- `python -m compileall -q src\tradingbotsuite\research_discovery`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_discovery_runner.py -q`
  - 24 passed
- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - 427 passed

## Operator Next Action

Resume BTC exact discovery from the existing run. The next run should skip the
407669 completed trials and continue from the remaining 162571 pending trial
IDs with the performance-first 8-worker default unless the operator explicitly
overrides it.
