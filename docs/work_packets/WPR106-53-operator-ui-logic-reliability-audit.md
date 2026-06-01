# Work Packet: WPR106-53 Operator UI Logic Reliability Audit

## Goal

Perform a focused, high-attention audit of operator and research UI logic after
the WPR106-52 connector hardening. The packet checks that UI pages, browser
actions, route handlers, status labels, and action availability are current,
fast, and fail-closed.

This is a UI reliability and consistency packet. It does not advance the stage,
create candidate-ready claims, emit candidate packs, or change live/paper
execution behavior.

## Current Repo Facts

- Current implementation branch:
  `codex/wpr106-47-full-replay-exit-lab-controls`.
- WPR106-52 is committed and pushed, and draft PR #2 is open on GitHub.
- `gh` is installed and the user reports the local session is authenticated.
- `.pytest_cache` files are dirty from local validation and are not source
  artifacts for this packet.
- Root-level handoff prompt files under `docs/NEXT_AGENT_HANDOFF_WPR106_*.md`
  remain unrelated to this packet and should stay unstaged.
- `ISSUE-R104-001` remains the only open P1 issue in
  `docs/KNOWN_ISSUES.md`; no P0 issues are open.

## Allowed Edit Paths

Edits are allowed only where the UI audit or validation finds concrete defects
or consistency gaps:

- `docs/ACTIVE_INDEX.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/STAGE_R106_*.md`
- `docs/work_packets/WPR106-*.md`
- `docs/work_packets/WPR106-*-progress.jsonl`
- `src/tradingbotsuite/web/**`
- `src/tradingbotsuite/ui/**`
- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/operator_commands.py`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/research/**`
- `src/tradingbotsuite/research_cycle/**`
- `src/tradingbotsuite/research_discovery/**`
- `src/tradingbotsuite/research_artifacts/**`
- `tests/tradingbotsuite/test_operator_ui.py`
- `tests/test_operator_ui.py`
- `tests/integration/test_research_ui.py`
- `tests/contracts/**`

Generated empirical artifacts under `data/research/operator_runs/` remain local
research outputs and should stay out of git unless a later packet explicitly
scopes them.

## Research Boundary

- Research outputs are not live signals.
- Artifacts must remain `research_only: true`, `observe_only: true`, and
  `promotion_ready: false`.
- UI copy must not imply promotion readiness, live execution proof, paper
  trading readiness, order placement, sizing, or runtime authorization.
- Mutating UI actions must be guarded and must not write live configuration,
  change runtime mode, place orders, or weaken candidate gates.

## Review Plan

1. Reconfirm stage ledger, active index, known issues, and dependency fuse.
2. Audit backend UI route handlers for mutating-action guards, stale action
   contracts, output-root handling, and slow recursive scans.
3. Audit templates and embedded browser logic for fetch/header consistency,
   disabled/error states, stale labels, and action availability.
4. Add focused patches and regression tests for concrete issues only.
5. Run compile, focused UI suites, contracts, and broader validation when shared
   contracts are touched.
6. Update packet progress, active docs, and stage report with evidence.
7. Stage only intended changes, commit, and push the current branch.

## Acceptance Criteria

- No UI endpoint exposes an unguarded mutating action.
- Browser actions have consistent request headers, failure handling, and visible
  state for operators.
- UI labels accurately reflect current research-only gate state and open
  blockers.
- Operator pages avoid obviously expensive repeated scans where a bounded
  summary is sufficient.
- Focused UI validation passes.
- Compile and contract validation pass.
- Full-suite or materially equivalent broad validation passes when shared
  behavior changes.
- `git diff --check` passes, ignoring expected line-ending notices.
- Pushed changes contain only intended source, docs, and tests.
