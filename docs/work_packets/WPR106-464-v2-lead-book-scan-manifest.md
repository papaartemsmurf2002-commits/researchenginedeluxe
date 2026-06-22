# WPR106-464 - V2 Lead Book Scan Manifest

Status: self_checked
Audit ID: `V2-AUD-LEAD-005`
Related audit IDs: `V2-AUD-AUTONOMY-015`

## Objective

Add a read-only Lead Book queue scan surface that filters the canonical Lead
Book by one or more lead states, writes a research-only scan manifest, and
exposes an equivalent `redx leadbook scan --status ...` CLI path. This fills
the Lead Book side of the required `Lead Book / strategy-spec queue scan`
operational loop without enqueueing jobs, running backtests, changing lead
state, or implying candidate/paper/live/promotion readiness.

## Allowed Paths

- `docs/work_packets/WPR106-464-v2-lead-book-scan-manifest.md`
- `docs/contracts/lead_book_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/lead_book/schemas.py`
- `src/tradingbotsuite/v2/lead_book/service.py`
- `src/tradingbotsuite/v2/lead_book/__init__.py`
- `src/tradingbotsuite/v2/cli/main.py`
- `tests/v2/test_lead_book_scan_phase34.py`

## No-Touch Paths

- `src/**/live/**`
- `src/**/runtime.py`
- `run_live_smoke.py`
- `run_manual.py`
- order-placement, broker, exchange-submit, sizing, runtime-config, promotion,
  shadow, and candidate-pack truth-layer paths
- committed `data/research/fixtures/**`
- committed `data/research/historical_cycles/**`
- legacy GUI/operator UI paths
- `src/tradingbot/**`
- `.env`, credential files, local SQLite operator DBs, private caches, and
  unreviewed generated `outputs/**`

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_lead_book_scan_phase34.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Planned Changed Files

- `src/tradingbotsuite/v2/lead_book/schemas.py`
- `src/tradingbotsuite/v2/lead_book/service.py`
- `src/tradingbotsuite/v2/lead_book/__init__.py`
- `src/tradingbotsuite/v2/cli/main.py`
- `tests/v2/test_lead_book_scan_phase34.py`
- `docs/contracts/lead_book_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR106-464-v2-lead-book-scan-manifest.md`

## Decisions Made

- The scan is read-only. It does not mutate Lead Book rows, request human
  inspection, approve deep validation, enqueue worker jobs, run backtests, or
  update ledger rows.
- The scan consumes the canonical Parquet Lead Book through `LeadBookStore`
  and writes only a derived JSON manifest under an explicit output path.
- Multiple status filters are supported to match the execution brief's
  `sandbox_screened,deep_validation_requested` queue-scan shape.
- Empty scans are blocker evidence for manager loops, not failures and not
  readiness claims.
- The independent WPR106-463 scheduler audit was recorded in the audit index
  and control docs because the audit completed during this packet. It found no
  P0/P1 findings and left a P2 focused-test follow-up.

## Acceptance Evidence

- Changed files stayed inside the allowed paths listed above.
- No-touch paths were not edited.
- Focused validation passed:

```powershell
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "& { `$env:PYTHONPATH = 'src'; python -m pytest tests/v2/test_lead_book_scan_phase34.py -q }"
# 4 passed in 0.49s
```

- Baseline validation passed:

```powershell
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "& { `$env:PYTHONPATH = 'src'; python -m pytest tests/v2 -q }"
# 317 passed in 27.10s

C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "& { `$env:PYTHONPATH = 'src'; python -m compileall -q src/tradingbotsuite }"
# passed with no output

C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "& { `$env:PYTHONPATH = 'src'; python -m pytest tests/contracts -q }"
# 463 passed in 6.92s

git diff --check
# passed; existing LF-to-CRLF working-tree warnings were reported by Git for
# modified files.
```

- Independent audit evidence: WPR106-463 scheduler tick audit completed with
  no P0/P1 findings. P2 follow-up remains to add focused missing-manifest and
  max-jobs-per-plan scheduler blocker tests.
- Open blockers: `ISSUE-R106-026` remains the known Python 3.11/full-suite
  parity blocker; this chunk did not change that risk.
- Acceptance status: implemented and self-checked as a read-only Lead Book
  queue visibility manifest. The result is not strategy performance evidence,
  not accepted research evidence, not autonomous-readiness proof, and not a
  paper/live/order/sizing/runtime/promotion surface.
