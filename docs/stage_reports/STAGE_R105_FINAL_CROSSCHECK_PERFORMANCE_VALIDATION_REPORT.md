# Stage R105 Final Crosscheck Performance Validation Report

Date: 2026-05-19
Owner: Codex Research Agent
Stage: R105 candidate factory component falsification
Status: final crosscheck complete; candidate-ready evidence still blocked by ISSUE-R104-001

## Research Boundary

This packet performed validation and narrow research-only fixes. It did not
place orders, change runtime mode, write live configuration, touch sizing,
promote a candidate, or mark any research artifact `promotion_ready: true`.

## Fixes

- Historical benchmark final-report byte accounting now reconciles
  `artifact_overhead.final_report_bytes` with the actual final report file
  size.
- R105 postmortem effective-trial and signature hashes now consistently use the
  shared artifact-key helpers.
- Secure handoff excludes no longer drop normal source/test files with `key` in
  the filename, while API/private/secret-key-like paths remain excluded.
- A tracked sanitized R105 postmortem summary was added at
  `docs/stage_reports/STAGE_R105_R104_POSTMORTEM_TRACKED_SUMMARY.json`; the
  larger local parquet/operator-run artifacts remain ignored generated
  evidence.
- Discovery benchmark reports now include compact child-run
  `compute_telemetry` payloads, including `discovery-compute-telemetry-v2`
  utilization and artifact-write diagnostics.

## Performance Evidence

Discovery benchmark:

- Command:
  `$env:PYTHONPATH='src'; python -m tradingbotsuite.main benchmark-discovery-run --tier quick --repeat 2 --output-dir operator_runs\r105\final_crosscheck\benchmarks\discovery_quick`
- Gate: passed
- Evidence complete: yes
- Mean completed trials: `3.0`
- Mean full elapsed seconds: `0.201139`
- Mean resumed elapsed seconds: `0.128462`
- Resumed child telemetry: `discovery-compute-telemetry-v2`, `1` active
  worker, `16` logical CPUs, about `955` trials/minute, artifact-write pressure
  flagged for the small artifact-heavy quick benchmark.

Historical-cycle benchmark:

- Command:
  `$env:PYTHONPATH='src'; python -m tradingbotsuite.main benchmark-historical-research-cycle --tier small --repeat 2 --output-dir operator_runs\r105\final_crosscheck\benchmarks\historical_small`
- Gate: passed
- Evidence complete: yes
- Mean elapsed seconds: `2.970509`
- Mean rows/second: `599.924665`
- Mean candidate backtests/minute: `385.303729`
- Mean feature rows/second: `1278.142324`
- Synthetic optimizer parallel evaluator: measured, `32` candidates,
  `4` workers, median serial `0.669559` seconds, median parallel `0.185008`
  seconds, speedup factor `3.619069`, result hashes equal, stability-region
  hashes equal.
- Artifact overhead: `1369` files, `14163027` bytes,
  `372711.236842` bytes per candidate backtest, final report byte count
  reconciled.

These are local regression guardrails and timing observations, not production
speedup, profitability, live-readiness, or candidate-ready claims.

## Validation

Passed:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest -q
$env:PYTHONPATH='src'; python -m tradingbotsuite.main benchmark-discovery-run --tier quick --repeat 2 --output-dir operator_runs\r105\final_crosscheck\benchmarks\discovery_quick
$env:PYTHONPATH='src'; python -m tradingbotsuite.main benchmark-historical-research-cycle --tier small --repeat 2 --output-dir operator_runs\r105\final_crosscheck\benchmarks\historical_small
git diff --check
```

Results:

- full pytest: `1374 passed, 1 skipped`
- discovery benchmark gate: passed, evidence complete
- historical benchmark gate: passed, evidence complete
- `git diff --check`: passed with CRLF normalization warnings only

## Issue State

`ISSUE-R104-001` remains open. Expanded durable BTC/ETH primary-bar fixtures
and reruns are still required before candidate-ready claims.
