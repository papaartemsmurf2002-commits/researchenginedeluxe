# V2 Hyperliquid Data Venue Runbook

Status: research-only operator runbook
Audit ID: `V2-AUD-DATASRC-047`
Source roadmap: `docs/roadmaps/V2_HYPERLIQUID_DATA_VENUE_ROADMAP.md`

## Boundary

The v2 data-venue work is a research-only, observe-only archive and feature
pipeline. No source, panel, coverage report, runbook step, or generated
artifact is paper-ready, live-ready, trade-ready, order-ready, sizing-ready,
signal-ready, candidate-pack-ready, or promotion-ready.

All outputs must preserve:

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

Do not import live order-placement adapters from research data modules. Do not
write live configuration. Do not place orders.

## Source Order

Use this order for future packets and operator runs:

1. Source registry and strict-free cost classes.
2. Symbol-map resolver and verified venue mappings.
3. As-of Hyperliquid universe snapshots with below-threshold exclusion
   evidence.
4. Binance Vision availability, checksum, parse, local archive ingest, and
   reconstructed-bar comparison.
5. Binance USD-M public derivatives context for funding, OI, mark/index,
   premium, taker flow, ratios, and basis.
6. Hyperliquid public REST recent/funding/L2 sources and bounded WebSocket
   capture sources.
7. Strict-zero-dollar requester-pays quarantine for official Hyperliquid files.
8. Bybit and OKX external comparison sources.
9. MEXC, Bitget, Gate, KuCoin, and HTX gap-filler sources.
10. dYdX, Deribit, spot, oracle, and on-chain context sources.
11. Bar reconstruction, feature reconstruction, data-family coverage gates, and
    gold research panels.

External venues are comparison/context sources. They must not be relabeled as
Hyperliquid-native fills, trades, execution truth, or venue-specific execution
proof.

## Strict-Free Policy

Allowed by default:

- `zero_cost_public`
- `public_rate_limited`
- `free_sample_only` only for schema diagnostics, never accepted historical
  coverage

Disabled by default:

- `public_requester_pays_transfer`
- `paid_or_keyed`

Hyperliquid official historical files are native but requester-pays. Under
strict-zero-dollar mode they remain quarantined. A future operator-approved
packet would need explicit scope, cost acknowledgement, source IDs, rollback,
coverage audits, and boundary validation before those files can be used.

## Prerequisites

Before any broad collection or gold panel work, confirm:

- `docs/ORCHESTRATOR_STAGE_LEDGER.md` has no active P0 blocker.
- `docs/KNOWN_ISSUES.md` has no open P0 and fewer than four open P1 issues.
- Source registry entries validate under strict-free mode.
- Symbol mappings are verified for the requested venue/source.
- The universe snapshot is as-of and records below-threshold exclusions.
- Archive root is local and root-contained.
- The requested source is not requester-pays or paid/keyed.
- The work packet allows every path being changed.

BTC and ETH are reference, fixture, smoke-test, and legacy evidence symbols.
They are not the full v2 product scope.

## Archive Layers

Use the local archive layout from the roadmap:

- `raw`: original downloaded or captured payloads, request/response metadata,
  source hashes, and checksums. Never mutate.
- `bronze`: parsed rows with source fields preserved.
- `silver`: normalized schemas by family and venue.
- `gold`: derived research panels and joined feature data.
- `manifests`: source registry, symbol maps, archive snapshots, coverage
  reports, quality reports, capture sessions, and gold panel manifests.

Gold panel artifacts must reference archive snapshot, universe snapshot, source
registry, symbol map, coverage gate, coverage reports, and feature reports.

## Data-Family Coverage

Do not rely on candle-only coverage. Track families separately:

- `universe_snapshot`
- `asset_contexts`
- `funding`
- `candles_1m`
- `trades`
- `bbo`
- `l2_snapshots`
- `open_interest`
- `liquidations`
- `spot_oracle_context`

Accepted family coverage requires `coverage_ratio >= 0.98`, no blocker
reasons, no diagnostic or external-proxy label, no requester-pays or paid/keyed
source, and full research-only boundary flags.

Coverage gates pass only when every required family already has accepted
coverage. Missing and rejected families must remain visible blocker evidence.

## Gold Panels

Gold panel construction is staged:

1. Build a `GoldResearchPanelManifest` from a passed coverage gate and feature
   refs.
2. Assemble in-memory `GoldResearchPanelRow` values from timestamped feature
   column values.
3. Write ready assemblies through `write_gold_research_panel_artifacts()` to
   the archive `gold` layer when a packet explicitly scopes the write.

Rows carry feature values, source row hashes, row hashes, and row-level
coverage flags. Nullable feature refs may be missing at a timestamp only when
the manifest declares the column nullable; missing non-nullable values block
assembly.

Gold panels remain research-only data artifacts. They are not accepted coverage
proof by themselves and they do not create candidate, paper, live, sizing,
order, runtime, or promotion evidence.

## Fail-Closed Handling

Fail before writing normalized data when:

- source registry entry is missing;
- cost class is not allowed under strict-free mode;
- symbol map status is ambiguous, missing, manual-review, or unverified;
- raw payload lacks source path, URL, or hash metadata;
- checksum verification fails where a checksum is expected;
- parser cannot classify the source schema;
- timestamps cannot normalize to UTC;
- interval rows are misaligned;
- API page caps or bounded session caps prevent requested coverage;
- output path includes unsafe or secret-like components.

Write explicit blocker evidence when:

- source has no symbol/date coverage;
- venue had not listed or had delisted the symbol;
- endpoint lookback is too short;
- rate limits prevent completion;
- Hyperliquid recent-window endpoints are requested for old history;
- requester-pays official sources are disabled by strict-free mode;
- data-family coverage is missing or rejected;
- gold-panel feature refs are missing, blocked, duplicated, or uncovered.

## Validation

For scoped code work, run focused tests first, then baseline validation:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

For docs-only runbook updates, at minimum run:

```powershell
git diff --check
```

`git diff --check` may report LF-to-CRLF warnings on this Windows checkout.
Those warnings are expected when no whitespace errors are reported.

## Operator Stops

Stop and open or update `docs/KNOWN_ISSUES.md` if:

- a P0 live/order/sizing/runtime/promotion boundary risk appears;
- strict-free mode cannot distinguish requester-pays or paid/keyed sources;
- a source appears to require credentials or payment despite being registered
  as strict-free;
- coverage appears accepted without archive, universe, source-registry,
  symbol-map, and coverage refs;
- external venue rows are labeled as Hyperliquid-native execution truth;
- generated artifacts would overwrite old evidence or no-touch paths.

Do not advance a stage while any P0 is open or four or more P1 issues are
unresolved.
