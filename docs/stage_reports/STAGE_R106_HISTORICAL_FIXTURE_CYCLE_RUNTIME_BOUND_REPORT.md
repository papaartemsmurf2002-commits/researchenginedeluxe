# Stage R106 Historical Fixture Cycle Runtime Bound Report

## Summary

WPR106-383 repairs the broad-suite validation timeout discovered after the
sandbox publication-coherence packets. The timeout was localized to historical
fixture tests that executed production-sized checked-in research-cycle specs as
normal suite fixtures.

The packet keeps the tests' source-contract assertions over the checked-in
configs, but runs bounded tmp copies for execution. The BTC full-cycle fixture
smoke now keeps the checked-in fixture manifest and synthetic-fallback
assertions while limiting execution to one feature set, one holding window, two
strategies, one metadata candidate, one refinement, and CPU-only compute. The
BTC/ETH perp-context fixture smokes keep all declared strategies and exit
policies while limiting execution to one holding window, default-seed
candidates only, one refinement, and CPU-only compute.

## Why This Path

Changing production candidate generation would have mixed validation ergonomics
with research behavior. The checked-in configs are intentionally broad
production/research specs; the tests only need to prove fixture-pack intake,
context feature materialization, strategy/exit declaration handling, and
fail-closed candidate-pack behavior. Bounding the tmp execution specs preserves
those contracts without weakening candidate gates or changing runtime behavior.

## Implemented

- Bounded `test_checked_in_full_cycle_config_consumes_btcusdt_fixture_pack` by
  executing a tmp copy of `full_cycle_btc_v1.json`.
- Bounded BTC and ETH perp-context fixture smokes by executing tmp copies with
  one holding window and metadata search disabled.
- Preserved direct assertions that the checked-in configs point at the expected
  checked-in fixture manifests and disable synthetic fallback.
- Preserved assertions that historical-cycle outputs remain non-promotable and
  candidate-pack writes remain false where covered by these tests.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_local_fixture_pack.py::test_checked_in_full_cycle_config_consumes_btcusdt_fixture_pack -q -p no:cacheprovider
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_local_fixture_pack.py::test_checked_in_perp_context_v2_cycle_consumes_provider_context_fixture tests\historical\test_full_cycle_local_fixture_pack.py::test_checked_in_eth_perp_context_v2_cycle_consumes_provider_context_fixture -q -p no:cacheprovider
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_local_fixture_pack.py -q -p no:cacheprovider
$env:PYTHONPATH='src'; python -m pytest tests\historical -q -p no:cacheprovider
$env:PYTHONPATH='src'; python -m pytest tests\backtesting tests\features tests\historical tests\integration -q -p no:cacheprovider
$env:PYTHONPATH='src'; python -m pytest tests\live tests\optimization tests\research_artifacts tests\research_cycle tests\research_discovery -q -p no:cacheprovider
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox tests\tradingbotsuite tests\unit -q -p no:cacheprovider
$env:PYTHONPATH='src'; python -m pytest -q -p no:cacheprovider
```

Results:

- Focused BTC fixture smoke: 1 passed in 1.26 seconds.
- BTC/ETH perp-context fixture smokes: 2 passed in 17.71 seconds.
- Full historical fixture-pack file: 12 passed in 41.86 seconds.
- Historical directory: 50 passed in 161.79 seconds.
- Original timed-out grouped slice: 213 passed, 1 skipped in 171.59 seconds.
- Live/optimization/research grouped slice: 440 passed in 116.64 seconds.
- Sandbox/package/unit grouped slice: 629 passed with 2 warnings in
  231.59 seconds.
- Full suite: 1890 passed, 1 skipped, 1 XGBoost device warning in
  559.03 seconds.

## Boundary Confirmation

This packet changes tests only. It does not change production research-cycle
candidate generation, strict validation, candidate-pack gates, sandbox artifact
semantics, live/paper behavior, sizing, order placement, runtime-mode behavior,
live-configuration writes, candidate-evidence claims, or promotion state.
