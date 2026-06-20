# WPR106-358 Next Agent Handoff - Sandbox Self-Audit

Date: 2026-06-19

## Read This First

This is the current visible self-audit for the rapid strategy iteration sandbox
rewrite. Read it after `AGENTS.md`, `docs/ACTIVE_INDEX.md`, and
`docs/ORCHESTRATOR_STAGE_LEDGER.md`.

The active objective is still broader than the latest packet: build a 2024+
research-only Rapid Strategy Iteration Sandbox that ingests existing strategy
spreadsheets/catalogs and multi-venue archive manifests, runs fast vectorized
strategy/exit/filter sweeps, writes compact reproducible JSON/Parquet artifacts
with deterministic trial IDs, ranks and falsifies hypotheses quickly, and emits
only descriptor evidence requests into the existing strict-validation cycle.

Do not mark the broad objective complete yet. Current evidence shows strong
incremental progress, not final completion.

## Current State

The sandbox exists under `src/tradingbotsuite/research_sandbox/` and is now a
large research-only subsystem. It has:

- strategy spreadsheet/catalog intake and materialization;
- local archive manifest building and descriptor audit paths;
- OKX, Bybit, Hyperliquid, Binance, and local archive descriptor handling;
- 2024+ market-window enforcement across sandbox loading paths;
- fixed-hold and vectorized primary-bar target/stop sweep support;
- exit/filter grids;
- run, suite, iteration, preflight, archive coverage, catalog, leaderboard,
  falsification, integrity, and request-bundle artifacts;
- deterministic trial, run, suite, bundle, and request identities;
- compact JSON/Parquet outputs and catalog sidecars for agent navigation;
- descriptor-only strict-validation request bundles;
- descriptor-only venue-expansion gap worklists and request bundles.

The newest closed packet is WPR106-357. It added
`export-rapid-strategy-sandbox-venue-expansion-requests`, which turns existing
catalog-level venue-expansion worklist rows into portable descriptor-only OKX,
Bybit, and Hyperliquid archive-intake request bundles:

- `sandbox_venue_expansion_request_bundle.json`
- `sandbox_venue_expansion_request_bundle.parquet`

The exporter reads only `sandbox_artifact_catalog.json` and its
`sandbox_artifact_catalog_iteration_venue_expansion_gap_worklist.parquet`
sidecar. It does not download provider data, mutate archive manifests, mutate
source files, execute replay commands, execute validation, or write candidate
packs.

## What Is Solid

- The research/live boundary remains intact. Sandbox artifacts are
  `research_only`, `observe_only`, `promotion_ready: false`,
  `candidate_evidence: false`, and `candidate_pack_eligible: false`.
- Sandbox commands are registered as research commands and covered by live CLI
  boundary tests.
- The artifact model is consistent: outputs are compact JSON/Parquet files with
  deterministic IDs, boundary flags, and non-authorizing handoff metadata.
- Agent navigation is much better than at the start of the sandbox rewrite:
  artifact catalogs, sidecar indexes, action queues, replay plans, strict
  validation queues, global evidence queues, and venue-expansion worklists now
  exist.
- The archive path is no longer Binance-only in the sandbox model. OKX, Bybit,
  and Hyperliquid are first-class target venues in archive coverage, iteration
  handoffs, catalog worklists, and request bundles.

## Validation Evidence

Latest WPR106-357 validation:

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "venue_expansion_request or iteration_index_summarizes_agent_iterations_and_briefs"`
  reported 2 passed, 173 deselected.
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`
  reported 23 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q`
  reported 175 passed.
- `$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` reported
  461 passed.
- `git diff --check` passed with existing LF-to-CRLF warnings only.
- A targeted trailing-whitespace scan of packet-touched files produced no
  output.

This proves WPR106-357, not the full sandbox rewrite objective.

## Worktree Reality

The worktree is heavily dirty. Many sandbox files and docs are still untracked
from Git's point of view even though tests use them as current working code.
There are also many unrelated modified files from prior WPR106 work.

Do not revert unrelated changes. Assume dirty files may be prior agent work
unless the current packet proves otherwise.

Known practical friction:

- `git diff --check` reports many LF-to-CRLF warnings from existing files.
- The sandbox has many sidecars and catalog fields. Agent navigation is fast,
  but the overall artifact map is now broad and needs careful naming discipline.
- The current system can identify missing venue archive coverage and emit
  descriptor-only requests, but it does not yet safely materialize repaired
  archive manifests from those requests.

## What Is Still Left

The next material gap is archive-request execution support that still preserves
the research boundary.

Current system:

1. Detects venue expansion gaps.
2. Surfaces them in iteration handoffs.
3. Flattens them into catalog worklists.
4. Exports portable descriptor-only venue-expansion request bundles.

Missing system:

1. Read a venue-expansion request bundle.
2. Scan only user-provided local archive roots.
3. Match local files to requested venue, symbol, data family, interval, and
   2024+ window.
4. Emit descriptor candidates and a dry-run manifest patch report.
5. Optionally write a new sandbox archive manifest in a later explicitly scoped
   packet, without mutating source manifests by default.

Other important unfinished work:

- End-to-end fixture from venue request bundle to repaired local manifest to
  coverage matrix to iteration rerun.
- Higher-level agent command such as "next sandbox action" or "repair requested
  local archives from roots" that avoids manually opening many sidecars.
- Larger realistic 2024+ integration runs against actual repo strategy sheets
  and local archive directories, not just synthetic tests.
- More performance instrumentation for cache hit rates, vectorized path use,
  market-frame reuse, and sweep throughput.
- A compact top-level sandbox dashboard artifact. The catalog is powerful, but
  a next-agent first-read summary would reduce orientation cost.
- Cleanup plan for the large local dirty/untracked worktree before any PR or
  branch publication.

## Recommended Next Packet

Recommended packet:

`docs/work_packets/WPR106-359-sandbox-venue-expansion-local-materializer.md`

Recommended title:

`Sandbox Venue Expansion Local Materializer`

Recommended objective:

Consume `sandbox_venue_expansion_request_bundle.json`, scan only explicitly
provided local archive roots, and write descriptor-candidate and dry-run
manifest patch artifacts for missing OKX, Bybit, and Hyperliquid archive
coverage. The packet should not download provider data and should not mutate
source archive files or existing manifests.

Recommended first implementation target:

- CLI command:
  `materialize-rapid-strategy-sandbox-venue-expansion-requests`
- Inputs:
  `--request-bundle`, one or more `--archive-root`, optional `--output-dir`,
  optional venue/symbol/data-family/interval filters.
- Outputs:
  `sandbox_venue_expansion_descriptor_candidates.json`
  `sandbox_venue_expansion_descriptor_candidates.parquet`
  `sandbox_venue_expansion_manifest_patch_dry_run.json`
  `sandbox_venue_expansion_manifest_patch_dry_run.parquet`
- Boundary:
  descriptor candidates only, dry-run manifest patch only, no provider
  downloads, no source mutation, no replay execution, no validation execution,
  no candidate packs, no live/paper/sizing/order/runtime behavior.

## Mandatory Next-Agent Rules

Before code or generated-evidence changes:

1. Read `AGENTS.md`.
2. Read `docs/ORCHESTRATOR_STAGE_LEDGER.md`.
3. Read `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`.
4. Read `docs/ACTIVE_INDEX.md`.
5. Read this handoff.
6. Write a new work packet and keep edits inside its allowed paths.
7. Preserve the 2024+ rule and the research-only/no-live/no-candidate boundary.

Do not treat descriptor bundles as execution authorization. They are navigation
and handoff artifacts only.
