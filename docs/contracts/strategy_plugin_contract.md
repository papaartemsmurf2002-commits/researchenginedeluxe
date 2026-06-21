# V2 Strategy Plugin Contract

Status: v2 contract foundation; metadata-only legacy wrapper added, plugin execution still forbidden
Audit IDs: `V2-AUD-STRAT-002`, `V2-AUD-LEGACY-010`

## Purpose

Python plugins are a later narrow extension point after declarative specs.
Phase 10 implements declarative specs only; plugin execution remains forbidden
until a later scoped packet adds the protocol, sandbox/audit checks, and tests.

## Initial Schema Names

- `StrategyPluginProtocol`
- `StrategyPluginManifest`
- `StrategyPluginRegistryManifest`

## Required Rules

- Plugins declare required inputs, output columns, parameter schema, and
  research-only boundary.
- Plugins cannot access network, secrets, live runtime, order adapters, sizing,
  account state, or arbitrary filesystem paths.
- Plugin output must be deterministic for a given input panel and spec hash.
- Any future plugin manifest must fail closed when it declares network,
  credentials, arbitrary file reads, live/order/sizing/runtime access, or
  undeclared inputs.
- Phase 18 may wrap audited legacy strategy parameter metadata into
  `StrategyPluginManifest` records when the legacy subsystem classification is
  `wrap_into_v2`.
- Metadata-only manifests must record legacy source path, source SHA-256,
  metadata hash, default parameters, parameter space, holding-window overrides,
  signal-density controls, failure modes, classification, and audit IDs.
- Metadata-only manifests must keep `plugin_execution_allowed: false` and
  include blocker reasons explaining that execution is disabled until a later
  scoped packet.
- Unknown legacy strategy IDs must fail closed instead of creating empty
  metadata manifests.

## Forbidden

- Unreviewed Python strategy execution by agents.
- Promotion or live-signal claims.
- Loading or executing Python strategy plugins through the Phase 10
  declarative-spec lane.
- Importing or instantiating legacy strategy classes as part of the Phase 18
  metadata wrapper.
- Treating metadata manifests as candidate evidence, candidate-pack
  eligibility, sizing instructions, paper/live signals, runtime-mode changes,
  or promotion evidence.
