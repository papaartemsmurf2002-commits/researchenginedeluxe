# Sandbox First-Look Recommendations

Date: 2026-06-20

## Status

This is a first-look recommendation memo, not an implementation guideline, not
a completed audit, and not authorization to continue the next development
packet. It records the current critical read of the long autonomous Rapid
Strategy Iteration Sandbox run so future work starts from a visible review
posture instead of only from the prior self-audit.

## Scope Of The First Look

The review was intentionally limited. It checked the current dirty repo state,
the stage ledger, active index, known issues, the latest sandbox handoff, the
new sandbox package shape, selected diffs, and light validation. It did not
perform a full semantic audit of all WPR106 follow-up packets, all generated
artifacts, all strategy math, all discovery config changes, or all sandbox
sidecars.

## Summary Judgment

The long run appears to have produced real implementation work, not pure
fabrication. The sandbox package imports locally, the latest venue-expansion
test slice passed, the full sandbox test file passed, the live CLI boundary
tests passed, and the package compiled.

The same run also created a review-readiness problem. The worktree is too broad
and too dirty to treat the prior self-audit as acceptance evidence. The
previous self-audit is useful as a handoff, but it is too soft: it admits the
broad goal is incomplete and mentions worktree friction, yet it does not
quantify the dirty tree, call out commitability risks, or challenge risky
semantic changes outside the sandbox.

Recommended posture: pause new sandbox feature development until a real
repo-state and semantic audit classifies what should be kept, split, ignored,
parked, or reverted.

## Observed Signals

- The sandbox is real enough to import and pass local sandbox tests.
- The latest tested packet behavior is not obviously hallucinated.
- The repo has a large dirty surface: many tracked files are modified and many
  untracked files exist.
- New tracked code imports the untracked `tradingbotsuite.research_sandbox`
  package, so a partial commit can break the CLI.
- The sandbox package is large for an unreviewed local subsystem, with many
  modules and a large single test file.
- Generated output, including a local `outputs/.../node_modules` tree, is
  present and not ignored by the current repository rules.
- Some non-sandbox changes are semantically important, including reductions to
  durable/exact discovery config budgets under existing exact/durable-looking
  config names.
- Current known issues do not show open P0/P1 blockers, but open P2 risks
  remain and the full contract-suite reliability has been affected by local
  Windows socket exhaustion in prior validation notes.

## What The Prior Self-Audit Got Right

- It did not claim the broad sandbox objective was complete.
- It preserved the research-only, observe-only, non-promotable boundary.
- It named a concrete missing capability: consuming venue-expansion request
  bundles and scanning local archive roots without downloads or source
  mutation.
- It identified that the artifact/query system is powerful but not yet a
  closed rapid-research loop.
- It correctly framed descriptor bundles as navigation and handoff artifacts,
  not execution authorization.

## What The Prior Self-Audit Underplayed

- The scale of the dirty worktree and untracked files.
- The partial-commit risk caused by tracked imports of untracked source.
- The maintainability risk of a large new sandbox subsystem and a very large
  single test file.
- The presence of generated output and dependency trees outside current ignore
  rules.
- The need to review non-sandbox semantic diffs before continuing sandbox work.
- The risk that continuing immediately with another materializer packet will
  compound overbuild before the current work is reviewable.

## Recommendation

Do not treat the next materializer packet as the immediate next action by
default. First run a dedicated repo-state and sandbox-readiness audit.

Recommended audit questions:

1. Which dirty files are required for the sandbox to work?
2. Which untracked files are source, tests, configs, docs, generated artifacts,
   or accidental local output?
3. Which tracked changes are unrelated to the sandbox and need separate review?
4. Would a commit that excludes untracked files break imports or tests?
5. Do discovery config changes still match the names and evidence claims in
   docs and manifests?
6. Are all sandbox boundary flags enforced at artifact boundaries, not only in
   tests?
7. Can the existing sandbox prove a smallest useful closed loop on realistic
   2024+ local materials before any new broad feature work?

## Suggested Order After Audit

If the audit supports keeping the sandbox work, the next development should be
narrow:

1. Clean review posture: ignore or quarantine generated output, preserve source
   files needed by tracked imports, and split unrelated semantic changes.
2. Minimal venue-expansion materializer: local-root scan, descriptor candidates,
   and dry-run manifest patch only.
3. Smallest end-to-end realistic smoke: request bundle to descriptor candidate
   to manifest candidate to coverage to one rerun.
4. First-read dashboard or next-action command only if it reduces navigation
   cost for that closed loop.
5. Strict-validation descriptor bridge audit before any claim that the sandbox
   handoff is trustworthy.
6. Throughput benchmark after the loop works, not before.
7. Expand sweep expressiveness only from observed research needs, not from a
   broad abstract checklist.

## Agent Continuation Recommendation

The previous agent was productive, but the shape of the work suggests it needs
a reset in scope discipline before more autonomous development. Prefer a new
agent or a sharply updated goal after audit. If the same agent continues, it
should operate under a narrow packet that forbids new feature expansion until
the dirty tree and semantic risks are classified.

## Non-Claims

This memo does not claim:

- the sandbox is correct;
- the sandbox is incorrect;
- the previous agent fabricated the implementation;
- the previous agent's work should be reverted;
- the next materializer should be implemented;
- any candidate pack, paper signal, live signal, sizing instruction, order
  behavior, runtime-mode change, live configuration write, or promotion state
  exists.

It only recommends that the next step be audit-first, with development resumed
only after the current work is made reviewable.
