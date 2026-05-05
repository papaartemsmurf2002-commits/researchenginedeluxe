# Stage R64 Checked Liquidation Fixture Evidence Report

Date: 2026-05-05
Work packet: `docs/work_packets/WPR64-01-checked-liquidation-fixture-evidence.md`

## Summary

R64 adds checked BTCUSDT liquidation fixture evidence from Crypto Lake anonymous
free-sample data. The fixture combines matching 2023-02-01 BTC-USDT-PERP 1m
candles and liquidation rows into a research-only fixture pack with an optional
`liquidation` context family.

The fixture-pack builder now preserves Crypto Lake free-sample metadata on the
primary source block as well as the optional context block, so consumers that
inspect only the fixture source still see diagnostic-only provenance.

This stage does not implement `liquidation_absorption_classifier_v1`, does not
wire liquidation features into checked BTCUSDT/ETHUSDT provider-cycle configs,
does not create candidate-pack eligibility, and does not change promotion or
live behavior.

## Evidence

- Candle source: Crypto Lake free-sample `candles`, `BINANCE_FUTURES`,
  `BTC-USDT-PERP`, 2023-02-01 to 2023-02-02.
- Candle fetch result: 1,441 source rows, 0 gaps, 0 duplicates.
- Liquidation source: Crypto Lake free-sample `liquidations`,
  `BINANCE_FUTURES`, `BTC-USDT-PERP`, 2023-02-01 to 2023-02-02.
- Liquidation fetch result: 1,162 source rows.
- Checked fixture:
  `data/research/fixtures/btcusdt_liquidation_free_sample_v1/fixture_pack_manifest.json`.
- Fixture manifest hash:
  `1e237d15bbd4a84987f2b81344cc32a957c94cb6ed597d3e5b38bbc47304cc83`.
- Fixture primary bars: 1,440 rows.
- Fixture liquidation context rows: 1,162 rows.

## Provenance And Limits

The fixture manifest preserves:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- `source_access_mode: free_sample`
- `coverage_scope: free_sample_diagnostic`
- `free_sample_data: true`
- `diagnostic_only: true`
- `context_family_role: perp_context`

The primary kline source block also preserves `source_access_mode: free_sample`,
`coverage_scope: free_sample_diagnostic`, `free_sample_data: true`, and
`diagnostic_only: true`.

This is checked local fixture evidence for development and contract validation.
It is not broad historical coverage, OOS/stress acceptance evidence,
candidate-pack eligibility, a performance claim, promotion evidence, or live
signal evidence.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
```

Passed.

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_historical_fixture_pack_contract.py tests\features -q
```

Passed: 53 passed.

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Passed: 337 passed.

## Next Gate

The liquidation classifier can now be implemented in a separate packet using
the checked fixture for local contract tests. Checked BTCUSDT/ETHUSDT
provider-cycle wiring should still be separate from classifier implementation
and must preserve fail-closed research gates.
