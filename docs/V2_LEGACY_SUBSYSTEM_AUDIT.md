# V2 Legacy Subsystem Audit

Status: Phase 3 legacy classification
Audit ID: `V2-AUD-LEGACY-001`
Source: `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md`

This audit classifies legacy and transition subsystems before v2 migration.
It does not authorize reuse by itself. Any later reuse or wrapping must open a
scoped packet, cite the relevant record here, and satisfy the v2 contracts.

## Summary

| Subsystem | Recommended action | V2 usefulness | Status |
| --- | --- | --- | --- |
| `strict_research_cycle` | `wrap_into_v2` | high | accepted |
| `candidate_pack_gates` | `reuse_after_fix` | high | accepted |
| `rapid_sandbox` | `wrap_into_v2` | high | accepted |
| `old_high_return_outputs` | `freeze_drawer` | medium | accepted |
| `rejected_rows` | `freeze_drawer` | high | accepted |
| `strategy_plugins` | `wrap_into_v2` | high | accepted |
| `feature_builders` | `wrap_into_v2` | high | accepted |
| `existing_backtest_engines` | `wrap_into_v2` | high | accepted |
| `legacy_gui` | `freeze_drawer` | medium | accepted |
| `live_runtime_adjacent_code` | `no_touch_without_scope` | low | accepted |
| `old_tradingbot_package` | `move_to_legacy_area` | medium | accepted |

## Records

### strict_research_cycle

```yaml
subsystem: strict_research_cycle
files_reviewed:
  - src/tradingbotsuite/research_cycle/**
  - configs/research/**
  - tests/contracts/test_research_cycle_contract.py
  - tests/historical/**
current_purpose: historical-cycle orchestration, feature building, candidate generation, backtests, rankings, and gate evidence
v2_usefulness: high
risks_found:
  - tightly coupled to legacy fixture/config contracts
  - BTC/ETH-era assumptions may appear in checked configs
  - broad changes can corrupt provenance, split, cost, and gate evidence
recommended_action: wrap_into_v2
required_fixes:
  - expose v2 data-service inputs only after backtest_data_service contract exists
  - preserve rejection and blocker evidence
  - keep legacy configs as reference/smoke material, not default v2 universe
audit_id: V2-AUD-LEGACY-001
final_status: accepted
```

### candidate_pack_gates

```yaml
subsystem: candidate_pack_gates
files_reviewed:
  - src/tradingbotsuite/research_artifacts/**
  - tests/research_artifacts/test_candidate_pack.py
  - tests/live/**
current_purpose: fail-closed evidence and live-boundary gate for candidate-pack artifacts
v2_usefulness: high
risks_found:
  - candidate-pack wording can imply readiness if reused carelessly
  - v2 leads must remain non-promotable and not candidate evidence
recommended_action: reuse_after_fix
required_fixes:
  - keep candidate-pack writes out of v2 until a later explicit validation scope
  - reuse rejection logic as guardrails, not as v2 promotion path
  - align terms with Lead Book and final hard-test survivor semantics
audit_id: V2-AUD-LEGACY-001
final_status: accepted
```

### rapid_sandbox

```yaml
subsystem: rapid_sandbox
files_reviewed:
  - src/tradingbotsuite/research_sandbox/**
  - configs/sandbox/**
  - tests/research_sandbox/**
  - RAPID_STRATEGY_SANDBOX_AUDIT.md
current_purpose: fast research-only strategy triage and artifact cataloging
v2_usefulness: high
risks_found:
  - sandbox rankings can be mistaken for accepted evidence
  - local archive descriptors need v2 archive/data-service wrapping
recommended_action: wrap_into_v2
required_fixes:
  - keep sandbox outputs non-promotable and candidate_evidence false
  - route future data through v2 archive snapshots when available
  - feed promising rows into Lead Book only after human inspection fields exist
audit_id: V2-AUD-LEGACY-001
final_status: accepted
```

### old_high_return_outputs

```yaml
subsystem: old_high_return_outputs
files_reviewed:
  - data/research/wpr106_*/**
  - data/research/v2-btc-*/**
  - docs/stage_reports/STAGE_R106_*.md
  - docs/V2_ADOPTION_CONVERSATION_REPO_PACKAGE_2026_06_20.md
current_purpose: historical research artifacts and empirical clues
v2_usefulness: medium
risks_found:
  - high-return rows can be overfit, concentrated, stale, or fixture-specific
  - generated data must not be rewritten by migration
recommended_action: freeze_drawer
required_fixes:
  - preserve artifacts in place
  - convert only selected rows to Lead Book sources with source refs and blockers
  - require deep validation before final hard-test consideration
audit_id: V2-AUD-LEGACY-001
final_status: accepted
```

### rejected_rows

```yaml
subsystem: rejected_rows
files_reviewed:
  - data/research/discovery_runs/**
  - data/research/historical_cycles/**
  - data/research/operator_runs/**
  - docs/KNOWN_ISSUES.md
current_purpose: negative evidence, blocker reasons, failed gates, and falsification history
v2_usefulness: high
risks_found:
  - rejection evidence can be lost if treated as scratch output
  - old blocker names may need mapping to v2 contracts
recommended_action: freeze_drawer
required_fixes:
  - preserve old rows and manifests
  - map useful rejection modes into validation and Lead Book blocker vocabularies
  - use as negative-control/falsification sources, not candidate evidence
audit_id: V2-AUD-LEGACY-001
final_status: accepted
```

### strategy_plugins

```yaml
subsystem: strategy_plugins
files_reviewed:
  - src/tradingbotsuite/strategies/**
  - configs/strategies/**
  - tests/contracts/test_strategy_contracts.py
current_purpose: legacy strategy registry, plugin contracts, parameter spaces, and signal validation
v2_usefulness: high
risks_found:
  - Python plugins are not the default v2 strategy interface
  - plugin metadata may reflect legacy feature/backtest assumptions
recommended_action: wrap_into_v2
required_fixes:
  - implement declarative strategy specs first
  - wrap useful plugins behind `strategy_plugin_contract.md`
  - forbid network, secrets, live/order/sizing/runtime access
audit_id: V2-AUD-LEGACY-001
final_status: accepted
```

Phase 18 migration note:

- WPR106-409 wraps legacy `src/tradingbotsuite/strategies/parameters.py`
  metadata into v2 `StrategyPluginManifest` records under audit
  `V2-AUD-LEGACY-010`.
- The wrapper preserves strategy IDs, defaults, parameter spaces,
  holding-window overrides, additional allowed values, signal-density controls,
  failure modes, source path, source SHA-256, and metadata hash.
- The wrapper does not import or instantiate legacy strategy classes and does
  not enable plugin execution.
- The emitted manifests remain research-only, observe-only, non-promotable,
  candidate-evidence false, candidate-pack ineligible, non-live, no-order,
  no-sizing, and no-runtime-mode-change.

### feature_builders

```yaml
subsystem: feature_builders
files_reviewed:
  - src/tradingbotsuite/features/**
  - configs/features/**
  - tests/contracts/test_feature_contracts.py
  - tests/features/**
current_purpose: completed-bar feature materialization, context joins, cache identity, and feature presets
v2_usefulness: high
risks_found:
  - point-in-time semantics must not be weakened
  - cache identity must incorporate v2 archive/universe/feature snapshot IDs
recommended_action: wrap_into_v2
required_fixes:
  - adapt only after v2 archive and backtest data service contracts are enforced
  - keep missing context explicit
  - preserve train-only preprocessing boundaries
audit_id: V2-AUD-LEGACY-001
final_status: accepted
```

### existing_backtest_engines

```yaml
subsystem: existing_backtest_engines
files_reviewed:
  - src/tradingbotsuite/backtesting/**
  - tests/contracts/test_backtest_contracts.py
  - tests/backtesting/**
current_purpose: reference/vector/cuda research backtesting, execution simulation, exits, splits, and metrics
v2_usefulness: high
risks_found:
  - v2 requires shared vectorized/event-driven artifacts and stronger data-service gating
  - optimistic fill assumptions would corrupt v2 evidence
recommended_action: wrap_into_v2
required_fixes:
  - use v2 backtest data service only
  - emit `RunManifest`-compatible artifacts
  - keep cost/funding/slippage/impact metadata explicit
audit_id: V2-AUD-LEGACY-001
final_status: accepted
```

### legacy_gui

```yaml
subsystem: legacy_gui
files_reviewed:
  - src/tradingbotsuite/web/**
  - src/tradingbotsuite/ui/**
  - docs/OPERATOR_GUIDE.md
  - docs/OPERATOR_QUICKSTART.md
current_purpose: existing operator/research visibility and command surface
v2_usefulness: medium
risks_found:
  - legacy GUI can define behavior prematurely if reused as the v2 source of truth
  - UI process must not run collectors or long backtests
recommended_action: freeze_drawer
required_fixes:
  - keep available as legacy/operator surface
  - do not rebuild v2 UI before data/archive/universe/ledger/Lead Book foundation
  - future v2 UI must be read/queue oriented and worker-backed
audit_id: V2-AUD-LEGACY-001
final_status: accepted
```

### live_runtime_adjacent_code

```yaml
subsystem: live_runtime_adjacent_code
files_reviewed:
  - src/tradingbotsuite/live/**
  - src/tradingbotsuite/promotion/**
  - src/tradingbotsuite/runtime.py
  - src/tradingbotsuite/adapters/execution.py
  - run_live_smoke.py
  - run_manual.py
current_purpose: guarded live/runtime/promotion-adjacent legacy surfaces and boundary tests
v2_usefulness: low
risks_found:
  - any accidental v2 import can violate research-only boundary
  - secrets/account/order paths are out of scope for v2
recommended_action: no_touch_without_scope
required_fixes:
  - keep forbidden import tests active
  - do not modify without explicit human-scoped live/boundary packet
  - never route v2 research artifacts into live runtime
audit_id: V2-AUD-LEGACY-001
final_status: accepted
```

### old_tradingbot_package

```yaml
subsystem: old_tradingbot_package
files_reviewed:
  - src/tradingbot/**
  - examples/**
  - tests/test_strategy_flow.py
current_purpose: legacy Lorentzian/classic tradingbot compatibility package and examples
v2_usefulness: medium
risks_found:
  - old CLI/backtest defaults are not v2 data-service or universe aware
  - legacy examples can look like current product path
recommended_action: move_to_legacy_area
required_fixes:
  - keep compatibility only where tests require it
  - avoid using it as v2 core
  - mark future references as legacy or wrap selected ideas through Lead Book
audit_id: V2-AUD-LEGACY-001
final_status: accepted
```

## Migration Rule

No legacy subsystem may be used as a v2 implementation dependency unless a
future packet cites its record above and either:

- wraps it behind the relevant v2 contract;
- classifies it as preserved evidence or negative-control source;
- or explicitly scopes a no-touch exception with validation.
