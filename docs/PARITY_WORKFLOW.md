# Parity Workflow

## Fixture Contract

Every TradingView export used for parity must record:

- source symbol and timeframe
- chart settings and loaded history
- feature list and parameters
- neighbor count and max bars back
- kernel parameters and smoothing state
- filter state
- whether the newest candle is included

Do not treat marker-only exports as proof of source parity. They are useful for final visual validation, not for diagnosing feature or ANN drift.

## Recommended Order

1. Validate kernel parity.
2. Validate feature parity with diagnostic exports.
3. Validate ANN diagnostics: prediction, accepted count, and neighbor tail indexes.
4. Validate signal state.
5. Validate Buy/Sell markers.

## Current Full-History Check

Profile:

```text
examples/btc_lc_close_10_6000.yaml
```

Export:

```text
C:\Users\papaa\Downloads\BINANCE_BTCUSDT.P, 15 (21).csv
```

Kernel:

```powershell
python -m tradingbot.cli parity-check --config examples\btc_lc_close_10_6000.yaml --symbol BTC --base-csv "C:\Users\papaa\Downloads\BINANCE_BTCUSDT.P, 15 (21).csv" --tv-export "C:\Users\papaa\Downloads\BINANCE_BTCUSDT.P, 15 (21).csv" --columns kernel --skip-rows 26 --tolerance 0.01 --kernel-preflight --exclude-last-bar
```

Entries:

```powershell
python -m tradingbot.cli entry-parity --config examples\btc_lc_close_10_6000.yaml --symbol BTC --base-csv "C:\Users\papaa\Downloads\BINANCE_BTCUSDT.P, 15 (21).csv" --tv-export "C:\Users\papaa\Downloads\BINANCE_BTCUSDT.P, 15 (21).csv" --mode full --tolerance-bars 1 --no-hypotheses
```

Expected marker result:

```text
407/407 within one bar
```

## Diagnostic Export Scripts

- `docs/lc_lorentzian_diagnostic_core_export.pine`
- `docs/lc_lorentzian_diagnostic_ann_export.pine`
- `docs/lc_lorentzian_diagnostic_export.pine`

Use the split scripts when TradingView plot limits block a single export.

Merge split exports:

```powershell
python -m tradingbot.cli merge-tv-exports --input "C:\path\core.csv" --input "C:\path\ann.csv" --output data\parity\merged_diagnostics.csv
```

Generated exports and merged CSVs are local artifacts and should not be committed.
