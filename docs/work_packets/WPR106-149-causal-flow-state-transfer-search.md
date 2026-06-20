# WPR106-149 Causal Flow-State Transfer Search

Date: 2026-06-12
Owner: Codex Research Agent
Status: closed

## Objective

Continue the broad 2024-forward search after WPR106-148 rejected the broad
behavior-deduped source selector. This packet tests materially different
artifact-only 15m price plus aggTrade-flow state variants over BTCUSDT and
ETHUSDT, with pre-May transfer constraints before any May benchmark.

The goal is not to defend the WPR106-146/WPR106-147/WPR106-148 source lineage.
The packet uses the WPR106-96 verified 2024-01 through 2026-05 context and
constructs fresh causal score families that combine completed-bar price path,
flow pressure, compression/expansion state, wick/sweep proxies, and
cross-symbol transfer checks.

## Allowed Paths

- `docs/work_packets/WPR106-149-causal-flow-state-transfer-search.md`
- `docs/stage_reports/STAGE_R106_CAUSAL_FLOW_STATE_TRANSFER_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_149_causal_flow_state_transfer_search/**`

## Inputs

- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/features/**`
- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/source_context/**`
- Prior stage reports for context only; no prior selected row may be used as a
  tuning target.

## Boundaries

- Research-only, observe-only, promotion-ready false.
- No candidate pack, paper/live artifact, order placement, sizing change,
  runtime-mode change, live configuration write, or promotion claim.
- May 2026 must not affect score formulas, thresholds, selected rows, transfer
  controls, rankings, or parameter choices.
- Use 2024-01-01 through 2026-04-30 as the default optimization/search window.
- Use May 2026 only as benchmark holdout after fixed pre-May survivors exist.
- Active rates near 1 to 5 trades per active day are allowed when costs,
  same-symbol overlap, and daily caps are accounted for.
- This packet is artifact-only. It does not change shared feature, strategy,
  KNN, backtest, live, or candidate-pack code.
- CUDA is not expected. Use vectorized pandas/numpy and truthful CPU reporting.
- If a blocking correctness risk is found, update `docs/KNOWN_ISSUES.md`.

## Evidence Plan

1. Load WPR106-96 BTCUSDT and ETHUSDT feature contexts through 2026-05.
2. Build causal completed-bar features from prior/available rows only, including
   flow pressure, rolling flow/volume z-scores, price momentum, range/wick
   state, compression, and expansion proxies.
3. Evaluate fresh score families:
   - flow-state continuation;
   - compression breakout with flow confirmation;
   - sweep/wick absorption reversal;
   - divergence between price path and taker-flow pressure;
   - cross-symbol relative flow confirmation;
   - transparent price-only controls.
4. Calibrate thresholds only on the pre-May window for target active rates and
   evaluate fixed-hold exits with costs, overlap avoidance, and daily caps.
5. Require pre-May monthly stability plus transfer checks across symbol and
   anchored quarter holdouts before selecting rows.
6. Replay only fixed pre-May survivors on May 2026.
7. Summarize whether the family is rejected, or whether any narrow research-only
   lead deserves deeper controls.

## Validation

Run focused script compile, then the branch baseline:

```powershell
python -m compileall -q data/research/wpr106_149_causal_flow_state_transfer_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

## Evidence Results

- Evaluated rows: 5,376 total; 2,688 BTCUSDT and 2,688 ETHUSDT.
- BTCUSDT positive pre-May rows: 127; max total net return +0.129187; median
  -0.377506.
- ETHUSDT positive pre-May rows: 511; max total net return +0.814188; median
  -0.332186.
- Strict pre-May rows: 0.
- Loose pre-May rows: 0.
- Transfer-strict rows: 0.
- Transfer-loose rows: 0.
- Fixed May benchmark rows: 0 because no row qualified as a promising pre-May
  lead under the packet rules.

## Closeout

WPR106-149 rejects this causal common-column price/flow state transfer search
as a promising lead source. Positive diagnostic rows exist, including some
same-configuration rows positive on both BTCUSDT and ETHUSDT, but monthly
stability is not close enough: the best positive-on-both config has 11 max
losing months, and every row fails strict/loose pre-May gates plus transfer
survival. May 2026 remains unused, correctly, because there were no promising
pre-May survivors.

Validation passed:

```powershell
python -m compileall -q data/research/wpr106_149_causal_flow_state_transfer_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Contracts result: 460 passed.
