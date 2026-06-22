# WPR106-470 - V2 Public Cycle Universe Mode Fix

Status: self_checked
Audit ID: `V2-AUD-AUTONOMY-016`
Related audit IDs: `V2-AUD-AUTONOMY-009`, `V2-AUD-UNIV-005`

## Objective

Fix the public diagnostic bounded-cycle generator so the generated
`universe_refresh` worker input uses the canonical v2 current-universe sandbox
mode value. WPR106-469 exposed that the spec emitted `mode=current`, which the
universe worker rejects because `UniverseMode` accepts `as_of`,
`current_labeled_sandbox`, or `static_fixture`.

The fix must preserve the diagnostic meaning of the public cycle: current
public universe evidence remains sandbox-only and must not become accepted
as-of research evidence.

## Allowed Paths

- `docs/work_packets/WPR106-470-v2-public-cycle-universe-mode-fix.md`
- `src/tradingbotsuite/v2/autonomy/cycle_public.py`
- `tests/v2/test_autopilot_public_cycle_phase30.py`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## No-Touch Paths

- `src/**/live/**`
- `src/**/runtime.py`
- `run_live_smoke.py`
- `run_manual.py`
- order-placement, broker, exchange-submit, sizing, runtime-config, promotion,
  shadow, and candidate-pack truth-layer paths
- committed `data/research/fixtures/**`
- committed `data/research/historical_cycles/**`
- legacy GUI/operator UI paths
- `src/tradingbot/**`
- `.env`, credential files, local SQLite operator DBs, private caches, and
  unreviewed generated `outputs/**`

## Expected Commands

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_public_cycle_phase30.py -q
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
git diff --check
```

If the fix passes, rerun the WPR106-469 operational smoke from a clean
packet-local generated output root.

## Planned Changed Files

- `docs/work_packets/WPR106-470-v2-public-cycle-universe-mode-fix.md`
- `src/tradingbotsuite/v2/autonomy/cycle_public.py`
- `tests/v2/test_autopilot_public_cycle_phase30.py`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Changed Files

- `docs/work_packets/WPR106-470-v2-public-cycle-universe-mode-fix.md`
- `src/tradingbotsuite/v2/autonomy/cycle_public.py`
- `tests/v2/test_autopilot_public_cycle_phase30.py`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Decisions Made

- Use the existing canonical string `current_labeled_sandbox` rather than
  introducing an alias for `current`. Adding aliases would broaden universe
  mode policy and is outside this bug-fix packet.
- Keep backtest and Lead Book diagnostic labels as `current` or
  `current_public_api_diagnostic` where those schemas already use them as
  sandbox descriptors. The deterministic failure is only in the universe
  worker's `UniverseMode` parsing.

## Acceptance Evidence

- WPR106-469 initial durable runner evidence failed the universe job with
  `job_failed:JOB-wpr106-469-public-cycle-universe:'current' is not a valid
  UniverseMode`.
- `src/tradingbotsuite/v2/autonomy/cycle_public.py` now emits
  `mode=current_labeled_sandbox` for public diagnostic universe refresh jobs.
- `tests/v2/test_autopilot_public_cycle_phase30.py` asserts the generated
  public cycle uses `current_labeled_sandbox`.
- Focused validation passed:
  `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_public_cycle_phase30.py -q`
  (3 passed).
- Final WPR106-469 rerun after this fix executed the universe refresh job
  successfully with `source_mode=public_api`, `instrument_count=230`, and
  `eligible_count=25`, proving the generated mode is accepted by the durable
  worker path while remaining current-sandbox diagnostic evidence.
- Broader validation passed:
  `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_public_cycle_phase30.py tests/v2/test_autopilot_research_cycle_runner_phase27.py -q`
  (11 passed).
- Final validation passed: `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
  (328 passed), `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
  (463 passed), `$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite`
  (passed), and `git diff --check` (passed with expected LF-to-CRLF warnings).
