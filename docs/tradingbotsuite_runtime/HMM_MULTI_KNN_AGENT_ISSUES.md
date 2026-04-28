# HMM Multi-KNN Agent Issues

This file is the shared clarification queue for HMM/KNN research agents.

## Protocol

- Agents append only unresolved blockers or high-impact ambiguities.
- Keep at most 4 unresolved issues in this file.
- If this file contains 4 or more unresolved issues, stop work and report:

```text
HMM_MULTI_KNN_AGENT_ISSUES.md contains 4 or more unresolved issues. Please provide a clarification markdown file for the collected issues.
```

- Do not invent product decisions to bypass a listed blocker.
- Resolve an issue by moving it from `Open Issues` to `Resolved Issues` with the clarification source and date.

## Issue Template

```markdown
### ISSUE-YYYYMMDD-NN: Short title

- Agent:
- Date:
- Task:
- Blocking question:
- Why this matters:
- Files or artifacts involved:
- Options considered:
- Recommended default if user approves:
- Status: open
```

## Open Issues

No open issues.

## Resolved Issues

### ISSUE-20260428-01: Root manual launcher drops config fields

- Agent: Execution and Risk Agent
- Date: 2026-04-28
- Task: HMM/KNN execution-risk boundary review
- Blocking question: Should root launchers be retained, and if retained, should they be converted to thin canonical CLI wrappers before any live/runtime merge?
- Why this matters: `run_manual.py` reconstructs `AppConfig` when overriding runtime mode and currently drops fields such as `research` and `operator_ui`. Root launchers are live-capable operational surfaces, so config loss can bypass future safety or isolation fields even though this does not wire HMM/KNN research output into execution.
- Files or artifacts involved: `run_manual.py`; `docs/tradingbotsuite_runtime/source_inputs/tradingbotsuite_critical_audit_orchestrator_next_agent.md`
- Options considered: Convert root launchers to canonical CLI wrappers; add a full-field config-copy helper and tests; remove root launchers from live/runtime scope.
- Recommended default if user approves: Convert `run_manual.py`, `run_server.py`, and `run_live_smoke.py` into thin wrappers around `python -m tradingbotsuite.main ...` and add regression tests proving all `AppConfig` fields are preserved.
- Resolution: Current worktree updates `run_manual.py` to use `dataclasses.replace(config, runtime_mode=...)`, preserving all existing `AppConfig` fields when overriding runtime mode. `src/tradingbotsuite/main.py` also uses replacement helpers for runtime-mode and research-config path changes.
- Status: resolved
