# WPR106-25 Cycle Manifest Evidence Portability

## Summary

Fix the follow-up autopilot failure after WPR106-24. The latest run got past
the prior discovery `blocked_candidates` portability failure, skipped completed
BTC/ETH cycle and exact-discovery artifacts, then failed during BTC candidate
eligibility because the BTC historical-cycle manifest still contains stale
absolute `required_outputs` paths from the old checkout root.

This packet keeps generated artifacts immutable. It broadens read-time
operator-run path normalization so historical-cycle evidence outputs such as
`ablation_report` are rebased to the mirrored current checkout, and ensures the
candidate-pack gate evaluator consumes normalized cycle manifests instead of
reading stale absolute paths directly.

## Allowed Paths

- `docs/work_packets/WPR106-25-cycle-manifest-evidence-portability.md`
- `docs/stage_reports/STAGE_R106_CYCLE_MANIFEST_EVIDENCE_PORTABILITY_REPORT.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/data/historical_data_catalog.py`
- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/research_artifacts/candidate_pack.py`
- `tests/tradingbotsuite/test_operator_ui.py`
- `tests/research_artifacts/test_candidate_pack.py`

## Findings

- Latest autopilot run:
  `run-research-autopilot-d77072dd939744e296edbddac253e29b`.
- It failed quickly during BTC `candidate_eligibility`.
- Error:
  `research manifest required output must stay inside the configured research output directory: ablation_report`.
- It confirmed WPR106-24 worked for discovery handoff because the previous
  `blocked_candidates` failure did not recur.
- BTC historical-cycle manifests under the current checkout still record
  stale `required_outputs` paths under
  `C:\Users\papaa\Music\tradingbotsuite`.
- Mirrored cycle evidence files exist under the current checkout.

## Implementation Plan

1. Open and resolve a P1 issue for migrated historical-cycle evidence outputs
   blocking candidate eligibility.
2. Broaden the shared operator-run artifact normalizer so exact absolute local
   path strings can rebase when a matching mirrored anchor exists, not only
   keys ending in `_path` or known discovery keys.
3. Keep the operator root guard fail-closed for genuinely outside paths.
4. Normalize cycle manifests inside the candidate-pack gate evaluator before
   resolving `required_outputs`.
5. Add regressions for:
   - operator candidate eligibility accepting mirrored migrated cycle
     `required_outputs.ablation_report`;
   - candidate-pack gate evaluation reading rebased migrated cycle evidence;
   - outside-root paths still rejected when no mirrored local path exists.
6. Run focused validation and baseline checks.

## Non-Goals

- Do not rewrite generated historical-cycle manifests or evidence files.
- Do not rerun historical cycles, exact discovery, exit labs, or candidate
  eligibility in this packet.
- Do not change live execution, runtime mode, sizing, order placement, live
  configuration, candidate-pack writing, or promotion readiness.

## Acceptance Criteria

- The latest BTC historical-cycle manifest can pass operator candidate
  eligibility root-boundary checks through read-time rebasing.
- Candidate-pack gate evaluation reads mirrored current-checkout evidence
  instead of old-checkout paths.
- Truly outside manifest outputs still fail closed.
- `ISSUE-R106-005` is resolved or remains open with explicit blocker evidence.
- Validation results are recorded in the stage report.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_artifacts\test_candidate_pack.py -q
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```
