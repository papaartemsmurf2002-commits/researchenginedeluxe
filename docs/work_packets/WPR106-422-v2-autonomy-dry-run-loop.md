# WPR106-422 V2 Autonomy Dry-Run Loop

Status: self_checked
Owner: Codex Manager Development Agent
Created: 2026-06-21

## Objective

Add a bounded, fixture-backed v2 autonomy dry-run that exercises the operational
research loop without claiming accepted evidence: universe fixture -> archive
fixture -> coverage fixture -> strategy spec validation -> vectorized backtest
-> validation evidence -> append-only ledger -> Lead Book -> blocker report.

This packet proves wiring and boundary invariants only. It must remain
research-only and sandbox-diagnostic, with no candidate packs, paper/live
signals, sizing instructions, order-placement behavior, runtime-mode changes,
promotion-ready artifacts, or committed generated research evidence.

## Audit IDs

- `V2-AUD-AUTONOMY-001`
- `V2-AUD-LEDGER-002`
- `V2-AUD-LEAD-002`
- `V2-AUD-VALIDATION-003`

## Allowed Paths

- `docs/work_packets/WPR106-422-v2-autonomy-dry-run-loop.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/audit/V2_COMPLETION_AUDIT_ISSUES_AND_HOLES_2026_06_21.md`
- `docs/contracts/autonomy_loop_contract.md`
- `src/tradingbotsuite/v2/autonomy/**`
- `src/tradingbotsuite/v2/cli/main.py`
- `src/tradingbotsuite/v2/config/schemas.py`
- `tests/v2/test_autonomy_phase23.py`

## No-Touch Paths

- `src/**/live/**`
- `src/**/runtime.py`
- `run_live_smoke.py`
- `run_manual.py`
- order-placement adapters, broker helpers, exchange submit helpers
- sizing/runtime configuration paths
- `src/tradingbotsuite/research_artifacts/candidate_pack.py`
- `src/tradingbotsuite/promotion/**`
- `src/tradingbotsuite/live/shadow_loader.py`
- committed generated research evidence under `data/research/**`
- legacy GUI/web/operator source paths
- `src/tradingbot/**`
- `.env`, credential files, local SQLite operator DBs, private caches

## Boundary Constraints

- The autonomy command must be explicitly dry-run and fixture-backed.
- It must not call venue APIs or collectors directly.
- It must log the run through the ledger as `sandbox_diagnostic`, not
  `accepted_research`.
- It must create only caller-specified local output artifacts.
- It must preserve canonical boundary flags:
  `research_only=true`, `observe_only=true`, and every paper/live/order/sizing/
  runtime/promotion/candidate flag false.
- It must report blockers for missing real archive/accepted evidence rather
  than implying autonomous-ready or promotion-ready status.

## Expected Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_autonomy_phase23.py tests\v2\test_cli_smoke.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite
git diff --check
```

The default full contracts lane remains subject to known local Windows socket
exhaustion tracked in `ISSUE-R106-026`.

## Acceptance Criteria

- `redx autonomy dry-run` exists and prints generated manifest, blocker report,
  ledger, and Lead Book paths.
- The dry-run writes an `autonomy_manifest.json` and `blocker_report.json`
  under the requested output root/run ID.
- The manifest records the loop steps, artifacts, decisions, research-only
  boundary flags, and sandbox evidence mode.
- A deterministic 2024+ vectorized backtest run is created from fixture panel
  data with gross/net/cost-stress artifacts.
- The run is appended to a local append-only ledger as `sandbox_diagnostic`.
- A non-promotable Lead Book row is created from the dry-run run manifest.
- The blocker report states that fixture dry-runs are not accepted research
  evidence and that real Hyperliquid archive operation remains required.
- Audit issue status drift in the completion-audit report is corrected.

## Completion Notes

Implemented and self-checked on 2026-06-21.

Changed files stayed inside the declared packet scope.

Changed files:

- `docs/work_packets/WPR106-422-v2-autonomy-dry-run-loop.md`
- `docs/contracts/autonomy_loop_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/audit/V2_COMPLETION_AUDIT_ISSUES_AND_HOLES_2026_06_21.md`
- `src/tradingbotsuite/v2/autonomy/__init__.py`
- `src/tradingbotsuite/v2/autonomy/schemas.py`
- `src/tradingbotsuite/v2/autonomy/runner.py`
- `src/tradingbotsuite/v2/cli/main.py`
- `src/tradingbotsuite/v2/config/schemas.py`
- `tests/v2/test_autonomy_phase23.py`

Decisions made:

- The autonomy loop is a fixture-backed dry-run only and is hard-coded to
  `sandbox_diagnostic` evidence.
- Fixture artifacts are written only under the caller-provided output root and
  are not committed research evidence.
- The dry-run uses existing v2 services for strategy spec validation,
  vectorized backtesting, ledger append, and Lead Book storage.
- The Lead Book row is non-promotable and carries missing real-evidence
  blockers.
- The blocker report always records that fixture dry-runs are not accepted
  research evidence and that real Hyperliquid archive operation remains
  required.
- The completion-audit report now keeps `ISSUE-R106-026` open and
  `ISSUE-R106-020` resolved by WPR106-421.

Acceptance evidence:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_autonomy_phase23.py tests\v2\test_cli_smoke.py -q
# 7 passed

$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
# 177 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 463 passed

git diff --check
# passed with existing LF-to-CRLF warnings only
```

`ISSUE-R106-026` remains open for the separate monolithic full-suite and
Python 3.11 socket-exhaustion certification gap, but the final default-Python
contracts lane passed for this packet.

No accepted-evidence, autonomous-ready, candidate-ready, paper/live signal,
order-placement behavior, sizing instruction, runtime-mode change, generated
committed research evidence, or promotion-ready artifact was created.
