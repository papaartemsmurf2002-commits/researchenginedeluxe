# WPR72-01 Discovery Engine Agent Plan

Stage: R72 discovery engine planning
Owner: Codex Research Agent
Status: closed
Created: 2026-05-07

## Goal

Digest the operator's latest research direction and the downloaded sparse idea notes into a repo-native implementation plan for a real discovery engine. The plan must separate perp/microstructure context from core entry discovery, define HMM as a split-safe regime detector, define regime-local KNN tuning, and specify resumable day-long runs with regular snapshots.

## Allowed Paths

```text
docs/RESEARCH_V4_DISCOVERY_ENGINE_AGENT_PLAN.md
docs/work_packets/WPR72-01-discovery-engine-agent-plan.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- Planning only: do not implement code in this packet.
- Preserve research-only, observe-only, promotion-ready false boundaries.
- Do not create live, paper, shadow, testnet, canary, sizing, or order-placement behavior.
- Do not treat perp context, microstructure, WT/KNN, HMM, or liquidation context as accepted performance evidence.
- Do not hard-wire microstructure/perp filters into candidate acceptance without ablation evidence.
- Keep future implementation additive and aligned with current package names, manifests, candidate gates, and operator jobs.

## Required Output

- A curated plan document that:
  - identifies which ideas are accepted, conditional, or rejected;
  - defines the target research architecture by layers;
  - separates core WT/KNN discovery from perp-context and microstructure ablations;
  - defines split-safe HMM posterior materialization;
  - defines per-regime KNN studies and candidate promotion into the historical cycle;
  - defines checkpointing, snapshots, resumability, and long-run progress safety;
  - provides staged agent work packets for implementation.

## Validation

Planning-only validation:

```powershell
git diff --check
```

## Close Evidence

Closed with `docs/RESEARCH_V4_DISCOVERY_ENGINE_AGENT_PLAN.md` added as the ready-to-agent development plan for the next implementation stage.
