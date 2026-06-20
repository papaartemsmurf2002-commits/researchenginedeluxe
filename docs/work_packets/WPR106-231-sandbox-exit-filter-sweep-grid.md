# WPR106-231 Sandbox Exit Filter Sweep Grid

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Extend the Rapid Strategy Iteration Sandbox from fixed-hold-only triage into a
bounded strategy/exit/filter sweep layer. The packet adds sandbox-only exit
variants and filter variants so agents can falsify hypothesis families faster
without touching the strict historical research cycle or producing candidate
evidence.

## Scope

- Add non-promotable sandbox exit variants:
  - fixed hold;
  - target-only;
  - stop-only;
  - conservative target/stop where same-bar target/stop ambiguity exits at the
    stop.
- Add run-spec filter variants that can sweep additional completed-bar column
  thresholds beside a strategy's base filter.
- Include exit/filter variant identity in deterministic trial IDs and result
  payloads.
- Preserve current default behavior when no exit/filter variants are supplied.
- Materialize all exit/filter logic after the 2024+ sandbox market-window
  filter.
- Record exit/fill assumptions in result metadata.
- Add focused tests for exit-grid behavior, filter-grid behavior, deterministic
  trial identity, blocked missing OHLC requirements, and non-promotable output
  flags.
- Update sandbox docs and stage closeout docs.

## Allowed Paths

- `docs/work_packets/WPR106-231-sandbox-exit-filter-sweep-grid.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_EXIT_FILTER_SWEEP_GRID_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/**`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- A default sandbox run still produces the same fixed-hold grid shape as before.
- Run specs can declare exit variants and filter variants.
- Trial IDs differ across exit/filter variants while remaining stable for the
  same variant payload.
- Target/stop exits require high/low data and block clearly when unavailable.
- Conservative target/stop exits document same-bar stop-first behavior.
- Filter variants apply to completed 2024+ rows only and can screen/reject
  different rows from the base strategy.
- All result and artifact payloads remain `research_only`, `observe_only`,
  `promotion_ready: false`, `sandbox_only`, `candidate_evidence: false`, and
  `candidate_pack_eligible: false`.
- Validation includes focused sandbox tests, import-boundary tests, package
  compile, and the contract baseline where the local Windows socket environment
  allows it to start asyncio fixtures.

## Boundary

Exit and filter variants are sandbox approximations for rapid falsification.
They are not strict lower-timeframe execution evidence and cannot create
candidate packs, paper/live signals, sizing instructions, order instructions,
runtime changes, live configuration writes, or promotion claims.

## Completion Notes

Implemented and closed on 2026-06-18. The packet added typed sandbox
`ExitVariant` and `FilterVariant` spec objects, JSON run-spec loading for
variant grids, variant-aware deterministic trial IDs, result payload columns for
exit/filter identity, primary-bar target/stop proxy exits, completed-row filter
variant application, and metadata documenting exit/fill assumptions.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results were 25 sandbox tests passed, 11 import-boundary tests passed,
package compileall passed, and 461 contract tests passed.
