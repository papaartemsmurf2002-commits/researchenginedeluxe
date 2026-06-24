# Data Family Coverage Contract

Status: v2 data-venue roadmap foundation
Audit IDs: `V2-AUD-QUAL-007`, `V2-AUD-DATASRC-001`, `V2-AUD-QUAL-009`, `V2-AUD-QUAL-010`, `V2-AUD-QUAL-011`, `V2-AUD-QUAL-012`, `V2-AUD-DATASRC-043`, `V2-AUD-DATASRC-048`
Source roadmap: `docs/roadmaps/V2_HYPERLIQUID_DATA_VENUE_ROADMAP.md`

## Purpose

The data-family coverage contract records coverage by asset, venue, source,
family, and time window. It replaces single candle-only coverage assumptions
with explicit family reports for universe snapshots, asset contexts, funding,
1m candles, trades, BBO, L2, open interest, liquidations, and spot/oracle
context.

## Schema

Primary code schema:

- `DataFamilyCoverageReport`
- `DataFamilyCoverageGateResult`
- `DataFamilyCoverageSymbolSummary`
- `evaluate_data_family_coverage_gate`
- `preflight_gold_research_panels`
- `build_binance_vision_data_family_coverage_report`
- `build_binance_derivatives_context_coverage_report`
- `run_binance_vision_daily_backfill`
- `run_binance_derivatives_context_backfill`

Checked JSON schema and sample fixture:

- `configs/data_sources/v2_data_family_coverage.schema.json`
- `configs/data_sources/samples/data_family_coverage_hl_btc_trades_forward_segment.json`

## Required References

Every `DataFamilyCoverageReport` must reference:

- `universe_snapshot_ref`
- `source_registry_ref`
- `symbol_map_ref`
- source IDs and source cost classes
- coverage window
- expected bucket definition
- observed bucket count
- coverage ratio
- acceptance status
- reason/blocker codes when not accepted

When an archive snapshot exists, `archive_snapshot_ref` must point at it. A
forward capture segment or smoke fixture may leave the archive snapshot unset
only when it is explicitly non-accepted diagnostic evidence.

## Labels

Coverage labels must make source meaning explicit:

- `native_hyperliquid`
- `external_comparison`
- `external_proxy`
- `diagnostic_sample`

External comparison coverage can support cross-venue research features, but it
does not prove Hyperliquid-native execution or venue-specific fill truth.
External proxy and diagnostic sample coverage cannot be accepted research
coverage.

## Binance Vision Coverage

Binance Vision coverage reports are generated from availability, parser,
archive-ingest, and optional reconstructed-bar comparison evidence. They must
use `external_comparison` labels and source cost classes from the strict-free
source registry.

For daily trades and aggTrades, coverage is a one-day source-presence bucket.
For daily 1m klines, coverage is 1,440 one-minute buckets. Parser gaps,
duplicate native IDs, missing ingest evidence, missing archive snapshots,
available-but-unverified checksums, and failed reconstructed-bar comparison are
blocker reasons. Missing source ZIPs and unverified symbol mappings remain
explicit non-accepted coverage reports rather than hidden skips.

`run_binance_vision_daily_backfill()` writes these reports as JSON under
`manifests/coverage_reports/` after the target download, parse, ingest, and
optional reconstructed-bar comparison steps complete or block. The written
report is still governed by `DataFamilyCoverageReport` acceptance rules.

## Binance Derivatives Context Coverage

Binance USD-M derivatives context coverage reports are generated from
paginated context results and local raw/silver archive-ingest evidence. They
cover context families separately from candle/trade coverage:

- `funding_rate_history`;
- `open_interest`;
- `open_interest_statistics`;
- `mark_price_klines`;
- `index_price_klines`;
- `premium_index_klines`;
- `taker_buy_sell_volume`;
- `long_short_ratios`;
- `basis`.

These reports use `external_comparison` labels and
`public_rate_limited` source cost class. Accepted coverage requires completed
page fetches, completed archive ingest, raw/silver archive refs, an archive
snapshot ref, and complete expected buckets. Current `open_interest` snapshots
are coverage reports but are not accepted historical coverage because they are
current-context observations rather than bounded historical windows.

`run_binance_derivatives_context_backfill()` writes derivatives context
coverage reports as JSON under `manifests/coverage_reports/` for completed or
blocked local attempts. The backfill result preserves the coverage ref even
when coverage is non-accepted because of missing buckets, current-only
snapshots, missing archive evidence, or blocked page/archive inputs.

## Data-Family Coverage Gates

`evaluate_data_family_coverage_gate()` starts the generic `DATA-016` gate
foundation. It consumes existing `DataFamilyCoverageReport` objects for one
symbol/ref context, requires an explicit family set, and returns a
deterministic `DataFamilyCoverageGateResult` with accepted family report IDs,
missing families, rejected families, blocker reasons, and a stable gate ID.

The gate does not create accepted coverage evidence by itself. A required
family passes only when an existing report is already
`accepted_for_research_reporting=true`, has no blocker reasons, and meets the
requested coverage minimum. Empty report inputs, missing required families,
non-accepted required family reports, mismatched symbol/ref context, and empty
required family sets fail closed. Gate results remain research-only,
observe-only, non-promotable, and not candidate or promotion evidence.

## Multi-Symbol Coverage Preflight

`preflight_gold_research_panels()` extends the gate foundation by grouping
existing `DataFamilyCoverageReport` objects across an explicit declared symbol
set. It calls `evaluate_data_family_coverage_gate()` independently for each
symbol and returns deterministic `DataFamilyCoverageSymbolSummary` rows with
all coverage report refs, accepted required-family report refs, missing
families, rejected required families, gate IDs, and blocker reasons.

The preflight does not infer symbols from provider data. The declared symbol
list must be sorted, unique, and nonempty. A symbol with no coverage reports,
missing required families, rejected required-family reports, mismatched
universe/source/symbol-map/archive refs, or failed gate output remains blocked
with explicit blocker reasons. Multi-symbol summaries remain research-only
aggregation metadata; they are not accepted historical coverage proof,
candidate evidence, candidate-pack evidence, paper/live signal evidence,
sizing instructions, order-placement instructions, runtime-mode changes, or
promotion evidence.

## Acceptance Rules

Accepted family coverage requires:

- `coverage_ratio >= coverage_min`;
- no blocker reasons;
- no `diagnostic_sample` or `external_proxy` labels;
- no `free_sample_only`, `public_requester_pays_transfer`, or `paid_or_keyed`
  source cost class;
- full canonical v2 research-only boundary flags.

The following reasons always block accepted coverage:

- `forward_capture_segment_only`
- `not_full_2024_plus_window`
- `recent_window_only`
- `recent_window_api_cap`
- `bounded_session_not_continuous`
- `free_sample_only`
- `diagnostic_sample_non_evidence`
- `requester_pays_disabled`
- `external_proxy_non_native`
- `paid_or_keyed_out_of_scope`

## Forbidden

- Bounded WebSocket sessions must not be accepted as continuous historical
  coverage proof.
- Recent Hyperliquid API snapshots must not be accepted as six-month or
  twelve-month historical coverage proof.
- External proxy coverage must not be treated as Hyperliquid-native coverage.
- Missing families must not be hidden. They must become explicit blocker
  evidence.
- Coverage reports must not emit paper/live/order/sizing/runtime-mode,
  candidate-pack, or promotion claims.
