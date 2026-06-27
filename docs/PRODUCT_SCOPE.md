# Product Scope

Status: v2 canonical scope document
Audit ID: `V2-AUD-SCOPE-001`
Source: `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md`

## Canonical Identity

ResearchEngineDeluxe v2 is a research-only, data-first, multi-instrument
perpetual-futures research platform focused on Hyperliquid perpetuals above
USD 5,000,000 daily notional volume, with support for compatible multi-venue
comparison data, strict validation, owned data archives, agent-safe strategy
evaluation, and audit-by-chunk migration.

BTC and ETH remain important fixture, smoke-test, reference, and legacy
evidence instruments. They do not define the full v2 product scope.

## Product Purpose

The product exists to run a repeatable research loop:

```text
discover liquid Hyperliquid perpetual universe
  -> collect and archive venue data with provenance
  -> normalize raw/bronze/silver/gold datasets
  -> enforce data quality, coverage, as-of universe, and lockbox policies
  -> evaluate declarative strategy specs through controlled backtest engines
  -> apply conservative costs, funding, spread, slippage, impact, and capacity assumptions
  -> append every passed or failed trial to a canonical experiment ledger
  -> move interesting non-promotable ideas into a Lead Book
  -> deep-validate one serious lead at a time
  -> allow only the top 3 survivors into final hard-test review
```

The product is not a live trading system, paper trading system, execution
system, sizing system, order-placement system, or promotion system.

## Non-Negotiable Invariant

Every v2 artifact, command, run, dashboard, audit record, and result must
preserve this invariant unless a future explicit human-approved process outside
this roadmap changes the repository role:

```json
{
  "research_only": true,
  "observe_only": true,
  "promotion_ready": false,
  "candidate_evidence": false,
  "candidate_pack_eligible": false,
  "live_signal": false,
  "paper_signal": false,
  "sizing_instruction": false,
  "order_placement_instruction": false,
  "runtime_mode_change": false
}
```

Allowed language includes `research platform`, `research-only archive`,
`non-promotable lead`, `sandbox lead`, `deep validation`, `final hard-test
survivor`, and `historical robustness`.

Disallowed language is blocked unless explicitly negated: `paper-ready`,
`live-ready`, `trade-ready`, `deployment-ready`, `sizing-ready`, `order-ready`,
`signal-ready`, `candidate-pack ready`, `guaranteed profitable`, and
`production trading strategy`.

## Default Evidence Universe

Accepted v2 research evidence uses this default universe:

```yaml
venue: hyperliquid
market_type: perpetual
min_day_notional_usd: 5000000
selection_mode: as_of
coverage_min: 0.98
earliest_reported_backtest_start: "2024-01-01"
minimum_usable_months: 6
preferred_usable_months: 12
lockbox_policy: dynamic_full_calendar_months
```

Current-universe analysis is allowed only as explicitly labeled sandbox/current
research and is blocked from evidence claims because it carries survivorship
bias risk.

Below-threshold instruments may be archived, observed, used for diagnostic
sandbox tests, used as negative controls, or stored with exclusion reasons.
They may not be accepted evidence under the default v2 universe rule.

## Operator-Approved Free-Venue Data Lane

As of WPR106-552, the current authoritative data baseline is the strict-free
venue data that can actually be collected, validated, and reproduced. Binance
USD-M, Bybit, and Hyperliquid public/free data may be treated as comparable
research inputs with venue provenance preserved. Hyperliquid remains preferred
when it has usable coverage and passes cross-venue quality checks, but missing
or requester-pays native Hyperliquid historical archives are not blockers for
the current data-readiness scope.

Artifacts must preserve venue provenance, source access mode, coverage,
quality/drop decisions, and the research-only boundary invariant. Hyperliquid
rows may be excluded when they are missing, below coverage floors, not
available under strict-free constraints, or materially divergent from
comparable no-paid providers. External/free-venue rows used in this lane are
research inputs, not paper/live/order/sizing/runtime, candidate-pack, or
promotion evidence.

## Centralized Market-History Store

As of WPR106-534, the multi-venue/proxy lane has a centralized local
market-history store under `data/research/central_market_history/**`. The
store is append-only by batch, keeps raw downloads where practical, writes
normalized Parquet and JSONL artifacts, records source metadata,
symbol/timeframe normalization, checksums, coverage reports, quality reports,
and provider provenance, and deduplicates provider/symbol/timeframe/timestamp
candle rows while preserving duplicate source hashes in the manifest.

As of WPR106-543, central market-history storage has an explicit 300 GiB local
budget cap, bounded parallel official no-paid archive collection, atomic
`.part` downloads, source validation, source-discovery reports, quality reports,
and progress telemetry. The prior strict Hyperliquid-only interpretation is
out of scope for this central data-readiness lane: Hyperliquid remains
preferred when usable, but central multi-provider market-history readiness must
not fail solely because Hyperliquid history is missing for a symbol/window when
valid no-paid comparable provider data is present with provenance, checksums,
coverage, and quality evidence.

As of WPR106-544, the central store has an explicit collection ledger for
2024+ bar and orderflow coverage:
`data/research/central_market_history/manifests/wpr106-544-central-market-history-exhaustive-coverage-v2-collection_ledger-ef0cfdcda209.json`.
The packet collected every currently reachable Binance USD-M monthly 1m kline
ZIP for the discovered 230-symbol universe under the 300 GiB cap, retried the
three initial worker anomalies as official 404s, and normalized complete
2024-01 through 2026-05 1m bar manifests for BTC, ETH, SOL, and DOGE. Broad
non-priority symbols are mostly raw-collected but not fully normalized, and
dense 2024+ orderflow beyond existing January-March row-limited evidence is
budget-blocked inside the central 300 GiB store unless a narrower
symbol/window request is made. Hyperliquid official S3 history remains recorded
as requester-pays/operator-gated provenance, but it is out of scope for
strict-free data readiness and must not be treated as a blocker. Any
backtest or strategy path that requires 2024+ central market-history data must
consult this ledger first; complete `backtest_usable=true` entries may run,
partial entries must restrict tests to manifest-covered windows, and missing,
budget-blocked, unavailable, or out-of-scope required families must call off
the specific strategy path rather than silently substituting incomplete data.

As of WPR106-545, the project-needed current-public 1m bar set has been
normalized with a bounded process-pool artifact writer and serialized
append-manifest commits. The run added 622 monthly normalized archives and
26,991,645 rows, bringing the central store to 918 normalized Parquet
artifacts, 918 append-manifest rows, 41,501,963 normalized rows, and about
46.98 GiB used under the 300 GiB cap. Validation verified 737 project-needed
manifests and 740 raw/checksum/CRC source archives with zero raw failures and
zero `.part` files, but strict all-symbol continuous 1m readiness remains
blocked by `ISSUE-R106-033`: official Binance USD-M LITUSDT data has no kline
or aggTrade rows for `2025-12-23T00:00:00Z` through
`2025-12-23T17:29:00Z`. The final validation report is
`data/research/central_market_history/manifests/wpr106-545-project-needed-1m-normalization-validation-report-after-gap-proof.json`.

As of WPR106-546, `ISSUE-R106-033` is resolved by current-contract lifecycle
scoping rather than data imputation. Binance `exchangeInfo` and the official
launch announcement show the current project `LITUSDT` contract is Lighter
Protocol and starts at `2025-12-23T17:30:00Z`; pre-onboard static/legacy rows
in the monthly archive are excluded from current-project bars. The lifecycle
repair appends an 11,910-row December 2025 LIT manifest from official onboard
time through month end and regenerates the current project-needed 1m report at
`data/research/central_market_history/manifests/wpr106-546-project-needed-1m-current-lifecycle-validation-report.json`.
That report passes all 29 project symbols with 715 current-lifecycle manifests,
31,032,285 verified project rows, 715 verified raw ZIPs, zero raw failures, and
zero `.part` files. The central store now has 919 normalized Parquet artifacts,
919 append-manifest rows, 41,513,873 normalized rows, and about 46.982 GiB used
under the 300 GiB cap.

As of WPR106-550 through WPR106-552, the current data catalog and testing-agent handoff is
`docs/V2_DATA_CATALOG_AND_AGENTIC_RESEARCH_POINTERS.md`. It records that all
29 project symbols have lifecycle-scoped official Binance USD-M 1m bars
normalized and backtest-usable for the multi-provider/proxy data lane through
2026-05, and that the operator-approved external WPR106-549 raw-heavy archive
at `M:\additional_archive\researchenginedeluxe\wpr106_549_of_style_raw`
contains 1,159,478 complete official Binance USD-M OF-style source files across
`bookDepth`, `aggTrades`, `bookTicker`, `trades`, `metrics`, `klines`,
`markPriceKlines`, `indexPriceKlines`, and `premiumIndexKlines`, with zero
missing, invalid, or partial files in the fresh validation report. The external
archive is raw source readiness only; central OF-style normalized coverage is
still partial and must not be treated as feature-ready without a later
normalization/feature packet.

As of WPR106-552, the OF-style normalization/feature proof gap is resolved for
final audit: `src/tradingbotsuite/v2/data_sources/of_style_materialization.py`
materializes compact research-only features directly from the external raw
archive, and
`data/research/of_style_feature_materialization/wpr106_552/manifests/wpr106-552-of-style-feature-materialization-report.json`
records 251 materialized source files, 81,093,159 parsed input rows, 256,523
feature rows, and zero blocked materialized sources across all nine requested
families. Full all-source feature-panel expansion is a compute-scope decision
for later packets, not a data-source blocker.

This is the authoritative research-only data baseline for final audit and
agentic research handoff under strict-free/no-paid constraints. Legacy blockers
that require unavailable requester-pays or native Hyperliquid historical
official data are out of scope for this branch. This is not accepted
bounded-loop strategy readiness and not candidate-pack, paper/live, order,
sizing, runtime, promotion, or production-trading readiness.

## Evidence Floor

A v2 backtest result is accepted for research reporting only when it proves:

- start date is on or after 2024-01-01;
- usable data covers at least 6 months;
- 12 usable months are preferred when available;
- the dynamic latest full-month lockbox is excluded from ordinary iteration;
- data coverage is at least 0.98;
- an as-of universe snapshot is used for accepted evidence;
- strategy spec, parameters, archive snapshot, universe snapshot, cost model,
  validation policy, and run identity are hashed or otherwise manifest-backed;
- gross and net metrics are present;
- conservative cost, funding, spread, slippage, impact, and liquidity
  assumptions are represented;
- failed runs and rejected trials are logged rather than hidden.

## Implementation Status

This document defines scope. It does not prove that v2 M1, M2, M3, M4, or M5 is
implemented. Future packets must add source code, contracts, tests, manifests,
and validation evidence for each milestone.
