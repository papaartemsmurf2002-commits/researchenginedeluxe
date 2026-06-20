# ResearchEngineDeluxe Completion Roadmap

Date: 2026-06-20
Last expanded: 2026-06-20 by WPR106-361

## Status And Boundary

This is the authoritative roadmap for finishing ResearchEngineDeluxe as a
research-only product. It is not a live, paper, sizing, order-placement,
runtime-mode, candidate-pack, or promotion roadmap.

The finished product should let an agent ingest strategy catalogs and 2024+
multi-venue archive roots, run bounded rapid sandbox sweeps, falsify and rank
hypotheses, explain blockers and next actions, and emit descriptor-only
strict-validation handoffs. Those handoffs are requests for later validation,
not evidence of candidate readiness.

This document is intentionally detailed. Future agents should treat it as the
first planning source after `AGENTS.md`, `docs/ACTIVE_INDEX.md`, the stage
ledger, known issues, and the dependency fuse.

## How To Use This Roadmap

Use this roadmap to choose and execute small work packets. Do not treat it as a
license to batch unrelated changes.

1. Read the current stage and issue state.
2. Pick exactly one packet-sized objective from the backlog or phase guidance.
3. Write or update a work packet before editing.
4. Keep changes inside the packet's allowed paths.
5. Add focused tests for every behavior change.
6. Preserve research-only boundaries and fail closed when evidence is missing.
7. Update the stage report, ledger, active index, and known issues when needed.
8. Stop and record an issue instead of weakening a contract to make progress.

## Product Definition

The finished research-only product is a rapid strategy research engine with the
following operator and agent experience:

- Ingest strategy ideas from repo configs, spreadsheet/workbook catalogs,
  structured JSON/CSV/Parquet catalogs, and prior sandbox artifact queues.
- Ingest 2024+ local archive roots for Binance, OKX, Bybit, Hyperliquid, and
  local normalized exports without downloading data by default.
- Build or repair local sandbox archive manifests from explicit local roots.
- Preflight data, strategy, exit, filter, and boundary compatibility before
  spending compute.
- Run bounded vectorized or cached sweeps over strategy/exit/filter/venue
  combinations.
- Write compact JSON/Parquet artifacts with deterministic identities,
  provenance, blocker reasons, integrity metadata, and boundary flags.
- Rank, falsify, and group hypotheses without making performance or promotion
  claims.
- Emit descriptor-only requests for strict validation, venue expansion, and
  replay work.
- Show the next action for an agent without requiring manual sidecar hunting.
- Prove throughput and memory behavior on realistic local 2024+ archives.

The product is complete only when an agent can run a short command sequence
from current local materials and get one of these truthful outcomes:

- a bounded research sweep with ranked or rejected hypotheses;
- a clear preflight blocker and repair queue;
- a local archive materialization dry run;
- a strict-validation descriptor preflight queue;
- a performance report showing bottlenecks and safe next optimizations.

The product is not complete if it only works on synthetic fixtures, requires
hand-editing generated files between steps, hides blocker reasons, or depends
on untracked source files.

## Non-Goals

Do not add these under this roadmap:

- live or paper trading;
- venue execution proof;
- order placement;
- position sizing or Martingale behavior;
- live runtime mode changes;
- live configuration writes;
- candidate-pack creation from sandbox evidence;
- `promotion_ready: true`;
- provider downloads inside local materializer packets unless a later explicit
  intake packet scopes downloads separately;
- pre-2024 sandbox evidence;
- weak synthetic evidence presented as real archive-backed validation.

## Current Repo Reality

The current checkout must be stabilized before feature work resumes.

- Local branch: `main`, behind `origin/main` by one commit, used as the local
  mirror of the research branch.
- Dirty tree: 59 tracked files modified and 8,101 untracked files observed in
  the current working tree.
- Commit-coherence risk: tracked CLI code imports the untracked
  `src/tradingbotsuite/research_sandbox/` package, while `git ls-files` shows
  the sandbox source, tests, and `configs/sandbox/` are not tracked.
- Generated-output risk: `outputs/` is untracked and contains generated
  dependency/output material; `.pytest_cache` is tracked and currently dirty.
- Current targeted red checks reproduced the audit failures:
  `tests/optimization/test_search_space_expansion.py::test_holding_window_search_space_includes_metadata_and_window_defaults`
  returns `spacing_bars == (4, 8, 12, 16)` where the test expects
  `(8, 12, 16)`;
  `tests/research_discovery/test_discovery_runner.py::test_discovery_runner_large_zero_stop_resume_recovers_lag_without_full_hydration`
  reports manifest `completed_trials == 1` where recovered run state has two
  completed trial IDs.
- Audit posture: `docs/SANDBOX_FIRST_LOOK_RECOMMENDATIONS.md` and
  `RAPID_STRATEGY_SANDBOX_AUDIT.md` supersede the softer WPR106-358 materializer
  handoff. The next work starts audit-first, then feature completion.

Do not build the venue materializer, dashboard, strict-validation bridge, or
performance layer until Phase 0 is closed.

## Roadmap Phases

| Phase | Packet theme | Objective | Dependencies | Allowed path pattern | Acceptance criteria | Validation | Stop conditions | Artifact outputs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | Repo-state and merge coherence | Classify keep, split, drop, ignore, or park for every dirty and untracked surface. Make a normal checkout commit-coherent. | Current dirty tree, WPR106-359, audit report. | Docs, `.gitignore`, source/tests/configs only as classified by packet. | Fresh checkout can import CLI without missing untracked sandbox source; generated outputs are ignored or quarantined; unrelated semantic diffs are split or explicitly parked. | `git status --short`, `git ls-files`, targeted import smoke, full suite once red tests are fixed. | More sandbox feature work requested before tracked/untracked coupling is resolved. | Repo-state audit report, classification table, cleaned ignore/quarantine plan. |
| 0A | Red-test repair | Fix current full-suite blockers before trusting sandbox evidence. | Phase 0 classification. | `src/tradingbotsuite/strategies/**`, `src/tradingbotsuite/research_discovery/**`, focused tests. | Strategy spacing metadata is intentional and test-aligned; discovery resume manifest counts match recovered state. | The two targeted tests, then `python -m pytest -q -p no:cacheprovider`. | Any fix weakens candidate gates or resume durability. | Repair packet, focused regression notes. |
| 0B | CI and validation coverage | Make sandbox and live CLI boundary tests part of required validation. | Commit-coherent sandbox source/tests. | `.github/workflows/**`, test docs. | CI runs `tests/research_sandbox` and `tests/live/test_cli_boundary.py` or a consciously bounded split equivalent. | Workflow syntax review and local focused test runs. | CI cannot run due to missing tracked dependencies. | Updated workflow and validation report. |
| 1 | Sandbox safety and provenance repair | Make existing sandbox artifacts safe enough to use as research-navigation evidence. | Phase 0 closed. | `src/tradingbotsuite/research_sandbox/**`, focused sandbox tests, live boundary tests. | Path-safe `run_id`; descriptor-window intersection used in audit, preflight, and execution; recursive boundary rejection; artifact child paths contained; identity includes decision-affecting fields; proxy-only behavior explicit or real strategy routing chosen. | Focused regressions plus sandbox suite and live CLI boundary tests. | Any artifact can carry live/paper/order/sizing fields or score rows outside descriptor windows. | Safety repair report, updated sandbox contract notes. |
| 1A | Fill-semantics compatibility | Resolve silent `signal_bar_close_plus_latency` behavior drift. | Phase 0 and relevant backtest ownership review. | `src/tradingbotsuite/backtesting/**`, focused backtest tests. | Old public source semantics are restored or a new explicit source name with migration/error behavior is introduced. | Reference, vector, CUDA/fallback parity tests where applicable. | Comparability is changed without a named migration path. | Backtest compatibility report. |
| 2 | Venue-expansion local materializer | Consume venue-expansion request bundles and scan only explicit local roots. | Phase 1 safety closed. | Sandbox materializer module, CLI wiring, tests, docs. | Writes descriptor candidates and dry-run manifest patch artifacts; no downloads; no source mutation; no existing manifest mutation by default. | Unit and CLI tests with OKX, Bybit, Hyperliquid, Binance/local samples. | Any provider download, archive source mutation, or validation execution. | `sandbox_venue_expansion_descriptor_candidates.*`, `sandbox_venue_expansion_manifest_patch_dry_run.*`. |
| 2A | End-to-end rapid loop smoke | Prove the smallest realistic closed loop. | Phase 2 materializer. | Sandbox fixtures/tests/docs. | Request bundle -> descriptor candidate -> manifest candidate -> coverage matrix -> preflight -> one bounded rerun -> analysis/falsification -> descriptor-only strict-validation request. | Reproducible smoke with 2024+ local archive samples and real repo strategy/catalog inputs. | Hand editing is needed between steps or any pre-2024 row leaks in. | End-to-end smoke manifest, replay command, blocker summary. |
| 2B | Spreadsheet/catalog hardening | Make messy strategy catalogs agent-usable. | Phase 1 safety. | Sandbox intake/materializer/tests. | Sheet provenance, header aliases, skipped-row repair queues, duplicate detection, parameter normalization, and clear errors. | Messy workbook fixtures and direct CSV/Parquet/JSON tests. | Real strategy IDs are silently proxied as real strategy evidence. | Strategy catalog build report and repair queue. |
| 2C | First-read dashboard and next action | Reduce navigation cost without hiding source evidence. | Phase 2A evidence shape. | Sandbox catalog/index/CLI/docs. | One top-level dashboard or `show-rapid-strategy-sandbox-next-action` command summarizes runs, blockers, missing venues, best hypotheses, strict-validation queues, and next actions. | Snapshot tests over existing artifact catalogs. | Dashboard recomputes or mutates evidence instead of summarizing existing artifacts. | Dashboard JSON/Parquet and next-action report. |
| 3 | Strict-validation descriptor bridge | Convert sandbox handoffs into schema-backed strict-validation preflight requests. | Phase 1 safety and Phase 2A loop. | Sandbox validation bundle, strict-validation preflight code, tests, contracts. | Import/preflight accepts or blocks descriptors deterministically; source context, archive identity, trial IDs, exit/filter assumptions, and validation requirements are preserved; execution disabled by default. | Export bundle -> import preflight tests, no candidate-pack write tests. | Candidate packs, promotion flags, live/paper artifacts, or strict-cycle execution are produced by the bridge packet. | Strict-validation descriptor import report and blocked/accepted preflight rows. |
| 4 | Performance proof and scalability | Prove rapid iteration speed with bounded memory before broad expansion. | Phase 2A closed-loop smoke. | Sandbox market-data, backtest, archive scanning, benchmark docs/tests. | Streaming or bounded archive scans; window pushdown; bounded compressed parsers; batched/vector paths; cache hit rates; vector/fallback counts; memory and throughput telemetry. | Benchmarks over realistic 2024+ multi-venue workloads, stress tests for large roots and compressed containers. | Full-memory behavior remains in high-throughput path without measured bounds. | Throughput benchmark report, cache/memory telemetry, bottleneck ranking. |
| 5 | Reviewable delivery and maintenance | Split work into PR-sized packets with durable evidence and ownership. | Phases 0 through 4. | Docs, stage reports, work packets, validated source/test slices. | Each packet has allowed paths, validation, stage report, ledger update, and no generated-output noise. | `git diff --check`, focused tests, contracts, full suite at release checkpoints. | Packet grows across unrelated subsystems or weakens research/live boundaries. | Packet registry, stage reports, branch publication checklist. |

## Target Architecture

The intended research dataflow is:

```text
strategy sources
  -> strategy catalog materializer
  -> normalized sandbox strategy catalog
local 2024+ archive roots
  -> archive scanner/materializer
  -> venue archive manifest candidates
strategy catalog + archive manifest
  -> compatibility preflight
  -> bounded sandbox sweep
  -> run manifest, rankings, rejections, evidence requests
  -> run analysis and hypothesis falsification
  -> artifact catalog and dashboard
  -> strict-validation descriptor preflight
```

The strict historical research cycle remains the validator. The sandbox is a
triage and iteration layer. It can request strict validation; it cannot grant
candidate readiness.

## Source Ownership And Likely Touchpoints

Use these ownership boundaries when creating future work packets.

| Subsystem | Purpose | Likely paths | Required tests |
| --- | --- | --- | --- |
| Sandbox specs and boundary | Non-promotable run/suite/request models, `run_id`, boundary flags, validation. | `src/tradingbotsuite/research_sandbox/spec.py`, `boundary.py`, `identity.py` | Sandbox tests, live CLI boundary, import-boundary. |
| Sandbox storage and integrity | Result writes, manifest child paths, hash/size verification. | `store.py`, `integrity.py`, `catalog.py`, `leaderboard.py` | Tamper/containment tests, artifact consumer tests. |
| Market/archive loading | Local root scans, CSV/JSON/Parquet/compressed parsing, 2024+ filtering. | `market_data.py`, `archive_manifest.py`, `archive_audit.py`, `archive_coverage.py` | Loader fixtures, malformed archive tests, coverage/preflight tests. |
| Strategy catalog intake | Workbook/catalog parsing, aliases, repair queues, proxy/real-strategy policy. | `intake.py`, `strategy_catalog_materializer.py`, `strategy_blueprints.py` | Messy workbook tests, duplicate/repair tests. |
| Sweep execution | Exit/filter grid, descriptor windows, ranking inputs, market-frame reuse. | `fast_backtest.py`, `runner.py`, `suite.py`, `iteration.py` | Descriptor-window, exit/filter, parity, cache, suite tests. |
| Agent navigation | Iteration index, action queues, dashboard, next-action command. | `iteration_index.py`, `catalog.py`, `analytics.py`, `falsification.py` | Snapshot tests over known artifacts. |
| Strict-validation handoff | Descriptor-only bundle import/preflight. | `validation_bundle.py`, future strict-validation preflight module | Bundle import tests, no candidate-pack tests. |
| Shared backtesting | Fill semantics, reference/vector/CUDA compatibility. | `src/tradingbotsuite/backtesting/**` | Backtesting contracts, vector/CUDA parity where applicable. |
| Discovery and optimizer | Red-test repair, resume manifest correctness, strategy metadata. | `research_discovery/**`, `strategies/parameters.py`, `optimization/**` | Targeted failing tests, research discovery, optimization tests. |
| CLI and UI routing | Research command registration and live-mode rejection. | `main.py`, `research/command_registry.py`, `operator_console.py`, `web/operator.py` | Live CLI boundary, operator tests if touched. |

## Phase 0 Detailed Guidance

Phase 0 is a gate, not a suggestion. It exists because the current repo state is
not safe for autonomous feature continuation.

### Phase 0A: Repo-State Classification

Create a classification artifact that lists every changed or untracked surface:

| Class | Meaning | Action |
| --- | --- | --- |
| keep | Required for current sandbox behavior and should be committed. | Keep in scoped PR after validation. |
| split | Useful but belongs to a separate packet. | Move to separate packet/PR plan. |
| drop | Accidental or obsolete. | Remove only when explicitly scoped and safe. |
| ignore | Generated or local-only output. | Add ignore/quarantine rules. |
| park | Needs human/product decision. | Record issue or decision note. |

Minimum classification commands:

```powershell
git status --short --branch
git diff --stat
git ls-files --others --exclude-standard
git ls-files src/tradingbotsuite/research_sandbox tests/research_sandbox configs/sandbox
git ls-files .pytest_cache outputs
```

Acceptance requires a fresh-checkout story: an implementation agent must know
which files need to be tracked for imports and tests, and which generated
outputs must not enter review.

### Phase 0B: Commit-Coherence Repair

Fix one of these states:

- track all intended sandbox source, tests, and configs referenced by tracked
  code; or
- remove/defer tracked imports and command registrations that depend on
  untracked sandbox code.

Required smoke:

```powershell
$env:PYTHONPATH='src'; python -c "import tradingbotsuite.main"
$env:PYTHONPATH='src'; python -m tradingbotsuite.main --help
```

### Phase 0C: Generated Output Hygiene

Generated output must not be silently available for commit. Handle:

- `/outputs/` and generated workbook previews;
- Python bytecode under source/test trees;
- `.pytest_cache`;
- large generated research artifacts outside tracked evidence scope;
- local dependency trees or native binaries.

Do not delete unrelated generated files unless the packet explicitly scopes
cleanup. Prefer ignore/quarantine decisions backed by `git ls-files` checks.

### Phase 0D: Red Test Repair

The two known targeted failures must be resolved before the sandbox can be
trusted as a base:

- Strategy metadata: decide whether `spacing_bars=4` is intended for
  `trend_following_v1` 4h search. If intended, update test expectations and
  docs explaining why the smaller spacing is valid. If not intended, remove it
  from the returned 4h search space without weakening other strategy domains.
- Discovery resume: manifest `counts.completed_trials` must match recovered
  completed trial IDs for large zero-stop resume without requiring full trial
  hydration. Preserve large-run performance behavior and durable trial record
  recovery.

Run the full suite only after these are fixed:

```powershell
$env:PYTHONPATH='src'; python -m pytest -q -p no:cacheprovider
```

### Phase 0E: CI Coverage

The baseline workflow should include sandbox and live CLI boundary tests after
the sandbox is commit-coherent. A minimal acceptable workflow addition is:

```powershell
python -m pytest tests/research_sandbox tests/live/test_cli_boundary.py -q
```

If that is too slow, split it into focused jobs and document why the split still
covers the sandbox contract.

## Phase 1 Safety And Provenance Repair Details

Phase 1 makes existing sandbox evidence safe enough to consume. It should be
split into narrow packets.

### Path-Safe Run IDs

Requirements:

- `SandboxRunSpec.run_id` must be a safe single path component.
- Reject `..`, `/`, `\`, drive roots, UNC paths, absolute paths, empty strings,
  trailing dots/spaces on Windows, and control characters.
- `ResultStore.write_run()` must resolve the final path and require containment
  under the configured output root.
- Tests must prove rejected IDs create no directories or files.

### Descriptor-Window Enforcement

Requirements:

- Preflight, audit, coverage, and execution must all use the intersection of
  the run data window and each descriptor window.
- Descriptor-routed sweeps must not use the first descriptor's filtered frame
  for other descriptors unless a shared-source cache key proves identical
  effective windows and source identity.
- A regression where signals exist only outside the descriptor window must
  produce zero runnable trades or blocked rows, not screened-positive results.

### Recursive Boundary Validation

Requirements:

- Reject forbidden keys and true values recursively in nested payloads,
  including `params`, `params_json`, source metadata, notes-derived structured
  payloads, and manifest extras.
- Forbidden concepts include live signal, paper signal, sizing instruction,
  order placement, runtime mode change, live config write, promotion readiness,
  and candidate-pack authorization.
- Tests must cover nested dicts, lists, stringly typed booleans where parsed,
  and artifact consumers.

### Artifact Path Containment

Requirements:

- Manifest-declared child artifact paths must resolve under the run directory,
  suite directory, or an explicitly allowed research output root.
- Integrity verification must fail closed before reading or hashing outside
  paths.
- Leaderboard/catalog/analysis consumers must not trust absolute paths from
  tampered manifests.

### Identity Correctness

Requirements:

- Split decision identity from local provenance.
- Include all decision-affecting fields such as `min_trades`, data window,
  exit/filter payloads, cost profile, validation profile, strategy params, and
  descriptor logical identity.
- Do not include local machine paths in decision identity unless the path is
  the only source identifier and is explicitly labeled local-provenance-only.
- Tests must prove `min_trades` changes trial IDs and identical source hashes
  under different roots keep stable logical archive identity.

### Proxy Strategy Policy

Choose exactly one policy:

- Proxy-only diagnostics: all built-in blueprint mappings are explicitly
  labeled proxy-only, excluded from real-strategy claims, and never represented
  as the named strategy's true implementation.
- Registry-backed real strategies: sandbox calls existing strategy registry
  code under completed-bar and 2024+ constraints, with parity tests against the
  strict research cycle where feasible.

Do not allow `baseline_no_trade` or named real strategies to generate active
proxy trades without an explicit proxy-only label and blocker for real-strategy
interpretation.

### Fill-Semantics Compatibility

Resolve `signal_bar_close_plus_latency` before broad benchmark comparisons:

- restore the old source behavior; or
- introduce a new source name for primary/open latency behavior and migrate
  configs/tests explicitly.

Reference, vector, and CUDA/fallback paths must agree on the chosen semantics
or fail closed with a clear unsupported-backend reason.

## Phase 2 Closed Rapid-Research Loop Details

Phase 2 turns the current artifact system into a useful loop.

### Venue-Expansion Local Materializer

Future command:

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.main materialize-rapid-strategy-sandbox-venue-expansion-requests `
  --request-bundle <bundle.json> `
  --archive-root <local-root> `
  --archive-root <local-root-2> `
  --output-dir <research-output-subdir>
```

Required behavior:

- Read only descriptor-only venue-expansion request bundles.
- Scan only explicitly provided local roots.
- Match by venue, symbol, data family, interval, requested 2024+ window,
  file/source identity, and normalized market columns.
- Write descriptor candidates and dry-run manifest patch rows.
- Never download provider data.
- Never mutate source archive files.
- Never mutate an existing archive manifest by default.
- Preserve skipped-file samples and blocker reasons.

Suggested outputs:

- `sandbox_venue_expansion_descriptor_candidates.json`
- `sandbox_venue_expansion_descriptor_candidates.parquet`
- `sandbox_venue_expansion_manifest_patch_dry_run.json`
- `sandbox_venue_expansion_manifest_patch_dry_run.parquet`
- `sandbox_venue_expansion_materializer_report.json`

Acceptance:

- Missing local roots fail closed.
- Non-overlapping windows are reported as `outside_requested_window`.
- Pre-2024 rows are excluded and cannot satisfy readiness.
- Multiple possible files are represented with deterministic candidate priority
  and no silent choice when ambiguity matters.

### End-To-End Smoke

The smallest useful closed loop should prove:

```text
venue expansion request bundle
  -> local materializer descriptor candidates
  -> candidate archive manifest written in a new output directory
  -> archive coverage matrix
  -> compatibility preflight
  -> bounded sandbox run or blocked preflight
  -> analysis/falsification
  -> artifact catalog/dashboard
  -> descriptor-only strict-validation request bundle
```

Use real local 2024+ samples where available. If samples are not available,
write an explicit skipped-real-smoke report and do not substitute synthetic
evidence as proof.

### Spreadsheet And Catalog Hardening

Required behavior:

- Multi-sheet workbook intake with sheet provenance.
- Header aliases for common human labels.
- Duplicate detection by hypothesis, strategy signature, signal column, params,
  and source sheet.
- Row-level skipped/repair queues with bounded sample payloads.
- Parameter normalization with strict parsing errors.
- `.xls` support either backed by declared dependency and tests, or explicitly
  unsupported with clear errors.
- Strategy source summaries in iteration manifests and dashboard artifacts.

### Dashboard And Next-Action Command

Future command:

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.main show-rapid-strategy-sandbox-next-action `
  --output-root data/research `
  --artifact-catalog <optional-catalog.json>
```

Required sections:

- current iteration status;
- top blockers;
- missing venue coverage;
- highest-priority strict-validation descriptors;
- highest-priority venue-expansion requests;
- stale or tampered artifact warnings;
- best hypotheses by source bucket;
- next recommended packet type;
- exact files to open next.

The dashboard must summarize existing artifacts. It must not recompute
rankings, mutate manifests, execute validation, or create candidate evidence.

## Phase 3 Strict-Validation Bridge Details

The bridge should make sandbox output useful to the strict cycle without giving
it authority.

Minimum descriptor fields:

- descriptor schema version;
- source sandbox run/suite/iteration IDs;
- source trial IDs and request IDs;
- strategy source identity and proxy/real policy;
- venue, symbol, data family, interval, window;
- archive logical identity and source integrity;
- entry, exit, filter, cost, fill, and validation assumptions;
- source metrics and blocker/falsification state;
- required strict-validation evidence;
- boundary flags and non-authorizing status.

Preflight outcomes:

- `accepted_for_strict_validation_planning`
- `blocked_missing_source_context`
- `blocked_missing_archive_identity`
- `blocked_proxy_only_strategy`
- `blocked_missing_required_validation_requirements`
- `blocked_boundary_violation`
- `blocked_pre_2024_window`
- `blocked_candidate_pack_or_promotion_flag`

The bridge packet must prove that accepted preflight rows still do not execute
strict validation, write candidate packs, or change promotion state.

## Phase 4 Performance Proof Details

Performance work must measure before optimizing.

Required telemetry:

- total runtime;
- per-stage runtime;
- rows loaded;
- rows retained after 2024+ and descriptor-window filters;
- archive files scanned, skipped, and loaded;
- compressed bytes and uncompressed bytes read;
- peak memory where measurable;
- trial cells planned, runnable, blocked, executed, and reused;
- cache hit rates by strategy mask, market array, descriptor frame, readiness,
  and suite input;
- vectorized path counts;
- fallback path counts and reasons;
- artifact write time and bytes written;
- workers requested and used;
- bottleneck ranking.

Required stress tests:

- thousands of files with `max_files=10` to prove early stop or bounded scan;
- ZIP/TAR/GZIP/NDJSON members with size/member limits;
- many descriptors sharing a source frame;
- descriptor windows that do not overlap the requested run window;
- dense 1m data and long holds for barrier exits;
- malformed workbook with excessive rows or XML/member sizes.

Do not claim "fast" without a benchmark artifact. A speedup claim requires a
baseline, repeated runs, cache state, hardware context, and identical output
identity or documented differences.

## Suggested Packet Backlog

Packet numbers are suggestions. If the ledger advances, use the next available
number and preserve the order/dependencies.

| Suggested packet | Phase | Objective |
| --- | --- | --- |
| WPR106-362 | 0 | Repo-state classification and commit-coherence audit. |
| WPR106-363 | 0 | Generated-output ignore/quarantine and tracked pytest-cache hygiene. |
| WPR106-364 | 0A | Strategy spacing metadata and discovery resume manifest red-test repair. |
| WPR106-365 | 0B | Sandbox and live CLI boundary CI coverage. |
| WPR106-366 | 1 | Path-safe `run_id` and output-root containment. |
| WPR106-367 | 1 | Descriptor-window intersection across audit, preflight, coverage, and execution. |
| WPR106-368 | 1 | Recursive sandbox boundary validation and nested forbidden-key tests. |
| WPR106-369 | 1 | Artifact child-path containment in integrity and consumers. |
| WPR106-370 | 1 | Decision identity and path-independent archive identity repair. |
| WPR106-371 | 1 | Proxy strategy policy decision and enforcement. |
| WPR106-372 | 1A | Fill-semantics compatibility and parity tests. |
| WPR106-373 | 2 | Venue-expansion local materializer, dry-run only. |
| WPR106-374 | 2A | End-to-end realistic closed-loop smoke. |
| WPR106-375 | 2B | Spreadsheet/catalog hardening and repair queues. |
| WPR106-376 | 2C | First-read dashboard and next-action command. |
| WPR106-377 | 3 | Strict-validation descriptor import/preflight schema. |
| WPR106-378 | 4 | Streaming/bounded archive scan and parser limits. |
| WPR106-379 | 4 | Throughput benchmark and telemetry report. |
| WPR106-380 | 5 | Reviewable PR split, final roadmap closeout, and publication checklist. |

## Evidence And Artifact Rules

Every generated research artifact should answer:

- What command or packet produced it?
- What source files or archive descriptors fed it?
- What window and 2024+ filter were applied?
- What rows were skipped and why?
- What exact strategy/exit/filter/cost/fill assumptions were used?
- What was blocked, falsified, mixed, or request-bearing?
- What next action is recommended?
- Why is it non-promotable?

Required artifact flags for sandbox outputs:

```json
{
  "research_only": true,
  "observe_only": true,
  "promotion_ready": false,
  "sandbox_only": true,
  "candidate_evidence": false,
  "candidate_pack_eligible": false,
  "live_signal": false,
  "paper_signal": false,
  "sizing_instruction": false,
  "order_placement_instruction": false,
  "runtime_mode_change": false
}
```

Parquet sidecars should be compact and query-friendly. JSON manifests should
retain enough nested context to reproduce and audit. Large row-level evidence
belongs in Parquet with bounded JSON summaries.

## Testing Matrix

| Change type | Minimum tests | Broaden when |
| --- | --- | --- |
| Docs-only | `git diff --check` | Docs alter validation or boundary claims. |
| CLI command | Command parser test, live CLI rejection test, focused behavior test. | Command touches output-root resolution or operator UI. |
| Sandbox spec/boundary | Focused sandbox tests, nested boundary regression, live CLI boundary. | Artifact consumers or shared manifests change. |
| Market loader | Loader fixtures, 2024+ filter, malformed input, source-integrity tests. | New compressed/container format is added. |
| Archive materializer | Request bundle fixtures, root scan tests, dry-run patch tests. | Manifest writer is added. |
| Sweep execution | Descriptor-window, exit/filter, ranking, cache identity tests. | Backtesting or fill semantics change. |
| Strategy intake | Workbook/CSV/JSON/Parquet tests, repair queue tests. | Strategy registry integration is added. |
| Strict-validation preflight | Accepted/blocked descriptor tests, no candidate-pack test. | Strict cycle starts consuming descriptors. |
| Performance | Benchmark smoke, stress test, telemetry schema test. | A speedup claim is made. |
| Backtesting shared code | Backtest contracts, reference/vector parity, focused unit tests. | CUDA/fallback paths are affected. |
| Discovery resume | Targeted resume tests and full `tests/research_discovery`. | Ledger/manifests/state schema changes. |

## Stop Conditions And Known-Issue Policy

Stop and open or update `docs/KNOWN_ISSUES.md` when:

- any P0 safety, live-boundary, data-corruption, or artifact-authority risk is
  found;
- a candidate pack can be written from sandbox evidence;
- a research artifact can contain nested live/paper/order/sizing instructions;
- pre-2024 rows can satisfy sandbox readiness;
- artifact consumers can read outside intended roots;
- full-suite failures are unrelated to a docs-only packet and block trust;
- a provider/source limitation changes the meaning of existing evidence;
- a speed or performance claim cannot be reproduced.

Do not close a P0/P1 by documenting it away. Close it only with a scoped fix
and validation evidence, or mark it accepted debt only if branch rules allow
that severity.

## Agent Operating Rules

Future implementation agents should follow this loop:

1. Read `AGENTS.md`, `docs/ACTIVE_INDEX.md`, this roadmap,
   `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md`, and
   `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`.
2. Confirm the latest packet number.
3. Create one packet with tight allowed paths.
4. Inspect code before editing.
5. Implement only the packet objective.
6. Add focused tests before broad validation.
7. Run validation and record exact results.
8. Update stage report, ledger, active index, and known issues if needed.
9. Leave unrelated dirty files untouched.
10. Do not merge or stage generated outputs accidentally.

## Definition Of Done

ResearchEngineDeluxe is complete for this roadmap when all are true:

- A clean or intentionally dirty-but-classified checkout is commit-coherent.
- Baseline validation and sandbox CI coverage pass.
- Known safety/provenance issues from the audit are fixed or explicitly parked
  as non-blocking with accepted severity.
- An agent can build or repair local archive descriptors from explicit 2024+
  local roots without downloads or source mutation.
- An agent can run a realistic end-to-end sandbox iteration from strategy
  catalogs and multi-venue archive manifests.
- The system writes a first-read dashboard or next-action artifact that points
  to exact blockers and next commands.
- Strict-validation descriptor preflight accepts or blocks handoffs
  deterministically without executing validation or writing candidate packs.
- Performance reports show realistic throughput, memory, cache, and fallback
  behavior.
- All outputs preserve research-only, observe-only, non-promotable boundaries.
- No live, paper, sizing, order, runtime-mode, live-config, candidate-pack, or
  promotion behavior is introduced by the research roadmap.

## Future Interfaces

The following are roadmap interfaces only. This document does not implement
them.

- `materialize-rapid-strategy-sandbox-venue-expansion-requests`
  - Inputs: `--request-bundle`, one or more `--archive-root`, optional
    `--output-dir`, optional venue/symbol/data-family/interval filters.
  - Outputs: descriptor candidates and dry-run manifest patch artifacts.
  - Required behavior: local-root scan only; no downloads; no source mutation;
    no validation execution.
- `show-rapid-strategy-sandbox-next-action`
  - Inputs: research output root, optional artifact catalog or iteration index.
  - Outputs: compact next-action JSON/Parquet and human-readable CLI summary.
  - Required behavior: summarize existing evidence only.
- Strict-validation descriptor import/preflight command, final name to be chosen
  in its packet.
  - Inputs: descriptor-only strict-validation bundle.
  - Outputs: accepted/blocked preflight rows.
  - Required behavior: no strict-cycle execution, no candidate packs, no
    promotion state.

## Non-Negotiable Gates

Every packet in this roadmap must preserve:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- `candidate_evidence: false` for sandbox outputs
- `candidate_pack_eligible: false` for sandbox outputs
- no live signals
- no paper signals
- no order-placement instructions
- no sizing instructions
- no runtime-mode changes
- no live configuration writes

Zero eligible candidates, missing archive coverage, blocked descriptors, failed
preflight rows, and validation-floor misses are acceptable research outputs.
They are not implementation failures by themselves.

## Packet Template For Future Agents

Use this packet shape for every implementation packet derived from the roadmap.

| Field | Required content |
| --- | --- |
| Objective | One concrete behavior change or audit outcome. |
| Dependencies | Prior packets and artifacts that must be closed first. |
| Allowed paths | Exact files or path globs; avoid broad paths unless justified. |
| Boundary constraints | Explicit no-live/no-paper/no-sizing/no-orders/no-promotion language. |
| Acceptance criteria | Observable behavior and artifact outputs. |
| Validation | Focused tests, contract baseline, and broader suites when touching shared contracts. |
| Stop conditions | Conditions that force issue logging instead of continuing. |
| Exit evidence | Stage report, ledger row, and any generated research-only artifacts. |

## Suggested First Implementation Sequence

1. Open a Phase 0 repo-state audit packet and classify all dirty and untracked
   files.
2. Make the sandbox source/test/config surface commit-coherent or remove tracked
   imports that depend on untracked code.
3. Ignore or quarantine generated `outputs/` and remove tracked pytest cache in
   a scoped hygiene packet.
4. Fix the two reproduced red tests and run the full suite.
5. Add sandbox and CLI-boundary validation to CI.
6. Repair sandbox path, boundary, descriptor-window, identity, artifact-path,
   proxy-strategy, and fill-semantics risks.
7. Only then implement the local venue-expansion materializer.
8. Prove the smallest realistic 2024+ closed loop.
9. Add dashboard/next-action and strict-validation preflight bridge.
10. Add performance proof after the closed loop works.

## Validation Baseline

For documentation-only roadmap packets:

```powershell
git diff --check
```

For Phase 0 and later implementation packets:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
```

Broaden validation when touching shared contracts:

- Backtesting/fill changes: `tests/backtesting`, `tests/contracts/test_backtest_contracts.py`, and relevant CUDA/vector parity tests.
- Strategy metadata changes: `tests/contracts/test_strategy_contracts.py`, `tests/optimization/test_search_space_expansion.py`.
- Discovery resume changes: `tests/research_discovery`.
- Candidate-pack or promotion-adjacent changes: `tests/research_artifacts`, `tests/live`, and import-boundary tests.

If Windows socket exhaustion blocks contract validation, cite
`ISSUE-R106-026` and do not claim a green contract baseline.
