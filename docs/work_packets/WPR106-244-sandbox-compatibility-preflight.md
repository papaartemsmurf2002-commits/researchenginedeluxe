# WPR106-244 Sandbox Compatibility Preflight

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Add a fast Rapid Strategy Iteration Sandbox preflight that checks a run spec,
strategy catalog, and venue archive manifest before a full archive-backed
sweep. Agents should see trial counts, missing signal/filter/OHLC columns,
window coverage, and blueprint materialization compatibility quickly.

## Scope

- Add a sandbox compatibility preflight API over existing sandbox loaders.
- Load an existing `SandboxRunSpec`, strategy catalog, and venue archive
  manifest.
- Load each venue market frame through the existing 2024+ normalization path.
- Materialize strategy blueprint proxy signals once per venue frame before
  checking required columns.
- Report compatibility rows for every strategy/venue pair and aggregate
  runnable/blocked trial estimates across holding periods, exit variants, and
  filter variants.
- Write compact JSON and Parquet artifacts:
  - `sandbox_compatibility_preflight.json`;
  - `sandbox_compatibility_preflight.parquet`.
- Add a research CLI command `preflight-rapid-strategy-sandbox` with
  research-root output enforcement.
- Register the command as research-owned and add boundary contract coverage.
- Add focused sandbox and live-boundary tests.
- Update sandbox docs and stage closeout docs.

## Allowed Paths

- `docs/work_packets/WPR106-244-sandbox-compatibility-preflight.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_COMPATIBILITY_PREFLIGHT_REPORT.md`
- `docs/contracts/boundary_contract.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/research/command_registry.py`
- `src/tradingbotsuite/research_sandbox/**`
- `tests/research_sandbox/**`
- `tests/live/test_cli_boundary.py`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Preflight reports runnable and blocked strategy/venue combinations before a
  sweep.
- Blueprint-derived strategy rows are checked after signal materialization, not
  as false missing-signal blockers.
- Missing direct signal columns, missing strategy/filter columns, missing
  variant filter columns, missing OHLC columns for target/stop exits, empty
  2024+ windows, and missing descriptor data paths are reported explicitly.
- Trial estimate counts reflect strategy x venue x holding-period x
  exit-variant x filter-variant combinations.
- Generated artifacts carry `research_only`, `observe_only`,
  `promotion_ready: false`, `sandbox_only`, `candidate_evidence: false`, and
  `candidate_pack_eligible: false`.
- The CLI rejects `--output-dir` outside the configured research output root.
- Validation includes focused sandbox tests, CLI boundary tests,
  import-boundary tests, package compile, and the contract baseline when the
  local validation environment allows pytest-asyncio socket setup.

## Boundary

This packet performs preflight analysis only. It does not execute sandbox
sweeps, execute strict validation, write candidate packs, create paper/live
signals, define sizing, place orders, mutate runtime mode, write live
configuration, download provider data, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. The packet added
`preflight_sandbox_compatibility()` and the
`preflight-rapid-strategy-sandbox` research CLI command. The preflight loads a
sandbox spec, strategy catalog, and venue archive manifest, normalizes each
venue frame through the existing 2024+ sandbox loader, materializes blueprint
signals inside the filtered window, and reports one compatibility row per
strategy/venue pair.

The preflight writes deterministic `sandbox_compatibility_preflight.json` and
`sandbox_compatibility_preflight.parquet` artifacts under the configured
research output root. Rows include runnable and blocked trial estimates across
holding periods, exit variants, and filter variants, plus explicit blockers for
missing data paths, loader failures, empty 2024+ windows, missing signal/filter
columns, and missing high/low columns required by target/stop exits. Artifacts
keep the required sandbox flags and remain non-promotable.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 67 sandbox tests passed, 19 CLI boundary tests passed, 11
import-boundary tests passed, package compileall passed, and the full contract
baseline passed with 461 tests.
