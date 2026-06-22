# WPR106-469 - V2 Public Diagnostic Cycle Operational Smoke

Status: self_checked
Audit ID: `V2-AUD-AUTONOMY-015`
Related audit IDs: `V2-AUD-AUTONOMY-009`, `V2-AUD-AUTONOMY-006`,
`V2-AUD-COLLECT-003`, `V2-AUD-QUAL-001`, `V2-AUD-BTENG-001`,
`V2-AUD-VAL-003`, `V2-AUD-LEDGER-001`, `V2-AUD-LEAD-001`

## Objective

Run an existing bounded public Hyperliquid diagnostic cycle through the durable
autopilot path: generate a public candle cycle spec, enqueue it, execute it
through durable workers, and record the exact pass/blocker evidence. This
packet verifies real operational wiring beyond the single universe refresh
smoke while keeping all generated venue/archive/job/ledger/Lead Book artifacts
under ignored local `data/research/wpr106_469_public_diagnostic_cycle/`
storage.

This packet must not claim accepted research evidence. Public current-universe
and public recent-window outputs remain `sandbox_diagnostic`, current-biased,
and non-promotable until a later as-of historical coverage packet proves the
accepted evidence requirements.

## Allowed Paths

- `docs/work_packets/WPR106-469-v2-public-diagnostic-cycle-operational-smoke.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- ignored local generated evidence under
  `data/research/wpr106_469_public_diagnostic_cycle/**`

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

Generate the public diagnostic cycle spec:

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.v2.cli.main autopilot public-candle-cycle-spec --output-root data/research/wpr106_469_public_diagnostic_cycle --run-id wpr106-469-public-cycle --instrument-id hyperliquid:perp:BTC --coin BTC --timeframe 1d --start-ts 2024-01-01T00:00:00+00:00 --end-ts 2024-08-01T00:00:00+00:00 --asof-date 2026-06-22 --created-by-id codex-manager-agent
```

Plan and enqueue the cycle:

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.v2.cli.main autopilot research-cycle --mode bounded --cycle-spec-file data/research/wpr106_469_public_diagnostic_cycle/wpr106-469-public-cycle/cycle_spec.json --output-root data/research/wpr106_469_public_diagnostic_cycle/wpr106-469-public-cycle/plans --job-store data/research/wpr106_469_public_diagnostic_cycle/wpr106-469-public-cycle/jobs.sqlite --enqueue
```

Run the enqueued bounded cycle:

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.v2.cli.main autopilot run-cycle-plan --plan-manifest <plan_manifest_path> --worker-id wpr106-469-public-cycle-runner --max-jobs 10
```

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_public_cycle_phase30.py tests/v2/test_autopilot_research_cycle_runner_phase27.py -q
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
git diff --check
```

## Planned Changed Files

- `docs/work_packets/WPR106-469-v2-public-diagnostic-cycle-operational-smoke.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Changed Files

- `docs/work_packets/WPR106-469-v2-public-diagnostic-cycle-operational-smoke.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Decisions Made

- This is an operational smoke, not a new implementation path. Existing public
  cycle, planner, runner, worker, archive, coverage, backtest, validation,
  ledger, Lead Book, and audit surfaces are used without source changes unless
  the smoke exposes a concrete bug that must be fixed in a separate scoped
  packet.
- Generated public venue data, worker state, run artifacts, ledger rows, and
  Lead Book rows stay in the ignored packet-local `data/research/` path and
  are not committed.
- The cycle uses `timeframe=1d` from 2024-01-01 through 2024-08-01 so the
  diagnostic run can exercise the six-month machinery without pretending this
  is accepted historical evidence.
- Network or endpoint failures are recorded as operational blockers, not as
  source-code failures, unless they reveal a deterministic local contract bug.
- The first smoke exposed a deterministic public-cycle universe-mode bug
  (`mode=current`) and the second smoke exposed a deterministic ledger
  validation-propagation bug. Those source fixes were handled in WPR106-470 and
  WPR106-471 before this packet accepted final operational evidence.

## Acceptance Evidence

- Initial generated public cycle spec succeeded, but the first durable runner
  pass completed with blockers after the universe job failed:
  `job_failed:JOB-wpr106-469-public-cycle-universe:'current' is not a valid
  UniverseMode`.
- After WPR106-470, the public cycle executed all 9 durable jobs, but WPR106-471
  was opened because the validation gate manifest correctly reported
  `validation_status=fail` and `cost_dependent_failure` while the ledger row
  still recorded `validation_status=pass`.
- Final fresh rerun after WPR106-471 used ignored output root
  `data/research/wpr106_469_public_diagnostic_cycle/rerun_after_wpr106_471/`
  and run ID `wpr106-469-public-cycle-ledger-fix`.
- Final spec evidence: `declared_job_count=8`, `declared_binding_count=10`,
  `source_mode=public_api`, `evidence_mode=sandbox_diagnostic`,
  `accepted_research_ready=false`, `promotion_ready=false`, and expected
  blockers for current public universe, recent public window, missing accepted
  historical coverage proof, independent completion audit, and authoritative
  full-suite validation.
- Final plan evidence: plan ID
  `665369065863b7b39962a47e8e0a5ca072388a331eeb826673537dd24ca6895b`,
  `planned_job_count=9`, `enqueued_job_count=9`, audit job
  `JOB-wpr106-469-public-cycle-ledger-fix-audit`.
- Final execution evidence: execution ID
  `55dd870d7433806c6419ce5bcf1569babcdfb51901c2021a4d108f26686f433e`,
  `status=completed_with_blockers`, `executed_job_count=9`,
  `skipped_job_count=0`, `audit_attempted=true`, `blocker_count=15`.
- Public universe evidence: `source_mode=public_api`, `instrument_count=230`,
  `eligible_count=25`, universe snapshot
  `b2e279db73109ebe65f5a074149ae5435d4ae7dab69ce03c6fb025d7de7437ba`, raw
  file ID `30a391aa793e2b9137cf5ff0908e61df496ca8c9c05a40ead1948a0e54e7f33f`.
- Public candle evidence: `row_count=214`, `api_row_count=214`,
  `api_page_count=1`, archive snapshot
  `b9540d6f5527e7464cd3728920357eefba4bf6a555cde45271cc2a9703e668cb`,
  coverage report `e387a4ed18bf3fd807efc72f2a2e030192078a5a0b1af2dd49ce21eeb87f2ea8`,
  raw file ID `259576a492d526cfe0df7abac8112d0e6e4e5fc2ed7f79a390dec4bf9a575464`.
- Coverage evidence: 25 eligible instruments audited, 0 evidence-eligible
  instruments, 25 blocked instruments, blockers
  `missing_silver_bars_file,sandbox_diagnostic_non_evidence`.
- Backtest evidence: run manifest SHA-256
  `b783caedb4f3d47141a9340616e76d2c46be4c8c77f62a1811470aaec6fc45ec`,
  `gross_return=0.011152825110`, `net_return=0.001322349454`.
- Validation/ledger evidence: validation gate manifest status `fail` with
  blocker `cost_dependent_failure`, SHA-256
  `45e8b6bb392ddbc800616f34d69c066acafa52d5d4e81590683195047ec6ba16`; the
  ledger row now records `validation_status=fail`, `walk_forward_pass=false`,
  `cost_fragile_warning=true`, and blocker reasons
  `validation_status_fail,cost_dependent_failure`.
- Lead Book/audit evidence: Lead ID `LEAD-0657e798229aac12`, `state=idea_only`,
  `promotion_ready=false`, `candidate_evidence=false`; audit report SHA-256
  `754b38b810be53a79c6ec0bf14347b744fb997f195a7f0f1080035d060bd2d54` and
  final blockers include public current-universe/recent-window non-evidence,
  missing accepted historical coverage/as-of/independent/full-suite evidence,
  `cost_dependent_failure`, `validation_status_fail`, minimum trade-frequency,
  and minimum six-month failures.
- Validation commands passed:
  `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_ledger_phase13.py tests/v2/test_workers_phase7.py -q`
  (64 passed) and
  `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_public_cycle_phase30.py tests/v2/test_autopilot_research_cycle_runner_phase27.py -q`
  (11 passed).
- Broader validation passed: `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
  (328 passed), `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
  (463 passed), `$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite`
  (passed), and `git diff --check` (passed with expected LF-to-CRLF warnings).
