# Project Audit Verdict

## Overall Verdict

**FAIL**. Confidence: **0.93**.

This repository state is not safe to merge or build on as-is. The work is directionally related to the Rapid Strategy Iteration Sandbox goal, but it is not merge-coherent, the full test suite is red, core provenance semantics are wrong, and the high-throughput archive/backtest paths still rely on full-memory processing.

## Executive Summary

- Biggest risks: untracked source imported by tracked code, red full test suite, descriptor-window provenance bug, shallow safety boundary validation, unsafe `run_id` path handling, proxy strategies masquerading as real strategy intake, and non-scalable archive/backtest memory behavior.
- Directionally useful: yes, but only as a prototype. The Parquet/JSON artifact direction, strict descriptor-only intent, venue descriptors, and boundary metadata are worth salvaging.
- Merge stance: **do not merge**. Split and salvage selected pieces after fixing correctness and safety blockers.
- Fix before more feature work: make the tree commit-coherent, get full tests green, fix archive window/identity/path safety, and decide whether the sandbox uses real strategy implementations or explicitly proxy-only diagnostics.

## Scope Reviewed

- Base used: local `HEAD` `0be5e0d` on `main`, inferred because no clean base branch was provided.
- Head reviewed: dirty working tree on `main`; local `main` is behind `origin/main` by 1 commit.
- Changed tracked files: **59** tracked files, **15,449 insertions / 526 deletions**.
- Untracked files: **8,100**, including **26** sandbox source files, **1** sandbox test file, `configs/sandbox/`, and **7,418** files under `outputs/`.
- Major subsystems touched: sandbox package, CLI/operator/web routing, backtesting fills, research discovery runner/state, strategy metadata/registry, sparse event strategy, candidate-pack eligibility, docs/stage ledger/work packets, tests, CI-ish files.
- Checks run: `compileall` passed; `pip check` passed; focused contracts/live/sandbox tests passed; full pytest failed.
- Could not meaningfully trust CI coverage because the new sandbox test suite is not in the workflow.

## Critical Findings

None found. I did not find direct live order placement or candidate-pack writes from the sandbox path, but safety validation is too shallow to trust downstream artifacts.

## High Findings

### H1. Tracked Code Imports Untracked Sandbox Package

- **Severity:** High
- **Confidence:** 0.95
- **Location:** `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/main.py:41`
- **Problem:** tracked code imports an untracked sandbox package.
- **Evidence:** `main.py` imports `tradingbotsuite.research_sandbox`, but `git ls-files src/tradingbotsuite/research_sandbox tests/research_sandbox configs/sandbox` returned `0`; the sandbox package is entirely untracked.
- **Impact:** a normal commit of the tracked diff is broken and reviewers can miss most of the implementation.
- **Fix direction:** stage intended sandbox source/tests/configs or remove tracked imports. Keep generated `outputs/` ignored.
- **Verification:** fresh checkout passes `python -c "import tradingbotsuite.main"` and has no intended source under `git ls-files --others`.

### H2. Full Test Suite Is Red

- **Severity:** High
- **Confidence:** 0.95
- **Location:** `C:/Users/papaa/Music/researchenginedeluxe/tests/optimization/test_search_space_expansion.py:90`, `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/strategies/parameters.py:74`, `C:/Users/papaa/Music/researchenginedeluxe/tests/research_discovery/test_discovery_runner.py:481`, `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_discovery/runner.py:3293`
- **Problem:** full test suite is red.
- **Evidence:** `pytest -q` produced `2 failed, 1828 passed, 1 skipped`: spacing search-space now returns `(4, 8, 12, 16)` where test expects `(8, 12, 16)`, and discovery resume manifest reports `completed_trials == 1` after recovering two trial IDs.
- **Impact:** branch is not mergeable; one failure is strategy metadata drift, the other corrupts discovery progress/manifest accounting.
- **Fix direction:** reconcile intended strategy parameter expansion and fix partial-resume ledger counts so manifest/state agree.
- **Verification:** full `python -m pytest -q -p no:cacheprovider` must pass.

### H3. Descriptor Windows Are Ignored During Execution And Preflight

- **Severity:** High
- **Confidence:** 0.95
- **Location:** `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/fast_backtest.py:99`, `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/fast_backtest.py:755`, `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/preflight.py:69`
- **Problem:** execution/preflight ignore `VenueArchiveDescriptor.window`.
- **Evidence:** `_market_window()` filters only `SandboxRunSpec.data_window`; `run_fixed_hold_sweep_for_venue_frames()` passes only the first venue frame/spec into that helper. A local probe accepted a trade outside the descriptor window.
- **Impact:** artifacts can claim archive-backed coverage while scoring rows outside declared archive coverage.
- **Fix direction:** filter on the intersection of spec window and descriptor window per descriptor; share this helper across audit, preflight, and execution.
- **Verification:** regression where the only signal outside descriptor window yields zero runnable trades and no screened result.

### H4. Sandbox Run ID Can Escape Output Root

- **Severity:** High
- **Confidence:** 0.95
- **Location:** `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/spec.py:345`, `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/intake.py:542`, `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/store.py:87`
- **Problem:** `SandboxRunSpec.run_id` is used as a filesystem path component without safe-component validation.
- **Evidence:** only non-empty text is checked; `ResultStore.write_run()` writes to `self.output_root / spec.run_id`.
- **Impact:** malicious or bad specs can write outside the intended output root.
- **Fix direction:** reject `..`, separators, drive paths, and absolute paths; resolve and require containment under `output_root`.
- **Verification:** tests for `../escape`, `..\escape`, and absolute Windows paths create no files and fail closed.

### H5. Sandbox Boundary Validation Is Shallow

- **Severity:** High
- **Confidence:** 0.90
- **Location:** `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/boundary.py:29`, `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/intake.py:358`, `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/store.py:137`
- **Problem:** sandbox boundary validation is shallow.
- **Evidence:** `sandbox_boundary_errors()` checks only top-level keys; free-form `params_json` can contain `live_signal`, `order_placement_instruction`, or sizing-like fields and still be serialized into manifests.
- **Impact:** research-only artifacts can carry forbidden live/paper/order/sizing instructions.
- **Fix direction:** recursively reject forbidden keys in all free-form payloads or sanitize before persistence.
- **Verification:** tests with forbidden nested keys in strategy params and source metadata must fail.

### H6. Catalog Exit Profile Is Parsed But Ignored

- **Severity:** High
- **Confidence:** 0.95
- **Location:** `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/intake.py:354`, `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/fast_backtest.py:691`
- **Problem:** catalog-level `exit_profile` is parsed but ignored during execution.
- **Evidence:** `StrategyCatalogRow.exit_profile` is loaded, but execution only iterates `run_spec.exit_variants`; a probe with `exit_profile="target_only"` produced a fixed-hold result.
- **Impact:** spreadsheet/catalog semantics do not match tested exits.
- **Fix direction:** either remove/label `exit_profile` as metadata-only, or convert it into executable `ExitVariant` with conflict validation.
- **Verification:** catalog row with target-only exits must produce target-only behavior or fail closed.

### H7. Real Strategy IDs Are Mapped To Generic Proxies

- **Severity:** High
- **Confidence:** 0.90
- **Location:** `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/strategy_blueprints.py:29`, `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/strategy_blueprints.py:52`
- **Problem:** real strategy IDs are mapped to three generic proxy strategies.
- **Evidence:** `baseline_no_trade`, `funding_basis_v1`, and `hmm_knn_local_analog_filter_v2` map to proxy blueprints such as `close_momentum_proxy`.
- **Impact:** rankings can appear tied to existing strategies while testing synthetic proxy logic.
- **Fix direction:** either make this explicitly proxy-only and block real strategy scoring, or route through the existing strategy registry.
- **Verification:** `baseline_no_trade` must not generate active proxy trades unless clearly marked and excluded from real-strategy rankings.

### H8. Existing Backtest Entry Price Semantics Changed Silently

- **Severity:** High
- **Confidence:** 0.90
- **Location:** `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/backtesting/engine.py:313`, `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/backtesting/execution_sim.py:448`, `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/backtesting/vector_engine.py:318`, `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/backtesting/cuda_batched_engine.py:140`
- **Problem:** `signal_bar_close_plus_latency` semantics silently changed to primary/open fill.
- **Evidence:** previous signal close fallback is removed; fill profile now returns `primary_bar_latency_fill`.
- **Impact:** historical backtest comparability breaks under the old public source name.
- **Fix direction:** restore old semantics or introduce a new explicit source name and migration/error path.
- **Verification:** compatibility tests for old source and new source across reference/vector/CUDA paths.

### H9. High-Throughput Sandbox Paths Are Still Full-Memory

- **Severity:** High
- **Confidence:** 0.92
- **Location:** `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/market_data.py:831`, `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/runner.py:110`, `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/fast_backtest.py:562`, `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/strategy_blueprints.py:348`
- **Problem:** the supposed high-throughput sandbox is still full-memory in key paths.
- **Evidence:** all descriptor frames are loaded into a dict; ZIP/TAR/JSONL members are fully read; barrier exits allocate dense entry-by-hold matrices; proxy signals add one column per strategy.
- **Impact:** 2024+ multi-venue archives can exhaust memory before meaningful vectorized work begins.
- **Fix direction:** stream/group by source, push down window filters, batch barrier exits, and compute masks lazily by unique signal definition.
- **Verification:** stress tests with many descriptors, dense 1m signals, and long holds asserting bounded peak memory.

### H10. CI Does Not Enforce The New Sandbox Tests

- **Severity:** High
- **Confidence:** 0.90
- **Location:** `C:/Users/papaa/Music/researchenginedeluxe/.github/workflows/research-validation.yml:39`
- **Problem:** CI omits the new sandbox suite and new CLI boundary tests.
- **Evidence:** workflow runs `tests/contracts` and four live/artifact files, not `tests/research_sandbox` or `tests/live/test_cli_boundary.py`.
- **Impact:** major sandbox regressions can land green.
- **Fix direction:** add focused sandbox and CLI-boundary jobs.
- **Verification:** CI runs `python -m pytest tests/research_sandbox tests/live/test_cli_boundary.py -q`.

## Medium Findings

### M1. Deterministic IDs Are Not Deterministic For The Right Boundary

- **Severity:** Medium
- **Confidence:** 0.95
- **Location:** `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/identity.py:31`, `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/fast_backtest.py:481`, `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/spec.py:180`
- **Problem:** deterministic trial IDs omit status-affecting fields and include local paths.
- **Evidence:** identity hashes data window/profile/cost but not `min_trades`; `venue.to_payload()` includes `data_path`/`manifest_path`. A probe produced the same trial ID for screened vs rejected `min_trades` settings.
- **Impact:** artifact dedupe and evidence requests can conflate different decisions, while identical data under a new root gets different IDs.
- **Fix direction:** split decision identity from provenance metadata and include all result-affecting spec fields.
- **Verification:** tests for min-trade identity divergence and path-independent archive identity.

### M2. `.xls` Catalog Support Is Advertised But Not Dependency-Complete

- **Severity:** Medium
- **Confidence:** 0.90
- **Location:** `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/intake.py:21`, `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/intake.py:172`, `C:/Users/papaa/Music/researchenginedeluxe/pyproject.toml:11`
- **Problem:** `.xls` catalog support is advertised but dependency support is missing.
- **Evidence:** suffix list includes `.xls`; fallback only handles `.xlsx`; no `xlrd` dependency.
- **Impact:** clean installs reject advertised spreadsheet inputs.
- **Fix direction:** add/test `xlrd` or remove `.xls` support.
- **Verification:** clean-env `.xls` intake test or explicit unsupported-format test.

### M3. Evidence Descriptors Are Not Integrated Into Strict Validation

- **Severity:** Medium
- **Confidence:** 0.88
- **Location:** `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/validation_bundle.py:23`, `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/validation_bundle.py:186`
- **Problem:** evidence descriptors are not integrated into the strict validation cycle.
- **Evidence:** bundle emits `STRICT_VALIDATION_ENTRYPOINT = "existing_historical_research_cycle"` and `strict_validation_executed=False`; no consumer was found in `research_cycle`.
- **Impact:** handoff is manual/stringly typed, not a strict import/preflight contract.
- **Fix direction:** define a schema consumed by strict validation preflight, execution disabled by default.
- **Verification:** export bundle, import into strict validation preflight, assert deterministic accept/block.

### M4. Artifact Consumers Trust Absolute Paths In Manifests

- **Severity:** Medium
- **Confidence:** 0.85
- **Location:** `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/integrity.py:91`, `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/leaderboard.py:85`
- **Problem:** artifact consumers trust manifest-declared absolute child paths.
- **Evidence:** resolved artifact paths are not required to stay under the run directory before hashing/parsing.
- **Impact:** tampered manifests can cause reads/hashes of arbitrary local files if metadata is supplied.
- **Fix direction:** require child artifact containment under run/suite root or configured research root.
- **Verification:** manifest pointing outside run dir must fail integrity/export.

### M5. `max_files` And `max_runs` Do Not Bound Discovery Cost

- **Severity:** Medium
- **Confidence:** 0.90
- **Location:** `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/archive_manifest.py:477`, `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/strategy_catalog_materializer.py:53`, `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/leaderboard.py:658`
- **Problem:** `max_files`/`max_runs` do not bound discovery cost.
- **Evidence:** code sorts full `rglob()` results and leaderboard concatenates all ranking frames before truncation/aggregation.
- **Impact:** large archive roots spend time and memory discovering files that should be skipped.
- **Fix direction:** streaming traversal with early stop and incremental aggregation.
- **Verification:** test thousands of files with `max_files=10`, asserting bounded reads.

### M6. Core Sandbox Code Is Organized As God Modules

- **Severity:** Medium
- **Confidence:** 0.95
- **Location:** `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/catalog.py:19`, `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/iteration_index.py:1805`, `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/iteration.py:1599`
- **Problem:** core sandbox code is organized as god modules.
- **Evidence:** `catalog.py` is 257 KB, `iteration_index.py` 114 KB, `iteration.py` 90 KB, mixing discovery, schemas, queues, reports, persistence, and orchestration.
- **Impact:** future changes will be brittle and hard to review.
- **Fix direction:** split by artifact discovery, schema writers, validation queues, replay planning, and orchestration.
- **Verification:** subsystem tests run independently through thin orchestration.

### M7. Sandbox Package Root Exposes Too Much

- **Severity:** Medium
- **Confidence:** 0.88
- **Location:** `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/__init__.py:8`, `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/main.py:41`
- **Problem:** package root eagerly re-exports almost the entire sandbox.
- **Evidence:** `main.py` imports from package root, pulling a broad graph at CLI startup.
- **Impact:** unrelated CLI commands can fail on sandbox import issues; internals become accidental API.
- **Fix direction:** minimal root exports and lazy subcommand imports.
- **Verification:** `tradingbotsuite --help` works without importing heavy sandbox modules.

### M8. CLI, Operator, And Web Routing Are Diverging

- **Severity:** Medium
- **Confidence:** 0.88
- **Location:** `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/main.py:981`, `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/operator_console.py:3990`, `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/web/operator.py:648`
- **Problem:** CLI, operator service, and web routes grow separate sandbox routing paths.
- **Evidence:** separate inline dispatch chains and request validators.
- **Impact:** behavior will drift across CLI/service/UI.
- **Fix direction:** shared typed research command/job registry.
- **Verification:** registry coverage test for every command handler and boundary classification.

### M9. Compressed Archive And Workbook Parsing Is Unbounded

- **Severity:** Medium
- **Confidence:** 0.95
- **Location:** `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/market_data.py:383`, `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/market_data.py:396`, `C:/Users/papaa/Music/researchenginedeluxe/src/tradingbotsuite/research_sandbox/intake.py:170`
- **Problem:** compressed archive/workbook parsing is unbounded.
- **Evidence:** ZIP/TAR members use `handle.read()`, GZIP uses full decompression, workbook XML has no size/member/row limits.
- **Impact:** malformed archive/workbook can exhaust memory/CPU.
- **Fix direction:** hard limits on member count, compressed/uncompressed bytes, XML size, and row count.
- **Verification:** zip-bomb-style fixtures fail before allocation.

## Low Findings

### L1. Generated Outputs Are Unignored

- **Severity:** Low
- **Confidence:** 0.95
- **Location:** `C:/Users/papaa/Music/researchenginedeluxe/.gitignore:28`; generated directory has no meaningful source line.
- **Problem:** `outputs/` is unignored and contains vendored/native package trees.
- **Evidence:** 7,418 untracked files under `outputs/`, including `node_modules`, `playwright`, `sharp`, and native binaries.
- **Impact:** accidental vendor/binary commit risk and noisy review state.
- **Fix direction:** remove generated outputs and ignore `/outputs/`.
- **Verification:** `git ls-files --others --exclude-standard outputs` returns nothing.

### L2. `.pytest_cache` Is Tracked

- **Severity:** Low
- **Confidence:** 0.95
- **Location:** `C:/Users/papaa/Music/researchenginedeluxe/.gitignore:2`, `C:/Users/papaa/Music/researchenginedeluxe/.pytest_cache/v/cache/nodeids`
- **Problem:** tracked pytest cache is modified despite ignore rules.
- **Evidence:** `git ls-files .pytest_cache` lists cache files.
- **Impact:** routine tests dirty the repo.
- **Fix direction:** remove `.pytest_cache` from version control.
- **Verification:** `git ls-files .pytest_cache` returns nothing.

### L3. Sandbox Tests Are Concentrated In One Huge File

- **Severity:** Low
- **Confidence:** 0.94
- **Location:** `C:/Users/papaa/Music/researchenginedeluxe/tests/research_sandbox/test_sandbox_foundation.py:486`
- **Problem:** sandbox tests are concentrated in one 498 KB / 11k-line file.
- **Evidence:** 244 tests in a single file.
- **Impact:** merge conflicts, slow review, and weak subsystem ownership.
- **Fix direction:** split by subsystem with shared fixtures in `conftest.py`.
- **Verification:** each subsystem test file runs independently.

## Suspicious / Needs Human Decision

- Current branch is `main`, but `AGENTS.md` says this work belongs to `research/v3-experimental-engine`; decide whether this was done on the wrong branch.
- `src/tradingbotsuite/research/monte_carlo_exit_sizing.py` is untracked and discusses Martingale/sizing research. It has research-only flags, but it conflicts strategically with the "no sizing" sandbox direction unless kept out of this PR.
- Hundreds of generated work packets/stage reports look like ledger spam. Decide what documentation is authoritative versus generated exhaust.
- Decide whether proxy strategies are acceptable. If yes, sandbox output must be clearly labeled proxy-only and excluded from real-strategy claims.
- Candidate-pack fields appear widely in sandbox catalog code, mostly false. Decide whether this is useful defensive metadata or unnecessary surface area.

## Dependency / Package Audit

- `pyproject.toml`/lockfiles were not meaningfully changed; `python -m pip check` passed.
- `.xls` support is not dependency-complete because `xlrd` is undeclared.
- Biggest package risk is not manifest dependencies; it is unignored generated `outputs/node_modules` and native binaries.
- No new package lock coverage was added for sandbox-specific assumptions.

## Test / Verification Audit

- Passes: `python -m compileall -q src/tradingbotsuite`; `python -m pip check`; `tests/contracts` passed; `tests/live/test_cli_boundary.py` passed; `tests/research_sandbox/test_sandbox_foundation.py` passed.
- Fails: full `pytest -q -p no:cacheprovider` failed with 2 failures: strategy spacing search-space and discovery resume manifest counts.
- Missing: descriptor-window regression, strategy `exit_profile` execution, recursive boundary rejection, `run_id` path escape tests, strict-validation descriptor import, parity tests against existing backtest engines, memory/performance stress tests.
- Weak: sandbox tests are large and local but not in CI; many critical risks were found by probes, not tests.
- Minimum before trusting: full suite green, sandbox tests in CI, safety/provenance regressions added, and at least one streaming/perf stress target.

## Architecture Audit

- Preserve: explicit research-only boundary metadata, Parquet/JSON artifact intent, venue/archive descriptors, source integrity concept, evidence-request-only handoff intent.
- Reverse: proxy strategies presented as real strategy ingestion, parallel backtest semantics without parity, eager package-root exports, path-unsafe run IDs.
- Overcomplicated: `catalog.py`, `iteration.py`, `iteration_index.py`, and duplicated serializer helpers.
- Redundant systems: sandbox has a separate engine/metrics path beside existing `tradingbotsuite.backtesting`.
- Direction got worse where CLI/operator/web routing diverged and where historical fill semantics changed under an existing public name.

## Salvage Plan

### 1. Must Fix Before Merge

- Make the worktree commit-coherent.
- Fix the full test suite failures.
- Apply descriptor-window filtering everywhere.
- Make `run_id` path-safe and containment-checked.
- Make boundary validation recursive or sanitize free-form payloads.
- Add sandbox and CLI-boundary tests to CI.
- Resolve `signal_bar_close_plus_latency` semantic drift with restoration or migration.

### 2. Should Fix Soon

- Correct trial identity and path-independent descriptor identity.
- Add strict-validation descriptor import/preflight integration.
- Decide and test `.xls` support.
- Add artifact path containment validation.
- Add parity tests against existing backtest engines.

### 3. Can Defer

- Split god modules.
- Consolidate serializer helpers.
- Introduce a shared command/job registry.
- Split the large sandbox test file.

### 4. Should Delete/Revert

- Generated `outputs/`.
- Tracked `.pytest_cache`.
- Accidental docs/packet spam not needed for review.
- Untracked sizing/Martingale work unless product-approved for this branch.

### 5. Needs Human Product/Architecture Decision

- Real strategy execution versus proxy-only sandbox.
- Whether sizing/Martingale research belongs in this branch.
- Whether the sandbox uses the existing backtest engine or maintains a separately validated engine.

## Final Recommendation

**Do not merge.** Split into smaller PRs and salvage selected pieces after fixing the safety/provenance/test blockers. The current state is useful as a prototype, not as a foundation for further agent work.

Confidence: **0.94**.

