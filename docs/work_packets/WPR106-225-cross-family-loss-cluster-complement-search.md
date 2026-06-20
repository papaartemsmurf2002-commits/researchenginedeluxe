# WPR106-225 Cross-Family Loss-Cluster Complement Search

Status: closed
Owner: Codex Research Agent
Created: 2026-06-13
Reconstructed: 2026-06-18 by WPR106-226 from summary JSON and ledger evidence after the prior markdown file was found NUL-filled.

## Objective

Test whether costed selected paths from different research families can
complement each other's loss clusters and improve month-to-month stability
without using May 2026 for tuning.

## Window Policy

- Selection window: 2024-01-01 through 2026-04-30.
- May 2026 source trades loaded only after fixed selected rows and selected
  pre-May replay artifacts were written.
- All outputs remain research-only, observe-only, promotion-ready false.

## Source Artifacts

- WPR106-220 WPR199 source-control stability expansion.
- WPR106-221 transparent motif active fallback repair.
- WPR106-222 directional KNN source stability repair.
- WPR106-224 dense KNN path-managed exit repair.

## Allowed Paths

- `docs/work_packets/WPR106-225-cross-family-loss-cluster-complement-search.md`
- `docs/stage_reports/STAGE_R106_CROSS_FAMILY_LOSS_CLUSTER_COMPLEMENT_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only for blocking risks
- `data/research/wpr106_225*/**`

## Evidence Summary

- Source rows loaded: 560.
- Source pre-May trades loaded: 215,710.
- Source component pool: 56 rows.
- Portfolio specs evaluated: 14,040.
- Pre-May ranking: 13,914 positive rows, 10,648 loose rows, 4,236 annual-target rows, 1,569 strict rows.
- Fixed selected set: 180 rows.
- Selected pre-May median return: +0.612399.
- Selected pre-May median active months: 27.
- Selected pre-May median losing months: four.
- Selected pre-May strict rows: 80 and annual-target rows: 140.
- May benchmark: two positive, 178 negative; median May -0.005795.

## Decision

Rejected as candidate-ready, portfolio-ready, paper/live-ready, or
promotion-ready. The pre-May selector looked strong but over-selected WPR106-220.
Every selected cross-family complement was negative in May. Future complement
work needs source-family caps or pseudo-holdouts before selecting portfolios.

## Validation

Passed:

```powershell
python -m compileall -q data\research\wpr106_225_cross_family_loss_cluster_complement_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
