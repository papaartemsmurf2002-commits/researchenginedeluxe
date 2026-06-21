# WPR106-409 V2 Legacy Strategy Plugin Metadata Wrapper

Status: closed
Owner: Codex Research Agent
Created: 2026-06-21

## Objective

Implement a narrow Phase 18 legacy migration chunk by wrapping the audited
legacy `strategy_plugins` subsystem's parameter metadata into v2
`StrategyPluginManifest` records. This packet preserves useful legacy strategy
metadata for future review while keeping Python plugin execution disabled.

This packet does not execute legacy strategy plugins, load arbitrary Python
plugins, run backtests, write candidate packs, place orders, produce paper/live
signals, emit sizing instructions, change runtime mode, or create promotion
evidence.

## Audit IDs

- `V2-AUD-LEGACY-010`
- `V2-AUD-STRAT-002`

## Dependencies

- Phase 3 legacy subsystem classification.
- Phase 10 declarative strategy lane.
- `docs/contracts/strategy_plugin_contract.md`
- `docs/V2_LEGACY_SUBSYSTEM_AUDIT.md`

## Selected Legacy Subsystem

- Subsystem: `strategy_plugins`
- Classification: `wrap_into_v2`
- Source record: `docs/V2_LEGACY_SUBSYSTEM_AUDIT.md`
- Useful behavior preserved: strategy IDs, default parameters, parameter
  spaces, holding-window overrides, additional allowed values, signal-density
  controls, and known failure modes.

## Allowed Paths

- `docs/contracts/strategy_plugin_contract.md`
- `docs/V2_LEGACY_SUBSYSTEM_AUDIT.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `src/tradingbotsuite/v2/strategy_plugins/**`
- `tests/v2/**`
- `docs/work_packets/WPR106-409-v2-legacy-strategy-plugin-metadata-wrapper.md`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Constraints

- Preserve research-only, observe-only, non-promotable semantics.
- Import legacy metadata only; do not import or instantiate legacy strategy
  plugin classes.
- Strategy plugin execution remains forbidden until a later scoped packet adds
  sandbox/audit checks and execution tests.
- Any manifest declaring network, secrets, arbitrary filesystem, live runtime,
  order, sizing, runtime-mode, candidate-pack, or promotion behavior must fail
  closed.

## Acceptance Criteria

- A known legacy strategy ID can be wrapped into a v2 `StrategyPluginManifest`
  with source hash and classification evidence.
- Useful legacy parameter metadata is preserved in the v2 manifest.
- Unknown legacy strategy IDs fail closed instead of silently creating empty
  manifests.
- Boundary tests prove execution and live/order/sizing/runtime flags are
  rejected.
- A manifest file can be written as v2 research-only evidence without enabling
  plugin execution.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_legacy_strategy_plugin_phase18.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_contract_docs.py -q
git diff --check
```

No broader non-v2 tests are required unless shared implementation files outside
the v2 shell are changed.

## Stop Conditions

- Legacy plugin execution becomes necessary.
- A live/runtime/order/sizing no-touch path must be modified.
- Metadata import requires importing legacy strategy registry classes or
  instantiated plugin objects.
- The wrapper cannot preserve boundary flags without weakening the v2 strategy
  plugin contract.

## Completion Notes

Closed on 2026-06-21.

- Added metadata-only v2 strategy plugin manifests:
  - `StrategyPluginProtocol`;
  - `StrategyPluginManifest`;
  - `StrategyPluginRegistryManifest`.
- Wrapped audited legacy `strategy_plugins` metadata from
  `src/tradingbotsuite/strategies/parameters.py` without importing legacy
  strategy registry classes or instantiated plugin objects.
- Preserved useful legacy metadata:
  - strategy IDs;
  - default parameters;
  - parameter spaces;
  - holding-window overrides;
  - additional allowed parameter values;
  - signal-density controls;
  - failure modes;
  - source path and source SHA-256;
  - legacy metadata hash.
- Added manifest writers for metadata evidence files.
- Unknown legacy strategy IDs now fail closed.
- Strategy plugin manifests reject execution, network, secrets, arbitrary file,
  live runtime, order, sizing, runtime-mode, candidate-pack, candidate-evidence,
  paper/live, and promotion flags.
- Updated the strategy plugin contract, legacy subsystem audit note, and audit
  index.
- No Python plugin execution, arbitrary plugin loading, backtesting,
  candidate-pack writing, live/paper signal, sizing instruction, order
  placement, runtime-mode change, or promotion behavior was implemented.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_legacy_strategy_plugin_phase18.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_contract_docs.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Result:

- Focused Phase 18 tests passed: 5 passed.
- Full v2 tests passed: 131 passed.
- `compileall` for `src\tradingbotsuite\v2` passed.
- Contract-doc smoke passed: 2 passed.
- Full `compileall` for `src\tradingbotsuite` passed.
- Contract tests passed: 462 passed.
- `git diff --check` passed with LF-to-CRLF warnings only for existing
  text-file line-ending behavior.
