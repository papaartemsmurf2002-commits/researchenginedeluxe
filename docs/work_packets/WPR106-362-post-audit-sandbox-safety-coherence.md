# WPR106-362 - Post-Audit Sandbox Safety And Coherence

## Status

closed

## Objective

Repair the highest-risk post-audit Rapid Strategy Iteration Sandbox blockers
that prevent safe local use: generated-output hygiene, path-safe sandbox run
IDs, output-root containment, recursive research-boundary validation,
descriptor-window enforcement, artifact child-path containment, deterministic
decision identity, and explicit proxy-only strategy semantics where applicable.

This packet does not add live, paper, sizing, order, candidate-pack, strict
validation execution, provider download, or promotion behavior.

## Dependencies

- `RAPID_STRATEGY_SANDBOX_AUDIT.md`
- `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md`
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`

## Allowed paths

- `.gitignore`
- `src/tradingbotsuite/research_sandbox/**`
- `tests/research_sandbox/**`
- `docs/work_packets/WPR106-362-post-audit-sandbox-safety-coherence.md`
- `docs/stage_reports/STAGE_R106_POST_AUDIT_SANDBOX_SAFETY_COHERENCE_REPORT.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`

## Boundary constraints

- Sandbox outputs remain `research_only: true`, `observe_only: true`,
  `sandbox_only: true`, `promotion_ready: false`,
  `candidate_evidence: false`, and `candidate_pack_eligible: false`.
- No live signal, paper signal, sizing instruction, order-placement
  instruction, runtime-mode change, live configuration write, candidate-pack
  write, strict-validation execution, provider download, source archive
  mutation, or promotion state change.
- No use of data older than 2024 for sandbox evidence.
- Missing source coverage, bad paths, boundary violations, proxy-only strategy
  ambiguity, or descriptor-window gaps must fail closed with explicit blocker
  reasons.

## Acceptance criteria

- Generated root `outputs/` is ignored so local dependency/output trees cannot
  be accidentally surfaced as review material.
- `SandboxRunSpec.run_id` accepts only safe single path components.
- Sandbox artifact writers resolve run directories under the configured output
  root and reject escaping paths.
- Sandbox boundary validation recursively rejects forbidden nested keys and
  truthy forbidden values in free-form payloads before artifacts are persisted.
- Preflight and execution apply the intersection of the run data window and the
  routed venue archive descriptor window.
- Artifact integrity/consumer code rejects manifest-declared child paths that
  escape the run or suite directory before reading or hashing.
- Trial identity includes decision-affecting fields such as minimum-trade
  thresholds and avoids local archive paths as decision identity when logical
  source identity is available.
- Built-in proxy blueprint output is explicitly proxy-only and cannot be
  presented as a real implementation of named strict-cycle strategies.

## Validation

Run focused validation first:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
python -m compileall -q src\tradingbotsuite
```

Run contracts when the local Windows socket state allows it:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

If the known Windows socket exhaustion blocker recurs, cite
`ISSUE-R106-026` and do not claim green contract validation.

## Stop conditions

- Any sandbox artifact can contain live/paper/order/sizing/promotion/candidate
  authorization fields after recursive validation.
- Any sandbox run can write outside its configured output root.
- Any artifact consumer can read a manifest child path outside the intended
  artifact directory.
- Any descriptor-routed sweep can score rows outside the descriptor/run window
  intersection.
- A fix requires weakening the strict validation cycle or candidate-pack gate.
