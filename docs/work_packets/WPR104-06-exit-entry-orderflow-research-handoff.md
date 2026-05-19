# WPR104-06 Exit Entry Orderflow Research Handoff

Owner: Codex Research Agent
Stage: R104 candidate validation on durable evidence
Status: closed
Created: 2026-05-19

## Goal

Synthesize the completed BTCUSDT exact discovery sweep, current research
weaknesses, and the next empirical falsification plan into one handoff
document for a separate research and evaluation model. The handoff must focus
on separating entry quality, exit-policy value-add, orderflow value-add, KNN
configuration, regime/filter effects, and compute-saving evaluation order.

## Allowed paths

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/**`
- `docs/stage_reports/**`
- `docs/KNOWN_ISSUES.md`

## Constraints

- Documentation only; do not change research code, configs, generated run
  artifacts, fixture packs, live runtime settings, order-placement code, or
  promotion behavior.
- Keep all findings research-only, observe-only, and `promotion_ready: false`.
- Do not claim a profitable or candidate-ready strategy from the completed
  sweep.
- Preserve `ISSUE-R104-001`; compact durable fixtures remain screening
  evidence, not expanded candidate-ready evidence.

## Planned implementation

1. Inspect the completed `exact_entry_sweep_btcusdt_durable_r104_v1` run
   manifest, resolved spec, run state, and ledgers.
2. Cross-reference existing exit lab, filter ablation, feature-set, orderflow,
   KNN, and regime surfaces already present in the branch.
3. Create a single research handoff document with the latest run evidence,
   weak points, recommended experiment matrix, decision rules, and next work
   packets.
4. Update the orchestrator ledger with the closed packet and evidence link.
5. Run documentation-focused validation.

## Validation target

```powershell
git diff --check
```

## Exit evidence

- Completed run evidence was inspected from
  `data/research/operator_runs/discovery_runs/exact-entry-sweep-btcusdt-durable-r104-v1/run-discovery-142f3b61b761470b8aeb105967dd9c47`.
- Handoff report:
  `docs/stage_reports/STAGE_R104_EXIT_ENTRY_ORDERFLOW_RESEARCH_HANDOFF.md`
- Validation passed:
  `git diff --check`.
