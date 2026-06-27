# WPR106-547 Hyperliquid Liquid 2025 Bar Certification

## Scope

Certify which Binance USD-M 1m bar instruments outside the current WPR106-546
project-complete set are reasonable next project additions because they:

- have official local Binance Vision monthly 1m kline ZIPs for every month from
  2025-01 through the latest complete monthly archive window, currently 2026-05;
- are currently available on Hyperliquid through public `metaAndAssetCtxs`;
- meet the default v2 Hyperliquid liquidity floor of USD 5,000,000
  `dayNtlVlm`.

This packet is evidence/reporting only. It does not normalize new bars, append
central manifests, run backtests, write candidate packs, change strategy scope,
or touch live/order/sizing/runtime/promotion paths.

## Allowed Paths

- `docs/work_packets/WPR106-547-hyperliquid-liquid-2025-bar-certification.md`
- `data/research/central_market_history/manifests/wpr106-547-*`
- `data/research/central_market_history/raw_sources/wpr106_547/**`

## Boundary

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

## Validation Plan

- Fetch one unsigned public Hyperliquid `metaAndAssetCtxs` snapshot and preserve
  raw request/response evidence under `raw_sources/wpr106_547`.
- Cross-check local raw Binance Vision monthly 1m ZIP coverage for non-project
  instruments from 2025-01 through 2026-05.
- Verify candidate source ZIPs are present, non-empty, valid ZIPs, and have no
  CRC failures.
- Write a certification report with pass/fail reasons and boundary flags.

## Result

Report:
`data/research/central_market_history/manifests/wpr106-547-hyperliquid-liquid-2025-1m-bar-certification-report.json`

Report SHA-256:
`c2f9628572a93c1b217225f1dcd6629bb8264c55f60c868f794594205564e9c2`

The fresh public Hyperliquid `metaAndAssetCtxs` snapshot dated 2026-06-26
reported 230 instruments and 24 instruments above the USD 5,000,000
`dayNtlVlm` floor. All 24 volume-eligible instruments are already included in
the WPR106-546 project-complete 1m bar universe, so zero additional
non-project instruments were certified.

Non-project raw-collected instruments rejected: 178.

Reason counts:

- `below_hyperliquid_day_notional_floor`: 178
- `missing_binance_archive_at_2025_01_start`: 37
- `missing_latest_complete_month_archive`: 2
- `missing_required_monthly_zip`: 39

Validation:

- `py -3.11 -m py_compile data/research/central_market_history/manifests/wpr106-547-certify-hyperliquid-liquid-2025-bars.py`
- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q` passed:
  463 passed, 1 warning
- central market-history `.part` file scan: 0
