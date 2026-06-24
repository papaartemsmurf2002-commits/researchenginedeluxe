# Gold Research Panel Contract

Status: v2 data-venue roadmap foundation
Audit IDs: `V2-AUD-DATASRC-044`, `V2-AUD-DATASRC-048`, `V2-AUD-DATASRC-049`
Source roadmap: `docs/roadmaps/V2_HYPERLIQUID_DATA_VENUE_ROADMAP.md`

## Purpose

The gold research panel contract records the manifest boundary for joined
research panels. A gold panel can only be considered ready when it carries
archive, universe, source-registry, symbol-map, coverage-gate, coverage-report,
and feature-report references.

This contract keeps `DATA-017` research-only. Manifest and preflight helpers
are metadata-only, while row assembly and artifact materialization must use the
explicit gold-panel assembly and archive gold-layer writer surfaces documented
below. The contract does not download data, create accepted coverage evidence,
run backtests, create candidate packs, or imply paper/live/order/sizing/
runtime/promotion readiness.

## Schema

Primary code schema:

- `GoldResearchPanelFeatureRef`
- `GoldResearchPanelManifest`
- `GoldResearchPanelInputValue`
- `GoldResearchPanelRow`
- `GoldResearchPanelAssemblyResult`
- `GoldResearchPanelWriteResult`
- `GoldPanelPreflightSymbolResult`
- `GoldPanelPreflightResult`
- `GoldPanelMaterializerSymbolResult`
- `GoldPanelMaterializerResult`
- `build_gold_research_panel_manifest`
- `gold_panel_feature_refs_from_report`
- `preflight_gold_research_panels`
- `materialize_gold_research_panels`
- `assemble_gold_research_panel_rows`
- `write_gold_research_panel_artifacts`

Helper identity functions:

- `gold_research_panel_feature_refs_hash`
- `gold_research_panel_manifest_id_for`
- `gold_research_panel_row_hash`
- `gold_research_panel_rows_hash`
- `gold_research_panel_assembly_id_for`
- `gold_research_panel_write_id_for`

## Required References

Every ready `GoldResearchPanelManifest` must reference:

- `universe_snapshot_ref`
- `source_registry_ref`
- `symbol_map_ref`
- `archive_snapshot_ref`
- `coverage_gate_id`
- `coverage_report_ids`
- feature refs with `feature_report_id` and `row_manifest_hash`

The coverage gate must be a passed `DataFamilyCoverageGateResult`. The gold
panel manifest consumes that gate; it does not create accepted coverage proof by
itself.

## Feature Refs

Each `GoldResearchPanelFeatureRef` records one planned panel column and its
feature provenance:

- column name;
- data family;
- source registry and symbol-map refs;
- source IDs, venue, venue symbol, and coverage label;
- source feature report ID;
- feature row count and row manifest hash;
- coverage-flag column name;
- nullable status and blocker reasons.

Native Hyperliquid feature refs must use the `native_hyperliquid` coverage
label. External feature refs must not use that label. Empty feature refs require
blocker reasons.

## Fail-Closed Rules

`build_gold_research_panel_manifest()` returns a blocked manifest when:

- the coverage gate is not passed;
- `archive_snapshot_ref` is missing;
- feature refs are empty;
- a required coverage family has no feature ref;
- a feature ref family is not covered by the gate;
- a feature ref is blocked or empty.

Malformed metadata, such as source-registry or symbol-map mismatches between a
feature ref and coverage gate, raises validation errors.

## Gold Panel Preflight

`preflight_gold_research_panels()` maps accepted feature reconstruction reports
into deterministic `GoldResearchPanelFeatureRef` objects before panel assembly.
It accepts existing coverage reports and existing feature reconstruction
reports only; it does not fetch provider data, write rows, or create accepted
coverage evidence.

The preflight validates declared symbol membership, universe/source/symbol-map
refs, archive refs when requested, and per-symbol required-family gates. A
feature reconstruction report is usable only when it has rows, carries no
blocker reasons, has source IDs and a coverage label, matches the declared
source-registry and symbol-map refs, and targets the declared symbol. Usable
reports are converted into planned feature columns with feature report refs,
row-manifest hashes, row counts, source IDs, coverage labels, and coverage-flag
columns.

Each symbol returns a `GoldPanelPreflightSymbolResult` with the coverage
summary, generated feature refs, optional `GoldResearchPanelManifest`, and
explicit blockers. Missing coverage, failed gates, blocked feature reports,
missing required feature families, or manifest blockers stay visible in the
preflight output. Ready preflight manifests are metadata for later row-value
materialization; they are not accepted historical coverage proof, candidate
evidence, paper/live signal evidence, sizing/order instructions, runtime-mode
changes, or promotion evidence.

## Gold Panel Materializer

`materialize_gold_research_panels()` consumes a ready `GoldPanelPreflightResult`
and explicit per-symbol `GoldResearchPanelInputValue` rows. It assembles every
declared symbol first with `assemble_gold_research_panel_rows()` and only then
delegates to `write_gold_research_panel_artifacts()` for archive gold-layer
writes.

The materializer is all-or-nothing at the preflight symbol set. It writes no
gold artifacts when any declared symbol has a blocked preflight result, missing
row-value inputs, duplicate column/timestamp values, missing non-nullable row
values, unknown input symbols, missing source row hashes, or row assembly
blockers. In blocked cases it returns deterministic
`GoldPanelMaterializerSymbolResult` and `GoldPanelMaterializerResult` metadata
with explicit blocker reasons and no write refs.

Materializer write results are archive artifact refs only. They are not
accepted historical coverage proof, candidate evidence, paper/live signal
evidence, sizing/order instructions, runtime-mode changes, or promotion
evidence.

## Row Assembly

`assemble_gold_research_panel_rows()` consumes a ready
`GoldResearchPanelManifest` and timestamped `GoldResearchPanelInputValue`
objects. It assembles in-memory `GoldResearchPanelRow` objects and a
`GoldResearchPanelAssemblyResult`; it does not write gold panel files.

Each row records:

- panel ID, symbol, interval, and timestamp;
- feature column values;
- row-level coverage flags by required family;
- source row hashes;
- stable row hash.

Assembly is ready only when the panel manifest is ready, input values are
present, column/timestamp pairs are unique, and every non-nullable feature ref
has a value at the timestamp. Nullable feature refs may be absent for a
timestamp, but the row must retain the column with `null` and the row-level
family coverage flag must reflect the missing value.

## Artifact Writes

`write_gold_research_panel_artifacts()` consumes a ready
`GoldResearchPanelAssemblyResult`, writes flattened rows to the archive `gold`
layer with the existing Parquet writer, records the file in the archive file
manifest, and writes the assembly result JSON under `manifests/gold_panels/`.

The writer refuses blocked or empty assembly results before writing. It uses the
archive layout path policy and safe partition values for dataset and venue
parts. The write result records the panel parquet ref/hash/file ID, assembly
manifest ref/hash, row count, date partition, timeframe, job ID, dataset, and
venue. The write result is not accepted coverage proof, candidate evidence, or
promotion evidence.

## Forbidden

- Gold panel helpers must not write gold panel row files in these foundation
  packets except through `write_gold_research_panel_artifacts()` and the
  archive gold-layer Parquet writer.
- Gold panel manifests must not be accepted historical coverage proof.
- Missing families must not be hidden; they must be explicit missing-feature or
  coverage flags.
- External venue data must not be relabeled as Hyperliquid-native data.
- Gold panel manifests must not emit paper/live/order/sizing/runtime-mode,
  candidate-pack, or promotion claims.
