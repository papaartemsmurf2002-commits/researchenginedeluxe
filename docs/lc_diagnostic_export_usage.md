# LC Diagnostic Export Usage

Use these scripts when marker-only exports stop being enough.

Each script is a copy of the original Lorentzian Classification Pine source with the calculation logic kept intact and CSV diagnostics added. The scripts disable redundant visual `plot`, `plotshape`, `barcolor`, `alertcondition`, label, and backtest stream output so the diagnostic columns stay within TradingView's 64-plot limit.

## Which Script To Use

- `docs/lc_lorentzian_diagnostic_core_export.pine`: feature, kernel, signal, marker, filter, and trade-stat diagnostics. Use this first.
- `docs/lc_lorentzian_diagnostic_ann_export.pine`: ANN window and neighbor-tail diagnostics. Use this with the core export when kernel/features match but markers do not.
- `docs/lc_lorentzian_diagnostic_export.pine`: single-file essential export. It is useful for quick checks, but the two-script workflow is preferred because it leaves more plot-budget headroom.

## TradingView Steps

1. Open the same symbol, exchange, timeframe, chart history, and LC settings used by the Python config.
2. Paste `docs/lc_lorentzian_diagnostic_core_export.pine` into Pine Editor.
3. Apply it to the chart.
4. Export chart data.
5. Repeat with `docs/lc_lorentzian_diagnostic_ann_export.pine`.
6. Merge the two exports:

```powershell
python -m tradingbot.cli merge-tv-exports --input "C:\path\to\core.csv" --input "C:\path\to\ann.csv" --output data\parity\tv_lc_merged_diagnostics.csv
```

7. Use the merged CSV as `--tv-export` in `parity-check` or `entry-parity`.

## Required 2k Settings

- Source: `close`
- Neighbors: `10`
- Max bars back: `2000`
- Features: `RSI 14/1`, `WT 10/11`, `CCI 23/1`, `ADX 20/1`, `RSI 9/1`
- Kernel: `8 / 8 / 25`, lag `2`
- Filters and dynamic exits: off

## Diagnostic Columns

The merged two-script export includes:

- Feature state: `f1..f5`, `y_train`
- Kernel state: `yhat1`, `yhat2`, `isBullish`, `isBearish`, `alertBullish`, `alertBearish`
- Signal state: `prediction`, `signal`, `barsHeld`, `signalChange`, `isNewBuySignal`, `isNewSellSignal`
- Entry/exit state: `startLongTrade`, `startShortTrade`, `endLongTrade`, `endShortTrade`
- ANN window state: `barIndex`, `lastBarIndex`, `maxBarsBackIndex`, `annWindowStart`, `annWindowEnd`, `annConsideredCount`, `annAcceptedCount`
- Neighbor tail state: `neighborIndexTail0..9`, `neighborLabelTail0..9`, `neighborDistanceTail0..9`

The decisive parity check is `--columns features,ann,signals`. If `f1..f5` match but `neighborIndexTail*` differs, the bug is ANN history/index alignment. If the neighbor indices match but labels or distances differ, the bug is label semantics or feature calculation. If ANN matches but `startLongTrade/startShortTrade` differs, the bug is signal-gate semantics.
