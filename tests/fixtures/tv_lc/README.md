# TradingView LC Parity Fixtures

Drop TradingView Lorentzian Classification exports here when validating parity.

Each fixture should include a matching settings snapshot with:

- symbol and exchange
- timeframe
- chart export start/end timestamps
- visible/loaded chart history notes
- source input
- all feature settings
- all filter settings
- all kernel settings
- `useWorstCase` value
- include-last-bar policy
- expected warmup rows to skip when TradingView had more loaded history than the export

Recommended files:

- `btc_15m_tv_export.csv`
- `btc_15m_settings.yaml`
- `btc_15m_python_dump.csv`

Marker export contract:

- Shape markers (`Buy`, `Sell`, `StopBuy`, `StopSell`) are price-or-blank exports. A nonblank numeric price means the marker fired.
- Diagnostic booleans (`startLongTrade`, `startShortTrade`, `endLongTrade`, `endShortTrade`) are `0/1` exports. Numeric `0` is false and numeric `1` is true.

Current local snapshot:

- `binance_btcusdt_p_kernel_default.yaml` documents the existing `BINANCE_BTCUSDT.P.csv` export. Its kernel matches original LC defaults `lookback=8`, `relativeWeight=8`, `regressionLevel=25` after `26` warmup rows when using the paired prehistory CSV.
- `binance_btcusdt_p_close_10_1000_marker.yaml` documents `C:/Users/papaa/Downloads/BINANCE_BTCUSDT.P, 15 (14).csv`. Its kernel matches exactly, but marker parity depends on the first loaded chart bars because the original ANN loop uses persistent arrays and scans absolute indices `0..maxBarsBack-1`, not a rolling recent window.

When kernel parity is exact but `Buy`/`Sell` marker parity is not, regenerate the TradingView export with `docs/lc_parity_export_template.pine` appended to the original LC script. The export must include at least `prediction`, `signal`, `startLongTrade`, `startShortTrade`, feature columns, and the `neighborLabelTail*`/`neighborDistanceTail*` columns. Marker-only exports are insufficient to distinguish feature-helper drift from ANN history/index drift.
