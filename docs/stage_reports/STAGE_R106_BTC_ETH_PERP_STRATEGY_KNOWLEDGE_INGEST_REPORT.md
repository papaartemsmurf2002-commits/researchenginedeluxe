# Stage R106 BTC ETH Perp Strategy Knowledge Ingest Report

Date: 2026-05-28
Packet: `WPR106-23-btc-eth-perp-strategy-knowledge-ingest`
Status: closed

## Summary

Cataloged the external BTC/ETH perpetual futures strategy master report as
repo-native research knowledge. The findings are intentionally recorded as a
hypothesis and validation-design base, not as an implementation roadmap,
candidate-ready evidence, promotion evidence, or live trading instruction.

## Artifacts

- `docs/research_knowledge/source_reports/btc_eth_perp_strategies_master_report.md`
  contains the imported source report for full-detail reference.
- `docs/research_knowledge/BTC_ETH_PERP_STRATEGY_KNOWLEDGE_BASE.md` contains a
  detailed, searchable knowledge base.
- `docs/research_knowledge/README.md` catalogs the knowledge artifacts.
- `START_HERE.md` now points future agents to the research knowledge catalog.

## Findings Preserved

The knowledge base preserves the report's core findings:

- BTC/ETH perp research should prioritize medium-frequency, execution-honest,
  risk-engineered systems over HFT imitation, generic deep learning, or
  public-API latency arbitrage.
- Alpha, execution, and risk must stay separable so tests can identify which
  layer creates or destroys PnL.
- Strong first baselines are adaptive trend with volatility targeting,
  BTC/ETH dynamic relative value, intraday compression breakout, and
  funding/OI crowding overlays.
- Carry, cross-venue funding, OFI/depth, liquidation tactics, options overlays,
  and market making are promising only when their required data and simulator
  assumptions are available.
- Feature groups worth preserving include returns/trend, volatility,
  funding/basis, OI/positioning, flow, book/depth, liquidations, options,
  events, and selected on-chain context.
- Honest validation requires chronological splits, walk-forward,
  post-cost/funding/slippage accounting, post-ETF and session splits,
  regime-separated OOS reporting, feature ablations, latency/fill sensitivity,
  and outlier-day analysis.
- Red-team cautions include mid-price PnL, passive spread capture without
  adverse selection, funding treated as risk-free, liquidation heatmaps as
  ground truth, ML accuracy without costs, and crowded public heuristics.

## Boundary

This packet changed documentation only. It did not edit source code, configs,
tests, fixtures, generated research artifacts, runtime mode, live configuration,
order placement, sizing, candidate packs, or promotion behavior.

All findings remain research-only, observe-only, and `promotion_ready: false`
by policy until future packets produce repo-native evidence.

## Validation

Passed:

- `git diff --check`
