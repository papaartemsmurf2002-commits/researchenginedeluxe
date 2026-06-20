# WPR106-222 Directional KNN Source Stability Repair

Status: closed
Owner: Codex Research Agent
Created: 2026-06-13
Reconstructed: 2026-06-18 by WPR106-226 from summary JSON and ledger evidence after the prior markdown file was found NUL-filled.

## Objective

Revisit the Lorentzian/KNN family from source-level evidence by using selected
WPR106-190 directional KNN and WPR106-213 regime-conditioned Lorentzian/KNN
trade paths before portfolio composition.

## Window Policy

- Selection window: 2024-01-01 through 2026-04-30.
- May 2026 benchmark loaded only after fixed selected rows were written.
- All outputs remain research-only, observe-only, promotion-ready false.

## Allowed Paths

- `docs/work_packets/WPR106-222-directional-knn-source-stability-repair.md`
- `docs/stage_reports/STAGE_R106_DIRECTIONAL_KNN_SOURCE_STABILITY_REPAIR_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only for blocking risks
- `data/research/wpr106_222*/**`

## Evidence Summary

- Loaded 200 source components, searched 84, materialized 5,518 variants.
- Selected 60 variants and built 266 bundles.
- Evaluated 17,024 pre-May portfolio rows; all were positive.
- Found 4,686 annual-target rows and 380 strict rows.
- Fixed selected set: 160 rows.
- Selected pre-May median return: +0.464644.
- Selected pre-May median active months: 24.
- Selected pre-May median losing months: five.
- May benchmark: 137 positive, zero negative, 23 flat; median May +0.001407.

## Decision

Rejected as candidate-ready, portfolio-ready, paper/live-ready, or
promotion-ready because May transfer was too sparse and no row combined all
28 active pre-May months with five or fewer losing months. Useful evidence:
source-before-portfolio KNN gates and mixed WPR106-190/WPR106-213 pairs improve
pre-May annual loss profile and keep May nonnegative.

## Validation

Passed per ledger closeout:

```powershell
python -m compileall -q data\research\wpr106_222_directional_knn_source_stability_repair\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```
