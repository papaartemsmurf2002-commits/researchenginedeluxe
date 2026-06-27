# Next Agent Handoff - WPR106-549 OF-Style Data Expansion

Date: 2026-06-27
Owner: Codex Research Agent
Status: validated

## Operator Direction

The operator requested aggressive collection of all possible no-paid
OF-style/L2-style data for the 29 project symbols into the external heavy
archive at:

`M:\additional_archive\researchenginedeluxe\wpr106_549_of_style_raw`

The operator explicitly removed size-limit concerns for this additional
archive. The central market-history 300 GiB cap still applies to the central
store under `data/research/central_market_history/**`, but it does not apply
to the `M:\additional_archive` raw-heavy archive.

## Completed Archive Collection

The following official Binance Vision USD-M daily source families were
collected and validated for the 29 project symbols:

- `bookDepth`
- `aggTrades`
- `bookTicker`
- `trades`
- `metrics`
- `klines`
- `markPriceKlines`
- `indexPriceKlines`
- `premiumIndexKlines`

Validated complete sources by family:

| Family | Complete sources | Missing | Invalid |
| --- | ---: | ---: | ---: |
| `aggTrades` | 22,256 | 0 | 0 |
| `bookDepth` | 22,236 | 0 | 0 |
| `bookTicker` | 1,680 | 0 | 0 |
| `indexPriceKlines` | 266,652 | 0 | 0 |
| `klines` | 267,384 | 0 | 0 |
| `markPriceKlines` | 267,384 | 0 | 0 |
| `metrics` | 22,282 | 0 | 0 |
| `premiumIndexKlines` | 267,348 | 0 | 0 |
| `trades` | 22,256 | 0 | 0 |

Total validated sources: 1,159,478.

## Fresh Validation Evidence

Fresh validation was run on 2026-06-27:

```powershell
$env:PYTHONPATH='src'
$env:WPR106549_VALIDATE_FAMILIES='bookDepth,aggTrades,bookTicker,trades,metrics,klines,markPriceKlines,indexPriceKlines,premiumIndexKlines'
$env:WPR106549_VALIDATE_SHA='0'
$env:WPR106549_VALIDATE_CRC='0'
python data/research/central_market_history/manifests/wpr106-549-heavy-raw-archive-validate.py
```

Result:

```json
{
  "source_count": 1159478,
  "complete_source_count": 1159478,
  "missing_source_count": 0,
  "invalid_source_count": 0,
  "partial_file_count": 0
}
```

Validation report:

`M:\additional_archive\researchenginedeluxe\wpr106_549_of_style_raw\manifests\wpr106-549-heavy-raw-archive-validation-report.json`

Report `created_at`: `2026-06-27T09:25:28.927445+00:00`.

The validation report also records:

- `metadata_missing_count=0`
- `sha_sidecar_missing_count=0`
- `sha_mismatch_count=0`
- `crc_failure_count=0`
- `research_only=true`
- `observe_only=true`
- `promotion_ready=false`
- `candidate_pack_eligible=false`
- `live_signal=false`
- `paper_signal=false`
- `sizing_instruction=false`
- `order_placement_instruction=false`
- `runtime_mode_change=false`

No downloader process is active and no `.part` files remain under the external
archive.

## Collector Implementation Notes

Primary scripts:

- `data/research/central_market_history/manifests/wpr106-549-heavy-raw-downloader.py`
- `data/research/central_market_history/manifests/wpr106-549-heavy-raw-source-discovery.py`
- `data/research/central_market_history/manifests/wpr106-549-heavy-raw-archive-validate.py`

The downloader supports:

- bounded threaded downloads;
- atomic `.part` files;
- expected-byte checks;
- ZIP validation at download time;
- optional upstream `.CHECKSUM` retrieval and comparison;
- SHA-256 sidecars;
- source metadata sidecars;
- progress JSONL;
- per-batch JSON reports plus `.sha256` report sidecars;
- repeat-until-done mode;
- run labels;
- disjoint symbol filters via `WPR106549_HEAVY_SYMBOLS` and
  `WPR106549_HEAVY_EXCLUDE_SYMBOLS`.

Large `trades` collection was completed with disjoint symbol shards. Shard A
found no remaining early-symbol files after the prior all-symbol run; shards B,
C, and D completed the remaining symbol ranges. A stuck JUP `.part` was removed
only after its owning shard was stopped and path containment was verified.

## Important Caveats

- The latest validation rerun did not recompute full SHA-256 or ZIP CRC for
  every file. It validated every discovered source for presence, expected byte
  size, ZIP recognizability, metadata sidecar, SHA sidecar, missing/invalid
  source counts, and no partial files. The downloader already performed size,
  ZIP, and available upstream checksum validation at download time.
- Do not copy all external raw-heavy data into the capped central store. Use
  external archive refs or derive compact normalized/feature artifacts under a
  separate packet with explicit central budget accounting.
- Hyperliquid-native historical L2/trade archives remain outside this packet:
  official historical S3 data is operator-gated/requester-pays rather than
  strict no-paid public archive intake. Public REST/WebSocket Hyperliquid L2 is
  live/current capture, not full historical L2 backfill.
- This packet creates no accepted strategy evidence, autonomous readiness,
  candidate pack, paper/live/order/sizing/runtime, or promotion claim.

## Recommended Next Work

1. Do not redownload these raw archives unless validation finds drift. Treat
   the external archive as the raw-heavy source of truth for WPR106-549.
2. Open a new work packet for normalization from external raw archive refs.
   Keep central-store writes compact and budget-gated.
3. Normalize in symbol/family shards rather than one monolithic job. Use
   process-level parallelism for parse-heavy families and serialized manifest
   appends for final commits.
4. Start with lower-risk derived artifacts:
   `metrics`, kline-style context, `aggTrades`, `trades`, then `bookTicker`
   and `bookDepth` features.
5. Preserve source provenance, raw refs, checksums, quality reports, and the
   canonical research-only boundary in every normalized or feature artifact.
6. If native Hyperliquid historical L2 is required, open a separate operator
   gate packet that explicitly handles requester-pays/AWS costs and quarantines
   that source lane from strict no-paid evidence.

## Validation Commands For The Next Agent

Fast archive coverage validation:

```powershell
$env:PYTHONPATH='src'
$env:WPR106549_VALIDATE_FAMILIES='bookDepth,aggTrades,bookTicker,trades,metrics,klines,markPriceKlines,indexPriceKlines,premiumIndexKlines'
python data/research/central_market_history/manifests/wpr106-549-heavy-raw-archive-validate.py
```

Focused code validation:

```powershell
python -m py_compile data/research/central_market_history/manifests/wpr106-549-heavy-raw-downloader.py data/research/central_market_history/manifests/wpr106-549-heavy-raw-archive-validate.py
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

## Required Boundary

Every future derived artifact must preserve:

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

No paper/live/order/sizing/runtime/promotion/candidate-pack semantics should
be introduced by normalization, feature construction, or future data audits.
