# V2 Data Catalog And Agentic Research Pointers

Status: WPR106-553 final-audited free-venue data and agentic testing handoff catalog  
Last updated: 2026-06-27  
Scope: research-only data readiness and testing-agent navigation

## Current Verdict

The project has the authoritative strict-free/no-paid market data baseline
needed for the current 29-symbol project research lane:

- lifecycle-scoped official Binance USD-M 1m bars are normalized and
  backtest-usable for all 29 project symbols through 2026-05;
- the external WPR106-549 raw-heavy archive contains all requested available
  official Binance USD-M OF-style source files for those symbols;
- WPR106-552 materializes a compact per-symbol OF-style feature proof pack
  directly from the raw archive, covering all nine requested families with zero
  blocked sources in the bounded audit pass;
- central market-history reports, source manifests, checksums, sidecars, and
  boundary flags are present for the accepted data-lane evidence.

This is the pragmatic data pass. It does not mean every theoretically possible
source on the internet has been collected. Native historical Hyperliquid
official S3 history is requester-pays/operator gated and is out of scope for
the strict-free lane; it is not a blocker and agents should not chase it.
Full row-level expansion of all 1,159,478 raw files into central storage is not
required for this data pass; the WPR106-552 materializer provides the compact
feature path and the WPR106-549 validation report remains the raw completeness
authority.

WPR106-553 completes the final repo audit. The repo is ready for
research-only agentic iteration strategy testing under scoped packets. This is
not autonomous readiness, accepted research readiness, candidate-pack
readiness, paper/live readiness, order/sizing/runtime readiness, promotion
readiness, production trading readiness, or a strategy-performance claim.

## Boundary Invariant

Every data artifact in this catalog is research-only:

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

No item below is a candidate pack, paper/live signal, sizing instruction,
runtime-mode change, promotion artifact, or production-trading claim.

## Authoritative Data Pointers

| Lane | Status | Use for testing | Primary evidence |
| --- | --- | --- | --- |
| Project 1m bars | Ready for bar-based research tests over current project lifecycle | Bar-only backtests and feature construction for the 29 project symbols, subject to lockbox rules | `data/research/central_market_history/manifests/wpr106-546-project-needed-1m-current-lifecycle-validation-report.json` |
| External OF-style raw archive | Authoritative raw source-of-truth complete for requested available official Binance USD-M families | Source inputs for later normalization/feature packets; do not consume as central normalized data directly | `M:\additional_archive\researchenginedeluxe\wpr106_549_of_style_raw\manifests\wpr106-549-heavy-raw-archive-validation-report.json` |
| OF-style compact feature materialization | Ready as bounded per-symbol feature proof pack and reusable materializer | Testing-agent proof that all available free OF-style family schemas parse and materialize under current constraints; open a compute packet for full 1.16M-source expansion if needed | `data/research/of_style_feature_materialization/wpr106_552/manifests/wpr106-552-of-style-feature-materialization-report.json` |
| Central OF-style normalized store | Partial by design | Use only manifest-covered windows; call off strategies requiring missing families/windows | `data/research/central_market_history/manifests/wpr106-549-of-style-overall-status-report.json` |
| Broad central collection ledger | Mixed: complete, partial, budget-blocked, unavailable, and operator-gated entries | First stop before any strategy path that requires specific symbols/families/windows | `data/research/central_market_history/manifests/wpr106-544-central-market-history-exhaustive-coverage-v2-collection_ledger-ef0cfdcda209.json` |
| Hyperliquid liquid-2025 additions | No extra non-project symbols certified | Confirms current 24 Hyperliquid volume-eligible symbols are already inside the project-complete lane | `data/research/central_market_history/manifests/wpr106-547-hyperliquid-liquid-2025-1m-bar-certification-report.json` |

## Project 1m Bar Dataset

Report:
`data/research/central_market_history/manifests/wpr106-546-project-needed-1m-current-lifecycle-validation-report.json`

Validated facts:

| Field | Value |
| --- | ---: |
| Project symbols | 29 |
| All project symbols backtest-usable for 1m bars | true |
| Verified normalized manifests | 715 |
| Verified normalized rows | 31,032,285 |
| Verified raw ZIPs | 715 |
| Append-manifest rows in central store | 919 |
| Central store used | about 46.981 GiB |
| Central store remaining under 300 GiB cap | about 253.019 GiB |
| Central `.part` files found in WPR106-550 scan | 0 |

Project symbols:

```text
AAVE, ADA, AERO, AVAX, BNB, BTC, DOGE, ENA, ETH, FARTCOIN, HYPE, IP,
JTO, JUP, KPEPE, LINK, LIT, NEAR, PUMP, SOL, SUI, TAO, UNI, VVV, WLD,
XMR, XPL, XRP, ZEC
```

Lifecycle caveat:

- `LIT` uses the current Lighter Protocol `LITUSDT` Binance USD-M lifecycle
  start at `2025-12-23T17:30:00Z`.
- Pre-onboard static/legacy `LITUSDT` rows remain excluded from current-project
  bars and must not be used as current LIT evidence.

Lockbox rule for testing agents:

- As of 2026-06-27, the latest full calendar month is 2026-05.
- Ordinary iteration must treat 2026-05 as the dynamic lockbox and avoid
  tuning on it unless a later packet explicitly scopes benchmark/final-test use.
- Bar-based research can use earlier covered windows according to the strategy
  packet's split, warmup, and lockbox policy.

## External Raw-Heavy OF-Style Archive

Report:
`M:\additional_archive\researchenginedeluxe\wpr106_549_of_style_raw\manifests\wpr106-549-heavy-raw-archive-validation-report.json`

The external archive is outside the central market-history 300 GiB cap by
operator direction. It is the raw-heavy source of truth for WPR106-549; do not
copy it into the central store without a separate budgeted normalization
packet.

Under the current strict-free/no-paid constraint, this archive is complete for
the requested available OF-style families. Missing native Hyperliquid official
history is not part of this lane and is not a data-readiness blocker.

Fresh report facts:

| Field | Value |
| --- | ---: |
| Report `created_at` | `2026-06-27T09:45:48.428484+00:00` |
| Source files | 1,159,478 |
| Complete source files | 1,159,478 |
| Missing source files | 0 |
| Invalid source files | 0 |
| Missing metadata sidecars | 0 |
| Missing SHA-256 sidecars | 0 |
| SHA mismatches | 0 |
| CRC failures reported | 0 |
| External `.part` files found in WPR106-550 scan | 0 |

Complete sources by family:

| Family | Complete sources |
| --- | ---: |
| `aggTrades` | 22,256 |
| `bookDepth` | 22,236 |
| `bookTicker` | 1,680 |
| `indexPriceKlines` | 266,652 |
| `klines` | 267,384 |
| `markPriceKlines` | 267,384 |
| `metrics` | 22,282 |
| `premiumIndexKlines` | 267,348 |
| `trades` | 22,256 |

## OF-Style Feature Materialization

Report:
`data/research/of_style_feature_materialization/wpr106_552/manifests/wpr106-552-of-style-feature-materialization-report.json`

WPR106-552 adds a deterministic materializer at
`src/tradingbotsuite/v2/data_sources/of_style_materialization.py` and validates
it with `tests/v2/test_of_style_materialization_phase78.py`. The real archive
run materialized one earliest available source per symbol/family, using `1m`
for kline-context families, and preserved the WPR106-549 archive validation
report as the full-source completeness proof.

Materialization facts:

| Field | Value |
| --- | ---: |
| Archive sources linked | 1,159,478 |
| Archive complete sources linked | 1,159,478 |
| Materialized source files | 251 |
| Blocked source files | 0 |
| Parsed input rows | 81,093,159 |
| Materialized feature rows | 256,523 |
| Feature families | `orderflow`, `bbo_spread`, `l2_depth`, `derivatives_context`, `kline_context` |
| Report `final_audit_data_ready` | true |

Materialized sources by raw family:

| Family | Source files | Input rows | Feature rows |
| --- | ---: | ---: | ---: |
| `aggTrades` | 29 | 8,192,915 | 32,414 |
| `bookDepth` | 29 | 646,620 | 32,372 |
| `bookTicker` | 19 | 50,235,987 | 26,250 |
| `indexPriceKlines` | 29 | 33,191 | 33,191 |
| `klines` | 29 | 32,415 | 32,415 |
| `markPriceKlines` | 29 | 33,266 | 33,266 |
| `metrics` | 29 | 6,482 | 6,482 |
| `premiumIndexKlines` | 29 | 27,719 | 27,719 |
| `trades` | 29 | 21,884,564 | 32,414 |

Use this as the audit proof that the available free OF-style schemas are
normalizable and feature-materializable. Treat full all-file materialization as
a compute expansion decision, not a data-readiness blocker.

Validation caveat:

- The latest validator report was generated with `check_sha=false` and
  `check_crc=false`.
- The downloader validates ZIP/size and available upstream checksums at
  download time.
- A full WPR106-550 validator invocation with SHA/CRC disabled refreshed the
  report but exceeded a five-minute local shell timeout before normal command
  completion. Use a longer timeout for independent audit if an exit code from
  the 1.16M-file scan is required.

## Central OF-Style Status

Report:
`data/research/central_market_history/manifests/wpr106-549-of-style-overall-status-report.json`

The central capped store is intentionally not complete for all raw-heavy
families:

| Family | Central-store status |
| --- | --- |
| `bookDepth` | Partial central normalized collection: AAVE complete, ADA started, 937 of 22,236 unique sources collected, 2,643,654 normalized rows, 0 `.part` files. |
| `aggTrades` | Raw bytes fit current cap, but full normalized collection still requires staged budget checks. |
| `bookTicker` | Discovery-only in central WPR106-549 status; high normalized-storage risk. Raw external archive is complete. |
| `trades` | Blocked from central capped store because raw bytes exceed remaining 300 GiB budget. Raw external archive is complete. |

`ISSUE-R106-004` is resolved for raw collection by the external archive lane,
not by central-store normalization. Strategies requiring OF-style features must
either consume WPR106-552 materialized refs within their scoped window, open a
full-scope compute/materialization packet, or call off.

## Hyperliquid Public And Native Provenance Status

Report:
`data/research/central_market_history/manifests/wpr106-547-hyperliquid-liquid-2025-1m-bar-certification-report.json`

Validated facts:

- public Hyperliquid snapshot instruments: 230;
- current volume-eligible instruments above USD 5,000,000 day notional: 24;
- volume-eligible non-project additions: 0;
- raw-collected non-project instruments rejected: 178;
- no additional non-project instrument was certified.

Controlling interpretation:

- Hyperliquid public/current data remains provenance-labeled and must not be
  relabeled as native historical as-of data.
- Hyperliquid official historical S3 data remains requester-pays/operator
  gated and was not collected in the no-paid data lane.
- WPR106-551 makes that absence out of scope for data readiness. It is a
  provenance caveat, not a blocker.
- Free-venue research can use Binance/Bybit/Hyperliquid comparable data with
  provenance. External rows must not be relabeled as Hyperliquid-native rows.

## Testing-Agent Rules

1. Start with this file, then read `docs/PRODUCT_SCOPE.md`,
   `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`, `docs/KNOWN_ISSUES.md`, and the
   latest work packet before running strategy tests.
2. For bar-only tests over the 29 project symbols, use the WPR106-546 report as
   the source of allowed symbols/windows and enforce the dynamic lockbox.
3. For any strategy needing raw trades, aggregate trades, BBO, depth, mark
   price, index price, premium, or metrics, start with the WPR106-552
   materialization report. If the required symbol/window is outside the compact
   proof pack, open a scoped compute/materialization packet rather than
   treating data collection as missing.
4. Do not silently substitute 1m bars for missing OF/L2/trade inputs.
5. Do not relabel current-public Hyperliquid data or external venue rows as
   native Hyperliquid historical data.
6. Keep failed data gates, partial coverage, budget blockers, and out-of-scope
   source states explicit. Do not let out-of-scope requester-pays Hyperliquid
   history block the free-venue data lane.
7. Append or derive new artifacts only through scoped packets with manifests,
   hashes, row counts, quality reports, and boundary flags.

## Final-Audit Checklist

Minimum checks for the next independent audit:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_central_market_history*.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_of_style_materialization_phase78.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_ui_visibility_phase22.py -q
```

Data checks:

```powershell
Get-ChildItem data\research\central_market_history -Recurse -Filter *.part
Get-ChildItem M:\additional_archive\researchenginedeluxe\wpr106_549_of_style_raw -Recurse -Filter *.part
```

Optional long external archive validation:

```powershell
$env:PYTHONPATH='src'
$env:WPR106549_VALIDATE_FAMILIES='bookDepth,aggTrades,bookTicker,trades,metrics,klines,markPriceKlines,indexPriceKlines,premiumIndexKlines'
$env:WPR106549_VALIDATE_SHA='0'
$env:WPR106549_VALIDATE_CRC='0'
python data\research\central_market_history\manifests\wpr106-549-heavy-raw-archive-validate.py
```

Use a timeout longer than five minutes for the optional validator on this
Windows host.

## Remaining Work

- WPR106-553 clears the final-audit wait for research-only agentic iteration
  strategy testing under scoped packets.
- No open P0/P1 data-source blocker remains for the strict-free/free-venue
  baseline.
- WPR106-552 resolves the normalization/feature-materialization proof gap for
  strict-free OF-style data. Full all-file feature-panel expansion is a
  compute-scope choice for a later packet, not a data-source blocker.
- No candidate pack, no accepted autonomous-readiness report, and no
  paper/live/order/sizing/runtime/promotion artifact exists.
