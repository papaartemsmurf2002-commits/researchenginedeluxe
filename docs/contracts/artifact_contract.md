# Artifact Contract

Research artifacts must be explicit about non-live status.

## Required research boundary fields

```json
{
  "research_only": true,
  "observe_only": true,
  "promotion_ready": false,
  "live_signal_input": false,
  "position_sizing_input": false,
  "operator_control_input": false,
  "live_execution_input": false,
  "runtime_control_input": false
}
```

## Rules

- Missing boundary fields make an artifact invalid.
- Any `research_only` or `observe_only` artifact is not a live input.
- Generated artifacts must include content hashes or config hashes where applicable.
- Generated artifacts must not be committed unless they are small deterministic fixtures explicitly listed in a work packet.
- Stage 12 ablation manifests must remain `research_only`, `observe_only`, and `promotion_ready: false`; accepted hypotheses require OOS and stress evidence and cannot be based on in-sample tuning only.
- Stage 12 aggregate research manifests must include a completion-limitations artifact when empirical OOS/stress evidence is not available. Planning artifacts alone are not promotion evidence.
- Stage 13 readiness manifests are planning and evidence-review artifacts only. `paper-run-manifest-v1`, `shadow-run-archive-manifest-v1`, `testnet-validation-manifest-v1`, and `stage13-readiness-report-v1` must keep all live input/control flags false.
- BTC-only artifacts must be rejected for ETH or multi-asset readiness requests unless the manifest explicitly includes the requested symbol in `asset_scope`.
- Execution-journal evidence for future live approval must include deterministic cloids, order intents, fills, cancel requests, reconciliation, and scheduled-cancel/dead-man evidence.
