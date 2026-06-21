# WPR106-401 V2 Declarative Strategy Spec Lane

Status: closed
Owner: Codex Research Agent
Created: 2026-06-21

## Objective

Implement Phase 10 of `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md`: add
the first v2 declarative strategy spec lane with a schema, validator, allowed
indicator/expression registry, deterministic compile-to-signal-frame helper,
example strategy specs, CLI validation, and side-effect rejection.

This packet does not implement Python strategy plugins, the Phase 11 vectorized
backtest engine, cost model execution, ledgers, Lead Book workflow, UI,
paper/live behavior, order placement, sizing, runtime-mode changes, candidate
packs, or promotion behavior.

## Audit IDs

- `V2-AUD-STRAT-001`

## Dependencies

- `docs/contracts/strategy_spec_contract.md`
- `docs/contracts/strategy_plugin_contract.md`
- `src/tradingbotsuite/v2/backtest_data/**`
- `src/tradingbotsuite/v2/config/**`
- `src/tradingbotsuite/v2/validation/**`

## Allowed Paths

- `docs/contracts/strategy_spec_contract.md`
- `docs/contracts/strategy_plugin_contract.md`
- `src/tradingbotsuite/v2/strategy_specs/**`
- `src/tradingbotsuite/v2/cli/main.py`
- `tests/v2/**`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/work_packets/WPR106-401-v2-declarative-strategy-spec-lane.md`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Constraints

- Preserve research-only, observe-only, non-promotable semantics.
- Declarative specs must not contain arbitrary Python, imports, eval/exec,
  shell/subprocess language, network/URL access, secret/credential references,
  arbitrary file/path references, live/order/sizing/paper/runtime behavior, or
  lockbox access.
- Evidence-mode specs must use as-of universe semantics and exclude lockbox.
- Unknown schema keys must fail closed.
- Cost and slippage model declarations are required.
- The compile helper may produce deterministic signal-frame rows from an
  in-memory panel only; it must not read files, call networks, place orders, or
  execute strategy code.

## Acceptance Criteria

- At least three declarative example strategies validate.
- Invalid specs fail with clear errors.
- Specs cannot request network, secrets, arbitrary files, live/order paths, or
  lockbox access.
- Unsupported indicators, expressions, data fields, or cost omissions fail.
- Spec hash changes when material strategy content changes.
- A validated spec can compile an in-memory fixture panel into a deterministic
  research-only signal frame.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

No broader non-v2 tests are required unless shared implementation files outside
the v2 shell are changed.

## Stop Conditions

- A no-touch live/runtime/order/sizing path must be modified.
- Python strategy plugin execution, a backtest runner, ledger append workflow,
  Lead Book workflow, candidate-pack, paper/live, order, sizing, runtime, or
  promotion behavior becomes necessary.
- Declarative specs cannot be made fail-closed for side-effect or unknown-key
  content.

## Completion Notes

Closed on 2026-06-21.

- Added Phase 10 declarative strategy schemas:
  - `StrategySpec`
  - `StrategySpecValidationResult`
  - `MarketScope`
  - `StrategyInputs`
  - `StrategyLogic`
  - `RiskConfig`
  - `ExecutionConfig`
  - `StrategyValidationConfig`
  - `SignalFrame`
  - `SignalRow`
- Added an allowed declarative registry for signal types, input fields, rank
  metrics, filters, price basis, fee models, and slippage models.
- Added fail-closed validation for:
  - unknown schema keys;
  - unsupported fields, filters, signal types, and rank metrics;
  - missing cost/slippage models;
  - arbitrary Python/eval/exec/import/subprocess/socket content;
  - network URLs;
  - secret or credential references;
  - arbitrary file/path references;
  - live/order/sizing/paper/runtime language;
  - lockbox access and current-universe accepted/reported evidence.
- Added five built-in declarative examples:
  - cross-sectional momentum;
  - mean reversion;
  - funding/carry;
  - volatility breakout;
  - liquidity-filtered momentum.
- Added deterministic `compile_signal_frame` over in-memory panel rows for the
  registered declarative strategy types.
- Added CLI `strategy-spec validate`, `strategy-spec examples`, and
  `strategy-spec registry`.
- Updated the strategy spec and strategy plugin contracts to document that
  Phase 10 remains declarative-only and does not load or execute Python
  plugins.
- Marked `V2-AUD-STRAT-001` as `self_checked`.
- No Python strategy plugin execution, backtest runner, ledger append workflow,
  Lead Book workflow, UI, paper/live behavior, order placement, sizing,
  runtime-mode changes, candidate-pack writing, or promotion behavior was
  implemented.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_strategy_specs_phase10.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Result:

- Focused Phase 10 tests passed: 11 passed.
- Focused v2 tests passed: 74 passed.
- `compileall` for `src\tradingbotsuite\v2` passed.
- Full `compileall` for `src\tradingbotsuite` passed.
- Contract tests passed: 462 passed.
- `git diff --check` passed with LF-to-CRLF warnings only for existing
  text-file line-ending behavior.
