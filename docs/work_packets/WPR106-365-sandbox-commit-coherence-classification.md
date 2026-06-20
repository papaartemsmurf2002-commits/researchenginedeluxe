# WPR106-365 - Sandbox Commit Coherence Classification

## Status

closed

## Objective

Classify the local Rapid Strategy Iteration Sandbox source, test, and smoke
configuration surface that must be kept together for a coherent publication,
while explicitly leaving inherited unrelated dirty-tree work out of scope.

## Dependencies

- `RAPID_STRATEGY_SANDBOX_AUDIT.md`
- `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md`
- `docs/work_packets/WPR106-362-post-audit-sandbox-safety-coherence.md`
- `docs/work_packets/WPR106-363-red-test-repair-strategy-discovery-resume.md`
- `docs/work_packets/WPR106-364-sandbox-ci-boundary-coverage.md`

## Allowed paths

- `docs/work_packets/WPR106-365-sandbox-commit-coherence-classification.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_COMMIT_COHERENCE_CLASSIFICATION_REPORT.md`
- `docs/research_knowledge/WPR106-365-sandbox-commit-surface-classification.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Boundary constraints

- Documentation-only classification.
- No staging, committing, deleting, moving, reverting, or rewriting unrelated
  dirty-tree files.
- No source behavior, config semantics, generated artifact, archive
  manifest/source mutation, provider download, replay execution,
  strict-validation execution, candidate pack, paper/live artifact, sizing,
  order behavior, runtime-mode change, live configuration write, or promotion
  state change.

## Acceptance criteria

- The intended sandbox publication surface is listed explicitly.
- Generated output hygiene is verified.
- Broader inherited dirty-tree work is documented as out of scope.
- The packet records that commit coherence still requires publishing/staging
  the classified sandbox source, config, tests, and packet/report files
  together.

## Validation

```powershell
git ls-files --others --exclude-standard src\tradingbotsuite\research_sandbox tests\research_sandbox configs\sandbox
git ls-files --others --exclude-standard outputs | Select-Object -First 20
git diff --check
```
