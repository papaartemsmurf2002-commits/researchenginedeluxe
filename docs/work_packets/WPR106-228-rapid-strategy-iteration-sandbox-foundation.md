# WPR106-228 Rapid Strategy Iteration Sandbox Foundation

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Add the first research-only Rapid Strategy Iteration Sandbox layer for
ResearchEngineDeluxe. The sandbox must let agents ingest existing strategy
catalog/spreadsheet rows and multi-venue archive manifest descriptors, run
fast 2024+ vectorized strategy/exit/filter sweeps, write compact reproducible
Parquet/JSON artifacts with deterministic trial IDs, rank and falsify
hypotheses quickly, and emit only evidence-request descriptors for later strict
validation.

This packet creates a sandbox foundation beside the existing strict
`research_cycle`; it does not rewrite candidate gates, historical-cycle
semantics, live execution, paper execution, sizing, runtime mode, or promotion
logic.

## Scope

- Add an isolated `tradingbotsuite.research_sandbox` package with:
  - sandbox spec and validation profiles;
  - non-promotable boundary invariants;
  - deterministic trial/run identity helpers;
  - strategy-catalog and venue-archive manifest intake models;
  - simple vectorized fixed-hold sweeps for high-throughput first-pass
    hypothesis falsification;
  - compact result storage under immutable run directories;
  - ranking/rejection summaries and evidence-request descriptors.
- Add focused tests for 2024+ enforcement, boundary flags, deterministic trial
  IDs, Parquet/JSON result artifacts, fast fixed-hold sweep behavior, and
  evidence-request descriptor safety.
- Extend import-boundary coverage so the sandbox package cannot import
  order-placement/live runtime paths.
- Document the sandbox contract and stage outcome.

## Allowed Paths

- `docs/work_packets/WPR106-228-rapid-strategy-iteration-sandbox-foundation.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/stage_reports/STAGE_R106_RAPID_STRATEGY_ITERATION_SANDBOX_FOUNDATION_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/ACTIVE_INDEX.md`
- `src/tradingbotsuite/research_sandbox/**`
- `tests/research_sandbox/**`
- `tests/contracts/test_import_boundaries.py`
- `configs/sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Sandbox specs reject any requested data window before `2024-01-01`.
- Sandbox manifests and evidence requests always contain
  `research_only: true`, `observe_only: true`, `promotion_ready: false`,
  `sandbox_only: true`, `candidate_evidence: false`, and
  `candidate_pack_eligible: false`.
- Strategy catalog rows can be loaded from CSV-like tables without importing or
  executing external strategy code.
- Venue archive descriptors can represent Binance, OKX, Bybit, Hyperliquid, or
  local manifest sources while defaulting to diagnostic/non-promotable evidence.
- Fast fixed-hold sweeps are deterministic, cost-aware enough for first-pass
  falsification, and record rejection reasons rather than candidate claims.
- Result storage writes a manifest, summary Parquet, rankings Parquet, and
  evidence-request JSON/Parquet outputs under a run directory.
- Import-boundary tests cover `tradingbotsuite.research_sandbox`.
- Validation includes focused sandbox tests, source compile, and contracts
  baseline.

## Boundary

Sandbox outputs are idea-triage artifacts only. They are not candidate-ready,
portfolio-ready, paper-ready, live-ready, sizing, runtime, order-placement, or
promotion artifacts. The sandbox can request later strict validation, but it
must not write candidate packs or weaken existing gates.

## Completion Notes

Implemented by WPR106-228 and closed on 2026-06-18. The packet added
`tradingbotsuite.research_sandbox`, focused tests, a sandbox research contract,
and a config template. Validation passed:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results were 7 focused sandbox tests passed, 11 import-boundary tests passed,
package compile passed, and 461 contract tests passed.
