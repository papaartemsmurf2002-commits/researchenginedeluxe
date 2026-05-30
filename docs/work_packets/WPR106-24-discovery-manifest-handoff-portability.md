# WPR106-24 Discovery Manifest Handoff Portability

## Summary

Fix the R106 migrated-checkout failure discovered by the latest autopilot retry.
The retry completed ETH exact discovery, then failed during BTC candidate
eligibility because the completed BTC discovery manifest still contained stale
absolute `required_outputs` paths from the old checkout root
`C:\Users\papaa\Music\tradingbotsuite`.

This packet keeps generated artifacts immutable. It rebases migrated
operator-run paths at read time for discovery manifests consumed by operator
eligibility and the discovery candidate-pack bridge.

## Allowed Paths

- `docs/work_packets/WPR106-24-discovery-manifest-handoff-portability.md`
- `docs/stage_reports/STAGE_R106_DISCOVERY_MANIFEST_HANDOFF_PORTABILITY_REPORT.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/data/historical_data_catalog.py`
- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/research_discovery/candidate_pack_bridge.py`
- `tests/tradingbotsuite/test_operator_ui.py`
- `tests/research_discovery/test_candidate_pack_bridge.py`

## Findings

- Latest autopilot retry:
  `run-research-autopilot-52719942d4604874a51a67489bbbe98a-restart-retry-1`.
- It completed ETH exact discovery to `570240/570240` trials.
- It then failed during BTC candidate eligibility with
  `research manifest required output must stay inside the configured research output directory: blocked_candidates`.
- BTC discovery manifest exists in the current checkout, but its
  `required_outputs` still point at `C:\Users\papaa\Music\tradingbotsuite`.
- Mirrored BTC ledger files exist under the current checkout at
  `C:\Users\papaa\Music\researchenginedeluxe`.

## Implementation Plan

1. Open and resolve a P1 known issue for migrated discovery manifests whose
   generated `required_outputs` still point at the old checkout root.
2. Update the operator candidate-eligibility manifest guard to normalize
   migrated operator-run paths before root-boundary validation.
3. Update the discovery candidate-pack bridge to read discovery manifests
   through the same normalization path before loading required ledgers and run
   state.
4. Add regressions proving:
   - migrated discovery manifest outputs are accepted when mirrored local files
     exist under the current research root;
   - truly outside manifest outputs remain rejected;
   - the bridge itself reads rebased migrated manifest outputs.
5. Run focused validation and baseline checks.

## Non-Goals

- Do not rewrite generated discovery manifests, ledgers, trial records, specs,
  or candidate artifacts.
- Do not rerun ETH exact discovery.
- Do not change live execution, runtime mode, sizing, order placement, or
  promotion readiness.
- Do not mark any candidate pack as ready.

## Acceptance Criteria

- BTC/ETH generated discovery manifests with mirrored stale absolute
  `required_outputs` are consumable by candidate eligibility.
- Discovery manifests with truly outside `required_outputs` still fail closed.
- Candidate-pack bridge can read rebased ledgers/run state without mutating the
  source manifest.
- `ISSUE-R106-004` is resolved or remains open with explicit blocker evidence.
- Validation results are recorded in the stage report.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_candidate_pack_bridge.py -q
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```
