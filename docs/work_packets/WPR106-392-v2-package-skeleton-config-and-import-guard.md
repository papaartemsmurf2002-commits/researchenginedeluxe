# WPR106-392 V2 Package Skeleton Config And Import Guard

Status: closed
Owner: Codex Research Agent
Created: 2026-06-20

## Objective

Implement Phase 1 of `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md`: create
the v2 code shell, bounded-context packages, shared config/schema constants,
audit marker helper, a minimal research-only CLI help entrypoint, and tests
that prove the skeleton imports without importing live/order/sizing runtime
modules.

This packet creates shell infrastructure only. It does not implement archive,
collector, universe, backtest, strategy, cost, ledger, Lead Book, validation,
UI, paper/live, runtime, sizing, order-placement, candidate-pack, or promotion
behavior.

## Audit IDs

- `V2-AUD-PKG-001`
- `V2-AUD-SCOPE-002`

## Dependencies

- `docs/PRODUCT_SCOPE.md`
- `docs/V2_DECISION_REGISTER.md`
- `docs/V2_NO_TOUCH_PATHS.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md`
- `docs/work_packets/WPR106-391-v2-phase0-scope-source-lock-and-safety-rails.md`

## Allowed Paths

- `src/tradingbotsuite/v2/**`
- `tests/v2/**`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/work_packets/WPR106-392-v2-package-skeleton-config-and-import-guard.md`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Constraints

- Preserve research-only, observe-only, non-promotable semantics.
- Do not create or modify candidate packs.
- Do not create paper/live artifacts.
- Do not place orders, change runtime mode, write live configuration, or add
  sizing/order-placement behavior.
- Do not modify legacy source packages outside `src/tradingbotsuite/v2/**`.
- Do not add a broad CLI integration into the existing top-level CLI in this
  packet; use `python -m tradingbotsuite.v2.cli.main --help` for the Phase 1
  smoke.

## Acceptance Criteria

- `python -m tradingbotsuite.v2.cli.main --help` works with `PYTHONPATH=src`.
- Importing `tradingbotsuite.v2` does not import live/order/sizing runtime
  modules.
- All new v2 modules contain module-level audit markers.
- CLI help states research-only and non-live/non-paper/non-order/non-sizing
  boundary.
- Focused v2 tests pass.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.v2.cli.main --help
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
python -m compileall -q src/tradingbotsuite/v2
git diff --check
```

No full contract run is required unless this packet touches shared non-v2
implementation files, which it explicitly does not.

## Stop Conditions

- A no-touch path must be modified.
- A live/order/sizing/runtime import is needed.
- A real archive, collector, universe, strategy, backtest, ledger, Lead Book,
  paper/live, order, sizing, runtime, candidate-pack, or promotion behavior
  becomes necessary.

## Completion Notes

Closed on 2026-06-20.

- Added the `src/tradingbotsuite/v2/` package shell.
- Added bounded-context package roots for archive, universe, venues,
  collectors, data quality, backtest data, strategy specs, strategy plugins,
  backtest engine, costs, validation, ledger, Lead Book, workers, audit, and
  security.
- Added v2 config defaults and schema constants for research-only boundary,
  bounded contexts, schema version, Hyperliquid primary venue, USD 5M notional
  floor, 2024+ start, 6-month minimum, 12-month preference, 0.98 coverage, and
  dynamic lockbox default.
- Added `src/tradingbotsuite/v2/audit/markers.py` as the Phase 1 marker helper.
- Added `python -m tradingbotsuite.v2.cli.main` as a minimal research-only
  command shell with help, boundary, version, and bounded-context output.
- Added focused tests under `tests/v2/` for CLI help, settings defaults, static
  forbidden-import scanning, runtime import loading, and required audit markers.
- Marked `V2-AUD-PKG-001` and `V2-AUD-SCOPE-002` as `self_checked` in
  `docs/audit/V2_AUDIT_INDEX.md`.
- No archive, collector, universe, strategy, backtest, ledger, Lead Book,
  paper/live, order, sizing, runtime, candidate-pack, or promotion behavior was
  implemented.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.v2.cli.main --help
$env:PYTHONPATH='src'; python -m tradingbotsuite.v2.cli.main --show-boundary
$env:PYTHONPATH='src'; python -m tradingbotsuite.v2.cli.main --list-contexts
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
git diff --check
```

Result:

- CLI help passed and states the research-only, non-live, non-paper, no-order,
  no-sizing, no-runtime, no-promotion boundary.
- Boundary command printed all required false/true invariant fields.
- Bounded-context command listed all Phase 1 context shells.
- Focused v2 tests passed: 6 passed.
- `compileall` for `src\tradingbotsuite\v2` passed.
- `git diff --check` passed with LF-to-CRLF warnings only for pre-existing
  text-file line-ending behavior.
