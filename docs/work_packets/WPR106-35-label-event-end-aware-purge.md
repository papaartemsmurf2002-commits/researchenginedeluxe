# WPR106-35 Label Event-End-Aware Purge

## Goal

Close `ISSUE-R106-011` by adding explicit label/event-end metadata to the
walk-forward split engine and using event-end-aware train-row purging where
label-producing research paths can otherwise leak long or overlapping labels.

This packet must preserve the research-only boundary. Zero safe training rows
or zero eligible candidates is valid evidence.

## Current Repo Facts

- `build_purged_walk_forward_splits()` currently cuts training with
  `validation_start - purge_embargo_bars - 1`.
- `WalkForwardSplit` exposes contiguous train start/end indices, and several
  consumers slice training frames from those bounds.
- Legacy research datasets can contain `label_exit_time_ms`,
  `label_interval_end_ms`, and `label_future_end_time_ms`.
- Discovery labels are generated in `_with_directional_labels()` from a
  configured label horizon, but that path does not currently stamp an event-end
  timestamp for the generic split engine.
- Discovery KNN has an additional source-row horizon filter, but the split
  contract itself does not prove event-end-aware purge.
- Historical-cycle split manifests include split payloads and can carry purge
  method evidence once the split engine exposes it.

## Conflicts And Stale Docs Found

- `docs/KNOWN_ISSUES.md` correctly lists `ISSUE-R106-011` as open.
- Older docs and tests still describe fixed-bar `purge_embargo_bars`; this
  remains a fallback only when no event-end label metadata is available and must
  be visible in split payloads/manifests.
- Some split consumers assume contiguous training rows. Event-end-aware purge
  may produce non-contiguous safe rows when labels overlap, so training-row
  consumers need to honor explicit train indices.

## Allowed Edit Paths

- `docs/work_packets/WPR106-35-label-event-end-aware-purge.md`
- `src/tradingbotsuite/backtesting/splits.py`
- `src/tradingbotsuite/features/split_transforms.py`
- `src/tradingbotsuite/research_cycle/runner.py`
- `src/tradingbotsuite/research_discovery/runner.py`
- `src/tradingbotsuite/research_discovery/hmm_materialization.py`
- `src/tradingbotsuite/research_discovery/knn_study.py`
- `tests/backtesting/test_splits.py`
- focused research-discovery tests if needed
- focused historical-cycle tests if needed
- `docs/ACTIVE_INDEX.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/STAGE_R106_LABEL_EVENT_END_AWARE_PURGE_REPORT.md`

## Forbidden Edit Paths

- live/runtime/order-placement modules
- promotion logic or candidate-gate weakening
- strategy/model/filter implementations unrelated to split safety
- data fixtures except temporary pytest output
- generated operator-run artifacts
- `.pytest_cache/**`

## Subagents Used

- Validation Engineer: inspect current split API, downstream training-frame
  consumers, and focused tests before implementation.

## Tests To Run

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\backtesting\test_splits.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_hmm_materialization.py tests\research_discovery\test_knn_study.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Broaden to historical-cycle tests if the cycle split manifest contract changes
in a way that focused tests do not cover.

## Artifacts Expected

- Split payloads/manifests identifying `purge_method`.
- Event-end-aware split tests proving unsafe overlapping train labels are
  excluded.
- Discovery label frames with explicit event-end timestamps.
- Updated issue registry and stage report.

No generated research data artifacts or candidate packs are expected.

## Definition Of Done

- A `LabelSpec` or equivalent explicit split contract exists.
- Event-end-aware purge uses label/event end time plus embargo, not a fixed
  bar offset, when event-end metadata is supplied.
- Missing required event-end columns fail closed.
- Split consumers that fit/train models honor explicit safe train indices.
- Fixed-bar purge remains only as an identified fallback for frames with no
  event-end metadata.
- `ISSUE-R106-011` is resolved only after focused validation passes.

## Rollback Plan

Revert only the files in the allowed edit paths for this packet. Do not touch
generated caches, fixture packs, runtime/live code, or unrelated docs.
