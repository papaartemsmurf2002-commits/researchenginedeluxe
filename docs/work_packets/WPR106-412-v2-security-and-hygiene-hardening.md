# WPR106-412 V2 Security And Hygiene Hardening

Status: closed
Owner: Codex Research Agent
Created: 2026-06-21

## Objective

Implement a bounded Phase 21 security hygiene slice from
`docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md`. This packet adds v2-local
secret fail-closed policy, logging redaction, trusted artifact validation, and
command classification metadata so research commands stay isolated from
live/order/sizing/runtime behavior.

This packet does not modify legacy live/runtime/order code, run trading jobs,
write generated research evidence, create candidate packs, place orders,
produce paper/live signals, emit sizing instructions, change runtime mode, or
create promotion-ready artifacts.

## Audit IDs

- `V2-AUD-SEC-003`

## Dependencies

- `docs/contracts/security_boundary_contract.md`
- Existing v2 root containment policy from `V2-AUD-SEC-002`
- Existing v2 package/import-boundary baseline

## Allowed Paths

- `docs/contracts/security_boundary_contract.md`
- `src/tradingbotsuite/v2/security/**`
- `tests/v2/**`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/work_packets/WPR106-412-v2-security-and-hygiene-hardening.md`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Constraints

- V2 security helpers must not import live, paper, order-placement, sizing,
  runtime mutation, or promotion execution paths.
- Secret policy must fail closed for required missing/default/weak values.
- Artifact validation must require root containment and SHA-256 matching before
  trusting files.
- Pickle-like artifacts remain blocked in this packet; no unsafe
  deserialization support is added.
- Command classification must reject live/order/sizing/runtime/promotion
  implications for v2 research commands.

## Acceptance Criteria

- Required webhook/credential-like secrets fail closed when missing, weak, or
  default-like.
- Logging redaction masks secret-bearing keys and sensitive token-like text.
- Trusted artifact validation accepts only existing root-contained files whose
  SHA-256 matches the expected digest.
- Pickle/joblib-style artifact extensions are rejected.
- Command metadata rejects live, order, sizing, runtime-mode, and promotion
  implications.
- Existing root containment traversal behavior remains covered.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_security_hygiene_phase21.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_contract_docs.py -q
git diff --check
```

No broader non-v2 tests are required unless shared implementation files outside
the v2 shell are changed.

## Stop Conditions

- A no-touch live/runtime/order/sizing path must be modified.
- Secret handling requires reading real local credential files or `.env`.
- Artifact acceptance would require pickle/deserialization enablement.
- Command classification cannot be enforced without touching legacy runtime
  dispatch paths.

## Completion Notes

Closed on 2026-06-21.

- Added v2-local security hygiene helpers:
  - `SecretPolicy`;
  - `SecretScanResult`;
  - `redact_text`;
  - `redact_mapping`;
  - `TrustedArtifactRef`;
  - `TrustedArtifactValidation`;
  - `validate_trusted_artifact`;
  - `CommandClass`;
  - `CommandClassification`.
- Enforced missing/default/short/low-entropy secret rejection.
- Added logging redaction for secret-bearing keys, token-like text, and
  account-like wallet values.
- Added trusted artifact validation requiring root containment, file existence,
  and matching SHA-256 before acceptance.
- Kept pickle-like `.pkl`, `.pickle`, `.joblib`, and `.dill` artifacts blocked.
- Added accepted-command metadata validation rejecting live runtime touches,
  orders, sizing, runtime-mode mutation, paper/live signals, and promotion
  implications.
- Updated the security boundary contract and marked `V2-AUD-SEC-003` as
  `self_checked`.
- No legacy live/runtime/order/sizing path was touched. No generated research
  evidence, candidate pack, paper/live signal, sizing instruction, order
  placement, runtime-mode change, promotion behavior, or live-runtime import
  was introduced.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_security_hygiene_phase21.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_contract_docs.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Result:

- Focused Phase 21 tests passed: 14 passed.
- Full v2 tests passed: 156 passed.
- `compileall` for `src\tradingbotsuite\v2` passed.
- Contract-doc smoke passed: 2 passed.
- Full `compileall` for `src\tradingbotsuite` passed.
- Contract tests passed: 462 passed.
- `git diff --check` passed with LF-to-CRLF warnings only for existing
  text-file line-ending behavior.
