# WPR106-357 - Sandbox Venue Expansion Request Bundle

## Status

closed

## Objective

Add a descriptor-only venue expansion request bundle that turns catalog-level
venue-expansion worklist rows into portable OKX, Bybit, and Hyperliquid
archive-intake tasks. The bundle must help agents collect or repair local
archive descriptors for missing venue coverage without opening every iteration
index, mutating source manifests, downloading provider data, or running
validation.

## Allowed paths

- `src/tradingbotsuite/research_sandbox/venue_expansion_requests.py`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `src/tradingbotsuite/research_sandbox/__init__.py`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/research/command_registry.py`
- `tests/research_sandbox/**`
- `tests/live/test_cli_boundary.py`
- `docs/contracts/sandbox_research_contract.md`
- `docs/contracts/boundary_contract.md`
- `docs/work_packets/WPR106-357-sandbox-venue-expansion-request-bundle.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_VENUE_EXPANSION_REQUEST_BUNDLE_REPORT.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a blocking risk is discovered

## Boundary constraints

- Research-only, sandbox-only output only.
- Derive requests only from already-written sandbox artifact catalog JSON or
  its venue-expansion worklist sidecar.
- Do not create or mutate archive manifests, source archive files, strategy
  catalogs, iteration indexes, or catalog sidecars.
- Do not download OKX, Bybit, Hyperliquid, Binance, or other provider data.
- Do not execute replay commands, sandbox sweeps, strict validation, or
  candidate-pack writes.
- Keep all output `research_only`, `observe_only`, `promotion_ready: false`,
  `candidate_evidence: false`, and `candidate_pack_eligible: false`.
- Preserve 2024+ sandbox window constraints, trial IDs, scoring, ranking,
  evidence-request selection, archive routing, replay readiness, and promotion
  state.

## Implementation notes

- Add a module that exports
  `sandbox_venue_expansion_request_bundle.json` and
  `sandbox_venue_expansion_request_bundle.parquet`.
- Dedupe rows by target venue, compact market-symbol key, data family,
  interval, target action, and target bucket key while preserving bounded
  source iteration/action/path references.
- Register a CLI command:
  `export-rapid-strategy-sandbox-venue-expansion-requests`.
- Require the command to resolve paths under the configured research output
  root through the existing CLI path guards.
- Register the command in `RESEARCH_COMMANDS` and the boundary contract.
- Add focused tests for bundle payloads, Parquet rows, CLI wiring, path guards,
  and live-boundary registration.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "venue_expansion_request or iteration_index_summarizes_agent_iterations_and_briefs"`
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q`
- `$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
- `git diff --check`

## Exit evidence

- Added `sandbox_venue_expansion_request_bundle.json` and
  `sandbox_venue_expansion_request_bundle.parquet` exporters that read only the
  sandbox artifact catalog and its venue-expansion gap worklist sidecar.
- Added deterministic descriptor dedupe by target venue, compact market-symbol
  key, data family, interval, target action, and target bucket key while
  preserving bounded source iteration, queue, path, and reference metadata.
- Added the `export-rapid-strategy-sandbox-venue-expansion-requests` research
  CLI command with catalog, optional worklist, and output path resolution under
  the configured research output root.
- Registered the bundle JSON in artifact catalog discovery as
  `venue_expansion_request_bundle`.
- Preserved descriptor-only, research-only, observe-only, non-promotable
  boundary flags; added explicit false authorization flags for provider
  download, archive manifest writes, archive source mutation, replay execution,
  strict validation, and candidate-pack writes.
- Validation passed:
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "venue_expansion_request or iteration_index_summarizes_agent_iterations_and_briefs"`
  reported 2 passed / 173 deselected;
  `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`
  reported 23 passed;
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q`
  reported 175 passed;
  `$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite` passed;
  `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` reported
  461 passed; `git diff --check` passed with only existing LF-to-CRLF warnings;
  targeted trailing-whitespace scan of packet-touched files produced no output.
