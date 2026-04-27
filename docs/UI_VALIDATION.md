# UI Validation

The UI is a local manual validation tool for TradingView exports.

Start it with an explicit export:

```powershell
python -m tradingbot.cli serve-ui --config examples\btc_lc_close_10_6000.yaml --symbol BTC --csv "C:\Users\papaa\Downloads\BINANCE_BTCUSDT.P, 15 (21).csv"
```

## Visual Encoding

- Blue upward triangle: Python simulated long entry.
- Blue downward triangle: Python simulated short entry.
- Yellow diamond: TradingView exported `Buy` or `Sell` marker.
- Blue line: Python kernel estimate.
- Yellow dashed line: TradingView kernel estimate.
- Purple dashed line: max-bars-back boundary for the compared closed-bar window.

## Defaults

- The newest candle is excluded by default.
- Tolerance defaults to `1` bar.
- The chart uses the full export window.
- The settings panel can override config values for one validation run.

The UI does not persist settings. To make a setting permanent, edit the YAML profile.

## What To Accept

For marker-only exports, accept `100%` within one bar when:

- kernel parity is exact after warmup;
- Python and TradingView entry counts match;
- exact mismatches are isolated to the max-bars-back boundary or known live-bar capture timing.

For deeper correctness, use the diagnostic Pine exports and compare feature, ANN, and signal columns before marker checks.
