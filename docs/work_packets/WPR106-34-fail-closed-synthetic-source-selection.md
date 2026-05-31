# WPR106-34 Fail-Closed Synthetic Source Selection

## Goal

Close `ISSUE-R106-010` by making historical research-cycle data loading fail
closed when no real source is declared and synthetic data is not explicitly
requested. Also record source-selection evidence in successful cycle manifests.

This packet must preserve synthetic fixture support for tests and demos, while
making synthetic evidence explicit, non-promotable, and ineligible for
candidate-ready claims.

## Current Repo Facts

- `CycleDataSpec` parses `synthetic_fixture`, but not
  `synthetic_fallback_allowed`.
- Several checked-in configs declare `synthetic_fallback_allowed: false`, but
  the field is currently not part of the parsed contract.
- `_load_cycle_dataset()` currently synthesizes data when `synthetic_fixture`
  is true or when no data source is declared.
- Candidate-pack gates already reject synthetic and non-ready source evidence,
  but the historical-cycle data loader can still silently synthesize if a spec
  omits sources.
- Discovery missing-data paths already fail with real-data-required behavior.

## Conflicts And Stale Docs Found

- Existing tests use explicit `synthetic_fixture: true` heavily for fast
  contract and cycle coverage. Those tests remain valid as demo/test-only
  synthetic runs.
- Existing blocked ETH blueprint tests expect missing real source paths to fail
  closed. This packet should preserve that behavior.

## Allowed Edit Paths

- `docs/work_packets/WPR106-34-fail-closed-synthetic-source-selection.md`
- `src/tradingbotsuite/research_cycle/spec.py`
- `src/tradingbotsuite/research_cycle/runner.py`
- `tests/contracts/test_research_cycle_contract.py`
- `tests/historical/test_full_cycle_synthetic.py`
- `tests/historical/test_full_cycle_local_fixture_pack.py`
- `docs/ACTIVE_INDEX.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/STAGE_R106_FAIL_CLOSED_SYNTHETIC_SOURCE_SELECTION_REPORT.md`

## Forbidden Edit Paths

- `configs/**`
- `data/research/**`
- fixture packs
- generated operator-run artifacts
- live/runtime/promotion/sizing/order-placement behavior
- strategy/model/filter implementations
- `.pytest_cache/**`

## Subagents Used

- P0-C source/synthetic fallback explorer.

## Tests To Run

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py tests\historical\test_full_cycle_synthetic.py tests\historical\test_full_cycle_local_fixture_pack.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

## Artifacts Expected

- Source-selection evidence in successful historical-cycle manifests.
- Focused tests proving no-source specs no longer synthesize silently.
- Updated issue registry and stage report.

No generated committed research data artifacts or candidate packs are expected.

## Definition Of Done

- `synthetic_fallback_allowed` is parsed and round-tripped.
- A spec with no dataset path, no dataset manifests, no local fixture dir, and
  `synthetic_fixture: false` fails closed instead of synthesizing data.
- Explicit synthetic runs still work and are labeled test/demo-only,
  `research_only`, `observe_only`, and `promotion_ready: false`.
- Source-selection evidence records selected/skipped source candidates in
  successful cycle manifests.
- `ISSUE-R106-010` is resolved only after validation passes.

## Rollback Plan

Revert only the files in the allowed edit paths for this packet. Do not touch
fixture packs, generated operator artifacts, or unrelated docs/cache state.
