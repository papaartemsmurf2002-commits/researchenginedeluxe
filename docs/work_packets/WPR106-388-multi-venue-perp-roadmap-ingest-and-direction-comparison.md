# WPR106-388 Multi-Venue Perp Roadmap Ingest And Direction Comparison

Status: closed
Owner: Codex Research Agent
Created: 2026-06-20

## Objective

Import the external v2 multi-venue perpetual research roadmap into the repo and
write a concise comparison against the current authoritative direction docs,
including the V4 discovery handoff, the real-strategy truthfulness plan, the
2024-forward broad strategy handoff, the rapid strategy sandbox foundation, and
the current completion roadmap.

This packet is documentation-only. It does not change implementation behavior,
generated research evidence, candidate gates, live/runtime code, strategy
algorithms, data collectors, or archive files.

## Dependencies

- `AGENTS.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- `docs/ACTIVE_INDEX.md`
- `docs/RESEARCH_V4_IMPLEMENTATION_AGENT_HANDOFF.md`
- `docs/RESEARCH_NEXT_PHASE_REAL_STRATEGIES_FILTERS_FEATURES_PLAN.md`
- `docs/NEXT_AGENT_HANDOFF_WPR106_85_2024_FORWARD_BROAD_STRATEGY_SEARCH.md`
- `docs/work_packets/WPR106-228-rapid-strategy-iteration-sandbox-foundation.md`
- `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md`
- `C:/Users/papaa/Downloads/researchenginedeluxe_v2_multi_venue_perp_research_roadmap.md`

## Allowed Paths

- `docs/work_packets/WPR106-388-multi-venue-perp-roadmap-ingest-and-direction-comparison.md`
- `docs/RESEARCH_ENGINE_DELUXE_V2_MULTI_VENUE_PERP_RESEARCH_ROADMAP.md`
- `docs/RESEARCH_ROADMAP_DIRECTION_COMPARISON_2026_06_20.md`
- `docs/ACTIVE_INDEX.md`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Constraints

- Research outputs remain research-only, observe-only, and
  `promotion_ready: false`.
- Do not create or modify candidate packs.
- Do not create paper/live artifacts.
- Do not place orders, change runtime mode, write live configuration, or add
  sizing/order-placement behavior.
- Do not modify source code, tests, configs, generated data, or archive files.

## Acceptance Criteria

- The external roadmap is present in `docs/` as an imported source document.
- The comparison memo states whether the new roadmap supersedes, extends, or
  conflicts with current repo direction.
- The memo identifies development progress, current gaps, and recommended next
  work without treating the imported roadmap as implemented evidence.
- `docs/ACTIVE_INDEX.md` points future agents to the imported roadmap and
  comparison memo as direction-analysis material.

## Validation

Documentation-only validation:

```powershell
git diff --check
```

No compile or pytest validation is required unless implementation files are
changed, which this packet explicitly forbids.

## Stop Conditions

- A blocking P0/P1 research/live boundary issue is discovered while reviewing
  the docs.
- The imported roadmap would be represented as active implementation
  authorization without an explicit orchestrator scope decision.
- Any source, config, test, generated data, or archive change becomes necessary.

## Completion Notes

Closed on 2026-06-20.

- Imported the external v2 roadmap unchanged into
  `docs/RESEARCH_ENGINE_DELUXE_V2_MULTI_VENUE_PERP_RESEARCH_ROADMAP.md`.
- Added `docs/RESEARCH_ROADMAP_DIRECTION_COMPARISON_2026_06_20.md` comparing
  the imported roadmap to the V4 discovery handoff, R94 strategy truthfulness
  plan, WPR106-85 broad strategy handoff, WPR106-228 rapid sandbox foundation,
  and the current completion roadmap.
- Updated `docs/ACTIVE_INDEX.md` with a conservative pointer that treats the
  v2 roadmap as a product-scope proposal until a later packet explicitly
  changes canonical identity, contracts, and implementation sequence.
- No source, test, config, generated data, archive, live, paper, runtime,
  candidate-pack, sizing, order, or promotion behavior was changed.

Validation:

```powershell
git diff --check
```

Result: passed, with the existing LF-to-CRLF warning for
`docs/ACTIVE_INDEX.md`.
