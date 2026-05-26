# Stage R105 Secure Handoff Export Hygiene Report

Date: 2026-05-19
Owner: Codex Research Agent
Stage: R105 candidate factory component falsification
Status: secure handoff config complete

## Research Boundary

This packet adds a conservative handoff/export configuration and a contract
test. It does not run research, generate candidate evidence, write live
configuration, place orders, change runtime mode, touch sizing, or alter
promotion behavior.

## Implemented

- Added `configs/handoff/r105_secure_repo_export.json`.
- Added `tests/contracts/test_r105_secure_handoff_export_config.py`.

The config includes source code, checked configs, docs, tests, README files,
`AGENTS.md`, `START_HERE.md`, and packaging metadata.

The config excludes:

- `data/**`
- `**/operator_runs/**`
- `.env` files
- secret, API-key, private-key, secret-key, and credential-like paths
- caches and Python bytecode
- virtual environments
- Parquet files
- SQLite/database files
- logs
- ZIP archives
- CSV exports

Security checks are explicitly enabled with `blockOnPotentialSecret: true`.
The config also carries research-only boundary metadata with
`promotion_ready: false` and all live input/control flags set to `false`.

## Validation

Passed:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_r105_secure_handoff_export_config.py -q
```

Result:

- `2 passed`

## Issue State

No issue was closed by this packet. `ISSUE-R104-001` remains open because it
requires expanded durable BTC/ETH primary-bar fixture evidence and reruns, not
handoff/export hygiene.
