# V2 Autonomous Readiness Contract

Status: v2 manager-gate contract
Audit IDs: `V2-AUD-COMPLETE-002`, `V2-AUD-COMPLETE-003`, `V2-AUD-AUDIT-006`, `V2-AUD-AUDIT-007`

## Purpose

The autonomous readiness gate turns the execution brief's final manager
checklist into a deterministic JSON blocker report. It is a repo-completion
gate for supplied evidence, not a strategy-quality certificate, accepted
research result, candidate pack, paper/live signal, order instruction, sizing
instruction, runtime-mode change, or promotion artifact.

## Schema Names

- `AutonomousReadinessEvidence`
- `ReadinessEvidenceItem`
- `AutonomousReadinessReport`
- `ReadinessCheckSummary`
- `AutonomousReadinessStatus`

## Required Evidence Inputs

- One readiness evidence JSON object using
  `autonomous_readiness_evidence_v1`.
- Exactly one evidence item for each required checklist key. Missing,
  duplicate, unexpected, failed, or reference-less items must block readiness.
- Optional evidence item paths may be supplied; if supplied, the path must
  exist.
- The data evidence checklist must include the current free-venue authority
  keys: `data.free_venue_authority_documented`,
  `data.project_bar_coverage_authoritative`, and
  `data.of_style_raw_archive_authoritative`. These keys are satisfied by
  manifest-backed strict-free/no-paid data evidence, not by requester-pays or
  otherwise uncollectable native Hyperliquid archives.
- A bounded-cycle execution manifest path proving the operational loop ran
  through universe, archive, coverage, strategy queue, backtest-data load,
  backtest, validation, ledger, Lead Book, and final audit job kinds.
- A final durable audit/blocker report path. The final audit report must parse
  as `AuditBlockerReport`, have `status=pass`, have no blockers, and keep
  `accepted_research_ready=false`.
- The final audit report must declare and contain current loop evidence for:
  `universe_snapshot_id=`, `archive_snapshot_id=`, `coverage_report_id`,
  `strategy_queue_manifest_id=`, `accepted_spec_path=`,
  `accepted_spec_sha256=`, `strategy_spec_hash=`,
  `backtest_data_manifest_path=`, `backtest_data_manifest_sha256=`,
  `data_manifest_id=`, `data_manifest_hash=`, `run_manifest_path=`,
  `validation_manifest_path=`, `validation_manifest_id=`, `ledger_path=`,
  and `lead_book_path=`.
- A canonical append-only ledger path containing at least one row.
- A canonical Lead Book path containing at least one row.
- Open P0 and P1 counts. Any open P0 or P1 count blocks autonomous readiness.

## Free-Venue Data Authority Lane

WPR106-533 records an operator-approved multi-venue/proxy research lane for
strict-free market data. WPR106-551 makes that lane authoritative for current
data readiness: the repo works with the no-paid venue data it can actually
collect, validate, and reproduce. Non-paid Binance, Bybit, and Hyperliquid
data may be treated as comparable research inputs, with Hyperliquid preferred
when it has usable coverage and passes cross-venue quality checks.

Free-venue data evidence must preserve per-venue provenance, source access
mode, coverage ratios, quality/drop decisions, and the full research-only
boundary invariant. Hyperliquid may be dropped when it is missing, below
coverage floors, unavailable under strict-free constraints, or materially
divergent from comparable no-paid providers. Binance/Bybit rows must not be
relabeled as Hyperliquid-native rows, but they may satisfy the current
free-venue data evidence keys when their manifests and validation reports pass.

WPR106-534 centralizes this lane under
`data/research/central_market_history/**`. Centralized market-history data
readiness may pass when at least one no-paid provider/timeframe group has
valid provenance, schema, timestamp, monotonicity, nonempty rows, and coverage
or quality evidence, even if Hyperliquid history is missing for another
symbol/timeframe. OHLCV provider pairs within five percent after
symbol/timeframe/UTC normalization are equivalent research data. Larger OHLCV
divergence must retain all providers with provider-specific quality status.
Trade, orderflow, and book-style data are not required to pass strict
cross-provider equality; they require provenance, schema validity, timestamp
sanity, monotonicity, nonempty rows, and coverage metrics. This central data
readiness remains separate from autonomous strategy readiness and must not be
reported as a passing manager readiness report by itself.

WPR106-543 updates the central store to a 300 GiB local budget cap and adds
bounded parallel official no-paid archive collection with atomic `.part`
downloads, source validation, source-discovery reports, quality reports, and
progress telemetry. For this central market-history data-readiness lane, the
prior strict Hyperliquid-only interpretation is out of scope and must not be
used by future agents as a blocker when valid comparable no-paid provider data
exists.

WPR106-544 adds the central collection ledger as the required truth source for
2024+ market-history availability decisions:
`data/research/central_market_history/manifests/wpr106-544-central-market-history-exhaustive-coverage-v2-collection_ledger-ef0cfdcda209.json`.
The ledger distinguishes complete normalized, raw-collected but not normalized,
partial, unavailable, budget-blocked, unsupported, and operator-gated data by
provider/family/symbol/window. Backtest-data loading and strategy evaluation
must not infer coverage from raw files alone. If a required bar/orderflow/book
family is not marked `backtest_usable=true`, the caller must either restrict
the run to explicit manifest-covered partial windows or call off the strategy
path for insufficient data. Hyperliquid official historical S3 orderflow/book
history remains recorded as requester-pays/operator-gated provenance, but it is
out of scope for strict-free data readiness and must not be used as a blocker.

## Required Rules

- Reports must preserve the full v2 research boundary invariant.
- Reports must set `promotion_ready=false`,
  `candidate_pack_eligible=false`, `paper_signal=false`, `live_signal=false`,
  `sizing_instruction=false`, `order_placement_instruction=false`, and
  `runtime_mode_change=false`.
- Reports must use `autonomous_readiness_report_v1` and include report ID, run
  ID, created timestamp, status, required-check count, passed-check count,
  blocker count, blocker reasons, required-check keys, per-check summaries,
  artifact refs, and required next actions.
- The status may be `autonomous_research_ready` only when all required
  checklist items pass, all required artifacts exist, the cycle execution
  manifest is completed and audited, the current loop job kinds are present,
  the final audit report passes with current required job-kind and
  artifact-prefix criteria, the ledger and Lead Book are nonempty, and P0/P1
  counts are zero.
- Any missing or failed evidence must produce `status=blocked` and
  `autonomous_research_ready=false`.
- Generated report files are JSON artifacts and must reject secret-like or
  unsupported output paths before writes.
- A passing readiness report for synthetic test fixtures proves gate semantics
  only. A real manager completion claim still requires real evidence paths and
  current validation evidence.

## Forbidden

- Treating readiness reports as accepted research evidence, strategy
  profitability evidence, candidate-pack evidence, paper/live signal output,
  order instructions, sizing instructions, runtime-mode changes, or promotion
  artifacts.
- Inferring readiness from a queued plan, an unrun audit job, a fixture-only
  sandbox cycle, a blocker-containing audit report, or stale loop evidence that
  omits the strategy queue or validation gate stages.
- Suppressing missing authoritative free-venue data manifests, validation,
  independent-audit, ledger, Lead Book, open-issue, or loop-execution blockers.
- Weakening coverage floors, date floors, lockbox policy, no-touch paths,
  credential policy, data-licensing boundaries, or candidate/promotion
  language through readiness evidence.
