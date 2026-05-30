# Stage R106 Full Repo Mismatch And Bug Audit Report

Work packet: `docs/work_packets/WPR106-26-full-repo-mismatch-bug-audit.md`

Date: 2026-05-29

## Summary

WPR106-26 audited the repo after the WPR106-24 and WPR106-25 autopilot
portability fixes. The audit focused on migration mismatches, stale checkout
paths, research/live boundary hazards, unsafe readiness claims, generated
artifact handoff paths, and validation health before the next autopilot run.

One additional portability gap was found and fixed: nested generated-manifest
metadata outside `required_outputs` still retained old checkout paths after
normalization. This could become a future handoff bug when downstream code
reads source evidence, feature-column metadata, or `repo_root` metadata. The
fix broadens read-time normalization only; no generated artifacts were
rewritten.

## Repo State

- Branch: `main...origin/main`.
- Existing dirty worktree was expected from WPR106-21 through WPR106-25 and
  the imported research knowledge docs.
- Open blockers after this audit:
  - no open P0;
  - one open P1: `ISSUE-R104-001`, the empirical candidate-ready evidence gate.
- Newly resolved issue:
  - `ISSUE-R106-006`, nested migrated artifact metadata can still point at old
    checkout paths.

## Static Scan Results

Stale checkout path scan:

- Production source/configs had no hard-coded
  `C:\Users\papaa\Music\tradingbotsuite` paths.
- Hits were limited to docs and intentional regression tests that simulate the
  migrated checkout.

Promotion readiness scan:

- No unsafe production `promotion_ready: true` hit was found.
- Hits were docs describing the forbidden state and tests that intentionally
  validate rejection.

Research/live boundary scan:

- No research-owned package imported known order-placement modules
  (`tradingbotsuite.adapters.execution`, `tradingbotsuite.runtime`,
  `tradingbot.live`, `tradingbot.data.hyperliquid`).
- Existing legacy research modules still import candle/model helper surfaces
  from `tradingbotsuite.adapters.binance` and `tradingbotsuite.core`; this is
  current architecture, and the import-boundary contract suite passed.

TODO/FIXME/HACK scan:

- No new blocker marker in research execution paths.
- One visible UI text says a testing-only workaround must be removed before
  real deployment. This is consistent with current non-live branch boundaries.

Silent zero-fill scan:

- Several expected `fillna(0.0)` usages remain in metrics, feature flags,
  legacy HMM/KNN research, and tests. No new P0/P1 was opened because contract
  and focused suites passed, and no scan hit showed promotion/candidate-ready
  evidence being silently completed from unknown optional context.

Broad recursive scan review:

- Recursive scans exist in tests, old research UI, telemetry, and benchmark
  helpers. They were not the active operator path causing failures. Current
  operator artifact indexing remains bounded enough for the validated R106
  workflow.

## Artifact Portability Audit

The targeted operator-run manifest audit checked these manifest classes without
descending into trial/download trees:

- historical catalog manifests;
- historical-cycle manifests;
- discovery-run manifests;
- research analysis manifests;
- analysis-delta manifests;
- frozen-entry exit-lab manifests;
- candidate-pack eligibility manifests;
- research autopilot manifests.

Post-fix result:

```json
{
  "manifests": 22,
  "raw_old_root_manifests": 16,
  "normalized_old_root_manifests": 0,
  "outside_required_outputs": [],
  "missing_required_outputs": [],
  "read_errors": []
}
```

Interpretation:

- Generated artifacts still preserve historical old-root strings on disk. That
  is expected because this packet does not rewrite generated evidence.
- Read-time normalization now clears all old-root strings in the checked
  payloads where mirrored local paths exist.
- Normalized `required_outputs` all stay under current `data/research` and
  exist locally.

## Fix Implemented

- `src/tradingbotsuite/data/historical_data_catalog.py`
  - Extended the shared operator-run path normalizer to rebase old-root
    absolute strings that point to repo-root-relative locations such as
    `data/...`, `configs/...`, `docs/...`, `src/...`, or `tests/...`.
  - Rebased `repo_root` metadata to the current checkout root.
  - Kept generated artifacts immutable and kept non-mirrored outside paths
    fail-closed.
- `tests/tradingbotsuite/test_market_data_collection.py`
  - Added coverage for rebasing nested `data/...`, `configs/...`, and
    `repo_root` old-checkout strings.
- `docs/KNOWN_ISSUES.md`
  - Added and resolved `ISSUE-R106-006`.

## Validation

Passed:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_artifacts tests\research_discovery -q
$env:PYTHONPATH='src'; python -m pytest tests\live -q
$env:PYTHONPATH='src'; python -m pytest tests\historical -q
$env:PYTHONPATH='src'; python -m pytest tests\backtesting tests\features tests\optimization tests\research_cycle -q
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py tests\tradingbotsuite\test_market_data_collection.py -q
$env:PYTHONPATH='src'; python -m pytest tests\unit tests\integration -q
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite -q
```

Observed results:

- `tests/contracts`: `427 passed`.
- `tests/research_artifacts tests/research_discovery`: `248 passed`.
- `tests/live`: `56 passed`.
- `tests/historical`: `42 passed`.
- `tests/backtesting tests/features tests/optimization tests/research_cycle`:
  `170 passed, 1 skipped`.
- `tests/tradingbotsuite/test_operator_ui.py`
  `tests/tradingbotsuite/test_market_data_collection.py`: `108 passed`.
- `tests/unit tests/integration`: `36 passed`.
- `tests/tradingbotsuite`: `348 passed, 2 warnings`.

The first combined `tests\historical tests\live` command hit a 244 second
timeout without useful failure output. The suites were then split; both passed.

JSON/config parse:

```text
68 JSON files parsed, 0 errors
```

Warnings:

- The full `tests/tradingbotsuite` run emitted two local GPU/XGBoost/CuPy
  warnings about mismatched prediction device and missing `CUDA_PATH`. These
  are diagnostic runtime warnings, not test failures.

## Final Assessment

No remaining P0/P1 mismatch was found in code or checked operator-run handoff
metadata after WPR106-26. The next autopilot run should not fail on the known
migrated-path classes:

- discovery `blocked_candidates`;
- historical-cycle `ablation_report`;
- nested source evidence, feature-column metadata, or `repo_root` stale paths.

The next failures, if any, should be treated as empirical research gate results
unless they present a new exception. `ISSUE-R104-001` remains open because
candidate-ready evidence still depends on downstream empirical gate review, not
because of a repo mismatch found in this audit.
