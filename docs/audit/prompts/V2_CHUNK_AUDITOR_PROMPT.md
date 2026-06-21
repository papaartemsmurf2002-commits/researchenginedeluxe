# V2 Chunk Auditor Prompt

Use this prompt for an independent review of any v2 audit chunk.

## Context To Provide

- Work packet path.
- Audit ID.
- Changed-file list.
- Relevant contract docs.
- Test commands and results.
- Any known skipped, failed, or environment-blocked checks.

## Auditor Questions

1. What changed?
2. What contracts apply?
3. What files were touched?
4. Were any no-touch paths modified?
5. Does the change preserve the research-only invariant from
   `docs/PRODUCT_SCOPE.md`?
6. Does it import live, paper, order-placement, sizing, runtime, promotion, or
   candidate-pack promotion code?
7. Does it mutate old evidence or generated artifacts?
8. Does it preserve deterministic IDs, hashes, manifests, and snapshots where
   relevant?
9. Does it enforce data snapshot identity where relevant?
10. Does it enforce 2024+, 6 usable months, 0.98 coverage, dynamic lockbox, and
    as-of universe where relevant?
11. Does it log failed trials or blocked jobs where relevant?
12. Are costs, funding, slippage, spread, impact, and net metrics represented
    where relevant?
13. Are tests adequate for the changed behavior and blast radius?
14. Is rollback clear?
15. Are hidden assumptions or weak evidence claims present?
16. Does the chunk introduce UI, live, paper, candidate-pack, sizing, order, or
    promotion implications?

## Required Verdict

Return one of:

- `pass`
- `pass_with_followup`
- `fail`
- `blocked_needs_decision`

The verdict must include file/line references for findings and must distinguish
historical documentation references from active v2 product claims.
