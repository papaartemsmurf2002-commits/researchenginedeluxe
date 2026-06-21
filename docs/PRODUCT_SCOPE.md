# Product Scope

Status: v2 canonical scope document
Audit ID: `V2-AUD-SCOPE-001`
Source: `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md`

## Canonical Identity

ResearchEngineDeluxe v2 is a research-only, data-first, multi-instrument
perpetual-futures research platform focused on Hyperliquid perpetuals above
USD 5,000,000 daily notional volume, with support for compatible multi-venue
comparison data, strict validation, owned data archives, agent-safe strategy
evaluation, and audit-by-chunk migration.

BTC and ETH remain important fixture, smoke-test, reference, and legacy
evidence instruments. They do not define the full v2 product scope.

## Product Purpose

The product exists to run a repeatable research loop:

```text
discover liquid Hyperliquid perpetual universe
  -> collect and archive venue data with provenance
  -> normalize raw/bronze/silver/gold datasets
  -> enforce data quality, coverage, as-of universe, and lockbox policies
  -> evaluate declarative strategy specs through controlled backtest engines
  -> apply conservative costs, funding, spread, slippage, impact, and capacity assumptions
  -> append every passed or failed trial to a canonical experiment ledger
  -> move interesting non-promotable ideas into a Lead Book
  -> deep-validate one serious lead at a time
  -> allow only the top 3 survivors into final hard-test review
```

The product is not a live trading system, paper trading system, execution
system, sizing system, order-placement system, or promotion system.

## Non-Negotiable Invariant

Every v2 artifact, command, run, dashboard, audit record, and result must
preserve this invariant unless a future explicit human-approved process outside
this roadmap changes the repository role:

```json
{
  "research_only": true,
  "observe_only": true,
  "promotion_ready": false,
  "candidate_evidence": false,
  "candidate_pack_eligible": false,
  "live_signal": false,
  "paper_signal": false,
  "sizing_instruction": false,
  "order_placement_instruction": false,
  "runtime_mode_change": false
}
```

Allowed language includes `research platform`, `research-only archive`,
`non-promotable lead`, `sandbox lead`, `deep validation`, `final hard-test
survivor`, and `historical robustness`.

Disallowed language is blocked unless explicitly negated: `paper-ready`,
`live-ready`, `trade-ready`, `deployment-ready`, `sizing-ready`, `order-ready`,
`signal-ready`, `candidate-pack ready`, `guaranteed profitable`, and
`production trading strategy`.

## Default Evidence Universe

Accepted v2 research evidence uses this default universe:

```yaml
venue: hyperliquid
market_type: perpetual
min_day_notional_usd: 5000000
selection_mode: as_of
coverage_min: 0.98
earliest_reported_backtest_start: "2024-01-01"
minimum_usable_months: 6
preferred_usable_months: 12
lockbox_policy: dynamic_full_calendar_months
```

Current-universe analysis is allowed only as explicitly labeled sandbox/current
research and is blocked from evidence claims because it carries survivorship
bias risk.

Below-threshold instruments may be archived, observed, used for diagnostic
sandbox tests, used as negative controls, or stored with exclusion reasons.
They may not be accepted evidence under the default v2 universe rule.

## Evidence Floor

A v2 backtest result is accepted for research reporting only when it proves:

- start date is on or after 2024-01-01;
- usable data covers at least 6 months;
- 12 usable months are preferred when available;
- the dynamic latest full-month lockbox is excluded from ordinary iteration;
- data coverage is at least 0.98;
- an as-of universe snapshot is used for accepted evidence;
- strategy spec, parameters, archive snapshot, universe snapshot, cost model,
  validation policy, and run identity are hashed or otherwise manifest-backed;
- gross and net metrics are present;
- conservative cost, funding, spread, slippage, impact, and liquidity
  assumptions are represented;
- failed runs and rejected trials are logged rather than hidden.

## Implementation Status

This document defines scope. It does not prove that v2 M1, M2, M3, M4, or M5 is
implemented. Future packets must add source code, contracts, tests, manifests,
and validation evidence for each milestone.
