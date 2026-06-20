# WPR106-220 WPR199 Source-Control Stability Expansion

Status: closed
Owner: Codex Research Agent
Created: 2026-06-13
Reconstructed: 2026-06-18 by WPR106-226 from summary JSON and ledger evidence after the prior markdown file was found NUL-filled.

## Objective

Expand the WPR106-219 same-direction WPR106-199 control clue by testing full
WPR106-199 source controls against WPR106-188 negative-control sources under
the 2024-forward pre-May selection policy.

## Window Policy

- Selection window: 2024-01-01 through 2026-04-30.
- May 2026 benchmark loaded only after fixed selected rows were written.
- All outputs remain research-only, observe-only, promotion-ready false.

## Allowed Paths

- `docs/work_packets/WPR106-220-wpr199-source-control-stability-expansion.md`
- `docs/stage_reports/STAGE_R106_WPR199_SOURCE_CONTROL_STABILITY_EXPANSION_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only for blocking risks
- `data/research/wpr106_220*/**`

## Evidence Summary

- Evaluated 26,496 source/filter/gate combinations.
- Materialized 24,632 pre-May variant rows.
- Found 21,833 positive pre-May rows, 3,157 annual-target rows, and 152 strict rows.
- Fixed selected set: 120 rows.
- Selected pre-May median return: +0.637255.
- Selected pre-May median active months: 26.
- Selected pre-May median losing months: four.
- Selected pre-May strict rows: 59.
- May benchmark: 29 positive, 86 negative, five flat; median May -0.005859.

## Decision

Rejected as candidate-ready, portfolio-ready, paper/live-ready, or
promotion-ready. Pre-May WPR106-199 source controls looked strong, but the
May 2026 benchmark failed. WPR106-188 failed as expected and remains a useful
negative-control reference. WPR106-199 can be used as diagnostic/control
evidence but should not dominate future selectors without pseudo-holdout or
source-family caps.

## Validation

Passed per ledger closeout:

```powershell
python -m compileall -q data\research\wpr106_220_wpr199_source_control_stability_expansion\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```
