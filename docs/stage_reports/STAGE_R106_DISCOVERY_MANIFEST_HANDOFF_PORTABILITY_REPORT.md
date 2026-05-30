# Stage R106 Discovery Manifest Handoff Portability Report

Work packet: `docs/work_packets/WPR106-24-discovery-manifest-handoff-portability.md`

Date: 2026-05-29

## Summary

WPR106-24 fixes the latest autopilot failure without rewriting generated
research artifacts. The failed retry was
`run-research-autopilot-52719942d4604874a51a67489bbbe98a-restart-retry-1`.
It recovered from the stale autopilot state, completed the expensive ETH exact
discovery sweep, then failed while trying to review BTC candidate eligibility.

The failure was not missing BTC discovery evidence. The BTC exact-discovery
manifest and ledgers exist in the migrated checkout, but the generated
`required_outputs` inside the manifest still referenced the previous absolute
repo root, `C:\Users\papaa\Music\tradingbotsuite`. The candidate-eligibility
root guard rejected `blocked_candidates` as outside the configured research
output directory before the bridge could read the mirrored local evidence under
`C:\Users\papaa\Music\researchenginedeluxe`.

The fix rebases migrated discovery-manifest paths at read time. It preserves
source manifests, ledgers, trial JSONs, specs, fixture packs, and catalogs
unchanged.

## Latest Run Findings

- Job id:
  `run-research-autopilot-52719942d4604874a51a67489bbbe98a-restart-retry-1`.
- Final status: failed.
- Failure timestamp: `2026-05-28T22:15:17Z`.
- Failure class: migrated discovery manifest handoff path portability.
- Error:
  `research manifest required output must stay inside the configured research output directory: blocked_candidates`.
- Completed useful work:
  - stale autopilot retry was recovered and resumed;
  - ETH exact discovery completed to `570240/570240` trials;
  - ETH exact discovery wrote `23040` interesting rows, `547200` blocked rows,
    and `0` filter blockers;
  - ETH discovery manifest exists at
    `data/research/operator_runs/discovery_runs/exact-entry-sweep-ethusdt-candidate-depth-v1/discovery_run_manifest.json`;
  - BTC analysis delta ran before downstream candidate review;
  - BTC frozen-entry exit lab produced explicit blocked evidence with
    `frozen_entry_signals_missing`.
- Work not completed because of the failure:
  - BTC candidate eligibility review did not consume the mirrored discovery
    ledgers;
  - downstream current-output review and candidate-ready gate evidence remain
    incomplete;
  - no candidate pack, promotion artifact, live-readiness claim, sizing change,
    runtime-mode change, live config write, or order-placement path was
    introduced.

## Root Cause

WPR106-22 fixed active historical catalog and generated spec portability by
rebasing stale absolute paths from the old checkout root when a mirrored local
artifact exists. The later candidate-eligibility path consumed generated
discovery manifests directly, and discovery `required_outputs` keys such as
`blocked_candidates`, `interesting_candidates`, `filter_blockers`, `run_state`,
`trials`, and `snapshots` did not pass through that same normalizer.

The operator boundary check was correct to fail closed for paths outside the
configured research output root. The missing piece was a read-time migration
layer for copied operator-run discovery manifests. The source artifact remains
valid research evidence, but its embedded absolute handoff paths are stale.

## Changes Made

- `src/tradingbotsuite/data/historical_data_catalog.py`
  - Extended the shared operator-run path normalizer to treat discovery
    manifest `required_outputs` keys as path-like fields.
  - Keeps rebasing conditional on a matching mirrored local path or parent
    directory existing under the current run tree.
- `src/tradingbotsuite/operator_console.py`
  - Normalizes discovery manifests before candidate-eligibility
    root-boundary validation.
  - Maintains fail-closed behavior for truly outside paths.
- `src/tradingbotsuite/research_discovery/candidate_pack_bridge.py`
  - Reads discovery manifests through the same path normalizer before loading
    run state, ledgers, trials, and snapshots.
- `tests/tradingbotsuite/test_operator_ui.py`
  - Adds regression coverage for migrated discovery-manifest outputs accepted
    under the current research root.
  - Keeps the existing outside-root rejection coverage.
- `tests/research_discovery/test_candidate_pack_bridge.py`
  - Adds bridge-level regression coverage proving stale absolute
    `required_outputs` are rebased before the bridge reports missing ledgers.
- `docs/KNOWN_ISSUES.md`
  - Adds and resolves `ISSUE-R106-004`.

## Artifact Checks

Targeted metadata checks over the current BTC and ETH exact-discovery manifests
confirmed that read-time normalization keeps all `required_outputs` under
`data/research` and leaves no missing mirrored output paths:

```text
BTCUSDT bad [] missing []
ETHUSDT bad [] missing []
```

This is a portability fix only. The generated manifest JSON files were not
rewritten.

## Validation

Passed:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_candidate_pack_bridge.py::test_bridge_rebases_migrated_discovery_manifest_required_outputs -q
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py::test_operator_candidate_eligibility_service_rebases_migrated_manifest_outputs tests\tradingbotsuite\test_operator_ui.py::test_operator_candidate_eligibility_service_rejects_manifest_outputs_outside_root -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_candidate_pack_bridge.py -q
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_market_data_collection.py -q
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
```

Observed results:

- `tests/research_discovery/test_candidate_pack_bridge.py`: `30 passed`.
- `tests/tradingbotsuite/test_market_data_collection.py`: `31 passed`.
- `tests/tradingbotsuite/test_operator_ui.py`: `76 passed`.
- `tests/contracts`: `427 passed`.
- `tests/research_discovery`: `211 passed`.

## Remaining Work

The immediate P1 handoff bug is resolved. The next operator run should be able
to get past the BTC candidate-eligibility path-portability guard and continue
from the already completed BTC and ETH exact-discovery evidence.

Remaining empirical gates are still research work, not implementation
completion claims:

- rerun autopilot or candidate eligibility so BTC/ETH current outputs are
  reviewed through the now-portable discovery manifests;
- review the ETH exact-discovery output that completed in the failed retry;
- rerun or continue analysis, delta, exit-lab, and eligibility evidence where
  the failed retry stopped;
- keep `ISSUE-R104-001` open until refreshed catalog evidence, downstream
  cycles, exact sweeps, exit labs, multiple-testing, cost/funding stress, and
  eligibility gates support a candidate-ready research-only claim.

No production API, live execution, live config, runtime mode, order placement,
sizing behavior, candidate-pack write path, or promotion readiness was changed.
