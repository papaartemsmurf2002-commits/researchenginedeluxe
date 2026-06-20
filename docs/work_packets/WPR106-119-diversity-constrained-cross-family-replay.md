# WPR106-119 Diversity-Constrained Cross-Family Replay

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Test the direct counterfactual to WPR106-118: if cross-family portfolio search
is forced to include BTCUSDT exposure and non-lead-lag/non-session-anchor
families before ranking, can any 2024-forward portfolio retain pre-May
month-to-month stability and survive the May 2026 benchmark? WPR106-118 found
excellent pre-May strict rows, but selection collapsed into an ETH-only
lead-lag/session-anchor archetype that May rejected. This packet should verify
whether diversity constraints help or whether the broader source pool remains
unable to produce a holdout-stable lead.

## Scope

- Reuse compatible selected trade streams from WPR106-105 through WPR106-117,
  with the same exclusions as WPR106-118:
  - exclude WPR106-110 because it lacks trade-level streams;
  - exclude WPR106-113 and WPR106-114 because they are already portfolio
    replays.
- Use WPR106-118 normalization/replay logic as a helper, but write all new
  evidence under `data/research/wpr106_119*/`.
- Use only 2024-01-01 through 2026-04-30 for source filtering,
  deduplication, diversity-bucket assignment, member choice, weights,
  policy choice, ranking, and fixed selection.
- Keep May 2026 fully out of tuning. Use May only as a benchmark after fixed
  pre-May portfolio selection.
- Build portfolios that satisfy stricter diversity rules before ranking:
  - at least one BTCUSDT source;
  - at least one ETHUSDT source;
  - at least three source families;
  - at least two source packets;
  - no more than one source from the ETH lead-lag/session-anchor bucket;
  - at least one source from a KNN, regime-switch, flow, dense, or barpath
    bucket.
- Replay at trade level with actual overlap, concurrent position, max
  trades/day, and optional daily guard controls.
- Preserve active-rate acceptance for roughly 1 to 5 trades/day when costs,
  overlap, drawdown, and monthly stability support it.
- Keep all artifacts `research_only: true`, `observe_only: true`, and
  `promotion_ready: false`.

## Allowed paths

- `docs/work_packets/WPR106-119-diversity-constrained-cross-family-replay.md`
- `docs/stage_reports/STAGE_R106_DIVERSITY_CONSTRAINED_CROSS_FAMILY_REPLAY_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_119*/**`

## Out of scope

- No May 2026 tuning, feedback, source choice, diversity-bucket choice,
  filter choice, ranking choice, risk-policy choice, or cost-policy choice.
- No shared `src/tradingbotsuite` package, strategy registry, feature registry,
  backtest engine, optimizer, research-cycle, candidate-pack, live, runtime,
  config, or test changes.
- No candidate pack, paper/live artifact, order placement, position sizing,
  live runtime change, live configuration write, CUDA speedup claim, or
  promotion claim.
- No synthetic fallback data.

## Exit evidence

- A deterministic WPR106-119 runner and artifacts are written under
  `data/research/wpr106_119*/`.
- The report records diversity buckets, source counts, portfolio count,
  strict/loose counts, selected portfolios, monthly and annual loss
  diagnostics, active-rate diagnostics, overlap/day-cap effects, cost-stress
  behavior, member attribution, and May benchmark result for fixed selected
  rows.
- May benchmark artifacts are written separately and only after fixed pre-May
  selection.
- Validation baseline is run or explicitly reported if blocked:
  `python -m compileall -q src/tradingbotsuite` and
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`.

## Outcome

WPR106-119 closed on 2026-06-11. The runner reused the WPR106-118
normalization/replay helper and loaded 185,714 pre-May trades plus 6,028 May
benchmark trades from WPR106-105, WPR106-106, WPR106-107, WPR106-108,
WPR106-109, WPR106-111, WPR106-112, WPR106-115, WPR106-116, and WPR106-117.
WPR106-110 was excluded because it has no trade-level stream, and
WPR106-113/WPR106-114 were excluded because they are already portfolio replays.

The pre-May funnel computed 893 source metric rows, built a 144-row diversity
source pool, screened 497,313 diversity-constrained monthly rows, replayed
3,640 portfolios at trade level, and found 3,640 positive pre-May rows, 254
annual-target rows, 254 loose rows, and 254 strict rows. The fixed selected
set contains 60 strict portfolios with BTCUSDT and ETHUSDT exposure, at least
three families, at least two packets, and at most one ETH lead-anchor source.
Selected rows had 28 active pre-May months, 536 to 1,241 trades, 3 to 5 losing
months, full cost-stress survival, zero rolling losing blocks, max drawdown
from -0.045107 to -0.105492, and 1.000 to 1.608 trades per active day.

May 2026 was benchmark-only after fixed pre-May selection. It improved on
WPR106-118 but still rejected the selected set as candidate-ready evidence: 8
May-positive, 52 May-negative, and 0 May-flat rows, with best May +0.009587,
worst May -0.045300, and median May -0.026690. The May-positive rows were
lower-ranked and still concentrated around ETH dense/wick behavior plus one
ETH lead-lag source and a small BTC sleeve. The top pre-May ranks were
May-negative. The family remains research-only and not candidate-ready.

Validation passed:

```powershell
python -m compileall -q data/research/wpr106_119_diversity_constrained_cross_family_replay/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Contracts reported 460 passed.
