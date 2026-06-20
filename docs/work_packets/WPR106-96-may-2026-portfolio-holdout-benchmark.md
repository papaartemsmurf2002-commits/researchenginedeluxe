# WPR106-96 May 2026 Portfolio Holdout Benchmark

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Resolve the immediate BTCUSDT May 2026 holdout dependency for the WPR106-95
pre-May cross-family portfolio-combination diagnostic leads, then benchmark
the preselected combinations on May 2026 without using May for tuning,
selection, feature choice, threshold choice, or parameter changes.

The primary preselected benchmark target is WPR106-95 rank 1:
`combo-d9edcc252c323b03`. Secondary benchmark rows may include other top
WPR106-95 combinations only if they were already ranked before May intake.

## Scope

- Download or verify only the BTCUSDT May 2026 Binance Vision public archive
  files needed for the historical-cycle style feature/backtest benchmark:
  15m klines, 1m klines, and aggTrades plus checksum sidecars.
- Reuse the WPR106-93 verified ETHUSDT May archive files where an ETHUSDT
  sleeve belongs to a preselected WPR106-95 combination.
- Preserve source URLs, local paths, SHA-256 hashes, checksum verification,
  row counts, gap/duplicate checks, completed-bar semantics, event-end
  semantics, and research-only metadata.
- Benchmark WPR106-95 selected sleeve candidates on May 2026 with their frozen
  strategy parameters and equal-sleeve weights.
- Report May trades, active days, trades per active day, overlap, net return,
  expectancy, daily behavior, and whether May contradicts the pre-May
  portfolio story.
- Keep all artifacts research-only, observe-only, and promotion-ready false.

## Allowed paths

- `docs/work_packets/WPR106-96-may-2026-portfolio-holdout-benchmark.md`
- `docs/stage_reports/STAGE_R106_MAY_2026_PORTFOLIO_HOLDOUT_BENCHMARK_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_96*/**`
- `data/research/historical_data_cache/binance_vision_public_archive/downloads/futures_um/monthly/klines/BTCUSDT/15m/*2026-05*`
- `data/research/historical_data_cache/binance_vision_public_archive/downloads/futures_um/monthly/klines/BTCUSDT/1m/*2026-05*`
- `data/research/historical_data_cache/binance_vision_public_archive/downloads/futures_um/monthly/aggTrades/BTCUSDT/*2026-05*`

## Out of scope

- No May 2026 tuning, ranking, selection, optimizer feedback, feature
  selection, threshold selection, or parameter changes.
- No new strategy, feature, research-cycle, live-boundary, or operator UI code.
- No candidate pack, promotion artifact, paper/live artifact, order placement,
  position sizing, runtime-mode change, or live-configuration write.
- No synthetic fallback if public archive files are unavailable.
- No CUDA speedup claim.

## Exit evidence

- BTCUSDT May 2026 Binance Vision 15m kline, 1m kline, and aggTrades
  archives are present under the local public-archive cache with checksum
  sidecars and verified SHA-256 hashes.
- WPR106-93 ETHUSDT May 2026 archive files were reused and re-verified for
  the ETHUSDT sleeve.
- Intake manifest:
  `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/intake/wpr106_96_may_archive_intake_manifest.json`.
- May fixture-compatible context artifacts:
  `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/source_context/`.
- Feature context manifest:
  `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/features/wpr106_96_feature_context_manifest.json`.
- Frozen rank-1 benchmark summary:
  `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/wpr106_96_holdout_benchmark_summary.json`.
- WPR106-95 rank-1 `combo-d9edcc252c323b03` May 2026 benchmark:
  25 May-entry member trades, 20 active days, 1.250 trades per active day,
  0.250 overlap-day share, +0.026603 equal-sleeve portfolio return, 8
  positive days, and 12 losing days.
- Sleeve May net-return sums: WPR106-94 BTC `c66b21e80bf2` +0.057419,
  WPR106-91 BTC `ea9b0ade9515` +0.057029, WPR106-90 ETH `335840e95fb1`
  -0.020243, WPR106-94 BTC `2ad619dad064` +0.012209.
- May was not used for tuning, selection, feature choice, threshold choice, or
  parameter changes; all sleeves used frozen WPR106-95 member definitions.
- No candidate pack, paper/live artifact, order/sizing/runtime change, live
  config write, CUDA speedup claim, or promotion claim was created.
- Validation passed:
  `python -m compileall -q src/tradingbotsuite` and
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` with 460 passed.
