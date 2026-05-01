# Known Issues

Last updated: 2026-05-01

This registry is the blocking issue source for orchestrator stage gates.

Severity levels:

- P0: safety, data leakage, live trading risk, corrupt data, branch boundary violation.
- P1: invalid backtest assumption, non-deterministic experiment, broken artifact contract, severe performance blocker.
- P2: incomplete docs, minor missing tests, non-blocking refactor debt.
- P3: polish and convenience.

Stage advancement stop rule:

- Any open P0 blocks stage advancement.
- Four or more unresolved P1 issues block stage advancement.
- P2/P3 can carry forward only with explicit orchestrator note and owner.

## Current summary

| Severity | Open | In progress | Resolved | Accepted debt |
| --- | ---: | ---: | ---: | ---: |
| P0 | 0 | 0 | 0 | 0 |
| P1 | 0 | 0 | 0 | 0 |
| P2 | 0 | 0 | 0 | 0 |
| P3 | 0 | 0 | 0 | 0 |

No issues are currently recorded.

## Issue template

```markdown
## ISSUE-ID: Short title

Severity: P0/P1/P2/P3
Stage discovered:
Owner:
Status: open | in_progress | resolved | accepted_debt
Paths affected:

### Problem

### Evidence

### Required resolution

### Resolution notes
```
