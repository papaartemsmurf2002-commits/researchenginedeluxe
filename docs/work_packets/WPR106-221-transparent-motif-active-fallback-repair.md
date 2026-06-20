# WPR106-221 Transparent Motif Active Fallback Repair

Status: closed
Owner: Codex Research Agent
Created: 2026-06-13
Reconstructed: 2026-06-18 by WPR106-226 from summary JSON and ledger evidence after the prior markdown file was found NUL-filled.

## Objective

Revisit the WPR106-214 transparent motif replacement family by adding causal
fallback sleeves in months where the primary opening-plus-motif sleeve is
gate-disabled.

## Window Policy

- Selection window: 2024-01-01 through 2026-04-30.
- May 2026 benchmark loaded only after fixed selected rows were written.
- All outputs remain research-only, observe-only, promotion-ready false.

## Allowed Paths

- `docs/work_packets/WPR106-221-transparent-motif-active-fallback-repair.md`
- `docs/stage_reports/STAGE_R106_TRANSPARENT_MOTIF_ACTIVE_FALLBACK_REPAIR_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only for blocking risks
- `data/research/wpr106_221*/**`

## Evidence Summary

- Evaluated 13,824 pre-May rows.
- Found 13,534 positive rows, 24 annual-target rows, 7,404 loose rows, and zero strict rows.
- Fixed selected set: 140 loose active fallback rows.
- Selected pre-May median return: +0.446878.
- Selected pre-May median active months: 27.
- Selected pre-May median losing months: six.
- May benchmark: 113 positive, 27 negative; median May +0.011323.

## Decision

Rejected as candidate-ready, portfolio-ready, paper/live-ready, or
promotion-ready. This remains a useful lead because fallback opening sleeves
improved active coverage and May transfer, but the annual loss-month profile
still misses the target.

## Validation

Passed per ledger closeout:

```powershell
python -m compileall -q data\research\wpr106_221_transparent_motif_active_fallback_repair\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```
