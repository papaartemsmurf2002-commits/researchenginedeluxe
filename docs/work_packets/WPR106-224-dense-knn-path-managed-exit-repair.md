# WPR106-224 Dense KNN Path-Managed Exit Repair

Status: closed
Owner: Codex Research Agent
Created: 2026-06-13
Reconstructed: 2026-06-18 by WPR106-226 from summary JSON and ledger evidence after the prior markdown file was found NUL-filled.

## Objective

Test whether packet-local path-managed exits applied to fixed WPR106-223 dense
KNN selected signal paths can reduce losing-month frequency without using
May 2026 for tuning.

## Window Policy

- Selection window: 2024-01-01 through 2026-04-30.
- May 2026 trades loaded only after fixed selected rows were written.
- All outputs remain research-only, observe-only, promotion-ready false.

## Allowed Paths

- `docs/work_packets/WPR106-224-dense-knn-path-managed-exit-repair.md`
- `docs/stage_reports/STAGE_R106_DENSE_KNN_PATH_MANAGED_EXIT_REPAIR_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only for blocking risks
- `data/research/wpr106_224*/**`

## Evidence Summary

- Source selected rows: 71.
- Source pre-May trade rows: 21,060.
- Exit policies evaluated: 36.
- Pre-May policy rows: 2,556.
- Positive pre-May policy rows: 552.
- Annual-target rows: 16; strict rows: zero.
- Fixed selected set: 140 rows.
- Selected pre-May median return: +0.314421.
- Selected pre-May median active months: 21.
- Selected pre-May median losing months: seven.
- May benchmark: 73 positive, zero negative, 67 flat; median May +0.000994.

## Decision

Rejected as candidate-ready, portfolio-ready, paper/live-ready, or
promotion-ready. Path exits improved WPR106-223 median return and reduced
median losing months from eight to seven, but strict rows remained absent and
active coverage dropped. Useful lead: `flow_wick_density` with two-loss-month
veto and target-only exits.

## Validation

Passed:

```powershell
python -m compileall -q data\research\wpr106_224_dense_knn_path_managed_exit_repair\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
