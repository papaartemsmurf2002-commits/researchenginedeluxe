# WPR105-99 Final Crosscheck And Performance Validation

Owner: Codex Research Agent
Stage: R105 candidate factory component falsification
Status: closed
Created: 2026-05-19

## Goal

Run a final autonomous crosscheck of the R105 work completed in this pass,
including full test coverage and local performance benchmark evidence. Fix any
code, contract, research-boundary, or documentation issue discovered during
validation if it can be addressed within the current research-only branch
rules.

## Allowed paths

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/work_packets/**`
- `docs/stage_reports/**`
- `configs/**`
- `src/tradingbotsuite/**`
- `tests/**`

## Constraints

- Preserve the research boundary: no live execution, no order placement, no
  runtime-mode mutation, no live configuration writes, no promotion behavior,
  and no sizing behavior.
- Do not mark research artifacts `promotion_ready: true`.
- Do not close `ISSUE-R104-001` unless expanded durable BTC/ETH primary-bar
  fixtures and rerun evidence actually exist.
- Treat benchmark reports as local regression guardrails, not profitability,
  live-readiness, or production speedup claims.

## Planned validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest -q
$env:PYTHONPATH='src'; python -m tradingbotsuite.main benchmark-discovery-run --tier quick --repeat 2 --output-dir operator_runs\r105\final_crosscheck\benchmarks\discovery_quick
$env:PYTHONPATH='src'; python -m tradingbotsuite.main benchmark-historical-research-cycle --tier small --repeat 2 --output-dir operator_runs\r105\final_crosscheck\benchmarks\historical_small
git diff --check
```

## Exit evidence

- Fixed the final full-suite failure in historical research-cycle benchmark
  report self-accounting: `artifact_overhead.final_report_bytes` now matches
  the actual final report file size after final write.
- Removed the inconsistent R105 postmortem no-regime fast hash path. The
  component factory now uses the shared artifact-key helper for effective
  trial keys, prediction signatures, and entry-event signatures.
- Tightened the secure handoff exclude patterns so source files such as
  `artifact_keys.py` and `test_artifact_keys.py` are not excluded by an
  over-broad `**/*key*` rule while API/private/secret-key-like paths remain
  excluded.
- Added `docs/stage_reports/STAGE_R105_R104_POSTMORTEM_TRACKED_SUMMARY.json`
  so the committed audit trail has a sanitized R105 postmortem summary even
  though the generated parquet/operator-run artifacts remain ignored local
  evidence.
- Added compact discovery compute telemetry to discovery benchmark run payloads
  so benchmark reports directly expose `discovery-compute-telemetry-v2`
  utilization and artifact-write diagnostics.
- Regenerated the local R105 postmortem under
  `data\research\operator_runs\r105\postmortem_r104` after the shared-key fix.
- Validation passed:
  `python -m compileall -q src\tradingbotsuite`;
  `$env:PYTHONPATH='src'; python -m pytest -q`
  (`1374 passed, 1 skipped`);
  `$env:PYTHONPATH='src'; python -m tradingbotsuite.main benchmark-discovery-run --tier quick --repeat 2 --output-dir operator_runs\r105\final_crosscheck\benchmarks\discovery_quick`
  (gate passed, evidence complete);
  `$env:PYTHONPATH='src'; python -m tradingbotsuite.main benchmark-historical-research-cycle --tier small --repeat 2 --output-dir operator_runs\r105\final_crosscheck\benchmarks\historical_small`
  (gate passed, evidence complete);
  `git diff --check` passed with CRLF normalization warnings only.
