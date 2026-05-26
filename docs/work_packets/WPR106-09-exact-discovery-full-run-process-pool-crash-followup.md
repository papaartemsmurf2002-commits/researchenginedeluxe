# WPR106-09 Exact Discovery Full Run Process Pool Crash Followup

Status: complete

## Scope

Investigate the latest BTC candidate-depth exact-discovery full run after it
ran for roughly 14 hours and stopped before completion.

- Compare durable trial files, `run_state.json`, snapshots, and manifest state.
- Identify whether the run lost progress, restarted, stalled, or failed during
  a process-pool batch.
- Tune the default full-run process concurrency toward memory-safe completion
  while preserving explicit operator overrides.
- Record the recovery status and next operator action.

## Allowed paths

- `src/tradingbotsuite/research_discovery/runner.py`
- `tests/research_discovery/test_discovery_runner.py`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/work_packets/WPR106-09-exact-discovery-full-run-process-pool-crash-followup.md`
- `docs/stage_reports/STAGE_R106_EXACT_DISCOVERY_FULL_RUN_PROCESS_POOL_CRASH_FOLLOWUP_REPORT.md`

## Constraints

- Do not delete or rewrite active discovery trial records.
- Do not mark the BTC exact discovery complete unless all planned trials finish.
- Preserve research-only, observe-only, and `promotion_ready: false` semantics.
- Do not weaken discovery gates or reinterpret incomplete evidence as
  candidate-ready.

## Acceptance

- Latest run state is explained with concrete completed/trial-file counts.
- Root cause is recorded with the impacted cache group/batch.
- Default process settings reduce the observed crash risk for resume.
- Focused discovery tests pass.

## Closure

The latest BTC exact-discovery output was recovered in place. Before recovery,
`run_state.json` had 407420 completed IDs while 407669 durable trial JSON files
existed. A zero-trial resume now merges only lagging trial files for large
resumes, bringing state and hashes to 407669/407669 without starting discovery
compute or hydrating the full trial corpus.

The stopped run left one partial cache-affinity group:
`price_trend_vol / none / 2h / cosine / hmm_state=3 / posterior=0.55 /
entropy=0.78 / k=8`, with 4469 of 5760 trials complete. The failure is
consistent with another process-pool worker termination under concurrent exact
KNN base memory pressure rather than lost artifacts or a clean completion.

Default real-discovery process workers were briefly capped at 4 in this packet,
then WPR106-10 restored the performance-first default to 8 after operator
direction that throughput outweighs instability risk. Operators can still set
`TBS_DISCOVERY_REAL_PROCESS_MAX_WORKERS` explicitly. Large resumes use
`run_state.json` as the authoritative completed-ID checkpoint, validate that
state-referenced trial files still exist, recover only trial files that are
ahead of state, skip real-context preparation when `stop_after_trials=0`, avoid
overwriting candidate ledgers from a partial in-memory subset, and rebuild full
ledgers from trial records only when a run completes.

Validation:

- `python -m compileall -q src\tradingbotsuite\research_discovery`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_discovery_runner.py -q`
- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
