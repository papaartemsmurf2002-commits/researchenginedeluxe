# WPR106-389 V2 Adoption Conversation Package

Status: closed
Owner: Codex Research Agent
Created: 2026-06-20

## Objective

Create one consolidated Markdown document that packages this conversation,
the latest repo read, the imported v2 roadmap, the old repo analysis handoff,
the user's stated migration preferences, and Codex recommendations for v2
adoption and legacy treatment.

This packet is documentation-only. It creates a handoff/reference document and
does not change implementation behavior, generated research artifacts,
candidate gates, strategy code, archive files, runtime code, live/paper
surfaces, sizing, order placement, or promotion state.

## Dependencies

- `AGENTS.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- `docs/KNOWN_ISSUES.md`
- `docs/RESEARCH_ENGINE_DELUXE_V2_MULTI_VENUE_PERP_RESEARCH_ROADMAP.md`
- `docs/RESEARCH_ROADMAP_DIRECTION_COMPARISON_2026_06_20.md`
- `C:/Users/papaa/Downloads/repo_analysis_implementation_handoff (1).md`

## Allowed Paths

- `docs/work_packets/WPR106-389-v2-adoption-conversation-package.md`
- `docs/V2_ADOPTION_CONVERSATION_REPO_PACKAGE_2026_06_20.md`

## Boundary Constraints

- Preserve research-only, observe-only, non-promotable semantics.
- Do not create or modify candidate packs.
- Do not create paper/live artifacts.
- Do not place orders, change runtime mode, write live configuration, or add
  sizing/order-placement behavior.
- Do not modify source code, tests, configs, generated data, or archive files.

## Acceptance Criteria

- The consolidated Markdown document exists under `docs/`.
- It labels user-provided source documents, user thoughts, Codex thoughts, and
  repo-read findings separately.
- It embeds the two user-provided documents as labeled source appendices.
- It states how legacy systems should be treated under v2 adoption.
- It records that the document is a handoff/reference package, not an
  implementation authorization by itself.

## Validation

Documentation-only validation:

```powershell
git diff --check
```

No compile or pytest validation is required because no implementation files are
changed.

## Stop Conditions

- A source, config, test, archive, generated-data, live, paper, runtime,
  sizing, order, candidate-pack, or promotion change becomes necessary.
- The package would mislabel sandbox or legacy evidence as candidate-ready or
  promotion-ready.

## Completion Notes

Closed on 2026-06-20.

- Added the consolidated package at
  `docs/V2_ADOPTION_CONVERSATION_REPO_PACKAGE_2026_06_20.md`.
- The package includes:
  - final repo read from active index, stage ledger, dependency fuse, known
    issues, and git status;
  - user direction from the conversation;
  - Codex recommendations for v2 adoption, legacy treatment, Lead Book,
    single-strategy deep validation, top-3 final hard-test phase, and GUI
    treatment;
  - assessment of the v2 roadmap;
  - assessment of the old repo-analysis implementation handoff;
  - recommended next work packet and v2 migration backlog;
  - full embedded text of the imported v2 roadmap;
  - full embedded text of the old downloaded handoff document.
- No source, test, config, generated data, archive, live, paper, runtime,
  candidate-pack, sizing, order-placement, or promotion behavior was changed.

Validation:

```powershell
git diff --check
```

Result: passed, with the existing LF-to-CRLF warning for
`docs/ACTIVE_INDEX.md`.
