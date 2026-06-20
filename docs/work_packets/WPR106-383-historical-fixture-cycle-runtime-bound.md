# WPR106-383 - Historical Fixture Cycle Runtime Bound

## Status

closed

## Objective

Repair the broad-suite validation timeout caused by
`test_checked_in_full_cycle_config_consumes_btcusdt_fixture_pack` executing the
production BTC full-cycle research spec as a normal fixture test. Preserve the
test's actual contract, which is checked-in fixture-pack data-source handling
without synthetic fallback, while bounding candidate search and compute in a
tmp spec.

## Dependencies

- `RAPID_STRATEGY_SANDBOX_AUDIT.md`
- `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md`
- `docs/work_packets/WPR106-382-sandbox-cli-publication-coherence.md`

## Allowed paths

- `tests/historical/test_full_cycle_local_fixture_pack.py`
- `docs/work_packets/WPR106-383-historical-fixture-cycle-runtime-bound.md`
- `docs/stage_reports/STAGE_R106_HISTORICAL_FIXTURE_CYCLE_RUNTIME_BOUND_REPORT.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Boundary constraints

- Do not change historical research-cycle production behavior in this packet.
- Do not change strategy parameter metadata, candidate gates, validation floors,
  candidate-pack behavior, sandbox code, live/paper behavior, sizing, order
  placement, runtime mode, or live configuration.
- The bounded test must still consume the checked-in BTC fixture-pack manifest
  path from `configs/research/full_cycle_btc_v1.json`.
- The bounded test must not use synthetic fixtures or claim candidate evidence.

## Acceptance criteria

- The historical fixture test no longer executes the full production candidate
  grid.
- The checked-in spec assertions still prove the repository config points at
  the checked-in BTC fixture pack and disables synthetic fallback.
- The cycle execution uses a tmp spec with explicit small candidate/compute
  bounds.
- Focused historical validation and staged diff hygiene pass.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_local_fixture_pack.py::test_checked_in_full_cycle_config_consumes_btcusdt_fixture_pack -q -p no:cacheprovider
$env:PYTHONPATH='src'; python -m pytest tests\historical -q -p no:cacheprovider
git diff --cached --check
```

Exit evidence:

- Previously hanging focused BTC fixture smoke passed:
  `$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_local_fixture_pack.py::test_checked_in_full_cycle_config_consumes_btcusdt_fixture_pack -q -p no:cacheprovider`
  with 1 test in 1.26 seconds.
- Bounded BTC/ETH perp-context fixture smokes passed:
  `$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_local_fixture_pack.py::test_checked_in_perp_context_v2_cycle_consumes_provider_context_fixture tests\historical\test_full_cycle_local_fixture_pack.py::test_checked_in_eth_perp_context_v2_cycle_consumes_provider_context_fixture -q -p no:cacheprovider`
  with 2 tests in 17.71 seconds.
- Full historical fixture-pack file passed:
  `$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_local_fixture_pack.py -q -p no:cacheprovider`
  with 12 tests in 41.86 seconds.
- Full historical directory passed:
  `$env:PYTHONPATH='src'; python -m pytest tests\historical -q -p no:cacheprovider`
  with 50 tests in 161.79 seconds.
- Original timed-out grouped slice passed:
  `$env:PYTHONPATH='src'; python -m pytest tests\backtesting tests\features tests\historical tests\integration -q -p no:cacheprovider`
  with 213 tests and 1 skipped in 171.59 seconds.
- Full suite passed:
  `$env:PYTHONPATH='src'; python -m pytest -q -p no:cacheprovider`
  with 1890 tests, 1 skipped, and 1 XGBoost device warning in 559.03 seconds.

## Stop conditions

- Fix requires changing production candidate generation or candidate gates.
- The test can pass only by switching to synthetic fixtures.
- The test stops asserting the checked-in fixture-pack source contract.
