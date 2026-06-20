# WPR106-98 Pre-May Deduped Portfolio Robustness Selector

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Revisit the WPR106-95 pre-May portfolio-combination evidence with a stricter
pre-May-only robustness selector. Remove repeated or near-duplicate sleeve
variants from candidate combinations, score month-to-month stability more
directly, and then use May 2026 only as a benchmark for the pre-May-selected
robustness leads.

## Scope

- Use WPR106-95 combination and sleeve artifacts as the pre-May optimization
  evidence source.
- Use WPR106-97 May benchmark artifacts only after pre-May robust leads are
  selected.
- Exclude combinations that repeat the same candidate hash or effectively
  duplicate the same packet-qualified sleeve identity.
- Prefer combinations with:
  - positive pre-May net return after costs;
  - active trading in the 1 to 5 trades-per-active-day range;
  - lower losing-month count and no severe annual losing-month clustering;
  - lower positive-month profit concentration;
  - lower overlap-day share;
  - better sleeve-level cost-stress survival and split-balance evidence.
- Write a deterministic robustness ranking, selected lead table, May benchmark
  join for selected leads, and summary report.
- Keep all outputs research-only, observe-only, and promotion-ready false.

## Allowed paths

- `docs/work_packets/WPR106-98-pre-may-deduped-portfolio-robustness-selector.md`
- `docs/stage_reports/STAGE_R106_PRE_MAY_DEDUPED_PORTFOLIO_ROBUSTNESS_SELECTOR_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_98*/**`

## Out of scope

- No strategy, feature, filter, threshold, parameter, optimizer, or execution
  retuning using May 2026.
- No new strategy, feature, research-cycle, backtest, live-boundary, or
  operator UI code.
- No candidate pack, promotion artifact, paper/live artifact, order placement,
  position sizing, runtime-mode change, live-configuration write, or CUDA
  speedup claim.
- No synthetic fallback data.

## Exit evidence

- Pre-May-only deduped robustness selection table written under
  `data/research/wpr106_98_pre_may_deduped_portfolio_robustness_selector/pre_may/`.
- Selected robustness leads are joined to May 2026 benchmark rows only after
  selection and reported as holdout diagnostics under
  `data/research/wpr106_98_pre_may_deduped_portfolio_robustness_selector/benchmark/`.
- The selector evaluated 650,622 WPR106-95 combinations, found 20 duplicate
  monthly-return fingerprint groups across 52 sleeve rows, reduced the strict
  pre-May hard-filter set to three combinations, and selected two unique
  behavior-signature leads.
- Selected lead 1: WPR106-95 rank 2 `combo-d1ccbd91dc5325e5`, +0.983789
  pre-May portfolio return, 572 trades, 1.372 trades per active day, 5 losing
  months, max full-year losing months 4, and +0.031402 May benchmark return.
- Selected lead 2: WPR106-95 rank 3 `combo-40bfb3546b9707ac`, +0.927046
  pre-May portfolio return, 800 trades, 1.515 trades per active day, 5 losing
  months, max full-year losing months 3, and -0.014460 May benchmark return.
- Neither selected lead satisfies the ideal zero-to-two losing-month target in
  every full pre-May calendar year, and no candidate-ready claim exists.
- Stage report records methodology, May non-tuning boundary, limitations, and
  next research direction.
- Validation baseline passed:
  `python -m compileall -q src/tradingbotsuite` and
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` with 460
  passed.
