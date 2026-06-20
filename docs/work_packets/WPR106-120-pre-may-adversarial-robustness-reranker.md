# WPR106-120 Pre-May Adversarial Robustness Reranker

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Test whether WPR106-119's diversity-constrained portfolio universe contains
holdout-surviving leads that can be identified without May 2026 feedback by
using a stricter pre-May robustness objective instead of aggregate pre-May
ranking. WPR106-119 found 8 May-positive rows, but they were lower-ranked and
the selected set remained mostly May-negative. This packet should determine
whether pre-May-only adversarial scoring, source-archetype penalties, rolling
block floors, and concentration controls can select a more holdout-stable
subset from the full WPR106-119 replay universe.

## Scope

- Use WPR106-119 pre-May replay artifacts as the source universe:
  `data/research/wpr106_119_diversity_constrained_cross_family_replay/pre_may/diversity_portfolio_replay_ranking.parquet`.
- Use only 2024-01-01 through 2026-04-30 for reranking, scoring,
  source-archetype penalties, selected-row choice, policy selection, and any
  deduplication.
- Keep May 2026 fully out of tuning. Use May only after fixed pre-May
  selections are written.
- Replay May 2026 for the WPR106-120 fixed selections at trade level using the
  same WPR106-118/WPR106-119 source loading and replay semantics, rather than
  relying only on WPR106-119's 60-row May benchmark.
- Evaluate multiple pre-May-only objective families, such as:
  - adversarial rolling-block score with minimum block return floors;
  - recent-window and early-window balance;
  - drawdown/downside-risk penalties;
  - best-month and best-source concentration penalties;
  - ETH lead-anchor/dense-core concentration penalties;
  - trade-rate, overlap, concurrent-skip, and day-cap sanity penalties;
  - rank-sensitivity and member-set deduplication.
- Preserve active-rate acceptance for roughly 1 to 5 trades/day when costs,
  overlap, drawdown, and monthly stability support it.
- Keep all artifacts `research_only: true`, `observe_only: true`, and
  `promotion_ready: false`.

## Allowed paths

- `docs/work_packets/WPR106-120-pre-may-adversarial-robustness-reranker.md`
- `docs/stage_reports/STAGE_R106_PRE_MAY_ADVERSARIAL_ROBUSTNESS_RERANKER_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_120*/**`

## Out of scope

- No May 2026 tuning, feedback, source choice, reranking-feature choice,
  scoring-weight choice, risk-policy choice, or cost-policy choice.
- No shared `src/tradingbotsuite` package, strategy registry, feature registry,
  backtest engine, optimizer, research-cycle, candidate-pack, live, runtime,
  config, or test changes.
- No candidate pack, paper/live artifact, order placement, position sizing,
  live runtime change, live configuration write, CUDA speedup claim, or
  promotion claim.
- No synthetic fallback data.
- No claim that a WPR106-120 row is candidate-ready without all downstream gate
  evidence.

## Exit evidence

- A deterministic WPR106-120 runner and artifacts are written under
  `data/research/wpr106_120*/`.
- The report records reranking objective families, pre-May selected rows,
  selection overlap with WPR106-119, rolling-block and annual diagnostics,
  active-rate diagnostics, concentration diagnostics, overlap/day-cap effects,
  cost-stress behavior, and May benchmark result for fixed selected rows.
- May benchmark artifacts are written separately and only after fixed pre-May
  selection.
- Validation baseline is run or explicitly reported if blocked:
  `python -m compileall -q src/tradingbotsuite` and
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`.

## Outcome

WPR106-120 closed on 2026-06-11. The runner read the 3,640-row WPR106-119
pre-May diversity replay universe, applied a strict pre-May base filter, and
found 254 base candidate rows. It scored those rows across five pre-May-only
objective families: adversarial rolling-block floor, anti-archetype
concentration, recent balance, low-drawdown/cost, and trade-quality stability.
The fixed selected set contains 80 strict-adversarial rows.

The selected rows looked stable before May: 28 active pre-May months for every
row, 522 to 1,241 trades, 3 to 5 losing months, annual loss targets satisfied,
full cost-stress survival, and 1.000 to 1.608 trades per active day. The set
contains 40 portfolio IDs not selected by WPR106-119, but only 20 genuinely
new member sets; 60 member sets overlap WPR106-119.

May 2026 was benchmark-only after fixed selection. It rejected the reranker:
8 May-positive, 72 May-negative, and 0 May-flat rows, with best May +0.009587,
worst May -0.061829, and median May -0.029856. The 20 genuinely new member
sets were all May-negative, and objective-level May medians were negative for
all five objective families. The result is useful negative evidence against
rescuing the WPR106-119 universe by pre-May reranking alone. It is not
candidate-ready.

Validation passed:

```powershell
python -m compileall -q data/research/wpr106_120_pre_may_adversarial_robustness_reranker/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Contracts reported 460 passed.
