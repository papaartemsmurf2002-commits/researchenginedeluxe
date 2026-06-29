# WPR106-567 - V2 Autonomous Research Systems Layer

Status: self_checked
Owner: Codex Research Agent
Date opened: 2026-06-29

## Scope

Build the first post-PR6 autonomous research systems layer so agents can
answer whether a strategy can be tested from existing archive evidence before
collecting, materializing, or adding venues.

This packet implements archive inventory, strategy data-requirement resolution,
structured `DataGapRequest` objects, archive-first agent rules, fast-lane
execution policy metadata, artifact-light run modes with replay metadata,
batched ledger parts, a feature-store catalog for discovered materializations,
research-only collector gap templates, and benchmark/report visibility.

This packet must not collect data, add a venue by default, rewrite generated
evidence, compact existing ledgers, update Lead Book rows, alter trade-frequency
or losing-month policy, weaken PR5/PR6 math fixes, or touch live, paper,
order-placement, sizing, promotion, candidate-pack, runtime-mode, secret, or
local-state paths.

## Allowed paths

- `docs/work_packets/WPR106-567-v2-autonomous-research-systems-layer.md`
- `AGENTS.md`
- `docs/RESEARCH_AGENT_QUICKSTART.md`
- `docs/hand_offs/WPR106-566-post-pr6-implementation-goal.md`
- `src/tradingbotsuite/v2/archive_inventory/**`
- `src/tradingbotsuite/v2/feature_store/**`
- `src/tradingbotsuite/v2/collectors/templates.py`
- `src/tradingbotsuite/v2/collectors/__init__.py`
- `src/tradingbotsuite/v2/backtest_engine/artifacts.py`
- `src/tradingbotsuite/v2/backtest_engine/benchmarks.py`
- `src/tradingbotsuite/v2/backtest_engine/engine.py`
- `src/tradingbotsuite/v2/backtest_engine/fast_lane.py`
- `src/tradingbotsuite/v2/backtest_engine/jobs.py`
- `src/tradingbotsuite/v2/backtest_engine/__init__.py`
- `src/tradingbotsuite/v2/data_sources/of_style_materialization.py`
- `src/tradingbotsuite/v2/archive/manifest_store.py`
- `src/tradingbotsuite/v2/data_quality/reports.py`
- `src/tradingbotsuite/v2/ledger/schemas.py`
- `src/tradingbotsuite/v2/ledger/service.py`
- `src/tradingbotsuite/v2/cli/main.py`
- `tests/v2/test_archive_inventory_phase80.py`
- `tests/v2/test_data_requirement_resolver_phase80.py`
- `tests/v2/test_feature_store_catalog_phase80.py`
- `tests/v2/test_collector_gap_template_phase80.py`
- `tests/v2/test_backtest_benchmark_phase80.py`
- `tests/v2/test_fast_lane_audit_phase80.py`
- `tests/v2/test_backtest_engine_phase11.py`
- `tests/v2/test_of_style_materialization_phase78.py`
- `tests/v2/test_ledger_phase13.py`
- `tests/v2/archive/test_archive_phase4.py`
- `tests/v2/test_data_quality_phase6.py`
- `tests/v2/test_backtest_data_phase9.py`

## No-touch review

- No live, paper, order-placement, sizing, promotion, candidate-pack,
  runtime-mode, secret, local-state, generated-evidence, archive data, ledger
  data, or Lead Book data paths are in scope.
- Source changes are research-only and must preserve
  `research_only=true`, `observe_only=true`, `promotion_ready=false`, and the
  full false live/paper/order/sizing/runtime/candidate invariant.
- New collector templates are request templates only. They must not fetch data
  and must require `DataGapRequest` evidence before any venue probe is planned.
- Fast-lane additions must keep the Python/reference vectorized engine as the
  correctness authority.
- Artifact-light runs must remain replayable to full artifacts through the same
  spec/data/config identity.
- Ledger batching must preserve append logs, hashes, duplicate protection,
  deterministic ordering, and compaction behavior.

## Implementation plan

1. Add `archive_inventory` schemas and service to read existing archive
   manifests, coverage reports, snapshots, backtest-data manifests, central
   collection-ledger JSON, and WPR106-552 feature reports without collecting
   data.
2. Add a data-requirement resolver that validates a strategy spec, maps fields
   to archive/feature families, checks universe/window/evidence/lockbox policy,
   returns usable archive refs, required materializations, and precise
   `DataGapRequest` objects.
3. Add CLI commands for archive inventory summary/query and strategy
   testability resolution.
4. Add archive-first rules to agent docs.
5. Add fast-lane policy metadata, artifact modes, replay metadata, and optional
   benchmark timing fields without claiming speedup.
6. Batch ledger parts with configurable row limits while keeping existing read,
   export, leaderboard, and compaction contracts.
7. Add a feature-store catalog over OF/funding/OI/spread/derived feature
   reports/parts so the resolver can discover materialized feature families.
8. Add a collector adapter template that converts proven gaps into bounded
   research-only collection plans without permitting automatic venue expansion.
9. Add focused tests and run the validation baseline.

## Validation target

```powershell
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_archive_inventory_phase80.py tests\v2\test_data_requirement_resolver_phase80.py tests\v2\test_feature_store_catalog_phase80.py tests\v2\test_collector_gap_template_phase80.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_backtest_data_phase9.py tests\v2\test_strategy_specs_phase10.py tests\v2\test_backtest_engine_phase11.py tests\v2\test_ledger_phase13.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_autonomy_agent_context_phase79.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
git diff --check
```

Broaden to `tests\v2 -q` if CLI or artifact contracts change more broadly
than this packet expects.

## Completion notes

Implemented and self-checked:

- Added `tradingbotsuite.v2.archive_inventory` with archive inventory schemas,
  manifest/coverage/snapshot/collection-ledger readers, strategy data
  requirement resolution, structured `DataGapRequest` objects, fast-lane policy
  metadata, artifact-mode metadata, benchmark-observation schema, and a
  read-only `archive-inventory` CLI.
- Added `tradingbotsuite.v2.feature_store` as a read-only catalog over existing
  OF-style materialization reports and feature part refs for orderflow, BBO
  spread, L2 depth, derivatives context, and kline/derived context discovery.
  The catalog also exposes archive-backed feature projections when accepted
  archive rows already contain funding, open-interest, spread, mark/oracle, or
  OHLCV-derived fields, so the resolver uses existing bars before opening a gap.
- Added direct `archive-inventory --feature-catalog` discovery so agents can
  query feature-family/source-family/venue/symbol/instrument/timeframe/window
  filters and `--accepted-only` before opening materialization packets.
- Added research-only collector adapter templates that require a
  `DataGapRequest`, preserve the full boundary invariant, and never authorize
  collection by themselves.
- Added `collectors gap-template` so agents can convert resolver JSON or raw
  `DataGapRequest` JSON into template-only collector plans. The command emits
  boundary-preserving JSON, never fetches data, never authorizes collection, and
  skips gaps that have no suggested collector.
- Hardened collector probe safety so venue-probe templates require checked
  archive refs or coverage-report evidence carried by the `DataGapRequest`.
  Resolver-created raw-data gaps with no matching local refs now carry a
  deterministic `archive_inventory://checked/no_usable_refs` proof marker;
  hand-written bare probe gaps fail closed.
- Added `artifact_mode = full | summary | metrics_only` to backtest run config
  and manifests. Full remains default and backward compatible; summary and
  metrics-only runs write replay metadata and can be replayed to full artifacts
  only with the same spec/data/config identity.
- Added `fast-lane full-artifact-replay-plan` and
  `FullArtifactReplayPlan` so promising summary/metrics-only runs can be turned
  into full-artifact replay plans without requiring a fast-lane manifest. The
  plan preserves the source engine lane, requests `artifact_mode=full`, and
  carries expected spec/data/params/replay identity hashes.
- Added `fast-lane verify-full-artifact-replay` and
  `FullArtifactReplayVerification` so agents can verify that a written full
  replay preserves a light run's spec/data/config identity, replay-manifest
  identity fields, matching metrics, and full artifact set before treating the
  replay as audit evidence.
- Added `tradingbotsuite.v2.backtest_engine.fast_lane` and the read-only
  `fast-lane` CLI group for deterministic sampled reference audit selection,
  reference/fast parity reports, and full-artifact reference rerun plans for
  suspicious fast results. The Python/reference vectorized lane remains the
  correctness authority.
- Added opt-in benchmark capture to backtest manifests. Benchmark-enabled runs
  can record data load time from durable jobs, panel preparation, signal
  compile, reference or fast runtime, artifact write time, total run time, and
  peak traced memory. `speedup_claimed=true` is rejected unless measured
  `speedup_ratio` evidence is present.
- Added `tradingbotsuite.v2.backtest_engine.benchmarks` and
  `fast-lane benchmark-run` for archive-backed reference/fast benchmark
  reports over the same existing archive snapshot, universe snapshot, strategy
  spec, instrument set, and time window. Benchmark runs use
  `write_manifest=false` for data loads, write artifacts only under the
  requested output root, default to `artifact_mode=metrics_only`, and report
  reference runtime, fast runtime, data load time, artifact write time, memory,
  parity status, and measured speedup ratio without claiming speedup unless
  explicitly requested and supported by measured evidence.
- Added benchmark tiers (`smoke`, `panel`, `sweep`) to benchmark configs,
  reports, and the `fast-lane benchmark-run` CLI. Benchmark reports now carry a
  scope summary with required observation keys and reject mislabeled
  panel/sweep evidence when the requested instrument/window scope is too small.
- Added deterministic source-level `parallel_workers` to OF-style archive
  materialization and moved feature-row writing to a streaming path for JSONL
  and Parquet part output. Parquet part indexes record
  `writer=streaming_feature_rows_v1` while preserving chunked part output,
  source result hashes, report ordering, and research-only boundary flags.
- Added ledger part batching with configurable `max_part_rows` while preserving
  the append log, row hashes, duplicate protection, deterministic ordering,
  part-aware reads, exports, leaderboards, and compaction.
- Added batch archive/data-quality manifest append APIs for high-churn stores:
  file-manifest upserts, ingestion-run appends, and coverage-report appends now
  have batch entry points with duplicate protection and deterministic ordering.
  `write_coverage_manifest` uses the batch coverage append path.
- Tightened resolver evidence handling so non-evidence feature materializations
  cannot satisfy `accepted_research` or `reported_evidence` readiness. They
  remain usable for `sandbox_diagnostic` exploration, and missing-family reports
  no longer ask for generic bars collection when a projected bar field is not
  present in the available bars schema.
- Extended resolver reports with actionable fast-lane planning fields:
  `recommended_engine_lane`, `reference_audit_required`, and
  `fast_lane_reason`. Explicit `prefer_fast_lane` requests and large sweeps
  default to `fast_vectorized` recommendation while preserving reference-engine
  authority and audit requirements.
- Extended `DataGapRequest` evidence so failed preflights carry checked archive
  refs and checked coverage report IDs for incomplete windows or rejected
  feature materializations.
- Updated agent docs with archive-first rules: query inventory/resolver before
  collection/materialization/venue work, use existing refs when sufficient, and
  act only on bounded gap requests. Added fast-lane audit/rerun commands and
  speedup evidence rules to the quickstart.

Validation completed:

```powershell
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_archive_inventory_phase80.py tests\v2\test_data_requirement_resolver_phase80.py tests\v2\test_feature_store_catalog_phase80.py tests\v2\test_collector_gap_template_phase80.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_backtest_benchmark_phase80.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_backtest_benchmark_phase80.py tests\v2\test_fast_lane_audit_phase80.py tests\v2\test_backtest_engine_phase11.py tests\v2\test_backtest_data_phase9.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_backtest_data_phase9.py tests\v2\test_strategy_specs_phase10.py tests\v2\test_backtest_engine_phase11.py tests\v2\test_ledger_phase13.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_backtest_engine_phase11.py tests\v2\test_fast_lane_audit_phase80.py tests\v2\test_of_style_materialization_phase78.py tests\v2\test_ledger_phase13.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_workers_phase7.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_autonomy_agent_context_phase79.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
$env:PYTHONPATH='src'; py -3.11 -m tradingbotsuite.v2.cli.main archive-inventory --summary
$env:PYTHONPATH='src'; py -3.11 -m tradingbotsuite.v2.cli.main fast-lane sample-reference-audits --sample-rate 0.5 --run-id run-a --run-id run-b --run-id run-c
git diff --check
```

Final self-check on 2026-06-29:

```powershell
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_archive_inventory_phase80.py tests\v2\test_data_requirement_resolver_phase80.py tests\v2\test_feature_store_catalog_phase80.py tests\v2\test_collector_gap_template_phase80.py tests\v2\test_fast_lane_audit_phase80.py tests\v2\test_backtest_benchmark_phase80.py tests\v2\test_backtest_engine_phase11.py tests\v2\test_ledger_phase13.py tests\v2\test_of_style_materialization_phase78.py tests\v2\test_autonomy_agent_context_phase79.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
$env:PYTHONPATH='src'; py -3.11 -m tradingbotsuite.v2.cli.main archive-inventory --summary
$env:PYTHONPATH='src'; py -3.11 -m tradingbotsuite.v2.cli.main archive-inventory --missing-for-strategy configs\strategies\wpr106_556\accepted\first_passing_atlas_strategy.json --instrument-id binance:perp:BTCUSDT --start-ts 2024-01-01T00:00:00Z --end-ts 2024-02-01T00:00:00Z --artifact-mode metrics_only --prefer-fast-lane --require-reference-audit
git diff --check
```

Results: compileall passed; the touched WPR106-567 suites passed with `44`
tests; contracts passed with `463` tests; real archive-inventory CLI summary
returned `492` inventory records, `8,633,194` rows, two venues, one timeframe,
accepted research records, `research_only=true`, and no live/paper/order/sizing
runtime/candidate flags; the accepted 1h strategy-spec CLI smoke returned
`ready=false` with bounded `DataGapRequest` objects for bars and coverage only;
an in-memory six-month 1m BTCUSDT spec returned `ready=true`,
`data_gap_request_count=0`, `artifact_mode=metrics_only`,
`replayable_to_full_artifacts=true`, `reference_engine_authority=true`, and the
usable ref
`ledger://data/research/central_market_history/manifests/wpr106-544-central-market-history-exhaustive-coverage-v2-collection_ledger-ef0cfdcda209.json#binance_usdm/bars/BTCUSDT/1m`;
fast-lane CLI sampling returned a bounded deterministic sample; `git diff
--check` passed with existing LF-to-CRLF warnings only.

Continuation self-check on 2026-06-29:

```powershell
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\archive\test_archive_phase4.py tests\v2\test_data_quality_phase6.py tests\v2\test_data_requirement_resolver_phase80.py -q
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_archive_inventory_phase80.py tests\v2\test_data_requirement_resolver_phase80.py tests\v2\test_feature_store_catalog_phase80.py tests\v2\test_collector_gap_template_phase80.py tests\v2\test_fast_lane_audit_phase80.py tests\v2\test_backtest_benchmark_phase80.py tests\v2\test_backtest_engine_phase11.py tests\v2\test_ledger_phase13.py tests\v2\test_of_style_materialization_phase78.py tests\v2\test_autonomy_agent_context_phase79.py tests\v2\archive\test_archive_phase4.py tests\v2\test_data_quality_phase6.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
git diff --check
```

Results: archive/data-quality/resolver focused suites passed with `22` tests.
The new resolver checks prove that non-evidence feature materializations do not
promote accepted readiness, while sandbox diagnostics can still use them. The
new manifest checks prove batch file-manifest and coverage-report writes dedupe
same-batch duplicates and preserve deterministic ordering. Compileall passed;
the expanded touched-suite set passed with `63` tests; contracts passed with
`463` tests; `git diff --check` passed with existing LF-to-CRLF warnings only.

Second continuation self-check on 2026-06-29:

```powershell
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_data_requirement_resolver_phase80.py -q
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_archive_inventory_phase80.py tests\v2\test_data_requirement_resolver_phase80.py tests\v2\test_feature_store_catalog_phase80.py tests\v2\test_collector_gap_template_phase80.py tests\v2\test_fast_lane_audit_phase80.py tests\v2\test_backtest_benchmark_phase80.py tests\v2\test_backtest_engine_phase11.py tests\v2\test_ledger_phase13.py tests\v2\test_of_style_materialization_phase78.py tests\v2\test_autonomy_agent_context_phase79.py tests\v2\archive\test_archive_phase4.py tests\v2\test_data_quality_phase6.py -q
$env:PYTHONPATH='src'; py -3.11 -m tradingbotsuite.v2.cli.main archive-inventory --missing-for-strategy configs\strategies\wpr106_556\accepted\first_passing_atlas_strategy.json --instrument-id binance:perp:BTCUSDT --start-ts 2024-01-01T00:00:00Z --end-ts 2024-02-01T00:00:00Z --artifact-mode metrics_only --prefer-fast-lane --require-reference-audit
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
git diff --check
```

Results: resolver focused suite passed with `7` tests; compileall passed; the
expanded touched-suite set passed with `65` tests; the real CLI smoke returned
the expected `ready=false` report for the accepted 1h spec and now includes
`recommended_engine_lane=fast_vectorized`, `reference_audit_required=true`, and
`fast_lane_reason=prefer_fast_lane_requested`; contracts passed with `463`
tests; `git diff --check` passed with existing LF-to-CRLF warnings only.

Third continuation self-check on 2026-06-29:

```powershell
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_feature_store_catalog_phase80.py -q
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_archive_inventory_phase80.py tests\v2\test_data_requirement_resolver_phase80.py tests\v2\test_feature_store_catalog_phase80.py tests\v2\test_collector_gap_template_phase80.py tests\v2\test_fast_lane_audit_phase80.py tests\v2\test_backtest_benchmark_phase80.py tests\v2\test_backtest_engine_phase11.py tests\v2\test_ledger_phase13.py tests\v2\test_of_style_materialization_phase78.py tests\v2\test_autonomy_agent_context_phase79.py tests\v2\archive\test_archive_phase4.py tests\v2\test_data_quality_phase6.py -q
$env:PYTHONPATH='src'; py -3.11 -m tradingbotsuite.v2.cli.main archive-inventory --feature-catalog --feature-family funding --accepted-only --timeframe 1m
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
git diff --check
```

Results: feature-store focused tests passed with `4` tests, including direct
CLI filtering; compileall passed; the expanded touched-suite set passed with
`67` tests; the real feature-catalog CLI smoke returned an empty accepted 1m
funding set for the local archive rather than implying missing docs or
performing materialization; contracts passed with `463` tests; `git diff
--check` passed with existing LF-to-CRLF warnings only.

Fourth continuation self-check on 2026-06-29:

```powershell
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_collector_gap_template_phase80.py -q
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_archive_inventory_phase80.py tests\v2\test_data_requirement_resolver_phase80.py tests\v2\test_feature_store_catalog_phase80.py tests\v2\test_collector_gap_template_phase80.py tests\v2\test_fast_lane_audit_phase80.py tests\v2\test_backtest_benchmark_phase80.py tests\v2\test_backtest_engine_phase11.py tests\v2\test_ledger_phase13.py tests\v2\test_of_style_materialization_phase78.py tests\v2\test_autonomy_agent_context_phase79.py tests\v2\archive\test_archive_phase4.py tests\v2\test_data_quality_phase6.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
git diff --check
```

Results: collector gap-template focused tests passed with `3` tests, including
CLI conversion from resolver-style JSON; compileall passed; the expanded
touched-suite set passed with `68` tests; contracts passed with `463` tests;
`git diff --check` passed with existing LF-to-CRLF warnings only.

Fifth continuation self-check on 2026-06-29:

```powershell
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_fast_lane_audit_phase80.py -q
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_archive_inventory_phase80.py tests\v2\test_data_requirement_resolver_phase80.py tests\v2\test_feature_store_catalog_phase80.py tests\v2\test_collector_gap_template_phase80.py tests\v2\test_fast_lane_audit_phase80.py tests\v2\test_backtest_benchmark_phase80.py tests\v2\test_backtest_engine_phase11.py tests\v2\test_ledger_phase13.py tests\v2\test_of_style_materialization_phase78.py tests\v2\test_autonomy_agent_context_phase79.py tests\v2\archive\test_archive_phase4.py tests\v2\test_data_quality_phase6.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
git diff --check
```

Results: fast-lane focused tests passed with `7` tests, including
full-artifact replay planning for metrics-only runs and fail-closed rejection
for already-full runs; compileall passed; the expanded touched-suite set passed
with `71` tests; contracts passed with `463` tests; `git diff --check` passed
with existing LF-to-CRLF warnings only.

Sixth continuation self-check on 2026-06-29:

```powershell
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_backtest_benchmark_phase80.py -q
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_backtest_benchmark_phase80.py tests\v2\test_fast_lane_audit_phase80.py tests\v2\test_backtest_engine_phase11.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
```

Results: benchmark focused tests passed with `3` tests, including benchmark
tier scope metadata and fail-closed panel/sweep tier validation; compileall
passed; neighboring benchmark/fast-lane/backtest-engine suites passed with
`20` tests; contracts passed with `463` tests.

Seventh continuation self-check on 2026-06-29:

```powershell
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_backtest_benchmark_phase80.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_backtest_benchmark_phase80.py tests\v2\test_backtest_data_phase9.py tests\v2\test_backtest_engine_phase11.py tests\v2\test_fast_lane_audit_phase80.py -q
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
git diff --check
```

Results: benchmark focused tests passed with `4` tests, including an
archive-backed two-instrument `benchmark_tier=panel` run through both
reference and fast lanes with `artifact_mode=metrics_only`; neighboring
benchmark/data/engine/fast-lane suites passed with `32` tests; compileall
passed; contracts passed with `463` tests; `git diff --check` passed with
existing LF-to-CRLF warnings only.

Eighth continuation self-check on 2026-06-29:

```powershell
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_fast_lane_audit_phase80.py -q
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_fast_lane_audit_phase80.py tests\v2\test_backtest_engine_phase11.py tests\v2\test_backtest_benchmark_phase80.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
git diff --check
```

Results: fast-lane focused tests passed with `10` tests, including
full-artifact replay verification pass/fail behavior and CLI verification for
a metrics-only source run replayed to full artifacts; compileall passed;
neighboring fast-lane/backtest-engine/benchmark suites passed with `24` tests;
contracts passed with `463` tests; `git diff --check` passed with existing
LF-to-CRLF warnings only.

Ninth continuation self-check on 2026-06-29:

```powershell
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_of_style_materialization_phase78.py -q
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_of_style_materialization_phase78.py tests\v2\test_feature_store_catalog_phase80.py tests\v2\test_data_requirement_resolver_phase80.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
git diff --check
```

Results: OF materialization focused tests passed with `3` tests, including the
streaming Parquet part-index writer marker and preserved source/result counts;
compileall passed; neighboring OF/feature-store/resolver suites passed with
`14` tests; contracts passed with `463` tests; `git diff --check` passed with
existing LF-to-CRLF warnings only.

Tenth continuation self-check on 2026-06-29:

```powershell
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_collector_gap_template_phase80.py tests\v2\test_data_requirement_resolver_phase80.py -q
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_archive_inventory_phase80.py tests\v2\test_data_requirement_resolver_phase80.py tests\v2\test_collector_gap_template_phase80.py tests\v2\test_feature_store_catalog_phase80.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
git diff --check
```

Results: collector/resolver focused tests passed with `11` tests, including
template rejection for bare venue-probe gaps and resolver proof markers for
raw-data gaps with no usable archive refs; compileall passed; adjacent
archive-inventory/resolver/collector/feature-store suites passed with `16`
tests; contracts passed with `463` tests; `git diff --check` passed with
existing LF-to-CRLF warnings only.

Eleventh continuation self-check on 2026-06-29:

```powershell
py -3.11 -m pytest tests\v2\test_ledger_phase13.py -q
py -3.11 -m pytest tests\v2\test_workers_phase7.py -k ledger -q
py -3.11 -m pytest tests\v2\test_validation_phase14.py tests\v2\test_autonomous_readiness_audit_phase29.py -q
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
git diff --check
```

Results: ledger focused tests passed with `18` tests, including fail-closed
rejection for corrupt part index mappings, part file hash drift, compacted
file hash drift, and CLI compaction; ledger worker subset passed with `4`
tests and `58` deselected; validation/readiness neighboring suites passed with
`17` tests; compileall passed; contracts passed with `463` tests;
`git diff --check` passed with existing LF-to-CRLF warnings only.

Twelfth continuation self-check on 2026-06-29:

```powershell
py -3.11 -m pytest tests\v2\test_of_style_materialization_phase78.py -q
py -3.11 -m pytest tests\v2\test_feature_store_catalog_phase80.py tests\v2\test_data_requirement_resolver_phase80.py -q
py -3.11 -m compileall -q src\tradingbotsuite
py -3.11 -m pytest tests\v2\test_of_style_materialization_phase78.py tests\v2\test_feature_store_catalog_phase80.py tests\v2\test_data_requirement_resolver_phase80.py tests\v2\test_collector_gap_template_phase80.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
git diff --check
```

Results: OF materialization focused tests passed with `4` tests, including
streaming sorted-bucket aggregation for monotonic trade buckets and full-sort
fallback for non-monotonic bucket order; adjacent feature-store/resolver tests
passed with `11` tests; compileall passed; the broader
OF/feature-store/resolver/collector touched slice passed with `19` tests;
contracts passed with `463` tests; `git diff --check` passed with existing
LF-to-CRLF warnings only.

Thirteenth continuation self-check on 2026-06-29:

```powershell
py -3.11 -m pytest tests\v2\test_data_requirement_resolver_phase80.py -q
py -3.11 -m pytest tests\v2\test_archive_inventory_phase80.py tests\v2\test_data_requirement_resolver_phase80.py tests\v2\test_feature_store_catalog_phase80.py tests\v2\test_collector_gap_template_phase80.py -q
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m tradingbotsuite.v2.cli.main archive-inventory --missing-for-strategy configs\strategies\wpr106_556\accepted\first_passing_atlas_strategy.json --instrument-id binance:perp:BTCUSDT --start-ts 2024-01-01T00:00:00Z --end-ts 2024-02-01T00:00:00Z --artifact-mode metrics_only --prefer-fast-lane --require-reference-audit
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
git diff --check
```

Results: resolver focused tests passed with `7` tests, including archive-first
partial-ref reporting for missing feature families and rejection of
non-evidence feature refs as accepted usable refs; adjacent
archive-inventory/resolver/feature-store/collector tests passed with `16`
tests; compileall passed; the real CLI smoke returned `ready=false` with
bounded bars/coverage gap requests for the one-month accepted spec and no
usable refs for that local request; contracts passed with `463` tests;
`git diff --check` passed with existing LF-to-CRLF warnings only.

Fourteenth continuation self-check on 2026-06-29:

```powershell
py -3.11 -m pytest tests\v2\test_fast_lane_audit_phase80.py -q
py -3.11 -m pytest tests\v2\test_backtest_engine_phase11.py -q
py -3.11 -m pytest tests\v2\test_backtest_benchmark_phase80.py -q
py -3.11 -m compileall -q src\tradingbotsuite
py -3.11 -m pytest tests\v2\test_fast_lane_audit_phase80.py tests\v2\test_backtest_benchmark_phase80.py tests\v2\test_backtest_engine_phase11.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
git diff --check
```

Results: fast-lane focused tests passed with `12` tests, including rejection
of speedup claims that lack data-load, artifact-write, and memory observations
and acceptance when complete measured evidence is present; backtest-engine
tests passed with `11` tests, including run-config rejection for speedup claims
with only a ratio; benchmark tests passed with `4` tests; compileall passed;
the combined fast-lane/benchmark/backtest-engine slice passed with `27` tests;
contracts passed with `463` tests; `git diff --check` passed with existing
LF-to-CRLF warnings only.

Fifteenth continuation self-check on 2026-06-29:

```powershell
py -3.11 -m pytest tests\v2\test_archive_inventory_phase80.py -q
py -3.11 -m pytest tests\v2\test_archive_inventory_phase80.py tests\v2\test_data_requirement_resolver_phase80.py tests\v2\test_feature_store_catalog_phase80.py tests\v2\test_collector_gap_template_phase80.py -q
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
git diff --check
```

Results: archive-inventory focused tests passed with `2` tests, including
service and CLI filtering by evidence scope, accepted-evidence allowance, and
coverage report ID; adjacent archive-inventory/resolver/feature-store/collector
tests passed with `17` tests; compileall passed; contracts passed with `463`
tests; `git diff --check` passed with existing LF-to-CRLF warnings only.

Sixteenth continuation self-check on 2026-06-29:

```powershell
py -3.11 -m pytest tests\v2\test_archive_inventory_phase80.py tests\v2\test_feature_store_catalog_phase80.py -q
py -3.11 -m compileall -q src\tradingbotsuite
py -3.11 -m pytest tests\v2\test_archive_inventory_phase80.py tests\v2\test_data_requirement_resolver_phase80.py tests\v2\test_feature_store_catalog_phase80.py tests\v2\test_collector_gap_template_phase80.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
git diff --check
```

Results: archive-inventory and feature-store focused tests passed with `8`
tests, including repeated `--instrument-id` CLI filtering for both inventory
records and feature-catalog entries; compileall passed; adjacent
archive-inventory/resolver/feature-store/collector tests passed with `19`
tests; contracts passed with `463` tests; `git diff --check` passed with
existing LF-to-CRLF warnings only.

Seventeenth continuation self-check on 2026-06-29:

```powershell
py -3.11 -m pytest tests\v2\test_collector_gap_template_phase80.py -q
py -3.11 -m pytest tests\v2\test_archive_inventory_phase80.py tests\v2\test_data_requirement_resolver_phase80.py tests\v2\test_feature_store_catalog_phase80.py tests\v2\test_collector_gap_template_phase80.py -q
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
git diff --check
```

Results: collector template focused tests passed with `6` tests, including
explicit bounded venue lists, `venue_expansion_allowed=false`, and rejection
of both proactive venue expansion and probe venues outside the DataGapRequest
venue preference; adjacent archive-inventory/resolver/feature-store/collector
tests passed with `21` tests; compileall passed; contracts passed with `463`
tests; `git diff --check` passed with existing LF-to-CRLF warnings only.

Known remaining follow-up outside this packet's completed increment:

- Run larger benchmark tiers over full local real archive panels before any
  broad platform speedup claim. The archive-backed benchmark command, tier
  labels, and fixture-backed two-instrument panel proof now exist, but no
  repository-level speedup claim has been made.
- Continue expanding fast-lane parity coverage as new strategy families are
  introduced.
- Continue improving OF-style feature aggregation for very large non-monotonic
  trade/book sources. Monotonic trade, BBO, and depth inputs now use streaming
  sorted-bucket aggregation with one active bucket at a time, while
  non-monotonic sources preserve correctness through the existing full-sort
  fallback.
