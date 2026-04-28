# Entry Gate Research

This guide covers the BTC-only observe-only entry blocker research pass. It is not live gating.

## Objective
- Test whether a smooth closed-bar trend/chop gate can reject at least 30% of low-quality corridor entries without damaging high-volatility trend entries.
- Use TradingView `Buy` and `Sell` chart-export markers as candidate entries.
- Use a simple research simulator: next-bar open entry, fixed `0.01 BTC`, worst-case SL first if TP and SL touch in the same bar, and reverse signal closes/reopens on the next bar open.
- Keep exit handling fixed by profile during optimizer runs: `runner` for the preferred runner profile, or `fixed` for `1.5% TP / 0.5% SL`.
- Compare every gate candidate against the no-gate TradingView baseline using capital return percent, winrate, profit factor, Sortino, drawdown, rejection rate, and split stability.

## Research Sources
- Lag-1 autocorrelation follows Pearson correlation semantics over closed-bar 15m log returns.
- Historical Volatility Ratio compares short-window log-return standard deviation to long-window log-return standard deviation.
- DSP cycle mode uses SciPy's causal Butterworth SOS bandpass filtering on returns. It does not use forward/backward filtering, so signal-time values do not see future bars.
- Grid search is bounded and time-ordered. It is not randomized cross-validation and it is not allowed to leak future bars into signal-time decisions.

## Command
```powershell
$env:PYTHONPATH="src"
python -m tradingbotsuite.main research-entry-gates --path "BINANCE_BTCUSDT.P, 15 (2).csv" --symbol BTCUSDT --strategy-version kernel_v1
```

The default `BINANCE_BTCUSDT.P, 15 (2).csv` artifact is currently a combined BTC 15m export. Its merge manifest is `data/imports/tradingview_exports/BINANCE_BTCUSDT.P_15_combined_manifest.json`. Binance-only rows before the first TradingView-exported bar are warmup/context rows with blank `Buy`/`Sell` markers.

The command defaults to a bounded `10000`-candidate sweep across the ACF/HVR/DSP ranges. Bounded runs are stratified across the full grid instead of taking the first parameter block. Use `--max-candidates` when you intentionally want a smaller smoke run or a deeper run.

The alternative `goldilocks` gate family tests ER, daily VWAP, and HVP. VWAP needs Binance 15m OHLCV enrichment because the current chart export does not include volume:

```powershell
python -m tradingbotsuite.main optimize-entry-gates `
  --path "BINANCE_BTCUSDT.P, 15 (2).csv" `
  --symbol BTCUSDT `
  --strategy-version kernel_v1_goldilocks `
  --gate-family goldilocks `
  --allowed-components er,vwap,hvp `
  --ohlcv-cache-policy use-or-fetch `
  --exit-profile runner `
  --workers 15
```

Optional knobs:
```powershell
python -m tradingbotsuite.main research-entry-gates `
  --path "BINANCE_BTCUSDT.P, 15 (2).csv" `
  --symbol BTCUSDT `
  --strategy-version kernel_v1 `
  --take-profit-pct 0.005 `
  --stop-loss-pct 0.005 `
  --position-size-btc 0.01 `
  --capital-quote 1000 `
  --fee-bps 5 `
  --entry-slippage-bps 5 `
  --exit-slippage-bps 5
```

## Heavy Optimizer
Use this when you want the script to optimize gate parameters and gate component selection in one pass. Exit parameters are not optimized in this pass; choose one predetermined research exit profile and keep the search focused on whether the entry gate itself adds value.

Run preflight first to test each gate family alone with the current preferred runner exit. This answers whether ACF, HVR, or DSP has standalone value before mixing them:

```powershell
$env:PYTHONPATH="src"
python -m tradingbotsuite.main preflight-entry-gates --path "BINANCE_BTCUSDT.P, 15 (2).csv" --symbol BTCUSDT --strategy-version kernel_v1_preflight
```

```powershell
$env:PYTHONPATH="src"
python -m tradingbotsuite.main optimize-entry-gates --path "BINANCE_BTCUSDT.P, 15 (2).csv" --symbol BTCUSDT --strategy-version kernel_v1_heavy --exit-profile runner --workers 15
```

The heavy optimizer uses process workers, not threads, because the simulation is CPU-bound. The default command is capped at `10000` gate candidates. That is heavy enough for normal local research on the 15-worker workstation while still avoiding the full all-component grid by accident. Raise or lower the cap explicitly when needed:

```powershell
python -m tradingbotsuite.main optimize-entry-gates --path "BINANCE_BTCUSDT.P, 15 (2).csv" --symbol BTCUSDT --strategy-version kernel_v1_deeper --max-gate-candidates 50000 --exit-profile runner --workers 15
```

The heavy optimizer tests:
- stepped gate-parameter ranges for ACF, HVR, and DSP cycle mode
- or, with `--gate-family goldilocks`, stepped ranges for ER, VWAP margin, and HVP windows/bands
- exactly the selected filter components; checked components stay enabled for every candidate and unchecked components stay disabled
- exactly one selected exit profile: `runner` or `fixed`
- top 5 configurations by constraint-first ranking, with selection capped at 50% rejection so at least half of TradingView signals must remain eligible
- separate top 5 leaderboards by raw return, profit factor, and winrate, because useful manual-tweak candidates can fail the strict selection gate while still being worth inspection

Range defaults are generated from fixed step rules, not manually curated one-off values: ACF window `[10, 12, 14, 16, 20]`, ACF block below `[-0.30, -0.25, -0.20, -0.15]`, ACF trend above `[0.05, 0.10, 0.15, 0.20]`, HVR short `[4, 6, 8, 10]`, HVR long `[40, 50, 60, 80]`, HVR block below `[0.40, 0.50, 0.60]`, HVR release above `[0.70, 0.75, 0.85]`, DSP min cycle `[4, 6]`, DSP max cycle `[12, 16, 24]`, DSP cycle ratio `[0.45, 0.55, 0.65]`, and DSP trend slope `[0.20, 0.25, 0.35]`. Capped runs sample across the full range instead of taking only the first combinations.

Full grid sizes by selected component set:

- ACF only: `80`, exhaustive by default.
- HVR only: `144`, exhaustive by default.
- DSP only: `54`, exhaustive by default.
- ACF + HVR: `11520`, nearly full at the `10000` default; use `--max-gate-candidates 11520` for exact exhaustive search.
- ACF + DSP: `4320`, exhaustive by default.
- HVR + DSP: `7776`, exhaustive by default.
- ACF + HVR + DSP: `622080`, sampled at the `10000` default; use `--uncapped` only for a long audit.

For a fast smoke test:
```powershell
python -m tradingbotsuite.main optimize-entry-gates --path "BINANCE_BTCUSDT.P, 15 (2).csv" --symbol BTCUSDT --strategy-version smoke --max-gate-candidates 64 --exit-profile fixed
```

`--uncapped` exists for audit completeness, but it should be treated as a long-running research job only for the all-component case. The full theoretical gate grid streams from memory-safe iterators, but `622080` candidates is far larger than a normal iteration loop.

The operator console `Analysis` tab now exposes the same chart-export replay path directly in the browser. Use it for fast visual checks, manual parameter changes, and filter on/off comparisons before queueing heavier preflight or optimizer jobs.

## Shared Acceptance Layer
The shared feature packet now carries an observe-only `rule_acceptance` block. This is the first implementation step for filtering TradingView KNN outputs without depending on the internals of the TradingView model itself.

Current rule stack:
- regime core: `lag1_autocorrelation`, `historical_volatility_ratio`, `dsp_cycle_ratio`, `dsp_cycle_mode`
- perp context overlay: `basis_bps`, `funding_rate`, `premium_basis_rate`, time to next funding
- liquidity guard: `spread_bps`, signed trade-flow ratio, top-of-book imbalance

The rule layer is intentionally compact and interpretable. It remains observe-only until replay proves that it improves post-signal acceptance quality without damaging strong trend participation.

## Outputs
- `metrics.json`: baseline versus best gate summary.
- `grid_results.csv`: every bounded grid candidate and its metrics.
- `best_gate_manifest.json`: selected observe-only gate parameters and selection status.
- `equity_curve.csv`: equity path for the selected gate.
- `rejected_vs_accepted.csv`: one row per TradingView signal with gate score, reason, cycle/chop state, and trend-override flags.
- Heavy optimizer additionally writes `top5_results.csv`, `top5_by_return_results.csv`, `top5_by_profit_factor_results.csv`, and `top5_by_winrate_results.csv`.

## Exit Modes
- `fixed`: uses the predetermined research profile with fixed `1.5%` TP and `0.5%` SL.
- `runner`: uses the same initial `0.5%` SL, activates a runner after `+0.5%` favorable movement, then trails by `0.3%` with a `0.1%` profit floor. Reverse TradingView signals still close and reopen on the next bar open.

These profiles are research-only. They exist to keep the entry-gate optimizer focused on gate value, not exit overfitting. The lower-level `research-entry-gates` CLI still exposes manual exit inputs for controlled audits, but the browser optimizer uses only these profiles.

## How To Read Results
- `selection_status=passed_all_constraints` means the selected gate met the current research constraints. It still does not approve live gating.
- `best_available_failed_constraints` means the run produced a best candidate but it failed at least one constraint.
- `candidate_rejection_target_count` should be non-zero. If it is zero, the grid is not exploring useful rejection levels.
- `candidate_full_pass_count` tells whether any candidate improved return/profit factor/split stability while rejecting 30-50% of entries. The 50% rejection cap is intentional: the gate must retain at least half of the TradingView signals to avoid becoming a hyper-selective overfit filter.
- `trend_override_retention_rate` should stay high when trend overrides appear; below `0.75` means the gate is probably damaging the TradingView model's best regime.
- If your manually tweaked setting looks better than the constraint-ranked best, inspect `top5_by_return_results.csv` and `top5_by_profit_factor_results.csv`. The optimizer may already have found it but kept it out of `top5_results.csv` because it missed the rejection-rate or split-stability constraints.
- Optimizer output directories include exit profile, selected component set, and candidate cap. This prevents `runner` and `fixed` runs with the same strategy version from overwriting each other.

## Data Sufficiency
- Goldilocks VWAP depends on cached Binance 15m OHLCV under `data/research/chart_ohlcv_cache/`. If the cache is missing or Binance OHLC differs from chart-export OHLC beyond `5 bps`, VWAP is marked unavailable rather than mixed silently.
- Missing Goldilocks components are reported as `missing_component_rate`, separate from strategic rejection rate. Treat high missingness as a data problem, not as evidence that the gate works.
- Extra closed-bar OHLC history without extra TradingView entries can improve feature warmup, ACF/HVR/DSP stability checks, and regime distribution diagnostics.
- Extra market-data history alone cannot prove that a filter improves the KNN signal stream. Gate profitability still needs actual TradingView `Buy`/`Sell` events so the replay can measure accepted versus rejected entries.
- Microstructure history can help describe normal spread, depth, and signed-flow regimes, but it should not be used as proof of entry-filter value unless it is aligned to real candidate signal times.

## Live Safety Boundary
- This layer is observe-only.
- It must not replace runtime safety checks.
- It must not use one-tick microstructure as a hard blocker.
- It can become a runtime gate only after repeated walk-forward evidence proves it improves the TradingView signal path without overfitting.
