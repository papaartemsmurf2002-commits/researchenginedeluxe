# WPR106-533 - V2 Multi-Venue Proxy Readiness Intake

Status: complete
Owner: Codex Research Agent
Date: 2026-06-25

## Objective

Implement the operator-approved direction that Binance, Bybit, and
Hyperliquid market candles may be treated as comparable research inputs for a
new multi-venue/proxy readiness lane, while preserving truthful provenance.
Hyperliquid remains the priority venue when available. If Hyperliquid data is
missing, low quality, or materially divergent from other providers, it may be
excluded from the proxy lane with explicit blocker/quality evidence.

This packet does not claim Hyperliquid-native accepted readiness. It creates
or prepares a separate multi-venue/proxy research evidence lane using non-paid
data only.

## Allowed Paths

- `docs/work_packets/WPR106-533-v2-multi-venue-proxy-readiness-intake.md`
- `docs/KNOWN_ISSUES.md`
- `docs/contracts/autonomous_readiness_contract.md`
- `docs/PRODUCT_SCOPE.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- New generated multi-venue proxy intake evidence under
  `data/research/wpr106_533_multi_venue_proxy_intake/**`

## No-Touch Paths

- Live runtime, order-placement, broker/execution, sizing, runtime config,
  promotion, shadow, and candidate-pack truth-layer paths.
- Existing generated research evidence under `data/research/**`, except the
  new WPR106-533 output root above.
- Secrets, `.env`, credential files, private caches, local SQLite operator
  databases, and generated `outputs/**`.

## Web Evidence Summary

- Hyperliquid official docs say historical market-data S3 access is
  requester-pays, and that S3 provides L2 book snapshots and asset contexts,
  not historical candle files. Under the operator's no-paid constraint, this
  route remains excluded.
- Hyperliquid public API remains usable for strict-free current/recent/daily
  diagnostic collection, but prior WPR106-532 evidence showed old 1h public
  windows can return empty.
- Binance public data and Binance Vision provide non-paid historical candle
  sources suitable for proxy/comparison research.
- Bybit public market APIs provide historical kline endpoints for spot, USDT
  contract, USDC contract, and inverse contract products without requiring a
  paid requester-pays path.
- Third-party Hyperliquid historical providers exist, but they must be
  separately classified before use. Requester-pays or paid/keyed paths remain
  excluded unless the operator later relaxes the no-paid constraint.

## Boundary

All generated artifacts must preserve:

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

- Collect or reuse Hyperliquid-priority public candle evidence where available.
- Collect non-paid Binance and Bybit public candle evidence for the same
  selected symbols/windows where endpoints permit.
- Record per-venue provenance, URL family, request bounds, row counts, hashes,
  coverage, and boundary flags.
- Compare venue coverage and close-price divergence. Keep Hyperliquid priority
  when usable; mark Hyperliquid missing/divergent as excluded when necessary;
  keep Binance/Bybit as proxy data only.
- Update docs/contracts so the original Hyperliquid-native readiness gate
  remains truthful while the new multi-venue/proxy readiness lane can progress.

## Collection Results

Generated evidence root:

`data/research/wpr106_533_multi_venue_proxy_intake/wpr106-533-binance-bybit-public-candles/**`

The packet collected non-paid public Binance USD-M and Bybit linear candles for
the 30 WPR106-532 Hyperliquid-current symbols. It covered:

- daily candles from 2024-01-01 through 2026-06-01;
- 1h candles from 2024-01-01 through 2024-07-01.

Artifacts:

- `manifests/multi_venue_proxy_public_candle_batch_manifest.json`
- `manifests/multi_venue_proxy_public_candle_batch_manifest.sha256`
- `parquet/multi_venue_proxy_candles.parquet`
- `manifests/multi_venue_proxy_quality_report.json`
- `manifests/multi_venue_proxy_quality_report.sha256`

Batch summary:

- `row_count=218735`
- `completed_count=103`
- `blocked_count=17`
- source access mode: `zero_cost_public_api`
- evidence role: `multi_venue_proxy_research_input`
- Hyperliquid-native readiness claim: `false`

Quality summary:

- Hyperliquid remained the priority daily venue for 20 symbols after coverage
  and cross-venue close-divergence checks.
- Binance/Bybit daily proxy had no additional selected symbols beyond those
  where Hyperliquid already passed the priority check; 10 daily symbols remain
  blocked by insufficient coverage or missing rows.
- Binance/Bybit 2024 H1 1h proxy is usable for 18 symbols and blocked for 12
  symbols due to missing/partial coverage.
- Close-divergence pass threshold was p95 absolute close difference <= 50 bps;
  coverage pass threshold was >= 0.98.

## Decision

Completed for the proxy lane. WPR106-533 does not close ISSUE-R106-032 because
that issue remains the original Hyperliquid-native autonomous-readiness
blocker. It does create a documented multi-venue/proxy research evidence lane
that follows the operator decision: Binance, Bybit, and Hyperliquid candles may
be treated as comparable non-paid research inputs, Hyperliquid is preferred
when usable, and low-quality or missing venues are blocked/dropped with
evidence.

## Expected Validation

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2/test_autonomous_readiness_audit_phase29.py -q
git diff --check
rg boundary scans for forbidden live/order/sizing/runtime/promotion/candidate-pack drift
```

## Validation

Passed:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2/test_autonomous_readiness_audit_phase29.py -q
# 8 passed, 1 warning
git diff --check
# passed; Git reported LF-to-CRLF working-copy warnings only
```

Boundary scans:

```powershell
rg -n "candidate_evidence\s*[:=]\s*true|candidate_pack_eligible\s*[:=]\s*true|promotion_ready\s*[:=]\s*true|live_signal\s*[:=]\s*true|paper_signal\s*[:=]\s*true|sizing_instruction\s*[:=]\s*true|order_placement_instruction\s*[:=]\s*true|runtime_mode_change\s*[:=]\s*true" src\tradingbotsuite\v2 docs\work_packets\WPR106-533-v2-multi-venue-proxy-readiness-intake.md data\research\wpr106_533_multi_venue_proxy_intake -g "*.json" -g "*.md"
# no matches
rg -n "tradingbotsuite\.(live|execution|orders|broker)|from\s+tradingbotsuite\.(live|execution|orders|broker)|place_order|submit_order|create_order" src\tradingbotsuite\v2\audit src\tradingbotsuite\v2\autonomy src\tradingbotsuite\v2\collectors src\tradingbotsuite\v2\data_sources src\tradingbotsuite\v2\backtest_data src\tradingbotsuite\v2\validation src\tradingbotsuite\v2\ledger src\tradingbotsuite\v2\lead_book docs\work_packets\WPR106-533-v2-multi-venue-proxy-readiness-intake.md
# no matches
rg -n "research_only\s*[:=]\s*false|observe_only\s*[:=]\s*false" src\tradingbotsuite\v2 docs\work_packets\WPR106-533-v2-multi-venue-proxy-readiness-intake.md data\research\wpr106_533_multi_venue_proxy_intake -g "*.json" -g "*.md"
# no matches
```
