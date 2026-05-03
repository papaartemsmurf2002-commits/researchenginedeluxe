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
