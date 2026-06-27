# WPR106-532 - V2 Autonomous Readiness Strict-Free Data Intake

Status: blocked
Owner: Codex Research Agent
Date: 2026-06-25

## Objective

Autonomously attempt strict-free data intake that could support
ISSUE-R106-032, using only current worktree capabilities and public/zero-cost
sources. Do not weaken readiness gates, relabel diagnostic/current/sandbox
evidence, fabricate historical as-of universe evidence, or use fixture,
synthetic, supplied-ref, paid/keyed, requester-pays, paper/live/order/sizing,
runtime, promotion, or candidate-pack machinery as accepted readiness evidence.

If public strict-free sources cannot provide the required accepted historical
as-of Hyperliquid inputs, record the exact reason and keep readiness blocked.

## Allowed Paths

- `docs/work_packets/WPR106-532-v2-autonomous-readiness-strict-free-data-intake.md`
- `docs/KNOWN_ISSUES.md`
- New generated strict-free intake and audit evidence under
  `data/research/wpr106_532_autonomous_readiness_strict_free_intake/**`

## No-Touch Paths

- Live runtime, order-placement, broker/execution, sizing, runtime config,
  promotion, shadow, and candidate-pack truth-layer paths.
- Existing generated research evidence under `data/research/**`, except the
  new WPR106-532 output root above.
- Source code, tests, and contracts unless a later scoped packet explicitly
  changes implementation.
- Secrets, `.env`, credential files, private caches, local SQLite operator
  databases, and generated `outputs/**`.

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

- Inspect currently exposed CLI/worker downloader capabilities and classify
  which are Hyperliquid-native versus external-comparison/context only.
- Run bounded strict-free Hyperliquid public collection attempts into the
  WPR106-532 root, including a current daily-window sanity run and an old
  intraday-window probe if feasible.
- Do not use external venues as Hyperliquid-native accepted evidence. External
  venue downloaders may be noted as context/comparison capability only.
- Audit produced manifests for historical `as_of` universe rows, accepted
  coverage, backtest-data readiness, and autonomous readiness eligibility.
- Update `docs/KNOWN_ISSUES.md` honestly if strict-free autonomous download
  cannot supply the required accepted evidence.

## Capability Inspection

The current CLI exposes one Hyperliquid-native bounded public collector:
`redx collectors historical-perps`. It supports `candle_source=public_api` and
`candle_source=trusted_records`; the latter reads operator-supplied local
Hyperliquid-native files and is not an autonomous public downloader.

The recent data-source work added many venue registries, symbol-map/probe
surfaces, Binance Vision downloading, Binance derivatives context workers, and
external venue/reference/context fetch-normalize foundations. Those are useful
for comparison/context evidence, but they are explicitly not Hyperliquid-native
historical as-of universe proof and cannot be relabeled into accepted
autonomous readiness evidence.

## Strict-Free Collection Attempts

All generated WPR106-532 data was written under:

`data/research/wpr106_532_autonomous_readiness_strict_free_intake/**`

Commands:

```powershell
$env:PYTHONPATH='src'; py -3.11 -m tradingbotsuite.v2.cli.main collectors historical-perps --output-root data\research\wpr106_532_autonomous_readiness_strict_free_intake --run-id wpr106-532-old-1h-btc-eth-sol-public --start-ts 2024-01-01T00:00:00+00:00 --end-ts 2024-01-08T00:00:00+00:00 --timeframe 1h --asof-date 2026-06-25 --max-instruments 0 --coin BTC --coin ETH --coin SOL --max-public-info-pages 20 --binance-timeout 20 --created-by-id WPR106-532
# accepted_research_ready=false
# selected_instrument_count=3
# collected_instrument_count=0
# technical_coverage_pass_count=0
# binance_skipped_count=3
# current_universe_caveat=current_public_universe_not_historical_asof

$env:PYTHONPATH='src'; py -3.11 -m tradingbotsuite.v2.cli.main collectors historical-perps --output-root data\research\wpr106_532_autonomous_readiness_strict_free_intake --run-id wpr106-532-daily-top5-public --start-ts 2024-01-01T00:00:00+00:00 --end-ts 2024-02-01T00:00:00+00:00 --timeframe 1d --asof-date 2026-06-25 --max-instruments 5 --max-public-info-pages 20 --binance-timeout 20 --created-by-id WPR106-532
# accepted_research_ready=false
# selected_instrument_count=5
# collected_instrument_count=4
# technical_coverage_pass_count=4
# min_coverage_ratio=1.0
# current_universe_caveat=current_public_universe_not_historical_asof

$env:PYTHONPATH='src'; py -3.11 -m tradingbotsuite.v2.cli.main collectors historical-perps --output-root data\research\wpr106_532_autonomous_readiness_strict_free_intake --run-id wpr106-532-daily-all-current-public-2024-2026 --start-ts 2024-01-01T00:00:00+00:00 --end-ts 2026-06-01T00:00:00+00:00 --timeframe 1d --asof-date 2026-06-25 --max-instruments 0 --max-public-info-pages 20 --binance-timeout 20 --created-by-id WPR106-532
# accepted_research_ready=false
# selected_instrument_count=30
# collected_instrument_count=30
# technical_coverage_pass_count=20
# min_coverage_ratio=0.182539682540
# binance_checked_count=30
# binance_pass_count=29
# binance_warning_count=1
# current_universe_caveat=current_public_universe_not_historical_asof
```

## Manifest Audit

- All three WPR106-532 runs wrote `accepted_research_ready=false`,
  `evidence_mode=sandbox_diagnostic`, and the caveat
  `current_public_universe_not_historical_asof`.
- Each generated universe manifest contains 230
  `universe_mode=current_labeled_sandbox` rows and 0
  `accepted_research_evidence_allowed=true` rows.
- The old 1h BTC/ETH/SOL public attempt collected 0/3 instruments; each
  validation row was skipped with `hyperliquid_candle_window_empty`.
- The broad daily current-public run collected 30/30 selected current eligible
  instruments, but only 20/30 had full technical coverage; all 30 coverage
  rows are `sandbox_diagnostic`.
- The broad daily run produced useful cross-venue Binance sanity metadata
  (29 pass, 1 warning), but the report caveat states that Binance validation is
  not Hyperliquid ground truth.
- Boundary flags remained `research_only=true`, `observe_only=true`, and all
  promotion/candidate/paper/live/order/sizing/runtime flags false.

## Decision

Blocked. Autonomous strict-free downloads can create useful diagnostic
Hyperliquid and external comparison evidence, but the current public sources do
not supply historical as-of Hyperliquid universe snapshots or accepted
historical coverage proof. The downloaded WPR106-532 artifacts therefore cannot
resolve ISSUE-R106-032 or make v2 research-only autonomous strategy readiness
accepted.

## Next Required Packet

Open a later packet only after one of these real source-input paths exists:

- operator-approved ingestion of manifest-backed historical as-of Hyperliquid
  universe snapshots; and
- Hyperliquid-native historical candle records with accepted provenance and
  coverage proof for the selected universe/timeframes; or
- explicit operator approval for quarantined requester-pays official
  Hyperliquid historical sources, including cost acknowledgement, source IDs,
  rollback plan, coverage audit, and boundary validation.

After those inputs exist, rerun the archive-ref bounded loop with
`backtest_data_load`, validation, ledger, Lead Book, final durable audit,
independent audit, authoritative Python 3.11 validation, clean committed/pushed
target state, and zero open P0/P1 blockers.

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
rg -n "candidate_evidence\s*[:=]\s*true|candidate_pack_eligible\s*[:=]\s*true|promotion_ready\s*[:=]\s*true|live_signal\s*[:=]\s*true|paper_signal\s*[:=]\s*true|sizing_instruction\s*[:=]\s*true|order_placement_instruction\s*[:=]\s*true|runtime_mode_change\s*[:=]\s*true" src\tradingbotsuite\v2 docs\work_packets\WPR106-532-v2-autonomous-readiness-strict-free-data-intake.md data\research\wpr106_532_autonomous_readiness_strict_free_intake -g "*.json" -g "*.md"
# no matches
rg -n "tradingbotsuite\.(live|execution|orders|broker)|from\s+tradingbotsuite\.(live|execution|orders|broker)|place_order|submit_order|create_order" src\tradingbotsuite\v2\audit src\tradingbotsuite\v2\autonomy src\tradingbotsuite\v2\collectors src\tradingbotsuite\v2\data_sources src\tradingbotsuite\v2\backtest_data src\tradingbotsuite\v2\validation src\tradingbotsuite\v2\ledger src\tradingbotsuite\v2\lead_book docs\work_packets\WPR106-532-v2-autonomous-readiness-strict-free-data-intake.md
# no matches
rg -n "research_only\s*[:=]\s*false|observe_only\s*[:=]\s*false" src\tradingbotsuite\v2 docs\work_packets\WPR106-532-v2-autonomous-readiness-strict-free-data-intake.md data\research\wpr106_532_autonomous_readiness_strict_free_intake -g "*.json" -g "*.md"
# no matches
```
