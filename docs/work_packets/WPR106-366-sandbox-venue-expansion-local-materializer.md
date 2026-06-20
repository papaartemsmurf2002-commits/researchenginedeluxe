# WPR106-366 - Sandbox Venue Expansion Local Materializer

## Status

closed

## Objective

Consume descriptor-only sandbox venue-expansion request bundles, scan only
explicitly supplied local archive roots, and emit descriptor-candidate plus
dry-run manifest patch artifacts for missing OKX, Bybit, and Hyperliquid
coverage.

## Dependencies

- `RAPID_STRATEGY_SANDBOX_AUDIT.md`
- `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md`
- `docs/NEXT_AGENT_HANDOFF_WPR106_358_SANDBOX_SELF_AUDIT.md`
- `docs/work_packets/WPR106-357-sandbox-venue-expansion-request-bundle.md`
- `docs/work_packets/WPR106-362-post-audit-sandbox-safety-coherence.md`
- `docs/work_packets/WPR106-365-sandbox-commit-coherence-classification.md`

## Allowed paths

- `src/tradingbotsuite/research_sandbox/venue_expansion_materializer.py`
- `src/tradingbotsuite/research_sandbox/__init__.py`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/research/command_registry.py`
- `tests/research_sandbox/**`
- `tests/live/test_cli_boundary.py`
- `docs/contracts/sandbox_research_contract.md`
- `docs/contracts/boundary_contract.md`
- `docs/work_packets/WPR106-366-sandbox-venue-expansion-local-materializer.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_VENUE_EXPANSION_LOCAL_MATERIALIZER_REPORT.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a blocking risk is discovered

## Boundary constraints

- Research-only, observe-only, sandbox-only output.
- Descriptor candidates and manifest patch previews are dry-run artifacts only.
- Do not download provider data.
- Do not mutate source archive files, existing archive manifests, strategy
  catalogs, iteration indexes, catalog sidecars, live config, or candidate
  packs.
- Do not execute sandbox sweeps, replay commands, strict validation, paper/live
  flows, order placement, sizing, or runtime-mode changes.
- Preserve 2024+ sandbox window constraints.
- Keep every output `promotion_ready: false`, `candidate_evidence: false`,
  and `candidate_pack_eligible: false`.

## Implementation notes

- Add a module that exports:
  - `sandbox_venue_expansion_descriptor_candidates.json`
  - `sandbox_venue_expansion_descriptor_candidates.parquet`
  - `sandbox_venue_expansion_manifest_patch_dry_run.json`
  - `sandbox_venue_expansion_manifest_patch_dry_run.parquet`
- Register the research CLI command:
  `materialize-rapid-strategy-sandbox-venue-expansion-requests`.
- Inputs:
  `--request-bundle`, one or more `--archive-root`, optional `--output-dir`,
  optional `--venue`, `--symbol`, `--data-family`, `--interval`, and
  `--max-files`.
- Matching should use canonical venue, compact symbol key, data family,
  interval, and requested/observed 2024+ window overlap.
- Missing coverage must produce blocker rows, not fabricated descriptors.

## Acceptance criteria

- Descriptor candidates are written only for matching local files.
- Dry-run rows report unmatched request blockers.
- Pre-2024 request windows are rejected.
- CLI output path stays under the configured research output root.
- Research command registry and boundary contract include the new command.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "venue_expansion_local_materializer"
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

## Exit evidence

- Added `materialize_sandbox_venue_expansion_requests`, which consumes a
  descriptor-only venue-expansion request bundle and scans only explicitly
  supplied local archive roots.
- Added descriptor-candidate output:
  `sandbox_venue_expansion_descriptor_candidates.json` and `.parquet`.
- Added manifest-patch dry-run output:
  `sandbox_venue_expansion_manifest_patch_dry_run.json` and `.parquet`.
- Added the research CLI command
  `materialize-rapid-strategy-sandbox-venue-expansion-requests` with
  request-bundle/output path guarding under the configured research output
  root and explicit archive-root read inputs.
- Added request matching by canonical venue, compact symbol key, data family,
  interval, and requested-window overlap. Unmatched requests produce blocker
  dry-run rows instead of fabricated descriptors.
- Added pre-2024 request-window refusal.
- Registered the command in the research command registry and boundary
  contract, and documented the dry-run materializer boundary in the sandbox
  research contract.
- Validation passed:
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "venue_expansion_local_materializer or materializes_venue_expansion_requests"`
  reported 3 passed / 175 deselected;
  `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`
  reported 23 passed;
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  reported 192 passed;
  `python -m compileall -q src\tradingbotsuite` passed;
  `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` reported
  461 passed.
- Ignored local smoke under `outputs/wpr106_366_smoke` ran
  `run-rapid-strategy-sandbox-iteration`, built an iteration index, exported a
  venue-expansion request bundle, and ran the new materializer. The final
  materializer smoke produced 2 request rows, 1 Bybit descriptor candidate,
  and 1 blocked Hyperliquid request; all outputs remained dry-run,
  descriptor-only, non-promotable, and non-candidate-evidence.
- `git diff --check` passed with existing LF-to-CRLF warnings only.
