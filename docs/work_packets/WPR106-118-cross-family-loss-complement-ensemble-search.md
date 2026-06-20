# WPR106-118 Cross-Family Loss-Complement Ensemble Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Test whether rejected or diagnostic 2024-forward families become more stable
when combined by pre-May loss-month complementarity and replayed with actual
trade overlap controls. This packet intentionally moves away from defending a
single KNN or sparse lead and instead reuses selected source streams from
recent broad-search packets, including newer WPR106-115 through WPR106-117
families that were not part of the earlier WPR106-113 portfolio replay.

## Scope

- Build an artifact-only source pool from selected pre-May and May benchmark
  trade streams and metrics from WPR106-105 through WPR106-117 where
  compatible trade files exist.
- Treat each source candidate as research-only evidence from its original
  packet. Preserve packet, family, symbol, candidate id, and source metadata in
  every derived artifact.
- Use only 2024-01-01 through 2026-04-30 for:
  - source filtering;
  - source deduplication;
  - source score calculation;
  - loss-month complement selection;
  - portfolio member choice;
  - weights, overlap policy, daily trade cap, and risk-control choice;
  - ranking and fixed selection.
- Keep May 2026 completely out of tuning. Load May trades only after fixed
  pre-May portfolios are selected, and report May separately as a benchmark
  holdout.
- Replay portfolios at trade level with explicit same-symbol overlap blocking,
  max concurrent position controls, max trades/day caps, and optional daily
  loss/profit guards.
- Allow active rates in the requested 1 to 5 trades/day range when costs,
  overlap, drawdown, and month-to-month stability support the behavior.
- Favor month-to-month stability:
  - annual losing-month target of at most 2 losing months in 2024, 2 in 2025,
    and 1 in 2026 Jan-Apr;
  - low best-month concentration;
  - broad active-month coverage;
  - cost-stress survival;
  - rolling pseudo-OOS block stability.
- Keep all artifacts `research_only: true`, `observe_only: true`, and
  `promotion_ready: false`.

## Allowed paths

- `docs/work_packets/WPR106-118-cross-family-loss-complement-ensemble-search.md`
- `docs/stage_reports/STAGE_R106_CROSS_FAMILY_LOSS_COMPLEMENT_ENSEMBLE_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_118*/**`

## Out of scope

- No May 2026 tuning, feedback, source choice, filter choice, ranking choice,
  risk-policy choice, or cost-policy choice.
- No shared `src/tradingbotsuite` package, strategy registry, feature registry,
  backtest engine, optimizer, research-cycle, candidate-pack, live, runtime,
  config, or test changes.
- No candidate pack, paper/live artifact, order placement, position sizing,
  live runtime change, live configuration write, CUDA speedup claim, or
  promotion claim.
- No synthetic fallback data and no fabricated missing May benchmark trades.
- No spreadsheet-only profit claim: selected portfolios must be replayed at
  trade level with overlap and daily controls.

## Exit evidence

- A deterministic WPR106-118 runner and artifacts are written under
  `data/research/wpr106_118*/`.
- The report records source packets, source counts, deduplication behavior,
  portfolio count, strict/loose counts, selected portfolios, monthly and
  annual loss diagnostics, active-rate diagnostics, overlap/day-cap effects,
  cost-stress behavior, and May benchmark result for fixed selected rows.
- May benchmark artifacts are written separately and only after fixed pre-May
  selection.
- Validation baseline is run or explicitly reported if blocked:
  `python -m compileall -q src/tradingbotsuite` and
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`.

## Outcome

WPR106-118 closed on 2026-06-11. The runner loaded 185,714 pre-May trades and
6,028 May benchmark trades from WPR106-105, WPR106-106, WPR106-107,
WPR106-108, WPR106-109, WPR106-111, WPR106-112, WPR106-115, WPR106-116, and
WPR106-117. WPR106-110 was excluded because it has no trade-level stream, and
WPR106-113/WPR106-114 were excluded because they are already portfolio replays.

The pre-May funnel found 57,060 monthly-screen rows, replayed 2,940 portfolios
at trade level, and found 2,940 positive pre-May rows, 203 annual-target rows,
203 loose rows, and 202 strict rows. The fixed selected set contains 40 strict
portfolios with 28 active pre-May months, 402 to 643 trades, 3 to 5 losing
months, full cost-stress survival, and low best-month concentration.

May 2026 was benchmark-only after fixed pre-May selection. It rejected the
selected set: 0 May-positive, 40 May-negative, and 0 May-flat rows, with best
May -0.008687 and worst May -0.042144. The selected portfolios were
effectively ETH-only and concentrated in WPR106-108 single-leg lead-lag,
WPR106-109 anchor, and one WPR106-106 dense volatility/session source. The
family remains research-only and not candidate-ready.

Validation passed:

```powershell
python -m compileall -q data/research/wpr106_118_cross_family_loss_complement_ensemble_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Contracts reported 460 passed.
