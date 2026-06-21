# V2 Security Boundary Contract

Status: v2 contract foundation
Audit IDs: `V2-AUD-SEC-001`, `V2-AUD-SEC-002`, `V2-AUD-SEC-003`

## Purpose

Security boundaries keep v2 research code away from live execution, secrets,
unsafe paths, and unsafe artifacts.

## Initial Schema Names

- `PathPolicy`
- `TrustedRoot`
- `SecretPolicy`
- `SecretScanResult`
- `TrustedArtifactRef`
- `TrustedArtifactValidation`
- `CommandClass`
- `CommandClassification`

## Required Rules

- V2 modules must not import live, paper, order-placement, sizing, runtime, or
  promotion execution paths.
- Root path checks reject traversal outside configured archive/run roots.
- Secrets fail closed and are not read by strategy specs/plugins.
- Required webhook and credential-like secrets fail closed when missing,
  default-like, too short, or low entropy.
- Pickle or unsafe deserialization is blocked. Artifact trust requires root
  containment, file existence, and a matching SHA-256 digest before any later
  consumer can treat the file as trusted.
- Logs redact secrets and account-like values.
- V2 command metadata records whether a command is research, collector, admin,
  or live-forbidden. Accepted v2 command metadata rejects live runtime touches,
  order placement, sizing output, runtime-mode mutation, paper/live signals,
  and promotion implications.

## Forbidden

- Direct live/order imports in v2.
- Arbitrary file reads from strategy code.
- Runtime-mode mutation.
- Trusting artifacts by path alone.
- Logging raw secrets, webhook tokens, wallet/account-like values, or API keys.
