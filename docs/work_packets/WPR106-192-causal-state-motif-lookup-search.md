# WPR106-192 Causal State Motif Lookup Search

Status: closed
Owner: Codex Research Agent
Date: 2026-06-13

## Objective

Continue the 2024-forward broad research search after WPR106-191 rejected
accepted-trade overlays over WPR106-190 directional KNN rows. This packet tests
a fresh non-KNN source family: causal rolling state/motif lookup entries built
from completed 15m bar path, wick/range, volatility, session, cross-symbol,
and aggTrade-flow states.

The goal is to test whether simple recurring recent-state motifs can support a
normal active profile, including 1 to 5 trades per active day, while preserving
month-to-month stability after realistic costs and overlap handling.

This is an artifact-only research packet, not a candidate-promotion packet.

## Scope

Selection/tuning window:

- 2024-01-01 through 2026-04-30 UTC.

Benchmark-only window:

- May 2026, replayed only after fixed pre-May row selection.

Inputs:

- WPR106-96 BTCUSDT/ETHUSDT source context exposed through WPR106-170 helpers.
- Completed 15m OHLCV bars and 1m aggTrade-flow proxy features already present
  in the source context.
- Embedded WPR106 research cost model.

Search family:

- causal discrete state keys built from completed prior bars;
- recent return direction, wick/close-location, range/volatility, session,
  cross-symbol residual, and aggTrade-flow buckets;
- rolling lookback windows that only use prior completed labels;
- source-side policies selected from the pre-May rolling lookup score;
- fixed holding horizons and active daily caps;
- same-symbol overlap blocking and costed accepted-trade replay;
- pre-May-only ranking by monthly stability, active-rate behavior,
  annual losing-month counts, drawdown, downside risk, best-month
  concentration, and cost-stress survival;
- May replay of the fixed selected rows only.

May must not be used for motif definition, feature choice, bucket choice,
lookback choice, threshold choice, side choice, daily-cap choice, row ranking,
or tie-breaking. May is benchmark-only after fixed pre-May selection.

## Allowed Paths

- `docs/work_packets/WPR106-192-causal-state-motif-lookup-search.md`
- `docs/stage_reports/STAGE_R106_CAUSAL_STATE_MOTIF_LOOKUP_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_192_causal_state_motif_lookup_search/**`

## Plan

1. Load WPR106-96 source contexts through WPR106-170 helpers.
2. Build completed-bar feature buckets and discrete motif keys without using
   future bars.
3. Compute future fixed-hold labels for pre-May and May benchmark windows.
4. Evaluate rolling prior-history motif lookup rows across motif definitions,
   horizons, lookbacks, thresholds, side modes, and daily caps.
5. Replay accepted trades with same-symbol overlap blocking and embedded costs.
6. Select fixed rows from pre-May diagnostics only.
7. Replay the fixed selected rows on May 2026.
8. Write ranking, monthly/daily/trade artifacts, summary, report, ledger
   update, and validation notes.

## Research Boundary

All outputs remain:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`

This packet must not create a candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim.

## Validation

Passed:

```powershell
python -m compileall -q data\research\wpr106_192_causal_state_motif_lookup_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.

## Exit Evidence

WPR106-192 first attempted a broader 64,800-row motif lookup grid. That pass
was stopped after a 15-minute command timeout after reaching 55,000 evaluated
pre-May rows and before aggregate artifacts were written. The timeout logs were
preserved as `wpr106_192_broad_timeout_stdout.log` and
`wpr106_192_broad_timeout_stderr.log`.

The final bounded run evaluated 5,184 rows across BTCUSDT and ETHUSDT,
four motif packs, 8/16/32-bar holds, two lookbacks, both/long/short side modes,
all/EU/US sessions, and daily caps of 1/3/5. It found 242 positive pre-May
rows, 43 annual-target rows, zero loose rows, and zero strict rows. The fixed
selected set contained 74 fallback `positive_recent_stability` rows: 62
ETHUSDT and 12 BTCUSDT.

Selected pre-May replay was 74 positive rows, zero negative rows, median
+0.205355, active mean +0.223349, best +0.489121, and worst +0.028659. May
benchmark was active for all 74 selected rows, with 45 positive rows, 29
negative rows, median +0.008759, active mean +0.015506, best +0.090413, and
worst -0.030529.

The result is not candidate-ready. It has zero strict/loose pre-May rows, and
the selected rows are fallback rows with excessive pre-May losing months and
drawdowns. The best May row is ETHUSDT `trend_pullback_clock`, 32-bar hold,
6144-bar lookback, US session, both-sided, daily cap 3: +0.439334 pre-May over
718 trades and +0.090413 in May over 40 trades, but it has 14 pre-May losing
months, seven losing months in 2024, six in 2025, and max drawdown -0.439939.
The annual-target rows were too sparse and not recently active; none passed
latest-four-month activity floors.

WPR106-192 therefore rejects the bounded causal state motif lookup search as
candidate-ready, portfolio-ready, or promotion-ready. It preserves ETHUSDT
US-session `trend_pullback_clock` and related active May motif behavior as a
research-only diagnostic for future source-family or risk-control work.
