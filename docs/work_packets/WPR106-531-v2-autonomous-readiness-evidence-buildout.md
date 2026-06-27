# WPR106-531 - V2 Autonomous Readiness Evidence Buildout

Status: blocked
Owner: Codex Research Agent
Date: 2026-06-25

## Objective

Attempt to make v2 research-only autonomous strategy readiness pass by
producing or wiring real accepted bounded-loop evidence, but only if the
required real inputs exist. Do not weaken readiness gates, relabel diagnostic
evidence, fabricate historical data, or accept fixture, sandbox,
public-current, synthetic, or supplied-ref machinery evidence.

If the required real historical as-of Hyperliquid evidence is not available,
close this packet as blocked with the exact external inputs and next packet
required.

## Allowed Paths

- `docs/work_packets/WPR106-531-v2-autonomous-readiness-evidence-buildout.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/contracts/autonomous_readiness_contract.md`
- `src/tradingbotsuite/v2/audit/readiness.py`
- `src/tradingbotsuite/v2/autonomy/cycle_archive.py`
- `src/tradingbotsuite/v2/autonomy/cycle_planner.py`
- `src/tradingbotsuite/v2/autonomy/cycle_runner.py`
- `src/tradingbotsuite/v2/backtest_data/jobs.py`
- `src/tradingbotsuite/v2/validation/jobs.py`
- `src/tradingbotsuite/v2/ledger/jobs.py`
- `src/tradingbotsuite/v2/lead_book/jobs.py`
- `src/tradingbotsuite/v2/cli/main.py`
- `tests/v2/test_autonomous_readiness_audit_phase29.py`
- `tests/v2/test_autopilot_archive_cycle_phase75.py`
- `tests/v2/test_autopilot_research_cycle_phase26.py`
- `tests/v2/test_autopilot_research_cycle_runner_phase27.py`
- `tests/v2/test_autopilot_fixture_cycle_phase28.py`
- `tests/v2/test_autopilot_public_cycle_phase30.py`
- `tests/v2/test_validation_worker_phase32.py`
- `tests/v2/test_workers_phase7.py`
- New generated evidence only under
  `data/research/wpr106_531_autonomous_readiness_evidence/**` if all source
  inputs satisfy accepted-evidence requirements before the bounded loop runs.

## No-Touch Paths

- Live runtime, order-placement, broker/execution, sizing, runtime config,
  promotion, shadow, and candidate-pack truth-layer paths.
- Legacy GUI paths.
- Existing generated research evidence under `data/research/**`, except the
  WPR106-531 output root above.
- Secrets, `.env`, credential files, private caches, local SQLite operator
  databases, and generated `outputs/**`.
- Existing WPR106-527 through WPR106-530 changes except where the current
  evidence buildout directly requires a scoped update.

## Required Boundary

All artifacts must preserve:

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

- Search the current worktree and local generated evidence for trusted
  historical Hyperliquid-native candle records, historical as-of universe
  snapshots, accepted archive snapshots, accepted coverage, backtest-data
  manifests, strategy queue refs, validation pass refs, ledger/Lead Book refs,
  independent audit evidence, and authoritative Python 3.11 validation.
- If valid source inputs exist, run the existing archive-ref bounded cycle into
  `data/research/wpr106_531_autonomous_readiness_evidence/**`, then run the
  autonomous readiness manager over the produced evidence.
- If source inputs are missing or only diagnostic/current/sandbox evidence is
  available, update this packet and `docs/KNOWN_ISSUES.md` as blocked.
- Do not change live/order/sizing/runtime/promotion/candidate-pack behavior.

## Findings

WPR106-531 did not generate new readiness evidence. The current worktree has
Hyperliquid candle material under the WPR106-473 operator historical dataset
runs, but the associated manifests are not accepted autonomous-readiness
inputs:

- 11 inspected `universe_snapshots.parquet` files under the current local
  Hyperliquid evidence roots all contain 230 rows of
  `universe_mode=current_labeled_sandbox` with
  `accepted_research_evidence_allowed=false`. No historical `as_of` accepted
  universe row is present.
- WPR106-473 historical dataset runs contain Hyperliquid raw/bronze/silver
  candle parquet and compressed raw payloads, but their coverage manifests are
  `evidence_mode=sandbox_diagnostic`, and their reports remain
  `accepted_research_ready=false`.
- The largest local Hyperliquid daily operator run,
  `data/research/operator_runs/v2_historical_dataset/wpr106-473-top25c-1d-2024-2026`,
  has 25 coverage rows, all `sandbox_diagnostic`; 14 rows have full coverage
  and the minimum coverage ratio is `0.18253968253968253`.
- The WPR106-469 public diagnostic cycle roots include nonempty ledger and
  Lead Book outputs, but the backtest-data request rows and ledger rows remain
  `evidence_mode=sandbox_diagnostic`; the Lead Book rows remain `idea_only`;
  the latest cycle remains public/current-window diagnostic evidence and not
  accepted historical as-of evidence.
- The WPR106-468 public universe refresh is a current public snapshot labeled
  `current_labeled_sandbox`; it cannot be relabeled into historical as-of
  evidence.
- No local trusted historical as-of Hyperliquid universe snapshot with accepted
  evidence provenance was found. Running the archive-ref bounded cycle with
  the current inputs would only repackage fixture, sandbox, current-window, or
  supplied-ref machinery evidence, which this packet explicitly forbids.

## Decision

Blocked. ISSUE-R106-032 cannot be resolved from the current worktree without
weakening the autonomous readiness contract or fabricating evidence. No
candidate pack, accepted research readiness, autonomous strategy readiness,
paper/live signal, order placement, sizing instruction, runtime-mode change,
promotion behavior, or production trading readiness was introduced.

## Next Required Packet

Open WPR106-532 to ingest and audit real accepted autonomous-readiness inputs:

- manifest-backed historical as-of Hyperliquid universe snapshots for the
  selected research dates, with source provenance, hashes, and accepted
  evidence policy review;
- Hyperliquid-native historical candle records for the selected v2 universe and
  timeframes, covering the strategy validation window with accepted coverage
  manifests and backtest-data manifests;
- a bounded archive-ref cycle that includes `universe_refresh`,
  `archive_snapshot`, `coverage_audit`, `backtest_data_load`,
  `strategy_queue_scan`, `vectorized_backtest`, `validation_gate`,
  `ledger_append_export`, `lead_book_upsert`, and `audit_check`, in order;
- validation-gate pass refs, nonempty append-only ledger and Lead Book refs,
  passing final durable audit evidence, independent audit evidence,
  authoritative Python 3.11 validation, clean committed/pushed target state,
  and zero open P0/P1 blockers.

## Expected Validation

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2/test_autonomous_readiness_audit_phase29.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2/test_autopilot_archive_cycle_phase75.py tests/v2/test_validation_worker_phase32.py tests/v2/test_workers_phase7.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/contracts -q
git diff --check
rg boundary scans for forbidden live/order/sizing/runtime/promotion/candidate-pack drift
```

## Validation

Passed:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2/test_autonomous_readiness_audit_phase29.py -q
# 8 passed, 1 warning
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2/test_autopilot_archive_cycle_phase75.py tests/v2/test_validation_worker_phase32.py tests/v2/test_workers_phase7.py -q
# 66 passed, 1 warning
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/contracts -q
# 463 passed, 1 warning
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2 -q
# 552 passed, 1 warning
$env:PYTHONPATH='src'; py -3.11 -m pytest tests -q
# 2459 passed, 2 skipped, 6 warnings
git diff --check
# passed; Git reported LF-to-CRLF working-copy warnings only
```

Boundary scans:

```powershell
rg -n "candidate_evidence\s*[:=]\s*true|candidate_pack_eligible\s*[:=]\s*true|promotion_ready\s*[:=]\s*true|live_signal\s*[:=]\s*true|paper_signal\s*[:=]\s*true|sizing_instruction\s*[:=]\s*true|order_placement_instruction\s*[:=]\s*true|runtime_mode_change\s*[:=]\s*true" src\tradingbotsuite\v2 docs\work_packets\WPR106-531-v2-autonomous-readiness-evidence-buildout.md
# no matches
rg -n "tradingbotsuite\.(live|execution|orders|broker)|from\s+tradingbotsuite\.(live|execution|orders|broker)|place_order|submit_order|create_order" src\tradingbotsuite\v2\audit src\tradingbotsuite\v2\autonomy src\tradingbotsuite\v2\backtest_data src\tradingbotsuite\v2\validation src\tradingbotsuite\v2\ledger src\tradingbotsuite\v2\lead_book
# no matches
rg -n "research_only\s*[:=]\s*false|observe_only\s*[:=]\s*false" src\tradingbotsuite\v2 docs\work_packets\WPR106-531-v2-autonomous-readiness-evidence-buildout.md
# no matches
```
