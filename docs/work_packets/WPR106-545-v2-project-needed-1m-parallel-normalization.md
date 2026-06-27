# WPR106-545 - V2 Project-Needed 1m Parallel Normalization

Status: complete - strict all-symbol 1m readiness blocked by ISSUE-R106-033
Owner: Codex Research Agent
Date: 2026-06-26

## Objective

Normalize all currently project-needed, raw-collected Binance USD-M monthly 1m
kline archives into central market-history manifests using bounded parallel
artifact creation and serialized append-manifest updates. Validate that every
current Hyperliquid USD 5M+ symbol, plus BTC/ETH reference symbols and known
compatible aliases such as `KPEPE -> 1000PEPE`, has complete local 1m bar
coverage from listing month or 2024-01, whichever is later, through 2026-05.

This packet remains research-only central data readiness. It does not create
candidate-pack, paper/live, order, sizing, runtime-mode, promotion, autonomous
strategy, or production trading readiness.

## Starting State

WPR106-544 collected and verified raw official Binance USD-M 1m ZIP archives
for the discovered central universe. BTC, ETH, SOL, and DOGE were normalized
and backtest-usable for 2024-01 through 2026-05. A follow-up validation report
found the remaining current project symbols had raw collected 1m archives but
not normalized central manifests.

The active central-store cap remains 300 GiB. Before this packet the central
store measured approximately 44.4 GiB, had 296 append-manifest rows,
14,510,318 normalized rows, 4,799 verified WPR106-544 raw ZIPs, and zero
`.part` files.

## Allowed Paths

- `docs/work_packets/WPR106-545-v2-project-needed-1m-parallel-normalization.md`
- `docs/PRODUCT_SCOPE.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/contracts/autonomous_readiness_contract.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/v2/data_sources/central_market_history.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `tests/v2/test_central_market_history_store_phase76.py`
- New append-only generated central market-history artifacts under
  `data/research/central_market_history/**`

## No-Touch Paths

- Live runtime, order-placement, broker/execution, sizing, runtime config,
  promotion, shadow, and candidate-pack truth-layer paths.
- Existing generated research evidence under `data/research/**`, except the
  append-only `data/research/central_market_history/**` output root.
- Secrets, `.env`, credential files, private caches, local SQLite operator
  databases, requester-pays data, paid sources, fixture-only/synthetic data as
  accepted evidence, sandbox-only evidence as accepted evidence, and generated
  `outputs/**`.

## Boundary

All new artifacts and helper models preserve:

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

## Plan

- Add deferred append-manifest support to the fast OHLCV writer so worker
  processes can create complete batch artifacts without racing on the central
  append manifest.
- Add a small public append helper that verifies the batch manifest SHA before
  serial append.
- Run a bounded process-pool normalizer over the remaining project-needed
  raw-collected symbols, with per-symbol workflows and coordinator-owned
  append-manifest writes.
- Regenerate a project-needed 1m readiness report and collection ledger.
- Validate source compile, focused central store tests, contracts, diff
  hygiene, absence of `.part` files, and research-boundary flags.

## Expected Validation

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2/test_central_market_history_store_phase76.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/contracts -q
git diff --check
rg boundary scans for forbidden live/order/sizing/runtime/promotion/candidate-pack drift
```

## Result

Implemented the fastest low-risk speedup: worker processes now create complete
OHLCV batch artifacts with `append_to_manifest=false`, and the coordinator
serially appends verified manifest entries through
`append_central_market_history_manifest_entry`. The focused store regression
proves deferred append is idempotent for exact retries.

Generated scripts and evidence:

- `data/research/central_market_history/manifests/wpr106-545-parallel-normalize-project-1m-bars.py`
- `data/research/central_market_history/manifests/wpr106-545-parallel-normalize-project-1m-bars-progress.jsonl`
- `data/research/central_market_history/manifests/wpr106-545-project-needed-1m-normalization-validation-report-after-gap-proof.json`
- `data/research/central_market_history/manifests/wpr106-545-project-needed-1m-normalization-readiness-after-gap-proof-collection_ledger-4ce5a7467c31.json`
- `data/research/central_market_history/manifests/wpr106-545-lit-2025-12-daily-repair-source-discovery-report.json`

The bounded four-worker normalization run completed in 1,989.5 seconds,
appended 622 additional monthly normalized Binance USD-M 1m archives, wrote
26,991,645 new normalized rows, skipped 116 already-normalized BTC/ETH/SOL/DOGE
archives, and reported zero failed symbols and zero failed archives. The
central store now has 918 normalized Parquet artifacts, 918 append-manifest
rows, 41,501,963 normalized rows, zero `.part` files, and uses approximately
46.98 GiB of the 300 GiB cap.

Independent validation verified 737 project-needed manifests, 32,028,375
project-needed normalized rows, and 740 official raw/checksum/CRC sources with
zero raw failures and zero partial files. Strict all-symbol continuous 1m
readiness did not pass because `LITUSDT` has an official provider gap on
`2025-12-23T00:00:00Z` through `2025-12-23T17:29:00Z`. The monthly kline,
daily kline, daily aggTrades, and public Binance USD-M kline API checks all
show no rows for that interval. This is tracked as `ISSUE-R106-033`; no
synthetic fill or carry-forward bars were written.
