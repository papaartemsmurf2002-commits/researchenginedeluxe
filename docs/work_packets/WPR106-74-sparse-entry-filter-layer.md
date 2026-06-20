# WPR106-74 - Sparse Entry Filter Layer

## Purpose

Continue from WPR106-73 by testing whether sparse entry selection can improve
durable BTCUSDT/ETHUSDT evidence after runner/exit tweaking failed to rescue
dense transparent leads. This packet is research-only and asks whether
cooldown/top-score selection, side-balance control, and optional aggTrade
trade-flow gating can produce a lead worth larger validation, or whether the
next theory should move to sparse KNN/event gating.

## Scope

Allowed edit paths:

- `docs/work_packets/WPR106-74-sparse-entry-filter-layer.md`
- `docs/stage_reports/STAGE_R106_SPARSE_ENTRY_FILTER_LAYER_REPORT.md`
- `configs/research/sparse_entry_filter_btcusdt_r106_v1.json`
- `configs/research/sparse_entry_filter_ethusdt_r106_v1.json`
- `src/tradingbotsuite/strategies/sparse_event_filter.py`
- `src/tradingbotsuite/strategies/registry.py`
- `src/tradingbotsuite/strategies/parameters.py`
- `src/tradingbotsuite/strategies/no_trade.py`
- `src/tradingbotsuite/strategies/trend.py`
- `src/tradingbotsuite/strategies/volatility_breakout.py`
- `tests/contracts/test_strategy_contracts.py`
- `tests/historical/test_full_cycle_synthetic.py`
- `docs/KNOWN_ISSUES.md` only if a new blocking risk is found

Allowed generated research-output paths:

- `data/research/historical_cycles/sparse_entry_filter_btcusdt_r106_v1/**`
- `data/research/historical_cycles/sparse_entry_filter_ethusdt_r106_v1/**`
- `data/research/historical_cycles/sparse_entry_filter_*_r106_v1_run_output.json`

Read-only evidence and reference paths:

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- `docs/KNOWN_ISSUES.md`
- `docs/stage_reports/STAGE_R106_DURABLE_LEAD_EXIT_SIEVE_REPORT.md`
- `docs/work_packets/WPR106-73-durable-lead-exit-sieve.md`
- `configs/research/durable_lead_exit_sieve_btcusdt_r106_v1.json`
- `configs/research/durable_lead_exit_sieve_ethusdt_r106_v1.json`
- `data/research/historical_cycles/durable_lead_exit_sieve_btcusdt_r106_v1/**`
- `data/research/historical_cycles/durable_lead_exit_sieve_ethusdt_r106_v1/**`
- `data/research/operator_runs/historical_data/refresh-historical-data-catalog-4dfa2700192f4b6fa1fa8fe833668cfb/**`
- `src/tradingbotsuite/features/**`
- `src/tradingbotsuite/backtesting/**`
- `src/tradingbotsuite/research_cycle/**`
- `src/tradingbotsuite/strategies/**`

Out of scope:

- Candidate-pack creation or promotion artifacts.
- Live, paper, order-placement, sizing, runtime-mode, or live-config behavior.
- Provider downloads, catalog rebuilds, or fixture rewrites.
- Treating sparse-filter evidence as candidate-ready acceptance evidence.
- Funding/OI/premium/liquidation claims on the current candidate-depth pack.
- Broad exact-discovery or 50-hour sweeps.

## Plan

1. Add a bounded `sparse_event_filter_v1` transparent research strategy that
   reuses price-trend or volatility-breakout score construction, then applies
   explicit sparse-selection gates.
2. Support compact theories:
   - top-score sparse admission via minimum score and per-window top-N;
   - cooldown between accepted events;
   - optional side-balance cap;
   - optional aggTrade signed-ratio/count-z-score confirmation when durable
     aggTrade proxy features are present.
3. Keep exits simple for the first durable test: fixed hold plus the WPR106-73
   best damage-control comparator where useful.
4. Run compact BTC/ETH durable candidate-depth cycles with low
   `top_regions_to_refine` and explicit rows.
5. Compare sparse rows against the WPR106-73 dense leads and no-trade, with
   separate interpretation of entry quality and exit quality.
6. Decide whether any sparse transparent lead deserves larger validation or
   whether the next packet should be sparse KNN/event gating.

## Research Boundary

All outputs are research-only, observe-only, and promotion-disabled. This
packet may identify a next validation experiment, but it cannot create
candidate packs, paper/live readiness, sizing changes, runtime changes, or
promotion claims.

## Outcome

Completed on 2026-06-08 as a research-only sparse entry/filter wave.

Implemented `sparse_event_filter_v1`, registered parameter metadata, and added
focused contract coverage. BTC and ETH sparse configs were completed,
JSON-validated, spec-loaded, expanded, and run on the durable candidate-depth
fixture packs. Final validation passed with `python -m compileall -q
src/tradingbotsuite` and `$env:PYTHONPATH='src'; python -m pytest
tests/contracts -q` (449 tests).

BTC sparse filtering produced two aggregate-positive 72h volatility-breakout
rows, but they are not validation-ready. The price-only row had 521 trades,
net +0.007351, expectancy +0.001309, PF 1.074839, and max drawdown -0.594381;
split follow-up passed only 2/4 splits and cost-stress survival was 5/11,
below the 70% floor. The aggTrade contrarian row had 546 trades, net
+0.065930, expectancy +0.001575, and PF 1.085587, but split follow-up passed
only 2/4 splits and full cost-stress validation exceeded the compact budget.
Side evidence showed longs carried the edge while shorts were negative.

ETH sparse filtering did not rescue the trend lead. No sparse ETH row had
positive aggregate net return; the dense WPR106-73 72h fixed-hold caveat
remained the best ETH target row and still failed durable gate evidence.

Decision: do not scale any WPR106-74 row to candidate validation or promotion
work. Open the next packet around BTC side-veto or long-only sparse
volatility-breakout selection plus cost-stress performance cleanup for combined
price+aggTrade feature frames. Sparse KNN/event gating should wait until the
transparent side-veto layer shows stronger split/cost evidence.

No candidate pack, paper/live readiness artifact, live config, runtime-mode
change, order placement, sizing change, or promotion claim was created.
