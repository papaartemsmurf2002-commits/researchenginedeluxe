# WPR106-423 V2 Archive-Backed Autonomy Dry-Run

Status: self_checked
Owner: Codex Manager Development Agent
Created: 2026-06-21

## Objective

Upgrade the v2 autonomy dry-run from manifest stubs to an archive-backed local
fixture path by default. The loop must create a real local archive root,
write silver bar rows through the archive writer, write a coverage report and
archive snapshot, refresh a fixture Hyperliquid as-of universe, load the panel
through `BacktestDataService`, then run the existing spec/backtest/ledger/Lead
Book/blocker-report flow.

This remains a dry-run and must stay `sandbox_diagnostic`; fixture archive
output is not accepted research evidence.

## Audit IDs

- `V2-AUD-AUTONOMY-002`
- `V2-AUD-ARCH-006`
- `V2-AUD-BTDATA-002`
- `V2-AUD-VALIDATION-004`

## Allowed Paths

- `docs/work_packets/WPR106-423-v2-archive-backed-autonomy-dry-run.md`
- `docs/contracts/autonomy_loop_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `src/tradingbotsuite/v2/autonomy/**`
- `src/tradingbotsuite/v2/cli/main.py`
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

- No venue/API call is allowed; all archive/universe inputs must be local
  fixtures.
- Backtest-data manifests for the autonomy dry-run must stay
  `sandbox_diagnostic`.
- The autonomy runner may explicitly check 2024+, six usable months, 0.98
  coverage, and as-of universe facts, but it must not mark fixture output as
  accepted evidence.
- The existing manifest-fixture mode may remain as a compatibility path, but
  the default CLI path should prove real archive/backtest-data service wiring.
- No generated dry-run artifacts may be committed.

## Expected Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_autonomy_phase23.py tests\v2\test_backtest_data_phase9.py tests\v2\test_cli_smoke.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

## Acceptance Criteria

- `redx autonomy dry-run` uses the archive-backed local fixture mode by default.
- The dry-run writes a local archive root under the requested output root.
- The archive root contains a silver bars file, coverage manifest, archive
  snapshot manifest, universe snapshot manifest, and backtest-data request
  manifest.
- `BacktestDataService` supplies the backtest panel from the archive snapshot.
- The autonomy manifest includes a `backtest_data_preflight` step.
- The dry-run still appends the ledger row as `sandbox_diagnostic` and creates
  only non-promotable Lead Book rows.
- The blocker report still says fixture output is not accepted research
  evidence and real Hyperliquid archive operation remains required.
- Existing WPR106-422 manifest-fixture behavior remains available through an
  explicit data-mode option.

## Completion Notes

Implemented and self-checked on 2026-06-21.

Changed files stayed inside the declared packet scope.

Changed files:

- `docs/work_packets/WPR106-423-v2-archive-backed-autonomy-dry-run.md`
- `docs/contracts/autonomy_loop_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `src/tradingbotsuite/v2/autonomy/__init__.py`
- `src/tradingbotsuite/v2/autonomy/schemas.py`
- `src/tradingbotsuite/v2/autonomy/runner.py`
- `src/tradingbotsuite/v2/cli/main.py`
- `tests/v2/test_autonomy_phase23.py`

Decisions made:

- `archive_fixture` is now the default autonomy dry-run data mode.
- `manifest_fixture` remains available explicitly for the WPR106-422 compact
  fixture path.
- The archive-backed path writes a local archive root under the requested
  output root and uses existing archive, universe, coverage, and
  `BacktestDataService` code.
- The backtest-data request and generated data manifest remain
  `sandbox_diagnostic`.
- The autonomy runner checks the fixture facts needed for the product loop
  without marking fixture output as accepted research evidence.

Acceptance evidence:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_autonomy_phase23.py tests\v2\test_backtest_data_phase9.py tests\v2\test_cli_smoke.py -q
# 17 passed

$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
# 178 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 463 passed

git diff --check
# passed with existing LF-to-CRLF warnings only
```

No venue/API fetch, accepted-evidence artifact, autonomous-ready claim,
candidate-ready claim, paper/live signal, order-placement behavior, sizing
instruction, runtime-mode change, committed generated research evidence, or
promotion-ready artifact was created.
