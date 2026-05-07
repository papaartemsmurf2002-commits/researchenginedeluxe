# WPR72-02 Discovery Feature-Set Flexibility Addendum

Stage: R72 discovery engine planning addendum
Owner: Codex Research Agent
Status: closed
Created: 2026-05-07

## Goal

Refine the V4 discovery-engine handoff so KNN feature sets are flexible, bounded, and stability-tested without becoming an uncontrolled brute-force search. The document must distinguish registered repo feature-set manifests from KNN feature-column sets, make WT/WT3D optional rather than privileged, support non-WT alternatives, and define calculation-quality standards for future implementation agents.

## Allowed Paths

```text
docs/RESEARCH_V4_DISCOVERY_ENGINE_AGENT_PLAN.md
docs/work_packets/WPR72-02-discovery-feature-set-flexibility-addendum.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- Planning/documentation only.
- Do not implement feature builders, KNN search, HMM materialization, or optimizer logic in this packet.
- Do not invent persistent feature-set IDs that are not registered.
- Treat the user's "dich WT" phrase as "ditch WT": WT/WT3D must be optional and compared against non-WT alternatives.
- Preserve research-only, observe-only, promotion-ready false boundaries.

## Close Evidence

- `docs/RESEARCH_V4_DISCOVERY_ENGINE_AGENT_PLAN.md` now describes flexible KNN feature-column sets, bounded predeclared search matrices, optional WT/WT3D handling, non-WT alternatives, feature-combination stability, and engineering-quality standards for future agentic development.
- Subagent reviews confirmed existing repo feature naming and current region-of-stability limitations.
