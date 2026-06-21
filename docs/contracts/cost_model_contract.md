# V2 Cost Model Contract

Status: v2 Phase 12 cost model contract
Audit ID: `V2-AUD-COST-001`

## Purpose

Cost models define conservative net-result assumptions for v2 research.

## Initial Schema Names

- `CostModelConfig`
- `CostStressScenario`
- `CostBreakdown`

## Required Rules

- Costs include fees, funding, spread, slippage, impact, and capacity/liquidity
  assumptions where relevant.
- Cost model ID and hash are part of run identity.
- Stress scenarios are recorded separately from base assumptions.
- Gross-only results cannot advance to Lead Book or final hard-test decisions.
- The conservative default model is taker-side and must include `base`,
  `stress_2x`, and `stress_3x`.
- Maker or mixed maker/taker assumptions require documented queue modeling.
- Funding is applied from manifested funding fields; missing required funding
  fails closed unless an explicit-zero policy is configured.
- Liquidity participation caps reject oversized trades instead of silently
  accepting optimistic fills.
- Cost manifests use `schema_version: cost_manifest_v1` and record fee,
  funding, slippage, spread, impact, capacity, stress matrix, cost sensitivity,
  research-only metadata, and `promotion_ready: false`.

## Forbidden

- Treating venue-specific historical costs as live execution proof.
- Missing-cost accepted evidence.
- Free maker fills without a queue model.
- Ranking or promotion from gross-only metrics.
